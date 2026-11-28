# 念晴时钟亮屏返回优化 · P0-9.7.9.3

## 确认范围

| 用户可见指标 | 0.6.15-dev/30 + 1.1.0/2 | 0.6.16-dev/31 + 1.2.0/3 |
|---|---|---|
| 亮屏至时钟窗口取得焦点 | CPDAY10 实测 3050～3200 ms | 待同机测量 |
| Activity 启动时刻 | 亮屏后约 3 秒 | 可分辨 Android 接到启动请求和回调应用的各自耗时 |
| 息屏预热 | 约 62 ms | 沿用暗屏应用预热，增加现存钟面复用 |
| 首次可见钟面、Freeme 闪现 | 用户看到桌面闪现 | 待观察面板 |
| LOCKED、80、时钟可触摸 | 原版真机通过 | 新版有软件回归，待 DSH 确认真实触摸 |

设备数据来自用户本轮反馈。本轮云端完成实现、构建和离线验证。验收要求是短时自然唤醒后用户更早看到钟面且手指可操作；首选目标为亮屏后 2 秒内。生产包仅在独立目录发布，真机继续使用已验收配套。

## 窗口从哪里省时间

原先开发退出会将单任务 MainActivity 的 ClockScreen 分支替换成空 Surface。新版在成功退出独立专机时保留该 Compose 子树，保持逻辑路由为原生桌面。后台停放期间不放置子树、不绘制钟面、不暴露可点击语义，也不以此签发绘制回执。时钟进程仍在且系统交回原 Activity 时可复用已构建内容。进程被回收或系统新建 Activity 时走原有冷启动。预热只操作应用内资源，暗屏期间不会发出 Activity 启动请求。新请求仍须取得真实前台焦点、完成本次绘制，再进入锁定并读取策略。

固件原件在本地核对了完整 SHA-256，公开交付只含结论。framework.jar 为 `2d3548851e2217616cdbb42083b2785c3f230e09d4f05ca009dd4a4c01a3d14d`，services.jar 为 `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468`。framework 的 classes.dex 中，ActivityThread.handleResumeActivity（code item 0x1f49d0）检查 mVisibleFromClient 后才 addView，Activity.performResume（0x1ff47c）包含不可见 NoDisplay Activity 的完成约束。services 的 classes3.dex 中，ActivityStarter.startActivityInner（0x93c78）处理 launchTaskBehind、mDoResume、任务置前及恢复焦点栈的条件。

透明 Activity 仍可能参与窗口焦点与任务切换。NoDisplay 不能提供可直接展示的时钟窗口。后台 task 的避让选项也无法承诺现有单任务在默认物理屏同时保有完整 Surface 与原焦点。采用已有窗口内容复用，Android 继续决定缓存 Surface 的寿命。默认 HOME 仍为 Freeme，显示器点亮和系统合成可能先于受保护的返回请求。即使复用成功，桌面零帧闪现仍需要观察面板。

## 启动前的关键路径

1. **完整唤醒判定。** 默认显示变化驱动，PowerManagerService 的固定只读 Binder dump 使用原有字段解析器，受 950 ms 和 256 KiB 上限约束。系统拒绝或读不到完整字段时才回退至现有有界 dumpsys。实际 DREAMING、切换中或睡眠证据直接保留。采样使用独立队列，前一请求的焦点查验或回执清理不会阻塞新周期取证。只允许一个当前序列进入发送，后续最多保留一个仍有效的完整周期。
2. **身份、前台和窗口。** 两次窗口检查保留完整的前后焦点标识、窗口分类、来电、锁屏、用户与策略校验。常规路径原有两次 pm path、两次 dpm list-owners 和三次 am get-current-user。在可用系统上下文中改为读取当前用户、包及真实管理员，并核对 APK 内容摘要。每次 Binder 检查限时 250 ms，明确拒绝照常拒绝，API 不可用或管理员身份有歧义时走原命令。
3. **受保护的 RETURN 与 COMMIT。** 第一次前台检查通过才发送正式广播。广播返回后并行执行终态 UID 取证与第二轮只读窗口检查。两项通过才发布单次凭据。取证结束晚于检查时再检查一次完整窗口。COMMIT 前再次核对同一焦点、亮屏、模式和时效，且 COMMIT 自身继续做终态证明。AMS 视图的自适应顺序只缓存上次可用的诊断视图，每一条请求都独立证明用户、组件、发送身份和终态。
4. **应用接收。** 固定受保护 Receiver 解析一次票据并保留应用私有凭据、用户、Owner、策略、有效期和消费检查。受理的 COMMIT 记录实际接收及请求 Activity 的时间。已在时钟、持续亮屏、维护暂停、旧请求或前台不稳定时遵从原有拒绝条件。
5. **可比较的结果。** ACTIVITY_START_AT 区分 onCreate / onNewIntent 与已保留的钟面。ACTIVITY_READY_AT 关联本次绘制，CLOCK_FOCUSED_AT 对应实际焦点，LOCKED_CONFIRMED_AT 在应用读回 LOCKED、80 和精确名单后产生。root 最后独立确认焦点与系统锁定。COMMIT 的 AMS 终态取证可晚于应用绘制。所有时间均以 elapsedRealtime 毫秒关联同开机、暗屏和请求。工具逐项保留未知值及失败样本。

