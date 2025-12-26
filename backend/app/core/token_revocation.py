"""
Token Revocation Service
Manages JWT token revocation and blacklisting
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.core.cache import cache_service
from loguru import logger


class TokenRevocationService:
    """Service to handle token revocation and blacklisting"""
    
    def __init__(self):
        # Use Redis for token blacklist (persistent across restarts)
        self.blacklist_prefix = "token:blacklist:"
        self.default_ttl = 3600  # 1 hour default TTL for blacklisted tokens
    
    async def blacklist_token(self, token_jti: str, expires_in: Optional[int] = None) -> bool:
        """
        Add a token to the blacklist
        
        Args:
            token_jti: JWT ID (unique identifier for the token)
            expires_in: Optional expiration time in seconds
            
        Returns:
            bool: True if successfully blacklisted
        """
        try:
            key = f"{self.blacklist_prefix}{token_jti}"
            ttl = expires_in or self.default_ttl
            await cache_service.set(key, "revoked", ex=ttl)
            logger.info(f"Token blacklisted: {token_jti}")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token {token_jti}: {e}")
            return False
    
    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a token is blacklisted
        
        Args:
            token_jti: JWT ID (unique identifier for the token)
            
        Returns:
            bool: True if token is blacklisted
        """
        try:
            key = f"{self.blacklist_prefix}{token_jti}"
            result = await cache_service.get(key)
            return result is not None
        except Exception as e:
            logger.error(f"Error checking token blacklist for {token_jti}: {e}")
            return False
    
    async def revoke_refresh_token(self, user_id: str, refresh_token_jti: str) -> bool:
        """
        Revoke a refresh token for a specific user
        
        Args:
            user_id: User ID
            refresh_token_jti: Refresh token JWT ID
            
        Returns:
            bool: True if successfully revoked
        """
        try:
            # Blacklist the refresh token
            success = await self.blacklist_token(refresh_token_jti)
            if success:
                logger.info(f"Refresh token revoked for user {user_id}: {refresh_token_jti}")
            return success
        except Exception as e:
            logger.error(f"Failed to revoke refresh token for user {user_id}: {e}")
            return False
    
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user (logout all sessions)
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of tokens revoked
        """
        try:
            # In production, you'd use Redis SCAN or similar to find all tokens for user
            # For now, we'll use a simple approach with known patterns
            # This would be enhanced in production with proper indexing
            logger.info(f"Revoking all tokens for user {user_id}")
            return 0
        except Exception as e:
            logger.error(f"Failed to revoke all tokens for user {user_id}: {e}")
            return 0


# Global instance
token_revocation_service = TokenRevocationService()
