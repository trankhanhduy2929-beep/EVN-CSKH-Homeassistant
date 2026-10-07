from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tokenize
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Self

import pytest
from aiohttp import ClientSession

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "poc" / "evn_cskh.py"
_SPEC = importlib.util.spec_from_file_location("_evn_cskh_poc_offline", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
poc = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = poc
_SPEC.loader.exec_module(poc)
api = poc.api


def write_json(path: Path, data: Any, mode: int = 0o600) -> None:
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
    path.chmod(mode)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_outbound(monkeypatch: pytest.MonkeyPatch) -> None:
    async def blocked_request(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound requests are disabled")

    def blocked_socket(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Outbound connections are disabled")

    monkeypatch.setattr(ClientSession, "_request", blocked_request)
    monkeypatch.setattr(socket.socket, "connect", blocked_socket)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked_socket)
    monkeypatch.setattr(socket, "create_connection", blocked_socket)
    monkeypatch.setattr(socket, "getaddrinfo", blocked_socket)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    directory = tmp_path / "poc"
    directory.mkdir()
    monkeypatch.setattr(poc, "ROOT", tmp_path)
    monkeypatch.setattr(poc, "POC_DIR", directory)
    username = "Offline-" + secrets.token_hex(8)
    password = secrets.token_urlsafe(24) + " &+%=?/'\"\\\n mật khẩu "
    credentials = directory / "credentials.json"
    write_json(credentials, {"username": "  " + username + "  ", "password": password})
    return SimpleNamespace(
        root=tmp_path,
        directory=directory,
        credentials=credentials,
        session=directory / "session.json",
        raw=directory / "capture.json",
        username=username,
        password=password,
        account_hash=hashlib.sha256(username.lower().encode()).hexdigest(),
    )


def seed_session(workspace: SimpleNamespace, *, tokens: Any = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "device_id": secrets.token_hex(8),
        "account_hash": workspace.account_hash,
    }
    if tokens is not None:
        data["tokens"] = tokens.to_dict()
    write_json(workspace.session, data)
    return data


class OfflineSession:
    def __init__(self, **options: Any) -> None:
        assert options == {"trust_env": False}
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True


class FakeClient:
    def __init__(
        self,
        session: OfflineSession,
        username: str,
        password: str,
        device_id: str,
        *,
        tokens: Any = None,
        on_tokens: Callable[[Any], None],
        harness: SimpleNamespace,
    ) -> None:
        self.session = session
        self.username, self.password, self.device_id = username, password, device_id
        self.tokens, self.on_tokens, self.harness = tokens, on_tokens, harness
        harness.instances.append(self)
        saved = read_json(harness.workspace.session)
        assert saved["device_id"] == device_id
        assert saved["account_hash"] == harness.workspace.account_hash
        assert stat.S_IMODE(harness.workspace.session.stat().st_mode) == 0o600

    def store(self, tokens: Any) -> None:
        self.tokens = tokens
        self.on_tokens(tokens)
        saved = read_json(self.harness.workspace.session)
        assert saved["tokens"] == tokens.to_dict()
        assert stat.S_IMODE(self.harness.workspace.session.stat().st_mode) == 0o600
        self.harness.persisted.append(saved)

    async def login(self) -> None:
        self.harness.events.append("login")
        if self.harness.failure is not None:
            raise self.harness.failure
        self.store(self.harness.login_tokens)

    async def customers(self) -> list[Any]:
        if self.tokens is None:
            await self.login()
        self.harness.events.append("customers")
        if self.harness.customer_failure is not None:
            raise self.harness.customer_failure
        if self.harness.rotate_discovery is not None:
            self.store(self.harness.rotate_discovery)
        return list(self.harness.inventory)

    async def fetch_snapshot(self, customer: Any) -> Any:
        assert customer in self.harness.inventory
        self.harness.events.append("snapshot")
        self.harness.fetched.append(customer)
        if self.harness.snapshot_failure is not None:
            raise self.harness.snapshot_failure
        if self.harness.rotate_snapshot is not None:
            self.store(self.harness.rotate_snapshot)
        return self.harness.snapshots[(customer.code, customer.management_unit)]


def snapshot(customer: Any, number: int) -> Any:
    point = "OFFLINE-POINT-" + str(number)
    pii = {
        "name": customer.name,
        "address": "OFFLINE-PRIVATE-ADDRESS",
        "phone": "OFFLINE-PRIVATE-PHONE",
        "MA_KHANG": customer.code,
        "MA_DVIQLY": customer.management_unit,
    }
    return api.Snapshot(
        customer=customer,
        region="PB",
        measurement_points=[{"MA_DDO": point, **pii}],
        monthly={
            point: [
                {
                    "NAM": 2026,
                    "THANG": 10,
                    "KY": 1,
                    "SO_CTO": "OFFLINE-METER",
                    "DIEN_TTHU": 123.5,
                    **pii,
                }
            ]
        },
        daily={
            point: [
                {
                    "NGAY_HTHI": "06/10/2026",
                    "BCS": "KT",
                    "SO_CTO": "OFFLINE-METER",
                    "DIEN_TTHU": 4.25,
                    **pii,
                }
            ]
        },
        invoices=[
            {
                "ID_HDON": "OFFLINE-PRIVATE-INVOICE",
                "TTRANG_TTOAN": "CHUATT",
                "TONG_NO": -125000,
                **pii,
            }
        ],
        outages=[
            {
                "TGIAN_BDAU": "08/10/2026 08:00",
                "TGIAN_KTHUC": "08/10/2026 10:00",
                "KHUVUCMATDIEN": "OFFLINE-PRIVATE-AREA",
                "LY_DO": "OFFLINE-PRIVATE-REASON",
                **pii,
            }
        ],
        fetched_at=datetime(2026, 10, 7, 5, tzinfo=UTC),
    )


@pytest.fixture
def harness(
    workspace: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    inventory = [
        api.Customer(
            "OFFLINE-CODE-1",
            "OFFLINE-UNIT-1",
            "OFFLINE-PRIVATE-NAME-1",
            "OFFLINE-PRIVATE-CONTRACT-1",
        ),
        api.Customer(
            "OFFLINE-CODE-2",
            "OFFLINE-UNIT-2",
            "OFFLINE-PRIVATE-NAME-2",
            "OFFLINE-PRIVATE-CONTRACT-2",
        ),
    ]
    result = SimpleNamespace(
        workspace=workspace,
        inventory=inventory,
        snapshots={
            (customer.code, customer.management_unit): snapshot(customer, index)
            for index, customer in enumerate(inventory, start=1)
        },
        login_tokens=api.TokenState(
            secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        ),
        instances=[],
        events=[],
        fetched=[],
        persisted=[],
        failure=None,
        customer_failure=None,
        snapshot_failure=None,
        rotate_discovery=None,
        rotate_snapshot=None,
    )

    def factory(*args: Any, **kwargs: Any) -> FakeClient:
        return FakeClient(*args, **kwargs, harness=result)

    monkeypatch.setattr(poc, "ClientSession", OfflineSession)
    monkeypatch.setattr(poc, "EvnClient", factory)
    return result


def assert_private_absent(
    output: str, workspace: SimpleNamespace, harness: SimpleNamespace
) -> None:
    for secret in (
        workspace.username,
        workspace.password,
        workspace.account_hash,
        harness.login_tokens.access_token,
        harness.login_tokens.refresh_token,
        "OFFLINE-PRIVATE",
        "OFFLINE-METER",
    ):
        assert secret not in output
    if workspace.session.exists() and not workspace.session.is_symlink():
        assert read_json(workspace.session)["device_id"] not in output


def test_help_and_defaults_are_offline(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for arguments in (
        ["--help"],
        ["login", "--help"],
        ["customers", "--help"],
        ["test", "--help"],
    ):
        assert poc.main(arguments) == 0
        output = capsys.readouterr()
        assert "--credentials" in output.out
        assert "--session" in output.out
        assert "--save-raw" in output.out
        assert not output.err
    assert not harness.instances
    assert not workspace.session.exists()
    options = poc._parser().parse_args(["test"])
    assert options.credentials == "poc/credentials.json"
    assert options.session == "poc/session.json"
    assert options.customer is None
    assert options.show_identifiers is False
    assert options.save_raw is None


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["unknown"],
        ["test", "--unknown"],
        ["--credentials"],
        ["test", "--credentials"],
        ["test", "--session"],
        ["test", "--customer"],
        ["test", "--save-raw"],
        ["test", "extra"],
        ["--show-identifiers"],
        ["test", "--show-identifiers", "true"],
        ["test", "--cred", "poc/credentials.json"],
    ],
)
def test_argument_errors_do_not_create_session_or_network(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(arguments) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "Invalid arguments" in output.err
    assert not harness.instances
    assert not workspace.session.exists()


def test_argparse_never_echoes_untrusted_values(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = harness.login_tokens.access_token
    for arguments in ([secret], ["test", "--unexpected=" + secret], ["test", secret]):
        assert poc.main(arguments) == 2
        output = capsys.readouterr()
        assert secret not in output.out + output.err
    assert not harness.instances


@pytest.mark.parametrize(
    "arguments",
    [
        ["login", "--save-raw", "poc/capture.json"],
        ["customers", "--save-raw", "poc/capture.json"],
        ["login", "--customer", "OFFLINE-CODE-1"],
        ["test", "--customer", " "],
    ],
)
def test_incompatible_flags_fail_locally(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(arguments) == 1
    output = capsys.readouterr()
    assert "Invalid command options" in output.err
    assert not output.out
    assert not harness.instances
    assert not workspace.session.exists()


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o660, 0o666, 0o400, 0o700])
@pytest.mark.parametrize("kind", ["credentials", "session"])
def test_secret_permissions_refused_without_disclosure(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    mode: int,
    kind: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if kind == "session":
        seed_session(workspace, tokens=harness.login_tokens)
    path = getattr(workspace, kind)
    path.chmod(mode)
    before = path.read_bytes()
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert "mode-600" in output.err
    assert_private_absent(output.out + output.err, workspace, harness)
    assert path.read_bytes() == before
    assert not harness.instances


@pytest.mark.parametrize("kind", ["credentials", "session"])
@pytest.mark.parametrize(
    "content", [b"not-json", b"[]", b"null", b"\xff", b"{" + b" " * 65536]
)
def test_secret_schema_and_size_fail_offline(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    kind: str,
    content: bytes,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = getattr(workspace, kind)
    path.write_bytes(content)
    path.chmod(0o600)
    assert poc.main(["customers"]) == 1
    output = capsys.readouterr()
    assert "64 KiB" in output.err
    assert not output.out
    assert not harness.instances
    assert path.read_bytes() == content


@pytest.mark.parametrize("kind", ["credentials", "session"])
def test_exact_64k_secret_file_is_accepted(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    kind: str,
) -> None:
    if kind == "session":
        seed_session(workspace, tokens=harness.login_tokens)
    path = getattr(workspace, kind)
    content = path.read_bytes()
    path.write_bytes(content + b" " * (65536 - len(content)))
    path.chmod(0o600)
    assert poc.main(["customers"]) == 0
    assert harness.events == (
        ["customers"] if kind == "session" else ["login", "customers"]
    )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"username": ""},
        {"username": "", "password": ""},
        {"username": " ", "password": "synthetic-pass"},
        {"username": "synthetic-user", "password": "\n\t "},
        {"username": "YOUR_USERNAME", "password": "synthetic-pass"},
        {"username": "synthetic-user", "password": "<YOUR_PASSWORD>"},
        {"username": "synthetic-user", "password": "CHANGE_ME"},
        {"username": "<username>", "password": "<password>"},
        {"username": "<YOUR_EVN_USERNAME>", "password": "synthetic-pass"},
        {"username": "ENTER_PHONE_NUMBER_HERE", "password": "synthetic-pass"},
        {"username": "synthetic-user", "password": "*****"},
        {"username": "synthetic-user", "password": "xxxxxxxx"},
        {"username": 123, "password": "synthetic-pass"},
        {"username": "synthetic-user", "password": None},
        {"username": "synthetic-user", "password": False},
        {
            "username": "synthetic-user",
            "password": "synthetic-pass",
            "extra": "private-extra",
        },
    ],
)
def test_blank_placeholder_or_invalid_credentials_block_before_outbound(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    data: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_json(workspace.credentials, data)
    assert poc.main(["login"]) == 1
    output = capsys.readouterr()
    assert "nonplaceholder" in output.err
    assert not output.out
    assert "synthetic-user" not in output.err
    assert "synthetic-pass" not in output.err
    assert not harness.instances
    assert not workspace.session.exists()


def test_missing_credentials_does_not_login(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(["login", "--credentials", "poc/absent.json"]) == 1
    output = capsys.readouterr()
    assert "Credentials" in output.err
    assert not output.out
    assert not harness.instances
    assert not workspace.session.exists()


def test_device_is_persisted_before_failed_login_and_stable_on_retry(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness.failure = api.EvnAuthError()
    assert poc.main(["login"]) == 1
    first = read_json(workspace.session)
    assert set(first) == {"device_id", "account_hash"}
    assert re.fullmatch(r"[0-9a-f]{16}", first["device_id"])
    assert first["account_hash"] == workspace.account_hash
    assert capsys.readouterr().err == "EVN authentication failed.\n"
    assert poc.main(["login"]) == 1
    assert read_json(workspace.session) == first
    assert harness.instances[0].device_id == harness.instances[1].device_id
    harness.failure = None
    assert poc.main(["login"]) == 0
    final = read_json(workspace.session)
    assert final["device_id"] == first["device_id"]
    assert final["tokens"] == harness.login_tokens.to_dict()
    output = capsys.readouterr()
    assert json.loads(output.out) == {"command": "login", "success": True}
    assert_private_absent(output.out + output.err, workspace, harness)
    assert all(client.session.closed for client in harness.instances)


def test_username_stripped_password_preserved_and_account_hash_canonicalized(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(["login"]) == 0
    client = harness.instances[-1]
    assert client.username == workspace.username
    assert client.password == workspace.password
    device_id = client.device_id
    write_json(
        workspace.credentials,
        {
            "username": "\t" + workspace.username.swapcase() + "\n",
            "password": workspace.password,
        },
    )
    assert poc.main(["customers"]) == 0
    assert harness.instances[-1].username == workspace.username.swapcase()
    assert harness.instances[-1].password == workspace.password
    assert harness.instances[-1].device_id == device_id
    assert harness.events == ["login", "customers"]
    output = capsys.readouterr()
    assert_private_absent(output.out + output.err, workspace, harness)


@pytest.mark.parametrize("command", ["login", "customers", "test"])
def test_account_mismatch_never_reuses_tokens_or_identity(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_session(workspace, tokens=harness.login_tokens)
    before = workspace.session.read_bytes()
    write_json(
        workspace.credentials,
        {
            "username": "other-offline-account",
            "password": workspace.password,
        },
    )
    assert poc.main([command]) == 1
    output = capsys.readouterr()
    assert "different account" in output.err
    assert "other-offline-account" not in output.err
    assert_private_absent(output.out + output.err, workspace, harness)
    assert workspace.session.read_bytes() == before
    assert not harness.instances


@pytest.mark.parametrize(
    "update",
    [
        {"device_id": "short"},
        {"device_id": "g" * 16},
        {"device_id": "0" * 17},
        {"device_id": None},
        {"account_hash": None},
        {"tokens": None},
        {"tokens": {}},
        {"tokens": {"access_token": "valid", "refresh_token": "bad space"}},
        {"password": "private-stored-password"},
    ],
)
def test_invalid_session_cannot_be_overwritten_or_used(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    update: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = seed_session(workspace) | update
    write_json(workspace.session, data)
    before = workspace.session.read_bytes()
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "private-stored-password" not in output.err
    assert "bad space" not in output.err
    assert not harness.instances
    assert workspace.session.read_bytes() == before


def test_lazy_login_reuse_and_explicit_reauthentication(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(["test"]) == 0
    assert harness.events == ["login", "customers", "snapshot", "snapshot"]
    first = read_json(workspace.session)
    assert poc.main(["test"]) == 0
    assert harness.events.count("login") == 1
    assert harness.instances[-1].tokens == harness.login_tokens
    assert poc.main(["customers"]) == 0
    assert harness.events.count("login") == 1
    harness.login_tokens = api.TokenState(
        secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    )
    assert poc.main(["login"]) == 0
    assert harness.events.count("login") == 2
    assert read_json(workspace.session)["device_id"] == first["device_id"]
    assert read_json(workspace.session)["tokens"] == harness.login_tokens.to_dict()
    output = capsys.readouterr()
    assert_private_absent(output.out + output.err, workspace, harness)


@pytest.mark.parametrize("command", ["customers", "test"])
def test_stored_tokens_are_reused_without_password_login(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stored = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    seed_session(workspace, tokens=stored)
    before = workspace.session.read_bytes()
    assert poc.main([command]) == 0
    assert "login" not in harness.events
    assert harness.instances[-1].tokens == stored
    assert workspace.session.read_bytes() == before
    output = capsys.readouterr()
    assert stored.access_token not in output.out + output.err
    assert stored.refresh_token not in output.out + output.err


def test_discovery_is_safe_and_default_identifiers_are_masked(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(["customers"]) == 0
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result == {
        "command": "customers",
        "authorized_customer_count": 2,
        "customer_count": 2,
        "customers": [{"code": "[redacted]", "management_unit": "[redacted]"}] * 2,
    }
    assert not harness.fetched
    assert not output.err
    assert_private_absent(output.out, workspace, harness)
    assert "OFFLINE-CODE" not in output.out
    assert "OFFLINE-UNIT" not in output.out


def test_snapshot_summaries_use_models_without_sensitive_arrays(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(["test"]) == 0
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["customer_count"] == result["authorized_customer_count"] == 2
    assert len(result["snapshots"]) == 2
    assert harness.fetched == harness.inventory
    for item in result["snapshots"]:
        assert item["region"] == "PB"
        assert item["counts"] == {
            "measurement_points": 1,
            "monthly_records": 1,
            "daily_records": 1,
            "invoices": 1,
            "outages": 1,
        }
        assert item["measurement_points"] == [
            {
                "point": "[redacted]",
                "monthly": {"period": "2026-10", "kwh": 123.5},
                "daily": {"period": "06/10/2026", "kwh": 4.25},
            }
        ]
        assert item["outstanding"] == {"amount": 125000.0, "count": 1}
        assert item["next_outage"] == {
            "start": "2026-10-08T08:00:00+07:00",
            "end": "2026-10-08T10:00:00+07:00",
        }
        assert (
            datetime.fromisoformat(item["next_outage"]["start"]).utcoffset() is not None
        )
    assert_private_absent(output.out + output.err, workspace, harness)
    for private in (
        "OFFLINE-CODE",
        "OFFLINE-UNIT",
        "OFFLINE-POINT",
        "TONG_NO",
        "ID_HDON",
        "LY_DO",
        "phone",
        "address",
        "name",
    ):
        assert private not in output.out


@pytest.mark.parametrize("command", ["customers", "test"])
def test_show_identifiers_is_explicit_and_does_not_show_names(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        poc.main(
            [command, "--customer", harness.inventory[0].code, "--show-identifiers"]
        )
        == 0
    )
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["customers"] == [
        {"code": "OFFLINE-CODE-1", "management_unit": "OFFLINE-UNIT-1"}
    ]
    if command == "test":
        assert (
            result["snapshots"][0]["measurement_points"][0]["point"]
            == "OFFLINE-POINT-1"
        )
    assert "OFFLINE-CODE-2" not in output.out
    assert "OFFLINE-UNIT-2" not in output.out
    assert_private_absent(output.out + output.err, workspace, harness)


@pytest.mark.parametrize("command", ["customers", "test"])
def test_customer_filter_selects_only_authorized_exact_code(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = harness.inventory[1]
    assert poc.main([command, "--customer", target.code]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["authorized_customer_count"] == 2
    assert result["customer_count"] == 1
    assert harness.fetched == ([target] if command == "test" else [])


@pytest.mark.parametrize(
    "candidate",
    [
        "UNAUTHORIZED-CODE",
        "offline-code-1",
        "OFFLINE-CODE",
        " OFFLINE-CODE-1",
        "OFFLINE-CODE-1 ",
    ],
)
@pytest.mark.parametrize("command", ["customers", "test"])
def test_unauthorized_customer_never_fetches_or_echoes_candidate(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    candidate: str,
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main([command, "--customer", candidate]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "authorized inventory" in output.err
    assert candidate not in output.err
    assert not harness.fetched
    assert harness.events == ["login", "customers"]


def test_duplicate_customer_codes_preserve_authorized_units(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    extra = api.Customer(harness.inventory[0].code, "OFFLINE-OTHER-UNIT")
    harness.inventory.append(extra)
    harness.snapshots[(extra.code, extra.management_unit)] = snapshot(extra, 3)
    assert poc.main(["test", "--customer", extra.code]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["customer_count"] == 2
    assert harness.fetched == [harness.inventory[0], extra]


def test_empty_inventory_and_missing_model_values_are_safe(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = harness.inventory[0]
    item = harness.snapshots[(first.code, first.management_unit)]
    item.monthly = {}
    item.daily = {}
    item.invoices = [{}]
    item.outages = []
    assert poc.main(["test", "--customer", first.code]) == 0
    result = json.loads(capsys.readouterr().out)["snapshots"][0]
    assert result["measurement_points"][0]["monthly"] is None
    assert result["measurement_points"][0]["daily"] is None
    assert result["outstanding"] == {"amount": None, "count": None}
    assert result["next_outage"] is None
    harness.inventory.clear()
    assert poc.main(["test"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["customer_count"] == 0
    assert result["customers"] == result["snapshots"] == []


@pytest.mark.parametrize("position", ["before", "after"])
def test_options_work_before_or_after_command_and_paths_ignore_cwd(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    position: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    custom = workspace.directory / "custom-credentials.json"
    workspace.credentials.rename(custom)
    workspace.credentials = custom
    workspace.session = workspace.directory / "custom-session.json"
    monkeypatch.chdir(workspace.directory)
    options = [
        "--credentials",
        str(custom),
        "--session",
        "poc/custom-session.json",
        "--customer",
        "OFFLINE-CODE-1",
        "--show-identifiers",
    ]
    arguments = options + ["test"] if position == "before" else ["test"] + options
    assert poc.main(arguments) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["customer_count"] == 1
    assert result["customers"][0]["code"] == "OFFLINE-CODE-1"
    assert workspace.session.exists()
    assert not (workspace.directory / "poc").exists()


@pytest.mark.parametrize("flag", ["--credentials", "--session", "--save-raw"])
@pytest.mark.parametrize(
    "value",
    [
        "/tmp/outside-evn.json",
        "../outside.json",
        "poc/../outside.json",
        "poc/bad\npath.json",
    ],
)
def test_all_paths_must_be_project_local_without_traversal(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    flag: str,
    value: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert poc.main(["test", flag, value]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "Paths must be project-local" in output.err
    assert value not in output.err
    assert not harness.instances
    assert not workspace.session.exists()


@pytest.mark.parametrize("flag", ["--session", "--save-raw"])
@pytest.mark.parametrize(
    "extension", ["xapk", "apk", "apks", "aab", "zip", "tar.gz", "XAPK", "apk.json"]
)
def test_archive_output_never_touches_original(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    flag: str,
    extension: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive = workspace.directory / ("input." + extension)
    archive.write_bytes(b"offline-original-archive")
    assert poc.main(["test", flag, str(archive)]) == 1
    output = capsys.readouterr()
    assert "Archive files" in output.err
    assert not output.out
    assert archive.read_bytes() == b"offline-original-archive"
    assert not harness.instances


@pytest.mark.parametrize("kind", ["credentials", "session", "raw"])
@pytest.mark.parametrize("dangling", [False, True])
def test_secret_and_raw_symlinks_are_never_followed(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    kind: str,
    dangling: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    external = workspace.root.parent / ("external-" + secrets.token_hex(8) + ".json")
    if not dangling:
        write_json(
            external, {"username": workspace.username, "password": workspace.password}
        )
    target = getattr(workspace, kind)
    if target.exists():
        target.unlink()
    target.symlink_to(external)
    before = external.read_bytes() if external.exists() else None
    arguments = ["test"] + (["--save-raw", str(target)] if kind == "raw" else [])
    assert poc.main(arguments) == 1
    output = capsys.readouterr()
    assert not output.out
    assert_private_absent(output.out + output.err, workspace, harness)
    assert not harness.instances
    assert target.is_symlink()
    assert (external.read_bytes() if external.exists() else None) == before


@pytest.mark.parametrize("kind", ["credentials", "session", "raw"])
def test_symlink_parent_directory_is_refused(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    kind: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    actual = workspace.root / "actual"
    actual.mkdir()
    linked = workspace.directory / "linked"
    linked.symlink_to(actual, target_is_directory=True)
    target = actual / "secret.json"
    write_json(target, {"username": workspace.username, "password": workspace.password})
    before = target.read_bytes()
    flag = {
        "credentials": "--credentials",
        "session": "--session",
        "raw": "--save-raw",
    }[kind]
    assert poc.main(["test", flag, str(linked / "secret.json")]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert not harness.instances
    assert_private_absent(output.out + output.err, workspace, harness)
    assert target.read_bytes() == before


@pytest.mark.parametrize("kind", ["credentials", "session"])
@pytest.mark.parametrize("file_type", ["directory", "fifo", "hardlink"])
def test_secrets_must_be_regular_private_files(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    kind: str,
    file_type: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = getattr(workspace, kind)
    if target.exists():
        target.unlink()
    if file_type == "directory":
        target.mkdir(mode=0o600)
    elif file_type == "fifo":
        os.mkfifo(target, 0o600)
    else:
        source = workspace.directory / "source.json"
        write_json(
            source, {"username": workspace.username, "password": workspace.password}
        )
        target.hardlink_to(source)
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert "regular mode-600" in output.err
    assert not output.out
    assert not harness.instances


@pytest.mark.parametrize(
    "collision",
    ["credentials", "session", "existing", "directory", "root", "outside-poc"],
)
def test_raw_output_preflight_never_overwrites_or_authenticates(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    collision: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if collision == "credentials":
        target = workspace.credentials
    elif collision == "session":
        seed_session(workspace, tokens=harness.login_tokens)
        target = workspace.session
    elif collision == "existing":
        target = workspace.raw
        target.write_bytes(b"private-existing-file")
    elif collision == "directory":
        target = workspace.raw
        target.mkdir()
    elif collision == "root":
        target = workspace.directory
    else:
        target = workspace.root / "capture.json"
    before = target.read_bytes() if target.is_file() else None
    assert poc.main(["test", "--save-raw", str(target)]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "private-existing-file" not in output.err
    assert not harness.instances
    assert (target.read_bytes() if target.is_file() else None) == before


def test_session_cannot_overwrite_credentials_or_unknown_user_file(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = workspace.credentials.read_bytes()
    assert poc.main(["login", "--session", str(workspace.credentials)]) == 1
    assert workspace.credentials.read_bytes() == before
    workspace.session.write_bytes(b"existing-private-user-data")
    workspace.session.chmod(0o600)
    assert poc.main(["login"]) == 1
    assert workspace.session.read_bytes() == b"existing-private-user-data"
    output = capsys.readouterr()
    assert "existing-private-user-data" not in output.err
    assert not output.out
    assert not harness.instances


def test_raw_capture_is_private_selected_list_without_any_tokens(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    old = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    seed_session(workspace, tokens=old)
    discovery = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    latest = api.TokenState(
        secrets.token_urlsafe(24),
        secrets.token_urlsafe(24),
        "OFFLINE-CODE-1",
        "OFFLINE-UNIT-1",
    )
    harness.rotate_discovery, harness.rotate_snapshot = discovery, latest
    target = harness.inventory[0]
    item = harness.snapshots[(target.code, target.management_unit)]
    item.measurement_points[0].update(
        {
            "accessToken": old.access_token,
            "nested": {
                "refresh_token": latest.refresh_token,
                "password": workspace.password,
                "Authorization": "Bearer " + discovery.access_token,
                "text": "prefix:" + old.refresh_token + ":" + latest.access_token,
                old.access_token: "secret-key",
            },
        }
    )
    assert (
        poc.main(
            [
                "test",
                "--customer",
                target.code,
                "--save-raw",
                str(workspace.raw),
            ]
        )
        == 0
    )
    output = capsys.readouterr()
    assert output.err == "Private raw capture saved: poc/capture.json\n"
    capture = read_json(workspace.raw)
    assert isinstance(capture, list) and len(capture) == 1
    assert capture[0]["customer"]["code"] == target.code
    assert capture[0]["customer"]["name"] == target.name
    assert capture[0]["fetched_at"] == "2026-10-07T05:00:00+00:00"
    assert stat.S_IMODE(workspace.raw.stat().st_mode) == 0o600
    assert read_json(workspace.session)["tokens"] == latest.to_dict()
    raw = workspace.raw.read_text(encoding="utf-8")
    for state in (old, discovery, latest):
        for token in (state.access_token, state.refresh_token):
            assert token not in raw + output.out + output.err
    assert workspace.password not in raw
    assert "accessToken" not in raw and "refresh_token" not in raw
    assert_private_absent(output.out + output.err, workspace, harness)
    before = workspace.raw.read_bytes()
    instance_count = len(harness.instances)
    assert poc.main(["test", "--save-raw", str(workspace.raw)]) == 1
    assert len(harness.instances) == instance_count
    assert workspace.raw.read_bytes() == before


def test_show_identifiers_cannot_expose_tokens_embedded_in_identifier(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    token = harness.login_tokens.access_token
    person = api.Customer("CODE-" + token, "UNIT-" + harness.login_tokens.refresh_token)
    harness.inventory = [person]
    item = snapshot(person, 1)
    item.measurement_points[0]["MA_DDO"] = "POINT-" + token
    harness.snapshots = {(person.code, person.management_unit): item}
    assert poc.main(["test", "--show-identifiers"]) == 0
    output = capsys.readouterr()
    assert token not in output.out + output.err
    assert harness.login_tokens.refresh_token not in output.out + output.err
    assert json.loads(output.out)["customers"][0]["code"] == "CODE-[redacted]"


def test_token_rotation_is_immediate_atomic_and_latest_refresh_survives(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    old = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    seed_session(workspace, tokens=old)
    rotated = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    latest = api.TokenState(
        secrets.token_urlsafe(24),
        rotated.refresh_token,
        "OFFLINE-CODE-1",
        "OFFLINE-UNIT-1",
    )
    harness.rotate_discovery, harness.rotate_snapshot = rotated, latest
    original_replace = os.replace
    replacements: list[dict[str, Any]] = []

    def replace(source: Any, destination: Any, **options: Any) -> None:
        directory = options["src_dir_fd"]
        temporary = Path(f"/proc/self/fd/{directory}") / source
        assert stat.S_IMODE(temporary.stat().st_mode) == 0o600
        candidate = read_json(temporary)
        previous = read_json(workspace.session)
        assert previous["tokens"] != candidate["tokens"]
        original_replace(source, destination, **options)
        assert read_json(workspace.session) == candidate
        replacements.append(candidate)

    monkeypatch.setattr(poc.os, "replace", replace)
    assert poc.main(["test", "--customer", "OFFLINE-CODE-1"]) == 0
    assert [entry["tokens"] for entry in replacements] == [
        rotated.to_dict(),
        latest.to_dict(),
    ]
    assert read_json(workspace.session)["tokens"] == latest.to_dict()
    assert not list(workspace.directory.glob(".evn-*.tmp"))
    output = capsys.readouterr()
    for state in (old, rotated, latest):
        assert state.access_token not in output.out + output.err
        assert state.refresh_token not in output.out + output.err


def test_rotation_write_failure_is_generic_and_preserves_existing_session(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    old = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    seed_session(workspace, tokens=old)
    before = workspace.session.read_bytes()
    latest = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    harness.rotate_discovery = latest

    def replace(*args: Any, **kwargs: Any) -> None:
        raise OSError(workspace.password + latest.access_token + latest.refresh_token)

    monkeypatch.setattr(poc.os, "replace", replace)
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert workspace.password not in output.err
    assert latest.access_token not in output.err
    assert latest.refresh_token not in output.err
    assert workspace.session.read_bytes() == before
    assert not harness.fetched
    assert not list(workspace.directory.glob(".evn-*.tmp"))


def test_new_session_race_cannot_overwrite_user_file_before_login(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original_open = os.open

    def open_file(path: Any, flags: int, *args: Any, **options: Any) -> int:
        if path == workspace.session.name and flags & os.O_EXCL:
            workspace.session.write_bytes(b"race-created-session-user-data")
        return original_open(path, flags, *args, **options)

    monkeypatch.setattr(poc.os, "open", open_file)
    assert poc.main(["login"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "race-created-session-user-data" not in output.err
    assert workspace.session.read_bytes() == b"race-created-session-user-data"
    assert not harness.instances
    assert not list(workspace.directory.glob(".evn-*.tmp"))


def test_raw_race_cannot_overwrite_new_user_file(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original_link = os.link

    def link(source: Any, destination: Any, **options: Any) -> None:
        workspace.raw.write_bytes(b"race-created-user-data")
        original_link(source, destination, **options)

    monkeypatch.setattr(poc.os, "link", link)
    assert poc.main(["test", "--save-raw", str(workspace.raw)]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "race-created-user-data" not in output.err
    assert workspace.raw.read_bytes() == b"race-created-user-data"
    assert not list(workspace.directory.glob(".evn-*.tmp"))


def test_raw_appearing_during_fetch_is_not_overwritten(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = FakeClient.fetch_snapshot

    async def fetch(self: FakeClient, customer: Any) -> Any:
        workspace.raw.write_bytes(b"created-during-fetch")
        return await original(self, customer)

    monkeypatch.setattr(FakeClient, "fetch_snapshot", fetch)
    assert poc.main(["test", "--save-raw", str(workspace.raw)]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "saved" not in output.err.lower()
    assert workspace.raw.read_bytes() == b"created-during-fetch"


def test_session_swapped_for_symlink_during_fetch_is_not_overwritten(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_session(workspace, tokens=harness.login_tokens)
    victim = workspace.root / "victim.json"
    victim.write_bytes(b"private-user-data")
    original = FakeClient.fetch_snapshot
    harness.rotate_snapshot = api.TokenState(
        secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    )

    async def fetch(self: FakeClient, customer: Any) -> Any:
        workspace.session.unlink()
        workspace.session.symlink_to(victim)
        return await original(self, customer)

    monkeypatch.setattr(FakeClient, "fetch_snapshot", fetch)
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert workspace.session.is_symlink()
    assert victim.read_bytes() == b"private-user-data"
    assert "private-user-data" not in output.err
    assert not list(workspace.directory.glob(".evn-*.tmp"))


@pytest.mark.parametrize(
    "exception", ["auth", "connection", "response", "generic", "runtime"]
)
def test_api_and_unexpected_errors_are_sanitized_without_tracebacks(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    exception: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    errors = {
        "auth": api.EvnAuthError(),
        "connection": api.EvnConnectionError(),
        "response": api.EvnResponseError(),
        "generic": api.EvnError(),
        "runtime": RuntimeError(workspace.password + harness.login_tokens.access_token),
    }
    harness.failure = errors[exception]
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert output.err.startswith("EVN ")
    assert "Traceback" not in output.err
    assert_private_absent(output.out + output.err, workspace, harness)
    assert not harness.fetched


def test_account_action_required_is_distinct_and_private(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness.failure = api.EvnUserActionRequired()
    assert poc.main(["login"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "official unified EVN CSKH" in output.err
    assert "No password retry" in output.err
    assert "authentication failed" not in output.err
    assert_private_absent(output.out + output.err, workspace, harness)
    assert not harness.fetched


def test_failed_stored_token_auth_does_not_fall_back_to_password(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_session(workspace, tokens=harness.login_tokens)
    before = workspace.session.read_bytes()
    harness.customer_failure = api.EvnAuthError()
    assert poc.main(["test"]) == 1
    output = capsys.readouterr()
    assert output.err == "EVN authentication failed.\n"
    assert not output.out
    assert harness.events == ["customers"]
    assert workspace.session.read_bytes() == before
    assert not harness.fetched


def test_snapshot_failure_prints_no_partial_private_data_or_capture(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness.snapshot_failure = RuntimeError(workspace.password + "OFFLINE-PRIVATE-NAME")
    assert poc.main(["test", "--save-raw", str(workspace.raw)]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert output.err == "EVN operation failed.\n"
    assert not workspace.raw.exists()
    assert_private_absent(output.out + output.err, workspace, harness)


def test_async_entrypoint_is_available(
    workspace: SimpleNamespace,
    harness: SimpleNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    options = poc._parser().parse_args(["customers"])
    assert asyncio.run(poc._async_main(options)) == 0
    assert json.loads(capsys.readouterr().out)["command"] == "customers"
    assert harness.events == ["login", "customers"]


class Reply:
    def __init__(self, data: Any = None, *, status: int = 200) -> None:
        self.status = status
        self.raw = json.dumps({"success": True, "data": data}).encode()
        self.content_length = len(self.raw)
        self.content = self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def iter_chunked(self, _size: int) -> AsyncIterator[bytes]:
        yield self.raw


class ScriptedSession:
    def __init__(self, replies: list[Reply], **options: Any) -> None:
        assert options == {"trust_env": False}
        self.replies = replies
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True

    def request(self, method: str, url: str, **options: Any) -> Reply:
        self.calls.append({"method": method, "url": url, **options})
        assert self.replies, "Unexpected offline request"
        return self.replies.pop(0)


@pytest.fixture
def scripted(
    workspace: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., ScriptedSession]:
    monkeypatch.setattr(poc, "EvnClient", api.EvnClient)

    def install(*replies: Reply) -> ScriptedSession:
        session = ScriptedSession(list(replies), trust_env=False)
        monkeypatch.setattr(poc, "ClientSession", lambda **options: session)
        return session

    return install


def test_real_api_login_canonical_username_and_special_password_offline(
    workspace: SimpleNamespace,
    scripted: Callable[..., ScriptedSession],
    capsys: pytest.CaptureFixture[str],
) -> None:
    access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    canonical = "canonical-offline-" + secrets.token_hex(8)
    session = scripted(
        Reply({"username": canonical}),
        Reply({"accessToken": access, "refreshToken": refresh}),
    )
    assert poc.main(["login"]) == 0
    assert session.calls[0]["json"] == {"phone": workspace.username}
    assert session.calls[1]["json"]["username"] == canonical
    assert session.calls[1]["json"]["password"] == workspace.password
    assert (
        session.calls[1]["json"]["deviceInfo"]["deviceId"]
        == read_json(workspace.session)["device_id"]
    )
    assert not session.replies and session.closed
    assert read_json(workspace.session)["tokens"]["refresh_token"] == refresh
    output = capsys.readouterr()
    assert json.loads(output.out) == {"command": "login", "success": True}
    for private in (workspace.username, canonical, workspace.password, access, refresh):
        assert private not in output.out + output.err


def test_real_api_lazy_then_reuse_without_extra_login(
    workspace: SimpleNamespace,
    scripted: Callable[..., ScriptedSession],
    capsys: pytest.CaptureFixture[str],
) -> None:
    access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    session = scripted(
        Reply({}), Reply({"accessToken": access, "refreshToken": refresh}), Reply([])
    )
    assert poc.main(["test"]) == 0
    assert [call["url"].removeprefix(api.CENTRAL_BASE) for call in session.calls] == [
        "/auth/checkAccInUse",
        "/auth/login",
        "/user/me",
    ]
    assert not session.replies
    reused = scripted(Reply([]))
    assert poc.main(["test"]) == 0
    assert len(reused.calls) == 1
    assert reused.calls[0]["url"].endswith("/user/me")
    assert reused.calls[0]["headers"]["Authorization"] == "Bearer " + access
    output = capsys.readouterr()
    for private in (workspace.username, workspace.password, access, refresh):
        assert private not in output.out + output.err


def test_real_api_rotation_persists_before_retry_and_callback_failure_is_generic(
    workspace: SimpleNamespace,
    scripted: Callable[..., ScriptedSession],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    old = api.TokenState(secrets.token_urlsafe(24), secrets.token_urlsafe(24))
    seed_session(workspace, tokens=old)
    access, refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    session = scripted(
        Reply(status=401),
        Reply({"accessToken": access, "refreshToken": refresh}),
        Reply([]),
    )
    original = session.request

    def request(method: str, url: str, **options: Any) -> Reply:
        if len(session.calls) == 2:
            assert read_json(workspace.session)["tokens"]["refresh_token"] == refresh
        return original(method, url, **options)

    monkeypatch.setattr(session, "request", request)
    assert poc.main(["customers"]) == 0
    assert len(session.calls) == 3 and not session.replies
    assert session.calls[1]["json"]["refreshToken"] == old.refresh_token
    assert read_json(workspace.session)["tokens"]["refresh_token"] == refresh
    capsys.readouterr()
    before = workspace.session.read_bytes()
    next_access, next_refresh = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    failing = scripted(
        Reply(status=401),
        Reply({"accessToken": next_access, "refreshToken": next_refresh}),
    )

    def replace(*args: Any, **kwargs: Any) -> None:
        raise OSError(workspace.password + next_refresh)

    monkeypatch.setattr(poc.os, "replace", replace)
    assert poc.main(["customers"]) == 1
    output = capsys.readouterr()
    assert output.err == "EVN operation failed.\n"
    assert not output.out
    assert len(failing.calls) == 2 and not failing.replies
    assert workspace.session.read_bytes() == before
    for private in (
        old.access_token,
        old.refresh_token,
        access,
        refresh,
        next_access,
        next_refresh,
        workspace.password,
    ):
        assert private not in output.out + output.err
    assert not list(workspace.directory.glob(".evn-*.tmp"))


def test_import_loads_only_api_models_without_homeassistant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname: str, *args: Any, **kwargs: Any) -> Any:
            if fullname == "homeassistant" or fullname.startswith(
                ("homeassistant.", "custom_components.")
            ):
                raise AssertionError("Home Assistant imports are forbidden")
            return None

    monkeypatch.setattr(sys, "meta_path", [Guard(), *sys.meta_path])
    spec = importlib.util.spec_from_file_location(
        "_evn_cskh_poc_standalone_probe", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module: ModuleType = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    try:
        spec.loader.exec_module(module)
        assert module.api.EvnClient.__module__ == spec.name + "_api"
        assert module.models.monthly_summary.__module__ == spec.name + "_models"
        assert Path(module.api.__file__).name == "api.py"
        assert Path(module.models.__file__).name == "models.py"
        assert not hasattr(module, "homeassistant")
    finally:
        sys.modules.pop(spec.name + "_api", None)
        sys.modules.pop(spec.name + "_models", None)


def test_standalone_client_session_runtime_without_ha_or_outbound(
    workspace: SimpleNamespace,
) -> None:
    copied_poc = workspace.directory / "evn_cskh.py"
    shutil.copyfile(SCRIPT, copied_poc)
    component = workspace.root / "custom_components" / "evn_cskh"
    component.mkdir(parents=True)
    for filename in ("api.py", "models.py"):
        shutil.copyfile(
            ROOT / "custom_components" / "evn_cskh" / filename, component / filename
        )
    bootstrap = (
        "import asyncio, importlib.abc, importlib.util, socket, sys\n"
        "class Guard(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, *args, **kwargs):\n"
        "        if fullname == 'homeassistant' or fullname.startswith(('homeassistant.', 'custom_components.')):\n"
        "            raise AssertionError('Forbidden HA import')\n"
        "def blocked(*args, **kwargs):\n"
        "    raise AssertionError('Outbound connections are disabled')\n"
        "socket.socket.connect = blocked\n"
        "socket.socket.connect_ex = blocked\n"
        "socket.create_connection = blocked\n"
        "socket.getaddrinfo = blocked\n"
        "sys.meta_path.insert(0, Guard())\n"
        "spec = importlib.util.spec_from_file_location('_standalone_smoke', sys.argv[1])\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "sys.modules[spec.name] = module\n"
        "spec.loader.exec_module(module)\n"
        "async def smoke():\n"
        "    async with module.ClientSession(trust_env=False) as session:\n"
        "        client = module.EvnClient(session, '', '', '0123456789abcdef')\n"
        "        assert client.tokens is None\n"
        "asyncio.run(smoke())\n"
        "assert not any(name == 'homeassistant' or name.startswith('homeassistant.') for name in sys.modules)\n"
        "assert module.main(['--help']) == 0\n"
    )
    standalone = Path("/tmp/opencode/evncskh-venv/bin/python")
    interpreter = str(standalone) if standalone.is_file() else sys.executable
    result = subprocess.run(
        [interpreter, "-B", "-c", bootstrap, str(copied_poc)],
        cwd=workspace.root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert "--credentials" in result.stdout
    assert not result.stderr
    assert not workspace.session.exists()


def test_requested_files_have_no_comments_or_docstrings() -> None:
    for path in (SCRIPT, Path(__file__).resolve()):
        content = path.read_text(encoding="utf-8")
        assert all(
            token.type != tokenize.COMMENT
            for token in tokenize.generate_tokens(io.StringIO(content).readline)
        )
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                assert ast.get_docstring(node) is None
