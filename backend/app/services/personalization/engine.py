"""
Personalization Engine - 偏好到策略的映射中心
"""
from uuid import UUID

from app.core.profile_context import ProfileContext

from .preference_service import PreferenceService
from .profiles import LLMProfile, PolicyExplanation, PushPolicyProfile, TaskPlanProfile
from .runtime_context_service import RuntimeContextService


def _as_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


class PersonalizationEngine:
    """
    个性化引擎 - 偏好到策略的映射中心

    设计原则：
    1. 显式偏好优先于推断偏好
    2. 运行时上下文可覆盖静态偏好
    3. 所有映射逻辑集中在此，避免各模块分散实现
    """

    def __init__(
        self,
        pref_service: PreferenceService,
        ctx_service: RuntimeContextService,
        profile_context_service=None,
    ):
        self.pref_service = pref_service
        self.ctx_service = ctx_service
        self.profile_context_service = profile_context_service

    async def get_llm_profile(
        self,
        user_id: UUID,
        session_context: dict | None = None,
        override_preferences: dict | None = None,
        profile_context: ProfileContext | None = None,
    ) -> LLMProfile:
        """生成 AI 系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()
        inferred = prefs.inferred or {}

        resolved_context = await self._resolve_profile_context(user_id, profile_context)
        if resolved_context:
            explicit = resolved_context.preferences.copy()

        if override_preferences:
            explicit.update(override_preferences)

        # 显式未设置时，使用推断值
        depth = explicit.get("depth_preference")
        if depth is None or prefs.last_explicit_update is None:
            depth = explicit.get(
                "depth_preference_signal",
                inferred.get("depth_preference_signal", inferred.get("depth_preference", 0.5)),
            )

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
        depth_source = (
            "explicit"
            if explicit.get("depth_preference") is not None and prefs.last_explicit_update is not None
            else "inferred"
        )
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
        error_density = inferred.get("error_density_score")
        applied_policies: list[PolicyExplanation] = []
        if isinstance(error_density, (int, float)) and error_density >= 0.7:
            system_additions += "\n- 用户近期错题密度较高，请放慢节奏，确认理解后再推进。"
            applied_policies.append(
                PolicyExplanation(
                    signal="llm.pacing.slow_down_for_error_density",
                    effect="The assistant slows the pace and verifies understanding before moving forward.",
                    source_pattern="error_book",
                )
            )
        if explicit.get("preferred_expansion_depth", inferred.get("preferred_expansion_depth")) == "shallow":
            system_additions += "\n- 当扩展相关知识时，优先给出核心结论，避免展开过多旁支细节。"
            applied_policies.append(
                PolicyExplanation(
                    signal="llm.expansion.reduce_detail",
                    effect="Knowledge expansions are kept concise because recent expansion feedback prefers shallower depth.",
                    source_pattern="galaxy_feedback",
                )
            )
        streak_consistency = _as_float(explicit.get("streak_consistency", inferred.get("streak_consistency")))
        motivation_type = explicit.get("motivation_type", inferred.get("motivation_type"))
        if streak_consistency is not None and streak_consistency >= 0.8:
            system_additions += "\n- 用户近期保持了很强的连续性，请在反馈中明确肯定这种坚持。"
            applied_policies.append(
                PolicyExplanation(
                    signal="llm.motivation.praise_consistency",
                    effect="Responses explicitly acknowledge the user's recent consistency streak.",
                    source_pattern="streak_stats",
                )
            )
        elif motivation_type == "streak_driven":
            system_additions += "\n- 用户对连续性反馈较敏感，适度强调今天继续完成的小闭环。"
            applied_policies.append(
                PolicyExplanation(
                    signal="llm.motivation.protect_streak",
                    effect="Responses frame progress in a way that helps preserve the user's study streak.",
                    source_pattern="streak_stats",
                )
            )
        if explicit.get("task_reflection_depth", inferred.get("task_reflection_depth")) == "deep":
            system_additions += "\n- 用户愿意做较深的任务反思，可适度鼓励其继续总结原因与下一步改进。"
            applied_policies.append(
                PolicyExplanation(
                    signal="llm.reflection.encourage_depth",
                    effect="Responses encourage the user to keep up their deeper task reflections.",
                    source_pattern="task_feedback",
                )
            )
        policy_signals = self._collect_policy_signals(resolved_context)
        signal_sources = self._collect_policy_signal_sources(resolved_context)
        policy_instructions = self._build_llm_policy_instructions(policy_signals)
        if policy_instructions:
            system_additions += f"\n## 行为策略适配\n{policy_instructions}\n"
        applied_policies.extend(self._build_policy_explanations("llm", policy_signals, signal_sources))

        return LLMProfile(
            system_prompt_additions=system_additions,
            verbosity_target=verbosity,
            temperature=temperature,
            should_ask_clarifying=depth > 0.6,
            should_provide_examples=depth > 0.5,
            exploration_level=exploration,
            tone=tone,
            applied_policies=applied_policies,
        )

    async def get_push_policy_profile(
        self,
        user_id: UUID,
        override_preferences: dict | None = None,
        profile_context: ProfileContext | None = None,
    ) -> PushPolicyProfile:
        """生成推送系统策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()
        inferred = prefs.inferred or {}

        resolved_context = await self._resolve_profile_context(user_id, profile_context)
        if resolved_context:
            explicit = resolved_context.preferences.copy()

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

        # 优先从 schedule_preferences 读取周日程表（168格格式）
        active_hours = []
        schedule_prefs = explicit.get("schedule_preferences")
        if schedule_prefs and isinstance(schedule_prefs, dict) and "grid" in schedule_prefs:
            from app.utils.schedule_converter import weekly_grid_to_weekly_active_hours

            grid = schedule_prefs.get("grid")
            if grid and isinstance(grid, list) and len(grid) == 168:
                active_hours = weekly_grid_to_weekly_active_hours(grid, timezone)

        # 如果没有 schedule_preferences 或解析失败，回退到 active_slots
        if not active_hours:
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

        chat_active_hours = inferred.get("chat_active_hours")
        if not active_hours and isinstance(chat_active_hours, list) and chat_active_hours:
            active_hours = self._expand_hours_to_minutes(chat_active_hours)

        push_receptivity = explicit.get("push_receptivity", inferred.get("push_receptivity"))
        applied_policies: list[PolicyExplanation] = []
        if isinstance(push_receptivity, (int, float)) and push_receptivity < 0.3:
            daily_cap = max(1, int(daily_cap * max(0.1, float(push_receptivity))))
            applied_policies.append(
                PolicyExplanation(
                    signal="push.frequency.reduce_for_low_receptivity",
                    effect=f"Daily push cap was reduced to {daily_cap} because recent push receptivity is low.",
                    source_pattern="push_feedback",
                )
            )

        community_engagement = inferred.get("community_engagement_level")
        if community_engagement == "passive":
            daily_cap = max(1, int(daily_cap * 0.85))
            applied_policies.append(
                PolicyExplanation(
                    signal="push.community.reduce_frequency",
                    effect="Community-related push pressure was reduced because community engagement is currently passive.",
                    source_pattern="community",
                )
            )
        streak_consistency = _as_float(explicit.get("streak_consistency", inferred.get("streak_consistency")))
        motivation_type = explicit.get("motivation_type", inferred.get("motivation_type"))
        if motivation_type == "streak_driven" and streak_consistency is not None and streak_consistency < 0.85:
            min_interval = max(30, int(min_interval * 0.85))
            applied_policies.append(
                PolicyExplanation(
                    signal="push.streak.send_recovery_reminders",
                    effect="Reminder spacing was tightened slightly to reduce the risk of breaking your current study streak.",
                    source_pattern="streak_stats",
                )
            )

        if explicit.get("curiosity_push_receptivity", inferred.get("curiosity_push_receptivity")) == "low":
            curiosity_freq = "low"
            applied_policies.append(
                PolicyExplanation(
                    signal="push.curiosity.lower_frequency",
                    effect="Curiosity push frequency was forced to low because recent curiosity pushes were often ignored.",
                    source_pattern="push_feedback",
                )
            )

        inactive_hours = set()
        for hour in explicit.get("inactive_push_hours", inferred.get("inactive_push_hours")) or []:
            try:
                hour_int = int(hour)
            except (TypeError, ValueError):
                continue
            if 0 <= hour_int <= 23:
                inactive_hours.add(hour_int)
        for hour in inferred.get("peak_focus_hours") or []:
            try:
                hour_int = int(hour)
            except (TypeError, ValueError):
                continue
            if 0 <= hour_int <= 23:
                inactive_hours.add(hour_int)
        if inactive_hours:
            if not active_hours:
                active_hours = list(range(480, 1321))
            active_hours = [minute for minute in active_hours if (minute // 60) not in inactive_hours]

        is_focusing = ctx.get("focus_session_active", False)

        policy_signals = self._collect_policy_signals(resolved_context)
        signal_sources = self._collect_policy_signal_sources(resolved_context)
        if "push.timing.earlier_reminder" in policy_signals:
            min_interval = max(30, int(min_interval * 0.8))
        if inactive_hours:
            applied_policies.append(
                PolicyExplanation(
                    signal="push.timing.avoid_inactive_hours",
                    effect="Push active hours were trimmed to avoid hours where you often ignore pushes or focus deeply.",
                    source_pattern="push_feedback",
                )
            )
        applied_policies.extend(self._build_policy_explanations("push", policy_signals, signal_sources))

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
            applied_policies=applied_policies,
        )

    async def get_task_plan_profile(
        self,
        user_id: UUID,
        override_preferences: dict | None = None,
        profile_context: ProfileContext | None = None,
    ) -> TaskPlanProfile:
        """生成任务规划策略配置"""
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = prefs.explicit.copy()
        inferred = prefs.inferred or {}

        resolved_context = await self._resolve_profile_context(user_id, profile_context)
        if resolved_context:
            explicit = resolved_context.preferences.copy()

        if override_preferences:
            explicit.update(override_preferences)

        focus_duration = explicit.get("focus_duration_preference")
        if focus_duration is None or prefs.last_explicit_update is None:
            inferred_focus = explicit.get("preferred_focus_duration", inferred.get("preferred_focus_duration"))
            if isinstance(inferred_focus, (int, float)):
                focus_duration = int(inferred_focus)
        if focus_duration is None:
            focus_duration = 25
        depth = explicit.get("depth_preference", 0.5)
        curiosity = explicit.get("curiosity_preference", 0.5)

        difficulty_gradient = 0.3 + (depth * 0.5)
        exploration_ratio = curiosity * 0.4
        review_priority = "high" if depth > 0.6 else ("medium" if depth > 0.3 else "low")
        applied_policies: list[PolicyExplanation] = []

        recurring_tags = inferred.get("recurring_error_tags")
        if isinstance(recurring_tags, list) and recurring_tags:
            review_priority = "high"
            exploration_ratio = max(0.05, exploration_ratio * 0.7)
            applied_policies.append(
                PolicyExplanation(
                    signal="task.review.raise_priority_for_recurring_errors",
                    effect="Review priority was raised and exploration was reduced because recurring error tags were detected.",
                    source_pattern="error_book",
                )
            )
        if explicit.get("vocabulary_retention_style", inferred.get("vocabulary_retention_style")) == "passive":
            review_priority = "high"
            exploration_ratio = max(0.05, exploration_ratio * 0.7)
            applied_policies.append(
                PolicyExplanation(
                    signal="task.review.raise_priority_for_passive_retention",
                    effect="Review work was prioritized because active learning assets show a passive retention pattern.",
                    source_pattern="learning_assets",
                )
            )
        difficulty_accuracy = _as_float(explicit.get("task_difficulty_accuracy", inferred.get("task_difficulty_accuracy")))
        if difficulty_accuracy is not None and difficulty_accuracy > 0.5:
            focus_duration = max(5, int(focus_duration * 1.3))
            applied_policies.append(
                PolicyExplanation(
                    signal="task.time_estimate.add_buffer_for_low_accuracy",
                    effect="Task duration was padded because recent estimates have drifted far from actual time spent.",
                    source_pattern="task_feedback",
                )
            )

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

        policy_signals = self._collect_policy_signals(resolved_context)
        signal_sources = self._collect_policy_signal_sources(resolved_context)
        if "task.time_estimate.add_buffer_30pct" in policy_signals:
            focus_duration = max(5, int(focus_duration * 1.3))
        if "task.difficulty.start_easy" in policy_signals:
            difficulty_gradient = max(0.1, difficulty_gradient * 0.8)
        if "task.content.scaffold_prerequisites" in policy_signals:
            exploration_ratio = max(0.05, exploration_ratio * 0.7)
            review_priority = "high"
        if "plan.milestone.add_checkpoint" in policy_signals:
            review_priority = "high"
        applied_policies.extend(self._build_policy_explanations("task", policy_signals, signal_sources))

        return TaskPlanProfile(
            preferred_task_duration=focus_duration,
            difficulty_gradient=difficulty_gradient,
            micro_task_friendly=len(fragmented) > 0,
            exploration_ratio=exploration_ratio,
            review_priority=review_priority,
            fragmented_time_slots=fragmented,
            applied_policies=applied_policies,
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

    async def _resolve_profile_context(
        self,
        user_id: UUID,
        profile_context: ProfileContext | None,
    ) -> ProfileContext | None:
        if profile_context is not None:
            return profile_context
        try:
            if self.profile_context_service is not None:
                return await self.profile_context_service.get_profile_context(user_id)
            from app.services.profile_context_service import ProfileContextService

            service = ProfileContextService(self.pref_service.db, self.pref_service.redis)
            return await service.get_profile_context(user_id)
        except Exception:
            return None

    @staticmethod
    def _collect_policy_signals(profile_context: ProfileContext | None) -> list[str]:
        if not profile_context or not profile_context.cognitive_summary:
            return []
        signals: list[str] = []
        for pattern in profile_context.cognitive_summary.active_patterns:
            for signal in pattern.policy_signals:
                if signal and signal not in signals:
                    signals.append(signal)
        return signals

    @staticmethod
    def _collect_policy_signal_sources(profile_context: ProfileContext | None) -> dict[str, str]:
        if not profile_context or not profile_context.cognitive_summary:
            return {}
        signal_sources: dict[str, str] = {}
        for pattern in profile_context.cognitive_summary.active_patterns:
            for signal in pattern.policy_signals:
                if signal and signal not in signal_sources:
                    signal_sources[signal] = pattern.pattern_name
        return signal_sources

    @staticmethod
    def _expand_hours_to_minutes(hours: list[int]) -> list[int]:
        minutes: list[int] = []
        for raw in hours:
            try:
                hour = int(raw)
            except (TypeError, ValueError):
                continue
            if 0 <= hour <= 23:
                minutes.extend(range(hour * 60, (hour + 1) * 60))
        return minutes

    @staticmethod
    def _build_llm_policy_instructions(policy_signals: list[str]) -> str:
        instructions: list[str] = []
        if "llm.feedback.emphasize_progress" in policy_signals:
            instructions.append("- 在回复中优先肯定用户已取得的进步，避免过度纠错")
        if "llm.explanation.add_foundation" in policy_signals:
            instructions.append("- 解释时先补充必要的前置概念，不跳步骤")
        return "\n".join(instructions)

    @staticmethod
    def _build_policy_explanations(
        profile_kind: str,
        policy_signals: list[str],
        signal_sources: dict[str, str],
    ) -> list[PolicyExplanation]:
        effect_map = {
            "llm": {
                "llm.feedback.emphasize_progress": "Responses emphasize progress and reduce over-correction.",
                "llm.explanation.add_foundation": "Responses add prerequisite concepts before jumping ahead.",
            },
            "push": {
                "push.timing.earlier_reminder": "Reminder timing was moved earlier to reduce procrastination risk.",
            },
            "task": {
                "task.time_estimate.add_buffer_30pct": "Task duration estimates include a 30% buffer.",
                "task.difficulty.start_easy": "Task difficulty was softened to lower the start barrier.",
                "task.content.scaffold_prerequisites": "Task plans now scaffold prerequisite knowledge first.",
                "plan.milestone.add_checkpoint": "Plans include extra checkpoints to reduce execution drift.",
            },
        }
        explanations: list[PolicyExplanation] = []
        seen: set[str] = set()
        for signal in policy_signals:
            effect = effect_map.get(profile_kind, {}).get(signal)
            if not effect or signal in seen:
                continue
            explanations.append(
                PolicyExplanation(
                    signal=signal,
                    effect=effect,
                    source_pattern=signal_sources.get(signal, "behavior_pattern"),
                )
            )
            seen.add(signal)
        return explanations

    @staticmethod
    def _slot_to_minutes(slot: dict, min_key: str, fallback_key: str, default: int) -> int:
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


_PERSONALIZATION_CACHE: dict[str, dict[str, str]] = {}


def invalidate_personalization_cache(user_id: UUID | str) -> None:
    """Invalidate per-user personalization caches (if any are introduced)."""
    _PERSONALIZATION_CACHE.pop(str(user_id), None)
