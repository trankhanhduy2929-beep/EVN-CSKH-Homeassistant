from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn

from aiohttp import ClientSession

ROOT = Path(__file__).resolve().parents[1]
POC_DIR = ROOT / "poc"
_MAX_FILE_BYTES = 64 * 1024
_ARCHIVE_SUFFIXES = {
    ".aab",
    ".apk",
    ".apks",
    ".bz2",
    ".gz",
    ".jar",
    ".rar",
    ".tar",
    ".tgz",
    ".xapk",
    ".xz",
    ".zip",
    ".7z",
}
_PLACEHOLDERS = {
    "username",
    "password",
    "phone",
    "phonenumber",
    "yourusername",
    "yourpassword",
    "yourphone",
    "yourphonenumber",
    "yourevnusername",
    "yourevnpassword",
    "enterusername",
    "enterpassword",
    "changeme",
    "replaceme",
    "replacewithusername",
    "replacewithpassword",
    "placeholder",
    "redacted",
    "example",
    "sample",
    "todo",
    "fillme",
    "xxx",
    "...",
    "***",
}
_REGIONS = {"PA", "PB", "PC", "HN", "PE"}
Signature = tuple[int, int, int, int]


def _load_module(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "custom_components" / "evn_cskh" / filename
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Standalone EVN modules are unavailable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


api = _load_module(__name__ + "_api", "api.py")
models = _load_module(__name__ + "_models", "models.py")
EvnClient = api.EvnClient
TokenState = api.TokenState


class LocalError(Exception):
    pass


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, "Invalid arguments; use --help.\n")


def _add_options(parser: argparse.ArgumentParser, *, defaults: bool) -> None:
    parser.add_argument(
        "--credentials",
        metavar="FILE",
        default="poc/credentials.json" if defaults else argparse.SUPPRESS,
        help="Project-local mode-600 credential JSON (default: poc/credentials.json).",
    )
    parser.add_argument(
        "--session",
        metavar="FILE",
        default="poc/session.json" if defaults else argparse.SUPPRESS,
        help="Project-local protected session JSON (default: poc/session.json).",
    )
    parser.add_argument(
        "--customer",
        metavar="CODE",
        default=None if defaults else argparse.SUPPRESS,
        help="Exact customer code from the authorized inventory.",
    )
    parser.add_argument(
        "--show-identifiers",
        action="store_true",
        default=False if defaults else argparse.SUPPRESS,
        help="Show authorized customer, unit and measurement-point identifiers only.",
    )
    parser.add_argument(
        "--save-raw",
        metavar="FILE",
        default=None if defaults else argparse.SUPPRESS,
        help="Test only: new private capture under poc; may contain personal data.",
    )


