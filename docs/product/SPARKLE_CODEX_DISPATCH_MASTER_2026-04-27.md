# Sparkle Codex Dispatch Master — v2.0 完全体落地

> **文档类型**: Codex Agent 并发 Dispatch 指令书
> **日期**: 2026-04-27
> **状态**: READY FOR DISPATCH
> **使用方式**: 每个 Codex agent 读取本文档 → 找到自己的 Task # → 执行

---

## Part 0: 所有 Agent 共用规则

### 0.1 项目上下文

Sparkle 是一个 AI-native 目标实现操作系统。三层架构：

```
Flutter (Mobile UI) → Go Gateway (Auth/Routing) → Python Engine (AI Logic)
```

你在 **Python Engine** 层工作，具体在 Signal-to-Action Spine 子系统。

### 0.2 必读参考文档

| 文档 | 路径 | 用途 |
|------|------|------|
| **路线图** | `docs/product/SPARKLE_V2_LIVING_EXPERIENCE_ROADMAP_2026-04-27.md` | 整体路线和任务定义 |
| **最终愿景** | `docs/product/SPARKLE_FULL_VISION_v1_2026-04-27.md` | 产品愿景和神性时刻 |
| **Causal Control OS** | `docs/product/SPARKLE_CAUSAL_CONTROL_OS_FINAL_2026-04-27.md` | 8 层架构详细规格 |
| **Spine 进度** | `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_PROGRESS_2026-04-27.md` | 已完成内容 |
| **Spine 方案** | `docs/product/SPARKLE_SIGNAL_TO_ACTION_SPINE_2026-04-27.md` | 技术方案 |
| **对齐文档** | `docs/product/SPARKLE_ALIGNMENT_2026-04-25.md` | Aurora Runtime v1 规格 |
| **CLAUDE.md** | `CLAUDE.md`（项目根目录） | 编码规范、文件约定、命令参考 |

### 0.3 代码规范

1. **语言**: Python 3.11，使用 `from __future__ import annotations`
2. **文件头**: 必须包含 Core/Phase/Stage 注释
3. **类型**: 所有函数必须有类型注解，使用 `dataclass`
4. **日志**: 使用 `loguru.logger`，不用 `logging`
5. **测试**: 使用 `pytest`，async 测试用 `asyncio` marker
6. **不使用**: 不用 `dataclasses_json`，不用 `pydantic`（API 层除外）
7. **序列化**: 每个数据类必须有 `to_dict()` 和 `from_dict()`
8. **UID 生成**: 使用 `from app.signals.types import _uid`

### 0.4 Spine Contract（12 条铁律）

每个新功能必须满足：

1. Signal 必须有且仅有一个 Policy 规则消费
2. Directive 必须有下游消费者
3. Audit 必须验证输出满足约束
4. Receipt 必须短、具体、可纠正
5. CausalTrace 必须记录完整链路
6. Outcome 必须记录干预结果
7. Kill switch 必须支持 off/shadow/live
8. **不写长期人格** (scope ≤ current_sprint)
9. 社群信号不直接写个人状态
10. 成就不直接改长期人格
11. 用户纠正 = 高置信度 claim
12. 所有参数有合理默认值

### 0.5 现有文件结构

```
backend/app/signals/          # Signal-to-Action Spine 所有模块
├── __init__.py               # 公共 API 导出
├── types.py                  # 7 核心数据对象 + 所有 dataclass
├── policy_engine.py          # PolicyEngine 规则仲裁
├── spine_orchestrator.py     # 全链路编排器
├── causal_trace_store.py     # CausalTrace Redis 存储
├── signal_ranker.py          # 信号排序 + 冲突解决
├── state_register.py         # 每用户持久化状态
├── directive_applier.py      # DirectiveApplier + DirectiveAuditor
├── outcome_recorder.py       # OutcomeRecorder + 归因
├── spine_metrics.py          # SpineMetricsCollector (10 指标)
├── task_timeout_detector.py  # 任务超时检测
├── exam_rescue_detector.py   # 考试意图检测
├── stale_state_guard.py      # 陈旧状态检测 + 恢复
├── state_packet_builder.py   # ActionableStatePacket 构建
├── achievement_reinforcement.py  # 成就动量 → 信号
├── recall_opportunity.py     # 4 种召回触发
├── predicted_reply_options.py # 快捷回答引擎
├── self_model.py             # 系统自建模
├── community_signal.py       # 社群信号检测
├── aurora_wake.py            # Aurora 唤醒判断
├── exam_sprint_policy.py     # D-7→D-0 考试冲刺策略
├── skill_extraction.py       # 策略→Skill 提取
├── source_tray_integration.py # SourceTray→Retrieval 集成
├── timeline_card_renderer.py # Timeline 卡片渲染 (P1-1 DONE)
├── mistake_signal.py         # 错因信号检测
├── material_signal.py        # 资料利用率信号
└── ...

backend/tests/unit/test_signal_spine.py  # 所有 spine 单元测试（349 tests）
backend/app/api/v1/aurora.py             # Spine REST API
```

### 0.6 测试规范

