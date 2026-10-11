import os
import sys
from pathlib import Path


def data_directory(override: str | Path | None = None) -> Path:
    if override is not None:
        path = Path(override).expanduser().resolve()
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        path = (Path(base) if base else Path.home() / "AppData" / "Local") / "ClipVault"
    else:
        path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ClipVault"
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        path.chmod(0o700)
    return path


def resource_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / name
