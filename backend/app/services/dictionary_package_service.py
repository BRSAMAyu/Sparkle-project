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
        self._project_root = Path(__file__).resolve().parents[3]
        self._package_dir = Path(settings.DICTIONARY_PACKAGE_DIR)
        if not self._package_dir.is_absolute():
            self._package_dir = (self._project_root / self._package_dir).resolve()

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
            path = Path(configured_path)
            if not path.is_absolute():
                path = (self._project_root / path).resolve()
            return path
        default_path = self._project_root / "data" / "dictionaries" / "oaldpe.mdx"
        return default_path if default_path.exists() else None

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
        if definition.source_path is None or not definition.source_path.exists():
            raise FileNotFoundError("Oxford dictionary source file is not available")
        if definition.words_file is None or not definition.words_file.exists():
            raise FileNotFoundError("Starter word list is not available")

        mdx = create_mdx_service(str(definition.source_path))
        if mdx is None:
            raise RuntimeError("MDX dictionary service is unavailable")

        words = [
            line.strip().lower()
            for line in definition.words_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        entries: dict[str, Any] = {}
        for word in words:
            result = mdx.lookup(word)
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


dictionary_package_service = DictionaryPackageService()
