from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.services.mdx_dictionary_service import create_mdx_service


@dataclass(frozen=True)
class DictionaryPackageDefinition:
    package_id: str
    name: str
    version: str
    description: str
    package_scope: str
    source: str
    source_path: Path | None
    words_file: Path | None


class DictionaryPackageService:
    def __init__(self) -> None:
        preferred_dir = Path(settings.DICTIONARY_PACKAGE_DIR)
        self._package_dir = preferred_dir.resolve() if not preferred_dir.is_absolute() else preferred_dir
        self._fallback_entries_path = Path(__file__).resolve().parents[1] / "data" / "oxford_starter_fallback_entries.json"
        if not self._is_directory_writable(self._package_dir):
            self._package_dir = (Path(settings.UPLOAD_DIR) / "dictionary_packages").resolve()
            self._package_dir.mkdir(parents=True, exist_ok=True)

        self._definitions = {
            "oxford-oaldpe-starter": DictionaryPackageDefinition(
                package_id="oxford-oaldpe-starter",
                name="Oxford Starter Pack",
                version="1.0.0",
                description="Oxford OALDPE starter package for common learning words.",
                package_scope="starter",
                source="oxford-oaldpe",
                source_path=self._resolve_source_path(settings.MDX_DICTIONARY_PATH),
                words_file=(Path(__file__).resolve().parents[1] / "data" / "oxford_starter_words.txt"),
            )
        }

    def _resolve_source_path(self, configured_path: str | None) -> Path | None:
        if configured_path:
            return Path(configured_path).resolve()
        candidates = [
            Path(settings.DICTIONARY_PACKAGE_DIR).resolve().parent / "oaldpe.mdx",
            self._package_dir.parent / "oaldpe.mdx",
            Path(__file__).resolve().parents[2] / "data" / "dictionaries" / "oaldpe.mdx",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _is_directory_writable(self, directory: Path) -> bool:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".sparkle-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def list_packages(self) -> list[dict[str, Any]]:
        packages: list[dict[str, Any]] = []
        for definition in self._definitions.values():
            manifest = self._read_manifest(definition.package_id)
            packages.append(
                {
                    "id": definition.package_id,
                    "name": definition.name,
                    "version": definition.version,
                    "description": definition.description,
                    "package_scope": definition.package_scope,
                    "source": definition.source,
                    "format": "json.gz",
                    "entry_count": manifest.get("entry_count", 0) if manifest else 0,
                    "size_bytes": manifest.get("size_bytes") if manifest else None,
                    "sha256": manifest.get("sha256") if manifest else None,
                    "generated_at": manifest.get("generated_at") if manifest else None,
                    "download_available": self._package_path(definition.package_id).exists(),
                }
            )
        return packages

    def lookup_fallback_entry(self, word: str) -> dict[str, Any] | None:
        normalized_word = word.strip().lower()
        if not normalized_word:
            return None
        entries = self._load_fallback_entries()
        entry = entries.get(normalized_word)
        if not entry:
            return None
        return {
            "word": normalized_word,
            "phonetic": entry.get("phonetic"),
            "pos": entry.get("pos"),
            "definitions": entry.get("definitions") or [],
            "examples": entry.get("examples") or [],
            "source": entry.get("source") or "oaldpe",
        }

    def ensure_package(self, package_id: str) -> Path:
        definition = self._definitions.get(package_id)
        if definition is None:
            raise FileNotFoundError(f"Unknown dictionary package: {package_id}")

        package_path = self._package_path(package_id)
        if package_path.exists():
            return package_path

        self._package_dir.mkdir(parents=True, exist_ok=True)
        payload = self._build_payload(definition)
        raw_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        compressed = gzip.compress(raw_bytes)
        package_path.write_bytes(compressed)
        self._manifest_path(package_id).write_text(
            json.dumps(
                {
                    "id": definition.package_id,
                    "version": definition.version,
                    "entry_count": len(payload["entries"]),
                    "size_bytes": len(compressed),
                    "sha256": hashlib.sha256(compressed).hexdigest(),
                    "generated_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return package_path

    def _build_payload(self, definition: DictionaryPackageDefinition) -> dict[str, Any]:
        if definition.words_file is None or not definition.words_file.exists():
            raise FileNotFoundError("Starter word list is not available")

        words = [
            line.strip().lower()
            for line in definition.words_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        entries: dict[str, Any] = {}
        mdx = None
        if definition.source_path is not None and definition.source_path.exists():
            mdx = create_mdx_service(str(definition.source_path))

        for word in words:
            result = mdx.lookup(word) if mdx else self.lookup_fallback_entry(word)
            if not result:
                continue
            entries[word] = {
                "word": str(result.get("word") or word).lower(),
                "phonetic": result.get("phonetic"),
                "pos": result.get("pos"),
                "definitions": result.get("definitions") or [],
                "examples": result.get("examples") or [],
                "source": result.get("source") or definition.source,
                "offline_package": definition.package_id,
            }

        if not entries:
            raise RuntimeError("No entries were extracted for the offline dictionary package")

        return {
            "package": {
                "id": definition.package_id,
                "name": definition.name,
                "version": definition.version,
                "description": definition.description,
                "package_scope": definition.package_scope,
                "source": definition.source,
                "format": "json.gz",
            },
            "entries": entries,
        }

    def _package_path(self, package_id: str) -> Path:
        return self._package_dir / f"{package_id}.json.gz"

    def _manifest_path(self, package_id: str) -> Path:
        return self._package_dir / f"{package_id}.manifest.json"

    def _read_manifest(self, package_id: str) -> dict[str, Any] | None:
        manifest_path = self._manifest_path(package_id)
        if not manifest_path.exists():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _load_fallback_entries(self) -> dict[str, dict[str, Any]]:
        if not self._fallback_entries_path.exists():
            return {}
        payload = json.loads(self._fallback_entries_path.read_text(encoding="utf-8"))
        return {
            str(key).strip().lower(): value
            for key, value in payload.items()
            if isinstance(value, dict)
        }


dictionary_package_service = DictionaryPackageService()
