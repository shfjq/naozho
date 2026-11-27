# CPDAY10 P0-9.7.4 · 窗口快照解析报告

**版本**　naozho_power_daily 1.0.4 / versionCode 5。交付可供审查的模块。设备状态引用 DSH 报告，本轮无设备操作。时钟 APK 继续使用 0.6.13-dev / 28。

## 失败位置与对照

1.0.3 的 VisibleWindowDump.project 在进入窗口循环之前将 lines[0].trim() 与完整 WMS 标题作相等比较。DSH 提供的第一行为 Dump time，第二行才是标题，故直接返回 window_snapshot_header。此路径中尚未执行 footer、窗口、flags 或可触摸区域检查。用 1.0.3 已发布的生产解析器重放同一份六窗格式样本，去掉时间前缀时解析成功，仅在开头加入提供的时间行便稳定复现该错误。

| 证据 | 能验证的范围 |
| --- | --- |
| DSH 任务原文 | 命令 dumpsys window -a visible；共 316 行；第 1 行为时间，第 2 行为标题，第 295 行为两空格的 mBlurEnabled=true；结尾有 SnapshotCache、显示器和动画信息 |
| 云端固定回归 | 用实际生产解析器检查上述行位、六窗布局、旋转参数、缺失字段和异常边界。316 行**格式样本使用测试字段与填充行**。有充分字段的样本读出 6 个可见、4 个装饰、1 个交互内容、0 个阻断和 0 个未知窗口 |
| 真实 316 行原始文件 | 当前附件、既有下载和开发工作区只有本次摘要和上轮片段。原始输出未取得，真实输入回放待补；本轮没有从样本推断实机六窗已通过 |

保存的原始文件可在云端源码根目录用以下命令私下重放。脚本调用与模块相同的解析器，仅输出行位、分类和公开标志诊断。离线 Freeme 焦点使用报告描述及唯一的 launcher 窗口令牌；真机工作流程还会读取真实焦点并再次核对。原始文件不进入 Git 或交付包。

```bash
python3 kernelsu/naozho_power_daily/test.py --replay /path/to/private-visible.txt
```

## 从同一次命令读取窗口列表

- 模块保留 /system/bin/dumpsys window -a visible 的完整换行和起始空白。命令须正常退出，读取上限 2 MiB，超时 2.5 秒。发布版的 check-windows、window-fields 与日常监听都进入 DailyBoard.visibleWindows → VisibleWindowDump.inspect → Foreground / WindowAttributes。旧主机命令 legacy-window-fields 仅供历史格式比对。
- 标题按整行语法匹配 WINDOW MANAGER WINDOWS，可带已知括号命令、冒号、水平空白。先在同次读取中定位唯一标题与唯一的两空格 mBlurEnabled 布尔行，报告从 1 开始的行号，再解析中间开区间。未知诊断前缀只记为 redacted_prefix，已知 Dump time 行只允许数字时间格式。footer 后的 SnapshotCache、display、Animation 不产生窗口。
- 缺标题、缺 footer、次序颠倒、重复标志、中途换另一 WMS 段、空窗口块及命令不完整会得到独立拒绝原因。边界失败时不运行分类，分类计数为 -1。window_block_count 表示已完整识别起始行的块数，失败前可能尚未计数。
- 分段要求两空格 Window #、数值序号、Window 标记、用户与令牌。相邻窗口分别处理，异常编号、重复令牌、其他用户及显示器仍被拒绝。附加摘要不会给上一窗补字段。隐藏告警或强制移除列表仍会阻断。

## 基础 flags 和旋转参数

| 输入位置 | 处理 |
| --- | --- |
| 基础 mAttrs 中的 fl 或 flags | 配对最外层花括号，支持同行与多行；记录公开字段在此次原始命令输出中的行号 |
| sim={…}、paramsForRotation 及各个 ROTATION_n={…} | 内层字段不参与基础值，paramsForRotation: 作为字段边界；测试覆盖 0、90、180、270 度，包含与基础窗口相冲突的 SECURE / NOT_TOUCHABLE |
| mAttrs 结束后紧邻的单独公开字段 | 允许同一窗的唯一相邻字段，来源标为 after_attrs。已有基础值又出现独立值、跨过其他字段或位置不明均拒绝 |
| pfl、sysui、vsysui | 保持各自命名空间，不进入公开位掩码 |
| 缺公开字段或结构不完整 | 报出窗口索引、来源和 parser_error。未找到行号用 -1；attrs_brace_depth 为扫描结束时未闭合的层数，attrs_parse_status 描述结构。壁纸缺基础公开位时保留 missing_flags 否决，无法由其他窗口或旋转状态推断 SECURE |

在 CPDAY10 对应的 WindowState.dump DEX 中，0327–032d 在 mTouchableInsets 为 0 且没有 pending 时直接跳过两个触区字段；0357 仅在另一分支读取区域。因此状态栏缺少这两行时可使用已验证的窗口 frame。前提还有 SystemUI 身份、边缘几何、非焦点、公开标志和无实际遮挡。存在自定义 insets 但区域缺失、超出 frame、活动通知面板或其他未知覆盖仍拒绝。两个 ScreenDecorOverlay 继续按各自身份、包、几何与实际交互状态检查。

## 回归与修改范围

生产测试覆盖前缀与尾部、CRLF、不同标题缩进、多个相邻窗口及乱序字段、四个旋转子块、基础与私有标志、相邻独立 flags、缺 region、缺 wallpaper flags、缺失及截断。负向用例覆盖通知面板、控制中心、输入法、USB、权限、系统认证、紧急、恢复、未知浮层、真实遮挡和焦点变化。分组计数及真实原始文件回放状态见 P0974-offline-results.json。

| 源码位置 | 本次修改 |
| --- | --- |
| kernelsu/naozho_power/src/com/naozho/power/Board.java | 增加保留行位的限量命令读取，原有调用仍返回 trim 后的字符串 |
| kernelsu/naozho_power_daily/src/com/naozho/power/ | VisibleWindowDump 解析外层边界和独立窗口；WindowAttributes 分离旋转并记录来源；Foreground 输出结构诊断；DailyBoard / DailyWindowCheck 共用入口 |
| kernelsu/naozho_power_daily/module/module.prop | 模块 1.0.4 / 5 |
| kernelsu/naozho_power_daily/test.py、tests/LayoutFieldsTest.java、tests/SnapshotBoundaryTest.java | 生产解析回归和私下文件重放入口 |
| tools/p097/cpday10_daily.py、test_daily.py、P0974-report.md、P0974-DSH.md | 解析通过与拒绝诊断、兼容旧记录、更新部署文件和审查说明 |

构建仍使用 JDK 17、NDK r27d、API 36 android.jar、Build Tools 35.0.0 和 Python 3.9+。端到端验收需要真实的单次投递、前台焦点、LOCKED + 80 和触摸。云端测试只验证到模块、解析、回归和可重复构建。
