# WT663 · D-01 增量复证报告（统一 Event / Evidence Lineage Contract）

- **Session**: wt663（卡池 D-01，worktree `Sparkle-sysrev/wt663-d01`，分支 `agent/node-b/wt663/d01`）
- **性质**: **增量复证轮**——D-01 已有首轮 dual-review ACCEPT（`6f488636`，2026-09-19，fleet state `done`），本轮按指令「git log 双证判卡面已完成部分，增量不重做」执行现状复核。
- **Base SHA**: `a4332fa2`（2026-09-25 集成波 HEAD，即 worktree 创建点）
- **Final SHA**: 本 commit（见 git log；零产品代码改动，仅本报告文件）
- **双证**: ①`git log` 含 `6f488636 D-01 ACCEPT merge (dual-review + rework)` 且为 HEAD 祖先；②`v3/.sparkle_v3_fleet_state.json` `done` 列表含 `D-01`。

## 1. 卡面逐条验收对照（现状复证）

### Work 1 — 复用现有 outbox/event store；V3 关键 event names + shared fields

| 项 | 首轮交付 | 本轮现状复证 | 结论 |
|---|---|---|---|
| 词表 | 33 名封闭入册，sha256 冻结于测试字面量 | **40 名**，冻结哈希 `3444257e9ffb1f4b26f2a5a02047b59575b381af15b048926dd70f994cd2e0a0` 本轮独立重算吻合（非仅信测试）；三次扩词表全走显式 re-freeze 流程并留 changelog（X-05→36、D-05→39、S-04 wt382→40） | HOLD |
| shared fields | `build_event_metadata`（event_id/user_id/schema_version=event.v1/source 封闭枚举/occurred_at/correlation 10 键） | `core/event_registry.py` 844 行在位；防御解析/豁免类冻结等 R2 返修四项全在场 | HOLD |
| 写入方接线 | 3 个 Python 写入方 | 现全仓 **7 个 raw-SQL `INSERT INTO event_outbox` 写入方全部经 `build_event_metadata` 构造 metadata，零绕过**（ACCEPT 后新增 4 个：`community_feedback_service`(S-04)、`intervention_lifecycle_service`(D-05)、`action_command_service`(X-03)、`memory_invalidation_pipeline`(M-04)）；另有 `aurora/joint_decision.py`、`action_allocation_policy.py` 按 shared-fields 契约构造供消费方落库 | HOLD+净增合规 |

### Work 2 — client telemetry 不成为业务真值

- 契约面 `source ∈ {client_telemetry, probe} ⇒ is_business_truth_eligible()==False` 代码强制在位。
- 首轮移交的 T1/T2/T3 渗透链 → **V3-FIX-11 FIXED**（三链根治+双层守卫）；其 follow-up → **V3-FIX-14 FIXED@e9f5629f**。本轮机械确认守卫机制在位：`telemetry_boundary.py`（`TELEMETRY_DERIVED_LOAD_CAP=0.3`/`TELEMETRY_DERIVED_STRAIN_CAP=0.3`）、`state_estimator_service`（`_DEBOUNCE_LOCKS` per-user 防抖锁）、plan_context waiver 收编。
- `tests/contract/test_telemetry_boundary_contract.py` 本轮随批量绿。

### Work 3 — intervention/action/run/outcome 经 IDs 关联 → Acceptance ① GJ03 trace

**本轮独立跑通全链 probe**（sqlite 内存库、真实 API 路由、零 mock 事件，判据可证伪，脚本 `/tmp/wt663_d01_gj03_probe.py`）：

```
HOP1 UI action   POST /tasks/{id}/complete -> 200 (真实 tasks 路由)
HOP2 tasks       status=COMPLETED, completed_at 落行
HOP3 study_records  task_id == task.id（因果键），record_type=task_complete, delta=5.0
HOP4 mastery_audit_log  ENV-LIMITED（见裁决 2）；代码路径 request_id=str(task_id) 源码在位
HOP5 user_node_status   mastery 0→5.0, study_count=1（state update 腿）
HOP6 event_outbox  galaxy.node.mastery_updated seq=1, event_id=evt_eba3e9cbc8c51339f5e471425b9e1b5e
                   metadata: is_v3_envelope=True, schema=event.v1, user_id 隔离键,
                   correlation={task_id, node_id} 与 payload 双带
                   node identity: state == event == study_record
HOP7 outcome ledger (D-02)  outcome_id == derive_outcome_id(task_completion, task.id) 精确吻合，
                   correlation.task_id 回链同一 task，study_record 以 pipeline_echo 附着为多源证据
GJ03 CHAIN COMPLETE — all hops ID-continuous
```

既有锚点测试同轮绿：`tests/api/test_task_complete_galaxy_outbox.py`（真实 API → projector 可见 outbox 行 → 序列递增）。

