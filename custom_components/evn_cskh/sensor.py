from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Customer, Snapshot
from .const import DOMAIN, NAME
from .coordinator import EvnConfigEntry, EvnCoordinator, customer_key
from .models import (
    PeriodUsage,
    daily_summary,
    invoice_summary,
    monthly_summary,
    next_outage,
)

PARALLEL_UPDATES = 0

POINT_SENSORS = (
    SensorEntityDescription(
        key="monthly_energy",
        translation_key="monthly_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="daily_energy",
        translation_key="daily_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
)

CUSTOMER_SENSORS = (
    SensorEntityDescription(
        key="outstanding_amount",
        translation_key="outstanding_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
    ),
    SensorEntityDescription(
        key="outstanding_count",
        translation_key="outstanding_count",
    ),
    SensorEntityDescription(
        key="next_outage",
        translation_key="next_outage",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="fetched_at",
        translation_key="fetched_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EvnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[EvnSensor] = []
    for snapshot in coordinator.data.values():
        entities.extend(
            EvnSensor(coordinator, entry, snapshot.customer, description)
            for description in CUSTOMER_SENSORS
        )
        for row in snapshot.measurement_points:
            entities.extend(
                EvnSensor(
                    coordinator,
                    entry,
                    snapshot.customer,
                    description,
                    point=row["MA_DDO"],
                )
                for description in POINT_SENSORS
            )
    async_add_entities(entities)


def _scope_id(*scope: str | None) -> str:
    return hashlib.sha256(
        json.dumps(scope, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


class EvnSensor(CoordinatorEntity[EvnCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EvnCoordinator,
        entry: EvnConfigEntry,
        customer: Customer,
        description: SensorEntityDescription,
        *,
        point: str | None = None,
    ) -> None:
        key = customer_key(customer)
        super().__init__(coordinator, context=key)
        self.entity_description = description
        self._customer_key = key
        self._point = point
        scope = (
            entry.unique_id or entry.entry_id,
            customer.management_unit,
            customer.code,
        )
        self._attr_unique_id = _scope_id(*scope, point, description.key)
        device_id = _scope_id(*scope)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"{NAME} {device_id[:8]}",
            manufacturer="EVN",
            model="Customer account",
            entry_type=DeviceEntryType.SERVICE,
        )
        if point is not None:
            self._attr_translation_placeholders = {"measurement_point": point[:256]}

    @property
    def _snapshot(self) -> Snapshot | None:
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return None
        snapshot = self.coordinator.data.get(self._customer_key)
        if (
            snapshot is not None
            and self._point is not None
            and not any(
                row.get("MA_DDO") == self._point for row in snapshot.measurement_points
            )
        ):
            return None
        return snapshot

    @property
    def available(self) -> bool:
        return self._snapshot is not None

    def _usage(self, snapshot: Snapshot) -> PeriodUsage | None:
        if self._point is None:
            return None
        if self.entity_description.key == "monthly_energy":
            return monthly_summary(snapshot.monthly.get(self._point, []))
        return daily_summary(snapshot.daily.get(self._point, []))

    @property
    def native_value(self) -> float | int | datetime | None:
        snapshot = self._snapshot
        if snapshot is None:
            return None
        match self.entity_description.key:
            case "monthly_energy" | "daily_energy":
                usage = self._usage(snapshot)
                return usage.value if usage is not None else None
            case "outstanding_amount":
                return invoice_summary(snapshot.invoices).amount
            case "outstanding_count":
                return invoice_summary(snapshot.invoices).count
            case "next_outage":
                outage = next_outage(snapshot.outages)
                return outage.start if outage is not None else None
            case "fetched_at":
                return snapshot.fetched_at
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self._snapshot
        if snapshot is None:
            return {}
        attributes: dict[str, Any] = {
            "last_update": snapshot.fetched_at.isoformat(),
        }
        if self._point is not None:
            attributes["measurement_point"] = self._point[:256]
            usage = self._usage(snapshot)
            if usage is not None:
                attributes["period"] = usage.period
        elif self.entity_description.key == "next_outage":
            outage = next_outage(snapshot.outages)
            if outage is not None:
                if outage.end is not None:
                    attributes["schedule_end"] = outage.end.isoformat()
                if outage.area:
                    attributes["area"] = outage.area
                if outage.reason:
                    attributes["reason"] = outage.reason
        return attributes
