# 诊断流程

## 目标

确认失败发生在系统代理、Shadowrocket TUN/fake-IP、代理出口、DNS/CDN edge，还是网站本身。

## 基础状态

```bash
git status -sb
scutil --proxy
route -n get default
dscacheutil -q host -a name example.com
```

判断要点：

- `198.18.0.x` 通常表示 fake-IP/TUN 已接管。
- `127.0.0.1:1082` 表示系统 HTTP(S) 代理路径。
- `skip-proxy` 是绕过 macOS 本地 HTTP proxy 入口；`DIRECT` 是流量进入 Shadowrocket 后的路由判定，两者不是一回事。

## 访问对照

```bash
fmt='dns=%{time_namelookup} conn=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total} code=%{http_code} ip=%{remote_ip} url=%{url_effective}\n'

curl -L -sS -o /tmp/site-current.out -m 15 \
  -w "$fmt" 'https://example.com/path'

curl -L -sS -o /tmp/site-proxy.out -m 15 \
  --proxy http://127.0.0.1:1082 \
  -w "$fmt" 'https://example.com/path'

curl -sS -m 10 \
  'https://dns.google/resolve?name=example.com&type=A'
```

如果 DoH 查到真实 A 记录，用物理网卡做直连基线：

```bash
curl -L -sS -o /tmp/site-direct.out -m 15 \
  --interface en0 --noproxy '*' \
  --resolve example.com:443:REAL_IP \
  -w "$fmt" 'https://example.com/path'
```

## 结论模式

- 当前路径和显式代理都超时，但 `en0` 直连真实 IP 返回 `200`：优先小范围 `DIRECT`。
- 当前路径失败，但显式代理成功：优先小范围 `PROXY`。
- 规则显示 `DIRECT` 但仍慢：比较 DoH 结果、真实 edge IP、`curl -w` 分段时间，不要只重复规则结论。
- 页面能打开但资源缺失：先检查主站和关键资源域名，不要一次性加入页面所有外链。
