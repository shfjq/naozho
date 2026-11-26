# CPDAY10 P0-9 系统 HOME 与电源双击可行性审查

**本轮决策**　保留 0.6.9-dev 与 naozho_boot 1.0.0 为真机基线。0.6.10-dev 是应用层审查候选版。下一步优先向厂商确认针对时钟包的 HOME 登记及真正掌握电源键仲裁的接口。固件中已定位导致全局 HOME 缺项的代码，也定位了双击目标 Activity 的调用链。两项产品能力都需要进一步系统集成及真机验收。

## 证据来源及版本

- 独立分支 p0-9-system-clock 从开发工作区 work 的 79954aa 派生。GitHub 检查时仅有公开下载分支 p5-download，起点 c2b8cb2。源码基线和原交付 APK 均为 0.6.9-dev / 24。P0-8 的 CE 自动解锁、模块可投递、前台与 LOCKED + 80 来自 DSH；Keyguard → Freeme → 时钟的录像结论仍是本轮的体验基线。
- 对 DSH 采集的 /system/framework/services.jar 三个 DEX 做离线反汇编。其 SHA-256 与同批设备端记录一致，为 70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468。下述地址是方法内的 DEX 指令偏移。设备 OTA 后须重新核对指纹和文件摘要。
- 平台参考为 AOSP android-16.0.0_r1，KernelSU 文档采用 v3.3.1。AOSP 的默认资源值与本机当前资源、Settings 值及运行中字段分别记证。[Android 16 HOME 启动](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/wm/RootWindowContainer.java) · [Android 16 电源键策略](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/policy/PhoneWindowManager.java) · [KernelSU 模块](https://github.com/tiann/KernelSU/blob/v3.3.1/website/docs/guide/module.md)

## HOME 为何一直解析为 Freeme

1. 固件 RootWindowContainer.startHomeOnTaskDisplayArea 和 resolveHomeActivity 走系统 HOME 解析。ResolveIntentHelper 在查询候选后选择最佳 Activity。ComputerEngine.queryIntentActivitiesInternal 有调用 applyPostResolutionFilter 的真实指令。
2. 在 ComputerEngine.applyPostResolutionFilter 的 0x013d，固件装入内置桌面列表，其中有 Android Settings、Freeme SetupWizard、DroiClaw 和 Freeme SuperPowerSaver。0x0198 起检查 Intent 未限定包、包含 HOME category、action 包含 MAIN，且列表有内容。
3. 0x01f7 起倒序遍历结果，0x0203 读取组件包名，0x0205 在内置字符串中检查该包名，0x0240 从候选列表移除未命中的项。时钟与原对照包都不匹配。限定包名的 Intent 跳过这段分支。附近的调试开关只控制日志。这里没有检查 FLAG_SYSTEM、priv-app、平台签名或窗口优先级。
4. 这解释了同机同用户全局查询缺项、按包查询存在的差异。RoleManager、用户默认桌面选择与 Device Owner 的持久化偏好只能在解析时发挥作用。时钟未进入有效候选时，持久策略 SET 成功仍可解析回 Freeme。显示结果要同时包含全局候选、系统 resolve、启动任务和窗口焦点，再以整段外拍确认首屏。

| 路线 | 实施决策与理由 |
| --- | --- |
| 官方 HOME 角色、持久 HOME、系统锁屏设置 | 保留并优先复用。须由厂商确认本固件支持的扩展登记接口或提供已签名的固件支持；在 NONE 下验证 user 0 全局候选、双向解析和实际启动，再启用既有锁定。 |
| 系统应用或 priv-app | PackageManager 在开机扫描有效分区时才赋予相应标志，已有 /data 更新包还涉及版本、原证书和实际生效路径。上面的删除分支没有系统应用豁免。仅改变安装位置无从解决该分支。保持原签名、原 UID 分配和 Owner 组件；本版新增特权许可为零。 |
| 可撤销的 KernelSU 系统集成 | 既有模块带 skip_mount，只负责观察和一次性恢复。v3.3.1 挂载 system 目录另需兼容的 metamodule；资源 overlay 还依赖目标资源可覆盖策略。当前白名单为 DEX 常量。简单资源覆盖不能把时钟加入它。先维护模块 1.0.0 的观察/备用用途。 |
| 厂商系统集成 | 若正式登记途径不存在，申请厂商针对 ComputerEngine.applyPostResolutionFilter 的单包、按用户、保留原四项的受支持配置；可由厂商将企业专机 HOME 接入正常选择。即使加入候选，仍须验证开机第一次 HOME 决策。框架更改会影响 system_server、OTA 与启动恢复。本轮只定位与设计。 |

**冷启动还有一个独立问题。** 日常退出若把持久 HOME 改回 Freeme，突然断电或正常重启时该偏好依然存在。解锁后再改回时钟必然有时序竞争。最终设计要让系统在第一次选择 HOME 之前就知道用户是否暂停专机。优先选择厂商支持的开机 HOME 选择器或部署配置；运行期退出恢复 Freeme，下一次启动由早期系统选择器应用新的启动意图。若厂商仅能静态增加候选，不能保证这一顺序，应把“退出后冷启动第一屏”为时钟保留为未解决项。保持时钟永远为 HOME 并在 Android 模式反复转发会改变正常桌面语义，需另行评估。

**目标时序**　开机动画 → user 0 的专机部署意图可读 → 系统选实际 HOME → MainActivity 首次可见即呈现可交互时钟 → 取得焦点 → 读回 LOCKED、80、仅时钟在允许名单。普通开发退出和维护暂停都不得用重启广播或模块在此轮开机拉回。验证首屏时使用模块 OBSERVE，并排除广播、Job 或显式启动作为时钟来源。

## Keyguard 与 Direct Boot

用户通过 Android 正常设置把屏幕锁定方式选为「无」。有无安全凭据、是否仍有滑动锁屏、CE 是否 RUNNING_UNLOCKED、当前窗口可触摸是四项不同的检查。确认无凭据且仍显示滑动页时，使用已具备 Owner 且处于 NONE 的现有维护入口评估 setKeyguardDisabled(true)，记录返回值与实际重启画面。恢复时使用同一入口的「恢复系统锁屏」。应用自身 PIN 与恢复能力的既有代码和非开发版本行为继续保留。

MainActivity 与 ModeBootReceiver 支持 Direct Boot，但完整界面和模式配置目前在 CE 可用后读取。CE 不可用时的 HH:mm TextClock 只用来过渡。一段只显示数字且不可操作的首屏不能通过验收。若证实系统第一次 HOME 早于 CE，下一步是在同一 MainActivity 内提供具备实际触摸功能的启动页并原位接入完整界面；维护暂停必须先可读，避免抢占设备。先前的 KSU 请求可用于故障恢复，并在视频中单独标记。

## 电源键双击的证据与限制

- 固件 FreemePhoneWindowManager.interceptKeyBeforeQueueing 调用父类。PhoneWindowManager 的 PowerKeyRule.onMultiPress 调用 powerPress，count=2 分支读取 mDoublePressOnPowerBehavior。updateSettings 路径读取全局 power_button_double_press，缺值才使用资源默认值。行为 3 在 powerMultiPressAction 调用 launchTargetActivityOnMultiPressPower；目标组件来自初始化时读取的框架字符串，对应 AOSP config_doublePressOnPowerTargetActivity。该路径显式解析组件，有 Keyguard 时还有不同的系统分支。采集包缺本固件的 framework-res 及生效 overlays，目前没有本机目标字符串或行为数字的可靠读数。
- 固件保留 GestureLauncherService.interceptPowerKeyDown 以及相机、钱包、紧急手势处理，Freeme 还在单击默认行为前调用 handlePowerShortPressBeforeDefaultAction，某些 GUI 状态会消费短按。仅把双击目标指向时钟，无法证明第一下没有提前灭屏、相机不会启动、关屏双击不受影响。
- AOSP 的 SingleKeyGestureDetector 区分 down/up、长按和多击。在达到最大多击数时可在该次按下时就派发。普通显式 Activity 收不到第一次按下前的亮屏状态、第二次释放、整段序列及紧急手势的最终归属。即使它启动后马上 finish，也可能产生一次可见的窗口切换。[Android 16 手势识别](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/policy/SingleKeyGestureDetector.java) · [相机及紧急手势](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/GestureLauncherService.java)
- 首选厂商已有可配置、能在整个系统范围内完成仲裁的快捷方式。若仅支持静态目标，要求厂商在既有 powerPress/powerMultiPressAction 分发处提供决定结果，同时保留 GestureLauncherService 的紧急优先级。需要从第一次按下记录原始 interactive 状态，通过同一串的两个短按与释放、取消、长按、重复及多次按压判断，等待原生策略确认这次双击独占，确认还在同一 user、boot、模式代次。无法排除竞争时交还原厂处理。不得在第一次按键发生时就抢占或延迟紧急动作。仲裁完成后才向已有前台时钟路径提交一次动作。窗口参数以本机原厂设置和实际按键时序为准。
- 仓库 tools/p09/power_contract.py 是仅在主机运行的判定模型。它接收已结束序列及模拟的系统决定，不采集或拦截按键。自动化覆盖两次短按、未松手、错序、长按、重复、连续多击、起始/结束屏幕和模式变化、竞争动作。它没有证明 CPDAY10 已提供独占回调。正式集成应使用仅受信系统调用者可达的窄接口，去重同一事件，并在界面取得实际锁定前保留待确认状态。

核对实际配置时，分别保存全局设置覆盖值、框架资源默认值、WindowManager 已加载的运行值。厂商若提供用户可见的快捷键配置，还须核对它是否同时处理屏幕初始状态与暂停切换。一般 RRO 只能覆盖被允许的资源，特权权限名单也只负责授权。 [Android RRO 机制](https://source.android.com/docs/core/runtime/rros) · [特权权限名单](https://source.android.com/docs/core/permissions/perms-allowlist) · [Android HOME 角色](https://developer.android.com/reference/android/app/role/RoleManager#ROLE_HOME) · [受管专机](https://developer.android.com/work/dpc/dedicated-devices/lock-task-mode)

## 双模式状态与数据归属

候选 APK 仍以 ModeState/desktop_mode 为持久的用户意图，由系统读回当前结果。新增的同源状态供恢复分支和开发日志使用，没有引入第二份设备管理身份或失配的镜像配置。

| 状态/事件 | 本轮实现及正式目标 |
| --- | --- |
| CLOCK | 当前窗口在时钟页、resumed、有焦点、Keyguard 已放行、Owner 和实际锁定/名单/标志均正确时记录 CLOCK。触摸另行验收。 |
| ANDROID | 确认开发退出后通过原路径停锁并回 Freeme；取消继续留在 CLOCK。同一次开机后台请求和过期 Intent 由原校验拒绝。图标仍可主动返回。 |
| MAINTENANCE_PAUSED | 用户明确暂停，撤销允许名单、取消独立 Job、保存 managed_lock=false。新 boot 或模块旧请求均不能重新武装。初装未配置单列 NOT_CONFIGURED。 |
| BOOT_PENDING | 已启用、意图为时钟但本次观察尚未确认锁定/焦点。也用于前台重新取得确认的过渡。保存的“想进时钟”不能转记为验收成功。 |
| 退出后重启、主动恢复 | 通过 boot_count 区分退出所属开机。已启用者转待恢复，维护暂停者保持安卓；仅用户主动恢复才能再次武装。新 APK 对有效跨开机入口优先恢复 CLOCK 页，同次开机重建仍保留设置页。 |
| 全局电源双击 | 仅设计和离线验证。在 ANDROID、已武装且屏幕原已点亮的条件下允许返回，维护暂停与 CLOCK 均交还原厂。正式变更须与现有 ManagedDeployment 的写串行化，重新核对模式代次和事件编号，处理投递失败，不通过回调提前宣告 CLOCK。 |

**DE 演进方案。** 当前 24/25 的专机设置仍统一位于 CE。只有厂商支持首个 HOME 决策、确认需要更早读取时，才迁移最小的 user 0 部署记录（schema、是否武装、维护暂停、上次主动退出的 boot、模式代次）到 DE。由唯一写入者原子更新，回读成功再提交迁移标记。缺失、损坏、版本太新或迁移中断时保持可恢复的安卓路径。暂停优先于老代次请求。解锁后可重试迁移，正式迁移版须配套兼容的反向迁移后再回退。应用凭据、个人设置及其他 CE 数据留在原处。当前版不涉及存储格式迁移。

## 分级实施与停止条件

1. **已执行**　核对原始制品及固件、制作独立分支、修正跨重启旧页面覆盖、加入可核验的模式状态、编译签名、主机测试及只读采集工具。没有安装模块或操作手机。
2. **DSH 只读取证**　使用随附手册记录指纹、services.jar 摘要、实际 HOME、Keyguard、当前电源键有效配置。提取所需资源，优先询问厂商是否提供专机 HOME 登记与可条件化电源快捷键。若与本次分析的固件哈希不同，重新分析。
3. **受支持接口验证**　先在 NONE 下验证 HOME 双向切换与恢复，再独立验证电源快捷键的无竞争仲裁。两项分别留存原值和撤销路径。若只能改变全局静态目标又不能维持熄屏、维护暂停与紧急功能，不进入整机部署。
4. **系统级整合须另审**　若厂商必须修改上述 PackageManager/Policy 类，要求同版本签名的 OEM 实现、救援机、可验证的原厂恢复包与 OTA 版本门控；先在备用机验收。系统服务解析失败可引起开机循环或整个系统输入失效。简单禁用 APK 无法回滚系统服务；需由提供方交付并演练独立的禁用及恢复路径。当前没有已审查的新系统模块或框架镜像可部署。
