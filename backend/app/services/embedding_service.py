"""
向量嵌入服务 (Embedding Service)
用于将文本转换为向量表示，支持语义搜索

支持双供应商配置（DashScope 主 / SiliconFlow 备）。

E-05 fail-closed 契约：
- 无任何可用 key -> EmbeddingNotConfiguredError（调用方据此明确关闭向量能力），
  绝不静默返回随机/零向量（旧 DEMO_MODE 零向量回退已于 E-05 移除）。
- 供应商失败 -> 显式 RuntimeError，由调用方降级（词法检索/关闭功能）。
- current_embedding_version() 提供模型身份（provider/model@dim），
  检索与缓存必须按它做版本隔离，防止跨模型余弦相似度污染。

E-05 D1（R2 返修）版本溯源不变量：本服务返回的**任何**向量都保证由
current_embedding_version() 所标识的供应商/模型生成。为此跨供应商的异构
failover 被禁止（dashscope 失败不会切到 siliconflow）：两个供应商的模型与
服务栈不同（dashscope 传 text_type=query/document，siliconflow 端点不接收），
向量不在同一余弦空间——写库会打上错误版本戳、查询侧会拿备用模型向量去比
主模型索引，两侧都击穿版本隔离；embedding 缓存键也会被备模型向量污染。
供应商故障时 fail-closed（EmbeddingProviderError），由调用方走既定降级路径
（词法检索/语义缓存跳过），而不是产出带错误溯源的向量。
"""
import asyncio
import hashlib
from http import HTTPStatus

import httpx
from loguru import logger
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.cache import cache_service
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service

try:
    import dashscope
except ImportError:  # pragma: no cover - optional dependency in some test/dev envs
    dashscope = None


class EmbeddingProviderError(RuntimeError):
    """所有 embedding 供应商都失败了（fail-closed，不返回零向量）。"""


class EmbeddingNotConfiguredError(EmbeddingProviderError):
    """没有任何 embedding 供应商配置了 API key。

    调用方捕获此错误后应明确关闭依赖向量的功能（返回空结果 + 显式原因），
    而不是重试或使用占位向量。tenacity 不重试此类错误。
    """


