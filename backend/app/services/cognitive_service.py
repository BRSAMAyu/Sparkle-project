"""
Cognitive Prism Service
认知棱镜核心服务
"""
from uuid import UUID
from typing import Optional, List, Dict
import json
from datetime import datetime, timedelta, time
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from app.models.cognitive import CognitiveFragment, BehaviorPattern
from app.models.task import Task, TaskStatus
from app.schemas.cognitive import CognitiveFragmentCreate
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service

class CognitiveService:
    """认知棱镜服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_fragment(
        self,
        user_id: UUID,
        data: CognitiveFragmentCreate,
        background_tasks: BackgroundTasks = None
    ) -> CognitiveFragment:
        """
        创建认知碎片
        自动触发 Embedding 和 LLM 分析
        """
        fragment = CognitiveFragment(
            user_id=user_id,
            task_id=data.task_id,
            source_type=data.source_type,
            content=data.content
        )
        self.db.add(fragment)
        await self.db.commit()
        await self.db.refresh(fragment)

        # 触发后续处理
        if background_tasks:
            background_tasks.add_task(self._process_fragment_async, fragment.id)
        else:
            # 如果没有传入 background_tasks，则同步执行(或忽略，视需求而定)
            # 为了开发方便，这里尝试同步执行一部分关键逻辑
            await self._process_fragment_async(fragment.id)

        return fragment

    async def _process_fragment_async(self, fragment_id: UUID):
        """后台处理碎片: Embedding + Analysis"""
        logger.info(f"Processing cognitive fragment: {fragment_id}")
        
        try:
            # 1. Get Fragment
            stmt = select(CognitiveFragment).where(CognitiveFragment.id == fragment_id)
            result = await self.db.execute(stmt)
            fragment = result.scalar_one_or_none()
            if not fragment:
                return

            # 2. Generate Embedding
            if not fragment.embedding:
                embedding = await embedding_service.get_embedding(fragment.content)
                fragment.embedding = embedding
            
            # 3. LLM Analysis (Simple Tagging)
            if not fragment.sentiment or not fragment.tags:
                analysis = await self._analyze_content(fragment.content)
                if analysis:
                    fragment.sentiment = analysis.get("sentiment")
                    fragment.tags = analysis.get("tags")

            await self.db.commit()
            logger.info(f"Processed cognitive fragment {fragment_id}")

        except Exception as e:
            logger.error(f"Error processing fragment {fragment_id}: {e}")

    async def _analyze_content(self, content: str) -> Optional[Dict]:
        """使用 LLM 分析内容"""
        system_prompt = """
        You are an expert cognitive psychologist. Analyze the following short text from a student.
        Return a JSON object with:
        1. "sentiment": One of [anxious, bored, frustrated, neutral, confident, happy].
        2. "tags": A list of 1-3 tags describing the cognitive/behavioral pattern (e.g., ["procrastination", "perfectionism", "distraction"]).
        
        JSON ONLY. No markdown.
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            response = await llm_service.chat(messages, temperature=0.1)
            # Cleanup
            cleaned = response.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {"sentiment": "neutral", "tags": []}

    async def get_fragments(
        self, 
        user_id: UUID, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[CognitiveFragment]:
        """获取用户碎片列表"""
        stmt = (
            select(CognitiveFragment)
            .where(CognitiveFragment.user_id == user_id)
            .order_by(CognitiveFragment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mining_implicit_behaviors(self, user_id: UUID) -> List[CognitiveFragment]:
        """
        隐式数据挖掘: 分析用户昨天的任务记录
        Triggered daily by scheduler
        """
        logger.info(f"Mining implicit behaviors for user {user_id}")
        
        yesterday = datetime.utcnow() - timedelta(days=1)
        start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        stmt = select(Task).where(
            and_(
                Task.user_id == user_id,
                Task.completed_at >= start_of_yesterday,
                Task.completed_at <= end_of_yesterday,
                Task.status == TaskStatus.COMPLETED
            )
        )
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()
        
        new_fragments = []
        
        for task in tasks:
            # 1. Planning Fallacy: Actual time significantly > Estimated time
            if task.estimated_minutes and task.actual_minutes:
                if task.actual_minutes > task.estimated_minutes * 2.0:
                    content = f"Planning Fallacy Detected: Task '{task.title}' estimated {task.estimated_minutes}m but took {task.actual_minutes}m."
                    fragment = CognitiveFragment(
                        user_id=user_id,
                        task_id=task.id,
                        source_type='behavior',
                        content=content,
                        tags=['planning_fallacy', 'time_management']
                    )
                    self.db.add(fragment)
                    new_fragments.append(fragment)

            # 2. Late Night Warrior: Completed between 23:00 and 04:00 (Local time approx check, assuming UTC+8 for now or relying on UTC)
            # Assuming simplified logic: UTC 15:00 - 20:00 is approx late night in Asia/US variations. 
            # For simplicity, let's just check the hour of completed_at (UTC).
            # If user is UTC+8, 23:00 is 15:00 UTC. 04:00 is 20:00 UTC.
            hour_utc = task.completed_at.hour
            if 15 <= hour_utc <= 20: 
                content = f"Late Night Activity: Task '{task.title}' completed late at night (UTC {hour_utc}:00)."
                fragment = CognitiveFragment(
                    user_id=user_id,
                    task_id=task.id,
                    source_type='behavior',
                    content=content,
                    tags=['sleep_deprivation', 'late_night']
                )
                self.db.add(fragment)
                new_fragments.append(fragment)

        if new_fragments:
            await self.db.commit()
            # Process embedding/analysis for new fragments
            for f in new_fragments:
                await self.db.refresh(f)
                await self._process_fragment_async(f.id)
                
        return new_fragments

    async def generate_weekly_report(self, user_id: UUID) -> List[BehaviorPattern]:
        """
        生成周报 (Cognitive Analysis)
        基于最近的 Fragments 生成 BehaviorPatterns
        """
        logger.info(f"Generating cognitive report for user {user_id}")
        
        # 1. Recall fragments from last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        stmt = select(CognitiveFragment).where(
            and_(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.created_at >= seven_days_ago
            )
        )
        result = await self.db.execute(stmt)
        fragments = result.scalars().all()
        
        if not fragments:
            return []
            
        # 2. Prepare Context for LLM
        fragment_texts = []
        for i, f in enumerate(fragments):
            fragment_texts.append(f"{i+1}. [{f.source_type}] {f.content}")
            
        context_str = "\n".join(fragment_texts)
        
        # 3. LLM Diagnosis
        system_prompt = """
        You are an expert Cognitive Psychologist.
        Analyze the following behavior fragments from a student.
        Identify 1-3 key "Behavior Patterns" (Cognitive Biases, Emotional Patterns, or Execution Habits).
        
        Output JSON format ONLY:
        [
            {
                "pattern_name": "Name (e.g., Planning Fallacy)",
                "pattern_type": "cognitive/emotional/execution",
                "description": "Deep insight in 2nd person (You...)",
                "solution_text": "One actionable micro-step.",
                "evidence_indices": [1, 3] // Indices of fragments that support this
            }
        ]
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User Fragments:\n{context_str}"}
            ]
            response = await llm_service.chat(messages, temperature=0.2)
            cleaned = response.replace("```json", "").replace("```", "").strip()
            patterns_data = json.loads(cleaned)
            
            new_patterns = []
            for p in patterns_data:
                # Map indices back to IDs
                evidence_ids = []
                for idx in p.get("evidence_indices", []):
                    if 0 < idx <= len(fragments):
                        evidence_ids.append(fragments[idx-1].id)
                
                pattern = BehaviorPattern(
                    user_id=user_id,
                    pattern_name=p["pattern_name"],
                    pattern_type=p["pattern_type"],
                    description=p["description"],
                    solution_text=p["solution_text"],
                    evidence_ids=evidence_ids
                )
                self.db.add(pattern)
                new_patterns.append(pattern)
            
            await self.db.commit()
            return new_patterns
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return []
