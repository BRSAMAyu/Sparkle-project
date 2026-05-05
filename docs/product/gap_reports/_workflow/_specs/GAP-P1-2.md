# GAP-P1-2: Plan 版本化 + 回滚 — Implementation Spec

> **Mode**: spec→you | **Level**: L3 | **Effort**: L (6.5-9.5 days)
> **Source**: 04 号报告 — Plan Versioning and Rollback Gap Analysis
> **Status**: 📋 Spec ready for user implementation

---

## 1. 目标 (Objectives)

为 Sparkle 的计划系统添加完整的版本管理、变更历史、差异对比和回滚能力。

### 核心目标
1. 所有计划变更自动生成版本快照
2. 支持任意版本间的差异对比
3. 支持手动和自动回滚到历史版本
4. Flutter 端展示版本历史和变更摘要

---

## 2. 文件清单 (File Inventory)

### 新建文件

| 文件 | 用途 |
|------|------|
| `backend/alembic/versions/pv001_add_plan_versioning.py` | DB migration: add version fields + history tables |
| `backend/app/models/plan_history.py` | SQLAlchemy models: PlanVersion, PlanRollback |
| `backend/app/services/plan_version_service.py` | Core version management service |
| `backend/app/services/plan_diff_engine.py` | Diff generation + impact scope calculation |
| `backend/tests/unit/test_plan_version_service.py` | Unit tests for version service |
| `backend/tests/unit/test_plan_diff_engine.py` | Unit tests for diff engine |
| `mobile/lib/features/plan/data/models/plan_history_model.dart` | Flutter history data model |
| `mobile/lib/features/plan/data/repositories/plan_history_repository.dart` | Flutter history API repository |
| `mobile/lib/features/plan/presentation/screens/plan_history_screen.dart` | Flutter history UI screen |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/models/plan.py` | Add `version`, `previous_version_id`, `superseded_at`, `superseded_by_id` |
| `backend/app/models/__init__.py` | Export PlanVersion, PlanRollback |
| `backend/app/orchestration/adaptive_replanner.py` | Integrate version snapshot on replan; wire `_maybe_rollback_after_feedback` |
| `backend/app/signals/types.py` | Extend PlanDirective: add `rollback`, `view_history`, `compare_versions` actions + `target_version` |
| `backend/app/schemas/plan.py` | Add version fields to Pydantic schemas |
| `backend/app/services/plan_service.py` | Call PlanVersionService on plan create/update |
| `backend/app/api/v1/plans.py` | Add GET `/history`, GET `/diff`, POST `/rollback` endpoints |
| `mobile/lib/features/plan/data/models/plan_model.dart` | Add `version`, `hasHistory`, `canRollback` fields |

---

## 3. 实现步骤 (Implementation Steps)

### Phase 1: Database Foundation (1-2 days)

**Step 1.1**: Add version fields to `backend/app/models/plan.py` Plan model:
```python
version = Column(Integer, nullable=False, default=1)
previous_version_id = Column(GUID(), ForeignKey("plans.id"), nullable=True)
superseded_at = Column(DateTime, nullable=True)
superseded_by_id = Column(GUID(), ForeignKey("plans.id"), nullable=True)
```

**Step 1.2**: Create `backend/app/models/plan_history.py` with two models:
- `PlanVersion`: `plan_id`, `version_number`, `snapshot` (JSONB), `diff_summary` (JSONB), `impact_scope` (JSONB), `change_reason`, `change_type`, `created_by`
  - Unique constraint on `(plan_id, version_number)`
- `PlanRollback`: `plan_id`, `from_version`, `to_version`, `rollback_reason`, `triggered_by`, `impact_assessment` (JSONB)

**Step 1.3**: Create Alembic migration:
```bash
alembic revision -m "add_plan_versioning_and_history"
# Edit the migration file with upgrade/downgrade
alembic upgrade head
make sync-db  # Update Go models if needed
```

### Phase 2: Backend Services (2-3 days)

**Step 2.1**: Implement `backend/app/services/plan_diff_engine.py`:
```python
class PlanDiffEngine:
    def generate_diff(old_plan: dict, new_plan: dict) -> dict
        # Returns: {field_changes: [...], added_tasks: [...], removed_tasks: [...],
        #           reordered_tasks: [...], structural_summary: str}

    def calculate_impact_scope(diff: dict) -> list[str]
        # Returns list of affected task/phase IDs

    def estimate_rollout_risk(diff: dict, impact_scope: list[str]) -> str
        # Returns: "low" | "medium" | "high"
