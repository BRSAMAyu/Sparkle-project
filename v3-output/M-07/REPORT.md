# M-07 Correction/Delete/Revocation + Memory Epoch 终局 — 执行报告

worktree: `Sparkle-sysrev/wt8 @ 10fde918`（基线）→ 本卡改动见 `changes.patch`（9 个文件：2 新增 + 7 修改）
gate: V3-2 ｜ stream MEMORY ｜ risk **critical** ｜ reviewers_required=2 ｜ locks: memory-semantics + privacy-delete ｜ 禁 commit/push（已遵守）

## 0. 六句总结

统一删除语义的落点是单一管线模块 `backend/app/services/memory_invalidation_pipeline.py`：correction(reject/no_longer_applicable)/revoke(用户删除+retract)/supersede(偏好版本推进)/bulk_revoke 四动作全部改为「状态变更 + 审计 + epoch bump + `memory.invalidated` 事件」**同事务原子生效**（M-01 的 best-effort 缺口就此关闭），提交后异步 DEL 派生缓存（profile_context / inline_snapshot / prefs_center / aurora self_model）。derived 不复活的关键修复有两个：①记忆面板删除偏好此前**不摘 live `user_preferences` 键**，ProfileContext/UserInsightCompiler 会永久复活已删值——现在链头删除在同一事务内摘 live 键并递增 preference_version（红→绿实证）；②ProfileContext 缓存与 inline snapshot 新增 **memory_epoch 读侧门**（E-05 version-key 先例），即使失效 DEL 失败/竞态，epoch 不一致的旧 derived 快照也会被拒绝（fail-closed，含 epoch 读失败场景）。幂等/并发：四个入口统一 `SELECT ... FOR UPDATE` + `derive_status != active` 复查，重复删除/双设备重试收敛为恰一次 epoch bump、一条审计、一条事件（行锁持有期间无中间提交，C2 锁保护不被破坏）。事件词表按 D-01 扩词表流程登记 `memory.invalidated`（STATE_UPDATE，aggregate=user_memory）并重冻 sha256（33→34 名），CorrelationIds 增补辅助键 `memory_id`；事件 payload **内容无关**（只有 ids/action/epoch，无 summary/reason 明文）。红绿证据：17 项新测试先 13 RED（4 项为既有行为钉桩）后 17/17 GREEN；受影响面回归 7 个测试文件 73 通过 + 3 项失败经 git stash 对照证实为基线预存（state_aggregator 遥测守卫、inferred-lane embedding retry、ltm e2e 连 dev Postgres 认证失败——均为环境性）。M-03R2 前置项 F4/F5 因 M-03 返修代码不在本树，登记说明见 §7（不可修补未合入代码，Leader 随 M-03R2 落地）。

## 1. 问题与目标

任务卡目标：用户纠正/删除贯穿派生状态、缓存和后续检索——删除后 retrieval/cache/context 新请求 0 使用；旧 derived summary 不复活；双设备/重试/重复删除幂等；审计保留事实但不暴露内容；in-flight 当前轮不回滚、下一轮零使用。

### 勘察发现的实质漏洞（红态实证，非理论）

1. **派生复活主通道（最严重）**：记忆面板删除偏好走 `retract_memory(kind=preference)` 只撤 `memory_preferences` 链；而 ProfileContext → UserInsightCompiler → 全部提示词装配的偏好真源是 live 表 `user_preferences`（`PreferenceService.get_preferences`）。删除后 live 键原样保留 → **每次编译永久复活已删偏好**（不是 TTL 问题，是双存储不同步）。测试 `test_memory_panel_preference_delete_removes_live_value` 红态证实。
2. **epoch 是 best-effort**：M-01 已把 bump 接到四个删除入口，但 `_bump_epoch_best_effort` 吞掉 `NON_CRITICAL_SERVICE_ERRORS`——bump 失败时缓存失效链整条静默丢失；且 bump 在状态变更提交**之后**独立提交，存在「已删除未 bump」窗口。
3. **重复删除不幂等**：`revoke_episodic_memory` 二次调用会重写 `revoked_at`、`correction_count+1`、再写一条 `MemoryCorrection(action=delete)`、再 bump 一次 epoch（红态实测：两次删除 epoch +2、审计 2 行）。
4. **派生缓存无 epoch 门**：`user:profile_context:{uid}` 只校验 `preference_version`（episodic 删除不改变它）；`user:inline_snapshot:{uid}` **无任何版本门**（120s TTL 内照常复活）；`aurora:self_model:{uid}` 90 天 TTL，删除后假设残留一个学期。
5. **无 invalidation 事件**：D-01 词表无 `memory.invalidated`，删除事实不进事件域，在途运行/跨服务消费者无从感知。
6. 次要：衰减批任务 `memory_jobs` 不过滤 revoked/retracted 行（已删记忆仍被后台触碰）。

