# V4-D02 · 独立审查 receipt（R1）

- 审查会话：wtD02R1（未参与 D02 实现，独立会话；只读审查 + 证据复跑 + 突变亲测，未改实现面）
- 审查对象：`agent/v4/d02` @ `63af3d2e`（base `56c3341c`；9 files +1566/−3）
- 卡标准：`v4/04_tasks/cards/V4-D02.md`；契约参照：`v4/evidence/V4-B05/contract_receipt_min.md`
- 日期：2026-09-28
- **总裁决：APPROVE**（4 条非阻塞观察 C-1…C-4，见 CHALLENGED；不阻塞集成）

## 1. 复跑证据（审查者本机亲跑，非转录实现者数据）

| 项 | 命令（`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`） | 实测结果 | 与声明对照 |
|---|---|---|---|
| 契约测 | `pytest tests/core/test_attribution.py -q` | **38 passed** (0.41s) | = 声明 38 |
| services 全量 | `pytest tests/services -q` | **1018 passed, 10 skipped** (455.87s) | = D01 基线 1018，零回归 |
| 受影响面 | `pytest tests/core tests/contract/{intervention_lifecycle,experience_memory,event_registry}_contract.py tests/services/{intervention_lifecycle,experience_event,f507_lifecycle_wiring,outcome_ledger}_service.py tests/services/test_x08_outcome_ledger_gj.py tests/unit/{outcome_ledger_contract,x08_outcome_capture}.py -q` | **666 passed, 1 skipped, 36 errors**；36 errors 全部 `tests/core/test_bert_intent_classifier.py`（transformers 未装，收集期环境噪声） | = 声明 666+36env；与 attribution 零交集 |
| mypy 棘轮 | `bash scripts/ci/mypy_ratchet.sh`（repo 根） | **errors: 55 / baseline: 77**，exit 0 | = 声明 55/77 |
| mypy 新文件 | `mypy app/core/attribution.py tests/core/test_attribution.py` | attribution/test 两文件 **0 error 行**（30 条 follow-import 噪声全在既有文件） | = 声明零新增 |
| ruff/black | `ruff check … && black --check …`（两新文件） | 全过 | = 声明 |
| 守卫（wtD02） | `bash scripts/run_all_rule_guards.sh` | 失败集 = **{BG}**；BJ PASS（豁免注记生效） | = 声明收口后状态 |
| 守卫（主检出） | 同命令 | **86 条全过**（manifest 记录的 AM/AURORA-CONFIG/CARD-DUAL-WRITE 三项在审查时点不可复现——该组守卫与本地未提交状态相关；此刻基线比声明更干净） | 本卡新增回归 = **0**（两个方向均成立） |
| BG 归因 | `check_rule_bg_proto_cross_language_parity.py` 两检出对照 | wtD02 = "Go/Dart generated file missing"（bare worktree 无 gitignored 生成物）；主检出 `[Rule BG] PASS` | 环境性失败，非代码回归，与 limitations #5 一致 |

## 2. 验收逐条核验

### 验收① 分域反伪归因 + 公开分母 — PASS

- 四域封闭：`AttributionDomain` StrEnum 仅 goal/task/occurrence/run；`ATTRIBUTION_DOMAINS` frozenset；测试 `test_domain_vocabulary_is_the_card_four` 字面冻结。
- 跨域逐字节相同 UUID 不串：`DomainKey.links` = `domain is other.domain and value == other.value`（domain 判定先于值）；`attribute_outcome` 在比对值**之前**判 `anchor.domain is not outcome_key.domain` → `unattributed/domain_mismatch`。红转绿反例 `test_identical_uuid_across_domains_never_links` / `test_cross_domain_verdict_is_unattributed_domain_mismatch`（同 UUID 跨 task/occurrence 域 → matched_key=None、sample_id=""）。
- `task_occurrence_id` 钉死：`DOMAIN_CORRELATION_KEYS` 表级仅 occurrence 域含 `("occurrence_id","task_occurrence_id")`；**import 期断言**两条（键名互斥 + `task_occurrence_id`/`goal_id` 永不入 task 域）；测试字面冻结 + 投影反例（`test_task_occurrence_id_only_projects_to_occurrence_domain`）。
- 公开分母：`AttributionDenominator` n_eligible=全体判定（含 unattributed/unjudgeable，不剔除难配对）；`unattributed_ratio` eligible=0 → `None`（不宣称 0%/100%）；`by_reason` 封闭四理由细分；`to_dict()` 公开面带 schema_version。测试含 3 样本 ratio=2/3 与空集 None 反例。

### 验收② 观察窗 censored + 幂等样本 id — PASS

