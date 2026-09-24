"""A-06 · Aurora Receipt Service —— Why-this 回执四动作的服务层委托。

分层纪律：handler（api/v1/aurora_receipts.py）只做协议适配；动作的**真实
生效**全部委托既有权威真源，本服务零新写路径、零新表、零新迁移：

- ``not_relevant``  → ``MemoryService.record_memory_reference_outcome(denied)``
  （引用层降噪 + 飞轮负样本；understanding_dimensions utility 的既有输入）；
- ``wrong``         → 带更正内容走 ``MemoryProvenanceService.update_item``
  （M-01 supersede 法则：episodic 建 user_confirmed 替代行 + 旧行
  superseded_by_id；preference 版本链推进；goal 字段白名单）；不带内容走
  ``MemoryService.apply_correction(lower_confidence)``（降置信 + 审计行）；
- ``change_scope``  → ``MemoryProvenanceService.update_scope(pause)``
  （archived_at 暂停召回，可恢复；USER_UPDATE invalidation）；
- ``delete``        → ``MemoryProvenanceService.revoke_item``
  （M-07 撤销链：epoch bump + memory.invalidated 事件 + 缓存 DEL + 三面不可见）。

所有权/隔离/幂等守卫全部由被委托服务既有实现承担：跨用户 id 与缺失 id 一律
``MemoryProvenanceNotFoundError``（404，无存在性泄漏）；非 ACTIVE 状态的
scope/edit 拒绝为 ``MemoryProvenanceConflictError``（409）；动作词表外拒绝
（422）。audit reason 统一携带 ``aurora_receipt:<action>`` 前缀——回执链路的
纠偏在既有审计面（memory_corrections 行）可追溯。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.aurora.calibration_receipt import receipt_action_plan
from app.core.cache import cache_service
from app.services.memory_provenance_service import (
    MemoryProvenanceNotFoundError,
    MemoryProvenanceService,
)
from app.services.memory_service import MemoryService

#: 回执动作支持的 memory kind（与既有权威一致：provenance/apply_correction 的 kind 域）。
SUPPORTED_MEMORY_KINDS: frozenset[str] = frozenset({"episodic", "preference", "goal"})


class AuroraReceiptService:
    def __init__(self, db: Any, redis: Any | None = None):
        self.db = db
        self.redis = redis or cache_service.redis

    async def respond(
        self,
        *,
        user_id: UUID,
        memory_type: str,
        memory_id: UUID,
        action: str,
        corrected_content: str | None = None,
        reason: str | None = None,
        response_id: str | None = None,
    ) -> dict[str, Any]:
        """执行一次回执纠偏动作（委托既有权威；返回诚实结果负载）。"""
        kind = str(memory_type or "").strip().lower()
        if kind not in SUPPORTED_MEMORY_KINDS:
            raise ValueError(f"Unsupported memory kind: {memory_type!r}")
        plan = receipt_action_plan(action=action, corrected_content=corrected_content)
        if not plan:
            raise ValueError(f"Unsupported receipt action: {action!r}")

        audit_reason = f"aurora_receipt:{plan['action']}"
        if reason:
            audit_reason = f"{audit_reason}; {str(reason)[:300]}"
        if response_id:
            audit_reason = f"{audit_reason}; response_id={str(response_id)[:100]}"

        memory_service = MemoryService(self.db, self.redis)
        provenance = MemoryProvenanceService(self.db, self.redis)

        if plan["action"] == "not_relevant":
            result = await memory_service.record_memory_reference_outcome(
                kind=kind,
                memory_id=memory_id,
                user_id=user_id,
                outcome="denied",
                response_id=str(response_id) if response_id else None,
                reason=audit_reason,
            )
            if result is None:
                raise MemoryProvenanceNotFoundError(f"{kind} memory {memory_id} not found")
            return {
                "status": "ok",
                "action": "not_relevant",
                "authority": plan["authority"],
                "memory_reference_outcome": result,
            }

        if plan["action"] == "wrong":
            if plan["mode"] == "supersede":
                content = str(corrected_content or "").strip()
                await provenance.update_item(
                    user_id,
                    kind,
                    memory_id,
                    content=content if kind in {"episodic", "preference"} else None,
                    pref_value={"value": content} if kind == "preference" else None,
                    title=content if kind == "goal" else None,
                    reason=audit_reason,
                )
                return {
                    "status": "ok",
                    "action": "wrong",
                    "mode": "supersede",
                    "authority": plan["authority"],
                }
            record = await memory_service.apply_correction(
                kind,
                memory_id,
                user_id,
                "lower_confidence",
                audit_reason,
            )
            if record is None:
                raise MemoryProvenanceNotFoundError(f"{kind} memory {memory_id} not found")
            return {
                "status": "ok",
                "action": "wrong",
                "mode": "lower_confidence",
                "authority": plan["authority"],
            }

        if plan["action"] == "change_scope":
            return {
                **await provenance.update_scope(
                    user_id,
                    kind,
                    memory_id,
                    action="pause",
                    reason=audit_reason,
                ),
                "status": "ok",
                "action": "change_scope",
                "authority": plan["authority"],
            }

        # delete
        return {
            **await provenance.revoke_item(user_id, kind, memory_id, reason=audit_reason),
            "status": "ok",
            "action": "delete",
            "authority": plan["authority"],
        }
