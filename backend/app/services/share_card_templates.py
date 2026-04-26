"""
Share card template definitions.

Four visual styles for achievement share cards:
- cosmic: Starry gradient background with particles and glow (default)
- minimal: Clean solid color with minimal decorations
- neon: Dark background with neon glow effects
- elegant: Golden borders with elegant typography
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.i18n import I18n


@dataclass(slots=True)
class TemplateStyle:
    """Color/style configuration for a template."""

    bg_top: tuple[int, int, int]
    bg_bottom: tuple[int, int, int]
    bg_mid: tuple[int, int, int] | None = None
    accent: tuple[int, int, int] = (255, 255, 255)
    glow: tuple[int, int, int] = (200, 200, 200)
    panel: tuple[int, int, int, int] = (255, 255, 255, 28)
    particle_count: int = 90
    particle_alpha_min: int = 70
    particle_alpha_max: int = 180


@dataclass(slots=True)
class ShareCardTemplate:
    """Template definition for share card rendering."""

    id: str
    name: str
    description: str
    style_map: dict[str, TemplateStyle]
    preview_url: str | None = None

    def get_style(self, rarity: str) -> TemplateStyle:
        """Get style for a given rarity."""
        return self.style_map.get(rarity, self.style_map["common"])


# ============================================================================
# COSMIC TEMPLATE (Default)
# ============================================================================

COSMIC_STYLES: dict[str, TemplateStyle] = {
    "common": TemplateStyle(
        bg_top=(51, 65, 85),
        bg_bottom=(15, 23, 42),
        accent=(226, 232, 240),
        glow=(148, 163, 184),
        panel=(255, 255, 255, 28),
    ),
    "rare": TemplateStyle(
        bg_top=(120, 53, 15),
        bg_bottom=(69, 26, 3),
        accent=(253, 224, 71),
        glow=(251, 191, 36),
        panel=(255, 255, 255, 30),
    ),
    "epic": TemplateStyle(
        bg_top=(76, 29, 149),
        bg_bottom=(59, 7, 100),
        accent=(216, 180, 254),
        glow=(192, 132, 252),
        panel=(255, 255, 255, 30),
    ),
    "legendary": TemplateStyle(
        bg_top=(5, 150, 105),
        bg_mid=(37, 99, 235),
        bg_bottom=(126, 34, 206),
        accent=(254, 240, 138),
        glow=(251, 191, 36),
        panel=(255, 255, 255, 36),
    ),
}

COSMIC_TEMPLATE = ShareCardTemplate(
    id="cosmic",
    name=I18n.t("share_card.cosmic_name", locale="zh"),
    description=I18n.t("share_card.cosmic_desc", locale="zh"),
    style_map=COSMIC_STYLES,
)


# ============================================================================
# MINIMAL TEMPLATE
# ============================================================================

MINIMAL_STYLES: dict[str, TemplateStyle] = {
    "common": TemplateStyle(
        bg_top=(250, 250, 250),
        bg_bottom=(245, 245, 245),
        accent=(100, 100, 100),
        glow=(180, 180, 180),
        panel=(0, 0, 0, 8),
        particle_count=0,
    ),
    "rare": TemplateStyle(
        bg_top=(255, 251, 235),
        bg_bottom=(254, 243, 199),
        accent=(161, 98, 7),
        glow=(217, 119, 6),
        panel=(161, 98, 7, 12),
        particle_count=0,
    ),
    "epic": TemplateStyle(
        bg_top=(250, 245, 255),
        bg_bottom=(243, 232, 255),
        accent=(107, 33, 168),
        glow=(147, 51, 234),
        panel=(107, 33, 168, 12),
        particle_count=0,
    ),
    "legendary": TemplateStyle(
        bg_top=(236, 253, 245),
        bg_bottom=(209, 250, 229),
        accent=(5, 150, 105),
        glow=(16, 185, 129),
        panel=(5, 150, 105, 15),
        particle_count=0,
    ),
}

MINIMAL_TEMPLATE = ShareCardTemplate(
    id="minimal",
    name=I18n.t("share_card.minimal_name", locale="zh"),
    description=I18n.t("share_card.minimal_desc", locale="zh"),
    style_map=MINIMAL_STYLES,
)


# ============================================================================
# NEON TEMPLATE
# ============================================================================

NEON_STYLES: dict[str, TemplateStyle] = {
    "common": TemplateStyle(
        bg_top=(10, 10, 10),
        bg_bottom=(5, 5, 5),
        accent=(0, 255, 255),
        glow=(0, 255, 255),
        panel=(0, 255, 255, 15),
        particle_count=60,
        particle_alpha_min=100,
        particle_alpha_max=200,
    ),
    "rare": TemplateStyle(
        bg_top=(10, 10, 10),
        bg_bottom=(5, 5, 5),
        accent=(255, 0, 255),
        glow=(255, 0, 255),
        panel=(255, 0, 255, 15),
        particle_count=60,
        particle_alpha_min=100,
        particle_alpha_max=200,
    ),
    "epic": TemplateStyle(
        bg_top=(10, 10, 10),
        bg_bottom=(5, 5, 5),
        accent=(128, 0, 255),
        glow=(128, 0, 255),
        panel=(128, 0, 255, 15),
        particle_count=60,
        particle_alpha_min=100,
        particle_alpha_max=200,
    ),
    "legendary": TemplateStyle(
        bg_top=(10, 10, 10),
        bg_bottom=(5, 5, 5),
        accent=(255, 215, 0),
        glow=(255, 215, 0),
        panel=(255, 215, 0, 20),
        particle_count=80,
        particle_alpha_min=120,
        particle_alpha_max=255,
    ),
}

NEON_TEMPLATE = ShareCardTemplate(
    id="neon",
    name=I18n.t("share_card.neon_name", locale="zh"),
    description=I18n.t("share_card.neon_desc", locale="zh"),
    style_map=NEON_STYLES,
)


# ============================================================================
# ELEGANT TEMPLATE
# ============================================================================

ELEGANT_STYLES: dict[str, TemplateStyle] = {
    "common": TemplateStyle(
        bg_top=(255, 248, 240),
        bg_bottom=(250, 240, 230),
        accent=(139, 90, 43),
        glow=(205, 170, 125),
        panel=(139, 90, 43, 20),
        particle_count=30,
        particle_alpha_min=40,
        particle_alpha_max=100,
    ),
    "rare": TemplateStyle(
        bg_top=(255, 250, 240),
        bg_bottom=(255, 240, 200),
        accent=(184, 134, 11),
        glow=(218, 165, 32),
        panel=(184, 134, 11, 25),
        particle_count=40,
        particle_alpha_min=60,
        particle_alpha_max=120,
    ),
    "epic": TemplateStyle(
        bg_top=(250, 240, 255),
        bg_bottom=(240, 225, 255),
        accent=(138, 43, 226),
        glow=(186, 85, 211),
        panel=(138, 43, 226, 25),
        particle_count=40,
        particle_alpha_min=60,
        particle_alpha_max=120,
    ),
    "legendary": TemplateStyle(
        bg_top=(255, 250, 205),
        bg_bottom=(255, 235, 150),
        accent=(212, 175, 55),
        glow=(255, 215, 0),
        panel=(212, 175, 55, 30),
        particle_count=50,
        particle_alpha_min=80,
        particle_alpha_max=150,
    ),
}

ELEGANT_TEMPLATE = ShareCardTemplate(
    id="elegant",
    name=I18n.t("share_card.elegant_name", locale="zh"),
    description=I18n.t("share_card.elegant_desc", locale="zh"),
    style_map=ELEGANT_STYLES,
)


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATES: dict[str, ShareCardTemplate] = {
    "cosmic": COSMIC_TEMPLATE,
    "minimal": MINIMAL_TEMPLATE,
    "neon": NEON_TEMPLATE,
    "elegant": ELEGANT_TEMPLATE,
}

TEMPLATE_LIST = list(TEMPLATES.values())


def get_template(template_id: str) -> ShareCardTemplate:
    """Get template by ID, returns cosmic as default."""
    return TEMPLATES.get(template_id, COSMIC_TEMPLATE)


def get_all_templates() -> list[ShareCardTemplate]:
    """Get all available templates."""
    return TEMPLATE_LIST