- **委托为真非复制**（核过源码）：`anchor_observation_status` 是透传门面，逐参调用 D-05 `resolve_observation_status`（`intervention_lifecycle.py:429`，三删失+unknown+observed）；`attribute_outcome` 的超窗分支亦直接调该权威函数。窗口缺省/钳制复用 `clamp_observation_window_hours`/`DEFAULT_OBSERVATION_WINDOW_HOURS`（72h/[1h,30d]），无第二份窗口语义。测试 `test_unified_window_matches_d05_authority_for_all_four_domains` 对四域逐域断言与权威函数同输入恒同输出。
- 超窗绝不记失败：73h outcome → `unattributed/outside_window` + 锚点 `censored_window_closed`；判定面无任何 negative/failed 语义位；时序倒置（早于锚点）同出口。未到期 `censored_not_yet_due`、流失 `censored_user_churned`、坏行 `unknown` 各有反例。延迟 outcome（71h 窗内、now=100h 后收到）照常 attributed——真实事件时间 `occurred_at` 判窗，不读 `received_at`。
- 幂等样本 id：`derive_attribution_sample_id` 派生种子仅 `{schema, domain, anchor_id, outcome_id}`，**时间字段不进派生**；5 次重放 → 1 个唯一 id（`test_consumer_dedup_by_sample_id_counts_once`）。**突变 M3 亲做**：掺入 `now` → `test_replay_produces_identical_verdict_and_sample_id` 红（`attr_8ba793…` vs `attr_be2996…` 两 id），还原后 38 绿。

### 验收③ 链路追踪还原 — PASS

- 四跳逐跳重算（无存储信任）：hop1 `receipt_ref_scheme` ∈ B05 六元封闭集（`EXPERIENCE_RECEIPT_REF_SCHEMES`）；hop2 `event_identity` 用 D01 `derive_dedupe_key`（B05 §3 冻结公式 sha256(receipt_ref+kind+version_token)）+ `derive_experience_event_id` 重算比对；hop3 `outcome_identity` 用 D-02 `derive_outcome_id` 重算且 `OutcomeSource` 词表外 fail-loud；hop4 `outcome_link` 三选一（`outcome://` 直连 tail 比对 / 同域键 `DomainKey.links` / D-05 `outcome_links_exposure`）。任一跳断 → `TraceHop(ok=False, detail=显式报因)`、`traceable=False`；outcome 缺失是显式结论非静默通过。
- 随机样本还原：`test_random_sample_full_chain_restore` 用 uuid4 随机 id + 真实 D01 投影事件 + 真实 D-02 outcome id，四跳全 ok、重跑 trace 恒同；跨域锚点（occurrence 域持同值 UUID）不得完成链路（`test_same_domain_anchor_link_restores_chain` 后半反例）。
- **突变 M4 亲做**：`event_identity` 比较改恒真 → 伪造 `eev_forged…` 事件被容事件 `traceable=True`，`test_mutated_event_breaks_chain_loudly` 红；还原后绿。报错形态核验：`TraceHop(hop='event_identity', ok=False, detail="stored event_id='…' does not match recomputed '…'")`。

### 既有权威零改动 — PASS

`git diff 56c3341c..63af3d2e -- backend/app backend/gateway mobile proto` **仅新增 `backend/app/core/attribution.py`**；`intervention_lifecycle.py`/`outcome_ledger.py`/`experience_event.py`/`event_registry.py` 四权威文件 diff **0 行**（字节级未动）。词表全部 import 复用 + import 期断言（`USER_RESPONSE_EVENT_TYPES` 四值齐备断言、72h 断言、键名表互斥断言），无复制无改写。`edited` 显式迁移语义举证到位：`LifecycleEventType.EDITED` 是 D-05 既有显式成员，`test_edited_and_accepted_are_distinct_event_identities` 钉 edited/accepted 事件身份不同（DATA_AND_GRAPH「不填假 accepted」）。

### BJ 豁免与债登记 — PASS

- 全仓 `grep -rn "from app.core.attribution|import attribution" backend/app` 零命中（生产零接线声明属实）；`# rule-bj: exempt` 注记在 `attribution.py:64`，与既有先例（`slo.py` 等 5+ 文件）同款；`KNOWN_CODE_DEBT_LEDGER.md` P3 **#13** 登记行落库，含删除条件（接线后删豁免与台账条目）。
- 消费面划界与卡面一致：`V4-D03`（撤回派生影响重算）`depends_on: V4-D02`；`V4-D05`（洞察面标来源/样本/missing/censored）`depends_on: V4-D02`——与台账「V4-D03 按关联键找受影响面 / V4-D05 公开 unattributed 分母」吻合。

### 突变可证伪性（审查者亲做 4/4） — PASS

每次突变后字节级还原，`shasum -a 256 app/core/attribution.py` 每次还原点均 = `4c0b1c45…ba50d0`（与 `test_results.json.artifacts_sha256` 一致），工作树 clean：

