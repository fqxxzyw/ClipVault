# ClipVault 0.3.1 Preview 1

新增设置：**自动清理复制文本（零宽脏字符与特殊空格）**，默认关闭，勾选并保存后立即生效。

- 清理 ZWSP、BOM、Word Joiner 等复制残留和无效控制字符；特殊空格逐个转换为普通空格。
- 新入库和从历史复制时生效；保留缩进、换行、正常代码/Markdown 和 Emoji 连接符。
- 清理后去重并重新检查敏感信息；文件路径及图片不变。
- 不批量改写已有记录，不接管外部系统剪贴板；请从 ClipVault 复制清理后的内容。
- 不移除有效星号/行号/代码围栏，不执行代码。

[CI 验证](https://github.com/fqxxzyw/ClipVault/actions/runs/38746819007)：Linux Python 3.11/3.12 各 170 passed / 3 skipped；Windows Python 3.11 为 169 passed / 4 skipped。Ruff、PyInstaller Windows x64 onedir 构建及冻结 EXE 隔离启动/退出检查通过。Windows 实体桌面操作未验证。

完整解压 Assets 中的 `ClipVault-0.3.1-preview.1-windows-x64.zip`，运行 `ClipVault.exe`，保留 `_internal` 和许可证目录。设置 → 隐私与历史记录 → 勾选“自动清理复制文本” → 保存。

SHA-256：`31291d9f072e9e0178e1e787f80ce1ba854192f88f3b79291ce7637eb35f1c07`。

源码提交：`e860609ee79063a16ce90e9e271e05bedd160cae`。

[直接下载 Windows 完整 ZIP](https://github.com/fqxxzyw/ClipVault/releases/download/v0.3.1-preview.1/ClipVault-0.3.1-preview.1-windows-x64.zip)（Release 正式附件，无需登录）。
