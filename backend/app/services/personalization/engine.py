"""
Personalization Engine - 偏好到策略的映射中心
"""
from typing import Optional, Dict
from uuid import UUID

from .preference_service import PreferenceService
from .profiles import LLMProfile, PushPolicyProfile, TaskPlanProfile
from .runtime_context_service import RuntimeContextService


class PersonalizationEngine:
    """
    个性化引擎 - 偏好到策略的映射中心

    设计原则：
    1. 显式偏好优先于推断偏好
    2. 运行时上下文可覆盖静态偏好
    3. 所有映射逻辑集中在此，避免各模块分散实现
    """

    def __init__(self, pref_service: PreferenceService, ctx_service: RuntimeContextService):
        self.pref_service = pref_service
        self.ctx_service = ctx_service

    async def get_llm_profile(
        self,
        user_id: UUID,
        session_context: Optional[Dict] = None,
        override_preferences: Optional[Dict] = None,
    ) -> LLMProfile:
        """生成 AI 系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()
        inferred = prefs.inferred or {}

        if override_preferences:
            explicit.update(override_preferences)

        # 显式未设置时，使用推断值
        depth = explicit.get("depth_preference")
        if depth is None:
            depth = inferred.get("depth_preference", 0.5)

        verbosity = "detailed" if depth > 0.7 else ("concise" if depth < 0.3 else "balanced")
        temperature = 0.3 + (depth * 0.4)

        curiosity = explicit.get("curiosity_preference")
        if curiosity is None:
            curiosity = inferred.get("curiosity_preference", 0.5)

        exploration = "exploratory" if curiosity > 0.7 else ("focused" if curiosity < 0.3 else "moderate")

        feedback_style = explicit.get("feedback_style", "balanced")
        tone = "playful" if feedback_style == "gentle" else "professional"

        persona = explicit.get("persona_type", "coach")
        persona_additions = self._get_persona_prompt_additions(persona)

        # 标记来源（用于调试）
        depth_source = "explicit" if explicit.get("depth_preference") is not None else "inferred"
        curiosity_source = "explicit" if explicit.get("curiosity_preference") is not None else "inferred"

        system_additions = f"""
## 用户偏好适配指令
- 回答详细程度：{verbosity}（depth_preference={depth:.2f} [source: {depth_source}]）
- 探索倾向：{exploration}（curiosity_preference={curiosity:.2f} [source: {curiosity_source}]）
- 语气风格：{tone}
{persona_additions}

根据用户偏好调整回答：
- 如果 verbosity=concise，控制在 3-5 句话内，直击要点
- 如果 verbosity=detailed，提供完整背景、示例和扩展内容
- 如果 exploration=exploratory，可以主动引入相关的有趣知识点
- 如果 exploration=focused，严格围绕用户问题，不发散
"""

        return LLMProfile(
            system_prompt_additions=system_additions,
            verbosity_target=verbosity,
            temperature=temperature,
            should_ask_clarifying=depth > 0.6,
            should_provide_examples=depth > 0.5,
            exploration_level=exploration,
            tone=tone,
        )

    async def get_push_policy_profile(
        self,
        user_id: UUID,
        override_preferences: Optional[Dict] = None,
    ) -> PushPolicyProfile:
        """生成推送系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()
        inferred = prefs.inferred or {}

        if override_preferences:
            explicit.update(override_preferences)

        timezone = explicit.get("timezone", "Asia/Shanghai")
        ctx = await self.ctx_service.get_runtime_context(user_id, timezone)

        daily_cap = explicit.get("daily_cap", 5)
        depth = explicit.get("depth_preference", 0.5)
        curiosity = explicit.get("curiosity_preference", 0.5)

        curiosity_freq = "high" if curiosity > 0.7 else ("low" if curiosity < 0.3 else "medium")

        consecutive_ignores = inferred.get("consecutive_ignores", 0)
        base_interval = 120
        min_interval = min(base_interval * (1 + consecutive_ignores * 0.5), 360)

        active_hours = []
        slots = explicit.get("active_slots", [])
        if isinstance(slots, dict):
            slots = slots.get("slots", [])
        current_dow = ctx.get("current_local_dow")
        for slot in slots:
            slot_dow = slot.get("dow")
            if slot_dow is not None and current_dow is not None:
                if isinstance(slot_dow, int):
                    slot_dow = [slot_dow]
                if isinstance(slot_dow, list) and slot_dow and current_dow not in slot_dow:
                    continue
            start = self._slot_to_minutes(slot, "start_min", "start", 480)
            end = self._slot_to_minutes(slot, "end_min", "end", 540)
            active_hours.extend(range(start, end))

        is_focusing = ctx.get("focus_session_active", False)

        return PushPolicyProfile(
            daily_cap=daily_cap,
            min_interval_minutes=int(min_interval),
            pressure_tolerance=depth,
            memory_urgency_threshold=0.3 if depth > 0.5 else 0.2,
            curiosity_frequency=curiosity_freq,
            silent_during_focus=is_focusing,
            active_hours=active_hours,
            timezone=timezone,
            preference_version=prefs.version,
        )

    async def get_task_plan_profile(
        self,
        user_id: UUID,
        override_preferences: Optional[Dict] = None,
    ) -> TaskPlanProfile:
        """生成任务规划策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()

        if override_preferences:
            explicit.update(override_preferences)

        focus_duration = explicit.get("focus_duration_preference", 25)
        depth = explicit.get("depth_preference", 0.5)
        curiosity = explicit.get("curiosity_preference", 0.5)

        difficulty_gradient = 0.3 + (depth * 0.5)
        exploration_ratio = curiosity * 0.4

        slots = explicit.get("active_slots", [])
        if isinstance(slots, dict):
            slots = slots.get("slots", [])
        fragmented = []
        for slot in slots:
            start = self._slot_to_minutes(slot, "start_min", "start", 480)
            end = self._slot_to_minutes(slot, "end_min", "end", 540)
            if end - start <= 30:
                normalized = dict(slot)
                normalized["start_min"] = start
                normalized["end_min"] = end
                fragmented.append(normalized)

        return TaskPlanProfile(
            preferred_task_duration=focus_duration,
            difficulty_gradient=difficulty_gradient,
            micro_task_friendly=len(fragmented) > 0,
            exploration_ratio=exploration_ratio,
            review_priority="high" if depth > 0.6 else ("medium" if depth > 0.3 else "low"),
            fragmented_time_slots=fragmented,
        )

    def _get_persona_prompt_additions(self, persona: str) -> str:
        """根据角色生成额外的 prompt 指令"""
        personas = {
            "coach": "- 角色：严格的学习教练，强调纪律和效率\n- 语气：直接、专业、有时略带督促",
            "anime": "- 角色：温柔可爱的二次元助手\n- 语气：甜美、鼓励、活泼，可以使用颜文字",
            "mentor": "- 角色：资深导师，提供深度指导\n- 语气：睿智、耐心、启发式提问",
            "friend": "- 角色：亲切的学习伙伴\n- 语气：轻松、友好、支持性",
        }
        return personas.get(persona, personas["coach"])

    @staticmethod
    def _slot_to_minutes(slot: Dict, min_key: str, fallback_key: str, default: int) -> int:
        value = slot.get(min_key)
        if value is None:
            value = slot.get(fallback_key, default)
        if isinstance(value, str) and ":" in value:
            parts = value.split(":")
            if len(parts) == 2:
                try:
                    return int(parts[0]) * 60 + int(parts[1])
                except Exception:
                    return default
        try:
            return int(value)
        except Exception:
            return default
