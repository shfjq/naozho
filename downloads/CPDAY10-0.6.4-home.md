# CPDAY10 0.6.4-dev · 持久 HOME 策略和 DSH 验收

交付给 DSH 的版本为 com.naozho.clock，versionCode 19。使用现有 user 0、Device Owner 和已保存的 Freeme。第一次验收全程保持 Lock Task 为 NONE。使用开发恢复页的「开始退出预演（保持未锁定）」切换 HOME。

## 故障依据

DSH 在 CPDAY10 上读到了时钟管理员为 user 0 设置的持久 HOME，其值为 Freeme，系统也实际解析到 Freeme。0.6.3 的暂停逻辑主动把 Freeme 写为持久目标。再次切换时，旧代码按目标方向推测要清理的包，在第一次 DPM 调用返回后立即发出第二次调用。接收器单独记日志，没有按清除和设置阶段关联结果。现场快照只证明当时的策略和值，尚不能确定原厂 PackageManager 在成功清除后的行为。

Android 16 的 DevicePolicyManagerService 枚举**当前用户、调用管理员**的持久偏好键，按所选 Activity 的包名匹配并逐个删除。旧值为 Freeme 时传 com.droiclaw.launcher3，旧值为时钟时传 com.naozho.clock。此 API 的作用范围可包含同一包的多条过滤器。对于真正存在的键，AOSP 的清除结果为 RESULT_POLICY_CLEARED；没有匹配键时可能没有回调。普通 Owner 应用没有读取系统完整策略表的公共 API。[Android 16 服务实现](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/devicepolicy/java/com/android/server/devicepolicy/DevicePolicyManagerService.java) · [策略引擎](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/devicepolicy/java/com/android/server/devicepolicy/DevicePolicyEngine.java) · [PolicyUpdateReceiver](https://developer.android.com/reference/android/app/admin/PolicyUpdateReceiver)

## 安装和采集基线

将本文、同版 APK 和 Read-Cpday10HomePolicy.ps1 下载到电脑同一目录，在该目录打开 PowerShell。需要已连接的 Android platform-tools。多台设备时，下面所有 adb 命令加上 `-s 序列号`，脚本加 `-Serial 序列号`。

```powershell
adb devices -l
Get-FileHash .\naozho-0.6.4-dev-debug.apk -Algorithm SHA256
adb install -r .\naozho-0.6.4-dev-debug.apk
adb shell dpm list-owners
adb shell dumpsys device_policy > .\r4-0-policy.txt
adb shell dumpsys activity activities | Select-String 'LockTaskModeState'
adb shell cmd package resolve-activity --brief --user 0 --query-flags 66560 -a android.intent.action.MAIN -c android.intent.category.HOME
```

基线应为 user 0 的 com.naozho.clock/.display.ClockDeviceAdmin、NONE、Freeme。应用私有配置继续使用原桌面 com.droiclaw.launcher3/com.freeme.launcher.FreemeLauncher。

## 第一阶段 · 只切 HOME

1. 打开「时钟管理员恢复」，在已有 DroiClaw 选择下点「登记 DSH 已核对的 HOME 策略」→「准备读取编号」。在电脑上执行下面的命令。执行前可用文本编辑器检查脚本。

   ```powershell
   .\Read-Cpday10HomePolicy.ps1
   ```

   脚本等待广播队列排空，通过 ADB shell 读取同一设备的 Android 16 策略快照，检查管理员、用户、过滤器、两个目标包的其他规则和冲突。唯一写入是开发应用私有目录的一份诊断回执。读取编号、目标桌面和采样时间均需匹配。输出应显示完整 Freeme 组件，五分钟内点「导入设备策略清单」。厂商接口拒绝读取、发现其他规则或输出与基线不符时，在此停下并保存证据。
2. 点「仅清除已核对的 HOME 策略（NONE）」。保存一份新的 device_policy 输出。确认本管理员的 Freeme 持久 HOME 条目消失，记录有效 HOME 和 Lock Task。即便清除后系统自然选择 Freeme，此步也可以通过。若没有 CLEARED 或条目仍在，在此停下。
3. 点「开始退出预演（保持未锁定）」。等待维护页切入时钟。用下列只读命令记录读数。要求策略值为 MainActivity、两种解析均为 MainActivity、全局列表有 MainActivity、Lock Task 为 NONE。
4. 在时钟点「开发退出」并确认，等待 Freeme。再次采集读数。要求 Freeme 恢复为持久且有效的 HOME、NONE、Owner 保留。留在桌面观察。再从时钟图标返回，确认仍能在 NONE 下重现向时钟的切换。用恢复页「暂停专机并恢复原桌面」结束预演。
5. 只要回调超时、系统仍解析到另一组件或出现其他管理策略，就保留完整反馈和日志。回调未确认会使写入状态失效，后续重试需要新编号、广播排空和新清单。若需恢复，从独立恢复入口重新核对实际状态后选「暂停专机并恢复原桌面」。可直接按 Home 返回已经验证为有效的 Freeme。

```powershell
adb shell dumpsys device_policy > .\r4-step-policy.txt
adb shell cmd package resolve-activity --brief --user 0 --query-flags 66560 -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell cmd package resolve-activity --brief --user 0 --query-flags 65536 -a android.intent.action.MAIN -c android.intent.category.HOME -c android.intent.category.DEFAULT
adb shell cmd package query-activities --components --user 0 --query-flags 0 -a android.intent.action.MAIN -c android.intent.category.HOME
adb shell dumpsys activity activities | Select-String 'LockTaskModeState'
adb shell dpm list-owners
adb logcat -d -s NaozhoMode:I > .\r4-step-home.log
```

每个节点更换输出文件名，例如 r4-1-clear、r4-2-clock、r4-3-freeme。日志中的 homeOp 为应用操作编号，phaseTarget 表示该阶段所处理的组件。系统广播没有调用编号或目标组件。应用串行等待当前用户、精确 HOME 过滤器和当前阶段的 set-result，单独记录 changed 和未能归属的回调。写入后继续读取系统启动解析和设置界面解析；超时、异常、解析不符均会给出具体步骤。

## 第二阶段 · 完整专机

仅在第一次双向诊断全部通过后开始。在 NONE 点「启用专机并进入时钟」。核对清 Freeme → CLEARED → 写 MainActivity → SET → 确认有效 HOME → 核对名单并在前台进入 LOCKED。测试上滑 1、2、5 次、Home、返回、最近任务及启动其他应用。开发退出第一次选取消，核对仍为 LOCKED；再次选择确认，核对 NONE 后清时钟策略、写回 Freeme 并实际解析到 Freeme。确认 Freeme 可停留，点击时钟图标后再次成为时钟 HOME 并进入 LOCKED，Owner 全程保留。正常暂停会有意保留 Freeme 的持久偏好，下次启用从清除这条旧规则开始。

## 云端测试边界

Android 16 / API 36 的 720×720 官方模拟器启动后，已用 ADB shell 从设备策略服务读到 user 0 的真实空策略快照。另在同一虚拟设备的 Android 运行时使用构造的框架策略对象验证了三种输入：以 Freeme 为目标、以 MainActivity 为目标、以及同包多出一条非 HOME 偏好。前两项得到预期组件，第三项拒绝清除。

该环境没有 KVM。system_server 启动期间多次触发 Watchdog，安装返回 `Error: device is still booting.`。在这台一次性模拟器上延长 Watchdog 等待时间后仍未能完成整机往返；上述快照和过滤测试没有执行系统 HOME 切换。CPDAY10 的双向设置、清除后实际解析、完整 LOCKED 回归和开发退出均待 DSH 记录。

## 交付记录

- 软件提交为 `6e2c3be`。已构建 development 和 debug。发布的 development APK 为 11,598,717 字节，SHA-256 为 `f68f41f8804d9669fdee5b3bd7271f9e02fa923c487862bc5eac8ca46e9a7186`。
- apksigner 验证通过，签名证书 SHA-256 与上一版一致，为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。APK Analyzer 比对两版最终 Manifest，只有版本字段不同。
- development 的 114 项和 debug 的 106 项主机测试全部通过，两套有共享用例。新增用例覆盖双向切换、清除范围、回调类型与用户、超时和清单重放。两个变体的 Lint 均为零错误。开发版读取工具涉及 Android 16 的内部只读诊断接口，有 OEM 兼容性警告。
- Windows 脚本的 ADB 输出解析和回执往返另经 PowerShell 7 的模拟 ADB 输入测试。Windows 与 CPDAY10 的实际连接仍由 DSH 验证。
