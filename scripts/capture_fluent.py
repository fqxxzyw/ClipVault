"""Capture real Qt HTML, extended code, glass picker and page animations."""

import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from clipvault.app import ClipVaultApplication
from clipvault.database.models import utc_now


def main():
    app = QApplication([])
    output = Path(__file__).resolve().parents[1] / "screenshots"
    with tempfile.TemporaryDirectory(prefix="clipvault-fluent-") as directory:
        controller = ClipVaultApplication(app, Path(directory), no_tray=True, enable_hotkey=False)

        def wait_until(predicate):
            deadline = time.monotonic() + 6
            while not predicate():
                if time.monotonic() > deadline:
                    raise RuntimeError("Capture state was not reached")
                QTest.qWait(20)

        try:
            controller.save_settings(
                replace(controller.settings, language="zh_CN", mini_topmost=True)
            )
            samples = [
                (
                    "typescript",
                    "interface Clip {\n"
                    "  content: string;\n"
                    "  language: string;\n"
                    "}\n"
                    "\n"
                    "const vault: Clip[] = [];",
                ),
                ("rust", 'fn main() {\n    println!("Local. Private. Yours.");\n}'),
                (
                    "csharp",
                    "using System;\n"
                    "\n"
                    "class ClipVault {\n"
                    "    public static void Main() {\n"
                    '        Console.WriteLine("Your data stays here.");\n'
                    "    }\n"
                    "}",
                ),
                (
                    "html",
                    '<html><body style="background:#162236;color:#e5edf8">\n'
                    '<h1 style="color:#9eb9ff">Hello, ClipVault.</h1>\n'
                    "<p>离线 HTML 预览 · 数据始终在本地。</p>\n"
                    '<table cellspacing="0" cellpadding="10" border="1">\n'
                    "<tr><th>内容</th><th>操作</th></tr>\n"
                    "<tr><td>HTML / Markdown</td><td>预览与复制</td></tr>\n"
                    "<tr><td>代码片段</td><td>识别与高亮</td></tr>\n"
                    "</table>\n"
                    "<p><b>不执行脚本，不加载外部资源。</b></p>\n"
                    "</body></html>",
                ),
            ]
            for _kind, text in samples:
                controller.database.submit("capture", (text, utc_now()))
            wait_until(lambda: len(controller.window.model.items) == 4)
            controller.window.list_view.setCurrentIndex(controller.window.model.index(0, 0))
            wait_until(
                lambda: (
                    controller.window.preview.clip is not None
                    and controller.window.preview.clip.content_type == "html"
                )
            )
            controller.window.notice.hide()
            QTest.qWait(300)
            controller.window.grab().save(str(output / "clipvault-html.png"))
            controller.window.list_view.setCurrentIndex(controller.window.model.index(1, 0))
            wait_until(
                lambda: (
                    controller.window.preview.clip is not None
                    and controller.window.preview.clip.content_type == "csharp"
                )
            )
            QTest.qWait(280)
            controller.window.grab().save(str(output / "clipvault-code.png"))
            controller.show_mini()
            wait_until(lambda: not controller.window.search_busy)
            controller.mini.resize(460, 420)
            QTest.qWait(280)
            controller.mini.grab().save(str(output / "clipvault-glass-mini.png"))
            controller._show_full()
            # Recorded frames come directly from running QPropertyAnimation widgets.
            try:
                from PIL import Image
            except ImportError:
                print("Pillow is optional for GIF capture; PNG screenshots were captured.")
            else:
                import io

                frames, durations = [], []
                for scope in ("settings", "emoji", "stats", "all"):
                    controller.window.navigate(scope)
                    for _ in range(18):
                        before = time.monotonic()
                        QTest.qWait(15)
                        data = QByteArray()
                        buffer = QBuffer(data)
                        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                        controller.window.grab().save(buffer, "PNG")
                        buffer.close()
                        frames.append(Image.open(io.BytesIO(bytes(data))).convert("RGB"))
                        durations.append(max(20, int((time.monotonic() - before) * 1000)))
                    durations[-1] += 450
                frames[0].save(
                    output / "clipvault-motion.gif",
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=0,
                )
            print("Captured actual HTML/code/mini PNGs and running page-animation GIF.")
        finally:
            controller.shutdown()
            app.clipboard().clear()


if __name__ == "__main__":
    main()
