# CPDAY10 日常电源双击 1.0.2 · Freeme 窗口分类与验证

模块 naozho_power_daily 1.0.2，versionCode 3；适用现有 arm64 CPDAY10 Android 16、KernelSU 3.3.1、时钟 0.6.13-dev / 28。源基线 5db8441516cea6cbf4c3d29ea3b1b1a96af5f2e6，与下载提交 4b3b507870aacd9645bec679b34cd07462529e8b 中的 1.0.1 模块源码逐文件核对一致。本次仅在开发电脑上运行。时钟 APK 沿用原包。

## 实机证据与结论

DSH 的这次自然双击实测为 DOWN 间隔 282 ms，两次按住 163、122 ms，无休眠迹象，前台为 Freeme。旧模块记录 attempts=0、delivered=0、skipped=2。旧记录中六个窗口自上而下为两个装饰面板、导航栏、状态栏、Freeme 和壁纸。两个 SystemUI 装饰面板身份经 DSH 确认为 ScreenDecorOverlay 和 ScreenDecorOverlayBottom。

1. **装饰类型判断有误，已定位。** 旧代码对 NAVIGATION_BAR_PANEL 只识别特定手柄；两个 ScreenDecor 窗口走到 additional_visible_window。
2. **两个栏的公开属性无法解析，原始编码尚缺。** 旧生产代码只截取独占一行的 fl=，再用“0 或大写标志名称”校验整行。字段缺失、非预期分隔符、数值掩码以及内联输出都可能得到同一个 unknown。旧日志没有原始 flags、mTouchableInsets 和 touchable region 行，无法从中确定上次两扇栏窗口究竟采用哪个编码。
3. **旧版与新版使用同一输入作过对照。** 按 DSH 的六窗顺序、类型、包与角色重建输入，用公开 flags 的数值和混合编码补充缺失样本。原 1.0.1 生产解析器得到 unclassified / unclassified / unknown / unknown / app / wallpaper；1.0.2 得到 decor / decor / decor / decor / app / wallpaper。只提供旧报告中的 unknown、不给两个栏补充可验证 flags 时，新版仍给出两个阻断项。此前真机从未投递本次请求；完整实体双击验收留待批准。

回归证据保存在源码的 kernelsu/naozho_power_daily/tests/fixtures/freeme-0971-evidence.json。该文件只转录本次提供的分类元数据。测试补充的矩形、窗口编号、标志写法与窗口令牌是独立测试输入。

## 固件和 Android 16 的字段依据

本地校验 CPDAY10 services.jar SHA-256 为 `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468`。classes3.dex 的 WindowState.dump 在 00a2–00b0 输出 mAttrs 并调用 LayoutParams.toString(prefix)；0337–0362 输出自定义触摸内边距、调用 getTouchableRegion 并打印区域；065a 和 0675 输出 isOnScreen 与 isVisible。WindowManagerService.dumpWindowsLocked 的 015f 开始打印所有窗口之后的 mBlurEnabled，采集器将这个实际段尾转成固定完成标记。命令出错和缺少段尾均拒绝。未发布固件或设备原始输出。

Android 16 的 LayoutParams.flags 中 NOT_FOCUSABLE 为 0x8、NOT_TOUCHABLE 为 0x10、SECURE 为 0x2000。ViewDebug.flagsToString 可输出标志名，未找到映射时可返回无前缀十六进制。焦点归属另取 WMS 的当前焦点和前台 Activity。焦点能力取自公开 flags；窗口没有当前焦点这一事实不足以推定它不可聚焦。flags 给出的触摸能力与实际触摸区域分别报告。

| 字段或输出形状 | 1.0.1 | 1.0.2 的处理 |
| --- | --- | --- |
| 单行 fl=NOT_FOCUSABLE … | 只支持旧名称格式 | 按 Android 公开标志名解释，识别 FLAG_ 前缀、空白、逗号和竖线 |
| fl=0x80000008、名称加 0x…、负的 32 位十进制掩码 | 多数归为 unknown | 解码公开位并独立检查 SECURE；符号名称不认识则阻止 |
| 无前缀数字、LayoutParams 头内 flags=…、fl=… pfl=… | 缺少格式证据 | 内联及独立字段分别解析，忽略私有 flags。纯数字按十六进制和十进制解释若导致三个保护位结论不同，则标 ambiguous_radix |
| 缺失、重复、空值或无法识别的公开 flags | 三种能力混为未知 | 保持 unknown；给出 missing_flags、duplicate_flags、empty_flags、unknown_token 等原因 |
| mTouchableInsets 与 touchable region=SkRegion(…) | 采集前即过滤掉 | 区分默认 frame、空区域、完全在 frame 内的区域、超界、缺失或不可解析。自定义区域未读到、insets 尚在变化或区域越界时，装饰候选被阻止 |
| 只读到前几个窗口、窗口序号断裂、重复 ID 或跨用户/显示 | 部分不完整情况无法定位 | 要求系统窗口段结尾、连续编号、唯一窗口身份、用户和显示正确，以及前后焦点一致 |

