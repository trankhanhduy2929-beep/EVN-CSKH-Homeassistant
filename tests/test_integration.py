from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
from custom_components.evn_cskh import config_flow, sensor
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


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    async def blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound requests are disabled in integration tests")

    monkeypatch.setattr(ClientSession, "_request", blocked)
    monkeypatch.setattr(asyncio, "open_connection", blocked)


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
                "ID_HDON": "PRIVATE INVOICE A",
                "TTRANG_TTOAN": "CHUATT",
                "TONG_NO": "-125000",
                "TONG_TIEN": 9999999,
                "TEN_KHANG": customer.name,
                "DIA_CHI": "PRIVATE ADDRESS",
                "password": IDENTITY[CONF_PASSWORD],
                "access_token": "offline-access",
            },
            {"ID_HDON": "PRIVATE INVOICE B", "TTRANG_TTOAN": "DATT"},
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


def test_real_homeassistant_types_and_identity() -> None:
    assert issubclass(EvnConfigFlow, ConfigFlow)
    assert issubclass(EvnOptionsFlow, OptionsFlowWithReload)
    assert issubclass(EvnCoordinator, DataUpdateCoordinator)
    assert issubclass(EvnSensor, SensorEntity)
    ha_path = __import__("homeassistant.core", fromlist=["core"]).__file__
    assert ha_path is not None
    assert "site-packages/homeassistant" in str(Path(ha_path))
    assert account_unique_id(" Offline-User ") == account_unique_id("offline-user")
    assert (
        account_unique_id("offline-user") == hashlib.sha256(b"offline-user").hexdigest()
    )
    assert DOMAIN == "evn_cskh"
    assert NAME == "EVN CSKH"
    assert VERSION == "0.2.0"
    assert MIN_HA_VERSION == "2025.12"
    assert PLATFORMS == (Platform.SENSOR,)


def test_manifest_and_complete_translations() -> None:
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
    for description in (*POINT_SENSORS, *CUSTOMER_SENSORS):
        assert description.translation_key == description.key
        assert description.key in english["entity"]["sensor"]
    for description in POINT_SENSORS:
        assert (
            "{measurement_point}"
            in english["entity"]["sensor"][description.key]["name"]
        )
        assert (
            "{measurement_point}"
            in vietnamese["entity"]["sensor"][description.key]["name"]
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
    assert all(entity.native_value is not None for entity in entities)


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
    assert len(entities) == 16
    assert len({entity.unique_id for entity in entities}) == 16
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
    expected = {
        ("monthly_energy", "POINT-A"): 12.5,
        ("monthly_energy", "POINT-B"): 27.5,
        ("daily_energy", "POINT-A"): 1.25,
        ("daily_energy", "POINT-B"): 2.25,
        ("outstanding_amount", None): 125000.0,
        ("outstanding_count", None): 1,
        ("next_outage", None): datetime(2099, 10, 8, 8, tzinfo=LOCAL),
        ("fetched_at", None): FETCHED_AT,
    }
    for entity in entities:
        assert isinstance(entity, SensorEntity)
        assert entity.has_entity_name
        assert not entity.should_poll
        assert entity.available
        attributes = entity.extra_state_attributes
        assert (
            entity.native_value
            == expected[
                (entity.entity_description.key, attributes.get("measurement_point"))
            ]
        )
        assert set(attributes) <= {
            "period",
            "measurement_point",
            "last_update",
            "schedule_end",
            "area",
            "reason",
        }
        public = str(attributes) + str(entity.device_info) + str(entity.unique_id)
        for private in (
            "PRIVATE NAME",
            "PRIVATE CONTRACT",
            "PRIVATE ADDRESS",
            "PRIVATE INVOICE",
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
        if entity.entity_description.key in ("monthly_energy", "daily_energy"):
            assert entity.device_class is SensorDeviceClass.ENERGY
            assert entity.native_unit_of_measurement == "kWh"
            assert entity.state_class is None
            assert attributes["period"] == (
                "2026-10"
                if entity.entity_description.key == "monthly_energy"
                else "05/10/2026 - 06/10/2026"
            )
            assert entity.translation_placeholders == {
                "measurement_point": attributes["measurement_point"]
            }
        elif entity.entity_description.key == "outstanding_amount":
            assert entity.device_class is SensorDeviceClass.MONETARY
            assert entity.native_unit_of_measurement == "VND"
        elif entity.entity_description.key in ("next_outage", "fetched_at"):
            assert entity.device_class is SensorDeviceClass.TIMESTAMP
            assert entity.native_unit_of_measurement is None
            assert isinstance(entity.native_value, datetime)
            assert entity.native_value.tzinfo is not None
        if entity.entity_description.key == "fetched_at":
            assert entity.entity_category is EntityCategory.DIAGNOSTIC
        if entity.entity_description.key == "next_outage":
            assert (
                attributes["schedule_end"]
                == datetime(2099, 10, 8, 10, tzinfo=LOCAL).isoformat()
            )
            assert attributes["area"] == "Synthetic public area"
            assert attributes["reason"] == "Scheduled maintenance"


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
    entities = collect_sensor(coordinator, entry)
    states = {
        (
            entity.entity_description.key,
            entity.extra_state_attributes.get("measurement_point"),
        ): entity.native_value
        for entity in entities
    }
    assert states[("monthly_energy", "POINT-A")] is None
    assert states[("daily_energy", "POINT-A")] is None
    assert states[("outstanding_amount", None)] == 0.0
    assert states[("outstanding_count", None)] == 0
    assert states[("next_outage", None)] is None
    assert all(entity.available for entity in entities)
    snapshot.monthly["POINT-A"] = [{"NAM": 2026, "THANG": 10, "DIEN_TTHU": "1,234"}]
    snapshot.daily["POINT-A"] = [
        {"NGAY": "06/10/2026", "BCS": "KT", "DIEN_TTHU": "NaN"}
    ]
    snapshot.invoices = [
        {"ID_HDON": "PRIVATE INVOICE", "TTRANG_TTOAN": "CHUATT", "TONG_TIEN": 999}
    ]
    for entity in entities:
        if entity.extra_state_attributes.get(
            "measurement_point"
        ) == "POINT-A" or entity.entity_description.key.startswith("outstanding"):
            assert entity.native_value is None
            assert entity.available
    snapshot.outages = [{"TGIAN_BDAU": "01/01/2000 08:00"}]
    outage_entity = next(
        entity for entity in entities if entity.entity_description.key == "next_outage"
    )
    assert outage_entity.native_value is None and outage_entity.available
    assert set(outage_entity.extra_state_attributes) == {"last_update"}


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
    assert len(affected) == 2
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
    assert len(entities) == 4
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
        assert "state_class" not in attributes
        assert "PRIVATE" not in str(attributes)
        assert IDENTITY[CONF_PASSWORD] not in str(attributes)
        assert tokens.access_token not in str(attributes)
        if key in ("monthly_energy", "daily_energy"):
            assert attributes["unit_of_measurement"] == "kWh"
            assert attributes["device_class"] == "energy"
            assert attributes["measurement_point"] in attributes["friendly_name"]
        elif key == "next_outage":
            assert calculated.state == "2099-10-08T01:00:00+00:00"
        elif key == "fetched_at":
            assert calculated.state == FETCHED_AT.isoformat(timespec="seconds")
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
