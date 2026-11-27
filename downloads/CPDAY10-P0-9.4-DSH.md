# CPDAY10 P0-9.4 安装、验收与回滚

本手册供批准后的真机试验使用。本轮云端开发没有连接手机。模块只在 DSH 手动运行时工作，管理器的 Action 只查输入源。一次最多观察 60 秒或发送一个请求。首轮范围是 user 0、已初始化的 CPDAY10 Android 16、现有 KernelSU、SELinux Enforcing、亮屏 Freeme 前台和 0.6.13-dev / versionCode 28。

## 准备

1. 在同一固定 GitHub 提交下载 naozho-power-trial-0.1.0.zip、Run-PowerTrial.ps1 和 SHA256SUMS。用 Get-FileHash 对照后再安装。模块 ZIP 是安装文件，源码 ZIP 供审查。
2. 记录试验前的专机启用状态、是否维护暂停、Device Owner、原厂 Freeme 和充电指示。先确认现有「开发退出」可以回到 Freeme，维护入口可用。普通开发退出保留专机开关；维护暂停会关闭它。若当前设备版本不同，先按已有计划审查 0.6.13 的部署，避免合并两次变更。脚本不会安装 APK 或授权 Root。
3. 在现有 KernelSU 管理器的模块页选「从本地安装」，选择模块 ZIP。等管理器显示新模块已生效；如提示需重启，另择获批的维护时段进行。保留原 naozho_boot 配置。新模块名称为 CPDAY10 Power Return Trial。安装后无开机任务。可在管理器点 Action 查看库存，随后回到亮屏 Freeme。
4. 在 Windows PowerShell 中使用已授权的本机 ADB。在脚本目录执行。用 adb devices 中的实际连接标识替换示例；无线 ADB 可使用 IP:端口。需要已有的本地维护授权，拒绝权限或校验失败时直接记录原因。

~~~powershell
Get-FileHash .\naozho-power-trial-0.1.0.zip -Algorithm SHA256
adb devices
$serial = '替换为本机连接标识'
.\Run-PowerTrial.ps1 -Serial $serial -Mode inventory
.\Run-PowerTrial.ps1 -Serial $serial -Mode status
~~~

## 实验顺序

1. **确认物理输入源。** inventory 应给出唯一 candidate、active_kl、active_kcm、scan=116 mapping=POWER 和 result=inventory_only。它只读元数据。无源、歧义、布局未知时停止；如需要增量资料，按 ANALYSIS.md 指定的字段采集，不放宽输入设备选择。
2. **只观察。** 使用已启用独立专机的正常开发退出到 Freeme。运行下方 observe，看到 ready=observe_only 后，在亮屏上快速完成两次正常的短按及松开。记录首击是否息屏、第二击是否唤醒、可见界面及最后的 result。期望 observed_qualified_double_no_request，仍为 Freeme / NONE。无论结果如何，observe 不允许向应用发送请求。
3. **判断实验分支。** sleep_or_wake_since_first_down 或 display_not_stably_awake 表明本序列不能用于亮屏返回；若实物也显示首击已息屏，停止实发，转交厂商按键策略集成。proof_too_slow、kernel_time_unusable、unknown 或 timed_out 表明证据不足；记录具体 reason。不得把超时单独解释为固件拦截。不要求补开发或改系统参数。
4. **实发一次。** 仅在步骤 2 通过且允许实发时运行 return，等待 ready=return_once，再做相同物理双击。随后运行 status。request_submitted 只说明系统命令返回；分别确认时钟窗口、实际 LOCKED、策略读回 80，且手指可触摸。记录第二次松开到可操作的时长。对未切换的情况只回传 result、实际焦点类别/锁定状态，必要时补应用标签 NaozhoPowerReturn 对应时段的一两行。不要上传通话记录、窗口全量转储或输入流。
5. **验证暂停与重复。** 用日常退出回 Freeme，分别试单击、长按、三击或连续双击，记录有无误入、是否出现多次切换及原厂菜单。每次观察新的手势都需单独发起本轮实验。在维护入口选择暂停，保持 Freeme；合格双击也须保持 NONE，不得出现时钟。再从维护入口显式恢复独立专机、正常开发退出后，新的双击才可成功。暂停与迟到交付、重复窗口的精确时序还有主机自动化覆盖。已经 LOCKED 的时钟前台运行试验会拒绝。
6. **基本电话与电源。** 检查正常单击息屏/唤醒、长按电源菜单、进入及离开基本紧急拨号界面；不得试拨真实紧急号码。使用允许的非紧急测试通话检查通话中和来电时不进时钟。正常充电时核对系统充电标识。关机及重新开机的验证在批准的维护时段进行。若需验证紧急呼叫接通，由具备运营商授权的测试环境单独实施。记录现象，以上均待实机验证。

~~~powershell
.\Run-PowerTrial.ps1 -Serial $serial -Mode observe
# 回到提示符并检查 observe 结果；满足第 4 步再运行下一条。
.\Run-PowerTrial.ps1 -Serial $serial -Mode return
.\Run-PowerTrial.ps1 -Serial $serial -Mode status
~~~

## 停止与恢复

- 试验到期自动关闭，无开机或保活工作。需要中途停止时，在 KernelSU 管理器停用本模块；进程按停用标记终止，默认最长检查间隔 500 ms（已发出的系统请求无法撤回）。如果已进入时钟，按原有「开发退出」二次确认回到 Freeme。如希望维持 Android 模式，使用既有维护暂停。
- 完全移除时在管理器只选择 naozho_power_trial，按管理器提示完成移除。核对模块已消失、Freeme 可用、输入、正常关机/唤醒与充电指示正常，并将专机启用/暂停设回试验前状态。模块没有修改 HOME、系统分区、充电策略或 Device Owner，也不需还原 RRO；原有开机模块的行为沿用原配置。
- 系统拒绝读取、时钟广播无回执或界面未变化时，保存原因并结束。若应用已收到请求但最终未锁定，分别记录应用接收、Activity 焦点和 LOCKED 状态。若管理器暂时不可用，此模块没有自启动入口，下一次正常启动不会自行运行试验。上述为设计的回滚路径，实机卸载恢复须另行签收。
