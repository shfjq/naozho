# CPDAY10 P0-9.7.9.7.1 黑屏 watcher 交接

## 当前可做的事

本次提供电脑端审查源码。缺少独立的 com.naozho.mask 1.0.0 和 naozho_mask 1.0.0 原件。手机上已经验证过的黑屏 Activity、SHOW/HIDE 实现、签名和回滚字节尚待核对。云端没有连接 CPDAY10。本批交付物没有可安装的新模块；切勿将源码 ZIP 放入 KernelSU，也不要将其中的示例 service.sh 覆盖当前模块。

如 DSH 已保存原始 APK 和模块 ZIP，直接提供这两份文件或固定下载地址即可。如有源码，附上黑屏 Activity 和原 watcher 即可。无需操作手机，不需要签名密钥、账号信息或整机备份。以下命令可选，仅在电脑上核对已有文件；将两个参数换成实际路径，apksigner 和 apkanalyzer 可用 Android SDK 中的绝对路径。

```powershell
py -3 check_originals.py --apk .\mask-original.apk --module .\mask-original.zip
```

工具核对 APK 签名、包名、版本和模块标识、ZIP CRC，并计算体积与 SHA-256。身份相符后，还需对照实际 SHOW/HIDE、导出保护和可见回执，才能把原件作为回滚基线。原件留在私有工作区。

## 正式模块准备好并获准后的单次验收

1. 用上一版同一固定提交的 `wake97_dsh.py status` 建立只读记录。另核对黑屏应用的包、版本、签名和实际 UID、两个模块的 module.prop 及停用标记、Root watcher 的身份、设备主用户、Device Owner、Enforcing、锁定状态和屏幕状态。保留原黑屏模块及 APK 并核对 SHA-256。上一版 status 只识别时钟和 wake，不能代替对另两个组件的检查。[上一版已验证交付](https://github.com/shfjq/naozho/tree/7f9c828dbbd1037ae8873c56b017547d7b00ede2/downloads/P0-9.7.9.7)
2. 安装真正集成后的签名匹配版本，按其手册从 KernelSU 生命周期启动。记录本次开机标识、watcher 的有效 UID、进程号、会话号和内核启动时刻，以及实例数。不要用 ADB 再起一个 watcher。此步骤须在后续安装包中补齐已核验的真实命令。
3. 打开普通浏览器页面，记录浏览器任务号。息屏超过 5 秒，关闭所有 ADB 会话和持续日志采集，再用实体电源键唤醒一次。由用户观察浏览器有无闪现、黑屏时内容区有无误触、系统栏是否可见、时钟是否按期出现并可触摸。误触见证可用上一版无表单的本地 tap-witness.html。为区分首帧，可用第二台设备仅对准测试屏幕录像。
4. 一次操作完成后才重新连接 ADB。核对开机标识、watcher 进程启动时刻与此前一致；核对息屏、遮罩实际显示及消失、RETURN、COMMIT、真实时钟首帧、WM 焦点、LOCKED、flags=80 和仅时钟允许名单。退出后检查原浏览器任务、页面和点击计数。有任何缺项按未验证记录；失败时保留这一次数据即可。
5. 在电脑上按生产格式检查该周期。取唤醒模块私有目录中的 `events` 和轮转前一代 `events.1`，在本地将两个数值替换为该次 DARK_OBSERVED_AT 的 boot 和 dark；没有轮转可省略 --previous。工具不需要 ADB，不会执行任何设备命令。

```powershell
py -3 mask971_events.py --current events --previous events.1 --boot <boot> --dark <dark>
```

wake 1.5.0 的 `mask=not_submitted` 只描述 wake 内置遮罩。独立黑屏窗口的可见性、输入与撤销需独立证据。浏览器焦点恢复到时钟、黑屏 Activity 消失以及真实触摸须分项填写。

## 停用、卸载与回滚

本审查包只在电脑解压，移除解压目录即可清理。离线核验过上一版时钟 APK 与 wake ZIP；它们的地址和准确摘要见 RESULTS.md。没有制作替代原件的黑屏回滚包。

对后续真机版本，停用时先阻止新的 SHOW，并通过经核验的原 HIDE 释放活动窗口。核对 watcher/子进程均退出、触摸可用且浏览器任务仍在，再按 KernelSU 模块管理器的卸载流程处理。失去 watcher 时，黑屏 APK 自身的可见超时必须仍能撤下窗口。回滚仅针对本次实际更新的组件，以原 APK 证书和两个原件的摘要确认恢复；如同签名降级受限，先留在停用状态。保留时钟、其数据、Device Owner、naozho_boot 和 ADB-Enabler。
