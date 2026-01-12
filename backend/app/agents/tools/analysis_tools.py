from typing import List, Dict, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode, UserNodeStatus

# --- Models ---

class ConceptAnalysisResult(BaseModel):
    concept_name: str
    source_importance: str # High/Medium/Low from document
    user_mastery: float    # 0.0 - 1.0 from Prism
    priority: str          # CRITICAL, IMPORTANT, REVIEW, SAFE, IGNORE
    reason: str

class ExamPredictionReport(BaseModel):
    critical_concepts: List[ConceptAnalysisResult]
    safe_concepts: List[ConceptAnalysisResult]
    suggested_strategy: str # "Crash Course" vs "Deep Review"

class AnalyzeConceptsInput(BaseModel):
    concepts: List[Dict] = Field(..., description="List of concepts extracted from documents (as dicts).")
    user_id: str = Field(..., description="The user's ID.")
    user_patterns: List[Dict] = Field(default=[], description="List of user behavior patterns (e.g. {'pattern_name': 'careless_reader', 'type': 'execution'}).")

# --- Tool ---

class ExamAnalysisTool(BaseTool):
    name: str = "analyze_exam_concepts"
    description: str = (
        "Analyzes concepts against user mastery (Galaxy) AND behavior patterns "
        "(Cognitive Prism) to determine exam priority."
    )
    args_schema: Type[BaseModel] = AnalyzeConceptsInput

    def _run(self, concepts: List[Dict], user_id: str, user_patterns: List[Dict] = []) -> Dict:
        raise NotImplementedError("Use async _arun")
    
    async def _arun(self, concepts: List[Dict], user_id: str, user_patterns: List[Dict] = []) -> Dict:
        # 1. Batch fetch REAL mastery from Galaxy DB
        concept_names = [c.get("name") for c in concepts]
        mastery_map = await self._fetch_user_mastery_real(user_id, concept_names)

        results = []
        critical_count = 0
        risk_count = 0
        
        # 2. Extract key behavior tags for O(1) lookup
        behavior_flags = {
            "careless": any("careless" in p.get("pattern_name", "").lower() for p in user_patterns),
            "calc_error": any("calc" in p.get("pattern_name", "").lower() for p in user_patterns),
            "anxiety": any("anxiety" in p.get("pattern_name", "").lower() for p in user_patterns),
        }

        for c in concepts:
            name = c.get("name")
            importance = c.get("importance", "Medium")
            context = c.get("context", "").lower()
            
            # Default to 0.5 if not found in Galaxy (treat as "uncertain/needs review")
            mastery = mastery_map.get(name.lower(), 0.5)
            
            # --- FUSION LOGIC ---
            priority, reason, strategy_hint = self._calculate_priority_with_behavior(
                importance, mastery, context, behavior_flags
            )
            
            if priority == "CRITICAL":
                critical_count += 1
            if priority == "RISKY":
                risk_count += 1
                
            results.append(ConceptAnalysisResult(
                concept_name=name,
                source_importance=importance,
                user_mastery=mastery,
                priority=priority,
                reason=reason
            ).dict())

        # 3. Determine Global Strategy
        strategy = "Deep Review"
        summary = f"Identified {critical_count} critical weaknesses and {risk_count} behavioral risks."
        
        if critical_count > 5:
            strategy = "Crash Course (Focus on High Frequency)"
        elif behavior_flags["anxiety"] and critical_count > 0:
            strategy = "Confidence Building (Easy -> Hard)"
        elif risk_count > 3:
            strategy = "Precision Drill (Focus on reducing careless errors)"
        elif critical_count == 0:
            strategy = "Maintenance Mode"

        return {
            "analysis": results,
            "strategy": strategy,
            "summary": summary
        }

    async def _fetch_user_mastery_real(self, user_id: str, concepts: List[str]) -> Dict[str, float]:
        """
        Fetches mastery scores from Galaxy DB using case-insensitive name matching.
        Returns: Dict[lowercase_concept_name, mastery_score_0_to_1]
        """
        async with AsyncSessionLocal() as db:
            try:
                # Normalize names for lookup
                lower_names = [n.lower() for n in concepts]
                
                # Query KnowledgeNode + UserNodeStatus
                stmt = (
                    select(KnowledgeNode.name, UserNodeStatus.mastery_score)
                    .join(UserNodeStatus, KnowledgeNode.id == UserNodeStatus.node_id)
                    .where(
                        UserNodeStatus.user_id == user_id,
                        func.lower(KnowledgeNode.name).in_(lower_names)
                    )
                )
                
                result = await db.execute(stmt)
                rows = result.fetchall()
                
                mastery_map = {}
                for name, score in rows:
                    # Score is 0-100 in DB, convert to 0-1 for logic
                    mastery_map[name.lower()] = score / 100.0
                    
                return mastery_map
                
            except Exception as e:
                # Fallback to empty map on DB error to allow partial function
                print(f"DB Error in AnalysisTool: {e}")
                return {}

    def _calculate_priority_with_behavior(self, importance: str, mastery: float, context: str, behaviors: Dict[str, bool]) -> (str, str, str):
        """
        The Fusion Decision Matrix:
        (Importance, Mastery, Context, Behavior) -> (Priority, Reason, Strategy)
        """
        imp_score = 3 if importance.lower() == "high" else (2 if importance.lower() == "medium" else 1)
        
        # 1. Behavior Overrides (The "Hidden Killer" Logic)
        
        # Case A: Good mastery, but careless on Calculation-heavy topics
        is_calculation = "formula" in context or "calculate" in context or "compute" in context
        if is_calculation and behaviors["calc_error"] and mastery > 0.7:
            return "RISKY", "Mastered but prone to calculation errors.", "Show Steps Drill"

        # Case B: Good mastery, but careless on Word Problems
        is_word_problem = "application" in context or "problem" in context or "story" in context
        if is_word_problem and behaviors["careless"] and mastery > 0.7:
            return "RISKY", "Mastered but prone to misreading.", "Keyword Highlighting"

        # 2. Standard Knowledge Logic
        if imp_score == 3: # High Importance
            if mastery < 0.4:
                return "CRITICAL", "High frequency concept with low mastery.", "Concept Re-learning"
            elif mastery < 0.7:
                return "IMPORTANT", "High frequency, needs reinforcement.", "Targeted Practice"
            else:
                return "SAFE", "Key concept well mastered.", "Periodic Review"
        
        elif imp_score == 2: # Medium
            if mastery < 0.3:
                return "IMPORTANT", "Medium frequency but significant knowledge gap."
            elif mastery < 0.6:
                return "REVIEW", "Standard review recommended."
            else:
                return "SAFE", "Stable."
                
        else: # Low
            return "IGNORE", "Low priority.", "Ignore"
