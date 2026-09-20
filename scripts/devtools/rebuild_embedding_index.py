#!/usr/bin/env python3
"""E-05: embedding 索引重建 / 版本迁移 / 回滚脚本。

职责（配合 Alembic e05_20260919_embedding_version_columns）：
1. 扫描 document_chunks / knowledge_nodes 中"向量缺失或版本不匹配"的行；
2. 用指定的 embedding provider 重嵌（批量），并写入
   embedding_model / embedding_dim 版本标记；
3. 对 document_chunks 所属文件重建 Redis 版本化 RAG key
   （sparkle:doc_chunk:{ver}:{file}:{idx}），旧版本 key 全量删除；
4. 确保 Redis 版本化索引（idx:knowledge@{ver}）存在；
5. 可选清理非当前版本资产（--prune-legacy）。

用法（backend/ 目录下）：
    # 干跑（默认）：只报告将重嵌的行数，不调 API 不写库
    python ../scripts/devtools/rebuild_embedding_index.py --table both

    # 真实执行（调 embedding API，注意配额）
    python ../scripts/devtools/rebuild_embedding_index.py --table both --execute

    # 只补 NULL/缺失向量的行（存量打标后最小成本迁移）
    python ../scripts/devtools/rebuild_embedding_index.py --table document_chunks --only-missing --execute

换模型 runbook（E-05 D5，R2 返修补充——必读）：
    换 embedding 模型**禁止直接改 .env 切流量**。版本隔离是硬过滤：切配置的
    瞬间，旧版本行被 `_embedding_version_filter` 无条件排除，且新版本的
    版本化 Redis 索引（KNN+BM25 同一索引）还是空的 → galaxy Redis hybrid
    双路皆空 → 全量落 pgvector fallback（同样按版本排除旧行）→ 最终词法。
    症状是**静默召回塌缩**（无任何报错与"因版本排除"信号）。

    正确顺序 = **先 rebuild 后切流量**：
    1. 线上仍按旧配置服务，先用覆盖参数把存量行重嵌到**新**版本：
         python ../scripts/devtools/rebuild_embedding_index.py --table both --execute \\
             --model <新模型名>          # 需要时配合 --provider / --dim
       （脚本会把行重嵌+打标到新版本、重建新命名空间 Redis key、确保新版本
       索引 idx:knowledge@{新ver} 存在；全部基于覆盖后的目标版本计算）
    2. 确认 summary 行数与 FT.INFO num_docs 符合预期；
    3. 改 .env 切流量 → 新版本命名空间即刻全量可用（切换动作本身零等待）；
    4. 观察稳定后可考虑 --prune-legacy（注意：它删除**所有**非当前版本 key，
       包括旧版本回滚资产——执行前确认不再需要回滚到旧模型）。

    诚实的窗口语义：rebuild 期间被重嵌的行会逐步离开旧版本命名空间，
    旧版本召回随重嵌进度**单调下降**（切换瞬间恢复 100%）；若选"先切流量
    后 rebuild"则相反——切换瞬间向量召回塌缩到 ~0 再逐步恢复。两者都存在
    迁移窗口，真正零塌缩需要过渡期双读（新旧命名空间 rank-list RRF 融合，
    记 follow-up）。中途放弃 rebuild 的恢复方式：重跑脚本（方向参数指回旧
    版本）即可把行重嵌回去。
    注意：换**维度**（≠1024）不是 rebuild 能解决的——DB 列是 Vector(1024)，
    需要列迁移，错维会在写入时响亮报错。

回滚路径（embedding 模型切换后想切回旧模型）：
    1. 把 .env 的 EMBEDDING_PROVIDER/EMBEDDING_MODEL/EMBEDDING_DIM 改回旧值；
    2. 重新运行本脚本 --execute（把不匹配行重嵌回旧模型）；
    3. Redis 旧版本索引与其 key 在切换期间从未删除（版本化命名空间隔离），
       切回旧配置后立即可用，无需重建；
    4. 语义缓存按 embedding_version 自动失效，无需手动清理。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 允许从仓库根直接运行：把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", choices=["document_chunks", "knowledge_nodes", "both"], default="both")
    parser.add_argument("--batch-size", type=int, default=10, help="embedding 批大小（dashscope <=10）")
    parser.add_argument("--only-missing", action="store_true", help="只处理 embedding 为 NULL 或未打标的行")
    parser.add_argument("--execute", action="store_true", help="真实执行（默认 dry-run）")
    parser.add_argument(
        "--prune-legacy",
        action="store_true",
        help="清理非当前版本资产：所有非当前版本 Redis key 与旧索引 idx:knowledge"
        "（含旧版本回滚资产，不可逆，需 --execute；执行前确认不再回滚）",
    )
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少行（0=不限制；排障用）")
    parser.add_argument(
        "--provider",
        choices=["dashscope", "siliconflow"],
        default=None,
        help="目标供应商覆盖（迁移窗口用：先 rebuild 后切流量，见模块 docstring）",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="目标 embedding 模型名覆盖（按目标供应商写入其专属模型配置）",
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=None,
        help="目标维度覆盖（警告：DB 列为 Vector(1024)，换维需要列迁移而非 rebuild）",
    )
    args = parser.parse_args()

    from sqlalchemy import select

    from app.core.redis_search_client import redis_search_client
    from app.db.session import AsyncSessionLocal
    from app.models.document_chunks import DocumentChunk
    from app.models.file_storage import SourceLifecycleStatus, StoredFile
    from app.models.galaxy import KnowledgeNode
    from app.services.embedding_service import embedding_service
    from app.services.rag_indexing_service import (
        DOCUMENT_CHUNK_PREFIX,
        GROUP_DOCUMENT_CHUNK_PREFIX,
        KNOWLEDGE_CHUNK_PREFIX,
        delete_document_chunk_keys,
        get_rag_redis,
        index_document_chunks,
        rag_index_name,
    )

    target_version = embedding_service.current_embedding_version()
    target_dim = embedding_service.embedding_dim

    # E-05 D5（R2）：迁移窗口覆盖——允许把存量重嵌到"尚未切换流量"的新版本
    # （先 rebuild 后切流量），线上进程不受影响（它们按自己的配置组命名空间）。
    if args.provider or args.model or args.dim:
        if args.provider:
            embedding_service.primary_provider = args.provider
        if args.model:
            if embedding_service.primary_provider == "siliconflow":
                embedding_service.siliconflow_model = args.model
            else:
                embedding_service.dashscope_model = args.model
        if args.dim:
            embedding_service.embedding_dim = args.dim
        target_version = embedding_service.current_embedding_version()
        target_dim = embedding_service.embedding_dim
        if target_dim != 1024:
            print(
                f"[E-05 rebuild] WARNING: target dim {target_dim} != 1024 (DB column type) — "
                "dimension change requires a column migration, rebuild alone will fail loudly on write"
            )

    print(f"[E-05 rebuild] target embedding version = {target_version}")
    print(f"[E-05 rebuild] redis versioned index     = {rag_index_name()}")
    if not embedding_service.is_configured():
        # FIX-16 ③（N3）：dry-run 不调 embedding API，无 key 不应 fail-close——
        # 否则无 key 环境无法盘点 stale/untagged 行（漂移监控依赖 dry-run）。
        # --execute 仍 fail-closed：真实重嵌绝不静默进行。
        if args.execute:
            print(
                "[E-05 rebuild] FATAL: no embedding provider key configured "
                "(DASHSCOPE_API_KEY / SILICONFLOW_API_KEY). Fail-closed: --execute refused."
            )
            return 2
        print(
            "[E-05 rebuild] WARNING: no embedding provider key configured "
            "(DASHSCOPE_API_KEY / SILICONFLOW_API_KEY); dry-run inventory only "
            "(--execute would be refused)."
        )

    async with AsyncSessionLocal() as session:
        tables = []
        if args.table in ("document_chunks", "both"):
            tables.append(("document_chunks", DocumentChunk))
        if args.table in ("knowledge_nodes", "both"):
            tables.append(("knowledge_nodes", KnowledgeNode))

        total_reembedded = 0
        files_touched: set[str] = set()

        for table_name, model in tables:
            if args.only_missing:
                stale_cond = (model.embedding.is_(None)) | (model.embedding_model.is_(None))
            else:
                stale_cond = (
                    (model.embedding.is_(None))
                    | (model.embedding_model.is_(None))
                    | (model.embedding_model != target_version)
                    | (model.embedding_dim != target_dim)
                )
            rows = (await session.execute(select(model).where(stale_cond).order_by(model.created_at))).scalars().all()
            if args.limit:
                rows = rows[: args.limit]
            mode = "dry-run" if not args.execute else "EXECUTE"
            print(f"[E-05 rebuild] {table_name}: {len(rows)} stale row(s) [{mode}]")

            for start in range(0, len(rows), args.batch_size):
                batch = rows[start : start + args.batch_size]
                texts = [
                    (r.content if table_name == "document_chunks" else f"{r.name} {r.description or ''}") for r in batch
                ]
                if not args.execute:
                    for r, t in zip(batch, texts, strict=True):
                        print(f"  would re-embed {table_name}#{r.id} ({len(t)} chars)")
                    continue
                embeddings = await embedding_service.batch_embeddings(texts, text_type="document")
                for row, vector in zip(batch, embeddings, strict=True):
                    row.embedding = vector
                    row.embedding_model = target_version
                    row.embedding_dim = len(vector)
                    if table_name == "document_chunks":
                        files_touched.add(str(row.file_id))
                await session.commit()
                total_reembedded += len(batch)
                print(f"  re-embedded {start + len(batch)}/{len(rows)}")

        # Redis 重建：只对 document_chunks 触碰过的文件
        redis = await get_rag_redis()
        if args.execute and redis is not None and files_touched:
            for file_id in files_touched:
                file_record = await session.get(StoredFile, file_id)
                if file_record is None:
                    print(f"  skip redis reindex: stored file {file_id} gone")
                    continue
                # 删掉该文件所有版本（含 legacy）的旧 key，再按当前版本重建
                await delete_document_chunk_keys(redis, file_id)
                if (
                    file_record.lifecycle_status or SourceLifecycleStatus.ACTIVE.value
                ) != SourceLifecycleStatus.ACTIVE.value:
                    print(f"  file {file_id} inactive: redis keys deleted, no reindex")
                    continue
                chunks = (
                    (
                        await session.execute(
                            select(DocumentChunk)
                            .where(
                                DocumentChunk.file_id == file_id,
                                DocumentChunk.deleted_at.is_(None),
                            )
                            .order_by(DocumentChunk.chunk_index)
                        )
                    )
                    .scalars()
                    .all()
                )
                indexed = await index_document_chunks(redis, file_record, chunks, db=session)
                print(f"  redis reindexed file {file_id}: {indexed} chunk(s) at version {target_version}")

        # 确保版本化索引存在（R2：只在 --execute 时执行——ensure_index 会真实
        # 建索引，dry-run 不应有 Redis 副作用）
        if args.execute and redis is not None:
            ok = await redis_search_client.ensure_index()
            print(f"[E-05 rebuild] versioned index ensure: {'ok' if ok else 'FAILED'}")

        # 可选 legacy 清理
        if args.prune_legacy and args.execute and redis is not None:
            legacy_prefixes = [KNOWLEDGE_CHUNK_PREFIX, DOCUMENT_CHUNK_PREFIX, GROUP_DOCUMENT_CHUNK_PREFIX]
            version_token = embedding_service.current_version_token()
            deleted_keys = 0
            for prefix in legacy_prefixes:
                async for key in redis.scan_iter(match=f"{prefix}*"):
                    # 保留当前版本的 key；无版本后缀的旧格式全删
                    rest = key[len(prefix) :]
                    if not rest.startswith(f"{version_token}:"):
                        deleted_keys += await redis.delete(key)
            try:
                await redis.ft(redis_search_client.LEGACY_INDEX_NAME).dropindex(delete_documents=False)
                print("[E-05 rebuild] dropped legacy index idx:knowledge (documents kept)")
            except Exception as exc:
                print(f"[E-05 rebuild] legacy index drop skipped: {exc}")
            print(f"[E-05 rebuild] pruned {deleted_keys} legacy redis key(s)")

        # 汇总
        for table_name, model in tables:
            current = (
                await session.execute(
                    select(model.id).where(model.embedding_model == target_version, model.embedding.isnot(None))
                )
            ).all()
            untagged = (await session.execute(select(model.id).where(model.embedding_model.is_(None)))).all()
            print(
                f"[E-05 rebuild] summary {table_name}: "
                f"{len(current)} row(s) at target version, {len(untagged)} untagged row(s) remain"
            )

    print(
        "[E-05 rebuild] done. "
        f"re-embedded={total_reembedded}, "
        "rollback: revert EMBEDDING_* settings and re-run this script with --execute"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
