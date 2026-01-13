from dataclasses import dataclass
from typing import Optional
import inspect
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
        hold_check = self.legal_hold_service.is_hold_active
        if getattr(hold_check, "__self__", None) is None and len(inspect.signature(hold_check).parameters) >= 2:
            hold_active = await hold_check(self.legal_hold_service, user_id)
        else:
            hold_active = await hold_check(user_id)

        if hold_active:
            return DeletionResult(allowed=False, reason="LEGAL_HOLD_ACTIVE")

        destroy_key = self.crypto_erase.destroy_user_key
        if getattr(destroy_key, "__self__", None) is None and len(inspect.signature(destroy_key).parameters) >= 2:
            certificate = await destroy_key(self.crypto_erase, user_id)
        else:
            certificate = await destroy_key(user_id)
        return DeletionResult(
            allowed=True,
            certificate_id=str(certificate.id)
        )
