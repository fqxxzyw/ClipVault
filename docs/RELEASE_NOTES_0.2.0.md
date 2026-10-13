## ClipVault 0.2.0 Preview 1

轻量、离线、隐私优先的 Windows 剪贴板工作台。

新增：中英文切换、200ms 可中断动效与减少动态效果、Code / TXT / MD 分类与日期筛选、Markdown 渲染/原文预览与 Markdown/纯文本复制、内容小窗单击复制、离线 Emoji 面板、本地图片和文件路径记录、复制/字符/行数/常见表情/图片/文件/复用统计。

**[下载 Windows x64 完整 ZIP](https://github.com/fqxxzyw/ClipVault/actions/runs/38339833962/artifacts/11785609502)**
下载需要登录 GitHub。完整解压后运行 ClipVault.exe，保留 _internal、licenses 和所有声明。二进制位于 Actions artifact，未上传为 Release 附件；产物有保留期限。

SHA-256:
```text
5c2680db56302fda2bec14560509c508170e9ddd8aa29d558ca3546127ce7260
```

构建源提交：f0de3577d31a4d2f5d2a2d40c549b977474d7215
[实际 CI 运行](https://github.com/fqxxzyw/ClipVault/actions/runs/38339833962)：Linux Python 3.11 / 3.12 各 123 passed / 3 skipped；Windows 122 passed / 4 skipped，EXE 构建与打包后隔离启动/退出检查通过。Windows 多跳过一项 Linux 专用检查。

真实 Windows 10/11 剪贴板、图片/文件 MIME、物理键盘、托盘、开机启动、多显示器/DPI 和系统减少动效仍需实机验收，因此标记 Pre-release。图片无敏感内容识别，复制保密资料前请暂停。粘贴事件不可准确观测，本版不记录键盘，不将复用计数当作粘贴次数。

English: Offline bilingual clipboard manager with Markdown preview/copy modes, a content-only mini picker, categories/date filters, emoji, local images/file paths and aggregate statistics. The verified Windows onedir ZIP is hosted in Actions (GitHub sign-in required); extract the entire bundle. Interactive Windows 10/11 acceptance and onefile remain unverified.

[中文 README](https://github.com/fqxxzyw/ClipVault/blob/main/README.md) · [English README](https://github.com/fqxxzyw/ClipVault/blob/main/README_EN.md) · [验证记录](https://github.com/fqxxzyw/ClipVault/blob/main/docs/VALIDATION.md)
