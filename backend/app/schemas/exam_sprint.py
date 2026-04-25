"""Schemas for exam sprint cold-start intake."""

from __future__ import annotations

from datetime import date as date_type
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    exam_date: date_type = Field(description="Exam date")
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

    exam_date: date_type
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


class HelpfulFeature(StrEnum):
    TASK_CARDS = "task_cards"
    ERROR_REVIEW = "error_review"
    STRATEGY_ADJUSTMENT = "strategy_adjustment"
    CALIBRATION_CARDS = "calibration_cards"


class ReviewTopicSelection(BaseModel):
    node_id: UUID | None = None
    node_name: str = Field(..., min_length=1, max_length=255)


class ReviewPlanSelection(BaseModel):
    task_id: UUID | None = None
    label: str = Field(..., min_length=1, max_length=255)


class PostExamReviewRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: UUID | None = None
    self_rating: int | None = Field(default=None, ge=1, le=10)
    result_rating: int | None = Field(default=None, ge=1, le=5)
    result_description: str = Field(default="", max_length=2000)
    biggest_challenge: str = Field(default="", max_length=2000)
    strategy_feedback: str = Field(default="", max_length=2000)
    self_advice: str = Field(default="", max_length=2000)
    underprepared_topics: list[ReviewTopicSelection] = Field(default_factory=list)
    prepared_but_not_tested_topics: list[ReviewPlanSelection] = Field(default_factory=list)
    sparkle_helped: bool = True
    helpful_features: list[HelpfulFeature] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_rating_scales(self) -> PostExamReviewRequest:
        if self.self_rating is None and self.result_rating is None:
            raise ValueError("self_rating or result_rating is required")
        if self.result_rating is None and self.self_rating is not None:
            self.result_rating = max(1, min(5, round(self.self_rating / 2)))
        if self.self_rating is None and self.result_rating is not None:
            self.self_rating = max(1, min(10, self.result_rating * 2))
        return self


class SprintTaskStats(BaseModel):
    total: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SprintScoreStats(BaseModel):
    baseline_score: float | None = Field(default=None, ge=0.0, le=100.0)
    current_score: float | None = Field(default=None, ge=0.0, le=100.0)
    delta: float | None = None
    baseline_source: str | None = None


class SprintMasteryDelta(BaseModel):
    node_id: UUID | None = None
    node_name: str
    before_mastery: float = Field(..., ge=0.0, le=100.0)
    after_mastery: float = Field(..., ge=0.0, le=100.0)
    delta: float


class SprintCoverageStats(BaseModel):
    baseline_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    current_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    delta_rate: float
    total_topics: int = Field(default=0, ge=0)
    covered_topics_before: int = Field(default=0, ge=0)
    covered_topics_after: int = Field(default=0, ge=0)


class SprintErrorRecoveryStats(BaseModel):
    total_errors: int = Field(default=0, ge=0)
    repaired_errors: int = Field(default=0, ge=0)
    repair_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SprintDailyStudyPoint(BaseModel):
    date: date_type
    minutes: int = Field(default=0, ge=0)


class SprintInvitationStatus(BaseModel):
    eligible: bool = False
    invited_at: str | None = None
    notification_id: str | None = None
    completed_at: str | None = None
    review_id: str | None = None


class SprintSummaryResponse(BaseModel):
    plan_id: UUID
    plan_name: str
    subject: str | None = None
    exam_date: date_type | None = None
    started_at: str
    days_used: int = Field(..., ge=1)
    headline: str
    task_stats: SprintTaskStats
    score_stats: SprintScoreStats
    mastery_changes: list[SprintMasteryDelta] = Field(default_factory=list)
    top_improvement: SprintMasteryDelta | None = None
    high_frequency_coverage: SprintCoverageStats
    error_recovery: SprintErrorRecoveryStats
    daily_study_trend: list[SprintDailyStudyPoint] = Field(default_factory=list)
    narrative_highlights: list[str] = Field(default_factory=list)
    invitation_status: SprintInvitationStatus = Field(default_factory=SprintInvitationStatus)


class PostExamReviewResponse(BaseModel):
    review_id: str
    plan_id: UUID
    archived_in_growth_profile: bool = True
    helpful_features: list[HelpfulFeature] = Field(default_factory=list)
    summary: SprintSummaryResponse
    unlocked_achievements: list[dict[str, Any]] = Field(default_factory=list)


class SprintCompletionSummary(BaseModel):
    mastered_nodes_count: int = Field(default=0, ge=0)
    repaired_errors_count: int = Field(default=0, ge=0)
    completed_tasks_count: int = Field(default=0, ge=0)
    strongest_area: str
    growth_area: str


