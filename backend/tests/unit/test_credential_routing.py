from __future__ import annotations

"""P2-9: Validate service-specific credential routing in LLMRouter.

Ensures each model key receives the correct provider-specific API key and
base URL from settings, and that credentials are isolated between providers.
"""

import pytest

from app.config.settings import Settings
from app.core.llm_router import LLMRouter, ModelProvider


def _settings_with_credentials(**overrides):
    values = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "JWT_SECRET": "test_jwt_secret_with_minimum_32_chars",
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/sparkle",
        "POSTGRES_PASSWORD": "test_pg_pass",
        "REDIS_PASSWORD": "test_redis_pass",
        "INTERNAL_API_KEY": "test_internal_key",
        "MINIO_ACCESS_KEY": "test_minio_access",
        "MINIO_SECRET_KEY": "test_minio_secret",
        "LLM_API_KEY": "llm_legacy_key",
        "XIAOMI_MIMO_API_KEY": "xm_mimo_key_abc123",
        "XIAOMI_MIMO_TOKEN_PLAN_API_KEY": "xm_token_plan_key_xyz789",
        "DEEPSEEK_API_KEY": "ds_deepseek_key_def456",
        "ZHIPU_API_KEY": "zhipu_glm_key_ghi012",
        "DASHSCOPE_API_KEY": "dashscope_key_jkl345",
        "SILICONFLOW_API_KEY": "sf_siliconflow_key_mno678",
        "HUNYUAN_API_KEY": "hunyuan_key_pqr901",
        "SPARKLE_RBAC_ENABLED": True,
        "PRODUCTION_URL": "https://sparkle.example.com",
        "BACKEND_CORS_ORIGINS": "https://sparkle.example.com",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_USER": "smtp_user",
        "SMTP_PASSWORD": "smtp_secret",
        "EMAIL_FROM": "no-reply@example.com",
        "EMAIL_ENABLED": True,
        "PRODUCTION_BACKUP_DIR": "/tmp/sparkle_backups",
        "XIAOMI_MIMO_BASE_URL": "https://mimo.xiaomi.example.com/v1",
        "XIAOMI_MIMO_TOKEN_PLAN_BASE_URL": "https://mimo-pro.xiaomi.example.com/v1",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.example.com/v1",
        "ZHIPU_BASE_URL": "https://open.bigmodel.example.com/api/paas/v4",
        "ZHIPU_CODING_BASE_URL": "https://coding.bigmodel.example.com/api/paas/v4",
        "DASHSCOPE_BASE_URL_COMPATIBLE": "https://dashscope.aliyuncs.example.com/compatible-mode/v1",
        "SILICONFLOW_BASE_URL": "https://api.siliconflow.example.com/v1",
        "XIAOMI_CHAT_MODEL": "mimo-chat-v2",
        "XIAOMI_STANDARD_MODEL": "mimo-standard-v2",
        "XIAOMI_PRO_MODEL": "mimo-pro-v2",
        "DEEPSEEK_CHAT_MODEL": "deepseek-chat",
        "DEEPSEEK_REASON_MODEL": "deepseek-reasoner",
        "ZHIPU_CHAT_MODEL": "glm-4.7",
        "ZHIPU_AIR_MODEL": "glm-4.5-air",
        "ZHIPU_LIGHT_MODEL": "glm-4.6",
        "ZHIPU_FLASH_MODEL": "glm-4.7-flash",
        "ZHIPU_MAX_MODEL": "glm-5",
        "GLM_4_7_FLASH_MODEL": "glm-4.7-flash-v2",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def router_with_known_keys():
    """Create LLMRouter backed by settings with unique per-provider API keys."""
    import app.core.llm_router as llm_router_module

    saved = getattr(llm_router_module, "settings", None)
    try:
        test_settings = _settings_with_credentials()
        llm_router_module.settings = test_settings
        router = LLMRouter()
        return router
    finally:
        if saved is not None:
            llm_router_module.settings = saved


# ── Credential correctness: each model → correct provider key ──────────

def test_xiaomi_models_use_mimo_api_key(router_with_known_keys):
    """小米 MIMO 标准模型使用 XIAOMI_MIMO_API_KEY"""
    for key in ("xiaomi_chat", "xiaomi_standard_thinking"):
        cfg = router_with_known_keys._available_models.get(key)
        assert cfg is not None, f"Model {key} not found"
        assert cfg.api_key == "xm_mimo_key_abc123", (
            f"{key}: expected XIAOMI_MIMO_API_KEY, got {cfg.api_key[:8]}..."
        )
        assert cfg.provider == ModelProvider.XIAOMI
        assert cfg.base_url == "https://mimo.xiaomi.example.com/v1"


