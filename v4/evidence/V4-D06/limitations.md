# V4-D06 limitations

## 环境与验证边界

1. **AGE 实机未验证**：本机（wtD06 环境）无 Apache AGE 实例，所有 AGE 交互在测试中以 mock 契约面覆盖（与仓内既有 AGE 测试模式一致）。真实 AGE 往返（Cypher 方言差异、agtype 解析、连接池行为）需集成环境验证后方可声称生产可用。`AGE_ONE_HOP_CYPHER` 为 main 既有原句提取，非新写。
2. **worker 覆盖推进未在真实 Redis 流上端到端跑过**：XREADGROUP/XAUTOCLAIM/XPENDING 交互以 stub 验证（3 用例），生产多 worker 并发下的水位推进节奏需运维面观察 `sparkle_graph_index_fallback_total` 与 `graph:index:age_watermark` 印证。

## 设计取舍与挂账

3. **`find_learning_path` / `find_related_concepts` 未接时效门**：二者仍直查 AGE（`_filter_path_nodes_by_access` 租户过滤保留）。同属"AGE 旧数据"风险类，但消费方少、不在 graph_search 主检索链上——挂账待单独卡收口（审查挑战 R4）。
4. **写生产者空缺未被本卡补齐**：覆盖水位仅由 `GraphKnowledgeService` 双写路径与 `sync_all_to_age` 推进；`expansion_service` 等直写 `knowledge_nodes`/`node_relations` 的生产者不入队同步流（B02 盘点在案的既有缺口）。这些写入使水位长期 stale → 常态走关系型作答。这是 DATA_AND_GRAPH 设计意图（关系型主真源优先）的自然结果，但意味着 AGE 派生索引的收益要等写生产者补齐/全量重建后才兑现。
5. **水位是等值比较不是序比较**：同毫秒并发写靠双表计数翻转区分；未建库内单调序列（不造第二世代计数器，D03 epoch 权威不被复用挪用）。若审查判定需单调 epoch，属增量演进（挑战 R2）。
6. **双读栅栏窗口非零**：fresh 判定与 AGE 查询之间的并发写窗口缩到毫秒级但存在；窗口内新关系本轮缺答、下轮自愈。删除面不受此窗影响（守卫 + 水位不等双保险）。
7. **每 graph_search 读放大**：水位解析 2 条聚合 SQL（stale 面再 + 1 条一跳查询；fresh 面 + 守卫 1 条 + 读后水位 2 条）。未压测——AGE 主路径本就按实体逐次 Cypher 往返，量级相当，但高频聊天场景的 P99 影响未量化。
8. **`metadata["graph_index"]` 尚无前端消费方**：本卡只落检索元数据与指标面；galaxy/星图可视化展示"索引中"状态属消费卡。
9. **tenant 隔离 fail-open 面保留**：`graph_search` 无 user_id 调用时跳过租户过滤（warning）——main 既有契约（R5-P0-6 注释原文），本卡未收紧（收紧会影响 plan_tools 等既有调用方，超出本卡锁范围）。

## 测试口径

10. **sqlite 方言差异**：`relational_one_hop` 在 PG（生产）与 sqlite（CI）双方言可跑（纯 SQLAlchemy select），但 PG 下的查询计划/索引利用未 EXPLAIN 验证（`node_relations` 的 source/target 索引在迁移中已存在，读路径为 join 两主键）。
11. **本地缓存兜底语义**：单测以 `cache_service` 进程内本地缓存承载覆盖水位键（业务键允许兜底）；生产多进程下该键在 Redis（worker 写、检索读跨进程一致）。Redis 长期缺席的生产部署会恒 uncovered → 常态关系型作答（正确但无 AGE 收益）。

## 无 LLM / 无 UI / 无迁移

12. 本卡零模型调用、零 UI 变更、零 DB 迁移、零 proto 变更。回滚开关 `GRAPH_INDEX_WATERMARK_GATE_ENABLED=False` 有专门测试钉住旧路径语义。
