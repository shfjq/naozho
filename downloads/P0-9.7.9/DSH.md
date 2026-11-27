# CPDAY10 全唤醒返回 · 部署、验收及回滚

适用于 CPDAY10 Android 16、KernelSU 3.3.1、用户 0。审批后执行。当前候选由 com.naozho.clock 0.6.14-dev（29）与 naozho_wake 1.0.0（1）配套。WakeProbe 保留已撤销 DUMP 的状态。naozho_boot 继续负责原有开机路径。

## 1　核对文件和安装前状态

从同一固定提交下载 APK、模块、回滚包和 SHA256SUMS.txt。Windows PowerShell 在下载目录执行下列命令，逐项与清单比对。以正常开发退出到 Freeme，保持屏幕亮起。

```powershell
Get-FileHash -Algorithm SHA256 .\*.apk,.\*.zip
adb shell dumpsys package com.naozho.clock | Select-String 'versionName=|versionCode=|userId=|appId='
adb shell dpm list-owners
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState='
adb shell getenforce
adb shell settings --user 0 get secure multi_press_timeout
adb shell su -c 'ls -l /data/adb/modules/naozho_power_daily/armed'
```

期望原时钟 28、现有业务数据和 UID、user 0 的 ClockDeviceAdmin、NONE、Freeme、Enforcing、300；最后一条应提示文件不存在。1.0.4 应维持停用。若基线不符，保存差异，等待审查。确认留有普通开发退出和 KernelSU 管理器操作入口。

## 2　覆盖安装和显式启用

1. 执行 `adb install -r naozho-0.6.14-dev-wake.apk`。复查上面的包、UID 和 Owner，确认版本 29。用正常图标进入时钟，验证 LOCKED、触摸及开发退出，回到 Freeme。
2. 在 KernelSU 管理器“模块”中选择 `naozho-wake-1.0.0.zip`，按管理器提示正常重启。安装初始关闭。时钟可能由既有开机模块打开；通过正常开发退出回到 Freeme。
3. 在新模块点一次 Action，返回 Freeme，屏幕保持亮起。模块注册后会先建立亮屏基线。可读取最近记录。若显示启动拒绝、固件/API 不匹配或部署提示缺失，停止测试并记录短原因。

```powershell
adb shell su -c 'tail -30 /data/adb/modules/naozho_wake/events'
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
```

正常首次启用可见 observer_ready、ENABLED、observer_registered 和 ON_BASELINE_CONFIRMED。Android 已暂停专机时可见 MAINTENANCE_PAUSED。模块按应用的专机设置订阅或撤销订阅；若另外使用一键停用，则需要再次在模块点 Action 才会观察。

## 3　逐项验收

每项从可操作的 Freeme 或已审查的普通页面开始，保持原厂设置。手动实施一次自然息屏和目标唤醒。记录屏幕实际变化、FULL_WAKE 周期、同一 request 的 RETURN 与 COMMIT 投递、最终 CLOCK_FOCUSED、焦点、策略数值、触摸；记录用户感知延时。一个周期最多一次正式 RETURN。投递证明与最终锁定回读是两个独立结果。

| 场景 | 现场判据 |
|---|---|
| 电源键、抬手、双击屏幕 | 每种受设备支持的方式分别验证。最终时钟能操作，连续上划后仍可触摸。 |
| 通知只触发 AOD；通知引起完整亮屏 | 前者保持环境显示，零正式请求。后者在安全前台、面板未遮挡的条件下可返回。 |
| 已配置的闹铃唤醒 | 检查完整唤醒事件；专用响铃/通话等受保护的交互应保留，避免覆盖停止闹铃操作。 |
| 屏幕持续亮着、开发退出、下一次唤醒 | 取消开发退出仍锁定，确认退出后 Freeme 可长期操作。只有新的真实暗屏及唤醒才能再返回。 |
| 已在时钟中、应用退到后台、普通进程回收 | 已锁定时不叠加第二次启动。对可复现的普通进程回收，下一次从安全前台唤醒应恢复时钟。Android 的强行停止有额外语义，不能代替普通进程回收。 |
| 专机维护暂停、重启、重新启用 | 暂停后没有正式请求，重启仍保持暂停。恢复独立锁定后正常开发退出，先建立新的亮屏基线，再测试下一周期。 |
| 紧急界面、通话、权限确认、输入法或未知遮挡 | 零前台抢占。查看入口即可，避免实际拨打紧急电话。 |
| 正常关机/开机、电源菜单及故障恢复 | 保留原操作。展示开机动画后第一屏的行为单独记录。 |

```powershell
adb shell su -c 'tail -40 /data/adb/modules/naozho_wake/events'
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState=|mLockTaskPackages'
adb shell dumpsys device_policy | Select-String 'lockTask|LockTask|mFlags=80'
adb shell dpm list-owners
```

每次成功必须看到当前时钟窗口与 Activity、本用户 LOCKED、实际 flags=80、允许名单仅 com.naozho.clock，并由用户触摸时钟上的一个可逆控件。没有显示相应字段时，使用时钟管理页的系统策略回读补证。设备不支持的唤醒来源标记未测。

## 4　停用、异常和恢复

- 一键停用：在该模块点第二次 Action，或运行下方第一条命令。它撤销 armed 和私有待交付收据。观察工作进程退出；短暂退避中的启动脚本也会在下一次检查时退出。已锁定的时钟仍可用“开发退出”正常回 Freeme。
- 若页面一直被拒绝，保存最近一次 REFUSED 短原因。三次未确认的正式提交会阻断本次开机的后续提交；排除原因后手动关闭、重新启用。不要通过替换焦点、删安全检查或重复强制广播进行验收。
- 移除模块时先停用，再在 KernelSU 选择卸载，按提示正常重启。若开机受影响，使用设备既有且已验证的 KernelSU 禁用模块/救援入口隔离 naozho_wake；本模块没有系统文件覆盖或分区写入。
- 保留新版 APK、只移除模块即可停用本功能。需要恢复旧代码时，可覆盖安装下方同签名、同 versionCode 29 的回滚 APK。恢复旧版后 1.0.4 的精确 APK 哈希检查会拒绝这个重打包文件。如果要恢复与 1.0.4 配套的原始字节，选择原版 0.6.13-dev/28，核实 SHA-256 后在支持调试包降级的系统执行最后一条；如系统拒绝降级，保留同版本号回滚包和停用的日常模块。无需卸载时钟、清数据或重设 Owner。
- 固定原版包 SHA-256 为 `8bcf50a524f58b6c8180d699f47a18fd096d94b7b12d737d1a60710d189597d4`。[原版 0.6.13-dev/28](https://raw.githubusercontent.com/shfjq/naozho/03f7bbdcbf3f77156659e6a0f65511548ebe168b/downloads/P0-9.5/naozho-0.6.13-dev-power-return.apk)

```powershell
adb shell su -c 'sh /data/adb/modules/naozho_wake/stop.sh'
adb shell pidof naozho_wake
# 选择一种 APK 恢复方式
adb install -r naozho-0.6.13-dev-rollback-vc29.apk
adb install -r -d naozho-0.6.13-dev-power-return.apk
```

回滚后复核 UID、Device Owner、Freeme、系统计时 300、维护设置和已有闹铃，再验证一次普通独立锁定及开发退出。无需给 WakeProbe 授权。
