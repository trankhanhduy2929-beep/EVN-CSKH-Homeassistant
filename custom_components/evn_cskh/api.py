from __future__ import annotations

import asyncio
import base64
import binascii
import json
import re
from collections.abc import Callable, Mapping
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote, unquote, urlsplit
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientSession, ClientTimeout

CENTRAL_BASE = "https://cskh.evn.com.vn/cskh/v1"

_REGION_HOSTS = {
    "PA": "apicskhevn.npc.com.vn",
    "PB": "api.cskh.evnspc.vn",
    "PC": "cskh-api.cpc.vn",
    "HN": "gwkong.evnhanoi.vn",
    "PE": "openapi.evnhcmc.vn",
}
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_PDF_BYTES = 16 * 1024 * 1024
_MAX_PDF_RESPONSE_BYTES = 24 * 1024 * 1024
_INVOICE_PATHS = {
    "invoice": "/api/evn/tracuu/file-hoadon",
    "statement": "/api/evn/tracuu/file-bangke-hoadon",
    "notice": "/api/evn/tracuu/file-thongbao-hoadon",
}
_REQUEST_TIMEOUT = 30.0
_LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


class EvnError(Exception):
    _message = "EVN operation failed."

    def __init__(self) -> None:
        super().__init__(self._message)


class EvnConnectionError(EvnError):
    _message = "EVN service is temporarily unavailable."


class EvnAuthError(EvnError):
    _message = "EVN authentication failed."


class EvnResponseError(EvnError):
    _message = "EVN returned an invalid response."


class EvnUserActionRequired(EvnAuthError):
    _message = "Account action is required in the official EVN application."


class _Unauthorized(EvnAuthError):
    pass


