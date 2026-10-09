from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any, cast
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant import loader
from homeassistant.bootstrap import async_load_base_functionality
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntries,
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.selector import NumberSelector, SelectSelector, TextSelector
from homeassistant.helpers.translation import async_get_translations
from homeassistant.setup import async_setup_component

from custom_components import evn_cskh as integration
from custom_components.evn_cskh import config_flow, sensor
from custom_components.evn_cskh.api import (
    Customer,
    EvnAuthError,
    EvnConnectionError,
    EvnError,
    EvnResponseError,
    EvnUserActionRequired,
    Snapshot,
    TokenState,
)
from custom_components.evn_cskh.const import (
    CONF_CUSTOMERS,
    CONF_DEVICE_ID,
    CONF_SELECTED_CUSTOMERS,
    CONF_TOKENS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    NAME,
    account_unique_id,
)
from custom_components.evn_cskh.coordinator import EvnConfigEntry, customer_key

ROOT = Path(__file__).resolve().parents[1]
DEVICE_ID = "0123456789abcdef"
POINT = "RUNTIME-POINT"
INVOICE_ID = "DUMMY-PRIVATE-INVOICE"
PAID_INVOICE_ID = "DUMMY-PAID-INVOICE"
OLDER_INVOICE_ID = "DUMMY-OLDER-INVOICE"
CANONICAL_INVOICE_ID = 10**30
CUSTOMER = Customer(
    "RUNTIME-CUSTOMER", "RUNTIME-UNIT", "DUMMY PRIVATE NAME", "DUMMY PRIVATE CONTRACT"
)
IDENTITY = {
    CONF_USERNAME: "runtime-offline-user",
    CONF_PASSWORD: "runtime-offline-password",
}
TOKENS = TokenState("runtime-offline-access", "runtime-offline-refresh")
ROTATED_TOKENS = TokenState(
    "runtime-rotated-access",
    "runtime-rotated-refresh",
    CUSTOMER.code,
    CUSTOMER.management_unit,
)
FETCHED_AT = datetime(2026, 10, 7, 5, tzinfo=UTC)
PROTECTED = (
    DEVICE_ID,
    *IDENTITY.values(),
    TOKENS.access_token,
    TOKENS.refresh_token,
    ROTATED_TOKENS.access_token,
    ROTATED_TOKENS.refresh_token,
    CUSTOMER.code,
    CUSTOMER.management_unit,
    CUSTOMER.name,
    CUSTOMER.contract,
    "DUMMY PRIVATE ADDRESS",
    INVOICE_ID,
    PAID_INVOICE_ID,
    OLDER_INVOICE_ID,
    str(CANONICAL_INVOICE_ID),
)
NAMES = {
    "en": {
        "monthly_energy": f"Latest monthly energy {POINT}",
        "prev_month_energy": f"Previous month energy {POINT}",
        "average_12m_energy": f"Average monthly energy over 12 months {POINT}",
        "month_over_month": f"Month-over-month change {POINT}",
        "daily_energy": f"Latest interval energy {POINT}",
        "meter_reading": f"Latest meter index {POINT}",
        "meter_multiplier": f"Meter multiplier {POINT}",
        "meter_read_date": f"Meter read date {POINT}",
        "outstanding_amount": "Outstanding amount",
        "outstanding_count": "Outstanding invoice count",
        "latest_invoice_amount": "Latest invoice amount",
        "latest_invoice_status": "Latest invoice status",
        "paid_invoice_count": "Paid invoice count",
        "next_outage": "Next scheduled outage",
        "next_outage_end": "Scheduled restoration time",
        "next_outage_duration": "Outage duration (hours)",
        "next_outage_area": "Outage area",
        "next_outage_reason": "Outage reason",
        "outage_count": "Scheduled outage count",
        "fetched_at": "Last successful update",
        "current_provisional_index": "Provisional index",
        "previous_cycle_final_index": "Previous cycle final index",
        "consumption_today": "Energy consumed today",
        "consumption_yesterday": "Energy consumed yesterday",
        "consumption_two_days_ago": "Energy consumed two days ago",
        "current_period_detail": "Current period",
        "invoice_year": "Invoice year",
        "invoice_this_period": "Invoice this period",
        "invoice_prev_period": "Invoice previous period",
        "invoice_prev_prev_period": "Invoice two periods ago",
        "consumption_this_period": "Energy this period",
        "consumption_prev_period": "Energy previous period",
        "consumption_prev_prev_period": "Energy two periods ago",
        "next_update": "Next update",
    },
    "vi": {
        "monthly_energy": f"Điện năng tháng gần nhất {POINT}",
        "prev_month_energy": f"Điện năng tháng trước {POINT}",
        "average_12m_energy": f"Điện năng trung bình 12 tháng {POINT}",
        "month_over_month": f"Thay đổi so với tháng trước {POINT}",
        "daily_energy": f"Điện năng khoảng gần nhất {POINT}",
        "meter_reading": f"Chỉ số công tơ gần nhất {POINT}",
        "meter_multiplier": f"Hệ số nhân công tơ {POINT}",
        "meter_read_date": f"Ngày đọc chỉ số công tơ {POINT}",
        "outstanding_amount": "Tiền còn nợ",
        "outstanding_count": "Số hóa đơn chưa thanh toán",
        "latest_invoice_amount": "Số tiền hóa đơn gần nhất",
        "latest_invoice_status": "Trạng thái hóa đơn gần nhất",
        "paid_invoice_count": "Số hóa đơn đã thanh toán",
        "next_outage": "Lịch ngừng cấp điện tiếp theo",
        "next_outage_end": "Giờ cấp điện lại (dự kiến)",
        "next_outage_duration": "Thời gian cắt điện (giờ)",
        "next_outage_area": "Khu vực cắt điện",
        "next_outage_reason": "Lý do cắt điện",
        "outage_count": "Số lịch cắt điện",
        "fetched_at": "Lần cập nhật thành công gần nhất",
        "current_provisional_index": "Chỉ số tạm chốt",
        "previous_cycle_final_index": "Chỉ số cuối kỳ trước",
        "consumption_today": "Tiêu thụ hôm nay",
        "consumption_yesterday": "Tiêu thụ hôm qua",
        "consumption_two_days_ago": "Tiêu thụ hôm kia",
        "current_period_detail": "Chi tiết kỳ này",
        "invoice_year": "Hóa đơn năm nay",
        "invoice_this_period": "Kỳ này",
        "invoice_prev_period": "Kỳ trước",
        "invoice_prev_prev_period": "Kỳ trước nữa",
        "consumption_this_period": "Tiêu thụ kỳ này",
        "consumption_prev_period": "Tiêu thụ kỳ trước",
        "consumption_prev_prev_period": "Tiêu thụ kỳ trước nữa",
        "next_update": "Cập nhật lúc",
    },
}
BUTTON_NAMES = {"en": "Refresh data", "vi": "Cập nhật dữ liệu"}
INFO = {
    "tenKhang": "Synthetic Public Name",
    "diaChi": "Synthetic Public Address",
    "dthoai": "0900000000",
    "maHdong": "SYNTHETIC-CONTRACT",
    "maDviCaptct": "PB",
}
MEASUREMENT_KEYS = (
    "average_12m_energy",
    "month_over_month",
    "current_provisional_index",
)
PUBLIC_ATTRIBUTES = {
    "friendly_name",
    "icon",
    "device_class",
    "unit_of_measurement",
    "state_class",
    "last_update",
    "latest_read_at",
    "target_date",
    "target_month",
    "target_year",
    "as_of",
    "period_basis",
    "cycle_basis",
    "source",
    "provisional",
    "period",
    "measurement_point",
    "schedule_start",
    "schedule_end",
    "start",
    "end",
    "duration_hours",
    "count",
    "seconds_until",
    "area",
    "reason",
    "current",
    "previous",
    "delta",
    "old",
    "new",
    "multiplier",
    "kind",
    "cycle",
    "due_date",
    "energy",
    "energy_unit",
    "paid_date",
    "status_label",
    "org_code",
    "payment_channel_label",
    "customer_name",
    "address",
    "phone",
    "contract",
    "region_code",
    "contracts",
    "banks",
    "paid",
}


