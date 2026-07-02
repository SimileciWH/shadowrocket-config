# 路由安全规则

## Claude/Anthropic 硬边界

每次修改前后都检查：

```bash
rg -n 'claude|anthropic|skip-proxy|always-real-ip' sr_ai_secure_final.conf
```

必须保持：

- `claude.ai`、`claude.com`、`anthropic.com`、`claudeusercontent.com` 强制 `PROXY`。
- 不把 Claude/Anthropic 域名加入 `skip-proxy`。
- 不新增会吞掉 Claude/Anthropic 的宽泛 `DIRECT` 规则、云厂商后缀或 IP 段。
- 除非用户明确要求“调整 Claude 路由”，否则 Claude 相关规则只验证，不顺手改。

## DIRECT 三层规则

当证据支持某域名直连时，优先加三层最小规则：

```ini
always-real-ip = ...,example.com,*.example.com,...
skip-proxy = ...,example.com,*.example.com,...

# Example direct
DOMAIN-SUFFIX,example.com,DIRECT
```

适用：国内站、CloudKit/iCloud、某些 CDN/EdgeOne 域名在代理或 fake-IP 路径超时，但真实直连可用。

## PROXY 规则

当证据支持代理路径更稳定时：

```ini
DOMAIN-SUFFIX,example.com,PROXY
```

同时确认该域名没有被误放进 `skip-proxy`。是否加入 `always-real-ip` 要有证据，不默认添加。

## 收敛原则

- 先加失败主域名，不加页面所有外链。
- 优先域名规则，不写死临时 IP。
- 不为了一个 URL 扩大到整个云厂商或整个 IP 段。
- AI 敏感域名、IP 检测站、国内直连站分区摆放，避免后续误读。