## 2. 设计（核心决策）

### 2.1 单一管线：`memory_invalidation_pipeline.py`

```
MemoryInvalidationPipeline(db, redis).apply_in_txn(
    user_id, action ∈ {correction, revoke, supersede, bulk_revoke, working_memory_forget},
    kind, memory_ids, reason_code) -> MemoryInvalidationResult(epoch, keys, event_written)
```

每个**有效**变更（真正把记录移出 active 态；幂等重复是 no-op）确定性触发，且 **epoch bump 与事件写入在调用方事务内**（flush 而非 commit）：

- **原子性**：状态变更、审计行、epoch bump、invalidation 事件同事务 all-or-nothing。不存在「已删除未 bump」或「bump 了但没删」的中间态。
- **锁纪律**：bump 不再有独立 commit，`upsert_preference` 的 SELECT FOR UPDATE（C2 修复）持有到最终提交，不被中间提交破坏。
- **顺序**：提交后 DEL 派生缓存（加速），读侧 epoch 门（保证）兜底——DEL 失败只剩 TTL 有界陈旧 + 门拒绝，方向安全。
- epoch bump 复用 M-01 的原子 `UPDATE..RETURNING` + 懒建语义（`_bump_memory_epoch_in_txn`），并发首撞 unique 让事务整体中止、客户端重试经幂等守卫收敛。

### 2.2 幂等与并发（验收 ②）

四个入口统一模式：`SELECT ... FOR UPDATE` → `derive_status(record) != active` 则返回当前记录（no-op）。PostgreSQL 上第二个并发调用阻塞到首个提交后重读，看到终态即 no-op；重试/重复删除同理。效果 = 恰一次 epoch bump、一条 `MemoryCorrection` 审计、一条事件（测试逐项断言）。语义收紧说明：对已处于 superseded/terminal 的链中历史版本执行 retract 现在是 no-op（此前会改写其 retracted_at）——终态行不再被二次变更，与状态机优先级一致。

### 2.3 derived 不复活（验收 ①）

| 消费面 | 处置 | 证据 |
|---|---|---|
| live `user_preferences`（ProfileContext 偏好真源） | **修**：链头删除同事务摘 live 键（按 provenance 分 explicit/inferred 桶）+ version+1 → 下游 version 门自动失效。仅当被删行仍是活跃链头（摘键不误伤更新的版本） | `test_memory_panel_preference_delete_removes_live_value` 红→绿 |
| UserInsightCompiler（canonical profile 所有权） | 消费 ProfileContext；受 epoch 门 + DEL + live 摘键三层保护，重编译即拉新真源 | `test_profile_context_cache_rejected_after_epoch_bump` 红→绿 |
| ProfileTruthCompiler | 适配 ProfileContext/UserInsightState，同上传递保护 | 同源，无独立存储 |
| inline snapshot（`user:inline_snapshot`） | **修**：写入钉 `memory_epoch`，读取 fail-closed 门（缺 epoch 或不一致 → None → 重编译）；epoch 读失败也 fail-closed 到 0 | `test_inline_snapshot_stale_after_epoch_bump` 红→绿 |
| Aurora self-model（`aurora:self_model`，90 天 TTL） | **修**：每次有效变更主动 DEL（TTL 一个学期不可接受） | `test_aurora_self_model_cache_cleared_on_delete` 红→绿 |
| semantic_cache | **豁免（如实登记）**：仅缓存 GraphRAG 知识节点检索结果（`hybrid_search`→knowledge_version 版本键 + user_id 严格可见域），从不持有记忆内容，删除无物可复活。另提供 `memory_epoch_version_string()`（E-05 模式）供 M-03 检索预筛/未来记忆敏感缓存方组键 | 代码证据 `semantic_cache_service.py`（cache_result 只序列化 KnowledgeNode） |
| nightly_review | **豁免**：输入仅 ErrorRecord + UserStateSnapshot（`nightly_review_service.py` imports/generate_for_user），不含 episodic/preference 内容 | 源码核对 |
| understanding_depth 聚合 | **豁免**：纯计数指标（context_pack_runs 注入条数、memory_corrections 行数），无内容载荷；删除本身计入当日纠错计数属预期语义 | `understanding_depth_metric_service.py` §表格 |
| state_aggregator（reflections/WM snapshot） | episodic 反思查询已过滤 revoked/retracted（service.py:335-346）；WM snapshot 每请求重建、仅进程内 30s 缓存（即 in-flight 豁免界） | 源码核对 |
| 衰减/归档批任务 | **修**：select 增加 `revoked_at IS NULL AND retracted_at IS NULL`，终态行不再被后台触碰 | `memory_jobs.py` |

