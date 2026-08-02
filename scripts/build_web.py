#!/usr/bin/env python3
"""Create the disposable static Explorer bundle, including both Python packages."""

from __future__ import annotations

import importlib.metadata
import json
import os
import re
import shutil
from pathlib import Path

PACKAGE_MANIFEST_SCHEMA_VERSION = "vbg_explorer_web_package_manifest/1.0"
RELEASE_MANIFEST_SCHEMA_VERSION = "vbg_explorer_release_manifest/1.0"
SOURCE_COMMIT_ENVIRONMENT_VARIABLE = "VBG_EXPLORER_SOURCE_COMMIT"
SOURCE_REPOSITORY = "https://github.com/reblocke/VBG_interpreter"
FULL_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
SAFE_PACKAGE_FILE_PATH = re.compile(
    r"^(?:stewartlight|vbg_interpreter)/(?:[A-Za-z0-9_][A-Za-z0-9_.-]*/)*[A-Za-z0-9_][A-Za-z0-9_.-]*$"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_SOURCE = PROJECT_ROOT / "web"
BUILD_ROOT = PROJECT_ROOT / ".build" / "web"
PYTHON_ASSET_ROOT = BUILD_ROOT / "assets" / "py"
PACKAGES = ("vbg_interpreter", "stewartlight")


def _ignore_web_source(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in {"assets", "__pycache__"}
        or name.endswith((".pyc", ".pyo"))
        or name == ".DS_Store"
    }


def _ignore_package(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name == "__pycache__" or name.endswith((".pyc", ".pyo")) or name == ".DS_Store"
    }


def _package_source(package_name: str) -> Path:
    if package_name == "vbg_interpreter":
        import vbg_interpreter

        source = Path(vbg_interpreter.__file__).resolve().parent
    elif package_name == "stewartlight":
        import stewartlight

        source = Path(stewartlight.__file__).resolve().parent
    else:  # pragma: no cover - closed package set
        raise ValueError("Unknown browser package.")
    if not (source / "__init__.py").is_file():
        raise RuntimeError("Installed browser package has no Python package entry point.")
    return source


def _stage_package(package_name: str) -> list[str]:
    source = _package_source(package_name)
    target = PYTHON_ASSET_ROOT / package_name
    shutil.copytree(source, target, ignore=_ignore_package)
    paths = [
        path.relative_to(PYTHON_ASSET_ROOT).as_posix()
        for path in target.rglob("*")
        if path.is_file()
    ]
    if not paths or f"{package_name}/__init__.py" not in paths:
        raise RuntimeError("Staged browser package is incomplete.")
    if any(SAFE_PACKAGE_FILE_PATH.fullmatch(path) is None for path in paths):
        raise RuntimeError("Staged browser package contains an unsafe path.")
    return paths


def _release_manifest() -> dict[str, object]:
    source_commit = os.environ.get(SOURCE_COMMIT_ENVIRONMENT_VARIABLE)
    if source_commit is not None and FULL_GIT_COMMIT.fullmatch(source_commit) is None:
        raise RuntimeError(
            f"{SOURCE_COMMIT_ENVIRONMENT_VARIABLE} must be a lowercase 40-character Git commit."
        )
    return {
        "build_binding": "SOURCE_COMMIT" if source_commit is not None else "LOCAL_UNBOUND",
        "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
        "source_commit": source_commit,
        "source_repository": SOURCE_REPOSITORY,
        "version": importlib.metadata.version("vbg-interpreter"),
    }


def build_web() -> Path:
    """Replace only the ignored `.build/web` output with a deterministic bundle."""

    release_manifest = _release_manifest()
    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    BUILD_ROOT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(WEB_SOURCE, BUILD_ROOT, ignore=_ignore_web_source)
    PYTHON_ASSET_ROOT.mkdir(parents=True, exist_ok=True)

    files = sorted(path for package in PACKAGES for path in _stage_package(package))
    if len(files) != len(set(files)):
        raise RuntimeError("Staged browser package manifest contains duplicate paths.")
    manifest = {
        "files": files,
        "schema_version": PACKAGE_MANIFEST_SCHEMA_VERSION,
    }
    (PYTHON_ASSET_ROOT / "package-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (BUILD_ROOT / "release-manifest.json").write_text(
        json.dumps(release_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return BUILD_ROOT


if __name__ == "__main__":
    print(build_web())
