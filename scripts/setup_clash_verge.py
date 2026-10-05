#!/usr/bin/env python3
"""Install current-profile extensions from a verified release snapshot.

Use scripts/update_clash.py for installation and upgrades. The updater verifies
one Git commit for this script and all providers before invoking this file.
Direct --check remains read-only; standalone installation is rejected.
"""

from __future__ import annotations

import os
import json
import hashlib
import copy
import tempfile
import uuid
import sys
import re
import socket
import ipaddress
import time
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Windows 控制台编码与虚拟终端 ANSI 颜色适配（彻底杜绝 cp936 / cp1252 乱码及问号 ???）
if sys.platform == "win32":
    try:
        import ctypes
        # 设置控制台代码页为 UTF-8 (65001)
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
        # 启用 ANSI 颜色序列支持 (ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004)
        handle = ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ctypes.windll.kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass
    try:
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

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
# Exact CNAME targets observed in the macOS resolver path; avoid broad CDN suffixes.
DOUYIN_CNAME_HOSTS = [
    "www.iesdouyin.com.bytedns1.com",
    "www.iesdouyin.com.w.kunluncan.com",
    "www.iesdouyin.com.queniuum.com",
    "v.douyin.com.bytedns1.com",
    "v.douyin.com.w.cdngslb.com",
    "v.douyin.com.queniuiq.com",
    "www.douyin.com.bytedns1.com",
    "www.douyin.com-1.download.ks-cdn.com",
    "q2.gslb.ksyuncdn.com",
    "q2-fclouddns.gslb.new.fclouddns.net",
]

