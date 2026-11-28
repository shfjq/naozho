# P0-9.7.9.9 测试与天气调度

## 调度

- 每次 Open-Meteo 请求成功并写入缓存后，按真实成功时间加 60 分钟安排下一次。闹钟权限已可用时调用 `setExactAndAllowWhileIdle`，否则改用非精确唤醒闹钟。已有 AlarmManager 权限沿用。
- 应用进程有单一请求入口，前台、私有 AlarmManager 接收器和受系统绑定权限保护的 JobService 共用。持久化、需要联网的 JobScheduler 任务用于非精确及重连补充。进程启动会立即补查过期天气。开机后在用户存储可用时恢复；App 更新和系统时间变化重新安排。
- 成功写入 `updatedAt`。断网保留温度、天气代码和原时间；最近失败时间与原因独立持久化。默认网络恢复时立即检查是否到期，不并发请求。
- 每小时使用已保存的坐标。定位与城市数据和天气数据分别保存。主动定位先用 Android Geocoder，再按需用 BigDataCloud 客户端接口；网络查询使用新取得的粗略位置，发送两位小数的坐标并使用缓存、请求节流和退避。UI 提前显示数据用途。没有获得新城市时保留原有保存位置；首次定位无城市仍可用坐标查询天气。
- 系统在 Doze、缺少精确闹钟权限或厂商限制下可能延长触发。CPDAY10 有拦截后台组件的历史，1.5.2 只更新了唤醒 APK 身份。天气在原厂 ROM 上是否按小时执行，需用实际缓存成功时间验收。[BigDataCloud 客户端使用约定](https://github.com/bigdatacloudapi/bigdatacloud-kotlin-client#fair-use-policy) · [Android 闹钟调度](https://developer.android.com/develop/background-work/services/alarms/schedule)

## 构建、权限与模块

JDK 17.0.21.1、Gradle 8.11.1、AGP 8.9.2、Android SDK 35 和 Build Tools 35.0.0 离线构建 `:app:assembleDevelopment`。APK v2、包名、versionCode 37、原设备管理员与受保护唤醒入口均已核对。三份 APK 的完整证书 SHA-256 相同。

`801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`

权限声明集合与 36 一致。保留普通粗定位请求及手动坐标输入。系统权限异常尚无现场日志。新增天气接收器未导出，天气 JobService 由 BIND_JOB_SERVICE 保护。源码基线是工作区可核验的 36 和 1.5.1 对应提交 `ced0fbaf703e3b6eb231c28138f072519b1484be`。

模块 1.5.2 以三份真实 APK 核验包名、版本、整包哈希和证书。26 项模块身份与投递断言，33 项 WakeFlow、18 项 WakePipeline 断言通过。测试涵盖版本切换、修改 APK 拒绝和原 RETURN/COMMIT 约束。

## Android 定向验证

| 测试 | 通过 |
|---|---:|
| DevelopmentClockHandoffTest | 4 |
| RetainedClockWindowTest | 2 |
| ClockDisplayTest | 1 |
| TapExitCounterTest | 5 |
| CityLocatorTest | 10 |
| WeatherRepositoryTest | 5 |

合计 27 项。小时用例通过实际仓库缓存写入两次成功时间戳，时钟由测试控制。第一次成功 1795343200173，第二次在满一小时后重连成功 1795346800346，单位为毫秒。到期前一毫秒没有网络请求。真实 CPDAY10 息屏、重启和联网调用仍待 DSH 验收。

七连击的 Compose 用例逐次检查前六次静默、标签不变、第七次确认、超时与离页重置。回归确认按钮仍走 desktop-handoff。缓存状态、城市和更新时间在 720×720 模拟布局中验证。

首次把定向用例与整套钟面 UI 回归并跑时，钟面时间戳及 Activity 重建恢复出现超时。时间戳用例改为触发真实设置变更入口后通过，Activity 重建恢复用例独立复跑通过。两项通过均为 Robolectric 环境结果。