def _string(value: Any, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise EvnResponseError()
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise EvnResponseError()
    return value


def _token(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise EvnAuthError()
    if any(not 33 <= ord(character) <= 126 for character in value):
        raise EvnAuthError()
    return value


def _join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def _regional_base(region: Any, value: Any) -> str:
    if not isinstance(region, str) or region not in _REGION_HOSTS:
        raise EvnResponseError()
    if not isinstance(value, str) or not value:
        raise EvnResponseError()
    if any(not 33 <= ord(character) <= 126 for character in value):
        raise EvnResponseError()
    if any(character in value for character in ("\\", "?", "#")):
        raise EvnResponseError()
    try:
        parsed = urlsplit(value)
        host = _REGION_HOSTS[region]
        if (
            parsed.scheme != "https"
            or parsed.hostname != host
            or parsed.netloc not in (host, host + ":443")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.query
            or parsed.fragment
        ):
            raise EvnResponseError()
        path = unquote(parsed.path, errors="strict")
        if (
            "\\" in path
            or any(ord(character) < 32 or ord(character) == 127 for character in path)
            or any(part in (".", "..") for part in path.split("/"))
        ):
            raise EvnResponseError()
    except (ValueError, UnicodeError):
        raise EvnResponseError() from None
    return value.rstrip("/")


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise EvnResponseError()
    return value


@dataclass(frozen=True, repr=False)
class Customer:
    code: str
    management_unit: str
    name: str = ""
    contract: str = ""


@dataclass(repr=False)
class Snapshot:
    customer: Customer
    region: str
    measurement_points: list[dict[str, Any]]
    monthly: dict[str, list[dict[str, Any]]]
    daily: dict[str, list[dict[str, Any]]]
    invoices: list[dict[str, Any]]
    outages: list[dict[str, Any]]
    fetched_at: datetime


@dataclass(repr=False)
class DetailSnapshot:
    customer: Customer
    region: str
    point: str
    start: date
    end: date
    monthly: list[dict[str, Any]]
    daily: list[dict[str, Any]]
    monthly_readings: list[dict[str, Any]]
    daily_readings: list[dict[str, Any]]
    invoices: list[dict[str, Any]]
    fetched_at: datetime


@dataclass(frozen=True, repr=False)
class TokenState:
    access_token: str
    refresh_token: str
    customer_code: str | None = None
    management_unit: str | None = None

    def __post_init__(self) -> None:
        _token(self.access_token)
        _token(self.refresh_token)
        for value in (self.customer_code, self.management_unit):
            if value is not None:
                try:
                    _string(value)
                except EvnResponseError:
                    raise EvnAuthError() from None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "customer_code": self.customer_code,
            "management_unit": self.management_unit,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TokenState:
        if not isinstance(value, Mapping):
            raise EvnAuthError()
        return cls(
            access_token=_token(value.get("access_token")),
            refresh_token=_token(value.get("refresh_token")),
            customer_code=value.get("customer_code"),
            management_unit=value.get("management_unit"),
        )


def _owned_rows(
    value: Any, customer: Customer, point: str | None = None
) -> list[dict[str, Any]]:
    rows = _rows(value)
    for row in rows:
        for field, expected in (
            ("MA_KHANG", customer.code),
            ("MA_DVIQLY", customer.management_unit),
        ):
            if field in row and _string(row[field]) != expected:
                raise EvnResponseError()
        if point is not None and "MA_DDO" in row and _string(row["MA_DDO"]) != point:
            raise EvnResponseError()
    return rows


def _invoice_id(value: Any) -> str:
    if type(value) is int and 0 < value < 10**128:
        return str(value)
    if (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is not None
        and value.strip("0")
    ):
        return value
    raise EvnResponseError()


def _invoice_key(invoice: dict[str, Any]) -> tuple[str, str | None]:
    original = _invoice_id(invoice.get("ID_HDON"))
    adjusted = invoice.get("ID_HDON_DC")
    return original, None if adjusted is None or adjusted == "" else _invoice_id(
        adjusted
    )


def _invoice_number(value: Any, maximum: int) -> int:
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,4}", value) is not None:
        value = int(value)
    if type(value) is not int or not 1 <= value <= maximum:
        raise EvnResponseError()
    return value


def _invoice_body(invoice: dict[str, Any]) -> dict[str, Any]:
    original, adjusted = _invoice_key(invoice)
    kind = invoice.get("LOAI_HDON")
    if (
        not isinstance(kind, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}", kind) is None
    ):
        raise EvnResponseError()
    return {
        "ID_HDON": adjusted if adjusted is not None else original,
        "LOAI_PSINH": "TATCA",
        "THANG": _invoice_number(invoice.get("THANG"), 12),
        "NAM": _invoice_number(invoice.get("NAM"), 9999),
        "LOAI_HDON": kind,
    }


def _pdf_bytes(value: Any) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _MAX_PDF_RESPONSE_BYTES
        or len(value) % 4
    ):
        raise EvnResponseError()
    padding = len(value) - len(value.rstrip("="))
    if padding > 2 or len(value) // 4 * 3 - padding > _MAX_PDF_BYTES:
        raise EvnResponseError()
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise EvnResponseError() from None
    if (
        len(decoded) > _MAX_PDF_BYTES
        or base64.b64encode(decoded).decode("ascii") != value
        or re.match(rb"%PDF-[0-9]\.[0-9](?:\r\n|\r|\n)", decoded) is None
        or re.search(rb"(?:\r\n|\r|\n)%%EOF[ \t\r\n\f]*\Z", decoded[-1024:]) is None
    ):
        raise EvnResponseError()
    return decoded


