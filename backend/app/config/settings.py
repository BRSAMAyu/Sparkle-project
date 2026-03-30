"""
Application Configuration Management
使用 pydantic-settings 管理配置
"""

import json
import logging
import os
from typing import Dict, Optional, Union
from urllib.parse import quote, unquote, urlparse, urlunparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# 获取当前文件的绝对路径，并兼容本地源码结构与容器内 /app 结构。
current_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/config
app_dir = os.path.dirname(current_dir)  # .../app
project_root = os.path.dirname(app_dir)  # local: .../backend, container: /app
repo_root = os.path.dirname(project_root) if os.path.basename(project_root) == "backend" else project_root
repo_env_path = os.path.join(repo_root, ".env")
service_env_path = os.path.join(project_root, ".env")
backend_env_path = service_env_path


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
    # urlparse may return percent-encoded userinfo; decode first to avoid double encoding.
    username = quote(unquote(parsed.username)) if parsed.username else ""
    password = quote(unquote(parsed.password)) if parsed.password else ""
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
        url = "postgresql://" + url[len("postgres://") :]
    if prefer_async:
        for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
            if url.startswith(prefix):
                url = "postgresql+asyncpg://" + url[len(prefix) :]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    host = urlparse(url).hostname
    if host:
        url = _replace_url_host(url, _normalize_local_docker_host(host))
    return url


