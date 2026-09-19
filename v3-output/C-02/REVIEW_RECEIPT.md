# C-02 REVIEW_RECEIPT · R1 标准验收（general 路线）

- 验收人：V3 Fleet R1（独立重验，不采信 Worker 自报）
- 验收时间：2026-09-19
- 对象：wt9 @ db652302 基线 + 未提交工作区改动（3 modified + 3 new files + v3-output/C-02/）
- 测试环境：借用 `/Users/brsama/code/GitHub/sparkle-cosmos/backend/.venv`（只读，PYTHONDONTWRITEBYTECODE=1）；
  DB 全部为 conftest 内存 sqlite（`tests/conftest.py:117` TEST_DATABASE_URL），未触碰主仓 dev DB；未起任何服务进程。
- 注：验收时为运行测试从主仓拷入 `backend/app/gen/`（gitignored 生成物，proto 在 db652302..1ea854c9 零漂移，
  `git diff --stat db652302 1ea854c9 -- proto/` 为空），验收完成后已删除，worktree 恢复交付态。

## 1. 逐断言 Verdict

### A1 改动面与自报清单一致、无夹带 — **ACCEPT**

- `git -C wt9 status`：恰好 3 个 modified（settings.py / context_pack.py / context_builder.py）+ 3 个 untracked
  （context_sources.py + 2 个测试文件）+ v3-output/C-02/，与自报完全一致，无其他文件被动。
- 密钥扫描：新文件 grep api_key/secret/password/bearer/AKIA/PEM —— 仅 `test_context_pack_sources.py:37`
  `hashed_password="test"`（测试夹具，无泄露）。无 `/Users/brsama` 绝对路径引用（EXIT:1）。
- `changes.patch` 完整性：与实际工作区 diff 逐行比对——modified 部分（529 行）逐字节一致，三个新文件 hunk
  均完整包含在 patch 内（`/dev/null → file` 生成对比验证 OK×3）。
- settings.py 中 JWT/AURORA_BAYESIAN 等无关行变更为 black 注释对齐归一（语义零变化，REPORT §8 已披露）。
  context_builder.py 头部 import 排序/行宽调整同为格式化，无逻辑变化。

### A2 四类封闭词表 + 四独立开关 + 计量 adapter 真实落地 — **ACCEPT**

- 封闭词表：`context_sources.py:68` `SOURCE_CATEGORIES=("state","memory","knowledge","events")`；
  `:76-85` `SOURCE_CATEGORY_BY_ITEM_TYPE` 与 C-01 冻结集精确等值——测试
  `test_every_decision_item_type_maps_to_a_category` 断言 `set(...) == set(DECISION_ITEM_TYPES)`
  （独立核对 wt9 `app/core/decision_context.py:63`：6 个 item type，全覆盖）；未知 type 走
  `item_source_category` KeyError（`:184-186`）+ pack 侧 unknown item 警告跳过（context_pack.py manifest 构建）。
- 四独立开关：`settings.py:660-663` `ENABLE_CONTEXT_SOURCE_{STATE,MEMORY,KNOWLEDGE,EVENTS}` 默认 True；
  `test_adapter_switches_default_on_and_independent` 验证关 state 不影响 memory。
- token/项数计量：`SourcedItem.item_count/token_estimate`、`SourceSection` 聚合属性、
  `build_payload_source_manifest` 逐 key 计量（:794-814），生产路径注入 `context_pack.estimate_tokens`
  （context_builder.py `_attach_source_manifest`），默认 `len//4` 降级保证模块独立可测。
- 两条路径统一词表：pack 侧 `_build_source_manifest`（context_pack.py:1744+）与 orchestrator 侧
  `build_payload_source_manifest` 均从同一模块取 `SOURCE_CATEGORIES/SOURCE_SCHEMA_VERSION/adapters/开关`，
  schema_version 同为 `context_sources.v1`。✅ 统一成立。
- KEY_CATEGORY_MAP 33 个 payload key 全登记 + `control` 显式桶 + unclassified 告警（:879-885）；
  `test_payload_manifest_unknown_keys_do_not_silently_land` 钉住 mystery_key 落 unclassified。

### A3 测试真实性（实际运行）— **ACCEPT**

- 新增测试实跑：`pytest tests/unit/test_context_sources.py tests/unit/test_context_pack_sources.py -q`
  → **34 passed in 15.09s**（30 单元 + 4 sqlite 集成，与自报数字一致）。