def _parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(prog="evn_cskh.py", allow_abbrev=False)
    _add_options(parser, defaults=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for command, description in (
        ("login", "Explicit password reauthentication; preserves device identity."),
        ("customers", "Discover authorized customers without fetching snapshots."),
        ("test", "Discover customers and summarize selected or all snapshots."),
    ):
        child = commands.add_parser(
            command, help=description, description=description, allow_abbrev=False
        )
        _add_options(child, defaults=False)
    return parser


def _path(value: str, *, raw: bool = False, output: bool = False) -> Path:
    if not value or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise LocalError("Paths must be project-local without symlinks or traversal.")
    candidate = Path(value)
    if ".." in candidate.parts:
        raise LocalError("Paths must be project-local without symlinks or traversal.")
    path = candidate if candidate.is_absolute() else ROOT / candidate
    scope = POC_DIR if raw else ROOT
    if not path.is_relative_to(scope) or path == scope:
        raise LocalError("Paths must be project-local; raw captures must be under poc.")
    if output and any(suffix.lower() in _ARCHIVE_SUFFIXES for suffix in path.suffixes):
        raise LocalError("Archive files cannot be used as output.")
    return path


@contextmanager
def _parent_fd(path: Path) -> Iterator[int]:
    descriptor = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parent.relative_to(ROOT).parts:
            child = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _signature(info: os.stat_result) -> Signature:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _protected(info: os.stat_result) -> bool:
    return (
        stat.S_ISREG(info.st_mode)
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_uid == os.getuid()
        and info.st_nlink == 1
    )


def _read_secret(
    path: Path, kind: str, *, missing_ok: bool = False
) -> tuple[dict[str, Any], Signature] | None:
    message = f"{kind} must be a regular mode-600 JSON file of at most 64 KiB."
    try:
        with _parent_fd(path) as directory:
            try:
                descriptor = os.open(
                    path.name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=directory,
                )
            except FileNotFoundError:
                if missing_ok:
                    return None
                raise
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not _protected(info) or info.st_size > _MAX_FILE_BYTES:
                    raise LocalError(message)
                content = stream.read(_MAX_FILE_BYTES + 1)
                if len(content) > _MAX_FILE_BYTES:
                    raise LocalError(message)
            data = json.loads(content)
            if not isinstance(data, dict):
                raise LocalError(message)
            return data, _signature(info)
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise LocalError(message) from None


def _placeholder(value: str) -> bool:
    normalized = re.sub(r"[\s_-]+", "", value.strip().casefold().strip("<>[]{}"))
    return (
        not value.strip()
        or normalized in _PLACEHOLDERS
        or re.fullmatch(
            r"(?:(?:enter|insert|replacewith|fillin))?(?:your)?(?:evn)?"
            r"(?:username|password|phone(?:number)?)(?:here)?|x{3,}|\*{3,}|\.{3,}",
            normalized,
        )
        is not None
    )


def _credentials(path: Path) -> tuple[str, str]:
    loaded = _read_secret(path, "Credentials")
    if loaded is None:
        raise LocalError("Credentials are unavailable.")
    data, _ = loaded
    username, password = data.get("username"), data.get("password")
    if (
        set(data) != {"username", "password"}
        or not isinstance(username, str)
        or not isinstance(password, str)
        or _placeholder(username)
        or _placeholder(password)
    ):
        raise LocalError(
            "Credentials require nonblank, nonplaceholder username and password."
        )
    return username.strip(), password


def _check_target(directory: int, name: str, expected: Signature | None) -> None:
    try:
        info = os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        if expected is None:
            return
    else:
        if expected is not None and _protected(info) and _signature(info) == expected:
            return
    raise LocalError("Output exists, changed, or is not a protected regular file.")


def _atomic_write(
    path: Path, data: Any, *, expected: Signature | None = None, replace: bool = False
) -> Signature:
    temporary: str | None = None
    try:
        encoded = (
            json.dumps(data, ensure_ascii=True, allow_nan=False, indent=2) + "\n"
        ).encode()
        if replace and len(encoded) > _MAX_FILE_BYTES:
            raise LocalError("Session exceeds the protected file size limit.")
        with _parent_fd(path) as directory:
            _check_target(directory, path.name, expected)
            descriptor, filename = tempfile.mkstemp(
                prefix=".evn-", suffix=".tmp", dir=f"/proc/self/fd/{directory}"
            )
            temporary = Path(filename).name
            reservation: Signature | None = None
            installed = False
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    os.fchmod(stream.fileno(), 0o600)
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                    signature = _signature(os.fstat(stream.fileno()))
                _check_target(directory, path.name, expected)
                if replace:
                    target = expected
                    if target is None:
                        descriptor = os.open(
                            path.name,
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600,
                            dir_fd=directory,
                        )
                        try:
                            reservation = _signature(os.fstat(descriptor))
                            os.fchmod(descriptor, 0o600)
                            target = reservation
                        finally:
                            os.close(descriptor)
                    _check_target(directory, path.name, target)
                    os.replace(
                        temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory
                    )
                else:
                    os.link(
                        temporary,
                        path.name,
                        src_dir_fd=directory,
                        dst_dir_fd=directory,
                        follow_symlinks=False,
                    )
                installed = True
                os.fsync(directory)
                return signature
            finally:
                if reservation is not None and not installed:
                    with suppress(OSError):
                        info = os.stat(
                            path.name, dir_fd=directory, follow_symlinks=False
                        )
                        if _protected(info) and _signature(info) == reservation:
                            os.unlink(path.name, dir_fd=directory)
                if temporary is not None:
                    with suppress(FileNotFoundError):
                        os.unlink(temporary, dir_fd=directory)
    except (OSError, ValueError, TypeError, RecursionError):
        raise LocalError("Could not safely save the protected output file.") from None


@dataclass(repr=False)
class SessionStore:
    path: Path
    data: dict[str, Any]
    signature: Signature | None
    tokens: Any = None
    private: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: Path, username: str, password: str) -> SessionStore:
        account_hash = hashlib.sha256(username.strip().lower().encode()).hexdigest()
        loaded = _read_secret(path, "Session", missing_ok=True)
        if loaded is None:
            store = cls(
                path,
                {"device_id": secrets.token_hex(8), "account_hash": account_hash},
                None,
            )
        else:
            data, signature = loaded
            device_id = data.get("device_id")
            if (
                not {"device_id", "account_hash"} <= data.keys()
                or not data.keys() <= {"device_id", "account_hash", "tokens"}
                or not isinstance(device_id, str)
                or re.fullmatch(r"[0-9a-fA-F]{16}", device_id) is None
            ):
                raise LocalError("Session identity is invalid.")
            if data.get("account_hash") != account_hash:
                raise LocalError(
                    "Session belongs to a different account; use a separate session file."
                )
            try:
                tokens = (
                    TokenState.from_dict(data["tokens"]) if "tokens" in data else None
                )
            except api.EvnError:
                raise LocalError(
                    "Session authentication state is invalid; use explicit login with a separate session file."
                ) from None
            store = cls(path, data, signature, tokens)
        store.private.add(password)
        store.private.update((store.data["device_id"], account_hash))
        if store.tokens is not None:
            store.private.update(
                (store.tokens.access_token, store.tokens.refresh_token)
            )
        return store

    def save(self) -> None:
        self.signature = _atomic_write(
            self.path, self.data, expected=self.signature, replace=True
        )

    def on_tokens(self, tokens: Any) -> None:
        self.private.update((tokens.access_token, tokens.refresh_token))
        candidate = self.data | {"tokens": tokens.to_dict()}
        signature = _atomic_write(
            self.path, candidate, expected=self.signature, replace=True
        )
        self.data, self.signature, self.tokens = candidate, signature, tokens


