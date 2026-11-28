# P0-9.7.9.5 · Freeme 小部件提交、缓存与首帧

**可将一份完整、可见的钟面 RemoteViews 提前提交给已绑定的 Freeme 小部件。** 即使宿主当时没有监听，这版系统可以保留该 ID 的最新布局，供宿主重新监听或重新建立视图时读取。亮屏仍需 Freeme 自己应用布局并提交显示帧。现有资料不能给这个过程规定毫秒上限。

## 证据范围

分析使用项目提交 `5842423390238031c22520047f37e8df52fb8550`、已归档的 CPDAY10 固件和 P0-9 BASIC 采集结果。固件指纹为 `coolpad/CPDAY10/CPDAY10:16/BP2A.250605.031.A3/1784819045:user/release-keys`。

| 实际核对文件 | SHA-256 |
| --- | --- |
| 补充证据 ZIP 内的 framework.jar | `2d3548851e2217616cdbb42083b2785c3f230e09d4f05ca009dd4a4c01a3d14d` |
| framework.jar 的 classes.dex | `bea5feda3aabb04c8a074af8482d8da2fc648b64398887d0c210d8e048126a37` |
| P0-4 归档的 services.jar | `70fa04e1e51c4008078cdc7fd6c1cc041769e39bd3cce99712ce1d374d81f468` |
| services.jar 的 classes.dex | `9a90166ac33208baf8dfc9dbcd98ff3eda498944c564d698d30bf613d735eab9` |

本次从两个 JAR 中读取的 DEX 均与用于反汇编的本地文件逐字节相同。P0-9 的 `p09-before.json` 记录 HOME 为 `com.droiclaw.launcher3/com.freeme.launcher.FreemeLauncher`。已检索工作区、历史调查文件和用户附件的归档目录，没有找到该 Launcher 的 APK 或宿主实现源码。已归档的 FreemeManager.apk 属于另一个应用。当前无法从 Freeme 自身代码确认其自定义 Host、桌面页回收、OFF 时停止监听或恢复监听的时刻。

## Android 16 实际路径

下表偏移均为上述固件具体方法内的十六进制 DEX code unit。

| 环节 | 反汇编结果 | 对时钟的影响 |
| --- | --- | --- |
| 提交 | framework 的 AppWidgetManager.updateAppWidget(int[], RemoteViews) 进入 tryAdapterConversion；普通远程布局经 lambda$updateAppWidget$5 @0004 调 IAppWidgetService.updateAppWidgetIds。legacy list 转换分支可能在另一线程执行。时钟预览未采用列表适配器。 | 记录 provider 发起更新、调用返回或抛异常。这个方法没有宿主绘制回调。 |
| 缓存完整布局 | services 的 AppWidgetServiceImpl.updateAppWidgetIds 按包及 ID 做查找并调用 updateAppWidgetInstanceLocked。后者对完整更新 @001a 写 Widget.views，@0061 取 getEffectiveViewsLocked，@0065 调 scheduleNotifyUpdateAppWidgetLocked。 | 服务进程持有按 ID 管理的最新视图。权限、组件状态和系统遮罩仍生效；普通应用不能读取或控制宿主进程生命周期。此缓存不能作为跨重启持久化承诺。 |
| 当下是否投递 | scheduleNotifyUpdateAppWidgetLocked @004b 更新视图序列号，@005a–005c 检查 Host.callbacks；为空则跳至出口。有活跃回调时，普通视图走 @0099–00a0 投递 Handler 消息。handleNotifyUpdateAppWidget @002a 调 IAppWidgetHost.updateAppWidget，随后 @002d 更新已通知的序列号。 | 序列号说明通知进度。宿主没有监听时可以跳过即时通知。 |
| 重新监听 | AppWidgetServiceImpl.stopListening @003b 清 Host.callbacks。startListening @0062 注册 callbacks，@0080 按宿主传入的 ID 读取待更新项。Host.getPendingUpdatesForIdLocked @0046–004e 采集最新有效视图。framework 的 AppWidgetHost.startListening @005d 交给 updateAppWidgetView。setListener @000e–0013 也可从服务读取现有布局再更新相应监听方。 | 当宿主实际恢复监听且包含这个 ID 时，可收到最新状态。一个后来的完整空白更新可以取代早先的钟面，宿主无须逐一绘制中间更新。 |
| 应用和绘制 | AppWidgetHost.Callbacks.updateAppWidget @0019–001d 往宿主 Handler 排队。AppWidgetHost.updateAppWidgetView 根据 ID 查监听方。AppWidgetHostView.applyRemoteViews 可以走 @003d 异步 inflate，或经 @004d canRecycleView、@005d reapply、@0079 apply、@0092 applyContent。 | 同布局有机会复用；宿主也可以重新创建视图。服务成功返回、宿主拿到消息、布局更新、合成到屏幕是不同时间点。 |

## 暗屏提交和亮屏回退

- **真实 OFF 期提交。** 只对经用户配置、当前绑定、Freeme HOME 且模式允许的 ID 提交完整可见布局。检查时间和最近一次撤销的 boot/dark；正常退出桌面时不能留下旧预览。仅发送不可见布局会把显示动作留到 ON 之后。保留原始 Application/Activity/Root 职责，无需增加权限或创建新窗口。
- **ON 回退。** 在同一 boot/dark 下，只在确认需要回退时投递一次；先检查维护暂停、锁屏、可交互态、绑定及本轮期限。暗屏已提交时静默等待宿主应用或由正式时钟接管。重复提交同一布局不能唤醒停止监听的宿主，还可能占用首次绘制时段。若应用被回收，已提交的视图可留在服务进程；无法从进程死亡这一事实推断是否曾显示。未确认暗屏提交、宿主不支持或没有绑定时，继续现有受保护的正式返回。
- **撤销。** 小部件状态需要与匹配的 boot/dark、维护暂停及本期终止绑定，并保留进程死亡后的清理途径；切回普通 Android 后也要清除。若 Freeme 停听，清理会更新服务中的视图，实际桌面纹理被替换仍由宿主决定。
- **可观测界限。** `PREVIEW_*SUBMITTED*` 只证明应用提交。公开 provider API 无法为另一个 UID 的 widget 提供 onDraw、FrameMetrics 或用户看到的像素时间。验收用一次外部视频标出第一帧亮屏、桌面上的可辨认钟面、首个正式 Activity 画面，再与单调时钟日志和手指操作对应。独立记录桌面仍然可见、仅局部预览或看不到预览的样本。触摸、时钟真实焦点与 LOCKED + 80 单独确认。

本节分析和反汇编均在云端完成。本轮没有连接手机，尚无新版本的宿主绘制或首帧测量。
