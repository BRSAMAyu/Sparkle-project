#!/usr/bin/env python3
"""G-05: Galaxy 规模梯度性能 + 恢复风暴回归（真实数据 + 真实图计算路径，可复跑）。

Usage (repo root, 指向独立性能库 + 真实 embedding key; 演示库会被 TEST-DBGUARD 语义拒收):
    cd backend && \\
    SECRET_KEY=perf \\
    DATABASE_URL='postgresql+asyncpg://postgres:***@127.0.0.1:5432/wt395_g05' \\
    REDIS_URL='redis://127.0.0.1:6379/0' \\
    EMBEDDING_PROVIDER=dashscope EMBEDDING_MODEL=text-embedding-v4 EMBEDDING_DIM=1024 \\
    DASHSCOPE_API_KEY=sk-*** \\
    ../.venv/bin/python ../scripts/devtools/g05_galaxy_scale_perf.py \\
        [--scales 50,500,5000] [--samples 30] [--storm-clients 16] [--storm-rounds 5]
        [--out ../v3-output/WT395-G05-GALAXY] [--skip-embeddings] [--keep-data]

做什么（全部走真实生产代码路径，零 mock 冒充测量值）:
  1. 每个规模档 S 生成真实 ORM 行: KnowledgeNode / NodeRelation / UserNodeStatus，
     并用真实 embedding 服务（DashScope batch, batch_size<=10）为全部节点写入真实向量。
  2. 规模梯度测量（每操作 n>=--samples, 输出 p50/p95/max）:
     get_galaxy_graph 冷/热缓存、zoom LOD(0.3) 降级、viewport(800 上限)窗口、
     calculate_user_stats、predict_next_node、semantic_search 真实 embedding 语义搜索、
     GetLearningPath 有界 BFS（近/远节点对）、GetNodeDetail。
  3. 恢复风暴（最大规模档）:
     a) 断线重连冷缓存风暴: 清缓存后 --storm-clients 并发 GetUserGalaxy × --storm-rounds 轮;
     b) 多端 CRDT 恢复风暴: 并发 SyncCollaborativeGalaxy（真实 y_py update +
        CRDTPersistenceManager Redis/DB 持久化/恢复）后再次 restore 校验合并态可读;
     c) 混合数据面风暴: 取图+节点统计+词法搜索 并发混合。
  4. graceful 降级断言: 视图 800 上限、LOD 过滤收窄、向量运行时不可用→搜索空返回不抛、
     keyword_search 兜底面可用、prerequisite 阻塞投影可运行、风暴零异常、尾部有界。
  5. 原始样本 + 汇总（由本程序从 raw 计算）落 --out 目录 raw_scale_perf.json /
     summary_scale_perf.md。汇总含阈值判定（阈值声明依据见 THRESHOLDS）。

注意: 只写 --database-url 指定的独立库；跑完默认清理本脚本生成的全部行。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# 阈值显式声明（依据见行尾注释; 全部为本机容器 headless 服务级基线, 非真机 FPS 口径）
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # 热缓存图取数是会话内常规操作: 交互级 1s 内可感知流畅（Nielsen 响应上限类）。
    "graph_warm_p95_ms": 800,
    # 冷缓存全图投影+统计+评审信号, 本机 PG16 容器: 首屏可接受 ≤5s(5000 档); 其余 ≤2.5s。
    "graph_cold_p95_ms_small": 2500,
    "graph_cold_p95_ms_large": 5000,
    # 语义搜索含真实网络 embedding RTT（DashScope 公网）: 移动端可接受 ≤2s p95。
    "search_p95_ms": 2000,
    # 学习路径 BFS 有界探索(MAX_VISITED=500)应为毫秒级 DB 读 + 内存遍历。
    "learning_path_p95_ms": 500,
    # 节点详情双查询面。
    "node_detail_p95_ms": 500,
    # 风暴尾部有界: 最慢客户端的绝对时延仍须落在冷缓存首拉 SLA 内
    # （排队使相对倍数随并发数放大, 相对单发中位数×N 的口径在低单发基线下失真,
    #  故以绝对 SLA 为门, 相对倍数只作观测记录）。
    "storm_tail_abs_budget_ms_small": 2500,
    "storm_tail_abs_budget_ms_large": 5000,
    # 语义搜索正确性: 领域内查询 top1 命中预期簇比率（真实 embedding 质量门;
    # 保守下限 0.6——只防"搜索失效", 不追求模型级最优）。
    "semantic_top1_hit_rate_min": 0.6,
    # LOD zoom<0.5 降级: 该档位以上必须返回 < 全图节点数。
    "lod_must_shrink_at_scale": 500,
}

# 主题簇（真实中文学习语面）: 语义搜索正确性的"领域内"语料。
TOPIC_CLUSTERS = [
    ("Transformer 自注意力机制", "深度学习", ["transformer", "attention", "自注意力", "深度学习"]),
    ("TCP 拥塞控制", "计算机网络", ["tcp", "拥塞控制", "慢启动", "计算机网络"]),
    ("CSS Flexbox 弹性布局", "前端开发", ["css", "flexbox", "弹性布局", "前端"]),
    ("光合作用暗反应", "生物", ["光合作用", "暗反应", "卡尔文循环", "生物"]),
    ("导数与微分中值定理", "高等数学", ["导数", "中值定理", "微积分", "数学"]),
    ("线性代数特征值分解", "高等数学", ["特征值", "特征向量", "矩阵分解", "线性代数"]),
    ("宏观经济通货膨胀", "经济学", ["通胀", "cpi", "货币政策", "经济学"]),
    ("Python 异步 asyncio", "编程语言", ["python", "asyncio", "协程", "并发"]),
    ("二次世界大战起因", "历史", ["二战", "凡尔赛", "历史", "战争史"]),
    ("英语虚拟语气", "英语语法", ["虚拟语气", "subjunctive", "英语语法", "时态"]),
]
OFF_DOMAIN_QUERIES = ["今天晚饭吃什么", "股票K线图技术分析", "猫藓治疗方法"]
FILLER_DOMAINS = [
    ("数据结构第{i}讲", "计算机基础", ["数据结构", "算法", "计算机基础"]),
    ("机器学习基础概念{i}", "机器学习", ["机器学习", "监督学习", "模型"]),
    ("近代史专题{i}", "历史", ["近代史", "历史", "专题"]),
    ("有机化学官能团{i}", "化学", ["有机化学", "官能团", "化学"]),
    ("概率统计第{i}章", "高等数学", ["概率", "统计", "数学"]),
]

SEED = 20260925


def _percentile(values: list[float], p: float) -> float:
    """线性插值百分位（NumPy 'linear' 口径）。"""
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _stats(values: list[float]) -> dict:
    return {
        "n": len(values),
        "p50_ms": round(_percentile(values, 50), 2),
        "p95_ms": round(_percentile(values, 95), 2),
        "max_ms": round(max(values), 2) if values else None,
        "mean_ms": round(statistics.fmean(values), 2) if values else None,
    }


class _GrpcContextStub:
    """最小 gRPC servicer 上下文替身: 只承载鉴权元数据传递, 不参与被测计算。"""

    def __init__(self, user_id: str):
        self._metadata = (("user-id", user_id),)

    def invocation_metadata(self):
        return self._metadata

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


def _scale_username(scale: int) -> str:
    return f"g05_wt395_{scale}"


def _scale_user_id(scale: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"wt395-g05-scale-{scale}-{SEED}")


async def generate_scale_data(db, scale: int, *, with_embeddings: bool) -> dict:
    """为规模档生成真实 ORM 行（幂等: 复跑先清同前缀数据）。

    口径说明: KnowledgeNode 无属主列（星图节点全局共享, 用户态在
    UserNodeStatus）。因此规模梯度 = 独立库内 published 节点总数; 本函数
    先全量清场（--allow-wipe 保证只对一次性库执行）再精确生成 S 个节点。
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func as sa_func
    from sqlalchemy import select

    from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus
    from app.models.user import User
    from app.services.embedding_service import embedding_service

    rng = random.Random(SEED + scale)
    user_id = _scale_user_id(scale)
    user = (await db.execute(select(User).where(User.username == _scale_username(scale)))).scalar_one_or_none()
    if user is None:
        user = User(
            id=user_id,
            username=_scale_username(scale),
            email=f"g05_wt395_{scale}@perf.local",
            hashed_password="x",
        )
        db.add(user)
        await db.flush()

    # 幂等清场: 一次性库全量清（规模 = 全库 published 节点数, 保证档位精确）
    existing = (await db.execute(select(sa_func.count()).select_from(KnowledgeNode))).scalar_one()
    if existing:
        await db.execute(sa_delete(UserNodeStatus))
        await db.execute(sa_delete(NodeRelation))
        await db.execute(sa_delete(KnowledgeNode))
        await db.flush()

    embedding_version = embedding_service.current_embedding_version()

    nodes: list[KnowledgeNode] = []
    grid_side = math.ceil(math.sqrt(scale))
    anchor_by_cluster: dict[int, list[UUID]] = {ci: [] for ci in range(len(TOPIC_CLUSTERS))}
    for i in range(scale):
        if i < len(TOPIC_CLUSTERS) * 2:
            ci = i % len(TOPIC_CLUSTERS)
            title, domain, keywords = TOPIC_CLUSTERS[ci]
            variant = "核心" if i < len(TOPIC_CLUSTERS) else "进阶"
            name = f"{title}（{variant}）"
            description = f"{domain}专题：{title}的{variant}讲解，覆盖{'、'.join(keywords[:3])}等要点。"
            anchor = True
        else:
            di = rng.randrange(len(FILLER_DOMAINS))
            title, domain, keywords = FILLER_DOMAINS[di]
            name = title.format(i=i)
            description = f"{domain}系列材料第 {i} 篇：{name}的知识点梳理与例题。"
            anchor = False
        importance = 3 if (anchor or rng.random() < 0.15) else rng.randint(1, 2)
        node = KnowledgeNode(
            id=uuid5(NAMESPACE_URL, f"wt395-g05-scale-{scale}-{SEED}-node-{i}"),
            name=name,
            description=description,
            keywords=list(keywords),
            importance_level=importance,
            is_seed=False,
            source_type="user_created",
            status="published",
            position_x=float(i % grid_side) * 90.0,
            position_y=float(i // grid_side) * 90.0,
        )
        nodes.append(node)
        if anchor:
            anchor_by_cluster[ci].append(node.id)

    embed_seconds = None
    if with_embeddings:
        texts = [f"{n.name}。{n.description or ''} 关键词：{'、'.join(n.keywords or [])}" for n in nodes]
        t0 = time.perf_counter()
        vectors = await embedding_service.batch_embeddings(texts, text_type="document")
        embed_seconds = time.perf_counter() - t0
        if len(vectors) != len(nodes):
            raise RuntimeError(f"embedding count mismatch: {len(vectors)} != {len(nodes)}")
        for node, vec in zip(nodes, vectors, strict=True):
            node.embedding = vec
            node.embedding_model = embedding_version
            node.embedding_dim = len(vec)

    db.add_all(nodes)
    await db.flush()

    relations: list[NodeRelation] = []
    for i in range(1, scale):
        parent = (i - 1) // 3
        relations.append(
            NodeRelation(
                source_node_id=nodes[parent].id,
                target_node_id=nodes[i].id,
                relation_type="prerequisite",
                strength=round(rng.uniform(0.4, 0.9), 3),
                created_by="g05_perf",
            )
        )
    for _ in range(math.ceil(scale * 0.6)):
        a, b = rng.sample(range(scale), 2)
        relations.append(
            NodeRelation(
                source_node_id=nodes[a].id,
                target_node_id=nodes[b].id,
                relation_type="related",
                strength=round(rng.uniform(0.3, 0.8), 3),
                created_by="g05_perf",
            )
        )
    db.add_all(relations)

    statuses: list[UserNodeStatus] = []
    for i in range(scale):
        if rng.random() > 0.6:
            continue
        mastery = min(100.0, max(0.0, rng.gauss(55, 25)))
        statuses.append(
            UserNodeStatus(
                user_id=user_id,
                node_id=nodes[i].id,
                mastery_score=mastery,
                bkt_mastery_prob=mastery / 100.0,
                is_unlocked=True,
                study_count=rng.randint(1, 20),
                total_minutes=rng.randint(5, 300),
                total_study_minutes=rng.randint(5, 300),
                first_unlock_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
    db.add_all(statuses)
    await db.commit()

    print(
        f"[gen] scale={scale} nodes={len(nodes)} relations={len(relations)} statuses={len(statuses)} "
        f"embed={f'{embed_seconds:.1f}s' if embed_seconds is not None else 'skipped'} "
        f"(pre-wipe {existing} rows)",
        flush=True,
    )
    return {
        "scale": scale,
        "user_id": str(user_id),
        "username": _scale_username(scale),
        "nodes": len(nodes),
        "relations": len(relations),
        "statuses": len(statuses),
        "embed_seconds": round(embed_seconds, 2) if embed_seconds is not None else None,
        "embedding_version": embedding_version if with_embeddings else None,
        "node_ids": [str(n.id) for n in nodes],
    }


async def flush_graph_cache(user_id: UUID) -> None:
    from app.config import settings
    from app.core.cache import cache_service

    if cache_service.redis is None:
        await cache_service.init_redis()
    await cache_service.delete_pattern(f"{settings.APP_NAME}:view:get_galaxy_graph:{user_id}:*")


async def measure_scale(db, session_factory, scale: int, samples: int, *, with_embeddings: bool) -> dict:
    """单规模档全部测量（真实服务路径; 每采样独立请求级会话）。"""
    from app.schemas.galaxy import GalaxyGraphResponse
    from app.services.galaxy_grpc_service import GalaxyGrpcServiceImpl
    from app.services.galaxy_service import GalaxyService

    meta = await generate_scale_data(db, scale, with_embeddings=with_embeddings)
    user_uuid = UUID(meta["user_id"])
    result: dict = {"meta": meta, "operations": {}, "correctness": {}}

    async def timed(coro_factory, n: int, timeout_s: float = 30.0) -> tuple[list[float], list]:
        latencies: list[float] = []
        payloads: list = []
        for _ in range(n):
            t0 = time.perf_counter()
            async with session_factory() as session:
                payload = await asyncio.wait_for(coro_factory(session), timeout=timeout_s)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            payloads.append(payload)
        return latencies, payloads

    def make_graph_call(**kwargs):
        async def call(session):
            graph = await GalaxyService(session).get_galaxy_graph(user_id=user_uuid, **kwargs)
            if isinstance(graph, dict):
                graph = GalaxyGraphResponse.model_validate(graph)
            return graph

        return call

    # 1) 冷缓存图取数（每采样前清缓存——断线重连后首拉口径）
    cold_lat: list[float] = []
    node_counts: set[int] = set()
    cold_errors = 0
    first_cold_error: str | None = None
    for _ in range(samples):
        await flush_graph_cache(user_uuid)
        try:
            (lat,), (payload,) = await timed(make_graph_call(), 1)
            cold_lat.append(lat)
            node_counts.add(len(payload.nodes or []))
        except Exception as exc:
            cold_errors += 1
            if first_cold_error is None:
                first_cold_error = f"{type(exc).__name__}: {exc}"
    result["operations"]["graph_cold"] = _stats(cold_lat)
    result["operations"]["graph_cold"]["errors"] = cold_errors
    result["operations"]["graph_cold"]["first_error"] = first_cold_error
    result["operations"]["graph_cold"]["node_counts_consistent"] = len(node_counts) == 1 and cold_errors == 0
    result["operations"]["graph_cold"]["nodes_returned"] = next(iter(node_counts)) if len(node_counts) == 1 else None

    # 2) 热缓存图取数
    warm_lat, warm_payloads = await timed(make_graph_call(), samples)
    result["operations"]["graph_warm"] = _stats(warm_lat)
    result["operations"]["graph_warm"]["cache_hit_consistent"] = len({len(p.nodes or []) for p in warm_payloads}) == 1

    # 3) LOD zoom=0.3 降级面（冷缓存同口径）
    lod_lat, lod_payloads = await timed(make_graph_call(zoom_level=0.3), samples)
    await flush_graph_cache(user_uuid)
    result["operations"]["graph_lod_zoom03"] = _stats(lod_lat)
    result["operations"]["graph_lod_zoom03"]["nodes_returned"] = len(lod_payloads[0].nodes or [])
    result["operations"]["graph_lod_zoom03"]["full_graph_nodes"] = result["operations"]["graph_cold"]["nodes_returned"]
    lod_n = result["operations"]["graph_lod_zoom03"]["nodes_returned"]
    full_n = result["operations"]["graph_lod_zoom03"]["full_graph_nodes"]
    result["operations"]["graph_lod_zoom03"]["shrunk"] = lod_n is not None and full_n is not None and lod_n < full_n

    # 4) viewport 窗口（800 上限降级面）
    async def viewport_call(session):
        return await GalaxyService(session).get_galaxy_graph_viewport(
            user_id=user_uuid, min_x=-1e9, max_x=1e9, min_y=-1e9, max_y=1e9
        )

    vp_lat, vp_payloads = await timed(viewport_call, samples)
    result["operations"]["graph_viewport_window"] = _stats(vp_lat)
    result["operations"]["graph_viewport_window"]["nodes_returned"] = len(vp_payloads[0].nodes or [])
    result["operations"]["graph_viewport_window"]["capped_at_800"] = (
        result["operations"]["graph_viewport_window"]["nodes_returned"] <= 800
    )

    # 5) 统计面
    async def stats_call(session):
        return await GalaxyService(session).stats.calculate_user_stats(user_id=user_uuid)

    st_lat, _ = await timed(stats_call, samples)
    result["operations"]["user_stats"] = _stats(st_lat)

    # 6) 推荐面
    async def predict_call(session):
        return await GalaxyService(session).predict_next_node(user_id=user_uuid)

    pr_lat, _ = await timed(predict_call, samples)
    result["operations"]["predict_next_node"] = _stats(pr_lat)

    # 7) 节点详情（gRPC servicer 真实路径; 替身上下文只传鉴权元数据）
    servicer = GalaxyGrpcServiceImpl(db_session_factory=session_factory)
    some_ids = [UUID(nid) for nid in meta["node_ids"][:samples]]
    dt_lat: list[float] = []
    detail_errors = 0
    for nid in some_ids:
        t0 = time.perf_counter()
        try:
            await servicer.GetNodeDetail(
                type("R", (), {"node_id": str(nid), "user_id": ""})(), _GrpcContextStub(meta["user_id"])
            )
        except Exception:
            detail_errors += 1
        dt_lat.append((time.perf_counter() - t0) * 1000.0)
    result["operations"]["node_detail_grpc"] = _stats(dt_lat)
    result["operations"]["node_detail_grpc"]["errors"] = detail_errors

    # 8) 学习路径（近对: 子→父; 远对: 树链两端——最坏有界探索）
    all_ids = [UUID(nid) for nid in meta["node_ids"]]
    near_pair = (all_ids[1], all_ids[0])

    async def path_call(pair):
        return await servicer.GetLearningPath(
            type("R", (), {"from_node_id": str(pair[0]), "to_node_id": str(pair[1]), "user_id": ""})(),
            _GrpcContextStub(meta["user_id"]),
        )

    for name, pair in (("learning_path_near", near_pair), ("learning_path_far", (all_ids[1], all_ids[-1]))):
        lat: list[float] = []
        found_flags: list[bool] = []
        path_errors = 0
        for _ in range(samples):
            t0 = time.perf_counter()
            try:
                resp = await path_call(pair)
                found_flags.append(bool(resp.path_found))
            except Exception:
                path_errors += 1
                found_flags.append(False)
            lat.append((time.perf_counter() - t0) * 1000.0)
        result["operations"][name] = _stats(lat)
        result["operations"][name]["samples_ms"] = [round(x, 2) for x in lat]
        result["operations"][name]["path_found_consistent"] = len(set(found_flags)) == 1
        result["operations"][name]["path_found"] = found_flags[0] if found_flags else None
        result["operations"][name]["errors"] = path_errors

    # 9) 语义搜索（真实 embedding; 轮换领域内/外查询）+ 正确性
    if with_embeddings:
        in_domain = [f"{title} 怎么理解" for title, _d, _k in TOPIC_CLUSTERS]
        cycle = in_domain + OFF_DOMAIN_QUERIES
        queries = [cycle[i % len(cycle)] for i in range(samples)]
        sem_lat: list[float] = []
        search_sizes: list[int] = []
        search_errors = 0
        for q in queries:
            async with session_factory() as session:
                t0 = time.perf_counter()
                try:
                    results = await asyncio.wait_for(
                        GalaxyService(session).semantic_search(user_id=user_uuid, query=q, limit=10, threshold=0.6),
                        timeout=30.0,
                    )
                    search_sizes.append(len(results))
                except Exception:
                    search_errors += 1
                sem_lat.append((time.perf_counter() - t0) * 1000.0)
        result["operations"]["semantic_search"] = _stats(sem_lat)
        result["operations"]["semantic_search"]["errors"] = search_errors
        result["operations"]["semantic_search"]["avg_hits"] = (
            round(statistics.fmean(search_sizes), 2) if search_sizes else 0.0
        )

        hits = 0
        detail_rows: list[dict] = []
        # 正确性门只在全簇语料档生效（scale >= 2×簇数: 每簇至少 核心+进阶 各一节点）。
        # 更小档位部分簇无节点, 命中率天花板受限, 只记录不判定。
        full_corpus = scale >= 2 * len(TOPIC_CLUSTERS)
        for title, _domain, _kw in TOPIC_CLUSTERS:
            query = f"{title} 怎么理解"
            async with session_factory() as session:
                results = await GalaxyService(session).semantic_search(
                    user_id=user_uuid, query=query, limit=5, threshold=0.6
                )
            top1 = results[0].node.name if results else None
            ok = bool(top1 and title[:6] in str(top1))
            hits += int(ok)
            detail_rows.append(
                {
                    "query": query,
                    "expected_cluster": title,
                    "top1": top1,
                    "top1_similarity": round(float(results[0].similarity), 4) if results else None,
                    "hit": ok,
                }
            )
        off_hits = 0
        off_detail: list[dict] = []
        for q in OFF_DOMAIN_QUERIES:
            async with session_factory() as session:
                results = await GalaxyService(session).semantic_search(
                    user_id=user_uuid, query=q, limit=5, threshold=0.6
                )
            off_hits += int(len(results) == 0)
            off_detail.append({"query": q, "hits": len(results)})
        result["correctness"]["semantic"] = {
            "in_domain_cases": detail_rows,
            "top1_hit_rate": round(hits / len(TOPIC_CLUSTERS), 3),
            "off_domain_zero_hit_rate": round(off_hits / len(OFF_DOMAIN_QUERIES), 3),
            "off_domain_cases": off_detail,
            "full_corpus": full_corpus,
        }

    return result


class _BrokenEmbeddingService:
    """异常注入替身: 只暴露检索面所需成员, 全部抛 EmbeddingNotConfiguredError。"""

    def current_embedding_version(self) -> str:
        return "broken/injected@0"

    async def get_embedding(self, text: str, text_type: str = "document") -> list[float]:
        from app.services.embedding_service import EmbeddingNotConfiguredError

        raise EmbeddingNotConfiguredError("g05 注入: embedding 供应商不可用")

    async def batch_embeddings(self, texts: list[str], text_type: str = "document") -> list[list[float]]:
        from app.services.embedding_service import EmbeddingNotConfiguredError

        raise EmbeddingNotConfiguredError("g05 注入: embedding 供应商不可用")


async def graceful_degradation_probe(db, session_factory, scale: int) -> dict:
    """异常注入口径的降级断言（只注入故障, 不伪造任何成功值）。"""
    from sqlalchemy import select

    from app.models.galaxy import KnowledgeNode, UserNodeStatus
    from app.services.galaxy_service import GalaxyService

    user_uuid = (await db.execute(UserIdOf(scale))).scalar_one()
    user_uuid = UUID(str(user_uuid))
    probe: dict = {}

    import app.services.galaxy.retrieval_service as rmod

    # keyword 面探针词: 必须取自带 UserNodeStatus 的节点（keyword_search 有租户面:
    # is_seed/source_type=seed/有用户状态三者其一）。取该用户已有状态节点自己的关键词。
    async with session_factory() as session:
        row = (
            await session.execute(
                select(KnowledgeNode.keywords)
                .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
                .where(UserNodeStatus.user_id == user_uuid, KnowledgeNode.keywords.isnot(None))
                .limit(1)
            )
        ).first()
    probe_keyword = str(next(iter(row[0]))) if row and row[0] else "知识"

    saved = rmod.embedding_service
    saved_fuse = rmod._PGVECTOR_RUNTIME_ENABLED
    rmod.embedding_service = _BrokenEmbeddingService()
    try:
        async with session_factory() as session:
            svc = GalaxyService(session)
            ranked = await svc.retrieval.semantic_search_ranked_nodes(query="TCP 拥塞控制", limit=10)
            probe["vector_down_returns_empty_no_raise"] = isinstance(ranked, list) and len(ranked) == 0
            probe["vector_down_semantic_search_no_raise"] = isinstance(
                await svc.semantic_search(user_id=user_uuid, query="TCP 拥塞控制", limit=10), list
            )
            probe["vector_fuse_blown_after_not_configured"] = rmod._PGVECTOR_RUNTIME_ENABLED is False
            kw = await svc.retrieval.keyword_search(user_uuid, probe_keyword, limit=10)
            probe["keyword_fallback_still_works"] = len(kw) > 0
            probe["keyword_probe_keyword"] = probe_keyword
    finally:
        rmod.embedding_service = saved
        rmod._PGVECTOR_RUNTIME_ENABLED = saved_fuse

    # prerequisite 阻塞投影（纯 python 判定面, 大图入参形态）
    from sqlalchemy import select

    from app.models.galaxy import KnowledgeNode, NodeRelation

    async with session_factory() as session:
        nodes = (await db.execute(select(KnowledgeNode).limit(200))).scalars().all()
        relations = (
            (
                await db.execute(
                    select(NodeRelation).where(
                        NodeRelation.source_node_id.in_([n.id for n in nodes]),
                        NodeRelation.target_node_id.in_([n.id for n in nodes]),
                    )
                )
            )
            .scalars()
            .all()
        )
    blocked = GalaxyService._get_blocked_prerequisites_by_node([(n, None) for n in nodes], list(relations))
    probe["blocked_prereq_projection_runs"] = isinstance(blocked, dict)
    return probe


def UserIdOf(scale: int):
    from sqlalchemy import select

    from app.models.user import User

    return select(User.id).where(User.username == _scale_username(scale))


async def ensure_storm_galaxy(db, user_id: UUID) -> str:
    """多端 CRDT 风暴前置: 建合法 CollaborativeGalaxy 行（FK 前提, 幂等）。"""
    from sqlalchemy import select

    from app.models.galaxy import CollaborativeGalaxy

    galaxy_id = uuid5(NAMESPACE_URL, f"wt395-g05-crdt-{SEED}")
    row = (
        await db.execute(select(CollaborativeGalaxy).where(CollaborativeGalaxy.id == galaxy_id))
    ).scalar_one_or_none()
    if row is None:
        row = CollaborativeGalaxy(
            id=galaxy_id,
            name=f"G05 Storm Galaxy {SEED}",
            description="wt395 G-05 恢复风暴专用（跑完清理）",
            created_by=user_id,
            galaxy_scope="shared",
            visibility="private",
        )
        db.add(row)
        await db.commit()
    return str(galaxy_id)


async def recovery_storm(db, session_factory, scale: int, clients: int, rounds: int) -> dict:
    """恢复风暴: a) 冷缓存并发取图 b) 多端 CRDT 并发同步+恢复校验 c) 混合数据面。"""
    import y_py as Y
    from sqlalchemy import select

    from app.core.cache import cache_service
    from app.models.galaxy import KnowledgeNode
    from app.services.galaxy_grpc_service import GalaxyGrpcServiceImpl
    from app.services.galaxy_service import GalaxyService

    user_uuid = UUID(str((await db.execute(UserIdOf(scale))).scalar_one()))
    user_id = str(user_uuid)
    storm: dict = {"scale": scale, "clients": clients, "rounds": rounds}
    servicer = GalaxyGrpcServiceImpl(db_session_factory=session_factory)

    # --- a) 断线重连冷缓存风暴 ---
    async with session_factory() as session:
        t0 = time.perf_counter()
        await GalaxyService(session).get_galaxy_graph(user_id=user_uuid)
        single_cold_ms = max((time.perf_counter() - t0) * 1000.0, 0.01)
    rounds_lat: list[list[float]] = []
    errors = 0
    counts_seen: set[int] = set()
    for _ in range(rounds):
        await flush_graph_cache(user_uuid)

        async def one_fetch(_i: int):
            async with session_factory() as session:
                t0 = time.perf_counter()
                graph = await GalaxyService(session).get_galaxy_graph(user_id=user_uuid)
                return (time.perf_counter() - t0) * 1000.0, len(graph.nodes or [])

        results = await asyncio.gather(*[one_fetch(i) for i in range(clients)], return_exceptions=True)
        round_lat: list[float] = []
        for r in results:
            if isinstance(r, BaseException):
                errors += 1
                continue
            lat, count = r
            round_lat.append(lat)
            counts_seen.add(count)
        rounds_lat.append(round_lat)
    flat = [x for r in rounds_lat for x in r]
    block = _stats(flat)
    block.update(
        {
            "errors": errors,
            "node_counts_consistent_across_clients": len(counts_seen) == 1 and errors == 0,
            "single_cold_median_ms": round(_stats([single_cold_ms])["p50_ms"], 2),
            "round_walls_ms": [round(max(r), 2) if r else None for r in rounds_lat],
        }
    )
    block["nodes_returned"] = next(iter(counts_seen)) if len(counts_seen) == 1 else None
    budget = (
        THRESHOLDS["storm_tail_abs_budget_ms_large"] if scale >= 1000 else THRESHOLDS["storm_tail_abs_budget_ms_small"]
    )
    block["tail_abs_budget_ms"] = budget
    block["tail_bounded"] = block["max_ms"] is not None and block["max_ms"] <= budget
    block["max_vs_single_cold_median"] = round(block["max_ms"] / single_cold_ms, 2) if single_cold_ms else None
    storm["reconnect_cold_storm"] = block

    # 风暴后缓存回热验证
    async with session_factory() as session:
        t0 = time.perf_counter()
        await GalaxyService(session).get_galaxy_graph(user_id=user_uuid)
        storm["post_storm_warm_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    # --- b) 多端 CRDT 并发同步风暴（真实 y_py 更新 + Redis/DB 持久化）---
    galaxy_id = await ensure_storm_galaxy(db, user_uuid)

    def make_client_update(device_idx: int) -> bytes:
        doc = Y.YDoc()
        m = doc.get_map("galaxy")
        with doc.begin_transaction() as txn:
            m.set(txn, f"device_{device_idx}", Y.YMap({"mastery": 60 + device_idx, "from": "g05"}))
        return Y.encode_state_as_update(doc)

    payloads = [make_client_update(i) for i in range(clients)]

    async def crdt_sync(payload: bytes):
        t0 = time.perf_counter()
        resp = await servicer.SyncCollaborativeGalaxy(
            type("R", (), {"galaxy_id": galaxy_id, "partial_update": payload, "user_id": ""})(),
            _GrpcContextStub(user_id),
        )
        return (time.perf_counter() - t0) * 1000.0, bool(resp.success)

    crdt_results = await asyncio.gather(*[crdt_sync(p) for p in payloads], return_exceptions=True)
    crdt_lat = [r[0] for r in crdt_results if not isinstance(r, BaseException)]
    crdt_errors = sum(1 for r in crdt_results if isinstance(r, BaseException) or not r[1])
    storm["crdt_multi_device_sync"] = _stats(crdt_lat)
    storm["crdt_multi_device_sync"]["errors"] = crdt_errors

    # 第 N+1 端重连恢复: 合并态应含全部 device 键
    from app.services.galaxy.crdt_persistence import CRDTPersistenceManager

    if cache_service.redis is None:
        await cache_service.init_redis()
    async with session_factory() as session:
        mgr = CRDTPersistenceManager(cache_service.redis, session)
        ydoc = await mgr.restore(galaxy_id)
        restored_keys = set(ydoc.get_map("galaxy").keys())
    storm["crdt_restore_after_storm"] = {
        "expected_devices": clients,
        "restored_devices": len([k for k in restored_keys if str(k).startswith("device_")]),
        "merged_state_readable": all(f"device_{i}" in restored_keys for i in range(clients)),
    }

    # --- c) 混合数据面风暴（多端同时: 取图 + 节点统计 + 词法搜索）---
    async with session_factory() as session:
        some_node = (await db.execute(select(KnowledgeNode.id).limit(1))).scalars().one()

    async def mixed(i: int):
        kind = i % 3
        async with session_factory() as session:
            t0 = time.perf_counter()
            if kind == 0:
                await GalaxyService(session).get_galaxy_graph(user_id=user_uuid)
            elif kind == 1:
                await GalaxyService(session).get_node_knowledge_stats(user_uuid, some_node)
            else:
                await GalaxyService(session).retrieval.keyword_search(user_uuid, "TCP", limit=10)
            return (time.perf_counter() - t0) * 1000.0

    mixed_results = await asyncio.gather(*[mixed(i) for i in range(clients * 2)], return_exceptions=True)
    mixed_lat = [r for r in mixed_results if not isinstance(r, BaseException)]
    storm["mixed_data_plane"] = _stats(mixed_lat)
    storm["mixed_data_plane"]["errors"] = sum(1 for r in mixed_results if isinstance(r, BaseException))
    return storm


async def cleanup(db, scales: list[int]) -> int:
    """删除本脚本生成的全部行（一次性库全量清; 返回删除节点数）。"""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func as sa_func
    from sqlalchemy import select

    from app.models.galaxy import (
        CollaborativeGalaxy,
        CRDTOperationLog,
        CRDTSnapshot,
        KnowledgeNode,
        NodeRelation,
        UserNodeStatus,
    )
    from app.models.user import User

    total = (await db.execute(select(sa_func.count()).select_from(KnowledgeNode))).scalar_one()
    await db.execute(sa_delete(UserNodeStatus))
    await db.execute(sa_delete(NodeRelation))
    await db.execute(sa_delete(KnowledgeNode))

    # 先清风暴 galaxy（created_by 引用用户），再清用户
    galaxy_id = uuid5(NAMESPACE_URL, f"wt395-g05-crdt-{SEED}")
    await db.execute(sa_delete(CRDTOperationLog).where(CRDTOperationLog.galaxy_id == galaxy_id))
    await db.execute(sa_delete(CRDTSnapshot).where(CRDTSnapshot.galaxy_id == galaxy_id))
    await db.execute(sa_delete(CollaborativeGalaxy).where(CollaborativeGalaxy.id == galaxy_id))
    await db.commit()

    for scale in scales:
        await db.execute(sa_delete(User).where(User.username == _scale_username(scale)))
    await db.commit()
    return total


def build_summary(raw: dict) -> str:
    """汇总: 全部数字从 raw 计算得出（含阈值判定）。"""
    lines: list[str] = []
    lines.append("# G-05 Galaxy 规模梯度性能汇总（wt395）")
    lines.append("")
    lines.append(f"- generated_at: {raw['generated_at']}")
    lines.append(f"- seed: {raw['seed']} ｜ samples/操作: {raw['args']['samples']}（p50/p95 口径 ≥30）")
    lines.append(f"- 数据: 真实 ORM 行 + 真实 DashScope embedding（skip={raw['args']['skip_embeddings']}）")
    lines.append("- 基线口径: 本机 Apple Silicon 容器栈（PG16+Redis 本地）headless 服务级时延; 非真机 FPS")
    lines.append("")
    lines.append("## 规模梯度（ms）")
    lines.append("")
    lines.append("| scale | 操作 | n | p50 | p95 | max | 备注 |")
    lines.append("|---|---|---|---|---|---|---|")
    checks: list[tuple[str, bool, str]] = []
    for scale, block in raw["scales"].items():
        meta = block["meta"]
        for op, s in block["operations"].items():
            note = ""
            if op == "graph_cold":
                note = f"nodes={s.get('nodes_returned')} errors={s.get('errors')}"
            elif op == "graph_lod_zoom03":
                note = f"lod_nodes={s.get('nodes_returned')}/{s.get('full_graph_nodes')} " f"shrunk={s.get('shrunk')}"
            elif op == "graph_viewport_window":
                note = f"capped800={s.get('capped_at_800')} nodes={s.get('nodes_returned')}"
            elif op == "semantic_search":
                note = f"avg_hits={s.get('avg_hits')} errors={s.get('errors')}"
            elif op == "learning_path_far":
                note = f"path_found={s.get('path_found')} errors={s.get('errors')}"
            elif op == "node_detail_grpc":
                note = f"errors={s.get('errors')}"
            lines.append(f"| {scale} | {op} | {s['n']} | {s['p50_ms']} | {s['p95_ms']} | {s['max_ms']} | {note} |")
        gc = block["operations"]["graph_cold"]
        limit = (
            THRESHOLDS["graph_cold_p95_ms_large"] if meta["nodes"] >= 1000 else THRESHOLDS["graph_cold_p95_ms_small"]
        )
        checks.append((f"冷缓存图取数 p95≤{limit}ms @{scale}", gc["p95_ms"] <= limit, f"p95={gc['p95_ms']}ms"))
        checks.append(
            (f"冷缓存零错误且全图一致 @{scale}", bool(gc.get("node_counts_consistent")), f"errors={gc.get('errors')}")
        )
        gw = block["operations"]["graph_warm"]
        checks.append(
            (
                f"热缓存图取数 p95≤{THRESHOLDS['graph_warm_p95_ms']}ms @{scale}",
                gw["p95_ms"] <= THRESHOLDS["graph_warm_p95_ms"],
                f"p95={gw['p95_ms']}ms",
            )
        )
        lod = block["operations"]["graph_lod_zoom03"]
        if meta["nodes"] >= THRESHOLDS["lod_must_shrink_at_scale"]:
            checks.append(
                (
                    f"LOD zoom<0.5 收窄 @{scale}",
                    bool(lod.get("shrunk")),
                    f"lod={lod.get('nodes_returned')}<full={lod.get('full_graph_nodes')}",
                )
            )
        vp = block["operations"]["graph_viewport_window"]
        checks.append(
            (f"viewport≤800 上限 @{scale}", bool(vp.get("capped_at_800")), f"nodes={vp.get('nodes_returned')}")
        )
        lp = block["operations"]["learning_path_far"]
        lpn = block["operations"]["learning_path_near"]
        # 离群点标注（如实区分环境级停顿与算法性超时）: >1s 的样本计数,
        # 与 near 档同签名（两者算法同体, 尖刺同时出现 → 环境级而非路径算法）
        def _outliers(op: dict) -> int:
            return sum(1 for x in op.get("samples_ms", []) if x > 1000)

        outlier_note = (
            f"离群(>1s) far={_outliers(lp)}/{lp['n']} near={_outliers(lpn)}/{lpn['n']}"
            if lp.get("samples_ms")
            else "无逐样本（旧版 raw）"
        )
        checks.append(
            (
                f"学习路径 p95≤{THRESHOLDS['learning_path_p95_ms']}ms @{scale}",
                lp["p95_ms"] <= THRESHOLDS["learning_path_p95_ms"],
                f"p95={lp['p95_ms']}ms p50={lp['p50_ms']}ms; {outlier_note}",
            )
        )
        nd = block["operations"]["node_detail_grpc"]
        checks.append((f"节点详情零错误 @{scale}", nd.get("errors") == 0, f"errors={nd.get('errors')}"))
        sem = block["operations"].get("semantic_search")
        if sem:
            checks.append(
                (
                    f"语义搜索(真实embedding) p95≤{THRESHOLDS['search_p95_ms']}ms @{scale}",
                    sem["p95_ms"] <= THRESHOLDS["search_p95_ms"],
                    f"p95={sem['p95_ms']}ms",
                )
            )
            corr = block["correctness"]["semantic"]
            rate = corr["top1_hit_rate"]
            if corr.get("full_corpus"):
                checks.append(
                    (
                        f"语义 top1 命中率≥{THRESHOLDS['semantic_top1_hit_rate_min']} @{scale}",
                        rate >= THRESHOLDS["semantic_top1_hit_rate_min"],
                        f"hit_rate={rate} off_domain_zero={corr['off_domain_zero_hit_rate']}",
                    )
                )
            else:
                lines.append("")
                lines.append(f"（注: @{scale} 非全簇语料档, top1 命中率 {rate} 只记录不判定）")
    lines.append("")
    lines.append("## 恢复风暴")
    lines.append("")
    st = raw["storm"]
    rc = st["reconnect_cold_storm"]
    lines.append(
        f"- 冷缓存重连风暴: clients={st['clients']} rounds={st['rounds']} ｜ {rc['n']} 采样 "
        f"p50={rc['p50_ms']} p95={rc['p95_ms']} max={rc['max_ms']} errors={rc['errors']} ｜ "
        f"节点数一致={rc['node_counts_consistent_across_clients']}"
    )
    lines.append(
        f"- 尾部有界(最慢客户端 ≤ 冷缓存首拉 SLA {rc['tail_abs_budget_ms']}ms): "
        f"max={rc['max_ms']}ms → {rc['tail_bounded']} ｜ "
        f"观测: max/单发冷中位={rc.get('max_vs_single_cold_median')}× ｜ 风暴后热取 {st['post_storm_warm_ms']}ms"
    )
    cr = st["crdt_multi_device_sync"]
    rs = st["crdt_restore_after_storm"]
    lines.append(
        f"- 多端 CRDT 并发同步: {cr['n']} 次 p50={cr['p50_ms']} p95={cr['p95_ms']} errors={cr['errors']} ｜ "
        f"风暴后 restore 合并态 {rs['restored_devices']}/{rs['expected_devices']} 台设备可读={rs['merged_state_readable']}"
    )
    mx = st["mixed_data_plane"]
    lines.append(
        f"- 混合数据面风暴(2×clients): p50={mx['p50_ms']} p95={mx['p95_ms']} max={mx['max_ms']} errors={mx['errors']}"
    )
    checks.append(
        (
            "重连风暴零错误且数据一致",
            rc["errors"] == 0 and rc["node_counts_consistent_across_clients"],
            f"errors={rc['errors']}",
        )
    )
    checks.append(("重连风暴尾部有界", bool(rc["tail_bounded"]), f"max={rc['max_ms']}ms"))
    checks.append(
        (
            "CRDT 风暴零错误且合并态可读",
            cr["errors"] == 0 and rs["merged_state_readable"],
            f"restored={rs['restored_devices']}/{rs['expected_devices']}",
        )
    )
    checks.append(("混合风暴零错误", mx["errors"] == 0, f"errors={mx['errors']}"))
    lines.append("")
    lines.append("## graceful 降级断言")
    lines.append("")
    for k, v in raw["graceful"].items():
        lines.append(f"- {k}: {v}")
        if isinstance(v, bool):
            checks.append((f"graceful: {k}", v, str(v)))
    lines.append("")
    lines.append("## 阈值判定（声明依据见 THRESHOLDS 与 raw_scale_perf.json）")
    lines.append("")
    failed = 0
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        lines.append(f"- [{mark}] {name} — {detail}")
    lines.append("")
    lines.append(f"总计 {len(checks)} 项判定, FAIL={failed}")
    return "\n".join(lines) + "\n"


async def async_main(args: argparse.Namespace) -> int:
    from loguru import logger

    logger.remove()  # 探针进程: 屏蔽应用日志噪声, 错误经异常/采集结果呈现

    from app.db.session import AsyncSessionLocal, engine

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    raw: dict = {
        "card": "G-05",
        "worker": "wt395",
        "generated_at": started.isoformat(),
        "seed": SEED,
        "args": {
            "scales": args.scales,
            "samples": args.samples,
            "storm_clients": args.storm_clients,
            "storm_rounds": args.storm_rounds,
            "skip_embeddings": args.skip_embeddings,
        },
        "thresholds": THRESHOLDS,
        "scales": {},
        "graceful": {},
        "storm": {},
    }
    exit_code = 0
    async with AsyncSessionLocal() as db:
        try:
            for scale in args.scales:
                print(f"=== scale {scale} (samples={args.samples}) ===", flush=True)
                raw["scales"][str(scale)] = await measure_scale(
                    db, AsyncSessionLocal, scale, args.samples, with_embeddings=not args.skip_embeddings
                )
            storm_scale = max(args.scales)
            print(
                f"=== recovery storm @ {storm_scale} (clients={args.storm_clients} rounds={args.storm_rounds}) ===",
                flush=True,
            )
            raw["storm"] = await recovery_storm(
                db, AsyncSessionLocal, storm_scale, args.storm_clients, args.storm_rounds
            )
            print("=== graceful degradation probe ===", flush=True)
            raw["graceful"] = await graceful_degradation_probe(db, AsyncSessionLocal, max(args.scales))

            raw_path = out_dir / "raw_scale_perf.json"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2))
            print(f"[raw] -> {raw_path}", flush=True)

            summary_path = out_dir / "summary_scale_perf.md"
            summary_path.write_text(build_summary(raw))
            print(f"[summary] -> {summary_path}", flush=True)
        finally:
            if not args.keep_data:
                removed = await cleanup(db, args.scales)
                print(f"[cleanup] removed {removed} generated nodes (keep-data=False)", flush=True)
            else:
                print("[cleanup] skipped (--keep-data)", flush=True)
    await engine.dispose()
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scales", default="50,500,5000", help="逗号分隔规模梯度（默认 50,500,5000）")
    parser.add_argument("--samples", type=int, default=30, help="每操作采样数（默认 30, p50/p95 口径下限）")
    parser.add_argument("--storm-clients", type=int, default=16, help="恢复风暴并发客户端数（默认 16）")
    parser.add_argument("--storm-rounds", type=int, default=5, help="冷缓存风暴轮数（默认 5）")
    parser.add_argument(
        "--out", default=str(BACKEND.parent / "v3-output" / "WT395-G05-GALAXY"), help="raw/summary 输出目录"
    )
    parser.add_argument(
        "--skip-embeddings", action="store_true", help="跳过真实 embedding 生成（仅结构梯度观测, 语义面将不可用）"
    )
    parser.add_argument("--keep-data", action="store_true", help="保留生成数据（默认跑完清理）")
    parser.add_argument(
        "--allow-wipe",
        action="store_true",
        help="确认目标库是一次性性能库（数据生成/清理会全量清 knowledge_nodes 等表; 缺省则拒跑）",
    )
    args = parser.parse_args()
    args.scales = [int(s) for s in str(args.scales).split(",") if s.strip()]
    if args.samples < 30:
        print("[warn] samples<30 不满足 p50/p95 口径下限, 抬升到 30")
        args.samples = 30
    if not args.allow_wipe:
        print(
            "[abort] 本脚本对 knowledge_nodes/node_relations/user_node_status 做全量清场与清理,\n"
            "        只允许指向一次性性能库。请显式传 --allow-wipe 确认（例如独立库 wt395_g05）。"
        )
        sys.exit(2)
    # 生产同款加载口径: grpc_server.py 启动时把各 gen/<svc>/v1 追加进 sys.path,
    # 使 *_pb2_grpc.py 里的裸 `import <svc>_service_pb2` 可解析。
    for gen_dir in ("galaxy",):
        p = BACKEND / "app" / "gen" / gen_dir / "v1"
        if p.is_dir() and str(p) not in sys.path:
            sys.path.append(str(p))
    sys.exit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
