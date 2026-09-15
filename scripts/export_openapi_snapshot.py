#!/usr/bin/env python3
"""Export canonical OpenAPI snapshot for contract checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _canonicalize(spec: dict) -> dict:
    """Remove noisy fields and sort maps for stable diffing."""
    spec.pop("servers", None)

    name_pattern = re.compile(r"^app__schemas__[^_]+__")

    def _normalize_schema_name(name: str) -> str:
        return name_pattern.sub("", name)

    def _normalize_ref(value: str) -> str:
        marker = "#/components/schemas/"
        if not value.startswith(marker):
            return value
        schema_name = value[len(marker):]
        return f"{marker}{_normalize_schema_name(schema_name)}"

    # Normalize schema keys to avoid module-path naming jitter.
    components = spec.get("components", {})
    schemas = components.get("schemas", {})
    if isinstance(schemas, dict):
        normalized = {}
        for key, val in schemas.items():
            normalized[_normalize_schema_name(key)] = val
        components["schemas"] = normalized
        spec["components"] = components

    def _sort_obj(value):
        if isinstance(value, dict):
            normalized_dict = {}
            for key in sorted(value.keys()):
                child = value[key]
                if key == "$ref" and isinstance(child, str):
                    normalized_dict[key] = _normalize_ref(child)
                else:
                    normalized_dict[key] = _sort_obj(child)
            return normalized_dict
        if isinstance(value, list):
            return [_sort_obj(v) for v in value]
        return value

    return _sort_obj(spec)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export OpenAPI snapshot")
    parser.add_argument("--output", default="docs/contracts/openapi_snapshot.json")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from app.main import app  # noqa: WPS433

    spec = app.openapi()
    canonical = _canonicalize(spec)

    output = repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(canonical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✅ OpenAPI snapshot exported: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
