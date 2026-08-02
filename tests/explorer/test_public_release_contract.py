from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from vbg_interpreter import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = PROJECT_ROOT / ".build" / "web"
PAGES_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "pages.yml"
TEST_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def test_public_metadata_and_documentation_keep_the_research_boundary() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    clinical_scope = (PROJECT_ROOT / "docs" / "CLINICAL_SCOPE.md").read_text(encoding="utf-8")
    release_review = (PROJECT_ROOT / "docs" / "PUBLIC_RELEASE_REVIEW.md").read_text(
        encoding="utf-8"
    )
    project = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "https://reblocke.github.io/VBG_interpreter/" in readme
    assert "Intended use cases" in readme and "It is not intended for" in readme
    assert "not clinically validated" in readme.lower()
    assert "do not enter PHI" in readme
    assert "public research preview" in clinical_scope
    assert "not independent legal advice" in release_review
    assert "No external rights or legal-opinion record exists" in release_review
    assert 'version = "0.1.0"' in project
    assert "Private VBG" not in project


def test_release_version_is_consistent_across_public_surfaces() -> None:
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    citation = (PROJECT_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert version == __version__ == "0.1.0"
    assert re.search(rf"^version: {re.escape(version)}$", citation, re.MULTILINE)
    assert f"## [{version}] - 2026-08-02" in changelog
    assert f"`v{version}`" in readme

    environment = os.environ.copy()
    environment.pop("VBG_EXPLORER_SOURCE_COMMIT", None)
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "build_web.py")],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((BUILD_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == version
    assert manifest["build_binding"] == "LOCAL_UNBOUND"
    assert manifest["source_commit"] is None


def test_pages_workflow_is_exact_repository_commit_and_live_visibility_bound() -> None:
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert "github.repository == 'reblocke/VBG_interpreter'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert workflow.count('gh api "repos/${GITHUB_REPOSITORY}"') == 3
    assert 'gh api "repos/${GITHUB_REPOSITORY}/commits/main"' in workflow
    assert "github.event.repository.visibility" not in workflow
    assert "VBG_EXPLORER_SOURCE_COMMIT: ${{ github.sha }}" in workflow
    assert 'manifest["source_commit"] == os.environ["GITHUB_SHA"]' in workflow
    assert "make verify" in workflow and "make validation" in workflow
    assert "path: .build/web" in workflow
    assert "pages: write" in workflow and "id-token: write" in workflow
    for action in (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
        "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9",
        "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9",
        "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d",
        "actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128",
    ):
        assert action in workflow


def test_web_build_emits_exact_commit_binding() -> None:
    environment = os.environ.copy()
    environment["VBG_EXPLORER_SOURCE_COMMIT"] = TEST_COMMIT
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "build_web.py")],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((BUILD_ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest == {
        "build_binding": "SOURCE_COMMIT",
        "schema_version": "vbg_explorer_release_manifest/1.0",
        "source_commit": TEST_COMMIT,
        "source_repository": "https://github.com/reblocke/VBG_interpreter",
        "version": "0.1.0",
    }


@pytest.mark.parametrize("invalid_commit", ["main", "A" * 40, "0" * 39, "0" * 41])
def test_web_build_rejects_an_invalid_release_commit_binding(invalid_commit: str) -> None:
    environment = os.environ.copy()
    environment["VBG_EXPLORER_SOURCE_COMMIT"] = invalid_commit
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "build_web.py")],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "must be a lowercase 40-character Git commit" in completed.stderr
