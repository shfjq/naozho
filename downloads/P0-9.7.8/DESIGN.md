# CPDAY10 P0-9.7.8 · 独立唤醒观察器

**交付状态：已完成云端开发、编译、签名和离线测试。尚未在 CPDAY10 安装或运行。** 本原型回答一个问题：设备自然息屏再亮屏时，一个与时钟无关的进程，能否在普通待机和深度待机后都取得足够证据识别完整唤醒。

## 核对的基线

开发从 P0-9.7.7 报告提交 `47b2e87` 开始。报告 SHA-256 为 `4de2b5f56bca3065744202b3269386b3c1e9ea58edc906e0f2cd3fa0a7b9300c`。0.6.13-dev/28 已交付时钟 APK 归档哈希为 `8bcf50a524f58b6c8180d699f47a18fd096d94b7b12d737d1a60710d189597d4`，daily 1.0.4 模块归档为 `e854ac34e79723ded44de0a33ee576399b5beccce3d04d29fa63727a2cd09725`，两项均已复算。上轮记录的同版本 Gradle 中间交付差异沿用原报告，固定基线取已发布的 APK。

设备状态引用用户最近提供的记录：CPDAY10，API 36，MT6789，原时钟 UID 10191，Owner、SELinux Enforcing、KernelSU 3.3.1，计时 300 ms；daily 关闭，armed 不存在，listener_count=0；ADB-Enabler 和 naozho_boot 保留。本轮没有联网读取手机。没有重签时钟或改动上述模块。观察器使用独立包 `com.naozho.wakeprobe`，版本 0.1.0/1，min/target 36，使用独立诊断证书。

## 事件与权威电源状态

- 用户从观察器自己的可见 Activity 手动开启专用前台服务。Service 与诊断 Activity 同包，和时钟完全不同包／UID／进程。退出诊断页面不会注销 Service 的订阅。系统回收时钟进程也不直接移除该订阅。后者还须在同一手机上验证。
- 使用 API 36 的 `DisplayManager.registerDisplayListener(Executor, long, listener)` 明确选择 STATE、ADDED 和 REMOVED。处理默认显示器 ID 0，通过 `Display.getState()` 和 `PowerManager.isInteractive()` 取样。P0-9.7.7 已核对原厂 framework 的公开 STATE 位 16 到内部位 128、服务端事件 9 的链路。事件本身没有物理触发源，也不携带硬件沿的时间戳。
- 同版本原厂 `PowerManagerService$BinderService.dump` 先调用 `DumpUtils.checkDumpPermission`。已授权时，工作线程通过 API 36 的 `Debug.dumpService("power", fd, ...)` 对当前电源状态取一次只读快照，只解析默认组、wakefulness、转换标记和最近睡／醒 uptime。通过内存管道读取，上限 256 KiB，读取预算 950 ms；至多一个在途 Binder 读取。遇到卡住的系统调用，错过这次证明，后续也不会堆积读取线程。原始 dump 不落盘。
- 新的显示／交互状态记录一行，取证在后台完成。ON 通常等约 200 ms 再核对；若系统只是在转换，可有限复核一次（通常再等 400 ms）。复核前重新读取显示与交互情况。若仅交互标志晚到，保留已观察的显示边沿；若显示已发生未观察到的改变，记录 GAP 并从头建立基线。超过 3 秒的 ON 证据失效。没有在无事件时定时查状态，没有唤醒型定时器。
- `Display.getState()` 是默认逻辑内屏的实读值。两次一致的显示读数、PowerManager 和同周期电源历史是软件证据。面板实际发光及可交互性需要人工观察；本阶段不检验时钟焦点、触摸或 LOCKED，不访问窗口内容。

## 状态、去重与失效

~~~mermaid
stateDiagram-v2
    [*] --> Baseline
    Baseline --> DARK : 已见亮屏，观察到 OFF
    Baseline --> DOZE : 已见亮屏，观察到低功耗显示
    DARK --> DOZE : AOD 进入
    DOZE --> DOZE_SUSPEND : AOD 挂起
    DOZE_SUSPEND --> DOZE : AOD 恢复
    DOZE --> DARK : 脉冲结束
    DARK --> WAKING : 默认屏 ON
    DOZE --> WAKING : 默认屏 ON
    DOZE_SUSPEND --> WAKING : 默认屏 ON
    WAKING --> INTERACTIVE : 稳定 ON、interactive、Awake、有效睡醒历史
    WAKING --> DOZE : 短暂 ON 后又进入 AOD
    WAKING --> DARK : 尚未确认就熄屏
    WAKING --> REFUSED : 超时、证据缺失或历史冲突
    INTERACTIVE --> DARK : 下一次息屏
    INTERACTIVE --> DOZE : 新的低功耗周期
    REFUSED --> Baseline : 新观察基线
~~~

