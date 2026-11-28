# CPDAY10 全局唤醒候选 · 安装、单次浏览器验收、停用与回滚

候选为 com.naozho.clock 0.6.20-dev / 35、KernelSU 模块 naozho_wake 1.5.0 / 7。云端未连接手机。手机可能仍在使用 0.6.18-dev 和 1.3.1；0.6.19-dev 和 1.4.0 曾作为候选发布。历史 UID 10191 只是对照值。请用安装前的实际读取结果填写本机记录。

## 在电脑上准备

下载可在空目录中一次完成。把本版发布页给出的 40 位固定提交贴入以下 PowerShell。命令仅从项目公开仓库下载到电脑，不连接手机。

```powershell
$rev = Read-Host '本版 40 位 GitHub 发布提交'
if ($rev -notmatch '^[0-9a-f]{40}$') { throw '需要完整提交号' }
$base = "https://raw.githubusercontent.com/shfjq/naozho/$rev/downloads/P0-9.7.9.7"
if ((Get-ChildItem -Force | Measure-Object).Count -ne 0) { throw '请在新的空目录运行' }
Invoke-WebRequest "$base/SHA256SUMS.txt" -OutFile SHA256SUMS.txt
foreach ($line in Get-Content SHA256SUMS.txt) {
    if ($line -notmatch '^([0-9a-f]{64})  ([a-zA-Z0-9][a-zA-Z0-9._-]+)$') { throw '无效清单行' }
    $want = $Matches[1]; $name = $Matches[2]
    Invoke-WebRequest "$base/$name" -OutFile $name
    if ((Get-FileHash $name -Algorithm SHA256).Hash -ne $want) { throw "校验失败 $name" }
}
```

从同一固定 Git 提交下载 wake97_dsh.py、timeline.py、tap-witness.html、SHA256SUMS.txt、候选与两对回滚 APK/ZIP。放在同一目录。使用 Python 3.9 或更高、Android SDK Platform Tools 和 Build Tools（apksigner）。新开 PowerShell，进入该目录。无参数运行部署工具会离线校验三对文件的 SHA-256、APK v2 签名及模块内绑定的 APK 摘要；完整目录中其他文件可对照发布清单。

```powershell
py -3 wake97_dsh.py
adb devices -l
$dev = Read-Host '粘贴本机已经授权的 CPDAY10 连接标识'
$env:ANDROID_SERIAL = $dev
py -3 wake97_dsh.py status --serial $dev --save before.json
```

status 仅读取。它在本地临时拉取已安装的 base.apk，验证证书，随后删除临时副本。输出包含应用版本及 SHA、实际 UID、user 0 的 Owner、锁定状态、策略、前台大类与任务号、KernelSU 和已生效的模块版本、运行进程数量，以及是否有待重启的更新。未知字段保留为 null 或 unknown。before.json 只保存至本机。若没有无线 ADB 授权或手机离线，先保留发布包，设备状态记为待核对。

保存 before.json 后保留原文件。工具可识别三个已发布组合：0.6.18-dev / 33 + 1.3.1、0.6.18-dev / 34 同签名回滚版 + 1.3.1、0.6.19-dev / 34 + 1.4.0。若实际版本、签名或 APK/模块绑定不匹配，记录 status 后停止部署。本机仍可正常使用当下的时钟版本。

## 经批准后部署

