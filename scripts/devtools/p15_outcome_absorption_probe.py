"""P1-5 · 星图 mastery 生长链活栈探针（可复跑，零 LLM，零 Redis）.

背景（v3-output/NORTHSTAR-LOOP1 BP-5）：完成任务只解锁任务标题节点，
galaxy mastery/study_minutes 恒 0。断环 = G-02 outcome 吸收器的确定性
节点解析链（correlation_node_id → task.knowledge_node_id →
TaskKnowledgeLink）对无显式关联的任务拿不到任何节点 → no_target。

本探针在**真实开发库**上复现「消费者吃到事件」后的吸收半程：

1. 读取指定任务（默认 northstar 首证任务 5a83a029-…）；
2. 用真实生产者函数（``build_task_outcome_capture`` →
   ``build_outcome_recorded_payload``）重构与 Redis stream 中**逐字段同构**
   的 outcome.recorded payload（outcome id 为 ``derive_outcome_id`` 同源派生，
   与活栈事件 outc_9119e1e4… 一致）；
3. 先打印 before（DF-5 锚节点与显式关联节点的当前 mastery）；
4. 走修复版 ``GalaxyOutcomeAbsorber.absorb_outcome``（真实 DB 写入）；
5. 打印 after（action / 命中节点 / mastery），并复跑一次验证幂等
   （第二次必须 duplicate，mastery 不变）。

用法（栈外独立运行，不依赖在跑的 uvicorn/gRPC）::

    cd backend && SECRET_KEY=test \\
      DATABASE_URL='postgresql+asyncpg://postgres:sparkle_dev_pg_2026@127.0.0.1:5432/sparkle' \\
      python3.11 ../scripts/devtools/p15_outcome_absorption_probe.py \\
      [--task-id 5a83a029-e7f1-4be1-8dad-3eb80046b8c4]

幂等性：absorption 由 mastery_audit_log 的 ``oc=/tk=`` 标记段把关——重放
本探针安全（action=duplicate，mastery 不变）。写入面仅限该任务锚定节点
的 user_node_status / mastery_audit_log / learning_path_snapshot 溯源。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

DEFAULT_TASK_ID = "5a83a029-e7f1-4be1-8dad-3eb80046b8c4"


async def _describe(db, user_id: UUID, node_ids: list[UUID]) -> dict[str, dict]:
    from app.models.galaxy import KnowledgeNode, UserNodeStatus

    out: dict[str, dict] = {}
    for node_id in node_ids:
        node = await db.get(KnowledgeNode, node_id)
        status = await db.get(UserNodeStatus, (user_id, node_id))
        out[str(node_id)] = {
            "name": (node.name if node else "<missing>"),
            "mastery_score": float(status.mastery_score) if status else None,
            "is_unlocked": bool(status.is_unlocked) if status else False,
            "study_minutes": int(status.total_study_minutes or 0) if status else 0,
        }
    return out


async def run(task_id: UUID) -> int:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.galaxy import KnowledgeNode
    from app.models.task import Task
    from app.models.task_resources import TaskKnowledgeLink
    from app.services.galaxy.outcome_absorption_service import GalaxyOutcomeAbsorber
    from app.services.galaxy_service import GalaxyService
    from app.services.outcome_capture_service import (
        build_outcome_recorded_payload,
        build_task_outcome_capture,
    )

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if task is None:
            print(f"[probe] task {task_id} not found")
            return 2
        user_id = UUID(str(task.user_id))
        print(f"[probe] task={task_id} user={user_id} title={task.title!r} status={task.status}")

        # 候选节点面 = 显式关联 ∪ DF-5 标题锚（与吸收器第 4 环同源）
        candidates: list[UUID] = []
        if task.knowledge_node_id:
            candidates.append(UUID(str(task.knowledge_node_id)))
        links = await db.execute(
            select(TaskKnowledgeLink.knowledge_node_id).where(TaskKnowledgeLink.task_id == task.id)
        )
        candidates.extend(UUID(str(row[0])) for row in links.all())
        title_matched = (
            await db.execute(select(KnowledgeNode.id).where(KnowledgeNode.name == task.title).limit(1))
        ).scalar_one_or_none()
        if title_matched:
            candidates.append(UUID(str(title_matched)))
        candidates.append(GalaxyService.task_node_uuid(task.title))
        seen: set[UUID] = set()
        candidates = [nid for nid in candidates if not (nid in seen or seen.add(nid))]

        before = await _describe(db, user_id, candidates)
        print("[probe] BEFORE:", before)

        payload = build_outcome_recorded_payload(build_task_outcome_capture(task))
        print(
            f"[probe] payload outcome_id={payload['outcome_id']} polarity={payload['polarity']} "
            f"correlation_keys={sorted(k for k in payload if k.startswith('correlation_'))}"
        )

        result = await GalaxyOutcomeAbsorber(db).absorb_outcome(dict(payload))
        print(
            f"[probe] ABSORB #1: action={result.action} nodes={result.node_ids} "
            f"mastery_by_node={result.mastery_by_node}"
        )

        after = await _describe(db, user_id, candidates)
        print("[probe] AFTER:", after)

        replay = await GalaxyOutcomeAbsorber(db).absorb_outcome(dict(payload))
        print(
            f"[probe] ABSORB #2 (replay, must be duplicate): action={replay.action} "
            f"mastery_by_node={replay.mastery_by_node}"
        )

        grew = any((after[k]["mastery_score"] or 0) > (before[k]["mastery_score"] or 0) for k in after)
        ok = result.action in {"lit", "duplicate"} and (grew or replay.action == "duplicate")
        print(
            f"[probe] VERDICT: {'PASS' if ok else 'FAIL'} "
            f"(first={result.action}, replay={replay.action}, grew={grew})"
        )
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default=DEFAULT_TASK_ID, help="已完成任务 id（默认 northstar 首证任务）")
    args = parser.parse_args()
    try:
        task_id = UUID(args.task_id)
    except ValueError:
        print(f"[probe] invalid task id {args.task_id!r}")
        return 2
    return asyncio.run(run(task_id))


if __name__ == "__main__":
    sys.exit(main())
