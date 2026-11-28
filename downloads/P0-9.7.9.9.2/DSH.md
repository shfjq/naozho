# CPDAY10 0.6.23-dev / 38 候选验收与回滚

本包用于城市跳转及 Android 调度恢复候选验证。Atlas 拒绝投递的场景仍待厂商授权方案。现有可用组合为 0.6.22-dev / 37 与 wake 1.5.2 / 9，两份原始文件均随包保留。全部下载应来自同一 GitHub 固定提交，请先比对 SHA256SUMS.txt。

1. 用已授权的本机 ADB 核对设备型号、原应用包、UID、Device Owner 和当前模块版本。通过正常操作从时钟退出，停用 wake。在 KernelSU 管理器升级至 1.5.3 / 10，按管理器提示重启并核对实效。保持 wake 停用直到 APK 已覆盖。
2. 保留原数据和 Owner，使用同签名包覆盖安装。

   ```powershell
   $serial = Read-Host "本机已授权的 CPDAY10 序列号"
   adb -s $serial install -r .\naozho-0.6.23-dev.apk
   adb -s $serial shell dumpsys package com.naozho.clock | Select-String 'versionName=|versionCode=|ACCESS_COARSE_LOCATION'
   adb -s $serial shell dpm list-owners
   ```

3. 用现有粗略定位权限及正常定位入口执行一次定位，记录城市、温度与成功时间。只有真实区域名称出现在钟面才能记为通过。若需要核对邻接任意一个跳转，只保留域名、HTTP 状态码及城市字段，设备坐标等信息留本机。
4. 启用 1.5.3 并核对 `CLOCK_IDENTITY_READY version=0.6.23-dev code=38`。验证一次实际息屏唤醒。天气先记真实成功时间 T0，再从普通应用息屏跨过 T0+60 分钟。核对 `NaozhoWeather` 的 `weather_schedule`、`forecast_cache_success updatedAt=...` 和任务 ID。若只有系统登记或 Atlas 拒绝记录，本次后台更新仍未通过。另检查一次断网后旧数据保留、恢复网络后补更，以及正常重启后能否恢复。
5. 如 Atlas 仍拒绝，只保留天气接收器的时间、组件与拒绝原因，并向厂商核对该机型支持的受管授权入口。

## 停用和回滚

wake 可通过 KernelSU 管理器的模块「操作」或停用开关关闭，按提示重启并核对进程退出。需要卸载时只移除 wake 模块，不卸载时钟。要完整恢复到 37，先正常退出时钟并停用 wake，然后在固件支持可调试包无损降级的条件下执行：

```powershell
adb -s $serial install -r -d .\naozho-0.6.22-dev.apk
```

如果安装器拒绝降级，保留 38、设备数据及 Owner，停止本次回滚。成功恢复 37 后，通过管理器恢复原始 wake 1.5.2 / 9 并按提示重启。核对模块版本、应用版本、UID、Device Owner 和实际唤醒后结束验收。
