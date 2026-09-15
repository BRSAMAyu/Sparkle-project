"""
偏好 API - 预览和生效证明
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.db.session import get_db
from app.models.user import User
from app.services.personalization import get_personalization_engine

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferencePreviewRequest(BaseModel):
    preview_preferences: dict[str, Any]


class PreferencePreviewResponse(BaseModel):
    ai_sample: str
    push_sample: str
    task_summary: str
    effect_summary: str


@router.post("/preview", response_model=PreferencePreviewResponse)
async def preview_preference_effects(
    request: PreferencePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    预览偏好调整后的效果
    """
    engine = get_personalization_engine(db, cache_service.redis)

    llm_profile = await engine.get_llm_profile(
        current_user.id,
        override_preferences=request.preview_preferences
    )

    ai_sample = await _generate_ai_sample(llm_profile)
    push_sample = await _generate_push_sample(request.preview_preferences)

    task_profile = await engine.get_task_plan_profile(
        current_user.id,
        override_preferences=request.preview_preferences
    )
    task_summary = _generate_task_summary(task_profile)
    effect_summary = _generate_effect_summary(request.preview_preferences)

    return PreferencePreviewResponse(
        ai_sample=ai_sample,
        push_sample=push_sample,
        task_summary=task_summary,
        effect_summary=effect_summary,
    )


async def _generate_ai_sample(llm_profile) -> str:
    """生成 AI 回复示例"""
    from app.services.llm_fallback_utils import preferences_llm

    sample_question = "什么是机器学习？请简单介绍一下。"

    messages = [
        {"role": "system", "content": f"你是一个学习助手。{llm_profile.system_prompt_additions}"},
        {"role": "user", "content": sample_question},
    ]

    response = await preferences_llm.call(
        messages,
        fallback="[预览生成失败，请稍后重试]",
        temperature=llm_profile.temperature,
        max_tokens=200,
    )
    return response


async def _generate_push_sample(prefs: dict[str, Any]) -> str:
    """生成推送内容示例"""
    persona = prefs.get("persona_type", "coach")
    depth = prefs.get("depth_preference", 0.5)

    detail_level = "详细" if depth > 0.7 else ("简洁" if depth < 0.3 else "适中")

    persona_styles = {
        "coach": f"【严格教练风格 | {detail_level}】该复习「数据结构」了！你的掌握度只有 35%，不抓紧就要忘光了。",
        "anime": f"【可爱助手风格 | {detail_level}】主人~ 「数据结构」想你啦！(◕ᴗ◕✿) 掌握度 35%，一起来复习吧~",
        "mentor": f"【导师风格 | {detail_level}】根据遗忘曲线分析，「数据结构」已进入关键复习期。建议抽 15 分钟回顾核心概念。",
        "friend": f"【伙伴风格 | {detail_level}】嘿，「数据结构」有点生疏了，要不一起看看？不用太久，15 分钟就好。",
    }

    return persona_styles.get(persona, persona_styles["coach"])


def _generate_task_summary(profile) -> str:
    """生成任务推荐摘要"""
    return (
        f"推荐任务时长：{profile.preferred_task_duration} 分钟\n"
        f"难度梯度：{profile.difficulty_gradient:.0%}\n"
        f"探索任务比例：{profile.exploration_ratio:.0%}\n"
        f"复习优先级：{profile.review_priority}"
    )


def _generate_effect_summary(prefs: dict[str, Any]) -> str:
    """生成效果总结"""
    summaries: list[str] = []

    depth = prefs.get("depth_preference", 0.5)
    if depth > 0.7:
        summaries.append("AI 将提供详细深入的解答")
    elif depth < 0.3:
        summaries.append("AI 将提供简洁精炼的解答")

    curiosity = prefs.get("curiosity_preference", 0.5)
    if curiosity > 0.7:
        summaries.append("系统将主动推荐相关知识扩展")
    elif curiosity < 0.3:
        summaries.append("系统将专注于您当前的学习内容")

    persona = prefs.get("persona_type", "coach")
    persona_names = {
        "coach": "严格教练",
        "anime": "可爱助手",
        "mentor": "智慧导师",
        "friend": "友好伙伴"
    }
    summaries.append(f"AI 将以「{persona_names.get(persona, persona)}」的风格与您互动")

    return "；".join(summaries) + "。"


class DecisionRecord(BaseModel):
    timestamp: datetime
    module: str
    action: str
    preference_version: int
    outcome: str


class EffectivenessResponse(BaseModel):
    records: list[DecisionRecord]
    total_decisions: int
    modules_summary: dict[str, int]


@router.get("/effectiveness", response_model=EffectivenessResponse)
async def get_preference_effectiveness(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取偏好生效证明
    """
    from app.services.decision_record_service import DecisionRecordService

    service = DecisionRecordService(db)
    records = await service.get_recent_records(current_user.id, limit)

    modules_summary: dict[str, int] = {}
    for record in records:
        modules_summary[record.module] = modules_summary.get(record.module, 0) + 1

    return EffectivenessResponse(
        records=[
            DecisionRecord(
                timestamp=record.created_at,
                module=record.module,
                action=record.action,
                preference_version=record.preference_version,
                outcome=record.outcome or "",
            )
            for record in records
        ],
        total_decisions=len(records),
        modules_summary=modules_summary,
    )