```

**Step 2.2**: Implement `backend/app/services/plan_version_service.py`:
```python
class PlanVersionService:
    async def create_snapshot(plan_id, change_type, change_reason, db) -> PlanVersion
        # 1. Load current plan
        # 2. Load previous snapshot if exists
        # 3. Generate diff via PlanDiffEngine
        # 4. Calculate impact scope
        # 5. Create PlanVersion row
        # 6. Increment plan.version

    async def get_history(plan_id, db) -> list[PlanVersion]

    async def compare_versions(plan_id, version_a, version_b, db) -> dict
        # Load both snapshots, diff them

    async def rollback(plan_id, target_version, reason, triggered_by, db) -> Plan
        # 1. Load target snapshot
        # 2. Create current snapshot (as undo point)
        # 3. Restore plan state from snapshot
        # 4. Create PlanRollback audit row
        # 5. Return restored plan
```

**Step 2.3**: Wire into `backend/app/services/plan_service.py`:
- On plan create → `create_snapshot(change_type="create")`
- On plan update → `create_snapshot(change_type="update")`
- On replan → `create_snapshot(change_type=replan_type)`

**Step 2.4**: Integrate with `backend/app/orchestration/adaptive_replanner.py`:
- Call `create_snapshot` before any replan operation
- Implement `_maybe_rollback_after_feedback` (confidence < 0.3 threshold)

### Phase 3: Signal Types (0.5 day)

**Step 3.1**: Extend `PlanDirective` in `backend/app/signals/types.py`:
```python
plan_action: str = "local_replan"
# Add: "rollback", "view_history", "compare_versions"

