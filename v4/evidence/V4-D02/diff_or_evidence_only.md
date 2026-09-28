# V4-D02 · diff_or_evidence_only

## 语义缺口清单（现状盘点结论，base @ 56c3341c）

| # | 缺口 | 现状证据 | 卡面判据 |
|---|---|---|---|
| G1 | **四域关联无显式分域**：全仓关联键是裸 UUID 平铺——`CorrelationIds`（event_registry.py:538）值域门只验 canonical UUID、不验域；D-05 `linkage_keys` 四键（task_id/plan_id/node_id/intervention_request_id）同样只做 UUID 规整。把 occurrence UUID 填进 task_id 槽（或 `task_occurrence_id` 当 `Task.id`）在结构上畅通无阻 = 伪归因拼接面 | `backend/app/core/event_registry.py:538-580`、`backend/app/core/intervention_lifecycle.py:374-400`；`goal_id`/`occurrence_id` 明文不在 CORRELATION_KEYS（event_registry.py:404 注释） | 「不同 ID 域不能拼接伪归因」「不能把 task_occurrence_id 当 Task.id」（DATA_AND_GRAPH §事件定义） |
| G2 | **unattributed 无公开分母**：D-05 切片仅有 friction/execution_mode 侧 `unattributed` 档；outcome 侧「关联不上」的事件无显式分域 unattributed 计数面，难配对事件可被静默剔除制造高关联率 | `grep -rn unattributed backend/app` 仅 D-05 切片词表 | 「归因不上的显式落 unattributed 分母（公开可查），不静默丢弃或硬塞」 |
| G3 | **观察窗只有 intervention 单锚点**：D-05 `resolve_observation_status` 语义完备（三删失+unknown）但签名绑 exposure；goal/task/occurrence/run 四域无统一入口，各域自造窗口语义的风险在册 | `backend/app/core/intervention_lifecycle.py:429-474` | 「统一 goal/task/occurrence/run 同域关联与观察窗」「超窗未回来不记失败」 |
| G4 | **UI→receipt→event→outcome 链路无还原机制**：receipt_ref→event 身份（D01）、outcome 身份（D-02）各自可重算，但全仓无逐跳重算验证器；链上任一存储行被篡改/丢失无处显式报因 | `grep -rn "trace_receipt\|溯源\|追踪" backend/app` 零命中 | 「任取一条 UI 交互，能沿 receipt_ref→experience_event→outcome 链把随机样本完整还原」 |

## 实现面（一句话）

新增冻结契约模块 `backend/app/core/attribution.py`（`attribution.domain.v1`）：`DomainKey=(域, canonical UUID)` 显式分域键（匹配只认同域+同值，跨域值逐字节相同也判 `domain_mismatch`→unattributed，`task_occurrence_id` 表级钉死只投影 occurrence 域）+ 确定性归因全函数 `attribute_outcome`（窗口内同域匹配才 attributed；`missing_key`/`domain_mismatch`/`no_same_domain_match`/`outside_window`/`broken_row` 封闭理由词表显式落分母）+ `AttributionDenominator` 公开分母（eligible 全集、`unattributed_ratio` 公开、eligible=0 时 ratio=None 不宣称）+ 幂等样本 id `attr_<sha256[:32]>`（重放恒同 id，样本不虚增）+ 统一观察窗门面 `anchor_observation_status`（四域逐值委托 D-05 权威函数，零第二语义）+ 链路追踪验证器 `trace_receipt_to_outcome`（receipt_ref scheme→event_id/dedupe_key 重算（D01 权威）→outcome_id 重算（D-02 权威）→链接语义三选一（outcome:// 直连 / 同域键匹配 / D-05 exposure linkage），逐跳显式报因）。

