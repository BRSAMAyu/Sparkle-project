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

请输出一份简洁的 Markdown 执行指南，包含：

1. **🎯 任务目标**
2. **📋 准备清单**
3. **📍 执行步骤**（3-4 步）
4. **⏱️ 时间分配**
5. **✅ 完成标准**

要求：
- 控制在 350 字以内
- 每步都要具体、可执行
- 直接输出 Markdown，不要额外开场白"""

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
                    "content": "你是一个高效的学习任务助手，擅长输出简短、清晰、可执行的任务指南。"
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
            return content
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
                    "content": "你是一个高效的学习任务助手，擅长输出简短、清晰、可执行的任务指南。"
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
            return content
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

        return f"""# {task.title}

## 🎯 任务目标
完成此{task_type_name}任务，预计耗时 {task.estimated_minutes} 分钟。

## 📋 准备清单
- [ ] 确认有充足的时间（{task.estimated_minutes} 分钟）
- [ ] 准备必要的学习材料
- [ ] 找一个安静的学习环境

## 📍 执行步骤

### 步骤 1: 准备阶段（约 {max(5, task.estimated_minutes // 10)} 分钟）
- 明确任务目标和预期产出
- 准备所需材料和工具
- 调整学习状态

### 步骤 2: 执行阶段（约 {task.estimated_minutes - 10} 分钟）
- 专注完成核心内容
- 及时记录重要笔记
- 遇到问题先尝试独立解决

### 步骤 3: 复盘阶段（约 5 分钟）
- 检查完成质量
- 总结经验教训
- 记录下次改进点

## ⏱️ 时间分配
- 准备: {max(5, task.estimated_minutes // 10)} 分钟
- 执行: {task.estimated_minutes - 10} 分钟
- 复盘: 5 分钟

## 💡 注意事项
- 保持专注，避免分心
- 遇到困难可以休息一下再继续
- 完成后及时记录心得

## ✅ 完成标准
- [ ] 按计划完成了所有步骤
- [ ] 达到了预期的学习效果
- [ ] 记录了相关的笔记和总结
"""


# 全局实例
task_guide_service = TaskGuideService()
