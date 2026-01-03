from typing import List, Dict, Optional
from datetime import datetime
import json
import asyncio
from loguru import logger

from app.orchestration.statechart_engine import GraphEvent

class ExecutionTracer:
    """Records and replays execution trace."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def record_event(self, event: GraphEvent):
        """Record execution event."""
        session_id = event.state.context_data.get("session_id")
        if not session_id:
            return

        trace_key = f"trace:{session_id}:{event.timestamp}"
        
        event_data = {
            'type': event.type.value,
            'node': event.node_id,
            'details': event.details,
            'timestamp': event.timestamp,
            'state': self._serialize_state(event.state)
        }
        
        # Store event data
        await self.redis.setex(trace_key, 86400, json.dumps(event_data))
        
        # Add to index (Sorted Set by timestamp)
        index_key = f"trace_index:{session_id}"
        await self.redis.zadd(index_key, {trace_key: event.timestamp})
        await self.redis.expire(index_key, 86400)
    
    async def replay(self, session_id: str, start_time: float = None, end_time: float = None) -> List[Dict]:
        """Replay execution process."""
        index_key = f"trace_index:{session_id}"
        
        if start_time or end_time:
            min_score = start_time or 0
            max_score = end_time or float('inf')
            trace_keys = await self.redis.zrangebyscore(index_key, min_score, max_score)
        else:
            trace_keys = await self.redis.zrange(index_key, 0, -1)
        
        if not trace_keys:
            return []
        
        events = []
        for trace_key in trace_keys:
            data = await self.redis.get(trace_key)
            if data:
                events.append(json.loads(data))
        
        # Ensure sorted by timestamp
        events.sort(key=lambda x: x['timestamp'])
        return events
    
    async def get_execution_summary(self, session_id: str) -> Optional[Dict]:
        """Get execution summary."""
        events = await self.replay(session_id)
        
        if not events:
            return None
        
        node_count = {}
        error_count = 0
        total_latency = 0
        
        for i, event in enumerate(events):
            node = event['node']
            node_count[node] = node_count.get(node, 0) + 1
            
            if event['type'] == 'ERROR':
                error_count += 1
            
            if i > 0:
                latency = event['timestamp'] - events[i-1]['timestamp']
                total_latency += latency
        
        return {
            'total_events': len(events),
            'nodes_visited': node_count,
            'error_count': error_count,
            'total_latency': total_latency,
            'avg_latency': total_latency / len(events) if events else 0,
            'execution_path': list(node_count.keys())
        }

    def _serialize_state(self, state) -> Dict:
        """Serialize state."""
        return {
            'messages_count': len(state.messages),
            'context_keys': list(state.context_data.keys()),
            'errors': state.errors,
            'next_step': state.next_step,
            'trace_id': state.trace_id
        }
