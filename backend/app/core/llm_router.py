"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

"""
LLM Router - 统一的LLM客户端获取入口

职责：
1. 根据 AgentProfile 选择合适的模型
2. 统一封装 OpenAICompatibleProvider 和 LangChain ChatModel
3. 支持任务级动态模型切换
4. 提供模型降级策略

设计原则：
- 单一入口：所有LLM请求通过此类
- 可观测：记录每次选择的模型和原因
- 可降级：主模型失败时自动降级
"""

import math
import threading
import time
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger

from app.config import settings
from app.core import complexity_analyzer as _cx
from app.core import routing_audit
from app.core.adaptive_routing import adaptive_routing_engine
from app.core.agent_profiles import TASK_TO_AGENT_PROFILE, AgentRole, ModelTier, TaskType, agent_profile_registry
from app.core.entitlement import request_tier_label
from app.core.metrics import (
    LLM_ROUTER_ESTIMATED_COST_PER_1K,
    LLM_ROUTER_FREE_TIER_DOWNGRADE_TOTAL,
    LLM_ROUTER_SELECTION_TOTAL,
)


class ModelProvider(StrEnum):
    """支持的LLM提供商"""
    XIAOMI = "xiaomi"      # XiaoMi MIMO (快速响应)
    DEEPSEEK = "deepseek"  # DeepSeek (核心模型)
    ZHIPU = "zhipu"        # Zhipu GLM (编程/工具)
    HUNYUAN = "hunyuan"    # Hunyuan Translation
    DASHSCOPE = "dashscope"  # Aliyun DashScope (通义千问)
    SILICONFLOW = "siliconflow"  # SiliconFlow (专家模型：OCR、翻译等)
    MINIMAX = "minimax"    # MiniMax M3 (异步分析车道：仅 GLM_BATCH 池，永不进主聊天能力层)


# ============================================
# 请求级用户分层信号（免费层模型降级）
# ============================================
# 由引擎 gRPC 入口（agent_grpc_service.StreamChat）按 ChatRequest.user_profile.is_pro
# 设置（网关已在 chatflow 中填充，真源 users.entitlement——O-04：flame_level 永不参与），
# 进程内透传给 LLM 路由做 tier 钳制，并向 metrics 提供有界 plan 维度
# （free/pro/unknown，core/entitlement.request_tier_label）；
# 未设置的调用面（内部批量/定时任务/测试）保持现状不钳制。

_REQUEST_USER_TIER: ContextVar[str | None] = ContextVar("sparkle_request_user_tier", default=None)


def set_request_user_tier(tier: str | None) -> Token:
    """标记当前请求的用户分层（"free" / "pro"），供 llm_router 钳制读取。"""
    normalized = str(tier).strip().lower() if tier else None
    return _REQUEST_USER_TIER.set(normalized or None)


def get_request_user_tier() -> str | None:
    """读取当前请求用户分层；未标记时返回 None（不钳制）。"""
    return _REQUEST_USER_TIER.get()


def reset_request_user_tier(token: Token) -> None:
    """按 set 返回的 token 复位分层标记（请求结束 hygiene）。"""
    _REQUEST_USER_TIER.reset(token)


# 能力层排序（高→低，数值越小越重）。免费层钳制只作用于这些 tier；
# FREE*/GLM_BATCH/SPECIALIST 等非直出能力层保持原路由。
_CAPABILITY_TIER_RANK: dict[ModelTier, int] = {
    ModelTier.TOP: 0,
    ModelTier.MAX: 1,
    ModelTier.PRO: 2,
    ModelTier.PLUS: 3,
    ModelTier.STANDARD: 4,
    ModelTier.FAST: 5,
}


# ============================================
# GLM 车道 thinking 控制 + max_tokens 留量（V3-FIX-04）
# 依据 B-05b 直连实测（v3-output/B-05/SUPPLEMENT_KEY_ROTATED.md）：
# - coding 端点（/api/coding/paas/v4）是唯一支持 `thinking:{"type":"disabled"}`
#   真关闭思考的通道；标准端点（/api/paas/v4）对该参数返 400 code 1210
#   （"该模型始终思考"）。
# - clear_thinking 是客户端侧概念，智谱静默忽略（不报错也不关思考）。
# - 思考吃掉 completion 预算 84-88%：显式 max_tokens=1024 可被思考清空，
#   用户收到空回复（finish=length）。
# ============================================

_ZHIPU_CODING_ENDPOINT_MARK = "/api/coding/"
# glm-5.3-flash 实测思考占 completion 预算比例的上界（实测 84-88%）
_GLM_WORST_THINKING_SHARE = 0.88
# 保护目标：最坏思考占比下，可见输出仍 ≥ 配置值的 15%
_GLM_MIN_VISIBLE_SHARE = 0.15


def is_zhipu_coding_endpoint(base_url: str) -> bool:
    """判断 base_url 是否为智谱 coding 端点（唯一支持关闭思考的通道）。"""
    return _ZHIPU_CODING_ENDPOINT_MARK in (base_url or "").lower()


def glm_thinking_disabled_on_wire(
    provider: ModelProvider,
    base_url: str,
    clear_thinking: bool | None,
) -> bool:
    """该候选在线上请求是否会附带 `thinking:{"type":"disabled"}`。

    仅 coding 端点 + clear_thinking=True 时为 True：标准端点发该参数会 400，
    clear_thinking=False 的思考车道保持默认思考行为。
    """
    return provider == ModelProvider.ZHIPU and bool(clear_thinking) and is_zhipu_coding_endpoint(base_url)


def glm_effective_max_tokens(
    provider: ModelProvider,
    base_url: str,
    clear_thinking: bool | None,
    requested: int | None,
) -> int | None:
    """GLM 车道 max_tokens 留量保护。

    思考仍会进行的车道（标准端点，或 clear_thinking=False）按最坏 88% 思考占比
    上浮请求值：effective = ceil(requested * 15% / (1 - 88%))，保证思考吃掉预算后
    可见输出仍 ≥ 配置值的 15%（1024 → 1280），避免空回复（finish=length）。
    思考已关闭（coding 端点 + clear_thinking=True）或非 zhipu → 原样返回。
    """
    if provider != ModelProvider.ZHIPU or requested is None or requested <= 0:
        return requested
    if glm_thinking_disabled_on_wire(provider, base_url, clear_thinking):
        return requested
    return math.ceil(requested * _GLM_MIN_VISIBLE_SHARE / (1 - _GLM_WORST_THINKING_SHARE))


# ============================================
# DashScope（通义千问）车道思考控制（TTFT-CFG）
# ============================================
# TTFT-PROBE 簇 B 根因：qwen3 混合模型流式下默认先思考后作答（reasoning 13-43s），
# DashScope 兼容模式的思考开关是 `enable_thinking`；引擎此前发的 GLM 风格
# `thinking:{"type":…}` 对其无效——主聊天档位思考从未被显式关闭（探针 M6：fast 档
# 不发参数仍流 reasoning，首块 356ms 即 reasoning，TTFT 33.4s）。
# 产品裁决（2026-09 主会话）：
# - FAST/STANDARD/PLUS（聊天主链路直出层，tier 池首均 dashscope_*）显式关思考；
#   PLUS 层注册语义即"非思考"（dashscope_chat=qwen3.7-plus 非思考），随主链路一并关。
# - PRO/MAX/TOP（深度分析层）保留思考：不注入参数（provider 默认思考开，流式），
#   reasoning_mode 显式要求深思考的调用经 router 落到这些层即自然保持开启。
# - GLM 车道 thinking:{} 现有发送保留：按 provider 分叉，不是全局替换。

_DASHSCOPE_THINKING_OFF_TIERS: frozenset[ModelTier] = frozenset(
    {ModelTier.FAST, ModelTier.STANDARD, ModelTier.PLUS}
)


def dashscope_enable_thinking_param(tier: ModelTier, thinking_mode: str | None) -> bool | None:
    """DashScope 车道应在线上注入的 enable_thinking 三态（TTFT-CFG）。

    返回 False = 显式注入关闭（FAST/STANDARD/PLUS 主聊天直出层）；
    返回 None  = 不注入该参数（PRO/MAX/TOP 保留思考走 provider 默认，其余层维持原状）。
    仅 provider=DASHSCOPE 的装配点调用；其他 provider 维持原 GLM 风格分支。
    本函数永不返回 True：思考保留层靠"不注入+模型默认"表达，避免对
    非流式/非混合模型注入 enable_thinking=true 触发 400。
    """
    if tier in _DASHSCOPE_THINKING_OFF_TIERS:
        return False
    return None


