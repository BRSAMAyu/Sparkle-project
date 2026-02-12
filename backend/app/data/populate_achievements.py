"""
填充初始成就数据到数据库
Populate initial achievement data to database
"""
import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.data.achievement_seeds import INITIAL_ACHIEVEMENTS, INITIAL_GALAXY_SKINS
from app.db.session import AsyncSessionLocal
from app.models.achievement import Achievement


def escape_sql(s: str) -> str:
    """Escape string for SQL (single quotes)"""
    if s is None:
        return "NULL"
    return f"'{s.replace(chr(39), chr(39) + chr(39))}'"


async def populate_achievements():
    """填充成就数据 - 使用 raw SQL 避免 enum 问题"""
    async with AsyncSessionLocal() as db:
        # Check if achievements already exist
        result = await db.execute(select(Achievement).limit(1))
        if result.scalar():
            print("Achievements already exist, skipping...")
            return

        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        # Populate achievements using raw SQL
        for data in INITIAL_ACHIEVEMENTS:
            type_str = data.get("type", "milestone")
            rarity_str = data.get("rarity", "common")
            visual_effect_str = data.get("visual_effect_type", "none")

            # Build the SQL query
            sql = text(f"""INSERT INTO achievements (
                id, name, description, icon_url, type, rarity, trigger_code, trigger_config,
                is_hidden, hint, prerequisites, visual_effect_type, visual_config,
                reward_config, total_unlocked, sort_order, category, parent_id,
                created_at, updated_at
            ) VALUES (
                '{data["id"]}',
                '{data["name"].replace(chr(39), chr(39) + chr(39))}',
                {escape_sql(data.get("description"))},
                {escape_sql(data.get("icon_url"))},
                '{type_str}'::achievementtype,
                '{rarity_str}'::achievementrarity,
                '{data["trigger_code"]}',
                '{json.dumps(data.get("trigger_config")).replace(chr(39), chr(39) + chr(39))}'::jsonb,
                {str(data.get("is_hidden", False)).lower()},
                {escape_sql(data.get("hint"))},
                '{json.dumps(data.get("prerequisites")).replace(chr(39), chr(39) + chr(39))}'::jsonb,
                '{visual_effect_str}'::visualeffecttype,
                '{json.dumps(data.get("visual_config")).replace(chr(39), chr(39) + chr(39))}'::jsonb,
                '{json.dumps(data.get("reward_config")).replace(chr(39), chr(39) + chr(39))}'::jsonb,
                0,
                {data.get("sort_order", 0)},
                {escape_sql(data.get("category"))},
                {escape_sql(data.get("parent_id"))},
                '{now}'::timestamp,
                '{now}'::timestamp
            )""")

            await db.execute(sql)

        # Populate galaxy skins
        for data in INITIAL_GALAXY_SKINS:
            rarity_str = data.get("rarity", "common")

            sql = text(f"""INSERT INTO galaxy_skins (
                id, name, description, preview_url, unlock_type, unlock_requirement,
                skin_config, rarity, sort_order, created_at, updated_at
            ) VALUES (
                '{data["id"]}',
                '{data["name"].replace(chr(39), chr(39) + chr(39))}',
                {escape_sql(data.get("description"))},
                {escape_sql(data.get("preview_url"))},
                {escape_sql(data.get("unlock_type"))},
                '{json.dumps(data.get("unlock_requirement")).replace(chr(39), chr(39) + chr(39))}'::jsonb,
                '{json.dumps(data.get("skin_config")).replace(chr(39), chr(39) + chr(39))}'::jsonb,
                '{rarity_str}'::achievementrarity,
                {data.get("sort_order", 0)},
                '{now}'::timestamp,
                '{now}'::timestamp
            )""")

            await db.execute(sql)

        await db.commit()
        print(f"Populated {len(INITIAL_ACHIEVEMENTS)} achievements and {len(INITIAL_GALAXY_SKINS)} galaxy skins")


async def show_achievement_summary():
    """Show achievement summary"""
    async with AsyncSessionLocal() as db:
        # Count by rarity
        from sqlalchemy import func
        result = await db.execute(
            select(Achievement.rarity, func.count(Achievement.id))
            .group_by(Achievement.rarity)
        )
        print("\nAchievements by rarity:")
        for rarity, count in result.all():
            print(f"  {rarity}: {count}")

        # Count by category
        result = await db.execute(
            select(Achievement.category, func.count(Achievement.id))
            .group_by(Achievement.category)
        )
        print("\nAchievements by category:")
        for category, count in result.all():
            print(f"  {category}: {count}")

        # Show galaxy skins
        result = await db.execute(select(Achievement))
        print(f"\nTotal achievements: {len(result.scalars().all())}")


if __name__ == "__main__":
    print("Populating achievement data...")
    asyncio.run(populate_achievements())
    asyncio.run(show_achievement_summary())
