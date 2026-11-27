# CPDAY10 日常电源双击 1.0.1 技术与测试报告

本版供 CPDAY10 原厂 Android 16、KernelSU 3.3.1 和现有时钟 0.6.13-dev / 28 审查。系统设置准备工具默认选 600 ms，可选 400、500、700、800、1000 ms。安装默认关闭。手机上的 1.0.0 关闭、上一轮有一次额外窗口否决，均来自 DSH。1.0.1 的实际计时、触控和功耗待 DSH 测量。

## 两套计时如何衔接

以手机原厂 services.jar 的 SHA-256 `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468` 锁定输入。独立检查器读取 classes2.dex 的实际方法和分支。本包未收录固件。

| 原厂执行位置 | 对产品的影响 |
| --- | --- |
| SingleKeyGestureDetector 类初始化 0000–0005 | 读取 ViewConfiguration.getMultiPressTimeout 并缓存为静态字段。Android 参考实现从核心设置中的用户级 Secure.multi_press_timeout 取值，缺值可退到平台默认。写入后的读回只能证明设置已保存。 |
| interceptKeyDown 00c6–00df | 比较两次 DOWN 的 downTime。差值严格小于 T 才累加。600 档下 599 ms 在窗口内，600 ms 开始新的一击。不是从第一次松开开始计时。 |
| interceptKeyUp 009c、00d6、00e0、00fe–0100 | 若系统只支持一击，松开即派发单击。若还可等待后续按键，系统从松开后延迟 T 派发当前计数。达到系统最大多击数可更早派发。 |
| KeyHandler.handleMessage 0092–0096 → PowerKeyRule.onMultiPress → PhoneWindowManager.powerPress | 最后一次 DOWN 的 uptime、亮屏状态及 count 进入 WindowManager 的系统日志。count=2 路由到平台原有双击行为。 |
| PhoneWindowManager.interceptPowerKeyDown 0067–0077 与 powerPress 的单击分支 | 满足原厂条件时，熄屏单击由短按分支处理；非交互状态的按下可走 wakeUpFromWakeKey。单击唤醒没有新增模块等待。长按继续走系统 onLongPress。 |

观察器沿用 CLOCK_MONOTONIC 电源键时间。单次按住须短于已验证保守上限（最多 250 ms），两次 DOWN 至少相隔 40 ms 且小于档位 T。第二次 UP 后静默 T 才提交候选，有额外按键、重复、长按、队列过期或模式变化即放弃。应用侧仍限制从首次 DOWN 到最后 UP 最长 1000 ms，模块仍要求提交时距第二次 UP 小于 1500 ms。高档位下第二击按住过久，或系统负载过高，实际可用区间会缩短。

模块先核对用户 0 的设置值，再按手势核对 system_server PID、WindowManager 标签、两次物理 DOWN 的时间。要求同一第二击恰有一条亮屏 count=2，且第一击未单独派发。只在合格候选出现时做有界查询，空结果至多补读一次。若日志不可读、时间对不上、策略仍用旧值、屏幕中途睡眠或不再符合模式条件，即放弃本次。没有伪造输入或显示状态。日志缺失不能单独证明设置失效。

系统确实采用 600 且支持多击时，短按熄屏通常在松开约 600 ms 后由系统派发，再加显示管线耗时。该设置可能影响同一用户的其他系统多击手势，包括紧急手势的节奏。长按全局电源菜单、基本紧急呼叫入口需单独验收。只要出现异常就恢复原值。这里没有新增系统按键拦截器。若正常重启后仍只能在原厂短窗口内通过，停在系统集成评估，核对厂商是否支持更新 SingleKeyGestureDetector 的有效阈值。替换输入处理、框架改动需另行评审。

Android 对照源码见 [ViewConfiguration](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/core/java/android/view/ViewConfiguration.java) 和 [SingleKeyGestureDetector](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/policy/SingleKeyGestureDetector.java)。

## 窗口分类及边界

从 WMS 的可见窗口快照按 Z 顺序读取。针对手势前后的真实焦点、窗口 ID、用户、显示、所属包、类型、标志和几何证据共同判断。只把窗口元数据用于判断，窗口标题不写入文件。以前的 skipped_additional_visible_window 无法反推是哪一扇窗口。

| 现场证据 | 处理 |
| --- | --- |
| SystemUI 的 StatusBar、NavBar / NavigationBar、SecondaryHomeHandle0 | 需匹配已知类型、不可获得焦点，且窗口是贴屏边窄条（厚度不超过相应显示维度的六分之一）。 |
| SysDecor、ScreenDecorOverlay | 仅接受 SystemUI 或平台 UID 1000 的 android 包、已知装饰类型、不可聚焦不可触摸且有边缘几何。未知全屏装饰保留否决。 |
| Wallpaper | 可接受在已确认前台窗口下方的 WALLPAPER 层。 |
| 未显示组件，包括 ShellDropTarget | 无焦点、isVisible 和 isOnScreen 均为 false，且无 surface 或 View 确实处于 INVISIBLE/GONE 才归为 inactive。缺席于 visible 查询的组件无需放行。 |
| 通知面板、ControlCenter、输入法、活跃拖放、USB 弹窗、系统安全窗口 | 活跃、遮挡、受保护或证据不完整时放弃。有安全标志、其他用户或未知显示、窗口集不完整也会放弃。 |
| Freeme、系统设置首页、普通应用 | 保留已审查的 Freeme、根设置首页，以及哈希锁定的 OpenCalc 主界面；已审查的第三方页面配置可复用。此轮不会自动批准所有前台包。 |

