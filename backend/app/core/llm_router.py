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

from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger

from app.config import settings
from app.core.agent_profiles import TASK_TO_AGENT_PROFILE, AgentRole, ModelTier, TaskType, agent_profile_registry


class ModelProvider(str, Enum):
    """支持的LLM提供商"""
    XIAOMI = "xiaomi"      # XiaoMi MIMO (快速响应)
    DEEPSEEK = "deepseek"  # DeepSeek (核心模型)
    ZHIPU = "zhipu"        # Zhipu GLM (编程/工具)
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
    # 成本/性能指标
    tier: ModelTier = ModelTier.STANDARD
    cost_per_1k_tokens: float = 0.001
    avg_latency_ms: float = 500


@dataclass
class LLMSelection:
    """LLM选择结果（可观测）"""
    model_key: str
    config: ModelConfig
    agent_role: AgentRole
    task_type: TaskType | None
    reason: str  # 选择此模型的原因
    is_fallback: bool = False


class LLMRouter:
    """
    统一的LLM路由器

    根据 AgentProfile 和 TaskType 选择最合适的模型。
    同时兼容主系统（llm_service）和 LangGraph（llm_factory）。
    """

    def __init__(self):
        self._available_models: dict[str, ModelConfig] = {}
        self._tier_mapping: dict[ModelTier, list[str]] = {}
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

            # ===== Zhipu GLM (标准 + 推理) =====
            # GLM-4.7 非思考模式 - 用于 STANDARD 任务（快速响应）
            "zhipu_chat": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,  # 关闭思考模式，用于标准任务的快速响应
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=400,
            ),
            # GLM-4.7 思考模式 - 用于 REASONING 任务（深度推理）
            # NOTE: clear_thinking=False 启用深度思考模式，实际延迟 10-30 秒
            "zhipu_reason": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_CHAT_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,  # 开启保留式思考，保持推理连续性
                tier=ModelTier.REASONING,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=20000,  # 实际 10-30s，设置为 20s 作为预期
            ),
            # GLM-4.7-FlashX 快速响应模型（非思考模式）
            "zhipu_flash": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_FLASH_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,  # 关闭思考模式，极速响应
                tier=ModelTier.FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=150,
            ),
            # GLM-4.7-Flash 非思考模式 - 快速响应（免费）
            "glm_4_7_flash_no_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.GLM_4_7_FLASH_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=True,  # 关闭思考模式，快速响应
                tier=ModelTier.FREE_FAST,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=200,
            ),
            # GLM-4.7-Flash 思考模式 - 深度推理（免费）
            # NOTE: clear_thinking=False 启用深度思考模式，实际延迟 10-20 秒
            "glm_4_7_flash_thinking": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.GLM_4_7_FLASH_MODEL,
                base_url=settings.ZHIPU_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=settings.ZHIPU_TEMPERATURE,
                clear_thinking=False,  # 开启保留式思考，深度推理
                tier=ModelTier.FREE_REASONING,
                cost_per_1k_tokens=0.0005,
                avg_latency_ms=15000,  # 实际 10-20s，设置为 15s 作为预期
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

            # ===== Specialist Models (OCR、翻译等) =====
            # 兼容旧 key：siliconflow_ocr 实际已切换到智谱 GLM OCR
            "siliconflow_ocr": ModelConfig(
                provider=ModelProvider.ZHIPU,
                model_name=settings.ZHIPU_OCR_MODEL,
                base_url=settings.ZHIPU_OCR_BASE_URL,
                api_key=settings.ZHIPU_API_KEY,
                temperature=0.0,
                tier=ModelTier.SPECIALIST,
                cost_per_1k_tokens=0.001,
                avg_latency_ms=2000,
            ),
            # Hunyuan MT - 机器翻译
            "siliconflow_translate": ModelConfig(
                provider=ModelProvider.SILICONFLOW,
                model_name=settings.HUNYUAN_TRANSLATE_MODEL,
                base_url=settings.HUNYUAN_BASE_URL,
                api_key=settings.HUNYUAN_API_KEY or settings.SILICONFLOW_API_KEY,
                temperature=0.2,
                tier=ModelTier.SPECIALIST,
                cost_per_1k_tokens=0.0005,
                avg_latency_ms=1000,
            ),

            # ===== 通用备用 =====
            "default": ModelConfig(
                provider=ModelProvider.DEEPSEEK,  # 默认用deepseek
                model_name=settings.DEEPSEEK_CHAT_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                temperature=0.7,
                tier=ModelTier.STANDARD,
            ),
        }

        self._available_models = configs

        # 按tier分组（优先级从高到低）
        # - FREE_FAST: 免费快速响应模型（glm-4.7-flash 非思考模式）
        # - FREE_REASONING: 免费深度推理模型（glm-4.7-flash 思考模式）
        # - FAST: 付费快速响应模型（xunfei暂不可用，使用zhipu_flash）
        # - STANDARD: 付费标准模型
        # - REASONING: 付费推理模型
        # - SPECIALIST: 专家模型（OCR、翻译等专用功能）
        standard_models = ["zhipu_chat", "deepseek_chat", "dashscope_chat"]
        reasoning_models = ["zhipu_reason", "deepseek_reason", "dashscope_reason"]

        preferred_provider = (settings.LLM_PROVIDER or "").strip().lower()
        provider_standard_preference = {
            "qwen": "dashscope_chat",
            "dashscope": "dashscope_chat",
            "deepseek": "deepseek_chat",
            "zhipu": "zhipu_chat",
            "xiaomi": "deepseek_chat",
        }
        provider_reasoning_preference = {
            "qwen": "dashscope_reason",
            "dashscope": "dashscope_reason",
            "deepseek": "deepseek_reason",
            "zhipu": "zhipu_reason",
            "xiaomi": "deepseek_reason",
        }

        preferred_standard = provider_standard_preference.get(preferred_provider)
        preferred_reasoning = provider_reasoning_preference.get(preferred_provider)
        if preferred_standard in standard_models:
            standard_models.remove(preferred_standard)
            standard_models.insert(0, preferred_standard)
        if preferred_reasoning in reasoning_models:
            reasoning_models.remove(preferred_reasoning)
            reasoning_models.insert(0, preferred_reasoning)

        self._tier_mapping = {
            ModelTier.FREE_FAST: ["glm_4_7_flash_no_thinking"],
            ModelTier.FREE_REASONING: ["glm_4_7_flash_thinking"],
            ModelTier.FAST: ["xiaomi_chat", "zhipu_flash"],
            ModelTier.STANDARD: standard_models,
            ModelTier.REASONING: reasoning_models,
            ModelTier.SPECIALIST: ["siliconflow_ocr", "siliconflow_translate"],
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
    ) -> LLMSelection:
        """
        选择最合适的模型

        Args:
            agent_role: Agent角色
            task_type: 任务类型（可选，用于更细粒度的选择）
            force_tier: 强制指定层级（用于测试或降级）

        Returns:
            LLMSelection: 选择结果
        """
        # 标准化输入
        agent_role = self._normalize_agent_role(agent_role)
        task_type = self._normalize_task_type(task_type)

        # 1. 获取Agent配置
        profile = agent_profile_registry.get_profile(agent_role)

        # 2. 确定目标tier
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
        elif task_type:
            # 根据任务类型调整tier
            task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
            target_tier = task_config.get("model_tier", profile.model_tier)
            reason = f"任务类型={task_type.value}, 推荐tier={target_tier.value}"
        else:
            target_tier = profile.model_tier
            reason = f"Agent角色={agent_role.value}, 默认tier={target_tier.value}"

        # 3. 从tier中选择具体模型
        candidates = self._tier_mapping.get(target_tier, [])
        if not candidates:
            logger.warning(f"No models for tier {target_tier}, falling back to standard")
            candidates = self._tier_mapping.get(ModelTier.STANDARD, ["deepseek_chat"])
            reason += " → 降级到standard"

        # 优先使用第一个候选
        model_key = candidates[0]
        model_config = self._available_models.get(model_key, self._available_models["default"])

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
        """创建LLMSelection对象"""
        return LLMSelection(
            model_key=model_key,
            config=config,
            agent_role=agent_role,
            task_type=task_type,
            reason=reason,
        )

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

        降级路径：
        REASONING → STANDARD → FAST
        """
        current_tier = failed_selection.config.tier

        if current_tier == ModelTier.REASONING:
            next_tier = ModelTier.STANDARD
            reason = f"主模型失败，从{current_tier.value}降级到{next_tier.value}"
        elif current_tier == ModelTier.STANDARD:
            next_tier = ModelTier.FAST
            reason = f"主模型失败，从{current_tier.value}降级到{next_tier.value}"
        else:
            # 已经是最快的了
            reason = "已是最快模型，无法再降级"
            return failed_selection

        candidates = self._tier_mapping.get(next_tier, [])
        if not candidates:
            return failed_selection

        fallback_key = candidates[0]
        fallback_config = self._available_models.get(fallback_key, self._available_models["default"])

        return LLMSelection(
            model_key=fallback_key,
            config=fallback_config,
            agent_role=failed_selection.agent_role,
            task_type=failed_selection.task_type,
            reason=reason,
            is_fallback=True,
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
