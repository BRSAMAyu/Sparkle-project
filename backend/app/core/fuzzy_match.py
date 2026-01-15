"""
FuzzyMatch MVP Service (模糊匹配服务)

Matches selected text against document chunks for provenance tracing.
Uses simple text similarity without external dependencies.

Match strength levels:
- STRONG (>= 0.85): High confidence match
- WEAK (0.70 - 0.85): Possible match, may need verification
- ORPHAN (< 0.70): No reliable match found
"""
import difflib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunks import DocumentChunk
from app.models.learning_assets import MatchStrength
from app.core.fingerprint import normalize_core

# Match thresholds
STRONG_THRESHOLD = 0.85
WEAK_THRESHOLD = 0.70

# Top-K candidates to consider
DEFAULT_TOP_K = 10


@dataclass
class MatchCandidate:
    """A potential match candidate"""
    chunk_id: UUID
    file_id: UUID
    page_numbers: List[int]
    score: float
    match_strength: MatchStrength
    matched_text: str  # Portion of chunk that matched


@dataclass
class ProvenanceMatch:
    """Result of provenance matching"""
    best_match: Optional[MatchCandidate]
    all_candidates: List[MatchCandidate]
    search_params: Dict[str, Any] = field(default_factory=dict)


def char_ngrams(text: str, n: int = 3) -> set:
    """
    Generate character n-grams from text.

    Args:
        text: Input text
        n: N-gram size (default: 3 for trigrams)

    Returns:
        Set of n-gram strings
    """
    if len(text) < n:
        return {text} if text else set()

    return {text[i:i+n] for i in range(len(text) - n + 1)}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    Calculate Jaccard similarity between two sets.

    Args:
        set_a: First set
        set_b: Second set

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0


