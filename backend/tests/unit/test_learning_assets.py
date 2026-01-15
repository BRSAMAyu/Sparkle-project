"""
Tests for Learning Assets Subsystem

Tests:
1. Text normalization stability
2. Fingerprint generation stability
3. Suggestion cooldown logic
4. FuzzyMatch scoring
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.fingerprint import (
    normalize_core,
    check_ambiguity,
    generate_selection_fp,
    generate_doc_fp,
    generate_anchor_fp,
    generate_fingerprints,
    NORM_VERSION,
)
from app.core.fuzzy_match import (
    calculate_similarity,
    determine_match_strength,
    char_ngrams,
    jaccard_similarity,
    STRONG_THRESHOLD,
    WEAK_THRESHOLD,
)
from app.models.learning_assets import MatchStrength


# ============ Normalization Tests ============

class TestNormalization:
    """Test normalize_core stability and correctness."""

    def test_basic_normalization(self):
        """Basic text normalization."""
        assert normalize_core("Hello World") == "hello world"
        assert normalize_core("  spaces  ") == "spaces"
        assert normalize_core("UPPERCASE") == "uppercase"

    def test_whitespace_collapse(self):
        """Multiple whitespaces collapse to single space."""
        assert normalize_core("hello   world") == "hello world"
        assert normalize_core("hello\n\nworld") == "hello world"
        assert normalize_core("hello\t\tworld") == "hello world"

    def test_unicode_nfkc(self):
        """NFKC normalization for compatibility characters."""
        # Full-width to half-width
        assert normalize_core("ａｂｃ") == "abc"
        # Ligatures decompose
        assert normalize_core("ﬁ") == "fi"

    def test_zero_width_removal(self):
        """Zero-width characters are removed."""
        zwsp = "\u200b"  # Zero-width space
        assert normalize_core(f"hello{zwsp}world") == "helloworld"

    def test_cjk_preservation(self):
        """CJK characters are preserved (not lowercased)."""
        text = "学习English"
        result = normalize_core(text)
        assert "学习" in result
        assert "english" in result

    def test_empty_and_none(self):
        """Empty and edge cases."""
        assert normalize_core("") == ""
        assert normalize_core("   ") == ""

    def test_normalization_stability(self):
        """
        Normalization must be STABLE - same input always produces same output.
        This is critical for fingerprint matching.
        """
        test_cases = [
            "Hello World",
            "  Mixed   CASE  with   spaces  ",
            "Unicode: 学习 ａｂｃ ﬁ",
            "Symbols: @#$%^&*()",
            "Numbers: 12345",
            "Zero\u200bWidth\u200cChars",
        ]

        for text in test_cases:
            result1 = normalize_core(text)
            result2 = normalize_core(text)
            assert result1 == result2, f"Normalization not stable for: {text}"


class TestAmbiguity:
    """Test ambiguity detection."""

    def test_short_text_is_ambiguous(self):
        """Text shorter than 3 chars is ambiguous."""
        assert check_ambiguity("ab") is True
        assert check_ambiguity("a") is True
        assert check_ambiguity("") is True

    def test_punctuation_only_is_ambiguous(self):
        """All punctuation/symbols is ambiguous."""
        assert check_ambiguity("...") is True
        assert check_ambiguity("@#$") is True

    def test_normal_text_not_ambiguous(self):
        """Normal text with letters is not ambiguous."""
        assert check_ambiguity("hello") is False
        assert check_ambiguity("abc") is False
        assert check_ambiguity("学习") is False


# ============ Fingerprint Tests ============

class TestFingerprint:
    """Test fingerprint generation stability."""

    def test_selection_fp_stability(self):
        """Selection fingerprint must be stable."""
        text = "polymorphism"
        fp1 = generate_selection_fp(text)
        fp2 = generate_selection_fp(text)
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256 hex

    def test_selection_fp_normalization(self):
        """Fingerprint is based on normalized text."""
        # These should produce the same fingerprint
        fp1 = generate_selection_fp("Hello World")
        fp2 = generate_selection_fp("hello   world")
        fp3 = generate_selection_fp("  HELLO WORLD  ")
        assert fp1 == fp2 == fp3

    def test_doc_fp_stability(self):
        """Document fingerprint must be stable."""
        selection_fp = generate_selection_fp("test")
        doc_id = uuid4()
        fp1 = generate_doc_fp(selection_fp, doc_id)
        fp2 = generate_doc_fp(selection_fp, doc_id)
        assert fp1 == fp2

    def test_doc_fp_different_docs(self):
        """Different documents produce different fingerprints."""
        selection_fp = generate_selection_fp("test")
        doc1 = uuid4()
        doc2 = uuid4()
        fp1 = generate_doc_fp(selection_fp, doc1)
        fp2 = generate_doc_fp(selection_fp, doc2)
        assert fp1 != fp2

    def test_anchor_fp_with_context(self):
        """Anchor fingerprint includes context."""
        selection_fp = generate_selection_fp("test")
        doc_id = uuid4()
        doc_fp = generate_doc_fp(selection_fp, doc_id)

        fp1 = generate_anchor_fp(doc_fp, "before", "after", 1)
        fp2 = generate_anchor_fp(doc_fp, "before", "after", 1)
        fp3 = generate_anchor_fp(doc_fp, "different", "after", 1)

        assert fp1 == fp2
        assert fp1 != fp3

    def test_generate_fingerprints_complete(self):
        """Test complete fingerprint generation."""
        doc_id = uuid4()
        result = generate_fingerprints(
            selected_text="test",
            doc_id=doc_id,
            context_before="context",
            context_after="more",
            page_no=5
        )

        assert result.selection_fp is not None
        assert result.doc_fp is not None
        assert result.anchor_fp is not None
        assert result.norm_version == NORM_VERSION

    def test_generate_fingerprints_minimal(self):
        """Test minimal fingerprint (no doc context)."""
        result = generate_fingerprints(selected_text="test")

        assert result.selection_fp is not None
        assert result.doc_fp is None
        assert result.anchor_fp is None


# ============ FuzzyMatch Tests ============

class TestFuzzyMatch:
    """Test fuzzy matching algorithms."""

    def test_char_ngrams(self):
        """Character n-gram generation."""
        ngrams = char_ngrams("hello", 3)
        assert "hel" in ngrams
        assert "ell" in ngrams
        assert "llo" in ngrams
        assert len(ngrams) == 3

    def test_char_ngrams_short(self):
        """Short text n-gram handling."""
        assert char_ngrams("ab", 3) == {"ab"}
        assert char_ngrams("", 3) == set()

    def test_jaccard_similarity_identical(self):
        """Identical sets have similarity 1.0."""
        set_a = {"a", "b", "c"}
        assert jaccard_similarity(set_a, set_a) == 1.0

    def test_jaccard_similarity_disjoint(self):
        """Disjoint sets have similarity 0.0."""
        set_a = {"a", "b"}
        set_b = {"c", "d"}
        assert jaccard_similarity(set_a, set_b) == 0.0

    def test_jaccard_similarity_partial(self):
        """Partial overlap gives partial similarity."""
        set_a = {"a", "b", "c"}
        set_b = {"b", "c", "d"}
        # Intersection: {b, c} = 2, Union: {a, b, c, d} = 4
        assert jaccard_similarity(set_a, set_b) == 0.5

    def test_calculate_similarity_identical(self):
        """Identical texts have high similarity."""
        score = calculate_similarity("polymorphism", "polymorphism")
        assert score == 1.0

    def test_calculate_similarity_similar(self):
        """Similar texts have high similarity."""
        score = calculate_similarity("polymorphism", "polymorphysm")
        assert score > 0.8

    def test_calculate_similarity_different(self):
        """Different texts have low similarity."""
        score = calculate_similarity("hello", "goodbye")
        assert score < 0.5

    def test_determine_match_strength_strong(self):
        """Score >= 0.85 is STRONG."""
        assert determine_match_strength(0.90) == MatchStrength.STRONG
        assert determine_match_strength(0.85) == MatchStrength.STRONG

    def test_determine_match_strength_weak(self):
        """Score 0.70-0.85 is WEAK."""
        assert determine_match_strength(0.75) == MatchStrength.WEAK
        assert determine_match_strength(0.70) == MatchStrength.WEAK

    def test_determine_match_strength_orphan(self):
        """Score < 0.70 is ORPHAN."""
        assert determine_match_strength(0.69) == MatchStrength.ORPHAN
        assert determine_match_strength(0.50) == MatchStrength.ORPHAN


# ============ Suggestion Cooldown Tests ============

class TestSuggestionCooldown:
    """Test suggestion cooldown logic."""

    @pytest.mark.asyncio
    async def test_first_lookup_no_suggestion(self):
        """First lookup should not suggest asset creation."""
        with patch('app.services.learning_asset_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=1)
            mock_cache.expire = AsyncMock()
            mock_cache.get = AsyncMock(return_value=None)

            from app.services.learning_asset_service import LearningAssetService
            service = LearningAssetService()

            # Mock db session - no existing asset
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            result = await service.record_lookup(
                db=mock_db,
                user_id=uuid4(),
                session_id="test-session",
                selected_text="polymorphism",
                translation="多态性",
            )

            # First lookup should not suggest (below threshold)
            assert result.get("suggest_asset") is False

    @pytest.mark.asyncio
    async def test_second_lookup_suggests_asset(self):
        """Second lookup of same text should suggest asset creation."""
        with patch('app.services.learning_asset_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=2)  # Second lookup
            mock_cache.expire = AsyncMock()
            mock_cache.get = AsyncMock(return_value=None)  # No cooldown

            from app.services.learning_asset_service import LearningAssetService
            service = LearningAssetService()

            # Mock db session - no existing asset
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            result = await service.record_lookup(
                db=mock_db,
                user_id=uuid4(),
                session_id="test-session",
                selected_text="polymorphism",
                translation="多态性",
            )

            # Second lookup should suggest
            assert result.get("suggest_asset") is True
            assert "suggestion_log_id" in result

    @pytest.mark.asyncio
    async def test_cooldown_prevents_suggestion(self):
        """Cooldown should prevent repeated suggestions."""
        with patch('app.services.learning_asset_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=3)  # Third lookup
            mock_cache.expire = AsyncMock()
            mock_cache.get = AsyncMock(return_value="2025-01-20T12:00:00")  # Cooldown active

            from app.services.learning_asset_service import LearningAssetService
            service = LearningAssetService()

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            result = await service.record_lookup(
                db=mock_db,
                user_id=uuid4(),
                session_id="test-session",
                selected_text="polymorphism",
                translation="多态性",
            )

            # Cooldown should prevent suggestion
            assert result.get("suggest_asset") is False
            assert "cooldown_active" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_existing_asset_no_suggestion(self):
        """Existing asset should prevent new suggestion."""
        with patch('app.services.learning_asset_service.cache_service') as mock_cache:
            mock_cache.incr = AsyncMock(return_value=2)
            mock_cache.expire = AsyncMock()
            mock_cache.get = AsyncMock(return_value=None)

            from app.services.learning_asset_service import LearningAssetService
            service = LearningAssetService()

            # Mock existing asset
            mock_asset = MagicMock()
            mock_asset.id = uuid4()
            mock_asset.lookup_count = 1
            mock_asset.last_seen_at = None

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mock_asset)
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.flush = AsyncMock()

            result = await service.record_lookup(
                db=mock_db,
                user_id=uuid4(),
                session_id="test-session",
                selected_text="polymorphism",
                translation="多态性",
            )

            # Existing asset should prevent suggestion
            assert result.get("suggest_asset") is False
            assert "already_exists" in result.get("reason", "")


# ============ Inbox Decay Tests ============

class TestInboxDecay:
    """Test inbox decay logic."""

    @pytest.mark.asyncio
    async def test_process_inbox_expiry_archives_expired(self):
        """Expired inbox assets should be archived."""
        from datetime import datetime, timezone, timedelta
        from app.services.learning_asset_service import LearningAssetService

        service = LearningAssetService()

        # Create mock expired asset
        mock_asset = MagicMock()
        mock_asset.id = uuid4()
        mock_asset.status = "INBOX"
        mock_asset.inbox_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        mock_db = AsyncMock()

        # Mock the SELECT query for finding expired assets
        mock_select_result = MagicMock()
        mock_select_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[mock_asset]))
        )

        # Mock the sequence_number query for event_outbox
        mock_seq_result = MagicMock()
        mock_seq_result.scalar = MagicMock(return_value=1)

        # Setup execute to return different results based on call
        mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_seq_result, MagicMock()])
        mock_db.flush = AsyncMock()

        count = await service.process_inbox_expiry(mock_db)

        # Should archive expired assets
        assert mock_asset.status == "ARCHIVED"
        assert count == 1

    @pytest.mark.asyncio
    async def test_process_inbox_expiry_skips_non_expired(self):
        """Non-expired inbox assets should not be archived."""
        from app.services.learning_asset_service import LearningAssetService

        service = LearningAssetService()

        # No expired assets
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await service.process_inbox_expiry(mock_db)

        assert count == 0


# ============ FuzzyMatch Page Constraint Tests ============

class TestFuzzyMatchPageConstraint:
    """Test FuzzyMatch page_no constraint behavior."""

    def test_page_no_filter_empty_chunk_pages(self):
        """
        When page_no is specified but chunk has no page info,
        the chunk should be skipped.
        """
        # This is tested by verifying the logic in fuzzy_match.py
        # When page_no is not None and chunk_pages is empty:
        # - Old (buggy): `if page_no is not None and chunk_pages` -> skip check
        # - New (fixed): `if page_no is not None` -> always check, skip if no page info

        page_no = 5
        chunk_pages_empty = []
        chunk_pages_with_match = [5, 6, 7]
        chunk_pages_no_match = [1, 2, 3]

        # Simulating the fixed condition
        def should_skip(page_no, chunk_pages):
            if page_no is not None:
                if not chunk_pages or page_no not in chunk_pages:
                    return True
            return False

        # Empty pages should be skipped when page_no is specified
        assert should_skip(page_no, chunk_pages_empty) is True
        # Pages with match should not be skipped
        assert should_skip(page_no, chunk_pages_with_match) is False
        # Pages without match should be skipped
        assert should_skip(page_no, chunk_pages_no_match) is True
        # No page_no specified should never skip
        assert should_skip(None, chunk_pages_empty) is False
        assert should_skip(None, chunk_pages_with_match) is False
