# CPDAY10 短时验收与回滚 · P0-9.7.9.4

审核后使用一对候选文件：时钟 `0.6.17-dev/32`、`naozho_wake 1.3.0/4`。验收分为用户看见钟面、正式时钟可操作两项。同一轮自然唤醒即可同时取证。基线 0.6.16-dev/31、1.2.0/3 在 3 次现场复用中，亮屏回调至应用首绘中位数 2305 ms，至焦点 2351 ms，至 LOCKED 2376 ms，用户看见 Freeme。

## 安装候选并准备回滚

1. 从本版同一固定提交下载正式 APK、模块、两件配套回滚文件、`timeline.py` 和 `SHA256SUMS.txt`。在 Windows 下载目录执行 `Get-FileHash -Algorithm SHA256 .\*.apk,.\*.zip,.\timeline.py` 逐项核对。回滚 APK 使用同 versionCode 32，以便保留数据覆盖安装。
2. 在现有模块处于启用状态时，用 KernelSU 模块 Action 停用；也可执行文末的幂等停用命令。使用正常开发退出返回 Freeme。原时钟数据、Owner、300 ms 系统计时、naozho_boot 和 ADB-Enabler 继续沿用，naozho_power_daily 保持关闭。
3. 执行 `adb install -r naozho-0.6.17-dev-wake.apk`。运行下面两条只读命令核实版本和原用户 ID，确认 user 0 的 Owner 为 `com.naozho.clock/.display.ClockDeviceAdmin`。点图标进入时钟并实际触摸一次，随后确认开发退出，Freeme 应可停留。
4. KernelSU 管理器更新同 ID 模块 `naozho-wake-1.3.0.zip`。按管理器提示正常重启，核对版本与停用状态。确认用户存储已解锁、独立专机已配置、维护未暂停，在 Freeme 通过模块 Action 启用一次。
5. 要测试桌面先显示钟面，在 Freeme 桌面空白处长按，在「小部件」中把「念晴唤醒钟面」放到本轮要使用的桌面页，尽量选空页并拉伸到所需宽度。平时部件区透明是预期行为。记录页码、位置及调整是否成功；收录隐私材料时只需记录成功/失败。宿主未提供放置入口、配置未确认或已有精确闹铃资格不满足时，按「无桌面预呈现」记录，继续测试正式返回。普通应用页面仅测正式返回。

```powershell
adb shell dpm list-owners
adb shell dumpsys package com.naozho.clock | Select-String 'userId=|versionCode=|versionName='
```

## 一次自然息屏再亮，同时验证两项目标

1. 回到装有小部件的 Freeme 页，正在使用的敏感界面请先正常离开。用另一台设备从外部拍摄屏幕（只在用户同意时，本地保留）；录像包含真实熄屏、点亮、第一幅可辨认钟面、正式时钟出现和一次手指点按。帧率固定时可数帧，变帧率用逐帧呈现时间。设备侧无需录屏或抓取输入。
2. 自然息屏，再用日常方式完整唤醒。即使首屏的钟面来自桌面小部件，也要等到正式时钟界面：第一次出现一个能辨认的时钟控件时点按，记录是否显示了该控件应有的响应。可以点「开发退出」观察确认框并点「取消」，检查时钟仍可操作。不要在 Freeme 上预先点快捷图标，也不要用强制启动补救本轮。
3. 从视频记录面板首个点亮帧到首次可辨钟面的时长，目标 **<1000 ms**。第一幅钟面可能来自当前页小部件；它显示的同时背景仍可能看见 Freeme 图标，需单独记录。对不能确定来源或欠缺视频的项目填「未知」。
4. 用同一视频记录面板点亮到正式时钟对触摸产生可见响应的时长，目标 **≤2000 ms**。在 2 秒内得到目标响应可证明届时已可操作。若人手在 2 秒后才点按，仍可证明功能，也给出了可操作延迟上限，但无法定出 2 秒时是否已响应。软件侧另核对应用首绘、焦点和锁定读回，后两项都要与实际触摸属于同一轮。
5. 在开发退出之前取得下面只读快照。确认 user 0 当前焦点与 focused app 指向同一个时钟任务（MainActivity 或其受保护入口），Lock Task=LOCKED，功能标志实际为 80，允许名单仅 `com.naozho.clock`。若看到其他用户、另一项策略的数值、PINNED 或字段缺失，记录查到的值并标明未证实。确认退出后应回到 Freeme 并保持 NONE，持续亮屏期间没有第二次返回。下一个独立暗→亮周期才能触发新的返回。

