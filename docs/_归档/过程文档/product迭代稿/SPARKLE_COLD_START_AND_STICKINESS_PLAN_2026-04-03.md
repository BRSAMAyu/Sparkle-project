# Sparkle — Cold Start & Stickiness Implementation Plan

**Date**: 2026-04-03
**Status**: In Progress
**Purpose**: Close the gap between "system is intelligent" and "user feels it from day 1"

---

## The Core Problem

Everything built works for a returning user with 2+ weeks of history. A new user on day 1 sees:
- Empty home screen (no plan, no mastery signal, no MIT)
- Empty galaxy (no nodes)
- Generic AI responses (companion section fires but fields are empty)
- No interventions (no patterns detected yet)
- No strategy personalization (< 5 samples required)

The backend story loop is complete. The gap is **activation latency** — the system needs data before it helps, but it only gets data by helping first.

**Solution**: Push the intelligence boundary to session 1 by seeding the environment from the onboarding data we already collect.

---

## Stage Overview

| Stage | What | Impact | Duration |
|-------|------|--------|----------|
| 1 | First Conversation — AI initiates after onboarding | Intelligence activates session 1 | 1 day |
| 2 | Galaxy seed nodes from goal | Galaxy is a map from day 1, not empty | 1 day |
| 3 | Cohort priors for strategy learning | Interventions are informed from session 1 | 0.5 day |
| 4 | Community signals visible in AI + home | Peer signals feel real, not silent | 0.5 day |
| 5 | Stickiness moments — surface generated evidence | User sees proof the system remembers them | 1 day |
| 6 | Galaxy evidence mode — mastery milestone animations | Growth is visible, galaxy = proof of progress | 1 day |

**Total**: ~5 days

---

## Stage 1: First Conversation — AI Initiates After Onboarding

### Problem
After `submitOnboarding()` succeeds, the app does `context.go('/home')`. The user arrives at an empty home screen with no direction. The AI is ready but silent.

### What Changes

#### Backend: `backend/app/api/v1/profile_transparency.py`
Extend the existing `POST /profile/onboarding` response to include a `first_message` field — an AI-generated opening message framed around the user's stated goal.

```python
# At end of submit_onboarding(), after saving preferences and goal:
first_message = await _generate_first_session_message(
    learning_goal=payload.learning_goal,
    learning_goal_type=payload.learning_goal_type,
    knowledge_level=payload.knowledge_level,
    study_time_minutes=payload.study_time_minutes,
)
return {"status": "ok", "updated": updated, "first_message": first_message}
```

New helper:
```python
async def _generate_first_session_message(
    *,
    learning_goal: str | None,
    learning_goal_type: str | None,
    knowledge_level: str | None,
    study_time_minutes: int | None,
) -> str:
    """Generate a personalized opening message for the user's first chat session."""
    if not learning_goal:
        return "你好！我是 Sparkle。告诉我你现在最想突破的学习难关，我们一起来想办法。"

    goal_type_map = {
        "exam": "考试备考",
        "skill": "技能学习",
        "interest": "兴趣探索",
    }
    goal_type_label = goal_type_map.get(learning_goal_type or "", "学习目标")
    time_label = f"每天 {study_time_minutes} 分钟" if study_time_minutes else "你的时间"
    level_map = {
        "beginner": "刚开始接触",
        "intermediate": "有一些基础",
        "advanced": "已经有较深积累",
    }
    level_label = level_map.get(knowledge_level or "", "")

    lines = [f"你好！我已经了解你想推进「{learning_goal}」这个{goal_type_label}目标。"]
    if level_label:
        lines.append(f"你目前{level_label}，我会根据这个来调整建议的节奏。")
    lines.append(f"我们用{time_label}来开始——先告诉我：你现在这个目标里，觉得最卡住的是哪一块？")
    return "\n".join(lines)
```

**Files changed**:
- `backend/app/api/v1/profile_transparency.py` — add `_generate_first_session_message()`, update `submit_onboarding()` return

#### Flutter: `mobile/lib/features/user/data/repositories/user_repository.dart`
`submitOnboarding()` already returns the response. Update it to surface `first_message`.