class EmbeddingService:
    """
    文本向量嵌入服务

    支持双供应商配置：
    - DashScope (阿里云百炼 SDK) - 使用 text-embedding-v4
    - SiliconFlow (HTTP API) - 使用 Qwen/Qwen3-Embedding-4B

    E-05 D1（R2）：故障切换只在**同版本**供应商之间发生（见 batch_embeddings
    的异构守卫）。跨供应商（dashscope↔siliconflow）的模型/服务栈不同，
    failover 会被显式跳过并 fail-closed，保证版本溯源不变量：
    任何返回向量 == current_embedding_version() 所标识的模型生成。
    """

    # 供应商优先级顺序
    PROVIDER_ORDER = ["dashscope", "siliconflow"]

    def __init__(self):
        self.primary_provider = settings.EMBEDDING_PROVIDER
        self.backup_provider = settings.EMBEDDING_BACKUP_PROVIDER
        self.embedding_dim = settings.EMBEDDING_DIM

        # DashScope 配置 (阿里云百炼)
        self.dashscope_api_key = settings.DASHSCOPE_API_KEY
        self.dashscope_base_url = settings.DASHSCOPE_BASE_HTTP_API_URL
        self.dashscope_model = settings.DASHSCOPE_EMBEDDING_MODEL  # text-embedding-v4

        # SiliconFlow 配置 (备用)
        self.siliconflow_api_key = settings.SILICONFLOW_API_KEY
        self.siliconflow_base_url = settings.SILICONFLOW_BASE_URL
        self.siliconflow_model = settings.SILICONFLOW_EMBEDDING_MODEL  # Qwen/Qwen3-Embedding-4B

    # ------------------------------------------------------------------ #
    # 版本身份 (E-05)                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def normalize_version_token(version: str) -> str:
        """把版本串归一化为可安全嵌入 Redis key / RediSearch tag 的 token。

        例如 ``dashscope/text-embedding-v4@1024`` -> ``dashscope_text-embedding-v4_1024``
        """
        keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        return "".join(ch if ch in keep else "_" for ch in version)

    def provider_version(self, provider: str) -> str:
        """指定供应商的解析版本串 ``{provider}/{model}@{dim}``（E-05 D1）。

        版本身份以供应商为前缀：不同供应商即使配置了同名模型，其服务栈
        （分词、text_type 语义、量化精度）也不可证明一致，一律视为不同版本
        （审计已实证 dashscope/siliconflow 的 text_type 行为不对称）。
        """
        model = self.siliconflow_model if provider == "siliconflow" else self.dashscope_model
        return f"{provider}/{model}@{self.embedding_dim}"

    def current_embedding_version(self) -> str:
        """当前 embedding 配置的规范版本串：``{provider}/{model}@{dim}``。

        检索过滤、chunk 元数据、语义缓存隔离都以它为准；配置变更（模型/维度）
        会产生新版本，旧向量与旧缓存因版本不同被隔离。

        E-05 D1（R2）不变量：本服务返回的任何向量都由该版本串标识的供应商/
        模型生成（异构 failover 在 batch_embeddings 内被拒绝），因此写点可以
        安全地用它打版本戳、检索侧用它做隔离过滤。
        """
        return self.provider_version(self.primary_provider)

    def current_version_token(self) -> str:
        """Redis key / index / tag 用的安全 token 形式。"""
        return self.normalize_version_token(self.current_embedding_version())

    def provider_status(self) -> dict[str, dict]:
        """每个供应商的配置状态（不含任何密钥内容），用于诊断与功能开关。

        E-05 D1：resolved_version 供运维直接看出"备用供应商为何不参与
        failover"（异构版本会被 batch_embeddings 的守卫跳过）。
        """
        return {
            "dashscope": {
                "configured": bool(self.dashscope_api_key),
                "model": self.dashscope_model,
                "resolved_version": self.provider_version("dashscope"),
                "env": "DASHSCOPE_API_KEY",
            },
            "siliconflow": {
                "configured": bool(self.siliconflow_api_key),
                "model": self.siliconflow_model,
                "resolved_version": self.provider_version("siliconflow"),
                "env": "SILICONFLOW_API_KEY",
            },
        }

    def is_configured(self) -> bool:
        """是否至少有一个供应商配置了 API key。"""
        return any(info["configured"] for info in self.provider_status().values())

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(EmbeddingNotConfiguredError),
    )
    async def get_embedding(self, text: str, text_type: str = "document") -> list[float]:
        """
        获取文本的向量表示

        Args:
            text: 输入文本
            text_type: query | document

        Returns:
            List[float]: 向量

        Raises:
            EmbeddingNotConfiguredError: 没有任何供应商配置 API key
            EmbeddingProviderError: 所有供应商都失败（fail-closed，无零向量回退）
        """
        embeddings = await self.batch_embeddings([text], text_type=text_type)
        return embeddings[0]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(EmbeddingNotConfiguredError),
    )
    async def batch_embeddings(self, texts: list[str], text_type: str = "document") -> list[list[float]]:
        """
        批量获取文本向量（同版本供应商内重试；跨供应商异构 failover 被拒绝）

        Args:
            texts: 文本列表
            text_type: query | document

        Returns:
            List[List[float]]: 向量列表（全部由 current_embedding_version()
            所标识的供应商/模型生成——版本溯源不变量，E-05 D1）

        Raises:
            EmbeddingNotConfiguredError: 没有任何供应商配置 API key（不重试）
            EmbeddingProviderError: 所有可用供应商都失败（fail-closed，无零向量
                回退；异构备用供应商被跳过时会在此错误中说明原因）
        """
        if not texts:
            return []

        # R5-P1-12: Cache embedding results to avoid repeated API calls
        cache_ttl = getattr(settings, "EMBEDDING_CACHE_TTL_SECONDS", 300)
        # E-05: 缓存键带上模型版本，切换 embedding 模型后旧模型的缓存向量自动失效，
        # 防止同维度不同模型的向量跨版本污染检索。
        version_token = self.current_version_token()
        cache_keys = []
        cached_results: list[list[float] | None] = [None] * len(texts)
        all_cached = True

        for i, text in enumerate(texts):
            # Use hash of text + text_type + model version as cache key
            cache_key = f"embedding:{version_token}:{text_type}:{hashlib.sha256(text.encode()).hexdigest()[:32]}"
            cache_keys.append(cache_key)
            try:
                cached = await cache_service.get(cache_key)
                if cached and isinstance(cached, list) and len(cached) == self.embedding_dim and any(cached):
                    cached_results[i] = cached
                else:
                    all_cached = False
            except Exception:
                all_cached = False

        # If all texts have cached results, return early
        if all_cached and cached_results and all(r is not None for r in cached_results):
            logger.debug(f"Embedding cache hit for {len(texts)} texts")
            return cached_results  # type: ignore[return-value]

        # Filter texts that need fresh embedding
        missing_indices = [i for i, r in enumerate(cached_results) if r is None]
        missing_texts = [texts[i] for i in missing_indices]

        # E-05 fail-closed 前置检查：没有任何供应商配置 key 时立刻显式失败。
        # 旧实现会静默跳过所有供应商，最后（DEMO_MODE 下）返回零向量——
        # 零向量会让余弦相似度静默变成垃圾结果，属于必须消除的静默失败路径。
        if not self.is_configured():
            missing = sorted(env for info in self.provider_status().values() if not info["configured"] for env in [info["env"]])
            raise EmbeddingNotConfiguredError(
                "No embedding provider is configured. "
                f"Set one of: {', '.join(missing)}. "
                "Vector-dependent features (semantic search / semantic cache) must be explicitly disabled."
            )

        # Build provider order for retry logic
        providers_to_try = self._get_provider_order()
        # E-05 D1（R2）：只有解析版本与当前版本身份一致的供应商才允许执行
        # embedding。跨供应商 failover（dashscope↔siliconflow）的模型/服务栈
        # 不同（含 text_type 语义不对称），其向量与主供应商向量不在同一余弦
        # 空间：写库会打上错误版本戳、查询侧会拿备用模型向量去比主模型索引，
        # embedding 缓存键也会被备模型向量污染——异构 failover 一律跳过
        # （fail-closed），由调用方走既定降级路径。
        active_version = self.current_embedding_version()
        skipped_heterogeneous: list[str] = []
        last_error = None
        for provider in providers_to_try:
            provider_version = self.provider_version(provider)
            if provider_version != active_version:
                skip_reason = f"{provider}:{provider_version}"
                if skip_reason not in skipped_heterogeneous:
                    skipped_heterogeneous.append(skip_reason)
                    logger.warning(
                        f"Embedding provider {provider} skipped: heterogeneous version "
                        f"({provider_version} != active {active_version}); cross-provider "
                        "failover is disabled to preserve version isolation (E-05 D1)"
                    )
                continue
            try:
                await circuit_breaker_service.check(f"embedding:{provider}")
                if provider == "dashscope":
                    if not self.dashscope_api_key:
                        continue
                    result = await self._dashscope_embeddings(missing_texts, text_type=text_type)
                elif provider == "siliconflow":
                    if not self.siliconflow_api_key:
                        continue
                    result = await self._siliconflow_embeddings(missing_texts)
                else:
                    continue
                await circuit_breaker_service.record_success(f"embedding:{provider}")

                if len(result) != len(missing_texts):
                    raise RuntimeError(
                        f"Embedding provider {provider} returned {len(result)} vectors for {len(missing_texts)} texts"
                    )
                # E-05: 向量健全性守卫——维度错误或零向量直接视为供应商失败，
                # 绝不让退化向量进入索引/检索（零向量余弦距离无意义）。
                for vec in result:
                    if not isinstance(vec, (list, tuple)) or len(vec) != self.embedding_dim:
                        raise RuntimeError(
                            f"Embedding provider {provider} returned invalid dimension "
                            f"(expected {self.embedding_dim}, got {len(vec) if isinstance(vec, (list, tuple)) else type(vec).__name__})"
                        )
                    if not any(vec):
                        raise RuntimeError(f"Embedding provider {provider} returned an all-zero vector")

                # Store results in cache and fill missing slots
                for i, idx in enumerate(missing_indices):
                    cache_key = cache_keys[idx]
                    embedding_result = result[i]
                    cached_results[idx] = embedding_result
                    try:
                        await cache_service.set(cache_key, embedding_result, ttl=cache_ttl)
                    except Exception:
                        pass  # Cache failures should not fail the request

                return cached_results  # type: ignore[return-value]
            except CircuitBreakerOpenException as e:
                logger.warning(f"Embedding provider {provider} skipped because circuit breaker is open: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Embedding provider {provider} failed: {e}")
                await circuit_breaker_service.record_failure(f"embedding:{provider}")
                last_error = e
                continue

        # 所有供应商都失败：fail-closed 显式报错。
        # （E-05：移除 DEMO_MODE 零向量静默回退——检索链宁可降级也不能喂零向量。）
        heterogeneity_note = ""
        if skipped_heterogeneous:
            heterogeneity_note = (
                f" Homogeneous failover unavailable: {', '.join(skipped_heterogeneous)} skipped "
                f"(version != {active_version}); cross-provider failover is disabled to "
                "preserve embedding version isolation (E-05 D1)."
            )
        raise EmbeddingProviderError(
            f"All embedding providers failed (providers tried: {providers_to_try}). "
            f"Last error: {last_error}.{heterogeneity_note}"
        )

    def _get_provider_order(self) -> list[str]:
        """获取供应商尝试顺序 (主供应商优先)"""
        order = [self.primary_provider, self.backup_provider]
        for provider in self.PROVIDER_ORDER:
            if provider not in order:
                order.append(provider)
        return order

    # DashScope text-embedding-v4 enforces batch_size <= 10
    DASHSCOPE_MAX_BATCH = 10

    async def _dashscope_embeddings(self, texts: list[str], text_type: str = "document") -> list[list[float]]:
        if dashscope is None:
            raise RuntimeError("dashscope package is required for dashscope embedding provider")

        # Split into chunks of DASHSCOPE_MAX_BATCH to comply with API limits
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.DASHSCOPE_MAX_BATCH):
            chunk = texts[i:i + self.DASHSCOPE_MAX_BATCH]

            def _call(batch=chunk):
                dashscope.api_key = self.dashscope_api_key
                if self.dashscope_base_url:
                    dashscope.base_http_api_url = self.dashscope_base_url
                payload = {
                    "model": self.dashscope_model,
                    "input": batch,
                    "dimension": self.embedding_dim,
                    "text_type": text_type,
                }
                return dashscope.TextEmbedding.call(**payload)

            resp = await asyncio.to_thread(_call)
            if resp.status_code != HTTPStatus.OK:
                raise RuntimeError(f"DashScope embedding failed: {resp.code} {resp.message}")

            embeddings = resp.output.get("embeddings", [])
            all_embeddings.extend([item["embedding"] for item in embeddings])

        return all_embeddings

    async def _siliconflow_embeddings(self, texts: list[str]) -> list[list[float]]:
        base_url = self.siliconflow_base_url.rstrip("/")
        url = base_url if base_url.endswith("/embeddings") else f"{base_url}/embeddings"
        payload = {
            "model": self.siliconflow_model,
            "input": texts,
            "encoding_format": "float",
            "dimensions": self.embedding_dim,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.siliconflow_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw: list[list[float] | None] = [None] * len(texts)
        for item in data["data"]:
            raw[item["index"]] = item["embedding"]
        embeddings: list[list[float]] = []
        for index, embedding in enumerate(raw):
            if embedding is None:
                raise ValueError(f"embedding response missing index {index}")
            embeddings.append(embedding)
        return embeddings


# 全局实例
embedding_service = EmbeddingService()


def stamp_embedding_version(obj, vector: list[float] | None, version: str | None = None) -> None:
    """把当前 embedding 版本写进 ORM 对象的 embedding_model/embedding_dim 字段。

    E-05 写入侧约定：任何持久化向量的地方（document chunk / knowledge node）
    都必须打上版本标记，检索侧才能做版本隔离。
    """
    version = version or embedding_service.current_embedding_version()
    if hasattr(obj, "embedding_model"):
        obj.embedding_model = version
    if hasattr(obj, "embedding_dim"):
        obj.embedding_dim = len(vector) if vector else None
