import importlib.util
import json
import sys
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "evn_cskh_models_unit",
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "evn_cskh"
    / "models.py",
)
assert _SPEC is not None and _SPEC.loader is not None
models = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = models
_SPEC.loader.exec_module(models)

PeriodUsage = models.PeriodUsage
InvoiceSummary = models.InvoiceSummary
Outage = models.Outage
monthly_summary = models.monthly_summary
daily_summary = models.daily_summary
invoice_summary = models.invoice_summary
next_outage = models.next_outage
outage_duration_hours = models.outage_duration_hours
current_outage = models.current_outage
upcoming_outage = models.upcoming_outage
month_over_month = models.month_over_month
trailing_average = models.trailing_average
latest_reading = models.latest_reading
outstanding_summary = models.outstanding_summary
outstanding_from_active = models.outstanding_from_active
latest_invoice = models.latest_invoice
month_label = models.month_label
vn_now = models.vn_now
previous_months = models.previous_months
daily_consumption_on = models.daily_consumption_on
latest_cycle_index = models.latest_cycle_index
latest_daily_index = models.latest_daily_index
invoice_for_month = models.invoice_for_month
customer_month_energy = models.customer_month_energy
LOCAL = ZoneInfo("Asia/Ho_Chi_Minh")
NOW = datetime(2026, 10, 7, 12, tzinfo=LOCAL)
INVALID_NUMBERS = (
    None,
    True,
    False,
    float("nan"),
    float("inf"),
    float("-inf"),
    Decimal("NaN"),
    Decimal("sNaN"),
    Decimal("Infinity"),
    10**400,
    "9" * 400,
    "",
    " ",
    "NaN",
    "Infinity",
    "1e3",
    "1,234",
    "1,5",
    "1.234,56",
    "1,234.56",
    "1 234",
    "1\u00a0234",
    "1_234",
    "1.2.3",
    ".5",
    "1.",
    "１２",
    "12 kWh",
    [],
    {},
    1 + 2j,
)


def _monthly(value: Any = 12.5, **fields: Any) -> dict[str, Any]:
    return {
        "NAM": 2026,
        "THANG": 10,
        "KY": 1,
        "SO_KY": 1,
        "SO_CTO": "METER-A",
        "DIEN_TTHU": value,
        **fields,
    }


def _daily(value: Any = 12.5, **fields: Any) -> dict[str, Any]:
    return {
        "NGAY": "06/10/2026",
        "NGAY_HTHI": "06/10/2026",
        "SO_CTO": "METER-A",
        "BCS": "KT",
        "DIEN_TTHU": value,
        **fields,
    }


def _invoice(value: Any = 125000, **fields: Any) -> dict[str, Any]:
    return {
        "ID_HDON": "INVOICE-A",
        "ID_HDON_DC": None,
        "TTRANG_TTOAN": "CHUATT",
        "LOAI_PSINH": "PS",
        "TONG_NO": value,
        **fields,
    }


def _outage(start: Any = "08/10/2026 08:00", **fields: Any) -> dict[str, Any]:
    return {
        "TGIAN_BDAU": start,
        "TGIAN_KTHUC": "08/10/2026 10:00",
        "KHUVUCMATDIEN": "Test area",
        "LY_DO": "Maintenance",
        **fields,
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0.0),
        (0.0, 0.0),
        (-3, -3.0),
        (12.125, 12.125),
        ("12", 12.0),
        ("12.125", 12.125),
        (" 12.50 ", 12.5),
        ("+001.50", 1.5),
        ("-2.25", -2.25),
        ("-0", 0.0),
        (Decimal("1.25"), 1.25),
        (Fraction(1, 8), 0.125),
        (1e100, 1e100),
    ],
)
def test_numeric_values_across_summaries(value: Any, expected: float) -> None:
    assert monthly_summary([_monthly(value)]) == PeriodUsage(expected, "2026-10")
    assert daily_summary([_daily(value)]) == PeriodUsage(expected, "06/10/2026")
    assert invoice_summary([_invoice(value)]) == InvoiceSummary(abs(expected), 1)


@pytest.mark.parametrize("value", INVALID_NUMBERS)
def test_invalid_numbers_make_selected_data_unknown(value: Any) -> None:
    assert monthly_summary([_monthly(value)]) is None
    assert daily_summary([_daily(value)]) is None
    assert invoice_summary([_invoice(value)]) == InvoiceSummary(None, None)


@pytest.mark.parametrize("factory", [_monthly, _daily, _invoice])
def test_missing_amount_is_not_zero(factory: Any) -> None:
    record = factory()
    field = "TONG_NO" if factory is _invoice else "DIEN_TTHU"
    record.pop(field)
    if factory is _invoice:
        assert invoice_summary([record]) == InvoiceSummary(None, None)
    elif factory is _monthly:
        assert monthly_summary([record]) is None
    else:
        assert daily_summary([record]) is None


@pytest.mark.parametrize("records", [None, {}, "", [None], [False], [{}]])
def test_missing_or_malformed_collections_are_unknown(records: Any) -> None:
    assert monthly_summary(records) is None
    assert daily_summary(records) is None
    assert invoice_summary(records) == InvoiceSummary(None, None)
    assert next_outage(records, NOW) is None


def test_confirmed_empty_collections() -> None:
    assert monthly_summary([]) is None
    assert daily_summary([]) is None
    assert invoice_summary([]) == InvoiceSummary(0.0, 0)
    assert next_outage([], NOW) is None


def test_monthly_numeric_month_and_year_sorting_not_lifetime_sum() -> None:
    records = [
        _monthly(9, THANG="9"),
        _monthly(12, THANG="12"),
        _monthly(11, THANG="11"),
        _monthly(10, THANG="10"),
        _monthly(999, NAM="2025", THANG="12"),
    ]
    assert monthly_summary(records) == PeriodUsage(12.0, "2026-12")
    records.insert(2, _monthly("3.5", NAM="2027", THANG="1"))
    assert monthly_summary(records) == PeriodUsage(3.5, "2027-01")


def test_monthly_multiple_cycles_meters_corrections_and_deduplication() -> None:
    first = _monthly(100, KY="1", SO_KY=3)
    records = [
        _monthly(3000, THANG=9),
        first,
        _monthly("-5.5", KY=2, SO_KY=3),
        deepcopy(first),
        _monthly(40, KY=3, SO_KY=3),
        _monthly(20, SO_CTO="METER-B"),
    ]
    assert monthly_summary(records) == PeriodUsage(154.5, "2026-10")
    assert monthly_summary(list(reversed(records))) == PeriodUsage(154.5, "2026-10")


def test_monthly_invalid_old_consumption_does_not_replace_latest_month() -> None:
    assert monthly_summary(
        [
            _monthly(None, NAM=2025, THANG=12),
            _monthly(20),
            _monthly(False, THANG=9),
        ]
    ) == PeriodUsage(20.0, "2026-10")


@pytest.mark.parametrize("value", INVALID_NUMBERS)
def test_monthly_invalid_latest_is_not_skipped_or_replaced_by_older(value: Any) -> None:
    assert (
        monthly_summary(
            [
                _monthly(50, THANG=9),
                _monthly(20, KY=1),
                _monthly(value, KY=2),
            ]
        )
        is None
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("NAM", None),
        ("NAM", True),
        ("NAM", 0),
        ("NAM", 10000),
        ("NAM", "2026x"),
        ("NAM", float("inf")),
        ("NAM", 2026.5),
        ("THANG", None),
        ("THANG", False),
        ("THANG", 0),
        ("THANG", 13),
        ("THANG", "1,0"),
        ("THANG", 10.5),
        ("THANG", float("nan")),
    ],
)
def test_monthly_invalid_period_cannot_establish_latest(field: str, value: Any) -> None:
    assert monthly_summary([_monthly(10), _monthly(20, **{field: value})]) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"DIEN_TTHU": 50},
        {"DIEN_TTHU": "12.5"},
        {"SO_KY": 2},
        {"metadata": "different"},
        {"KY": "1"},
    ],
)
def test_monthly_conflicting_duplicate_unknown(changes: dict[str, Any]) -> None:
    assert monthly_summary([_monthly(), _monthly(**changes)]) is None


@pytest.mark.parametrize("field", ["KY", "SO_KY"])
@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "1,2", float("inf")])
def test_monthly_invalid_cycle_metadata(field: str, value: Any) -> None:
    assert monthly_summary([_monthly(**{field: value})]) is None


def test_monthly_missing_ids_never_mix_with_identified_records() -> None:
    assert monthly_summary([_monthly(KY=None), _monthly(KY=2)]) is None
    assert monthly_summary([_monthly(SO_CTO=None), _monthly(SO_CTO="METER-B")]) is None
    assert monthly_summary([{"NAM": 2026, "THANG": 10, "DIEN_TTHU": 5}]) == PeriodUsage(
        5.0, "2026-10"
    )


@pytest.mark.parametrize("display", [None, ""])
def test_daily_uses_ngay_when_display_missing(display: Any) -> None:
    assert daily_summary([_daily(NGAY_HTHI=display)]) == PeriodUsage(12.5, "06/10/2026")
    record = _daily()
    record.pop("NGAY_HTHI")
    assert daily_summary([record]) == PeriodUsage(12.5, "06/10/2026")


def test_daily_numeric_date_sorting_and_year_rollover() -> None:
    records = [
        _daily(99, NGAY="31/12/2025", NGAY_HTHI="31/12/2025"),
        _daily(11, NGAY="09/10/2026", NGAY_HTHI="09/10/2026"),
        _daily(10, NGAY="01/10/2026", NGAY_HTHI="01/10/2026"),
        _daily(90, NGAY="30/09/2026", NGAY_HTHI="30/09/2026"),
    ]
    assert daily_summary(records) == PeriodUsage(11.0, "09/10/2026")
    records.append(_daily(3, NGAY="01/01/2027", NGAY_HTHI="01/01/2027"))
    assert daily_summary(records) == PeriodUsage(3.0, "01/01/2027")


def test_daily_uses_rightmost_display_date_and_preserves_multiday_total() -> None:
    interval = "29/09/2026 - 07/10/2026"
    records = [
        _daily(99, NGAY="06/10/2026", NGAY_HTHI="06/10/2026"),
        _daily(24, NGAY="29/09/2026", NGAY_HTHI=interval),
        _daily(17, NGAY="30/09/2026", NGAY_HTHI="30/09/2026 - 05/10/2026"),
    ]
    assert daily_summary(records) == PeriodUsage(24.0, interval)
    assert daily_summary(list(reversed(records))) == PeriodUsage(24.0, interval)


def test_daily_display_only_interval_and_leap_day() -> None:
    record = _daily(5, NGAY_HTHI="28/02/2024 - 29/02/2024")
    record.pop("NGAY")
    assert daily_summary([record]) == PeriodUsage(5.0, "28/02/2024 - 29/02/2024")


@pytest.mark.parametrize(
    "display",
    [
        "31/02/2026",
        "29/02/2025",
        "2026-10-06",
        "06/10/26",
        "6/10/2026",
        "07/10/2026 - 05/10/2026",
        "06/10/2026 - invalid",
        "01/10/2026 - 02/10/2026 - 03/10/2026",
        " ",
        "x" * 129,
        False,
        [],
        {},
    ],
)
def test_daily_invalid_display_not_hidden_by_ngay(display: Any) -> None:
    assert daily_summary([_daily(NGAY_HTHI=display)]) is None


def test_daily_missing_date_does_not_manufacture_period() -> None:
    assert daily_summary([_daily(NGAY=None, NGAY_HTHI=None)]) is None


