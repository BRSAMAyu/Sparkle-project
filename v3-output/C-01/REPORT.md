# C-01 REPORT · DecisionContext / ContextPack 契约冻结

- **Task**: C-01 · DecisionContext / ContextPack 契约冻结（stream CONTEXT, gate V3-2, risk high, reviewers=2, locks context-contract）
- **Status**: READY_FOR_REVIEW（未 commit；改动以 `changes.patch` 交付）
- **Base SHA**: `2f52a972`（worktree wt5）
- **工作树最终态**: 2 个修改文件 + 2 个新增文件，未 commit / 未 push

## 1. 问题定义

Aurora / Router / Planner 需要一个共同消费的"最小高信号决策上下文"。基线勘察结论：

| 现状 | 事实 |
|---|---|
| ContextPack（`backend/app/core/context_pack.py:1086`） | 唯一上下文契约，但 item 只有隐式 id，无 ref/scope/version/why_included 语义；`metadata["ranking"]` 只是 ranking 开启时的影子元数据，非冻结契约 |
| UserStateV1（`state_aggregator/schema.py:285`） | UserWorldSnapshot 权威（20 字段 envelope），但其决策关键信号（engagement/emotion/srl）**不在 ContextPack 里**，只经 ContextBuilderMixin 平行 dict 流动（B-06 D-CTX） |
| 决策侧真值 | event_store + decision_records（live 947 行）；TTL 唯一真源是 `StateAggregatorService.FIELD_TTLS_SECONDS` |

即：决策面消费方要么各自再查（重复装配），要么吃 prompt 面大 dict（无 provenance）。这正是卡要冻的缝。

## 2. 契约形态与关键设计决策

### 2.1 形态：extend ContextPack，不新建真源

新增模块 `backend/app/core/decision_context.py`（纯契约类型，只依赖 stdlib + `state_aggregator.schema`），`ContextPack` 增加一个可选尾字段：

```python
decision_context: DecisionContext | None = None
```

三个冻结 dataclass（schema_version = `decision_context.v1`）：

| dataclass | 字段（顺序冻结） |
|---|---|
| `ContextItemDescriptor` | ref / type / scope / why_included / ttl_seconds? / epoch? / relevance? / version |
| `DecisionStateSignal` | name / ref / value / why_included / ttl_seconds? / epoch? / computed_at? / freshness_seconds? / source_snapshot_ids / version |
| `DecisionContext` | user_id / intent / schema_version / route_intent / focus_mode / plan_id / query_text_hash / signals / items / omitted_counts(只读 Mapping) / degraded_fields / built_at |

每字段满足卡面要求 **ref/type/scope/ttl_or_epoch/version/why_included**：
- `ref`：真源 URI，封闭 scheme 集 `{memory, user_state, plan, document, profile}`，如 `memory://episodic/<uuid>`、`user_state://srl_phase`、`plan://<plan_id>`（id 可解析回 DB 记录）；
- `ttl_or_epoch`：契约规则"至少其一"（`validate()` 强校验）。signal 的 TTL 来自权威表 `FIELD_TTLS_SECONDS`，epoch=UserStateV1.schema_version；memory item 的 epoch=记录 updated_at/occurred_at ISO；
- `why_included`：封闭词表 10 个 reason code（rank_policy / evidence_order / budget_carryover / semantic_gate / focus_mode / plan_scope / state_signal / direct_request / diversity / fallback），builder 按真实选择链组装（如 `(rank_policy, focus_mode, semantic_gate, budget_carryover)`）；
- `omitted_counts`：候选→注入差值（CONTEXT_COMPILER_V3 §6 观测面）；`query_text_hash`：sha256[:16]，PII 最小化；
- `cache_key_components()`：落 CONTEXT_COMPILER_V3 §7 的 cache key 组件（user/decision-type/item_refs/epochs/query_hash），纠偏请求带新 hash 不得复用旧 cache。

### 2.2 备选方案与取舍

