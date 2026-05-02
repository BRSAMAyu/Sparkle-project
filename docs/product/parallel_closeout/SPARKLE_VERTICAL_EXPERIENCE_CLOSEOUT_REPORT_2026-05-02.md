# Sparkle Vertical Experience Closeout Report — 2026-05-02

## Scope

本轮不按 Aurora、Memory、Galaxy、RAG、Planning、Card Protocol 分模块继续打补丁，而是把它们收束成一条用户可感知的纵向体验主链：

用户提出目标 → 引用/上传资料 → Sparkle 选择 ContextPlan → source receipt/知识图谱进入判断 → Aurora 给出“我对你的理解” → 计划卡/任务卡/知识卡/来源卡统一流转 → 用户纠正或执行 → 后续回答、推荐、报告和分享能变聪明。

## Implemented Changes

### 1. Unified Experience Packets

新增 `backend/app/orchestration/experience_packets.py`，定义并构建以下 per-turn 聚合对象：

- `AuroraExperiencePacket`: 当前判断、证据、置信度、不确定性、开放问题、最近纠正、下一步语气与策略。
- `GoalRealizationContext`: 当前目标、计划健康、下一步动作、记忆声明、ContextPlan、Aurora packet、source receipt、graph trace、Card Protocol 覆盖范围。
- `KnowledgeSourceReceipt`: 检索模式、回答依据、加载/跳过/排除来源、来源不确定性和纠正提示。
- `GraphDecisionTrace`: graph 对下一步任务、RAG 范围、计划可行性和 Aurora 判断的影响痕迹。

这些对象不创建新的状态孤岛，只聚合已有 `user_context_payload`、document retrieval receipt、Aurora everyday presence、memory、learning gaps 和 graph entities。

### 2. Main Orchestration Path

`ChatOrchestrator` 在 document context hydration 之后调用 `attach_goal_realization_context()`，确保普通聊天主链在进入后续计划/执行/响应前已经拿到统一纵向上下文。

这避免了过去“资料、记忆、图谱、Aurora 各自存在，但一轮回答还是像普通聊天”的体验断裂。

### 3. Response Metadata Contract

`ResponseBuilderMixin` 现在输出：

- `goal_realization_context`
- `aurora_experience_packet`
- `knowledge_source_receipt`
- `graph_decision_trace`
- `goal_realization_summary`

移动端可以只消费统一 metadata，不必为每个来源单独猜测语义。

### 4. Card Protocol Coverage For Sources

新增 `build_source_document_entity_card()`，让 source tray / RAG 引用资料具备和 plan/task/knowledge/review/vocabulary/shared resource 一致的 Card Protocol 能力：

- 打开资料来源；
- 纠正来源；
- 转成知识点；
- 分享为 `source_document`；
- 接收方可保存为自己的资料副本；
- 保留 source receipt、context plan、confidence、linked knowledge node 等语义。

## Acceptance Against User Journey

| Journey segment | Status | Evidence |
|---|---|---|
| 每轮对话能引用 Aurora 当前理解 | Implemented | `AuroraExperiencePacket` 注入主链和 response metadata |
| 目标、计划、任务、资料、记忆、图谱统一进入同一上下文 | Implemented | `GoalRealizationContext` 聚合 active goal / next actions / memory claims / ContextPlan / source receipt / graph trace |
| RAG 不污染每轮上下文，必须说明使用模式 | Implemented | `KnowledgeSourceReceipt.context_plan_mode` 和 `answer_basis` 每轮输出 |
| Graph 参与下一步任务、RAG 范围、计划可行性、Aurora 判断 | Implemented | `GraphDecisionTrace.affects` 固定暴露四类影响面 |
| 资料来源也能成为通用卡片并可分享/纠正/转知识点 | Implemented | `source_document` entity card + validation coverage |
| 用户纠正能进入结构化后续变化 | Preserved and surfaced | 复用现有 Aurora correction / SGW closed loop；packet 中暴露 recent corrections 和 correction-derived memory claim |

## Verification

```bash
cd backend && .venv/bin/python -m py_compile \
  app/orchestration/experience_packets.py \
  app/orchestration/orchestrator.py \
  app/orchestration/response_builder.py \
  app/tools/entity_cards.py \
  tests/unit/test_goal_realization_experience_packets.py \
  tests/unit/test_entity_cards.py \
  tests/unit/orchestrator/mixins/test_response_builder_mixin.py
```

Result: PASS

```bash
cd backend && .venv/bin/python -m ruff check \
  app/orchestration/experience_packets.py \
  app/orchestration/orchestrator.py \
  app/orchestration/response_builder.py \
  app/tools/entity_cards.py \
  tests/unit/test_goal_realization_experience_packets.py \
  tests/unit/test_entity_cards.py \
  tests/unit/orchestrator/mixins/test_response_builder_mixin.py
```

Result: PASS

```bash
cd backend && .venv/bin/python -m pytest \
  tests/unit/test_goal_realization_experience_packets.py \
  tests/unit/test_entity_cards.py \
  tests/unit/orchestrator/mixins/test_response_builder_mixin.py -q
```

Result: `30 passed`

## Remaining Human QA

本轮完成后端主链和协议收束。最终上线前仍应进行一次移动端真机 E2E：

1. 零基础考试目标用户输入目标；
2. 上传或选择资料；
3. 查看聊天中 Aurora 理解、source tray 和 graph 影响提示；
4. 生成计划卡/任务卡/知识卡/来源卡；
5. 纠正一次误判；
6. 分享计划卡或来源卡给好友；
7. 接收方接受为私有副本；
8. 回到聊天确认后续推荐明显使用了纠正、资料和图谱。

## Boundary

本轮没有替换已有 Aurora、Spine、Memory、Galaxy、Card Protocol、Community Share 架构，也没有新增独立状态源。它的目标是把已有能力串成同一条主路径，并给移动端和审计系统一个统一、可验证、可纠正的 per-turn contract。
