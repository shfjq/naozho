# CPDAY10 开机恢复实验 · 0.6.8-dev / 23

**先验证 Job 的自然调度，再验收可触摸的独立时钟。** DSH 已在 CPDAY10 的 0.6.7 看到 Atlas 拦截发给时钟的两种开机广播。关于 JobService 是否受到同样限制，目前需要独立取证。

## 安装与登记

1. 正常确认开发退出，进入 Freeme。核对下载文件，再用 `adb install -r .\naozho-0.6.8-dev-debug.apk` 覆盖安装。主包为 com.naozho.clock，Device Owner 仍为 com.naozho.clock/.display.ClockDeviceAdmin。复用原有部署。多设备时给 adb 指定 CPDAY10 的序列号。
2. 打开「时钟管理员恢复」。若当前桌面没有该入口，可**仅在重启前准备阶段**执行 `adb shell am start --user 0 -n com.naozho.clock/.mode.AdminRecoveryActivity`。已有的 0.6.7 独立配置无需暂停或重新部署。
3. **调度对照轮**点「登记仅观察任务」，再点「读取开机 Job 状态」。任务编号为 **6801**，模式应为「仅观察」，persisted=true。此模式的 Job 只记录执行。已有的开机广播仍可独立工作，按日志来源归因。
4. 完成对照后做**恢复轮**。若独立专机已启用，点「登记独立恢复任务」。若已暂停，使用原入口「锁定当前时钟（开机自动恢复）」，它会登记恢复任务。两种模式共用一个 Job。显式切换会替换同一 ID 下的模式和 ticket，相同模式重复登记保留原 ticket。单纯覆盖安装不能作为任务已登记的证据。
5. 每轮登记后退出维护页面。准备重启时，确认任务条目仍在、登记 boot 与当前相同，保存 ticket、模式、间隔及运行时间窗口。若刚好 active，等待该次自然结束，再确认仍有下一周期的条目并留档。仅观察期间时钟出现也要查来源。

## 三个节点的只读采样

每轮都采集**重启前、重启后 ADB 可用时、自然执行后或观察窗口结束时**三个节点。下面在 Windows PowerShell 运行，把 `$step` 改为不同文件名前缀。保存完整快照可保留相邻 Job 和上下文。

```powershell
$step = 'probe-before'
Get-Date -Format o
adb shell settings get global boot_count
adb shell cat /proc/uptime
adb shell getprop sys.boot_completed
adb shell am get-started-user-state 0
adb shell dpm list-owners
adb shell dumpsys device_policy > ".\$step-policy.txt"
Select-String -Path ".\$step-policy.txt" -Pattern 'lockTask|mFlags' -Context 1,5
adb shell cmd jobscheduler get-job-state -u 0 com.naozho.clock 6801
adb shell dumpsys jobscheduler > ".\$step-jobs.txt"
Select-String -Path ".\$step-jobs.txt" -Pattern 'IndependentBootJobService|/6801' -Context 2,22
adb logcat -d -v monotonic -b main -b system -b events > ".\$step-log.txt"
Select-String -Path ".\$step-log.txt" -Pattern 'NaozhoBootJob|Independent boot|Lock Task after start|Clock window focused|ComponentFirewallButler|IndependentBootJobService|Background activity start'
adb shell dumpsys activity activities | Select-String 'mLockTaskModeState|topResumedActivity|mResumedActivity'
adb shell dumpsys window windows | Select-String 'mCurrentFocus|mFocusedApp'
adb shell cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.HOME
```

维护页的只读按钮显示 getPendingJob 的登记读回、Android 16 公开接口 getPendingJobReasons 的原始原因数组、上次回调及该开机内首次回调的 elapsedRealtime。系统调度原因可能同时有多个。为避免打开应用影响待机桶，在重启后的无人干预观察结束后再进维护页。若无线 ADB 晚于任务恢复连接，开发包可用 `adb shell run-as com.naozho.clock cat shared_prefs/independent_job_history.xml` 读取最新采样。核对 boot 和 ticket，避免使用上次开机的数据。

