# CPDAY10 日常电源双击 1.0.0 部署与验收

**当前只做电脑端审查。以下设备操作留待批准。** 手机继续使用已验收的 0.6.13-dev / 28、原 Owner、naozho_boot 和 ADB-Enabler。P0-9.6 的试验模块已卸载，无需运行 Inventory、Observe 或 Return。

## 电脑端

下载同一固定提交的 kit 和 SHA256SUMS.txt。对 kit 使用 Get-FileHash，与固定提交公布的 SHA-256 比较。解压到新目录，在该目录执行以下 PowerShell 校验。

```powershell
Get-Content .\CONTENTS-SHA256.txt | ForEach-Object {
    $hash,$name = $_ -split '  ',2
    if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash -ne $hash) { throw "校验失败 $name" }
}
py -3 .\cpday10_daily.py --help
```

压缩包内的 cpday10_daily.py 可独立运行，要求 Python 3.9+。手机侧日常使用不需要 Python 或 ADB。源码构建说明及权限范围见技术报告。

## 获准后安装和启用

1. 使用已有无线 ADB 连接。将下面的 $s 填为已授权连接。preflight 只读已装 APK，核验精确哈希、签名、版本、Receiver、UID 和 Owner。apksigner 位于 Android SDK Build Tools，必要时用 --apksigner 指定路径。
2. stage 仅把已校验模块复制到手机 Downloads 并回读哈希。由 DSH 在 KernelSU Manager 中选择该 ZIP 安装；仅在批准的维护窗口按管理器提示重启。
3. 新安装默认关闭。先采一份未启用快照，确认进程数为 0。进入正常 Android 模式后，在本模块点击一次 **Action** 明确启用，再回到 Freeme，待状态出现 listening、进程数为 1。开机脚本只启动监听，不发送广播。重启后首次合格手势需要重新证明发送权限；若证明耗时超过时效，丢弃这次手势并保留记录。之后电脑可以断开，日常从合格的亮屏界面双击实体电源键即可。重复点击 Action 会切换开关。
4. 状态为 disabled_、启动后找不到进程或有多个进程时，停止验收，保留快照并按下方恢复。安装器、脚本和工具均不配置 Owner、HOME 或应用锁定。

```powershell
$s = '填写已授权 ADB 连接'
py -3 .\cpday10_daily.py preflight --serial $s
py -3 .\cpday10_daily.py stage --serial $s
py -3 .\cpday10_daily.py snapshot --serial $s --out installed-off.json
```

## 支持的前台与第三方页面

内置范围为 Freeme 主桌面、直接从普通入口打开的系统设置首页，以及经过源码核对并固定 APK 哈希的 OpenCalc 3.2.1 计算主页。测试可使用已装并审查的普通应用。OpenCalc 参考构建为作者发布的 com.darkempire78.opencalculator / versionCode 54，完整 SHA-256 在技术报告中；采用不同签名或分包的商店版本会被拒绝。模块不安装任何第三方应用。

同一 Activity 可以同时显示普通页面和认证、付款、恢复页面。通用 SubSettings、混合用途页面和未知弹窗都按不可确认处理。其他单一用途应用可由 Codex 提供经审查的页面清单，每行绑定一个完整组件及该 APK 的 SHA-256。DSH 无需编辑程序。在批准后用 inspect-page 读取选定普通应用的组件及哈希交回审查，随后在本模块已停用、监听进程为 0 时使用 profile 装入审查文件，再明确启用。profile 替换整个附加清单；空文件清空附加项。当前清单机制支持完整的单 APK 构建。

```powershell
py -3 .\cpday10_daily.py inspect-page --serial $s
py -3 .\cpday10_daily.py profile --serial $s --review .\reviewed-pages.txt
```

## 每次手势的验收方法

**成功一轮需要同时看到**：唯一监听进程、一次正式尝试和终态回执、该时段唯一的应用请求/焦点提交/锁定读回、系统焦点在时钟、Lock Task=LOCKED、user 0 名单只有 com.naozho.clock、策略 flags=80，以及 DSH 实际触摸有效。就绪后在测试页保存 before，断开电脑也可完成实体手势；在 after 前只触摸时钟内不会退出的控件。不要用 ADB 启动 Activity、合成按键或发送广播。

```powershell
py -3 .\cpday10_daily.py snapshot --serial $s --out freeme01-before.json
# 用户手指双击；看到时钟后实际触摸，确认有响应
py -3 .\cpday10_daily.py snapshot --serial $s --out freeme01-after.json
py -3 .\cpday10_daily.py assess freeme01-before.json freeme01-after.json --expect return --touch-confirmed
```

