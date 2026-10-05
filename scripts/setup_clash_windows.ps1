#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$InstallDir = "$env:ProgramFiles\Clash Verge",
    [string]$DataDir = "$env:APPDATA\io.github.clash-verge-rev.clash-verge-rev",
    [string]$Python = 'python',
    [string]$ProfileFile,
    [string]$ProfileName = '同步基准订阅',
    [switch]$Doh,
    [switch]$Work
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$app = Join-Path $InstallDir 'clash-verge.exe'
$core = Join-Path $InstallDir 'verge-mihomo.exe'
foreach ($file in @($app, $core, (Join-Path $DataDir 'profiles.yaml'))) {
    if (!(Test-Path -LiteralPath $file)) {
        throw "缺少 $file；请先安装 Clash Verge Rev，并在当前用户下导入、选中订阅。"
    }
}
& $Python -c 'import sys; assert sys.version_info >= (3, 10)'
if ($LASTEXITCODE -ne 0) { throw '需要 Python 3.10 或更高版本。' }
& $Python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('yaml') else 1)"
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install PyYAML
    if ($LASTEXITCODE -ne 0) { throw 'PyYAML 安装失败。' }
}

# Keep private operational files outside the repository.
$stage = Join-Path $env:TEMP ("clash-windows-deploy-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
$updater = Join-Path $stage 'update_clash.py'

$service = Get-Service 'clash_verge_service' -ErrorAction SilentlyContinue
if (!$service) {
    $installer = Join-Path $InstallDir 'resources\clash-verge-service-install.exe'
    if (!(Test-Path $installer)) { throw '缺少 Clash 官方服务安装程序。' }
    $process = Start-Process $installer -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Clash 服务安装失败。' }
}
Set-Service 'clash_verge_service' -StartupType Automatic

# Launch in the logged-in user's desktop, including when invoked over SSH.
$taskName = 'Clash-Deployment-' + [guid]::NewGuid().ToString('N')
$action = New-ScheduledTaskAction -Execute $app
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal | Out-Null
$internetSettings = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$proxyBefore = (Get-ItemProperty $internetSettings).ProxyEnable
$failure = $null
try {
    Get-Process 'clash-verge' -ErrorAction SilentlyContinue | Stop-Process -Force
    Stop-Service 'clash_verge_service' -ErrorAction SilentlyContinue
    (Get-Service 'clash_verge_service').WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    # A stopped core must not remain the updater's HTTP proxy.
    Set-ItemProperty $internetSettings -Name ProxyEnable -Value 0
    Invoke-WebRequest 'https://raw.githubusercontent.com/SimileciWH/shadowrocket-config/main/scripts/update_clash.py' `
        -OutFile $updater -TimeoutSec 60 -UseBasicParsing
    if ($ProfileFile) {
        # Import only an explicitly supplied private profile; preserve existing entries.
        $importer = Join-Path $stage 'import_profile.py'
        @'
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import uuid
import yaml

root, source = map(pathlib.Path, sys.argv[1:3])
raw = source.read_bytes()
data = yaml.safe_load(raw.decode("utf-8-sig"))
if not isinstance(data, dict) or not data.get("proxies") or not data.get("proxy-groups"):
    raise ValueError("基准订阅必须包含节点和代理组")
uid = "sr_import_" + hashlib.sha256(raw).hexdigest()[:16]
index_path = root / "profiles.yaml"
before = index_path.read_bytes()
index = yaml.safe_load(before.decode("utf-8-sig"))
found = [item for item in index["items"] if item["uid"] == uid]
target = root / "profiles" / (uid + ".yaml")
if found:
    if len(found) != 1 or found[0].get("file") != target.name or found[0].get("type") != "local" or target.read_bytes() != raw:
        raise ValueError("基准订阅标识冲突，未覆盖已有配置")
else:
    if target.exists():
        raise ValueError("基准订阅文件已存在但未登记，停止导入")
    index["items"].append({"uid": uid, "type": "local", "name": sys.argv[3],
                           "file": target.name, "updated": int(time.time())})
index["current"] = uid
encoded = json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8")
if yaml.safe_load(before.decode("utf-8-sig")) != index:
    backup = root / ("sr-import-backup-" + uuid.uuid4().hex)
    backup.mkdir()
    shutil.copy2(index_path, backup / "profiles.yaml")
    if index_path.read_bytes() != before:
        raise ValueError("订阅索引被其他程序修改，停止导入")
    created = False
    try:
        if not found:
            with target.open("xb") as handle:
                handle.write(raw)
            created = True
        fd, name = tempfile.mkstemp(dir=root, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
            os.replace(name, index_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    except Exception:
        if created:
            target.unlink()
        raise
    print("基准订阅已导入并选中；旧订阅保留；备份：" + str(backup))
else:
    print("当前已选中同一基准订阅，无需重复导入。")
'@ | Set-Content -LiteralPath $importer -Encoding UTF8
        & $Python $importer $DataDir $ProfileFile $ProfileName
        if ($LASTEXITCODE -ne 0) { throw '基准订阅导入失败。' }
    }
    $env:CLASH_MIHOMO_BIN = $core
    $arguments = @($updater, '--dir', $DataDir)
    if ($Work) { $arguments += '--work' }
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw '正式更新入口失败；未绕过发布校验。' }

    # Verge's base configuration overrides these Merge fields at runtime.
    $aligner = Join-Path $stage 'align_runtime.py'
    @'
import copy
import json
import os
import pathlib
import shutil
import sys
import tempfile
import uuid
import yaml

root = pathlib.Path(sys.argv[1])
def read(path):
    value = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("配置必须是 YAML 映射：" + str(path))
    return value

index = read(root / "profiles.yaml")
items = {item["uid"]: item for item in index["items"]}
profile = items[index["current"]]
merge_item = items[profile["option"]["merge"]]
merge_path = (root / "profiles" / merge_item["file"]).resolve()
if not merge_path.is_relative_to((root / "profiles").resolve()):
    raise ValueError("Merge 路径超出配置目录")
merge = read(merge_path)
providers = merge.get("rule-providers", {})
if not all(name in providers for name in ("sr-direct", "sr-proxy")):
    raise ValueError("当前订阅缺少正式同步扩展")
if sys.argv[2] == "True":
    original_merge = copy.deepcopy(merge)
    replacements = {"223.5.5.5": "https://223.5.5.5/dns-query",
                    "119.29.29.29": "https://doh.pub/dns-query"}
    def https_resolvers(value):
        if isinstance(value, dict):
            return {key: https_resolvers(item) for key, item in value.items()}
        if isinstance(value, list):
            return [https_resolvers(item) for item in value]
        return replacements.get(value, value) if isinstance(value, str) else value
    merge["dns"] = https_resolvers(merge["dns"])
    # Bootstrap resolvers must not depend on a DNS hostname.
    merge["dns"]["default-nameserver"] = ["https://223.5.5.5/dns-query", "https://223.6.6.6/dns-query"]
    if merge != original_merge:
        backup = root / ("sr-doh-backup-" + uuid.uuid4().hex)
        backup.mkdir()
        shutil.copy2(merge_path, backup / merge_path.name)
        if read(merge_path) != original_merge:
            raise ValueError("Merge 被其他进程修改，停止写入")
        fd, name = tempfile.mkstemp(dir=merge_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(merge, handle, ensure_ascii=False, indent=2)
            os.replace(name, merge_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print("已按显式参数将默认 DNS 改为 HTTPS；备份：" + str(backup))
base_path = root / "config.yaml"
before = base_path.read_bytes()
base = read(base_path)
desired = copy.deepcopy(base)
desired["ipv6"] = merge["ipv6"]
desired.setdefault("tun", {})
for key in ("stack", "mtu", "dns-hijack", "auto-route", "auto-detect-interface", "strict-route"):
    desired["tun"][key] = copy.deepcopy(merge["tun"][key])
if desired != base:
    backup = root / ("sr-runtime-backup-" + uuid.uuid4().hex)
    backup.mkdir()
    shutil.copy2(base_path, backup / "config.yaml")
    if base_path.read_bytes() != before:
        raise ValueError("配置被其他进程修改，停止写入")
    fd, name = tempfile.mkstemp(dir=root, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(desired, handle, ensure_ascii=False, indent=2)
        os.replace(name, base_path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print("基础设置已对齐；备份：" + str(backup))
else:
    print("基础设置已经一致，无需修改。")
'@ | Set-Content -LiteralPath $aligner -Encoding UTF8
    & $Python $aligner $DataDir $Doh.IsPresent.ToString()
    if ($LASTEXITCODE -ne 0) { throw '基础设置对齐失败。' }
} catch {
    $failure = $_
} finally {
    if ($null -ne $proxyBefore) {
        Set-ItemProperty $internetSettings -Name ProxyEnable -Value $proxyBefore
    }
    Start-Service 'clash_verge_service'
    Start-ScheduledTask -TaskName $taskName
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Remove-Item -LiteralPath $stage -Recurse -Force
}
if ($failure) { throw $failure }
Write-Host '同步及重启请求完成。仍须验收内核、规则集、系统 DNS 和实际 HTTP 请求。'
