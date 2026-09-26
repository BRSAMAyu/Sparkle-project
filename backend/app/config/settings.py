"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Application Configuration Management
使用 pydantic-settings 管理配置
"""

import json
import logging
import os
from urllib.parse import quote, unquote, urlparse, urlunparse

from pydantic import AliasChoices, Field, PrivateAttr, field_validator, model_validator
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
    # 动态私有旋钮（kill-switch 服务运行期写入；PrivateAttr() 无默认=未写入即读仍抛 AttributeError，语义不变）
    _aurora_stage29_lag_points: list[str] = PrivateAttr()
    _aurora_stage29_misjudgment_days: list[str] = PrivateAttr()
    _aurora_traits_bias_streak: list[str] = PrivateAttr()
    _aurora_scene_quality_streak: list[str] = PrivateAttr()
    APP_NAME: str = "Sparkle"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool | None = None
    SERVICE_ROLE: str = "api"  # api | grpc

    # ── Release scope flags（T36 对齐 wt483 PLAN §2.1/§3；v3-output/wt483-t36-align/PLAN.md）──
    # 用户可见功能面的发布域闸，默认全 False（安全默认）；与既有 ENABLE_* 内部实验旋钮
    # 不共用命名空间与判据，但共用本 Settings 唯一权威与 env 管道——禁止另立
    # BaseSettings（V3-FIX-21 同族禁令，双权威脑裂）。只读视图与 FastAPI 依赖工厂见
    # app/config/release_flags.py；挂旗在卡 B/C（本卡=零行为变化，唯一消费面是
    # GET /api/v1/release-flags 契约端点）。
    RELEASE_ENABLE_SHOP: bool = False
    RELEASE_ENABLE_PHOTON_TRANSFER: bool = False
    RELEASE_ENABLE_PUBLIC_LEADERBOARDS: bool = False
    RELEASE_ENABLE_PUBLIC_COMMUNITY: bool = False
    RELEASE_ENABLE_VISUAL_ELEMENTS: bool = False

    # Security
    # Prefer JWT_SECRET to keep Python-issued JWT fully compatible with Gateway verification.
    SECRET_KEY: str = Field(default="", validation_alias=AliasChoices("JWT_SECRET", "SECRET_KEY"))
    JWT_ISSUER: str = "sparkle-gateway"
    JWT_AUDIENCE: str = "sparkle-app"

    # Community Settings
    MESSAGE_REVOKE_TIME_LIMIT_SECONDS: int = 120  # 消息撤回时间限制（秒），默认2分钟
    MESSAGE_SEND_MAX_RETRIES: int = 3  # 消息发送最大重试次数

    # Photon → Pro redemption（D-COMM-2「学出会员」有界兑换通道）
    # 汇率校准（2026-09-22，TOUR 活栈全旅程实测依据）：诚实日均光子收入 30-80，
    # 旧值 3000 → 兑 Pro 需约 100 天、实际无人可达（「学出会员」形同虚设）；
    # 1500 ≈ 强投入月（25 天 × 60 均值）可达、休闲刷分不可达——即「学出」的语义边界。
    # 下次校准数据钩子：photon status 端点上线后观测真实收入/兑换分布，30 天后复议。
    PHOTON_REDEEM_PRO_COST: int = 1500  # 单次兑换所需光子（仅合同/首胜/成就所得计入基数）
    PHOTON_REDEEM_PRO_DAYS: int = 7  # 单次兑换授予 Pro 天数
    PHOTON_REDEEM_PRO_MONTHLY_CAP: int = 1  # 每自然月硬顶次数（设计卡裁决：月顶 1 次）

    # 契约押金托管（MINT-FIX 关铸币洞，D-MONETIZE 审计 §1.5-R1/§1.6-1；
    # 参数面收尾 PHOTON-TUNE）。押金参数全部单点在 settings，运维改值即生效，
    # 代码零硬编码：
    #
    # - PHOTON_CONTRACT_STAKE_MAX：单契约押金上限。创建时 service 层强制
    #   （achievement_engine.ContractService.create_contract，超限 ValueError→API 400），
    #   schema 仅保留下限 `ge=10`——上限是经济参数，单点留在本文件（动态值不进
    #   pydantic Field）。1000 ≈ 诚实日均收入（30-80）两周量级、低于单次兑 Pro 价
    #   1500，兜住「完成双倍返还」的单契约通胀面。
    # - PHOTON_CONTRACT_REWARD_MULTIPLIER：完成奖励倍率（默认 2.0 = 还本 + 等额
    #   奖励，净得 stake×(multiplier−1)）。创建契约时从本值写入
    #   spark_contracts.reward_multiplier（存量契约按落库值结算，改配置不改在途）。
    # - 托管流转：创建即预扣（contract_escrow 流水）→ 完成发 stake×multiplier
    #   （grant_contract，其中 1 份还本）→ 失败/取消没收托管本金，不碰余额。
    #
    # 审计建议 1 的其余子项裁决（PHOTON-TUNE 登记不做）：审计原文未提议
    # 「押金日利率/超时罚则」，且二者会引入新的铸币/扣款语义（利息=无行为
    # 铸币、罚则=托管没收之外重复惩罚），无审计依据不落码。
    PHOTON_CONTRACT_STAKE_MAX: int = 1000
    PHOTON_CONTRACT_REWARD_MULTIPLIER: float = 2.0

    # 连击加成效果门槛 + 日上限/边际递减（PHOTON-TUNE，D-MONETIZE 审计 §1.6-2/R2：
    # 批量归档刷出 5050 光子 vs 诚实日均 30-80，激励须从「归档吞吐」改锚「学习效果」）
    # - PHOTON_COMBO_EFFECT_GATE_ENABLED：效果门槛总开关。开启后 combo 计数只由
    #   「带真实学习行为」的解锁事件累积（task_completed 事件按
    #   actual_minutes ≥ PHOTON_COMBO_EFFECT_MIN_MINUTES 判定；契约/签到/掌握度等
    #   事件自带真实行为判据，不设门槛）。关闭=旧行为（纯解锁计数，刷量路径，
    #   仅供回滚，测试以新旧对照钉住）。
    # - PHOTON_COMBO_DAILY_CAP：单用户单 UTC 日 combo 加成总额上限（发满即停，
    #   本笔 bonus_photons=0，连击展示不受影响）；≤0 表示不设上限。
    # - PHOTON_COMBO_DAILY_DECAY_FACTOR / _FLOOR：金额锚「当笔效果增量」
    #   （有效解锁数×10；旧式 combo×10 对窗口内前序解锁重复计价，属纯计数
    #   刷量锚点），同日第 n 次发放金额 = 增量×10×max(floor, factor^n)
    #   （n=当日已发放次数）；factor≥1 或 ≤0 语义视为不加衰减（=1.0）。
    #   诚实日 2-3 轮连击几乎无感，批量刷量迅速衰减。
    #   默认 100 日上限 ≈ 诚实日均总收入（30-80）上界，脉冲压到数百级。
    PHOTON_COMBO_EFFECT_GATE_ENABLED: bool = True
    PHOTON_COMBO_EFFECT_MIN_MINUTES: int = 1
    PHOTON_COMBO_DAILY_CAP: int = 100
    PHOTON_COMBO_DAILY_DECAY_FACTOR: float = 0.5
    PHOTON_COMBO_DAILY_DECAY_FLOOR: float = 0.1

    # 经济仪表告警阈值占位（PHOTON-TUNE，D-MONETIZE 审计 §1.6-5）。三个阈值
    # 对应 sparkle_photon_economy_daily_mint / _daily_burn /
    # _avg_balance_per_active_user 三仪表；0=默认静默不响（仅记仪表不告警），
    # >0 后日快照超限走 loguru 告警日志（alertmanager 接线的占位面）。
    PHOTON_ECONOMY_ALERT_DAILY_MINT_MAX: int = 0
    PHOTON_ECONOMY_ALERT_DAILY_BURN_MAX: int = 0
    PHOTON_ECONOMY_ALERT_AVG_BALANCE_MAX: int = 0

    COMMUNITY_INTELLIGENCE_ENABLED: bool = True
    COMMUNITY_INTELLIGENCE_MIN_COHORT_SIZE: int = 5
    COMMUNITY_INTELLIGENCE_DP_ENABLED: bool = True
    COMMUNITY_INTELLIGENCE_EPSILON: float = 1.0
    COMMUNITY_INTELLIGENCE_QUERY_EPSILON: float = 0.5
    COMMUNITY_INTELLIGENCE_DAILY_EPSILON: float = 3.0

    # Database (canonical envs: POSTGRES_*)
    DATABASE_URL: str = ""
    POSTGRES_HOST: str = Field(default="sparkle_db", validation_alias=AliasChoices("POSTGRES_HOST", "DB_HOST"))
    POSTGRES_PORT: int = Field(default=5432, validation_alias=AliasChoices("POSTGRES_PORT", "DB_PORT"))
    POSTGRES_USER: str = Field(default="postgres", validation_alias=AliasChoices("POSTGRES_USER", "DB_USER"))
    POSTGRES_PASSWORD: str = Field(default="", validation_alias=AliasChoices("POSTGRES_PASSWORD", "DB_PASSWORD"))
    POSTGRES_DB: str = Field(default="sparkle", validation_alias=AliasChoices("POSTGRES_DB", "DB_NAME"))
    SPARKLE_RBAC_ENABLED: bool = False
    SPARKLE_JWT_KEY_VERSION: str = "v1"  # P1-8: active JWT key version for rotation
    SPARKLE_JWT_PREVIOUS_KEY: str = ""  # P1-8: previous key for grace-period validation
    SPARKLE_ENGINE_DATABASE_URL: str = ""
    SPARKLE_CELERY_DATABASE_URL: str = ""

    # Redis (canonical envs: REDIS_*)
    REDIS_URL: str = ""
    REDIS_HOST: str = Field(default="sparkle_redis", validation_alias=AliasChoices("REDIS_HOST", "REDIS_HOSTNAME"))
    REDIS_PORT: int = Field(default=6379, validation_alias=AliasChoices("REDIS_PORT", "REDIS_PORT_NUMBER"))
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
    # V3-FIX-156 统一池治理：所有自建池上限经 app/core/database_pool_config.
    # resolve_pool_caps() 统一取数与校验，单进程上限之和 ≤ DB_CONNECTION_BUDGET
    # ≤ PG_MAX_CONNECTIONS − DB_CONNECTION_RESERVE（修前主引擎 20+40=60/进程，
    # 双进程+AGE+lane 之和 165 > PG 100 → "too many clients already"）。
    PG_MAX_CONNECTIONS: int = 100  # 共享 PostgreSQL max_connections（部署事实核验值）
    DB_CONNECTION_BUDGET: int = 80  # 单进程所有自建池上限之和的顶
    DB_CONNECTION_RESERVE: int = 20  # 给迁移/运维/超级用户的预留
    DB_POOL_SIZE: int = 15  # 主引擎常驻连接数（修前 20）
    DB_MAX_OVERFLOW: int = 15  # 主引擎最大溢出（修前 40，60 上限超预算已下调）
    DB_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）
    DB_POOL_TIMEOUT: int = 30  # 获取连接超时时间（秒，有界获取）
    AGE_POOL_MAX_SIZE: int = 6  # AGE asyncpg 池上限（修前 10）
    AGE_POOL_ACQUIRE_TIMEOUT: float = 5.0  # AGE acquire 超时（修前无超时=无限排队）
    DB_ECHO: bool = False  # 是否打印SQL语句（生产环境应为False）

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in value.split(",") if i.strip()]
        return v

    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"  # Set to "RS256" in production for asymmetric signing
    JWT_PRIVATE_KEY: str = ""  # PEM-encoded RSA private key (required for RS256 signing)
    JWT_PUBLIC_KEY: str = ""  # PEM-encoded RSA public key (required for RS256 verification)
    APPLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_ID: str = ""
    WS_ALLOW_QUERY_TOKEN: bool | None = None

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
    OPENCLAW_DEFAULT_WORKDIR: str = ""
    OPENCLAW_DEFAULT_TIMEOUT_SECONDS: int = 300
    OPENCLAW_MAX_DOWNLOAD_BYTES: int = 10 * 1024 * 1024
    OPENCLAW_MAX_CONCURRENT_RUNS: int = 3
    OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY: int = 5
    OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE: float = 0.85
    TOOL_EXECUTION_TIMEOUT_SECONDS: float = 120.0

    # Aurora Stage 18
    AURORA_STAGE18_AGGREGATOR_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE18_PUSH_POLICY_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE18_PUSH_DELIVERY_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 19
    AURORA_STAGE19_WORKING_MEMORY_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE19_LLM_EXTRACTOR_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE19_CONSOLIDATION_MODE: str = "live"  # off | shadow | live
    # Memory V3 (M-02): episodic 写路径 storage gate（off | shadow | live）
    AURORA_STAGE19_STORAGE_GATE_MODE: str = "live"

    # Aurora Stage 21
    AURORA_STAGE21_SKILL_STORE_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE21_SKILL_SELECTION_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE21_SKILL_SHARE_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 23
    AURORA_BAYESIAN_MODE: str = "live"  # Promoted to live: shadow soak passed (2026-04-28)
    AURORA_BAYESIAN_LIVE_CANARY_PERCENT: int = 5
    AURORA_BAYESIAN_TTL_DAYS: int = 30

    # Aurora Stage 24
    AURORA_POLICY_COMPILER_MODE: str = "live"  # off | shadow | live
    AURORA_POLICY_DAILY_BUDGET: int = 2
    AURORA_POLICY_COOLDOWN_HOURS: int = 24

    # Aurora Stage 25
    AURORA_REFLECTION_WIRE_MODE: str = "live"  # off | shadow | live
    AURORA_REFLECTION_CONTEXT_LIMIT: int = 20
    AURORA_REFLECTION_CONTEXT_MAX_TOKENS: int = 800
    AURORA_REFLECTION_TRIGGER_TOO_DIFFICULT: bool = True
    AURORA_REFLECTION_TRIGGER_UNCLEAR: bool = True
    AURORA_REFLECTION_TRIGGER_ABANDONED: bool = True
    AURORA_REFLECTION_TRIGGER_INTERVENTION_INEFFECTIVE: bool = True
    AURORA_REFLECTION_TRIGGER_PLAN_STALL: bool = True
    AURORA_REFLECTION_TRIGGER_OVERLOAD: bool = True

    # Aurora Stage 26
    AURORA_SCENE_MODE: str = "live"  # off | shadow | live
    AURORA_SCENE_SIMILARITY_THRESHOLD: float = 0.75
    AURORA_SCENE_TIME_WINDOW_HOURS: int = 72
    AURORA_SCENE_QUALITY_THRESHOLD: float = 0.6

    # Aurora Stage 27
    AURORA_FORESIGHT_MODE: str = "live"  # off | shadow | live
    AURORA_FORESIGHT_ATTRACTOR: str = "live"  # off | shadow | live
    AURORA_FORESIGHT_DEVIATION: str = "live"  # off | shadow | live
    AURORA_FORESIGHT_JITAI: str = "live"  # off | shadow | live
    AURORA_FORESIGHT_CACHE_TTL_SECONDS: int = 60
    AURORA_FORESIGHT_ATTRACTOR_ALPHA: float = 0.1
    AURORA_FORESIGHT_ATTRACTOR_MIN_CONFIDENCE: float = 0.3
    AURORA_FORESIGHT_DEVIATION_Z_THRESHOLD: float = 1.5
    AURORA_FORESIGHT_JITAI_DAILY_BUDGET: int = 3
    AURORA_FORESIGHT_JITAI_COOLDOWN_HOURS: int = 24
    AURORA_FORESIGHT_JITAI_MISFIRE_THRESHOLD: float = 0.15

    # Aurora Stage 28
    AURORA_TRAITS_MODE: str = "live"  # off | shadow | live
    AURORA_TRAITS_NLP_MODE: str = "live"  # off | shadow | live
    AURORA_TRAITS_COLDSTART_MODE: str = "live"  # off | shadow | live
    AURORA_TRAITS_NLP_COOLDOWN_HOURS: int = 24
    AURORA_TRAITS_NLP_BIAS_THRESHOLD: float = 0.10
    AURORA_TRAITS_NLP_MAX_DAYS: int = 30
    AURORA_TRAITS_NLP_MAX_COST_USD: float = 0.003
    AURORA_TRAITS_NLP_P95_MS_BUDGET: int = 800

    # Aurora Stage 29
    AURORA_SRL_MODE: str = "live"  # off | shadow | live
    AURORA_SRL_TRACKER_MODE: str = "live"  # off | shadow | live
    AURORA_SRL_BRIDGE_MODE: str = "live"  # off | shadow | live
    AURORA_SRL_SCAFFOLDING_CONSUME_MODE: str = "live"  # off | shadow | live
    AURORA_SRL_EVENT_LAG_P95_THRESHOLD_SECONDS: float = 5.0
    AURORA_SRL_MISJUDGMENT_THRESHOLD: float = 0.20
    AURORA_SRL_TRACKER_P95_MS_BUDGET: int = 20
    AURORA_SRL_AGGREGATOR_TTL_SECONDS: int = 15

    # Aurora Stage 30
    AURORA_METACOG_MODE: str = "live"  # off | shadow | live
    AURORA_METACOG_DASHBOARD_MODE: str = "live"  # off | shadow | live
    AURORA_METACOG_PROCESS_SCAFFOLDING_MODE: str = "live"  # off | shadow | live
    AURORA_METACOG_FSM_COMBINE_MODE: str = "live"  # off | shadow | live
    AURORA_METACOG_CACHE_TTL_SECONDS: int = 60
    AURORA_METACOG_MIN_SAMPLE_SIZE: int = 20
    AURORA_METACOG_PROCESS_TRIGGER_ABS_BIAS: float = 0.30
    AURORA_METACOG_PROCESS_COOLDOWN_HOURS: int = 72
    AURORA_METACOG_P95_MS_BUDGET: int = 100
    AURORA_METACOG_PROXY_REVISION_FREQUENCY: str = "live"
    AURORA_METACOG_PROXY_SELF_CORRECTION_RATE: str = "live"
    AURORA_METACOG_PROXY_QUESTION_TO_STATEMENT_RATIO: str = "live"
    AURORA_METACOG_PROXY_TIME_TO_FIRST_ACTION: str = "live"
    AURORA_METACOG_PROXY_COMPLETION_VS_ESTIMATE_DELTA_SIGN: str = "live"
    AURORA_IDIOGRAPHIC_MODE: str = "live"  # off | shadow | live
    AURORA_IDIOGRAPHIC_TTL_SECONDS: int = 300

    # Dual-Core Router
    AURORA_DUAL_CORE_ROUTER_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 33
    AURORA_STAGE33_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE33_SOCIAL_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE33_SRL_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE33_WM_PROMPT_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE33_EVENTS_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE33_COMMUNITY_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 34
    AURORA_STAGE34_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE34_ERROR_BRIDGE_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE34_CAPSULE_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE34_JOURNEY_SUBSCRIBERS_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 35
    AURORA_STAGE35_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE35_METACOG_ROUTER_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 37
    AURORA_STAGE37_LLM_SAFETY_MODE: str = "live"  # off | shadow | live

    # Aurora Stage 39
    AURORA_STAGE39_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE39_SCAFFOLDING_PROMPT_MODE: str = "live"  # off | shadow | live
    AURORA_STAGE39_COGLOAD_ROUTE_MODE: str = (
        "live"  # Promoted to live: Stage 39 tests pass, shadow soak complete (2026-04-22)
    )
    AURORA_STAGE39_GALAXY_INJECT_MODE: str = (
        "live"  # Promoted to live: Stage 39 tests pass, shadow soak complete (2026-04-22)
    )

    # Aurora Stage 40
    AURORA_STAGE40_CALENDAR_MODE: str = "live"  # off | shadow | live

    # FME Phase-1 — First-Minute Experience kill switches.
    # Shadow: analyze + log but return disabled so behavior stays identical.
    # Promote to "live" after validating intent analysis quality on real data.
    # See backend/app/services/fme_kill_switch_service.py
    FME_GOAL_FIRST_MINUTE_MODE: str = "shadow"  # off | shadow | live
    FME_TASK_CARD_PROTOCOL_MODE: str = "shadow"  # off | shadow | live

    # Email (SMTP)
    EMAIL_ENABLED: bool | None = None
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "Sparkle"

    # Release approval governance
    # JSON env example:
    # {"policy_publish":["ops@example.com"],"experiment_promote":["admin@example.com"],"*":["cto@example.com"]}
    RELEASE_APPROVERS_BY_CATEGORY: dict[str, list[str]] = Field(default_factory=dict)

    # WeChat Configuration
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # LLM Service
    LLM_API_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "deepseek-flash"
    LLM_REASON_MODEL_NAME: str = "deepseek-v4-pro"
    LLM_PROVIDER: str = (
        "qwen"  # 'qwen' | 'dashscope' | 'xiaomi' | 'deepseek' | 'zhipu' | 'openai' | 'hunyuan'（2026-09 主力切 Qwen；GLM 车道保留待用）
    )
    LLM_QUOTA_ENABLED: bool = False  # Disable token quota checks by default for demo recording
    LLM_DAILY_BUDGET_USD: float = 10.0  # Daily USD budget for LLM calls (cost_controller circuit breaker)
    RAG_DAILY_BUDGET_USD: float = 2.0  # Daily USD budget for RAG operations
    AURORA_DAILY_BUDGET_USD: float = 5.0  # Daily USD budget for Aurora operations
    # O-07 · Redis 故障时 cost 预算核算的有界降级（与网关 GW-P2-4 QuotaLocalFallback
    # 同设计语言：实例本地有界兜底，而非无界 fail-open）。开启后 Redis 读/写失败
    # 期间用进程内保守累计值继续执行预算闸门，防止成本面在 Redis 故障时变成无界。
    COST_BUDGET_REDIS_FALLBACK_ENABLED: bool = True
    # O-07 · run 预算派生（budget by user/plan/run/tier 的 run×tier 面）：
    # create_run 未显式携带 budget 时，按 users.entitlement（真源 app/core/entitlement.py）
    # 派生四维 run 预算默认值（JSON: max_total_tokens/max_cost_usd/max_tool_calls/
    # max_duration_seconds 的任意子集）。未知 entitlement 一律按 free（宁降不升）。
    RUN_BUDGET_DEFAULTS_ENABLED: bool = True
    RUN_BUDGET_LIMITS_FREE_JSON: str = (
        '{"max_total_tokens": 150000, "max_cost_usd": 0.5, "max_tool_calls": 50, "max_duration_seconds": 1800}'
    )
    RUN_BUDGET_LIMITS_PRO_JSON: str = (
        '{"max_total_tokens": 600000, "max_cost_usd": 2.0, "max_tool_calls": 200, "max_duration_seconds": 3600}'
    )
    # O-07 · 队列背压（FIX-49 glm_batch 无界回积的闸面）：投递前 LLEN 探测队列深度，
    # 超上限即丢弃（显式 outcome + 指标 + WARNING），不再无界堆积。LIMITS_JSON 为
    # 按队列覆盖（键=队列名，值=深度上限；0/负数=该队列显式不限），未覆盖队列用
    # DEFAULT_MAX_DEPTH。探测自身失败不阻断投递（broker 不可达时 send_task 必然
    # 失败，不存在无界堆积路径——见 app/core/queue_backpressure.py 模块注释）。
    QUEUE_BACKPRESSURE_ENABLED: bool = True
    QUEUE_BACKPRESSURE_DEFAULT_MAX_DEPTH: int = 1000
    QUEUE_BACKPRESSURE_LIMITS_JSON: str = '{"glm_batch": 200}'
    QUEUE_BACKPRESSURE_PROBE_TIMEOUT_SECONDS: float = 1.5
    # BATCH-CAP（PROD-LOG2 ②-2）：饱和聚合告警间隔（秒）。饱和期首条 ERROR +
    # 每隔该间隔一条 ERROR 汇总（含 episode 时长与累计丢弃数）+ 恢复 INFO——
    # 丢弃可观测为「速率/时长」而非 103 条逐条 WARNING。
    QUEUE_BACKPRESSURE_SATURATION_LOG_INTERVAL_SECONDS: float = 30.0
    # SECTOR-BACKFILL-Dedup · 星域回填在途去重 TTL（秒）：同用户回填批次入队后
    # 在该窗口内不重复入队（get_galaxy_graph 每次取图都触发 ensure_backfill，
    # 活栈实证无去重时同一批节点 0.7s 内被重复 enqueue、队列恒满 200/200）。
    NODE_SECTOR_BACKFILL_DEDUP_TTL: int = 600
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
    LLM_TIER_TOP: str = ""
    LLM_TIER_GLM_BATCH: str = ""
    LLM_TIER_SPECIALIST: str = ""

    # XiaoMi MIMO Configuration
    # XIAOMI-MODEL（2026-09-22 考证回挂）：旧名 mimo-v2-flash 已于北京时间
    # 2026-06-30 00:00 正式下线（官方 deprecate 公告，系统替换 06-18→mimo-v2.5），
    # 此后该名一律 404 Unsupported model（PROD-LOG2 ②-3 实测）。现挂
    # mimo-v2.6-flash（2026-09-22 发布的 V2.6 系列，官方定位「高频调用/大规模
    # 任务」；官方替代品 mimo-v2.5 将于 2026-10-21 10:00 下线，故不挂它）。
    # 来源：mimo.mi.com/static/docs/{updates/deprecate.md, updates/model.md,
    # quick-start/summary/model.md}；端点形制与下方 BASE_URL 逐字核对一致。
    XIAOMI_MIMO_API_KEY: str = ""
    XIAOMI_MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    XIAOMI_CHAT_MODEL: str = "mimo-v2.6-flash"
    XIAOMI_STANDARD_MODEL: str = "mimo-v2.6-flash"
    # 注意：官方模型 id 为全小写 mimo-v2.5（"MiMo-V2.5" 是展示名，非 id），
    # 且 mimo-v2.5 将于 2026-10-21 10:00 下线（无系统替换）——mimo_pro 复活前
    # 应切 mimo-v2.6-pro（本卡不动 mimo_pro，仅登记考证事实）。
    XIAOMI_PRO_MODEL: str = "MiMo-V2.5"
    XIAOMI_TEMPERATURE: float = 0.3
    XIAOMI_PRO_TEMPERATURE: float = 0.3

    # MIMO Token Plan API (Pro route uses a different base URL from flash/standard)
    XIAOMI_MIMO_TOKEN_PLAN_API_KEY: str = ""
    XIAOMI_MIMO_TOKEN_PLAN_BASE_URL: str = "https://token-plan-cn.xiaomimimo.com/v1"

    # Prompt Snapshot (debug observability)
    PROMPT_SNAPSHOT_ENABLED: bool = False
    PROMPT_SNAPSHOT_SAMPLE_RATE: float = 0.0
    PROMPT_SNAPSHOT_MAX_CHARS: int = 1200

    # DeepSeek Configuration (核心模型 - 思考模式)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_CHAT_MODEL: str = "deepseek-flash"
    DEEPSEEK_REASON_MODEL: str = "deepseek-v4-pro"

    # MiniMax 异步分析通道（DIST-SEMAPHORE 口径校正，依据 v3-output/MINIMAX-QUOTA：
    # MiniMax 官方按**账户**（主+子账号共享）限 RPM/TPM——免费 20 RPM / 1M TPM，
    # 充值 200 RPM / 10M TPM，无文档化并发数；MINIMAX_MAX_CONCURRENCY 是进程内
    # 自保护阀，不是官方配额口径。只承接后台/离线、非用户直面分析，不进主聊天
    # 路由；车道满时快速拒绝）
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimaxi.com/v1"
    MINIMAX_CHAT_MODEL: str = "MiniMax-M3"
    MINIMAX_MAX_CONCURRENCY: int = 8
    # DIST-SEMAPHORE：跨进程 MiniMax 账户级 RPM 预算（Redis 60s 固定窗口，容量 =
    # 本值/分钟，引擎与全部 celery worker 共享一份）。官方按账户限 RPM（免费 20 /
    # 充值 200，主+子账号共享），三进程各持本地 asyncio 池时 RPM 预算无全局面。
    # - 0（默认，回滚位）= 禁用：仅本地并发池，行为与本设置引入前完全一致
    #   （与 BATCH-CAP 的 env 分摊路径兼容，二者可叠加）；
    # - >0 = 启用；Redis 缺席/出错时诚实降级回本地池并限频告警（不阻断）。
    # 本地并发池保留为第二道防线：RPM 桶通过后仍过 MINIMAX_MAX_CONCURRENCY 槽。
    MINIMAX_RPM_BUDGET: int = 0
    # BATCH-CAP（PROD-LOG2 ②-2）：llm_concurrency MINIMAX 池的等槽超时（秒）。
    # 原 45s 固定值在双 batch worker 载荷下被打穿（34 次超时→熔断 OPEN）。本池
    # 全部 in-engine 消费者都有降级/重试面，按直连车道同语义 fast-fail；5s ≈
    # 2×聊天车道 p95 2.2s，覆盖正常瞬态排队，饱和时快速失败走 fallback/重试。
    MINIMAX_QUEUE_TIMEOUT_SECONDS: float = 5.0
    # glm_batch 车道执行 provider 开关（B 线模型切换 2026-09-22，测试替换语义）：
    # - "glm"：batch 类调用走 GLM 原链；MINIMAX/DASHSCOPE key 即便已配置，
    #   batch 专用条目（minimax_m3_batch/qwen3_7_flash_batch）也不注册
    #   ——「GLM 保留配置不删、不启用」。
    # - "minimax"（默认，2026-09-24 切换）：充值档真 key 冒烟已过（预测任务
    #   POST api.minimaxi.com 200 OK / 4.9s 成功），MM-M3+QWEN-PLAN 验证车道
    #   （MiniMax M3 置首、Qwen batch 次位，均 key-gated；全无 key 落 GLM 原链
    #   兜底）。回滚 = 改回 "glm" 重启引擎。
    # 非法值/显式空值仍安全回退 glm（见 llm_router.batch_llm_provider）。
    BATCH_LLM_PROVIDER: str = "minimax"

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
    ZHIPU_TOP_MODEL: str = "glm-5.1"  # TOP 层模型
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
    # R2-fix: 12s 低于审查模型实测延迟（qwen3.8-flash 常态 12-14s、P95 超
    # 30s，见 round2 验收与 wt6 实测引擎日志），几乎每轮触发 TimeoutError →
    # fail-closed（score=0.00 + 1 个 critical"审查过程出错"）→ 无效重写。
    # 45s 与 ReviewerAgent.DEFAULT_LLM_TIMEOUT_SECONDS 对齐，覆盖 P95+。
    REVIEWER_LLM_TIMEOUT_SECONDS: int = 45
    # 演示缺陷 ❌#6：生成后审查链（generation_review→reflection）在末个内容
    # delta 之后、done 之前同步执行；审查 LLM 不可用时每轮烧满超时预算
    # （review 45s + reflection 多轮 × 45s+ ≈ 实测 done 尾延迟 120-145s）。
    # 置 False 可整体跳过生成后审查（内容审查本就无法撤回已流出的正文）。
    ENABLE_GENERATION_REVIEW: bool = True

    # OCR / Document Cleaning
    OCR_PROVIDER: str = "zhipu"  # zhipu | siliconflow
    OCR_BACKUP_PROVIDER: str = "siliconflow"  # zhipu | siliconflow

    # Embedding Service
    EMBEDDING_PROVIDER: str = "dashscope"  # dashscope | siliconflow
    EMBEDDING_BACKUP_PROVIDER: str = "siliconflow"  # dashscope | siliconflow
    EMBEDDING_MODEL: str = "text-embedding-v4"  # 向量模型
    EMBEDDING_DIM: int = 1024  # 向量维度
    EMBEDDING_CACHE_TTL_SECONDS: int = 300  # embedding 结果 Redis 缓存 TTL
    # E-05 版本隔离：True 时检索只使用 embedding_model 等于当前版本的向量；
    # False（过渡期默认）额外容忍 embedding_model 为 NULL 的存量向量，
    # 但任何"标记了其他模型"的向量始终被排除。重建索引后建议置 True。
    EMBEDDING_STRICT_VERSION_FILTER: bool = False
    ENABLE_CONTEXTUAL_CHUNK_ENRICHMENT: bool = True
    RERANK_PROVIDER: str = "dashscope"  # dashscope | siliconflow
    RERANK_BACKUP_PROVIDER: str = "siliconflow"  # dashscope | siliconflow
    RERANK_MODEL: str = "qwen3-rerank"  # 重排序模型

    # DashScope (Aliyun) —— 2026-09 主力模型切换：GLM 系 → Qwen（通义千问）系。
    # 分层定价基准（北京地域，元/百万Token，2026-09 官方页）：
    #   qwen3.7-flash 0.2/0.8（≤32K 阶梯）｜qwen3.8-flash 0.8/2.7｜
    #   qwen3.7-plus 非思考 ~2/2（限时8折），思考 8/8｜qwen3.8-max 12/36
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_HTTP_API_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    DASHSCOPE_BASE_URL_COMPATIBLE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_CHAT_MODEL: str = "qwen3.7-plus"  # PLUS 层：高质量非思考
    DASHSCOPE_REASON_MODEL: str = "qwen3.7-plus"  # PRO 层：思考模式（enable_thinking 车道）
    DASHSCOPE_FAST_MODEL: str = "qwen3.7-flash"  # FAST 层：轻对话/首 token 延迟取向
    DASHSCOPE_STANDARD_MODEL: str = "qwen3.8-flash"  # STANDARD 层：甜点轻思考
    DASHSCOPE_MAX_MODEL: str = "qwen3.8-max"  # MAX 层：旗舰深推理
    DASHSCOPE_TOP_MODEL: str = "qwen3.8-max"  # TOP 层：超高层（同旗舰，思考默认开）
    DASHSCOPE_BATCH_MODEL: str = "qwen3.7-flash"  # glm_batch 异步分析车道（Batch API 半价为后续优化项）
    DASHSCOPE_TEMPERATURE: float = 0.7
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v4"
    DASHSCOPE_RERANK_MODEL: str = "qwen3-rerank"

    # SiliconFlow (Embedding/Rerank)
    SILICONFLOW_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-4B"
    SILICONFLOW_RERANK_MODEL: str = "Qwen/Qwen3-Reranker-4B"

    # STT (Speech to Text) Service
    STT_PROVIDER: str = "bailian"  # bailian | zhipu | xunfei
    STT_BACKUP_PROVIDER: str = "zhipu"  # zhipu | xunfei | bailian
    STT_ENHANCE_ENABLED: bool = True  # 是否启用LLM后处理增强

    # Qwen ASR (Bailian realtime) Configuration
    # 实时协议: wss://.../api-ws/v1/realtime?model={QWEN_ASR_MODEL}，manual commit 模式
    QWEN_ASR_WS_URL: str = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    QWEN_ASR_MODEL: str = "qwen3-asr-flash-realtime"
    QWEN_ASR_SAMPLE_RATE: int = 16000
    QWEN_ASR_STREAM_SEGMENT_SECONDS: int = 4
    QWEN_ASR_MAX_AUDIO_SECONDS: int = 60
    QWEN_ASR_REQUEST_TIMEOUT_SECONDS: int = 30
    QWEN_ASR_LANGUAGE: str = "zh"

    # TTS (Text to Speech) Service
    TTS_PROVIDER: str = "bailian"  # bailian
    QWEN_TTS_MODEL: str = "qwen3-tts-instruct-flash"
    QWEN_TTS_VOICE: str = "Cherry"
    QWEN_TTS_AUDIO_FORMAT: str = "wav"
    QWEN_TTS_REQUEST_TIMEOUT_SECONDS: int = 60

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

    # E-06 Async Batch Cognitive Worklane（异步批处理认知车道）
    # 三类不需实时的认知负载（reflection/profile aggregation/analytics）统一
    # 经 batch_worklane 路由到 GLM_BATCH tier（MiniMax 优先）。并发/预算均与
    # 前台隔离；模型真源仍是 llm_router（E-02），车道只做 tier 钳制。
    BATCH_LANE_ENABLED: bool = True
    BATCH_LANE_ENABLED_REFLECTION: bool = True
    BATCH_LANE_ENABLED_PROFILE_AGGREGATION: bool = True
    BATCH_LANE_ENABLED_ANALYTICS: bool = True
    # 有界重试：耗尽进死信终态（指标+死信登记），绝不无限循环
    BATCH_LANE_MAX_ATTEMPTS: int = 3
    BATCH_LANE_RETRY_BACKOFF_SECONDS: float = 2.0
    # 车道级总并发闸（跨三类 kind；提供商池再由 llm_concurrency 隔离）
    BATCH_LANE_MAX_CONCURRENCY: int = 4
    BATCH_LANE_CALL_TIMEOUT_SECONDS: float = 90.0
    # freshness SLA：超过即视为 stale 结果，消费方必须拒绝
    BATCH_LANE_FRESHNESS_SLA_REFLECTION_SECONDS: int = 6 * 3600
    BATCH_LANE_FRESHNESS_SLA_PROFILE_AGGREGATION_SECONDS: int = 24 * 3600
    BATCH_LANE_FRESHNESS_SLA_ANALYTICS_SECONDS: int = 48 * 3600
    # batch 独立日预算（USD）：与前台 LLM_DAILY_BUDGET_USD 分桶核算
    BATCH_LANE_DAILY_BUDGET_USD: float = 0.5
    # 幂等：结果保留时长需 ≥ 最长 freshness SLA；claim 防同 key 并发双执行
    BATCH_LANE_RESULT_TTL_SECONDS: int = 48 * 3600
    BATCH_LANE_CLAIM_TTL_SECONDS: int = 600
    BATCH_LANE_DEADLETTER_MAX_ENTRIES: int = 200

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
    STANDARD_CHAT_FORCE_FAST_TIER: bool = True  # 标准对话首答强制走 FAST/Flash 层（仅 standard 档，F-1 保留其性能取向）
    # F-1：deep_analysis 档延迟逃生阀。False（默认）= deep_analysis 生成真实路由 MAX 层
    # （deepseek_reason → deepseek-v4-pro，产品"深度规划"核心卖点）；True = 强制 FAST 层换首 token 延迟。
    # 与免费层钳制正交：free 用户即使本开关为 False 仍会被钳到 ceiling（默认 fast）。
    DEEP_ANALYSIS_FORCE_FAST_TIER: bool = False
    FAST_INTERACTION_COPY_ENABLED: bool = True  # 澄清/确认文案优先由 FAST 模型生成
    EARLY_ACK_PROGRESS_ENABLED: bool = True  # 编排开始前先推送即时状态确认
    # B-02 MIDSTREAM-HEARTBEAT：建模图长工具/思考段（实测 50s+ 无帧静默窗）周期补发
    # 诚实心跳帧（仍在处理 + 已耗时，复用 AgentStatus.THINKING 既有帧型，零网关改动）。
    # 心跳只保证「流还活着」的可见性，绝不伪造阶段进度；间隔 <=0 视为关闭。
    STREAM_HEARTBEAT_ENABLED: bool = True  # 图执行静默段周期心跳帧总开关
    STREAM_HEARTBEAT_INTERVAL_SECONDS: float = 10.0  # 静默多少秒后开始周期发心跳

    # Free Tier Model Downgrade (免费层跨层模型降级)
    FREE_TIER_DOWNGRADE_ENABLED: bool = True  # 免费用户能力层请求钳制总开关
    FREE_TIER_MODEL_CEILING: str = "fast"  # 免费层允许的最高能力 tier（fast|standard）

    # E-07: Provider 健康滞回（health circuit + hysteresis）。
    # 语义：连续 FAILURE_THRESHOLD 次失败 → unhealthy（路由跳过）；冷却 RECOVERY_SECONDS
    # 无新失败 → probation（恢复观察：可选但观察期内 1 次失败立即回 unhealthy 且冷却翻倍，
    # 防 provider 抖动引发切换风暴）；probation 内连续 PROBE_SUCCESS_THRESHOLD 次成功
    # → healthy（恢复完整失败容错）。冷却翻倍封顶 COOLDOWN_MAX_SECONDS（有界，不无界退避）。
    LLM_HEALTH_FAILURE_THRESHOLD: int = 5
    LLM_HEALTH_RECOVERY_SECONDS: float = 300.0
    LLM_HEALTH_PROBE_SUCCESS_THRESHOLD: int = 3
    LLM_HEALTH_COOLDOWN_MAX_SECONDS: float = 1800.0

    # V3-FIX-78/79（wt448）：provider 断供/过载的快速诚实失败（Q-06 波动注入实锤）。
    # LLM_FALLBACK_TOTAL_BUDGET_SECONDS：单次 LLM 调用 fallback 链的总时延预算。
    # 首个尝试不受预算限制（走既有 first-chunk/整体超时窗）；预算到点后拒绝发起新的
    # 上游尝试，以 LLMProvidersExhaustedError 快速收场——S2 实锤 86 连败/180s 静默
    # 的重试预算上界。默认 45s 与流式 first-chunk 窗对齐：慢面（S3b 65s TTFT）在
    # 一个完整窗口后即诚实失败，而不是继续换道烧满客户端超时。
    LLM_FALLBACK_TOTAL_BUDGET_SECONDS: float = 45.0
    # LLM_POOL_MAX_WAITING：单 provider 并发池排队深度 admission cap。超限的新到
    # 请求立即以 LLMOverloadedError 拒绝（429 语义优先于等满 queue_timeout）——
    # S5 实锤 22/30 静默烧满 150s 的背压出口；等槽者数量有界，拒绝者毫秒级拿到
    # 繁忙语义。<=0 视为不设 cap（旧行为）。
    LLM_POOL_MAX_WAITING: int = 20

    # E-07: 三维自适应路由（quality/latency/cost 反馈环）。
    # 真实调用结果回流打分；候选链内稳定重排，不跨 tier 提升（自适应是 E-02 路由的
    # 反馈维度扩展，不是新决策真源）。冷启动（样本 < MIN_SAMPLES）不介入 = E-02 既有策略。
    # 滞回 margin：首位分差低于阈值不交换（防评分抖动引发候选顺序抖动）。
    ADAPTIVE_ROUTING_ENABLED: bool = True
    ADAPTIVE_ROUTING_WINDOW: int = 64  # 每模型 outcome 滑窗上限（有界内存）
    ADAPTIVE_ROUTING_MIN_SAMPLES: int = 8  # 介入所需最少样本（冷启动保护）
    ADAPTIVE_ROUTING_MARGIN: float = 0.05  # 首位切换最小分差（滞回）
    ADAPTIVE_ROUTING_WEIGHT_QUALITY: float = 0.5
    ADAPTIVE_ROUTING_WEIGHT_LATENCY: float = 0.3
    ADAPTIVE_ROUTING_WEIGHT_COST: float = 0.2
    ADAPTIVE_ROUTING_LATENCY_REF_MS: float = 5000.0  # 延迟归一参考（≥此值 latency_score=0）
    ADAPTIVE_ROUTING_COST_REF_PER_1K: float = 0.01  # 成本归一参考（≥此值 cost_score=0）

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
    # C-01: ContextPack.decision_context 决策面契约（Aurora/Router/Planner 共同消费）
    ENABLE_DECISION_CONTEXT: bool = True
    # C-02: 四分 source adapter 独立开关（state/memory/knowledge/events）
    ENABLE_CONTEXT_SOURCE_STATE: bool = True
    ENABLE_CONTEXT_SOURCE_MEMORY: bool = True
    ENABLE_CONTEXT_SOURCE_KNOWLEDGE: bool = True
    ENABLE_CONTEXT_SOURCE_EVENTS: bool = True
    ENABLE_BUDGET_TUNING: bool = True
    CONTEXT_PACK_FEEDBACK_WINDOW_MINUTES: int = 10
    ENABLE_CONTEXT_RANKING: bool = True
    ENABLE_CONTEXT_FOCUSING: bool = True
    ENABLE_CONTEXT_SEMANTIC_GATING: bool = True
    # M-05: over-personalization Self-ReCheck at the memory output-assembly
    # faces (context_pack.build / stage34 / past-session pull). Default on;
    # off is an explicit ops action (passthrough + no metadata) — wiring
    # guards turn removal of any final-gate call red.
    ENABLE_MEMORY_USE_SELFCHECK: bool = True
    ENABLE_CONTEXT_BRIEFING: bool = True
    ENABLE_CONTEXT_FOCUS_METADATA: bool = True
    ENABLE_FOCUS_DOCUMENT_CONTEXT: bool = True
    CONTEXT_TOTAL_TOKEN_BUDGET: int = 8000
    # C-06：tier × decision-type 预算矩阵（core/context_budget_matrix.py）。
    # CONTEXT_TOTAL_TOKEN_BUDGET 语义降级为「全局硬顶」（运维刹车）；矩阵值
    # 经它钳制后成为各 tier/决策类型的实际总预算。显式传入
    # ContextBudgetManager(total_token_budget=...) 时矩阵不介入（向后兼容）。
    ENABLE_CONTEXT_BUDGET_MATRIX: bool = True
    CONTEXT_BUDGET_MATRIX_JSON: str = ""  # 可选整体覆盖，见 load_budget_matrix
    DEFAULT_CONTEXT_ENTITLEMENT: str = "free"  # 上下文面缺失 entitlement 时的预算层
    # C-06：长会话确定性 compaction（orchestration/conversation_compaction.py）。
    # 默认路径零 LLM；ENABLE_LLM_SESSION_SUMMARY=True 时 LLM 摘要作为可选档
    # 回归（tier-3 原路径），LLM 失败仍回落确定性 compaction。
    ENABLE_DETERMINISTIC_COMPACTION: bool = True
    ENABLE_LLM_SESSION_SUMMARY: bool = False
    COMPACTION_RECENT_WINDOW: int = 6
    COMPACTION_KEY_MESSAGE_CAP_TOKENS: int = 220
    # C-06：knowledge JIT（core/knowledge_jit.py）——大知识源只注入
    # references + top chunks，Agent 经 retrieve_user_material 按需 fetch。
    ENABLE_KNOWLEDGE_JIT: bool = True
    KNOWLEDGE_JIT_FULL_LOAD_MAX_TOKENS: int = 1200
    KNOWLEDGE_JIT_KEEP_TOP_TOKENS: int = 600
    KNOWLEDGE_JIT_MAX_REFERENCES: int = 8
    CONVERSATION_HISTORY_CONTEXT_RATIO: float = 0.40
    ENABLE_DOCUMENT_CONTEXT_INJECTION: bool = True
    DOCUMENT_CONTEXT_RATIO: float = 0.25
    DOCUMENT_CONTEXT_MAX_CHUNKS: int = 5
    DOCUMENT_CONTEXT_RECENCY_BOOST_DAYS: int = 30
    GALAXY_KNOWLEDGE_CONTEXT_RATIO: float = 0.15
    TASK_ERROR_CONTEXT_RATIO: float = 0.10
    COGNITIVE_PROFILE_CONTEXT_RATIO: float = 0.10
    AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE: str = "live"  # off | shadow | live
    # Aurora document-context gate. auto/live/on run the classifier; off/skip disable
    # document retrieval for every turn; selective/aggressive cap positive decisions.
    AURORA_DOC_CONTEXT_MODE: str = "auto"
    AURORA_DOC_CONTEXT_AGGRESSIVE_BUDGET_TOKENS: int = 2200
    AURORA_DOC_CONTEXT_SELECTIVE_BUDGET_TOKENS: int = 900
    AURORA_DOC_CONTEXT_AMBIGUOUS_BUDGET_TOKENS: int = 500
    AURORA_STAGE38_ERR_REPLAN_MODE: str = "live"
    AURORA_STAGE38_PUSH_SCHEDULER_MODE: str = "live"
    AURORA_STAGE38_PUSH_SCHEDULER_INTERVAL_MINUTES: int = 5
    CONTEXT_SEMANTIC_GATING_RULES_JSON: str = ""
    CONTEXT_RANKING_SOFT_CAP_EPISODIC: int = 6
    CONTEXT_RANKING_SOFT_CAP_GOALS: int = 5
    ENABLE_MEMORY_CONFLICT_RESOLUTION: bool = True
    ENABLE_PERSONALIZED_RANKING: bool = True
    MEMORY_RANK_DEFAULT_EVIDENCE: float = 0.6
    MEMORY_RANK_DEFAULT_FRESHNESS: float = 0.3
    MEMORY_RANK_DEFAULT_CORRECTION: float = 0.1
    ENABLE_USER_MEMORY_CONTROLS: bool = True
    SPARKLE_MEMORY_INFERRED_WRITE_ENABLED: bool = True
    SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED: bool = False
    SPARKLE_AGGREGATOR_ENABLED: bool = True
    AURORA_LEDGER_PATH: str = "backend/data/aurora/ledger.json"
    AURORA_FME_L3_CLOSURE_MODE: str = "live"
    # This data is prompt context only, not a routing decision signal.
    # Any if/switch logic based on it requires Stage 19B Sufficiency Judge acceptance.
    SPARKLE_ROUTER_SOCIAL_CONTEXT_READ_ENABLED: bool = True
    SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER: bool = True
    SPARKLE_PUSH_POLICY_ENABLED: bool = True
    SPARKLE_PUSH_DELIVERY_ENABLED: bool = True
    # daily-flow DF-9: 推送总开关默认值。False 意味着从未显式 opt-in 的用户
    # 永远收不到任何提醒（渠道结构性静默）；默认 True = opt-out 产品语义，
    # 用户仍可在 push-settings 里一键关闭（落库 enabled=False 后不再打扰）。
    PUSH_OPT_IN_DEFAULT_ENABLED: bool = True
    SPARKLE_WORKING_MEMORY_ENABLED: bool = True
    SPARKLE_LLM_EXTRACTOR_ENABLED: bool = True
    SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED: bool = False
    SPARKLE_DUAL_CORE_BELIEF_SIGNALS_ENABLED: bool = False
    SPARKLE_DUAL_CORE_BELIEF_UNCERTAINTY_MAX: float = 0.10
    SPARKLE_CONSOLIDATION_ENABLED: bool = True
    SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE: bool = False
    SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED: bool = True
    AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE: str = "live"
    AURORA_STAGE20_CONFLICT_RESOLVER_MODE: str = "live"
    SPARKLE_SKILL_STORE_ENABLED: bool = True
    SPARKLE_SKILL_EXTRACT_ENABLED: bool = True
    SPARKLE_SKILL_SELECTION_ENABLED: bool = True
    SPARKLE_SKILL_SHARE_ENABLED: bool = True
    SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED: bool = False
    SPARKLE_SKILL_EXTRACT_MODEL: str = "claude-haiku-4-5"
    SPARKLE_SKILL_EXTRACT_MAX_TOKENS: int = 300
    SPARKLE_SKILL_SHARE_REVIEW_MODEL: str = "claude-haiku-4-5"
    SPARKLE_SKILL_SHARE_REVIEW_MAX_TOKENS: int = 200
    SPARKLE_LLM_EXTRACTOR_MODEL: str = "claude-haiku-4-5"
    SPARKLE_LLM_EXTRACTOR_TIMEOUT_SECONDS: float = 12.0
    SPARKLE_LLM_EXTRACTOR_RETRY_COUNT: int = 1
    SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_CALL: int = 200
    SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_SESSION: int = 2000
    # Legacy alias kept for Stage 17 compatibility with the prompt renderer.
    SPARKLE_PROMPT_SOCIAL_CONTEXT_RENDER_ENABLED: bool = True
    MEMORY_INFERRED_MIN_CONFIDENCE: float = 0.9
    # Memory V3 (M-02) Personalized Storage Gate —— episodic 写路径五分类
    # （store/current_state/event/ignore/confirm）。语义判定层可独立关闭
    # （纯规则仍完整工作）；熔断/超时/失败一律降级为规则默认，不炸主链。
    # 默认模型取 flash 档（与 DASHSCOPE_FAST_MODEL 同款、router 已注册）；
    # 未注册名会 router 失败 → 语义层自动降级（不致命，但等于白开）。
    SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED: bool = False
    SPARKLE_STORAGE_GATE_SEMANTIC_MODEL: str = "qwen3.8-flash"
    # 3.0s 会截断 flash 档 thinking 模型（实测 qwen3.8-flash JSON 分类 ~2-3.4s），
    # 5.0s 为实测可用下限；写路径仍由外层韧性兜底（超时→规则默认）。
    SPARKLE_STORAGE_GATE_SEMANTIC_TIMEOUT_SECONDS: float = 5.0
    SPARKLE_STORAGE_GATE_SEMANTIC_MAX_PER_MINUTE: int = 30
    # X-02 · Action Allocation Policy（Human/Agent/Hybrid delegation rubric）——
    # 语义灰区层（可选）。纯规则层完整可用且可独立评测；语义层仅对 D6 灰区
    # 残留生效，且只能在规则层算出的 feasible set 内选 mode（代码强制），
    # 熔断/超时/失败一律降级规则默认。
    SPARKLE_ALLOCATION_SEMANTIC_ENABLED: bool = False
    SPARKLE_ALLOCATION_SEMANTIC_MODEL: str = "qwen3.8-flash"
    SPARKLE_ALLOCATION_SEMANTIC_TIMEOUT_SECONDS: float = 5.0
    SPARKLE_ALLOCATION_SEMANTIC_MAX_PER_MINUTE: int = 30
    # A-04 · Aurora Joint Decision（intervention × allocation 联合决策）——
    # 语义开放选择层（可选，A-02 receipt §4.6 settings 化）。纯规则联合核
    # 完整可用；语义层仅对规则层标记 semantic_eligible 的开放选择生效，
    # 且只能在联合可行 (intervention, mode) 对集内选干预（代码强制，
    # mode 永不由 LLM 决定）；熔断/超时/失败一律降级规则默认。
    SPARKLE_JOINT_SEMANTIC_ENABLED: bool = False
    SPARKLE_JOINT_SEMANTIC_MODEL: str = "qwen3.8-flash"
    SPARKLE_JOINT_SEMANTIC_TIMEOUT_SECONDS: float = 5.0
    SPARKLE_JOINT_SEMANTIC_MAX_PER_MINUTE: int = 30
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

    # HyDE (Hypothetical Document Embeddings) pre-retrieval query expansion
    ENABLE_HYDE: bool = True
    HYDE_SKIP_THRESHOLD: float = 0.85
    HYDE_MAX_TOKENS: int = 80
    HYDE_TIMEOUT_SECONDS: float = 2.0
    ENABLE_GRAPHRAG_MONITOR_API: bool = False
    GRAPHRAG_TRACE_TTL_SECONDS: int = 86400
    GRAPHRAG_TRACE_MAX_BYTES: int = 20000
    GRAPHRAG_TRACE_QUERY_MAX_CHARS: int = 256
    ENABLE_GRAPHRAG_TRACE_PII: bool = False
    ENABLE_GRAPHRAG_RERANKER: bool = False
    DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD: float = 0.72
    DOCUMENT_CONTEXT_WEAK_EVIDENCE_MARGIN: float = 0.08
    DOCUMENT_CONTEXT_KEYWORD_OVERLAP_WEIGHT: float = 0.0
    MASTERY_BOOST_FACTOR: float = 0.5
    ENABLE_DOCUMENT_FEEDBACK_LOOP: bool = True
    AURORA_PRIVACY_PII_REDACTION_MODE: str = "live"  # off | shadow | live
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
    FILE_MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    FILE_PRESIGN_EXPIRES_SECONDS: int = 420
    FILE_ALLOWED_MIME_TYPES: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
        "text/markdown,"
        "text/plain,"
        "image/png,"
        "image/jpeg,"
        "image/gif,"
        "image/webp"
    )
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_PUBLIC_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "sparkle-files"
    MINIO_REGION: str = ""
    MINIO_USE_SSL: bool = False

    # MDX Dictionary Configuration
    # Default is True but the mdx_dictionary_service module will gracefully
    # degrade to MDX_AVAILABLE=False when readmdict/python-lzo are missing.
    MDX_DICTIONARY_ENABLED: bool = True
    MDX_DICTIONARY_PATH: str = ""
    MDD_RESOURCES_PATH: str | None = None
    DICTIONARY_PACKAGE_DIR: str = "data/dictionaries/packages"
    DICTIONARY_PACKAGE_BASE_URL: str = ""

    # Internal API
    INTERNAL_API_KEY: str = ""
    GATEWAY_INTERNAL_URL: str = ""

    # FV-24: SLO auto-degrade kill switch modes (off=normal, live=degraded)
    SLO_AUTO_LLM_DEGRADE_MODE: str = "off"
    SLO_AUTO_REDIS_FALLBACK_MODE: str = "off"
    SLO_AUTO_DB_THROTTLE_MODE: str = "off"
    SLO_AUTO_EVENT_BUS_THROTTLE_MODE: str = "off"
    SLO_AUTO_RATE_LIMIT_TIGHTEN_MODE: str = "off"

    # Production URL (used for Flutter deeplinks, CORS, and email links)
    PRODUCTION_URL: str = ""  # e.g. https://sparkle.example.com

    # Logging
    LOG_LEVEL: str = "INFO"
    # ENGINE-LOGROT: 可选轮转文件 sink——默认空串 = 关闭（行为与未合入本配置前一致）。
    # 仅 uvicorn 进程消费（gRPC 进程在 grpc_server.py 自带轮转文件 sink）；
    # rotation=LOG_ROTATION_MB（MB 尺寸），retention=LOG_RETENTION（保留文件数）。
    LOG_FILE_PATH: str = ""
    LOG_ROTATION_MB: float = 20.0
    LOG_RETENTION: int = 10

    # Sentry crash reporting
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Demo Mode (演示模式 - 用于竞赛演示，确保关键流程稳定)
    DEMO_MODE: bool = False  # 生产环境应设为 False

    # Optional Agent Graph V2
    ENABLE_AGENT_GRAPH_V2: bool = False
    ENABLE_MODE_WORKFLOW_V2: bool = True
    ENABLE_AURORA_RUNTIME_V1: bool = True
    # .env.example 声明的 Aurora 开关总默认（managed key，Rule AURORA-CONFIG 校验两侧一致）
    AURORA_DEFAULT_MODE: str = "live"
    ENABLE_EXPERT_ENTRY: bool = True
    # V3-FIX-231：独立开关 ENABLE_VISUAL_ELEMENTS 已删——visual-elements 闸唯一
    # 权威=RELEASE_ENABLE_VISUAL_ELEMENTS（上方 Release scope flags 五旗分节，
    # /release-flags 契约同源），双权威脑裂禁绝；闸仍只挂组注册级（T36 教训）。
    ENABLE_UNIFIED_GRAPH_ROUTING: bool = True
    ENABLE_EXPERT_STRATEGY_V1: bool = True
    ENABLE_SESSION_FEEDBACK_ADAPTATION: bool = True
    ENABLE_ADAPTIVE_PRESENTATION: bool = True
    ENABLE_STRUCTURED_NEXT_ACTIONS: bool = True
    ENABLE_BLOCKED_TEMPERATURE: bool = True
    ENABLE_UX_PRESENTATION_METADATA: bool = True
    ENABLE_PERCEPTIBLE_INTELLIGENCE: bool = True
    ENABLE_PROACTIVE_INSIGHTS: bool = True
    ENABLE_PLAN_REASONING_SUMMARY: bool = True
    ENABLE_WEEKLY_LEARNING_REPORT: bool = True
    ENABLE_PROGRESS_COMPARISONS: bool = True
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
    EVENT_BUS_PUBLISH_BASE_DELAY_MS: int = 200
    EVENT_BUS_PUBLISH_MAX_DELAY_MS: int = 2000
    EVENT_BUS_DLQ_SUFFIX: str = ":dlq"
    EVENT_BUS_STREAM_MAXLEN: int = 50000  # Soft cap for primary/retry Redis streams
    EVENT_BUS_RETRY_STREAM_MAXLEN: int = 50000  # Prevent retry storms from growing streams unbounded
    EVENT_BUS_DLQ_MAXLEN: int = 10000  # Maximum messages in DLQ before trimming
    EVENT_BUS_DLQ_ENABLED: bool = True
    EVENT_BUS_PENDING_RETRY_IDLE_MS: int = 5000

    # FSM context guardrails
    MAX_CONTEXT_DATA_KEYS: int = 200
    MAX_CONTEXT_DATA_VALUE_BYTES: int = 10 * 1024

    # Translation Service
    TRANSLATION_DAILY_CARD_LIMIT: int = 20  # Max vocabulary cards created per day from translation

    # gRPC Server
    GRPC_PORT: int = 50051
    GRPC_ENABLE_REFLECTION: bool = False
    GRPC_REQUIRE_TLS: bool | None = None
    GRPC_TLS_CERT_PATH: str = ""
    GRPC_TLS_KEY_PATH: str = ""
    GRPC_TLS_CA_CERT_PATH: str = ""  # P2-28: For mTLS client verification

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
    def CONTEXT_SEMANTIC_GATING_RULES(self) -> dict[str, dict[str, float | int]]:
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
        rbac_database_url = self._service_database_url()
        if rbac_database_url:
            self.DATABASE_URL = normalize_database_url(rbac_database_url)
        elif not self.DATABASE_URL:
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

    def _service_database_url(self) -> str:
        if not self.SPARKLE_RBAC_ENABLED:
            return ""
        role = (self.SERVICE_ROLE or "").strip().lower()
        if role in {"celery", "celery-glm-batch", "worker", "beat"}:
            return self.SPARKLE_CELERY_DATABASE_URL or self.SPARKLE_ENGINE_DATABASE_URL
        return self.SPARKLE_ENGINE_DATABASE_URL

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

        # P1-8: RBAC must be enabled in production
        if env in ("prod", "production") and not self.SPARKLE_RBAC_ENABLED:
            raise ValueError("SPARKLE_RBAC_ENABLED must be True in production")

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

        if self.EMAIL_ENABLED is None:
            self.EMAIL_ENABLED = env in ("prod", "production")

        if env in ("prod", "production"):
            production_url = (self.PRODUCTION_URL or "").strip().rstrip("/")
            if not production_url:
                raise ValueError("PRODUCTION_URL must be set in production for HTTPS links and CORS")
            parsed_production_url = urlparse(production_url)
            if parsed_production_url.scheme != "https" or not parsed_production_url.netloc:
                raise ValueError("PRODUCTION_URL must be an HTTPS URL in production")
            self.PRODUCTION_URL = production_url

            cors_origins = [origin.strip().rstrip("/") for origin in self.BACKEND_CORS_ORIGINS if origin.strip()]
            if not cors_origins:
                cors_origins = [production_url]
            if "*" in cors_origins:
                raise ValueError("BACKEND_CORS_ORIGINS cannot include '*' in production")
            for origin in cors_origins:
                parsed_origin = urlparse(origin)
                if parsed_origin.scheme != "https" or not parsed_origin.netloc:
                    raise ValueError("BACKEND_CORS_ORIGINS must contain only HTTPS origins in production")
            self.BACKEND_CORS_ORIGINS = cors_origins

        # Production secret validation: critical credentials must not be empty
        if env in ("prod", "production"):
            _placeholder_prefixes = ("your_", "replace_with", "changeme")
            _critical_secrets = {
                "SECRET_KEY": self.SECRET_KEY,
                "POSTGRES_PASSWORD": self.POSTGRES_PASSWORD,
                "REDIS_PASSWORD": self.REDIS_PASSWORD,
                "INTERNAL_API_KEY": self.INTERNAL_API_KEY,
                "MINIO_ACCESS_KEY": self.MINIO_ACCESS_KEY,
                "MINIO_SECRET_KEY": self.MINIO_SECRET_KEY,
            }
            for _name, _val in _critical_secrets.items():
                if not _val or any(_val.startswith(p) for p in _placeholder_prefixes):
                    raise ValueError(f"{_name} must be set to a real value in production (not empty or placeholder)")

            _llm_keys = {
                "LLM_API_KEY": self.LLM_API_KEY,
                "DASHSCOPE_API_KEY": self.DASHSCOPE_API_KEY,
                "ZHIPU_API_KEY": self.ZHIPU_API_KEY,
                "DEEPSEEK_API_KEY": self.DEEPSEEK_API_KEY,
            }
            _has_any_llm = any(
                v and not any(v.startswith(p) for p in _placeholder_prefixes) for v in _llm_keys.values()
            )
            if not _has_any_llm:
                raise ValueError(
                    "At least one LLM API key must be set in production (LLM_API_KEY, DASHSCOPE_API_KEY, ZHIPU_API_KEY, or DEEPSEEK_API_KEY)"
                )

            if self.EMAIL_ENABLED:
                _required_email = {
                    "SMTP_HOST": self.SMTP_HOST,
                    "SMTP_USER": self.SMTP_USER,
                    "SMTP_PASSWORD": self.SMTP_PASSWORD,
                    "EMAIL_FROM": self.EMAIL_FROM,
                }
                for _name, _val in _required_email.items():
                    if not _val or any(_val.startswith(p) for p in _placeholder_prefixes):
                        raise ValueError(f"{_name} must be set when EMAIL_ENABLED=true in production")
                if self.SMTP_PORT < 1 or self.SMTP_PORT > 65535:
                    raise ValueError("SMTP_PORT must be a valid TCP port")

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

        self.MINIMAX_MAX_CONCURRENCY = max(1, int(self.MINIMAX_MAX_CONCURRENCY or 8))
        # DIST-SEMAPHORE：RPM 预算非负（0 = 禁用回滚位；负值视为未配置）
        self.MINIMAX_RPM_BUDGET = max(0, int(self.MINIMAX_RPM_BUDGET or 0))

        return self


# Create global settings instance
settings = Settings()
