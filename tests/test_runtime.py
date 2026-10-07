from __future__ import annotations

import hashlib
import json
import re
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any, cast

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
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers.selector import NumberSelector, SelectSelector, TextSelector
from homeassistant.helpers.translation import async_get_translations
from homeassistant.setup import async_setup_component

from custom_components import evn_cskh as integration
from custom_components.evn_cskh import config_flow
from custom_components.evn_cskh.api import (
    Customer,
    EvnError,
    EvnResponseError,
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
    "DUMMY PRIVATE INVOICE",
)
NAMES = {
    "en": {
        "monthly_energy": f"Latest monthly energy {POINT}",
        "daily_energy": f"Latest interval energy {POINT}",
        "outstanding_amount": "Outstanding amount",
        "outstanding_count": "Outstanding invoice count",
        "next_outage": "Next scheduled outage",
        "fetched_at": "Last successful update",
    },
    "vi": {
        "monthly_energy": f"Điện năng tháng gần nhất {POINT}",
        "daily_energy": f"Điện năng khoảng gần nhất {POINT}",
        "outstanding_amount": "Tiền còn nợ",
        "outstanding_count": "Số hóa đơn chưa thanh toán",
        "next_outage": "Lịch ngừng cấp điện tiếp theo",
        "fetched_at": "Lần cập nhật thành công gần nhất",
    },
}
PUBLIC_ATTRIBUTES = {
    "friendly_name",
    "device_class",
    "unit_of_measurement",
    "last_update",
    "period",
    "measurement_point",
    "schedule_end",
    "area",
    "reason",
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
                "ID_HDON": "DUMMY PRIVATE INVOICE",
                "TTRANG_TTOAN": "CHUATT",
                "TONG_NO": "-125000",
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
    rows = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(rows) == 6
    assert all(row.domain == "sensor" and row.platform == DOMAIN for row in rows)
    assert {row.translation_key for row in rows} == set(NAMES["en"])
    return {cast(str, row.translation_key): row for row in rows}


def sensor_states(hass: HomeAssistant, entry: EvnConfigEntry) -> dict[str, State]:
    result = {}
    for key, row in registry_rows(hass, entry).items():
        state = hass.states.get(row.entity_id)
        assert isinstance(state, State)
        assert "state_class" not in state.attributes
        assert all(
            value not in str(state)
            for value in (*PROTECTED, entry.data[CONF_DEVICE_ID])
        )
        result[key] = state
    return result


def registry_identity(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> dict[str, tuple[str, str, str | None]]:
    return {
        key: (row.entity_id, row.unique_id, row.device_id)
        for key, row in registry_rows(hass, entry).items()
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
    assert {"homeassistant", DOMAIN, "sensor"} <= hass.config.components
    platforms = [
        platform
        for platform in async_get_platforms(hass, DOMAIN)
        if platform.config_entry is entry
    ]
    assert len(platforms) == 1 and platforms[0].domain == "sensor"
    assert len(platforms[0].entities) == 6
    assert tuple(entry.runtime_data.async_contexts()) == (customer_key(CUSTOMER),) * 6
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
    assert (
        states["next_outage"].attributes["schedule_end"] == "2099-10-08T10:00:00+07:00"
    )
    assert states["next_outage"].attributes["area"] == "Synthetic public area"
    assert states["next_outage"].attributes["reason"] == "Scheduled maintenance"
    assert states["fetched_at"].state == FETCHED_AT.isoformat(timespec="seconds")
    assert rows["fetched_at"].entity_category is EntityCategory.DIAGNOSTIC
    assert not [record for record in caplog.records if record.levelno >= 40]


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
        invoices=[{"ID_HDON": "DUMMY PRIVATE INVOICE", "TTRANG_TTOAN": "CHUATT"}],
        outages=[],
    )
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert entry.runtime_data.last_update_success
    assert all(
        states[key].state == STATE_UNKNOWN for key in NAMES["en"] if key != "fetched_at"
    )
    assert all("period" not in state.attributes for state in states.values())
    assert "schedule_end" not in states["next_outage"].attributes
    assert "area" not in states["next_outage"].attributes
    offline_evn.failure = EvnResponseError()
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert not entry.runtime_data.last_update_success
    for state in sensor_states(hass, entry).values():
        assert state.state == STATE_UNAVAILABLE
        assert set(state.attributes) <= {
            "friendly_name",
            "device_class",
            "unit_of_measurement",
        }
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
    offline_evn.snapshot = replace(make_snapshot(), measurement_points=[])
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    states = sensor_states(hass, entry)
    assert states["monthly_energy"].state == STATE_UNAVAILABLE
    assert states["daily_energy"].state == STATE_UNAVAILABLE
    assert states["outstanding_count"].state == "1"
    assert registry_identity(hass, entry) == identity
    assert len(offline_evn.clients) == 1 and offline_evn.clients[0].login_calls == 0


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
    assert entry.runtime_data.update_interval == timedelta(minutes=60)
    assert len(offline_evn.clients) == 2
    assert not entry.update_listeners
    assert registry_identity(hass, entry) == identity
    assert sensor_states(hass, entry)["monthly_energy"].state == "12.5"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(offline_evn.clients) == 3
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
