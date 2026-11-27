# P0-9.7.9 离线验收记录

本次发布对象为 CPDAY10 的 KernelSU 模块 naozho_wake 1.0.0/1 和时钟 0.6.14-dev/29。云端未连接或部署到手机。DSH 先前验证的 0.6.13 双击返回、WakeProbe 全亮屏识别，是本次复用的基线。

| 验证 | 本次执行结果 |
|---|---|
| Gradle assembleDevelopment、testDevelopmentUnitTest | 构建成功；25 个测试套件、158 项测试，失败 0、错误 0、跳过 0。Robolectric 时钟链路使用 API 35。 |
| 端到端协议互操作 | 生产 WakeWire 的 am 类型化字段和不同 trace 进入实际 ConfirmedPowerReceiver、私有入口和 MainActivity；生产 WakeDispatch 协调整个流程。验证正式信封不启动窗口、提交后得到焦点并消费请求、LOCKED、flags=80、单包名单和本次确认文件。系统传输、AMS 回执和服务状态在此测试中用测试替身提供。 |
| 暂停、重放与回收 | 覆盖无收据、错 boot/source/UID、改动请求、过期、取消收据、暂停期间迟到、恢复后拒绝旧事件、已锁定、PINNED、开发退出后拒绝原事件，以及任务丢失后新周期可认领。 |
| 显示与 Power 证据 | 复跑原生产 WakeCycle/PowerEvidence 的 24 组测试；新流程另有 27 项断言，覆盖 AOD、DREAMING、长待机时 uptime 与 elapsed 分离、重复 ON、下一周期、系统再次睡醒、UID 不一致、暂停竞态、回读失败及单次调度。 |
| 窗口与身份保护回归 | 生产共享模块回归成功。Daily JVM 190 项、Freeme 53 项、字段格式 49 项、快照边界 46 项。另运行 AMS 投递历史解析、负向窗口、单监听器及 DSH 工具测试。 |
| 模块构建 | JDK 17 使用 API 36 SDK 编译，R8 裁剪代码。ZIP 完整性检查通过，包内 clock.sha256 匹配最终候选 APK。DEX 检查确认 WakeDaemon、WakeEpochManager、WakeWire、WakeDispatch、DeliveryProof 与可见窗口解析器均在包内。构建检查排除了输入监听和系统计时设置代码。随包 shell 通过语法检查。 |
| 覆盖与回滚 | 候选 0.6.14-dev/29、回滚 0.6.13-dev/29 和原 0.6.13-dev/28 三者均通过 apksigner，证书 SHA-256 一致，为 801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578。新旧 APK 的权限清单一致。最终 APK 的 ConfirmedPowerReceiver 受 STATUS_BAR_SERVICE 保护，PowerClockEntry 未导出，管理员组件名及 BIND_DEVICE_ADMIN 保护保留。 |

一次中间测试因两个 Gradle 进程同时输出 XML 失败。重新串行运行，并在加入生产协议互操作测试后核对最终 25 份 XML。上述数字来自最终测试结果。

## 真机尚待确认

首先核对 CPDAY10 上的覆盖安装、UID 与 Owner。然后检查 root 进程初始化 Context、真实显示回调、AMS 投递身份、维护暂停的实时撤销及实际触摸。电源键、抬手、双击屏幕、通知 AOD、通知完整亮屏、闹钟、普通进程回收、重启与完全停用都要分别记录。完整唤醒遇到真实响铃交互、认证或遮挡时，预期记录拒绝。默认显示状态变更由系统回调；固件漏发的状态不能由云端测试排除。

新模块的耗电、所有唤醒来源的成功率、真实设备触摸和开机第一屏均无本版真机结果。详见 DSH 手册。
