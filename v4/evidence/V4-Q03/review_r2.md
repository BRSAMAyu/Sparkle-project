# V4-Q03 · 二审 receipt（review_r2）

- 审查会话：wtQ03R2（独立未参与 Q03 验收实现、一审与整改；kind=verification · risk=high · 双审之第二审）
- 审查对象：分支 `agent/v4/q03` @ `487b2019`（被评链 = 验收交付 `13771c0d` → 一审 receipt `94909b7c` → F1 整改 `1aa40314` → receipt 注记 `487b2019`；基线 `a8f46650`）
- 审查日期：2026-09-29（worktree 审查全程保持干净；所有复跑追加记录均按一审同法 `git checkout` 还原并复验哈希）
- 二审靶：①F1 整改复核（首靶）②I07 红线零放松 ③一审护栏抽验 ④数字与封存完整性 ⑤移动端登记项定性 ⑥合并落差

## 裁决

**APPROVE**（二审；一审 APPROVE_WITH_CONDITIONS 的终门条件 1——F1 修复 + S1④b 复验——经本轮独立复证判定为**有效关闭**；条件 2（F2 wrinkle 知悉义务）不属本卡整改面，维持对后续真模型 j06 复跑卡的知悉要求）

**F1 整改判定：处方 A 有效，缺陷关闭（defect_F1_enter_stuck_from_example 翻绿亲证）。**

## 1. F1 整改复核（首靶）

### 1.1 处方 A 语义亲读 + reason 枚举完备性核

- **封闭集枚举**：`SCAFFOLD_TRANSITION_REASONS` 共 6 项（`backend/app/core/hybrid_policy.py:107-115`，
  封闭集注释明示「扩展 = bump」）。包装层调用点硬编码 `user_chose=True` 且从不传 `attempt_failed`
  （`backend/app/core/learning_journey.py:289`，签名不暴露二者）→ **经此生产路径可达的 reason 仅 3 类**：
  1. `OK.independent_check_reached`（已在检验段，幂等）→ 分支一（stage==check）→ `hold_reason=None` ✓
  2. `OK.advance_user_chose_with_evidence`（user_chose+证据支持单点推进：example→attempt 中间跳 /
     attempt→check 终跳）→ 分支二（`reason.startswith("OK.")`）→ `None` ✓
  3. `HOLD.evidence_not_supported`（user_chose=True 落到转移表末行的唯一 HOLD 形态）→ 分支三 →
     `CHECK_REASON_HOLD_EVIDENCE` ✓（标签与真实裁决**逐字一致**，无错标）
- **不可达类目核（「过宽」质疑的答案）**：`OK.hint_fading_prior_example_sufficient`（需 user_chose=False）、
  `HOLD.user_did_not_choose`（同）、`SUPPORT.failure_adds_local_hint`（需 attempt_failed=True）在本调用
  路径**均不可达**。故「构造非 OK 也非 HOLD.evidence_not_supported 的裁决」在现签名下无实例；
  `OK.*→None` 对可达集**不过宽**——两个可达 `OK.*` 都是真实的非暂缓裁决。
- **前向观察 O-r2-1（非缺陷，登记）**：分支二的 `startswith("OK.")` 是前缀信任 + 分支三是兜底
  （一切非 OK 非 check 一律标 `HOLD.evidence_not_supported`）。当前可达集下两者零错标；若未来封闭集
  扩展出新的 OK.*/HOLD.* 类目，需按「扩展 = bump」纪律过审时同步核对本包装层三分支映射（尤其兜底
  分支会把新 HOLD.* 类目统一错标为 `HOLD.evidence_not_supported`）。现封闭集纪律下可接受。
- **服务层零改动声明核**：`git diff a8f46650..1aa40314 -- backend/app/services/learning_journey_service.py`
  = 仅 `CheckEnterResult` docstring 三结局口径化（+8/-1），持久化门单条件
  `hold_reason is None and decision.stage != scaffold.stage`（`learning_journey_service.py:337`）逐字符未动。
  三结局在实现上一一对应：幂等在段（hold=None、stage 相等→不写、`check_available=True` 重出题）、
  中间推进（hold=None、stage 变→写回、stage 门拦出题）、真实暂缓（hold≠None→不写不出题）。
  docstring 声明与行为一致。

