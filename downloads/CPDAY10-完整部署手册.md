# CPDAY10 · 路线 A 专机部署手册

本文件供 DSH 审查 0.5.5 交付物。取得 APK 和完整手册、完成核对并获得设备侧实施批准后，再操作手机。

[部署 APK](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/naozho-0.5.5-device-owner.apk) · [首次设置二维码模板](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/CPDAY10-%E9%A6%96%E6%AC%A1%E8%AE%BE%E7%BD%AE%E4%BA%8C%E7%BB%B4%E7%A0%81%E6%A8%A1%E6%9D%BF.json) · [独立真机验收清单](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/CPDAY10-%E7%9C%9F%E6%9C%BA%E9%AA%8C%E6%94%B6%E6%B8%85%E5%8D%95.md)

部署基线为 0.5.5（10），应用 `com.naozho.clock`，Device Admin 组件 `com.naozho.clock/.display.ClockDeviceAdmin`。部署 APK 使用现有项目签名，`debuggable=false`。DSH 已确认目标设备为 CPDAY10、Android 16 / API 36，原桌面为 `com.droiclaw.launcher3/com.freeme.launcher.FreemeLauncher`。此前快照只有普通 Device Admin、允许名单为空、`NONE`。以下涉及设备变更的步骤由 DSH 在获得实施批准后操作。

APK 文件 SHA-256 为 `0ff02b37c9b417022c1dc8bf65219c7eea149ca4fcd1fa2fff76779233e8798a`。供二维码向导使用的签名证书 SHA-256 已转换并写入模板。**二维码下载地址待配置。** JSON 的 `pending-configuration.example.invalid` 是保留占位地址，无法下载。待 DSH 确认部署地址，并从首次设置使用的实际网络验证下载及哈希后，再替换字段并生成二维码。本次交付仅包含 JSON 模板。

部署构建、签名、APK 完整性和对齐校验通过。87 项单元与 Robolectric 回归通过，覆盖受保护的入管回调、仅全托管模式、Owner 和普通管理员区分、允许名单、受管 Home 往返、同次开机模式保持、重启后恢复、原桌面丢失时的暂停，以及既有响铃按键映射。Lint 为 0 错误、3 条既有警告。

Android 16 x86_64 软件模拟器通过 ADB 读到了 API 36、用户 0、零账户和空 Owner。首次开机与系统服务重试均未完成。日志显示 `system_server` 在启动系统 Home 时被 Watchdog 重启，模拟器预检在 APK 安装和 Owner 登记前中止。首次设置路径已核对 Android 16 契约、二维码模板和包内回调，设备端扫码及 Shell 登记均仍需在 CPDAY10 验收。

## 1. 安装前核对