DOUYIN_REAL_IP_DOMAINS = [
    *DOUYIN_CNAME_HOSTS,
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

# 微软 Windows 系统更新、交付优化 (Delivery Optimization) 与网络探测直连域名
MICROSOFT_REAL_IP_DOMAINS = [
    "+.mp.microsoft.com",
    "+.windowsupdate.com",
    "+.update.microsoft.com",
    "+.msftconnecttest.com",
    "+.msftncsi.com",
    "+.windows.com",
    "+.s-microsoft.com",
]

# 所有需要确保返回真实公网 IP 的目标域名集
ALL_REAL_IP_DOMAINS = WECHAT_REAL_IP_DOMAINS + DOUYIN_REAL_IP_DOMAINS + MICROSOFT_REAL_IP_DOMAINS

# 系统代理 Bypass 核心直连后缀
BYPASS_LIST_ITEMS = [
    "*.qq.com", "*.wechat.com", "*.weixin.qq.com", "*.weixin.com",
    "*.qpic.cn", "*.qpic.com", "*.gtimg.cn", "*.gtimg.com", "*.qlogo.cn",
    "*.wechatos.net", "*.servicewechat.com", "*.weixinbridge.com",
    "*.wechatpay.cn", "*.tenpay.com", "*.myqcloud.com", "*.qcloud.com",
    "*.tencent.com", "*.cdn-go.cn", "*.tencentcs.cn", "*.tencent-cloud.com", "*.tencent-cloud.cn",
    "*.douyin.com", "*.iesdouyin.com", "*.douyincdn.com", "*.douyinpic.com",
    "*.douyinstatic.com", "*.douyinvod.com", "*.zjcdn.com", "*.ydycdn.com",
    "*.bytednsdoc.com", "*.byteimg.com", "*.ibytedtos.com",
    "*.mp.microsoft.com", "*.windowsupdate.com", "*.update.microsoft.com",
    "*.msftconnecttest.com", "*.msftncsi.com", "*.windows.com", "*.s-microsoft.com"
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

def system_dns_status(host: str) -> tuple[list[str], bool]:
    """Check the application's resolver path, including every returned address."""
    try:
        addresses = sorted({record[4][0] for record in socket.getaddrinfo(
            host, 443, type=socket.SOCK_STREAM)})
        parsed = [ipaddress.ip_address(address) for address in addresses]
        public = bool(parsed) and all(
            ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified)
            for ip in parsed
        )
        return addresses, public
    except (OSError, ValueError):
        return [], False


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


def extract_yaml_name(line: str) -> str | None:
    """从 YAML 行为 name: 'xxx' 或 - name: xxx 提取纯净名称。"""
    m = re.search(r"name:\s*(.+)", line)
    if not m:
        return None
    val = m.group(1).strip()
    if val.startswith('"'):
        q_m = re.match(r'"([^"]+)"', val)
        if q_m:
            return q_m.group(1)
    elif val.startswith("'"):
        q_m = re.match(r"'([^']+)'", val)
        if q_m:
            return q_m.group(1)
    if "," in val:
        val = val.split(",", 1)[0].strip()
    if val.endswith("}"):
        val = val[:-1].strip()
    return val.strip("\"' ")

def load_yaml(text):
    """Parse YAML safely without installing packages on the customer's machine."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:
        import yaml
    except ImportError:
        if not shutil.which("ruby"):
            raise ValueError("缺少 YAML 解析器，请安装 PyYAML 后重试：python3 -m pip install PyYAML")
        result = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e",
             "puts YAML.safe_load(STDIN.read, [], [], true).to_json"],
            input=text, capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise ValueError("YAML 解析失败；未修改配置")
        return json.loads(result.stdout)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        raise ValueError("YAML 解析失败；未修改配置") from None


def yaml_text(data):
    # JSON is a YAML subset and preserves names without manual quoting.
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def resolve_profile_file(profiles_dir, p_uid, p_file=None):
    """Resolve only the exact metadata path; never guess another subscription."""
    path = profiles_dir / (p_file or (p_uid + ".yaml"))
    if path.resolve().parent != profiles_dir.resolve():
        raise ValueError("配置文件必须位于 profiles 目录内")
    if not path.is_file():
        raise ValueError("元数据指向的配置文件不存在：" + path.name)
    return path


def detect_main_proxy_group(profile_path):
    """Choose an existing unambiguous group, never silently route AI directly."""
    data = load_yaml(profile_path.read_text(encoding="utf-8"))
    names = [g["name"] for g in data.get("proxy-groups", [])]
    matches = [r.split(",")[1].strip() for r in data.get("rules", [])
               if isinstance(r, str) and r.startswith("MATCH,")]
    for name in matches + ["PROXY", "节点选择", "🚀 节点选择", "Proxy"]:
        if name in names and name not in ("DIRECT", "REJECT"):
            return name, names
    candidates = [n for n in names if not any(k in n.lower()
                  for k in ("direct", "reject", "直连", "拦截", "广告"))]
    if len(candidates) == 1:
        return candidates[0], names
    raise ValueError("无法唯一确定代理组，请在订阅中设置 MATCH 指向实际代理组")


def build_client_merge_content(main_group: str = "DIRECT", existing_groups: list[str] = None) -> str:
    """构建客户通用纯净版 Merge 扩展内容（根据实际代理组自适应绑定与注入兼容别名）。"""
    cname_filter = "\n".join(f'    - "{host}"' for host in DOUYIN_CNAME_HOSTS)
    if existing_groups is None:
        existing_groups = []

    alias_groups = []
    target = main_group if main_group and main_group != "DIRECT" else "DIRECT"
    if "节点选择" not in existing_groups and main_group != "节点选择":
        alias_groups.append(f"""  - name: 节点选择\n    type: select\n    proxies:\n      - "{target}"\n      - DIRECT""")
    if "PROXY" not in existing_groups and main_group != "PROXY":
        alias_groups.append(f"""  - name: PROXY\n    type: select\n    proxies:\n      - "{target}"\n      - DIRECT""")

    prepend_groups_block = ""
    if alias_groups:
        prepend_groups_block = "prepend-proxy-groups:\n" + "\n".join(alias_groups) + "\n\n"

    return f"""# Profile Enhancement Merge for Clash Verge Rev (Client Public Edition)
# Generated by shadowrocket-config sync script
# Auto-syncs rules from CDN: fastly.jsdelivr.net / GitHub

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

{prepend_groups_block}prepend-rules:
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
  # 微软 Windows 系统更新与交付优化直连（彻底杜绝 Windows Update / Delivery Optimization 走代理导致 EOF 报错及消耗大量流量）
  - DOMAIN-SUFFIX,mp.microsoft.com,DIRECT
  - DOMAIN-SUFFIX,windowsupdate.com,DIRECT
  - DOMAIN-SUFFIX,windowsupdate.microsoft.com,DIRECT
  - DOMAIN-SUFFIX,update.microsoft.com,DIRECT
  - DOMAIN-SUFFIX,msftconnecttest.com,DIRECT
  - DOMAIN-SUFFIX,msftncsi.com,DIRECT
  - DOMAIN-SUFFIX,windows.com,DIRECT
  - DOMAIN-SUFFIX,s-microsoft.com,DIRECT
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
    - "+.mp.microsoft.com"
    - "+.windowsupdate.com"
    - "+.update.microsoft.com"
    - "+.windows.com"
    - "+.s-microsoft.com"
    # 抖音全系核心域名直连（返回真实 IP，彻底防止 ClipVault / 爬虫因 fake-ip 判定非公网拒绝连接）
{cname_filter}
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

def build_work_merge_content(main_group: str = "DIRECT", existing_groups: list[str] = None) -> str:
    """构建个人工作定制版 Merge 扩展内容（包含公司 1088 SSH 隧道与自适应代理组）。"""
    cname_filter = "\n".join(f'    - "{host}"' for host in DOUYIN_CNAME_HOSTS)
    if existing_groups is None:
        existing_groups = []

    alias_groups = []
    target = main_group if main_group and main_group != "DIRECT" else "DIRECT"
    if "节点选择" not in existing_groups and main_group != "节点选择":
        alias_groups.append(f"""  - name: 节点选择\n    type: select\n    proxies:\n      - "{target}"\n      - DIRECT""")
    if "PROXY" not in existing_groups and main_group != "PROXY":
        alias_groups.append(f"""  - name: PROXY\n    type: select\n    proxies:\n      - "{target}"\n      - DIRECT""")

    prepend_groups = [
        f"""  - name: CORP-WINDOWS\n    type: select\n    proxies:\n      - CORP-WINDOWS-NODE\n      - DIRECT\n      - "{target}" """
    ] + alias_groups

    prepend_groups_block = "prepend-proxy-groups:\n" + "\n".join(prepend_groups) + "\n\n"

    return f"""# Profile Enhancement Merge for Clash Verge Rev (Work Private Edition)
# Generated by shadowrocket-config sync script
# Auto-syncs rules from CDN: fastly.jsdelivr.net / GitHub

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

{prepend_groups_block}prepend-rules:
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
  # 微软 Windows 系统更新与交付优化直连（彻底杜绝 Windows Update / Delivery Optimization 走代理导致 EOF 报错及消耗大量流量）
  - DOMAIN-SUFFIX,mp.microsoft.com,DIRECT
  - DOMAIN-SUFFIX,windowsupdate.com,DIRECT
  - DOMAIN-SUFFIX,windowsupdate.microsoft.com,DIRECT
  - DOMAIN-SUFFIX,update.microsoft.com,DIRECT
  - DOMAIN-SUFFIX,msftconnecttest.com,DIRECT
  - DOMAIN-SUFFIX,msftncsi.com,DIRECT
  - DOMAIN-SUFFIX,windows.com,DIRECT
  - DOMAIN-SUFFIX,s-microsoft.com,DIRECT
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
    - "+.mp.microsoft.com"
    - "+.windowsupdate.com"
    - "+.update.microsoft.com"
    - "+.windows.com"
    - "+.s-microsoft.com"
    # 抖音全系核心域名直连（返回真实 IP，彻底防止 ClipVault / 爬虫因 fake-ip 判定非公网拒绝连接）
{cname_filter}
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


def get_custom_dir_arg():
    for i, arg in enumerate(sys.argv):
        if arg in ("--dir", "-d", "--path") and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
        if arg.startswith("--dir=") or arg.startswith("--path="):
            return Path(arg.split("=", 1)[1].strip("'\""))
    if "CLASH_VERGE_DIR" in os.environ:
        return Path(os.environ["CLASH_VERGE_DIR"])
    return None

def find_verge_dir():
    """
    智能定位 Clash Verge Rev 数据目录，返回 (Path, status)。
    status 可取值:
      - "ok": 成功找到目录且 profiles.yaml 存在
      - "no_profiles": 找到了有效数据目录（存在 verge.yaml/clash-verge.yaml 等），但尚未生成 profiles.yaml
      - "empty_dir": 找到了候选目录，但目录为空
      - "custom_not_found": 用户指定的 --dir 不存在
      - "not_found": 候选目录均未匹配到
    """
    custom_dir = get_custom_dir_arg()
    if custom_dir:
        if custom_dir.is_dir():
            if (custom_dir / "profiles.yaml").exists():
                return custom_dir, "ok"
            elif any((custom_dir / f).exists() for f in ["verge.yaml", "clash-verge.yaml", "config.yaml"]):
                return custom_dir, "no_profiles"
            return custom_dir, "ok"
        return None, "custom_not_found"

    appdata = os.environ.get("APPDATA")
    localappdata = os.environ.get("LOCALAPPDATA")
    userprofile = os.environ.get("USERPROFILE") or str(Path.home())
    prog_files = os.environ.get("ProgramFiles")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)")

    candidates = [
        # macOS 常见路径
        Path.home() / "Library" / "Application Support" / "io.github.clash-verge-rev.clash-verge-rev",
        Path.home() / "Library" / "Application Support" / "clash-verge-rev",
        Path.home() / "Library" / "Application Support" / "clash-verge",
        Path.home() / "Library" / "Application Support" / "Clash Verge Rev",
        # Linux / portable
        Path.home() / ".config" / "clash-verge-rev",
        Path.home() / ".config" / "clash-verge",
        Path.home() / ".config" / "io.github.clash-verge-rev.clash-verge-rev",
    ]

    sub_names = [
        "io.github.clash-verge-rev.clash-verge-rev",
        "clash-verge-rev",
        "Clash Verge Rev",
        "clash-verge",
        "Clash Verge",
        "clash_verge_rev",
        "clash_verge",
    ]

    # Windows 目录
    if appdata:
        appdata_path = Path(appdata)
        for name in sub_names:
            candidates.append(appdata_path / name)
    if localappdata:
        local_path = Path(localappdata)
        for name in sub_names:
            candidates.append(local_path / name)
            candidates.append(local_path / "Programs" / name)
            candidates.append(local_path / "Programs" / name / "config")
            candidates.append(local_path / "Programs" / name / "data")
    if userprofile:
        up = Path(userprofile)
        for name in sub_names:
            candidates.append(up / ".config" / name)
        # 扫描用户 Downloads 与 Desktop 下的便携解压目录
        for folder in [up / "Downloads", up / "Desktop"]:
            if folder.exists():
                try:
                    for sub in folder.iterdir():
                        if sub.is_dir() and any(k in sub.name.lower() for k in ["clash", "verge"]):
                            candidates.append(sub)
                            candidates.append(sub / "config")
                            candidates.append(sub / "data")
                            candidates.append(sub / ".config")
                except Exception:
                    pass

    if prog_files:
        pf = Path(prog_files)
        for name in sub_names:
            candidates.append(pf / name)
            candidates.append(pf / name / "config")
            candidates.append(pf / name / "data")
    if prog_files_x86:
        pfx = Path(prog_files_x86)
        for name in sub_names:
            candidates.append(pfx / name)
            candidates.append(pfx / name / "config")
            candidates.append(pfx / name / "data")

    # 尝试从 Windows 正在运行的进程提取路径 (针对免配置便携版定位)
    if sys.platform == "win32":
        try:
            ps_cmd = [
                "powershell", "-NoProfile", "-Command",
                "Get-Process | Where-Object { $_.ProcessName -match 'verge|clash|mihomo' } | Select-Object -ExpandProperty Path -ErrorAction SilentlyContinue"
            ]
            res = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    p = Path(line.strip())
                    if p.is_file():
                        p_dir = p.parent
                        for sub in [p_dir / "config", p_dir / "data", p_dir / ".config", p_dir]:
                            candidates.insert(0, sub)
        except Exception:
            pass

    # 去重
    unique_candidates = []
    seen = set()
    for c in candidates:
        try:
            p_str = str(c)
            if p_str not in seen:
                seen.add(p_str)
                unique_candidates.append(c)
        except Exception:
            pass

    # 1. 优先选择包含 profiles.yaml 的目录
    for c in unique_candidates:
        try:
            if c.exists() and (c / "profiles.yaml").exists():
                return c, "ok"
        except Exception:
            pass

    # 2. 其次选择包含 verge.yaml / clash-verge.yaml / config.yaml 的目录
    for c in unique_candidates:
        try:
            if c.exists() and any((c / f).exists() for f in ["verge.yaml", "clash-verge.yaml", "config.yaml"]):
                return c, "no_profiles"
        except Exception:
            pass

    # 3. 再次选择已存在的候选目录
    for c in unique_candidates:
        try:
            if c.exists() and c.is_dir():
                return c, "empty_dir"
        except Exception:
            pass

    return None, "not_found"

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
    try:
        curl_bin = "curl.exe" if sys.platform == "win32" else "curl"
        result = subprocess.run([
            curl_bin, "-sS", "-L", "--max-time", str(timeout),
            "--noproxy", "", "--proxy", f"http://127.0.0.1:{port}",
            "-o", os.devnull, "-w", "%{http_code}", target_url,
        ], capture_output=True, text=True, timeout=timeout + 2)
        code = result.stdout.strip()
        if result.returncode == 0 and code.isdigit() and 200 <= int(code) < 400:
            return True, "HTTP " + code
        return False, "HTTP " + code if code.isdigit() else "连接失败"
    except (OSError, subprocess.TimeoutExpired):
        return False, "curl 不可用或访问超时"

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

def release_snapshot():
    """Require a complete, verified snapshot when a release context is supplied."""
    sha = os.environ.get("SR_RELEASE_SHA")
    root = os.environ.get("SR_RELEASE_DIR")
    if not sha and not root:
        return None
    if not sha or not root or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("发布版本上下文不完整，请使用 update_clash.py")
    directory = Path(root)
    manifest = json.loads((directory / "release.json").read_text(encoding="utf-8"))
    if manifest.get("sha") != sha:
        raise ValueError("发布清单版本不一致")
    files = {}
    for name in ("scripts/setup_clash_verge.py", "clash/rules_direct.yaml", "clash/rules_proxy.yaml", "clash/rules_company.yaml"):
        data = (directory / name).read_bytes()
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if manifest.get("files", {}).get(name) != digest:
            raise ValueError("发布文件校验失败：" + name)
        files[name] = data.decode("utf-8")
    return sha, files


def prepare_deployment(verge_dir, work=False):
    """Prepare current-profile extensions without mutating live configuration."""
    index_path = verge_dir / "profiles.yaml"
    index_content = index_path.read_bytes()
    index = load_yaml(index_content.decode("utf-8"))
    expected = {index_path: index_content}
    items = index.get("items", [])
    by_uid = {item["uid"]: item for item in items}
    if len(by_uid) != len(items):
        raise ValueError("profiles.yaml 含重复 UID")
    profile = by_uid.get(index.get("current"))
    if not profile or profile.get("type") not in ("local", "remote"):
        raise ValueError("请先在 Clash 中选择一个有效订阅；不会自动选择第一个订阅")
    directory = verge_dir / "profiles"
    source = resolve_profile_file(directory, profile["uid"], profile.get("file"))
    group, groups = detect_main_proxy_group(source)
    if "," in group or "\n" in group:
        raise ValueError("代理组名称包含规则分隔符，无法安全生成规则")
    generated = load_yaml((build_work_merge_content if work else build_client_merge_content)("SR_TARGET", ["PROXY", "节点选择"]))
    generated["prepend-rules"] = [rule.replace(",SR_TARGET", "," + group)
                                  for rule in generated["prepend-rules"]]
    options = profile.setdefault("option", {})
    updates = {}
    snapshot = release_snapshot()
    if snapshot:
        sha, files = snapshot
        for name, provider in generated["rule-providers"].items():
            filename = "rules_" + name[3:] + ".yaml"
            cache = (verge_dir / "ruleset" / (name + "-" + sha + ".yaml")).resolve()
            provider["url"] = "https://cdn.jsdelivr.net/gh/SimileciWH/shadowrocket-config@" + sha + "/clash/" + filename
            provider["path"] = str(cache.resolve())
            updates[cache] = files["clash/" + filename]
            expected[cache] = cache.read_bytes() if cache.exists() else None

    def extension(kind):
        uid = options.get(kind)
        if uid:
            item = by_uid.get(uid)
            if not item or item.get("type") != kind:
                raise ValueError("扩展引用无效：" + kind)
            if any(p.get("uid") != profile["uid"] and
                   p.get("option", {}).get(kind) == uid for p in items):
                raise ValueError("当前扩展被其他订阅共享，请先在 Clash 中创建独立扩展：" + kind)
            path = resolve_profile_file(directory, uid, item.get("file"))
            expected[path] = path.read_bytes()
            data = load_yaml(expected[path].decode("utf-8")) or {}
        else:
            uid = "sr_" + uuid.uuid4().hex[:12]
            path = directory / (uid + ".yaml")
            item = {"uid": uid, "type": kind, "name": "SR-AutoSync-" + kind,
                    "file": path.name, "updated": int(time.time())}
            expected[path] = None
            items.append(item)
            options[kind] = uid
            data = {}
        if not isinstance(data, dict):
            raise ValueError("扩展必须为 YAML 映射：" + kind)
        return path, data

    merge_path, merge = extension("merge")
    rules_path, rules = extension("rules")
    desired = [r for r in generated.pop("prepend-rules")
               if not r.startswith(("MATCH,", "GEOIP,"))]
    generated.pop("prepend-proxy-groups", None)
    corp_nodes = generated.pop("proxies", [])
    # Only migrate known installer-managed legacy entries; preserve unknown data.
    def managed(rule):
        return isinstance(rule, str) and (rule in desired or
            rule.startswith(("RULE-SET,sr-proxy,", "RULE-SET,sr-direct,", "RULE-SET,sr-company,")))
    legacy = merge.pop("prepend-rules", [])
    legacy_groups = merge.get("prepend-proxy-groups", [])
    if legacy_groups:
        # Unknown legacy group definitions require manual migration.
        if any(g.get("name") not in ("PROXY", "节点选择", "CORP-WINDOWS")
               or g.get("type") != "select"
               or any(n not in (group, "DIRECT", "CORP-WINDOWS-NODE") for n in g.get("proxies", []))
               for g in legacy_groups):
            raise ValueError("Merge 含自定义旧版代理组，请先在 Clash 编辑组中迁移")
        merge.pop("prepend-proxy-groups")
    for key in ("prepend", "append", "delete"):
        if not isinstance(rules.get(key, []), list):
            raise ValueError("规则扩展字段必须是列表：" + key)
        rules[key] = [r for r in rules.get(key, []) if not managed(r)]
    for rule in legacy:
        if not managed(rule) and not rule.startswith(("MATCH,", "GEOIP,")) and rule not in rules["prepend"]:
            rules["prepend"].append(rule)
    rules["prepend"] = desired + rules["prepend"]
    # Merge mappings recursively rather than replacing customer provider entries.
    def combine(dst, src):
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                combine(dst[key], value)
            else:
                dst[key] = copy.deepcopy(value)
        return dst
    if "proxies" in merge:
        old_nodes = merge["proxies"]
        if old_nodes == [{"name": "CORP-WINDOWS-NODE", "type": "socks5", "server": "127.0.0.1", "port": 1088}]:
            merge.pop("proxies")
    combine(merge, generated)
    if not work:
        merge.get("rule-providers", {}).pop("sr-company", None)
    updates[merge_path] = yaml_text(merge)
    updates[rules_path] = yaml_text(rules)
    if work:
        for kind, entries in (("proxies", corp_nodes), ("groups", [{"name": "CORP-WINDOWS", "type": "select", "proxies": ["CORP-WINDOWS-NODE"]}])):
            path, data = extension(kind)
            names = {entry["name"] for entry in entries}
            data["prepend"] = entries + [v for v in data.get("prepend", []) if v.get("name") not in names]
            data.setdefault("append", [])
            data.setdefault("delete", [])
            updates[path] = yaml_text(data)
    updates[index_path] = yaml_text(index)
    # Check a synthetic candidate, explicitly not the application's full script pipeline.
    candidate = load_yaml(source.read_text(encoding="utf-8"))
    combine(candidate, merge)
    for kind, field in (("proxies", "proxies"), ("groups", "proxy-groups"), ("rules", "rules")):
        uid = options.get(kind)
        if not uid:
            continue
        item = next(i for i in items if i["uid"] == uid)
        path = directory / item["file"]
        data = load_yaml(updates[path] if path in updates else resolve_profile_file(directory, uid, item.get("file")).read_text(encoding="utf-8"))
        existing = candidate.get(field, [])
        deleted = data.get("delete", [])
        existing = [v for v in existing if (v.get("name") if isinstance(v, dict) else v) not in deleted]
        candidate[field] = data.get("prepend", []) + existing + data.get("append", [])
    targets = {g["name"] for g in candidate.get("proxy-groups", [])} | {p["name"] for p in candidate.get("proxies", [])} | {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
    for rule in candidate.get("rules", []):
        fields = rule.split(",")
        target = fields[-2] if fields[-1] == "no-resolve" else fields[-1]
        if target not in targets:
            raise ValueError("候选规则引用不存在的代理目标：" + target)
    core = os.environ.get("CLASH_MIHOMO_BIN") or shutil.which("verge-mihomo") or shutil.which("mihomo")
    mac_core = Path("/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo")
    if not core and mac_core.is_file():
        core = str(mac_core)
    if not core:
        raise ValueError("未找到 Mihomo，未写入配置；请将 CLASH_MIHOMO_BIN 设置为当前 Clash 内核的完整路径")
    validation = "候选引用检查通过"
    if core:
        with tempfile.TemporaryDirectory(prefix="sr-check-") as temp:
            if snapshot:
                for name, provider in candidate.get("rule-providers", {}).items():
                    if name in generated["rule-providers"]:
                        cache = Path(provider["path"])
                        staged = Path(temp) / cache.name
                        staged.write_text(updates[cache], encoding="utf-8")
                        provider["path"] = str(staged)
            path = Path(temp) / "candidate.yaml"
            path.write_text(yaml_text(candidate), encoding="utf-8")
            path.chmod(0o600)
            result = subprocess.run([core, "-t", "-d", temp, "-f", str(path)], capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise ValueError("候选配置未通过 Mihomo 校验；未写入配置。请在 Clash 中检查订阅和扩展")
        validation = "候选配置通过 Mihomo 校验；应用最终合成配置仍需重载确认"
    return {"updates": updates, "expected": expected, "profile": profile, "validation": validation}


def apply_deployment(plan):
    """Back up all targets and roll back already-written files on failure."""
    originals = {p: p.read_bytes() if p.exists() else None for p in plan["updates"]}
    if originals != plan["expected"]:
        raise ValueError("准备期间配置已被其他程序修改，请重新运行")
    backup_dir = next(p.parent for p in originals if p.name == "profiles.yaml") / ("sr-backup-" + uuid.uuid4().hex)
    backup_dir.mkdir(mode=0o700)
    print("配置备份目录：" + str(backup_dir))
    for i, (path, content) in enumerate(originals.items()):
        if content is not None:
            backup = backup_dir / (str(i) + "-" + path.name)
            backup.write_bytes(content)
            backup.chmod(0o600)
    written = []
    try:
        for path, text in plan["updates"].items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temp = Path(handle.name)
                handle.write(text.encode("utf-8"))
            try:
                os.replace(temp, path)
            finally:
                if temp.exists():
                    temp.unlink()
            written.append(path)
    except Exception:
        for path in reversed(written):
            if originals[path] is None:
                path.unlink()
            else:
                path.write_bytes(originals[path])
        raise


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
    verge_dir, dir_status = find_verge_dir()
    if dir_status == "custom_not_found":
        custom_arg = get_custom_dir_arg()
        print(f"[{RED}FAIL{RESET}] 无法找到指定的配置目录: {custom_arg}")
        print(f"       请检查路径拼写是否正确。")
        sys.exit(1)

    if dir_status == "not_found" or not verge_dir:
        print(f"[{RED}FAIL{RESET}] 未能自动定位到 Clash Verge Rev 数据目录。")
        print(f"\n{BOLD}排查与解决指引：{RESET}")
        print(f"  1. 【初次安装未运行】：如果刚在电脑上安装完客户端，请先【双击打开运行一次】Clash Verge Rev。")
        print(f"     （客户端初次启动时才会自动生成 AppData 基础数据目录）")
        print(f"  2. 【便携绿色版 / 自定义安装路径】：若使用解压即用的便携版，请通过参数指定其数据目录，例如：")
        if sys.platform == "win32":
            print(f"     python setup_clash_verge.py --dir \"C:\\你的路径\\config\"")
            print(f"     或 irm <url> -OutFile $env:TEMP\\setup.py; python $env:TEMP\\setup.py --dir \"C:\\你的路径\\config\"")
        else:
            print(f"     python3 scripts/setup_clash_verge.py --dir \"/path/to/clash-verge-dir\"")
        sys.exit(1)

    if dir_status == "empty_dir":
        print(f"[{YELLOW}WARN{RESET}] 探测到目录: {verge_dir}，但目录为空。")
        print(f"       请先打开一次 Clash Verge Rev，并在界面中导入一个订阅配置。")
        sys.exit(1)

    print(f"[{GREEN}OK{RESET}] 定位到 Clash Verge Rev 数据目录: {verge_dir}")

    # 2. 读取 profiles.yaml 识别所有配置（包括当前配置与备用配置，如 justg, bwg-cal 等）
    profiles_yaml_path = verge_dir / "profiles.yaml"
    if not profiles_yaml_path.exists():
        print(f"[{RED}FAIL{RESET}] 目录中未找到 profiles.yaml 配置文件！")
        print(f"\n{BOLD}排查与解决指引：{RESET}")
        print(f"  👉 原因：Clash Verge Rev 刚安装启动，但【配置 (Profiles)】中尚未添加任何代理节点或订阅。")
        print(f"  👉 解决步骤：")
        print(f"     1. 打开 Clash Verge Rev 界面；")
        print(f"     2. 点击左侧【配置 (Profiles)】菜单，导入您的机场订阅链接（或添加一个本地配置）；")
        print(f"     3. 导入后在列表中点击选中该配置；")
        print(f"     4. 重新执行本同步脚本即可完成一键对齐与规则注入！\n")
        sys.exit(1)

    try:
        if not check_only and release_snapshot() is None:
            raise ValueError("请通过 scripts/update_clash.py 更新，以保证脚本和规则版本一致")
        deployment = prepare_deployment(verge_dir, is_work_mode)
        if not check_only:
            apply_deployment(deployment)
            print(f"[{GREEN}OK{RESET}] 当前订阅扩展已写入并备份；请在 Clash 中重新选择当前订阅。")
        else:
            print(f"[{BLUE}INFO{RESET}] 仅检查模式：未修改文件。")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"[{RED}FAIL{RESET}] {exc}")
        return 1
    profiles_dir = verge_dir / "profiles"
    cur_profile = deployment["profile"]

    if os.environ.get("SR_RELEASE_SHA"):
        global DIRECT_URL, PROXY_URL, COMPANY_URL, FALLBACK_BASES
        revision = os.environ["SR_RELEASE_SHA"]
        base = "https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/" + revision + "/clash"
        DIRECT_URL, PROXY_URL, COMPANY_URL = [base + "/rules_" + kind + ".yaml" for kind in ("direct", "proxy", "company")]
        FALLBACK_BASES = ["https://cdn.jsdelivr.net/gh/SimileciWH/shadowrocket-config@" + revision + "/clash"]
        print("扩展与规则固定版本：" + revision)

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

    # 7. 检测系统代理残留状态 (例如旧的 1082)
    import socket
    if sys.platform != "win32":
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
    else:
        try:
            reg_cmd = ["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"]
            reg_out = subprocess.run(reg_cmd, capture_output=True, text=True).stdout
            if "ProxyEnable    REG_DWORD    0x1" in reg_out:
                ps_m = re.search(r"ProxyServer\s+REG_SZ\s+(.+)", reg_out)
                if ps_m:
                    server_str = ps_m.group(1).strip()
                    host_port = server_str.split(";")[-1].split("=")[-1]
                    if ":" in host_port:
                        h, p = host_port.split(":")
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(0.5)
                            if s.connect_ex((h, int(p))) != 0:
                                print(f"[{YELLOW}WARN{RESET}] 检测到 Windows 系统代理指向失效地址: {server_str}")
                                print(f"       会导致 curl 报 'Proxy CONNECT aborted'。")
                                print(f"       {BOLD}解决办法：请在 Windows 设置 -> 网络和 Internet -> 代理 中关闭手动代理，或在 Clash Verge Rev 中重新开启【系统代理】覆盖。{RESET}")
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
            status_tag = f"{GREEN}收到 HTTP 响应: {msg}{RESET}" if ok else f"{YELLOW}响应: {msg[:30]}{RESET}"
            print(f"  - {label:<16}: {status_tag}")
    else:
        print(f"\n[{BLUE}INFO{RESET}] Clash 代理端口 {mixed_port} 当前未在监听（内核未启动），尚未验证配置加载和网络可用性。")

    # 8.2 核心域名 Real-IP DNS 深度拨测（确保 v.douyin.com / www.iesdouyin.com / www.douyin.com 绝不返回 198.18.x.x）
    douyin_dns_status = {}
    test_dns_domains = ["v.douyin.com", "www.iesdouyin.com", "www.douyin.com"]
    print(f"\n{BOLD}正在检测核心域名 Real-IP 解析状态 (保障非 198.18.x.x Fake-IP)...{RESET}")
    for d in test_dns_domains:
        # Direct DNS queries can pass while getaddrinfo follows a fake-IP CNAME.
        addresses, is_real = system_dns_status(d)
        resolved_ip = ", ".join(addresses) if addresses else None
        douyin_dns_status[d] = (resolved_ip, is_real)
        
        if is_real:
            print(f"  - {d:<22}: {GREEN}真实公网 IP ({resolved_ip}){RESET}")
        elif resolved_ip:
            print(f"  - {d:<22}: {RED}非公网/Fake-IP 拦截 ({resolved_ip}){RESET} -> 请刷新配置")
        else:
            print(f"  - {d:<22}: {YELLOW}解析等待中{RESET}")

    all_douyin_real = all(st[1] for st in douyin_dns_status.values()) if douyin_dns_status else False

    print("\n验收状态：")
    print("  扩展文件：" + ("已准备，未写入" if check_only else "已写入并备份"))
    print("  内核校验：" + deployment["validation"])
    print("  应用加载：未验证；请重新选择当前订阅，确认无校验错误")
    print("  网络探测：仅代表当前正在运行的配置，不证明新扩展已加载")
    print("  当前模式：" + current_mode)
    print("  请勿将文件写入成功视为部署验收通过。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
