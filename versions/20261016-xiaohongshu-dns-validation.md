# 小红书真实 IP 配置修复记录

## 原因与范围

2026-10-16 在客户 macOS 15 / arm64 上只读核验：实际运行的 ClipVault 版本为 1.8.4。用户提供的 9 条小红书链接均能对应到失败任务，错误为 `UNSAFE_URL` / “DNS 返回非公网地址，已拒绝连接。”，阶段记录只有解析开始，尚未下载。系统解析主站 `www.xiaohongshu.com` 返回 `198.18.0.10`，视频域名 `sns-video-v6.xhscdn.com` 返回 `198.18.0.6`。Clash 的生成配置启用了 TUN、DNS 劫持和 fake-IP，小红书未进入排除列表。同机独立 HTTPS DNS 查询能得到公网地址。

现有 Shadowrocket 源配置已有小红书主站和 CDN 的 `always-real-ip`、`skip-proxy`、DIRECT 规则，但 Clash 模板和安装器没有同步对应 DNS 排除项。这是本次修复范围，不扩大到整个公共 CDN 厂商。

## 本地修改

- 版本元数据更新为 `2026.10.16`，归档为 `sr_ai_secure_final_20261016.conf`；源规则正文不变。
- 安装器统一定义 `+.xiaohongshu.com`、`+.xhscdn.com`、`+.xhscdn.net`，供客户版和工作版 Merge 使用。
- `sync_clash.py` 使用同一份常量，三份生成模板均补齐 DNS 排除项；规则文件重新生成，路由正文不变。
- 更新后的系统 DNS 拨测同时检查小红书主站和实际视频域名。
- 客户依旧通过既有 `update_clash.py` 获取同一提交的已校验快照。脚本不自动重载运行内核；客户等待任务完成后更新并手动重新激活当前订阅。

## 初版准备时的验证记录

| 项目 | 结果 | 实际证据与限制 |
|---|---|---|
| 修复前回归 | FAIL，符合预期 | 客户版、工作版部署候选均缺三项排除规则；新测试复现 |
| DNS 与模板回归 | PASS，9 项 | `python3 -m unittest discover -s tests -p test_douyin_real_ip.py -v` |
| 订阅同步回归 | PASS，14 项 | `python3 -m unittest discover -s tests -p test_clash_profile_sync.py -v`；仅隔离夹具，内核检查为替代命令 |
| 发布快照回归 | PASS，8 项 | `python3 -m unittest discover -s tests -p test_release_sync.py -v`；本地测试不等于线上发布 |
| Mihomo 配置校验 | PASS | 本机真实内核 `-t` 校验含生成 DNS 的隔离配置，无 TUN，无系统代理变更 |
| 默认上游探测 | 未通过 | 本机到 `223.5.5.5:53` 超时，默认上游隔离探测未取得主站 A 记录；不据此宣称默认网络通过 |
| 隔离 DNS 规则实测 | PASS | 使用真实 Mihomo，临时 loopback 端口，TUN 关闭；仅测试实例的上游改为 HTTPS DNS，普通域名仍获 fake-IP，小红书主站与视频域名返回公网 IP。不是客户配置修改或完整部署验收 |
| 生成、语法与差异 | PASS | 重复生成 SHA256 一致；`py_compile`、`git diff --check`、源文件与归档一致性通过 |
| 路由及秘密边界 | PASS | 源规则正文与 HEAD 一致；Claude/Anthropic 保持 PROXY，不在 skip-proxy；新增 diff 无代理凭据 URI、入网密钥或私钥 |
| 线上发布 | NOT_RUN | 尚未 commit/push，不可让客户用线上入口领取本地修改 |
| 客户重新激活和真实下载 | NOT_RUN | 未远程修改客户配置，未重启、取消或重试客户任务 |
| Windows 实机 | NOT_RUN | 覆盖了工作版和客户版生成/部署夹具，未在 Windows 加载或执行 |

隔离 HTTPS DNS 实测：`example.com` 返回 `198.18.0.4`；`www.xiaohongshu.com` 返回 `43.159.95.157`；`sns-video-v6.xhscdn.com` 返回多个公网 A 记录。所有地址仅为当时观察，不写入配置；临时内核已结束，临时数据目录已清理。

## 发布后客户操作

等待现有下载完成，执行 README 场景一的统一更新命令。发布门禁成功、更新脚本完成后，按终端提示重新选择当前订阅。核实以下系统解析全部返回公网地址：

