# P0-9.7.9 念晴时钟 · 完整唤醒返回

本候选绑定 CPDAY10 API 36 的已审查 services.jar 和指定时钟 APK。KernelSU 启动独立的 app_process；时钟、WakeProbe、Freeme 的 Activity 生命周期均不负责维持观察。应用增加单独的唤醒协议，因此从 0.6.13-dev/28 更新为 0.6.14-dev/29。包名、签名及现有管理员组件延续原项目。

## 从显示事件到时钟

1. 模块初始关闭。用户启用后，启动器取得进程文件锁，检查本机、Enforcing、固件、APK 摘要与 user 0 的 Device Owner。显式初始化 Android 主 Looper、ActivityThread 和系统 Context，用 DisplayManager 注册默认显示器的状态、加入和移除回调。私有框架初始化路径受固件约束，发生拒绝时记录具体阶段。正常等待没有定时心跳。
2. 观察器先建立本次进程的亮屏基线。真实 OFF、非交互 DOZE 或 DOZE_SUSPEND 建立暗屏证据。ON 回调后在工作线程读取有大小、时间上限的 power 服务诊断。复用 WakeProbe 的 WakeCycle 和 PowerEvidence：默认显示组、Awake、转换结束、isInteractive、上一对睡眠及唤醒 uptime 必须一致。200 ms 初查；必要时再等待 400 ms 收敛；超过 3 秒放弃。DREAMING、AOD 脉冲、未知显示、丢失显示器或过时回调不会产生有效返回。进程在暗屏中首次启动时，须先建立亮屏基线再观察下一周期。
3. 一次完整唤醒产生一个内核 boot UUID、暗屏 elapsedRealtime 毫秒及序号组成的 epoch。上电持续时间含休眠；配对系统 Power 历史使用 uptime，两种时钟分开。重复 ON 不产生新 epoch。真实唤醒来源无需猜测；从进程外接收通知只点亮 AOD 时没有正式请求。
4. Root 核对 user 0、独立部署、上次模式变化时间、窗口焦点、可见窗口、锁屏、通话及 Lock Task。沿用 1.0.4 的完整窗口解析和页面范围。Freeme、设置首页、既有已审查页面可返回；正在响铃的专门界面、通知面板、凭据页、电话、无法归类的应用页面或遮挡均保留当前交互。每种正常唤醒来源都使用同一判断。
5. 每个模块进程首次需要投递时，向已有权限保护的显式 Receiver 做一次无副作用权限探测，核对 AMS 实际投递身份。每个有效周期至多一份 WAKE_EPOCH_RETURN 正式信封。接收器此时不显示界面。Root 确认 AMS 对本次唯一编号、实际 UID、user 0、精确组件的 DELIVERED 记录，再检查当前电源、窗口和模式，通过固定 run-as 操作以时钟应用 UID 原子发布私有收据，最后发送同一请求的 COMMIT。正式信封和提交回执使用不同的 AMS identifier。显示状态失效或模块停用会撤销收据。
6. 时钟核对请求号、boot_count、boot_id、epoch、单调时间戳、12 秒有效期、source、sender_uid、私有收据、锁屏和音频状态；系统提供发送方身份时同时匹配 UID。每个暗屏边界最多一次持久认领。只有恢复到私有 Activity 入口并获得真实焦点后才进入时钟模式。上一轮开发退出及维护暂停的模式时间边界能拒绝迟到请求。
7. 取得焦点、成功调用既有专机逻辑并读取系统实际 LOCKED、flags=80、精确单包允许名单后，时钟写入本次 request_id 确认。Root 在有限次数的只读回查中独立验证当前窗口及前台 Activity 都是时钟、系统仍 LOCKED，才记录 CLOCK_FOCUSED。真实触摸由 DSH 与用户现场验证。

## 模式、进程及故障处理

| 当前情况 | 行为 |
|---|---|
| ANDROID；经历新暗屏及完整交互唤醒 | 检查窗口与系统身份，提交一次正式请求。 |
| 当前已是锁定的时钟 | 跳过投递，保留正常电源键息屏/亮屏。 |
| 开发退出到 Freeme | 屏幕持续亮起期间不会重新拉回。 |
| 管理员维护暂停 | 应用的 CE 状态用于授权，DE 提示控制订阅。取消显示监听，复位所有历史周期；同一个进程只等待配置文件事件。恢复独立部署后重新订阅并建立新基线。如需连配置监听也停止，模块 Action/stop.sh 可完全停用。 |
| 现有实例在后台或时钟进程已被普通回收 | 受保护接收器经私有别名交给 MainActivity；沿用 singleTask 和 onNewIntent。独立策略仍启用、系统回到 NONE 且前台安全时，下一次新唤醒也能恢复丢失的时钟任务。 |
| 一次提交未确认、时钟崩溃 | 同一周期不重发。同次开机连续三次正式提交未确认即停止新的提交，手动重新启用可复位。观察器进程自身失败最多额外重启两次，退避 2 秒和 8 秒，重启时丢弃旧周期。 |
| 设备重启 | 既有 naozho_boot 处理开机请求；新模块在 boot-completed 阶段恢复用户的启用选择。初次亮屏不触发一份额外返回。开机第一屏体验另行验收。 |

## 权限与数据

- KernelSU 管理目录仅 root 可访问。固定读取 boot UUID、boot_count、固件及包摘要、Owner、显示及 power 状态、前台/可见窗口、通话数字状态和应用现有部署字段。框架层通过有界系统命令取样，不给 WakeProbe 保留 DUMP。
- 正式投递只面向 user 0 的 com.naozho.clock/.mode.ConfirmedPowerReceiver；系统原有 STATUS_BAR_SERVICE 权限保持。用户应用没有 root 命令入口。时钟更新的最终清单未增加组件、权限或网络能力。
- 持久写入限于模块的启用令牌、进程锁、失败预算、轮转日志和时钟私有的收据、锁定确认、模式状态。窗口和 power 原文只在 RAM 中短暂存在。events 达到约 32 KiB 后轮转，仅保留一个旧文件。日志进入的是分类、单调时间、请求编号及短原因。
- 模块没有输入设备访问、按键注入、网络上传、WakeLock、Secure 设置写入、挂载替换或策略写入。既有时钟作为 Owner 使用早已验证的独立 Lock Task。
- 待真机确认的接口包括 KernelSU app_process 上下文与显示监听、root 域读取 power、Atlas 对新动作的真实投递，以及 Android 对从后台接收器恢复 Activity 的处理。原有的 38 分 28 秒观察记录属于 WakeProbe。新模块的功耗及该时长的存活表现尚未测量。

## 离线构建

使用 JDK 17，Android SDK 35 编译时钟，API 36 的 android.jar 编译模块。构建工具 35.0.0 的 R8 保留唯一 main 并移除共享目录里不可达的旧按键及系统设置代码。DEX 最低生成级别为 34，安装和运行均检查 API 36。应用必须用设备上现有签名构建。

```sh
./gradlew :app:assembleDevelopment :app:testDevelopmentUnitTest
python3 kernelsu/naozho_wake/test.py
python3 kernelsu/naozho_power_daily/test.py
python3 kernelsu/naozho_wake/build.py --sdk "$ANDROID_HOME/platforms/android-36/android.jar" \
  --r8 "$ANDROID_HOME/build-tools/35.0.0/lib/d8.jar" \
  --apk app/build/outputs/apk/development/app-development.apk --out naozho-wake-1.0.0.zip
```

部署、功能覆盖和恢复步骤见随包 DSH 手册。
