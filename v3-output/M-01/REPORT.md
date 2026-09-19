# M-01 Memory V3 实体映射与 Epistemic Types — 执行报告

worktree: `Sparkle-sysrev/wt2 @ 2f52a972`（基线）→ 本卡改动见 `changes.patch`
gate: V3-2 ｜ risk: high ｜ reviewers_required: 2 ｜ 禁 commit/push（已遵守）

## 0. 六句总结

契约落点是单一权威模块 `backend/app/services/memory_epistemic_contract.py`（五类型 × source/scope/status 派生 + lane 注册表 + 守卫谓词 + epoch 契约），不改五层契约、不建第二库。迁移 `m01a_20260919` 只做加法：`episodic_memories.epistemic_class/superseded_by_id`（含按 lane 回填 FACT/HYPOTHESIS）与 `user_memory_settings` 三列 epoch；sqlite 隔离重放测试验证加列/回填/可回滚。守卫证据为红→绿：改动前 7 项守卫测试失败（含**推断写今天真的会覆盖显式偏好事实**这一实证漏洞），改动后 10/10 通过；conflict `apply_live_decision` 补了变更点级 lane 守卫与 supersede 链。映射覆盖度：MAPPING.csv 23 行 × 9 列，覆盖五类型 + 瞬态 + 五层联动 + aurora_calibration_receipt 保留位（不替产品裁决，V3-FIX-06）。epoch 已接删除/撤回四入口（best-effort 不阻塞主路径）。存量回归：受影响 11 个测试文件无新增失败（9 项失败经 git stash 对照证实全部为基线预存的环境性失败）。

> **R2 返修后记（2026-09-19）**：按 REVIEW_RECEIPT_2.md 判 CHANGES，已返修 F1（回填 CASE 收紧：FACT 仅限用户陈述，机器写行落 OBSERVATION）与 F3（epoch 原子自增+懒建竞态回滚重试）；测试集 21→23 项全绿，详见 §8（含重跑输出与红态复现）。F2/F4/F5-F7 按裁决登记 M-04 前置卡，未修。

## 1. 问题与目标

任务卡目标：在现有 memory/五层用户模型上落实 FACT / CONFIRMED_PREFERENCE / OBSERVATION / HYPOTHESIS / EXPERIENCE 与 provenance，不建第二库；区分瞬态；建立 status/supersede/revoke/epoch contract；保障 Inference 不覆盖 fact。

### 勘察发现的实质漏洞（守卫红态实证）

1. **推断写可覆盖显式偏好事实（真 bug，非理论）**：`MemoryService.upsert_preference` 无条件新建版本并把当前链头标记 `replaced_by_id=新版本`。`ProfileWriteService.update_inferred_preference`（ai_inferred 来源）调用该入口时，会把用户显式设置的 `memory_preferences` 链头（FACT 域）supersede 掉；`find_preference`/`list_preference_records` 按最高版本取头 → 读侧拿到推断值，显式事实被埋进版本链。user_preferences live 表有 `_has_explicit_override` 保护，但版本链域没有。守卫测试 `test_inferred_preference_write_cannot_supersede_explicit_fact` 在基线上失败（红）证明该行为存在。
2. **conflict 变更点无 lane 守卫**：`apply_live_decision(action=accept)` 对 loser 直接落 `retracted_at`，不校验 winner/loser lane 档位。`resolve()` 的算术不会产出越权决策，但该方法是公开 API（M-04 接线后调用方更多），守卫必须落在变更点（defense in depth）。
3. **HYPOTHESIS 无显式标注**（B-06 §1.2 已冻结）：inferred lane 隐式承载，查询层无法按类型过滤。
4. **episodic 无 supersede 链**：冲突败者被 retracted 但不指向胜者，与 preferences 的 `replaced_by_id` 不对称，状态机无法区分"被替换"与"被撤回"。
5. **epoch 无数据结构**（MEMORY_V3 §6：删除→bump→缓存失效，M-07/C-07 消费）。

## 2. 契约设计（核心决策）

### 2.1 单一权威模块

`app/services/memory_epistemic_contract.py`（`MEMORY_EPISTEMIC_CONTRACT_VERSION = "memory-v3.m01.v1"`）：

