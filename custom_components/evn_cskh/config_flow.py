from __future__ import annotations

import secrets
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorMode,
    TextSelector,
    TextSelectorType,
)

from .api import (
    EvnAuthError,
    EvnClient,
    EvnConnectionError,
    EvnError,
    EvnResponseError,
    EvnUserActionRequired,
)
from .const import (
    CONF_CUSTOMERS,
    CONF_DEVICE_ID,
    CONF_SELECTED_CUSTOMERS,
    CONF_TOKENS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    NAME,
    account_unique_id,
    interval_minutes,
)
from .coordinator import customer_inventory, customer_key

_CREDENTIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector({"autocomplete": "username"}),
        vol.Required(CONF_PASSWORD): TextSelector(
            {"type": TextSelectorType.PASSWORD, "autocomplete": "current-password"}
        ),
    }
)


class EvnConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._device_id: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EvnOptionsFlow:
        return EvnOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_credentials(user_input, "user")

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_credentials(
            user_input, "reauth_confirm", self._get_reauth_entry()
        )

    async def _async_credentials(
        self,
        user_input: dict[str, Any] | None,
        step_id: str,
        entry: ConfigEntry | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            if not isinstance(username, str) or not username.strip():
                errors[CONF_USERNAME] = "invalid_username"
            if not isinstance(password, str) or not password:
                errors[CONF_PASSWORD] = "invalid_password"
            if not errors:
                username = str(username).strip()
                password = str(password)
                unique_id = account_unique_id(username)
                if entry is not None and unique_id != account_unique_id(
                    entry.data[CONF_USERNAME]
                ):
                    errors["base"] = "wrong_account"
                else:
                    await self.async_set_unique_id(unique_id)
                    if entry is None:
                        self._abort_if_unique_id_configured()
                    else:
                        self._abort_if_unique_id_mismatch(reason="wrong_account")
                    if entry is not None:
                        self._device_id = entry.data[CONF_DEVICE_ID]
                    elif self._device_id is None:
                        self._device_id = secrets.token_hex(8)
                    assert self._device_id is not None
                    try:
                        client = EvnClient(
                            async_get_clientsession(self.hass),
                            username,
                            password,
                            self._device_id,
                        )
                        await client.login()
                        customers = await client.customers()
                        if not customers:
                            return self.async_abort(reason="no_customers")
                        tokens = client.tokens
                        if tokens is None:
                            raise EvnAuthError()
                    except EvnUserActionRequired:
                        errors["base"] = "user_action_required"
                    except EvnAuthError:
                        errors["base"] = "invalid_auth"
                    except EvnConnectionError:
                        errors["base"] = "cannot_connect"
                    except EvnResponseError:
                        errors["base"] = "invalid_response"
                    except EvnError:
                        errors["base"] = "unknown"
                    else:
                        data = {
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_DEVICE_ID: self._device_id,
                            CONF_CUSTOMERS: customer_inventory(customers),
                            CONF_TOKENS: tokens.to_dict(),
                        }
                        if entry is not None:
                            return self.async_update_reload_and_abort(
                                entry, title=NAME, data_updates=data
                            )
                        return self.async_create_entry(
                            title=NAME,
                            data=data,
                            options={
                                CONF_SELECTED_CUSTOMERS: [
                                    customer_key(customer) for customer in customers
                                ],
                                CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                            },
                        )
        suggested = (
            {CONF_USERNAME: entry.data[CONF_USERNAME]} if entry is not None else {}
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                _CREDENTIAL_SCHEMA, suggested
            ),
            errors=errors,
        )


class EvnOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        inventory = self.config_entry.data.get(CONF_CUSTOMERS, [])
        authorized = [f"{row['management_unit']}:{row['code']}" for row in inventory]
        errors: dict[str, str] = {}
        minutes = DEFAULT_UPDATE_INTERVAL
        if user_input is not None:
            try:
                minutes = interval_minutes(user_input.get(CONF_UPDATE_INTERVAL))
            except ValueError:
                errors[CONF_UPDATE_INTERVAL] = "invalid_interval"
            selected = user_input.get(CONF_SELECTED_CUSTOMERS)
            if not isinstance(selected, list) or not selected:
                errors[CONF_SELECTED_CUSTOMERS] = "no_selection"
            elif any(
                not isinstance(key, str) or key not in authorized for key in selected
            ):
                errors[CONF_SELECTED_CUSTOMERS] = "invalid_customer"
            if not errors:
                assert isinstance(selected, list)
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_UPDATE_INTERVAL: minutes,
                        CONF_SELECTED_CUSTOMERS: list(dict.fromkeys(selected)),
                    },
                )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): NumberSelector(
                    {
                        "min": MIN_UPDATE_INTERVAL,
                        "max": MAX_UPDATE_INTERVAL,
                        "step": 1,
                        "mode": NumberSelectorMode.BOX,
                        "unit_of_measurement": "min",
                    }
                ),
                vol.Required(
                    CONF_SELECTED_CUSTOMERS,
                    default=self.config_entry.options.get(CONF_SELECTED_CUSTOMERS, []),
                ): SelectSelector(
                    {
                        "options": authorized,
                        "multiple": True,
                        "custom_value": False,
                        "mode": SelectSelectorMode.LIST,
                    }
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