```dart
// In submitOnboarding():
Future<String?> submitOnboarding(Map<String, dynamic> payload) async {
  final response = await _apiClient.post('/profile/onboarding', data: payload);
  return response.data?['first_message'] as String?;
}
```

#### Flutter: `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart`
After `submitOnboarding()` succeeds, navigate to `/chat` with the first message pre-loaded instead of `/home`.

```dart
// In _handleContinue(), replace context.go('/home') with:
final firstMessage = await repo.submitOnboarding({...});
await ref.read(onboardingCompletedProvider.notifier).setCompleted(true);
// Invalidate providers...
if (mounted) {
  if (firstMessage != null && firstMessage.isNotEmpty) {
    context.go('/chat', extra: {'initial_ai_message': firstMessage});
  } else {
    context.go('/home');
  }
}
```

#### Flutter: Chat screen — accept `initial_ai_message` extra
The chat screen needs to display the AI's opening message when launched with `initial_ai_message` in route extras. The message should appear as an AI bubble immediately, before the user types anything. This does NOT call the backend — it's a local display of the pre-generated message from onboarding.

**Files changed**:
- `mobile/lib/features/user/data/repositories/user_repository.dart`
- `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart`
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (or relevant chat entry point)

### Verification
Open app as new user → complete onboarding → lands in chat with AI message that names their goal → user replies with their weak area → AI responds with a focused plan draft within 3 turns.

---

## Stage 2: Galaxy Seed Nodes from Goal

### Problem
After onboarding, the galaxy is empty. The user has no map of where they're going. First task completion lights a node — but there are no nodes to light until the AI creates a plan, which only happens after the first chat session.

### What Changes

#### Backend: New `GalaxyBootstrapService`
**New file**: `backend/app/services/galaxy_bootstrap_service.py`

```python
"""Bootstrap a minimal galaxy from onboarding goal data."""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.galaxy_service import GalaxyService
from app.models.galaxy import KnowledgeNode

GOAL_TYPE_SEED_MAP: dict[str, list[dict]] = {
    "exam": [
        {"name": "核心概念理解", "description": "目标学科的基础概念与定义"},
        {"name": "典型题型训练", "description": "高频考题结构与解题方法"},
        {"name": "错题归因分析", "description": "分析失分原因，针对性改进"},
        {"name": "时间管理策略", "description": "备考节奏规划与复习周期设计"},
        {"name": "模拟考试评估", "description": "阶段性水平测验与差距识别"},
    ],
    "skill": [
        {"name": "基础技能搭建", "description": "该技能的核心入门知识"},
        {"name": "实践项目练习", "description": "通过具体项目积累经验"},
        {"name": "难点突破", "description": "当前阶段最容易卡住的地方"},
        {"name": "进阶技巧", "description": "区分初级和中级水平的关键能力"},
        {"name": "应用场景拓展", "description": "将技能应用到实际场景"},
    ],
    "interest": [
        {"name": "领域概览", "description": "该兴趣领域的整体地图"},
        {"name": "入门资源精选", "description": "最值得先接触的内容"},
        {"name": "核心概念", "description": "理解这个领域的关键概念"},
        {"name": "深度探索方向", "description": "最有深度可挖的方向"},
        {"name": "实践与表达", "description": "用行动加深理解"},
    ],
}

DEFAULT_SEEDS = [
    {"name": "目标拆解", "description": "将大目标分解为可执行的小步骤"},
    {"name": "基础知识盘点", "description": "梳理已知与未知的边界"},
    {"name": "核心难点识别", "description": "找出最需要突破的卡点"},
    {"name": "学习节奏建立", "description": "建立稳定、可持续的学习习惯"},
    {"name": "进展追踪", "description": "定期回顾目标与实际进度"},
]


class GalaxyBootstrapService:
    """Create scaffold knowledge nodes from onboarding goal data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.galaxy_service = GalaxyService(db)

    async def seed_from_goal(
        self,
        *,
        user_id: UUID,
        learning_goal: str | None,
        goal_type: str | None,
    ) -> list[KnowledgeNode]:
        """Create 5 scaffold nodes for the user's galaxy based on their goal."""
        seeds = GOAL_TYPE_SEED_MAP.get(goal_type or "", DEFAULT_SEEDS)
        created: list[KnowledgeNode] = []
        for i, seed in enumerate(seeds[:5]):
            node = await self.galaxy_service.create_node(
                user_id=user_id,
                name=seed["name"],
                description=seed["description"],
                keywords=["onboarding_seed", f"goal_type:{goal_type or 'general'}", f"rank:{i}"],
                mastery_score=0,
                is_user_node=True,
            )
            created.append(node)
        await self.db.flush()
        return created
```

