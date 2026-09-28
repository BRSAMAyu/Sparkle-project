# V4-Q03 · 一审（R1）终门条件 F1 整改 receipt

- 整改会话：wtQ03（原分支续作，未 push）
- 整改对象：review_r1.md 终门条件 1——F1（B 级）example 起点经 check/enter API 不可达独立检验段（U10 责任面）；一审 receipt 文件（review_r1.md）与验收五件套原文未动
- 分支：`agent/v4/q03`，一审 receipt `94909b7c` 之上
- 条件 2（F2 wrinkle 知悉义务）不属本次整改面：F2 归 U04/j06 责任面，本卡整改未触 hybrid_journey_service；后续在真模型（L2+）复跑 j06 旅程的卡须按 review_r1 条件 2 知悉重放重起草风险
- 方法：处方裁决（一审两选一）+ 最小改法 + 一正一反测试 + **mutation 自证**；回归面全量复跑；ruff/black 零新增；OpenAPI 契约零漂移

---

## F1（B）example 起点 → 检验段不可达（合法中间推进被误标 HOLD、持久化门永不写回）

**处置：处方 A——`request_independent_check` 中间推进返回 None hold（=推进合法）。未选处方 B，裁决理由如下。**

- **缺陷本体是标注错误，不是门条件错误**：`next_scaffold_step`（hybrid_policy.py:421-428）在 user_chose+evidence_supported 下对 example→attempt 给出 `reason=OK.advance_user_chose_with_evidence`——证据**支持**推进；`request_independent_check`（learning_journey.py 原 :275-283）却把一切非直达 check 的裁决改标 `HOLD.evidence_not_supported`，向封闭 HOLD 词表注入假语义，且该假 reason 原样出口到客户端载荷（一审探针亲证同一响应内 `decision.reason=OK.advance_*` 与 `hold_reason=HOLD.evidence_not_supported` 并存）。服务层持久化门 `hold_reason is None`（learning_journey_service.py:329-333，N-r1-2 勘误行幅）因此对合法推进永不写回。
- **为什么 A 而非 B**：
  1. A 在标注源头修——`OK.*` 裁决一律 `hold_reason=None`，`HOLD.evidence_not_supported` 只留给真实不支持的裁决，词表语义恢复诚实；B 在消费侧绕过标注，假 HOLD 继续出口（payload 同时携带 persisted=true 与 hold_reason=HOLD.*，自相矛盾），且需在服务层复制 reason 前缀字符串判定，制造第二真源。
  2. A 保持服务层持久化门 `hold_reason is None` 的单一书面写条件——learning_journey_service 模块 docstring「写路径只有一个：用户显式选择『检验』且证据支持时……写回」在修复后**第一次在 example 起点为真**；无需改服务层任何逻辑（本次服务层仅 CheckEnterResult docstring 三结局口径化，逻辑零改动）。
  3. **MASTER_DESIGN §5/§6 语义最精确侧**：「人必须完成理解/尝试/独立检验」「示例→自己做→检查」——中间推进是设计旅程的**合法**一步，应当可达且诚实标注；「脚手架是否暂缓」（hold_reason）与「是否放行出题」（check_available）分立后，出题仍被服务层 stage 门（`decision.stage == independent_check` + 题面在）拦住：中间步不出题、用户回 practice 段亲自完成（attempt），再点检验进入检验段——人不被跳步，答案面零放松。
- **改动**：`backend/app/core/learning_journey.py` `request_independent_check`——`decision.stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK`（单跳正落/幂等在段）与 `decision.reason.startswith("OK.")`（合法中间推进）两分支返回 `hold_reason=None`；其余（真实证据不支持）保持 `CHECK_REASON_HOLD_EVIDENCE`。
- **不放宽面（红线核对）**：submit 判分门未动（未到检验段提交仍 `HOLD.scaffold_not_at_check`，新用例钉死）；I07 判分权威 `answer` 原地保留服务端 guide_json（新用例断言写回后仍在）；`INDEPENDENT_CHECK_ANSWER_KEYS`/红化/泄漏探针零改动；证据门零放宽（无证据反例保持，见下）。

## 测试（一正一反 + 全链 + mutation 自证）

- 正（core）：`test_request_check_from_example_intermediate_advance_is_not_a_hold`——example+证据 → attempt + `OK.advance_user_chose_with_evidence` + hold=None；`test_request_check_example_reaches_check_in_two_legal_hops`——两跳纯函数可达 check。
- 反（core，反例保持）：`test_request_check_from_example_without_evidence_still_holds`——example 无证据 → 原地 + HOLD。
- 正（services，F1 全链复验面）：`test_enter_check_from_example_reaches_check_in_two_persisted_hops`——enter#1 中间推进 `scaffold_persisted=True`、`check_available=False`、**无 hold_reason 键**、不出题、DB 权威位写回 attempt；中间推进后提交仍拒判分；enter#2 `check_available=True` + 题面 + DB 写回 independent_check；`answer` 原地保留。
- 反（services，反例保持）：`test_enter_check_from_example_without_evidence_still_holds`——example 无证据 → HOLD + 不推进不落库 + DB 恒 example。
- **mutation 自证**：`git stash` 还原修法（回到恒 HOLD 旧实现）→ 新增用例 **3 failed**（两跳链 ×2 + 中间推进非 HOLD ×1）、**1 passed**（无证据反例——HOLD 路径本就不受修法影响，正确）→ `stash pop` 复原全绿。

