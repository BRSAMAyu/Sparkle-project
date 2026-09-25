"""S-02 · Community Context Privacy Boundary —— 群上下文隐私红线（单一守卫面）.

红线：群聊/小队的 AI prompt/tool 上下文**绝不能自动带入**私人 Memory/Profile。
群组装的唯一合法输入是 shared context allowlist —— 用户**主动**分享进群的
Goal / Action / Artifact；私人 permission 面（M-03 ``memory_retrieval_prefilter``
的 ``llm_context`` 等私人 purpose）对 surface=group 无感知，因此群面**禁止**
走私人检索路径，必须经过本模块。

与既有真源的关系（不重建真源、零新存储）：

- **分享真源 = 既有 ``SharedResource``**（``collaboration_service.share_resource``
  写入，软删即 revoke）。载体映射（列 → 群上下文类别）：

      plan_id           -> goal      （计划是目标在社区面的分享载体；社区
                                     goal 采纳流以 PLAN 为源，adopted_into_
                                     goal_id 回执）
      task_id           -> action
      knowledge_node_id -> artifact

  词表外的分享载体（seed/cognitive/curiosity/prism 族）群资源 UI 可见是既有
  功能，但**永不进入群 AI 上下文**（本模块直接跳过）。
- **成员真源 = 既有 ``GroupMember``**（软删即离群；SQUAD-REJOIN 部分唯一
  索引保证活跃行口径唯一）。
- **过滤纪律 = M-03/C-03 同构**：纯函数滤芯（无 I/O）+ 固定维度求值顺序 +
  封闭 reason 词表 + ``Rejection``/结果形状逐字对齐 + Prometheus 逐维度/
  逐原因计量；DB 侧只做 allowlist 快照解析（``build_prompt_access_context``）。

两层防线：

1. **快照层（DB）**：``build_prompt_access_context`` 在组装时点解析允许表 ——
   请求者必须是活跃成员（否则 fail-closed 异常）；allowlist 只含「分享行未
   撤销 且 分享者仍是活跃成员」的条目；撤销/离群条目落入 ``invalid_entries``
   携带精确失效原因。离群/revoke 的失效因此是**时序内建**的：下一次组装
   （重新 build）即不再包含。
2. **滤芯层（纯函数）**：``filter_group_prompt_candidates`` 对进入群 prompt
   组装的每个候选做确定性判定（身份 → 类型 → 分享 → 生命周期），陈旧/手工
   构造的上下文同样被逐候选归因拦截（defense in depth）—— 私人 memory/
   profile 类候选在类型维即被拒（词表外），词表内未分享候选在分享维被拒，
   伪造 owner 在分享维被拒（``owner_mismatch``）。

fail-closed 纪律：

- 无群权限上下文（``ctx=None``）→ 全拒（``group_context:no_group_surface``）
  —— 没有可校验的主体/群面就没有放行依据。
- 请求者非活跃成员 → 异常（解析层）/全拒（滤芯层）。
- shared_at 只是元数据：本层不做时间过期（TTL 属 memory 面 M-03），唯一失效
  开关是 revoke / 离群。

封闭 reason 词表（冻结；新增必须 bump ``GROUP_CONTEXT_BOUNDARY_VERSION`` 并
同步 ``test_reason_codes_frozen``）：

    identity:  group_context:no_group_surface
               group_context:requester_not_member
    type:      group_context:unknown_item_type
    share:     group_context:not_in_allowlist
               group_context:owner_mismatch
    lifecycle: group_context:share_revoked
               group_context:sharer_left_group
"""

from __future__ import annotations

# rule-at: orphan-by-design S-02 群上下文隐私边界守卫库：生产消费方是后续群 AI 面
# （当前全仓尚无 group prompt 组装点，本卡交付该面必须经过的唯一边界 + 契约测试钉死），
# 由 tests/unit/test_community_context_privacy_boundary.py 守卫；登记于 docs/aurora/rule_at_exceptions.md
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import COMMUNITY_GROUP_CONTEXT_REJECTIONS_TOTAL
from app.models.community import Group, GroupMember, GroupRole, SharedResource
from app.services.memory_retrieval_prefilter import Rejection

GROUP_CONTEXT_BOUNDARY_VERSION = "community-v3.s02.group_context.v1"

# ---------------------------------------------------------------------------
# 1. 封闭词表（单一事实源）
# ---------------------------------------------------------------------------