class EvnClient:
    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        device_id: str,
        *,
        tokens: TokenState | None = None,
        on_tokens: Callable[[TokenState], None] | None = None,
    ) -> None:
        if (
            not isinstance(device_id, str)
            or re.fullmatch(r"[0-9a-fA-F]{16}", device_id) is None
        ):
            raise EvnError()
        if tokens is not None and not isinstance(tokens, TokenState):
            raise EvnAuthError()
        self._session = session
        self._username = username
        self._password = password
        self._device_id = device_id
        self._tokens = tokens
        self._on_tokens = on_tokens
        self._lock = asyncio.Lock()
        self._auth_failed = False
        self._customers: list[Customer] | None = None
        self._regions: dict[str, str] | None = None
        self._issued_invoices: dict[
            tuple[str, str], dict[tuple[str, str | None], dict[str, Any]]
        ] = {}

    @property
    def tokens(self) -> TokenState | None:
        return self._tokens

    def _store_tokens(self, tokens: TokenState) -> None:
        self._tokens = tokens
        if self._on_tokens is not None:
            with suppress(Exception):
                self._on_tokens(tokens)
                return
            raise EvnError() from None

    async def _send(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, Any] | None = None,
        access_token: str | None = None,
        auth_response: bool = False,
        device_header: bool = False,
        max_response_bytes: int = _MAX_RESPONSE_BYTES,
    ) -> Any:
        if type(max_response_bytes) is not int or max_response_bytes not in (
            _MAX_RESPONSE_BYTES,
            _MAX_PDF_RESPONSE_BYTES,
        ):
            raise EvnResponseError()
        headers = {"Accept": "application/json"}
        if access_token is not None:
            headers["Authorization"] = "Bearer " + access_token
        if device_header:
            headers["X-deviceId"] = self._device_id
        options: dict[str, Any] = {}
        if body is not None:
            options["json"] = body
        else:
            options["skip_auto_headers"] = {"Content-Type"}
        try:
            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=ClientTimeout(
                        total=_REQUEST_TIMEOUT, connect=10, sock_read=20
                    ),
                    allow_redirects=False,
                    raise_for_status=False,
                    **options,
                ) as response:
                    if response.status == 401:
                        raise _Unauthorized()
                    if response.status == 403:
                        raise EvnAuthError()
                    if response.status in (408, 429) or 500 <= response.status <= 599:
                        raise EvnConnectionError()
                    rejected = auth_response and response.status == 417
                    if response.status not in (200, 400) and not rejected:
                        raise EvnResponseError()
                    if (
                        response.content_length is not None
                        and response.content_length > max_response_bytes
                    ):
                        raise EvnResponseError()
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        if len(raw) + len(chunk) > max_response_bytes:
                            raise EvnResponseError()
                        raw.extend(chunk)
                    payload = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError):
            raise EvnResponseError() from None
        except (ClientError, OSError, TimeoutError, RuntimeError):
            raise EvnConnectionError() from None
        if not isinstance(payload, dict) or type(payload.get("success")) is not bool:
            raise EvnResponseError()
        if payload["success"] is not True:
            if auth_response:
                raise EvnAuthError()
            raise EvnResponseError()
        if rejected:
            raise EvnResponseError()
        if "data" not in payload:
            if (
                auth_response
                and method == "POST"
                and url == _join_url(CENTRAL_BASE, "/auth/checkAccInUse")
            ):
                return None
            raise EvnResponseError()
        return payload["data"]

    async def login(self) -> None:
        async with self._lock:
            await self._login_locked()

    async def _login_locked(self) -> None:
        self._issued_invoices.clear()
        try:
            if (
                not isinstance(self._username, str)
                or not self._username
                or not isinstance(self._password, str)
                or not self._password
            ):
                raise EvnAuthError()
            account = await self._send(
                "POST",
                _join_url(CENTRAL_BASE, "/auth/checkAccInUse"),
                body={"phone": self._username},
                auth_response=True,
            )
            if account is None:
                raise EvnUserActionRequired()
            if not isinstance(account, dict):
                raise EvnResponseError()
            if "isDefaultPassVneid" in account:
                if type(account["isDefaultPassVneid"]) is not bool:
                    raise EvnResponseError()
                if account["isDefaultPassVneid"]:
                    raise EvnUserActionRequired()
            canonical_username = account.get("username")
            if canonical_username is None or canonical_username == "":
                username = self._username
            else:
                username = _string(canonical_username)
                if any(character.isspace() for character in username):
                    raise EvnResponseError()
            data = await self._send(
                "POST",
                _join_url(CENTRAL_BASE, "/auth/login"),
                body={
                    "username": username,
                    "password": self._password,
                    "deviceInfo": {
                        "deviceId": self._device_id,
                        "deviceType": "Home Assistant",
                    },
                },
                auth_response=True,
            )
            if not isinstance(data, dict):
                raise EvnAuthError()
            tokens = TokenState(
                _token(data.get("accessToken")), _token(data.get("refreshToken"))
            )
        except (EvnUserActionRequired, EvnResponseError):
            self._auth_failed = True
            raise
        except EvnAuthError:
            self._auth_failed = True
            raise EvnAuthError() from None
        self._auth_failed = False
        self._customers = None
        self._store_tokens(tokens)

    async def _ensure_login_locked(self) -> None:
        if self._auth_failed:
            raise EvnAuthError()
        if self._tokens is None:
            await self._login_locked()

    async def _refresh_locked(self) -> None:
        previous = self._tokens
        if previous is None:
            self._auth_failed = True
            raise EvnAuthError()
        try:
            data = await self._send(
                "POST",
                _join_url(CENTRAL_BASE, "/auth/refresh"),
                body={
                    "refreshToken": previous.refresh_token,
                    "maKhachhang": previous.customer_code,
                    "donviquanly": previous.management_unit,
                },
                auth_response=True,
                device_header=True,
            )
            if not isinstance(data, dict):
                raise EvnAuthError()
            refresh_token = data.get("refreshToken")
            if refresh_token is None or refresh_token == "":
                refresh_token = previous.refresh_token
            tokens = TokenState(
                _token(data.get("accessToken")),
                _token(refresh_token),
                previous.customer_code,
                previous.management_unit,
            )
        except (EvnAuthError, EvnResponseError):
            self._auth_failed = True
            raise EvnAuthError() from None
        self._store_tokens(tokens)

    async def _authenticated_locked(
        self,
        method: str,
        base: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        max_response_bytes: int = _MAX_RESPONSE_BYTES,
    ) -> Any:
        for attempt in range(2):
            if self._tokens is None or self._auth_failed:
                raise EvnAuthError()
            try:
                return await self._send(
                    method,
                    _join_url(base, path),
                    body=body,
                    access_token=self._tokens.access_token,
                    max_response_bytes=max_response_bytes,
                )
            except _Unauthorized:
                if attempt:
                    self._auth_failed = True
                    raise EvnAuthError() from None
                await self._refresh_locked()
            except EvnAuthError:
                self._auth_failed = True
                raise EvnAuthError() from None
        raise EvnAuthError()

    async def customers(self) -> list[Customer]:
        async with self._lock:
            await self._ensure_login_locked()
            return list(await self._customers_locked())

    async def _customers_locked(self) -> list[Customer]:
        if self._customers is None:
            data = await self._authenticated_locked("GET", CENTRAL_BASE, "/user/me")
            customers: dict[tuple[str, str], Customer] = {}
            for row in _rows(data):
                customer = Customer(
                    code=_string(row.get("maKhang")),
                    management_unit=_string(row.get("maDviqly")),
                    name=_string(row.get("tenKhang", ""), empty=True),
                    contract=_string(row.get("maHdong", ""), empty=True),
                )
                if customer.code in (".", ".."):
                    raise EvnResponseError()
                customers.setdefault(
                    (customer.code, customer.management_unit), customer
                )
            self._customers = list(customers.values())
        return self._customers

    async def _regions_locked(self) -> dict[str, str]:
        if self._regions is None:
            data = await self._send("GET", _join_url(CENTRAL_BASE, "/public/allconfig"))
            regions: dict[str, str] = {}
            for row in _rows(data):
                if _string(row.get("key")) != "URL_API":
                    continue
                region = _string(row.get("subdivisionid"))
                base = _regional_base(region, row.get("value"))
                if region in regions and regions[region] != base:
                    raise EvnResponseError()
                regions[region] = base
            self._regions = regions
        return self._regions

    async def _authorized_customer_locked(self, customer: Customer) -> Customer:
        customers = await self._customers_locked()
        if not isinstance(customer, Customer):
            raise EvnAuthError()
        authorized = next(
            (
                known
                for known in customers
                if (known.code, known.management_unit)
                == (customer.code, customer.management_unit)
            ),
            None,
        )
        if authorized is None:
            raise EvnAuthError()
        return authorized

    async def _select_customer_locked(self, customer: Customer) -> tuple[str, str]:
        regions = await self._regions_locked()
        selected = await self._authenticated_locked(
            "GET", CENTRAL_BASE, "/user/switch/" + quote(customer.code, safe="")
        )
        if not isinstance(selected, dict) or not isinstance(selected.get("data"), dict):
            raise EvnResponseError()
        context = selected["data"]
        region = _string(context.get("maDviCaptct"))
        for field, expected in (
            ("maKhang", customer.code),
            ("maDviqly", customer.management_unit),
        ):
            if field in context and _string(context[field]) != expected:
                raise EvnResponseError()
        if self._tokens is None:
            raise EvnAuthError()
        self._store_tokens(
            TokenState(
                _token(selected.get("accessToken")),
                self._tokens.refresh_token,
                customer.code,
                customer.management_unit,
            )
        )
        if region not in regions:
            raise EvnResponseError()
        return region, regions[region]

    async def fetch_snapshot(self, customer: Customer) -> Snapshot:
        async with self._lock:
            await self._ensure_login_locked()
            customer = await self._authorized_customer_locked(customer)
            region, base = await self._select_customer_locked(customer)
            today = datetime.now(_LOCAL_TIMEZONE).date()
            previous_month = today.replace(day=1) - timedelta(days=1)
            points = _owned_rows(
                await self._authenticated_locked(
                    "GET", base, "/api/evn/customers/diemdo"
                ),
                customer,
            )
            point_codes = [_string(point.get("MA_DDO")) for point in points]
            if len(set(point_codes)) != len(point_codes):
                raise EvnResponseError()
            monthly: dict[str, list[dict[str, Any]]] = {}
            daily: dict[str, list[dict[str, Any]]] = {}
            for point in point_codes:
                monthly[point] = _owned_rows(
                    await self._authenticated_locked(
                        "POST",
                        base,
                        "/api/evn/tracuu/diennangthang",
                        {
                            "MA_DVIQLY": customer.management_unit,
                            "MA_DDO": point,
                            "MA_KHANG": customer.code,
                            "TU_THANG_NAM": previous_month.strftime("%m/%Y"),
                            "DEN_THANG_NAM": today.strftime("%m/%Y"),
                        },
                    ),
                    customer,
                    point,
                )
                daily[point] = _owned_rows(
                    await self._authenticated_locked(
                        "POST",
                        base,
                        "/api/evn/tracuu/diennangngay",
                        {
                            "MA_DVIQLY": customer.management_unit,
                            "MA_DDO": point,
                            "TU_NGAY": (today - timedelta(days=7)).strftime("%d/%m/%Y"),
                            "DEN_NGAY": (today - timedelta(days=1)).strftime(
                                "%d/%m/%Y"
                            ),
                        },
                    ),
                    customer,
                    point,
                )
            invoices = _owned_rows(
                await self._authenticated_locked(
                    "POST", base, "/api/evn/tracuu/hoadon-thanhtoan"
                ),
                customer,
            )
            outages = _owned_rows(
                await self._authenticated_locked(
                    "POST",
                    base,
                    "/api/evn/tracuu/ngungcapdien",
                    {
                        "TU_NGAY": today.strftime("%d/%m/%Y"),
                        "DEN_NGAY": (today + timedelta(days=14)).strftime("%d/%m/%Y"),
                    },
                ),
                customer,
            )
            return Snapshot(
                customer=customer,
                region=region,
                measurement_points=points,
                monthly=monthly,
                daily=daily,
                invoices=invoices,
                outages=outages,
                fetched_at=datetime.now(UTC),
            )

    async def details(
        self, customer: Customer, point: str, start: date, end: date
    ) -> DetailSnapshot:
        async with self._lock:
            today = datetime.now(_LOCAL_TIMEZONE).date()
            if (
                type(start) is not date
                or type(end) is not date
                or start > end
                or end > today
                or (end - start).days > 366
                or start < today - timedelta(days=5 * 366)
            ):
                raise EvnResponseError()
            point = _string(point)
            if not isinstance(customer, Customer):
                raise EvnAuthError()
            await self._ensure_login_locked()
            customer = await self._authorized_customer_locked(customer)
            owner = (customer.code, customer.management_unit)
            self._issued_invoices.pop(owner, None)
            region, base = await self._select_customer_locked(customer)
            points = _owned_rows(
                await self._authenticated_locked(
                    "GET", base, "/api/evn/customers/diemdo"
                ),
                customer,
            )
            point_codes = [_string(row.get("MA_DDO")) for row in points]
            if len(set(point_codes)) != len(point_codes):
                raise EvnResponseError()
            if point not in point_codes:
                raise EvnAuthError()
            monthly_body = {
                "MA_DVIQLY": customer.management_unit,
                "MA_DDO": point,
                "MA_KHANG": customer.code,
                "TU_THANG_NAM": start.strftime("%m/%Y"),
                "DEN_THANG_NAM": end.strftime("%m/%Y"),
            }
            monthly = _owned_rows(
                await self._authenticated_locked(
                    "POST", base, "/api/evn/tracuu/diennangthang", monthly_body
                ),
                customer,
                point,
            )
            daily_end = min(end, today - timedelta(days=1))
            daily_start = max(start, daily_end - timedelta(days=30))
            daily: list[dict[str, Any]] = []
            daily_readings: list[dict[str, Any]] = []
            daily_body = {
                "MA_DVIQLY": customer.management_unit,
                "MA_DDO": point,
                "TU_NGAY": daily_start.strftime("%d/%m/%Y"),
                "DEN_NGAY": daily_end.strftime("%d/%m/%Y"),
            }
            if daily_start <= daily_end:
                daily = _owned_rows(
                    await self._authenticated_locked(
                        "POST", base, "/api/evn/tracuu/diennangngay", daily_body
                    ),
                    customer,
                    point,
                )
            monthly_readings = _owned_rows(
                await self._authenticated_locked(
                    "POST", base, "/api/evn/tracuu/chisothang", monthly_body
                ),
                customer,
                point,
            )
            if daily_start <= daily_end:
                daily_readings = _owned_rows(
                    await self._authenticated_locked(
                        "POST",
                        base,
                        "/api/evn/tracuu/chisongay",
                        daily_body
                        | {
                            "TU_NGAY": (daily_start - timedelta(days=1)).strftime(
                                "%d/%m/%Y"
                            )
                        },
                    ),
                    customer,
                    point,
                )
            history = _owned_rows(
                await self._authenticated_locked(
                    "POST",
                    base,
                    "/api/evn/tracuu/lichsu-hoadon",
                    {
                        "TU_THANG_NAM": monthly_body["TU_THANG_NAM"],
                        "DEN_THANG_NAM": monthly_body["DEN_THANG_NAM"],
                    },
                ),
                customer,
            )
            invoices: dict[tuple[str, str | None], dict[str, Any]] = {}
            for row in history:
                key = _invoice_key(row)
                invoices[key] = invoices.get(key, {}) | row
            current = _owned_rows(
                await self._authenticated_locked(
                    "POST", base, "/api/evn/tracuu/hoadon"
                ),
                customer,
            )
            for row in current:
                key = _invoice_key(row)
                invoices[key] = invoices.get(key, {}) | row
            snapshot = DetailSnapshot(
                customer=customer,
                region=region,
                point=point,
                start=start,
                end=end,
                monthly=monthly,
                daily=daily,
                monthly_readings=monthly_readings,
                daily_readings=daily_readings,
                invoices=list(invoices.values()),
                fetched_at=datetime.now(UTC),
            )
            self._issued_invoices[owner] = deepcopy(invoices)
            return snapshot

    async def invoice_pdf(
        self, customer: Customer, invoice: dict[str, Any], kind: str = "invoice"
    ) -> bytes:
        async with self._lock:
            if not isinstance(kind, str) or kind not in _INVOICE_PATHS:
                raise EvnResponseError()
            if (
                not isinstance(customer, Customer)
                or not isinstance(customer.code, str)
                or not isinstance(customer.management_unit, str)
            ):
                raise EvnAuthError()
            _owned_rows([invoice], customer)
            body = _invoice_body(invoice)
            issued = self._issued_invoices.get(
                (customer.code, customer.management_unit), {}
            ).get(_invoice_key(invoice))
            if issued is None or issued != invoice:
                raise EvnAuthError()
            await self._ensure_login_locked()
            customer = await self._authorized_customer_locked(customer)
            _, base = await self._select_customer_locked(customer)
            return _pdf_bytes(
                await self._authenticated_locked(
                    "POST",
                    base,
                    _INVOICE_PATHS[kind],
                    body,
                    max_response_bytes=_MAX_PDF_RESPONSE_BYTES,
                )
            )
