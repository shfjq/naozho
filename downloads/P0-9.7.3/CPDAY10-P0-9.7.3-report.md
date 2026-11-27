# CPDAY10 · DailyWindowCheck 1.0.3 窗口采集根因与验证

**结论。** 1.0.2 在解析 mAttrs 时执行 section.indexOf('}')，把软键盘模式 sim={adjust=pan} 或 sim={adjust=nothing} 的结束符当成整个 LayoutParams 的结束符，并在截断后的字符串里找 fl。五个报错窗口的第一行都具备这个特征，而且内层结束符在 ty 之前。即使公开 fl 完好地到达 Java，这五个窗口随后写出的 fl 也无法被这段代码看到。ImageWallpaper 的第一行无 sim 分组，符合旧 JSON 摘要中它独自成功的表现。另一个缺陷是按至多四个空格的缩进猜测属性结束，较浅缩进的续行也可能被提前切掉。

## 依据和缺口

- DSH 报告设备为 CPDAY10 / Android 16、build 1784819045。核对本地原厂 services.jar 的 SHA-256 为 `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468`。classes3.dex 中 WindowState.dump 00a2/00a9 写 mAttrs 并调用 LayoutParams.toString(prefix)，0357 调用 getTouchableRegion，0675 输出 isVisible；WindowManagerService.dumpWindowsLocked 在 015f 输出窗口列表之后的 mBlurEnabled。Android 16 的 LayoutParams.toString 会先输出 sim={…}、ty=…，随后换行输出公开 fl= 及可选 pfl= 等字段。
- 本轮读取了粘贴任务和用户随后提供的六段原始字段、两个栏的主机结果及旧分类计数。此工作区没有可打开的第二阶段原始 ZIP、完整报告、freeme-classifier-102.json 和 13-原始窗口字段对照.txt 四个文件；309 / 547 行是用户报告的规模。没有将这些文件记作已逐行审核。
- 三个可直接复核的公开 flags 为导航栏的 3 项、状态栏的 3 项与 Freeme 的 6 项。两个装饰窗与壁纸的摘录均未提供公开 fl。固定证据文件 freeme-102-attrs.txt 按回复转录这些缺口。测试包装所用的窗口令牌、几何和补全用例的 flags 都与原始摘录分开。

## A、B 两条旧路径的逐步对照

| 问题 | 1.0.2 取证结果 |
| --- | --- |
| 1–4 · 命令与数据源 | 主机 window-fields → bar_sample → BAR_SLICE，通过 ADB shell 调用 dumpsys window -a visible。模块 check-windows → DailyWindowCheck → DailyBoard.visibleWindows，也调用 dumpsys window -a visible，经模块运行身份执行。两者查询同一 WMS 服务和子命令，但执行用户上下文、采样时刻及输出投影不同。原设备两次调用没有共享同一缓冲区。离线比较把同一份输入送给双方。 |
| 5 · 截断 | 旧模块在 sed 之后限制为 128 KiB、2.5 秒，并查窗口段尾；溢出或超时会停止。没有本次系统输出被截断的证据。Java 在单个属性组内做字符串截断可独立复现故障。 |
| 6 · Window 边界 | 模块按 Window #N 与 user 0 标识分段，另有两空格 summary 边界启发式。此次六窗数量、包和类型已被读出。旧模块在正确分段的单个窗口也能复现相同错误。 |
| 7–8 · 多行 mAttrs 与搜索范围 | 主机只要遇到正在跟踪的 SystemUI 栏，就独立提取行首的 fl/flags；内层 } 不影响它。模块对每个窗口都找 mAttrs，然后再按缩进和第一个 } 缩小缓冲区。由此出现同一数据源中，一方取得公开行，另一方报告不存在。 |
| 9 · 私有标志 | fl 是公开 flags。pfl、sysui、vsysui 属于不同字段。已有的三个原文样本都是合法的公开标志名，不需要把任何私有标志补入其中。 |
| 10 · 缩进、大小写、换行 | 本次提供的为小写 fl 与大写 Android 标志。回放时仅内层 } 即足以触发。另测了零/两/四空格、Tab、CRLF、等号两侧空白、换行续值。大小写错误与无法识别的公开值均不能推导出“安全”。 |

## 1.0.3 的数据流与权限

DailyBoard 直接以固定参数执行 /system/bin/dumpsys window -a visible，要求退出成功，超时 2.5 秒，原始输出上限 2 MiB。VisibleWindowDump 在内存中读取当前窗口列表，按 Window # 切块，要求系统段尾确认。到全局摘要、历史/附加列表时停止纳入窗口；隐藏系统告警或强制移除状态会被否决。写入诊断的内容仍为限定的结构化元数据。

