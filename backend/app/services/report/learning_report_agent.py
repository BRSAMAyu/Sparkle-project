from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.core.agent_persona import build_agent_persona
from app.core.agent_profiles import AgentRole, agent_profile_registry
from app.services.llm_fallback_utils import analysis_llm
from app.services.report.report_logger import ReportLogger
from app.services.report.report_templates import DEFAULT_REPORT_SECTIONS
from app.services.report.report_tools import LearningReportTools
from app.services.system_update_service import SystemUpdateService, build_system_update


class LearningReportAgent:
    def __init__(self, db):
        self.db = db
        self.tools = LearningReportTools(db)
        self.logger = ReportLogger()

    async def generate_report(self, user_id: UUID, section_limit: int = 5) -> dict[str, Any]:
        report_id = str(uuid4())
        mastery = await self.tools.query_mastery_scores(user_id)
        patterns = await self.tools.query_error_patterns(user_id)
        timeline = await self.tools.query_study_timeline(user_id)
        learner_voice = await self.tools.interview_learner(user_id)

        sections = DEFAULT_REPORT_SECTIONS[: max(2, min(section_limit, 5))]
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
                "mastery": mastery,
                "patterns": patterns,
                "timeline": timeline,
                "learner_voice": learner_voice,
                "markdown": draft_markdown,
            },
        )
        self.logger.log_text(report_id, "Draft learning report generated.")

        reflection = await self._reflect_on_markdown(
            sections=sections,
            draft_markdown=draft_markdown,
            mastery=mastery,
            patterns=patterns,
            timeline=timeline,
        )
        self.logger.log_jsonl(report_id, {"stage": "reflection", "reflection": reflection})
        self.logger.log_text(report_id, f"Reflection pass completed. needs_revision={reflection.get('needs_revision')}.")

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
        }
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
        lines = [
            f"# {sections[0]}",
            f"近期最需要关注的知识点：{weak_text}。",
            "",
            "## 知识掌握度分析",
            f"当前掌握度最低的节点集中在：{weak_text}。",
            "",
            "## 薄弱点诊断",
            f"当前行为模式主要表现为：{pattern_text}。",
            "",
            "## 学习路径建议",
            str(learner_voice.get("learner_voice") or "建议先补前置，再进入高强度训练。"),
            "",
            "## 行动计划",
            f"- 先复盘 {weak_text}",
            "- 选 1 个节点做 20-30 分钟专项练习",
            f"- 复盘近期变化：{recent_text}",
        ]
        return "\n".join(lines)
