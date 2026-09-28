# WT798-E08SAMPLE notes — 实录

> 2026-09-28 ｜ worker wt798 ｜ worktree `Sparkle-sysrev/wt798-e08sample`（分支 `agent/node-b/wt798/e08sample`，base `7e50726b`）
> 任务：E-08 首帧重采——wt755（L0 首帧前移，集成 `0b063c7c`）滚动重启激活后，对活栈实测首帧改进，产出 E-08 收口核心证据。

## 时间线实录（+0800）

- ~09:31 领任务。`git log --oneline -2` 确认主仓 HEAD `7e50726b`（轮#295 J-02 销账 103/107+引擎滚动重启+wt798 重采补位）。
- 09:31 建 worktree。**首次误建**：cwd 重置致 `git worktree add` 落在 sparkle-cosmos 仓库（checkout 出 dc99118）——发现后即删该 worktree+分支，改用 `git -C` 显式重建，得 7e50726b。教训实录：本环境每次 Bash 调用间 cwd 复位，仓库操作必须显式 `-C`。
- 09:32 活栈体检：:50051/:8000 活且 healthy；**:8080 拒连**。取证：`/tmp/gateway_day7.log` 尾部 09:29:09 `Server exited gracefully`（滚动重启流程关掉网关未重启）；wt792 08:23 preflight 时网关还 healthy（uptime 48m）。按硬约束**立即停手披露**并报主会话（不自行拉起）。
- ~09:36 主会话批复：①引擎直连口径（wt372 同构）正确继续；②网关已由主会话 09:37 复原（根因=引擎重启触发 workers 优雅退出+启动 CWD 相对路径，登记 FIX-542）；③采样窗口内 :50051/:8000 异常即停。
- 09:35-09:40 方案定型：引擎有真实 key（.env 键名在、值非空，未打印值）且非 demo_mode → 普通请求会打真模型，keyless 臂改取「>2000 字符校验确定性拒收」——ack 发出点与正常请求同构（wt755 新序：锚定→run_started→ack→drain→校验），LLM 零消耗。读 `validator.py` MAX_MESSAGE_LENGTH、`orchestrator.py` `_emit_early_ack_progress`（stage=intake、early_ack=true）、wt755 钉测、wt372 harness 口径后写探针 `scripts/devtools/probe_first_frame_wt798.py`。
- 09:42 冒烟 2 样本：首帧即 intake early_ack（9.2/33.5ms）→ INVALID_ARGUMENT 终帧，零 LLM。修一个枚举引用（pb2.FinishReason 顶层非嵌套）。
- 09:42:40-09:43:04 **run1**（guest `wt798_e08_guest`，n=24）：t_ack p50 29.6ms/p95 36.7ms/max 37.9ms；24/24 首帧=intake early_ack、次帧=ERROR；引擎日志窗内 `Validation failed` 恰 24 行 1:1。
- 09:44:10 次序单点实录（`evidence/wt798_ordering_check.json`）：客户端 ack 墙钟 09:44:10.232 vs 引擎校验日志 09:44:10.232——**毫秒粒度不可分辨**（gap −0.2ms），严格次序改以流内帧序（生成器先 yield ack 后执行校验）+钉测事件序为准，如实记两处。
- 09:44:49 **run2**（新 guest `wt798_e08_guest_b`，n=12）：p50 25.7ms/p95 30.0ms/max 31.9ms——用户无关性成立。
- 09:45 **key 探测**：wt372 harness `--limit 2 --layers L0 --tag wt798keyprobe` → 2/2 成功（err=False，真响应 160/253 字符）→ **本机 key 有效**（推翻任务预设的 BLOCKED-on-keys）。
- 09:45-09:49 真模型小臂 L0×5（tag wt798e08postL0）+ L1×5（wt798e08postL1）：全成功；TTFT 0.66-0.91s（L0）/1.24-2.72s（L1）；DB 归因 10/10 dashscope_fast。intake 到达 L0 p50 14.2ms / L1 p50 18.1ms。L0-05 一条 total 21.1s 离群（113 字符响应，疑拥塞窗）——如实记录不占号。
- 09:50-09:55 并置分析（对 wt372 raw.jsonl 103 条 t_first_stage_s + 104 条 t_first_event_s 逐条复算）→ 撰 report.md → commit。

## 决策与偏差登记

- **口径**：引擎直连（主会话批复）；网关 :8080 透传不进口径（与 wt372 报告口径注记一致，网关当时也尚未复原）。
- **keyless 臂形态**：任务原话是「demo/mock 路径」；实测引擎持有效 key、非 demo_mode，走 demo 会失真或需改栈配置（禁止）。改取校验拒收臂——ack 路径与正常请求完全同构且零 LLM，达成任务意图（「ack 路径在 LLM 之前，keyless 可测」）。
- **真模型臂超出预设**：任务预设无 key→BLOCKED；实测 key 有效，故做了 n=12 小臂作为「key 有效」的直接证据，并把验收级复测从 BLOCKED 改判「本机可执行」（命令包在 report §5）。n=12 不冒充卡面 ≥100 验收。
- 测试用户：新建 guest×3（wt798_e08_guest/_b/_ordering）+ 复用 wt372 bench guest（同账号利于同 query 对照）；**未触碰 ns001**，未读 `/tmp/northstar_ns001_real_drive_state.json`。
- 活栈：全程只消费，零重启零改动；引擎 PID 68807/68827 采样前后一致。

## 缺陷/新发现登记

- **无新缺陷占号**。下一空闲号经 grep 复核为 **V3-FIX-543**（540/541/542 已占用；542=网关事件，主会话登记）。以下两条为观察项，不足以立缺陷号，留档：
  1. L0-05 total 21.1s 离群（113 字符响应）——与 wt755 notes 描述的事件循环拥塞形状吻合，待验收级 bench 重采核账（若复现，归 L3 拥塞治理勘察项）。
  2. harness enrich 的 DB 归因在流结束后立取可能滞后（keyprobe 1/2 attributed；后续两批均 5/5）——wt372 既有 harness 行为，非本改引入。
- 任务执行瑕疵自曝：worktree 首次误建到 sparkle-cosmos（已删净，无残留对象；`git worktree list` 已核）。

## 产物清单

- `report.md` — 数字表+结论+E-08 收口建议（主交付）
- `evidence/ack_24s_run1/`（raw.jsonl+summary.json+server_validation_log_lines.json）
- `evidence/ack_12s_run2_guestB/`（同构）
- `evidence/keyprobe/raw-wt798keyprobe.jsonl`、`raw-wt798e08postL0.jsonl`、`raw-wt798e08postL1.jsonl`
- `evidence/wt798_ordering_check.json`
- `scripts/devtools/probe_first_frame_wt798.py`（可复跑探针，复测命令包之一）
- 未改台账/tasks.json/运行栈；未 push。
