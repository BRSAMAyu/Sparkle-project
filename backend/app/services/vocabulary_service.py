import json
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models.vocabulary import WordBook, DictionaryEntry
from app.services.llm_service import llm_service

class VocabularyService:
    # 艾宾浩斯复习间隔 (天)
    REVIEW_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 60] # 阶段 0 到 7

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
        task_id: Optional[UUID] = None
    ) -> WordBook:
        """Add a word to the user's wordbook"""
        # Check if already exists
        stmt = select(WordBook).where(
            and_(WordBook.user_id == user_id, WordBook.word == word.lower())
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.definition = definition
            existing.next_review_at = datetime.utcnow() # Reset review if re-added?
            return existing

        word_book = WordBook(
            user_id=user_id,
            word=word.lower(),
            phonetic=phonetic,
            definition=definition,
            context_sentence=context_sentence,
            source_task_id=task_id,
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
    async def record_review(db: AsyncSession, word_id: UUID, success: bool):
        """Record review result and schedule next review"""
        word_book = await db.get(WordBook, word_id)
        if not word_book:
            return

        if success:
            word_book.mastery_level = min(len(VocabularyService.REVIEW_INTERVALS) - 1, word_book.mastery_level + 1)
        else:
            word_book.mastery_level = max(0, word_book.mastery_level - 1)
            
        interval_days = VocabularyService.REVIEW_INTERVALS[word_book.mastery_level]
        word_book.next_review_at = datetime.utcnow() + timedelta(days=interval_days)
        word_book.last_review_at = datetime.utcnow()
        word_book.review_count += 1
        
        await db.commit()

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
