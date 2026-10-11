import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_source_smoke_checks_window_database_icons_and_pygments(tmp_path):
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-m", "clipvault", "--smoke-test"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0
    # The smoke profile is temporary; no real or test DB leaks into its working directory.
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(sys.platform == "win32", reason="Cross-compilation guard is tested on Linux")
def test_windows_build_refuses_non_windows_by_default():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build.py")], capture_output=True, timeout=10
    )
    assert result.returncode != 0
    assert b"cannot cross-compile" in result.stderr
