from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from .base import BaseTool, ToolCategory, ToolResult

# ============ Schemas ============

class CheckSystemStatusParams(BaseModel):
    """Check system health status parameters"""
    pass

class QueryErrorLogsParams(BaseModel):
    """Query error logs parameters"""
    minutes: int = Field(default=30, description="Time range in minutes to check for errors")
    limit: int = Field(default=20, description="Maximum number of log lines to return")

class ExplainTraceParams(BaseModel):
    """Explain a distributed trace parameters"""
    trace_id: str = Field(..., description="The Trace ID to investigate")

# ============ Tools ============

class CheckSystemStatusTool(BaseTool):
    """Check current system health metrics (CPU, Memory, QPS, Error Rate)"""
    name = "check_system_status"
    description = """
    Check the current health status of the Sparkle system.
    Returns metrics like QPS, Error Rate, CPU usage, and Memory usage.
    Use this when asking "How is the system?", "Is everything healthy?", or during incident diagnosis.
    """
    category = ToolCategory.QUERY
    parameters_schema = CheckSystemStatusParams
    requires_confirmation = False

    async def execute(self, params: CheckSystemStatusParams, user_id: str, db_session: Any, tool_call_id: Optional[str] = None) -> ToolResult:
        metrics = {}
        prometheus_url = "http://sparkle_prometheus:9090"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 1. Error Rate (HTTP 5xx)
                # sum(rate(http_server_requests_total{status=~"5.."}[5m]))
                # Note: Adjust query based on actual metrics exposed by instrumentator
                resp = await client.get(f"{prometheus_url}/api/v1/query", params={
                    "query": 'sum(rate(http_requests_total{status=~"5.."}[5m])) or vector(0)'
                })
                if resp.status_code == 200:
                    data = resp.json()['data']['result']
                    metrics['error_rate'] = float(data[0]['value'][1]) if data else 0.0

                # 2. QPS
                resp = await client.get(f"{prometheus_url}/api/v1/query", params={
                    "query": 'sum(rate(http_requests_total[5m])) or vector(0)'
                })
                if resp.status_code == 200:
                    data = resp.json()['data']['result']
                    metrics['qps'] = float(data[0]['value'][1]) if data else 0.0

                # 3. Latency (P99)
                resp = await client.get(f"{prometheus_url}/api/v1/query", params={
                    "query": 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) or vector(0)'
                })
                if resp.status_code == 200:
                    data = resp.json()['data']['result']
                    metrics['p99_latency'] = float(data[0]['value'][1]) if data else 0.0

            status = "healthy"
            if metrics.get('error_rate', 0) > 0.05: # > 5% error rate
                status = "critical"
            elif metrics.get('error_rate', 0) > 0.01: # > 1% error rate
                status = "warning"

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "status": status,
                    "metrics": metrics,
                    "timestamp": datetime.now().isoformat()
                },
                widget_type="system_status_card", # Custom widget for frontend
                widget_data={
                    "status": status,
                    "metrics": metrics
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"Failed to query metrics: {str(e)}",
                suggestion="Please check if the monitoring stack is running."
            )

class QueryErrorLogsTool(BaseTool):
    """Query recent error logs from Loki"""
    name = "query_error_logs"
    description = """
    Fetch recent error logs from the system.
    Use this when investigating an issue or when system status reports errors.
    This helps identify the root cause of failures.
    """
    category = ToolCategory.QUERY
    parameters_schema = QueryErrorLogsParams
    requires_confirmation = False

    async def execute(self, params: QueryErrorLogsParams, user_id: str, db_session: Any, tool_call_id: Optional[str] = None) -> ToolResult:
        loki_url = "http://sparkle_loki:3100"
        # Query: {container=~"sparkle.+"} |= "error"
        # Adjust based on Promtail config labels
        query = '{container=~"sparkle_backend|sparkle_gateway"} |= "error"'
        
        start_time = int((datetime.now() - timedelta(minutes=params.minutes)).timestamp() * 1e9)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{loki_url}/loki/api/v1/query_range", params={
                    "query": query,
                    "start": start_time,
                    "limit": params.limit
                })
                
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        tool_name=self.name,
                        error_message=f"Loki returned status {resp.status_code}"
                    )

                data = resp.json()['data']['result']
                logs = []
                for stream in data:
                    container = stream['stream'].get('container', 'unknown')
                    for value in stream['values']:
                        # value is [timestamp, log_line]
                        logs.append({
                            "container": container,
                            "timestamp": value[0],
                            "message": value[1]
                        })

            return ToolResult(
                success=True,
                tool_name=self.name,
                data={
                    "log_count": len(logs),
                    "logs": logs
                },
                # We can return logs as text for LLM to analyze, no widget needed
                widget_type=None
            )

        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error_message=f"Failed to query logs: {str(e)}"
            )