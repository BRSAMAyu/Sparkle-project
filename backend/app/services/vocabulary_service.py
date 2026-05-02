from __future__ import annotations

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
import csv
import io
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Float, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vocabulary import DictionaryEntry, WordBook


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class VocabularyService:
    """生词本与词典服务"""

    MIN_IMPORTANCE = 1
    MAX_IMPORTANCE = 5
    DEFAULT_REVIEW_BATCH_SIZE = 50

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
            return _utcnow() + timedelta(days=1)

        # 重要度 5 -> 基础 1 天（关键词汇）
        # 重要度 1 -> 基础 5 天（普通词汇）
        base_interval = max(1, min(5, 6 - importance))

        # 指数退避: 2^(streak-1)
        multiplier = 2 ** max(0, consecutive_correct - 1)
        days = base_interval * multiplier

        # 上限 180 天
        days = min(days, 180)

        return _utcnow() + timedelta(days=int(days))

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
    async def lookup(db: AsyncSession, word: str) -> DictionaryEntry | None:
        """Search for a word in the dictionary"""
        stmt = select(DictionaryEntry).where(DictionaryEntry.word == word.lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _extract_json_object(content: str) -> dict[str, Any] | None:
        """Extract the first JSON object from a model response."""
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _normalize_definitions(value: Any) -> list[str]:
        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _extract_definition_lines(content: str) -> list[str]:
        definitions: list[str] = []
        for raw_line in (content or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^[-*•\d.\)\s]+", "", line).strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith(("word:", "phonetic:", "pos:", "examples:", "example:")):
                continue
            definitions.append(line)
            if len(definitions) >= 3:
                break
        return definitions

    @staticmethod
    async def synthesize_lookup(word: str) -> dict[str, Any]:
        """
        Generate a lightweight dictionary result via LLM fallback.

        This keeps the lookup tool usable even when the local dictionary or MDX
        assets are not populated in a fresh environment.
        """
        from app.services.llm_fallback_utils import vocabulary_llm

        prompt = (
            "You are a compact English dictionary service. "
            "Return strict JSON with keys: word, phonetic, pos, definitions, examples. "
            "definitions and examples must be arrays of short strings. "
            "If unsure, keep phonetic or pos null instead of inventing details.\n"
            f"word: {word}"
        )
        data = await vocabulary_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON. Do not add markdown, explanation, or extra keys."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            fallback={"word": word, "definitions": [], "examples": []},
            temperature=0.2,
        )
        if data is None:
            data = {}

        definitions = VocabularyService._normalize_definitions(data.get("definitions"))
        examples = data.get("examples")

        if not definitions:
            raw_text = await vocabulary_llm.call(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an English dictionary. "
                            "Return 1 to 3 short English definitions as plain text lines only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Provide short dictionary definitions for the word: {word}",
                    },
                ],
                fallback="",
                temperature=0.2,
            )
            definitions = VocabularyService._extract_definition_lines(raw_text)

        normalized = {
            "word": str(data.get("word") or word).strip().lower(),
            "phonetic": data.get("phonetic") if isinstance(data.get("phonetic"), str) else None,
            "pos": data.get("pos") if isinstance(data.get("pos"), str) else None,
            "definitions": definitions,
            "examples": [str(item).strip() for item in examples] if isinstance(examples, list) else [],
            "source": "llm_fallback",
        }

        if not normalized["definitions"]:
            normalized["definitions"] = [f"{word}: definition unavailable"]

        return normalized

    @staticmethod
    async def add_to_wordbook(
        db: AsyncSession,
        user_id: UUID,
        word: str,
        definition: str,
        phonetic: str | None = None,
        context_sentence: str | None = None,
        task_id: UUID | None = None,
        importance: int = 3,
        part_of_speech: str | None = None,
        source_translation_id: str | None = None
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
            existing.next_review_at = _utcnow()
            if context_sentence:
                existing.context_sentence = context_sentence
            if part_of_speech:
                existing.part_of_speech = part_of_speech
            if source_translation_id:
                existing.source_translation_id = source_translation_id
            await db.commit()
            await db.refresh(existing)
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
            next_review_at=_utcnow()
        )
        db.add(word_book)
        await db.commit()
        await db.refresh(word_book)
        return word_book

    @staticmethod
    def build_learning_loop_summary(
        word_book: WordBook,
        *,
        graph_node_id: UUID | str | None = None,
        learning_asset_id: UUID | str | None = None,
        graph_status: str | None = None,
        asset_status: str | None = None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        """Expose where a saved word goes next in the learning OS."""
        tag_links = VocabularyService._extract_learning_links(word_book.tags)
        graph_node_id = graph_node_id or tag_links.get("knowledge_node_id")
        learning_asset_id = learning_asset_id or tag_links.get("learning_asset_id")

        return {
            "vocabulary_card": {
                "word_id": str(word_book.id),
                "word": word_book.word,
                "source_translation_id": word_book.source_translation_id,
            },
            "review": {
                "scheduled": True,
                "next_review_at": word_book.next_review_at.isoformat() if word_book.next_review_at else None,
                "importance": word_book.importance,
                "review_count": word_book.review_count,
            },
            "knowledge_card": {
                "created": bool(graph_node_id),
                "node_id": str(graph_node_id) if graph_node_id else None,
                "status": graph_status or tag_links.get("knowledge_status"),
            },
            "learning_asset": {
                "created": bool(learning_asset_id),
                "asset_id": str(learning_asset_id) if learning_asset_id else None,
                "status": asset_status or tag_links.get("learning_asset_status"),
            },
            "task_recommendation_hint": {
                "eligible": bool(graph_node_id),
                "reason": (
                    "translation_vocabulary_review_due"
                    if graph_node_id
                    else "wordbook_spaced_review_due"
                ),
            },
            "warnings": warnings or [],
        }

    @staticmethod
    def _extract_learning_links(tags: Any) -> dict[str, Any]:
        if not isinstance(tags, list):
            return {}
        for tag in tags:
            if isinstance(tag, dict) and tag.get("type") == "learning_loop":
                return tag
        return {}

    @staticmethod
    async def attach_learning_links(
        db: AsyncSession,
        word_book: WordBook,
        *,
        graph_node_id: UUID | str | None = None,
        graph_status: str | None = None,
        learning_asset_id: UUID | str | None = None,
        learning_asset_status: str | None = None,
    ) -> WordBook:
        """Store graph/asset links on the wordbook row without a schema migration."""
        tags = word_book.tags if isinstance(word_book.tags, list) else []
        retained_tags = [
            tag
            for tag in tags
            if not (isinstance(tag, dict) and tag.get("type") == "learning_loop")
        ]
        retained_tags.append(
            {
                "type": "learning_loop",
                "knowledge_node_id": str(graph_node_id) if graph_node_id else None,
                "knowledge_status": graph_status,
                "learning_asset_id": str(learning_asset_id) if learning_asset_id else None,
                "learning_asset_status": learning_asset_status,
                "linked_at": _utcnow().isoformat(),
            }
        )
        word_book.tags = retained_tags
        await db.commit()
        await db.refresh(word_book)
        return word_book

    @staticmethod
    async def get_review_list(
        db: AsyncSession,
        user_id: UUID,
        limit: int = DEFAULT_REVIEW_BATCH_SIZE,
    ) -> list[WordBook]:
        """Get words due for review"""
        safe_limit = max(1, limit)
        stmt = select(WordBook).where(
            and_(
                WordBook.user_id == user_id,
                WordBook.next_review_at <= _utcnow()
            )
        ).order_by(WordBook.next_review_at).limit(safe_limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_wordbook(
        db: AsyncSession,
        user_id: UUID,
        search: str | None = None,
    ) -> list[WordBook]:
        """Get the user's full wordbook, optionally filtered by search text."""
        stmt = select(WordBook).where(WordBook.user_id == user_id)

        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                func.lower(WordBook.word).like(term) |
                func.lower(WordBook.definition).like(term)
            )

        stmt = stmt.order_by(WordBook.next_review_at.asc(), WordBook.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_today_creation_count(db: AsyncSession, user_id: UUID) -> int:
        """Get number of words added today (timezone.utc)"""
        today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

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
        remembered: bool,
        user_id: UUID | None = None,
    ) -> WordBook | None:
        """
        Record review result and schedule next review (使用统一算法)

        Args:
            db: Database session
            word_id: Word book entry ID
            remembered: Whether the user remembered the word

        Returns:
            Updated word book entry or None if not found
        """
        if user_id is not None:
            result = await db.execute(
                select(WordBook).where(
                    and_(WordBook.id == word_id, WordBook.user_id == user_id)
                )
            )
            word_book = result.scalar_one_or_none()
        else:
            word_book = await db.get(WordBook, word_id)
        if not word_book:
            return None

        word_book.review_count += 1
        word_book.last_review_at = _utcnow()

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
    async def delete_wordbook_entry(
        db: AsyncSession,
        user_id: UUID,
        word_id: UUID,
    ) -> bool:
        """Delete a wordbook entry owned by the current user."""
        stmt = select(WordBook).where(
            and_(WordBook.id == word_id, WordBook.user_id == user_id)
        )
        result = await db.execute(stmt)
        word_book = result.scalar_one_or_none()
        if not word_book:
            return False

        await db.delete(word_book)
        await db.commit()
        return True

    @staticmethod
    async def update_importance(
        db: AsyncSession,
        word_id: UUID,
        importance: int
    ) -> WordBook | None:
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
    ) -> dict[str, Any]:
        """
        Get vocabulary statistics for a user

        Returns:
            Dictionary with statistics:
            - total_words: Total number of words in wordbook
            - due_for_review: Number of words due for review
            - accuracy_rate: Overall accuracy rate (correct / total reviews)
            - by_importance: Breakdown by importance level
        """
        summary_stmt = select(
            func.count().label("total_words"),
            func.coalesce(
                func.sum(
                    case(
                        (WordBook.next_review_at <= _utcnow(), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("due_for_review"),
            func.coalesce(
                func.sum(WordBook.correct_review_count).cast(Float) /
                func.nullif(func.sum(WordBook.review_count), 0),
                0.0
            )
            .label("accuracy_rate"),
        ).where(WordBook.user_id == user_id)
        summary_result = await db.execute(summary_stmt)
        summary = summary_result.one()

        by_importance = {
            str(i): 0 for i in range(VocabularyService.MIN_IMPORTANCE, VocabularyService.MAX_IMPORTANCE + 1)
        }
        importance_stmt = (
            select(WordBook.importance, func.count())
            .where(WordBook.user_id == user_id)
            .group_by(WordBook.importance)
        )
        importance_result = await db.execute(importance_stmt)
        for importance, count in importance_result.all():
            if importance is None:
                continue
            by_importance[str(int(importance))] = int(count or 0)

        return {
            "total_words": int(summary.total_words or 0),
            "due_for_review": int(summary.due_for_review or 0),
            "accuracy_rate": round(float(summary.accuracy_rate or 0.0), 4),
            "by_importance": by_importance,
        }

    # ================= LLM Helpers =================

    @staticmethod
    async def get_word_associations(word: str) -> list[str]:
        """Get related words/synonyms/antonyms via LLM"""
        from app.services.llm_fallback_utils import vocabulary_llm

        prompt = f"Provide 5-8 related words (synonyms, antonyms, or related concepts) for the word '{word}'. Format as a simple comma-separated list."
        response = await vocabulary_llm.chat(prompt, fallback="")
        if not response:
            return []
        return [w.strip() for w in response.split(',') if w.strip()]

    @staticmethod
    async def generate_example_sentence(word: str, context: str | None = None) -> str:
        """Generate a natural example sentence for the word"""
        from app.services.llm_fallback_utils import vocabulary_llm

        prompt = f"Create a natural, helpful example sentence for the word '{word}'."
        if context:
            prompt += f" The context is: {context}"
        return await vocabulary_llm.chat(
            prompt,
            fallback=f"Example sentence for '{word}' is not available at the moment."
        )

    @staticmethod
    async def polish_definition(word: str, original_def: str) -> str:
        """Polish and simplify a word definition for a student"""
        from app.services.llm_fallback_utils import vocabulary_llm

        prompt = f"Polish and simplify this definition for the word '{word}' so it's easier for a college student to understand: '{original_def}'. Keep it concise."
        return await vocabulary_llm.chat(prompt, fallback=original_def)


vocabulary_service = VocabularyService()
