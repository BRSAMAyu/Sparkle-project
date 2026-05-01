"""Dormant injector — assembles the 5-item injection set for task assistant.

Cold-start fallback: when a data source is unavailable, the item gets
``available=False`` and the session starts with ``UXIntent.ROUTINE`` and
``AuroraPresenceLevel.AMBIENT``.

Strong-signal refresh rules: only refresh the cached injection set when
one of these signals fires:
  1. FocusContract version bump
  2. TaskGuidance content change
  3. New TransitionDecisionRecord for this user
  4. InsightClaim status change (open → confirmed/refuted)
  5. ProbeOutcome with significant confidence adjustment

Otherwise reuse the cached sidecar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.aurora.schemas.enums import AuroraPresenceLevel, UXIntent
from app.task_assistant.schemas import (
    DormantInjection,
    DormantInjectionItem,
    DormantInjectionKind,
)
from app.task_assistant.store import CacheBackedDormantStore


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class DormantInjector:
    """Assemble the approved 5-item dormant injection set."""

    def __init__(self, store: CacheBackedDormantStore | None = None) -> None:
        self._store = store or CacheBackedDormantStore()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def inject(
        self,
        task_id: UUID,
        user_id: UUID,
        *,
        force_refresh: bool = False,
        prior_outputs: dict[str, Any] | None = None,
    ) -> DormantInjection:
        """Build (or reuse) the dormant injection set for a task session.

        Parameters
        ----------
        task_id, user_id:
            Identifies the task + user.
        force_refresh:
            True when a strong-signal trigger fired.
        prior_outputs:
            Aurora outputs from inline/nearline that may carry fresh data.
        """
        if not force_refresh:
            cached = await self._store.get_injection(task_id, user_id)
            if cached is not None:
                return cached

        po = prior_outputs or {}
        items = await self._build_items(user_id, task_id, po)

        injection = DormantInjection(
            task_id=task_id,
            user_id=user_id,
            items=items,
            ux_intent=self._resolve_ux_intent(items),
            aurora_presence=self._resolve_presence(items),
            generated_by="dormant_injector_v1",
            created_at=_utcnow(),
        )
        await self._store.save_injection(injection)
        return injection

    # ------------------------------------------------------------------
    # 5-item builders
    # ------------------------------------------------------------------

    async def _build_items(
        self,
        user_id: UUID,
        task_id: UUID,
        prior_outputs: dict[str, Any],
    ) -> list[DormantInjectionItem]:
        return [
            await self._item_focus_contract(user_id, prior_outputs),
            await self._item_task_guidance(task_id, user_id, prior_outputs),
            await self._item_tdr_intent_presence(user_id, prior_outputs),
            await self._item_insight_claim(user_id, prior_outputs),
            await self._item_probe_outcome(user_id, prior_outputs),
        ]

    # 1. FocusContract summary
    async def _item_focus_contract(
        self, user_id: UUID, po: dict,
    ) -> DormantInjectionItem:
        fc = po.get("focus_contract")
        if fc and isinstance(fc, dict) and fc.get("id"):
            return DormantInjectionItem(
                kind=DormantInjectionKind.FOCUS_CONTRACT_SUMMARY,
                available=True,
                payload={
                    "focus_description": fc.get("focus_description", ""),
                    "desire_hypothesis": fc.get("desire_hypothesis"),
                    "active_node": fc.get("active_node", ""),
                },
                source_ref=f"FocusContract:{fc['id']}",
            )
        return DormantInjectionItem(
            kind=DormantInjectionKind.FOCUS_CONTRACT_SUMMARY,
            available=False,
        )

    # 2. TaskGuidance AI version, or human-summary fallback
    async def _item_task_guidance(
        self, task_id: UUID, user_id: UUID, po: dict,
    ) -> DormantInjectionItem:
        tg = po.get("task_guidance")
        if tg and isinstance(tg, dict) and tg.get("content"):
            return DormantInjectionItem(
                kind=DormantInjectionKind.TASK_GUIDANCE_AI_OR_FALLBACK,
                available=True,
                payload={"content": tg["content"], "audience": tg.get("audience", "ai")},
                source_ref=f"TaskGuidance:{tg.get('id', 'unknown')}",
            )
        # Try to load from TaskGuidance sidecar store
        try:
            from app.task_guidance.schemas import TaskGuidanceAudience
            from app.task_guidance.store import CacheBackedTaskGuidanceStore

            guidance_store = CacheBackedTaskGuidanceStore()
            guidance = await guidance_store.get_for_task(task_id, TaskGuidanceAudience.AI)
            if guidance is None:
                guidance = await guidance_store.get_for_task(task_id, TaskGuidanceAudience.HUMAN)
            if guidance is not None:
                return DormantInjectionItem(
                    kind=DormantInjectionKind.TASK_GUIDANCE_AI_OR_FALLBACK,
                    available=True,
                    payload={"content": guidance.content, "audience": guidance.audience.value},
                    source_ref=f"TaskGuidance:{guidance.id}",
                )
        except Exception as exc:
            logger.debug(f"WS-D: task guidance fallback lookup skipped: {exc}")

        return DormantInjectionItem(
            kind=DormantInjectionKind.TASK_GUIDANCE_AI_OR_FALLBACK,
            available=False,
        )

    # 3. Latest TransitionDecisionRecord UXIntent + AuroraPresenceLevel
    async def _item_tdr_intent_presence(
        self, user_id: UUID, po: dict,
    ) -> DormantInjectionItem:
        tdr = po.get("transition_decision_record")
        if tdr and isinstance(tdr, dict):
            return DormantInjectionItem(
                kind=DormantInjectionKind.LATEST_TDR_INTENT_PRESENCE,
                available=True,
                payload={
                    "ux_intent": tdr.get("ux_intent", UXIntent.ROUTINE.value),
                    "aurora_presence": tdr.get("aurora_presence", AuroraPresenceLevel.AMBIENT.value),
                },
                source_ref=f"TDR:{tdr.get('id', 'unknown')}",
            )
        return DormantInjectionItem(
            kind=DormantInjectionKind.LATEST_TDR_INTENT_PRESENCE,
            available=False,
        )

    # 4. Projection-allowed active InsightClaim
    async def _item_insight_claim(
        self, user_id: UUID, po: dict,
    ) -> DormantInjectionItem:
        claim = po.get("insight_claim")
        if claim and isinstance(claim, dict) and claim.get("content"):
            return DormantInjectionItem(
                kind=DormantInjectionKind.PROJECTION_ALLOWED_INSIGHT_CLAIM,
                available=True,
                payload={
                    "claim_type": claim.get("claim_type", ""),
                    "content": claim["content"],
                    "confidence": claim.get("confidence", 0.0),
                },
                source_ref=f"InsightClaim:{claim.get('id', 'unknown')}",
            )
        return DormantInjectionItem(
            kind=DormantInjectionKind.PROJECTION_ALLOWED_INSIGHT_CLAIM,
            available=False,
        )

    # 5. Recent relevant ProbeOutcome
    async def _item_probe_outcome(
        self, user_id: UUID, po: dict,
    ) -> DormantInjectionItem:
        probe = po.get("probe_outcome")
        if probe and isinstance(probe, dict):
            return DormantInjectionItem(
                kind=DormantInjectionKind.RECENT_PROBE_OUTCOME,
                available=True,
                payload={
                    "probe_type": probe.get("probe_type", ""),
                    "result": probe.get("result", ""),
                    "confidence_adjustment": probe.get("confidence_adjustment", 0.0),
                },
                source_ref=f"ProbeOutcome:{probe.get('id', 'unknown')}",
            )
        return DormantInjectionItem(
            kind=DormantInjectionKind.RECENT_PROBE_OUTCOME,
            available=False,
        )

    # ------------------------------------------------------------------
    # Cold-start resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_ux_intent(items: list[DormantInjectionItem]) -> str:
        """Only cold-start fallback values: UXIntent.ROUTINE."""
        return UXIntent.ROUTINE.value

    @staticmethod
    def _resolve_presence(items: list[DormantInjectionItem]) -> str:
        """Only cold-start fallback values: AuroraPresenceLevel.AMBIENT."""
        return AuroraPresenceLevel.AMBIENT.value

    # ------------------------------------------------------------------
    # Strong-signal refresh rules
    # ------------------------------------------------------------------

    @staticmethod
    def should_refresh(trigger: str) -> bool:
        """Return True only for approved strong signals."""
        return trigger in {
            "focus_contract_version_bump",
            "task_guidance_content_change",
            "new_transition_decision_record",
            "insight_claim_status_change",
            "probe_outcome_significant_adjustment",
        }
