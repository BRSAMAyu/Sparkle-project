"""
Specialist Agents - 专业智能体

各领域的专家AI智能体
"""

import re
from typing import List
from loguru import logger

from .base_agent import BaseAgent, AgentRole, AgentContext, AgentResponse
from app.services.llm_service import llm_service


class MathAgent(BaseAgent):
    """数学专家智能体"""

    def __init__(self):
        super().__init__()
        self.role = AgentRole.MATH
        self.name = "Math Expert"
        self.description = "Specialist in mathematics, equations, and symbolic computation"
        self.capabilities = [
            "Solve algebraic equations",
            "Calculate derivatives and integrals",
            "Explain mathematical concepts",
            "Verify mathematical proofs",
            "Perform statistical analysis"
        ]

    def can_handle(self, query: str) -> float:
        """判断是否为数学相关查询"""
        math_keywords = [
            "方程", "equation", "积分", "integral", "微分", "derivative",
            "矩阵", "matrix", "向量", "vector", "概率", "probability",
            "统计", "statistics", "计算", "calculate", "求解", "solve",
            "证明", "proof", "公式", "formula"
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in math_keywords if kw in query_lower)

        # 检查数学符号
        has_math_symbols = bool(re.search(r'[\+\-\*/\=\^∫∑∏√]', query))

        confidence = min((matches * 0.2) + (0.3 if has_math_symbols else 0), 1.0)
        return confidence

    async def process(self, context: AgentContext) -> AgentResponse:
        """处理数学问题"""
        logger.info(f"MathAgent processing: {context.user_query[:50]}...")

        # 构建专业化提示词
        system_prompt = self.get_system_prompt() + """

When solving math problems:
1. Show step-by-step solutions
2. Use proper mathematical notation
3. Explain the reasoning behind each step
4. Verify the final answer
5. Provide alternative methods if applicable

Format your response with:
- **Problem**: Restate the problem clearly
- **Solution**: Step-by-step solution with LaTeX for equations
- **Answer**: Final answer highlighted
"""

        try:
            # 调用 LLM
            response_text = await llm_service.chat(
                prompt=f"{system_prompt}\n\nUser Question: {context.user_query}",
                model="deepseek-chat"  # 使用 DeepSeek 进行数学推理
            )

            return self.format_response(
                text=response_text,
                reasoning="Applied mathematical reasoning and symbolic computation",
                confidence=0.9,
                metadata={"agent_type": "math", "model": "deepseek"}
            )

        except Exception as e:
            logger.error(f"MathAgent error: {e}")
            return self.format_response(
                text=f"Sorry, I encountered an error while processing this math problem: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )


class CodeAgent(BaseAgent):
    """编程专家智能体"""

    def __init__(self):
        super().__init__()
        self.role = AgentRole.CODE
        self.name = "Code Expert"
        self.description = "Specialist in programming, code generation, and debugging"
        self.capabilities = [
            "Write code in multiple languages (Python, JavaScript, Java, C++, etc.)",
            "Debug and fix code errors",
            "Explain code functionality",
            "Optimize algorithms and performance",
            "Design software architecture"
        ]

    def can_handle(self, query: str) -> float:
        """判断是否为编程相关查询"""
        code_keywords = [
            "代码", "code", "编程", "program", "函数", "function",
            "算法", "algorithm", "python", "javascript", "java",
            "debug", "调试", "实现", "implement", "写", "write",
            "class", "类", "方法", "method"
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in code_keywords if kw in query_lower)

        # 检查代码语法元素
        has_code_syntax = bool(re.search(r'(def |class |import |function |var |const |\{|\})', query))

        confidence = min((matches * 0.2) + (0.4 if has_code_syntax else 0), 1.0)
        return confidence

    async def process(self, context: AgentContext) -> AgentResponse:
        """处理编程问题"""
        logger.info(f"CodeAgent processing: {context.user_query[:50]}...")

        system_prompt = self.get_system_prompt() + """

When writing code:
1. Provide clean, well-commented code
2. Follow best practices and coding standards
3. Include error handling where appropriate
4. Explain the code logic in plain language
5. Suggest optimizations if applicable

Format your response with:
- **Code**: The complete code solution with proper syntax highlighting
- **Explanation**: How the code works
- **Usage Example**: How to use the code
- **Notes**: Any important considerations
"""

        try:
            response_text = await llm_service.chat(
                prompt=f"{system_prompt}\n\nUser Request: {context.user_query}",
                model="deepseek-chat"
            )

            return self.format_response(
                text=response_text,
                reasoning="Applied software engineering principles and best practices",
                confidence=0.95,
                metadata={"agent_type": "code", "model": "deepseek"}
            )

        except Exception as e:
            logger.error(f"CodeAgent error: {e}")
            return self.format_response(
                text=f"Sorry, I encountered an error while generating code: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )


class WritingAgent(BaseAgent):
    """写作专家智能体"""

    def __init__(self):
        super().__init__()
        self.role = AgentRole.WRITING
        self.name = "Writing Expert"
        self.description = "Specialist in writing, grammar, and content creation"
        self.capabilities = [
            "Write essays, articles, and reports",
            "Improve grammar and style",
            "Create study guides and summaries",
            "Generate quiz questions",
            "Provide writing feedback"
        ]

    def can_handle(self, query: str) -> float:
        """判断是否为写作相关查询"""
        writing_keywords = [
            "写", "write", "作文", "essay", "文章", "article",
            "报告", "report", "总结", "summary", "语法", "grammar",
            "润色", "polish", "修改", "revise", "问题", "question",
            "quiz", "测试"
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in writing_keywords if kw in query_lower)

        confidence = min(matches * 0.25, 1.0)
        return confidence

    async def process(self, context: AgentContext) -> AgentResponse:
        """处理写作任务"""
        logger.info(f"WritingAgent processing: {context.user_query[:50]}...")

        system_prompt = self.get_system_prompt() + """

When assisting with writing:
1. Use clear, concise language
2. Maintain proper grammar and punctuation
3. Organize content logically
4. Adapt tone to the context (formal/informal)
5. Provide constructive feedback

Format your response with:
- **Content**: The written piece or revised text
- **Explanation**: Key writing choices made
- **Tips**: Writing tips for improvement
"""

        try:
            response_text = await llm_service.chat(
                prompt=f"{system_prompt}\n\nUser Request: {context.user_query}",
                model="qwen-plus"  # 使用 Qwen 进行中文写作
            )

            return self.format_response(
                text=response_text,
                reasoning="Applied writing best practices and style guidelines",
                confidence=0.9,
                metadata={"agent_type": "writing", "model": "qwen"}
            )

        except Exception as e:
            logger.error(f"WritingAgent error: {e}")
            return self.format_response(
                text=f"Sorry, I encountered an error while writing: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )


class ScienceAgent(BaseAgent):
    """科学专家智能体"""

    def __init__(self):
        super().__init__()
        self.role = AgentRole.SCIENCE
        self.name = "Science Expert"
        self.description = "Specialist in scientific concepts, experiments, and research"
        self.capabilities = [
            "Explain scientific phenomena",
            "Design experiments",
            "Analyze scientific data",
            "Discuss physics, chemistry, biology concepts",
            "Provide scientific context and background"
        ]

    def can_handle(self, query: str) -> float:
        """判断是否为科学相关查询"""
        science_keywords = [
            "物理", "physics", "化学", "chemistry", "生物", "biology",
            "实验", "experiment", "科学", "science", "理论", "theory",
            "原理", "principle", "现象", "phenomenon", "分子", "molecule",
            "原子", "atom", "能量", "energy", "力", "force"
        ]

        query_lower = query.lower()
        matches = sum(1 for kw in science_keywords if kw in query_lower)

        confidence = min(matches * 0.25, 1.0)
        return confidence

    async def process(self, context: AgentContext) -> AgentResponse:
        """处理科学问题"""
        logger.info(f"ScienceAgent processing: {context.user_query[:50]}...")

        system_prompt = self.get_system_prompt() + """

When explaining science:
1. Use clear, accessible language
2. Provide real-world examples
3. Explain the underlying principles
4. Reference established scientific theories
5. Distinguish facts from hypotheses

Format your response with:
- **Concept**: The scientific concept explained
- **Explanation**: Detailed explanation with examples
- **Real-world Application**: How this applies in practice
- **Further Reading**: Suggested topics to explore
"""

        try:
            response_text = await llm_service.chat(
                prompt=f"{system_prompt}\n\nUser Question: {context.user_query}",
                model="qwen-plus"
            )

            return self.format_response(
                text=response_text,
                reasoning="Applied scientific method and evidence-based reasoning",
                confidence=0.85,
                metadata={"agent_type": "science", "model": "qwen"}
            )

        except Exception as e:
            logger.error(f"ScienceAgent error: {e}")
            return self.format_response(
                text=f"Sorry, I encountered an error while processing this science question: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )
