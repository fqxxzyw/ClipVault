"""Capture the running Qt app using synthetic clips in a disposable profile."""

import argparse
import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offscreen", action="store_true")
    options = parser.parse_args()
    if options.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from clipvault.app import ClipVaultApplication

    application = QApplication([])
    output = Path(__file__).resolve().parents[1] / "screenshots"
    output.mkdir(exist_ok=True)

    def wait_until(predicate):
        deadline = time.monotonic() + 6
        while not predicate():
            if time.monotonic() > deadline:
                raise RuntimeError("Screenshot capture could not reach the expected UI state")
            QTest.qWait(25)

    with tempfile.TemporaryDirectory(prefix="clipvault-screenshot-") as directory:
        controller = ClipVaultApplication(
            application, Path(directory), no_tray=True, enable_hotkey=False
        )
        try:
            samples = [
                "Weekend ideas\nBuild something small. Ship something useful.\nKeep it local.",
                "https://docs.python.org/3/library/sqlite3.html",
                "git log --oneline --graph --decorate -12",
                '{"app":"ClipVault","offline":true,"theme":"dark"}',
                'def find_clips(query: str):\n    """Find your next idea, locally."""\n'
                "    terms = query.split()\n    return [\n        clip for clip in history\n"
                "        if all(term in clip for term in terms)\n    ]\n\n"
                'results = find_clips("weekend ideas")\nprint(results)',
            ]
            for index, text in enumerate(samples):
                application.clipboard().setText(text)
                wait_until(
                    lambda expected=index + 1: len(controller.window.model.items) == expected
                )
            wait_until(lambda: controller.window.preview.clip is not None)
            controller.window.list_view.setCurrentIndex(controller.window.model.index(0, 0))
            wait_until(
                lambda: (
                    controller.window.preview.clip is not None
                    and controller.window.preview.clip.content_type == "python"
                )
            )
            controller.window.list_view.verticalScrollBar().setValue(0)
            selected = controller.window.preview.clip.id
            controller.database.submit("flag", (selected, "is_favorite", True))
            wait_until(
                lambda: (
                    controller.window.preview.clip is not None
                    and controller.window.preview.clip.is_favorite
                )
            )
            controller.window.notice.hide()
            QTest.qWait(120)
            assert controller.window.grab().save(str(output / "clipvault-dark.png"))
            controller.save_settings(replace(controller.settings, theme="light"))
            wait_until(
                lambda: (
                    controller.window.preview.clip is not None
                    and not controller.refresh_timer.isActive()
                    and not controller.window.search_busy
                    and "#06287e" in controller.window.preview.browser.toHtml().lower()
                )
            )
            controller.window.notice.hide()
            QTest.qWait(150)
            assert controller.window.grab().save(str(output / "clipvault-light.png"))
            controller.save_settings(replace(controller.settings, theme="dark"))
            controller.window.navigate("settings")
            controller.window.notice.hide()
            QTest.qWait(150)
            assert controller.window.grab().save(str(output / "clipvault-settings.png"))
            print("Captured 3 actual Qt window images from a disposable example profile.")
        finally:
            controller.shutdown()
            application.clipboard().clear()


if __name__ == "__main__":
    main()
