"""V3-FIX-333 红测：能力宣称真实化（wt642，裁决=混合轨道）。

五族能力（llm/embedding/stt/tts/ocr）状态机 DoD 词表（封闭集）：
- 键空 -> not_configured（不可用；绝不是 active/available/healthy）
- 键非空但从未有真实调用证据 -> unverified（「已配置未验证」；绝不是 active/available/healthy）
- 真实调用成功证据 -> verified
- 真实调用失败证据 -> unavailable（后续成功可翻回 verified）

非冒充声明（红线）：本套件不向任何真实供应商发起网络调用，也不伪造探测
结果冒充探活。测试通过 ``capability_runtime_status.observe_*`` 与
``llm_router.report_model_success/report_model_failure`` 注入的，是
「一次真实调用的成败回调已发生」这一事实——与生产代码在真实流量路径上
调用的是同一入口——仅用于验证状态机映射与宣称词表。
"""

from __future__ import annotations

import time

import pytest

from app.core.llm_router import ModelConfig, ModelHealthState, ModelProvider, ModelTier, llm_router
from app.orchestration.capability_selection_policy import CapabilitySelectionPolicy
from app.services import embedding_service as embedding_service_module
from app.services import ocr_service as ocr_service_module
from app.services import stt_service as stt_service_module
from app.services import tts_service as tts_service_module
from app.services.capability_registry_service import CapabilityRegistryService
from app.services.capability_runtime_status import (
    aggregate_family_state,
    capability_runtime_status,
)

_ALL_STATES = {"not_configured", "unverified", "verified", "unavailable"}


@pytest.fixture()
def clean_capability_observations():
    """隔离进程级状态登记：每个用例前后清空，防全局单例跨用例污染。"""
    capability_runtime_status.reset()
    yield
    capability_runtime_status.reset()


# ---------------------------------------------------------------- #
# 1) 状态机本体（embedding/stt/tts/ocr 共用）
# ---------------------------------------------------------------- #


def test_capability_status_machine_transitions(clean_capability_observations) -> None:
    capability_runtime_status.observe_success("statemachine", "probe_ok")
    capability_runtime_status.observe_failure("statemachine", "probe_bad", detail="boom")

    assert capability_runtime_status.status("statemachine", "probe_ok").state == "verified"
    assert capability_runtime_status.status("statemachine", "probe_bad").state == "unavailable"
    # 无证据 -> None（调用方结合「键非空」得 unverified，绝不默认可用）
    assert capability_runtime_status.status("statemachine", "never_touched") is None
    # 失败后真实成功可翻回 verified
    capability_runtime_status.observe_success("statemachine", "probe_bad")
    assert capability_runtime_status.status("statemachine", "probe_bad").state == "verified"


def test_capability_family_aggregation_is_honest() -> None:
    assert aggregate_family_state(["verified", "unverified"]) == "verified"
    assert aggregate_family_state(["unverified", "not_configured"]) == "unverified"
    assert aggregate_family_state(["not_configured", "not_configured"]) == "not_configured"
    assert aggregate_family_state(["unavailable", "not_configured"]) == "unavailable"
    assert aggregate_family_state(["unavailable", "verified"]) == "verified"
    assert aggregate_family_state([]) == "not_configured"


# ---------------------------------------------------------------- #
# 2) embedding：键非空只配得上 unverified，provider_status 不再只报 configured
# ---------------------------------------------------------------- #


