# DSH · 1.0.4 审查、部署及恢复手册

当前阶段仅下载并审查。手机可保持 1.0.3、armed 不存在、零监听、300 ms、NONE + Freeme。原有 0.6.13-dev / 28 APK 与 Device Owner 继续使用。

## 电脑端审查

从本次固定提交下载 kit 和 SHA256SUMS.txt。核对 kit 的 SHA-256 后解压，在包内运行以下 PowerShell。cpday10_daily.py 已包含依赖的项目工具代码。

```powershell
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $hash,$name = $_ -split '  ',2
    if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash -ne $hash) { throw "校验不符 $name" }
}
py -3 .\cpday10_daily.py --help
```

如需要完成真实输入回归，只须私下提供此前保存的 316 行原文件。Codex 可直接在开发机重放，不需要 DSH 编程或重新连接手机。完整 dump 可能含窗口标题和应用信息，请留在私下交付位置。

## 仅在后续部署获批后执行

1. 在 Freeme 保持亮屏、无弹窗和监听关闭。核对 CPDAY10 标识、正常开发退出能力，保留既有计时备份和 1.0.3 模块文件。
2. preflight 核对既有 APK、签名、UID、Receiver 和 Owner。stage 将同一个经过校验的 1.0.4 ZIP 复制到 Downloads。使用 KernelSU 管理器更新已有 naozho_power_daily，并按批准范围完成其生效步骤。核对版本 1.0.4 / 5、armed=false、listener_count=0，保留系统计时原值。
3. 首次只做 check-windows，不启用监听、不改 300 ms。查看 snapshot_parse_status、header_found、footer_found、两条实际行号、window_block_count、每窗 flags 来源及 actual_blocker。不同采样的行号可变化。在正常六窗快照上预期 ordinary_freeme 和 6/4/1/0/0。如有阻断，保存本次脱敏 JSON 并停在此处。
4. 只有另获批准才进入既有 600 ms 手势流程。核对一次投递、一次应用返回、时钟焦点、真实 LOCKED + 80 和用户触摸。通知面板、认证、紧急界面和维护暂停应阻断。无需拨打紧急电话。

```powershell
$s = Read-Host "批准测试的 CPDAY10 ADB 标识"
py -3 .\cpday10_daily.py preflight --serial $s
py -3 .\cpday10_daily.py snapshot --serial $s --out before104.json
py -3 .\cpday10_daily.py stage --serial $s
# 管理器更新生效，确认监听仍关闭后
py -3 .\cpday10_daily.py check-windows --serial $s --out freeme104.json
```

## 停用、卸载和完整回滚

- 若以后已启用监听，使用日常模块 Action 停用，确认 armed=false 和 listener_count=0。出现模块故障可在 KernelSU 管理器仅禁用 naozho_power_daily；若管理器不可用，沿用该机既有 KernelSU 安全模式。独立时钟图标与正常开发退出仍是恢复入口。
- 解析器回滚可在停用状态用上版 ZIP 恢复 1.0.3 / 4，并保持关闭。核对 APK、Owner、NONE/Freeme、零监听、原系统计时及其他模块。1.0.3 模块为 45,514 字节，SHA-256 为 `ecaf4eebc0aa686328a9d1f3ad2d8e6c1164e7bb663731b3fa9c15db4b8736c6`。[1.0.3 固定下载](https://raw.githubusercontent.com/shfjq/naozho/10227999c7358b97954a56d70eef3a6bea9dac46/downloads/P0-9.7.3/naozho-power-daily-1.0.3.zip)
- 要彻底撤回日常模块，在停用后用配套工具 timing-status 确认原值与租约。仅当曾批准设置计时时执行 timing-restore 并核对备份；再通过已有管理器流程移除日常模块，检查模块和监听均不存在。若卸载时设置服务不可用，沿用原备份及 recover-timing；出现与备份及目标均不一致的外部设置值应停止。保留时钟、naozho_boot 和设备管理身份。