| 备选 | 结论 | 理由 |
|---|---|---|
| 新建 UserContextV3 aggregate | **否决** | 直接违反卡面 acceptance（不存在 parallel UserContextV3 真源）与 B-06 R2-C1 |
| signal 全量拷贝 UserStateV1 20 字段 | 否决 | 违反"最小高信号"；20 字段里大量与当轮决策无关；且会制造快照聚合漂移面。默认 3 字段（engagement_state/emotion_hint/srl_phase）= Router/Aurora 最小共同需要，且是确定性 DB 投影（无 LLM、无 sufficiency turn-parse 依赖） |
| DecisionContext 进 `to_prompt_context()` | 否决（刻意） | manifest 是观测/决策元数据不是 prompt 内容；进 prompt 会 token 膨胀并改变 5 个消费者行为。prompt 面集成留给 Context Compiler V3 实现卡，契约面已冻结 key 集 |
| proto 化（跨层） | 不需要 | 全仓证据：ContextPack 无 proto message、无 Go/Dart 引用（grep proto/ + gateway + mobile 为空）；Aurora/Router/Planner 全在 backend/app 进程内。按卡面"纯 Python 消费→契约快照测试防漂移"执行，proto 单一生成链零触碰 |
| item ref 用 pref_key 而非记录 id | 否决 | ref 必须可解析回权威记录（correction_actions/API 都以 memory id 寻址） |

### 2.3 信号投影 = 投影 + 指针，非新真源

`state_signal_from_envelope()` 只做 envelope→最小 value 投影（每字段冻结投影形状，如 engagement→{last_active_at, session_count_7d, streak}），TTL/epoch/`source_snapshot_ids`/`freshness_seconds` 原样携带，ref 指回 `user_state://<field>`。真源仍是 state_aggregator。

## 3. 消费方映射表

### 3.1 三个决策消费方（接入点已就绪，消费迁移属后续卡）

| 消费方 | 接入点 | 读什么 |
|---|---|---|
| Router（`orchestration/dual_core_router.py`） | `pack.decision_context.signals` + `intent/route_intent/focus_mode` | engagement（streak/session_count_7d）、emotion（dominant_sentiment/emotional_block_detected）、srl_phase——替代从 ContextBuilderMixin 平行 dict 二次取数 |
| Aurora（`app/aurora/*`） | `pack.decision_context.items` | ref/relevance/why_included 即 AURORA_V3 要求的 "relevant memories + provenance" 与 memory_use_receipts 的数据面；`refs()`/`items_of_type()` 直接可用 |
| Planner（`orchestration/plan_review_service.py` 等） | `pack.decision_context.items_in_scope("plan")` + plan ref | plan 链接 goal（scope=plan）+ `plan://<id>` item + omitted_counts（预算裁剪可见） |

### 3.2 现有 5 个 ContextPack 消费者（零破坏验证）

| 消费者 | 用法 | 兼容性 |
|---|---|---|
| `orchestration/context_focus.py:385` | builder.build() 后读 preferences/goals/… | 新字段可选默认 None；相关测试 `test_context_focusing.py` 21 项通过 |
| `orchestration/plan_review_service.py:2379` | `to_prompt_context()` | prompt 面 key 集冻结不变（契约测试断言） |
| `api/v1/chat.py:863` | `to_prompt_context()` | 同上 |
| `services/memory_eval_service.py:93` | 读 preferences/goals/episodic | 测试通过 |
| ContextPackRun 行级消费（budget_optimization / response_feedback / understanding_depth） | DB 表 | 零触碰（本卡不改 DB schema） |

## 4. Parity guard（验收项 1）

- **跨层 parity**：不适用（证据：§2.2 proto 取舍行）。全仓 grep 确认 Go/Dart/proto 无 ContextPack 引用。
- **纯 Python 契约快照**：`backend/tests/contract/test_decision_context_contract.py`（15 项）——
  - 三个 dataclass 字段名+顺序 == 契约常量，且 (name,type) 序列 sha256 == 测试内字面量（双重冻结）；
  - scope/ref-scheme/why/item-type 四个封闭词表精确集冻结；
  - ttl_or_epoch 规则、词表违规、ref 格式违规的 `validate()` 行为；
  - **ContextPack 向后兼容面**：旧签名可构造、`decision_context` 默认 None、`to_prompt_context()` 输出 key 集与旧完全一致（prompt 面零变化被测试钉死）；
  - 序列化 JSON-safe + omitted_counts 只读；
  - builder 填充：manifest 精确覆盖注入集合、signal TTL==FIELD_TTLS_SECONDS、聚合器故障降级（signals 空 + degraded_fields 登记、pack 不炸）、kill switch、goal→plan scope 规则、与 memory governance 共存。

