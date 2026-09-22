# COLDSTART 调查报告：新账号 galaxy 图面冷启动异常定性

- Worker：COLDSTART（wt141，基线 `37cac6e8`）
- 日期：2026-09-23（取证窗口：演示栈日志 2026-09-23 01:13–01:48 本地时间 = DB 2026-09-22 17:13–17:48 UTC）
- 性质：调查卡（默认零代码改动）；**例外产出 1 个真缺陷的红测+最小修复**（见 §4，证据充分后按红绿流程执行）
- 交付物：本报告 + `changes.patch`（galaxy_grpc_service.py 修复 + 新测试文件）

---

## 0. 结论摘要（定性裁决）

主会话观察到的"两轮探针图面不同"**不是单一缺陷**，是三个独立机制叠加：

| # | 定性 | 内容 |
|---|------|------|
| 1 | **测试数据污染**（非产品逻辑） | `node-0..4` VOID 占位节点是 **pytest fixture 泄漏进演示库**的历史数据，全局 published，对所有用户的图面永久可见。**不存在"占位生成器"**——生产代码零 `node-N` 命名点。 |
| 2 | **真缺陷（已红测复现+最小修复）** | `GetUserGalaxy` gRPC 分支在 `@cached` Redis 缓存命中时拿到 plain dict，`graph.nodes` 必崩 `'dict' object has no attribute 'nodes'` → 空响应 + INTERNAL → 网关回落 REST。生产日志 4 次 ERROR 实证。 |
| 3 | **行为不一致（设计层面，移交裁决）** | 同一 `/api/v1/galaxy/graph` 有两种应答键形（gRPC 简化键形 vs REST 完整契约）；且 600s TTL 内诊断评分后取图可能拿到诊断前缓存（失效链有时序缺口）。A/B 差异的直接来源是**取图相对诊断评分的相位差 × 双分支 × 缓存**。 |

**诚实申报的缺口**：服务器端证据显示 B 的每次取图载荷都含 129 节点（含 mastery），无法从服务端复现"0 真节点 + 仅 VOID 占位、持续 >2 分钟"的报告。探针侧解析/请求参数需要主会话复核（§3.4）。

---

## 1. 两账号对比取证表

账号标识按纪律脱敏：A = `probe_inv5_…`（短 id `df9f0a2a`），B = `probe_shield_…`（短 id `a7e59544`）。DB 时间为 UTC；日志时间为本地（UTC+8）。

| 维度 | A（probe_inv5_… / df9f0a2a） | B（probe_shield_… / a7e59544） |
|---|---|---|
| 注册 | 17:42:33.777 | 17:43:47.793 |
| 取图 #1 | 01:42:34.0 网关 → **gRPC 分支**，cache-miss 计算（grpc 日志 backfill enqueue :34.003 实证） | 01:43:47.8 网关 → **gRPC 分支**，cache-miss 计算（enqueue :47.895） |
| 取图 #2 | 01:42:34.7 网关 → gRPC 分支，再计算（enqueue :34.751） | — |
| 诊断评分 | ~01:42:5x，写 8 行 mastery | 01:43:58.9–59.5，写 **8 行 mastery**（`user_node_status.created_at` 实证：命题逻辑 25 / 二元关系 50，全部指向 published dm-pack 节点） |
| 取图 #3 | 01:42:58.7（评分后登录取图）→ gRPC **缓存命中 → dict 崩溃**（ERROR :58.737）→ REST 回落 → FastAPI 命中 #1/#2 的**诊断前缓存**（600s TTL），200 | 01:44:13.1 → gRPC **缓存命中 → dict 崩溃**（ERROR :44:13.173）→ REST 回落 → FastAPI 命中评分后 #2 重算缓存（**含 8 行 mastery**），200 |
| 取图 #4 | — | 01:44:31.6 → 同 #3（ERROR :44:31.723），200 |
| 图缓存失效 | 评分失效发生在 #3 命中之后（时序竞态）→ #3 拿到**评分前**载荷 | 评分失效发生在 #2 之前 → #2 **重算**（enqueue :59.614 实证），载荷已含 mastery |
| 服务端载荷节点数 | 129（via:grpc 简化键形 ×2；REST 完整键形 ×1） | 129（via:grpc 简化键形 ×2；REST 完整键形 ×2） |
| 探针报告 | "129 真节点" | "0 真节点 + 一批 VOID 占位、持续为空 >2 分钟" |

