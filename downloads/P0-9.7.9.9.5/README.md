# CPDAY10 P0-9.7.9.9.5 交付

离线省/市选择器：34个省级地区、498个下级选项。确认后立即写入原天气字段并刷新；取消不写。当前宁波设置保留。

- 新APK：[naozho-0.6.25-dev.apk](naozho-0.6.25-dev.apk)，versionCode40，同原签名。
- 配套模块：[naozho_wake-1.5.7.zip](naozho_wake-1.5.7.zip)，versionCode14，接受35～40。
- [完整交付包](P0-9.7.9.9.5-release-bundle.zip) / [完整源码](P0-9.7.9.9.5-source.zip)
- [安装、验收与回滚](DSH-安装与验收.md) / [离线测试报告](测试报告.md)
- [行政区JSON](china_regions.json) / [地区数据来源与坐标精度](地区数据来源.md)
- [SHA256SUMS.txt](SHA256SUMS.txt) / [APK权限与签名核对](offline-verification.json)
- 回滚原件：[APK39](naozho-0.6.24-dev-rollback.apk) / [模块1.5.6](naozho_wake-1.5.6-rollback.zip)。必须先回滚APK39，才恢复旧模块。

按用户补充授权，wake.jar仅扩展版本身份集合；weather.sh及全部其他运行脚本与1.5.6逐字节一致。模块ZIP改变项仅身份表、模块版本和wake.jar。

31项应用测试、42条Root身份/派发断言通过。所有待部署文件构建、签名及哈希均已核对；GitHub发布后须逐文件回下载再确认。本轮没有连接手机。720×720真实操作、断网保存、重启保留、一次自然小时更新及真实升级/回滚仍待DSH批准后验证。设备数据备份只能由DSH在用户电脑本地执行，未声称云端已有手机备份。

请在GitHub固定提交查看和下载；不要拿分支移动链接作校验基线。