def _redact(value: str, private: set[str]) -> str:
    for secret in sorted(private, key=len, reverse=True):
        if secret:
            value = value.replace(secret, "[redacted]")
    return value


def _clean(value: Any, private: set[str]) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
            if any(
                word in normalized
                for word in ("token", "password", "authorization", "cookie")
            ):
                continue
            if normalized in {
                "passwd",
                "pwd",
                "deviceid",
                "accounthash",
                "credentials",
            }:
                continue
            if _redact(key, private) != key:
                continue
            result[key] = _clean(item, private)
        return result
    if isinstance(value, list):
        return [_clean(item, private) for item in value]
    if isinstance(value, str):
        return _redact(value, private)
    return value


def _customer_summary(customer: Any, show: bool) -> dict[str, str]:
    return {
        "code": customer.code if show else "[redacted]",
        "management_unit": customer.management_unit if show else "[redacted]",
    }


def _usage(usage: Any) -> dict[str, Any] | None:
    return {"period": usage.period, "kwh": usage.value} if usage is not None else None


def _snapshot_summary(snapshot: Any, show: bool) -> dict[str, Any]:
    points = []
    for row in snapshot.measurement_points:
        point = row["MA_DDO"]
        points.append(
            {
                "point": point if show else "[redacted]",
                "monthly": _usage(
                    models.monthly_summary(snapshot.monthly.get(point, []))
                ),
                "daily": _usage(models.daily_summary(snapshot.daily.get(point, []))),
            }
        )
    invoices = models.invoice_summary(snapshot.invoices)
    outage = models.next_outage(snapshot.outages, now=snapshot.fetched_at)
    return {
        "customer": _customer_summary(snapshot.customer, show),
        "region": snapshot.region if snapshot.region in _REGIONS else None,
        "counts": {
            "measurement_points": len(snapshot.measurement_points),
            "monthly_records": sum(map(len, snapshot.monthly.values())),
            "daily_records": sum(map(len, snapshot.daily.values())),
            "invoices": len(snapshot.invoices),
            "outages": len(snapshot.outages),
        },
        "measurement_points": points,
        "outstanding": {"amount": invoices.amount, "count": invoices.count},
        "next_outage": {
            "start": outage.start.isoformat(),
            "end": outage.end.isoformat() if outage.end is not None else None,
        }
        if outage is not None
        else None,
    }


