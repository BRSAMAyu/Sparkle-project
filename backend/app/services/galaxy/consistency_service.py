"""G-04 · Galaxy 对 Correction/Delete/Version 的一致性 —— 派生视图不留残影.

定位（stream=GALAXY, gate=V3-3, locks=galaxy-model+privacy-delete）：错题/任务/
草稿节点被删除或纠正后，星图派生读面（学习状态、Review 信号、节点详情溯源、
目标关联）必须同步——**不留残影、不复活旧版本**，且**不重建任何权威真源**。

三类写面的按类型处理（卡面 work 2）：
- ``error_book``（document/材料证据面）：错题软删（``is_deleted`` tombstone）
  后——①剪除 ``UserNodeStatus.learning_path_snapshot.graph_event_sources``
  中引用该错题的溯源行（node detail 残影）；②重算 ``signal:weak_at`` 弱点
  标记——该用户在这些节点上已无存活错题证据时摘除（学习状态 WEAK 残影）；
  ③失效星图读面视图缓存（``view:get_galaxy_graph`` ttl=600 + shield 10s，
  NBP-4 同款失效面）——否则 recent_error_count/review_signal 旧值最长 10 分钟。
- ``task``：任务硬删（``TaskService.delete``）后失效读面——目标关联
  （``_get_goal_connected_node_ids``）旧值残影。已吸收的掌握度与溯源**刻意
  不回滚**：真实完成过的学习是已发生事实（absorber 的 GHOST-OUTCOME 守卫
  阻止已删任务的 outcome 再被点亮，回归见 test_outcome_absorption）。
- ``outcome_ledger``：极性翻转防御（corrected）只写纠正溯源、不二次点亮，
  读面零变化；真正的 outcome 删除路径尚不存在，本模块的通用
  ``handle_reference_deleted`` 为其预留（剪溯源 + 失效，不含掌握度回滚）。
- ``memory``（episodic）：galaxy 读面不读 episodic memory（零耦合，已核），
  无派生残影面。
- ``document``：``document.ontology_created`` 溯源以 ``source_type="document"``
  + ``reference_id=file_id`` 落库；文档删除路径尚未落地，同样走通用 handler。

边界纪律（卡面 forbidden）：
- 不重建真源：本模块只做**派生面**修复（snapshot 溯源行、全局弱点标记、
  视图缓存），mastery 账本（``mastery_audit_log``）与 tombstone 本体不动。
- 不做全图重建：溯源剪除按受影响节点定界（``node_ids`` 已知时走主键定位，
  卡面 work 3），绝不扫全量 ``UserNodeStatus``。
- 所有清理 best-effort：删除主流程（tombstone 提交）不因图谱派生面故障而
  失败——调用方包 try/except，本模块内部只保证自身会话写一致。
"""

from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import UserNodeStatus

#: ``graph_event_sources`` 里可被"源头删除"作废的 source_type 注册面。
#: 值为该面在 ``UserNodeStatus`` 上的溯源语义（仅文档用途；键供分派）。
PRUNEABLE_SOURCE_TYPES = frozenset({"error_book", "document", "translation", "outcome_ledger", "task_completion"})


