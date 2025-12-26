"""
Account Lockout Policy Implementation
Prevents brute force attacks by locking accounts after failed login attempts
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.core.cache import cache_service
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger


class AccountLockoutService:
    """Service to handle account lockout logic"""
    
    def __init__(self):
        self.lockout_duration = timedelta(minutes=15)  # 15 minutes lockout
        self.max_failed_attempts = 5
    
    async def get_failed_attempts(self, user_id: str) -> int:
        """Get number of failed login attempts for a user"""
        key = f"lockout:{user_id}"
        attempts = await cache_service.get(key)
        return int(attempts) if attempts else 0
    
    async def increment_failed_attempts(self, user_id: str) -> int:
        """Increment failed login attempts counter"""
        key = f"lockout:{user_id}"
        attempts = await cache_service.incr(key)
        # Set expiration for the lockout counter
        await cache_service.expire(key, int(self.lockout_duration.total_seconds()))
        return attempts
    
    async def reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts counter"""
        key = f"lockout:{user_id}"
        await cache_service.delete(key)
    
    async def is_account_locked(self, user_id: str) -> bool:
        """Check if account is currently locked"""
        attempts = await self.get_failed_attempts(user_id)
        return attempts >= self.max_failed_attempts
    
    async def check_and_handle_lockout(self, user_id: str, db: AsyncSession) -> bool:
        """
        Check if account is locked and handle lockout logic
        Returns True if account is locked, False otherwise
        """
        if await self.is_account_locked(user_id):
            # Get user info for logging
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if user:
                logger.warning(f"Account locked for user: {user.username} (ID: {user_id})")
            return True
        
        return False
    
    async def record_failed_login(self, user_id: str):
        """Record a failed login attempt"""
        await self.increment_failed_attempts(user_id)
        logger.info(f"Failed login attempt recorded for user ID: {user_id}")
    
    async def handle_successful_login(self, user_id: str):
        """Reset failed attempts counter on successful login"""
        await self.reset_failed_attempts(user_id)
        logger.info(f"Failed login attempts reset for user ID: {user_id}")


# Global instance
account_lockout_service = AccountLockoutService()
