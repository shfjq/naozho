# P0-9.7.9.2 · 息屏预热与唤醒性能对照

目标为 CPDAY10 在完整交互唤醒后 2 秒内显示时钟，并验证窗口焦点、独立锁定与触摸。候选为时钟 0.6.15-dev/30、naozho_wake 1.1.0/2。操作范围为云端源码、构建、离线测试及发布。

## 设备时间基线

| CPDAY10 指标 | 1.0.0 周期 1 | 1.0.0 周期 3 | 1.1.0 |
|---|---:|---:|---|
| WAKE_CANDIDATE 至 root 最终确认 | 5250 ms | 4731 ms | 待真机测量 |
| 亮屏至时钟取得焦点 | 约 4540 ms | 约 4150 ms | 待真机测量 |
| 完整唤醒至首次时钟绘制及独立锁定 | 未提供同口径时间戳 | 未提供同口径时间戳 | 待真机测量 |
| 用户看到 Freeme 的时长 | 未量化 | 未量化 | 待视觉观察 |

DSH 对旧版周期 1 的分段为唤醒至 RETURN_PENDING 约 1.47 秒、投递约 1.19 秒、COMMIT 阶段约 1.65 秒、最终焦点约 0.93 秒。仅凭这些汇总无法把某段时间全部归因于进程冷启、AMS 调度或绘制。

## 息屏阶段做了什么

- 使用已有 STATUS_BAR_SERVICE 保护的显式 Receiver 接收独立 **WAKE_DARK_PREWARM**。模块订阅真实 OFF 并核对非交互、用户、模式、APK 及 Owner；应用再检查 OFF、用户已解锁、独立部署、处于安卓模式、boot 编号、暗屏时间和有效期。一次暗屏最多一次工作，预热标识与正式 request_id、wake_epoch_id 分开。
- 进程未运行时由 Android 创建原应用进程及 Application，进程已运行时复用。后台加载现有显示/天气偏好文件、星期资源，并通过同一个 AlarmRepository / Room 连接执行 SELECT 1。时钟显示时仍读实时日期、电量与闹铃；预热无需读取用户闹铃行。Room 第一次打开时可进行其正常数据库初始化。
- Application 的 IO 工作立即与广播分离，没有 Activity、通知、服务、窗口、WakeLock、锁定或正式返回。进程内初始化只做一次；复用原进程和回收后冷启动都受支持。PREWARM_READY_AT 仅由真实完成工作的应用记录。Root 的广播成功不能代替这个标记。
- 首次可用的发送 UID 证明也可利用息屏期同运输、同组件、同权限的 AMS 终态投递。未取得证明时走原有亮屏权限探测。亮屏工作用不同执行器，预热未完成、被系统回收或被 Atlas 拒绝均不构成唤醒前置条件。

| 方案 | 选择依据 |
|---|---|
| 复用受保护 Receiver 和原进程 | 已有本机显式广播链路；只增加一个无界面动作。新预热动作的实际冷启和存活率待设备验证。 |
| 内部 Service | 跨 UID 的 root 请求不能直接当作应用内部调用，另有后台服务启动和生命周期成本。此阶段无长期运行需求。 |
| ContentProvider | 可触发进程初始化，但需增加跨进程端点及访问保护，还需单独处理 Atlas 对 Provider 的限制。 |
| NoDisplay Activity | 仍参与任务启动与窗口调度，无法满足严格的息屏不取焦点要求。 |
| Root 自行读文件预热 | 页缓存不能代替目标应用进程里的 Application、Room 和资源对象；仅由 root 准备受保护的传输链路。 |

## 亮屏关键路径的改动

1. ON 回调立即读取 power。若转换尚未收敛，保留 200、400 ms 的有限后续读回。只有显示、交互、Awake、同一对睡眠/唤醒 uptime 同时符合才建立 epoch。AOD、DREAMING 和未知情况继续受限。
2. 预热已证明发送身份时，复用原本就会执行的两次完整前台守卫，合并外层重复的模式及焦点查询。APK 与 Owner 在守卫工作线程核对；两个守卫使用实际窗口 token 和页面，COMMIT 前并行核对电源历史、部署代次和实时焦点。所有必需条件满足后才投递。
3. AMS 定向查询未给出可证明的终态时立即读一次完整历史。若此时仍在排队、历史缺失或较大，原有延迟读回仍然可用。每次独立核对 action、唯一编号、user 0、实际 UID、组件和明确 DELIVERED。只重读证据，不重投。
4. 已确认的唤醒入口单独申请 FLAG_ACTIVITY_NO_ANIMATION。系统可自行决定转场和启动窗口。MainActivity 使用原 singleTask 复用实例；当前请求已获焦点且 ClockScreen 完成非零尺寸 drawContent 后，才消费唤醒收据和执行原独立锁定。
5. root 在 COMMIT 前注册只读收据文件观察。收到时提前做实际确认；文件事件丢失时仍走有界读回。应用核对 LOCKED、80 和精确允许名单，root 单独核对实际前台与锁定。

