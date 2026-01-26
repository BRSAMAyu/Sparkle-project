"""
生词本与词典服务
Vocabulary & Dictionary Service

统一复习算法（与前端 vocab_word.dart 一致）:
- 如果忘记: 1天后复习
- 如果记住:
    - base_interval = (6 - importance).clamp(1, 5)
    - 重要度越高，基础间隔越短
    - interval = base_interval * (2 ^ (consecutive_correct - 1))
    - 上限 180 天
"""
import json
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, Float

from app.models.vocabulary import WordBook, DictionaryEntry
from app.services.llm_service import llm_service


class VocabularyService:
    """生词本与词典服务"""

    MIN_IMPORTANCE = 1
    MAX_IMPORTANCE = 5

    # 旧版艾宾浩斯复习间隔 (天) - DEPRECATED，保留用于向后兼容
    REVIEW_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 60]

    @staticmethod
    def _calculate_next_review(
        importance: int,
        consecutive_correct: int,
        remembered: bool
    ) -> datetime:
        """
        统一复习算法（匹配前端）

        Args:
            importance: 1-5 星，5 星为最需要复习的词汇
            consecutive_correct: 当前连续正确次数
            remembered: 是否记住

        Returns:
            下次复习时间

        算法逻辑:
        - 如果忘记: 1天后复习
        - 如果记住:
            - base_interval = (6 - importance).clamp(1, 5)
            - 重要度 5 -> 基础 1 天（关键词汇）
            - 重要度 1 -> 基础 5 天（普通词汇）
            - interval = base_interval * (2 ^ (consecutive_correct - 1))
            - 上限 180 天
        """
        if not remembered:
            return datetime.utcnow() + timedelta(days=1)

        # 重要度 5 -> 基础 1 天（关键词汇）
        # 重要度 1 -> 基础 5 天（普通词汇）
        base_interval = max(1, min(5, 6 - importance))

        # 指数退避: 2^(streak-1)
        multiplier = 2 ** max(0, consecutive_correct - 1)
        days = base_interval * multiplier

        # 上限 180 天
        days = min(days, 180)

        return datetime.utcnow() + timedelta(days=int(days))

    @staticmethod
    async def import_dictionary(
        db: AsyncSession,
        content: str,
        format: str = 'json',
        source: str = 'unknown'
    ) -> int:
        """
        Import dictionary data from JSON or CSV.
        JSON format expected: [{"word": "...", "definitions": [...], "phonetic": "...", "pos": "..."}]
        CSV format expected: word,phonetic,pos,definitions,examples
        """
        count = 0
        if format == 'json':
            data = json.loads(content)
            for item in data:
                entry = DictionaryEntry(
                    word=item.get('word'),
                    phonetic=item.get('phonetic'),
                    pos=item.get('pos'),
                    definitions=item.get('definitions', []),
                    examples=item.get('examples', []),
                    source=source
                )
                db.add(entry)
                count += 1
        elif format == 'csv':
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                entry = DictionaryEntry(
                    word=row.get('word'),
                    phonetic=row.get('phonetic'),
                    pos=row.get('pos'),
                    definitions=row.get('definitions', '').split(';'),
                    examples=row.get('examples', '').split(';'),
                    source=source
                )
                db.add(entry)
                count += 1

        await db.commit()
        return count

    @staticmethod
    async def lookup(db: AsyncSession, word: str) -> Optional[DictionaryEntry]:
        """Search for a word in the dictionary"""
        stmt = select(DictionaryEntry).where(DictionaryEntry.word == word.lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def add_to_wordbook(
        db: AsyncSession,
        user_id: UUID,
        word: str,
        definition: str,
        phonetic: Optional[str] = None,
        context_sentence: Optional[str] = None,
        task_id: Optional[UUID] = None,
        importance: int = 3,
        part_of_speech: Optional[str] = None,
        source_translation_id: Optional[str] = None
    ) -> WordBook:
        """
        Add a word to the user's wordbook

        Args:
            db: Database session
            user_id: User ID
            word: Word to add
            definition: Word definition
            phonetic: Phonetic transcription
            context_sentence: Source context sentence
            task_id: Source task ID
            importance: 1-5 star importance rating
            part_of_speech: Part of speech
            source_translation_id: Source translation ID
        """
        # Check if already exists
        stmt = select(WordBook).where(
            and_(WordBook.user_id == user_id, WordBook.word == word.lower())
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing entry
            existing.definition = definition
            existing.phonetic = phonetic or existing.phonetic
            existing.importance = importance
            existing.next_review_at = datetime.utcnow()
            if context_sentence:
                existing.context_sentence = context_sentence
            if part_of_speech:
                existing.part_of_speech = part_of_speech
            if source_translation_id:
                existing.source_translation_id = source_translation_id
            return existing

        word_book = WordBook(
            user_id=user_id,
            word=word.lower(),
            phonetic=phonetic,
            definition=definition,
            context_sentence=context_sentence,
            source_task_id=task_id,
            importance=importance,
            part_of_speech=part_of_speech,
            source_translation_id=source_translation_id,
            next_review_at=datetime.utcnow()
        )
        db.add(word_book)
        await db.commit()
        await db.refresh(word_book)
        return word_book

    @staticmethod
    async def get_review_list(db: AsyncSession, user_id: UUID) -> List[WordBook]:
        """Get words due for review"""
        stmt = select(WordBook).where(
            and_(
                WordBook.user_id == user_id,
                WordBook.next_review_at <= datetime.utcnow()
            )
        ).order_by(WordBook.next_review_at)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_today_creation_count(db: AsyncSession, user_id: UUID) -> int:
        """Get number of words added today (UTC)"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        stmt = select(func.count()).select_from(WordBook).where(
            and_(
                WordBook.user_id == user_id,
                WordBook.created_at >= today_start
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def record_review(
        db: AsyncSession,
        word_id: UUID,
        remembered: bool
    ) -> Optional[WordBook]:
        """
        Record review result and schedule next review (使用统一算法)

        Args:
            db: Database session
            word_id: Word book entry ID
            remembered: Whether the user remembered the word

        Returns:
            Updated word book entry or None if not found
        """
        word_book = await db.get(WordBook, word_id)
        if not word_book:
            return None

        word_book.review_count += 1
        word_book.last_review_at = datetime.utcnow()

        if remembered:
            word_book.correct_review_count += 1
            word_book.consecutive_correct += 1
        else:
            word_book.consecutive_correct = 0  # 重置连续计数

        # 使用统一算法计算下次复习时间
        word_book.next_review_at = VocabularyService._calculate_next_review(
            importance=word_book.importance,
            consecutive_correct=word_book.consecutive_correct,
            remembered=remembered
        )

        await db.commit()
        await db.refresh(word_book)
        return word_book

    @staticmethod
    async def update_importance(
        db: AsyncSession,
        word_id: UUID,
        importance: int
    ) -> Optional[WordBook]:
        """
        Update word importance rating

        Args:
            db: Database session
            word_id: Word book entry ID
            importance: New importance rating (1-5)

        Returns:
            Updated word book entry or None if not found
        """
        if not VocabularyService.MIN_IMPORTANCE <= importance <= VocabularyService.MAX_IMPORTANCE:
            raise ValueError(f"Importance must be between {VocabularyService.MIN_IMPORTANCE} and {VocabularyService.MAX_IMPORTANCE}")

        word_book = await db.get(WordBook, word_id)
        if not word_book:
            return None

        word_book.importance = importance
        # Recalculate next review time with new importance
        word_book.next_review_at = VocabularyService._calculate_next_review(
            importance=word_book.importance,
            consecutive_correct=word_book.consecutive_correct,
            remembered=True  # Assume remembered when manually updating
        )

        await db.commit()
        await db.refresh(word_book)
        return word_book

    @staticmethod
    async def get_statistics(
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get vocabulary statistics for a user

        Returns:
            Dictionary with statistics:
            - total_words: Total number of words in wordbook
            - due_for_review: Number of words due for review
            - accuracy_rate: Overall accuracy rate (correct / total reviews)
            - by_importance: Breakdown by importance level
        """
        # Total words
        total_stmt = select(func.count()).select_from(WordBook).where(
            WordBook.user_id == user_id
        )
        total_result = await db.execute(total_stmt)
        total_words = total_result.scalar() or 0

        # Due for review
        due_stmt = select(func.count()).select_from(WordBook).where(
            and_(
                WordBook.user_id == user_id,
                WordBook.next_review_at <= datetime.utcnow()
            )
        )
        due_result = await db.execute(due_stmt)
        due_for_review = due_result.scalar() or 0

        # Overall accuracy
        accuracy_stmt = select(
            func.coalesce(
                func.sum(WordBook.correct_review_count).cast(Float) /
                func.nullif(func.sum(WordBook.review_count), 0),
                0.0
            )
        ).where(WordBook.user_id == user_id)
        accuracy_result = await db.execute(accuracy_stmt)
        accuracy_rate = accuracy_result.scalar() or 0.0

        # Breakdown by importance
        by_importance = {}
        for i in range(VocabularyService.MIN_IMPORTANCE, VocabularyService.MAX_IMPORTANCE + 1):
            imp_stmt = select(func.count()).select_from(WordBook).where(
                and_(
                    WordBook.user_id == user_id,
                    WordBook.importance == i
                )
            )
            imp_result = await db.execute(imp_stmt)
            by_importance[str(i)] = imp_result.scalar() or 0

        return {
            "total_words": total_words,
            "due_for_review": due_for_review,
            "accuracy_rate": round(accuracy_rate, 4),
            "by_importance": by_importance,
        }

    # ================= LLM Helpers =================

    @staticmethod
    async def get_word_associations(word: str) -> List[str]:
        """Get related words/synonyms/antonyms via LLM"""
        prompt = f"Provide 5-8 related words (synonyms, antonyms, or related concepts) for the word '{word}'. Format as a simple comma-separated list."
        response = await llm_service.chat([{"role": "user", "content": prompt}])
        return [w.strip() for w in response.split(',')]

    @staticmethod
    async def generate_example_sentence(word: str, context: Optional[str] = None) -> str:
        """Generate a natural example sentence for the word"""
        prompt = f"Create a natural, helpful example sentence for the word '{word}'."
        if context:
            prompt += f" The context is: {context}"
        return await llm_service.chat([{"role": "user", "content": prompt}])

    @staticmethod
    async def polish_definition(word: str, original_def: str) -> str:
        """Polish and simplify a word definition for a student"""
        prompt = f"Polish and simplify this definition for the word '{word}' so it's easier for a college student to understand: '{original_def}'. Keep it concise."
        return await llm_service.chat([{"role": "user", "content": prompt}])


vocabulary_service = VocabularyService()
