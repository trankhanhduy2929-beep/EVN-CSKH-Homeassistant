from __future__ import annotations

import asyncio
import re
import secrets
from collections import OrderedDict
from collections.abc import Coroutine
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any, TypeVar
from zoneinfo import ZoneInfo

import voluptuous as vol
from aiohttp import web
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.setup import async_setup_component

from .api import (
    Customer,
    DetailSnapshot,
    EvnAuthError,
    EvnConnectionError,
    EvnResponseError,
    Snapshot,
    _invoice_body,
)
from .const import CONF_CUSTOMERS, CONF_SELECTED_CUSTOMERS, DOMAIN, VERSION
from .coordinator import EvnConfigEntry, EvnCoordinator, customer_key
from .models import (
    PeriodUsage,
    _date,
    _integer,
    _interval,
    _number,
    _outage_time,
    _reading_stamp,
    customer_month_energy,
    daily_consumption_on,
    daily_summary,
    invoice_for_month,
    latest_reading,
    month_over_month,
    monthly_summary,
    next_outage,
    outstanding_from_active,
    previous_months,
    trailing_average,
)

_DATA_KEY = "evn_cskh_panel"
_PANEL_PATH = "evn-cskh"
_STATIC_URL = "/evn_cskh_static/evn-cskh-panel.js"
_STATIC_FILE = Path(__file__).parent / "frontend" / "evn-cskh-panel.js"
_CACHE_TTL = 300
_MIN_REFRESH = 60
_MAX_CACHE_KEYS = 8
_MAX_INVOICES = 200
_MAX_READINGS = 1000
_MAX_OUTAGES = 100
_MAX_PDF_BYTES = 16 * 1024 * 1024
_MAX_CONTRACTS = 20
_MAX_BANKS = 40
_MAX_PAID = 24
_LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
_DOCUMENTS = ("invoice", "statement", "notice")
_REGIONS = ("PA", "PB", "PC", "HN", "PE")
_ENERGY_UNITS = {"TD": "kWh", "TC": "kVArh"}
_STATUSES = {
    "CHUATT": "Chưa thanh toán",
    "DATT": "Đã thanh toán",
    "TTOANMOTPHAN": "Đã thanh toán một phần",
    "DAHT": "Đã hoàn trả",
    "CHUAHT": "Chưa hoàn trả",
    "CHOXULY": "Chờ xử lý",
}
_MESSAGES = {
    "auth": "EVN authentication is required.",
    "cannot_connect": "EVN service is unavailable.",
    "invalid_response": "EVN data or request is invalid.",
    "not_found": "EVN resource is unavailable.",
    "stale": "EVN data expired. Reload the details.",
    "unauthorized": "Administrator access is required.",
}
_DOWNLOAD_HEADERS = {
    "Cache-Control": "private, no-store",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "sandbox; default-src 'none'",
}
_IDENTIFIER_SCHEMA = vol.All(str, vol.Length(min=1, max=1025))
_T = TypeVar("_T")
type _Query = tuple[str, str, date, date]


class PanelUnavailable(HomeAssistantError):
    pass


class _PanelError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(_MESSAGES[code])


def _error_code(error: Exception) -> str:
    if isinstance(error, _PanelError):
        return error.code
    if isinstance(error, (EvnAuthError, ConfigEntryAuthFailed)):
        return "auth"
    if isinstance(error, (EvnConnectionError, TimeoutError, OSError)):
        return "cannot_connect"
    return "invalid_response"


def _safe_text(value: Any, limit: int = 512) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(char for char in value[: limit * 2] if char.isprintable()).strip()[
        :limit
    ]


def _identifier(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or value != value.strip()
        or not value.isprintable()
    ):
        raise EvnResponseError()
    return value


def _now() -> date:
    return datetime.now(_LOCAL_TIMEZONE).date()


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise EvnResponseError()
    return value.isoformat()