### 1.2 S1④b 复验探针亲放（中间推进→出题→判分全链）

- 命令：`cd wtQ03/backend && SECRET_KEY=… ENVIRONMENT=test …/.venv/bin/python -m pytest
  ../v4/evidence/V4-Q03/probes/test_f1_recheck_s1_4b.py -q` → **1 passed**（1.61s）。
- 复跑追加的 7 条记录与已提交 `r1_fix_recheck/recheck_records.jsonl` 逐条 diff：**除 ts 外逐字段一致**
  （enter_hop1 持久化 attempt 无误报 HOLD / submit 提前拒判分 / enter_hop2 出题+DB 写回
  independent_check+answer 原地保留 / 判分 correct=true 零答案材料 / 无证据反例 HOLD / 单跳回归 /
  verdict PASS）。复跑后已还原，文件 sha256=`d227801b…4282` 与提交态一致。
- 「S1④b 同构」声明核：探针 import 验收剧本 `_make_mastery_task/_CHECK_ANSWER/_CHECK_QUESTION`
  （probes/test_f1_recheck_s1_4b.py:44-49，复用不复制），真实 REST 三端点 + 独立记录文件，**不污染**
  验收 raw_records（复核属实：`raw_records/` 在整改 commit 中零 diff）。

### 1.3 「原 S1 探针翻红于缺陷存在性断言」形态核验——**形态属实**

- 亲跑 `pytest …/test_q03_acceptance.py::test_s1_example_isolation_and_hint_fading` → **1 failed**，
  翻红位置 = `test_q03_acceptance.py:318`
  `assert ok.scaffold_persisted is False, "F1：合法推进未持久化（缺陷本体）"`；
  pytest E 行显示实际值 `scaffold_persisted=True`，且 CheckEnterResult view =
  `{stage: attempt, reason: OK.advance_user_chose_with_evidence}`（无误报 HOLD）。
- ①示例隔离/②投影剥除/③渐隐链/④a 无证据门的断言全部先于 :318 执行通过——**翻红不是其他面
  被破坏，而是「缺陷不复现」这一存在性断言本体**，与整改自述逐字吻合。复跑追加记录已还原，
  S1 raw_records sha256 复验与 manifest 一致；`test_q03_acceptance.py`/`conftest.py` 零改动
  （sha256 复验 MATCH，见 §4）。

## 2. I07 红线零放松——**亲证成立**

- 新用例单列亲跑：`pytest tests/services/test_learning_journey_service.py::test_enter_check_from_example_reaches_check_in_two_persisted_hops
  ::…without_evidence_still_holds` → **2 passed**（4.32s）。用例内断言亲读：中间推进后
  `grade_check` 仍返回 `graded=False/correct=None/reason=HOLD.scaffold_not_at_check`；两跳后
  `guide_json…independent_check.answer` 原地保留服务端（判分权威不动）。
- 转移表零改动声明核：`git diff a8f46650..HEAD -- backend/app/core/hybrid_policy.py
  backend/tests/unit/test_hybrid_policy.py` = **空**；`test_hybrid_policy.py` 亲跑 **31 passed**
  （37.27s）。I07 权威面零触碰属实。
- 出题 stage 门亲读：`check_available` 要求 `hold_reason is None AND stage==independent_check AND
  题面在`（learning_journey_service.py:349-353）——中间步不出题；`assert_client_payload_clean(view)`
  仍在出口（:366）。整改未新增任何答案可达面（复验探针对两跳全 payload 做 `"answer"` 子串断言）。

## 3. 一审四护栏抽验——**抽 ① + M1，均复证成立**

