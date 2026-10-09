from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
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
    customer_month_energy,
    daily_consumption_on,
    daily_summary,
    invoice_for_month,
    latest_cycle_index,
    latest_daily_index,
    latest_invoice,
    latest_reading,
    month_label,
    month_over_month,
    monthly_summary,
    next_outage,
    outage_duration_hours,
    outstanding_from_active,
    previous_months,
    trailing_average,
    vn_now,
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
_DAY_OFFSETS = {
    "consumption_today": 0,
    "consumption_yesterday": 1,
    "consumption_two_days_ago": 2,
}

POINT_SENSORS = (
    SensorEntityDescription(
        key="monthly_energy",
        translation_key="monthly_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:flash",
    ),
    SensorEntityDescription(
        key="prev_month_energy",
        translation_key="prev_month_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:flash",
    ),
    SensorEntityDescription(
        key="average_12m_energy",
        translation_key="average_12m_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
    SensorEntityDescription(
        key="month_over_month",
        translation_key="month_over_month",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-line",
    ),
    SensorEntityDescription(
        key="daily_energy",
        translation_key="daily_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:flash-outline",
    ),
    SensorEntityDescription(
        key="meter_reading",
        translation_key="meter_reading",
        icon="mdi:gauge",
    ),
    SensorEntityDescription(
        key="meter_multiplier",
        translation_key="meter_multiplier",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:multiplication",
    ),
    SensorEntityDescription(
        key="meter_read_date",
        translation_key="meter_read_date",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-check",
    ),
    SensorEntityDescription(
        key="current_provisional_index",
        translation_key="current_provisional_index",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="previous_cycle_final_index",
        translation_key="previous_cycle_final_index",
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="consumption_today",
        translation_key="consumption_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:flash",
    ),
    SensorEntityDescription(
        key="consumption_yesterday",
        translation_key="consumption_yesterday",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:flash",
    ),
    SensorEntityDescription(
        key="consumption_two_days_ago",
        translation_key="consumption_two_days_ago",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:flash",
    ),
)

CUSTOMER_SENSORS = (
    SensorEntityDescription(
        key="outstanding_amount",
        translation_key="outstanding_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
        icon="mdi:cash",
    ),
    SensorEntityDescription(
        key="outstanding_count",
        translation_key="outstanding_count",
        icon="mdi:file-document-alert",
    ),
    SensorEntityDescription(
        key="latest_invoice_amount",
        translation_key="latest_invoice_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
        icon="mdi:receipt-text",
    ),
    SensorEntityDescription(
        key="latest_invoice_status",
        translation_key="latest_invoice_status",
        icon="mdi:check-decagram",
    ),
    SensorEntityDescription(
        key="paid_invoice_count",
        translation_key="paid_invoice_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:file-document-check",
    ),
    SensorEntityDescription(
        key="next_outage",
        translation_key="next_outage",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:transmission-tower-off",
    ),
    SensorEntityDescription(
        key="next_outage_end",
        translation_key="next_outage_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-end",
    ),
    SensorEntityDescription(
        key="next_outage_duration",
        translation_key="next_outage_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
        icon="mdi:timer-outline",
    ),
    SensorEntityDescription(
        key="next_outage_area",
        translation_key="next_outage_area",
        icon="mdi:map-marker-outline",
    ),
    SensorEntityDescription(
        key="next_outage_reason",
        translation_key="next_outage_reason",
        icon="mdi:text-box-outline",
    ),
    SensorEntityDescription(
        key="outage_count",
        translation_key="outage_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="fetched_at",
        translation_key="fetched_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:update",
    ),
    SensorEntityDescription(
        key="current_period_detail",
        translation_key="current_period_detail",
        icon="mdi:calendar-month",
    ),
    SensorEntityDescription(
        key="invoice_year",
        translation_key="invoice_year",
        icon="mdi:calendar",
    ),
    SensorEntityDescription(
        key="invoice_this_period",
        translation_key="invoice_this_period",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
        icon="mdi:cash-multiple",
    ),
    SensorEntityDescription(
        key="invoice_prev_period",
        translation_key="invoice_prev_period",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
        icon="mdi:cash-multiple",
    ),
    SensorEntityDescription(
        key="invoice_prev_prev_period",
        translation_key="invoice_prev_prev_period",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="VND",
        icon="mdi:cash-multiple",
    ),
    SensorEntityDescription(
        key="consumption_this_period",
        translation_key="consumption_this_period",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:chart-bar",
    ),
    SensorEntityDescription(
        key="consumption_prev_period",
        translation_key="consumption_prev_period",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:chart-bar",
    ),
    SensorEntityDescription(
        key="consumption_prev_prev_period",
        translation_key="consumption_prev_prev_period",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:chart-bar",
    ),
    SensorEntityDescription(
        key="next_update",
        translation_key="next_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-sync",
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


def _point_rows(source: Any, point: str) -> list[dict[str, Any]]:
    if not isinstance(source, dict):
        return []
    rows = source.get(point)
    return rows if isinstance(rows, list) else []


def _customer_month_energy(snapshot: Snapshot, period: tuple[int, int]) -> float | None:
    return customer_month_energy(
        snapshot.measurement_points,
        snapshot.monthly,
        snapshot.monthly_readings,
        period[0],
        period[1],
    )


def _next_update(coordinator: EvnCoordinator) -> datetime | None:
    candidate = getattr(coordinator, "next_iteration", None)
    if (
        not isinstance(candidate, datetime)
        or candidate.tzinfo is None
        or candidate.utcoffset() is None
    ):
        return None
    return candidate.astimezone(UTC)


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
        if self.entity_description.key == "next_update":
            return (
                _next_update(self.coordinator) is not None or self._snapshot is not None
            )
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
        if self.entity_description.key == "next_update":
            return _next_update(self.coordinator)
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
            case "next_outage_end":
                outage = next_outage(snapshot.outages)
                return outage.end if outage is not None else None
            case "next_outage_duration":
                return outage_duration_hours(next_outage(snapshot.outages))
            case "next_outage_area":
                outage = next_outage(snapshot.outages)
                return (outage.area or None) if outage is not None else None
            case "next_outage_reason":
                outage = next_outage(snapshot.outages)
                return (outage.reason or None) if outage is not None else None
            case "outage_count":
                return (
                    len(snapshot.outages)
                    if isinstance(snapshot.outages, list)
                    else None
                )
            case "fetched_at":
                return snapshot.fetched_at
            case "current_provisional_index":
                return latest_daily_index(
                    _point_rows(snapshot.daily_readings, self._point or "")
                )[0]
            case "previous_cycle_final_index":
                return latest_cycle_index(
                    _point_rows(snapshot.monthly_readings, self._point or ""),
                    0,
                    as_of=vn_now(),
                )
            case (
                "consumption_today"
                | "consumption_yesterday"
                | "consumption_two_days_ago"
            ):
                days = _DAY_OFFSETS[self.entity_description.key]
                target = vn_now() - timedelta(days=days)
                return daily_consumption_on(
                    _point_rows(snapshot.daily, self._point or ""), target
                )
            case "current_period_detail":
                return month_label(vn_now()) or None
            case "invoice_year":
                today = vn_now()
                return today.year if isinstance(today, date) else None
            case (
                "invoice_this_period"
                | "invoice_prev_period"
                | "invoice_prev_prev_period"
            ):
                period = self._period()
                if period is None:
                    return None
                return invoice_for_month(
                    snapshot.invoices, snapshot.paid_invoices, period[0], period[1]
                )
            case (
                "consumption_this_period"
                | "consumption_prev_period"
                | "consumption_prev_prev_period"
            ):
                period = self._period()
                if period is None:
                    return None
                return _customer_month_energy(snapshot, period)
        return None

    def _period(self) -> tuple[int, int] | None:
        today = vn_now()
        if not isinstance(today, date):
            return None
        match self.entity_description.key:
            case "invoice_this_period" | "consumption_this_period":
                return today.year, today.month
            case _:
                periods = previous_months(today, 2)
                index = (
                    1 if self.entity_description.key.endswith("prev_prev_period") else 0
                )
                return periods[index] if len(periods) > index else None

    def _calendar_attributes(self, snapshot: Snapshot) -> dict[str, Any]:
        key = self.entity_description.key
        today = vn_now()
        if key in _DAY_OFFSETS:
            target = today - timedelta(days=_DAY_OFFSETS[key])
            return {
                "target_date": target.isoformat(),
                "period_basis": "calendar_day",
                "source": "diennangngay",
                "provisional": True,
            }
        if key == "previous_cycle_final_index":
            periods = previous_months(today, 1)
            return {
                "target_month": f"{periods[0][0]:04d}-{periods[0][1]:02d}"
                if periods
                else None,
                "as_of": today.isoformat(),
                "period_basis": "previous_completed_month_label",
                "cycle_basis": "latest_verified_end_date_or_month_cycle_order",
                "source": "chisothang",
                "provisional": False,
            }
        if key.startswith(("invoice_", "consumption_")) and key.endswith("period"):
            period = self._period()
            if period is None:
                return {}
            invoice = key.startswith("invoice_")
            if invoice:
                source: str | None = "hoadon+lichsu-hoadon"
            else:
                sources = set()
                for point in snapshot.measurement_points:
                    code = point.get("MA_DDO")
                    if not isinstance(code, str):
                        continue
                    for name, rows in (
                        ("diennangthang", _point_rows(snapshot.monthly, code)),
                        ("chisothang", _point_rows(snapshot.monthly_readings, code)),
                    ):
                        if any(
                            isinstance(row, dict) and _record_period(row) == period
                            for row in rows
                        ):
                            sources.add(name)
                            break
                source = "+".join(sorted(sources)) or None
            return {
                "target_month": f"{period[0]:04d}-{period[1]:02d}",
                "period_basis": "invoice_month_label"
                if invoice
                else "energy_month_label",
                "source": source,
                "provisional": not invoice and period == (today.year, today.month),
            }
        if key == "current_period_detail":
            return {
                "target_month": f"{today.year:04d}-{today.month:02d}",
                "period_basis": "calendar_month_label",
                "source": "vietnam_calendar",
                "provisional": False,
            }
        if key == "invoice_year":
            return {
                "target_year": today.year,
                "period_basis": "calendar_year",
                "source": "vietnam_calendar",
                "provisional": False,
            }
        return {}

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
        elif key == "current_provisional_index":
            attributes.update({"source": "chisongay", "provisional": True})
            index, stamp = latest_daily_index(
                _point_rows(snapshot.daily_readings, self._point or "")
            )
            if index is not None and stamp is not None:
                text = _text(stamp, 128)
                attributes["latest_read_at"] = text
                attributes["period"] = text.split(" ")[0]
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
        key = self.entity_description.key
        if snapshot is None:
            if key == "next_update" and _next_update(self.coordinator) is not None:
                return {"source": "coordinator_timer", "provisional": False}
            return {}
        attributes: dict[str, Any] = {
            "last_update": snapshot.fetched_at.isoformat(),
        }
        attributes.update(self._calendar_attributes(snapshot))
        if key == "next_update":
            attributes.update({"source": "coordinator_timer", "provisional": False})
        if self._point is not None:
            attributes["measurement_point"] = self._point[:256]
            attributes.update(self._point_attributes(snapshot))
        elif key == "next_outage":
            outage = next_outage(snapshot.outages)
            if outage is not None:
                attributes["start"] = outage.start.isoformat()
                if outage.end is not None:
                    attributes["end"] = outage.end.isoformat()
                if outage.area:
                    attributes["area"] = outage.area
                if outage.reason:
                    attributes["reason"] = outage.reason
                duration = outage_duration_hours(outage)
                if duration is not None:
                    attributes["duration_hours"] = duration
            attributes["count"] = (
                len(snapshot.outages) if isinstance(snapshot.outages, list) else 0
            )
        elif key == "latest_invoice_amount":
            attributes.update(self._invoice_attributes(snapshot))
        elif key == "fetched_at":
            attributes.update(self._info_attributes(snapshot))
        return attributes
