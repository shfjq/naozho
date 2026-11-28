# CPDAY10 的源窗口遮罩能力

本记录适用于 CPDAY10 的 BP2A.250605.031.A3 / 1784819045。结论来自已保存的同机固件。没有连接手机或试加窗口。编译时附带的 SDK 不足以证明厂商授权，运行时 Binder 可达也不证明画面和触摸行为。

| 私下对照的原厂文件 | 完整 SHA-256 |
|---|---|
| services.jar | `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468` |
| framework.jar | `2d3548851e2217616cdbb42083b2785c3f230e09d4f05ca009dd4a4c01a3d14d` |

离线逐字节对照了上面两个归档中的 3 个 services DEX 和 5 个 framework DEX。以下偏移是方法内的 DEX code-unit 偏移。

| 候选窗口路径 | 实际方法和边界 |
|---|---|
| 直接由 KSU 创建系统悬浮窗 | services classes2 的 WindowManagerPolicy.getWindowLayerFromTypeLw(int,boolean,boolean) 在 0009–0011 将应用窗口类型 1 至 99 放在第 2 层。0015 的 packed-switch 将 2038 TYPE_APPLICATION_OVERLAY 映射到 0038，返回第 11 层。0015 的同一张表将状态栏、导航栏映射到第 15 和 24 层。层号局部于该策略，与 SurfaceFlinger 的最终合成序号不同。第 11 层可以遮挡另外一个以普通 Activity 层显示的来电或凭据窗口。WindowState.setForceHideNonSystemOverlayWindowIfNeeded 在 0006 读取 mCanAddInternalSystemWindow，具有内部授权的 Session 可以提前返回。使用这条路径无法承诺新弹出的关键界面及时可见及可点。 |
| 厂商无障碍窗口特例 | PhoneWindowManager.checkAddPermission 在 006e 调用 isAgentOsAccessibilityOverlayCaller。后者先比较厂商 Launcher 的精确包名，再将 Binder.getCallingUid 与当前用户下 PackageManager 返回的应用 UID 比较。独立 Root 进程和时钟没有该 Launcher 身份。 |
| 针对原任务的系统接口 | services classes3 中 WindowManagerService.LocalService.addTrustedTaskOverlay 在 WMS 全局锁内执行 getRootTask、getTopVisibleAppMainWindow、addTrustedOverlay（001e、0024、0028）。同机 framework 的 IWindowManager、IWindowSession、ITaskOrganizerController 没有暴露这个方法。取得 root task 的顶层遮罩后，仍须处理同一 task 内新弹出的认证 Activity。 |
| Shell root、任务组织器 | IWindowManager.addShellRoot 调用权限检查，并交给指定显示器的 DisplayContent，而非当前普通窗口。TaskOrganizerController.registerTaskOrganizer 要求 manage-tasks 权限；Task.updateTaskOrganizerState 可实际调用 setTaskOrganizer。重新注册组织器会参与原系统任务管理。上述接口均不能为独立进程提供只针对一个普通源窗口的安全短期租约。 |
| 系统过渡或启动窗口 | ActivityRecord.addStartingWindow 先判定是否适合显示、已有窗口是否已画及启动窗口类型，最后在 00e2 调用 scheduleAddStartingWindow。系统有权跳过已驻留且画好的 Activity 的启动窗口。远程启动动画在实际转场时才获得系统交付的动画对象。两者的最早时机均受正式启动约束。 |
| 只有黑色 Surface | 建立颜色层、提交事务和为窗口建立 InputChannel 是独立操作。Surface 提交没有证据表示原任务停止收触摸。扩大为全局输入接管又会影响关键系统窗口。 |

## 候选具体行为

同一模块进程使用固定的只读调用取 WMS、SurfaceFlinger、SurfaceFlingerAIDL 的 Binder 存活状态与接口描述，以及当前进程的 INTERNAL_SYSTEM_WINDOW 和 SYSTEM_ALERT_WINDOW 权限检查结果。第一次尝试限时 350 ms，正式唤醒调度独立执行。WINDOW_CAPABILITY 行里的 REACHED 指回执描述符匹配。部分构建仅发布其中一个 compositor 服务名。ABSENT、DENIED、DEAD、MISMATCH 和 UNKNOWN 分开记录。权限探测不会注册窗口、增加权限、索取其他应用窗口令牌或截取屏幕。

在审查的原厂构建上，独立服务没有可验证的、将输入与画面一起限定到**原应用窗口**的厂商接口。模块因此会报告 stock_no_source_window_attachment（服务不可读则保留对应实测诊断），直接继续真实 FULL_WAKE 与正式时钟返回。此情形不可记为 MASK_VISIBLE 或已挡住触摸。亮屏到正式启动间是否出现原应用须由本机录像确认。

## 真正早于正式启动覆盖的后续条件

要在 OFF 和 WAKE_CANDIDATE 期间拥有系统级遮罩，应取得该版本的厂商 WM 或 Shell 集成支持，使系统在自己的窗口锁内把图层与输入目标同时绑定到原应用窗口。如果焦点、任务、显示器或安全窗口状态改变，系统本身必须在同一次窗口重排中更新或撤销。可由厂商提供已有的签名接口或基于同版本源码添加受限组件，先在独立固件环境测试，再另行审核。运行中读取 dumpsys 后将一个独立置顶窗口覆盖在所有 Activity 上，存在状态变化到撤销之间的竞争窗口。

维护退出、模块停用和卸载应恢复当前普通应用。此候选没有修改系统框架或系统输入设备，也没有引入驻留的全局遮罩，因而停用无需处理跨任务系统窗口。
