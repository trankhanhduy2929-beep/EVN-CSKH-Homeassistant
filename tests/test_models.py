import importlib.util
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
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
