import argparse
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QLockFile, Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from clipvault import __version__
from clipvault.app import ClipVaultApplication
from clipvault.core.clipboard import ClipboardRead
from clipvault.database.models import utc_now
from clipvault.utils.paths import data_directory, resource_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ClipVault — local clipboard manager")
    parser.add_argument("--version", action="version", version=f"ClipVault {__version__}")
    parser.add_argument("--background", action="store_true", help="Start hidden in the tray")
    parser.add_argument("--data-dir", type=Path, help="Explicit isolated data directory")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Open and exit with an isolated temporary profile (no clipboard reads)",
    )
    options = parser.parse_args(argv)
    temporary = (
        tempfile.TemporaryDirectory(prefix="clipvault-smoke-") if options.smoke_test else None
    )
    try:
        directory = data_directory(temporary.name if temporary else options.data_dir)
    except OSError:
        # No user content, paths or traceback are printed, even for a windowless frozen app.
        return 2
    application = QApplication([sys.argv[0]])
    application.setApplicationName("ClipVault")
    application.setOrganizationName("ClipVault")
    application.setApplicationVersion(__version__)
    lock = QLockFile(str(directory / "instance.lock"))
    lock.setStaleLockTime(30_000)
    if not lock.tryLock(100):
        QMessageBox.information(
            None, "ClipVault 已在运行", "请从系统托盘或全局快捷键打开 ClipVault。"
        )
        return 1
    controller = None
    try:
        controller = ClipVaultApplication(
            application,
            directory,
            background=options.background,
            no_tray=options.smoke_test,
            enable_hotkey=not options.smoke_test,
        )
        if options.smoke_test:
            controller.clipboard.close()
            smoke_state = {
                "initialized": False,
                "preview": False,
                "failed": False,
                "preview_job": None,
                "stage": "code",
                "markdown": False,
                "image": False,
            }

            def smoke_result(job_id, name, value):
                if name == "initialize":
                    smoke_state["initialized"] = True
                    controller.database.submit(
                        "capture", ("def clipvault_smoke():\n    return 'local-only'", utc_now())
                    )
                elif name in {"capture", "capture_rich"} and value["clip_id"] is not None:
                    smoke_state["preview_job"] = controller.database.submit(
                        "preview", value["clip_id"]
                    )
                elif name == "preview" and job_id == smoke_state["preview_job"]:
                    if smoke_state["stage"] == "code":
                        smoke_state["preview"] = value[0] is not None and "<span" in value[1]
                        smoke_state["stage"] = "markdown"
                        controller.database.submit(
                            "capture", ("# Markdown smoke\n\n**local**", utc_now())
                        )
                    elif smoke_state["stage"] == "markdown":
                        from clipvault.services.markdown import markdown_plain_text

                        smoke_state["markdown"] = (
                            value[0] is not None
                            and value[0].content_type == "markdown"
                            and "Markdown smoke" in markdown_plain_text(value[0].content)
                        )
                        smoke_state["stage"] = "image"
                        image = QImage(16, 16, QImage.Format.Format_ARGB32)
                        image.fill(Qt.GlobalColor.blue)
                        controller.database.submit(
                            "capture_rich",
                            (ClipboardRead(None, kind="image", image=image), utc_now()),
                        )
                    else:
                        smoke_state["image"] = (
                            value[0] is not None
                            and value[0].content_type == "image"
                            and value[2] is not None
                            and value[2].width() == 16
                        )

            def smoke_error(job_id, name, message):
                smoke_state["failed"] = True

            def finish_smoke():
                passed = (
                    smoke_state["initialized"]
                    and smoke_state["preview"]
                    and smoke_state["markdown"]
                    and smoke_state["image"]
                    and not smoke_state["failed"]
                    and resource_path("clipvault.svg").is_file()
                    and resource_path("clipvault.ico").is_file()
                    and not controller.window.windowIcon().isNull()
                    and controller.window.isVisible()
                )
                controller.shutdown()
                application.exit(0 if passed else 3)

            controller.database.result.connect(smoke_result)
            controller.database.error.connect(smoke_error)
            QTimer.singleShot(1600, finish_smoke)
        code = application.exec()
    except Exception:
        if not options.smoke_test:
            QMessageBox.critical(
                None, "ClipVault", "应用无法启动，请检查安装依赖和本地数据目录权限。"
            )
        code = 2
    finally:
        if controller is not None:
            controller.shutdown()
        lock.unlock()
        if temporary is not None:
            temporary.cleanup()
    return code
