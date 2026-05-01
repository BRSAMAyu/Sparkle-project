"""
SummarizationWorker - 后台总结任务处理器

从 Redis 队列消费总结任务，使用 LLM 生成历史对话摘要，
并将结果缓存回 Redis。
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import redis.asyncio as redis
from loguru import logger



class SummarizationWorker:
    """
    后台总结任务处理器

    功能:
    1. 从队列消费总结任务
    2. 调用 LLM 生成摘要
    3. 缓存结果到 Redis
    4. 支持任务优先级和重试
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        batch_size: int = 10,
        max_retries: int = 3,
        worker_id: str = None
    ):
        """
        初始化 SummarizationWorker

        Args:
            redis_client: Redis 客户端
            batch_size: 批量处理的任务数
            max_retries: 最大重试次数
            worker_id: 工作器 ID（用于日志和监控）
        """
        self.redis = redis_client
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.worker_id = worker_id or f"worker-{id(self)}"

        self.running = False
        self.processed_count = 0
        self.failed_count = 0

        logger.info(f"SummarizationWorker {self.worker_id} initialized")

    async def start(self):
        """
        启动工作器，开始消费队列
        """
        if self.running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self.running = True
        logger.info(f"SummarizationWorker {self.worker_id} started")

        try:
            while self.running:
                # 批量消费任务
                await self._process_batch()
                await asyncio.sleep(0.1)  # 短暂休眠，避免忙等待

        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_id} cancelled")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} crashed: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info(f"SummarizationWorker {self.worker_id} stopped")

    async def stop(self):
        """停止工作器"""
        self.running = False
        logger.info(f"Stopping SummarizationWorker {self.worker_id}...")

    async def _process_batch(self):
        """
        批量处理队列中的任务
        """
        queue_key = "queue:summarization"

        # 批量获取任务
        for _ in range(self.batch_size):
            try:
                # 非阻塞获取任务
                task_data = await self.redis.blpop(queue_key, timeout=0.1)

                if task_data is None:
                    break  # 队列为空

                # 解析任务
                task = json.loads(task_data[1])

                # 处理单个任务
                success = await self._process_task(task)

                if success:
                    self.processed_count += 1
                else:
                    self.failed_count += 1

            except Exception as e:
                logger.error(f"Failed to process batch item: {e}")
                self.failed_count += 1

    async def _process_task(self, task: dict[str, Any]) -> bool:
        """
        处理单个总结任务

        Args:
            task: 任务数据

        Returns:
            是否处理成功
        """
        session_id = task.get("session_id")
        user_id = task.get("user_id")
        history = task.get("history", [])
        task.get("timestamp", time.time())
        priority = task.get("priority", "normal")

        if not session_id or not history:
            logger.warning("Invalid task: missing session_id or history")
            return False

        logger.info(
            f"Processing summarization task for session {session_id}, "
            f"history size: {len(history)}, priority: {priority}"
        )

        # 检查是否已经有总结（避免重复处理）
        cache_key = f"summary:{session_id}"
        existing = await self.redis.get(cache_key)
        if existing:
            logger.debug(f"Summary already exists for session {session_id}, skipping")
            return True

        # 重试逻辑
        for attempt in range(1, self.max_retries + 1):
            try:
                summary = await self._generate_summary(history, user_id)

                # 验证总结结果
                if not summary or len(summary.strip()) < 10:
                    raise ValueError("Summary too short or empty")

                # 保存到 Redis
                await self.redis.setex(
                    cache_key,
                    3600,  # 1小时 TTL
                    summary
                )

                logger.info(
                    f"✅ Summary generated for session {session_id} "
                    f"(attempt {attempt}/{self.max_retries})"
                )

                # 记录到历史日志（可选）
                await self._log_summary(session_id, summary, history)

                return True

            except Exception as e:
                logger.warning(
                    f"❌ Summary attempt {attempt}/{self.max_retries} failed "
                    f"for session {session_id}: {e}"
                )

                if attempt < self.max_retries:
                    await asyncio.sleep(1 * attempt)  # 指数退避
                else:
                    logger.error(
                        f"Failed to generate summary after {self.max_retries} attempts: {e}"
                    )

        return False

    async def _generate_summary(self, history: list[dict], user_id: str) -> str:
        """
        使用 LLM 生成历史对话摘要

        Args:
            history: 历史对话列表
            user_id: 用户 ID

        Returns:
            生成的摘要文本
        """
        from app.services.llm_fallback_utils import summarization_llm

        # 构建总结提示词
        prompt = self._build_summary_prompt(history)

        # 调用 LLM 服务（带降级保护）
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的对话总结助手。请用简洁的语言总结对话核心内容。",
            },
            {"role": "user", "content": prompt},
        ]
        try:
            summary = await summarization_llm.call(
                messages,
                fallback="",  # 空字符串作为fallback
                temperature=0.3,
                max_tokens=500,
            )
        except Exception as exc:
            logger.warning(
                "LLM summarization unavailable for user %s, using local fallback: %s",
                user_id,
                exc,
            )
            summary = ""

        if summary and len(summary.strip()) >= 10:
            return summary

        fallback_summary = self._build_local_fallback_summary(history)
        logger.warning(
            "Using local fallback summary for user %s because LLM summary was empty or too short",
            user_id,
        )
        return fallback_summary

    def _build_summary_prompt(self, history: list[dict]) -> str:
        """
        构建总结提示词

        Args:
            history: 历史对话

        Returns:
            提示词文本
        """
        # 限制历史长度，避免输入过大
        limited_history = history[-20:] if len(history) > 20 else history

        prompt_parts = [
            "请总结以下对话的核心内容，提取关键信息：",
            "",
            "对话历史："
        ]

        for msg in limited_history:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")

        prompt_parts.extend([
            "",
            "请用简洁的语言总结：",
            "1. 用户的核心需求是什么？",
            "2. 讨论的关键主题有哪些？",
            "3. 达成了什么结论或下一步行动？",
            "",
            "总结（用中文，不超过200字）："
        ])

        return "\n".join(prompt_parts)

    def _build_local_fallback_summary(self, history: list[dict]) -> str:
        """Build a deterministic fallback summary when the LLM path is unavailable."""
        limited_history = history[-8:] if len(history) > 8 else history
        user_messages = [
            str(msg.get("content", "")).strip()
            for msg in limited_history
            if msg.get("role") == "user" and str(msg.get("content", "")).strip()
        ]
        assistant_messages = [
            str(msg.get("content", "")).strip()
            for msg in limited_history
            if msg.get("role") == "assistant" and str(msg.get("content", "")).strip()
        ]

        user_focus = "；".join(user_messages[:2]) if user_messages else "用户提出了一个需要持续跟进的话题。"
        assistant_focus = (
            "；".join(assistant_messages[:2])
            if assistant_messages
            else "助手给出了初步回应，但需要后续补充。"
        )
        next_step = (
            "建议下一轮继续围绕用户最新问题推进，并补充更具体的行动建议。"
            if user_messages
            else "建议下一轮先确认用户当前最想解决的问题。"
        )

        return (
            f"用户主要在讨论：{user_focus}\n"
            f"当前助手回应重点：{assistant_focus}\n"
            f"下一步：{next_step}"
        )

    async def _log_summary(self, session_id: str, summary: str, history: list[dict]):
        """
        记录总结日志（用于监控和调试）

        可以扩展为写入数据库或专门的日志系统
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "summary": summary,
            "original_length": len(history),
            "worker_id": self.worker_id
        }

        # 写入 Redis 日志队列（可选）
        try:
            await self.redis.rpush(
                "logs:summarization",
                json.dumps(log_entry),
                ex=86400  # 24小时过期
            )
        except (TypeError, redis.RedisError):
            pass  # 日志失败不影响主流程

    def get_stats(self) -> dict[str, Any]:
        """
        获取工作器统计信息
        """
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "processed": self.processed_count,
            "failed": self.failed_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.failed_count)
                if (self.processed_count + self.failed_count) > 0
                else 0
            )
        }


# 工厂函数
def create_summarization_worker(
    redis_url: str | redis.Redis,
    worker_id: str = None,
    **kwargs
) -> SummarizationWorker:
    """
    创建 SummarizationWorker 实例

    Args:
        redis_url: Redis 连接 URL 或现成的 Redis 客户端
        worker_id: 工作器 ID
        **kwargs: 其他配置参数

    Returns:
        SummarizationWorker 实例
    """
    from app.config import settings
    from app.core.redis_utils import resolve_redis_password

    if isinstance(redis_url, redis.Redis):
        redis_client = redis_url
    else:
        resolved_password, _ = resolve_redis_password(redis_url, settings.REDIS_PASSWORD)
        redis_client = redis.from_url(redis_url, decode_responses=False, password=resolved_password)
    return SummarizationWorker(redis_client, worker_id=worker_id, **kwargs)


# 独立的运行脚本入口
async def run_worker():
    """
    作为独立进程运行工作器的入口函数

    使用方式:
    python -m app.orchestration.summarization_worker
    """
    from app.config import settings

    worker = create_summarization_worker(
        redis_url=settings.REDIS_URL,
        worker_id="main-worker"
    )

    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_worker())
