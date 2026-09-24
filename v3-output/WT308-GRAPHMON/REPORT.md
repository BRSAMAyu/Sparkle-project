# WT308 — graph-monitor 健康探针真缺陷修复报告

- 分支：`wt308-graph-monitor-probes`
- base SHA：`61cea7652f080716b70988387018fca3e38fb269`（main HEAD）
- final SHA：`0bd67b0e26cffa19804f16c20b585a9041de5c4d`
- 交付物：`v3-output/WT308-GRAPHMON/changes.patch`（35,025 bytes，3 文件，+544/−88）

## 一、缺陷与全面盘点

`backend/app/api/v1/graph_monitor.py` 全部 `graph_ks.` 调用点核对（对 `backend/app/services/graph_knowledge_service.py` 的 `def` 清单）：

| 调用点 | 端点 | 修复前状态 |
| --- | --- | --- |
| `check_graph_connection()` :113 / :500 | graph_rag_health、detailed_health_check | **不存在** → AttributeError→500 |
| `check_vector_connection()` :134 / :523 | graph_rag_health、detailed_health_check | **不存在** |
| `get_graph_statistics()` :156 / :550 | graph_rag_health、detailed_health_check | **不存在** |
| `get_detailed_statistics()` :251 | graph_statistics | **不存在**（任务预言的第 4 个） |
| `graph_rag_search()` :198 / :412 / :635 | 三处 | 已存在（:194），未动 |

即 4 缺失 / 5 方法。三个消费端点（`/monitor/graph/health`、`/health/detailed`、`/statistics`）在修复前被调用必然 500；`/query/test` 依赖的 `graph_rag_search` 幸存。旁证：`tests/test_graph_rag.py` 的 `test_check_graph_connection` 是断言体全被注释掉的占位（方法从未存在过）。

## 二、实现说明（真探针，非桩）

全部落在 `GraphKnowledgeService`，沿用既有类型注解 / logger / 服务层模式：

1. **`check_graph_connection() -> bool`**：AGE `RETURN 1 AS result` 轻量 Cypher 真往返（走 `AgeClient.execute_cypher`，含连接池懒初始化），`asyncio.wait_for` 5s 超时（类常量 `GRAPH_PROBE_TIMEOUT_SECONDS`）；任何异常/超时归一化 `False`。
2. **`check_vector_connection() -> bool`**：pgvector 真查询——`select(count()).select_from(KnowledgeNode).where(embedding IS NOT NULL)`，向量列真实 SQL 往返；pgvector 扩展缺失/向量类型不可用时查询直接失败 → `False`；空表 count=0 仍算连通。
3. **`get_graph_statistics() -> dict`**：AGE 全图真实聚合计数，字段与端点消费契约一字不差（`total_nodes` / `total_relations` / `node_types` / `relation_types`，均为 int/int/dict/dict，端点逐 `.get` 读取）。类型分布（`labels(n)[0]` / `type(r)` 分组）经 `_graph_type_distribution` 执行，AGE 版本差异导致失败时降级空分布且总量照常返回；总量失败向上抛（端点已有 try/except 兜底分支，语义未弱化）。
4. **`get_detailed_statistics() -> dict`**：基于 3 + `graph_name` + Postgres 双写侧对照（`pg_total_nodes` / `pg_total_relations`，与 AGE 差值=同步滞后规模）+ Redis 同步积压 `sync_stream_length`（Redis 缺席/失败降级 0）。

端点侧 `status` / `health_score` / `alerts` / `recommendations` 分支逻辑**零改动**（graph_monitor.py 本次未改一行）；探针归一化 False 恰好喂给既有 disconnected 分支，使无图数据时端点返回结构化 degraded/unhealthy 报告而非异常。

## 三、测试证据

新增 `backend/tests/test_graph_monitor_probes.py`（18 例）：
- 探针分支：成功/异常归一化/超时（0.05s 短超时真实触发 `wait_for`）/空表仍连通/统计字段契约精确断言/空图零值/分布降级/总量失败传播/详细统计三源组合与降级；
- 组装层：直接调用 `detailed_health_check()`，锁全组件字典结构（graph_db/vector_db/redis 子字段）、`data_integrity` 四字段契约、`health_score`（score/rating/deductions，redis disabled→95 分锁扣分语义）、summary、degraded/unhealthy/统计失败三路径。

命令与数字（worktree 内，`SECRET_KEY=… DATABASE_URL="sqlite+aiosqlite:///:memory:"`，worktree 无 .env）：
- `pytest tests/test_graph_monitor_probes.py tests/test_graph_rag.py -q` → **57 passed**（test_graph_rag.py 含占位测试替换成的 2 个真断言用例；另以 `ruff --fix` 清掉该文件 3 个 main 上已存在的未用 import）
- `pytest tests/services/ -q` 回归 → **801 passed, 10 skipped**（6m22s）
- `mypy app --ignore-missing-imports`（口径同 `scripts/ci/mypy_ratchet.sh`）→ **1796 < 1803 棘轮**（未推高）
- `black --check --line-length 120` 三改动文件干净；`ruff check` 三改动文件干净
- `bash scripts/run_all_rule_guards.sh` → **exit 0，all rule guards passed (83 rules)**

## 四、风险

1. **分布聚合的 AGE 版本兼容**：`{type_name: labels(n)[0], type_count: count(*)}` 单列 map 分组聚合在极老 AGE 版本可能不支持——已用 try/except 降级为空分布（总量计数用最保守形态，不受影响），且该降级路径有单测。
2. **全图 count 为全扫描**：AGE 无免扫计数，节点量到 10 万级时 `get_graph_statistics` 耗时上升；探针本身有 5s 超时护栏，监控端点另有性能评级分支。
3. **`check_vector_connection` 的 sqlite 语义**：单测走 mock session；真实语义依赖 PG+pgvector（`Vector(1024)` 列），与生产部署形态一致。
4. **环境性踩坑记录**（非本缺陷引入）：worktree 从主仓拷贝 `app/gen` 时 `cp -R` 保留了 3 个指回主仓的 symlink，曾令 Rule K/Z 崩溃，已改 `cp -L` 解引用；worktree 缺 gitignored 的 `backend/gateway/gen`、`mobile/lib/gen` 曾令 Rule BG 红，已从主仓只读拷贝。最终全套守卫 83 绿。收工已清 /tmp 探针日志。