def _iso_date(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise vol.Invalid("Use an ISO calendar date.")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise vol.Invalid("Use an ISO calendar date.") from None
    return value


def _date_range(start: str, end: str) -> tuple[date, date]:
    try:
        first = date.fromisoformat(_iso_date(start))
        last = date.fromisoformat(_iso_date(end))
    except (ValueError, vol.Invalid):
        raise _PanelError("invalid_response") from None
    today = _now()
    if (
        first > last
        or last > today
        or (last - first).days > 366
        or first < today - timedelta(days=5 * 366)
    ):
        raise _PanelError("invalid_response")
    return first, last


def _customer_dto(snapshot: Snapshot | DetailSnapshot) -> dict[str, Any]:
    customer = snapshot.customer
    return {
        "key": customer_key(customer),
        "code": _identifier(customer.code),
        "name": _safe_text(customer.name),
        "unit": _identifier(customer.management_unit),
        "region": snapshot.region if snapshot.region in _REGIONS else "",
    }


def _points(snapshot: Snapshot) -> list[dict[str, Any]]:
    return [
        {
            "id": _identifier(row.get("MA_DDO")),
            "address": _safe_text(row.get("DIA_CHI")),
            "contract": _safe_text(row.get("MA_HDONG"), 128),
            "valid_from": _safe_text(row.get("NGAY_HLUC"), 128),
        }
        for row in snapshot.measurement_points
    ]


def _usage(value: PeriodUsage | None) -> dict[str, Any] | None:
    return {"period": value.period, "kwh": _number(value.value)} if value else None


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() in {"1", "true"}


def _alert_count(value: Any) -> int | None:
    if isinstance(value, list):
        return len(value)
    return None if value is None else 0


def _info_dto(source: Any) -> dict[str, Any]:
    info = source if isinstance(source, dict) else {}
    return {
        "name": _safe_text(info.get("tenKhang")),
        "address": _safe_text(info.get("diaChi")),
        "phone": _safe_text(info.get("dthoai")),
        "customer_type": _safe_text(info.get("loaiKhang")),
        "subject_type": _safe_text(info.get("loaiChuthe")),
        "region_code": _safe_text(info.get("maDviCaptct"), 64),
        "province": _safe_text(info.get("maTinh"), 64),
        "commune": _safe_text(info.get("maXa"), 64),
        "contract": _safe_text(info.get("maHdong"), 128),
        "pay_reference": _safe_text(info.get("thanhtoanho"), 256),
        "alert_count": _alert_count(info.get("powerAlert")),
        "default_contract": _flag(info.get("hdMacdinh")),
        "pay_on_behalf": _safe_text(info.get("maKhang"), 128),
    }


def _contracts(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        number = _safe_text(row.get("MA_HDONG"), 128)
        if not number:
            continue
        result.append(
            {
                "number": number,
                "address": _safe_text(row.get("DUONG_PHO"), 256),
                "unit": _safe_text(row.get("MA_DVIQLY"), 64),
            }
        )
        if len(result) == _MAX_CONTRACTS:
            break
    return result


def _banks(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _safe_text(row.get("MA_TCHUC"), 64)
        if not code:
            continue
        result.append({"code": code, "name": _safe_text(row.get("TEN_TCHUC"), 256)})
        if len(result) == _MAX_BANKS:
            break
    return result


def _change(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {key: _number(item) for key, item in value.items()}


def _latest_reading_dto(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "period": _safe_text(value.get("period"), 128),
        "old": _number(value.get("old")),
        "new": _number(value.get("new")),
        "multiplier": _number(value.get("multiplier")),
        "kwh": _number(value.get("kwh")),
        "kind": _safe_text(value.get("kind"), 64),
    }


def _usage_rows(snapshot: Snapshot) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for point in _points(snapshot):
        point_id = point["id"]
        monthly = snapshot.monthly.get(point_id, [])
        reading = _latest_reading_dto(
            latest_reading(snapshot.daily_readings.get(point_id, []))
            or latest_reading(snapshot.monthly_readings.get(point_id, []))
        )
        result.append(
            {
                "point_id": point_id,
                "monthly": _usage(monthly_summary(monthly)),
                "daily": _usage(daily_summary(snapshot.daily.get(point_id, []))),
                "mom": _change(month_over_month(monthly)),
                "average_12m": _number(trailing_average(monthly, 12)),
                "reading": reading,
            }
        )
    return result


def _invoice_rows(
    rows: list[dict[str, Any]], banks: dict[str, str], limit: int
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        if len(result) >= limit:
            break
        if not isinstance(row, dict):
            continue
        try:
            result.append(_invoice_dto(row, banks))
        except EvnResponseError:
            continue
    return result


def _outage_dto(row: dict[str, Any]) -> dict[str, Any]:
    start = _outage_time(row.get("TGIAN_BDAU"))
    end = _outage_time(row.get("TGIAN_KTHUC"))
    if start is not None and end is not None and end < start:
        end = None
    return {
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
        "area": _safe_text(row.get("KHUVUCMATDIEN")),
        "reason": _safe_text(row.get("LY_DO")),
    }


def _comparisons(snapshot: Snapshot, as_of: date) -> dict[str, Any]:
    days = [as_of - timedelta(days=offset) for offset in (2, 1, 0)]
    current = as_of.year, as_of.month
    months = [*reversed(previous_months(as_of, 2)), current]
    return {
        "as_of": as_of.isoformat(),
        "points": [
            {
                "point_id": point["id"],
                "daily": [
                    {
                        "period": day.isoformat(),
                        "kwh": _number(
                            daily_consumption_on(
                                snapshot.daily.get(point["id"], []), day
                            )
                        ),
                        "provisional": True,
                    }
                    for day in days
                ],
            }
            for point in _points(snapshot)
        ],
        "monthly": [
            {
                "period": f"{year:04d}-{month:02d}",
                "kwh": _number(
                    customer_month_energy(
                        snapshot.measurement_points,
                        snapshot.monthly,
                        snapshot.monthly_readings,
                        year,
                        month,
                    )
                ),
                "vnd": _number(
                    invoice_for_month(
                        snapshot.invoices, snapshot.paid_invoices, year, month
                    )
                ),
                "provisional": (year, month) == current,
            }
            for year, month in months
        ],
    }


def _overview(snapshot: Snapshot, available: bool) -> dict[str, Any]:
    as_of = _now()
    result: dict[str, Any] = {
        "customer": _customer_dto(snapshot),
        "available": available,
        "fetched_at": _timestamp(snapshot.fetched_at),
        "info": _info_dto(None),
        "contracts": [],
        "banks": [],
        "usage": [],
        "outstanding": {"amount": None, "count": None},
        "invoices": [],
        "paid_count": 0,
        "paid_recent": [],
        "outages": [],
        "outage_count": len(snapshot.outages),
        "next_outage": None,
        "comparisons": {"as_of": as_of.isoformat(), "points": [], "monthly": []},
    }
    if not available:
        return result
    result["comparisons"] = _comparisons(snapshot, as_of)
    result["info"] = _info_dto(snapshot.info)
    result["contracts"] = _contracts(snapshot.contracts)
    result["banks"] = _banks(snapshot.banks)
    result["usage"] = _usage_rows(snapshot)
    outstanding = outstanding_from_active(snapshot.invoices)
    result["outstanding"] = {
        "amount": _number(outstanding.amount),
        "count": outstanding.count,
    }
    names = {row["code"]: row["name"] for row in result["banks"]}
    result["invoices"] = _invoice_rows(snapshot.invoices, names, _MAX_INVOICES)
    result["paid_count"] = len(snapshot.paid_invoices)
    result["paid_recent"] = _invoice_rows(snapshot.paid_invoices, names, _MAX_PAID)
    outages = snapshot.outages[:_MAX_OUTAGES]
    result["outages"] = [_outage_dto(row) for row in outages]
    if upcoming := next_outage(outages):
        result["next_outage"] = {
            "start": upcoming.start.isoformat(),
            "end": upcoming.end.isoformat() if upcoming.end else None,
            "area": _safe_text(upcoming.area),
            "reason": _safe_text(upcoming.reason),
        }
    return result


def _month(row: dict[str, Any]) -> tuple[int, int]:
    year, month = _integer(row.get("NAM")), _integer(row.get("THANG"))
    if year is None or month is None or not (1 <= year <= 9999 and 1 <= month <= 12):
        raise EvnResponseError()
    return year, month


def _monthly(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault(_month(row), []).append(row)
    return [
        {
            "period": f"{year:04d}-{month:02d}",
            "kwh": summary.value if (summary := monthly_summary(rows)) else None,
        }
        for (year, month), rows in sorted(groups.items())
    ]


def _daily(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[date, date], list[dict[str, Any]]] = {}
    for row in records:
        interval = _interval(row)
        if interval is None:
            raise EvnResponseError()
        groups.setdefault(interval[:2], []).append(row)
    result = []
    for rows in (rows for _, rows in sorted(groups.items())):
        interval = _interval(rows[0])
        assert interval is not None
        summary = daily_summary(rows)
        result.append(
            {"period": interval[2], "kwh": summary.value if summary else None}
        )
    return result


def _reading_time(
    row: dict[str, Any], kind: str
) -> tuple[str | None, str | None, str | None]:
    display = row.get("NGAY_CKY" if kind == "monthly" else "THOI_DIEM")
    if isinstance(display, str) and ":" in display and display == display.strip():
        source: dict[str, Any] = {"THOI_DIEM": display}
        if kind == "daily" and re.fullmatch(
            r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", display
        ):
            source["NGAY"] = row.get("NGAY")
        parsed = _reading_stamp(source)
        if parsed is not None:
            stamp = parsed[0]
            return stamp.isoformat(), stamp.date().isoformat(), "time"
    day = _date(row.get("NGAY_CKY" if kind == "monthly" else "NGAY"))
    if day is None and kind == "daily":
        day = _date(display)
    return None, day.isoformat() if day is not None else None, "day" if day else None


def _reading(row: dict[str, Any], kind: str) -> dict[str, Any]:
    timestamp, reading_date, resolution = _reading_time(row, kind)
    period = _safe_text(
        row.get("NGAY_HTHI") or row.get("NGAY") or row.get("THOI_DIEM"), 128
    )
    if kind == "monthly":
        try:
            year, month = _month(row)
            period = f"{year:04d}-{month:02d}"
        except EvnResponseError:
            pass
    meter = row.get("SO_CTO")
    if type(meter) is int and 0 <= meter < 10**128:
        meter = str(meter)
    return {
        "period": period,
        "timestamp": timestamp,
        "reading_date": reading_date,
        "resolution": resolution,
        "meter": _safe_text(meter, 128),
        "register": _safe_text(row.get("BCS"), 64),
        "old": _number(row.get("CHISO_CU")),
        "new": _number(row.get("CHISO_MOI")),
        "multiplier": _number(row.get("HSN")),
        "kwh": _number(row.get("DIEN_TTHU")),
        "kind": kind,
    }


def _due_date(row: dict[str, Any]) -> str | None:
    value = row.get("HAN_TTOAN")
    if value is None or value == "":
        value = row.get("TT")
    return _safe_text(value, 128) or None


def _payable_amount(row: dict[str, Any]) -> float | None:
    status = row.get("TTRANG_TTOAN")
    if status == "DATT":
        return 0.0
    if status == "TTOANMOTPHAN":
        kind = row.get("LOAI_PSINH")
        if (
            not isinstance(kind, str)
            or not kind.strip()
            or kind != kind.strip()
            or kind == "TH"
        ):
            return None
    elif status != "CHUATT":
        return None
    amount = _number(row.get("TONG_NO"))
    return abs(amount) if amount is not None else None


def _invoice_dto(
    row: dict[str, Any], banks: dict[str, str] | None = None
) -> dict[str, Any]:
    year, month = _month(row)
    status = _safe_text(row.get("TTRANG_TTOAN"), 32).upper()
    if status not in _STATUSES:
        status = "UNKNOWN"
    label = _STATUSES.get(status, "Không xác định")
    if status == "TTOANMOTPHAN" and row.get("LOAI_PSINH") == "TH":
        label = "Đã hoàn trả một phần"
    cycle = _integer(row.get("KY"))
    kind = row.get("LOAI_HDON")
    energy_unit = _ENERGY_UNITS.get(kind, "") if isinstance(kind, str) else ""
    directory = banks or {}
    org_code = _safe_text(row.get("MA_TCHUC"), 64)
    channel = _safe_text(row.get("KENH_THANH_TOAN"), 128)
    documents = list(_DOCUMENTS)
    try:
        _invoice_body(row)
    except EvnResponseError:
        documents = []
    return {
        "key": secrets.token_urlsafe(24),
        "period": f"{month:02d}/{year:04d}",
        "cycle": cycle if cycle is not None and 1 <= cycle <= 1000 else None,
        "amount": _number(row.get("TONG_TIEN")),
        "tax": _number(row.get("TIEN_GTGT")),
        "outstanding": _number(row.get("TONG_NO")),
        "payable_amount": _payable_amount(row),
        "status": status,
        "status_label": label,
        "paid_date": _safe_text(row.get("NGAY_TTOAN"), 128),
        "due_date": _due_date(row),
        "org_code": org_code,
        "payment_channel_label": directory.get(org_code) or channel,
        "energy": _number(row.get("DIEN_TTHU")),
        "energy_unit": energy_unit,
        "documents": documents,
    }


@dataclass(repr=False)
class _CachedDetails:
    dto: dict[str, Any]
    invoices: dict[str, dict[str, Any]]
    customer: Customer
    generation: int
    expires: float


@dataclass(repr=False)
class _Entry:
    entry: EvnConfigEntry
    coordinator: EvnCoordinator
    generation: int
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    cache: OrderedDict[_Query, _CachedDetails] = field(default_factory=OrderedDict)
    jobs: set[asyncio.Task[Any]] = field(default_factory=set)
    last_refresh: float = float("-inf")
    last_details: float = float("-inf")

    def invalidate(self) -> None:
        self.generation += 1
        self.cache.clear()
        for job in self.jobs:
            job.cancel()


class _PanelManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lock = asyncio.Lock()
        self.entries: dict[str, _Entry] = {}
        self.generation = 0
        self.static_registered = False
        self.view_registered = False
        self.panel_custom_ready = False
        self.commands_registered: set[str] = set()
        self.panel_registered = False

    async def setup(self) -> None:
        async with self.lock:
            if "frontend" not in self.hass.config.components:
                raise PanelUnavailable("The Home Assistant frontend is not loaded.")
            if not self.panel_custom_ready:
                for component in ("http", "websocket_api", "panel_custom"):
                    if not await async_setup_component(self.hass, component, {}):
                        raise PanelUnavailable(
                            f"The Home Assistant {component} component is unavailable."
                        )
                self.panel_custom_ready = True
            if (
                not self.static_registered or not self.view_registered
            ) and self.hass.http.app.router.frozen:
                raise HomeAssistantError("EVN panel HTTP routes are unavailable.")
            if not self.static_registered:
                if not await self.hass.async_add_executor_job(_STATIC_FILE.is_file):
                    raise HomeAssistantError("EVN panel module is unavailable.")
                await self.hass.http.async_register_static_paths(
                    [
                        StaticPathConfig(
                            _STATIC_URL, str(_STATIC_FILE), cache_headers=False
                        )
                    ]
                )
                self.static_registered = True
            if not self.view_registered:
                self.hass.http.register_view(_InvoiceView(self))
                self.view_registered = True
            for command, handler in (
                ("list_entries", _ws_list_entries),
                ("overview", _ws_overview),
                ("details", _ws_details),
            ):
                if command not in self.commands_registered:
                    websocket_api.async_register_command(self.hass, handler)
                    self.commands_registered.add(command)

    async def attach(self, entry: EvnConfigEntry) -> None:
        await self.setup()
        async with self.lock:
            previous = self.entries.get(entry.entry_id)
            if (
                previous is not None
                and previous.entry is entry
                and previous.coordinator is entry.runtime_data
            ):
                return
            if not self.panel_registered:
                await panel_custom.async_register_panel(
                    self.hass,
                    frontend_url_path=_PANEL_PATH,
                    webcomponent_name="evn-cskh-panel",
                    sidebar_title="EVN CSKH",
                    sidebar_icon="mdi:transmission-tower",
                    module_url=f"{_STATIC_URL}?v={VERSION}",
                    require_admin=True,
                )
                self.panel_registered = True
            if previous is not None:
                previous.invalidate()
            self.generation += 1
            self.entries[entry.entry_id] = _Entry(
                entry, entry.runtime_data, self.generation
            )

    async def detach(self, entry_id: str) -> None:
        async with self.lock:
            if state := self.entries.pop(entry_id, None):
                state.invalidate()
            if not self.entries and self.panel_registered:
                frontend.async_remove_panel(self.hass, _PANEL_PATH)
                self.panel_registered = False

    def check(self, state: _Entry, generation: int) -> None:
        if (
            self.entries.get(state.entry.entry_id) is not state
            or state.generation != generation
            or state.entry.runtime_data is not state.coordinator
        ):
            raise _PanelError("stale")

    def ready(self, state: _Entry) -> None:
        if (
            state.entry.domain != DOMAIN
            or state.entry.state is not ConfigEntryState.LOADED
        ):
            raise _PanelError("not_found")

    def entry(self, entry_id: str) -> _Entry:
        state = self.entries.get(entry_id)
        if state is None:
            raise _PanelError("not_found")
        self.check(state, state.generation)
        self.ready(state)
        return state

    def snapshots(self, state: _Entry) -> dict[str, Snapshot]:
        self.check(state, state.generation)
        inventory = state.entry.data.get(CONF_CUSTOMERS, [])
        allowed = {
            f"{row['management_unit']}:{row['code']}"
            for row in inventory
            if isinstance(row, dict)
            and isinstance(row.get("management_unit"), str)
            and isinstance(row.get("code"), str)
        }
        selected = state.entry.options.get(CONF_SELECTED_CUSTOMERS, [])
        return {
            key: snapshot
            for key, snapshot in (state.coordinator.data or {}).items()
            if isinstance(snapshot, Snapshot)
            and key == customer_key(snapshot.customer)
            and key in selected
            and key in state.coordinator.selected_customers
            and key in allowed
        }

    def snapshot(self, state: _Entry, key: str, point: str | None = None) -> Snapshot:
        snapshot = self.snapshots(state).get(key)
        if snapshot is None or (
            point is not None and point not in {row["id"] for row in _points(snapshot)}
        ):
            raise _PanelError("not_found")
        return snapshot

    async def work(self, state: _Entry, awaitable: Coroutine[Any, Any, _T]) -> _T:
        generation = state.generation
        task = asyncio.create_task(awaitable, name="evn_cskh_panel_request")
        state.jobs.add(task)
        try:
            result = await task
        except (Exception, asyncio.CancelledError):
            self.check(state, generation)
            raise
        finally:
            state.jobs.discard(task)
        self.check(state, generation)
        return result

    def list_entries(self) -> dict[str, Any]:
        entries = []
        for state in self.entries.values():
            try:
                self.ready(state)
            except _PanelError:
                continue
            entries.append(
                {
                    "entry_id": state.entry.entry_id,
                    "title": _safe_text(state.entry.title),
                    "customers": [
                        _customer_dto(snapshot)
                        | {
                            "points": _points(snapshot),
                            "available": bool(state.coordinator.last_update_success),
                        }
                        for snapshot in self.snapshots(state).values()
                    ],
                }
            )
        return {"entries": entries}

    async def overview(self, state: _Entry, key: str, refresh: bool) -> dict[str, Any]:
        generation = state.generation
        self.snapshot(state, key)
        if refresh:
            async with state.lock:
                self.check(state, generation)
                self.snapshot(state, key)
                if monotonic() - state.last_refresh >= _MIN_REFRESH:
                    state.last_refresh = monotonic()
                    await self.work(state, state.coordinator.async_request_refresh())
        self.check(state, generation)
        return _overview(
            self.snapshot(state, key), bool(state.coordinator.last_update_success)
        )

    def prune(self, state: _Entry) -> None:
        now = monotonic()
        for query, cached in list(state.cache.items()):
            if cached.expires <= now or cached.generation != state.generation:
                del state.cache[query]

    async def details(
        self, state: _Entry, key: str, point: str, start: str, end: str, force: bool
    ) -> dict[str, Any]:
        first, last = _date_range(start, end)
        generation = state.generation
        self.snapshot(state, key, point)
        query = (key, point, first, last)
        async with state.lock:
            self.check(state, generation)
            snapshot = self.snapshot(state, key, point)
            self.prune(state)
            cached = state.cache.get(query)
            if cached is not None and (
                not force or monotonic() - state.last_details < _MIN_REFRESH
            ):
                state.cache.move_to_end(query)
                return deepcopy(cached.dto)
            for old_query in list(state.cache):
                if old_query[0] == key:
                    del state.cache[old_query]
            state.last_details = monotonic()
            details = await self.work(
                state,
                state.coordinator.client.details(snapshot.customer, point, first, last),
            )
            current = self.snapshot(state, key, point)
            if (
                details.customer != current.customer
                or details.point != point
                or details.start != first
                or details.end != last
                or len(details.invoices) > _MAX_INVOICES
            ):
                raise EvnResponseError()
            invoices = [_invoice_dto(row) for row in details.invoices]
            readings = [_reading(row, "monthly") for row in details.monthly_readings]
            readings.extend(_reading(row, "daily") for row in details.daily_readings)
            if len(readings) > _MAX_READINGS:
                raise EvnResponseError()
            dto = {
                "customer": _customer_dto(details),
                "point_id": point,
                "start": first.isoformat(),
                "end": last.isoformat(),
                "daily_window": {
                    "start": details.daily_start.isoformat()
                    if details.daily_start is not None
                    else None,
                    "end": details.daily_end.isoformat()
                    if details.daily_end is not None
                    else None,
                },
                "fetched_at": _timestamp(details.fetched_at),
                "monthly": _monthly(details.monthly),
                "daily": _daily(details.daily),
                "readings": readings,
                "invoices": invoices,
            }
            state.cache[query] = _CachedDetails(
                dto,
                {
                    invoice["key"]: deepcopy(row)
                    for invoice, row in zip(invoices, details.invoices, strict=True)
                    if invoice["documents"]
                },
                current.customer,
                generation,
                monotonic() + _CACHE_TTL,
            )
            while len(state.cache) > _MAX_CACHE_KEYS:
                state.cache.popitem(last=False)
            return deepcopy(dto)

    def invoice(self, state: _Entry, key: str) -> tuple[_CachedDetails, dict[str, Any]]:
        self.prune(state)
        for query, cached in state.cache.items():
            if key in cached.invoices:
                snapshot = self.snapshot(state, query[0], query[1])
                if snapshot.customer != cached.customer:
                    raise _PanelError("stale")
                return cached, cached.invoices[key]
        raise _PanelError("stale")

    async def pdf(self, state: _Entry, key: str, kind: str) -> tuple[bytes, str]:
        generation = state.generation
        async with state.lock:
            self.check(state, generation)
            cached, row = self.invoice(state, key)
            data = await self.work(
                state, state.coordinator.client.invoice_pdf(cached.customer, row, kind)
            )
            if self.invoice(state, key)[0] is not cached:
                raise _PanelError("stale")
            if (
                not isinstance(data, bytes)
                or len(data) > _MAX_PDF_BYTES
                or re.match(rb"%PDF-[0-9]\.[0-9](?:\r\n|\r|\n)", data) is None
                or re.search(rb"(?:\r\n|\r|\n)%%EOF[ \t\r\n\f]*\Z", data[-1024:])
                is None
            ):
                raise EvnResponseError()
            year, month = _month(row)
            return data, f"evn-{kind}-{year:04d}-{month:02d}.pdf"


def _manager(hass: HomeAssistant) -> _PanelManager:
    manager = hass.data.get(_DATA_KEY)
    if manager is None:
        manager = _PanelManager(hass)
        hass.data[_DATA_KEY] = manager
    return manager


async def async_setup_panel(hass: HomeAssistant) -> None:
    await _manager(hass).setup()


async def async_attach_entry(hass: HomeAssistant, entry: EvnConfigEntry) -> None:
    await _manager(hass).attach(entry)


async def async_detach_entry(hass: HomeAssistant, entry_id: str) -> None:
    if manager := hass.data.get(_DATA_KEY):
        await manager.detach(entry_id)


def _admin(user: Any) -> bool:
    return bool(user is not None and user.is_admin and getattr(user, "is_active", True))


async def _ws_request(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    operation: str,
) -> None:
    state = None
    manager = _manager(hass)
    try:
        if not _admin(connection.user):
            raise _PanelError("unauthorized")
        if operation == "list_entries":
            if set(msg) - {"id", "type"}:
                raise _PanelError("invalid_response")
            result = manager.list_entries()
        else:
            state = manager.entry(msg["entry_id"])
            generation = state.generation
            if operation == "overview":
                result = await manager.overview(
                    state, msg["customer_key"], msg["refresh"]
                )
            else:
                result = await manager.details(
                    state,
                    msg["customer_key"],
                    msg["point_id"],
                    msg["start"],
                    msg["end"],
                    msg["force"],
                )
            manager.check(state, generation)
        if not _admin(connection.user):
            raise _PanelError("unauthorized")
    except Exception as error:  # noqa: BLE001
        code = _error_code(error)
        connection.send_error(msg["id"], code, _MESSAGES[code])
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "evn_cskh/list_entries"})
@websocket_api.require_admin
@websocket_api.async_response
async def _ws_list_entries(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    await _ws_request(hass, connection, msg, "list_entries")


@websocket_api.websocket_command(
    {
        "type": "evn_cskh/overview",
        vol.Required("entry_id"): _IDENTIFIER_SCHEMA,
        vol.Required("customer_key"): _IDENTIFIER_SCHEMA,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def _ws_overview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    await _ws_request(hass, connection, msg, "overview")


@websocket_api.websocket_command(
    {
        "type": "evn_cskh/details",
        vol.Required("entry_id"): _IDENTIFIER_SCHEMA,
        vol.Required("customer_key"): _IDENTIFIER_SCHEMA,
        vol.Required("point_id"): _IDENTIFIER_SCHEMA,
        vol.Required("start"): _iso_date,
        vol.Required("end"): _iso_date,
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def _ws_details(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    await _ws_request(hass, connection, msg, "details")


class _InvoiceView(HomeAssistantView):
    url = "/api/evn_cskh/invoice/{entry_id}/{invoice_key}/{kind}"
    name = "api:evn_cskh:invoice"
    requires_auth = True

    def __init__(self, manager: _PanelManager) -> None:
        self.manager = manager

    async def get(
        self, request: web.Request, entry_id: str, invoice_key: str, kind: str
    ) -> web.Response:
        try:
            authorization = request.headers.get("Authorization", "")
            if (
                "?" in request.raw_path
                or not authorization.startswith("Bearer ")
                or not authorization[7:].strip()
                or not _admin(request.get("hass_user"))
            ):
                raise _PanelError("unauthorized")
            if kind not in _DOCUMENTS or not re.fullmatch(
                r"[A-Za-z0-9_-]{32}", invoice_key
            ):
                raise _PanelError("not_found")
            state = self.manager.entry(entry_id)
            generation = state.generation
            data, filename = await self.manager.pdf(state, invoice_key, kind)
            self.manager.check(state, generation)
            if not _admin(request.get("hass_user")):
                raise _PanelError("unauthorized")
        except Exception as error:  # noqa: BLE001
            code = _error_code(error)
            status = {
                "unauthorized": 403,
                "auth": 403,
                "not_found": 404,
                "stale": 410,
                "cannot_connect": 503,
            }.get(code, 502)
            return web.json_response(
                {"error": code, "message": _MESSAGES[code]},
                status=status,
                headers=_DOWNLOAD_HEADERS,
            )
        return web.Response(
            body=data,
            content_type="application/pdf",
            headers=_DOWNLOAD_HEADERS
            | {"Content-Disposition": f'attachment; filename="{filename}"'},
        )
