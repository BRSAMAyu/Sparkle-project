"""
gRPC Implementation for Error Book Service
"""
import grpc
from typing import Optional
from uuid import UUID
from google.protobuf.timestamp_pb2 import Timestamp

from app.gen.proto.error_book import error_book_pb2, error_book_pb2_grpc
from app.services.error_book_service import ErrorBookService
from app.schemas.error_book import (
    ErrorRecordCreate, ErrorRecordUpdate, ErrorQueryParams,
    ReviewAction, ReviewPerformanceEnum, SubjectEnum, ErrorTypeEnum
)
from app.db.session import AsyncSessionLocal
from app.core.task_manager import task_manager
from app.core.celery_app import schedule_long_task

class ErrorBookGrpcServiceImpl(error_book_pb2_grpc.ErrorBookServiceServicer):

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    async def _run_analysis_task(self, error_id: UUID, user_id: UUID):
        """Helper to run analysis in background with dedicated session"""
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            try:
                await service.analyze_and_link(error_id, user_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Background analysis failed for error {error_id}: {e}")

    async def CreateError(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            try:
                # Convert gRPC request to Pydantic Create Schema
                # Assuming simple mapping for enums or exact string match
                data = ErrorRecordCreate(
                    user_id=request.user_id,
                    question_text=request.question_text if request.question_text else None,
                    question_image_url=request.question_image_url if request.question_image_url else None,
                    user_answer=request.user_answer if request.user_answer else None,
                    correct_answer=request.correct_answer if request.correct_answer else None,
                    subject=SubjectEnum(request.subject_code),
                    chapter=request.chapter if request.chapter else None
                )

                error = await service.create_error(UUID(request.user_id), data)

                # 方案1: 使用 TaskManager (快速任务, < 10秒)
                await task_manager.spawn(
                    self._run_analysis_task(error.id, UUID(request.user_id)),
                    task_name="error_analysis",
                    user_id=request.user_id
                )

                # 方案2: 使用 Celery (长时任务, > 10秒) - 可选
                # schedule_long_task(
                #     "analyze_error_batch",
                #     args=([str(error.id)], request.user_id),
                #     queue="default"
                # )

                return self._map_to_proto(error)
            except ValueError as e:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(str(e))
                return error_book_pb2.ErrorRecord()
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return error_book_pb2.ErrorRecord()

    async def ListErrors(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            
            # Map params
            params = ErrorQueryParams(
                subject=SubjectEnum(request.subject_code) if request.subject_code else None,
                chapter=request.chapter if request.chapter else None,
                error_type=ErrorTypeEnum(request.error_type) if request.error_type else None,
                mastery_min=request.mastery_min if request.HasField('mastery_min') else None,
                mastery_max=request.mastery_max if request.HasField('mastery_max') else None,
                need_review=request.need_review if request.HasField('need_review') else None,
                keyword=request.keyword if request.keyword else None,
                page=request.page if request.page > 0 else 1,
                page_size=request.page_size if request.page_size > 0 else 20
            )
            
            items, total = await service.list_errors(UUID(request.user_id), params)
            
            return error_book_pb2.ListErrorsResponse(
                items=[self._map_to_proto(item) for item in items],
                total=total,
                page=params.page,
                page_size=params.page_size,
                has_next=(params.page * params.page_size) < total
            )

    async def GetError(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            error = await service.get_error(UUID(request.error_id), UUID(request.user_id))
            if not error:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Error record not found")
                return error_book_pb2.ErrorRecord()
            
            return self._map_to_proto(error)

    async def UpdateError(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            
            data = ErrorRecordUpdate(
                question_text=request.question_text if request.HasField('question_text') else None,
                user_answer=request.user_answer if request.HasField('user_answer') else None,
                correct_answer=request.correct_answer if request.HasField('correct_answer') else None,
                subject=SubjectEnum(request.subject_code) if request.HasField('subject_code') else None,
                chapter=request.chapter if request.HasField('chapter') else None,
                question_image_url=request.question_image_url if request.HasField('question_image_url') else None
            )
            
            error = await service.update_error(UUID(request.error_id), UUID(request.user_id), data)
            if not error:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return error_book_pb2.ErrorRecord()
                
            return self._map_to_proto(error)

    async def DeleteError(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            success = await service.delete_error(UUID(request.error_id), UUID(request.user_id))
            return error_book_pb2.DeleteErrorResponse(success=success)

    async def AnalyzeError(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            error = await service.get_error(UUID(request.error_id), UUID(request.user_id))
            if not error:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return error_book_pb2.AnalyzeErrorResponse()
            
            import asyncio
            asyncio.create_task(self._run_analysis_task(UUID(request.error_id), UUID(request.user_id)))
            
            return error_book_pb2.AnalyzeErrorResponse(message="Analysis task submitted")

    async def SubmitReview(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            
            try:
                data = ReviewAction(
                    performance=ReviewPerformanceEnum(request.performance),
                    time_spent_seconds=request.time_spent_seconds
                )
                
                error = await service.submit_review(UUID(request.user_id), UUID(request.error_id), data)
                return self._map_to_proto(error)
                
            except ValueError as e:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(str(e))
                return error_book_pb2.ErrorRecord()
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return error_book_pb2.ErrorRecord()

    async def GetReviewStats(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            stats = await service.get_review_stats(UUID(request.user_id))
            
            return error_book_pb2.ReviewStatsResponse(
                total_errors=stats['total_errors'],
                mastered_count=stats['mastered_count'],
                need_review_count=stats['need_review_count'],
                review_streak_days=stats['review_streak_days'],
                subject_distribution=stats['subject_distribution']
            )

    async def GetTodayReviews(self, request, context):
        async with self.db_session_factory() as db:
            service = ErrorBookService(db)
            params = ErrorQueryParams(
                need_review=True,
                page=request.page if request.page > 0 else 1,
                page_size=request.page_size if request.page_size > 0 else 20
            )
            
            items, total = await service.list_errors(UUID(request.user_id), params)
            
            return error_book_pb2.ListErrorsResponse(
                items=[self._map_to_proto(item) for item in items],
                total=total,
                page=params.page,
                page_size=params.page_size,
                has_next=(params.page * params.page_size) < total
            )

    def _map_to_proto(self, error) -> error_book_pb2.ErrorRecord:
        proto = error_book_pb2.ErrorRecord(
            id=str(error.id),
            user_id=str(error.user_id),
            subject_code=error.subject_code,
            chapter=error.chapter or "",
            question_text=error.question_text or "",
            question_image_url=error.question_image_url or "",
            user_answer=error.user_answer or "",
            correct_answer=error.correct_answer or "",
            mastery_level=error.mastery_level or 0.0,
            review_count=error.review_count or 0,
        )
        
        if error.next_review_at:
            proto.next_review_at.FromDatetime(error.next_review_at)
        if error.last_reviewed_at:
            proto.last_reviewed_at.FromDatetime(error.last_reviewed_at)
        if error.created_at:
            proto.created_at.FromDatetime(error.created_at)
        if error.updated_at:
            proto.updated_at.FromDatetime(error.updated_at)
            
        if error.latest_analysis:
            # error.latest_analysis is dict (from JSONB)
            la = error.latest_analysis
            proto.latest_analysis.CopyFrom(error_book_pb2.ErrorAnalysisResult(
                error_type=la.get('error_type', ''),
                error_type_label=la.get('error_type_label', ''),
                root_cause=la.get('root_cause', ''),
                correct_approach=la.get('correct_approach', ''),
                similar_traps=la.get('similar_traps', []),
                recommended_knowledge=la.get('recommended_knowledge', []),
                study_suggestion=la.get('study_suggestion', ''),
                ocr_text=la.get('ocr_text', '')
            ))
            
        # Mapping transient knowledge links if available
        if hasattr(error, 'knowledge_links') and error.knowledge_links:
            for link in error.knowledge_links:
                # link is KnowledgeLinkBrief (Pydantic) or similar object
                l = proto.knowledge_links.add()
                l.id = str(link.id)
                l.name = link.name
                l.relevance = link.relevance
                l.is_primary = link.is_primary
                
        return proto
