from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from importlib.metadata import version
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol
from aiohttp import ClientSession, web
from aiohttp.test_utils import make_mocked_request
from homeassistant.auth.models import User
from homeassistant.auth.permissions import PermissionLookup
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components.http.cors import setup_cors
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntries,
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers.http import KEY_AUTHENTICATED, request_handler_factory

from custom_components.evn_cskh import panel
from custom_components.evn_cskh.api import (
    Customer,
    DetailSnapshot,
    EvnAuthError,
    EvnClient,
    EvnConnectionError,
    EvnResponseError,
    Snapshot,
)
from custom_components.evn_cskh.const import (
    CONF_CUSTOMERS,
    CONF_SELECTED_CUSTOMERS,
    DOMAIN,
    VERSION,
)
from custom_components.evn_cskh.coordinator import (
    EvnConfigEntry,
    EvnCoordinator,
    customer_inventory,
    customer_key,
)

PERSON = Customer(
    "OFFLINE-CUSTOMER", "OFFLINE-UNIT", "Synthetic name", "PRIVATE-CONTRACT"
)
OTHER = Customer("OFFLINE-OTHER", "OFFLINE-UNIT", "Other synthetic name")
POINT = "OFFLINE-POINT"
NOW = datetime(2026, 10, 7, 5, tzinfo=UTC)
START = "2026-01-01"
END = "2026-10-06"
START_DATE = date.fromisoformat(START)
END_DATE = date.fromisoformat(END)
PDF = b"%PDF-1.7\nsynthetic offline document\n%%EOF\n"
PRIVATE = {
    "username": "PRIVATE-USERNAME",
    "password": "PRIVATE-PASSWORD",
    "access_token": "PRIVATE-ACCESS",
    "refresh_token": "PRIVATE-REFRESH",
    "ID_HDON": "PRIVATE-INVOICE-ID",
    "ID_HDON_DC": "PRIVATE-ADJUSTMENT-ID",
    "phone": "PRIVATE-PHONE",
    "DCHI_KHANG": "PRIVATE-INVOICE-ADDRESS",
}


def invoice_row(**updates: Any) -> dict[str, Any]:
    return PRIVATE | {
        "NAM": 2026,
        "THANG": 9,
        "KY": 1,
        "LOAI_HDON": "TD",
        "TTRANG_TTOAN": "CHUATT",
        "TONG_TIEN": "110",
        "TIEN_GTGT": "10",
        "TONG_NO": "110",
        "DIEN_TTHU": "12.5",
        "NGAY_TTOAN": None,
        "HAN_TTOAN": "20/10/2026",
        **updates,
    }


def make_snapshot(person: Customer = PERSON) -> Snapshot:
    return Snapshot(
        customer=person,
        region="PB",
        measurement_points=[
            PRIVATE | {"MA_DDO": POINT, "DIA_CHI": "A" * 600 + "\n\x00"}
        ],
        monthly={POINT: [{"NAM": 2026, "THANG": 9, "DIEN_TTHU": "12.5"}]},
        daily={POINT: [{"NGAY": "06/10/2026", "BCS": "KT", "DIEN_TTHU": "2.5"}]},
        invoices=[invoice_row()],
        outages=[
            PRIVATE
            | {
                "TGIAN_BDAU": "08/10/2099 08:00",
                "TGIAN_KTHUC": "08/10/2099 09:00",
                "KHUVUCMATDIEN": "Synthetic area",
                "LY_DO": "Maintenance",
            },
            {"TGIAN_BDAU": "unknown", "LY_DO": "Unknown schedule"},
        ],
        fetched_at=NOW,
    )


def make_details(
    person: Customer = PERSON,
    point: str = POINT,
    start: date = START_DATE,
    end: date = END_DATE,
) -> DetailSnapshot:
    return DetailSnapshot(
        customer=person,
        region="PB",
        point=point,
        start=start,
        end=end,
        monthly=[
            {"NAM": 2026, "THANG": 9, "SO_CTO": "A", "DIEN_TTHU": "10"},
            {"NAM": 2026, "THANG": 1, "SO_CTO": "A", "DIEN_TTHU": "4"},
            {"NAM": 2026, "THANG": 9, "SO_CTO": "B", "DIEN_TTHU": "2.5"},
        ],
        daily=[
            {"NGAY": "06/10/2026", "BCS": "KT", "DIEN_TTHU": "10"},
            {"NGAY": "05/10/2026", "BCS": "KT", "DIEN_TTHU": "2.5"},
            {"NGAY": "06/10/2026", "BCS": "BT", "DIEN_TTHU": "3"},
            {"NGAY": "06/10/2026", "BCS": "CD", "DIEN_TTHU": "4"},
            {"NGAY": "06/10/2026", "BCS": "TD", "DIEN_TTHU": "3"},
        ],
        monthly_readings=[
            PRIVATE
            | {
                "NAM": 2026,
                "THANG": 9,
                "SO_CTO": "SYNTHETIC-METER",
                "BCS": "KT",
                "CHISO_CU": "10",
                "CHISO_MOI": "22.5",
                "HSN": "1",
                "DIEN_TTHU": "12.5",
            }
        ],
        daily_readings=[
            PRIVATE
            | {
                "NGAY": "06/10/2026",
                "CHISO_CU": "NaN",
                "CHISO_MOI": float("inf"),
                "HSN": True,
                "DIEN_TTHU": "1,000",
            }
        ],
        invoices=[invoice_row()],
        fetched_at=NOW,
    )


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    async def blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound HTTP is disabled")

    monkeypatch.setattr(ClientSession, "_request", blocked)
    monkeypatch.setattr(panel, "_now", lambda: NOW.date())


