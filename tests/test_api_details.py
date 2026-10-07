from __future__ import annotations

import asyncio
import base64
import json
import traceback
from collections.abc import AsyncIterator
from copy import deepcopy
from dataclasses import fields
from datetime import UTC, date, datetime, timedelta
from typing import Any, Self, cast

import pytest
from aiohttp import ClientRequest, ClientSession, ClientTimeout
from aiohttp.payload import JsonPayload
from yarl import URL

from custom_components.evn_cskh import api

MISSING = object()
NOW = datetime(2025, 12, 31, 17, 30, tzinfo=UTC)
TODAY = date(2026, 1, 1)
START = date(2025, 11, 10)
POINT = "OFFLINE-POINT-A"
PERSON = api.Customer("OFFLINE-CUSTOMER-A", "OFFLINE-UNIT-A", "Synthetic name A")
OTHER = api.Customer("OFFLINE-CUSTOMER-B", "OFFLINE-UNIT-B", "Synthetic name B")
TOKENS = api.TokenState("offline-access", "offline-refresh")
BASES = {
    "PA": "https://apicskhevn.npc.com.vn/offline-prefix",
    "PB": "https://api.cskh.evnspc.vn/api-cskh-evn",
    "PC": "https://cskh-api.cpc.vn/offline-prefix",
    "HN": "https://gwkong.evnhanoi.vn/offline-prefix",
    "PE": "https://openapi.evnhcmc.vn/evn-ttcskh/appcskh",
}
DATA_PATHS = [
    "/api/evn/tracuu/diennangthang",
    "/api/evn/tracuu/diennangngay",
    "/api/evn/tracuu/chisothang",
    "/api/evn/tracuu/chisongay",
    "/api/evn/tracuu/lichsu-hoadon",
    "/api/evn/tracuu/hoadon",
]
PDF_PATHS = {
    "invoice": "/api/evn/tracuu/file-hoadon",
    "statement": "/api/evn/tracuu/file-bangke-hoadon",
    "notice": "/api/evn/tracuu/file-thongbao-hoadon",
}


class Reply:
    def __init__(
        self,
        data: Any = None,
        *,
        status: int = 200,
        payload: Any = MISSING,
        raw: bytes | None = None,
        content_length: Any = MISSING,
        read_error: BaseException | None = None,
    ) -> None:
        self.status = status
        self.raw = (
            raw
            if raw is not None
            else json.dumps(
                {"success": True, "data": data} if payload is MISSING else payload
            ).encode()
        )
        self.content_length = (
            len(self.raw) if content_length is MISSING else content_length
        )
        self.read_error = read_error
        self.content = self
        self.consumed = 0
        self.exited = False

    async def __aenter__(self) -> Self:
        await asyncio.sleep(0)
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


class GatedReply(Reply):
    def __init__(self, data: Any) -> None:
        super().__init__(data)
        self.reading = asyncio.Event()
        self.release = asyncio.Event()

    async def iter_chunked(self, size: int) -> AsyncIterator[bytes]:
        self.reading.set()
        await self.release.wait()
        async for chunk in super().iter_chunked(size):
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
        assert timeout.total == 30
        assert timeout.connect == 10
        assert timeout.sock_read == 20
        self.calls.append({"method": method, "url": url, **options})
        assert self.replies, "Unexpected offline request"
        return self.replies.pop(0)

    def done(self) -> None:
        assert not self.replies


@pytest.fixture(autouse=True)
def offline_clock_and_network(monkeypatch: pytest.MonkeyPatch) -> None:
    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Self:
            return cls.fromtimestamp(NOW.timestamp(), tz)

    async def blocked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound requests are disabled")

    monkeypatch.setattr(api, "datetime", Clock)
    monkeypatch.setattr(ClientSession, "_request", blocked)


def client_for(
    session: Session, *, tokens: Any = TOKENS, on_tokens: Any = None
) -> api.EvnClient:
    return api.EvnClient(
        cast(ClientSession, session),
        "offline-user",
        "offline-password",
        "0123456789abcdef",
        tokens=tokens,
        on_tokens=on_tokens,
    )


def contracts(*people: api.Customer) -> Reply:
    return Reply(
        [
            {
                "maKhang": person.code,
                "maDviqly": person.management_unit,
                "tenKhang": person.name,
                "maHdong": person.contract,
            }
            for person in people
        ]
    )


def config() -> Reply:
    return Reply(
        [
            {"key": "URL_API", "subdivisionid": region, "value": base}
            for region, base in BASES.items()
        ]
    )


def selected(
    person: api.Customer = PERSON,
    region: str = "PB",
    access: str = "offline-selected",
) -> Reply:
    return Reply(
        {
            "accessToken": access,
            "data": {
                "maDviCaptct": region,
                "maKhang": person.code,
                "maDviqly": person.management_unit,
            },
        }
    )


def owned(person: api.Customer = PERSON) -> dict[str, Any]:
    return {"MA_KHANG": person.code, "MA_DVIQLY": person.management_unit}


def invoice_row(person: api.Customer = PERSON, **updates: Any) -> dict[str, Any]:
    return owned(person) | {
        "ID_HDON": "OFFLINE-INVOICE-A",
        "ID_HDON_DC": None,
        "THANG": 11,
        "NAM": 2025,
        "LOAI_HDON": "TD",
        "LOAI_PSINH": "PS",
        "TONG_TIEN": 12345,
        **updates,
    }


def details_replies(
    person: api.Customer = PERSON,
    *,
    region: str = "PB",
    access: str = "offline-selected",
    history: list[dict[str, Any]] | None = None,
    current: list[dict[str, Any]] | None = None,
    skip_daily: bool = False,
) -> list[Reply]:
    data = [
        Reply([owned(person) | {"MA_DDO": POINT, "DIEN_TTHU": 123}]),
        Reply([owned(person) | {"MA_DDO": POINT, "DIEN_TTHU": 4}]),
        Reply([owned(person) | {"MA_DDO": POINT, "CHISO_MOI": 345}]),
        Reply([owned(person) | {"MA_DDO": POINT, "CHISO_MOI": 234}]),
        Reply([] if history is None else history),
        Reply([] if current is None else current),
    ]
    if skip_daily:
        data = [data[index] for index in (0, 2, 4, 5)]
    return [
        selected(person, region, access),
        Reply([owned(person) | {"MA_DDO": POINT}]),
        *data,
    ]


async def issued_client(
    row: dict[str, Any] | None = None,
    *,
    person: api.Customer = PERSON,
    region: str = "PB",
    on_tokens: Any = None,
) -> tuple[api.EvnClient, Session, api.DetailSnapshot]:
    session = Session(
        contracts(person),
        config(),
        *details_replies(
            person,
            region=region,
            history=[invoice_row(person) if row is None else row],
        ),
    )
    client = client_for(session, on_tokens=on_tokens)
    result = await client.details(person, POINT, START, TODAY)
    session.done()
    return client, session, result


def minimal_pdf() -> bytes:
    content = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for number, body in enumerate(
        (
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>",
        ),
        start=1,
    ):
        offsets.append(len(content))
        content += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(content)
    content += b"xref\n0 4\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        content += f"{offset:010d} 00000 n \n".encode()
    return (
        content
        + b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )


PDF = minimal_pdf()
PDF_BASE64 = base64.b64encode(PDF).decode("ascii")


def sized_pdf(size: int) -> bytes:
    head = b"%PDF-1.7\n"
    end = b"\n%%EOF\n"
    return head + b" " * (size - len(head) - len(end)) + end