def calculate_similarity(text_a: str, text_b: str) -> float:
    """
    Calculate composite similarity score between two texts.

    Score = 0.6 * char_3gram_jaccard + 0.4 * difflib_ratio

    Args:
        text_a: First text (typically selection)
        text_b: Second text (typically chunk excerpt)

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize both texts
    norm_a = normalize_core(text_a)
    norm_b = normalize_core(text_b)

    if not norm_a or not norm_b:
        return 0.0

    # Calculate character trigram Jaccard similarity
    ngrams_a = char_ngrams(norm_a, 3)
    ngrams_b = char_ngrams(norm_b, 3)
    jaccard = jaccard_similarity(ngrams_a, ngrams_b)

    # Calculate difflib SequenceMatcher ratio
    matcher = difflib.SequenceMatcher(None, norm_a, norm_b)
    difflib_ratio = matcher.ratio()

    # Composite score
    return 0.6 * jaccard + 0.4 * difflib_ratio


def determine_match_strength(score: float) -> MatchStrength:
    """
    Determine match strength from similarity score.

    Args:
        score: Similarity score

    Returns:
        MatchStrength enum value
    """
    if score >= STRONG_THRESHOLD:
        return MatchStrength.STRONG
    elif score >= WEAK_THRESHOLD:
        return MatchStrength.WEAK
    else:
        return MatchStrength.ORPHAN


def find_best_substring_match(selection: str, chunk_content: str) -> tuple[float, str]:
    """
    Find the best matching substring within a chunk.

    Uses a sliding window approach to find the portion of the chunk
    that best matches the selection.

    Args:
        selection: Selected text to match
        chunk_content: Full chunk content

    Returns:
        Tuple of (best_score, matched_substring)
    """
    norm_selection = normalize_core(selection)
    norm_chunk = normalize_core(chunk_content)

    if not norm_selection or not norm_chunk:
        return 0.0, ""

    # If selection is longer than chunk, compare directly
    if len(norm_selection) >= len(norm_chunk):
        score = calculate_similarity(norm_selection, norm_chunk)
        return score, chunk_content

    # Sliding window with size roughly equal to selection length
    window_size = len(norm_selection)
    best_score = 0.0
    best_match = ""

    # Use larger steps for efficiency
    step = max(1, window_size // 4)

    for i in range(0, len(norm_chunk) - window_size + 1, step):
        window = norm_chunk[i:i + window_size]
        score = calculate_similarity(norm_selection, window)

        if score > best_score:
            best_score = score
            # Extract corresponding original text (approximate)
            ratio = len(chunk_content) / len(norm_chunk)
            start_orig = int(i * ratio)
            end_orig = int((i + window_size) * ratio)
            best_match = chunk_content[start_orig:end_orig]

    # Also try matching against the full chunk
    full_score = calculate_similarity(norm_selection, norm_chunk)
    if full_score > best_score:
        best_score = full_score
        best_match = chunk_content

    return best_score, best_match


async def find_provenance(
    db: AsyncSession,
    selected_text: str,
    file_id: UUID,
    page_no: Optional[int] = None,
    user_id: Optional[UUID] = None,
    top_k: int = DEFAULT_TOP_K
) -> ProvenanceMatch:
    """
    Find provenance for selected text in document chunks.

    Strategy:
    1. If page_no provided: Query chunks with that page number
    2. Otherwise: Query all chunks for the file (limited to top_k)

    Args:
        db: Database session
        selected_text: Text to find provenance for
        file_id: Source file UUID
        page_no: Page number hint (optional)
        user_id: User UUID for filtering (optional)
        top_k: Maximum candidates to consider

    Returns:
        ProvenanceMatch with best match and all candidates
    """
    # Build query
    query = select(DocumentChunk).where(
        and_(
            DocumentChunk.file_id == file_id,
            DocumentChunk.deleted_at.is_(None)
        )
    )

    if user_id:
        query = query.where(DocumentChunk.user_id == user_id)

    # Limit results
    query = query.limit(top_k * 2)  # Get more candidates for filtering

    result = await db.execute(query)
    chunks = result.scalars().all()

    candidates: List[MatchCandidate] = []
    search_params = {
        "file_id": str(file_id),
        "page_no": page_no,
        "user_id": str(user_id) if user_id else None,
        "top_k": top_k,
        "chunks_searched": len(chunks)
    }

    for chunk in chunks:
        chunk_pages = chunk.page_numbers or []

        # Skip if page_no specified but chunk doesn't contain that page
        # (or chunk has no page info when page_no is specified)
        if page_no is not None:
            if not chunk_pages or page_no not in chunk_pages:
                continue

        # Calculate similarity
        score, matched_text = find_best_substring_match(selected_text, chunk.content)
        strength = determine_match_strength(score)

        # Only include if score >= WEAK threshold or we have few candidates
        if score >= WEAK_THRESHOLD or len(candidates) < 3:
            candidates.append(MatchCandidate(
                chunk_id=chunk.id,
                file_id=chunk.file_id,
                page_numbers=chunk_pages,
                score=score,
                match_strength=strength,
                matched_text=matched_text[:500]  # Truncate for storage
            ))

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Take top_k
    candidates = candidates[:top_k]

    # Determine best match
    best_match = None
    if candidates and candidates[0].score >= WEAK_THRESHOLD:
        best_match = candidates[0]

    return ProvenanceMatch(
        best_match=best_match,
        all_candidates=candidates,
        search_params=search_params
    )


def build_provenance_json(match: ProvenanceMatch) -> Dict[str, Any]:
    """
    Build provenance JSON for storage in learning_asset.

    Args:
        match: ProvenanceMatch result

    Returns:
        Dict suitable for provenance_json column
    """
    if not match.best_match:
        return {
            "match_strength": MatchStrength.ORPHAN.value,
            "reason": "no_match_found",
            "search_params": match.search_params,
            "candidates_count": len(match.all_candidates)
        }

    best = match.best_match
    return {
        "match_strength": best.match_strength.value,
        "chunk_id": str(best.chunk_id),
        "file_id": str(best.file_id),
        "page_numbers": best.page_numbers,
        "score": round(best.score, 4),
        "matched_text_preview": best.matched_text[:200] if best.matched_text else None,
        "search_params": match.search_params,
        "candidates_count": len(match.all_candidates),
        "recalculated": False  # Will be True after provenance update
    }
