from __future__ import annotations

import asyncio
import importlib.util
import json
import secrets
import sys
import traceback
from collections.abc import AsyncIterator, Callable
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, cast
from unittest.mock import Mock
from urllib.parse import quote

import pytest
from aiohttp import ClientConnectionError, ClientRequest, ClientSession, ClientTimeout
from aiohttp.client_proto import ResponseHandler
from aiohttp.payload import JsonPayload
from yarl import URL

_SPEC = importlib.util.spec_from_file_location(
    "_evn_cskh_api_offline",
    Path(__file__).resolve().parents[1] / "custom_components" / "evn_cskh" / "api.py",
)
assert _SPEC is not None and _SPEC.loader is not None
api = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = api
_SPEC.loader.exec_module(api)

_MISSING = object()
BASES = {
    "PA": "https://apicskhevn.npc.com.vn",
    "PB": "https://api.cskh.evnspc.vn/api-cskh-evn",
    "PC": "https://cskh-api.cpc.vn",
    "HN": "https://gwkong.evnhanoi.vn",
    "PE": "https://openapi.evnhcmc.vn/evn-ttcskh/appcskh",
}


class Reply:
    def __init__(
        self,
        data: Any = None,
        *,
        status: int = 200,
        payload: Any = _MISSING,
        raw: bytes | None = None,
        content_length: Any = _MISSING,
        error: BaseException | None = None,
        read_error: BaseException | None = None,
        delay: float = 0,
    ) -> None:
        self.status = status
        self.raw = (
            raw
            if raw is not None
            else json.dumps(
                {"success": True, "data": data} if payload is _MISSING else payload
            ).encode()
        )
        self.content_length = (
            len(self.raw) if content_length is _MISSING else content_length
        )
        self.error = error
        self.read_error = read_error
        self.delay = delay
        self.content = self
        self.consumed = 0
        self.exited = False

    async def __aenter__(self) -> Self:
        await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self

    async def __aexit__(self, *args: object) -> bool:
        self.exited = True
        return False

    async def iter_chunked(self, size: int) -> AsyncIterator[bytes]:
        if self.read_error is not None:
            raise self.read_error
        for offset in range(0, len(self.raw), size):
            await asyncio.sleep(0)
            chunk = self.raw[offset : offset + size]
            self.consumed += len(chunk)
            yield chunk


class Session:
    def __init__(self, *replies: Reply) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **options: Any) -> Reply:
        assert options["allow_redirects"] is False
        assert options["raise_for_status"] is False
        timeout = options["timeout"]
        assert isinstance(timeout, ClientTimeout)
        assert timeout.total is not None and 0 < timeout.total <= 30
        assert timeout.connect is not None and 0 < timeout.connect <= 30
        assert timeout.sock_read is not None and 0 < timeout.sock_read <= 30
        self.calls.append({"method": method, "url": url, **options})
        assert self.replies, "Unexpected offline request"
        return self.replies.pop(0)

    def done(self) -> None:
        assert not self.replies


@pytest.fixture(autouse=True)
def block_real_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    async def blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound requests are disabled")

    monkeypatch.setattr(ClientSession, "_request", blocked)


@pytest.fixture
def identity() -> dict[str, str]:
    return {
        "username": "offline-" + secrets.token_hex(8),
        "password": secrets.token_urlsafe(24) + " &+%=?/'\"\\\n mật khẩu ",
        "device_id": secrets.token_hex(8),
    }


@pytest.fixture
def tokens() -> Any:
    return api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))


def make_client(session: Session, identity: dict[str, str], **options: Any) -> Any:
    return api.EvnClient(cast(ClientSession, session), **identity, **options)


def contract(number: int = 1) -> dict[str, str]:
    return {
        "maKhang": f"TEST-CUSTOMER-{number}",
        "maDviqly": f"TEST-UNIT-{number}",
        "tenKhang": f"Offline customer {number}",
        "maHdong": f"TEST-CONTRACT-{number}",
    }


def customer(number: int = 1) -> Any:
    row = contract(number)
    return api.Customer(
        row["maKhang"], row["maDviqly"], row["tenKhang"], row["maHdong"]
    )


def config(region: str = "PB", base: Any = _MISSING) -> Reply:
    return Reply(
        [
            {"key": "OTHER_SETTING", "value": "ignored"},
            {
                "key": "URL_API",
                "subdivisionid": region,
                "value": BASES[region] if base is _MISSING else base,
            },
        ]
    )


def switched(person: Any, access_token: str, region: str = "PB") -> Reply:
    return Reply(
        {
            "accessToken": access_token,
            "data": {
                "maDviCaptct": region,
                "maKhang": person.code,
                "maDviqly": person.management_unit,
            },
        }
    )


def snapshot_replies(person: Any, access_token: str, region: str = "PB") -> list[Reply]:
    owner = {"MA_KHANG": person.code, "MA_DVIQLY": person.management_unit}
    return [
        switched(person, access_token, region),
        Reply([owner | {"MA_DDO": "POINT-1", "SO_CTO": "METER-A"}]),
        Reply([owner | {"DIEN_TTHU": 123, "SO_CTO": "METER-A"}]),
        Reply([owner | {"MA_DDO": "POINT-1", "DIEN_TTHU": 4, "BCS": "KT"}]),
        Reply([owner | {"MA_DDO": "POINT-1", "CHISO_MOI": 10}]),
        Reply([owner | {"MA_DDO": "POINT-1", "CHISO_MOI": 3}]),
        Reply([owner | {"DUONG_PHO": "Offline street"}]),
        Reply([owner | {"ID_HDON": "INVOICE-1", "TONG_TIEN": 321}]),
        Reply([owner | {"ID_HDON": "INVOICE-0", "TONG_TIEN": 300}]),
        Reply([{"MA_TCHUC": "BANK-1", "TEN_TCHUC": "Offline bank"}]),
        Reply([owner | {"NOI_DUNG": "Offline planned work"}]),
    ]


def paths(session: Session) -> list[str]:
    return [call["url"].removeprefix(api.CENTRAL_BASE) for call in session.calls]


def test_dataclasses_and_serialization(tokens: Any) -> None:
    person = customer()
    with pytest.raises(FrozenInstanceError):
        person.code = "OTHER"
    state = api.TokenState(
        tokens.access_token, tokens.refresh_token, person.code, person.management_unit
    )
    serialized = state.to_dict()
    assert serialized == {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "customer_code": person.code,
        "management_unit": person.management_unit,
    }
    assert api.TokenState.from_dict(serialized) == state
    assert api.TokenState.from_dict(tokens.to_dict()) == tokens
    serialized["access_token"] = secrets.token_urlsafe(24)
    assert state.access_token == tokens.access_token
    for private in (state.access_token, state.refresh_token, state.customer_code):
        assert private not in repr(state)
    assert person.name not in repr(person)
    assert api.Customer("TEST", "UNIT").name == ""
    assert api.Customer("TEST", "UNIT").contract == ""


@pytest.mark.parametrize(
    "update",
    [
        {"access_token": None},
        {"access_token": ""},
        {"access_token": "invalid\r\nheader"},
        {"access_token": "invalid space"},
        {"refresh_token": 12},
        {"refresh_token": ""},
        {"customer_code": ""},
        {"management_unit": 12},
        {"customer_code": 12, "management_unit": "UNIT"},
    ],
)
def test_invalid_stored_tokens(tokens: Any, update: dict[str, Any]) -> None:
    with pytest.raises(api.EvnAuthError):
        api.TokenState.from_dict(tokens.to_dict() | update)


@pytest.mark.parametrize("value", [None, [], {}, "invalid"])
def test_invalid_stored_mapping(value: Any) -> None:
    with pytest.raises(api.EvnAuthError):
        api.TokenState.from_dict(value)


@pytest.mark.parametrize("device_id", ["", "short", "g" * 16, "0" * 17, "0" * 15, None])
def test_invalid_device_id(identity: dict[str, str], device_id: Any) -> None:
    session = Session()
    with pytest.raises(api.EvnError):
        make_client(session, identity | {"device_id": device_id})
    assert not session.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("canonicalize", [False, True])
async def test_login_payload_and_callback(
    identity: dict[str, str], tokens: Any, canonicalize: bool
) -> None:
    canonical = "canonical-" + secrets.token_hex(8)
    account = (
        {"username": canonical, "isDefaultPassVneid": False} if canonicalize else {}
    )
    session = Session(
        Reply(account),
        Reply(
            {"accessToken": tokens.access_token, "refreshToken": tokens.refresh_token}
        ),
    )
    changes: list[Any] = []

    def changed(state: Any) -> None:
        assert client.tokens is state
        assert len(session.calls) == 2
        changes.append(state)

    client = make_client(session, identity, on_tokens=changed)
    assert client.tokens is None
    assert await client.login() is None
    assert paths(session) == ["/auth/checkAccInUse", "/auth/login"]
    assert session.calls[0]["json"] == {"phone": identity["username"]}
    assert session.calls[1]["json"] == {
        "username": canonical if canonicalize else identity["username"],
        "password": identity["password"],
        "deviceInfo": {
            "deviceId": identity["device_id"],
            "deviceType": "Home Assistant",
        },
    }
    assert all(call["method"] == "POST" for call in session.calls)
    assert all("Authorization" not in call["headers"] for call in session.calls)
    assert changes == [tokens]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize("account", [_MISSING, None, {"isDefaultPassVneid": True}])
