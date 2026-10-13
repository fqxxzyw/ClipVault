# ClipVault 0.3.0 验证记录

验证日期：2026-10-13。Linux / Python 3.12 / PySide6 / Qt offscreen 环境。

## 本机结果

- 158 passed / 3 skipped，0 failed；Ruff 检查及格式检查通过。
- 源码隔离 smoke 通过，窗口、数据库、SVG/ICO、Pygments、Markdown、PNG 编码/读取与退出通过。
- 新增 35 项覆盖：20 种新增语言样例、普通文本回退、全语言 lexer、Code 分组、手动类型和重新识别、安全 HTML 渲染、拖动不复制、边缘缩放、尺寸位置保存、独立透明度和置顶、置顶复制保持显示、DWM 参数版本守卫、页面滑动恢复和减少动效。
- v4 数据库标记保留既有历史/收藏/图片/统计；新增语言标识对旧版本不兼容，旧版会拒绝打开而非错误渲染。不要降级使用同一数据目录。
- 真实 Qt 截图包括 HTML、C# 高亮、圆角玻璃小窗。GIF 来自实际运行的 QPropertyAnimation 帧，不是静态效果图或生成设计稿。

## Windows

0.3.0 Windows EXE 构建待 CI 验证，目前不标记通过。前版本构建不替代本次结果。现有只读 CI 未增加 contents-write 权限。

## 未验证与限制

真实 Windows 10/11 的鼠标原生移动/缩放、DWM 圆角/Mica/Acrylic、窗口置顶、独立透明度、多显示器/DPI、物理快捷键与托盘仍需实机验收。offscreen 测试只验证 Qt 路径及 fallback，不代表真实系统原生视觉效果。

HTML 为本地 Qt 静态富文本，禁用脚本和外部资源，不能当作完整浏览器的 CSS/Flex/Grid/JavaScript 预览。玻璃为半透明高光外观与支持平台的原生背景请求，不声称实现 Apple 光学折射。图片无敏感识别；粘贴次数不可观测。
