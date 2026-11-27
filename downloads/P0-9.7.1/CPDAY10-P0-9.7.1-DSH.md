# DSH 手册 · CPDAY10 日常电源双击 1.0.1

目前只作电脑端审查。以下设备步骤在另行批准后执行。沿用现有 0.6.13-dev / 28、ClockDeviceAdmin、naozho_boot 和正常开发退出。安装包是模块 ZIP，不要在时钟应用上做卸载或降级。

## 电脑端准备

下载同一固定提交的 kit 和 SHA256SUMS.txt。在 PowerShell 用 Get-FileHash 核对 kit，再解压到新目录。打开该目录运行以下命令。用 Android SDK 的 apksigner 和已授权的 adb。工具只在 preflight 临时拉取已安装 APK 检查签名和哈希。

```powershell
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $hash,$name = $_ -split '  ',2
    if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash -ne $hash) { throw "校验失败 $name" }
}
py -3 .\cpday10_daily.py --help
$s = Read-Host "输入已批准的 CPDAY10 ADB 连接标识"
py -3 .\cpday10_daily.py preflight --serial $s
py -3 .\cpday10_daily.py snapshot --serial $s --out old-disarmed.json
```

核对当前手机为 1.0.0 关闭、armed=false、listener_count=0、NONE、Freeme、Owner 和 Enforcing。保留该文件及原来的 1.0.0 模块。若基线不同，先核对原因。

## 分开安装、准备系统值和启动监听

1. 运行 stage 仅复制 ZIP 到 Downloads。经批准后，用管理器安装此 ZIP 并按管理器要求正常重启。只更新 naozho_power_daily。安装后检查版本 1.0.1、未 armed 和零监听；开机模块如已恢复时钟，先通过正常开发退出回到 Freeme。
2. 运行 timing-status、timing-prepare。准备工具先把用户 0 原值存入一个新电脑文件，手机侧也先写私有恢复记录，再通过 SettingsProvider 设置并读回。保留该文件，缺省值会保存为 null。默认 600。改档时须先关闭监听并 restore，然后以新的备份文件 prepare，可传 --ms 400、500、600、700、800 或 1000。
3. 原厂策略在类初始化时缓存值。准备后按批准流程正常重启一次，核对读回和正常单击，再在管理器点击本模块 Action 一次。任一步失败都先停下。不使用系统进程强制重启。即使写入成功，也要以实际按键派发和实测边界验收。

```powershell
py -3 .\cpday10_daily.py stage --serial $s
# 经批准在管理器安装并正常重启
py -3 .\cpday10_daily.py timing-status --serial $s
py -3 .\cpday10_daily.py timing-prepare --serial $s --backup baseline-600.json
py -3 .\cpday10_daily.py timing-status --serial $s
# 经批准正常重启，回到普通 Android，再用 Action 启用
py -3 .\cpday10_daily.py snapshot --serial $s --out enabled.json
```

检查监听进程恰好一个。若显示 disabled_timing_not_prepared、timing_setting_changed、APK 或权限探测失败，先停用再诊断。平时使用无需 ADB 或管理器。

## 真实双击计时与窗口验收

每轮从真实亮屏、NONE 的预定页面开始。snapshot 不会制造输入。可选 sample-pair 让同一监听器在 30 秒内量一对实体 POWER 的两次按下间隔、各次按住时长。它不会使非合格手势变为合格。记录电脑输出的票号，与 after JSON 中 sample 票号核对。超过时限、遇到长按重复或样本跨休眠时重新编号记录，不能作为边界成功证据。平时无需开启该测量。

```powershell
py -3 .\cpday10_daily.py snapshot --serial $s --out freeme01-before.json
py -3 .\cpday10_daily.py sample-pair --serial $s
# 用手指按；返回时钟后触摸一个可见控件，实际确认界面有回应
py -3 .\cpday10_daily.py snapshot --serial $s --out freeme01-after.json
py -3 .\cpday10_daily.py assess freeme01-before.json freeme01-after.json --expect return --touch-confirmed
```

**每次成功**均要求 1 次正式请求、同一进程确认投递、系统实际识别该第二击、时钟获得真实焦点、LOCKED、flags=80、允许名单只有时钟、手指实际可操作。policy_return.down_gap_ms 可验证成功时的间隔。失败时结合 veto.last_veto_at 与本轮时间、veto.extra_windows、veto.windows、sample 及投递计数。负向测试使用 --expect no-return（正常开关屏测试可在恢复原来的页面后取 after，另行记录实际屏幕变化）。若缺少系统回执，留存当前记录，勿反复发送探测。

