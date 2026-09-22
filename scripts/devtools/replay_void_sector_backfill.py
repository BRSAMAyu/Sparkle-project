#!/usr/bin/env python3
"""存量 VOID 节点星域回填重放（SECTOR-BACKFILL-Dedup 配套运维工具）。

背景（COLDSTART 双可靠性项之一）：热路径 ``ensure_backfill_for_user`` 的选择面
修复后，completed-VOID 节点不再走每次取图的重选循环（那是队列灌满、背压丢新
任务的根因）；本脚本提供这些存量节点的幂等重放手段：

- 按 user 分组、进程内直接调用 ``NodeSectorService.classify_nodes_by_ids``
  （逐节点 LLM 重分类，每批 commit + 按 user 失效星图缓存），不经过
  glm_batch 队列（不占背压额度、不依赖 celery worker 在跑）；
- 幂等：可重复执行，重跑只是按当前 LLM 判定重写 sector_weights / dominant /
  坐标；LLM 单节点失败只标 failed，不影响其余节点与后续批次；
- 默认重放「未分类 / VOID 主星域 / pending / failed」；completed-VOID 是否
  包含由 ``--no-completed-void`` 控制（默认包含——它们正是积压主体）。

用法（backend 依赖已装、DB 可达；worktree 无 .env 时先导出必要变量）::

    SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://... \
        python scripts/devtools/replay_void_sector_backfill.py --dry-run
    SECRET_KEY=test DATABASE_URL=... \
        python scripts/devtools/replay_void_sector_backfill.py \
        --user-id <uuid> --batch-size 12

零凭据：本脚本不读不写任何密钥；只按运行者显式给的 DATABASE_URL 连库。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from loguru import logger  # noqa: E402

from app.models.sector import SectorCode  # noqa: E402


async def _targets_by_user(
    session,
    *,
    user_id: str | None,
    include_completed_void: bool,
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """按 user 分组收集需要重放的节点 id。

    用户↔节点关联与 ``GalaxyService`` 取图同源（``UserNodeStatus`` join，
    见 galaxy_service.get_graph_view）。选择语义（与修复后的热路径互补——
    这里是重放面，包含 completed-VOID）：
    - 未分类（weights NULL / status NULL、pending、failed）一律重放；
    - dominant == VOID 且已 completed 的节点仅在 include_completed_void 时重放。
    """
    from sqlalchemy import select

    from app.models.galaxy import KnowledgeNode, UserNodeStatus

    stmt = (
        select(
            UserNodeStatus.user_id,
            KnowledgeNode.id,
            KnowledgeNode.dominant_sector_code,
            KnowledgeNode.sector_classification_status,
        )
        .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
        .where(KnowledgeNode.deleted_at.is_(None))  # 软删节点不重放
        .order_by(UserNodeStatus.user_id, KnowledgeNode.created_at.asc())
    )
    if user_id:
        stmt = stmt.where(UserNodeStatus.user_id == uuid.UUID(user_id))

    grouped: dict[uuid.UUID, list[uuid.UUID]] = {}
    for owner_id, node_id, dominant, status in (await session.execute(stmt)).all():
        completed = str(status or "") == "completed"
        if completed and not include_completed_void:
            continue
        needs_replay = not completed or str(dominant or "") == SectorCode.VOID.value
        if not needs_replay:
            continue
        grouped.setdefault(owner_id, []).append(node_id)
    return grouped


async def main_async(args: argparse.Namespace) -> int:
    from app.db.session import AsyncSessionLocal
    from app.services.node_sector_service import NodeSectorService

    async with AsyncSessionLocal() as session:
        grouped = await _targets_by_user(
            session,
            user_id=args.user_id,
            include_completed_void=args.include_completed_void,
        )
        total = sum(len(ids) for ids in grouped.values())
        logger.info(
            "replay targets: {} nodes across {} users{}",
            total,
            len(grouped),
            f" (user={args.user_id})" if args.user_id else " (all users)",
        )
        if total == 0:
            logger.info("nothing to replay")
            return 0
        if args.dry_run:
            shown = 0
            for owner_id, node_ids in grouped.items():
                for node_id in node_ids:
                    if shown >= args.sample:
                        break
                    logger.info("  dry-run target user={} node={}", owner_id, node_id)
                    shown += 1
            logger.info("dry-run only, no writes; rerun without --dry-run to replay")
            return 0

        processed = updated = 0
        for owner_id, node_ids in grouped.items():
            for start in range(0, len(node_ids), args.batch_size):
                chunk = node_ids[start : start + args.batch_size]
                result = await NodeSectorService(session).classify_nodes_by_ids(
                    user_id=owner_id,
                    node_ids=chunk,
                )
                processed += result.get("processed", 0)
                updated += result.get("updated", 0)
                logger.info(
                    "chunk replayed user={} processed={} updated={} (cum {}/{})",
                    owner_id,
                    result.get("processed", 0),
                    result.get("updated", 0),
                    processed,
                    total,
                )
        logger.info("replay done: processed={} updated={}", processed, updated)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay VOID node sector backfill (idempotent, in-process)")
    parser.add_argument("--user-id", default=None, help="scope to one user (subjects.user_id); default all users")
    parser.add_argument("--batch-size", type=int, default=24, help="nodes per classify batch (default 24)")
    parser.add_argument("--dry-run", action="store_true", help="list targets without LLM calls or writes")
    parser.add_argument("--sample", type=int, default=20, help="dry-run listing cap (default 20)")
    parser.add_argument(
        "--no-completed-void",
        dest="include_completed_void",
        action="store_false",
        help="exclude completed nodes whose dominant sector is VOID",
    )
    parser.set_defaults(include_completed_void=True)
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
