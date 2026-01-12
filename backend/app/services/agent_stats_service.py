"""
Agent Execution Statistics Service

跟踪和分析Multi-Agent系统中各个Agent的使用情况和性能指标。
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.agent_stats import AgentExecutionStats, AgentStatsSummary


class AgentStatsService:
    """Agent协作统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_agent_execution(
        self,
        user_id: int,
        session_id: str,
        request_id: str,
        agent_type: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        status: str = "success",
        tool_name: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> AgentExecutionStats:
        """
        记录一次Agent执行

        Args:
            user_id: 用户ID
            session_id: 会话ID
            request_id: 请求ID
            agent_type: Agent类型 (orchestrator, knowledge, math, code, etc.)
            started_at: 开始时间
            completed_at: 完成时间
            status: 状态 (success, failed, timeout)
            tool_name: 工具名称（如果执行了工具）
            operation: 操作描述
            metadata: 额外元数据
            error_message: 错误信息（如果失败）

        Returns:
            AgentExecutionStats记录
        """
        duration_ms = None
        if completed_at and started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        stat = AgentExecutionStats(
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            agent_type=agent_type,
            agent_name=self._get_agent_display_name(agent_type),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            status=status,
            tool_name=tool_name,
            operation=operation,
            extra_metadata=metadata or {},
            error_message=error_message
        )

        self.db.add(stat)
        await self.db.commit()
        await self.db.refresh(stat)

        logger.info(f"Recorded agent execution: {agent_type} for user {user_id}, duration: {duration_ms}ms")
        return stat

    async def get_user_stats(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取用户的Agent使用统计

        Args:
            user_id: 用户ID
            days: 统计最近N天的数据

        Returns:
            统计数据字典
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # 总体统计
        total_query = select(
            func.count(AgentExecutionStats.id).label('total_executions'),
            func.avg(AgentExecutionStats.duration_ms).label('avg_duration'),
            func.count(func.distinct(AgentExecutionStats.session_id)).label('total_sessions')
        ).where(
            and_(
                AgentExecutionStats.user_id == user_id,
                AgentExecutionStats.created_at >= cutoff_date
            )
        )
        result = await self.db.execute(total_query)
        overall = result.fetchone()

        # 按Agent类型统计
        agent_query = select(
            AgentExecutionStats.agent_type,
            func.count(AgentExecutionStats.id).label('count'),
            func.avg(AgentExecutionStats.duration_ms).label('avg_duration'),
            func.max(AgentExecutionStats.duration_ms).label('max_duration'),
            func.count(
                func.case(
                    [
                        (AgentExecutionStats.status == 'success', 1)
                    ],
                    else_=None
                )
            ).label('success_count')
        ).where(
            and_(
                AgentExecutionStats.user_id == user_id,
                AgentExecutionStats.created_at >= cutoff_date
            )
        ).group_by(
            AgentExecutionStats.agent_type
        ).order_by(
            desc('count')
        )

        result = await self.db.execute(agent_query)
        agent_stats = [
            {
                'agent_type': row.agent_type,
                'count': row.count,
                'avg_duration_ms': int(row.avg_duration) if row.avg_duration else 0,
                'max_duration_ms': row.max_duration or 0,
                'success_rate': (row.success_count / row.count * 100) if row.count > 0 else 0
            }
            for row in result.fetchall()
        ]

        # 最近活动
        recent_query = select(AgentExecutionStats).where(
            AgentExecutionStats.user_id == user_id
        ).order_by(
            desc(AgentExecutionStats.created_at)
        ).limit(10)

        result = await self.db.execute(recent_query)
        recent_executions = result.scalars().all()

        return {
            'period_days': days,
            'overall': {
                'total_executions': overall.total_executions or 0,
                'avg_duration_ms': int(overall.avg_duration) if overall.avg_duration else 0,
                'total_sessions': overall.total_sessions or 0
            },
            'by_agent': agent_stats,
            'recent_executions': [
                {
                    'agent_type': exec.agent_type,
                    'operation': exec.operation,
                    'duration_ms': exec.duration_ms,
                    'status': exec.status,
                    'created_at': exec.created_at.isoformat()
                }
                for exec in recent_executions
            ]
        }

    async def get_most_used_agents(
        self,
        user_id: int,
        limit: int = 5,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取用户最常用的Agent类型

        Args:
            user_id: 用户ID
            limit: 返回数量
            days: 统计周期（天）

        Returns:
            Agent列表，按使用次数排序
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = select(
            AgentExecutionStats.agent_type,
            AgentExecutionStats.agent_name,
            func.count(AgentExecutionStats.id).label('usage_count'),
            func.avg(AgentExecutionStats.duration_ms).label('avg_duration')
        ).where(
            and_(
                AgentExecutionStats.user_id == user_id,
                AgentExecutionStats.created_at >= cutoff_date
            )
        ).group_by(
            AgentExecutionStats.agent_type,
            AgentExecutionStats.agent_name
        ).order_by(
            desc('usage_count')
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {
                'agent_type': row.agent_type,
                'agent_name': row.agent_name,
                'usage_count': row.usage_count,
                'avg_duration_ms': int(row.avg_duration) if row.avg_duration else 0
            }
            for row in rows
        ]

    async def get_performance_metrics(
        self,
        user_id: Optional[int] = None,
        agent_type: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取性能指标

        Args:
            user_id: 用户ID（可选，为空则查询全局）
            agent_type: Agent类型（可选，为空则查询所有）
            days: 统计周期

        Returns:
            性能指标字典
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        filters = [AgentExecutionStats.created_at >= cutoff_date]
        if user_id:
            filters.append(AgentExecutionStats.user_id == user_id)
        if agent_type:
            filters.append(AgentExecutionStats.agent_type == agent_type)

        query = select(
            func.count(AgentExecutionStats.id).label('total'),
            func.avg(AgentExecutionStats.duration_ms).label('avg_duration'),
            func.max(AgentExecutionStats.duration_ms).label('max_duration'),
            func.count(
                func.case(
                    [
                        (AgentExecutionStats.status == 'success', 1)
                    ],
                    else_=None
                )
            ).label('success_count'),
            func.count(
                func.case(
                    [
                        (AgentExecutionStats.status == 'failed', 1)
                    ],
                    else_=None
                )
            ).label('failure_count')
        ).where(and_(*filters))

        result = await self.db.execute(query)
        row = result.fetchone()

        total = row.total or 0
        success_count = row.success_count or 0
        failure_count = row.failure_count or 0

        return {
            'period_days': days,
            'total_executions': total,
            'avg_duration_ms': int(row.avg_duration) if row.avg_duration else 0,
            'median_duration_ms': int(row.median_duration) if row.median_duration else 0,
            'p95_duration_ms': int(row.p95_duration) if row.p95_duration else 0,
            'max_duration_ms': row.max_duration or 0,
            'success_rate': (success_count / total * 100) if total > 0 else 0,
            'failure_rate': (failure_count / total * 100) if total > 0 else 0
        }

    async def refresh_materialized_view(self):
        """刷新物化视图（用于定时任务）"""
        await self.db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY agent_stats_summary;")
        await self.db.commit()
        logger.info("Refreshed agent_stats_summary materialized view")

    def _get_agent_display_name(self, agent_type: str) -> str:
        """获取Agent的显示名称"""
        name_map = {
            'orchestrator': 'Orchestrator',
            'knowledge': 'KnowledgeAgent',
            'math': 'MathAgent',
            'code': 'CodeAgent',
            'data_analysis': 'DataAnalyst',
            'translation': 'Translator',
            'image': 'ImageAgent',
            'audio': 'AudioAgent',
            'writing': 'WritingAgent',
            'reasoning': 'ReasoningAgent'
        }
        return name_map.get(agent_type, agent_type.title())