- **EpistemicClass**：五类型枚举。`EPISODIC_EPISTEMIC_CLASSES` 限定 episodic 合法值为 FACT/OBSERVATION/HYPOTHESIS/EXPERIENCE；**CONFIRMED_PREFERENCE 由表成员资格承载**（memory_preferences/memory_goals 即该类型），不加列——这是"不建第二库"的落法。
- **classify_episodic_class(source_lane, explicit_class)**：显式列值优先；NULL 时按 lane 保守派生——`direct_capture/user_confirmed → FACT`，其余（含未登记 lane）→ `HYPOTHESIS`。OBSERVATION/EXPERIENCE 只能由未来写方显式声明（行为观察/经验投影），杜绝"未知来源冒领事实档"。
- **derive_status(record)**：存储派生状态机，优先级 `revoked > superseded > retracted > archived > expired > resolved > active`；superseded = `replaced_by_id`(prefs)/`superseded_by_id`(episodic) 非空。candidate/confirmed 明确为**视图级**限定（HYPOTHESIS 分区 + MemoryCorrection(action=confirm)），不落存储——避免为 UI 语义加列。
- **derive_scope(record)**：scope 为现有列的派生投影（prefs=global；goals=goal+task/plan；episodic=domain+entity_hash+time_window；working_memory=session），零新增存储。
- **preference_write_provenance**：与 API 层 `_resolve_preference_source` 同口径（refs 含 ai_inferred 或 source_type=ai_inferred → inferred）。
- **lane_priority**：委托 `ConflictResolverService.KNOWN_SOURCE_LANES/PRIORITY_BY_TIER`，lane 档位唯一真源仍在 resolver，契约不重复定义（测试断言两侧一致）。
- **RESERVED_UNREGISTERED_LANES**：`aurora_calibration_receipt` 有文档位（epistemic 归类 HYPOTHESIS、仲裁按 unknown 最低档），**不登记、不裁决**——登记权在 V3-FIX-06（红线继承）。
- **EPOCH_BUMP_CORRECTION_ACTIONS** = {delete, reject, no_longer_applicable}。

### 2.2 status / supersede / revoke / epoch contract

- **supersede**：preferences 沿用 version+replaced_by_id；episodic 新增 `superseded_by_id`（`apply_live_decision` accept 分支落链）。链指针使"纠错产生 supersede 而非覆盖"可机读。
- **revoke**：`revoke_episodic_memory`（用户删除，一律 revoked_at）与 `_apply_retraction`（按 lane 分流：inferred→revoked_at，其余→retracted_at）语义不变，本卡不动产品行为。
- **epoch**：`user_memory_settings.memory_epoch`（server_default=1，单调递增）+ `bumped_at` + `reason`；`MemoryService.bump/get_memory_epoch` 为唯一入口；bump 写 `MemoryCorrection(action="epoch_bump")` 审计。已接四个删除/撤回入口（retract_memory、revoke_episodic_memory、apply_correction 的 reject 分支、revoke_inferred_memories 批量按用户去重 bump），全部 best-effort（NON_CRITICAL_SERVICE_ERRORS 吞掉并告警），不阻塞主路径。M-07 编译上下文时取 epoch、消费前复查即可检测缓存过期；C-07 敏感删除后的在途重授权同接口。**本卡不做缓存失效接线**（契约+数据结构+最小生产 bump）。

### 2.3 Inference 不覆盖 fact（软件级保障，红→绿）

1. **preference 域**（memory_service.upsert_preference）：incoming=inferred 且链头=explicit → 拒写（返回 None，指标 `MEMORY_WRITE_TOTAL{status="blocked_inferred_over_fact"}`），链头/版本链零变动。推断值仍进 user_preferences live 表（原有 explicit_override 保护）——推断演化不丢，只是不再冒充事实链头。显式写接管任意头、推断写演替推断头、空链首写均不受影响（三个不回归测试）。
2. **episodic 域**（conflict_resolver.apply_live_decision）：winner lane 档位 < loser 档位 → 跳过该 loser 的 retract/supersede，越权 ID 记入 resolution metadata（`epistemic_guard_skipped_loser_ids`）并告警。用户仲裁（arbitrate_unresolved_conflict）不经过此路径，人类选择保持最高权限。

