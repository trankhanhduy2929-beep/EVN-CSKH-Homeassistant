import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from math import fsum, isfinite
from numbers import Real
from typing import Any
from zoneinfo import ZoneInfo

_LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
_DECIMAL_PATTERN = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")
_DATE_PATTERN = r"[0-9]{2}/[0-9]{2}/[0-9]{4}"
_INTERVAL_PATTERN = re.compile(rf"({_DATE_PATTERN})(?:\s*-\s*({_DATE_PATTERN}))?")
_INVOICE_STATUSES = {"CHUATT", "TTOANMOTPHAN", "DATT", "DAHT", "CHUAHT", "CHOXULY"}
_TARIFF_REGISTERS = {"BT", "CD", "TD"}


@dataclass(frozen=True, slots=True)
class PeriodUsage:
    value: float
    period: str


@dataclass(frozen=True, slots=True)
class InvoiceSummary:
    amount: float | None
    count: int | None
    notes: tuple[str, ...] = (
        (
            "App display sums abs(TONG_NO) for CHUATT or non-TH TTOANMOTPHAN; "
            "this is not a signed net balance or proof of payment. "
            "Missing invoices do not establish that they were paid."
        ),
    )


@dataclass(frozen=True, slots=True)
class Outage:
    start: datetime
    end: datetime | None
    area: str
    reason: str


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not _DECIMAL_PATTERN.fullmatch(value):
            return None
    elif not isinstance(value, (Real, Decimal)):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if isfinite(result) else None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None and number.is_integer() else None


def _total(values: Iterable[float]) -> float | None:
    try:
        result = fsum(values)
    except (OverflowError, ValueError):
        return None
    return result if isfinite(result) else None


def _valid_id(value: Any) -> bool:
    return type(value) is int or (
        isinstance(value, str) and bool(value) and value == value.strip()
    )


def _identical(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _identical(value, right[key]) for key, value in left.items()
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _identical(a, b) for a, b in zip(left, right)
        )
    try:
        return bool(left == right)
    except (ArithmeticError, TypeError, ValueError):
        return False


def _remember(
    seen: dict[tuple[Any, ...], dict[str, Any]],
    key: tuple[Any, ...],
    record: dict[str, Any],
) -> bool:
    if key in seen:
        try:
            return _identical(seen[key], record)
        except RecursionError:
            return False
    seen[key] = record
    return True


def monthly_summary(records: list[dict[str, Any]]) -> PeriodUsage | None:
    if not isinstance(records, list) or not records:
        return None
    latest: tuple[int, int] | None = None
    selected: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            return None
        year = _integer(record.get("NAM"))
        month = _integer(record.get("THANG"))
        if (
            year is None
            or month is None
            or not (1 <= year <= 9999 and 1 <= month <= 12)
        ):
            return None
        period = year, month
        if latest is None or period > latest:
            latest = period
            selected = [record]
        elif period == latest:
            selected.append(record)
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in selected:
        meter = record.get("SO_CTO")
        if meter is not None and not _valid_id(meter):
            return None
        cycle = None
        for field in ("KY", "SO_KY"):
            if record.get(field) is not None:
                number = _integer(record[field])
                if number is None or number < 1:
                    return None
                if field == "KY":
                    cycle = number
        if not _remember(seen, (meter, cycle), record):
            return None
    meters = {key[0] for key in seen}
    if None in meters and len(meters) > 1:
        return None
    for meter in meters:
        cycles = {key[1] for key in seen if key[0] == meter}
        if None in cycles and len(cycles) > 1:
            return None
    values = []
    for record in seen.values():
        value = _number(record.get("DIEN_TTHU"))
        if value is None:
            return None
        values.append(value)
    total = _total(values)
    if total is None or latest is None:
        return None
    return PeriodUsage(total, f"{latest[0]:04d}-{latest[1]:02d}")


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(_DATE_PATTERN, value):
        return None
    try:
        day, month, year = (int(part) for part in value.split("/"))
        return date(year, month, day)
    except ValueError:
        return None


def _interval(record: dict[str, Any]) -> tuple[date, date, str] | None:
    display = record.get("NGAY_HTHI")
    if display is None or display == "":
        display = record.get("NGAY")
    if not isinstance(display, str) or len(display) > 128:
        return None
    display = display.strip()
    match = _INTERVAL_PATTERN.fullmatch(display)
    if match is None:
        return None
    start = _date(match[1])
    end = _date(match[2]) if match[2] else start
    if start is None or end is None or start > end:
        return None
    return start, end, display


