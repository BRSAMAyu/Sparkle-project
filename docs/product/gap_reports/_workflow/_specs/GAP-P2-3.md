# GAP-P2-3: Stuck Type 运行时分类器 — Implementation Spec

> **Mode**: spec→you | **Level**: L2 | **Effort**: M (5-8 days)
> **Source**: 08 号报告 E2E-045 — StuckProtocol 定义 5 种卡点类型，但无运行时行为分类器
> **Status**: 📋 Spec ready for user implementation

---

## 1. 目标 (Objectives)

为 Sparkle 的 StuckProtocol 补全运行时行为分类能力：在用户卡住时观察行为信号，动态判定 stuck_type，替代静态预置值。

### 核心目标
1. 实现 `StuckTypeClassifier`: Deterministic 规则引擎，根据用户行为信号分类 stuck_type
2. 集成到现有 `POST /{task_id}/stuck` 管线，动态更新 TaskCardProtocol.stuck_protocol
3. 将分类结果写入 Redis 缓存，供 Flutter 端消费
4. 根据分类结果自动调整 hint_strategy 和 fallback_task_type
5. Flutter `StuckHelpSheet` 根据运行时 stuck_type 展示差异化帮助内容

---

## 2. 现状评估 (Current State Assessment)

### 已实现

| 能力 | 文件 | 状态 |
|------|------|------|
| STUCK_TYPES 常量 (5 types) | `backend/app/signals/types.py:1279` | ✅ 完整 |
| StuckProtocol dataclass | `backend/app/signals/types.py:1283-1301` | ✅ 完整 |
| TaskCardProtocol.stuck_protocol 字段 | `backend/app/signals/types.py:1351` | ✅ 完整 |
| TaskCardBuilder (6 task type builders) | `backend/app/signals/task_card_protocol.py` | ✅ 完整 |
| TaskCardGenerator (stuck_help generation) | `backend/app/orchestration/task_card_generator.py` | ✅ 完整 |
| POST /{task_id}/stuck 端点 | `backend/app/api/v1/tasks.py` | ✅ 完整 |
| TaskStuckRequest schema | `backend/app/schemas/task.py` | ✅ 完整 |
| Flutter StuckHelpSheet | `mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart` | ✅ 完整 |
| MistakeSignalDetector (consecutive errors) | `backend/app/signals/mistake_signal.py` | ✅ 完整 |
| Spine stuck detection (keyword match) | `backend/app/signals/spine_orchestrator.py:1833` | ✅ 完整 |

### 实际缺口

| # | 缺口 | 严重程度 | 描述 |
|---|------|---------|------|
| G1 | **无运行时 stuck_type 分类器** | 🔴 High | stuck_type 始终为 ""，从未根据用户行为动态判定 |
| G2 | **stuck_type 从未被任何 builder 设置** | 🔴 High | 所有 TaskCardBuilder 方法均未设置 stuck_type |
| G3 | **hint_strategy 硬编码** | 🟡 Medium | 由 TaskCardBuilder 固定设置，不随 stuck_type 调整 |
| G4 | **StuckHelpSheet 无 stuck_type 感知** | 🟡 Medium | Flutter 始终渲染通用建议，无类型特定帮助 |
| G5 | **无行为信号聚合层** | 🟡 Medium | 多种行为数据源存在但无统一聚合点 |

---

## 3. 文件清单 (File Inventory)

### 新建文件

