import os
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

class LLMFactory:
    """
    LLM 模型工厂
    负责根据 Agent 需求动态分发不同的模型实例
    """
    
    # 模型预设配置
    MODEL_CONFIGS = {
        # 1. 强推理模型 (Planner, ExamOracle)
        "gpt-4o": {
            "model": "gpt-4o",
            "temperature": 0.7
        },
        # 2. 高性价比/通用模型 (Router, TimeTutor)
        "gpt-4o-mini": {
            "model": "gpt-4o-mini",
            "temperature": 0.5
        },
        # 3. 中文/RAG 特化模型 (GalaxyGuide)
        # DeepSeek V3 (假设通过 OpenAI 兼容接口调用)
        "deepseek-chat": {
            "model": "deepseek-chat",
            "base_url": settings.DEEPSEEK_BASE_URL,
            "api_key": settings.DEEPSEEK_API_KEY,
            "temperature": 0.3 # RAG 需要低温
        },
        # 4. 兜底模型
        "default": {
            "model": settings.LLM_MODEL_NAME, # .env 中的默认配置
            "base_url": settings.LLM_API_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "temperature": 0.7
        }
    }

    @staticmethod
    def get_llm(
        agent_role: str, 
        override_model: Optional[str] = None
    ) -> BaseChatModel:
        """
        根据 Agent 角色获取最佳 LLM 实例
        
        Args:
            agent_role: Agent 角色名称 (router, galaxy, time...)
            override_model: 强制指定模型名称
        """
        
        # 1. 策略路由: 决定用哪个模型配置
        config_key = "default"
        
        if override_model:
            config_key = override_model if override_model in LLMFactory.MODEL_CONFIGS else "default"
        else:
            # 角色 -> 模型 映射策略
            if agent_role in ["planner", "exam_oracle"]:
                config_key = "gpt-4o"
            elif agent_role in ["galaxy_guide"]:
                config_key = "deepseek-chat"
            elif agent_role in ["router", "time_tutor"]:
                config_key = "gpt-4o-mini"
        
        # 2. 获取配置
        config = LLMFactory.MODEL_CONFIGS.get(config_key, LLMFactory.MODEL_CONFIGS["default"]).copy()
        
        # 提取特殊参数
        base_url = config.pop("base_url", None)
        api_key = config.pop("api_key", None)
        
        # 3. 实例化 LangChain ChatModel
        # 如果是 DeepSeek 或自定义 endpoint
        if base_url:
            return ChatOpenAI(
                base_url=base_url,
                api_key=api_key or "sk-placeholder", # 有些本地模型随便填
                **config
            )
        
        # 默认 OpenAI
        return ChatOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY, 
            **config
        )
