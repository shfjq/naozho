# CPDAY10 全局唤醒候选 · 部署、单轮验收与回滚

从普通应用息屏。现场要回答三个问题：亮屏到时钟之间是否露出原应用、正式返回是否只发生一次、时钟能否真正接收触摸。云端没有连接手机，候选的真机效果为**待测**。覆盖系统设置以外的普通浏览器更能验证应用规则的变化。请选择没有隐私内容的页面。

## 安装

| 配对 | 时钟 | KernelSU |
|---|---|---|
| 候选 | naozho-0.6.19-dev-wake.apk，0.6.19-dev / 34 | naozho-wake-1.4.0.zip，1.4.0 / 6 |
| 保留数据回滚 | naozho-0.6.18-dev-vc34.apk，0.6.18-dev / 34 | naozho-wake-1.3.1-vc34-rollback.zip，1.3.1 / 5 |

1. 经用户批准后，从同一个固定提交下载两对文件、SHA256SUMS.txt 和 timeline.py。在 Windows 工作目录执行 `Get-FileHash -Algorithm SHA256 .\*.apk,.\*.zip,.\timeline.py`，核对每个文件。使用已验证的 user 0 和原应用签名。
2. 用原模块 Action 停用唤醒服务；也可运行本手册最后的停用命令。正常开发退出，回到能使用的 Android。记录现有 UID 和 Owner，在手机上保留 KernelSU 的维护及恢复入口。
3. `adb install -r naozho-0.6.19-dev-wake.apk` 后再用 KernelSU 管理器更新同 ID 的 naozho-wake-1.4.0.zip，依管理器提示正常重启。在用户存储已解锁、独立专机已启用且维护未暂停的条件下，从正常 Android 启用本模块一次。复用原 Device Owner、独立锁定设置、默认 HOME 和开机模块。日常双击模块继续停用。无需添加应用到白名单或放置桌面小部件。
4. 对过渡黑幕，用户须在 Android 设置 → 无障碍 → 已下载的应用中主动启用「念晴唤醒黑屏过渡」。核对包名为 com.naozho.clock。若 ROM 阻止启用，记录为遮罩条件缺失。此服务可以观察窗口的存在与边界并在已核验的普通应用窗口上添加过渡层。Android 会为这项授权显示读取窗口内容的能力提示。当前候选用它枚举窗口元数据；代码不读取节点树、窗口文字或输入，也不注入手势。该层跟随原应用的窗口范围，系统栏、通话或认证等高层窗口保持系统控制。正式时钟的返回资格与遮罩授权分别核对。
5. 运行以下只读检查。版本应符合上表、UID 与此前一致、user 0 的 Device Owner 仍为 com.naozho.clock/.display.ClockDeviceAdmin。开始本轮前应为 NONE。准备一台已获用户同意用于本地录像的外部摄像设备，画面须包含屏幕和手指。若没有录像，无法精确判断单帧闪现，记为未知。

```powershell
adb shell dpm list-owners
adb shell dumpsys package com.naozho.clock | Select-String 'userId=|versionName=|versionCode='
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState='
adb shell settings get global boot_count
```

## 一次普通应用息屏唤醒

1. 建议下载同目录的 tap-witness.html，在普通浏览器以本地 HTML 打开。轻点绿色区域一次确认计数可变，记下页面实例号、数字和按钮位置。页面只在本次加载中计数，无网络或持久记录。也可选择其他能看出点击副作用的普通页面。如有通知面板、输入法、通话、认证或权限弹窗，先正常退出这些界面。开始录像。记录一个无敏感内容的页面位置；用以下只读命令在本地记下前台组件及任务号。原应用页应确实在前台。
2. 手指按电源键息屏；确认屏幕熄灭后，用电源键正常唤醒一次。关注**第一个可辨画面**，以及到正式时钟出现之前的全部视频帧。原应用即使只闪现一次也记为 yes。单纯看到黑色无法辨别面板还在熄屏还是过渡窗口已经可见；只有有独立证据时才判定亮屏黑幕。无法确定时填写 unknown。受保护的系统界面、未知保护弹窗、过场变暗或屏幕尚未点亮均不能作为成功遮罩的证据。
3. 若过渡黑场足以操作，在录像中向之前绿色区域点一次。直接出现时钟或黑场太短时跳过该项触摸，单独记为未测。等正式钟面出现，实际点「开发退出」并观察确认框，再点「取消」。如出现卡黑或真实触摸无响应，记录延迟和现场后执行停用恢复，**不要**重复唤醒、强行拉起时钟或再次发 RETURN。正式返回失败会分为窗口或权限资格、取证、投递、提交、前台锁定、超时清理等阶段。
4. 仍在时钟时读取同用户的活动焦点、LOCKED、flags=80，及仅 com.naozho.clock 的允许名单。随后正常开发退出到 Android，保持屏幕亮起。从最近任务恢复原应用，核对原页面、任务号和状态。回到浏览器时，对比计数与页面实例号。只有录像确认黑场内确实点过、同一页面实例仍在且计数未增，才有本次触摸未穿透的证据。实例已变、点击时机不明或没有点到，均记录为未知。同一个任务号与用户可识别的原页面都有证据时才记为任务保留；单靠原进程 PID 无法证明这一点。
5. 只保存该次已有日志。选择本轮新增的 boot/dark 行并填写下表；其余行留空。原始日志、录像、应用内容、任务栈和个人信息留在本机。若输出文件已存在请新建文件名。

