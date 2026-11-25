# CPDAY10 · 0.6.6-dev HOME 对照与整机验收

**从 0.6.5-dev / 20 的独立锁定开始。** DSH 已在 CPDAY10 Android 16 上确认 LOCKED、independent=true、flags=80、名单仅 com.naozho.clock。手指上划两次及五次后触摸有效，电源键灭亮正常，开发退出取消保持锁定，确认退出回到 Freeme，点击图标可重新锁定。16:19:24 至 16:20:37 的取消专项无退出记录。15:39:01 的旧记录仍无归因。准备好采样后再在手机上确认「开发退出」。

## 交付与复核

| 文件 | 用途 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| naozho-0.6.6-dev-debug.apk | com.naozho.clock，0.6.6-dev / 21，覆盖安装 | 11631572 | `d929a9192aec61ede294a859aa0edd66d4d06b9569db5219aee75082c1dcc89c` |
| naozho-homeprobe-1.0-debug.apk | com.naozho.homeprobe，1.0 / 1，独立安装 | 8937 | `f32858ec1133a8b7cae7cefc55711e46a439223680a669a68790cc8132456585` |

两个 APK 均通过 apksigner、ZIP 完整性和对齐检查。主包签名证书与 0.6.5 一致，SHA-256 为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。最终主包 Manifest 与 0.6.5 的差异仅有版本字段。Device Owner 接收器仍为 `com.naozho.clock/.display.ClockDeviceAdmin`。

## 第一次只比较两个 HOME

0.6.4 实机清除 Freeme 策略后条目消失，写时钟收到 SET，但有效 HOME 仍为 Freeme。Android 16 AOSP 的 findPersistentPreferredActivity 会在本次解析候选中寻找所选组件。要定位 CPDAY10 为什么只有限定包名才查得到时钟，先引入一个只有普通 HOME Activity 的独立 APK。它与主包 targetSdk 相同，有 MAIN、HOME、DEFAULT，独立 UID，无设备管理或锁定权限。安装 HOME 候选本身可能使系统重新评估桌面偏好，故先取基线。[Android 16 PackageManager 实现](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/pm/ComputerEngine.java)

1. 在 0.6.5 上走正常开发退出并确认。见到 Freeme 后，用 Windows PowerShell 执行下方命令。只连接待测手机，多设备时给 adb 指定 `-s 序列号`，给脚本指定 `-Serial 序列号`。保留输出，确认 user 0、Owner、NONE 和 Freeme。
2. 先只装对照包，主包仍用已验收的版本。显式打开对照页一次，点亮状态下运行脚本，再点「结束对照」。对照应用没有桌面图标；出现系统桌面选择器时请保留原 Freeme，勿把对照设为默认。脚本只读取状态。
3. 在「时钟管理员恢复」点「记录 Home 诊断」补充时钟自身 UID 的视角。普通时钟图标会恢复独立锁定，准备阶段请用独立恢复图标。

```powershell
adb devices -l
adb shell dpm list-owners
adb shell dumpsys activity activities | Select-String 'LockTaskModeState'
adb shell cmd package query-activities --components --user 0 --query-flags 0 -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell cmd package resolve-activity --brief --user 0 --query-flags 66560 -a android.intent.action.MAIN -c android.intent.category.HOME
Get-FileHash .\naozho-homeprobe-1.0-debug.apk
adb install -r .\naozho-homeprobe-1.0-debug.apk
adb shell am start -W --user 0 -n com.naozho.homeprobe/.MainActivity
.\Compare-Cpday10Home.ps1 | Tee-Object .\cpday10-home-control.txt
adb logcat -d -s NaozhoMode:I > .\cpday10-clock-home.log
```

### 用结果决定下一步

| 同一用户、同一时间、同一查询条件下的结果 | DSH 接下来做什么 |
| --- | --- |
| 任一包在限定包名时也缺失 | 核对脚本中 user 0 的 installed、enabled、suspended、stopped、组件和实际版本。先恢复可比较的安装及前台用户状态。 |
| 两包限定查询均有。全局有对照，缺时钟 | 保留两包 dumpsys package 及「记录 Home 诊断」，比较无 category 的 MAIN、HOME 和 HOME+DEFAULT。问题已缩小到与时钟包、组件或其管理状态相关。下一轮可在同一个时钟包增加临时最小组件作进一步对照。 |
| 两包限定查询均有。两包在全局均缺失 | 留存系统角色和策略快照。若存在已核对的单一 Freeme 持久 HOME，可在 NONE 按下节的审计与独立清除流程再采一份对照，报告清除前后差异。需要以同条件在标准 API 36 系统复核，厂商限制尚待证实。 |
| Shell 与应用 UID 答案不同，或仅改变 flags 就改变结果 | 附脚本的完整命令、两种 UID 的原始输出和采样时间，复核包可见性、用户状态和 Intent 筛选条件。保持 NONE。 |
| 两包全局都存在 | 可以继续验证有效 HOME。尚未选择时钟时，Freeme 仍为默认符合预期。 |

每种结果均可从「结束对照」回到原界面。在 NONE 完成采样后，可用 `adb uninstall com.naozho.homeprobe` 只移除独立测试包，重新采全局 HOME 和有效 HOME。若主包仍缺失，先交回对照结果。保留已验证的独立锁定方案。

## 第二次才验收完整专机

