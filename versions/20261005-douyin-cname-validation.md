# 抖音 CNAME 假 IP：修复与验证记录

2026-10-05，macOS 15.0 arm64、Clash Verge Rev / mihomo v1.19.32、正式 ClipVault v1.7.6。

## 现场证据

- 原失败为 13 条 UNSAFE_URL、1 条 AUTH_OR_BLOCKED。未改设置先各抽一条重试，两条成功；其余 12 条再次 DNS 非公网失败。
- 主域名已有 fake-ip-filter 排除规则，dig 与 dscacheutil 返回公网；但 Python getaddrinfo 返回 198.18.0.x。dns-sd 将落地页对应到 www.iesdouyin.com.bytedns1.com，地址为假 IP；直接查询该别名同样为假 IP。相关 CNAME 的后续两跳也返回假 IP。
- 清理 DNS 缓存未修复。补齐 10 个已观察到的精确 CNAME 主机名，配置语义检查确认只增加 fake-ip-filter 条目，mihomo -t 通过，运行配置重载 HTTP 204 后，系统 getaddrinfo 恢复公网。
- 现场只改 Clash 当前配置的持久 merge 扩展与生成配置；备份保留在客户自己的 Clash 数据目录内。没有修改 ClipVault 安装包、账号或授权，没有发布视频。
- 重载后有 6 条 DoH 网络错误；固定 bootstrap 的 DoH 后续连续探测成功（约 1–2 秒），仅重试这 6 条后成功。该短暂超时不是假 IP；不据此承诺网络永不超时。
- 最终现有 21 条任务全部 completed（包含先前 3 条独立测试）。原 14 条失败产物均检查三文件、视频 SHA256 和完整解码。翻译质量沿用此前限制：生成成功不等于术语与标签完全准确。

## 仓库变更

- Shadowrocket always-real-ip 添加精确别名，版本 2026.10.05-2，并归档。
- 一键脚本中的黑/白名单增量合并、客户/工作模式模板，以及同步生成的 Clash 模板覆盖同一组别名。默认客户模式不新增工作参数或公司规则。
- 健康检查改为系统 getaddrinfo，并检查全部地址是否公网，避免 dig 正常掩盖应用路径异常。
- 仅 DNS Real-IP 策略变化；不增加 CDN 厂商通配直连，不修改 Claude/Anthropic 路由，不保存客户节点或运行配置。

## 交付边界

客户现场环境修正及上述任务复测已执行。仓库本地测试与生成检查单独记录；本轮已获得提交推送授权，公开配置与一键脚本的更新以远端提交和内容核验为准。Shadowrocket 与 Windows 未进行本轮运行验收。ClipVault 的后续代码修正只走仓库和正式发行，不在客户安装目录打补丁。

## 本地验证结果

- `python3 -m unittest discover -s tests -p test_douyin_real_ip.py -v`：8 项通过；包含假 IP、混合答案、回环/私网、查询失败、公开地址，以及规则覆盖、黑/白名单和幂等。
- 所有生成 YAML 可解析；两个脚本生成器与三个 Clash 模板覆盖同组别名，归档与主配置一致，再次同步生成 hash 不变。
- `[Rule]`、skip-proxy、bypass-tun 与本轮基线逐字一致，Claude/Anthropic 路由未改。`git diff --check` 通过。
- 以上本地检查未执行 `setup_clash_verge.py` 的写配置入口，不影响开发机的活动代理。

## 登录后恢复与持久性

- 客户原先关闭 Clash 自动启动。本轮新增用户级 `~/Library/LaunchAgents/local.clash-verge.customer-autostart.plist`，`RunAtLoad=true`、Aqua 登录会话，以 `/usr/bin/open -g -a /Applications/Clash Verge.app` 启动；不包含凭据，不启动 ClipVault，不设置循环拉起。
- `plutil -lint` 通过，已加载到用户 GUI launchd 域。测试退出 Clash 后通过该任务重开，任务退出 0；GUI 和 mihomo 均换新 PID，Rule 模式及 TUN 自动恢复。
- 重开后三个抖音域名的 getaddrinfo 均仍返回公网，确认持久 merge 能重新生成有效配置，而非仅内存修改。
- 整机重启未执行；自动启动在用户登录之后发生，不承诺登录前联网。后续卸载该自启动任务时需先 `launchctl bootout gui/$(id -u)/local.clash-verge.customer-autostart`，再删除对应 plist；不要误删 Clash 自身系统服务。
- Clash/内核重新启动后，使用独立目录重新提交一个先前失败的真实抖音短链，任务 completed，三个文件均非空，视频 13324416 字节、SHA256 与任务摘要一致、完整解码退出 0。该验证未复用原目录；最终新增这条后共 22 条 completed。
