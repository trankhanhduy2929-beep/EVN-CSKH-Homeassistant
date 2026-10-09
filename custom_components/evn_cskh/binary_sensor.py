from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Customer, Snapshot
from .const import PLATFORMS, customer_device_info, scope_id
from .coordinator import EvnConfigEntry, EvnCoordinator, customer_key
from .models import current_outage, next_outage, upcoming_outage

PARALLEL_UPDATES = 0
_LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

BINARY_SENSORS = (
    BinarySensorEntityDescription(
        key="outage_scheduled",
        translation_key="outage_scheduled",
        icon="mdi:calendar-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="outage_soon",
        translation_key="outage_soon",
        icon="mdi:clock-alert-outline",
    ),
    BinarySensorEntityDescription(
        key="outage_active",
        translation_key="outage_active",
        icon="mdi:power-plug-off",
    ),
)


def _now() -> datetime:
    return datetime.now(_LOCAL_TIMEZONE)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EvnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if Platform.BINARY_SENSOR not in PLATFORMS:
        return
    coordinator = entry.runtime_data
    async_add_entities(
        [
            EvnBinarySensor(coordinator, entry, snapshot.customer, description)
            for snapshot in coordinator.data.values()
            for description in BINARY_SENSORS
        ]
    )


class EvnBinarySensor(CoordinatorEntity[EvnCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EvnCoordinator,
        entry: EvnConfigEntry,
        customer: Customer,
        description: BinarySensorEntityDescription,
    ) -> None:
        key = customer_key(customer)
        super().__init__(coordinator, context=key)
        self.entity_description = description
        self._customer_key = key
        scope = (
            entry.unique_id or entry.entry_id,
            customer.management_unit,
            customer.code,
        )
        self._attr_unique_id = scope_id(*scope, None, description.key)
        self._attr_device_info = customer_device_info(scope)

    @property
    def _snapshot(self) -> Snapshot | None:
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._customer_key)

    @property
    def available(self) -> bool:
        return self._snapshot is not None

    @property
    def is_on(self) -> bool | None:
        snapshot = self._snapshot
        if snapshot is None:
            return None
        key = self.entity_description.key
        if key == "outage_soon":
            return upcoming_outage(snapshot.outages, _now(), 24) is not None
        if key == "outage_active":
            return current_outage(snapshot.outages, _now()) is not None
        return bool(next_outage(snapshot.outages))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self._snapshot
        if snapshot is None:
            return {}
        attributes: dict[str, Any] = {
            "last_update": snapshot.fetched_at.isoformat(),
        }
        key = self.entity_description.key
        if key == "outage_soon":
            outage = upcoming_outage(snapshot.outages, _now(), 24)
            if outage is not None:
                attributes["start"] = outage.start.isoformat()
                if outage.end is not None:
                    attributes["end"] = outage.end.isoformat()
                seconds = int((outage.start - _now()).total_seconds())
                attributes["seconds_until"] = max(seconds, 0)
        elif key == "outage_active":
            outage = current_outage(snapshot.outages, _now())
            if outage is not None:
                attributes["start"] = outage.start.isoformat()
                if outage.end is not None:
                    attributes["end"] = outage.end.isoformat()
                if outage.area:
                    attributes["area"] = outage.area
                if outage.reason:
                    attributes["reason"] = outage.reason
        elif key == "outage_scheduled":
            outage = next_outage(snapshot.outages)
            if outage is not None:
                attributes["schedule_start"] = outage.start.isoformat()
                if outage.end is not None:
                    attributes["schedule_end"] = outage.end.isoformat()
                if outage.area:
                    attributes["area"] = outage.area
                if outage.reason:
                    attributes["reason"] = outage.reason
            attributes["count"] = (
                len(snapshot.outages) if isinstance(snapshot.outages, list) else 0
            )
        return attributes