#### Backend: Call from `submit_onboarding()`
After saving the learning goal, call `GalaxyBootstrapService.seed_from_goal()`:

```python
# In submit_onboarding(), after saving learning_goal:
if payload.learning_goal:
    bootstrap_service = GalaxyBootstrapService(db)
    await bootstrap_service.seed_from_goal(
        user_id=current_user.id,
        learning_goal=payload.learning_goal,
        goal_type=payload.learning_goal_type,
    )
```

**Files changed**:
- `backend/app/services/galaxy_bootstrap_service.py` (new)
- `backend/app/api/v1/profile_transparency.py` — call bootstrap after goal save

### Verification
Complete onboarding with a goal → open Galaxy tab → 5 dim scaffold nodes visible, labeled with goal-relevant names. Complete first task → the matching node visually brightens.

---

## Stage 3: Cohort Priors for Strategy Learning Cold Start

### Problem
`InterventionStrategyLearner.get_best_strategy()` returns `None` when `len(outcomes) < MIN_PERSONALIZED_SAMPLES` (5). This means every intervention for a new user uses a random/default strategy for the first 5 cycles. For a typical user, this means 2-3 weeks of suboptimal interventions.

### What Changes

#### Backend: `backend/app/services/intervention_strategy_learner.py`
Add cohort fallback to `get_best_strategy()`:

```python
async def get_best_strategy(
    self,
    user_id: UUID,
    trigger_type: InterventionTriggerType,
    *,
    cohort_profile: dict | None = None,  # NEW: {goal_type, knowledge_level, learning_style}
) -> tuple[DeliveryStrategy | None, str]:  # returns (strategy, confidence_level)
    outcomes = await self._load_outcomes(user_id=user_id, trigger_type=trigger_type)
    if len(outcomes) >= self.MIN_PERSONALIZED_SAMPLES:
        return self._select_best(outcomes), "personal"

    # Fall back to cohort priors
    if cohort_profile:
        cohort_outcomes = await self._load_cohort_outcomes(
            trigger_type=trigger_type,
            goal_type=cohort_profile.get("goal_type"),
            knowledge_level=cohort_profile.get("knowledge_level"),
            learning_style=cohort_profile.get("learning_style"),
        )
        if len(cohort_outcomes) >= self.MIN_PERSONALIZED_SAMPLES:
            return self._select_best(cohort_outcomes), "cohort"

    return None, "none"

async def _load_cohort_outcomes(
    self,
    *,
    trigger_type: InterventionTriggerType,
    goal_type: str | None,
    knowledge_level: str | None,
    learning_style: str | None,
) -> list[InterventionStrategyOutcome]:
    """Load outcomes from users with a similar profile (cohort)."""
    stmt = (
        select(InterventionStrategyOutcome)
        .where(InterventionStrategyOutcome.trigger_type == trigger_type)
        .where(InterventionStrategyOutcome.not_deleted_filter())
    )
    # Filter by profile fields stored in context_snapshot
    if goal_type:
        stmt = stmt.where(
            InterventionStrategyOutcome.context_snapshot["goal_type"].as_string() == goal_type
        )
    if knowledge_level:
        stmt = stmt.where(
            InterventionStrategyOutcome.context_snapshot["knowledge_level"].as_string() == knowledge_level
        )
    stmt = stmt.limit(50)  # cap cohort size for performance
    return list((await self.db.execute(stmt)).scalars().all())
```

Also update `_build_context_snapshot()` to save `goal_type`, `knowledge_level`, `learning_style` from the user's profile at time of intervention — so future cohort queries can match on them.

**Files changed**:
- `backend/app/services/intervention_strategy_learner.py`
- `backend/app/services/card_protocol/behavior_intervention_bridge.py` — pass cohort_profile when calling `get_best_strategy()`

