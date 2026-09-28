# V4-D06 diff_or_evidence_only

**性质判定：implementation（产品代码最小增量，非重写）。**

## 一句话设计

关系型主真源优先：`GraphIndexWatermark` 以「关系型水位（max(updated_at)+双表计数）vs AGE 覆盖水位（写路径入队携带、worker 零积压后推进）」判定图索引时效——fresh 才允许 AGE 一跳作答（外加双读栅栏+存在性/软删守卫），stale/uncovered/unknown/AGE 故障一律**显式降级**关系型一跳查询（软删安全），降级原因/水位/失败原文进 `metadata["graph_index"]` 与 `GRAPH_INDEX_FALLBACK_TOTAL` 指标，同题双源可经 `recompute_graph_sources` 复算。不造第二世界模型，不做 DB 迁移。

## 现状缺口（盘点，main=f9729cc5，2026-09-28）

1. `stream:graph_sync` 仅 `node_created`/`relation_created`/`user_status_updated` 三类消息——关系型 UPDATE/DELETE（galaxy_service 草稿评审硬删 `_delete_draft_node`、BaseModel 软删 `deleted_at`）从不进 AGE，且无任何 watermark 记录 AGE 落后程度。
2. `GraphRAGRetriever.graph_search` 直查 AGE，逐实体异常吞成 warning——降级零元数据零指标（静默空结果）。
3. DATA_AND_GRAPH.md §星图权威为直接设计真源（"AGE 只能作可检查版本/覆盖率的派生检索索引，落后时回到关系查询"）。

## 产品代码 diff（8 文件，全部在 graph-retrieval 锁范围内）

| 文件 | 变更 |
|---|---|
| `backend/app/services/graph_index_watermark.py` | **新增**：`GraphIndexWatermark`（关系型水位/AGE 覆盖水位/resolve_state/record_age_coverage）、`relational_one_hop`（关系型一跳作答，软删安全）、`recompute_graph_sources`（同题双源复算，失败原文保留）、`GraphIndexState` |
| `backend/app/orchestration/graph_rag.py` | `graph_search` 接时效门（fresh→AGE+守卫+双读栅栏；否则显式关系型 fallback）；AGE 逐实体失败不再静默（结构化收集+关系型补答）；`metadata["graph_index"]` 快照；`fuse_results` 接受 `graph_relational` 来源标签 |
| `backend/app/workers/graph_sync_worker.py` | 消息可选携带 `watermark`；批次成功且 XPENDING==0 才推进 AGE 覆盖水位（保守不越权声称覆盖未处理消息；积压/失败/无 Redis 一律不推进） |
| `backend/app/services/graph_knowledge_service.py` | `create_knowledge_node`/`create_node_relation` 入队携带本事务关系型水位；`sync_all_to_age` 全量重建后推进覆盖水位 |
| `backend/app/config/settings.py` | 新增 `GRAPH_INDEX_WATERMARK_GATE_ENABLED: bool = True`（False=回滚开关，恢复旧 AGE-always 路径） |
| `backend/app/core/metrics.py` | 新增 `GRAPH_INDEX_FALLBACK_TOTAL`（reason: watermark_mismatch/index_uncovered/resolution_failed/concurrent_write_detected/staleness_guard_error/age_entity_error/relational_query_error） |
| `backend/tests/test_graph_rag.py` | `test_graph_search` 旧行为面（AGE 直查）显式归回滚开关路径（关门），断言不削弱、语义保留并加 last_graph_index 断言 |
| `backend/tests/unit/test_graph_index_freshness_fallback.py` | **新增** 19 用例（每验收面一正一反，见 test_results.json） |

无 proto/迁移/生成文件改动；`backend/app/gen` 为 gitignored 实体复制，不入库。

## 验收对照（卡面原文 → 实现/证据）

1. **新资料立即有明确版本/索引中状态** → 关系型写即翻水位（计数进版，E-05 delete-isolation 判例）；未覆盖/落后时关系型立即作答并携带 `graph_index.{state, relational_watermark, fallback_reason}`。正例 `test_new_relation_answered_immediately_with_index_status`（AGE 零调用、版本串可见）；反例 M1 突变（绕过 stale 判定）被 2 用例抓住。
2. **AGE 旧数据不能压过更新/删除的关系型事实** → 水位不等即 AGE 不作答；fresh 面仍有存在性/软删守卫（删除不复活）+ 双读栅栏（并发写检出）。正例 `test_stale_age_rows_cannot_override_relational_delete`、`test_soft_deleted_node_dropped_by_fresh_guard`；反例 M2 突变（守卫旁路）被抓住。
3. **对同题关系型/AGE 来源可复算，失败保留** → `recompute_graph_sources` 双源并列、同型一跳语义（无向/strength 下限/LIMIT 对齐），任一侧失败原文保留（`age_error`/`relational_error`，match=None）。正例 `test_recompute_graph_sources_match`；反例 `test_recompute_graph_sources_keeps_age_failure`、`test_recompute_graph_sources_keeps_relational_failure`。

## 与既有决策的一致性

- DATA_AND_GRAPH §星图权威：关系型当前真源优先、AGE 只作派生检索索引——本卡即该句的实现面。
- D03 epoch 栅栏同型：双读栅栏（读前/读后水位比对）复用「世代比对判陈旧」思想，不引入新机制名目。
- D04 通道/撤回语义零接触（其验收面 galaxy 178 全绿回归）。
- 回滚：`GRAPH_INDEX_WATERMARK_GATE_ENABLED=False` 一键恢复旧路径；旧消息格式（无 watermark 字段）不推进覆盖，向后兼容。

## V3 资产

V3 已 DONE 任务 ID 与证据零触碰；`GraphKnowledgeService`（orphan-by-design 资产）仅在其既有双写路径上增量加水印，不重建其消费面。