- **护栏①（S2）亲跑**：`pytest …/test_q03_acceptance.py::test_s2_agent_answer_never_settles_human_mastery`
  → **1 passed**（44.87s）。agent 完成 COMPLETED 而人类掌握面 0.0、NON_HUMAN receipt、
  正面对照 user 结算 +25.0 一审记录维持。
- **M1 mutation 亲放复放**：`sed app/services/task_service.py:826 'if settlement is not None and not
  settlement.allowed:' → 'if False and …'`（diff +1/-1 确认命中）→ 复跑 S2 **1 failed**（17.67s，
  结算门被旁路即红）→ `git checkout -- app/services/task_service.py` 还原 → S2 **1 passed**（38.82s）
  → `git status` 干净、10 件哈希复验 ALL_MATCH。探针可失败性成立，用后零残留。
- 护栏②③④本轮未复放（二审抽验约定：护栏抽 1 + mutation 抽 1）；一审 7/7 全绿记录与 S1/S2 两面
  本轮再证一致，无冲突信号。

## 4. 数字与封存完整性——**逐项亲证**

| 申报 | 亲跑结果 | 一致 |
|---|---|---|
| U10 34→39 | core 22 + services 13 + api 4 = **39 passed**（12.24s + 3.78s） | ✓ |
| I07 31 不变 | **31 passed**（37.27s）+ 零 diff | ✓ |
| 基线 174→176 | manifest 同一 10 文件命令 → **176 passed in 256.08s**（exit 0） | ✓ |
| 10 件封存 sha256 | `run_manifest.artifacts_sha256` 全 10 件（7 raw_records + 2 probes + transcript）`shasum -a 256` 逐件 **MATCH**（每轮复跑还原后各复验一次） | ✓ |
| ruff/black 零新增 | 4 个整改触碰文件 `ruff check` All checks passed；`black --check -l 120` 4 files clean | ✓ |
| OpenAPI 零漂移 | `scripts/check_openapi_contract.py`（仓根）→ **PASS**，exit 0；快照产物落 `quality/`（gitignore，不入库） | ✓ |
| 五件套+一审 receipt 未动 | `git diff 13771c0d..HEAD` 对 test_results/limitations/diff_or_evidence_only/raw_records/probes/transcript = 空；review_r1.md 自 `94909b7c` 起零 diff；run_manifest 仅 r1_errata 授权勘误（路径口径+行幅），历史数字保留并内嵌勘误节 | ✓ |
| 时间线 | 验收记录 ts 09-28T20:37Z < 交付提交 09-29T04:51+0800；复验记录 21:28Z（=05:28+0800）< 整改提交 05:34+0800 < 注记提交——无倒签 | ✓ |

## 5. 移动端登记项定性——**cosmetic（用户面不可见），归属恰当**

- 源码亲读：`mobile/lib/features/learning/presentation/providers/learning_journey_provider.dart:99`
  `checkHoldReason: result.available ? null : (result.holdReason ?? 'HOLD.evidence_not_supported')`——
  修复后中间推进响应（`available=false` 且无 `hold_reason`）确会触发该兜底字面量进客户端状态。
- **但 UI 从不渲染该字面量**：`learning_journey_screen.dart:399-405` 中 `holdReason` 仅作非空标记，
  展示的是本地化通用提示 `l10n.learningCheckHoldHint`（「证据门暂缓：先完成练习再检验」）。
  该提示对中间推进状态**语义恰好正确**（用户刚被推进到 attempt=practice 段，「先练习再点检验」
  正是正确指引），下次点击检验即 `available=true` 出题。
- **定性：cosmetic-to-invisible，非用户误导**。真实残余风险在客户端状态面——`checkHoldReason`
  携带服务端从未发送的伪造 reason 值（证据明明支持），若未来遥测/调试面/生成文案把它当服务端
  真值消费即成谎值；当前消费面仅一处且不外显。C- 级客户端卫生项，不阻塞。
- **归属核**：U10（资料→错题→练习→检验连续体验，DONE_REVIEWED）即该移动面的交付 owner，登记
  「U10 移动面后续项」恰当。勘误一处措辞（N-r2-1，info）：remediation_r1.md「会短暂显示该兜底」
  高估了可见性——显示的是通用提示而非 `HOLD.evidence_not_supported` 字面量；登记方向与归属不受影响。

