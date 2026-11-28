# CPDAY10 P0-9.7.9.5 · 单次物理唤醒验收

本轮看三个画面：屏幕点亮时看到什么，桌面钟面与正式时钟之间是否断开，正式时钟能否操作。只安排一次自然息屏与唤醒。审核批准后再部署。视频和软件摘录仅保存在本地。

## 配套文件与准备

| 用途 | APK | KernelSU 模块 |
| --- | --- | --- |
| 候选 | naozho-0.6.18-dev-wake.apk，0.6.18-dev/33 | naozho-wake-1.3.1.zip，1.3.1/5 |
| 回滚 | naozho-0.6.17-dev-vc33.apk，0.6.17-dev/33 | naozho-wake-1.3.0-vc33-rollback.zip，1.3.0/4 |

1. 从同一发布提交取得表中的四个文件、`timeline.py` 和 `SHA256SUMS.txt`。在 Windows 下载目录用 `Get-FileHash -Algorithm SHA256 .\*.apk,.\*.zip,.\timeline.py` 核对各文件。
2. 停用当前唤醒模块（已启用时点 KernelSU 的 Action，或执行下文停用命令），从时钟正常开发退出到 Freeme。运行 `adb install -r naozho-0.6.18-dev-wake.apk` 覆盖安装。用 `adb shell dpm list-owners`、`adb shell dumpsys package com.naozho.clock | Select-String 'userId=|versionCode=|versionName='` 核对原 UID、user 0 的 ClockDeviceAdmin 及版本。
3. KernelSU 管理器更新同 ID 的 1.3.1 模块，按提示重启。确认独立专机已配置、维护未暂停、用户已正常解锁；正常退出到 Freeme 后显式启用一次。维持 naozho_boot、ADB-Enabler 与原默认桌面，日常双击模块继续关闭。
4. 在待测 Freeme 页复用已放置的「念晴唤醒钟面」，长按调整到 **4×2**。如果原先没放置，长按桌面空白处，从小部件列表拖至该页。以宿主实际分配的格数为准；如果调整失败，记录实际尺寸。平时透明是预期行为。桌面布局、宿主资格或精确闹铃资格无法满足时，记录原因；同一次仍可观察正式链路。
5. 经用户同意，用外部摄像设备拍摄屏幕和操作手指，最好在构图中避开个人信息。开始前可运行 `adb shell settings get global boot_count` 留下本次开机号。保持正常 Freeme 页面；不在设备上开录屏，不注入操作。

## 一轮验收

1. 手机自然熄屏。稍候，按平常方式唤醒一次。相机连续记录从黑屏到第一次可辨时钟数字，到正式时钟出现及实际点按的整个过程。不要用第二次唤醒补齐第一轮的数据。
2. 从本地视频记录首个面板亮帧的呈现时间 `t0`；记录首个**完整、可辨**的钟面（包括尺寸/字形能否辨清）的时间。记录是否来自小部件、是否露出 Freeme 图标，同时观察两个钟面之间有无遮掉数字、仅剩普通桌面或空白的帧。如果发生中断，标出首次失去钟面、随后正式钟面恢复的两帧。用视频呈现时间换算相对 `t0` 的毫秒数。视频看不清来源、存在丢帧或未拍摄时填未知，不用日志补看见的画面。
3. 出现可操作的正式时钟控件后，手指点「开发退出」并观察确认框，再点「取消」。记录真实响应时间，核实仍可触摸。确认退出之前运行以下只读命令，核对同用户实际时钟焦点、LOCKED、策略功能 80 和允许名单仅 com.naozho.clock。若触摸较晚，只能给出点击时已经可操作的上限。最后正常确认退出，检查回到 Freeme、保持 NONE，持续亮屏期间能继续使用手机。
4. 运行以下命令保存本轮证据。选择刚刚这次 boot/dark 的行，其余行保持空白。哪个环节失败就保存该次结果后停止，不重新部署、强制拉起或追加多轮。文件如已存在，换一个新文件名。

```powershell
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState=|mLockTaskPackages'
adb shell dumpsys device_policy | Select-String 'lockTask|LockTask|mFlags=80' -Context 1,3
py -3 timeline.py --collect --save-logs wake95.txt --summary --write-field-sheet witness95.csv > software95.json
```

## 同一轮的现场记录和软件证据

在 CSV 原有 `boot,dark_elapsed` 之后填写下列字段，未知时留空。对不确定的时间点不要填 0。

