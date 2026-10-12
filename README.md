# ClipVault

Your Clipboard. Your Data. Your Control.

一款轻量、离线、注重隐私的 Windows 剪贴板管理器。

[English](README_EN.md) · [验证报告](docs/VALIDATION.md) · [Windows 验收](docs/WINDOWS_CHECKLIST.md)

- **完全离线，隐私优先**：无账号、无云同步、无遥测。识别、搜索和保存都在本机完成。
- **快捷搜索，快速复用**：多关键词和中文子串搜索、收藏、置顶、代码高亮。
- **轻量简洁，开箱即用**：原生 Qt 桌面界面，托盘常驻，Windows 全局快捷键。

> 当前公开预览版：0.1.0 Preview 1。[下载 Windows x64 完整包](https://github.com/fqxxzyw/ClipVault/releases)。Linux 两组 CI 各 90 项通过；Windows CI 89 项通过，EXE 构建及隔离启动检查通过。真实 Windows 10/11 桌面的剪贴板、物理快捷键、多显示器、托盘和开机启动尚需实测；预览版不代表桌面验收完成。详细结果见验证报告。

## 软件截图

下图来自**实际运行的 PySide6 程序**，使用隔离的临时数据目录和公开的示例内容，通过 Qt 窗口截图生成。当前捕获环境为 Linux/offscreen，窗口装饰与 Windows 实际显示略有不同；并非概念图或 Windows 实测截图。

![ClipVault 深色主题](screenshots/clipvault-dark.png)

![ClipVault 浅色主题](screenshots/clipvault-light.png)

![ClipVault 设置页](screenshots/clipvault-settings.png)

## 功能

| 功能 | 行为 |
| --- | --- |
| 自动监听 | `QClipboard.dataChanged` 事件；Windows 使用有界 Unicode 文本读取，剪贴板被占用时有限重试 |
| 历史记录 | SQLite 持久化、SHA-256 去重、最近复制时间更新；每次加载 50 条 |
| 搜索 | 多关键词 AND 子串匹配、类型筛选、收藏/置顶范围、时间排序；180 ms 防抖 |
| 内容识别 | 普通文本、HTTP(S) URL、Python、JavaScript、JSON、Shell、SQL；不确定时归为文本 |
| 预览 | Pygments 本地代码高亮；详情查看完整内容；JSON 格式化并复制 |
| 复用 | 双击/Enter/复制按钮；收藏和置顶持久化；HTTP(S) 链接可主动交给默认浏览器 |
| 隐私 | 暂停记录、默认敏感规则过滤、自动清理、确认后清空普通记录 |
| 设置 | 深浅主题、字体、透明度、快捷键、普通记录数量、保留天数、通知、自动隐藏、关闭行为 |
| Windows 集成 | `RegisterHotKey`、当前用户 `HKCU\…\Run` 开机启动、系统托盘 |

程序不执行剪贴板中的代码，也不读取启动前已有的剪贴板。MVP 不保存图片或文件；超过 **100,000 字符**的文本整条跳过，不截断后偷偷保存。Windows CRLF 换行统一为 LF；其他空格保持原样。

## 安装和运行

优先支持 Windows 10/11 64 位与 Python 3.11+。需要图形桌面。安装依赖和构建时可能需要联网；安装后的软件核心功能离线运行。

### 源码运行（PowerShell）

在解压后的 `clipvault` 目录中执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m clipvault
```

如果电脑只有 Python 3.12 或更高版本，将第一行的 `-3.11` 改为已安装版本。只运行软件可安装 `-e .`，无需开发依赖。

后台启动：

```powershell
.\.venv\Scripts\pythonw.exe -m clipvault --background
```

默认用户数据目录：`%LOCALAPPDATA%\ClipVault\`，包含 `history.sqlite3`、SQLite WAL/SHM 和 `settings.json`。不会写进源码目录。通过 Settings → Open data folder 打开。

可指定隔离目录，用于开发或验证：

```powershell
.\.venv\Scripts\python.exe -m clipvault --data-dir "$env:TEMP\clipvault-check"
```

Linux 可用 `python -m clipvault` 检查桌面界面；全局快捷键与开机启动仅支持 Windows。无系统托盘时，关闭窗口会退出，Esc 会最小化，避免窗口隐藏后无法找回。

### 已构建版本

在 [Releases](https://github.com/fqxxzyw/ClipVault/releases) 下载 `ClipVault-0.1.0-preview.1-windows-x64.zip` 和同名 `.sha256` 文件。将 ZIP **完整解压到一个单独目录**，再运行 `ClipVault.exe`；无需安装 Python。保留 `_internal`、`licenses` 和许可证文件，不要只拷贝 EXE。此包由 Windows Actions 构建并通过 offscreen 启动检查，真实桌面验收待完成。

Windows PowerShell 可用 `Get-FileHash .\ClipVault-0.1.0-preview.1-windows-x64.zip -Algorithm SHA256` 与校验文件核对。开发构建仍可从 Actions 下载 `ClipVault-windows-x64-onedir` artifact。

## 使用方式和快捷键

启动后在任意应用复制文本，记录会出现在 All Clips。单击查看预览；双击或 Enter 复制，再到目标应用按 Ctrl+V 粘贴。本版不自动把内容注入其他应用。

| 快捷键/动作 | 作用 |
| --- | --- |
| Ctrl+Shift+V | Windows 全局呼出/隐藏；可在设置中修改 |
| ↑ / ↓ | 搜索框或记录列表中切换记录 |
| Enter | 复制选中记录；由快捷键呼出的面板随后隐藏 |
| Esc | 有托盘时隐藏窗口；无托盘时最小化 |
| 托盘单击/双击 | 打开窗口 |
| Pause / Resume | 暂停或恢复新记录；暂停期间的内容不会补录 |

全局组合必须包含 Ctrl、Alt 或 Win，支持字母、数字、F1–F11、Space、Insert、Home、End、PageUp、PageDown。F12 保留给系统调试器。与其他应用冲突时提示失败并保留已有快捷键；Windows 保留组合也可能无法注册。没有使用全局键盘钩子，不截获普通键盘输入。

收藏和置顶独立；置顶条目始终排在前面。默认最多保留 **5,000 条普通记录**、**30 天**。数量限制不计入收藏和置顶，因此总记录数可能超过该值。清理在启动、捕获新内容、保存设置和每小时执行。

## 搜索与性能边界

空格分隔多个关键词，所有关键词必须出现在内容中；`%`、`_` 和引号按字面搜索。

- SQLite 支持 FTS5 trigram 时，对长度至少 3 的简单 ASCII 关键词使用 FTS5 候选集，并验证字面子串。
- **中文、短词、特殊字符**和没有 FTS5 的环境使用参数化 `LIKE` 查询。中文如“知识追踪 遗忘”能够匹配包含这两个子串的文本。
- `LIKE '%…%'` 不能使用普通 B-tree 索引，需扫描对应记录；耗时随记录数与文本量增长。默认 5,000 条普通记录控制规模，最多可设置 100,000 条；大量长文本及大量收藏仍可能使搜索变慢。没有编造性能指标。
- 所有 SQLite 查询、清理、分类和高亮在独立 Qt 工作线程执行，使用信号回到主线程；界面使用增量列表和过期结果丢弃。预览仅高亮前 20,000 字符，完整内容可在 Details 查看。

## 隐私说明

默认检测常见私钥头、明确的密码字段、GitHub/API Token、AWS Key、Bearer 字段等。规则只能降低误存风险，可能误判或漏判。复制密码、令牌或保密资料前应先暂停；过滤不是密码管理器。

SQLite 数据**未加密**，当前 Windows 用户和有读取权限的软件可以访问文件。共享设备请结合操作系统账号权限与磁盘加密。不会记录剪贴板原文到日志或错误对话框；本版不创建内容日志。

清空仅删除非收藏、非置顶记录，必须确认。数据库启用 `secure_delete`，清空后尝试截断 WAL，但删除不是对 SSD、备份、文件系统快照的安全擦除保证。收藏和置顶需要单独删除。关闭程序后可备份或删除整个数据目录。

核心没有网络客户端、账号、API Key、云同步或遥测。只有点击 **Open in browser** 才把 HTTP(S) 链接交给默认浏览器，浏览器随后可能联网。Settings 的 Open data folder 仅打开本地文件夹。

## Windows EXE 打包

```powershell
# 默认 onedir；脚本会安装依赖、构建并运行隔离启动检查
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1

# 或使用已有 Python 环境
.\.venv\Scripts\python.exe scripts/build.py
.\.venv\Scripts\python.exe scripts/smoke_bundle.py
```

输出：`dist/ClipVault/ClipVault.exe` 和同目录依赖。使用 `--windowed` 避免额外控制台；包含 Qt 平台插件、Pygments lexers、SVG/ICO 图标和 Windows 版本信息。构建不要求管理员权限。

单文件版是可选构建，尚未验证：

```powershell
.\.venv\Scripts\python.exe scripts/build.py --onefile
.\.venv\Scripts\python.exe scripts/smoke_bundle.py dist/ClipVault.exe
```

PyInstaller 不是交叉编译器，Windows EXE 必须在 Windows 构建。`scripts/build.py --allow-linux` 仅用于本地 Linux 打包检查，产物不是 Windows EXE。启动检查使用临时数据目录、不读取真实剪贴板、不注册快捷键；它不能替代真实桌面测试。

## 架构

```text
src/clipvault/
  main.py                 入口、单实例锁和隔离启动检查
  app.py                  控制器、托盘、设置与生命周期
  core/                   剪贴板适配器、快捷键、内容识别、隐私规则
  database/               数据模型、事务迁移、参数化仓储
  services/               Qt 后台数据库服务、搜索、清理、预览渲染
  ui/                     主窗口、卡片委托、预览、设置、主题、矢量图标
  utils/                  用户目录、原子设置文件、Windows 启动项
  resources/              应用 SVG 和多尺寸 ICO
tests/                    逻辑、模拟剪贴板、Qt 集成、可选 Windows 桌面测试
scripts/                  构建、启动检查、截图脚本
.github/workflows/ci.yml   Linux 测试和 Windows 打包
```

SQLite 启用 WAL、2.5 秒 `busy_timeout`，数据库繁忙时后台有限重试；最终失败会明确提示本次操作未完成。数据库版本通过 `PRAGMA user_version` 迁移，遇到更高版本会拒绝降级。应用不自动覆盖损坏的数据库。

## 测试

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m clipvault --smoke-test
```

普通 CI 测试使用 Qt offscreen 和临时目录，不读写真实 Windows 剪贴板。真实 Windows 集成测试需要用户主动在交互桌面运行，见 [Windows 验收](docs/WINDOWS_CHECKLIST.md)。GitHub 托管 Runner 的非交互测试结果不能代表真实用户桌面通过。

重新生成实际截图：

```powershell
.\.venv\Scripts\python.exe scripts/capture_screenshots.py --offscreen
```

截图脚本仅使用公开示例与临时数据库，但会暂时使用系统/Qt 剪贴板；请先暂停日常 ClipVault 实例，避免示例进入自己的历史。

## 已知限制

- Windows EXE 已在 Windows Server 2025 CI 构建并通过隔离启动检查；Windows 10/11 的原生监听、快捷键、托盘、开机启动和多显示器仍待真实桌面实测。
- Windows 10/11 是目标平台，不代表所有系统版本和 DPI 组合均已验证。
- 仅文本；不是密码库，无加密、自动粘贴、图片/文件历史或跨设备同步。
- 超长文本整条跳过，代码识别是保守启发式，JSON 解析/格式化不保留原有空格。
- 极短时间内复制后立即被下一次复制覆盖的内容，系统可能合并事件；本软件不能保证捕获每一个中间剪贴板状态。被占用时重试读取当前状态，避免伪造历史。
- Windows 剪贴板持续锁定或磁盘持续忙时会提示错误；后台队列和重试仅保存在内存，退出时尚未完成的重试可能无法保存。
- 第二实例通过用户数据目录中的锁拒绝启动；不会主动唤醒第一个实例，请用快捷键或托盘。
- EXE 未签名；是否出现 SmartScreen 或防病毒提示需在 Windows 上实际检查，不要发布未经检查的二进制。

## GitHub 发布准备

项目仓库：[fqxxzyw/ClipVault](https://github.com/fqxxzyw/ClipVault)。构建结果见 [GitHub Actions](https://github.com/fqxxzyw/ClipVault/actions)，发布步骤见 [发布指南](docs/RELEASE.md)。仓库描述：

```text
A lightweight, offline-first clipboard manager for Windows with instant search, syntax highlighting, and privacy protection.
```

Topics：`clipboard-manager` `windows` `python` `pyside6` `sqlite` `desktop-app` `productivity` `open-source` `privacy`。

## 贡献

Fork 后创建功能分支，提交前运行 Ruff、pytest，并为影响捕获/隐私/存储的行为补充测试。问题反馈请提供系统、Python/Qt 版本和不含隐私的复现步骤，不要附真实剪贴板数据库或密钥。真实 Windows 验证请按验收表记录环境和结果。

[MIT License](LICENSE)。第三方依赖保留各自许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
