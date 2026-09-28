# V4-D05 · 独立审查 receipt（一审）

- 审查会话：wtD05R1（未参与实现；只读审查 + 本 receipt 落盘，未 push、未动实现 commit）
- 审查对象：`agent/v4/d05` 实现 `1e626998` + 状态/证据 `45a896f2`，基线 `90d8196a`；工作树干净（`git status` 空）
- 卡标准：`Sparkle-project/v4/04_tasks/tasks.json` `V4-D05` 全文（三验收 + D02-R1 C-3 notes）
- 裁决：**PASS_WITH_CHALLENGES**（三验收全过、证据数字全部独立复现；两条挑战登记为后续 owner 事项，不阻塞 REVIEW_READY）

---

## 1. 独立复现矩阵（本会话亲跑）

| 项 | 命令（wtD05/backend，进程级 SECRET_KEY，venv=Sparkle-project/backend/.venv） | 结果 | 与自述 |
|---|---|---|---|
| 新测 52 | `pytest tests/unit/test_insight_presentation.py tests/services/test_evidence_insight_presentation.py -q` | **52 passed**（15.30s） | 一致 |
| 回归面 | manifest 同款命令 `tests/core + 8 文件 --ignore=tests/core/test_bert_intent_classifier.py` | **597 passed, 1 skipped**（234.66s） | 一致 |
| mypy branch | `mypy app --ignore-missing-imports --no-error-summary \| grep 'error:' \| sort` | **59**；两新/改文件零错误（grep 计 0） | 一致 |
| mypy base | 临时 worktree @`90d8196a`（Sparkle-project 仓 add，gen/ 实体复制，用后已删） | **59**；`diff base branch` = **空（字节级同清单）** | 一致 |
| API/OpenAPI | `pytest tests/contract/test_api_router_openapi_contract.py tests/api/test_insights_evidence_cards_api.py -q` | **9 passed**（回归扫描清单外补跑） | 一致 |
| artifacts | `shasum -a 256` 五件套+3 代码文件 | 与 run_manifest.json `artifacts_sha256` **逐字节一致** | 一致 |

## 2. 预登记挑战 R-C1..R-C5 独立裁决

**R-C1 夸大门参数面 + user-content 豁免 — 裁决：豁免正确，无绕行。**
分子/分母按卡型取数与「关联」语义一致（friction=响应数/暴露数；helped=n_observed/n_exposed；goal=completed/total），anchor `evidence_insight_service.py::_card_linked_count/_card_denominator_count`。探针亲验（临时脚本，用后即删）：
- 用户 goal 标题 `背单词导致词汇量提升67%`（`fact.title`，非 SYSTEM_CLAIM_KEYS）→ **allowed**——按卡语义裁决为正确：系统引用用户自述目标标题是标识不是宣称，验收①约束的是系统组写面；
- 同文案放 `note` → rejected（`causal_assertion_detected`+`causal_percentage_claim`）；放 `claim` → rejected（M-06 通道）。系统组写自由文本不存在逃逸键：现行三卡型全部 prose 面要么不存在要么落在扫描键集内，数值面通道当前为纯防御纵深。
- 服务层门扣下分支（`meta.presentation_gate_dropped`）9 个服务测只测了正路——探针以 monkeypatch 注入违例卡亲验：卡被整体扣下、reasons 在册、不发出（见挑战 CH-2）。

**R-C2 样本身份 OCCURRENCE 命名空间 — 裁决：无碰撞，约定可接受。**
`presentation_sample_id` = D02 `derive_attribution_sample_id(domain=OCCURRENCE, anchor=decision_id, outcome_id)`（`attribution.py:243` 单一权威，测试 `test_sample_id_matches_d02_authority_and_is_replay_stable` 钉恒同）。D02 OCCURRENCE 域锚 = `occurrence_id`/`task_occurrence_id`（`attribution.py:147`），canonical UUID 空间；D-05 decision_id 被 `_DECISION_ID_RE`（`intervention_lifecycle.py:254`）钉死为 `aurora_<32hex>`——两个 id 空间结构不相交，域串还进 hash seed。limitations #5 已如实声明这是呈现面约定并登记迁移路径。可接受。

