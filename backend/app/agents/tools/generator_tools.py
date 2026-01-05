from typing import List, Dict, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.agents.graph.llm_factory import LLMFactory

# --- Models ---

class GenerateFlashcardsInput(BaseModel):
    concepts: List[Dict] = Field(..., description="List of critical concepts (name, context).")
    style: str = Field("concise", description="Style: concise, detailed, or mnemonic.")

class GenerateQuestionsInput(BaseModel):
    concept_name: str = Field(..., description="Target concept.")
    risk_type: str = Field(..., description="Risk type detected (e.g. 'calc_error', 'concept_confusion').")
    difficulty: str = Field("medium", description="Difficulty level.")

# --- Tools ---

class FlashcardGeneratorTool(BaseTool):
    name: str = "generate_flashcards"
    description: str = "Generates high-density study flashcards for given concepts."
    args_schema: Type[BaseModel] = GenerateFlashcardsInput

    def _run(self, concepts: List[Dict], style: str = "concise") -> str:
        # LLM Call
        try:
            llm = LLMFactory.get_llm("galaxy_guide") # Using Galaxy Guide model for knowledge generation
            
            # Format concepts for prompt
            concepts_text = "\n".join([f"- {c.get('name')}: {c.get('context', '')}" for c in concepts])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert tutor creating study materials."),
                ("human", f"""Create {style} flashcards for the following concepts. 
                Format as a Markdown list. 
                For each card, include:
                1. **Concept Name**
                2. **Core Definition/Formula**
                3. **⚡ Pitfall Alert** (Common mistakes)
                4. **🧠 Mnemonic** (Memory aid, if applicable) 
                
                Concepts:
                {concepts_text}""")
            ])
            
            chain = prompt | llm
            response = chain.invoke({})
            return response.content
            
        except Exception as e:
            return f"Error generating flashcards: {e}"

    async def _arun(self, concepts: List[Dict], style: str = "concise") -> str:
        # Async implementation mimicking _run
        try:
            llm = LLMFactory.get_llm("galaxy_guide")
            concepts_text = "\n".join([f"- {c.get('name')}: {c.get('context', '')}" for c in concepts])
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert tutor. Create Markdown flashcards."),
                ("human", f"Create {style} flashcards for:\n{concepts_text}\nInclude Pitfall Alerts.")
            ])
            chain = prompt | llm
            response = await chain.ainvoke({})
            return response.content
        except Exception as e:
            return f"Error: {e}"


class QuestionGeneratorTool(BaseTool):
    name: str = "generate_practice_question"
    description: str = "Generates a practice question tailored to specific user risks (e.g. calculation errors)."
    args_schema: Type[BaseModel] = GenerateQuestionsInput

    def _run(self, concept_name: str, risk_type: str, difficulty: str = "medium") -> str:
        try:
            llm = LLMFactory.get_llm("exam_oracle") # Exam Oracle is better for question generation
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert exam setter. Generate a practice question."),
                ("human", f"""Generate a {difficulty} difficulty practice question for '{concept_name}'.
                
                **User Profile Constraint**: The user is prone to '{risk_type}'.
                - If 'calc_error': Include complex numbers or multi-step arithmetic.
                - If 'careless_reading': Hide a key constraint in the text (e.g. 'positive integers only').
                - If 'concept_confusion': Create a question that tests the boundary conditions.
                
                Output Format (JSON):
                {{
                    "question": "...",
                    "options": ["A...", "B...", "C...", "D..."],
                    "correct_option": "A",
                    "explanation": "...",
                    "trap_analysis": "Why this specific trap was set for the user."
                }}
                """)
            ])
            
            chain = prompt | llm
            response = chain.invoke({})
            return response.content
            
        except Exception as e:
            return f"Error generating question: {e}"

    async def _arun(self, concept_name: str, risk_type: str, difficulty: str = "medium") -> str:
        try:
            llm = LLMFactory.get_llm("exam_oracle")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an exam setter. Return JSON."),
                ("human", f"Generate {difficulty} question for '{concept_name}' targeting risk '{risk_type}'.")
            ])
            chain = prompt | llm
            response = await chain.ainvoke({})
            return response.content
        except Exception as e:
            return f"Error: {e}"
