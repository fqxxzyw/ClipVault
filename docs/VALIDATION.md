# ClipVault 0.1.0 验证与交付记录

本机验证日期：2026-10-11；GitHub CI 验证日期：2026-10-12。项目根目录为 `clipvault/`。源码内含完整项目、双语 README、MIT License、测试、真实截图、Windows 构建脚本和 GitHub Actions。

## 结论

**90 项 pytest 测试通过，3 项真实 Windows 桌面测试跳过，0 失败、0 错误。Ruff 检查和格式检查通过。**

PySide6 主窗口已实际启动，深色、浅色及设置页截图来自运行中的 Qt 程序。源码启动检查验证窗口、数据库、SVG/ICO 资源及 Pygments 预览。Linux onedir 构建已完成；该产物的离屏启动、数据库初始化、代码高亮及干净退出检查结果列于下方。

**本机环境不是 Windows。远程 GitHub Actions 已在 Windows Server 2025 x64 / Python 3.11.9 上构建 EXE，并通过隔离 offscreen 启动、图标、数据库、高亮及退出检查。真实 Windows 10/11 剪贴板、物理快捷键、系统托盘、开机启动和多显示器仍未标记为通过。**

最终构建源提交：`4945479301646278c185c49d3d804d7bc0f12da7`。[实际 CI 运行](https://github.com/fqxxzyw/ClipVault/actions/runs/38194979657) 的三个任务全部成功：Linux Python 3.11 为 90 passed / 3 skipped，Linux 3.12 为 90 passed / 3 skipped；Windows 3.11 为 89 passed / 4 skipped。Windows 多跳过一项仅用于 Linux 的禁止交叉编译检查；三个真实桌面测试仍按条件跳过。

## 实际环境

| 组件 | 本次版本/环境 |
| --- | --- |
| OS | Linux x86_64，glibc 2.39 |
| Python | 3.12.14 |
| Qt 平台 | `offscreen`；无 Windows 交互桌面 |
| PySide6 | 6.12.0 |
| SQLite | 3.53.1 |
| Pygments | 2.21.0 |
| pytest / pytest-qt | 9.1.1 / 4.5.0 |
| Ruff | 0.17.0 |
| PyInstaller | 6.22.3 |

运行依赖只有 PySide6 与 Pygments；pytest、Ruff 和 PyInstaller 是开发/构建依赖。`requirements.txt` 使用兼容范围，因此未来解析出的版本可能不同。本次结果不代表所有满足范围的依赖组合已验证。

## 已执行命令

以下命令在安装项目和开发依赖后的隔离 Python 环境执行，路径均相对项目根目录：

```bash
ruff check .
ruff format --check .
QT_QPA_PLATFORM=offscreen python -m pytest -q --junitxml=test-results/pytest.xml
QT_QPA_PLATFORM=offscreen python -m clipvault --smoke-test
python scripts/capture_screenshots.py --offscreen
python scripts/build.py --allow-linux
python scripts/smoke_bundle.py
```

| 检查 | 实际结果 |
| --- | --- |
| Ruff 规则检查 | 通过 |
| Ruff 格式检查 | 通过 |
| pytest | 90 passed, 3 skipped；最近一次运行 9.45 秒 |
| 源码隔离启动检查 | 退出码 0 |
| Qt 实际截图 | 深色、浅色、设置页各 1 张；公开示例和临时数据库 |
| Linux PyInstaller onedir | 成功，原生 Linux 可执行文件；不是 Windows EXE |
| Linux 打包后离屏启动检查 | 通过；窗口、图标、SQLite、Pygments 和正常退出 |
| Windows onedir | Windows Server 2025 CI 构建成功；打包后隔离启动检查成功 |
| Windows onefile | 未执行 |
| 远程 CI | Linux 3.11 / 3.12 和 Windows 构建三个任务均通过；见上方实际运行链接 |
| Windows ZIP 检查 | SHA-256 与 CI artifact 一致、ZIP CRC 通过；x64 PE / GUI 子系统、Qt Windows 插件、图标和许可证齐全；不包含用户数据库或设置 |

测试用时只描述本次运行，不是性能基准或产品延迟承诺。XML 原始结果生成于临时检查目录，测试数据没有混入真实用户目录或源码包。

## 自动化覆盖

| 功能 | 验证内容与范围 |
| --- | --- |
| 数据库写入/读取 | SQLite 事务写入、重开连接读取，中文与多行内容 |
| 去重 | SHA-256 唯一记录、时间更新、创建时间与收藏/置顶保留；旧重试不倒退时间 |
| 收藏/置顶 | 持久化、筛选和置顶排序，Qt 按钮操作，重启应用恢复 |
| 删除/清空 | 单条删除、FTS 联动、普通历史清空，Qt 确认拒绝与确认执行 |
| 搜索 | 中文子串、多关键词、英文子串、大小写、特殊字符字面处理、FTS/LIKE 路径 |
| 列表 | 50 条分页、125+ 样例、类型和时间筛选 |
| 分类/JSON | 七种类别、保守回退、Unicode 格式化、拒绝 NaN |
| 清理 | 天数与数量策略，收藏/置顶保护，Never 设置 |
| 隐私 | 私钥、显式密码、常见 Token、暂停、超长、空白、NUL、无效代理字符 |
| 设置 | 原子保存、重载、无效类型与值、未知未来字段、保存失败回退 |
| 迁移/占用 | v1→v2 保留已有数据、未来版本拒绝、SQLite 占用后恢复 |
| Qt 剪贴板 | **offscreen Qt 的真实信号与 MIME 接口**到数据库/UI；内部复制不重复；不代表 Windows 系统剪贴板 |
| 模拟剪贴板 | 连续事件、暂停不补录、占用重试、过期重试取消、有限失败、下一事件恢复 |
| 快捷键 | 参数解析和**模拟原生 API**的热更换、冲突回退、资源释放 |
| 键盘/窗口 | Qt ↑↓/Enter 操作、重复显隐 25 次、无托盘 Esc 最小化回退 |
| 托盘菜单 | 实际 Qt 菜单/动作，平台可用性模拟；**不是 OS 托盘验证** |
| URL/文件夹 | 只主动打开 HTTP(S)，本地目录 URL；测试替换了启动默认浏览器/文件管理器动作 |
| 预览安全 | HTML 转义、高亮上限、详情来源，错误不含剪贴板原文 |
| 打包入口 | 资源和高亮的隔离启动检查；非 Windows 默认拒绝构建 Windows EXE |

## 跳过与待验证项目

`tests/test_windows_native.py` 包含 3 项 opt-in 原生测试：外部进程修改真实 Windows 剪贴板、原生快捷键注册/冲突/释放、`WM_HOTKEY` 通过 Qt 分发。由于本机为 Linux，它们全部跳过。

物理键盘、托盘宿主、多显示器/DPI、开机启动与 Windows 打包兼容性须按 [WINDOWS_CHECKLIST.md](WINDOWS_CHECKLIST.md) 在真实登录桌面完成，不能由 offscreen 或模拟测试结果代替。

Linux 打包日志提示本环境缺少 `libxcb-cursor.so.0`；本次使用 offscreen 不依赖 X11，未验证 Linux X11 原生窗口。因此也没有声称 Linux 图形桌面发布兼容性。

## 打包产物与交付

本次本机验证产物位置：`dist/ClipVault/ClipVault`，为 **Linux ELF**。它是构建检查结果，未放进 Windows 源码交付包。

Windows CI 产物为 **`dist/ClipVault/ClipVault.exe`**（带完整依赖和许可证目录），已上传为 `ClipVault-windows-x64-onedir` artifact。发布 ZIP 为 `ClipVault-0.1.0-preview.1-windows-x64.zip`，包含 236 个文件；大小 54,326,240 字节，SHA-256 为 `a8d8ac528e857e339144422c8356815528295af5ffbc2713af6767eb7326c89d`。可选 onefile 目标 `dist/ClipVault.exe` 未构建。

交付包的项目结构和关键入口：

| 文件/目录 | 用途 |
| --- | --- |
| `src/clipvault/` | 完整模块化程序源码和图标 |
| `tests/` | 逻辑、Qt 集成与可选真实 Windows 测试 |
| `README.md`, `README_EN.md` | 中英安装、运行、功能、隐私、限制及构建说明 |
| `scripts/build_windows.ps1`, `scripts/build.py` | Windows onedir/可选 onefile 构建 |
| `scripts/smoke_bundle.py` | 打包后的隔离启动和退出检查 |
| `.github/workflows/ci.yml` | Linux 检查、Windows 构建与 artifact 上传 |
| `screenshots/` | 实际 Qt 程序的 3 张截图 |
| `docs/RELEASE.md` | 仓库创建、推送、Actions 产物下载和 Release 步骤 |
| `docs/WINDOWS_CHECKLIST.md` | 未执行的 Windows 项目验收表 |
| `LICENSE`, `THIRD_PARTY_NOTICES.md` | MIT 与第三方依赖许可证说明 |

公开 GitHub 仓库为 [fqxxzyw/ClipVault](https://github.com/fqxxzyw/ClipVault)，远程构建状态见 Actions。本机与远程 CI 验证已分别注明；Windows 桌面未验证项仍然保留。源码 ZIP 不含 Git 元数据、用户数据库、设置、虚拟环境、缓存或测试数据库；从 ZIP 解压后可重新 `git init`。

## 已知问题和边界

- Windows 二进制已构建并完成隔离启动检查；Windows 10/11 桌面行为仍须实机验证，详见上表与验收单。
- SQLite 无加密；敏感检测会漏判/误判，删除不保证 SSD/备份安全擦除。
- 仅文本，超出 100,000 字符不保存；高亮只预览前 20,000 字符；不自动粘贴到其他程序。
- 中文/短词 LIKE 扫描随数据规模增长；大量长文本或收藏可能降低搜索速度。
- 系统可能合并极快复制的事件；持续锁定剪贴板/数据库时会提示失败，不能保证保存所有中间状态。
- 源码/EXE 依赖安装与构建可以联网，但核心捕获、搜索、分类和保存没有网络请求。
- 正常退出会关闭线程、连接和快捷键；尚在定时重试队列中的失败操作不保证跨退出保存。

所有截图使用公开示例。没有包含真实用户剪贴板历史、密码、Token、API Key 或个人身份信息。
