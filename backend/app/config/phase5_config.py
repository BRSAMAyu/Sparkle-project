"""
Phase 5 Configuration - Stability & Evolution
稳定性护栏和文档引擎的配置参数
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), ".env")


class Phase5Config(BaseSettings):
    """Phase 5 特定配置"""

    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra="ignore",
        env_prefix="PHASE5_"  # 所有配置项都以 PHASE5_ 开头
    )

    # ==========================================
    # RAG & HyDE Configuration
    # ==========================================

    # HyDE 策略开关
    HYDE_ENABLED: bool = True

    # HyDE Gate: 仅在查询长度小于此阈值时启用 HyDE
    HYDE_QUERY_LENGTH_THRESHOLD: int = 100

    # HyDE 生成超时（秒）- 延迟预算
    HYDE_LATENCY_BUDGET_SEC: float = 1.5

    # HyDE 生成提示词最大长度
    HYDE_PROMPT_MAX_WORDS: int = 50

    # RAG 检索数量（Raw）
    RAG_RAW_RETRIEVAL_LIMIT: int = 3

    # RAG 检索数量（HyDE）
    RAG_HYDE_RETRIEVAL_LIMIT: int = 3

    # RAG 最终合并结果上限
    RAG_MERGE_RESULT_LIMIT: int = 5

    # ==========================================
    # Circuit Breaker Configuration
    # ==========================================

    # 熔断器失败阈值（1分钟窗口内）
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5

    # 熔断器恢复超时（秒）
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 30

    # 熔断器失败窗口（秒）
    CIRCUIT_BREAKER_FAILURE_WINDOW: int = 60

    # ==========================================
    # SSE Configuration
    # ==========================================

    # SSE 事件缓冲区大小（每个用户保留最近N条事件）
    SSE_BUFFER_SIZE: int = 100

    # SSE 事件缓冲区 TTL（秒）
    SSE_BUFFER_TTL: int = 60

    # SSE 重放最大事件数（防止过大的重放）
    SSE_REPLAY_MAX_EVENTS: int = 50

    # ==========================================
    # Document Quality Gate Configuration
    # ==========================================

    # 质量检测：乱码率阈值（0.0-1.0）
    DOC_QUALITY_GARBLED_THRESHOLD: float = 0.05

    # 质量检测：最小内容长度（字符数）
    DOC_QUALITY_MIN_LENGTH: int = 20

    # 质量检测：最大乱码连续字符数
    DOC_QUALITY_MAX_CONSECUTIVE_GARBLED: int = 10

    # 质量检测：数学符号白名单（允许的特殊字符范围）
    DOC_QUALITY_MATH_SYMBOLS_ALLOWED: bool = True

    # 质量检测：中文字符最小比例（针对中文文档）
    DOC_QUALITY_CHINESE_MIN_RATIO: float = 0.3

    # 质量检测：置信度阈值（OCR）
    DOC_QUALITY_OCR_CONFIDENCE_THRESHOLD: float = 0.7

    # ==========================================
    # Document Processing Pipeline
    # ==========================================

    # Pipeline 版本（用于追溯）
    DOC_PIPELINE_VERSION: str = "v1.0.0"

    # 是否自动生成草稿知识节点
    DOC_AUTO_DRAFT_NODES: bool = True

    # 草稿节点最大数量（防止爆炸）
    DOC_MAX_DRAFT_NODES: int = 100

    # 切片最大页码跨度（防止单个切片跨越过多页）
    DOC_CHUNK_MAX_PAGE_SPAN: int = 3

    # ==========================================
    # OCR Configuration
    # ==========================================

    # OCR 提供商
    OCR_PROVIDER: str = "deepseek"  # "deepseek" | "tesseract" | "paddle"

    # OCR API 超时（秒）
    OCR_TIMEOUT: int = 30

    # OCR 最大重试次数
    OCR_MAX_RETRIES: int = 2

    # ==========================================
    # Deletion Cascade Configuration
    # ==========================================

    # 软删除 vs 硬删除
    DELETION_SOFT_DELETE: bool = True

    # 软删除标记保留时间（天）
    DELETION_RETENTION_DAYS: int = 30

    # 是否级联删除草稿节点
    DELETION_CASCADE_DRAFT_NODES: bool = True

    # 是否级联删除向量索引
    DELETION_CASCADE_EMBEDDINGS: bool = True

    # ==========================================
    # Observability & Metrics
    # ==========================================

    # 是否启用详细指标
    METRICS_DETAILED_ENABLED: bool = True

    # 指标收集间隔（秒）
    METRICS_COLLECT_INTERVAL: int = 60

    # 是否记录 HyDE 性能指标
    METRICS_HYDE_PERF: bool = True

    # 是否记录熔断器状态
    METRICS_CIRCUIT_BREAKER_STATE: bool = True


# 创建全局实例
phase5_config = Phase5Config()


# ==========================================
# 便利函数：获取文档类型特定配置
# ==========================================

def get_quality_threshold_for_doc_type(doc_type: str) -> float:
    """
    根据文档类型返回适当的质量阈值

    Args:
        doc_type: "academic" | "invoice" | "general" | "code"

    Returns:
        float: 乱码率阈值
    """
    thresholds = {
        "academic": 0.08,  # 学术论文允许更多数学符号
        "invoice": 0.02,   # 发票要求严格
        "general": 0.05,   # 通用文档
        "code": 0.15,      # 代码文件允许更多特殊字符
    }
    return thresholds.get(doc_type, phase5_config.DOC_QUALITY_GARBLED_THRESHOLD)


def get_rag_config() -> dict:
    """获取 RAG 相关配置的字典"""
    return {
        "hyde_enabled": phase5_config.HYDE_ENABLED,
        "hyde_threshold": phase5_config.HYDE_QUERY_LENGTH_THRESHOLD,
        "hyde_timeout": phase5_config.HYDE_LATENCY_BUDGET_SEC,
        "raw_limit": phase5_config.RAG_RAW_RETRIEVAL_LIMIT,
        "hyde_limit": phase5_config.RAG_HYDE_RETRIEVAL_LIMIT,
        "merge_limit": phase5_config.RAG_MERGE_RESULT_LIMIT,
    }


def get_circuit_breaker_config() -> dict:
    """获取熔断器配置的字典"""
    return {
        "failure_threshold": phase5_config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        "recovery_timeout": phase5_config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        "failure_window": phase5_config.CIRCUIT_BREAKER_FAILURE_WINDOW,
    }