**当前库面复核**（只读）：`knowledge_nodes` published = **129**（与 A 报告的 129 完全吻合 = 119 真节点 + 10 个 node-0..4 占位）；draft = 54。用 `get_graph_view` 的精确 WHERE 对 B 的 user_id 复算：**可见 129**（`status IS NULL OR 'published' OR draft+unlocked`，`structure_service.py:361-434`）。

---

## 2. VOID 占位节点溯源（任务 1）

- **库中事实**：`node-0..node-4` 共 **两批**：2026-09-19 06:27:25 与 2026-09-20 04:34:50 各 5 行。`source_type='seed'`、`is_seed=f`、`status='published'`、`importance_level=1`、`dominant_sector_code='VOID'`、description/keywords 全空、无 parent/subject。
- **生成器排查**：全仓（backend py / gateway go / dart / sql / 迁移）**不存在任何生产侧 `node-N` 命名点**。唯一匹配：测试 fixture 模式 `KnowledgeNode(name=f"node-{index}", …)`——`backend/tests/unit/test_achievement_event_consumer.py:32`、`backend/tests/integration/test_north_star_journey.py:901`。两批时间戳与"pytest 直连演示库整跑"的形态一致（一次 5 个、成批毫秒级连创）。
- **裁决：测试污染**，不是冷启动 scaffold。产品里的 scaffold 是另外两家，均已排除：`galaxy_bootstrap_service.py`（onboarding 5 个中文标题节点）、诊断 `_ensure_topic_node`（`exam_sprint_diagnostic_service.py:1517-1553`，published + is_seed=True + 真实主题名）。
- **为何人人可见**：`get_graph_view` 对 published 节点是**全局查询**（无用户过滤）→ 这 10 行进入每个新用户的图面。A 报告的"129 真节点"其实**也含这 10 个占位**。
- **VOID 语义**：`sector_code:"VOID"` 不是生成器产物，而是无星域数据节点的**回退显示值**（`node_sector_service.py:185-197 resolve_sector_weights` / `dominant_sector_from_weights` fallback=VOID）。当前库 VOID-dominant 共 29 行（10 个 node-N + 19 个星域分类未完成的真节点——见 §3.5 backfill 积压）。
- **处置建议**：清理这 10 行属演示库**写操作**，本卡只读未执行，移交主会话裁决（`DELETE FROM knowledge_nodes WHERE name ~ '^node-[0-9]+$'`，删除前核对无关联关系/状态行）；同时建议测试套件与演示库隔离（独立 test DB），否则占位会再次积累。

---

## 3. 异常因果链（行号证据）

### 3.1 缺陷链：gRPC 缓存命中必崩（真缺陷，已修复）

1. `galaxy_service.py:2254-2268`：`get_galaxy_graph` 挂 `@cached(ttl=600, key_builder=…user_id…)`；缓存后端 Redis（`core/cache.py` `CacheService.set` `json.dumps`/`get` `json.loads`，L117-135/L155-166）。
2. 缓存命中 → `@cached` 返回 **plain dict**（JSON 往返，模型类型被侵蚀）。
3. `galaxy_grpc_service.py:325`（修复前）：`graph.nodes or []` → `AttributeError: 'dict' object has no attribute 'nodes'`。
4. `galaxy_grpc_service.py:343-347`：except → 空响应 + `StatusCode.INTERNAL`。
5. 网关 `galaxy_handler.go:530-553` GetGraph：`err != nil` → log "gRPC failed, falling back to REST" → `ProxyToBackend` 双跳回落。
6. **生产实证**：`/private/tmp/sparkle_grpc.log` 4×ERROR（01:42:16.149 / 01:42:58.737 / 01:44:13.173 / 01:44:31.723），全部是缓存命中路径；A 的 #3、B 的 #3/#4 均走了回落。
7. 影响面：gRPC 分支在 600s TTL 内**永远不可用**（每次都崩）；未命中时正常但应答为**简化键形**（`id/name/mastery_score/node_type/tags`，无 `sector_code/importance_level/user_status/user_stats`，`galaxy_handler.go:575-640`）——与 REST 完整契约（`schemas/galaxy.py:650-657 GalaxyGraphResponse`）不同形。

