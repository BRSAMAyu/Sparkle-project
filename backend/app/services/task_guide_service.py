"""
Task Guide Service
Generates AI guides for tasks using GLM model.
"""
from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task
from app.models.user import User


class TaskGuideService:
    """任务执行指南生成服务 - 使用 GLM 模型"""

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    PRIMARY_TIMEOUT_SECONDS = 4.0
    FALLBACK_TIMEOUT_SECONDS = 3.0
    MAX_OUTPUT_TOKENS = 900

    async def generate_guide(
        self,
        task: Task,
        user: User,
        db: AsyncSession,
        user_context: dict | None = None
    ) -> str:
        """
        使用 GLM 生成任务执行指南，失败时降级到 DeepSeek

        Args:
            task: 任务对象
            user: 用户对象
            db: 数据库会话
            user_context: 额外用户上下文 (可选)

        Returns:
            str: Markdown 格式的执行指南
        """
        prompt = self._build_prompt(task, user, user_context)

        # 优先使用 GLM
        if settings.ZHIPU_API_KEY:
            try:
                result = await self._call_glm(prompt)
                if result:
                    return result
            except Exception:
                # GLM 失败，尝试 DeepSeek
                pass

        # 降级到 DeepSeek
        if settings.DEEPSEEK_API_KEY:
            try:
                result = await self._call_deepseek(prompt)
                if result:
                    return result
            except Exception:
                pass

        # 最终降级：固定模板
        return self._static_guide(task)

    def _build_prompt(self, task: Task, user: User, user_context: dict | None) -> str:
        """构建生成指南的提示词"""
        task_type_value = getattr(task.type, "value", task.type)

        # 任务类型映射
        task_type_map = {
            "learning": "学习",
            "training": "练习",
            "error_fix": "错题订正",
            "reflection": "反思总结",
            "social": "协作",
            "planning": "规划"
        }
        task_type_name = task_type_map.get(str(task_type_value).lower(), str(task_type_value))

        # 难度描述
        difficulty_desc = {
            1: "非常简单，适合入门",
            2: "较简单，可以轻松完成",
            3: "中等，需要一定专注",
            4: "较难，需要深入思考",
            5: "困难，建议分步完成"
        }.get(task.difficulty, "中等")

        # 构建提示词
        prompt = f"""请为以下学习任务生成一份执行指南：

**任务标题**: {task.title}
**任务类型**: {task_type_name}
**预计时长**: {task.estimated_minutes} 分钟
**难度等级**: {task.difficulty}/5 ({difficulty_desc})
**能量消耗**: {task.energy_cost}/5"""

        if task.tags:
            prompt += f"\n**标签**: {', '.join(task.tags)}"

        if task.due_date:
            prompt += f"\n**截止日期**: {task.due_date.strftime('%Y-%m-%d')}"

        if user_context and "recent_tasks" in user_context:
            recent_count = len(user_context["recent_tasks"])
            prompt += f"\n**用户近期已完成任务数**: {recent_count}"

        prompt += """

请输出一份简洁的执行指南，只允许使用稳定的基础 Markdown：

## 任务目标
- 一到两条

## 准备清单
- 一到三条

## 执行步骤
1. 第一步
2. 第二步
3. 第三步

## 时间分配
- 准备：X 分钟
- 执行：X 分钟
- 收尾：X 分钟

## 完成标准
- 一到两条

严格要求：
- 不要使用 emoji
- 不要使用表格
- 不要使用引用块
- 不要使用非常规符号项目符号
- 不要输出代码块
- 不要额外开场白或结尾
- 控制在 350 字以内
- 每一步必须具体、可执行"""

        return prompt

    async def _call_glm(self, prompt: str) -> str | None:
        """调用 GLM API 生成指南"""
        headers = {
            "Authorization": f"Bearer {settings.ZHIPU_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.ZHIPU_FLASH_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个高效的学习任务助手，擅长输出简短、清晰、可执行的任务指南。你只能使用基础 Markdown 标题、数字列表和短横线列表，禁止 emoji、表格、引用、代码块和特殊符号。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,
            "top_p": 0.8,
            "max_tokens": self.MAX_OUTPUT_TOKENS,
        }

        async with httpx.AsyncClient(timeout=self.PRIMARY_TIMEOUT_SECONDS) as client:
            response = await client.post(self.API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            if content.startswith("```"):
                content = self._extract_markdown(content)
            return self._normalize_output(content)
        return None

    async def _call_deepseek(self, prompt: str) -> str | None:
        """调用 DeepSeek API 作为降级方案"""
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.DEEPSEEK_CHAT_MODEL,  # deepseek-chat
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个高效的学习任务助手，擅长输出简短、清晰、可执行的任务指南。你只能使用基础 Markdown 标题、数字列表和短横线列表，禁止 emoji、表格、引用、代码块和特殊符号。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,
            "max_tokens": self.MAX_OUTPUT_TOKENS,
        }

        async with httpx.AsyncClient(timeout=self.FALLBACK_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.DEEPSEEK_BASE_URL + "/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            if content.startswith("```"):
                content = self._extract_markdown(content)
            return self._normalize_output(content)
        return None

    def _extract_markdown(self, content: str) -> str:
        """从代码块中提取 markdown 内容"""
        lines = content.split('\n')
        in_code_block = False
        result = []

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if not in_code_block:
                result.append(line)

        return '\n'.join(result).strip()

    def _normalize_output(self, content: str) -> str:
        """Normalize model output into a markdown subset the client renders reliably."""
        normalized = content.replace("\r\n", "\n").replace("\uFFFD", "")
        normalized_lines: list[str] = []

        for raw_line in normalized.split("\n"):
            line = raw_line.strip()
            if not line:
                normalized_lines.append("")
                continue
            if line.startswith(("•", "●", "▪", "◦", "‣", "？", "?", "�")):
                line = f"- {line[1:].strip()}"
            if line.startswith("-**") or line.startswith("-__"):
                line = f"- {line[1:].strip()}"
            normalized_lines.append(line)

        return "\n".join(normalized_lines).strip()

    def _static_guide(self, task: Task) -> str:
        """降级方案：当 API 不可用时返回固定模板"""
        task_type_value = getattr(task.type, "value", task.type)
        task_type_map = {
            "learning": "学习",
            "training": "练习",
            "error_fix": "错题订正",
            "reflection": "反思总结",
            "social": "协作",
            "planning": "规划"
        }
        task_type_name = task_type_map.get(str(task_type_value).lower(), str(task_type_value))

        return f"""## 任务目标
- 完成此{task_type_name}任务，预计耗时 {task.estimated_minutes} 分钟。

## 准备清单
- 确认有充足的时间（{task.estimated_minutes} 分钟）
- 准备必要的学习材料
- 找一个安静的学习环境

## 执行步骤
1. 准备阶段（约 {max(5, task.estimated_minutes // 10)} 分钟）：明确目标，准备材料，进入专注状态。
2. 执行阶段（约 {task.estimated_minutes - 10} 分钟）：专注完成核心内容，及时记录关键点。
3. 收尾阶段（约 5 分钟）：检查完成质量，总结改进点。

## 时间分配
- 准备：{max(5, task.estimated_minutes // 10)} 分钟
- 执行：{task.estimated_minutes - 10} 分钟
- 收尾：5 分钟

## 完成标准
- 按计划完成主要步骤
- 达到预期学习效果
- 记录关键笔记或总结
"""


# 全局实例
task_guide_service = TaskGuideService()