def test_mimo_pro_uses_token_plan_api_key(router_with_known_keys):
    """小米 MIMO Pro 使用独立的 XIAOMI_MIMO_TOKEN_PLAN_API_KEY（凭据隔离）"""
    cfg = router_with_known_keys._available_models.get("mimo_pro")
    assert cfg is not None
    assert cfg.api_key == "xm_token_plan_key_xyz789", (
        f"mimo_pro: expected XIAOMI_MIMO_TOKEN_PLAN_API_KEY, got {cfg.api_key[:8]}..."
    )
    assert cfg.provider == ModelProvider.XIAOMI
    assert cfg.base_url == "https://mimo-pro.xiaomi.example.com/v1"


def test_deepseek_models_use_deepseek_api_key(router_with_known_keys):
    """DeepSeek 模型使用 DEEPSEEK_API_KEY"""
    for key in ("deepseek_fast", "deepseek_chat", "deepseek_reason"):
        cfg = router_with_known_keys._available_models.get(key)
        assert cfg is not None, f"Model {key} not found"
        assert cfg.api_key == "ds_deepseek_key_def456", (
            f"{key}: expected DEEPSEEK_API_KEY, got {cfg.api_key[:8]}..."
        )
        assert cfg.provider == ModelProvider.DEEPSEEK


def test_zhipu_models_use_zhipu_api_key(router_with_known_keys):
    """智谱 GLM 模型使用 ZHIPU_API_KEY"""
    glm_keys = [
        "glm_4_7_no_thinking", "glm_4_7_thinking", "glm_4_5_air_batch",
        "glm_4_6_batch", "glm_4_7_flash_no_thinking", "glm_4_7_flash_thinking",
        "glm_4_5_air_free", "glm_5_max", "glm_4_7_plus",
    ]
    for key in glm_keys:
        cfg = router_with_known_keys._available_models.get(key)
        assert cfg is not None, f"Model {key} not found"
        assert cfg.api_key == "zhipu_glm_key_ghi012", (
            f"{key}: expected ZHIPU_API_KEY, got {cfg.api_key[:8]}..."
        )
        assert cfg.provider == ModelProvider.ZHIPU


# ── Credential isolation: different providers don't cross-contaminate ──

def test_credential_isolation_between_providers(router_with_known_keys):
    """不同提供商的模型使用不同的 API 密钥（凭据隔离）"""
    provider_keys = {}
    for model_key, cfg in router_with_known_keys._available_models.items():
        provider_keys.setdefault(cfg.provider, set()).add(cfg.api_key)

    # Per-provider key counts: Xiaomi has 2 keys (MIMO standard + token-plan) by design.
    # All other providers should have exactly 1 key.
    for provider, keys in provider_keys.items():
        if provider == ModelProvider.XIAOMI:
            assert len(keys) == 2, (
                f"Xiaomi must have 2 keys (standard + token-plan), got: {keys}"
            )
        else:
            assert len(keys) == 1, (
                f"Provider {provider.value} has mixed API keys: {keys}"
            )

    # Different providers should use different API keys
    xiaomi_keys = provider_keys.get(ModelProvider.XIAOMI, set())
    deepseek_keys = provider_keys.get(ModelProvider.DEEPSEEK, set())
    zhipu_keys = provider_keys.get(ModelProvider.ZHIPU, set())

    assert xiaomi_keys.isdisjoint(deepseek_keys), "Xiaomi/DeepSeek key collision"
    assert xiaomi_keys.isdisjoint(zhipu_keys), "Xiaomi/Zhipu key collision"
    assert deepseek_keys.isdisjoint(zhipu_keys), "DeepSeek/Zhipu key collision"


def test_mimo_pro_credential_isolation_from_standard_xiaomi(router_with_known_keys):
    """MIMO Pro 的凭据与标准小米凭据隔离（不同的 API key + base URL）"""
    standard = router_with_known_keys._available_models["xiaomi_chat"]
    pro = router_with_known_keys._available_models["mimo_pro"]

    assert standard.api_key != pro.api_key, (
        "Standard Xiaomi and Pro must use different API keys"
    )
    assert standard.base_url != pro.base_url, (
        "Standard Xiaomi and Pro must use different base URLs"
    )


# ── Production credential validation ────────────────────────────────────

def test_production_rejects_all_llm_keys_placeholder():
    """生产环境：三个核心 LLM key 都是占位符时拒绝启动"""
    with pytest.raises(ValueError, match="At least one LLM API key"):
        _settings_with_credentials(
            LLM_API_KEY="your_llm_api_key_here",
            ZHIPU_API_KEY="your_zhipu_api_key",
            DEEPSEEK_API_KEY="changeme_deepseek",
        )


def test_production_allows_one_valid_llm_key():
    """生产环境：至少一个核心 LLM key 有效即可通过"""
    cfg = _settings_with_credentials(
        LLM_API_KEY="",
        ZHIPU_API_KEY="",
        DEEPSEEK_API_KEY="sk-real-deepseek-key-123",
    )
    assert cfg.DEEPSEEK_API_KEY == "sk-real-deepseek-key-123"


def test_production_rejects_empty_critical_secrets():
    """生产环境：关键基础设施密钥不能为空"""
    with pytest.raises(ValueError, match="must be set to a real value"):
        _settings_with_credentials(
            INTERNAL_API_KEY="",
        )
