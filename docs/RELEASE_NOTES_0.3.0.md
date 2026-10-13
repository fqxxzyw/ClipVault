# ClipVault 0.3.0 Preview 1

修复小窗只能 Alt 拖动且每次重置尺寸/位置的问题：普通拖动、边缘缩放、几何位置持久化；独立透明度、置顶、玻璃外观菜单，置顶复制后保持显示。

扩展到 24 种代码/配置语言，新增 HTML 静态预览及源码切换、手动类型选择和“自动识别”重识别已有条目。

界面更新圆角、Segoe UI Variable 字体优先、Windows 11 DWM 深色标题栏/系统圆角与 Mica/Acrylic 请求；页面 220ms 滑动+渐显，玻璃指针高光可中断，并遵循减少动效。

下载：[Windows x64 完整 ZIP](https://github.com/fqxxzyw/ClipVault/actions/runs/38357562691/artifacts/11793796402)（需要登录 GitHub，Actions 产物有效至 2027-01-11；二进制未附加到 Release）。完整解压后运行 `ClipVault.exe`，保留 `_internal` 与许可证目录。

SHA-256：`98c3d617681abd8190e8e69ed16b447b059b86551eb2ed71280bb6f2d3f84e59`。

[CI](https://github.com/fqxxzyw/ClipVault/actions/runs/38357562691)：Linux 158 passed / 3 skipped；Windows 157 passed / 4 skipped，PyInstaller onedir 构建与冻结 EXE 启动/退出 smoke 通过。源码提交 `2304c629c33bf4b21509fe64232382e7588365a0`。

真实 Windows 11 原生视觉和鼠标系统操作未验收，仍为预览版。

HTML 是 Qt 富文本静态预览，不执行脚本、不加载外部资源，不支持完整浏览器 Flex/Grid/JS。玻璃效果不是 Apple 光学折射。v4 数据库保留既有数据，但请勿用旧版打开升级后的目录。