- 所有测试加到 `backend/tests/unit/test_signal_spine.py` 末尾
- 每个新方法至少 1 个测试
- 测试用 `# ══════` 分隔符 + 任务编号标题
- 不引入新依赖，只用 `pytest` + `unittest.mock`
- Mock Redis 用 `AsyncMock` 或 `MagicMock`
- **不要修改已有测试**
- 运行测试: `cd backend && python3 -m pytest tests/unit/test_signal_spine.py -q`

### 0.7 Definition of Done

1. [ ] CausalTrace 完整记录 signal → directive → outcome
2. [ ] UserVisibleReceipt 用户可见
3. [ ] DirectiveApplicationAudit 验证通过
4. [ ] 单元测试覆盖
5. [ ] E2E 测试覆盖关键路径
6. [ ] 零 TODO/FIXME
7. [ ] 无安全漏洞
8. [ ] 文档更新（progress doc 不需要你更新，main agent 会做）
9. [ ] 无 import 错误
10. [ ] 所有测试通过

### 0.8 关键接口

```python
# ActionableSignal — 所有信号的通用格式
from app.signals.types import ActionableSignal, _uid
signal = ActionableSignal(
    signal_id=_uid("sig"),
    source_event_ids=["evt_1"],
    source_system="your_detector",
    state_key="your_state_key",
    claim="your_claim",
    confidence=0.85,
    scope="current_sprint",
    ttl_hours=48,
    evidence_summary="human readable evidence",
    possible_effects=["effect_1", "effect_2"],
    priority="medium",
)

# PolicyEngine.evaluate() — 规则匹配
result = await policy_engine.evaluate(signal, context={})
# Returns None or (PolicyDecision, ExecutionDirective)

# SpineOrchestrator._run_signal_pipeline() — 完整链路
trace = await orchestrator._run_signal_pipeline(user_id="u1", signal=signal)

# PolicyEngine.build_*_directive() — 构建 9 类 directive
response_dir = policy_engine.build_response_directive(decision, signal)
plan_dir = policy_engine.build_plan_directive(decision, signal)
# ... 等等
```

---

## Part 1: 独立任务列表

### Task #1: Source Tray → RetrievalDirective 集成 (P1-2)

**目标**: 用户通过 SourceTray 控制什么资料进入 AI 上下文

**参考文件**:
- `backend/app/signals/types.py` — `SourceTrayState`, `SourceAsset`, `SourceSlice`, `RetrievalDirective`
- `backend/app/signals/source_tray_integration.py` — `compute_retrieval_plan()` 已存在
- `backend/app/signals/policy_engine.py` — `build_retrieval_directive()`
- `backend/app/signals/spine_orchestrator.py` — `_store_retrieval_directive()`

**需要做的**:
1. 在 `source_tray_integration.py` 中添加 `build_source_receipt()` 函数：
   - 输入: `RetrievalDirective`, `SourceTrayState`, 实际加载的 source_ids
   - 输出: dict 包含 `loaded`, `skipped`, `excluded`, `reason_for_user`
   - 格式: `{"loaded": [{"source_id": "s1", "title": "...", "reason": "user_selected"}], "skipped": [...], "reason_for_user": "使用了你选的 2 份资料，跳过了 1 份（解析失败）"}`

2. 在 `source_tray_integration.py` 中添加 `validate_source_tray_selections()` 函数：
   - 输入: `SourceTrayState`, 可用的 `List[SourceAsset]`
   - 输出: `SourceTrayState`（清洗后的），invalid selections 被移除
   - 规则: include 但 source 不在 available 中 → 移除

3. 在 `policy_engine.py` 的 `build_retrieval_directive()` 中集成 SourceTray：
   - 当 signal 是 `material_utilization/material_underutilized` 时，设置 `retrieval_mode="targeted_source_rag"`
   - 添加 `source_scope` 字段读取逻辑

4. 添加测试（至少 8 个）:
   - `test_build_source_receipt_with_loaded_sources`
   - `test_build_source_receipt_empty`
   - `test_build_source_receipt_mixed`
   - `test_validate_source_tray_removes_invalid`
   - `test_validate_source_tray_keeps_valid`
   - `test_retrieval_directive_source_tray_integration`
   - `test_retrieval_directive_material_signal`
   - `test_source_receipt_serialization`

**验收标准**:
- [ ] `build_source_receipt()` 返回结构化的资料使用回执
- [ ] `validate_source_tray_selections()` 清洗无效选择
- [ ] RetrievalDirective 在 material 信号时读取 SourceTray
- [ ] 8+ 测试通过
- [ ] 无 TODO/FIXME

---

### Task #2: Core Session Lifecycle (P1-3)

**目标**: 一次完整 goal→plan→execute→reflect 周期的状态管理

**参考文件**:
- `backend/app/signals/aurora_wake.py` — `AuroraWakeJudge` 已有
- `backend/app/signals/types.py` — 数据结构
- `backend/app/signals/spine_orchestrator.py` — `check_aurora_wake()`

**需要做的**:
1. 创建 `backend/app/signals/core_session.py`，包含：

