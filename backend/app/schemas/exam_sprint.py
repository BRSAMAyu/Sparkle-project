"""Schemas for exam sprint cold-start intake."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

TargetMode = Literal["pass", "hold", "high_score"]
PackSelectionType = Literal["scenario_pack", "generic_policy"]


class ExamSprintScopeContext(BaseModel):
    """Structured scope input from the setup form."""

    text: str | None = Field(default=None, max_length=5000, description="Teacher focus, scope notes, or pasted text")
    file_ids: list[str] = Field(default_factory=list, description="Previously uploaded file IDs")
    file_names: list[str] = Field(default_factory=list, description="Display names for uploaded files")


class ExamSprintBaselineInput(BaseModel):
    """Current self-reported baseline."""

    current_level: int = Field(ge=0, le=100, description="Self-rated current mastery from 0-100")
    weak_chapters: list[str] = Field(default_factory=list, description="User-selected weak chapters/tags")


class ExamSprintIntakeRequest(BaseModel):
    """Cold-start intake request for exam sprint mode."""

    subject: str = Field(min_length=1, max_length=120, description="Course or exam subject")
    exam_date: date = Field(description="Exam date")
    target_mode: TargetMode = Field(description="User-selected goal mode")
    scope_context: ExamSprintScopeContext = Field(default_factory=ExamSprintScopeContext)
    baseline: ExamSprintBaselineInput = Field(description="Current baseline and weak chapters")
    daily_study_minutes: int = Field(ge=15, le=720, description="Realistic daily study minutes")
    conversation_id: str | None = Field(default=None, max_length=160, description="Optional conversation/session id")


class ExamSprintUserModel(BaseModel):
    """Initial user model derived from cold-start intake."""

    subject: str
    exam_scope: str
    knowledge_baseline: str
    current_level: int
    weak_chapters: list[str] = Field(default_factory=list)
    daily_study_minutes: int
    available_materials: list[str] = Field(default_factory=list)
    scope_file_ids: list[str] = Field(default_factory=list)
    scope_file_names: list[str] = Field(default_factory=list)
    planning_session_id: str
    conversation_id: str


class ExamSprintGoalModel(BaseModel):
    """Initial goal model returned after intake."""

    exam_date: date
    days_left: int = Field(ge=1)
    target_mode: TargetMode
    estimated_score_now: int = Field(ge=0, le=100)
    target_score_hint: int = Field(ge=0, le=100)
    recommended_mode: TargetMode


class ExamSprintPackSelection(BaseModel):
    """Selected pack or fallback policy."""

    pack_id: str
    pack_name: str
    selection_type: PackSelectionType
    reason: str


class ExamSprintAssessment(BaseModel):
    """Initial assessment shown immediately after intake."""

    pass_probability: float = Field(ge=0.0, le=1.0)
    recommended_mode: TargetMode
    recommended_mode_label: str
    summary: str


class ExamSprintLaunchPayload(BaseModel):
    """Plan/task launch targets returned to the client."""

    plan_id: str
    plan_name: str
    first_day_task_ids: list[str] = Field(default_factory=list)
    recommended_task_id: str | None = None
    plan_route: str
    recommended_task_route: str | None = None


class ExamSprintStrategyPreview(BaseModel):
    """Small preview of the selected sprint strategy."""

    sprint_mode: str
    daily_commitment_range: str
    first_day_focus: str
    first_day_output: str


class ExamSprintIntakeResponse(BaseModel):
    """Exam sprint intake response."""

    planning_session_id: str
    conversation_id: str
    user_model: ExamSprintUserModel
    goal_model: ExamSprintGoalModel
    selected_pack: ExamSprintPackSelection
    initial_assessment: ExamSprintAssessment
    strategy_preview: ExamSprintStrategyPreview
    launch: ExamSprintLaunchPayload


class DiagnoseConfidence(StrEnum):
    CERTAIN = "certain"
    FUZZY = "fuzzy"
    GUESS = "guess"


class DiagnoseQuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    SHORT_ANSWER = "short_answer"


class RecommendedPath(StrEnum):
    MINIMUM_PASS = "minimum_pass"
    SCORE_MAX = "score_max"


class DiagnosticKnowledgeNode(BaseModel):
    node_id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    domain: str | None = Field(default=None, max_length=100)
    exam_weight: float = Field(default=1.0, ge=0.1, le=3.0)
    frequency: float = Field(default=1.0, ge=0.1, le=3.0)
    prerequisites: list[str] = Field(default_factory=list)
    mistake_tags: list[str] = Field(default_factory=list)


class DiagnosticQuestionPrompt(BaseModel):
    question_id: str
    domain: str
    archetype: str
    question_type: DiagnoseQuestionType
    stem: str
    choices: list[str] = Field(default_factory=list)
    linked_node_slugs: list[str] = Field(default_factory=list)
    linked_node_ids: list[UUID] = Field(default_factory=list)
    linked_node_names: list[str] = Field(default_factory=list)
    points: float = Field(default=1.0, ge=0.1, le=5.0)
    expected_seconds: int = Field(default=50, ge=15, le=300)
    confidence_prompt: str = Field(default="你现在对这道题的把握是？")


class DiagnosticQuestionGrader(BaseModel):
    template_key: str
    question_type: DiagnoseQuestionType
    correct_choice_index: int | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    partial_keywords: list[str] = Field(default_factory=list)
    error_tags: list[str] = Field(default_factory=list)
    linked_node_slugs: list[str] = Field(default_factory=list)
    linked_node_ids: list[UUID] = Field(default_factory=list)
    linked_node_names: list[str] = Field(default_factory=list)
    points: float = Field(default=1.0, ge=0.1, le=5.0)


class DiagnosticGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    question_count: int = Field(default=12, ge=10, le=15)
    sprint_pack_id: str | None = Field(default=None, max_length=100)
    sprint_pack_path: str | None = Field(default=None, max_length=500)
    days_left: int | None = Field(default=None, ge=1, le=365)
    pass_score: float = Field(default=60.0, ge=0.0, le=100.0)
    knowledge_nodes: list[DiagnosticKnowledgeNode] = Field(default_factory=list)


class DiagnosticGenerateResponse(BaseModel):
    diagnostic_id: str
    subject: str
    sprint_pack_id: str
    question_count: int
    estimated_minutes: int
    coverage_domains: list[str] = Field(default_factory=list)
    question_archetypes: list[str] = Field(default_factory=list)
    checkpoint_template: str
    questions: list[DiagnosticQuestionPrompt] = Field(default_factory=list)
    grading_payload: dict[str, DiagnosticQuestionGrader] = Field(default_factory=dict)


class DiagnosticAnswerSubmission(BaseModel):
    question_id: str
    answer: str = Field(default="")
    confidence: DiagnoseConfidence = DiagnoseConfidence.FUZZY
    elapsed_seconds: int | None = Field(default=None, ge=0, le=3600)


class DiagnosticGradeRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    answers: list[DiagnosticAnswerSubmission] = Field(default_factory=list, min_length=1)
    grading_payload: dict[str, DiagnosticQuestionGrader] = Field(default_factory=dict)
    sprint_pack_id: str | None = Field(default=None, max_length=100)
    sprint_pack_path: str | None = Field(default=None, max_length=500)
    days_left: int | None = Field(default=None, ge=1, le=365)
    pass_score: float = Field(default=60.0, ge=0.0, le=100.0)
    update_galaxy: bool = True
    knowledge_nodes: list[DiagnosticKnowledgeNode] = Field(default_factory=list)


class DiagnosticBottleneck(BaseModel):
    node_id: UUID | None = None
    node_name: str
    node_slug: str | None = None
    domain: str
    mastery: float = Field(..., ge=0.0, le=100.0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    mistake_tags: list[str] = Field(default_factory=list)
    avg_confidence: str
    reason: str


class DiagnosticMasteryUpdate(BaseModel):
    node_id: UUID | None = None
    node_name: str
    node_slug: str | None = None
    mastery: float = Field(..., ge=0.0, le=100.0)
    source: str = "exam_sprint_diagnose"


class DiagnosticGradeResponse(BaseModel):
    estimated_score_now: float = Field(..., ge=0.0, le=100.0)
    pass_probability: float = Field(..., ge=0.0, le=1.0)
    top_bottlenecks: list[DiagnosticBottleneck] = Field(default_factory=list)
    error_distribution: dict[str, float] = Field(default_factory=dict)
    mistake_clusters: list[dict[str, Any]] = Field(default_factory=list)
    recommended_path: RecommendedPath
    node_mastery_updates: list[DiagnosticMasteryUpdate] = Field(default_factory=list)
    coverage_domains: list[str] = Field(default_factory=list)
    confidence_calibration: dict[str, float] = Field(default_factory=dict)