**R-C3 拒绝优先序 + 零惩罚 — 裁决：成立。**
`build_revisit_record` 判定序 no_prior → rejected → 去重样本≥1 → 窗口二分；拒绝时计数仍如实随行、`proves_relevance=False`、`revisit_evidence_integrity` 钉死（伪造 related 无身份 → False，单测亲证）。张力面（拒绝后用户又显式 accept 也被拒绝压制）为「少宣称」方向——对本卡「不夸大」红线是安全侧，登记为观察 O-1。零惩罚：`record_response` 全文无任何经济路径（亲读 `intervention_lifecycle_service.py:218` 起）；服务测钉 REJECTED 行恰一 + `photon_balance==0` + `reward_consequence="none"`；信封常量结构冻结（mutation 3 亲验 fail-loud 测会咬）。不变量强度充分（回归性钉，非形式化证明——对本卡目的够用）。

**R-C4 understanding 门对 friction 卡放行 — 裁决：合规，不过松。**
按卡验收字面：「无数据不出充分理解」——friction 卡 `samples=exposures>0` **有数据**，放行是字面合规。bounded：本服务任何档位都不产理解宣称文案；band 名 `qualitative_only` 不构成「充分理解」读法；`find_understanding_overclaims` 词表在册。对照面：helped 卡有删失即扣（服务测 `claim_allowed=False`+`censored>=1` 亲证）。登记 O-2：`find_understanding_overclaims` 目前只存在于契约层未被生产路径调用（今日无理解文案可扫，属防御纵深，非缺口）。

**R-C5 outcome 账本撤回未接呈现面 — 裁决：不阻塞 REVIEW_READY。**
亲核：`outcome_ledger_service.py` 零 retract/tombstone 路径；`retraction_recompute_service.py` 只 tombstone mastery_evidence 行，对 `InterventionLifecycleEvent` 零引用——**账本级撤回状态今天不存在**，无从接线。本读面真实删除信号 = 软删行，已全查询面 `not_deleted_filter` 且正反测亲证（关联行软删 → 样本 2→1；exposure 软删 → 回访不引用）。`exclude_withdrawn_refs` 为未来接线点。limitations #6 描述与事实相符（诚实）。后续 owner 事项见 CH-1。

## 3. 三验收独立核验（mutation + 构造亲验）

- **验收①「三例两例不写 67%」**：mutation 亲测——把 `_claim_violations` 数值面置空（`has_percent/has_causal_effect=False`）→ `test_three_examples_two_linked_causal_percentage_rejected` **红**（另 3 门测同红，4 failed/39 passed）；还原后绿。服务层 `test_three_exposures_two_linked_card_carries_no_causal_percentage` 以真实生产入口构造 3 暴露 2 链接：fact 3/2 随行、全 payload 字符串无 67%/成效族、M-06 零违例、`causal=False`。**PASS**
- **验收② 无数据不出充分理解 + 已删来源不复用**：mutation 2（`samples<=0` 放行）→ `test_no_data_never_claims`+`test_zero_samples_with_censored_is_still_no_claim` **红**；还原后绿。软删亲构造：服务测软删关联行 → 样本 2→1 即刻回落；软删 exposure → 回访不再引用（断言为弱析取，见 O-3；契约层 no_prior 逻辑另有正反钉）。**PASS**
- **验收③ 一观察≤一主建议 + 可拒绝零扣奖**：mutation 3（信封容忍 >1）→ `test_two_primary_candidates_fail_loud` **红**；还原后绿。拒绝路径：真实 `record_response(REJECTED)` 落行恰一、`photon_balance==0`、回访 `rejected_by_user`+`reward_consequence="none"`、事后链接 outcome 不改写。**PASS**

三次 mutation 用后全部还原（`git diff` 空），临时探针/临时 worktree 全部删除。

## 4. 纯函数 / 零第二真源 — 核验通过

