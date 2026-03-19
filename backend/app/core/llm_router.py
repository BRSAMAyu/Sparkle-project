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

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from app.config import settings
from app.core.agent_profiles import TASK_TO_AGENT_PROFILE, AgentRole, ModelTier, TaskType, agent_profile_registry
from app.core import complexity_analyzer as _cx


class ModelProvider(str, Enum):
    """支持的LLM提供商"""
    XIAOMI = "xiaomi"      # XiaoMi MIMO (快速响应)
    DEEPSEEK = "deepseek"  # DeepSeek (核心模型)
    ZHIPU = "zhipu"        # Zhipu GLM (编程/工具)
    HUNYUAN = "hunyuan"    # Hunyuan Translation
    DASHSCOPE = "dashscope"  # Aliyun DashScope (通义千问)
    SILICONFLOW = "siliconflow"  # SiliconFlow (专家模型：OCR、翻译等)


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
    """模型健康状态（内存缓存，无持久化）"""
    consecutive_failures: int = 0
    last_failure_at: float | None = None
    is_healthy: bool = True

    # 5次连续失败 → 标记不健康；300秒无失败 → 自动恢复
    FAILURE_THRESHOLD: int = field(default=5, init=False, repr=False)
    RECOVERY_SECONDS: float = field(default=300.0, init=False, repr=False)

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_at = time.monotonic()
        if self.consecutive_failures >= self.FAILURE_THRESHOLD:
            self.is_healthy = False
            logger.warning(f"Model marked unhealthy after {self.consecutive_failures} consecutive failures")

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.is_healthy = True

    def check_recovery(self) -> None:
        """检查是否应该自动恢复（300s 无新失败）"""
        if not self.is_healthy and self.last_failure_at is not None:
            if time.monotonic() - self.last_failure_at >= self.RECOVERY_SECONDS:
                self.is_healthy = True
                self.consecutive_failures = 0
                logger.info("Model recovered after cooldown period")


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


