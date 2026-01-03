from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
import json
from loguru import logger

from app.models.cognitive import CognitiveFragment, BehaviorPattern, AnalysisStatus
from app.models.user import User
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.services.analytics_service import AnalyticsService

class CognitiveService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = AnalyticsService(db)

    def _sanitize_content(self, content: str) -> str:
        """Sanitize user content for logging."""
        if not content:
            return ""
        return f"{content[:15]}... [len={len(content)}]"

    async def create_fragment(
        self,
        user_id: UUID,
        content: str,
        source_type: str,
        resource_type: str = "text",
        resource_url: Optional[str] = None,
        context_tags: Optional[dict] = None,
        error_tags: Optional[List[str]] = None,
        severity: int = 1,
        task_id: Optional[UUID] = None,
        fragment_id: Optional[UUID] = None
    ) -> CognitiveFragment:
        """Create a new cognitive fragment and generate its embedding."""
        
        # 1. Create Fragment Object
        fragment = CognitiveFragment(
            id=fragment_id or uuid4(),
            user_id=user_id,
            content=content,
            source_type=source_type,
            resource_type=resource_type,
            resource_url=resource_url,
            context_tags=context_tags,
            error_tags=error_tags,
            severity=severity,
            task_id=task_id,
            analysis_status=AnalysisStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        logger.info(f"Creating fragment {fragment.id} for user {user_id}: {self._sanitize_content(content)}")
        
        # 2. Generate Embedding
        try:
            embedding = await embedding_service.get_embedding(content)
            fragment.embedding = embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for fragment: {e}")
            # We continue without embedding, but RAG won't work for this item until updated
        
        self.db.add(fragment)
        await self.db.commit()
        await self.db.refresh(fragment)
        
        return fragment

    async def analyze_behavior(self, user_id: UUID, fragment_id: UUID) -> Dict:
        """
        Analyze a specific fragment using RAG + LLM to identify behavioral patterns.
        Returns the analysis result and potentially created/updated pattern.
        """
        # 1. Fetch Target Fragment
        stmt = select(CognitiveFragment).where(CognitiveFragment.id == fragment_id)
        result = await self.db.execute(stmt)
        fragment = result.scalar_one_or_none()
        
        if not fragment:
            logger.error(f"Fragment {fragment_id} not found for analysis")
            raise ValueError("Fragment not found")
            
        try:
            # Update Status to PROCESSING (Patch 2)
            fragment.analysis_status = AnalysisStatus.PROCESSING
            await self.db.commit()

            logger.info(f"Analyzing fragment {fragment_id}: {self._sanitize_content(fragment.content)}")

            # 2. RAG: Retrieve Similar Fragments
            similar_fragments = []
            if fragment.embedding is not None:
                # Use pgvector cosine distance
                from pgvector.sqlalchemy import Vector
                
                rag_query = (
                    select(CognitiveFragment)
                    .where(CognitiveFragment.user_id == user_id)
                    .where(CognitiveFragment.id != fragment_id) 
                    .where(CognitiveFragment.embedding.isnot(None))
                    .order_by(CognitiveFragment.embedding.cosine_distance(fragment.embedding))
                    .limit(3)
                )
                rag_result = await self.db.execute(rag_query)
                similar_fragments = rag_result.scalars().all()
                
            similar_text = "\n".join([f"- {f.content} (Tags: {f.error_tags})" for f in similar_fragments])
            
            # 3. Get User Context
            user_summary = await self.analytics_service.get_user_profile_summary(user_id)
            
            # 4. Construct Prompt
            prompt = f"""
            Analyze this behavioral error/thought:
            User Input: "{fragment.content}"
            Context: {fragment.context_tags}
            Error Tags: {fragment.error_tags}
            Severity: {fragment.severity}/5
            
            Similar Past Events (RAG Context):
            {similar_text}
            
            User Profile:
            {user_summary}
            
            Task:
            1. Identify the Root Cause.
            2. Identify Pattern.
            3. Suggest SMART Intervention.
            4. Provide Confidence Score (0.0 - 1.0).
            
            Output JSON Format:
            {{
                "root_cause": "...",
                "pattern_name": "...",
                "pattern_type": "cognitive/emotional/execution",
                "description": "...",
                "solution_text": "...",
                "confidence_score": 0.85
            }}
            """
            
            messages = [
                {"role": "system", "content": "You are an expert Cognitive Behavioral Therapist and Learning Coach. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ]
            
            # 5. Call LLM
            response_text = await llm_service.chat(messages, temperature=0.5)
            
            try:
                cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                analysis = json.loads(cleaned_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM analysis for {fragment_id}")
                fragment.analysis_status = AnalysisStatus.FAILED
                fragment.error_message = "Invalid JSON from LLM"
                await self.db.commit()
                return {"error": "Analysis failed parsing"}
                
            # 6. Save/Update Pattern
            if analysis.get("confidence_score", 0) > 0.6:
                await self._upsert_pattern(user_id, analysis, fragment_id)
            
            # Update Status to COMPLETED
            fragment.analysis_status = AnalysisStatus.COMPLETED
            await self.db.commit()
            logger.info(f"Successfully analyzed fragment {fragment_id}")
            return analysis

        except Exception as e:
            logger.exception(f"Error during behavior analysis for {fragment_id}: {e}")
            fragment.analysis_status = AnalysisStatus.FAILED
            fragment.error_message = str(e)[:200]
            await self.db.commit()
            return {"error": str(e)}

    async def _upsert_pattern(self, user_id: UUID, analysis: Dict, fragment_id: UUID):
        """Find existing pattern or create new one."""
        pattern_name = analysis.get("pattern_name", "Unknown Pattern")
        
        # Simple string matching for now. Ideal: Vector search on pattern descriptions.
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.pattern_name == pattern_name
        )
        result = await self.db.execute(stmt)
        pattern = result.scalar_one_or_none()
        
        if pattern:
            # Update existing
            pattern.frequency += 1
            # Update confidence (simple moving average-ish or max)
            pattern.confidence_score = max(pattern.confidence_score, analysis.get("confidence_score", 0))
            if pattern.evidence_ids:
                # evidence_ids is JSON list
                try:
                    ev_list = json.loads(pattern.evidence_ids) if isinstance(pattern.evidence_ids, str) else pattern.evidence_ids
                    if str(fragment_id) not in ev_list:
                            ev_list.append(str(fragment_id))
                            pattern.evidence_ids = ev_list
                except:
                    pattern.evidence_ids = [str(fragment_id)]
            else:
                pattern.evidence_ids = [str(fragment_id)]
        else:
            # Create new
            pattern = BehaviorPattern(
                user_id=user_id,
                pattern_name=pattern_name,
                pattern_type=analysis.get("pattern_type", "execution"),
                description=analysis.get("description"),
                solution_text=analysis.get("solution_text"),
                confidence_score=analysis.get("confidence_score", 0),
                frequency=1,
                evidence_ids=[str(fragment_id)]
            )
            self.db.add(pattern)
            
        await self.db.commit()

    async def get_fragments(self, user_id: UUID, limit: int = 20, offset: int = 0) -> List[CognitiveFragment]:
        """Get list of fragments for a user."""
        stmt = (
            select(CognitiveFragment)
            .where(CognitiveFragment.user_id == user_id)
            .order_by(desc(CognitiveFragment.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    