## 离线性能对照

| 被测的生产代码 | 旧实现 | 新实现 | 测量条件 |
|---|---:|---:|---|
| 解析 AMS 历史，中位数 | 2.752 ms | 0.741 ms | 同一份 31,345 B、100 条脱敏构造历史，150 次主机 JVM 测量 |
| 上项 P90 | 6.565 ms | 1.600 ms | 相同输入 |
| 完成正式广播后至进入 COMMIT，中位数 | 110.213 ms | 83.552 ms | 主机真实调度，注入 30 ms 证明及 80 ms 检查，7 对样本 |
| 证明慢且需刷新窗口的分支 | 135.273 ms | 142.491 ms | 同上，注入 100 ms 证明及 35 ms 检查 |

以上结果只量化特定代码路径，不能从 3050～3200 ms 中直接扣减。CPDAY10 上候选能否使用 Binder 快路径、AMS 每次等待及系统从 START 到首帧的调度需要分别读取。后续优先按真实数据区分等待前台检查、等待进入 Receiver、Android 启动 Activity 和实际绘制；若 UI 一帧就绘制完但仍看见 Freeme，进一步工作应位于系统合成和唤醒策略。

## 复现与源码

Android 工程使用原有 Gradle Wrapper、development 签名及编译配置。使用本项目签名环境才能生成可覆盖安装的同签名 APK。生产用 KeyStore 不随源码导出。项目根目录执行：

```sh
./gradlew :app:assembleDevelopment :app:testDevelopmentUnitTest
python3 kernelsu/naozho_wake/test.py
python3 kernelsu/naozho_wake/test_system_facts.py --sdk "$SDK36/android.jar"
python3 -m unittest discover -s kernelsu/naozho_wake/perf -p 'test_*.py'
python3 kernelsu/naozho_power_daily/test.py
python3 kernelsu/naozho_wake/build.py --sdk "$SDK36/android.jar" --r8 "$ANDROID_HOME/build-tools/35.0.0/lib/d8.jar" --apk app/build/outputs/apk/development/app-development.apk --out naozho-wake-1.2.0.zip
```

`SDK36` 指向 API 36 平台目录。共享窗口回归另支持在本地私有原件目录运行 `test.py --capture-dir <目录>`。对比脚本 `kernelsu/naozho_wake/perf/compare_proof_scan.py` 可使用源码 Git 历史，或提供 `--baseline-root` 指向解压的 P0-9.7.9.2 源码。回滚源码还原方式见源码包 rollback/README.txt。部署与真机记录步骤见同目录 DSH.md。

## 权限、兼容性和验证边界

比较两个最终 APK 的二进制 Manifest 经 APK Analyzer 解码后的整棵 XML 树，仅 versionCode 和 versionName 有变化。包名、minSdk 23、targetSdk 35、管理员组件、受保护 Receiver、私有启动别名均与 30 版一致。APK v1、v2 验签成功，原版、候选与回滚 APK 的签名证书 SHA-256 为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。沿用原 Room 与 CE/DE 数据格式。Root 的新读操作集中在既有模块进程，无新增系统写权限或对其他应用开放的服务。回滚模块与原始 1.1.0 的归档逐项内容相同，仅配套 APK 的摘要随版本号变更。

固件窗口分析也可对照公开 Android 文档。系统可在后台收回 Activity 或其 Surface；launch-behind 所需的新文档任务语义与本项目已验证的 singleTask 入口不兼容。[Activity 停止生命周期](https://developer.android.com/guide/components/activities/activity-lifecycle#onstop) · [ActivityOptions.makeTaskLaunchBehind](https://developer.android.com/reference/android/app/ActivityOptions#makeTaskLaunchBehind())

## 离线回归结果

- Gradle development APK 构建完成。26 个应用测试套件、163 个测试，失败 0、错误 0、跳过 0。Robolectric Android 35 使用原生绘制验证，模块源码使用 Android API 36 编译。新增的窗口生命周期回归在同一 Activity 实际停放和恢复后验证同一 Compose 节点身份，必须重新绘制并获取焦点才允许 LOCKED。另覆盖停放后进入维护、无预热冷启动、过期回执和重复请求。
- 共享唤醒状态机 24 组、流程断言 27 项、新采样与周期交接断言 30 项、新并发投递断言 18 项全部通过。系统身份快路径回归覆盖 Binder 超时、明确拒绝、管理员组件歧义和 APK pin 错误。时间线工具 7 项通过。
- 生产窗口代码通过两个本地私有窗口采集样本的 49 项交叉检查。既有日常保护测试通过 190 项 JVM 检查、53 项 Freeme 检查、49 项布局字段检查、46 项快照边界检查，以及原生 14 项和 Python 17 项。共享投递证明组件 34 项、平台仲裁 23 项及旧协议 55 项回归通过。
- 合规收据、每次最多一次 RETURN / COMMIT、同一 token 的前后焦点、窗口遮挡、来电、权限拒绝、维护/退出以及实际锁定回读均保留。未安装候选到手机。固件实际 Binder 兼容性、实际 Android 任务复用、完整唤醒到物理首帧/焦点/触摸的时间及桌面闪现仍待实测。
