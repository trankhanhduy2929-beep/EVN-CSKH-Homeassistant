from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_USER,
    ConfigEntries,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResultType
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.entity_platform import PlatformData
from homeassistant.helpers.selector import SelectSelector, TextSelector
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components import evn_cskh as integration
from custom_components.evn_cskh import binary_sensor, button, config_flow, sensor
from custom_components.evn_cskh.api import (
    Customer,
    EvnAuthError,
    EvnClient,
    EvnConnectionError,
    EvnError,
    EvnResponseError,
    EvnUserActionRequired,
    Snapshot,
    TokenState,
)
from custom_components.evn_cskh.button import EvnButton
from custom_components.evn_cskh.config_flow import EvnConfigFlow, EvnOptionsFlow
from custom_components.evn_cskh.const import (
    CONF_CUSTOMERS,
    CONF_DEVICE_ID,
    CONF_SELECTED_CUSTOMERS,
    CONF_TOKENS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_HA_VERSION,
    NAME,
    PLATFORMS,
    VERSION,
    account_unique_id,
    interval_minutes,
)
from custom_components.evn_cskh.coordinator import (
    EvnConfigEntry,
    EvnCoordinator,
    customer_inventory,
    customer_key,
)
from custom_components.evn_cskh.sensor import CUSTOMER_SENSORS, POINT_SENSORS, EvnSensor

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ZoneInfo("Asia/Ho_Chi_Minh")
DEVICE_ID = "0123456789abcdef"
IDENTITY = {
    CONF_USERNAME: "offline-user",
    CONF_PASSWORD: "offline-password +&%/ mật khẩu",
}
FETCHED_AT = datetime(2026, 10, 7, 5, tzinfo=UTC)
PRIVATE_INVOICE_ID = "PRIVATE-INVOICE"
INFO = {
    "tenKhang": "Synthetic Public Name",
    "diaChi": "Synthetic Public Address",
    "dthoai": "0900000000",
    "maHdong": "SYNTHETIC-CONTRACT",
    "maDviCaptct": "PB",
}
POINT_A_READINGS = [
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
MONTHLY_READINGS = [
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
INVOICES = [
    {
        "ID_HDON": f"{PRIVATE_INVOICE_ID}-A",
        "TTRANG_TTOAN": "CHUATT",
        "TONG_NO": "-125000",
        "TONG_TIEN": 9999999,
        "NAM": 2026,
        "THANG": 10,
        "KY": 10,
        "DIEN_TTHU": "12.5",
        "MA_TCHUC": "BANK-A",
        "KENH_THANH_TOAN": "Synthetic channel",
    },
    {"ID_HDON": f"{PRIVATE_INVOICE_ID}-B", "TTRANG_TTOAN": "DATT"},
]
PAID_INVOICES = [
    {
        "ID_HDON": f"{PRIVATE_INVOICE_ID}-C",
        "TTRANG_TTOAN": "DATT",
        "NAM": 2026,
        "THANG": 9,
        "TONG_TIEN": 500000,
        "NGAY_TTOAN": "15/09/2026",
        "MA_TCHUC": "BANK-A",
        "KENH_THANH_TOAN": "Synthetic channel",
    }
]
BANKS = [{"MA_TCHUC": "BANK-A", "TEN_TCHUC": "Synthetic Bank"}]
CONTRACTS = [{"MA_HD": "SYNTHETIC-CONTRACT"}]


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    async def blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound requests are disabled in integration tests")

    monkeypatch.setattr(ClientSession, "_request", blocked)
    monkeypatch.setattr(asyncio, "open_connection", blocked)
    monkeypatch.setattr(sensor, "vn_now", lambda: date(2026, 10, 7))


@pytest_asyncio.fixture
async def hass(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[HomeAssistant]:
    instance = HomeAssistant(str(ROOT))
    instance.config_entries = ConfigEntries(instance, {})
    monkeypatch.setattr(instance.config_entries, "_async_schedule_save", Mock())
    monkeypatch.setattr(instance.config_entries, "async_schedule_reload", Mock())
    monkeypatch.setattr(
        instance.config_entries, "async_forward_entry_setups", AsyncMock()
    )
    monkeypatch.setattr(
        instance.config_entries,
        "async_unload_platforms",
        AsyncMock(return_value=True),
    )
    async with ClientSession() as session:
        monkeypatch.setattr(
            integration, "async_get_clientsession", Mock(return_value=session)
        )
        monkeypatch.setattr(
            config_flow, "async_get_clientsession", Mock(return_value=session)
        )
        yield instance
    for entry in instance.config_entries.async_entries():
        if hasattr(entry, "runtime_data"):
            await entry.runtime_data.async_shutdown()
    await instance.async_stop(force=True)


@pytest.fixture
def customers() -> list[Customer]:
    return [
        Customer("TEST-CUSTOMER", "TEST-UNIT", "PRIVATE NAME A", "PRIVATE CONTRACT A"),
        Customer("TEST-CUSTOMER", "OTHER-UNIT", "PRIVATE NAME B", "PRIVATE CONTRACT B"),
    ]


@pytest.fixture
def tokens() -> TokenState:
    return TokenState("offline-access", "offline-refresh")


def snapshot_for(customer: Customer) -> Snapshot:
    points = ("POINT-A", "POINT-B")
    return Snapshot(
        customer=customer,
        region="PB",
        measurement_points=[
            {
                "MA_DDO": "POINT-A",
                "TEN_KHANG": customer.name,
                "DIA_CHI": "PRIVATE ADDRESS",
            },
            {"MA_DDO": "POINT-B"},
        ],
        monthly={
            point: [
                {"NAM": 2026, "THANG": 9, "DIEN_TTHU": "900"},
                {"NAM": 2026, "THANG": 10, "DIEN_TTHU": value},
            ]
            for point, value in (("POINT-A", "12.5"), ("POINT-B", "27.5"))
        },
        daily={
            point: [
                {
                    "NGAY_HTHI": "05/10/2026 - 06/10/2026",
                    "BCS": "KT",
                    "DIEN_TTHU": value,
                }
            ]
            for point, value in (("POINT-A", "1.25"), ("POINT-B", "2.25"))
        },
        invoices=[
            {
                **INVOICES[0],
                "TEN_KHANG": customer.name,
                "DIA_CHI": "PRIVATE ADDRESS",
                "password": IDENTITY[CONF_PASSWORD],
                "access_token": "offline-access",
            },
            INVOICES[1],
        ],
        outages=[
            {
                "TGIAN_BDAU": "08/10/2099 08:00",
                "TGIAN_KTHUC": "08/10/2099 10:00",
                "KHUVUCMATDIEN": "Synthetic public area",
                "LY_DO": "Scheduled maintenance",
                "TEN_KHANG": customer.name,
                "DIA_CHI": "PRIVATE ADDRESS",
                "refresh_token": "offline-refresh",
            }
        ],
        fetched_at=FETCHED_AT,
        info=dict(INFO),
        contracts=[dict(row) for row in CONTRACTS],
        monthly_readings={
            point: [dict(row) for row in MONTHLY_READINGS] for point in points
        },
        daily_readings={
            "POINT-A": [dict(row) for row in POINT_A_READINGS],
            "POINT-B": [],
        },
        paid_invoices=[dict(row) for row in PAID_INVOICES],
        banks=[dict(row) for row in BANKS],
    )


@pytest.fixture
def mocked_client(
    monkeypatch: pytest.MonkeyPatch, customers: list[Customer], tokens: TokenState
) -> tuple[Mock, Mock]:
    client = Mock(spec=EvnClient)
    client.login = AsyncMock()
    client.customers = AsyncMock(return_value=customers)
    client.fetch_snapshot = AsyncMock(side_effect=snapshot_for)
    client.tokens = tokens
    factory = Mock(return_value=client)
    monkeypatch.setattr(integration, "EvnClient", factory)
    monkeypatch.setattr(config_flow, "EvnClient", factory)
    return client, factory


def make_entry(
    hass: HomeAssistant,
    customers: list[Customer],
    tokens: TokenState,
    *,
    options: dict[str, Any] | None = None,
    data_updates: dict[str, Any] | None = None,
    username: str = IDENTITY[CONF_USERNAME],
) -> EvnConfigEntry:
    data = {
        **IDENTITY,
        CONF_USERNAME: username,
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_CUSTOMERS: customer_inventory(customers),
        CONF_TOKENS: tokens.to_dict(),
        **(data_updates or {}),
    }
    if options is None:
        options = {
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            CONF_SELECTED_CUSTOMERS: [customer_key(customer) for customer in customers],
        }
    entry: EvnConfigEntry = ConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=account_unique_id(username),
        data=data,
        options=options,
        source=SOURCE_USER,
        version=1,
        minor_version=1,
        discovery_keys=MappingProxyType({}),
        subentries_data=(),
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    hass.config_entries._entries[entry.entry_id] = entry
    return entry


def make_flow(
    hass: HomeAssistant, entry: EvnConfigEntry | None = None
) -> EvnConfigFlow:
    flow = EvnConfigFlow()
    flow.hass = hass
    flow.flow_id = "offline-config-flow"
    flow.handler = DOMAIN
    flow.context = {"source": SOURCE_USER}
    if entry is not None:
        flow.context = {"source": SOURCE_REAUTH, "entry_id": entry.entry_id}
    return flow


def make_options(hass: HomeAssistant, entry: EvnConfigEntry) -> EvnOptionsFlow:
    flow = EvnConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.flow_id = "offline-options-flow"
    flow.handler = entry.entry_id
    flow.context = {"source": SOURCE_USER}
    return flow


def collect_sensor(
    coordinator: EvnCoordinator, entry: EvnConfigEntry
) -> list[EvnSensor]:
    result: list[EvnSensor] = []
    for snapshot in coordinator.data.values():
        result.extend(
            EvnSensor(coordinator, entry, snapshot.customer, description)
            for description in CUSTOMER_SENSORS
        )
        for point in snapshot.measurement_points:
            result.extend(
                EvnSensor(
                    coordinator,
                    entry,
                    snapshot.customer,
                    description,
                    point=point["MA_DDO"],
                )
                for description in POINT_SENSORS
            )
    return result


def collect_button(
    coordinator: EvnCoordinator, entry: EvnConfigEntry
) -> list[EvnButton]:
    return [
        EvnButton(coordinator, entry, snapshot.customer)
        for snapshot in coordinator.data.values()
    ]


def test_real_homeassistant_types_and_identity() -> None:
    assert issubclass(EvnConfigFlow, ConfigFlow)
    assert issubclass(EvnOptionsFlow, OptionsFlowWithReload)
    assert issubclass(EvnCoordinator, DataUpdateCoordinator)
    assert issubclass(EvnSensor, SensorEntity)
    assert issubclass(EvnButton, ButtonEntity)
    assert issubclass(binary_sensor.EvnBinarySensor, BinarySensorEntity)
    ha_path = __import__("homeassistant.core", fromlist=["core"]).__file__
    assert ha_path is not None
    assert "site-packages/homeassistant" in str(Path(ha_path))
    assert account_unique_id(" Offline-User ") == account_unique_id("offline-user")
    assert (
        account_unique_id("offline-user") == hashlib.sha256(b"offline-user").hexdigest()
    )
    assert DOMAIN == "evn_cskh"
    assert NAME == "EVN CSKH"
    assert VERSION == "0.5.0"
    assert MIN_HA_VERSION == "2025.12"
    assert PLATFORMS == (Platform.SENSOR, Platform.BUTTON, Platform.BINARY_SENSOR)
    assert binary_sensor.PLATFORMS is PLATFORMS


def test_manifest_version_matches_release() -> None:
    folder = ROOT / "custom_components" / DOMAIN
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest == {
        "domain": DOMAIN,
        "name": NAME,
        "codeowners": [],
        "config_flow": True,
        "documentation": "https://cskh.evn.com.vn",
        "integration_type": "service",
        "iot_class": "cloud_polling",
        "requirements": [],
        "version": VERSION,
    }


def test_complete_translations() -> None:
    folder = ROOT / "custom_components" / DOMAIN
    english = json.loads((folder / "strings.json").read_text())
    assert english == json.loads((folder / "translations" / "en.json").read_text())
    vietnamese = json.loads((folder / "translations" / "vi.json").read_text())

    def leaves(value: dict[str, Any], prefix: str = "") -> set[str]:
        result = set()
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if isinstance(item, dict):
                result.update(leaves(item, path))
            else:
                assert isinstance(item, str) and item
                result.add(path)
        return result

    assert leaves(english) == leaves(vietnamese)
    point_keys = {description.key for description in POINT_SENSORS}
    sensor_keys = point_keys | {description.key for description in CUSTOMER_SENSORS}
    assert set(english["entity"]["sensor"]) == sensor_keys
    assert set(vietnamese["entity"]["sensor"]) == sensor_keys
    assert set(english["entity"]["binary_sensor"]) == {
        "outage_scheduled",
        "outage_soon",
        "outage_active",
    }
    assert (
        english["entity"]["binary_sensor"]["outage_scheduled"]["name"]
        == "Outage scheduled"
    )
    assert (
        vietnamese["entity"]["binary_sensor"]["outage_scheduled"]["name"]
        == "Lịch cắt điện"
    )
    assert (
        english["entity"]["binary_sensor"]["outage_soon"]["name"]
        == "Outage soon (within 24 hours)"
    )
    assert (
        english["entity"]["binary_sensor"]["outage_active"]["name"]
        == "Within scheduled outage window"
    )
    assert (
        vietnamese["entity"]["binary_sensor"]["outage_soon"]["name"]
        == "Sắp cắt điện (≤24 giờ)"
    )
    assert (
        vietnamese["entity"]["binary_sensor"]["outage_active"]["name"]
        == "Đang trong khung giờ cắt điện"
    )
    assert set(english["entity"]["button"]) == {"refresh"}
    assert set(vietnamese["entity"]["button"]) == {"refresh"}
    assert vietnamese["entity"]["button"]["refresh"]["name"]
    for names in (english["entity"]["button"], vietnamese["entity"]["button"]):
        assert "{" not in names["refresh"]["name"]
    for description in (*POINT_SENSORS, *CUSTOMER_SENSORS):
        assert description.translation_key == description.key
        for names in (english["entity"]["sensor"], vietnamese["entity"]["sensor"]):
            name = names[description.key]["name"]
            assert name
            assert ("{measurement_point}" in name) == (
                description.key in {item.key for item in POINT_SENSORS[:8]}
            )
    labels = {
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
    }
    for key, name in labels.items():
        assert vietnamese["entity"]["sensor"][key]["name"] == name
    assert (
        english["entity"]["sensor"]["current_provisional_index"]["name"]
        == "Provisional index"
    )
    assert (
        english["entity"]["sensor"]["previous_cycle_final_index"]["name"]
        == "Previous cycle final index"
    )


@pytest.mark.parametrize(
    "value", [None, True, False, "60", 59, 1441, 60.5, float("nan"), float("inf")]
)
def test_invalid_interval(value: object) -> None:
    with pytest.raises(ValueError):
        interval_minutes(value)


@pytest.mark.parametrize("value", [60, 360, 1440, 60.0])
def test_valid_interval(value: float) -> None:
    assert interval_minutes(value) == int(value)


@pytest.mark.asyncio
async def test_user_schema_and_success(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, factory = mocked_client
    flow = make_flow(hass)
    form = await flow.async_step_user()
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "user"
    schema = form["data_schema"]
    assert schema is not None
    assert isinstance(schema.schema[CONF_PASSWORD], TextSelector)
    assert schema.schema[CONF_PASSWORD].config["type"] == "password"
    assert schema(IDENTITY) == IDENTITY
    with pytest.raises(vol.Invalid):
        schema({CONF_USERNAME: "offline-user"})
    result = await flow.async_step_user(IDENTITY | {CONF_USERNAME: " Offline-User "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME
    assert result["context"]["unique_id"] == account_unique_id("offline-user")
    data = result["data"]
    assert data[CONF_USERNAME] == "Offline-User"
    assert data[CONF_PASSWORD] == IDENTITY[CONF_PASSWORD]
    assert re.fullmatch(r"[0-9a-f]{16}", data[CONF_DEVICE_ID])
    assert data[CONF_CUSTOMERS] == customer_inventory(customers)
    assert all(set(row) == {"code", "management_unit"} for row in data[CONF_CUSTOMERS])
    assert data[CONF_TOKENS] == tokens.to_dict()
    assert result["options"] == {
        CONF_UPDATE_INTERVAL: 360,
        CONF_SELECTED_CUSTOMERS: [customer_key(customer) for customer in customers],
    }
    factory.assert_called_once()
    assert factory.call_args.args[3] == data[CONF_DEVICE_ID]
    client.login.assert_awaited_once_with()
    client.customers.assert_awaited_once_with()
    client.fetch_snapshot.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("reauth", [False, True])
@pytest.mark.parametrize("method", ["login", "customers"])
@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (EvnUserActionRequired, "user_action_required"),
        (EvnAuthError, "invalid_auth"),
        (EvnConnectionError, "cannot_connect"),
        (EvnResponseError, "invalid_response"),
        (EvnError, "unknown"),
    ],
)
async def test_config_errors_are_safe(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    reauth: bool,
    method: str,
    exception: type[EvnError],
    error: str,
) -> None:
    client, factory = mocked_client
    getattr(client, method).side_effect = exception()
    entry = make_entry(hass, customers, tokens) if reauth else None
    flow = make_flow(hass, entry)
    result = await (
        flow.async_step_reauth_confirm(IDENTITY)
        if reauth
        else flow.async_step_user(IDENTITY)
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert IDENTITY[CONF_PASSWORD] not in str(result)
    assert tokens.access_token not in str(result)
    cast(Mock, hass.config_entries.async_schedule_reload).assert_not_called()
    if entry is not None:
        assert entry.data[CONF_TOKENS] == tokens.to_dict()
        assert factory.call_args.args[3] == DEVICE_ID


@pytest.mark.asyncio
@pytest.mark.parametrize("reauth", [False, True])
async def test_no_customers_aborts_without_fake_device(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    reauth: bool,
) -> None:
    client, _ = mocked_client
    client.customers.return_value = []
    entry = make_entry(hass, customers, tokens) if reauth else None
    flow = make_flow(hass, entry)
    result = await (
        flow.async_step_reauth_confirm(IDENTITY)
        if reauth
        else flow.async_step_user(IDENTITY)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_customers"
    client.login.assert_awaited_once()
    client.customers.assert_awaited_once()
    client.fetch_snapshot.assert_not_awaited()
    cast(Mock, hass.config_entries.async_schedule_reload).assert_not_called()


@pytest.mark.asyncio
async def test_invalid_credentials_and_missing_tokens(
    hass: HomeAssistant, mocked_client: tuple[Mock, Mock]
) -> None:
    client, factory = mocked_client
    flow = make_flow(hass)
    result = await flow.async_step_user({CONF_USERNAME: " ", CONF_PASSWORD: ""})
    assert result["errors"] == {
        CONF_USERNAME: "invalid_username",
        CONF_PASSWORD: "invalid_password",
    }
    factory.assert_not_called()
    client.tokens = None
    result = await flow.async_step_user(IDENTITY)
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_device_id_stable_on_config_retry(
    hass: HomeAssistant, mocked_client: tuple[Mock, Mock]
) -> None:
    client, factory = mocked_client
    client.login.side_effect = [EvnConnectionError(), None]
    flow = make_flow(hass)
    first = await flow.async_step_user(IDENTITY)
    assert first["errors"] == {"base": "cannot_connect"}
    result = await flow.async_step_user(IDENTITY)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert factory.call_args_list[0].args[3] == factory.call_args_list[1].args[3]
    assert factory.call_args.args[3] == result["data"][CONF_DEVICE_ID]


@pytest.mark.asyncio
async def test_duplicate_account_does_not_login(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    _, factory = mocked_client
    make_entry(hass, customers, tokens)
    flow = make_flow(hass)
    with pytest.raises(AbortFlow, match="already_configured"):
        await flow.async_step_user(IDENTITY)
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_reauth_checks_account_and_preserves_selection_and_device(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, factory = mocked_client
    options = {
        CONF_UPDATE_INTERVAL: 1440,
        CONF_SELECTED_CUSTOMERS: [customer_key(customers[1])],
    }
    entry = make_entry(hass, customers, tokens, options=options)
    flow = make_flow(hass, entry)
    form = await flow.async_step_reauth(entry.data)
    assert form["step_id"] == "reauth_confirm"
    result = await flow.async_step_reauth_confirm(
        IDENTITY | {CONF_USERNAME: "wrong-user"}
    )
    assert result["errors"] == {"base": "wrong_account"}
    factory.assert_not_called()
    rotated = TokenState(
        "rotated-access",
        "rotated-refresh",
        customers[1].code,
        customers[1].management_unit,
    )
    client.tokens = rotated
    client.customers.return_value = [customers[1]]
    result = await flow.async_step_reauth_confirm(
        IDENTITY
        | {CONF_USERNAME: " OFFLINE-USER ", CONF_PASSWORD: "new-offline-password"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_USERNAME] == "OFFLINE-USER"
    assert entry.data[CONF_PASSWORD] == "new-offline-password"
    assert entry.data[CONF_DEVICE_ID] == DEVICE_ID
    assert entry.data[CONF_TOKENS] == rotated.to_dict()
    assert entry.data[CONF_CUSTOMERS] == customer_inventory([customers[1]])
    assert dict(entry.options) == options
    assert not entry.update_listeners
    assert factory.call_args.args[3] == DEVICE_ID
    cast(Mock, hass.config_entries.async_schedule_reload).assert_called_once_with(
        entry.entry_id
    )


@pytest.mark.asyncio
async def test_options_schema_uses_full_inventory_not_selected_subset(
    hass: HomeAssistant, customers: list[Customer], tokens: TokenState
) -> None:
    entry = make_entry(
        hass,
        customers,
        tokens,
        options={CONF_SELECTED_CUSTOMERS: [customer_key(customers[0])]},
    )
    flow = make_options(hass, entry)
    result = await flow.async_step_init()
    schema = result["data_schema"]
    assert schema is not None
    selector = schema.schema[CONF_SELECTED_CUSTOMERS]
    assert isinstance(selector, SelectSelector)
    assert selector.config["multiple"] is True
    assert selector.config["custom_value"] is False
    assert set(selector.config["options"]) == {
        customer_key(customer) for customer in customers
    }
    valid = {
        CONF_UPDATE_INTERVAL: 60,
        CONF_SELECTED_CUSTOMERS: [customer_key(customers[1])],
    }
    assert schema(valid) == valid
    assert (
        schema({CONF_SELECTED_CUSTOMERS: [customer_key(customers[1])]})[
            CONF_UPDATE_INTERVAL
        ]
        == 360
    )
    for minutes in (59, 1441):
        with pytest.raises(vol.Invalid):
            schema(valid | {CONF_UPDATE_INTERVAL: minutes})
    with pytest.raises(vol.Invalid):
        schema(valid | {CONF_SELECTED_CUSTOMERS: ["UNAUTHORIZED:TEST"]})
    with pytest.raises(vol.Invalid):
        schema(valid | {CONF_SELECTED_CUSTOMERS: customer_key(customers[0])})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("updates", "errors"),
    [
        ({CONF_UPDATE_INTERVAL: 59}, {CONF_UPDATE_INTERVAL: "invalid_interval"}),
        ({CONF_UPDATE_INTERVAL: 1441}, {CONF_UPDATE_INTERVAL: "invalid_interval"}),
        ({CONF_UPDATE_INTERVAL: 60.5}, {CONF_UPDATE_INTERVAL: "invalid_interval"}),
        (
            {CONF_UPDATE_INTERVAL: float("nan")},
            {CONF_UPDATE_INTERVAL: "invalid_interval"},
        ),
        ({CONF_SELECTED_CUSTOMERS: []}, {CONF_SELECTED_CUSTOMERS: "no_selection"}),
        ({CONF_SELECTED_CUSTOMERS: None}, {CONF_SELECTED_CUSTOMERS: "no_selection"}),
        (
            {CONF_SELECTED_CUSTOMERS: ["UNAUTHORIZED:TEST"]},
            {CONF_SELECTED_CUSTOMERS: "invalid_customer"},
        ),
        (
            {CONF_SELECTED_CUSTOMERS: [None]},
            {CONF_SELECTED_CUSTOMERS: "invalid_customer"},
        ),
    ],
)
async def test_options_errors(
    hass: HomeAssistant,
    customers: list[Customer],
    tokens: TokenState,
    updates: dict[str, Any],
    errors: dict[str, str],
) -> None:
    entry = make_entry(hass, customers, tokens)
    flow = make_options(hass, entry)
    result = await flow.async_step_init(
        {
            CONF_UPDATE_INTERVAL: 360,
            CONF_SELECTED_CUSTOMERS: [customer_key(customers[0])],
        }
        | updates
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors
    cast(Mock, hass.config_entries.async_schedule_reload).assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [60, 1440])
async def test_options_native_reload_exactly_once_when_changed(
    hass: HomeAssistant, customers: list[Customer], tokens: TokenState, minutes: int
) -> None:
    entry = make_entry(hass, customers, tokens)
    flow = make_options(hass, entry)
    result = await flow.async_step_init(
        {
            CONF_UPDATE_INTERVAL: minutes,
            CONF_SELECTED_CUSTOMERS: [
                customer_key(customers[1]),
                customer_key(customers[1]),
            ],
        }
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_UPDATE_INTERVAL: minutes,
        CONF_SELECTED_CUSTOMERS: [customer_key(customers[1])],
    }
    await hass.config_entries.options.async_finish_flow(flow, result)
    cast(Mock, hass.config_entries.async_schedule_reload).assert_called_once_with(
        entry.entry_id
    )
    assert dict(entry.options) == result["data"]
    await hass.config_entries.options.async_finish_flow(flow, result)
    cast(Mock, hass.config_entries.async_schedule_reload).assert_called_once()


@pytest.mark.asyncio
async def test_setup_lazy_fetch_token_rotation_and_restart(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory = mocked_client
    entry = make_entry(hass, customers, tokens)
    update = Mock(wraps=hass.config_entries.async_update_entry)
    monkeypatch.setattr(hass.config_entries, "async_update_entry", update)
    rotated = TokenState(
        "rotated-access",
        "rotated-refresh",
        customers[1].code,
        customers[1].management_unit,
    )

    async def fetch(customer: Customer) -> Snapshot:
        factory.call_args.kwargs["on_tokens"](rotated)
        assert entry.data[CONF_TOKENS] == rotated.to_dict()
        return snapshot_for(customer)

    client.fetch_snapshot.side_effect = fetch
    assert await integration.async_setup_entry(hass, entry) is True
    coordinator = entry.runtime_data
    assert isinstance(coordinator, EvnCoordinator)
    assert coordinator.config_entry is entry
    assert coordinator.client is client
    assert coordinator.update_interval == timedelta(minutes=360)
    assert set(coordinator.data) == {customer_key(customer) for customer in customers}
    assert factory.call_args.kwargs["tokens"] == tokens
    assert factory.call_args.args[3] == DEVICE_ID
    client.login.assert_not_awaited()
    client.customers.assert_awaited_once_with()
    assert update.call_count == 1
    assert not entry.update_listeners
    callback = factory.call_args.kwargs["on_tokens"]
    callback(rotated)
    assert update.call_count == 1
    assert entry.data[CONF_CUSTOMERS] == customer_inventory(customers)
    cast(Mock, hass.config_entries.async_forward_entry_setups).assert_awaited_once_with(
        entry, PLATFORMS
    )
    cast(Mock, hass.config_entries.async_schedule_reload).assert_not_called()
    assert await integration.async_unload_entry(hass, entry) is True
    cast(Mock, hass.config_entries.async_unload_platforms).assert_awaited_once_with(
        entry, PLATFORMS
    )
    await entry._async_process_on_unload(hass)
    assert coordinator._shutdown_requested
    client.fetch_snapshot.side_effect = snapshot_for
    assert await integration.async_setup_entry(hass, entry) is True
    assert entry.runtime_data is not coordinator
    assert factory.call_args.kwargs["tokens"] == rotated
    assert factory.call_args.args[3] == DEVICE_ID
    assert entry.data[CONF_DEVICE_ID] == DEVICE_ID
    assert not entry.update_listeners
    cast(Mock, hass.config_entries.async_schedule_reload).assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("unloaded", [False, True])
async def test_unload_result(
    hass: HomeAssistant, customers: list[Customer], tokens: TokenState, unloaded: bool
) -> None:
    entry = make_entry(hass, customers, tokens)
    cast(AsyncMock, hass.config_entries.async_unload_platforms).return_value = unloaded
    assert await integration.async_unload_entry(hass, entry) is unloaded
    cast(Mock, hass.config_entries.async_unload_platforms).assert_awaited_once_with(
        entry, PLATFORMS
    )


@pytest.mark.asyncio
async def test_setup_without_tokens_is_lazy(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, factory = mocked_client
    entry = make_entry(hass, customers, tokens, data_updates={CONF_TOKENS: None})
    assert await integration.async_setup_entry(hass, entry)
    assert factory.call_args.kwargs["tokens"] is None
    client.login.assert_not_awaited()
    client.customers.assert_awaited_once()


@pytest.mark.asyncio
async def test_corrupt_tokens_require_reauth_before_api(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    _, factory = mocked_client
    entry = make_entry(
        hass, customers, tokens, data_updates={CONF_TOKENS: {"access_token": "bad"}}
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await integration.async_setup_entry(hass, entry)
    factory.assert_not_called()
    cast(Mock, hass.config_entries.async_forward_entry_setups).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "options", [{}, {CONF_SELECTED_CUSTOMERS: []}, {CONF_SELECTED_CUSTOMERS: None}]
)
async def test_empty_selection_never_defaults_to_all(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    options: dict[str, Any],
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens, options=options)
    with pytest.raises(ConfigEntryError) as caught:
        await integration.async_setup_entry(hass, entry)
    assert caught.value.translation_key == "invalid_selection"
    client.login.assert_not_awaited()
    client.customers.assert_not_awaited()
    client.fetch_snapshot.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_rejects_invalid_interval(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, _ = mocked_client
    entry = make_entry(
        hass,
        customers,
        tokens,
        options={
            CONF_UPDATE_INTERVAL: 1,
            CONF_SELECTED_CUSTOMERS: [customer_key(customers[0])],
        },
    )
    with pytest.raises(ConfigEntryError) as caught:
        EvnCoordinator(hass, entry, cast(EvnClient, client))
    assert caught.value.translation_key == "invalid_interval"


@pytest.mark.asyncio
async def test_coordinator_selected_authorized_subset_sequential(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, _ = mocked_client
    third = Customer(
        "OTHER-CUSTOMER", "TEST-UNIT", "PRIVATE NAME C", "PRIVATE CONTRACT C"
    )
    client.customers.return_value = [*customers, third]
    entry = make_entry(
        hass,
        customers,
        tokens,
        options={
            CONF_UPDATE_INTERVAL: 60,
            CONF_SELECTED_CUSTOMERS: [customer_key(third), customer_key(customers[0])],
        },
    )
    active = False
    order = []

    async def fetch(customer: Customer) -> Snapshot:
        nonlocal active
        assert not active
        active = True
        order.append(customer_key(customer))
        await asyncio.sleep(0)
        active = False
        return snapshot_for(customer)

    client.fetch_snapshot.side_effect = fetch
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    assert coordinator.update_interval == timedelta(minutes=60)
    assert (
        list(coordinator.data)
        == order
        == [customer_key(third), customer_key(customers[0])]
    )
    assert entry.data[CONF_CUSTOMERS] == customer_inventory([*customers, third])
    assert len(entry.data[CONF_CUSTOMERS]) == 3
    assert not entry.update_listeners
    cast(Mock, hass.config_entries.async_schedule_reload).assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("linked", [False, True])
async def test_removed_selected_customer_requires_auth_and_does_not_fetch(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    linked: bool,
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens)
    client.customers.return_value = [customers[0]] if linked else []
    with pytest.raises(ConfigEntryAuthFailed) as caught:
        await integration.async_setup_entry(hass, entry)
    assert caught.value.translation_key == (
        "customer_removed" if linked else "no_customers"
    )
    assert customers[1].code not in str(caught.value)
    assert customers[1].management_unit not in str(caught.value)
    assert entry.data[CONF_CUSTOMERS] == customer_inventory(
        client.customers.return_value
    )
    client.fetch_snapshot.assert_not_awaited()
    cast(Mock, hass.config_entries.async_forward_entry_setups).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["customers", "fetch_snapshot"])
@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (EvnAuthError, ConfigEntryAuthFailed),
        (EvnUserActionRequired, ConfigEntryAuthFailed),
        (EvnConnectionError, UpdateFailed),
        (EvnResponseError, UpdateFailed),
        (EvnError, UpdateFailed),
    ],
)
async def test_coordinator_exception_mapping(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    method: str,
    failure: type[EvnError],
    expected: type[Exception],
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens)
    coordinator = EvnCoordinator(hass, entry, cast(EvnClient, client))
    getattr(client, method).side_effect = failure()
    with pytest.raises(expected) as caught:
        await coordinator._async_update_data()
    assert IDENTITY[CONF_USERNAME] not in str(caught.value)
    assert IDENTITY[CONF_PASSWORD] not in str(caught.value)
    assert tokens.access_token not in str(caught.value)
    assert tokens.refresh_token not in str(caught.value)
    assert not isinstance(caught.value, ConfigEntryAuthFailed) or issubclass(
        failure, EvnAuthError
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [EvnConnectionError, EvnResponseError, EvnError])
async def test_failed_initial_update_is_retryable_not_forwarded(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    failure: type[EvnError],
) -> None:
    client, _ = mocked_client
    client.fetch_snapshot.side_effect = failure()
    entry = make_entry(hass, customers, tokens)
    with pytest.raises(ConfigEntryNotReady):
        await integration.async_setup_entry(hass, entry)
    assert not hasattr(entry, "runtime_data")
    cast(Mock, hass.config_entries.async_forward_entry_setups).assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_batch_hides_stale_values_and_recovers(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    previous = coordinator.data
    entities = collect_sensor(coordinator, entry)
    previous_values = [entity.native_value for entity in entities]
    changed = snapshot_for(customers[0])
    changed.monthly["POINT-A"][1]["DIEN_TTHU"] = 777
    client.fetch_snapshot.side_effect = [changed, EvnResponseError()]
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert coordinator.data is previous
    assert all(not entity.available for entity in entities)
    assert all(entity.native_value is None for entity in entities)
    assert all(entity.extra_state_attributes == {} for entity in entities)
    client.fetch_snapshot.side_effect = snapshot_for
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert all(entity.available for entity in entities)
    assert [entity.native_value for entity in entities] == previous_values


@pytest.mark.asyncio
async def test_snapshot_scope_mismatch_and_customer_key_collision_fail(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens)
    coordinator = EvnCoordinator(hass, entry, cast(EvnClient, client))
    client.fetch_snapshot.side_effect = None
    client.fetch_snapshot.return_value = snapshot_for(
        Customer("UNAUTHORIZED", "OTHER-UNIT")
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    client.customers.return_value = [Customer("b:c", "a"), Customer("c", "a:b")]
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_sensor_platform_all_points_native_values_and_private_attributes(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    add = Mock()
    await sensor.async_setup_entry(hass, entry, add)
    add.assert_called_once()
    entities: list[EvnSensor] = add.call_args.args[0]
    assert len(entities) == 94
    assert len({entity.unique_id for entity in entities}) == 94
    assert len(POINT_SENSORS) == 13
    assert len(CUSTOMER_SENSORS) == 21
    assert (
        len(
            {
                tuple(entity.device_info["identifiers"])
                for entity in entities
                if entity.device_info
            }
        )
        == 2
    )
    expected: dict[tuple[str, str | None], Any] = {
        ("monthly_energy", "POINT-A"): 12.5,
        ("monthly_energy", "POINT-B"): 27.5,
        ("prev_month_energy", "POINT-A"): 900.0,
        ("prev_month_energy", "POINT-B"): 900.0,
        ("average_12m_energy", "POINT-A"): (900.0 + 12.5) / 2,
        ("average_12m_energy", "POINT-B"): (900.0 + 27.5) / 2,
        ("month_over_month", "POINT-A"): (12.5 - 900.0) / 900.0 * 100,
        ("month_over_month", "POINT-B"): (27.5 - 900.0) / 900.0 * 100,
        ("daily_energy", "POINT-A"): 1.25,
        ("daily_energy", "POINT-B"): 2.25,
        ("meter_reading", "POINT-A"): 1012.5,
        ("meter_reading", "POINT-B"): 1050.0,
        ("meter_multiplier", "POINT-A"): 2.0,
        ("meter_multiplier", "POINT-B"): 3.0,
        ("meter_read_date", "POINT-A"): "06/10/2026 08:00",
        ("meter_read_date", "POINT-B"): "31/10/2026",
        ("outstanding_amount", None): 125000.0,
        ("outstanding_count", None): 1,
        ("latest_invoice_amount", None): 9999999.0,
        ("latest_invoice_status", None): "Chưa thanh toán",
        ("paid_invoice_count", None): 1,
        ("next_outage", None): datetime(2099, 10, 8, 8, tzinfo=LOCAL),
        ("next_outage_end", None): datetime(2099, 10, 8, 10, tzinfo=LOCAL),
        ("next_outage_duration", None): 2.0,
        ("next_outage_area", None): "Synthetic public area",
        ("next_outage_reason", None): "Scheduled maintenance",
        ("outage_count", None): 1,
        ("fetched_at", None): FETCHED_AT,
        ("current_provisional_index", "POINT-A"): 1012.5,
        ("current_provisional_index", "POINT-B"): None,
        ("previous_cycle_final_index", "POINT-A"): None,
        ("previous_cycle_final_index", "POINT-B"): None,
        ("consumption_today", "POINT-A"): None,
        ("consumption_today", "POINT-B"): None,
        ("consumption_yesterday", "POINT-A"): None,
        ("consumption_yesterday", "POINT-B"): None,
        ("consumption_two_days_ago", "POINT-A"): None,
        ("consumption_two_days_ago", "POINT-B"): None,
        ("current_period_detail", None): "10-2026",
        ("invoice_year", None): 2026,
        ("invoice_this_period", None): 9999999.0,
        ("invoice_prev_period", None): 500000.0,
        ("invoice_prev_prev_period", None): None,
        ("consumption_this_period", None): 40.0,
        ("consumption_prev_period", None): 1800.0,
        ("consumption_prev_prev_period", None): None,
        ("next_update", None): None,
    }
    assert {key for key, _ in expected} == {
        description.key for description in (*CUSTOMER_SENSORS, *POINT_SENSORS)
    }
    for entity in entities:
        assert isinstance(entity, SensorEntity)
        assert entity.has_entity_name
        assert not entity.should_poll
        assert entity.available
        assert entity.icon == entity.entity_description.icon
        assert entity.icon is not None and entity.icon.startswith("mdi:")
        attributes = entity.extra_state_attributes
        key = entity.entity_description.key
        point = attributes.get("measurement_point")
        expected_value = expected[(key, point)]
        if isinstance(expected_value, float):
            assert entity.native_value == pytest.approx(expected_value)
        else:
            assert entity.native_value == expected_value
        assert set(attributes) <= {
            "period",
            "measurement_point",
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
            "schedule_end",
            "start",
            "end",
            "duration_hours",
            "count",
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
        public = str(attributes) + str(entity.device_info) + str(entity.unique_id)
        for private in (
            "PRIVATE NAME",
            "PRIVATE CONTRACT",
            "PRIVATE ADDRESS",
            PRIVATE_INVOICE_ID,
            IDENTITY[CONF_USERNAME],
            IDENTITY[CONF_PASSWORD],
            tokens.access_token,
            tokens.refresh_token,
        ):
            assert private not in public
        assert entity.unique_id is not None and re.fullmatch(
            r"[0-9a-f]{64}", entity.unique_id
        )
        assert entity.device_info is not None
        assert entity.device_info["manufacturer"] == "EVN"
        assert entity.device_info["model"] == "Customer account"
        if key in ("monthly_energy", "prev_month_energy", "daily_energy"):
            assert entity.device_class is SensorDeviceClass.ENERGY
            assert entity.native_unit_of_measurement == "kWh"
            assert entity.state_class is None
            assert (
                attributes["period"]
                == {
                    "monthly_energy": "2026-10",
                    "prev_month_energy": "2026-09",
                    "daily_energy": "05/10/2026 - 06/10/2026",
                }[key]
            )
            assert entity.translation_placeholders == {
                "measurement_point": attributes["measurement_point"]
            }
        elif key == "average_12m_energy":
            assert entity.device_class is None
            assert entity.native_unit_of_measurement == "kWh"
            assert entity.state_class is SensorStateClass.MEASUREMENT
        elif key == "month_over_month":
            assert entity.device_class is None
            assert entity.native_unit_of_measurement == "%"
            assert entity.state_class is SensorStateClass.MEASUREMENT
            assert point is not None
            current = 12.5 if point == "POINT-A" else 27.5
            assert attributes["current"] == pytest.approx(current)
            assert attributes["previous"] == pytest.approx(900.0)
            assert attributes["delta"] == pytest.approx(current - 900.0)
        elif key in ("meter_reading", "meter_multiplier", "meter_read_date"):
            assert entity.device_class is None
            assert entity.native_unit_of_measurement is None
            assert entity.state_class is None
            if key == "meter_reading":
                assert attributes["old"] is not None
                assert attributes["new"] == pytest.approx(entity.native_value)
                assert attributes["multiplier"] == pytest.approx(
                    2.0 if point == "POINT-A" else 3.0
                )
                assert attributes["kind"] == "KT"
                assert attributes["period"] == expected[("meter_read_date", point)]
        elif key in ("outstanding_amount", "latest_invoice_amount"):
            assert entity.device_class is SensorDeviceClass.MONETARY
            assert entity.native_unit_of_measurement == "VND"
            assert entity.state_class is None
            if key == "latest_invoice_amount":
                assert attributes["status_label"] == "Chưa thanh toán"
                assert attributes["cycle"] == 10
                assert attributes["energy"] == pytest.approx(12.5)
                assert attributes["energy_unit"] == "kWh"
                assert attributes["org_code"] == "BANK-A"
                assert attributes["payment_channel_label"] == "Synthetic Bank"
                assert attributes["paid_date"] is None
                assert attributes["due_date"] is None
        elif key in ("next_outage", "next_outage_end", "fetched_at"):
            assert entity.device_class is SensorDeviceClass.TIMESTAMP
            assert entity.native_unit_of_measurement is None
            assert isinstance(entity.native_value, datetime)
            assert entity.native_value.tzinfo is not None
        if key in ("paid_invoice_count", "outstanding_count", "latest_invoice_status"):
            assert entity.device_class is None
            assert entity.native_unit_of_measurement is None
        if key == "next_outage_duration":
            assert entity.device_class is SensorDeviceClass.DURATION
            assert entity.native_unit_of_measurement == "h"
        if key in (
            "fetched_at",
            "meter_multiplier",
            "meter_read_date",
            "paid_invoice_count",
            "next_update",
            "outage_count",
        ):
            assert entity.entity_category is EntityCategory.DIAGNOSTIC
        else:
            assert entity.entity_category is None
        if key == "next_outage":
            assert (
                attributes["start"]
                == datetime(2099, 10, 8, 8, tzinfo=LOCAL).isoformat()
            )
            assert (
                attributes["end"] == datetime(2099, 10, 8, 10, tzinfo=LOCAL).isoformat()
            )
            assert attributes["area"] == "Synthetic public area"
            assert attributes["reason"] == "Scheduled maintenance"
            assert attributes["duration_hours"] == pytest.approx(2.0)
            assert attributes["count"] == 1
        if key == "fetched_at":
            assert attributes["customer_name"] == INFO["tenKhang"]
            assert attributes["address"] == INFO["diaChi"]
            assert attributes["phone"] == INFO["dthoai"]
            assert attributes["contract"] == INFO["maHdong"]
            assert attributes["region_code"] == "PB"
            assert attributes["contracts"] == 1
            assert attributes["banks"] == 1
            assert attributes["paid"] == 1
        if key in ("outstanding_amount", "outstanding_count", "latest_invoice_amount"):
            assert "customer_name" not in attributes


@pytest.mark.asyncio
async def test_empty_and_uncertain_data_not_fabricated(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    snapshot = coordinator.data[customer_key(customers[0])]
    snapshot.monthly["POINT-A"] = []
    snapshot.daily["POINT-A"] = []
    snapshot.invoices = []
    snapshot.outages = []
    snapshot.monthly_readings = {}
    snapshot.daily_readings = {}
    snapshot.paid_invoices = []
    snapshot.banks = []
    snapshot.contracts = []
    snapshot.info = {}
    entities = collect_sensor(coordinator, entry)
    states = {
        (
            entity.entity_description.key,
            entity.extra_state_attributes.get("measurement_point"),
        ): entity.native_value
        for entity in entities
    }
    assert states[("monthly_energy", "POINT-A")] is None
    assert states[("prev_month_energy", "POINT-A")] is None
    assert states[("average_12m_energy", "POINT-A")] is None
    assert states[("month_over_month", "POINT-A")] is None
    assert states[("daily_energy", "POINT-A")] is None
    assert states[("meter_reading", "POINT-A")] is None
    assert states[("meter_multiplier", "POINT-A")] is None
    assert states[("meter_read_date", "POINT-A")] is None
    assert states[("outstanding_amount", None)] == 0.0
    assert states[("outstanding_count", None)] == 0
    assert states[("latest_invoice_amount", None)] is None
    assert states[("latest_invoice_status", None)] is None
    assert states[("paid_invoice_count", None)] == 0
    assert states[("next_outage", None)] is None
    assert all(entity.available for entity in entities)
    snapshot.monthly["POINT-A"] = [{"NAM": 2026, "THANG": 10, "DIEN_TTHU": "1,234"}]
    snapshot.daily["POINT-A"] = [
        {"NGAY": "06/10/2026", "BCS": "KT", "DIEN_TTHU": "NaN"}
    ]
    snapshot.invoices = [
        {"ID_HDON": "PRIVATE INVOICE", "TTRANG_TTOAN": "CHUATT", "TONG_TIEN": 999}
    ]
    snapshot.monthly_readings["POINT-A"] = [{"NGAY_CKY": "bad", "CHISO_MOI": 1}]
    snapshot.daily_readings["POINT-A"] = [{"NGAY": "bad", "CHISO_MOI": 1}]
    for entity in entities:
        if entity.extra_state_attributes.get(
            "measurement_point"
        ) == "POINT-A" or entity.entity_description.key.startswith(
            ("outstanding", "latest_invoice")
        ):
            assert entity.native_value is None
            assert entity.available
    snapshot.outages = [{"TGIAN_BDAU": "01/01/2000 08:00"}]
    outage_entity = next(
        entity for entity in entities if entity.entity_description.key == "next_outage"
    )
    assert outage_entity.native_value is None and outage_entity.available
    assert set(outage_entity.extra_state_attributes) == {"last_update", "count"}
    assert outage_entity.extra_state_attributes["count"] == 1
    snapshot.invoices = []
    snapshot.paid_invoices = [dict(row) for row in PAID_INVOICES]
    invoice_amount = next(
        entity
        for entity in entities
        if entity.entity_description.key == "latest_invoice_amount"
    )
    invoice_status = next(
        entity
        for entity in entities
        if entity.entity_description.key == "latest_invoice_status"
    )
    assert invoice_amount.native_value == 500000.0
    assert invoice_status.native_value == "Đã thanh toán"
    assert invoice_amount.extra_state_attributes["paid_date"] == "15/09/2026"
    assert invoice_amount.extra_state_attributes["org_code"] == "BANK-A"
    average = next(
        entity
        for entity in entities
        if entity.entity_description.key == "average_12m_energy"
        and entity.extra_state_attributes.get("measurement_point") == "POINT-A"
    )
    assert invoice_amount.extra_state_attributes["payment_channel_label"] == (
        "Synthetic channel"
    )
    snapshot.monthly["POINT-A"] = [{"NAM": 2026, "THANG": 10, "DIEN_TTHU": "5"}]
    change = next(
        entity
        for entity in entities
        if entity.entity_description.key == "month_over_month"
        and entity.extra_state_attributes.get("measurement_point") == "POINT-A"
    )
    previous = next(
        entity
        for entity in entities
        if entity.entity_description.key == "prev_month_energy"
        and entity.extra_state_attributes.get("measurement_point") == "POINT-A"
    )
    assert change.native_value is None
    assert change.available
    assert change.extra_state_attributes["current"] == 5.0
    assert "previous" not in change.extra_state_attributes
    assert "delta" not in change.extra_state_attributes
    assert previous.native_value is None
    assert previous.available
    assert "period" not in previous.extra_state_attributes
    assert average.native_value == 5.0


@pytest.mark.asyncio
async def test_measurement_removal_and_absent_snapshot_unavailable(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    entities = collect_sensor(coordinator, entry)
    snapshot = coordinator.data[customer_key(customers[0])]
    snapshot.measurement_points = [{"MA_DDO": "POINT-B"}]
    affected = [
        entity
        for entity in entities
        if entity._customer_key == customer_key(customers[0])
        and entity._point == "POINT-A"
    ]
    assert len(affected) == len(POINT_SENSORS)
    assert all(
        not entity.available and entity.native_value is None for entity in affected
    )
    coordinator.data.pop(customer_key(customers[0]))
    assert all(
        not entity.available
        for entity in entities
        if entity._customer_key == customer_key(customers[0])
    )
    assert all(
        entity.available
        for entity in entities
        if entity._customer_key == customer_key(customers[1])
    )
    coordinator.data = {}
    assert all(
        not entity.available and entity.extra_state_attributes == {}
        for entity in entities
    )


@pytest.mark.asyncio
async def test_no_points_still_creates_customer_sensors_and_outage_text_bounded(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    snapshot = entry.runtime_data.data[customer_key(customers[0])]
    snapshot.measurement_points = []
    snapshot.outages[0]["KHUVUCMATDIEN"] = "a" * 2000
    snapshot.outages[0]["LY_DO"] = "r" * 2000
    add = Mock()
    await sensor.async_setup_entry(hass, entry, add)
    entities = add.call_args.args[0]
    assert len(entities) == len(CUSTOMER_SENSORS)
    outage = next(
        entity for entity in entities if entity.entity_description.key == "next_outage"
    )
    assert outage.extra_state_attributes["area"] == "a" * 512
    assert outage.extra_state_attributes["reason"] == "r" * 512
    snapshot.outages[0].pop("TGIAN_KTHUC")
    assert outage.native_value is not None
    assert "schedule_end" not in outage.extra_state_attributes


@pytest.mark.asyncio
async def test_unique_ids_separate_scopes_and_are_reload_stable(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    original = EvnSensor(
        coordinator, entry, customers[0], POINT_SENSORS[0], point="POINT-A"
    )
    same = EvnSensor(
        coordinator, entry, customers[0], POINT_SENSORS[0], point="POINT-A"
    )
    assert original.unique_id == same.unique_id
    other_account = make_entry(
        hass, customers, tokens, username="other-offline-account"
    )
    restored = make_entry(hass, customers, tokens)
    assert restored.entry_id != entry.entry_id
    reloaded = EvnSensor(
        coordinator, restored, customers[0], POINT_SENSORS[0], point="POINT-A"
    )
    assert reloaded.unique_id == original.unique_id
    assert reloaded.device_info == original.device_info
    variants = [
        original,
        EvnSensor(coordinator, entry, customers[1], POINT_SENSORS[0], point="POINT-A"),
        EvnSensor(
            coordinator,
            entry,
            Customer("OTHER-CUSTOMER", customers[0].management_unit),
            POINT_SENSORS[0],
            point="POINT-A",
        ),
        EvnSensor(coordinator, entry, customers[0], POINT_SENSORS[0], point="POINT-B"),
        EvnSensor(coordinator, entry, customers[0], POINT_SENSORS[1], point="POINT-A"),
        EvnSensor(
            coordinator, other_account, customers[0], POINT_SENSORS[0], point="POINT-A"
        ),
    ]
    assert len({entity.unique_id for entity in variants}) == len(variants)
    assert original.device_info != variants[-1].device_info


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [EvnAuthError, EvnUserActionRequired])
async def test_runtime_auth_failure_requests_reauth(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[EvnAuthError],
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    start_reauth = Mock()
    monkeypatch.setattr(entry, "async_start_reauth", start_reauth)
    entities = collect_sensor(entry.runtime_data, entry)
    client.fetch_snapshot.side_effect = failure()
    await entry.runtime_data.async_refresh()
    assert not entry.runtime_data.last_update_success
    assert isinstance(entry.runtime_data.last_exception, ConfigEntryAuthFailed)
    start_reauth.assert_called_once_with(hass)
    assert all(not entity.available for entity in entities)
    assert all(entity.native_value is None for entity in entities)


@pytest.mark.asyncio
async def test_native_ha_state_serialization_translation_and_unavailability(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    entities = collect_sensor(coordinator, entry)
    platform_data = PlatformData(hass, domain="sensor", platform_name=DOMAIN)
    english = json.loads(
        (ROOT / "custom_components" / DOMAIN / "strings.json").read_text()
    )
    translations = {
        f"component.{DOMAIN}.entity.sensor.{key}.name": value["name"]
        for key, value in english["entity"]["sensor"].items()
    }
    platform_data.platform_translations = translations
    platform_data.default_language_platform_translations = translations
    for entity in entities:
        entity.hass = hass
        entity.platform_data = platform_data
        calculated = entity._async_calculate_state()
        key = entity.entity_description.key
        attributes = calculated.attributes
        assert attributes["friendly_name"]
        assert "{" not in attributes["friendly_name"]
        if key in (
            "average_12m_energy",
            "month_over_month",
            "current_provisional_index",
        ):
            assert attributes["state_class"] == "measurement"
        else:
            assert "state_class" not in attributes
        assert "PRIVATE" not in str(attributes)
        assert IDENTITY[CONF_PASSWORD] not in str(attributes)
        assert tokens.access_token not in str(attributes)
        if key in ("monthly_energy", "prev_month_energy", "daily_energy"):
            assert attributes["unit_of_measurement"] == "kWh"
            assert attributes["device_class"] == "energy"
            assert attributes["measurement_point"] in attributes["friendly_name"]
        elif key == "average_12m_energy":
            assert attributes["unit_of_measurement"] == "kWh"
            assert "device_class" not in attributes
            assert attributes["measurement_point"] in attributes["friendly_name"]
        elif key == "month_over_month":
            assert attributes["unit_of_measurement"] == "%"
            assert "device_class" not in attributes
            assert attributes["measurement_point"] in attributes["friendly_name"]
        elif key in ("meter_reading", "meter_multiplier", "meter_read_date"):
            assert "unit_of_measurement" not in attributes
            assert "device_class" not in attributes
            assert attributes["measurement_point"] in attributes["friendly_name"]
        elif key in ("next_outage", "fetched_at"):
            if key == "next_outage":
                assert calculated.state == "2099-10-08T01:00:00+00:00"
            else:
                assert calculated.state == FETCHED_AT.isoformat(timespec="seconds")
        elif key == "meter_read_date":
            assert calculated.state in {"06/10/2026", "31/10/2026"}
        elif key == "latest_invoice_status":
            assert calculated.state == "Chưa thanh toán"
        elif key == "latest_invoice_amount":
            assert calculated.state == "9999999.0"
            assert attributes["unit_of_measurement"] == "VND"
            assert attributes["device_class"] == "monetary"
    coordinator.data[customer_key(customers[0])].outages = []
    outage = next(
        entity for entity in entities if entity.entity_description.key == "next_outage"
    )
    assert outage._async_calculate_state().state == "unknown"
    assert outage.available
    coordinator.last_update_success = False
    for entity in entities:
        calculated = entity._async_calculate_state()
        assert calculated.state == "unavailable"
        assert "last_update" not in calculated.attributes
        assert "period" not in calculated.attributes


@pytest.mark.asyncio
async def test_button_platform_one_per_customer_and_shared_device(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    add = Mock()
    await button.async_setup_entry(hass, entry, add)
    add.assert_called_once()
    entities: list[EvnButton] = add.call_args.args[0]
    assert len(entities) == 2
    assert len({entity.unique_id for entity in entities}) == 2
    coordinator = entry.runtime_data
    sensor_entities = collect_sensor(coordinator, entry)
    sensor_devices = {
        tuple(entity.device_info["identifiers"])
        for entity in sensor_entities
        if entity.device_info
    }
    button_devices = {
        tuple(entity.device_info["identifiers"])
        for entity in entities
        if entity.device_info
    }
    assert len(sensor_devices) == 2
    assert button_devices == sensor_devices
    for entity, customer in zip(entities, customers, strict=True):
        assert entity.translation_key == "refresh"
        assert entity.has_entity_name
        assert entity.entity_category is None
        assert entity.available
        assert entity.unique_id is not None
        assert re.fullmatch(r"[0-9a-f]{64}", entity.unique_id)
        assert entity.device_info is not None
        assert entity.device_info["manufacturer"] == "EVN"
        assert entity.device_info["model"] == "Customer account"
        assert customer_key(customer) in coordinator.data
        public = str(entity.device_info) + str(entity.unique_id)
        for private in (
            "PRIVATE NAME",
            "PRIVATE CONTRACT",
            IDENTITY[CONF_USERNAME],
            IDENTITY[CONF_PASSWORD],
        ):
            assert private not in public
    assert not {entity.unique_id for entity in entities} & {
        entity.unique_id for entity in sensor_entities
    }
    refresh = AsyncMock()
    monkeypatch.setattr(coordinator, "async_request_refresh", refresh)
    for entity in entities:
        await entity.async_press()
    assert refresh.await_count == 2


@pytest.mark.asyncio
async def test_button_press_refreshes_and_maps_auth_failure_to_reauth(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    entities = collect_button(coordinator, entry)
    start_reauth = Mock()
    monkeypatch.setattr(entry, "async_start_reauth", start_reauth)
    client.fetch_snapshot.side_effect = EvnAuthError()
    await entities[0].async_press()
    assert not coordinator.last_update_success
    assert isinstance(coordinator.last_exception, ConfigEntryAuthFailed)
    start_reauth.assert_called_once_with(hass)
    assert all(not entity.available for entity in entities)


@pytest.mark.asyncio
async def test_button_unique_ids_stable_scopes_and_reload_safe(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    original = EvnButton(coordinator, entry, customers[0])
    assert original.unique_id == EvnButton(coordinator, entry, customers[0]).unique_id
    assert (
        original.device_info == EvnButton(coordinator, entry, customers[0]).device_info
    )
    other_account = make_entry(
        hass, customers, tokens, username="other-offline-account"
    )
    restored = make_entry(hass, customers, tokens)
    variants = [
        original,
        EvnButton(coordinator, entry, customers[1]),
        EvnButton(
            coordinator,
            entry,
            Customer("OTHER-CUSTOMER", customers[0].management_unit),
        ),
        EvnButton(coordinator, other_account, customers[0]),
        EvnButton(coordinator, restored, customers[0]),
    ]
    assert variants[-1].unique_id == original.unique_id
    assert variants[-1].device_info == original.device_info
    assert len({entity.unique_id for entity in variants[:4]}) == 4
    assert original.device_info != variants[3].device_info


@pytest.mark.asyncio
async def test_binary_platform_states_identity_and_unavailability(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers, tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    add = Mock()
    await binary_sensor.async_setup_entry(hass, entry, add)
    entities = add.call_args.args[0]
    sensors = collect_sensor(coordinator, entry)
    buttons = collect_button(coordinator, entry)
    assert len(sensors) == 94
    assert len(buttons) == 2
    assert len(entities) == 6
    assert len({entity.unique_id for entity in [*sensors, *buttons, *entities]}) == 102
    for index, customer in enumerate(customers):
        scheduled, soon, active = entities[index * 3 : index * 3 + 3]
        for entity in (scheduled, soon, active):
            assert isinstance(entity, BinarySensorEntity)
            assert entity.available
            assert entity.device_class is None
            assert (
                entity.device_info
                == EvnButton(coordinator, entry, customer).device_info
            )
            assert entity.icon == entity.entity_description.icon
            assert entity.icon is not None and entity.icon.startswith("mdi:")
        assert scheduled.translation_key == "outage_scheduled"
        assert scheduled.is_on is True
        assert scheduled.entity_category is EntityCategory.DIAGNOSTIC
        assert scheduled.extra_state_attributes == {
            "last_update": FETCHED_AT.isoformat(),
            "schedule_start": "2099-10-08T08:00:00+07:00",
            "schedule_end": "2099-10-08T10:00:00+07:00",
            "area": "Synthetic public area",
            "reason": "Scheduled maintenance",
            "count": 1,
        }
        assert soon.translation_key == "outage_soon"
        assert soon.is_on is False
        assert soon.entity_category is None
        assert soon.extra_state_attributes == {"last_update": FETCHED_AT.isoformat()}
        assert active.translation_key == "outage_active"
        assert active.is_on is False
        assert active.entity_category is None
        assert active.extra_state_attributes == {"last_update": FETCHED_AT.isoformat()}
    coordinator.data[customer_key(customers[0])].outages = []
    assert entities[0].is_on is False and entities[3].is_on is True
    assert entities[0].extra_state_attributes == {
        "last_update": FETCHED_AT.isoformat(),
        "count": 0,
    }
    coordinator.data[customer_key(customers[1])].outages[0].pop("TGIAN_KTHUC")
    assert "schedule_end" not in entities[3].extra_state_attributes
    coordinator.last_update_success = False
    assert all(not entity.available and entity.is_on is None for entity in entities)
    assert all(entity.extra_state_attributes == {} for entity in entities)
    coordinator.last_update_success = True
    coordinator.data.pop(customer_key(customers[0]))
    assert not entities[0].available and entities[3].available
    restored = make_entry(hass, customers, tokens)
    other_account = make_entry(hass, customers, tokens, username="another-offline-user")
    description = binary_sensor.BINARY_SENSORS[0]
    assert (
        binary_sensor.EvnBinarySensor(
            coordinator, restored, customers[1], description
        ).unique_id
        == entities[3].unique_id
    )
    assert (
        binary_sensor.EvnBinarySensor(
            coordinator, other_account, customers[1], description
        ).unique_id
        != entities[3].unique_id
    )


@pytest.mark.asyncio
async def test_rich_scheduled_outage_entities_for_automation(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))

    def stamp(moment: datetime) -> str:
        return moment.strftime("%d/%m/%Y %H:%M")

    snapshot = coordinator.data[customer_key(customers[0])]
    snapshot.outages = [
        {
            "TGIAN_BDAU": stamp(now - timedelta(minutes=30)),
            "TGIAN_KTHUC": stamp(now + timedelta(minutes=30)),
            "KHUVUCMATDIEN": "Active area",
            "LY_DO": "Active reason",
        },
        {
            "TGIAN_BDAU": stamp(now + timedelta(hours=2)),
            "TGIAN_KTHUC": stamp(now + timedelta(hours=3)),
            "KHUVUCMATDIEN": "Soon area",
            "LY_DO": "Soon reason",
        },
        {
            "TGIAN_BDAU": stamp(now + timedelta(days=30)),
            "TGIAN_KTHUC": stamp(now + timedelta(days=30, hours=2)),
            "KHUVUCMATDIEN": "Far area",
            "LY_DO": "Far reason",
        },
        {
            "TGIAN_BDAU": stamp(now - timedelta(days=2)),
            "TGIAN_KTHUC": stamp(now - timedelta(days=2) + timedelta(hours=1)),
            "KHUVUCMATDIEN": "Past area",
            "LY_DO": "Past reason",
        },
    ]
    add = Mock()
    await binary_sensor.async_setup_entry(hass, entry, add)
    alerts = {entity.entity_description.key: entity for entity in add.call_args.args[0]}
    assert alerts["outage_active"].is_on is True
    active = alerts["outage_active"].extra_state_attributes
    assert active["area"] == "Active area"
    assert active["reason"] == "Active reason"
    assert alerts["outage_soon"].is_on is True
    soon = alerts["outage_soon"].extra_state_attributes
    assert datetime.fromisoformat(soon["start"]).tzinfo is not None
    assert datetime.fromisoformat(soon["end"]).tzinfo is not None
    assert soon["seconds_until"] >= 0
    assert soon["seconds_until"] <= 3 * 3600
    assert alerts["outage_scheduled"].is_on is True
    assert alerts["outage_scheduled"].extra_state_attributes["count"] == 4
    assert alerts["outage_active"].entity_category is None
    assert alerts["outage_soon"].entity_category is None
    assert alerts["outage_scheduled"].entity_category is EntityCategory.DIAGNOSTIC

    sensor_add = Mock()
    await sensor.async_setup_entry(hass, entry, sensor_add)
    sensors = {
        entity.entity_description.key: entity
        for entity in sensor_add.call_args.args[0]
        if entity._point is None
    }
    assert sensors["outage_count"].native_value == 4
    assert sensors["outage_count"].entity_category is EntityCategory.DIAGNOSTIC
    assert sensors["next_outage_area"].native_value == "Soon area"
    assert sensors["next_outage_reason"].native_value == "Soon reason"
    assert sensors["next_outage_duration"].native_value == pytest.approx(1.0)
    end_value = sensors["next_outage_end"].native_value
    assert isinstance(end_value, datetime) and end_value.tzinfo is not None
    assert sensors["next_outage_area"].entity_category is None

    snapshot.outages = []
    assert sensors["next_outage_duration"].native_value is None
    assert sensors["next_outage_area"].native_value is None
    assert sensors["next_outage_reason"].native_value is None
    assert sensors["next_outage_end"].native_value is None
    assert sensors["outage_count"].native_value == 0
    assert alerts["outage_active"].is_on is False
    assert alerts["outage_soon"].is_on is False
    assert alerts["outage_scheduled"].is_on is False


@pytest.mark.asyncio
async def test_calendar_sensors_cross_year_and_preserve_existing_ids(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    snapshot = entry.runtime_data.data[customer_key(customers[0])]
    snapshot.measurement_points = [{"MA_DDO": "POINT-A"}]
    snapshot.monthly = {
        "POINT-A": [
            {"NAM": 2026, "THANG": 1, "DIEN_TTHU": 10},
            {"NAM": 2025, "THANG": 12, "DIEN_TTHU": 20},
        ]
    }
    snapshot.monthly_readings = {
        "POINT-A": [
            {"NAM": 2025, "THANG": 11, "DIEN_TTHU": 30, "CHISO_MOI": 100},
            {"NAM": 2025, "THANG": 12, "DIEN_TTHU": 20, "CHISO_MOI": 120},
        ]
    }
    snapshot.daily = {
        "POINT-A": [
            {
                "NGAY": day,
                "NGAY_HTHI": day,
                "BCS": "KT",
                "SO_CTO": "METER-A",
                "DIEN_TTHU": amount,
            }
            for day, amount in (
                ("30/12/2025", 1),
                ("31/12/2025", 2),
                ("01/01/2026", 3),
            )
        ]
    }
    snapshot.daily_readings = {
        "POINT-A": [
            {"NGAY": day, "BCS": "KT", "CHISO_MOI": index}
            for day, index in (
                ("30/12/2025", 117),
                ("31/12/2025", 119),
                ("01/01/2026", 122),
            )
        ]
    }
    snapshot.monthly_readings["POINT-A"][0]["BCS"] = "KT"
    snapshot.invoices = [
        {
            "ID_HDON": "CURRENT",
            "NAM": 2026,
            "THANG": 1,
            "TTRANG_TTOAN": "CHUATT",
            "TONG_TIEN": 1000,
        }
    ]
    snapshot.paid_invoices = [
        {
            "ID_HDON": "PREVIOUS",
            "NAM": 2025,
            "THANG": 12,
            "TONG_TIEN": 2000,
            "NGAY_TTOAN": "31/12/2025",
        },
        {
            "ID_HDON": "OLDER",
            "NAM": 2025,
            "THANG": 11,
            "TONG_TIEN": 3000,
            "NGAY_TTOAN": "30/11/2025",
        },
    ]
    monkeypatch.setattr(sensor, "vn_now", lambda: date(2026, 1, 1))
    entities = {
        entity.entity_description.key: entity
        for entity in collect_sensor(entry.runtime_data, entry)
    }
    expected = {
        "consumption_today": 3.0,
        "consumption_yesterday": 2.0,
        "consumption_two_days_ago": 1.0,
        "current_provisional_index": 122.0,
        "previous_cycle_final_index": 120.0,
        "current_period_detail": "01-2026",
        "invoice_year": 2026,
        "invoice_this_period": 1000.0,
        "invoice_prev_period": 2000.0,
        "invoice_prev_prev_period": 3000.0,
        "consumption_this_period": 10.0,
        "consumption_prev_period": 20.0,
        "consumption_prev_prev_period": 30.0,
    }
    for key, value in expected.items():
        assert entities[key].native_value == value
    old = entities["prev_month_energy"]
    alias = entities["consumption_prev_period"]
    assert old.native_value == alias.native_value
    assert old.unique_id != alias.unique_id and old.device_info == alias.device_info
    assert (
        entities["current_provisional_index"].state_class
        is SensorStateClass.MEASUREMENT
    )
    assert entities["current_provisional_index"].native_unit_of_measurement is None
    snapshot.daily_readings["POINT-A"] = []
    snapshot.daily["POINT-A"] = []
    snapshot.monthly_readings["POINT-A"] = []
    assert entities["current_provisional_index"].native_value is None
    assert entities["previous_cycle_final_index"].native_value is None
    assert entities["consumption_today"].native_value is None
    assert entities["consumption_prev_prev_period"].native_value is None


@pytest.mark.asyncio
async def test_next_update_uses_coordinator_schedule_not_snapshot_time(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    entity = next(
        item
        for item in collect_sensor(coordinator, entry)
        if item.entity_description.key == "next_update"
    )
    assert entity.native_value is None
    coordinator._schedule_refresh()
    scheduled = entity.native_value
    assert isinstance(scheduled, datetime) and scheduled.tzinfo is UTC
    assert abs((scheduled - datetime.now(UTC)).total_seconds() - 360 * 60) < 2
    assert entity.entity_category is EntityCategory.DIAGNOSTIC
    assert entity.device_class is SensorDeviceClass.TIMESTAMP
    coordinator._async_unsub_refresh()
    assert entity.native_value is None
    coordinator.update_interval = timedelta(minutes=60)
    coordinator._schedule_refresh()
    assert abs((entity.native_value - datetime.now(UTC)).total_seconds() - 60 * 60) < 2
    coordinator.last_update_success = False
    assert entity.available and isinstance(entity.native_value, datetime)
    assert entity.extra_state_attributes == {
        "source": "coordinator_timer",
        "provisional": False,
    }
    assert not any(
        item.available
        for item in collect_sensor(coordinator, entry)
        if item.entity_description.key != "next_update"
    )
    await coordinator.async_shutdown()
    assert not entity.available and entity.native_value is None


@pytest.mark.asyncio
async def test_requested_daily_sensors_read_energy_not_index_snapshot(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    snapshot = entry.runtime_data.data[customer_key(customers[0])]
    snapshot.measurement_points = [{"MA_DDO": "POINT-A"}]
    snapshot.daily_readings["POINT-A"] = [
        {
            "NGAY": day,
            "THOI_DIEM": day + " 08:00",
            "BCS": "KT",
            "SO_CTO": "METER-A",
            "CHISO_MOI": value,
            "HSN": 2,
        }
        for day, value in (
            ("05/10/2026", 1000),
            ("06/10/2026", 1012.5),
            ("07/10/2026", 1018),
        )
    ]
    snapshot.daily["POINT-A"] = [
        {
            "NGAY": day,
            "NGAY_HTHI": day,
            "SO_CTO": "METER-A",
            "BCS": "KT",
            "DIEN_TTHU": value,
        }
        for day, value in (
            ("05/10/2026", -1.5),
            ("06/10/2026", 4.25),
            ("07/10/2026", 0),
        )
    ]
    entities = {
        item.entity_description.key: item
        for item in collect_sensor(entry.runtime_data, entry)
    }
    for key, value, target in (
        ("consumption_today", 0.0, "2026-10-07"),
        ("consumption_yesterday", 4.25, "2026-10-06"),
        ("consumption_two_days_ago", -1.5, "2026-10-05"),
    ):
        entity = entities[key]
        assert entity.native_value == value
        attributes = entity.extra_state_attributes
        assert attributes["target_date"] == target
        assert attributes["source"] == "diennangngay"
        assert attributes["provisional"] is True
        assert attributes["period_basis"] == "calendar_day"
    assert entities["current_provisional_index"].native_value == 1018.0
    snapshot.daily["POINT-A"].pop()
    assert entities["consumption_today"].native_value is None
    snapshot.daily["POINT-A"] = [
        dict(row) for row in snapshot.daily_readings["POINT-A"]
    ]
    assert all(entities[key].native_value is None for key in sensor._DAY_OFFSETS)
    snapshot.daily["POINT-A"] = [
        {"NGAY_HTHI": "05/10/2026 - 07/10/2026", "BCS": "KT", "DIEN_TTHU": 100}
    ]
    assert all(entities[key].native_value is None for key in sensor._DAY_OFFSETS)


@pytest.mark.asyncio
async def test_previous_final_index_sensor_uses_as_of_and_verified_counter(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    snapshot = entry.runtime_data.data[customer_key(customers[0])]
    snapshot.measurement_points = [{"MA_DDO": "POINT-A"}]
    snapshot.monthly_readings["POINT-A"] = [
        {
            "NAM": 2026,
            "THANG": 9,
            "KY": 1,
            "BCS": "KT",
            "SO_CTO": "OLD",
            "NGAY_CKY": "15/09/2026",
            "CHISO_MOI": 9000,
        },
        {
            "NAM": 2026,
            "THANG": 9,
            "KY": 2,
            "BCS": "KT",
            "SO_CTO": "NEW",
            "NGAY_CKY": "30/09/2026",
            "CHISO_MOI": 100,
        },
        {
            "NAM": 2026,
            "THANG": 10,
            "BCS": "KT",
            "SO_CTO": "NEW",
            "NGAY_CKY": "06/10/2026",
            "CHISO_MOI": 110,
        },
    ]
    entities = {
        item.entity_description.key: item
        for item in collect_sensor(entry.runtime_data, entry)
    }
    entity = entities["previous_cycle_final_index"]
    assert entity.native_value == 100.0
    assert entity.device_class is None and entity.native_unit_of_measurement is None
    attributes = entity.extra_state_attributes
    assert attributes["target_month"] == "2026-09"
    assert attributes["as_of"] == "2026-10-07"
    assert attributes["period_basis"] == "previous_completed_month_label"
    assert attributes["cycle_basis"] == "latest_verified_end_date_or_month_cycle_order"
    assert attributes["source"] == "chisothang" and attributes["provisional"] is False
    snapshot.monthly_readings["POINT-A"].append(
        snapshot.monthly_readings["POINT-A"][1] | {"BCS": "BT"}
    )
    assert entity.native_value is None
    snapshot.monthly_readings["POINT-A"].pop()
    monkeypatch.setattr(sensor, "vn_now", lambda: date(2026, 11, 1))
    assert entity.native_value == 110.0


@pytest.mark.asyncio
async def test_customer_month_sensors_share_typed_helper_and_explicit_sources(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    snapshot = entry.runtime_data.data[customer_key(customers[0])]
    snapshot.measurement_points = [
        {"MA_DDO": "POINT-A"},
        {"MA_DDO": "POINT-A"},
        {"MA_DDO": "POINT-B"},
    ]
    snapshot.monthly = {"POINT-A": [{"NAM": 2026, "THANG": 10, "DIEN_TTHU": 0}]}
    snapshot.monthly_readings = {
        "POINT-A": [{"NAM": 2026, "THANG": 10, "BCS": "KT", "DIEN_TTHU": 999}],
        "POINT-B": [
            {"NAM": 2026, "THANG": 10, "BCS": band, "DIEN_TTHU": value}
            for band, value in (("KT", 5), ("BT", 1), ("CD", 1), ("TD", 1))
        ],
    }
    entities = {
        item.entity_description.key: item
        for item in collect_sensor(entry.runtime_data, entry)
    }
    current = entities["consumption_this_period"]
    assert current.native_value == 5.0
    assert current.extra_state_attributes["target_month"] == "2026-10"
    assert current.extra_state_attributes["source"] == "chisothang+diennangthang"
    assert current.extra_state_attributes["period_basis"] == "energy_month_label"
    assert current.extra_state_attributes["provisional"] is True
    assert entities["consumption_prev_period"].native_value is None
    snapshot.monthly["POINT-A"][0]["DIEN_TTHU"] = None
    assert current.native_value is None
    shared = Mock(return_value=123.25)
    monkeypatch.setattr(sensor, "customer_month_energy", shared)
    assert sensor._customer_month_energy(snapshot, (2026, 10)) == 123.25
    shared.assert_called_once_with(
        snapshot.measurement_points,
        snapshot.monthly,
        snapshot.monthly_readings,
        2026,
        10,
    )


@pytest.mark.asyncio
async def test_invoice_period_sensor_keeps_distinct_history_and_unknown_vs_zero(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    snapshot = entry.runtime_data.data[customer_key(customers[0])]
    active = {
        "ID_HDON": "CURRENT",
        "ID_HDON_DC": None,
        "NAM": 2026,
        "THANG": 10,
        "KY": 2,
        "TONG_TIEN": 100,
        "TTRANG_TTOAN": "CHUATT",
    }
    snapshot.invoices = [active]
    snapshot.paid_invoices = [
        active | {"TTRANG_TTOAN": "DATT", "TONG_TIEN": 999},
        {
            "ID_HDON": "PAID",
            "NAM": 2026,
            "THANG": 10,
            "KY": 1,
            "TONG_TIEN": 50,
            "NGAY_TTOAN": "01/11/2026",
        },
    ]
    entity = next(
        item
        for item in collect_sensor(entry.runtime_data, entry)
        if item.entity_description.key == "invoice_this_period"
    )
    assert entity.native_value == 150.0
    assert entity.extra_state_attributes["target_month"] == "2026-10"
    assert entity.extra_state_attributes["period_basis"] == "invoice_month_label"
    assert entity.extra_state_attributes["source"] == "hoadon+lichsu-hoadon"
    snapshot.invoices = []
    snapshot.paid_invoices = []
    assert entity.native_value is None
    snapshot.invoices = [active | {"TONG_TIEN": 0}]
    assert entity.native_value == 0.0
    snapshot.invoices[0]["TONG_TIEN"] = None
    assert entity.native_value is None


@pytest.mark.asyncio
async def test_actual_retry_timer_survives_cloud_failure_without_stale_data(
    hass: HomeAssistant,
    mocked_client: tuple[Mock, Mock],
    customers: list[Customer],
    tokens: TokenState,
) -> None:
    client, _ = mocked_client
    entry = make_entry(hass, customers[:1], tokens)
    assert await integration.async_setup_entry(hass, entry)
    coordinator = entry.runtime_data
    entities = collect_sensor(coordinator, entry)
    next_update = next(
        item for item in entities if item.entity_description.key == "next_update"
    )
    unsubscribe = coordinator.async_add_listener(Mock())
    try:
        client.fetch_snapshot.side_effect = EvnConnectionError()
        await coordinator.async_refresh()
        assert not coordinator.last_update_success
        assert next_update.available
        stamp = next_update.native_value
        assert isinstance(stamp, datetime) and stamp.tzinfo is UTC
        assert coordinator.next_iteration is not None
        assert abs((stamp - coordinator.next_iteration).total_seconds()) < 0.1
        for item in entities:
            if item is next_update:
                continue
            assert not item.available
            assert item.native_value is None and item.extra_state_attributes == {}
        coordinator._async_unsub_refresh()
        assert not next_update.available and next_update.native_value is None
    finally:
        unsubscribe()
        await coordinator.async_shutdown()
