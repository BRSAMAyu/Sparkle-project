"""Scenario pack registry helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.aurora.schemas import ScenarioPackManifest

try:  # pragma: no cover - yaml is optional at runtime, json is enough for tests
    import yaml
except Exception:  # pragma: no cover - keep registry usable without PyYAML
    yaml = None

PACKS_DIR = Path(__file__).resolve().parent
SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}


@dataclass(frozen=True)
class PackLoadResult:
    """A loaded pack manifest and its source path."""

    path: Path
    manifest: ScenarioPackManifest


class ScenarioPackRegistry:
    """In-memory registry for scenario pack manifests."""

    def __init__(self, manifests: Iterable[ScenarioPackManifest] | None = None) -> None:
        self._manifests: dict[str, ScenarioPackManifest] = {}
        if manifests:
            for manifest in manifests:
                self.register(manifest)

    def register(self, manifest: ScenarioPackManifest) -> None:
        self._manifests[manifest.id] = manifest

    def replace(self, manifest: ScenarioPackManifest) -> None:
        self._manifests[manifest.id] = manifest

    def remove(self, pack_id: str) -> ScenarioPackManifest | None:
        return self._manifests.pop(pack_id, None)

    def list(self) -> list[ScenarioPackManifest]:
        return sorted(self._manifests.values(), key=lambda item: (item.name.lower(), item.id))

    def get_by_id(self, pack_id: str) -> ScenarioPackManifest | None:
        return self._manifests.get(pack_id)

    def load_from_directory(self, directory: Path | str = PACKS_DIR) -> list[PackLoadResult]:
        results: list[PackLoadResult] = []
        for path in sorted(Path(directory).iterdir()):
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            manifest = load_pack_manifest(path)
            self.register(manifest)
            results.append(PackLoadResult(path=path, manifest=manifest))
        return results


def _load_raw_payload(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(raw)
    else:
        if yaml is None:  # pragma: no cover - exercised only when yaml missing
            raise RuntimeError(f"YAML support is unavailable, cannot load {path}")
        payload = yaml.safe_load(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Scenario pack manifest must be a mapping: {path}")
    return payload


def load_pack_manifest(path: Path | str) -> ScenarioPackManifest:
    """Load a scenario pack manifest from JSON or YAML."""

    manifest_path = Path(path)
    payload = _load_raw_payload(manifest_path)
    return ScenarioPackManifest.model_validate(payload)


def load_pack_registry(directory: Path | str = PACKS_DIR) -> ScenarioPackRegistry:
    """Load all manifests from a directory into a registry."""

    registry = ScenarioPackRegistry()
    registry.load_from_directory(Path(directory))
    return registry


def load_default_registry() -> ScenarioPackRegistry:
    """Load the built-in scenario pack registry."""

    return load_pack_registry(PACKS_DIR)


def build_pack_context_overlay(
    user_signals: Mapping[str, Any],
    manifest: ScenarioPackManifest,
) -> dict[str, Any]:
    """Lightweight pack-aware context hook for later signal assembly."""

    from app.scenario_packs.readiness import assemble_pack_context

    assembly = assemble_pack_context(user_signals, manifest)
    return {
        "pack_id": manifest.id,
        "pack_name": manifest.name,
        "ready": assembly.ready,
        "core_signals": assembly.core_signals,
        "enhanced_signals": assembly.enhanced_signals,
        "optional_signals": assembly.optional_signals,
        "missing_signals": assembly.missing_signals,
    }


def flatten_node_signals(manifest: ScenarioPackManifest) -> set[str]:
    """Return pack-relevant signal keys from node configs and readiness criteria."""

    signal_keys: set[str] = set(manifest.readiness_criteria.keys())
    for node in manifest.backbone_nodes:
        for key in node.ux_mapping.get("signal_terms", []):
            if isinstance(key, str) and key.strip():
                signal_keys.add(key.strip())
        for trigger_key in node.transition_triggers.keys():
            if trigger_key.strip():
                signal_keys.add(trigger_key.strip())
    return signal_keys