@pytest.mark.parametrize("region", list(BASES))
async def test_details_contract_and_trusted_regional_routing(region: str) -> None:
    history = [invoice_row(TTRANG_TTOAN="DATT")]
    current = [invoice_row(ID_HDON="OFFLINE-INVOICE-B", TTRANG_TTOAN="CHUATT")]
    session = Session(
        contracts(PERSON),
        config(),
        *details_replies(region=region, history=history, current=current),
    )
    changes: list[api.TokenState] = []
    client = client_for(session, on_tokens=changes.append)
    forged_display = api.Customer(PERSON.code, PERSON.management_unit, "Untrusted name")
    result = await client.details(forged_display, POINT, START, TODAY)
    assert type(result) is api.DetailSnapshot
    assert [field.name for field in fields(result)] == [
        "customer",
        "region",
        "point",
        "start",
        "end",
        "monthly",
        "daily",
        "monthly_readings",
        "daily_readings",
        "invoices",
        "fetched_at",
    ]
    assert result.customer == PERSON
    assert result.region == region
    assert result.point == POINT
    assert (result.start, result.end) == (START, TODAY)
    assert result.fetched_at == NOW
    assert result.fetched_at.tzinfo is UTC
    assert result.invoices == history + current
    assert result.monthly == [owned() | {"MA_DDO": POINT, "DIEN_TTHU": 123}]
    assert result.daily == [owned() | {"MA_DDO": POINT, "DIEN_TTHU": 4}]
    assert result.monthly_readings == [owned() | {"MA_DDO": POINT, "CHISO_MOI": 345}]
    assert result.daily_readings == [owned() | {"MA_DDO": POINT, "CHISO_MOI": 234}]
    for private in (PERSON.code, PERSON.name, POINT, history[0]["ID_HDON"]):
        assert private not in repr(result)
    assert [call["url"] for call in session.calls] == [
        api.CENTRAL_BASE + "/user/me",
        api.CENTRAL_BASE + "/public/allconfig",
        api.CENTRAL_BASE + "/user/switch/" + PERSON.code,
        BASES[region] + "/api/evn/customers/diemdo",
        *(BASES[region] + path for path in DATA_PATHS),
    ]
    assert [call["method"] for call in session.calls] == ["GET"] * 4 + ["POST"] * 6
    monthly_body = owned() | {
        "MA_DDO": POINT,
        "TU_THANG_NAM": "11/2025",
        "DEN_THANG_NAM": "01/2026",
    }
    assert session.calls[4]["json"] == session.calls[6]["json"] == monthly_body
    assert session.calls[5]["json"] == {
        "MA_DVIQLY": PERSON.management_unit,
        "MA_DDO": POINT,
        "TU_NGAY": "01/12/2025",
        "DEN_NGAY": "31/12/2025",
    }
    assert session.calls[7]["json"] == session.calls[5]["json"] | {
        "TU_NGAY": "30/11/2025"
    }
    assert session.calls[8]["json"] == {
        "TU_THANG_NAM": "11/2025",
        "DEN_THANG_NAM": "01/2026",
    }
    assert "json" not in session.calls[9]
    assert "data" not in session.calls[9]
    assert session.calls[9]["skip_auto_headers"] == {"Content-Type"}
    assert "Authorization" not in session.calls[1]["headers"]
    assert all(
        call["headers"]["Authorization"] == "Bearer offline-selected"
        for call in session.calls[3:]
    )
    assert changes == [
        api.TokenState(
            "offline-selected",
            TOKENS.refresh_token,
            PERSON.code,
            PERSON.management_unit,
        )
    ]
    session.done()


@pytest.mark.parametrize(
    ("start", "end", "daily_start", "daily_end"),
    [
        (TODAY - timedelta(days=365), TODAY, date(2025, 12, 1), date(2025, 12, 31)),
        (TODAY - timedelta(days=366), TODAY, date(2025, 12, 1), date(2025, 12, 31)),
        (date(2025, 12, 1), date(2025, 12, 31), date(2025, 12, 1), date(2025, 12, 31)),
        (date(2025, 8, 1), date(2025, 8, 20), date(2025, 8, 1), date(2025, 8, 20)),
        (date(2024, 2, 27), date(2024, 2, 29), date(2024, 2, 27), date(2024, 2, 29)),
        (date(2025, 12, 31), TODAY, date(2025, 12, 31), date(2025, 12, 31)),
        (date(2025, 5, 5), date(2025, 5, 5), date(2025, 5, 5), date(2025, 5, 5)),
        (
            TODAY - timedelta(days=5 * 366),
            TODAY - timedelta(days=5 * 366 - 365),
            TODAY - timedelta(days=5 * 366 - 335),
            TODAY - timedelta(days=5 * 366 - 365),
        ),
    ],
)
async def test_calendar_range_and_daily_windows(
    start: date, end: date, daily_start: date, daily_end: date
) -> None:
    session = Session(contracts(PERSON), config(), *details_replies())
    result = await client_for(session).details(PERSON, POINT, start, end)
    assert (result.start, result.end) == (start, end)
    month_fields = {
        "TU_THANG_NAM": start.strftime("%m/%Y"),
        "DEN_THANG_NAM": end.strftime("%m/%Y"),
    }
    assert (
        session.calls[4]["json"]
        == session.calls[6]["json"]
        == (owned() | {"MA_DDO": POINT} | month_fields)
    )
    assert session.calls[8]["json"] == month_fields
    assert session.calls[5]["json"] == {
        "MA_DVIQLY": PERSON.management_unit,
        "MA_DDO": POINT,
        "TU_NGAY": daily_start.strftime("%d/%m/%Y"),
        "DEN_NGAY": daily_end.strftime("%d/%m/%Y"),
    }
    assert session.calls[7]["json"] == session.calls[5]["json"] | {
        "TU_NGAY": (daily_start - timedelta(days=1)).strftime("%d/%m/%Y")
    }
    assert (daily_end - daily_start).days + 1 <= 31
    assert (daily_end - (daily_start - timedelta(days=1))).days + 1 <= 32
    session.done()


async def test_today_only_has_no_completed_daily_window() -> None:
    session = Session(contracts(PERSON), config(), *details_replies(skip_daily=True))
    result = await client_for(session).details(PERSON, POINT, TODAY, TODAY)
    assert result.daily == result.daily_readings == []
    assert [call["url"] for call in session.calls[4:]] == [
        BASES["PB"] + DATA_PATHS[index] for index in (0, 2, 4, 5)
    ]
    session.done()


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (None, TODAY),
        (START, None),
        (True, TODAY),
        (START, False),
        (123, TODAY),
        (START, 123),
        (START.isoformat(), TODAY),
        (START, TODAY.isoformat()),
        (datetime(2025, 12, 1, tzinfo=UTC), TODAY),
        (START, datetime(2025, 12, 1, tzinfo=UTC)),
        (TODAY, START),
        (START, TODAY + timedelta(days=1)),
        (TODAY - timedelta(days=367), TODAY),
        (TODAY - timedelta(days=5 * 366 + 1), TODAY - timedelta(days=5 * 366)),
        (date.min, date.min),
        (date.max, date.max),
    ],
)
async def test_invalid_dates_rejected_before_any_request(start: Any, end: Any) -> None:
    session = Session()
    client = client_for(session, tokens=None)
    with pytest.raises(api.EvnResponseError):
        await client.details(PERSON, POINT, start, end)
    assert not session.calls
    assert client.tokens is None


@pytest.mark.parametrize("point", [None, True, 123, {}, [], "", " ", "POINT\n", "\x7f"])
async def test_malformed_point_before_login(point: Any) -> None:
    session = Session()
    with pytest.raises(api.EvnResponseError):
        await client_for(session, tokens=None).details(PERSON, point, START, TODAY)
    assert not session.calls


@pytest.mark.parametrize("candidate", [None, {}, "CUSTOMER", True])
async def test_malformed_customer_before_login(candidate: Any) -> None:
    session = Session()
    with pytest.raises(api.EvnAuthError):
        await client_for(session, tokens=None).details(candidate, POINT, START, TODAY)
    assert not session.calls


@pytest.mark.parametrize(
    "candidate",
    [OTHER, api.Customer(PERSON.code, OTHER.management_unit)],
)
async def test_unlinked_customer_cannot_switch(candidate: api.Customer) -> None:
    session = Session(contracts(PERSON))
    with pytest.raises(api.EvnAuthError):
        await client_for(session).details(candidate, POINT, START, TODAY)
    assert [call["url"] for call in session.calls] == [api.CENTRAL_BASE + "/user/me"]
    session.done()


@pytest.mark.parametrize(
    "point", ["UNKNOWN", "../private", "https://example.invalid/doc"]
)
async def test_point_must_be_in_selected_customer_inventory(point: str) -> None:
    session = Session(*[contracts(PERSON), config(), *details_replies()[:2]])
    with pytest.raises(api.EvnAuthError):
        await client_for(session).details(PERSON, point, START, TODAY)
    assert len(session.calls) == 4
    assert session.calls[-1]["url"] == BASES["PB"] + "/api/evn/customers/diemdo"
    session.done()