```python
@dataclass
class CoreSession:
    session_id: str
    user_id: str
    goal_id: str | None
    phase: str              # "modeling" | "planning" | "executing" | "reflecting" | "completed"
    started_at: str
    updated_at: str
    pause_count: int = 0
    task_count: int = 0
    completed_task_count: int = 0
    last_directive_id: str | None = None
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]: ...
    
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CoreSession: ...


class CoreSessionManager:
    def __init__(self, redis_client: Any): ...
    
    async def create_session(self, user_id: str, goal_id: str | None = None) -> CoreSession: ...
    async def get_session(self, session_id: str) -> CoreSession | None: ...
    async def get_active_session(self, user_id: str) -> CoreSession | None: ...
    async def advance_phase(self, session_id: str, to_phase: str) -> CoreSession: ...
    async def pause_session(self, session_id: str) -> CoreSession: ...
    async def resume_session(self, session_id: str) -> CoreSession: ...
    async def complete_session(self, session_id: str) -> CoreSession: ...
    async def record_task(self, session_id: str, completed: bool = False) -> CoreSession: ...
    async def link_directive(self, session_id: str, directive_id: str) -> CoreSession: ...
```

2. Redis keys:
   - `spine:session:{session_id}` → JSON (TTL 7 days)
   - `spine:session_active:{user_id}` → session_id (TTL 7 days)

3. 在 `spine_orchestrator.py` 中添加：
   - `create_core_session(user_id)` → 委托 CoreSessionManager
   - `advance_session_phase(session_id, phase)` → 委托
   - 在 `_run_signal_pipeline()` 中自动 `link_directive`

4. 添加测试（至少 10 个）:
   - `test_core_session_create`
   - `test_core_session_advance_phases`
   - `test_core_session_pause_resume`
   - `test_core_session_complete`
   - `test_core_session_record_tasks`
   - `test_core_session_link_directive`
   - `test_core_session_serialization`
   - `test_core_session_manager_redis`
   - `test_core_session_active_user`
   - `test_spine_orchestrator_session_integration`

**验收标准**:
- [ ] Session lifecycle: create → advance → pause → resume → complete
- [ ] Redis 持久化 + TTL
- [ ] SpineOrchestrator 集成
- [ ] 10+ 测试通过

---

### Task #3: CommunityDirective v1 — 3 Loops (P1-4)

**目标**: 同伴错误→匿名提示、伙伴反馈→策略微调、资源评分→推荐优化

**参考文件**:
- `backend/app/signals/community_signal.py` — `CommunitySignalDetector` 已有
- `backend/app/signals/types.py` — `CommunityDirective` 已有
- `backend/app/signals/policy_engine.py` — `build_community_directive()` 已有
- `backend/app/signals/spine_orchestrator.py` — `on_community_cohort_data()`, `on_community_resource_data()`

**需要做的**:
1. 创建 `backend/app/signals/community_loops.py`，包含：

```python
class CommunityLoopManager:
    """3 community feedback loops."""
    
    # Loop 1: cohort_mistake → anonymous hint
    def build_cohort_mistake_hint(self, pattern: dict) -> dict[str, Any]:
        """Convert cohort mistake pattern to anonymous hint card.
        
        Input pattern: {knowledge_node_id, subject, mistake_type, cohort_size, error_count, common_misconception}
        Output: {hint_type, title, anonymous_summary, affected_nodes, tip}
        Rules: 
          - Never show individual student data
          - cohort_size < 3 → return None (too small)
          - Format: "有{cohort_size}位同学在{subject}的{topic}上容易犯{mistake_type}错误"
        """
    
    # Loop 2: partner_observation → strategy adjustment
    def apply_partner_feedback(self, feedback: dict) -> dict[str, Any] | None:
        """Process accountability partner observation.
        
        Input feedback: {partner_id, observation_type, observation_text, target_area}
        Output: {adjustment_type, strategy_patch, scope} or None
        Rules:
          - observation_type: "pacing" | "focus" | "difficulty" | "morale"
          - pacing → suggest pace adjustment (scope: next_48h)
          - focus → suggest topic refocus (scope: current_sprint)
          - difficulty → suggest difficulty shift (scope: next_48h)
          - morale → trigger encouragement (scope: this_turn)
          - Never write to personal state directly
        """
    
    # Loop 3: resource_quality → recommendation optimization
    def score_resource_quality(self, resource_data: dict) -> dict[str, Any]:
        """Score a shared resource for recommendation quality.
        
        Input: {resource_id, peer_ratings: list[float], usage_count, completion_rate, relevance_score}
        Output: {quality_score, recommendation_level, reason}
        Rules:
          - quality_score = avg(peer_ratings) * 0.5 + completion_rate * 0.3 + relevance_score * 0.2
          - recommendation_level: "high" (>=0.8) | "medium" (>=0.5) | "low" (<0.5)
          - usage_count < 3 → too_few_data, quality_score = None
        """
```

2. 在 `spine_orchestrator.py` 中添加:
   - `on_partner_observation()` — 调用 `CommunityLoopManager.apply_partner_feedback()` → signal pipeline
   - 更新 `on_community_cohort_data()` 使用 `build_cohort_mistake_hint()`
   - 更新 `on_community_resource_data()` 使用 `score_resource_quality()`

