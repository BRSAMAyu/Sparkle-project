from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.compliance.legal_hold import LegalHoldService
from app.services.compliance.crypto_erase import CryptoEraseManager


@dataclass
class DeletionResult:
    allowed: bool
    reason: Optional[str] = None
    certificate_id: Optional[str] = None


class DeletionProtocol:
    """
    用户删除与被遗忘权流程
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.legal_hold_service = LegalHoldService(db)
        self.crypto_erase = CryptoEraseManager(db)

    async def request_deletion(self, user_id: UUID) -> DeletionResult:
        if await self.legal_hold_service.is_hold_active(user_id):
            return DeletionResult(allowed=False, reason="LEGAL_HOLD_ACTIVE")

        certificate = await self.crypto_erase.destroy_user_key(user_id)
        return DeletionResult(
            allowed=True,
            certificate_id=str(certificate.id)
        )
