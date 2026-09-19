# E-05 Review Receipt — 第二路 Reviewer（DeepAudit）返修 delta 复核

> 原始收据（D1-D8 首轮发现）已归档主仓 staging：
> `/Users/brsama/code/GitHub/Sparkle-project/v3-output/E-05-staging/REVIEW_RECEIPT_2.md`（首检对象 wt5@57c87a8e，VERDICT CHANGES）。
> 本收据为 Worker 返修（REPORT §R2）后的 delta 复核，写于 wt5。

- reviewer: DeepAudit #2（delta 轮） ｜ date: 2026-09-19 ｜ 对象: wt5 未提交 diff + `v3-output/E-05/`
- 方法：D1-D4 逐项实现核对（embedding_service / source_lifecycle / semantic_cache / rag_indexing / retrieval_service / rebuild 脚本全量精读）＋ 事务顺序推演 ＋ 独立探针 1 个（/tmp，mock 供应商，零网络零 DB 零 Redis 写，已清理）＋ 定向 pytest 串行单文件（真实 dev Redis）＋ rebuild dry-run ×3（只读 DB、FT._LIST 前后快照比对）
- 环境：临时 venv 在 /tmp（requirements 去 python-lzo，官方 PyPI 源，已删）；密钥仅经环境变量传入（**未创建任何 .env 副本**）；dev DB 只读（全程 SELECT + 脚本 ROLLBACK）；真实 embed 1 次（live green，Worker 预热缓存已过期，属 ≤2 预算内）
- 纪律：未改 Worker 代码、未跑 alembic、未写生产 key、未 commit/push

## 验证记录（本轮我亲跑）

```
tests/services/test_embedding_fail_closed.py              17 passed
tests/services/test_semantic_cache_version_isolation.py    5 passed（真 Redis，含 D2 真实缓存层 + D3 拒写）
tests/services/test_rag_indexing_service.py                8 passed（真 Redis + 可控 db 桩）
tests/services/test_embedding_live_green.py（E05_LIVE=1）   1 passed（真实 API 1 次批调用）
tests/services/galaxy/test_retrieval_service.py           15 passed（回归抽查，含 D3 新增 3 项）
探针：原 D1 PROVENANCE MISMATCH 场景重放 → EmbeddingProviderError（fail-closed），
      siliconflow 调用 0 次，错误信息含 version isolation 说明 —— PASS
rebuild dry-run（默认 + --model new-model-x）：目标版本/索引名/谓词正确联动；
      FT._LIST 三次快照完全一致（dry-run 无 Redis 副作用，R2 修复实证）
patch：29 条目与 git diff 一致（20 modified + 7 新源文件 + 2 输出物）；
      密钥扫描仅 3 处假 fixture（sk-invalid-key / sk-secret-value），无真实密钥
```

## D1 [P1] fail-closed 取舍 — **论证成立，实现一致，复核通过**

**取舍评估**：Worker 弃"按实际供应商打标"（A）选"异构 failover 拒绝"（B），四条理由逐一核过，均技术上成立：
1. **查询侧击穿是 A 的死穴**（成立且是决定性理由）：failover 窗口内查询 embedding 也来自备用模型，写侧打标再正确，查询仍拿备用向量比主索引——正是本卡要消灭的静默垃圾相似度；救它需要查询路由到备用命名空间，而那里只有 failover 窗口的少量行，召回塌缩使 failover 收益趋零。
2. 混合批次（缓存命中主模型旧向量 + 备用新嵌）无单一真实版本——逐条溯源要改 6+ 写点返回类型，属实。
3. truthful 打标 = 写入查询不可见命名空间（版本隔离本意），比显式降级更糟——属实。
4. rebuild/回滚单版本假设保留——属实，且与 D5 runbook 一致。
附加核verified：两供应商 text_type 语义不对称（dashscope 传 query/document，siliconflow 端点不收）审计已实证，"同款模型同空间"假设不成立。

**实现核对**：`provider_version(provider)` 供应商前缀化版本串；`batch_embeddings` 异构守卫在供应商循环首位（`provider_version != current_embedding_version()` → 跳过 + warning + 记入 skipped 清单）；最终 `EmbeddingProviderError` 携带 heterogeneity_note（含被跳过供应商与其 resolved_version、原因）；`provider_status()` 暴露 resolved_version 且不泄 key 内容；embedding 缓存键带 version token——备用向量污染缓存键的路径随"备用零调用"一并消失。守卫语义上等价于"恒只执行主供应商"（版本串含供应商名，唯一可匹配者是 primary 自身），同供应商重试保留（tenacity + 循环）。
**探针重放**：原 mismatch 场景现为显式报错拒写，断言零备用调用通过。

## D2 [P1] knowledge:version:v1 失效 — **四路径齐备，真实缓存层口径已修，复核通过**

- `invalidate_source_retrieval` 末尾 `DEL KNOWLEDGE_VERSION_CACHE_KEY`（常量单源 import，try/except+warning 不阻塞主流程）；函数内 DEL 之前**无任何 early return**；archive(L84)/revoke(L118)/orphan(L156)/delete(L181) 四路径全部经此函数。
- 常开单测走真实 Redis + 真实 `invalidate_source_retrieval`（仅桩外部依赖）：预热真实键 → 失效 → 断言键清除，且测试礼貌恢复/清理共享键。我亲跑通过。
- live 集成测试口径修正属实且正确：`_get_knowledge_version()`（真实缓存层）+ 预热后断言键确实在缓存中（使删除后断言有意义）+ 删除后断言键被 DEL、新版本即时可见、旧语义缓存条目不可命中。
- 写路径不失效的论证我接受：新内容 ≤30s 延迟可见是缓存 TTL 语义（非泄漏已删内容）；全局键每次写入失效会让语义缓存命中率塌缩。取舍合理。

