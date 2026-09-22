# TTFT-PROBE：聊天首包 29-31s 簇根因调查与缓解（wt126）

> 2026-09-23 ｜ Worker: TTFT-PROBE ｜ worktree: `Sparkle-sysrev/wt126`
> 北极星基线：LOOP3 5 条实测 TTFT **12.2 / 28.8 / 30.1 / 30.6s**（3/4 聚在 29-31s 簇）
> 交付物：本报告 + `changes.patch` + `probe-runs/`（7 条逐帧时间线）+ `ttft_probe.py`（可复跑探针）

---

## 一、结论（TL;DR）

**30s 不花在网关、不花在编排前置的常规链路，花在两处：**

| 簇 | 构成 | 实测占比 |
|---|---|---|
| **簇 B：思考档 reasoning 时长（主害，占比 5/7）** | qwen3 混合模型流式下**默认先思考后作答**，`reasoning_content` 流 13-43s 后才出现首个可见 token；引擎把 reasoning 块**整段丢弃**，前端在 0.3s 收到一次静态"思考中"后陷入长静默 | M2=42.9s、M6=33.4s、M4=30.8s、V2C=28.8s、V2E=30.1s、M3=19.3s、M5=13.1s |
| **簇 A：规划意图轮的串行前置链（占比 4/12）** | `check_sufficiency`（LLM 3.2-19.2s）→ `check_goal_quality`（LLM 15.7-35.7s）→ `plan_and_validate`（**LangGraph planner 恒定 10s 超时后走兜底**）串行执行，全部发生在首个事件之前 | V1A=30.6s、M7=39.8s、V1B=19.4s、M1=11.6s、V2D=12.2s |

**分段实测（connect→ack ≈ 0.0s；gateway 纯透传无缓冲，附加 ≈ 0.02-0.35s；引擎前置 hops 除上表三项外全部 < 0.9s）。**

**定性裁决**：
- 簇 B 的**延迟本身是模型侧**（思考耗时无法压缩），但**暴露面是可修配置缺陷**：①qwen 车道默认思考未被显式关闭（`thinking_mode=None` 不发任何参数）；②思考控制参数疑似无效（发的是 GLM 风格 `thinking:{"type":…}`，DashScope 兼容模式期望 `enable_thinking`——推断，见 §4.3）；③reasoning 事件被丢弃导致 S18 假卡。
- 簇 A **纯属代码/配置可修**：10s 恒定超时税 + 无上界的串行 LLM 质量门 + 死代码 fast-track。

---

## 二、基线与复测采样（Worker 要素①）

### 2.1 本次复测（探针 wt126，注册新账号 `wt126_ttft_*`，7 条串行，2026-09-23 00:02-00:08）

| # | 消息类型 | 首事件(任意) | 首状态帧 | **TTFT(首 delta)** | 总墙钟 | delta 数 | 引擎 first_stream | 引擎分段（[LATENCY] hops） |
|---|---|---|---|---|---|---|---|---|
| M1 | 新会话·冲刺规划 | 0.000s | 11.31s | **11.57s** | 62.7s | 12 | 11.22s | build=0.7s + **plan=10.05s(超时)** + exec=51.3s |
| M2 | 同会话追问 | 0.000s | 0.42s | **42.93s** | 61.2s | 19 | 42.90s | 前置≈0.4s + exec=60.7s（纯思考） |
| M3 | 澄清类模糊提问 | 0.000s | 0.42s | **19.28s** | 39.9s | 28 | 19.25s | 前置≈0.35s + exec=39.4s（纯思考） |
| M4 | 新会话·知识讲解 | 0.000s | 0.33s | **30.84s** | 52.6s | 36 | 30.83s | 前置≈0.28s + exec=52.3s（纯思考） |
| M5 | 极简快问 | 0.000s | 0.48s | **13.14s** | 13.3s | 1 | 13.13s | 前置≈0.44s + exec=12.8s（思考后短答） |
| M6 | 同 M4 + `reasoning_mode=fast` | 0.000s | 0.29s | **33.45s** | 54.8s | 22 | 33.43s | 前置≈0.25s + exec=54.4s（**fast 档仍思考**，见 §4.2） |
| M7 | 新会话·冲刺规划（信息不足） | 0.000s | 39.79s | None（0 delta，full_text 直发） | 39.8s | 0 | 39.77s | **suff=3.99s + goal_quality=35.75s**（澄清门 full_text） |

