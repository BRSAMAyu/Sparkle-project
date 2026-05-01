from __future__ import annotations

"""
A/B Test Experiment Management API
A/B测试实验管理API

RESTful API endpoints for managing A/B test experiments including:
- Experiment CRUD operations
- Variant management
- Experiment lifecycle (start, pause, resume, complete)
- Statistical analysis
- Metric recording
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
from app.learning.statistics import ABTestStatistics
from app.models.experiment import (
    ABExperiment,
    ABExperimentMetric,
    ABExperimentVariant,
    ExperimentStatus,
)
from app.models.user import User

router = APIRouter(tags=["experiments"])


def _get_redis_client_or_503():
    redis_client = cache_service.redis
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis is not available")
    return redis_client


def _is_uuid_like(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (TypeError, ValueError):
        return False


async def _get_owned_experiment(
    db: AsyncSession,
    experiment_id: str,
    current_user: User,
    *,
    load_variants: bool = False,
) -> ABExperiment:
    query = select(ABExperiment).where(
        ABExperiment.id == experiment_id,
        ABExperiment.not_deleted_filter(),
    )
    if not current_user.is_superuser:
        query = query.where(ABExperiment.created_by == current_user.id)
    if load_variants:
        query = query.options(selectinload(ABExperiment.variants))

    result = await db.execute(query)
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


# Request/Response Models
class VariantConfig(BaseModel):
    """Variant configuration"""
    name: str = Field(..., description="Variant name")
    is_control: bool = Field(False, description="Whether this is the control variant")
    weight: float = Field(1.0, description="Allocation weight")
    description: str | None = Field(None, description="Variant description")
    prompt_version: str | None = Field(None, description="Prompt version identifier")
    configuration: dict | None = Field(None, description="Variant configuration (JSON)")


class CreateExperimentRequest(BaseModel):
    """Request to create a new experiment"""
    name: str = Field(..., max_length=200, description="Experiment name")
    description: str | None = Field(None, description="Experiment description")
    hypothesis: str = Field(..., description="Research hypothesis")
    variants: list[VariantConfig] = Field(
        ...,
        min_items=2,
        description="Experiment variants (at least 2: control + treatment)",
    )
    metrics: list[str] = Field(
        default=["success", "latency"],
        description="Metrics to track",
    )
    sample_size_target: int | None = Field(None, description="Target sample size")
    significance_level: float = Field(0.05, description="Significance level (alpha)")
    power: float = Field(0.8, description="Statistical power")
    minimum_detectable_effect: float | None = Field(
        None,
        description="Minimum detectable effect (relative)",
    )


class UpdateExperimentRequest(BaseModel):
    """Request to update an experiment"""
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    hypothesis: str | None = None


class CompleteExperimentRequest(BaseModel):
    """Request to complete an experiment"""
    conclusion: str = Field(..., description="Experiment conclusion")
    winning_variant_id: str | None = Field(None, description="ID of winning variant")


class RecordMetricRequest(BaseModel):
    """Request to record a metric"""
    metric_name: str = Field(..., description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    metric_type: str = Field(..., description="Metric type: success, latency, engagement, etc.")
    context_data: dict | None = Field(None, description="Additional context")


class VariantResponse(BaseModel):
    """Variant response"""
    id: UUID
    variant_name: str
    description: str | None
    is_control: bool
    allocation_weight: float
    traffic_allocation_percentage: float
    prompt_version: str | None
    configuration: dict | None

    model_config = ConfigDict(from_attributes=True)


class ExperimentResponse(BaseModel):
    """Experiment response"""
    id: UUID
    name: str
    description: str | None
    hypothesis: str
    status: str
    created_by: UUID | None
    sample_size_target: int | None
    significance_level: float
    power: float
    minimum_detectable_effect: float | None
    start_date: datetime | None
    end_date: datetime | None
    conclusion: str | None
    winning_variant_id: UUID | None
    created_at: datetime
    updated_at: datetime
    variants: list[VariantResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ExperimentStatsResponse(BaseModel):
    """Experiment statistics response"""
    experiment_id: str
    experiment_name: str
    status: str
    start_date: str | None
    sample_size_target: int | None
    sample_size_collected: int
    completion_percentage: float
    variants: list[dict]


# Endpoints
@router.post("/", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new A/B test experiment

    Creates an experiment with the specified variants and metrics.
    Automatically calculates sample size if not provided.
    """
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    # Prepare variant configs
    variant_configs = [
        {
            "name": v.name,
            "is_control": v.is_control,
            "weight": v.weight,
            "description": v.description,
            "prompt_version": v.prompt_version,
            "configuration": v.configuration,
        }
        for v in request.variants
    ]

    # Calculate sample size if not provided
    sample_size_target = request.sample_size_target
    if sample_size_target is None:
        # Assume baseline rate and calculate
        try:
            result = ABTestStatistics.calculate_sample_size(
                baseline_rate=0.1,  # Assumption
                minimum_detectable_effect=request.minimum_detectable_effect or 0.1,
                alpha=request.significance_level,
                power=request.power,
            )
            sample_size_target = result["total_sample_size"]
        except Exception as e:
            logger.warning(f"Could not calculate sample size: {e}")
            sample_size_target = 1000  # Default

    experiment = await framework.create_experiment(
        name=request.name,
        description=request.description,
        hypothesis=request.hypothesis,
        variants=variant_configs,
        metrics=request.metrics,
        created_by=str(current_user.id),
        sample_size_target=sample_size_target,
        significance_level=request.significance_level,
        power=request.power,
        minimum_detectable_effect=request.minimum_detectable_effect,
    )

    # Load with variants
    await db.refresh(experiment, ["variants"])

    return experiment


