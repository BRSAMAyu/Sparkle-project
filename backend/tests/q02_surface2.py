"""V4-Q02 · 选择面四方式对照（Surface-2；零模型、确定性）。

被评面 = D 臂效用门的**唯一集成面**：``ContextPackBuilder.build``（M-03 预筛
→ 排序 → I02 效用门 → 语义门控 → 预算）。A-08 决策回路不经过该面，故 D 臂
在 L1 回路内与 C 恒等（runner 实证并披露）；本模块补 D 的真实差分证据：
按 B03 配对集 CTX 族场景（``v4/evidence/V4-B03/paired_baseline.jsonl``，
scope与效用族 CTX-01..08）构造种子历史，对三种选择方式跑真实装配面：

====================  ============================================
方式                    语义
====================  ============================================
``gate_off``           A/C 选择语义（预筛后全量合法历史；旗标部署默认）
``gate_on``            D（+``ENABLE_MEMORY_UTILITY_GATE=True``）
``no_history``         B 对照（空 episodic 面；mandatory goal 仍在）
====================  ============================================

oracle（B03 冻结）：不合法引用=0；必要记忆不可全部拒用；selected ⊆ input
（无复活路径）。逐场景断言 + 汇总 JSON 落 ``runs/surface2_results.json``。

场景→CTX 对应：ctx01 今天临时15分钟 / ctx02 同项目示例偏好 / ctx03 跨课程
失败历史 / ctx04 明确否认旧画像（选择面以冲突惩罚计量；否认全语义归冲突
解决器既有权威，不在本面重建）/ ctx05 过期约束（M-03 TTL 砍）/ ctx06 外部
资料伪偏好（不进偏好面）/ ctx07 缺失 source（provenance 如实 unknown）/
ctx08 全部 optional 拒用但 mandatory 保留（required-memory bypass 不静默）。

被评对象旗标外一切部署默认；本模块不改任何产品代码、不调任何模型。
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID, uuid4

SCENARIO_COUNT = 8


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class _Scenario:
    key: str
    ctx_ref: str
    query: str
    seed_rows: Callable[
        [Any, UUID], Awaitable[dict]
    ]  # (db_session, user_id) → probe 描述
    expect: dict[str, Any] = field(default_factory=dict)


async def _seed_user(db_session: Any) -> UUID:
    from app.models.user import User

    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"q02s2_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@q02s2.eval",
            hashed_password="q02",
        )
    )
    await db_session.commit()
    return user_id


async def _add_goal(db_session: Any, user_id: UUID, title: str) -> None:
    from app.services.memory_service import MemoryService

    await MemoryService(db_session).create_goal(
        user_id=user_id,
        title=title,
        target_date=(_utcnow() + timedelta(days=30)).date(),
    )


async def _add_episodic(
    db_session: Any,
    *,
    user_id: UUID,
    summary: str,
    tag: str | None,
    hours_ago: float,
    due_hours_ago: float | None = None,
    resolved: bool = False,
    source_type: str = "analysis",
    correction_count: int = 0,
    source_id: str | None = None,
) -> None:
    from app.services.memory_service import MemoryService

    now = _utcnow()
    record = await MemoryService(db_session).create_episodic_memory(
        user_id=user_id,
        summary=summary,
        source_type=source_type,
        source_id=source_id if source_id is not None else f"src_{uuid4().hex[:8]}",
        occurred_at=now - timedelta(hours=hours_ago),
        importance_score=0.5,
        tags=[f"task_type:{tag}"] if tag else [],
        evidence_refs=[{"type": "event", "id": f"evt_{uuid4().hex[:8]}"}],
        due_at=(
            now - timedelta(hours=due_hours_ago) if due_hours_ago is not None else None
        ),
        resolved_at=now - timedelta(hours=1) if resolved else None,
    )
    if record is not None and correction_count:
        # 被纠正画像（ctx04）：写入服务不带 correction_count 入参——直接 ORM
        # 修正（评测种子面，非产品行为面）。
        record.correction_count = correction_count
        await db_session.commit()


async def _add_foreign_episodic(db_session: Any, summary: str, tag: str) -> None:
    await _add_episodic(
        db_session, user_id=uuid4(), summary=summary, tag=tag, hours_ago=1
    )


# ---------------------------------------------------------------------------
# 场景定义（B03 CTX 族逐一对应）
# ---------------------------------------------------------------------------


async def _seed_ctx01(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    await _add_episodic(
        db,
        user_id=user_id,
        summary="上次数学练习用了错题本方法，效果不错",
        tag="math_practice",
        hours_ago=6,
    )
    return {}


async def _seed_ctx02(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    await _add_episodic(
        db,
        user_id=user_id,
        summary="math exercise plan with word count and progress worked well",
        tag="math_practice",
        hours_ago=6,
    )
    await _add_foreign_episodic(db, "他人用户的私有数学练习记录", "math_practice")
    return {"foreign": True}


async def _seed_ctx03(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    # 跨课程失败历史：essay_writing 失败 × math 查询（锚零交集）——FIX52 硬拒面。
    await _add_episodic(
        db,
        user_id=user_id,
        summary="math exercise plan with word count and progress failed overdue",
        tag="essay_writing",
        hours_ago=4,
        due_hours_ago=2,
    )
    await _add_foreign_episodic(db, "他人用户的作文失败记录", "essay_writing")
    return {"foreign": True}


async def _seed_ctx04(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    # 被纠正两次的旧画像经验（选择面以 conflict_penalty 计量；否认全语义归
    # 冲突解决器既有权威）。
    await _add_episodic(
        db,
        user_id=user_id,
        summary="math exercise plan with word count and progress",
        tag="math_practice",
        hours_ago=6,
        correction_count=2,
    )
    return {}


async def _seed_ctx05(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    # 过期约束：到期未解决（TTL/failed 面）+ 已超 90 天 stale 行。
    await _add_episodic(
        db,
        user_id=user_id,
        summary="过期约束：每天必须做满 3 小时（已到期未解决）",
        tag="time_rule",
        hours_ago=24,
        due_hours_ago=20,
    )
    await _add_episodic(
        db,
        user_id=user_id,
        summary="math exercise plan with word count and progress old",
        tag="math_practice",
        hours_ago=24 * 120,
    )
    return {}


async def _seed_ctx06(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    # 外部资料伪偏好：document 来源行只能走 episodic 面，不得进 preferences。
    await _add_episodic(
        db,
        user_id=user_id,
        summary="外部资料说应该先刷题（document 来源行）",
        tag="math_practice",
        hours_ago=5,
        source_type="document",
    )
    return {}


async def _seed_ctx07(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    # 缺失 source：空 source_id/source_type（provenance 如实 unknown/missing）。
    await _add_episodic(
        db,
        user_id=user_id,
        summary="math exercise plan with word count and progress no-source",
        tag="math_practice",
        hours_ago=5,
        source_type="",
        source_id="",
    )
    return {}


async def _seed_ctx08(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    # 唯一 optional 候选 = 异类型失败（required-memory query 下全拒 → bypass 面）。
    await _add_episodic(
        db,
        user_id=user_id,
        summary="单词背诵任务到期未完成，连续失败",
        tag="vocab_memorization",
        hours_ago=4,
        due_hours_ago=2,
    )
    return {}


async def _seed_ctx08_good(db: Any, user_id: UUID) -> dict:
    await _add_goal(db, user_id, "期末计算机网络冲 85 分")
    await _add_episodic(
        db,
        user_id=user_id,
        summary="上次数学练习用了错题本方法，效果不错",
        tag="math_practice",
        hours_ago=6,
    )
    return {}


SCENARIOS: tuple[_Scenario, ...] = (
    _Scenario(
        "ctx01_time_budget",
        "CTX-01",
        "今天临时只有15分钟，先做点什么",
        _seed_ctx01,
        {"goal_present": True, "illegal": 0},
    ),
    _Scenario(
        "ctx02_same_project_example",
        "CTX-02",
        "math exercise plan with word count and progress",
        _seed_ctx02,
        {"goal_present": True, "illegal": 0, "gate_on_selects_example": True},
    ),
    _Scenario(
        "ctx03_cross_course_failure",
        "CTX-03",
        "math exercise plan with word count and progress",
        _seed_ctx03,
        {
            "goal_present": True,
            "illegal": 0,
            "gate_on_hard_rejects": "negative_transfer_cross_type",
        },
    ),
    _Scenario(
        "ctx04_denied_old_profile",
        "CTX-04",
        "math exercise plan with word count and progress",
        _seed_ctx04,
        {"goal_present": True, "illegal": 0},
    ),
    _Scenario(
        "ctx05_expired_constraint",
        "CTX-05",
        "math exercise plan with word count and progress",
        _seed_ctx05,
        {"goal_present": True, "illegal": 0},
    ),
    _Scenario(
        "ctx06_external_pseudo_preference",
        "CTX-06",
        "先刷题还是先看书",
        _seed_ctx06,
        {"goal_present": True, "illegal": 0},
    ),
    _Scenario(
        "ctx07_missing_source",
        "CTX-07",
        "math exercise plan with word count and progress",
        _seed_ctx07,
        {"goal_present": True, "illegal": 0},
    ),
    _Scenario(
        "ctx08_all_optional_rejected_mandatory_kept",
        "CTX-08",
        "继续上次的数学练习，回顾上次错题",
        _seed_ctx08,
        {"goal_present": True, "illegal": 0, "required_memory_bypass": True},
    ),
    _Scenario(
        "ctx08_good_required_memory_recall",
        "CTX-08+",
        "继续上次的数学练习，回顾上次错题",
        _seed_ctx08_good,
        {"goal_present": True, "illegal": 0, "gate_on_recalls": True},
    ),
)


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------


async def _build_pack(
    db_session: Any, user_id: UUID, query: str, *, gate_on: bool
) -> Any:
    from app.config import settings
    from app.core.context_budget import ContextBudgetScheduler
    from app.core.context_pack import ContextPackBuilder

    original_flag = settings.ENABLE_MEMORY_UTILITY_GATE
    original_selfcheck = getattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False)
    try:
        settings.ENABLE_MEMORY_UTILITY_GATE = gate_on
        settings.ENABLE_MEMORY_USE_SELFCHECK = (
            False  # 隔离 M-05 selfcheck（独立下游词法门）
        )
        scheduler = ContextBudgetScheduler(
            budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 600}}
        )
        builder = ContextPackBuilder(db_session, scheduler=scheduler)
        return await builder.build(user_id, intent="chat", query_text=query)
    finally:
        settings.ENABLE_MEMORY_UTILITY_GATE = original_flag
        settings.ENABLE_MEMORY_USE_SELFCHECK = original_selfcheck


def _pack_facts(pack: Any) -> dict:
    meta = pack.metadata or {}
    gate = meta.get("memory_utility_gate") or {}
    goal_blob = json.dumps(
        pack.to_prompt_context().get("active_goals"), ensure_ascii=False, default=str
    )
    return {
        "episodic_summaries": [
            str(e.get("summary") or "") for e in pack.episodic_memories
        ],
        "episodic_ids": [str(e.get("id") or "") for e in pack.episodic_memories],
        "goal_present": "计算机网络" in goal_blob,
        "gate_meta": gate,
        "pref_keys": sorted((pack.preferences or {}).keys()),
    }


async def run_surface2(runs_dir: Path) -> int:
    """逐场景 × 三方式跑真实装配面；oracle 断言 + 汇总落盘。"""
    from tests.v3_action_eval.dbfixture import ScenarioDB

    results: list[dict] = []
    failures: list[str] = []
    for scenario in SCENARIOS:
        row: dict[str, Any] = {
            "scenario": scenario.key,
            "ctx_ref": scenario.ctx_ref,
            "query": scenario.query,
            "modes": {},
        }
        for mode in ("gate_off", "gate_on", "no_history"):
            async with ScenarioDB() as db:
                factory = db.session_factory()
                session = factory()
                try:
                    user_id = await _seed_user(session)
                    probe = dict(await scenario.seed_rows(session, user_id))
                    if mode == "no_history":
                        # B 对照：清空 optional 历史（mandatory goal 保留）。
                        from sqlalchemy import delete

                        from app.models.memory import EpisodicMemory

                        await session.execute(
                            delete(EpisodicMemory).where(
                                EpisodicMemory.user_id == user_id
                            )
                        )
                        await session.commit()
                    pack = await _build_pack(
                        session, user_id, scenario.query, gate_on=(mode == "gate_on")
                    )
                    facts = _pack_facts(pack)
                    facts["seed_probe"] = probe
                    row["modes"][mode] = facts
                finally:
                    await session.close()
        verdict = _judge(scenario, row)
        row["oracle_ok"] = verdict["ok"]
        row["oracle_notes"] = verdict["notes"]
        if not verdict["ok"]:
            failures.append(f"{scenario.key}: {verdict['notes']}")
        results.append(row)
        print(
            f"[q02-s2] {scenario.key}: ok={verdict['ok']} {verdict['notes']}",
            file=sys.stderr,
        )

    summary = {
        "task": "V4-Q02",
        "kind": "SURFACE2_SELECTION_FOUR_MODE_ZERO_MODEL",
        "surface": "ContextPackBuilder.build（M-03 预筛 + I02 效用门；D 臂唯一集成面）",
        "modes": {"gate_off": "A/C 选择语义", "gate_on": "D", "no_history": "B 对照"},
        "oracle_frozen": "不合法引用=0；必要记忆不可全部拒用；selected⊆input（B03 配对集 CTX 族）",
        "scenarios": results,
        "all_ok": not failures,
        "failures": failures,
    }
    out = runs_dir / "surface2_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"[q02-s2] all_ok={summary['all_ok']} failures={failures}", file=sys.stderr)
    return 0 if summary["all_ok"] else 1


def _judge(scenario: _Scenario, row: dict) -> dict:
    notes: list[str] = []
    gate_off = row["modes"]["gate_off"]
    gate_on = row["modes"]["gate_on"]

    # 全局 oracle ①：不合法引用=0（wrong-user 行任何方式都不得出现）。
    for mode, facts in row["modes"].items():
        blob = " ".join(facts["episodic_summaries"])
        if "他人用户" in blob or "他人用户的" in blob:
            notes.append(f"{mode}: ILLEGAL wrong-user row surfaced")
    # 全局 oracle ②：mandatory 当前约束（goal）各方式保留。
    for mode, facts in row["modes"].items():
        if scenario.expect.get("goal_present") and not facts["goal_present"]:
            notes.append(f"{mode}: mandatory goal missing")
    # 全局 oracle ③：selected ⊆ input——按内容比对（各方式独立种子库，id 不
    # 可跨库比较）：gate_on 的选择集不得包含 gate_off 之外的条目（无复活路径）。
    set_off = set(gate_off["episodic_summaries"])
    set_on = set(gate_on["episodic_summaries"])
    if not set_on <= set_off:
        notes.append("gate_on selected set not subset of gate_off (resurrection path)")

    if scenario.expect.get("gate_on_selects_example"):
        if not any("worked well" in s for s in gate_on["episodic_summaries"]):
            notes.append("gate_on dropped legal positive example (recall loss)")
    if scenario.expect.get("gate_on_hard_rejects"):
        reason = scenario.expect["gate_on_hard_rejects"]
        decisions = gate_on["gate_meta"].get("decisions", [])
        if not any(
            not d.get("selected") and reason in d.get("reasons", []) for d in decisions
        ):
            notes.append(f"gate_on missing hard-reject reason {reason}")
        if any("overdue" in s for s in gate_on["episodic_summaries"]):
            notes.append("gate_on cross-type failure entered pack")
    if scenario.expect.get("required_memory_bypass"):
        meta = gate_on["gate_meta"]
        if (
            not meta
            or not meta.get("bypassed")
            or meta.get("verdict") != "required_memory_recall_miss_bypass"
        ):
            notes.append(
                f"gate_on bypass not registered: verdict={meta.get('verdict')}"
            )
        if not gate_on["episodic_summaries"]:
            notes.append("gate_on silently empty on required-memory (not allowed)")
        if gate_on["gate_meta"].get("precision") not in (None,):
            notes.append("precision must be N/A (None) on bypass, not 0%/100%")
    if scenario.expect.get("gate_on_recalls"):
        if not any("错题本" in s for s in gate_on["episodic_summaries"]):
            notes.append("gate_on failed to recall good required memory")

    return {"ok": not notes, "notes": notes or ["all oracle checks passed"]}


__all__ = ["run_surface2", "SCENARIOS"]
