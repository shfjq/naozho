# CPDAY10 息屏预热 · 安装、实测和恢复

候选配对为时钟 0.6.15-dev/30 和 naozho_wake 1.1.0/2。以下设备步骤留待批准。云端没有安装候选。保持 naozho_power_daily 关闭，naozho_boot、ADB-Enabler、Device Owner、系统计时 300 及现有独立专机配置沿用。

## 批准后的升级顺序

1. 从同一个固定提交下载候选 APK、候选模块、两份同版本号回滚文件、timeline.py 和 SHA256SUMS.txt。Windows 执行 `Get-FileHash -Algorithm SHA256 .\*.apk,.\*.zip,.\timeline.py`，逐项核对。
2. 先在现有 naozho_wake 的 KernelSU 页面点一次 Action 停用（当前基线已启用），或执行下方明确停用命令。确认 armed 已移除，events 显示 STOPPED。正常“开发退出”到 Freeme 后操作。
3. `adb install -r naozho-0.6.15-dev-wake.apk` 覆盖安装。使用 `adb shell dumpsys package com.naozho.clock` 核对版本 30、原 UID，用 `adb shell dpm list-owners` 核对 ClockDeviceAdmin。先验证图标进入、触摸、开发退出和 Freeme 停留。出现异常就停止。
4. 用 KernelSU 管理器选择 `naozho-wake-1.1.0.zip` 更新同 ID 模块，依管理器提示正常重启。检查新版本及默认停用状态。一次 Action 启用，回到 Freeme。基线为独立专机已配置、维护未暂停、设备清醒、LOCKED 已正常退为 NONE。
5. 保持屏幕亮着直至进入 Freeme。第一次测试前确认 events 中已有 observer_ready 和 ON 基线。整个测试期间通过自然操作亮屏，不使用强制拉起或发送返回指令。

## 短时对照

使用相同亮度、解锁配置和 Freeme 页面。先测三个自然息屏和亮屏周期，每个周期之间用正常开发退出返回 Freeme。可以先用电源键复用上一版条件，再用抬手、双击屏幕或设备支持的完整通知亮屏。另测迅速息屏后立刻唤醒，允许该周期没有预热成功。每次记录时钟首次可见、Freeme 是否闪现、实际触摸反馈。视觉闪现可用外部计时或录像核对，只需在本地查看。

每次实测后在 Windows 下载目录运行：

```powershell
py -3 timeline.py --collect > wake-timeline.json
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState=|mLockTaskPackages'
adb shell dumpsys device_policy | Select-String 'lockTask|LockTask|mFlags=80'
```

timeline 工具只读取模块当前及上一份轮转日志、NaozhoWakePerf 标签。多设备环境先选定 CPDAY10。跨重启的历史归入各自 boot 组；logcat 轮转造成缺项时标明 incomplete。已有 UTF-8 短日志可运行 `py -3 timeline.py --logs module.txt clock.txt` 离线汇总。请在测试后及时导出，无需清理 logcat。

- `warm=ready_same_process` 表示 READY 在亮屏候选前且 Activity 运行于相同 PID。进程被回收、预热未获投递、未达 READY 或过晚，独立记录冷路径。
- `on_to_focus_ms`、`on_to_first_clock_draw_ms`、`on_to_locked_ms` 以观察到默认显示器 ON 回调为起点。`full_to_ready_and_locked_ms` 用于 2 秒目标；另由用户确认点击有响应。
- `candidate_to_root_confirmed_ms` 是与旧版 5250 / 4731 ms 最接近的指标。CLOCK_FOCUSED_AT 是应用收到焦点的时刻，末尾 CLOCK_FOCUSED 是 root 在外部确认并结束该次请求的时刻。COMMIT 回执可能晚于 Activity 启动。应用绘制完成的日志与屏幕物理呈现有合成及刷新差异。
- 跨多轮对照时记录逐轮数值和中位数，不取单个最快周期替代结果。缺少阶段、重复请求和相互矛盾的记录由工具标明，不能计为成功周期。

## 必须回归的行为

|操作|验收|
|---|---|
|普通 Android 息屏|预热没有窗口、无正式 RETURN、无锁定；显示保持暗。已有进程可复用，Application 不重复初始化。|
|完整唤醒|一个独立 epoch、最多一个 RETURN 和一个 COMMIT；实际时钟前台、LOCKED、flags=80、单包允许名单且手指可操作。|
|AOD 脉冲、DREAMING、普通通知未点亮、通话、凭据或实际遮挡|保留现有拒绝行为。闹铃本身的响铃交互优先。|
|开发退出、已锁定时再次亮屏|确认退出后 Freeme 可停留，持续亮屏不再拉回。已锁定时不重复启动。|
|时钟进程被普通回收|无预热 READY 仍应冷启动。请只记录自然回收或可安全复现的情况，避免以“强行停止”替代进程回收。|
|维护暂停、恢复|暂停后历史预热和请求均无返回权；恢复后重新建立亮屏基线，在新周期验收。|

## 停用和回滚

一键停用当前模块：

```powershell
adb shell "su -c 'sh /data/adb/modules/naozho_wake/stop.sh'"
```

也可在已启用状态点模块 Action。确认停止后从时钟正常退出。单独停用模块即可停止自动返回，时钟图标和独立锁定继续可用。

**恢复到上一版已验证的行为**：覆盖安装 `adb install -r naozho-0.6.14-dev-vc30.apk`，再在 KernelSU 中选择 `naozho-wake-1.0.0-vc30-rollback.zip`。按管理器提示重启、检查版本和 Owner、再显式启用。这两件配套：应用保留 versionCode 30，回滚模块使用原 1.0.0 观察代码，内置 APK 校验值对应同版本号回滚包。升级与回滚无需卸载时钟或清除应用数据。回滚后短测一次自然唤醒以及正常开发退出。

如确需恢复为原始 29 字节版本，先停用模块，再使用设备允许的调试降级安装方式及原配的 1.0.0 ZIP。降级拒绝时使用上述同版本号配套。原始发布仍可下载。[0.6.14-dev/29 与原版 1.0.0](https://github.com/shfjq/naozho/tree/873bf0ddf8f7302549a06d9bd24de3a50c7afc11/downloads/P0-9.7.9)

若出现启动异常，沿用设备已有的 KernelSU 恢复入口单独禁用 naozho_wake。模块未写入系统镜像。恢复后核对应用数据、Owner、300ms 计时及原桌面。