@pytest.mark.parametrize(
    "points",
    [
        None,
        {},
        [None],
        [{}],
        [{"MA_DDO": None}],
        [{"MA_DDO": 123}],
        [{"MA_DDO": POINT}, {"MA_DDO": POINT}],
        [{"MA_DDO": POINT, "MA_KHANG": OTHER.code}],
        [{"MA_DDO": POINT, "MA_DVIQLY": OTHER.management_unit}],
    ],
)
async def test_point_inventory_schema_and_ownership_fail_closed(points: Any) -> None:
    session = Session(contracts(PERSON), config(), selected(), Reply(points))
    with pytest.raises(api.EvnResponseError):
        await client_for(session).details(PERSON, POINT, START, TODAY)
    assert len(session.calls) == 4
    session.done()


async def test_empty_point_inventory_is_not_permission_to_query() -> None:
    session = Session(contracts(PERSON), config(), selected(), Reply([]))
    with pytest.raises(api.EvnAuthError):
        await client_for(session).details(PERSON, POINT, START, TODAY)
    session.done()


@pytest.mark.parametrize("stage", range(6))
@pytest.mark.parametrize(
    "bad_rows",
    [
        None,
        {},
        {"data": []},
        [None],
        [[]],
        [{"MA_KHANG": OTHER.code}],
        [{"MA_DVIQLY": OTHER.management_unit}],
        [{"MA_KHANG": None}],
        [{"MA_DVIQLY": False}],
    ],
)
async def test_details_schema_or_ownership_failure_aborts_all(
    stage: int, bad_rows: Any
) -> None:
    replies = details_replies()
    replies[stage + 2] = Reply(bad_rows)
    session = Session(contracts(PERSON), config(), *replies[: stage + 3])
    client = client_for(session)
    with pytest.raises(api.EvnResponseError):
        await client.details(PERSON, POINT, START, TODAY)
    assert not client._issued_invoices
    session.done()


@pytest.mark.parametrize("stage", range(4))
@pytest.mark.parametrize("point", ["OTHER", None, 123, False])
async def test_all_point_data_are_owned(stage: int, point: Any) -> None:
    replies = details_replies()
    replies[stage + 2] = Reply([owned() | {"MA_DDO": point}])
    session = Session(contracts(PERSON), config(), *replies[: stage + 3])
    with pytest.raises(api.EvnResponseError):
        await client_for(session).details(PERSON, POINT, START, TODAY)
    session.done()


@pytest.mark.parametrize("stage", range(6))
@pytest.mark.parametrize("status", [302, 417, 503])
async def test_any_endpoint_failure_is_not_empty_data(stage: int, status: int) -> None:
    replies = details_replies()
    failed = Reply(
        status=status, payload={"success": False, "message": "synthetic-private"}
    )
    replies[stage + 2] = failed
    session = Session(contracts(PERSON), config(), *replies[: stage + 3])
    client = client_for(session)
    error = api.EvnConnectionError if status == 503 else api.EvnResponseError
    with pytest.raises(error) as caught:
        await client.details(PERSON, POINT, START, TODAY)
    assert "synthetic-private" not in "".join(traceback.format_exception(caught.value))
    assert not client._issued_invoices
    assert failed.consumed == 0
    session.done()


async def test_explicit_empty_lists_remain_empty() -> None:
    replies = details_replies()[:2] + [Reply([]) for _ in DATA_PATHS]
    session = Session(contracts(PERSON), config(), *replies)
    result = await client_for(session).details(PERSON, POINT, START, TODAY)
    assert result.monthly == result.daily == result.monthly_readings == []
    assert result.daily_readings == result.invoices == []
    session.done()


async def test_invoice_dedup_preserves_original_adjusted_ids_and_metadata() -> None:
    original = invoice_row(ID_HDON=123, ID_HDON_DC=456, NGAY_TTOAN="11/11/2025")
    same = original | {
        "ID_HDON": "123",
        "ID_HDON_DC": "456",
        "TONG_TIEN": 23456,
        "KENH_THANH_TOAN": "Offline channel",
    }
    adjustment = invoice_row(ID_HDON=123, ID_HDON_DC=789, TTRANG_TTOAN=None)
    unadjusted = invoice_row(ID_HDON=123, TTRANG_TTOAN="CHUATT")
    distinct = invoice_row(ID_HDON=321, ID_HDON_DC=456)
    session = Session(
        contracts(PERSON),
        config(),
        *details_replies(
            history=[original, adjustment, unadjusted],
            current=[same, same.copy(), distinct],
        ),
    )
    client = client_for(session)
    result = await client.details(PERSON, POINT, START, TODAY)
    assert result.invoices == [original | same, adjustment, unadjusted, distinct]
    assert "TTRANG_TTOAN" not in result.invoices[0]
    assert result.invoices[1]["TTRANG_TTOAN"] is None
    assert result.invoices[0]["NGAY_TTOAN"] == original["NGAY_TTOAN"]
    assert result.invoices[0]["KENH_THANH_TOAN"] == same["KENH_THANH_TOAN"]
    assert len(client._issued_invoices[(PERSON.code, PERSON.management_unit)]) == 4
    assert original["ID_HDON"] == 123
    assert original["ID_HDON_DC"] == 456
    assert "KENH_THANH_TOAN" not in original
    session.done()


async def test_invoice_missing_optional_ids_and_owner_not_fabricated() -> None:
    row = {key: value for key, value in invoice_row().items() if key not in owned()}
    row.pop("ID_HDON_DC")
    current = row | {"ID_HDON_DC": "", "NGAY_TTOAN": None}
    session = Session(
        contracts(PERSON),
        config(),
        *details_replies(history=[row], current=[current]),
    )
    client = client_for(session)
    result = await client.details(PERSON, POINT, START, TODAY)
    assert result.invoices == [current]
    assert "MA_KHANG" not in result.invoices[0]
    assert "TTRANG_TTOAN" not in result.invoices[0]
    session.replies.extend([selected(), Reply(PDF_BASE64)])
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == PDF
    assert session.calls[-1]["json"]["ID_HDON"] == row["ID_HDON"]
    session.done()


@pytest.mark.parametrize("stage", [4, 5])
@pytest.mark.parametrize(
    "bad_id",
    [
        None,
        True,
        False,
        0,
        -1,
        1.0,
        float("inf"),
        float("nan"),
        [],
        {},
        "",
        "..",
        "../file",
        "https://example.invalid/file",
        "id\n",
    ],
)
async def test_invalid_invoice_ids_do_not_issue_documents(
    stage: int, bad_id: Any
) -> None:
    replies = details_replies()
    replies[stage + 2] = Reply([invoice_row(ID_HDON=bad_id)])
    session = Session(contracts(PERSON), config(), *replies[: stage + 3])
    client = client_for(session)
    with pytest.raises(api.EvnResponseError):
        await client.details(PERSON, POINT, START, TODAY)
    assert not client._issued_invoices
    session.done()


@pytest.mark.parametrize("kind", list(PDF_PATHS))
@pytest.mark.parametrize("original", [123, "OFFLINE-INVOICE-A"])
@pytest.mark.parametrize("adjusted", [None, "", 456, "OFFLINE-ADJUSTED-A"])
async def test_pdf_kinds_use_fetched_record_and_effective_id(
    kind: str, original: Any, adjusted: Any
) -> None:
    raw = invoice_row(ID_HDON=original, ID_HDON_DC=adjusted, THANG="11", NAM="2025")
    preserved = deepcopy(raw)
    client, session, result = await issued_client(raw)
    session.replies.extend([selected(access="offline-pdf-selected"), Reply(PDF_BASE64)])
    row = result.invoices[0]
    if kind == "invoice":
        content = await client.invoice_pdf(PERSON, row.copy())
    else:
        content = await client.invoice_pdf(PERSON, row.copy(), kind)
    assert content == PDF
    assert row == preserved
    assert raw == preserved
    assert session.calls[-2]["url"] == api.CENTRAL_BASE + "/user/switch/" + PERSON.code
    call = session.calls[-1]
    assert call["url"] == BASES["PB"] + PDF_PATHS[kind]
    assert call["method"] == "POST"
    assert call["json"] == {
        "ID_HDON": str(adjusted if adjusted not in (None, "") else original),
        "LOAI_PSINH": "TATCA",
        "THANG": 11,
        "NAM": 2025,
        "LOAI_HDON": "TD",
    }
    assert call["headers"]["Authorization"] == "Bearer offline-pdf-selected"
    assert "skip_auto_headers" not in call
    session.done()