@router.get("/", response_model=list[ExperimentResponse])
async def list_experiments(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List experiments with optional filtering"""
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    status_enum = None
    if status:
        try:
            status_enum = ExperimentStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter") from None

    experiments = await framework.list_experiments(
        status=status_enum,
        created_by=str(current_user.id) if not current_user.is_superuser else None,
        limit=limit,
        offset=offset,
    )

    # Load variants for each experiment
    result = []
    for exp in experiments:
        await db.refresh(exp, ["variants"])
        result.append(exp)

    return result


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get experiment details"""
    return await _get_owned_experiment(db, experiment_id, current_user, load_variants=True)


@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an experiment"""
    await _get_owned_experiment(db, experiment_id, current_user)
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    try:
        experiment = await framework.start_experiment(experiment_id)
        await db.refresh(experiment, ["variants"])
        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{experiment_id}/pause", response_model=ExperimentResponse)
async def pause_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause a running experiment"""
    await _get_owned_experiment(db, experiment_id, current_user)
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    try:
        experiment = await framework.pause_experiment(experiment_id)
        await db.refresh(experiment, ["variants"])
        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{experiment_id}/resume", response_model=ExperimentResponse)
async def resume_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused experiment"""
    await _get_owned_experiment(db, experiment_id, current_user)
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    try:
        experiment = await framework.resume_experiment(experiment_id)
        await db.refresh(experiment, ["variants"])
        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
async def complete_experiment(
    experiment_id: str,
    request: CompleteExperimentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete an experiment with conclusions"""
    await _get_owned_experiment(db, experiment_id, current_user)
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    try:
        experiment = await framework.complete_experiment(
            experiment_id=experiment_id,
            conclusion=request.conclusion,
            winning_variant_id=request.winning_variant_id,
        )
        await db.refresh(experiment, ["variants"])
        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{experiment_id}/stats", response_model=ExperimentStatsResponse)
async def get_experiment_stats(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get experiment statistics"""
    await _get_owned_experiment(db, experiment_id, current_user)
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    stats = await framework.get_experiment_stats(experiment_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return stats


@router.post("/{experiment_id}/assign")
async def assign_variant(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get or create variant assignment for current user

    Returns the assigned variant for the user. Assignments are deterministic
    based on user ID and experiment ID.
    """
    redis_client = _get_redis_client_or_503()

    framework = ABTestFrameworkEnhanced(db, redis_client)

    if not _is_uuid_like(experiment_id):
        logger.warning(
            "Experiment %s is not UUID-backed; falling back to control cohort",
            experiment_id,
        )
        return {
            "variant_id": "control",
            "variant_name": "control",
            "is_control": True,
            "is_new_assignment": False,
            "fallback": True,
        }

    try:
        variant, is_new = await framework.assign_variant(
            experiment_id=experiment_id,
            user_id=str(current_user.id),
        )
        return {
            "variant_id": str(variant.id),
            "variant_name": variant.variant_name,
            "is_control": variant.is_control,
            "is_new_assignment": is_new,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{experiment_id}/metrics")
async def record_metric(
    experiment_id: str,
    variant_id: str,
    request: RecordMetricRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record a metric for an experiment

    Records a metric value for the specified variant.
    """
    redis_client = _get_redis_client_or_503()

    if not _is_uuid_like(experiment_id) or not _is_uuid_like(variant_id):
        logger.warning(
            "Skipping metric for non-UUID experiment assignment: experiment_id=%s, variant_id=%s",
            experiment_id,
            variant_id,
        )
        return {"status": "skipped", "reason": "non_uuid_assignment"}

    framework = ABTestFrameworkEnhanced(db, redis_client)

    await framework.record_metric(
        experiment_id=experiment_id,
        variant_id=variant_id,
        metric_name=request.metric_name,
        metric_value=request.metric_value,
        metric_type=request.metric_type,
        user_id=str(current_user.id),
        context_data=request.context_data,
    )

    return {"status": "recorded"}


@router.get("/{experiment_id}/analyze")
async def analyze_experiment(
    experiment_id: str,
    use_sequential: bool = Query(False, description="Use sequential analysis"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze experiment results with statistical tests

    Performs statistical analysis on the collected metrics,
    including hypothesis tests and effect size estimation.
    """
    experiment = await _get_owned_experiment(db, experiment_id, current_user)

    # Get metrics grouped by variant
    metrics_query = select(ABExperimentMetric).where(
        ABExperimentMetric.experiment_id == experiment_id
    )
    metrics_result = await db.execute(metrics_query)
    metrics = metrics_result.scalars().all()

    # Group metrics by variant
    variant_metrics = {}
    for metric in metrics:
        if metric.variant_id not in variant_metrics:
            variant_metrics[metric.variant_id] = {
                "success": [],
                "latency": [],
            }

        if metric.metric_name == "success":
            variant_metrics[metric.variant_id]["success"].append(metric.metric_value)
        elif metric.metric_name == "latency":
            variant_metrics[metric.variant_id]["latency"].append(metric.metric_value)

    # Find control and treatment variants
    variants_query = select(ABExperimentVariant).where(
        ABExperimentVariant.experiment_id == experiment_id
    )
    variants_result = await db.execute(variants_query)
    variants = variants_result.scalars().all()

    control_variant = next((v for v in variants if v.is_control), None)
    treatment_variant = next((v for v in variants if not v.is_control), None)

    if not control_variant or not treatment_variant:
        raise HTTPException(
            status_code=400,
            detail="Experiment must have both control and treatment variants",
        )

    control_id = str(control_variant.id)
    treatment_id = str(treatment_variant.id)

    # Perform statistical analysis
    analysis_results = {}

    # Analyze success metrics (proportion test)
    if control_id in variant_metrics and treatment_id in variant_metrics:
        control_success = sum(variant_metrics[control_id]["success"])
        control_total = len(variant_metrics[control_id]["success"])
        treatment_success = sum(variant_metrics[treatment_id]["success"])
        treatment_total = len(variant_metrics[treatment_id]["success"])

        if control_total > 0 and treatment_total > 0:
            analysis_results["success_rate"] = ABTestStatistics.chi_square_test(
                control_success=control_success,
                control_total=control_total,
                treatment_success=treatment_success,
                treatment_total=treatment_total,
                alpha=experiment.significance_level,
            )

        # Analyze latency metrics (t-test)
        if len(variant_metrics[control_id]["latency"]) > 0 and len(
            variant_metrics[treatment_id]["latency"]
        ) > 0:
            analysis_results["latency"] = ABTestStatistics.t_test(
                control_data=variant_metrics[control_id]["latency"],
                treatment_data=variant_metrics[treatment_id]["latency"],
                alpha=experiment.significance_level,
            )

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment.name,
        "analysis_results": analysis_results,
    }