### 3.2 A/B 相位差链（为何"同链路不同结果"）

- **B 的评分→失效→重算**：评分写 mastery（`exam_sprint_diagnostic_service.py:1540-1546 _write_mastery_value` → `GalaxyService.update_node_mastery`，outbox 事件）→ 事件消费侧读面失效（`outcome_absorption_service.py:172 invalidate_galaxy_graph_view_cache`，键面 `{APP}:view:get_galaxy_graph:{user}:*` 与 @cached 命名空间一致）→ B#2 在失效后到达 → 重算（enqueue :59.614 实证）→ 载荷含 8 行 mastery → 缓存。
- **A 的 #3 抢在失效前**：A 的取图与评分几乎同刻（:58.69 login、:58.737 gRPC HIT）→ 命中 #1/#2 的**诊断前**缓存 → 评分未反映。两账号只是**相位不同**，机制同一。
- A/B 各自取图 #1/#2（via:grpc 简化键形）与 #3/#4（REST 完整键形）**键形不同**——任何按 REST 契约解析的探针，在 gRPC 应答上会读不到 `sector_code/importance_level/user_status` 等键。

### 3.3 "图面持续为空 >2 分钟"的服务端核查

服务端**无**"持续为空"实证：B#2 重算即含 mastery；#3/#4 从 Redis 命中同一载荷；网关日志最后一条 /graph 请求为 01:44:31，之后无该端点流量（">2 分钟重拉"未见于网关/FastAPI/任意进程日志）。`@cached` TTL=600s（主会话以为的"10s 缓存早过期"是 API 层 `EndpointShield`，`api/v1/galaxy.py:66` ttl=10——它只做单飞/短去重，服务级缓存是 600s）。

### 3.4 诚实申报：探针报告与服务器真相的缺口

B 报告的 VOID 占位签名（`name:"node-1"`、`sector_code:"VOID"`、`importance_level:1`、`user_status:null`）**与 REST 完整键形吻合**（=B#3/#4 载荷），该载荷服务端含 129 节点；其中的 node-0..4 占位恰好完整匹配该签名（10/129）。但"**0 真节点**/仅 VOID"无法由任何服务端路径产生（`get_graph_view` 全局 WHERE 对 129 恒真；`sector_code=VOID` 过滤按 `node_belongs_to_sector`（`node_sector_service.py:289-296`）会留下 ≥29 行而非恰好 10；LOD（zoom<0.5）方向相反，会滤掉占位而非真节点）。可能解释（按可能性排序）：(a) 探针只解析/展示了部分字段或子集后判定为空；(b) 探针在 gRPC 简化键形应答（#1/#2）上按默认值渲染；(c) 探针带了未申报的查询参数。**建议主会话用网关 curl 重放 B#3（带 B 的 token）直接核对节点数。**

### 3.5 顺带发现的机制性弱点（移交，不在本卡修）

- 星域回填队列**持续满载丢弃**：`glm_batch_service` enqueue 时 `QueueBackpressure drop dispatch queue=glm_batch depth=200 cap=200`（grpc 日志每次取图后均有）→ 星域分类长期不执行 → VOID 回退面扩大（当前 29/129）。
- 演示库另有一处独立污染证据：`security_audit_logs` INSERT 因 `id` 无默认值持续失败（FastAPI 日志高频 NotNullViolationError），与 galaxy 无关，移交。
- `GetUserGalaxy` 鉴权失败路径返回**空响应而非错误码**的旧注释（`galaxy_galaxy_grpc_service` 曾有 set UNAUTHENTICATED 现行为正确，gateway SEC-3 注释仍描述旧行为）——文档漂移，无行为影响。

---

## 4. 修复（红绿流程）与回归

**改动域**：`backend/app/services/galaxy_grpc_service.py`（+13 行含注释）+ 新测试 `backend/tests/unit/test_galaxy_grpc_cached_graph.py`（3 例）。未触碰 `@cached`/`cache.py`/`structure_service`/`api/v1/galaxy.py`。

