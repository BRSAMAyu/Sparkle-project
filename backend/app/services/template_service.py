"""Template selection and rendering for interventions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from app.core.cache import cache_service
from app.learning.prompt_bandit import PromptBandit
from app.services.template_registry import TemplateEntry, TemplateRegistry, TemplateVariant


@dataclass
class SelectedTemplate:
    template_id: str
    intent_type: str
    support_level: int
    variant_id: str
    content: str


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class TemplateService:
    def __init__(self, registry: TemplateRegistry, bandit: PromptBandit | None = None):
        self.registry = registry
        self.bandit = bandit

    async def select_variant(
        self,
        intent_type: str,
        support_level: int,
        user_id: str,
    ) -> SelectedTemplate:
        self.registry.ensure_loaded()
        templates = self.registry.get_templates(intent_type, support_level)
        if not templates:
            candidates = self.registry.get_all(intent_type)
            if not candidates:
                raise ValueError(f"No templates available for {intent_type} level {support_level}")
            templates = sorted(
                candidates,
                key=lambda entry: abs(entry.support_level - support_level),
            )

        entry = templates[0]
        variant = await self._choose_variant(entry, user_id)
        return SelectedTemplate(
            template_id=entry.template_id,
            intent_type=entry.intent_type,
            support_level=entry.support_level,
            variant_id=variant.variant_id,
            content=variant.content,
        )

    async def _choose_variant(
        self,
        entry: TemplateEntry,
        user_id: str,
    ) -> TemplateVariant:
        variants = entry.variants
        if not variants:
            raise ValueError(f"Template {entry.template_id} has no variants")

        if self.bandit is not None:
            try:
                workflow_id = f"intervention:{entry.intent_type}:{entry.support_level}"
                arm_list = [variant.variant_id for variant in variants]
                chosen = await self.bandit.select(workflow_id, arm_list)
                for variant in variants:
                    if variant.variant_id == chosen:
                        return variant
            except Exception:
                pass

        recent_key = f"intervention:recent:{user_id}:{entry.intent_type}:{entry.support_level}"
        recent = await cache_service.get(recent_key)
        recent_ids = recent if isinstance(recent, list) else []
        pool = [v for v in variants if v.variant_id not in recent_ids]
        if not pool:
            pool = variants
        selected = random.choice(pool)

        updated = (recent_ids + [selected.variant_id])[-6:]
        await cache_service.set(recent_key, updated, ttl=86400)
        return selected

    def render(self, template: SelectedTemplate, variables: dict[str, Any]) -> str:
        return template.content.format_map(_SafeDict(variables))
