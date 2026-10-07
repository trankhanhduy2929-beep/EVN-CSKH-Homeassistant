from __future__ import annotations

import hashlib

from homeassistant.const import Platform

DOMAIN = "evn_cskh"
NAME = "EVN CSKH"
VERSION = "0.2.0"
MIN_HA_VERSION = "2025.12"
PLATFORMS = (Platform.SENSOR,)

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


def interval_minutes(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not MIN_UPDATE_INTERVAL <= value <= MAX_UPDATE_INTERVAL
        or int(value) != value
    ):
        raise ValueError("The update interval must be 60 to 1440 whole minutes.")
    return int(value)
