# CPDAY10 P0-9.3 云端检查点

北京时间 2026-11-26。手机可离线。源码分支 p0-9-system-clock，提交 `4f490c0f269e2927c6beee358223776d17e9eb57`。完整仓库已在原云端工作区打包，并通过从备份重新克隆和 git fsck 的恢复验证。

## 结果

- 开发包 0.6.12-dev / 27 已构建、验签。原包名、签名、Device Owner 组件保持一致。两份 APK 已从 GitHub 固定提交实际回下载并逐字节比较。
- 应用自动化 139 项、产品按键时序 21 项、既有采集/手势模型 10 项、既有开机模块 12 项均通过。development Lint 零错误、10 项警告。
- 标准 Android 16 云端模拟器：已连上云端虚拟设备；系统完成启动前 system_server 发生重启，安装器返回 device is still booting。本次未取得运行时 HOME、冷启动首屏或实体电源验收结果。
- 专机主屏已具备从系统 HOME 启动的应用侧实现；受控条件下能在用户存储开放前点击切换时间和日期。已实现系统按键仲裁核心和可运行的主机测试。候选 APK 的实体快捷入口保持禁用。
- 原厂固件的紧急拨号豁免有一条依赖 KEYGUARD(32)；flags=80 不含该位。SOS 是否能抢占已经锁定的时钟，仍需系统集成和专项验证。

## 续做

第一步是在同板开发资源可用时接入主屏与系统按键 Host，并验证能独立恢复原系统。第二步是在隔离电话环境中验证紧急抢占。第三步才是另行批准的 CPDAY10 首屏、实际双击、锁定触摸、退出与硬件验收。目前没有需要在线手机执行的事项。

审查 ZIP 内包含设计、DSH 验收/回滚手册、源码差异、平台库、可用 JDK 运行的 tests/station-power-tests.jar 和测试摘要。原云端检查点位于 /workspace/shared/downloads/P0-9.3-checkpoint/，入口文件为 RESTORE.md。

## 已核验安装包

- 11,476,890 字节，SHA-256 `06ecef2215bb384515b46edce71a0513b8bb5494897319342201a85735926d16`。[naozho-0.6.12-dev-station-review.apk](https://raw.githubusercontent.com/shfjq/naozho/4520bab7f4e290f118a0a3ac20f144b1d325998a/downloads/naozho-0.6.12-dev-station-review.apk)
- 11,467,767 字节，SHA-256 `8f6a7fda0b6eb95d8e1ef396c052f3be23d40481cf2156bfb690257441acc8f8`。[naozho-0.6.9-rollback-vc27.apk](https://raw.githubusercontent.com/shfjq/naozho/4520bab7f4e290f118a0a3ac20f144b1d325998a/downloads/naozho-0.6.9-rollback-vc27.apk)
