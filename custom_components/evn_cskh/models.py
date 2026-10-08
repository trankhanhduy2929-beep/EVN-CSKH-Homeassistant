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


def _date_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not re.fullmatch(
        rf"{_DATE_PATTERN}(?: [0-9]{{2}}:[0-9]{{2}}(?::[0-9]{{2}})?)?", value
    ):
        return None
    format_string = "%d/%m/%Y"
    if " " in value:
        format_string += " %H:%M:%S" if value.count(":") == 2 else " %H:%M"
    try:
        return datetime.strptime(value, format_string).replace(tzinfo=_LOCAL_TIMEZONE)
    except ValueError:
        return None


def _reading_bounds(
    record: dict[str, Any],
) -> tuple[datetime | None, datetime | None] | None:
    raw_start, raw_end = record.get("NGAY_DKY"), record.get("NGAY_CKY")
    start = _date_time(raw_start) if raw_start not in (None, "") else None
    end = _date_time(raw_end) if raw_end not in (None, "") else None
    if (raw_start not in (None, "") and start is None) or (
        raw_end not in (None, "") and end is None
    ):
        return None
    if (
        start is not None
        and end is not None
        and (
            start.date() > end.date()
            or (
                isinstance(raw_start, str)
                and isinstance(raw_end, str)
                and " " in raw_start
                and " " in raw_end
                and start > end
            )
        )
    ):
        return None
    return start, end


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
    total = _register_total([item[3] for item in selected])
    if total is None:
        return None
    return PeriodUsage(total, min(item[2] for item in selected))


def _register_total(
    records: list[dict[str, Any]], *, reading_register: bool = False
) -> float | None:
    if not records:
        return None
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        meter = record.get("SO_CTO")
        register = record.get("BCS")
        if register is None and reading_register:
            register = record.get("LOAI_CHISO")
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
    return _total(values)


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


_INVOICE_STATUS_LABELS = {
    "CHUATT": "Chưa thanh toán",
    "TTOANMOTPHAN": "Thanh toán một phần",
    "DATT": "Đã thanh toán",
    "DAHT": "Đã hủy",
    "CHUAHT": "Chưa hủy",
    "CHOXULY": "Chờ xử lý",
}
_READING_PERIOD_FIELDS = ("NGAY_CKY", "NGAY_DKY")
_READING_KIND_FIELDS = ("LOAI_CHISO", "BCS")
_INVALID = object()


def _period_groups(
    records: Any, *, skip_invalid_periods: bool = False
) -> dict[tuple[int, int], list[dict[str, Any]]] | None:
    if not isinstance(records, list) or not records:
        return None
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for record in records:
        period = _record_period_pair(record) if isinstance(record, dict) else None
        if period is None:
            if skip_invalid_periods:
                continue
            return None
        groups.setdefault(period, []).append(record)
    return groups


def _period_totals(records: Any) -> dict[tuple[int, int], float] | None:
    groups = _period_groups(records)
    if not groups:
        return None
    totals: dict[tuple[int, int], float] = {}
    for period, rows in groups.items():
        usage = monthly_summary(rows)
        if usage is None:
            return None
        totals[period] = usage.value
    return totals


def month_over_month(records: Any) -> dict[str, Any] | None:
    totals = _period_totals(records)
    if not totals:
        return None
    latest = max(totals)
    current = totals[latest]
    earlier = previous_months(date(*latest, 1), 1)
    previous = totals.get(earlier[0]) if earlier else None
    delta = _total((current, -previous)) if previous is not None else None
    percent = (
        _number(delta / previous * 100)
        if delta is not None and previous is not None and previous != 0
        else None
    )
    return {
        "current": current,
        "previous": previous,
        "delta": delta,
        "percent": percent,
    }


