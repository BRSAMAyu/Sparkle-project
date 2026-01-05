from typing import List, Dict, Any
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app.agents.graph.state import SparkleState
from app.agents.graph.llm_factory import LLMFactory

# Import new tools
from app.agents.tools.document_tools import ParseDocumentTool, ConceptExtractionTool
from app.agents.tools.galaxy_tools import GalaxyUpdateTool
from app.agents.tools.analysis_tools import ExamAnalysisTool
from app.agents.tools.generator_tools import FlashcardGeneratorTool, QuestionGeneratorTool
from app.agents.tools.scheduling_tools import StudyPlanCreatorTool

# ... (Previous Mock Tools) ...


@tool
def analyze_past_papers(subject: str) -> str:
    """Analyze past exam papers to surface common topics."""
    return f"Past paper analysis placeholder for {subject}."


@tool
def predict_exam_focus(subject: str) -> str:
    """Predict likely exam focus areas for a subject."""
    return f"Exam focus prediction placeholder for {subject}."

# --- 2. 节点逻辑 (Node Logic) ---

async def exam_oracle_node(state: SparkleState):
    """
    Exam Oracle 专家节点
    负责考点预测、真题分析、模拟出题、文档清洗、任务调度
    """
    messages = state["messages"]
    
    # 使用强推理模型 (GPT-4o) 处理复杂分析
    llm = LLMFactory.get_llm("exam_oracle")
    
    # 绑定工具
    # Updated with Scheduling capabilities (The Execution Loop)
    tools = [
        analyze_past_papers, 
        predict_exam_focus,
        ParseDocumentTool(),
        ConceptExtractionTool(),
        GalaxyUpdateTool(),
        ExamAnalysisTool(),
        FlashcardGeneratorTool(),
        QuestionGeneratorTool(),
        StudyPlanCreatorTool()
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # 执行推理
    response = await llm_with_tools.ainvoke(messages)
    
    return {
        "messages": [response],
        "active_agent": "exam_oracle",
        "next_step": None 
    }
