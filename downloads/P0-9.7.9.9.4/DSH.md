# CPDAY10 0.6.24-dev / 39 定位候选验收

云端未连接 CPDAY10。先在本机保存当前缓存和模块配置，核对文件 SHA-256、原 APK 签名和设备实际 UID/Owner。正常退出时钟并停用 wake，然后按 KernelSU 原管理流程升级 1.5.6 / 13，核对实际生效版本，再以 adb install -r 覆盖安装 0.6.24-dev。时钟数据和 Owner 应继续保留，安装后实际回读确认。

## 一次真实定位

1. 在已授权的 Android 正常设置中结束 Mock Location 测试与测试 provider。确认粗略定位授权和定位服务状态。若权限已被拒绝，记录拒绝并保留该选择。
2. 手机放在实际可取得定位的位置，主动点天气自动定位。核对实际物理城市与设备返回的 provider、原位置时间、accuracy、elapsedRealtime 年龄和 mock 状态。
3. 新诊断在应用私有 shared_prefs/clock_location_evidence.xml。已授权的调试应用可通过 run-as 在本机读取。它含位置信息，仅保留本机，不提交公开仓库。
4. 只有被接受的设备位置、城市反查与钟面城市一致时才能记为通过。旧城市缓存、天气 API 成功或 am_rc=0 都不能代替位置证明。失败时保留旧天气并标记位置待验证。
5. 若实际自然移动条件允许，移动后重新定位并核对新坐标、城市及天气。无法移动则记为待测。
6. 让现有 Root 调度器自然执行一次。核对 Root task 与应用位置/天气日志 task 一致，位置接受、天气成功及新 updatedAt 后再检查下一次任务。Android 后台位置返回空或超时时记为未通过，不将旧位置写成最新成功。

本机只读命令示例，先填入已授权的设备标识。

    adb -s SERIAL shell dpm list-owners
    adb -s SERIAL shell cmd package list packages --user 0 -U com.naozho.clock
    adb -s SERIAL shell run-as com.naozho.clock cat shared_prefs/clock_location_evidence.xml

## 停用和回滚

保留原始 38 APK 与原始 1.5.5 模块。先正常退出时钟，再通过原维护流程停止唤醒及天气进程。恢复 APK 可用 adb install -r -d naozho-0.6.23-dev.apk。固件拒绝降级时停止回滚并保留数据/Owner。降级成功后通过 KernelSU 管理器恢复原始 naozho_wake-1.5.5-original.zip，按提示处理重启，再核对实际版本、UID、Owner 和既有天气调度。卸载模块使用原管理器，原卸载钩子会释放天气 wakelock。新增定位诊断为私有文件，旧 APK 不使用它。

收到的完整大包超过下载工具限制。若需进一步核对原始定位记录，只需从已保存的大包取出既有小日志，无需重做全量采集。
