"""
将现有偏好数据迁移到 user_preferences_center 表
"""
import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User, PushPreference
from app.models.user_preferences import UserPreferencesCenter


async def migrate() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        migrated = 0
        for user in users:
            existing = await db.execute(
                select(UserPreferencesCenter).where(
                    UserPreferencesCenter.user_id == user.id
                )
            )
            if existing.scalar_one_or_none():
                continue

            push_pref_result = await db.execute(
                select(PushPreference).where(PushPreference.user_id == user.id)
            )
            push_pref = push_pref_result.scalar_one_or_none()

            explicit = {
                "depth_preference": user.depth_preference,
                "curiosity_preference": user.curiosity_preference,
                "persona_type": push_pref.persona_type if push_pref else "coach",
                "daily_cap": push_pref.daily_cap if push_pref else 5,
                "timezone": push_pref.timezone if push_pref else "Asia/Shanghai",
                "enable_push": True,
                "enable_curiosity_push": push_pref.enable_curiosity if push_pref else True,
            }

            if push_pref and push_pref.active_slots:
                explicit["active_slots"] = _convert_slots(push_pref.active_slots)

            prefs = UserPreferencesCenter(
                user_id=user.id,
                explicit=explicit,
                inferred={},
            )
            db.add(prefs)
            migrated += 1

        await db.commit()
        print(f"Migrated {migrated} users")


def _convert_slots(slots):
    """转换时间段格式"""
    if not slots:
        return []
    result = []
    for slot in slots:
        start = slot.get("start", "08:00")
        end = slot.get("end", "09:00")
        start_min = int(start.split(":")[0]) * 60 + int(start.split(":")[1])
        end_min = int(end.split(":")[0]) * 60 + int(end.split(":")[1])
        result.append({
            "dow": [0, 1, 2, 3, 4],
            "start_min": start_min,
            "end_min": end_min,
        })
    return result


if __name__ == "__main__":
    asyncio.run(migrate())
