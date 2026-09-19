"""E-05 fail-closed 单元测试（无网络、无真实 key）。

红→绿对照（见 v3-output/E-05/REPORT.md）：
- RED（旧代码）：DEMO_MODE=True 且无 key 时 batch_embeddings 静默返回
  [[0.0]*1024]，零向量进入检索/索引 → 本文件中的
  test_no_key_demo_mode_never_returns_zero_vectors 在旧代码上失败。
- GREEN（E-05 后）：无 key → EmbeddingNotConfiguredError；供应商失败 /
  返回零向量 / 维度不符 → EmbeddingProviderError；绝不返回占位向量。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.services.embedding_service as emb_mod
from app.services.embedding_service import (
    EmbeddingNotConfiguredError,
    EmbeddingProviderError,
    EmbeddingService,
    stamp_embedding_version,
)


@pytest.fixture(autouse=True)
def _reset_circuit_breaker_local_state():
    from app.services import circuit_breaker as cb_mod

    cb_mod._LOCAL_FAILURES.clear()
    cb_mod._LOCAL_OPEN.clear()
    yield
    cb_mod._LOCAL_FAILURES.clear()
    cb_mod._LOCAL_OPEN.clear()


def _make_service(
    monkeypatch,
    *,
    dashscope_key: str = "",
    siliconflow_key: str = "",
    demo_mode: bool = False,
    backup_provider: str = "siliconflow",
):
    # 钉住模型配置，测试不随环境 .env 漂移
    monkeypatch.setattr(emb_mod.settings, "EMBEDDING_PROVIDER", "dashscope")
    monkeypatch.setattr(emb_mod.settings, "EMBEDDING_BACKUP_PROVIDER", backup_provider)
    monkeypatch.setattr(emb_mod.settings, "DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
    monkeypatch.setattr(emb_mod.settings, "SILICONFLOW_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
    monkeypatch.setattr(emb_mod.settings, "EMBEDDING_DIM", 1024)
    monkeypatch.setattr(emb_mod.settings, "DASHSCOPE_API_KEY", dashscope_key)
    monkeypatch.setattr(emb_mod.settings, "SILICONFLOW_API_KEY", siliconflow_key)
    monkeypatch.setattr(emb_mod.settings, "DEMO_MODE", demo_mode)
    return EmbeddingService()


class TestNotConfiguredFailClosed:
    async def test_no_key_raises_not_configured(self, monkeypatch):
        svc = _make_service(monkeypatch)
        assert not svc.is_configured()
        with pytest.raises(EmbeddingNotConfiguredError) as exc_info:
            await svc.get_embedding("期末复习 操作系统")
        # 错误必须指明缺哪些环境变量（可据此明确关闭功能）
        assert "DASHSCOPE_API_KEY" in str(exc_info.value)
        assert "SILICONFLOW_API_KEY" in str(exc_info.value)

    async def test_no_key_demo_mode_never_returns_zero_vectors(self, monkeypatch):
        """RED（旧代码）/ GREEN（E-05）：DEMO_MODE 不构成零向量回退的理由。"""
        svc = _make_service(monkeypatch, demo_mode=True)
        with pytest.raises(EmbeddingNotConfiguredError):
            await svc.batch_embeddings(["hello", "world"])

    async def test_not_configured_is_not_retried(self, monkeypatch):
        """EmbeddingNotConfiguredError 必须立即抛出（不消耗 tenacity 重试）。"""
        svc = _make_service(monkeypatch)
        calls = []

        async def _spy(*args, **kwargs):
            calls.append(1)

        monkeypatch.setattr(svc, "_dashscope_embeddings", _spy)
        with pytest.raises(EmbeddingNotConfiguredError):
            await svc.batch_embeddings(["hello"])
        assert calls == []


def _core_batch(svc: EmbeddingService, texts: list[str]):
    """直接调用未装饰的核心函数（跳过 tenacity 等待，测试提速且不影响语义）。"""
    wrapped = getattr(type(svc).batch_embeddings, "__wrapped__", None)
    if wrapped is not None:
        return wrapped(svc, texts)
    return svc.batch_embeddings(texts)


class TestProviderFailureFailClosed:
    async def test_wrong_key_raises_provider_error(self, monkeypatch):
        """错误 key（HTTP 非 200）→ 显式失败，绝不静默降级为零向量。"""
        if emb_mod.dashscope is None:
            pytest.skip("dashscope package not installed")

        svc = _make_service(monkeypatch, dashscope_key="sk-invalid-key")

        def _fake_call(**payload):
            return SimpleNamespace(status_code=401, code="InvalidApiKey", message="Invalid API-key")

        monkeypatch.setattr(emb_mod.dashscope.TextEmbedding, "call", _fake_call)
        with pytest.raises(EmbeddingProviderError):
            await _core_batch(svc, ["hello"])

    async def test_provider_returning_zero_vector_is_rejected(self, monkeypatch):
        if emb_mod.dashscope is None:
            pytest.skip("dashscope package not installed")

        svc = _make_service(monkeypatch, dashscope_key="sk-test")

        def _fake_call(**payload):
            n = len(payload["input"])
            return SimpleNamespace(
                status_code=200,
                output={"embeddings": [{"embedding": [0.0] * svc.embedding_dim} for _ in range(n)]},
            )

        monkeypatch.setattr(emb_mod.dashscope.TextEmbedding, "call", _fake_call)
        with pytest.raises(EmbeddingProviderError):
            await _core_batch(svc, ["hello"])

    async def test_provider_wrong_dimension_is_rejected(self, monkeypatch):
        if emb_mod.dashscope is None:
            pytest.skip("dashscope package not installed")

        svc = _make_service(monkeypatch, dashscope_key="sk-test")

        def _fake_call(**payload):
            n = len(payload["input"])
            return SimpleNamespace(
                status_code=200,
                output={"embeddings": [{"embedding": [0.1, 0.2, 0.3]} for _ in range(n)]},
            )

        monkeypatch.setattr(emb_mod.dashscope.TextEmbedding, "call", _fake_call)
        with pytest.raises(EmbeddingProviderError):
            await _core_batch(svc, ["hello"])

    async def test_cache_poisoned_zero_entry_treated_as_miss(self, monkeypatch):
        """Redis 缓存中的零向量（历史脏数据）不得被直接复用。"""
        if emb_mod.dashscope is None:
            pytest.skip("dashscope package not installed")

        svc = _make_service(monkeypatch, dashscope_key="sk-test")

        def _fake_call(**payload):
            n = len(payload["input"])
            return SimpleNamespace(
                status_code=200,
                output={"embeddings": [{"embedding": [0.01] * svc.embedding_dim} for _ in range(n)]},
            )

        monkeypatch.setattr(emb_mod.dashscope.TextEmbedding, "call", _fake_call)

        cache_store: dict[str, list] = {}

        async def fake_get(key):
            return cache_store.get(key)

        async def fake_set(key, value, ttl=None):
            cache_store[key] = value

        monkeypatch.setattr(emb_mod.cache_service, "get", fake_get)
        monkeypatch.setattr(emb_mod.cache_service, "set", fake_set)

        # 预置被"投毒"的零向量缓存
        import hashlib

        poisoned_key = (
            f"embedding:{svc.current_version_token()}:document:" f"{hashlib.sha256(b'hello').hexdigest()[:32]}"
        )
        cache_store[poisoned_key] = [0.0] * svc.embedding_dim

        result = await svc.get_embedding("hello")
        assert len(result) == svc.embedding_dim
        assert any(result), "must not return the poisoned all-zero cache entry"


class TestVersionIdentity:
    def test_current_embedding_version_format(self, monkeypatch):
        svc = _make_service(monkeypatch)
        assert svc.current_embedding_version() == "dashscope/text-embedding-v4@1024"

    def test_provider_version_is_provider_scoped(self, monkeypatch):
        """D1：版本身份以供应商为前缀——不同供应商即使同名模型也是不同版本，
        这是异构 failover 必须被拒绝的根因。"""
        svc = _make_service(monkeypatch, dashscope_key="sk-a", siliconflow_key="sk-b")
        assert svc.provider_version("dashscope") == "dashscope/text-embedding-v4@1024"
        assert svc.provider_version("siliconflow") == "siliconflow/Qwen/Qwen3-Embedding-4B@1024"
        assert svc.provider_version("dashscope") != svc.provider_version("siliconflow")
        # 当前版本恒等于主供应商的解析版本（版本戳唯一来源）
        assert svc.current_embedding_version() == svc.provider_version(svc.primary_provider)

    def test_provider_status_exposes_resolved_versions(self, monkeypatch):
        """D1：诊断面必须能看出备用供应商被跳过的原因（异构版本）。"""
        svc = _make_service(monkeypatch, dashscope_key="sk-a", siliconflow_key="sk-b")
        status = svc.provider_status()
        assert status["dashscope"]["resolved_version"] == "dashscope/text-embedding-v4@1024"
        assert status["siliconflow"]["resolved_version"] == "siliconflow/Qwen/Qwen3-Embedding-4B@1024"
        assert "sk-" not in str(status)

    def test_version_token_is_key_safe(self, monkeypatch):
        svc = _make_service(monkeypatch)
        token = svc.current_version_token()
        assert token == "dashscope_text_embedding_v4_1024"
        assert ":" not in token and "/" not in token and "@" not in token

    def test_provider_status_hides_keys(self, monkeypatch):
        svc = _make_service(monkeypatch, dashscope_key="sk-secret-value")
        status = svc.provider_status()
        assert status["dashscope"]["configured"] is True
        assert "sk-secret-value" not in str(status)

    def test_stamp_embedding_version(self, monkeypatch):
        class _Node:
            embedding_model = None
            embedding_dim = None

        # stamp 读取模块级全局实例：钉住其配置避免环境漂移
        monkeypatch.setattr(emb_mod.embedding_service, "primary_provider", "dashscope")
        monkeypatch.setattr(emb_mod.embedding_service, "dashscope_model", "text-embedding-v4")
        monkeypatch.setattr(emb_mod.embedding_service, "embedding_dim", 1024)

        node = _Node()
        stamp_embedding_version(node, [0.1] * 1024)
        assert node.embedding_model == "dashscope/text-embedding-v4@1024"
        assert node.embedding_dim == 1024

    def test_cache_key_includes_version(self, monkeypatch):
        """同文本在不同模型版本下必须产生不同 embedding 缓存键。"""
        svc = _make_service(monkeypatch)
        v1 = svc.current_version_token()
        monkeypatch.setattr(svc, "embedding_dim", 768)
        v2 = svc.current_version_token()
        assert v1 != v2


class TestHeterogeneousFailoverFailClosed:
    """E-05 D1（R2 返修）：版本戳必须反映实际执行 embed 的供应商。

    取舍：选择"异构 failover 拒绝"而非"按实际供应商打标"。理由见
    REVIEW_RECEIPT_2 D1 与 REPORT §R2：查询侧 failover 会拿备用模型向量去比
    主模型索引（写侧打标救不了查询侧）；缓存命中+备用补嵌的混合批次没有
    单一真实版本；truthful 打标会把 failover 窗口的写入打进任何查询都看不见
    的命名空间（静默写不可见）。fail-closed 复用既定降级路径（词法检索），
    且 rebuild/回滚脚本保持单版本保证。
    """

    async def test_cross_provider_failover_is_refused(self, monkeypatch):
        """主供应商失败时不得切到异构备用供应商（防版本戳/缓存键被污染）。"""
        svc = _make_service(monkeypatch, dashscope_key="sk-a", siliconflow_key="sk-b")
        calls: list[str] = []

        async def _ds_fail(texts, text_type="document"):
            calls.append("dashscope")
            raise RuntimeError("simulated primary outage")

        async def _sf_should_never_run(texts):
            calls.append("siliconflow")
            return [[0.01] * svc.embedding_dim for _ in texts]

        monkeypatch.setattr(svc, "_dashscope_embeddings", _ds_fail)
        monkeypatch.setattr(svc, "_siliconflow_embeddings", _sf_should_never_run)

        with pytest.raises(EmbeddingProviderError) as exc_info:
            await _core_batch(svc, ["hello"])

        assert calls == ["dashscope"], "heterogeneous backup provider must never be called"
        # 错误必须显式说明异构跳过原因（可观测，而非静默少了一个供应商）
        msg = str(exc_info.value)
        assert "siliconflow" in msg and "version isolation" in msg

    async def test_same_provider_retry_still_works(self, monkeypatch):
        """同版本（同供应商）的重试/切换保留——守卫只拦异构，不拦重试。"""
        svc = _make_service(monkeypatch, dashscope_key="sk-a", siliconflow_key="", backup_provider="dashscope")
        attempts: list[int] = []

        async def _flaky(texts, text_type="document"):
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("transient failure")
            return [[0.02] * svc.embedding_dim for _ in texts]

        monkeypatch.setattr(svc, "_dashscope_embeddings", _flaky)
        result = await _core_batch(svc, ["hello"])
        assert len(attempts) == 2
        assert len(result[0]) == svc.embedding_dim and any(result[0])

    async def test_failover_vectors_always_match_stamped_version(self, monkeypatch):
        """版本溯源不变量（D1 探针口径）：成功路径返回的向量必须来自
        current_embedding_version() 所标识的供应商——任何调用点拿它打戳都成立。"""
        svc = _make_service(monkeypatch, dashscope_key="sk-a", siliconflow_key="sk-b")
        served_by: list[str] = []

        async def _ds_ok(texts, text_type="document"):
            served_by.append("dashscope")
            return [[0.03] * svc.embedding_dim for _ in texts]

        # 屏蔽 embedding 结果缓存（防历史缓存命中绕过真实供应商调用）
        async def _cache_miss(key):
            return None

        async def _cache_noop_set(key, value, ttl=None):
            return None

        monkeypatch.setattr(emb_mod.cache_service, "get", _cache_miss)
        monkeypatch.setattr(emb_mod.cache_service, "set", _cache_noop_set)
        monkeypatch.setattr(svc, "_dashscope_embeddings", _ds_ok)

        vectors = await _core_batch(svc, ["hello"])
        assert len(vectors[0]) == svc.embedding_dim
        # 实际服务供应商 == 版本串里的供应商（PROVENANCE MATCH）
        assert served_by == ["dashscope"]
        assert svc.current_embedding_version().startswith(f"{served_by[0]}/")