async def test_account_action_stops_password_login(
    identity: dict[str, str], account: Any, status: int
) -> None:
    payload = {"success": True, "timestamp": "2026-10-07T00:00:00Z"}
    if account is not _MISSING:
        payload["data"] = account
    session = Session(Reply(payload=payload, status=status))
    changes: list[Any] = []
    client = make_client(session, identity, on_tokens=changes.append)
    with pytest.raises(api.EvnUserActionRequired):
        await client.login()
    for _ in range(3):
        with pytest.raises(api.EvnAuthError):
            await client.customers()
        with pytest.raises(api.EvnAuthError):
            await client.fetch_snapshot(customer())
    assert paths(session) == ["/auth/checkAccInUse"]
    assert session.calls[0]["json"] == {"phone": identity["username"]}
    assert "Authorization" not in session.calls[0]["headers"]
    assert client.tokens is None
    assert not changes
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "account",
    [
        [],
        False,
        {"username": 123},
        {"username": False},
        {"username": 0},
        {"username": []},
        {"username": {}},
        {"username": " "},
        {"username": "\t"},
        {"username": "\u00a0"},
        {"username": " leading"},
        {"username": "trailing "},
        {"username": "embedded whitespace"},
        {"username": "invalid\r\nheader"},
        {"isDefaultPassVneid": "false"},
    ],
)
async def test_lookup_schema_rejected(identity: dict[str, str], account: Any) -> None:
    session = Session(Reply(account))
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity).login()
    assert paths(session) == ["/auth/checkAccInUse"]
    session.done()


@pytest.mark.asyncio
async def test_lazy_login_is_serialized(identity: dict[str, str], tokens: Any) -> None:
    session = Session(
        Reply({}),
        Reply(
            {"accessToken": tokens.access_token, "refreshToken": tokens.refresh_token}
        ),
        Reply([contract(), contract(), contract(2)]),
    )
    changes: list[Any] = []
    client = make_client(session, identity, on_tokens=changes.append)
    results = await asyncio.gather(*(client.customers() for _ in range(5)))
    assert all(result == [customer(), customer(2)] for result in results)
    results[0].clear()
    assert await client.customers() == [customer(), customer(2)]
    assert paths(session) == ["/auth/checkAccInUse", "/auth/login", "/user/me"]
    assert changes == [tokens]
    session.done()


@pytest.mark.asyncio
async def test_customer_dedup_uses_code_and_unit(
    identity: dict[str, str], tokens: Any
) -> None:
    row = contract()
    other_unit = row | {"maDviqly": "OTHER-UNIT"}
    session = Session(Reply([row, row.copy(), other_unit]))
    result = await make_client(session, identity, tokens=tokens).customers()
    assert [(entry.code, entry.management_unit) for entry in result] == [
        (row["maKhang"], row["maDviqly"]),
        (row["maKhang"], "OTHER-UNIT"),
    ]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 400])
async def test_imported_tokens_and_empty_customers(
    identity: dict[str, str], tokens: Any, status: int
) -> None:
    session = Session(Reply([], status=status))
    changes: list[Any] = []
    client = make_client(
        session,
        identity | {"username": "", "password": ""},
        tokens=tokens,
        on_tokens=changes.append,
    )
    assert await client.customers() == []
    assert await client.customers() == []
    assert paths(session) == ["/user/me"]
    assert (
        session.calls[0]["headers"]["Authorization"] == "Bearer " + tokens.access_token
    )
    assert not changes
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"data": []},
        {"success": 1, "data": []},
        {"success": "true", "data": []},
        {"success": True},
        {"success": False, "data": []},
        {"success": True, "data": None},
        {"success": True, "data": {}},
        {"success": True, "data": {"data": []}},
        {"success": True, "data": [None]},
        {"success": True, "data": [[]]},
        {"success": True, "data": [{}]},
        {"success": True, "data": [contract() | {"maKhang": 1}]},
        {"success": True, "data": [contract() | {"maDviqly": ""}]},
        {"success": True, "data": [contract() | {"tenKhang": None}]},
        {"success": True, "data": [contract() | {"maHdong": []}]},
        {"success": True, "data": [contract() | {"maKhang": ".."}]},
    ],
)
async def test_customer_schema_failures_not_empty(
    identity: dict[str, str], tokens: Any, payload: Any
) -> None:
    session = Session(Reply(payload=payload))
    client = make_client(session, identity, tokens=tokens)
    with pytest.raises(api.EvnResponseError):
        await client.customers()
    assert client.tokens is tokens
    session.done()


@pytest.mark.parametrize("region", list(BASES))
def test_url_prefix_and_allowlist(region: str) -> None:
    base = BASES[region]
    assert api._regional_base(region, base + "/") == base
    assert (
        api._join_url(base + "///", "///api/evn/customers/diemdo")
        == base + "/api/evn/customers/diemdo"
    )
    assert (
        api._join_url(api.CENTRAL_BASE + "/", "/user/me")
        == "https://cskh.evn.com.vn/cskh/v1/user/me"
    )
    assert (
        api._regional_base("PB", "https://api.cskh.evnspc.vn:443/api-cskh-evn/")
        == "https://api.cskh.evnspc.vn:443/api-cskh-evn"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_base",
    [
        "http://api.cskh.evnspc.vn/api-cskh-evn",
        "//api.cskh.evnspc.vn/api-cskh-evn",
        "https://api.cskh.evnspc.vn.evil.invalid/api",
        "https://evil.invalid/api",
        "https://127.0.0.1/api",
        "https://[::1]/api",
        "https://cskh.evn.com.vn/api",
        "https://apicskhevn.npc.com.vn/api",
        "https://user@api.cskh.evnspc.vn/api",
        "https://user:pass@api.cskh.evnspc.vn/api",
        "https://api.cskh.evnspc.vn:444/api",
        "https://api.cskh.evnspc.vn:invalid/api",
        "https://api.cskh.evnspc.vn./api",
        "https://api.cskh.evnspc.vn/api?secret=synthetic",
        "https://api.cskh.evnspc.vn/api?",
        "https://api.cskh.evnspc.vn/api#fragment",
        "https://api.cskh.evnspc.vn/api#",
        "https://api.cskh.evnspc.vn\\@evil.invalid/api",
        "https://api.cskh.evnspc.vn/api/../other",
        "https://api.cskh.evnspc.vn/api/%2e%2e/other",
        "https://api.cskh.evnspc.vn/api/%0aheader",
        "https://api.cskh.evnspc.vn/api/%5cother",
        " https://api.cskh.evnspc.vn/api",
        "https://api.cskh.evnspc.vn/api\n",
        "https://[invalid/api",
        None,
        123,
        {},
    ],
)
async def test_malicious_config_never_receives_tokens(
    identity: dict[str, str], tokens: Any, bad_base: Any
) -> None:
    session = Session(Reply([contract()]), config(base=bad_base))
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    with pytest.raises(api.EvnResponseError):
        await client.fetch_snapshot(customer())
    assert paths(session) == ["/user/me", "/public/allconfig"]
    assert "Authorization" not in session.calls[1]["headers"]
    assert client.tokens is tokens
    assert not changes
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rows",
    [
        None,
        {},
        [None],
        [{}],
        [{"key": "URL_API", "value": BASES["PB"]}],
        [{"key": "URL_API", "subdivisionid": "UNKNOWN", "value": BASES["PB"]}],
        [
            {"key": "URL_API", "subdivisionid": "PB", "value": BASES["PB"]},
            {
                "key": "URL_API",
                "subdivisionid": "PB",
                "value": BASES["PB"] + "/different",
            },
        ],
    ],
)
async def test_invalid_config_schema(
    identity: dict[str, str], tokens: Any, rows: Any
) -> None:
    session = Session(Reply([contract()]), Reply(rows))
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(customer())
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [201, 204, 300, 301, 302, 303, 307, 308, 404, 418])
async def test_unexpected_status_and_redirect_not_followed(
    identity: dict[str, str], tokens: Any, status: int
) -> None:
    session = Session(Reply([], status=status))
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).customers()
    assert paths(session) == ["/user/me"]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("context", [False, True])