## 5. 红绿纪律与测试证据

1. **RED**（先写测试）：`ModuleNotFoundError: No module named 'app.core.decision_context'`（2026-09-19 12:35 collection error，实跑记录）。
2. **GREEN**：实现后 `tests/contract/test_decision_context_contract.py` **15 passed**。
3. **回归**（定向串行，sqlite 内存库，未触碰 dev DB）：
   - `test_context_pack*.py` 6 文件 **12 passed**
   - `test_state_aggregator_service.py + test_aggregator_schema_v1_{5,10,11}.py` **16 passed**
   - `test_context_focusing.py + test_memory_eval_service.py` **21 passed**
   - lint：改动文件 ruff + black(120) 全通过（ruff --fix 仅排序/UTC 字面量归一）
   - 运行环境注记：worktree 无 venv，借用 `sparkle-cosmos/backend/.venv`（Python 3.11，依赖全匹配，`PYTHONDONTWRITEBYTECODE=1` 只读借用）；`backend/app/gen/` 为 gitignore 生成物，从主仓只读拷入 worktree 供测试。

## 6. 顺带修复与发现的既有缺陷（非本卡引入）

1. **修复**：`context_pack.py` telemetry 块把 `goal_scores`/`episodic_scores`（trim 结果 dict）就地遮蔽成 list——潜在变量遮蔽缺陷，本次以 `telemetry_*` 重命名根治（RED 调试时实锤命中）。
2. **记录不修**：`app.core.plan_context` ↔ `orchestration.prompts` 存在既有循环 import（`import app.core.plan_context` 单独即失败，与本次改动无关，正常入口顺序不受影响）——建议记入 KNOWN_CODE_DEBT_LEDGER 跟进。

## 7. 风险与边界

- **热路径成本**：默认 `ENABLE_DECISION_CONTEXT=True` 每次 build 增加 3 个聚合器字段读取（~6 条小索引查询 + kill-switch 读）。三层防护：总开关 settings、整段 try/except（失败→None 不阻断 pack）、逐字段降级（degraded_fields 登记）。与 `_build_stage33_working_memory_snapshot` 既有每轮 get_user_state 调用同量级，有先例。Reviewer 如有顾虑可改默认 False，契约不受影响。
- **默认信号集刻意不含 task/context_sufficiency**：二者依赖当轮 turn parse（pack build 无此输入，硬塞只会得到 0 分脏数据）；待 Planner 链路传入 turn parse 后按契约版本 bump 扩展。
- **document_chunk / event 类型在词表中预留但 builder 暂不产出**：RAG 材料注入位（紧邻 user 消息，f01f4ae8）与 event_store 决策引用属 Context Compiler V3 后续卡，契约不提前造假数据。
- **未做**：decision_context 落 ContextPackRun telemetry（存储面）、orchestrator 侧 ContextBuilderMixin 消费迁移——均为后续卡范围，本卡只冻契约。

## 8. 改动清单

```
新增  backend/app/core/decision_context.py          # 契约（3 dataclass + 词表 + 投影 + 校验）
新增  backend/tests/contract/test_decision_context_contract.py  # parity guard（15 项）
修改  backend/app/core/context_pack.py              # ContextPack.decision_context 字段 + builder 填充 + telemetry 遮蔽修复
修改  backend/app/config/settings.py                # ENABLE_DECISION_CONTEXT 开关
产物  v3-output/C-01/REPORT.md + changes.patch
```

## 9. 收工清理

- 删除 `backend/app/gen/`（主仓拷贝的生成物）、`__pycache__`、`.pytest_cache`；无进程/模拟器/Gradle/浏览器；无 /tmp 产物；venv 借用未写入（PYTHONDONTWRITEBYTECODE）；未 commit/push。
