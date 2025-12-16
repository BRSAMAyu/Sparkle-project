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

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