- 断言钉真实行为（非同义反复）抽查：
  - `test_pack_carries_four_category_source_manifest` 断言
    `memory.token_estimate == pack.token_usage["preferences"] + pack.token_usage["episodic"]`（真实不变量）；
    memory item_count==3（1 pref + 2 episodic）、seed_or_demo==1（startup_seed 条目）与种子数据对应。
  - `test_pack_telemetry_carries_sources`：从 sqlite 回读 `context_pack_runs.memory_counts["sources"]`
    四类齐全，且 `normalize_memory_counts(...)` 等于三已知 key 之和（兼容性钉死）。
  - `test_apply_memory_prefilter_delegates_when_module_present`：捕获 RetrievalContext kwargs，
    断言 `purpose=="llm_context"`、`plan_ids=={"p1"}` 传参正确（真委托语义）。
- 红测语义抽查（A6 一并结论）：两例 characterization 红测（`test_red_flat_dict_merge_silently_drops_local_value` /
  `test_red_preference_records_same_key_collapse`）本身在缺陷代码上即通过——它们锁定缺陷现状而非失败用例；
  文件级"红态"来自模块不存在时 import 失败（ModuleNotFoundError），成立。Worker 已如实披露该性质（REPORT §4）。

### A4 回归套件 — **ACCEPT**（两处计数与自报不符，全绿事实不受影响）

实测（全部 passed，除注明外）：
- `tests/contract/test_decision_context_contract.py`：**15 passed**（与自报一致）。
- `tests/contract/test_event_registry_contract.py`：1 failed（state_aggregator，见 A5）+ 46 passed。
- context_pack 家族 8 文件（pack/conflicts/ranking/personalized_ranking/rollout/feedback/budget_manager/focusing）：
  **33 passed**；+budget_scheduler=34。自报 "45✓" 与实测口径不符（疑含额外文件），但全绿结论成立。
- `tests/unit/orchestrator/`（含 mixins）：**125 passed**（仅 mixins/ 目录为 111）；自报 "127✓" 与实测目录口径不符，全绿成立。
- `tests/test_context_pruner.py + tests/unit/test_rule_as_guard.py`：4 passed, 8 skipped。
- lint 实跑：black --check(120) 6 文件全过；ruff check 新 3 文件全过。

### A5 预存失败归因（抽查 ①，深验）— **ACCEPT（确属预存）**

- 失败点：`test_event_registry_contract.py:379` 对 `app/state_aggregator/service.py` 全文做
  `"tracking_events" not in source` 子串守卫；该文件 :530 在**注释**里含
  `# ... from stream:tracking_events and by the` —— 守卫把注释当引用，属误报。
- 归因证据：`git show db652302:backend/app/state_aggregator/service.py | grep -c tracking_events` → 1
  （基线即含该字符串）；`git diff db652302 -- <该文件> <测试文件>` → 0 行（两者均未被 Worker 触碰）。
  该失败在 clean 基线必然复现，与 C-02 改动无关。②RB-06、③K/Z/BG 守卫未逐个深验（Worker 归因为
  环境/无生成物，性质类似且与本卡改动面无交集），不影响总 Verdict。

### A6 契约一致性 — **ACCEPT**

- **D-01**：`decision.recorded` 确在 wt9 `app/core/event_registry.py:182`：status="reserved"、
  producers=("v3: decision_records read projection",)、stage=DECISION——与 Worker 描述逐字一致；
  `event_name_for_decision_record` 经 `is_registered_event_name`（:395）校验，撤名抛 LookupError →
  EventSourceAdapter 降级标记（degraded note），绝不静默换名（context_sources.py:205-214, 714-749）。
  `EVENT_SCHEMA_VERSION`（:73，"event.v1"）盖章进 manifest（:896）。语义正确：适配器是 decision_records
  读投影的消费方标注，不产出新事件、不越 reserved 语义。
- **C-01**：SOURCE_CATEGORY_BY_ITEM_TYPE 与 DECISION_ITEM_TYPES 精确等值（A2）；goal→state 有
  USER_WORLD_MODEL §1 依据并写进代码注释与测试名；events 条目不进冻结 items，不越权改 C-01 契约面。
- **M-03 兼容（重点核对项）**：主仓 @1ea854c9 `memory_retrieval_prefilter.py` 实测——
  `RetrievalContext(user_id: str, purpose: str, now: datetime, goal_ids, task_ids, plan_ids, domain_keys,
  task_type, session_id, ...)`（:238-250）与 Worker 传参逐字段匹配；`purpose="llm_context"` ∈
  RETRIEVAL_PURPOSES（:158）；`prefilter_candidates(candidates, ctx)`（:601）与 Worker 调用形状一致；
  返回 `PrefilterResult.allowed/.rejections`（:291-293）与 Worker 读取字段一致；
  `MEMORY_PREFILTER_VERSION`（:73）经 getattr 读取。**透传/调用兼容性成立，M-03 已合入时零改动生效。**
  委托失败有 except Exception 兜底透传（:557-561），符合 M-03「指标不破坏检索」。
