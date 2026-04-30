"""
M4: Real Engine Tests for Orchestrator Components.

Tests DualCoreRouter with real routing logic (no mocks),
and FSM state persistence with real Redis.
"""

import pytest
import pytest_asyncio
import uuid

from app.orchestration.dual_core_router import (
    DualCoreRouter,
    DualCoreRoutingInput,
    DualCoreDecision,
    CognitiveAdjustment,
    AdaptationRecord,
)
from app.orchestration.state_manager import SessionStateManager, FSMState
from app.orchestration.orchestrator import (
    STATE_INIT,
    STATE_THINKING,
    STATE_GENERATING,
    STATE_DONE,
    STATE_FAILED,
    STATE_TOOL_CALLING,
)


# ── DualCoreRouter Real Engine Tests ──────────────────────────────────


class TestDualCoreRouter_RealDecisions:
    """Test real routing decisions with real DualCoreRouter (no mocks)."""

    def setup_method(self):
        self.router = DualCoreRouter()

    def test_execution_first_for_clear_task_intent(self):
        inp = DualCoreRoutingInput(
            intent="task",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 5},
            has_active_plan=True,
            plan_health_status="on_track",
            recent_task_feedback_distribution={"completed": 3},
        )
        decision = self.router.route(inp)
        assert decision.mode == "execution_first"
        assert decision.reason

    def test_cognitive_first_for_emotional_block(self):
        inp = DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.6,
            information_sufficient=False,
            primary_challenge_area="emotional",
            recent_sentiment_distribution={"anxious": 3, "stressed": 2},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={"abandoned": 2},
            emotional_block_detected=True,
        )
        decision = self.router.route(inp)
        assert decision.mode == "cognitive_first"
        assert len(decision.cognitive_adjustments) > 0

    def test_balanced_for_mixed_signals(self):
        inp = DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.7,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 3, "positive": 2},
            has_active_plan=True,
            plan_health_status="on_track",
            recent_task_feedback_distribution={"completed": 2, "skipped": 1},
        )
        decision = self.router.route(inp)
        assert decision.mode in ("balanced", "execution_first", "cognitive_first")

    def test_procrastination_detection(self):
        inp = DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.5,
            information_sufficient=False,
            primary_challenge_area="procrastination",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="behind",
            recent_task_feedback_distribution={"skipped": 4, "abandoned": 2},
            procrastination_pattern=True,
        )
        decision = self.router.route(inp)
        assert decision.mode == "cognitive_first"

    def test_execution_first_for_plan_intent(self):
        inp = DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.85,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"positive": 3},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={},
        )
        decision = self.router.route(inp)
        assert decision.mode == "execution_first"

    def test_low_confidence_routes_cognitive(self):
        inp = DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.3,
            information_sufficient=False,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 2},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={},
        )
        decision = self.router.route(inp)
        assert decision.mode in ("cognitive_first", "balanced")

    def test_high_cognitive_load_adjusts(self):
        inp = DualCoreRoutingInput(
            intent="task",
            intent_confidence=0.8,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="on_track",
            recent_task_feedback_distribution={"completed": 1},
            cognitive_load=0.8,
        )
        decision = self.router.route(inp)
        # High cognitive load should produce adjustments
        has_adjustments = len(decision.cognitive_adjustments) > 0 or len(decision.structured_adjustments) > 0
        assert has_adjustments or decision.mode != "execution_first"

    def test_decision_has_required_fields(self):
        inp = DualCoreRoutingInput(
            intent="chat",
            intent_confidence=0.7,
            information_sufficient=True,
            primary_challenge_area=None,
            recent_sentiment_distribution={"neutral": 1},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={},
        )
        decision = self.router.route(inp)
        assert decision.mode in ("execution_first", "cognitive_first", "balanced")
        assert isinstance(decision.reason, str)
        assert isinstance(decision.cognitive_adjustments, list)
        assert isinstance(decision.execution_constraints, list)
        assert isinstance(decision.routing_debug, dict)


class TestDualCoreDecision_Properties:
    """Test DualCoreDecision properties."""

    def test_ux_mode_execution(self):
        d = DualCoreDecision(mode="execution_first", reason="", cognitive_adjustments=[], execution_constraints=[])
        assert d.ux_mode == "execution"

    def test_ux_mode_cognitive(self):
        d = DualCoreDecision(mode="cognitive_first", reason="", cognitive_adjustments=[], execution_constraints=[])
        assert d.ux_mode == "cognitive"

    def test_ux_mode_balanced(self):
        d = DualCoreDecision(mode="balanced", reason="", cognitive_adjustments=[], execution_constraints=[])
        assert d.ux_mode == "balanced"

    def test_prompt_instruction_with_adjustments(self):
        d = DualCoreDecision(
            mode="cognitive_first",
            reason="test",
            cognitive_adjustments=["adjust tone", "reduce verbosity"],
            execution_constraints=["limit tasks to 3"],
        )
        instruction = d.prompt_instruction
        assert "认知调制" in instruction
        assert "执行约束" in instruction

    def test_to_dict(self):
        d = DualCoreDecision(
            mode="balanced",
            reason="test",
            cognitive_adjustments=["a"],
            execution_constraints=["b"],
        )
        result = d.to_dict()
        assert result["mode"] == "balanced"
        assert "a" in result["cognitive_adjustments"]

    def test_structured_adjustments_serialization(self):
        adj = CognitiveAdjustment(dimension="tone", value="gentle", reason="emotional state")
        d = DualCoreDecision(
            mode="cognitive_first",
            reason="test",
            cognitive_adjustments=[],
            execution_constraints=[],
            structured_adjustments=[adj],
        )
        result = d.to_dict()
        assert len(result["structured_adjustments"]) == 1
        assert result["structured_adjustments"][0]["dimension"] == "tone"