### Verification
New user receives first intervention → `get_best_strategy()` returns a cohort-based strategy (not `None`) → intervention uses an evidence-informed tone from day 1.

---

## Stage 4: Community Signals Visible in AI + Home

### Problem
The `CommunitySignalBridge` runs and pushes signals into the system but:
- The AI never explicitly references peer context in responses
- The home screen has no accountability partner visibility

### Part A: AI verbalizes peer context

#### Backend: `backend/app/orchestration/prompts.py`
In `_format_companion_persona_section()`, check for `community_context` in `user_context` and add a peer framing line:

```python
# After existing lines in _format_companion_persona_section():
community_ctx = user_context.get("community_context") if isinstance(user_context, dict) else None
if isinstance(community_ctx, dict):
    peer_insight = str(community_ctx.get("peer_insight") or "").strip()
    group_name = str(community_ctx.get("group_name") or "").strip()
    if peer_insight:
        lines.append(f"- 群组参考: {peer_insight}")
    elif group_name:
        lines.append(f"- 你在「{group_name}」群组中学习，和同学保持了联结。")
```

The community_signal_bridge already pushes context into `system_update_service`. We need it to also inject into `user_context` that flows to the prompt. Check `backend/app/core/context_manager.py` for where `community_context` should be populated.

**Files changed**:
- `backend/app/orchestration/prompts.py` — add peer framing in `_format_companion_persona_section()`
- `backend/app/core/context_manager.py` — ensure `community_context` is fetched and included in user_context payload

### Part B: Home screen accountability partner card

When an accountability partner completes a task, `CommunitySignalBridge.handle_group_task_completed()` already fires a `community.group_task_completed` event. Wire this to a home screen notification card.

**Backend**: The `SystemUpdateService` call already creates a system update. Ensure it includes `partner_name` and `task_title` in the metadata so Flutter can render it.

**Flutter**: The home dashboard already has a configurable card grid (`dashboard_card_config_provider.dart`). Add an `accountability_partner` card type that:
- Polls for `community.group_task_completed` system updates
- Shows: "你的学习伙伴今天完成了「{task_title}」"
- Only shows if user has an accountability partner (not for solo users)

**Files changed**:
- `backend/app/services/community_signal_bridge.py` — ensure metadata has partner_name, task_title
- `mobile/lib/features/home/presentation/providers/dashboard_card_config_provider.dart` — add accountability_partner card type
- `mobile/lib/features/home/presentation/widgets/accountability_partner_card.dart` (new)

### Verification
User with an accountability partner: partner completes a task → home screen shows partner progress card within next refresh cycle. User asks AI about their progress → AI references peer context in response.

---

## Stage 5: Stickiness Moments — Surface Generated Evidence Visibly

### Problem
Every key system event generates evidence internally but shows nothing or just a generic toast to the user. The "system is watching" feeling never registers.

### The 4 Stickiness Moments

#### Moment 1: First task completion → galaxy node reaction + AI acknowledgment

**Backend**: When `TaskCompleted` event fires and it's the user's first ever task, emit a special `FIRST_TASK_COMPLETED` system update with the linked knowledge node ID.

**Flutter**:
- When the user completes a task in the task list, navigate to galaxy and highlight the linked node with `star_success_animation.dart`
- In the chat, after task completion, trigger a short AI acknowledgment: "你刚完成了「{task_title}」！这个知识点的掌握度已经开始积累了。"

**Files**:
- `backend/app/services/achievement_engine.py` — add FIRST_TASK_COMPLETED signal
- `mobile/lib/features/task/presentation/` — trigger galaxy animation on first completion

#### Moment 2: Error logged → AI proactively mentions plan adjustment

**Backend**: `ErrorReplanBridge` already fires and may trigger `evaluate_plan_health_now()`. After it fires, publish a `SystemUpdate` with `update_type="plan_adjusted_from_error"`, including the affected node name and what changed.

**Flutter**: On next chat session open, if there's an unread `plan_adjusted_from_error` system update, prepend an AI bubble: "我注意到你在「{node_name}」上遇到了问题，我已经把相关任务调整到本周更早的时间段。"

