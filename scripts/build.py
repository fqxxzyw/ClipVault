"""Native PyInstaller build. Windows by default; Linux check requires an explicit flag."""

import argparse
import subprocess
import sys
from pathlib import Path


def build_arguments(root: Path, *, onefile=False) -> list[str]:
    arguments = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "ClipVault",
        "--onefile" if onefile else "--onedir",
        "--paths",
        str(root / "src"),
        "--distpath",
        str(root / "dist"),
        "--workpath",
        str(root / "build"),
        "--specpath",
        str(root / "build"),
        "--collect-data",
        "clipvault",
        "--collect-submodules",
        "pygments.lexers",
        "--exclude-module",
        "PySide6.QtWebEngineCore",
        "--exclude-module",
        "PySide6.QtWebEngineWidgets",
        "--exclude-module",
        "PySide6.QtWebEngineQuick",
        "--exclude-module",
        "PySide6.QtPdf",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "tkinter",
    ]
    if sys.platform == "win32":
        arguments.extend(
            [
                "--icon",
                str(root / "src" / "clipvault" / "resources" / "clipvault.ico"),
                "--version-file",
                str(root / "packaging" / "version_info.txt"),
            ]
        )
    arguments.append(str(root / "scripts" / "entrypoint.py"))
    return arguments


def main():
    parser = argparse.ArgumentParser(description="Build ClipVault for the current OS")
    parser.add_argument("--onefile", action="store_true", help="Experimental single executable")
    parser.add_argument(
        "--allow-linux", action="store_true", help="Native Linux smoke build, NOT an EXE"
    )
    options = parser.parse_args()
    if sys.platform != "win32" and not (sys.platform == "linux" and options.allow_linux):
        parser.error("Build the Windows EXE on Windows. PyInstaller cannot cross-compile.")
    root = Path(__file__).resolve().parents[1]
    subprocess.run(build_arguments(root, onefile=options.onefile), check=True, cwd=root)
    executable = root / "dist" / ("ClipVault.exe" if sys.platform == "win32" else "ClipVault")
    if not options.onefile:
        executable = executable.parent / "ClipVault" / executable.name
    if not executable.exists():
        raise RuntimeError("Packaged executable was not created")
    print(f"Build output: {executable}")
    print("Run scripts/smoke_bundle.py to validate isolated-profile startup and exit.")


if __name__ == "__main__":
    main()