@pytest.mark.parametrize("region", list(BASES))
async def test_pdf_uses_selected_region_not_customer_prefix(region: str) -> None:
    client, session, result = await issued_client()
    session.replies.extend([selected(region=region), Reply(PDF_BASE64)])
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == PDF
    assert session.calls[-1]["url"] == BASES[region] + PDF_PATHS["invoice"]
    session.done()


async def test_uncached_invoice_rejected_without_login_or_inventory_request() -> None:
    session = Session()
    client = client_for(session, tokens=None)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, invoice_row())
    assert not session.calls
    assert client.tokens is None


@pytest.mark.parametrize(
    "kind",
    [
        None,
        True,
        [],
        {},
        "",
        "Invoice",
        "bangke",
        "../file",
        "/api/evn/tracuu/file-hoadon",
        "https://example.invalid/file",
    ],
)
async def test_unknown_pdf_kind_fails_before_outbound(kind: Any) -> None:
    client, session, result = await issued_client()
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0], kind)
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize("candidate", [None, True, {}, PERSON.code])
async def test_pdf_invalid_customer_without_outbound(candidate: Any) -> None:
    session = Session()
    with pytest.raises(api.EvnAuthError):
        await client_for(session).invoice_pdf(candidate, invoice_row())
    assert not session.calls


@pytest.mark.parametrize("invoice", [None, True, [], "OFFLINE-INVOICE-A", 123])
async def test_pdf_requires_raw_mapping(invoice: Any) -> None:
    session = Session()
    with pytest.raises(api.EvnResponseError):
        await client_for(session).invoice_pdf(PERSON, invoice)
    assert not session.calls


@pytest.mark.parametrize(
    "updates",
    [
        {"ID_HDON": "OFFLINE-UNKNOWN"},
        {"ID_HDON_DC": "OFFLINE-UNKNOWN"},
        {"THANG": 12},
        {"NAM": 2024},
        {"LOAI_HDON": "TC"},
        {"TTRANG_TTOAN": "DATT"},
        {"TONG_TIEN": 0},
        {"ADDED_METADATA": "synthetic"},
    ],
)
async def test_cached_id_does_not_authorize_tampered_raw_record(
    updates: dict[str, Any],
) -> None:
    client, session, result = await issued_client()
    before = len(session.calls)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, result.invoices[0] | updates)
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize(
    "updates",
    [
        {"MA_KHANG": OTHER.code},
        {"MA_DVIQLY": OTHER.management_unit},
        {"MA_KHANG": None},
        {"MA_DVIQLY": False},
    ],
)
async def test_pdf_row_ownership_is_still_strict(updates: dict[str, Any]) -> None:
    client, session, result = await issued_client()
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0] | updates)
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize("field", ["THANG", "NAM"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        0,
        -1,
        1.0,
        1.5,
        float("inf"),
        float("nan"),
        [],
        {},
        "",
        "1.0",
        "Infinity",
        "../file",
        "https://example.invalid/file",
        " 1",
        "1\n",
        "99999",
    ],
)
async def test_pdf_numeric_fields_validated_from_cached_rows(
    field: str, value: Any
) -> None:
    client, session, result = await issued_client(invoice_row(**{field: value}))
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize(
    "updates",
    [
        {"THANG": 13},
        {"NAM": 10000},
        {"LOAI_HDON": None},
        {"LOAI_HDON": True},
        {"LOAI_HDON": 123},
        {"LOAI_HDON": ""},
        {"LOAI_HDON": "TD\n"},
        {"LOAI_HDON": "../file"},
        {"LOAI_HDON": "https://example.invalid/file"},
    ],
)
async def test_pdf_payload_invalid_period_or_kind(updates: dict[str, Any]) -> None:
    client, session, result = await issued_client(invoice_row(**updates))
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize("field", ["ID_HDON", "ID_HDON_DC"])
@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        0,
        -1,
        1.0,
        float("inf"),
        float("nan"),
        [],
        {},
        "..",
        "/tmp/file",
        "../file",
        "id?query",
        "id#fragment",
        "id\\file",
        "https://example.invalid/file",
        "file://private",
        "id\r\n",
        "000",
        "a" * 129,
    ],
)
async def test_pdf_file_id_cannot_be_path_url_or_unsafe_scalar(
    field: str, value: Any
) -> None:
    client, session, result = await issued_client()
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0] | {field: value})
    assert len(session.calls) == before
    session.done()


async def test_missing_pdf_fields_fail_without_outbound() -> None:
    client, session, result = await issued_client({"ID_HDON": "OFFLINE-ID"})
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert len(session.calls) == before
    session.done()


async def test_cache_is_deep_copied_and_bound_to_this_client_and_customer() -> None:
    row = invoice_row(EXTRA={"nested": ["synthetic"]})
    client, session, result = await issued_client(row)
    original = deepcopy(result.invoices[0])
    result.invoices[0]["EXTRA"]["nested"].append("tampered")
    before = len(session.calls)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(OTHER, original | owned(OTHER))
    separate = client_for(session, tokens=client.tokens)
    with pytest.raises(api.EvnAuthError):
        await separate.invoice_pdf(PERSON, original)
    assert len(session.calls) == before
    session.replies.extend([selected(), Reply(PDF_BASE64)])
    assert await client.invoice_pdf(PERSON, original) == PDF
    session.done()


async def test_successful_new_details_replaces_issued_customer_documents() -> None:
    client, session, first = await issued_client()
    session.replies.extend(
        details_replies(history=[invoice_row(ID_HDON="OFFLINE-NEW")])
    )
    second = await client.details(PERSON, POINT, START, TODAY)
    before = len(session.calls)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, first.invoices[0])
    assert len(session.calls) == before
    session.replies.extend([selected(), Reply(PDF_BASE64)])
    assert await client.invoice_pdf(PERSON, second.invoices[0]) == PDF
    session.done()


async def test_failed_details_does_not_leave_partial_or_stale_authorization() -> None:
    client, session, first = await issued_client()
    replies = details_replies(history=[invoice_row(ID_HDON="OFFLINE-NEW")])
    replies[-1] = Reply(status=503)
    session.replies.extend(replies)
    with pytest.raises(api.EvnConnectionError):
        await client.details(PERSON, POINT, START, TODAY)
    before = len(session.calls)
    for candidate in (first.invoices[0], invoice_row(ID_HDON="OFFLINE-NEW")):
        with pytest.raises(api.EvnAuthError):
            await client.invoice_pdf(PERSON, candidate)
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize("accepted", [True, False])
async def test_password_session_reset_revokes_issued_rows(accepted: bool) -> None:
    client, session, result = await issued_client()
    session.replies.extend(
        [
            Reply({}),
            Reply(
                {
                    "accessToken": "offline-new-access",
                    "refreshToken": "offline-new-refresh",
                }
            )
            if accepted
            else Reply(
                status=417, payload={"success": False, "message": "synthetic-private"}
            ),
        ]
    )
    if accepted:
        await client.login()
    else:
        with pytest.raises(api.EvnAuthError):
            await client.login()
    before = len(session.calls)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert len(session.calls) == before
    assert not client._issued_invoices
    session.done()


@pytest.mark.parametrize(
    "data",
    [
        None,
        True,
        123,
        [],
        {},
        {"data": PDF_BASE64},
        "",
        "https://example.invalid/document.pdf",
        "/private/document.pdf",
        "data:application/pdf;base64," + PDF_BASE64,
        PDF_BASE64 + "\n",
        " " + PDF_BASE64,
        PDF_BASE64[:8] + "\t" + PDF_BASE64[8:],
        PDF_BASE64[:-1],
        "!!!!",
        "éééé",
        "AAAA=AAA",
        "====",
        "YWJjZA======",
        base64.b64encode(b"<html>%PDF-1.7\n%%EOF</html>").decode(),
        base64.b64encode(b"\x00\x01\x02\xff").decode(),
        base64.b64encode(b" prefix " + PDF).decode(),
        base64.b64encode(b"%PDF-<script>bad()</script>\n%%EOF\n").decode(),
        base64.b64encode(b"%PDF-1.7\ntruncated").decode(),
        base64.b64encode(b"%PDF-1.7\n%%EOF\n<html>bad</html>").decode(),
        base64.urlsafe_b64encode(b"%PDF-1.7\n%\xfb\xff\n%%EOF\n").decode(),
    ],
)
async def test_pdf_rejects_non_raw_base64_non_pdf_or_malformed_file(data: Any) -> None:
    client, session, result = await issued_client()
    reply = Reply(data)
    session.replies.extend([selected(), reply])
    with pytest.raises(api.EvnResponseError) as caught:
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert "example.invalid" not in "".join(traceback.format_exception(caught.value))
    assert reply.exited
    session.done()