每次另取一对文件，工具拒绝覆盖。保留设备时钟设置，避免比较区间内调整系统时间。单击、长按、暂停和特殊界面用 --expect no-return，另行肉眼核对原有单击亮灭、菜单和原页面触控。若手机锁屏，不为采样解锁或抢焦；可在完成原有操作、回到起点后留存结果及人工说明。

| 项目 | 操作与预期 |
| --- | --- |
| 多轮日常返回 | Freeme 连续完成三轮，每次经开发退出确认进入 NONE 后正常停留。从设置首页、经审查的普通应用各重复两轮。用不同文件记录每轮结果。 |
| 正常电源操作 | 分别单击熄屏、单击唤醒、长按看到原电源菜单后取消。检查双击过程中跨过息屏或唤醒时放弃该次请求。 |
| 维护暂停与恢复 | 通过应用原有维护入口主动暂停，回到 Freeme 后双击应为零正式投递。重启后验证暂停仍有效；明确恢复独立专机，正常退出后用新手势验收。 |
| 已锁定 | 在 LOCKED 时双击与单击熄屏再亮，时钟仍可触摸，正式请求计数不增加。取消开发退出应继续锁定，确认退出应能正常停留 Freeme。 |
| 系统特殊界面 | 在系统凭据、展开的系统面板、紧急拨号入口及故障恢复提示出现时保持原界面。只检查紧急入口可用，绝不拨打实际电话。涉及系统恢复操作时只观察入口。 |
| 热重启、完整关机再开 | 各一次。保存新的 boot_count 后，在本次开机内重新建立 before/after。先核对只有一个进程，再正常退出时钟到普通 Android；断开电脑后用实体双击返回。不把 naozho_boot 的自动拉起记作双击成功。 |
| 其他能力 | 复核正常开关机、充电和电池温度读数、Wi-Fi/蓝牙连接、Owner 保留及正常开发退出。 |
| 停用与卸载 | Action 再次点击，确认实际进程数为 0；在亮屏 Freeme 双击不会拉起。明确启用后再验证管理器禁用和卸载，两种情况下都检查进程消失。 |

若屏幕切到未预期页面、紧急入口受干扰、正式尝试计数增加但回执缺失，立即停止该场景，保留状态，禁用本模块。不能通过反复双击替代故障定位。

## 耗电和长期运行

对照使用相同的网络、蓝牙、温度、亮度、后台应用、充电状态和放置方式。关闭本模块测一次基线，启用后按同条件测一次；两组都保留原开机模块。各观察一个完整夜间，建议各 8 小时，随后做至少 24 小时启用观察。每段采起止两份 snapshot，中途断开 ADB、保持真正息屏。多轮取样比较自然波动，单次电量百分比仅供参考。短时压力测试可在同一进程下做若干双击往返，查看 RSS、线程和 FD 是否持续增长。

```powershell
py -3 .\cpday10_daily.py consumption off-start.json off-end.json
py -3 .\cpday10_daily.py consumption on-start.json on-end.json
```

CPU 使用进程累计 ticks 算区间均值；时钟频率不可读时保留原始 ticks。RSS 单位 KiB。系统 wakeup_count 属于全机，不能直接计作本模块唤醒次数；节点不可读会标为 null。比较电量、可用的电荷计数、温度及充电标志。不同开机不直接相减。留意多进程、FD 或 RSS 持续增长、周期性唤醒、息屏掉电差异和日志超限，记录实测值后再决定是否长期启用。

## 停用及回滚

- **停用手势**：在本模块点击 Action 关闭，或在 KernelSU Manager 禁用此模块。进程监听本模块的撤销标记，空闲时也会停止。snapshot 中 listener_count 应为 0；旧的 status 文件只反映上次运行。管理器重新启用后，如需重新启动，可按管理器要求正常重启并复核 armed 与进程数。
- **暂停整个专机**：使用时钟自身的维护暂停，保留用户主动退出和恢复入口。模块即使仍在监听也不能据此返回。停用前已经提交的系统广播不能撤回；应用会在接收、进入和焦点消费时复核维护状态。
- **清除日常适配**：从时钟正常开发退出，确认 NONE/Freeme，在管理器仅移除 naozho_power_daily，按批准流程正常重启。检查进程数为 0、Owner 保留、原模块仍在、时钟图标仍能正常进入。卸载删除模块私有配置和轮转日志。
- **无法使用界面时**：若现有已授权 ADB 仍可用，可由 DSH 执行下列仅针对本模块的停用操作。保留正常电源菜单与原厂恢复能力；若 ADB 也不可用，采用该设备既有、经验证的 KernelSU 模块安全模式恢复流程。无需重装 APK、恢复出厂或更改 SELinux。

```powershell
adb -s $s shell "su -c 'touch /data/adb/modules/naozho_power_daily/disable'"
```

开机动画结束后的第一帧单独验收。本手册的日常双击、重启后监听或原开机模块恢复均不能证明第一帧已是可交互时钟。
