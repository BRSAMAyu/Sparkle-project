"""
JPush (极光推送) Configuration

Initializes JPush SDK for push notifications targeting Chinese domestic users.
Provides an alternative to FCM for users in mainland China where Google services
are not available.

JPush REST API v3: https://docs.jiguang.cn/jpush/server/push/rest_api_v3_push
"""
from functools import lru_cache
from typing import Literal

from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings


class JPushSettings(BaseSettings):
    """JPush configuration from environment variables"""

    # JPush Application Credentials
    JPUSH_APP_KEY: str | None = Field(default=None, env="JPUSH_APP_KEY")
    JPUSH_MASTER_SECRET: str | None = Field(default=None, env="JPUSH_MASTER_SECRET")

    # JPush Region: cn (default), us, sg (Singapore)
    JPUSH_REGION: Literal["cn", "us", "sg"] = Field(default="cn", env="JPUSH_REGION")

    # Enable/Disable JPush
    JPUSH_ENABLED: bool = Field(default=True, env="JPUSH_ENABLED")

    # API endpoints for different regions
    JPUSH_API_URL: str = Field(default="", env="JPUSH_API_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def is_configured(self) -> bool:
        """Check if JPush is properly configured"""
        if not self.JPUSH_ENABLED:
            return False
        return bool(self.JPUSH_APP_KEY and self.JPUSH_MASTER_SECRET)

    def get_api_url(self) -> str:
        """Get the API URL based on region"""
        if self.JPUSH_API_URL:
            return self.JPUSH_API_URL

        region_urls = {
            "cn": "https://api.jpush.cn/v3",
            "us": "https://api.jpush.cn/v3",  # US uses same endpoint
            "sg": "https://api.jpush.cn/v3",  # Singapore uses same endpoint
        }
        return region_urls.get(self.JPUSH_REGION, "https://api.jpush.cn/v3")

    def get_auth_string(self) -> str | None:
        """Get the basic auth string for JPush API"""
        if not self.is_configured():
            return None

        import base64

        auth_str = f"{self.JPUSH_APP_KEY}:{self.JPUSH_MASTER_SECRET}"
        return base64.b64encode(auth_str.encode()).decode()


# Global JPush status
_jpush_initialized: bool = False
_jpush_available: bool = False


def initialize_jpush() -> bool:
    """
    Initialize JPush SDK.

    Returns:
        True if initialization was successful, False otherwise
    """
    global _jpush_initialized, _jpush_available

    if _jpush_initialized:
        return _jpush_available

    _jpush_initialized = True

    try:
        settings = JPushSettings()

        if not settings.JPUSH_ENABLED:
            logger.info("JPush is disabled via JPUSH_ENABLED=false")
            return False

        if not settings.is_configured():
            logger.warning(
                "JPush not configured. Set JPUSH_APP_KEY and JPUSH_MASTER_SECRET "
                "environment variables to enable JPush notifications."
            )
            return False

        # JPush uses REST API, so no SDK initialization needed
        # Just verify credentials are present
        _jpush_available = True
        logger.info(
            f"JPush configured successfully. Region: {settings.JPUSH_REGION}, "
            f"AppKey: {settings.JPUSH_APP_KEY[:8]}..."
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize JPush: {e}")
        return False


@lru_cache
def get_jpush_settings() -> JPushSettings:
    """Get JPush settings instance"""
    return JPushSettings()


def is_jpush_available() -> bool:
    """Check if JPush is available and configured"""
    if not _jpush_initialized:
        initialize_jpush()
    return _jpush_available
