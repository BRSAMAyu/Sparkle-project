"""
Application Configuration Management
使用 pydantic-settings 管理配置
"""
import os
from urllib.parse import quote, urlparse, urlunparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # backend/app
project_root = os.path.dirname(backend_dir)  # backend
repo_root = os.path.dirname(project_root)  # repo root
repo_env_path = os.path.join(repo_root, ".env")
service_env_path = os.path.join(project_root, ".env")
backend_env_path = os.path.join(backend_dir, ".env")

def _is_running_in_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("IN_DOCKER") == "true"


def _normalize_local_docker_host(host: str) -> str:
    if _is_running_in_docker():
        return host
    if host in ("sparkle_db", "sparkle_redis"):
        return "127.0.0.1"
    return host


def _replace_url_host(raw_url: str, new_host: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.hostname:
        return raw_url
    username = quote(parsed.username) if parsed.username else ""
    password = quote(parsed.password) if parsed.password else ""
    auth = ""
    if username:
        auth = username
        if password:
            auth = f"{username}:{password}"
        auth = f"{auth}@"
    elif password:
        auth = f":{password}@"
    port = f":{parsed.port}" if parsed.port else ""
    new_netloc = f"{auth}{new_host}{port}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def normalize_database_url(raw_url: str, *, prefer_async: bool = True) -> str:
    if not raw_url:
        return ""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if prefer_async:
        for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
            if url.startswith(prefix):
                url = "postgresql+asyncpg://" + url[len(prefix):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    host = urlparse(url).hostname
    if host:
        url = _replace_url_host(url, _normalize_local_docker_host(host))
    return url


def to_sync_database_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    url = raw_url.strip()
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://"):]
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://"):]
    if url.startswith("postgresql+psycopg2://"):
        url = "postgresql://" + url[len("postgresql+psycopg2://"):]
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def normalize_redis_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    url = raw_url.strip()
    host = urlparse(url).hostname
    if host:
        url = _replace_url_host(url, _normalize_local_docker_host(host))
    return url

class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(
        # Load repo root .env first, then backend/.env, then backend/app/.env
        env_file=[repo_env_path, service_env_path, backend_env_path],
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Sparkle"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool | None = None

    # Security
    # Support JWT_SECRET as alias for SECRET_KEY to align with Gateway/Go convention
    SECRET_KEY: str = Field("", validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"))
    JWT_ISSUER: str = "sparkle-gateway"
    JWT_AUDIENCE: str = "sparkle-app"

    # Database (canonical envs: POSTGRES_*)
    DATABASE_URL: str = ""
    POSTGRES_HOST: str = Field("sparkle_db", validation_alias=AliasChoices("POSTGRES_HOST", "DB_HOST"))
    POSTGRES_PORT: int = Field(5432, validation_alias=AliasChoices("POSTGRES_PORT", "DB_PORT"))
    POSTGRES_USER: str = Field("postgres", validation_alias=AliasChoices("POSTGRES_USER", "DB_USER"))
    POSTGRES_PASSWORD: str = Field("change-me", validation_alias=AliasChoices("POSTGRES_PASSWORD", "DB_PASSWORD"))
    POSTGRES_DB: str = Field("sparkle", validation_alias=AliasChoices("POSTGRES_DB", "DB_NAME"))

    # Redis (canonical envs: REDIS_*)
    REDIS_URL: str = ""
    REDIS_HOST: str = Field("sparkle_redis", validation_alias=AliasChoices("REDIS_HOST", "REDIS_HOSTNAME"))
    REDIS_PORT: int = Field(6379, validation_alias=AliasChoices("REDIS_PORT", "REDIS_PORT_NUMBER"))
    REDIS_PASSWORD: str = "change-me"
    REDIS_DB: int = 0

    @property
    def DB_HOST(self) -> str:
        return _normalize_local_docker_host(self.POSTGRES_HOST)

    @property
    def DB_PORT(self) -> int:
        return self.POSTGRES_PORT

    @property
    def DB_USER(self) -> str:
        return self.POSTGRES_USER

    @property
    def DB_PASSWORD(self) -> str:
        return self.POSTGRES_PASSWORD

    @property
    def DB_NAME(self) -> str:
        return self.POSTGRES_DB

    # Database Pool Settings (for PostgreSQL)
    DB_POOL_SIZE: int = 20  # 连接池大小
    DB_MAX_OVERFLOW: int = 40  # 最大溢出连接数
    DB_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）
    DB_POOL_TIMEOUT: int = 30  # 获取连接超时时间（秒）
    DB_ECHO: bool = False  # 是否打印SQL语句（生产环境应为False）

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = []

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
    WS_ALLOW_QUERY_TOKEN: bool | None = None

    # WeChat Configuration
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # LLM Service
    LLM_API_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "qwen-plus"
    LLM_REASON_MODEL_NAME: str = "deepseek-reasoner"
    LLM_PROVIDER: str = "xiaomi"  # 'xiaomi' | 'deepseek' | 'zhipu' | 'qwen' | 'openai' | 'hunyuan'
    # LLM Tier Routing (comma-separated model keys from LLMRouter)
    LLM_TIER_FREE_FAST: str = ""
    LLM_TIER_FREE_REASONING: str = ""
    LLM_TIER_FAST: str = ""
    LLM_TIER_STANDARD: str = ""
    LLM_TIER_REASONING: str = ""
    LLM_TIER_SPECIALIST: str = ""

    # XiaoMi MIMO Configuration (快速响应)
    XIAOMI_MIMO_API_KEY: str = ""
    XIAOMI_MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    XIAOMI_CHAT_MODEL: str = "mimo-v2-flash"
    XIAOMI_TEMPERATURE: float = 0.3

    # DeepSeek Configuration (核心模型 - 思考模式)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASON_MODEL: str = "deepseek-reasoner"

    # Zhipu GLM Configuration (编程/工具调用)
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_CHAT_MODEL: str = "glm-4.7"
    ZHIPU_TOOLS_MODEL: str = "glm-4.7"
    ZHIPU_FLASH_MODEL: str = "glm-4.7-flashx"  # 快速响应模型 (FlashX)
    GLM_4_7_FLASH_MODEL: str = "glm-4.7-flash"  # GLM-4.7-Flash 模型（支持思考模式）
    ZHIPU_TEMPERATURE: float = 0.3

    # SiliconFlow API
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_OCR_MODEL: str = "deepseek-ai/DeepSeek-OCR"

    # Translation Service (via SiliconFlow)
    # Uses Hunyuan-MT-7B (Machine Translation model) for best translation quality
    # Falls back to SILICONFLOW_API_KEY if HUNYUAN_API_KEY is not set
    HUNYUAN_API_KEY: str = ""  # Optional: overrides SILICONFLOW_API_KEY for translation
    HUNYUAN_BASE_URL: str = "https://api.siliconflow.cn/v1"
    HUNYUAN_TRANSLATE_MODEL: str = "tencent/Hunyuan-MT-7B"  # Translation-specific model

    # Embedding Service
    EMBEDDING_PROVIDER: str = "dashscope"  # dashscope | siliconflow
    EMBEDDING_MODEL: str = "text-embedding-v4"  # 向量模型
    EMBEDDING_DIM: int = 1024  # 向量维度
    RERANK_PROVIDER: str = "dashscope"  # dashscope | siliconflow
    RERANK_MODEL: str = "qwen3-rerank"  # 重排序模型

    # DashScope (Aliyun)
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_HTTP_API_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    DASHSCOPE_BASE_URL_COMPATIBLE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_CHAT_MODEL: str = "qwen-plus"
    DASHSCOPE_REASON_MODEL: str = "qwen-plus"
    DASHSCOPE_TEMPERATURE: float = 0.7
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v4"
    DASHSCOPE_RERANK_MODEL: str = "qwen3-rerank"

    # SiliconFlow (Embedding/Rerank)
    SILICONFLOW_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-4B"
    SILICONFLOW_RERANK_MODEL: str = "Qwen/Qwen3-Reranker-4B"

    # STT (Speech to Text) Service
    STT_PROVIDER: str = "xunfei"  # 仅支持 'xunfei'
    STT_ENHANCE_ENABLED: bool = True  # 是否启用LLM后处理增强

    # XunFei (科大讯飞) STT Configuration
    XUNFEI_APP_ID: str = ""
    XUNFEI_API_KEY: str = ""
    XUNFEI_API_SECRET: str = ""
    XUNFEI_STT_DOMAIN: str = "slm"
    XUNFEI_STT_LANGUAGE: str = "zh-CN"
    XUNFEI_STT_SAMPLE_RATE: int = 16000
    XUNFEI_STT_MAX_AUDIO_DURATION: int = 60
    XUNFEI_STT_EOS_MS: int = 6000  # 静音检测阈值（毫秒）

    # Semantic Cache
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_SIM_THRESHOLD: float = 0.9
    SEMANTIC_CACHE_MAX_CANDIDATES: int = 200
    KNOWLEDGE_VERSION_CACHE_TTL_SECONDS: int = 30
    FEEDBACK_EFFECT_TTL_SECONDS: int = 604800

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

    # Next Step Recommendation Settings
    NEXT_STEP_FATIGUE_HIGH_THRESHOLD: float = 1.5  # 高疲劳阈值
    NEXT_STEP_FATIGUE_EXTREME_THRESHOLD: float = 2.0  # 极度疲劳阈值
    NEXT_STEP_MAX_RECOMMENDATIONS: int = 3  # 最多推荐数量
    NEXT_STEP_DEFAULT_DURATION: int = 15  # 默认推荐时长
    NEXT_STEP_DEFAULT_ENERGY: int = 2  # 默认精力消耗

    # Feature Flags
    USE_CONTEXT_PACK: bool = True
    ANALYSIS_SYNC_ON_EVENT: bool = True
    ENABLE_EVIDENCE_HEALTH_JOB: bool = True
    ENABLE_BEHAVIOR_DECAY: bool = True
    ENABLE_MEMORY_RETRACTION: bool = True
    USE_CONTEXT_INTENT_ROUTER: bool = True
    ENABLE_MEMORY_PANEL: bool = True
    ENABLE_MEMORY_GOVERNANCE: bool = True
    ENABLE_MEMORY_EXPORT: bool = True
    ENABLE_MEMORY_CORRECTION: bool = True
    ENABLE_LTM_EVAL: bool = True
    LTM_EVAL_DATASET_PATH: str = "backend/tests/fixtures/ltm_eval_sample.jsonl"
    LTM_EVAL_FAIL_THRESHOLD: float = 0.6
    ENABLE_CONTEXT_PACK_TELEMETRY: bool = True
    ENABLE_BUDGET_TUNING: bool = True
    CONTEXT_PACK_FEEDBACK_WINDOW_MINUTES: int = 10
    ENABLE_CONTEXT_RANKING: bool = True
    CONTEXT_RANKING_SOFT_CAP_EPISODIC: int = 6
    CONTEXT_RANKING_SOFT_CAP_GOALS: int = 5
    ENABLE_MEMORY_CONFLICT_RESOLUTION: bool = True
    ENABLE_PERSONALIZED_RANKING: bool = True
    MEMORY_RANK_DEFAULT_EVIDENCE: float = 0.6
    MEMORY_RANK_DEFAULT_FRESHNESS: float = 0.3
    MEMORY_RANK_DEFAULT_CORRECTION: float = 0.1
    ENABLE_USER_MEMORY_CONTROLS: bool = True
    ENABLE_MEMORY_JOBS: bool = True
    ENABLE_EVIDENCE_SNAPSHOT_ON_WRITE: bool = True
    ENABLE_MEMORY_DECAY: bool = True
    ENABLE_LTM_ROLLOUT: bool = True
    LTM_ROLLOUT_PERCENT: int = 100
    LTM_ROLLOUT_USER_ALLOWLIST: list[str] = []
    LTM_ROLLOUT_COHORT_TAGS: list[str] = []
    LTM_RELEASE_EVIDENCE_MISSING_THRESHOLD: float = 0.1
    LTM_RELEASE_EVAL_THRESHOLD: float = 0.6
    LTM_RELEASE_JOB_SUCCESS_THRESHOLD: float = 0.9
    LTM_RELEASE_BUDGET_MULTIPLIER_MIN: float = 0.7
    LTM_RELEASE_BUDGET_MULTIPLIER_MAX: float = 1.3
    ENABLE_MEMORY_DAILY_SUMMARY: bool = True
    ENABLE_MEMORY_HEALTH_SNAPSHOT: bool = True
    ENABLE_GRAPHRAG_FASTPATH: bool = False
    GRAPHRAG_CACHE_TTL_SECONDS: int = 120
    GRAPHRAG_FASTPATH_TIMEOUT_SECONDS: float = 2.5
    ENABLE_GRAPHRAG_MONITOR_API: bool = False
    GRAPHRAG_TRACE_TTL_SECONDS: int = 86400
    GRAPHRAG_TRACE_MAX_BYTES: int = 20000
    GRAPHRAG_TRACE_QUERY_MAX_CHARS: int = 256
    ENABLE_GRAPHRAG_TRACE_PII: bool = False
    REDIS_HYBRID_TIMEOUT_SECONDS: float = 2.0
    RERANK_TIMEOUT_SECONDS: float = 2.5
    ENABLE_REDIS_HYBRID_FALLBACK: bool = False

    # Transparency System (透明模式)
    TRANSPARENCY_MODE_ENABLED: bool = True  # Global transparency mode toggle
    TRANSPARENCY_MODE_DEFAULT: bool = False  # Default user preference
    TRANSPARENCY_SHOW_TOKEN_USAGE: bool = True  # Show token usage in transparency panel
    TRANSPARENCY_SHOW_AGENT_SWITCHING: bool = True  # Show agent switching
    TRANSPARENCY_SHOW_REASONING_STEPS: bool = True  # Show LLM reasoning steps
    TRANSPARENCY_STEP_DEBOUNCE_MS: int = 100  # Minimum time between step updates

    # Plan Quota Settings (并行计划数限制)
    PLAN_QUOTA_DEFAULT: int = 3           # 免费用户默认3个活跃计划
    PLAN_QUOTA_PREMIUM: int = 10          # 付费用户10个活跃计划
    PLAN_QUOTA_UNLIMITED: int = -1        # 无限制 (特殊用户)

    # Event Retention
    EVENT_RETENTION_DAYS: int = 30
    STATE_RETENTION_DAYS: int = 30

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # MDX Dictionary Configuration
    MDX_DICTIONARY_ENABLED: bool = True
    MDX_DICTIONARY_PATH: str = ""
    MDD_RESOURCES_PATH: str | None = None

    # Internal API
    INTERNAL_API_KEY: str = ""
    GATEWAY_INTERNAL_URL: str = ""

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

    # Translation Service
    TRANSLATION_DAILY_CARD_LIMIT: int = 20  # Max vocabulary cards created per day from translation

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
        return normalize_database_url(v)

    @field_validator("LLM_API_BASE_URL", mode="before")
    @classmethod
    def validate_llm_api_base_url(cls, v):
        if not v:
            return ""
        return v

    @model_validator(mode="after")
    def finalize_urls(self):
        if not self.DATABASE_URL:
            host = _normalize_local_docker_host(self.POSTGRES_HOST)
            self.DATABASE_URL = normalize_database_url(
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            self.DATABASE_URL = normalize_database_url(self.DATABASE_URL)

        if self.REDIS_URL:
            self.REDIS_URL = normalize_redis_url(self.REDIS_URL)
        else:
            host = _normalize_local_docker_host(self.REDIS_HOST)
            self.REDIS_URL = normalize_redis_url(
                f"redis://:{self.REDIS_PASSWORD}@{host}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return self

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

    @field_validator("XUNFEI_API_KEY", mode="before")
    @classmethod
    def validate_xunfei_api_key(cls, v):
        if not v:
            return ""
        return v

    @field_validator("XUNFEI_APP_ID", mode="before")
    @classmethod
    def validate_xunfei_app_id(cls, v):
        if not v:
            return ""
        return v

    @field_validator("XUNFEI_API_SECRET", mode="before")
    @classmethod
    def validate_xunfei_api_secret(cls, v):
        if not v:
            return ""
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

        if env in ("prod", "production") and "*" in self.BACKEND_CORS_ORIGINS:
            raise ValueError("BACKEND_CORS_ORIGINS cannot include '*' in production")

        if self.WS_ALLOW_QUERY_TOKEN is None:
            self.WS_ALLOW_QUERY_TOKEN = env not in ("prod", "production")

        if self.GRPC_REQUIRE_TLS and (not self.GRPC_TLS_CERT_PATH or not self.GRPC_TLS_KEY_PATH):
            raise ValueError("GRPC TLS is required but cert/key are not configured")

        return self


# Create global settings instance
settings = Settings()
