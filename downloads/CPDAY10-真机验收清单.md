# CPDAY10 · 0.5.5 真机验收清单

当前仅供部署前审查。以下真机项目均待 DSH 验证。确认取得 APK 和完整手册后，才进入设备操作的审批与验收。

## 部署前审查

- [ ] 核对 `naozho-0.5.5-device-owner.apk` 的包名 `com.naozho.clock`、versionName `0.5.5`、versionCode `10`，以及 SHA-256 `0ff02b37c9b417022c1dc8bf65219c7eea149ca4fcd1fa2fff76779233e8798a`。
- [ ] 审查完整部署手册中的两条入管路径、日常 PIN 退出、维护暂停和彻底恢复流程。
- [ ] 如采用二维码入管，先配置并验证首次设置网络可访问的 APK 下载地址。交付 JSON 的地址为占位，二维码待生成。

[部署 APK](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/naozho-0.5.5-device-owner.apk) · [完整部署手册](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/CPDAY10-%E5%AE%8C%E6%95%B4%E9%83%A8%E7%BD%B2%E6%89%8B%E5%86%8C.md) · [首次设置二维码模板](https://raw.githubusercontent.com/shfjq/naozho/p5-download/downloads/CPDAY10-%E9%A6%96%E6%AC%A1%E8%AE%BE%E7%BD%AE%E4%BA%8C%E7%BB%B4%E7%A0%81%E6%A8%A1%E6%9D%BF.json)

## 获得实施批准后的真机验收

- [ ] **入管**。分别记录首次设置阶段的二维码实际支持情况，以及单用户、无账户的 ADB Shell 入管结果。二者需要独立的干净基线。正常安装 Owner 必须为本应用，未启用专机前为 `NONE`。
- [ ] **实体电源键**。屏幕实际息屏。短按后直接出现可触控时钟，再按正常息屏。覆盖连续切换、空闲超时、夜间待机和开机后状态，分别记录 `mWakefulness`、Keyguard 和前台组件。
- [ ] **普通导航**。`LOCKED` 下覆盖上滑、侧滑、返回、Home、最近任务、通知面板及外部应用入口。原厂紧急和电源长按路径单独核对。
- [ ] **PIN 及原桌面**。错误、取消均保持锁定。正确后 `NONE`、有效 Home 是 Freeme、Device Owner 仍是本应用。使用 Freeme 的 Home 和最近任务，重新打开时钟后恢复 `LOCKED`。
- [ ] **重启、崩溃、升级**。时钟模式及 Freeme 模式各测冷启动，已启用专机应回时钟。模拟时钟进程异常后由当前 Home 恢复。分别从两种模式验证同签名 APK 覆盖更新。系统 OTA 前后记录指纹、Owner、Home、Lock Task、闹铃登记和恢复。
- [ ] **实际响铃与实体音量键**。在息屏、锁屏和 `LOCKED` 下确认响铃界面和实际声音。音量＋停止，音量－贪睡，长按和连按无重复，响铃期间系统音量面板不出现，平时保持正常按键。无网络和勿扰模式也要验证。
- [ ] **vivo 健康**。保留原厂应用及必要蓝牙、网络、定位和前台服务条件。对照息屏、冷启动和不同模式的后台结果。
- [ ] **恢复**。演练一次性恢复码、维护暂停及恢复锁定。完整恢复出厂另在批准后的独立步骤执行和记录。

建议在关键场景保留 `dpm list-owners`、有效 HOME 解析、`dumpsys activity activities` 及 `logcat -d -s NaozhoMode NaozhoAlarm`。保存结果时遮盖设备串号、PIN、恢复码和账号。物理电源键、厂商向导、Freeme 手势和实际音量键结果以 DSH 的 CPDAY10 记录为准。