def make_snapshot() -> Snapshot:
    return Snapshot(
        customer=CUSTOMER,
        region="PB",
        measurement_points=[
            {
                "MA_DDO": POINT,
                "TEN_KHANG": CUSTOMER.name,
                "DIA_CHI": "DUMMY PRIVATE ADDRESS",
            }
        ],
        monthly={
            POINT: [
                {"NAM": 2026, "THANG": 9, "DIEN_TTHU": "900"},
                {"NAM": 2026, "THANG": 10, "DIEN_TTHU": "12.5"},
            ]
        },
        daily={
            POINT: [
                {
                    "NGAY_HTHI": "05/10/2026 - 06/10/2026",
                    "BCS": "KT",
                    "DIEN_TTHU": "1.25",
                }
            ]
        },
        invoices=[
            {
                "ID_HDON": INVOICE_ID,
                "TTRANG_TTOAN": "CHUATT",
                "TONG_NO": "-125000",
                "TONG_TIEN": 125000,
                "NAM": 2026,
                "THANG": 10,
                "KY": 10,
                "DIEN_TTHU": "12.5",
                "MA_TCHUC": "BANK-A",
                "KENH_THANH_TOAN": "Synthetic channel",
                "TEN_KHANG": CUSTOMER.name,
                "DIA_CHI": "DUMMY PRIVATE ADDRESS",
                "password": IDENTITY[CONF_PASSWORD],
                "access_token": TOKENS.access_token,
            }
        ],
        outages=[
            {
                "TGIAN_BDAU": "08/10/2099 08:00",
                "TGIAN_KTHUC": "08/10/2099 10:00",
                "KHUVUCMATDIEN": "Synthetic public area",
                "LY_DO": "Scheduled maintenance",
                "TEN_KHANG": CUSTOMER.name,
                "DIA_CHI": "DUMMY PRIVATE ADDRESS",
                "refresh_token": TOKENS.refresh_token,
            }
        ],
        fetched_at=FETCHED_AT,
        info=dict(INFO),
        contracts=[{"MA_HD": "SYNTHETIC-CONTRACT"}],
        monthly_readings={
            POINT: [
                {
                    "NAM": 2026,
                    "THANG": 10,
                    "NGAY_CKY": "31/10/2026",
                    "LOAI_CHISO": "KT",
                    "CHISO_CU": 1012.5,
                    "CHISO_MOI": 1050,
                    "HSN": 3,
                    "DIEN_TTHU": "112.5",
                }
            ]
        },
        daily_readings={
            POINT: [
                {
                    "NGAY": "05/10/2026",
                    "THOI_DIEM": "05/10/2026 08:00",
                    "BCS": "KT",
                    "LOAI_CHISO": "KT",
                    "CHISO_CU": 900,
                    "CHISO_MOI": 1000,
                    "HSN": 2,
                    "DIEN_TTHU": "200",
                },
                {
                    "NGAY": "06/10/2026",
                    "THOI_DIEM": "06/10/2026 08:00",
                    "BCS": "KT",
                    "LOAI_CHISO": "KT",
                    "CHISO_CU": 1000,
                    "CHISO_MOI": 1012.5,
                    "HSN": 2,
                    "DIEN_TTHU": "25",
                },
            ]
        },
        paid_invoices=[
            {
                "ID_HDON": PAID_INVOICE_ID,
                "TTRANG_TTOAN": "DATT",
                "NAM": 2026,
                "THANG": 9,
                "TONG_TIEN": 500000,
                "NGAY_TTOAN": "15/09/2026",
                "MA_TCHUC": "BANK-A",
            }
        ],
        banks=[{"MA_TCHUC": "BANK-A", "TEN_TCHUC": "Synthetic Bank"}],
    )


class FakeEvnClient:
    def __init__(
        self,
        backend: OfflineEvn,
        device_id: str,
        tokens: TokenState | None,
        on_tokens: Callable[[TokenState], None] | None,
    ) -> None:
        self.backend = backend
        self.device_id = device_id
        self.initial_tokens = tokens
        self.tokens = tokens
        self.on_tokens = on_tokens
        self.login_calls = 0
        self.customer_calls = 0
        self.fetch_calls: list[Customer] = []

    async def login(self) -> None:
        self.login_calls += 1
        self.tokens = TOKENS

    async def customers(self) -> list[Customer]:
        self.customer_calls += 1
        assert self.tokens is not None
        return [CUSTOMER]

    async def fetch_snapshot(self, customer: Customer) -> Snapshot:
        self.fetch_calls.append(customer)
        assert customer == CUSTOMER
        assert self.tokens is not None
        if self.backend.failure is not None:
            raise self.backend.failure
        if self.backend.rotate_tokens and self.tokens != ROTATED_TOKENS:
            self.tokens = ROTATED_TOKENS
            assert self.on_tokens is not None
            self.on_tokens(self.tokens)
        return self.backend.snapshot


@dataclass(repr=False)
class OfflineEvn:
    snapshot: Snapshot = field(default_factory=make_snapshot)
    clients: list[FakeEvnClient] = field(default_factory=list)
    failure: EvnError | None = None
    rotate_tokens: bool = False

    def create_client(
        self,
        session: ClientSession,
        username: str,
        password: str,
        device_id: str,
        *,
        tokens: TokenState | None = None,
        on_tokens: Callable[[TokenState], None] | None = None,
    ) -> FakeEvnClient:
        assert isinstance(session, ClientSession) and not session.closed
        assert username == IDENTITY[CONF_USERNAME]
        assert password == IDENTITY[CONF_PASSWORD]
        assert re.fullmatch(r"[0-9a-f]{16}", device_id)
        client = FakeEvnClient(self, device_id, tokens, on_tokens)
        self.clients.append(client)
        return client


@pytest.fixture
def offline_evn() -> OfflineEvn:
    return OfflineEvn()


@pytest.fixture
def runtime_config_dir(request: pytest.FixtureRequest) -> Iterator[Path]:
    scratch = ROOT / "analysis" / "runtime_tmp"
    basetemp = request.config.getoption("basetemp")
    if basetemp is not None and Path(basetemp).resolve().is_relative_to(scratch):
        yield request.getfixturevalue("tmp_path")
        return
    assert scratch.parent.is_dir()
    scratch.mkdir(mode=0o700, exist_ok=True)
    with TemporaryDirectory(prefix="ha-runtime-", dir=scratch) as directory:
        yield Path(directory)


@pytest_asyncio.fixture
async def runtime_hass(
    runtime_config_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    offline_evn: OfflineEvn,
    caplog: pytest.LogCaptureFixture,
) -> AsyncIterator[HomeAssistant]:
    assert version("homeassistant").startswith("2025.12.")
    assert runtime_config_dir.resolve().is_relative_to(
        ROOT / "analysis" / "runtime_tmp"
    )
    config_dir = runtime_config_dir / "ha"
    config_dir.mkdir(mode=0o700)
    (config_dir / "custom_components").symlink_to(
        ROOT / "custom_components", target_is_directory=True
    )
    monkeypatch.syspath_prepend(str(config_dir))
    network_attempts: list[None] = []

    async def blocked_request(*args: Any, **kwargs: Any) -> Any:
        network_attempts.append(None)
        raise AssertionError("Outbound HTTP is disabled in the offline HA runtime")

    monkeypatch.setattr(ClientSession, "_request", blocked_request)
    monkeypatch.setattr(sensor, "vn_now", lambda: date(2026, 10, 7))
    async with ClientSession() as session:
        monkeypatch.setattr(
            integration, "async_get_clientsession", lambda hass: session
        )
        monkeypatch.setattr(
            config_flow, "async_get_clientsession", lambda hass: session
        )
        monkeypatch.setattr(integration, "EvnClient", offline_evn.create_client)
        monkeypatch.setattr(config_flow, "EvnClient", offline_evn.create_client)
        hass = HomeAssistant(str(config_dir))
        hass.config.skip_pip = True
        hass.config_entries = ConfigEntries(hass, {})
        loader.async_setup(hass)
        try:
            await hass.config.async_set_time_zone("Asia/Ho_Chi_Minh")
            await async_load_base_functionality(hass)
            assert await async_setup_component(hass, "homeassistant", {})
            await hass.async_start()
            await hass.async_block_till_done()
            assert hass.is_running
            yield hass
        finally:
            try:
                for entry in hass.config_entries.async_entries(DOMAIN):
                    if entry.state is ConfigEntryState.LOADED:
                        assert await hass.config_entries.async_unload(entry.entry_id)
            finally:
                await hass.async_stop(force=True)
                await hass.async_block_till_done()
    assert not network_attempts
    protected = (*PROTECTED, *(client.device_id for client in offline_evn.clients))
    assert all(value not in caplog.text for value in protected)