数据文件：`probe-runs/M*.json`（逐帧时间线）+ `probe-runs/summary.json`。引擎侧日志：`/tmp/sparkle_grpc.log`（活栈当前落盘）。

### 2.2 LOOP3 原始 5 条（对照，来源主仓 evidence + /tmp/sparkle_engine.log）

| 消息 | 客户端 TTFT | 引擎 first_stream | 主要构成 |
|---|---|---|---|
| V1A 冲刺开场 | 30.64s | 30.27s | suff=3.19s + goal_quality=15.69s + **plan=10.05s(超时)** |
| V1B 澄清快交互 | —（0 delta） | 19.41s | **suff=19.16s**（单次 LLM 质量门） |
| V2C 追问 | 28.82s | 28.81s | 前置≈0.5s + exec=65.6s（纯思考） |
| V2D 纠错 | 12.20s | 12.18s | **plan=10.23s(超时)** + exec |
| V2E 污染探测 | 30.12s | 30.09s | 前置≈0.5s + exec=50.8s（纯思考） |

### 2.3 关键读数

1. **connect→首事件（任意类型）= 0.000s**：网关 ack 即时。首包体感损失 100% 发生在 ack 之后。
2. **首状态帧**：非规划轮 0.3-0.5s（THINKING 帧正常到达）——但之后是**一整段无帧静默**（M2 的最大帧间隙 42.1s）。S18"假卡"实锤：有反馈、无进度。
3. **规划轮首个状态帧被前置链吃掉**（M1=11.3s、M7=39.8s）：用户在收到任何帧之前就等了全程的 1/4～2/3。
4. 网关 `first_event_ms/first_token_ms` 透传指标与逐帧转发逻辑核实无缓冲（`chat_orchestrator_chatflow.go:735-886`，Recv 后立即写 WS）。

---

## 三、根因链（沿链路证据）

```
Flutter → /ws/chat(Go :8080) → gRPC StreamChat(:50051) → ChatOrchestrator.process_stream
  ├─ [簇 A] validation/lock → build_full_context(≤0.9s)
  │    → _check_sufficiency   —— LLM 调用，串行，无独立超时预算（3.2s / 19.2s / 35.8s 波动）
  │    → _check_goal_quality  —— LLM 调用，串行（15.7s / 35.8s）
  │    → _plan_and_validate   —— asyncio.wait_for(lang_graph_planner.plan, 10.0s)
  │         实测 3/3 规划轮全部打满 10.0s 超时 → "using synthesized fallback"
  │         （execution_engine.py:58 _LANGGRAPH_PLANNER_TIMEOUT_SECONDS=10.0，硬编码）
  │    ※ 本应秒开的 _fast_track_exam_sprint 是死代码（见 §4.1）
  ├─ [簇 B] execute_graph → generation_node → chat_stream_with_tools
  │    → dashscope_standard_thinking(qwen3.8-flash, thinking_mode="enabled"
  │      → wire: extra_body.thinking={"type":"enabled"}——GLM 风格参数)
  │    → 引擎日志：first_chunk_after 356-670ms (type=reasoning)
  │    → reasoning_content 持续 13-43s，期间块被 generation_node 丢弃
  │    → 首个 type=text 块 → FT-LAT-5 立即 flush → 客户端 TTFT
  └─ gateway 收到即转发，无缓冲
```

---

## 四、修复与缓解

### 4.1 【已修·代码】`asyncio.timeout` 误用导致规划快车道整体死亡

`orchestrator.py` 两处（`_attach_aurora_planning_sidecar` :456、`_fast_track_exam_sprint` :767）：

