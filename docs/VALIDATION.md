# ClipVault 0.2.0 验证记录

验证日期：2026-10-13。本机为 Linux x64 / Python 3.12.14 / PySide6 6.12.0 / Qt offscreen，不具备 Windows 交互桌面。

## 已完成

- pytest：**123 passed，3 skipped，0 failed**；完整测试结果生成于隔离检查目录。
- Ruff 规则和格式检查通过。
- 源码隔离启动检查退出码 0；验证窗口、资源、SQLite、Pygments、Markdown 转换、PNG 编码/读取与干净退出，不读取真实剪贴板。
- 9 张真实 Qt 窗口截图：英文深/浅色、中文设置、Markdown、小窗、图片、文件路径、统计和 Emoji。仅公开合成样例；使用临时数据库与示例路径。
- 功能集成测试覆盖 Markdown 两种复制且原文不改、资源加载拒绝、语言切换保留查询/选择、旧设置兼容、小窗单击/Enter/Esc、动画结束/减少动效/快速切页、Code 与日期筛选、图片保存/恢复/级联删除、文件路径和图标、暂停与图片开关、统计过滤/重置、Emoji 键盘复制。
- 数据库升级为 v3：在已有文字、收藏、置顶基础上新增本地图片表和按日聚合统计；现有迁移、未来版本拒绝及重开读取测试通过。

## Windows 构建

[本次实际 CI](https://github.com/fqxxzyw/ClipVault/actions/runs/38339833962) 三个任务均成功。构建源提交：`f0de3577d31a4d2f5d2a2d40c549b977474d7215`。

| 环境 | 测试与构建结果 |
| --- | --- |
| Ubuntu Python 3.11 | 123 passed / 3 skipped |
| Ubuntu Python 3.12 | 123 passed / 3 skipped |
| Windows Python 3.11 | 122 passed / 4 skipped；额外跳过 Linux 专用交叉编译检查 |
| Windows PyInstaller onedir | 构建成功，完整 `ClipVault.exe` 及 Qt/资源/许可证 |
| 打包后隔离启动 | 通过：窗口、图标、SQLite、Pygments、Markdown、PNG 存储/读取及干净退出 |

[Windows 完整 ZIP](https://github.com/fqxxzyw/ClipVault/actions/runs/38339833962/artifacts/11785609502)：54,375,079 字节，236 个文件。已下载并验证 SHA-256 `5c2680db56302fda2bec14560509c508170e9ddd8aa29d558ca3546127ce7260`、ZIP CRC、x64 PE GUI 子系统、Qt Windows 插件、ICO 与许可证齐全；不包含用户历史或设置。当前为 Actions artifact，下载需要 GitHub 登录，保留期限至 2027-01-11；不是已上传的 Release 二进制附件。

本地交付副本：`ClipVault-0.2.0-preview.1-windows-x64.zip`。已发布 [v0.2.0-preview.1](https://github.com/fqxxzyw/ClipVault/releases/tag/v0.2.0-preview.1)，标签指向上述已验证构建源。README 与验证说明在随后文档提交更新，运行代码一致。

现有 `.github/workflows/ci.yml` 保持 `contents: read`，运行 Ubuntu Python 3.11/3.12、Windows Python 3.11 测试和 PyInstaller onedir 构建，随后对完整打包程序执行隔离启动/退出检查并上传 artifact。

## 未完成 / 不声称已验证

3 项真实 Windows 桌面测试因平台条件跳过。真实 Windows 10/11 的剪贴板、图片/CF_HDROP 文件 MIME、物理快捷键、系统托盘、开机启动、多个显示器/DPI、Windows 动画偏好和 Emoji 系统字体仍须按 [清单](WINDOWS_CHECKLIST.md) 实测。

粘贴次数不可观测，本版没有键盘记录或注入粘贴。统计仅包含实际捕获的新复制和本软件成功复用事件。普通窗口复制、内部图片复制和 Markdown 转换复制均通过集成验证，不能把它们等同于其他应用已经粘贴。

未构建/验证 onefile；Linux 原生 X11 桌面不是本次验证范围。测试时长不是性能基准。图片无 OCR 或敏感图像检测；文件只保存路径。

发布凭证：[GitHub 预览版截图](clipvault-release-0.2.0-1791861059913.jpg)，来自实际发布页面；它不是软件窗口截图。
