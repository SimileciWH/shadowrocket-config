#!/usr/bin/env python3
"""Download one verified release snapshot and run its installer."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = "SimileciWH/shadowrocket-config"
FILES = ["scripts/setup_clash_verge.py", "clash/rules_direct.yaml",
         "clash/rules_proxy.yaml", "clash/rules_company.yaml"]


def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "shadowrocket-config-updater", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def api(path):
    return json.loads(fetch("https://api.github.com/repos/" + REPO + path +
                            ("&" if "?" in path else "?") + "_=" + str(time.time_ns())))


def latest_release():
    sha = api("/commits/main")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("GitHub 返回了无效提交号")
    runs = api("/actions/workflows/verify-release.yml/runs?head_sha=" + sha)["workflow_runs"]
    runs = [run for run in runs if run.get("head_sha") == sha and
            run.get("head_branch") == "main" and run.get("event") == "push"]
    if not runs:
        raise ValueError("最新提交尚无发布校验，请等待 GitHub Actions 完成后重试")
    latest = max(runs, key=lambda run: run["id"])
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        raise ValueError("最新提交尚未通过发布校验；未回退到旧版本，请稍后重试")
    return sha


def blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def download_snapshot(sha, directory):
    tree = api("/git/trees/" + sha + "?recursive=1")
    if tree.get("truncated"):
        raise ValueError("GitHub 文件清单不完整，停止更新")
    hashes = {item["path"]: item["sha"] for item in tree["tree"] if item["type"] == "blob"}
    for path in FILES:
        expected = hashes.get(path)
        if not expected:
            raise ValueError("发布缺少文件：" + path)
        urls = ["https://cdn.jsdelivr.net/gh/" + REPO + "@" + sha + "/" + path,
                "https://fastly.jsdelivr.net/gh/" + REPO + "@" + sha + "/" + path,
                "https://raw.githubusercontent.com/" + REPO + "/" + sha + "/" + path]
        for url in urls:
            try:
                data = fetch(url)
                if blob_hash(data) != expected:
                    continue
                target = directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                break
            except (OSError, ValueError):
                continue
        else:
            raise ValueError("无法下载并校验同版本文件：" + path + "；本机配置未修改")
    (directory / "release.json").write_text(json.dumps({"sha": sha, "files": {p: hashes[p] for p in FILES}}), encoding="utf-8")


def main():
    try:
        sha = latest_release()
        print("本次更新版本：" + sha, flush=True)
        with tempfile.TemporaryDirectory(prefix="clash-release-") as temp:
            directory = Path(temp)
            download_snapshot(sha, directory)
            if api("/commits/main")["sha"] != sha:
                raise ValueError("下载期间 main 已更新，请重新执行以获取最新完整版本")
            if "--download-only" in sys.argv:
                print("脚本和三份规则下载、哈希校验通过；未执行安装")
                return 0
            env = os.environ.copy()
            env["SR_RELEASE_SHA"] = sha
            env["SR_RELEASE_DIR"] = str(directory)
            return subprocess.call([sys.executable, str(directory / FILES[0])] + sys.argv[1:], env=env)
    except (OSError, ValueError, KeyError) as exc:
        print("更新停止：" + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
