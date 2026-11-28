# P0-9.7.9.9.5 部署与验收（尚未执行）

交付：com.naozho.clock 0.6.25-dev / 40 + naozho_wake 1.5.7 / 14。
本轮云端没有连接或操作 CPDAY10。以下步骤由 DSH 在获准部署后执行。任何版本、签名、Owner 或 UID 异常立即停止。

## 1. 下载与私有备份

从本次固定 Git 提交目录下载 APK、模块、回滚文件及 SHA256SUMS.txt。Windows 用 `Get-FileHash -Algorithm SHA256 .\文件名` 与清单比对。完整发布包内亦包含所有交付文件。

先用已经验证的开发退出进入 NONE + Freeme，记录实际应用 UID 与 Owner。确认当前 0.6.24-dev /39、模块1.5.6/13。仅只读核对，不设置 Owner、不改 HOME。

```powershell
adb -s <设备序列号> shell dumpsys package com.naozho.clock
adb -s <设备序列号> shell dpm list-owners
adb -s <设备序列号> shell dumpsys activity activities
python .\backup-prefs.py --serial <设备序列号> --out .\private-before-40
```

备份工具只读取当前39版本的 shared_prefs，二进制直写本机 TAR，保留所有 prefs 文件，包含当前宁波设置。它不会安装、写设备或上传文件。备份目录含用户位置/配置，只留本机。不要把 prefs、Owner 输出、序列号或原始设备日志上传公开仓库。若工具失败，停止升级并保留原版本。

## 2. 覆盖升级

1. 在 KernelSU 管理器安装 `naozho_wake-1.5.7.zip`，按管理器要求安排正常重启。先保留 APK39。新模块兼容35～40。
2. 确认实际已加载1.5.7/14，再用正常开发退出回到安卓。需要临时停止观察器时使用既有 `stop.sh`；它停止唤醒观察，不等同于停止天气脚本。
3. 覆盖安装：
   `adb -s <设备序列号> install -r .\naozho-0.6.25-dev.apk`
4. 确认包名、40/0.6.25-dev、UID与升级前一致、ClockDeviceAdmin仍为 Owner。不要执行 uninstall、clear、set-device-owner 或 clear-device-owner。
5. 首次打开设置，现有宁波、29.8683/121.544、weatherAuto=false 应保持不变；读取旧配置不会主动写入新目录坐标。
6. 唤醒观察器如被主动暂停，沿用 KernelSU 已有动作入口恢复，核验事件不出现 apk_changed/apk_allowlist_invalid。只做一次必要兼容核验，不重复完整历史测试。

签名证书 SHA-256：
`801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578`。

## 3. 本轮一次性针对验收

- 设置 → 天气 → 选择省/市：省份列表滚动选浙江省 → 宁波市。未点确定时不写；取消不改原设置；确定后立即保存并刷新，不必再按“保存显示设置”。重开选择器显示当前选择。
- 选择时省份可返回重选，市列表不可串省。抽看直辖市区县、香港/澳门分区和台湾县市。720×720真机实际触摸和大字体适配均须实测。
- 断网选择宁波：城市、坐标、weatherAuto=false、weatherResolvedAt=0仍保存。天气请求失败不伪造成功时间。恢复网络后确认新天气及真实更新时间。
- 手动经纬度输入仍可覆盖；清空并保存仍关闭天气；自动定位为可选，失败保留地区并提示手动选择，不重复要求定位。无需新增任何定位权限。
- 重启后地区保留、不被自动定位覆盖。无需重复整个唤醒来源测试。
- 记录一次选择后的真实成功时间T0，等待一次自然到期 T0+60分钟，在后台息屏条件下核对 ROOT_WEATHER_DUE/TRIGGER/SUCCESS 与新的 updatedAt。不得通过手工触发冒充自然调度。下一次按新成功时间+60分钟。
- 七连击静默退出、确认/取消、LockTask=LOCKED且flags=80做必要快速回归。确认触摸真实可用。

## 4. 结果记录

逐项写“通过/失败/未测”，附实际时间和 updatedAt。云端31项自动化测试与42条Root身份/派发断言仅为离线验证；不能代替上述真机结果。当前本轮所有真机项目均为待验证。

## 5. 停用、卸载与回滚

- 临时停止唤醒观察：`adb -s <设备序列号> shell su -c 'sh /data/adb/modules/naozho_wake/stop.sh'`。注意该脚本不停止独立天气脚本。
- 完全停用模块：KernelSU 中停用 naozho_wake，按正常流程重启使所有旧进程退出。需要移除时使用 KernelSU 卸载模块及其既有 uninstall.sh；不卸载时钟，不删除应用数据或 Owner。此操作也停掉该模块承担的天气调度。
- 回滚优先只覆盖APK：`adb -s <设备序列号> install -r -d .\naozho-0.6.24-dev-rollback.apk`。两份都是同证书 Debug APK，`-d`允许调试包版本降级；如果系统拒绝，立即停止，不卸载、不清数据。真实CPDAY10降级本轮尚未执行。
- 保留1.5.7时也接受39。需要完整回滚时，先确认APK已恢复39，再在KernelSU安装 `naozho_wake-1.5.6-rollback.zip` 并按管理器流程重启。不得让旧1.5.6配APK40。
- 39会忽略新增的省/市代码，仍读取相同 weatherLabel/weatherLat/weatherLon/weatherAuto 字段；已选择地区可继续使用。通常无需恢复数据备份。
- 如果确有配置损坏，先停用模块并保留当前配置副本，再单独审查本机私有备份恢复；不自动整包覆盖prefs。禁止复制到其他设备/UID，禁止恢复出厂作为常规回滚方式。
