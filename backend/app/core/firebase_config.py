"""
Firebase Admin SDK Configuration

Initializes Firebase Admin SDK for Cloud Messaging (FCM) push notifications.
Supports both FCM (Android/Web) and APNs (iOS) through Firebase.
"""
from functools import lru_cache
from typing import Any

from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings


class FirebaseSettings(BaseSettings):
    """Firebase configuration from environment variables"""

    # Firebase Project Configuration
    FIREBASE_PROJECT_ID: str | None = Field(default=None, env="FIREBASE_PROJECT_ID")
    FIREBASE_PRIVATE_KEY: str | None = Field(default=None, env="FIREBASE_PRIVATE_KEY")
    FIREBASE_CLIENT_EMAIL: str | None = Field(default=None, env="FIREBASE_CLIENT_EMAIL")
    FIREBASE_STORAGE_BUCKET: str | None = Field(default=None, env="FIREBASE_STORAGE_BUCKET")

    # Alternative: Path to service account JSON file
    FIREBASE_CREDENTIALS_PATH: str | None = Field(
        default=None, env="FIREBASE_CREDENTIALS_PATH"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def is_configured(self) -> bool:
        """Check if Firebase is properly configured"""
        # Either credentials path or all three fields must be set
        if self.FIREBASE_CREDENTIALS_PATH:
            return True
        return bool(
            self.FIREBASE_PROJECT_ID
            and self.FIREBASE_PRIVATE_KEY
            and self.FIREBASE_CLIENT_EMAIL
        )

    def get_credentials_dict(self) -> dict[str, Any] | None:
        """Get credentials as a dictionary for Firebase Admin SDK"""
        if not self.is_configured():
            return None

        if self.FIREBASE_CREDENTIALS_PATH:
            import json

            try:
                with open(self.FIREBASE_CREDENTIALS_PATH, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load Firebase credentials from file: {e}")
                return None

        # Build credentials from individual fields
        private_key = self.FIREBASE_PRIVATE_KEY
        if private_key:
            # Handle escaped newlines in environment variable
            private_key = private_key.replace("\\n", "\n")

        return {
            "type": "service_account",
            "project_id": self.FIREBASE_PROJECT_ID,
            "private_key_id": None,  # Optional
            "private_key": private_key,
            "client_email": self.FIREBASE_CLIENT_EMAIL,
            "client_id": None,  # Optional
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": None,  # Optional
            "universe_domain": "googleapis.com",
        }


# Global Firebase app instance
_firebase_app: Any = None
_firebase_initialized: bool = False


def initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK.

    Returns:
        True if initialization was successful, False otherwise
    """
    global _firebase_app, _firebase_initialized

    if _firebase_initialized:
        return _firebase_app is not None

    _firebase_initialized = True

    try:
        import firebase_admin
        from firebase_admin import credentials

        settings = FirebaseSettings()

        if not settings.is_configured():
            logger.warning(
                "Firebase not configured. Set FIREBASE_CREDENTIALS_PATH or "
                "FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL "
                "environment variables to enable push notifications."
            )
            return False

        cred_dict = settings.get_credentials_dict()
        if not cred_dict:
            logger.error("Failed to build Firebase credentials")
            return False

        cred = credentials.Certificate(cred_dict)

        # Check if already initialized
        try:
            _firebase_app = firebase_admin.get_app()
            logger.info("Firebase app already initialized")
        except ValueError:
            # Not initialized, create new app
            _firebase_app = firebase_admin.initialize_app(
                cred,
                {
                    "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
                },
            )
            logger.info(
                f"Firebase Admin SDK initialized for project: {settings.FIREBASE_PROJECT_ID}"
            )

        return True

    except ImportError:
        logger.warning(
            "firebase-admin not installed. Install with: pip install firebase-admin"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return False


@lru_cache
def get_firebase_app() -> Any:
    """
    Get the Firebase app instance.

    Returns:
        Firebase app instance or None if not initialized
    """
    if not _firebase_initialized:
        initialize_firebase()
    return _firebase_app


def is_firebase_available() -> bool:
    """Check if Firebase is available and initialized"""
    return get_firebase_app() is not None


# Convenience function to get settings
def get_firebase_settings() -> FirebaseSettings:
    """Get Firebase settings instance"""
    return FirebaseSettings()