3. 在 `policy_engine.py` 中添加 partner_observation 规则:
   - `state_key=community_partner_feedback`, claim `pacing_too_fast/slow` → PlanDirective scope=next_48h

4. 添加测试（至少 10 个）:
   - `test_cohort_mistake_hint_basic`
   - `test_cohort_mistake_hint_too_small`
   - `test_cohort_mistake_hint_anonymous`
   - `test_partner_feedback_pacing`
   - `test_partner_feedback_focus`
   - `test_partner_feedback_morale`
   - `test_resource_quality_high`
   - `test_resource_quality_low`
   - `test_resource_quality_too_few_data`
   - `test_community_loop_serialization`

**验收标准**:
- [ ] 3 loops 各有完整数据流
- [ ] 隐私: 不暴露个体数据
- [ ] PolicyEngine 有 partner_feedback 规则
- [ ] 10+ 测试通过

---

### Task #4: SkillDirective v1 — inject/recommend/extract (P1-5)

**目标**: Skill 注入任务生成、推荐用户确认、触发新提取

**参考文件**:
- `backend/app/signals/skill_extraction.py` — `SkillExtractionService` 已有
- `backend/app/signals/types.py` — `SkillDirective`, `SkillEntry` 已有
- `backend/app/signals/policy_engine.py` — `build_skill_directive()` 已有

**需要做的**:
1. 创建 `backend/app/signals/skill_lifecycle.py`，包含：

```python
class SkillLifecycleManager:
    """Skill inject/recommend/extract lifecycle."""
    
    def __init__(self, redis_client: Any): ...
    
    # Store/retrieve skills
    async def store_skill(self, user_id: str, skill: SkillEntry) -> None: ...
    async def get_user_skills(self, user_id: str) -> list[SkillEntry]: ...
    async def get_skill(self, skill_id: str) -> SkillEntry | None: ...
    
    # Inject: find applicable skills for current context
    def find_applicable_skills(
        self,
        skills: list[SkillEntry],
        context: dict[str, Any],
    ) -> list[SkillEntry]:
        """Find skills matching current goal_mode/state_key.
        Rules:
          - scope match: personal skills first, then cohort, then system
          - applicable_when match: goal_mode and/or state_key
          - min effective_count >= 3
          - Sort by effective_count descending
        """
    
    # Build worked-example-repair TCP (Transfer Control Protocol)
    def build_worked_example_repair(self, skill: SkillEntry, task_context: dict) -> dict[str, Any]:
        """Convert a skill into a worked-example-repair task modification.
        
        Output: {
            "task_type_override": "worked_example_then_drill",
            "strategy_summary": skill.strategy["intervention_summary"],
            "applies_to_nodes": skill.applicable_when.get("state_key"),
            "evidence": skill.evidence,
        }
        """
    
    # Recommend: build user-facing skill recommendation
    def build_recommendation(self, skill: SkillEntry) -> dict[str, Any] | None:
        """Build a user-confirmable skill recommendation.
        Rules:
          - Only recommend skills with effective_count >= 5
          - Show evidence summary, not raw data
          - Include "not now" and "don't suggest again" options
        """
    
    # Validate skill before extraction
    def validate_extraction(self, skill: SkillEntry) -> dict[str, Any]:
        """Validate a candidate skill before extraction.
        Returns: {"valid": bool, "issues": list[str]}
        """
```

2. Redis keys:
   - `spine:skills:{user_id}` → JSON list of SkillEntry
   - `spine:skill:{skill_id}` → JSON SkillEntry (TTL 30 days)

3. 在 `spine_orchestrator.py` 中添加:
   - `get_applicable_skills(user_id, context)` → 委托 SkillLifecycleManager
   - `inject_skill_to_task(user_id, task_spec, context)` → find + apply worked-example-repair
   - `recommend_skill(user_id)` → find recommendable skills

4. 添加测试（至少 10 个）:
   - `test_skill_store_and_retrieve`
   - `test_find_applicable_skills_by_scope`
   - `test_find_applicable_skills_by_context`
   - `test_find_applicable_min_effective_count`
   - `test_build_worked_example_repair`
   - `test_build_recommendation_high_evidence`
   - `test_build_recommendation_low_evidence_none`
   - `test_validate_extraction_valid`
   - `test_validate_extraction_issues`
   - `test_skill_lifecycle_serialization`

**验收标准**:
- [ ] Skill store/retrieve 正确
- [ ] find_applicable_skills 按 scope/context/effective_count 筛选
- [ ] worked-example-repair TCP 生成正确
- [ ] 推荐包含用户选项
- [ ] 10+ 测试通过

---

### Task #5: Goal-Respectful Recall — Notification 集成 (P1-6)

**目标**: RecallOpportunity → NotificationDirective → 用户收到有意义的提醒

**参考文件**:
- `backend/app/signals/recall_opportunity.py` — `RecallOpportunityDetector` 已有 (4 triggers)
- `backend/app/signals/types.py` — `NotificationDirective` 已有
- `backend/app/signals/policy_engine.py` — `build_notification_directive()` 已有
- `backend/app/signals/spine_orchestrator.py` — `on_recall_check()` 已有