def test_daily_kt_preferred_per_meter_and_interval_without_double_counting() -> None:
    records = [
        _daily(30, BCS="KT"),
        _daily(10, BCS="BT"),
        _daily(8, BCS="CD"),
        _daily(12, BCS="TD"),
        _daily(2, SO_CTO="METER-B", BCS="BT"),
        _daily(3, SO_CTO="METER-B", BCS="CD"),
        _daily(4, SO_CTO="METER-B", BCS="TD"),
    ]
    records.extend(deepcopy(records))
    assert daily_summary(records) == PeriodUsage(39.0, "06/10/2026")


def test_daily_tariff_aggregation_preserves_negative_corrections() -> None:
    records = [_daily(10, BCS="BT"), _daily(-2, BCS="CD"), _daily("3.5", BCS="TD")]
    assert daily_summary(records) == PeriodUsage(11.5, "06/10/2026")


@pytest.mark.parametrize("register", ["KT", "BT", "CD", "TD"])
def test_daily_invalid_latest_register_not_hidden_by_kt_preference(
    register: str,
) -> None:
    records = [_daily(1, BCS=band) for band in ("KT", "BT", "CD", "TD")]
    for record in records:
        if record["BCS"] == register:
            record["DIEN_TTHU"] = None
    assert daily_summary(records) is None


def test_daily_kt_need_not_equal_register_sum_and_no_fallback_for_bad_kt() -> None:
    records = [
        _daily(30),
        _daily(1, BCS="BT"),
        _daily(1, BCS="CD"),
        _daily(1, BCS="TD"),
    ]
    assert daily_summary(records) == PeriodUsage(30.0, "06/10/2026")
    records[0]["DIEN_TTHU"] = "1,234"
    assert daily_summary(records) is None


@pytest.mark.parametrize("registers", [("BT",), ("BT", "TD"), ("CD", "TD")])
def test_daily_incomplete_tariffs_do_not_imply_zero_for_missing_registers(
    registers: tuple[str, ...],
) -> None:
    assert daily_summary([_daily(1, BCS=register) for register in registers]) is None


@pytest.mark.parametrize("register", [None, "", "UNKNOWN", "kt", True, []])
def test_daily_unknown_register_is_not_silently_dropped(register: Any) -> None:
    assert daily_summary([_daily(10), _daily(2, BCS=register)]) is None


def test_daily_meter_replacement_same_day_is_not_deduplicated_across_meters() -> None:
    first = _daily(4, SO_CTO="OLD-METER")
    second = _daily(6, SO_CTO="NEW-METER")
    assert daily_summary(
        [first, second, deepcopy(first), deepcopy(second)]
    ) == PeriodUsage(10.0, "06/10/2026")


@pytest.mark.parametrize("changes", [{"DIEN_TTHU": 5}, {"metadata": "different"}])
def test_daily_conflicting_duplicates_unknown(changes: dict[str, Any]) -> None:
    assert daily_summary([_daily(), _daily(**changes)]) is None


def test_boolean_and_numeric_raw_records_are_not_exact_duplicates() -> None:
    assert monthly_summary([_monthly(1), _monthly(True)]) is None
    assert daily_summary([_daily(1), _daily(True)]) is None
    assert invoice_summary([_invoice(1), _invoice(True)]) == InvoiceSummary(None, None)


@pytest.mark.parametrize("value", INVALID_NUMBERS)
def test_invalid_duplicate_values_do_not_raise_or_turn_into_zero(value: Any) -> None:
    assert monthly_summary([_monthly(value), _monthly(value)]) is None
    assert daily_summary([_daily(value), _daily(value)]) is None
    assert invoice_summary([_invoice(value), _invoice(value)]) == InvoiceSummary(
        None, None
    )


def test_nested_raw_metadata_deduplicates_without_coercing_booleans() -> None:
    for factory, helper in ((_monthly, monthly_summary), (_daily, daily_summary)):
        record = factory(metadata={"values": [1, "test"]})
        assert helper([record, deepcopy(record)]) == helper([record])
        assert helper([record, factory(metadata={"values": [True, "test"]})]) is None
    record = _invoice(metadata={"values": [1, "test"]})
    assert invoice_summary([record, deepcopy(record)]) == invoice_summary([record])
    assert invoice_summary(
        [record, _invoice(metadata={"values": [True, "test"]})]
    ) == InvoiceSummary(None, None)


@pytest.mark.parametrize(
    ("factory", "helper", "expected"),
    [
        (_monthly, monthly_summary, None),
        (_daily, daily_summary, None),
        (_invoice, invoice_summary, InvoiceSummary(None, None)),
    ],
    ids=["monthly", "daily", "invoice"],
)
@pytest.mark.parametrize(
    ("prefix", "suffix"),
    [('{"nested":', "}"), ("[", "]")],
    ids=["dict", "list"],
)
def test_deep_decoded_json_duplicates_are_unknown_without_crashing(
    factory: Any, helper: Any, expected: Any, prefix: str, suffix: str
) -> None:
    depth = 500
    leaf = "x" * (6000 - depth * (len(prefix) + len(suffix)))
    metadata = prefix * depth + json.dumps(leaf) + suffix * depth
    record = json.dumps(factory())[:-1] + ', "metadata": ' + metadata + "}"
    payload = "[" + record + "," + record + "]"
    assert 12000 <= len(payload) <= 13000
    records = json.loads(payload)
    assert records[0]["metadata"] is not records[1]["metadata"]
    node = records[0]["metadata"]
    for _ in range(depth):
        node = node["nested"] if isinstance(node, dict) else node[0]
    assert node == leaf
    assert helper([records[0]]) != expected
    assert helper(records) == expected


@pytest.mark.parametrize("other_meter", ["METER-A", "METER-B"])
def test_daily_same_endpoint_mismatched_intervals_not_combined(
    other_meter: str,
) -> None:
    assert (
        daily_summary(
            [
                _daily(20, NGAY_HTHI="01/10/2026 - 06/10/2026"),
                _daily(5, SO_CTO=other_meter, NGAY_HTHI="06/10/2026"),
            ]
        )
        is None
    )


def test_daily_does_not_combine_kt_and_tariffs_with_mismatched_intervals() -> None:
    records = [_daily(20, NGAY_HTHI="01/10/2026 - 06/10/2026")]
    records.extend(_daily(1, BCS=register) for register in ("BT", "CD", "TD"))
    assert daily_summary(records) is None


def test_daily_invalid_latest_does_not_fall_back_to_previous_reading() -> None:
    assert (
        daily_summary(
            [
                _daily(10, NGAY="05/10/2026", NGAY_HTHI="05/10/2026"),
                _daily(None),
            ]
        )
        is None
    )
    assert daily_summary(
        [
            _daily(None, NGAY="05/10/2026", NGAY_HTHI="05/10/2026"),
            _daily(10),
        ]
    ) == PeriodUsage(10.0, "06/10/2026")


def test_daily_missing_meter_not_combined_with_identified_meter() -> None:
    assert daily_summary([_daily(SO_CTO=None), _daily(SO_CTO="METER-B")]) is None


@pytest.mark.parametrize("meter", [True, False, [], {}, "", " METER-A", 1.5])
def test_invalid_meter_identifiers(meter: Any) -> None:
    assert monthly_summary([_monthly(SO_CTO=meter)]) is None
    assert daily_summary([_daily(SO_CTO=meter)]) is None


@pytest.mark.parametrize(
    ("status", "kind", "expected"),
    [
        ("CHUATT", "PS", InvoiceSummary(25.0, 1)),
        ("CHUATT", "TH", InvoiceSummary(25.0, 1)),
        ("CHUATT", None, InvoiceSummary(25.0, 1)),
        ("TTOANMOTPHAN", "PS", InvoiceSummary(25.0, 1)),
        ("TTOANMOTPHAN", "TH", InvoiceSummary(0.0, 0)),
        ("DATT", "PS", InvoiceSummary(0.0, 0)),
        ("DAHT", "TH", InvoiceSummary(0.0, 0)),
        ("CHUAHT", "TH", InvoiceSummary(0.0, 0)),
        ("CHOXULY", "PS", InvoiceSummary(0.0, 0)),
    ],
)
def test_invoice_app_outstanding_predicate(
    status: str, kind: Any, expected: Any
) -> None:
    assert (
        invoice_summary([_invoice(-25, TTRANG_TTOAN=status, LOAI_PSINH=kind)])
        == expected
    )


def test_invoice_abs_is_per_selected_invoice_not_abs_of_net_or_gross() -> None:
    records = [
        _invoice(100, TONG_TIEN=1000),
        _invoice(-40, ID_HDON="INVOICE-B", TONG_TIEN=999),
        _invoice(-20, ID_HDON="INVOICE-C", TTRANG_TTOAN="TTOANMOTPHAN"),
        _invoice(
            -80, ID_HDON="INVOICE-D", TTRANG_TTOAN="TTOANMOTPHAN", LOAI_PSINH="TH"
        ),
        _invoice(500, ID_HDON="INVOICE-E", TTRANG_TTOAN="DATT"),
    ]
    result = invoice_summary(records)
    assert result == InvoiceSummary(160.0, 3)
    assert result.notes
    assert "abs(TONG_NO)" in " ".join(result.notes)
    assert "not a signed net balance" in " ".join(result.notes)
    assert "Missing invoices" in " ".join(result.notes)


def test_invoice_selected_zero_debt_is_still_an_outstanding_record() -> None:
    assert invoice_summary([_invoice(0)]) == InvoiceSummary(0.0, 1)


@pytest.mark.parametrize("status", [None, "", "UNKNOWN", "datt", "DATT ", True, 0, {}])
def test_invoice_missing_or_unknown_status_is_not_paid(status: Any) -> None:
    assert invoice_summary([_invoice(TTRANG_TTOAN=status)]) == InvoiceSummary(
        None, None
    )
    record = _invoice()
    record.pop("TTRANG_TTOAN")
    assert invoice_summary([record]) == InvoiceSummary(None, None)


@pytest.mark.parametrize("kind", [None, "", " ", "TH ", False, 1, []])
def test_invoice_partial_missing_or_invalid_kind_is_unknown(kind: Any) -> None:
    assert invoice_summary(
        [_invoice(TTRANG_TTOAN="TTOANMOTPHAN", LOAI_PSINH=kind)]
    ) == InvoiceSummary(None, None)


def test_invoice_selected_bad_debt_invalidates_whole_summary_without_gross_fallback() -> (
    None
):
    assert invoice_summary(
        [_invoice(100), _invoice(None, ID_HDON="INVOICE-B", TONG_TIEN=999)]
    ) == InvoiceSummary(None, None)
    record = _invoice(TONG_TIEN=999)
    record.pop("TONG_NO")
    assert invoice_summary([record]) == InvoiceSummary(None, None)


@pytest.mark.parametrize(
    "status", ["DATT", "DAHT", "CHUAHT", "CHOXULY", "TTOANMOTPHAN"]
)
def test_invoice_unselected_debt_does_not_need_numeric_amount(status: str) -> None:
    record = _invoice(TTRANG_TTOAN=status, LOAI_PSINH="TH")
    record.pop("TONG_NO")
    assert invoice_summary([record]) == InvoiceSummary(0.0, 0)


def test_invoice_exact_duplicates_and_adjustments_use_raw_pair() -> None:
    original = _invoice(100)
    adjusted = _invoice(-40, ID_HDON_DC="ADJUSTMENT-A")
    other = _invoice(10, ID_HDON="INVOICE-B", ID_HDON_DC="ADJUSTMENT-A")
    assert invoice_summary(
        [
            original,
            adjusted,
            other,
            deepcopy(original),
            deepcopy(adjusted),
            deepcopy(other),
        ]
    ) == InvoiceSummary(150.0, 3)