**Files**:
- `backend/app/services/error_replan_bridge.py` — emit SystemUpdate after replan fires
- `mobile/lib/features/chat/presentation/` — show system update as AI bubble on session open

#### Moment 3: Routing shifts execution→cognitive → AI acknowledges

**Backend**: In `routing_engine.py`, when mode changes from `execution_first` to `cognitive_first` vs last session, log the shift. This is already stored in `routing_debug`. Expose it in the context pack.

**Flutter/Prompt**: The dual_core_section in prompts already receives the mode. When mode is `cognitive_first` and the user's last session was `execution_first`, add to the dual_core_section: a natural transition phrase. Example system prompt addition: "用户上次以执行模式对话，但现在情绪状态或行为模式提示需要先处理认知层——本轮开场用一句承接语，不要直接进入任务。"

**Files**:
- `backend/app/orchestration/prompts.py` — add mode-shift transition phrase to dual_core_section
- `backend/app/orchestration/routing_engine.py` — detect and expose mode shift in context

#### Moment 4: 3-day streak → home screen streak indicator

The streak indicator already exists in Flutter (`streak_indicator.dart`, `DashboardCardIds.streak`). The growth dashboard already returns `streak_days` from `GrowthDashboardService._get_current_streak_days()`. Verify the streak card is visible in the default dashboard card config for new users.

**Files**:
- `mobile/lib/features/home/presentation/providers/dashboard_card_config_provider.dart` — ensure `streak` is in default card list for new users

### Verification
Complete first task → see galaxy node reaction. Log an error → next chat open shows plan adjustment message. Use app 3 days in a row → home screen shows "连续第3天". These are the moments users screenshot and share.

---

## Stage 6: Galaxy Evidence Mode — Mastery Milestone Animations

### Problem
The galaxy already has mastery-based glow logic (`star_map_painter.dart` lines 2021-2088). But mastery changes are silent — no animation fires when a threshold is crossed. The galaxy looks the same before and after growth.

### What Changes

#### Flutter: Mastery threshold detection in galaxy provider

When user node statuses are refreshed, compare new mastery scores to cached previous scores. When a node crosses a threshold (0→30, 30→60, 60→85, 85→100), fire a `mastery_milestone_event` that triggers `star_success_animation.dart` on that node.

**New thresholds** (add to galaxy constants):
```dart
static const List<int> masteryMilestones = [30, 60, 85, 100];
```

**Detection in provider**: When galaxy nodes refresh, check for threshold crossings and emit milestone events to a local stream that the galaxy canvas listens to.

#### Flutter: Error cluster visualization

Nodes with linked errors and mastery_score < 30 should render with a distinct "friction" visual — dim red atmosphere instead of normal glow. This uses the existing `_masteryTemperatureColor()` and error count data already available in node metadata.

**Add to `star_map_painter.dart`**:
- When `node.errorCount > 2` AND `node.masteryScore < 30`: render atmosphere with a reddish tint
- Add `errorCount` field to the galaxy node model (fetched from `UserNodeStatus`)

#### Backend: Ensure error count flows to Flutter

`GET /api/v1/galaxy/nodes` or equivalent should include `error_count` per node. If not already present, add it from `UserNodeStatus` or a count query on `Error` table linked to the node.

**Files changed**:
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart` — error cluster tint
- `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart` — mastery threshold detection
- `mobile/lib/features/galaxy/data/models/galaxy_node.dart` — add errorCount field
- `backend/app/api/v1/galaxy.py` or equivalent — include error_count in node response

### Verification
Study a topic, log errors, do tasks → open galaxy → nodes with errors show dim red friction glow, nodes with completed tasks show brightening glow. Cross a mastery threshold → brief animation plays on that star. After 2 weeks the galaxy is visibly different from day 1 — it's evidence, not decoration.

---

## Implementation Order

```
Stage 1 (First Conversation)     ← Start here. Highest day-1 impact.
  └─→ Stage 2 (Galaxy Seeds)     ← Triggered from same onboarding endpoint.
       └─→ Stage 5 Moment 4      ← Streak card in default config (trivial).

Stage 3 (Cohort Priors)          ← Independent. Do in parallel with Stage 2.

Stage 4 (Community Visibility)   ← Depends on community bridge being wired (already done).

