# CPDAY10 独立唤醒观察器 · DSH 验收单

**当前状态是待审核。以下操作仅供以后获批的真机试验使用。** 包名为 com.naozho.wakeprobe。安装不触碰时钟、KernelSU 模块或 Device Owner。诊断不会将屏幕切到时钟。APK、源码和测试结果可先在电脑审查。

## 核对与启动

1. 在电脑校验交付目录的 SHA256SUMS.txt。Windows 可用 `Get-FileHash .\cpday10-wake-observer-0.1.0.apk -Algorithm SHA256`。用 `apksigner verify --verbose --print-certs cpday10-wake-observer-0.1.0.apk` 核对诊断证书 SHA-256 `2618dfdd7a610abcad93e2d99164d7e1430ce468a9360186e3652a72e9a86c99`。
2. 确认仅连接目标 CPDAY10；多个设备时为每条 adb 命令显式指定序列号。核对用户 0、API 36、时钟 0.6.13-dev/28、UID 10191、原 Owner、Enforcing、300 ms、daily 关闭且无 armed/监听，保留 ADB-Enabler 和 naozho_boot。沿用已有只读基线核对流程，任何差异先记录并暂停。记录目标 APK 是否已安装，避免误覆盖。设备测试记录保存在本机。
3. 审核批准后，安装**独立包**。完整电源证据还需单独批准向这个包授予 DUMP。两步可分开；未授予时可以先做“回调存在、完整唤醒数为 0”的负向用例。使用 Windows 命令提示符：

   ~~~bat
   adb install cpday10-wake-observer-0.1.0.apk
   adb shell pm grant --user 0 com.naozho.wakeprobe android.permission.DUMP
   ~~~

   任一步失败，保留错误原文并停在该步。无需更改系统设置。若已开始未授权会话，完成该用例后先正常停止，再开新会话。
4. 用户从图标打开“唤醒观察器”，点“开始观察”，允许显示通知。点“刷新状态”，确认电源状态读取已授权、持续通知可见。点击“记录检查点”，退出该页面回 Freeme。初始亮屏只建立基线。记录开始时刻、起始电量、会话/PID。等待自然产生新的息屏与唤醒。

## 每轮如何判定

为每次人为动作记录一行；即使没有观察器日志也保留该行。表格样例中留空处代表尚未采集。

| 场景与操作 | 待填写的实测证据 | 预期 |
|---|---|---|
| Freeme，短按电源键息屏，等待 10 秒再自然点亮；重复 3 轮 | 动作起止、目视 OFF/亮、回调数、epoch、重复数、前后台 | 每个完整周期各有一个 FULL_WAKE；普通系统界面仍可使用 |
| 抬手 | 开关／硬件可用性、目视结果、显示/电源状态、epoch | 实际自然完整唤醒才计 1；设备无此能力记未测试 |
| 双击屏幕（与双击电源键不同） | 真实息屏后双击；记录是否只呈现 AOD | 完整醒来计 1；单纯脉冲计 0 |
| 通知触发 AOD | 使用已允许的另一台设备／正常通知，默认内屏是否只短暂显示 | DOZE／DOZE_SUSPEND 及退出可见；FULL_WAKE 为 0。不主动配置或启用 AOD 伪造样本 |
| 通知完整亮屏 | 选择已知会自然点亮的普通通知，记录消息到达的时间和目视结果，不记录正文 | 若完整醒来则 1，普通通知未点亮不认作失败 |
| 闹钟唤醒 | 使用已存在的测试闹铃或另行批准的系统闹铃；用户正常处理响铃 | 独立观察器记录是否完整醒来。响铃 UI 可继续操作，不会启动时钟首页或改变锁定 |
| 长待机自然唤醒 | 30 分钟及 8 小时分别进行；记录自然唤醒方式、会话与 PID | 息屏行和醒来行可配对，FULL_WAKE 1，同一会话、无额外主动亮屏 |