def test_invoice_raw_identifiers_not_normalized_or_replaced_by_truthiness() -> None:
    assert invoice_summary(
        [
            _invoice(1, ID_HDON="001"),
            _invoice(2, ID_HDON="1"),
            _invoice(4, ID_HDON="001", ID_HDON_DC=0),
            _invoice(8, ID_HDON="001", ID_HDON_DC="0"),
        ]
    ) == InvoiceSummary(15.0, 4)


@pytest.mark.parametrize(
    "changes",
    [{"TONG_NO": -125000}, {"TTRANG_TTOAN": "DATT"}, {"metadata": "different"}],
)
def test_invoice_conflicting_duplicate_is_unknown(changes: dict[str, Any]) -> None:
    assert invoice_summary([_invoice(), _invoice(**changes)]) == InvoiceSummary(
        None, None
    )


@pytest.mark.parametrize(
    "identifier", [None, "", True, False, [], {}, 1.5, " INVOICE-A"]
)
def test_invoice_invalid_identity_prevents_counting(identifier: Any) -> None:
    assert invoice_summary([_invoice(ID_HDON=identifier)]) == InvoiceSummary(None, None)


@pytest.mark.parametrize("identifier", [True, False, [], {}, 1.5])
def test_invoice_invalid_adjustment_identity(identifier: Any) -> None:
    assert invoice_summary([_invoice(ID_HDON_DC=identifier)]) == InvoiceSummary(
        None, None
    )


def test_invoice_no_payment_state_inferred_between_calls() -> None:
    records = [_invoice(-5)]
    previous = invoice_summary(records)
    assert invoice_summary([]) == InvoiceSummary(0.0, 0)
    assert invoice_summary(None) == InvoiceSummary(None, None)
    assert previous == InvoiceSummary(5.0, 1)
    assert records[0]["TTRANG_TTOAN"] == "CHUATT"
    assert records[0]["TONG_NO"] == -5


def test_nonfinite_aggregate_is_unknown() -> None:
    assert monthly_summary([_monthly(1e308), _monthly(1e308, KY=2)]) is None
    assert daily_summary([_daily(1e308), _daily(1e308, SO_CTO="METER-B")]) is None
    assert invoice_summary(
        [_invoice(1e308), _invoice(1e308, ID_HDON="INVOICE-B")]
    ) == InvoiceSummary(None, None)


def test_outage_nearest_future_from_unsorted_past_and_future_rows() -> None:
    records = [
        _outage("09/10/2026 08:00", TGIAN_KTHUC="09/10/2026 10:00"),
        _outage("01/10/2026 08:00", TGIAN_KTHUC="01/10/2026 10:00"),
        _outage("07/10/2026 13:00", TGIAN_KTHUC="07/10/2026 14:00"),
        _outage("08/10/2026 08:00"),
    ]
    expected = Outage(
        datetime(2026, 10, 7, 13, tzinfo=LOCAL),
        datetime(2026, 10, 7, 14, tzinfo=LOCAL),
        "Test area",
        "Maintenance",
    )
    assert next_outage(records, NOW) == expected
    assert next_outage(list(reversed(records)), NOW) == expected


def test_outage_active_window_excluded_and_future_start_inclusive() -> None:
    active = _outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 14:00")
    assert next_outage([active], NOW) is None
    starts_now = _outage("07/10/2026 12:00", TGIAN_KTHUC="07/10/2026 14:00")
    result = next_outage([active, starts_now], NOW)
    assert result is not None
    assert result.start == NOW


@pytest.mark.parametrize("end", [None, ""])
def test_outage_missing_end_allowed(end: Any) -> None:
    record = _outage(TGIAN_KTHUC=end)
    result = next_outage([record], NOW)
    assert result is not None
    assert result.end is None
    record.pop("TGIAN_KTHUC")
    assert next_outage([record], NOW) == result


@pytest.mark.parametrize(
    "start",
    [None, "", False, [], "31/02/2026 08:00", "08/10/2026 25:00", "2026-10-08 08:00"],
)
def test_outage_invalid_starts_ignored(start: Any) -> None:
    invalid = _outage(start)
    assert next_outage([invalid], NOW) is None
    assert next_outage([invalid, _outage()], NOW) == next_outage([_outage()], NOW)


@pytest.mark.parametrize(
    "end", [False, "invalid", "08/10/2026 07:00", "31/02/2026 10:00"]
)
def test_outage_invalid_or_reversed_end_ignored(end: Any) -> None:
    assert next_outage([_outage(TGIAN_KTHUC=end)], NOW) is None
    valid = _outage("09/10/2026 08:00", TGIAN_KTHUC=None)
    result = next_outage([_outage(TGIAN_KTHUC=end), valid], NOW)
    assert result is not None
    assert result.start == datetime(2026, 10, 9, 8, tzinfo=LOCAL)


@pytest.mark.parametrize("status", [None, True, False, 0, 1, "HOAN", "UNKNOWN"])
def test_outage_unverified_status_does_not_guess_cancellation(status: Any) -> None:
    assert next_outage([_outage(TTHAI_HOAN=status)], NOW) is not None


def test_outage_timezone_and_naive_now_are_explicitly_local() -> None:
    result = next_outage([_outage()], NOW.astimezone(UTC))
    assert result is not None
    assert result.start.tzinfo == LOCAL
    assert result.start.utcoffset() == timedelta(hours=7)
    assert result.end is not None and result.end.tzinfo == LOCAL
    assert next_outage([_outage()], NOW.replace(tzinfo=None)) == result
    assert next_outage([_outage()], datetime(2026, 10, 8, 2, tzinfo=UTC)) is None


def test_outage_default_now_uses_local_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            assert tz == LOCAL
            return NOW

    monkeypatch.setattr(models, "datetime", Clock)
    assert next_outage([_outage()]) == next_outage([_outage()], NOW)


def test_outage_text_attributes_capped_and_bad_types_not_stringified() -> None:
    result = next_outage([_outage(KHUVUCMATDIEN="a" * 2000, LY_DO="r" * 2000)], NOW)
    assert result is not None
    assert result.area == "a" * 512
    assert result.reason == "r" * 512
    result = next_outage(
        [_outage(KHUVUCMATDIEN={"unexpected": "value"}, LY_DO=None)], NOW
    )
    assert result is not None
    assert result.area == result.reason == ""