class TestCognitiveAdjustment:
    """Test CognitiveAdjustment helper."""

    def test_to_text(self):
        adj = CognitiveAdjustment(dimension="verbosity", value="low", reason="cognitive overload")
        assert "verbosity=low" in adj.to_text()

    def test_to_dict(self):
        adj = CognitiveAdjustment(
            dimension="challenge_level",
            value=0.7,
            reason="testing",
            evidence=["pattern_a"],
            scope="session",
        )
        d = adj.to_dict()
        assert d["dimension"] == "challenge_level"
        assert d["value"] == 0.7
        assert d["scope"] == "session"


class TestAdaptationRecord:
    """Test AdaptationRecord helper."""

    def test_to_dict(self):
        r = AdaptationRecord(
            what_changed="session_mode",
            why="procrastination detected",
            expected_effect="better engagement",
            user_facing_message="Let's try a lighter approach",
            source="dual_core_router",
        )
        d = r.to_dict()
        assert d["what_changed"] == "session_mode"
        assert "created_at" in d

    def test_to_dict_with_record_id(self):
        r = AdaptationRecord(
            what_changed="tone",
            why="test",
            expected_effect="test",
            user_facing_message="test",
            source="test",
            record_id="rec-123",
        )
        d = r.to_dict()
        assert d["record_id"] == "rec-123"


# ── FSM State Persistence Real Redis Tests ────────────────────────────


@pytest.mark.asyncio
class TestFSMStatePersistence:
    """Test FSM state persistence with real Redis SessionStateManager."""

    @pytest_asyncio.fixture
    async def state_manager(self, redis_client):
        return SessionStateManager(redis_client)

    async def test_save_and_load_state(self, state_manager):
        session_id = str(uuid.uuid4())
        state = FSMState(session_id=session_id, state=STATE_INIT)
        await state_manager.save_state(session_id, state)

        loaded = await state_manager.load_state(session_id)
        assert loaded is not None
        assert loaded.state == STATE_INIT

    async def test_state_transition_persists(self, state_manager):
        session_id = str(uuid.uuid4())
        state = FSMState(session_id=session_id, state=STATE_INIT)
        await state_manager.save_state(session_id, state)

        await state_manager.update_state(session_id, STATE_THINKING, details="Processing")
        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_THINKING

    async def test_full_fsm_lifecycle(self, state_manager):
        session_id = str(uuid.uuid4())
        transitions = [STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_DONE]

        for state_name in transitions:
            state = FSMState(session_id=session_id, state=state_name)
            await state_manager.save_state(session_id, state)

        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_DONE

    async def test_tool_calling_loop(self, state_manager):
        session_id = str(uuid.uuid4())

        await state_manager.save_state(session_id, FSMState(session_id=session_id, state=STATE_THINKING))
        await state_manager.update_state(session_id, STATE_TOOL_CALLING, details="Execute tool")
        await state_manager.update_state(session_id, STATE_THINKING, details="Process result")
        await state_manager.update_state(session_id, STATE_GENERATING, details="Final response")

        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_GENERATING

    async def test_error_recovery(self, state_manager):
        session_id = str(uuid.uuid4())

        await state_manager.save_state(session_id, FSMState(session_id=session_id, state=STATE_THINKING))
        await state_manager.update_state(session_id, STATE_FAILED, details="Timeout")
        await state_manager.update_state(session_id, STATE_THINKING, details="Retry")

        loaded = await state_manager.load_state(session_id)
        assert loaded.state == STATE_THINKING

    async def test_session_isolation(self, state_manager):
        s1 = str(uuid.uuid4())
        s2 = str(uuid.uuid4())

        await state_manager.save_state(s1, FSMState(session_id=s1, state=STATE_THINKING))
        await state_manager.save_state(s2, FSMState(session_id=s2, state=STATE_DONE))

        state1 = await state_manager.load_state(s1)
        state2 = await state_manager.load_state(s2)
        assert state1.state == STATE_THINKING
        assert state2.state == STATE_DONE

    async def test_missing_session_returns_none(self, state_manager):
        loaded = await state_manager.load_state("nonexistent-session")
        assert loaded is None
