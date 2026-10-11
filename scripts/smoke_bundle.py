import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", nargs="?", type=Path)
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    filename = "ClipVault.exe" if sys.platform == "win32" else "ClipVault"
    executable = options.executable or root / "dist" / "ClipVault" / filename
    if not executable.is_file():
        executable = root / "dist" / filename
    if not executable.is_file():
        raise SystemExit("Packaged executable was not found. Build first.")
    environment = os.environ.copy()
    # This is a render/startup check, not interactive desktop verification.
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [str(executable.resolve()), "--smoke-test"],
        env=environment,
        capture_output=True,
        timeout=40,
    )
    if result.returncode:
        # Do not print arbitrary stderr: a launcher or Qt may expose environment paths.
        raise SystemExit(f"Packaged startup/exit check failed (code {result.returncode})")
    print(
        "PASS: bundled Qt window, icons, SQLite, syntax highlighting and clean exit "
        "(isolated profile)."
    )
    print("Real Windows clipboard, hotkey and tray verification is a separate desktop check.")


if __name__ == "__main__":
    main()