@pytest.mark.parametrize("refresh_mode", ["missing", "null", "empty", "rotate"])
async def test_one_refresh_with_device_context_and_rotation(
    identity: dict[str, str], tokens: Any, context: bool, refresh_mode: str
) -> None:
    old = api.TokenState(
        tokens.access_token,
        tokens.refresh_token,
        customer().code if context else None,
        customer().management_unit if context else None,
    )
    new_access = secrets.token_urlsafe(24)
    new_refresh = (
        secrets.token_urlsafe(24) if refresh_mode == "rotate" else old.refresh_token
    )
    refresh_data: dict[str, Any] = {"accessToken": new_access}
    if refresh_mode != "missing":
        refresh_data["refreshToken"] = {
            "null": None,
            "empty": "",
            "rotate": new_refresh,
        }[refresh_mode]
    session = Session(Reply(status=401), Reply(refresh_data), Reply([]))
    changes: list[Any] = []

    def changed(state: Any) -> None:
        assert client.tokens is state
        assert len(session.calls) == 2
        changes.append(state)

    client = make_client(session, identity, tokens=old, on_tokens=changed)
    assert await client.customers() == []
    assert paths(session) == ["/user/me", "/auth/refresh", "/user/me"]
    assert session.calls[1]["method"] == "POST"
    assert session.calls[1]["json"] == {
        "refreshToken": old.refresh_token,
        "maKhachhang": old.customer_code,
        "donviquanly": old.management_unit,
    }
    assert session.calls[1]["headers"]["X-deviceId"] == identity["device_id"]
    assert "Authorization" not in session.calls[1]["headers"]
    assert session.calls[0]["headers"]["Authorization"] == "Bearer " + old.access_token
    assert session.calls[2]["headers"]["Authorization"] == "Bearer " + new_access
    assert changes == [
        api.TokenState(new_access, new_refresh, old.customer_code, old.management_unit)
    ]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reply_factory",
    [
        lambda: Reply(status=401),
        lambda: Reply(status=403),
        lambda: Reply(status=302),
        lambda: Reply(payload={"success": False, "data": None}, status=400),
        lambda: Reply(payload={"success": False, "data": None}),
        lambda: Reply(None),
        lambda: Reply({}),
        lambda: Reply({"accessToken": ""}),
        lambda: Reply(
            {"accessToken": secrets.token_urlsafe(24), "refreshToken": False}
        ),
        lambda: Reply(raw=b"not JSON"),
        lambda: Reply(payload={"data": {"accessToken": secrets.token_urlsafe(24)}}),
    ],
)
async def test_failed_refresh_never_retries_password(
    identity: dict[str, str], tokens: Any, reply_factory: Callable[[], Reply]
) -> None:
    session = Session(Reply(status=401), reply_factory())
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    for _ in range(3):
        with pytest.raises(api.EvnAuthError):
            await client.customers()
    assert paths(session) == ["/user/me", "/auth/refresh"]
    assert client.tokens is tokens
    assert not changes
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_replay_is_once(
    identity: dict[str, str], tokens: Any, status: int
) -> None:
    access = secrets.token_urlsafe(24)
    refresh = secrets.token_urlsafe(24)
    session = Session(
        Reply(status=401),
        Reply({"accessToken": access, "refreshToken": refresh}),
        Reply(status=status),
    )
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    for _ in range(2):
        with pytest.raises(api.EvnAuthError):
            await client.customers()
    assert paths(session) == ["/user/me", "/auth/refresh", "/user/me"]
    assert client.tokens == api.TokenState(access, refresh)
    assert changes == [client.tokens]
    session.done()


@pytest.mark.asyncio
async def test_forbidden_does_not_refresh(
    identity: dict[str, str], tokens: Any
) -> None:
    session = Session(Reply(status=403))
    client = make_client(session, identity, tokens=tokens)
    for _ in range(2):
        with pytest.raises(api.EvnAuthError):
            await client.customers()
    assert paths(session) == ["/user/me"]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("during_refresh", [False, True])
@pytest.mark.parametrize(
    "failure", [408, 429, 500, 502, 503, 599, "connection", "timeout", "read"]
)
async def test_transient_failures_preserve_tokens(
    identity: dict[str, str], tokens: Any, during_refresh: bool, failure: int | str
) -> None:
    sensitive = identity["password"] + tokens.access_token + api.CENTRAL_BASE
    if isinstance(failure, int):
        reply = Reply(payload={"message": sensitive}, status=failure)
    elif failure == "connection":
        reply = Reply(error=ClientConnectionError(sensitive))
    elif failure == "read":
        reply = Reply(read_error=ClientConnectionError(sensitive))
    else:
        reply = Reply(error=TimeoutError(sensitive))
    session = Session(
        *([Reply(status=401)] if during_refresh else []), reply, Reply([])
    )
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    with pytest.raises(api.EvnConnectionError) as caught:
        await client.customers()
    formatted = "".join(traceback.format_exception(caught.value))
    for private in (identity["password"], tokens.access_token, api.CENTRAL_BASE):
        assert private not in formatted
    assert client.tokens is tokens
    assert not changes
    assert await client.customers() == []
    assert all("/auth/login" not in call["url"] for call in session.calls)
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw", [b"", b"<html>failure</html>", b"\xff", b"{", b"[]", b"null"]
)
async def test_malformed_json_is_redacted(
    identity: dict[str, str], tokens: Any, raw: bytes
) -> None:
    session = Session(Reply(raw=raw))
    with pytest.raises(api.EvnResponseError) as caught:
        await make_client(session, identity, tokens=tokens).customers()
    assert str(caught.value) == "EVN returned an invalid response."
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("content_length", [None, 1, api._MAX_RESPONSE_BYTES + 1])
async def test_response_size_is_bounded(
    identity: dict[str, str], tokens: Any, content_length: int | None
) -> None:
    reply = Reply(
        raw=b" " * (api._MAX_RESPONSE_BYTES + 131072), content_length=content_length
    )
    session = Session(reply)
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).customers()
    assert reply.consumed <= api._MAX_RESPONSE_BYTES + 65536
    assert reply.consumed < len(reply.raw)
    assert reply.exited
    session.done()


@pytest.mark.asyncio
async def test_response_size_boundary(identity: dict[str, str], tokens: Any) -> None:
    raw = json.dumps({"success": True, "data": []}).encode()
    reply = Reply(
        raw=raw + b" " * (api._MAX_RESPONSE_BYTES - len(raw)), content_length=None
    )
    session = Session(reply)
    assert await make_client(session, identity, tokens=tokens).customers() == []
    assert reply.consumed == api._MAX_RESPONSE_BYTES
    session.done()


@pytest.mark.asyncio
async def test_actual_timeout_and_cancellation(
    identity: dict[str, str], tokens: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api, "_REQUEST_TIMEOUT", 0.01)
    session = Session(
        Reply([], delay=1), Reply(error=asyncio.CancelledError()), Reply([])
    )
    client = make_client(session, identity, tokens=tokens)
    with pytest.raises(api.EvnConnectionError):
        await asyncio.wait_for(client.customers(), 0.5)
    assert client.tokens is tokens
    with pytest.raises(asyncio.CancelledError):
        await client.customers()
    assert client.tokens is tokens
    assert await client.customers() == []
    session.done()


