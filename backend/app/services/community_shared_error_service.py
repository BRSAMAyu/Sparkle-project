"""小队错题卡分享服务（D-COMM-5 · 错题卡互助分享）。

定位（设计卡 §3.5）：小队第一次**知识互助**——把我的错题+掌握度变化
分享到小队，队友看到「谁在哪卡住了」。与既有面零重叠：榜/完成度是
D-COMM-3/4 的进度互助（sprint_task_ledger 口径），本卡是错因互助
（error_book 只读面），纯读 + 分发。

复用裁决：
- 小队与成员鉴权全部委托 D-COMM-3 ``SquadService``（Group(type=SPRINT)
  场景门面），不复制第二套成员语义（照 D-COMM-4 先例）；
- 错题内容服务端取：POST 只收 error_id，服务端校验「本人名下 + 未删除」
  后从 error_records 读取并投影成可分享白名单快照——客户端不可伪造内容；
- 安全过滤复用既有 SAFETY 词库面 ``core/llm_output_validator.py``
  （LLMOutputValidator / output_validator 单例，敏感信息/恶意指令/合规
  词库四层）——分享是 UGC 出用户边界的动作，命中即拒（fail-closed），
  且检查对象=快照本体，快照即所服务内容（关闭分享后 PATCH 错题夹带
  违规内容的 TOCTOU 绕过）。

可分享白名单（诚实性 + 反抄答案裁决，逐字段落界）：
- 分享：question_text、question_image 引用（sparkle-file:// 原样）、
  subject_code、chapter、知识点链接（id/name/primary）、cognitive_tags、
  错因（error_type/root_cause/study_suggestion）、附言、掌握度快照
  （mastery_level/mastery_delta/review_count——如实呈现「卡在哪」，
  负 delta 不粉饰）；
- 不分享：correct_answer、user_answer、latest_analysis.correct_approach/
  similar_traps（≈解题思路/答案——备考互助不能退化成抄答案）、
  ocr_text（与题目内容重复且含噪）、ai_analysis_summary（可能含解析）。

红线（反刷分，D20）：分享**不产生光子/不进任何榜**——本服务不 import
photon/experience/leaderboard/xp 域（AST 钉死），无任何行为量写路径；
tests/unit/test_community_shared_errors.py 以源码扫描 + 行为双断言钉死。
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import _utcnow
from app.core.llm_output_validator import output_validator
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.squad_shared_error import SquadSharedError
from app.models.user import User
from app.schemas.community_shared_errors import (
    MAX_ACTIVE_SHARED_ERRORS_PER_MEMBER,
    SHARED_ERRORS_DEFAULT_LIMIT,
    SHARED_ERRORS_MAX_LIMIT,
    SharedErrorEntry,
    SharedKnowledgeNode,
)
from app.services.community_squad_service import SquadService

logger = logging.getLogger(__name__)

# 拒分享时对客户端的一律话术（违规明细只进服务端日志，不回泄露过滤规则）。
_REJECT_MESSAGE = "内容未通过安全检查，暂不能分享到小队"


class SourceErrorNotFound(LookupError):
    """错题不存在、不属于分享者或已删除（统一 404，不泄露存在性）。"""


class SharedErrorStateError(ValueError):
    """分享状态不允许该操作（超上限等，API 层映射 400）。"""


class SharedErrorRejected(ValueError):
    """内容未通过安全过滤（SAFETY 词库面命中），API 层映射 400。"""


def _coerce_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


class SquadSharedErrorService:
    """错题卡分享：error_book 只读面 → 小队分发的最小门面。"""

    # ------------------------------------------------------------------
    # 快照投影（可分享白名单的唯一事实点）
    # ------------------------------------------------------------------
    @staticmethod
    def _build_content_snapshot(error: ErrorRecord, note: str | None) -> dict:
        """从真实 ErrorRecord 投影可分享白名单（含知识点名称解析的原料）。

        知识点：affected_node_id（主）+ linked_knowledge_node_ids（去重），
        sqlite 路径该列是 JSON 字符串列表，统一 _coerce_uuid 容错（与
        mastery 同步读法一致）。
        """
        primary_id = _coerce_uuid(getattr(error, "affected_node_id", None))
        node_ids: list[UUID] = []
        if primary_id is not None:
            node_ids.append(primary_id)
        for raw in error.linked_knowledge_node_ids or []:
            node_id = _coerce_uuid(raw)
            if node_id is not None and node_id not in node_ids:
                node_ids.append(node_id)

        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        return {
            "question_text": error.question_text,
            # 图片只带 sparkle-file:// 引用原样字符串；解析成可下载 URL 是
            # 网关内 MinIO 鉴权面的事，分享面不新开公共 URL。
            "question_image_ref": error.question_image_url,
            "subject_code": error.subject_code,
            "chapter": error.chapter,
            "knowledge_node_ids": [str(node_id) for node_id in node_ids],
            "cognitive_tags": list(error.cognitive_tags or []),
            "error_type": analysis.get("error_type"),
            "root_cause": analysis.get("root_cause"),
            "study_suggestion": analysis.get("study_suggestion") or analysis.get("study_suggestions"),
            "note": (note or "").strip() or None,
        }

    @staticmethod
    def _moderation_text(snapshot: dict) -> str:
        """安全过滤的输入 = 快照内全部自由文本（fail-closed 的检查对象）。"""
        parts = [
            snapshot.get("question_text") or "",
            snapshot.get("chapter") or "",
            snapshot.get("root_cause") or "",
            snapshot.get("study_suggestion") or "",
            snapshot.get("note") or "",
        ]
        parts.extend(str(tag) for tag in snapshot.get("cognitive_tags") or [])
        return "\n".join(part for part in parts if part)

    @staticmethod
    async def _resolve_node_names_async(db: AsyncSession, node_ids: list[str]) -> dict[str, str]:
        """知识点 id → 名称（缺失节点如实缺席，不造名）。"""
        ids = [nid for nid in (_coerce_uuid(item) for item in node_ids) if nid is not None]
        if not ids:
            return {}
        result = await db.execute(select(KnowledgeNode.id, KnowledgeNode.name).where(KnowledgeNode.id.in_(ids)))
        return {str(row.id): row.name for row in result.all()}

    @staticmethod
    async def _to_entry(
        db: AsyncSession,
        share: SquadSharedError,
        sharer_name: str | None,
    ) -> SharedErrorEntry:
        content = share.content or {}
        node_ids_raw = list(content.get("knowledge_node_ids") or [])
        node_names = await SquadSharedErrorService._resolve_node_names_async(db, node_ids_raw)
        primary_id = node_ids_raw[0] if node_ids_raw else None
        nodes = []
        for raw in node_ids_raw:
            node_id = _coerce_uuid(raw)
            if node_id is None:
                continue
            name = node_names.get(str(node_id))
            if not name:
                continue  # 名称解析不到的节点（节点后被删）如实缺席——不造默认名
            nodes.append(
                SharedKnowledgeNode(
                    id=node_id,
                    name=name,
                    is_primary=(primary_id is not None and str(node_id) == str(primary_id)),
                )
            )
        return SharedErrorEntry(
            share_id=share.id,
            group_id=share.group_id,
            sharer_id=share.sharer_id,
            sharer_name=sharer_name,
            error_id=share.error_id,
            question_text=content.get("question_text"),
            question_image_ref=content.get("question_image_ref"),
            subject_code=content.get("subject_code") or "",
            chapter=content.get("chapter"),
            knowledge_nodes=nodes,
            cognitive_tags=list(content.get("cognitive_tags") or []),
            error_type=content.get("error_type"),
            root_cause=content.get("root_cause"),
            study_suggestion=content.get("study_suggestion"),
            note=content.get("note"),
            mastery_level=float(share.mastery_level or 0.0),
            mastery_delta=float(share.mastery_delta) if share.mastery_delta is not None else None,
            review_count=int(share.review_count or 0),
            created_at=share.created_at,
        )

    # ------------------------------------------------------------------
    # 分享
    # ------------------------------------------------------------------
    @staticmethod
    async def share_error(
        db: AsyncSession,
        group_id: UUID,
        error_id: UUID,
        sharer_id: UUID,
        *,
        note: str | None = None,
    ) -> tuple[SquadSharedError, bool]:
        """分享一张自己的错题到小队（引用 error_id，内容服务端取）。

        返回 (分享记录, 是否新建)；幂等：同一张错题已在册 → 原样返回
        既有分享（reshared=False），不建重复记录。
        """
        await SquadService._get_active_squad(db, group_id)
        await SquadService._require_active_member(db, group_id, sharer_id)

        # 源错题：本人名下 + 未删除（服务端取真实内容的唯一入口）。
        # 先于幂等检查——他人重复分享同一张（非本人）错题必须 404，
        # 不得被「已有在册分享」的幂等分支吞掉。
        result = await db.execute(
            select(ErrorRecord).where(
                ErrorRecord.id == error_id,
                ErrorRecord.user_id == sharer_id,
                ErrorRecord.is_deleted.is_(False),
            )
        )
        error = result.scalar_one_or_none()
        if error is None:
            raise SourceErrorNotFound("错题不存在或不属于你")

        existing = await SquadSharedErrorService._get_active_share(db, group_id, error_id, sharer_id)
        if existing is not None:
            return existing, False

        snapshot = SquadSharedErrorService._build_content_snapshot(error, note)

        # 安全过滤（SAFETY 词库面）：命中即拒，违规明细只进服务端日志。
        verdict = output_validator.validate(SquadSharedErrorService._moderation_text(snapshot))
        if not verdict.is_valid:
            logger.warning(
                "Shared-error rejected by SAFETY lexicon: group=%s error=%s sharer=%s violations=%s",
                group_id,
                error_id,
                sharer_id,
                verdict.violations,
            )
            raise SharedErrorRejected(_REJECT_MESSAGE)

        active_count = await SquadSharedErrorService._active_share_count(db, group_id, sharer_id)
        if active_count >= MAX_ACTIVE_SHARED_ERRORS_PER_MEMBER:
            raise SharedErrorStateError(f"每人在小队内最多同时分享 {MAX_ACTIVE_SHARED_ERRORS_PER_MEMBER} 张错题卡")

        share = SquadSharedError(
            group_id=group_id,
            error_id=error.id,
            sharer_id=sharer_id,
            content=snapshot,
            snapshot_note=snapshot.get("note"),
            mastery_level=float(error.mastery_level or 0.0),
            mastery_delta=float(error.mastery_delta) if error.mastery_delta is not None else None,
            review_count=int(error.review_count or 0),
        )
        db.add(share)
        await db.flush()
        return share, True

    # ------------------------------------------------------------------
    # 列表（成员可见）
    # ------------------------------------------------------------------
    @staticmethod
    async def list_shared_errors(
        db: AsyncSession,
        group_id: UUID,
        requester_id: UUID,
        *,
        limit: int = SHARED_ERRORS_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict:
        """小队错题卡流（新→旧）：仅小队成员可见（非成员 403）。

        - 鉴权：小队存在且 SPRINT + 请求者在册（委托 D-COMM-3）；
        - liveness：源错题被主人删除（软删）→ 该分享自动从流中消失
          （删错题=撤回所有下游曝光，隐私裁决）；
        - 空数据诚实：无分享返回空 items（不造默认卡）。
        """
        await SquadService._get_active_squad(db, group_id)
        await SquadService._require_active_member(db, group_id, requester_id)

        limit = max(1, min(int(limit), SHARED_ERRORS_MAX_LIMIT))
        offset = max(0, int(offset))

        # 在册分享全集（行数有上界：每成员 50 张 × 小队 3-8 人，无需 SQL 级分页）。
        # 注意不做 squad_shared_errors ⋈ error_records 的 SQL join：
        # error_records.id 是原生 postgresql.UUID（sqlite 侧存 32 位 hex），
        # 与 BaseModel.GUID（36 位连字符串）跨类型比较恒不匹配——liveness
        # 改为取回后按 id 集合过滤（方言无关，同 mastery 同步的读法）。
        result = await db.execute(
            select(SquadSharedError, User)
            .outerjoin(User, User.id == SquadSharedError.sharer_id)
            .where(
                SquadSharedError.group_id == group_id,
                SquadSharedError.not_deleted_filter(),
            )
            .order_by(SquadSharedError.created_at.desc(), SquadSharedError.id.asc())
        )
        rows = result.all()

        error_ids = [share.error_id for share, _user in rows]
        live_error_ids: set[UUID] = set()
        if error_ids:
            live_result = await db.execute(
                select(ErrorRecord.id).where(
                    ErrorRecord.id.in_(error_ids),
                    ErrorRecord.is_deleted.is_(False),
                )
            )
            live_error_ids = {row_id for (row_id,) in live_result.all()}

        live_rows = [(share, user) for share, user in rows if share.error_id in live_error_ids]
        total = len(live_rows)

        items = [
            await SquadSharedErrorService._to_entry(
                db, share, (user.nickname if user else None) or (user.username if user else None)
            )
            for share, user in live_rows[offset : offset + limit]
        ]
        return {
            "squad_id": group_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "generated_at": _utcnow(),
            "items": items,
        }

    # ------------------------------------------------------------------
    # 撤回（软删）
    # ------------------------------------------------------------------
    @staticmethod
    async def retract_shared_error(
        db: AsyncSession,
        group_id: UUID,
        share_id: UUID,
        requester_id: UUID,
    ) -> dict:
        """撤回分享（软删）。只有分享者本人能撤回；不存在/已撤回 → 404。"""
        await SquadService._get_active_squad(db, group_id)
        await SquadService._require_active_member(db, group_id, requester_id)

        share = await SquadSharedError.get_by_id(db, share_id)
        if share is None or share.group_id != group_id or share.sharer_id != requester_id or share.is_deleted:
            raise LookupError("分享不存在或已撤回")
        share.soft_delete()
        await db.flush()
        return {"share_id": share.id, "retracted": True, "already_retracted": False}

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    async def _get_active_share(
        db: AsyncSession, group_id: UUID, error_id: UUID, sharer_id: UUID | None = None
    ) -> SquadSharedError | None:
        stmt = select(SquadSharedError).where(
            SquadSharedError.group_id == group_id,
            SquadSharedError.error_id == error_id,
            SquadSharedError.not_deleted_filter(),
        )
        if sharer_id is not None:
            stmt = stmt.where(SquadSharedError.sharer_id == sharer_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _active_share_count(db: AsyncSession, group_id: UUID, sharer_id: UUID) -> int:
        result = await db.execute(
            select(func.count(SquadSharedError.id)).where(
                SquadSharedError.group_id == group_id,
                SquadSharedError.sharer_id == sharer_id,
                SquadSharedError.not_deleted_filter(),
            )
        )
        return int(result.scalar() or 0)