def test_embedding_provider_status_distinguishes_configured_from_verified(
    monkeypatch: pytest.MonkeyPatch,
    clean_capability_observations,
) -> None:
    service = embedding_service_module.EmbeddingService()
    monkeypatch.setattr(service, "dashscope_api_key", "k", raising=False)
    monkeypatch.setattr(service, "siliconflow_api_key", "", raising=False)

    payload = service.provider_status()
    assert payload["dashscope"]["configured"] is True
    # 键非空、无真实调用证据 -> unverified（不是 available/healthy）
    assert payload["dashscope"]["runtime_state"] == "unverified"
    # 键空 -> not_configured
    assert payload["siliconflow"]["runtime_state"] == "not_configured"

    # 真实调用成功回调（生产路径同一入口）-> verified
    capability_runtime_status.observe_success("embedding", "dashscope")
    payload = service.provider_status()
    assert payload["dashscope"]["runtime_state"] == "verified"

    # 真实调用失败回调 -> unavailable
    capability_runtime_status.observe_failure("embedding", "dashscope", detail="http 500")
    payload = service.provider_status()
    assert payload["dashscope"]["runtime_state"] == "unavailable"


# ---------------------------------------------------------------- #
# 3) stt / tts / ocr：新增如实 runtime_status 面
# ---------------------------------------------------------------- #


def test_stt_runtime_status_states(
    monkeypatch: pytest.MonkeyPatch,
    clean_capability_observations,
) -> None:
    monkeypatch.setattr(stt_service_module.settings, "STT_PROVIDER", "bailian", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "STT_BACKUP_PROVIDER", "xunfei", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "DASHSCOPE_API_KEY", "k", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "XUNFEI_APP_ID", "", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "XUNFEI_API_KEY", "", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "XUNFEI_API_SECRET", "", raising=False)
    service = stt_service_module.STTService()

    payload = service.runtime_status()
    # 键非空、从未探活 -> unverified；键空 -> not_configured（空位不消失，如实报名）
    assert payload["primary"]["provider"] == "bailian"
    assert payload["primary"]["state"] == "unverified"
    assert payload["backup"]["provider"] == "xunfei"
    assert payload["backup"]["state"] == "not_configured"

    # 键在 + 真实转写成败证据 -> verified / unavailable
    monkeypatch.setattr(stt_service_module.settings, "XUNFEI_APP_ID", "app", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "XUNFEI_API_KEY", "key", raising=False)
    monkeypatch.setattr(stt_service_module.settings, "XUNFEI_API_SECRET", "secret", raising=False)
    service = stt_service_module.STTService()
    capability_runtime_status.observe_success("stt", "bailian")
    capability_runtime_status.observe_failure("stt", "xunfei")
    payload = service.runtime_status()
    assert payload["primary"]["state"] == "verified"
    assert payload["backup"]["state"] == "unavailable"


def test_tts_runtime_status_states(
    monkeypatch: pytest.MonkeyPatch,
    clean_capability_observations,
) -> None:
    monkeypatch.setattr(tts_service_module.settings, "TTS_PROVIDER", "bailian", raising=False)
    monkeypatch.setattr(tts_service_module.settings, "DASHSCOPE_API_KEY", "k", raising=False)
    service = tts_service_module.TTSService()

    payload = service.runtime_status()
    assert payload["bailian"]["state"] == "unverified"

    capability_runtime_status.observe_success("tts", "bailian")
    assert service.runtime_status()["bailian"]["state"] == "verified"

    monkeypatch.setattr(tts_service_module.settings, "DASHSCOPE_API_KEY", "", raising=False)
    service = tts_service_module.TTSService()
    assert service.runtime_status()["bailian"]["state"] == "not_configured"


def test_ocr_runtime_status_states(
    monkeypatch: pytest.MonkeyPatch,
    clean_capability_observations,
) -> None:
    service = ocr_service_module.OCRService()
    monkeypatch.setattr(service, "api_key", "k", raising=False)
    monkeypatch.setattr(service, "siliconflow_api_key", "", raising=False)

    payload = service.runtime_status()
    # 键非空、从未探活 -> unverified；键空 -> not_configured
    assert payload["zhipu"]["state"] == "unverified"
    assert payload["siliconflow"]["state"] == "not_configured"

    # 键在 + 真实调用成败证据 -> verified / unavailable
    monkeypatch.setattr(service, "siliconflow_api_key", "k2", raising=False)
    capability_runtime_status.observe_success("ocr", "zhipu")
    capability_runtime_status.observe_failure("ocr", "siliconflow", detail="401")
    payload = service.runtime_status()
    assert payload["zhipu"]["state"] == "verified"
    assert payload["siliconflow"]["state"] == "unavailable"