## 实测的离线等待差异

在云端运行生产 DeliveryProof.verify 的两个策略，使用同一已脱敏 AMS 格式：定向视图仅有摘要、完整视图已具备该请求的完整终态。使用真实 Thread.sleep 和 System.nanoTime，不模拟时间推进。

| 生产证明策略 | 三次运行耗时（毫秒） | 每次读取 |
|---|---|---:|
| 旧策略 | 1906.05、1803.54、1814.61 | 4 |
| 唤醒快速路径 | 1.35、0.81、1.22 | 2 |

这是单个“摘要可见而终态已可读”分支的 JVM 实测，输入在内存中，未包含 Android IPC。若 CPDAY10 的首个定向查询直接命中，旧版也无需这段等待。不能把该差值从整机基线直接扣除。新方案另消除了已收敛时固定的首读前 200 ms 排队。数据库冷启动、Atlas 调度、窗口切换和真实像素呈现仍需实机区分。

## 时间线与结果判读

所有阶段用本机 elapsedRealtime 毫秒。按 boot_count、暗屏单调时间、request_id 合并，模块另保留含内核 boot UUID 的 epoch。工具按时刻重排两端日志，并拒绝将多次正式请求或缺项数据算成完整成功。

| 时间点 | 实际测量位置 |
|---|---|
| DARK_OBSERVED_AT | 默认显示器进入 OFF 的观察时间 |
| PREWARM_START_AT / PREWARM_READY_AT | root 发出预热前 / 应用完成工作并仍符合暗屏条件。同阶段 PID 可与 Activity PID 比对 |
| WAKE_CANDIDATE_AT / FULL_WAKE_AT | 观察到由暗到 ON / Power 与显示状态共同确认 |
| RETURN_PENDING_AT / RETURN_DELIVERED_AT | 进入正式决策 / root 取得本次 RETURN 的 AMS 终态证明 |
| COMMIT_DELIVERED_AT | root 取得同一请求独立 COMMIT 的终态证明；可能晚于 Activity 的第一帧 |
| ACTIVITY_START_AT / ACTIVITY_READY_AT | 有效请求进入 onCreate 或 onNewIntent 的时间 / 实际时钟 Compose 内容绘制结束 |
| CLOCK_FOCUSED_AT / LOCKED_CONFIRMED_AT | 当前请求的时钟窗口已恢复且取得焦点 / 应用读回 LOCKED、80 和精确名单 |
| CLOCK_FOCUSED | root 独立验证成功并结束请求 |

软件首绘与面板实际输出存在合成间隔。保留 Freeme 为默认 HOME，并在完整唤醒后才允许切换焦点，系统可能先呈现上一帧 Freeme。首帧和焦点提前可缩短可见时间；新版是否达到 2 秒、闪现是否消失、用户触摸是否正常，须分别填入实测结果。

## 构建与回归

最终 Gradle development 构建成功，25 个套件共 160 项测试通过，错误、失败及跳过均为 0。覆盖真实生产信封/Receiver/MainActivity；预热用同一 Room 代码；唤醒首绘测试使用 Robolectric Android 35 的原生图形渲染并实际绘制时钟 View。覆盖热资源复用、重复暗屏、OFF/DOZE、维护暂停、无预热的完整返回、焦点先到但首绘未完成、首绘前进入维护、重复请求与实际策略回读。共享唤醒判定 24 组与 27 项流程断言、窗口分类和 DeliveryProof 回归另行运行。时间线工具测试缺项、重复和跨日志顺序。

独立 APK 和配套回滚 APK 均与原版证书 SHA-256 一致：801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578。回滚模块与原始 1.0.0 逐条比较，仅 clock.sha256 因配套 APK 版本号而不同。两对 ZIP 均核对内置 APK 摘要。[DSH 手册](DSH.md)