@pytest.fixture
async def hass(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[HomeAssistant]:
    assert version("homeassistant") == "2025.12.5"
    hass = HomeAssistant("/tmp/opencode")
    hass.config_entries = ConfigEntries(hass, {})
    hass.http = HomeAssistantHTTP(
        hass, None, None, None, ["127.0.0.1"], 0, [], "modern"
    )
    setup_cors(hass.http.app, [])
    hass.config.components.add("frontend")

    async def ready_panel_component(*args: Any, **kwargs: Any) -> bool:
        return True

    monkeypatch.setattr(panel, "async_setup_component", ready_panel_component)
    original = Path.is_file
    monkeypatch.setattr(
        Path, "is_file", lambda path: path == panel._STATIC_FILE or original(path)
    )
    try:
        yield hass
    finally:
        for entry_id in list(panel._manager(hass).entries):
            await panel.async_detach_entry(hass, entry_id)
        await hass.async_stop(force=True)
        await hass.async_block_till_done()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    value = [1000.0]
    monkeypatch.setattr(panel, "monotonic", lambda: value[0])
    return value


def make_entry(hass: HomeAssistant, *people: Customer) -> EvnConfigEntry:
    people = people or (PERSON,)
    entry: EvnConfigEntry = ConfigEntry(
        domain=DOMAIN,
        title="EVN CSKH",
        unique_id=None,
        data=PRIVATE | {CONF_CUSTOMERS: customer_inventory(list(people))},
        options={CONF_SELECTED_CUSTOMERS: [customer_key(person) for person in people]},
        source=SOURCE_USER,
        version=1,
        minor_version=1,
        discovery_keys=MappingProxyType({}),
        subentries_data=(),
    )
    client = Mock(spec=EvnClient)
    client.details = AsyncMock(side_effect=make_details)
    client.invoice_pdf = AsyncMock(return_value=PDF)
    coordinator = EvnCoordinator(hass, entry, client)
    coordinator.data = {
        customer_key(person): make_snapshot(person) for person in people
    }
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    entry.runtime_data = coordinator
    object.__setattr__(entry, "state", ConfigEntryState.LOADED)
    return entry


@pytest.fixture
async def entry(hass: HomeAssistant) -> EvnConfigEntry:
    entry = make_entry(hass)
    await panel.async_attach_entry(hass, entry)
    return entry


class Connection:
    def __init__(self, user: Any = None) -> None:
        self.user = (
            user if user is not None else SimpleNamespace(is_admin=True, is_active=True)
        )
        self.messages: list[dict[str, Any]] = []
        self.ready = asyncio.Event()

    def send_result(self, message_id: int, result: Any) -> None:
        self.messages.append({"id": message_id, "result": result})
        self.ready.set()

    def send_error(self, message_id: int, code: str, message: str) -> None:
        self.messages.append(
            {"id": message_id, "error": {"code": code, "message": message}}
        )
        self.ready.set()

    def async_handle_exception(self, msg: dict[str, Any], error: Exception) -> None:
        raise AssertionError(
            "An unsanitized exception escaped the WS handler"
        ) from error


async def ws(
    hass: HomeAssistant, command: str, *, user: Any = None, **args: Any
) -> dict[str, Any]:
    connection = Connection(user)
    handler, schema = hass.data[websocket_api.DOMAIN][f"evn_cskh/{command}"]
    message = {"id": 1, "type": f"evn_cskh/{command}", **args}
    if schema is not False:
        message = schema(message)
    handler(hass, cast(websocket_api.ActiveConnection, connection), message)
    await asyncio.wait_for(connection.ready.wait(), timeout=3)
    assert len(connection.messages) == 1
    json.dumps(connection.messages, allow_nan=False)
    return connection.messages[0]


def detail_args(entry: EvnConfigEntry, **updates: Any) -> dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "customer_key": customer_key(PERSON),
        "point_id": POINT,
        "start": START,
        "end": END,
        **updates,
    }