Stage 5 Moments 1-3              ← Depend on Stage 1 (first chat) being live.

Stage 6 (Galaxy Evidence)        ← Depends on Stage 2 (nodes existing).
```

---

## Files to Change — Complete List

### Backend (Python)
| File | Change |
|------|--------|
| `backend/app/api/v1/profile_transparency.py` | Add `_generate_first_session_message()`, call galaxy bootstrap, return `first_message` |
| `backend/app/services/galaxy_bootstrap_service.py` | **New file** — `GalaxyBootstrapService.seed_from_goal()` |
| `backend/app/services/intervention_strategy_learner.py` | Add cohort fallback in `get_best_strategy()`, add `_load_cohort_outcomes()` |
| `backend/app/services/card_protocol/behavior_intervention_bridge.py` | Pass cohort_profile when calling `get_best_strategy()` |
| `backend/app/orchestration/prompts.py` | Add peer framing in `_format_companion_persona_section()`, mode-shift transition phrase |
| `backend/app/core/context_manager.py` | Ensure `community_context` populated in user_context payload |
| `backend/app/services/error_replan_bridge.py` | Emit `plan_adjusted_from_error` SystemUpdate after replan fires |
| `backend/app/services/community_signal_bridge.py` | Include partner_name, task_title in SystemUpdate metadata |
| `backend/app/api/v1/galaxy.py` (or equivalent) | Include `error_count` in node response |

### Flutter (Dart)
| File | Change |
|------|--------|
| `mobile/lib/features/user/data/repositories/user_repository.dart` | `submitOnboarding()` returns `first_message` |
| `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart` | Navigate to `/chat` with first message instead of `/home` |
| `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | Accept and display `initial_ai_message` from route extras |
| `mobile/lib/features/home/presentation/providers/dashboard_card_config_provider.dart` | Add `accountability_partner` card, ensure `streak` in default config |
| `mobile/lib/features/home/presentation/widgets/accountability_partner_card.dart` | **New file** — partner progress card |
| `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart` | Mastery threshold detection + milestone event emission |
| `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart` | Error cluster tint (reddish atmosphere for high-error low-mastery nodes) |
| `mobile/lib/features/galaxy/data/models/galaxy_node.dart` | Add `errorCount` field |

---

## Success Metrics

| Stage | Metric | Target |
|-------|--------|--------|
| 1 | New user creates first plan within session 1 | ≥ 70% of new users |
| 2 | Galaxy has ≥ 5 nodes visible on day 1 | 100% of users who complete onboarding |
| 3 | `get_best_strategy()` returns non-null from session 1 (cohort) | 100% when cohort data exists |
| 4 | Community signals referenced in AI response | Detectable in prompt inspection |
| 5 | At least 2 stickiness moments visible in first week | Via demo run |
| 6 | Galaxy visually different after 5 task completions vs day 1 | Visual inspection |

---

## Completion Checklist

- [x] Stage 1: `_generate_first_session_message()` implemented and tested
- [x] Stage 1: onboarding → chat navigation wired in Flutter
- [x] Stage 1: chat screen displays initial AI message from route extras
- [x] Stage 2: `GalaxyBootstrapService` created and called from onboarding endpoint
- [x] Stage 2: Seed nodes visible in galaxy on day 1
- [x] Stage 3: `_load_cohort_outcomes()` implemented
- [x] Stage 3: `behavior_intervention_bridge` passes cohort_profile
- [x] Stage 4A: `community_context` flows to prompt companion section
- [x] Stage 4B: streak card in defaultVisible (community partner card low-priority)
- [x] Stage 5: Streak card in default config verified
- [x] Stage 5: `plan_adjusted_from_error` SystemUpdate emitted and shown in chat
- [x] Stage 5: Mode-shift transition phrase in `routing_engine.py` (cognitive_first transition)
- [x] Stage 6: Error cluster tint in `star_map_painter.dart` (red pulse ring for nodes with errors)
- [x] Stage 6: Mastery milestone animation fires (`masteryMilestones` stream + `_handleMasteryMilestone`)
- [x] Stage 6: `recent_error_count` in galaxy node API response (`UserStatusInfo.recent_error_count`)

---

**Document owner**: Claude Code
**Last updated**: 2026-04-03