1. 在 NONE / Freeme 核对主包哈希并执行 `adb install -r .\naozho-0.6.6-dev-debug.apk`。从 Freeme 打开「时钟管理员恢复」，选择「暂停专机并恢复原桌面」，结束此前保留的独立配置，再核对 Owner 和已保存的 DroiClaw。如果缺少恢复图标，可只在准备阶段用 `adb shell am start --user 0 -n com.naozho.clock/.mode.AdminRecoveryActivity`。复查更新后时钟在全局 HOME 中。
2. 在 NONE 点「登记 DSH 已核对的 HOME 策略」→「准备读取编号」，运行已有的 Read-Cpday10HomePolicy.ps1，并在五分钟内点「导入设备策略清单」。该工具读取 user 0 的策略并写入本应用的诊断回执。若发现额外策略或回执失效，先保存提示。需要采清除后的对照时，使用「仅清除已核对的 HOME 策略（NONE）」，再查实际条目和解析。[策略审计脚本](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/Read-Cpday10HomePolicy.ps1)
3. 「开始退出预演（保持未锁定）」切到时钟。下列两种 resolve 均须为 `com.naozho.clock/.MainActivity`，全局含该组件；在 NONE 按真实 Home 也应回到时钟。开发退出确认后两种 resolve 须变回 `com.droiclaw.launcher3/com.freeme.launcher.FreemeLauncher`，桌面可以停留。结束预演。若 SET 成功但实际解析仍为 Freeme，请保存下方记录及操作编号，先停在 NONE。
4. 在维护页点「启用专机并进入时钟」。读回有效 HOME、`state=LOCKED independent=false flags=80` 和唯一允许包 `com.naozho.clock`。手指连续上划两次及五次，每次都实际点开并取消开发退出弹框。试返回、Home、最近任务及实体电源键熄屏再亮。确认触摸仍有效且全程 LOCKED。
5. 明确确认开发退出，查 NONE、两种解析回 Freeme。留在桌面观察后，用真正的「小方块时钟」图标回来，再查有效 HOME、LOCKED、80、触摸。Owner 应始终保留。

```powershell
adb shell cmd package query-activities --components --user 0 --query-flags 0 -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell cmd package resolve-activity --brief --user 0 --query-flags 66560 -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell cmd package resolve-activity --brief --user 0 --query-flags 65536 -a android.intent.action.MAIN -c android.intent.category.HOME -c android.intent.category.DEFAULT
adb shell dumpsys activity activities | Select-String 'LockTaskModeState|topResumedActivity|mResumedActivity'
adb shell dumpsys window windows | Select-String 'mCurrentFocus|mFocusedApp'
adb logcat -d -s NaozhoMode:I > .\step-home.log
adb shell dumpsys device_policy > .\step-policy.txt
```

每步换用新的输出文件名。若全局有时钟但设置后解析仍不变，再保存 `adb shell dumpsys role`、`adb shell dumpsys package preferred` 和 `adb shell cmd package query-activities --user 0 --query-flags 65600 -a android.intent.action.MAIN -c android.intent.category.HOME -c android.intent.category.DEFAULT`，比较候选优先级、过滤器、策略值和默认角色。遇到回退请同时保留失败及恢复 Freeme 的两段日志。

## 重启验收

在**完整专机**中记录 boot_count、有效 HOME、LOCKED、flags 和可触摸状态，用手机电源菜单正常重启。等待首次画面，记录是否有任何人手动解锁或点图标。如 ADB 尚不可用，先用另一台设备记录屏幕经过；连接恢复后只读采样。

```powershell
adb shell getprop sys.boot_completed
adb shell settings get global boot_count
adb shell am get-started-user-state 0
adb shell dpm list-owners
adb logcat -d -s NaozhoMode:I | Select-String 'Home recovery|Direct Boot|Lock Task after start|Clock window'
```

同时采集上节的两种 HOME、前台组件和锁定状态。通过条件为新 boot_count、用户未手动解锁或打开应用、有效 HOME 与可操作前台均为时钟、LOCKED、flags=80、名单仅时钟。仅见简版 Direct Boot 时钟或仅收到 BOOT_COMPLETED 时继续记录。需要手动首次解锁、点时钟图标或用 ADB 拉起时钟才恢复，均记为未通过自动恢复，并记录该动作前后的读数。

## 云端验证

- development 116 项、debug 106 项主机测试全部通过，两组有共享用例。覆盖完整专机与独立路径、旧 112 迁到 80、切回时钟前检查、HOME 全局候选消失时拒绝启动完整锁定、开机恢复及退出行为。两套主包与对照包的 Lint 均为零错误，分别有 9、7、2 项警告。
- AOSP API 28 软件模拟器上，独立对照 Activity 与 adb shell 均在全局和限定包名下查到两个 HOME。另在模拟器设置测试 Owner 并移除对照包，调用主包的部署、暂停、再次启用流程，两种系统解析依次为时钟、Launcher3、时钟，Owner 保留。API 28 读回功能标志 16；数值 80 适用于支持 bit 64 的较新系统。
- Windows 用的只读脚本经过 PowerShell 7 + API 28 实际输出验证。API 36 精确 flags 对照、Freeme、触摸、电源、退出再进入与重启均需 DSH 在 CPDAY10 实测。
- API 28 模拟器另做了一次操作系统重启。boot_count 从 13 到 14，设备自动进入 RUNNING_UNLOCKED，系统 HOME 与 resumed Activity 均为时钟。重启前后均读到 SystemUI 无响应弹窗占有窗口焦点，锁定状态为 NONE。此轮只验证了自动返回时钟，未通过重启恢复锁定与触摸验收。整个重启观测期间只读采样，无手动解锁或拉起时钟。
- 代码提交 `5cde079`，开发分支 `work`。0.6.5 独立锁定的真机结论沿用 DSH 实测；完整专机的第一次 CPDAY10 实测请单独归档。
