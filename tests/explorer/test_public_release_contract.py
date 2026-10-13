from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
