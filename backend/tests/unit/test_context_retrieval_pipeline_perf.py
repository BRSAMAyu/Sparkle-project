"""C-03 · 硬过滤→rerank pipeline 性能剖面（1000+ 合成候选）。

卡面验收：「1000+ memory synthetic 下仍稳定——过滤+rerank 延迟剖面，无超线性
退化」。设计约束：

- **真实 LLM / embedding 0 次**：rerank_fn 是合成向量余弦排序（预生成随机
  单位向量 + 点积，确定性 seed）；滤芯走真实实现（M-03 prefilter +
  C-03 knowledge 滤芯），候选为合成 ORM/namespace 对象（无 DB 会话）。
- **规模轴**：100 / 250 / 500 / 1000 / 2000（每档 memory 与 knowledge 各 N，
  即最大档 4000 候选总量）；每档 best-of-3 计时（共享 CI 机器方差抑制）。
- **稳定性断言**：
  1. 绝对预算：1000 档（2000 候选）全管道 < 5s（防病理回归的宽上界）；
  2. 无超线性：最大档 per-candidate µs ≤ 3× 最小档 per-candidate µs
     （线性扫描 + O(n log n) 排序的合理包络；超线性即红）；
  3. 正确性不随规模漂移：每档 rerank 输入的非法候选恒为 0、合法计数与
     构造split 一致（性能路径同时是正确性回归钉）。

延迟剖面表随测试打印（stdout），供 v3-output/C-03/REPORT.md 引用；
可复跑剖面脚本：scripts/devtools/c03_pipeline_perf_profile.py。
"""

from __future__ import annotations

import random
import time
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.core.time_utils import utcnow
from app.models.memory import EpisodicMemory
from app.services.context_retrieval_pipeline import (
    KnowledgeAccessContext,
    run_hard_filter_pipeline,
)
from app.services.memory_retrieval_prefilter import (
    PURPOSE_LLM_CONTEXT,
    RetrievalContext,
)

SCALES = (100, 250, 500, 1000, 2000)
SEED = 20260919


# ---------------------------------------------------------------------------
# 合成候选工厂（确定性；illegal 比例固定 ~40%，覆盖 M-03 六维度中可合成的
# 四类 + knowledge 三类非法）
# ---------------------------------------------------------------------------


def _memory_candidates(n: int, user_id, now, rng: random.Random) -> list[EpisodicMemory]:
    rows: list[EpisodicMemory] = []
    for i in range(n):
        kind = i % 10
        row = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            summary=f"synthetic episodic {i}",
            source_type="chat_turn",
            source_lane="direct_capture",
            subject_type="self",
            occurred_at=now - timedelta(hours=rng.randint(1, 48)),
            created_at=now - timedelta(hours=rng.randint(1, 48)),
            importance_score=0.5,
            evidence_refs=[{"type": "user_state", "id": "t"}],
        )
        if kind == 0:  # wrong user
            row.user_id = uuid4()
        elif kind == 1:  # revoked (status machine cut)
            row.revoked_at = now
        elif kind == 2:  # superseded (status machine cut)
            row.superseded_by_id = uuid4()
        elif kind == 3:  # expired commitment (ttl cut)
            row.subject_type = "commitment"
            row.decay_policy = "due_at+7d"
            row.due_at = now - timedelta(days=30)
        rows.append(row)
    return rows


def _knowledge_candidates(n: int, user_id: str, group_id: str, rng: random.Random) -> list[SimpleNamespace]:
    docs: list[SimpleNamespace] = []
    for i in range(n):
        kind = i % 10
        doc = SimpleNamespace(
            id=f"synthetic-doc-{i}",
            parent_id=f"parent-{i}",
            content=" ".join(f"token{rng.randint(0, 999)}" for _ in range(24)),
            source_type="document_chunk",
            user_id=user_id,
            vector=[rng.random() for _ in range(16)],
        )
        if kind == 0:  # wrong user
            doc.user_id = f"other-user-{i}"
        elif kind == 1:  # group inaccessible（group 恒不在 allowed 集，保证确定性 split）
            doc.group_id = f"group-blocked-{i}"
            doc.user_id = ""
        elif kind == 2:  # unattributed
            doc.user_id = ""
        elif kind == 3:  # lifecycle inactive
            doc.lifecycle_status = "archived"
        docs.append(doc)
    return docs


def _make_rerank(query_vector: list[float], top_k: int):
    """合成向量 rerank：候选预挂随机向量，rerank = 余弦排序（无模型调用）。"""

    def rerank(candidates: list) -> list:
        def score(candidate):
            vector = getattr(candidate, "vector", None)
            if not vector:
                return 0.0
            dot = sum(a * b for a, b in zip(query_vector, vector, strict=False))
            norm = sum(v * v for v in vector) ** 0.5
            return dot / norm if norm else 0.0

        return sorted(candidates, key=score, reverse=True)[:top_k]

    return rerank


