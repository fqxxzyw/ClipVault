import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


class SettingsError(Exception):
    """Safe, content-free configuration error."""


@dataclass(frozen=True, slots=True)
class Settings:
    theme: str = "dark"
    language: str = "system"
    reduce_motion: bool = False
    shortcut_panel: str = "full"
    capture_images: bool = True
    capture_files: bool = True
    hotkey: str = "Ctrl+Shift+V"
    max_history: int = 5000
    retention_days: int = 30
    sensitive_filter: bool = True
    opacity: int = 100
    font_size: int = 13
    copy_notification: bool = True
    quit_on_close: bool = False
    auto_hide: bool = False
    start_at_login: bool = False
    paused: bool = False

    def validate(self) -> "Settings":
        from clipvault.core.hotkeys import parse_hotkey

        if self.theme not in {"dark", "light"}:
            raise SettingsError("Unsupported theme")
        if self.language not in {"system", "zh_CN", "en"}:
            raise SettingsError("Unsupported language")
        if self.shortcut_panel not in {"full", "compact"}:
            raise SettingsError("Unsupported shortcut panel")
        for field, minimum, maximum in (
            ("max_history", 100, 100_000),
            ("opacity", 65, 100),
            ("font_size", 11, 20),
        ):
            value = getattr(self, field)
            if type(value) is not int or not minimum <= value <= maximum:
                raise SettingsError("Invalid numeric setting")
        if type(self.retention_days) is not int or self.retention_days not in {0, 7, 30, 90}:
            raise SettingsError("Invalid retention period")
        if not isinstance(self.hotkey, str):
            raise SettingsError("Invalid shortcut")
        try:
            parse_hotkey(self.hotkey)
        except ValueError as error:
            raise SettingsError(str(error)) from None
        for field in (
            "sensitive_filter",
            "copy_notification",
            "quit_on_close",
            "auto_hide",
            "start_at_login",
            "paused",
            "reduce_motion",
            "capture_images",
            "capture_files",
        ):
            if type(getattr(self, field)) is not bool:
                raise SettingsError("Invalid boolean setting")
        return self


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            if self.path.stat().st_size > 32_768:
                raise SettingsError("Settings file is too large")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise SettingsError("Settings must be an object")
            allowed = {field.name for field in fields(Settings)}
            return Settings(
                **{key: value for key, value in raw.items() if key in allowed}
            ).validate()
        except (ValueError, TypeError, OSError) as error:
            raise SettingsError("Settings could not be loaded; defaults are in use") from error

    def save(self, settings: Settings) -> None:
        settings.validate()
        temporary = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(asdict(settings), handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if os.name != "nt":
                temporary.chmod(0o600)
            os.replace(temporary, self.path)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise SettingsError("Settings could not be saved") from error