@pytest.mark.asyncio
async def test_response_error_does_not_expose_payload(
    identity: dict[str, str], tokens: Any
) -> None:
    private = identity["username"] + identity["password"] + tokens.access_token
    session = Session(
        Reply(payload={"success": False, "message": private, "url": api.CENTRAL_BASE})
    )
    with pytest.raises(api.EvnResponseError) as caught:
        await make_client(session, identity, tokens=tokens).customers()
    formatted = "".join(traceback.format_exception(caught.value))
    assert private not in formatted
    assert identity["username"] not in repr(caught.value)
    assert api.CENTRAL_BASE not in formatted
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("region", list(BASES))
async def test_regional_snapshot_and_local_dates(
    identity: dict[str, str], tokens: Any, monkeypatch: pytest.MonkeyPatch, region: str
) -> None:
    frozen = datetime(2025, 12, 31, 17, 30, tzinfo=UTC)

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Self:
            return cls.fromtimestamp(frozen.timestamp(), tz)

    monkeypatch.setattr(api, "datetime", Clock)
    person = customer()
    access = secrets.token_urlsafe(24)
    owner = {"MA_KHANG": person.code, "MA_DVIQLY": person.management_unit}
    points = [
        owner | {"MA_DDO": "POINT-1", "SO_CTO": "METER-A"},
        {"MA_DDO": "POINT-2"},
    ]
    monthly = [[owner | {"DIEN_TTHU": 123}], []]
    daily = [[], [owner | {"MA_DDO": "POINT-2", "DIEN_TTHU": 4, "BCS": "KT"}]]
    monthly_readings = [[owner | {"MA_DDO": "POINT-1", "CHISO_MOI": 10}], []]
    daily_readings = [[], [owner | {"MA_DDO": "POINT-2", "CHISO_MOI": 3}]]
    contracts = [owner | {"DUONG_PHO": "Offline street"}]
    invoices = [owner | {"ID_HDON": "INVOICE-1", "TONG_TIEN": 321}]
    paid = [owner | {"ID_HDON": "INVOICE-0", "TONG_TIEN": 300}]
    banks = [{"MA_TCHUC": "BANK-1", "TEN_TCHUC": "Offline bank"}]
    outages = [owner | {"NOI_DUNG": "Offline planned work"}]
    session = Session(
        Reply([contract()]),
        config(region, BASES[region] + "/"),
        switched(person, access, region),
        Reply(points),
        Reply(monthly[0]),
        Reply(daily[0]),
        Reply(monthly_readings[0]),
        Reply(daily_readings[0]),
        Reply(monthly[1]),
        Reply(daily[1]),
        Reply(monthly_readings[1]),
        Reply(daily_readings[1]),
        Reply(contracts),
        Reply(invoices),
        Reply(paid),
        Reply(banks),
        Reply(outages),
    )
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    forged_display = api.Customer(
        person.code, person.management_unit, "Untrusted display", "Untrusted contract"
    )
    snapshot = await client.fetch_snapshot(forged_display)
    assert snapshot.customer == person
    assert snapshot.region == region
    assert snapshot.measurement_points == points
    assert snapshot.monthly == {"POINT-1": monthly[0], "POINT-2": monthly[1]}
    assert snapshot.daily == {"POINT-1": daily[0], "POINT-2": daily[1]}
    assert snapshot.monthly_readings == {
        "POINT-1": monthly_readings[0],
        "POINT-2": monthly_readings[1],
    }
    assert snapshot.daily_readings == {
        "POINT-1": daily_readings[0],
        "POINT-2": daily_readings[1],
    }
    assert snapshot.contracts == contracts
    assert snapshot.invoices == invoices
    assert snapshot.paid_invoices == paid
    assert snapshot.banks == banks
    assert snapshot.outages == outages
    assert snapshot.info == contract()
    assert snapshot.fetched_at == frozen
    assert snapshot.fetched_at.tzinfo is UTC
    assert changes == [
        api.TokenState(
            access, tokens.refresh_token, person.code, person.management_unit
        )
    ]
    assert session.calls[2]["url"] == api.CENTRAL_BASE + "/user/switch/" + person.code
    assert session.calls[2]["method"] == "GET"
    for index, point in ((4, "POINT-1"), (8, "POINT-2")):
        assert session.calls[index]["method"] == "POST"
        assert (
            session.calls[index]["url"]
            == BASES[region] + "/api/evn/tracuu/diennangthang"
        )
        assert session.calls[index]["json"] == {
            "MA_DVIQLY": person.management_unit,
            "MA_DDO": point,
            "MA_KHANG": person.code,
            "TU_THANG_NAM": "02/2025",
            "DEN_THANG_NAM": "01/2026",
        }
    for index, point in ((5, "POINT-1"), (9, "POINT-2")):
        assert session.calls[index]["json"] == {
            "MA_DVIQLY": person.management_unit,
            "MA_DDO": point,
            "TU_NGAY": "25/12/2025",
            "DEN_NGAY": "01/01/2026",
        }
        assert (
            session.calls[index]["url"]
            == BASES[region] + "/api/evn/tracuu/diennangngay"
        )
    for index, point in ((6, "POINT-1"), (10, "POINT-2")):
        assert session.calls[index]["method"] == "POST"
        assert (
            session.calls[index]["url"] == BASES[region] + "/api/evn/tracuu/chisothang"
        )
        assert session.calls[index]["json"] == {
            "MA_DVIQLY": person.management_unit,
            "MA_DDO": point,
            "MA_KHANG": person.code,
            "TU_THANG_NAM": "12/2024",
            "DEN_THANG_NAM": "01/2026",
        }
    for index, point in ((7, "POINT-1"), (11, "POINT-2")):
        assert (
            session.calls[index]["url"] == BASES[region] + "/api/evn/tracuu/chisongay"
        )
        assert session.calls[index]["json"] == {
            "MA_DVIQLY": person.management_unit,
            "MA_DDO": point,
            "TU_NGAY": "01/12/2025",
            "DEN_NGAY": "01/01/2026",
        }
    assert session.calls[3]["url"] == BASES[region] + "/api/evn/customers/diemdo"
    assert session.calls[3]["method"] == "GET"
    assert "json" not in session.calls[3]
    assert session.calls[12]["url"] == BASES[region] + "/api/evn/customers/info"
    assert session.calls[12]["method"] == "GET"
    assert session.calls[13]["method"] == "POST"
    assert session.calls[13]["url"] == BASES[region] + "/api/evn/tracuu/hoadon"
    assert "json" not in session.calls[13]
    assert session.calls[14]["url"] == BASES[region] + "/api/evn/tracuu/lichsu-hoadon"
    assert session.calls[14]["json"] == {
        "TU_THANG_NAM": "12/2024",
        "DEN_THANG_NAM": "01/2026",
    }
    assert (
        session.calls[15]["url"]
        == BASES[region] + "/api/evn/thanhtoan/danhsach-nganhang"
    )
    assert session.calls[15]["method"] == "GET"
    assert session.calls[16]["url"] == BASES[region] + "/api/evn/tracuu/ngungcapdien"
    assert session.calls[16]["json"] == {
        "TU_NGAY": "01/01/2026",
        "DEN_NGAY": "15/01/2026",
    }
    assert all(
        call["headers"]["Authorization"] == "Bearer " + access
        for call in session.calls[3:]
    )
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("frozen", "today", "monthly_start", "readings_start"),
    [
        (
            datetime(2025, 12, 31, 16, 59, tzinfo=UTC),
            date(2025, 12, 31),
            "01/2025",
            "11/2024",
        ),
        (
            datetime(2025, 12, 31, 17, 0, tzinfo=UTC),
            date(2026, 1, 1),
            "02/2025",
            "12/2024",
        ),
        (
            datetime(2026, 1, 31, 17, 0, tzinfo=UTC),
            date(2026, 2, 1),
            "03/2025",
            "01/2025",
        ),
        (
            datetime(2024, 2, 28, 17, 0, tzinfo=UTC),
            date(2024, 2, 29),
            "03/2023",
            "01/2023",
        ),
        (
            datetime(2024, 2, 29, 17, 0, tzinfo=UTC),
            date(2024, 3, 1),
            "04/2023",
            "02/2023",
        ),
    ],
)
async def test_snapshot_twelve_months_and_inclusive_days_across_rollovers(
    identity: dict[str, str],
    tokens: Any,
    monkeypatch: pytest.MonkeyPatch,
    frozen: datetime,
    today: date,
    monthly_start: str,
    readings_start: str,
) -> None:
    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Self:
            return cls.fromtimestamp(frozen.timestamp(), tz)

    monkeypatch.setattr(api, "datetime", Clock)
    person = customer()
    session = Session(
        Reply([contract()]),
        config(),
        *snapshot_replies(person, secrets.token_urlsafe(24)),
    )
    snapshot = await make_client(session, identity, tokens=tokens).fetch_snapshot(
        person
    )
    assert snapshot.fetched_at == frozen
    assert [call["url"] for call in session.calls[3:]] == [
        BASES["PB"] + path
        for path in (
            "/api/evn/customers/diemdo",
            "/api/evn/tracuu/diennangthang",
            "/api/evn/tracuu/diennangngay",
            "/api/evn/tracuu/chisothang",
            "/api/evn/tracuu/chisongay",
            "/api/evn/customers/info",
            "/api/evn/tracuu/hoadon",
            "/api/evn/tracuu/lichsu-hoadon",
            "/api/evn/thanhtoan/danhsach-nganhang",
            "/api/evn/tracuu/ngungcapdien",
        )
    ]
    monthly_body = session.calls[4]["json"]
    assert monthly_body == {
        "MA_DVIQLY": person.management_unit,
        "MA_DDO": "POINT-1",
        "MA_KHANG": person.code,
        "TU_THANG_NAM": monthly_start,
        "DEN_THANG_NAM": today.strftime("%m/%Y"),
    }
    first_month, first_year = map(int, monthly_body["TU_THANG_NAM"].split("/"))
    last_month, last_year = map(int, monthly_body["DEN_THANG_NAM"].split("/"))
    first = date(first_year, first_month, 1)
    last = date(last_year, last_month, 1)
    assert (last.year - first.year) * 12 + last.month - first.month + 1 == 12
    assert session.calls[6]["json"] == monthly_body | {"TU_THANG_NAM": readings_start}
    assert session.calls[10]["json"] == {
        "TU_THANG_NAM": readings_start,
        "DEN_THANG_NAM": today.strftime("%m/%Y"),
    }
    for index, days in ((5, 7), (7, 31)):
        assert session.calls[index]["json"] == {
            "MA_DVIQLY": person.management_unit,
            "MA_DDO": "POINT-1",
            "TU_NGAY": (today - timedelta(days=days)).strftime("%d/%m/%Y"),
            "DEN_NGAY": today.strftime("%d/%m/%Y"),
        }
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["current", "historical_only", "empty"])
async def test_snapshot_periods_are_only_fetched_endpoint_data(
    identity: dict[str, str],
    tokens: Any,
    monkeypatch: pytest.MonkeyPatch,
    response: str,
) -> None:
    frozen = datetime(2025, 12, 31, 17, 30, tzinfo=UTC)

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Self:
            return cls.fromtimestamp(frozen.timestamp(), tz)

    monkeypatch.setattr(api, "datetime", Clock)
    person = customer()
    owner = {
        "MA_KHANG": person.code,
        "MA_DVIQLY": person.management_unit,
        "MA_DDO": "POINT-1",
    }
    month_labels = [(2025, month) for month in range(2, 13)] + [(2026, 1)]
    if response != "current":
        month_labels = month_labels[:-1]
    days = [date(2025, 12, 30), date(2025, 12, 31)]
    if response == "current":
        days.append(date(2026, 1, 1))
    monthly = [
        owner | {"NAM": year, "THANG": month, "DIEN_TTHU": 50 + index}
        for index, (year, month) in enumerate(month_labels)
    ]
    daily = [
        owner
        | {
            "NGAY": day.strftime("%d/%m/%Y"),
            "NGAY_HTHI": day.strftime("%d/%m/%Y"),
            "BCS": "KT",
            "DIEN_TTHU": 2.5 + index,
        }
        for index, day in enumerate(days)
    ]
    invoices = (
        [owner | {"ID_HDON": "CURRENT", "NAM": 2026, "THANG": 1, "TONG_TIEN": 123}]
        if response == "current"
        else []
    )
    paid = [
        owner
        | {
            "ID_HDON": f"PREVIOUS-{month}",
            "NAM": 2025,
            "THANG": month,
            "TONG_TIEN": 100 + month,
        }
        for month in (11, 12)
    ]
    if response == "empty":
        monthly, daily, paid = [], [], []
    monthly_readings = [
        owner | {"NAM": 2026, "THANG": 1, "CHISO_CU": 100, "CHISO_MOI": 999}
    ]
    daily_readings = [owner | {"NGAY": "01/01/2026", "CHISO_CU": 100, "CHISO_MOI": 999}]
    replies = snapshot_replies(person, secrets.token_urlsafe(24))
    replies[2:6] = [
        Reply(monthly),
        Reply(daily),
        Reply(monthly_readings),
        Reply(daily_readings),
    ]
    replies[7:9] = [Reply(invoices), Reply(paid)]
    session = Session(Reply([contract()]), config(), *replies)
    snapshot = await make_client(session, identity, tokens=tokens).fetch_snapshot(
        person
    )
    assert snapshot.monthly == {"POINT-1": monthly}
    assert snapshot.daily == {"POINT-1": daily}
    assert snapshot.monthly_readings == {"POINT-1": monthly_readings}
    assert snapshot.daily_readings == {"POINT-1": daily_readings}
    assert snapshot.invoices == invoices
    assert snapshot.paid_invoices == paid
    assert session.calls[4]["json"]["TU_THANG_NAM"] == "02/2025"
    assert session.calls[4]["json"]["DEN_THANG_NAM"] == "01/2026"
    assert session.calls[5]["json"]["DEN_NGAY"] == "01/01/2026"
    if response == "current":
        assert len(snapshot.monthly["POINT-1"]) == 12
        assert snapshot.monthly["POINT-1"][-1]["DIEN_TTHU"] == 61
        assert snapshot.daily["POINT-1"][-1]["DIEN_TTHU"] == 4.5
    else:
        assert not any(row["NAM"] == 2026 for row in snapshot.monthly["POINT-1"])
        assert not any(row["NGAY"] == "01/01/2026" for row in snapshot.daily["POINT-1"])
        assert snapshot.invoices == []
    session.done()


