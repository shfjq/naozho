# P0-9.7.9.8.1 身份绑定与测试

| APK | versionCode | APK SHA-256 |
|---|---:|---|
| 0.6.20-dev 原始 APK | 35 | `25ab5f89f19912ee9521fa5e1b18c9d2348677c7eb3d46cb54bf5f52373df559` |
| 0.6.21-dev 原始 APK | 36 | `f1b2580e00d34f1dfe15b8a043c22f21a3dc561a9788970b6f30bae380fd2db5` |

任务中的旧 APK SHA-256 少了一位。表中取自实际原版 APK，且与发布模块 1.5.0 的绑定一致。两份仍为 com.naozho.clock。aapt2 确认二者均可调试，apksigner v2 验证均通过。单一当前签名证书 SHA-256 为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。

## 代码核对

- 1.5.0 启动时读取 clock.sha256，随后在预热和唤醒守卫中沿用该摘要。DailyBoard.verifyBase 会在 base.apk 实际摘要不等时拒绝并报告 apk_changed。
- 1.5.1 通过只读身份表核验包名、版本名、版本号和整包 SHA-256，通过 Android PackageManager 验证当前签名、user 0 安装 UID 和两个接收器的组件状态、UID 与权限。DevicePolicyManager 验证 Device Owner 及活跃 ClockDeviceAdmin。身份读不全时拒绝。
- 守卫和投递分别验证同一份已安装身份。进程启动、预热、首次权限探测、RETURN、私有收据、COMMIT、Activity 启动及最终确认均受约束。请求期间版本、路径或 UID 变化时放弃本次请求。下一完整唤醒可选择另一个已批准版本。
- 启动日志中的 app_uid 表示安装 APK 的 UID。RETURN 和 COMMIT 的发送 UID 仍来自现有 AMS DeliveryProof，保留 0 或 2000 的原有约束。每个唤醒周期只提交一次正式 RETURN，COMMIT 仍绑定同一请求。窗口和首帧、焦点、锁定验证仍由现有逻辑负责。

## 离线结果

| 项目 | 结果 |
|---|---|
| 两份原始 APK 的版本、整包摘要和 v2 证书 | 构建时实际核验通过 |
| 35 → 36 → 原始 35 | 用实际 APK 字节变更安装路径，调用生产身份验证及 WakeDispatch 流程，三个阶段均各发一次 RETURN 和 COMMIT |
| 未登记版本、版本与文件交叉、修改文件、错误签名、错误 UID | 生产验证拒绝 |
| RETURN 之后切换版本、伪造发送 UID | 拒绝继续 COMMIT 或启动 |
| 新身份与投递测试 | 19 项断言通过 |
| Device Owner 组件与 Binder 读回降级 | 定向测试通过 |
| 既有 WakeFlow 与 WakePipeline | 33 项及 18 项断言通过 |
| KernelSU 模块 ZIP | JDK 17、API 36 编译接口与 Build Tools 35.0.0 R8 构建通过 |
| CPDAY10 真实无损覆盖、ADB 降级、实际 Owner/UID 与触摸、两版实际唤醒 | 待 DSH 真机验证 |

主机验证器使用真实 APK 字节，并模拟 Android PackageManager 的身份输入。运行时仍须从 CPDAY10 PackageManager 取得签名、UID、组件和 Owner。测试期间未连接设备。
