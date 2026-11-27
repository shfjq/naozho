# CPDAY10 P0-9.4 系统电源键适配器

## 工程决策

本次交付一个可安装、手动开启、限时一次的 KernelSU 试验模块。首个有判别力的实验是从亮屏 Freeme 桌面观察真实双击。只有在两击期间系统保持唤醒、输入源可确认的情况下，才进入第二阶段，复用 0.6.13 的受保护返回入口。若首击已使系统休眠，被动观察不能可靠仲裁单击和双击；届时推荐厂商按键策略集成。其余应用前台、持续驻留和开机自动监听均未纳入本原型。无需更新时钟 APK。

## 证据及边界

静态对象为 DSH 在 CPDAY10 Android 16 上校验的 /system/framework/services.jar，SHA-256 为 70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468。下列十六进制偏移为各 DEX 方法内部的指令偏移。Android 原生 C++ 层另取 android-16.0.0_r1 对照。主板的内核驱动、实际启用的节点和厂商 native 库尚未取得逐文件实证。没有使用模拟器按键代替主板取证。

| 环节 | 实际可核对的路径 |
| --- | --- |
| 内核、EventHub | 通用路径是驱动上报 EV_KEY，经 evdev、EventHub::getEvents、InputReader 与 KeyboardInputMapper::process / processKey，由设备实际采用的 KL/KCM 把 scan/usage 映射成 Android KeyEvent。不能从 MT6789 型号推出 GPIO、PMIC、驱动名或 event 编号。原型仅接受当前内置节点、唯一映射及可信单调时间。 |
| InputDispatcher 到 Java | Android 16 参考实现由 InputDispatcher::notifyKey 进入 policy，JNI NativeInputManager::interceptKeyBeforeQueueing 交给 Java。CP 固件 classes2.dex 的 InputManagerService.interceptKeyBeforeQueueing 在 0000 调用 notifyKeyActivityListeners，在 0013 调用 KeyGestureController。如事件未被其接管，在 001e 转给 WindowManagerCallbacks。 |
| 厂商策略分派 | classes3.dex 的 InputManagerCallback.interceptKeyBeforeQueueing 在 0004 委派 WindowManagerPolicy。FreemePhoneWindowManager 同方法在 0000 调父实现。classes2.dex 的 PhoneWindowManager.interceptKeyBeforeQueueing 经 handleKeyGesture 及 POWER 分支，可分别到 044e 的 interceptPowerKeyDown、0453 的 interceptPowerKeyUp。策略还处理组合键及 GestureLauncherService，因此不同上下文可能提前消费。 |
| 原生多击到 Activity | classes2.dex 的 PowerKeyRule.onMultiPress 在 0002 调 powerPress，后者在 005a 调 powerMultiPressAction。行为 3 在 000f 调 launchTargetActivityOnMultiPressPower。该方法 0016 设显式组件、0020 解析，在锁屏未显示时于 0038 执行 startActivityAsUser，或走 0040 的锁屏代理流程。此 Intent 没有首击及第二次松开时间。现存资源基线为行为 0、目标空。 |
| Freeme 特有短击 | powerPress 的 008c 调 handlePowerShortPressBeforeDefaultAction。classes3.dex 子类要求 isGuiRunning、设备已初始化、FREEME_FORWARD_CUSTOM_KEY_SUPPORT。成立时 0023 以键码 26 生成 Intent、0027 发送；getIntent 在 0005 载入 com.droiclaw.launcher3.action.AI_KEY，在 000a 定向 com.droiclaw.launcher3。该分支只有条件短击，没有对外发布的一对按下与松开。 |
| 系统监听 API | classes2.dex 的 InputManagerService.notifyKeyActivityListeners(KeyEvent) 方法体只有 uptimeMillis 和 return-void。即使注册端能通过权限检查，这条具体调用也没有下发事件。未发现适用于时钟的公开厂商回调；不能据此否定厂商私有产品 SDK 的存在。 |

[Android 16 EventHub](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/services/inputflinger/reader/EventHub.cpp) · [键映射](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/services/inputflinger/reader/mapper/KeyboardInputMapper.cpp) · [InputDispatcher](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp) · [JNI](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/jni/com_android_server_input_InputManagerService.cpp)

## 实现与权限

模块 ID 为 naozho_power_trial，版本 0.1.0。KernelSU 3.3.1 提供模块生命周期、管理器 Action 和停用/移除标记。公开的模块接口未提供 Android 实体电源键回调。模块显式运行固定 DEX，以已有授权读取单一内置输入节点；运行仍受 SELinux Enforcing 和系统命令权限控制。库存检查只读 sysfs、EventHub 和实际映射文件。模块自身目录的 trial.lock 用于并发互斥。

