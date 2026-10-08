from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EvnAuthError, EvnClient, EvnError, TokenState
from .const import CONF_DEVICE_ID, CONF_TOKENS, DOMAIN, PLATFORMS
from .coordinator import EvnConfigEntry, EvnCoordinator
from .panel import (
    PanelUnavailable,
    async_attach_entry,
    async_detach_entry,
    async_setup_panel,
)

_LOGGER = logging.getLogger(__name__)


class _ScheduledEvnCoordinator(EvnCoordinator):
    _published_refresh: float | None = None

    @property
    def _refresh_deadline(self) -> float | None:
        handle = getattr(self._unsub_refresh, "__self__", None)
        if not isinstance(handle, asyncio.TimerHandle) or handle.cancelled():
            return None
        return handle.when()

    @property
    def next_iteration(self) -> datetime | None:
        deadline = self._refresh_deadline
        if deadline is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=deadline - self.hass.loop.time())

    @callback
    def async_update_listeners(self) -> None:
        self._published_refresh = self._refresh_deadline
        super().async_update_listeners()

    async def _async_refresh(
        self,
        log_failures: bool = True,
        raise_on_auth_failed: bool = False,
        scheduled: bool = False,
        raise_on_entry_error: bool = False,
    ) -> None:
        previous_success = self.last_update_success
        await super()._async_refresh(
            log_failures=log_failures,
            raise_on_auth_failed=raise_on_auth_failed,
            scheduled=scheduled,
            raise_on_entry_error=raise_on_entry_error,
        )
        if (
            not previous_success
            and not self.last_update_success
            and self._published_refresh != self._refresh_deadline
            and not self._shutdown_requested
            and not self.hass.is_stopping
        ):
            self.async_update_listeners()


async def async_setup_entry(hass: HomeAssistant, entry: EvnConfigEntry) -> bool:
    @callback
    def async_store_tokens(tokens: TokenState) -> None:
        serialized = tokens.to_dict()
        if entry.data.get(CONF_TOKENS) != serialized:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_TOKENS: serialized}
            )

    try:
        stored = entry.data.get(CONF_TOKENS)
        tokens = TokenState.from_dict(stored) if stored is not None else None
        client = EvnClient(
            async_get_clientsession(hass),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_DEVICE_ID],
            tokens=tokens,
            on_tokens=async_store_tokens,
        )
    except EvnAuthError:
        raise ConfigEntryAuthFailed(
            "Stored EVN authentication is invalid. Reauthenticate this integration.",
            translation_domain=DOMAIN,
            translation_key="auth_failed",
        ) from None
    except (EvnError, KeyError):
        raise ConfigEntryError("Stored EVN account configuration is invalid.") from None
    coordinator = _ScheduledEvnCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    try:
        await async_setup_panel(hass)
        await async_attach_entry(hass, entry)
    except PanelUnavailable as error:
        _LOGGER.debug("EVN CSKH panel is unavailable: %s", error)
    except Exception:
        _LOGGER.warning("EVN CSKH panel could not be registered", exc_info=True)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EvnConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await async_detach_entry(hass, entry.entry_id)
    return unloaded