## 3. 迁移（m01a_20260919，全部加法、可逆）

`backend/alembic/versions/m01a_20260919_memory_v3_epistemic.py`，down_revision=`ud01_20260919`（当前唯一 head，ScriptDirectory 实测）：

- `episodic_memories.epistemic_class` String(24) nullable + 索引 (user_id, epistemic_class)；
- `episodic_memories.superseded_by_id` GUID nullable + 索引；
- 回填（幂等 UPDATE，仅填 NULL）：direct_capture/user_confirmed→FACT，其余→HYPOTHESIS（含未登记 lane，保守档）；
- `user_memory_settings.memory_epoch` Integer NOT NULL server_default='1' + `memory_epoch_bumped_at` + `memory_epoch_reason`。

**安全性**：全部 nullable/带默认，在跑旧代码零感知；downgrade 干净 drop。**未对 dev PostgreSQL 执行**（主库只读纪律；sqlite 隔离重放测试 `tests/unit/test_memory_v3_migration_sqlite.py` 验证加列/回填/幂等/可回滚，沿用 ud01 的重放模式）。随常规发布走 `make sync-db`。

## 4. 写路径接线（最小集）

- `create_episodic_memory` 新增 `epistemic_class` 参数；`_build_episodic_memory_record` 落 `classify_episodic_class(...)`（含 pgvector 降级重试路径）。所有既有调用方零改动即获得派生标注。
- 治理 API 序列化补字段：`GET /memory/episodic` 与 preferences 面板加 `epistemic_class/status/scope`；export 序列化加 `epistemic_class/memory_status/scope`（`memory_status` 避开 MemoryGoal 业务 `status` 列冲突）。source 侧 `source_annotation` 已有，不动。
- aurora correction_feedback / working_memory pipeline / 五层契约 / ConflictResolver 接线（M-04）/ EXPERIENCE 投影（M-06）/ epoch 缓存消费（M-07）——本卡均不动，仅在契约中留位。

## 5. 证据

### 守卫红→绿（同一测试集，改动前后）

- 红（基线代码 + 新测试）：`7 failed, 3 passed` —— 失败项即第 1 节漏洞的实证（推断覆盖 fact ×2、episodic class 缺失、epoch 缺失、conflict 守卫缺失 ×1、supersede 链缺失 ×2）；3 个通过项为合法路径基线。
- 绿（守卫实施后）：`10 passed`（tests/unit/test_memory_inference_write_guard.py 7 + test_conflict_resolver_epistemic_guard.py 3）。

### 契约与迁移

- `tests/unit/test_memory_epistemic_contract.py`：10 passed（lane 注册表与 resolver 一致性、保留位不登记、状态机优先级、守卫真值表、epoch 动作集）。
- `tests/unit/test_memory_v3_migration_sqlite.py`：1 passed（加列/回填/幂等/回滚 + down_revision 挂链断言）。

### 存量回归（受影响域）

- `test_memory_service*.py`（4 文件）+ `test_conflict_resolver_service.py`：30 passed, 0 failed。
- 大套（含 inferred_write_lane/working_memory_consolidation）：4 failed —— **经 git stash 对照，与干净基线逐项相同**（LLM demo-mode、semantic gating RetryError、Redis/kill-switch 缺失的环境性预存失败）。
- `test_memory_api.py`/`test_memory_episodic_governance_api.py`/`test_memory_export_api.py` 等无法收集：`app.gen` 缺失（本 worktree 未跑 proto-gen，基线同样无法收集）。API 序列化改动以进程内 stub 导入 + 断言直接验证（episodic FACT/HYPOTHESIS、prefs/goals CONFIRMED_PREFERENCE、scope/status 键齐全）。

### 命令复现

```bash
cd backend
SECRET_KEY=$(python3 -c "print('x'*40)") python3.11 -m pytest \
  tests/unit/test_memory_epistemic_contract.py \
  tests/unit/test_memory_inference_write_guard.py \
  tests/unit/test_conflict_resolver_epistemic_guard.py \
  tests/unit/test_memory_v3_migration_sqlite.py -q
# => 21 passed
```

