# CPDAY10 唤醒模块 1.5.1 部署与回滚

配套包包含两份原始、同签名、可调试的时钟 APK，唤醒模块 1.5.1 / 8 和原始唤醒模块 1.5.0 / 7。1.5.1 同时接受 35 和 36。1.5.0 仅接受 35。两版 APK 的源码和签名材料无需重建。本轮未连接 CPDAY10。Android 16 原厂固件上的覆盖安装、降级和自动唤醒仍需 DSH 验证。

## 下载与核验

在电脑上新建空目录。把发布页提供的 40 位提交填入 PowerShell，并执行下列命令。所有文件从同一固定提交获取。

```powershell
$rev = Read-Host "GitHub 发布提交"
if ($rev -notmatch '^[0-9a-f]{40}$') { throw "请输入完整提交" }
$base = "https://raw.githubusercontent.com/shfjq/naozho/$rev/downloads/P0-9.7.9.8.1"
Invoke-WebRequest "$base/SHA256SUMS.txt" -OutFile SHA256SUMS.txt
foreach ($line in Get-Content SHA256SUMS.txt) {
    if ($line -notmatch '^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)$') { throw "校验清单格式错误" }
    $expected = $Matches[1]
    $file = $Matches[2]
    Invoke-WebRequest "$base/$file" -OutFile $file
    if ((Get-FileHash -Algorithm SHA256 $file).Hash.ToLowerInvariant() -ne $expected) { throw "文件校验失败 $file" }
}
```

用已有授权的 ADB 连接，并指定已核对的设备序列号。记录安装前 APK 版本、实际 UID、Device Owner、锁定状态、SELinux 和 KernelSU 中的模块状态。时钟若在 LOCKED 中，先走正常开发退出。通过 KernelSU 当前模块的「操作」停用已启用的 wake，等到它退出，再开始更换文件。

```powershell
$serial = Read-Host "已授权的 CPDAY10 ADB 序列号"
adb -s $serial shell dumpsys package com.naozho.clock |
    Select-String 'versionCode=|versionName=|userId=|appId='
adb -s $serial shell cmd package list packages --user 0 -U com.naozho.clock
adb -s $serial shell dpm list-owners
adb -s $serial shell getenforce
adb -s $serial shell dumpsys activity activities | Select-String 'mLockTaskModeState='
```

## 升级 35 → 36

1. 在 KernelSU 管理器安装 `naozho_wake-1.5.1.zip`。按管理器提示重启并核对 1.5.1 / 8 实际生效。此时先保留 35。需要验收 35 时，启用 wake，完成一次真实息屏唤醒，核对最新日志中的 `CLOCK_IDENTITY_READY version=0.6.20-dev code=35` 和同一请求的正式接管。继续升级前再次正常退出时钟并停用 wake。
2. 使用下列覆盖安装命令。确认 Package Manager 返回 `Success`，复核 versionCode 36、原 UID 和同一 Device Owner。

```powershell
adb -s $serial install -r .\naozho-0.6.21-dev.apk
```

3. 在管理器启用 wake。确认当前进程的 `CLOCK_IDENTITY_READY version=0.6.21-dev code=36`，且之后出现 `observer_ready`。正常用浏览器完成一次息屏唤醒。核对同一请求的 RETURN 与 COMMIT 各一次，`CLOCK_FOCUS_LOCK_VERIFIED_AT`、`HANDOFF_COMPLETE`、时钟真实可触摸和 LOCKED + 80。日志仅保存在本机。

## 回滚 36 → 35

1. 先正常退出时钟，停用 wake，确认时钟没有处于 LOCKED。
2. 两份 APK 均已确认带 `application-debuggable`。ADB 在可调试应用上以 `-d` 请求允许版本号降级，以 `-r` 覆盖并保留数据。使用已验证的原始 35 APK。

```powershell
adb -s $serial install -r -d .\naozho-0.6.20-dev-rollback.apk
```

3. 如果 CPDAY10 固件拒绝降级，保留 36 与应用数据，保留 wake 停用状态。记录安装器错误，停止本次回滚。
4. 降级成功后复核实际版本 35、相同 UID、Device Owner 和原设置。启用 1.5.1 并确认日志识别 35。用一次正常息屏唤醒核对真实焦点与锁定。
5. 如果还要恢复模块 1.5.0，确认现在已恢复原始 35 并停用 wake，然后从管理器安装 `naozho_wake-1.5.0-original.zip`，重启核实版本并启用。若管理器拒绝同 ID 的旧版本安装，可以只在管理器移除 wake 模块、重启、再安装原模块。时钟应用、应用数据和 Device Owner 继续保留。

## 停用

在 KernelSU 管理器中使用 wake 模块的「操作」停用已启用实例，或使用模块开关并按管理器提示重启。若系统仍处于专机锁定，先用应用正常退出。停用或回滚后，确认实例退出且正常 Android 可用。此次更换只涉及 `naozho_wake` 和已核验 APK 的覆盖安装。
