"""
填充并同步成就定义数据到数据库
Populate and sync achievement definitions to database
"""
import asyncio
import json
from datetime import timezone, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.achievement_seeds import (
    INITIAL_ACHIEVEMENTS,
    INITIAL_GALAXY_SKINS,
    INITIAL_VISUAL_ELEMENTS,
)
from app.db.session import AsyncSessionLocal
from app.models.achievement import Achievement, GalaxySkin
from app.models.visual_element import VisualElement

SUPPORTED_REWARD_TYPES = {"photon", "title", "galaxy_skin", "freeze_charge", "visual_element"}
ACHIEVEMENT_I18N_DIR = Path(__file__).resolve().parent / "achievement_i18n"
SUPPORTED_ACHIEVEMENT_LOCALES = ("zh", "en")
ACHIEVEMENT_SYNC_FIELDS = [
    "name",
    "description",
    "icon_url",
    "type",
    "rarity",
    "trigger_code",
    "trigger_config",
    "is_hidden",
    "hint",
    "prerequisites",
    "visual_effect_type",
    "visual_config",
    "reward_config",
    "sort_order",
    "category",
    "parent_id",
]
ACHIEVEMENT_FIELD_DEFAULTS = {
    "trigger_config": {},
    "is_hidden": False,
    "visual_effect_type": "none",
    "reward_config": [],
    "is_limited": False,
}
GALAXY_SKIN_SYNC_FIELDS = [
    "name",
    "description",
    "preview_url",
    "unlock_type",
    "unlock_requirement",
    "skin_config",
    "rarity",
    "sort_order",
]
VISUAL_ELEMENT_SYNC_FIELDS = [
    "name",
    "description",
    "element_type",
    "rarity",
    "unlock_source",
    "unlock_requirement",
    "config",
    "preview_url",
    "icon_url",
    "is_active",
    "is_default",
    "sort_order",
    "category",
]
VISUAL_ELEMENT_FIELD_DEFAULTS = {
    "unlock_requirement": None,
    "config": {},
    "is_active": True,
    "is_default": False,
    "sort_order": 0,
}


def _load_achievement_i18n() -> dict[str, dict[str, dict[str, str]]]:
    i18n_map: dict[str, dict[str, dict[str, str]]] = {}
    for locale in SUPPORTED_ACHIEVEMENT_LOCALES:
        path = ACHIEVEMENT_I18N_DIR / f"{locale}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        for achievement_id, content in payload.items():
            if not isinstance(content, dict):
                continue
            entry = i18n_map.setdefault(
                achievement_id,
                {"name_i18n": {}, "description_i18n": {}},
            )
            name = content.get("name")
            description = content.get("description")
            if isinstance(name, str) and name:
                entry["name_i18n"][locale] = name
            if isinstance(description, str) and description:
                entry["description_i18n"][locale] = description
    return i18n_map


def _normalize_rewards(reward_config: Any) -> list[dict[str, Any]]:
    if not reward_config:
        return []
    if isinstance(reward_config, list):
        return reward_config
    return reward_config.get("rewards", [])


def validate_achievement_seed_data() -> None:
    skin_ids = {skin["id"] for skin in INITIAL_GALAXY_SKINS}
    visual_element_ids = {element["id"] for element in INITIAL_VISUAL_ELEMENTS}

    for achievement in INITIAL_ACHIEVEMENTS:
        for reward in _normalize_rewards(achievement.get("reward_config")):
            reward_type = reward.get("type")
            if reward_type not in SUPPORTED_REWARD_TYPES:
                raise ValueError(
                    f"Unsupported reward type '{reward_type}' in achievement '{achievement['id']}'"
                )
            if reward_type == "galaxy_skin":
                skin_id = reward.get("skin_id")
                if skin_id not in skin_ids:
                    raise ValueError(
                        f"Achievement '{achievement['id']}' references unknown galaxy skin '{skin_id}'"
                    )
            if reward_type == "visual_element":
                element_id = reward.get("element_id")
                if element_id not in visual_element_ids:
                    raise ValueError(
                        f"Achievement '{achievement['id']}' references unknown visual element '{element_id}'"
                    )


async def sync_achievement_definitions(db: AsyncSession) -> tuple[int, int, int]:
    synced_achievements = 0
    synced_skins = 0
    synced_visual_elements = 0
    i18n_map = _load_achievement_i18n()

    for data in INITIAL_ACHIEVEMENTS:
        achievement = await db.get(Achievement, data["id"])

        if achievement is None:
            achievement = Achievement(id=data["id"])
            db.add(achievement)

        for field in ACHIEVEMENT_SYNC_FIELDS:
            if field in data:
                value = data[field]
            else:
                value = ACHIEVEMENT_FIELD_DEFAULTS.get(field)
            setattr(achievement, field, value)

        i18n_entry = i18n_map.get(data["id"])
        if i18n_entry:
            achievement.name_i18n = i18n_entry.get("name_i18n", {})
            achievement.description_i18n = i18n_entry.get("description_i18n", {})

        achievement.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        synced_achievements += 1

    for data in INITIAL_GALAXY_SKINS:
        skin = await db.get(GalaxySkin, data["id"])

        if skin is None:
            skin = GalaxySkin(id=data["id"])
            db.add(skin)

        for field in GALAXY_SKIN_SYNC_FIELDS:
            setattr(skin, field, data.get(field))
        skin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        synced_skins += 1

    for data in INITIAL_VISUAL_ELEMENTS:
        element = await db.get(VisualElement, data["id"])

        if element is None:
            element = VisualElement(id=data["id"])
            db.add(element)

        for field in VISUAL_ELEMENT_SYNC_FIELDS:
            if field in data:
                value = data[field]
            else:
                value = VISUAL_ELEMENT_FIELD_DEFAULTS.get(field)
            setattr(element, field, value)
        unlock_source_value = getattr(element.unlock_source, "value", element.unlock_source)
        if unlock_source_value == "achievement" and not element.unlock_requirement:
            source_achievement_id = element.config.get("source_achievement_id")
            if source_achievement_id:
                element.unlock_requirement = {"achievement_id": source_achievement_id}
        element.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        synced_visual_elements += 1

    await db.commit()
    return synced_achievements, synced_skins, synced_visual_elements


async def _upsert_achievement_definitions() -> tuple[int, int, int]:
    async with AsyncSessionLocal() as db:
        return await sync_achievement_definitions(db)


async def populate_achievements() -> tuple[int, int, int]:
    """幂等同步成就、星系皮肤和荣耀装扮定义"""
    validate_achievement_seed_data()
    synced_achievements, synced_skins, synced_visual_elements = await _upsert_achievement_definitions()
    print(
        "Synchronized "
        f"{synced_achievements} achievements, "
        f"{synced_skins} galaxy skins and "
        f"{synced_visual_elements} visual elements"
    )
    return synced_achievements, synced_skins, synced_visual_elements


async def show_achievement_summary() -> None:
    """Show achievement summary"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Achievement.rarity, func.count(Achievement.id)).group_by(Achievement.rarity)
        )
        print("\nAchievements by rarity:")
        for rarity, count in result.all():
            print(f"  {rarity}: {count}")

        result = await db.execute(
            select(Achievement.category, func.count(Achievement.id)).group_by(Achievement.category)
        )
        print("\nAchievements by category:")
        for category, count in result.all():
            print(f"  {category}: {count}")

        total = await db.execute(select(func.count(Achievement.id)))
        print(f"\nTotal achievements: {total.scalar_one()}")


if __name__ == "__main__":
    print("Synchronizing achievement definitions...")
    asyncio.run(populate_achievements())
    asyncio.run(show_achievement_summary())
