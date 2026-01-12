"""
异步任务服务
Job Service - 管理异步任务的创建、状态查询和恢复 (v2.1 增强版)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger
import asyncio
import json

from app.models.job import Job, JobStatus, JobType
from app.config import settings
from app.db.session import AsyncSessionLocal

class JobService:
    """异步任务服务 - v2.1 增强版"""
    
    # 🆕 任务超时时间（秒）- 从配置读取或默认
    JOB_TIMEOUT_SECONDS = getattr(settings, "JOB_TIMEOUT_SECONDS", 120)  # 2分钟
    
    async def startup_recovery(self, db: AsyncSession) -> None:
        """
        🆕 启动时恢复 - 处理中断的任务
        
        在服务启动时调用，将所有 running 状态的任务重置为 failed
        """
        logger.info("Starting job recovery scan...")
        
        # 查找所有 running 状态的任务
        result = await db.execute(
            select(Job).where(Job.status == JobStatus.RUNNING)
        )
        stale_jobs = result.scalars().all()
        
        if not stale_jobs:
            logger.info("No stale jobs found")
            return
        
        # 批量重置为 failed
        for job in stale_jobs:
            job.status = JobStatus.FAILED
            job.error_message = "任务因服务重启而中断，请重试"
            job.completed_at = datetime.now(timezone.utc)
            logger.warning(f"Reset stale job {job.id} to FAILED")
        
        await db.commit()
        logger.info(f"Recovery complete: {len(stale_jobs)} jobs reset")
    
    async def create_job(
        self,
        db: AsyncSession,
        user_id: UUID,
        job_type: JobType,
        params: dict
    ) -> Job:
        """创建异步任务"""
        now = datetime.now(timezone.utc)
        
        job = Job(
            id=uuid4(),
            user_id=user_id,
            type=job_type,
            status=JobStatus.PENDING,
            params=params,
            progress=0,
            started_at=None,
            completed_at=None,
            created_at=now,
            # 🆕 设置超时时间
            timeout_at=now + timedelta(seconds=self.JOB_TIMEOUT_SECONDS)
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # 触发后台执行（不等待）
        # 注意: 这里的 _execute_job_safe 需要能获取 DB session
        asyncio.create_task(self._execute_job_safe(job.id))
        
        return job
    
    async def get_job_status(
        self,
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID
    ) -> Optional[Job]:
        """
        查询任务状态
        
        🆕 v2.1: 查询时检查超时
        """
        result = await db.execute(
            select(Job).where(
                Job.id == job_id,
                Job.user_id == user_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        # 🆕 检查是否超时
        if job.status == JobStatus.RUNNING and job.timeout_at:
            # 使用 timezone-aware datetime 进行比较
            current_time = datetime.now(timezone.utc)
            timeout_at = job.timeout_at
            # 如果数据库返回 naive datetime，假定它是 UTC
            if timeout_at.tzinfo is None:
                timeout_at = timeout_at.replace(tzinfo=timezone.utc)

            if current_time > timeout_at:
                job.status = JobStatus.FAILED
                job.error_message = "任务执行超时，请重试"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                logger.warning(f"Job {job_id} marked as FAILED due to timeout")
        
        return job
    
    async def _execute_job_safe(self, job_id: UUID) -> None:
        """
        后台执行任务（带异常保护）
        """
        logger.info(f"Starting execution for job {job_id}")
        try:
            # 获取新的 DB session
            async with AsyncSessionLocal() as db:
                # 标记为 Running
                result = await db.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.now(timezone.utc)
                    await db.commit()
                    
                    # 执行实际逻辑
                    await self._execute_job(db, job)
                    
                    # 标记为 Completed (如果 _execute_job 没有抛出异常)
                    # 注意: _execute_job 可能会自己更新状态和进度
                    await db.refresh(job)
                    if job.status == JobStatus.RUNNING:
                        job.status = JobStatus.COMPLETED
                        job.completed_at = datetime.now(timezone.utc)
                        job.progress = 100
                        await db.commit()
                        
        except Exception as e:
            logger.exception(f"Job {job_id} execution failed: {e}")
            # 更新任务状态为失败
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Job)
                    .where(Job.id == job_id)
                    .values(
                        status=JobStatus.FAILED,
                        error_message=str(e)[:500],
                        completed_at=datetime.now(timezone.utc)
                    )
                )
                await db.commit()
    
    async def _execute_job(self, db: AsyncSession, job: Job) -> None:
        """后台执行任务的实际逻辑 - 需要子类覆盖或在此扩展"""
        # 这里是实际的业务逻辑分发
        # 比如根据 job.type 调用不同的 service
        
        # 模拟耗时操作
        if job.type == JobType.GENERATE_TASKS:
            # TODO: Call Task Generation Service
            pass
        elif job.type == JobType.EXECUTE_ACTIONS:
            # TODO: Call Action Execution Service
            pass
        
        # 模拟完成
        await asyncio.sleep(1)
        logger.info(f"Job {job.id} logic executed")
