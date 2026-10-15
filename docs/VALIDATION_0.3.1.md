# ClipVault 0.3.1 验证记录

本机 Linux / Python 3.12：170 passed / 3 skipped，Ruff 检查、格式检查及 diff 空白检查通过。Qt offscreen 隔离启动/退出 smoke 通过；本机没有交互式桌面，未进行 Windows 物理剪贴板/快捷键验收。

新增 12 项测试覆盖零宽字符、控制字符、特殊空格、缩进换行、Emoji/多语言连接符、正常 Markdown/字面转义保留、清理幂等、清理后去重、敏感信息检查、大小限制、关闭开关、文件路径绕过、持久化及设置立即生效。

清理默认关闭，仅作用于新入库文本及从历史复制的文本。图片、文件路径、已有记录不改写；不直接覆盖外部应用刚复制的系统剪贴板，不进行粘贴注入。

[CI 38746819007](https://github.com/fqxxzyw/ClipVault/actions/runs/38746819007) 对源码 `e860609ee79063a16ce90e9e271e05bedd160cae` 全部通过：Ubuntu Python 3.11/3.12 各 170 passed / 3 skipped；Windows Python 3.11 为 169 passed / 4 skipped（额外跳过 Linux 专用测试）。Windows onedir 构建及冻结 EXE 启动/退出 smoke 通过。

完整 ZIP：54,427,040 字节，SHA-256 `31291d9f072e9e0178e1e787f80ce1ba854192f88f3b79291ce7637eb35f1c07`。
