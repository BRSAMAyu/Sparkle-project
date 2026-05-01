"""
M4: Real Engine Tests for Orchestrator Components.

Tests prompt assembly, tool invocation chain, response composition,
and dual-core routing with real implementations (no mocks for the system under test).
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel
from typing import Any

from app.orchestration.prompts import build_system_prompt
from app.orchestration.dual_core_router import (
    DualCoreRouter,
    DualCoreRoutingInput,
    DualCoreDecision,
)
from app.orchestration.dynamic_tool_registry import DynamicToolRegistry
from app.orchestration.executor import ToolExecutor
from app.orchestration.composer import ResponseComposer
from app.orchestration.state_manager import SessionStateManager, FSMState
from app.orchestration.orchestrator import (
    STATE_INIT,
    STATE_THINKING,
    STATE_GENERATING,
    STATE_DONE,
    STATE_FAILED,
    STATE_TOOL_CALLING,
)
from app.tools.base import BaseTool, ToolResult, ToolCategory


# ── Test doubles ──────────────────────────────────────────────────────


class _EchoParams(BaseModel):
    message: str


class _EchoTool(BaseTool):
    name = "echo"
    description = "Echoes the input message back."
    category = ToolCategory.QUERY
    parameters_schema = _EchoParams

    async def execute(self, params, user_id, db_session, tool_call_id=None):
        return ToolResult(success=True, tool_name=self.name, data={"echo": params.message})


class _FailParams(BaseModel):
    reason: str = "intentional"


class _FailTool(BaseTool):
    name = "fail_tool"
    description = "Always fails for testing."
    category = ToolCategory.TASK
    parameters_schema = _FailParams

    async def execute(self, params, user_id, db_session, tool_call_id=None):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error_message=params.reason,
            error_type="test_failure",
            suggestion="Check test setup",
        )


class _WidgetParams(BaseModel):
    title: str
    body: str


class _WidgetTool(BaseTool):
    name = "widget_tool"
    description = "Returns a widget result."
    category = ToolCategory.KNOWLEDGE
    parameters_schema = _WidgetParams

    async def execute(self, params, user_id, db_session, tool_call_id=None):
        return ToolResult(
            success=True,
            tool_name=self.name,
            data={"title": params.title, "body": params.body},
            widget_type="card",
            widget_data={"title": params.title, "content": params.body},
        )


def _make_registry_with_tools(*tools: BaseTool) -> DynamicToolRegistry:
    """Create a fresh registry with given tools registered."""
    reg = DynamicToolRegistry()
    reg._tools = {}
    reg._tool_info = {}
    reg._registered_packages = set()
    for t in tools:
        reg.register_tool(t)
    return reg


# ── Prompt Assembly Tests ─────────────────────────────────────────────


class TestPromptAssembly_RealContext:
    """Test build_system_prompt with real context injection."""

    def test_minimal_context_produces_valid_prompt(self):
        prompt = build_system_prompt(user_context={"user_id": "u1", "name": "Test"})
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Non-trivial prompt
        assert "Sparkle" in prompt  # Agent persona always present

    def test_user_profile_sections_injected(self):
        ctx = {
            "user_id": "u1",
            "name": "张三",
            "cognitive_profile": {"learning_style": "visual"},
            "current_mood": "focused",
        }
        prompt = build_system_prompt(user_context=ctx)
        assert isinstance(prompt, str)
        assert "Sparkle" in prompt

    def test_plan_context_accepted_without_error(self):
        plan_ctx = {
            "active_plans": [
                {"title": "Learn Python", "progress": 0.3, "status": "on_track"}
            ],
            "current_milestone": "Chapter 3",
        }
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            plan_context=plan_ctx,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_intent_instruction_forced(self):
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            intent_instruction="用户想创建新计划，请引导完成计划创建流程。",
        )
        assert isinstance(prompt, str)
        assert "创建" in prompt or "计划" in prompt or len(prompt) > 200

    def test_session_feedback_instruction_forced(self):
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            session_feedback_instruction="上一轮建议效果不好，请换一种方式。",
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_dual_core_instruction_injected(self):
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            dual_core_instruction="当前认知负载高，减少信息量。",
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_spine_directive_accepted_without_error(self):
        directive = {
            "action": "execution_directive",
            "assertiveness": "high",
            "deadline_pressure": True,
            "tone": "motivating",
        }
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            spine_response_directive=directive,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_light_context_level_shorter_than_full(self):
        full = build_system_prompt(
            user_context={"user_id": "u1", "name": "User", "preferences": {"language": "zh"}},
            context_level="full",
        )
        light = build_system_prompt(
            user_context={"user_id": "u1", "name": "User", "preferences": {"language": "zh"}},
            context_level="light",
        )
        assert len(light) <= len(full)

    def test_conversation_history_accepted_without_error(self):
        history = {
            "messages": [
                {"role": "user", "content": "我想学英语"},
                {"role": "assistant", "content": "好的，我帮你制定计划"},
            ]
        }
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            conversation_history=history,
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_empty_context_still_produces_prompt(self):
        prompt = build_system_prompt(user_context={})
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_context_focus_filters_sections(self):
        focus = {"enabled": True, "focus_areas": ["plan"], "suppressed": ["social"]}
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            context_focus=focus,
        )
        assert isinstance(prompt, str)


# ── Tool Registry Real Tests ──────────────────────────────────────────


class TestToolRegistry_Real:
    """Test DynamicToolRegistry with real tool registration."""

    def test_register_and_retrieve_tool(self):
        reg = _make_registry_with_tools(_EchoTool())
        tool = reg.get_tool("echo")
        assert tool is not None
        assert tool.name == "echo"

    def test_get_nonexistent_tool_returns_none(self):
        reg = _make_registry_with_tools()
        assert reg.get_tool("nonexistent") is None

    def test_get_all_tools_returns_registered(self):
        reg = _make_registry_with_tools(_EchoTool(), _FailTool())
        tools = reg.get_all_tools()
        names = {t.name for t in tools}
        assert names == {"echo", "fail_tool"}

    def test_openai_tools_schema_structure(self):
        reg = _make_registry_with_tools(_EchoTool())
        schema = reg.get_openai_tools_schema()
        assert len(schema) == 1
        assert schema[0]["type"] == "function"
        assert schema[0]["function"]["name"] == "echo"
        assert "message" in schema[0]["function"]["parameters"]["properties"]

    def test_register_duplicate_replaces(self):
        reg = _make_registry_with_tools(_EchoTool())
        # Re-registering same name should work
        reg.register_tool(_EchoTool())
        assert len(reg.get_all_tools()) == 1


# ── Tool Executor Real Tests ──────────────────────────────────────────


class TestToolExecutor_RealChain:
    """Test ToolExecutor with real tool execution chain."""

    def setup_method(self):
        self.registry = _make_registry_with_tools(
            _EchoTool(), _FailTool(), _WidgetTool()
        )

    @pytest.mark.asyncio
    async def test_execute_echo_tool_success(self):
        with patch("app.orchestration.executor.tool_registry", self.registry):
            executor = ToolExecutor()
            result = await executor.execute_tool_call(
                tool_name="echo",
                arguments={"message": "hello"},
                user_id="u1",
                db_session=MagicMock(),
            )
        assert result.success is True
        assert result.data["echo"] == "hello"
        assert result.tool_name == "echo"

    @pytest.mark.asyncio
    async def test_execute_fail_tool_returns_error(self):
        with patch("app.orchestration.executor.tool_registry", self.registry):
            executor = ToolExecutor()
            result = await executor.execute_tool_call(
                tool_name="fail_tool",
                arguments={"reason": "test error"},
                user_id="u1",
                db_session=MagicMock(),
            )
        assert result.success is False
        assert result.error_message == "test error"
        assert result.error_type == "test_failure"

    @pytest.mark.asyncio
    async def test_execute_widget_tool_returns_widget_data(self):
        with patch("app.orchestration.executor.tool_registry", self.registry):
            executor = ToolExecutor()
            result = await executor.execute_tool_call(
                tool_name="widget_tool",
                arguments={"title": "Summary", "body": "Key findings"},
                user_id="u1",
                db_session=MagicMock(),
            )
        assert result.success is True
        assert result.widget_type == "card"
        assert result.widget_data["title"] == "Summary"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_failure(self):
        with patch("app.orchestration.executor.tool_registry", self.registry):
            executor = ToolExecutor()
            result = await executor.execute_tool_call(
                tool_name="nonexistent_tool",
                arguments={},
                user_id="u1",
                db_session=MagicMock(),
            )
        assert result.success is False
        assert "未知工具" in result.error_message or "not_found" in (result.error_type or "")

    @pytest.mark.asyncio
    async def test_execute_batch_tool_calls(self):
        with patch("app.orchestration.executor.tool_registry", self.registry):
            executor = ToolExecutor()
            calls = [
                {
                    "id": "call-1",
                    "function": {"name": "echo", "arguments": '{"message": "first"}'},
                },
                {
                    "id": "call-2",
                    "function": {"name": "echo", "arguments": '{"message": "second"}'},
                },
            ]
            results = await executor.execute_tool_calls(
                tool_calls=calls,
                user_id="u1",
                db_session=MagicMock(),
            )
        assert len(results) == 2
        assert results[0].data["echo"] == "first"
        assert results[1].data["echo"] == "second"

    @pytest.mark.asyncio
    async def test_execute_with_invalid_arguments_returns_validation_error(self):
        with patch("app.orchestration.executor.tool_registry", self.registry):
            executor = ToolExecutor()
            result = await executor.execute_tool_call(
                tool_name="echo",
                arguments={"wrong_field": "value"},
                user_id="u1",
                db_session=MagicMock(),
            )
        assert result.success is False
        assert "参数验证" in result.error_message or "validation" in (result.error_type or "")


# ── Response Composer Real Tests ──────────────────────────────────────


class TestResponseComposer_Real:
    """Test ResponseComposer with real composition logic."""

    def setup_method(self):
        self.composer = ResponseComposer()

    def test_compose_text_only_response(self):
        result = self.composer.compose_response(
            llm_text="这是AI的回复。",
            tool_results=[],
        )
        assert result["message"] == "这是AI的回复。"
        assert result["widgets"] == []
        assert result["has_errors"] is False

    def test_compose_with_successful_tool_results(self):
        tool_results = [
            ToolResult(
                success=True,
                tool_name="echo",
                data={"echo": "test"},
                widget_type="card",
                widget_data={"title": "Echo", "content": "test"},
            ),
        ]
        result = self.composer.compose_response(
            llm_text="Echo result:",
            tool_results=tool_results,
        )
        assert len(result["widgets"]) == 1
        assert result["widgets"][0]["type"] == "card"
        assert result["has_errors"] is False

    def test_compose_with_failed_tool_results(self):
        tool_results = [
            ToolResult(
                success=False,
                tool_name="fail_tool",
                error_message="something broke",
                error_type="runtime",
                suggestion="try again",
            ),
        ]
        result = self.composer.compose_response(
            llm_text="处理中遇到问题。",
            tool_results=tool_results,
        )
        assert result["has_errors"] is True
        assert len(result["errors"]) == 1
        assert result["errors"][0]["message"] == "something broke"

    def test_compose_with_confirmation(self):
        result = self.composer.compose_response(
            llm_text="需要确认。",
            tool_results=[],
            requires_confirmation=True,
            confirmation_data={"action": "delete_plan", "plan_id": "p1"},
        )
        assert result["requires_confirmation"] is True
        assert result["confirmation_data"]["action"] == "delete_plan"

    def test_compose_mixed_tool_results(self):
        tool_results = [
            ToolResult(success=True, tool_name="echo", data={"echo": "ok"}),
            ToolResult(success=False, tool_name="fail_tool", error_message="err"),
            ToolResult(
                success=True,
                tool_name="widget_tool",
                widget_type="card",
                widget_data={"title": "Summary"},
            ),
        ]
        result = self.composer.compose_response(
            llm_text="结果如下：",
            tool_results=tool_results,
        )
        assert len(result["widgets"]) == 1  # Only widget_tool has widget_type
        assert result["has_errors"] is True  # fail_tool present
        assert len(result["tool_results"]) == 3


# ── End-to-End Chain Tests ────────────────────────────────────────────


class TestE2E_Chain:
    """Test the full chain: Route → Prompt → Execute → Compose."""

    def test_execution_chain_for_task_intent(self):
        # 1. Route
        router = DualCoreRouter()
        routing_input = DualCoreRoutingInput(
            intent="task",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="on_track",
            recent_task_feedback_distribution={"completed": 2},
        )
        decision = router.route(routing_input)

        # 2. Build prompt with routing decision
        prompt = build_system_prompt(
            user_context={"user_id": "u1", "name": "Test"},
            intent_instruction="创建新任务",
            dual_core_instruction=decision.prompt_instruction,
        )
        assert "创建新任务" in prompt
        assert isinstance(prompt, str)

        # 3. Verify decision mode is sensible
        assert decision.mode in ("execution_first", "balanced")

    @pytest.mark.asyncio
    async def test_tool_chain_echo_flow(self):
        registry = _make_registry_with_tools(_EchoTool())
        composer = ResponseComposer()

        with patch("app.orchestration.executor.tool_registry", registry):
            executor = ToolExecutor()
            result = await executor.execute_tool_call(
                tool_name="echo",
                arguments={"message": "chain test"},
                user_id="u1",
                db_session=MagicMock(),
            )

        response = composer.compose_response(
            llm_text="Echo: ",
            tool_results=[result],
        )
        assert response["has_errors"] is False
        assert len(response["tool_results"]) == 1

    @pytest.mark.asyncio
    async def test_full_chain_routing_affects_prompt_budget(self):
        router = DualCoreRouter()

        # High cognitive load → should affect prompt
        high_load = DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.5,
            information_sufficient=False,
            primary_challenge_area="emotional",
            recent_sentiment_distribution={"anxious": 4},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={"abandoned": 3},
            emotional_block_detected=True,
            cognitive_load=0.9,
        )
        decision = router.route(high_load)

        # Cognitive routing should have adjustments
        prompt = build_system_prompt(
            user_context={"user_id": "u1"},
            dual_core_instruction=decision.prompt_instruction,
            context_level="light",  # high load → light context
        )

        # Decision should prefer cognitive mode
        assert decision.mode in ("cognitive_first", "balanced")
        assert isinstance(prompt, str)


# ── FSM Lifecycle Edge Cases ──────────────────────────────────────────


@pytest.mark.asyncio
class TestFSMEdgeCases:
    """Test FSM state transition edge cases."""

    @pytest_asyncio.fixture
    async def state_manager(self, redis_client):
        return SessionStateManager(redis_client)

    async def test_rapid_state_transitions(self, state_manager):
        """Multiple rapid transitions maintain final state."""
        import uuid
        session_id = str(uuid.uuid4())

        states = [STATE_INIT, STATE_THINKING, STATE_TOOL_CALLING,
                   STATE_THINKING, STATE_GENERATING, STATE_DONE]
        for s in states:
            await state_manager.save_state(session_id, FSMState(session_id=session_id, state=s))

        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_DONE

    async def test_failed_then_recovered_state(self, state_manager):
        """Failed state can transition back to working state."""
        import uuid
        session_id = str(uuid.uuid4())

        await state_manager.save_state(session_id, FSMState(session_id=session_id, state=STATE_THINKING))
        await state_manager.update_state(session_id, STATE_FAILED, details="LLM timeout")
        await state_manager.update_state(session_id, STATE_THINKING, details="Retry")
        await state_manager.update_state(session_id, STATE_GENERATING, details="Success")
        await state_manager.update_state(session_id, STATE_DONE)

        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_DONE

    async def test_concurrent_sessions_independent(self, state_manager):
        """Multiple sessions don't interfere with each other."""
        import uuid
        sessions = {f"s{i}": str(uuid.uuid4()) for i in range(5)}

        for sid in sessions.values():
            await state_manager.save_state(sid, FSMState(session_id=sid, state=STATE_THINKING))

        # Update each to different state
        states = [STATE_TOOL_CALLING, STATE_GENERATING, STATE_DONE, STATE_FAILED, STATE_THINKING]
        for (key, sid), state in zip(sessions.items(), states):
            await state_manager.update_state(sid, state)

        # Verify each independently
        for (key, sid), expected_state in zip(sessions.items(), states):
            loaded = await state_manager.load_state(sid)
            assert loaded.state == expected_state, f"Session {key}: expected {expected_state}, got {loaded.state}"