async def _async_main(options: argparse.Namespace) -> int:
    if (
        options.command not in {"login", "customers", "test"}
        or (options.save_raw is not None and options.command != "test")
        or (
            options.customer is not None
            and (options.command == "login" or not options.customer.strip())
        )
    ):
        raise LocalError("Invalid command options; use --help.")
    credentials_path = _path(options.credentials)
    session_path = _path(options.session, output=True)
    raw_path = (
        _path(options.save_raw, raw=True, output=True)
        if options.save_raw is not None
        else None
    )
    if credentials_path == session_path or raw_path in (credentials_path, session_path):
        raise LocalError("Credential, session and capture files must be separate.")
    if raw_path is not None:
        try:
            with _parent_fd(raw_path) as directory:
                _check_target(directory, raw_path.name, None)
        except OSError:
            raise LocalError(
                "Raw capture requires a new file under an existing poc directory without symlinks."
            ) from None
    username, password = _credentials(credentials_path)
    store = SessionStore.load(session_path, username, password)
    if store.signature is None:
        store.save()
    async with ClientSession(trust_env=False) as session:
        client = EvnClient(
            session,
            username,
            password,
            store.data["device_id"],
            tokens=store.tokens,
            on_tokens=store.on_tokens,
        )
        if options.command == "login":
            await client.login()
            result: dict[str, Any] = {"command": "login", "success": True}
        else:
            inventory = await client.customers()
            selected = [
                customer
                for customer in inventory
                if options.customer is None or customer.code == options.customer
            ]
            if options.customer is not None and not selected:
                raise LocalError(
                    "Requested customer is not in the authorized inventory."
                )
            result = {
                "command": options.command,
                "authorized_customer_count": len(inventory),
                "customer_count": len(selected),
                "customers": [
                    _customer_summary(customer, options.show_identifiers)
                    for customer in selected
                ],
            }
            if options.command == "test":
                snapshots = [
                    await client.fetch_snapshot(customer) for customer in selected
                ]
                result["snapshots"] = [
                    _snapshot_summary(snapshot, options.show_identifiers)
                    for snapshot in snapshots
                ]
                if raw_path is not None:
                    capture = []
                    for snapshot in snapshots:
                        item = asdict(snapshot)
                        item["fetched_at"] = snapshot.fetched_at.isoformat()
                        capture.append(item)
                    _atomic_write(raw_path, _clean(capture, store.private))
                    relative = _redact(
                        raw_path.relative_to(ROOT).as_posix(), store.private
                    )
                    print(f"Private raw capture saved: {relative}", file=sys.stderr)
        print(
            json.dumps(
                _clean(result, store.private),
                ensure_ascii=True,
                allow_nan=False,
                indent=2,
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        options = _parser().parse_args(argv)
    except SystemExit as argument_exit:
        return int(argument_exit.code) if isinstance(argument_exit.code, int) else 2
    with suppress(Exception):
        try:
            return asyncio.run(_async_main(options))
        except LocalError as local_error:
            print(str(local_error), file=sys.stderr)
        except api.EvnUserActionRequired:
            print(
                "EVN requires account confirmation in the official unified EVN CSKH application. "
                "No password retry was attempted.",
                file=sys.stderr,
            )
        except api.EvnAuthError:
            print("EVN authentication failed.", file=sys.stderr)
        except api.EvnConnectionError:
            print("EVN service is temporarily unavailable.", file=sys.stderr)
        except api.EvnResponseError:
            print("EVN returned an invalid response.", file=sys.stderr)
        except KeyboardInterrupt:
            print("Operation cancelled.", file=sys.stderr)
            return 130
        return 1
    print("EVN operation failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
