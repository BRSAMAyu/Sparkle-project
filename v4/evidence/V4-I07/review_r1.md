# V4-I07 · 独立审查 R1 receipt（wtI07R1）

- 审查会话：wtI07R1（未参与 I07 实现，独立会话）
- 审查对象：branch `agent/v4/i07` @ `c4da470e`，base `1063abb3`
- 卡：`v4/04_tasks/cards/V4-I07.md`（implementation · high · 双审）；本 receipt 为 r1，r2 待另一位
- 方法：只读审查 + 独立复跑 + 两处独立 mutation 实证；未 push
- **总裁决：PASS_WITH_CHALLENGES**（验收①②③机制经独立实证成立；4 项挑战成立需跟进，见 §D；不构成拒收——核心门/红化/脚手架语义与接线真实）

---

## A. 复跑结果（本会话独立执行，非转录）

| 面 | 命令（`cd backend && SECRET_KEY=ci-test-key DATABASE_URL=sqlite://` 前缀） | 结果 |
|---|---|---|
| 新增验收面 | `.venv/bin/python -m pytest tests/unit/test_hybrid_policy.py -q` | **29 passed** in 11.36s |
| X-02 面 | `… tests/unit/test_action_allocation_policy.py tests/unit/test_action_allocation_guard.py tests/unit/test_action_allocation_eval.py -q` | **112 passed** in 1.03s |
| contract 全量 | `… -m pytest tests/contract -q` | **352 passed** in 11.86s |
| chat 面 | `… tests/api/test_chat_legacy_user_context.py tests/unit/test_v3_fix53… tests/unit/test_v3_fix57… tests/unit/test_v3_fix166… -q` | **21 passed** in 22.24s |
| mypy | `… -m mypy app/core/hybrid_policy.py app/services/action_allocation_policy.py app/services/task_service.py app/api/v1/chat.py` | Found 30 errors in 30 files——grep 归因 `hybrid_policy` = **0**；与 base 基线 30 一致（零新增成立） |
| ruff | `-m ruff check`（6 改动文件） | All checks passed |
| black | `-m black --check --line-length 120`（5 文件，task_service.py 按登记排除） | 5 files unchanged |

与 run_manifest.json 申报完全一致，无虚报。

## B. 独立 mutation 实证（接线级 RED 复核，任务书第 7 项）

1. **门 mutation**：`task_service.py` 结算门条件改 `if False and settlement is not None and not settlement.allowed:` →
   `pytest tests/unit/test_hybrid_policy.py::test_complete_by_agent_does_not_settle_sprint_mastery` → **FAILED (1 failed)**；
   `git checkout --` 还原后 29 全绿。证实该测试真实钉住 service 接线（非仅纯函数自测），实现方 stash 回退 RED 声明属实。
2. **C2 漂移探针**（本审查追加）：`hybrid_policy._X02_ALIGNED_LEARNING_TASK_TYPES` 删除 `REFLECTION` 成员 →
   **29/29 仍全绿**（含 `test_derive_goal_purpose_matches_x02_learning_types`）。详见 C2 判定。

两处 mutation 均已还原，工作树 clean。

## C. 预登记挑战点 C1-C6 逐判

### C1 结算门覆盖完整性 —— 挑战成立（undeclared 残面），核心声明部分成立

全仓扫描面（证据）：`update_node_mastery` 全部 16 个 app 调用点、`spark_node` 全部 9 个调用点、`mastery_audit_log` 写点、galaxy API/gRPC 入口、aurora runtime、celery、focus、error_book sync、community bridge、exam sprint review/diagnostic、event_listener、feedback_service、`galaxy/stats_service`（spark 活动面）。

- **声明「完成→人类掌握结算面只有 sprint pack 一处」**：就 `TaskService.complete` 结算级写面（`_update_sprint_pack_mastery_for_completed_task`，+25，reason=sprint_task_completed）而言**成立**；agent 委托路径（`ExecutionIngestor._complete_task_safely`）绕过 `complete()` 且零掌握写——limitations §2 该句经核属实。
- **spark 活动面自认不在门内——如实性：属实，风险定级：低-中**。同一 `complete()` 流程内 `spark_node`（`task_service.py:773-813`）先于门（:826）无条件执行：agent 完成的 learning 任务仍走 legacy 时间公式涨 `mastery_score`。但 `LEGACY_TIME_MASTERY_CAP=40.0` 封顶、audit 行 `effect_kind=PROJECTION`（"只留痕，重放跳过"）、`task_complete` ∈ NON_EVIDENCE_REASONS 永不清 legacy 旗、永不进证据账本（`galaxy/mastery_evidence.py:119` 及分类函数）——**呈现面有界冒充，非证据级冒充**。定级：低-中（可接受，建议 receipt 补一句边界数字 40）。
- **新发现（limitations 未登记）：aurora correct-answer 面是门外的第二 agent 可触发掌握写**。`aurora/runtime_v1/service.py:1561-1627`：agent LLM 自己的 `decision.state_updates.correct_answer_node`（decision_loop 提示词鼓励模型发出）→ 白名单 sprint 节点 `update_node_mastery(reason=aurora_completion_check_correct)`，每次 **+15 分**（0.15×100 标尺），无每节点次数上限。reason 不在 QUIZ/NON_EVIDENCE 词表 → 分类 None → projection（不进证据账本），但 mastery_score 直涨且判定者是模型本身（幻觉/自答回路即涨）。属**既有行为**（非 I07 引入），但 C1 的「只有一处」声明在无它的情况下不完整。跟进项 F1。

