# Shadowrocket Config

这个仓库只保存 Shadowrocket 规则配置，不保存代理节点、订阅链接、账号、密码、token、API key 或本地运行数据库。

## Import URL

```text
https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/sr_ai_secure_final.conf
```

在 Shadowrocket 里通过 URL 添加或下载配置后，后续只要继续更新仓库里的 `sr_ai_secure_final.conf`，手机端使用同一个 URL 更新配置即可，不需要再次传文件。

## Files

- `sr_ai_secure_final.conf`: 稳定导入入口，手机端应使用这个 URL。
- `versions/`: 历史版本归档，用于回滚和对比。

## Safety

提交前请检查不要包含：

- 代理节点或订阅链接：`ss://`、`vmess://`、`vless://`、`trojan://`
- 账号、邮箱、密码、token、API key
- Shadowrocket 运行数据库、备份数据库或本地私有配置