class LLMRouter:
    """
    统一的LLM路由器

    根据 AgentProfile 和 TaskType 选择最合适的模型。
    同时兼容主系统（llm_service）和 LangGraph（llm_factory）。
    """

    # Tier 降级顺序（从高到低成本）
    _FALLBACK_TIER_ORDER: list[ModelTier] = [
        ModelTier.REASONING,
        ModelTier.STANDARD,
        ModelTier.FAST,
        ModelTier.FREE_FAST,
    ]

    def __init__(self):
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
        self._available_models.update(configs)
        if tier_mapping:
            self._tier_mapping = tier_mapping
        agent_profile_registry.register_model_configs(configs)
        logger.info(f"LLMRouter updated with {len(configs)} model configs")

    def _load_model_configs(self):
        """从settings加载所有可用模型配置"""
        dashscope_base_url = settings.DASHSCOPE_BASE_URL_COMPATIBLE or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        translation_primary = (settings.TRANSLATION_PRIMARY_PROVIDER or "hunyuan").strip().lower()
        translation_backup = (settings.TRANSLATION_BACKUP_PROVIDER or "siliconflow").strip().lower()
        ocr_primary = (settings.OCR_PROVIDER or "zhipu").strip().lower()
        ocr_backup = (settings.OCR_BACKUP_PROVIDER or "siliconflow").strip().lower()
        configs = {
            # ===== XiaoMi MIMO (快速) =====
            "xiaomi_chat": ModelConfig(
                provider=ModelProvider.XIAOMI,
                model_name=settings.XIAOMI_CHAT_MODEL,
                base_url=settings.XIAOMI_MIMO_BASE_URL,
                api_key=settings.XIAOMI_MIMO_API_KEY,
                temperature=settings.XIAOMI_TEMPERATURE,
                tier=ModelTier.FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=200,
            ),

            # ===== XiaoMi MIMO Pro (标准 + 推理，支持联网搜索) =====
            "mimo_pro": ModelConfig(
                provider=ModelProvider.XIAOMI,
                model_name=settings.XIAOMI_PRO_MODEL,
                base_url=settings.XIAOMI_MIMO_BASE_URL,
                api_key=settings.XIAOMI_MIMO_API_KEY,
                temperature=settings.XIAOMI_PRO_TEMPERATURE,
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=600,
                enable_web_search=settings.XIAOMI_WEB_SEARCH_ENABLED,
                thinking_mode="enabled",  # mimo-v2-pro 默认启用思考
            ),

            # ===== DeepSeek (标准 + 推理) =====
            "deepseek_chat": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_CHAT_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.7,
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=800,
            ),
            "deepseek_reason": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_REASON_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.2,
                tier=ModelTier.REASONING,
                cost_per_1k_tokens=0.005,
                avg_latency_ms=3000,
            ),

            # ===== Zhipu GLM Batch (独立层级) =====
            # GLM-4.7 非思考模式 - 用于批量处理任务
            "glm_4_7_no_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,  # 关闭思考模式
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=400,
            ),
            # GLM-4.7 思考模式 - 用于批量深度推理
            "glm_4_7_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,  # 开启保留式思考
                tier=ModelTier.GLM_BATCH,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=20000,
            ),
            # GLM-4.7-Flash 非思考模式 - 快速响应（免费）
            "glm_4_7_flash_no_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_FLASH_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,
                tier=ModelTier.FREE_FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=200,
            ),
            # GLM-4.7-Flash 思考模式 - 深度推理（免费）
            "glm_4_7_flash_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.GLM_4_7_FLASH_MODEL,
                base_url=settings.ZHIPU_CODING_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,
                tier=ModelTier.FREE_REASONING,
                cost_per_1k_tokens=0.0005,
                avg_latency_ms=15000,
            ),

            # ===== Aliyun DashScope (通义千问) =====
            "dashscope_chat": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_CHAT_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=settings.DASHSCOPE_TEMPERATURE,
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.0004,
                avg_latency_ms=500,
            ),
            "dashscope_reason": ModelConfig(
                provider=ModelProvider.DASHSCOPE,
                model_name=settings.DASHSCOPE_REASON_MODEL,
                base_url=dashscope_base_url,
                api_key=settings.DASHSCOPE_API_KEY,
                temperature=0.2,
                tier=ModelTier.REASONING,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=2000,
            ),
            # Qwen3.5-Flash 快速响应
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

            # ===== Specialist Models (OCR、翻译等) =====
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

            # ===== 通用备用 =====
            "default": ModelConfig(
                provider=ModelProvider.DEEPSEEK,
                model_name=settings.DEEPSEEK_CHAT_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.7,
                tier=ModelTier.STANDARD,
            ),
        }

        self._available_models = configs

        # 按tier分组（优先级从高到低）
        # - FREE_FAST: 免费快速响应模型
        # - FREE_REASONING: 免费深度推理模型
        # - FAST: 付费快速响应模型（mimo-v2-flash, qwen3.5-flash）
        # - STANDARD: 付费标准模型（mimo-v2-pro, deepseek, qwen3.5-plus）
        # - REASONING: 付费推理模型（mimo-v2-pro, deepseek-reasoner, qwen3.5-plus）
        # - GLM_BATCH: GLM批量处理（glm-4.7 非思考+思考）
        # - SPECIALIST: 专家模型
        standard_models = ["mimo_pro", "dashscope_chat", "deepseek_chat"]
        reasoning_models = ["mimo_pro", "dashscope_reason", "deepseek_reason"]
        fast_models = ["xiaomi_chat", "dashscope_fast"]

        preferred_provider = (settings.LLM_PROVIDER or "").strip().lower()
        provider_standard_preference = {
            "qwen": "dashscope_chat",
            "dashscope": "dashscope_chat",
            "deepseek": "deepseek_chat",
            "zhipu": "deepseek_chat",
            "xiaomi": "mimo_pro",  # xiaomi 优先使用 mimo_pro
        }
        provider_reasoning_preference = {
            "qwen": "dashscope_reason",
            "dashscope": "dashscope_reason",
            "deepseek": "deepseek_reason",
            "zhipu": "deepseek_reason",
            "xiaomi": "mimo_pro",  # xiaomi 优先使用 mimo_pro
        }

        preferred_standard = provider_standard_preference.get(preferred_provider)
        preferred_reasoning = provider_reasoning_preference.get(preferred_provider)
        if preferred_standard in standard_models:
            standard_models.remove(preferred_standard)
            standard_models.insert(0, preferred_standard)
        if preferred_reasoning in reasoning_models:
            reasoning_models.remove(preferred_reasoning)
            reasoning_models.insert(0, preferred_reasoning)

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
            ModelTier.FREE_FAST: ["glm_4_7_flash_no_thinking"],
            ModelTier.FREE_REASONING: ["glm_4_7_flash_thinking"],
            ModelTier.FAST: fast_models,
            ModelTier.STANDARD: standard_models,
            ModelTier.REASONING: reasoning_models,
            ModelTier.GLM_BATCH: [
                "glm_4_7_no_thinking",
                "glm_4_7_thinking",
                "glm_4_7_flash_no_thinking",
                "glm_4_7_flash_thinking",
            ],
            ModelTier.SPECIALIST: specialist_models,
        }
        self._override_tier_mapping_from_env()

        # 注册到agent_profile_registry
        agent_profile_registry.register_model_configs(configs)

        logger.info(f"LLMRouter initialized with {len(configs)} model configs")

    def _override_tier_mapping_from_env(self):
        """允许通过 .env 覆盖 tier 映射（逗号分隔模型key）"""
        overrides = {
            ModelTier.FREE_FAST: settings.LLM_TIER_FREE_FAST,
            ModelTier.FREE_REASONING: settings.LLM_TIER_FREE_REASONING,
            ModelTier.FAST: settings.LLM_TIER_FAST,
            ModelTier.STANDARD: settings.LLM_TIER_STANDARD,
            ModelTier.REASONING: settings.LLM_TIER_REASONING,
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

        # 2. 确定目标tier / policy
        if force_tier:
            target_tier = force_tier
            reason = f"强制tier={target_tier.value}"
        elif profile.specific_model:
            # Agent指定了具体模型，直接用
            return self._create_selection(
                profile.specific_model,
                self._available_models.get(profile.specific_model, self._available_models["default"]),
                agent_role,
                task_type,
                f"Agent指定模型: {profile.specific_model}"
            )
        elif profile.model_policy:
            selection = self._select_by_policy(
                profile=profile,
                agent_role=agent_role,
                task_type=task_type,
            )
            if selection is not None:
                return selection
        elif task_type:
            # 根据任务类型调整tier
            task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
            target_tier = task_config.get("model_tier", profile.model_tier)
            reason = f"任务类型={task_type.value}, 推荐tier={target_tier.value}"
        else:
            target_tier = profile.model_tier
            reason = f"Agent角色={agent_role.value}, 默认tier={target_tier.value}"

        # 2.5 复杂度感知调整（仅当复杂度路由开关打开且有 user_message）
        if user_message and getattr(settings, "COMPLEXITY_ROUTING_ENABLED", True):
            assessment = _cx.assess(user_message)
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

        # 3. 从tier中选择具体模型（跳过不健康模型）
        candidates = [
            k for k in self._tier_mapping.get(target_tier, [])
            if self._is_model_healthy(k)
        ]
        if not candidates:
            logger.warning(f"No healthy models for tier {target_tier}, falling back to standard")
            candidates = [
                k for k in self._tier_mapping.get(ModelTier.STANDARD, ["deepseek_chat"])
                if self._is_model_healthy(k)
            ] or ["deepseek_chat"]
            reason += " → 降级到standard"

        # 优先使用第一个候选
        model_key = candidates[0]
        model_config = self._available_models.get(model_key, self._available_models["default"])

        return self._create_selection(model_key, model_config, agent_role, task_type, reason)

    def resolve_candidate_models(
        self,
        agent_role: AgentRole | str | Any,
        task_type: TaskType | str | Any | None = None,
        force_tier: ModelTier | None = None,
    ) -> list[str]:
        """返回某个 agent 在当前配置下的候选模型顺序。"""
        agent_role = self._normalize_agent_role(agent_role)
        task_type = self._normalize_task_type(task_type)
        profile = agent_profile_registry.get_profile(agent_role)

        if force_tier:
            return list(self._tier_mapping.get(force_tier, []))
        if profile.specific_model:
            return [profile.specific_model]

        candidates: list[str] = []
        blocked = set(profile.model_policy.blocked_models or []) if profile.model_policy else set()

        def _append(model_key: str) -> None:
            if not model_key or model_key in blocked or model_key not in self._available_models:
                return
            if model_key not in candidates:
                candidates.append(model_key)

        if profile.model_policy:
            for model_key in profile.model_policy.preferred_models or []:
                _append(model_key)

            tiers: list[ModelTier] = []
            if profile.model_policy.preferred_tier is not None:
                tiers.append(profile.model_policy.preferred_tier)
            elif task_type is not None and not getattr(profile.model_policy, "lock_to_policy", True):
                task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
                task_tier = task_config.get("model_tier")
                if isinstance(task_tier, ModelTier):
                    tiers.append(task_tier)
            if profile.model_tier not in tiers:
                tiers.append(profile.model_tier)
            for tier in profile.model_policy.fallback_tiers or []:
                if tier not in tiers:
                    tiers.append(tier)
            for tier in tiers:
                for model_key in self._tier_mapping.get(tier, []):
                    _append(model_key)
        else:
            target_tier = profile.model_tier
            if task_type:
                task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
                target_tier = task_config.get("model_tier", target_tier)
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
    ) -> dict[str, Any]:
        """提供 agent 当前模型编排的可观测摘要。"""
        candidates = self.resolve_candidate_models(
            agent_role=agent_role,
            task_type=task_type,
            force_tier=force_tier,
        )
        selection = self.select_model(
            agent_role=agent_role,
            task_type=task_type,
            force_tier=force_tier,
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
    ) -> LLMSelection | None:
        policy = getattr(profile, "model_policy", None)
        if policy is None:
            return None

        blocked = set(policy.blocked_models or [])
        candidates: list[str] = []

        def _append(model_key: str) -> None:
            if not model_key or model_key in blocked or model_key not in self._available_models:
                return
            if not self._is_model_healthy(model_key):
                logger.debug(f"Skipping unhealthy model: {model_key}")
                return
            if model_key not in candidates:
                candidates.append(model_key)

        for model_key in policy.preferred_models or []:
            _append(model_key)

        tiers: list[ModelTier] = []
        if policy.preferred_tier is not None:
            tiers.append(policy.preferred_tier)
        elif task_type is not None and not getattr(policy, "lock_to_policy", True):
            task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
            task_tier = task_config.get("model_tier")
            if isinstance(task_tier, ModelTier):
                tiers.append(task_tier)
        if profile.model_tier not in tiers:
            tiers.append(profile.model_tier)
        for tier in policy.fallback_tiers or []:
            if tier not in tiers:
                tiers.append(tier)

        for tier in tiers:
            for model_key in self._tier_mapping.get(tier, []):
                _append(model_key)

        if not candidates:
            return None

        model_key = candidates[0]
        model_config = self._available_models.get(model_key, self._available_models["default"])
        reason = f"Agent策略路由: {agent_role.value} -> {model_key}"
        return self._create_selection(model_key, model_config, agent_role, task_type, reason)

    def select_specific_model(
        self,
        model_key: str,
        agent_role: AgentRole | str | Any = AgentRole.GENERATION,
        task_type: TaskType | str | Any | None = None,
    ) -> LLMSelection:
        """
        直接按已注册模型key选择（用于调试或手动指定）。
        """
        agent_role = self._normalize_agent_role(agent_role)
        task_type = self._normalize_task_type(task_type)
        config = self._available_models.get(model_key, self._available_models["default"])
        reason = f"指定模型key: {model_key}" if model_key in self._available_models else f"模型key未注册: {model_key}，回退默认"
        resolved_key = model_key if model_key in self._available_models else "default"
        return self._create_selection(resolved_key, config, agent_role, task_type, reason)

    def _create_selection(
        self,
        model_key: str,
        config: ModelConfig,
        agent_role: AgentRole,
        task_type: TaskType | None,
        reason: str,
    ) -> LLMSelection:
        """创建LLMSelection对象，含成本可观测字段"""
        cost = config.cost_per_1k_tokens if hasattr(config, "cost_per_1k_tokens") else 0.0
        tier_str = config.tier.value if hasattr(config, "tier") and config.tier else ""
        rich_reason = f"{reason} [${cost:.4f}/1k, tier={tier_str}]"
        return LLMSelection(
            model_key=model_key,
            config=config,
            agent_role=agent_role,
            task_type=task_type,
            reason=rich_reason,
            estimated_cost_per_1k=cost,
            tier_used=tier_str,
        )

    # ============================================
    # 模型健康上报
    # ============================================

    def report_model_failure(self, model_key: str) -> None:
        """上报模型调用失败（由 providers.py 调用）"""
        if model_key not in self._model_health:
            self._model_health[model_key] = ModelHealthState()
        self._model_health[model_key].record_failure()

    def report_model_success(self, model_key: str) -> None:
        """上报模型调用成功"""
        if model_key in self._model_health:
            self._model_health[model_key].record_success()

    def _is_model_healthy(self, model_key: str) -> bool:
        """检查模型是否健康（含自动恢复检测）"""
        if model_key not in self._model_health:
            return True
        state = self._model_health[model_key]
        state.check_recovery()
        return state.is_healthy

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

        降级路径：REASONING → STANDARD → FAST → FREE_FAST
        FREE_REASONING → FREE_FAST → FAST
        """
        current_tier = failed_selection.config.tier

        # 免费推理降级路径
        if current_tier == ModelTier.FREE_REASONING:
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

        # GLM 特有参数：通过 extra_body 传递
        if config.provider == ModelProvider.ZHIPU and config.clear_thinking is not None:
            kwargs["extra_body"] = {
                "clear_thinking": config.clear_thinking
            }

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
