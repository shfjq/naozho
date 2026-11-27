# CPDAY10 · 1.0.4 完整真机采样离线回归

**结论**　已发布的 naozho_power_daily 1.0.4 / versionCode 5 直接解析完整 316 行 visible 输入，返回 ordinary_freeme。6 个可见窗口中有 4 个系统装饰、1 个交互内容窗口、1 个壁纸；阻断和未知均为 0。此次补充回归、旧版复现工具和报告。生产解析器沿用源码提交 353682c，重新构建所得模块与原发布文件逐字节相同。手机没有连接，实际在线采样、投递、锁定及触摸须另行验收。

## 输入完整性与时钟来源

ZIP 为 11,588 字节，SHA-256 为 `7b43deaf77eec27f147352b4635dceeef6ef05ed93b489916785d24c150e6206`。ZIP CRC 通过，内部清单中 5 个文件的字节数、SHA-256 全部吻合。清单自身 SHA-256 为 `5983edead8f710cf07ba6a156e20347ea88cdc34fdd460f7d8f2465ef7226182`，其完整性由外层摘要覆盖。两份 stderr 均为 0 字节。私有输入按原字节保留。

| 采集 | 字节 | 内容行 | 标题 / footer 行 | SHA-256 |
| --- | ---: | ---: | --- | --- |
| visible | 28,802 | 316 | 2 / 295 | ad1055999e0c458b867523956bffe396db8215a490cc91d72c1f3f5de01e7071 |
| windows | 45,545 | 512 | 2 / 491 | 0b8331033e8e7f1c03ae00068e62bd5c426f8c5e674e4cba19f3e1e8a303e52a |

两文件均为 UTF-8、无 BOM、CRLF、末尾有换行；按换行切分多出的末尾空串解释了清单中的 317 / 513。环境报告记录为 `2026-11-27T16:15:07.420+08:00 ~ 2026-11-27T16:15:16.436+08:00`。两份 dump 的时间行依次为 `Dump time : 2026-11-27 04:15:11.544`、`Dump time : 2026-11-27 04:15:14.612`。以上照录，本报告未对时钟差异作换算。本次附件是补采样本。

## 1.0.3 的失败点

对固定发布的 1.0.3 源码归档校验 SHA-256，编译其中真实的 VisibleWindowDump、WindowAttributes、Foreground 及其依赖。宿主只替代 WMS 命令的数据来源与输出，同步使用设备报告记录的焦点。命令读取的 UTF-8 解码和首尾 trim 按 1.0.3 的 Board.command 实现重放。CRLF 进入按 `\\r?\\n` 切分的生产代码。

| 生产版本及输入 | 实际结果 |
| --- | --- |
| 1.0.3，完整 visible | window_snapshot_header，0 行窗口诊断，5 项分类计数均为 -1 |
| 1.0.3，只在内存副本中移除首行 | ordinary_freeme，6 / 4 / 1 / 0 / 0 |
| 1.0.4，完整 visible | ordinary_freeme，6 / 4 / 1 / 0 / 0；原始首行保留 |

正确标题位于第 2 行；1.0.3 强制将 lines[0].trim() 与标题作相等比较。时间前缀完整保留下来，解析在进入 footer 和窗口循环前即返回。去首行对照证明旧 footer 对本快照的两空格布尔行匹配有效。两份原件都含完整段尾、后续两处 SnapshotCache 及末尾动画字段，大小低于 2 MiB 上限；本次复现无需引入传输截断假设。单次历史设备进程内的缓冲区没有独立记录。基线复现的完整脱敏输出见 P0974-baseline103.txt。

## 六窗逐项结果

行号指 visible 原始行。角色以显示顺序和用途标示；窗口令牌、原始标题和界面内容都留在私有文件中。回放使用环境报告里的 mCurrentFocus 和 mFocusedApp 校对包及令牌。