target_version: int | None = None
compare_version_a: int | None = None
compare_version_b: int | None = None
```

### Phase 4: API Endpoints (1 day)

**Step 4.1**: Add to `backend/app/api/v1/plans.py`:
- `GET /{plan_id}/history` → list of PlanVersion items
- `GET /{plan_id}/versions/{v_a}/diff/{v_b}` → diff dict
- `POST /{plan_id}/rollback` → body: `{target_version, reason}` → restored Plan

**Step 4.2**: Update Pydantic schemas in `backend/app/schemas/plan.py`:
- Plan response includes `version`, `has_history`, `can_rollback`

### Phase 5: Mobile Layer (2-3 days)

**Step 5.1**: Update `mobile/lib/features/plan/data/models/plan_model.dart`:
- Add `version` (int), `hasHistory` (bool), `canRollback` (bool)

**Step 5.2**: Create `plan_history_model.dart`:
- `PlanHistoryModel`: planId, versionNumber, snapshot, diffSummary, impactScope, changeReason, changeType, createdBy, createdAt

**Step 5.3**: Create `plan_history_repository.dart`:
- `getPlanHistory(planId)` → List<PlanHistoryModel>
- `compareVersions(planId, versionA, versionB)` → Map
- `rollbackToVersion(planId, targetVersion, reason)` → PlanModel

**Step 5.4**: Create `plan_history_screen.dart`:
- Timeline-style version history list
- Each item shows: version number, change type icon, change reason, timestamp
- Tap to see diff (added/removed/modified tasks)
- Rollback button with confirmation dialog
- Use `isChinese ? '中文' : 'English'` pattern for i18n

---

## 4. 测试计划 (Test Plan)

### Backend Tests

| Test | 描述 |
|------|------|
| `test_create_snapshot_on_plan_create` | 创建计划时自动生成 v1 快照 |
| `test_create_snapshot_on_plan_update` | 更新计划时生成新版本快照 |
| `test_diff_generation` | 两个版本间正确生成字段/任务级 diff |
| `test_impact_scope_calculation` | 正确计算影响范围（受影响的任务/阶段ID） |
| `test_rollback_restores_state` | 回滚后计划状态与目标版本一致 |
| `test_rollback_creates_audit_row` | 回滚操作写入 PlanRollback 审计表 |
| `test_get_history_returns_ordered` | 版本历史按时间降序返回 |
| `test_compare_versions` | 任意两版本对比正确 |
| `test_rollback_creates_undo_point` | 回滚前创建当前状态快照作为撤销点 |
| `test_adaptive_replanner_auto_rollback` | 低置信度反馈触发自动回滚 |

### Mobile Tests

| Test | 描述 |
|------|------|
| `test_plan_history_screen_renders` | 历史页面正确渲染版本列表 |
| `test_version_tap_shows_diff` | 点击版本显示变更摘要 |
| `test_rollback_button_with_confirmation` | 回滚按钮弹出确认对话框 |
| `test_rollback_success_navigates_back` | 回滚成功后返回计划页 |
| `test_empty_history_state` | 无历史版本时显示空状态 |

### Integration Tests

| Test | 描述 |
|------|------|
| `test_full_version_lifecycle` | 创建→更新→回滚完整流程 |
| `test_concurrent_version_creation` | 并发版本创建下唯一约束不冲突 |

---

## 5. 验收标准 (Acceptance Criteria)

### Functional
- [ ] 所有计划创建/更新/重规划自动生成版本快照
- [ ] Plan 表每条记录的 `version` >= 1
- [ ] `GET /{plan_id}/history` 返回完整版本列表
- [ ] `GET /{plan_id}/versions/{a}/diff/{b}` 返回结构化 diff
- [ ] `POST /{plan_id}/rollback` 正确恢复到目标版本
- [ ] 回滚操作写入 `plan_rollbacks` 审计表
- [ ] Flutter 计划详情页显示版本号和历史入口
- [ ] Flutter 历史页展示时间线式版本列表
- [ ] Flutter 回滚按钮带确认对话框

### Non-Functional
- [ ] 版本历史查询 < 100ms
- [ ] Diff 生成 < 500ms (典型计划)
- [ ] 回滚操作 < 1s
- [ ] 无数据丢失 (回滚不破坏历史)

### Quality Gates
- [ ] 所有测试通过 (backend + mobile)
- [ ] 无 CLI 启动错误
- [ ] Alembic upgrade/downgrade 双向可逆
- [ ] `make sync-db` 成功
- [ ] 无硬编码 secrets/tokens
- [ ] i18n 双语覆盖新增 UI 文本

---

## 6. 设计决策 (Design Decisions)

| 决策 | 选择 | 理由 |
|------|------|------|
| 迁移策略 | Option A: 现有计划 version=1 | 最简单, 无数据丢失 |
| 历史保留 | Option A: 保留全部版本 | 用户安全优先; 数据量小 |
| 冲突解决 | Option A: Last write wins | 当前单用户; 多用户冲突另案处理 |
| Card Protocol 集成 | Option B: 增强 legacy Plan | 避免大规模迁移, 04 号报告建议 |

---

## 7. 依赖与阻塞 (Dependencies)

- Phase 2 (backend services) 依赖 Phase 1 (DB migration)
- Phase 4 (API) 依赖 Phase 2 (services)
- Phase 5 (mobile rollback UI) 依赖 Phase 4 (rollback API)
- Phase 3 (signal types) 可独立进行
- Phase 5 (mobile models) 可并行于 Phase 2-4 (用 mock 数据)

---

## 8. 开放问题 (Open Questions)

1. 版本快照存储完整计划 JSON — 大计划可能达到几百KB。是否需要压缩？
2. 回滚后是否通知 Flutter via WebSocket？当前设计是轮询。
3. Celery beat 是否需要定期清理版本快照？

---

*Spec generated 2026-05-06 by claude-B (GAP Closer Agent)*