1. 初始 ON 或安装／重启观察器时已经 OFF 只提供基线。观察到 OFF 记一次 DARK；若 DOZE 是第一暗态，单列 AOD，不虚报 OFF。重复相同的显示和交互读数增加 duplicate_count。DOZE↔DOZE_SUSPEND↔OFF 不会自行生成完整唤醒。
2. 完整唤醒要求已观察到从先前 ON 进入暗期、默认屏回到 ON 且复读一致、`isInteractive=true`、唯一显示组 0、`mWakefulness=Awake`、`mWakefulnessChanging=false`。最近一次系统睡眠须处于先前亮屏基线和首个暗态观测之间，最近一次系统唤醒须晚于睡眠且落在最后暗态观测和核验之间。睡醒排序使用 uptime；进程存活、长待机与证据过期使用含深睡的 elapsedRealtime。系统的睡醒时间若与回调交错以致无法配对，这一轮记为未证实。
3. 只有 `FULL_WAKE` 产生新 ID：启动计数、随机观察会话 ID、该会话的递增序号。重复回调可引用同一个已确认 ID，但不会新增 ID。进程重建会生成新会话并丢弃半途的周期。DREAMING 即使 interactive=true 也不能通过。UNKNOWN、VR、ON_SUSPEND、默认显示器消失、缺少权限、多显示组或快照不完备均不能证明完整唤醒。
4. 总结方面，原始计数与产品结论分开。丢失的回调不能凭一张事后 ON 快照补成成功。手工做了三次自然唤醒而只有两次可确认时，报告分母仍是三次。新入口不引用时钟包、不发送广播、不设置策略；未来的返回决策、受保护投递、焦点和 Lock Task 验证均不在此 APK 内。

## 事件格式

UTF-8 JSON Lines，每条带 session 和 session_row。下表给出字段语义。行的 `callback_source` 指软件来源，实际“抬手／通知”等来源由测试员另记，避免猜测归因。

| 字段 | 含义 |
|---|---|
| boot_id、session、observer_pid | 系统 BOOT_COUNT 的署名形式 boot_count:N（读不到为 null），随机会话及 PID；不采集硬件标识 |
| wall_clock、elapsedRealtimeNanos、event_timestamp | UTC 写行时间、写行时的单调纳秒、原始回调／采样在观察端的 elapsed 纳秒。延迟核验保留触发该核验的时间；不是物理电源键／面板的硬件时间 |
| observation_uptime_ms、last_sleep_uptime_ms、last_wake_uptime_ms | 不含深睡的系统时间域；后两项只在取得有效电源快照时输出 |
| callback_source、display_id、old_display_state、new_display_state | 注册、默认显示回调、读取复核、人工检查点或服务生命周期，及观察到的前后状态；电源复核行自身不代表又发生一条显示边沿 |
| isInteractive、wakefulness、wakefulness_changing、power_status | 初始未知或未做同步读取时显式 UNKNOWN／not_sampled；随后通过同一 revision 的复核行关联。缺 DUMP 会记 dump_permission_absent |
| state、event_classification、aod_transition | DARK、DOZE、DOZE_SUSPEND、WAKING、INTERACTIVE 或 REFUSED；分类包括 AOD 进退、WAKING_REVERSED、FULL_WAKE、DUPLICATE、STALE_SAMPLE_DISCARDED、DISPLAY_CALLBACK_GAP 等 |
| wake_epoch_id、duplicate_count、duplicate_callback、revision | 各状态边界的修订号、最近相同读数的连续重复数；只数 FULL_WAKE 行作为成功次数 |
| battery_pct、device_idle、session_age_ms、process_cpu_ms、previous_unclean_sessions | 电池容量，系统设备空闲模式，服务经过时间，观察器进程累计 CPU，以及发现“上次有开始标志却没有正常收尾”的会话数。缺少的结束行本身不能证明崩溃原因 |

仅写应用私有的两份轮转日志，每份最多 256 KiB。分析工具按会话行号报告轮转或导出造成的缺行。诊断只处理默认内屏。需要归因时以人为记录的触发方式、目视反应和相邻时间关联，禁止以软件回调推断物理手势。

## 权限、存活与待机

| 能力 | 原因与限制 |
|---|---|
| FOREGROUND_SERVICE、FOREGROUND_SERVICE_SPECIAL_USE | 供用户手动启动、持续通知可停止的本地测试会话。普通广播或只在 Activity 注册不足以做长待机观察。采用 START_NOT_STICKY；系统杀掉观察器、用户强停、重启后不会自己重启或重放事件 |
| POST_NOTIFICATIONS | 确保观察中的通知／停用入口可见。应用在用户点击开始时申请；拒绝则界面不启动观察。测试期间请保留此诊断通知渠道 |
| DUMP | 系统级只读诊断权限，范围广于本程序实际读取的字段，普通界面无法授予。只有在审核允许后，才能单独向该诊断包授权并验证；没有授权也可观察显示回调，但不得判完整唤醒。若原厂拒绝，保留拒绝结果，不提升权限、不开 Root |
| 耗电边界 | 没有 WAKE_LOCK、网络、位置、传感器、输入设备、开机自启或闹钟权限。显示回调、受限采样与日志会消耗 CPU，不申请 WakeLock 不能证明零耗电。设备空闲模式和显示 DOZE 是两个不同指标，分别记载 |

状态监听的可靠性取决于观察器进程仍存活、系统实际送达回调、读数能与历史配对。只有在同一会话跨过待机、目视记录与周期数吻合时，才记“该样本通过”。根据信息不足明确报告漏检，避免用常驻前台服务的存在代替实际验收。官方接口可参阅 [DisplayManager](https://developer.android.com/reference/android/hardware/display/DisplayManager)、[PowerManager](https://developer.android.com/reference/android/os/PowerManager)、[Debug.dumpService](https://developer.android.com/reference/android/os/Debug#dumpService(java.lang.String,java.io.FileDescriptor,java.lang.String%5B%5D)) 及 [前台服务类型](https://developer.android.com/develop/background-work/services/fgs/service-types#special-use)。
