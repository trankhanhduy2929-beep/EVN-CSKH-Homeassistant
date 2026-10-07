from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    Customer,
    EvnAuthError,
    EvnClient,
    EvnConnectionError,
    EvnError,
    EvnResponseError,
    EvnUserActionRequired,
    Snapshot,
)
from .const import (
    CONF_CUSTOMERS,
    CONF_SELECTED_CUSTOMERS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    NAME,
    interval_minutes,
)

_LOGGER = logging.getLogger(__name__)


def customer_key(customer: Customer) -> str:
    return f"{customer.management_unit}:{customer.code}"


def customer_inventory(customers: list[Customer]) -> list[dict[str, str]]:
    return [
        {"code": customer.code, "management_unit": customer.management_unit}
        for customer in sorted(customers, key=customer_key)
    ]


class EvnCoordinator(DataUpdateCoordinator[dict[str, Snapshot]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry[EvnCoordinator],
        client: EvnClient,
    ) -> None:
        try:
            minutes = interval_minutes(
                entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            )
        except ValueError:
            raise ConfigEntryError(
                "Set an update interval of 60 to 1440 whole minutes in the options.",
                translation_domain=DOMAIN,
                translation_key="invalid_interval",
            ) from None
        selected = entry.options.get(CONF_SELECTED_CUSTOMERS, [])
        if (
            not isinstance(selected, list)
            or not selected
            or any(not isinstance(key, str) or not key for key in selected)
        ):
            raise ConfigEntryError(
                "Select at least one authorized customer in the integration options.",
                translation_domain=DOMAIN,
                translation_key="invalid_selection",
            )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=NAME,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.entry = entry
        self.selected_customers = tuple(dict.fromkeys(selected))

    async def _async_update_data(self) -> dict[str, Snapshot]:
        try:
            customers = await self.client.customers()
            authorized = {customer_key(customer): customer for customer in customers}
            if len(authorized) != len(customers):
                raise EvnResponseError()
            inventory = customer_inventory(customers)
            if self.entry.data.get(CONF_CUSTOMERS) != inventory:
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, CONF_CUSTOMERS: inventory}
                )
            if not authorized:
                raise ConfigEntryAuthFailed(
                    "No linked customers remain. Link a customer in the official EVN "
                    "application, then reauthenticate.",
                    translation_domain=DOMAIN,
                    translation_key="no_customers",
                )
            if any(key not in authorized for key in self.selected_customers):
                raise ConfigEntryAuthFailed(
                    "A selected customer is no longer linked to this account. "
                    "Review the selected customers in the options or reauthenticate.",
                    translation_domain=DOMAIN,
                    translation_key="customer_removed",
                )
            snapshots: dict[str, Snapshot] = {}
            for key in self.selected_customers:
                snapshot = await self.client.fetch_snapshot(authorized[key])
                if snapshot.customer != authorized[key]:
                    raise EvnResponseError()
                snapshots[key] = snapshot
            return snapshots
        except EvnUserActionRequired:
            raise ConfigEntryAuthFailed(
                "Complete the account action in the official EVN application, "
                "then reauthenticate.",
                translation_domain=DOMAIN,
                translation_key="user_action_required",
            ) from None
        except EvnAuthError:
            raise ConfigEntryAuthFailed(
                "EVN authentication failed. Reauthenticate this integration.",
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from None
        except EvnConnectionError:
            raise UpdateFailed("EVN service is temporarily unavailable.") from None
        except EvnResponseError:
            raise UpdateFailed("EVN returned an invalid response.") from None
        except EvnError:
            raise UpdateFailed("EVN update failed.") from None


type EvnConfigEntry = ConfigEntry[EvnCoordinator]