1. 保留 naozho_boot、ADB-Enabler、Device Owner、现有默认桌面、系统凭据和应用数据。日常电源键模块继续关闭。记录维护暂停状态。若应用当前为 LOCKED，用已经验收的正常「开发退出」回 Android。
2. 在同一个 PowerShell 运行以下命令。stop 停用本项目的唤醒控制器。等状态显示 NONE、observer_count=0、armed 未设置，再安装。每次命令完成后检查结果。如安装后 APK 或模块阶段失败，让观察器保持关闭，保存本机报告，使用下文的回滚步骤。
3. 工具通过 KernelSU v3.3.1 官方 ksud 模块安装接口写入已核对的 ZIP。APK 使用同签名覆盖安装。安装阶段结束后，手动正常重启一次以启用 KernelSU 的更新。工具不会自动重启。
4. 使用既有无线 ADB 重新连接，端口如有变化，更新 $dev 和 $env:ANDROID_SERIAL。先读 status，核对 versionCode 35、模块 1.5.0 / 7、待安装标志已清、证书与 UID、Owner 未变。确认独立专机已配置、当前普通 Android 可操作，使用 start 明确启用观察器。
5. 这版不需要进入无障碍设置。若上个候选启用了旧服务，在安装后以实际组件状态为准；保留其他应用既有的无障碍配置。出现系统窗口权限或 SELinux 拒绝时，保留该次拒绝证据，不授予额外权限或调整系统策略。

```powershell
py -3 wake97_dsh.py stop --serial $dev --apply
py -3 wake97_dsh.py status --serial $dev
py -3 wake97_dsh.py install --serial $dev --before before.json --apply
# 上一步成功后手动正常重启；无线连接重建后继续。
py -3 wake97_dsh.py status --serial $dev --save installed.json
py -3 wake97_dsh.py start --serial $dev --before before.json --apply
py -3 wake97_dsh.py status --serial $dev
```

start 重复执行时不会切换已启用的开关。armed 表示启动请求；观察到一个实际运行的观察进程和本次 observer_ready 才记录已就绪。若模块意外退出，不重复触发。维护暂停、正常开发退出和本阶段的主动停用分别记录。

## 本候选的显示能力边界

本版使用 Root 守护进程核验 FULL_WAKE 和来源任务，在受保护的 COMMIT 获得证明后，由 Root 经 ActivityTaskManager 请求恢复原时钟。独立全屏黑幕的窗口、输入通道和安全层级须全部获得固件支持。当前候选会记录该能力未满足，并继续正式启动，不会把未知层级的系统窗口盖在权限、来电或安全界面上。

每次记录分开核对 ROOT_MASK_CAPABILITY、MASK_REFUSED_AT、ACTIVITY_REQUEST_AT、ROOT_ATM_ACCEPTED_AT、CLOCK_FOCUS_LOCK_VERIFIED_AT 和 HANDOFF_COMPLETE。日志中出现 mask=not_submitted 时，该次没有提交前置黑层。如果 ATM 请求后画面发黑，可能是 Android 自己创建的启动窗口，或者仍在屏幕点亮过程中。将观察到的黑色、它出现的时刻和能否归因分别记录。浏览器已闪现时应如实判定首屏目标失败，即使随后时钟可以操作。

## 一次真机浏览器验收

先在普通浏览器打开附带的本地 tap-witness.html 或等效无隐私页面。页面切实位于前台，轻触一次使计数变化，记下实例号、计数、任务号。关闭输入法及真实弹窗。建议用独立摄像设备记录屏幕和手指，避免系统录屏产生额外窗口。允许观察不到的项保留为未知。

1. 自然息屏一次，再按实体电源键正常唤醒一次。记录物理面板首次发光、首个可辨认画面、时钟首帧和触摸可用时刻。完整检查从亮屏到正式时钟的录像片段。过渡中哪怕浏览器仅出现一帧，也记录闪现。
2. 若黑幕长到足以点按，在录像中向原浏览器计数按钮位置点击一次。若时钟直接出现或黑场太短，遮罩触摸项记未测。黑色外观本身无法证明面板已经点亮、系统合成成功或实际触摸被拦住。
3. 时钟出现后，点「开发退出」并点「取消」，确认两次点击都得到相应界面反馈。读一次 status，核对真实焦点为 clock、LOCKED、flags 80、clock_only 为 true。必要时在本地核查系统 WMS、ActivityManager 和 DPM 读回值。保留证据缺口。
4. 正常开发退出。屏幕持续亮着，在最近任务回原浏览器，比较任务号、实例号和计数。黑场中确实点过且同一实例计数不增，是本次输入未穿透的证据。页面发生重载、触摸时刻不确定或任务变化，应分别如实记下。
5. 只收集这一轮已有的时序日志。保存本地新文件。按相同 wake_epoch_id、request_id 核对 FULL_WAKE、RETURN 和 COMMIT 的发送及 DeliveryProof、首帧提交、实际焦点、LOCKED、遮罩释放、HANDOFF_COMPLETE。任何请求发送或本地帧回执都无法单独证明物理第一帧。完成这一次后停止；失败定位到对应环节。

