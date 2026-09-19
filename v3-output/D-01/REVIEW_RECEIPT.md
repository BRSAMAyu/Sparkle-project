# D-01 REVIEW RECEIPT · Reviewer #1（独立复核）

- Reviewer: 第一路独立 Reviewer（D-01 risk high 需 2 Reviewer 之一）
- 日期: 2026-09-19
- 对象: wt4 未 commit 改动 + v3-output/D-01/（base 7251128e）
- 方法: 契约代码审查 + dev DB（sparkle 库）只读 SQL 独立复走 + 测试实跑 + patch 双向 apply 实测

## 1. 契约审查 — 通过

- **词表封闭性**：`len(EVENT_REGISTRY)==33` 实测；`REGISTERED_EVENT_NAMES` 为 frozenset；测试字面量 `_FROZEN_VOCABULARY_SHA256=4e8ccdcd…` 经本 reviewer 用 `sha256("|".join(sorted(names)))` 独立重算**逐字匹配**。状态分布实测 live 18 / reserved 10 / observed_unregistered 5（注意：REPORT.md §2 "live 27 / reserved 11" 为笔误，EVENT_REGISTRY.md 表格统计 18/10/5 正确——仅文档 nit，不阻塞）。
- **correlation 设计**：`CORRELATION_KEYS` 四卡面域（intervention_id/action_id/run_id/outcome_id）+ 辅助链（task_id/session_id/message_id/decision_id/plan_id/node_id）全覆盖 DATA_FLYWHEEL §1 闭环 `Interaction→…→Aurora Decision→Intervention→Action→Outcome` 的可寻址性；全键 canonical UUID 强制（`_canonical_uuid`，非法值抛 EventContractError，测试钉死）。
- **naive-UTC**：`normalize_occurred_at()` 与 `app/core/time_utils.py` 的 canonical form（tz-naive UTC，~286 call sites）语义一致；测试验证 aware 输入转 naive。
- **兼容性**：Go `gateway/internal/cqrs/event/types.go` EventMetadata 用标准 json.Unmarshal（无 DisallowUnknownFields），metadata 多余字段天然容忍，已亲自核对。

## 2. GJ03 链独立复走 — 五段全部实证（只读 SQL，sparkle 库）

| # | 环节 | 本 reviewer 实测 |
|---|---|---|
| 1 | tasks e5f5a8b6 | status=COMPLETED，completed_at=02:00:58.885，actual_minutes=20，user fc62a43c ✓ |
| 2 | study_records bd26a7a7 | task_id=e5f5a8b6（因果键），record_type=task_complete，mastery_delta=3.999…≈4.0，02:00:58.959 ✓ |
| 3 | mastery_audit_log id=106 | old=0→new=3（int 存储），reason=task_complete，request_id=e5f5a8b6，node 5e103872 ✓ |
| 4 | event_outbox f3f5958c | galaxy.node.mastery_updated，seq=1，**published_at=02:00:59.052 非空（published 实证）**；payload 无 task_id（=本卡接线修复的断点，属实）；legacy metadata=`{"service":"galaxy_stats_service"}` ✓ |
| 5 | user_node_status | mastery=3.999…≈4.0（float 0→4.0），study_count=1，total_study_minutes=20，last_study_at=02:00:58.959 ✓ |

audit/outbox 的 new=3（int 舍入）与 study_record/user_node_status 的 ≈4.0（float）为同一事实的两种精度，非矛盾。106 行总量 =101 mastery + 5 probe，与声称一致。

**断点抽查（要求≥2，实查 4 条全部属实）**：B1 `event_store`=0 行 ✓；B2 `intervention_outcomes`/`execution_audit_log`/`behavioral_outcomes` 全 0 ✓；B3 `decision_records` 列结构（user_id/module/action/outcome…）确无 correlation 列 ✓；B4 五行 probe 残留（plan_id=plan-rt02-pg；引用 task 07269751 在 tasks 表 0 行；`grep run.awaiting_user` app/ 无生产者）✓。