class SharedContextKind(StrEnum):
    """群 AI 上下文允许的类别（卡面：Goal/Action/Artifact 三族）。"""

    GOAL = "goal"
    ACTION = "action"
    ARTIFACT = "artifact"


SHARED_CONTEXT_KINDS: frozenset[str] = frozenset(kind.value for kind in SharedContextKind)

#: 既有分享真源 ``SharedResource`` 的载体列 → 群上下文类别（词表外载体永不进群上下文）。
SHARE_COLUMN_TO_KIND: Mapping[str, SharedContextKind] = {
    "plan_id": SharedContextKind.GOAL,
    "task_id": SharedContextKind.ACTION,
    "knowledge_node_id": SharedContextKind.ARTIFACT,
}

#: revoke 授权面：分享者本人，或群 OWNER/ADMIN（成员管理角色）。
_REVOKER_ROLES: frozenset[GroupRole] = frozenset({GroupRole.OWNER, GroupRole.ADMIN})


class GroupContextFilterDimension(StrEnum):
    """粗粒度筛选维度（metrics label；M-03/C-03 同型）。"""

    IDENTITY = "identity"
    TYPE = "type"
    SHARE = "share"
    LIFECYCLE = "lifecycle"


#: 固定求值顺序：首个失败维度独占拒绝归因（确定性指标归因；
#: ``test_filter_dimensions_order_pinned`` 钉死）。
GROUP_CONTEXT_FILTER_DIMENSIONS: tuple[GroupContextFilterDimension, ...] = (
    GroupContextFilterDimension.IDENTITY,
    GroupContextFilterDimension.TYPE,
    GroupContextFilterDimension.SHARE,
    GroupContextFilterDimension.LIFECYCLE,
)

REASON_NO_GROUP_SURFACE = "group_context:no_group_surface"
REASON_REQUESTER_NOT_MEMBER = "group_context:requester_not_member"
REASON_UNKNOWN_ITEM_TYPE = "group_context:unknown_item_type"
REASON_NOT_IN_ALLOWLIST = "group_context:not_in_allowlist"
REASON_OWNER_MISMATCH = "group_context:owner_mismatch"
REASON_SHARE_REVOKED = "group_context:share_revoked"
REASON_SHARER_LEFT_GROUP = "group_context:sharer_left_group"

#: 冻结 reason code 全集（新增必须 bump GROUP_CONTEXT_BOUNDARY_VERSION）。
GROUP_CONTEXT_REJECTION_REASONS: frozenset[str] = frozenset(
    {
        REASON_NO_GROUP_SURFACE,
        REASON_REQUESTER_NOT_MEMBER,
        REASON_UNKNOWN_ITEM_TYPE,
        REASON_NOT_IN_ALLOWLIST,
        REASON_OWNER_MISMATCH,
        REASON_SHARE_REVOKED,
        REASON_SHARER_LEFT_GROUP,
    }
)


class GroupContextPermissionError(PermissionError):
    """群上下文权限不满足（非成员/群不存在/撤销越权）。fail-closed。"""


# ---------------------------------------------------------------------------
# 2. 数据形状（纯数据；I/O 由服务层完成 —— M-03 build_retrieval_context 分层同型）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroupContextCandidate:
    """一个待进入群 prompt/tool 组装的上下文候选（纯描述符，任何输入路径可表达）。"""

    item_kind: str
    item_id: str
    owner_user_id: str
    source: str = ""


@dataclass(frozen=True)
class GroupSharedEntry:
    """allowlist 条目：一条**有效**的群分享（kind/item/owner/share 四元组绑定）。"""

    kind: str
    item_id: str
    owner_user_id: str
    share_id: str
    permission: str = "view"
    comment: str = ""
    shared_at: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.item_id)


@dataclass(frozen=True)
class InvalidGroupSharedEntry:
    """失效条目（撤销/分享者离群）：保留以支持陈旧上下文的精确失效归因。"""

    entry: GroupSharedEntry
    reason: str  # REASON_SHARE_REVOKED | REASON_SHARER_LEFT_GROUP

    @property
    def key(self) -> tuple[str, str]:
        return self.entry.key


