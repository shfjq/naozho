# CPDAY10 · KernelSU 开机任务实验与 DSH 验收手册

适用环境为原厂 Android 16 / user 0、已有 KernelSU v3.3.1、SELinux Enforcing、原有 Device Owner 和 Freeme。模块 ID 为 `naozho_boot`，版本 1.0.0。应用更新为 com.naozho.clock 0.6.9-dev（24）。源码提交 `cea3b28`。第一阶段可以继续用 0.6.8-dev（23）。

## 交付物

| 文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| naozho-ksu-boot-1.0.0.zip | 3,566 | ad7973a9deb07d0084ec5b135c0378f24e8b94e1672e1f94262a9a0250cbc9cb |
| naozho-0.6.9-dev-debug.apk | 11,467,756 | 2df55e6aa4159ed33608c514dcd39842ad8381ad4afa586b9db4f210481c5aae |

安装 ZIP 内即为完整模块源码，包含 module.prop、skip_mount、customize.sh、service.sh、boot-completed.sh、action.sh、status.sh。可用普通解压软件审阅。APK 通过 apksigner v2 和对齐检查，签名证书 SHA-256 与 0.6.8-dev 相同，为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。

## 两个开机阶段怎样运行

已核对 KernelSU 官方 v3.3.1 源码与随附文档。ksud 分别以非阻塞方式运行 service 和 boot-completed 阶段，脚本由 KernelSU 自带的 BusyBox sh 执行。service.sh 只记录进入时刻与当时能读到的状态，早期 boot_count 或用户状态可能尚不可用。boot-completed.sh 再记录系统属性、boot_count、当前用户和 user 0 存储状态。两个阶段各有自己的日志。[v3.3.1 模块文档](https://github.com/tiann/KernelSU/blob/v3.3.1/website/docs/zh_CN/guide/module.md) · [阶段执行源码](https://github.com/tiann/KernelSU/blob/v3.3.1/userspace/ksud/src/init_event.rs)

模块默认为观察。KernelSU 的「操作 / Action」在观察与请求之间切换，启用请求从下次内核开机生效。请求阶段只在 sys.boot_completed=1、boot_count 可读、前台用户为 0、user 0 为 RUNNING_UNLOCKED 时发送一次固定的 Android 信号。初次采样未就绪时，最多观察约两分钟，再计入最后一次系统查询用时。超时结束本轮。开机编号传给应用，模块另外用内核 boot_id 防止重复回调。墙上时钟采用 UTC，uptime_s 为设备开机后的秒数。

开发 APK 新增一个受签名权限保护的显式接收器。0.6.8 的桌面图标代表用户主动进入时钟，直接打开它会丢失“维护暂停”的语义。新接收器不接受命令、路径、包名或任意目标，时钟应用也无需取得 su 权限。应用复核开机编号、用户存储、安全锁屏、独立模式与 Owner，复用原有恢复逻辑，由应用自身请求 MainActivity。广播、Job 和模块共享应用的开机记录。应用收到请求但系统不允许显示时，模块只采样并记录，发送到此结束。

## 第一阶段 · 自然执行

1. 通过已验证的开发退出进入 Freeme。在 KernelSU 管理器确认当前版本和既有救援方式可用，记录原有模块与 Owner。维护人员可核对文件。

   ```powershell
   Get-FileHash .\naozho-ksu-boot-1.0.0.zip -Algorithm SHA256
   Get-FileHash .\naozho-0.6.9-dev-debug.apk -Algorithm SHA256
   ```
2. 在 KernelSU 管理器的「模块」页面从本地 ZIP 安装，保持默认观察。通过电源菜单执行正常重启。首轮不点模块「操作」，不手动运行脚本，不通过 ADB 拉起时钟或执行 Job。
3. 重启后用已有授权的维护连接读取记录。以下三条读取模块私有日志，需要 DSH 电脑上既有且经用户授权的维护权限。多设备时先选择 CPDAY10。

   ```powershell
   adb shell settings get global boot_count
   adb shell "su -c 'cat /data/adb/modules/naozho_boot/state/service.log'"
   adb shell "su -c 'cat /data/adb/modules/naozho_boot/state/boot.log'"
   ```

   第一阶段通过条件为本次开机的 service、boot-completed 时间戳及 `phase=observe`，并与设备 boot_count 对上。若开机早期编号为 unknown，以后一个阶段为准。只看到 service 时，记录 KernelSU 的阶段日志、模块是否启用及正常重启方式。仅观察时如有时钟出现，查明广播、Job 或其他来源。

## 第二阶段 · 请求一次并验收

1. 经正常开发退出进入 Freeme。覆盖安装配套 APK，保留应用数据和原 Owner。用现有维护页核实「独立锁定」已启用。若仅为进入 Freeme 而正常退出，独立部署仍应保留。若曾维护暂停，按既有入口重新启用，再正常开发退出。

   ```powershell
   adb install -r .\naozho-0.6.9-dev-debug.apk
   adb shell dumpsys package com.naozho.clock | Select-String 'versionCode=|versionName='
   adb shell dpm list-owners
   adb shell getenforce
   ```
2. 在 KernelSU 管理器模块页对本模块点一次「操作 / Action」，确认输出 **REQUEST on subsequent boots**。正常重启。记录是否先显示 Freeme、是否需要首次人工解锁，以及从按下重启到时钟可触摸的耗时。一次需要人工解锁的样本应登记为“解锁后恢复”。观察期间保持自然启动。
3. 核对模块日志、应用日志与实际窗口。同一 boot 的证据链应为 `phase=request submitting`、结果 201、应用 `source=kernelsu`、Activity 的 `accepted=true`、实际前台时钟、有焦点、独立 LOCKED + flags=80，允许名单仅时钟。模块在 201 后约 3 秒做一次只读窗口与锁定采样。窗口较慢时单次读数可以为 unknown 或尚未就绪，记录实际现场结果。

   ```powershell
   adb shell "su -c 'cat /data/adb/modules/naozho_boot/state/boot.log'"
   adb logcat -d -v monotonic -s NaozhoKsu NaozhoModuleBoot NaozhoMode ActivityTaskManager Atlas | Select-String 'before-request|result=|Independent boot|Clock window focused|Lock Task after start|com.naozho.clock'
   adb shell dumpsys activity activities | Select-String 'mLockTaskModeState|topResumedActivity|mResumedActivity'
   adb shell dumpsys window windows | Select-String 'mCurrentFocus|mFocusedApp'
   adb shell dumpsys device_policy | Select-String 'LockTask|mFlags' -Context 1,4
   adb shell cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.HOME
   ```
4. 连续上划 2 次和 5 次后检查真实触摸，实体电源键熄屏再亮后再检查。开发退出选取消时应保持 LOCKED，确认后应为 NONE + Freeme。留在 Freeme 检查同次开机可正常使用。用户点时钟图标应重新锁定。
5. 单独验证维护暂停。保持模块在 REQUEST 模式，正常退出，使用时钟维护页「暂停专机并恢复原桌面」。正常重启，预期为 204、NONE + Freeme、Owner 保留。同次开机有其他来源先提交请求时，分别记录来源，不计为模块独立恢复通过。测试后按需要用原维护入口恢复独立锁定。
6. 建议至少 3 次正常重启、1 次完整关机再开机。分开记录脚本入场、信号应答、实际锁定、手指可操作四个时刻。系统健康回归包括 Freeme、普通应用、电源菜单、Wi-Fi、蓝牙和 vivo 健康的原有运行条件。

### 如何判读失败

| 证据 | 含义及处理 |
| --- | --- |
| stop=readiness_timeout | 用户、存储、系统服务或 boot_count 在窗口内尚未就绪。保存最后状态和正常首次解锁时间。 |
| result=0 或没有应用应答 | 尚未证明收到信号。核对 APK 是否为 24、组件、平台投递、签名权限及 OEM 日志。不要将这一结果直接归因于 Atlas。 |
| 204 | 应用主动跳过。independent_not_armed 为未启用或已暂停。desktop_mode 为同次开机安卓模式。no_new_request 包含已有请求、已锁定或条件变化。 |
| 403 / 409 / 423 / 503 | 分别核对 Owner、开机编号、用户或安全锁屏及应用/系统错误。模块日志保存 Android 返回值，应用把捕获到的异常写入日志。 |
| 201，时钟未出现或失焦 | 仅确认应用发出 Activity 请求。模块保留单次只读焦点和锁定状态，能匹配到当前请求后的系统拒绝文字时记录 system_reason。not_observed 表示未采到具体原因。保留日志，不自动再次请求。 |
| 超时或进程中断 | 调用方超时后也可能出现迟到的投递。对照同一 boot 的应用日志和窗口，禁止把超时当作再次发送的理由。 |

## 停用、卸载与故障恢复

- 暂停开机实验可点模块「操作」，看到 **OBSERVE**。要停用所有模块脚本，在 KernelSU 管理器中关闭 **CPDAY10 Clock Boot Experiment**，正常重启。要解除当前时钟锁定，仍用时钟的开发退出或维护暂停。
- 卸载前先导出需要保留的 service.log、boot.log 和 previous-boot.log。KernelSU 模块页选择该模块的卸载并正常重启，确认模块已消失。模块阶段设置和日志只在其自身目录，移除后随目录清理。时钟 APK、Owner 及原有独立锁定配置继续由原维护入口管理，无需降级 APK。
- 若窗口异常但开发退出可用，先退出到 Freeme，维持可用状态并禁用模块。若界面不可用而已有维护 ADB 可连接，可依 KernelSU 文档给**本模块**设置标准 disable 标记，再正常重启。该操作会修改本模块的启用状态。

  ```powershell
  adb shell "su -c 'touch /data/adb/modules/naozho_boot/disable'"
  ```
- 若无法正常进入管理界面或连接 ADB，按已核实适用于本机 KernelSU 集成方式的官方安全模式恢复，进入管理器卸载该模块。官方安全模式可能同时禁用其他模块，回来后按原记录核对。CPDAY10 的物理按键救援尚需 DSH 确认。[KernelSU v3.3.1 官方故障恢复说明](https://github.com/tiann/KernelSU/blob/v3.3.1/website/docs/guide/rescue-from-bootloop.md)

## 验证范围

主机使用 v3.3.1 官方 x86_64 BusyBox 的 standalone ash 运行 12 项脚本用例，同一组也在主机 sh 通过。Android 命令与开机时间使用替身，覆盖真实脚本的默认观察、下一次开机启用、并发回调只提交一次、取消、存储锁定、用户切换、等待期间禁用、拒绝后不重试、无应答及焦点异常证据。Gradle development 127 项、debug 106 项通过，两组有共享用例。development Lint 零错误、10 项警告。APK 与 0.6.8 的签名证书比对通过。CPDAY10 上的 KernelSU 自然调度、Android 对显式请求的实际处理、锁定耗时、真实触摸以及卸载恢复留给 DSH 实测。