### 2.4 事件词表（D-01 扩词表流程）

- 登记 `memory.invalidated`：stage=STATE_UPDATE，aggregate_type=`user_memory`，producer=`memory_invalidation_pipeline.py`，status=live。冻结 sha256 从 33 名**有意** bump 到 34 名（`_FROZEN_VOCABULARY_SHA256` 更新 + 注释说明）。
- `CorrelationIds`/`CORRELATION_KEYS` 增补辅助因果键 `memory_id`（沿用 task_id/session_id 等 auxiliary 先例；`test_correlation_ids_keys_match_contract` 两侧一致性测试保持绿）。单条删除 correlation 带 memory_id；批量事件 memory_ids 全量进 payload。
- **隐私**：payload = `{schema_version, memory_type, action, memory_ids, memory_epoch, reason_code(≤40 动作码)}`——无 summary、无 pref_value、无用户 reason 原文。审计侧 `MemoryCorrection` 本就只存 action/reason（用户自述、租户内可见），事件侧新增的是零内容事实记录（SECURITY_PRIVACY「审计保留不暴露内容」口径）。测试断言敏感原文不出现在 payload。

### 2.5 缓存/上下文零使用（验收 ①'）与 in-flight（验收 ⑤）

- 读路径硬过滤（M-03 前已有）：`list_recent_episodic`/`get_recent_episodic`/`list_preferences`/`find_preference`/state_aggregator 反思查询的 SQL 均排除 revoked/retracted——context_builder(stage34)/context_pack 的装配数据源即这些方法。测试钉桩：删除后 `list_recent_episodic` 0 返回、bulk 后空集。
- working_memory（Redis 即真源）：forget 直接删键、reject 置位且 `list_entries`/`build_snapshot` 默认过滤（钉桩测试）；面板 forget 端点接管线（epoch+事件+DEL，`apply_working_memory_forget`）。WM 无跨请求版本化快照可门控——这是与 semantic_cache 不同的形态，按真源直接失效处理并登记。
- in-flight：当前轮已注入引用不被追改（`test_inflight_current_turn_snapshot_is_not_rolled_back` 钉住不抛错、已注入快照不变），下一轮装配 0 使用（上一条钉住）——声明式验收成立。

## 3. 改动清单（`changes.patch`，9 文件）

| 文件 | 改动 |
|---|---|
| `backend/app/services/memory_invalidation_pipeline.py` | **新增**：统一管线（apply_in_txn / invalidate_derived_caches / apply_working_memory_forget / memory_epoch_version_string / 事务内 epoch bump / outbox 事件写入） |
| `backend/app/services/memory_service.py` | 四入口接线：`retract_memory`（FOR UPDATE+幂等守卫+审计+live 摘键+管线）、`revoke_episodic_memory`（同）、`apply_correction` reject 分支（同）、`revoke_inferred_memories`（每用户一次 bump+一条聚合事件）、`upsert_preference` supersede 分支（管线，首写不 bump）；删除 `_bump_epoch_best_effort`；新增 `_remove_live_preference_key_in_txn` |
| `backend/app/core/event_registry.py` | 登记 `memory.invalidated` + CorrelationKeys 增 `memory_id` |
| `backend/app/core/profile_context.py` | `ProfileContext.memory_epoch: int = 1` |
| `backend/app/services/profile_context_service.py` | 缓存门 = preference_version ∧ memory_epoch；inline snapshot 写入钉 epoch、读取 fail-closed 门；`_get_memory_epoch`（读失败 fail-closed 0） |
| `backend/app/api/v1/memory.py` | WM forget 端点接 `apply_working_memory_forget` |
| `backend/app/services/memory_jobs.py` | 衰减批任务过滤终态行 |
| `backend/tests/contract/test_event_registry_contract.py` | 冻结 sha 有意 bump（33→34）+ 注释 |
| `backend/tests/unit/test_memory_invalidation_pipeline.py` | **新增**：17 项红绿测试（词表 2、幂等 3、硬保证/事件 3、derived 不复活 5、零使用 2、in-flight 1、pin 1） |

