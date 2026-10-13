# GitHub 发布步骤

公开仓库：[fqxxzyw/ClipVault](https://github.com/fqxxzyw/ClipVault)。现有预览：[Releases](https://github.com/fqxxzyw/ClipVault/releases)。0.2.0 源码提供新语言、Markdown、小窗和富内容功能；早期 0.1.0 二进制不包含本次更新。

1. 用临时数据完成 Ruff、pytest、源码 smoke 和 [Windows 桌面清单](WINDOWS_CHECKLIST.md)，明确记录未验证项。
2. 提交功能和真实截图，查看现有 `Test and build ClipVault` CI。工作流仅 `contents: read`；上传完整 onedir artifact，不写 Release 或变更仓库权限。
3. Windows 构建与打包 smoke 通过后下载完整 `ClipVault-windows-x64-onedir`，验证 SHA-256、ZIP CRC、Qt 插件、图标与许可证。检查没有用户历史、设置、照片、私人路径或密钥。
4. 在普通用户 Windows 10/11 登录桌面测试打包程序。不把 CI/offscreen 结果称为实机验收。
5. 为当前源码创建 `v0.2.0-preview.1` 标签和 GitHub Pre-release，使用 [发布说明](RELEASE_NOTES_0.2.0.md) 并记录实际提交/CI/下载链接及校验值。尚未上传 Release 附件时明确注明 artifact 下载需要登录和有保留期限。
6. 手动上传完整 ZIP、SHA256 和验证记录时，不要只上传 EXE。打包包含 `_internal`、`licenses`、MIT 与第三方声明。

源码运行/构建命令见中英文 README。可用 PowerShell `Get-FileHash .\ClipVault-0.2.0-preview.1-windows-x64.zip -Algorithm SHA256` 校验下载文件。

发布自己的 Fork 请自行创建远程并正常推送；已有仓库不要重写或强制覆盖历史。当前没有签名证书，onefile 和真实 Windows 10/11 验收仍须单独完成。