async def add_entry(hass: HomeAssistant) -> EvnConfigEntry:
    entry: EvnConfigEntry = ConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=account_unique_id(IDENTITY[CONF_USERNAME]),
        data={
            **IDENTITY,
            CONF_DEVICE_ID: DEVICE_ID,
            CONF_CUSTOMERS: [
                {"code": CUSTOMER.code, "management_unit": CUSTOMER.management_unit}
            ],
            CONF_TOKENS: TOKENS.to_dict(),
        },
        options={
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            CONF_SELECTED_CUSTOMERS: [customer_key(CUSTOMER)],
        },
        source=SOURCE_USER,
        version=1,
        minor_version=1,
        discovery_keys=MappingProxyType({}),
        subentries_data=(),
    )
    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


def registry_rows(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> dict[str, er.RegistryEntry]:
    rows = [
        row
        for row in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if row.domain == "sensor"
    ]
    assert len(rows) == len(NAMES["en"])
    assert all(row.platform == DOMAIN for row in rows)
    assert {row.translation_key for row in rows} == set(NAMES["en"])
    return {cast(str, row.translation_key): row for row in rows}


def button_rows(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> dict[str, er.RegistryEntry]:
    rows = [
        row
        for row in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if row.domain == "button"
    ]
    assert len(rows) == 1
    assert all(row.platform == DOMAIN for row in rows)
    assert {row.translation_key for row in rows} == {"refresh"}
    return {cast(str, row.translation_key): row for row in rows}


def binary_rows(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> dict[str, er.RegistryEntry]:
    rows = [
        row
        for row in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if row.domain == "binary_sensor"
    ]
    assert len(rows) == 3
    assert {row.translation_key for row in rows} == {
        "outage_scheduled",
        "outage_soon",
        "outage_active",
    }
    return {cast(str, row.translation_key): row for row in rows}


def sensor_states(hass: HomeAssistant, entry: EvnConfigEntry) -> dict[str, State]:
    result = {}
    for key, row in registry_rows(hass, entry).items():
        state = hass.states.get(row.entity_id)
        assert isinstance(state, State)
        if key in MEASUREMENT_KEYS:
            assert state.attributes["state_class"] == "measurement"
        else:
            assert "state_class" not in state.attributes
        assert all(
            value not in str(state)
            for value in (*PROTECTED, entry.data[CONF_DEVICE_ID])
        )
        result[key] = state
    return result


def button_states(hass: HomeAssistant, entry: EvnConfigEntry) -> dict[str, State]:
    result = {}
    for key, row in button_rows(hass, entry).items():
        state = hass.states.get(row.entity_id)
        assert isinstance(state, State)
        assert all(
            value not in str(state)
            for value in (*PROTECTED, entry.data[CONF_DEVICE_ID])
        )
        result[key] = state
    return result


def registry_identity(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> dict[str, tuple[str, str, str | None]]:
    rows = {
        **registry_rows(hass, entry),
        **button_rows(hass, entry),
        **binary_rows(hass, entry),
    }
    return {
        key: (row.entity_id, row.unique_id, row.device_id) for key, row in rows.items()
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["en", "vi"])
async def test_installed_loader_setup_and_sensor_states(
    runtime_hass: HomeAssistant,
    offline_evn: OfflineEvn,
    language: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hass = runtime_hass
    await hass.config.async_update(language=language)
    await hass.async_block_till_done()
    loaded = await loader.async_get_integration(hass, DOMAIN)
    assert not loaded.is_built_in and loaded.config_flow
    assert (
        loaded.file_path == Path(hass.config.config_dir) / "custom_components" / DOMAIN
    )
    component = await loaded.async_get_component()
    assert component is integration
    assert (
        Path(integration.__file__).resolve()
        == ROOT / "custom_components" / DOMAIN / "__init__.py"
    )
    assert DOMAIN in await loader.async_get_config_flows(hass)
    entry = await add_entry(hass)
    assert {
        "homeassistant",
        DOMAIN,
        "sensor",
        "button",
        "binary_sensor",
    } <= hass.config.components
    platforms = [
        platform
        for platform in async_get_platforms(hass, DOMAIN)
        if platform.config_entry is entry
    ]
    assert {platform.domain for platform in platforms} == {
        "sensor",
        "button",
        "binary_sensor",
    }
    sensor_platform = next(
        platform for platform in platforms if platform.domain == "sensor"
    )
    button_platform = next(
        platform for platform in platforms if platform.domain == "button"
    )
    assert len(sensor_platform.entities) == len(NAMES["en"])
    assert len(button_platform.entities) == 1
    binary_platform = next(
        platform for platform in platforms if platform.domain == "binary_sensor"
    )
    assert len(binary_platform.entities) == 3
    assert tuple(entry.runtime_data.async_contexts()) == (customer_key(CUSTOMER),) * (
        len(NAMES["en"]) + 4
    )
    assert offline_evn.clients[0].login_calls == 0
    assert offline_evn.clients[0].fetch_calls == [CUSTOMER]
    translations = await async_get_translations(hass, language, "entity", {DOMAIN})
    states = sensor_states(hass, entry)
    rows = registry_rows(hass, entry)
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    expected_id = hashlib.sha256(
        json.dumps(
            (entry.unique_id, CUSTOMER.management_unit, CUSTOMER.code),
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    assert device.identifiers == {(DOMAIN, expected_id)}
    assert device.name == f"{NAME} {expected_id[:8]}"
    assert device.manufacturer == "EVN" and device.model == "Customer account"
    assert all(value not in str(device) for value in PROTECTED)
    for key, state in states.items():
        translated = translations[f"component.{DOMAIN}.entity.sensor.{key}.name"]
        assert translated.format(measurement_point=POINT) == NAMES[language][key]
        assert rows[key].original_name == NAMES[language][key]
        assert rows[key].has_entity_name and not rows[key].disabled
        assert rows[key].device_id == device.id
        assert re.fullmatch(r"[0-9a-f]{64}", rows[key].unique_id)
        assert (
            state.attributes["friendly_name"] == f"{device.name} {NAMES[language][key]}"
        )
        assert "{" not in state.attributes["friendly_name"]
        assert set(state.attributes) <= PUBLIC_ATTRIBUTES
        assert state.attributes["last_update"] == FETCHED_AT.isoformat()
    for key, expected in (("monthly_energy", "12.5"), ("daily_energy", "1.25")):
        assert states[key].state == expected
        assert states[key].attributes["unit_of_measurement"] == "kWh"
        assert states[key].attributes["device_class"] == "energy"
        assert states[key].attributes["measurement_point"] == POINT
    assert states["monthly_energy"].attributes["period"] == "2026-10"
    assert states["daily_energy"].attributes["period"] == "05/10/2026 - 06/10/2026"
    amount = states["outstanding_amount"]
    assert float(amount.state) == 125000.0
    assert amount.attributes["unit_of_measurement"] == "VND"
    assert amount.attributes["device_class"] == "monetary"
    assert states["outstanding_count"].state == "1"
    assert "unit_of_measurement" not in states["outstanding_count"].attributes
    assert states["next_outage"].state == "2099-10-08T01:00:00+00:00"
    assert states["next_outage"].attributes["start"] == "2099-10-08T08:00:00+07:00"
    assert states["next_outage"].attributes["end"] == "2099-10-08T10:00:00+07:00"
    assert states["next_outage"].attributes["area"] == "Synthetic public area"
    assert states["next_outage"].attributes["reason"] == "Scheduled maintenance"
    assert states["next_outage"].attributes["duration_hours"] == 2.0
    assert states["next_outage"].attributes["count"] == 1
    assert states["next_outage_end"].state == "2099-10-08T03:00:00+00:00"
    assert float(states["next_outage_duration"].state) == 2.0
    assert states["next_outage_duration"].attributes["unit_of_measurement"] == "h"
    assert states["next_outage_area"].state == "Synthetic public area"
    assert states["next_outage_reason"].state == "Scheduled maintenance"
    assert states["outage_count"].state == "1"
    assert rows["outage_count"].entity_category is EntityCategory.DIAGNOSTIC
    assert rows["next_outage_area"].entity_category is None
    assert rows["next_outage_reason"].entity_category is None
    assert states["fetched_at"].state == FETCHED_AT.isoformat(timespec="seconds")
    assert rows["fetched_at"].entity_category is EntityCategory.DIAGNOSTIC
    assert states["prev_month_energy"].state == "900.0"
    assert states["prev_month_energy"].attributes["period"] == "2026-09"
    assert states["prev_month_energy"].attributes["device_class"] == "energy"
    assert states["average_12m_energy"].state == "456.25"
    assert states["average_12m_energy"].attributes["unit_of_measurement"] == "kWh"
    assert "device_class" not in states["average_12m_energy"].attributes
    assert float(states["month_over_month"].state) == pytest.approx(
        (12.5 - 900.0) / 900.0 * 100
    )
    assert states["month_over_month"].attributes["unit_of_measurement"] == "%"
    assert "device_class" not in states["month_over_month"].attributes
    assert states["month_over_month"].attributes["current"] == 12.5
    assert states["month_over_month"].attributes["previous"] == 900.0
    assert states["month_over_month"].attributes["delta"] == -887.5
    assert states["meter_reading"].state == "1012.5"
    assert states["meter_reading"].attributes["old"] == 1000.0
    assert states["meter_reading"].attributes["new"] == 1012.5
    assert states["meter_reading"].attributes["multiplier"] == 2.0
    assert states["meter_reading"].attributes["kind"] == "KT"
    assert states["meter_reading"].attributes["period"] == "06/10/2026 08:00"
    assert "unit_of_measurement" not in states["meter_reading"].attributes
    assert states["meter_multiplier"].state == "2.0"
    assert states["meter_read_date"].state == "06/10/2026 08:00"
    assert rows["meter_read_date"].entity_category is EntityCategory.DIAGNOSTIC
    assert rows["meter_multiplier"].entity_category is EntityCategory.DIAGNOSTIC
    assert states["latest_invoice_amount"].state == "125000.0"
    assert states["latest_invoice_amount"].attributes["device_class"] == "monetary"
    assert states["latest_invoice_amount"].attributes["unit_of_measurement"] == "VND"
    assert states["latest_invoice_amount"].attributes["status_label"] == (
        "Chưa thanh toán"
    )
    assert states["latest_invoice_amount"].attributes["cycle"] == 10
    assert states["latest_invoice_amount"].attributes["energy"] == 12.5
    assert states["latest_invoice_amount"].attributes["energy_unit"] == "kWh"
    assert states["latest_invoice_amount"].attributes["org_code"] == "BANK-A"
    assert states["latest_invoice_amount"].attributes["payment_channel_label"] == (
        "Synthetic Bank"
    )
    assert states["latest_invoice_status"].state == "Chưa thanh toán"
    assert "unit_of_measurement" not in states["latest_invoice_status"].attributes
    assert states["paid_invoice_count"].state == "1"
    assert rows["paid_invoice_count"].entity_category is EntityCategory.DIAGNOSTIC
    assert states["fetched_at"].attributes["customer_name"] == INFO["tenKhang"]
    assert states["fetched_at"].attributes["address"] == INFO["diaChi"]
    assert states["fetched_at"].attributes["phone"] == INFO["dthoai"]
    assert states["fetched_at"].attributes["contract"] == INFO["maHdong"]
    assert states["fetched_at"].attributes["region_code"] == "PB"
    assert states["fetched_at"].attributes["contracts"] == 1
    assert states["fetched_at"].attributes["banks"] == 1
    assert states["fetched_at"].attributes["paid"] == 1
    button = button_rows(hass, entry)
    button_state = button_states(hass, entry)["refresh"]
    assert (
        translations[f"component.{DOMAIN}.entity.button.refresh.name"]
        == BUTTON_NAMES[language]
    )
    assert button["refresh"].original_name == BUTTON_NAMES[language]
    assert button["refresh"].has_entity_name
    assert button["refresh"].entity_category is None
    assert button["refresh"].device_id == device.id
    assert re.fullmatch(r"[0-9a-f]{64}", cast(str, button["refresh"].unique_id))
    assert button["refresh"].unique_id not in {row.unique_id for row in rows.values()}
    assert button_state.state == STATE_UNKNOWN
    assert button_state.attributes["friendly_name"] == (
        f"{device.name} {BUTTON_NAMES[language]}"
    )
    assert len(NAMES["en"]) == 34
    expected_new = {
        "current_provisional_index": "1012.5",
        "previous_cycle_final_index": STATE_UNKNOWN,
        "consumption_today": STATE_UNKNOWN,
        "consumption_yesterday": STATE_UNKNOWN,
        "consumption_two_days_ago": STATE_UNKNOWN,
        "current_period_detail": "10-2026",
        "invoice_year": "2026",
        "invoice_this_period": "125000.0",
        "invoice_prev_period": "500000.0",
        "invoice_prev_prev_period": STATE_UNKNOWN,
        "consumption_this_period": "12.5",
        "consumption_prev_period": "900.0",
        "consumption_prev_prev_period": STATE_UNKNOWN,
    }
    for key, expected in expected_new.items():
        assert states[key].state == expected
    provisional = states["current_provisional_index"]
    assert provisional.attributes["latest_read_at"] == "06/10/2026 08:00"
    assert provisional.attributes["period"] == "06/10/2026"
    assert "unit_of_measurement" not in provisional.attributes
    assert rows["next_update"].entity_category is EntityCategory.DIAGNOSTIC
    assert states["next_update"].attributes["device_class"] == "timestamp"
    scheduled = datetime.fromisoformat(states["next_update"].state)
    assert scheduled.tzinfo is UTC
    assert abs((scheduled - entry.runtime_data.next_iteration).total_seconds()) < 2
    assert scheduled > datetime.now(UTC)
    binary = binary_rows(hass, entry)
    outage_row = binary["outage_scheduled"]
    outage_state = hass.states.get(outage_row.entity_id)
    assert outage_state is not None and outage_state.state == "on"
    assert outage_state.attributes["schedule_start"] == "2099-10-08T08:00:00+07:00"
    assert outage_state.attributes["schedule_end"] == "2099-10-08T10:00:00+07:00"
    assert outage_state.attributes["area"] == "Synthetic public area"
    assert outage_state.attributes["reason"] == "Scheduled maintenance"
    assert outage_state.attributes["count"] == 1
    assert outage_row.entity_category is EntityCategory.DIAGNOSTIC
    assert outage_row.device_id == device.id
    assert (
        outage_row.original_name
        == {"en": "Outage scheduled", "vi": "Lịch cắt điện"}[language]
    )
    assert "device_class" not in outage_state.attributes
    for key in ("outage_soon", "outage_active"):
        row = binary[key]
        state = hass.states.get(row.entity_id)
        assert state is not None and state.state == "off"
        assert row.entity_category is None
        assert (
            row.original_name
            == {
                "outage_soon": {
                    "en": "Outage soon (within 24 hours)",
                    "vi": "Sắp cắt điện (≤24 giờ)",
                },
                "outage_active": {
                    "en": "Within scheduled outage window",
                    "vi": "Đang trong khung giờ cắt điện",
                },
            }[key][language]
        )
        assert "device_class" not in state.attributes
    assert not [record for record in caplog.records if record.levelno >= 40]


@pytest.mark.asyncio
async def test_native_button_press_refreshes_data(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    entry = await add_entry(hass)
    entity_id = cast(str, button_rows(hass, entry)["refresh"].entity_id)
    before = len(offline_evn.clients[0].fetch_calls)
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert len(offline_evn.clients[0].fetch_calls) == before + 1
    assert entry.runtime_data.last_update_success
    state = hass.states.get(entity_id)
    assert isinstance(state, State)
    assert state.state != STATE_UNKNOWN
    assert all(
        value not in str(state) for value in (*PROTECTED, entry.data[CONF_DEVICE_ID])
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [EvnAuthError, EvnUserActionRequired], ids=["auth", "action"]
)
async def test_button_press_maps_auth_failure_to_reauth(
    runtime_hass: HomeAssistant,
    offline_evn: OfflineEvn,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[EvnError],
) -> None:
    hass = runtime_hass
    entry = await add_entry(hass)
    entity_id = cast(str, button_rows(hass, entry)["refresh"].entity_id)
    start_reauth = Mock()
    monkeypatch.setattr(entry, "async_start_reauth", start_reauth)
    offline_evn.failure = failure()
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert isinstance(entry.runtime_data.last_exception, ConfigEntryAuthFailed)
    start_reauth.assert_called_once_with(hass)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_runtime_unknown_unavailable_and_recovery(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    entry = await add_entry(hass)
    identity = registry_identity(hass, entry)
    offline_evn.snapshot = replace(
        make_snapshot(),
        monthly={POINT: [{"NAM": 2026, "THANG": 10, "DIEN_TTHU": "1,234"}]},
        daily={POINT: [{"NGAY": "06/10/2026", "BCS": "KT", "DIEN_TTHU": "NaN"}]},
        invoices=[{"ID_HDON": INVOICE_ID, "TTRANG_TTOAN": "CHUATT"}],
        outages=[],
        monthly_readings={},
        daily_readings={},
        paid_invoices=[],
        banks=[],
        contracts=[],
        info={},
    )
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert entry.runtime_data.last_update_success
    assert all(
        states[key].state == STATE_UNKNOWN
        for key in NAMES["en"]
        if key
        not in (
            "fetched_at",
            "paid_invoice_count",
            "next_update",
            "current_period_detail",
            "invoice_year",
            "outage_count",
        )
    )
    assert states["paid_invoice_count"].state == "0"
    assert states["outage_count"].state == "0"
    assert all("period" not in state.attributes for state in states.values())
    assert "end" not in states["next_outage"].attributes
    assert "area" not in states["next_outage"].attributes
    assert states["next_outage"].attributes["count"] == 0
    assert states["next_outage_end"].state == STATE_UNKNOWN
    assert states["next_outage_duration"].state == STATE_UNKNOWN
    assert states["next_outage_area"].state == STATE_UNKNOWN
    assert states["next_outage_reason"].state == STATE_UNKNOWN
    assert "customer_name" not in states["fetched_at"].attributes
    assert states["fetched_at"].attributes["contracts"] == 0
    assert states["fetched_at"].attributes["banks"] == 0
    binary_id = binary_rows(hass, entry)["outage_scheduled"].entity_id
    assert hass.states.get(binary_id).state == "off"
    assert "start" not in hass.states.get(binary_id).attributes
    offline_evn.failure = EvnResponseError()
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert not entry.runtime_data.last_update_success
    for key, state in sensor_states(hass, entry).items():
        if key == "next_update":
            scheduled = datetime.fromisoformat(state.state)
            assert scheduled.tzinfo is UTC
            assert (
                abs((scheduled - entry.runtime_data.next_iteration).total_seconds()) < 2
            )
            assert state.attributes["source"] == "coordinator_timer"
            assert state.attributes["provisional"] is False
            assert "last_update" not in state.attributes
        else:
            assert state.state == STATE_UNAVAILABLE
            assert set(state.attributes) <= {
                "friendly_name",
                "icon",
                "device_class",
                "unit_of_measurement",
                "state_class",
            }
    for state in button_states(hass, entry).values():
        assert state.state == STATE_UNAVAILABLE
    assert hass.states.get(binary_id).state == STATE_UNAVAILABLE
    assert "start" not in hass.states.get(binary_id).attributes
    offline_evn.failure = None
    offline_evn.snapshot = replace(make_snapshot(), invoices=[], outages=[])
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert states["monthly_energy"].state == "12.5"
    assert states["daily_energy"].state == "1.25"
    assert float(states["outstanding_amount"].state) == 0.0
    assert states["outstanding_count"].state == "0"
    assert states["next_outage"].state == STATE_UNKNOWN
    assert float(states["latest_invoice_amount"].state) == 500000.0
    assert states["latest_invoice_status"].state == "Đã thanh toán"
    assert states["latest_invoice_amount"].attributes["paid_date"] == "15/09/2026"
    assert states["latest_invoice_amount"].attributes["payment_channel_label"] == (
        "Synthetic Bank"
    )
    offline_evn.snapshot = replace(make_snapshot(), measurement_points=[])
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert states["monthly_energy"].state == STATE_UNAVAILABLE
    assert states["daily_energy"].state == STATE_UNAVAILABLE
    assert states["meter_reading"].state == STATE_UNAVAILABLE
    assert states["outstanding_count"].state == "1"
    assert registry_identity(hass, entry) == identity
    assert len(offline_evn.clients) == 1 and offline_evn.clients[0].login_calls == 0


@pytest.mark.asyncio
async def test_runtime_rich_scheduled_outage_entities(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    entry = await add_entry(hass)
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    def stamp(moment: datetime) -> str:
        return moment.strftime("%d/%m/%Y %H:%M")

    offline_evn.snapshot = replace(
        make_snapshot(),
        outages=[
            {
                "TGIAN_BDAU": stamp(now - timedelta(minutes=15)),
                "TGIAN_KTHUC": stamp(now + timedelta(minutes=45)),
                "KHUVUCMATDIEN": "Active area",
                "LY_DO": "Active reason",
            },
            {
                "TGIAN_BDAU": stamp(now + timedelta(hours=1)),
                "TGIAN_KTHUC": stamp(now + timedelta(hours=4)),
                "KHUVUCMATDIEN": "Soon area",
                "LY_DO": "Soon reason",
            },
            {
                "TGIAN_BDAU": stamp(now + timedelta(days=20)),
                "TGIAN_KTHUC": stamp(now + timedelta(days=20, hours=2)),
            },
            {
                "TGIAN_BDAU": stamp(now - timedelta(days=3)),
                "TGIAN_KTHUC": stamp(now - timedelta(days=3) + timedelta(hours=2)),
            },
        ],
    )
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert states["outage_count"].state == "4"
    assert "device_class" not in states["outage_count"].attributes
    assert states["next_outage"].state != STATE_UNKNOWN
    assert states["next_outage"].attributes["count"] == 4
    assert states["next_outage_area"].state == "Soon area"
    assert states["next_outage_reason"].state == "Soon reason"
    assert float(states["next_outage_duration"].state) == pytest.approx(3.0, abs=0.1)
    assert states["next_outage_end"].state != STATE_UNKNOWN
    binary = binary_rows(hass, entry)
    assert hass.states.get(binary["outage_scheduled"].entity_id).state == "on"
    assert hass.states.get(binary["outage_soon"].entity_id).state == "on"
    assert hass.states.get(binary["outage_active"].entity_id).state == "on"
    assert binary["outage_scheduled"].entity_category is EntityCategory.DIAGNOSTIC
    assert binary["outage_soon"].entity_category is None
    assert binary["outage_active"].entity_category is None
    soon_attrs = hass.states.get(binary["outage_soon"].entity_id).attributes
    assert 0 <= soon_attrs["seconds_until"] <= 3 * 3600
    active_attrs = hass.states.get(binary["outage_active"].entity_id).attributes
    assert active_attrs["area"] == "Active area"
    assert active_attrs["reason"] == "Active reason"
    active_day = (now - timedelta(minutes=15)).strftime("%Y-%m-%d")
    assert active_attrs["start"].startswith(active_day)


@pytest.mark.asyncio
@pytest.mark.parametrize("scheduled", [False, True], ids=["manual", "timer"])
async def test_runtime_retry_schedule_publication(
    runtime_hass: HomeAssistant,
    offline_evn: OfflineEvn,
    monkeypatch: pytest.MonkeyPatch,
    scheduled: bool,
) -> None:
    hass = runtime_hass
    entry = await add_entry(hass)
    coordinator = cast(integration._ScheduledEvnCoordinator, entry.runtime_data)
    identity = registry_identity(hass, entry)
    client = offline_evn.clients[0]
    states = sensor_states(hass, entry)
    assert states["daily_energy"].state == "1.25"
    assert states["consumption_today"].state == STATE_UNKNOWN
    previous = datetime.fromisoformat(states["next_update"].state)
    updates = Mock(wraps=coordinator.async_update_listeners)
    monkeypatch.setattr(coordinator, "async_update_listeners", updates)
    start_reauth = Mock()
    monkeypatch.setattr(entry, "async_start_reauth", start_reauth)
    monotonic = hass.loop.time
    elapsed = 0.0
    clock = Mock(wraps=datetime)
    clock.now.side_effect = lambda tz: datetime.now(tz) + timedelta(seconds=elapsed)

    async def refresh() -> None:
        nonlocal elapsed
        timer = getattr(coordinator._unsub_refresh, "__self__", None)
        assert isinstance(timer, asyncio.TimerHandle) and not timer.cancelled()
        if scheduled:
            elapsed += timer.when() - hass.loop.time() + 1
            await asyncio.sleep(0)
        else:
            elapsed += 60
            await coordinator.async_refresh()
            assert timer.cancelled()
        await hass.async_block_till_done()

    with monkeypatch.context() as time_patch:
        time_patch.setattr(hass.loop, "time", lambda: monotonic() + elapsed)
        time_patch.setattr(integration, "datetime", clock)
        offline_evn.failure = EvnConnectionError()
        for attempt in (1, 2):
            await refresh()
            assert not coordinator.last_update_success
            assert client.fetch_calls == [CUSTOMER] * (attempt + 1)
            assert client.customer_calls == attempt + 1
            states = sensor_states(hass, entry)
            next_update = states.pop("next_update")
            stamp = datetime.fromisoformat(next_update.state)
            assert stamp > previous + timedelta(seconds=30)
            assert updates.call_count == attempt
            next_iteration = coordinator.next_iteration
            assert next_iteration is not None
            assert abs((stamp - next_iteration).total_seconds()) < 1
            assert next_update.attributes["source"] == "coordinator_timer"
            assert next_update.attributes["provisional"] is False
            assert "last_update" not in next_update.attributes
            assert all(state.state == STATE_UNAVAILABLE for state in states.values())
            assert all(
                "last_update" not in state.attributes for state in states.values()
            )
            previous = stamp
        start_reauth.assert_not_called()
        offline_evn.failure = EvnAuthError()
        await refresh()
        assert isinstance(coordinator.last_exception, ConfigEntryAuthFailed)
        assert not coordinator.last_update_success
        assert coordinator._unsub_refresh is None
        assert coordinator.next_iteration is None
        assert updates.call_count == 3
        assert client.fetch_calls == [CUSTOMER] * 4 and client.customer_calls == 4
        start_reauth.assert_called_once_with(hass)
        states = sensor_states(hass, entry)
        assert all(state.state == STATE_UNAVAILABLE for state in states.values())
        assert "source" not in states["next_update"].attributes
        assert "last_update" not in states["next_update"].attributes
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert updates.call_count == 3
        assert client.fetch_calls == [CUSTOMER] * 5 and client.customer_calls == 5
        assert coordinator.next_iteration is None
        offline_evn.failure = None
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert coordinator.last_update_success and updates.call_count == 4
        assert sensor_states(hass, entry)["daily_energy"].state == "1.25"
        assert sensor_states(hass, entry)["consumption_today"].state == STATE_UNKNOWN
        await refresh()
        assert coordinator.last_update_success and updates.call_count == 5
        assert client.fetch_calls == [CUSTOMER] * 7 and client.customer_calls == 7
        assert len(offline_evn.clients) == 1 and client.login_calls == 0
        assert entry.data[CONF_TOKENS] == TOKENS.to_dict()
        assert registry_identity(hass, entry) == identity
        timer = getattr(coordinator._unsub_refresh, "__self__", None)
        assert isinstance(timer, asyncio.TimerHandle)
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert timer.cancelled()
        assert coordinator._unsub_refresh is None
        assert coordinator.next_iteration is None
        assert not coordinator._listeners
        assert coordinator._shutdown_requested
        assert coordinator._debounced_refresh._timer_task is None
        assert coordinator._debounced_refresh.function is None
        assert all(
            not platform.entities for platform in async_get_platforms(hass, DOMAIN)
        )
        assert sensor_states(hass, entry)["next_update"].state == STATE_UNAVAILABLE
        assert await hass.config_entries.async_remove(entry.entry_id) == {
            "require_restart": False
        }
        elapsed += 2 * DEFAULT_UPDATE_INTERVAL * 60
        await asyncio.sleep(0)
        await hass.async_block_till_done()
        assert all(
            hass.states.get(entity_id) is None for entity_id, _, _ in identity.values()
        )
        assert updates.call_count == 5
        assert client.fetch_calls == [CUSTOMER] * 7 and client.customer_calls == 7


@pytest.mark.asyncio
async def test_native_options_reload_unload_and_entry_removal(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    offline_evn.rotate_tokens = True
    entry = await add_entry(hass)
    assert entry.supports_options and entry.supports_unload
    assert entry.data[CONF_TOKENS] == ROTATED_TOKENS.to_dict()
    assert offline_evn.clients[0].initial_tokens == TOKENS
    identity = registry_identity(hass, entry)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    identifiers = set(device.identifiers)
    coordinator = entry.runtime_data
    timer = getattr(coordinator._unsub_refresh, "__self__", None)
    assert isinstance(timer, asyncio.TimerHandle) and not timer.cancelled()
    scheduled = datetime.fromisoformat(sensor_states(hass, entry)["next_update"].state)
    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"] is FlowResultType.FORM and options["step_id"] == "init"
    schema = options["data_schema"]
    assert schema is not None
    number = schema.schema[CONF_UPDATE_INTERVAL]
    selected = schema.schema[CONF_SELECTED_CUSTOMERS]
    assert isinstance(number, NumberSelector)
    assert number.config["min"] == 60 and number.config["max"] == 1440
    assert isinstance(selected, SelectSelector)
    assert selected.config["multiple"] is True
    assert selected.config["custom_value"] is False
    assert selected.config["options"] == [customer_key(CUSTOMER)]
    assert schema({}) == dict(entry.options)
    for invalid in (
        {CONF_UPDATE_INTERVAL: 59},
        {CONF_SELECTED_CUSTOMERS: ["UNAUTHORIZED:CUSTOMER"]},
    ):
        with pytest.raises(vol.Invalid):
            schema(dict(entry.options) | invalid)
    result = await hass.config_entries.options.async_configure(
        options["flow_id"], user_input=dict(entry.options)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data is coordinator and len(offline_evn.clients) == 1
    options = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        options["flow_id"],
        user_input={
            CONF_UPDATE_INTERVAL: 60,
            CONF_SELECTED_CUSTOMERS: [customer_key(CUSTOMER)],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not coordinator
    assert coordinator._shutdown_requested and not tuple(coordinator.async_contexts())
    assert timer.cancelled() and coordinator._unsub_refresh is None
    assert coordinator._debounced_refresh._timer_task is None
    assert coordinator._debounced_refresh.function is None
    assert entry.runtime_data.update_interval == timedelta(minutes=60)
    rescheduled = datetime.fromisoformat(
        sensor_states(hass, entry)["next_update"].state
    )
    assert scheduled - rescheduled > timedelta(hours=4)
    assert abs((rescheduled - datetime.now(UTC)).total_seconds() - 60 * 60) < 2
    assert len(offline_evn.clients) == 2
    assert offline_evn.clients[0].fetch_calls == [CUSTOMER]
    assert not entry.update_listeners
    assert registry_identity(hass, entry) == identity
    assert sensor_states(hass, entry)["monthly_energy"].state == "12.5"
    coordinator = entry.runtime_data
    timer = getattr(coordinator._unsub_refresh, "__self__", None)
    assert isinstance(timer, asyncio.TimerHandle) and not timer.cancelled()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert coordinator._shutdown_requested and not coordinator._listeners
    assert timer.cancelled() and coordinator._unsub_refresh is None
    assert coordinator._debounced_refresh._timer_task is None
    assert coordinator._debounced_refresh.function is None
    assert len(offline_evn.clients) == 3
    assert all(client.fetch_calls == [CUSTOMER] for client in offline_evn.clients)
    assert all(client.device_id == DEVICE_ID for client in offline_evn.clients)
    assert all(
        client.initial_tokens == ROTATED_TOKENS for client in offline_evn.clients[1:]
    )
    assert all(client.login_calls == 0 for client in offline_evn.clients)
    assert entry.data[CONF_DEVICE_ID] == DEVICE_ID
    assert registry_identity(hass, entry) == identity
    reloaded_device = dr.async_get(hass).async_get(device.id)
    assert reloaded_device is not None and reloaded_device.identifiers == identifiers
    coordinator = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert coordinator._shutdown_requested and not tuple(coordinator.async_contexts())
    assert all(not platform.entities for platform in async_get_platforms(hass, DOMAIN))
    for state in sensor_states(hass, entry).values():
        assert state.state == STATE_UNAVAILABLE and state.attributes["restored"] is True
        assert "last_update" not in state.attributes
    assert registry_identity(hass, entry) == identity
    assert await hass.config_entries.async_remove(entry.entry_id) == {
        "require_restart": False
    }
    await hass.async_block_till_done()
    assert hass.config_entries.async_get_entry(entry.entry_id) is None
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert dr.async_get(hass).async_get(device.id) is None
    assert all(
        hass.states.get(entity_id) is None for entity_id, _, _ in identity.values()
    )


@pytest.mark.asyncio
async def test_native_credentials_form_creation_and_duplicate(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert form["type"] is FlowResultType.FORM and form["step_id"] == "user"
    assert form["errors"] == {}
    schema = form["data_schema"]
    assert schema is not None
    password = schema.schema[CONF_PASSWORD]
    assert isinstance(password, TextSelector) and password.config["type"] == "password"
    assert schema(IDENTITY) == IDENTITY
    with pytest.raises(vol.Invalid):
        schema({CONF_USERNAME: IDENTITY[CONF_USERNAME]})
    assert not offline_evn.clients
    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], user_input=IDENTITY
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = cast(EvnConfigEntry, result["result"])
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.config_entries.async_get_entry(entry.entry_id) is entry
    assert entry.unique_id == account_unique_id(IDENTITY[CONF_USERNAME])
    assert re.fullmatch(r"[0-9a-f]{16}", entry.data[CONF_DEVICE_ID])
    assert entry.data[CONF_TOKENS] == TOKENS.to_dict()
    assert entry.data[CONF_CUSTOMERS] == [
        {"code": CUSTOMER.code, "management_unit": CUSTOMER.management_unit}
    ]
    assert dict(entry.options) == {
        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
        CONF_SELECTED_CUSTOMERS: [customer_key(CUSTOMER)],
    }
    assert len(offline_evn.clients) == 2
    assert [client.login_calls for client in offline_evn.clients] == [1, 0]
    assert all(
        client.device_id == entry.data[CONF_DEVICE_ID] for client in offline_evn.clients
    )
    assert offline_evn.clients[1].initial_tokens == TOKENS
    assert sensor_states(hass, entry)["monthly_energy"].state == "12.5"
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        duplicate["flow_id"], user_input=IDENTITY
    )
    assert (
        result["type"] is FlowResultType.ABORT
        and result["reason"] == "already_configured"
    )
    assert len(offline_evn.clients) == 2
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


@pytest.mark.asyncio
async def test_requested_daily_and_historical_entity_states(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    snapshot = offline_evn.snapshot
    snapshot.daily_readings[POINT] = [
        {
            "NGAY": day,
            "THOI_DIEM": day + " 08:00",
            "BCS": "KT",
            "SO_CTO": "METER-A",
            "CHISO_MOI": index,
            "HSN": 2,
        }
        for day, index in (
            ("04/10/2026", 900),
            ("05/10/2026", 1000),
            ("06/10/2026", 1012.5),
            ("07/10/2026", 1018),
        )
    ]
    snapshot.daily[POINT] = [
        {
            "NGAY": day,
            "NGAY_HTHI": day,
            "SO_CTO": "METER-A",
            "BCS": "KT",
            "DIEN_TTHU": energy,
        }
        for day, energy in (("05/10/2026", 200), ("06/10/2026", 25), ("07/10/2026", 11))
    ]
    snapshot.monthly_readings[POINT].append(
        {"NAM": 2026, "THANG": 8, "BCS": "KT", "DIEN_TTHU": 800, "CHISO_MOI": 900}
    )
    snapshot.paid_invoices.append(
        {
            "ID_HDON": OLDER_INVOICE_ID,
            "NAM": 2026,
            "THANG": 8,
            "TONG_TIEN": 75000,
            "NGAY_TTOAN": "31/08/2026",
        }
    )
    entry = await add_entry(hass)
    states = sensor_states(hass, entry)
    for key, expected in {
        "current_provisional_index": "1018.0",
        "consumption_today": "11.0",
        "consumption_yesterday": "25.0",
        "consumption_two_days_ago": "200.0",
        "invoice_prev_prev_period": "75000.0",
        "consumption_prev_prev_period": "800.0",
    }.items():
        assert states[key].state == expected
    assert states["consumption_prev_period"].state == states["prev_month_energy"].state
    rows = registry_rows(hass, entry)
    assert (
        rows["consumption_prev_period"].unique_id != rows["prev_month_energy"].unique_id
    )
    assert (
        states["current_provisional_index"].attributes["latest_read_at"]
        == "07/10/2026 08:00"
    )
    assert states["current_provisional_index"].attributes["period"] == "07/10/2026"
    for key in (
        "consumption_today",
        "consumption_yesterday",
        "consumption_two_days_ago",
        "consumption_this_period",
        "consumption_prev_period",
        "consumption_prev_prev_period",
    ):
        assert states[key].attributes["unit_of_measurement"] == "kWh"
        assert states[key].attributes["device_class"] == "energy"
    for key in (
        "invoice_this_period",
        "invoice_prev_period",
        "invoice_prev_prev_period",
    ):
        assert states[key].attributes["unit_of_measurement"] == "VND"
        assert states[key].attributes["device_class"] == "monetary"
    coordinator = entry.runtime_data
    coordinator._async_unsub_refresh()
    coordinator.async_update_listeners()
    await hass.async_block_till_done()
    assert sensor_states(hass, entry)["next_update"].state == STATE_UNKNOWN
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert sensor_states(hass, entry)["next_update"].state != STATE_UNKNOWN
    snapshot.daily[POINT] = []
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert all(states[key].state == STATE_UNKNOWN for key in sensor._DAY_OFFSETS)
    assert states["current_provisional_index"].state == "1018.0"


@pytest.mark.asyncio
async def test_runtime_actual_daily_schema_unknown_zero_and_month_gap(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    snapshot = offline_evn.snapshot
    snapshot.daily_readings[POINT] = [
        {
            "NGAY": day,
            "THOI_DIEM": day + " 08:00",
            "BCS": "KT",
            "SO_CTO": "METER-A",
            "CHISO_MOI": 100,
            "HSN": 2,
        }
        for day in ("06/10/2026", "07/10/2026")
    ]
    snapshot.daily[POINT] = [
        {
            "NGAY": "07/10/2026",
            "NGAY_HTHI": "07/10/2026",
            "SO_CTO": "METER-A",
            "BCS": "KT",
            "DIEN_TTHU": 0,
        }
    ]
    snapshot.monthly = {
        POINT: [
            {"NAM": 2026, "THANG": 10, "DIEN_TTHU": 0},
            {"NAM": 2026, "THANG": 8, "DIEN_TTHU": 20},
        ]
    }
    snapshot.monthly_readings = {}
    snapshot.invoices = []
    snapshot.paid_invoices = []
    entry = await add_entry(hass)
    states = sensor_states(hass, entry)
    assert states["consumption_today"].state == "0.0"
    assert states["consumption_yesterday"].state == STATE_UNKNOWN
    assert states["consumption_today"].attributes["target_date"] == "2026-10-07"
    assert states["consumption_today"].attributes["source"] == "diennangngay"
    assert states["consumption_this_period"].state == "0.0"
    assert states["consumption_prev_period"].state == STATE_UNKNOWN
    assert states["consumption_prev_prev_period"].state == "20.0"
    assert states["invoice_this_period"].state == STATE_UNKNOWN
    assert states["month_over_month"].state == STATE_UNKNOWN
    assert "previous" not in states["month_over_month"].attributes
    assert states["average_12m_energy"].state == "10.0"
    snapshot.daily[POINT] = [dict(row) for row in snapshot.daily_readings[POINT]]
    snapshot.monthly[POINT][0]["DIEN_TTHU"] = None
    snapshot.invoices = [
        {
            "ID_HDON": INVOICE_ID,
            "NAM": 2026,
            "THANG": 10,
            "TTRANG_TTOAN": "CHUATT",
            "TONG_TIEN": 0,
            "TONG_NO": 0,
        }
    ]
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert states["consumption_today"].state == STATE_UNKNOWN
    assert states["consumption_this_period"].state == STATE_UNKNOWN
    assert states["invoice_this_period"].state == "0.0"
    assert states["current_provisional_index"].state == "100.0"
    identity = registry_identity(hass, entry)
    assert len({values[1] for values in identity.values()}) == 38


@pytest.mark.asyncio
@pytest.mark.parametrize("active_adjustment,paid_adjustment", [(None, ""), ("", None)])
async def test_runtime_canonical_invoice_overlap_keeps_distinct_paid_invoice(
    runtime_hass: HomeAssistant,
    offline_evn: OfflineEvn,
    active_adjustment: str | None,
    paid_adjustment: str | None,
) -> None:
    hass = runtime_hass
    snapshot = offline_evn.snapshot
    active = snapshot.invoices[0] | {
        "ID_HDON": str(CANONICAL_INVOICE_ID),
        "ID_HDON_DC": active_adjustment,
        "TONG_TIEN": 100,
        "TONG_NO": 100,
    }
    paid = active | {
        "ID_HDON": CANONICAL_INVOICE_ID,
        "ID_HDON_DC": paid_adjustment,
        "TTRANG_TTOAN": "DATT",
        "TONG_TIEN": 999,
        "TONG_NO": 0,
        "NGAY_TTOAN": "07/10/2026",
    }
    snapshot.invoices = [active]
    snapshot.paid_invoices = [paid]
    entry = await add_entry(hass)
    assert sensor_states(hass, entry)["invoice_this_period"].state == "100.0"
    snapshot.paid_invoices.append(paid | {"ID_HDON": PAID_INVOICE_ID, "TONG_TIEN": 50})
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    invoice = sensor_states(hass, entry)["invoice_this_period"]
    assert invoice.state == "150.0"
    assert invoice.attributes["target_month"] == "2026-10"
    assert invoice.attributes["source"] == "hoadon+lichsu-hoadon"
    assert invoice.attributes["period_basis"] == "invoice_month_label"


@pytest.mark.asyncio
async def test_runtime_final_counter_replacement_and_reconciled_bill_cycles(
    runtime_hass: HomeAssistant, offline_evn: OfflineEvn
) -> None:
    hass = runtime_hass
    snapshot = offline_evn.snapshot
    snapshot.monthly_readings[POINT] = [
        {
            "NAM": 2026,
            "THANG": 9,
            "KY": 1,
            "SO_CTO": "OLD",
            "BCS": "KT",
            "NGAY_CKY": "15/09/2026",
            "CHISO_MOI": 9000,
        },
        {
            "NAM": 2026,
            "THANG": 9,
            "KY": 2,
            "SO_CTO": "NEW",
            "BCS": "KT",
            "NGAY_CKY": "30/09/2026",
            "CHISO_MOI": 100,
        },
        {
            "NAM": 2026,
            "THANG": 10,
            "SO_CTO": "NEW",
            "BCS": "KT",
            "NGAY_CKY": "06/10/2026",
            "CHISO_MOI": 110,
        },
    ]
    active = {
        "ID_HDON": INVOICE_ID,
        "NAM": 2026,
        "THANG": 10,
        "KY": 2,
        "TONG_TIEN": 100,
        "TONG_NO": 100,
        "TTRANG_TTOAN": "CHUATT",
    }
    snapshot.invoices = [active]
    snapshot.paid_invoices = [
        active
        | {
            "TTRANG_TTOAN": "DATT",
            "TONG_TIEN": 999,
            "TONG_NO": 0,
            "NGAY_TTOAN": "07/10/2026",
        },
        {
            "ID_HDON": PAID_INVOICE_ID,
            "NAM": 2026,
            "THANG": 10,
            "KY": 1,
            "TONG_TIEN": 50,
            "NGAY_TTOAN": "01/11/2026",
        },
    ]
    entry = await add_entry(hass)
    identity = registry_identity(hass, entry)
    states = sensor_states(hass, entry)
    assert states["previous_cycle_final_index"].state == "100.0"
    assert states["previous_cycle_final_index"].attributes["target_month"] == "2026-09"
    assert (
        states["previous_cycle_final_index"].attributes["period_basis"]
        == "previous_completed_month_label"
    )
    assert "device_class" not in states["previous_cycle_final_index"].attributes
    assert "unit_of_measurement" not in states["previous_cycle_final_index"].attributes
    assert states["invoice_this_period"].state == "150.0"
    assert (
        states["invoice_this_period"].attributes["period_basis"]
        == "invoice_month_label"
    )
    snapshot.monthly_readings[POINT].append(
        snapshot.monthly_readings[POINT][1] | {"BCS": "BT"}
    )
    snapshot.paid_invoices.append(snapshot.paid_invoices[1] | {"TONG_TIEN": 60})
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert states["previous_cycle_final_index"].state == STATE_UNKNOWN
    assert states["invoice_this_period"].state == STATE_UNKNOWN
    assert registry_identity(hass, entry) == identity
