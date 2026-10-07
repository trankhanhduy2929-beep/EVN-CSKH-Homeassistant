from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "custom_components" / "evn_cskh"
DIST = ROOT / "dist"


def build() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    files = sorted(
        path
        for path in PACKAGE.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".json", ".js"}
        and "__pycache__" not in path.parts
    )
    required = {
        "__init__.py",
        "api.py",
        "config_flow.py",
        "const.py",
        "coordinator.py",
        "frontend/evn-cskh-panel.js",
        "manifest.json",
        "models.py",
        "panel.py",
        "sensor.py",
        "strings.json",
        "translations/en.json",
        "translations/vi.json",
    }
    if {path.relative_to(PACKAGE).as_posix() for path in files} != required:
        raise RuntimeError("Unexpected integration files; release aborted.")
    if not DIST.is_dir():
        raise RuntimeError("Project dist directory is missing.")
    artifacts = []
    for name, prefix in (
        (f"evn_cskh-{version}.zip", "custom_components/evn_cskh/"),
        ("evn_cskh.zip", ""),
    ):
        destination = DIST / name
        if destination.is_symlink():
            raise RuntimeError("Release destinations must not be symlinks.")
        with ZipFile(
            destination, "w", compression=ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in files:
                entry = ZipInfo(prefix + path.relative_to(PACKAGE).as_posix())
                entry.date_time = (2026, 10, 7, 0, 0, 0)
                entry.compress_type = ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, path.read_bytes())
        with ZipFile(destination) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("Release integrity validation failed.")
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        artifacts.append(f"{digest}  {name}")
    checksum = DIST / "SHA256SUMS"
    if checksum.is_symlink():
        raise RuntimeError("Checksum destination must not be a symlink.")
    checksum.write_text("\n".join(artifacts) + "\n", encoding="utf-8")
    print(
        "Built and verified two integration-only archives; no credentials or APK included."
    )


if __name__ == "__main__":
    build()
