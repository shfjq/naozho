# CPDAY10 · 保留 Freeme 的开机独立锁定验收

部署包 `com.naozho.clock`，0.6.7-dev / 22。直接覆盖真机上的 0.6.5-dev / 20。复用 user 0、已保存的 Freeme 和现有 `com.naozho.clock/.display.ClockDeviceAdmin`。本轮从开机恢复独立锁定，HOME 接管继续作为单独的实验入口。

## 开机过程

- 据 DSH 对照，时钟和最小 HOME 包均只在限定包名时出现，Shell 与应用 UID 一致，清除 Freeme 持久偏好前后无变化。原厂额外过滤的原因尚未定论。独立路径使用显式 MainActivity。
- 原版的开机接收器遇到独立锁定会提前返回。新版收到 LOCKED_BOOT_COMPLETED 时只记录阶段。部署、暂停和日常模式沿用原应用的凭据加密存储。系统开放该用户存储、发送 BOOT_COMPLETED 后，才读取配置。设置了安全屏幕锁的手机可能需要首次正常解锁。实际需要与否由现场记录。[Direct Boot](https://developer.android.com/privacy-and-security/direct-boot)
- 独立专机仍启用时，新开机编号使日常模式回到时钟。应用核对自己的 Device Owner 身份、唯一允许包与功能标志，必要时按现有部署恢复名单及 flags。存在其他允许包时报告冲突。启动请求与维护暂停、开发退出串行，同一开机编号最多记录并发出一次启动请求。更新 APK 本身不会代替开机启动独立时钟。Android 16 AOSP 后台 Activity 启动判断中有针对 Device Owner UID 的例外。[Android 后台启动规则](https://developer.android.com/guide/components/activities/background-starts) · [Android 16 实现](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/wm/BackgroundActivityStartController.java)
- 时钟收到开机 Intent 后重读开机编号、模式和策略。过期请求退出。实际 Lock Task 沿用已验证的前台路径，等待时钟处于 resumed、获得窗口焦点、系统锁屏允许，再由 Activity 请求锁定并读取实际结果。屏幕不会被开机处理强制点亮。CPDAY10 预期独立模式、LOCKED、80、名单仅时钟。80 包含 GLOBAL_ACTIONS 和 BLOCK_ACTIVITY_START_IN_TASK。
- 日常确认开发退出后，本次开机保持 Freeme；点时钟图标可恢复独立锁定。维护页「暂停专机并恢复原桌面」会持久关闭自动恢复。独立暂停和独立开机都无需写 HOME 策略。重新启用入口为「锁定当前时钟（开机自动恢复）」。

## DSH 实机步骤

**更新。** 从已验收的 0.6.5 正常确认「开发退出」，看到 Freeme 后，在 Windows PowerShell 执行以下命令。使用已配对的 CPDAY10；多设备时给 adb 指定 `-s 序列号`。

```powershell
Get-FileHash .\naozho-0.6.7-dev-debug.apk -Algorithm SHA256
adb devices -l
adb install -r .\naozho-0.6.7-dev-debug.apk
adb shell dumpsys package com.naozho.clock | Select-String 'versionName=|versionCode='
adb shell dpm list-owners
adb shell cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.HOME
```

确认 Owner 仍是时钟、有效 HOME 为 Freeme。如果此前的独立专机仍启用，可直接从 Freeme 开始第一次重启；如果对照实验中曾暂停，从「时钟管理员恢复」点「锁定当前时钟（开机自动恢复）」启用，并记录初始状态。两个起点都需要覆盖。

1. **从启用的专机重启。** 手机电源菜单正常重启，从确认重启时开始计时。保持无线 ADB 仅作观测。用第二台设备录像，记录启动动画、锁屏、首次显示 Freeme、时钟出现、首次触摸有响应的时间。需要凭据时先记录画面和时间，再正常解锁；把解锁前后结果分开。如果始终停在 Freeme，保留现场后再作人工恢复。手动点图标或显式拉起的结果不能计为自动启动通过。
2. **验证可操作。** 用下方只读命令确认有效 HOME 为 Freeme，实际前台及窗口焦点在时钟。查 LOCKED、independent=true、flags=80、允许名单仅时钟。手指连续上划两次、五次，每次点开开发退出并取消，核对可触摸和保持 LOCKED。用电源键息屏再亮，确认时钟可触摸。
3. **验证同次开机与下次开机。** 在时钟确认开发退出，验证 NONE 和 Freeme，在桌面停留并实际操作；点真正的时钟图标验证重新 LOCKED + 80。再确认开发退出，保留独立配置，从 Freeme 正常重启。若第 1 步已经从 Freeme 启动，这次改由 LOCKED 的时钟重启。两个已启用起点最终都应自动进入可操作的时钟。
4. **验证维护暂停。** 正常退出，在独立恢复图标点「暂停专机并恢复原桌面」，重启。预期 Freeme、NONE、Owner 保留，时钟不会自动启动。验收结束如需恢复独立专机，从维护入口重新启用，核对实际状态。全程保留系统电源菜单和原桌面。

每次重启记录一行。启动动画或黑屏期间无法无线采样时，用外部录像补足时间线。

| 起点 | 重启编号 | 首见 Freeme / 时钟 / 可触摸耗时 | 是否手动首次解锁 | 实际 HOME / 窗口焦点 | Lock Task / flags / 名单 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| 独立锁定 | | | | | | |
| 已开发退出、专机仍启用 | | | | | | |
| 维护已暂停 | | | | | | |

## 只读取证

在每个节点另存一份，日志文件名按起点区分。无线 ADB 重新连上前不要为验收手动打开时钟。

```powershell
adb shell settings get global boot_count
adb shell getprop sys.boot_completed
adb shell am get-started-user-state 0
adb shell cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState|topResumedActivity|mResumedActivity'
adb shell dumpsys window windows | Select-String 'mCurrentFocus|mFocusedApp'
adb shell dumpsys device_policy > .\boot-policy.txt
adb logcat -d -b main -b system -v monotonic -s NaozhoMode:I ActivityTaskManager:I > .\boot-clock.log
```

按同一 boot_count 对照 `waitingForUnlockedBoot`、`Independent boot count`、`launch requested`、`Independent boot Activity ... accepted=true`、`Clock window focused=true`、`Lock Task after start`。`launch requested` 在 startActivity 返回后写出，Activity 的 accepted 日志可能先出现。若暂停，预期 `automatic launch disabled`。若启动请求已发出但没有 Activity 日志，保留 ActivityTaskManager 对同一时段的后台启动裁决；若 Activity 已进入但未锁定，另存 `adb shell dumpsys window policy` 与锁屏、焦点状态。记录人的第一下点击发生在什么时间。需要人工首次解锁才成功时，结果写为“解锁后自动恢复”，单列无人干预项。

## 构建与回归

- APK 为 11,451,240 字节，SHA-256 为 `a2c243773bd03685ce7ab1a85123fa36b37638cbcae391a56b04fa47be28606e`。apksigner 验证签名，证书 SHA-256 为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`，与 0.6.5 一致。ZIP 完整性和对齐检查通过。最终 Manifest 与 0.6.6 的差异为版本和 ModeBootReceiver 的开机声明。
- 源码提交 `49a28d0`。development 的 121 项与 debug 的 106 项主机测试通过，两组有共享用例。覆盖开机编号、独立模式、策略恢复、HOME 缺失、重复广播、冲突名单、缺 Owner、Direct Boot 等待、退出后的过期启动与暂停后重新启用。Lint 两个变体均为零错误，分别有 10、8 项警告。
- 隔离的 AOSP API 28 软件模拟器使用 Launcher3 作默认桌面。从实际 0.6.5 APK 的已启用独立配置、安卓模式、NONE 开始，覆盖安装 0.6.7。正常重启，boot_count 从 1 到 2，用户存储自行解锁。已记录独立开机请求及 MainActivity 接受同一编号，约为虚拟设备启动后 295 秒，有效 HOME 仍是 Launcher3。该模拟器在解锁前还曾由系统作普通 HOME 解析拉起简版时钟，日志中可与解锁后的显式请求区分。
- 第一次无人干预采样中，系统出现 SystemUI 无响应及一次时钟 TIME_TICK 广播超时，弹窗占据焦点。MainActivity 已恢复到前台，Lock Task 读数为 NONE。此轮验证了显式请求送达，未通过无人干预锁定与触摸验收。模拟器无硬件加速，该耗时与现象不能作为 CPDAY10 的设备结论。
- 无人干预采样结束后，在模拟器的两个无响应弹窗点「等待」。未再次启动时钟，焦点回到 MainActivity，系统随即读回 LOCKED、independent=true、唯一允许包 com.naozho.clock。API 28 的实际 flags 为 16，bit 64 从 API 30 起可用。这个诊断验证了焦点到达后的锁定路径，不能替代 CPDAY10 上的无人干预启动、flags=80 和手指操作。
- 另经生产暂停逻辑持久关闭独立专机，再次正常重启，boot_count 从 2 到 3。开机接收器记录 automatic launch disabled managed=false。系统有效 HOME 和 resumed Activity 均为 Launcher3，Lock Task 为 NONE，Owner 保留。此次只读采样仍观察到 SystemUI 无响应窗口，未给桌面触摸体验判定通过。
