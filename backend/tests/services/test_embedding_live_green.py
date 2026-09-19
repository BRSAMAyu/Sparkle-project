"""E-05 绿测：真实 key 下 embedding 真实性（1 次 API 批调用）。

断言（acceptance ②）：1024 维、非全零、非恒定（不同文本 → 不同向量，
且与零向量有实质距离），并验证版本串与配置一致。
运行：E05_LIVE=1 pytest tests/services/test_embedding_live_green.py
"""

from __future__ import annotations

import math
import os

import pytest

from app.services.embedding_service import embedding_service

pytestmark = pytest.mark.asyncio

if os.getenv("E05_LIVE") != "1":
    pytest.skip("live green test requires E05_LIVE=1 (real provider key)", allow_module_level=True)


async def test_real_embedding_1024_nonzero_nonconstant():
    if not embedding_service.is_configured():
        pytest.fail("E05_LIVE=1 but no embedding provider key configured — cannot run green test")
    texts = [
        "期末复习：操作系统的进程调度与页面置换。",
        "Machine learning: gradient descent and regularization.",
    ]
    vectors = await embedding_service.batch_embeddings(texts, text_type="document")

    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == embedding_service.embedding_dim == 1024, f"expected 1024 dims, got {len(vec)}"
        norm = math.sqrt(sum(x * x for x in vec))
        assert norm > 0.5, f"embedding near-zero (norm={norm}) — provider returned degenerate vector"

    # 非恒定：两向量必须显著不同（同模型同批不同文本余弦应远低于 1）
    dot = sum(a * b for a, b in zip(vectors[0], vectors[1], strict=True))
    norm0 = math.sqrt(sum(x * x for x in vectors[0]))
    norm1 = math.sqrt(sum(x * x for x in vectors[1]))
    cosine = dot / (norm0 * norm1)
    assert cosine < 0.98, f"two distinct texts produced near-identical vectors (cos={cosine})"

    # 版本串与配置一致（供索引/缓存隔离使用）。
    # 注意：真实模型身份来自 provider 专属配置（DASHSCOPE_EMBEDDING_MODEL），
    # 而非遗留标签 EMBEDDING_MODEL —— E-05 的版本串正是为此从 provider 派生。
    from app.config import settings as app_settings

    expected_model = (
        app_settings.SILICONFLOW_EMBEDDING_MODEL
        if embedding_service.primary_provider == "siliconflow"
        else app_settings.DASHSCOPE_EMBEDDING_MODEL
    )
    assert embedding_service.current_embedding_version() == (
        f"{embedding_service.primary_provider}/{expected_model}@{embedding_service.embedding_dim}"
    )
