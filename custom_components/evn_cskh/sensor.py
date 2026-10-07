from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Customer, Snapshot
from .const import customer_device_info, scope_id
from .coordinator import EvnConfigEntry, EvnCoordinator, customer_key
from .models import (
    PeriodUsage,
    daily_summary,
    latest_invoice,
    latest_reading,
    month_over_month,
    monthly_summary,
    next_outage,
    outstanding_from_active,
    trailing_average,
)

PARALLEL_UPDATES = 0

_METER_FIELDS = {
    "meter_reading": "new",
    "meter_multiplier": "multiplier",
    "meter_read_date": "period",
}
_INVOICE_FIELDS = (
    "cycle",
    "due_date",
    "energy",
    "energy_unit",
    "paid_date",
    "status_label",
)

POINT_SENSORS = (
    SensorEntityDescription(
        key="monthly_energy",
        translation_key="monthly_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="prev_month_energy",
        translation_key="prev_month_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="average_12m_energy",
        translation_key="average_12m_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="month_over_month",
        translation_key="month_over_month",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_energy",
        translation_key="daily_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="meter_reading",
        translation_key="meter_reading",
    ),
    SensorEntityDescription(
        key="meter_multiplier",
        translation_key="meter_multiplier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="meter_read_date",
        translation_key="meter_read_date",
        entity_category=EntityCategory.DIAGNOSTIC,
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
        key="latest_invoice_amount",
        translation_key="latest_invoice_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
    ),
    SensorEntityDescription(
        key="latest_invoice_status",
        translation_key="latest_invoice_status",
    ),
    SensorEntityDescription(
        key="paid_invoice_count",
        translation_key="paid_invoice_count",
        entity_category=EntityCategory.DIAGNOSTIC,
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


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(
        character for character in value[: limit * 2] if character.isprintable()
    ).strip()[:limit]


def _whole_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,4}", value.strip()):
        return int(value.strip())
    return None


def _record_period(record: dict[str, Any]) -> tuple[int, int] | None:
    year = _whole_number(record.get("NAM"))
    month = _whole_number(record.get("THANG"))
    if year is None or month is None or not 1 <= year <= 9999 or not 1 <= month <= 12:
        return None
    return year, month


def _previous_month_records(records: Any) -> list[dict[str, Any]] | None:
    if not isinstance(records, list) or not records:
        return None
    periods: list[tuple[int, int]] = []
    for record in records:
        if not isinstance(record, dict):
            return None
        period = _record_period(record)
        if period is None:
            return None
        periods.append(period)
    earlier = {period for period in periods if period < max(periods)}
    if not earlier:
        return None
    previous = max(earlier)
    return [record for record, period in zip(records, periods) if period == previous]


def _reading_records(snapshot: Snapshot, point: str) -> list[dict[str, Any]]:
    daily = snapshot.daily_readings.get(point)
    if daily:
        return daily
    monthly = snapshot.monthly_readings.get(point)
    return monthly if monthly else []


def _latest_record(rows: Any) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        return None
    selected: tuple[int, int] | None = None
    row: dict[str, Any] | None = None
    for record in rows:
        if not isinstance(record, dict):
            return None
        period = _record_period(record)
        if period is None:
            continue
        if selected is None or period > selected:
            selected, row = period, record
    return row


def _latest_invoice_pair(
    snapshot: Snapshot,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for records in (snapshot.invoices, snapshot.paid_invoices):
        row = _latest_record(records)
        if row is None:
            continue
        invoice = latest_invoice([row])
        if invoice is not None:
            return invoice, row
    return None


def _bank_names(rows: Any) -> dict[str, str]:
    names: dict[str, str] = {}
    if not isinstance(rows, list):
        return names
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _text(row.get("MA_TCHUC"), 64)
        name = _text(row.get("TEN_TCHUC"), 256)
        if code and name:
            names.setdefault(code, name)
    return names


def _number(value: Any) -> float | int | None:
    return (
        value
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else None
    )


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
        self._attr_unique_id = scope_id(*scope, point, description.key)
        self._attr_device_info = customer_device_info(scope)
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
        match self.entity_description.key:
            case "monthly_energy":
                return monthly_summary(snapshot.monthly.get(self._point, []))
            case "prev_month_energy":
                records = _previous_month_records(snapshot.monthly.get(self._point, []))
                return monthly_summary(records) if records is not None else None
            case "daily_energy":
                return daily_summary(snapshot.daily.get(self._point, []))
        return None

    def _monthly(self, snapshot: Snapshot) -> list[dict[str, Any]]:
        if self._point is None:
            return []
        records = snapshot.monthly.get(self._point, [])
        return records if isinstance(records, list) else []

    def _reading(self, snapshot: Snapshot) -> dict[str, Any] | None:
        if self._point is None:
            return None
        return latest_reading(_reading_records(snapshot, self._point))

    @property
    def native_value(self) -> StateType | datetime:
        snapshot = self._snapshot
        if snapshot is None:
            return None
        match self.entity_description.key:
            case "monthly_energy" | "prev_month_energy" | "daily_energy":
                usage = self._usage(snapshot)
                return usage.value if usage is not None else None
            case "average_12m_energy":
                return trailing_average(self._monthly(snapshot), 12)
            case "month_over_month":
                change = month_over_month(self._monthly(snapshot))
                if change is None:
                    return None
                percent = change.get("percent")
                return percent if isinstance(percent, (int, float)) else None
            case "meter_reading" | "meter_multiplier" | "meter_read_date":
                reading = self._reading(snapshot)
                if reading is None:
                    return None
                value = reading.get(_METER_FIELDS[self.entity_description.key])
                if isinstance(value, bool):
                    return None
                if isinstance(value, str):
                    return value
                return _number(value)
            case "outstanding_amount":
                return outstanding_from_active(snapshot.invoices).amount
            case "outstanding_count":
                return outstanding_from_active(snapshot.invoices).count
            case "latest_invoice_amount":
                pair = _latest_invoice_pair(snapshot)
                return _number(pair[0].get("amount")) if pair is not None else None
            case "latest_invoice_status":
                pair = _latest_invoice_pair(snapshot)
                if pair is None:
                    return None
                return _text(pair[0].get("status_label"), 128) or None
            case "paid_invoice_count":
                return len(snapshot.paid_invoices)
            case "next_outage":
                outage = next_outage(snapshot.outages)
                return outage.start if outage is not None else None
            case "fetched_at":
                return snapshot.fetched_at
        return None

    def _point_attributes(self, snapshot: Snapshot) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        key = self.entity_description.key
        if key == "month_over_month":
            change = month_over_month(self._monthly(snapshot))
            if change is not None:
                for field in ("current", "previous", "delta"):
                    value = _number(change.get(field))
                    if value is not None:
                        attributes[field] = value
        elif key in _METER_FIELDS:
            reading = self._reading(snapshot)
            if reading is not None:
                attributes["period"] = _text(reading.get("period"), 128)
                if key == "meter_reading":
                    for field in ("old", "new", "multiplier"):
                        attributes[field] = _number(reading.get(field))
                    attributes["kind"] = _text(reading.get("kind"), 32) or None
        else:
            usage = self._usage(snapshot)
            if usage is not None:
                attributes["period"] = usage.period
        return attributes

    def _invoice_attributes(self, snapshot: Snapshot) -> dict[str, Any]:
        pair = _latest_invoice_pair(snapshot)
        if pair is None:
            return {}
        invoice, row = pair
        attributes: dict[str, Any] = {}
        for field in _INVOICE_FIELDS:
            value = invoice.get(field)
            if isinstance(value, str):
                attributes[field] = _text(value, 128) or None
            elif isinstance(value, bool):
                attributes[field] = None
            else:
                attributes[field] = value if isinstance(value, (int, float)) else None
        org_code = _text(row.get("MA_TCHUC"), 64)
        if org_code:
            attributes["org_code"] = org_code
        label = _bank_names(snapshot.banks).get(org_code) or _text(
            row.get("KENH_THANH_TOAN"), 128
        )
        if label:
            attributes["payment_channel_label"] = label
        return attributes

    def _info_attributes(self, snapshot: Snapshot) -> dict[str, Any]:
        info = snapshot.info if isinstance(snapshot.info, dict) else {}
        fields = (
            ("customer_name", "tenKhang", 256),
            ("address", "diaChi", 256),
            ("phone", "dthoai", 64),
            ("contract", "maHdong", 128),
            ("region_code", "maDviCaptct", 64),
        )
        attributes: dict[str, Any] = {}
        for name, key, limit in fields:
            text = _text(info.get(key), limit)
            if text:
                attributes[name] = text
        if "region_code" not in attributes:
            region = _text(snapshot.region, 64)
            if region:
                attributes["region_code"] = region
        attributes["contracts"] = len(snapshot.contracts)
        attributes["banks"] = len(snapshot.banks)
        attributes["paid"] = len(snapshot.paid_invoices)
        return attributes

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self._snapshot
        if snapshot is None:
            return {}
        attributes: dict[str, Any] = {
            "last_update": snapshot.fetched_at.isoformat(),
        }
        key = self.entity_description.key
        if self._point is not None:
            attributes["measurement_point"] = self._point[:256]
            attributes.update(self._point_attributes(snapshot))
        elif key == "next_outage":
            outage = next_outage(snapshot.outages)
            if outage is not None:
                if outage.end is not None:
                    attributes["schedule_end"] = outage.end.isoformat()
                if outage.area:
                    attributes["area"] = outage.area
                if outage.reason:
                    attributes["reason"] = outage.reason
        elif key == "latest_invoice_amount":
            attributes.update(self._invoice_attributes(snapshot))
        elif key == "fetched_at":
            attributes.update(self._info_attributes(snapshot))
        return attributes