async def test_noncanonical_base64_pad_bits_are_rejected() -> None:
    data = PDF + b" " * ((1 - len(PDF)) % 3)
    encoded = base64.b64encode(data).decode()
    assert encoded.endswith("==")
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    index = alphabet.index(encoded[-3])
    mutated = encoded[:-3] + alphabet[index + 1] + "=="
    assert base64.b64decode(mutated, validate=True) == data
    client, session, result = await issued_client()
    session.replies.extend([selected(), Reply(mutated)])
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    session.done()


@pytest.mark.parametrize("size", [api._MAX_RESPONSE_BYTES + 1024, api._MAX_PDF_BYTES])
async def test_pdf_larger_than_normal_json_and_exact_decoded_limit(size: int) -> None:
    data = sized_pdf(size)
    client, session, result = await issued_client()
    reply = Reply(base64.b64encode(data).decode(), content_length=None)
    session.replies.extend([selected(), reply])
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == data
    assert reply.consumed == len(reply.raw)
    assert reply.exited
    session.done()


async def test_decoded_pdf_over_limit_rejected_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = sized_pdf(api._MAX_PDF_BYTES + 1)
    client, session, result = await issued_client()
    session.replies.extend([selected(), Reply(base64.b64encode(data).decode())])

    def blocked_decode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Oversized decoded PDF must not be allocated")

    monkeypatch.setattr(api.base64, "b64decode", blocked_decode)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    session.done()


@pytest.mark.parametrize("content_length", [None, api._MAX_PDF_RESPONSE_BYTES + 1])
async def test_pdf_json_stream_and_content_length_are_bounded(
    content_length: Any,
) -> None:
    client, session, result = await issued_client()
    reply = Reply(
        raw=b" " * (api._MAX_PDF_RESPONSE_BYTES + 131072),
        content_length=content_length,
    )
    session.replies.extend([selected(), reply])
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert reply.consumed <= api._MAX_PDF_RESPONSE_BYTES + 65536
    assert reply.consumed < len(reply.raw)
    assert reply.exited
    session.done()


async def test_pdf_json_ceiling_boundary_and_normal_json_ceiling_unchanged() -> None:
    client, session, result = await issued_client()
    raw = Reply(PDF_BASE64).raw
    reply = Reply(
        raw=raw + b" " * (api._MAX_PDF_RESPONSE_BYTES - len(raw)), content_length=None
    )
    session.replies.extend([selected(), reply])
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == PDF
    assert reply.consumed == api._MAX_PDF_RESPONSE_BYTES
    normal = Reply(
        raw=raw + b" " * (api._MAX_RESPONSE_BYTES + 131072), content_length=None
    )
    session.replies.append(normal)
    with pytest.raises(api.EvnResponseError):
        await client._authenticated_locked("GET", api.CENTRAL_BASE, "/user/me")
    assert normal.consumed < len(normal.raw)
    session.done()


