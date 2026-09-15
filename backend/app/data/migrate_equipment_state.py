"""
回填用户装备真源状态
Backfill user equipment state
"""
import asyncio

from app.db.session import AsyncSessionLocal
from app.services.equipment_service import EquipmentService


async def migrate_equipment_state() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        service = EquipmentService(db)
        summary = await service.backfill_user_equipment_state()
        print(summary)
        return summary


if __name__ == "__main__":
    asyncio.run(migrate_equipment_state())
