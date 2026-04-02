"""
RiskRegisterService — Tracks detected risks and mitigation outcomes.

Each risk register is stored as a PlanningArtifact(RISK_REGISTER) with a risks
array. Behavior patterns and plan health signals can auto-register risks,
and the outcome verifier updates their status based on intervention effectiveness.

Phase 3 of the Card Protocol.
"""
from __future__ import annotations

from copy import deepcopy
import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import ArtifactType
from app.services.planning_artifact_service import PlanningArtifactService
from app.core.event_bus import EventBus


class RiskRegisterService:
    """Tracks risks and mitigation outcomes in RISK_REGISTER artifacts."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)

    async def register_risk(
        self,
        *,
        plan_card_id: uuid.UUID,
        description: str,
        likelihood: str = "medium",
        impact_level: str = "medium",
        mitigation_strategy: str = "",
        trigger_threshold: str = "",
        source_pattern: str | None = None,
        evidence: dict | None = None,
    ) -> dict | None:
        """Add a risk entry to the plan's RISK_REGISTER artifact.

        Returns the risk entry dict or None on failure.
        """
        risk_id = str(uuid.uuid4())
        risk_entry = {
            "id": risk_id,
            "description": description,
            "likelihood": likelihood,
            "impact_level": impact_level,
            "mitigation_strategy": mitigation_strategy,
            "trigger_threshold": trigger_threshold,
            "source_pattern": source_pattern or "",
            "status": "ACTIVE",
            "detected_at": datetime.utcnow().isoformat(),
            "mitigated_at": None,
            "evidence": evidence or {},
            "occurrence_count": 1,
        }

        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.RISK_REGISTER
        )

        if artifact:
            payload = deepcopy(artifact.payload or {})
            risks = list(payload.get("risks", []))
            # Check for duplicate description
            for existing in risks:
                if (
                    existing.get("description") == description
                    and existing.get("status") == "ACTIVE"
                ):
                    # Increment occurrence count instead of duplicating
                    existing["occurrence_count"] = existing.get("occurrence_count", 1) + 1
                    if evidence:
                        existing_evidence = existing.get("evidence", {})
                        existing_evidence.update(evidence)
                        existing["evidence"] = existing_evidence
                    payload["risks"] = risks
                    await self.artifact_service.update_payload(artifact.id, payload)
                    return existing
            risks.append(risk_entry)
            payload["risks"] = risks
            await self.artifact_service.update_payload(artifact.id, payload)
        else:
            await self.artifact_service.get_or_create_approved(
                plan_card_id=plan_card_id,
                artifact_type=ArtifactType.RISK_REGISTER,
                default_payload={"risks": [risk_entry]},
                created_by_agent="risk_detector",
            )

        logger.info(
            "RiskRegisterService: registered risk '{}' for plan {}",
            description[:50],
            plan_card_id,
        )
        return risk_entry

    async def update_status(
        self,
        plan_card_id: uuid.UUID,
        risk_id: str,
        status: str,
        evidence: dict | None = None,
    ) -> bool:
        """Update a risk's status (ACTIVE -> MITIGATED / ACCEPTED / CLOSED)."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.RISK_REGISTER
        )
        if not artifact:
            return False

        payload = deepcopy(artifact.payload or {})
        risks = list(payload.get("risks", []))
        found = False
        for risk in risks:
            if risk.get("id") == risk_id:
                risk["status"] = status
                if status == "MITIGATED":
                    risk["mitigated_at"] = datetime.utcnow().isoformat()
                if evidence:
                    existing = risk.get("evidence", {})
                    existing.update(evidence)
                    risk["evidence"] = existing
                found = True
                break

        if not found:
            return False

        payload["risks"] = risks
        await self.artifact_service.update_payload(artifact.id, payload)

        logger.info(
            "RiskRegisterService: risk {} -> {} for plan {}",
            risk_id[:8],
            status,
            plan_card_id,
        )
        return True

    async def get_active_risks(self, plan_card_id: uuid.UUID) -> list[dict]:
        """Get currently active risks for a plan."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.RISK_REGISTER
        )
        if not artifact:
            return []
        risks = list(deepcopy((artifact.payload or {}).get("risks", [])))
        return [r for r in risks if r.get("status") == "ACTIVE"]

    async def get_all_risks(
        self, plan_card_id: uuid.UUID, limit: int = 50
    ) -> list[dict]:
        """Get all risks for a plan."""
        artifact = await self.artifact_service.get_approved(
            plan_card_id, ArtifactType.RISK_REGISTER
        )
        if not artifact:
            return []
        risks = list(deepcopy((artifact.payload or {}).get("risks", [])))
        return risks[-limit:]

    async def auto_register_from_pattern(
        self,
        *,
        user_id: uuid.UUID,
        plan_card_id: uuid.UUID,
        pattern_name: str,
        confidence: float,
        evidence: dict | None = None,
    ) -> dict | None:
        """Auto-register a risk from a detected behavior pattern."""
        risk_mapping = {
            "procrastination": {
                "description": "User shows procrastination pattern — deferring tasks repeatedly",
                "likelihood": "high",
                "impact_level": "medium",
                "mitigation_strategy": "Reduce task scope, add micro-restart prompts",
                "trigger_threshold": "3+ consecutive deferred tasks",
            },
            "avoidance": {
                "description": "User avoids specific task types or topics",
                "likelihood": "high",
                "impact_level": "high",
                "mitigation_strategy": "Break avoided tasks into smaller steps, provide gentle encouragement",
                "trigger_threshold": "Repeated abandonment of similar tasks",
            },
            "overload": {
                "description": "User is overloaded — too many concurrent tasks or time pressure",
                "likelihood": "high",
                "impact_level": "high",
                "mitigation_strategy": "Reduce concurrency, extend timelines, prioritize critical tasks",
                "trigger_threshold": "4+ active tasks or consecutive time overruns",
            },
            "perfectionism": {
                "description": "User shows perfectionism — excessive time on single tasks",
                "likelihood": "medium",
                "impact_level": "medium",
                "mitigation_strategy": "Set time caps, emphasize progress over perfection",
                "trigger_threshold": "Repeated tasks exceeding estimate by 2x+",
            },
            "planning_fallacy": {
                "description": "User consistently underestimates task duration",
                "likelihood": "high",
                "impact_level": "medium",
                "mitigation_strategy": "Apply time buffer multiplier from strategy map",
                "trigger_threshold": "3+ consecutive tasks exceeding estimate by 50%+",
            },
        }

        mapping = risk_mapping.get(pattern_name.lower())
        if not mapping:
            mapping = {
                "description": f"Detected behavior pattern: {pattern_name}",
                "likelihood": "medium",
                "impact_level": "medium",
                "mitigation_strategy": "Monitor and adapt execution parameters",
                "trigger_threshold": f"Pattern confidence >= {confidence:.0%}",
            }

        return await self.register_risk(
            plan_card_id=plan_card_id,
            source_pattern=pattern_name,
            evidence={**(evidence or {}), "confidence": confidence},
            **mapping,
        )

    async def update_from_outcome(
        self,
        *,
        plan_card_id: uuid.UUID,
        trigger_type: str,
        effective: bool,
        evidence: dict | None = None,
    ) -> int:
        """Update risks matching a trigger type based on intervention outcome.

        Returns count of risks updated.
        """
        risks = await self.get_active_risks(plan_card_id)
        updated = 0
        for risk in risks:
            source = risk.get("source_pattern", "").lower()
            trigger_match = (
                (trigger_type in ("STALL_PATTERN",) and source in ("procrastination", "avoidance", "execution"))
                or (trigger_type in ("OVERLOAD",) and source in ("overload", "planning_fallacy"))
                or (trigger_type in ("CONCEPT_GAP",) and source in ("cognitive",))
            )
            if trigger_match:
                new_status = "MITIGATED" if effective else "ACTIVE"
                await self.update_status(
                    plan_card_id=plan_card_id,
                    risk_id=risk["id"],
                    status=new_status,
                    evidence=evidence,
                )
                updated += 1
        return updated
