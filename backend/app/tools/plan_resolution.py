from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan


class PlanResolutionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        suggestion: str | None = None,
        available_plan_names: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.suggestion = suggestion
        self.available_plan_names = available_plan_names or []


@dataclass(frozen=True)
class ResolvedPlanReference:
    plan_id: UUID
    plan_name: str
    resolution: str
    available_plan_names: list[str]


def _normalize_plan_ref(plan_ref: str | None) -> str:
    if not plan_ref:
        return ""
    return (
        plan_ref.strip()
        .strip('"')
        .strip("'")
        .replace("（", "(")
        .replace("）", ")")
    )


def _base_plan_query(user_id: UUID) -> Select[tuple[Plan]]:
    return (
        select(Plan)
        .where(
            Plan.user_id == user_id,
            Plan.deleted_at.is_(None),
        )
        .order_by(
            Plan.is_primary.desc(),
            Plan.is_active.desc(),
            Plan.updated_at.desc(),
            Plan.created_at.desc(),
        )
    )


async def _fetch_user_plans(
    db_session: AsyncSession,
    user_id: UUID,
) -> list[Plan]:
    result = await db_session.execute(_base_plan_query(user_id))
    return list(result.scalars().all())


def _fallback_plan(plans: list[Plan]) -> Plan | None:
    for plan in plans:
        if getattr(plan, "is_primary", False):
            return plan
    for plan in plans:
        if getattr(plan, "is_active", False):
            return plan
    return plans[0] if plans else None


async def resolve_user_plan_reference(
    db_session: AsyncSession,
    *,
    user_id: UUID,
    plan_ref: str | None,
) -> ResolvedPlanReference:
    normalized_ref = _normalize_plan_ref(plan_ref)
    plans = await _fetch_user_plans(db_session, user_id)
    available_plan_names = [plan.name for plan in plans if getattr(plan, "name", None)]

    if not plans:
        raise PlanResolutionError(
            "当前还没有可用的学习计划",
            suggestion="请先创建或激活一个计划后再查询任务与计划状态",
        )

    if normalized_ref:
        try:
            plan_uuid = UUID(normalized_ref)
        except ValueError:
            plan_uuid = None
        if plan_uuid is not None:
            matched = next((plan for plan in plans if plan.id == plan_uuid), None)
            if matched is None:
                raise PlanResolutionError(
                    f"未找到计划: {normalized_ref}",
                    suggestion="请检查计划 ID 是否正确，或直接使用计划名称查询",
                    available_plan_names=available_plan_names,
                )
            return ResolvedPlanReference(
                plan_id=matched.id,
                plan_name=matched.name,
                resolution="uuid",
                available_plan_names=available_plan_names,
            )

    lowered_ref = normalized_ref.casefold()
    if lowered_ref:
        exact_matches = [
            plan for plan in plans if plan.name and plan.name.casefold() == lowered_ref
        ]
        if len(exact_matches) == 1:
            matched = exact_matches[0]
            return ResolvedPlanReference(
                plan_id=matched.id,
                plan_name=matched.name,
                resolution="exact_name",
                available_plan_names=available_plan_names,
            )

        partial_matches = [
            plan for plan in plans if plan.name and lowered_ref in plan.name.casefold()
        ]
        if len(partial_matches) == 1:
            matched = partial_matches[0]
            return ResolvedPlanReference(
                plan_id=matched.id,
                plan_name=matched.name,
                resolution="partial_name",
                available_plan_names=available_plan_names,
            )

    fallback = _fallback_plan(plans)
    if fallback is not None:
        resolution = (
            "primary_fallback"
            if getattr(fallback, "is_primary", False)
            else "active_fallback"
            if getattr(fallback, "is_active", False)
            else "latest_fallback"
        )
        return ResolvedPlanReference(
            plan_id=fallback.id,
            plan_name=fallback.name,
            resolution=resolution,
            available_plan_names=available_plan_names,
        )

    raise PlanResolutionError(
        f"无法识别计划引用: {normalized_ref or '当前计划'}",
        suggestion="请提供计划名称，或先设置一个主计划",
        available_plan_names=available_plan_names,
    )
