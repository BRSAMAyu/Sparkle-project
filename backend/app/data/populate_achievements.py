"""
填充并同步成就定义数据到数据库
Populate and sync achievement definitions to database
"""
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.achievement_seeds import INITIAL_ACHIEVEMENTS, INITIAL_GALAXY_SKINS
from app.db.session import AsyncSessionLocal
from app.models.achievement import Achievement, GalaxySkin

SUPPORTED_REWARD_TYPES = {"photon", "title", "galaxy_skin", "freeze_charge"}
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


async def sync_achievement_definitions(db: AsyncSession) -> tuple[int, int]:
    synced_achievements = 0
    synced_skins = 0
    i18n_map = _load_achievement_i18n()

    for data in INITIAL_ACHIEVEMENTS:
        achievement = await db.get(Achievement, data["id"])

        if achievement is None:
            achievement = Achievement(id=data["id"])
            db.add(achievement)

        for field in ACHIEVEMENT_SYNC_FIELDS:
            setattr(achievement, field, data.get(field))

        i18n_entry = i18n_map.get(data["id"])
        if i18n_entry:
            achievement.name_i18n = i18n_entry.get("name_i18n", {})
            achievement.description_i18n = i18n_entry.get("description_i18n", {})

        achievement.updated_at = datetime.now(UTC).replace(tzinfo=None)
        synced_achievements += 1

    for data in INITIAL_GALAXY_SKINS:
        skin = await db.get(GalaxySkin, data["id"])

        if skin is None:
            skin = GalaxySkin(id=data["id"])
            db.add(skin)

        for field in GALAXY_SKIN_SYNC_FIELDS:
            setattr(skin, field, data.get(field))
        skin.updated_at = datetime.now(UTC).replace(tzinfo=None)
        synced_skins += 1

    await db.commit()
    return synced_achievements, synced_skins


async def _upsert_achievement_definitions() -> tuple[int, int]:
    async with AsyncSessionLocal() as db:
        return await sync_achievement_definitions(db)


async def populate_achievements() -> tuple[int, int]:
    """幂等同步成就和星系皮肤定义"""
    validate_achievement_seed_data()
    synced_achievements, synced_skins = await _upsert_achievement_definitions()
    print(
        f"Synchronized {synced_achievements} achievements and {synced_skins} galaxy skins"
    )
    return synced_achievements, synced_skins


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
