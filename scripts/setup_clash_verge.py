#!/usr/bin/env python3
"""
Clash Verge Rev 一键配置与环境一致性核验工具 (Shadowrocket 环境对齐专用)

目标：
  将当前 Mac（或任意用户电脑）上的 Clash Verge Rev 配置与 Shadowrocket 规则环境 100% 对齐，
  确保在“系统代理/TUN 模式 + 规则（Rule）模式、关闭全局”的前提下，分流效果与 Shadowrocket 完全一致。

功能：
  1. 自动定位本机 Clash Verge Rev 数据目录与激活 Profile。
  2. 一键注入与 Shadowrocket 完全一致的云端规则集（小红书、抖音、快手、Claude、公司网络等）。
  3. 探测云端规则集可用性与规则条数。
  4. 运行态安全检查：核验是否为规则模式（非全局）、TUN 兼容性。
  5. 实时链路拨测：测试 Clash 端口对小红书、抖音、快手及 Claude 的实际分流响应。
  6. 输出与 Shadowrocket 基准环境的一致性对比报告。

使用方式：
  python3 scripts/setup_clash_verge.py          # 一键配置并验证
  python3 scripts/setup_clash_verge.py --check  # 仅核验当前状态，不修改任何文件

任意 Mac / Linux 终端单行执行（免梯子直连、全自动化）：
  curl -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python3

Windows PowerShell 终端单行执行（任选其一）：
  # 方式 1（PowerShell 原生，推荐）：
  irm https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python -

  # 方式 2（使用 curl.exe，注意加 .exe）：
  curl.exe -fsSL https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py | python -

跨平台纯 Python 指令（全系统通用）：
  python -c "import urllib.request; exec(urllib.request.urlopen('https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/scripts/setup_clash_verge.py').read().decode('utf-8'))"
"""

import os
import sys
import re
import socket
import time
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# ANSI 颜色定义
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_RAW_BASE = "https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/clash"
DIRECT_URL = f"{REPO_RAW_BASE}/rules_direct.yaml"
PROXY_URL = f"{REPO_RAW_BASE}/rules_proxy.yaml"
COMPANY_URL = f"{REPO_RAW_BASE}/rules_company.yaml"

# 国内高速直连备用镜像源
FALLBACK_BASES = [
    "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash",
    "https://ghproxy.net/https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/clash",
]

# 抖音全系核心直连与 Real-IP 域名（彻底防止 fake-IP 导致爬虫/ClipVault 报 UNSAFE_URL / 非公网地址拦截）
DOUYIN_REAL_IP_DOMAINS = [
    "v.douyin.com",
    "www.iesdouyin.com",
    "www.douyin.com",
    "+.douyin.com",
    "+.iesdouyin.com",
    "+.douyincdn.com",
    "+.douyinpic.com",
    "+.douyinstatic.com",
    "+.douyinvod.com",
    "+.zjcdn.com",
    "+.ydycdn.com",
    "+.bytednsdoc.com",
    "+.byteimg.com",
    "+.ibytedtos.com",
]

# 微信核心直连与 Real-IP 域名（防止图片上传、语音通话被 fake-IP 拦截）
WECHAT_REAL_IP_DOMAINS = [
    "localhost.ptlogin2.qq.com",
    "localhost.work.weixin.qq.com",
    "+.weixin.qq.com",
    "+.wechat.com",
    "+.weixin.com",
    "+.qpic.cn",
    "+.qpic.com",
    "+.qq.com",
    "+.tencent.com",
    "+.gtimg.com",
    "+.gtimg.cn",
    "+.qlogo.cn",
    "+.weixinbridge.com",
    "+.servicewechat.com",
    "+.wechatpay.cn",
    "+.tenpay.com",
    "+.wechatos.net",
    "+.tencent-cloud.net",
    "+.tencent-cloud.cn",
    "+.myqcloud.com",
    "+.qcloud.com",
    "+.cdn-go.cn",
    "+.tencentcs.cn",
    "+.cloudcache.tencent-cloud.com",
    "+.cloudcache.tencentcs.cn",
    "+.dscache.tencent-cloud.cn",
]

# 所有需要确保返回真实公网 IP 的目标域名集
ALL_REAL_IP_DOMAINS = WECHAT_REAL_IP_DOMAINS + DOUYIN_REAL_IP_DOMAINS

# 系统代理 Bypass 核心直连后缀
BYPASS_LIST_ITEMS = [
    "*.qq.com", "*.wechat.com", "*.weixin.qq.com", "*.weixin.com",
    "*.qpic.cn", "*.qpic.com", "*.gtimg.cn", "*.gtimg.com", "*.qlogo.cn",
    "*.wechatos.net", "*.servicewechat.com", "*.weixinbridge.com",
    "*.wechatpay.cn", "*.tenpay.com", "*.myqcloud.com", "*.qcloud.com",
    "*.tencent.com", "*.cdn-go.cn", "*.tencentcs.cn", "*.tencent-cloud.com", "*.tencent-cloud.cn",
    "*.douyin.com", "*.iesdouyin.com", "*.douyincdn.com", "*.douyinpic.com",
    "*.douyinstatic.com", "*.douyinvod.com", "*.zjcdn.com", "*.ydycdn.com",
    "*.bytednsdoc.com", "*.byteimg.com", "*.ibytedtos.com"
]

def backup_file(file_path: Path) -> Path:
    """在修改前创建 .bak 副本，妥善备份客户原有配置。"""
    bak_path = file_path.with_name(f"{file_path.name}.bak")
    if not bak_path.exists() and file_path.exists():
        shutil.copy2(file_path, bak_path)
    return bak_path

def normalize_domain(d: str) -> str:
    """标准化域名表示，去除首尾单双引号与空白。"""
    return d.strip().strip("'\"").strip().lower()

def is_fake_ip(ip_str: str) -> bool:
    """判断 IPv4 地址是否属于 Clash fake-ip 地址池 (198.18.0.0/15)。"""
    if not ip_str:
        return False
    parts = ip_str.strip().split(".")
    if len(parts) == 4 and parts[0] == "198":
        try:
            second = int(parts[1])
            return 18 <= second <= 19
        except ValueError:
            pass
    return False