**N1 残余观察（非阻断，建议并入 D4 follow-up）**：`invalidate_source_retrieval` 在四路径中均先于 `db.flush()`/commit 执行（delete() 甚至先失效后软删）。DEL→commit 窗口内若并发检索触发 `_get_knowledge_version` 重算，会以 READ COMMITTED 旧快照重播**删除前**版本并再缓存 30s——删除内容可在删除完成后继续可见 ≤30s。这与 §R2.4 已披露的 D4 残余（"失效与提交不同原子"）同类：Worker 对 D4 披露了毫秒级交错，对 D2 未明说；发生概率已从"每次删除必有 30s"压缩到"亚秒窗口内恰有并发重算"，自愈于 TTL。**D4 的"DB 提交后再失效 Redis"事务后钩子 follow-up 若落地，同时闭掉 D2 此残余**——建议在 follow-up 卡中把两处并列。

## D3 [P2] 降级结果拒写语义缓存 — **复核通过**

- `factory_meta`→`exec_meta` 通道：`get_with_lock` 三处 factory 调用点（无 redis / 未启用 / 锁内 / 锁超时 / mutex 异常）统一走 `_call_factory`，仅 factory_meta 非 None 时注入——未传通道的既有调用方零影响；全仓 `get_with_lock` 生产调用面仅 hybrid_search 一处（已核实 grep 唯一）。
- `_execute_hybrid_search` 两处 embedding 降级点（NotConfigured / 一般异常）均 `_mark_degraded`；pgvector fallback 与 rerank 失败不标记——语义正确（前者是全质量向量路径，后者返回的是 RRF 全质量融合序，均非 D3 所指的词法降级产物）。
- 拒写实现：结果照常返回 + `SEMANTIC_CACHE_BYPASS_TOTAL` + 显式日志；选"完全不缓存"而非短 TTL 的论证（降级连 exact 都不该服务）我接受。`get()` 全程 try/except 返回 None，供应商故障期读路径不会先于 factory 抛错——降级链路两层均成立。
- 测试真实性：真 Redis 上"降级不落缓存 + 对照组正常落缓存 + calls 序列断言"，非 mock 断言。我亲跑通过。

## D4 [P2] 写前新鲜复查 + 写后补偿 — **复核通过，残余披露如实**

- `source_is_active_fresh` 用列 SELECT（绕开 ORM 身份映射的陈旧实例态）判 `deleted_at IS NULL AND lifecycle=ACTIVE`；写前复查（内存态活→DB 复核，死则短路只清理）、写后复核（`indexed>0` 且复查死→清全部版本 key + 按 0 上报）。三个调用方（orchestrator ×2、source_lifecycle.restore、rebuild 脚本）全部接 db——已逐一核对。
- 测试用真 Redis + 按调用次序可控的 db 桩断言 `db.queries` 次数与 key 存在性，断言真实。
- 毫秒级残余交错（删除事务在校验后提交）披露如实，且方向正确（原窗口=整个 Celery 处理时长分钟级 → 现亚秒）。
- **N2 小瑕疵（非阻断）**：`test_source_is_active_fresh_interpretation` docstring 称覆盖"行不存在"，但 `_FakeDB` 空表时兜底返回 `("active", None)`，实际未走到代码的 `row is None → False` 分支（代码本身处理正确）。补一行 `_FakeResult(None)` 用例即可。

## D5 / 脚本 — **复核通过**

runbook 已写进脚本 docstring（执行者第一眼）；`--model` 覆盖联动实证（target version / 索引名 / 谓词一致变化）；dry-run 无 Redis/DB 副作用实证（FT._LIST 三次快照一致，R1 误建索引问题已修且已清理）；`--prune-legacy` 帮助文本已如实。

**N3 观察（非阻断）**：dry-run 也 fail-close 于无 key（"no embedding provider key configured"）——dry-run 不调 API，此检查偏严但与本卡哲学一致，运维知道即可。另：dev 库 untagged 行已从 R1 的 157 涨到 168（其它 worktree 以 HEAD 代码在共享 dev 库写入），live rebuild 规模会大于 R1 数字，lenient NULL 过渡过滤是 load-bearing——**live 窗口全量 rebuild 完成前不要置 `EMBEDDING_STRICT_VERSION_FILTER=true`**（与 REPORT §9.1 建议一致）。

## live 缺口裁定 — **接受"合入后由 Leader 在 live 窗口补验"**

理由：① D1/D2/D3 的语义全部由我亲跑的真实 Redis 单测钉死（D2 更是真实 `invalidate_source_retrieval` 函数级验证）；live 集成测试补的是端到端确认（真实 PG 删除事务流 + 真实 embedding 三路隔离），无新语义；② 唯有 live 能新增覆盖的点是删除事务与失效的**端到端时序**（N1 残余恰在此类）——而它已被识别且属 follow-up 级；③ Worker 披露诚实、口径已按生产语义修正。**条件**：live 窗口须跑 `test_document_retrieval_isolation.py` 全量 + `rebuild --execute` 全量（168+25 行）+ rebuild 后再评估 strict filter 翻转，并把 N1（D2 残余）并入 D4 事务后钩子 follow-up。

## 结论

D1-D4 四项返修实现与论证一致、测试断言真实且只增强未弱化、探针重放通过、patch 干净。三条非阻断观察（N1 事务顺序残余 / N2 测试口径小瑕疵 / N3 脚本偏严+dev 库漂移）建议随 follow-up 处理。首轮 CHANGES 的两条 P1 均已闭环。

VERDICT: ACCEPT