## 6. 风险与限制（如实）

1. **lane 冒领未封死**：`create_episodic_memory` 的 source_lane 仍由调用方申报（如 unified_analysis_service 以默认 direct_capture 写入）。按 lane 归档 epistemic class 依赖申报诚实。全量改写各写方 lane 是产品行为变更（影响冲突裁决与 UI 标签），本卡不越权裁决，已在 MAPPING 标注，建议随 M-04 接线一并治理。
2. **推断偏好历史改道**：被守卫拦截的推断写不再留 memory_preferences 版本行（此前会留一条 ai_inferred 版本）。推断状态仍完整保留于 user_preferences live 表（inference_metadata）；如果后续需要推断历史审计行，可加"非链头 inferred 备忘行"机制（本卡不做，避免复杂化）。
3. **epoch 无消费者**：数据结构与 bump 已就绪，M-07/C-07 接线前无运行时效果（契约预留，符合任务卡边界）。
4. **backfill 保守档**：未登记 lane 全部落 HYPOTHESIS——aurora_calibration_receipt 若未来登记升档，需一次性 UPDATE 校正（V3-FIX-06 决策后）。
5. 本地 black 与仓库既有格式存在版本偏差（基线文件本身不过本地 black）；本卡新增代码人工对齐既有风格，ruff 全过，未整文件重排（避免格式噪音）。

## 7. 交付物清单

- 契约：`backend/app/services/memory_epistemic_contract.py`（新）
- 守卫：`backend/app/services/memory_service.py`（preference 守卫 + epoch API + epistemic_class 接线）、`backend/app/services/conflict_resolver_service.py`（变更点守卫 + supersede 链）
- 模型：`backend/app/models/memory.py`（2 列 + 2 索引）、`backend/app/models/user_memory_settings.py`（3 列）
- 迁移：`backend/alembic/versions/m01a_20260919_memory_v3_epistemic.py`
- API：`backend/app/api/v1/memory.py`（序列化补 epistemic_class/status/scope）
- 测试（新 4 文件 21 项）：`test_memory_epistemic_contract.py`、`test_memory_inference_write_guard.py`、`test_conflict_resolver_epistemic_guard.py`、`test_memory_v3_migration_sqlite.py`
- 映射：`v3-output/M-01/MAPPING.csv`（23 行 × 9 列）
- 本报告 + `changes.patch`

## 8. R2 返修（REVIEW_RECEIPT_2.md，CHANGES → 本节为 F1/F3 修复记录）

返修范围：仅 F1（P1）与 F3（P2）两处最小改动；F2（apply_live_decision TOCTOU/行锁）、F4（epoch 第 5 入口+语义不对称）、F5-F7 按裁决不修，已登记 M-04 前置卡。其余设计未动。

### 8.1 F1（P1）回填 CASE 收紧 —— FACT 仅限用户陈述

- **问题**：原回填把全部 direct_capture 行标为 FACT，但 R2 dev 库实证（只读）184 direct_capture 行中 183 行为机器写入（chat_turn=164——其中 148 行是同一完成事件重复、analysis=9、reflection=6、error_analysis=2、practice_outcome=2），仅 user_registered=1 行是用户陈述（写方 `user_memory_seed_consumer.py:25`）。按契约自身定义（OBSERVATION = 系统/行为观察），机器写行落 FACT 是把系统观察冒充事实，且经本卡 API 直接对外暴露。
- **修法（契约+迁移+接线三处对齐）**：
  1. 契约 `USER_STATEMENT_SOURCE_TYPES = {"user_registered"}`（附 dev 库证据注释，扩展属产品决策随 M-04 写方治理）；`classify_episodic_class` 收紧为：`user_confirmed` lane → FACT（确认动作即用户陈述）；`direct_capture` + source_type ∈ 用户陈述集 → FACT；`direct_capture` 其余（机器写）→ OBSERVATION；其余 lane → HYPOTHESIS；source_type 缺失时保守落 OBSERVATION 不冒领事实档。
  2. 迁移回填 CASE 同步收紧（SQL 内注释声明须与 `USER_STATEMENT_SOURCE_TYPES` 保持同步；Migration Contract 的 backfill_plan 已更新）。
  3. 运行时接线：`_build_episodic_memory_record` 与 API 两处序列化均传入 `source_type`——若只改回填不改写路径，增量机器写会继续污染 FACT 分区。
