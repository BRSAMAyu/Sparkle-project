
from app.orchestration.statechart_engine import StateGraph, WorkflowState


class StateVisualizer:
    """
    Generates Mermaid.js diagrams for StateGraph visualization.
    """

    def generate_mermaid(self, graph: StateGraph, current_state: WorkflowState | None = None) -> str:
        """
        Generate Mermaid graph syntax.
        Highlights current node if state is provided.
        """
        lines = ["graph TD"]
        context_data = None
        if current_state is not None:
            if isinstance(current_state, dict):
                context_data = current_state.get("context_data", {})
            else:
                context_data = current_state.context_data

        # Nodes
        for node_name in graph.nodes:
            style = ""
            if context_data and context_data.get("current_node") == node_name:
                style = ":::current"
            elif node_name == graph.entry_point:
                style = ":::start"

            lines.append(f"    {node_name}[{node_name}]{style}")

        # Edges
        for from_node, to_node in graph.edges.items():
            if callable(to_node):
                # Conditional edge
                lines.append(f"    {from_node} -.-> {to_node.__name__}{{?}}")
            else:
                lines.append(f"    {from_node} --> {to_node}")

        # Styles
        lines.append("    classDef current fill:#f96,stroke:#333,stroke-width:2px;")
        lines.append("    classDef start fill:#9f6,stroke:#333,stroke-width:2px;")

        return "\n".join(lines)

    def generate_trace_diagram(self, history: list) -> str:
        """
        Generate sequence diagram from execution history.
        """
        lines = ["sequenceDiagram"]
        for _event in history:
            # Placeholder for trace logic
            pass
        return "\n".join(lines)
