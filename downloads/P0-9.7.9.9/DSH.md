# CPDAY10 0.6.22-dev / 37 部署与验收

时钟候选使用原证书。先核对现场的时钟版本、安装 UID、Device Owner、SELinux 和 wake 模块版本。正常退出 LOCKED 后停用 wake，确认进程已退出，再用 KernelSU 管理器安装 1.5.2 / 9 并按管理器提示重启。新模块同时接受原始 35、36、37。先读回模块版本，再覆盖安装时钟。

## 从固定提交下载

在电脑的新目录运行下列 PowerShell，填入发布页的 40 位提交。下载并逐项核对清单。

```powershell
$rev = Read-Host "GitHub 发布提交"
if ($rev -notmatch '^[0-9a-f]{40}$') { throw "请输入完整提交" }
$base = "https://raw.githubusercontent.com/shfjq/naozho/$rev/downloads/P0-9.7.9.9"
Invoke-WebRequest "$base/SHA256SUMS.txt" -OutFile SHA256SUMS.txt
foreach ($line in Get-Content SHA256SUMS.txt) {
    if ($line -notmatch '^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)$') { throw "校验清单格式错误" }
    $expected = $Matches[1]
    $file = $Matches[2]
    Invoke-WebRequest "$base/$file" -OutFile $file
    if ((Get-FileHash -Algorithm SHA256 $file).Hash.ToLowerInvariant() -ne $expected) { throw "文件校验失败 $file" }
}
```

用已授权的本机连接，只选择已核对的 CPDAY10。在完成 wake 模块升级并保持停用后执行覆盖安装。

```powershell
$serial = Read-Host "已授权的 CPDAY10 ADB 序列号"
adb -s $serial shell dpm list-owners
adb -s $serial shell cmd package list packages --user 0 -U com.naozho.clock
adb -s $serial install -r .\naozho-0.6.22-dev.apk
adb -s $serial shell dumpsys package com.naozho.clock | Select-String 'versionName=|versionCode=|ACCESS_COARSE_LOCATION'
adb -s $serial shell dpm list-owners
```

确认 `Success`、37、原 UID、原 Owner 和已有设置后再启用 wake。确认当前日志有 `CLOCK_IDENTITY_READY version=0.6.22-dev code=37` 和 `observer_ready`。做一次普通息屏唤醒，核对同一请求的 RETURN、COMMIT、焦点和锁定证据及真实触摸。[既有唤醒日志核对说明](https://github.com/shfjq/naozho/blob/673baff3245b1107e275145968338c9ad5bc365b/downloads/P0-9.7.9.8.1/DSH.md)

## 天气与退出验收

1. 打开显示设置并点「自动获取当前位置」。正常授权后检查城市、温度、天气状况及最后成功时间。拒绝授权时检查手动坐标可用。在 CPDAY10 异常授权弹窗出现时记录当时的 app 权限实际状态，以及前台权限 Activity 是否出现。历史只确认该 ROM 上弹窗异常和单项授权后可定位，缺少本轮 PermissionController 日志，原因尚未证实。已授权维护人员如需使用现有 Android 管理路径，只处理 `com.naozho.clock` 的 `android.permission.ACCESS_COARSE_LOCATION`，并用上面的 PackageManager 查询确认结果。
2. 第一次天气成功后记录界面更新时间。让时钟后台或屏幕熄灭跨过下一小时边界，再检查实际保存的下一次成功时间。记录是否处于 Doze、精确闹钟可用性和实际差值。队列中出现 Alarm 或 Job 只能证明已登记。可用针对性的重启与系统回收测试核对补更。使用 Android 正常的应用进程回收场景，强行停止属于不同的系统状态。
3. 做一次断网后恢复。失败应保留读数和时间，联网后已到期的天气应尽快补更。后台请求只读已保存坐标。定位权限仅用于用户点击自动定位，网络城市识别可收到约略坐标。保留日志在本机。
4. 版本号前六次完全静默。五秒内第七次出现原确认框。先取消验证仍留在时钟，再触发一次并确认退出到 Freeme。另检查超过五秒及离页重入不会累计。

用本机只读日志核对两条 `forecast_cache_success updatedAt=` 的时间差，以及 `forecast_refresh_failed reason=`。这些行来自更新结果。检查调度时可另行查看 `weather_schedule`，它只显示登记情况。

```powershell
adb -s $serial logcat -d -s NaozhoWeather
```

## 回滚到上一生产组合

从时钟正常退出并停用 wake。使用上一生产版 36 的原始 APK 覆盖降级，检查安装结果、版本、原 UID、应用数据与 Device Owner。

```powershell
adb -s $serial install -r -d .\naozho-0.6.21-dev.apk
```

如果系统拒绝降级，保留当前 APK、数据与 Owner，停止回滚。降级成功后，可保留 1.5.2 并再次启用，也可在 wake 停用时用管理器恢复原始 `naozho_wake-1.5.1.zip`，按管理器提示重启后再启用。原始 35 也随包提供，由 1.5.2 接受。完成后核对版本、有效 UID、Owner、数据与实际唤醒。
