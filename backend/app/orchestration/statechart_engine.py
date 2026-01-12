import asyncio
import inspect
import uuid
from typing import Dict, Any, Callable, List, Optional, Union, Coroutine, Set
from dataclasses import dataclass, field
from loguru import logger
from enum import Enum

# ==========================================
# 1. Core Data Structures
# ==========================================

@dataclass
class WorkflowState:
    """
    Workflow State Blackboard.
    Shared state passed between nodes.
    """
    messages: List[Dict[str, str]] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    next_step: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    is_finished: bool = False
    
    # Trace ID for the current execution flow
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # For nested states: Stack of active graphs
    # stack: List[str] = field(default_factory=list) 

    def update(self, new_data: Dict[str, Any]):
        """Update context data."""
        self.context_data.update(new_data)

    def append_message(self, role: str, content: str, name: Optional[str] = None):
        """Append a message to history."""
        msg = {"role": role, "content": content}
        if name:
            msg["name"] = name
        self.messages.append(msg)

    def clone(self) -> 'WorkflowState':
        """Create a shallow copy of the state for parallel execution."""
        new_state = WorkflowState(
            messages=list(self.messages),
            context_data=dict(self.context_data),
            next_step=self.next_step,
            errors=list(self.errors),
            is_finished=self.is_finished,
            trace_id=self.trace_id
        )
        return new_state


class GraphEventType(Enum):
    NODE_START = "NODE_START"
    NODE_END = "NODE_END"
    EDGE_TRAVERSAL = "EDGE_TRAVERSAL"
    GRAPH_START = "GRAPH_START"
    GRAPH_END = "GRAPH_END"
    ERROR = "ERROR"

@dataclass
class GraphEvent:
    type: GraphEventType
    node_id: str
    state: WorkflowState
    details: Optional[str] = None
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())


# ==========================================
# 2. State Engine
# ==========================================

