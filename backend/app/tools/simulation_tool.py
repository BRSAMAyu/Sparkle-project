from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.i18n import I18n
from app.services.simulation.scenario_templates import normalize_scenario_key
from app.services.simulation.seed_extractor import SeedExtractor
from app.services.simulation.simulation_engine import SimulationEngine
from app.tools.base import BaseTool, ToolCategory, ToolResult


class QuickSimulationParams(BaseModel):
    scenario_key: str = Field(default="study_group", description=I18n.t("simulation.scenario_key_desc", locale="zh"))
    seed_topic: str | None = Field(default=None, description=I18n.t("simulation.seed_topic_desc", locale="zh"))
    source_chat_session_id: str | None = Field(default=None, description=I18n.t("simulation.source_chat_session_desc", locale="zh"))


class QuickSimulationTool(BaseTool):
    name = "run_quick_simulation"
    description = I18n.t("simulation.tool_desc", locale="zh")
    category = ToolCategory.QUERY
    parameters_schema = QuickSimulationParams
    requires_confirmation = False

    async def execute(
        self,
        params: QuickSimulationParams,
        user_id: str,
        db_session,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            scenario_key = normalize_scenario_key(params.scenario_key)
            topic = await self._resolve_topic(
                raw_topic=(params.seed_topic or I18n.t("simulation.current_topic", locale="zh")).strip(),
                scenario_key=scenario_key,
                user_id=UUID(user_id),
                db_session=db_session,
            )
            engine = SimulationEngine(db_session)
            session = await engine.preview(
                topic=topic,
                scenario_key=scenario_key,
                user_id=UUID(user_id),
            )
            query = {
                "topic": session.topic,
                "scenario_key": scenario_key,
            }
            if params.source_chat_session_id:
                query["source_chat_session_id"] = params.source_chat_session_id

            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={
                    "session_id": session.id,
                    "scenario_key": session.scenario_key,
                    "topic": session.topic,
                    "participants": list(session.participants or []),
                    "round_preview": list(session.rounds or [])[:3],
                    "insight_summary": session.insight_summary,
                    "open_simulation": True,
                    "deep_link": f"/simulation?{urlencode(query)}",
                    "source_chat_session_id": params.source_chat_session_id,
                },
            )
        except ValueError as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(exc),
                error_type="invalid_simulation_scenario",
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=I18n.t("simulation.launch_failed", locale="zh", exc=exc),
                error_type="simulation_launch_failed",
            )

    async def _resolve_topic(
        self,
        *,
        raw_topic: str,
        scenario_key: str,
        user_id: UUID,
        db_session,
    ) -> str:
        topic = raw_topic.strip() or I18n.t("simulation.current_topic", locale="zh")
        if not self._looks_generic_prompt(topic):
            return topic

        seeds = await SeedExtractor(db_session).get_cached_or_generate(
            user_id,
            scenario_key=scenario_key,
            limit=1,
            allow_llm_refine=False,
        )
        if seeds and str(seeds[0].topic).strip():
            return str(seeds[0].topic).strip()
        return I18n.t("simulation.current_topic", locale="zh")

    @staticmethod
    def _looks_generic_prompt(topic: str) -> bool:
        normalized = topic.strip().lower()
        if not normalized:
            return True
        generic_markers = (
            "模拟一下学习场景",
            "学习场景",
            "帮我模拟",
            "我想模拟",
            "演练一下",
            "角色扮演",
            I18n.t("simulation.current_topic", locale="zh"),
        )
        return any(marker in normalized for marker in generic_markers)
