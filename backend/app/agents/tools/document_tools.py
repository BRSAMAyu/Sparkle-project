from typing import List, Dict, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import os
from pypdf import PdfReader

class ParseDocumentInput(BaseModel):
    file_path: str = Field(..., description="The absolute path to the document file (PDF or TXT).")

import asyncio
from typing import List, Dict, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.services.document_service import document_service

class ParseDocumentInput(BaseModel):
    file_path: str = Field(..., description="The absolute path to the document file (PDF, DOCX, PPTX).")

class ParseDocumentTool(BaseTool):
    name: str = "parse_document"
    description: str = "Reads document. For large files, auto-generates a concept summary map to save tokens."
    args_schema: Type[BaseModel] = ParseDocumentInput

    def _run(self, file_path: str) -> str:
        return asyncio.run(self._arun(file_path))

    async def _arun(self, file_path: str) -> str:
        try:
            result = await document_service.clean_and_summarize(file_path)
            
            if result.get("status") in ["failed", "error"]:
                return f"Error: {result.get('error')}"
            
            if result.get("mode") == "full_text":
                return f"Document Content ({result['char_count']} chars):\n\n{result['full_text']}"
            else:
                return result['summary'] # Return the map-reduce summary

        except Exception as e:
            return f"Error parsing file: {str(e)}"



# Define the structure for extracted concepts
class ExtractedConcept(BaseModel):
    name: str = Field(..., description="Name of the concept (e.g., 'Taylor Series').")
    importance: str = Field(..., description="Importance level: High, Medium, Low.")
    context: str = Field(..., description="Brief context or definition from the text.")
    is_exam_point: bool = Field(False, description="True if marked as 'exam', 'test', 'important'.")

class ExtractConceptsInput(BaseModel):
    text_segment: str = Field(..., description="The text content to analyze.")

# Note: This tool usually wraps an LLM call. 
# In a real scenario, this might be a Chain, not just a Tool, 
# but for the Agent's toolbox, we can wrap the LLM call here.
# For now, I will create a placeholder implementation that uses simple keyword extraction
# or assumes the Agent (ExamOracle) uses its own brain to extract this.
# 
# BETTER APPROACH:
# The ExamOracle *is* the intelligence. It should use `parse_document` to get text,
# and then *internally* use structured output to digest it.
# So we might not strictly need an `extract_concepts` *tool* if the Agent does it directly.
# However, providing a specific tool for "Concept Extraction" allows us to use a smaller/specialized
# LLM or specific prompt for this task, decoupling it from the main chat.

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.agents.graph.llm_factory import LLMFactory

class ConceptExtractionTool(BaseTool):
    name: str = "extract_concepts"
    description: str = "Analyzes text to extract key learning concepts and exam metadata."
    args_schema: Type[BaseModel] = ExtractConceptsInput

    def _run(self, text_segment: str) -> str:
        # We need to invoke an LLM here.
        # Ideally we use dependency injection, but for this Tool class we might lazy load.
        try:
            llm = LLMFactory.get_llm("galaxy_guide", temperature=0) # Use precise mode
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert educational content analyzer. Extract key concepts from the text."),
                ("human", "Analyze the following text and extract key concepts (JSON format list with name, importance, context, is_exam_point):\n\n{text}")
            ])
            
            # Simple chain
            chain = prompt | llm
            
            # We run it synchronously here (LangChain tools are sync by default unless async implemented)
            # Since we are in an async environment, we should ideally use `_arun`.
            # But for simplicity in this prototype, we stick to sync or standard invoke.
            # Wait, LLMFactory returns an Async capable LLM.
            # I will implement `_run` using `invoke` which might block.
            # Let's just return a instruction for the main Agent to do it, 
            # OR implement _arun.
            
            response = chain.invoke({"text": text_segment})
            return response.content
            
        except Exception as e:
            return f"Error extracting concepts: {str(e)}"
    
    async def _arun(self, text_segment: str) -> str:
        try:
            llm = LLMFactory.get_llm("galaxy_guide", temperature=0)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert educational content analyzer. Extract key concepts from the text. Return ONLY a JSON array."),
                ("human", "Analyze: {text}")
            ])
            chain = prompt | llm
            response = await chain.ainvoke({"text": text_segment})
            return response.content
        except Exception as e:
            return f"Error: {e}"