## 3. T1/T2 裁定 — 两条均确证为真实渗透路径（代码亲读）

- **T1 成立**：`state_estimator_service.py:64-69` 查询 `TrackingEvent`（tracking_events）→ 写 `user_state_snapshots`；`nightly_review_service.py:173-177` `_latest_state` 读该快照表。telemetry→快照→nightly review 决策输入路径存在（当前 live 快照表休眠，风险为"一旦调度即激活"）。**同意开修复卡**。
- **T2 成立**：`analytics/cognitive_stream_worker.py:81` 消费 Redis `stream:tracking_events` → 写 `CognitiveFragment`（:205）→ `behavior_pattern_service` 产 `BehaviorPattern` → `orchestration/adaptive_replanner.py:132-136` 读入规划调整（confidence≥MIN_CONFIDENCE 门）。telemetry 衍生信号实际进编排决策面。**同意开修复卡**。

## 4. 测试实跑证据

```
tests/contract/test_event_registry_contract.py + tests/services/test_event_idempotency_isolation.py
  → 34 passed（25 contract + 9 isolation）
tests/unit/test_learning_assets.py + tests/api/test_task_complete_galaxy_outbox.py → 39 passed
tests/services/galaxy/ → 29 passed
合计 102 passed，与 worker 自报一致
```

- 幂等测试非空壳：三种重放（跨请求全重放/同批 dict 副本/跨用户同 event_id）均断言**物理行恒 1 + RecordingBus 恰好 1 次 publish + 跨用户 deduped 且不可读他户事件**；`derive_event_id` 同因同 id/seq 与 aggregate 敏感性逐项断言。
- 环境注意（非代码缺陷）：isolation 套件中 galaxy_service 用例 import `app.gen`（gitignore 生成物）。worktree 无 gen 时该用例 ModuleNotFoundError；需按 worker 方法从主仓只读拷入 `backend/app/gen/` 后再跑。reviewer 实测拷入后全绿（收工已删）。

## 5. legacy 兼容实测

dev DB 抽 3 行真实 legacy metadata（galaxy_service b14049ee / run_worker_service 45df91a2 / task_command_executor 48398813）+ 边界（非 JSON 串、None）跑 `read_event_metadata()`：全部不炸不误读——`service` 正确保留、`is_v3_envelope=False`、无幻影字段、坏 JSON 优雅降级为空 view。

## 6. patch 完整性

- `git apply --check`（base 7251128e 干净导出）通过，apply 后 7 个代码/测试文件与 wt4 工作树 **byte-identical（cmp 全 SAME）**；`git apply --reverse --check` 亦通过（双向）。
- patch 覆盖 wt4 全部改动（4 修改 + 3 新增）；v3-output/D-01/ 三产物与 patch 同目录交付。
- 无 .env/密钥（SECRET/PASSWORD/api_key/PRIVATE KEY 零命中）；零 Alembic/migration 内容，"零迁移"声称属实。

## 7. 结论与移交给 Reviewer #2 / 主会话的备注

1. **裁定 ACCEPT**。契约、链实证、测试、patch 四面均独立复核通过。
2. 文档 nit（可不改）：REPORT.md §2 "live 27 / reserved 11" 应为 live 18 / reserved 10（EVENT_REGISTRY.md 正确）。
3. nit（非阻塞）：galaxy_service `_write_mastery_outbox_event` 中 `build_event_metadata` 在 seq 消耗之后调用，未来若有人传未注册 event_type 会烧号后抛错（当前唯一调用方传注册名字面量；learning_asset 侧已做前置校验，可作后续对齐项）。
4. B1–B6/T1–T2 未修属实且与卡面口径一致；T1/T2 修复卡证据充分，建议主会话据此开卡。

VERDICT: ACCEPT
