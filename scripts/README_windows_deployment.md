# Windows 批量部署与验收

`setup_clash_windows.ps1` 是 Windows 前置准备和重载包装器；规则更新仍调用 README 中的 `update_clash.py` 正式入口，不绕过 GitHub 发布校验、不改用旧发布、不复制 macOS 的运行态配置。

## 前提

- 安装 Clash Verge Rev，优先使用与 Windows 系统架构匹配的官方安装包。
- 安装 Python 3.10 或更高版本；脚本会在缺少 PyYAML 时通过该 Python 的 pip 安装。
- 在实际使用 Clash 的 Windows 用户下启动一次客户端，导入并选中自己的订阅。
- 以同一用户的管理员 PowerShell 执行。SSH 执行时，该用户也须已登录 Windows 桌面，脚本通过临时交互式计划任务启动客户端。
- 根据测试目标在客户端启用 TUN 或系统代理。脚本保留这个选择，不通过复制 macOS 的开关状态决定 Windows 网络模式。

本仓库不包含节点和订阅凭据。各设备保留自己的当前订阅；规则一致不代表节点、出口 IP 或操作系统行为完全一致。

若需要和某台基准电脑使用同一份节点配置，通过私有通道传输该电脑的原始订阅文件，显式传入 `-ProfileFile`。脚本添加并选中新订阅，保留旧订阅；同一内容重复导入不会新增条目。不要把这个私有文件放进仓库。

## 执行

将仓库中的 `scripts/setup_clash_windows.ps1` 复制到目标 Windows 后执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup_clash_windows.ps1
```

UTM 本次采用同一基准订阅，并在确认 UDP 53 超时、HTTPS DNS 可用后显式切换默认 DNS 传输：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup_clash_windows.ps1 `
  -ProfileFile .\mac-baseline.private.yaml -ProfileName mac-bwg-cal -Doh
```

`-Doh` 将脚本预设的阿里/腾讯 UDP 解析器改为 HTTPS，使用 IP 地址形式的阿里 DoH 完成引导解析；保留自定义解析器及 Real-IP 过滤。后续更新也需要携带这个显式参数，否则正式入口会恢复默认 DNS 传输。此选项不改变 DIRECT/PROXY 规则，也不关闭 TLS 校验。Mihomo 的相关设置见 [DNS 官方文档](https://wiki.metacubex.one/config/dns/)。

`ExecutionPolicy Bypass` 仅作用于本次 PowerShell 进程，不修改机器的永久执行策略。

工作模式仍需显式参数：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup_clash_windows.ps1 -Work
```

自定义路径：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup_clash_windows.ps1 `
  -InstallDir 'D:\Clash Verge' -DataDir 'D:\ClashData' -Python 'C:\Python312\python.exe'
```

脚本会安装缺失的官方后台服务并设为自动启动，停止当前 Clash、临时关闭当前用户的系统代理，调用正式更新入口，然后对齐基础配置中会覆盖 Merge 的 IPv6 和 TUN 参数。订阅、节点、端口、TUN 开关及其他基础配置保持原值。

正式入口创建 `sr-backup-*`；基础配置有变化时另建 `sr-runtime-backup-*`，保存原 `config.yaml`。可选导入及 DoH 调整分别创建 `sr-import-backup-*` 和 `sr-doh-backup-*`。修改完成或更新失败后均尝试恢复代理开关、启动服务和客户端。多个阶段不构成一个事务；失败时以实际日志与备份为准。

## 必须独立验收

脚本完成仅表示同步及启动请求完成，不能代替以下验收：

将 `scripts/check_clash_windows.py` 一起复制到 Windows，执行 `python .\check_clash_windows.py`。它从当前用户的内核命名管道读取实际状态，不开放控制端口；检查失败返回非零退出码。`--skip-network` 只能用于内核运行检查，不代表网络就绪。

1. 后台服务、Mihomo 内核和本机代理端口确实运行。
2. 实际内核是 Rule 模式，`sr-direct`、`sr-proxy` 已加载且规则数量正确，规则目标存在。
3. 实际 IPv6 设置及 TUN 栈与当前 Merge 一致；基础配置不能再次覆盖成旧值。
4. 用应用相同的 `socket.getaddrinfo` 路径检查抖音域名，所有地址均为公网 IP。
5. 分别执行显式代理、系统网络路径的 HTTPS 请求；HTTP CONNECT 成功不代表后续 TLS 成功，403 也不能记为 200。
6. 重启 Clash 后重复关键检查，最后再由 ClipVault 执行真实解析、下载及文件落盘验证。

## UTM 共享网络

UTM 的 Windows 除了自己的 Clash，还可能受到 macOS VPN/TUN 的影响。先检查 Windows DHCP DNS：若指向 UTM 网关，应核实该网关是否返回宿主机的 Fake-IP。

同时存在宿主机 Fake-IP 和来宾 TUN 时，不能仅凭脚本已写入 Real-IP 过滤断言 Windows 的系统 DNS 正常。应对照来宾 TUN 开关、公共 DNS 与 HTTPS，并在允许短暂影响宿主机网络时做宿主 VPN 开关对照。不要为了通过测试而关闭 ClipVault 的非公网地址校验。