```python
# 修前：把 Timeout 上下文管理器当可调用对象 → 必然 TypeError → 被 except 吞掉
planning_response = await asyncio.timeout(30)(manager.process_planning_turn)(...)
# 修后：
async with asyncio.timeout(30):
    planning_response = await manager.process_planning_turn(...)
```

- **这是每次考试冲刺开场都 100% 命中的死代码**：活栈日志 23:26:12.614 `Exam sprint fast-track failed, continuing generic path: 'Timeout' object is not callable`——正是 LOOP3 V1A 跌入 29s 通用链的直接原因。
- **回归证据（单测级前后对比）**：`tests/orchestration/test_orchestrator_process_stream_integration.py` 修前 **6 failed / 19 passed** → 修后 **5 failed / 20 passed**，唯一差异 = `test_process_stream_modeling_complete_fast_track_returns_launch_route` 转绿；fast-track 测试推进到 DONE 态（剩余失败为陈旧期望，见 §6 诚实申报）。

### 4.2 【已修·代码】reasoning 进度帧（S18 缓解，等待面板心跳）

`standard_workflow.py generation_node`：reasoning 块不再整段丢弃，按 **3s 节流**下发 THINKING 状态帧（`"仍在深度思考中…（已思考 N 秒）"`），不透传思考正文，失败不阻断主链。新增单测 `tests/unit/test_generation_reasoning_progress.py` 3 条全绿（节流触发/窗口静默/失败兜底）。

> 效果定位：不缩短簇 B 的 13-43s（模型侧），但把"静默假卡"变成有节奏的进度反馈——DL-R1-AUDIT S18（"等待有反馈但不携带进度感"，chat 首流只配三点动画）的最大单点回收，与前端 wt123 的分期状态渲染对接即可。

### 4.3 【建议·配置级，未实现——需主会话/产品决策】

1. **qwen 车道思考控制参数疑似无效（簇 B 的真正开关）**：`llm_service.py:875-877,928-930` 对所有 provider 统一发 GLM 风格 `extra_body={"thinking":{"type":…}}`；DashScope 兼容模式的标准做法是 `enable_thinking: true/false`。**推断证据**：M6 显式 `reasoning_mode=fast` 成功把 generation 切到 `dashscope_fast`(qwen3.7-flash, `thinking_mode=None` 不发参数)，日志 `[LLMRouter] generation → qwen3.7-flash (强制tier=plus|free_tier_downgrade(plus->fast))`，但首块仍是 `type=reasoning`（356ms）且 TTFT=33.4s——**fast 档模型也在默认思考**，说明"不发参数=默认思考开"，而 `thinking:{}` 是否被 DashScope 接受存疑。**建议**：provider=DASHSCOPE 时改发 `enable_thinking`，然后把 fast/balanced 普通聊天显式关思考（预期簇 B 13-43s → ~1-3s，M6 首块 356ms 即到达证明链路本身很快）。风险：关闭思考影响回答深度，建议按 reasoning_mode 分档（fast=关、balanced=关或短思考、deep=开）。
2. **`_LANGGRAPH_PLANNER_TIMEOUT_SECONDS` 10s → 3s（或入 settings）**：样本内规划轮 3/3 全部打满 10s 超时走兜底——这是纯交税；提前 7s 失败到同一个 synthesized fallback，产物不变。
3. **前置质量门限界**：`check_goal_quality`/`check_sufficiency` 的 LLM 调用移入 FAST 车道并加 3-5s 预算（启发式兜底已存在：`GoalQualityEvaluator._heuristic_fallback`）。样本：M7 单次 goal_quality=35.8s、V1B suff=19.2s、V1A 15.7s——全部串行在首个事件之前。
4. **前端（wt123 对接）**：把 status_update 节奏渲染为分期进度（已收到→理解中→思考中(Ns)→生成中），静态三点动画是 S18 主害形态。

### 4.4 活栈验证交接

