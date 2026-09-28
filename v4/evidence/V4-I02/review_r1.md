# V4-I02 · 独立审查 receipt（一审 R1）

- 审查会话：wtI02R1（未参与 I02 实现）
- 对象：`agent/v4/i02` @ `fed88d6f`（feat(v4): I02 合法历史的效用筛选与反向迁移抑制）
- 审查方式：只读 + 受影响面复跑 + 对抗探针（本 receipt 新增代码仅探针脚本，未改实现）
- 日期：2026-09-28

## 总裁决：**CHALLENGED**（1 项实质挑战；其余审查点通过）

---

## 逐点结论

### 1. 负迁移抑制真实性（FIX52 双层语义等价）——**FAIL，实质 CHALLENGE-1**

审查指令：构造带异类型失败经验的历史走**集成面**（context_pack 真实调用形态），验证被拒或被打到阈下；拦不住 = 实质 CHALLENGE。实测拦不住（部分现实构造下）。

事实链：

- `context_pack.build`（`backend/app/core/context_pack.py:1584`）调用 `apply_history_utility_gate(ranked_episodic, query_text=..., top_k=...)`，**未传 `current_type_anchors`**（默认 `frozenset()`）。
- 硬门条件（`memory_utility_gate.py:364-370`）含 `bool(current_type_anchors)` → 集成面恒 False → **`negative_transfer_cross_type` 硬拒在集成面对任何输入都不可能触发**。FIX52 语义在 flag on 后唯一生效面（pack）上不存在。
- 集成面只剩软路径：`unresolved_episode -1.0 + confirmed_bonus +0.3 + relevance`。当词法相关 ≥ 0.7 时失败经验回到阈上。

R1 探针实测（同 commit 代码，`apply_history_utility_gate` 不传锚 = context_pack 形态）：

| 构造 | relevance | 单测面（带锚 math_practice） | 集成面（不传锚，真实形态） |
|---|---|---|---|
| 异类型失败 `task_type:essay_writing`，content 与 query 覆盖 6/8 项 | 0.75 | 硬拒 `negative_transfer_cross_type`（score +0.04） | **SELECTED，score=+0.04，进 pack/prompt** |
| 极端：relevance=1.0 异类型失败 | 1.00 | 硬拒（score +0.2925） | **SELECTED，score=+0.2925** |
| 低相关异类型失败（wiring fixture 同款） | ≈0.11 | 硬拒（score -0.71） | 拒（`utility_low_score`，score=-0.71） |

即：软路径只拦**低词法相关**的异类型失败。FIX52 的靶害恰是经由泛词汇（任务/练习/计划/进度）的跨类型虚假迁移——现实可构造，非刁钻案例。

**挑战定性**：
- 卡验收①「FIX52异类型失败不拉向skill/difficulty」在集成面不成立（仅单测面成立）。
- `limitations.md` #2 已披露「集成面 `current_type_anchors` 恒为空」，方向诚实；但断言「pack 集成层：异类型失败**仍被抑制**，但走的是软路径」**失实**——抑制是条件性的（低相关才被压下），本探针证伪其全称表述。`diff_or_evidence_only.md` 验收①「集成面 …证明污染条目不进 pack」同样只在低相关 fixture 上成立。
- 缓解（降风险但不撤销挑战）：旗标默认关（当前零生产影响）；`current_type_anchors` 参数挂点已在，后续卡可补。

**整改要求（Leader 裁决，二选一或等效）**：
- (a) 集成面补类型锚派生（从 plan/route_intent 取当次 task_type/domain 传入），使硬门在集成面生效 + 补高相关异类型失败的集成回归测——真正满足验收①；
- (b) 若维持卡边界「不越界猜类型」：勘误 limitations #2 与 diff_or_evidence_only 验收①表述（"集成面仅低相关软抑制，FIX52 硬语义集成面未生效"），登记为已知未决并挂后续卡，不得以现状宣称验收①通过。

### 2. B03 冻结权重对表——**PASS**

`FROZEN_OUTCOME_WEIGHTS` 与 `v4/evidence/V4-B03/frozen_utility.json` → `utility_frozen.weights` 逐项一致（5/5）：`resolved_episode 1.0 / unresolved_episode -1.0 / wrong_followed_decision -0.4 / question -0.15 / control_intrusion -0.6`。本审直接对读两文件核实（非仅依赖锚测试）；锚测试 `test_frozen_outcome_weights_match_b03_freeze` 存在且直读 JSON 断言全等（改动即红）。