无迁移（epoch 三列 M-01 已上线；事件走既有 event_outbox/event_sequence_counters 表；`ProfileContext.memory_epoch` 是带默认的 pydantic 字段，旧缓存 payload 解析默认 1、任何 bump 后即失配被拒）。

## 4. 红绿证据

- **红态**（实现前运行）：`17 collected → 13 failed, 4 passed`（4 项为既有行为钉桩：零使用检索、WM 过滤、in-flight 不回滚 + bulk 零使用其一）。
- **绿态**（实现后）：`17 passed`（`pytest tests/unit/test_memory_invalidation_pipeline.py`，sqlite in-memory + FakeRedis，hermetic 不触 dev Redis）。
- 实现中还抓到并修复一个**真实生产 bug**：`invalidate_derived_caches` 初版是同步方法，异步 Redis 的 `delete` 协程从未被 await——缓存 DEL 在生产会静默不生效（测试经 FakeRedis 暴露 `RuntimeWarning: coroutine ... never awaited`）。已改 async 并 await。
- 测试隔离 bug 一并修复：outbox 表存在性的模块级缓存在 per-test 内存库间串味，改为每次检查（galaxy 先例）。

## 5. 回归与验证

串行单文件执行（内存纪律：swap 空闲 ~1.0G，未起模拟器/浏览器/全库测试；真实 LLM 0 次）：

| 文件 | 结果 |
|---|---|
| `tests/unit/test_memory_invalidation_pipeline.py` | 17 passed |
| `tests/contract/test_event_registry_contract.py` | 31 passed, 1 failed（**基线预存**，见下） |
| `tests/unit/test_memory_inference_write_guard.py`（M-01） | 8 passed |
| `tests/unit/test_memory_epistemic_contract.py`（M-01） | 11 passed |
| `tests/unit/test_conflict_resolver_epistemic_guard.py`（M-01） | 3 passed |
| `tests/unit/test_working_memory_rejection_guard.py` | 3 passed |
| `tests/unit/test_memory_inferred_write_lane.py` | 6 passed, 1 failed（**基线预存**） |
| `tests/integration/test_ltm_e2e.py` | 2 failed（**基线预存**：asyncpg 连 dev Postgres 认证失败） |
| `tests/unit/test_chat_signal_collector_profile_loop.py` / `test_aurora_control_surface_service.py` | 2+2 passed |
| 治理守卫 | `--rule AC` PASS；全量 run K/Z 失败为 **worktree 环境伪影**（守卫脚本把 `app/gen` 解析到主仓路径，stash 后基线同样失败） |
| black / ruff（8 个改动文件） | 全部通过（memory_service 一处预存 import 序序顺手修复） |

**基线预存失败对照法**：每项失败均 `git stash` 后在干净树上复现相同失败再 `stash pop`，证实与本卡无关。3 项分别是：state_aggregator 遥测守卫（V3-FIX-11 已知跟进域）、inferred-lane 测试的 embedding RetryError（60s 超时环境性）、ltm e2e 的 dev Postgres 密码认证（集成环境凭据）。

## 6. 残留风险与边界（如实）