| 文件 | 用途 |
|------|------|
| `backend/app/signals/stuck_type_classifier.py` | 核心分类器：行为信号聚合 + deterministic 规则引擎 |
| `backend/tests/unit/test_stuck_type_classifier.py` | StuckTypeClassifier 单元测试 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/signals/types.py` | StuckProtocol 新增 `classified_at`, `classification_confidence`, `classification_signals` 字段；新增 `StuckClassificationResult` dataclass |
| `backend/app/signals/__init__.py` | Export StuckTypeClassifier, StuckClassificationResult |
| `backend/app/services/task_service.py` | `mark_stuck()` 调用 StuckTypeClassifier，注入分类结果 |
| `backend/app/api/v1/tasks.py` | POST /{task_id}/stuck 响应包含 classification 详情 |
| `backend/app/schemas/task.py` | TaskStuckRequest 新增 `user_mood` 字段 |
| `mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart` | 根据 stuck_type 展示类型特定帮助 |
| `mobile/lib/l10n/app_en.arb` | 新增 ~18 个 stuck_type i18n keys |
| `mobile/lib/l10n/app_zh.arb` | 新增 ~18 个 stuck_type i18n keys |

---

## 4. 实现步骤 (Implementation Steps)

### Phase 1: 数据模型扩展 (0.5 day)

**Step 1.1**: 扩展 `StuckProtocol` (types.py:1283)：

```python
classified_at: str | None = None       # ISO timestamp
classification_confidence: float = 0.0  # 0.0-1.0
classification_signals: list[str] = field(default_factory=list)
```

**Step 1.2**: 新增 `StuckClassificationResult` dataclass：

```python
@dataclass
class StuckClassificationResult:
    stuck_type: str                    # concept|application|process|time|state|""
    confidence: float                   # 0.0-1.0
    primary_signal: str                # human-readable reason
    signal_ids: list[str]
    suggested_hint_strategy: str
    suggested_fallback_task_type: str | None
    evidence_summary: str
    user_visible_reason: str