分别记下电源菜单确认重启到首次可触摸的实测时间，以及应用记录的开机到首次 onStartJob 的 elapsedMs。前者包括关机、固件和界面启动所用时间。若状态页的「首次执行」仍属于旧 boot，仅记录为旧样本。

## 自然重启与判读

用手机电源菜单正常重启，外部录像计时。保持系统正常使用条件。重启后不点时钟或维护页，不用 ADB 启动 Activity，不强制运行 Job。记录是否先显示 Freeme、是否需要首次解锁、何时可触摸。若必须输入系统凭据，记录解锁时刻并按正常流程操作。JobService 在用户存储可用后才处理模式配置。

| 现场证据 | 应记录的结论 |
| --- | --- |
| 重启前没有 6801，或仅在历史执行列表出现 | 登记未确认。核对用户、包、ID、组件、持久属性以及应用提示，先取得有效登记快照。 |
| 新 boot 无有效条目，重启前确有 PERSISTED 条目 | 该次重启后未读到持久任务。保留两份完整快照、是否曾取消或更新应用、采样时刻。 |
| 相同 ticket 仍在，尚无新 boot 的 onStartJob | 已看到持久任务。结合 earliest/latest、ready、用户状态、配额、待机桶、Doze 和系统调度原因判断。可在开机后约 5、15、30 分钟采样；超出窗口写明“截至 X 分钟仍未执行”。 |
| 系统有准备启动或绑定服务的记录，应用没有回调 | 核对 JobScheduler、ActivityManager 的绑定失败、进程异常及厂商日志。只有出现对应服务、用户和时段的实际阻止证据，才可归因于 Atlas。 |
| NaozhoBootJob 有新 boot 的 service onStartJob 和 finish | 任务已自然执行。用首次回调 elapsedMs / 1000 记录从系统启动到回调的秒数。仅观察轮到此即可通过。 |
| 任务执行后没有时钟，或窗口失焦 | 依次对照 source=job 的恢复检查、launch requested、同 boot 的 Activity accepted、Clock window focused、Lock Task after start 和实际窗口。系统接受启动请求、Activity 接收、实际锁定分别记录。来源为 broadcast 时单列。 |

