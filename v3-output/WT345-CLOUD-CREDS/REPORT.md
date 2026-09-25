# WT345-CLOUD-CREDS — 阿里云凭据获取（HEAVY 浏览器槽）：BLOCKED 报告

- **base SHA**: `b280d38a`（main）
- **工位**: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt345-cloud-creds`
- **触碰面**: 仅本文档（`v3-output/WT345-CLOUD-CREDS/REPORT.md`，纯文档新增）。**零产品代码改动**；后端/mobile/gateway/proto 未触碰。
- **结论**: **BLOCKED**——卡面第 1 步（computer-use 操控用户桌面 Chrome）在本 worker 运行时被结构性拒绝，未获得任何凭据，未执行任何云上操作（含读）。按卡面「如实 BLOCKED 收场并写明卡点」与 AGENTS.md「无真实凭据或设备时交付阻塞证据，不伪造通过」办理。

## 一、卡点：子 Agent 运行时拒绝全部官方浏览器/桌面自动化通道（按尝试顺序逐字记录）

1. **computer-use（卡面指定通道）**：按 `computer-use` 0.6.3 SKILL.md 引导（`setupComputerUseRuntime`）调用 `agent.computerUse.listApps()`，运行时直接抛错：
   > `Computer Use is not available in subagent`

   这与 SKILL.md 自身契约一致（"Main agent only. Never delegate Computer Use to a subagent"）——本 worker 即子 Agent，通道在宿主层面（`mcp__node_repl__js` host）被拒，非权限弹窗、非暂时占用（非 `CONTROLLER_BUSY`）。
2. **browser-use 降级探测**：bootstrap `setupBrowserRuntime` 后调用 `agent.browsers.list()`，同样被宿主拒绝：
   > `Browser is not available in subagent`

   且卡面明确排除 browser-use 自带实例（无阿里云登录态）；`extension` 后端即便存在也属同一被拒宿主面。
3. **不越权换技术栈**：computer-use SKILL.md 明文禁止在被拒后切换其他 UI 自动化技术（"Do not switch to a different UI-automation technology after an access refusal"），故不走 `osascript`/System Events 等野路子操控登录态浏览器——那既违反技能契约，也绕开「全舰队唯一浏览器槽」的并发纪律，且对含登录态的浏览器做未受审计的 UI 脚本化风险不可接受。

## 二、外围事实核验（全部只读，证明无旁路可自助完成）

| 检查项 | 命令/位置 | 结果 |
|---|---|---|
| Chrome 进程 | `pgrep -fl "Google Chrome"` | **未运行**（无登录态会话可附着） |
| CDP 调试口 | `lsof` + curl 探 `127.0.0.1:9222/9223/9333 /json/version` | **全关**，无既有调试口 |
| aliyun CLI | `aliyun version` | 已装 3.5.1（`/opt/homebrew/bin/aliyun`） |
| CLI 凭据 | `~/.aliyun/acs-cfg.json` | 仅 profile `default`，mode=Account，**无 AccessKey** |
| CLI secrets | `~/.aliyun/secrets.json` | 空结构，无凭据 |
| 环境变量 | `env` + rc 文件 grep | 无 `ALIBABA_CLOUD_*`/`ALIYUN_*` |
| 舰队密钥目录 | `/tmp/sparkle_cloud_secrets/env.prod`（0700 目录，既有文件属其他卡） | **0 处** `ALIBABA_CLOUD_ACCESS_KEY` 引用（该文件与本卡无关，未改动） |

结论：本机不存在任何可复用的阿里云凭据或可附着浏览器通道，卡面目标无法在本 worker 内自助达成。

## 三、已就绪的交接面（下次尝试零准备成本）

1. **凭据落盘点已建**：`/tmp/sparkle_cloud_secrets/`（mode `0700`）。目标文件仍为 `aliyun_ak.sh`，格式照卡面：
   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID=...
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
   ```
   `chmod 600`，不入 git、不在任何返回文本复述 SK。
2. **worktree/分支已建**：`git worktree add ../Sparkle-sysrev/wt345-cloud-creds -b wt345-cloud-creds main`（base `b280d38a`），本报告即首个交付物。
3. **验证与侦察 runbook**（凭据就位后原样执行）：
   ```bash
   source /tmp/sparkle_cloud_secrets/aliyun_ak.sh
   aliyun configure set --profile sparkle --mode AccessKey \
     --access-key-id "$ALIBABA_CLOUD_ACCESS_KEY_ID" --access-key-secret "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" --region cn-beijing
   aliyun sts GetCallerIdentity                       # 返回账号 UID 即凭据有效
   aliyun ecs DescribeInstanceAttribute --InstanceId i-2ze439t934c2gsdqm778   # 只读侦察：公网 IP/状态/规格
   ```
4. **解锁路径（需协调者动作，非本 worker 可自助）**：二选一——
   - (a) 由**主 Agent**（computer-use/browser-use 可用面）执行卡面第 1–4 步的浏览器腿：打开 RAM 控制台创建 AccessKey（子账号优先，授权含 ECS + 云助手），AK 写入上述路径；浏览器腿完成后再派发本卡收尾（验证+侦察+报告补全），或直接并入主 Agent 会话一次完成；
   - (b) 用户提供凭据的其他合规交付渠道（如用户自行创建 AK 后安全放置），本卡 runbook 直接从第 3 步续跑。
   浏览器腿若遇 MFA/二次验证无法自助完成，按卡面仍以 BLOCKED 收场并记录卡点。

## 四、安全与边界自查

- 全程**零云上写操作**（未进控制台，重启/清机/安全组/云助手一概未触）；唯一产出为本报告与空凭据目录，无任何凭据明文出现于日志、报告或返回文本。
- `~/.aliyun`、`/tmp/sparkle_cloud_secrets` 既有文件一律未读值、未改动（仅键名/计数级检查）。
- HEAVY 浏览器槽：本 worker 从未实际占用（宿主即拒），无窗口遗留需清理；`agent.computerUse.stop()` 无从也无需调用。

## 五、收工门

| 门 | 结果 |
|---|---|
| 凭据落盘 | 未达成（无凭据可落盘）；落盘点与格式已备好 |
| sts GetCallerIdentity | 未执行（前置缺失，未伪造） |
| DescribeInstanceAttribute 侦察 | 未执行（同上） |
| 浏览器槽释放 | 天然释放（从未获得通道） |
| 守卫 | `scripts/run_all_rule_guards.sh` 于本 worktree：仅 AQ/BG 两规则失败——基线 A/B 实证为存量环境失败（两规则是 proto 生成物 parity 检查，`app.gen`/`*.pb.go`/`*_pb2.py`/`*.pb.dart` 为 gitignore 产物，fresh worktree 天然缺失；`git checkout HEAD~1` 后复跑同两规则，失败逐字一致），**零新增回归**，其余规则全过 |
| 状态 | **BLOCKED**（卡点=子 Agent 运行时拒绝浏览器/桌面自动化通道，需主 Agent 或用户侧解锁） |
