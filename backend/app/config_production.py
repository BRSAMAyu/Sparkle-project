"""
生产级配置管理

增强特性:
1. ✅ 环境变量支持 (优先级最高)
2. ✅ 配置验证 (启动时检查)
3. ✅ 敏感信息脱敏 (日志输出)
4. ✅ 默认值和类型转换
5. ✅ 配置分组 (核心、性能、安全)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator, PostgresDsn, RedisDsn
from loguru import logger
import os


class ProductionSettings(BaseSettings):
    """
    生产级配置

    所有配置都可以通过环境变量设置，例如:
    - APP_NAME -> APP_NAME
    - DATABASE_URL -> DATABASE_URL
    - REDIS_URL -> REDIS_URL
    """

    # ==================== 核心配置 ====================
    APP_NAME: str = Field(default="Sparkle", env="APP_NAME")
    APP_VERSION: str = Field(default="0.3.0", env="APP_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # ==================== 网络配置 ====================
    GRPC_PORT: int = Field(default=50051, env="GRPC_PORT")
    HTTP_PORT: int = Field(default=8000, env="HTTP_PORT")
    GATEWAY_PORT: int = Field(default=8080, env="GATEWAY_PORT")

    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["*"],
        env="BACKEND_CORS_ORIGINS"
    )

    # ==================== 数据库配置 ====================
    DATABASE_URL: PostgresDsn = Field(
        ...,
        env="DATABASE_URL",
        description="PostgreSQL connection URL"
    )

    # 连接池配置
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=30, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")

    # ==================== Redis 配置 ====================
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )

    # Redis 连接配置
    REDIS_POOL_SIZE: int = Field(default=50, env="REDIS_POOL_SIZE")
    REDIS_SOCKET_TIMEOUT: float = Field(default=5.0, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(default=5.0, env="REDIS_SOCKET_CONNECT_TIMEOUT")

    # ==================== LLM 配置 ====================
    LLM_PROVIDER: str = Field(default="deepseek", env="LLM_PROVIDER")
    LLM_API_BASE_URL: str = Field(..., env="LLM_API_BASE_URL")
    LLM_API_KEY: str = Field(..., env="LLM_API_KEY")
    LLM_MODEL_NAME: str = Field(default="deepseek-chat", env="LLM_MODEL_NAME")
    LLM_TIMEOUT: int = Field(default=60, env="LLM_TIMEOUT")

    # ==================== 安全配置 ====================
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRE_MINUTES: int = Field(default=1440, env="JWT_EXPIRE_MINUTES")  # 24小时

    # 密码哈希强度
    PASSWORD_HASH_ROUNDS: int = Field(default=12, env="PASSWORD_HASH_ROUNDS")

    # ==================== 性能配置 ====================
    # 并发控制
    MAX_CONCURRENT_SESSIONS: int = Field(default=100, env="MAX_CONCURRENT_SESSIONS")
    MAX_REQUESTS_PER_MINUTE: int = Field(default=1000, env="MAX_REQUESTS_PER_MINUTE")

    # 熔断器配置
    CIRCUIT_BREAKER_THRESHOLD: int = Field(default=5, env="CIRCUIT_BREAKER_THRESHOLD")
    CIRCUIT_BREAKER_TIMEOUT: int = Field(default=60, env="CIRCUIT_BREAKER_TIMEOUT")

    # ContextPruner 配置
    CONTEXT_PRUNER_MAX_HISTORY: int = Field(default=10, env="CONTEXT_PRUNER_MAX_HISTORY")
    CONTEXT_PRUNER_SUMMARY_THRESHOLD: int = Field(default=20, env="CONTEXT_PRUNER_SUMMARY_THRESHOLD")
    CONTEXT_PRUNER_CACHE_TTL: int = Field(default=3600, env="CONTEXT_PRUNER_CACHE_TTL")

    # Token 配额
    DAILY_QUOTA: int = Field(default=100000, env="DAILY_QUOTA")

    # ==================== 业务配置 ====================
    # 推送系统
    PUSH_CYCLE_MINUTES: int = Field(default=15, env="PUSH_CYCLE_MINUTES")
    PUSH_DAILY_CAP: int = Field(default=5, env="PUSH_DAILY_CAP")

    # 知识拓展
    EXPANSION_WORKER_INTERVAL: int = Field(default=60, env="EXPANSION_WORKER_INTERVAL")
    EXPANSION_MAX_NODES: int = Field(default=5, env="EXPANSION_MAX_NODES")

    # 遗忘曲线
    DECAY_HALF_LIFE_DAYS: float = Field(default=7.0, env="DECAY_HALF_LIFE_DAYS")

    # ==================== 日志配置 ====================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    LOG_RETENTION_DAYS: int = Field(default=7, env="LOG_RETENTION_DAYS")

    # ==================== 监控配置 ====================
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    ENABLE_TRACING: bool = Field(default=True, env="ENABLE_TRACING")

    # ==================== 存储配置 ====================
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, env="MAX_UPLOAD_SIZE_MB")

    # ==================== 缓存配置 ====================
    CACHE_TTL_DEFAULT: int = Field(default=3600, env="CACHE_TTL_DEFAULT")
    CACHE_TTL_SHORT: int = Field(default=300, env="CACHE_TTL_SHORT")
    CACHE_TTL_LONG: int = Field(default=86400, env="CACHE_TTL_LONG")

    # ==================== 验证器 ====================
    @validator("APP_NAME")
    def validate_app_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("APP_NAME cannot be empty")
        return v

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v

    @validator("LLM_API_KEY")
    def validate_llm_key(cls, v):
        if len(v) < 10:
            raise ValueError("LLM_API_KEY appears to be invalid")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v

    # ==================== 配置验证 ====================
    def validate_all(self) -> Dict[str, Any]:
        """
        验证所有配置并返回报告

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 检查生产环境关键配置
        if not self.DEBUG:
            if self.SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
                errors.append("SECRET_KEY must be changed in production")

        # 检查性能配置合理性
        if self.MAX_CONCURRENT_SESSIONS > 1000:
            warnings.append("Very high MAX_CONCURRENT_SESSIONS may cause resource issues")

        if self.CIRCUIT_BREAKER_THRESHOLD < 3:
            warnings.append("Very low circuit breaker threshold may cause frequent outages")

        # 检查 Redis 配置
        if self.REDIS_POOL_SIZE < 10:
            warnings.append("Low Redis pool size may limit concurrency")

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "app": f"{self.APP_NAME} v{self.APP_VERSION}",
                "environment": "production" if not self.DEBUG else "development",
                "features": {
                    "metrics": self.ENABLE_METRICS,
                    "tracing": self.ENABLE_TRACING,
                    "circuit_breaker": True,
                    "context_pruner": True,
                    "token_tracker": True,
                }
            }
        }

        return result

    def get_safe_config(self) -> Dict[str, Any]:
        """
        获取脱敏后的配置（用于日志输出）

        Returns:
            脱敏配置
        """
        config = self.dict()

        # 脱敏敏感信息
        sensitive_keys = [
            "SECRET_KEY", "LLM_API_KEY", "DATABASE_URL", "REDIS_URL"
        ]

        for key in sensitive_keys:
            if key in config:
                value = config[key]
                if value:
                    if key == "SECRET_KEY":
                        config[key] = value[:4] + "***" + value[-4:]
                    elif key == "LLM_API_KEY":
                        config[key] = "***" + value[-4:]
                    elif key in ["DATABASE_URL", "REDIS_URL"]:
                        # 保留协议和主机，隐藏密码
                        if "@" in value:
                            parts = value.split("@")
                            if len(parts) == 2:
                                config[key] = parts[0].split(":")[0] + "://***@" + parts[1]

        return config

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 单例实例
_settings: Optional[ProductionSettings] = None