@dataclass
class ModelConfig:
    """模型配置"""
    provider: ModelProvider
    model_name: str
    base_url: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int | None = None
    # GLM 特有参数
    clear_thinking: bool | None = None  # False=保留式思考(适合Coding/Agent), True=None=默认
    # MIMO 特有参数
    enable_web_search: bool = False     # 启用内置联网搜索
    thinking_mode: str | None = None    # "enabled" | "disabled" | None
    # 成本/性能指标
    tier: ModelTier = ModelTier.STANDARD
    cost_per_1k_tokens: float = 0.001
    avg_latency_ms: float = 500


@dataclass
class ModelHealthState:
    """模型健康状态（内存缓存，无持久化）— E-07 三相滞回状态机。

    phase 封闭集：
    - healthy:   正常。连续 FAILURE_THRESHOLD 次失败 → unhealthy。
    - unhealthy: 路由跳过（is_healthy=False）。冷却 cooldown_seconds 无新失败
                 → probation。**此相内的 record_success 不复活**（在途旧请求的
                 成功不能解除熔断——滞回核心，防 provider 抖动引发切换风暴）。
    - probation: 恢复观察（is_healthy=True，可与健康模型同权参与选型=冷却后的
                 自然回切）。此相内 1 次失败立即回 unhealthy 且冷却翻倍（封顶
                 COOLDOWN_MAX_SECONDS，有界不无界退避）；连续 PROBE_SUCCESS_THRESHOLD
                 次成功 → healthy（恢复完整失败容错，冷却复位）。

    兼容性：is_healthy 字段保留原语义（False=路由必跳过；True=可选），现有
    E-02 消费面零改动；新增 phase 表达三相。
    """

    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_at: float | None = None
    is_healthy: bool = True
    phase: str = "healthy"  # "healthy" | "probation" | "unhealthy"
    cooldown_seconds: float | None = None  # None = 取 settings 默认

    FAILURE_THRESHOLD: int = field(default=5)
    RECOVERY_SECONDS: float = field(default=300.0)
    PROBE_SUCCESS_THRESHOLD: int = field(default=3)
    COOLDOWN_MAX_SECONDS: float = field(default=1800.0)

    def __post_init__(self) -> None:
        # 默认值以 settings 为准（测试/部署可调）；显式传参优先。
        self.FAILURE_THRESHOLD = int(
            getattr(settings, "LLM_HEALTH_FAILURE_THRESHOLD", self.FAILURE_THRESHOLD)
        )
        self.RECOVERY_SECONDS = float(
            getattr(settings, "LLM_HEALTH_RECOVERY_SECONDS", self.RECOVERY_SECONDS)
        )
        self.PROBE_SUCCESS_THRESHOLD = int(
            getattr(settings, "LLM_HEALTH_PROBE_SUCCESS_THRESHOLD", self.PROBE_SUCCESS_THRESHOLD)
        )
        self.COOLDOWN_MAX_SECONDS = float(
            getattr(settings, "LLM_HEALTH_COOLDOWN_MAX_SECONDS", self.COOLDOWN_MAX_SECONDS)
        )
        if self.cooldown_seconds is None:
            self.cooldown_seconds = self.RECOVERY_SECONDS

    def _transition(self, new_phase: str) -> None:
        from app.core.metrics import LLM_HEALTH_TRANSITIONS_TOTAL

        old = self.phase
        self.phase = new_phase
        self.is_healthy = new_phase != "unhealthy"
        if old != new_phase:
            LLM_HEALTH_TRANSITIONS_TOTAL.labels(
                model_key=getattr(self, "_model_key", "unknown"),
                transition=f"{old}->{new_phase}",
            ).inc()

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_at = time.monotonic()
        if self.phase == "probation":
            # 恢复观察期内失败：立即回 unhealthy，冷却翻倍（防风暴滞回；有界封顶）
            self.cooldown_seconds = min(
                self.cooldown_seconds * 2.0, self.COOLDOWN_MAX_SECONDS
            )
            self._transition("unhealthy")
            logger.warning(
                f"Model failed during probation, back to unhealthy "
                f"(cooldown escalated to {self.cooldown_seconds:.0f}s)"
            )
        elif self.consecutive_failures >= self.FAILURE_THRESHOLD:
            self._transition("unhealthy")
            logger.warning(
                f"Model marked unhealthy after {self.consecutive_failures} consecutive failures"
            )

    def record_success(self) -> None:
        if self.phase == "unhealthy":
            # 滞回：unhealthy 期间在途旧请求的成功不解除熔断，等待冷却走完
            return
        if self.phase == "probation":
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.PROBE_SUCCESS_THRESHOLD:
                self.consecutive_failures = 0
                self.cooldown_seconds = self.RECOVERY_SECONDS
                self._transition("healthy")
                logger.info("Model recovered to healthy after probation probe successes")
            return
        # healthy：单次成功清零失败计数（E-02 既有行为）
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    def check_recovery(self) -> None:
        """unhealthy → probation（冷却到期、无新失败）。probation/healthy 不变。"""
        if self.phase == "unhealthy" and self.last_failure_at is not None:
            if time.monotonic() - self.last_failure_at >= self.cooldown_seconds:
                self.consecutive_failures = 0
                self.consecutive_successes = 0
                self._transition("probation")
                logger.info(
                    f"Model entered probation after cooldown ({self.cooldown_seconds:.0f}s)"
                )


@dataclass
class LLMSelection:
    """LLM选择结果（可观测）"""
    model_key: str
    config: ModelConfig
    agent_role: AgentRole
    task_type: TaskType | None
    reason: str  # 选择此模型的原因（含成本信息）
    is_fallback: bool = False
    estimated_cost_per_1k: float = 0.0
    tier_used: str = ""
    free_tier_downgrade: bool = False  # 免费层钳制触发标记（reason 含 free_tier_downgrade）