| 突变 | 手法 | 实测红 |
|---|---|---|
| M1 跨域拼接 | `links()` 去掉域相等条件 | 1 failed：`test_identical_uuid_across_domains_never_links` |
| M2 超窗归因 | `if not in_window:` → `if False:` | 2 failed：`…beyond_window…` + `…before_anchor_never_retro_attributed`（见 C-1 措辞勘误） |
| M3 重放虚增 | sample id 派生掺 `now` | 1 failed：`test_replay_produces_identical_verdict_and_sample_id` |
| M4 链路篡改容忍 | event_identity 比较恒真 | 1 failed：`test_mutated_event_breaks_chain_loudly` |

## 3. CHALLENGED（非阻塞观察；建议随 V4-D03/D05 接线卡或勘误顺带处理）

- **C-1（receipt 措辞精度）**：`run_manifest.json` 突变②条目的失败标注「超窗反例+统一窗对照」不准确——实测两红为 `beyond_window` + `before_anchor` 时序倒置守卫；「统一窗对照」测（`test_unified_window_matches_d05_authority_for_all_four_domains`）走 `anchor_observation_status` 门面、不受该突变影响、始终绿。红数（2）与 `test_results.json` 记录（"…等"）本身无误，仅 manifest 括注措辞需勘误，不影响可失败性结论。
- **C-2（n_unknown ⊆ n_unattributed 的重叠语义）**：`broken_row` 判定同时计入 n_unattributed 与 n_unknown（保持 `n_attributed + n_unattributed == n_eligible` 不变式，ratio 口径保守不虚高）。该口径已在 `review_receipt.json` review-focus #2 向审查者显式申报、可接受；但 `UnjudgeableReason` docstring「与 unattributed 分开计数」易读作「互斥」，建议措辞改为「单列子计数」。
- **C-3（重放分母的消费方义务）**：`AttributionDenominator.from_verdicts` 对 5 次重放如实计 n_eligible=5（观测面），去重靠消费方按 `sample_id` 先行（归因面）——契约 docstring 已明示。登记为 V4-D05 呈现侧硬要求：公开比率前必须按 sample_id 去重，否则重放会放大分母。
- **C-4（naive-UTC 时戳的 DST 边缘）**：`normalize_occurred_at` 归一到 naive-UTC 后经 `.timestamp()`（按本地时区解释）比较；两侧同归一故内部自洽，但跨 DST 转换日窗口比较可偏 ±1h。该模式与 D-05 权威函数同款（继承约定，非本卡新缺陷），登记给后续可靠性卡统一收口。

## 4. limitations 如实性核验 — PASS

limitations.md 实为 **8 项**（审查指令述「⑥项」，工件只多不少）。逐项核实：#1 生产零接线（grep 实证）+「公开可查暂为 to_dict 结构面」不夸大；#2 `CorrelationIds` 未分域化、裸事件流槽位错置仍可能、收口归 event-domain 单头契约卡（event_registry 确未动，属实）；#3 四域外不统一（属实，intervention/plan/memory 归各自权威）；#4 unjudgeable 无持久化队列/告警（代码实证无）；#5 守卫基线差异（BG 环境性实证成立；主检出三项失败在审查时点不可复现、方向对本卡有利，见 §1）；#6 共享 venv（实证：worktree 无 .venv，ruff/black 取自 homebrew、pytest/mypy 取自主检出 venv）；#7 追踪入口依赖消费方持有 event_id（trace 签名如实）；#8 只用 `occurred_at` 不读 `received_at`（代码实证）。

## 5. 边界与红线自查

- 纯 backend 增量，mobile/gateway/proto/迁移零改动；`app/gen` 为 gitignored 复制物未入库。
- 无权限/跨用户/删除复活/假成功语义：unattributed/censored 均为显式不结论，与假成功方向相反；本模块不产不改 `TruthClass`（D-02 唯一权威），I01 透传兼容由构造成立。
- 零模型调用、零费用：纯 stdlib 确定性函数；测试不触 DB/LLM。
- `tasks.json` 状态 `in_progress/REVIEW_READY/PENDING_REVIEW` 与在审状态一致（状态推进归协调面，审查者不代改）。

## 6. 裁决

**APPROVE** —— 三条验收全部红转绿可失败、突变 4/4 亲测可证伪、既有权威字节级零改动、债务双登记落库、复跑与基线同数且新增回归 = 0。C-1…C-4 均非阻塞，不降任何验收阈值。建议集成复验按 fleet 流程在本分支 HEAD 复跑 §1 契约测与守卫归因后收口 DONE_REVIEWED。

---
*审查者：wtD02R1（独立会话，未参与实现）· 复跑与突变均为本机真实执行 · receipt 本身以 commit sha 为准*
