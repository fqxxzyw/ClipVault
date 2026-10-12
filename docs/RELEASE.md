# GitHub 发布步骤

公开源码仓库：[fqxxzyw/ClipVault](https://github.com/fqxxzyw/ClipVault)，于 2026-10-11 创建。Windows 桌面验收尚未完成；二进制正式发布前按以下步骤验证。远程构建状态以 [Actions](https://github.com/fqxxzyw/ClipVault/actions) 实际运行记录为准。

当前预览发布：`v0.1.0-preview.1`，完整 Windows x64 ZIP 和 SHA-256 文件见 [Releases](https://github.com/fqxxzyw/ClipVault/releases)。CI 构建及隔离启动检查通过，真实 Windows 桌面验收仍待完成；预览版标记为 Pre-release。不要将它描述为已经完成 Windows 10/11 实机认证。

1. 在 Windows 10/11 桌面按 `WINDOWS_CHECKLIST.md` 实测并记录结果。
2. 运行 Ruff、pytest、`scripts/build.py`、`scripts/smoke_bundle.py`，再实际运行打包软件。
3. 检查不含真实数据库、配置、缓存、密钥、个人信息；本项目的 `.gitignore` 已排除这些文件。
4. 本仓库已设置公开可见、项目描述及 Topics。若发布自己的 Fork，可使用下方命令创建独立远程仓库；维护本仓库则直接克隆并提交功能分支。
5. ZIP 不包含 Git 元数据，以下命令仅用于从 ZIP 建立自己的新仓库；不要对已有远程历史强制推送。

```powershell
git init -b main
git add .
git commit -m "Initial ClipVault implementation"
git remote add origin https://github.com/YOUR_ACCOUNT/ClipVault.git
git push -u origin main
```

6. 在 Actions 查看 `Test and build ClipVault`。工作流成功后下载完整 `ClipVault-windows-x64-onedir`，在普通用户 Windows 桌面再验证启动、复制、快捷键、托盘、退出。
7. 将完整 `dist/ClipVault` 目录压缩为 `ClipVault-0.1.0-windows-x64.zip`，保留 `_internal`、许可证和通知；不要只发布 EXE。
8. 生成 SHA-256：`Get-FileHash .\ClipVault-0.1.0-windows-x64.zip -Algorithm SHA256`。
9. 创建 `v0.1.0` 标签并推送，建立 GitHub Release，上传 ZIP、SHA256、验证记录。未验证项明确写出，不编造下载量或兼容性认证。

构建默认不请求管理员权限，也不自动修改远程仓库。发布前检查 Qt/Pygments 许可证随包保留情况。当前没有代码签名证书；是否签名由维护者决定。
