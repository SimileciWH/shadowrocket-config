# Shadowrocket & Clash Verge Rev 统一分流配置仓库

本项目提供 **Shadowrocket（iOS/Mac）** 与 **Clash Verge Rev（Windows/Mac/Linux）** 100% 规则对齐的双端分流配置体系。

> **核心原则**：本仓库仅维护路由规则与分流逻辑，**绝不保存**任何代理节点、订阅链接、账号密码、Token、API Key 或私有运行数据。

---

## 目录
- [全场景使用总览 (Quick Start by Scenario)](#全场景使用总览-quick-start-by-scenario)
  - [场景一：发给外部客户 / 朋友电脑（客户通用纯净版，推荐）](#场景一发给外部客户--朋友电脑客户通用纯净版推荐)
  - [场景二：个人工作电脑（工作定制版，带公司内网隧道）](#场景二个人工作电脑工作定制版带公司内网隧道)
  - [场景三：本地开发 / 短视频爬虫 / ClipVault 媒体解析下载](#场景三本地开发--短视频爬虫--clipvault-媒体解析下载)
  - [场景四：仅环境健康检查（只读体检模式，不改动任何文件）](#场景四仅环境健康检查只读体检模式不改动任何文件)
  - [场景五：Shadowrocket 手机端 (iOS / iPadOS) 导入与更新](#场景五shadowrocket-手机端-ios--ipados-导入与更新)
- [核心保障与双端一致性特性](#核心保障与双端一致性特性)
- [常见问题与验证排查 (FAQ)](#常见问题与验证排查-faq)
- [文件结构索引](#文件结构索引)
- [安全提交规范](#安全提交规范)

---

## 全场景使用总览 (Quick Start by Scenario)

先按**用途**选择模式，再按**操作系统**选择命令。Windows / Mac / Linux 不决定 work 模式，脚本不会根据电脑名称、账号或上次执行记录自动判断。

| 电脑 / 使用场景 | 选择 | 参数 | 说明 |
|---|---|---|---|
| 客户、朋友、普通个人电脑（Windows / Mac / Linux） | 非 work | 不加模式参数 | 不添加公司规则源和 1088 隧道节点 |
| 需要公司内网的工作电脑（Windows / Mac / Linux） | work | `--work` | 添加公司分流；需要另行建立本机 1088 SOCKS 隧道 |
| 只做 ClipVault、短视频下载，不访问公司内网 | 非 work | 不加模式参数 | 不因用途是开发而自动开启 work |
| 便携版 / 多套 Clash 数据目录 | 在上面模式基础上指定目录 | `--dir "实际数据目录"` | 指向包含 `profiles.yaml` 的目录，不是应用安装目录 |
| 只检查普通配置 | 非 work 候选检查 | `--check` | 不修改 Clash 配置 |
| 只检查工作配置 | work 候选检查 | `--work --check` | 不修改 Clash 配置 |
| 只验证线上版本是否完整 | 下载验证 | `--download-only` | 不执行安装器，不需要本机 Clash |
| Shadowrocket 手机 / 平板 | 使用场景五 | 不用 Python 参数 | 在 Shadowrocket 中更新配置 |

**每次更新都要带对参数**：工作电脑后续更新仍需 `--work`，默认不记忆上次模式。每次只更新指定数据目录中**当前激活的订阅**；多个订阅需要逐个激活后执行。同名订阅按 UID 区分。

**首次准备**：先安装 Clash Verge Rev、打开一次并导入/选中订阅，再关闭应用执行同步，最后重新打开并选择订阅。更新入口不会安装 Python、Clash 或创建公司 SSH 隧道。

Windows 需可用的 `python` 和 PyYAML；若系统使用 `py -3`，将下文所有 `python` 换成 `py -3`。可以先执行：

```powershell
python --version
python -m pip install PyYAML
```

Windows / Linux 内核若不在 PATH，需要设置 `CLASH_MIHOMO_BIN` 为实际内核路径。Windows 示例（请替换路径，不能照抄占位目录）：

```powershell
$env:CLASH_MIHOMO_BIN = 'C:\实际安装目录\verge-mihomo.exe'
```

macOS 自动检测标准安装路径；其他路径同样可以指定。找不到内核会停止，不会跳过校验。已完成 macOS 真实内核与 Linux CI 测试；Windows 安装和桌面流程仍需实机验收。

### 场景一：发给外部客户 / 朋友电脑（客户通用纯净版，默认推荐）

* **适用对象**：客户电脑、外部合作方、朋友电脑（支持 Windows 和 Mac）。
* **配置范围**：默认添加客户版规则，不新增公司 provider 或隧道节点；保留原订阅和客户自定义配置。默认模式不是清理或脱敏工具，曾使用工作配置的电脑可能保留已有公司节点或组。
* **备份与检查**：写入前创建 `sr-backup-*` 备份并校验候选，实际应用加载及网络结果需单独确认。
* **下载方式**：通过 GitHub 确认版本，经 CDN 或 GitHub 下载同版本文件；可用性取决于当地网络。

#### 1. Mac / Linux 用户

```bash
curl -fSL --max-time 60 https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/scripts/update_clash.py -o /tmp/update_clash.py && python3 /tmp/update_clash.py
```

#### 2. Windows 用户（PowerShell）

```powershell
$ErrorActionPreference = 'Stop'; Invoke-WebRequest https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/scripts/update_clash.py -OutFile "$env:TEMP\update_clash.py"; python "$env:TEMP\update_clash.py"
```

入口先查询 GitHub 当前提交及发布校验状态，再下载同一提交的安装脚本和三份规则，逐文件校验 Git blob 哈希。镜像只允许回退到同一提交，禁止回退旧版本。GitHub 不可达、限流、校验未完成或下载不完整时停止，不改本机配置。

**整套更新**：以后更新请重新执行上述入口。规则 URL 和本地缓存都绑定同一提交；24 小时 provider 刷新只检查该版本，不会自行混入下一版本。旧安装需执行一次新入口迁移。打开 Clash 重新选择订阅后，再验收实际加载和网络访问。

发布规范及环境依赖见 [同步与验收说明](scripts/README_clash_profile_sync.md)。

Windows 多机部署可使用 [Windows 部署脚本与验收说明](scripts/README_windows_deployment.md)：自动补齐 PyYAML 和后台服务、调用上述正式入口，并对齐会覆盖 Merge 的基础设置。需要先安装客户端并选中订阅；脚本完成后仍须验收实际网络。

#### 3. 客户生效确认：
1. 打开 Clash Verge Rev，激活当前配置：
   * 本地和远程订阅均重新选择当前配置（Select），让应用重新生成配置并加载扩展；检查无校验红框。
2. 确保代理模式为 **`规则 (Rule)`**，按需要开启 **`TUN 模式`** 或 **`系统代理 (System Proxy)`**。
3. 在浏览器访问目标网站，确认实际可用；终端文件写入成功不等于网络验收通过。

---

### 场景二：个人工作电脑（工作定制版，显式带 `--work`）

* **适用对象**：个人开发与办公电脑（需访问公司内网、Jenkins、内部代码仓）。
* **功能特性**：
  * 自动挂载 `127.0.0.1:1088` SSH 隧道节点，将 `realtek.com`、`realsil.com.cn`、`rtkbf.com` 及内网 IP 自动分流到 `CORP-WINDOWS` 出口。
  * 脚本不创建 SSH 隧道，也不保证 TUN 自动排除 Tailscale；使用公司隧道前需单独验证路由和 1088 监听状态。

#### 1. Mac / Linux 终端

```bash
curl -fSL --max-time 60 https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/scripts/update_clash.py -o /tmp/update_clash.py && python3 /tmp/update_clash.py --work
```

本地仓库使用 `python3 scripts/update_clash.py --work`；该入口更新到 GitHub 已验证的最新版本，不安装未发布的本地改动。

#### 2. Windows PowerShell

```powershell
$ErrorActionPreference = 'Stop'; Invoke-WebRequest https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/scripts/update_clash.py -OutFile "$env:TEMP\update_clash.py"; python "$env:TEMP\update_clash.py" --work
```

---

### 场景三：本地开发 / 短视频爬虫 / ClipVault 媒体解析下载

* **痛点根治**：
  许多视频解析工具（如 ClipVault、自研爬虫等）内置严格的 SSRF 安全防御机制。如果 Clash 的 Fake-IP 分配了 `198.18.x.x`（Benchmark 测速保留网段），爬虫会判定为非公网地址并直接阻断（报错 `UNSAFE_URL` / `DNS 返回非公网地址`）。
* **解决机制**：
  脚本对 `v.douyin.com`、`www.iesdouyin.com`、`www.douyin.com`、已有抖音 CDN 域名，以及本轮实际观察到的 10 个 CNAME 别名配置 Real-IP 增量合并。仅排除主域名不够：macOS 可能继续解析 `www.iesdouyin.com.bytedns1.com` 等别名并收到假 IP。别名使用精确主机名，不扩大到整个 CDN 厂商后缀：
  * 若当前为 `blacklist` 黑名单模式：自动将域名加入 `fake-ip-filter`，确保**直接返回真实公网 IP**。
  * 若当前为 `whitelist` 白名单模式：自动将域名从过滤列表中剔除，确保**返回真实公网 IP**。
* **验证真实 IP 命令**：
  ```bash
  python3 -c "import socket; [print(h, sorted({r[4][0] for r in socket.getaddrinfo(h, 443, type=socket.SOCK_STREAM)})) for h in ['v.douyin.com', 'www.iesdouyin.com', 'www.douyin.com']]"
  ```
  预期结果：所有返回地址均为公网 IP，不能混入 `198.18.0.0/15`、回环或其他非公网地址。`--check` 使用同一路径，不再用 `dig` 的成功结果代替应用解析结果。

* **生效与验收**：更新脚本后重新执行并激活配置。Rule-Provider 的定时更新只更新路由规则，不会自动补充本机 DNS 过滤列表；Shadowrocket 则更新配置中的 `always-real-ip`。配置生效后先验证上述系统解析，再重试失败素材并核验文件。短暂 DoH 超时与假 IP 是两类问题，不要关闭应用安全校验。
* 本轮案例及验证边界见 [抖音 CNAME 假 IP 修复记录](versions/20261005-douyin-cname-validation.md)。
* **重启恢复**：DNS 规则必须保存到当前配置的持久 Merge 扩展，并验证重新激活后仍生效。需要登录后自动恢复代理时，启用 Clash 自动启动或已验证的用户登录启动任务；本一键脚本不会自动更改登录项。

---

### 场景四：仅环境健康检查（不修改 Clash 配置）

先按场景一或二下载 `update_clash.py`，再执行相应命令：

| 用途 | Windows PowerShell | Mac / Linux |
|---|---|---|
| 普通配置检查 | `python "$env:TEMP\update_clash.py" --check` | `python3 /tmp/update_clash.py --check` |
| 工作配置检查 | `python "$env:TEMP\update_clash.py" --work --check` | `python3 /tmp/update_clash.py --work --check` |
| 仅验证线上发布 | `python "$env:TEMP\update_clash.py" --download-only` | `python3 /tmp/update_clash.py --download-only` |
| 指定普通配置目录并更新 | `python "$env:TEMP\update_clash.py" --dir "C:\实际数据目录"` | `python3 /tmp/update_clash.py --dir "/实际数据目录"` |
| 指定工作配置目录并更新 | `python "$env:TEMP\update_clash.py" --work --dir "C:\实际数据目录"` | `python3 /tmp/update_clash.py --work --dir "/实际数据目录"` |

`--check` 构造并校验对应模式的候选，检查规则源、当前代理访问和 DNS 状态。它不会写入配置，也不证明运行中的配置已经与候选一致。入口会下载临时文件，结束后清理。

---

### 场景五：Shadowrocket 手机端 (iOS / iPadOS) 导入与更新

#### 1. 稳定导入 URL：
```text
https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/sr_ai_secure_final.conf
```

#### 2. 使用与更新方法：
- 在 Shadowrocket 底栏点击 **“配置 (Config)”** -> **“添加配置 (Add Configuration)”** -> 粘贴上方 URL 下载。
- 点击该配置文件右侧的“圆圈 i”图标可查看详情，点击 **“更新 (Update)”** 即可拉取最新规则，无需重新传文件。
- 手机端仅同步路由规则，应用内已保存的节点信息完全不受影响。

---

## 核心保障与双端一致性特性

1. **出站策略组自适应识别**：
   根据当前订阅的真实代理组绑定规则，写入 Rules 扩展并进行内核候选校验；无法确定目标时停止，不回退到 DIRECT。
2. **微信/QQ 全媒体极速直连**：
   采用“进程级直连 + 关键词直连 + 腾讯全系 Real-IP”三重保障，彻底杜绝微信发高清图片、语音通话转圈与超时问题。
3. **国内大厂 100% 直连**：
   小红书、抖音、快手、微博、B站、支付宝等国内主流服务自动直连，不耗费代理流量，速度拉满。
4. **海外 AI 工具智能保护**：
   Claude (Anthropic)、OpenAI (ChatGPT) 敏感流量强制指定走高质量代理出口。
5. **同版本整套更新**：
   Clash 端挂载固定提交的 Classical Rule-Provider；新版本通过更新入口整套切换，避免脚本与规则混用。

---

## 常见问题与验证排查 (FAQ)

### Q1: 在 Clash Verge Rev 开启 TUN 模式时弹红框报错？
- **原因**：部分配置中主代理组叫 `PROXY`，而旧规则硬编码了 `节点选择`。
- **解决**：直接重新执行场景一的单行命令，脚本会检查当前订阅的真实代理组并修正规则引用；重新选择配置后，还需确认内核和网络正常。

### Q2: 为什么终端 curl 报 `Failed to connect after 2 ms`？
- **原因**：此前运行过 Shadowrocket 或其他代理软件，退出后残留了旧系统代理端口（如 1082）。
- **解决**：打开 Clash Verge Rev，拨动一次 **【系统代理 (System Proxy)】** 开关（关一次再开），即可自动将系统代理修正覆盖为 7897 端口。

### Q3: 微信发图或视频仍失败怎么办？
- 部署成功不能保证所有应用网络都可用。分别检查当前规则命中、系统 DNS 返回、代理/TUN 接管和目标站点响应。
- 当前安装器写入持久扩展，不会强制改写运行态 TUN 协议栈、MTU 或系统代理开关。排查后再做有证据的最小修改。

### Q4: 能否同时开启 Clash Verge Rev 和 Shadowrocket？
- **原因**：两者都会接管系统网络代理与虚拟 TUN 网卡（如 7897 vs 1082），同时开启会导致流量冲突、端口竞争或连接中断 (EOF)。
- **解决**：在验证或使用 Clash Verge Rev 时，请先将 Shadowrocket 断开连接；同样使用 Shadowrocket 时关闭 Clash 即可。

### Q5: 为什么 `dig` 返回公网 IP，应用仍报 `UNSAFE_URL`？
- `dig` 直接查询 DNS 服务，与 macOS 应用的系统解析路径不完全相同。系统可能继续查询 CNAME 别名，而别名仍被分配假 IP。
- 使用场景三的 `socket.getaddrinfo` 命令核实全部地址；若不一致，可用 `dns-sd -G v4 www.iesdouyin.com` 查看 macOS 实际返回的别名及地址（完成后按 Ctrl+C 停止）。
- 将实际观察到的别名加入 Real-IP 规则后重新激活配置；单纯清缓存不一定解决。不要把主域名的 `dig` 成功当作下载通过。

### Q6: Windows 执行提示 `Proxy CONNECT aborted` 或 `未找到数据目录`？
- **`curl: (56) Proxy CONNECT aborted` 解决**：
  * 说明 Windows 系统代理中残留了已失效的旧端口设置。
  * **解决**：先确认系统代理指向实际运行的 Clash 端口；旧代理失效时在 Windows 网络设置中修正，然后重试场景一的新入口。
- **`未找到 Clash Verge Rev 数据目录` 或 `未找到 profiles.yaml` 解决**：
  * **原因 1（初次安装未运行）**：刚安装好客户端，但从未双击打开过（Clash Verge Rev 只有在初次启动时才会自动生成 AppData 基础目录）。
  * **原因 2（未导入节点订阅）**：打开了客户端，但在【配置 (Profiles)】中尚未添加任何机场订阅。
  * **解决**：先双击打开一次 Clash Verge Rev，在【配置 (Profiles)】中导入您的订阅链接并点击选中激活，然后重新运行本脚本即可！
  * **便携绿色版用户**：若使用的是解压版且安装在自定义路径，可直接指定 `--dir` 参数运行（如 `python "$env:TEMP\update_clash.py" --dir "C:\你的路径\config"`）。

---

## 文件结构索引

```text
├── README.md                           # 全场景使用指南与运维文档
├── sr_ai_secure_final.conf             # Shadowrocket 手机端/Mac端主规则基准文件
├── clash/                              # Clash Verge 自动对齐规则集
│   ├── rules_direct.yaml               # 国内直连规则库（小红书/抖音/快手等）
│   ├── rules_proxy.yaml                # AI 与海外代理规则库（Claude/OpenAI等）
│   ├── rules_company.yaml              # 公司内网与研发系统专用分流规则库
│   ├── client_merge_template.yaml      # 客户纯净版 Merge 扩展手工模板
│   └── work_merge_template.yaml        # 个人工作版 Merge 扩展手工模板
└── scripts/
    ├── update_clash.py                 # 统一更新入口，验证提交与文件哈希
    ├── setup_clash_verge.py            # 由更新入口调用的配置安装器
    └── sync_clash.py                   # 双端规则自动转换生成脚本
```

---

## 安全提交规范

任何向本仓库推送的改动，必须遵守以下安全合规红线：
1. **严禁包含节点凭据**：禁止提交 `ss://`、`vmess://`、`vless://`、`trojan://` 等任何真实节点链接。
2. **严禁包含敏感凭证**：禁止提交密码、Token、API Key、公司密钥。
3. **保持增量幂等**：任何脚本修改均需保障多次重复运行无副作用、不产生重复规则行。