[Android 16 WindowManager.LayoutParams](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/WindowManager.java) · [ViewDebug](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/ViewDebug.java) · [WindowState](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/wm/WindowState.java)

## 放行与诊断

- 新增的 NAVIGATION_BAR_PANEL 装饰身份只有两个精确名称。要求 user 0、display 0、系统 UI 包、实际显示、有 surface、未获焦、不可聚焦、不可触摸、未被遮挡、窗口是显示范围内的窄边（厚度至多为相应维度的六分之一），且触摸区域证据合理。其他同类型窗口单独判断；未知身份被阻断。
- 导航栏和状态栏须是既有的确切身份与类型，满足上述位置、可见性、非焦点和不可聚焦条件。正常栏可以接收手指触摸；报告的自定义触摸区域须局限在栏内。显示区域上的所有其他窗口仍参加检查。实际通知面板、控制中心、输入法、弹窗、认证、紧急、故障恢复、未知覆盖或不稳定焦点会阻止请求。
- 每扇窗口有 class、class_reason、parser_source、field_missing、focusable_parse_status、touchable_parse_status、geometry_valid、edge、obscured、touch_region 和 actual_blocker。同时保留归属包、窗口类型和输入能力。标题、窗口 token、界面内容、截图与输入内容不落盘。
- 总计数分别为实际可见、已认证装饰、具有交互能力的活动窗口、阻断窗口、未知窗口。可触摸的正常状态栏可同时计入装饰与交互；计数含义独立。blocking_window_count 指此次窗口检查本身判定的阻断项。全局焦点或权限检查也可能独立否决。未取得完整快照前总数记为 -1。最多保存 24 条明细，超出则标记遗漏、保留优先阻断项并放弃本次请求。
- last-veto 保存最近一次否决。last-window-check 保存最近一次成功投递所依据的窗口检查，含时间和投递序号。两个文件均覆盖写入。新增 check-windows 可在已装 1.0.2、监听关闭时只读执行同一生产分类器，独立查看当前 Freeme 判断，无需碰电源键。
- 输入设备打开方式、按键状态机、600 ms 档位、原值备份、DeliveryProof、Receiver、Owner、原应用白名单和开机模块均沿用既有实现。新增读权限用途仅是 WMS 窗口元数据；成功或故障诊断不需要采集 ADB UI 树。没有常驻新增进程。

## 测试与构建

测试使用模块实际 sed 采集过滤器、Java 分类器及 DailyReturn 提交流程。Freeme 专项覆盖六窗正例、缺字段原例、名称及掩码格式、缺失/冲突/安全位、未知同类型面板、错误包/用户/显示、异常几何、真实可触摸状态栏、空/超界/丢失区域、通知/控制中心/IME/USB/权限/认证/紧急或恢复窗口、不完整快照、焦点在检查期间变化，以及连续五轮每轮恰好一次提交。负向用例使用输入窗口属性和系统窗口类型构造；手机实际皮肤、实际触摸与系统投递仍需实测。完整执行结果见 P0972-offline-results.json。

从源码目录使用 JDK 17、Linux GCC、Python 3.9+、Android 36 SDK、D8 和 NDK r27d。构建仅针对模块。可独立重跑以下命令。

```bash
python3 kernelsu/naozho_power_daily/test.py
python3 kernelsu/naozho_power_daily/build.py --ndk "$NDK" --android-jar "$ANDROID_JAR" --d8 "$D8" --out naozho-power-daily-1.0.2.zip
python3 tools/p097/export_tool.py cpday10_daily.py
```

## 修改文件

| 位置 | 改动 |
| --- | --- |
| kernelsu/naozho_power_daily/module/module.prop | 版本 1.0.2 / 3 |
| 模块 src/com/naozho/power/{Foreground,WindowAttributes,WindowGeometry}.java | 分类、公开标志、几何与触摸区域解析 |
| 同目录 {DailyBoard,DailyWindowCheck,DailyLog,DailyPower}.java | 采集与焦点复核、只读诊断入口、最新一组诊断的保存 |
| 模块 test.py、tests/FreemeWindowsTest.java、tests/fixtures/freeme-0971-evidence.json | 实机证据转录、使用生产代码执行的回归 |
| tools/p097/{cpday10_daily.py,test_daily.py,P0972-report.md,P0972-DSH.md} | 兼容新旧诊断、最小只读采样、验收工具测试及两份交付文档 |