WindowAttributes 在每个窗口内独立扫描同一 mAttrs，按花括号深度识别完整外层，保留换行，屏蔽内层值；仅解码顶层小写 fl 和 flags。可区分同/多行、缺字段、重复字段、字段落在属性组之外、格式未知和未闭合结构。数值仍按现有 Android 公开位定义解码，进制有歧义时停止。不会用上一窗的 flags，也不会把 pfl、sysui、vsysui 当成 fl。

日常监听、check-windows 和新版 window-fields 共用上述生产采集器、解码器。主机 window-fields 调用 DailyWindowCheck --bar-fields，只返回两个 SystemUI 栏经验证的公开标志信息。旧 BAR_SLICE 保留在显式 legacy-window-fields 中，以便比较历史工具结果。窗口诊断增加 collector_command、collector_source、window_block_index、flags_line_found、flags_parse_status、flags_source、flags_value_count、parser_error。保留 field_missing、class_reason、actual_blocker、触摸区域、焦点及遮挡证据。具体窗口标题、原始 WMS dump 和未识别标志文本不保存。

interactive_window_count 在此版本统计实际可交互的**内容窗口**，排除已验证的系统装饰和背景壁纸；单窗的 touchable 字段照实反映状态栏等窗口的输入能力。内容计数的口径改变不参与放行决策。前台 BASE_APPLICATION 可在身份、焦点、可见性及几何充分时单独识别；公开标志缺失时仍保留安全否决，因为 SECURE 位无法确认。缺少可选的私有字段不会把前台应用变成未知窗口。

## 新旧版本在同一输入上的试验

使用固定发布提交 5cae15d 的 1.0.2 源码编译旧生产解码器与过滤器，使用 1.0.3 生产代码作对照。分别给旧主机 BAR_SLICE、旧模块和新模块输入相同的窗口字段。测试未连接手机、未发广播。

| 输入 | 旧模块 | 新模块 |
| --- | --- | --- |
| 六段真实摘录加测试用 WMS 包装，保留三处 fl 缺口 | 六窗均 missing_flags；旧主机仍取得两个栏的 fl | 导航栏、状态栏、Freeme 三窗解析成功；三处缺口各自阻断，不能据此宣布普通桌面放行 |
| 相同摘录加独立的合成公开 flags，用于验证有完整字段的情况 | 前五窗 missing_flags、壁纸成功；可见/装饰/交互/阻断/未知为 6/0/1/5/5，与真机报告相符 | 面板依次 verified_passive_decor、verified_passive_decor，两条栏为 verified_edge_bar，Freeme 为 app，壁纸为 wallpaper。统计 6/4/1/0/0 |

新增 JVM 回归还覆盖乱序但编号有效的窗口、相邻窗口缺字段、嵌套 fl 字样、私有和 UI 命名空间冲突、FLAG_ 前缀、公开字段格式未知、焦点稳定性与快照边界。保留原有通知面板、控制中心、输入法、USB/权限/认证窗口、紧急/恢复窗口、未知覆盖、遮挡和多轮去重测试。测试次数、逐组结果及新旧回放结果见随包 P0973-offline-results.json。主机/Robolectric 的成功不能证明此版本在 CPDAY10 上已取得焦点、LOCKED + 80 或真实触控。

## 修改文件与构建

- kernelsu/naozho_power_daily/module/module.prop 更新为 1.0.3 / 4。
- 模块 src/com/naozho/power/{DailyBoard,DailyWindowCheck,VisibleWindowDump,WindowAttributes,Foreground}.java 更新采集、解析、诊断与内容窗口统计。
- 模块 test.py、tests/FreemeWindowsTest.java、tests/LayoutFieldsTest.java、tests/fixtures/freeme-102-attrs.txt 增加发布基线问题的回归。
- tools/p097/{cpday10_daily.py,test_daily.py,P0973-report.md,P0973-DSH.md} 更新主机工具、回归和手册。0.6.13-dev / 28 时钟和现有权限保护继续使用原包。计时、原值备份、监听方式、UID / DeliveryProof、维护暂停、开发退出、模块停用及卸载沿用原实现。

在发布源码根目录，以 JDK 17、NDK r27d、API 36 android.jar、Build Tools 35.0.0 D8、Python 3.9+ 运行：

```bash
python3 kernelsu/naozho_power_daily/test.py
python3 kernelsu/naozho_power_daily/build.py --ndk "$NDK" --android-jar "$ANDROID_JAR" --d8 "$D8" --out naozho-power-daily-1.0.3.zip
python3 tools/p097/export_tool.py cpday10_daily.py
```

下一次获准部署后先在关闭监听的状态运行 check-windows，直接读同一次快照中六窗的判定。现有资料足以修复已复现的截断，不需要 DSH 为本轮重采数据。若新版本某一窗仍失败，先看该次的 window_block_index、flags_parse_status、parser_error、class_reason 和 actual_blocker；无需提供完整系统日志。