@pytest.mark.asyncio
async def test_empty_measurement_points_are_valid(
    identity: dict[str, str], tokens: Any
) -> None:
    session = Session(
        Reply([contract()]),
        config(),
        switched(customer(), secrets.token_urlsafe(24)),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
    )
    snapshot = await make_client(session, identity, tokens=tokens).fetch_snapshot(
        customer()
    )
    assert snapshot.measurement_points == snapshot.invoices == snapshot.outages == []
    assert snapshot.monthly == snapshot.daily == {}
    assert snapshot.monthly_readings == snapshot.daily_readings == {}
    assert snapshot.contracts == snapshot.paid_invoices == snapshot.banks == []
    assert snapshot.info == contract()
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "candidate", [customer(2), api.Customer(customer().code, "OTHER-UNIT"), None]
)
async def test_unknown_customer_is_never_selected(
    identity: dict[str, str], tokens: Any, candidate: Any
) -> None:
    session = Session(Reply([contract()]))
    with pytest.raises(api.EvnAuthError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(candidate)
    assert paths(session) == ["/user/me"]
    session.done()


@pytest.mark.asyncio
async def test_switch_customer_code_is_urlencoded(
    identity: dict[str, str], tokens: Any
) -> None:
    row = contract() | {"maKhang": "TEST /?&#% ü"}
    person = api.Customer(row["maKhang"], row["maDviqly"])
    session = Session(
        Reply([row]),
        config(),
        switched(person, secrets.token_urlsafe(24)),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
    )
    await make_client(session, identity, tokens=tokens).fetch_snapshot(person)
    assert session.calls[2]["url"] == api.CENTRAL_BASE + "/user/switch/" + quote(
        person.code, safe=""
    )
    assert "?" not in session.calls[2]["url"]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", [1, 2, 3, 4, 5])
@pytest.mark.parametrize(
    "bad_rows",
    [
        None,
        {},
        [None],
        [{"MA_KHANG": "OTHER"}],
        [{"MA_DVIQLY": "OTHER"}],
        [{"MA_KHANG": None}],
        [{"MA_DVIQLY": 1}],
    ],
)
async def test_cross_customer_data_or_schema_fails_entire_snapshot(
    identity: dict[str, str], tokens: Any, stage: int, bad_rows: Any
) -> None:
    replies = snapshot_replies(customer(), secrets.token_urlsafe(24))
    replies[stage] = Reply(bad_rows)
    session = Session(Reply([contract()]), config(), *replies[: stage + 1])
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(customer())
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stage", "rows"),
    [
        (1, [{}]),
        (1, [{"MA_DDO": 1}]),
        (1, [{"MA_DDO": ""}]),
        (1, [{"MA_DDO": "POINT-1"}, {"MA_DDO": "POINT-1"}]),
        (2, [{"MA_DDO": "OTHER-POINT"}]),
        (3, [{"MA_DDO": "OTHER-POINT"}]),
        (2, [{"MA_DDO": None}]),
        (3, [{"MA_DDO": 1}]),
    ],
)
async def test_measurement_point_mismatches_fail(
    identity: dict[str, str], tokens: Any, stage: int, rows: Any
) -> None:
    replies = snapshot_replies(customer(), secrets.token_urlsafe(24))
    replies[stage] = Reply(rows)
    session = Session(Reply([contract()]), config(), *replies[: stage + 1])
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(customer())
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", [1, 2, 3, 4, 5])
async def test_any_regional_failure_aborts_snapshot(
    identity: dict[str, str], tokens: Any, stage: int
) -> None:
    replies = snapshot_replies(customer(), secrets.token_urlsafe(24))
    replies[stage] = Reply(status=503)
    session = Session(Reply([contract()]), config(), *replies[: stage + 1])
    with pytest.raises(api.EvnConnectionError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(customer())
    session.done()


@pytest.mark.asyncio
async def test_regional_redirect_aborts_snapshot(
    identity: dict[str, str], tokens: Any
) -> None:
    session = Session(
        Reply([contract()]),
        config(),
        switched(customer(), secrets.token_urlsafe(24)),
        Reply(status=302),
    )
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(customer())
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("previous_context", [False, True])
@pytest.mark.parametrize("refresh_mode", ["missing", "null", "empty"])
async def test_switch_401_refresh_uses_previous_context_then_rotates(
    identity: dict[str, str], tokens: Any, previous_context: bool, refresh_mode: str
) -> None:
    previous = customer() if previous_context else None
    target = customer(2)
    old = api.TokenState(
        tokens.access_token,
        tokens.refresh_token,
        previous.code if previous else None,
        previous.management_unit if previous else None,
    )
    refreshed = secrets.token_urlsafe(24)
    rotated = secrets.token_urlsafe(24)
    selected = secrets.token_urlsafe(24)
    regional_access = secrets.token_urlsafe(24)
    regional_refresh_data: dict[str, Any] = {"accessToken": regional_access}
    if refresh_mode != "missing":
        regional_refresh_data["refreshToken"] = None if refresh_mode == "null" else ""
    session = Session(
        Reply([contract(), contract(2)]),
        config(),
        Reply(status=401),
        Reply({"accessToken": refreshed, "refreshToken": rotated}),
        switched(target, selected),
        Reply(status=401),
        Reply(regional_refresh_data),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
    )
    changes: list[Any] = []
    callback_positions: list[int] = []

    def changed(state: Any) -> None:
        assert client.tokens is state
        changes.append(state)
        callback_positions.append(len(session.calls))

    client = make_client(session, identity, tokens=old, on_tokens=changed)
    snapshot = await client.fetch_snapshot(target)
    assert snapshot.customer == target
    assert session.calls[3]["json"] == {
        "refreshToken": old.refresh_token,
        "maKhachhang": old.customer_code,
        "donviquanly": old.management_unit,
    }
    assert session.calls[4]["headers"]["Authorization"] == "Bearer " + refreshed
    assert session.calls[6]["json"] == {
        "refreshToken": rotated,
        "maKhachhang": target.code,
        "donviquanly": target.management_unit,
    }
    assert session.calls[7]["headers"]["Authorization"] == "Bearer " + regional_access
    assert changes == [
        api.TokenState(refreshed, rotated, old.customer_code, old.management_unit),
        api.TokenState(selected, rotated, target.code, target.management_unit),
        api.TokenState(regional_access, rotated, target.code, target.management_unit),
    ]
    assert callback_positions == [4, 5, 7]
    session.done()


@pytest.mark.asyncio
async def test_multiple_snapshots_are_isolated_with_initial_login(
    identity: dict[str, str], tokens: Any
) -> None:
    first, second = customer(), customer(2)
    first_access, second_access = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    session = Session(
        Reply({}),
        Reply(
            {"accessToken": tokens.access_token, "refreshToken": tokens.refresh_token}
        ),
        Reply([contract(), contract(2)]),
        config(),
        *snapshot_replies(first, first_access),
        *snapshot_replies(second, second_access),
    )
    changes: list[Any] = []
    positions: list[int] = []

    def changed(state: Any) -> None:
        assert client.tokens is state
        changes.append(state)
        positions.append(len(session.calls))

    client = make_client(session, identity, on_tokens=changed)
    result1, result2, linked = await asyncio.gather(
        client.fetch_snapshot(first), client.fetch_snapshot(second), client.customers()
    )
    assert linked == [first, second]
    assert result1.monthly["POINT-1"][0]["MA_KHANG"] == first.code
    assert result2.monthly["POINT-1"][0]["MA_KHANG"] == second.code
    assert result1.invoices[0]["MA_KHANG"] == first.code
    assert result2.invoices[0]["MA_KHANG"] == second.code
    assert positions == [2, 5, 16]
    assert changes == [
        tokens,
        api.TokenState(
            first_access, tokens.refresh_token, first.code, first.management_unit
        ),
        api.TokenState(
            second_access, tokens.refresh_token, second.code, second.management_unit
        ),
    ]
    assert (
        session.calls[4]["headers"]["Authorization"] == "Bearer " + tokens.access_token
    )
    assert all(
        call["headers"]["Authorization"] == "Bearer " + first_access
        for call in session.calls[5:15]
    )
    assert session.calls[15]["headers"]["Authorization"] == "Bearer " + first_access
    assert all(
        call["headers"]["Authorization"] == "Bearer " + second_access
        for call in session.calls[16:]
    )
    assert paths(session).count("/public/allconfig") == 1
    assert paths(session).count("/user/me") == 1
    session.done()


@pytest.mark.asyncio
async def test_explicit_login_waits_for_snapshot(
    identity: dict[str, str], tokens: Any
) -> None:
    person = customer()
    selected, logged_in, refresh = (secrets.token_urlsafe(24) for _ in range(3))
    session = Session(
        Reply([contract()]),
        config(),
        *snapshot_replies(person, selected),
        Reply({}),
        Reply({"accessToken": logged_in, "refreshToken": refresh}),
        Reply([]),
    )
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    snapshot, _ = await asyncio.gather(client.fetch_snapshot(person), client.login())
    assert snapshot.customer == person
    assert paths(session)[-2:] == ["/auth/checkAccInUse", "/auth/login"]
    assert await client.customers() == []
    assert changes == [
        api.TokenState(
            selected, tokens.refresh_token, person.code, person.management_unit
        ),
        api.TokenState(logged_in, refresh),
    ]
    session.done()


@pytest.mark.asyncio
async def test_callback_failure_keeps_rotation_and_is_redacted(
    identity: dict[str, str], tokens: Any
) -> None:
    access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    session = Session(
        Reply(status=401),
        Reply({"accessToken": access, "refreshToken": refresh}),
        Reply([]),
    )

    def changed(state: Any) -> None:
        assert client.tokens is state
        raise RuntimeError(identity["password"] + access + refresh)

    client = make_client(session, identity, tokens=tokens, on_tokens=changed)
    with pytest.raises(api.EvnError) as caught:
        await client.customers()
    assert client.tokens == api.TokenState(access, refresh)
    formatted = "".join(traceback.format_exception(caught.value))
    for private in (identity["password"], access, refresh):
        assert private not in formatted
    assert await client.customers() == []
    assert session.calls[-1]["headers"]["Authorization"] == "Bearer " + access
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [401, 403, "rejected", "missing_token"])
async def test_failed_login_latches_without_storm(
    identity: dict[str, str], failure: int | str
) -> None:
    if isinstance(failure, int):
        reply = Reply(status=failure)
    elif failure == "rejected":
        reply = Reply(
            payload={"success": False, "message": identity["password"]}, status=400
        )
    else:
        reply = Reply({})
    session = Session(Reply({}), reply)
    client = make_client(session, identity)
    results = await asyncio.gather(
        *(client.customers() for _ in range(4)), return_exceptions=True
    )
    assert all(isinstance(result, api.EvnAuthError) for result in results)
    assert paths(session) == ["/auth/checkAccInUse", "/auth/login"]
    assert client.tokens is None
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [None, customer().code])
@pytest.mark.parametrize("unit", [None, customer().management_unit])
async def test_optional_token_context_fields(
    identity: dict[str, str], tokens: Any, code: str | None, unit: str | None
) -> None:
    original = api.TokenState(tokens.access_token, tokens.refresh_token, code, unit)
    assert api.TokenState.from_dict(original.to_dict()) == original
    access = secrets.token_urlsafe(24)
    session = Session(Reply(status=401), Reply({"accessToken": access}), Reply([]))
    client = make_client(session, identity, tokens=original)
    assert await client.customers() == []
    assert session.calls[1]["json"] == {
        "refreshToken": original.refresh_token,
        "maKhachhang": code,
        "donviquanly": unit,
    }
    assert client.tokens == api.TokenState(access, original.refresh_token, code, unit)
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["lookup", "login", "switch", "refresh"])
async def test_callback_failure_stops_followup_requests(
    identity: dict[str, str], tokens: Any, state: str
) -> None:
    access = secrets.token_urlsafe(24)
    if state in ("lookup", "login"):
        session = Session(
            Reply({}),
            Reply({"accessToken": access, "refreshToken": tokens.refresh_token}),
        )
        initial = None
    elif state == "switch":
        session = Session(Reply([contract()]), config(), switched(customer(), access))
        initial = tokens
    else:
        session = Session(Reply(status=401), Reply({"accessToken": access}))
        initial = tokens

    def changed(current: Any) -> None:
        assert client.tokens is current
        raise ValueError(identity["password"])

    client = make_client(session, identity, tokens=initial, on_tokens=changed)
    with pytest.raises(api.EvnError) as caught:
        if state == "lookup":
            await client.customers()
        elif state == "login":
            await client.login()
        elif state == "switch":
            await client.fetch_snapshot(customer())
        else:
            await client.customers()
    assert str(caught.value) == "EVN operation failed."
    assert caught.value.__context__ is None or caught.value.__suppress_context__
    assert client.tokens.access_token == access
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["login", "lookup"])
async def test_malformed_authentication_does_not_storm(
    identity: dict[str, str], failure: str
) -> None:
    session = Session(
        *([Reply({})] if failure == "login" else []), Reply(raw=b"invalid")
    )
    client = make_client(session, identity)
    with pytest.raises(api.EvnResponseError):
        await client.customers()
    with pytest.raises(api.EvnAuthError):
        await client.customers()
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context",
    [
        None,
        [],
        {},
        {"maDviCaptct": None},
        {"maDviCaptct": "PB", "maKhang": "OTHER"},
        {"maDviCaptct": "PB", "maDviqly": "OTHER"},
    ],
)
async def test_invalid_switch_context_never_reaches_region(
    identity: dict[str, str], tokens: Any, context: Any
) -> None:
    session = Session(
        Reply([contract()]),
        config(),
        Reply({"accessToken": secrets.token_urlsafe(24), "data": context}),
    )
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    with pytest.raises(api.EvnResponseError):
        await client.fetch_snapshot(customer())
    assert not changes
    assert client.tokens is tokens
    session.done()