class StateGraph:
    """
    Hierarchical State Graph Engine (Statecharts).
    Supports:
    - Nodes (Tasks)
    - Edges (Transitions)
    - Conditional Edges (Routing)
    - Nested States (Sub-graphs)
    - Parallel Execution
    """
    def __init__(self, name: str = "RootGraph"):
        self.name = name
        self.nodes: Dict[str, Union[Callable, 'StateGraph', List[Callable]]] = {}
        self.edges: Dict[str, Union[str, Callable]] = {}
        self.entry_point: Optional[str] = None
        self.end_points: Set[str] = {"__end__"}
        self._compiled = False
        
        # Hooks for monitoring
        self.on_event: Optional[Callable[[GraphEvent], Coroutine[Any, Any, None]]] = None
        self.checkpointer: Any = None # Optional checkpointer interface

    def add_node(self, name: str, action: Union[Callable, 'StateGraph']):
        """
        Register a node. 
        'action' can be a function or another StateGraph (Nested State).
        """
        self.nodes[name] = action
        return self

    def add_edge(self, from_node: str, to_node: str):
        """Add a static edge."""
        self.edges[from_node] = to_node
        return self

    def add_conditional_edge(self, from_node: str, router: Callable[[WorkflowState], str]):
        """Add a conditional edge (Dynamic Routing)."""
        self.edges[from_node] = router
        return self

    def set_entry_point(self, node_name: str):
        """Set the entry point node."""
        self.entry_point = node_name
        return self

    def compile(self):
        """Compile and validate the graph."""
        if not self.entry_point:
            raise ValueError(f"Graph '{self.name}' entry point not set")
        if self.entry_point not in self.nodes:
            raise ValueError(f"Entry point '{self.entry_point}' not found in nodes of '{self.name}'")
        self._compiled = True
        return self

    async def _emit_event(self, event_type: GraphEventType, node_id: str, state: WorkflowState, details: str = ""):
        if self.on_event:
            event = GraphEvent(type=event_type, node_id=node_id, state=state, details=details)
            if inspect.iscoroutinefunction(self.on_event):
                await self.on_event(event)
            else:
                # If it returns a coroutine but wasn't caught by iscoroutinefunction (e.g. partial)
                res = self.on_event(event)
                if inspect.isawaitable(res):
                    await res

    async def invoke(self, initial_state: WorkflowState, max_steps: int = 50) -> WorkflowState:
        """Execute the graph."""
        if not self._compiled:
            self.compile()

        assert self.entry_point is not None
        current_node_name: str = self.entry_point
        state = initial_state
        
        # Load from checkpoint if available (TODO: Implement resume logic)
        # For now, we always start fresh or from provided state
        
        steps = 0

        logger.info(f"🚀 [{self.name}] Starting execution from '{current_node_name}'")
        await self._emit_event(GraphEventType.GRAPH_START, self.name, state)

        while current_node_name not in self.end_points and steps < max_steps:
            steps += 1
            logger.info(f"📍 [{self.name}] Executing node: {current_node_name}")
            await self._emit_event(GraphEventType.NODE_START, current_node_name, state)
            
            # Save Checkpoint (Before execution)
            if self.checkpointer:
                await self.checkpointer.save(state, current_node_name)
            
            # 1. Execute Node
            node_action = self.nodes[current_node_name]
            
            try:
                # Check if it's a Nested Graph
                if isinstance(node_action, StateGraph):
                    logger.info(f"↳ Entering nested graph: {node_action.name}")
                    # Pass the on_event handler down to sub-graph
                    node_action.on_event = self.on_event
                    new_state = await node_action.invoke(state, max_steps=max_steps - steps)
                    # Sync back state? Usually yes.
                    if new_state:
                        state = new_state
                
                # Check if it's a Parallel State (List of callables/graphs)
                elif isinstance(node_action, list):
                    logger.info(f"🔀 Executing parallel nodes: {len(node_action)}")
                    new_state = await self._execute_parallel(node_action, state)
                    if new_state:
                        state = new_state

                # Standard Callable Node
                else:
                    if inspect.iscoroutinefunction(node_action):
                        new_state = await node_action(state)
                    else:
                        new_state = node_action(state)
                    
                    if new_state:
                        state = new_state

            except Exception as e:
                logger.error(f"❌ Error in node '{current_node_name}': {e}", exc_info=True)
                state.errors.append(f"[{self.name}] Node {current_node_name} failed: {str(e)}")
                await self._emit_event(GraphEventType.ERROR, current_node_name, state, str(e))
                break # Or handle error transition

            await self._emit_event(GraphEventType.NODE_END, current_node_name, state)

            # 2. Transition (Next Hop)
            if current_node_name in self.edges:
                edge = self.edges[current_node_name]
                
                if isinstance(edge, str):
                    next_node = edge
                elif callable(edge):
                    next_node = edge(state)
                    logger.info(f"🔀 Router decided: {next_node}")
                else:
                    logger.warning(f"Unknown edge type for {current_node_name}")
                    next_node = "__end__"
                
                await self._emit_event(GraphEventType.EDGE_TRAVERSAL, f"{current_node_name}->{next_node}", state)
            else:
                next_node = "__end__"

            current_node_name = next_node

        if steps >= max_steps:
            logger.warning(f"⚠️ [{self.name}] Max steps reached ({max_steps})")

        logger.info(f"🏁 [{self.name}] Execution finished")
        await self._emit_event(GraphEventType.GRAPH_END, self.name, state)
        return state

    async def _execute_parallel(self, branches: List[Callable], state: WorkflowState) -> WorkflowState:
        """
        Execute multiple branches in parallel.
        Merges results back into the main state.
        Strategy: Clone state for each branch -> Gather -> Merge.
        """
        # Create a clone for each branch to avoid race conditions on the same dicts
        # Note: This is a shallow clone strategy. For complex objects, be careful.
        tasks = []
        for branch in branches:
            branch_state = state.clone()
            if isinstance(branch, StateGraph):
                branch.on_event = self.on_event
                tasks.append(branch.invoke(branch_state))
            elif inspect.iscoroutinefunction(branch):
                tasks.append(branch(branch_state))
            else:
                # Wrap synchronous function
                async def wrapper(f, s):
                    return f(s)
                tasks.append(wrapper(branch, branch_state))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge logic: Combine messages and context
        # This is a naive merge strategy. Conflict resolution might be needed.
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Parallel branch {i} failed: {res}")
                state.errors.append(f"Parallel branch {i} failed: {str(res)}")
            elif isinstance(res, WorkflowState):
                # Append new messages
                new_msgs = res.messages[len(state.messages):] # Only take new ones if strictly append-only? 
                # Actually, simpler to just append everything generated in the branch
                # But since we cloned, 'state.messages' length is the baseline.
                # Let's just blindly extend for now, assuming parallel branches don't chat over each other much.
                # Better: Filter for messages added during branch execution.
                
                # We can't easily diff messages without IDs. 
                # Let's assume branches add unique messages.
                # A safer way is to return the delta.
                
                # Merge Context
                state.context_data.update(res.context_data)
                
                # Merge messages (Naively append diff)
                # Ideally, each branch should produce a distinct set of outputs.
                # We'll just take the messages that are NOT in the original state.
                # (This clone check is imperfect but works for POC)
                if len(res.messages) > len(state.messages):
                     # Append the tail
                     state.messages.extend(res.messages[len(state.messages):])

        return state