@dataclass(frozen=True)
class GroupPromptAccessContext:
    """一次群 prompt/tool 组装的权限上下文（组装时点快照；纯数据）。"""

    group_id: str
    requester_id: str
    active_member_ids: frozenset[str]
    allowlist: frozenset[GroupSharedEntry] = field(default_factory=frozenset)
    invalid_entries: frozenset[InvalidGroupSharedEntry] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_id", str(self.group_id))
        object.__setattr__(self, "requester_id", str(self.requester_id))
        object.__setattr__(self, "active_member_ids", frozenset(str(m) for m in self.active_member_ids))
        object.__setattr__(self, "allowlist", frozenset(self.allowlist))
        object.__setattr__(self, "invalid_entries", frozenset(self.invalid_entries))


@dataclass(frozen=True)
class GroupContextFilterResult:
    """与 M-03 ``PrefilterResult`` / C-03 ``KnowledgeFilterResult`` 同字段集。"""

    allowed: list[Any]
    rejections: list[Rejection]
    input_count: int
    dimension_counts: dict[str, int]
    reason_counts: dict[str, int]

    @property
    def allowed_count(self) -> int:
        return len(self.allowed)

    def to_metric_payload(self) -> dict[str, Any]:
        return {
            "version": GROUP_CONTEXT_BOUNDARY_VERSION,
            "input_count": self.input_count,
            "allowed_count": self.allowed_count,
            "dimension_counts": dict(self.dimension_counts),
            "reason_counts": dict(self.reason_counts),
        }


# ---------------------------------------------------------------------------
# 3. 纯函数滤芯（无 I/O；任何调用方可守卫）
# ---------------------------------------------------------------------------


def _candidate_rejection(
    candidate: GroupContextCandidate, dimension: GroupContextFilterDimension, reason: str, detail: str
) -> Rejection:
    record_id = str(candidate.item_id or "<unknown>")
    source = f" (source={candidate.source})" if candidate.source else ""
    return Rejection(record_id=record_id, dimension=dimension.value, reason=reason, detail=f"{detail}{source}")


def _judge_candidate(candidate: GroupContextCandidate, ctx: GroupPromptAccessContext | None) -> Rejection | None:
    """单候选判定（维度固定顺序，首个失败维度独占归因）。None = 放行。"""
    if ctx is None:
        return _candidate_rejection(
            candidate,
            GroupContextFilterDimension.IDENTITY,
            REASON_NO_GROUP_SURFACE,
            "no group prompt access context; group assembly without the boundary is forbidden",
        )
    if ctx.requester_id not in ctx.active_member_ids:
        return _candidate_rejection(
            candidate,
            GroupContextFilterDimension.IDENTITY,
            REASON_REQUESTER_NOT_MEMBER,
            f"requester={ctx.requester_id} not an active member of group={ctx.group_id}",
        )
    kind = str(candidate.item_kind or "").strip().lower()
    if kind not in SHARED_CONTEXT_KINDS:
        return _candidate_rejection(
            candidate,
            GroupContextFilterDimension.TYPE,
            REASON_UNKNOWN_ITEM_TYPE,
            f"item_kind={candidate.item_kind!r} vocabulary={sorted(SHARED_CONTEXT_KINDS)}; "
            "private memory/profile families never enter group context",
        )
    entry = next((e for e in ctx.allowlist if e.key == (kind, str(candidate.item_id))), None)
    if entry is not None:
        if entry.owner_user_id != str(candidate.owner_user_id):
            return _candidate_rejection(
                candidate,
                GroupContextFilterDimension.SHARE,
                REASON_OWNER_MISMATCH,
                f"candidate owner={candidate.owner_user_id!r} does not bind share owner={entry.owner_user_id!r} "
                f"(share_id={entry.share_id})",
            )
        return None
    invalid = next((i for i in ctx.invalid_entries if i.key == (kind, str(candidate.item_id))), None)
    if invalid is not None:
        return _candidate_rejection(
            candidate, GroupContextFilterDimension.LIFECYCLE, invalid.reason, f"share_id={invalid.entry.share_id}"
        )
    return _candidate_rejection(
        candidate,
        GroupContextFilterDimension.SHARE,
        REASON_NOT_IN_ALLOWLIST,
        f"no active share of ({kind}, {candidate.item_id}) into group={ctx.group_id}",
    )


