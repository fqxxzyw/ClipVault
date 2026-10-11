"""Current-user Windows Run entry. No elevated permissions or scheduled tasks."""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_command(executable: str | None = None, *, frozen: bool | None = None) -> str:
    exe = Path(executable or sys.executable)
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not is_frozen and exe.name.lower() == "python.exe":
        windowless = exe.with_name("pythonw.exe")
        if windowless.exists():
            exe = windowless
    arguments = (
        [str(exe), "--background"] if is_frozen else [str(exe), "-m", "clipvault", "--background"]
    )
    return subprocess.list2cmdline(arguments)


@dataclass(frozen=True)
class StartupState:
    value: str | None


class WindowsStartup:
    @property
    def available(self) -> bool:
        return sys.platform == "win32"

    def snapshot(self) -> StartupState:
        if not self.available:
            return StartupState(None)
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, "ClipVault")
                return StartupState(value)
        except FileNotFoundError:
            return StartupState(None)

    def set_enabled(self, enabled: bool) -> None:
        if not self.available:
            if enabled:
                raise OSError("Startup registration is only supported on Windows")
            return
        self.restore(StartupState(startup_command() if enabled else None))

    def restore(self, state: StartupState) -> None:
        if not self.available:
            return
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if state.value is None:
                try:
                    winreg.DeleteValue(key, "ClipVault")
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(key, "ClipVault", 0, winreg.REG_SZ, state.value)
