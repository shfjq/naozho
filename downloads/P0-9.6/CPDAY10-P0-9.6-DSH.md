# CPDAY10 P0-9.6 续测与回滚手册

**当前只审查文件。手机保留 0.6.13-dev / 28，上一轮正式 Return 为 0。以下设备步骤留待单独批准。** 使用 P0-9.6 新目录，保留 P0-9.5 目录及其 .attempt。桌面 Python 3.9+、ADB、JDK 和 Android SDK Build Tools 的 apksigner 需可用。

## 1　电脑离线检查

从同一固定 GitHub 提交下载 kit 和 SHA256SUMS.txt。在 PowerShell 中对 kit 运行以下命令，将结果与下载页的完整 SHA-256 比较，成功后解压。包内 CONTENTS-SHA256.txt 覆盖各独立交付物。

```powershell
Get-FileHash .\CPDAY10-P0-9.6-kit.zip -Algorithm SHA256
Expand-Archive .\CPDAY10-P0-9.6-kit.zip -DestinationPath .\P096
Set-Location .\P096
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $hash, $name = $_ -split '  ', 2
    if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash -ne $hash) { throw "校验失败 $name" }
}
```

## 2　审批后，建立已升级设备的新基线

将 $s 填为已授权的 ADB 连接，$old 填为原始 p095-local.json 的位置，其 .attempt 必须仍在同目录且同名前缀。工具自动寻找 apksigner；必要时在每条命令末尾加 `--apksigner '实际 SDK 路径\build-tools\35.0.0\apksigner.bat'`。

```powershell
$s = '填写 DSH 已授权的连接'
$old = '填写 P0-9.5 原目录\p095-local.json'
py -3 .\cpday10_joint.py resume --serial $s --previous-record $old
```

resume 只读手机，在电脑独占创建 p096-local.json。它核验已装 APK 全文件哈希、v2 签名、证书、版本和 Receiver 的 enabled/exported/STATUS_BAR_SERVICE，再核验 user 0 的 Owner、UID 10191、原桌面配置、独立锁定已启用、正常开发退出边界、NONE/Freeme、唤醒、Enforcing 和实际 boot_count。旧基线和失败记录以 SHA-256 关联，内容原样保留。若上一轮文件在档案机，可保留档案并省略 --previous-record。起点不同或任一项无法验证就停下核对。

## 3　获准安装模块后，只核验环境

通过现有 KernelSU Manager 安装已校验的 naozho-power-trial-0.2.1.zip。仅在本轮审批包含重启且 Manager 需要时正常重启。若自动进入时钟，沿用已验证的开发退出回到 NONE + Freeme，保持亮屏。保留 ADB-Enabler、naozho_boot 和 Owner。模块没有开机动作。模块管理器的 Action 是 Inventory，本轮无需点击。

```powershell
py -3 .\cpday10_joint.py verify --serial $s
```

verify 重新核验基线，允许批准重启后的 boot_count 改变，只读设备。此时仍未发送探测或正式广播。

## 4　仅在单次 Return 获批后

```powershell
py -3 .\cpday10_joint.py return --serial $s
```

工具核对已启用环境与模块版本 0.2.1 / 3，独占创建 p096-local.json.attempt。正常探测使用无手势数据的唯一 action。等到先显示 `permission_probe=DELIVERED`、再显示 `ready=return_once` 后才在亮屏 Freeme 用手指双击一次实体电源键；只出现探测回执时继续等待。到时仍未就绪或报 STOP，保留窗口和本轮 .attempt 即结束。不再开一次 Return。

判读次序如下。

1. probe 的 history_check 显示本轮 trace、user=0、component=clock_receiver、state=DELIVERED 和 sender_uid。出现 ready 才进入实体双击窗口。
2. 双击后有且仅有一条 stage=return 的 dispatch_attempt 和一条同 trace 的已验证历史。return_receiver 的实际发送 UID 等于探测 UID。
3. 工具确认应用仅请求一次、焦点提交一次、时钟窗口在前台、实际 LOCKED，并有本轮 flags=80 及仅时钟允许名单的应用读回日志。
4. DSH 实际触摸时钟并记录是否响应。只有一次软件链和触摸均通过才能签收。正常开发退出二次确认后，应回到 NONE + Freeme，Owner 保留。

## 5　故障判读与恢复

| .attempt 情况 | 含义与处置 |
| --- | --- |
| no_record、pending_or_frozen、summary_only | 该次快照尚无完整终态。查看随后各次 sample、elapsed_ms、source；均不完整则停止。 |
| matching_intent_outside_terminal_record、unparsed_related_record | 找到相关文字或独立 Intent，缺乏可归属的完整历史结构。保留当次记录。 |
| identifier_missing、no_matching_identifier、incomplete_receipt | 检查 matching_id、sender_uid、receiver_state 等缺项。10191 是应用 UID，不可填入发送 UID。 |
| delivery_denied_STATUS_BAR_SERVICE、delivery_SKIPPED、delivery_autostart_policy_blocked、wrong_user、wrong_component | 权限、终态或目标明确不符；按具体错误留档。 |
| read_failed、output_limit、system_command_timeout | 此次历史读取未完整取得。无法据此判定系统拒绝了探测。 |
| probe 已通过，正式请求读回失败 | 用 dispatch_attempt stage=return 的计数判定是否已尝试正式发送；先观察当前焦点和实际锁定，保留本轮记录，不重发。 |
| adb 中断或报告不完整 | 已发请求数量可能未知，不用空文件推定为 0。保留 .attempt，本轮结束。 |

若已进入时钟，通过现有开发退出确认回到 Freeme。在 KernelSU Manager 仅禁用或卸载 **naozho_power_trial**；按批准的维护流程处理所需重启。工具无后台常驻任务。在正常结束后复核 NONE/Freeme 和原 Owner。APK 继续使用 0.6.13-dev / 28，保留应用数据、原模块及系统配置。归档新旧两个目录，不删除 .attempt 来重复测试。