def trailing_average(records: Any, months: int = 12) -> float | None:
    if type(months) is not int or not 1 <= months <= 120:
        return None
    groups = _period_groups(records, skip_invalid_periods=True)
    if not groups:
        return None
    totals: dict[tuple[int, int], float] = {}
    for period, rows in groups.items():
        usage = monthly_summary(rows)
        if usage is None:
            if all(_number(row.get("DIEN_TTHU")) is None for row in rows):
                continue
            return None
        totals[period] = usage.value
    values = [totals[period] for period in sorted(totals)[-months:]]
    average = _total(values)
    return average / len(values) if average is not None and values else None


def _reading_period(record: dict[str, Any]) -> tuple[datetime, str] | None:
    if not any(record.get(field) not in (None, "") for field in _READING_PERIOD_FIELDS):
        return _reading_stamp(record)
    bounds = _reading_bounds(record)
    if bounds is None:
        return None
    start, end = bounds
    if end is not None:
        return end, record["NGAY_CKY"]
    if start is not None:
        return start, record["NGAY_DKY"]
    return None


def _single_reading(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        meter = record.get("SO_CTO")
        if meter is not None and not _valid_id(meter):
            return None
        registers = tuple(record.get(field) for field in ("BCS", "LOAI_CHISO"))
        if any(
            value is not None
            and (
                not isinstance(value, str)
                or not value
                or value != value.strip()
                or len(value) > 32
            )
            for value in registers
        ):
            return None
        identity = (meter, *registers)
        if not _remember(seen, identity, record):
            return None
    return next(iter(seen.values())) if len(seen) == 1 else None


def latest_reading(records: Any) -> dict[str, Any] | None:
    if not isinstance(records, list) or not records:
        return None
    dated: list[tuple[datetime, str, dict[str, Any]]] = []
    for record in records:
        if not isinstance(record, dict):
            return None
        period = _reading_period(record)
        if period is None:
            return None
        dated.append((*period, record))
    latest = max(item[0] for item in dated)
    selected = [item for item in dated if item[0] == latest]
    record = _single_reading([item[2] for item in selected])
    if record is None:
        return None
    numbers: dict[str, float | None] = {}
    for field in ("CHISO_CU", "CHISO_MOI", "HSN", "DIEN_TTHU"):
        value = record.get(field)
        if value is None:
            numbers[field] = None
            continue
        number = _number(value)
        if number is None:
            return None
        numbers[field] = number
    kind = None
    for field in _READING_KIND_FIELDS:
        value = record.get(field)
        if value is None:
            continue
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 32
        ):
            return None
        kind = value
        break
    return {
        "period": selected[0][1],
        "old": numbers["CHISO_CU"],
        "new": numbers["CHISO_MOI"],
        "multiplier": numbers["HSN"],
        "kwh": numbers["DIEN_TTHU"],
        "kind": kind,
    }


def outstanding_summary(records: Any) -> InvoiceSummary:
    return invoice_summary(records)


def outstanding_from_active(records: Any) -> InvoiceSummary:
    return invoice_summary(records)


def _invoice_optional_number(record: dict[str, Any], *fields: str) -> Any:
    for field in fields:
        value = record.get(field)
        if value is None or value == "":
            continue
        number = _number(value)
        if number is None:
            return _INVALID
        return number
    return None


def _normalized_invoice(record: dict[str, Any]) -> dict[str, Any] | None:
    raw_id = record.get("ID_HDON")
    if raw_id is None:
        id_key = None
    elif _valid_id(raw_id):
        id_key = str(raw_id)
    else:
        return None
    year = _integer(record.get("NAM"))
    month = _integer(record.get("THANG"))
    if year is None or month is None or not (1 <= year <= 9999 and 1 <= month <= 12):
        period = None
    else:
        period = f"{year:04d}-{month:02d}"
    cycle = None
    for field in ("KY", "SO_KY"):
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, str) and re.fullmatch(r"[0-9]{1,4}", value) is not None:
            value = int(value)
        if type(value) is not int or value < 0:
            return None
        cycle = value
        break
    amount = _invoice_optional_number(record, "TONG_TIEN")
    if amount is _INVALID:
        return None
    tax = _invoice_optional_number(record, "TIEN_GTGT", "THUE_NO")
    if tax is _INVALID:
        return None
    outstanding = _invoice_optional_number(record, "TONG_NO")
    if outstanding is _INVALID:
        return None
    energy = _invoice_optional_number(record, "DIEN_TTHU")
    if energy is _INVALID:
        return None
    status = record.get("TTRANG_TTOAN")
    if status is not None and (
        not isinstance(status, str) or status not in _INVOICE_STATUSES
    ):
        return None
    paid_date = record.get("NGAY_TTOAN")
    if paid_date is not None and not isinstance(paid_date, str):
        return None
    return {
        "id_key": id_key,
        "period": period,
        "cycle": cycle,
        "amount": amount,
        "tax": tax,
        "outstanding": outstanding,
        "status": status,
        "status_label": _INVOICE_STATUS_LABELS.get(status)
        if isinstance(status, str)
        else None,
        "paid_date": paid_date if paid_date != "" else None,
        "due_date": None,
        "energy": energy,
        "energy_unit": "kWh" if energy is not None else None,
    }