### C2 同集防漂移 —— 挑战成立（钉了一半，mutation 实证）

`test_derive_goal_purpose_matches_x02_learning_types` 首断言钉的是**字面集 ≡ X-02 `LEARNING_TASK_TYPES`**——X-02 侧改集会红（该方向真实）。但 hybrid 侧内部集 `_X02_ALIGNED_LEARNING_TASK_TYPES` 与 X-02 **无任何直接相等断言**，且用例缺 `derive(REFLECTION)` 逐成员例。本审查 mutation 删 `REFLECTION` 后 **29/29 全绿**（§B.2）：legacy REFLECTION 行将静默推导 mixed → agent 完成照常结算。「测试钉死防漂移」对 hybrid 侧**不成立**。ERROR_FIX∈mixed 合理（错题修复含准备/决策/执行/检验混合语义）。跟进项 F2（一行修复：断言 `derive` 内部集与 `LEARNING_TASK_TYPES` 逐成员相等，或补 REFLECTION 用例）。

### C3 反学习后门 —— 声明的攻击面关闭；相邻洞登记

`goal_purpose=deliverable` 写面普查：
- **API 面**：`TaskCreate.guide_json`/`TaskUpdate.guide_json`（schemas/task.py:224/278）接受任意 guide_json——user bearer 语义，即「用户选择交给 Sparkle」的合法声明通道；无出处标记（任何持 token 者可写），现信任模型下可接受，登记即可。
- **Agent 工具面**：`app/tools/task_tools.py` 的 `create_task`（:71-103 窄参映射，不含 guide_json）/`update_task_status`/`batch_create_tasks`/`suggest_quick_task`/`breakdown_task` 均不暴露 guide_json——agent 经由注册工具**无块写路径**（经 dynamic_tool_registry 包扫描确认在册）。
- **编排面**：planning_workflow/task_card_generator 逐字段构造 guide_json，无块透传；ExecutionIngestor 不触 guide_json。
- **守卫组合**（构造验证）：deliverable+human_required → 结算 BLOCK + G5（测试在）；deliverable+learning_goal/user_core → X-02 G1 仍守（代码路径+测试在）。mastery 目标 agent 完成 → BLOCK（mutation 证明接线真实）。
- **相邻洞（既有行为，登记）**：`update_task_status` 工具 `completed` 分支调 `TaskService.complete` **不传 evidence_source**（默认 `"user"`，task_tools.py:180）——生产 `complete()` 调用者只有 user/focus_auto，**门的 BLOCK 分支在当前生产面不可达**；agent 对话完成结算以 user 名义通过。验收①机制层成立，判别子未穿 chat 工具层。跟进项 F3。

### C4 红化绕过 —— 声明范围内核验通过；两处弱点登记

- **非 chat 模型可见入口普查**：`current_task` 上下文注入全仓仅 `chat.py:238` 一处（已门）；主线 `orchestration/context_builder.py` 不携带 guide_json（grep 0 命中）；`task_query_tool` 向模型只回 `guide_content` 等标量字段、不含 guide_json；entity_cards/state_aggregator/agents 无 guide_json。limitations §4 的「唯一模型可见入口就是 chat 注入（已门）」**核验属实**。
- **嵌套/列表**：`redact_independent_check` 深递归 dict/list，标记子树内嵌套答案键剥除（测试在）。
- **弱点 1（语义洞）**：封闭键集含 `solution` 却**保留 `solution_steps`**——仓内自家 fixture（test_hybrid_policy.py:330）的 `solution_steps=["展开到二阶","e^x 的导数恒为自身"]` 即解题实质，红化后随题面进上下文；测试还断言其保留。对验收③「答案不出现在上下文」构成构造性泄漏。跟进项 F4。
- **弱点 2（约定性）**：键集精确匹配大小写敏感（`Answer`/`answers`/`expected_answers` 逃逸），且未标记子树内同义键不动（opt-in 标记）——生产者纪律依赖，建议生产写面唯一化 + 探针进守卫。

