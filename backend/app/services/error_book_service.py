"""
错题档案服务层 - Phase 4 Optimized
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, update, or_, String
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from uuid import UUID
import random
import json
from loguru import logger

from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.schemas.error_book import (
    ErrorRecordCreate, ErrorRecordUpdate, ErrorQueryParams,
    ErrorAnalysisResult, ReviewAction, ReviewPerformanceEnum,
    KnowledgeLinkBrief
)
from app.core.llm_client import llm_client
from app.services.embedding_service import embedding_service

class ReviewSchedulerService:
    """
    复习计划调度服务
    SM-2 Algorithm with Fuzzing/Jitter to prevent review bombing.
    """
    
    def calculate_next_review(
        self,
        current_mastery: float,
        easiness_factor: float,
        interval_days: float,
        review_count: int,
        performance: ReviewPerformanceEnum
    ) -> Tuple[float, float, float, datetime]:
        """
        Returns: (new_mastery, new_ef, new_interval, next_review_date)
        """
        now = datetime.utcnow()
        
        # SM-2 Logic
        # Quality: Forgotten=1, Fuzzy=3, Remembered=5 (simplified mapping)
        if performance == ReviewPerformanceEnum.REMEMBERED:
            quality = 5
        elif performance == ReviewPerformanceEnum.FUZZY:
            quality = 3
        else: # Forgotten
            quality = 1 
            
        # 1. Update Easiness Factor (EF)
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef) # SM-2 minimum EF
        
        # 2. Update Interval
        if quality < 3:
            # Failed
            new_interval = 1.0
            review_count = 0 # Reset count or keep? SM-2 usually resets interval chain
        else:
            if review_count == 0:
                new_interval = 1.0
            elif review_count == 1:
                new_interval = 6.0
            else:
                new_interval = interval_days * new_ef
            
            review_count += 1
            
        # 3. Update Mastery (Simplified)
        if quality == 5:
            new_mastery = min(1.0, current_mastery + 0.15)
        elif quality == 3:
            new_mastery = max(0.0, current_mastery - 0.05)
        else:
            new_mastery = max(0.0, current_mastery - 0.2)

        # 4. Apply Jitter (Fuzzing) ±10%
        # Do not fuzz if interval is small (<= 1 day)
        if new_interval > 1.5:
            jitter = random.uniform(0.9, 1.1)
            final_interval = new_interval * jitter
        else:
            final_interval = new_interval
            
        next_review = now + timedelta(days=final_interval)
        
        return new_mastery, new_ef, final_interval, next_review


class ErrorBookService:
    """
    错题档案核心服务 (Phase 4)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.review_scheduler = ReviewSchedulerService()
    
    async def create_error(self, user_id: UUID, data: ErrorRecordCreate) -> ErrorRecord:
        error = ErrorRecord(
            user_id=user_id,
            question_text=data.question_text,
            question_image_url=data.question_image_url,
            user_answer=data.user_answer,
            correct_answer=data.correct_answer,
            subject_code=data.subject.value,
            chapter=data.chapter,
            
            # Initial State
            next_review_at=datetime.utcnow(), # Immediate review or +1 day? Usually immediate for first learn.
            interval_days=0.0,
            easiness_factor=2.5,
            review_count=0,
            mastery_level=0.0
        )
        
        self.db.add(error)
        await self.db.commit()
        await self.db.refresh(error)
        
        logger.info(f"Created error record {error.id} for user {user_id}")
        return error
    
    async def analyze_and_link(self, error_id: UUID, user_id: UUID):
        """
        Async Background Task:
        1. Check/Run OCR
        2. RAG Retrieval
        3. LLM Analysis
        4. Update DB
        """
        # Note: This runs in a background task, so we need to ensure the session is valid.
        # Ideally, the caller handles the session scope, or we use a fresh session here.
        # Assuming `self.db` is valid or using `AsyncSessionLocal` pattern in the worker wrapper.
        # Here we assume self.db is injected correctly (likely needing a fresh session if run in background).
        
        try:
            stmt = select(ErrorRecord).where(ErrorRecord.id == error_id)
            res = await self.db.execute(stmt)
            error = res.scalar_one_or_none()
            
            if not error:
                logger.error(f"Error {error_id} not found for analysis")
                return

            # --- Step 1: OCR / Text Check ---
            ocr_text = None
            final_text = error.question_text or ""
            
            if error.question_image_url and (not error.question_text or len(error.question_text) < 10):
                # Trigger OCR
                logger.info(f"Running OCR for error {error.id}")
                ocr_text = await self._run_mock_ocr(error.question_image_url)
                if ocr_text:
                    final_text = f"{final_text}\n[OCR]: {ocr_text}".strip()
                    # Optionally update the record's text or just keep it for analysis context
                    # Let's save it in latest_analysis['ocr_text'] later.

            if not final_text:
                logger.warning("No text available for analysis")
                return

            # --- Step 2: RAG Retrieval ---
            linked_ids = []
            suggested_concepts = []
            
            try:
                # Retrieve relevant knowledge nodes
                nodes = await self._search_knowledge_nodes(user_id, final_text)
                if nodes:
                    linked_ids = [n.id for n in nodes]
                    logger.info(f"Found {len(linked_ids)} linked nodes for error {error.id}")
                else:
                    logger.info("No relevant nodes found (Cold Start), asking LLM for suggestions")
            except Exception as e:
                logger.error(f"RAG search failed: {e}")
                # Continue without links

            # --- Step 3: LLM Analysis ---
            analysis_result = await self._run_llm_analysis(
                subject=error.subject_code,
                question=final_text,
                user_ans=error.user_answer,
                correct_ans=error.correct_answer,
                linked_nodes=nodes if 'nodes' in locals() and nodes else []
            )
            
            if ocr_text:
                analysis_result['ocr_text'] = ocr_text
            
            # Extract suggested concepts if any (from LLM or fallback)
            # Currently strict JSON schema doesn't have 'suggested_concepts' in top level, 
            # but we can add it to the DB column.
            
            # --- Step 4: Update DB ---
            error.latest_analysis = analysis_result
            error.linked_knowledge_node_ids = linked_ids
            # error.suggested_concepts = ... (if LLM returns them)
            
            # If question text was empty, maybe fill it with OCR?
            if not error.question_text and ocr_text:
                error.question_text = ocr_text

            await self.db.commit()
            logger.info(f"Analysis completed for error {error.id}")

        except Exception as e:
            logger.error(f"Async analysis failed for error {error_id}: {e}")
            await self.db.rollback()

    async def _run_mock_ocr(self, image_url: str) -> str:
        # TODO: Integrate real OCR service (e.g., GPT-4o Vision or Tesseract)
        return "Simulated OCR Text: This is a placeholder for the text extracted from the image."

    async def _search_knowledge_nodes(self, user_id: UUID, text: str, limit: int = 3) -> List[KnowledgeNode]:
        # Generate embedding
        embedding = await embedding_service.get_embedding(text)
        
        # PGVector search
        # Note: This requires the KnowledgeNode model to have the `embedding` column and pgvector extension
        # We assume KnowledgeNode.embedding is mapped.
        stmt = select(KnowledgeNode).order_by(
            KnowledgeNode.embedding.l2_distance(embedding)
        ).limit(limit)
        
        # Filter by user? Global vs User nodes?
        # Assuming global syllabus nodes + user specific nodes.
        # But KnowledgeNode table usually has user_id.
        # For now, search all visible nodes (public or user's).
        # stmt = stmt.where(or_(KnowledgeNode.user_id == user_id, KnowledgeNode.is_public == True))
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _run_llm_analysis(self, subject, question, user_ans, correct_ans, linked_nodes) -> dict:
        node_context = ", ".join([n.name for n in linked_nodes])
        
        prompt = f"""
        Analyze this {subject} error.
        Question: {question}
        Student Answer: {user_ans}
        Correct Answer: {correct_ans}
        Related Concepts: {node_context}
        
        Provide output in JSON:
        {{
            "error_type": "concept_confusion" | "calculation_error" | "reading_careless" | "knowledge_gap" | "method_wrong" | "logic_error" | "other",
            "error_type_label": "Short Chinese Label",
            "root_cause": "Detailed analysis...",
            "correct_approach": "Step-by-step approach...",
            "similar_traps": ["Trap 1", "Trap 2"],
            "recommended_knowledge": ["Concept 1", "Concept 2"],
            "study_suggestion": "Actionable advice..."
        }}
        """
        
        try:
            response = await llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert tutor."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            # Parse JSON
            if isinstance(response, str):
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                content = json_match.group(1) if json_match else response
                return json.loads(content)
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "error_type": "other",
                "error_type_label": "分析失败",
                "root_cause": "暂时无法进行智能分析",
                "correct_approach": "请参考正确答案",
                "similar_traps": [],
                "recommended_knowledge": [],
                "study_suggestion": "请稍后重试"
            }

    async def get_error(self, error_id: UUID, user_id: UUID) -> Optional[ErrorRecord]:
        stmt = select(ErrorRecord).where(
            and_(
                ErrorRecord.id == error_id,
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record and record.linked_knowledge_node_ids:
            # Manually fetch knowledge nodes for response mapping
            # This transient data handling is tricky with Pydantic from_attributes=True
            # We might need to attach it to the record instance dynamically
            node_stmt = select(KnowledgeNode).where(KnowledgeNode.id.in_(record.linked_knowledge_node_ids))
            nodes = (await self.db.execute(node_stmt)).scalars().all()
            
            # Create transient list of dicts/objects expected by Schema
            record.knowledge_links = [
                KnowledgeLinkBrief(id=n.id, name=n.name, is_primary=True) 
                for n in nodes
            ]
        
        return record

    async def list_errors(
        self, 
        user_id: UUID, 
        params: ErrorQueryParams
    ) -> Tuple[List[ErrorRecord], int]:
        query = select(ErrorRecord).where(
            and_(
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted == False
            )
        )
        
        if params.subject:
            query = query.where(ErrorRecord.subject_code == params.subject.value)
        if params.chapter:
            query = query.where(ErrorRecord.chapter.ilike(f"%{params.chapter}%"))
        if params.mastery_min is not None:
            query = query.where(ErrorRecord.mastery_level >= params.mastery_min)
        if params.mastery_max is not None:
            query = query.where(ErrorRecord.mastery_level <= params.mastery_max)
        if params.need_review:
            query = query.where(ErrorRecord.next_review_at <= datetime.utcnow())
        if params.keyword:
            # Search in text or analysis or OCR
            query = query.where(
                or_(
                    ErrorRecord.question_text.ilike(f"%{params.keyword}%"),
                    func.cast(ErrorRecord.latest_analysis, String).ilike(f"%{params.keyword}%")
                )
            )
            
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0
        
        # Order
        query = query.order_by(
            ErrorRecord.next_review_at.asc().nullslast(),
            ErrorRecord.created_at.desc()
        ).offset((params.page - 1) * params.page_size).limit(params.page_size)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        # Optimizing list view: likely don't need full knowledge link details for every item
        # If needed, we'd need a batched fetch strategy.
        
        return items, total

    async def update_error(self, error_id: UUID, user_id: UUID, data: ErrorRecordUpdate) -> Optional[ErrorRecord]:
        error = await self.get_error(error_id, user_id)
        if not error:
            return None
            
        update_data = data.dict(exclude_unset=True)
        # Rename subject to subject_code if present
        if 'subject' in update_data:
            update_data['subject_code'] = update_data.pop('subject').value
            
        for key, value in update_data.items():
            if hasattr(error, key):
                setattr(error, key, value)
                
        await self.db.commit()
        await self.db.refresh(error)
        return error

    async def delete_error(self, error_id: UUID, user_id: UUID) -> bool:
        stmt = select(ErrorRecord).where(
            and_(ErrorRecord.id == error_id, ErrorRecord.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        error = result.scalar_one_or_none()
        
        if not error:
            return False
            
        error.is_deleted = True
        await self.db.commit()
        return True

    async def submit_review(self, user_id: UUID, error_id: UUID, data: ReviewAction) -> ErrorRecord:
        error = await self.get_error(error_id, user_id)
        if not error:
            raise ValueError(f"Error {error_id} not found")
        
        # Calculate new schedule
        new_mastery, new_ef, new_interval, next_review = self.review_scheduler.calculate_next_review(
            current_mastery=error.mastery_level or 0.0,
            easiness_factor=error.easiness_factor or 2.5,
            interval_days=error.interval_days or 0.0,
            review_count=error.review_count or 0,
            performance=data.performance
        )
        
        # Update Record
        error.mastery_level = new_mastery
        error.easiness_factor = new_ef
        error.interval_days = new_interval
        error.next_review_at = next_review
        error.review_count = (error.review_count or 0) + 1
        error.last_reviewed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(error)
        
        return error

    async def get_review_stats(self, user_id: UUID) -> dict:
        # Base query
        base_filter = and_(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted == False)
        
        total = await self.db.scalar(
            select(func.count()).select_from(ErrorRecord).where(base_filter)
        )
        
        mastered = await self.db.scalar(
            select(func.count()).select_from(ErrorRecord).where(
                and_(base_filter, ErrorRecord.mastery_level >= 0.8)
            )
        )
        
        need_review = await self.db.scalar(
            select(func.count()).select_from(ErrorRecord).where(
                and_(base_filter, ErrorRecord.next_review_at <= datetime.utcnow())
            )
        )
        
        subject_result = await self.db.execute(
            select(ErrorRecord.subject_code, func.count())
            .where(base_filter)
            .group_by(ErrorRecord.subject_code)
        )
        subject_distribution = {row[0]: row[1] for row in subject_result}
        
        return {
            "total_errors": total or 0,
            "mastered_count": mastered or 0,
            "need_review_count": need_review or 0,
            "review_streak_days": 0, # TODO: Calculate from study logs
            "subject_distribution": subject_distribution
        }