# CPDAY10 P0-9.5 联调与恢复手册

**当前为审查包。批准之前只在电脑上核对下载文件。** 手机当前为 NONE + Freeme、0.6.9-dev/24。P0-9.4 已经用手指完成 Inventory 和 Observe，本轮直接从 APK 升级开始。沿用现有 Device Owner、naozho_boot、ADB-Enabler 和原桌面。以下机上步骤仅供批准后执行。

## 电脑端与基线

从同一固定提交获取完整套件与外部 SHA256SUMS.txt。用 Get-FileHash 核对套件 ZIP，解压到新目录后在 PowerShell 中运行下列命令。要求 Windows 的 Python 3.8+、可用的 adb 和原先获授权的本地维护连接。每一步单独执行，看到 STOP、失败或不符时保留输出并停止。本地基线和 .attempt 文件不要公开。

~~~powershell
Get-FileHash .\CPDAY10-P0-9.5-kit.zip -Algorithm SHA256
# 解压后在套件目录执行
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $h,$f = $_ -split '  ',2
    if ((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash -ne $h) { throw "文件校验失败 $f" }
}
adb devices
$s = '替换为本机实际连接标识'
py -3 .\cpday10_joint.py before --serial $s
~~~

before 核对 user 0、设备型号、系统版本、已安装 24 原 APK 的字节哈希、Device Owner、NONE/Freeme、原版不含接收器，并把应用 UID 和指定部署字段保存在电脑。脚本读的是本应用少数模式配置项。若旧 APK 来自不同构建且哈希不符，先核对来源。

## 覆盖升级并验收 Receiver

~~~powershell
adb -s $s install -r .\naozho-0.6.13-dev-power-return.apk
py -3 .\cpday10_joint.py verify --serial $s
~~~

安装须为 Success，核验须得到 APK_OK。verify 对比应用 UID、Device Owner、managed_lock、managed_home、native_home 及新 APK 实际 SHA-256，并通过 PackageManager 的显式查询检查 user 0 的接收器名称、启用、导出和发送者权限。此阶段不会发任何广播。若需额外核对应用数据，记录升级前后维护页上的已有闹铃数及所选原桌面，只比对本机结果。

0.6.9 的旧配置可能没有 mode_since。通过正常桌面图标进入时钟，然后用现有「开发退出」确认返回 Freeme 一次，为 0.6.13 建立时序基线。此时应是专机已启用、当前处于 Android 模式、NONE、亮屏 Freeme。若原先处于维护暂停，先由维护人员决定是否明确恢复独立专机，再按上述步骤正常退出。

## 安装模块，最后只做一次 Return

1. 用已有 KernelSU 管理器安装 naozho-power-trial-0.2.0.zip。核对 ID 为 naozho_power_trial，版本 0.2.0，不点 Action，不运行旧版脚本。若管理器要求重启，按批准的维护窗口操作；无线 ADB 地址变化时更新 $s，脚本优先用本地保存的设备标识摘要匹配基线。原开机模块可能自动进入时钟，再用正常开发退出回到 Freeme。
2. 回到 Freeme 主屏，避免这次手势期间切桌面或接入其它显示器。运行下方命令。程序先用模块自己的 /system/bin/am 向同一个有权限保护的 Receiver 发一次无手势数据的诊断广播。成功应为 permission_probe=DELIVERED，带实际 Android 记录的 uid 和 user=0。未证明系统投递时程序就停止，不按电源键、不授权新权限。
3. **只在看到 ready=return_once 后**，按上轮已通过的节奏做一次亮屏物理双击。继续观察 return_receiver=DELIVERED、发送 UID 与探测一致、result 和读取到的窗口/Lock Task 状态。无需手动发广播、命令拉起时钟或重复触发。
4. SOFTWARE_CHAIN_OK 表示本窗口内恰有一次有效应用返回、一次焦点提交和一次 LOCKED + 80 读回（允许名单仅时钟）。DSH 用手指实际点开并返回一个本地界面、确认时钟可操作后，再签署真机通过。维护暂停、进程在途失去资格、重复请求由套件测试覆盖；如要在板上专项验证，另开审批，不混在这次正常样本中。

~~~powershell
py -3 .\cpday10_joint.py return --serial $s
~~~

同一基线旁的 p095-local.json.attempt 以独占方式创建，包括失败和超时，不会自动重发。保存控制台及该文件。探测的未知 action 会产生一次预期的 “Double rejected at receiver”，之后才应出现正式请求与焦点日志。分开记录权限未证实、实发被系统跳过、应用条件拒绝、未获焦点、未锁定及不可触摸；权限拒绝时也保留 Android 报告的阶段，不修改 SELinux 或接收器权限。

## 故障恢复

1. 正常试验会自行到期。需要中途停止时，在管理器停用 naozho_power_trial；已发出的返回请求可能已经到达。若已入锁，使用原「开发退出」并确认，读回 NONE + Freeme。
2. 在 KernelSU 管理器中只移除 naozho_power_trial；依管理器提示完成移除。其它模块、Device Owner 和 HOME 保持现有配置。若希望此后开机也停留 Android，按原有维护暂停机制操作，并单独记录这项主动修改。
3. 需要回退应用时使用随包的 0.6.9-rollback-dev/28，可同签名同 versionCode 替换 0.6.13，在基线上恢复旧版逻辑。请勿以原 versionCode 24 强行降级。若安装器拒绝，立即保留错误并停止；不卸载时钟，不清数据，不移除 Owner。

~~~powershell
adb -s $s install -r .\naozho-0.6.9-rollback-vc28.apk
py -3 .\cpday10_joint.py rollback --serial $s
~~~

回滚后确认 Owner、UID、原桌面与配置、NONE/Freeme、旧版接收器缺席、实际触摸正常。若本轮主动启用或暂停更改过专机开关，先用维护界面恢复为基线对应状态再比对。保留试验记录；再次执行 Return 需要新的测试安排。