## 6. 合并落差——**零冲突亲证**

- `git merge-tree --write-tree HEAD main`（本地 main=`c859df37`，已含一审所指 `f5ed0fcf` 及其后的
  心跳提交）→ **exit 0，零 CONFLICT**。
- 双侧改动交集（`a8f46650` 起）：仅 `v4/04_tasks/tasks.json`（卡片登记追加，两侧不同条目，merge-tree
  干净解）；main 侧 67 个变更文件与 backend `core/learning_journey`、`hybrid_policy`、`task_service`、
  mobile learning 面**零重叠**。声明成立。

## 审查动作清单（可复现）

| 动作 | 命令/锚点 | 结果 |
|---|---|---|
| F1 复验探针亲放 | `pytest ../v4/evidence/V4-Q03/probes/test_f1_recheck_s1_4b.py -q` | 1 passed；7 记录逐字段复现（ts 差异外） |
| 原 S1 翻红形态 | `pytest …::test_s1_example_isolation_and_hint_fading` | 1 failed @ :318 缺陷存在性断言本体 |
| U10 三面 | `pytest tests/core/test_learning_journey.py tests/services/test_learning_journey_service.py tests/api/test_learning_journey_api.py -q` | 39 passed |
| I07 红线用例 | `pytest tests/services/…::test_enter_check_from_example_reaches_check_in_two_persisted_hops …without_evidence_still_holds` | 2 passed |
| I07 权威 | `pytest tests/unit/test_hybrid_policy.py -q` | 31 passed（hybrid_policy 零 diff） |
| 护栏① S2 | `pytest …::test_s2_agent_answer_never_settles_human_mastery` | 1 passed |
| M1 复放 | `sed task_service.py:826 'if False and …' → S2 RED → checkout → S2 GREEN` | 复证，零残留 |
| 基线 | manifest 同命令 10 文件 | 176 passed, 256.08s, exit 0 |
| 哈希 | `run_manifest.artifacts_sha256` 全 10 件 × 2 轮 | 逐件 MATCH |
| 质量/契约 | ruff + black 4 文件；`scripts/check_openapi_contract.py` | 全 PASS |
| 合并落差 | `git merge-tree --write-tree HEAD main` | exit 0 零冲突；交集仅 tasks.json |
| 还原 | 每轮复跑后 `git checkout -- raw_records/ r1_fix_recheck/…` + 全树 status 复查 | 工作树干净 |

（环境：cwd=`wtQ03/backend`，解释器=主检出共享 `.venv` Python 3.11.15，`SECRET_KEY=… ENVIRONMENT=test`；
探针独立 sqlite 内存库，无 .env/DATABASE_URL，与演示库零接触同一审核。本 receipt 提交后工作树仅新增
本文件与 review_receipt.json 的 R2 回填。）

## 二审结论与遗留登记

1. **F1 关闭**（处方 A 语义正确、枚举完备、全链亲放、翻红形态属实）；终门条件 1 满足。
2. **O-r2-1（观察项，非缺陷）**：`request_independent_check` 分支二的 `OK.*` 前缀信任与分支三兜底，
   在封闭集「扩展 = bump」时须同步复核三分支映射（否则新 HOLD.* 类目会被兜底错标）。
3. **N-r2-1（info）**：移动端兜底「短暂显示」措辞高估——字面量不渲染，展示为通用本地化提示；
   语义当前恰好正确，伪造 reason 值仅存在于客户端状态（U10 移动面后续项定性不变）。
4. 条件 2（F2 wrinkle）维持：后续在真模型（L2+）复跑 j06 旅程的卡仍须按 review_r1 条件 2 知悉
   重放重起草风险（归 U04/j06 责任面，本卡未触）。

Q03 双审齐全（R1 APPROVE_WITH_CONDITIONS → 条件关闭 → R2 **APPROVE**），可进入终门裁决。
