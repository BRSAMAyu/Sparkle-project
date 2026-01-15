"""
Text Normalization and Fingerprint Module (文本规范化与指纹模块)

Provides stable text normalization and fingerprint generation for:
- Deduplication of learning assets
- Provenance tracing (matching assets to source documents)
- Signal detection (tracking repeated lookups)

Key design principles:
- norm_core is extremely stable (changes require migration)
- Version fields (norm_version, match_profile) enable future evolution
- Fingerprints are SHA-256 hashes for stability and collision resistance
"""
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

# Current normalization version - increment on any change
NORM_VERSION = "v1"

# Current match profile for FuzzyMatch - can be language/doc-type specific
DEFAULT_MATCH_PROFILE = "default_v1"


@dataclass(frozen=True)
class NormalizationResult:
    """Result of text normalization"""
    original: str
    normalized: str
    ambiguity_hint: bool  # True if text is too short or all punctuation
    norm_version: str


@dataclass(frozen=True)
class FingerprintResult:
    """Complete fingerprint set for a text selection"""
    selection_fp: str      # sha256(normalize_core(selected_text))
    doc_fp: Optional[str]  # sha256(selection_fp + doc_id) - None if no doc
    anchor_fp: Optional[str]  # sha256(doc_fp + context + page) - None if no context
    norm_version: str
    match_profile: str


def normalize_core(text: str) -> str:
    """
    Core normalization function - must be EXTREMELY stable.

    Any change to this function requires:
    1. Increment NORM_VERSION
    2. Migration plan for existing fingerprints

    Transformations applied:
    1. NFKC normalization (compatibility decomposition + canonical composition)
    2. Remove zero-width characters
    3. Collapse whitespace (multiple spaces/tabs/newlines → single space)
    4. Strip leading/trailing whitespace
    5. Lowercase for ASCII/Latin characters (preserve CJK case)
    6. Preserve digits and letters

    Args:
        text: Raw input text

    Returns:
        Normalized text string
    """
    if not text:
        return ""

    # Step 1: NFKC normalization (handles ligatures, compatibility chars)
    normalized = unicodedata.normalize("NFKC", text)

    # Step 2: Remove zero-width characters
    zero_width_chars = (
        "\u200b"  # Zero-width space
        "\u200c"  # Zero-width non-joiner
        "\u200d"  # Zero-width joiner
        "\ufeff"  # BOM / Zero-width no-break space
        "\u2060"  # Word joiner
    )
    for char in zero_width_chars:
        normalized = normalized.replace(char, "")

    # Step 3: Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized)

    # Step 4: Strip leading/trailing whitespace
    normalized = normalized.strip()

    # Step 5: Lowercase for ASCII/Latin (preserve CJK)
    # We use a character-by-character approach to preserve CJK
    result = []
    for char in normalized:
        # Check if char is ASCII or Latin script
        if ord(char) < 128 or unicodedata.category(char).startswith('L'):
            # Check if it's a script that should be lowercased
            name = unicodedata.name(char, "")
            if "CJK" not in name and "HIRAGANA" not in name and "KATAKANA" not in name:
                result.append(char.lower())
            else:
                result.append(char)
        else:
            result.append(char)

    return "".join(result)


def check_ambiguity(text: str) -> bool:
    """
    Check if text is ambiguous for asset creation.

    Ambiguity hints:
    - Text is too short (< 3 characters after normalization)
    - Text is all punctuation/symbols
    - Text is all whitespace

    Args:
        text: Normalized text

    Returns:
        True if ambiguous, False otherwise
    """
    if len(text) < 3:
        return True

    # Check if all non-alphanumeric (considering Unicode)
    has_alphanumeric = False
    for char in text:
        if unicodedata.category(char).startswith(('L', 'N')):
            has_alphanumeric = True
            break

    return not has_alphanumeric