# ---------------------------------------------------------------- #
# 4) registry：不再硬编码 active；models 未触达不再宣称 healthy；五族入册
# ---------------------------------------------------------------- #


def _model_config(*, api_key: str) -> ModelConfig:
    return ModelConfig(
        provider=ModelProvider.DASHSCOPE,
        model_name="test-model",
        base_url="https://example.invalid/v1",
        api_key=api_key,
        tier=ModelTier.FAST,
    )


def _health_state_in_phase(phase: str) -> ModelHealthState:
    state = ModelHealthState()
    for _ in range(state.FAILURE_THRESHOLD):
        state.record_failure()
    assert state.phase == "unhealthy"
    if phase == "probation":
        state.last_failure_at = time.monotonic() - (float(state.cooldown_seconds or 0) + 10.0)
        state.check_recovery()
        assert state.phase == "probation"
    elif phase == "healthy":
        state.reset_to_healthy()
        state.record_success()
        assert state.ever_observed is True
    return state


def test_registry_subsystems_do_not_hardcode_active() -> None:
    payload = CapabilityRegistryService().build_registry()
    subsystems = payload["subsystems"]

    for item in subsystems:
        assert "state_evidence" in item, f"subsystem {item['id']} 缺 state_evidence"
    # 唯一允许 active 的是 chat_orchestrator（自证：本响应即出自活进程）
    active_ids = {item["id"] for item in subsystems if item["state"] == "active"}
    assert active_ids <= {"chat_orchestrator"}
    # 其余 in-process 子系统如实降为 configured（装配证据，非运行宣称）
    others = {item["state"] for item in subsystems if item["id"] != "chat_orchestrator"}
    assert others <= {"configured", "not_configured", "unverified", "unavailable"}


def test_registry_models_state_mapping_is_evidence_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = {
        "claim_no_key": _model_config(api_key=""),
        "claim_never_probed": _model_config(api_key="k"),
        "claim_verified": _model_config(api_key="k"),
        "claim_probation": _model_config(api_key="k"),
        "claim_unhealthy": _model_config(api_key="k"),
    }
    healths = {
        "claim_verified": _health_state_in_phase("healthy"),
        "claim_probation": _health_state_in_phase("probation"),
        "claim_unhealthy": _health_state_in_phase("unhealthy"),
    }
    monkeypatch.setattr(llm_router, "_available_models", configs)
    monkeypatch.setattr(llm_router, "_model_health", healths)

    models = {item["key"]: item for item in CapabilityRegistryService().build_registry()["models"]}
    assert models["claim_no_key"]["state"] == "not_configured"
    assert models["claim_never_probed"]["state"] == "unverified"
    assert models["claim_verified"]["state"] == "verified"
    assert models["claim_probation"]["state"] == "degraded"
    assert models["claim_unhealthy"]["state"] == "unavailable"


def test_registry_canonical_model_availability_uses_honest_vocab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = {
        "claim_no_key": _model_config(api_key=""),
        "claim_never_probed": _model_config(api_key="k"),
    }
    monkeypatch.setattr(llm_router, "_available_models", configs)
    monkeypatch.setattr(llm_router, "_model_health", {})

    capabilities = {
        item["capability_id"]: item
        for item in CapabilityRegistryService().build_registry()["canonical_capabilities"]
    }
    assert capabilities["model:claim_no_key"]["availability"] == "not_configured"
    assert capabilities["model:claim_never_probed"]["availability"] == "unverified"