逐行记录 `前状态 → 后状态 / 物理触发方式 / 显示回调是否到达 / FULL_WAKE 的 epoch 数 / 重复回调数 / 目视分类一致性 / 备注`。不安全或不能复现的来源写“未测试”；设备已知不支持时注明依据。区分“无回调”“回调失序／证据不足”“收到并拒绝”“正常 AOD”“完整唤醒”。重复回调允许出现；同一物理周期两个 FULL_WAKE 判失败。

## 后台和待机

- **诊断页面退后台**后执行短测。另在受控条件下确认时钟进程退后台或已被正常回收。可在事件前后只读运行 `adb shell pidof com.naozho.clock` 与 `adb shell pidof com.naozho.wakeprobe`。要证明“时钟被杀后仍工作”，须记录先有时钟 PID、后来消失的证据和其后完整暗→亮；开始时就未运行只记“时钟不在运行时观察成功”。无法安全制造普通回收时记待测，不停止或卸载 Owner 应用。诊断服务如被杀，记录会话断点，手动重启形成新会话，不能跨会话拼接。
- **短测**先核对 3 轮正常息屏/唤醒、一轮只息屏和有条件时一轮 AOD。每种场景前后点一次检查点（亮屏后再做，避免改变测试）。首例无法读出 power 或缺少完整睡/醒对就停在取证，不通过重复制造事件掩盖问题。
- **30 分钟**在同一会话自然待机，断开 USB 供电或保持各组同样供电条件，不强制 Doze、不持续 logcat、不定时查询设备。观察屏幕变暗及自然唤醒时间，结束后记电量／PID／日志。DeviceIdle 若从未观测到，不能标记“已验证系统深度 Doze”。
- **8 小时**单独排期。相同起始电量区间、室温、无线设置、通知负载、息屏时长和供电，交替记录诊断关闭／开启，至少两对夜间样本，分开报告短测和夜测。关闭组用系统读数和人工时刻，不为测量启动观察器。开启组分析开始／结束电量、百分比点／小时、进程 CPU 时间差、经过时间、异常结束、日志总字节、实际物理唤醒数。系统若能提供可靠的唤醒归因，再记录对应次数；无法归因写 unknown。回调数、CPU 时间、电量下降均不能替代 CPU 唤醒次数。若设备明显异常发热、意外亮屏或持续耗电，结束试验并软停。
- 每组结束后先记录检查点，再“停止观察”（或点通知中的停止）。不要根据一次起始电量或一次未变化的整数百分比判定功耗通过。

## 取出诊断记录

已停止后，在 Windows **cmd.exe** 中执行；不从 PowerShell 5 的文本重定向生成 JSONL。先列目录，previous 文件只在发生轮转时存在。

~~~bat
adb shell run-as com.naozho.wakeprobe ls -l files
adb exec-out run-as com.naozho.wakeprobe cat files/wake.jsonl > wake.jsonl
python summarize.py wake.jsonl > result.json
~~~

若目录有 previous：

~~~bat
adb exec-out run-as com.naozho.wakeprobe cat files/wake.previous.jsonl > wake.previous.jsonl
python summarize.py wake.previous.jsonl wake.jsonl > result.json
~~~

汇总中的 session_age 是观察服务已经过的时间，CPU delta 是读到的区间；开始／结束行缺失或中途轮转须如实标注。previous_unclean_sessions 表示有会话未干净结束，原因可能是进程死亡、系统强停或故障，不能自动断言为崩溃。需要判断时结合设备历史退出原因和 PID。日志缺行数与系统未投递回调是两类不同证据。完整手机日志不需要公开。

## 退出与撤回

先点“停止观察”，确认通知消失、服务注销并导出所需记录。服务停止后进程可被 Android 缓存，出现 PID 不能单独判为仍在监听。必要时在已批准的撤回操作中使用：

~~~bat
adb shell pm revoke --user 0 com.naozho.wakeprobe android.permission.DUMP
adb uninstall com.naozho.wakeprobe
~~~

卸载会删除**诊断包自己的日志**。原时钟、Owner、daily 和开机模块不在这些命令的目标中。结束时复核原基线。本轮不安排安装、授权或真机操作。
