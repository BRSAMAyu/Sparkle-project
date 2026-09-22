# BP-3B · 含规划词汇的纠正请求被规划澄清快速通道劫持——修复报告

- 任务卡：BP-3B（P1-3 复盘立卡：纠正请求被 `_check_sufficiency` 规划澄清快速通道劫持）
- 工作树：wt105（wt105-v3，基于 main@db9e9fd8）
- 结论先行：**劫持是判定序问题，不是能力缺失**——影子意图预测对「复习/总结」词面的
  规划判定，压过了用户明示的纠正/指错信号。修复以最小侵入改判定序（纠正信号原语 +
  意图归一化降级 + 消息级规划回退压制），sufficiency 通道本身零重构。真栈 RED→GREEN
  双向实证：同一句纠正，修复前被单帧澄清吞掉，修复后获得完整知识应答。
- 交付物：`changes.patch`（2 个产品文件 + 1 个测试文件，+323/−3）、
  `evidence/live-red-probe.json`、`evidence/live-green-probe.json`、本报告。

---

## 1. 劫持机制（一句）

`predict_intent_only` 的关键词分类把「我要复习这块」归为 `time_planning`
（planning_keywords 含「复习」，且纠正消息不含知识问法词面）→
`_check_sufficiency`（validation_engine.py:234-357）按规划意图走澄清快速通道：
`_check_phase_a_planning_preflight` 的 `detect_planning_like_turn` 命中或
sufficiency 的 LLM 精化判「信息不足」→ `_emit_fast_interaction` 单帧 full_text+STOP
返回「先判断对错还是安排复习？」——纠正内容从未送达知识应答链路。

证据对照（P1-3 复盘 + 本卡复测）：纯知识问法（去掉规划词、语义不变）纠正完整送达，
**纠正能力一直存在，劫持纯由措辞/意图判定驱动**。

## 2. 修法（判定序，最小侵入）

核心原则：**用户明示纠正/指错的优先级高于规划词汇触发**；结构性规划信号
（分类器意图、route_intent、Phase A 会话态）不受纠正词面改写。

1. `app/orchestration/planning_intent.py`
   - 新增纠正信号原语 `has_correction_signal()`：`你说错了/说错了/你错了/你搞错了/
     搞错了/不对/纠正/更正/其实是`（「不对」用负向断言 `(?<!对)` 排除「对不对」求确认句式）。
   - `detect_planning_like_turn` 的 **message_fallback 分支**：消息含纠正信号时压制词面
     规划回退（「复习计划」等词面不再把指错消息判成规划回合）。normalized_intent /
     route_intent / decision_context 三条结构性分支保持原样。
2. `app/orchestration/validation_engine.py::_normalize_sufficiency_intent_type`
   - 归一化降级条件并入纠正信号：`create_plan/time_planning` + 纠正信号
     → `knowledge_query`；**保留 explicit_plan_markers 逃生口**——用户同时明确要求出计划
     （「帮我重新制定复习计划」等）时维持规划意图，真规划请求的澄清体验不回退。

修后链路（对应事故消息）：predict `time_planning`（复习词面）→ 归一化降级
`knowledge_query` → preflight 判定非规划回合 → sufficiency 走 knowledge_query
（required=query 满足，SUFFICIENT，不触发 LLM 精化）→ 返回 `(False, "knowledge_query")`
→ 流式继续，纠正送达知识应答。

**未触碰面**：sufficiency 通道结构、clarification/confirmation 帧协议、
`_emit_fast_interaction`、Phase A ask-before-plan 护栏本体、流式协议（帧形状零改动）。

## 3. 红→绿统计

红测试：`backend/tests/orchestration/test_correction_priority_over_planning.py`
（294 行，7 项；真实 `_check_sufficiency` 判定链 + 确定性 LLM 桩 +
`predict_intent_only` 启发式 + 生产形状 situation_brief payload，DB/网络零依赖）。

| 测试 | 修复前 | 修复后 |
|---|---|---|
| 纯知识纠正 → 知识应答路径（对照） | PASS | PASS |
| **含规划词纠正 → 知识应答路径（核心红）** | **FAIL**（被短路为 time_planning 澄清帧） | PASS |
| 纯规划请求 → 仍触发规划澄清（红线） | PASS | PASS |
| Phase A ask 硬停对真规划回合保持原样（红线） | PASS | PASS |
| 纠正信号原语词面覆盖 | FAIL（原语不存在） | PASS |
| detect_planning_like_turn 判定序 | FAIL | PASS |
| 归一化降级 + explicit_plan 逃生口 + advisory 兼容 | FAIL | PASS |
| **合计** | **4 failed / 3 passed** | **7 passed** |

回归（关键面，绝对路径 pytest，`SECRET_KEY=test python3.11 -m pytest`）：

