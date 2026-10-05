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

### 场景一：发给外部客户 / 朋友电脑（客户通用纯净版，默认推荐）

* **适用对象**：客户电脑、外部合作方、朋友电脑（支持 Windows 和 Mac）。
* **安全承诺**：
  * **0 隐私风险**：**默认彻底剥离任何公司内网信息**（不含 realtek/realsil/rtkbf 规则及公司隧道节点），绝对不泄漏公司私密。
  * **微信全流程直连**：彻底解决 TUN 模式下微信发文字、发图片、大文件上传被卡住的问题。
  * **无损增量合并**：修改前自动创建 `.bak` 备份，**严格保留**客户原有的机场订阅和代理节点。
  * **国内高速直连**：脚本与规则集托管于 jsDelivr CDN，免翻墙即可秒级拉取。

#### 1. Mac 用户（终端 Terminal 执行单行命令）
```bash
curl -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python3
```

#### 2. Windows 用户（PowerShell 执行单行命令，任选其一）
按快捷键 `Win + X` 打开 **Windows PowerShell**，粘贴并回车：

* **方式 1（推荐，写入临时文件执行，彻底避免管道编码乱码）：**
  ```powershell
  irm https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py -OutFile $env:TEMP\setup_clash.py; python $env:TEMP\setup_clash.py
  ```
* **方式 2（跨平台纯 Python 指令，全系统通用）：**
  ```powershell
  python -c "import urllib.request; exec(urllib.request.urlopen('https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py').read().decode('utf-8'))"
  ```
* **方式 3（单行管道执行，需前置声明 UTF-8 输出编码）：**
  ```powershell
  $OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; irm https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python -
  ```

#### 3. 客户生效确认（仅需 2 步）：
1. 打开 Clash Verge Rev，激活当前配置：
   * 若配置为 **远程订阅链接导入**：右键点击该配置 -> 选择 **“刷新 (Refresh)”**。
   * 若配置为 **本地文件导入 (Local)**：直接点击该配置卡片切换一下（或右键选择 **“Select”**）。
2. 确保代理模式为 **`规则 (Rule)`**（禁止使用 Global 全局），开启 **`TUN 模式`** 或 **`系统代理 (System Proxy)`** 均可。

---

### 场景二：个人工作电脑（工作定制版，显式带 `--work`）

* **适用对象**：个人开发与办公电脑（需访问公司内网、Jenkins、内部代码仓）。
* **功能特性**：
  * 自动挂载 `127.0.0.1:1088` SSH 隧道节点，将 `realtek.com`、`realsil.com.cn`、`rtkbf.com` 及内网 IP 自动分流到 `CORP-WINDOWS` 出口。
  * TUN 虚拟网卡自动排除 Tailscale（`100.64.0.0/10`）与局域网网段，防止劫持公司跳板机隧道。

#### 1. Mac / Linux 终端：
```bash
# 云端拉取执行：
curl -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python3 - --work

# 或本地仓库直接执行：
python3 scripts/setup_clash_verge.py --work
```

#### 2. Windows PowerShell：
```powershell
# 推荐执行：
irm https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py -OutFile $env:TEMP\setup_clash.py; python $env:TEMP\setup_clash.py --work

# 或纯 Python 通用执行：
python -c "import sys, urllib.request; sys.argv.append('--work'); exec(urllib.request.urlopen('https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py').read().decode('utf-8'))"
```

---

### 场景三：本地开发 / 短视频爬虫 / ClipVault 媒体解析下载

* **痛点根治**：
  许多视频解析工具（如 ClipVault、自研爬虫等）内置严格的 SSRF 安全防御机制。如果 Clash 的 Fake-IP 分配了 `198.18.x.x`（Benchmark 测速保留网段），爬虫会判定为非公网地址并直接阻断（报错 `UNSAFE_URL` / `DNS 返回非公网地址`）。
* **解决机制**：
  脚本已对 `v.douyin.com`、`www.iesdouyin.com`、`www.douyin.com` 及全系抖音 CDN 域名（`zjcdn.com`、`ydycdn.com` 等）配置智能 Real-IP 增量合并：
  * 若当前为 `blacklist` 黑名单模式：自动将域名加入 `fake-ip-filter`，确保**直接返回真实公网 IP**。
  * 若当前为 `whitelist` 白名单模式：自动将域名从过滤列表中剔除，确保**返回真实公网 IP**。
* **验证真实 IP 命令**：
  ```bash
  python3 -c "import socket; print('v.douyin.com:', socket.gethostbyname('v.douyin.com')); print('www.douyin.com:', socket.gethostbyname('www.douyin.com'))"
  ```
  预期结果：输出均为真实电信/联通/CDN 公网 IP，**绝无 `198.18.x.x`**。

---

### 场景四：仅环境健康检查（只读体检模式，不改动任何文件）

* **适用对象**：想先检查当前 Clash 与基准规则的一致性，不想改动任何配置文件。
* **执行命令**：
  ```bash
  python3 scripts/setup_clash_verge.py --check
  ```
* **检查维度**：
  * 检测云端规则集（GitHub Raw / CDN 镜像）网络可达性与规则条数。
  * 探测小红书、抖音、快手、微信多媒体及 Claude 的实时分流响应。
  * 拨测核心域名是否仍被 Fake-IP 劫持。
  * 输出 10 项环境一致性对比看板（`完全一致 (MATCH)` / `不一致 (DIFF)`）。

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
   自动识别用户当前配置中主代理组命名（无论是 `PROXY`、`Proxy` 还是 `节点选择`），自适应绑定规则并注入别名映射，**开启 TUN 网卡接管模式绝不报错阻断**（彻底解决 `proxy [节点选择] not found` 异常）。