```

### Phase 2: StuckTypeClassifier 核心实现 (2-3 days)

**Step 2.1**: 创建 `backend/app/signals/stuck_type_classifier.py`

Detection priority (first match wins):
- P1: **time** — overrun > 1.5x OR elapsed > 20min without progress
- P2: **concept** — MistakeSignalDetector triggered on bound_nodes OR feedback "unclear"
- P3: **state** — user_mood matches low-state keywords OR response feedback downturn > 60%
- P4: **application** — stuck at step > 1 but step progress > 30%
- P5: **process** — stuck at early step (<= 1) OR total progress < 20%
- P6: default — stuck_type="" (insufficient signals)

Each check method returns `StuckClassificationResult | None`.

**Step 2.2**: stuck_type→hint_strategy mapping:

| stuck_type | hint_strategy | fallback_task_type |
|------------|--------------|-------------------|
| concept | worked_example | study |
| application | worked_example | practice |
| process | simplify | artifact_build |
| time | skip | habit_action |
| state | ask_peer | review |

**Step 2.3**: Redis caching — `stuck:classification:{user_id}:{task_id}` key, 1h TTL.

### Phase 3: 集成到 Stuck 管线 (1 day)

**Step 3.1**: `task_service.py` 的 `mark_stuck()` 调用 classifier
**Step 3.2**: `POST /{task_id}/stuck` 响应增加 `stuck_type_classification` 字段
**Step 3.3**: 新增 `GET /{task_id}/stuck-classification` 读取缓存

### Phase 4: Flutter 端适配 (1-2 days)

**Step 4.1**: `StuckHelpSheet` 接收 `stuckType` 参数
**Step 4.2**: 5 种 stuck_type 各自独立 suggestion list
**Step 4.3**: stuck_type 徽章（图标+颜色+解释）显示在 sheet 顶部
**Step 4.4**: stuckType=null 时回退通用建议（backward compat）

### Phase 5: i18n (0.5 day)

新增 ~18 个 key 到 `app_en.arb` / `app_zh.arb`，覆盖 5 种 stuck_type 的建议文本和标题。

---

## 5. 测试计划 (Test Plan)

### Unit Tests — StuckTypeClassifier (8 tests)

| Test | 描述 |
|------|------|
| `test_classify_time_pressure_overrun` | actual/estimated > 1.5 → "time" |
| `test_classify_long_pause_no_progress` | elapsed > 1200s, step=0 → time/process |
| `test_classify_concept_error_streak` | 3+ consecutive errors on bound_node → "concept" |
| `test_classify_cognitive_state_mood` | user_mood="焦虑" → "state" |
| `test_classify_application_late_step` | step=3/4 → "application" |
| `test_classify_process_early_step` | step=0/4, long pause → "process" |
| `test_classify_priority_order` | time > concept > state > application > process |
| `test_classify_insufficient_signals` | No data → stuck_type="" confidence=0 |

### Integration Tests (4 tests)

| Test | 描述 |
|------|------|
| `test_mark_stuck_with_classification` | POST /{id}/stuck returns classification |
| `test_classification_cached_to_redis` | Redis key exists with correct data |
| `test_get_stuck_classification_endpoint` | GET returns cached result |
| `test_classification_graceful_no_redis` | No Redis → no error |

### Flutter Widget Tests (3 tests)

| Test | 描述 |
|------|------|
| `test_stuck_help_sheet_concept_type` | concept → concept suggestions |
| `test_stuck_help_sheet_time_type` | time → time suggestions |
| `test_stuck_help_sheet_null_fallback` | null → generic suggestions |

---

## 6. 验收标准 (Acceptance Criteria)

### Functional
- [ ] `StuckTypeClassifier.classify()` 根据行为信号判定 stuck_type
- [ ] Priority order 严格执行: time > concept > state > application > process
- [ ] `POST /{task_id}/stuck` 响应包含 `stuck_type_classification`
- [ ] 分类结果写入 Redis (TTL 3600s)
- [ ] StuckProtocol 的 classified_at/confidence/signals 字段正确填充
- [ ] StuckHelpSheet 根据 stuckType 展示差异化帮助
- [ ] 5 种 stuck_type 各自独立 suggestion list
- [ ] stuckType=null 回退通用建议（零回归）

### Non-Functional
- [ ] `classify()` < 50ms (deterministic, no LLM)
- [ ] Redis 读写不影响 stuck-mark 端点延迟
- [ ] 无内存泄漏（Redis keys 均有 TTL）

### Quality Gates
- [ ] 15 backend + 3 Flutter tests pass
- [ ] `flutter analyze` 无新增 warning
- [ ] 无 hardcoded secrets/tokens
- [ ] i18n 双语覆盖新增 UI 文本
- [ ] 现有 mark_task_stuck API 向后兼容

---

## 7. 设计决策 (Design Decisions)

| 决策 | 选择 | 理由 |
|------|------|------|
| 分类引擎 | Deterministic 规则引擎 (无 LLM) | 与 L1LightAurora, NonExamFirstMinuteDetector 模式一致；成本零增加 |
| State 存储 | Redis (TTL 1h) | 对齐 MistakeSignalDetector 模式；临时数据不需持久化 |
| Priority | 固定优先级链 (P1-P6) | 明确性>模糊性；规则引擎必须确定性可解释 |
| 调用时机 | 仅 POST /{task_id}/stuck | 避免每轮都跑分类器；stuck mark 是明确用户信号 |
| 向后兼容 | stuck_type="" as "unclassified" | 现有 TaskCardBuilder 仍可预置 stuck_type |

---

## 8. 依赖与阻塞 (Dependencies)

- Phase 2 (Classifier) 依赖 Phase 1 (data model)
- Phase 3 (API integration) 依赖 Phase 2
- Phase 4 (Flutter) 依赖 Phase 3 (API response stable)
- Phase 5 (i18n) 可并行于 Phase 2-4
- 内部依赖: MistakeSignalDetector Redis keys (reads only), cache_service.redis
- 无外部依赖阻塞

---

## 9. 开放问题 (Open Questions)

1. **Proactive classification**: 是否在 Celery beat 中定期扫描（如任务 in_progress > 30min 自动触发）？建议 Phase 1 保持 passive（仅用户点 stuck 时触发）。
2. **连续 stuck 模式**: 同一用户连续 3 次 stuck 都归为 "concept"，是否提升置信度基线？当前设计每次独立判断。
3. **user_mood 来源**: Flutter 是否在 stuck_help_sheet 打开时让用户选择情绪？建议 V1 从 stuck_point/trigger 文本提取关键词。
4. **classification_confidence 校准**: 初始固定值（overrun=0.85，mood=0.75）。后续是否需要 Bayesian 更新？

---

*Spec generated 2026-05-07 by claude-B (GAP Closer Agent)*