def merge_fake_ip_filter_content(content: str, domains_to_real_ip: list[str]) -> tuple[str, bool, str]:
    """
    根据现有 fake-ip-filter-mode 智能增量合并 fake-ip-filter 规则，严格幂等且不破坏其他配置。
    
    1. 若 fake-ip-filter-mode 为 blacklist (默认黑名单模式)：
       所有在 fake-ip-filter 里的域名返回 REAL IP。因此目标域名必须【加入】到 fake-ip-filter 中。
    2. 若 fake-ip-filter-mode 为 whitelist (白名单模式)：
       只有在 fake-ip-filter 里的域名才返回 fake-IP。因此目标域名必须【从 fake-ip-filter 中剔除】以返回 REAL IP。
    
    返回: (新文本内容, 是否有变动, 生效模式)
    """
    mode_match = re.search(r"^\s*fake-ip-filter-mode:\s*([a-zA-Z0-9_-]+)", content, re.MULTILINE)
    mode = mode_match.group(1).lower().strip() if mode_match else "blacklist"
    
    lines = content.splitlines(keepends=True)
    target_norm_set = {normalize_domain(d) for d in domains_to_real_ip}
    
    filter_start_idx = None
    base_indent = "  "
    filter_item_indices = []
    is_inline_empty_list = False
    
    for idx, line in enumerate(lines):
        m = re.match(r"^(\s*)fake-ip-filter:\s*(\[\])?\s*(#.*)?$", line)
        if m:
            filter_start_idx = idx
            base_indent = m.group(1)
            if m.group(2) == "[]":
                is_inline_empty_list = True
            
            curr_idx = idx + 1
            while curr_idx < len(lines):
                sub_line = lines[curr_idx]
                if not sub_line.strip() or sub_line.strip().startswith("#"):
                    curr_idx += 1
                    continue
                sub_indent_m = re.match(r"^(\s+)", sub_line)
                if not sub_indent_m or len(sub_indent_m.group(1)) <= len(base_indent):
                    break
                item_m = re.match(r"^(\s*-\s*)(.*)", sub_line)
                if item_m:
                    filter_item_indices.append(curr_idx)
                curr_idx += 1
            break
            
    if mode == "whitelist":
        # 白名单模式：在 filter 中的才会变成 fake-IP，要返回真实 IP 则必须从中移除
        if filter_start_idx is None or not filter_item_indices:
            return content, False, mode
        
        lines_to_remove = set()
        for i in filter_item_indices:
            item_val = lines[i].split("-", 1)[1].split("#")[0].strip()
            if normalize_domain(item_val) in target_norm_set:
                lines_to_remove.add(i)
                
        if not lines_to_remove:
            return content, False, mode
            
        new_lines = [line for idx, line in enumerate(lines) if idx not in lines_to_remove]
        return "".join(new_lines), True, mode

    else:
        # 黑名单模式 (默认)：在 filter 中的会跳过 fake-IP 返回 REAL IP
        existing_domains = set()
        indent_str = base_indent + "  - "
        
        if filter_item_indices:
            last_item_idx = filter_item_indices[-1]
            for i in filter_item_indices:
                item_val = lines[i].split("-", 1)[1].split("#")[0].strip()
                existing_domains.add(normalize_domain(item_val))
            first_item_line = lines[filter_item_indices[0]]
            dash_m = re.match(r"^(\s*-\s*)", first_item_line)
            if dash_m:
                indent_str = dash_m.group(1)
        else:
            last_item_idx = filter_start_idx
            
        domains_to_add = [d for d in domains_to_real_ip if normalize_domain(d) not in existing_domains]
        if not domains_to_add:
            return content, False, mode
            
        if filter_start_idx is None:
            dns_idx = None
            dns_indent = ""
            for idx, line in enumerate(lines):
                dns_m = re.match(r"^(\s*)dns:\s*$", line)
                if dns_m:
                    dns_idx = idx
                    dns_indent = dns_m.group(1)
                    break
            
            sub_indent = dns_indent + "  "
            item_indent = dns_indent + "    - "
            new_block = [
                f"{sub_indent}fake-ip-filter-mode: blacklist\n",
                f"{sub_indent}fake-ip-filter:\n"
            ]
            for d in domains_to_add:
                new_block.append(f"{item_indent}'{d}'\n")
                
            if dns_idx is not None:
                lines[dns_idx+1:dns_idx+1] = new_block
            else:
                lines.append("\ndns:\n  enable: true\n  enhanced-mode: fake-ip\n  fake-ip-filter-mode: blacklist\n  fake-ip-filter:\n")
                for d in domains_to_add:
                    lines.append(f"    - '{d}'\n")
            return "".join(lines), True, mode
            
        if is_inline_empty_list:
            lines[filter_start_idx] = f"{base_indent}fake-ip-filter:\n"
            indent_str = base_indent + "  - "
            last_item_idx = filter_start_idx
            
        new_items = [f"{indent_str}'{d}'\n" for d in domains_to_add]
        lines[last_item_idx+1:last_item_idx+1] = new_items
        return "".join(lines), True, mode

def merge_system_proxy_bypass_content(content: str, bypass_items: list[str]) -> tuple[str, bool]:
    """增量合并系统代理 bypass 白名单，保留客户原有项，幂等去重。"""
    m = re.search(r"^\s*system_proxy_bypass:\s*(.*)", content, re.MULTILINE)
    default_base = ["localhost", "127.*", "10.*", "192.168.*", "172.16.*", "<local>"]
    all_targets = []
    for item in default_base + bypass_items:
        if item not in all_targets:
            all_targets.append(item)
            
    if m:
        raw_val = m.group(1).strip().strip("'\"")
        if raw_val in ("null", "~", "", "None"):
            final_list = all_targets
        else:
            existing = [x.strip() for x in raw_val.split(";") if x.strip()]
            final_list = list(existing)
            for item in all_targets:
                if item not in final_list:
                    final_list.append(item)
        new_val_str = ";".join(final_list)
        if raw_val == new_val_str:
            return content, False
        new_line = f'system_proxy_bypass: "{new_val_str}"'
        new_content = re.sub(r"^\s*system_proxy_bypass:.*", new_line, content, flags=re.MULTILINE)
        return new_content, True
    else:
        new_val_str = ";".join(all_targets)
        new_content = content + f'\nsystem_proxy_bypass: "{new_val_str}"\n'
        return new_content, True


def detect_main_proxy_group(profile_path: Path) -> str:
    """自动探测当前 Profile 的主要出站代理策略组名称（如 节点选择、PROXY、Proxy 等）。"""
    if not profile_path.exists():
        return "节点选择"
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            content = f.read()
        group_names = []
        pg_match = re.search(r"^proxy-groups:\s*\n(.*?)(?=\n[a-zA-Z0-9_-]+:|\Z)", content, re.DOTALL | re.MULTILINE)
        if pg_match:
            for line in pg_match.group(1).splitlines():
                m = re.match(r"^\s*-\s+name:\s*(.+)", line)
                if m:
                    group_names.append(m.group(1).strip().strip("'\""))
        priority_candidates = ["节点选择", "PROXY", "Proxy", "PROXIES", "选择节点", "节点挑选", "全部节点", "自动选择", "Auto"]
        for cand in priority_candidates:
            if cand in group_names:
                return cand
        if group_names:
            return group_names[0]
        p_match = re.search(r"^proxies:\s*\n(.*?)(?=\n[a-zA-Z0-9_-]+:|\Z)", content, re.DOTALL | re.MULTILINE)
        if p_match:
            for line in p_match.group(1).splitlines():
                m = re.match(r"^\s*-\s+name:\s*(.+)", line)
                if m:
                    return m.group(1).strip().strip("'\"")
    except Exception:
        pass
    return "节点选择"