**需要做的**:
1. 创建 `backend/app/signals/recall_notification.py`，包含：

```python
@dataclass
class RecallMessage:
    message_id: str
    trigger_type: str        # undigested_material | task_not_started | task_missed | pre_exam_silence
    strategy: str            # low_effort_next_step | recovery_offer | quick_review_offer
    title: str               # 用户可见标题
    body: str                # 用户可见正文
    deep_link: str           # 点击后跳转路径
    cooldown_until: str | None  # 冷却截止时间
    frequency_tag: str       # 1_per_day | 2_per_day
    to_dict(self) -> dict: ...
    
    @classmethod
    def from_dict(cls, d: dict) -> RecallMessage: ...


class RecallNotificationBuilder:
    """Build user-facing recall messages from NotificationDirective."""
    
    MESSAGE_TEMPLATES: dict[str, dict[str, str]] = {
        "undigested_material": {
            "low_effort_next_step": {
                "title": "你的课件还没看完",
                "body": "上次上传的{material_count}份资料，还有{undigested}份没诊断。花5分钟看看？",
                "deep_link": "/materials?filter=undigested",
            },
        },
        "task_not_started": {
            "low_effort_next_step": {
                "title": "任务等你开始",
                "body": "今天的第一个任务还没开始，要不要先看一眼？",
                "deep_link": "/tasks?status=pending",
            },
        },
        "task_missed": {
            "recovery_offer": {
                "title": "有个任务错过了",
                "body": "没关系，帮你重新安排了一个更合适的任务。",
                "deep_link": "/tasks?status=recovery",
            },
        },
        "pre_exam_silence": {
            "quick_review_offer": {
                "title": "考前快速复习",
                "body": "还有{days_to_exam}天就考了，要不要快速过一遍高频考点？",
                "deep_link": "/review?mode=quick",
            },
        },
    }
    
    def build_message(
        self,
        trigger_type: str,
        message_strategy: str,
        context: dict[str, Any],
    ) -> RecallMessage | None: ...
    
    def check_cooldown(
        self,
        user_id: str,
        trigger_type: str,
        redis_client: Any,
    ) -> bool:
        """Check if user is in cooldown for this trigger type.
        Cooldowns: undigested_material=24h, task_not_started=12h, task_missed=8h, pre_exam_silence=6h
        """
    
    def record_sent(self, user_id: str, trigger_type: str, redis_client: Any) -> None:
        """Record that a recall message was sent, starting cooldown."""
    
    def build_user_preference_schema(self) -> dict[str, Any]:
        """Return the schema for user recall preferences.
        {trigger_type: {enabled: bool, quiet_hours: str, max_per_day: int}}
        """
```

2. 在 `spine_orchestrator.py` 中添加:
   - `build_recall_notification(user_id, trigger_type, context)` → 组合 RecallNotificationBuilder + NotificationDirective

3. 添加测试（至少 10 个）:
   - `test_recall_message_undigested_material`
   - `test_recall_message_task_not_started`
   - `test_recall_message_task_missed`
   - `test_recall_message_pre_exam_silence`
   - `test_recall_message_unknown_trigger_none`
   - `test_recall_cooldown_check`
   - `test_recall_cooldown_not_in_cooldown`
   - `test_recall_record_sent`
   - `test_recall_user_preference_schema`
   - `test_recall_message_serialization`

**验收标准**:
- [ ] 4 trigger types × 对应 message strategy 有正确模板
- [ ] 冷却期按 trigger type 区分
- [ ] 用户偏好 schema 返回
- [ ] 10+ 测试通过

---

### Task #6: P2-1 — PolicyEffectLedger 高级分析

**目标**: 从 PolicyEffectLedger 中提取策略模式，支持异步深度分析

**参考文件**:
- `backend/app/signals/outcome_recorder.py` — `OutcomeRecorder` 已有 `get_recent_policy_effects()`
- `backend/app/signals/skill_extraction.py` — `SkillExtractionService` 已有
- `backend/app/signals/policy_engine.py` — `_apply_shadow_learning()` 已有

**需要做的**:
1. 创建 `backend/app/signals/policy_analytics.py`，包含：

```python
class PolicyAnalytics:
    """Analyze policy effectiveness patterns from PolicyEffectLedger."""
    
    def __init__(self, redis_client: Any): ...
    
    def compute_strategy_accuracy(self, effects: list[PolicyEffectEntry]) -> dict[str, float]:
        """Compute accuracy per policy_key.
        Returns: {policy_key: accuracy_ratio}
        """
    
    def detect_degrading_strategies(self, effects: list[PolicyEffectEntry], window: int = 10) -> list[str]:
        """Find policy_keys where recent accuracy < historical accuracy.
        Compare last `window` entries vs all entries.
        """
    
    def compute_confidence_distribution(self, effects: list[PolicyEffectEntry]) -> dict[str, Any]:
        """Distribution of attribution_confidence.
        Returns: {mean, median, std, min, max, count}
        """
    
    def suggest_policy_review(self, effects: list[PolicyEffectEntry]) -> list[dict[str, Any]]:
        """Suggest which policies need human review.
        Criteria: accuracy < 0.5, or confidence declining, or mixed user feedback
        """
    
    def build_analytics_snapshot(self, user_id: str, effects: list[PolicyEffectEntry]) -> dict[str, Any]:
        """Build a complete analytics snapshot for a user's policy effects.
        Returns: {total_effects, accuracy_by_policy, degrading, confidence_stats, review_suggestions}
        """
```