```bash
python3 -c "import socket; [print(h, sorted({r[4][0] for r in socket.getaddrinfo(h, 443, type=socket.SOCK_STREAM)})) for h in ['www.xiaohongshu.com', 'sns-video-v6.xhscdn.com']]"
```

再由客户手动重试原失败素材，核对实际视频文件。若仍有 fake-IP，保留结果继续排查生成配置、当前订阅和真实 CNAME；不放行非公网连接，不直接修改生成配置充当持久修复。重新激活后仍须另行验证重启恢复。

## 正式远程更新复测发现与第二版

用户授权支持人员通过 SSH 运行正式更新入口、加载并验收。确认 ClipVault 最近二十分钟无任务更新，VK 发布调度关闭，未停止 ClipVault；仅重启 Clash 应用。第一版 `ee297cc` 正式入口返回 0，保存备份且候选通过内核校验；但加载后两个边界未通过，不能据退出 0 宣称修复：

1. 视频 CDN 的系统解析继续查询别名，分别返回 fake-IP：`sns-video-v6.xhscdn.com.volcgslb.com`、`sns-video-v6.xhscdn.com.m.v19.volcgtm.com`、`sns-video-hs.xhscdn.com.m.v05.volcgtm.com`、`hcdnv.ydbdxhsv6.m.v05.volcgtm.com`。第二版只增加这四个精确别名，源配置同步 always-real-ip，不扩大厂商后缀。
2. 运行服务内核 `/providers/rules` 的两份管理规则均 ruleCount=0，应用日志提示缓存未同步。Clash 2.5.8 [运行包实现](https://github.com/clash-verge-rev/clash-verge-rev/blob/v2.5.8/src-tauri/src/core/runtime_bundle.rs)将 HTTP provider 声明为需内核下载的远程缓存，不把应用目录已有快照作为本地资产复制；file provider 则复制本地资产。第二版将正式更新器已经校验的快照用 `type: file` 部署，并清除管理规则源的历史 URL / interval，保留其他自定义规则源。

新增/加强测试先分别复现漏别名和仍部署 HTTP provider 两项失败，修改后 31 项相关回归通过。归档为 `sr_ai_secure_final_20261016_2.conf`，版本 `2026.10.16.2`。第二版客户运行态和实际下载结果须以远程执行回执为准，本节不预先标为通过。

## 第二版客户实测结果（2026-10-16）

正式入口部署提交 `465c3c7889024fc6d5a0fe7494477ff68e4e3832`，发布门禁通过。客户侧更新器退出 0、生成备份、候选内核校验通过；由支持人员通过 SSH 重启 Clash 自身加载，未手工修改客户生成配置。

- 运行服务内核 `/configs` 确认 TUN enable=true；`/providers/rules` 确认 `sr-direct` 97 条、`sr-proxy` 12 条，管理规则源为 file provider。
- 主站、视频 CDN 和四个已观察 CNAME 的系统解析均为公网 IP，不再返回 fake-IP。
- 用户给定 9 条在客户现有 ClipVault 1.8.4 中均已实际解析、下载，`media_validated_this_attempt=true`。保留已完成或已在途结果，不重复下载；对原 DNS 失败任务使用应用自有重试接口，超时后先读取状态确认服务端已受理，不盲目重发。
- 独立读取 9 份落盘 MP4，大小及 SHA256 均与管线记录一致，独立 FFprobe 通过，均为 720×1280 H.264；媒体验证结果 9/9 PASS。
- 任务状态为 7 completed、2 partial。两项 partial 为 `TRANSLATE_UNTRANSLATED`，分别对应作品 `6ac794c0000000000a0277ba`、`6aca3efe000000000b007c43`；视频均有效，俄文翻译未通过，不能把 9 条都称为完整任务完成。这是独立于 DNS 的后续边界。
- ClipVault 主进程未重启，未取消其他任务。检测到客户新启动的任务时，复测提交前停止；既有任务结束后继续。客户又开始批量小红书任务时保留进度，仅只读核实已完成样本。VK 定时发布关闭，未发起发布。

结论：本轮小红书 DNS 配置修复已在客户端通过真实下载和实际文件核验。操作系统重启恢复、Windows 实机以及其余批量任务不在此 9 条验收结论内；俄文翻译两项仍未通过。完整逐文件摘要留存于本地远程支持证据，不包含入网密钥、Cookie 或带签名源 URL。

## 后续批量暴露的 V3 CDN 别名

继续观察客户自行运行的其他小红书任务，发现 7 条在下载阶段报 `DNS_NON_PUBLIC`，脱敏诊断均指向 `sns-video-v3.xhscdn.com`，与已通过的 9 条使用的 V6 CDN 不同。客户系统实际查询别名 `sns-video-v3.xhscdn.com.a.bdydns.com` 返回 `198.18.0.27`；可信 HTTPS DNS 同时核实后继别名 `opencdnxhsvod1.jomodns.com` 及其公网 A 记录。

第三版 `2026.10.16.3` 仅将这两个实测精确别名加入真实 IP 规则，同时在更新器 DNS 拨测中加入 V3 入口；不添加整个 `bdydns.com` / `jomodns.com` 厂商后缀。归档 `sr_ai_secure_final_20261016_3.conf`。先复现新检查失败，修改后 9 项 DNS 回归通过。第三版仍经正式入口部署，客户其余任务完成后再加载，不直接改生成配置。V3 实际复测结果另以远程支持回执记录。

## 第三版部署与补充验收

提交 `dca1ea80217da7f424a2b491d1a93fe0ef218a90` 发布校验通过。客户在线更新先后遇到 GitHub 超时和 TLS EOF，失败日志保留，均发生在配置写入前。改为支持端调用同一更新器的 `latest_release` / `download_snapshot` 验证最新提交、发布门禁及 Git blob 哈希；经已核实主机指纹的 SSH 传送快照，客户侧再验证归档 SHA256 与 manifest，并使用原正式安装器的 `SR_RELEASE_SHA` / `SR_RELEASE_DIR` 输入安装。不是直接修改客户 YAML，也未跳过发布或候选校验。

- 传送快照归档 SHA256：`a5ba892f2fc1a69bd6af81db6557ac3f4a751d70639ca102bcf68d625729168a`。
- 正式安装器退出 0、备份保留、候选通过内核校验。客户任务空闲后才重新加载 Clash；实际 TUN 开启，97 条直连、12 条代理规则已加载。
- V3、V6 入口及新增 V3 两个 CNAME 系统解析全部为公网 IP。
- 原来另报 DNS 错误的 7 条任务全部 completed，均完成视频、正文和俄文文案；独立读取全部 7 份 MP4，大小/SHA256 与媒体记录一致，FFprobe 通过。
- 本轮这 7 次实际媒体传输为 V2 CDN 六次、V3 CDN 一次，均成功；不能把解析器切换到 V2 的六次记成 V3 传输验证。
- 加上最初 9 条，本次独立文件核验覆盖 16 条，16/16 视频有效；任务结果为 14 completed、2 partial（原九条中的俄文翻译未通过），不把媒体成功扩大为全部翻译成功。

更新操作规范同步调整为：下载、校验期间保留所需代理网络，不切换订阅或编辑扩展；写入成功且任务空闲后再加载。客户正常在线更新仍使用既有入口。此次特殊网络失败由支持端传送同一已验证快照完成，没有更改客户账号、订阅凭据或全局代理环境变量。

## 新批次的稳定性边界与第四版

第三版 16 条视频已通过，不代表持续稳定。客户继续新增一批任务后，出现新的 V2/V3 下载 DNS 拒绝；配置和内核没有回退，系统解析链新增 `sns-video-v2.xhscdn.com.w.cdngslb.com`、`sns-video-bd.xhscdn.com.c8c10c27.cm.bdydns.com`、`hcdnv.ydbdxhsv6.cm.bdydns.com`。这说明继续逐条列举叶子别名不能覆盖 CDN 版本、区域和中间标签变化。

第四版 `2026.10.16.4` 在 Clash 中使用七条受限命名空间通配规则：只匹配包含 `xhscdn.com` 的专属 CNAME 分支，或已观察到的 `ydbdxhsv6` 平台标识；不排除整个 `bdydns.com`、`volcgtm.com`、`cdngslb.com` 等共享厂商区域。路由正文、Claude/Anthropic PROXY 与 skip-proxy 均不变。Shadowrocket 源仅同步三条实测精确别名，不混用 Clash 的中间层通配语法。归档 `sr_ai_secure_final_20261016_4.conf`。

按 [Mihomo 域名通配语义](https://wiki.metacubex.one/handbook/syntax/#_8)实现，并新增真实内核隔离测试：本地受控 UDP DNS 上游返回固定公网地址，六个未写死的新版本/区域别名必须得到公网 A 记录；五个无关厂商、相似拼写、恶意后缀和 AI 对照域名仍得到 fake-IP。测试不使用 TUN，不改系统 DNS，无外网依赖，结束后清理临时内核和 DNS 服务。本机十项 DNS 测试全部通过；无真实 Mihomo 的 CI 会明确 skip 此项，不能当作运行态通过。