| 验收项目 | 操作与判据 |
| --- | --- |
| 用户自然速度 | 先不看秒表，Freeme 连续三轮，记录间隔和用户是否仍需刻意抢按。正常开发退出后应停留原桌面。 |
| 300、400、500、600 附近 | 交替试约 300、400、500 ms，以及接近 600 的两边；按实际 sample 分组。原厂严格小于，599 ms 可合格，等于及大于 600 不合格。人工未取得精确的 600 ms 样本就标“边界待测”。两次独立单击可使屏幕熄灭再唤醒，不能计作成功返回。 |
| 系统单击与长按 | 在相同亮度与页面，分别在配置前、启用后、恢复原值后，用外部计时或慢动作视频仅观察实体键与屏幕亮灭（不要摄入私人界面）。记录松开至屏幕熄灭、熄屏按下至亮屏的时间。长按应显示原电源菜单，取消后原页仍可用。 |
| 普通窗口 | 无弹窗的 Freeme、设置首页、已评审 OpenCalc 主界面各多轮；打开实际 USB 弹窗、通知面板、控制中心、输入法、认证或紧急入口时应为零正式请求。不要拨打真实紧急电话。未知普通页返回 unreviewed_page 时记为适用范围限制。 |
| 模式与时序 | 已 LOCKED 时重复双击不重启。应用主动维护暂停后双击、暂停后重启、暂停前已排队的请求均不能带回时钟；恢复专机、正常退出，再用一组新双击返回。快速三击、长按不应提交。检查开发退出取消/确认与实际触控。 |
| 重启与正常手机功能 | 已授权启用时，分别正常重启和关机再开，核对一个监听、设置读回、实际双击。检查单击、充电、温度、Wi-Fi、蓝牙和基本紧急入口。不要把开机模块自动进入时钟计作双击。 |
| 耗电 | 取相同亮度、网络、充电及后台负载下两段等长的息屏时间，建议各 8 小时且不充电。一段停用，一段启用。每段独立取两次 snapshot，运行下面的 consumption。比较电量/小时、温度、电荷计数、系统唤醒、进程 CPU/FD/RSS/线程数和日志字节，记录不可读项。之后按相同方法再测 24 小时资源增长。 |

```powershell
py -3 .\cpday10_daily.py consumption standby-before.json standby-after.json
```

如 400–599 ms 的真实手势总被系统处理为单击，记录该次屏幕亮灭、实际样本、setting、veto 和正式请求数；若是 policy_double_unconfirmed，还可能是该机不输出可关联的系统日志。不要用短间隔成功替代 600 档验收。若是 additional_visible_window，只需交回此次快照的脱敏窗口条目。无需全量日志、截屏或再次采集固件。

## 停用、卸载与恢复

1. Action 关闭监听。核对 armed=false、listener_count=0。管理器禁用也会让监听退出。关闭监听与恢复用户全局计时是两个操作，前者单独执行时仍保留所选计时。
2. 完整回退时，在本模块仍安装、监听已停止时运行 timing-restore，按原值或原缺省状态恢复，再做正常重启、读回及真实单击。若检测到设置已被其他程序改成第三个值，会保留该值和日志，交 DSH 核实，不要强制覆盖。
3. 需要卸载时，仅移除 naozho_power_daily。卸载脚本在设置服务可用时也尝试恢复；如无法运行，私有恢复记录保留，电脑备份可作补救。用普通时钟图标、原开发退出和原维护入口继续使用。
4. 卸载后若读回仍是本模块目标值，使用同一台设备的备份执行 recover-timing。工具校验设备、模块已移除、当前值属于备份的目标或原值，然后恢复并读回。再次正常重启验证。需要退至 1.0.0 时，在原值确认后用上一版已校验的 ZIP 安装，保持关闭。Owner、时钟和 naozho_boot 无需改动。
5. 界面异常时，使用已批准的管理器禁用本模块，或由 DSH 使用设备既有的 KernelSU 模块安全恢复流程。ADB 已授权且可用时，以下命令只停用当前日常模块；随后处理计时恢复。出现基本紧急入口、开机或单键唤醒异常时，结束本轮体验测试。

```powershell
py -3 .\cpday10_daily.py timing-restore --serial $s
py -3 .\cpday10_daily.py timing-status --serial $s
# 仅在已卸载且需要用电脑备份恢复时执行
py -3 .\cpday10_daily.py recover-timing --serial $s --backup baseline-600.json
# 仅在故障时停用此模块
adb -s $s shell "su -c 'touch /data/adb/modules/naozho_power_daily/disable'"
```

电脑备份和真机 JSON 留在本地。开机动画后的第一屏单独验收，需另行记录动画结束到首次可触摸时钟之间有无锁屏或 Freeme。
