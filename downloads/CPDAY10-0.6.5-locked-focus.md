# CPDAY10 独立锁定与触摸验收 · 0.6.5-dev

版本码 20，包名 com.naozho.clock。DSH 请记录每一步的设备时间、Lock Task、时钟是否能用手指操作，以及有无使用 ADB 拉起 Activity。

1. 在旧版使用已确认的「开发退出」回到 Freeme 和 NONE，再覆盖安装。

   ```powershell
   adb install -r .\naozho-0.6.5-dev-debug.apk
   adb shell dpm list-owners
   ```

2. 从 Freeme 打开时钟。旧版已保存独立锁定且保留唯一允许名单时，点击图标会重新配置并锁定。首次启用时在开发恢复页选择「锁定当前时钟」。核对 Owner 为 user 0 的 com.naozho.clock/.display.ClockDeviceAdmin、现场状态为 LOCKED、flags 为 80、名单仅 com.naozho.clock，且当前时钟可点击。以下命令均为只读。

   ```powershell
   adb logcat -d -v threadtime -s NaozhoMode:I | Select-String 'Lock Task after start' | Select-Object -Last 2
   adb shell dumpsys activity activities | Select-String 'LockTaskModeState|LockTaskModeTasks|topResumedActivity'
   adb shell dumpsys device_policy | Select-String 'LockTaskPolicy|mFlags|mPackages' -Context 0,2
   ```

   以本次启动时间为准。应用应读回 `state=LOCKED independent=true flags=80 (GLOBAL_ACTIONS|BLOCK_ACTIVITY_START_IN_TASK) allowlist=[com.naozho.clock]`。112 为 16+32+64，80 为 16+64，两组都没有 NOTIFICATIONS(2)。HOME 接管和锁屏设置均无需操作。

3. **用手指**从底边快速连续上划两次，立刻点击「开发退出」，看到确认框后点「取消」。记录弹框和取消是否响应、是否仍为 LOCKED。再次从底边快速连续上划五次，重复同样的触摸检查。只有时钟始终可操作才算通过。
4. 短按电源键真实息屏，再按唤醒，再次用手指打开并取消退出框。最后确认「开发退出」，检查 NONE、Freeme 可停留、Owner 仍在。从图标重进后核对再次读到 80、LOCKED 且能操作。
5. 任一步需要 ADB 拉回时钟才能继续，记为失败。请在恢复操作前保持现场，运行下方采样。对照正常 LOCKED 基线和同一次失焦故障的样本，不要通过打开通知栏或输入凭据来制造证据。

## 故障时同一时段的只读取证

在已连一台设备的 Windows PowerShell 执行以下代码。正常锁定时把 `$sample` 设为 `baseline`，失焦时设为 `fault`。执行期间保持设备原状。文件保存在电脑当前目录，开始和结束时间可与用户手势及应用日志对齐。

```powershell
$sample = 'fault'
$queries = [ordered]@{
    activity = @('dumpsys activity activities', 'LockTaskModeState|LockTaskModeTasks|topResumedActivity|mResumedActivity')
    focus = @('dumpsys window windows', 'mCurrentFocus|mFocusedApp|mTopFocusedDisplayId')
    keyguard = @('dumpsys window policy', 'keyguard|occluded|showing|inputRestricted|bouncer')
    statusbar = @('dumpsys statusbar', 'mDisabled|disable1|disable2|disabled1|disabled2|DisableRecord|displayId|expanded')
    systemui = @('dumpsys activity service com.android.systemui/.SystemUIService', 'bouncer|keyguardShowing|keyguardOccluded|isShowing|shadeExpansion|panelExpansion|expansionFraction|shadeExpanded|panelExpanded|fullyExpanded|tracking|currentScene|disableFlags')
}
$serial = ((& adb get-serialno) -join '').Trim()
if ($LASTEXITCODE -ne 0 -or !$serial -or $serial -eq 'unknown') { throw '请连接一台已授权的 CPDAY10。' }
$jobs = foreach ($entry in $queries.GetEnumerator()) {
    Start-Job -Name $entry.Key -ArgumentList $serial,$entry.Value[0],$entry.Value[1] -ScriptBlock {
        param($device,$query,$pattern)
        "BEGIN $(Get-Date -Format o)  $query"
        $raw = & adb -s $device shell $query 2>&1
        $matched = $raw | Select-String -Pattern $pattern
        if ($LASTEXITCODE -ne 0 -or !$matched) { '未取得对应字段，请核对本机服务名和 dump 输出。' }
        $matched | ForEach-Object { $_.Line }
        "END $(Get-Date -Format o)"
    }
}
$jobs | Wait-Job | Out-Null
foreach ($job in $jobs) {
    Receive-Job $job | Set-Content -Encoding utf8 -Path ("{0}-{1}.txt" -f $sample,$job.Name)
}
$jobs | Remove-Job
adb logcat -d -t 3000 -v threadtime -s NaozhoMode ActivityTaskManager WindowManager StatusBarManagerService |
    Set-Content -Encoding utf8 -Path "$sample-log.txt"
```

核对当前显示器上焦点归属、Keyguard 是否显示或被遮挡、凭据输入页（bouncer）是否显示、面板是否展开及其展开比例，并对照 statusbar 的有效 disable1/disable2 和记录来源。Lock Task 的 feature mask 和 statusbar 的 disable mask 分别解读。若原厂 SystemUI 未导出对应状态，在报告中标为未知；单凭 NotificationShade 窗口名无法区分锁屏、凭据输入页或通知面板。