1. **派生缓存 DEL 后到 epoch 门生效前**：理论上无窗口（门与 DEL 同时上线）；若 Redis 完全不可用，DEL 与 epoch 读都失败 → epoch 读 fail-closed 0 → 缓存一律拒绝重编译（正确性优先，代价是 Redis 故障期编译频率上升）。
2. **Postgres 并发删除**：FOR UPDATE + 终态复查在 sqlite 单连接下只能验证串行收敛（重复/重试路径）；真双设备并发依赖 PG 行锁语义，逻辑上等价（锁持有到提交、无中间提交），未做双连接 PG 实测（dev DB 只读纪律）。
3. **`memory.invalidated` 消费者**：当前为事件域事实记录（D-01 台账语义），尚无在线消费者订阅它做主动失效——本卡的保证由 epoch 门 + DEL 直接兑现，事件为 C-07（在途重授权）与后续异步消费者预留。gateway 侧 `processed_events` 的 `evt_` 前缀解析问题是 D-01 已登记跟进项，未在本卡范围。
4. **测试对 dev Redis 的既有污染**：修复前的一次中间运行里 `apply_correction` 用真实 cache_service.redis 写了 ~4 个 `aurora:self_model:{随机测试UUID}` 键（90d TTL，无功能影响；红线禁止在共享 Redis 上按模式删除，未清理，如实登记）。测试现已 monkeypatch 该副作用，后续运行 hermetic。
5. **`docs/product/stage22_prompt_coverage_baseline.md`**：跑某回归测试时被自动审计改写时间戳，已 `git checkout` 还原，不在 patch 内。

## 7. M-03R2 前置项处置（F4/F5）——登记说明

- **F5（settings 读失败 fail-open 不对称）**与 **F4（today-only UTC 切日对 UTC+8 失效）**：均位于 M-03 检索预筛（`memory_retrieval_prefilter`）代码内，该卡在另一 worktree 返修中，**未合入本树**（本树 grep 无该符号）。不可修补不存在于本基线的代码；若在本树造同名实现会在 M-03 合入时形成双真源冲突。
- 建议：Leader 在 M-03R2 合入时执行（其接口约定已对齐：本卡提供 `memory_epoch_version_string()` 供其组缓存版本键；status 维度沿用 M-01 `derive_status`）。若 M-03R2 合入后仍缺这两项，转入 M-04 前置卡清单。
- 本树内可核的相邻事实：写路径 `MemoryPolicyEvaluator` 对 settings 行缺失返回 allowed=True（缺失即默认，非读异常 fail-open）；读异常会向上抛（写路径实际 fail-closed）。不对称若确指读路径异常吞并，只能在其返修代码里修。

## 8. 结论

统一管线 + epoch 门 + live 摘键 + 幂等守卫 + 内容无关事件全部落地并红绿验证；验收 ①②③⑤ 均有测试锚定，④（cache/context 零使用）由读路径 SQL 硬过滤（钉桩）+ 派生缓存 epoch 门（红绿）共同构成。无迁移、无 schema 变更、无第二真源。

STATUS 之外的执行细节：报告与 patch 位于 `v3-output/M-07/`；未 commit/push；`git add -N` 仅用于让新文件进 patch（intent-to-add，未暂存内容）。

## 9. R1+R2 返修记录（2026-09-19 rework，对两路验收 CHANGES 裁决的逐项闭环）

返修基点：wt8 @ 10fde918 上的原交付（1399+/124-）+ 双路回执（`REVIEW_RECEIPT.md` R1 / `REVIEW_RECEIPT_2.md` R2）。R1 的 C1 = R2 的 P1（同因同象），C2-1..C2-4 对应 R2 P2-4/P2-3/P2-1/P2-2。返修后 patch 规模 1689+/127-（新增 3 项回归测试 + 1 项加固）。

### 9.1 C1（P1，阻断合入）— supersede 链后删链头 live 键不摘除

- **修复**：`_remove_live_preference_key_in_txn` 链头查询补 `MemoryPreference.replaced_by_id.is_(None)`（memory_service.py）。按 M-01 契约 `derive_status` 对齐语义：`replaced_by_id` 置位（等价 episodic 侧 `superseded_by_id`）= SUPERSEDED 终态，不是活跃链头；「设值→改值→删链头」这一最常见产品流下，head-check 不再命中被顶替的旧版本，live 键正确摘除。
- **回归**：采纳 R2 探针 #1（`r2_probe1_supersede_chain_test.py`）为 `test_preference_delete_after_supersede_chain_removes_live_key`（set 0.6 → 0.8 → delete v2 → live `explicit["depth_preference"]` 必须消失，含 `head.version == 2` 前置断言）。
- **变异击杀实证**：删除该过滤行 → 回归测试 FAILED（restore 后 20/20 GREEN）。

### 9.2 C2-1（P2-4）— epoch 门测试未钉住（变异 M1 存活）

