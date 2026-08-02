#!/usr/bin/env python3
"""Verify the checked-in, same-origin Pyodide runtime without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = PROJECT_ROOT / "web/vendor/pyodide/0.29.3"
MANIFEST_FILENAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = "pyodide_vendor_manifest/1.0"
VERIFICATION_SCHEMA_VERSION = "pyodide_vendor_verification/1.0"
EXPECTED_MANIFEST_SHA256 = "e170602eee51a3bf5fea051187e01b83b3f895c6ab97c09eb96abc7c04d714ae"
EXPECTED_COMPONENT = {
    "name": "Pyodide",
    "version": "0.29.3",
    "python_version": "3.13.2",
    "delivery_mode": "SAME_ORIGIN_STATIC_CORE_SUBSET",
}
EXPECTED_RELEASE_ARCHIVE = {
    "filename": "pyodide-core-0.29.3.tar.bz2",
    "url": (
        "https://github.com/pyodide/pyodide/releases/download/0.29.3/pyodide-core-0.29.3.tar.bz2"
    ),
    "size_bytes": 5_986_900,
    "sha256": "83b764fe1a0ab6a2d76dba035fbef7284e06dac945a958be2d6447eced592f5a",
    "retrieved_on": "2026-07-31",
}
EXPECTED_OWNER_REVIEW_DATE = "2026-08-02"
EXPECTED_REVIEW_STATUS = "OWNER_REVIEWED_COMPONENT_NOTICE_INVENTORY_NO_INDEPENDENT_FTO_OPINION"
EXPECTED_RUNTIME_FILES = {
    "pyodide-lock.json": {
        "role": "package lock required by the core loader",
        "size_bytes": 120_010,
        "sha256": "3256ffc76388de0e37f4b34d42ab484268d1afc675179ff97b2a5bb14f84ccac",
    },
    "pyodide.asm.js": {
        "role": "Emscripten JavaScript runtime",
        "size_bytes": 1_074_322,
        "sha256": "1263f02b5b26099b96112378156f242dd98b39a8201ba7765e5fe3d455c5ce91",
    },
    "pyodide.asm.wasm": {
        "role": "WebAssembly runtime",
        "size_bytes": 8_647_684,
        "sha256": "e2f4ee75b325e35eb31bfb8c613d4dd5098f5502c156a97847686875b5025480",
    },
    "pyodide.js": {
        "role": "classic-worker loader",
        "size_bytes": 18_597,
        "sha256": "718d40f1c015dd25ec724cc8fc4e2325d6a45a92ae225121ff6953f224a16f72",
    },
    "python_stdlib.zip": {
        "role": "CPython and Pyodide standard-library archive",
        "size_bytes": 2_423_989,
        "sha256": "4298b6ee445cb724c3973437da47789752b9e6ff4e26619026b283ec801fc46b",
    },
}
EXPECTED_NOTICE_FILES = {
    "COMPONENT-SOURCES.md": {
        "role": "owner-reviewed component, source, and notice inventory",
        "size_bytes": 3_757,
        "sha256": "b4e228b6b992611adfde5d4d39cc7ec0aca91da94656ae82372adfa3b1f7577e",
    },
    "LICENSE-BZIP2.txt": {
        "role": "bzip2 1.0.6 license copied from the pinned Emscripten port source",
        "size_bytes": 1_895,
        "sha256": "a04a013cbbb1ff794c0bdf77af4cef040e67583f75bc6cf6d44dda692db7c7a0",
    },
    "LICENSE-CPYTHON-EXPAT.txt": {
        "role": "Expat notice copied from CPython 3.13.2 source",
        "size_bytes": 1_144,
        "sha256": "122f2c27000472a201d337b9b31f7eb2b52d091b02857061a8880371612d9534",
    },
    "LICENSE-CPYTHON-HACL.txt": {
        "role": "HACL* notice copied from CPython 3.13.2 source",
        "size_bytes": 1_141,
        "sha256": "328a079d376d3e1e966317c647906004d38d42b7624531456b90ae1b710ddc0c",
    },
    "LICENSE-CPYTHON-LIBMPDEC.txt": {
        "role": "libmpdec notice copied from CPython 3.13.2 source",
        "size_bytes": 1_284,
        "sha256": "669512af7219f58be03a398766d7c9da11a3b3df9d3f05cb74c5ceca25c8da3b",
    },
    "LICENSE-CPYTHON.txt": {
        "role": "CPython 3.13.2 source license",
        "size_bytes": 13_809,
        "sha256": "78b12c3a81360b357002334f0e70ea0e92eebf7a9b358805c03c48484945f3bb",
    },
    "LICENSE-EMSCRIPTEN.txt": {
        "role": "Emscripten 4.0.9 dual MIT and NCSA license",
        "size_bytes": 5_091,
        "sha256": "2fd38dc06e484cdd7a3f1e2f6577f5d53062052a2fd85131b56b89fbd673731c",
    },
    "LICENSE-LIBFFI.txt": {
        "role": "libffi notice copied from the exact Pyodide-pinned source commit",
        "size_bytes": 1_132,
        "sha256": "2c9c2acb9743e6b007b91350475308aee44691d96aa20eacef8e199988c8c388",
    },
    "LICENSE-MUSL.txt": {
        "role": "musl copyright notice copied from Emscripten 4.0.9",
        "size_bytes": 6_204,
        "sha256": "f9bc4423732350eb0b3f7ed7e91d530298476f8fec0c6c427a1c04ade22655af",
    },
    "LICENSE-PYODIDE.txt": {
        "role": "Pyodide 0.29.3 source license",
        "size_bytes": 16_725,
        "sha256": "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5",
    },
    "LICENSE-STACKFRAME.txt": {
        "role": "StackFrame notice copied from the Pyodide 0.29.3 source tree",
        "size_bytes": 1_080,
        "sha256": "899da9d991cb211a3642b84e82a9ae0b4b4e44546fd207e34d7d4ec2eb40f420",
    },
    "LICENSE-ZLIB.txt": {
        "role": "zlib 1.3.1 notice copied from the pinned Emscripten port source",
        "size_bytes": 1_002,
        "sha256": "845efc77857d485d91fb3e0b884aaa929368c717ae8186b66fe1ed2495753243",
    },
}
EXPECTED_SOURCE_COMPONENTS = {
    "Pyodide",
    "CPython",
    "Emscripten",
    "zlib Emscripten port",
    "bzip2 Emscripten port",
    "libffi",
    "hiwire",
    "musl libc",
    "CPython libmpdec",
    "CPython Expat",
    "CPython HACL*",
    "StackFrame",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class PyodideVendorError(RuntimeError):
    """Raised when the checked-in runtime or its provenance record drifts."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reject_symlinked_path(vendor_root: Path, project_root: Path) -> None:
    try:
        relative = vendor_root.relative_to(project_root)
    except ValueError as error:
        raise PyodideVendorError(
            "Pyodide vendor root must remain within the project root"
        ) from error

    current = project_root
    components = [current]
    for part in relative.parts:
        current /= part
        components.append(current)
    for component in components:
        try:
            mode = component.lstat().st_mode
        except OSError as error:
            raise PyodideVendorError("Pyodide vendor path is unavailable") from error
        if stat.S_ISLNK(mode):
            raise PyodideVendorError("Pyodide vendor path contains a symlinked component")


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PyodideVendorError(f"vendor manifest contains duplicate member: {key}")
        value[key] = item
    return value


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_members
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PyodideVendorError("vendor manifest is unavailable or invalid") from error
    if not isinstance(value, dict):
        raise PyodideVendorError("vendor manifest root must be an object")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], location: str) -> None:
    if set(value) != expected:
        raise PyodideVendorError(f"{location} keys do not match the fixed schema")