2. 添加测试（至少 8 个）:
   - `test_compute_strategy_accuracy_basic`
   - `test_compute_strategy_accuracy_empty`
   - `test_detect_degrading_strategies`
   - `test_detect_degrading_stable`
   - `test_compute_confidence_distribution`
   - `test_suggest_policy_review`
   - `test_suggest_policy_review_none_needed`
   - `test_build_analytics_snapshot`

**验收标准**:
- [ ] 5 个分析方法完整
- [ ] 空输入安全处理
- [ ] 8+ 测试通过

---

### Task #7: P2-2 — Skill Lifecycle 完善 (验证→推广→废弃)

**目标**: Skill 完整生命周期 — 从验证到推广到废弃

**参考文件**:
- `backend/app/signals/skill_extraction.py` — `SkillExtractionService`
- `backend/app/signals/types.py` — `SkillEntry` (有 scope, evidence, effective_count)

**需要做的**:
1. 创建 `backend/app/signals/skill_lifecycle.py` (如果 Task #4 已创建，在同一文件中添加)

```python
class SkillLifecycleManager:
    # ... (Task #4 的内容)
    
    # 新增：验证→推广→废弃
    
    async def promote_skill(self, user_id: str, skill_id: str, to_scope: str) -> SkillEntry | None:
        """Promote a skill from personal → cohort → system.
        Rules:
          - personal → cohort: effective_count >= 10, avg_confidence >= 0.8
          - cohort → system: effective_count >= 50, avg_confidence >= 0.85
          - Only if privacy.shareable == True
        """
    
    async def deprecate_skill(self, user_id: str, skill_id: str, reason: str) -> None:
        """Mark a skill as deprecated.
        Rules:
          - Don't delete, set evidence["deprecated"] = True
          - Record deprecation reason and timestamp
        """
    
    async def auto_deprecate_check(self, user_id: str) -> list[str]:
        """Check if any skills should be auto-deprecated.
        Criteria: effective_count hasn't increased in 30 days, or last 5 outcomes are insufficient
        Returns: list of deprecated skill_ids
        """
    
    def compute_skill_health(self, skill: SkillEntry) -> dict[str, Any]:
        """Compute health metrics for a skill.
        Returns: {health_score, trend, recommendation}
        health_score = effective_count / sample_size
        trend: "improving" | "stable" | "declining"
        """
```

2. 添加测试（至少 8 个）:
   - `test_promote_skill_personal_to_cohort`
   - `test_promote_skill_insufficient_evidence`
   - `test_promote_skill_cohort_to_system`
   - `test_deprecate_skill`
   - `test_auto_deprecate_stale_skill`
   - `test_auto_deprecate_healthy_skill`
   - `test_compute_skill_health_good`
   - `test_compute_skill_health_declining`

**验收标准**:
- [ ] promote 有门槛限制
- [ ] deprecate 不删除，标记
- [ ] auto_deprecate 有时间窗口
- [ ] 8+ 测试通过

---

### Task #8: P2-3 — Relationship Model (用户-AI 关系建模)

**目标**: 建模用户与 AI 的关系状态，影响策略选择

**参考文件**:
- `backend/app/signals/self_model.py` — `SparkleSelfModelService` 已有
- `backend/app/signals/types.py`

**需要做的**:
1. 创建 `backend/app/signals/relationship_model.py`，包含：

```python
@dataclass
class RelationshipState:
    user_id: str
    trust_level: float          # 0-1, starts at 0.5
    interaction_style: str      # "exploratory" | "directive" | "passive" | "corrective"
    correction_frequency: float # corrections per 10 interactions
    engagement_depth: str       # "surface" | "moderate" | "deep"
    last_interaction_at: str
    total_interactions: int = 0
    total_corrections: int = 0
    total_confirmations: int = 0
    preferences: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> RelationshipState: ...


class RelationshipModelService:
    def __init__(self, redis_client: Any): ...
    
    async def get_or_create(self, user_id: str) -> RelationshipState: ...
    async def update_from_interaction(self, user_id: str, interaction_type: str) -> RelationshipState:
        """Update relationship from an interaction.
        interaction_type: "confirmed" | "corrected" | "dismissed" | "expanded" | "ignored"
        Rules:
          - confirmed → trust_level += 0.02 (cap 1.0)
          - corrected → trust_level -= 0.05 (floor 0.1)
          - dismissed → trust_level -= 0.01
          - Update interaction_style based on correction_frequency
        """
    
    async def get_strategy_adjustment(self, user_id: str) -> dict[str, Any]:
        """Get strategy adjustments based on relationship state.
        Returns: {tone_adjustment, proactivity_level, explanation_depth}
        Rules:
          - trust < 0.3 → conservative (confirm before acting, brief explanations)
          - trust > 0.8 → proactive (act first, summarize)
          - corrective style → always provide "why" evidence
          - passive style → reduce frequency, increase incentives
        """
```

2. 添加测试（至少 8 个）:
   - `test_relationship_create_default`
   - `test_relationship_update_confirmed`
   - `test_relationship_update_corrected`
   - `test_relationship_update_dismissed`
   - `test_relationship_trust_bounds`
   - `test_relationship_interaction_style`
   - `test_relationship_strategy_conservative`
   - `test_relationship_strategy_proactive`

**验收标准**:
- [ ] trust_level 有上下界
- [ ] 4 种 interaction type 各有信任度调整
- [ ] strategy_adjustment 基于 trust 和 style
- [ ] 8+ 测试通过

---

### Task #9: P3-1 — GoalWorldGraph 泛化 (Goal Type 抽象)

**目标**: 从考试冲刺泛化到任何目标类型

**参考文件**:
- `backend/app/signals/exam_sprint_policy.py` — `ExamSprintPolicyService` 已有
- `backend/app/signals/exam_rescue_detector.py` — 考试意图检测
- `backend/app/services/galaxy_service.py` — Galaxy 知识星图

**需要做的**:
1. 创建 `backend/app/signals/goal_type_adapter.py`，包含：

```python
@dataclass
class GoalTypeProfile:
    goal_type: str              # "exam" | "project" | "job_search" | "fitness" | "startup" | "general"
    deadline_sensitive: bool
    mastery_trackable: bool
    has_knowledge_graph: bool
    default_phase_count: int
    default_sprint_duration_days: int
    node_label: str             # "知识点" | "里程碑" | "技能" | etc.
    
    @classmethod
    def get_profile(cls, goal_type: str) -> GoalTypeProfile: ...


GOAL_TYPE_PROFILES = {
    "exam": GoalTypeProfile(
        goal_type="exam", deadline_sensitive=True, mastery_trackable=True,
        has_knowledge_graph=True, default_phase_count=5, default_sprint_duration_days=7,
        node_label="知识点",
    ),
    "project": GoalTypeProfile(
        goal_type="project", deadline_sensitive=True, mastery_trackable=False,
        has_knowledge_graph=False, default_phase_count=4, default_sprint_duration_days=14,
        node_label="里程碑",
    ),
    "job_search": GoalTypeProfile(
        goal_type="job_search", deadline_sensitive=False, mastery_trackable=True,
        has_knowledge_graph=True, default_phase_count=5, default_sprint_duration_days=30,
        node_label="技能",
    ),
    "fitness": GoalTypeProfile(
        goal_type="fitness", deadline_sensitive=False, mastery_trackable=True,
        has_knowledge_graph=False, default_phase_count=3, default_sprint_duration_days=30,
        node_label="训练目标",
    ),
    "startup": GoalTypeProfile(
        goal_type="startup", deadline_sensitive=True, mastery_trackable=False,
        has_knowledge_graph=False, default_phase_count=6, default_sprint_duration_days=14,
        node_label="交付物",
    ),
    "general": GoalTypeProfile(
        goal_type="general", deadline_sensitive=False, mastery_trackable=False,
        has_knowledge_graph=False, default_phase_count=3, default_sprint_duration_days=7,
        node_label="步骤",
    ),
}


class GoalTypeAdapter:
    """Adapt spine policies to different goal types."""
    
    def adapt_mastery_mapping(self, mastery: float, goal_type: str) -> dict[str, Any]:
        """Map mastery score to task type/difficulty based on goal type.
        For exam: concept_compression → mixed_practice (existing)
        For project: outline → draft → review → submit
        For job_search: learn → practice → mock → apply
        """
    
    def adapt_sprint_phases(self, days_to_deadline: int, goal_type: str) -> list[dict[str, Any]]:
        """Generate sprint phase strategy based on goal type and time remaining."""
    
    def adapt_recall_message(self, trigger_type: str, goal_type: str, context: dict) -> str:
        """Adjust recall message language based on goal type.
        "考试" → "考前复习" for exam
        "截止" → "交付前检查" for project
        """
```

2. 添加测试（至少 8 个）:
   - `test_goal_type_profile_exam`
   - `test_goal_type_profile_project`
   - `test_goal_type_profile_job_search`
   - `test_goal_type_profile_general`
   - `test_adapt_mastery_mapping_exam`
   - `test_adapt_mastery_mapping_project`
   - `test_adapt_sprint_phases`
   - `test_adapt_recall_message`

**验收标准**:
- [ ] 6 种 goal type 有 profile
- [ ] mastery mapping 按 goal type 差异化
- [ ] sprint phases 按 goal type 和时间生成
- [ ] recall message 按 goal type 适配
- [ ] 8+ 测试通过

---

### Task #10: P3-2 — Growth Chronicle (成长叙事)

**目标**: 用户共治的成长叙事系统

**参考文件**:
- `backend/app/signals/types.py` — `OutcomeRecord`, `CausalTrace`
- `backend/app/services/achievement_engine.py` — 成就系统

**需要做的**:
1. 创建 `backend/app/signals/growth_chronicle.py`，包含：

```python
@dataclass
class ChronicleEntry:
    entry_id: str
    user_id: str
    entry_type: str           # "milestone" | "turning_point" | "pattern_discovered" | "user_reflection"
    timestamp: str
    title: str                # 用户可见标题
    narrative: str            # 1-3 句故事
    evidence_refs: list[str]  # trace_id / outcome_id / achievement_id
    user_editable: bool       # True = 用户可以编辑/隐藏
    user_hidden: bool = False
    
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> ChronicleEntry: ...


class GrowthChronicleService:
    def __init__(self, redis_client: Any): ...
    
    async def add_entry(self, user_id: str, entry: ChronicleEntry) -> None: ...
    async def get_chronicle(self, user_id: str, limit: int = 20) -> list[ChronicleEntry]: ...
    async def hide_entry(self, user_id: str, entry_id: str) -> None: ...
    async def edit_entry(self, user_id: str, entry_id: str, new_narrative: str) -> None: ...
    
    def build_milestone_from_outcome(self, outcome: dict) -> ChronicleEntry | None:
        """Build a milestone entry from a positive OutcomeRecord.
        Rules:
          - Only for attribution="effective" with confidence >= 0.8
          - Title from intervention summary
          - Narrative: "你连续{count}次完成了{type}任务，系统发现{strategy}对你特别有效。"
        """
    
    def build_turning_point_from_correction(self, correction: dict) -> ChronicleEntry:
        """Build a turning point from a user correction.
        Narrative: "系统对{topic}的判断有偏差，你纠正了它。这让系统学会了{lesson}。"
        """
    
    def build_pattern_discovery(self, patterns: list[dict]) -> ChronicleEntry | None:
        """Build a pattern discovery from multiple outcomes.
        Rules:
          - Need >= 5 outcomes with same strategy
          - Summarize the pattern in user language
        """
    
    async def generate_weekly_summary(self, user_id: str) -> str:
        """Generate a weekly narrative summary.
        Not AI-generated — template-based from ChronicleEntry aggregation.
        """
```

2. Redis keys:
   - `spine:chronicle:{user_id}` → JSON list of ChronicleEntry (TTL 90 days)

3. 添加测试（至少 8 个）:
   - `test_chronicle_entry_create`
   - `test_build_milestone_from_outcome`
   - `test_build_milestone_insufficient_outcome`
   - `test_build_turning_point_from_correction`
   - `test_build_pattern_discovery`
   - `test_chronicle_hide_entry`
   - `test_chronicle_edit_entry`
   - `test_weekly_summary`

**验收标准**:
- [ ] 3 种 entry type (milestone/turning_point/pattern)
- [ ] 用户可编辑/隐藏 (user_editable=True)
- [ ] 不是 surveillance — 是用户共治叙事
- [ ] 8+ 测试通过

---

## Part 2: 任务依赖图

```
Task #1 (Source Tray)      ──→ Task #5 (Recall Notification)
Task #2 (Core Session)     ──→ Task #3 (Community)
Task #3 (Community)        ──→ Task #4 (Skill)
Task #4 (Skill)            ──→ Task #7 (Skill Lifecycle)
Task #6 (Policy Analytics) ──→ 独立
Task #8 (Relationship)     ──→ 独立
Task #9 (Goal Type)        ──→ 独立
Task #10 (Growth Chronicle)──→ 独立

可并发组:
  Wave 1: Task #1, #2, #6, #8, #9, #10 (6 个独立)
  Wave 2: Task #3, #5 (依赖 #2 和 #1)
  Wave 3: Task #4 (依赖 #3)
  Wave 4: Task #7 (依赖 #4)
```

---

## Part 3: Agent Prompt 模板

每个 Codex agent 的 prompt 格式:

```
你是 Sparkle 项目的一名 Codex 执行 agent。

## 你的任务

读取文件: docs/product/SPARKLE_CODEX_DISPATCH_MASTER_2026-04-27.md
执行任务: Task #{N}

## 必读文件
1. docs/product/SPARKLE_CODEX_DISPATCH_MASTER_2026-04-27.md — 找到你的 Task # 并执行
2. CLAUDE.md — 编码规范
3. 你的 Task 中列出的参考文件

## 工作方式
1. 读取 Task #{N} 的完整描述
2. 读取所有参考文件，理解现有代码
3. 创建新文件或修改现有文件（遵循 CLAUDE.md 规范）
4. 在 backend/tests/unit/test_signal_spine.py 末尾添加测试
5. 运行测试: cd backend && python3 -m pytest tests/unit/test_signal_spine.py -q
6. 确保所有测试通过

## 约束
- 不要修改已有测试
- 不要修改你不负责的文件（除非 Task 明确要求）
- 所有新数据结构必须有 to_dict() 和 from_dict()
- 使用 from __future__ import annotations
- 使用 loguru logger
- 使用 from app.signals.types import _uid 生成 ID
- 不要引入新的 pip 依赖
```