```powershell
adb shell dumpsys window displays | Select-String 'mCurrentFocus=|mFocusedApp='
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState=|mLockTaskPackages'
adb shell dumpsys device_policy | Select-String 'lockTask|LockTask|mFlags=80' -Context 1,3
py -3 timeline.py --collect --save-logs short-01.txt --summary --write-field-sheet witness-01.csv > software-01.json
```

工具只收集模块自己的轮转日志和应用 `NaozhoWakePerf` 标签。输出和录像留在本机；工具不会覆盖已存在的原始摘录和 CSV。按实际测试顺序匹配 `boot,dark_elapsed,epoch`，对未观察的行保留空白。只做一轮测试时可先记录当前开机编号和旧暗周期，匹配新增的一轮。在 `witness-01.csv` 填以下五列，然后离线生成合并结果：

| 列 | 填写方法 |
|---|---|
| first_clock_ms | 首个可辨钟面的帧相对首次亮屏的毫秒数，以整数填写；未测留空 |
| first_clock_surface | 能确认时填 launcher_widget 或 clock_activity；不确定填 unknown |
| freeme_seen | 亮屏到正式时钟之间见到 Freeme 背景或图标填 yes，全程未见填 no，无法判别填 unknown |
| clock_touch | 正式时钟点击有对应响应填 responded，点击无响应填 failed，未测填 untested |
| first_touch_response_ms | 视频中首次真实时钟点击得到预期响应的帧相对首次亮屏的毫秒数；未测留空 |

```powershell
py -3 timeline.py --logs short-01.txt --summary --field-sheet witness-01.csv > reviewed-01.json
```

`physical_observation` 只出现在填写过的周期。`preview.submission_minus_on_callback_ms` 是小部件更新提交与 root 观察到 ON 的时间差；两条监听独立，可能是负数。Freeme 宿主何时绘制 RemoteViews、此刻用户在哪一页、面板何时显示、用户是否真正点得动，需要视频或现场观察补充。小部件清除回执同样只表示撤销更新已发给宿主。没有小部件时，`on_to_first_clock_draw_ms` 仍能测量正式时钟本轮的本地首绘。

## 速度归因与短时回归

基线第 3 轮从 ON 到 FULL_WAKE 为 847 ms，FULL_WAKE 到 RETURN 证明 662 ms，证明到第二轮窗口检查完成 416 ms，随后至 COMMIT 到达应用 263 ms。后面接收器至请求启动 19 ms，请求至 Activity 入口 38 ms，入口至实际时钟绘制 74 ms，再至应用焦点 72 ms。证明和窗口检查可并行，这些是该轮实测端点的相对时间，不能将各线程的执行时长相加。

候选重点看 `on_to_full_ms`、`full_to_return_proof_ms`、`return_send_to_guard2_ready_ms`、`guard2_ready_to_commit_receiver_ms`、`on_to_first_clock_draw_ms`、`on_to_focus_ms`、`on_to_locked_ms`。用 `power_evidence_source` 和 `window_evidence` 识别本次走的读取路径。应用焦点和本地绘制各有自己的时间戳；`CLOCK_FOCUSED` 是 root 的最终核对。软件阶段缺失、身份冲突或顺序矛盾的周期会标出 issues，应计入总尝试并保留。本轮只验收一次。单次结果与旧版范围并列记录，不据此计算新版中位数。

本次验收通过即结束。触摸无响应、重复返回、遮挡系统窗口、开发退出失败或无法证实策略时，停止操作，保存该周期的 JSON 和现场记录。按缺失的具体阶段定位问题；无须重新进行普通唤醒来源和待机测试。

## 停用与恢复

1. 用正常维护暂停关闭自动返回。需要立即独立停用模块时，用 KernelSU 已启用状态的 Action，或执行：

   ```powershell
   adb shell "su -c 'sh /data/adb/modules/naozho_wake/stop.sh'"
   ```

   检查模块停止、armed 消失，正常开发退出回到 Freeme。当前代的停止/暂停会请求撤销预呈现，应用也有本地过期清除。请在 Freeme 核对小部件退回透明；使用桌面编辑移除「念晴唤醒钟面」可彻底撤下该部件。
2. 已保存当前测试结果后，执行 `adb install -r naozho-0.6.16-dev-vc32.apk`，然后在 KernelSU 管理器选择 `naozho-wake-1.2.0-vc32-rollback.zip`。按管理器提示重启；核对应用为 0.6.16-dev/32、原 UID/Owner、模块 1.2.0 和停用状态，再显式启用并短测一次。配套模块中的 APK 摘要对应这份回滚 APK。
3. 只移除本轮模块时，先停用，再在 KernelSU 管理器单独卸载 naozho_wake 并按提示重启。启动异常时，使用本设备已确认可用的 KernelSU 恢复入口禁用该模块。保留原时钟应用、设备管理身份、开机模块和 ADB-Enabler。