def admin(*, active: bool = True, owner: bool = True) -> User:
    return User(
        "Offline", cast(PermissionLookup, None), is_active=active, is_owner=owner
    )


def request(
    *,
    user: Any = None,
    authorization: str | None = "Bearer synthetic-ha-header",
    query: str = "",
    authenticated: bool = True,
) -> web.Request:
    headers = {} if authorization is None else {"Authorization": authorization}
    req = make_mocked_request(
        "GET", "/api/evn_cskh/invoice/a/b/invoice" + query, headers=headers
    )
    if user is not False:
        req["hass_user"] = user if user is not None else admin()
    req[KEY_AUTHENTICATED] = authenticated
    return req


async def download(
    hass: HomeAssistant,
    entry: EvnConfigEntry,
    key: str,
    kind: str = "invoice",
    **kwargs: Any,
) -> web.Response:
    return await panel._InvoiceView(panel._manager(hass)).get(
        request(**kwargs), entry.entry_id, key, kind
    )


async def invoice_key(
    hass: HomeAssistant, entry: EvnConfigEntry, **updates: Any
) -> str:
    response = await ws(hass, "details", **detail_args(entry, **updates))
    return cast(str, response["result"]["invoices"][0]["key"])


async def test_registration_once_dynamic_entries(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    static = AsyncMock(wraps=hass.http.async_register_static_paths)
    view = Mock(wraps=hass.http.register_view)
    register = Mock(wraps=websocket_api.async_register_command)
    custom = AsyncMock(wraps=panel_custom.async_register_panel)
    monkeypatch.setattr(hass.http, "async_register_static_paths", static)
    monkeypatch.setattr(hass.http, "register_view", view)
    monkeypatch.setattr(websocket_api, "async_register_command", register)
    monkeypatch.setattr(panel_custom, "async_register_panel", custom)
    sentinel = object()
    hass.data[DOMAIN] = sentinel
    await asyncio.gather(*(panel.async_setup_panel(hass) for _ in range(5)))
    assert not hass.data.get(frontend.DATA_PANELS)
    first, second = make_entry(hass), make_entry(hass, OTHER)
    coordinator = first.runtime_data
    await asyncio.gather(
        panel.async_attach_entry(hass, first),
        panel.async_attach_entry(hass, first),
        panel.async_attach_entry(hass, second),
    )
    assert first.runtime_data is coordinator
    assert hass.data[DOMAIN] is sentinel
    custom.assert_awaited_once_with(
        hass,
        frontend_url_path="evn-cskh",
        webcomponent_name="evn-cskh-panel",
        sidebar_title="EVN CSKH",
        sidebar_icon="mdi:transmission-tower",
        module_url=f"/evn_cskh_static/evn-cskh-panel.js?v={VERSION}",
        require_admin=True,
    )
    assert len((await ws(hass, "list_entries"))["result"]["entries"]) == 2
    await panel.async_detach_entry(hass, first.entry_id)
    assert "evn-cskh" in hass.data[frontend.DATA_PANELS]
    await panel.async_detach_entry(hass, second.entry_id)
    assert "evn-cskh" not in hass.data[frontend.DATA_PANELS]
    assert (await ws(hass, "list_entries"))["result"] == {"entries": []}
    response = await ws(hass, "details", **detail_args(first))
    assert response["error"]["code"] == "not_found"
    await panel.async_attach_entry(hass, first)
    assert custom.await_count == 2
    assert static.await_count == view.call_count == 1
    assert register.call_count == 3
    config = static.call_args.args[0][0]
    assert config.url_path == "/evn_cskh_static/evn-cskh-panel.js"
    assert (
        Path(config.path)
        == Path(panel.__file__).parent / "frontend" / "evn-cskh-panel.js"
    )
    assert not config.cache_headers
    routes = {route.resource.canonical for route in hass.http.app.router.routes()}
    assert routes == {config.url_path, panel._InvoiceView.url}
    assert set(hass.data[websocket_api.DOMAIN]) == {
        "evn_cskh/list_entries",
        "evn_cskh/overview",
        "evn_cskh/details",
    }


async def test_panel_registration_rollback(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = make_entry(hass)
    original = panel_custom.async_register_panel
    register = AsyncMock(side_effect=ValueError("Synthetic failure"))
    monkeypatch.setattr(panel_custom, "async_register_panel", register)
    with pytest.raises(ValueError):
        await panel.async_attach_entry(hass, entry)
    assert not panel._manager(hass).entries
    assert not panel._manager(hass).panel_registered
    monkeypatch.setattr(panel_custom, "async_register_panel", original)
    await panel.async_attach_entry(hass, entry)
    assert len(panel._manager(hass).entries) == 1


async def test_setup_recovers_without_duplicate_routes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = hass.http.register_view
    monkeypatch.setattr(hass.http, "register_view", Mock(side_effect=RuntimeError))
    with pytest.raises(RuntimeError):
        await panel.async_setup_panel(hass)
    monkeypatch.setattr(hass.http, "register_view", original)
    await panel.async_setup_panel(hass)
    routes = list(hass.http.app.router.routes())
    assert len(routes) == 2


async def test_frozen_router_fails_cleanly(hass: HomeAssistant) -> None:
    hass.http.app.router.freeze()
    with pytest.raises(HomeAssistantError, match="routes are unavailable"):
        await panel.async_setup_panel(hass)
    assert not panel._manager(hass).entries
    assert not hass.data.get(websocket_api.DOMAIN)


async def test_missing_packaged_module_fails_cleanly(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "is_file", lambda _: False)
    with pytest.raises(HomeAssistantError, match="module is unavailable"):
        await panel.async_setup_panel(hass)
    assert not list(hass.http.app.router.routes())


async def test_running_http_allows_dynamic_setup(hass: HomeAssistant) -> None:
    hass.http.app._router.freeze = lambda: None
    assert not hass.http.app.router.frozen
    await panel.async_setup_panel(hass)
    routes = {route.resource.canonical for route in hass.http.app.router.routes()}
    assert routes == {panel._STATIC_URL, panel._InvoiceView.url}


async def test_entry_state_and_domain_required(hass: HomeAssistant) -> None:
    entry = make_entry(hass)
    await panel.async_attach_entry(hass, entry)
    object.__setattr__(entry, "state", ConfigEntryState.SETUP_IN_PROGRESS)
    assert (await ws(hass, "list_entries"))["result"] == {"entries": []}
    assert (await ws(hass, "details", **detail_args(entry)))["error"][
        "code"
    ] == "not_found"
    assert (await download(hass, entry, "a" * 32)).status == 404
    object.__setattr__(entry, "state", ConfigEntryState.LOADED)
    assert len((await ws(hass, "list_entries"))["result"]["entries"]) == 1
    object.__setattr__(entry, "domain", "other_domain")
    assert (await ws(hass, "list_entries"))["result"] == {"entries": []}
    assert (await ws(hass, "details", **detail_args(entry)))["error"][
        "code"
    ] == "not_found"
    assert (await download(hass, entry, "a" * 32)).status == 404


async def test_list_selected_customers_and_redaction(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    entry.runtime_data.data[customer_key(OTHER)] = make_snapshot(OTHER)
    result = (await ws(hass, "list_entries"))["result"]
    assert result == {
        "entries": [
            {
                "entry_id": entry.entry_id,
                "title": "EVN CSKH",
                "customers": [
                    {
                        "key": customer_key(PERSON),
                        "code": PERSON.code,
                        "name": PERSON.name,
                        "unit": PERSON.management_unit,
                        "region": "PB",
                        "points": [{"id": POINT, "address": "A" * 512}],
                        "available": True,
                    }
                ],
            }
        ]
    }
    serialized = json.dumps(result)
    assert not any(
        value in serialized for value in (*PRIVATE.values(), PERSON.contract)
    )
    entry.runtime_data.last_update_success = False
    assert not (await ws(hass, "list_entries"))["result"]["entries"][0]["customers"][0][
        "available"
    ]


@pytest.mark.parametrize("command", ["list_entries", "overview", "details"])
async def test_ws_admin_and_active_user(
    hass: HomeAssistant, entry: EvnConfigEntry, command: str
) -> None:
    args = {} if command == "list_entries" else detail_args(entry)
    if command == "overview":
        args = {key: args[key] for key in ("entry_id", "customer_key")}
    with pytest.raises(Unauthorized):
        await ws(hass, command, user=admin(owner=False), **args)
    response = await ws(hass, command, user=admin(active=False), **args)
    assert response["error"]["code"] == "unauthorized"
    cast(AsyncMock, entry.runtime_data.client.details).assert_not_awaited()


@pytest.mark.parametrize(
    "command,updates",
    [
        ("overview", {"refresh": "true"}),
        ("overview", {"refresh": 1}),
        ("overview", {"customer_key": 123}),
        ("details", {"force": "false"}),
        ("details", {"point_id": ""}),
        ("details", {"start": "20261001"}),
        ("details", {"start": "2026-1-01"}),
        ("details", {"start": "2026-02-30"}),
        ("details", {"start": "2026-01-01T00:00:00"}),
        ("details", {"start": 20260101}),
        ("details", {"end": "2026-W01-1"}),
    ],
)
async def test_ws_schemas(
    hass: HomeAssistant, entry: EvnConfigEntry, command: str, updates: dict[str, Any]
) -> None:
    args = {} if command == "list_entries" else detail_args(entry)
    if command == "overview":
        args = {key: args[key] for key in ("entry_id", "customer_key")}
    with pytest.raises(vol.Invalid):
        await ws(hass, command, **(args | updates))
    cast(AsyncMock, entry.runtime_data.client.details).assert_not_awaited()


async def test_list_entries_rejects_unknown_fields(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    result = await ws(hass, "list_entries", extra=True)
    assert result["error"]["code"] == "invalid_response"


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-10-06", "2026-01-01"),
        ("2026-10-01", "2099-01-01"),
        ("2020-01-01", "2020-01-02"),
        ("2024-01-01", "2026-01-01"),
    ],
)
async def test_date_ranges_before_client(
    hass: HomeAssistant, entry: EvnConfigEntry, start: str, end: str
) -> None:
    result = await ws(hass, "details", **detail_args(entry, start=start, end=end))
    assert result["error"]["code"] == "invalid_response"
    cast(AsyncMock, entry.runtime_data.client.details).assert_not_awaited()


async def test_overview_cached_refresh_and_unavailable(
    hass: HomeAssistant, entry: EvnConfigEntry, clock: list[float]
) -> None:
    args = {"entry_id": entry.entry_id, "customer_key": customer_key(PERSON)}
    result = (await ws(hass, "overview", **args))["result"]
    assert result["usage"] == [
        {
            "point_id": POINT,
            "monthly": {"period": "2026-09", "kwh": 12.5},
            "daily": {"period": "06/10/2026", "kwh": 2.5},
        }
    ]
    assert result["outstanding"] == {"amount": 110, "count": 1}
    assert result["next_outage"]["start"] == "2099-10-08T08:00:00+07:00"
    assert result["outages"][1] == {
        "start": None,
        "end": None,
        "area": "",
        "reason": "Unknown schedule",
    }
    refresh = cast(AsyncMock, entry.runtime_data.async_request_refresh)
    refresh.assert_not_awaited()
    await asyncio.gather(
        *(ws(hass, "overview", **args, refresh=True) for _ in range(4))
    )
    assert refresh.await_count == 1
    clock[0] += 59
    await ws(hass, "overview", **args, refresh=True)
    assert refresh.await_count == 1
    clock[0] += 1
    await ws(hass, "overview", **args, refresh=True)
    assert refresh.await_count == 2
    entry.runtime_data.last_update_success = False
    result = (await ws(hass, "overview", **args))["result"]
    assert result == {
        "customer": panel._customer_dto(make_snapshot()),
        "available": False,
        "fetched_at": NOW.isoformat(),
        "usage": [],
        "outstanding": {"amount": None, "count": None},
        "outages": [],
        "outage_count": 2,
        "next_outage": None,
    }


async def test_details_contract_aggregation_and_redaction(
    hass: HomeAssistant, entry: EvnConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    result = (await ws(hass, "details", **detail_args(entry)))["result"]
    assert set(result) == {
        "customer",
        "point_id",
        "start",
        "end",
        "fetched_at",
        "monthly",
        "daily",
        "readings",
        "invoices",
    }
    assert result["monthly"] == [
        {"period": "2026-01", "kwh": 4},
        {"period": "2026-09", "kwh": 12.5},
    ]
    assert result["daily"] == [
        {"period": "05/10/2026", "kwh": 2.5},
        {"period": "06/10/2026", "kwh": 10},
    ]
    assert result["readings"][0] == {
        "period": "2026-09",
        "meter": "SYNTHETIC-METER",
        "register": "KT",
        "old": 10,
        "new": 22.5,
        "multiplier": 1,
        "kwh": 12.5,
        "kind": "monthly",
    }
    assert result["readings"][1] == {
        "period": "06/10/2026",
        "meter": "",
        "register": "",
        "old": None,
        "new": None,
        "multiplier": None,
        "kwh": None,
        "kind": "daily",
    }
    invoice = result["invoices"][0]
    assert len(invoice["key"]) == 32
    assert invoice == {
        "key": invoice["key"],
        "period": "09/2026",
        "cycle": 1,
        "amount": 110,
        "tax": 10,
        "outstanding": 110,
        "status": "CHUATT",
        "status_label": "Chưa thanh toán",
        "paid_date": "",
        "due_date": "20/10/2026",
        "energy": 12.5,
        "energy_unit": "kWh",
        "documents": ["invoice", "statement", "notice"],
    }
    serialized = json.dumps(result, allow_nan=False) + caplog.text
    assert not any(
        value in serialized for value in (*PRIVATE.values(), PERSON.contract)
    )
    cast(AsyncMock, entry.runtime_data.client.details).assert_awaited_once_with(
        PERSON, POINT, date.fromisoformat(START), date.fromisoformat(END)
    )


@pytest.mark.parametrize(
    "status,label",
    [
        ("CHUATT", "Chưa thanh toán"),
        ("DATT", "Đã thanh toán"),
        ("TTOANMOTPHAN", "Đã thanh toán một phần"),
        ("DAHT", "Đã hoàn trả"),
        ("CHUAHT", "Chưa hoàn trả"),
        ("CHOXULY", "Chờ xử lý"),
        (None, "Không xác định"),
        ("NEW-STATUS", "Không xác định"),
    ],
)
def test_invoice_status_is_explicit(status: str | None, label: str) -> None:
    result = panel._invoice_dto(invoice_row(TTRANG_TTOAN=status))
    assert result["status_label"] == label
    assert result["status"] == (status if status in panel._STATUSES else "UNKNOWN")


@pytest.mark.parametrize(
    "kind,unit", [("TD", "kWh"), ("TC", "kVArh"), ("XX", ""), (None, "")]
)
def test_invoice_energy_and_unknown_numbers(kind: str | None, unit: str) -> None:
    result = panel._invoice_dto(
        invoice_row(
            LOAI_HDON=kind,
            TONG_TIEN="NaN",
            TIEN_GTGT=True,
            TONG_NO=float("inf"),
            DIEN_TTHU="1,000",
            KY=0,
        )
    )
    assert result["energy_unit"] == unit
    assert all(
        result[key] is None
        for key in ("amount", "tax", "outstanding", "energy", "cycle")
    )
    if kind is None:
        assert result["documents"] == []


async def test_empty_states_and_output_limits(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    snapshot = entry.runtime_data.data[customer_key(PERSON)]
    snapshot.monthly.clear()
    snapshot.daily.clear()
    snapshot.invoices.clear()
    snapshot.outages = [{"LY_DO": "X" * 1000}] * 101
    overview = (
        await ws(
            hass, "overview", entry_id=entry.entry_id, customer_key=customer_key(PERSON)
        )
    )["result"]
    assert overview["outstanding"] == {"amount": 0, "count": 0}
    assert overview["usage"][0]["monthly"] is None
    assert overview["outage_count"] == 101
    assert len(overview["outages"]) == 100
    assert len(overview["outages"][0]["reason"]) == 512
    assert overview["next_outage"] is None
    details = make_details()
    details.monthly = details.daily = details.invoices = []
    details.monthly_readings = [{}] * 600
    details.daily_readings = [{}] * 400
    cast(AsyncMock, entry.runtime_data.client.details).side_effect = None
    cast(AsyncMock, entry.runtime_data.client.details).return_value = details
    result = (await ws(hass, "details", **detail_args(entry)))["result"]
    assert result["monthly"] == result["daily"] == result["invoices"] == []
    assert len(result["readings"]) == 1000
    details.daily_readings = [{}] * 401
    result = await ws(hass, "details", **detail_args(entry, start="2026-02-01"))
    assert result["error"]["code"] == "invalid_response"


async def test_more_than_200_invoices_rejected(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    details = make_details()
    details.invoices = [invoice_row(ID_HDON=str(number)) for number in range(1, 202)]
    cast(AsyncMock, entry.runtime_data.client.details).side_effect = None
    cast(AsyncMock, entry.runtime_data.client.details).return_value = details
    result = await ws(hass, "details", **detail_args(entry))
    assert result["error"]["code"] == "invalid_response"
    assert not panel._manager(hass).entry(entry.entry_id).cache


async def test_details_ttl_force_lock_and_key_invalidation(
    hass: HomeAssistant, entry: EvnConfigEntry, clock: list[float]
) -> None:
    results = await asyncio.gather(
        *(ws(hass, "details", **detail_args(entry)) for _ in range(6))
    )
    assert all(result == results[0] for result in results)
    client = cast(AsyncMock, entry.runtime_data.client.details)
    assert client.await_count == 1
    old_key = results[0]["result"]["invoices"][0]["key"]
    assert await invoice_key(hass, entry, force=True) == old_key
    assert client.await_count == 1
    clock[0] += 60
    new_key = await invoice_key(hass, entry, force=True)
    assert new_key != old_key and client.await_count == 2
    assert (await download(hass, entry, old_key)).status == 410
    clock[0] += 299
    assert await invoice_key(hass, entry) == new_key
    clock[0] += 1
    assert (await download(hass, entry, new_key)).status == 410
    assert await invoice_key(hass, entry) not in (old_key, new_key)
    assert client.await_count == 3


async def test_query_change_invalidates_same_customer_keys(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    first = await invoice_key(hass, entry)
    second = await invoice_key(hass, entry, start="2026-02-01")
    assert first != second
    assert (await download(hass, entry, first)).status == 410
    assert (await download(hass, entry, second)).status == 200
    assert len(panel._manager(hass).entry(entry.entry_id).cache) == 1


async def test_cache_bound_and_cross_entry_customer_keys(hass: HomeAssistant) -> None:
    people = [Customer(f"OFFLINE-{index}", "UNIT") for index in range(10)]
    entry = make_entry(hass, *people)
    await panel.async_attach_entry(hass, entry)
    keys = [
        await invoice_key(hass, entry, customer_key=customer_key(person))
        for person in people
    ]
    assert len(panel._manager(hass).entry(entry.entry_id).cache) == 8
    assert (await download(hass, entry, keys[0])).status == 410
    assert (await download(hass, entry, keys[-1])).status == 200
    cast(AsyncMock, entry.runtime_data.client.invoice_pdf).assert_awaited_once_with(
        people[-1], invoice_row(), "invoice"
    )
    other = make_entry(hass, people[-1])
    await panel.async_attach_entry(hass, other)
    assert (await download(hass, other, keys[-1])).status == 410
    entry.runtime_data.selected_customers = (customer_key(people[0]),)
    assert (await download(hass, entry, keys[-1])).status == 404


@pytest.mark.parametrize(
    "updates",
    [
        {"customer_key": customer_key(OTHER)},
        {"customer_key": PERSON.code},
        {"point_id": "UNAUTHORIZED-POINT"},
        {"entry_id": "unknown"},
    ],
)
async def test_unauthorized_inventory_and_point(
    hass: HomeAssistant, entry: EvnConfigEntry, updates: dict[str, Any]
) -> None:
    result = await ws(hass, "details", **detail_args(entry, **updates))
    assert result["error"]["code"] == "not_found"
    cast(AsyncMock, entry.runtime_data.client.details).assert_not_awaited()


@pytest.mark.parametrize("kind", ["invoice", "statement", "notice"])
async def test_pdf_attachment_and_headers(
    hass: HomeAssistant, entry: EvnConfigEntry, kind: str
) -> None:
    key = await invoice_key(hass, entry)
    response = await download(hass, entry, key, kind)
    assert response.status == 200 and response.body == PDF
    assert response.content_type == "application/pdf"
    assert response.content_length == len(PDF)
    assert (
        response.headers["Content-Disposition"]
        == f'attachment; filename="evn-{kind}-2026-09.pdf"'
    )
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Security-Policy"] == "sandbox; default-src 'none'"
    assert "Set-Cookie" not in response.headers and "Location" not in response.headers
    assert not any(value in str(response.headers) for value in PRIVATE.values())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user": False},
        {"user": SimpleNamespace(is_admin=False, is_active=True)},
        {"user": SimpleNamespace(is_admin=True, is_active=False)},
        {"authorization": None},
        {"authorization": "Basic fake"},
        {"authorization": "Bearer "},
        {"query": "?authSig=fake"},
        {"query": "?anything=1"},
        {"query": "?authSig="},
    ],
)
async def test_pdf_header_admin_only(
    hass: HomeAssistant, entry: EvnConfigEntry, kwargs: dict[str, Any]
) -> None:
    key = await invoice_key(hass, entry)
    response = await download(hass, entry, key, **kwargs)
    assert response.status == 403
    cast(AsyncMock, entry.runtime_data.client.invoice_pdf).assert_not_awaited()


async def test_http_auth_is_delegated_to_ha(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    view = panel._InvoiceView(panel._manager(hass))
    handler = request_handler_factory(hass, view, view.get)
    with pytest.raises(web.HTTPUnauthorized):
        await handler(request(authenticated=False))
    assert view.requires_auth


@pytest.mark.parametrize(
    "key,kind",
    [
        ("PRIVATE-INVOICE-ID", "invoice"),
        ("a" * 32, "invoice"),
        ("a" * 32, "other"),
        ("../invoice", "invoice"),
    ],
)
async def test_pdf_keys_not_raw_ids(
    hass: HomeAssistant, entry: EvnConfigEntry, key: str, kind: str
) -> None:
    response = await download(hass, entry, key, kind)
    assert response.status in (404, 410)
    cast(AsyncMock, entry.runtime_data.client.invoice_pdf).assert_not_awaited()


@pytest.mark.parametrize(
    "error,code,status",
    [
        (EvnAuthError(), "auth", 403),
        (EvnConnectionError(), "cannot_connect", 503),
        (EvnResponseError(), "invalid_response", 502),
        (RuntimeError("PRIVATE-ACCESS"), "invalid_response", 502),
    ],
)
async def test_generic_errors_never_echo_or_log(
    hass: HomeAssistant,
    entry: EvnConfigEntry,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    code: str,
    status: int,
) -> None:
    key = await invoice_key(hass, entry)
    cast(AsyncMock, entry.runtime_data.client.invoice_pdf).side_effect = error
    response = await download(hass, entry, key)
    assert response.status == status
    assert json.loads(cast(str, response.text))["error"] == code
    cast(AsyncMock, entry.runtime_data.client.details).side_effect = error
    result = await ws(hass, "details", **detail_args(entry, start="2026-02-01"))
    assert result["error"]["code"] == code
    assert "PRIVATE-ACCESS" not in caplog.text + str(result) + str(response.body)


@pytest.mark.parametrize(
    "data",
    [
        b"not PDF",
        b"%PDF-1.7\nmissing EOF",
        b"%PDF-1.7\n%%EOF\n<script>",
        b"%PDF-1.7\n" + b"x" * (16 * 1024 * 1024) + b"\n%%EOF\n",
    ],
)
async def test_invalid_pdf_body_rejected(
    hass: HomeAssistant, entry: EvnConfigEntry, data: bytes
) -> None:
    key = await invoice_key(hass, entry)
    cast(AsyncMock, entry.runtime_data.client.invoice_pdf).return_value = data
    response = await download(hass, entry, key)
    assert response.status == 502
    assert response.content_type == "application/json"


@pytest.mark.parametrize("operation", ["details", "overview", "pdf"])
@pytest.mark.parametrize("ignore_cancel", [False, True])
async def test_unload_reload_inflight_never_returns_data(
    hass: HomeAssistant, entry: EvnConfigEntry, operation: str, ignore_cancel: bool
) -> None:
    entered, released = asyncio.Event(), asyncio.Event()
    key = await invoice_key(hass, entry) if operation == "pdf" else ""

    async def gated(*args: Any) -> Any:
        entered.set()
        try:
            await released.wait()
        except asyncio.CancelledError:
            if not ignore_cancel:
                raise
            await released.wait()
        return PDF if operation == "pdf" else make_details()

    if operation == "details":
        cast(AsyncMock, entry.runtime_data.client.details).side_effect = gated
        task = asyncio.create_task(ws(hass, "details", **detail_args(entry)))
    elif operation == "overview":
        cast(AsyncMock, entry.runtime_data.async_request_refresh).side_effect = gated
        task = asyncio.create_task(
            ws(
                hass,
                "overview",
                entry_id=entry.entry_id,
                customer_key=customer_key(PERSON),
                refresh=True,
            )
        )
    else:
        cast(AsyncMock, entry.runtime_data.client.invoice_pdf).side_effect = gated
        task = asyncio.create_task(download(hass, entry, key))
    await asyncio.wait_for(entered.wait(), 3)
    previous = panel._manager(hass).entry(entry.entry_id)
    await panel.async_detach_entry(hass, entry.entry_id)
    await panel.async_attach_entry(hass, entry)
    released.set()
    result = await asyncio.wait_for(task, 3)
    if isinstance(result, web.Response):
        assert result.status == 410
        assert result.body != PDF
    else:
        assert result["error"]["code"] == "stale"
        assert "result" not in result
    assert not previous.cache and not previous.jobs
    assert not panel._manager(hass).entry(entry.entry_id).cache


async def test_lock_does_not_block_other_entries_or_detach(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked(*args: Any) -> DetailSnapshot:
        entered.set()
        await release.wait()
        return make_details()

    cast(AsyncMock, entry.runtime_data.client.details).side_effect = blocked
    pending = asyncio.create_task(ws(hass, "details", **detail_args(entry)))
    await asyncio.wait_for(entered.wait(), 3)
    other = make_entry(hass, OTHER)
    await asyncio.wait_for(panel.async_attach_entry(hass, other), 3)
    result = await ws(
        hass, "details", **detail_args(other, customer_key=customer_key(OTHER))
    )
    assert "result" in result
    await asyncio.wait_for(panel.async_detach_entry(hass, entry.entry_id), 3)
    assert (await pending)["error"]["code"] == "stale"


async def test_selection_and_admin_rechecked_after_await(
    hass: HomeAssistant, entry: EvnConfigEntry
) -> None:
    key = await invoice_key(hass, entry)
    entered, release = asyncio.Event(), asyncio.Event()

    async def gated(*args: Any) -> bytes:
        entered.set()
        await release.wait()
        return PDF

    user = admin()
    cast(AsyncMock, entry.runtime_data.client.invoice_pdf).side_effect = gated
    pending = asyncio.create_task(download(hass, entry, key, user=user))
    await entered.wait()
    user.is_active = False
    release.set()
    assert (await pending).status == 403
    entered.clear()
    release.clear()
    pending = asyncio.create_task(download(hass, entry, key))
    await entered.wait()
    entry.runtime_data.selected_customers = ()
    release.set()
    assert (await pending).status == 404