- Board 只接受已识别的内置总线与平台路径，能力限 POWER 或 POWER 加音量。运行前从 Event Hub 的设备条目匹配启用状态和真实 KL/KCM。系统 getevent 以固定设备、只读非独占方式读取。发现音量组合、未知 usage、SYN_DROPPED 或时钟不可信即结束。带更多键的混合输入设备可能会被拒绝。区分其它节点上发生的组合键、持续获知电话和系统手势的优先级仍需厂商 policy 提供。
- PowerTrial 将有序事件送给已有 StationPowerShortcut 与 StationPowerArbiter，两次短按、第二次松开、第三击、去抖和交付时限继续使用原实现。为共享实现增加了交付回调构造参数；原有产品构造函数保留。跨休眠不接受序列。到提交边界再次查单显示组、电源转换历史、user 0、实际 Freeme 窗口、节点身份、模块状态及序列是否变化。窗口/电源状态来自分时快照，不能提供系统 policy 线程的原子性。
- 实发进一步要求匹配 services.jar、0.6.13-dev / 28 和实际 Device Owner。唯一目的地为 com.naozho.clock/.mode.ConfirmedPowerReceiver，显式广播携带 boot_count、first_elapsed、released_elapsed。接收器要求 android.permission.STATUS_BAR_SERVICE，按 Android 自身授权判断。OEM 拒绝时停止，不降低接收器权限。
- 0.6.13 在接收、目标 Activity 与首次获得焦点时复核条件；维护暂停、未启用独立专机、已锁定、旧开机编号、模式切换前的手势、在途/已消费、屏幕锁、非正常音频模式等均可拒绝。只有私有入口消费有效请求并获得焦点后才走原有 LOCKED + 80。本模块不直接调用 startActivity 或 startLockTask。
- 每轮最长 60 秒、最多提交一次。模块不启动系统服务，不写系统设置，无开机脚本、system 挂载、输入独占、按键注入、唤醒或电话控制。只报告筛选结果和拒绝原因。设备上的时钟可自行记录原有状态日志。试验开始时系统必须允许相应的读取与广播；KernelSU 有效本身不足以证明交付。

[KernelSU v3.3.1 官方模块文档](https://github.com/tiann/KernelSU/blob/v3.3.1/website/docs/guide/module.md) · [Android getevent 实现](https://android.googlesource.com/platform/system/core/+/refs/tags/android-16.0.0_r1/toolbox/getevent.c)

## 方案选择与下一步

| 方案 | 能力与实施判断 |
| --- | --- |
| KernelSU 被动观察 | 已构建。适合优先验证原厂单击时序、实际输入映射、广播权限和应用回执。若休眠抢先、输入源混合或系统无法提供可靠证据，仅保留诊断用途。长期运行的功耗、前台切换和组合键正确性尚未验证。 |
| 厂商支持的策略回调 | 作为需要可靠仲裁时的产品优先路线。向厂商确认能提供受信的默认显示器 POWER down/up、是否 interactive、取消、用户/焦点变更及单击等待窗口。用同一策略 Looper 接入现有 StationPowerShortcut，由产品系统发送固定广播。现有 AI_KEY 不能直接满足此契约。 |
| 正规产品 RRO | 上阶段离线 idmap 在合格产品身份验证过值 3 和目标 Activity 的映射。该固件的原生目标可能在第二次按下时就派发，也不附带释放时间、模式世代。仅改资源不能满足本项目误触、暂停后迟到请求的要求。若将来厂商提供兼容的回调，可重新评估。 |
| 匹配 BSP 的源码集成 | 没有可用回调时，由厂商在签名产品构建中接入上面的系统适配器，保留其原有单击、长按、关机和通话路径。需提供匹配构建、签名/验签与原厂恢复能力，开发及回滚成本高于模块。当前没有据此制作或发布系统映像。 |

如试验拒绝或要进入产品集成，仅需以下增量资料。能够读取不等于可以公开分发。

1. **输入映射**：先取 inventory 的 candidate、active_kl、active_kcm 和结果。找不到节点时只取候选内置开关键的 /sys/class/input/eventN/device/{name,id/bustype,capabilities/key}，以及 dumpsys input 中对应 Event Hub 条目的 Path、Enabled、KeyLayoutFile、KeyCharacterMapFile；成功发现后仅提取输出指出的实际 KL/KCM。N 和供应商文件名由实机确定。
2. **原生分歧**：若板上行为与 Android 16 参考实现不符，由固件提供方从同 build 的符号/映像交付 EventHub、InputReader/InputDispatcher、NativeInputManager 涉及的 ELF build ID 与对应实现。通常关注 libandroid_servers.so 及承载 inputflinger/inputreader 的库；实际分区、文件名和是否合并，以同构建的 system_server 已加载映射为准。无需导出全量日志。
3. **产品策略源**：向酷派 CPDAY10 产品技术支持/ODM 请求 MT6789、vnd_L930E_M41、与上述 services.jar 匹配的 FreemePhoneWindowManager（com.freeme.server.policy）、PhoneWindowManager/PowerKeyRule，以及相应产品资源或已签名的按键回调规范。Android 参考树位置是 frameworks/base/services/core/java/com/android/server/policy/PhoneWindowManager.java；Freeme 源码仓路径、是否提供第三方回调及厂商下载地址均待厂商确认。底层映射有分歧时，向 OEM 索取匹配的 GPL 输入驱动/设备树及 ODM 实际启用的配置；相同芯片其它机型的源码不足以确定本板映射。

升级固件后实发校验会拒绝未审查的 services.jar。先重做对应方法和资源对照，再决定是否支持新版。产品验收需要基本紧急呼叫入口、开关机、充电正常、维护暂停关闭返回、重复手势只进一次。原厂五击 SOS 不是本阶段必要条件。开机第一屏为独立验收项目。