def to_sync_database_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    url = raw_url.strip()
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://") :]
    if url.startswith("postgresql+psycopg2://"):
        url = "postgresql://" + url[len("postgresql+psycopg2://") :]
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def _normalize_local_path(raw_path: str | None, *, base_dir: str) -> str:
    if not raw_path:
        return ""
    expanded = os.path.expanduser(raw_path.strip())
    if os.path.isabs(expanded):
        return os.path.abspath(expanded)
    return os.path.abspath(os.path.join(base_dir, expanded))


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
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Sparkle"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: Optional[bool] = None
    SERVICE_ROLE: str = "api"  # api | grpc

    # Security
    # Prefer JWT_SECRET to keep Python-issued JWT fully compatible with Gateway verification.
    SECRET_KEY: str = Field("", validation_alias=AliasChoices("JWT_SECRET", "SECRET_KEY"))
    JWT_ISSUER: str = "sparkle-gateway"
    JWT_AUDIENCE: str = "sparkle-app"

    # Community Settings
    MESSAGE_REVOKE_TIME_LIMIT_SECONDS: int = 120  # 消息撤回时间限制（秒），默认2分钟
    MESSAGE_SEND_MAX_RETRIES: int = 3  # 消息发送最大重试次数

    # Database (canonical envs: POSTGRES_*)
    DATABASE_URL: str = ""
    POSTGRES_HOST: str = Field("sparkle_db", validation_alias=AliasChoices("POSTGRES_HOST", "DB_HOST"))
    POSTGRES_PORT: int = Field(5432, validation_alias=AliasChoices("POSTGRES_PORT", "DB_PORT"))
    POSTGRES_USER: str = Field("postgres", validation_alias=AliasChoices("POSTGRES_USER", "DB_USER"))
    POSTGRES_PASSWORD: str = Field("", validation_alias=AliasChoices("POSTGRES_PASSWORD", "DB_PASSWORD"))
    POSTGRES_DB: str = Field("sparkle", validation_alias=AliasChoices("POSTGRES_DB", "DB_NAME"))

    # Redis (canonical envs: REDIS_*)
    REDIS_URL: str = ""
    REDIS_HOST: str = Field("sparkle_redis", validation_alias=AliasChoices("REDIS_HOST", "REDIS_HOSTNAME"))
    REDIS_PORT: int = Field(6379, validation_alias=AliasChoices("REDIS_PORT", "REDIS_PORT_NUMBER"))
    REDIS_PASSWORD: str = ""
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
    WS_ALLOW_QUERY_TOKEN: Optional[bool] = None

    # OpenClaw Integration
    OPENCLAW_ENABLED: bool = False
    OPENCLAW_GATEWAY_URL: str = ""
    OPENCLAW_AUTH_TOKEN: str = ""
    OPENCLAW_DEFAULT_AGENT_ID: str = ""
    OPENCLAW_TRANSPORT: str = "responses_http"  # responses_http | gateway_ws
    OPENCLAW_WS_URL: str = ""
    OPENCLAW_WS_PROTOCOL_VERSION: int = 3
    OPENCLAW_WS_WAIT_TIMEOUT_MS: int = 30000
    OPENCLAW_WS_ALLOW_INSECURE_AUTH: bool = False
    OPENCLAW_WS_DEVICE_TOKEN: str = ""
    OPENCLAW_WS_DEVICE_IDENTITY_PATH: str = ""
    OPENCLAW_WS_CLIENT_ID: str = "sparkle-backend"
    OPENCLAW_DEFAULT_TIMEOUT_SECONDS: int = 300
    OPENCLAW_MAX_CONCURRENT_RUNS: int = 3
    OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY: int = 5
    OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE: float = 0.85

    # Email (SMTP)
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "Sparkle"

    # WeChat Configuration
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # LLM Service
    LLM_API_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "qwen-plus"
    LLM_REASON_MODEL_NAME: str = "deepseek-reasoner"
    LLM_PROVIDER: str = "xiaomi"  # 'xiaomi' | 'deepseek' | 'zhipu' | 'qwen' | 'openai' | 'hunyuan'
    LLM_QUOTA_ENABLED: bool = False  # Disable token quota checks by default for demo recording
    AI_MODE_FAST_DAILY_REQUEST_LIMIT: int = 120
    AI_MODE_BALANCED_DAILY_REQUEST_LIMIT: int = 60
    AI_MODE_DEEP_DAILY_REQUEST_LIMIT: int = 24
    AI_PREDICTION_FREE_TIMEOUT_SECONDS: float = 1.5
    AI_PREDICTION_FREE_FAST_TIMEOUT_SECONDS: float = 2.5
    FRONTEND_TELEMETRY_ENABLED: bool = True
    FRONTEND_TELEMETRY_SAMPLE_RATE: float = 1.0
    PRODUCTION_BACKUP_DIR: str = "./backups"
    # LLM Tier Routing (comma-separated model keys from LLMRouter)
    LLM_TIER_FREE: str = ""
    LLM_TIER_FREE_FAST: str = ""
    LLM_TIER_FREE_REASONING: str = ""
    LLM_TIER_FAST: str = ""
    LLM_TIER_STANDARD: str = ""
    LLM_TIER_PLUS: str = ""
    LLM_TIER_PRO: str = ""
    LLM_TIER_REASONING: str = ""
    LLM_TIER_MAX: str = ""
    LLM_TIER_GLM_BATCH: str = ""
    LLM_TIER_SPECIALIST: str = ""

    # XiaoMi MIMO Configuration (快速响应)
    XIAOMI_MIMO_API_KEY: str = ""
    XIAOMI_MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    XIAOMI_CHAT_MODEL: str = "mimo-v2-flash"
    XIAOMI_STANDARD_MODEL: str = "mimo-v2-flash"
    XIAOMI_TEMPERATURE: float = 0.3

    # Prompt Snapshot (debug observability)
    PROMPT_SNAPSHOT_ENABLED: bool = False
    PROMPT_SNAPSHOT_SAMPLE_RATE: float = 0.0
    PROMPT_SNAPSHOT_MAX_CHARS: int = 1200

    # DeepSeek Configuration (核心模型 - 思考模式)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-chat"
    DEEPSEEK_REASON_MODEL: str = "deepseek-reasoner"

    # Zhipu GLM Configuration (编程/工具调用)
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_CODING_BASE_URL: str = "https://open.bigmodel.cn/api/coding/paas/v4"
    ZHIPU_CHAT_MODEL: str = "glm-4.7"
    ZHIPU_TOOLS_MODEL: str = "glm-4.7"
    ZHIPU_FLASH_MODEL: str = "glm-4.7-flashx"  # 快速响应模型 (FlashX)
    GLM_4_7_FLASH_MODEL: str = "glm-4.7-flash"  # GLM-4.7-Flash 模型（支持思考模式）
    ZHIPU_AIR_MODEL: str = "glm-4.5-air"
    ZHIPU_LIGHT_MODEL: str = "glm-4.6"
    ZHIPU_MAX_MODEL: str = "glm-5"
    ZHIPU_TEMPERATURE: float = 0.3
    ZHIPU_OCR_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_OCR_MODEL: str = "glm-ocr"
    ZHIPU_OCR_TIMEOUT_SECONDS: int = 120

    # SiliconFlow API
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_FREE_MODEL: str = "Qwen/Qwen3.5-4B"
    SILICONFLOW_OCR_MODEL: str = "deepseek-ai/DeepSeek-OCR"
    SILICONFLOW_OCR_TIMEOUT_SECONDS: int = 120

    # Translation Service (via SiliconFlow)
    # Uses Hunyuan-MT-7B (Machine Translation model) for best translation quality
    # Falls back to SILICONFLOW_API_KEY if HUNYUAN_API_KEY is not set
    HUNYUAN_API_KEY: str = ""  # Optional: overrides SILICONFLOW_API_KEY for translation
    HUNYUAN_BASE_URL: str = "https://api.siliconflow.cn/v1"
    HUNYUAN_TRANSLATE_MODEL: str = "tencent/Hunyuan-MT-7B"  # Translation-specific model
    SILICONFLOW_TRANSLATE_MODEL: str = "tencent/Hunyuan-MT-7B"
    TRANSLATION_PRIMARY_PROVIDER: str = "hunyuan"  # hunyuan | siliconflow
    TRANSLATION_BACKUP_PROVIDER: str = "siliconflow"  # hunyuan | siliconflow
    TRANSLATION_PROVIDER_TIMEOUT_SECONDS: int = 30
    REVIEWER_LLM_TIMEOUT_SECONDS: int = 12

    # OCR / Document Cleaning
    OCR_PROVIDER: str = "zhipu"  # zhipu | siliconflow
    OCR_BACKUP_PROVIDER: str = "siliconflow"  # zhipu | siliconflow

    # Embedding Service
    EMBEDDING_PROVIDER: str = "dashscope"  # dashscope | siliconflow
    EMBEDDING_BACKUP_PROVIDER: str = "siliconflow"  # dashscope | siliconflow
    EMBEDDING_MODEL: str = "text-embedding-v4"  # 向量模型
    EMBEDDING_DIM: int = 1024  # 向量维度
    RERANK_PROVIDER: str = "dashscope"  # dashscope | siliconflow
    RERANK_BACKUP_PROVIDER: str = "siliconflow"  # dashscope | siliconflow
    RERANK_MODEL: str = "qwen3-rerank"  # 重排序模型

    # DashScope (Aliyun)
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_HTTP_API_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    DASHSCOPE_BASE_URL_COMPATIBLE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_CHAT_MODEL: str = "qwen3.5-plus"  # 标准/推理模型
    DASHSCOPE_REASON_MODEL: str = "qwen3.5-plus"
    DASHSCOPE_FAST_MODEL: str = "qwen3.5-flash"  # 快速响应模型
    DASHSCOPE_STANDARD_MODEL: str = "qwen3.5-flash"
    DASHSCOPE_TEMPERATURE: float = 0.7
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v4"
    DASHSCOPE_RERANK_MODEL: str = "qwen3-rerank"

    # SiliconFlow (Embedding/Rerank)
    SILICONFLOW_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-4B"
    SILICONFLOW_RERANK_MODEL: str = "Qwen/Qwen3-Reranker-4B"

    # STT (Speech to Text) Service
    STT_PROVIDER: str = "zhipu"  # zhipu
    STT_BACKUP_PROVIDER: str = "xunfei"  # xunfei | zhipu
    STT_ENHANCE_ENABLED: bool = True  # 是否启用LLM后处理增强

    # GLM Batch
    GLM_BATCH_ENABLED: bool = True
    GLM_BATCH_QUEUE: str = "glm_batch"
    GLM_BATCH_MIN_CONCURRENCY: int = 1
    GLM_BATCH_MAX_CONCURRENCY: int = 6
    GLM_BATCH_PEAK_START_HOUR: int = 14
    GLM_BATCH_PEAK_END_HOUR: int = 18
    GLM_BATCH_PEAK_CONCURRENCY: int = 2
    GLM_BATCH_OFFPEAK_DEFAULT_CONCURRENCY: int = 3
    GLM_BATCH_ADAPTIVE_ENABLED: bool = True
    GLM_BATCH_ADAPTIVE_SUCCESS_THRESHOLD: int = 8
    GLM_BATCH_ADAPTIVE_INCREASE_COOLDOWN_SECONDS: int = 180
    GLM_BATCH_ADAPTIVE_RATE_LIMIT_COOLDOWN_SECONDS: int = 300
    GLM_BATCH_SPILLOVER_ENABLED: bool = True
    GLM_BATCH_SPILLOVER_BACKLOG_FACTOR: int = 2
    GLM_BATCH_CAPSULES_ENABLED: bool = True
    GLM_BATCH_COGNITIVE_ANALYSIS_ENABLED: bool = True
    GLM_BATCH_THINKING_DEPTH_THRESHOLD: float = 0.72
    GLM_BATCH_THINKING_SEVERITY_THRESHOLD: int = 4

    # Zhipu ASR Configuration
    ZHIPU_ASR_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_ASR_MODEL: str = "glm-asr-2512"
    ZHIPU_ASR_SAMPLE_RATE: int = 16000
    ZHIPU_ASR_STREAM_SEGMENT_SECONDS: int = 4
    ZHIPU_ASR_MAX_AUDIO_SECONDS: int = 30
    ZHIPU_ASR_MAX_FILE_SIZE_BYTES: int = 26214400  # 25MB
    ZHIPU_ASR_REQUEST_TIMEOUT_SECONDS: int = 90

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

    # Complexity-Aware Routing (P3)
    COMPLEXITY_ROUTING_ENABLED: bool = True  # 总开关
    COMPLEXITY_DOWNGRADE_ENABLED: bool = True  # 允许简单消息降级到更便宜模型
    COMPLEXITY_UPGRADE_ENABLED: bool = True  # 允许复杂消息升级到更强模型
    STANDARD_CHAT_FORCE_FAST_TIER: bool = True  # 标准对话首答强制走 FAST/Flash 层
    FAST_INTERACTION_COPY_ENABLED: bool = True  # 澄清/确认文案优先由 FAST 模型生成
    EARLY_ACK_PROGRESS_ENABLED: bool = True  # 编排开始前先推送即时状态确认

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
    ENABLE_CONTEXT_FOCUSING: bool = False
    ENABLE_CONTEXT_SEMANTIC_GATING: bool = False
    ENABLE_CONTEXT_BRIEFING: bool = False
    ENABLE_CONTEXT_FOCUS_METADATA: bool = False
    CONTEXT_SEMANTIC_GATING_RULES_JSON: str = ""
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
    RUN_LEDGER_ENABLED: bool = True  # Unified control-tower ledger toggle
    RUN_LEDGER_STREAM_SNAPSHOTS: bool = True  # Stream live ledger snapshots to clients
    RUN_LEDGER_TTL_SECONDS: int = 86400  # 24h trace replay window in Redis

    # Plan Quota Settings (并行计划数限制)
    PLAN_QUOTA_DEFAULT: int = 3  # 免费用户默认3个活跃计划
    PLAN_QUOTA_PREMIUM: int = 10  # 付费用户10个活跃计划
    PLAN_QUOTA_UNLIMITED: int = -1  # 无限制 (特殊用户)

    # Event Retention
    EVENT_RETENTION_DAYS: int = 30
    STATE_RETENTION_DAYS: int = 30

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # MDX Dictionary Configuration
    MDX_DICTIONARY_ENABLED: bool = True
    MDX_DICTIONARY_PATH: str = ""
    MDD_RESOURCES_PATH: Optional[str] = None
    DICTIONARY_PACKAGE_DIR: str = "data/dictionaries/packages"
    DICTIONARY_PACKAGE_BASE_URL: str = ""

    # Internal API
    INTERNAL_API_KEY: str = ""
    GATEWAY_INTERNAL_URL: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Demo Mode (演示模式 - 用于竞赛演示，确保关键流程稳定)
    DEMO_MODE: bool = False  # 生产环境应设为 False

    # Optional Agent Graph V2
    ENABLE_AGENT_GRAPH_V2: bool = False
    ENABLE_MODE_WORKFLOW_V2: bool = True
    ENABLE_EXPERT_ENTRY: bool = True
    ENABLE_UNIFIED_GRAPH_ROUTING: bool = True
    ENABLE_EXPERT_STRATEGY_V1: bool = True
    ENABLE_SESSION_FEEDBACK_ADAPTATION: bool = False
    ENABLE_ADAPTIVE_PRESENTATION: bool = False
    ENABLE_STRUCTURED_NEXT_ACTIONS: bool = False
    ENABLE_BLOCKED_TEMPERATURE: bool = False
    ENABLE_UX_PRESENTATION_METADATA: bool = False
    ENABLE_PERCEPTIBLE_INTELLIGENCE: bool = False
    ENABLE_PROACTIVE_INSIGHTS: bool = False
    ENABLE_PLAN_REASONING_SUMMARY: bool = False
    ENABLE_WEEKLY_LEARNING_REPORT: bool = False
    ENABLE_PROGRESS_COMPARISONS: bool = False
    ENABLE_SUMMARIZATION_WORKER: bool = True
    ENABLE_AGENT_QUALITY_FEEDBACK: bool = True
    ENABLE_AGENT_LLM_COLLAB_ROUTING: bool = True
    AGENT_COMBINATION_EXPLORATION_RATE: float = 0.1

    # Optional Graph Sync Worker
    ENABLE_GRAPH_SYNC_WORKER: bool = False

    # Idempotency Store
    IDEMPOTENCY_STORE: str = "redis"  # 'memory' | 'redis' | 'database'

    # Event Bus reliability
    EVENT_BUS_MAX_RETRIES: int = 3
    EVENT_BUS_DLQ_SUFFIX: str = ":dlq"
    EVENT_BUS_STREAM_MAXLEN: int = 50000  # Soft cap for primary/retry Redis streams
    EVENT_BUS_RETRY_STREAM_MAXLEN: int = 50000  # Prevent retry storms from growing streams unbounded
    EVENT_BUS_DLQ_MAXLEN: int = 10000  # Maximum messages in DLQ before trimming

    # Translation Service
    TRANSLATION_DAILY_CARD_LIMIT: int = 20  # Max vocabulary cards created per day from translation

    # gRPC Server
    GRPC_PORT: int = 50051
    GRPC_ENABLE_REFLECTION: bool = False
    GRPC_REQUIRE_TLS: Optional[bool] = None
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

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def validate_upload_dir(cls, v):
        if not v:
            return _normalize_local_path("./uploads", base_dir=project_root)
        return _normalize_local_path(str(v), base_dir=project_root)

    @field_validator("MDX_DICTIONARY_PATH", mode="before")
    @classmethod
    def validate_mdx_dictionary_path(cls, v):
        if not v:
            return ""
        return _normalize_local_path(str(v), base_dir=repo_root)

    @field_validator("MDD_RESOURCES_PATH", mode="before")
    @classmethod
    def validate_mdd_resources_path(cls, v):
        if not v:
            return None
        return _normalize_local_path(str(v), base_dir=repo_root)

    @field_validator("DICTIONARY_PACKAGE_DIR", mode="before")
    @classmethod
    def validate_dictionary_package_dir(cls, v):
        if not v:
            return _normalize_local_path("data/dictionaries/packages", base_dir=repo_root)
        return _normalize_local_path(str(v), base_dir=repo_root)

    @property
    def CONTEXT_SEMANTIC_GATING_RULES(self) -> Dict[str, Dict[str, Union[float, int]]]:
        raw = str(self.CONTEXT_SEMANTIC_GATING_RULES_JSON or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

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
        service_role = (self.SERVICE_ROLE or "").strip().lower()
        if service_role == "":
            service_role = "api"
        self.SERVICE_ROLE = service_role

        if env in ("prod", "production") and self.DEBUG:
            raise ValueError("DEBUG must be disabled in production")

        if env in ("prod", "production") and self.SERVICE_ROLE == "grpc" and not self.GRPC_REQUIRE_TLS:
            raise ValueError("GRPC_REQUIRE_TLS must be enabled in production")

        # C6 Security Fix: 强制所有环境设置 SECRET_KEY
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be set in environment variables. "
                'Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

        # 最小长度警告（不阻止启动）
        if len(self.SECRET_KEY) < 32:
            logger.warning(
                f"SECRET_KEY is only {len(self.SECRET_KEY)} characters. "
                "Recommended minimum: 32 characters for production."
            )

        # 生产环境额外检查：禁止使用常见默认值
        if not self.DEBUG and self.SECRET_KEY in ["", "dev", "test", "secret", "changeme", "your-secret-key"]:
            raise ValueError("SECRET_KEY cannot be a default value in production")

        if env in ("prod", "production") and not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in production")

        if env in ("prod", "production") and "*" in self.BACKEND_CORS_ORIGINS:
            raise ValueError("BACKEND_CORS_ORIGINS cannot include '*' in production")

        if self.WS_ALLOW_QUERY_TOKEN is None:
            self.WS_ALLOW_QUERY_TOKEN = env not in ("prod", "production")

        if (
            self.SERVICE_ROLE == "grpc"
            and self.GRPC_REQUIRE_TLS
            and (not self.GRPC_TLS_CERT_PATH or not self.GRPC_TLS_KEY_PATH)
        ):
            raise ValueError("GRPC TLS is required but cert/key are not configured")

        self.GLM_BATCH_MIN_CONCURRENCY = max(1, int(self.GLM_BATCH_MIN_CONCURRENCY or 1))
        self.GLM_BATCH_MAX_CONCURRENCY = max(
            self.GLM_BATCH_MIN_CONCURRENCY,
            min(int(self.GLM_BATCH_MAX_CONCURRENCY or 6), 6),
        )
        self.GLM_BATCH_PEAK_CONCURRENCY = max(
            self.GLM_BATCH_MIN_CONCURRENCY,
            min(int(self.GLM_BATCH_PEAK_CONCURRENCY or 2), self.GLM_BATCH_MAX_CONCURRENCY),
        )
        self.GLM_BATCH_OFFPEAK_DEFAULT_CONCURRENCY = max(
            self.GLM_BATCH_PEAK_CONCURRENCY,
            min(int(self.GLM_BATCH_OFFPEAK_DEFAULT_CONCURRENCY or 3), self.GLM_BATCH_MAX_CONCURRENCY),
        )
        self.GLM_BATCH_ADAPTIVE_SUCCESS_THRESHOLD = max(1, int(self.GLM_BATCH_ADAPTIVE_SUCCESS_THRESHOLD or 8))
        self.GLM_BATCH_ADAPTIVE_INCREASE_COOLDOWN_SECONDS = max(
            30,
            int(self.GLM_BATCH_ADAPTIVE_INCREASE_COOLDOWN_SECONDS or 180),
        )
        self.GLM_BATCH_ADAPTIVE_RATE_LIMIT_COOLDOWN_SECONDS = max(
            30,
            int(self.GLM_BATCH_ADAPTIVE_RATE_LIMIT_COOLDOWN_SECONDS or 300),
        )
        self.GLM_BATCH_SPILLOVER_BACKLOG_FACTOR = max(1, int(self.GLM_BATCH_SPILLOVER_BACKLOG_FACTOR or 2))

        return self


# Create global settings instance
settings = Settings()