def normalize_with_hint(text: str) -> NormalizationResult:
    """
    Normalize text and check for ambiguity.

    Args:
        text: Raw input text

    Returns:
        NormalizationResult with normalized text and ambiguity hint
    """
    normalized = normalize_core(text)
    return NormalizationResult(
        original=text,
        normalized=normalized,
        ambiguity_hint=check_ambiguity(normalized),
        norm_version=NORM_VERSION
    )


def generate_selection_fp(selected_text: str) -> str:
    """
    Generate fingerprint for selected text.

    selection_fp = sha256(normalize_core(selected_text))

    Args:
        selected_text: User-selected text

    Returns:
        64-character hex string (SHA-256)
    """
    normalized = normalize_core(selected_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_doc_fp(selection_fp: str, doc_id: UUID) -> str:
    """
    Generate document-bound fingerprint.

    doc_fp = sha256(selection_fp + doc_id)

    Note: Uses doc_id (stored_files.id) without version,
    so fingerprint is stable across doc versions.

    Args:
        selection_fp: Selection fingerprint
        doc_id: Document UUID (stored_files.id)

    Returns:
        64-character hex string
    """
    combined = f"{selection_fp}:{str(doc_id)}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def generate_anchor_fp(
    doc_fp: str,
    context_before: Optional[str],
    context_after: Optional[str],
    page_no: Optional[int]
) -> str:
    """
    Generate anchor fingerprint for precise location.

    anchor_fp = sha256(doc_fp + normalize_core(context_before) +
                       normalize_core(context_after) + page_no)

    Args:
        doc_fp: Document-bound fingerprint
        context_before: Text before selection (can be None)
        context_after: Text after selection (can be None)
        page_no: Page number (can be None)

    Returns:
        64-character hex string
    """
    ctx_before_norm = normalize_core(context_before or "")
    ctx_after_norm = normalize_core(context_after or "")
    page_str = str(page_no) if page_no is not None else ""

    combined = f"{doc_fp}:{ctx_before_norm}:{ctx_after_norm}:{page_str}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def generate_fingerprints(
    selected_text: str,
    doc_id: Optional[UUID] = None,
    context_before: Optional[str] = None,
    context_after: Optional[str] = None,
    page_no: Optional[int] = None,
    match_profile: str = DEFAULT_MATCH_PROFILE
) -> FingerprintResult:
    """
    Generate complete fingerprint set for a text selection.

    This is the main entry point for fingerprint generation.

    Args:
        selected_text: User-selected text
        doc_id: Source document UUID (optional)
        context_before: Text before selection (optional)
        context_after: Text after selection (optional)
        page_no: Page number (optional)
        match_profile: Match algorithm profile

    Returns:
        FingerprintResult with all fingerprints
    """
    # Always generate selection fingerprint
    selection_fp = generate_selection_fp(selected_text)

    # Generate doc_fp if doc_id provided
    doc_fp = None
    if doc_id is not None:
        doc_fp = generate_doc_fp(selection_fp, doc_id)

    # Generate anchor_fp if doc_fp and any context/page provided
    anchor_fp = None
    if doc_fp and (context_before or context_after or page_no is not None):
        anchor_fp = generate_anchor_fp(doc_fp, context_before, context_after, page_no)

    return FingerprintResult(
        selection_fp=selection_fp,
        doc_fp=doc_fp,
        anchor_fp=anchor_fp,
        norm_version=NORM_VERSION,
        match_profile=match_profile
    )


# Utility functions for testing normalization stability
def demonstrate_normalization(text: str) -> dict:
    """
    Demonstrate normalization for debugging/testing.

    Returns dict with original, normalized, and hex comparison.
    """
    normalized = normalize_core(text)
    return {
        "original": text,
        "original_hex": text.encode("utf-8").hex(),
        "normalized": normalized,
        "normalized_hex": normalized.encode("utf-8").hex(),
        "ambiguity_hint": check_ambiguity(normalized),
        "selection_fp": hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] + "..."
    }
