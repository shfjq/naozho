# P0-9.7.8.1 · WakeObserver 真机部署前权限审查

**审查意见：这个固定版本适合分两步做诊断。先在未授予 DUMP 的条件下验证显示回调；确实需要确认完整唤醒时，再经单独批准，向用户 0 的诊断包临时授予 DUMP。** 权限和代码审查通过。CPDAY10 的实际授予、撤销、唤醒和长待机仍待验证。本轮仅在云端审查；没有执行 ADB、安装、授权或修改设备。

## 1. 权限定义、获得途径与厂商边界

| 问题 | 证据和结论 |
|---|---|
| Android 16 的 DUMP 是什么级别？ | 从 CPDAY10 固件取证 ZIP 的二进制 AndroidManifest.xml 解出 `android.permission.DUMP`，原始行 4226，`protectionLevel=0x00000032`。API 36 官方 SDK android.jar 的平台 Manifest 给出同一数值。PermissionInfo 常量解码为基础级别 **signature** (0x02)，加 **privileged** (0x10) 与 **development** (0x20)。三个值描述不同授予路径。 |
| 普通 APK 能否申请？ | 可以在 Manifest 使用 uses-permission 声明。侧载本身不会因此自动获得，Android 的普通运行时授权弹窗也不能授予 DUMP。观察器界面唯一的运行时申请是 POST_NOTIFICATIONS。 |
| ADB shell 能否授予？ | **权限类别与这份原厂授权实现均支持命名的 development 授权和撤销。** 已授权调试连接上的 Shell 还须通过授予方权限、用户、包及策略检查。原厂代码有标准命令路径；本轮没有读取真机当前 Shell 的有效授权或执行命令，因此这台手机上的最终结果为待测。 |
| 需要平台签名、priv-app、Root、Device Owner 吗？ | 利用合法 development 授权路径时，接收授权的已安装 APK 无需这些身份。平台签名或符合系统特权应用授予条件是其他途径。此包有独立调试证书。debuggable 方便授权调试主机取私有日志，本身不授予 DUMP；时钟的 Device Owner 身份也不会转给此包。 |
| 范围与期限？ | DUMP 是系统诊断服务可检查的宽权限，没有按“仅 power 的五个字段”授权的开关。具体服务仍能做额外检查。授权附在应用身份上，退出页面、停服务、断开 ADB 均不能当作撤权；需要显式撤销并验证，或卸载独立诊断包。 |
| 有没有厂商限制？ | 同型号权限定义、包管理器与电源服务已核实，未见这些已查路径有专门针对本诊断包的禁止。现有材料没有证明当时的 Shell 权限、用户限制、授权标志或 OEM 调试策略必然放行。Atlas 拦截其他应用开机广播的既有记录也不能用来断定这里会拒绝。若正常授权被拒，保留错误，改用下文 A/B。 |

**固件依据。** 设备取证包 SHA-256 为 `0c190b7c33c5fb2a63e0cac2567a80d2760c3c33f98a4e8a3b6172cd242a1950`。其中平台 Manifest 为 386,048 B，SHA-256 为 `a63550d1d4f8253d06bf9a4877905c120b8cab0be7757fa3ae882f9bb4a20887`；本次用于 aapt2 的本地容器中，该成员逐字节相同。原厂 framework-res.apk 的整包哈希 `48a3f6912392d1d5fb066be715c3e0f888d9016011cdc9cf50b2609a2c040d02` 来自采集元数据。本轮复算了成员，未将资源切片容器当作完整原厂 APK。另复算同版本 framework.jar（SHA-256 `2d3548851e2217616cdbb42083b2785c3f230e09d4f05ca009dd4a4c01a3d14d`）和 services.jar（`70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468`），核对以下方法，@ 为方法内 DEX 指令偏移。