Android 没有能证明普通 Activity 内当前没有凭据页、支付页或恢复页的通用窗口标志。同一 Activity 可无窗口切换地更换内容。后续可由开发侧统一提供与版本绑定的页面配置，或由厂商提供可验证的系统交互状态。用户无需逐应用编写规则。

最新否决单独覆盖写入 last-veto，含 last_veto_at（Unix 毫秒）、last_veto_reason、额外窗口数、当次按下间隔和最多九条分类元数据。未取得快照记为 -1 或 unknown。每行提供窗口类型、包、实际可见、在屏、surface、焦点、是否可聚焦/触摸、是否被更高层遮挡、边缘几何及类别。这些字段不能推测用户正在输入什么。last-return 只保存最近一次成功的间隔、策略计数和投递计数。文件留在手机本地。

## 权限、资源和测试

继续只读监听已有专用节点的 KEY_POWER，逐客户端屏蔽其他按键，内核阻塞等待。无独占、无输入注入、无系统分区写入、无常驻 logcat、无持有唤醒锁。使用原受保护 Receiver 及同身份投递自证，时钟自行在焦点处确认 LOCKED。新增可选设置准备只改用户 0 的 multi_press_timeout，记录原值及缺省态。具体停用、卸载和断电恢复见手册。按手势读取的 WMS 和系统策略日志是有界的；日志按日或大小轮转，每个轮转文件最多 8 KiB。DSH 的可选 30 秒测量票只在既有监听器中记录一对 POWER 的三个时长，不添加监听进程。

| 已执行的离线验证 | 可支持的结论 |
| --- | --- |
| 原厂 DEX 分支检查 | 缓存、严格小于的比较、松开立即或延迟分支、系统双击回执、单击睡眠与按下唤醒调用。没有测出面板物理延迟。 |
| 生产 Java 状态机和 Robolectric | 100、200、300、400、500、599、600 ms，各档 T−1/T/T+1，长按、抖动、静默窗口、维护暂停、恢复、已锁定、过期和重复、焦点消费与 flags=80。 |
| 生产窗口分类、定时恢复和原生代码 | 验证边缘装饰、前台/壁纸顺序、活动与未显示系统窗口、缺失字段、敏感标题不落盘、原值不存在/已存在/外部改变、唯一监听和停用。主机管道连续 10,000 个事件后未增加打开的 FD。 |
| 打包与交付 | arm64 JNI 与 API 36 DEX 构建、ZIP 完整性与权限、从发布源码再次构建比较、独立 DSH 工具。机器计数见随包 P0971-offline-results.json。 |

## 修改文件

- kernelsu/naozho_power_daily/module 下更改 module.prop、customize.sh、uninstall.sh，新增 timing.sh。
- kernelsu/naozho_power_daily/src/com/naozho/power 下更改 DailyPower、DailyBoard、Foreground、DailyLog，新增 TimingSetup、TimingLease、TimingSample、PolicyReceipt。
- platform/station/android/com/naozho/station/StationPowerShortcut.java 以两次非重复 DOWN 划分序列。
- kernelsu/naozho_power_daily/test.py、tests/DailyTest.java 和 app/src/testDevelopment/java/com/naozho/clock/mode/ConfirmedPowerReturnTest.kt 补充回归。应用生产代码、Manifest 与安装包沿用 0.6.13。
- tools/p097 下更改 cpday10_daily.py、test_daily.py，新增 verify_firmware_timing.py、本报告与 P0971-DSH.md。

## 可复核构建

环境为 JDK 17、Android API 36 android.jar、SDK Build Tools 35.0.0 的 D8 与 dexdump、NDK r27d，主机测试使用 Linux、GCC、Python 3.9+。

```bash
python3 kernelsu/naozho_power_daily/test.py
python3 kernelsu/naozho_power_daily/build.py --ndk "$NDK" --android-jar "$ANDROID_JAR" --d8 "$D8" --out naozho-power-daily-1.0.1.zip
python3 tools/p097/export_tool.py cpday10_daily.py
./gradlew :app:testDevelopmentUnitTest --tests '*ConfirmedPowerReturnTest' --tests '*PowerReturnActivityTest'
# 开发侧有本次原厂文件时可额外复核，DSH 无需重新提取
python3 tools/p097/verify_firmware_timing.py --firmware "$SERVICES_JAR" --dexdump "$DEXDUMP"
```

## 开机第一屏交接

目前证据覆盖开机模块就绪后拉起时钟，以及独立锁定。开机动画退出至首个可交互窗口之间是否出现锁屏/Freeme 仍待独立验收。下一阶段先沿用已有 P0-9 启动链和厂商 HOME 过滤证据核对首个窗口由哪个系统组件选择，单独评审可回滚的交接点。双击模块不参与开机选桌面。
