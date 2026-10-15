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

## 验证

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
