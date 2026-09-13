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

## Files

- `sr_ai_secure_final.conf`: 稳定导入入口，手机端应使用这个 URL。
- `versions/`: 历史版本归档，用于回滚和对比。

## Safety

提交前请检查不要包含：

- 代理节点或订阅链接：`ss://`、`vmess://`、`vless://`、`trojan://`
- 账号、邮箱、密码、token、API key
- Shadowrocket 运行数据库、备份数据库或本地私有配置
