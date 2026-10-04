#!/usr/bin/env python3
"""
Sync Shadowrocket configuration rules to Clash Verge YAML rule sets.

This script parses `sr_ai_secure_final.conf` and generates:
1. `clash/rules_direct.yaml`: Classical rule-provider payload for all DIRECT rules.
2. `clash/rules_proxy.yaml`: Classical rule-provider payload for all PROXY rules (Claude, Anthropic, etc.).
3. `clash/rules_company.yaml`: Classical rule-provider payload for company routes (CORP-WINDOWS).
4. `clash/clash_rules.yaml`: Complete full rules list (with policy targets mapped).
5. `clash/clash_merge_template.yaml`: Drop-in template for Clash Verge Rev Merge extension.
"""

import os
import re
import sys
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parent.parent
    sr_conf_path = repo_root / "sr_ai_secure_final.conf"
    clash_dir = repo_root / "clash"
    clash_dir.mkdir(parents=True, exist_ok=True)

    if not sr_conf_path.exists():
        print(f"Error: {sr_conf_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(sr_conf_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract version metadata
    version_match = re.search(r"^#\s*Shadowrocket Config Version:\s*(.+)$", content, re.MULTILINE)
    version = version_match.group(1).strip() if version_match else "unknown"
    change_match = re.search(r"^#\s*Change:\s*(.+)$", content, re.MULTILINE)
    change = change_match.group(1).strip() if change_match else "N/A"

    lines = content.splitlines()
    in_rules = False

    direct_payload = []
    proxy_payload = []
    company_payload = []
    ru_payload = []
    full_rules = []

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith("[Rule]"):
            in_rules = True
            continue
        if in_rules and line_clean.startswith("[") and line_clean.endswith("]"):
            in_rules = False
            break

        if not in_rules:
            continue

        if line_clean.startswith("#"):
            # Comment line
            full_rules.append(line_clean)
            continue

        # Parse rule line: TYPE,VALUE,TARGET[,OPTIONS...]
        parts = [p.strip() for p in line_clean.split(",")]
        rule_type = parts[0].upper()

        if rule_type == "FINAL":
            target = parts[1]
            # Map PROXY -> 节点选择 for Clash
            clash_target = "节点选择" if target == "PROXY" else target
            full_rules.append(f"- MATCH,{clash_target}")
            continue

        if rule_type == "RULE-SET":
            # Nested external rule-set, keep in full rules
            url = parts[1]
            target = parts[2]
            clash_target = "节点选择" if target == "PROXY" else target
            full_rules.append(f"- RULE-SET,{url},{clash_target}")
            continue

        if len(parts) >= 3:
            rule_type = parts[0]
            value = parts[1]
            target = parts[2]
            options = parts[3:] if len(parts) > 3 else []

            # Format for classical rule-provider payload (without policy target)
            payload_entry = f"{rule_type},{value}"
            if options:
                payload_entry += f",{','.join(options)}"

            # Format for full Clash rules
            clash_target = "节点选择" if target == "PROXY" else target
            full_rule_entry = f"- {rule_type},{value},{clash_target}"
            if options:
                full_rule_entry += f",{','.join(options)}"
            full_rules.append(full_rule_entry)

            # Categorize into classical payloads
            if target == "DIRECT":
                direct_payload.append(payload_entry)
            elif target == "PROXY":
                proxy_payload.append(payload_entry)
            elif target == "CORP-WINDOWS":
                company_payload.append(payload_entry)
            elif "justg" in target.lower() or "ru" in target.lower():
                ru_payload.append(payload_entry)
            else:
                # default fallback category
                direct_payload.append(payload_entry)

    # 1. Write clash/rules_direct.yaml
    direct_file = clash_dir / "rules_direct.yaml"
    with open(direct_file, "w", encoding="utf-8") as f:
        f.write(f"# Clash Classical Rule Provider: DIRECT\n")
        f.write(f"# Synced from: sr_ai_secure_final.conf (Version: {version})\n")
        f.write(f"# Change: {change}\n")
        f.write(f"# Total entries: {len(direct_payload)}\n")
        f.write("payload:\n")
        for item in direct_payload:
            f.write(f"  - {item}\n")

    # 2. Write clash/rules_proxy.yaml
    proxy_file = clash_dir / "rules_proxy.yaml"
    with open(proxy_file, "w", encoding="utf-8") as f:
        f.write(f"# Clash Classical Rule Provider: PROXY (Claude / Anthropic / AI)\n")
        f.write(f"# Synced from: sr_ai_secure_final.conf (Version: {version})\n")
        f.write(f"# Change: {change}\n")
        f.write(f"# Total entries: {len(proxy_payload)}\n")
        f.write("payload:\n")
        for item in proxy_payload:
            f.write(f"  - {item}\n")

    # 3. Write clash/rules_company.yaml
    company_file = clash_dir / "rules_company.yaml"
    with open(company_file, "w", encoding="utf-8") as f:
        f.write(f"# Clash Classical Rule Provider: CORP-WINDOWS (Company Internal)\n")
        f.write(f"# Synced from: sr_ai_secure_final.conf (Version: {version})\n")
        f.write(f"# Change: {change}\n")
        f.write(f"# Total entries: {len(company_payload)}\n")
        f.write("payload:\n")
        for item in company_payload:
            f.write(f"  - {item}\n")

    # 4. Write clash/clash_rules.yaml
    full_rules_file = clash_dir / "clash_rules.yaml"
    with open(full_rules_file, "w", encoding="utf-8") as f:
        f.write(f"# Complete Clash Rules\n")
        f.write(f"# Synced from: sr_ai_secure_final.conf (Version: {version})\n")
        f.write(f"# Change: {change}\n")
        f.write(f"# Note: 'PROXY' in Shadowrocket maps to '节点选择' in Clash.\n")
        f.write("rules:\n")
        for r in full_rules:
            if r.startswith("#"):
                f.write(f"  {r}\n")
            else:
                f.write(f"  {r}\n")

    # 5. Write clash/client_merge_template.yaml (客户纯净版：0 公司隐私，纯净分流)
    client_merge_file = clash_dir / "client_merge_template.yaml"
    with open(client_merge_file, "w", encoding="utf-8") as f:
        f.write("# Clash Verge Rev Merge 模版 (客户通用纯净版)\n")
        f.write("# 适用于外部客户/朋友电脑，彻底剥离任何公司内网信息与私有节点\n")
        f.write("# 包含：小红书/抖音/快手等国内大厂直连 + Claude/OpenAI 等海外 AI 智能分流\n\n")
        f.write("rule-providers:\n")
        f.write("  sr-direct:\n")
        f.write("    type: http\n")
        f.write("    behavior: classical\n")
        f.write("    format: yaml\n")
        f.write("    interval: 86400\n")
        f.write('    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_direct.yaml"\n')
        f.write("    path: ./ruleset/sr-direct.yaml\n\n")
        f.write("  sr-proxy:\n")
        f.write("    type: http\n")
        f.write("    behavior: classical\n")
        f.write("    format: yaml\n")
        f.write("    interval: 86400\n")
        f.write('    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_proxy.yaml"\n')
        f.write("    path: ./ruleset/sr-proxy.yaml\n\n")
        f.write("# 优先匹配规则列表\n")
        f.write("prepend-rules:\n")
        f.write("  - RULE-SET,sr-proxy,节点选择\n")
        f.write("  - RULE-SET,sr-direct,DIRECT\n")
        f.write("  - GEOIP,LAN,DIRECT,no-resolve\n")
        f.write("  - GEOIP,CN,DIRECT\n")
        f.write("  - MATCH,节点选择\n")

    # 6. Write clash/work_merge_template.yaml (个人工作版：包含公司 1088 SSH 隧道)
    work_merge_file = clash_dir / "work_merge_template.yaml"
    merge_template_file = clash_dir / "clash_merge_template.yaml"
    for mfile in [work_merge_file, merge_template_file]:
        with open(mfile, "w", encoding="utf-8") as f:
            f.write("# Clash Verge Rev Merge 模版 (个人工作定制版)\n")
            f.write("# 适用于个人办公电脑，包含公司内网 SSH 隧道 (127.0.0.1:1088) 与公司服务分流\n\n")
            f.write("rule-providers:\n")
            f.write("  sr-direct:\n")
            f.write("    type: http\n")
            f.write("    behavior: classical\n")
            f.write("    format: yaml\n")
            f.write("    interval: 86400\n")
            f.write('    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_direct.yaml"\n')
            f.write("    path: ./ruleset/sr-direct.yaml\n\n")
            f.write("  sr-proxy:\n")
            f.write("    type: http\n")
            f.write("    behavior: classical\n")
            f.write("    format: yaml\n")
            f.write("    interval: 86400\n")
            f.write('    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_proxy.yaml"\n')
            f.write("    path: ./ruleset/sr-proxy.yaml\n\n")
            f.write("  sr-company:\n")
            f.write("    type: http\n")
            f.write("    behavior: classical\n")
            f.write("    format: yaml\n")
            f.write("    interval: 86400\n")
            f.write('    url: "https://fastly.jsdelivr.net/gh/SimileciWH/shadowrocket-config@main/clash/rules_company.yaml"\n')
            f.write("    path: ./ruleset/sr-company.yaml\n\n")
            f.write("# 预定义公司节点与策略组\n")
            f.write("proxies:\n")
            f.write("  - name: CORP-WINDOWS-NODE\n")
            f.write("    type: socks5\n")
            f.write("    server: 127.0.0.1\n")
            f.write("    port: 1088\n\n")
            f.write("prepend-proxy-groups:\n")
            f.write("  - name: CORP-WINDOWS\n")
            f.write("    type: select\n")
            f.write("    proxies:\n")
            f.write("      - CORP-WINDOWS-NODE\n")
            f.write("      - DIRECT\n")
            f.write("      - 节点选择\n\n")
            f.write("  - name: justg-vps-RU-direct\n")
            f.write("    type: select\n")
            f.write("    proxies:\n")
            f.write("      - 节点选择\n")
            f.write("      - DIRECT\n\n")
            f.write("# 优先匹配规则列表\n")
            f.write("prepend-rules:\n")
            f.write("  - RULE-SET,sr-company,CORP-WINDOWS\n")
            f.write("  - RULE-SET,sr-proxy,节点选择\n")
            f.write("  - RULE-SET,sr-direct,DIRECT\n")
            f.write("  - GEOIP,LAN,DIRECT,no-resolve\n")
            f.write("  - GEOIP,CN,DIRECT\n")
            f.write("  - MATCH,节点选择\n")

    print(f"Successfully synced Clash rules from {sr_conf_path.name} (v{version}):")
    print(f"  - DIRECT rules: {len(direct_payload)} -> {direct_file.name}")
    print(f"  - PROXY rules: {len(proxy_payload)} -> {proxy_file.name}")
    print(f"  - COMPANY rules: {len(company_payload)} -> {company_file.name}")
    print(f"  - Full rules: {len(full_rules)} lines -> {full_rules_file.name}")
    print(f"  - Merge template: -> {merge_template_file.name}")

if __name__ == "__main__":
    main()
