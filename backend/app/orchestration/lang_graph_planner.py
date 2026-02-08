"""
LangGraph Planner - Phase 3

Responsibilities:
1. Receive user message and state snapshot
2. Output ExecutablePlan (does NOT execute tools)
3. Support re-plan mechanism for version conflicts
4. Support multi-agent collaboration output (Phase 3)
"""
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from app.agents.graph.state import SparkleState
from app.agents.graph.workflow import sparkle_planning_graph  # Phase 2: Use planning-only graph
from app.orchestration.schemas import ExecutablePlan, StateSnapshot, StepCriteria, ToolCallSpec


class LangGraphPlanner:
    """LangGraph Planner (Phase 2)

    Responsibilities:
    1. Convert LangGraph output to ExecutablePlan
    2. Does NOT execute any tools or database operations
    3. Returns executable JSON structure
    """

    # Tools that should trigger PONR flag
    PONR_TOOLS = {
        "delete_task", "delete_plan", "remove_user",
        "clear_all_tasks", "reset_progress"
    }

    # Tools whose output is typically consumed by downstream steps
    CREATOR_TOOLS = {
        "create_plan", "create_task", "batch_create_tasks",
        "create_knowledge_node",
    }

    # Parameter keys that indicate a dependency on a creator tool's output
    DEPENDENCY_PARAM_KEYS = {"plan_id", "task_id", "parent_id", "node_id"}

    # Default per-step criteria by tool category
    _STEP_CRITERIA: dict[str, StepCriteria] = {
        "create_plan": StepCriteria(expected_output_keys=["plan_id"], max_duration_ms=15000, required=True),
        "create_task": StepCriteria(expected_output_keys=["task_id"], max_duration_ms=10000, required=True),
        "batch_create_tasks": StepCriteria(expected_output_keys=["task_ids"], max_duration_ms=20000, required=True),
        "generate_tasks_for_plan": StepCriteria(expected_output_keys=["task_ids"], max_duration_ms=30000, required=True),
        "query_knowledge": StepCriteria(expected_output_keys=["results"], max_duration_ms=10000, required=False),
        "suggest_focus_session": StepCriteria(expected_output_keys=["session_id"], max_duration_ms=10000, required=False),
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client
        # Phase 2: Use planning-only graph (no ToolNode)
        # This ensures planner does NOT execute tools
        self.graph = sparkle_planning_graph
        logger.info("LangGraphPlanner initialized with planning-only graph (no tool execution)")

    async def plan(
        self,
        message: str,
        snapshot: StateSnapshot,
        user_id: str,
        session_id: str,
        conversation_history: list[dict] | None = None,
        plan_id: str | None = None,  # Phase 4: for plan_version tracking
        execution_feedback: dict[str, Any] | None = None,  # Phase C: past feedback
    ) -> ExecutablePlan:
        """Generate execution plan from LangGraph

        Args:
            message: User message
            snapshot: State snapshot
            user_id: User ID
            session_id: Session ID
            conversation_history: Optional conversation history for context
            plan_id: Plan ID for version tracking (Phase 4)
            execution_feedback: Past execution feedback (slow_tools, failed_tools, etc.)

        Returns:
            ExecutablePlan: Executable plan with tool_calls
        """
        # Get plan_version from PlanState (Phase 4)
        plan_version = 1
        if plan_id:
            plan_version = await self._get_plan_version(user_id, plan_id)

        # Build initial state
        messages = [HumanMessage(content=message)]

        # Phase C: Inject execution feedback as system context
        if execution_feedback:
            feedback_context = self._build_feedback_context(execution_feedback)
            if feedback_context:
                messages.insert(0, HumanMessage(content=feedback_context))

        # Add conversation history if provided
        if conversation_history:
            for hist in conversation_history[-5:]:  # Last 5 messages
                if hist.get("role") == "user":
                    messages.insert(-1, HumanMessage(content=hist.get("content", "")))
                elif hist.get("role") == "assistant":
                    messages.insert(-1, AIMessage(content=hist.get("content", "")))

        initial_state: SparkleState = {
            "messages": messages,
            "user_id": user_id,
            "session_id": session_id,
            "user_profile": snapshot.to_dict() if snapshot else {},
            "next_step": None,
            "active_agent": None,
            "require_approval": False,
            "approval_context": None,
            "approval_result": None,
            "error": None,
            "planning_mode": "langgraph",
            # Phase 2: Inject snapshot info
            "_snapshot": snapshot.to_dict() if snapshot else {},
            "_planning_mode": True,
            # Phase 4: Pass plan_version and plan_id
            "_plan_version": plan_version,
            "_plan_id": plan_id,
            # Phase C: Execution feedback for planning context
            "_execution_feedback": execution_feedback,
        }

        # Execute planning graph (stops at tool_calls, does NOT execute tools)
        config = {"configurable": {"thread_id": session_id}}
        final_state = None

        logger.info(f"Starting LangGraph planning for session {session_id}")

        try:
            # The planning graph will complete when agents generate tool_calls
            # It will NOT execute them (no ToolNode in planning graph)
            result_state = await self.graph.ainvoke(initial_state, config)
            final_state = result_state

        except Exception as e:
            logger.error(f"LangGraph planning error: {e}")
            # Return empty plan on error
            return ExecutablePlan(
                schema_version="5.0",
                snapshot_id=snapshot.snapshot_id if snapshot else "",
                context_version=snapshot.context_versions.get("tasks", "v0") if snapshot else "v0",
                source="langgraph",
                confidence=0.0,
                rationale=f"Planning failed: {str(e)}",
                tool_calls=[],
                plan_version=plan_version,
            )

        # Convert to ExecutablePlan
        return self._convert_to_plan(final_state, snapshot, user_id, session_id)

    def _convert_to_plan(
        self,
        langgraph_state: SparkleState,
        snapshot: StateSnapshot,
        user_id: str,
        session_id: str
    ) -> ExecutablePlan:
        """Convert LangGraph state to ExecutablePlan (Phase 4: with plan_version)

        Args:
            langgraph_state: State from LangGraph execution
            snapshot: Original state snapshot
            user_id: User ID
            session_id: Session ID

        Returns:
            ExecutablePlan: Converted plan
        """
        tool_calls = []
        active_agent = "unknown"
        rationale = "Generated via LangGraph"

        # Phase 3: Extract collaboration metadata
        agents_involved = langgraph_state.get("collaboration_agents", [])
        collaboration_mode = langgraph_state.get("collaboration_mode", "single")
        collaboration_order = langgraph_state.get("collaboration_order", [])

        # Phase 4: Extract plan_version and plan_id
        plan_version = langgraph_state.get("_plan_version", 1)
        plan_id = langgraph_state.get("_plan_id")

        def _normalize_tool_call(tc) -> dict[str, Any] | None:
            if isinstance(tc, dict):
                name = tc.get("name") or tc.get("tool") or tc.get("function", {}).get("name")
                args = tc.get("args") or tc.get("arguments") or tc.get("function", {}).get("arguments", {})
                call_id = tc.get("id") or tc.get("tool_call_id")
            else:
                name = getattr(tc, "name", None) or getattr(tc, "tool", None)
                args = getattr(tc, "args", None) or getattr(tc, "arguments", None)
                call_id = getattr(tc, "id", None) or getattr(tc, "tool_call_id", None)

            if isinstance(args, str):
                try:
                    import json
                    args = json.loads(args)
                except Exception:
                    args = {"_raw": args}

            if not name:
                return None

            return {"id": call_id, "name": name, "args": args}

        # Extract tool_calls from messages
        messages = langgraph_state.get("messages", [])
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    normalized = _normalize_tool_call(tc)
                    if not normalized:
                        continue
                    tool_name = normalized["name"]
                    tool_args = normalized["args"]

                    tool_calls.append(ToolCallSpec(
                        id=normalized.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                        name=tool_name,
                        params=tool_args,
                        timeout_ms=10000,
                        priority="normal",
                        allow_retry=True,
                        max_retries=2,
                        point_of_no_return=tool_name in self.PONR_TOOLS
                    ))

        # Phase 5: Infer DAG dependencies and build execution order
        tool_calls = self._infer_dependencies(tool_calls)
        execution_order = self._build_execution_order(tool_calls)

        # Get active_agent for rationale
        active_agent = langgraph_state.get("active_agent")
        if active_agent:
            if collaboration_mode != "single" and agents_involved:
                rationale = f"Planned via collaboration: {', '.join(agents_involved)}"
            else:
                rationale = f"Planned by {active_agent} via LangGraph"
        else:
            # Try to infer from next_step
            next_step = langgraph_state.get("next_step")
            if next_step:
                rationale = f"Planned for {next_step} via LangGraph"

        # Calculate confidence based on tool_calls presence and collaboration
        confidence = 0.8 if tool_calls else 0.5
        if collaboration_mode != "single":
            confidence = min(confidence + 0.1, 1.0)  # Boost confidence for collaboration

        # Get context version from snapshot
        context_version = "v0"
        if snapshot and snapshot.context_versions:
            context_version = snapshot.context_versions.get("tasks", "v0")

        return ExecutablePlan(
            schema_version="5.0",
            plan_id=plan_id or str(uuid.uuid4()),
            snapshot_id=snapshot.snapshot_id if snapshot else "",
            context_version=context_version,
            source="langgraph",
            confidence=confidence,
            rationale=rationale,
            agents_involved=agents_involved,
            collaboration_mode=collaboration_mode,
            collaboration_order=collaboration_order,
            tool_calls=tool_calls,
            fallback_strategy={
                "on_validation_fail": "replan",
                "on_version_conflict": "replan",
                "on_execution_fail": "skip"
            },
            plan_version=plan_version,
            execution_order=execution_order,
            total_steps=len(tool_calls),
        )

    # ------------------------------------------------------------------
    # Phase 5: DAG dependency inference & topological sort
    # ------------------------------------------------------------------

    def _infer_dependencies(self, tool_calls: list[ToolCallSpec]) -> list[ToolCallSpec]:
        """Analyze tool_calls and populate ``depends_on`` / ``output_key``.

        Heuristic rules:
        1. Creator tools (create_plan, create_task, …) produce an output_key.
        2. Any later tool referencing a dependency param key (plan_id, task_id, …)
           where the *value* is a placeholder or matches a creator output_key is
           linked via ``depends_on``.
        3. ``generate_tasks_for_plan`` always depends on the preceding
           ``create_plan`` if present.
        4. Per-step ``success_criteria`` are assigned from the default map.
        """
        # Pass 1 — assign output_keys and criteria to creator tools
        creator_index: dict[str, str] = {}  # tool_name -> spec.id (latest)
        for tc in tool_calls:
            if tc.name in self.CREATOR_TOOLS:
                tc.output_key = f"{tc.name}_result_{tc.id[-8:]}"
                creator_index[tc.name] = tc.id
            if tc.name in self._STEP_CRITERIA and tc.success_criteria is None:
                tc.success_criteria = self._STEP_CRITERIA[tc.name]

        # Pass 2 — link dependent steps
        for i, tc in enumerate(tool_calls):
            for param_key in tc.params:
                if param_key not in self.DEPENDENCY_PARAM_KEYS:
                    continue
                # Find the most recent creator that produces this param type
                for earlier in reversed(tool_calls[:i]):
                    if earlier.output_key and earlier.name in self.CREATOR_TOOLS:
                        # e.g. plan_id param → depends on create_plan
                        if (param_key == "plan_id" and "plan" in earlier.name) or \
                           (param_key == "task_id" and "task" in earlier.name) or \
                           (param_key == "node_id" and "node" in earlier.name) or \
                           (param_key == "parent_id"):
                            if earlier.id not in tc.depends_on:
                                tc.depends_on.append(earlier.id)
                            break

            # Special: generate_tasks_for_plan always depends on create_plan
            if tc.name == "generate_tasks_for_plan" and "create_plan" in creator_index:
                dep_id = creator_index["create_plan"]
                if dep_id not in tc.depends_on:
                    tc.depends_on.append(dep_id)

        return tool_calls

    @staticmethod
    def _build_execution_order(tool_calls: list[ToolCallSpec]) -> list[list[str]]:
        """Topological sort into execution layers (Kahn's algorithm).

        Steps within the same layer have no mutual dependencies and can
        execute in parallel.  Returns ``[]`` when all steps are independent
        (caller falls back to single-layer sequential).
        """
        if not tool_calls:
            return []

        ids = [tc.id for tc in tool_calls]
        id_set = set(ids)

        # Build in-degree map
        in_degree: dict[str, int] = {tc_id: 0 for tc_id in ids}
        children: dict[str, list[str]] = {tc_id: [] for tc_id in ids}
        has_edges = False
        for tc in tool_calls:
            for dep_id in tc.depends_on:
                if dep_id in id_set:
                    in_degree[tc.id] += 1
                    children[dep_id].append(tc.id)
                    has_edges = True

        if not has_edges:
            return []  # No dependencies → single layer fallback

        layers: list[list[str]] = []
        remaining = set(ids)

        while remaining:
            layer = [tc_id for tc_id in ids if tc_id in remaining and in_degree[tc_id] == 0]
            if not layer:
                # Cycle detected — break by taking remaining in original order
                logger.warning("Cycle detected in tool call dependencies, breaking cycle")
                layers.append(sorted(remaining, key=ids.index))
                break
            layers.append(layer)
            for tc_id in layer:
                remaining.discard(tc_id)
                for child in children[tc_id]:
                    in_degree[child] -= 1

        return layers

    async def replan(
        self,
        message: str,
        snapshot: StateSnapshot,
        user_id: str,
        session_id: str,
        previous_plan: ExecutablePlan | None = None,
        conflict_info: dict[str, Any] | None = None,
        plan_id: str | None = None,
    ) -> ExecutablePlan:
        """Re-plan after version conflict or validation failure

        Args:
            message: Original user message
            snapshot: New state snapshot
            user_id: User ID
            session_id: Session ID
            previous_plan: Previous plan that failed
            conflict_info: Optional conflict details

        Returns:
            ExecutablePlan: New execution plan
        """
        logger.info(
            f"Re-planning for session {session_id}, "
            f"previous confidence: {previous_plan.confidence if previous_plan else 0.0}"
        )

        # Include conflict info in message for context
        enhanced_message = message
        if conflict_info and conflict_info.get("has_conflict"):
            conflicted_domains = conflict_info.get("conflicted_domains", [])
            enhanced_message = (
                f"{message}\n\n"
                f"[Context: State changed in {conflicted_domains} since initial planning. "
                f"Please consider current state.]"
            )

        # Generate new plan
        new_plan = await self.plan(
            message=enhanced_message,
            snapshot=snapshot,
            user_id=user_id,
            session_id=session_id,
            plan_id=plan_id,
        )

        # Mark as re-plan
        new_plan.rationale += " (re-planned after state change)"

        logger.info(
            f"Re-planning complete: {len(new_plan.tool_calls)} tool_calls, "
            f"confidence: {new_plan.confidence}"
        )

        return new_plan

    def should_use_planner(self, route_decision) -> bool:
        """Check if LangGraph planner should be used based on route decision

        Args:
            route_decision: RouteDecision from RequestRouter

        Returns:
            bool: True if planner should be used
        """
        return route_decision.execution_mode in ["langgraph", "hybrid"]

    def get_plan_summary(self, plan: ExecutablePlan) -> str:
        """Get a human-readable summary of the plan

        Args:
            plan: ExecutablePlan to summarize

        Returns:
            str: Plan summary
        """
        if not plan.tool_calls:
            return "No tool calls planned"

        tool_names = [tc.name for tc in plan.tool_calls]
        summary = f"Plan ({plan.source}): {', '.join(tool_names)}"

        if plan.risk_flags:
            summary += f" [Risks: {', '.join(plan.risk_flags)}]"

        return summary

    async def _get_plan_version(self, user_id: str, plan_id: str) -> int:
        """获取 PlanState.version (Phase 4)

        Args:
            user_id: 用户 ID
            plan_id: 计划 ID

        Returns:
            PlanState.version or 1 if not found
        """
        if not self.redis:
            return 1

        # 先从 Redis 缓存尝试
        cache_key = f"state:plan:{plan_id}"
        try:
            import json
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return data.get("version", 1)
        except Exception:
            pass

        return 1  # 默认值

    @staticmethod
    def _build_feedback_context(feedback: dict[str, Any]) -> str:
        """Build a context string from past execution feedback.

        Provides the planning LLM with information about tools that
        were slow, failed, or had unreliable dependencies, so it can
        adjust its planning accordingly.
        """
        parts: list[str] = []

        slow = feedback.get("slow_tools", [])
        if slow:
            parts.append(f"Previously slow tools (consider alternatives or longer timeouts): {', '.join(slow)}")

        failed = feedback.get("failed_tools", [])
        if failed:
            parts.append(f"Recently failed tools (may need retries or different approach): {', '.join(failed)}")

        unreliable = feedback.get("unreliable_dependencies", [])
        if unreliable:
            parts.append(f"Unreliable dependency steps from last execution: {', '.join(unreliable)}")

        score = feedback.get("quality_score")
        if score is not None and score < 0.5:
            parts.append(f"Last execution quality was low ({score:.2f}). Consider simplifying the plan.")

        if not parts:
            return ""

        return "[Planning Context - Execution Feedback]\n" + "\n".join(parts)
