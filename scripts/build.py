"""Native PyInstaller build. Windows by default; Linux check requires an explicit flag."""

import argparse
import json
import shutil
import subprocess
import sys
from importlib.metadata import distribution
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


def copy_notices(root: Path, output: Path) -> None:
    """Keep notices beside the EXE, including when building the optional onefile."""
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(root / name, output / name)
    licenses = output / "licenses"
    shutil.copytree(root / "packaging" / "licenses", licenses, dirs_exist_ok=True)
    packages = {}
    for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "Pygments"):
        package = distribution(name)
        destination = licenses / name
        destination.mkdir(parents=True, exist_ok=True)
        metadata = package.read_text("METADATA")
        if metadata:
            (destination / "METADATA").write_text(metadata, encoding="utf-8")
        for item in package.files or ():
            if any(word in item.name.lower() for word in ("license", "copying", "authors")):
                source = Path(package.locate_file(item))
                if source.is_file():
                    shutil.copy2(source, destination / item.name)
        packages[name] = package.version
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    elif sys.platform == "win32":
        raise RuntimeError("Python runtime license was not found; refusing an incomplete bundle")
    (licenses / "versions.json").write_text(
        json.dumps({"Python": sys.version.split()[0], **packages}, indent=2) + "\n",
        encoding="utf-8",
    )
    for required in ("LGPL-3.0.txt", "GPL-3.0.txt", "Pygments/LICENSE"):
        if not (licenses / required).is_file():
            raise RuntimeError("Required dependency license was not included")


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
    copy_notices(root, executable.parent)
    print(f"Build output: {executable}")
    print("Run scripts/smoke_bundle.py to validate isolated-profile startup and exit.")


if __name__ == "__main__":
    main()