Android 16 诊断中可见的原因码包括 9（最小延迟）、2（待机桶）、3（后台限制）、12（设备状态）、13（系统调度优化）、14（配额）、15（用户状态）、-1（正在执行）、-2（编号不存在）。没有明确拦截日志时，保留系统读数和观察时长。[JobScheduler](https://developer.android.com/reference/android/app/job/JobScheduler) · [JobInfo.Builder](https://developer.android.com/reference/android/app/job/JobInfo.Builder)

**整机通过条件**为无需手动打开时钟、有效 HOME 保持 Freeme、前台和焦点均为时钟、LOCKED + independent=true + flags=80、名单仅 com.naozho.clock。手指连续上划两次和五次后仍需可触摸。用实体电源键熄屏再亮，打开开发退出弹框并取消，确认仍 LOCKED。

**双模式与取消。** 确认开发退出后应为 NONE + Freeme。留在 Freeme，观察到同一 boot 内至少一个后续自然周期，再核对没有被拉回。点图标应重新锁定。随后正常退出、点维护页「暂停专机并恢复原桌面」，确认 6801 已消失，重启后再确认无有效 6801、NONE、Freeme、Owner 保留。历史事件可能继续出现在 dumpsys 中。需要重新启用时使用原独立锁定入口。

## 实现与适用性

固定 ID 6801 独立于闹铃任务 100–102。Job 由系统持久化，使用 Android 最小周期间隔 15 分钟，不要求联网、充电或设备空闲。它可以在重启前先执行，并继续保留供后续开机调度。实际唤醒时间由系统决定。CPDAY10 的实测延迟将用于判断它是否适合作为成品路径。应用没有常驻服务或自行重排的循环。

登记时写入开机编号。登记所在的开机及仅观察模式均不由 Job 拉起界面。后续开机复用 0.6.7 的 Device Owner、允许名单、用户模式和同一 boot 的启动记录。与暂停、切换模式的操作串行，旧 ticket 和已停止的执行不能继续申请启动。真正的锁定仍发生在时钟取得焦点之后。设备策略与 Job 登记分别读回。登记失败时可继续手动使用已验证的独立锁定。

Android 官方后台 Activity 启动规则列出了以 Device Owner 运行的设备策略控制器。现场仍须核对当前用户的 Owner 身份及系统是否接受窗口启动。同一 boot 内提交过启动请求后，即使系统没有让时钟获得焦点，后续周期也不会反复拉起。此时应保留该次启动与窗口日志。[Android 后台 Activity 启动规则](https://developer.android.com/guide/components/activities/background-starts)

## 构建和验证记录

- 源码提交 `ca34356`。发布 APK 为 11,644,363 字节，SHA-256 为 `4cb6c605aaeb0dbde66edc51b4020a6d18efc90c628ed7aa68d39608ea2af576`。apksigner、包对齐、ZIP 完整性验证通过。签名证书 SHA-256 与 0.6.7 一致，为 `801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。最终 Manifest 差异仅为版本和受 BIND_JOB_SERVICE 保护的 JobService 声明，服务按开发变体开关启用。已从 GitHub 下载发布 APK，HTTP 200，逐字节比对一致。
- Gradle 构建成功。主机测试 development 125 项、debug 106 项全部通过，两组含共享用例。两套 Lint 均为零错误，分别有 10、8 项警告。新增测试覆盖同模式幂等登记、不同 ticket 替换、登记时的开机及观察模式不拉起、两种来源仅启动一次、已停止的任务、存储未解锁、升级后补登记、退出与暂停、登记被拒仍保留手动独立锁定。
- 第一轮使用 AOSP API 28 无硬件加速模拟器和 0.6.8 开发候选包。登记 boot=4 时有固定 ID、PERSISTED、15 分钟周期和唯一 ticket。首次采样时任务已进入 active。重启早期观察到 no-component 和 BOOTING。期间 system_server 重启，稳定采样时 boot=6，仍能找到同一 ticket。系统自然调用了 onStartJob，elapsedRealtime 为 612,867 ms。系统在交付回调之前已记下「No response from client for onStartJob」，该轮未观察到任务处理完成。随后时钟接受的启动请求来源为 broadcast，窗口焦点停在系统无响应弹窗，Lock Task 为 NONE。这个样本未通过 Job 自动锁定验收。
- 第二轮在同一模拟器覆盖安装最终发布 APK，暂停专机后登记「仅观察」，系统读回 persisted=true、observe=true、Owner 保留。重启前的一次绑定尝试超时，随后 Job 为 waiting，可见下一周期的时间窗口。正常重启后 boot 从 6 变为 7，两份有效任务快照的 ID、ticket、登记 boot 一致。开机约 102 秒时用户处于 BOOTING，排队原因包含 no-component。约 170 秒时用户存储已解锁，排队状态为 waiting。系统给出的最早调度时间仍在未来。
- **最终发布包的观察轮通过。** boot=7 的系统自然回调在开机后 **668,138 ms（11 分 8.138 秒）** 到达。`service onStartJob`、带原 ticket 的 `onStartJob`、`finish` 以及私有记录中的 `first_ms=668138` 相互吻合。结果为「仅观察，已收到系统调度」。该轮的时钟恢复未启用，最终有效 HOME 和 resumed Activity 均为 AOSP Launcher，Lock Task 为 NONE。窗口焦点采样还有一个时钟无响应系统弹窗，该轮没有验证触摸。最后调用正式维护暂停，系统读回 Owner 为 true，Job 查询返回找不到 6801。CPDAY10 上 Atlas 是否允许同样的自然调度、Job 能否自动拉起可操作的时钟、耗时及暂停后的重启行为，均待 DSH 验证。
- 该模拟器没有 CPDAY10 的 Atlas。预备阶段尝试在一次性模拟器上仅关闭时钟自己的开机接收器以隔离广播，系统因 Owner 受保护而拒绝，后续保留广播工作。所有重启观察均无强制运行 Job 或 ADB 拉起时钟。