def get_settings() -> ProductionSettings:
    """
    获取配置单例

    Returns:
        ProductionSettings 实例
    """
    global _settings

    if _settings is None:
        try:
            _settings = ProductionSettings()

            # 验证配置
            validation = _settings.validate_all()

            if not validation["valid"]:
                logger.error(f"Configuration validation failed: {validation['errors']}")
                raise ValueError("Invalid configuration")

            if validation["warnings"]:
                logger.warning(f"Configuration warnings: {validation['warnings']}")

            # 日志输出安全配置
            safe_config = _settings.get_safe_config()
            logger.info(f"Configuration loaded: {safe_config}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    return _settings


# 向后兼容别名
settings = get_settings()


# 配置检查脚本
def check_config():
    """配置检查工具"""
    print("=" * 60)
    print("Configuration Check")
    print("=" * 60)

    try:
        settings = get_settings()
        validation = settings.validate_all()

        print(f"✅ Valid: {validation['valid']}")
        print(f"📊 Environment: {'PRODUCTION' if not settings.DEBUG else 'DEVELOPMENT'}")

        if validation['errors']:
            print("\n❌ Errors:")
            for error in validation['errors']:
                print(f"  - {error}")

        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")

        print("\n✅ Summary:")
        summary = validation['summary']
        print(f"  App: {summary['app']}")
        print(f"  Environment: {summary['environment']}")
        print(f"  Features: {', '.join([k for k, v in summary['features'].items() if v])}")

        print("\n" + "=" * 60)
        return validation['valid']

    except Exception as e:
        print(f"\n❌ Configuration check failed: {e}")
        return False


if __name__ == "__main__":
    check_config()