## 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **未重建 V3**：无新表、无迁移、无 proto、无新事件总线、不改 D-05/D-02/D01 任一冻结词表与行为（`git diff 56c3341c -- backend/app` 仅新增文件；既有文件零改动，`KNOWN_CODE_DEBT_LEDGER.md` 登记行除外）。
- **复用既有权威 4 处（import 期断言钉死，不复制语义）**：观察窗= D-05 `resolve_observation_status`/`clamp_observation_window_hours`（统一门面逐值委托，测试钉四域同输入恒同输出）；用户响应词表= D-05 `USER_RESPONSE_EVENT_TYPES`（edited 显式成员，`edited` 与 `accepted` 事件身份不同测试钉死——DATA_AND_GRAPH「不填假 accepted」在 V3 已满足，本卡举证不重做）；outcome 身份= D-02 `derive_outcome_id`；呈现事件身份= D01 `derive_dedupe_key`/`derive_experience_event_id` + `EXPERIENCE_RECEIPT_REF_SCHEMES`。
- **新增仅 2 文件**：`backend/app/core/attribution.py`（717 行，含模块 docstring 冻结声明与 import 期断言）+ `backend/tests/core/test_attribution.py`（560 行，38 测）；登记行 1 处（`docs/engineering/KNOWN_CODE_DEBT_LEDGER.md` P3 #13，BJ 豁免双登记）。
- **I01 透传兼容（任务上下文要求）**：本模块不产、不改 `TruthClass`（真相唯一权威=D-02 账本）；censored/unknown 复用 D-05 `ObservationStatus` 原词表五值——`last_valid_outcome.truth_class`（B05 §5 全 5 值 1:1 透传、demo 含）语义不受影响，兼容由构造成立。

## 与验收逐条对照（可失败 = 每条有红转绿反例 + 突变注入演示）

1. **不同 ID 域不能拼接伪归因；unattributed 公开分母** —— 红转绿：`test_identical_uuid_across_domains_never_links` / `test_cross_domain_verdict_is_unattributed_domain_mismatch`（同 UUID 跨 task/occurrence 域 → `domain_mismatch`，不归因）；`test_task_occurrence_id_only_projects_to_occurrence_domain` + import 期断言（`task_occurrence_id` 永不入 task 域）；`test_missing_key_is_unattributed_not_forced_not_dropped` + `test_denominator_counts_every_eligible_event`（3 eligible=1 归因+2 unattributed，ratio=2/3 公开、难配对事件全在分母）。突变注入①：把 `links()` 改成裸值比较 → `TestCrossDomainSpliceRejection` 立红（1 failed），还原后 38 绿。
2. **超窗未回来不记失败；重复回放不加样本** —— 红转绿：`test_outcome_beyond_window_is_outside_window_and_anchor_censored`（73h outcome → `outside_window` + 锚点 `censored_window_closed`，判定面无任何 failed/negative 语义位）；`test_window_not_yet_due_is_censored_not_failure` / `test_churned_user_after_window_is_censored_churned`；`test_delayed_outcome_within_window_is_attributed`（延迟 outcome 窗内照常归因）；`test_replay_produces_identical_verdict_and_sample_id` + `test_consumer_dedup_by_sample_id_counts_once`（5 次重放 → 1 个唯一样本 id）。突变注入②③：超窗照常归因 → 2 红；sample id 混入 now → 重放幂等测红。
3. **UI→receipt→event→outcome 随机追踪可还原** —— 红转绿：`test_random_sample_full_chain_restore`（uuid4 随机样本，真实 D01 投影事件 + 真实 D-02 outcome id，四跳全 ok、重跑 trace 恒同）；篡改/断链各跳均有显式报因反例（`test_mutated_event_breaks_chain_loudly` 等 5 条）。突变注入④：trace 跳过 event 身份比对 → `test_mutated_event_breaks_chain_loudly` 立红。

## 红线自查

- 纯 backend：mobile/ 与 gateway/ 零改动（git status 佐证）。
- 零 HEAVY、零模型调用：纯 stdlib 确定性函数；测试无 DB 依赖（`tests/core` 纯函数面），不触真库、不调模型、零费用。
- 无权限/跨用户/删除复活/假成功变更：模块无权限语义字段；unattributed/censored 均为「显式不结论」，与假成功方向相反。
- 已知债务如实登记：attribution.py 生产消费面本卡零接线（BJ 豁免 + KNOWN_CODE_DEBT_LEDGER P3 #13 双登记，消费卡序 = V4-D03/V4-D05）。