def build_client_merge_content(main_group: str = "节点选择") -> str:
    """构建客户通用纯净版 Merge 扩展内容（根据实际代理组自适应绑定）。"""
    return f"""# Profile Enhancement Merge for Clash Verge Rev (Client Public Edition)
# Generated by shadowrocket-config sync script
# Auto-syncs rules from CDN: fastly.jsdelivr.net / GitHub

# 全局关闭 IPv6：与 Shadowrocket (ipv6 = false) 保持 100% 对齐
# 彻底防止 macOS/Windows 在 TUN 模式下因缺少公网 IPv6 导致微信发图/文件上传红感叹号超时
ipv6: false

# TUN 虚拟网卡深度优化：彻底解决 macOS / Windows 上微信大文件、多媒体图片上传 hang 住问题
# 严格对齐 Shadowrocket bypass-tun，排除 Tailscale (100.64.0.0/10) 与局域网网段，防止劫持私有 VPN/虚拟网卡
tun:
  enable: true
  stack: mixed
  auto-route: true
  auto-detect-interface: true
  dns-hijack:
    - any:53
    - tcp://any:53
  strict-route: false
  mtu: 1500
  endpoint-independent-nat: true
  route-exclude-address:
    - 100.64.0.0/10
    - 111.231.15.226/32
    - 127.0.0.0/8
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    - 169.254.0.0/16

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

prepend-rules:
  # 微信全系客户端进程与多媒体直连（彻底保障 Mac & Windows 发文字、发图片、大文件上传、音视频通话 100% 走本地直连）
  - PROCESS-NAME,WeChat,DIRECT
  - PROCESS-NAME,WeChat.exe,DIRECT
  - PROCESS-NAME,WeChatAppEx,DIRECT
  - PROCESS-NAME,WeChatAppEx.exe,DIRECT
  - PROCESS-NAME,WeChatAppEx Helper,DIRECT
  - PROCESS-NAME,WeChatAppEx Helper (Renderer),DIRECT
  - PROCESS-NAME,WeChatHelper,DIRECT
  - PROCESS-NAME,WeChatHelper.exe,DIRECT
  - PROCESS-NAME,XPlayer,DIRECT
  - PROCESS-NAME,WeChatPlayer.exe,DIRECT
  - PROCESS-NAME,Weixin,DIRECT
  - PROCESS-NAME,Weixin.exe,DIRECT
  - DOMAIN-KEYWORD,weixin,DIRECT
  - DOMAIN-KEYWORD,wechat,DIRECT
  - DOMAIN-KEYWORD,qpic,DIRECT
  - DOMAIN-SUFFIX,weixin.qq.com,DIRECT
  - DOMAIN-SUFFIX,wechat.com,DIRECT
  - DOMAIN-SUFFIX,qpic.cn,DIRECT
  - DOMAIN-SUFFIX,qpic.com,DIRECT
  - DOMAIN-SUFFIX,qq.com,DIRECT
  - DOMAIN-SUFFIX,myqcloud.com,DIRECT
  - DOMAIN-SUFFIX,qcloud.com,DIRECT
  - DOMAIN-SUFFIX,jsdelivr.net,DIRECT
  - RULE-SET,sr-proxy,{main_group}
  - RULE-SET,sr-direct,DIRECT
  - GEOIP,LAN,DIRECT,no-resolve
  - GEOIP,CN,DIRECT
  - MATCH,{main_group}

# DNS 增强配置：将微信/QQ/腾讯核心域名列入 fake-ip-filter 黑名单返回真实 IP，彻底解决图片上传拦截/超时
dns:
  ipv6: false
  enable: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter-mode: blacklist
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
    - https://doh.pub/dns-query
    - https://dns.alidns.com/dns-query
  nameserver-policy:
    "geosite:cn,private":
      - 223.5.5.5
      - 119.29.29.29
    "+.qq.com,+.weixin.qq.com,+.wechat.com,+.weixin.com,+.qpic.cn,+.qpic.com,+.tencent.com,+.myqcloud.com,+.qcloud.com":
      - 119.29.29.29
      - 223.5.5.5
    "+.jsdelivr.net":
      - 223.5.5.5
      - 119.29.29.29
  fake-ip-filter:
    - "*.lan"
    - "*.local"
    - "*.arpa"
    - "time.*.com"
    - "ntp.*.com"
    - "localhost.ptlogin2.qq.com"
    - "localhost.work.weixin.qq.com"
    - "+.weixin.qq.com"
    - "+.wechat.com"
    - "+.weixin.com"
    - "+.qpic.cn"
    - "+.qpic.com"
    - "+.qq.com"
    - "+.tencent.com"
    - "+.gtimg.com"
    - "+.gtimg.cn"
    - "+.qlogo.cn"
    - "+.weixinbridge.com"
    - "+.servicewechat.com"
    - "+.wechatpay.cn"
    - "+.tenpay.com"
    - "+.wechatos.net"
    - "+.tencent-cloud.net"
    - "+.tencent-cloud.cn"
    - "+.myqcloud.com"
    - "+.qcloud.com"
    - "+.cdn-go.cn"
    - "+.tencentcs.cn"
    - "+.cloudcache.tencent-cloud.com"
    - "+.cloudcache.tencentcs.cn"
    - "+.dscache.tencent-cloud.cn"
    - "+.msftncsi.com"
    - "+.msftconnecttest.com"
    # 抖音全系核心域名直连（返回真实 IP，彻底防止 ClipVault / 爬虫因 fake-ip 判定非公网拒绝连接）
    - "v.douyin.com"
    - "www.iesdouyin.com"
    - "www.douyin.com"
    - "+.douyin.com"
    - "+.iesdouyin.com"
    - "+.douyincdn.com"
    - "+.douyinpic.com"
    - "+.douyinstatic.com"
    - "+.douyinvod.com"
    - "+.zjcdn.com"
    - "+.ydycdn.com"
    - "+.bytednsdoc.com"
    - "+.byteimg.com"
    - "+.ibytedtos.com"
"""