```powershell
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
adb shell dumpsys activity activities | Select-String 'topResumedActivity|mResumedActivity|mLockTaskModeState=|mLockTaskPackages'
adb shell dumpsys device_policy | Select-String 'lockTask|LockTask|mFlags=80' -Context 1,3
py -3 timeline.py --collect --save-logs wake96.txt --summary --write-field-sheet witness96.csv > software96.json
```

在同一个新增周期的 CSV 行填写以下现场观察。首个可辨画面与真实点击响应需要现场证据；时间不明时留空。

| 字段 | 填值与含义 |
|---|---|
| origin | 浏览器、普通文件管理器等填 ordinary_app，设置填 settings。home 不能验收本轮目标 |
| first_visible | 亮屏首先可辨为时钟填 clock、原应用填 origin、有证据的亮屏黑幕填 black，其余为 other 或 unknown |
| origin_seen_after_wake | 过渡期间任意一帧露出原应用则 yes，整段完整录像均未露出为 no，否则 unknown |
| first_clock_surface / first_clock_ms | 当场确认正式时钟填 clock_activity；能逐帧辨别时填写相对第一帧物理亮屏的毫秒数 |
| clock_touch / first_touch_response_ms | 手指点按后看到预期反馈填 responded，否则 failed 或 untested；有时间证据再填毫秒数 |
| origin_task_preserved | 确认原任务恢复和页面状态填 yes，确认破坏或丢失填 no，证据不足为 unknown |

```powershell
py -3 timeline.py --logs wake96.txt --summary --field-sheet witness96.csv > reviewed96.json
```

软件证据在 `global_return` 和 `stages_elapsed_ms`。同一个 boot、dark、epoch、request 下，RETURN_SEND_AT、RETURN_DELIVERED_AT、COMMIT_SEND_AT、COMMIT_DELIVERED_AT 都应恰好一条。重复、缺失、请求 ID 矛盾、缺失正式硬件帧或同代本地回执时，不确认本轮正式接管。使用单一完整采集文件，拼接相互重叠的采集将重复记录。CLOCK_FRAME_COMMITTED_AT 是应用硬件帧提交回调；CLOCK_FRAME_ACK_AT 和 HANDOFF_COMPLETE 分别记录应用和模块在本次请求的交接证据。另核对焦点、实锁及真实触摸。小部件、亮屏或黑色窗口实例本身不能证明以上任何一项。

遮罩在 `curtain` 单独汇总。MASK_PREPARE_SENT_AT 和 MASK_CANCEL_SENT_AT 记录模块提交准备或撤销；MASK_ATTACH_REQUESTED_AT 和 MASK_FRAME_COMMITTED_AT 记录应用靠近原窗口的挂载请求和本地帧提交；MASK_RELEASED_AT 或 MASK_REFUSED_AT 记录实际释放或拒绝。只有视频能够判断亮屏时哪些区域露出了原应用。若原应用未铺满屏幕，单独记录状态栏、导航区或未覆盖的系统/OEM 区域。请勿将“已请求挂载”填作“用户已看到黑幕”。

若时钟直接出现在亮屏第一帧且可用，可以没有黑色过渡帧。若用黑幕过渡，需记录软件的遮罩启用、失败或撤销，以及视频中是否露过原应用、是否留下无法操作的黑屏。原应用出现后才变黑、状态数据缺失或仅有屏幕亮灭证据时，分别记录实际结果。完成这一轮后停止；失败时保留该周期的证据和失败环节。单个普通应用的通过仅适用于本次样本。

## 独立停用与回滚

在 Android 仍可操作时从正常维护入口暂停；需立刻终止模块时使用 KernelSU 模块 Action 或以下已授权的独立停用命令。停用后核对模块停止、遮罩已撤、armed 已移除和屏幕可操作。在设置 → 无障碍 → 已下载的应用中关闭「念晴唤醒黑屏过渡」，并核对已停用。如果时钟已正常进入 LOCKED，可以使用正常开发退出回 Freeme，继续使用原应用。

```powershell
adb shell "su -c 'sh /data/adb/modules/naozho_wake/stop.sh'"
```

如出现卡黑，先从已授权的电脑执行以上停用；如果调试通道不可用，使用 CPDAY10 已验证的 KernelSU 恢复入口禁用该模块再正常开机。保持已配置的 Device Owner、系统恢复能力和其他模块。

若只需停用过渡层，在同一无障碍设置中关闭「念晴唤醒黑屏过渡」。需要完整回退时，先停用模块并关闭这项服务，正常开发退出，再运行 `adb install -r naozho-0.6.18-dev-vc34.apk`。通过 KernelSU 安装配套 naozho-wake-1.3.1-vc34-rollback.zip，按提示重启。核对旧版功能、原 UID、Owner、可操作状态后再决定是否启用。配套回滚 APK 使用 versionCode 34 以支持同签名覆盖，模块内摘要精确绑定该文件。原始 0.6.18-dev/33 和其固定模块继续保留。[原始发布](https://github.com/shfjq/naozho/tree/f290b9c6b2597f625272cb82f99efb505bfac603/downloads/P0-9.7.9.5)