class GalaxyConsistencyService:
    """Post-delete / post-correction consistency for Galaxy derived views."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- by-type entry points ---------------------------------------------

    async def handle_error_deleted(
        self, *, user_id: UUID, error_id: UUID, node_ids: list[UUID] | None = None
    ) -> dict[str, int]:
        """错题删除（软删 tombstone 已由调用方提交）后的星图派生面清理。

        三步：溯源剪除 → 弱点标记重算 → 读面视图缓存失效。
        返回观测计数（剪除的状态行数 / 摘除的弱点标记数 / 失效的缓存键数）。
        """
        target_node_ids = [nid for nid in (node_ids or []) if isinstance(nid, UUID)]
        pruned = await self.prune_provenance(
            user_id=user_id, source_type="error_book", reference_id=error_id, node_ids=target_node_ids
        )
        cleared_tags = 0
        if target_node_ids:
            cleared_tags = await self.recompute_weak_signals(user_id=user_id, node_ids=target_node_ids)
        invalidated = await self.invalidate_read_model(user_id)
        return {
            "pruned_statuses": pruned,
            "weak_tags_cleared": cleared_tags,
            "cache_keys_deleted": invalidated,
        }

    async def handle_reference_deleted(
        self,
        *,
        user_id: UUID,
        source_type: str,
        reference_id: UUID | str,
        node_ids: list[UUID] | None = None,
    ) -> dict[str, int]:
        """通用溯源面删除一致性（document/translation/outcome_ledger/task）。

        剪除 (source_type, reference_id) 溯源行 + 失效读面。弱点标记重算仅
        error_book 面（其余面不写弱点标记，无需重算）。
        """
        if source_type not in PRUNEABLE_SOURCE_TYPES:
            raise ValueError(f"unknown pruneable source_type: {source_type}")
        target_node_ids = [nid for nid in (node_ids or []) if isinstance(nid, UUID)]
        pruned = await self.prune_provenance(
            user_id=user_id, source_type=source_type, reference_id=reference_id, node_ids=target_node_ids
        )
        invalidated = await self.invalidate_read_model(user_id)
        return {"pruned_statuses": pruned, "weak_tags_cleared": 0, "cache_keys_deleted": invalidated}

    # -- recompute primitives ---------------------------------------------

    async def prune_provenance(
        self,
        *,
        user_id: UUID,
        source_type: str,
        reference_id: UUID | str,
        node_ids: list[UUID] | None = None,
    ) -> int:
        """剪除 ``graph_event_sources`` 中 (source_type, reference_id) 命中的溯源行.

        定界纪律：``node_ids`` 已知（删除实体的关联节点，可从实体行读到）
        时按复合主键定位，O(受影响节点)；未知时按 user 定界（该用户的全部
        状态行）——仍不做全表扫描。JSON 列**拷贝后**再赋值（原地变更不产生
        UPDATE，与 outcome_absorber ``_stamp_absorbed_marker`` 同款纪律）。
        幂等：重复调用零变更零写。
        """
        ref_text = str(reference_id) if reference_id is not None else ""
        if not ref_text:
            return 0

        stmt = select(UserNodeStatus).where(UserNodeStatus.user_id == user_id)
        if node_ids:
            stmt = stmt.where(UserNodeStatus.node_id.in_(node_ids))
        result = await self.db.execute(stmt)
        statuses = list(result.scalars().all())

        pruned = 0
        for status in statuses:
            raw_snapshot = getattr(status, "learning_path_snapshot", None)
            if not isinstance(raw_snapshot, dict):
                continue
            sources = raw_snapshot.get("graph_event_sources")
            if not isinstance(sources, list) or not sources:
                continue
            kept = [
                item
                for item in sources
                if not (
                    isinstance(item, dict)
                    and str(item.get("source_type") or "") == source_type
                    and str(item.get("reference_id") or "") == ref_text
                )
            ]
            if len(kept) == len(sources):
                continue
            # snapshot 顶层**拷贝后再赋值**（拷贝在先、任何变更只落在副本上）：
            # JSON 列对同对象原地变更不产生 UPDATE——若先改原对象再拷贝，
            # 已提交值与待写值经 == 比较相等，UPDATE 被静默吞掉（与本服务
            # `_stamp_absorbed_marker` 同款拷贝纪律，红测可捕获）。
            snapshot = dict(raw_snapshot)
            snapshot["graph_event_sources"] = kept
            status.learning_path_snapshot = snapshot
            self.db.add(status)
            pruned += 1
        if pruned:
            await self.db.commit()
        return pruned

    async def recompute_weak_signals(self, *, user_id: UUID, node_ids: list[UUID]) -> int:
        """重算弱点标记：该用户在节点上已无存活错题证据 → 摘除 ``signal:weak_at``.

        权威判据是 ErrorRecord 存活面（``is_deleted`` tombstone，与读面
        ``_get_recent_error_counts_by_node`` 同一真源）；``KnowledgeNode``
        上的标记只是派生信号。摘除走既有 ``tag_node_signal(active=False)``
        （keywords 集合语义，幂等），不碰任何 mastery 状态。
        """
        if not node_ids:
            return 0
        from app.models.error_book import ErrorRecord
        from app.services.galaxy.graph_evolution_service import GraphEvolutionService

        still_weak: list[UUID] = []
        try:
            result = await self.db.execute(
                select(ErrorRecord.linked_knowledge_node_ids).where(
                    ErrorRecord.user_id == user_id,
                    ErrorRecord.is_deleted.is_(False),
                )
            )
            live_by_node: set[UUID] = set()
            for (linked_ids,) in result.all():
                for raw in linked_ids or []:
                    try:
                        live_by_node.add(raw if isinstance(raw, UUID) else UUID(str(raw)))
                    except (ValueError, AttributeError):
                        continue
            still_weak = [nid for nid in node_ids if nid in live_by_node]
        except Exception as exc:  # noqa: BLE001 — 判据不可读时保守：不摘任何标记
            logger.warning("weak-signal recompute evidence read failed for user {}: {}", user_id, exc)
            return 0

        evolution = GraphEvolutionService(self.db)
        cleared = 0
        for node_id in node_ids:
            if node_id in still_weak:
                continue
            if await evolution.structure.tag_node_signal(node_id, GraphEvolutionService.WEAK_SIGNAL_TAG, active=False):
                cleared += 1
        return cleared

    async def invalidate_read_model(self, user_id: UUID) -> int:
        """失效星图读面视图缓存（NBP-4 canonical 失效面：Redis 模式键 + shield）。

        best-effort：缓存面不可达只降级（最坏退回 TTL 自然过期），不回滚
        调用方已提交的删除事务。
        """
        from app.services.galaxy.outcome_absorption_service import invalidate_galaxy_graph_view_cache

        try:
            return await invalidate_galaxy_graph_view_cache(user_id)
        except Exception as exc:  # noqa: BLE001 — 读投影失效失败不阻断删除主流程
            logger.warning("galaxy read-model invalidation failed for user {}: {}", user_id, exc)
            return 0


async def invalidate_galaxy_view_for_user(user_id: UUID) -> None:
    """模块级便捷失效（服务层写路径接线用，best-effort）。

    供任务硬删/事件消费等"图谱可见状态变了但从未失效读面"的路径接入
    （NBP-4/70eb9b68 同类缺口的收口点）。
    """
    from app.services.galaxy.outcome_absorption_service import invalidate_galaxy_graph_view_cache

    try:
        await invalidate_galaxy_graph_view_cache(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("galaxy view invalidation failed for user {}: {}", user_id, exc)


__all__ = [
    "GalaxyConsistencyService",
    "PRUNEABLE_SOURCE_TYPES",
    "invalidate_galaxy_view_for_user",
]