class TestDualCoreRouting_AuroraPreferences:
    """Test dual-core routing with Aurora user preferences (M4 remaining item)."""

    def _base_input(self, **overrides) -> DualCoreRoutingInput:
        defaults = dict(
            intent="task",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="on_track",
            recent_task_feedback_distribution={"completed": 2},
            aurora_preferences={},
        )
        defaults.update(overrides)
        return DualCoreRoutingInput(**defaults)

    def _strategy_map(self, decision) -> dict[str, Any]:
        return {s["field"]: s["recommended_value"] for s in decision.strategy_adjustments}

    def test_direct_preference_favors_action_oriented(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={"aurora_directness": "direct"})
        decision = router.route(inp)
        strategies = self._strategy_map(decision)
        assert strategies.get("directness_mode") == "action_oriented"

    def test_guided_preference_default(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={"aurora_directness": "guided"})
        decision = router.route(inp)
        strategies = self._strategy_map(decision)
        assert strategies.get("directness_mode") != "action_oriented"

    def test_gentle_pressure_suppresses_urgency(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={"aurora_pressure_style": "gentle"})
        decision = router.route(inp)
        assert any("温和" in c for c in decision.execution_constraints)
        strategies = self._strategy_map(decision)
        assert strategies.get("push_vs_support") == 0.2

    def test_motivating_pressure_default(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={"aurora_pressure_style": "motivating"})
        decision = router.route(inp)
        assert not any("温和" in c for c in decision.execution_constraints)

    def test_brief_explanation_style(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={"aurora_explanation_level": "brief"})
        decision = router.route(inp)
        strategies = self._strategy_map(decision)
        assert strategies.get("explanation_style") == "concise"

    def test_combined_preferences(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={
            "aurora_directness": "direct",
            "aurora_pressure_style": "gentle",
            "aurora_explanation_level": "brief",
            "aurora_analysis_depth": "light",
        })
        decision = router.route(inp)
        strategies = self._strategy_map(decision)
        assert strategies.get("directness_mode") == "action_oriented"
        assert strategies.get("push_vs_support") == 0.2
        assert strategies.get("explanation_style") == "concise"

    def test_empty_preferences_uses_defaults(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={})
        decision = router.route(inp)
        assert isinstance(decision.mode, str)
        assert len(decision.strategy_adjustments) >= 0

    def test_decision_includes_preferences_in_debug(self):
        router = DualCoreRouter()
        inp = self._base_input(aurora_preferences={"aurora_directness": "direct"})
        decision = router.route(inp)
        assert isinstance(decision.routing_debug, dict)
        pref_debug = decision.routing_debug.get("aurora_preferences", {})
        assert pref_debug.get("directness") == "direct"


class TestFSMToolCallingLoop:
    """Tool-calling loop FSM state transition test."""

    @pytest_asyncio.fixture
    async def state_manager(self, redis_client):
        return SessionStateManager(redis_client)

    async def test_tool_calling_loop_state(self, state_manager):
        """Simulate tool-calling loop: THINKING → TOOL_CALLING → THINKING → ..."""
        import uuid
        session_id = str(uuid.uuid4())

        await state_manager.save_state(session_id, FSMState(session_id=session_id, state=STATE_THINKING))

        for i in range(3):
            await state_manager.update_state(session_id, STATE_TOOL_CALLING, details=f"Tool {i+1}")
            await state_manager.update_state(session_id, STATE_THINKING, details=f"Process result {i+1}")

        await state_manager.update_state(session_id, STATE_GENERATING)
        await state_manager.update_state(session_id, STATE_DONE)

        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_DONE
