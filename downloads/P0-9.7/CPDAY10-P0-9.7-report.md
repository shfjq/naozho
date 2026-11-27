# CPDAY10 P0-9.7 日常电源键双击适配报告

模块为 **naozho_power_daily 1.0.0 / code 1**，面向 CPDAY10、arm64、原厂 Android 16 / API 36、KernelSU 3.3.1 和 SELinux Enforcing。发布的是默认关闭的待审查模块。0.6.13-dev / 28 的安装包和应用源码沿用既有交付。

## 基线和新能力

P0-9.6 的一次性投递、焦点、LOCKED + 80、触摸和正常退出来自 DSH 的实机验收。此次云端实现了独立的日常模块、用户明确开启、跨开机记忆、多次不同手势、前台筛选、停止监听及资源测量。新模块在 CPDAY10 的日常运行、各页面兼容性、冷启动及耗电均待 DSH 测量。

沿用已有结论：该固件公开的可用回调不能提供本项目需要的完整、受条件限制的实体电源键手势。正式版选用 KernelSU 官方 boot-completed 和 Action 生命周期；继续复用已经验收的手势状态机及受保护广播。无 system_server 修改、RRO、系统文件挂载、输入注入、事件独占、设备电话控制或按键策略设置。原有 naozho_boot 负责原开机恢复，本模块的开机脚本仅按已保存的用户选择启动监听。

## 实现

| 阶段 | 实际行为 |
| --- | --- |
| 安装、开启和重启 | 首次安装没有 armed 标记。用户 Action 生成新授权代次；下次正常开机在同一代次恢复。文件锁限定一个实际监听进程，重复启动直接退出。停止后重新启用会淘汰旧代次。 |
| 输入 | 核对当前固件、内置总线、唯一节点、EventHub 启用状态、实际 KL/KCM 和字符设备号，仅打开已经实测的 /dev/input/event1。只读 fd 使用 EVIOCSMASK，并以 EVIOCGMASK 读回类型与键码掩码。内核仅向此客户端交付 KEY_POWER 以及内核必需的同步边界。不接收普通按键、触摸或文本，不注入和独占。映射含 usage 覆盖且源可报告 MSC 时拒绝启用。 |
| 等待与停止 | 在同一进程内用 poll 同时等待 evdev 和 inotify，无固定轮询周期，无唤醒锁。停用、移除、授权代次变化、监听目录失效和事件丢失均可中断空闲等待。系统命令只在初始化或合格双击时短暂运行。 |
| 识别 | 复用 StationPowerShortcut 和 StationPowerArbiter 的两次短按、松开、静默时间窗、重复、长按、第三击及时间新鲜度处理。以物理事件的单调时间和设备电源历史排除熄屏、刚唤醒及跨休眠序列。 |
| 前台 | 读取 user 0、实际锁定、Keyguard、各 SIM 呼叫状态、项目现有模式与 mode_since、焦点窗口与聚焦 Activity。核对可见窗口类型、标志、所有者、显示器和焦点窗口 ID。仅允许已审查的普通页面、预期的壳层窗口以及位于其后的壁纸。发送前再次比对聚焦窗口身份。陌生格式、非零呼叫、SECURE、通知面板、IME、额外应用窗口、弹框、认证页均放弃本次手势。 |
| 范围 | 内置 Freeme、普通入口打开且无深链或额外参数的设置首页、OpenCalc 3.2.1 的计算主页。设置检查聚焦 Activity 的实际启动 Intent 与主任务根。其他经审查的单一用途第三方 Activity 可绑定确切组件与 APK 内容摘要；分包、更新、共享敏感页面或不能分类的 UI 暂不放行。附加配置不能将系统安全组件或默认拨号器放行。 |
| 模式与投递 | 模块只读既有模式字段。仅在本来已启用独立专机且处于 ANDROID、NONE、正常唤醒时提出请求。进入 CLOCK、维护暂停或重新启用前的旧手势失效。模块使用 0.2.1 的投递证明，探测须在一个完整用户 0 记录中匹配 action、identifier、显式组件、实际发送 UID 和 manifest DELIVERED。每次正式交付独立验证，发送 UID 必须相同。 |
| 前台提交 | 唯一接收器为 com.naozho.clock/.mode.ConfirmedPowerReceiver，仍要求 android.permission.STATUS_BAR_SERVICE。时钟自己在保留、进入和获得焦点时复查模式、Owner、独立专机、锁屏/交互、音频模式、开机编号、时效及重复。模块不调用 startActivity 或 startLockTask。 |
| 失败 | 无法判断前台只丢弃该次手势。发送结果不明、身份不符或输入完整性故障时停止并需明确重新启用。没有重发、循环拉回、故障自启或替代权限通道。 |

