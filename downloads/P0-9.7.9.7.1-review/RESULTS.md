# P0-9.7.9.7.1 离线修复及真机验收状态

## 本次进展

将待接入的 watcher 生命周期移到 KernelSU 的 late_start service.sh。源码里的固定只读 worker 通过独立会话、单例文件锁和阻塞式文件事件监听工作，保留对停用、卸载标记及进程退出的处理。核对的是 KernelSU v3.3.1 标签中的模块文档。[官方启动阶段](https://github.com/tiann/KernelSU/blob/v3.3.1/website/docs/guide/module.md#boot-scripts)

已复核 naozho_wake 1.5.0 的真实生产者。日志在 /data/adb/modules/naozho_wake/events，超过 32768 字节后轮到 events.1。最早的 DARK_OBSERVED_AT 和 WAKE_CANDIDATE_AT 只有 boot/dark 身份，正式唤醒后才有 epoch；正式投递另以 request 和实际发送 UID 关联。不能在 DARK 自创正式 epoch。CLOCK_FOCUSED_AT 可能早于时钟首帧。正常撤幕应绑定本周期已核对的正式 HANDOFF_COMPLETE，拒绝、停用、状态不确定或可见超时则走故障撤幕。单独的 MASK_REFUSED_AT 表示唤醒模块自身对既有遮罩接口的能力判断。

可见计时源码将 DARK 准备和可见期分开。息屏任意久不会消耗可见预算。相同窗口取得显示 ON、可见和硬件帧提交三项证据后开启 5000ms；重复回调不延长。请求显示后另给 1500ms 等待窗口回执，收不到即放弃并要求撤幕。1500ms 是本次离线设计的上限，仍须结合原 APK 的回执和时钟基准核对。可见超时既要由窗口拥有者本地执行，也要能在 watcher 停止后生效。已报告的原 APK 五秒行为未经云端重测。

修复了一个可独立复现的问题。原普通应用判定可把单独获得焦点的 com.naozho.mask 当作普通来源；对应生产分支现在明确拒绝。没有新增基于包名放行未知窗口的例外。另一处是整合阻塞，原 wake 守卫多次核对页、Window Token、ActivityRecord、任务号及 UID。独立黑屏若成为焦点，或者遮挡了原浏览器，守卫可能抛出 focus_transition、wake_task_transition 或额外窗口拒绝。需要在授权展示前保存真实来源，在同一周期用实际黑屏组件、已验证包签名与 UID、真正的 Window Token 关联，并依然能识别新出现的来电、认证或权限界面。当前未建立这种关联。重启 watcher 或仅在窗口列表中跳过一个包名均不能证明浏览器来源仍有效。

## 可交付范围与阻塞

在工作区、历史归档、附件、Git 引用与已有发布中核对到时钟 0.6.20-dev / 35 和 wake 1.5.0 / 7，未取得单独的 com.naozho.mask 1.0.0 APK、naozho_mask 1.0.0 模块及其 SHOW/HIDE 实现。上一版源码中的 OEM 窗口原型属于另一实现。这次交付是可编译的 watcher 与计时器源码、窗口判定修复和离线工具；没有可以替代现有黑屏组件的 KernelSU 安装包。没有重新打包时钟或唤醒模块。将 DSH 已保存的两个黑屏原件交付 Codex 即可继续，已有对应源码也可一并提供。

初次集成前应在原件中逐项确认真实 Activity/receiver、SHOW/HIDE 授权及窗口引用、启动标志和 taskAffinity、界面可见/撤下回执、计时所用时钟、停用/卸载及原始回滚路径。如果原 Activity 在屏幕关闭时创建就开始计时，应在原 Activity 修复计时，而不能只延后 Root 的第二个计时器。如果黑屏单独取得焦点，原应用是否仍可验证取决于真实窗口结构，不能提前记为通过。

## 本轮离线核验

| 项目 | 状态 |
|---|---|
| 时钟与 wake 回滚原件 | 已从上一固定提交重新下载并逐字节比对，保留原件 |
| 真实 wake 事件格式 | 12 个定向回放用例通过，覆盖轮转、乱序、重复、截断、UID 不匹配及缺少正式接管 |
| 可见超时 | JDK 17 以 Java 8 目标编译，63 项断言通过，包含 61 秒 DARK、重复可见回调、超时、停止与旧周期回调 |
| 窗口来源修复 | 从源码编译 WakeOrdinaryTest 并执行，新例验证聚焦的黑屏不能单独作为原应用；真实窗口归属仍需配对 |
| 原件核验工具 | 两项离线用例通过；尚未取得黑屏原件，故未核验其证书和 SHA |
| KernelSU 生命周期 | 12 个 Linux 进程用例通过，实际运行监督进程及事件 worker。结束启动进程组、并发启动、子进程异常退出、停用和移除均有针对性检查；真实日志游标的轮转、拒绝及截断测试通过；Android NDK r27d 编译出 arm64 PIE |
| 真机全链路 | 未运行。云端没有 USB 设备总线或已配置的本机 ADB 通道，无法读取当前版本、签名、UID、Owner、锁定及实际屏幕状态 |

## 恢复文件

这两个原件在本轮均从固定发布重新下载，与保存文件逐字节一致。无需因本轮离线工作重装其中任何一个。

| 固定发布原件 | 字节数 | SHA-256 |
|---|---:|---|
| [com.naozho.clock 0.6.20-dev / 35](https://raw.githubusercontent.com/shfjq/naozho/7f9c828dbbd1037ae8873c56b017547d7b00ede2/downloads/P0-9.7.9.7/naozho-0.6.20-dev-wake.apk) | 11506206 | `25ab5f89f19912ee9521fa5e1b18c9d2348677c7eb3d46cb54bf5f52373df559` |
| [naozho_wake 1.5.0 / 7](https://raw.githubusercontent.com/shfjq/naozho/7f9c828dbbd1037ae8873c56b017547d7b00ede2/downloads/P0-9.7.9.7/naozho-wake-1.5.0.zip) | 59370 | `8623b7db3cabf263649641ee5f9166ad04101b32d36b78f6b3bd2a8cb59aca39` |

## 现场记录

| 唯一一次浏览器唤醒 | 本轮结果 |
|---|---|
| 真机 KernelSU 启动 watcher，断开全部 ADB 后仍为同一实例 | 待测 |
| 息屏超过 5 秒，浏览器内容区被遮挡，过渡期间触摸被消费，系统栏实际可见性 | 待测 |
| 同一 epoch 的 RETURN 和 COMMIT 各一次，真实首帧、系统焦点、LOCKED + 80 及仅时钟允许 | 待测 |
| 成功后撤幕并可触摸，退出返回原浏览器任务 | 待测 |
| 实际端到端耗时 | 无本轮真机时间戳 |

已报告的黑屏 Activity 可覆盖 BASE_APPLICATION 内容区域。系统栏覆盖、整段无闪现和撤幕时机均需实机证据。[单次验收与回滚手册](DSH.md)
