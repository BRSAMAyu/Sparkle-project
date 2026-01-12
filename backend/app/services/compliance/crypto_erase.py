import base64
import os
from datetime import datetime
from typing import Optional, Tuple
from uuid import uuid4, UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.compliance import UserPersonaKey, CryptoShreddingCertificate
from app.services.compliance.key_provider import get_master_key_provider


class CryptoEraseManager:
    """
    云原生加密抹除管理器 (V3.1)
    使用用户级 DEK + 主密钥派生加密存储。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.master_key = self._load_master_key()

    def _load_master_key(self) -> bytes:
        provider = get_master_key_provider()
        return provider.get_master_key()

    def _encrypt_key(self, key_bytes: bytes) -> str:
        aes = AESGCM(self.master_key)
        nonce = os.urandom(12)
        ciphertext = aes.encrypt(nonce, key_bytes, None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def _decrypt_key(self, blob: str) -> bytes:
        data = base64.b64decode(blob.encode("ascii"))
        nonce, ciphertext = data[:12], data[12:]
        aes = AESGCM(self.master_key)
        return aes.decrypt(nonce, ciphertext, None)

    async def get_or_create_user_key(self, user_id: UUID) -> UserPersonaKey:
        stmt = select(UserPersonaKey).where(
            UserPersonaKey.user_id == user_id,
            UserPersonaKey.is_active == True
        )
        result = await self.db.execute(stmt)
        key = result.scalar_one_or_none()
        if key:
            return key

        dek = os.urandom(32)
        encrypted = self._encrypt_key(dek)
        key = UserPersonaKey(
            user_id=user_id,
            key_id=str(uuid4()),
            encrypted_key=encrypted,
            is_active=True
        )
        self.db.add(key)
        await self.db.commit()
        await self.db.refresh(key)
        return key

    async def encrypt_payload(self, user_id: UUID, plaintext: str) -> Tuple[str, str]:
        key = await self.get_or_create_user_key(user_id)
        if not key.encrypted_key:
            raise ValueError("User key is not available")
        dek = self._decrypt_key(key.encrypted_key)
        aes = AESGCM(dek)
        nonce = os.urandom(12)
        ciphertext = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        blob = base64.b64encode(nonce + ciphertext).decode("ascii")
        return blob, key.key_id

    async def decrypt_payload(self, user_id: UUID, blob: str) -> Optional[str]:
        stmt = select(UserPersonaKey).where(
            UserPersonaKey.user_id == user_id,
            UserPersonaKey.is_active == True
        )
        result = await self.db.execute(stmt)
        key = result.scalar_one_or_none()
        if not key or not key.encrypted_key:
            return None

        dek = self._decrypt_key(key.encrypted_key)
        data = base64.b64decode(blob.encode("ascii"))
        nonce, ciphertext = data[:12], data[12:]
        aes = AESGCM(dek)
        plaintext = aes.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    async def destroy_user_key(self, user_id: UUID, cloud_provider_ack: Optional[str] = None) -> CryptoShreddingCertificate:
        stmt = select(UserPersonaKey).where(
            UserPersonaKey.user_id == user_id,
            UserPersonaKey.is_active == True
        )
        result = await self.db.execute(stmt)
        key = result.scalar_one_or_none()
        if not key:
            raise ValueError("Active user key not found")

        key.is_active = False
        key.destroyed_at = datetime.utcnow()
        key.encrypted_key = None
        await self.db.commit()

        certificate = CryptoShreddingCertificate(
            user_id=user_id,
            key_id=key.key_id,
            cloud_provider_ack=cloud_provider_ack,
            certificate_data={
                "key_id": key.key_id,
                "destroyed_at": key.destroyed_at.isoformat()
            }
        )
        self.db.add(certificate)
        await self.db.commit()
        await self.db.refresh(certificate)
        return certificate