def test_helpers_do_not_mutate_raw_records() -> None:
    for helper, records in (
        (monthly_summary, [_monthly(-5), _monthly(10, KY=2)]),
        (daily_summary, [_daily(-5), _daily(10, SO_CTO="METER-B")]),
        (invoice_summary, [_invoice(-5)]),
    ):
        original = deepcopy(records)
        helper(records)
        assert records == original
    records = [_outage()]
    original = deepcopy(records)
    next_outage(records, NOW)
    assert records == original
    records = [_outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 13:00")]
    original = deepcopy(records)
    current_outage(records, NOW)
    upcoming_outage(records, NOW)
    assert records == original


def test_outage_duration_hours_positive_and_unknown() -> None:
    for hours in (0.5, 1.0, 2.25, 25.0):
        end = datetime(2026, 10, 8, 8, tzinfo=LOCAL) + timedelta(hours=hours)
        outage = Outage(datetime(2026, 10, 8, 8, tzinfo=LOCAL), end, "a", "r")
        assert outage_duration_hours(outage) == pytest.approx(hours)


def test_outage_duration_hours_missing_or_non_positive_is_unknown() -> None:
    start = datetime(2026, 10, 8, 8, tzinfo=LOCAL)
    assert outage_duration_hours(Outage(start, None, "a", "r")) is None
    assert outage_duration_hours(Outage(start, start, "a", "r")) is None
    assert (
        outage_duration_hours(Outage(start, start - timedelta(hours=1), "a", "r"))
        is None
    )
    assert outage_duration_hours(None) is None


def test_current_outage_contains_now_inclusive_bounds() -> None:
    inside = _outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 13:00")
    result = current_outage([inside], NOW)
    assert result is not None
    assert result.start == datetime(2026, 10, 7, 11, tzinfo=LOCAL)
    assert result.end == datetime(2026, 10, 7, 13, tzinfo=LOCAL)
    starts_now = _outage("07/10/2026 12:00", TGIAN_KTHUC="07/10/2026 13:00")
    ends_now = _outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 12:00")
    assert current_outage([starts_now], NOW) is not None
    assert current_outage([ends_now], NOW) is not None


def test_current_outage_outside_window_is_unknown() -> None:
    before = _outage("07/10/2026 13:00", TGIAN_KTHUC="07/10/2026 14:00")
    after = _outage("07/10/2026 09:00", TGIAN_KTHUC="07/10/2026 11:00")
    assert current_outage([before], NOW) is None
    assert current_outage([after], NOW) is None


def test_current_outage_missing_end_is_not_active_forever() -> None:
    record = _outage("07/10/2026 09:00", TGIAN_KTHUC=None)
    assert current_outage([record], NOW) is None
    record.pop("TGIAN_KTHUC")
    assert current_outage([record], NOW) is None


def test_current_outage_ignores_invalid_rows_and_unsorted_input() -> None:
    active = _outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 13:00")
    records = [
        _outage("bad start"),
        _outage("07/10/2026 11:30", TGIAN_KTHUC="bad end"),
        _outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 10:00"),
        None,
        {"TGIAN_BDAU": "07/10/2026 10:00", "TGIAN_KTHUC": "07/10/2026 10:30"},
        active,
    ]
    result = current_outage(records, NOW)
    assert result is not None
    assert result.start == datetime(2026, 10, 7, 11, tzinfo=LOCAL)
    assert current_outage(list(reversed(records)), NOW) == result


def test_current_outage_selection_and_bad_input() -> None:
    earlier = _outage("07/10/2026 10:00", TGIAN_KTHUC="07/10/2026 13:00")
    later = _outage("07/10/2026 11:00", TGIAN_KTHUC="07/10/2026 13:00")
    chosen = current_outage([earlier, later], NOW)
    assert chosen is not None
    assert chosen.start == datetime(2026, 10, 7, 11, tzinfo=LOCAL)
    assert current_outage(None, NOW) is None
    assert current_outage({}, NOW) is None
    assert current_outage([_outage()], NOW.replace(tzinfo=None)) is None


def test_upcoming_outage_within_window_selection() -> None:
    within = _outage("07/10/2026 13:00", TGIAN_KTHUC="07/10/2026 14:00")
    boundary = _outage("08/10/2026 12:00", TGIAN_KTHUC="08/10/2026 13:00")
    beyond = _outage("08/10/2026 12:01", TGIAN_KTHUC="08/10/2026 13:00")
    far = _outage("09/10/2026 08:00", TGIAN_KTHUC="09/10/2026 10:00")
    records = [far, beyond, boundary, within]
    result = upcoming_outage(records, NOW, 24)
    assert result is not None
    assert result.start == datetime(2026, 10, 7, 13, tzinfo=LOCAL)
    assert upcoming_outage([boundary], NOW, 24) is not None
    assert upcoming_outage([beyond], NOW, 24) is None
    assert upcoming_outage([far], NOW, 24) is None
    assert upcoming_outage([within], NOW, 0) is None
    assert upcoming_outage([_outage("07/10/2026 12:00")], NOW, 0) is not None


def test_upcoming_outage_ignores_invalid_rows_and_unsorted_input() -> None:
    soon = _outage("07/10/2026 13:00", TGIAN_KTHUC="07/10/2026 14:00")
    records = [None, _outage("bad"), _outage("01/10/2026 08:00"), soon]
    assert upcoming_outage(records, NOW, 24) == next_outage([soon], NOW)
    assert upcoming_outage(list(reversed(records)), NOW, 24) == next_outage([soon], NOW)


@pytest.mark.parametrize("within", [True, False, 24.0, "24", None, -1])
def test_upcoming_outage_invalid_within_hours_is_unknown(within: Any) -> None:
    assert upcoming_outage([_outage()], NOW, within) is None


def test_upcoming_outage_bad_records_and_naive_now() -> None:
    assert upcoming_outage(None, NOW, 24) is None
    assert upcoming_outage({}, NOW, 24) is None
    assert upcoming_outage([_outage()], NOW.replace(tzinfo=None), 24) is not None
    assert upcoming_outage([_outage()], NOW.astimezone(UTC), 24) is not None


def _monthly_usage(
    value: Any, year: Any = 2026, month: Any = 10, **fields: Any
) -> dict[str, Any]:
    return {"NAM": year, "THANG": month, "DIEN_TTHU": value, **fields}


def _reading(**fields: Any) -> dict[str, Any]:
    return {
        "CHISO_CU": 100.0,
        "CHISO_MOI": 150.0,
        "HSN": 1.0,
        "DIEN_TTHU": 50.0,
        "LOAI_CHISO": "DIEN",
        "BCS": "KT",
        "NGAY_CKY": "06/10/2026",
        **fields,
    }


def _invoice_record(**fields: Any) -> dict[str, Any]:
    return {
        "ID_HDON": "INVOICE-A",
        "NAM": 2026,
        "THANG": 10,
        "KY": 1,
        "SO_KY": 1,
        "TONG_TIEN": 150000,
        "TIEN_GTGT": 10000,
        "TONG_NO": 0,
        "TTRANG_TTOAN": "DATT",
        "NGAY_TTOAN": "07/10/2026",
        "DIEN_TTHU": 50,
        **fields,
    }


def test_month_over_month_totals_and_percent() -> None:
    records = [
        _monthly_usage(100, month=9),
        _monthly_usage(120, month=10),
    ]
    assert month_over_month(records) == {
        "current": 120.0,
        "previous": 100.0,
        "delta": 20.0,
        "percent": 20.0,
    }


def test_month_over_month_sums_same_period_and_ignores_string_whitespace() -> None:
    records = [
        _monthly_usage(10, month=10, KY=1),
        _monthly_usage(" 2.5 ", month=10, KY=2),
        _monthly_usage(5, month=9),
    ]
    assert month_over_month(records) == {
        "current": 12.5,
        "previous": 5.0,
        "delta": 7.5,
        "percent": 150.0,
    }


def test_month_over_month_previous_zero_has_no_percent() -> None:
    records = [
        _monthly_usage(0, month=9),
        _monthly_usage(50, month=10),
    ]
    assert month_over_month(records) == {
        "current": 50.0,
        "previous": 0.0,
        "delta": 50.0,
        "percent": None,
    }


def test_month_over_month_single_period_has_unknown_previous() -> None:
    assert month_over_month([_monthly_usage(10)]) == {
        "current": 10.0,
        "previous": None,
        "delta": None,
        "percent": None,
    }


@pytest.mark.parametrize(
    "records",
    [
        None,
        {},
        [],
        [None],
        [_monthly_usage(1, month=13)],
        [_monthly_usage(1, year=0)],
        [_monthly_usage("NaN")],
        [_monthly_usage(1, THANG=None)],
    ],
)
def test_month_over_month_rejects_bad_or_missing(records: Any) -> None:
    assert month_over_month(records) is None


def test_trailing_average_last_n_and_skips_invalid() -> None:
    records = [
        _monthly_usage(6, month=7),
        _monthly_usage(12, month=8),
        _monthly_usage(24, month=9),
        _monthly_usage("bad", month=10),
        _monthly_usage("NaN", month=11),
        _monthly_usage(99, year=2025, month=13),
    ]
    assert trailing_average(records, 2) == 18.0
    assert trailing_average(records, 12) == 14.0


@pytest.mark.parametrize("months", [0, -1, 121, 1.5, True, "12", None])
def test_trailing_average_invalid_months(months: Any) -> None:
    assert trailing_average([_monthly_usage(10)], months) is None


@pytest.mark.parametrize("records", [None, {}, [], [None], [_monthly_usage("bad")]])
def test_trailing_average_no_usable_records(records: Any) -> None:
    assert trailing_average(records) is None


def test_latest_reading_month_picks_newest() -> None:
    records = [
        _reading(NGAY_CKY="06/09/2026", CHISO_MOI=120.0),
        _reading(
            NGAY_CKY="06/10/2026", CHISO_CU=120.0, CHISO_MOI=150.0, DIEN_TTHU=30.0
        ),
    ]
    assert latest_reading(records) == {
        "period": "06/10/2026",
        "old": 120.0,
        "new": 150.0,
        "multiplier": 1.0,
        "kwh": 30.0,
        "kind": "DIEN",
    }


def test_latest_reading_daily_uses_ngay_and_kind_bcs() -> None:
    record = {
        "CHISO_CU": None,
        "CHISO_MOI": None,
        "HSN": None,
        "DIEN_TTHU": 4.0,
        "BCS": "KT",
        "NGAY": "06/10/2026",
        "THOI_DIEM": "06/10/2026 08:30",
    }
    assert latest_reading([record]) == {
        "period": "06/10/2026 08:30",
        "old": None,
        "new": None,
        "multiplier": None,
        "kwh": 4.0,
        "kind": "KT",
    }


@pytest.mark.parametrize("field", ["CHISO_CU", "CHISO_MOI", "HSN", "DIEN_TTHU"])
def test_latest_reading_rejects_bad_numbers(field: str) -> None:
    assert latest_reading([_reading(**{field: "NaN"})]) is None


@pytest.mark.parametrize(
    "records",
    [None, {}, [], [None], [{"CHISO_MOI": 1}], [_reading(NGAY_CKY="bad")]],
)
def test_latest_reading_unknown(records: Any) -> None:
    assert latest_reading(records) is None


def test_outstanding_helpers_match_invoice_summary() -> None:
    records = [
        _invoice(125000),
        _invoice(50000, ID_HDON="INVOICE-B", TTRANG_TTOAN="DATT"),
        _invoice(
            30000, ID_HDON="INVOICE-C", TTRANG_TTOAN="TTOANMOTPHAN", LOAI_PSINH="TH"
        ),
    ]
    assert outstanding_summary(records) == InvoiceSummary(125000.0, 1)
    assert outstanding_from_active(records) == invoice_summary(records)


@pytest.mark.parametrize("records", [None, {}, [None], [{}], "x"])
def test_outstanding_helpers_unknown(records: Any) -> None:
    assert outstanding_summary(records) == InvoiceSummary(None, None)
    assert outstanding_from_active(records) == InvoiceSummary(None, None)


def test_latest_invoice_normalized_and_latest() -> None:
    older = _invoice_record(NAM=2026, THANG=9, ID_HDON="INVOICE-0")
    newer = _invoice_record(
        NAM=2026, THANG=10, ID_HDON=12345, TTRANG_TTOAN="CHUATT", NGAY_TTOAN=None
    )
    assert latest_invoice([older, newer]) == {
        "id_key": "12345",
        "period": "2026-10",
        "cycle": 1,
        "amount": 150000.0,
        "tax": 10000.0,
        "outstanding": 0.0,
        "status": "CHUATT",
        "status_label": "Chưa thanh toán",
        "paid_date": None,
        "due_date": None,
        "energy": 50.0,
        "energy_unit": "kWh",
    }


def test_latest_invoice_missing_fields_stay_none() -> None:
    record = {"ID_HDON": "INVOICE-A", "NAM": 2026, "THANG": 10}
    assert latest_invoice([record]) == {
        "id_key": "INVOICE-A",
        "period": "2026-10",
        "cycle": None,
        "amount": None,
        "tax": None,
        "outstanding": None,
        "status": None,
        "status_label": None,
        "paid_date": None,
        "due_date": None,
        "energy": None,
        "energy_unit": None,
    }


@pytest.mark.parametrize(
    "records",
    [
        None,
        {},
        [],
        [None],
        [{"ID_HDON": "A"}],
        [{"ID_HDON": 1.5, "NAM": 2026, "THANG": 10}],
    ],
)
def test_latest_invoice_unknown(records: Any) -> None:
    assert latest_invoice(records) is None


@pytest.mark.parametrize("field", ["TONG_TIEN", "TONG_NO", "DIEN_TTHU"])
def test_latest_invoice_rejects_bad_numbers(field: str) -> None:
    assert latest_invoice([_invoice_record(**{field: "NaN"})]) is None


def test_latest_invoice_unknown_status_rejected() -> None:
    assert latest_invoice([_invoice_record(TTRANG_TTOAN="WEIRD")]) is None


def _daily_reading(value: Any = 25, **fields: Any) -> dict[str, Any]:
    return {
        "NGAY": "06/10/2026",
        "THOI_DIEM": "06/10/2026 07:30",
        "BCS": "KT",
        "SO_CTO": "METER-A",
        "CHISO_CU": 1000,
        "CHISO_MOI": 1012.5,
        "HSN": 2,
        "DIEN_TTHU": value,
        **fields,
    }


def _cycle_record(month: Any = 10, index: Any = 1050, **fields: Any) -> dict[str, Any]:
    return {
        "NAM": 2026,
        "THANG": month,
        "SO_KY": 1,
        "CHISO_MOI": index,
        "SO_CTO": "METER-A",
        **fields,
    }


def test_month_label_and_previous_months_cross_year_boundary() -> None:
    assert month_label(date(2026, 10, 7)) == "10-2026"
    assert month_label(date(2026, 1, 1)) == "01-2026"
    assert previous_months(date(2026, 10, 7), 2) == [(2026, 9), (2026, 8)]
    assert previous_months(date(2026, 1, 15), 3) == [(2025, 12), (2025, 11), (2025, 10)]
    assert previous_months(date(2026, 3, 30), 1) == [(2026, 2)]


@pytest.mark.parametrize("value", [None, {}, "", date, 20261007])
def test_month_label_rejects_non_dates(value: Any) -> None:
    assert month_label(value) == ""


@pytest.mark.parametrize(
    "value", [None, {}, [], [None], [_daily("x")], [_daily(1, BCS=None)], "x"]
)
def test_daily_consumption_on_no_data_is_none(value: Any) -> None:
    assert daily_consumption_on(value, date(2026, 10, 6)) is None


@pytest.mark.parametrize("target", [None, {}, "", datetime(2026, 10, 6, tzinfo=UTC)])
def test_daily_consumption_on_requires_a_date(target: Any) -> None:
    assert daily_consumption_on([_daily_reading()], target) is None


def test_daily_consumption_on_selects_the_requested_day() -> None:
    records = [_daily_reading(25), _daily_reading(200, NGAY="05/10/2026")]
    assert daily_consumption_on(records, date(2026, 10, 6)) == 25.0
    assert daily_consumption_on(records, date(2026, 10, 5)) == 200.0
    assert daily_consumption_on(records, date(2026, 10, 7)) is None


def test_daily_consumption_on_does_not_assign_multi_day_total_to_one_day() -> None:
    records = [
        _daily_reading(
            25,
            NGAY=None,
            NGAY_HTHI="05/10/2026 - 06/10/2026",
        )
    ]
    assert daily_consumption_on(records, date(2026, 10, 6)) is None
    assert daily_consumption_on(records, date(2026, 10, 5)) is None


def test_daily_consumption_on_groups_registers_like_daily_summary() -> None:
    records = [
        _daily_reading(1, BCS="BT"),
        _daily_reading(2, BCS="CD"),
        _daily_reading(3, BCS="TD"),
    ]
    assert daily_consumption_on(records, date(2026, 10, 6)) == 6.0
    mixed = [
        _daily_reading(1, BCS="BT"),
        _daily_reading(9, BCS="KT"),
    ]
    assert daily_consumption_on(mixed, date(2026, 10, 6)) == 9.0
    assert (
        daily_consumption_on([_daily_reading(1, BCS="BT")], date(2026, 10, 6)) is None
    )


def test_daily_consumption_on_does_not_fabricate_missing_energy() -> None:
    assert daily_consumption_on([_daily_reading("25")], date(2026, 10, 6)) == 25.0
    without_total = _daily_reading()
    without_total.pop("DIEN_TTHU")
    assert daily_consumption_on([without_total], date(2026, 10, 6)) is None
    scaled = without_total | {"CHISO_MOI": 1020, "HSN": "3"}
    assert daily_consumption_on([scaled], date(2026, 10, 6)) is None
    rolled = without_total | {"CHISO_MOI": 900}
    assert daily_consumption_on([rolled], date(2026, 10, 6)) is None


def test_daily_consumption_on_rejects_bad_numbers_and_duplicate_conflicts() -> None:
    assert daily_consumption_on([_daily_reading("NaN")], date(2026, 10, 6)) is None
    assert daily_consumption_on([_daily_reading(True)], date(2026, 10, 6)) is None
    conflicting = [
        _daily_reading(25),
        _daily_reading(26, THOI_DIEM="06/10/2026 07:30"),
    ]
    assert daily_consumption_on(conflicting, date(2026, 10, 6)) is None


def test_latest_cycle_index_selects_descending_periods() -> None:
    records = [
        _cycle_record(8, 900),
        _cycle_record(10, 1050, KY=1),
        _cycle_record(10, 1060, KY=2),
        _cycle_record(9, 1000),
    ]
    assert latest_cycle_index(records) == 1060.0
    assert latest_cycle_index(records, 0) == 1060.0
    assert latest_cycle_index(records, 1) == 1000.0
    assert latest_cycle_index(records, 2) == 900.0
    assert latest_cycle_index(records, 3) is None


@pytest.mark.parametrize(
    "records",
    [
        None,
        {},
        [],
        [None],
        [{"CHISO_MOI": 1}],
        [_cycle_record(month=13)],
        [_cycle_record(index="NaN")],
    ],
)
def test_latest_cycle_index_failures(records: Any) -> None:
    assert latest_cycle_index(records) is None


@pytest.mark.parametrize("position", [-1, 1.0, True, "0", None, 121])
def test_latest_cycle_index_invalid_position(position: Any) -> None:
    assert latest_cycle_index([_cycle_record()], position) is None


def test_latest_daily_index_prefers_reading_time_stamp() -> None:
    records = [
        _daily_reading(NGAY="05/10/2026", THOI_DIEM="05/10/2026 07:30", CHISO_MOI=1000),
        _daily_reading(
            NGAY="06/10/2026", THOI_DIEM="06/10/2026 07:45", CHISO_MOI=1012.5
        ),
    ]
    assert latest_daily_index(records) == (1012.5, "06/10/2026 07:45")
    without_time = [_daily_reading(THOI_DIEM=None, CHISO_MOI=7)]
    assert latest_daily_index(without_time) == (7.0, "06/10/2026")


@pytest.mark.parametrize(
    "records", [None, {}, [], [None], [{"CHISO_MOI": 1}], [_daily_reading(NGAY="bad")]]
)
def test_latest_daily_index_failures(records: Any) -> None:
    assert latest_daily_index(records) == (None, None)


def test_latest_daily_index_rejects_bad_index_numbers() -> None:
    assert latest_daily_index([_daily_reading(CHISO_MOI="NaN")]) == (None, None)


def test_invoice_for_month_retains_distinct_paid_cycles_with_active() -> None:
    active = [
        _invoice_record(TTRANG_TTOAN="CHUATT", TONG_TIEN=125000),
        _invoice_record(ID_HDON="INVOICE-B", TTRANG_TTOAN="DATT", TONG_TIEN=25000),
    ]
    paid = [_invoice_record(ID_HDON="INVOICE-C", TONG_TIEN=999999)]
    assert invoice_for_month(active, paid, 2026, 10) == 1149999.0


def test_invoice_for_month_falls_back_to_paid_history() -> None:
    active = [_invoice_record(TTRANG_TTOAN=None)]
    paid = [
        _invoice_record(ID_HDON="INVOICE-P", TONG_TIEN=400000, THANG=9),
        _invoice_record(ID_HDON="INVOICE-Q", TONG_TIEN=100000, THANG=9),
    ]
    assert invoice_for_month(active, paid, 2026, 9) == 500000.0
    assert invoice_for_month(active, paid, 2026, 10) is None


@pytest.mark.parametrize(
    ("active", "paid", "year", "month"),
    [
        (None, [], 2026, 10),
        ([], None, 2026, 10),
        ([], [], 2026, 10),
        ([None], [], 2026, 10),
        ([], [{}], 2026, 13),
        ([], [{}], 0, 10),
        ([], [{}], "2026", 10),
        ([], [{}], 2026, True),
        ([_invoice_record(TONG_TIEN="NaN")], [], 2026, 10),
    ],
)
def test_invoice_for_month_unknown(
    active: Any, paid: Any, year: Any, month: Any
) -> None:
    assert invoice_for_month(active, paid, year, month) is None


def test_vn_now_uses_local_calendar_day(monkeypatch: pytest.MonkeyPatch) -> None:
    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            assert tz == LOCAL
            return datetime(2026, 10, 7, 17, 30, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(models, "datetime", Clock)
    assert vn_now() == date(2026, 10, 8)


@pytest.mark.parametrize("count", [-1, True, 1.5, "2", None])
def test_previous_months_invalid_count(count: Any) -> None:
    assert previous_months(date(2026, 1, 1), count) == []


def test_previous_months_empty_and_minimum_date() -> None:
    assert previous_months(date(2026, 1, 1), 0) == []
    assert previous_months(date.min, 2) == []
    assert previous_months(date(1, 2, 1), 3) == [(1, 1)]


@pytest.mark.parametrize("value", INVALID_NUMBERS)
def test_new_model_helpers_reject_ambiguous_numbers(value: Any) -> None:
    assert daily_consumption_on([_daily_reading(value)], date(2026, 10, 6)) is None
    assert latest_daily_index([_daily_reading(CHISO_MOI=value)]) == (None, None)
    assert latest_cycle_index([_cycle_record(index=value)]) is None
    assert invoice_for_month([_invoice_record(TONG_TIEN=value)], [], 2026, 10) is None


def test_latest_daily_index_orders_times_and_months_not_strings() -> None:
    records = [
        _daily_reading(NGAY="30/09/2026", THOI_DIEM="30/09/2026 23:00", CHISO_MOI=1000),
        _daily_reading(NGAY="01/10/2026", THOI_DIEM="01/10/2026 11:00", CHISO_MOI=1015),
        _daily_reading(NGAY="01/10/2026", THOI_DIEM="01/10/2026 09:00", CHISO_MOI=1012),
    ]
    assert latest_daily_index(records) == (1015.0, "01/10/2026 11:00")
    assert latest_daily_index(list(reversed(records))) == (1015.0, "01/10/2026 11:00")
    assert latest_daily_index([_daily_reading(THOI_DIEM="08:30:00")]) == (
        1012.5,
        "08:30:00",
    )


@pytest.mark.parametrize(
    "stamp", [True, 123, "bad", "06/10/2026 25:00", "06/10/2026\ninjected"]
)
def test_latest_daily_index_invalid_timestamp(stamp: Any) -> None:
    assert latest_daily_index([_daily_reading(THOI_DIEM=stamp)]) == (None, None)


def test_latest_daily_index_conflicting_ties_are_unknown() -> None:
    row = _daily_reading()
    assert latest_daily_index([row, row.copy()]) == (1012.5, "06/10/2026 07:30")
    for updates in ({"CHISO_MOI": 99}, {"SO_CTO": "METER-B"}, {"BCS": "BT"}):
        assert latest_daily_index([row, row | updates]) == (None, None)


def test_invoice_for_month_deduplicates_and_preserves_unknown() -> None:
    row = _invoice_record(TONG_TIEN=25)
    assert invoice_for_month([row, row.copy()], [], 2026, 10) == 25.0
    assert invoice_for_month([row, row | {"TONG_TIEN": 30}], [], 2026, 10) is None
    assert invoice_for_month([row | {"TONG_TIEN": None}], [row], 2026, 10) is None
    assert invoice_for_month([row | {"TONG_TIEN": 0}], [], 2026, 10) == 0.0
    assert invoice_for_month([row | {"TTRANG_TTOAN": None}], [row], 2026, 10) is None


def test_new_model_helpers_do_not_mutate_input() -> None:
    rows = [_daily_reading()]
    saved = deepcopy(rows)
    daily_consumption_on(rows, date(2026, 10, 6))
    latest_daily_index(rows)
    assert rows == saved
    invoices = [_invoice_record()]
    saved = deepcopy(invoices)
    invoice_for_month(invoices, invoices, 2026, 10)
    assert invoices == saved
    cycles = [_cycle_record()]
    saved = deepcopy(cycles)
    latest_cycle_index(cycles)
    assert cycles == saved


def test_daily_consumption_is_not_derived_from_consecutive_indices() -> None:
    rows = [
        {
            "NGAY": day,
            "BCS": "KT",
            "SO_CTO": "METER-A",
            "HSN": 2,
            "CHISO_MOI": value,
            "THOI_DIEM": day + " 08:00",
        }
        for day, value in (
            ("04/10/2026", 900),
            ("05/10/2026", 1000),
            ("06/10/2026", 1012.5),
        )
    ]
    original = deepcopy(rows)
    assert daily_consumption_on(rows, date(2026, 10, 6)) is None
    assert daily_consumption_on(rows, date(2026, 10, 5)) is None
    assert daily_consumption_on(rows, date(2026, 10, 4)) is None
    assert daily_consumption_on(rows, date(2026, 10, 7)) is None
    assert rows == original


@pytest.mark.parametrize(
    "updates",
    [
        {"CHISO_MOI": 90},
        {"CHISO_MOI": True},
        {"HSN": None},
        {"HSN": True},
        {"HSN": 0},
        {"HSN": "NaN"},
        {"HSN": 3},
        {"SO_CTO": "METER-B"},
        {"BCS": "BT"},
        {"MA_DDO": "OTHER"},
        {"NGAY": "07/10/2026"},
    ],
)
def test_daily_index_difference_rejects_unverified_predecessors(
    updates: dict[str, Any],
) -> None:
    previous = {
        "NGAY": "05/10/2026",
        "BCS": "KT",
        "SO_CTO": "METER-A",
        "HSN": 2,
        "CHISO_MOI": 100,
    }
    current = previous | {"NGAY": "06/10/2026", "CHISO_MOI": 110} | updates
    assert daily_consumption_on([previous, current], date(2026, 10, 6)) is None


def test_daily_index_tariff_registers_do_not_imply_energy() -> None:
    rows = []
    for register, index, increment in (("BT", 100, 1), ("CD", 200, 2), ("TD", 300, 3)):
        base = {"BCS": register, "SO_CTO": "METER-A", "HSN": 2}
        rows.extend(
            [
                base | {"NGAY": "05/10/2026", "CHISO_MOI": index},
                base | {"NGAY": "06/10/2026", "CHISO_MOI": index + increment},
            ]
        )
    assert daily_consumption_on(rows, date(2026, 10, 6)) is None


@pytest.mark.parametrize("index", [100, 110])
def test_actual_daily_index_schema_without_energy_remains_unknown(index: int) -> None:
    rows = [
        {
            "NGAY": day,
            "THOI_DIEM": day + " 08:00",
            "BCS": "KT",
            "SO_CTO": "METER-A",
            "CHISO_MOI": value,
        }
        for day, value in (("05/10/2026", 100), ("06/10/2026", index))
    ]
    assert daily_consumption_on(rows, date(2026, 10, 6)) is None
    assert latest_daily_index(rows) == (float(index), "06/10/2026 08:00")


@pytest.mark.parametrize("value", [0, -2.5, "7.125"])
def test_daily_consumption_uses_energy_date_not_index_timestamp(value: Any) -> None:
    row = _daily(value, THOI_DIEM="07/10/2026 08:00", CHISO_MOI=9999, HSN=10)
    assert daily_consumption_on([row, deepcopy(row)], date(2026, 10, 6)) == float(value)
    assert daily_consumption_on([row], date(2026, 10, 7)) is None
    assert (
        daily_consumption_on(
            [row | {"NGAY": None, "NGAY_HTHI": None}], date(2026, 10, 7)
        )
        is None
    )


@pytest.mark.parametrize("day", [5, 6, 7])
def test_daily_consumption_multiday_overlap_invalidates_single_day(day: int) -> None:
    interval = _daily(30, NGAY_HTHI="05/10/2026 - 07/10/2026")
    single = _daily(0, NGAY=f"{day:02d}/10/2026", NGAY_HTHI=f"{day:02d}/10/2026")
    assert daily_consumption_on([single, interval], date(2026, 10, day)) is None


def test_monthly_aggregates_share_deduplication_and_correction_semantics() -> None:
    rows = [
        _monthly(10, THANG=9),
        _monthly(20),
        _monthly(-2, KY=2),
        _monthly(4, SO_CTO="METER-B"),
    ]
    rows.extend(deepcopy(rows))
    assert monthly_summary(rows) == PeriodUsage(22.0, "2026-10")
    assert models._period_totals(rows) == {(2026, 9): 10.0, (2026, 10): 22.0}
    assert month_over_month(rows) == {
        "current": 22.0,
        "previous": 10.0,
        "delta": 12.0,
        "percent": 120.0,
    }
    assert trailing_average(rows) == 16.0
    assert trailing_average(list(reversed(rows))) == 16.0


@pytest.mark.parametrize(
    "helper", [models._period_totals, month_over_month, trailing_average]
)
@pytest.mark.parametrize(
    "changes", [{"DIEN_TTHU": 30}, {"metadata": "conflict"}, {"DIEN_TTHU": "20"}]
)
def test_monthly_aggregates_reject_same_identity_conflicts(
    helper: Any, changes: dict[str, Any]
) -> None:
    row = _monthly(20)
    assert helper([_monthly(10, THANG=9), row, row | changes]) is None


@pytest.mark.parametrize(
    "helper", [models._period_totals, month_over_month, trailing_average]
)
@pytest.mark.parametrize("value", [None, True, "bad"])
def test_monthly_aggregates_never_sum_partial_invalid_period(
    helper: Any, value: Any
) -> None:
    rows = [_monthly(10, THANG=9), _monthly(20), _monthly(value, KY=2)]
    assert helper(rows) is None


def test_month_over_month_requires_adjacent_calendar_labels_across_years() -> None:
    rows = [_monthly(10, NAM=2025, THANG=12), _monthly(15, NAM=2026, THANG=1)]
    assert month_over_month(rows) == {
        "current": 15.0,
        "previous": 10.0,
        "delta": 5.0,
        "percent": 50.0,
    }
    rows[0]["THANG"] = 11
    assert month_over_month(rows) == {
        "current": 15.0,
        "previous": None,
        "delta": None,
        "percent": None,
    }
    assert trailing_average(rows) == 12.5


def test_trailing_average_uses_last_twelve_validated_periods_not_row_count() -> None:
    rows = [_monthly(100, NAM=2025, THANG=12)]
    rows.extend(_monthly(month, THANG=month) for month in range(1, 13))
    rows.extend(deepcopy(rows))
    rows.append(_monthly(None, NAM=2027, THANG=1))
    assert trailing_average(rows) == 6.5
    assert trailing_average(rows, 2) == 11.5


def test_latest_reading_monthly_uses_closing_date_and_newer_lower_counter() -> None:
    older = _reading(
        NGAY_DKY="01/09/2026", NGAY_CKY="01/10/2026", SO_CTO="OLD", CHISO_MOI=9000
    )
    newer = _reading(
        NGAY_DKY="30/08/2026", NGAY_CKY="02/10/2026", SO_CTO="NEW", CHISO_MOI=100
    )
    result = latest_reading([newer, older])
    assert result is not None and result["new"] == 100.0
    assert result["period"] == "02/10/2026"


def test_latest_reading_daily_orders_full_timestamp_before_day_or_counter() -> None:
    rows = [
        _daily_reading(THOI_DIEM="06/10/2026 09:00", CHISO_MOI=9000, SO_CTO="OLD"),
        _daily_reading(THOI_DIEM="07/10/2026 08:00", CHISO_MOI=100, SO_CTO="NEW"),
        _daily_reading(THOI_DIEM="06/10/2026 10:00", CHISO_MOI=9001, SO_CTO="OLD"),
    ]
    result = latest_reading(rows)
    assert result is not None and result["new"] == 100.0
    assert result["period"] == "07/10/2026 08:00"
    assert latest_reading(list(reversed(rows))) == result
    same_day = latest_reading([rows[0], rows[2]])
    assert same_day is not None and same_day["new"] == 9001.0
    assert same_day["period"] == "06/10/2026 10:00"


@pytest.mark.parametrize("factory", [_reading, _daily_reading])
@pytest.mark.parametrize(
    "changes",
    [{"SO_CTO": "METER-B"}, {"BCS": "BT"}, {"LOAI_CHISO": "TD"}, {"CHISO_MOI": 9000}],
)
def test_latest_reading_ties_require_one_verified_counter(
    factory: Any, changes: dict[str, Any]
) -> None:
    row = factory(SO_CTO="METER-A")
    assert latest_reading([row, deepcopy(row)]) == latest_reading([row])
    assert latest_reading([row, row | changes]) is None


def test_latest_cycle_index_as_of_filters_month_labels_and_future_boundaries() -> None:
    rows = [
        _cycle_record(8, 800, NGAY_CKY="31/08/2026"),
        _cycle_record(9, 900, NGAY_CKY="05/10/2026"),
        _cycle_record(9, 950, KY=2, NGAY_CKY="09/10/2026"),
        _cycle_record(10, 1000, NGAY_CKY="06/10/2026"),
        _cycle_record(11, "bad", NGAY_CKY="30/11/2026"),
    ]
    assert latest_cycle_index(rows, as_of=date(2026, 10, 7)) == 900.0
    assert latest_cycle_index(rows, 1, as_of=date(2026, 10, 7)) == 800.0
    assert latest_cycle_index(rows, 2, as_of=date(2026, 10, 7)) is None
    assert latest_cycle_index(rows, as_of=date(2026, 10, 5)) == 900.0


def test_latest_cycle_index_chooses_newer_replacement_not_larger_counter() -> None:
    rows = [
        _cycle_record(
            9, 9000, SO_CTO="OLD", NGAY_DKY="01/09/2026", NGAY_CKY="15/09/2026"
        ),
        _cycle_record(
            9, 100, SO_CTO="NEW", NGAY_DKY="15/09/2026", NGAY_CKY="30/09/2026"
        ),
    ]
    assert latest_cycle_index(rows, as_of=date(2026, 10, 7)) == 100.0
    assert latest_cycle_index(list(reversed(rows))) == 100.0
    assert latest_cycle_index(rows + [deepcopy(rows[1])]) == 100.0
    fallback = [
        row | {"KY": cycle, "NGAY_CKY": None, "NGAY_DKY": None}
        for cycle, row in enumerate(rows, 1)
    ]
    assert latest_cycle_index(fallback) == 100.0


@pytest.mark.parametrize(
    "changes",
    [
        {"SO_CTO": "METER-B"},
        {"BCS": "BT"},
        {"LOAI_CHISO": "TD"},
        {"CHISO_MOI": 9000},
        {"metadata": "conflict"},
    ],
)
def test_latest_cycle_index_ambiguous_ties_are_unknown(changes: dict[str, Any]) -> None:
    row = _cycle_record(9, 100, BCS="KT", LOAI_CHISO="KT", NGAY_CKY="30/09/2026")
    assert latest_cycle_index([row, row | changes], as_of=date(2026, 10, 7)) is None
    fallback = row | {"NGAY_CKY": None}
    assert latest_cycle_index([fallback, fallback | changes]) is None


def test_latest_cycle_index_chronological_boundary_priority_and_year_rollover() -> None:
    rows = [
        _cycle_record(12, 100, NAM=2025, NGAY_CKY="31/12/2025"),
        _cycle_record(1, 1),
    ]
    assert latest_cycle_index(rows, as_of=date(2026, 1, 1)) == 100.0
    rows = [
        _cycle_record(8, 80, NGAY_CKY="30/09/2026"),
        _cycle_record(9, 90, NGAY_CKY="29/09/2026"),
    ]
    assert latest_cycle_index(rows, as_of=date(2026, 10, 7)) == 80.0
    assert (
        latest_cycle_index(rows + [_cycle_record(9, 95, KY=2)], as_of=date(2026, 10, 7))
        == 80.0
    )


@pytest.mark.parametrize(
    "as_of", [True, "2026-10-07", datetime(2026, 10, 7, tzinfo=UTC), {}]
)
def test_latest_cycle_index_requires_calendar_date_as_of(as_of: Any) -> None:
    assert latest_cycle_index([_cycle_record(9)], as_of=as_of) is None


@pytest.mark.parametrize(
    "fields",
    [
        {"NGAY_CKY": "bad"},
        {"NGAY_DKY": "01/10/2026", "NGAY_CKY": "30/09/2026"},
        {"KY": True},
        {"SO_KY": 0},
    ],
)
def test_latest_cycle_index_invalid_cycle_metadata_is_unknown(
    fields: dict[str, Any],
) -> None:
    assert (
        latest_cycle_index([_cycle_record(9, **fields)], as_of=date(2026, 10, 7))
        is None
    )


def test_invoice_month_reconciles_exact_identity_not_cycle_or_payment_date() -> None:
    active = [_invoice_record(TTRANG_TTOAN="CHUATT", TONG_TIEN=100, KY=2)]
    overlap = active[0] | {"TTRANG_TTOAN": "DATT", "TONG_TIEN": 999}
    history = _invoice_record(
        ID_HDON="INVOICE-B", TONG_TIEN=50, KY=1, NGAY_TTOAN="01/11/2026"
    )
    history.pop("TTRANG_TTOAN")
    assert (
        invoice_for_month(active, [overlap, history, deepcopy(history)], 2026, 10)
        == 150.0
    )
    assert invoice_for_month(active, [overlap, history], 2026, 11) is None
    assert latest_invoice([history])["status"] is None
    assert latest_invoice([history])["status_label"] is None


def test_invoice_month_active_overlap_removes_old_history_month_label() -> None:
    row = _invoice_record(TONG_TIEN=100)
    assert invoice_for_month([row], [row | {"THANG": 9}], 2026, 9) is None
    assert invoice_for_month([row], [row | {"THANG": 9}], 2026, 10) == 100.0


def test_invoice_month_raw_adjustment_pairs_are_distinct_and_deduplicated() -> None:
    row = _invoice_record(TONG_TIEN=10, ID_HDON="001", ID_HDON_DC=None)
    rows = [
        row,
        row | {"ID_HDON_DC": "ADJUSTED", "TONG_TIEN": 5},
        row | {"ID_HDON": 1, "TONG_TIEN": 2},
    ]
    assert invoice_for_month(rows, deepcopy(rows), 2026, 10) == 17.0
    assert invoice_for_month([row], [row, row | {"TONG_TIEN": 20}], 2026, 10) is None


@pytest.mark.parametrize("identifier", [None, "", True, [], 1.5])
@pytest.mark.parametrize("source", ["active", "paid"])
def test_invoice_month_requires_identity(identifier: Any, source: str) -> None:
    rows = [_invoice_record(ID_HDON=identifier)]
    assert (
        invoice_for_month(
            rows if source == "active" else [],
            rows if source == "paid" else [],
            2026,
            10,
        )
        is None
    )


@pytest.mark.parametrize(
    "fields",
    [
        {"TTRANG_TTOAN": "DAHT"},
        {"TTRANG_TTOAN": "CHUAHT"},
        {"LOAI_PSINH": "TH"},
        {"TTRANG_TTOAN": "UNKNOWN"},
    ],
)
@pytest.mark.parametrize("source", ["active", "paid"])
def test_invoice_month_rejects_unsupported_refunds_cancellations(
    fields: dict[str, Any], source: str
) -> None:
    rows = [_invoice_record(**fields)]
    assert (
        invoice_for_month(
            rows if source == "active" else [],
            rows if source == "paid" else [],
            2026,
            10,
        )
        is None
    )


@pytest.mark.parametrize(
    "paid_date", [None, "", "bad", "31/02/2026", True, "07/10/2026 25:00"]
)
def test_invoice_history_without_status_requires_valid_payment_date(
    paid_date: Any,
) -> None:
    row = _invoice_record(NGAY_TTOAN=paid_date)
    row.pop("TTRANG_TTOAN")
    assert invoice_for_month([], [row], 2026, 10) is None


@pytest.mark.parametrize("paid_date", ["07/10/2026", "07/10/2026 08:30"])
def test_invoice_history_payment_date_allows_amount_without_fabricating_status(
    paid_date: str,
) -> None:
    row = _invoice_record(NGAY_TTOAN=paid_date, TONG_TIEN=0)
    row.pop("TTRANG_TTOAN")
    assert invoice_for_month([], [row], 2026, 10) == 0.0
    normalized = latest_invoice([row])
    assert normalized["status"] is None and normalized["status_label"] is None
    assert invoice_for_month([], [row | {"TONG_TIEN": None}], 2026, 10) is None


def test_customer_month_energy_counts_owned_distinct_points_once() -> None:
    point = {"MA_DDO": "POINT-A", "MA_KHANG": "OWNER"}
    points = [
        point,
        deepcopy(point),
        point | {"display": "another name"},
        {"MA_DDO": "POINT-B"},
    ]
    monthly = {
        "POINT-A": [_monthly(10, MA_DDO="POINT-A", MA_KHANG="OWNER")],
        "POINT-B": [_monthly(-2)],
        "UNOWNED": [_monthly(1000)],
    }
    readings = {
        "POINT-A": [_monthly(900, BCS="KT")],
        "POINT-B": [_monthly(900, BCS="KT")],
    }
    original = deepcopy((points, monthly, readings))
    assert customer_month_energy(points, monthly, readings, 2026, 10) == 8.0
    assert customer_month_energy(points, monthly, readings, 2026, 9) is None
    assert (points, monthly, readings) == original


def test_customer_month_energy_primary_zero_and_invalid_never_replaced_by_index() -> (
    None
):
    points = [{"MA_DDO": "POINT-A"}]
    readings = {"POINT-A": [_monthly(100, BCS="KT")]}
    assert (
        customer_month_energy(points, {"POINT-A": [_monthly(0)]}, readings, 2026, 10)
        == 0.0
    )
    assert (
        customer_month_energy(points, {"POINT-A": [_monthly(None)]}, readings, 2026, 10)
        is None
    )
    assert (
        customer_month_energy(
            points + [{"MA_DDO": "POINT-B"}],
            {"POINT-A": [_monthly(1)]},
            readings,
            2026,
            10,
        )
        is None
    )


def test_customer_month_energy_fallback_uses_canonical_meter_register_cycle_groups() -> (
    None
):
    points = [{"MA_DDO": "POINT-A"}, {"MA_DDO": "POINT-B"}]
    rows = [
        _monthly(10, BCS="KT", NGAY_DKY="01/09/2026", NGAY_CKY="30/09/2026", THANG=9),
        *[
            _monthly(
                100, BCS=register, NGAY_DKY="01/09/2026", NGAY_CKY="30/09/2026", THANG=9
            )
            for register in ("BT", "CD", "TD")
        ],
        *[
            _monthly(value, SO_CTO="METER-B", BCS=register, THANG=9)
            for value, register in ((2, "BT"), (-1, "CD"), (3, "TD"))
        ],
        _monthly(5, BCS="KT", KY=2, THANG=9),
    ]
    rows.extend(deepcopy(rows))
    assert (
        customer_month_energy(
            points, {"POINT-B": [_monthly(1, THANG=9)]}, {"POINT-A": rows}, 2026, 9
        )
        == 20.0
    )
    rows[0]["DIEN_TTHU"] = None
    assert (
        customer_month_energy(
            points, {"POINT-B": [_monthly(1, THANG=9)]}, {"POINT-A": rows}, 2026, 9
        )
        is None
    )


def test_customer_month_energy_fallback_accepts_explicit_reading_register_only() -> (
    None
):
    points = [{"MA_DDO": "POINT-A"}]
    row = _monthly(5, LOAI_CHISO="KT")
    assert customer_month_energy(points, {}, {"POINT-A": [row]}, 2026, 10) == 5.0
    assert (
        customer_month_energy(points, {}, {"POINT-A": [_monthly(5)]}, 2026, 10) is None
    )
    assert (
        customer_month_energy(
            points, {}, {"POINT-A": [row | {"BCS": "UNKNOWN"}]}, 2026, 10
        )
        is None
    )


@pytest.mark.parametrize(
    "rows",
    [
        [_monthly(1, BCS="BT")],
        [_monthly(5, BCS="KT"), _monthly(None, BCS="BT")],
        [_monthly(5, BCS="KT"), _monthly(6, BCS="KT")],
        [_monthly(5, BCS="KT", SO_CTO=None), _monthly(6, BCS="KT")],
        [_monthly(5, BCS="KT", KY=None), _monthly(6, BCS="KT", KY=2)],
        [
            _monthly(5, BCS="KT", NGAY_CKY="30/10/2026"),
            _monthly(1, BCS="BT", NGAY_CKY="31/10/2026"),
        ],
    ],
)
def test_customer_month_energy_fallback_rejects_ambiguous_or_partial_groups(
    rows: list[dict[str, Any]],
) -> None:
    assert (
        customer_month_energy([{"MA_DDO": "POINT-A"}], {}, {"POINT-A": rows}, 2026, 10)
        is None
    )


@pytest.mark.parametrize(
    "rows",
    [
        [_monthly(1, MA_DDO="OTHER")],
        [_monthly(1, MA_KHANG="OTHER")],
        [_monthly(1, MA_DVIQLY="OTHER")],
    ],
)
def test_customer_month_energy_rejects_foreign_ownership(
    rows: list[dict[str, Any]],
) -> None:
    points = [{"MA_DDO": "POINT-A", "MA_KHANG": "OWNER", "MA_DVIQLY": "UNIT"}]
    assert customer_month_energy(points, {"POINT-A": rows}, {}, 2026, 10) is None
    assert customer_month_energy(points, {}, {"POINT-A": rows}, 2026, 10) is None


@pytest.mark.parametrize(
    "points",
    [
        [],
        None,
        {},
        [None],
        [{"MA_DDO": None}],
        [{"MA_DDO": ""}],
        [
            {"MA_DDO": "POINT-A", "MA_KHANG": "OWNER"},
            {"MA_DDO": "POINT-A", "MA_KHANG": "OTHER"},
        ],
    ],
)
def test_customer_month_energy_requires_owned_points(points: Any) -> None:
    assert (
        customer_month_energy(points, {"POINT-A": [_monthly(1)]}, {}, 2026, 10) is None
    )


@pytest.mark.parametrize("year,month", [(True, 10), ("2026", 10), (2026, 13), (0, 10)])
def test_customer_month_energy_requires_valid_month_label(
    year: Any, month: Any
) -> None:
    assert (
        customer_month_energy(
            [{"MA_DDO": "POINT-A"}], {"POINT-A": [_monthly(1)]}, {}, year, month
        )
        is None
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        (1, "1"),
        (123, "123"),
        (10**128 - 1, "9" * 128),
        ("123", "123"),
        ("00123", "00123"),
        ("INVOICE-A_1.2", "INVOICE-A_1.2"),
        ("A" * 128, "A" * 128),
    ],
)
def test_month_invoice_identity_matches_api_canonical_id(
    raw: Any, expected: str
) -> None:
    assert models._invoice_id(raw) == expected
    assert models._invoice_key({"ID_HDON": raw}) == (expected, None)
    assert models._invoice_key({"ID_HDON": raw, "ID_HDON_DC": ""}) == (expected, None)
    assert models._invoice_key({"ID_HDON": raw, "ID_HDON_DC": 456}) == (expected, "456")


@pytest.mark.parametrize(
    "raw",
    [
        None,
        True,
        False,
        0,
        -1,
        1.0,
        10**128,
        float("inf"),
        float("nan"),
        Decimal(123),
        [],
        {},
        "",
        "0",
        "000",
        "A" * 129,
        " INVOICE-A",
        "INVOICE-A ",
        "INVOICE A",
        "..",
        "../file",
        "A/file",
        "id\n",
        "１２３",
    ],
)
def test_month_invoice_invalid_id_is_unknown_not_coerced(raw: Any) -> None:
    assert models._invoice_id(raw) is None
    row = _invoice_record(ID_HDON=raw)
    assert invoice_for_month([row], [], 2026, 10) is None
    assert invoice_for_month([], [row], 2026, 10) is None
    if raw is not None and raw != "":
        adjusted = _invoice_record(ID_HDON_DC=raw)
        assert models._invoice_key(adjusted) is None
        assert invoice_for_month([adjusted], [], 2026, 10) is None
        assert invoice_for_month([], [adjusted], 2026, 10) is None


def test_month_invoice_canonical_overlap_active_wins_and_keeps_distinct_paid_cycles() -> (
    None
):
    active = _invoice_record(
        ID_HDON="123", ID_HDON_DC="", TTRANG_TTOAN="CHUATT", TONG_TIEN=100, KY=2
    )
    paid = [
        active
        | {
            "ID_HDON": 123,
            "ID_HDON_DC": None,
            "TTRANG_TTOAN": "DATT",
            "TONG_TIEN": 999,
        },
        _invoice_record(ID_HDON=124, TTRANG_TTOAN=None, TONG_TIEN=50, KY=1),
        _invoice_record(ID_HDON=123, ID_HDON_DC=456, TONG_TIEN=10, KY=3),
    ]
    original = deepcopy((active, paid))
    assert invoice_for_month([active], paid, 2026, 10) == 160.0
    assert invoice_for_month([active], list(reversed(paid)), 2026, 10) == 160.0
    assert invoice_for_month([active | {"TONG_TIEN": 0}], paid, 2026, 10) == 60.0
    assert invoice_for_month([active | {"TONG_TIEN": None}], paid, 2026, 10) is None
    assert invoice_for_month([active | {"TTRANG_TTOAN": None}], paid, 2026, 10) is None
    assert (active, paid) == original


@pytest.mark.parametrize("source", ["active", "paid"])
@pytest.mark.parametrize("adjusted", [None, "", 456, "456"])
def test_month_invoice_same_source_canonical_duplicates_count_once(
    source: str, adjusted: Any
) -> None:
    row = _invoice_record(ID_HDON=123, ID_HDON_DC=adjusted, TONG_TIEN=25)
    normalized_adjustment = None if adjusted in (None, "") else "456"
    duplicate = row | {"ID_HDON": "123", "ID_HDON_DC": normalized_adjustment}
    rows = [row, deepcopy(row), duplicate]
    if normalized_adjustment is None:
        rows.append(
            {key: value for key, value in duplicate.items() if key != "ID_HDON_DC"}
        )
    original = deepcopy(rows)
    assert (
        invoice_for_month(
            rows if source == "active" else [],
            rows if source == "paid" else [],
            2026,
            10,
        )
        == 25.0
    )
    assert rows == original


@pytest.mark.parametrize("source", ["active", "paid"])
@pytest.mark.parametrize(
    "changes",
    [
        {"TONG_TIEN": 30},
        {"TONG_TIEN": "25"},
        {"TTRANG_TTOAN": "CHUATT"},
        {"metadata": {"value": True}},
        {"THANG": 9},
    ],
)
def test_month_invoice_canonical_identity_keeps_nonidentity_conflicts_unknown(
    source: str, changes: dict[str, Any]
) -> None:
    row = _invoice_record(
        ID_HDON=123, ID_HDON_DC=None, TONG_TIEN=25, metadata={"value": 1}
    )
    duplicate = row | {"ID_HDON": "123", "ID_HDON_DC": ""} | changes
    rows = [row, duplicate]
    assert (
        invoice_for_month(
            rows if source == "active" else [],
            rows if source == "paid" else [],
            2026,
            10,
        )
        is None
    )
    assert invoice_for_month([row], rows, 2026, 10) is None


def test_month_invoice_canonical_adjustments_and_zero_padded_originals_stay_distinct() -> (
    None
):
    row = _invoice_record(ID_HDON=123, ID_HDON_DC=456, TONG_TIEN=10)
    active = [row | {"ID_HDON": "123", "ID_HDON_DC": "456", "TONG_TIEN": 15}]
    paid = [
        row,
        row | {"ID_HDON_DC": 789, "TONG_TIEN": 20},
        row | {"ID_HDON_DC": None, "TONG_TIEN": 30},
        row | {"ID_HDON": "00123", "TONG_TIEN": 40},
        row | {"ID_HDON": 321, "TONG_TIEN": 50},
    ]
    assert invoice_for_month(active, paid, 2026, 10) == 155.0
    assert models._invoice_key(row) != models._invoice_key(row | {"ID_HDON_DC": "0456"})
    assert (
        invoice_for_month(active, paid + [_invoice_record(ID_HDON=None)], 2026, 10)
        is None
    )


def test_month_invoice_canonical_overlap_uses_active_month_label() -> None:
    active = _invoice_record(ID_HDON="123", ID_HDON_DC="", TONG_TIEN=20)
    paid = active | {"ID_HDON": 123, "ID_HDON_DC": None, "THANG": 9, "TONG_TIEN": 10}
    assert invoice_for_month([active], [paid], 2026, 9) is None
    assert invoice_for_month([active], [paid], 2026, 10) == 20.0


@pytest.mark.parametrize(
    "closing",
    ["30/09/2026", "30/09/2026 23:45", "30/09/2026 23:45:12"],
)
def test_monthly_reading_closing_precision_and_date_only_display_are_preserved(
    closing: str,
) -> None:
    row = _reading(
        NAM=2026,
        THANG=9,
        NGAY_DKY="01/09/2026 08:00:01",
        NGAY_CKY=closing,
        THOI_DIEM="07/10/2026 12:00",
    )
    original = deepcopy(row)
    result = latest_reading([row])
    assert result is not None and result["period"] == closing
    assert result["new"] == 150.0
    assert latest_cycle_index([row], as_of=date(2026, 10, 7)) == 150.0
    assert models._reading_period(row) == models._reading_stamp({"THOI_DIEM": closing})
    assert row == original


@pytest.mark.parametrize("closing", ["30/09/2026 08:31", "30/09/2026 08:30:01"])
def test_monthly_same_day_later_closing_selects_lower_replacement_counter(
    closing: str,
) -> None:
    old = _cycle_record(
        9,
        9000,
        NGAY_DKY="01/09/2026 08:00",
        NGAY_CKY="30/09/2026 08:30",
        SO_CTO="OLD",
        BCS="KT",
    )
    new = _cycle_record(
        9, 10, NGAY_DKY="30/09/2026 08:30:00", NGAY_CKY=closing, SO_CTO="NEW", BCS="KT"
    )
    rows = [old, new, deepcopy(new)]
    for ordered in (rows, list(reversed(rows))):
        assert latest_cycle_index(ordered, as_of=date(2026, 10, 7)) == 10.0
        result = latest_reading(ordered)
        assert result is not None and result["new"] == 10.0
        assert result["period"] == closing


def test_monthly_closing_times_sort_chronologically_across_years() -> None:
    rows = [
        _cycle_record(
            12,
            9000,
            NAM=2025,
            NGAY_DKY="01/12/2025 08:00",
            NGAY_CKY="31/12/2025 23:59:59",
        ),
        _cycle_record(
            1,
            20,
            NAM=2026,
            NGAY_DKY="31/12/2025 23:59:59",
            NGAY_CKY="01/01/2026 00:00:01",
        ),
    ]
    result = latest_reading(rows)
    assert result is not None and result["new"] == 20.0
    assert result["period"] == "01/01/2026 00:00:01"
    assert latest_cycle_index(rows, as_of=date(2026, 2, 1)) == 20.0
    assert latest_cycle_index(rows, 1, as_of=date(2026, 2, 1)) == 9000.0
    assert latest_cycle_index(rows, as_of=date(2026, 1, 1)) == 9000.0


def test_monthly_as_of_is_inclusive_of_whole_vietnam_day_not_midnight() -> None:
    row = _cycle_record(9, 9000, NGAY_CKY="07/10/2026 00:00:00")
    rows = [
        row,
        row | {"CHISO_MOI": 10, "NGAY_CKY": "07/10/2026 23:59:59"},
        row | {"CHISO_MOI": 20, "NGAY_CKY": "08/10/2026 00:00:00"},
        row | {"THANG": 10, "CHISO_MOI": 30, "NGAY_CKY": "07/10/2026 23:59:59"},
    ]
    assert latest_cycle_index(rows, as_of=date(2026, 10, 7)) == 10.0
    assert latest_cycle_index(rows, as_of=date(2026, 10, 8)) == 20.0
    assert latest_cycle_index(rows, as_of=date(2026, 10, 6)) is None


@pytest.mark.parametrize(
    "changes", [{"BCS": "BT"}, {"SO_CTO": "OTHER"}, {"CHISO_MOI": 9000}]
)
def test_monthly_exact_timestamp_ties_remain_ambiguous(changes: dict[str, Any]) -> None:
    row = _cycle_record(9, 10, BCS="KT", NGAY_CKY="30/09/2026 08:30:01")
    assert latest_cycle_index([row, deepcopy(row)]) == 10.0
    assert latest_reading([row, deepcopy(row)])["new"] == 10.0
    assert latest_cycle_index([row, row | changes]) is None
    assert latest_reading([row, row | changes]) is None


@pytest.mark.parametrize(
    "stamp",
    [
        True,
        20260930,
        {},
        [],
        "bad",
        "31/02/2026 08:30",
        "29/02/2025 08:30:01",
        "30/09/2026 24:00",
        "30/09/2026 08:60",
        "30/09/2026 08:30:60",
        "30/09/26 08:30",
        "3/09/2026 08:30",
        "30/9/2026 08:30",
        "30/09/2026 8:30",
        "30/09/2026 08:3",
        "30/09/2026 08:30:1",
        "30/09/2026 08:30:00.1",
        "30/09/2026 08:30Z",
        "30/09/2026 08:30+07:00",
        "2026-09-30T08:30:00+07:00",
        "30/09/2026  08:30",
        "30/09/2026\t08:30",
        " 30/09/2026 08:30",
        "30/09/2026 08:30 ",
        "30/09/2026 08:30\n",
        "30/09/2026 - 01/10/2026",
    ],
)
def test_monthly_and_daily_timestamp_validation_is_shared_and_strict(
    stamp: Any,
) -> None:
    row = _cycle_record(9, NGAY_DKY="01/09/2026", NGAY_CKY=stamp)
    assert latest_reading([row]) is None
    assert latest_cycle_index([row], as_of=date(2026, 10, 7)) is None
    assert models._reading_stamp({"THOI_DIEM": stamp}) is None
    assert models._date_time(stamp) is None
    assert (
        latest_reading([row | {"NGAY_DKY": stamp, "NGAY_CKY": "30/09/2026 12:00"}])
        is None
    )
    assert (
        latest_cycle_index([row | {"NGAY_DKY": stamp, "NGAY_CKY": "30/09/2026 12:00"}])
        is None
    )


@pytest.mark.parametrize(
    "opening,closing",
    [
        ("30/09/2026 08:30:01", "30/09/2026 08:30"),
        ("30/09/2026 08:31", "30/09/2026 08:30:59"),
        ("01/10/2026 00:00:00", "30/09/2026 23:59:59"),
        ("01/01/2026", "31/12/2025 23:59:59"),
        ("01/01/2026 00:00:01", "31/12/2025"),
    ],
)
def test_monthly_reversed_datetime_bounds_are_unknown(
    opening: str, closing: str
) -> None:
    row = _cycle_record(9, NGAY_DKY=opening, NGAY_CKY=closing)
    assert latest_reading([row]) is None
    assert latest_cycle_index([row]) is None
    assert (
        customer_month_energy(
            [{"MA_DDO": "POINT-A"}],
            {},
            {"POINT-A": [row | {"DIEN_TTHU": 1, "BCS": "KT"}]},
            2026,
            9,
        )
        is None
    )


@pytest.mark.parametrize(
    "opening,closing",
    [
        ("30/09/2026 08:30", "30/09/2026 08:30:00"),
        ("30/09/2026", "30/09/2026 08:30:01"),
        ("30/09/2026 08:30:01", "30/09/2026"),
        ("29/02/2024 08:30", "29/02/2024 08:31:01"),
    ],
)
def test_monthly_date_and_time_bounds_keep_available_precision(
    opening: str, closing: str
) -> None:
    row = _cycle_record(9, NGAY_DKY=opening, NGAY_CKY=closing)
    result = latest_reading([row])
    assert result is not None and result["period"] == closing
    assert latest_cycle_index([row]) == 1050.0
    assert (
        customer_month_energy(
            [{"MA_DDO": "POINT-A"}],
            {},
            {"POINT-A": [row | {"DIEN_TTHU": 1, "BCS": "KT"}]},
            2026,
            9,
        )
        == 1.0
    )


def test_monthly_reading_time_only_closing_does_not_borrow_an_arbitrary_date() -> None:
    row = _cycle_record(
        9, NGAY="30/09/2026", NGAY_DKY="01/09/2026", NGAY_CKY="08:30:01"
    )
    assert latest_reading([row]) is None
    assert latest_cycle_index([row]) is None
    assert models._reading_stamp({"NGAY": "30/09/2026", "THOI_DIEM": "08:30:01"}) == (
        datetime(2026, 9, 30, 8, 30, 1, tzinfo=LOCAL),
        "08:30:01",
    )