按红线未重启活栈，两处代码修复只做了单测/集成级验证。**主会话合入并重启引擎后复验方法**：`cd wt126 && /opt/homebrew/bin/python3.11 v3-output/TTFT-PROBE/ttft_probe.py /tmp/repro`（同剧本 7 条，自动注册新账号），对照本报告 §2.1 表——预期：M1/M7 类规划轮首帧从 11.3s/39.8s 显著前移；所有消息在等待期每 3s 收到 THINKING 进度帧；TTFT 数值本身待 §4.3-1 配置落地后才下降。

---

## 五、冲突面

在途卡 wt123（chat 面积重划，改 **mobile** chat UI）与本任务**零文件交集**：本任务只改 `backend/app/orchestration/orchestrator.py`、`backend/app/agents/standard_workflow.py`、`backend/tests/unit/test_generation_reasoning_progress.py`（新增）。§4.2 的进度帧是其 UI 渲染的数据来源，属对接关系非代码冲突。

---

## 六、诚实申报

1. **未做活栈级前后对比探针**：修复验证止于单测/集成测试（红线禁重启活栈）。§4.4 给了主会话复验剧本。changes.patch 的行为级效果（尤其 §4.3-1 参数修正未实施）在活栈上尚不可见。
2. **`thinking:{}` 参数对 DashScope 无效"是推断非实测**：依据是 wire 格式惯例 + M6 fast 档仍流 reasoning 的旁证；未直连 provider API 验证（避免用探针账号打真实计费请求做参数实验）。
3. **基线非全绿**：`tests/orchestration/` 在 HEAD 即有 **35 failed / 26 errors**（多代 stub 漂移：`_GraphStub.invoke` 不认 `resume_policy`、PlanningWorkflowManager DONE 态过滤 vs 旧测试期望等）。本修复后 **34 failed / 160 passed / 26 errors**，逐名 diff 确认唯一变化 = 修复目标测试转绿，零新增红。剩余 5 个 failed 与 26 errors 属存量债务，未越权清理。
4. **探针样本量**：7 条（任务要求 ≥6），单实例串行收发，非压测；M5/M3 单条样本，其数值波动未做重复测量。
5. `reasoning_mode=fast` 走 `extra_context` 传递，网关 `chatInput.ExtraContext` 透传已验证；但 **mobile 端目前并不发送该字段**（M6 是探针显式注入），前端快捷档位属 wt123 面积。

---

## 七、Worker 五要素

**① 基线证据**：§2.1 复测 7 条 + §2.2 LOOP3 对照，逐帧时间线在 `probe-runs/`；引擎 hops 与客户端时间线双向对齐（误差 0.02-0.35s = 网关转发+传输）。

**② 红线面**：未改 `.env`（worktree 无）；未重启活栈任何进程；DB 仅经 API 探针（账号注册/登录/WS 消息），无直连写库；主仓只读（日志/evidence 读取 + `gen/` 生成代码复制入 worktree，gen/ 在 .gitignore）；未 commit/push；探针单实例串行、无模拟器/浏览器。

**③ 冲突面**：与 wt123（mobile chat UI）零交集，见 §5。

**④ 诚实申报**：见 §6（活栈级对比缺失、参数推断性质、存量红测试、样本量、fast 档位前端未接入）。

**⑤ 收工核查**：
- 探针账号（`wt126_ttft_*` ×2：主跑 + 基线注册各一）数据**保留**——活栈 DB 本任务只读，账号系探针产物，留给主会话复验；
- /tmp 已清理：`/tmp/ttft_probe/`、`/tmp/wt126-baseline/`、`/tmp/base_fails.txt`、`/tmp/fix_fails.txt`；
- 无进程残留（探针已退出，未起任何服务/模拟器）；
- 交付物齐：`REPORT.md`（本文）+ `changes.patch`（新文件 diff 头 `--- /dev/null` 已自查，`git add -N` 后已 reset）+ `probe-runs/`（8 文件）+ `ttft_probe.py`。
