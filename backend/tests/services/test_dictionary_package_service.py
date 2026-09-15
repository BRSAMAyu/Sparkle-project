from __future__ import annotations

import gzip
import json
from pathlib import Path
from unittest.mock import patch

from app.services.dictionary_package_service import DictionaryPackageService


class _FakeMdx:
    def lookup(self, word: str):
        return {
            "word": word,
            "phonetic": None,
            "pos": "noun",
            "definitions": [f"{word} definition"],
            "examples": [f"{word} example"],
            "source": "oaldpe",
        }


def test_ensure_package_builds_gzip_payload(tmp_path: Path):
    service = DictionaryPackageService()
    definition = service._definitions["oxford-oaldpe-starter"]
    service._package_dir = tmp_path
    service._definitions["oxford-oaldpe-starter"] = definition.__class__(
        package_id=definition.package_id,
        name=definition.name,
        version=definition.version,
        description=definition.description,
        package_scope=definition.package_scope,
        source=definition.source,
        source_path=tmp_path / "oaldpe.mdx",
        words_file=tmp_path / "starter_words.txt",
    )
    (tmp_path / "oaldpe.mdx").write_bytes(b"not-a-real-mdx")
    (tmp_path / "starter_words.txt").write_text("hello\nworld\n", encoding="utf-8")

    with patch("app.services.dictionary_package_service.create_mdx_service", return_value=_FakeMdx()):
        package_path = service.ensure_package("oxford-oaldpe-starter")

    assert package_path.exists()
    payload = json.loads(gzip.decompress(package_path.read_bytes()).decode("utf-8"))
    assert payload["package"]["id"] == "oxford-oaldpe-starter"
    assert payload["entries"]["hello"]["source"] == "oaldpe"
    assert payload["entries"]["world"]["definitions"] == ["world definition"]


def test_list_packages_uses_manifest_metadata(tmp_path: Path):
    service = DictionaryPackageService()
    service._package_dir = tmp_path
    manifest_path = tmp_path / "oxford-oaldpe-starter.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "entry_count": 12,
                "size_bytes": 3456,
                "sha256": "deadbeef",
                "generated_at": "2026-03-19T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "oxford-oaldpe-starter.json.gz").write_bytes(b"gzip")

    packages = service.list_packages()

    assert packages[0]["entry_count"] == 12
    assert packages[0]["download_available"] is True
    assert packages[0]["sha256"] == "deadbeef"
