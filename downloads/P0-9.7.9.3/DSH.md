# DSH 短时验收与恢复 · P0-9.7.9.3

配套版本为时钟 0.6.16-dev/31、naozho_wake 1.2.0/3。原版 0.6.15-dev/30、1.1.0/2 的固定下载目录保留。本轮仅在审核批准后执行设备步骤。[已验收版本](https://github.com/shfjq/naozho/tree/e19f8e6ad0c4d311daa4b50116fac63fb916ed59/downloads/P0-9.7.9.2)

## 安装

1. 从本版本同一固定提交下载候选 APK、候选模块、两份回滚文件、timeline.py 和 SHA256SUMS.txt。下列命令在下载目录执行。PowerShell 使用 `Get-FileHash -Algorithm SHA256 .\*.apk,.\*.zip,.\timeline.py` 对照清单，保存回滚文件。
2. 停用原唤醒模块。用现有「开发退出」正常回到 Freeme，检查 Owner、UID、独立锁定设置及版本。保留现有开机模块和 ADB-Enabler，日常电源键模块维持停用。
3. 覆盖安装 `adb install -r naozho-0.6.16-dev-wake.apk`。用 `adb shell dpm list-owners` 和 `adb shell dumpsys package com.naozho.clock` 核对 user 0 的 ClockDeviceAdmin、原 UID 和版本。点图标进入时钟，确认触摸可用，再走一次开发退出，确保可在 Freeme 停留。
4. 在 KernelSU 管理器更新同 ID 模块 `naozho-wake-1.2.0.zip`，按管理器提示重启。核对新模块版本和停用状态，确认当前为普通 Android、独立专机已配置、维护未暂停；用模块 Action 启用一次。模块只接受本版本配套 APK 摘要。

## 判断时钟出现是否更快

1. 在 Freeme 正常息屏，再自然唤醒。前一轮已测得亮屏到焦点 3.05～3.20 秒，尽量使用相同页面、亮度和唤醒方式。每次检查时钟显示时间正确，实际点击一个控件有响应，再开发退出，亮屏停留在 Freeme。做三次短周期，记录每一次结果，包括失败。
2. 用外部摄像设备（如有）在本地观察从面板首次点亮到可辨认钟面的帧数，按实际帧率换算，逐轮标记有无 Freeme 可见帧。不能观察清楚时记「未知」。时钟得到焦点、应用执行绘制、面板显示、指尖可操作分别记。
3. 每轮用下面的只读命令记录实际时钟焦点、LOCKED、80 和仅含 com.naozho.clock 的允许名单。保存 JSON 到本机。无须清理系统日志。

```powershell
py -3 timeline.py --collect --summary > wake-result.json
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState=|mLockTaskPackages'
adb shell dumpsys device_policy | Select-String 'lockTask|LockTask|mFlags=80'
```

4. 同一开机内分别看 `on_to_first_clock_draw_ms`、`on_to_focus_ms`、`on_to_locked_ms`，目标为亮屏后尽可能在 2000 ms 内看到钟面。关注 `on_to_activity_ms`、`activity_request_to_start_ms`、`activity_to_first_draw_ms`。先区分 `on_new_intent/retained_clock=true` 与 `on_create`，再看相同组的逐轮结果和中位数；保留缺段、拒绝和触摸失败的次数。单独记录冷启动或系统回收。正常维护使用中已有的前台启动即可建立下次可复用的窗口。旧版日志缺少新增阶段时仍能读取共有指标。
5. 复测一次快速息屏再亮、一次暂停期间息屏再亮、恢复后下一次完整唤醒。已经在时钟时唤醒应留在可操作时钟，持续亮屏没有第二次请求。优先验收到达实机的唤醒来源。若出现 AOD、DREAMING、来电、系统确认等受保护场景，记录是否按既有规则留给系统；不主动拨打紧急电话。出现重复启动、退不出、触摸异常或无焦点锁定时立即停用。

## 停用与回滚

随时可以单独停用自动返回。在已启用时点模块 Action 一次，或执行下列幂等命令。核对 armed 已移除及日志 STOPPED，再用正常开发退出回到 Freeme。

```powershell
adb shell "su -c 'sh /data/adb/modules/naozho_wake/stop.sh'"
```

恢复到真机验收过的代码时，执行 `adb install -r naozho-0.6.15-dev-vc31.apk`，再用 KernelSU 管理器安装 `naozho-wake-1.1.0-vc31-rollback.zip`，按提示重启，核对 Owner、应用数据、原生桌面、锁定和触摸，再显式启用。回滚 APK 保留 versionCode 31 以允许等版本覆盖；模块校验该回滚 APK。两者成对使用。只想移除自动返回，可停用后仅在管理器卸载 naozho_wake 并按提示重启。手机启动异常时使用设备已验证的 KernelSU 恢复入口禁用此模块。原时钟、naozho_boot 和正常维护退出仍可使用。
