# CPDAY10 P0-9.6 投递验证修复报告

**结论**　0.2.0 对终态广播记录的缩进作了错误假设。0.2.1 已通过同输入的新旧解析器对照。DSH 保存的摘录不足以追认证书所保护的那一次投递，旧轮正式返回请求为 0。0.2.1 的实体双击、窗口焦点、实际锁定和触摸仍待 CPDAY10 验收。

## 原始失败与回放

核对了 DSH 证据 ZIP 的 CRC 和内部清单中全部 10 个文件的字节数、SHA-256。原始 .attempt 为 346 字节。AMS 在 10:47:28.171 记录探测、.172 入队，应用在 .181 记录拒绝，AMS 在 .184 打印广播完成。保存的 Intent 同时有唯一 action 后缀、相同 id 和显式目标，记录指向 user 0。接收器会拒绝无手势参数的探测，这符合应用设计。进程 10191 是应用 UID；旧摘录未提供这次探测的 callingUid。

完整历史约 12,469 行，上一轮只落盘了按关键字筛选的行。留存的六格缩进正文与系统 DEX 一致，缺少该条历史记录的编号标题、caller 行和同一 manifest 接收器的 DELIVERED 行。附近其他广播的 DELIVERED 或 Atlas 跳过记录不能归到本次探测。旧模块三次采样的内容和时间没有落盘，因此无法追认当时发送 UID，也无法断定某次采样时该记录已进入终态环。

| 同一输入交给两版解析器 | 0.2.0 | 0.2.1 |
| --- | --- | --- |
| 完整合成回执，原测试缩进 | 读出样例发送 UID | 相同 |
| 同一完整回执，仅按固件输出增加一级缩进 | 无回执 | 读出同一样例 UID |
| DSH 的原始 04 摘录，保留原始字节内容和行结构 | 无回执 | 停止，识别到孤立的匹配 Intent，指出缺历史边界、关联发送 UID 和 manifest 终态 |

这项 A/B 对照证明了一个足以产生原症状的代码缺陷。P0-9.5 的 API 28 模拟器曾测试系统对受保护接收器的放行与拒绝，未验证 CPDAY10 Android 16 的 dumpsys 输出格式。

## 固件与代码依据

核对的原厂 services.jar SHA-256 为 `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468`。以下位置均在其 classes.dex，以方法内 DEX 指令偏移计。

- BroadcastController.dumpBroadcastsLocked 识别 history 与 filter --action，并将筛选条件传入队列输出。
- BroadcastQueueImpl.dumpLocked 的 0005–000a 创建 IndentingPrintWriter 并增加缩进，0036 将该 writer 传入 BroadcastHistory.dumpLocked。
- BroadcastHistory.dumpLocked 的 0061 输出带两个前导空格的编号标题，0030、006e 给 BroadcastRecord.dump 的正文前缀为四格。它们还会叠加外层 writer 的缩进。
- BroadcastRecord.dump 输出记录所属用户、Intent 和 callingUid，0084 读取 callingUid，0314 附近输出接收器状态，0387 对 ResolveInfo 输出 (manifest)。历史摘要不包含全部字段。
- 0.2.0 的 DeliveryProof.sender 在行首硬匹配两格标题和四格 Intent、caller、状态，错过记录后统一报 delivery_history_unconfirmed。0.2.1 改为在每个编号终态记录内部按相对层级读取。
- 系统对接收器的 STATUS_BAR_SERVICE 检查仍生效。发送路径、用户、目标组件和应用 APK 均沿用原实现。终态投递证明适用于本次发送，不授予或推导通用权限。

## 新判定与诊断

每个独立快照必须同时包含精确 action、Intent identifier、显式时钟 Receiver、user 0、唯一 caller UID、唯一 #0 manifest 接收器及 DELIVERED。正式请求和探测使用各自的 identifier，实际发送 UID 须相同。拒绝、冲突、其他用户或组件立即停止。孤立 Intent、另一条广播的字段、广播退出码、应用拒绝日志均不能补足回执。

首次立即读 action 过滤视图，必要时分别等待 200、600、1000 ms 后再读取。最后一次为带 -a 的完整历史视图，限 4 MiB；定向视图限 512 KiB。最多四个只读快照，不混拼快照，不重复发送。每次输出 stage、trace、采样序号、来源、经过毫秒数、上一轮结果、相关记录数、唯一 ID 匹配情况、用户、接收组件、发送 UID、接收状态与缺失字段。命令超时和超过输出上限单独报错。设备完整广播历史不写入 .attempt。

## 验证范围

| 离线测试组 | 通过 |
| --- | ---: |
| 模块既有输入、保护、发送与回执行为 | 55 |
| 投递解析专项，包括相对缩进、原摘录结构、缺字段、冲突、迟到及读历史回退 | 26 |
| 电源按键序列状态机 | 23 |
| DSH 工具，含已升级续测、旧记录保护、签名校验与单次投递顺序 | 17 |

共 121 项通过。以 JDK 17、API 36 android.jar 和 Build Tools 35.0.0 d8 实际构建模块两次，字节相同。检查 ZIP/DEX、CRC、脚本语法与执行位。另用两个版本的实际解析器回放原始摘录和合成对照。未安装模块或执行真机 Return。

保留 com.naozho.clock 0.6.13-dev / 28。aapt2 读取旧交付 APK 包与版本，apksigner 核验其 v2 签名和唯一签名者。APK SHA-256 为 `8bcf50a524f58b6c8180d699f47a18fd096d94b7b12d737d1a60710d189597d4`，证书 SHA-256 为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。核验的是云端原交付文件；下次获批续测时工具还会实际拉取已装 APK 再验。

## 变更与交接

- kernelsu/naozho_power 内的 DeliveryProof.java、Board.java、module/module.prop、test.py、PowerTrialTest.java、DeliveryProofTest.java。
- tools/p095 内的 cpday10_joint.py、test_resume.py、本报告和 P096-DSH.md。
- 接收器和应用代码无变化。模块没有开机服务或系统挂载。公开包只含项目源码、可执行模块、工具、说明、测试结果和校验清单。用户提供的原始日志、固件和旧基线保留在私有分析环境。
