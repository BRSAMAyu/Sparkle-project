#!/usr/bin/env python3
"""E-05: hybrid lexical+vector 检索基准（真实文档、真实 API、hit@5 / 时延）。

流程：
1. 建立基准语料：专用 bench 用户 + 12 个真实学习材料 chunk（中/英/代码混合），
   一次批量真实 embedding（版本打标）；
2. 6 个 paraphrase 查询（非关键词抄写，考察语义检索），预先 warm 查询向量
   （进入 embedding Redis 缓存，避免策略间时延不公平）；
3. 三种策略各跑全部查询并计时：
   - vector-only  : document_vector_search (pgvector cosine)
   - lexical-only : document_lexical_search (ILIKE token match)
   - hybrid       : document_hybrid_search (RRF + rerank)
4. 输出 hit@5 / MRR@5 / p50 / p95 到 stdout 与 --json 指定文件；
5. --cleanup 清除 bench 数据（默认跑完自动清理）。

用法（backend/ 目录，需真实 key）：
    python ../scripts/devtools/bench_hybrid_retrieval.py --json ../v3-output/E-05/benchmark.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

BENCH_USER_SUFFIX = "e05bench"

CORPUS = [
    # (section_title, content, gold_query_id)
    (
        "进程调度",
        "时间片轮转调度（Round Robin）中，时间片大小的选择至关重要：时间片过大时，多个进程需要等待整个时间片用完才发生切换，算法退化为先来先服务（FCFS），响应时间变差；时间片过小时，上下文切换开销占比过高，CPU 有效利用率下降。经验法则是一次切换的开销不应超过时间片的百分之十。",
        "q_rr_timeslice",
    ),
    (
        "页面置换",
        "请求分页系统中发生缺页中断时，需要在内存中选择一页淘汰。LRU 算法淘汰最长时间未被访问的页，近似算法 Clock（时钟）只使用访问位做环形扫描，开销更低。OPT 是理论最优但无法在线实现，只用于对比评估。抖动（thrashing）发生在进程驻留集过小、缺页率极高的时候。",
        "q_page_replace",
    ),
    (
        "梯度下降",
        "批量梯度下降每步使用全部样本计算梯度，收敛稳定但代价高；随机梯度下降每步只用一个样本，噪声大但逃逸鞍点能力强；小批量是折中。学习率过大导致损失震荡甚至发散，过小则收敛缓慢。常用技巧：学习率衰减、动量、Adam 自适应。",
        "q_gd",
    ),
    (
        "过拟合",
        "模型在训练集上表现远好于验证集即为过拟合。缓解手段包括：L2 正则化惩罚大权重、Dropout 随机失活神经元、早停（early stopping）、数据增强与降低模型复杂度。偏差-方差权衡指出容量越大方差越大，需要匹配数据规模。",
        "q_overfit",
    ),
    (
        "红黑树",
        "红黑树是自平衡二叉搜索树，通过红黑着色约束最长路径不超过最短路径两倍，保证查找、插入、删除均为 O(log n)。与 AVL 相比平衡条件更宽松，插入删除的旋转次数更少，工程上更常用（如 C++ map 的典型实现）。",
        "q_rbt",
    ),
    (
        "哈希冲突",
        "哈希表发生冲突的解决方法主要分两类：开放寻址（线性探测、二次探测、双重哈希）与链地址法（拉链）。负载因子超过阈值时需要扩容再散列。一致性哈希通过虚拟节点把键空间映射到环上，是分布式缓存分片与容错的基础。",
        "q_hash",
    ),
    (
        "TCP 拥塞控制",
        "TCP 拥塞控制包含慢启动、拥塞避免、快重传与快恢复四个部分。慢启动阶段拥塞窗口（cwnd）每个 RTT 指数增长，到达阈值（ssthresh）后进入线性增长的拥塞避免阶段；发生三次重复 ACK 触发快重传，超时则 cwnd 重置为 1 重新慢启动。",
        "q_tcp",
    ),
    (
        "HTTP2",
        "HTTP/2 相比 1.1 的核心改进：二进制分帧、头部压缩（HPACK）、服务器推送，以及最重要的一条 TCP 连接上的多路复用——多个 stream 并行交错传输，消除了 HTTP/1.1 的队头阻塞（应用层），但 TCP 层队头阻塞仍在，HTTP/3 改用 QUIC 解决。",
        "q_http2",
    ),
    (
        "特征值",
        "方阵 A 的特征值 λ 满足 det(A - λI) = 0，对应非零解向量称为特征向量。对称矩阵的特征值必为实数且特征向量正交，可正交对角化。谱定理把矩阵分解为 QΛQ^T，是 PCA 降维与谱聚类等算法的数学基础。",
        "q_eig",
    ),
    (
        "图着色",
        "图着色问题要求相邻顶点颜色不同，最少颜色数称为色数。四色定理说明任意平面图可用四种颜色着色。判定任意图是否 k-可着色在 k>=3 时是 NP 完全问题，贪心策略按度数排序依次着色是常用近似。",
        "q_coloring",
    ),
    (
        "CAP Theorem",
        "The CAP theorem states that a distributed data store can provide at most two of three guarantees: consistency, availability, and partition tolerance. Since network partitions are unavoidable in practice, real systems choose between CP (e.g., ZooKeeper) and AP (e.g., Cassandra) behavior during a partition.",
        "q_cap",
    ),
    (
        "quickSort",
        "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    mid = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + mid + quicksort(right)\n# Average time complexity O(n log n); worst case O(n^2) with bad pivots.",
        "q_sort",
    ),
]

QUERIES = [
    ("q_rr_timeslice", "轮转调度的时间片设得太大会有什么问题？"),
    ("q_page_replace", "缺页的时候应该按什么策略挑选被换出的页面？"),
    ("q_gd", "学习率设置不合适对训练有什么影响？"),
    ("q_overfit", "训练集准确率很高但验证集很差，有哪些缓解办法？"),
    ("q_tcp", "慢启动阶段拥塞窗口是怎么变化的？"),
    ("q_cap", "Which guarantee must a distributed store sacrifice during a network partition?"),
]


async def run_bench(json_out: str | None, keep_data: bool) -> int:
    from sqlalchemy import delete

    from app.db.session import AsyncSessionLocal
    from app.models.document_chunks import DocumentChunk
    from app.models.file_storage import StoredFile
    from app.models.user import User
    from app.services.embedding_service import embedding_service
    from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
    from app.services.rag_indexing_service import delete_document_chunk_keys, get_rag_redis

    if not embedding_service.is_configured():
        print("FATAL: embedding provider not configured (fail-closed); benchmark requires real key")
        return 2

    bench_tag = f"e05bench-{uuid.uuid4().hex[:8]}"
    user_email = f"{bench_tag}@bench.local"

    async with AsyncSessionLocal() as session:
        user = User(username=bench_tag, email=user_email, hashed_password="bench-no-login")
        session.add(user)
        await session.flush()

        file_record = StoredFile(
            user_id=user.id,
            file_name=f"{bench_tag}_corpus.txt",
            mime_type="text/plain",
            status="processed",
            file_size=0,
            bucket="e05-bench",
            object_key=f"e05-bench/{bench_tag}/corpus.txt",
        )
        session.add(file_record)
        await session.flush()

        # 1) 真实批量 embedding（1 次 API 批调用 <=10/批 → 12 条 = 2 批）
        texts = [f"{title}。{content}" for title, content, _ in CORPUS]
        vectors = await embedding_service.batch_embeddings(texts, text_type="document")
        version = embedding_service.current_embedding_version()
        gold_by_index = {}
        for i, ((title, content, gold), vector) in enumerate(zip(CORPUS, vectors)):
            session.add(
                DocumentChunk(
                    file_id=file_record.id,
                    user_id=user.id,
                    chunk_index=i,
                    section_title=title,
                    content=content,
                    embedding=vector,
                    quality_score=1.0,
                    pipeline_version="e05-bench",
                    embedding_model=version,
                    embedding_dim=len(vector),
                )
            )
            gold_by_index[i] = gold
        await session.commit()

        # 2) warm 查询向量（进入 embedding redis 缓存；6 次 API，之后三策略复用）
        for _qid, qtext in QUERIES:
            await embedding_service.get_embedding(qtext, text_type="query")

        file_ids = [file_record.id]
        retrieval = KnowledgeRetrievalService(session)

        strategies = {
            "vector_only": lambda q: retrieval.document_vector_search(
                user_id=user.id, query=q, file_ids=file_ids, limit=5, threshold=0.6
            ),
            "lexical_only": lambda q: retrieval.document_lexical_search(
                user_id=user.id, query=q, file_ids=file_ids, limit=5
            ),
            "hybrid": lambda q: retrieval.document_hybrid_search(
                user_id=user.id, query=q, file_ids=file_ids, limit=5, threshold=0.6
            ),
        }

        results: dict[str, dict] = {}
        for name, runner in strategies.items():
            hits, mrr_sum, latencies = 0, 0.0, []
            per_query = []
            for gold_id, qtext in QUERIES:
                t0 = time.perf_counter()
                items = await runner(qtext)
                latencies.append((time.perf_counter() - t0) * 1000.0)
                ranks = [gold_by_index.get(item.chunk.chunk_index) for item in items]
                rank = ranks.index(gold_id) + 1 if gold_id in ranks else 0
                if 0 < rank <= 5:
                    hits += 1
                    mrr_sum += 1.0 / rank
                per_query.append({"gold": gold_id, "rank": rank, "returned": [r for r in ranks if r]})
            lat_sorted = sorted(latencies)
            results[name] = {
                "hit@5": round(hits / len(QUERIES), 4),
                "mrr@5": round(mrr_sum / len(QUERIES), 4),
                "latency_ms_p50": round(statistics.median(latencies), 1),
                "latency_ms_p95": round(lat_sorted[max(0, int(len(lat_sorted) * 0.95) - 1)], 1),
                "latency_ms_max": round(max(latencies), 1),
                "per_query": per_query,
            }

        meta = {
            "corpus_chunks": len(CORPUS),
            "queries": len(QUERIES),
            "embedding_version": version,
            "knowledge_language": "zh+en+code",
        }

        # 清理：bench 数据用完即清（--keep-data 供复用排障）
        if not keep_data:
            redis = await get_rag_redis()
            if redis is not None:
                await delete_document_chunk_keys(redis, file_record.id)
            await session.execute(delete(DocumentChunk).where(DocumentChunk.file_id == file_record.id))
            await session.execute(delete(StoredFile).where(StoredFile.id == file_record.id))
            await session.execute(delete(User).where(User.id == user.id))
            await session.commit()
            meta["cleanup"] = "removed bench user/files/chunks/redis keys"

    print(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2))
    if json_out:
        out = Path(json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2))
        print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", default=None, help="结果 JSON 输出路径")
    parser.add_argument("--keep-data", action="store_true", help="保留 bench 数据（排障用）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_bench(args.json, args.keep_data)))
