#!/usr/bin/env python3
"""
Seed Phase 2 demo data for all Phase 2 features.

Usage:
    cd backend && python3 scripts/seed_phase2_demo_data.py

Covers:
    1. Goals (GOAL creation wizard + GOAL-012 strategy migration)
    2. Strategy Beliefs (GOAL-012 Bayesian beliefs)
    3. Error Patterns (KG-005 remediable error patterns)
    4. Directive Audit Entries (TASK-014)
    5. Source Lifecycle (Source badge widget)
    6. Priority Reasoning (KG-009)
    7. Growth Chronicle / Return Case File (GOAL-011)
    8. Community Resource Quality (FV-22 quality scores)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import redis.asyncio as aioredis
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import (
    ErrorRecord,
    Goal,
    KnowledgeNode,
    SharedResource,
    Task,
    TaskStatus,
    TaskType,
    User,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEMO_USERNAME = "chat_test"
DEMO_EMAIL = "test@example.com"

DEFAULT_REDIS_URL = "redis://:change-me@127.0.0.1:6379/0"

REDIS_URL = os.environ.get("REDIS_URL") or DEFAULT_REDIS_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# 1. Goals
# ---------------------------------------------------------------------------

async def seed_goals(session: AsyncSession, user_id) -> None:
    """Create 3 goals with milestones for the demo user."""
    logger.info("[GOALS] Seeding goals ...")

    # Check existing goals for this user so we stay idempotent
    existing = (await session.execute(
        select(Goal).where(Goal.user_id == user_id)
    )).scalars().all()
    existing_titles = {g.title for g in existing}

    goals_data = [
        {
            "title": "高数期末90+",
            "goal_type": "exam",
            "description": "高等数学期末考试达到90分以上，掌握微积分和线性代数核心概念",
            "status": "active",
            "priority": "critical",
            "is_primary": True,
            "target_date": date(2026, 7, 15),
            "progress": 0.35,
            "mastery": 0.40,
            "minimum_acceptance_criteria": [
                {"metric": "exam_score", "threshold": 90, "unit": "percent"},
                {"metric": "practice_tests_passed", "threshold": 5, "unit": "count"},
            ],
            "metadata_payload": {
                "milestones": [
                    {"title": "掌握极限与连续", "progress": 0.8, "due": "2026-05-20"},
                    {"title": "掌握导数与微分", "progress": 0.6, "due": "2026-06-01"},
                    {"title": "掌握积分与应用", "progress": 0.2, "due": "2026-06-15"},
                    {"title": "掌握级数理论", "progress": 0.0, "due": "2026-06-30"},
                    {"title": "模拟考试稳定90+", "progress": 0.0, "due": "2026-07-10"},
                ],
                "source": "exam_sprint",
            },
        },
        {
            "title": "掌握React前端",
            "goal_type": "project",
            "description": "系统学习React框架，能独立开发中等复杂度的前端应用",
            "status": "active",
            "priority": "normal",
            "is_primary": False,
            "target_date": date(2026, 8, 30),
            "progress": 0.20,
            "mastery": 0.25,
            "minimum_acceptance_criteria": [
                {"metric": "projects_completed", "threshold": 3, "unit": "count"},
                {"metric": "component_library_size", "threshold": 15, "unit": "count"},
            ],
            "metadata_payload": {
                "milestones": [
                    {"title": "React基础与JSX", "progress": 1.0, "due": "2026-05-15"},
                    {"title": "组件与Props/State", "progress": 0.6, "due": "2026-06-01"},
                    {"title": "Hooks深入理解", "progress": 0.1, "due": "2026-06-20"},
                    {"title": "路由与状态管理", "progress": 0.0, "due": "2026-07-15"},
                    {"title": "完成3个实战项目", "progress": 0.0, "due": "2026-08-25"},
                ],
                "source": "manual",
            },
        },
        {
            "title": "每天7点起床",
            "goal_type": "general",
            "description": "养成早起习惯，工作日7:00前起床，坚持30天",
            "status": "active",
            "priority": "high",
            "is_primary": False,
            "target_date": date(2026, 6, 15),
            "progress": 0.53,
            "mastery": 0.60,
            "minimum_acceptance_criteria": [
                {"metric": "consecutive_days", "threshold": 30, "unit": "days"},
                {"metric": "avg_wake_time", "threshold": "07:00", "unit": "time"},
            ],
            "metadata_payload": {
                "milestones": [
                    {"title": "连续7天早起", "progress": 1.0, "due": "2026-05-09"},
                    {"title": "连续14天早起", "progress": 1.0, "due": "2026-05-16"},
                    {"title": "连续21天早起", "progress": 0.6, "due": "2026-05-23"},
                    {"title": "连续30天早起", "progress": 0.0, "due": "2026-05-30"},
                ],
                "source": "manual",
                "streak_current": 16,
                "streak_best": 16,
            },
        },
    ]

    created = 0
    for gdata in goals_data:
        if gdata["title"] in existing_titles:
            logger.info(f"  [GOALS] Goal '{gdata['title']}' already exists, skipping")
            continue
        goal = Goal(user_id=user_id, **gdata)
        session.add(goal)
        created += 1

    await session.flush()
    logger.info(f"[GOALS] Created {created} new goals (total existing: {len(existing) + created})")


# ---------------------------------------------------------------------------
# 2. Strategy Beliefs
# ---------------------------------------------------------------------------

async def seed_strategy_beliefs(redis_client: aioredis.Redis, user_id) -> None:
    """Create StrategyBeliefSnapshot entries in Redis."""
    logger.info("[STRATEGY-BELIEFS] Seeding strategy beliefs ...")

    uid = str(user_id)
    beliefs = {
        "repair_knowledge_bottleneck": {
            "alpha": 7.2,
            "beta": 2.8,
            "evidence_count": 10,
            "last_updated": _iso(_now()),
            "counter_evidence": [
                {"date": "2026-04-28", "context": "User already mastered topic", "penalty": 0.05},
            ],
            "metadata": {"description": "识别知识瓶颈并定向修复策略"},
        },
        "task_granularity_fit": {
            "alpha": 5.5,
            "beta": 3.5,
            "evidence_count": 9,
            "last_updated": _iso(_now() - timedelta(hours=6)),
            "counter_evidence": [],
            "metadata": {"description": "任务粒度自适应调整策略"},
        },
        "exam_rescue_sprint": {
            "alpha": 8.1,
            "beta": 1.9,
            "evidence_count": 12,
            "last_updated": _iso(_now() - timedelta(days=1)),
            "counter_evidence": [
                {"date": "2026-04-25", "context": "Burnout detected after sprint", "penalty": 0.05},
                {"date": "2026-04-20", "context": "Retention drop post-sprint", "penalty": 0.05},
            ],
            "metadata": {"description": "考前冲刺策略（7天生存模式）"},
        },
        "sustain_momentum": {
            "alpha": 4.3,
            "beta": 4.7,
            "evidence_count": 6,
            "last_updated": _iso(_now() - timedelta(days=2)),
            "counter_evidence": [],
            "metadata": {"description": "学习势头维持策略"},
        },
    }

    for strategy_key, payload in beliefs.items():
        redis_key = f"strategy_belief:{uid}:{strategy_key}"
        existing = await redis_client.get(redis_key)
        if existing:
            logger.info(f"  [STRATEGY-BELIEFS] {strategy_key} exists, overwriting")
        await redis_client.set(redis_key, json.dumps(payload, ensure_ascii=False), ex=86400 * 30)
        logger.info(f"  [STRATEGY-BELIEFS] Set {strategy_key}: alpha={payload['alpha']}, beta={payload['beta']}")

    logger.info(f"[STRATEGY-BELIEFS] Seeded {len(beliefs)} strategy beliefs")


# ---------------------------------------------------------------------------
# 3. Error Patterns
# ---------------------------------------------------------------------------

async def seed_error_patterns(session: AsyncSession, user_id) -> None:
    """Create error book entries that form remediable patterns."""
    logger.info("[ERROR-PATTERNS] Seeding error patterns ...")

    # Get or create a knowledge node for the errors
    kn_result = await session.execute(
        select(KnowledgeNode).where(KnowledgeNode.name == "微积分基本定理").limit(1)
    )
    kn_calc = kn_result.scalar_one_or_none()

    kn2_result = await session.execute(
        select(KnowledgeNode).where(KnowledgeNode.name == "极限与连续").limit(1)
    )
    kn_limit = kn2_result.scalar_one_or_none()

    # Use a fixed node ID if found, otherwise generate stable ones
    calc_node_id = kn_calc.id if kn_calc else uuid.uuid4()
    limit_node_id = kn_limit.id if kn_limit else uuid.uuid4()

    now = _now()

    # Pattern 1: Calculation errors in calculus (same node, same error_type) -- 3 occurrences
    calc_errors = [
        {
            "question_text": "求不定积分 ∫(2x³ + 3x² - x + 1)dx",
            "user_answer": "½x⁴ + x³ - ½x² + x + C",
            "correct_answer": "½x⁴ + x³ - ½x² + x + C",
            "latest_analysis": {
                "error_type": "calculation_error",
                "root_cause": "多项式积分系数计算错误，第二项应为x³而非½x³",
                "study_suggestions": "复习幂函数积分公式，特别注意系数处理",
            },
        },
        {
            "question_text": "求定积分 ∫₀¹ (3x² + 2x)dx",
            "user_answer": "2.5",
            "correct_answer": "3",
            "latest_analysis": {
                "error_type": "calculation_error",
                "root_cause": "代入上下限时计算错误，2x积分应为x²，在0到1之间是1",
                "study_suggestions": "加强定积分上下限代入的练习",
            },
        },
        {
            "question_text": "计算 ∫ sin(2x)dx",
            "user_answer": "-cos(2x) + C",
            "correct_answer": "-½cos(2x) + C",
            "latest_analysis": {
                "error_type": "calculation_error",
                "root_cause": "复合函数积分忘记除以内层函数的导数（链式法则遗漏系数1/2）",
                "study_suggestions": "复习换元积分法，注意复合函数的系数处理",
            },
        },
    ]

    # Pattern 2: Concept errors in limits (same node, same error_type) -- 2 occurrences
    limit_errors = [
        {
            "question_text": "求极限 lim(x→0) sin(x)/x",
            "user_answer": "不存在",
            "correct_answer": "1",
            "latest_analysis": {
                "error_type": "concept_error",
                "root_cause": "混淆了0/0型不定式与极限不存在的概念",
                "study_suggestions": "复习重要极限公式，理解洛必达法则的适用条件",
            },
        },
        {
            "question_text": "判断函数 f(x) = |x|/x 在 x=0 处是否连续",
            "user_answer": "连续，因为左右极限相等",
            "correct_answer": "不连续，左极限为-1，右极限为1，不相等",
            "latest_analysis": {
                "error_type": "concept_error",
                "root_cause": "未正确计算左右极限，忽略绝对值函数的符号变化",
                "study_suggestions": "加强分段函数和绝对值函数在特殊点的极限分析",
            },
        },
    ]

    # Additional standalone errors for variety
    standalone_errors = [
        {
            "question_text": "证明 lim(n→∞) (1+1/n)ⁿ = e",
            "user_answer": "直接代入n=∞得到(1+0)^∞ = 1",
            "correct_answer": "利用单调有界定理或泰勒展开证明极限存在且等于e≈2.718",
            "latest_analysis": {
                "error_type": "method_error",
                "root_cause": "错误地将∞直接代入表达式",
                "study_suggestions": "复习极限的严格定义和证明方法",
            },
            "node": None,
        },
    ]

    created = 0

    def _make_record(data, node_id, offset_days):
        return ErrorRecord(
            id=uuid.uuid4(),
            user_id=user_id,
            subject_code="math",
            chapter="高等数学",
            question_text=data["question_text"],
            user_answer=data["user_answer"],
            correct_answer=data["correct_answer"],
            latest_analysis=data["latest_analysis"],
            mastery_level=0.3 if data["latest_analysis"]["error_type"] == "calculation_error" else 0.2,
            easiness_factor=2.3,
            review_count=0,
            interval_days=1.0,
            next_review_at=now + timedelta(days=1 + offset_days),
            cognitive_tags=[data["latest_analysis"]["error_type"]],
            affected_node_id=node_id,
            mastery_delta=-0.05,
            linked_knowledge_node_ids=[node_id] if node_id else [],
            suggested_concepts=[],
        )

    for i, edata in enumerate(calc_errors):
        rec = _make_record(edata, calc_node_id, i)
        session.add(rec)
        created += 1

    for i, edata in enumerate(limit_errors):
        rec = _make_record(edata, limit_node_id, i)
        session.add(rec)
        created += 1

    for edata in standalone_errors:
        rec = _make_record(edata, None, 0)
        session.add(rec)
        created += 1

    await session.flush()
    logger.info(f"[ERROR-PATTERNS] Created {created} error records (2 patterns: 3 calc + 2 limit + 1 standalone)")


# ---------------------------------------------------------------------------
# 4. Directive Audit Entries
# ---------------------------------------------------------------------------

async def seed_directive_audit(redis_client: aioredis.Redis, user_id) -> None:
    """Store 10+ directive audit entries in Redis."""
    logger.info("[DIRECTIVE-AUDIT] Seeding directive audit entries ...")

    uid = str(user_id)
    now = _now()

    directives = [
        {
            "directive_id": _uid(),
            "directive_type": "response",
            "user_visible_reason": "检测到你对微积分概念理解有偏差，切换到引导式教学",
            "trigger_signal": {"type": "error_pattern", "pattern": "concept_error", "confidence": 0.87},
            "policy": {"rule": "concept_error_high_confidence", "action": "switch_to_socratic"},
            "actual_result": {"success": True, "user_engagement_delta": 0.15},
            "timestamp": _iso(now - timedelta(hours=2)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "retrieval",
            "user_visible_reason": "你之前学过相关知识点，为你召回记忆",
            "trigger_signal": {"type": "knowledge_overlap", "nodes": ["微积分基本定理"], "similarity": 0.92},
            "policy": {"rule": "knowledge_overlap_threshold", "threshold": 0.8, "action": "retrieve_context"},
            "actual_result": {"success": True, "retrieved_count": 3},
            "timestamp": _iso(now - timedelta(hours=3)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "ux",
            "user_visible_reason": "检测到疲劳信号，简化界面展示",
            "trigger_signal": {"type": "fatigue_signal", "session_minutes": 85, "error_rate": 0.4},
            "policy": {"rule": "fatigue_detection", "action": "reduce_complexity", "threshold_minutes": 75},
            "actual_result": {"success": True, "session_extended_minutes": 20},
            "timestamp": _iso(now - timedelta(hours=5)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "community",
            "user_visible_reason": "学习小组有新动态，推送相关消息",
            "trigger_signal": {"type": "group_activity", "group_id": "demo_group", "event": "member_completed_task"},
            "policy": {"rule": "social_reinforcement", "action": "notify_relevant_activity"},
            "actual_result": {"success": True, "user_opened": True},
            "timestamp": _iso(now - timedelta(hours=8)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "skill",
            "user_visible_reason": "推荐间隔复习策略以巩固薄弱知识点",
            "trigger_signal": {"type": "mastery_decline", "node": "极限与连续", "old_mastery": 0.7, "new_mastery": 0.45},
            "policy": {"rule": "spaced_repetition_trigger", "action": "schedule_review", "threshold": 0.5},
            "actual_result": {"success": True, "review_scheduled": True},
            "timestamp": _iso(now - timedelta(hours=12)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "plan",
            "user_visible_reason": "任务完成进度落后，建议调整计划",
            "trigger_signal": {"type": "plan_deviation", "expected_progress": 0.5, "actual_progress": 0.3},
            "policy": {"rule": "plan_deviation_threshold", "deviation_limit": 0.15, "action": "suggest_replan"},
            "actual_result": {"success": True, "user_accepted": True, "new_plan_created": True},
            "timestamp": _iso(now - timedelta(days=1)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "response",
            "user_visible_reason": "连续3次计算错误，降低题目难度维持信心",
            "trigger_signal": {"type": "consecutive_errors", "count": 3, "subject": "math"},
            "policy": {"rule": "confidence_protection", "action": "reduce_difficulty", "threshold_errors": 3},
            "actual_result": {"success": True, "next_task_difficulty_delta": -1},
            "timestamp": _iso(now - timedelta(days=1, hours=4)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "retrieval",
            "user_visible_reason": "你上周学过类似题目，展示对比分析",
            "trigger_signal": {"type": "similarity_match", "similarity": 0.85, "source": "error_book"},
            "policy": {"rule": "analogical_retrieval", "threshold": 0.8, "action": "show_comparison"},
            "actual_result": {"success": True, "comparison_shown": True},
            "timestamp": _iso(now - timedelta(days=1, hours=8)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "ux",
            "user_visible_reason": "检测到高效学习状态，提供深度模式挑战",
            "trigger_signal": {"type": "flow_state", "correct_rate": 0.9, "speed_ratio": 1.3},
            "policy": {"rule": "flow_maintenance", "action": "increase_challenge", "threshold_rate": 0.85},
            "actual_result": {"success": True, "difficulty_delta": 1},
            "timestamp": _iso(now - timedelta(days=2)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "skill",
            "user_visible_reason": "跨学科关联发现：物理学与微积分的联系",
            "trigger_signal": {"type": "cross_domain", "domains": ["physics", "math"], "bridge_node": "微积分应用"},
            "policy": {"rule": "cross_domain_bridge", "action": "suggest_connection", "min_confidence": 0.7},
            "actual_result": {"success": True, "connection_accepted": True},
            "timestamp": _iso(now - timedelta(days=2, hours=3)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "plan",
            "user_visible_reason": "目标截止日期临近，自动切换冲刺模式",
            "trigger_signal": {"type": "deadline_proximity", "days_remaining": 3, "progress": 0.65},
            "policy": {"rule": "deadline_sprint", "action": "activate_sprint_mode", "threshold_days": 5},
            "actual_result": {"success": True, "sprint_activated": True},
            "timestamp": _iso(now - timedelta(days=3)),
        },
        {
            "directive_id": _uid(),
            "directive_type": "community",
            "user_visible_reason": "社群资源质量评分已更新",
            "trigger_signal": {"type": "quality_score_update", "resource_id": "shared_001", "new_score": 0.85},
            "policy": {"rule": "quality_broadcast", "action": "notify_subscribers", "min_score_change": 0.2},
            "actual_result": {"success": True, "notified_count": 5},
            "timestamp": _iso(now - timedelta(days=3, hours=6)),
        },
    ]

    seeded = 0
    for directive in directives:
        redis_key = f"directive_audit:{uid}:{directive['directive_id']}"
        await redis_client.set(redis_key, json.dumps(directive, ensure_ascii=False), ex=86400 * 30)
        seeded += 1

    logger.info(f"[DIRECTIVE-AUDIT] Seeded {seeded} directive audit entries")


# ---------------------------------------------------------------------------
# 5. Source Lifecycle
# ---------------------------------------------------------------------------

async def seed_source_lifecycle(redis_client: aioredis.Redis, user_id) -> None:
    """Store source lifecycle metadata in Redis for the badge widget."""
    logger.info("[SOURCE-LIFECYCLE] Seeding source lifecycle data ...")

    uid = str(user_id)
    now = _now()

    sources = [
        {
            "source_id": _uid(),
            "task_title": "复习微积分第三章",
            "status": "active",
            "origin": "ai_generated",
            "created_at": _iso(now - timedelta(days=7)),
            "last_accessed": _iso(now - timedelta(hours=1)),
            "access_count": 12,
            "quality_rating": 0.9,
            "badge": "verified",
        },
        {
            "source_id": _uid(),
            "task_title": "React Hooks练习",
            "status": "active",
            "origin": "community_shared",
            "created_at": _iso(now - timedelta(days=5)),
            "last_accessed": _iso(now - timedelta(days=1)),
            "access_count": 8,
            "quality_rating": 0.75,
            "badge": "community",
        },
        {
            "source_id": _uid(),
            "task_title": "早起习惯追踪",
            "status": "archived",
            "origin": "manual",
            "created_at": _iso(now - timedelta(days=14)),
            "last_accessed": _iso(now - timedelta(days=3)),
            "access_count": 28,
            "quality_rating": 0.6,
            "badge": None,
        },
        {
            "source_id": _uid(),
            "task_title": "线性代数期末复习",
            "status": "revoked",
            "origin": "ai_generated",
            "created_at": _iso(now - timedelta(days=30)),
            "revoked_at": _iso(now - timedelta(days=10)),
            "revoke_reason": "outdated_content",
            "access_count": 3,
            "quality_rating": 0.2,
            "badge": None,
        },
        {
            "source_id": _uid(),
            "task_title": "概率论练习题集",
            "status": "orphaned",
            "origin": "community_shared",
            "created_at": _iso(now - timedelta(days=20)),
            "last_accessed": _iso(now - timedelta(days=18)),
            "access_count": 1,
            "quality_rating": 0.4,
            "badge": None,
        },
    ]

    seeded = 0
    for src in sources:
        redis_key = f"source_lifecycle:{uid}:{src['source_id']}"
        await redis_client.set(redis_key, json.dumps(src, ensure_ascii=False), ex=86400 * 30)
        seeded += 1

    # Also store a summary key for badge widget quick lookup
    summary_key = f"source_lifecycle_summary:{uid}"
    summary = {
        "total": len(sources),
        "active": sum(1 for s in sources if s["status"] == "active"),
        "archived": sum(1 for s in sources if s["status"] == "archived"),
        "revoked": sum(1 for s in sources if s["status"] == "revoked"),
        "orphaned": sum(1 for s in sources if s["status"] == "orphaned"),
        "updated_at": _iso(now),
    }
    await redis_client.set(summary_key, json.dumps(summary, ensure_ascii=False), ex=86400 * 30)

    logger.info(f"[SOURCE-LIFECYCLE] Seeded {seeded} source lifecycle entries + summary")


# ---------------------------------------------------------------------------
# 6. Priority Reasoning
# ---------------------------------------------------------------------------

async def seed_priority_reasoning(session: AsyncSession, redis_client: aioredis.Redis, user_id) -> None:
    """Store priority reasoning data in Redis for tasks."""
    logger.info("[PRIORITY-REASONING] Seeding priority reasoning ...")

    # Fetch some existing tasks for the user
    tasks = (await session.execute(
        select(Task).where(Task.user_id == user_id).limit(5)
    )).scalars().all()

    if not tasks:
        # Create a couple of placeholder tasks if none exist
        t1 = Task(
            id=uuid.uuid4(),
            user_id=user_id,
            title="复习微积分极限章节",
            type=TaskType.LEARNING,
            tags=["math", "calculus"],
            estimated_minutes=45,
            difficulty=3,
            energy_cost=3,
            status=TaskStatus.PENDING,
            priority=2,
            order_index=0,
        )
        t2 = Task(
            id=uuid.uuid4(),
            user_id=user_id,
            title="React Hooks 实践练习",
            type=TaskType.TRAINING,
            tags=["react", "frontend"],
            estimated_minutes=60,
            difficulty=3,
            energy_cost=3,
            status=TaskStatus.PENDING,
            priority=1,
            order_index=1,
        )
        t3 = Task(
            id=uuid.uuid4(),
            user_id=user_id,
            title="早起打卡",
            type=TaskType.LEARNING,
            tags=["habit", "morning"],
            estimated_minutes=5,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.COMPLETED,
            priority=0,
            order_index=2,
        )
        session.add_all([t1, t2, t3])
        await session.flush()
        tasks = [t1, t2, t3]

    reasoning_data = [
        {
            "primary_reason": "deadline_proximity",
            "detail": "期末考试在3周内，微积分是核心科目",
            "supporting_signals": [
                {"signal": "exam_date", "value": "2026-07-15", "weight": 0.9},
                {"signal": "current_mastery", "value": 0.4, "weight": 0.7},
                {"signal": "error_pattern_count", "value": 3, "weight": 0.6},
            ],
            "alternative_options_skipped": [
                {"option": "react_practice", "reason": "no_deadline_pressure"},
                {"option": "habit_maintenance", "reason": "already_automated"},
            ],
        },
        {
            "primary_reason": "skill_gap_urgency",
            "detail": "React项目实践落后于计划进度",
            "supporting_signals": [
                {"signal": "plan_progress", "value": 0.2, "weight": 0.8},
                {"signal": "skill_assessment", "value": 0.25, "weight": 0.7},
            ],
            "alternative_options_skipped": [
                {"option": "passive_review", "reason": "hands_on_needed_for_skill"},
            ],
        },
        {
            "primary_reason": "momentum_preservation",
            "detail": "维持早起习惯连续性，防止中断",
            "supporting_signals": [
                {"signal": "streak_current", "value": 16, "weight": 0.85},
                {"signal": "streak_risk", "value": "high", "weight": 0.9},
            ],
            "alternative_options_skipped": [
                {"option": "sleep_in", "reason": "breaks_streak"},
            ],
        },
    ]

    seeded = 0
    for i, task in enumerate(tasks):
        if i >= len(reasoning_data):
            break
        redis_key = f"task_priority_reasoning:{task.id}"
        existing = await redis_client.get(redis_key)
        if existing:
            logger.info(f"  [PRIORITY-REASONING] Task {task.id} reasoning exists, overwriting")
        await redis_client.set(redis_key, json.dumps(reasoning_data[i], ensure_ascii=False), ex=86400 * 30)
        seeded += 1

    logger.info(f"[PRIORITY-REASONING] Seeded {seeded} task priority reasoning entries")


# ---------------------------------------------------------------------------
# 7. Growth Chronicle / Return Case File
# ---------------------------------------------------------------------------

async def seed_growth_chronicle(redis_client: aioredis.Redis, user_id) -> None:
    """Create chronicle entries and a cached return case file."""
    logger.info("[GROWTH-CHRONICLE] Seeding growth chronicle ...")

    uid = str(user_id)
    now = _now()

    chronicle_entries = [
        {
            "entry_id": _uid(),
            "type": "milestone_achieved",
            "title": "连续7天早起达成",
            "description": "成功完成连续7天早起的目标，培养了良好的作息习惯",
            "timestamp": _iso(now - timedelta(days=9)),
            "tags": ["habit", "milestone", "streak"],
            "emotional_tone": "positive",
            "related_goal": "每天7点起床",
            "progress_snapshot": {"streak": 7, "goal_progress": 0.23},
        },
        {
            "entry_id": _uid(),
            "type": "breakthrough",
            "title": "理解了导数的几何意义",
            "description": "通过AI引导式教学，终于理解了导数就是切线斜率，连接了代数和几何",
            "timestamp": _iso(now - timedelta(days=7)),
            "tags": ["math", "insight", "calculus"],
            "emotional_tone": "excited",
            "related_goal": "高数期末90+",
            "progress_snapshot": {"mastery_delta": 0.15, "goal_progress": 0.30},
        },
        {
            "entry_id": _uid(),
            "type": "pattern_detected",
            "title": "计算错误模式识别",
            "description": "系统检测到在积分计算中反复犯系数处理错误，已生成专项练习计划",
            "timestamp": _iso(now - timedelta(days=5)),
            "tags": ["math", "error_pattern", "ai_detected"],
            "emotional_tone": "neutral",
            "related_goal": "高数期末90+",
            "progress_snapshot": {"error_pattern_count": 3, "goal_progress": 0.32},
        },
        {
            "entry_id": _uid(),
            "type": "streak_milestone",
            "title": "连续14天早起达成",
            "description": "两周连续早起，生物钟正在调整，起床变得更容易",
            "timestamp": _iso(now - timedelta(days=2)),
            "tags": ["habit", "milestone", "streak"],
            "emotional_tone": "proud",
            "related_goal": "每天7点起床",
            "progress_snapshot": {"streak": 14, "goal_progress": 0.47},
        },
        {
            "entry_id": _uid(),
            "type": "social_reinforcement",
            "title": "学习小队互相激励",
            "description": "社群成员分享了学习笔记，通过互相讨论加深了对极限概念的理解",
            "timestamp": _iso(now - timedelta(days=1)),
            "tags": ["community", "social", "reinforcement"],
            "emotional_tone": "connected",
            "related_goal": "高数期末90+",
            "progress_snapshot": {"community_engagement": 0.8, "goal_progress": 0.35},
        },
        {
            "entry_id": _uid(),
            "type": "strategy_shift",
            "title": "学习策略调整：从题海到精练",
            "description": "AI建议减少重复刷题，转向深度理解每个题目的解题思路",
            "timestamp": _iso(now - timedelta(hours=6)),
            "tags": ["strategy", "ai_suggestion", "metacognition"],
            "emotional_tone": "curious",
            "related_goal": "高数期末90+",
            "progress_snapshot": {"strategy_effectiveness": 0.72, "goal_progress": 0.35},
        },
    ]

    # Write individual chronicle entries
    seeded = 0
    for entry in chronicle_entries:
        redis_key = f"growth_chronicle:{uid}:{entry['entry_id']}"
        await redis_client.set(redis_key, json.dumps(entry, ensure_ascii=False), ex=86400 * 90)
        seeded += 1

    # Build and cache the return case file
    return_case_file = {
        "user_id": uid,
        "generated_at": _iso(now),
        "summary": {
            "total_entries": len(chronicle_entries),
            "milestones_achieved": 2,
            "breakthroughs": 1,
            "patterns_detected": 1,
            "strategy_shifts": 1,
            "social_events": 1,
        },
        "growth_trajectory": "steady_upward",
        "key_moments": [
            {"date": chronicle_entries[1]["timestamp"], "event": "breakthrough", "title": chronicle_entries[1]["title"]},
            {"date": chronicle_entries[3]["timestamp"], "event": "streak_milestone", "title": chronicle_entries[3]["title"]},
        ],
        "active_goals_progress": [
            {"goal": "高数期末90+", "progress": 0.35, "trend": "improving"},
            {"goal": "掌握React前端", "progress": 0.20, "trend": "steady"},
            {"goal": "每天7点起床", "progress": 0.53, "trend": "strong"},
        ],
        "recommendations": [
            "继续巩固积分计算技巧，重点关注系数处理",
            "React学习可以安排在精力较低的时段",
            "早起习惯即将进入自动化阶段，继续保持",
        ],
    }
    return_key = f"return_case_file:{uid}"
    await redis_client.set(return_key, json.dumps(return_case_file, ensure_ascii=False), ex=86400 * 7)

    logger.info(f"[GROWTH-CHRONICLE] Seeded {seeded} chronicle entries + return case file")


# ---------------------------------------------------------------------------
# 8. Community Resource Quality
# ---------------------------------------------------------------------------

async def seed_community_resource_quality(session: AsyncSession, user_id) -> None:
    """Update shared resources with varied quality scores."""
    logger.info("[COMMUNITY-QUALITY] Seeding resource quality scores ...")

    # Check for existing shared resources
    existing_resources = (await session.execute(
        select(SharedResource).limit(10)
    )).scalars().all()

    if existing_resources:
        # Update existing resources with varied quality scores
        scores = [0.85, 0.60, 0.30, 0.72, 0.91, 0.45, 0.68, 0.83, 0.55, 0.38]
        updated = 0
        for i, resource in enumerate(existing_resources):
            if i >= len(scores):
                break
            resource.quality_score = scores[i]
            resource.quality_hidden = scores[i] < 0.3
            updated += 1
        await session.flush()
        logger.info(f"[COMMUNITY-QUALITY] Updated {updated} existing shared resources with quality scores")
    else:
        logger.info("[COMMUNITY-QUALITY] No existing shared resources found; "
                     "quality scores will be populated when resources are shared via the app")

    # Also store quality metadata in Redis for quick badge display
    redis = None  # We pass redis separately below; see caller
    logger.info("[COMMUNITY-QUALITY] Resource quality seeding done")


async def seed_community_quality_redis(redis_client: aioredis.Redis, user_id) -> None:
    """Store community resource quality metadata in Redis."""
    uid = str(user_id)

    quality_entries = [
        {
            "resource_id": _uid(),
            "title": "微积分公式速查表",
            "shared_by": uid,
            "quality_score": 0.85,
            "k_reviews": 5,
            "status": "active",
            "last_updated": _iso(_now()),
        },
        {
            "resource_id": _uid(),
            "title": "React入门笔记",
            "shared_by": uid,
            "quality_score": 0.60,
            "k_reviews": 3,
            "status": "active",
            "last_updated": _iso(_now() - timedelta(days=2)),
        },
        {
            "resource_id": _uid(),
            "title": "早起习惯养成指南",
            "shared_by": uid,
            "quality_score": 0.30,
            "k_reviews": 2,
            "status": "active",
            "last_updated": _iso(_now() - timedelta(days=5)),
        },
    ]

    for entry in quality_entries:
        redis_key = f"resource_quality:{entry['resource_id']}"
        await redis_client.set(redis_key, json.dumps(entry, ensure_ascii=False), ex=86400 * 30)

    logger.info(f"[COMMUNITY-QUALITY] Seeded {len(quality_entries)} resource quality entries in Redis")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("=" * 60)
    logger.info("Phase 2 Demo Data Seeding")
    logger.info("=" * 60)

    # --- Connect to DB ---
    async with AsyncSessionLocal() as session:
        # --- Find demo user ---
        result = await session.execute(
            select(User).where(
                (User.username == DEMO_USERNAME) | (User.email == DEMO_EMAIL)
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            logger.error(f"Demo user not found (username={DEMO_USERNAME}, email={DEMO_EMAIL}). "
                         "Run seed_demo_user_enhanced.py first.")
            return
        user_id = user.id
        logger.info(f"Found demo user: {user.username} (id={user_id})")

        # --- Connect to Redis ---
        redis_client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_URL.split('@')[-1]}")
        except Exception as exc:
            logger.warning(f"Redis connection failed: {exc}. Redis-based features will be skipped.")
            redis_client = None

        # --- Seed all features ---
        await seed_goals(session, user_id)
        await seed_strategy_beliefs(redis_client, user_id)
        await seed_error_patterns(session, user_id)
        await seed_directive_audit(redis_client, user_id)
        await seed_source_lifecycle(redis_client, user_id)
        await seed_priority_reasoning(session, redis_client, user_id)
        await seed_growth_chronicle(redis_client, user_id)
        await seed_community_resource_quality(session, user_id)
        if redis_client:
            await seed_community_quality_redis(redis_client, user_id)

        # --- Commit DB changes ---
        await session.commit()
        logger.info("DB session committed")

        # --- Cleanup Redis ---
        if redis_client:
            await redis_client.aclose()

    logger.info("=" * 60)
    logger.info("Phase 2 demo data seeding complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
