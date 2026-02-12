"""
Enhanced A/B Testing Framework with Database Persistence
增强的A/B测试框架，支持数据库持久化和统计分析

This module extends the existing Redis-based framework with:
- Database-backed experiment metadata
- Persistent metric storage
- Experiment lifecycle management
- Statistical analysis integration
"""
import hashlib
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.experiment import (
    ABExperiment,
    ABExperimentAssignment,
    ABExperimentMetric,
    ABExperimentVariant,
    ExperimentStatus,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ABTestFrameworkEnhanced:
    """
    Enhanced A/B Testing Framework with database persistence.

    This class bridges the Redis-based implementation with database models,
    providing persistent storage for experiment metadata and metrics while
    maintaining Redis for fast variant assignment.
    """

    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client

    async def create_experiment(
        self,
        name: str,
        description: str,
        hypothesis: str,
        variants: list[dict],
        metrics: list[str],
        created_by: str,
        sample_size_target: int | None = None,
        significance_level: float = 0.05,
        power: float = 0.8,
        minimum_detectable_effect: float | None = None,
    ) -> ABExperiment:
        """
        Create a new A/B test experiment with database persistence.

        Args:
            name: Experiment name
            description: Experiment description
            hypothesis: Research hypothesis
            variants: List of variant configs, e.g.:
                [
                    {"name": "control", "is_control": True, "weight": 0.5},
                    {"name": "treatment", "is_control": False, "weight": 0.5}
                ]
            metrics: List of metric names to track
            created_by: User ID of creator
            sample_size_target: Target sample size (optional, will calculate if not provided)
            significance_level: Statistical significance level (alpha)
            power: Statistical power (1-beta)
            minimum_detectable_effect: Minimum detectable effect (relative)

        Returns:
            ABExperiment: Created experiment
        """
        # Create experiment
        experiment = ABExperiment(
            name=name,
            description=description,
            hypothesis=hypothesis,
            status=ExperimentStatus.CREATED,
            created_by=created_by,
            sample_size_target=sample_size_target,
            significance_level=significance_level,
            power=power,
            minimum_detectable_effect=minimum_detectable_effect,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

        self.db.add(experiment)
        await self.db.flush()

        # Create variants
        total_weight = sum(v.get("weight", 1.0) for v in variants)

        for variant_config in variants:
            weight = variant_config.get("weight", 1.0)
            traffic_percentage = (weight / total_weight) * 100 if total_weight > 0 else 50.0

            variant = ABExperimentVariant(
                experiment_id=experiment.id,
                variant_name=variant_config["name"],
                description=variant_config.get("description"),
                is_control=variant_config.get("is_control", False),
                prompt_version=variant_config.get("prompt_version"),
                configuration=variant_config.get("configuration"),
                allocation_weight=weight,
                traffic_allocation_percentage=traffic_percentage,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            self.db.add(variant)

        await self.db.commit()

        # Cache in Redis for fast access
        await self._cache_experiment_config(experiment, variants)

        logger.info(f"Created experiment {experiment.id}: {name}")
        return experiment

    async def start_experiment(self, experiment_id: str) -> ABExperiment:
        """Start an experiment."""
        experiment = await self.db.get(ABExperiment, experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = _utcnow()
        experiment.updated_at = _utcnow()

        await self.db.commit()
        logger.info(f"Started experiment {experiment_id}")

        return experiment

    async def pause_experiment(self, experiment_id: str) -> ABExperiment:
        """Pause an experiment."""
        experiment = await self.db.get(ABExperiment, experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError(f"Cannot pause experiment in status {experiment.status}")

        experiment.status = ExperimentStatus.PAUSED
        experiment.updated_at = _utcnow()

        await self.db.commit()
        logger.info(f"Paused experiment {experiment_id}")

        return experiment

    async def resume_experiment(self, experiment_id: str) -> ABExperiment:
        """Resume a paused experiment."""
        experiment = await self.db.get(ABExperiment, experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if experiment.status != ExperimentStatus.PAUSED:
            raise ValueError(f"Cannot resume experiment in status {experiment.status}")

        experiment.status = ExperimentStatus.RUNNING
        experiment.updated_at = _utcnow()

        await self.db.commit()
        logger.info(f"Resumed experiment {experiment_id}")

        return experiment

    async def complete_experiment(
        self,
        experiment_id: str,
        conclusion: str,
        winning_variant_id: str | None = None,
    ) -> ABExperiment:
        """
        Complete an experiment with results.

        Args:
            experiment_id: Experiment ID
            conclusion: Experiment conclusion
            winning_variant_id: ID of winning variant (optional)

        Returns:
            ABExperiment: Updated experiment
        """
        experiment = await self.db.get(ABExperiment, experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if experiment.status not in [ExperimentStatus.RUNNING, ExperimentStatus.PAUSED]:
            raise ValueError(f"Cannot complete experiment in status {experiment.status}")

        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = _utcnow()
        experiment.conclusion = conclusion
        experiment.winning_variant_id = winning_variant_id
        experiment.updated_at = _utcnow()

        await self.db.commit()
        logger.info(f"Completed experiment {experiment_id}")

        return experiment

    async def assign_variant(
        self,
        experiment_id: str,
        user_id: str,
    ) -> tuple[ABExperimentVariant, bool]:
        """
        Assign user to a variant (deterministic).

        Args:
            experiment_id: Experiment ID
            user_id: User ID

        Returns:
            Tuple of (variant, is_new_assignment)
        """
        # Check if already assigned
        assignment = await self.db.execute(
            select(ABExperimentAssignment).where(
                and_(
                    ABExperimentAssignment.experiment_id == experiment_id,
                    ABExperimentAssignment.user_id == user_id,
                    not ABExperimentAssignment.is_excluded,
                )
            )
        )
        existing = assignment.scalar_one_or_none()

        if existing:
            # Load variant
            variant = await self.db.get(ABExperimentVariant, existing.variant_id)
            return variant, False

        # Get variants
        variants_result = await self.db.execute(
            select(ABExperimentVariant).where(
                ABExperimentVariant.experiment_id == experiment_id
            ).order_by(ABExperimentVariant.created_at.asc())
        )
        variants = variants_result.scalars().all()

        if not variants:
            raise ValueError(f"No variants found for experiment {experiment_id}")

        # Deterministic assignment based on hash
        digest = hashlib.sha256(f"{user_id}:{experiment_id}".encode()).hexdigest()
        hash_val = int(digest, 16) % 10000
        cumulative = 0

        for variant in variants:
            cumulative += variant.traffic_allocation_percentage * 100
            if hash_val < cumulative:
                assigned_variant = variant
                break
        else:
            # Fallback to control variant
            control_variant = next((v for v in variants if v.is_control), variants[0])
            assigned_variant = control_variant

        # Record assignment
        assignment = ABExperimentAssignment(
            experiment_id=experiment_id,
            user_id=user_id,
            variant_id=assigned_variant.id,
            assignment_date=_utcnow(),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(assignment)
        await self.db.commit()

        logger.debug(f"Assigned user {user_id} to variant {assigned_variant.variant_name}")
        return assigned_variant, True

    async def record_metric(
        self,
        experiment_id: str,
        variant_id: str,
        metric_name: str,
        metric_value: float,
        metric_type: str,
        user_id: str | None = None,
        context_data: dict | None = None,
    ):
        """
        Record a metric for an experiment variant.

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID
            metric_name: Metric name
            metric_value: Metric value
            metric_type: Metric type (success, latency, engagement, etc.)
            user_id: User ID (optional)
            context_data: Additional context (optional)
        """
        metric = ABExperimentMetric(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_type=metric_type,
            context_data=context_data,
            timestamp=_utcnow(),
            created_at=_utcnow(),
        )
        self.db.add(metric)
        await self.db.commit()

        logger.debug(
            f"Recorded metric {metric_name}={metric_value} for variant {variant_id}"
        )

    async def get_experiment_stats(self, experiment_id: str) -> dict:
        """
        Get aggregate statistics for an experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Dict with statistics by variant
        """
        # Get experiment with variants
        experiment = await self.db.get(
            ABExperiment,
            experiment_id,
            options=[selectinload(ABExperiment.variants)]
        )

        if not experiment:
            return None

        stats = {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "status": experiment.status,
            "start_date": experiment.start_date.isoformat() if experiment.start_date else None,
            "sample_size_target": experiment.sample_size_target,
            "sample_size_collected": 0,
            "variants": [],
        }

        total_sample_size = 0

        for variant in experiment.variants:
            # Get metrics for this variant
            metrics_result = await self.db.execute(
                select(
                    func.count(ABExperimentMetric.id).label("count"),
                    func.avg(
                        case(
                            (ABExperimentMetric.metric_name == "success", ABExperimentMetric.metric_value),
                            else_=0
                        )
                    ).label("success_rate"),
                    func.avg(
                        case(
                            (ABExperimentMetric.metric_name == "latency", ABExperimentMetric.metric_value),
                            else_=None
                        )
                    ).label("avg_latency"),
                ).where(
                    and_(
                        ABExperimentMetric.experiment_id == experiment_id,
                        ABExperimentMetric.variant_id == variant.id,
                    )
                )
            )
            row = metrics_result.one()

            variant_stats = {
                "variant_id": str(variant.id),
                "variant_name": variant.variant_name,
                "is_control": variant.is_control,
                "sample_size": row.count or 0,
                "success_rate": float(row.success_rate or 0),
                "avg_latency": float(row.avg_latency or 0),
            }

            total_sample_size += row.count or 0
            stats["variants"].append(variant_stats)

        stats["sample_size_collected"] = total_sample_size
        stats["completion_percentage"] = (
            (total_sample_size / experiment.sample_size_target * 100)
            if experiment.sample_size_target and experiment.sample_size_target > 0
            else 0
        )

        return stats

    async def list_experiments(
        self,
        status: ExperimentStatus | None = None,
        created_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ABExperiment]:
        """
        List experiments with optional filtering.

        Args:
            status: Filter by status (optional)
            created_by: Filter by creator (optional)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of experiments
        """
        query = select(ABExperiment).order_by(ABExperiment.created_at.desc())

        if status:
            query = query.where(ABExperiment.status == status)

        if created_by:
            query = query.where(ABExperiment.created_by == created_by)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _cache_experiment_config(self, experiment: ABExperiment, variants: list[dict]):
        """Cache experiment config in Redis for fast access."""
        import json

        config = {
            "experiment_id": str(experiment.id),
            "name": experiment.name,
            "variants": [v["name"] for v in variants],
            "traffic_split": {
                v["name"]: v.get("weight", 1.0) for v in variants
            },
            "status": experiment.status,
            "significance_level": experiment.significance_level,
            "power": experiment.power,
        }

        redis_key = f"ab_experiment:{experiment.id}"
        await self.redis.set(redis_key, json.dumps(config), ex=86400 * 7)  # 7 days TTL


# Import case for SQL
from sqlalchemy import case
