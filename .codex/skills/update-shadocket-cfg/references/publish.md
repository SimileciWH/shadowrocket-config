# 编辑、归档与发布

## 编辑范围

通常只改：

- `sr_ai_secure_final.conf`
- `versions/sr_ai_secure_final_YYYYMMDD[_N].conf`

不要改本地 Shadowrocket 运行态 DB，除非用户明确要求 reload 运行态。

## 版本命名

- 当天第一次：`versions/sr_ai_secure_final_YYYYMMDD.conf`
- 当天追加：`versions/sr_ai_secure_final_YYYYMMDD_2.conf`、`_3.conf`
- 如果已有当天归档，使用下一个后缀。

同步归档：

```bash
cp sr_ai_secure_final.conf versions/sr_ai_secure_final_YYYYMMDD[_N].conf
```

## 必跑校验

```bash
git diff --check
cmp -s sr_ai_secure_final.conf versions/sr_ai_secure_final_YYYYMMDD[_N].conf && echo 'stable and archive are identical'
rg -n '目标域名|Config Version|Change:' sr_ai_secure_final.conf versions/sr_ai_secure_final_YYYYMMDD[_N].conf
rg -n 'claude|anthropic|skip-proxy|always-real-ip' sr_ai_secure_final.conf
rg -n -i 'ss://|vmess://|vless://|trojan://|password|passwd|token|api[_-]?key|secret|订阅|节点' sr_ai_secure_final.conf versions/sr_ai_secure_final_YYYYMMDD[_N].conf README.md || true
```

## 提交与推送

只 stage 相关文件：

```bash
git add sr_ai_secure_final.conf versions/sr_ai_secure_final_YYYYMMDD[_N].conf
git commit -m 'Route example direct'
git push origin main
```

推送后验证远端和 raw：

```bash
git ls-remote origin refs/heads/main
curl -fsSL --max-time 20 https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/sr_ai_secure_final.conf \
  | rg -n 'Config Version|Change:|目标域名'
```

如果用户只要求总结或本地准备，不要提交推送。
