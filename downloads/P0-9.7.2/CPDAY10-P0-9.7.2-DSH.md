# DSH 验收手册 · Freeme 窗口分类 1.0.2

**当前只在电脑审查。设备操作全部留待下一次明确批准。** 本轮没有操作 CPDAY10。现有手机的 300 ms 设置、已安装时钟、Owner 和模块状态按现场读数登记。1.0.1 已有的 600 ms 验证和电源键单次链路无需重做。

## 电脑上核对交付

从固定提交下载完整 kit 与 SHA256SUMS.txt，先核对 kit 的 Get-FileHash，再解压。在新目录执行以下 PowerShell 命令；Python 3.9+、既有 ADB 和 apksigner 即可。

```powershell
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $hash,$name = $_ -split '  ',2
    if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash -ne $hash) { throw "文件校验失败 $name" }
}
py -3 .\cpday10_daily.py --help
```

## 需要原始字段时，仅一次只读采样

目前缺失的是出错当时两扇 SystemUI 栏的公开 fl / flags 原始写法，以及它们是否给出 mTouchableInsets、mGivenInsetsPending 和 touchable region。历史资料若有相应两扇窗口的这些字段即可复核。以后获准且确需补采时，在普通 Freeme、无弹窗下运行下面命令一次。可用已有 1.0.1，监听保持关闭。它只读一次 WMS 可见窗口，从中仅输出 STATUS_BAR 和 NAVIGATION_BAR 的标志与区域格式，未识别的标志词会脱敏；不采集标题，不需要 Root 写入、触发手势、改设置或重启。它测量采集当时的状态。

```powershell
$s = Read-Host "已批准的 CPDAY10 ADB 连接标识"
py -3 .\cpday10_daily.py window-fields --serial $s --out two-bars.json
```

## 获批后，先验证分类

1. 保存现有 timing-prepare 的本地备份及 1.0.1 发布包。只读核对包签名、UID、Owner、NONE、Freeme、Enforcing 和零监听。此版本接受旧 last-veto 数据。
2. 获批安装时执行 stage（仅复制），在 KernelSU 管理器按设备既有流程升级**同一个** naozho_power_daily。安装默认关闭。若管理器提示需要重启，按下一阶段批准范围安排。无需重新安装 APK 或重配 Owner。
3. 确认版本、现场计时读回和零监听。在普通 Freeme 使用 check-windows。此诊断与手势走同一 WMS 采集、分类和前后焦点复核；它不启动监听、不发送探测、不提交返回。**在 300 ms、没有计时 lease 时也能检查。**
4. 期待 decision=ordinary_freeme、blocking_window_count=0、unknown_window_count=0，点查两个面板均为 verified_passive_decor，导航栏及状态栏为 verified_edge_bar；六窗基线应有四个装饰。真实窗口数变化时逐项核对，不能以“恰好六个”替代检查。如果失败，查看 actual_blocker=true 的行、class_reason、parser_source、field_missing、触摸区域和解析状态；整体中止时同时看 decision。保留这一次 JSON，暂停手势测试。

```powershell
py -3 .\cpday10_daily.py preflight --serial $s
py -3 .\cpday10_daily.py snapshot --serial $s --out before-upgrade.json
py -3 .\cpday10_daily.py stage --serial $s
# 获准安装 1.0.2 后，保持监听关闭
py -3 .\cpday10_daily.py timing-status --serial $s
py -3 .\cpday10_daily.py check-windows --serial $s --out freeme-classifier.json
```

## 再单独验收完整返回

此阶段需要获批的日常模块和系统计时配置。如果现场仍是 300 ms、lease 不匹配，停在只读检查。以后获批恢复 600 ms 测试时，沿用 timing-prepare --serial $s --backup <新的本地文件名>，默认 600；不得覆盖原有备份。按既有流程检查读回和缓存，确认条件再通过模块 Action 主动启用。日常使用不用电脑。

| 场景 | 操作与判据 |
| --- | --- |
| 自然双击 | 亮屏普通 Freeme，先取 before，用户用自然速度双击一次，触摸时钟可见控件，再取 after。正式请求及投递各恰好加一、应用取得焦点、实际 LOCKED、flags=80、仅时钟获准、触摸正常。 |
| 多轮 | 确认开发退出，Freeme 保持 NONE，重复三轮，每次使用不同文件。已 LOCKED 时重复双击应无新增返回请求。 |
| 负向 | 普通用户可见的通知面板、控制中心、输入法或 USB/权限弹窗逐项观察，保持原界面，正式投递不增加。系统认证、紧急入口和恢复界面保持受保护；只观察入口，不拨号或执行恢复。 |
| 暂停与退出 | 维护暂停、已排队请求、恢复后新手势、开发退出取消与确认走既有流程。检查原电源键单击与长按菜单。任何异常先停测。 |

```powershell
py -3 .\cpday10_daily.py snapshot --serial $s --out freeme01-before.json
# 经批准后，用户完成一次实体双击；触摸确认后再取样
py -3 .\cpday10_daily.py snapshot --serial $s --out freeme01-after.json
py -3 .\cpday10_daily.py assess freeme01-before.json freeme01-after.json --expect return --touch-confirmed
```

正向 after 中的 last_window_check 可按 delivered 序号和时间核对。负向看最新 veto 的时间、原因和阻断行。设备检查未执行时不要记录为真机通过。

## 停用、卸载和回滚

- **停用**。在 KernelSU 的本模块用 Action 关闭监听，或在管理器禁用模块。确认 armed 和实际进程数，普通 Android 仍可使用。保留时钟图标和原开发退出。
- **回到 1.0.1**。停止监听，记录现场 timing-status 和现有备份；需要还原系统计时时通过已批准的 timing-restore 恢复备份的原值并核对。用上一版固定下载提交的 ZIP 恢复 1.0.1，保持关闭，按批准的管理器流程完成并核对零监听、原桌面、Owner 和原设置。1.0.1 ZIP 的 SHA-256 为 `64f18d6e4190d75a2ec01399316252551c4fa609da646efdf3c8eb2999dc6335`。[1.0.1 固定下载](https://raw.githubusercontent.com/shfjq/naozho/4b3b507870aacd9645bec679b34cd07462529e8b/downloads/P0-9.7.1/naozho-power-daily-1.0.1.zip)
- **完整卸载**。按上项恢复计时后仅移除 naozho_power_daily。若卸载时设置服务不可用、设备上仍是模块目标值，用同一设备原备份执行 recover-timing --serial $s --backup <原备份文件>，检查原值。发现第三方改动时由工具停止，先核对来源。时钟、naozho_boot、Owner 和 SELinux 沿用原配置。
- **无法从界面操作**。使用设备既有 KernelSU 模块安全模式；已有授权 ADB 时可仅设置本模块的 disable 标志，恢复界面后再核对计时备份和零监听。无需恢复出厂、重刷系统或清理时钟数据。
