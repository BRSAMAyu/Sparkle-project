from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.core.agent_persona import build_agent_persona
from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.services.insight_copy import present_pattern_solution
from app.services.llm_fallback_utils import analysis_llm
from app.services.report.report_logger import ReportLogger
from app.services.report.report_templates import DEFAULT_REPORT_SECTIONS
from app.services.report.report_tools import LearningReportTools
from app.services.simulation.seed_extractor import SeedExtractor
from app.services.system_update_service import SystemUpdateService, build_system_update


class LearningReportAgent:
    def __init__(self, db):
        self.db = db
        self.tools = LearningReportTools(db)
        self.logger = ReportLogger()

    async def generate_report(
        self,
        user_id: UUID,
        section_limit: int = 5,
        *,
        delivery_mode: str = "full",
        trigger_source: str = "api",
    ) -> dict[str, Any]:
        report_id = str(uuid4())
        mastery = await self.tools.query_mastery_scores(user_id)
        patterns = await self.tools.query_error_patterns(user_id)
        timeline = await self.tools.query_study_timeline(user_id)
        learner_voice = await self.tools.interview_learner(user_id)
        chat_inference = await self.tools.infer_learning_state_from_chat(user_id)
        learner_voice = self._merge_chat_inference_into_learner_voice(learner_voice, chat_inference)
        starter_focus = await self._build_starter_focus(
            user_id=user_id,
            mastery=mastery,
            patterns=patterns,
            timeline=timeline,
            chat_inference=chat_inference,
        )
        mastery, patterns, timeline = self._hydrate_cold_start_inputs(
            mastery=mastery,
            patterns=patterns,
            timeline=timeline,
            starter_focus=starter_focus,
            chat_inference=chat_inference,
        )

        normalized_delivery_mode = self._normalize_delivery_mode(delivery_mode)
        max_sections = 4 if normalized_delivery_mode == "chat_bridge" else 5
        sections = DEFAULT_REPORT_SECTIONS[: max(2, min(section_limit, max_sections))]
        if self._should_use_fallback_draft(
            delivery_mode=normalized_delivery_mode,
            mastery=mastery,
            patterns=patterns,
            timeline=timeline,
        ):
            draft_markdown = self._fallback_markdown(
                sections,
                mastery,
                patterns,
                timeline,
                learner_voice,
            )
        else:
            draft_markdown = await self._compose_markdown(
                sections=sections,
                mastery=mastery,
                patterns=patterns,
                timeline=timeline,
                learner_voice=learner_voice,
            )
        self.logger.log_jsonl(
            report_id,
            {
                "stage": "draft",
                "sections": sections,
                "delivery_mode": normalized_delivery_mode,
                "mastery": mastery,
                "patterns": patterns,
                "timeline": timeline,
                "learner_voice": learner_voice,
                "markdown": draft_markdown,
            },
        )
        self.logger.log_text(report_id, "Draft learning report generated.")

        reflection = self._fallback_reflection(sections, mastery, patterns, timeline)
        if self._should_run_reflection(
            delivery_mode=normalized_delivery_mode,
            draft_markdown=draft_markdown,
            sections=sections,
            mastery=mastery,
            patterns=patterns,
            timeline=timeline,
        ):
            reflection = await self._reflect_on_markdown(
                sections=sections,
                draft_markdown=draft_markdown,
                mastery=mastery,
                patterns=patterns,
                timeline=timeline,
            )
            self.logger.log_jsonl(report_id, {"stage": "reflection", "reflection": reflection})
            self.logger.log_text(
                report_id,
                f"Reflection pass completed. needs_revision={reflection.get('needs_revision')}.",
            )
        else:
            reflection = {
                **reflection,
                "needs_revision": False,
                "revision_brief": "聊天桥接使用快速生成模式，当前报告已满足预览质量要求。",
            }
            self.logger.log_jsonl(report_id, {"stage": "reflection_skipped", "reflection": reflection})
            self.logger.log_text(report_id, "Reflection skipped for fast bridge delivery.")

        supplemental_context = await self._expand_context(user_id, reflection)
        if supplemental_context:
            self.logger.log_jsonl(report_id, {"stage": "requery", "supplemental_context": supplemental_context})
            self.logger.log_text(report_id, "Supplemental report context loaded.")

        markdown = draft_markdown
        if reflection.get("needs_revision"):
            markdown = await self._refine_markdown(
                sections=sections,
                draft_markdown=draft_markdown,
                reflection=reflection,
                learner_voice=learner_voice,
                supplemental_context=supplemental_context,
            )
            self.logger.log_text(report_id, "Report refined after reflection.")

        payload = {
            "report_id": report_id,
            "sections": sections,
            "markdown": markdown,
            "mastery": mastery,
            "patterns": patterns,
            "timeline": timeline,
            "reflection": reflection,
            "quality_mode": "instant_preview" if normalized_delivery_mode == "chat_bridge" else "full_analysis",
            "delivery_mode": normalized_delivery_mode,
            "deep_link": "/learning-report",
            "starter_focus": starter_focus,
            "chat_inference": chat_inference,
        }
        payload["report_preview"] = self._build_report_preview(payload)
        self.logger.log_jsonl(report_id, {"stage": "final", "payload": payload})
        self.logger.log_text(report_id, "Learning report generated successfully.")
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="learning_report_ready",
                category="learning_insight",
                title="学习分析报告已就绪",
                description="你可以查看最新的知识掌握度分析与行动建议。",
                priority="medium",
                metadata={
                    "report_id": report_id,
                    "title": "学习分析报告",
                    "deep_link": "/learning-report",
                    "report_payload": payload,
                    "report_preview": payload["report_preview"],
                    "quality_mode": payload["quality_mode"],
                    "delivery_mode": normalized_delivery_mode,
                    "trigger_source": trigger_source,
                },
            ),
        )
        return payload

    async def _compose_markdown(
        self,
        *,
        sections: list[str],
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        learner_voice: dict[str, Any],
    ) -> str:
        fallback = self._fallback_markdown(sections, mastery, patterns, timeline, learner_voice)
        persona_section = self._build_report_persona_section()
        data = await analysis_llm.json_call(
            [
                {"role": "system", "content": f"Return valid JSON with a single key markdown.\n{persona_section}"},
                {
                    "role": "user",
                    "content": (
                        f"Sections: {sections}\n"
                        f"Mastery: {mastery}\n"
                        f"Patterns: {patterns}\n"
                        f"Timeline: {timeline}\n"
                        f"Learner voice: {learner_voice}\n"
                        "Write a concise learning analysis report in Markdown."
                    ),
                },
            ],
            fallback={"markdown": fallback},
            temperature=0.3,
        )
        return str((data or {}).get("markdown") or fallback)

    async def _reflect_on_markdown(
        self,
        *,
        sections: list[str],
        draft_markdown: str,
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fallback = self._fallback_reflection(sections, mastery, patterns, timeline)
        persona_section = self._build_report_persona_section()
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return valid JSON with keys needs_revision, missing_sections, focus_areas, "
                        f"revision_brief, query_expansion. Be a strict reviewer of the draft report.\n{persona_section}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Expected sections: {sections}\n"
                        f"Draft markdown:\n{draft_markdown}\n"
                        f"Mastery data: {mastery}\n"
                        f"Error patterns: {patterns}\n"
                        f"Timeline: {timeline}\n"
                        "Check whether the report is missing evidence, weak-point prioritization, or a concrete action plan."
                    ),
                },
            ],
            fallback=fallback,
            temperature=0.2,
        )
        return {
            "needs_revision": bool((data or {}).get("needs_revision")),
            "missing_sections": [str(item) for item in list((data or {}).get("missing_sections") or []) if str(item).strip()],
            "focus_areas": [str(item) for item in list((data or {}).get("focus_areas") or []) if str(item).strip()],
            "revision_brief": str((data or {}).get("revision_brief") or fallback["revision_brief"]),
            "query_expansion": [str(item) for item in list((data or {}).get("query_expansion") or fallback["query_expansion"]) if str(item).strip()],
        }

    async def _expand_context(self, user_id: UUID, reflection: dict[str, Any]) -> dict[str, Any]:
        if not reflection.get("needs_revision"):
            return {}
        expanded_mastery = await self.tools.query_mastery_scores(user_id, limit=12)
        expanded_patterns = await self.tools.query_error_patterns(user_id, limit=8)
        expanded_timeline = await self.tools.query_study_timeline(user_id, limit=15)
        follow_up_voice = await self.tools.interview_learner(user_id)
        return {
            "mastery": expanded_mastery,
            "patterns": expanded_patterns,
            "timeline": expanded_timeline,
            "learner_voice": follow_up_voice,
        }

    async def _refine_markdown(
        self,
        *,
        sections: list[str],
        draft_markdown: str,
        reflection: dict[str, Any],
        learner_voice: dict[str, Any],
        supplemental_context: dict[str, Any],
    ) -> str:
        fallback = self._fallback_refined_markdown(draft_markdown, reflection, supplemental_context)
        persona_section = self._build_report_persona_section()
        data = await analysis_llm.json_call(
            [
                {"role": "system", "content": f"Return valid JSON with a single key markdown.\n{persona_section}"},
                {
                    "role": "user",
                    "content": (
                        f"Sections: {sections}\n"
                        f"Draft markdown:\n{draft_markdown}\n"
                        f"Reflection: {reflection}\n"
                        f"Learner voice: {learner_voice}\n"
                        f"Supplemental context: {supplemental_context}\n"
                        "Revise the report so it is more evidence-driven, points to weak prerequisites clearly, "
                        "and ends with a concrete next-step action plan."
                    ),
                },
            ],
            fallback={"markdown": fallback},
            temperature=0.25,
        )
        return str((data or {}).get("markdown") or fallback)

    def _build_report_persona_section(self) -> str:
        profile = agent_profile_registry.get_profile(AgentRole.GENERATION)
        persona = build_agent_persona(
            agent_role=AgentRole.GENERATION,
            user_context={},
            profile=profile,
        )
        return (
            "保持与你在日常对话中的导师语气一致，但报告仍需结构清晰、证据充分。\n"
            f"{persona.to_prompt_section()}"
        )

    @staticmethod
    def _normalize_delivery_mode(value: str | None) -> str:
        normalized = str(value or "full").strip().lower()
        if normalized in {"chat_bridge", "full"}:
            return normalized
        return "full"

    def _should_run_reflection(
        self,
        *,
        delivery_mode: str,
        draft_markdown: str,
        sections: list[str],
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
    ) -> bool:
        if not mastery and not timeline:
            return False
        if delivery_mode != "chat_bridge":
            return True
        heading_hits = sum(1 for section in sections[:3] if section in draft_markdown)
        evidence_points = int(bool(mastery)) + int(bool(patterns)) + int(bool(timeline))
        return len(draft_markdown.strip()) < 260 or heading_hits < 2 or evidence_points < 2

    def _should_use_fallback_draft(
        self,
        *,
        delivery_mode: str,
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
    ) -> bool:
        if delivery_mode != "chat_bridge":
            return not mastery and not timeline
        return True

    def _build_report_preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        mastery = list(payload.get("mastery") or [])
        patterns = list(payload.get("patterns") or [])
        sections = [str(item) for item in list(payload.get("sections") or []) if str(item).strip()]
        weak_nodes = [
            str(item.get("node_name") or "").strip()
            for item in mastery[:3]
            if isinstance(item, dict) and str(item.get("node_name") or "").strip()
        ]
        pattern_names = [
            str(item.get("pattern_name") or "").strip()
            for item in patterns[:2]
            if isinstance(item, dict) and str(item.get("pattern_name") or "").strip()
        ]
        summary = (
            f"优先关注 {weak_nodes[0]}，并结合最近学习记录补一轮针对性练习。"
            if weak_nodes
            else (
                f"当前最影响推进节奏的是 {pattern_names[0]}，建议先调整节奏再展开高强度学习。"
                if pattern_names
                else "已整理出一份学习状态速览，适合先看结论再展开细节。"
            )
        )
        highlights = weak_nodes or pattern_names or sections[:3]
        return {
            "report_id": str(payload.get("report_id") or ""),
            "markdown": str(payload.get("markdown") or ""),
            "sections": sections,
            "mastery": mastery,
            "summary": summary,
            "highlights": highlights,
        }

    def _fallback_reflection(
        self,
        sections: list[str],
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        missing_sections = [section for section in sections if section not in {"Executive Summary", "行动计划"}]
        needs_revision = bool(mastery or patterns or timeline)
        focus_areas: list[str] = []
        if mastery:
            focus_areas.append(f"更明确解释 {mastery[0]['node_name']} 的薄弱原因")
        if patterns:
            focus_areas.append(f"把 {patterns[0]['pattern_name']} 转成可执行建议")
        if timeline:
            focus_areas.append("结合最近学习记录补充趋势判断")
        return {
            "needs_revision": needs_revision,
            "missing_sections": missing_sections[:1],
            "focus_areas": focus_areas[:3],
            "revision_brief": "补充更多证据引用，并将建议改写成更具体的行动计划。",
            "query_expansion": ["mastery", "patterns", "timeline"],
        }

    def _fallback_refined_markdown(
        self,
        draft_markdown: str,
        reflection: dict[str, Any],
        supplemental_context: dict[str, Any],
    ) -> str:
        expanded_mastery = list(supplemental_context.get("mastery") or [])
        expanded_timeline = list(supplemental_context.get("timeline") or [])
        mastery_text = "、".join(item["node_name"] for item in expanded_mastery[:3]) or "暂无新增薄弱点"
        progress_text = "；".join(
            f"{item['node_name']} {float(item['mastery_delta'] or 0.0):+.1f}" for item in expanded_timeline[:3]
        ) or "暂无新增趋势数据"
        return (
            f"{draft_markdown}\n\n"
            "## 反思修订补充\n"
            f"- 修订重点：{reflection.get('revision_brief')}\n"
            f"- 需要优先回看的节点：{mastery_text}\n"
            f"- 最近趋势佐证：{progress_text}"
        )

    def _fallback_markdown(
        self,
        sections: list[str],
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        learner_voice: dict[str, Any],
    ) -> str:
        weak_text = "、".join(item["node_name"] for item in mastery[:3]) or "暂无明显薄弱点"
        pattern_text = "、".join(item["pattern_name"] for item in patterns[:3]) or "暂无显著模式"
        recent_text = "；".join(
            f"{item['node_name']} +{item['mastery_delta']:.1f}" for item in timeline[:3]
        ) or "暂无近期学习记录"
        primary_pattern = patterns[0] if patterns else {}
        primary_pattern_name = str(primary_pattern.get("pattern_name") or "").strip()
        primary_pattern_solution = present_pattern_solution(
            primary_pattern.get("raw_pattern_name") or primary_pattern_name,
            primary_pattern.get("solution_text"),
        )
        action_hint = primary_pattern_solution or (
            f"先针对 {primary_pattern_name} 做一次最小行动修正。"
            if primary_pattern_name
            else "先补前置薄弱点，再进入高强度训练。"
        )
        lines = [
            "# 学习分析报告",
            "## 总结速览",
            f"近期最需要关注的知识点：{weak_text}。",
            (
                f"当前最影响学习推进的模式是 {primary_pattern_name}。"
                if primary_pattern_name
                else f"当前最值得留意的学习模式包括：{pattern_text}。"
            ),
            "",
            "## 知识掌握度分析",
            f"当前需要优先回看的主题集中在：{weak_text}。",
            "",
            "## 薄弱点诊断",
            f"当前行为模式主要表现为：{pattern_text}。",
            "",
            "## 学习路径建议",
            str(learner_voice.get("learner_voice") or "建议先补前置，再进入高强度训练。"),
            "",
            "## 行动计划",
            f"- 先复盘 {weak_text}，确认最容易卡住的 1 个知识点或任务环节",
            f"- 立刻执行：{action_hint}",
            "- 选 1 个节点做 20-30 分钟专项练习，并记录这轮练习后的变化",
            f"- 复盘近期变化：{recent_text}",
        ]
        return "\n".join(lines)

    async def _build_starter_focus(
        self,
        *,
        user_id: UUID,
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        chat_inference: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if mastery or timeline:
            return []
        chat_topics = [str(item).strip() for item in list(chat_inference.get("topics") or []) if str(item).strip()]
        if chat_topics:
            evidence_text = "；".join(
                str(item).strip()
                for item in list(chat_inference.get("evidence") or [])[:2]
                if str(item).strip()
            ) or str(chat_inference.get("goal_summary") or "最近聊天里反复提到这个方向。").strip()
            friction = str(
                (list(chat_inference.get("frictions") or []) or ["先把第一步和关键卡点说清楚"])[0]
            ).strip()
            return [
                {
                    "topic": topic,
                    "context": f"最近聊天里，你多次提到这个方向：{evidence_text}",
                    "tension_point": friction,
                    "source_type": "chat_inference",
                    "source_ids": [],
                    "relevance_score": 0.76,
                    "suggested_scenario": "study_group",
                    "suggested_experts": ["学伴", "深度分析"],
                }
                for topic in chat_topics[:3]
            ]
        seeds = await SeedExtractor(self.db).extract_seeds(user_id, limit=3)
        return [seed.to_dict() for seed in seeds]

    def _hydrate_cold_start_inputs(
        self,
        *,
        mastery: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        starter_focus: list[dict[str, Any]],
        chat_inference: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        if not starter_focus:
            return mastery, patterns, timeline

        hydrated_mastery = list(mastery)
        if not hydrated_mastery:
            hydrated_mastery = [
                {
                    "node_name": str(item.get("topic") or "").strip(),
                    "mastery_score": 45.0,
                }
                for item in starter_focus
                if str(item.get("topic") or "").strip()
            ][:3]

        hydrated_patterns = list(patterns)
        if not hydrated_patterns:
            frictions = [
                str(item).strip()
                for item in list(chat_inference.get("frictions") or [])
                if str(item).strip()
            ]
            first_focus = starter_focus[0] if starter_focus else {}
            focus_label = str(first_focus.get("topic") or "当前学习方向").strip() or "当前学习方向"
            if frictions:
                hydrated_patterns = [
                    {
                        "pattern_name": "对话推断：起步与理解待收敛",
                        "raw_pattern_name": "chat_inferred_bootstrap_friction",
                        "confidence": 0.48,
                        "description": f"最近聊天里反复出现的信号是：{frictions[0]}。",
                        "solution_text": f"先围绕 {focus_label} 做一次低门槛试跑，把第一步和第一处卡点记录下来。",
                    }
                ]
            else:
                hydrated_patterns = [
                    {
                        "pattern_name": "学习基线尚在建立",
                        "raw_pattern_name": "baseline_building",
                        "confidence": 0.42,
                        "description": "当前历史样本不足，系统先根据你现在最值得启动的方向来生成一份起步期报告。",
                        "solution_text": f"先围绕 {focus_label} 完成一次 20-30 分钟的试跑，再回来对照这份报告做调整。",
                    }
                ]

        hydrated_timeline = list(timeline)
        if not hydrated_timeline:
            hydrated_timeline = [
                {
                    "node_name": str(item.get("topic") or "").strip(),
                    "study_minutes": 25,
                    "mastery_delta": 0.0,
                    "created_at": None,
                }
                for item in starter_focus
                if str(item.get("topic") or "").strip()
            ][:3]

        return hydrated_mastery, hydrated_patterns, hydrated_timeline

    def _merge_chat_inference_into_learner_voice(
        self,
        learner_voice: dict[str, Any],
        chat_inference: dict[str, Any],
    ) -> dict[str, Any]:
        if not chat_inference:
            return learner_voice
        merged = dict(learner_voice)
        parts = [str(merged.get("learner_voice") or "").strip()]
        goal_summary = str(chat_inference.get("goal_summary") or "").strip()
        frictions = [str(item).strip() for item in list(chat_inference.get("frictions") or []) if str(item).strip()]
        if goal_summary:
            parts.append(f"最近聊天里，你最在意的是：{goal_summary}。")
        if frictions:
            parts.append(f"当前更像是 {frictions[0]}。")
        merged["learner_voice"] = " ".join(part for part in parts if part).strip()
        merged["chat_inference"] = chat_inference
        return merged