def filter_group_prompt_candidates(
    candidates: Iterable[GroupContextCandidate], ctx: GroupPromptAccessContext | None
) -> GroupContextFilterResult:
    """确定性砍除不可进入群 prompt/tool 组装的候选（L0 层，纯函数）。

    返回合法子集 + 逐候选拒绝归因 + 逐维度/逐原因计数（同步落 Prometheus，
    M-03/C-03 同型）。任何群面组装在把候选交给语义阶段前必须先过本滤芯。
    """
    allowed: list[GroupContextCandidate] = []
    rejections: list[Rejection] = []
    dimension_counts: dict[str, int] = {dim.value: 0 for dim in GROUP_CONTEXT_FILTER_DIMENSIONS}
    reason_counts: dict[str, int] = {}
    input_count = 0

    for candidate in candidates:
        input_count += 1
        rejection = _judge_candidate(candidate, ctx)
        if rejection is None:
            allowed.append(candidate)
            continue
        rejections.append(rejection)
        dimension_counts[rejection.dimension] = dimension_counts.get(rejection.dimension, 0) + 1
        reason_counts[rejection.reason] = reason_counts.get(rejection.reason, 0) + 1
        try:
            COMMUNITY_GROUP_CONTEXT_REJECTIONS_TOTAL.labels(
                dimension=rejection.dimension, reason=rejection.reason
            ).inc()
        except Exception:  # pragma: no cover - metrics must never break assembly
            pass

    result = GroupContextFilterResult(
        allowed=allowed,
        rejections=rejections,
        input_count=input_count,
        dimension_counts=dimension_counts,
        reason_counts=reason_counts,
    )
    if rejections:
        logger.info(
            "S-02 group-context boundary: input={} allowed={} rejected_dims={} rejected_reasons={}",
            input_count,
            result.allowed_count,
            {k: v for k, v in dimension_counts.items() if v},
            reason_counts,
        )
    return result


def group_tool_context_permits(
    ctx: GroupPromptAccessContext | None, *, item_kind: str, item_id: str, owner_user_id: str
) -> bool:
    """Aurora group tool context 布尔判定面（单候选便捷层；新代码批量用滤芯）。"""
    candidate = GroupContextCandidate(item_kind=item_kind, item_id=item_id, owner_user_id=owner_user_id)
    return _judge_candidate(candidate, ctx) is None


# ---------------------------------------------------------------------------
# 4. DB 侧：allowlist 快照解析 + revoke（真源 = SharedResource / GroupMember）
# ---------------------------------------------------------------------------


def _share_kind_and_ref(share: SharedResource) -> tuple[SharedContextKind, Any] | None:
    for column, kind in SHARE_COLUMN_TO_KIND.items():
        ref = getattr(share, column, None)
        if ref:
            return kind, ref
    return None


def _entry_from_share(share: SharedResource, kind: SharedContextKind, ref: Any) -> GroupSharedEntry:
    created_at = getattr(share, "created_at", None)
    return GroupSharedEntry(
        kind=kind.value,
        item_id=str(ref),
        owner_user_id=str(share.shared_by),
        share_id=str(share.id),
        permission=str(share.permission or "view"),
        comment=str(share.comment or ""),
        shared_at=created_at.isoformat() if created_at is not None else None,
    )


