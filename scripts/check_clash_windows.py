#!/usr/bin/env python3
"""Read-only Windows runtime and network acceptance checks."""
import argparse
import ctypes
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

import yaml


def pipe_api(pipe, secret, path):
    if not ctypes.windll.kernel32.WaitNamedPipeW(pipe, 5000):
        raise OSError("内核命名管道不可用")
    with open(pipe, "r+b", buffering=0) as handle:
        class PipeSocket:
            def makefile(self, *args, **kwargs):
                return handle

        request = (f"GET {path} HTTP/1.1\r\nHost: localhost\r\n"
                   f"Authorization: Bearer {secret}\r\nConnection: close\r\n\r\n")
        handle.write(request.encode())
        response = http.client.HTTPResponse(PipeSocket())
        response.begin()
        body = response.read()
        if response.status != 200:
            raise ValueError(f"内核接口 {path} 返回 {response.status}")
        return json.loads(body)


def main():
    parser = argparse.ArgumentParser(description="只读验证 Windows Clash 实际运行与联网状态")
    parser.add_argument("--dir", type=Path, default=Path(os.environ.get("APPDATA", ".")) /
                        "io.github.clash-verge-rev.clash-verge-rev")
    parser.add_argument("--skip-network", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("此验收脚本需要在 Windows 上运行")
    sys.stdout.reconfigure(encoding="utf-8")
    results = []

    def record(name, ok, detail):
        results.append(bool(ok))
        print(json.dumps({"检查": name, "通过": bool(ok), "详情": detail}, ensure_ascii=False), flush=True)

    try:
        config = yaml.safe_load((args.dir / "clash-verge.yaml").read_text(encoding="utf-8-sig"))
        suffix = re.search(r"([0-9a-f]{64})$", config.get("external-controller-pipe", ""))
        if not suffix:
            raise ValueError("无法从当前配置确定内核实例，停止而不选择其他用户的内核")
        names = [name for name in os.listdir("\\\\.\\pipe\\")
                 if name.startswith("verge-mihomo-") and name.endswith(suffix.group(1))]
        if len(names) != 1:
            raise ValueError("当前用户的运行内核数量不是 1")
        pipe = "\\\\.\\pipe\\" + names[0]
        secret = config.get("secret", "")
        actual = pipe_api(pipe, secret, "/configs")
        record("实际配置", actual.get("mode") == "rule" and actual.get("ipv6") is False
               and actual.get("tun", {}).get("stack", "").lower() == "mixed",
               {"mode": actual.get("mode"), "ipv6": actual.get("ipv6"), "tun": actual.get("tun")})
        providers = pipe_api(pipe, secret, "/providers/rules").get("providers", {})
        for name in ("sr-direct", "sr-proxy"):
            count = providers.get(name, {}).get("ruleCount", 0)
            record(name, count > 0, {"ruleCount": count})
        proxies = pipe_api(pipe, secret, "/proxies").get("proxies", {})
        rules = pipe_api(pipe, secret, "/rules").get("rules", [])
        targets = {rule.get("proxy") for rule in rules}
        missing = sorted(targets - set(proxies) - {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"})
        record("规则目标", not missing, {"rules": len(rules), "missing": missing})
        print(json.dumps({"选中代理组": {k: v.get("now") for k, v in proxies.items() if "now" in v}},
                         ensure_ascii=False), flush=True)
        if not args.skip_network:
            for host in ("v.douyin.com", "www.iesdouyin.com", "www.douyin.com"):
                try:
                    addresses = sorted({r[4][0] for r in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
                    record(host, bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses), addresses)
                except OSError as exc:
                    record(host, False, str(exc))
            port = actual.get("mixed-port", 7897)
            for label, flags in (("显式代理", ["--proxy", f"http://127.0.0.1:{port}"]),
                                 ("系统网络", ["--noproxy", "*"])):
                for host, url, expected in (
                    ("微信资源", "https://res.wx.qq.com/open/js/jweixin-1.6.0.js", "200"),
                    ("Google", "https://www.google.com/generate_204", "204"),
                ):
                    try:
                        result = subprocess.run(["curl.exe", "-sS", "--max-time", "12", *flags,
                                                 "-o", "NUL", "-w", "%{http_code}", url],
                                                capture_output=True, timeout=17)
                        status = result.stdout.decode(errors="replace").strip()
                        record(label + "/" + host, result.returncode == 0 and status == expected,
                               {"exit": result.returncode, "http": status,
                                "error": result.stderr.decode(errors="replace")[-350:]})
                    except subprocess.TimeoutExpired:
                        record(label + "/" + host, False, "请求超时")
    except (OSError, ValueError, KeyError, yaml.YAMLError, http.client.HTTPException) as exc:
        record("运行态检查", False, str(exc))
    if args.skip_network:
        print("本次跳过网络；不能据此判定 ClipVault 测试环境就绪。")
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