### C5 脚手架语义 —— 通过

设计原文（EXPERIENCE_AND_LEARNING §学习目标：「只在用户选择且证据支持时推进；失败时增加局部支持，不把用户降级」）与转移表逐条对上：推进 ∧-门（两 HOLD 码）、示例充分渐隐（full→reduced→none 封顶）、尝试失败提示回升一档且 stage 不回退、independent_check 终态。脏状态 ValueError（parse 侧 fail-closed）。两处解释性收窄（渐隐仅示例段触发；attempt 段失败优先于推进选择）均偏保守，不违设计。MASTER_DESIGN「人必须完成理解/尝试/独立检验」由 human_required 门承载。

### C6 无第二真源 —— 通过，附版本兼容注记

`GOAL_PURPOSES` 全仓唯一定义于 `core/hybrid_policy.py`（allocation 处仅 docstring 提及）；X-02 import 消费（diff 在）；`ExecutionMode`/`CognitiveOwnership` 自 `app.models.task` import 不复制；orchestration 各处 "mastery" 用法为评分/关键词/提示词条目，非竞争词表。guide_json 策略块与 X-01 契约列分层无语义冲突（分配面 G1/G5 管可行性、结算门管结算，human_required 两面同向）。
注记：`schema_version` 不符时 `settlement_for_task_row` 静默降 legacy 推导（`_degrade` 原因被丢弃不落日志）——未来 v2 块携带的 human_required=true 会被 v1 读取方忽略（约束上 fail-open，方向与 legacy 一致）。建议登记：degrade 原因落 WARN + 未知版本从严。

## D. 挑战汇总与跟进项（不阻塞合入本卡，须销账前认领）

| # | 内容 | 来源 | 严重度 |
|---|---|---|---|
| F1 | aurora `_apply_correct_answer_mastery_update`（+15/次，模型自判，白名单 sprint 节点）为门外第二 agent 可触发掌握写；limitations 未登记。建议：进 limitations/已知债台账；中期把该写点纳入 `human_mastery_settlement` 或加每节点频次/证据门 | C1 新发现 | 中 |
| F2 | C2 防漂移测试未钉 hybrid 内部集（mutation 实证 REFLECTION 漂移全绿）；补集相等断言或 REFLECTION 逐成员用例 | C2 | 中（修复一行） |
| F3 | agent `update_task_status` 完成分支不传 evidence_source → 门在对话完成面不生效（生产 BLOCK 分支不可达）；穿参或门侧另判 | C3 相邻 | 中-高（既有行为） |
| F4 | 红化键集保留 `solution_steps`（内容即解题实质）且 fixture 断言保留；键集补齐或语义按值红化 | C4 | 中 |
| N1 | spark 活动面边界数字（cap 40/PROJECTION）建议补进 limitations §2 | C1 | 低 |
| N2 | schema_version 不符静默降 legacy：degrade 原因落日志 + 未知版本从严 | C6 | 低 |
| N3 | REST `/node/{id}/spark` 接受客户端自报 quiz 级 outcome（证据账本直写，G-01 既有面）；与直接 REST mastery 改分入口同属既有信任模型，登记备忘 | C1 | 备忘 |

## E. 合并落差（base 1063abb3 vs origin/main @ 71553984）

- base..main 全部为 mobile 面（S04 资产账本/F02 像素组件）+ tasks.json 状态行 + 证据 + guards 脚本；**与 I07 触及的 4 个 backend 文件零交集**（`git diff --name-only 1063abb3 origin/main -- backend/...` 空）。预测合并干净，唯一可能冲突点是两侧都改的 `v4/04_tasks/tasks.json`（不同条目状态行，行级可解）。
- I04 在 main 为 PENDING、无在航代码；I07 limitations §5 与移交节已把「脚手架推进对话流写点」划归 I04、把「新掌握写点必须过 settlement_for_task_row」划归 I08——划界清晰，合并时序无依赖。

## F. 裁决

**PASS_WITH_CHALLENGES**：三条验收的机制层（结算门/红化/脚手架转移 + 三处真实接线）经独立复跑与独立 mutation 实证成立，实现与证据五件套无虚报；F1-F4 跟进项成立但均属边界补强而非验收失效，须在销账（DONE_REVIEWED）前由实现/下游卡认领。r2 由第二位独立审查完成后按双审口径销账。

—— wtI07R1，2026-09-28