| 套件 | HEAD 基线（/tmp 干净克隆） | 修复后 | 判定 |
|---|---|---|---|
| `tests/orchestration/` 全目录 | 36 failed, 26 errors, 146 passed | 36 failed, 26 errors, **153 passed** | 失败/错误集与基线**逐项 diff 为空**；+7 passed 即新增测试 |
| `tests/unit/orchestrator/` + orchestrator_simple + done_tail_latency + generation_routing + insight_gap_detector | — | **160 passed** | 全绿 |
| `tests/integration/test_phase5_orchestrator_north_star_acceptance.py` + 3 个 context 套件 | 116 passed, 1 skipped | **116 passed, 1 skipped** | 与基线一致 |
| ruff / black(120) | — | 全部通过（validation_engine 仅余基线即存在的 7 处 black 历史 hunks，未动） | 零新增违规 |

说明：`tests/orchestration/` 的 36F/26E 为本 worktree 既有环境缺口（与 P1-3 报告记录
一致），本改动零新增、零掩盖。环境缺口处理：`backend/app/gen` 从主仓拷贝
（gitignored 构建产物，不入 patch）。

## 4. 真栈验证（可选档，实际做满：RED + GREEN 双向）

账号 `northstar_bp3b_a`（本卡新建）；消息逐字使用 P1-3 事故句；评测驱动用 P1-3 修复版
`real_drive.py`（request_id 归因 + 残帧排干，全程 stale_frames_drained=0）。

**RED（共享栈：gateway :8080 → 主仓引擎 :50051，main@e43fde1e，未含修复）**：

- 事故句 → 27.76s 返回**单帧 full_text**：「已收到您的指正，正在为您同步更新复习方案。
  ……需跟您确认：您计划复习这块内容多久？目前更倾向于先梳理核心概念，还是直接通过刷题
  巩固？」——事件形状 `status_update×2 + metadata×2 + full_text×1`，即
  `_check_sufficiency` 短路签名；**纠正内容未被回答**。劫持在真栈复现。
- 规划控制句 → 同形澄清帧（快速通道工作正常）。

**GREEN（worktree 引擎 :50061，main@db9e9fd8 + 本修复，gRPC 直连 s2s 内部密钥鉴权）**：

- 同一事故句 → **21 个 delta + 终局 full_text 的完整知识应答**：「你指出的完全正确。
  ……**偶数度确实不保证图是连通的**。……画两个完全独立的三角形……」（并顺势照顾复习
  诉求给出复习边界清单）；`requires_clarification=false`、无 phase_a 标记、非单帧澄清。
- 规划控制句 → 仍为 `requires_clarification=true` 单帧澄清——**快速通道既有价值在
  修复后引擎上原样保留**。

成本：全程 LLM 消耗约 6 次调用（远低于 $0.2 护栏）。证据帧级 JSON：
`evidence/live-red-probe.json`、`evidence/live-green-probe.json`。

## 5. 红线面核查

- **快速通道既有价值**：纯规划请求澄清（pytest + 真栈双向）、Phase A ask 硬停
  （pytest）全绿；orchestration 失败集与 HEAD 逐项一致——零回退。
- **chat 流式协议**：帧形状/终止语义零改动（修复仅改判定优先序，见 patch）。
- **冲突面**：无并行卡触碰 orchestration/validation（树内改动仅本卡 3 文件）。

## 6. 新发现（超出本卡范围，建议立卡）

1. **P2 · preflight NoneType 崩溃静默杀死 sufficiency 检查**：
   `validation_engine.py:429-431`——当 situation_brief 的 `insight_state.contradiction_map`
   为 None 时 `for item in contradiction_map` 抛 TypeError，被 `_check_sufficiency`
   的 try/except 吞掉后**整个 sufficiency 检查（含澄清）被跳过**，流照常继续。
   深远影响：某些会话态下规划澄清会「无声消失」。本卡未动（修它会改变行为面，
   与「不重构 sufficiency 通道」约束冲突），仅留痕。
2. **P3 · 会话态残留的 Phase A 劫持**：`_check_phase_a_planning_preflight` 的
   decision_context 分支（残留 `planning_readiness_action=ask`）不属词面劫持，本卡
   判定序未覆盖——活跃规划会话中的纠正句仍可能被 ask 硬停。按卡约束保留（结构性
   信号不改写），GP-07 重测若在长规划会话内取样需注意此路径。
3. 环境注记：本 worktree `backend/app/gen` 为预置缺口，已从主仓拷贝补齐（不入 patch）。

## 7. 收工核查声明

- 已停掉自起进程：worktree 引擎（:50061，pid 88975）已杀净；未起模拟器/浏览器/Gradle。
- 已删 `/tmp` 产物：`bp3b_live_red.py`、`bp3b_live_green.py`、`bp3b_engine.log`、
  `bp3b-baseline/`（基线克隆）、`bp3b_baseline.txt`/`bp3b_postfix*.txt`。
- 主仓（Sparkle-project）零写入（仅读 .env 变量名与 gen 产物拷贝源）；改动全部在
  wt105 树内；未 commit / 未 push。
- 测试账号 `northstar_bp3b_a` 及其 4 条会话行留在共享开发库（沿用 P1-3 先例不做
  级联删除；按 username 前缀 `northstar_bp3b_` 可定位清理）。
- 产物清单：`v3-output/BP-3B/changes.patch`（apply 已在 HEAD 干净克隆上
  `git apply --check` 通过）、`evidence/live-red-probe.json`、
  `evidence/live-green-probe.json`、`REPORT.md`。
