# 汇报模板

## 已定位并修改

定位结果：

- 失败路径：`当前路径/显式代理/其他`，现象：`超时/证书/TLS/HTTP code`
- 可用路径：`en0 直连/代理/其他`，证据：`HTTP code、耗时、remote_ip、size`
- 结论：`应走 DIRECT/PROXY/保持不变`

改动内容：

- `sr_ai_secure_final.conf`
- `versions/sr_ai_secure_final_YYYYMMDD[_N].conf`
- 规则：`always-real-ip`、`skip-proxy`、`DOMAIN-SUFFIX`

验证：

- `git diff --check`
- 归档一致性
- 敏感信息扫描
- Claude/Anthropic 规则检查
- GitHub raw 链接检查

发布：

- commit: `<hash> <message>`
- raw: `https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/sr_ai_secure_final.conf`

用户操作：

- 在 Shadowrocket Configuration 中点击 `Update`。

## 仅诊断未修改

定位结果：

- 当前路径：
- 显式代理路径：
- 真实 DNS / DoH：
- 直连基线：

建议：

- 推荐规则：
- 风险：
- 下一步需要用户确认：