def latest_invoice(records: Any) -> dict[str, Any] | None:
    if not isinstance(records, list) or not records:
        return None
    selected = None
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
            continue
        period = (year, month)
        if selected is None or period > selected[0]:
            selected = (period, record)
    if selected is None:
        return None
    return _normalized_invoice(selected[1])


def month_label(day: date) -> str:
    if type(day) is not date:
        return ""
    return f"{day.month:02d}-{day.year:04d}"


def vn_now() -> date:
    return datetime.now(_LOCAL_TIMEZONE).date()


def previous_months(day: date, count: int) -> list[tuple[int, int]]:
    if type(day) is not date or type(count) is not int or count < 0:
        return []
    index = (day.year - 1) * 12 + day.month - 1
    return [
        (value // 12 + 1, value % 12 + 1)
        for value in range(index - 1, max(-1, index - count - 1), -1)
    ]


def _record_period_pair(record: dict[str, Any]) -> tuple[int, int] | None:
    year = _integer(record.get("NAM"))
    month = _integer(record.get("THANG"))
    if year is None or month is None or not (1 <= year <= 9999 and 1 <= month <= 12):
        return None
    return year, month


def daily_consumption_on(
    daily_records: list[dict[str, Any]], target_date: date
) -> float | None:
    if not isinstance(daily_records, list) or type(target_date) is not date:
        return None
    matching: list[dict[str, Any]] = []
    for record in daily_records:
        if not isinstance(record, dict):
            return None
        interval = _interval(record)
        if interval is None:
            return None
        if interval[0] <= target_date <= interval[1]:
            if interval[0] != interval[1]:
                return None
            matching.append(record)
    usage = daily_summary(matching)
    return usage.value if usage is not None else None


def latest_cycle_index(
    monthly_readings: list[dict[str, Any]],
    position: int = 0,
    *,
    as_of: date | None = None,
) -> float | None:
    if (
        not isinstance(monthly_readings, list)
        or type(position) is not int
        or position < 0
        or (as_of is not None and type(as_of) is not date)
    ):
        return None
    groups: dict[
        tuple[int, int], list[tuple[datetime | None, int | None, dict[str, Any]]]
    ] = {}
    for record in monthly_readings:
        if not isinstance(record, dict):
            return None
        period = _record_period_pair(record)
        if period is None:
            return None
        if as_of is not None and period >= (as_of.year, as_of.month):
            continue
        bounds = _reading_bounds(record)
        if bounds is None:
            return None
        start, end = bounds
        if start is not None and end is None:
            return None
        if as_of is not None and end is not None and end.date() > as_of:
            continue
        cycle = _integer(record["KY"]) if record.get("KY") is not None else None
        if record.get("KY") is not None and (cycle is None or cycle < 1):
            return None
        if record.get("SO_KY") is not None:
            count = _integer(record["SO_KY"])
            if count is None or count < 1:
                return None
        groups.setdefault(period, []).append((end, cycle, record))
    if not groups or position >= len(groups):
        return None
    boundaries = {
        period: max(item[0] for item in rows if item[0] is not None)
        for period, rows in groups.items()
        if any(item[0] is not None for item in rows)
    }
    if boundaries:
        ordered = sorted(
            boundaries, key=lambda period: (boundaries[period], period), reverse=True
        )
        if position >= len(ordered):
            return None
        boundary = boundaries[ordered[position]]
        if sum(value == boundary for value in boundaries.values()) > 1:
            return None
    else:
        ordered = sorted(groups, reverse=True)
    rows = groups[ordered[position]]
    if any(item[0] is not None for item in rows):
        if any(item[0] is None for item in rows):
            return None
        latest_end = max(item[0] for item in rows if item[0] is not None)
        selected = [item[2] for item in rows if item[0] == latest_end]
    elif any(item[1] is not None for item in rows):
        if any(item[1] is None for item in rows):
            return None
        latest_cycle = max(item[1] for item in rows if item[1] is not None)
        selected = [item[2] for item in rows if item[1] == latest_cycle]
    else:
        selected = [item[2] for item in rows]
    reading = _single_reading(selected)
    return _number(reading.get("CHISO_MOI")) if reading is not None else None


def _reading_stamp(record: dict[str, Any]) -> tuple[datetime, str] | None:
    raw_day = record.get("NGAY")
    day = _date(raw_day) if raw_day is not None else None
    if raw_day is not None and day is None:
        return None
    display = record.get("THOI_DIEM")
    if display is None or display == "":
        display = raw_day
    if not isinstance(display, str) or len(display) > 128:
        return None
    value = display
    if re.fullmatch(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", value) and day is not None:
        value = day.strftime("%d/%m/%Y") + " " + value
    stamp = _date_time(value)
    return (stamp, display) if stamp is not None else None


def latest_daily_index(
    daily_readings: list[dict[str, Any]],
) -> tuple[float | None, str | None]:
    if not isinstance(daily_readings, list) or not daily_readings:
        return None, None
    dated: list[tuple[datetime, str, dict[str, Any]]] = []
    for record in daily_readings:
        if not isinstance(record, dict):
            return None, None
        stamp = _reading_stamp(record)
        if stamp is None:
            return None, None
        dated.append((*stamp, record))
    latest = max(item[0] for item in dated)
    selected = [item for item in dated if item[0] == latest]
    first = _single_reading([item[2] for item in selected])
    if first is None:
        return None, None
    index = _number(first.get("CHISO_MOI"))
    return (index, selected[0][1]) if index is not None else (None, None)


def _invoice_id(value: Any) -> str | None:
    if type(value) is int and 0 < value < 10**128:
        return str(value)
    if (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is not None
        and value.strip("0")
    ):
        return value
    return None


def _invoice_key(record: dict[str, Any]) -> tuple[str, str | None] | None:
    original = _invoice_id(record.get("ID_HDON"))
    if original is None:
        return None
    raw_adjusted = record.get("ID_HDON_DC")
    if raw_adjusted is None or raw_adjusted == "":
        return original, None
    adjusted = _invoice_id(raw_adjusted)
    return (original, adjusted) if adjusted is not None else None


def invoice_for_month(active: Any, paid: Any, year: Any, month: Any) -> float | None:
    if (
        not isinstance(active, list)
        or not isinstance(paid, list)
        or type(year) is not int
        or type(month) is not int
        or not (1 <= year <= 9999 and 1 <= month <= 12)
    ):
        return None
    sources: list[dict[tuple[str, str | None], dict[str, Any]]] = []
    for rows in (active, paid):
        source: dict[tuple[str, str | None], dict[str, Any]] = {}
        seen: dict[tuple[Any, ...], dict[str, Any]] = {}
        for record in rows:
            if not isinstance(record, dict):
                return None
            key = _invoice_key(record)
            if key is None:
                return None
            normalized = record | {"ID_HDON": key[0], "ID_HDON_DC": key[1]}
            if not _remember(seen, key, normalized):
                return None
            source.setdefault(key, record)
        sources.append(source)
    current, history = sources
    selected = {
        key: record
        for key, record in (history | current).items()
        if _record_period_pair(record) == (year, month)
    }
    if not selected:
        return None
    values: list[float] = []
    for key, record in selected.items():
        status = record.get("TTRANG_TTOAN")
        if status is None:
            if (
                key in current
                or _reading_stamp({"THOI_DIEM": record.get("NGAY_TTOAN")}) is None
            ):
                return None
        elif (
            not isinstance(status, str)
            or status not in _INVOICE_STATUSES
            or status in {"DAHT", "CHUAHT"}
        ):
            return None
        kind = record.get("LOAI_PSINH")
        if kind is not None and (
            not isinstance(kind, str)
            or not kind
            or kind != kind.strip()
            or kind == "TH"
        ):
            return None
        amount = _number(record.get("TONG_TIEN"))
        if amount is None:
            return None
        values.append(amount)
    return _total(values)


def _monthly_reading_usage(records: list[dict[str, Any]]) -> float | None:
    groups: dict[int | None, list[dict[str, Any]]] = {}
    for record in records:
        raw_cycle = record.get("KY")
        cycle = _integer(raw_cycle) if raw_cycle is not None else None
        if raw_cycle is not None and (cycle is None or cycle < 1):
            return None
        if record.get("SO_KY") is not None:
            count = _integer(record["SO_KY"])
            if count is None or count < 1:
                return None
        groups.setdefault(cycle, []).append(record)
    if None in groups and len(groups) > 1:
        return None
    values: list[float] = []
    for rows in groups.values():
        bounds: dict[Any, set[tuple[datetime | None, datetime | None]]] = {}
        for row in rows:
            meter = row.get("SO_CTO")
            if meter is not None and not _valid_id(meter):
                return None
            interval = _reading_bounds(row)
            if interval is None:
                return None
            bounds.setdefault(meter, set()).add(interval)
        if any(len(intervals) > 1 for intervals in bounds.values()):
            return None
        value = _register_total(rows, reading_register=True)
        if value is None:
            return None
        values.append(value)
    return _total(values) if values else None


def customer_month_energy(
    points: list[dict[str, Any]],
    monthly: dict[str, list[dict[str, Any]]],
    monthly_readings: dict[str, list[dict[str, Any]]],
    year: int,
    month: int,
) -> float | None:
    if (
        not isinstance(points, list)
        or not points
        or not isinstance(monthly, dict)
        or not isinstance(monthly_readings, dict)
        or type(year) is not int
        or type(month) is not int
        or not (1 <= year <= 9999 and 1 <= month <= 12)
    ):
        return None
    owned: dict[str, dict[str, Any]] = {}
    for point in points:
        if not isinstance(point, dict):
            return None
        code = point.get("MA_DDO")
        if not isinstance(code, str) or not _valid_id(code):
            return None
        if code in owned and any(
            field in point
            and field in owned[code]
            and not _identical(point[field], owned[code][field])
            for field in ("MA_KHANG", "MA_DVIQLY")
        ):
            return None
        owned[code] = owned.get(code, {}) | point
    values: list[float] = []
    for code, point in owned.items():
        selected: list[dict[str, Any]] = []
        primary = True
        for source, primary in ((monthly, True), (monthly_readings, False)):
            rows = source.get(code, [])
            if not isinstance(rows, list):
                return None
            for row in rows:
                if not isinstance(row, dict) or _record_period_pair(row) is None:
                    return None
                if any(
                    field in row and row[field] != expected
                    for field, expected in (
                        ("MA_DDO", code),
                        *(
                            (field, point[field])
                            for field in ("MA_KHANG", "MA_DVIQLY")
                            if field in point
                        ),
                    )
                ):
                    return None
            selected = [
                row for row in rows if _record_period_pair(row) == (year, month)
            ]
            if selected:
                break
        if not selected:
            return None
        if primary:
            usage = monthly_summary(selected)
            value = usage.value if usage is not None else None
        else:
            value = _monthly_reading_usage(selected)
        if value is None:
            return None
        values.append(value)
    return _total(values)