### Acceptance ② — 事件幂等且跨用户隔离

- `tests/contract/test_event_registry_contract.py`（34）+ `tests/services/test_event_idempotency_isolation.py`（9）本轮在当前 HEAD **43/43 绿**（幂等：同 event_id 重放物理单行、derive_event_id 确定性；隔离：event_id 唯一约束跨用户去重、get_event 用户域过滤、estimator 只见本 user 事件）。

## 2. 裁决要点

1. **不重做已验收部分**：首轮 ACCEPT 的词表/信封/幂等/隔离/telemetry 边界契约全部经测试与独立哈希重算复证 HOLD，本轮零产品代码改动。
2. **HOP4 审计腿 sqlite 环境受限，如实标注**：`spark_node` 经 raw `text()` 传 UUID 对象写 `mastery_audit_log`，sqlite 驱动拒绑（PG 原生支持）；该腿的 live-PG 实证在首轮 REPORT §3（audit id=106, request_id=task_id），代码路径本轮源码在位未变。非产品缺陷、非本卡回归，probe 内显式降级不静默。
3. **B1（event_store 0 行）已被后续波次消解**：gateway `cqrs/outbox/repository.go::SaveWithTx` 由 publisher 原子落库 event_store（wt657 B-06 ENTITY_MAP 同判：单向流健康），首轮断点清单中的此项已过时。
4. **R2 移交项现状盘点**（均已在 ACCEPT 件 REVIEW_RECEIPT_2 §7 登记，非新发现，**本轮不新开 FIX 号**）：
   - F2 真值门 None→eligible=True 的 fail-open 语义保留（FIX-11 根治选在摄入/边界层 caps+debounce，门语义未改）——消费方接入前需重审；
   - F6 gateway 第二 envelope 仍在（`cqrs/event/types.go::Metadata` 无 schema_version/10 键 correlation）；本轮确认读侧 `read_event_metadata` 对该形态**容忍不丢行**（user_id/source 存活、is_v3_envelope=False 降级视图），首轮「静默排除」风险已被读侧兼容消解大半，跨层统一仍属后续卡；
   - F7 outbox 7 天清理 vs lineage 目的：`cleanup_worker` 仍按 7 天删 published 行，显式留存决策仍开放（intervention_lifecycle/agent_run transitions 等持久账本已分流，冲突面收敛但未关闭）；
   - F8 spark 链路业务 commit 与 outbox 写非原子（双 commit 窗口）仍在；F9 aggregate_id 归一化未深查。F10/F11/F12 已由首轮返修关闭（本轮代码确认在位）。
5. **并行卡避让**：本轮零产品代码改动，与 wt655/659/661/662 无撞面。

## 3. 验证件套

```
测试（当前 HEAD，sqlite 内存口径，venv 只读借用主仓）:
  contract + isolation 核心          43 passed (3.60s)
  加 telemetry_boundary + 写入方回归  247 passed (66.88s)
    含 test_event_registry_contract 34 / test_event_idempotency_isolation 9 /
       test_telemetry_boundary_contract / test_learning_assets 35 /
       test_task_complete_galaxy_outbox 4 / tests/services/galaxy 29+ / galaxy 契约族
词表冻结独立复算: 40 名，sha256 == 3444257e…2e0a0（测试字面量吻合）
GJ03 全链 probe: 7 hop 全通（HOP4 env-limited 如实标注），判据输出见 §1
门禁: 本轮零产品代码改动 → ruff/mypy 无新增面；未触 .env；未 push；未占用并行卡文件
清理: probe 脚本留存 /tmp（会话产物不入库）；worktree gen 为 gitignored 拷贝不入 commit
```

## 4. 新登记 FIX

**无**。本轮全部发现要么已登记（V3-FIX-11/14 FIXED、R2 移交项在 ACCEPT 件 §7），要么属测试环境口径说明（HOP4 sqlite UUID 绑定），不构成新不诚实面。台账零改动。

## 5. 运行级待验清单（移交协调侧）

1. **live dev DB PG 端 GJ03 全链复走**（含 HOP4 audit 腿 PG 绑定实跑）——本轮 sqlite 口径 + 首轮 live 实证组合覆盖，PG 现值未重采。
2. **B4 probe 残留行清理**（event_outbox 内 `run.*`/`task.status_changed` 5 行，生产者不在仓）——首轮已建议主会话清理，现状未核。
3. **F1 event_id 消费侧接线**（gateway processed_events uuid.Parse 拒收 `evt_` 前缀问题）——后续消费卡前置。
4. **F6/F7/F8 裁决**：跨层 envelope 统一、outbox 留存策略显式化、spark 双 commit 原子化——均为已登记的结构性开放项，需排卡。
