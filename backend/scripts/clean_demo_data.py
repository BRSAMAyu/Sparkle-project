#!/usr/bin/env python3
"""
Clean Demo Data Script
清理演示数据脚本

用于演示日之前清理数据库中的调试/测试数据。

Usage:
    python scripts/clean_demo_data.py --dry-run  # 查看会删除什么
    python scripts/clean_demo_data.py             # 实际执行清理
"""
import asyncio
import argparse
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.candidate_feedback import CandidateActionFeedback


async def clean_draft_nodes(db: AsyncSession, dry_run: bool = False) -> int:
    """清理所有草稿节点"""

    # 查找所有 draft 节点
    result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.status == "draft")
    )
    draft_nodes = result.scalars().all()

    logger.info(f"Found {len(draft_nodes)} draft nodes")

    if dry_run:
        for node in draft_nodes[:10]:  # Show first 10
            logger.info(f"  - Would delete: {node.name} (created: {node.created_at})")
        if len(draft_nodes) > 10:
            logger.info(f"  - ... and {len(draft_nodes) - 10} more")
        return len(draft_nodes)

    # 实际删除
    deleted_count = 0
    for node in draft_nodes:
        logger.info(f"Deleting draft node: {node.name} ({node.id})")
        await db.delete(node)
        deleted_count += 1

    await db.commit()
    logger.success(f"✅ Deleted {deleted_count} draft nodes")
    return deleted_count


async def clean_old_feedback(db: AsyncSession, days: int = 30, dry_run: bool = False) -> int:
    """清理旧的反馈数据（保留最近 N 天）"""

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(CandidateActionFeedback).where(
            CandidateActionFeedback.created_at < cutoff_date
        )
    )
    old_feedback = result.scalars().all()

    logger.info(f"Found {len(old_feedback)} feedback records older than {days} days")

    if dry_run:
        for fb in old_feedback[:10]:
            logger.info(f"  - Would delete: {fb.action_type} feedback from {fb.created_at}")
        if len(old_feedback) > 10:
            logger.info(f"  - ... and {len(old_feedback) - 10} more")
        return len(old_feedback)

    # 实际删除
    delete_stmt = delete(CandidateActionFeedback).where(
        CandidateActionFeedback.created_at < cutoff_date
    )
    result = await db.execute(delete_stmt)
    await db.commit()

    logger.success(f"✅ Deleted {result.rowcount} old feedback records")
    return result.rowcount


async def clean_orphaned_user_status(db: AsyncSession, dry_run: bool = False) -> int:
    """清理孤立的用户节点状态（节点已被删除但状态仍存在）"""

    # 查找没有对应节点的 UserNodeStatus
    result = await db.execute(
        select(UserNodeStatus)
        .outerjoin(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
        .where(KnowledgeNode.id.is_(None))
    )
    orphaned = result.scalars().all()

    logger.info(f"Found {len(orphaned)} orphaned user node statuses")

    if dry_run:
        for status in orphaned[:10]:
            logger.info(f"  - Would delete: status for node_id={status.node_id}")
        if len(orphaned) > 10:
            logger.info(f"  - ... and {len(orphaned) - 10} more")
        return len(orphaned)

    # 实际删除
    deleted_count = 0
    for status in orphaned:
        logger.info(f"Deleting orphaned status: node_id={status.node_id}")
        await db.delete(status)
        deleted_count += 1

    await db.commit()
    logger.success(f"✅ Deleted {deleted_count} orphaned user node statuses")
    return deleted_count


async def clean_duplicate_nodes(db: AsyncSession, dry_run: bool = False) -> int:
    """清理重复的节点（同名节点保留最新的一个）"""

    # 查找所有节点并按名称分组
    result = await db.execute(select(KnowledgeNode).order_by(KnowledgeNode.created_at))
    all_nodes = result.scalars().all()

    # 按名称分组
    nodes_by_name = {}
    for node in all_nodes:
        if node.name not in nodes_by_name:
            nodes_by_name[node.name] = []
        nodes_by_name[node.name].append(node)

    # 找到重复的
    duplicates_to_delete = []
    for name, nodes in nodes_by_name.items():
        if len(nodes) > 1:
            # 保留最新的，删除旧的
            nodes_sorted = sorted(nodes, key=lambda n: n.created_at, reverse=True)
            duplicates_to_delete.extend(nodes_sorted[1:])

    logger.info(f"Found {len(duplicates_to_delete)} duplicate nodes")

    if dry_run:
        for node in duplicates_to_delete[:10]:
            logger.info(f"  - Would delete duplicate: {node.name} (created: {node.created_at})")
        if len(duplicates_to_delete) > 10:
            logger.info(f"  - ... and {len(duplicates_to_delete) - 10} more")
        return len(duplicates_to_delete)

    # 实际删除
    deleted_count = 0
    for node in duplicates_to_delete:
        logger.info(f"Deleting duplicate node: {node.name} ({node.id})")
        await db.delete(node)
        deleted_count += 1

    await db.commit()
    logger.success(f"✅ Deleted {deleted_count} duplicate nodes")
    return deleted_count


async def main():
    parser = argparse.ArgumentParser(description="Clean demo data for presentation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--feedback-days",
        type=int,
        default=30,
        help="Keep feedback from last N days (default: 30)",
    )
    parser.add_argument(
        "--skip-drafts",
        action="store_true",
        help="Skip cleaning draft nodes",
    )
    parser.add_argument(
        "--skip-feedback",
        action="store_true",
        help="Skip cleaning old feedback",
    )
    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        help="Skip cleaning duplicate nodes",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("🧹 Clean Demo Data Script")
    logger.info("=" * 60)

    if args.dry_run:
        logger.warning("DRY RUN MODE - No actual changes will be made")

    async with AsyncSessionLocal() as db:
        total_cleaned = 0

        # Clean draft nodes
        if not args.skip_drafts:
            logger.info("\n📝 Step 1: Cleaning draft nodes...")
            count = await clean_draft_nodes(db, dry_run=args.dry_run)
            total_cleaned += count

        # Clean old feedback
        if not args.skip_feedback:
            logger.info(f"\n💬 Step 2: Cleaning feedback older than {args.feedback_days} days...")
            count = await clean_old_feedback(db, days=args.feedback_days, dry_run=args.dry_run)
            total_cleaned += count

        # Clean orphaned statuses
        logger.info("\n🧹 Step 3: Cleaning orphaned user node statuses...")
        count = await clean_orphaned_user_status(db, dry_run=args.dry_run)
        total_cleaned += count

        # Clean duplicates
        if not args.skip_duplicates:
            logger.info("\n🔍 Step 4: Cleaning duplicate nodes...")
            count = await clean_duplicate_nodes(db, dry_run=args.dry_run)
            total_cleaned += count

        logger.info("\n" + "=" * 60)
        if args.dry_run:
            logger.info(f"📊 Would clean {total_cleaned} records in total")
            logger.info("Run without --dry-run to actually clean")
        else:
            logger.success(f"✅ Cleaned {total_cleaned} records in total")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