@pytest.mark.asyncio
async def test_missing_regional_config_does_not_guess_base(
    identity: dict[str, str], tokens: Any
) -> None:
    access = secrets.token_urlsafe(24)
    session = Session(Reply([contract()]), Reply([]), switched(customer(), access))
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    with pytest.raises(api.EvnResponseError):
        await client.fetch_snapshot(customer())
    assert len(changes) == 1
    assert changes[0] is client.tokens
    assert client.tokens.access_token == access
    session.done()


@pytest.mark.asyncio
async def test_minimal_customer_and_switch_payloads(
    identity: dict[str, str], tokens: Any
) -> None:
    person = api.Customer(customer().code, customer().management_unit)
    access = secrets.token_urlsafe(24)
    session = Session(
        Reply([{"maKhang": person.code, "maDviqly": person.management_unit}]),
        config(),
        Reply({"accessToken": access, "data": {"maDviCaptct": "PB"}}),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply([]),
    )
    client = make_client(session, identity, tokens=tokens)
    assert await client.customers() == [person]
    assert (await client.fetch_snapshot(person)).customer == person
    session.done()


@pytest.mark.asyncio
async def test_session_error_is_generic_and_preserves_tokens(
    identity: dict[str, str], tokens: Any
) -> None:
    session = Session(Reply(error=RuntimeError(identity["password"])))
    client = make_client(session, identity, tokens=tokens)
    with pytest.raises(api.EvnConnectionError) as caught:
        await client.customers()
    assert identity["password"] not in "".join(traceback.format_exception(caught.value))
    assert client.tokens is tokens
    session.done()