1. 保存 `naozho-0.5.5-device-owner.apk`，核对本手册公布的 SHA-256。Windows 用 `Get-FileHash .\naozho-0.5.5-device-owner.apk -Algorithm SHA256`，对照交付值。APK 外部下载和二维码下载必须指向同一份已签名文件。
2. 准备 Windows Google Platform-Tools、数据线及设备需要的 USB 驱动。此前实机无线 ADB 仅证明本次已配对的状态。恢复出厂会失去调试授权和无线配对，届时重新开启调试并在手机上批准 Windows 电脑。先验证 USB 有效，之后再决定是否启用无线配对。 [Google Platform-Tools](https://developer.android.com/tools/releases/platform-tools)
3. 记录原厂 Build Fingerprint、屏幕锁定选项、Freeme 组件和已启用的设备管理身份。即使当前没有数据要迁移，也要确认以前绑定的账号归属与恢复出厂保护所需的原账号认证。通过官方回收／重置路径处理已有管理和账号，先确认设备可以进入已知的原厂恢复入口。
4. 选择下面的一条入管路径。实际结果统一以 `dpm list-owners` 中 **Device Owner** 指向本应用为准。应用界面出现设备管理员、绑定权限声明或 `PINNED` 时继续按实际状态诊断。

## 2. 路径一 · 在首次设置阶段由系统完成入管

适用于 CPDAY10 首次设置向导实际支持 Android Enterprise 全托管二维码的固件。此路径应在欢迎阶段进入企业设置，由向导负责下载安装 APK，入管前无需 ADB。

1. 使用经批准的 HTTPS 地址托管交付 APK，确认设备网络可直接下载，页面无需网页登录或交互。复制 `CPDAY10-首次设置二维码模板.json` 并替换下载地址。签名校验值是签名证书 SHA-256 的 URL-safe Base64，文件 SHA-256 单独核对。保留 `PROVISIONING_LEAVE_ALL_SYSTEM_APPS_ENABLED=true`，避免向导按全托管默认列表停用 Freeme 或其他 OEM 系统应用。用离线二维码工具把确认过的 JSON 转成二维码。 [Google Test DPC 二维码流程](https://github.com/googlesamples/android-testdpc#qr-code-provisioning-device-owner-n-only)
2. 如需且已批准，恢复出厂。开机停在初始欢迎页。AOSP/Google 常见入口是同一处轻点六次，OEM 入口可能不同。识别到企业设置界面后，按向导连网、扫码并接受全托管。确认 APK 由系统落盘后再完成向导。若只出现工作资料、扫码入口缺失、管理包下载或权限校验失败，记录页面及错误，改用路径二的独立条件检查。
3. Android 12 及以上的流程调用 `GET_PROVISIONING_MODE` 和 `ADMIN_POLICY_COMPLIANCE`。本 APK 仅在系统允许的模式包含全托管时返回该模式。合规回调验证本应用已是活动 Device Owner 才返回成功。两个入口都由 `BIND_DEVICE_ADMIN` 保护，登记完成后保持可操作，等待管理员另外启用专机。 [Android 16 入管回调契约](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/core/java/android/app/admin/DevicePolicyManager.java#L554)
4. 向导结束后，如固件允许，在设置开启开发者选项和 USB 调试，重新批准 Windows 电脑。按第 4 节验证账户与 Owner 状态，打开「管理员恢复」核对。同一次初始化中成功登记的 Owner 应保留，避免重复执行 `dpm set-device-owner`。如果固件限制 USB 调试，先记录系统界面和应用里的 Owner 状态，并在正式启用专机前解决完整验收所需的只读诊断能力。

## 3. 路径二 · ADB Shell 在无账户、单用户条件下登记

适用于 OEM 向导没有全托管入口、或采用单台研发验证流程的情况。**APK 必须先安装到目标用户，然后由 Shell 登记本应用为 Device Owner。** 已完成设置向导的 AOSP 设备仍可能符合 Shell 路径，但要通过检查，而且 CPDAY10 固件可以施加额外限制。 [Android 16 Device Owner 预检实现](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/services/devicepolicy/java/com/android/server/devicepolicy/DevicePolicyManagerService.java#L17187)

1. 从干净状态只完成到能进系统设置并启用 USB 调试的程度。跳过 Google、酷派或其他账户、云恢复、工作资料及额外用户。需要联网完成向导时，联网与登录账号分开处理。已有其他所有者、账号、第二用户或工作资料时先停止，核对原厂支持的解除方案。确需清除时，使用已批准的正常恢复出厂流程。
2. USB 调试开启后，将 CPDAY10 接上 Windows，解锁屏幕并在手机上确认当前电脑的调试授权。以下示例假定只有一台设备。若存在多台连接，将每条 `adb` 命令换成 `adb -s <CPDAY10序列号>`。`unauthorized`、`offline` 或空列表需处理连接，设备可用后再继续。USB 通道确认后可作为无线配对失效时的恢复通道。

```powershell
adb devices -l
adb shell getprop ro.product.model
adb shell getprop ro.build.version.sdk
adb shell am get-current-user
adb shell pm list users
adb shell dumpsys account | Select-String 'Accounts:'
adb shell dpm list-owners
adb shell pm list features | Select-String 'device_admin|managed_users'
adb shell settings get global device_provisioned
adb shell settings --user 0 get secure user_setup_complete
```

3. 确认 `CPDAY10`、API 36、当前前台用户为 0、只有预期的系统用户、账户确认为零，且不存在 Device Owner/Profile Owner。`Accounts:` 字段空缺时查阅设备设置或原始账户服务输出确认。设备标志仅用于记录。保持授权会话，安装后核对版本确为 0.5.5（10），再登记 Owner。

```powershell
adb install -r .\naozho-0.5.5-device-owner.apk
adb shell dumpsys package com.naozho.clock | Select-String 'versionName|versionCode'
adb shell dpm set-device-owner --user 0 com.naozho.clock/.display.ClockDeviceAdmin
adb shell dpm list-owners
```

4. Shell 返回 `Success` 后仍须核对实际 Owners 列表。如果提示账户、额外用户、已配置、固件不支持或组件无效，保留原文与前面的读数。根据报错处理真实前提或切换路径。保留 `device_provisioned`、`user_setup_complete` 等系统原值。系统设置触发的普通 Device Admin 激活不会完成此步骤。 [Google Test DPC ADB 路径](https://github.com/googlesamples/android-testdpc#adb-command)

## 4. 核对 Owner 并初始化专机

```powershell
adb shell dpm list-owners
adb shell dumpsys device_policy | Select-String 'Device Owner|Profile Owner|ClockDeviceAdmin|lockTask' -Context 0,2
adb shell cmd package query-activities --user 0 --brief -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell cmd package resolve-activity --user 0 --brief -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell dumpsys activity activities | Select-String 'LockTaskModeState|mResumedActivity|topResumedActivity'
```

1. 确认 `DeviceOwner` 指向用户 0 的本应用组件，且 Freeme 可用、时钟包存在。登记 Owner 后 Lock Task 应仍为 `NONE`。普通 Device Admin 只支持相关锁屏能力。
2. 在进入专机前核对精确闹铃、通知、全屏提醒、勿扰访问。先用测试闹铃确认能响。暂不调整 vivo 健康的权限与后台配置，记录原始状态供对照。
3. 从 Freeme 打开「小方块时钟 · 管理员恢复」。先用 Android 屏幕凭据验证，设置应用 PIN 和离线一次性恢复码。在认证后的「原生桌面」选择并保存 Freeme。首次没有系统屏幕凭据时，可先在系统设置添加临时 PIN。完成应用配置后，用原系统 PIN 确认并把屏幕锁定方式设为「无」。演练用一次性恢复码重设应用 PIN，保管换发的码。系统设置缺少「无」时，经管理员认证可试「关闭非安全系统锁屏」。只有无 Android 凭据且 `NONE` 时按该路径测试，操作后以实际电源键表现为准。
4. 在已认证的「管理员恢复」选择「启用专机并进入时钟」。如果上一步退出了该页面，此时用恢复码重新授权并保存换发的码，再启用。应用仅在现有 Lock Task 允许名单为空或只含本包时启用专机。系统锁定功能保留 Keyguard 和电源长按菜单，限制 Home、最近任务和通知面板，并在 API 30 及以上限制在锁定任务中打开其他未获准应用。应用核对受管默认 Home 后由前台时钟请求 `startLockTask()`。
5. 确认有效 Home 为 `com.naozho.clock/.MainActivity`，允许名单只有 `com.naozho.clock`，状态是 `LOCKED`。若只显示 `PINNED`、`NONE`、OEM 桌面无法解析或策略冲突，记录实际值，在管理员恢复内处理再试。保持 USB 调试仅限 DSH 验收和维护所需范围。验收后的连接策略由设备所有者决定。

## 5. PIN 日常退出和恢复锁定

1. 左上角和右下角同时按住 5 秒后松开，按原有隐藏手势从左下向右上完成滑动。错误、取消或系统仍处于锁屏时保留时钟模式。
2. 正确 PIN 后，应用暂停自己的通知隔离规则，调用 `stopLockTask()`，确认 `NONE`，保存安卓模式并将受管默认 Home 恢复成原 Freeme。然后显式打开 Freeme。Device Owner 与时钟的允许名单保留。从其他应用按 Home 应由系统解析到 Freeme。
3. 在 Freeme 点击小方块时钟图标。应用把受管 Home 改回时钟，核对实际解析及策略后进入 `LOCKED`。同一次开机中的普通前后台切换、应用进程重建或 APK 覆盖更新应保留安卓模式。设备重启后，专机启用时默认回到时钟。失败时保留 `NONE` 或既有受管状态的实测读数，通过管理员恢复处理。系统规则由权限和实际状态共同决定。

已经在 0.5.4 启用过受管锁定的设备，可先用 PIN 退出，然后在管理入口暂停旧策略并重新启用专机，启用后才由新版管理两种模式的有效 Home。若操作者主动对应用执行了系统的「强行停止」，需重新打开时钟再验收恢复，普通进程退出和系统的强行停止分别记录。

## 6. 维护暂停与彻底恢复

**临时停用专机。** 认证进入「管理员恢复」，选择「暂停专机并恢复原桌面」。应用停用自动重锁，只从 Lock Task 名单中移除自己，尝试将有效 Home 恢复至保存的 Freeme。该入口可用于 Freeme 或 Lock Task 策略异常时的维护，支持从真正的 `LOCKED` 中按允许名单移除规则解锁。核对 `NONE`、Home 和 Owner。Device Owner 继续保留，需要时可恢复系统锁屏或重新启用专机。 [Android 16 Lock Task 允许名单实现](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/services/core/java/com/android/server/wm/LockTaskController.java#L772)

**彻底恢复到原厂非受管使用。** 本单机路线以经批准的原厂恢复出厂作为清除 Device Owner 和设备策略的正式恢复路径。先从 Freeme 进入原厂系统设置并走原厂重置流程。时钟持续崩溃或系统设置不可达时，使用事先核实的 CPDAY10 原厂 Recovery 入口及厂商恢复指引。重置会清除用户与应用数据并保留当前固件版本。首次启动可能要求之前关联的原账号认证。重置后按普通个人模式设置，核对 Freeme、账号和 Owner 列表，再安装所需普通应用。应用采用正常 Device Owner，未把已弃用的 `clearDeviceOwnerApp()` 或测试管理员移除命令纳入部署和恢复。 [Android 16 设备所有者 API](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/core/java/android/app/admin/DevicePolicyManager.java)

## 7. DSH 真机验收清单

| 场景 | 通过依据 |
| --- | --- |
| 入管 | 分别记录首次设置阶段的二维码实际支持情况，以及单用户、无账户的 ADB Shell 入管结果。二者需要独立的干净基线。正常安装 Owner 必须为本应用，未启用专机前为 `NONE`。 |
| 实体电源键 | 屏幕实际息屏。短按后直接出现可触控时钟，再按正常息屏。覆盖连续切换、空闲超时、夜间待机和开机后状态，分别记录 `mWakefulness`、Keyguard 和前台组件。 |
| 普通导航 | `LOCKED` 下覆盖上滑、侧滑、返回、Home、最近任务、通知面板及外部应用入口。原厂紧急和电源长按路径单独核对。 |
| PIN 及原桌面 | 错误、取消均保持锁定。正确后 `NONE`、有效 Home 是 Freeme、Device Owner 仍是本应用。使用 Freeme 的 Home 和最近任务，重新打开时钟后恢复 `LOCKED`。 |
| 重启、崩溃、升级 | 时钟模式及 Freeme 模式各测冷启动，已启用专机应回时钟。模拟时钟进程异常后由当前 Home 恢复。分别从两种模式验证同签名 APK 覆盖更新。系统 OTA 前后记录指纹、Owner、Home、Lock Task、闹铃登记和恢复。 |
| 实际响铃与实体音量键 | 在息屏、锁屏和 `LOCKED` 下确认响铃界面和实际声音。音量＋停止，音量－贪睡，长按和连按无重复，响铃期间系统音量面板不出现，平时保持正常按键。无网络和勿扰模式也要验证。 |
| vivo 健康 | 保留原厂应用及必要蓝牙、网络、定位和前台服务条件。对照息屏、冷启动和不同模式的后台结果。 |
| 恢复 | 演练一次性恢复码、维护暂停及恢复锁定。完整恢复出厂另在批准后的独立步骤执行和记录。 |

建议在关键场景保留 `dpm list-owners`、有效 HOME 解析、`dumpsys activity activities` 及 `logcat -d -s NaozhoMode NaozhoAlarm`。保存结果时遮盖设备串号、PIN、恢复码和账号。物理电源键、厂商向导、Freeme 手势和实际音量键结果以 DSH 的 CPDAY10 记录为准。