def daily_summary(records: list[dict[str, Any]]) -> PeriodUsage | None:
    if not isinstance(records, list) or not records:
        return None
    dated: list[tuple[date, date, str, dict[str, Any]]] = []
    for record in records:
        if not isinstance(record, dict):
            return None
        interval = _interval(record)
        if interval is None:
            return None
        dated.append((*interval, record))
    latest = max(item[1] for item in dated)
    selected = [item for item in dated if item[1] == latest]
    if len({(item[0], item[1]) for item in selected}) != 1:
        return None
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for _, _, _, record in selected:
        meter = record.get("SO_CTO")
        register = record.get("BCS")
        if meter is not None and not _valid_id(meter):
            return None
        if not isinstance(register, str) or register not in _TARIFF_REGISTERS | {"KT"}:
            return None
        if not _remember(seen, (meter, register), record):
            return None
    meters = {key[0] for key in seen}
    if None in meters and len(meters) > 1:
        return None
    grouped: dict[str | int | None, dict[str, float]] = {}
    for (meter, register), record in seen.items():
        value = _number(record.get("DIEN_TTHU"))
        if value is None:
            return None
        grouped.setdefault(meter, {})[register] = value
    values = []
    for registers in grouped.values():
        if "KT" in registers:
            values.append(registers["KT"])
        elif registers.keys() == _TARIFF_REGISTERS:
            values.extend(registers.values())
        else:
            return None
    total = _total(values)
    if total is None:
        return None
    return PeriodUsage(total, min(item[2] for item in selected))


def invoice_summary(records: list[dict[str, Any]]) -> InvoiceSummary:
    if not isinstance(records, list):
        return InvoiceSummary(None, None)
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            return InvoiceSummary(None, None)
        invoice_id = record.get("ID_HDON")
        adjustment_id = record.get("ID_HDON_DC")
        if not _valid_id(invoice_id):
            return InvoiceSummary(None, None)
        if (
            adjustment_id is not None
            and adjustment_id != ""
            and not _valid_id(adjustment_id)
        ):
            return InvoiceSummary(None, None)
        if not _remember(seen, (invoice_id, adjustment_id), record):
            return InvoiceSummary(None, None)
    amounts = []
    for record in seen.values():
        status = record.get("TTRANG_TTOAN")
        if not isinstance(status, str) or status not in _INVOICE_STATUSES:
            return InvoiceSummary(None, None)
        if status == "TTOANMOTPHAN":
            kind = record.get("LOAI_PSINH")
            if not isinstance(kind, str) or not kind.strip() or kind != kind.strip():
                return InvoiceSummary(None, None)
            if kind == "TH":
                continue
        elif status != "CHUATT":
            continue
        amount = _number(record.get("TONG_NO"))
        if amount is None:
            return InvoiceSummary(None, None)
        amounts.append(abs(amount))
    total = _total(amounts)
    if total is None:
        return InvoiceSummary(None, None)
    return InvoiceSummary(total, len(amounts))


def _outage_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.fullmatch(rf"{_DATE_PATTERN} [0-9]{{2}}:[0-9]{{2}}", value):
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y %H:%M").replace(
            tzinfo=_LOCAL_TIMEZONE
        )
    except ValueError:
        return None


def _attribute(value: Any) -> str:
    return value.strip()[:512] if isinstance(value, str) else ""


def next_outage(
    records: list[dict[str, Any]], now: datetime | None = None
) -> Outage | None:
    if not isinstance(records, list):
        return None
    if now is None:
        now = datetime.now(_LOCAL_TIMEZONE)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=_LOCAL_TIMEZONE)
    else:
        now = now.astimezone(_LOCAL_TIMEZONE)
    nearest = None
    for record in records:
        if not isinstance(record, dict):
            continue
        start = _outage_time(record.get("TGIAN_BDAU"))
        if start is None or start < now:
            continue
        raw_end = record.get("TGIAN_KTHUC")
        end = _outage_time(raw_end)
        if raw_end is not None and raw_end != "" and end is None:
            continue
        if end is not None and end < start:
            continue
        if nearest is None or start < nearest.start:
            nearest = Outage(
                start,
                end,
                _attribute(record.get("KHUVUCMATDIEN")),
                _attribute(record.get("LY_DO")),
            )
    return nearest