```powershell
py -3 wake97_dsh.py status --serial $dev --save locked.json
# 回到浏览器后
py -3 wake97_dsh.py status --serial $dev --save returned.json
py -3 timeline.py --root-atm --collect --save-logs local-wake97.log --summary --write-field-sheet witness97.csv > software97.json
# 在本轮 CSV 行填写现场观察，不确定的字段留空或填 unknown
py -3 timeline.py --root-atm --logs local-wake97.log --summary --field-sheet witness97.csv > reviewed97.json
```

在输出的 global_return 查看 RETURN/COMMIT 各自一次及最终回执；root_activity_start 核对启动守卫、请求、ATM 受理、独立核验四阶段。independent_early_mask 单独记录前置遮罩能力及拒绝阶段。窗口使用 Root 启动不会自动获得可拦截触摸的前置黑层。资料缺少软件时间戳、可识别录像帧或手指反馈时，在报告中保留未知。只有客户端和系统的单调时钟可以直接互相比较；物理录像按同一视频的第一亮帧计时。

### 真机实际效果记录

| 现场项目 | 部署前的本轮结果 |
|---|---|
| 浏览器为实际来源，任务号及页面实例 | 待测 |
| 首个物理画面、原应用是否闪现 | 待测 |
| 黑幕期间点击及原页面是否响应；失败后是否恢复 | 待测 |
| 一次正式 RETURN、一次 COMMIT，同一发送身份及请求 | 待测 |
| 正式时钟硬件帧、焦点、LOCKED + 80、唯一允许包、撤罩 | 待测 |
| 实际触摸反馈、亮屏至首次可操作的毫秒数 | 待测 |
| 退出后原浏览器任务保留、页面实例和计数 | 待测 |

## 独立停用、卸载和回滚

黑幕卡住时，先用已批准的 ADB 运行 stop。即使签名验证工具暂不可用，紧急停用仍可使用。核对 armed 已撤和进程消失，观察实际显示及触摸恢复。若调试连接也不可用，使用 CPDAY10 既有 KernelSU 恢复入口禁用 naozho_wake 后正常开机。永久移除本模块使用 uninstall。该命令只给该模块加移除标记，下次正常重启生效；不会卸载具有 Device Owner 的时钟 APK。

```powershell
py -3 wake97_dsh.py stop --serial $dev --apply
# 只在决定卸载而非回退时执行
py -3 wake97_dsh.py uninstall --serial $dev --apply
```

回退时先停用观察器，正常开发退出到 NONE，保持原模块仍安装且未标记移除。使用保存的 before.json 选回当时的 0.6.18 / 1.3.1 或 0.6.19 / 1.4.0 组合。两对回滚 APK 都使用 versionCode 35，便于同签名覆盖安装且保留数据；原生产签名、版本名及模块绑定关系都需要复核。回滚工具不会重置设备或清除管理状态。若回退中途断开，重新获取一次 status，核对已完成的步骤后再决定是否继续。

```powershell
py -3 wake97_dsh.py rollback --serial $dev --before before.json --apply
# 核实回退配对已写入，手动重启，再次核对
py -3 wake97_dsh.py status --serial $dev --save recovered.json
```

按 before.json 中原有状态恢复。原先已主动停用的模块继续关闭；若原来正常启用，使用原版本已验收的 KernelSU Action。原来的 1.4.0 若曾使用可选黑幕服务，恢复该功能另遵循该版授权流程。0.6.18 / 1.3.1 沿用该版本的原有操作。录像、设备绑定摘要、实际应用和窗口日志只留本机。