- 修复：`GetUserGalaxy` 在 `get_galaxy_graph` 返回后加 `if isinstance(graph, dict): graph = GalaxyGraphResponse.model_validate(graph)`（还原模型后再取 `.nodes/.edges/.user_stats`）。REST 路径不动（FastAPI `response_model` 本就重验 dict）。
- 红测证据（修复前）：servicer 级测试复现与生产日志**逐字相同**的失败——`code=StatusCode.INTERNAL details="'dict' object has no attribute 'nodes'"`；`2 failed, 1 passed`。
- 绿测证据（修复后）：`3 passed`。
- 定向回归：`test_f821_undefined_name_bugfix.py`（同文件既有测试）+ 新测试 = `11 passed`；`pytest tests/unit -k galaxy` = `38 passed, 1 failed, 1 skipped`——该 1 failed（`test_theater_seed_and_accuracy`，theater bundle 域）**已用基线对照确认预先存在**（stash 本修复后单跑仍 FAILED，与本次改动无关）。
- 边界：修复未在真实 gRPC 链路端到端验证（演示栈三进程属主仓运行态，本卡零运维动作，未重启）。建议合并者重启 grpc_server 后以网关拉图并观察 grpc 日志不再出现该 ERROR。

---

## 5. 冲突面声明（Worker 要素③）

- 本卡改动文件：`backend/app/services/galaxy_grpc_service.py`、新增 `backend/tests/unit/test_galaxy_grpc_cached_graph.py`。
- **wt140**：改动 `backend/app/core/request_coalescing.py`（EndpointShield）——**零文件交叠**。语义关联仅在报告：本卡引用 shield 的 ttl=10 行为（`api/v1/galaxy.py:66`），未改其任何代码。
- **wt138/139**：按任务卡说明与 galaxy 无关；本地未发现其 worktree（sysrev 下仅 wt140/141/142），无交叠。
- 本卡未动：`galaxy_service.py`、`core/cache.py`、`api/v1/galaxy.py`、`structure_service.py`、`node_sector_service.py`（全部只读走查）。

## 6. 诚实申报（Worker 要素④）

1. 读主仓 `backend/.env` 获取库连接（任务卡明示允许）；凭据仅进入本会话命令环境与 psql 连接串，未写入任何文件/报告。
2. 一次 `git stash push/pop`（单 tracked 文件、秒级、立即恢复，用于基线对照；worktree 为本卡专属，无并发会话；untracked 交付物未受影响）。
3. worktree 缺 gitignored 的 `app/gen`，pytest 前临时 `ln -s` 主仓生成产物，**收工已删**（复跑测试需重建：`ln -s <主仓>/backend/app/gen <worktree>/backend/app/gen`）。
4. 探针"VOID-only"报告未能服务端复现（§3.4），未强行归因。
5. 主会话给出的变量（"A prime 后 0.5s 二次取图；B 多 sleep 11s"）与日志相位吻合（A 两次取图 :34.0/:34.7；B #1→评分间隔 11.1s），但它们**不是**差异根因——根因是 §3.1/§3.2。
6. 未执行任何演示库写操作；`node-0..4` 清理与 `security_audit_logs` 缺陷移交。

## 7. 收工核查（Worker 要素⑤）

- psql 只读证明：所有取证查询以 `SET default_transaction_read_only=on` 开头执行；未发出任何 DML/DDL；`docker ps`/`redis-cli --scan`/日志均为只读。
- /tmp 自清：仅**读取**了既有 `/private/tmp/sparkle_{fastapi,gateway,grpc}.log`，未新增任何 /tmp 文件。
- 脱明文：报告不含完整 username（仅 probe 前缀+短 id）、不含任何凭据/连接串；`changes.patch` 为纯代码。
- git：零 commit / 零 push；工作区 = 1 个 tracked 修改 + 2 个 untracked 交付目录（patch/报告），`git status` 已核对。
- 交付物：`v3-output/COLDSTART/REPORT.md`、`v3-output/COLDSTART/changes.patch`。