- **测试**：sqlite 重放测试改为按 dev 库 live source_type 构成播种的期望矩阵（user_registered→FACT、user_confirmed→FACT、chat_turn/analysis→OBSERVATION、inferred→HYPOTHESIS、未登记 lane→HYPOTHESIS）；契约测试补 source_type 矩阵与用户陈述集证据断言；guard 派生测试改三例（用户陈述/机器写/推断）。
- **效果（对 dev 库回填的推演）**：FACT 分区从 ~184 行降至 2 行（user_registered=1 + user_confirmed=0），机器事件行全部落 OBSERVATION，符合"你告诉我的/我观察到的"分区语义。

### 8.2 F3（P2）bump_memory_epoch 原子化

- **问题**：原实现 SELECT（无 FOR UPDATE）→ python +1 → commit，并发双 bump 均返回 2、终值 2（R2 探针 B 复现；本 worker 返修中以同法复现：并发结果 `[2, 2]`、终值 2）；懒建行并发撞 unique(user_id) 时 IntegrityError 被 best-effort 吞掉但 session 残留 aborted 态，`revoke_inferred_memories` 多用户循环中后续 bump 全部 PendingRollbackError 静默丢失。
- **修法**：自增改单条原子 `UPDATE ... SET memory_epoch = memory_epoch + 1, ... RETURNING (id, memory_epoch)`（数据库端自增 + 行级锁，各 bump 得各自返回值）；审计 MemoryCorrection(action="epoch_bump") 与自增同事务提交。懒建路径 INSERT 撞 unique 时**先 rollback（清 aborted 态）再走原子自增重试**；重试仍无行（如被软删）显式 raise 而非静默丢 bump（仍被外层 best-effort 捕获并告警）。
- **验证**：
  - 新增并发测试 `test_memory_epoch_concurrent_bumps_no_lost_increment`：3 个独立连接（真实文件 sqlite）同时首 bump，断言返回值集合 {2,3,4}、终值 4、审计行 3——该断言在旧算法下必失败（[2,2]→2 已复现），新实现 10/10 稳定通过；
  - 懒建竞态确定性探针（进程内一次性，不入库）：A 持未提交 INSERT、B 撞 unique → rollback → 原子重试返回 2，事后同 session 再 bump 得 3（session 未被毒化）；
  - 旧算法红态复现：并发 `[2, 2]`、终值 2（丢增量）。

### 8.3 返修后重跑输出

```
# M-01 全套（guard 8 + 契约 11 + conflict guard 3 + 迁移重放 1）
tests/unit/test_memory_epistemic_contract.py tests/unit/test_memory_inference_write_guard.py
tests/unit/test_conflict_resolver_epistemic_guard.py tests/unit/test_memory_v3_migration_sqlite.py
=> 23 passed in 3.76s

# 并发稳定性：test_memory_epoch_concurrent_bumps_no_lost_increment 连跑 10 次 => 10× 1 passed

# 存量回归抽样（memory service×4 + conflict resolver + inferred lane）
=> 1 failed, 28 passed
   （唯一失败 test_two_consecutive_sessions_prompt_includes_inferred_memory 为基线预存环境性失败，
    git stash 对照与首轮交付时相同：LLM demo-mode + semantic gating RetryError）

# API 序列化（app.gen stub 进程内验证）
direct_capture+user_registered->FACT / direct_capture+chat_turn->OBSERVATION
user_confirmed->FACT / inferred_extraction->HYPOTHESIS => OK
```

### 8.4 返修后仍未修（登记确认）

F2（apply_live_decision 生命周期过滤+行锁）、F4（arbitrate_unresolved_conflict 补 epoch bump+supersede 语义对称）、F5（schema-先于-代码发布序）、F6（守卫"explicit"判据=非 ai_inferred 的边界文档化）、F7（episodic 守卫跳过计数指标）——按主会话裁决留给 M-04 前置卡，本卡不修。
