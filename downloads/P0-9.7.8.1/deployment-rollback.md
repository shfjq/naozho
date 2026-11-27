# WakeObserver 0.1.0 · 最小权限部署及撤回手册（待批准）

本轮只交付手册。下面的设备命令供批准之后由 DSH 在受信任电脑执行。所有变更只针对 `com.naozho.wakeprobe`。已发布时钟的包名是 `com.naozho.clock`，任何安装、停止、授权和清理命令都不应以它为目标。

## 1. 离线核对

使用原交付 APK [固定版本下载](https://raw.githubusercontent.com/shfjq/naozho/add3fe1d7309a1632cede19b4b821d8c4bd080ce/downloads/P0-9.7.8/cpday10-wake-observer-0.1.0.apk)。本版大小为 **33,195 字节**，APK SHA-256 为 `68712d6a3e68d1b7306984b92d6ed89dffdc0bf891d5e32cd6db997ae7a095e5`。在 Windows 电脑上执行：

~~~powershell
(Get-Item .\cpday10-wake-observer-0.1.0.apk).Length
Get-FileHash .\cpday10-wake-observer-0.1.0.apk -Algorithm SHA256
apksigner verify --verbose --print-certs .\cpday10-wake-observer-0.1.0.apk
~~~

整套复核时，保持下载分支的目录层级：这次报告和校验清单在 P0-9.7.8.1/，原 APK 和源码包在相邻的 P0-9.7.8/。在 P0-9.7.8.1/ 执行 `sha256sum -c SHA256SUMS.txt` 可逐项核对。

确认 v3 验签成功、仅 1 个签名者、签名证书 SHA-256 为 `2618dfdd7a610abcad93e2d99164d7e1430ce468a9360186e3652a72e9a86c99`。哈希与证书指纹是两个不同的核验项目。若 Android build-tools 未加入 PATH，可用已安装的 apksigner.bat 完整路径。

## 2. 获批后的只读前置检查

确认目标是 CPDAY10、用户 0、API 36，核对时钟版本、原 Owner、生产模块停用等已批准的原基线。以下命令以仅连接目标设备为例；若设备多于一台，使用 `adb -s 序列号` 明确选择。检查当前目标用户与诊断包是否已存在：

~~~bat
adb devices -l
adb shell am get-current-user
adb shell pm list packages --user 0 com.naozho.wakeprobe
~~~

若不是预期用户，或已存在同名包／既有数据，先报告状态。不要覆盖或卸载来消除差异。需要核对 Shell 实际权限时可在本地阅读 `adb shell dumpsys package com.android.shell`，查 GRANT_RUNTIME_PERMISSIONS 和 REVOKE_RUNTIME_PERMISSIONS 的有效授予记录；requested permissions 只表示申请过。

## 3. 第一档：仅安装及显示回调

~~~bat
adb install --user 0 cpday10-wake-observer-0.1.0.apk
adb shell pm path --user 0 com.naozho.wakeprobe
~~~

只安装此 APK，省略 `-g` 和 `-r`。从“唤醒观察器”图标打开，点“刷新状态”，应显示电源状态读取未授权。如果全新安装却显示 DUMP 已授权，先暂停并查来源。用户点击“开始观察”后按需允许 POST_NOTIFICATIONS，核对可见通知和停止入口；拒绝通知时本版应不开始。做获批的一个短暗→亮样本后正常停止，验证有显示状态行，电源快照为 `dump_permission_absent`，本次没有 FULL_WAKE。此档可只做安装、查看状态、卸载，不必授权 DUMP。

## 4. 第二档：单独批准后的限时 DUMP

该权限在系统层不限于 power 服务，需另行同意。先结束未授权会话，再在同一台已授权的电脑执行：

~~~bat
adb shell pm grant --user 0 com.naozho.wakeprobe android.permission.DUMP
adb shell dumpsys package com.naozho.wakeprobe
~~~

1. 记录命令结果。检查包管理器的有效授予状态，区分 install/runtime 等段中的 `granted=true` 与单纯的 requested 声明。再从图标打开“刷新状态”，由应用自己的 checkSelfPermission 确认“已授权”。
2. 开一个新会话，在已批准的一次自然息屏／唤醒后，核对 `callback_source=power_readback` 的记录确有 `power_status=ok`，并获得实际 wakefulness 与最近睡醒时间。若整周期也符合规则才可出现唯一 FULL_WAKE。**Shell 命令成功、UI 已授权、快照可用和周期确认是四个不同的检查点。**
3. 若出现 SecurityException、用户不对、权限固定、未获授或不允许调试，停在该步；若已授但快照失败，记录本次 error 分类、会话和阶段，仍按计划撤权。不要通过 Root、修改策略、赋予额外权限或反复执行 grant 来处理。回到只用公开 API 的观察，或按报告选 B。
4. 短样本完成即结束本次授权。后续 30 分钟或 8 小时应单独确认测试窗口、开始／结束电量、回收标准与撤权时间。

## 5. 停止、异常和数据处理

- **正常停止**：从持续通知点“停止观察”，或在诊断页点“停止观察”。核对通知消失、服务已注销。日志正常会有 SESSION_END。Android 可以缓存进程，仅看到 PID 不代表仍在监听。
- **异常退出**：PID 改变、缺 SESSION_END 或 previous_unclean_sessions 增加，不能单独确定崩溃原因。保留本地已写的诊断行，结束这次样本。该 Service 为 START_NOT_STICKY，没有开机 Receiver。只有获批继续时才手动开始新会话，从已亮屏重新建立基线，不能跨会话补算一个唤醒。若界面无响应且需立即中止，可执行 `adb shell am force-stop --user 0 com.naozho.wakeprobe`，再撤权；无需重启设备。
- **可选导出**：先停止服务，在 Windows **cmd.exe** 中运行以下命令，仅取应用已经筛选的记录。轮转文件存在时才取第二份。

  ~~~bat
  adb shell run-as com.naozho.wakeprobe ls -l files
  adb exec-out run-as com.naozho.wakeprobe cat files/wake.jsonl > wake.jsonl
  adb exec-out run-as com.naozho.wakeprobe cat files/wake.previous.jsonl > wake.previous.jsonl
  ~~~

  日志包含使用时刻、电量及唤醒模式，仅本地保留必要副本。原始 power 服务 dump 无需导出。

## 6. 撤权、清理与彻底回滚

1. 结束服务。若曾授予 DUMP，先显式撤销并验证：

   ~~~bat
   adb shell pm revoke --user 0 com.naozho.wakeprobe android.permission.DUMP
   adb shell dumpsys package com.naozho.wakeprobe
   ~~~

   重新打开诊断页只点“刷新状态”，应为“未授权”。撤权可能终止诊断包进程，属可恢复情况。如需验证负向样本，在已批准条件下重新手动开启，记录 `dump_permission_absent` 后停止。若撤权验证失败，停用诊断包并报告；可按获批的彻底卸载路径移除。
2. **保留 APK 但清除测试痕迹**：先确认是否需要保留本地结果；如需撤回已授通知权限，可执行 `adb shell pm revoke --user 0 com.naozho.wakeprobe android.permission.POST_NOTIFICATIONS`。确认 DUMP 已撤销后，若获准删除**该诊断包的全部本地数据**，执行 `adb shell pm clear --user 0 com.naozho.wakeprobe`。该步会删除本包日志、会话偏好等，无法靠重新授权恢复。只想停止观察时不需要清数据。
3. **完全撤回**：若如本手册所设，该 APK 仅为此次单用户诊断安装，在导出／放弃所需日志后执行：

   ~~~bat
   adb uninstall com.naozho.wakeprobe
   adb shell pm list packages --user 0 com.naozho.wakeprobe
   ~~~

   应卸载成功，用户 0 的精确包名不再出现。若发现其他用户也安装了同包，避免执行全用户卸载，先确认处置范围；仅需移除用户 0 时用 `adb shell pm uninstall --user 0 com.naozho.wakeprobe` 并核对。卸载时不加保留数据的 `-k`。电脑端导出副本不随设备卸载删除，保留期结束后仅清理本次导出的文件。
4. 核对原时钟、Owner、Freeme、300 ms、模块停用状态与测试前一致。至此观察器的订阅、权限和设备上的诊断数据均有对应撤回路径。

设备状态和授权前后结果由 DSH 在批准后独立记录。本轮手册不代表已执行部署。
