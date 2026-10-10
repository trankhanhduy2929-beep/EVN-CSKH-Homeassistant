from __future__ import annotations

import hashlib
import json

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

DOMAIN = "evn_cskh"
NAME = "EVN CSKH"
VERSION = "0.5.1"
MIN_HA_VERSION = "2025.12"
PLATFORMS = (Platform.SENSOR, Platform.BUTTON, Platform.BINARY_SENSOR)

CONF_CUSTOMERS = "customers"
CONF_DEVICE_ID = "device_id"
CONF_SELECTED_CUSTOMERS = "selected_customers"
CONF_TOKENS = "tokens"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 360
MIN_UPDATE_INTERVAL = 60
MAX_UPDATE_INTERVAL = 1440


def account_unique_id(username: str) -> str:
    return hashlib.sha256(username.strip().lower().encode()).hexdigest()


def scope_id(*scope: str | None) -> str:
    return hashlib.sha256(
        json.dumps(scope, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def customer_device_info(scope: tuple[str | None, ...]) -> DeviceInfo:
    device_id = scope_id(*scope)
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=f"{NAME} {device_id[:8]}",
        manufacturer="EVN",
        model="Customer account",
        entry_type=DeviceEntryType.SERVICE,
    )


def interval_minutes(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not MIN_UPDATE_INTERVAL <= value <= MAX_UPDATE_INTERVAL
        or int(value) != value
    ):
        raise ValueError("The update interval must be 60 to 1440 whole minutes.")
    return int(value)
