# Clash 当前订阅同步与验收

`setup_clash_verge.py` 默认同步客户版；只有显式 `--work` / `--company` 才添加公司规则和本机 1088 SOCKS 节点。

```bash
python3 scripts/update_clash.py --dir "/path/to/clash-verge-data"
python3 scripts/update_clash.py --check --dir "/path/to/clash-verge-data"
```

脚本通过 `profiles.yaml.current` 定位当前订阅，通过每个条目的 `file` 定位订阅和扩展。它不会按显示名称匹配，不扫描最新 YAML 兜底，也不会自动切换到第一份订阅。缺少 Merge / Rules 扩展时创建独立扩展并登记元数据；已有引用失效或扩展被其他订阅共享时停止，避免误改其他订阅。

规则写入 Rules 扩展的 `prepend`，规则源和 DNS 设置写入 Merge。工作版代理与组分别写入 Proxies / Groups 扩展。只替换脚本管理的 sr-* 规则及去重的预设规则，保留其他 prepend / append / delete 项和自定义 provider。旧版 Merge 的脚本字段被迁移；无法确认来源的旧代理组要求人工迁移。

代理目标从真实订阅的代理组读取，优先沿 MATCH 选择。无法确定时停止，绝不回退为 DIRECT。特殊字符由 YAML 解析器处理，不通过正则猜文件结构。

依赖 PyYAML；macOS 未安装 PyYAML 时可使用系统 Ruby 的安全 YAML 解析器。无需为此自动安装软件。找不到解析器时会显示安装方式。

写入前使用 Mihomo 检查候选配置。macOS 自动识别 `/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo`；也搜索 PATH 中的 verge-mihomo / mihomo。其他安装路径可设置环境变量：

```bash
export CLASH_MIHOMO_BIN="/path/to/verge-mihomo"
```

Windows PowerShell 示例：

```powershell
$env:CLASH_MIHOMO_BIN = 'C:\path\to\verge-mihomo.exe'
```

内核缺失或校验失败时不写入配置。候选使用临时目录校验，不直接重载内核或改写 `clash-verge.yaml`。候选校验不模拟全局扩展和 JavaScript 脚本的执行，不能替代 Clash 自身最终配置校验。规则源、Geo 数据不可用也可能导致内核校验失败。

原文件备份到数据目录下独立的 `sr-backup-*` 私有目录，路径会在终端显示。文件逐个原子替换，写入异常时恢复已写入文件；整个多文件操作不是跨进程事务。准备期间检测到元数据或目标扩展被其他程序修改会停止。建议先关闭 Clash 再同步，以避免应用内存中的旧配置覆盖修改。

`--check` 只构造和校验候选并探测当前运行环境，不修改数据目录，也不表示当前安装内容已与候选相同。

完成写入后，打开 Clash 并重新选择当前订阅：

1. 确认界面不再报 `proxy [...] not found`。
2. 检查应用生成配置的真正 `rules`，目标必须存在于 `proxy-groups` / `proxies`。
3. 检查内核接口中的实际组和选中节点。
4. 开启系统代理或 TUN，用显式代理访问 Google 等目标，最后由浏览器验证。

脚本网络探测只代表探测时正在运行的配置，不能证明刚写入的新扩展已加载。收到 HTTP 403 等响应也不会标为 HTTP 200 成功。

本次小红书修复保留 Shadowrocket 分流规则正文，仅更新版本元数据并同步生成文件、归档。发布前须单独授权 commit / push；本地脚本修改不会自动更新 CDN。

## 一致版本发布

推送 main 后，GitHub Actions `verify-release.yml` 运行生成器并检查生成结果与已提交的 clash 文件一致，再运行相关测试。生成结果有差异时发布校验失败；应本地运行 `python3 scripts/sync_clash.py` 并一起提交，不能只提交源配置。

`update_clash.py` 查询 main 的完整 SHA，要求该提交最新的 push 校验成功；不会在失败或等待时自动退回旧发布。下载同 SHA 的脚本和三份规则，对照 GitHub tree 中的 blob 哈希校验；下载过程中 main 改变则停止，要求重试。

安装器将已校验规则保存到带 SHA 的独立路径，以 `type: file` 交给内核。Clash 服务模式会复制本地 file provider 到服务运行目录，避免将已下载快照误当成需重新下载的 HTTP 缓存。候选内核使用临时副本校验，正式写入纳入备份和回滚；已有管理规则源的旧 URL / interval 会移除，自定义规则源保留。镜像即使缓存异常也不能绕过下载哈希校验。系统时钟、GitHub 可用性和匿名 API 额度会影响更新，失败时原配置保留。

`python3 scripts/update_clash.py --download-only` 只验证线上快照，不修改或启动 Clash。`--check` 仍只检查候选和运行状态。直接运行 setup 安装写入会被拒绝，防止与未确认版本的规则混搭。

更新入口保证一次更新使用同一版本，不是后台远程推送服务：已安装设备需要再次执行入口并在 Clash 中重新选择订阅，或由支持人员在任务空闲后通过 SSH 执行同一入口并重启 Clash 加载。安装器使用本地快照，不依赖内核运行时重新下载；下次版本更新仍需执行入口。旧 Fastly @main 安装命令应停用。

## 小红书真实 IP 修复（2026-10-16）

客户版和工作版的当前订阅 Merge 均补入 `+.xiaohongshu.com`、`+.xhscdn.com`、`+.xhscdn.net`，以及客户系统实际返回的四个精确 CNAME 别名（见验证记录）；生成模板使用同一份域名常量，避免安装器与模板漏同步。系统 DNS 拨测同时覆盖小红书主站和本次实际视频 CDN。

操作顺序：等待客户现有下载完成 → 执行已发布的 `update_clash.py` → 按输出重新激活当前订阅 → 检查主站/CDN 的系统 DNS 全部为公网地址 → 客户重试失败素材并核对文件。支持人员不直接编辑客户生成配置，不为验证强制中断任务。发布前本地改动不会进入客户更新入口。