def test_registry_surfaces_five_media_families_with_honest_availability() -> None:
    capabilities = CapabilityRegistryService().build_registry()["canonical_capabilities"]
    media_items = [item for item in capabilities if item.get("capability_kind") == "media"]
    media_ids = {item["capability_id"] for item in media_items}
    assert {"media:embedding", "media:stt", "media:tts", "media:ocr"} <= media_ids
    for item in media_items:
        # 宣称词必须落在封闭集内，绝不出现无证据的 active/available/healthy
        assert item["availability"] in _ALL_STATES


def test_registry_media_availability_follows_real_evidence(
    monkeypatch: pytest.MonkeyPatch,
    clean_capability_observations,
) -> None:
    service = embedding_service_module.EmbeddingService()
    monkeypatch.setattr(service, "dashscope_api_key", "k", raising=False)
    monkeypatch.setattr(service, "siliconflow_api_key", "k", raising=False)
    monkeypatch.setattr(embedding_service_module, "embedding_service", service)

    capabilities = {
        item["capability_id"]: item
        for item in CapabilityRegistryService().build_registry()["canonical_capabilities"]
    }
    # 键非空但无证据 -> unverified（修复前这里不会有 media 条目）
    assert capabilities["media:embedding"]["availability"] == "unverified"

    capability_runtime_status.observe_success("embedding", "dashscope")
    capabilities = {
        item["capability_id"]: item
        for item in CapabilityRegistryService().build_registry()["canonical_capabilities"]
    }
    assert capabilities["media:embedding"]["availability"] == "verified"


# ---------------------------------------------------------------- #
# 5) 消费面词表：policy 认 verified 为健康、不把 unverified 冒充健康
# ---------------------------------------------------------------- #


def test_selection_policy_vocabulary_treats_verified_as_healthy() -> None:
    policy = CapabilitySelectionPolicy()
    assert "verified" in policy._HEALTHY_AVAILABILITY  # noqa: SLF001 - 词表契约断言
    assert "unverified" not in policy._HEALTHY_AVAILABILITY
    assert "unverified" not in policy._BLOCKED_AVAILABILITY
    assert "not_configured" in policy._BLOCKED_AVAILABILITY


def test_body_map_places_unverified_outside_healthy_organs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = {"claim_never_probed": _model_config(api_key="k")}
    monkeypatch.setattr(llm_router, "_available_models", configs)
    monkeypatch.setattr(llm_router, "_model_health", {})

    registry = CapabilityRegistryService().build_registry()
    body_map = CapabilitySelectionPolicy().build_body_map(
        registry=registry,
        route_intent="chat",
        capability_requirements=None,
    )
    # unverified 模型可选（available）但绝不进 healthy_organs（不冒充健康）
    assert "model:claim_never_probed" in body_map["available_organs"]
    assert "model:claim_never_probed" not in body_map["healthy_organs"]


# ---------------------------------------------------------------- #
# 6) llm_router：E-07 真实流量回调留下证据痕迹（路由语义不变）
# ---------------------------------------------------------------- #


def test_model_health_state_tracks_observation_evidence() -> None:
    fresh = ModelHealthState()
    assert fresh.ever_observed is False
    assert fresh.is_healthy is True  # 路由语义（E-02/E-07）不变：缺省不熔断

    fresh.record_success()
    assert fresh.ever_observed is True

    observed_failure = ModelHealthState()
    observed_failure.record_failure()
    assert observed_failure.ever_observed is True


def test_llm_router_report_leaves_evidence_for_registry_claims() -> None:
    registry_key = "claim_report_evidence"
    llm_router._available_models[registry_key] = _model_config(api_key="k")  # noqa: SLF001 - 测试注册
    try:
        llm_router.report_model_success(registry_key)
        state = llm_router._model_health[registry_key]  # noqa: SLF001
        assert state.ever_observed is True
    finally:
        llm_router._available_models.pop(registry_key, None)  # noqa: SLF001
        llm_router._model_health.pop(registry_key, None)  # noqa: SLF001
