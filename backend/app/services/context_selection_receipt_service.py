"""V4-I06 · ContextSelectionReceipt 服务层——落库、读取、来源验证。

三件事（卡 V4-I06 要点）：

1. **落库与读面**：``record_receipt``（ContextPackBuilder.build 装配完成后落账，
   幂等键 = ``receipt_id`` 唯一约束，同轮重算不重复计数）；``latest_receipt`` 供
   U03「我的理解」与移动端理解条目消费。
2. **来源验证（E4 双重校验，不可悬空）**：``verify_receipt_sources`` 把回执的
   ``basis_refs``/selected 候选 ref 逐条 join **真实存储条目**：
   - 第一重：scheme ∈ ``ACTION_SOURCE_REF_SCHEMES`` 封闭集（契约层，本模块复用
     ``app.core.context_selection_receipt.ref_in_closed_schemes``）；
   - 第二重：按 scheme 解析到存储真源（episodic_memories / memory_preferences /
     memory_goals / plans / tasks / files），**且属主必须是当前授权用户**（I3
     跨对象拒绝——他人对象与不存在对象同样判 ``unresolved``，不区分泄漏）。
   解析成功给出存储行的定位锚（kind/id/存在性/软删状态）；失败一律
   ``resolution="unresolved"``——**来源不可定位时明确 unknown，不编时间/quote**
   （卡验收第 1 条）。
3. **删除后旧 receipt 更新（读时验证语义）**：回执行不就地改写（权威记录只读）；
   每次 读面消费都现场 join 存储验证——被删/纠正/越权的来源在验证结果中如实
   反映（``deleted_at`` 非空 → ``unresolved(deleted)``），用户看到的 scope 与
   后台一致（卡验收第 2 条）。

隐私纪律：验证结果 metadata-only（kind/id/resolution/软删标记），**永不携带正文、
永不构造 quote/时间**（卡验收"不编时间/quote"）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_selection_receipt import (
    CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION,
    ContextSelectionReceipt,
    context_selection_receipt_from_payload,
)
from app.models.context_selection_receipt import ContextSelectionReceiptRow

#: 验证结果的封闭词表（本模块输出面）。
SOURCE_RESOLUTION_RESOLVED = "resolved"
SOURCE_RESOLUTION_UNRESOLVED = "unresolved"
SOURCE_RESOLUTIONS: frozenset[str] = frozenset({SOURCE_RESOLUTION_RESOLVED, SOURCE_RESOLUTION_UNRESOLVED})

#: unresolved 的封闭细分（metadata-only；unknown = 存储中不可定位——含不存在、
#: 已删除、scheme 集合外、跨用户，**统一 unknown 不区分泄漏**，I3 纪律）。
UNRESOLVED_UNKNOWN = "unknown"
UNRESOLVED_DELETED = "deleted"


class SourceVerificationEntry(dict[str, Any]):
    """单条 ref 的验证结果（dict 形，metadata-only）。"""


def _entry(ref: str, *, resolution: str, status_code: str, detail: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ref": ref,
        "resolution": resolution,
        "status_code": status_code,
    }
    if detail:
        payload["detail"] = detail
    return payload


async def verify_receipt_sources(
    db: AsyncSession, user_id: UUID | str, receipt: ContextSelectionReceipt
) -> list[dict[str, Any]]:
    """回执依据面 → 逐条 join 存储验证（E4 双重校验）。

    验证对象 = selected 候选 ∪ why_now.basis_refs（呈现层可引用的全集，合同 §7
    「结论必须可溯源到 selected ref」）。rejected/unavailable 候选不进验证面
    （debug 面才可见拒用摘要，且正文不得引用它们）。
    """
    refs: list[str] = []
    seen: set[str] = set()
    for ref in receipt.selected_refs:
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    if receipt.why_now is not None:
        for ref in receipt.why_now.basis_refs:
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    verified: list[dict[str, Any]] = []
    for ref in refs:
        verified.append(await verify_source_ref(db, user_id, ref))
    return verified


async def verify_source_ref(db: AsyncSession, user_id: UUID | str, ref: str) -> dict[str, Any]:
    """单条 ref 的存储验证（第一重 scheme 门 + 第二重 join 门，都过才 resolved）。

    scheme → 真源映射（当前仓库已存在的存储权威，**只读**）：
    - ``memory://episodic/<id>`` → episodic_memories
    - ``memory://preference/<pref_key>`` → memory_preferences（pref_key 字符串键）
    - ``memory://goal/<id>`` → memory_goals
    - ``plan://<id>`` → plans；``task://<id>`` / ``goal://<id>`` → tasks / goals 表
    - ``document://<file_id>`` → files
    - ``user_state://`` / ``profile://`` / ``chat://`` / ``decision://`` / ``run://``：
      非单行存储面（投影/事件域），本轮装配未作为依据产生 → 判 unknown（诚实，
      不伪造可点定位）。后续卡需要时在此登记各自真源。
    """
    from app.core.context_selection_receipt import parse_ref_scheme

    scheme = parse_ref_scheme(ref)
    if scheme is None:
        return _entry(
            ref, resolution=SOURCE_RESOLUTION_UNRESOLVED, status_code=UNRESOLVED_UNKNOWN, detail="malformed ref"
        )
    path = ref.split("://", 1)[1]
    try:
        resolved: dict[str, Any] | None = await _resolve_scheme(db, user_id, scheme, path)
    except Exception as exc:  # noqa: BLE001 - 验证失败不炸读面，如实 unknown
        logger.warning("I06 source verify failed ref={}: {}", ref, exc)
        resolved = None
    if resolved is None:
        return _entry(ref, resolution=SOURCE_RESOLUTION_UNRESOLVED, status_code=UNRESOLVED_UNKNOWN)
    return resolved


def _split_memory_path(path: str) -> tuple[str, str]:
    kind, _, item_id = path.partition("/")
    return kind.strip(), item_id.strip()


async def _resolve_scheme(db: AsyncSession, user_id: UUID | str, scheme: str, path: str) -> dict[str, Any] | None:
    """第二重门：join 真源 + 属主校验。返回 resolved entry 或 None（unknown）。"""
    uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))

    if scheme == "memory":
        kind, item_id = _split_memory_path(path)
        if kind == "episodic":
            return await _resolve_row(
                db,
                ref=f"memory://episodic/{item_id}",
                user_id=uid,
                model=_model("EpisodicMemory", "app.models.memory"),
                row_id=item_id,
                kind="memory_episodic",
            )
        if kind == "preference":
            from app.models.memory import MemoryPreference

            result = await db.execute(
                select(MemoryPreference).where(
                    MemoryPreference.user_id == uid,
                    MemoryPreference.pref_key == item_id,
                    MemoryPreference.deleted_at.is_(None),
                )
            )
            row = result.scalar_one_or_none()
            return _row_entry(f"memory://preference/{item_id}", "memory_preference", row)
        if kind == "goal":
            return await _resolve_row(
                db,
                ref=f"memory://goal/{item_id}",
                user_id=uid,
                model=_model("MemoryGoal", "app.models.memory"),
                row_id=item_id,
                kind="memory_goal",
            )
        return None
    if scheme == "plan":
        return await _resolve_row(
            db, ref=f"plan://{path}", user_id=uid, model=_model("Plan", "app.models.plan"), row_id=path, kind="plan"
        )
    if scheme == "task":
        return await _resolve_row(
            db, ref=f"task://{path}", user_id=uid, model=_model("Task", "app.models.task"), row_id=path, kind="task"
        )
    if scheme == "goal":
        return await _resolve_row(
            db, ref=f"goal://{path}", user_id=uid, model=_model("Goal", "app.models.goal"), row_id=path, kind="goal"
        )
    if scheme == "document":
        return await _resolve_row(
            db,
            ref=f"document://{path}",
            user_id=uid,
            model=_model("StoredFile", "app.models.file_storage"),
            row_id=path,
            kind="document",
        )
    # user_state / profile / chat / decision / run：非单行存储投影面 → unknown。
    return None


def _model(name: str, module: str) -> Any:
    import importlib

    return getattr(importlib.import_module(module), name)


async def _resolve_row(
    db: AsyncSession,
    *,
    ref: str,
    user_id: UUID,
    model: Any,
    row_id: str,
    kind: str,
) -> dict[str, Any] | None:
    """UUID 主键行的 join 验证：属主过滤 + 软删检测。非法 UUID → unknown（不炸）。"""
    try:
        row_uuid = UUID(row_id)
    except (ValueError, AttributeError):
        return None
    result = await db.execute(select(model).where(model.id == row_uuid, model.user_id == user_id))
    row = result.scalar_one_or_none()
    return _row_entry(ref, kind, row)


def _row_entry(ref: str, kind: str, row: Any) -> dict[str, Any]:
    """存储行 → 验证 entry。行不存在/跨用户 → unknown（统一，不区分泄漏，I3）。"""
    if row is None:
        return _entry(ref, resolution=SOURCE_RESOLUTION_UNRESOLVED, status_code=UNRESOLVED_UNKNOWN)
    deleted_at = getattr(row, "deleted_at", None)
    if isinstance(deleted_at, datetime) or deleted_at is not None:
        return _entry(
            ref,
            resolution=SOURCE_RESOLUTION_UNRESOLVED,
            status_code=UNRESOLVED_DELETED,
            detail="source deleted after receipt (read-time verification)",
        )
    return _entry(ref, resolution=SOURCE_RESOLUTION_RESOLVED, status_code="ok", detail=kind)


# ---------------------------------------------------------------------------
# 落库 / 读取
# ---------------------------------------------------------------------------


async def record_receipt(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    receipt: ContextSelectionReceipt,
    pack_run_id: UUID | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> str | None:
    """回执落账（幂等：receipt_id 唯一约束，冲突跳过——同轮重算不重复计数）。

    落库前过 ``validate_contract``：违例回执**不落库**（fail-closed——带契约
    违例的记录进库即第二真值污染），返回 None 并记 WARN。
    """
    violations = receipt.validate_contract()
    if violations:
        logger.warning(
            "I06 receipt contract violations, not persisted: id={} violations={}",
            receipt.receipt_id,
            violations,
        )
        return None
    uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    existing = await db.execute(
        select(ContextSelectionReceiptRow.id).where(ContextSelectionReceiptRow.receipt_id == receipt.receipt_id)
    )
    if existing.scalar_one_or_none() is not None:
        return receipt.receipt_id
    row = ContextSelectionReceiptRow(
        user_id=uid,
        receipt_id=receipt.receipt_id,
        schema_version=receipt.schema_version,
        selection_role=receipt.selection_role,
        decision_id=receipt.decision_id,
        memory_epoch=int(receipt.input_versions.memory_epoch or 0),
        selector_version=receipt.input_versions.selector_version,
        input_versions=receipt.input_versions.model_dump(mode="json"),
        candidates=[candidate.model_dump(mode="json") for candidate in receipt.candidates],
        budget=receipt.budget.model_dump(mode="json"),
        why_now=(receipt.why_now.model_dump(mode="json") if receipt.why_now is not None else None),
        pack_run_id=pack_run_id,
        request_id=request_id,
        trace_id=trace_id,
    )
    db.add(row)
    await db.commit()
    return receipt.receipt_id


async def latest_receipt(
    db: AsyncSession, user_id: UUID | str
) -> tuple[ContextSelectionReceipt | None, dict[str, Any] | None]:
    """最近一条回执 → (receipt, row_payload)。读侧版本门在
    ``context_selection_receipt_from_payload``（schema 集合外/结构损坏 → None+违例）。"""
    uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    result = await db.execute(
        select(ContextSelectionReceiptRow)
        .where(ContextSelectionReceiptRow.user_id == uid, ContextSelectionReceiptRow.deleted_at.is_(None))
        .order_by(ContextSelectionReceiptRow.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None, None
    payload: dict[str, Any] = {
        "schema_version": row.schema_version,
        "receipt_id": row.receipt_id,
        "selection_role": row.selection_role,
        "decision_id": row.decision_id,
        "input_versions": row.input_versions if isinstance(row.input_versions, dict) else {},
        "candidates": list(row.candidates or []) if isinstance(row.candidates, list) else [],
        "budget": row.budget if isinstance(row.budget, dict) else {},
        "why_now": row.why_now,
    }
    receipt, violations = context_selection_receipt_from_payload(payload)
    return receipt, {
        "row": {"created_at": row.created_at.isoformat() if row.created_at else None},
        "violations": violations,
    }


def schema_version_constant() -> str:
    """读面暴露用常量（避免 API 层散落字符串字面量）。"""
    return CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION


__all__ = [
    "SOURCE_RESOLUTIONS",
    "SOURCE_RESOLUTION_RESOLVED",
    "SOURCE_RESOLUTION_UNRESOLVED",
    "UNRESOLVED_DELETED",
    "UNRESOLVED_UNKNOWN",
    "latest_receipt",
    "record_receipt",
    "verify_receipt_sources",
    "verify_source_ref",
]
