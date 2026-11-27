# P0-9.7.8 离线测试报告

| 对象 | 实际结果 |
|---|---|
| 独立诊断 APK | com.naozho.wakeprobe 0.1.0，versionCode 1，min / target / compile SDK 36 |
| 最终产物 | 33,195 字节，SHA-256 `68712d6a3e68d1b7306984b92d6ed89dffdc0bf891d5e32cd6db997ae7a095e5` |
| 签名 | apksigner verify 通过，APK Signature Scheme v3，一个独立诊断签名者。证书 SHA-256 `2618dfdd7a610abcad93e2d99164d7e1430ce468a9360186e3652a72e9a86c99` |
| JVM | 24 组测试运行实际打包代码中的 WakeCycle 及 PowerEvidence |
| 主机汇总 | 3 项，包括跨轮转顺序、缺行、重复导出、冲突样本及 epoch 冲突 |
| 最终 APK 检查 | 解压 CRC、最终二进制 Manifest、逐个 DEX 的直接调用检查通过。导出 1 个控制 Activity；1 个非导出 FGS；无广播接收器、Provider 或时钟目标。4 项权限与设计相符 |
| 真机安装／试验 | 尚未安装。实体唤醒各来源、时钟进程回收、OEM 是否授予 DUMP、系统 idle、30 分钟、8 小时、耗电与漏报率均待测试 |
| 自动返回 | 本阶段没有实现或执行。测试不使用手机、仿真按键或唤醒命令 |

## 离线构建与复核

从源码包目录运行。需要 JDK 17、Android API 36 的 android.jar、本机 Android build-tools（本次使用 35.0.0）、zip 和 Python 3。令 JAVA_HOME、ANDROID_JAR 和 BUILD_TOOLS 分别指向上述安装。令 PROBE_KEYSTORE 指向树外的独立诊断 PKCS12，PROBE_STORE_PASS 通过本地安全方式传入环境。build.sh 在目标 key 不存在时生成一把新诊断 key。私钥不随交付包分发，自行构建的签名和 SHA 可能不同。D8 以 34 为 DEX 最低生成级别；APK 的实际安装下限由 Manifest 固定为 36。各构建临时文件留在被 Git 忽略的 build/。

~~~sh
./build.sh
python3 tests/test_summary.py -v
python3 tests/check_apk.py build/cpday10-wake-observer-0.1.0.apk
~~~

## 生产代码测试输出

~~~text
PASS complete OFF to ON
PASS initial ON only
PASS initial OFF without observed falling edge
PASS AOD pulse and suspension
PASS interactive ambient pulse is insufficient
PASS full wake directly out of noninteractive DOZE
PASS ON pulse returns to DOZE before confirmation
PASS DREAMING with interactive true
PASS noninteractive ON
PASS display ON before interactivity converges
PASS power transition settles
PASS duplicate callbacks and duplicate proof
PASS multi group and missing group
PASS ambiguous power snapshot
PASS missing history
PASS CRLF and bare uptime
PASS future, reversed or unrelated history
PASS missing boot ID
PASS loss of default display
PASS readback gap cannot create epoch
PASS inaccessible power is refused
PASS multi-source alternating cycles and 8h uptime scale
PASS dark to unsupported VR and ON_SUSPEND
PASS new process cannot inherit old cycle
RESULT 24 test groups passed
~~~

8h uptime scale 用的是加大的模拟单调时间间隔。它覆盖整数范围及每一轮 ID 唯一性，不能提供 8 小时待机证据。Android 的 OEM 回调时机、FGS 生命周期及 DUMP 的运行权限边界也需真实运行验证。

## 主机统计与包装审计输出

~~~text
test_collisions_and_missing_end (__main__.SummaryTest.test_collisions_and_missing_end) ... ok
test_conflicting_exports (__main__.SummaryTest.test_conflicting_exports) ... ok
test_rotations_and_gaps (__main__.SummaryTest.test_rotations_and_gaps) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.000s

OK

PASS APK CRC, manifest components/permissions, DEX observer calls and forbidden-call audit
~~~