| 字段 | 填写来源 |
| --- | --- |
| first_clock_ms / first_clock_surface | 首个完整钟面相对 t0 的毫秒数；能确认来源时填 launcher_widget 或 clock_activity，否则填 unknown |
| freeme_seen | 见到普通桌面图标或背景填 yes，观察全程未见填 no，不确定填 unknown |
| handoff_gap_seen | 看见小部件钟面之后、正式钟面接上之前，有中间帧丢失钟面填 yes，全程连续填 no；小部件未出现或无法判断则填 unknown |
| gap_start_ms / gap_end_ms | 同一视频相对 t0：首个缺钟面的帧、随后恢复正式钟面的首帧；能测时两个一起填。仅知确有中断时可只填 yes |
| clock_touch / first_touch_response_ms | 点按正式时钟得到了对应可见反馈填 responded、无响应填 failed、未测填 untested。只有响应且有时间证据才填毫秒数 |

```powershell
py -3 timeline.py --logs wake95.txt --summary --field-sheet witness95.csv > reviewed95.json
```

`physical_observation.first_clock_ms` 和 `gap_duration_ms` 来自视频。`PREVIEW_SUBMITTED_AT phase=off` 表示应用在息屏期向小部件服务提交了显示内容；它可能比 ON 日志早几个小时。`phase=on` 表示用了亮屏后提交的降级路径。二者均不能证明 Freeme 已收取、绘制或把这帧显示到面板。旧记录缺少 phase 时工具保留 `unreported`。OFF 预提交、ON 观察和正式 RETURN 分开，软件记录的负时间差不可作为负的亮屏显示延迟。

`ACTIVITY_READY_AT` 表示本地时钟绘制，`CLOCK_FRAME_COMMITTED_AT` 表示该次时钟的硬件帧提交回调。帧提交可先于或晚于 LOCKED。`CLOCK_PREVIEW_HANDOFF_AT` 表示在正式帧、焦点和锁定均满足后执行本次交接。`PREVIEW_CLEARED_AT reason=handoff` 表示同一代小部件撤销更新已提交。`reason=timeout`、维护或拒绝导致的清除单列。正式帧提交无法证明面板已扫描输出，也不能推出视觉无缝。缺少提交回调时保留「未获证」；保留真实焦点、策略读回与视频点按三种证据。报告同时列出首次可见时长、空档有无与实测长度、正式时钟首绘/帧提交、获得焦点及实锁、触摸结果，标明这只是本次样本。

上版两次记录中，小部件提交分别为 +751/+611 ms，正式首绘为 +1952/+1942 ms，LOCKED 为 +2031/+2004 ms。沿用原记录的相对记法；它没有给出统一的物理亮屏起点、桌面部件的显示帧或两钟面之间的可见间隙。本轮用同一段视频的 t0 直接测量这两个视觉结果。

## 停用与回滚

用正常维护暂停停止自动返回。要立即独立停用模块，可执行：

```powershell
adb shell "su -c 'sh /data/adb/modules/naozho_wake/stop.sh'"
```

核对 armed 已移除、模块已停止，必要时用桌面编辑移除该小部件。保存单轮现场记录。恢复到上一版时先正常开发退出，再 `adb install -r naozho-0.6.17-dev-vc33.apk`。用 KernelSU 管理器更新为配套的 `naozho-wake-1.3.0-vc33-rollback.zip`，按提示正常重启。核对原 UID、Owner、版本和原桌面后再显式启用。保留应用数据；若只需停止自动返回，可单独停用或移除本模块，其他模块保留。若遇启动异常，使用本设备已验证的 KernelSU 恢复入口禁用本模块。

0.6.17-dev / 32 的原始发布物仍可按以下固定提交取得。已升级到 33 的设备可用本次提供的同签名、同 versionCode 回滚配对保留数据，直接覆盖安装。原始 /32 安装包和原版模块供存档及基线核验。[原始 APK](https://raw.githubusercontent.com/shfjq/naozho/4c2f20e6044d141177e538b1aeb50415f698c558/downloads/P0-9.7.9.4/naozho-0.6.17-dev-wake.apk) · [原始模块](https://raw.githubusercontent.com/shfjq/naozho/4c2f20e6044d141177e538b1aeb50415f698c558/downloads/P0-9.7.9.4/naozho-wake-1.3.0.zip)