@pytest.mark.asyncio
async def test_explicit_login_recovers_from_rejected_refresh(
    identity: dict[str, str], tokens: Any
) -> None:
    access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    session = Session(
        Reply(status=401),
        Reply(status=401),
        Reply({}),
        Reply({"accessToken": access, "refreshToken": refresh}),
        Reply([]),
    )
    client = make_client(session, identity, tokens=tokens)
    with pytest.raises(api.EvnAuthError):
        await client.customers()
    await client.login()
    assert await client.customers() == []
    assert client.tokens == api.TokenState(access, refresh)
    session.done()


@pytest.mark.asyncio
async def test_username_and_password_special_characters_are_unchanged(
    identity: dict[str, str], tokens: Any
) -> None:
    special = identity | {"username": identity["username"] + " +&%@/ ữ "}
    session = Session(
        Reply({}),
        Reply(
            {"accessToken": tokens.access_token, "refreshToken": tokens.refresh_token}
        ),
    )
    await make_client(session, special).login()
    assert session.calls[0]["json"] == {"phone": special["username"]}
    assert session.calls[1]["json"]["username"] == special["username"]
    assert session.calls[1]["json"]["password"] == special["password"]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("canonical_username", [_MISSING, None, ""])
async def test_empty_canonical_username_uses_original(
    identity: dict[str, str], tokens: Any, canonical_username: Any
) -> None:
    original = identity | {"username": identity["username"] + "+%@/&ữ"}
    account = {} if canonical_username is _MISSING else {"username": canonical_username}
    session = Session(
        Reply(account),
        Reply(
            {"accessToken": tokens.access_token, "refreshToken": tokens.refresh_token}
        ),
    )
    changes: list[Any] = []

    def changed(state: Any) -> None:
        assert client.tokens is state
        assert len(session.calls) == 2
        changes.append(state)

    client = make_client(session, original, on_tokens=changed)
    await client.login()
    assert session.calls[0]["json"] == {"phone": original["username"]}
    assert session.calls[1]["json"] == {
        "username": original["username"],
        "password": original["password"],
        "deviceInfo": {
            "deviceId": original["device_id"],
            "deviceType": "Home Assistant",
        },
    }
    assert changes == [tokens]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("default_pass", [True, False, None, "unsupported", 0, [], {}])
async def test_unknown_default_pass_setting_is_ignored(
    identity: dict[str, str], tokens: Any, default_pass: Any
) -> None:
    canonical = "canonical-" + secrets.token_hex(8)
    session = Session(
        Reply({"username": canonical, "defaultPass": default_pass}),
        Reply(
            {"accessToken": tokens.access_token, "refreshToken": tokens.refresh_token}
        ),
    )
    changes: list[Any] = []
    client = make_client(session, identity, on_tokens=changes.append)
    await client.login()
    assert session.calls[1]["json"]["username"] == canonical
    assert changes == [tokens]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "refresh_token",
    [
        False,
        True,
        0,
        1,
        [],
        {},
        ["invalid"],
        {"token": "invalid"},
        " ",
        "invalid space",
        "invalid\r\nheader",
        "ữ",
    ],
)
async def test_malformed_refresh_token_is_not_a_fallback(
    identity: dict[str, str], tokens: Any, refresh_token: Any
) -> None:
    original = api.TokenState(
        tokens.access_token,
        tokens.refresh_token,
        customer().code,
        customer().management_unit,
    )
    session = Session(
        Reply(status=401),
        Reply(
            {"accessToken": secrets.token_urlsafe(24), "refreshToken": refresh_token}
        ),
    )
    changes: list[Any] = []
    client = make_client(session, identity, tokens=original, on_tokens=changes.append)
    with pytest.raises(api.EvnAuthError):
        await client.customers()
    with pytest.raises(api.EvnAuthError):
        await client.customers()
    assert client.tokens is original
    assert not changes
    assert paths(session) == ["/user/me", "/auth/refresh"]
    assert session.calls[1]["json"] == {
        "refreshToken": original.refresh_token,
        "maKhachhang": original.customer_code,
        "donviquanly": original.management_unit,
    }
    session.done()


@pytest.mark.asyncio
async def test_aiohttp_request_wire_headers_and_bodies(
    identity: dict[str, str], tokens: Any
) -> None:
    person = customer()
    session = Session(
        Reply([contract()]),
        config(),
        *snapshot_replies(person, secrets.token_urlsafe(24)),
    )
    client = make_client(session, identity, tokens=tokens)
    await client.fetch_snapshot(person)
    session.done()
    saw_bodyless_post = False
    saw_json_post = False

    async def wire_bytes(call: dict[str, Any], skip_content_type: bool = True) -> bytes:
        transport = Mock(spec=asyncio.Transport)
        transport.is_closing.return_value = False
        protocol = ResponseHandler(asyncio.get_running_loop())
        protocol.transport = transport
        connection = SimpleNamespace(
            protocol=protocol,
            _connector=SimpleNamespace(force_close=False),
        )
        request = ClientRequest(
            call["method"],
            URL(call["url"]),
            headers=call["headers"],
            skip_auto_headers=call.get("skip_auto_headers")
            if skip_content_type
            else None,
            data=JsonPayload(call["json"]) if "json" in call else None,
            loop=asyncio.get_running_loop(),
        )
        response = await request.send(cast(Any, connection))
        await request.close()
        response.close()
        chunks: list[bytes] = []
        for operation in transport.method_calls:
            if operation[0] == "write":
                chunks.append(bytes(operation[1][0]))
            elif operation[0] == "writelines":
                chunks.extend(bytes(chunk) for chunk in operation[1][0])
        return b"".join(chunks)

    for call in session.calls:
        serialized = await wire_bytes(call)
        header_bytes, body_bytes = serialized.split(b"\r\n\r\n", 1)
        headers = {
            name.lower(): value.strip()
            for line in header_bytes.split(b"\r\n")[1:]
            for name, value in [line.split(b":", 1)]
        }
        if "json" in call:
            assert call.get("skip_auto_headers") is None
            assert headers[b"content-type"] == b"application/json"
            assert json.loads(body_bytes) == call["json"]
            saw_json_post = saw_json_post or call["method"] == "POST"
        else:
            assert call["skip_auto_headers"] == {"Content-Type"}
            assert "data" not in call
            assert b"content-type" not in headers
            assert body_bytes == b""
            if call["method"] == "POST":
                saw_bodyless_post = True
                assert headers[b"content-length"] == b"0"
                assert call["url"].endswith("/api/evn/tracuu/hoadon")
                baseline_headers, baseline_body = (await wire_bytes(call, False)).split(
                    b"\r\n\r\n", 1
                )
                assert b"Content-Type: application/octet-stream" in baseline_headers
                assert baseline_body == b""
    assert saw_bodyless_post and saw_json_post


@pytest.mark.asyncio
async def test_valid_snapshot_consumption_model_roundtrip(
    identity: dict[str, str], tokens: Any
) -> None:
    spec = importlib.util.spec_from_file_location(
        "_evn_cskh_models_api_offline",
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "evn_cskh"
        / "models.py",
    )
    assert spec is not None and spec.loader is not None
    models = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = models
    spec.loader.exec_module(models)
    person = customer()
    monthly: list[dict[str, Any]] = [
        {
            "NAM": 2026,
            "THANG": 9,
            "KY": 1,
            "SO_KY": 1,
            "SO_CTO": "METER-A",
            "DIEN_TTHU": "100.0",
        },
        {
            "NAM": 2026,
            "THANG": 10,
            "KY": 1,
            "SO_KY": 2,
            "SO_CTO": "METER-A",
            "DIEN_TTHU": "12.5",
        },
        {
            "NAM": 2026,
            "THANG": 10,
            "KY": 2,
            "SO_KY": 2,
            "SO_CTO": "METER-A",
            "DIEN_TTHU": "7.5",
        },
    ]
    daily: list[dict[str, Any]] = [
        {
            "NGAY": "05/10/2026",
            "NGAY_HTHI": "05/10/2026",
            "SO_CTO": "METER-A",
            "BCS": "KT",
            "DIEN_TTHU": 5,
        },
        {
            "NGAY": "06/10/2026",
            "NGAY_HTHI": "06/10/2026",
            "SO_CTO": "METER-A",
            "BCS": "BT",
            "DIEN_TTHU": "1.25",
        },
        {
            "NGAY": "06/10/2026",
            "NGAY_HTHI": "06/10/2026",
            "SO_CTO": "METER-A",
            "BCS": "CD",
            "DIEN_TTHU": "2.5",
        },
        {
            "NGAY": "06/10/2026",
            "NGAY_HTHI": "06/10/2026",
            "SO_CTO": "METER-A",
            "BCS": "TD",
            "DIEN_TTHU": "0.25",
        },
    ]
    ownership = {"MA_KHANG": person.code, "MA_DVIQLY": person.management_unit}
    invoices = [
        ownership
        | {
            "ID_HDON": "INVOICE-A",
            "TTRANG_TTOAN": "CHUATT",
            "LOAI_PSINH": "PS",
            "TONG_NO": "125000",
        },
        ownership
        | {
            "ID_HDON": "INVOICE-B",
            "TTRANG_TTOAN": "DATT",
            "LOAI_PSINH": "PS",
            "TONG_NO": "50000",
        },
    ]
    session = Session(
        Reply([contract()]),
        config(),
        switched(person, secrets.token_urlsafe(24)),
        Reply([ownership | {"MA_DDO": "POINT-1", "SO_CTO": "METER-A"}]),
        Reply(monthly),
        Reply(daily),
        Reply([]),
        Reply([]),
        Reply([]),
        Reply(invoices),
        Reply([]),
        Reply([]),
        Reply([]),
    )
    snapshot = await make_client(session, identity, tokens=tokens).fetch_snapshot(
        person
    )
    assert snapshot.monthly["POINT-1"] == monthly
    assert snapshot.daily["POINT-1"] == daily
    assert all("MA_DDO" not in row for row in monthly + daily)
    assert models.monthly_summary(snapshot.monthly["POINT-1"]) == models.PeriodUsage(
        20.0, "2026-10"
    )
    assert models.daily_summary(snapshot.daily["POINT-1"]) == models.PeriodUsage(
        4.0, "06/10/2026"
    )
    assert models.invoice_summary(snapshot.invoices) == models.InvoiceSummary(
        125000.0, 1
    )
    session.done()