def _expected_legal_memory(n: int) -> int:
    # kind in {0,1,2,3} 每 10 个里占 4 个 → illegal = ceil 分布
    return sum(1 for i in range(n) if i % 10 not in (0, 1, 2, 3))


def _expected_legal_knowledge(n: int) -> int:
    return sum(1 for i in range(n) if i % 10 not in (0, 1, 2, 3))


def _run_once(memory, knowledge, retrieval_ctx, knowledge_ctx, top_k):
    rerank = _make_rerank([0.5] * 16, top_k)
    start = time.perf_counter()
    result = run_hard_filter_pipeline(
        memory_candidates=memory,
        retrieval_ctx=retrieval_ctx,
        knowledge_candidates=knowledge,
        knowledge_ctx=knowledge_ctx,
        rerank_fn=rerank,
    )
    return (time.perf_counter() - start) * 1000.0, result


def _profile_row(scale: int) -> tuple[float, dict]:
    rng = random.Random(SEED + scale)
    user_id = uuid4()
    now = utcnow()
    memory = _memory_candidates(scale, user_id, now, rng)
    knowledge = _knowledge_candidates(scale, str(user_id), "group-0", rng)
    retrieval_ctx = RetrievalContext(user_id=str(user_id), purpose=PURPOSE_LLM_CONTEXT, now=now)
    knowledge_ctx = KnowledgeAccessContext(user_id=str(user_id), allowed_group_ids=frozenset({"group-0"}))

    # best-of-3（首次运行含 warmup 效应，取最快抑制调度噪声；表中各列均取
    # 同一最快 run，保证 filter/rerank/total 自洽）
    runs = [_run_once(memory, knowledge, retrieval_ctx, knowledge_ctx, top_k=50) for _ in range(3)]
    best_ms, result = min(runs, key=lambda run: run[0])

    # 正确性钉：非法候选恒 0 进入 rerank，合法计数与构造 split 一致
    assert result is not None
    assert result.report["rerank"]["input_count"] == _expected_legal_memory(scale) + _expected_legal_knowledge(
        scale
    ), f"scale={scale}: rerank input {result.report['rerank']['input_count']} != expected legal split"
    memory_channel = result.report["channels"]["memory"]
    knowledge_channel = result.report["channels"]["knowledge"]
    assert memory_channel["allowed_count"] == _expected_legal_memory(scale)
    assert knowledge_channel["allowed_count"] == _expected_legal_knowledge(scale)
    assert memory_channel["reason_counts"].get("user:wrong_user") == sum(1 for i in range(scale) if i % 10 == 0)
    assert knowledge_channel["reason_counts"].get("knowledge:wrong_user") == sum(1 for i in range(scale) if i % 10 == 0)
    rerank_input_ids = {getattr(candidate, "id", None) for candidate in result.rerank_input}
    illegal_ids = {row.id for row in memory if row.user_id != user_id}
    assert not (rerank_input_ids & illegal_ids), "illegal memory candidate reached rerank"
    return best_ms, {
        "scale": scale,
        "total_candidates": 2 * scale,
        "filter_ms": round(memory_channel["latency_ms"] + knowledge_channel["latency_ms"], 3),
        "total_ms": round(best_ms, 3),
        "rerank_ms": result.report["rerank"]["latency_ms"],
        "per_candidate_us": round(best_ms * 1000.0 / (2 * scale), 2),
    }


def test_pipeline_perf_profile_and_linearity():
    rows = []
    for scale in SCALES:
        rows.append(_profile_row(scale)[1])

    header = f"{'candidates':>10} {'filter_ms':>10} {'rerank_ms':>10} {'total_ms':>10} {'per_cand_us':>12}"
    print("\nC-03 hard-filter pipeline perf profile (memory+knowledge, best-of-3)")
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['total_candidates']:>10} {row['filter_ms']:>10} {row['rerank_ms']:>10} "
            f"{row['total_ms']:>10} {row['per_candidate_us']:>12}"
        )

    # 1) 绝对预算：1000+ memory 档（2000 总候选）全管道 < 5s（宽上界）
    scale_1000 = next(row for row in rows if row["scale"] == 1000)
    assert scale_1000["total_ms"] < 5000, f"1000-scale pipeline took {scale_1000['total_ms']}ms (>5s budget)"
    scale_2000 = next(row for row in rows if row["scale"] == 2000)
    assert scale_2000["total_ms"] < 10000, f"2000-scale pipeline took {scale_2000['total_ms']}ms (>10s budget)"

    # 2) 无超线性：最大档 per-candidate µs ≤ 3× 最小档
    ratio = scale_2000["per_candidate_us"] / max(rows[0]["per_candidate_us"], 0.001)
    print(f"\nlinearity ratio (per-candidate us @2000 / @100) = {ratio:.2f}x (bound: 3x)")
    assert ratio <= 3.0, (
        f"superlinear degradation: per-candidate {rows[0]['per_candidate_us']}us @100 -> "
        f"{scale_2000['per_candidate_us']}us @2000 (ratio {ratio:.2f}x > 3x)"
    )