@pytest.mark.parametrize(
    "limit",
    [
        None,
        True,
        0,
        -1,
        api._MAX_RESPONSE_BYTES + 1,
        api._MAX_PDF_RESPONSE_BYTES + 1,
        float("inf"),
    ],
)
async def test_private_response_ceiling_cannot_be_arbitrarily_increased(
    limit: Any,
) -> None:
    session = Session()
    with pytest.raises(api.EvnResponseError):
        await client_for(session)._send(
            "GET", api.CENTRAL_BASE + "/user/me", max_response_bytes=limit
        )
    assert not session.calls


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 417])
async def test_pdf_redirects_and_non_auth_417_do_not_refresh(status: int) -> None:
    client, session, result = await issued_client()
    reply = Reply(PDF_BASE64, status=status)
    session.replies.extend([selected(), reply])
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert len(session.calls) == before + 2
    assert session.calls[-1]["allow_redirects"] is False
    assert reply.consumed == 0
    assert client.tokens is not None
    assert client.tokens.access_token == "offline-selected"
    session.done()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"success": True},
        {"success": False, "data": PDF_BASE64},
        {"success": 1, "data": PDF_BASE64},
        {"success": "true", "data": PDF_BASE64},
    ],
)
async def test_pdf_envelope_failure_never_returns_empty_bytes(payload: Any) -> None:
    client, session, result = await issued_client()
    session.replies.extend([selected(), Reply(payload=payload)])
    with pytest.raises(api.EvnResponseError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    session.done()


@pytest.mark.parametrize(
    "failure", [asyncio.CancelledError(), TimeoutError("synthetic-private")]
)
async def test_pdf_read_failure_unlocks_and_preserves_cache(
    failure: BaseException,
) -> None:
    client, session, result = await issued_client()
    reply = Reply(PDF_BASE64, read_error=failure)
    session.replies.extend([selected(), reply, selected(), Reply(PDF_BASE64)])
    expected = (
        asyncio.CancelledError
        if isinstance(failure, asyncio.CancelledError)
        else api.EvnConnectionError
    )
    with pytest.raises(expected):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert reply.exited
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == PDF
    session.done()


async def test_details_and_snapshot_concurrency_keep_account_context_isolated() -> None:
    session = Session(
        contracts(PERSON, OTHER),
        config(),
        *details_replies(
            PERSON, region="PB", access="offline-first", history=[invoice_row()]
        ),
        selected(OTHER, "PE", "offline-second"),
        Reply([owned(OTHER) | {"MA_DDO": POINT}]),
        Reply([owned(OTHER) | {"MA_DDO": POINT, "DIEN_TTHU": 12}]),
        Reply([owned(OTHER) | {"MA_DDO": POINT, "DIEN_TTHU": 1}]),
        Reply([owned(OTHER) | {"MA_DDO": POINT, "CHISO_MOI": 13}]),
        Reply([owned(OTHER) | {"MA_DDO": POINT, "CHISO_MOI": 2}]),
        Reply([owned(OTHER) | {"DUONG_PHO": "Offline street"}]),
        Reply([owned(OTHER) | {"TONG_NO": 321}]),
        Reply([owned(OTHER) | {"ID_HDON": "OFFLINE-HISTORY", "TONG_TIEN": 100}]),
        Reply([{"MA_TCHUC": "OFFLINE-BANK", "TEN_TCHUC": "Offline bank"}]),
        Reply([]),
    )
    changes: list[api.TokenState] = []
    client = client_for(session, on_tokens=changes.append)
    detail, snapshot, people = await asyncio.gather(
        client.details(PERSON, POINT, START, TODAY),
        client.fetch_snapshot(OTHER),
        client.customers(),
    )
    assert detail.customer == PERSON
    assert snapshot.customer == OTHER
    assert people == [PERSON, OTHER]
    assert snapshot.invoices[0]["MA_KHANG"] == OTHER.code
    assert snapshot.info["maKhang"] == OTHER.code
    assert snapshot.contracts == [owned(OTHER) | {"DUONG_PHO": "Offline street"}]
    assert snapshot.monthly_readings == {
        POINT: [owned(OTHER) | {"MA_DDO": POINT, "CHISO_MOI": 13}]
    }
    assert snapshot.daily_readings == {
        POINT: [owned(OTHER) | {"MA_DDO": POINT, "CHISO_MOI": 2}]
    }
    assert snapshot.paid_invoices == [
        owned(OTHER) | {"ID_HDON": "OFFLINE-HISTORY", "TONG_TIEN": 100}
    ]
    assert snapshot.banks == [{"MA_TCHUC": "OFFLINE-BANK", "TEN_TCHUC": "Offline bank"}]
    assert detail.invoices[0]["MA_KHANG"] == PERSON.code
    assert all(
        call["headers"]["Authorization"] == "Bearer offline-first"
        for call in session.calls[3:10]
    )
    assert all(
        call["headers"]["Authorization"] == "Bearer offline-second"
        for call in session.calls[11:]
    )
    assert session.calls[10]["headers"]["Authorization"] == "Bearer offline-first"
    assert changes == [
        api.TokenState(
            "offline-first", TOKENS.refresh_token, PERSON.code, PERSON.management_unit
        ),
        api.TokenState(
            "offline-second", TOKENS.refresh_token, OTHER.code, OTHER.management_unit
        ),
    ]
    session.done()


async def test_pdf_holds_same_lock_through_body_read_before_other_details() -> None:
    client, session, first = await issued_client()
    client._customers = [PERSON, OTHER]
    gate = GatedReply(PDF_BASE64)
    session.replies.extend(
        [
            selected(access="offline-pdf"),
            gate,
            *details_replies(
                OTHER, region="PE", access="offline-other", history=[invoice_row(OTHER)]
            ),
        ]
    )
    before = len(session.calls)
    pdf_task = asyncio.create_task(client.invoice_pdf(PERSON, first.invoices[0]))
    await asyncio.wait_for(gate.reading.wait(), 1)
    details_task = asyncio.create_task(client.details(OTHER, POINT, START, TODAY))
    await asyncio.sleep(0)
    assert len(session.calls) == before + 2
    assert not details_task.done()
    gate.release.set()
    content, second = await asyncio.gather(pdf_task, details_task)
    assert content == PDF
    assert second.customer == OTHER
    assert (
        session.calls[before + 2]["url"]
        == api.CENTRAL_BASE + "/user/switch/" + OTHER.code
    )
    assert all(
        call["url"].startswith(BASES["PE"]) for call in session.calls[before + 3 :]
    )
    session.replies.extend([selected(PERSON, "PB", "offline-again"), Reply(PDF_BASE64)])
    assert await client.invoice_pdf(PERSON, first.invoices[0]) == PDF
    assert session.calls[-1]["url"] == BASES["PB"] + PDF_PATHS["invoice"]
    session.done()


async def test_same_invoice_ids_for_two_customers_do_not_collide() -> None:
    session = Session(
        contracts(PERSON, OTHER),
        config(),
        *details_replies(history=[invoice_row()]),
        *details_replies(OTHER, region="PE", history=[invoice_row(OTHER)]),
    )
    client = client_for(session)
    first, second = await asyncio.gather(
        client.details(PERSON, POINT, START, TODAY),
        client.details(OTHER, POINT, START, TODAY),
    )
    session.replies.extend(
        [selected(), Reply(PDF_BASE64), selected(OTHER, "PE"), Reply(PDF_BASE64)]
    )
    values = await asyncio.gather(
        client.invoice_pdf(PERSON, first.invoices[0]),
        client.invoice_pdf(OTHER, second.invoices[0]),
    )
    assert values == [PDF, PDF]
    assert session.calls[-3]["url"] == BASES["PB"] + PDF_PATHS["invoice"]
    assert session.calls[-1]["url"] == BASES["PE"] + PDF_PATHS["invoice"]
    session.done()


@pytest.mark.parametrize("refresh_mode", ["missing", "null", "empty", "rotate"])
async def test_pdf_refresh_context_rotation_and_large_ceiling_replay(
    refresh_mode: str,
) -> None:
    changes: list[api.TokenState] = []
    client, session, result = await issued_client(on_tokens=changes.append)
    refresh_data: dict[str, Any] = {"accessToken": "offline-replayed"}
    new_refresh = (
        "offline-rotated" if refresh_mode == "rotate" else TOKENS.refresh_token
    )
    if refresh_mode != "missing":
        refresh_data["refreshToken"] = {
            "null": None,
            "empty": "",
            "rotate": new_refresh,
        }[refresh_mode]
    content = sized_pdf(api._MAX_RESPONSE_BYTES + 1024)
    session.replies.extend(
        [
            selected(access="offline-pdf"),
            Reply(status=401),
            Reply(refresh_data),
            Reply(base64.b64encode(content).decode(), content_length=None),
        ]
    )
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == content
    assert session.calls[-2]["url"] == api.CENTRAL_BASE + "/auth/refresh"
    assert session.calls[-2]["json"] == {
        "refreshToken": TOKENS.refresh_token,
        "maKhachhang": PERSON.code,
        "donviquanly": PERSON.management_unit,
    }
    assert session.calls[-2]["headers"]["X-deviceId"] == "0123456789abcdef"
    assert "Authorization" not in session.calls[-2]["headers"]
    assert session.calls[-1]["headers"]["Authorization"] == "Bearer offline-replayed"
    assert session.calls[-1]["json"] == session.calls[-3]["json"]
    assert changes[-1] is client.tokens
    assert client.tokens == api.TokenState(
        "offline-replayed", new_refresh, PERSON.code, PERSON.management_unit
    )
    session.done()


async def test_switch_refresh_uses_previous_context_then_pdf_refresh_selected_context() -> (
    None
):
    changes: list[api.TokenState] = []
    client, session, result = await issued_client(on_tokens=changes.append)
    client._store_tokens(
        api.TokenState(
            "offline-other",
            "offline-previous-refresh",
            OTHER.code,
            OTHER.management_unit,
        )
    )
    session.replies.extend(
        [
            Reply(status=401),
            Reply(
                {
                    "accessToken": "offline-switch-replay",
                    "refreshToken": "offline-latest-refresh",
                }
            ),
            selected(access="offline-pdf"),
            Reply(status=401),
            Reply({"accessToken": "offline-file-replay"}),
            Reply(PDF_BASE64),
        ]
    )
    assert await client.invoice_pdf(PERSON, result.invoices[0]) == PDF
    assert session.calls[-5]["json"] == {
        "refreshToken": "offline-previous-refresh",
        "maKhachhang": OTHER.code,
        "donviquanly": OTHER.management_unit,
    }
    assert session.calls[-2]["json"] == {
        "refreshToken": "offline-latest-refresh",
        "maKhachhang": PERSON.code,
        "donviquanly": PERSON.management_unit,
    }
    assert changes[-2] == api.TokenState(
        "offline-pdf", "offline-latest-refresh", PERSON.code, PERSON.management_unit
    )
    assert changes[-1] is client.tokens
    assert client.tokens == api.TokenState(
        "offline-file-replay",
        "offline-latest-refresh",
        PERSON.code,
        PERSON.management_unit,
    )
    session.done()


@pytest.mark.parametrize("failure", ["refresh", "replay", "forbidden"])
async def test_pdf_auth_failure_latches_without_password_login_storm(
    failure: str,
) -> None:
    client, session, result = await issued_client()
    replies = [selected(), Reply(status=403 if failure == "forbidden" else 401)]
    if failure == "refresh":
        replies.append(
            Reply(
                status=417, payload={"success": False, "message": "synthetic-private"}
            )
        )
    elif failure == "replay":
        replies.extend([Reply({"accessToken": "offline-once"}), Reply(status=401)])
    session.replies.extend(replies)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    before = len(session.calls)
    for _ in range(3):
        with pytest.raises(api.EvnAuthError):
            await client.invoice_pdf(PERSON, result.invoices[0])
        with pytest.raises(api.EvnAuthError):
            await client.details(PERSON, POINT, START, TODAY)
    assert len(session.calls) == before
    assert all(not call["url"].endswith("/auth/login") for call in session.calls)
    session.done()


async def test_details_bodyless_post_wire_content_type_skip_preserved() -> None:
    session = Session(contracts(PERSON), config(), *details_replies())
    await client_for(session).details(PERSON, POINT, START, TODAY)
    for call in session.calls:
        request = ClientRequest(
            call["method"],
            URL(call["url"]),
            headers=call["headers"],
            skip_auto_headers=call.get("skip_auto_headers"),
            data=JsonPayload(call["json"]) if "json" in call else None,
            loop=asyncio.get_running_loop(),
        )
        if "json" in call:
            assert request.headers["Content-Type"] == "application/json"
        else:
            assert "Content-Type" not in request.headers
            if call["method"] == "POST":
                assert request.headers["Content-Length"] == "0"
                assert call["url"].endswith("/api/evn/tracuu/hoadon")
    session.done()


@pytest.mark.parametrize("operation", ["details", "pdf"])
@pytest.mark.parametrize(
    "base",
    [
        "https://example.invalid/private",
        "http://api.cskh.evnspc.vn/api",
        "https://api.cskh.evnspc.vn.evil.invalid/api",
        "https://api.cskh.evnspc.vn/api/../file",
        "https://api.cskh.evnspc.vn/api?token=offline",
    ],
)
async def test_new_operations_never_send_tokens_to_untrusted_config(
    operation: str, base: str
) -> None:
    invalid = Reply([{"key": "URL_API", "subdivisionid": "PB", "value": base}])
    if operation == "details":
        session = Session(contracts(PERSON), invalid)
        client = client_for(session)
        row = invoice_row()
    else:
        client, session, result = await issued_client()
        client._regions = None
        session.replies.append(invalid)
        row = result.invoices[0]
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        if operation == "details":
            await client.details(PERSON, POINT, START, TODAY)
        else:
            await client.invoice_pdf(PERSON, row)
    new_calls = session.calls[before:]
    assert all(call["url"].startswith(api.CENTRAL_BASE) for call in new_calls)
    assert new_calls[-1]["url"] == api.CENTRAL_BASE + "/public/allconfig"
    assert "Authorization" not in new_calls[-1]["headers"]
    session.done()


@pytest.mark.parametrize("operation", ["details", "pdf"])
@pytest.mark.parametrize(
    "context",
    [
        None,
        [],
        {},
        {"maDviCaptct": "UNKNOWN"},
        {"maDviCaptct": "PB", "maKhang": OTHER.code},
        {"maDviCaptct": "PB", "maDviqly": OTHER.management_unit},
    ],
)
async def test_new_operations_reject_mismatched_switch_context(
    operation: str, context: Any
) -> None:
    invalid = Reply({"accessToken": "offline-invalid-context", "data": context})
    if operation == "details":
        session = Session(contracts(PERSON), config(), invalid)
        client = client_for(session)
        row = invoice_row()
    else:
        client, session, result = await issued_client()
        session.replies.append(invalid)
        row = result.invoices[0]
    before = len(session.calls)
    with pytest.raises(api.EvnResponseError):
        if operation == "details":
            await client.details(PERSON, POINT, START, TODAY)
        else:
            await client.invoice_pdf(PERSON, row)
    assert all(
        call["url"].startswith(api.CENTRAL_BASE) for call in session.calls[before:]
    )
    session.done()


@pytest.mark.parametrize("stage", range(2, 8))
async def test_details_endpoint_refresh_preserves_context_and_exact_replay(
    stage: int,
) -> None:
    replies = details_replies(history=[invoice_row()])
    successful = replies[stage]
    replies[stage : stage + 1] = [
        Reply(status=401),
        Reply(
            {
                "accessToken": "offline-detail-replay",
                "refreshToken": "offline-detail-rotated",
            }
        ),
        successful,
    ]
    session = Session(contracts(PERSON), config(), *replies)
    changes: list[api.TokenState] = []
    client = client_for(session, on_tokens=changes.append)
    result = await client.details(PERSON, POINT, START, TODAY)
    assert result.invoices == [invoice_row()]
    request, refresh, replay = session.calls[stage + 2 : stage + 5]
    assert refresh["url"] == api.CENTRAL_BASE + "/auth/refresh"
    assert refresh["json"] == {
        "refreshToken": TOKENS.refresh_token,
        "maKhachhang": PERSON.code,
        "donviquanly": PERSON.management_unit,
    }
    assert request["url"] == replay["url"]
    assert request.get("json") == replay.get("json")
    assert request.get("skip_auto_headers") == replay.get("skip_auto_headers")
    assert replay["headers"]["Authorization"] == "Bearer offline-detail-replay"
    assert changes[-1] is client.tokens
    assert client.tokens == api.TokenState(
        "offline-detail-replay",
        "offline-detail-rotated",
        PERSON.code,
        PERSON.management_unit,
    )
    session.done()


async def test_lazy_details_login_serializes_once_for_multiple_customers() -> None:
    session = Session(
        Reply({}),
        Reply(
            {"accessToken": TOKENS.access_token, "refreshToken": TOKENS.refresh_token}
        ),
        contracts(PERSON, OTHER),
        config(),
        *details_replies(history=[invoice_row()]),
        *details_replies(OTHER, history=[invoice_row(OTHER)]),
    )
    client = client_for(session, tokens=None)
    first, second = await asyncio.gather(
        client.details(PERSON, POINT, START, TODAY),
        client.details(OTHER, POINT, START, TODAY),
    )
    assert first.customer == PERSON
    assert second.customer == OTHER
    assert sum(call["url"].endswith("/auth/login") for call in session.calls) == 1
    assert sum(call["url"].endswith("/user/me") for call in session.calls) == 1
    session.done()


async def test_customer_and_unit_both_scope_issued_cache() -> None:
    other_unit = api.Customer(PERSON.code, "OFFLINE-OTHER-UNIT")
    client, session, result = await issued_client()
    before = len(session.calls)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(other_unit, result.invoices[0] | owned(other_unit))
    assert len(session.calls) == before
    session.done()


@pytest.mark.parametrize(
    "person", [api.Customer(cast(Any, []), "UNIT"), api.Customer("CODE", cast(Any, {}))]
)
async def test_malformed_customer_fields_fail_without_type_error(
    person: api.Customer,
) -> None:
    session = Session()
    with pytest.raises(api.EvnAuthError):
        await client_for(session).invoice_pdf(person, {"ID_HDON": "OFFLINE-ID"})
    assert not session.calls


async def test_issued_cache_does_not_replace_account_inventory_authorization() -> None:
    client, session, result = await issued_client()
    client._customers = None
    session.replies.append(contracts(OTHER))
    before = len(session.calls)
    with pytest.raises(api.EvnAuthError):
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert [call["url"] for call in session.calls[before:]] == [
        api.CENTRAL_BASE + "/user/me"
    ]
    session.done()


async def test_pdf_payload_is_detached_before_mutable_input_can_change() -> None:
    client, session, result = await issued_client()
    raw = result.invoices[0]
    switch_payload = json.loads(selected().raw)["data"]
    gate = GatedReply(switch_payload)
    session.replies.extend([gate, Reply(PDF_BASE64)])
    task = asyncio.create_task(client.invoice_pdf(PERSON, raw))
    await asyncio.wait_for(gate.reading.wait(), 1)
    raw["ID_HDON"] = "OFFLINE-UNAUTHORIZED"
    raw["THANG"] = 12
    gate.release.set()
    assert await task == PDF
    assert session.calls[-1]["json"]["ID_HDON"] == "OFFLINE-INVOICE-A"
    assert session.calls[-1]["json"]["THANG"] == 11
    session.done()


@pytest.mark.parametrize("first_operation", ["pdf", "login"])
async def test_explicit_login_and_pdf_share_one_lock(first_operation: str) -> None:
    client, session, result = await issued_client()
    login_replies = [
        Reply({}),
        Reply(
            {
                "accessToken": "offline-new-session",
                "refreshToken": "offline-new-session-refresh",
            }
        ),
    ]
    if first_operation == "pdf":
        session.replies.extend([selected(), Reply(PDF_BASE64), *login_replies])
        content, _ = await asyncio.gather(
            client.invoice_pdf(PERSON, result.invoices[0]), client.login()
        )
        assert content == PDF
    else:
        session.replies.extend(login_replies)
        outcomes = await asyncio.gather(
            client.login(),
            client.invoice_pdf(PERSON, result.invoices[0]),
            return_exceptions=True,
        )
        assert outcomes[0] is None
        assert isinstance(outcomes[1], api.EvnAuthError)
    assert not client._issued_invoices
    assert client.tokens == api.TokenState(
        "offline-new-session", "offline-new-session-refresh"
    )
    session.done()


@pytest.mark.parametrize("stage", ["switch", "refresh"])
async def test_pdf_callback_failure_preserves_latest_tokens_and_stops(
    stage: str,
) -> None:
    client, session, result = await issued_client()
    changes: list[api.TokenState] = []
    sensitive = "offline-private-callback-value"

    def changed(tokens: api.TokenState) -> None:
        assert client.tokens is tokens
        changes.append(tokens)
        if stage == "switch" or tokens.access_token == "offline-refreshed":
            raise RuntimeError(sensitive)

    client._on_tokens = changed
    session.replies.append(selected(access="offline-pdf-switch"))
    if stage == "refresh":
        session.replies.extend(
            [
                Reply(status=401),
                Reply(
                    {
                        "accessToken": "offline-refreshed",
                        "refreshToken": "offline-rotated",
                    }
                ),
            ]
        )
    with pytest.raises(api.EvnError) as caught:
        await client.invoice_pdf(PERSON, result.invoices[0])
    assert sensitive not in "".join(traceback.format_exception(caught.value))
    assert changes[-1] is client.tokens
    assert client.tokens is not None
    assert client.tokens.refresh_token == (
        "offline-rotated" if stage == "refresh" else TOKENS.refresh_token
    )
    session.done()


def snapshot_replies(
    person: api.Customer = PERSON,
    *,
    region: str = "PB",
    access: str = "offline-selected",
) -> list[Reply]:
    return [
        selected(person, region, access),
        Reply([owned(person) | {"MA_DDO": POINT, "DIA_CHI": "Offline address"}]),
        Reply([owned(person) | {"MA_DDO": POINT, "DIEN_TTHU": 12}]),
        Reply([owned(person) | {"MA_DDO": POINT, "DIEN_TTHU": 1}]),
        Reply([owned(person) | {"MA_DDO": POINT, "CHISO_MOI": 13}]),
        Reply([owned(person) | {"MA_DDO": POINT, "CHISO_MOI": 2}]),
        Reply([owned(person) | {"DUONG_PHO": "Offline street"}]),
        Reply([owned(person) | {"ID_HDON": "OFFLINE-CURRENT", "TONG_NO": 321}]),
        Reply([owned(person) | {"ID_HDON": "OFFLINE-HISTORY", "TONG_TIEN": 100}]),
        Reply([{"MA_TCHUC": "OFFLINE-BANK", "TEN_TCHUC": "Offline bank"}]),
        Reply([owned(person) | {"TGIAN_BDAU": "01/01/2026 08:00"}]),
    ]


BANK_INDEX = 11


@pytest.mark.parametrize(
    "reply",
    [
        Reply(status=401),
        Reply(status=403),
        Reply(status=417),
        Reply(status=503),
        Reply(status=302),
        Reply(raw=b"not json"),
        Reply(payload={"success": False}),
        Reply(payload={"success": True}),
        Reply(None),
        Reply({}),
        Reply([None]),
    ],
)
async def test_snapshot_bank_directory_is_optional_and_never_latches(
    reply: Reply,
) -> None:
    session = Session(
        contracts(PERSON),
        config(),
        *snapshot_replies(PERSON),
        *snapshot_replies(PERSON, access="offline-second"),
    )
    session.replies[BANK_INDEX] = reply
    changes: list[api.TokenState] = []
    client = client_for(session, on_tokens=changes.append)
    first = await client.fetch_snapshot(PERSON)
    assert first.banks == []
    assert first.invoices == [
        owned(PERSON) | {"ID_HDON": "OFFLINE-CURRENT", "TONG_NO": 321}
    ]
    assert first.outages == [owned(PERSON) | {"TGIAN_BDAU": "01/01/2026 08:00"}]
    second = await client.fetch_snapshot(PERSON)
    assert second.banks == [{"MA_TCHUC": "OFFLINE-BANK", "TEN_TCHUC": "Offline bank"}]
    assert [
        call["url"] for call in session.calls if call["url"].endswith("/auth/refresh")
    ] == []
    assert changes == [
        api.TokenState(
            "offline-selected",
            TOKENS.refresh_token,
            PERSON.code,
            PERSON.management_unit,
        ),
        api.TokenState(
            "offline-second",
            TOKENS.refresh_token,
            PERSON.code,
            PERSON.management_unit,
        ),
    ]
    session.done()


@pytest.mark.parametrize(
    ("index", "path"),
    [
        (3, "/api/evn/customers/diemdo"),
        (4, "/api/evn/tracuu/diennangthang"),
        (5, "/api/evn/tracuu/diennangngay"),
        (6, "/api/evn/tracuu/chisothang"),
        (7, "/api/evn/tracuu/chisongay"),
        (8, "/api/evn/customers/info"),
        (9, "/api/evn/tracuu/hoadon"),
        (10, "/api/evn/tracuu/lichsu-hoadon"),
        (12, "/api/evn/tracuu/ngungcapdien"),
    ],
)
@pytest.mark.parametrize(
    "row",
    [
        {"MA_KHANG": OTHER.code, "MA_DVIQLY": OTHER.management_unit},
        {"MA_KHANG": PERSON.code, "MA_DVIQLY": OTHER.management_unit},
        {"MA_KHANG": None},
        {"MA_DVIQLY": 1},
    ],
)
async def test_snapshot_every_required_section_is_ownership_checked(
    index: int, path: str, row: dict[str, Any]
) -> None:
    session = Session(
        contracts(PERSON), config(), *snapshot_replies(PERSON)[: index - 2]
    )
    session.replies.append(Reply([row]))
    client = client_for(session)
    with pytest.raises(api.EvnResponseError):
        await client.fetch_snapshot(PERSON)
    assert session.calls[index]["url"].endswith(path)
    session.done()


@pytest.mark.parametrize(
    "index",
    [3, 4, 5, 6, 7, 8, 9, 10, 12],
)
@pytest.mark.parametrize("status", [403, 503, 302, 417])
async def test_snapshot_required_section_failure_aborts(
    index: int, status: int
) -> None:
    session = Session(
        contracts(PERSON), config(), *snapshot_replies(PERSON)[: index - 2]
    )
    session.replies.append(Reply(status=status))
    client = client_for(session)
    with pytest.raises(api.EvnError):
        await client.fetch_snapshot(PERSON)
    session.done()


async def test_snapshot_reads_current_invoices_not_the_empty_payment_list() -> None:
    session = Session(contracts(PERSON), config(), *snapshot_replies(PERSON))
    await client_for(session).fetch_snapshot(PERSON)
    requested = [call["url"].rsplit("/api/evn/", 1)[-1] for call in session.calls[3:]]
    assert requested[:9] == [
        "customers/diemdo",
        "tracuu/diennangthang",
        "tracuu/diennangngay",
        "tracuu/chisothang",
        "tracuu/chisongay",
        "customers/info",
        "tracuu/hoadon",
        "tracuu/lichsu-hoadon",
        "thanhtoan/danhsach-nganhang",
    ]
    assert requested[-1] == "tracuu/ngungcapdien"
    assert not any("hoadon-thanhtoan" in call["url"] for call in session.calls)
    session.done()


async def test_snapshot_reading_windows_are_one_point_back_and_last_days() -> None:
    session = Session(contracts(PERSON), config(), *snapshot_replies(PERSON))
    await client_for(session).fetch_snapshot(PERSON)
    assert session.calls[6]["json"] == {
        "MA_DVIQLY": PERSON.management_unit,
        "MA_DDO": POINT,
        "MA_KHANG": PERSON.code,
        "TU_THANG_NAM": "12/2024",
        "DEN_THANG_NAM": "01/2026",
    }
    assert session.calls[7]["json"] == {
        "MA_DVIQLY": PERSON.management_unit,
        "MA_DDO": POINT,
        "TU_NGAY": "01/12/2025",
        "DEN_NGAY": "31/12/2025",
    }
    assert session.calls[10]["json"] == {
        "TU_THANG_NAM": "12/2024",
        "DEN_THANG_NAM": "01/2026",
    }
    assert session.calls[12]["json"] == {
        "TU_NGAY": "01/01/2026",
        "DEN_NGAY": "15/01/2026",
    }
    for index in (3, 8, 9, 11):
        assert "json" not in session.calls[index]
    session.done()


async def test_snapshot_info_keeps_only_bounded_string_fields() -> None:
    row = {
        "maKhang": PERSON.code,
        "maDviqly": PERSON.management_unit,
        "tenKhang": "Synthetic name A",
        "maHdong": "OFFLINE-CONTRACT",
        "diaChi": "Offline address",
        "userId": "OFFLINE-USER",
        "dthoai": None,
        "loaiKhang": 3,
        "powerAlert": True,
        "thoigian": "x" * 400,
        "maDviCaptct": "PB\r\nInjected",
        "token": "offline-secret-token",
        "secret": "offline-secret-value",
    }
    session = Session(Reply([row]), config(), *snapshot_replies(PERSON))
    snapshot = await client_for(session).fetch_snapshot(PERSON)
    assert snapshot.info == {
        "maKhang": PERSON.code,
        "maDviqly": PERSON.management_unit,
        "tenKhang": "Synthetic name A",
        "maHdong": "OFFLINE-CONTRACT",
        "diaChi": "Offline address",
        "userId": "OFFLINE-USER",
    }
    assert "offline-secret-token" not in str(snapshot.info)
    session.done()


async def test_snapshot_new_sections_default_when_constructed_directly() -> None:
    snapshot = api.Snapshot(
        PERSON,
        "PB",
        [],
        {},
        {},
        [],
        [],
        NOW,
    )
    assert snapshot.info == {}
    assert snapshot.contracts == []
    assert snapshot.monthly_readings == {}
    assert snapshot.daily_readings == {}
    assert snapshot.paid_invoices == []
    assert snapshot.banks == []