@pytest.mark.asyncio
async def test_mixed_invoice_ownership_is_not_discarded(
    identity: dict[str, str], tokens: Any
) -> None:
    person = customer()
    invoices = [
        {"MA_KHANG": person.code, "MA_DVIQLY": person.management_unit},
        {"MA_KHANG": customer(2).code, "MA_DVIQLY": customer(2).management_unit},
    ]
    replies = snapshot_replies(person, secrets.token_urlsafe(24))
    replies[7] = Reply(invoices)
    session = Session(Reply([contract()]), config(), *replies[:8])
    with pytest.raises(api.EvnResponseError):
        await make_client(session, identity, tokens=tokens).fetch_snapshot(person)
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize(
    ("method", "path", "auth_response"),
    [
        ("GET", "/auth/checkAccInUse", True),
        ("POST", "/auth/checkAccInUse", False),
        ("POST", "/auth/checkAccInUse/", True),
        ("POST", "/auth/login", True),
        ("POST", "/auth/refresh", True),
        ("GET", "/user/me", False),
        ("GET", "/public/allconfig", False),
    ],
)
async def test_missing_data_lookup_exception_is_narrow(
    identity: dict[str, str],
    status: int,
    method: str,
    path: str,
    auth_response: bool,
) -> None:
    session = Session(Reply(payload={"success": True}, status=status))
    client = make_client(session, identity)
    with pytest.raises(api.EvnResponseError):
        await client._send(method, api.CENTRAL_BASE + path, auth_response=auth_response)
    assert client.tokens is None
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 400])
@pytest.mark.parametrize("stage", ["customers", "login", "refresh"])
async def test_missing_data_elsewhere_does_not_create_session(
    identity: dict[str, str], tokens: Any, status: int, stage: str
) -> None:
    prefix = (
        [Reply({})]
        if stage == "login"
        else [Reply(status=401)]
        if stage == "refresh"
        else []
    )
    session = Session(*prefix, Reply(payload={"success": True}, status=status))
    initial = None if stage == "login" else tokens
    changes: list[Any] = []
    client = make_client(session, identity, tokens=initial, on_tokens=changes.append)
    expected_error = api.EvnAuthError if stage == "refresh" else api.EvnResponseError
    with pytest.raises(expected_error):
        if stage == "login":
            await client.login()
        else:
            await client.customers()
    if stage != "customers":
        for _ in range(3):
            with pytest.raises(api.EvnAuthError):
                await client.customers()
    assert client.tokens is initial
    assert not changes
    assert (
        paths(session)
        == {
            "customers": ["/user/me"],
            "login": ["/auth/checkAccInUse", "/auth/login"],
            "refresh": ["/user/me", "/auth/refresh"],
        }[stage]
    )
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["lookup", "login", "refresh"])
@pytest.mark.parametrize("data_mode", ["missing", "null", "message"])
async def test_auth_417_failure_is_redacted_and_latched(
    identity: dict[str, str], tokens: Any, stage: str, data_mode: str
) -> None:
    secret = "synthetic-fake-secret-" + secrets.token_hex(16)
    message = secret + identity["password"] + tokens.access_token + api.CENTRAL_BASE
    payload = {
        "success": False,
        "timestamp": "2026-10-07T00:00:00Z",
        "message": message,
    }
    if data_mode != "missing":
        payload["data"] = None if data_mode == "null" else message
    prefix = (
        [Reply({"username": identity["username"], "defaultPass": True})]
        if stage == "login"
        else [Reply(status=401)]
        if stage == "refresh"
        else []
    )
    rejection = Reply(payload=payload, status=417)
    session = Session(*prefix, rejection)
    initial = tokens if stage == "refresh" else None
    changes: list[Any] = []
    client = make_client(session, identity, tokens=initial, on_tokens=changes.append)
    with pytest.raises(api.EvnAuthError) as caught:
        if stage == "refresh":
            await client.customers()
        else:
            await client.login()
    assert type(caught.value) is api.EvnAuthError
    assert str(caught.value) == "EVN authentication failed."
    formatted = "".join(traceback.format_exception(caught.value))
    for private in (
        secret,
        identity["password"],
        tokens.access_token,
        api.CENTRAL_BASE,
    ):
        assert private not in str(caught.value)
        assert private not in formatted
    for _ in range(3):
        with pytest.raises(api.EvnAuthError):
            await client.customers()
        with pytest.raises(api.EvnAuthError):
            await client.fetch_snapshot(customer())
    assert rejection.consumed == len(rejection.raw)
    assert rejection.exited
    assert client.tokens is initial
    assert not changes
    assert (
        paths(session)
        == {
            "lookup": ["/auth/checkAccInUse"],
            "login": ["/auth/checkAccInUse", "/auth/login"],
            "refresh": ["/user/me", "/auth/refresh"],
        }[stage]
    )
    if stage == "login":
        assert session.calls[1]["json"] == {
            "username": identity["username"],
            "password": identity["password"],
            "deviceInfo": {
                "deviceId": identity["device_id"],
                "deviceType": "Home Assistant",
            },
        }
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["lookup", "login"])
@pytest.mark.parametrize("success", [_MISSING, True, None, "false", "true", 0, 1])
async def test_auth_417_cannot_accept_success_or_malformed_envelope(
    identity: dict[str, str], tokens: Any, stage: str, success: Any
) -> None:
    payload = {
        "data": {
            "accessToken": tokens.access_token,
            "refreshToken": tokens.refresh_token,
        }
    }
    if success is not _MISSING:
        payload["success"] = success
    session = Session(
        *([Reply({})] if stage == "login" else []),
        Reply(payload=payload, status=417),
    )
    changes: list[Any] = []
    client = make_client(session, identity, on_tokens=changes.append)
    with pytest.raises(api.EvnResponseError):
        await client.login()
    for _ in range(3):
        with pytest.raises(api.EvnAuthError):
            await client.customers()
    assert client.tokens is None
    assert not changes
    assert paths(session) == ["/auth/checkAccInUse"] + (
        ["/auth/login"] if stage == "login" else []
    )
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [b"", b"not JSON", b"\xff", b"[]", b"null"])
async def test_auth_417_invalid_json_is_response_error(
    identity: dict[str, str], raw: bytes
) -> None:
    session = Session(Reply({}), Reply(status=417, raw=raw))
    client = make_client(session, identity)
    with pytest.raises(api.EvnResponseError):
        await client.login()
    with pytest.raises(api.EvnAuthError):
        await client.customers()
    assert client.tokens is None
    assert paths(session) == ["/auth/checkAccInUse", "/auth/login"]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("success", [True, False, None])
async def test_non_auth_417_remains_response_error(
    identity: dict[str, str], tokens: Any, success: Any
) -> None:
    rejection = Reply(status=417, payload={"success": success, "data": []})
    session = Session(rejection)
    changes: list[Any] = []
    client = make_client(session, identity, tokens=tokens, on_tokens=changes.append)
    with pytest.raises(api.EvnResponseError):
        await client.customers()
    assert rejection.consumed == 0
    assert client.tokens is tokens
    assert not changes
    assert paths(session) == ["/user/me"]
    session.done()


@pytest.mark.asyncio
@pytest.mark.parametrize("content_length", [None, api._MAX_RESPONSE_BYTES + 1])
async def test_auth_417_response_size_is_bounded(
    identity: dict[str, str], content_length: int | None
) -> None:
    rejection = Reply(
        status=417,
        raw=b" " * (api._MAX_RESPONSE_BYTES + 131072),
        content_length=content_length,
    )
    session = Session(Reply({}), rejection)
    client = make_client(session, identity)
    with pytest.raises(api.EvnResponseError):
        await client.login()
    with pytest.raises(api.EvnAuthError):
        await client.customers()
    assert rejection.consumed <= api._MAX_RESPONSE_BYTES + 65536
    assert rejection.consumed < len(rejection.raw)
    assert rejection.exited
    assert client.tokens is None
    session.done()
