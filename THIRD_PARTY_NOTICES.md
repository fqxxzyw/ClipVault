# Third-party notices

ClipVault's own source code and original code-drawn icons are MIT licensed.

- **PySide6 / Qt / Shiboken6**: LGPL/GPL/commercial licensing as distributed by The Qt Company and upstream contributors. This project uses dynamically bundled Qt libraries and does not change them. The application's MIT license does not relicense Qt. Distributors must retain the applicable Qt license texts/notices and satisfy the license they choose.
- **Pygments**: BSD license. Retain its upstream notice when redistributing.
- **PyInstaller**: GPL with the upstream bootloader exception for packaged applications. Its license does not replace dependency obligations.
- **pytest, pytest-qt, Ruff**: development tools retain their respective upstream licenses; they are not application runtime modules.

The build copies this notice and ClipVault's MIT license beside the executable. The `licenses/` directory contains LGPLv3/GPLv3 texts, installed runtime-package metadata and license files, Pygments' BSD notice, the Windows Python runtime license and exact dependency versions. Qt libraries are dynamically bundled; ClipVault does not modify them or restrict replacement of those libraries. Qt source and additional component notices are available from the upstream links below. Optional onefile builds also require the accompanying notices directory when redistributed.

Source-build users can inspect the installed Python distributions. Third-party components retain their own licenses; the application's MIT license applies to ClipVault's source, not its dependencies. See upstream for source code and component notices corresponding to the versions recorded in `licenses/versions.json`:

- https://doc.qt.io/qtforpython-6/licenses.html
- https://code.qt.io/cgit/pyside/pyside-setup.git/
- https://code.qt.io/cgit/qt/qtbase.git/
- https://code.qt.io/cgit/qt/qtsvg.git/
- https://doc.qt.io/qt-6/qtcore-attribution.html
- https://doc.qt.io/qt-6/qtgui-attribution.html
- https://doc.qt.io/qt-6/qtsvg-attribution.html
- https://pygments.org/docs/license/
- https://github.com/pygments/pygments
- https://github.com/python/cpython
- https://pyinstaller.org/en/stable/license.html