- `insight_presentation.py` 615 行亲读：import 仅 stdlib + `attribution`/`experience_memory`/`intervention_lifecycle` 三权威；零 IO、零 LLM、零网络、零时钟（时间由调用方传入）。
- `git diff --stat 90d8196a..1e626998` 恰 4 文件（契约层 + 服务层 + 两测试）；`backend/app/api/`、`models/`、migrations、`proto/`、`mobile/`、`gateway/` 零改动——**零新表、零新端点**。路由 `response_model=dict[str, Any]`（`insights.py:46`），payload 附加字段不改 OpenAPI schema；openapi 契约测 + evidence_cards API 契约测亲跑全绿。
- 单一权威复用 5 处核实为 import 消费（D02 sample id / M-06 扫描 / D-05 禁词·窗口·摘要），未复制语义。

## 5. 测试质量与数字诚实性 — 全部属实

- 52 = 43 + 9：单测逐类点数 10+6+4+5+4+12+2=43，服务测 9；亲跑 52 passed。
- 597/1skip 口径与 manifest 完全一致；`--ignore` 的 bert 文件确为环境债（transformers 缺），与 diff 零交集。
- mypy 59=59 字节级同清单独立复证（base 在精确分支点临时 worktree 复跑）。
- D02 去重面测试真实：`test_replayed_outcome_delivery_does_not_inflate_sample_size` 经生产入口 + 绕过写幂等的直插行构造，raw=2 如实 / samples=1 不放大 / qualifier 在册——非纸面测试。
- 五件套 SHA256 逐字节核验一致；review_receipt.json 为作者 PENDING 占位（无审查结论泄漏），合规。

## 6. 合并落差 — 零冲突

`git merge-base 1e626998 24c176cb` = `90d8196a`；`git merge-tree` **0 个 "changed in both"**；main@`24c176cb` 变更面 = mobile/**、.gitignore、backend/tests/q02_surface2.py——与 backend/app insights 族零重叠。合并落差：**无**。

## 7. 挑战与观察（不阻塞，移交后续 owner）

- **CH-1（呈现样本量分组粒度，探针实证）**：`_directional_outcome_rows` 按 `(intervention_type, friction_tag)` 二元组分组去重，而 D-05 `SliceSummary` 按 `SituationSignature` 四元组切片。探针（合法切片词表 exam/project，各带正 outcome）：同 `(rescope, knowledge_bottleneck)` 两切片产两张**同 id** 卡（重复 id 为 V3 既有行为，非本卡引入），各自 `fact.n_observed=3/1` 但 `uncertainty.samples` 均为 **4**——单卡内样本量面与事实面不一致。重放不放大红线仍成立（samples 恒 ≤ 窗口内 unique (decision,outcome) 对），但「分母随行」精神被削弱。建议：去重分组键对齐全四元组，或在契约 docstring 明示呈现粒度 = 卡公开 id 的二元组。
- **CH-2（服务层门扣下分支零测试）**：`meta.presentation_gate_dropped` 分支无服务测覆盖（封闭模板使生产数据构造不出违例卡——本测文件 docstring 已如实声明）；本审查以 monkeypatch 探针实证分支工作。建议补一条 monkeypatch 式服务测钉死「扣下+登记+不发出」。
- **O-1**：回访拒绝优先序把「拒绝后又显式 accept」也压成 rejected_by_user（少宣称方向，安全；如未来需要可按响应时序取最近）。
- **O-2**：`find_understanding_overclaims` 未接入生产路径（今日无理解文案可扫，防御纵深）。
- **O-3**：`test_deleted_source_rows_are_not_reused_by_cards_or_revisit` 的回访断言为弱析取（存在其他活 exposure 时恒真）；建议加「全 exposure 软删 → no_prior」直证。

## 8. 裁决

**PASS_WITH_CHALLENGES**：三验收 + objective + D02-R1 C-3 全部独立复现且 mutation 反例钉真实可失败；证据五件套数字无夸大；纯函数/零第二真源声明属实；与 main 零冲突。CH-1/CH-2 与 O-1..O-3 登记为后续 owner 事项，不改判本卡。