- `services/classes2.dex PackageManagerShellCommand.runGrantRevokePermission` 解析 `--user`、包和权限名，@00b2/@00d2 调用 grant/revokeRuntimePermission。这里的 API 名称包含 runtime，系统实际也识别 development。
- `PermissionManagerService` 转发给权限后端。固件内的 `access.permission.PermissionService.setRuntimePermissionGranted` 外层 @0042–0049 强制检查调用方的 GRANT_RUNTIME_PERMISSIONS 或 REVOKE_RUNTIME_PERMISSIONS，并处理跨用户及目标包；内部 @0041–0050 检查 protection flag 0x20，满足时跳过“不可变更类型”的拒绝分支，随后检查目标请求和固定策略等条件。固件中的旧后端 `PermissionManagerServiceImpl.grantRuntimePermissionInternal` 与撤销路径也有 `Permission.isDevelopment()` 分支。探针本身不申请授予方权限。
- `framework/classes3.dex Debug.dumpService` @0000 查固定名称的 Binder，@0020 调 IBinder.dump。`services/classes2.dex PowerManagerService$BinderService.dump` @0008 在读取前检查 `DumpUtils.checkDumpPermission`。该工具在 `framework/classes5.dex` @0000–0002 用 DUMP 检查 Binder 调用者。缺权限时可以向输出写拒绝文本；单凭 dumpService 的布尔返回值不能判定拿到了权威字段。从电源服务这个入口未发现额外的 PACKAGE_USAGE_STATS 前置检查。
- 开发权限用于显式调试授权。Android 官方将 DUMP 定位为系统诊断权限，并说明普通第三方应用不宜普遍持有。本次建议限时仅用于这一固定诊断包。[Manifest.permission.DUMP](https://developer.android.com/reference/android/Manifest.permission#DUMP) · [PermissionInfo](https://developer.android.com/reference/android/content/pm/PermissionInfo) · [ADB 包管理命令](https://developer.android.com/tools/adb#pm)

## 2. 已交付 APK 的全部权限与入口

以固定下载提交 `add3fe1d7309a1632cede19b4b821d8c4bd080ce` 的字节为准。包名 `com.naozho.wakeprobe`，0.1.0 / versionCode 1，min/target/compile SDK 36，33,195 B。APK SHA-256 为 `68712d6a3e68d1b7306984b92d6ed89dffdc0bf891d5e32cd6db997ae7a095e5`，classes.dex 为 `f2c725793ee6558d7d2c42dd4486f7bb178d5b2b7c89ac7a274c4e27799963e3`。ZIP CRC 和 v3 签名均已复验，一个签名者。证书 SHA-256 为 `2618dfdd7a610abcad93e2d99164d7e1430ce468a9360186e3652a72e9a86c99`。源码基线 `c77c54e51390f2b6d1e2162326e675cebf97a0e6` 与已发布源码包的 15 个源文件、测试及文档逐字节相符。

| 最终 uses-permission | CPDAY10 平台保护值 | 实际用途与必要性 |
|---|---|---|
| FOREGROUND_SERVICE | 0x1000，normal + instant | 用户从可见页面主动启动可停止的前台服务；用于页面退后台后的长期观察。 |
| FOREGROUND_SERVICE_SPECIAL_USE | 0x1040，normal + appop + instant | 与 Manifest 的 specialUse 类型、说明属性和实际 startForeground 类型相符。运行仍受系统 FGS/AppOps 与 OEM 管理。 |
| POST_NOTIFICATIONS | 0x1001，dangerous + instant | 用户点击开始才申请，让诊断持续通知与停止入口可见。Android 平台允许在没有此授权的某些情况下启动 FGS；此版本主动要求它，拒绝即不开始。授权后还要核对实际渠道和通知是否可见。 |
| DUMP | 0x32，signature + privileged + development | 只在授权时进入电源快照读取。**只观察显示边沿可以省去授予，现版独立确认 FULL_WAKE 需要它。** |

**组件清点。** 最终 Manifest 有一个导出的 `.Control`（MAIN + LAUNCHER），可被打开的是控制界面。其 onCreate/onResume 创建按钮或刷新状态，未读取外部 Intent extras 来启动观察。唯一 Service `.Observer` 为 exported=false，onBind 返回 null；通知里的停止按钮使用指向该 Service 的不可变 PendingIntent。Receiver、Provider、activity-alias 各为 0。没有 HOME、BOOT_COMPLETED、全屏通知或开机自启入口。应用 debuggable=true，allowBackup=false；已经获准的调试主机可通过 run-as 读应用私有文件，适用范围是本地诊断。

## 3. DUMP 的完整使用点与数据边界

| 源码位置 | 在发布 DEX 中核对的行为 |
|---|---|
| `Control.java:53` | `refresh` 调用 checkSelfPermission(DUMP)，只显示当前授权状态。 |
| `Observer.java:30, 108, 115–118` | `dumpAllowed` 再检查进程权限。显示注册或状态变化后，串行调度工作线程；有权才调用 PowerRead.read，无权生成 dump_permission_absent。 |
| `PowerRead.java:19–57` | 此包**唯一实际 DUMP 调用点**位于第 30 行，D8 生成的 `PowerRead.lambda$read$0…` @0004 载入常量 `power`，@000c 调 `Debug.dumpService("power", fd, new String[0])`。名称和参数均不取自界面、文件、外部 Intent 或网络。 |
| `PowerEvidence.java:32–44` | 从文本只提取 displayGroupId、mWakefulness、mWakefulnessChanging、mLastSleepTime、mLastWakeTime。要求唯一默认组 0、可识别的状态和可解析的数值。关键字段缺失等情况产生 unknown。 |
| `Observer.java:124–155`，`WakeCycle.java:88–120` | 回读默认内屏和交互态，验证修订号、事件时效及睡醒时间是否对应。只有已有真实暗期、内屏 ON、interactive、Awake、转换结束且证据配对，才记 FULL_WAKE 和对应 epoch。Dreaming 不能通过。 |
| `Journal.java:20–67` | 写入私有 wake.jsonl／wake.previous.jsonl。保存筛选后的状态、睡醒 uptime、显示回调、相对和墙钟时间、会话/PID、启动计数、电量、进程 CPU、设备空闲及未正常结束统计。每份最高 256 KiB。私有 sessions 偏好只保留会话状态。 |

**超出判定所需的读取确实存在。** 空参数让电源服务产生常规整份 dump。它还可能含电池／供电状态、已持有的 Wake Lock 标签、Suspend Blocker 和其他服务诊断信息；这些内容在观察器内存里先经过有界缓冲、再转换成字符串。应用只解析上表字段，未发现将原始 dump 写文件、写日志或上传的路径。读端接受上限为 256 KiB，等待预算约 950 ms；超限或超时即拒绝。该预算不能强行结束已在系统中执行的 Binder 工作。初始基线、部分暗态也可能触发取样，读取并不限于最后确认 ON 的那个瞬间。因此该授权只适合已审查测试会话。若后续要减少接触面，可先评估仅在候选阶段取权威快照，并在读取过程中筛字段；本轮没有修改实现。

**公开 API 可覆盖的部分。** 显示事件和 OFF/DOZE/ON 取自 DisplayManager/Display；交互布尔值、设备 idle 取自 PowerManager；电量、进程 CPU、boot count 各有只读接口。这些均不依赖 DUMP。已核对 API 36 的公开接口，未发现普通应用可以取得上述同组、同周期的精确 wakefulness、转换标记以及最近睡／醒 uptime 的等价组合。DREAMING 时 interactive 也可能为真。

## 4. 系统调用与不必要权限检查

对最终 APK 解包，只有一个 classes.dex，无 `.so`、脚本资产或额外 DEX。反汇编清点 15 个类（含 D8 产生的 lambda）及实际 invoke 目标，复跑最终 APK 检查。下列结果针对该固定哈希。

| 检查项 | 结论 |
|---|---|
| 网络、上传和外部存储 | 没有 INTERNET、网络状态、媒体或共享存储权限；未见网络库、socket、上传、外部文件路径、内容提供器或分享调用。应用写自己的文件和 SharedPreferences 无需存储权限。获准后导出到电脑会产生另一份需独立管理的日志。 |
| 系统设置与策略 | Settings.Global 只有对 BOOT_COUNT 的 getInt；putInt/putBoolean 出现在本包的 SharedPreferences.Editor。没有写系统计时、亮度、HOME、Owner、Lock Task、SELinux 或系统文件的调用。 |
| 输入、启动与 Return | 没有读取输入节点、ioctl/EVIOCGRAB、uinput、注入、执行 shell、动态加载、更改焦点、startActivity、广播 Return 或启动原时钟的路径。后台 Activity 启动权限、通知全屏 Intent 权限均未声明。startForegroundService 指向自己的 Observer。 |
| 唤醒锁与轮询 | 没有 WAKE_LOCK 声明，无 newWakeLock/acquire、主动点亮、AlarmManager 或定时作业。DisplayListener 事件触发取样，必要时延迟一次复核。Os.poll 等待有界管道上的数据，作用是读取当前一次快照；无事件时不会固定频率查询屏幕。实际功耗仍待真机测量。 |
| 最小性 | 4 项声明均找到实际用途。基础显示回调一档可不授 DUMP；POST_NOTIFICATIONS 是本版的可见性要求。没有理由追加 PACKAGE_USAGE_STATS、READ_LOGS、WRITE_SECURE_SETTINGS、忽略电池优化、Root 或任何生产模块权限。 |

本轮复跑 24 组状态机／电源字段 JVM 测试、3 项日志汇总测试及最终 APK 权限／DEX 审计，全部通过。它们未验证这台手机上的实际 Shell 身份、授权结果、进程存活或待机耗电。

## 5. 授权失败时的选择

| 路线 | 独立与长待机 | 可以计作的结论 |
|---|---|---|
| A · 仅公开显示／电源 API | 本 APK 可不授 DUMP 使用。FGS 和时钟进程分离，电脑可以断开；实际能否在 OEM 上跨长待机存活仍待测。无需改包 | 可验显示回调、暗态、AOD 和 ON 候选；完整电源状态缺失，FULL_WAKE 必须继续记为未证实。 |
| B · 观察器独立记录，ADB 旁证 | 不向 APK 授予 DUMP。只在获批的短测前后由受信任主机取得最少量的 power 字段，与同一 boot、同一段 uptime、同一内屏配对。只在端点连接时可做长待机辅助；持续 USB 供电或无线调试可能干扰耗电对照 | 可独立解释某个记录到的周期。事后最近睡醒值可能已被覆盖，不能证明 8 小时内每个沿，也不能将主机判读写成“APK 自主确认”。保持现版日志原样。 |
| C · 经授权的系统诊断组件 | 由厂商授权的窄接口或受管诊断服务仅提供指定字段，设计访问控制、故障断开及撤回机制。可脱离电脑，但需要另行开发、审查与长测。现有材料没有这样一个已验证可用的组件 | 接口确有同周期权威数据并验证后才可作为独立证据。当前不应安装特权应用或改系统来替代拒绝的普通授权。 |

**推荐放行顺序。** 首先批准 A 的短测即可。在确需完整唤醒证据、已核验包和证书、操作者接受系统诊断范围后，再单独批准短时 DUMP。确认授权前后的正负样本都能区分并能撤回，再决定是否另行批准 30 分钟和 8 小时。遇到厂商拒绝时优先用 B 补一个短样本，长期产品接口另行评估。执行与回滚见同目录 deployment-rollback.md。