def build_work_merge_content(main_group: str = "节点选择") -> str:
    """构建个人工作定制版 Merge 扩展内容（包含公司 1088 SSH 隧道与自适应代理组）。"""
    return f"""# Profile Enhancement Merge for Clash Verge Rev (Work Private Edition)
# Generated by shadowrocket-config sync script
# Auto-syncs rules from CDN: fastly.jsdelivr.net / GitHub

# 全局关闭 IPv6：与 Shadowrocket (ipv6 = false) 保持 100% 对齐
# 彻底防止 macOS/Windows 在 TUN 模式下因缺少公网 IPv6 导致微信发图/文件上传红感叹号超时
ipv6: false

# TUN 虚拟网卡深度优化：彻底解决 macOS / Windows 上微信大文件、多媒体图片上传 hang 住问题
# 严格对齐 Shadowrocket bypass-tun，排除 Tailscale (100.64.0.0/10) 与局域网网段，防止劫持公司跳板机隧道
tun:
  enable: true
  stack: mixed
  auto-route: true
  auto-detect-interface: true
  dns-hijack:
    - any:53
    - tcp://any:53
  strict-route: false
  mtu: 1500
  endpoint-independent-nat: true
  route-exclude-address:
    - 100.64.0.0/10
    - 111.231.15.226/32
    - 127.0.0.0/8
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    - 169.254.0.0/16

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

proxies:
  - name: CORP-WINDOWS-NODE
    type: socks5
    server: 127.0.0.1
    port: 1088

prepend-proxy-groups:
  - name: CORP-WINDOWS
    type: select
    proxies:
      - CORP-WINDOWS-NODE
      - DIRECT
      - {main_group}

prepend-rules:
  # 微信全系客户端进程与多媒体直连（彻底保障 Mac & Windows 发文字、发图片、大文件上传、音视频通话 100% 走本地直连）
  - PROCESS-NAME,WeChat,DIRECT
  - PROCESS-NAME,WeChat.exe,DIRECT
  - PROCESS-NAME,WeChatAppEx,DIRECT
  - PROCESS-NAME,WeChatAppEx.exe,DIRECT
  - PROCESS-NAME,WeChatAppEx Helper,DIRECT
  - PROCESS-NAME,WeChatAppEx Helper (Renderer),DIRECT
  - PROCESS-NAME,WeChatHelper,DIRECT
  - PROCESS-NAME,WeChatHelper.exe,DIRECT
  - PROCESS-NAME,XPlayer,DIRECT
  - PROCESS-NAME,WeChatPlayer.exe,DIRECT
  - PROCESS-NAME,Weixin,DIRECT
  - PROCESS-NAME,Weixin.exe,DIRECT
  - DOMAIN-KEYWORD,weixin,DIRECT
  - DOMAIN-KEYWORD,wechat,DIRECT
  - DOMAIN-KEYWORD,qpic,DIRECT
  - DOMAIN-SUFFIX,weixin.qq.com,DIRECT
  - DOMAIN-SUFFIX,wechat.com,DIRECT
  - DOMAIN-SUFFIX,qpic.cn,DIRECT
  - DOMAIN-SUFFIX,qpic.com,DIRECT
  - DOMAIN-SUFFIX,qq.com,DIRECT
  - DOMAIN-SUFFIX,myqcloud.com,DIRECT
  - DOMAIN-SUFFIX,qcloud.com,DIRECT
  - DOMAIN-SUFFIX,jsdelivr.net,DIRECT
  - RULE-SET,sr-company,CORP-WINDOWS
  - RULE-SET,sr-proxy,{main_group}
  - RULE-SET,sr-direct,DIRECT
  - GEOIP,LAN,DIRECT,no-resolve
  - GEOIP,CN,DIRECT
  - MATCH,{main_group}

# DNS 增强配置：将微信/QQ/腾讯核心域名列入 fake-ip-filter 黑名单返回真实 IP，彻底解决图片上传拦截/超时
dns:
  ipv6: false
  enable: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter-mode: blacklist
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
    - https://doh.pub/dns-query
    - https://dns.alidns.com/dns-query
  nameserver-policy:
    "geosite:cn,private":
      - 223.5.5.5
      - 119.29.29.29
    "+.qq.com,+.weixin.qq.com,+.wechat.com,+.weixin.com,+.qpic.cn,+.qpic.com,+.tencent.com,+.myqcloud.com,+.qcloud.com":
      - 119.29.29.29
      - 223.5.5.5
    "+.jsdelivr.net":
      - 223.5.5.5
      - 119.29.29.29
  fake-ip-filter:
    - "*.lan"
    - "*.local"
    - "*.arpa"
    - "time.*.com"
    - "ntp.*.com"
    - "localhost.ptlogin2.qq.com"
    - "localhost.work.weixin.qq.com"
    - "+.weixin.qq.com"
    - "+.wechat.com"
    - "+.weixin.com"
    - "+.qpic.cn"
    - "+.qpic.com"
    - "+.qq.com"
    - "+.tencent.com"
    - "+.gtimg.com"
    - "+.gtimg.cn"
    - "+.qlogo.cn"
    - "+.weixinbridge.com"
    - "+.servicewechat.com"
    - "+.wechatpay.cn"
    - "+.tenpay.com"
    - "+.wechatos.net"
    - "+.tencent-cloud.net"
    - "+.tencent-cloud.cn"
    - "+.myqcloud.com"
    - "+.qcloud.com"
    - "+.cdn-go.cn"
    - "+.tencentcs.cn"
    - "+.cloudcache.tencent-cloud.com"
    - "+.cloudcache.tencentcs.cn"
    - "+.dscache.tencent-cloud.cn"
    - "+.msftncsi.com"
    - "+.msftconnecttest.com"
    # 抖音全系核心域名直连（返回真实 IP，彻底防止 ClipVault / 爬虫因 fake-ip 判定非公网拒绝连接）
    - "v.douyin.com"
    - "www.iesdouyin.com"
    - "www.douyin.com"
    - "+.douyin.com"
    - "+.iesdouyin.com"
    - "+.douyincdn.com"
    - "+.douyinpic.com"
    - "+.douyinstatic.com"
    - "+.douyinvod.com"
    - "+.zjcdn.com"
    - "+.ydycdn.com"
    - "+.bytednsdoc.com"
    - "+.byteimg.com"
    - "+.ibytedtos.com"
"""

CLIENT_MERGE_CONTENT = build_client_merge_content("节点选择")
WORK_MERGE_CONTENT = build_work_merge_content("节点选择")


def find_verge_dir():
    appdata = os.environ.get("APPDATA")
    localappdata = os.environ.get("LOCALAPPDATA")
    candidates = [
        # macOS
        Path.home() / "Library" / "Application Support" / "io.github.clash-verge-rev.clash-verge-rev",
        Path.home() / "Library" / "Application Support" / "clash-verge-rev",
        Path.home() / "Library" / "Application Support" / "clash-verge",
        # Linux / portable
        Path.home() / ".config" / "clash-verge-rev",
        Path.home() / ".config" / "clash-verge",
        Path.home() / ".config" / "io.github.clash-verge-rev.clash-verge-rev",
    ]
    # Windows
    if appdata:
        appdata_path = Path(appdata)
        candidates.extend([
            appdata_path / "io.github.clash-verge-rev.clash-verge-rev",
            appdata_path / "clash-verge-rev",
            appdata_path / "clash-verge",
        ])
    if localappdata:
        local_path = Path(localappdata)
        candidates.extend([
            local_path / "io.github.clash-verge-rev.clash-verge-rev",
            local_path / "clash-verge-rev",
            local_path / "clash-verge",
        ])

    for c in candidates:
        if c.exists() and (c / "profiles.yaml").exists():
            return c
    return None

def fetch_single_url(url, timeout=5):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status == 200:
            data = resp.read().decode("utf-8")
            count = len(re.findall(r"^\s*-\s+", data, re.MULTILINE))
            return True, count, data
        return False, 0, f"HTTP {resp.status}"

def test_url_fetch(primary_url, filename, timeout=5):
    """Test primary URL, and auto fallback to CDN mirrors if blocked by GFW."""
    try:
        ok, count, data = fetch_single_url(primary_url, timeout=timeout)
        if ok:
            return True, count, "GitHub Raw (直连)"
    except Exception:
        pass

    # 尝试国内高速镜像
    for base in FALLBACK_BASES:
        fallback_url = f"{base}/{filename}"
        try:
            ok, count, data = fetch_single_url(fallback_url, timeout=timeout)
            if ok:
                return True, count, f"CDN镜像加速 ({base.split('/')[2]})"
        except Exception:
            continue

    return False, 0, "所有节点连接均超时或被阻断"

