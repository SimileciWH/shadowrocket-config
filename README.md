# Shadowrocket Config

这个仓库只保存 Shadowrocket 规则配置，不保存代理节点、订阅链接、账号、密码、token、API key 或本地运行数据库。

## Import URL

```text
https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/sr_ai_secure_final.conf
```

在 Shadowrocket 里通过 URL 添加或下载配置后，后续只要继续更新仓库里的 `sr_ai_secure_final.conf`，手机端使用同一个 URL 更新配置即可，不需要再次传文件。

## Mac 公司网络分流

Mac 统一使用 `sr_ai_secure_final.conf`，不再维护独立的公司规则配置。

- `ezgo.realsil.com.cn` 精确匹配后直连 Mac 本地网络。
- `realtek.com`、`realsil.com.cn`、`rtkbf.com` 的其余匹配流量使用应用内已有的 `CORP-WINDOWS` 节点。
- 原有国内直连、局域网与默认 VPS 规则保留。

`CORP-WINDOWS` 是本机已有的 SOCKS5 节点，地址为 `127.0.0.1:1088`，由 Mac 的登录服务维护 SSH 隧道到公司 Windows。它和 VPS 节点一样保存在 Shadowrocket 应用中，仓库只引用节点名称。其他设备需要自行配置可用的公司出口，不能仅导入规则就获得这台 Mac 的隧道。

配置内的 `update-url` 指向上述稳定 GitHub raw 地址。在 Shadowrocket 中选择 `sr_ai_secure_final.conf` →“更新”，即可下载仓库 `main` 分支的最新规则。更新只同步规则，应用中的 VPS 和 `CORP-WINDOWS` 节点仍独立保存。

## 俄罗斯网站分流

版本 `2026.09.27-3` 将以下目标固定交给应用内已有的 `justg-vps-RU-direct` 节点：

- VK 主站、登录/API 子域名，以及已列出的图片、音视频和 CDN 域名。
- `.ru`、`.su`、`.рф` 域名，以及固定版本的俄罗斯服务域名规则集（包含部分非 `.ru` 域名）。
- 未命中前面域名策略、且 GeoIP 判断为俄罗斯的目标 IP。

其他流量继续遵循原规则；`FINAL,PROXY` 保持不变，因此默认代理仍可选 BWG。俄罗斯规则直接指定 JustG，不通过自动选择或故障回退组切换到 BWG。使用时需要选择“配置”分流模式，并确保本机已导入名称完全一致的 `justg-vps-RU-direct` 节点；规则文件不包含节点凭据。

域名规则集固定于 MetaCubeX/meta-rules-dat 的 `f77c0e1442146059a2c6357721f43d19542d1734` 快照，更新时需重新核验。域名归属和 IP 地理库不能识别所有俄罗斯网站，后续遗漏可按具体域名补充。原有 Claude/Anthropic、公司网络和国内直连规则保留。

仓库规则更新与客户端启用是两个步骤：发布到 `main` 后，再在 Shadowrocket 中更新配置。实际出口需从客户端连接记录核验；本次路由变更不修改 DNS 设置，也不代表完成 DNS 泄漏验收。

## Files

- `sr_ai_secure_final.conf`: 稳定导入入口，手机端应使用这个 URL。
- `versions/`: 历史版本归档，用于回滚和对比。

## Safety

提交前请检查不要包含：

- 代理节点或订阅链接：`ss://`、`vmess://`、`vless://`、`trojan://`
- 账号、邮箱、密码、token、API key
- Shadowrocket 运行数据库、备份数据库或本地私有配置
