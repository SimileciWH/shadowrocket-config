---
name: update-shadocket-cfg
description: 当用户在 shadowrocket-config 仓库中要求处理 Shadowrocket 分流配置、某个网站或 App 无法访问、iCloud/CloudKit 同步失败、Claude/Anthropic 出口稳定性、fake-IP/TUN/系统代理/DIRECT/PROXY/always-real-ip/skip-proxy 规则、或 GitHub raw 规则发布时使用。用于先复现和定位，再按最小规则更新 sr_ai_secure_final.conf，归档版本，验证，提交推送，并确保 Claude/Anthropic 不被误改成直连。
---

# 更新 Shadowrocket 配置

## 1. 触发场景

当用户提到以下内容时触发本 skill：

- 某个 URL、网站、App、iCloud/CloudKit、PasteNow、国内站点、AI 服务在 Shadowrocket 下无法访问或超时。
- 需要判断某个域名应走 `DIRECT` 还是 `PROXY`。
- 需要修改 `sr_ai_secure_final.conf`、`versions/` 归档，或推送 GitHub raw 配置。
- 需要排查 `fake-IP`、`TUN`、`198.18.0.x`、`127.0.0.1:1082`、`always-real-ip`、`skip-proxy`、`bypass-tun`。
- 任何可能影响 Claude/Anthropic 出口稳定性的 Shadowrocket 规则修改。

## 2. 要做什么

- 先取证再改规则：用 `curl -w`、DoH、显式代理、物理网卡直连基线定位失败点。
- 需要诊断命令时加载 [diagnosis.md](references/diagnosis.md)。
- 需要决定规则形态或保护 Claude 时加载 [routing-safety.md](rules/routing-safety.md)。
- 需要编辑、归档、验证、提交、推送时加载 [publish.md](references/publish.md)。
- 需要最终汇报格式时加载 [report-template.md](templates/report-template.md)。
- 默认只改 GitHub raw 配置链路；除非用户明确要求，不直接改 Shadowrocket 运行态 DB。

## 3. 不要做什么

- 不要凭感觉直接把域名加进 `DIRECT` 或 `PROXY`。
- 不要只用 `ping` 或普通 `dig` 下结论；fake-IP/TUN 场景会误导。
- 不要把 Claude/Anthropic 从稳定 `PROXY` 路径误改到 `DIRECT`。
- 不要把 Claude/Anthropic 域名加进 `skip-proxy`。
- 不要为了一个站点失败而扩大到整类云厂商、整段 IP 或大量外链，除非证据支持。
- 不要提交代理节点、订阅链接、token、API key、Shadowrocket 运行数据库或本地私有配置。