内置普通第三方示例核对了作者发布 APK 的 Manifest 和主 Activity 源码。包名 com.darkempire78.opencalculator、code 54、主页 .activities.MainActivity，审核的 APK SHA-256 为 `43b6befd1fecc686ba1611bbda18896cc26d966047e788be995def569a4510f3`。版本更新须重新审查。[OpenCalc 发布页](https://github.com/clementwzk/OpenCalc/releases/tag/v3.2.1)

前台读回属于连续系统快照。若 OEM 隐藏任一必要证据或在快照与广播间切换到安全界面，仍有兼容性和时序风险。实际开测试前保持模块关闭；若特殊界面测试出现抢占，停用模块并沿用时钟图标返回。尚无证据能把任意第三方应用内部动态网页或凭据页面一概判定为普通界面。

## 权限和持久化

| 范围 | 用途 |
| --- | --- |
| KernelSU 已有授权 | 限定 arm64 监听进程、只读 evdev、sysfs、固定系统诊断与固定目标的探测和正式广播。未增加应用权限或 SELinux 规则。 |
| 模块私有目录 | 授权代次、运行锁、PID、可选的已审查页面清单、最近状态与轮转日志。没有通用命令入口，没有外部网络服务。 |
| 存储与日志 | 启用进程约定的两份轮转文件各不超过 8 KiB，达到上限或跨 UTC 日后的下次写入轮转；另外有一条覆盖更新的状态。普通拒绝的文件日志至多每分钟一条；机内报告只含原因和累计计数，不记录目标应用内容、逐键事件或输入时间线。Android 系统及既有 APK 自行管理其原有 logcat。 |
| DSH 观测 | 默认保留计数、焦点分类、锁态、白名单、flags 和本轮相关应用收据；inspect-page 仅用于主动选定的第三方页面审查。验收和能耗快照在 DSH 电脑本地独占创建。 |

时钟 APK SHA-256 为 `8bcf50a524f58b6c8180d699f47a18fd096d94b7b12d737d1a60710d189597d4`，云端以 apksigner 核验保留文件的 v2 签名，证书 SHA-256 为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。无 APK 重建或回滚。新模块未改变 HOME、Lock Task 策略、Keyguard、Wi-Fi、蓝牙、充电或温控设置。

## 自动化与资源实测

| 环境 | 通过项 | 覆盖 |
| --- | ---: | --- |
| Linux 原生测试 | 14 | ioctl 能力/掩码模拟，真实 pipe、inotify 和阻塞读取；非法事件、丢失、停用、FD 稳定性 |
| 日常模块 JVM | 81 | 多轮返回、维护与迟到手势、权限不明停止、设置路由、窗口/弹框/通话、重入与跨进程锁、日志轮转 |
| 共享手势及投递 JVM | 49 | 23 项手势测试、26 项投递证明测试 |
| DSH 工具 | 8 | 时间段内的回执、实际模式/触摸、不同步样本、策略读取、耗电比较 |
| 现有 0.6.13 应用 Robolectric | 16 | 定向执行 ConfirmedPowerReturnTest 与 PowerReturnActivityTest，包含 Keyguard、通话、维护暂停、焦点提交、重复及过期场景 |

合计 **168 项通过**。软件编译使用 API 36 SDK、JDK 17、D8 Build Tools 35.0.0 和 NDK r27d。模块包含 DEX 和 arm64 JNI 库，ELF LOAD 段按 16 KiB 对齐，非可执行栈。对照交付源码可重建相同字节。

在 Linux 上以 10,000 个合成电源边沿运行实际读取循环，FD 增量为 0，进程最大 RSS 增量为 0 KiB。在两次 250 ms 空闲阻塞至停用标记的主机样本中，读取线程 CPU 时间分别为 0.031 和 0.107 ms。芯片、Android 运行时、唤醒源与射频耗电不同，此测量只验证阻塞机制；它不能给出 CPDAY10 待机小时数、实际 RSS 或整机唤醒次数。手机上的进程数、FD、RSS、CPU ticks、唤醒次数与电池 A/B 测量由交付工具和手册覆盖。

## 构建和源码

从源码包根目录，设置 JAVA_HOME，使用 Linux 和以下命令。NDK 值指向 r27d 解压目录，SDK 值指向 Android SDK。

```sh
python3 kernelsu/naozho_power_daily/test.py
python3 kernelsu/naozho_power_daily/build.py --ndk "$NDK" --android-jar "$SDK/platforms/android-36/android.jar" --d8 "$SDK/build-tools/35.0.0/d8" --out naozho-power-daily-1.0.0.zip
python3 tools/p097/export_tool.py cpday10_daily.py
```

新增源码在 kernelsu/naozho_power_daily 和 tools/p097。与试验模块共享的 Board 仅增加可选的安静回执输出，原试验调用保留原接口与验证条件。系统模块和主机工具各自独立运行。手机不需要编译工具。

## 待真机签收

须逐轮验证亮屏前台、正确受理一次、实际时钟焦点、LOCKED、flags=80、唯一允许名单和真实触摸。另验正常退出停留、暂停与恢复、特殊界面、重启、关开机、热管理、网络、耗电和卸载。开机动画后第一帧为可交互时钟仍是独立待解决目标。

[KernelSU 官方模块说明](https://kernelsu.org/guide/module.html) · [Android 16 WindowState](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-16.0.0_r1/services/core/java/com/android/server/wm/WindowState.java) · [Linux evdev 每客户端过滤机制](https://github.com/torvalds/linux/blob/v6.6/drivers/input/evdev.c)
