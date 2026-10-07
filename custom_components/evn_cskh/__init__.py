from __future__ import annotations

import logging

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
    coordinator = EvnCoordinator(hass, entry, client)
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
