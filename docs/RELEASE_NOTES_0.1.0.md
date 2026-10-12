首个公开预览版：轻量、离线、注重隐私的 Windows 剪贴板管理器。此版本标记为 **Pre-release**，Windows 10/11 真实桌面验收尚未完成。

**下载与运行**

下载 `ClipVault-0.1.0-preview.1-windows-x64.zip` 和同名 `.sha256` 文件，将 ZIP 完整解压到一个单独目录，再运行 `ClipVault.exe`。无需安装 Python。保留 `_internal`、`licenses` 和许可证文件。

数据默认保存在当前用户 `%LOCALAPPDATA%\ClipVault`，不写入软件目录，不上传服务器。

**主要功能**

- 事件驱动的文本剪贴板记录、SQLite 持久化与 SHA-256 去重。
- 中文子串和多关键词搜索、类型筛选、收藏和置顶。
- 本地识别文本、URL、Python、JavaScript、JSON、Shell、SQL；代码高亮与 JSON 格式化。
- Windows 全局快捷键、托盘操作、深浅主题与本地设置。
- 暂停记录、敏感规则过滤、自动清理和确认后清空普通历史。

**已验证**

- Linux Python 3.11 和 3.12：各 90 passed / 3 skipped。
- Windows Server 2025 x64 / Python 3.11.9：89 passed / 4 skipped。
- Windows PyInstaller onedir 构建成功；打包后 Qt 窗口、图标、SQLite、代码高亮和正常退出的隔离 offscreen 检查通过。
- ZIP CRC、SHA-256、x64 Windows GUI 子系统、Qt Windows 平台插件和许可证检查通过。

[实际构建记录](https://github.com/fqxxzyw/ClipVault/actions/runs/38194979657)。二进制构建源提交：`4945479301646278c185c49d3d804d7bc0f12da7`。

**验证边界**

真实 Windows 10/11 系统剪贴板、物理快捷键、托盘宿主、开机启动、多显示器/DPI 仍待桌面实测。CI 结果不能替代这些项目。EXE 未签名；onefile 尚未构建。

仅保存文本，超过 100,000 字符跳过；SQLite 未加密，敏感规则可能漏判或误判。核心无账号、云同步、遥测或网络传输，不执行剪贴板代码。主动打开 URL 会交给默认浏览器。

**English**

A lightweight, offline-first clipboard manager for Windows. Extract the complete x64 ZIP before running `ClipVault.exe`; Python is not required. Keep all dependency and license folders. The Windows CI build passed tests and an isolated offscreen startup check. Interactive Windows 10/11 clipboard, keyboard, tray, startup and multi-monitor verification remains pending; this is a preview release.
