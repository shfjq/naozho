# DSH · P0-9.7.3 审查、部署与回滚

**本轮仅云端审查。当前不用连接手机。** 后续设备步骤分别需要部署和功能测试批准。

## 电脑端检查

从同一个 GitHub 固定提交下载完整 kit 与 SHA256SUMS.txt。用 Get-FileHash 核对 kit 并解压，在新目录执行以下 PowerShell 命令。交付包附有独立 cpday10_daily.py，无需编程。

```powershell
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $hash,$name = $_ -split '  ',2
    if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash -ne $hash) { throw "校验不符 $name" }
}
py -3 .\cpday10_daily.py --help
```

## 以后获准部署时，先只检查窗口

1. 保留安装中的 0.6.13-dev / 28、Owner、开机模块、计时原值备份及 1.0.2 ZIP。在普通 Freeme 亮屏、无弹窗状态记录基线，确认日常监听关闭。应用 APK 不用安装。
2. preflight 核对现有 APK、签名、用户与 Receiver。stage 只向手机 Downloads 复制模块 ZIP；经批准后在 KernelSU 管理器更新同一模块 naozho_power_daily。按既有管理器批准流程完成安装，核对版本 1.0.3、code 4、armed=false、listener_count=0。
3. 保持监听关闭，使用 check-windows 取得一份新 JSON。它既不设置计时，也不要求切到 600 ms、按电源键或触发锁定。现场不需要重复 1.0.2 的采集。如果只需查看两栏的公开标志，1.0.3 的 window-fields 与检查器共用同一个模块解码器；两命令各自运行时仍是两次快照。
4. 对这台手机的正常六窗基线，期待 ordinary_freeme、6/4/1/0/0，以及两个已验证的非交互装饰、两个正常窄边栏、前台 app、背景 wallpaper。根据实际字段逐项核对。若不符，保留这一次脱敏 JSON，暂停手势测试。查看 flags_line_found、flags_parse_status、parser_error、class_reason、actual_blocker；不要启用模块来绕开否决。

```powershell
$s = Read-Host "输入获准的 CPDAY10 ADB 标识"
py -3 .\cpday10_daily.py preflight --serial $s
py -3 .\cpday10_daily.py snapshot --serial $s --out before103.json
py -3 .\cpday10_daily.py stage --serial $s
# 安装批准后由管理器完成更新并保持关闭
py -3 .\cpday10_daily.py check-windows --serial $s --out freeme103.json
```

## 以后单独获准手势验收时

复用已有 600 ms 备份与 lease，先用 timing-status 核对。如现场仍为 300 ms，停留在只读验收，系统计时的后续改变须在批准范围内。从亮屏 NONE + Freeme 开始，取 before，用户自然双击一次；时钟出现后触摸可见控件，再取 after。每轮用新文件。完整通过要求一次正式请求、一次验证投递、时钟焦点、实际 LOCKED、flags=80、仅时钟获准并且触摸成功。

```powershell
py -3 .\cpday10_daily.py snapshot --serial $s --out gesture-before.json
# 已批准后才进行实体双击和触摸
py -3 .\cpday10_daily.py snapshot --serial $s --out gesture-after.json
py -3 .\cpday10_daily.py assess gesture-before.json gesture-after.json --expect return --touch-confirmed
```

确认开发退出回到 NONE/Freeme，取消退出继续锁定。活动通知面板、控制中心、输入法、USB/授权弹窗、凭据/紧急界面及维护暂停时应无正式返回；只观察紧急入口，不拨号。单击息屏/唤醒、长按菜单继续沿用已验收行为。某一次投递或模式切换不清楚时，留存当前记录并停止。

## 停用、卸载、回滚

- 日常模块已启用时用其 Action 关闭，核对 armed=false 和实际监听进程为零；模块有故障时使用管理器仅禁用 naozho_power_daily。需要界面故障恢复时沿用设备既有 KernelSU 模块安全模式。时钟图标和原开发退出可继续使用。
- 若仅回滚窗口解析版本，在已停用状态用已校验的 1.0.2 模块恢复原版，保持关闭，核对 Owner、APK、原计时值、NONE/Freeme 及零监听。无需操作系统框架。1.0.2 ZIP SHA-256 为 `dbe30d35a404da4937dde6df9bbad67e7d1a82a7077cc00ebbe6b2eb53e708d1`。[1.0.2 固定下载](https://raw.githubusercontent.com/shfjq/naozho/5cae15d3f1e708266b0a50a34c2fcdcbf748db5d/downloads/P0-9.7.2/naozho-power-daily-1.0.2.zip)
- 若以后批准完整撤销系统计时，用当时安装版本的工具在停用后执行 timing-restore 并核对原值，再只移除日常模块；若卸载发生在设置服务不可用时，可对同一设备与原备份运行 recover-timing。遇到非备份原值、非模块目标值的外部改变，应停止并核对。此次云端修复不需要执行这些设备操作。
