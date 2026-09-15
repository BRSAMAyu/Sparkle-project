"""First-Minute Experience (FME) — goal intent analysis.

Phase-1 Entry Wire endpoint that replaces the 5-step wizard's step 0 with a
single natural-language input. Returns a 60s-budget rules-based judgement
(no LLM call) so the user sees an immediate "啊哈" they can correct or accept.

Reuses ExamRescueDetector + NonExamFirstMinuteDetector under the hood — no
new ML, no new model, just exposing existing signal logic.

Wire mode is gated by the `goal_first_minute` kill switch:
  off    — endpoint returns 200 with mode="disabled" so the client can
           transparently fall back to the legacy wizard.
  shadow — analyzer runs and result is logged for ops, but the response
           still reports mode="disabled" so UI is unchanged.
  live   — full analysis returned to the client.

Kept in a dedicated module rather than augmenting goals.py so the legacy
goal CRUD path stays untouched and the FME feature can be removed cleanly
if rolled back.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.kill_switch import is_enabled_mode, is_live_mode
from app.models.user import User
from app.services.fme_kill_switch_service import fme_kill_switch_service
from app.signals.exam_rescue_detector import ExamRescueDetector, FirstMinuteSnapshot
from app.signals.non_exam_first_minute_detector import NonExamFirstMinuteDetector

router = APIRouter()

_exam_detector = ExamRescueDetector()
_non_exam_detector = NonExamFirstMinuteDetector()


class GoalIntentAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class GoalIntentCorrectionOption(BaseModel):
    key: str
    label: str


class GoalIntentSuggestedAction(BaseModel):
    key: str
    label: str
    estimated_minutes: int = 0


class GoalIntentAnalyzeResponse(BaseModel):
    # "disabled" | "exam_rescue" | "exam_build" | "job_search_*"
    # | "project_*" | "habit_*" | "standard"
    mode: str
    detected_subject: str | None = None
    deadline_days: int | None = None
    baseline: str | None = None
    confidence: float = 0.0
    headline: str = ""
    next_best_action: str = ""
    correction_options: list[GoalIntentCorrectionOption] = Field(default_factory=list)
    suggested_actions: list[GoalIntentSuggestedAction] = Field(default_factory=list)


_DEFAULT_CORRECTION_OPTIONS: list[GoalIntentCorrectionOption] = [
    GoalIntentCorrectionOption(key="confirm", label="对，就是这个"),
    GoalIntentCorrectionOption(key="adjust_high_score", label="我有基础，想冲高分"),
    GoalIntentCorrectionOption(key="not_exam", label="不是考试，是别的"),
    GoalIntentCorrectionOption(key="explain_self", label="都不对，我解释一下"),
]


def _suggested_actions_for(snapshot: FirstMinuteSnapshot) -> list[GoalIntentSuggestedAction]:
    """Translate the detector's next_best_action into 1-2 concrete options."""
    nxt = snapshot.next_best_action or ""
    if "diagnostic_or_upload_materials" in nxt:
        return [
            GoalIntentSuggestedAction(
                key="upload_materials",
                label="上传课件 / 往年题（≈12 分钟诊断）",
                estimated_minutes=12,
            ),
            GoalIntentSuggestedAction(
                key="quick_pretest",
                label="直接做一套往年题摸底",
                estimated_minutes=20,
            ),
        ]
    if nxt == "diagnostic":
        return [
            GoalIntentSuggestedAction(
                key="quick_pretest",
                label="先做 10 分钟摸底题",
                estimated_minutes=10,
            ),
        ]
    if nxt == "suggest_minimum_pass_path":
        return [
            GoalIntentSuggestedAction(
                key="minimum_pass_outline",
                label="生成「先过线」最小路径",
                estimated_minutes=5,
            ),
        ]
    if nxt:
        return [
            GoalIntentSuggestedAction(
                key="next_step",
                label=str(nxt),
                estimated_minutes=10,
            ),
        ]
    return []


def _empty_response() -> GoalIntentAnalyzeResponse:
    return GoalIntentAnalyzeResponse(mode="disabled")


# route-tier: authed
# Mounted at /goals/analyze-intent in app.api.v1.router
@router.post("/analyze-intent", response_model=GoalIntentAnalyzeResponse)
async def analyze_goal_intent(
    payload: GoalIntentAnalyzeRequest,
    current_user: User = Depends(get_current_user),
) -> GoalIntentAnalyzeResponse:
    """Rules-based intent analysis (≤60s budget, no LLM)."""
    mode = await fme_kill_switch_service.get_feature_mode("goal_first_minute")

    # off — never run analyzer; client falls back to legacy wizard.
    if not is_enabled_mode(mode):
        return _empty_response()

    text = payload.text.strip()
    if not text:
        return _empty_response()

    # Try exam first (matches user's example "7天后计网考试基本没学想先别挂").
    snapshot: FirstMinuteSnapshot | None = _exam_detector.analyze_first_message(
        text,
        is_new_conversation=True,
        user_id=str(current_user.id),
    )
    if snapshot is None:
        snapshot = _non_exam_detector.analyze_first_message(
            text,
            is_new_conversation=True,
            user_id=str(current_user.id),
        )

    if snapshot is None:
        analysis = GoalIntentAnalyzeResponse(
            mode="standard",
            confidence=0.0,
            headline="我需要再了解一点你的目标",
            next_best_action="continue_with_wizard",
        )
    else:
        analysis = GoalIntentAnalyzeResponse(
            mode=snapshot.detected_mode,
            detected_subject=snapshot.subject,
            deadline_days=snapshot.deadline_days,
            baseline=snapshot.baseline,
            confidence=float(snapshot.confidence),
            headline=snapshot.first_user_visible_hypothesis,
            next_best_action=snapshot.next_best_action,
            correction_options=list(_DEFAULT_CORRECTION_OPTIONS),
            suggested_actions=_suggested_actions_for(snapshot),
        )

    # shadow — log for ops, don't expose to client.
    if not is_live_mode(mode):
        logger.info(
            "FME[shadow] goal_first_minute user={} mode={} confidence={:.2f}",
            current_user.id,
            analysis.mode,
            analysis.confidence,
        )
        return _empty_response()

    fme_kill_switch_service.record_gauge("goal_first_minute", mode)
    return analysis