class SprintCompletionCheckResponse(BaseModel):
    completed: bool = False
    summary: SprintCompletionSummary | None = None


class ExamSprintDashboardTaskItem(BaseModel):
    """One task entry shown inside the sprint dashboard card."""

    id: str
    title: str
    status: str
    estimated_minutes: int = Field(default=0, ge=0)
    is_completed: bool = False
    knowledge_node_id: str | None = None
    due_date: date_type | None = None
    compressed: bool = False
    compression_reason: str | None = None


class ExamSprintDashboardTaskGroup(BaseModel):
    """Tasks bucketed by sprint day."""

    day_index: int = Field(ge=1)
    date: date_type | None = None
    is_today: bool = False
    completed_count: int = Field(default=0, ge=0)
    total_count: int = Field(default=0, ge=0)
    tasks: list[ExamSprintDashboardTaskItem] = Field(default_factory=list)


class ExamSprintDashboardProgress(BaseModel):
    """Today's completion summary."""

    completed: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class ExamSprintDashboardResponse(BaseModel):
    """Aggregated payload for the exam sprint dashboard home card."""

    active: bool
    plan_id: str | None = None
    plan_name: str | None = None
    subject: str | None = None
    days_left: int | None = Field(default=None, ge=0)
    target_mode: TargetMode | None = None
    estimated_score_now: float | None = Field(default=None, ge=0.0, le=100.0)
    baseline_estimated_score: float | None = Field(default=None, ge=0.0, le=100.0)
    pass_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    baseline_pass_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    today_progress: ExamSprintDashboardProgress = Field(default_factory=ExamSprintDashboardProgress)
    high_freq_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    high_freq_covered_count: int = Field(default=0, ge=0)
    high_freq_total_count: int = Field(default=0, ge=0)
    mistake_fix_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    fixed_mistake_count: int = Field(default=0, ge=0)
    total_mistake_count: int = Field(default=0, ge=0)
    streak_days: int = Field(default=0, ge=0)
    high_yield_low_mastery_topics: list[str] = Field(default_factory=list)
    task_groups: list[ExamSprintDashboardTaskGroup] = Field(default_factory=list)
    sleep_guard_hint: str | None = None


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


class PortfolioSprintEntry(BaseModel):
    """One sprint entry in the learning portfolio."""

    plan_id: UUID
    plan_name: str
    subject: str | None = None
    sprint_mode: str | None = None
    status: str = Field(description="active | completed | planned")
    mastered_nodes_count: int = Field(default=0, ge=0)
    started_at: str | None = None
    completed_at: str | None = None
    target_date: date_type | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    strongest_area: str | None = None
    growth_area: str | None = None
    self_rating: int | None = Field(default=None, ge=1, le=10)
    result_rating: int | None = Field(default=None, ge=1, le=5)
    result_description: str | None = None
    headline: str | None = None
    current_score: float | None = Field(default=None, ge=0.0, le=100.0)
    weakest_points: list[str] = Field(default_factory=list)
    proud_nodes: list[str] = Field(default_factory=list)


class LearningPortfolioResponse(BaseModel):
    """Aggregated learning portfolio across all exam sprints."""

    entries: list[PortfolioSprintEntry] = Field(default_factory=list)
    total_mastered_nodes: int = Field(default=0, ge=0)
    active_count: int = Field(default=0, ge=0)
    completed_count: int = Field(default=0, ge=0)
    planned_count: int = Field(default=0, ge=0)


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


# ---------------------------------------------------------------------------
# G27: Sprint Pack Node Quality Alert
# ---------------------------------------------------------------------------


class NodeQualityAlert(BaseModel):
    """Alert indicating a pack node's difficulty may be miscalibrated."""

    node_id: str
    node_label: str
    current_difficulty: int = Field(ge=1, le=5)
    suggested_difficulty: int = Field(ge=1, le=5)
    average_post_sprint_mastery: float = Field(ge=0.0, le=100.0)
    expected_mastery: float = Field(ge=0.0, le=100.0)
    evidence_count: int = Field(ge=0)


class PackQualityReport(BaseModel):
    """Quality report for a Sprint Pack, generated from user mastery data."""

    pack_id: str
    pack_name: str
    total_nodes: int = Field(ge=0)
    nodes_analyzed: int = Field(ge=0)
    alerts: list[NodeQualityAlert] = Field(default_factory=list)
    insufficient_data_nodes: int = Field(ge=0, default=0)
