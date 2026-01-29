"""Template registry for adaptive intervention messages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class TemplateVariant:
    variant_id: str
    content: str


@dataclass
class TemplateEntry:
    template_id: str
    intent_type: str
    support_level: int
    variants: list[TemplateVariant]


class TemplateRegistry:
    def __init__(self, template_path: str | None = None):
        if template_path:
            self.template_path = template_path
        else:
            root = Path(__file__).resolve().parents[2]
            self.template_path = str(root / "config" / "intervention_templates.yaml")
        self._templates: dict[str, list[TemplateEntry]] = {}

    def load_templates(self) -> None:
        with open(self.template_path, encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}

        entries: dict[str, list[TemplateEntry]] = {}
        for item in payload.get("templates", []):
            variants = [
                TemplateVariant(variant_id=v["id"], content=v["content"])
                for v in item.get("variants", [])
            ]
            entry = TemplateEntry(
                template_id=item["template_id"],
                intent_type=item["intent_type"],
                support_level=int(item.get("support_level", 3)),
                variants=variants,
            )
            entries.setdefault(entry.intent_type, []).append(entry)

        self._templates = entries

    def get_templates(self, intent_type: str, support_level: int) -> list[TemplateEntry]:
        entries = self._templates.get(intent_type, [])
        return [entry for entry in entries if entry.support_level == support_level]

    def get_all(self, intent_type: str) -> list[TemplateEntry]:
        return list(self._templates.get(intent_type, []))

    def ensure_loaded(self) -> None:
        if not self._templates:
            self.load_templates()