- **修复**：`test_profile_context_cache_rejected_after_epoch_bump` 采纳 R2 探针 #2（`r2_probe2_epoch_gate_test.py`）构造——monkeypatch `PreferenceService.get_preference_version` 返回 7，与构建时 fake `_get_preferences` 的 version=7 **一致**，使 preference_version 门恒通过，唯一能拒绝 stale 缓存的只剩 epoch 条件（旧构造 fake version=7 vs 门读真实 DB 默认 0，版本失配先行拒绝，epoch 条件从未参与——R1/R2 双路变异实证）。
- **变异击杀实证**：删除 `and context.memory_epoch == current_epoch` 门条件行（R2 变异实验 M1 同款）→ 该测试 FAILED（旧版此变异下 17/17 仍绿）；restore 后 20/20 GREEN。「DEL 失败也不复活」硬保证脱离零有效测试状态。

### 9.3 C2-2（P2-3）— bulk 入口无行锁无终态复查

- **修复**：`revoke_inferred_memories` select 补 `.with_for_update()` + 行锁内逐行 `derive_status(...) == active` 复查（与三个单记录入口同款守卫）。并发语义：PG 上两个重叠批量批次（admin kill-switch 重试/双触发/subject_types 相交）在本查询行锁上串行化；先提交批次置 `revoked_at`/`superseded_by_id` 后，后到批次锁内重读被 SQL 预过滤 + derive_status 复查双重排除 → 每用户恰一次 epoch bump / 一条聚合事件，双 bump 双事件路径不复存在。全部行已终态时零副作用返回 0（顺序重试幂等由既有 `test_bulk_revoke_zero_use_afterwards` 钉住）。
- **报告表述更正**：原 §0「四个入口统一 SELECT...FOR UPDATE + derive_status 复查」在返修前对 bulk 入口**失实**（R1 C2-2 指出）；返修后该表述与实现一致。真双连接 PG 并发未实测（dev DB 只读纪律，三方一致受限），sqlite 单连接下钉住的是锁内复查语义 + 串行收敛。
- **回归**：新增 `test_bulk_revoke_locked_recheck_skips_terminal_rows`——superseded 终态行（`superseded_by_id` 置位、`revoked_at` 为 NULL，能穿过 SQL 预过滤）必须被复查排除：不撤销、不计 count、memory_ids 不含、恰一次 bump 一条事件。变异击杀实证：删复查过滤 → FAILED。

### 9.4 C2-3（P2-1）— DEL 在 caller commit 之前执行（与 docstring/REPORT 相反）

- **修复**：DEL 移出 `apply_in_txn`——`commit=False`（服务层四路径：retract / bulk / correction-reject / revoke_episodic / supersede，共 5 个调用点）时管线只**计算**待失效键（新纯函数 `derived_cache_keys`）不 DEL，各 caller 在自己 `await self.db.commit()` 之后调用 `invalidate_derived_caches`；`commit=True`（WM forget 端点）路径在内部 commit 后 DEL，顺序本就正确、保持。模块 docstring 与 `MemoryInvalidationResult.invalidated_cache_keys` 语义注释同步更正（后者现在如实说明 commit=False 时 DEL 尚未执行）。
- **效果**：回滚不再产生多余 DEL（旧实现回滚方向无害但加宽 9.5 的 ABA 窗）；「提交后 DEL」表述与实现一致。既有 DEL 行为测试（`test_profile_context_cache_cleared_on_delete` / `test_aurora_self_model_cache_cleared_on_delete`）保持绿，证明 DEL 后置无功能回归。

### 9.5 C2-4（P2-2）— inline snapshot 写时钉 epoch 的 ABA 复活窗

- **修复**：`get_profile_context` 把 epoch 读取**前置到内容装配之前**（prefs→knowledge→cognitive→error→compile 序列之前），单次读取、两处复用——`ProfileContext.memory_epoch` 与 `_write_inline_snapshot_cache(memory_epoch=...)` 嵌入同一个前置值，写缓存时不再二次读取。构建期间（数百 ms）若有删除事务 commit，本快照携带旧 epoch → 读侧门以 current（已 bump）拒绝：fail-closed 方向（多一次重编译，绝无复活）；「旧内容 + 新 epoch 过门」的 120s TTL 复活窗关闭。`_write_inline_snapshot_cache` 的 `memory_epoch` 参数可选，直接外部调用回退写时读取（旧语义，供既有测试/外部调用方）。
- **回归**：新增 `test_inline_snapshot_pins_epoch_read_before_content_assembly`——模拟 ABA 竞态（首次读取=1，此后任何读取=2，等价构建期间删除 commit），断言整个编译恰一次 epoch 读取、两处缓存载荷均携带 1、读侧门拒绝。变异击杀实证：回退为写时二次读取 → FAILED。

