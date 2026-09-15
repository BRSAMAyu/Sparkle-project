"""Registry and subject matcher for Sprint Pack JSON assets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from loguru import logger
except ModuleNotFoundError:
    import logging

    class _FallbackLogger:
        def __init__(self) -> None:
            self._logger = logging.getLogger(__name__)

        def warning(self, message: str, *args: Any) -> None:
            self._logger.warning(message.format(*args))

    logger = _FallbackLogger()

PACKS_DIR = Path(__file__).resolve().parent
PACK_VERSION_SUFFIX = "_v1"


def _pack_id_from_path(path: Path) -> str:
    stem = path.stem
    if stem.endswith(PACK_VERSION_SUFFIX):
        return stem[: -len(PACK_VERSION_SUFFIX)]
    return stem


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_\-]+", "", text)
    text = re.sub(r"[，。！？、,.;:!?'\"]+", "", text)
    text = re.sub(r"[\(\)（）\[\]【】{}<>《》/\\|]+", "", text)
    return text


def _normalize_pack_id(pack_id: str) -> str:
    normalized = str(pack_id or "").strip()
    if "@" in normalized:
        normalized = normalized.split("@", 1)[0]
    if normalized.endswith(PACK_VERSION_SUFFIX):
        normalized = normalized[: -len(PACK_VERSION_SUFFIX)]
    return normalized


def _substring_score(user_input: str, candidate: str) -> float:
    if not user_input or not candidate:
        return 0.0
    if user_input == candidate:
        return 100.0
    if candidate in user_input and len(candidate) >= 2:
        return 80.0 + min(len(candidate) / max(len(user_input), 1), 1.0)
    if user_input in candidate and len(user_input) >= 2:
        return 60.0 + min(len(user_input) / max(len(candidate), 1), 1.0)
    return 0.0


class SprintPackRegistry:
    """In-memory registry for Sprint Pack metadata and subject matching."""

    def __init__(self, packs_dir: Path | str = PACKS_DIR) -> None:
        self.packs_dir = Path(packs_dir)
        self._packs: dict[str, dict[str, Any]] | None = None

    def scan_packs_dir(self) -> dict[str, dict]:
        """Scan the Sprint Pack directory and return metadata by pack file stem."""

        packs: dict[str, dict[str, Any]] = {}
        for path in sorted(self.packs_dir.glob("*_v1.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to scan Sprint Pack {}: {}", path, exc)
                continue
            if not isinstance(payload, dict):
                logger.warning("Sprint Pack payload must be a JSON object: {}", path)
                continue

            pack_id = _pack_id_from_path(path)
            packs[pack_id] = {
                "pack_id": pack_id,
                "file_stem": pack_id,
                "filename": path.name,
                "path": str(path),
                "id": payload.get("id"),
                "name": payload.get("name"),
                "version": payload.get("version"),
                "subject": payload.get("subject"),
                "aliases": payload.get("aliases"),
                "description": payload.get("description"),
                "author": payload.get("author"),
                "created_at": payload.get("created_at"),
            }

        self._packs = packs
        return dict(packs)

    def get_pack_meta(self, pack_id: str) -> dict | None:
        """Return metadata for a pack id, JSON id, or versioned file stem."""

        if self._packs is None:
            self.scan_packs_dir()
        assert self._packs is not None
        return self._packs.get(_normalize_pack_id(pack_id))

    def match_subject(self, user_input: str) -> str | None:
        """Return the best matching Sprint Pack file stem for the user's subject text."""

        user_key = str(user_input or "").strip().lower()
        user_text = _normalize_text(user_input)
        if not user_text:
            return None

        if self._packs is None:
            self.scan_packs_dir()
        assert self._packs is not None

        alias_match = self._match_alias(user_key, user_text)
        if alias_match is not None:
            return alias_match

        subject_match = self._best_field_match(user_text, "subject")
        if subject_match is not None:
            return subject_match

        return self._best_field_match(user_text, "name")

    def list_available_subjects(self) -> list[str]:
        """Return human-readable subject names for all available Sprint Packs."""

        if self._packs is None:
            self.scan_packs_dir()
        assert self._packs is not None

        subjects = {
            str(meta.get("subject") or meta.get("name") or pack_id).strip()
            for pack_id, meta in self._packs.items()
            if str(meta.get("subject") or meta.get("name") or pack_id).strip()
        }
        return sorted(subjects)

    def _match_alias(self, user_key: str, user_text: str) -> str | None:
        from app.sprint_packs.sprint_pack_loader import _SUBJECT_ALIASES

        raw_match = _SUBJECT_ALIASES.get(user_key)
        if raw_match and self.get_pack_meta(raw_match) is not None:
            return raw_match

        normalized_aliases = {
            _normalize_text(alias): pack_id
            for alias, pack_id in _SUBJECT_ALIASES.items()
        }
        normalized_match = normalized_aliases.get(user_text)
        if normalized_match and self.get_pack_meta(normalized_match) is not None:
            return normalized_match
        return None

    def _best_field_match(self, user_text: str, field_name: str) -> str | None:
        assert self._packs is not None

        best_pack_id: str | None = None
        best_score = 0.0
        for pack_id, meta in self._packs.items():
            candidate = _normalize_text(meta.get(field_name))
            score = _substring_score(user_text, candidate)
            if score > best_score:
                best_score = score
                best_pack_id = pack_id

        return best_pack_id if best_score > 0 else None