| 角色 | owner | type | class | class_reason | flags_source / flags_parse_status | fl 行 / 标志数 | field_missing | geometry_valid | actual_blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 底部装饰 | com.android.systemui | NAVIGATION_BAR_PANEL | decor | verified_passive_decor | flags_line_names / parsed | 7 / 6 | none | true | false |
| 顶部装饰 | com.android.systemui | NAVIGATION_BAR_PANEL | decor | verified_passive_decor | flags_line_names / parsed | 36 / 6 | none | true | false |
| 导航栏 | com.android.systemui | NAVIGATION_BAR | decor | verified_edge_bar | flags_line_names / parsed | 65 / 3 | none | true | false |
| 状态栏 | com.android.systemui | STATUS_BAR | decor | verified_edge_bar | flags_line_names / parsed | 152 / 3 | none | true | false |
| 前台桌面 | com.droiclaw.launcher3 | BASE_APPLICATION | app | focused_application | flags_line_names / parsed | 227 / 6 | none | true | false |
| 背景壁纸 | com.android.systemui | WALLPAPER | wallpaper | below_foreground | flags_line_names / parsed | 261 / 6 | none | true | false |

两个装饰窗触区为空；导航栏实际触区位于自身 frame；状态栏允许触摸、未取得焦点、触区使用默认 frame。该固件在默认 insets 且无 pending 时省略触区行。判定同时核对窗口身份、焦点、可见性、几何与遮挡。完整壁纸块此次实际提供 6 个公开标志。

## 13 窗对照与旋转隔离

每份 dump 分别进入同一生产解析器。另按令牌、用户及组件身份在内存中关联窗口。visible 的 0–5 号依次对应 windows 的 0、1、4、7、10、12 号。比较各窗口从头行之后到下窗或全局摘要之前的全部字段，六对记录相同；生产分类与字段诊断也相同，只有列表序号、原始来源行随命令改变。

windows 独有 2、3、5、6、8、9、11 号。七窗分别满足 isVisible=false、isOnScreen=false、mHasSurface=false。可证实它们在该采样中不可见，未用类型推断父子关系。日常监听仅执行 visible；对照结果不会参与返回决策。

两份数据分别含 14 / 21 行公开 fl、14 / 21 行私有 pfl。每份各有两个 paramsForRotation 段、八个旋转条目。visible 中六个基础窗口的公开标志逐一与其原始 fl 行一致。独立测试在内存副本中把全部八个旋转 fl 改为与基础状态冲突的值，同时改变私有 pfl 和 vendor vsysui，生产分类和逐窗诊断完全相同；另将真实基础窗口设为 SECURE，生产代码拒绝。实际输入没有独立 sysui 行，其命名空间还由既有格式回归覆盖。

## 生产入口、安全测试与复现

check-windows 和 window-fields 都运行 DailyWindowCheck，后者仅改变输出字段；两者及日常监听均经 DailyBoard.visibleWindows → VisibleWindowDump.inspect → Foreground / WindowAttributes。现场运行还需核对实时焦点及其稳定性。回放只读环境报告中的观察值。

附加安全窗口的负向测试均在原始 visible 的内存副本上分别执行。生产解析器拒绝了通知面板、控制中心、输入法、USB、权限、认证、紧急页面和未知覆盖；真实快照的遮挡位修改、前后两次焦点不一致也均被拒绝。没有扩大应用或系统窗口白名单。机器可读结果与测试计数见 P0974-offline-results.json。

云端复现使用 JDK 17、Python 3.9+。下列路径使用本地私有解压目录及已发布的 1.0.3 源码 ZIP。真实输入无需加入源码库。

```bash
python3 tools/p097/baseline103/replay.py /path/to/CPDAY10-P0-9.7.3-source.zip /path/to/private/extracted
python3 kernelsu/naozho_power_daily/test.py --capture-dir /path/to/private/extracted
```

本轮源码调整集中在模块 tests/CapturedWindowsTest.java、test.py、tools/p097/baseline103/{Replay103.java,replay.py} 和两份 P0974 Markdown。生产模块仍使用 1.0.4 的快照起止检测、独立窗口切片、平衡的 mAttrs 括号及基础 flags 行位追踪。计时策略和 APK 均沿用当前版本。