2. **微信/QQ 全媒体极速直连**：
   采用“进程级直连 + 关键词直连 + 腾讯全系 Real-IP”三重保障，彻底杜绝微信发高清图片、语音通话转圈与超时问题。
3. **国内大厂 100% 直连**：
   小红书、抖音、快手、微博、B站、支付宝等国内主流服务自动直连，不耗费代理流量，速度拉满。
4. **海外 AI 工具智能保护**：
   Claude (Anthropic)、OpenAI (ChatGPT) 敏感流量强制指定走高质量代理出口。
5. **24 小时静默静默同步**：
   Clash 端挂载 Classical Rule-Provider，每 24 小时静默从 CDN 自动更新规则集，双端长期保持最新。

---

## 常见问题与验证排查 (FAQ)

### Q1: 在 Clash Verge Rev 开启 TUN 模式时弹红框报错？
- **原因**：部分配置中主代理组叫 `PROXY`，而旧规则硬编码了 `节点选择`。
- **解决**：直接重新执行场景一的单行命令，脚本会自动探测当前配置的主组名并建立映射，执行后右键刷新配置即可正常开启 TUN。

### Q2: 为什么终端 curl 报 `Failed to connect after 2 ms`？
- **原因**：此前运行过 Shadowrocket 或其他代理软件，退出后残留了旧系统代理端口（如 1082）。
- **解决**：打开 Clash Verge Rev，拨动一次 **【系统代理 (System Proxy)】** 开关（关一次再开），即可自动将系统代理修正覆盖为 7897 端口。

### Q3: 为什么微信在开启 TUN 模式下发送图片/视频提示红色感叹号？
- **原因**：
  1. **IPv6 假死黑洞**：Clash Verge 默认开启 IPv6，TUN 虚拟网卡接管了全局 IPv6 路由，但用户物理 Wi-Fi 没有公网 IPv6，微信优先发起的 IPv6 握手死锁超时。
  2. **用户态协议栈缓冲瓶颈**：TUN 默认使用的 `gvisor` 用户态栈在处理连续大文件上传（如数兆的高清图/视频）时，存在 TCP Window Scaling 缺陷导致缓冲区溢出丢包，腾讯 CDN 服务器超时断开。
  3. **虚拟网卡 MTU 错配**：macOS 虚拟网卡默认 MTU 9000 发生以太网（MTU 1500）巨帧分片丢弃。
- **解决**：最新一键脚本已强制关闭 IPv6（与 Shadowrocket 对齐）、将 TUN 协议栈深度优化为 `stack: mixed`（TCP 走系统内核原生高性能网络栈）并对齐 MTU 1500，同时注入微信全系进程直连与 Real-IP 过滤。客户直接执行场景一的一键命令即可彻底根治，TUN 模式下秒发大图与高清视频。

### Q4: 能否同时开启 Clash Verge Rev 和 Shadowrocket？
- **原因**：两者都会接管系统网络代理与虚拟 TUN 网卡（如 7897 vs 1082），同时开启会导致流量冲突、端口竞争或连接中断 (EOF)。
- **解决**：在验证或使用 Clash Verge Rev 时，请先将 Shadowrocket 断开连接；同样使用 Shadowrocket 时关闭 Clash 即可。

### Q5: 如何确认抖音等短视频已正常获得真实 IP？
- 在终端运行：
  ```bash
  dig @127.0.0.1 -p 1053 v.douyin.com +short
  ```
  若返回形如 `117.68.x.x` 或 `155.102.x.x` 的公网地址（而非 `198.18.x.x`），即表示 Real-IP 已成功生效。

### Q6: Windows 执行提示 `Proxy CONNECT aborted` 或 `未找到数据目录`？
- **`curl: (56) Proxy CONNECT aborted` 解决**：
  * 说明 Windows 系统代理中残留了已失效的旧端口设置。
  * **解决**：改用 PowerShell 原生推荐命令 `irm ... -OutFile $env:TEMP\setup_clash.py; python $env:TEMP\setup_clash.py`，或在 Windows **设置 -> 网络和 Internet -> 代理** 中关闭手动代理开关。
- **`未找到 Clash Verge Rev 数据目录` 或 `未找到 profiles.yaml` 解决**：
  * **原因 1（初次安装未运行）**：刚安装好客户端，但从未双击打开过（Clash Verge Rev 只有在初次启动时才会自动生成 AppData 基础目录）。
  * **原因 2（未导入节点订阅）**：打开了客户端，但在【配置 (Profiles)】中尚未添加任何机场订阅。
  * **解决**：先双击打开一次 Clash Verge Rev，在【配置 (Profiles)】中导入您的订阅链接并点击选中激活，然后重新运行本脚本即可！
  * **便携绿色版用户**：若使用的是解压版且安装在自定义路径，可直接指定 `--dir` 参数运行（如 `python setup_clash.py --dir "C:\你的路径\config"`）。

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
    ├── setup_clash_verge.py            # 全自动化一键对齐与环境核验工具（全平台通用）
    └── sync_clash.py                   # 双端规则自动转换生成脚本
```

---

## 安全提交规范

任何向本仓库推送的改动，必须遵守以下安全合规红线：
1. **严禁包含节点凭据**：禁止提交 `ss://`、`vmess://`、`vless://`、`trojan://` 等任何真实节点链接。
2. **严禁包含敏感凭证**：禁止提交密码、Token、API Key、公司密钥。
3. **保持增量幂等**：任何脚本修改均需保障多次重复运行无副作用、不产生重复规则行。
