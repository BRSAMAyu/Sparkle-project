from typing import Optional, Dict, Any, List
from loguru import logger
import asyncio
import json

from app.visualization.state_visualizer import StateVisualizer
from app.orchestration.statechart_engine import GraphEvent, GraphEventType
from app.core.websocket import manager

class RealtimeVisualizer(StateVisualizer):
    """
    Real-time visualization of state chart execution via WebSocket.
    """
    
    def __init__(self):
        super().__init__()
        self.event_buffer = {}
    
    async def on_graph_event(self, event: GraphEvent):
        """Listen to graph events and push updates."""
        # Extract session_id from state
        session_id = event.state.context_data.get("session_id")
        if not session_id:
            return
        
        # Generate visualization
        # Note: We need access to the graph structure. 
        # But GraphEvent only has state and node_id.
        # Ideally, we should pass the graph to generate_mermaid.
        # But StateVisualizer.generate_mermaid takes (graph, state).
        # We don't have the graph object here easily unless we attach it to the event or state.
        # For now, we'll send the event data and let frontend handle it or send simplified update.
        
        # However, the report implementation had `self.generate_mermaid(current_state.graph, ...)`
        # `WorkflowState` doesn't have `graph` attribute.
        # I will send the event details so frontend can highlight.
        # Or I can modify `GraphEvent` to include graph? No.
        
        # Let's just send the event type and node.
        
        # Prepare update data
        update_data = {
            "type": "graph_update",
            "event": event.type.value,
            "node": event.node_id,
            "timestamp": event.timestamp,
            "details": event.details,
            # Snapshot of state
            "state_snapshot": self._serialize_state(event.state)
        }
        
        # Send to subscribers via WebSocket Manager
        await manager.broadcast_visualization(session_id, update_data)
        
        # Buffer event
        await self._buffer_event(session_id, update_data)
    
    async def _buffer_event(self, session_id: str, event: dict):
        """Buffer event for replay."""
        if session_id not in self.event_buffer:
            self.event_buffer[session_id] = []
        
        self.event_buffer[session_id].append(event)
        
        # Limit buffer size
        if len(self.event_buffer[session_id]) > 1000:
            self.event_buffer[session_id] = self.event_buffer[session_id][-500:]
    
    async def get_event_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get event history."""
        if session_id not in self.event_buffer:
            return []
        
        return self.event_buffer[session_id][-limit:]
    
    def _serialize_state(self, state) -> Dict:
        """Serialize state for transport."""
        return {
            "messages_count": len(state.messages),
            "context_keys": list(state.context_data.keys()),
            "errors": state.errors,
            "next_step": state.next_step,
            "trace_id": state.trace_id,
            # Maybe include last message content preview
            "last_message": state.messages[-1]["content"][:50] + "..." if state.messages else ""
        }

# Global instance
visualizer = RealtimeVisualizer()
