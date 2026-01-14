"""
Application Configuration Management
使用 pydantic-settings 管理配置
"""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from dotenv import load_dotenv

# 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 假设 .env 在 backend 目录下，即 app 的父目录
env_path = os.path.join(os.path.dirname(current_dir), ".env")

# 不再显式加载 .env，交给 pydantic-settings 处理，以支持环境变量覆盖
# load_dotenv(env_path, override=True)

class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Sparkle"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool | None = None
    SECRET_KEY: str = ""

    # Database
    DATABASE_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = "devpassword"

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
    APPLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_ID: str = ""

    # LLM Service
    LLM_API_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "qwen-turbo"
    LLM_REASON_MODEL_NAME: str = "deepseek-reasoner"
    LLM_PROVIDER: str = "qwen"  # 'qwen' | 'deepseek' | 'openai'

    # DeepSeek Specific
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASON_MODEL: str = "deepseek-reasoner"

    # Embedding Service
    EMBEDDING_MODEL: str = "text-embedding-v2"  # 向量模型
    EMBEDDING_DIM: int = 1536  # 向量维度

    # Semantic Cache
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_SIM_THRESHOLD: float = 0.9
    SEMANTIC_CACHE_MAX_CANDIDATES: int = 200

    # Reranker
    RERANKER_ENABLED: bool = True

    # Expansion Feedback Loop
    EXPANSION_AB_TEST_ENABLED: bool = True
    EXPANSION_SEMANTIC_DEDUP_ENABLED: bool = True
    EXPANSION_SEMANTIC_DEDUP_THRESHOLD: float = 0.15

    # Intervention Phase 0
    INTERVENTION_REQUIRE_EVIDENCE: bool = True
    INTERVENTION_MIN_CONFIDENCE: float = 0.35
    INTERVENTION_DEFAULT_INTERRUPT_THRESHOLD: float = 0.5
    INTERVENTION_DEFAULT_DAILY_BUDGET: int = 3
    INTERVENTION_DEFAULT_COOLDOWN_MINUTES: int = 120
    INTERVENTION_QUIET_HOURS_START: str = "22:00"
    INTERVENTION_QUIET_HOURS_END: str = "07:00"
    INTERVENTION_BUDGET_TTL_SECONDS: int = 86400

    # Event Retention
    EVENT_RETENTION_DAYS: int = 30
    STATE_RETENTION_DAYS: int = 30

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # Internal API
    INTERNAL_API_KEY: str = ""
    GATEWAY_URL: str = "http://localhost:8080"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Demo Mode (演示模式 - 用于竞赛演示，确保关键流程稳定)
    DEMO_MODE: bool = False  # 生产环境应设为 False

    # Optional Agent Graph V2
    ENABLE_AGENT_GRAPH_V2: bool = False

    # Optional Graph Sync Worker
    ENABLE_GRAPH_SYNC_WORKER: bool = False

    # Idempotency Store
    IDEMPOTENCY_STORE: str = "memory"  # 'memory' | 'redis' | 'database'

    # gRPC Server
    GRPC_PORT: int = 50051
    GRPC_ENABLE_REFLECTION: bool = False
    GRPC_REQUIRE_TLS: bool | None = None
    GRPC_TLS_CERT_PATH: str = ""
    GRPC_TLS_KEY_PATH: str = ""

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v):
        if not v:
            return ""
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            return ""
        return v

    @field_validator("LLM_API_BASE_URL", mode="before")
    @classmethod
    def validate_llm_api_base_url(cls, v):
        if not v:
            return ""
        return v

    @field_validator("LLM_API_KEY", mode="before")
    @classmethod
    def validate_llm_api_key(cls, v):
        if not v:
            return ""
        return v

    @field_validator("DEEPSEEK_API_KEY", mode="before")
    @classmethod
    def validate_deepseek_api_key(cls, v):
        if not v:
            return ""
        return v

    @field_validator("DEEPSEEK_BASE_URL", mode="before")
    @classmethod
    def validate_deepseek_base_url(cls, v):
        if not v:
            return "https://api.deepseek.com"
        return v

    @model_validator(mode="after")
    def validate_security(self):
        env = (self.ENVIRONMENT or "").strip().lower()
        if env == "":
            env = "production"
        self.ENVIRONMENT = env
        if self.DEBUG is None:
            self.DEBUG = env not in ("prod", "production")

        if self.GRPC_REQUIRE_TLS is None:
            self.GRPC_REQUIRE_TLS = env in ("prod", "production")

        if env in ("prod", "production") and self.DEBUG:
            raise ValueError("DEBUG must be disabled in production")

        if env in ("prod", "production") and not self.GRPC_REQUIRE_TLS:
            raise ValueError("GRPC_REQUIRE_TLS must be enabled in production")

        if not self.DEBUG and not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set when DEBUG is false")

        if env in ("prod", "production") and not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in production")

        if env in ("prod", "production"):
            if not self.REDIS_PASSWORD or self.REDIS_PASSWORD == "devpassword":
                raise ValueError("REDIS_PASSWORD must be set to a non-default value in production")

        if env in ("prod", "production") and "*" in self.BACKEND_CORS_ORIGINS:
            raise ValueError("BACKEND_CORS_ORIGINS cannot include '*' in production")

        if self.GRPC_REQUIRE_TLS and (not self.GRPC_TLS_CERT_PATH or not self.GRPC_TLS_KEY_PATH):
            raise ValueError("GRPC TLS is required but cert/key are not configured")

        return self


# Create global settings instance
settings = Settings()