class GroupContextBoundaryService:
    """群上下文边界服务：allowlist 快照解析（组装时点）+ 撤销授权。"""

    @staticmethod
    async def build_prompt_access_context(
        db: AsyncSession, group_id: UUID | str, requester_id: UUID | str
    ) -> GroupPromptAccessContext:
        """解析组装时点的群权限快照。

        fail-closed：群不存在/已解散、请求者非活跃成员 →
        ``GroupContextPermissionError``。allowlist 只含「分享行未撤销 且 分享者
        仍是活跃成员」的条目；撤销行/分享者离群行进 ``invalid_entries`` 携带
        失效原因（时序内建：下一次组装即失效）。
        """
        group = await db.get(Group, group_id)
        if group is None or group.deleted_at is not None:
            raise GroupContextPermissionError(f"group {group_id} not found or dissolved")

        member_rows = (
            (
                await db.execute(
                    select(GroupMember).where(
                        GroupMember.group_id == group.id,
                        GroupMember.not_deleted_filter(),
                    )
                )
            )
            .scalars()
            .all()
        )
        member_ids = {str(row.user_id) for row in member_rows}
        if str(requester_id) not in member_ids:
            raise GroupContextPermissionError(f"requester {requester_id} is not an active member of group {group.id}")

        # 含软删行：revoke 后的陈旧上下文仍能拿到精确失效归因。
        share_rows = (
            (await db.execute(select(SharedResource).where(SharedResource.group_id == group.id))).scalars().all()
        )

        allowlist: set[GroupSharedEntry] = set()
        invalid_entries: set[InvalidGroupSharedEntry] = set()
        for share in share_rows:
            derived = _share_kind_and_ref(share)
            if derived is None:
                continue  # 词表外载体（seed/cognitive/curiosity/prism 族）永不进群上下文
            kind, ref = derived
            entry = _entry_from_share(share, kind, ref)
            if share.deleted_at is not None:
                invalid_entries.add(InvalidGroupSharedEntry(entry=entry, reason=REASON_SHARE_REVOKED))
            elif str(share.shared_by) not in member_ids:
                invalid_entries.add(InvalidGroupSharedEntry(entry=entry, reason=REASON_SHARER_LEFT_GROUP))
            else:
                allowlist.add(entry)

        return GroupPromptAccessContext(
            group_id=str(group.id),
            requester_id=str(requester_id),
            active_member_ids=frozenset(member_ids),
            allowlist=frozenset(allowlist),
            invalid_entries=frozenset(invalid_entries),
        )

    @staticmethod
    async def resolve_prompt_context(
        db: AsyncSession, group_id: UUID | str, requester_id: UUID | str
    ) -> dict[str, Any]:
        """Aurora group prompt/tool 上下文的**唯一合法组装入口**。

        只读群 permission 面（allowlist），**绝不触碰**私人 memory/profile 检索
        面。payload 形状冻结（``test_allowlisted_shares_enter_group_prompt_context``
        钉死 entry 键集）：仅 share 元数据 + 类别 + 条目引用，零私人字段。
        """
        ctx = await GroupContextBoundaryService.build_prompt_access_context(db, group_id, requester_id)
        entries = [
            {
                "share_id": entry.share_id,
                "kind": entry.kind,
                "item_id": entry.item_id,
                "permission": entry.permission,
                "comment": entry.comment,
                "shared_by": entry.owner_user_id,
                "shared_at": entry.shared_at,
            }
            for entry in sorted(ctx.allowlist, key=lambda e: (e.kind, e.share_id))
        ]
        return {
            "schema_version": GROUP_CONTEXT_BOUNDARY_VERSION,
            "group_id": ctx.group_id,
            "requester_id": ctx.requester_id,
            "entry_count": len(entries),
            "entries": entries,
        }

    @staticmethod
    async def revoke_share(db: AsyncSession, share_id: UUID | str, revoked_by: UUID | str) -> SharedResource:
        """撤销一条群分享（软删 = revoke，社群既有惯例）。

        授权：分享者本人，或该群 OWNER/ADMIN。撤销后下一次组装即不含该条目
        （快照层时序内建），陈旧上下文由滤芯层以 ``share_revoked`` 归因拦截。
        """
        share = await db.get(SharedResource, share_id)
        if share is None or share.deleted_at is not None:
            raise LookupError(f"shared resource {share_id} not found or already revoked")

        if str(revoked_by) != str(share.shared_by):
            if share.group_id is None:
                raise GroupContextPermissionError("revoker is neither the sharer nor a group admin")
            member_row = (
                await db.execute(
                    select(GroupMember).where(
                        GroupMember.group_id == share.group_id,
                        GroupMember.user_id == revoked_by,
                        GroupMember.not_deleted_filter(),
                    )
                )
            ).scalar_one_or_none()
            if member_row is None or member_row.role not in _REVOKER_ROLES:
                raise GroupContextPermissionError("revoker is neither the sharer nor a group owner/admin")

        share.soft_delete()
        await db.flush()
        logger.info(
            "S-02 group-context share revoked: share_id={} group={} revoked_by={}",
            share.id,
            share.group_id,
            revoked_by,
        )
        return share


__all__ = [
    "GROUP_CONTEXT_BOUNDARY_VERSION",
    "GROUP_CONTEXT_FILTER_DIMENSIONS",
    "GROUP_CONTEXT_REJECTION_REASONS",
    "SHARED_CONTEXT_KINDS",
    "SHARE_COLUMN_TO_KIND",
    "GroupContextBoundaryService",
    "GroupContextCandidate",
    "GroupContextFilterDimension",
    "GroupContextFilterResult",
    "GroupContextPermissionError",
    "GroupPromptAccessContext",
    "GroupSharedEntry",
    "InvalidGroupSharedEntry",
    "SharedContextKind",
    "filter_group_prompt_candidates",
    "group_tool_context_permits",
]
