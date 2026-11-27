# P0-9.4 离线测试报告

测试对象为 KernelSU 试验模块 0.1.0 与现有 0.6.13-dev / 28 的接收协议。复核日期为 2026-11-27。没有连接、部署或操作 CPDAY10。

| 实际执行 | 结果 | 边界 |
| --- | --- | --- |
| 模块 JVM 测试 | 42 项通过 | 输入源与能力掩码、KL/KCM、Linux 单调时钟、按键/松开/重复、音量组合、丢事件、打开权限拒绝、显示组、休眠历史、超时、前台、暂停或新事件使提交作废、固定目的地、单次提交。以合成数据和假系统服务验证。 |
| 原有手势判定 JVM 测试 | 23 项通过 | 正常两次短按、单击、长按、第三击、抖动、取消、过期及重复等。沿用原判定器。 |
| 原工程 :app:testDevelopmentUnitTest | 148 项通过，25 套件，0 失败、错误或跳过 | 离线 Gradle 重跑。含原有 9 项 ConfirmedPowerReturnTest 和 4 项 PowerReturnActivityTest。Robolectric 的返回流程覆盖收件、暂停/迟到、重复、电话/锁屏、前台提交和 LOCKED + 80；跨用户回调由测试显式投递。 |
| 模块打包 | 两次独立 javac、D8 编译和压缩得到相同字节 | 检查 ZIP 及内嵌 JAR 的 CRC、固定文件集合、脚本权限、shell 语法；dexdump 可解析模块中的 DEX。模块不包含原厂固件、日志、私钥、启动脚本或系统分区内容。 |
| 已发布应用接口 | 0.6.13-dev 原 APK SHA-256 为 8bcf50a524f58b6c8180d699f47a18fd096d94b7b12d737d1a60710d189597d4 | 用 aapt 从二进制 Manifest 核对 ConfirmedPowerReceiver 已导出且发送者须有 STATUS_BAR_SERVICE。时钟 APK 和 Device Owner 组件没有改动。 |

## 独立重建模块

解压源码包，保留 platform/station 和 kernelsu/naozho_power 的相对目录。在 Linux 或 WSL 中使用 Python 3、JDK 17、官方 Android SDK Platform 36 和 Build Tools 35.0.0。示例从源码包根目录运行。脚本编译使用 Java 11 语言级，D8 的最低 API 参数是 34；模块安装和实发校验限本次审查的 API 36 固件。

~~~sh
export JAVA_HOME=/path/to/jdk17
export ANDROID_HOME=/path/to/android-sdk
python3 kernelsu/naozho_power/test.py \
  --android-jar "$ANDROID_HOME/platforms/android-36/android.jar" \
  --d8 "$ANDROID_HOME/build-tools/35.0.0/d8" \
  --out ./naozho-power-trial-0.1.0.zip
~~~

只需构建时用同参数运行 build.py。完整时钟仓库中可另运行 ./gradlew :app:testDevelopmentUnitTest。源码包附带本次模块测试逐项结果和应用套件计数。请以下载分支同提交 SHA256SUMS 为准。

## 待真机验证

KernelSU Manager 安装和移除、SELinux 对输入节点和广播的实际许可、主板物理键及 KL/KCM、两击之间的实际休眠、厂商窗口与电源查询格式、DSH 的 Windows 脚本实机运行、广播到达、前台焦点、锁定数值及可触摸性、暂停/重复、正常关机开机和充电、紧急拨号入口及通话不中断。试验仅在 Freeme 亮屏前台运行；从其它普通应用直接返回、待机耗电及长期监听属于后续设计。保护基本电话能力的机制已审查，实际通话行为仍待验证。