### 3. 零复活/子集约束与 bypass 登记语义——**PASS**

- 选择集 ⊆ 输入集：`evaluate_history_utility` 的 `selected_ids` 仅从输入 features 派生，decisions 覆盖每条输入恰好一次；`apply_history_utility_gate` 的 `kept` 是对输入 `ranked_items` 的过滤（列表推导），无任何外加 id 路径。集成面 bypass 回退的 `_pre_gate_episodic = list(ranked_episodic)` 是 **M-03 预筛后**列表——非法条目在门上游已被砍，bypass 不构成复活。
- bypass 非静默：`passed=False` 时恢复预筛后全量 + `bypassed=True` + `verdict="required_memory_recall_miss_bypass"` + Prometheus 计数（outcome=bypassed）+ metadata 落 pack，wiring 测试断言 `required_memory_recall=False` 如实登记。miss 不被包装成通过（`evidence_verdict` 亦保持 NOT_RUN）。
- 非 required 场景空选择 → `passed=True` + verdict `all_rejected`（设计如此，宁缺勿假），有单测钉住。

### 4. 默认关零行为变化——**PASS**

- `context_pack.py` 中 gate 相关引用**全部**位于 `if settings.ENABLE_MEMORY_UTILITY_GATE:` 单一块内（本审 grep 全文：1580–1605 行，无块外引用）；import 为块内惰性。
- `settings.ENABLE_MEMORY_UTILITY_GATE` 默认 `False`；flag off 时不调用、无 metadata、无指标增量。`test_flag_off_default_keeps_v3_behavior` 断言无 `memory_utility_gate` metadata 且候选原样进 pack。
- 其余变更（settings +9、business_metrics +11 计数器注册）在 flag off 时均为惰性/无行为。

### 5. 复跑测试——**PASS**

| 模块 | 结果 |
|---|---|
| `tests/unit/test_memory_utility_gate.py` | 20 passed |
| `tests/unit/test_memory_utility_gate_wiring.py` | 5 passed |
| `tests/unit/test_memory_retrieval_prefilter.py`（抽样受影响面） | 61 passed |
| `tests/unit/test_context_pack.py`（直接消费面） | 7 passed |

环境：`SECRET_KEY=x`，主检出 `backend/.venv`（对齐 run_manifest 声明），worktree `wtI02` @ fed88d6f。全绿，与 run_manifest/test_results.json 记录一致。（mypy 棘轮、86 守卫未复跑——超出本审抽样范围，非背书项。）

### 6. limitations 定性如实性——**大体如实，#2 部分失实（见 CHALLENGE-1）**

- #1（resolved 正例被 M-03/M-01 上游剔除 → `+1.0` 权重在 pack 面为潜在）：**经代码佐证**——`memory_retrieval_prefilter._reject_status` 对非 ACTIVE 一律拒（`status:resolved`），resolved 行到不了门。诚实且重要。
- #2：方向诚实（披露锚未接线），但「异类型失败仍被抑制」为全称表述，被本审探针证伪（高相关异类型失败阈上入选）。失实部分即 CHALLENGE-1 本体。
- #3（marker tag 无写入方 → 后三项权重当前为 0）、#4（bypass 不是注入好历史，该轮污染仍在）、#5（无伪 precision）、#6（权重为冻结初值非最优）、#7（worktree 环境事实）、#8（未审查≠通过）：均如实，无掩盖。

---

## 次要观察（不构成挑战）

- O1：`apply_history_utility_gate` 主体无 fail-soft 包裹（`ensure_naive_utc`/`int()` 对脏数据理论可抛）；M-03 式「metrics never break retrieval」容错只盖 metrics inc。flag on 面生效，建议后续卡补 try/except 降级为跳过门。
- O2：required-memory 词表较宽（"之前"/"记得"）→ 误判方向偏保守（更易触发 bypass 保召回），可接受。
- O3：`tasks.json` 状态 `REVIEW_READY` + `evidence_verdict=NOT_RUN`，与实际（待 2 审）一致，诚实。

## 结论

实现质量整体良好（冻结锚、子集约束、flag-off 等价、反 gaming 登记均扎实，测试可失败且真实），但 **FIX52 验收①在集成面不成立且 limitations #2 存在失实表述**，按审查指令判 **CHALLENGED**。整改路径 (a)/(b) 由 Leader 裁决后销账；二审需复核整改面 + 本探针场景回归。

- 审查人：wtI02R1（独立，未参与实现）
- 本 receipt 落盘即登记；不 push，由 Leader 流程收口。
