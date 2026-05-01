from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.cache import cache_service
from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService
from app.services.card_protocol.phase_design_service import PhaseDesignService
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.planning_memory_service import PlanningMemoryService


@dataclass
class FeedbackGateSession:
    session_id: str
    phase_card_id: str
    plan_card_id: str
    questions: list[str]
    retrospective: dict[str, Any]
    current_index: int
    answers: list[dict[str, Any]]
    status: str


class FeedbackGateEngine:
    """Context-aware phase feedback gate and next-phase advancement."""

    CACHE_PREFIX = "phase_e:feedback_gate:"
    SESSION_TTL_SECONDS = 60 * 60

    def __init__(self, db, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.phase_service = PhaseService(db, event_bus)
        self.memory_service = PlanningMemoryService(db, event_bus)
        self.phase_design_service = PhaseDesignService(db, event_bus)
        self.main_chain_artifact_service = MainChainArtifactService(db, event_bus)

    async def trigger_feedback_gate(
        self,
        *,
        phase_card_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        phase = await self.phase_service._get_owned_phase(phase_card_id, user_id)
        plan = await self.phase_service._get_parent_plan(phase.id)
        if not plan:
            raise ValueError("Phase must belong to a plan")

        retrospective = await self.phase_service._build_phase_retrospective(phase.id)
        questions = self._build_questions(phase.metadata_ or {}, retrospective)
        session = FeedbackGateSession(
            session_id=str(uuid4()),
            phase_card_id=str(phase.id),
            plan_card_id=str(plan.id),
            questions=questions,
            retrospective=retrospective,
            current_index=0,
            answers=[],
            status="ACTIVE",
        )
        await cache_service.set(self._session_key(session.session_id), asdict(session), ttl=self.SESSION_TTL_SECONDS)
        return {
            "session_id": session.session_id,
            "phase_card_id": session.phase_card_id,
            "plan_card_id": session.plan_card_id,
            "retrospective": retrospective,
            "questions": questions,
            "workflow_state": "PHASE_FEEDBACK_GATE",
        }

    async def process_feedback_response(
        self,
        *,
        session_id: str,
        user_message: str,
    ) -> dict[str, Any]:
        session = await self._load_session(session_id)
        if session is None:
            raise ValueError("Feedback gate session not found or expired")
        if session.status != "ACTIVE":
            raise ValueError("Feedback gate session is already completed")

        question = session.questions[session.current_index]
        session.answers.append({"question": question, "answer": user_message, "answered_at": datetime.utcnow().isoformat()})
        session.current_index += 1

        completed = session.current_index >= len(session.questions)
        if completed:
            session.status = "COMPLETED"
        await cache_service.set(self._session_key(session.session_id), asdict(session), ttl=self.SESSION_TTL_SECONDS)

        if not completed:
            return {
                "session_id": session.session_id,
                "completed": False,
                "next_question": session.questions[session.current_index],
                "answers_collected": len(session.answers),
            }

        phase = await self.phase_service._get_owned_phase(UUID(session.phase_card_id), await self._resolve_phase_owner(UUID(session.phase_card_id)))
        feedback_payload = self._build_feedback_payload(session)
        phase_feedback = await self.phase_service.submit_phase_feedback(
            phase_card_id=phase.id,
            user_id=phase.owner_id,
            feedback=feedback_payload,
        )
        archive_entry = await self.memory_service.archive_phase(
            phase_card_id=phase.id,
            retrospective=session.retrospective,
            feedback_gate=feedback_payload,
        )
        drift = await self.memory_service.compute_drift_score(
            plan_card_id=UUID(session.plan_card_id),
            current_phase={"feedback_gate": {"alignment_score": phase_feedback.alignment_score}},
        )
        await self.main_chain_artifact_service.refresh_active_phase_pack(
            plan_card_id=UUID(session.plan_card_id),
            generated_reason="phase_feedback_gate_completed",
        )
        await self.main_chain_artifact_service.refresh_reflection_report(
            plan_card_id=UUID(session.plan_card_id),
            generated_reason="phase_feedback_gate_completed",
        )
        await cache_service.delete(self._session_key(session.session_id))
        return {
            "session_id": session.session_id,
            "completed": True,
            "feedback_payload": feedback_payload,
            "phase_feedback": phase_feedback.__dict__,
            "archive_entry": archive_entry,
            "drift_assessment": asdict(drift),
            "recommended_next_step": drift.recommendation,
        }

    async def advance_to_next_phase(
        self,
        *,
        plan_card_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        plan_card = await self.phase_service._get_owned_plan(plan_card_id, user_id)
        phases = await self.phase_service.get_plan_phases(plan_card.id)
        current_phase_id = (plan_card.metadata_ or {}).get("current_phase_card_id")
        if not current_phase_id:
            raise ValueError("Plan has no active phase")
        current_phase = next((phase for phase in phases if str(phase.id) == str(current_phase_id)), None)
        if current_phase is None:
            raise ValueError("Current phase pointer is invalid")

        drift = await self.memory_service.compute_drift_score(plan_card_id=plan_card.id)
        if drift.recommendation == "review_compass":
            metadata = dict(plan_card.metadata_ or {})
            metadata["workflow_state"] = "COMPASS_REVIEW"
            plan_card.metadata_ = metadata
            plan_card.version += 1
            await self.db.flush()
            return {
                "advanced": False,
                "reason": "drift_requires_compass_review",
                "drift_assessment": asdict(drift),
                "workflow_state": "COMPASS_REVIEW",
            }

        current_design = dict((current_phase.metadata_ or {}).get("phase_design") or {})
        if not current_design.get("created_task_ids"):
            target_phase = current_phase
            advanced = False
        else:
            current_index = phases.index(current_phase)
            target_phase = phases[current_index + 1] if current_index + 1 < len(phases) else None
            if target_phase is None:
                return {
                    "advanced": False,
                    "reason": "no_next_phase",
                    "workflow_state": "COMPASS_REVIEW",
                    "drift_assessment": asdict(drift),
                }
            await self.phase_service.activate_phase(
                phase_card_id=target_phase.id,
                user_id=user_id,
            )
            advanced = True

        designed = await self.phase_design_service.design_phase_tasks(
            phase_card_id=target_phase.id,
            plan_card_id=plan_card.id,
            user_id=user_id,
        )
        await self.main_chain_artifact_service.refresh_active_phase_pack(
            plan_card_id=plan_card.id,
            generated_reason="phase_advanced",
        )
        return {
            "advanced": advanced,
            "next_phase_card_id": str(target_phase.id),
            "designed_task_count": len(designed),
            "designed_tasks": designed,
            "workflow_state": "PHASE_DESIGN",
            "drift_assessment": asdict(drift),
        }

    async def _load_session(self, session_id: str) -> FeedbackGateSession | None:
        payload = await cache_service.get(self._session_key(session_id))
        if not isinstance(payload, dict):
            return None
        return FeedbackGateSession(**payload)

    def _session_key(self, session_id: str) -> str:
        return f"{self.CACHE_PREFIX}{session_id}"

    def _build_questions(self, phase_metadata: dict, retrospective: dict[str, Any]) -> list[str]:
        questions = []
        progress = float(retrospective.get("progress") or 0.0)
        if progress >= 0.75:
            questions.append("这个阶段你最大的收获是什么？哪种安排最帮助你持续推进？")
        else:
            questions.append("这个阶段最卡住你的地方是什么？是难度、节奏，还是现实约束？")
        if retrospective.get("deferred_occurrence_count", 0) > 0:
            questions.append("你多次延期的根本原因更接近时间不够、任务太重，还是注意力不稳定？")
        questions.append("你的生活情况或目标优先级有变化吗？这会影响下一阶段的规划吗？")
        questions.append("如果下一阶段只保留一件最值得坚持的事，你希望它是什么？")
        return questions[:3]

    def _build_feedback_payload(self, session: FeedbackGateSession) -> dict[str, Any]:
        free_text = " ".join(answer["answer"] for answer in session.answers)
        lower = free_text.lower()
        blocked = any(token in free_text for token in ("卡住", "没时间", "太难", "阻力", "忙")) or "stuck" in lower
        life_changed = any(token in free_text for token in ("变化", "换工作", "考试", "家庭", "生病")) or "changed" in lower
        request_compass_review = any(token in free_text for token in ("换目标", "不想继续", "方向变了")) or "pivot" in lower
        positive = any(token in free_text for token in ("收获", "顺利", "有效", "进步")) or "progress" in lower
        alignment_score = 0.8 if positive and not blocked else 0.45 if blocked or life_changed else 0.6
        return {
            "rating": round(alignment_score * 5, 1),
            "reflection": free_text[:2000],
            "blocked": blocked,
            "life_changed": life_changed,
            "request_compass_review": request_compass_review,
            "structured_answers": {"answers": session.answers},
        }

    async def _resolve_phase_owner(self, phase_card_id: UUID) -> UUID:
        phase = await self.phase_service.card_service.get_card(phase_card_id)
        if not phase:
            raise ValueError("Phase card not found")
        return phase.owner_id