def _mapping(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PyodideVendorError(f"{location} must be an object")
    return value


def _sequence(value: object, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise PyodideVendorError(f"{location} must be an array")
    return value


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PyodideVendorError(f"{location} must be nonempty text")
    return value


def _filename(value: object, location: str) -> str:
    filename = _text(value, location)
    pure = PurePosixPath(filename)
    if pure.is_absolute() or len(pure.parts) != 1 or pure.name != filename:
        raise PyodideVendorError(f"{location} must be a direct child filename")
    return filename


def _file_rows(value: object, location: str) -> tuple[list[str], dict[str, dict[str, object]]]:
    rows = _sequence(value, location)
    names: list[str] = []
    observed: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(rows):
        row_location = f"{location}[{index}]"
        row = _mapping(raw, row_location)
        _exact_keys(row, {"path", "role", "size_bytes", "sha256"}, row_location)
        name = _filename(row["path"], f"{row_location}.path")
        _text(row["role"], f"{row_location}.role")
        if type(row["size_bytes"]) is not int or row["size_bytes"] < 0:
            raise PyodideVendorError(f"{row_location}.size_bytes must be a nonnegative integer")
        digest = _text(row["sha256"], f"{row_location}.sha256")
        if SHA256_PATTERN.fullmatch(digest) is None:
            raise PyodideVendorError(f"{row_location}.sha256 must be a lowercase SHA-256")
        if name in observed:
            raise PyodideVendorError(f"{location} contains duplicate file: {name}")
        names.append(name)
        observed[name] = {
            "role": row["role"],
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
        }
    if names != sorted(names):
        raise PyodideVendorError(f"{location} must be sorted by path")
    return names, observed


def _validate_source_components(value: object, notice_names: set[str]) -> None:
    rows = _sequence(value, "manifest.source_components")
    components: list[str] = []
    for index, raw in enumerate(rows):
        location = f"manifest.source_components[{index}]"
        row = _mapping(raw, location)
        _exact_keys(
            row,
            {
                "component",
                "identity",
                "evidence_url",
                "relationship",
                "notice_path",
                "review_status",
            },
            location,
        )
        components.append(_text(row["component"], f"{location}.component"))
        _text(row["identity"], f"{location}.identity")
        evidence_url = _text(row["evidence_url"], f"{location}.evidence_url")
        if not evidence_url.startswith("https://"):
            raise PyodideVendorError(f"{location}.evidence_url must use HTTPS")
        _text(row["relationship"], f"{location}.relationship")
        notice_path = row["notice_path"]
        if (
            notice_path is not None
            and _filename(notice_path, f"{location}.notice_path") not in notice_names
        ):
            raise PyodideVendorError(f"{location}.notice_path is not a checked notice")
        _text(row["review_status"], f"{location}.review_status")
    if len(components) != len(set(components)) or set(components) != EXPECTED_SOURCE_COMPONENTS:
        raise PyodideVendorError("manifest.source_components does not match the fixed inventory")


def _validate_manifest(record: Mapping[str, object]) -> tuple[list[str], list[str]]:
    _exact_keys(
        record,
        {
            "schema_version",
            "data_classification",
            "component",
            "release_archive",
            "runtime_files",
            "notice_files",
            "source_components",
            "owner_reviewed_on",
            "review_status",
        },
        "manifest",
    )
    if record["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise PyodideVendorError("vendor manifest schema_version is not approved")
    if record["data_classification"] != "PUBLIC_THIRD_PARTY_SOFTWARE":
        raise PyodideVendorError("vendor manifest data_classification is not approved")
    if _mapping(record["component"], "manifest.component") != EXPECTED_COMPONENT:
        raise PyodideVendorError("vendor manifest component identity drifted")
    if _mapping(record["release_archive"], "manifest.release_archive") != EXPECTED_RELEASE_ARCHIVE:
        raise PyodideVendorError("vendor manifest release archive identity drifted")
    if record["owner_reviewed_on"] != EXPECTED_OWNER_REVIEW_DATE:
        raise PyodideVendorError("vendor manifest owner review date drifted")
    if record["review_status"] != EXPECTED_REVIEW_STATUS:
        raise PyodideVendorError("vendor manifest owner-reviewed notice status drifted")

    runtime_names, runtime_rows = _file_rows(record["runtime_files"], "manifest.runtime_files")
    notice_names, notice_rows = _file_rows(record["notice_files"], "manifest.notice_files")
    if runtime_rows != EXPECTED_RUNTIME_FILES:
        raise PyodideVendorError("vendor manifest runtime identities drifted")
    if notice_rows != EXPECTED_NOTICE_FILES:
        raise PyodideVendorError("vendor manifest notice identities drifted")
    if set(runtime_names).intersection(notice_names):
        raise PyodideVendorError("vendor manifest repeats a runtime file as a notice")
    _validate_source_components(record["source_components"], set(notice_names))
    return runtime_names, notice_names


def verify_vendor(
    vendor_root: Path = VENDOR_ROOT,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, object]:
    vendor_root = vendor_root.absolute()
    project_root = project_root.absolute()
    _reject_symlinked_path(vendor_root, project_root)
    if not vendor_root.is_dir():
        raise PyodideVendorError("Pyodide vendor root is missing or not a directory")

    actual_entries: dict[str, Path] = {}
    for entry in vendor_root.iterdir():
        if entry.is_symlink():
            raise PyodideVendorError(f"Pyodide vendor tree contains symlink: {entry.name}")
        if not entry.is_file():
            raise PyodideVendorError(f"Pyodide vendor tree contains non-file entry: {entry.name}")
        actual_entries[entry.name] = entry

    manifest_path = actual_entries.get(MANIFEST_FILENAME)
    if manifest_path is None:
        raise PyodideVendorError("Pyodide vendor manifest is missing")
    record = _load_manifest(manifest_path)
    runtime_names, notice_names = _validate_manifest(record)
    manifest_sha256 = _sha256(manifest_path)
    if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        raise PyodideVendorError("Pyodide vendor manifest digest mismatch")
    expected_names = {MANIFEST_FILENAME, *runtime_names, *notice_names}
    actual_names = set(actual_entries)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise PyodideVendorError(
            f"Pyodide vendor tree inventory mismatch; missing={missing}, extra={extra}"
        )

    rows = [*record["runtime_files"], *record["notice_files"]]
    for row in rows:
        path = actual_entries[row["path"]]
        if path.stat().st_size != row["size_bytes"]:
            raise PyodideVendorError(f"Pyodide vendor size mismatch: {path.name}")
        if _sha256(path) != row["sha256"]:
            raise PyodideVendorError(f"Pyodide vendor digest mismatch: {path.name}")

    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "verification_status": "PASS",
        "component": EXPECTED_COMPONENT,
        "release_archive": EXPECTED_RELEASE_ARCHIVE,
        "manifest_sha256": manifest_sha256,
        "runtime_file_count": len(runtime_names),
        "notice_file_count": len(notice_names),
        "review_status": EXPECTED_REVIEW_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=VENDOR_ROOT)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    try:
        evidence = verify_vendor(args.root, project_root=args.project_root)
    except PyodideVendorError as error:
        parser.exit(1, f"Pyodide vendor verification refused: {error}\n")
    print(json.dumps(evidence, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
