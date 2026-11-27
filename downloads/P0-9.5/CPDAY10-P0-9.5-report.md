# CPDAY10 P0-9.5 联调审查

## 已经成立的证据

DSH 的 P0-9.4 实测确认 event1、scan 116、KEY_POWER、300 ms 多击窗口和合格双击；两击之间保持唤醒。以首击为零，四个边沿分别为 0、100、189、314 ms。本轮将该时间序列直接用于既有共享判定器、Receiver、Activity 焦点与 LOCKED + 80 的联调测试。

使用 Android SDK apkanalyzer 解析已发布的二进制 Manifest 和候选 APK 的接收器 DEX，并以 apksigner 验证原 24、候选 28、回滚 28。三者包名为 com.naozho.clock，签名证书 SHA-256 均为 801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578，管理员组件均为 .display.ClockDeviceAdmin，接收器保护为 BIND_DEVICE_ADMIN。

| 项目 | 0.6.13-dev / 28 的实际情况 |
| --- | --- |
| 接收器 | 类 com.naozho.clock.mode.ConfirmedPowerReceiver 存在，DEX 定义 onReceive。Manifest 导出为 true，应用及接收器都采用 enabled 默认值 true。user 0 的安装后启用/停用状态由 verify 检查。 |
| 发送者权限 | 接收器声明 android:permission="android.permission.STATUS_BAR_SERVICE"；发件方须通过系统对这个组件的授权。该声明不授予时钟这个权限。接收器没有 intent-filter，模块指定显式组件。 |
| 正式请求 | user 0、目的 com.naozho.clock/.mode.ConfirmedPowerReceiver、action com.naozho.clock.action.CONFIRMED_POWER_DOUBLE。boot_count 为 int，first_elapsed 与 released_elapsed 为 long 毫秒；后两者与应用 elapsedRealtime 相同时间基准。0.2.0 添加 Intent identifier 以关联单次投递；应用校验不依赖 identifier。 |
| 窗口与锁定 | 私有别名 .mode.PowerClockEntry 不导出，目标 .MainActivity。RESERVE 只占用单个请求，CHECK 在入口复核，CONSUME 在真实获得焦点时执行；再由原代码读回 Lock Task、features 和名单。 |
| 更新兼容 | 同应用身份及签名，24→28 正常覆盖。时钟正式源码与 0.6.13 的 d82bc12 一致；对比 0.6.9 源码，Room schema v1、数据库定义及原管理员实现没有改变。升级/回滚仍须读回用户实际数据与 Owner。应用的模式基线会按现有逻辑增加字段。 |

## 发送方权限的具体证明

CPDAY10 原厂 services.jar 的 SHA-256 为 70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468。其 classes.dex 中 ActivityManagerShellCommand.runSendBroadcast 于 006b 调 broadcastIntentWithFeature；BroadcastController.broadcastIntentWithFeature 于 001d、0021 读取 Binder PID、UID。清单 Receiver 分支 BroadcastSkipPolicy.shouldSkipMessageInternal(…ResolveInfo…) 在 0121–012d 把 ActivityInfo.permission、发件 PID/UID、目标 UID 与 exported 交给 checkComponentPermission。外围 shouldSkipMessage(…ResolveInfo…) 于 0025 调用 Freeme Atlas 的 onBroadcastReceiver。可读取输入节点、拥有 Device Owner、shell 命令零退出、Broadcast completed 等事实均不足以证明受保护目标收到事件。

0.2.0 从同一个模块进程、同一 /system/bin/am、user 0、相同显式接收器和分发 flags，先发唯一探测 action，不含任何手势或时间数据。已核对的应用会在 action 不匹配时立即拒绝，不碰 mode_since、pending、桌面或锁定。模块读取 Android 按 action 过滤的历史，匹配本轮标识、实际组件、目标 user 0、唯一清单接收器、终态 DELIVERED，并记录系统认定的 sender UID。只有证据完整才开始等待实体双击。

实发使用新标识，再对正式 action 独立核对实际投递与发送 UID。这样可发现厂商按 action 区别处理。最多短读取三次以等候历史入账；广播各发一次。历史不存在、字段不兼容、权限拒绝、系统明确报告自启动拦截或其它跳过时，分别报告并停止。终态证明组件投递，应用接受、焦点锁定和实际触摸分别另证。探测成功表明该发送身份在当时的目标组件检查中获准，不代表某个普通安装包被永久授予系统签名权限。

[Android 16 BroadcastSkipPolicy](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/java/com/android/server/am/BroadcastSkipPolicy.java) · [Android 16 BroadcastHistory](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/java/com/android/server/am/BroadcastHistory.java)

## 测试与限制

- 应用 Development 测试 151 项通过，0 失败、错误、跳过。Robolectric API 35 复现 DSH 双击边沿；确认两击结束前没有请求，合格后只产生一个请求，重送无新窗口，焦点后为 LOCKED + 80。另测暂停、暂停后恢复与迟到交付、已锁定、探测纯拒绝、旧版本配置通过正常退出初始化。Robolectric 测试显式投递回调，不能验证板上 Binder 权限。
- 系统适配器 JVM 55 项、原有双击判定器 23 项、DSH 工具 8 项通过。覆盖实际 UID 回读、无历史、旧标识、跨用户、错误组件、权限拒绝、厂商明确自启动拒绝、重复历史与其它边界。正式请求的 UID 与权限探测 UID 的一致性仍需设备读回。包内模块可用 JDK 17、Android SDK 36、D8 重建。签名密钥与设备日志不随源码分发。
- 独立的 AOSP API 28 模拟器完成两次真实覆盖安装：在已有时钟 Device Owner 的 0.6.9-dev/24 上安装 0.6.13-dev/28，再覆盖回滚至 0.6.9-rollback-dev/28。两次均读回相同 Owner 和应用 UID，应用私有目录内预先放置的测试数据逐次读取一致。系统 PackageManager 返回候选 Receiver 的启用、导出及权限，旧版和回滚版查不到该组件。
- 同一 API 28 实例上实际进行受保护 Receiver 的正反对照。普通 ADB shell（UID 2000）被系统以 STATUS_BAR_SERVICE 拒绝，应用回调次数为 0。该 AOSP 工程镜像的特权发送进程用同一 am 广播路径投递惰性探测，应用回调增加 1 并按预期忽略未知 action。此实验验证应用接收路径与身份差异；API 28 没有运行限 API 36 的 KernelSU 模块，也未测试 CPDAY10 的 Atlas、调用身份、历史读回或物理按键。
- 云端 x86 API 36 尝试启动，未提供 KVM。软件模拟中发现 SystemUI/PermissionController 的 DeadSystemException，未在等待窗口内进入 sys.boot_completed=1。没有以此环境签署 Android 16 实际投递或专机验收。
- CPDAY10 的 24→28 实际更新、模块实发身份和投递、进入可触摸时钟、flags=80、开发退出及覆盖回滚均待批准后由 DSH 独立读回。当前没有改动用户手机。该模块为从亮屏 Freeme 前台手动启动的一次试验。