class LLMRouter:
    """
    统一的LLM路由器

    根据 AgentProfile 和 TaskType 选择最合适的模型。
    同时兼容主系统（llm_service）和 LangGraph（llm_factory）。
    """

    # Tier 降级顺序（从高到低成本）
    _FALLBACK_TIER_ORDER: list[ModelTier] = [
        ModelTier.TOP,
        ModelTier.MAX,
        ModelTier.PRO,
        ModelTier.PLUS,
        ModelTier.STANDARD,
        ModelTier.FAST,
        ModelTier.FREE_FAST,
        ModelTier.REASONING,
        ModelTier.FREE_REASONING,
        ModelTier.GLM_BATCH,
        ModelTier.SPECIALIST,
    ]

    def __init__(self):
        self._lock = threading.RLock()
        self._available_models: dict[str, ModelConfig] = {}
        self._tier_mapping: dict[ModelTier, list[str]] = {}
        self._model_health: dict[str, ModelHealthState] = {}
        self._load_model_configs()

    def register_model_configs(self, configs: dict[str, ModelConfig], tier_mapping: dict[ModelTier, list[str]] | None = None):
        """
        运行时注册/更新模型配置。

        Args:
            configs: 以模型key为索引的配置字典
            tier_mapping: 可选，更新层级映射
        """
        with self._lock:
            self._available_models.update(configs)
            if tier_mapping:
                self._tier_mapping = tier_mapping
            agent_profile_registry.register_model_configs(configs)
        logger.info(f"LLMRouter updated with {len(configs)} model configs")

    @staticmethod
    def _normalize_reasoning_mode(value: str | None) -> str:
        normalized = str(value or "balanced").strip().lower()
        if normalized in {"fast", "balanced", "deep"}:
            return normalized
        return "balanced"

    @staticmethod
    def _normalize_tier_value(tier: ModelTier) -> ModelTier:
        if tier == ModelTier.REASONING:
            return ModelTier.PRO
        if tier == ModelTier.FREE_REASONING:
            return ModelTier.FREE_FAST
        return tier

    # ============================================
    # 免费层模型降级（free_tier_downgrade）
    # ============================================

    def _free_tier_ceiling(self) -> tuple[ModelTier, int] | None:
        """返回免费层允许的最高能力 tier 及其 rank；开关关闭时返回 None。"""
        if not getattr(settings, "FREE_TIER_DOWNGRADE_ENABLED", True):
            return None
        raw = str(getattr(settings, "FREE_TIER_MODEL_CEILING", "fast") or "fast").strip().lower()
        try:
            ceiling = ModelTier(raw)
        except ValueError:
            logger.warning(f"Invalid FREE_TIER_MODEL_CEILING={raw!r}, falling back to 'fast'")
            ceiling = ModelTier.FAST
        ceiling = self._normalize_tier_value(ceiling)
        rank = _CAPABILITY_TIER_RANK.get(ceiling)
        if rank is None:
            # ceiling 配置成非能力层（如 free/glm_batch）时按 fast 兜底，避免免费层失控
            ceiling = ModelTier.FAST
            rank = _CAPABILITY_TIER_RANK[ModelTier.FAST]
        return ceiling, rank

    def _clamp_tier_for_free_tier(self, target_tier: ModelTier) -> tuple[ModelTier, bool]:
        """免费用户请求高于 ceiling 的能力层时压到 ceiling。返回 (tier, 是否降级)。"""
        if get_request_user_tier() != "free":
            return target_tier, False
        ceiling = self._free_tier_ceiling()
        if ceiling is None:
            return target_tier, False
        ceiling_tier, ceiling_rank = ceiling
        normalized = self._normalize_tier_value(target_tier)
        rank = _CAPABILITY_TIER_RANK.get(normalized)
        if rank is None or rank >= ceiling_rank:
            return target_tier, False
        return ceiling_tier, True

    def _filter_tiers_for_free_tier(self, tiers: list[ModelTier]) -> tuple[list[ModelTier], ModelTier | None]:
        """策略候选层列表的免费层钳制：剔除高于 ceiling 的能力层，全被剔除时落到 ceiling。

        返回 (过滤后的 tiers, 被钳制的最高能力层；未钳制时为 None)。
        非能力层（GLM_BATCH/SPECIALIST/FREE*）保留。
        """
        if get_request_user_tier() != "free":
            return tiers, None
        ceiling = self._free_tier_ceiling()
        if ceiling is None:
            return tiers, None
        ceiling_tier, ceiling_rank = ceiling

        def _rank(tier: ModelTier) -> int | None:
            return _CAPABILITY_TIER_RANK.get(self._normalize_tier_value(tier))

        above = [t for t in tiers if (r := _rank(t)) is not None and r < ceiling_rank]
        if not above:
            return tiers, None
        clamped_from = min(above, key=lambda t: _CAPABILITY_TIER_RANK[self._normalize_tier_value(t)])
        kept = [t for t in tiers if t not in above]
        if not kept:
            kept = [ceiling_tier]
        return kept, clamped_from

    def _adjust_policy_for_free_tier(
        self,
        tiers: list[ModelTier],
        allowed_tiers: set[ModelTier] | None,
        preferred_models: list[str],
    ) -> tuple[list[ModelTier], set[ModelTier] | None, list[str], ModelTier | None]:
        """免费层钳制下同步收敛策略三元组（候选层 / 模式允许层 / 偏好模型）。

        reasoning_mode 的 allowed_tiers 与 policy.preferred_models 都可能把重模型
        带回候选链，钳制时必须一并收敛，否则 clamp 会被旁路。仅 free 用户且触发
        钳制时改动；返回 (tiers, allowed_tiers, preferred_models, clamped_from)。
        """
        tiers, clamped_from = self._filter_tiers_for_free_tier(tiers)
        if clamped_from is None:
            return tiers, allowed_tiers, preferred_models, None
        ceiling_tier, ceiling_rank = self._free_tier_ceiling()  # type: ignore[misc]

        def _keep_tier(tier: ModelTier) -> bool:
            rank = _CAPABILITY_TIER_RANK.get(self._normalize_tier_value(tier))
            return rank is None or rank >= ceiling_rank

        if allowed_tiers is not None:
            kept_allowed = {t for t in allowed_tiers if _keep_tier(t)}
            kept_allowed.add(ceiling_tier)
            allowed_tiers = kept_allowed

        filtered_preferred: list[str] = []
        for model_key in preferred_models:
            cfg = self._available_models.get(model_key)
            if cfg is not None and not _keep_tier(cfg.tier):
                continue
            filtered_preferred.append(model_key)
        return tiers, allowed_tiers, filtered_preferred, clamped_from

    def _preferred_tiers_for_reasoning_mode(
        self,
        *,
        reasoning_mode: str,
        task_type: TaskType | None,
        allow_max: bool = False,
    ) -> list[ModelTier]:
        mode = self._normalize_reasoning_mode(reasoning_mode)
        task_type = self._normalize_task_type(task_type)

        if mode == "fast":
            if task_type in {TaskType.QUICK_QUERY, TaskType.SIMPLE_CHAT, TaskType.ROUTING, TaskType.RETRIEVAL}:
                ordered = [ModelTier.FAST, ModelTier.STANDARD]
            else:
                ordered = [ModelTier.STANDARD, ModelTier.FAST]
        elif mode == "deep":
            if task_type in {TaskType.ERROR_DIAGNOSIS, TaskType.DEEP_REASONING, TaskType.REVIEW}:
                ordered = [ModelTier.PRO, ModelTier.PLUS, ModelTier.STANDARD]
            elif task_type in {TaskType.TASK_DECOMPOSITION, TaskType.COLLABORATION, TaskType.TOOL_PLANNING}:
                ordered = [ModelTier.PLUS, ModelTier.STANDARD, ModelTier.PRO]
            else:
                ordered = [ModelTier.STANDARD, ModelTier.PLUS, ModelTier.PRO]
        else:
            if task_type in {TaskType.QUICK_QUERY, TaskType.SIMPLE_CHAT, TaskType.ROUTING, TaskType.RETRIEVAL}:
                ordered = [ModelTier.FAST, ModelTier.STANDARD, ModelTier.PLUS, ModelTier.PRO]
            elif task_type in {TaskType.ERROR_DIAGNOSIS, TaskType.DEEP_REASONING, TaskType.REVIEW}:
                ordered = [ModelTier.PLUS, ModelTier.PRO, ModelTier.STANDARD, ModelTier.FAST]
            else:
                ordered = [ModelTier.STANDARD, ModelTier.FAST, ModelTier.PLUS, ModelTier.PRO]

        if allow_max and ModelTier.MAX not in ordered:
            ordered = [*ordered, ModelTier.MAX]
        return ordered

    def _load_model_configs(self):
        """从 settings 加载所有可用模型配置。"""
        dashscope_base_url = settings.DASHSCOPE_BASE_URL_COMPATIBLE or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        translation_primary = (settings.TRANSLATION_PRIMARY_PROVIDER or "hunyuan").strip().lower()
        translation_backup = (settings.TRANSLATION_BACKUP_PROVIDER or "siliconflow").strip().lower()
        ocr_primary = (settings.OCR_PROVIDER or "zhipu").strip().lower()
        ocr_backup = (settings.OCR_BACKUP_PROVIDER or "siliconflow").strip().lower()

        configs = {
            "xiaomi_chat": ModelConfig(
                provider=ModelProvider.XIAOMI,
                model_name=settings.XIAOMI_CHAT_MODEL,
                base_url=settings.XIAOMI_MIMO_BASE_URL,
                api_key=settings.XIAOMI_MIMO_API_KEY,
                temperature=settings.XIAOMI_TEMPERATURE,
                tier=ModelTier.FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=200,
                thinking_mode="disabled",
            ),
            "xiaomi_standard_thinking": ModelConfig(
                provider=ModelProvider.XIAOMI,
                model_name=settings.XIAOMI_STANDARD_MODEL,
                base_url=settings.XIAOMI_MIMO_BASE_URL,
                api_key=settings.XIAOMI_MIMO_API_KEY,
                temperature=settings.XIAOMI_TEMPERATURE,
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.0002,
                avg_latency_ms=350,
                thinking_mode="enabled",
            ),
            "mimo_pro": ModelConfig(
                provider=ModelProvider.XIAOMI,
                model_name=settings.XIAOMI_PRO_MODEL,
                base_url=settings.XIAOMI_MIMO_TOKEN_PLAN_BASE_URL,
                api_key=settings.XIAOMI_MIMO_TOKEN_PLAN_API_KEY,
                temperature=settings.XIAOMI_PRO_TEMPERATURE,
                tier=ModelTier.MAX,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=1500,
                thinking_mode="enabled",
            ),
            "deepseek_fast": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_CHAT_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.7,
                tier=ModelTier.FAST,
                cost_per_1k_tokens=0.0002,
                avg_latency_ms=200,
                thinking_mode="disabled",
            ),
            "deepseek_chat": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_CHAT_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.7,
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.0004,
                avg_latency_ms=500,
                thinking_mode="enabled",
            ),
            "deepseek_reason": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_REASON_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.2,
                tier=ModelTier.MAX,
                cost_per_1k_tokens=0.008,
                avg_latency_ms=2500,
            ),
            # ---- GLM 车道（Zhipu）—— 全部「保留待用」----
            # 用户决策（2026-09 MM-M3 + QWEN-PLAN）：glm_batch 车道默认档 = MiniMax M3
            # 优先（免费测试用）、Qwen batch 次之；主力聊天层切 Qwen。GLM 条目保留
            # 注册不删除：作无 MINIMAX/DASHSCOPE key 环境的原链兜底 + 降级链价值；
            # 回切 = .env 设 LLM_PROVIDER=zhipu / LLM_TIER_* 覆盖，零代码回切
            # —— 见下方 _tier_mapping[ModelTier.GLM_BATCH]。
            "glm_4_7_no_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=400,
            ),
            "glm_4_7_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=2000,
            ),
            "glm_4_5_air_batch": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_AIR_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.0004,
                avg_latency_ms=250,
            ),
            "glm_4_6_batch": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_LIGHT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.0006,
                avg_latency_ms=300,
            ),
            # ---- GLM batch 池条目【保留待用】结束 ----
            "glm_4_7_flash_no_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_FLASH_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=200,
            ),
            "glm_4_7_flash_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.GLM_4_7_FLASH_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,
                tier=ModelTier.FREE_FAST,
                cost_per_1k_tokens=0.0005,
                avg_latency_ms=1200,
            ),
            "glm_4_5_air_free": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_AIR_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.FREE_FAST,
                cost_per_1k_tokens=0.0002,
                avg_latency_ms=220,
            ),
            "glm_5_max": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_MAX_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,
                tier=ModelTier.MAX,
                cost_per_1k_tokens=0.004,
                avg_latency_ms=2500,
            ),
            "glm_4_7_plus": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.PLUS,
                cost_per_1k_tokens=0.0008,
                avg_latency_ms=600,
            ),
            "glm_4_7_pro": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,
                tier=ModelTier.PRO,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=2000,
            ),
            "glm_5_1_top": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_TOP_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,
                tier=ModelTier.TOP,
                cost_per_1k_tokens=0.008,
                avg_latency_ms=4000,
            ),
            "siliconflow_free": ModelConfig(
                provider=ModelProvider.SILICONFLOW,
                model_name=settings.SILICONFLOW_FREE_MODEL,
                base_url=settings.SILICONFLOW_BASE_URL,
                api_key=settings.SILICONFLOW_API_KEY,
                temperature=0.7,
                tier=ModelTier.FREE,
                cost_per_1k_tokens=0.0,
                avg_latency_ms=300,
            ),
            # ---- DashScope（通义千问）—— 2026-09 主力车道 ----
            # 定价基准（北京地域，元/百万Token，2026-09 官方页，汇率 7.1 折算 USD/1k）：
            #   qwen3.7-flash 0.2/0.8 → blended ~$0.00007｜qwen3.8-flash 0.8/2.7 → ~$0.00025｜
            #   qwen3.7-plus 非思考 ~2/2（限时8折）→ ~$0.00028，思考 8/8 → ~$0.0011｜
            #   qwen3.8-max 12/36 → ~$0.0034。全部支持 1M 上下文 + Batch 半价 + 缓存折扣。
            "dashscope_fast": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_FAST_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=settings.DASHSCOPE_TEMPERATURE,
                tier=ModelTier.FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=150,
            ),
            "dashscope_standard_thinking": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_STANDARD_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=settings.DASHSCOPE_TEMPERATURE,
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.00025,
                avg_latency_ms=260,
                thinking_mode="enabled",
            ),
            "dashscope_chat": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_CHAT_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=settings.DASHSCOPE_TEMPERATURE,
                tier=ModelTier.PLUS,
                cost_per_1k_tokens=0.0003,
                avg_latency_ms=500,
            ),
            "dashscope_reason": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_REASON_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=0.2,
                tier=ModelTier.PRO,
                cost_per_1k_tokens=0.0012,
                avg_latency_ms=2000,
                thinking_mode="enabled",
            ),
            # 旗舰：MAX/TOP 层（qwen3.8-max，1M 上下文，思考/非思考同价）
            "qwen3_8_max": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_MAX_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=0.3,
                tier=ModelTier.MAX,
                cost_per_1k_tokens=0.0034,
                avg_latency_ms=2500,
                thinking_mode="enabled",
            ),
            "qwen3_8_max_top": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_TOP_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=0.3,
                tier=ModelTier.TOP,
                cost_per_1k_tokens=0.0034,
                avg_latency_ms=3500,
                thinking_mode="enabled",
            ),
            "zhipu_ocr": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_OCR_MODEL,
                base_url=settings.ZHIPU_OCR_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=0.0,
                tier=ModelTier.SPECIALIST,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=2000,
            ),
            "siliconflow_ocr": ModelConfig(
                provider=ModelProvider.SILICONFLOW,
                model_name=settings.SILICONFLOW_OCR_MODEL,
                base_url=settings.SILICONFLOW_BASE_URL,
                api_key=settings.SILICONFLOW_API_KEY,
                temperature=0.0,
                tier=ModelTier.SPECIALIST,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=2000,
            ),
            "hunyuan_translate": ModelConfig(
                provider=ModelProvider.HUNYUAN,
                model_name=settings.HUNYUAN_TRANSLATE_MODEL,
                base_url=settings.HUNYUAN_BASE_URL,
                api_key=settings.HUNYUAN_API_KEY,
                temperature=0.2,
                tier=ModelTier.SPECIALIST,
                cost_per_1k_tokens=0.0005,
                avg_latency_ms=1000,
            ),
            "siliconflow_translate": ModelConfig(
                provider=ModelProvider.SILICONFLOW,
                model_name=settings.SILICONFLOW_TRANSLATE_MODEL,
                base_url=settings.SILICONFLOW_BASE_URL,
                api_key=settings.SILICONFLOW_API_KEY,
                temperature=0.2,
                tier=ModelTier.SPECIALIST,
                cost_per_1k_tokens=0.0005,
                avg_latency_ms=1000,
            ),
            "default": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_CHAT_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.7,
                tier=ModelTier.STANDARD,
            ),
        }

        # MiniMax 异步分析池条目：仅在配置了 MINIMAX_API_KEY 的环境注册。
        # 定位约束（用户决策）：MiniMax M3（token plan 免费档，并发硬上限
        # MINIMAX_MAX_CONCURRENCY=8）只承接 glm_batch 异步分析任务，**永不**加入
        # fast/standard/plus/pro/max/top 等主聊天能力层 —— 无 key 环境零行为变化。
        # 执行面走 OpenAI 兼容 {base}/chat/completions（2026-09 实测 200 OK），
        # 并发由 llm_concurrency 的 minimax 池按 lane 上限钳制；思考链以 <think>
        # 前缀内联在 content，由 LLMService._parse_json_payload 的 <think> 剥离兜底。
        if (settings.MINIMAX_API_KEY or "").strip():
            configs["minimax_m3_batch"] = ModelConfig(
                provider=ModelProvider.MINIMAX,
                model_name=settings.MINIMAX_CHAT_MODEL,
                base_url=settings.MINIMAX_BASE_URL,
                api_key=settings.MINIMAX_API_KEY,
                temperature=0.3,
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.0,  # token plan 免费档
                avg_latency_ms=2500,
            )

        # Qwen 异步分析车道条目：仅在配置了 DASHSCOPE_API_KEY 的环境注册（MiniMax
        # 同款 key-gate 先例，无 key 环境零行为变化）。定位约束（2026-09 用户决策）：
        # qwen3.7-flash 承接 glm_batch 异步分析任务（GLM 池条目保留待用，排其后），
        # **永不**加入 fast/standard/plus/pro/max/top 等主聊天能力层（批处理走
        # DashScope Batch API 半价为后续优化项，本条目先走 OpenAI 兼容同步路径）。
        if (settings.DASHSCOPE_API_KEY or "").strip():
            configs["qwen3_7_flash_batch"] = ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_BATCH_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=0.3,
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=300,
            )

        self._available_models = configs

        # 2026-09 主力切换：各能力层 Qwen（dashscope）置首；deepseek/xiaomi/GLM
        # 条目全部保留为降级候选（GLM「保留待用」，.env LLM_TIER_* 可零代码回切）。
        fast_models = ["dashscope_fast", "deepseek_fast", "xiaomi_chat", "glm_4_7_flash_no_thinking"]
        standard_models = ["deepseek_chat", "dashscope_standard_thinking", "xiaomi_standard_thinking"]
        plus_models = ["dashscope_chat"]
        pro_models = ["dashscope_reason"]
        max_models = ["qwen3_8_max", "deepseek_reason", "glm_5_max"]

        preferred_provider = (settings.LLM_PROVIDER or "").strip().lower()
        provider_standard_preference = {
            "qwen": "dashscope_standard_thinking",
            "dashscope": "dashscope_standard_thinking",
            "deepseek": "xiaomi_standard_thinking",
            "zhipu": "xiaomi_standard_thinking",
            "xiaomi": "xiaomi_standard_thinking",
        }
        provider_plus_preference = {
            "qwen": "dashscope_chat",
            "dashscope": "dashscope_chat",
            "deepseek": "dashscope_chat",
            "zhipu": "dashscope_chat",
            "xiaomi": "dashscope_chat",
        }
        provider_pro_preference = {
            "qwen": "dashscope_reason",
            "dashscope": "dashscope_reason",
            "deepseek": "dashscope_reason",
            "zhipu": "dashscope_reason",
            "xiaomi": "dashscope_reason",
        }

        preferred_standard = provider_standard_preference.get(preferred_provider)
        preferred_plus = provider_plus_preference.get(preferred_provider)
        preferred_pro = provider_pro_preference.get(preferred_provider)
        if preferred_standard in standard_models:
            standard_models.remove(preferred_standard)
            standard_models.insert(0, preferred_standard)
        if preferred_plus in plus_models:
            plus_models.remove(preferred_plus)
            plus_models.insert(0, preferred_plus)
        if preferred_pro in pro_models:
            pro_models.remove(preferred_pro)
            pro_models.insert(0, preferred_pro)

        specialist_models: list[str] = []
        specialist_aliases = {
            "zhipu": "zhipu_ocr",
            "siliconflow": "siliconflow_ocr",
            "hunyuan": "hunyuan_translate",
        }
        for provider_name in (ocr_primary, ocr_backup, translation_primary, translation_backup):
            model_key = specialist_aliases.get(provider_name)
            if model_key and model_key not in specialist_models:
                specialist_models.append(model_key)
        for default_key in ("zhipu_ocr", "siliconflow_ocr", "hunyuan_translate", "siliconflow_translate"):
            if default_key not in specialist_models:
                specialist_models.append(default_key)

        self._tier_mapping = {
            ModelTier.FREE: ["siliconflow_free"],
            # FREE_FAST：Qwen 置首（dashscope_fast=qwen3.7-flash；siliconflow_free
            # 本就是 Qwen3.5-4B），GLM 免费通道条目「保留待用」排其后。
            ModelTier.FREE_FAST: [
                "dashscope_fast",
                "siliconflow_free",
                "glm_4_7_flash_thinking",
                "glm_4_5_air_free",
            ],
            ModelTier.FREE_REASONING: ["glm_4_7_flash_thinking", "glm_4_5_air_free"],  # GLM 保留待用
            ModelTier.FAST: fast_models,
            ModelTier.STANDARD: standard_models,
            ModelTier.PLUS: plus_models + ["glm_4_7_plus"],
            ModelTier.PRO: pro_models + ["glm_4_7_pro"],
            ModelTier.REASONING: list(pro_models) + ["glm_4_7_pro"],
            ModelTier.MAX: max_models,
            ModelTier.TOP: ["qwen3_8_max_top", "glm_5_1_top"],  # 主力 Qwen；glm-5.1 保留待用
            # 用户决策（2026-09 MM-M3，QWEN-PLAN 合入后维持）：GLM_BATCH 车道 =
            # MiniMax M3 优先（免费测试用）→ Qwen batch 次位（均 key-gated）；
            # 任一注册即不启用 GLM（批任务不静默回落付费 GLM，失败走 celery 重试）；
            # 两者均未注册（零 key 环境）保留 GLM 原链，零行为变化。
            # 回切方式：LLM_TIER_GLM_BATCH=minimax_m3_batch,qwen3_7_flash_batch,glm_4_7_no_thinking,...
            ModelTier.GLM_BATCH: (
                [
                    key
                    for key in ("minimax_m3_batch", "qwen3_7_flash_batch")
                    if key in self._available_models
                ]
                or [
                    "glm_4_7_no_thinking",
                    "glm_4_7_thinking",
                    "glm_4_5_air_batch",
                    "glm_4_6_batch",
                ]
            ),
            ModelTier.SPECIALIST: specialist_models,
        }
        self._override_tier_mapping_from_env()
        agent_profile_registry.register_model_configs(configs)
        logger.info(f"LLMRouter initialized with {len(configs)} model configs")

    def _override_tier_mapping_from_env(self):
        """允许通过 .env 覆盖 tier 映射（逗号分隔模型key）"""
        overrides = {
            ModelTier.FREE: settings.LLM_TIER_FREE,
            ModelTier.FREE_FAST: settings.LLM_TIER_FREE_FAST,
            ModelTier.FREE_REASONING: settings.LLM_TIER_FREE_REASONING,
            ModelTier.FAST: settings.LLM_TIER_FAST,
            ModelTier.STANDARD: settings.LLM_TIER_STANDARD,
            ModelTier.PLUS: settings.LLM_TIER_PLUS,
            ModelTier.PRO: settings.LLM_TIER_PRO,
            ModelTier.REASONING: settings.LLM_TIER_REASONING,
            ModelTier.MAX: settings.LLM_TIER_MAX,
            ModelTier.TOP: settings.LLM_TIER_TOP,
            ModelTier.GLM_BATCH: settings.LLM_TIER_GLM_BATCH,
            ModelTier.SPECIALIST: settings.LLM_TIER_SPECIALIST,
        }

        for tier, raw_value in overrides.items():
            if not raw_value:
                continue
            candidates = [item.strip() for item in raw_value.split(",") if item.strip()]
            valid_candidates = [item for item in candidates if item in self._available_models]
            if not valid_candidates:
                logger.warning(f"LLM tier override ignored for {tier.value}: no valid model keys in {candidates}")
                continue
            self._tier_mapping[tier] = valid_candidates
            logger.info(f"LLM tier override applied for {tier.value}: {valid_candidates}")

    # ============================================
    # 核心选择逻辑
    # ============================================

    def select_model(
        self,
        agent_role: AgentRole | str | Any,
        task_type: TaskType | str | Any | None = None,
        force_tier: ModelTier | None = None,
        user_message: str | None = None,
        avoid_providers: list[ModelProvider] | None = None,
        reasoning_mode: str | None = None,
        allow_max: bool = False,
    ) -> LLMSelection:
        """
        选择最合适的模型

        Args:
            agent_role: Agent角色
            task_type: 任务类型（可选，用于更细粒度的选择）
            force_tier: 强制指定层级（用于测试或降级）
            user_message: 用户原始消息（用于复杂度感知路由）

        Returns:
            LLMSelection: 选择结果
        """
        # 标准化输入
        agent_role = self._normalize_agent_role(agent_role)
        task_type = self._normalize_task_type(task_type)

        # 1. 获取Agent配置
        profile = agent_profile_registry.get_profile(agent_role)
        complexity_level = "unknown"

        # 2. 确定目标tier / policy
        if force_tier:
            target_tier = self._normalize_tier_value(force_tier)
            reason = f"强制tier={target_tier.value}"
        elif profile.specific_model:
            # Agent指定了具体模型，直接用
            return self._create_selection(
                profile.specific_model,
                self._available_models.get(profile.specific_model, self._available_models["default"]),
                agent_role,
                task_type,
                f"Agent指定模型: {profile.specific_model}",
                complexity_level=complexity_level,
            )
        elif profile.model_policy:
            selection = self._select_by_policy(
                profile=profile,
                agent_role=agent_role,
                task_type=task_type,
                avoid_providers=avoid_providers,
                complexity_level=complexity_level,
                reasoning_mode=reasoning_mode,
                allow_max=allow_max,
            )
            if selection is not None:
                return selection
        elif task_type:
            # 根据任务类型调整tier
            task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
            target_tier = self._normalize_tier_value(task_config.get("model_tier", profile.model_tier))
            reason = f"任务类型={task_type.value}, 推荐tier={target_tier.value}"
        else:
            target_tier = self._normalize_tier_value(profile.model_tier)
            reason = f"Agent角色={agent_role.value}, 默认tier={target_tier.value}"

        if not force_tier and reasoning_mode:
            preferred_chain = self._preferred_tiers_for_reasoning_mode(
                reasoning_mode=reasoning_mode,
                task_type=task_type,
                allow_max=allow_max,
            )
            if target_tier not in preferred_chain:
                target_tier = preferred_chain[0]
            else:
                target_tier = preferred_chain[0]
            reason += f" | user_mode={self._normalize_reasoning_mode(reasoning_mode)} -> {target_tier.value}"

        # 2.5 复杂度感知调整（仅当复杂度路由开关打开且有 user_message）
        if user_message and getattr(settings, "COMPLEXITY_ROUTING_ENABLED", True):
            assessment = _cx.assess(user_message)
            complexity_level = assessment.level.value
            delta = assessment.suggested_tier_delta
            if delta != 0:
                allow_down = delta < 0 and getattr(settings, "COMPLEXITY_DOWNGRADE_ENABLED", True)
                allow_up = delta > 0 and getattr(settings, "COMPLEXITY_UPGRADE_ENABLED", True)
                if allow_down or allow_up:
                    try:
                        idx = self._FALLBACK_TIER_ORDER.index(target_tier)
                        new_idx = max(0, min(len(self._FALLBACK_TIER_ORDER) - 1, idx - delta))
                        # FALLBACK_TIER_ORDER 从高到低，delta>0 升级(idx减小)，delta<0 降级(idx增大)
                        target_tier = self._FALLBACK_TIER_ORDER[new_idx]
                        reason += f" → complexity={assessment.level.value}(delta={delta:+d})"
                    except ValueError:
                        pass  # target_tier 不在标准链中，跳过复杂度调整

        # 2.6 免费层钳制（free_tier_downgrade）：免费用户请求高于 ceiling 的能力层时压到 ceiling
        clamped_tier, free_downgraded = self._clamp_tier_for_free_tier(target_tier)
        if free_downgraded:
            reason += f" | free_tier_downgrade({target_tier.value}->{clamped_tier.value})"
            LLM_ROUTER_FREE_TIER_DOWNGRADE_TOTAL.labels(
                agent_role=agent_role.value,
                from_tier=target_tier.value,
                to_tier=clamped_tier.value,
                plan=request_tier_label(get_request_user_tier()),
            ).inc()
            logger.info(
                f"[LLMRouter] free_tier_downgrade: {target_tier.value} -> {clamped_tier.value} "
                f"(agent={agent_role.value}, task={task_type.value if task_type else None})"
            )
            target_tier = clamped_tier

        # 3. 从tier中选择具体模型（跳过不健康模型）
        candidates = [
            k for k in self._tier_mapping.get(target_tier, [])
            if self._is_model_healthy(k)
        ]
        candidates = self._apply_provider_avoidance(candidates, avoid_providers)
        if not candidates:
            logger.warning(f"No healthy models for tier {target_tier}, falling back to standard")
            candidates = [
                k for k in self._tier_mapping.get(ModelTier.STANDARD, ["xiaomi_standard_thinking"])
                if self._is_model_healthy(k)
            ] or ["deepseek_chat"]
            candidates = self._apply_provider_avoidance(candidates, avoid_providers)
            reason += " → 降级到standard"

        # E-07 健康秩：probation（恢复观察）降权，健康优先；秩内保持策略原序
        candidates = self._order_candidates_by_health(candidates)
        # E-07 三维自适应反馈：候选链内稳定重排（冷启动零介入，不跨 tier）
        candidates = adaptive_routing_engine.reorder_candidates(candidates)

        # 优先使用第一个候选
        model_key = candidates[0]
        model_config = self._available_models.get(model_key, self._available_models["default"])

        return self._create_selection(
            model_key,
            model_config,
            agent_role,
            task_type,
            reason,
            is_fallback="降级" in reason,
            complexity_level=complexity_level,
            free_tier_downgrade=free_downgraded,
        )

    def resolve_candidate_models(
        self,
        agent_role: AgentRole | str | Any,
        task_type: TaskType | str | Any | None = None,
        force_tier: ModelTier | None = None,
        reasoning_mode: str | None = None,
        allow_max: bool = False,
    ) -> list[str]:
        """返回某个 agent 在当前配置下的候选模型顺序。"""
        agent_role = self._normalize_agent_role(agent_role)
        task_type = self._normalize_task_type(task_type)
        profile = agent_profile_registry.get_profile(agent_role)

        if force_tier:
            target_tier, _ = self._clamp_tier_for_free_tier(self._normalize_tier_value(force_tier))
            return list(self._tier_mapping.get(target_tier, []))
        if profile.specific_model:
            return [profile.specific_model]

        candidates: list[str] = []
        blocked = set(profile.model_policy.blocked_models or []) if profile.model_policy else set()
        allowed_tiers: set[ModelTier] | None = None

        if reasoning_mode:
            allowed_tiers = set(
                self._preferred_tiers_for_reasoning_mode(
                    reasoning_mode=reasoning_mode,
                    task_type=task_type,
                    allow_max=allow_max,
                )
            )

        def _append(model_key: str) -> None:
            if not model_key or model_key in blocked or model_key not in self._available_models:
                return
            if allowed_tiers is not None and self._available_models[model_key].tier not in allowed_tiers:
                return
            if model_key not in candidates:
                candidates.append(model_key)

        if profile.model_policy:
            tiers: list[ModelTier] = []
            if profile.model_policy.preferred_tier is not None:
                tiers.append(self._normalize_tier_value(profile.model_policy.preferred_tier))
            elif task_type is not None and not getattr(profile.model_policy, "lock_to_policy", True):
                task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
                task_tier = task_config.get("model_tier")
                if isinstance(task_tier, ModelTier):
                    tiers.append(self._normalize_tier_value(task_tier))
            normalized_profile_tier = self._normalize_tier_value(profile.model_tier)
            if normalized_profile_tier not in tiers:
                tiers.append(normalized_profile_tier)
            for tier in profile.model_policy.fallback_tiers or []:
                normalized_tier = self._normalize_tier_value(tier)
                if normalized_tier not in tiers:
                    tiers.append(normalized_tier)
            if reasoning_mode:
                # E-02 可观测一致性：与 _select_by_policy 相同的 reversed-insert，
                # 使候选层顺序 = 模式优先链顺序。旧实现按正序 insert(0) 会把链
                # 反转（balanced+STANDARD_RESPONSE 时 PLUS 排到 STANDARD 前），
                # describe_agent_routing 的候选链首位与实际选择不符。
                for tier in reversed(
                    self._preferred_tiers_for_reasoning_mode(
                        reasoning_mode=reasoning_mode,
                        task_type=task_type,
                        allow_max=allow_max,
                    )
                ):
                    if tier in tiers:
                        tiers.remove(tier)
                    tiers.insert(0, tier)
            # 免费层钳制：候选链/模式允许层/偏好模型一并收敛
            tiers, allowed_tiers, policy_preferred, _ = self._adjust_policy_for_free_tier(
                tiers, allowed_tiers, list(profile.model_policy.preferred_models or [])
            )
            for tier in tiers:
                for model_key in self._tier_mapping.get(tier, []):
                    _append(model_key)
            for model_key in policy_preferred:
                _append(model_key)
        else:
            target_tier = self._normalize_tier_value(profile.model_tier)
            if task_type:
                task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
                target_tier = self._normalize_tier_value(task_config.get("model_tier", target_tier))
            if reasoning_mode:
                preferred = self._preferred_tiers_for_reasoning_mode(
                    reasoning_mode=reasoning_mode,
                    task_type=task_type,
                    allow_max=allow_max,
                )
                target_tier = preferred[0]
            target_tier, _ = self._clamp_tier_for_free_tier(target_tier)
            for model_key in self._tier_mapping.get(target_tier, []):
                _append(model_key)

        if not candidates:
            return ["default"]
        return candidates

    def describe_agent_routing(
        self,
        agent_role: AgentRole | str | Any,
        task_type: TaskType | str | Any | None = None,
        force_tier: ModelTier | None = None,
        reasoning_mode: str | None = None,
        allow_max: bool = False,
    ) -> dict[str, Any]:
        """提供 agent 当前模型编排的可观测摘要。"""
        candidates = self.resolve_candidate_models(
            agent_role=agent_role,
            task_type=task_type,
            force_tier=force_tier,
            reasoning_mode=reasoning_mode,
            allow_max=allow_max,
        )
        selection = self.select_model(
            agent_role=agent_role,
            task_type=task_type,
            force_tier=force_tier,
            reasoning_mode=reasoning_mode,
            allow_max=allow_max,
        )
        return {
            "selected_model_key": selection.model_key,
            "selected_tier": selection.config.tier.value,
            "selection_reason": selection.reason,
            "candidate_models": candidates,
        }

    def _select_by_policy(
        self,
        *,
        profile,
        agent_role: AgentRole,
        task_type: TaskType | None,
        avoid_providers: list[ModelProvider] | None = None,
        complexity_level: str = "unknown",
        reasoning_mode: str | None = None,
        allow_max: bool = False,
    ) -> LLMSelection | None:
        policy = getattr(profile, "model_policy", None)
        if policy is None:
            return None

        blocked = set(policy.blocked_models or [])
        candidates: list[str] = []
        allowed_tiers: set[ModelTier] | None = None

        if reasoning_mode:
            allowed_tiers = set(
                self._preferred_tiers_for_reasoning_mode(
                    reasoning_mode=reasoning_mode,
                    task_type=task_type,
                    allow_max=allow_max,
                )
            )

        def _append(model_key: str) -> None:
            if not model_key or model_key in blocked or model_key not in self._available_models:
                return
            if allowed_tiers is not None and self._available_models[model_key].tier not in allowed_tiers:
                return
            if not self._is_model_healthy(model_key):
                logger.debug(f"Skipping unhealthy model: {model_key}")
                return
            if model_key not in candidates:
                candidates.append(model_key)

        tiers: list[ModelTier] = []
        if policy.preferred_tier is not None:
            tiers.append(self._normalize_tier_value(policy.preferred_tier))
        elif task_type is not None and not getattr(policy, "lock_to_policy", True):
            task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
            task_tier = task_config.get("model_tier")
            if isinstance(task_tier, ModelTier):
                tiers.append(self._normalize_tier_value(task_tier))
        normalized_profile_tier = self._normalize_tier_value(profile.model_tier)
        if normalized_profile_tier not in tiers:
            tiers.append(normalized_profile_tier)
        for tier in policy.fallback_tiers or []:
            normalized_tier = self._normalize_tier_value(tier)
            if normalized_tier not in tiers:
                tiers.append(normalized_tier)
        if reasoning_mode:
            preferred_tiers = self._preferred_tiers_for_reasoning_mode(
                reasoning_mode=reasoning_mode,
                task_type=task_type,
                allow_max=allow_max,
            )
            for tier in reversed(preferred_tiers):
                if tier in tiers:
                    tiers.remove(tier)
                tiers.insert(0, tier)

        # 免费层钳制：候选层/模式允许层/偏好模型一并收敛，防止重模型经旁路回流
        tiers, allowed_tiers, policy_preferred, clamped_from = self._adjust_policy_for_free_tier(
            tiers, allowed_tiers, list(policy.preferred_models or [])
        )

        for tier in tiers:
            for model_key in self._tier_mapping.get(tier, []):
                _append(model_key)
        for model_key in policy_preferred:
            _append(model_key)

        candidates = self._apply_provider_avoidance(candidates, avoid_providers)

        if not candidates:
            return None

        # E-07 健康秩 + 三维自适应反馈（与 select_model 同一语义：链内重排，不跨层）
        candidates = self._order_candidates_by_health(candidates)
        candidates = adaptive_routing_engine.reorder_candidates(candidates)

        model_key = candidates[0]
        model_config = self._available_models.get(model_key, self._available_models["default"])
        reason = f"Agent策略路由: {agent_role.value} -> {model_key}"
        if clamped_from is not None:
            reason += f" | free_tier_downgrade({clamped_from.value}->{model_config.tier.value})"
            LLM_ROUTER_FREE_TIER_DOWNGRADE_TOTAL.labels(
                agent_role=agent_role.value,
                from_tier=clamped_from.value,
                to_tier=model_config.tier.value,
                plan=request_tier_label(get_request_user_tier()),
            ).inc()
            logger.info(
                f"[LLMRouter] free_tier_downgrade: {clamped_from.value} -> {model_config.tier.value} "
                f"(agent={agent_role.value}, task={task_type.value if task_type else None})"
            )
        return self._create_selection(
            model_key,
            model_config,
            agent_role,
            task_type,
            reason,
            complexity_level=complexity_level,
            free_tier_downgrade=clamped_from is not None,
        )

    def get_model_provider(self, model_key: str) -> ModelProvider | None:
        with self._lock:
            config = self._available_models.get(model_key)
            return config.provider if config else None

    def _apply_provider_avoidance(
        self,
        candidates: list[str],
        avoid_providers: list[ModelProvider] | None,
    ) -> list[str]:
        if not candidates or not avoid_providers:
            return candidates
        avoid_set = {provider for provider in avoid_providers if provider is not None}
        if not avoid_set:
            return candidates
        filtered = [
            model_key
            for model_key in candidates
            if self.get_model_provider(model_key) not in avoid_set
        ]
        return filtered or candidates

    def select_specific_model(
        self,
        model_key: str,
        agent_role: AgentRole | str | Any = AgentRole.GENERATION,
        task_type: TaskType | str | Any | None = None,
    ) -> LLMSelection:
        """
        直接按已注册模型key选择（用于调试或手动指定）。
        """
        with self._lock:
            agent_role = self._normalize_agent_role(agent_role)
            task_type = self._normalize_task_type(task_type)
            config = self._available_models.get(model_key, self._available_models["default"])
            reason = (
                f"指定模型key: {model_key}"
                if model_key in self._available_models
                else f"模型key未注册: {model_key}，回退默认"
            )
            resolved_key = model_key if model_key in self._available_models else "default"
            return self._create_selection(resolved_key, config, agent_role, task_type, reason)

    def _create_selection(
        self,
        model_key: str,
        config: ModelConfig,
        agent_role: AgentRole,
        task_type: TaskType | None,
        reason: str,
        *,
        is_fallback: bool = False,
        complexity_level: str = "unknown",
        free_tier_downgrade: bool = False,
    ) -> LLMSelection:
        """创建LLMSelection对象，含成本可观测字段"""
        cost = config.cost_per_1k_tokens if hasattr(config, "cost_per_1k_tokens") else 0.0
        tier_str = config.tier.value if hasattr(config, "tier") and config.tier else ""
        rich_reason = f"{reason} [${cost:.4f}/1k, tier={tier_str}]"
        selection = LLMSelection(
            model_key=model_key,
            config=config,
            agent_role=agent_role,
            task_type=task_type,
            reason=rich_reason,
            is_fallback=is_fallback,
            estimated_cost_per_1k=cost,
            tier_used=tier_str,
            free_tier_downgrade=free_tier_downgrade,
        )
        task_label = task_type.value if task_type is not None else "none"
        # O-04: plan 有界 label（free/pro/unknown）——metrics 可区分付费层；
        # 真源是请求级 tier（gRPC 入口按 users.entitlement 派生的 is_pro 设置）。
        plan_label = request_tier_label(get_request_user_tier())
        LLM_ROUTER_SELECTION_TOTAL.labels(
            agent_role=agent_role.value,
            model_key=model_key,
            provider=config.provider.value,
            tier=tier_str or "unknown",
            task_type=task_label,
            complexity=complexity_level or "unknown",
            fallback="true" if is_fallback else "false",
            plan=plan_label,
        ).inc()
        LLM_ROUTER_ESTIMATED_COST_PER_1K.labels(
            agent_role=agent_role.value,
            provider=config.provider.value,
            tier=tier_str or "unknown",
            plan=plan_label,
        ).observe(cost)
        # E-07 可观测：路由决策审计（requested→actual + reason，切换可查）
        routing_audit.record(
            "selection",
            {
                "requested": {
                    "agent_role": agent_role.value,
                    "task_type": task_label,
                    "complexity": complexity_level or "unknown",
                },
                "actual": {
                    "model_key": model_key,
                    "provider": config.provider.value,
                    "model_name": config.model_name,
                    "tier": tier_str or "unknown",
                },
                "reason": rich_reason,
                "is_fallback": is_fallback,
                "free_tier_downgrade": free_tier_downgrade,
                "estimated_cost_per_1k": cost,
            },
        )
        return selection

    # ============================================
    # 模型健康上报（E-07：键型对齐 + 三相滞回）
    # ============================================

    def report_model_failure(self, model_key: str) -> None:
        """上报模型调用失败（由 providers/llm_service 调用；**按注册 model_key**）

        FIX-23（键型对齐）：历史调用面曾按 config.model_name 上报，而选型按
        model_key 查询——健康态在选型侧是死键。此处对未注册 key 拒收并告警，
        不再制造死键。
        """
        with self._lock:
            if model_key not in self._available_models:
                if model_key:
                    logger.debug(f"[LLMRouter] health report for unregistered key ignored: {model_key!r}")
                return
            state = self._model_health.get(model_key)
            if state is None:
                state = ModelHealthState()
                state._model_key = model_key  # type: ignore[attr-defined]  # 指标标签关联
                self._model_health[model_key] = state
            state.record_failure()

    def report_model_success(self, model_key: str) -> None:
        """上报模型调用成功（**按注册 model_key**；未注册 key 忽略）"""
        with self._lock:
            if model_key not in self._available_models:
                return
            state = self._model_health.get(model_key)
            if state is None:
                state = ModelHealthState()
                state._model_key = model_key  # type: ignore[attr-defined]
                self._model_health[model_key] = state
            state.record_success()

    def resolve_model_key(self, config: Any) -> str | None:
        """FIX-23：按模型配置反查注册 model_key（model_name→key 对齐）。

        用于旧调用面只持有 config（如 legacy provider 路径的 duck-typed
        selection）时的健康上报归一。唯一匹配返回 key；歧义/未注册返回 None
        （宁缺毋滥，不造死键）。
        """
        if config is None:
            return None
        model_name = getattr(config, "model_name", None)
        if not model_name:
            return None
        provider = getattr(config, "provider", None)
        base_url = getattr(config, "base_url", None)
        matches: list[str] = []
        with self._lock:
            for key, cfg in self._available_models.items():
                if cfg.model_name != model_name:
                    continue
                if provider is not None and cfg.provider != provider:
                    continue
                if base_url is not None and cfg.base_url != base_url:
                    continue
                matches.append(key)
        return matches[0] if len(matches) == 1 else None

    def _is_model_healthy(self, model_key: str) -> bool:
        """检查模型是否健康（含冷却恢复检测；unknown 默认健康，语义不变）"""
        with self._lock:
            if model_key not in self._model_health:
                return True
            state = self._model_health[model_key]
            state.check_recovery()
            return state.is_healthy

    def _health_rank(self, model_key: str) -> int:
        """候选健康秩：healthy=0，probation=1（恢复观察降权），unhealthy=2。"""
        with self._lock:
            state = self._model_health.get(model_key)
            if state is None:
                return 0
            state.check_recovery()
            if state.phase == "probation":
                return 1
            if state.phase == "unhealthy":
                return 2
            return 0

    def _order_candidates_by_health(self, candidates: list[str]) -> list[str]:
        """按健康秩稳定排序：健康优先，probation 其次；秩内保持策略原序。

        注意：unhealthy 候选通常已在上方被过滤；此排序兜底保留其相对位置，
        保证「全不健康时仍可合法降级/明确不可用」而不是崩溃。
        """
        if not candidates:
            return candidates
        return sorted(candidates, key=self._health_rank)

    @staticmethod
    def _normalize_agent_role(agent_role: AgentRole | str | Any) -> AgentRole:
        if isinstance(agent_role, AgentRole):
            return agent_role
        if isinstance(agent_role, str):
            role_value = agent_role.lower()
            role_aliases = {
                "math": AgentRole.MATH_AGENT,
                "code": AgentRole.CODE_AGENT,
                "writing": AgentRole.WRITING_AGENT,
                "science": AgentRole.SCIENCE_AGENT,
                "search": AgentRole.SEARCH_AGENT,
            }
            if role_value in role_aliases:
                return role_aliases[role_value]
            try:
                return AgentRole(role_value)
            except ValueError:
                return AgentRole.GENERATION
        role_value = getattr(agent_role, "value", None)
        if role_value:
            role_value = str(role_value).lower()
            role_aliases = {
                "math": AgentRole.MATH_AGENT,
                "code": AgentRole.CODE_AGENT,
                "writing": AgentRole.WRITING_AGENT,
                "science": AgentRole.SCIENCE_AGENT,
                "search": AgentRole.SEARCH_AGENT,
            }
            if role_value in role_aliases:
                return role_aliases[role_value]
            try:
                return AgentRole(role_value)
            except ValueError:
                return AgentRole.GENERATION
        return AgentRole.GENERATION

    @staticmethod
    def _normalize_task_type(task_type: TaskType | str | Any | None) -> TaskType | None:
        if task_type is None:
            return None
        if isinstance(task_type, TaskType):
            return task_type
        if isinstance(task_type, str):
            try:
                return TaskType(task_type.lower())
            except ValueError:
                task_map = {
                    "learning": TaskType.STANDARD_RESPONSE,
                    "training": TaskType.STANDARD_RESPONSE,
                    "reflection": TaskType.STANDARD_RESPONSE,
                    "social": TaskType.SIMPLE_CHAT,
                    "planning": TaskType.TOOL_PLANNING,
                    "error_fix": TaskType.ERROR_DIAGNOSIS,
                }
                return task_map.get(task_type.lower())
        task_value = getattr(task_type, "value", None)
        if task_value:
            try:
                return TaskType(str(task_value).lower())
            except ValueError:
                task_map = {
                    "learning": TaskType.STANDARD_RESPONSE,
                    "training": TaskType.STANDARD_RESPONSE,
                    "reflection": TaskType.STANDARD_RESPONSE,
                    "social": TaskType.SIMPLE_CHAT,
                    "planning": TaskType.TOOL_PLANNING,
                    "error_fix": TaskType.ERROR_DIAGNOSIS,
                }
                return task_map.get(str(task_value).lower())
        return None

    # ============================================
    # 降级策略
    # ============================================

    def get_fallback_model(self, failed_selection: LLMSelection) -> LLMSelection:
        """
        获取降级模型

        降级路径：MAX → PRO → PLUS → STANDARD → FAST → FREE_FAST
        FREE_REASONING → FREE_FAST → FAST
        """
        raw_tier = failed_selection.config.tier
        current_tier = self._normalize_tier_value(raw_tier)

        # 免费推理降级路径
        if raw_tier == ModelTier.FREE_REASONING:
            next_tier = ModelTier.FREE_FAST
        else:
            # 标准降级链
            try:
                idx = self._FALLBACK_TIER_ORDER.index(current_tier)
            except ValueError:
                return failed_selection
            if idx >= len(self._FALLBACK_TIER_ORDER) - 1:
                return failed_selection
            next_tier = self._FALLBACK_TIER_ORDER[idx + 1]

        candidates = [
            k for k in self._tier_mapping.get(next_tier, [])
            if self._is_model_healthy(k)
        ]
        # E-07：probation 恢复观察降权，秩内保持原序
        candidates = self._order_candidates_by_health(candidates)
        if not candidates:
            return failed_selection

        fallback_key = candidates[0]
        fallback_config = self._available_models.get(fallback_key, self._available_models["default"])
        reason = f"主模型失败，从{current_tier.value}降级到{next_tier.value}"

        return LLMSelection(
            model_key=fallback_key,
            config=fallback_config,
            agent_role=failed_selection.agent_role,
            task_type=failed_selection.task_type,
            reason=reason,
            is_fallback=True,
            estimated_cost_per_1k=fallback_config.cost_per_1k_tokens,
            tier_used=next_tier.value,
        )

    # ============================================
    # 兼容接口
    # ============================================

    def get_openai_client_kwargs(self, selection: LLMSelection) -> dict[str, Any]:
        """
        获取用于创建 OpenAI 兼容客户端的参数

        兼容：
        - app.services.llm_service.OpenAICompatibleProvider
        - langchain_openai.ChatOpenAI
        """
        config = selection.config
        kwargs = {
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        extra_body: dict[str, Any] | None = None

        # GLM 特有参数：通过 extra_body 传递
        if config.provider == ModelProvider.ZHIPU and config.clear_thinking is not None:
            extra_body = {"clear_thinking": config.clear_thinking}
            # V3-FIX-04: 仅 coding 端点附 thinking disabled（唯一真关闭思考的通道）；
            # 标准端点发该参数会 400 code 1210，clear_thinking 字段本身被智谱静默忽略
            if glm_thinking_disabled_on_wire(config.provider, config.base_url, config.clear_thinking):
                extra_body["thinking"] = {"type": "disabled"}

        # TTFT-CFG: DashScope 车道思考开关是 enable_thinking（GLM 风格 thinking:{}
        # 对其无效，主聊天档位思考从未被显式关过——簇 B 根因）。FAST/STANDARD/PLUS
        # 显式关；PRO/MAX/TOP 不注入（provider 默认思考开 = 保留思考）。
        if config.provider == ModelProvider.DASHSCOPE:
            enable_thinking = dashscope_enable_thinking_param(config.tier, config.thinking_mode)
            if enable_thinking is not None:
                extra_body = dict(extra_body or {})
                extra_body["enable_thinking"] = enable_thinking

        if extra_body is not None:
            kwargs["extra_body"] = extra_body

        # V3-FIX-04: 思考车道 max_tokens 留量（最坏 88% 思考占比下保证可见输出 ≥ 配置值的 15%）
        kwargs["max_tokens"] = glm_effective_max_tokens(
            config.provider, config.base_url, config.clear_thinking, config.max_tokens
        )

        return kwargs

    def get_langchain_client_kwargs(self, selection: LLMSelection) -> dict[str, Any]:
        """获取用于创建 LangChain ChatOpenAI 的参数"""
        return self.get_openai_client_kwargs(selection)


# ============================================
# 全局实例
# ============================================

llm_router = LLMRouter()


# ============================================
# 便捷函数
# ============================================

def select_model_for_agent(
    agent_role: AgentRole | str,
    task_type: TaskType | None = None,
) -> LLMSelection:
    """为Agent选择模型的便捷函数"""
    return llm_router.select_model(agent_role, task_type)


def select_model_for_task(task_type: TaskType) -> LLMSelection:
    """根据任务类型选择模型的便捷函数"""
    return llm_router.select_model(
        agent_role=agent_profile_registry.get_profile_for_task(task_type).role,
        task_type=task_type,
    )