- **seed/demo 口径 vs 实际写方**：`guest_seed_service.py:233` registration_source="seed"、
  `simulation_runner.py:303` ="system"、`app/api/v1/auth.py:878` ="guest" —— {seed,system,guest} 三值
  与既有写方一致；`guest_seed_service.py:171` source_type="startup_seed" 与条目级口径一致。
  与 B-02 卡验收项「seed/demo namespace 与真实 cohort 可被查询区分」对齐：manifest 输出
  user_is_seed_or_demo + 每类 seed_or_demo 计数 + seed_or_demo_items，且 telemetry JSONB 可 SQL 查询
  （REPORT §6 的验证 SQL 形状与实际 JSONB 结构相符——已由 test_pack_telemetry_carries_sources 从
  sqlite 回读验证同构）。
- **normalize_memory_counts 兼容**：主仓 `understanding_depth_metric_service.py:60-70` 只对
  ("preferences","goals","episodic") 三个 key 做 `isinstance(value,(int,float))` 求和——附加的 "sources"
  为 dict，被自然跳过，行为不变。集成测试断言钉死（A3）。
- **无覆盖保证**：红测为普通通过型 characterization 测试（非 xfail/skip/注释），不阻塞任何测试运行；
  机制面（SourceRegistry 覆盖登记+WARNING、detect_merge_overrides 接 grpc 合并面、
  detect_preference_key_overrides 接非 resolver 分支、LATE_STAGE_WRITERS 静态溯源）由 30 个单测中的
  Part 1/9/10 钉死。`GRPC_MERGE_KEYS=("next_actions","active_plans","focus_stats","recent_progress")`
  与 `_merge_user_contexts`（context_builder.py:311-333）实际覆盖键逐字核对一致。
- **rule-as**：`# rule-as: ignore` 为该守卫既有约定（test_rule_as_guard_allows_explicit_ignore 验证
  约定合法）；带 ignore 标签后 `test_rule_as_guard_passes_on_repo` 实跑通过。

### A7 orchestrator 侧装配安全 — **ACCEPT**

- `_attach_source_manifest` 置于 stage39 之后（context_builder.py:1057-1062），纯 metadata 面：
  payload 既有 key 值零改动（`test_attach_source_manifest_degrades_without_db` 断言 active_plans/
  episodic_memories 原值不变）；provider 读双 try/except 只降级该输入（DB 不可用测试覆盖）。
- grpc 合并面 override 附加有 `isinstance(... , dict)` 双重守卫（manifest 附加失败时不崩）；
  history 附加同样守卫 + copy-on-write（原 manifest 不被污染，有测试）。
- `select` 于 context_builder.py:25 已导入；`DecisionRecordService.get_recent_records(user_id, limit=3)`
  与 wt9 既有签名（:46, limit=10 默认）兼容；`ContextPruner.summary_recent_window=4`（:45）存在。

## 2. 必修项清单

**无 C1（阻断）/C2（合入前必修）项。**

- C3-1（报告口径）：REPORT 自报 "context_sources.py ~640 行"（实际 941 行）、"context_pack 全家族 45✓"
  （实测同清单 33/34）、"mixins 目录 127✓"（实测 mixins/ 111、unit/orchestrator/ 125）。全绿结论不受影响，
  但后续卡的行数/计数自报应与实测口径对齐。
- C3-2（测试可读性）：`test_context_pack_sources.py:105-109` 的 `assert A or B` 结构冗余（B 为有效断言），
  建议合入时简化为单条件。
- C3-3（移交守卫维护方，非本卡）：rule-as 守卫违规项打印路径硬编码为 profile_context_service（REPORT §9
  已报）；D-01 守卫注释误报（A5）建议 D-01/state_aggregator 维护方将守卫改为 strip 注释或改词。

## 3. 总 Verdict

**ACCEPT**（可直接合入；C3 项不阻塞，随合入或后续卡处理）

四类封闭词表、四独立开关、计量 adapter、双路径统一 manifest、覆盖显式化、seed/demo 口径、
M-03 前向兼容、telemetry 兼容全部独立复核成立；34 新测试 + 全部抽查回归实跑通过；
唯一抽查的预存失败经基线证据确证与本次改动无关。