### 9.6 P3 项处置

- **P3-6 衰减批任务漏滤 superseded 终态行**：已修——`apply_episodic_decay_policies` 与 `_apply_episodic_decay` 两条 episodic 衰减路径均补 `EpisodicMemory.superseded_by_id.is_(None)`，superseded 终态行不再被后台触碰。
- **P3-7 lower_confidence 不走管线**：登记边界（分数类微调非删除，不构成派生复活通道；M-01 契约 `NON_EPOCH_CORRECTION_ACTIONS` 有意排除）。不修，属语义边界而非缺陷。
- **P3-8 epoch 读持续失败期 epoch=0 条目互配**：登记边界——`_get_memory_epoch` 读失败 fail-closed 0 期间写入的 epoch=0 条目会在持续失败期内互相匹配放行；影响极窄（要求 epoch 读连续失败且恰有同窗写入），fail-closed 方向本身正确（宁可多编译），不修。
- **C3-① 测试恒真断言**：顺手修复——`test_profile_context_cache_rejected_after_epoch_bump` 内 `assert fake_redis.get(...)` 未 await 协程对象恒真，补 await 后断言真实生效（R1 C3-①，原 :497）。

### 9.7 返修后验证矩阵（2026-09-19 实跑）

| 项 | 结果 |
|---|---|
| `tests/unit/test_memory_invalidation_pipeline.py` | **20 passed**（原 17 + 新增 3：supersede 链回归 / bulk 终态复查 / ABA 前置读取） |
| 变异击杀 ×4 | C1 过滤行 / M1 epoch 门条件行 / C2-2 复查过滤 / C2-4 写时二次读取——逐一 FAILED 后 restore 复绿；两源文件 restore 后与备份 **byte-identical** |
| `test_memory_inference_write_guard` + `test_memory_epistemic_contract` + `test_conflict_resolver_epistemic_guard` + `test_working_memory_rejection_guard` | 25 passed |
| `tests/contract/test_event_registry_contract.py` | 31 passed, 1 failed（**基线预存**：state_aggregator 遥测守卫，本卡未触碰文件，R1/R2 双路已核） |
| `tests/unit/test_memory_inferred_write_lane.py` | 6 passed, 1 failed（**基线预存**：embedding RetryError 环境性，与 R1 实测一致） |
| `test_chat_signal_collector_profile_loop` / `test_aurora_control_surface_service` | 2+2 passed |
| 治理守卫 `--rule AC` | PASS |
| black(120) / ruff（5 个本次触碰文件） | 全部通过 |
| `changes.patch` | 重生成（md5 `721b0e7308ed683ae9c5fde15f6f1041`，9 文件 1689+/127-）；`ltm_e2e` 未复跑（PG 认证环境性，R1 已三方核） |

环境：wt8/backend 专属 venv（Python 3.11.15，pytest 9.0.3 / sqlalchemy 2.0.49，requirements.lock 除 python-lzo——本机 lzo 头文件缺位构建失败、全代码库零 import、不在测试路径），sqlite in-memory + FakeRedis，SECRET_KEY 内联未落盘，dev DB/Redis 零接触，真实 LLM 0 次，未起模拟器/浏览器（LIGHT 任务）。

### 9.8 合入后事项（随 Leader checklist，非本卡范围）

- `memory_epoch_version_string()` 进 M-03 检索预筛/记忆敏感缓存组键（主仓零引用，M-03R2 接线项）。
- 主仓 context_manager `get_user_context` 缓存命中刷 `past_session_memory` 的 `suppress(Exception)` fail-open 与 CognitiveContext 缓存（300s，仅 preference_version 门）——M-03/M-04 域登记。
- dev Redis ~4 个 `aurora:self_model:{uuid}` 测试残留键（90d TTL）：红线禁模式删除，Leader 知悉择机处理。
