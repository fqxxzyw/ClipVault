# Third-party notices

ClipVault's own source code and original code-drawn icons are MIT licensed.

- **PySide6 / Qt / Shiboken6**: LGPL/GPL/commercial licensing as distributed by The Qt Company and upstream contributors. This project uses dynamically bundled Qt libraries and does not change them. The application's MIT license does not relicense Qt. Distributors must retain the applicable Qt license texts/notices and satisfy the license they choose.
- **Pygments**: BSD license. Retain its upstream notice when redistributing.
- **PyInstaller**: GPL with the upstream bootloader exception for packaged applications. Its license does not replace dependency obligations.
- **pytest, pytest-qt, Ruff**: development tools retain their respective upstream licenses; they are not application runtime modules.

The PyInstaller build uses its dependency hooks to collect upstream metadata and licenses. Before distributing an EXE, inspect the bundled third-party notices, obtain any license texts that a hook has omitted, and include them in the release. Source-build users can inspect licenses in the installed Python distributions. See the upstream projects for authoritative license terms:

- https://doc.qt.io/qtforpython-6/licenses.html
- https://pygments.org/docs/license/
- https://pyinstaller.org/en/stable/license.html
