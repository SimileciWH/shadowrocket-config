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

## Clash Verge 同步配置

仓库同时为 Clash Verge (Rev) 自动维护一份严格对齐的规则集（位于 `clash/` 目录），由 `scripts/sync_clash.py` 自动从 `sr_ai_secure_final.conf` 转换生成。

### 一键配置与状态一致性校验（推荐）

#### 1. 发给客户 / 朋友的单行命令（客户通用纯净版，0 公司隐私，开箱即用）：

* **Mac / Linux 终端**：
  ```bash
  curl -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python3
  ```

* **Windows PowerShell 终端（任选其一）**：
  ```powershell
  # 推荐方式 1（PowerShell 原生，免装额外工具）：
  irm https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python -

  # 方式 2（调用 Windows 10/11 内置 curl.exe）：
  curl.exe -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python -
  ```

* **跨平台纯 Python 指令（全系统通用）**：
  ```bash
  python -c "import urllib.request; exec(urllib.request.urlopen('https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py').read().decode('utf-8'))"
  ```

#### 2. 个人工作电脑命令（个人工作定制版，带公司 1088 SSH 隧道与内部服务分流）：

* **Mac / Linux 终端**：
  ```bash
  curl -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python3 - --work
  # 或本地运行：
  python3 scripts/setup_clash_verge.py --work
  ```

* **Windows PowerShell 终端**：
  ```powershell
  irm https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python - --work
  ```

### 手动接入方式（Merge 扩展）

* **客户纯净版**：使用 [`clash/client_merge_template.yaml`](clash/client_merge_template.yaml)
* **个人工作版**：使用 [`clash/work_merge_template.yaml`](clash/work_merge_template.yaml)

在 Clash Verge Rev 中打开 **订阅 (Profiles)** -> 找到你的主配置（如 `bwg-cal`）-> 右键选择 **编辑扩展配置 (Edit Merge)**，将 [`clash/clash_merge_template.yaml`](clash/clash_merge_template.yaml) 的内容粘贴保存即可：

```yaml
rule-providers:
  sr-direct:
    type: http
    behavior: classical
    format: yaml
    interval: 86400
    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_direct.yaml"
    path: ./ruleset/sr-direct.yaml

  sr-proxy:
    type: http
    behavior: classical
    format: yaml
    interval: 86400
    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_proxy.yaml"
    path: ./ruleset/sr-proxy.yaml

  sr-company:
    type: http
    behavior: classical
    format: yaml
    interval: 86400
    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_company.yaml"
    path: ./ruleset/sr-company.yaml

prepend-proxy-groups:
  - name: CORP-WINDOWS
    type: select
    proxies:
      - DIRECT
      - 节点选择

  - name: justg-vps-RU-direct
    type: select
    proxies:
      - 节点选择
      - DIRECT

prepend-rules:
  - RULE-SET,sr-company,CORP-WINDOWS
  - RULE-SET,sr-proxy,节点选择
  - RULE-SET,sr-direct,DIRECT
  - GEOIP,LAN,DIRECT,no-resolve
  - GEOIP,CN,DIRECT
  - MATCH,节点选择
```

配置后，Clash Verge 启动系统代理即可无缝继承全量直连与分流规则，并在后台每 24h 自动静默拉取 GitHub 最新规则。

## Files

- `sr_ai_secure_final.conf`: Shadowrocket 稳定导入入口。
- `clash/`: Clash Verge 规则集（`rules_direct.yaml`、`rules_proxy.yaml`、`clash_rules.yaml` 等）。
- `scripts/sync_clash.py`: 自动化双端规则同步脚本。
- `versions/`: 历史版本归档，用于回滚和对比。

## Safety

提交前请检查不要包含：

- 代理节点或订阅链接：`ss://`、`vmess://`、`vless://`、`trojan://`
- 账号、邮箱、密码、token、API key
- Shadowrocket 运行数据库、备份数据库或本地私有配置