## S1④b 复验（终门条件翻绿记录）

- 复验探针：`probes/test_f1_recheck_s1_4b.py`（**复用验收剧本同一场景设定** `_make_mastery_task`：example 默认起点 + 真实 ErrorRecord review_count=2 + 服务端判分权威；真实 REST 面；原始记录独立落 `r1_fix_recheck/recheck_records.jsonl`，**不追加**验收 raw_records）。
- 结果 **PASS**：enter#1 落库推进（attempt，不出题、无误报 HOLD）→ enter#2 放行出题（independent_check）→ DB 两跳写回 → 到段判分 correct=true 且响应零答案材料；无证据反例 HOLD 保持；attempt 起点单跳既有行为不变。逐条记录见 recheck_records.jsonl，汇总见 `r1_fix_recheck/recheck_summary.json`。
- **原剧本探针翻红（缺陷不复现的直接证据）**：`test_q03_acceptance.py::test_s1_example_isolation_and_hint_fading` 修复后 exit 1，恰好红在缺陷存在性断言本体（line 318 `assert ok.scaffold_persisted is False, "F1：合法推进未持久化（缺陷本体）"` → `assert True is False`）；其 ①②③④a（示例隔离/投影剥除/渐隐链/无证据门）修复后仍全过。复跑追加行已按一审同法 `git checkout -- raw_records/` 还原，S1 raw_records sha256=`1b21c464…bbdb` 与 manifest 封存值一致；`conftest.py`/`test_q03_acceptance.py` 零改动（sha256 复验 MATCH）。

## 测试计数（本整改后）

| 面 | 整改前 | 整改后 | 增量 |
|---|---|---|---|
| `tests/core/test_learning_journey.py` | 19 | **22** | +3 |
| `tests/services/test_learning_journey_service.py` | 11 | **13** | +2 |
| `tests/api/test_learning_journey_api.py` | 4 | **4** | 0 |
| U10 小计（一审口径 34） | 34 | **39** | +5 |
| `tests/unit/test_hybrid_policy.py`（I07 权威） | 31 | **31** | 0（转移表零改动） |
| manifest 基线 10 文件（U10/U04/I07/D04+结算面） | 174 | **176** | +2（该命令不含 tests/core，故非 +5） |

全部复跑绿（本会话独立执行，解释器=主检出共享 `.venv` Python 3.11.15，cwd=wtQ03/backend，`SECRET_KEY=… ENVIRONMENT=test`，与 sqlite 探针隔离纪律同一审）。

## 回归面清单

- I07 权威 31（`test_hybrid_policy.py`）全绿——冻结转移表零改动，单跳 attempt→check 既有服务用例不改一字通过（`test_enter_check_with_review_evidence_advances_and_serves_question` 等）。
- U10 契约/服务/API 三文件 39 全绿；REST 三端点契约面零变化——`scripts/check_openapi_contract.py` **PASS，快照零漂移**（行为变化无新路由、无 schema 变化）。
- 结算/星图/混合旅程面（manifest 基线 10 文件）176 全绿。

## 质量门（零新增口径，与一审同法）

- ruff：4 个改动/新增 backend 文件 **All checks passed**。
- black（line-length 120）：4 文件 clean（would be left unchanged）。

## 行为变更声明（既有行为修改，如实）

1. **F1 是生产行为变更**：example（默认 ScaffoldState）起点的任务经旅程 check/enter 现可两跳到达独立检验段（整改前任何 API 序列不可达）；每跳持久化写回 I07 权威位。中间推进响应不再携带 `hold_reason`（客户端以 `check_available` 为放行权威、`scaffold.reason` 为路由面）。
2. 判分/出题/红化门零放松：未到检验段 submit 仍拒判分；出题仍 stage 门；答案材料可达面经复查零新增（复验探针全 payload 断言）。
3. **登记项（不在本次责任面）**：移动端 `learning_journey_provider.dart:99` 对 `available=false` 且无 hold_reason 的响应有兜底文案 `'HOLD.evidence_not_supported'`——中间推进一跳后若立即弹检验面板会短暂显示该兜底。后端契约已不再说谎；该展示兜底归 U10 移动面后续项，供 owner 参考。

## 记录面勘误（一审授权项，N-r1-1/N-r1-2）

- `run_manifest.json`：commands_and_exit_codes 的 pytest 命令路径口径修正为自洽形式（真实 cwd=wtQ03/backend + 共享 .venv 绝对路径解释器；M1-M3 补 cwd 注记）；line_anchors.F1_defect 持久化门行幅勘误为 `learning_journey_service.py:329-333`。勘误说明内嵌于 manifest 新增 `r1_errata` 节；**历史结果数字（174/7 passed 等）为被评 SHA a8f46650 的原始记录，不改写**。limitations.md 的 330-333 与 test_results.json 的 322-333 属五件套原文，保留不改，以 manifest 勘误为准。

—— wtQ03 整改会话，2026-09-29
