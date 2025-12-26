"""
Application Configuration Management
使用 pydantic-settings 管理配置
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Sparkle"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Database Pool Settings (for PostgreSQL)
    DB_POOL_SIZE: int = 20  # 连接池大小
    DB_MAX_OVERFLOW: int = 40  # 最大溢出连接数
    DB_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）
    DB_POOL_TIMEOUT: int = 30  # 获取连接超时时间（秒）
    DB_ECHO: bool = False  # 是否打印SQL语句（生产环境应为False）

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # LLM Service
    LLM_API_BASE_URL: str
    LLM_API_KEY: str
    LLM_MODEL_NAME: str = "qwen-turbo"
    LLM_PROVIDER: str = "qwen"  # 'qwen' | 'deepseek' | 'openai'

    # Embedding Service
    EMBEDDING_MODEL: str = "text-embedding-v2"  # 向量模型
    EMBEDDING_DIM: int = 1536  # 向量维度

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB

    # Logging
    LOG_LEVEL: str = "INFO"

    # Demo Mode (演示模式 - 用于竞赛演示，确保关键流程稳定)
    DEMO_MODE: bool = False  # 生产环境应设为 False

    # Idempotency Store
    IDEMPOTENCY_STORE: str = "memory"  # 'memory' | 'redis' | 'database'

    # gRPC Server
    GRPC_PORT: int = 50051

    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY must be set in the environment variables.")
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL must be set in the environment variables.")
        return v

    @field_validator("LLM_API_BASE_URL", mode="before")
    @classmethod
    def validate_llm_api_base_url(cls, v):
        if not v:
            raise ValueError("LLM_API_BASE_URL must be set in the environment variables.")
        return v

    @field_validator("LLM_API_KEY", mode="before")
    @classmethod
    def validate_llm_api_key(cls, v):
        if not v:
            raise ValueError("LLM_API_KEY must be set in the environment variables.")
        return v


# Create global settings instance
settings = Settings()