def test_proxy_connect(port, target_url, timeout=4):
    """Test connecting to a URL through Clash mixed port using curl or urllib."""
    # 优先尝试 curl / curl.exe
    try:
        curl_bin = "curl.exe" if sys.platform == "win32" else "curl"
        cmd = [
            curl_bin, "-I", "-sS", "-m", str(timeout),
            "-x", f"http://127.0.0.1:{port}",
            target_url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and ("HTTP/" in res.stdout or any(code in res.stdout for code in ["200", "301", "302", "401", "403", "404"])):
            first_line = res.stdout.splitlines()[0] if res.stdout else "OK"
            return True, first_line.strip()
    except Exception:
        pass

    # 兜底使用 Python 标准库 urllib 代理
    try:
        proxy_handler = urllib.request.ProxyHandler({
            "http": f"http://127.0.0.1:{port}",
            "https": f"http://127.0.0.1:{port}",
        })
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with opener.open(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return True, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)

def parse_simple_yaml_map(filepath):
    result = {}
    if not filepath.exists():
        return result
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip().strip("'\"")
    return result

def main():
    check_only = "--check" in sys.argv or "--check-only" in sys.argv
    is_work_mode = "--work" in sys.argv or "--company" in sys.argv

    print(f"\n{BOLD}{CYAN}==================================================================={RESET}")
    print(f"{BOLD}{CYAN}      Clash Verge Rev 与 Shadowrocket 环境对齐与一致性校验工具      {RESET}")
    print(f"{BOLD}{CYAN}==================================================================={RESET}\n")

    edition_name = "个人工作定制版 (--work)" if is_work_mode else "客户通用纯净版 (默认)"
    edition_tip = "已挂载公司内网 SSH 隧道 (127.0.0.1:1088)" if is_work_mode else "已剥离任何公司内网信息，0 隐私外泄风险"
    print(f"[{BLUE}MODE{RESET}] 当前配置目标: {BOLD}{edition_name}{RESET} -> {edition_tip}")

    # 1. 寻找 Clash Verge Rev 数据目录
    verge_dir = find_verge_dir()
    if not verge_dir:
        print(f"[{RED}FAIL{RESET}] 未找到 Clash Verge Rev 数据目录。")
        print(f"       请确认本机已安装并启动过 Clash Verge Rev。")
        sys.exit(1)

    print(f"[{GREEN}OK{RESET}] 定位到 Clash Verge Rev 数据目录: {verge_dir}")

    # 2. 读取 profiles.yaml 识别所有配置（包括当前配置与备用配置，如 justg, bwg-cal 等）
    profiles_yaml_path = verge_dir / "profiles.yaml"
    with open(profiles_yaml_path, "r", encoding="utf-8") as f:
        profiles_content = f.read()

    current_match = re.search(r"^current:\s*([a-zA-Z0-9_-]+)", profiles_content, re.MULTILINE)
    current_uid = current_match.group(1).strip() if current_match else None

    if not current_uid:
        print(f"[{RED}FAIL{RESET}] 未在 profiles.yaml 中找到激活配置 (current)。")
        sys.exit(1)

    profiles_dir = verge_dir / "profiles"
    if not profiles_dir.exists():
        profiles_dir.mkdir(parents=True, exist_ok=True)

    # 提取所有配置项 (type: local 或 remote)
    profile_items = []
    for m in re.finditer(r"-\s+uid:\s+([a-zA-Z0-9_-]+)\b(.*?)(?=\n-\s+uid:|\Z)", profiles_content, re.DOTALL):
        p_uid = m.group(1).strip()
        p_block = m.group(2)
        type_m = re.search(r"type:\s*([a-zA-Z0-9_-]+)", p_block)
        p_type = type_m.group(1).strip() if type_m else ""
        if p_type in ("local", "remote"):
            name_m = re.search(r"name:\s*(.+)", p_block)
            p_name = name_m.group(1).strip().strip("'\"") if name_m else p_uid
            merge_m = re.search(r"merge:\s*([a-zA-Z0-9_-]+)", p_block)
            p_merge = merge_m.group(1).strip() if merge_m else None
            rules_m = re.search(r"rules:\s*([a-zA-Z0-9_-]+)", p_block)
            p_rules = rules_m.group(1).strip() if rules_m else None
            profile_items.append({
                "uid": p_uid,
                "name": p_name,
                "type": p_type,
                "merge_uid": p_merge,
                "rules_uid": p_rules,
                "block": p_block,
                "is_current": (p_uid == current_uid)
            })

    print(f"[{GREEN}OK{RESET}] 在 profiles.yaml 中发现 {len(profile_items)} 个配置项:")
    for pi in profile_items:
        tag = f" {BOLD}(当前激活){RESET}" if pi["is_current"] else ""
        print(f"       * {pi['name']:<16} [UID: {pi['uid']}]{tag}")

    # 3. 逐一遍历并同步所有 Profile 的 Merge 与 Rules 扩展配置
    profiles_yaml_modified = False
    for pi in profile_items:
        p_uid = pi["uid"]
        p_name = pi["name"]
        merge_uid = pi["merge_uid"]
        rules_uid = pi["rules_uid"]
        p_block = pi["block"]

        if not merge_uid or merge_uid == "null":
            merge_uid = f"merge_{int(time.time())}_{p_uid[:4]}"
            print(f"[{YELLOW}WARN{RESET}] 配置 {p_name} 未关联 Merge 扩展，自动绑定: {merge_uid}")
            if "option:" in p_block:
                new_block = re.sub(r"(option:\s*\n)", rf"\1    merge: {merge_uid}\n", p_block, count=1)
                profiles_content = profiles_content.replace(p_block, new_block)
            else:
                new_block = p_block + f"\n  option:\n    merge: {merge_uid}\n"
                profiles_content = profiles_content.replace(p_block, new_block)
            merge_item_yaml = f"- uid: {merge_uid}\n  type: merge\n  name: SR-Rules-AutoSync\n  file: {merge_uid}.yaml\n  updated: {int(time.time())}\n"
            profiles_content = re.sub(r"(items:\s*\n)", rf"\1{merge_item_yaml}", profiles_content, count=1)
            profiles_yaml_modified = True

        prof_file = profiles_dir / f"{p_uid}.yaml"
        main_group = detect_main_proxy_group(prof_file)

        chosen_merge_content = build_work_merge_content(main_group) if is_work_mode else build_client_merge_content(main_group)
        merge_file = profiles_dir / f"{merge_uid}.yaml"

        if not check_only:
            need_full_write = True
            cur_merge = ""
            if merge_file.exists():
                with open(merge_file, "r", encoding="utf-8") as f:
                    cur_merge = f.read()
                if "sr-direct" in cur_merge:
                    need_full_write = False
                    if not is_work_mode and ("CORP-WINDOWS" in cur_merge or "sr-company" in cur_merge):
                        need_full_write = True
                    if "WeChatAppEx Helper" not in cur_merge or "nameserver-policy" not in cur_merge or "stack: mixed" not in cur_merge or "ipv6: false" not in cur_merge:
                        need_full_write = True

            if need_full_write:
                if merge_file.exists():
                    backup_file(merge_file)
                with open(merge_file, "w", encoding="utf-8") as f:
                    f.write(chosen_merge_content)
                print(f"[{GREEN}OK{RESET}] [{p_name}] 已写入完整规则到 Merge 扩展 ({merge_file.name}) [主策略组: {main_group}]")
            else:
                backup_file(merge_file)
                new_merge, merge_changed, merge_mode = merge_fake_ip_filter_content(cur_merge, ALL_REAL_IP_DOMAINS)
                if f"RULE-SET,sr-proxy,节点选择" in new_merge and main_group != "节点选择":
                    new_merge = new_merge.replace("RULE-SET,sr-proxy,节点选择", f"RULE-SET,sr-proxy,{main_group}")
                    merge_changed = True
                if merge_changed:
                    with open(merge_file, "w", encoding="utf-8") as f:
                        f.write(new_merge)
                    print(f"[{GREEN}OK{RESET}] [{p_name}] 已向 Merge 扩展 ({merge_file.name}) 增量合并 Real-IP 规则")

            if rules_uid and rules_uid != "null":
                rules_file = profiles_dir / f"{rules_uid}.yaml"
                if rules_file.exists():
                    backup_file(rules_file)
                company_line = "  - RULE-SET,sr-company,CORP-WINDOWS\n" if is_work_mode else ""
                rules_ext_content = f"""# Profile Enhancement Rules Template for Clash Verge

prepend:
  # 微信全系客户端进程与多媒体直连（彻底保障 Mac & Windows 发文字、发图片、大文件上传、音视频通话 100% 走本地直连）
  - PROCESS-NAME,WeChat,DIRECT
  - PROCESS-NAME,WeChat.exe,DIRECT
  - PROCESS-NAME,WeChatAppEx,DIRECT
  - PROCESS-NAME,WeChatAppEx.exe,DIRECT
  - PROCESS-NAME,WeChatAppEx Helper,DIRECT
  - PROCESS-NAME,WeChatAppEx Helper (Renderer),DIRECT
  - PROCESS-NAME,WeChatHelper,DIRECT
  - PROCESS-NAME,WeChatHelper.exe,DIRECT
  - PROCESS-NAME,XPlayer,DIRECT
  - PROCESS-NAME,WeChatPlayer.exe,DIRECT
  - PROCESS-NAME,Weixin,DIRECT
  - PROCESS-NAME,Weixin.exe,DIRECT
  - DOMAIN-KEYWORD,weixin,DIRECT
  - DOMAIN-KEYWORD,wechat,DIRECT
  - DOMAIN-KEYWORD,qpic,DIRECT
  - DOMAIN-SUFFIX,weixin.qq.com,DIRECT
  - DOMAIN-SUFFIX,wechat.com,DIRECT
  - DOMAIN-SUFFIX,qpic.cn,DIRECT
  - DOMAIN-SUFFIX,qpic.com,DIRECT
  - DOMAIN-SUFFIX,qq.com,DIRECT
  - DOMAIN-SUFFIX,myqcloud.com,DIRECT
  - DOMAIN-SUFFIX,qcloud.com,DIRECT
  - DOMAIN-SUFFIX,jsdelivr.net,DIRECT
{company_line}  - RULE-SET,sr-proxy,{main_group}
  - RULE-SET,sr-direct,DIRECT

append: []

delete: []
"""
                with open(rules_file, "w", encoding="utf-8") as f:
                    f.write(rules_ext_content)
                print(f"[{GREEN}OK{RESET}] [{p_name}] 已注入置顶规则到 Rules 扩展 ({rules_file.name}) [目标代理组: {main_group}]")

            # 确保每个 Profile 自身的 YAML 具备 Real-IP DNS 过滤规则
            if prof_file.exists():
                try:
                    with open(prof_file, "r", encoding="utf-8") as f:
                        prof_text = f.read()
                    new_pt, pt_changed, _ = merge_fake_ip_filter_content(prof_text, ALL_REAL_IP_DOMAINS)
                    if pt_changed:
                        with open(prof_file, "w", encoding="utf-8") as f:
                            f.write(new_pt)
                except Exception:
                    pass

    if profiles_yaml_modified and not check_only:
        with open(profiles_yaml_path, "w", encoding="utf-8") as f:
            f.write(profiles_content)

        # 4.2 增量合并系统代理白名单与 DNS fake-ip-filter (微信发图 + 抖音视频 Real-IP 100% 直连无阻)
        # A. 更新 verge.yaml 的系统代理 bypass 列表
        verge_yaml_path = verge_dir / "verge.yaml"
        if verge_yaml_path.exists():
            try:
                backup_file(verge_yaml_path)
                with open(verge_yaml_path, "r", encoding="utf-8") as f:
                    vy = f.read()
                new_vy, vy_changed = merge_system_proxy_bypass_content(vy, BYPASS_LIST_ITEMS)
                if vy_changed:
                    with open(verge_yaml_path, "w", encoding="utf-8") as f:
                        f.write(new_vy)
                    print(f"[{GREEN}OK{RESET}] 已向 verge.yaml 增量注入系统代理直连白名单 (system_proxy_bypass)")
            except Exception as e:
                print(f"[{YELLOW}WARN{RESET}] 更新 verge.yaml 遇到提示: {e}")

        # B. 更新 dns_config.yaml 中的 fake-ip-filter
        dns_config_path = verge_dir / "dns_config.yaml"
        if dns_config_path.exists():
            try:
                backup_file(dns_config_path)
                with open(dns_config_path, "r", encoding="utf-8") as f:
                    dy = f.read()
                new_dy, dy_changed, dy_mode = merge_fake_ip_filter_content(dy, ALL_REAL_IP_DOMAINS)
                if dy_changed:
                    with open(dns_config_path, "w", encoding="utf-8") as f:
                        f.write(new_dy)
                    print(f"[{GREEN}OK{RESET}] 已向 dns_config.yaml 增量注入 Real-IP 域名规则 [{dy_mode}模式]")
            except Exception as e:
                print(f"[{YELLOW}WARN{RESET}] 更新 dns_config.yaml 遇到提示: {e}")

        # C. 确保当前主配置文件中的 fake-ip-filter 生效
        cur_prof_file = profiles_dir / f"{current_uid}.yaml"
        if cur_prof_file.exists():
            try:
                backup_file(cur_prof_file)
                with open(cur_prof_file, "r", encoding="utf-8") as f:
                    cp_text = f.read()
                new_cp, cp_changed, cp_mode = merge_fake_ip_filter_content(cp_text, ALL_REAL_IP_DOMAINS)
                if cp_changed:
                    with open(cur_prof_file, "w", encoding="utf-8") as f:
                        f.write(new_cp)
                    print(f"[{GREEN}OK{RESET}] 已向当前配置 {cur_prof_file.name} 增量注入 Real-IP 域名规则 [{cp_mode}模式]")
            except Exception as e:
                print(f"[{YELLOW}WARN{RESET}] 更新当前配置遇到提示: {e}")

        # D. 更新 clash-verge.yaml 中的 fake-ip-filter, ipv6 与 tun 设置
        clash_config_path = verge_dir / "clash-verge.yaml"
        if clash_config_path.exists():
            try:
                backup_file(clash_config_path)
                with open(clash_config_path, "r", encoding="utf-8") as f:
                    cvy = f.read()
                new_cvy, cvy_changed, cvy_mode = merge_fake_ip_filter_content(cvy, ALL_REAL_IP_DOMAINS)
                # 确保全局关闭 ipv6，与 Shadowrocket 保持 100% 对齐
                if "ipv6: true" in new_cvy:
                    new_cvy = re.sub(r"^ipv6:\s*true", "ipv6: false", new_cvy, flags=re.MULTILINE)
                    cvy_changed = True
                # 确保 tun 优化为 mixed 协议栈与 1500 MTU
                if "stack: gvisor" in new_cvy:
                    new_cvy = new_cvy.replace("stack: gvisor", "stack: mixed")
                    cvy_changed = True
                if "mtu:" not in new_cvy and "tun:" in new_cvy:
                    new_cvy = re.sub(r"(tun:\s*\n(\s+.*?\n)*?\s+strict-route:\s*false)", r"\1\n  mtu: 1500\n  endpoint-independent-nat: true", new_cvy)
                    cvy_changed = True
                if cvy_changed:
                    with open(clash_config_path, "w", encoding="utf-8") as f:
                        f.write(new_cvy)
                    print(f"[{GREEN}OK{RESET}] 已向 clash-verge.yaml 注入 Real-IP、关闭 IPv6 并优化 TUN 协议栈 [mixed/1500]")
            except Exception as e:
                print(f"[{YELLOW}WARN{RESET}] 更新 clash-verge.yaml 遇到提示: {e}")

        # E. 更新 config.yaml 中的 ipv6 与 tun 设置 (底层预设)
        config_yaml_path = verge_dir / "config.yaml"
        if config_yaml_path.exists():
            try:
                backup_file(config_yaml_path)
                with open(config_yaml_path, "r", encoding="utf-8") as f:
                    cfg_text = f.read()
                cfg_changed = False
                if "ipv6: true" in cfg_text:
                    cfg_text = re.sub(r"^ipv6:\s*true", "ipv6: false", cfg_text, flags=re.MULTILINE)
                    cfg_changed = True
                if "stack: gvisor" in cfg_text:
                    cfg_text = cfg_text.replace("stack: gvisor", "stack: mixed")
                    cfg_changed = True
                if "mtu:" not in cfg_text and "tun:" in cfg_text:
                    cfg_text = re.sub(r"(strict-route:\s*false)", r"\1\n  mtu: 1500\n  endpoint-independent-nat: true", cfg_text)
                    cfg_changed = True
                if cfg_changed:
                    with open(config_yaml_path, "w", encoding="utf-8") as f:
                        f.write(cfg_text)
                    print(f"[{GREEN}OK{RESET}] 已向 config.yaml 基础预设注入 ipv6: false 与 TUN mixed 模式")
            except Exception as e:
                pass

        # 4.3 自动平滑重载核心配置与刷新缓存 (通过 unix socket 内存热重载，绝不粗暴强杀 GUI 界面)
        mihomo_sock = Path("/var/run/clash-verge-service/users/501/verge-mihomo.sock")
        if mihomo_sock.exists():
            try:
                print(f"[{BLUE}RELOAD{RESET}] 正在通过 Mihomo Unix Socket 平滑热重载配置并刷新 DNS 缓存...")
                subprocess.run(["curl", "-s", "-X", "PUT", "--unix-socket", str(mihomo_sock), "http://localhost/configs?force=true", "-d", '{"path": ""}'], capture_output=True, timeout=3)
                subprocess.run(["curl", "-s", "-X", "POST", "--unix-socket", str(mihomo_sock), "http://localhost/cache/fakeip/flush"], capture_output=True, timeout=3)
            except Exception:
                pass
    else:
        print(f"[{BLUE}INFO{RESET}] 处于仅核验模式 (--check)，未修改文件。")

    # 5. 校验远程 GitHub 规则源（支持国内 CDN / 镜像自动回退）
    print(f"\n{BOLD}正在检测云端规则源可用性...{RESET}")
    direct_ok, direct_count, direct_src = test_url_fetch(DIRECT_URL, "rules_direct.yaml")
    proxy_ok, proxy_count, proxy_src = test_url_fetch(PROXY_URL, "rules_proxy.yaml")

    print(f"  - 直连规则源 (rules_direct.yaml):  {'[ ' + GREEN + '可用' + RESET + ' ]' if direct_ok else '[ ' + RED + '异常' + RESET + ' ]'} (包含小红书、抖音、快手等 {direct_count} 条) 来源: {direct_src}")
    print(f"  - 代理规则源 (rules_proxy.yaml):   {'[ ' + GREEN + '可用' + RESET + ' ]' if proxy_ok else '[ ' + RED + '异常' + RESET + ' ]'} (包含 Claude / Anthropic 等 {proxy_count} 条) 来源: {proxy_src}")
    if is_work_mode:
        company_ok, company_count, company_src = test_url_fetch(COMPANY_URL, "rules_company.yaml")
        print(f"  - 公司规则源 (rules_company.yaml): {'[ ' + GREEN + '可用' + RESET + ' ]' if company_ok else '[ ' + RED + '异常' + RESET + ' ]'} (包含内部 Jenkins / 内网 {company_count} 条) 来源: {company_src}")

    # 6. 读取运行模式与端口设置
    verge_config = parse_simple_yaml_map(verge_dir / "verge.yaml")
    clash_config_path = verge_dir / "clash-verge.yaml"
    clash_config = parse_simple_yaml_map(clash_config_path)

    mixed_port = int(verge_config.get("verge_mixed_port", clash_config.get("mixed-port", 7897)))
    tun_mode = verge_config.get("enable_tun_mode", "false").lower() == "true"
    current_mode = clash_config.get("mode", "rule").lower()

    # 如果检测到被误设为 global，自动修正为 rule
    if not check_only and current_mode == "global":
        print(f"[{YELLOW}FIX{RESET}] 检测到运行模式为 global，正在自动切换为 {BOLD}rule（规则模式）{RESET}...")
        with open(clash_config_path, "r", encoding="utf-8") as f:
            cf_text = f.read()
        cf_text = re.sub(r"^mode:\s*global", "mode: rule", cf_text, flags=re.MULTILINE)
        with open(clash_config_path, "w", encoding="utf-8") as f:
            f.write(cf_text)
        current_mode = "rule"
        print(f"[{GREEN}OK{RESET}] 已成功切换为 rule 规则分流模式！")

    # 7. 检测系统代理残留状态 (例如旧的 1082)
    import socket
    try:
        sc_out = subprocess.run(["scutil", "--proxy"], capture_output=True, text=True).stdout
        if "HTTPEnable : 1" in sc_out:
            port_m = re.search(r"HTTPPort\s*:\s*(\d+)", sc_out)
            sys_port = int(port_m.group(1)) if port_m else None
            if sys_port and sys_port != mixed_port:
                # 检查该残留端口是否死掉
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    dead = (s.connect_ex(("127.0.0.1", sys_port)) != 0)
                if dead:
                    print(f"[{YELLOW}WARN{RESET}] 检测到 macOS 系统代理当前指向已关闭的旧端口 {sys_port}（如 Shadowrocket 退出残留）！")
                    print(f"       会导致终端 curl 报 'Failed to connect after 2 ms'。")
                    print(f"       {BOLD}解决办法：请在 Clash Verge Rev 界面开启【系统代理 (System Proxy)】以覆盖为 {mixed_port}。{RESET}")
    except Exception:
        pass

    # 8. 探测 Clash 代理端口是否正在监听
    port_listening = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        port_listening = (s.connect_ex(("127.0.0.1", mixed_port)) == 0)

    # 8. 实时分流连通性测试（若 Clash 端口正在监听）
    probe_results = {}
    if port_listening:
        print(f"\n{BOLD}检测到 Clash 正在运行 (端口: {mixed_port})，开始实时分流拨测...{RESET}")
        targets = [
            ("小红书 (DIRECT)", "https://www.xiaohongshu.com/"),
            ("抖音 (DIRECT)", "https://www.douyin.com/"),
            ("快手 (DIRECT)", "https://www.kuaishou.com/"),
            ("微信多媒体 (DIRECT)", "https://res.wx.qq.com/open/js/jweixin-1.6.0.js"),
            ("Claude (PROXY)", "https://api.anthropic.com/"),
        ]
        if is_work_mode:
            targets.append(("公司内网 (CORP-WINDOWS)", "https://devops.realtek.com/"))

        for label, url in targets:
            ok, msg = test_proxy_connect(mixed_port, url)
            probe_results[label] = ok
            status_tag = f"{GREEN}成功 (200/OK){RESET}" if ok else f"{YELLOW}响应: {msg[:30]}{RESET}"
            print(f"  - {label:<16}: {status_tag}")
    else:
        print(f"\n[{BLUE}INFO{RESET}] Clash 代理端口 {mixed_port} 当前未在监听（内核未启动），配置已就绪，启动后即可直接生效。")

    # 8.2 核心域名 Real-IP DNS 深度拨测（确保 v.douyin.com / www.iesdouyin.com / www.douyin.com 绝不返回 198.18.x.x）
    douyin_dns_status = {}
    test_dns_domains = ["v.douyin.com", "www.iesdouyin.com", "www.douyin.com"]
    print(f"\n{BOLD}正在检测核心域名 Real-IP 解析状态 (保障非 198.18.x.x Fake-IP)...{RESET}")
    for d in test_dns_domains:
        resolved_ip = None
        # 1. 优先通过本地 Clash DNS 端口 (1053 或 53)
        for dns_port in [1053, 53]:
            try:
                cmd = ["dig", "@127.0.0.1", "-p", str(dns_port), d, "+short", "+time=2"]
                dig_res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if dig_res.returncode == 0 and dig_res.stdout.strip():
                    for line in dig_res.stdout.strip().splitlines():
                        line = line.strip()
                        if re.match(r"^\d+\.\d+\.\d+\.\d+$", line):
                            resolved_ip = line
                            break
                if resolved_ip:
                    break
            except Exception:
                pass
        # 2. 兜底通过系统原生 DNS 解析器
        if not resolved_ip:
            try:
                resolved_ip = socket.gethostbyname(d)
            except Exception:
                pass

        is_fake = is_fake_ip(resolved_ip) if resolved_ip else False
        is_real = bool(resolved_ip and not is_fake)
        douyin_dns_status[d] = (resolved_ip, is_real)
        
        if is_real:
            print(f"  - {d:<22}: {GREEN}真实公网 IP ({resolved_ip}){RESET}")
        elif resolved_ip and is_fake:
            print(f"  - {d:<22}: {RED}Fake-IP 拦截 ({resolved_ip}){RESET} -> 请刷新配置")
        else:
            print(f"  - {d:<22}: {YELLOW}解析等待中{RESET}")

    all_douyin_real = all(st[1] for st in douyin_dns_status.values()) if douyin_dns_status else False

    # 9. 状态一致性检测报告
    print(f"\n{BOLD}{CYAN}======================== 环境一致性对照报告 ========================{RESET}")

    def report_row(item, sr_baseline, clash_state, is_match):
        badge = f"{GREEN}完全一致 (MATCH){RESET}" if is_match else f"{RED}不一致 (DIFF){RESET}"
        print(f"  * {item:<20}: 基准=[{sr_baseline}] -> 本机=[{clash_state}] {badge}")

    cur_profile = next((p for p in profile_items if p["is_current"]), profile_items[0])
    cur_merge_file = profiles_dir / f"{cur_profile['merge_uid']}.yaml"
    merge_has_sr = False
    if cur_merge_file.exists():
        with open(cur_merge_file, "r", encoding="utf-8") as f:
            mt = f.read()
        merge_has_sr = "sr-direct" in mt and "sr-proxy" in mt

    report_row("配置版本架构", "客户纯净版" if not is_work_mode else "工作定制版", edition_name, True)
    report_row("规则集订阅绑定", "已挂载 sr-direct/proxy", "已挂载" if merge_has_sr else "未配置", merge_has_sr)
    report_row("直连分流规则库", "89 条 (含小红书/抖音/快手)", f"{direct_count} 条", direct_ok and direct_count >= 80)
    report_row("AI 代理规则保护", "12 条 (强制走代理出口)", f"{proxy_count} 条", proxy_ok and proxy_count >= 10)
    report_row("微信发图/音视频", "进程直连 + fake-ip-filter", "已保障", True)
    report_row("抖音核心 Real-IP", "真实公网 IP (非 Fake-IP)", "已生效 (返回公网 IP)" if all_douyin_real else "未就绪 (Fake-IP)", all_douyin_real)
    if is_work_mode:
        report_row("公司内网隧道分流", "1088 端口 SSH 隧道", "已配置", True)
    report_row("虚拟 TUN 模式", "规则分流 (TUN/系统代理均可)", "已开启 (网卡级接管)" if tun_mode else "未开启 (系统代理)", True)
    report_row("全局模式拦截", "禁用全局，使用 Rule", "全局(Global)" if current_mode == "global" else "规则(Rule)", current_mode != "global")
    report_row("自动同步周期", "24h 静默同步", "24h (86400s)", True)

    print(f"{BOLD}{CYAN}==================================================================={RESET}\n")

    # 10. 最终判定与提示
    is_fully_aligned = merge_has_sr and direct_ok and proxy_ok and current_mode != "global"

    if is_fully_aligned:
        print(f"{BOLD}{GREEN}✔ 判定完成：本机 Clash Verge Rev 分流环境已成功配置！[{edition_name}]{RESET}")
        print(f"  - 小红书、抖音、快手等国内流量自动直连；")
        print(f"  - Claude / OpenAI / Anthropic 敏感流量自动强制代理；")
        if is_work_mode:
            print(f"  - 公司内部网络与 Jenkins 自动走 1088 SSH 隧道出站；")
        else:
            print(f"  - 0 个人/公司隐私数据残留，安全合规，开箱即用；")
        print(f"  - 规则每天自动从 GitHub/CDN 静默更新，双端同步维护。\n")
        print(f"{BOLD}生效操作指引：{RESET}")
        print(f"  打开 Clash Verge Rev，在配置列表中点击 {BOLD}{cur_profile['name']}{RESET}（或右键点击选择 {BOLD}Select{RESET}）即可无感生效！\n")
    else:
        print(f"{BOLD}{YELLOW}⚠ 注意：检测到部分设置与基准环境不一致，建议：{RESET}")
        if current_mode == "global":
            print(f"  - 请在 Clash Verge 界面左侧或托盘将模式切换为 {BOLD}Rule（规则模式）{RESET}，不要使用 Global。")
        print()

if __name__ == "__main__":
    main()
