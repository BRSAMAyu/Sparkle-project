# SECTOR-AUDIT · 收工报告

> 卡面：glm 星域回填队列满载丢弃 + security_audit_logs INSERT 失败（COLDSTART 卡移交双可靠性项）
> Worker worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt147`（基线 dd2be807）
> 交付物：本报告 + `changes.patch`（7 个 hunk 面：4 改 3 新，零 commit）
> 日期：2026-09-23

---

## ① 双根因（代码 + 活栈实证）

### 根因 A：星域回填队列满载持续丢弃（VOID 29/129 劣化）

**丢弃机制**（哪里丢的）：`backend/app/core/queue_backpressure.py:138-149` + `:232-245`
—— glm_batch 队列深度 ≥ 上限 200（`app/config/settings.py:435`
`QUEUE_BACKPRESSURE_LIMITS_JSON = '{"glm_batch": 200}'`）时投递被拒，返回 False +
drops 指标 + WARNING。活栈实证（`/tmp/sparkle_grpc.log:137` 起共 19+ 条）：

```
[QueueBackpressure] drop dispatch queue=glm_batch depth=200 cap=200
(queue_depth=200>=cap=200); task NOT enqueued (bounded backlog policy)
```

**为什么恒满**（三个叠加的生产面缺陷，均在 `node_sector_service.py`）：

1. **completed-VOID 节点被永久重选**（主源头）：`find_nodes_needing_backfill`
   旧条件 `dominant_sector_code == 'VOID'` 无 status 门槛——LLM 判定确属 VOID
   的 **completed** 节点永远命中重选。演示库实证（只读 SELECT）：
   `completed|VOID = 27 个`、`pending|VOID = 19 个`。27 个 completed-VOID
   每次取图都被重新灌进队列，且 LLM 重分类后大概率仍是 VOID（信息不足的节点
   本就该 VOID），形成永久重复入队源。
2. **无在途去重**：`ensure_backfill_for_user`（:517，修复前）挂在
   `get_galaxy_graph`（galaxy_service.py:2280）**每次取图**上；节点入队后到
   worker 执行前一直停在 `pending`，而 `pending` 又在重选集里 → 同一批节点被
   反复 enqueue。活栈实证（/tmp/sparkle_grpc.log:4174-4181）：同一用户 0.7s /
   12s 内两次 `enqueue node_sector_backfill node_count=24`。
3. **消费端缺位/慢**：收工时点 `ps` 实证无 celery worker 在跑
   （glm_batch 专用 worker 未随栈起）；且 minimax_m3_batch 单任务 24 节点逐个
   LLM 调用（/tmp/glm_batch_drain2.log 实证单调用秒级），即使 worker 在跑，
   生产速率（每次取图 1 任务）> 消费速率时队列必然顶满。

**VOID 形态**：修复时点演示库 173 节点，27 completed-VOID + 19 pending-VOID
（COLDSTART 记录的 29/129 为早期快照，形态一致）。丢弃策略后果：新节点回填
被丢 → VOID 只进不出 → 星图分区质量劣化。

### 根因 B：security_audit_logs INSERT 持续失败

**具体错误**（活栈实证，`/tmp/fastapi_engine.log:109` 起共 29 条）：

```
NotNullViolationError: null value in column "id" of relation
"security_audit_logs" violates not-null constraint
```

- 表 DDL（baseline 迁移 `cc9383c4c29f_full_baseline_schema.py:1580`）：
  `sa.Column('id', sa.UUID(), nullable=False)` **无 server_default**；
- 模型（`app/models/audit_log.py:22` 修复前）：
  `id = Column(PGUUID(as_uuid=True), primary_key=True, index=True)`
  **无 Python 侧 default**（对照同文件 AdminAuditLog.id:56 有 `default=uuid.uuid4`）；
- 写入点 `_record_security_event`（`app/core/security_monitor.py:403`）构造
  SecurityAuditLog 不传 id → 每条 INSERT 必带 NULL id → 必然失败。
  SAWarning 在日志里同点位复证（fastapi_engine.log:108）。

**失败降级行为的二次伤害**（修复前）：except 分支 `await db.rollback()`
回滚**整个请求事务**——同事务里已 flush 的 LoginAttempt（登录审计）一并被吞；
且 flush 成功后 Redis setex 失败也会误入同一 except → 把已落库的审计行回滚。
安全审计数据 100% 丢失 + 请求级数据放大丢失。

## ② 修法与红线面

### A. 回填队列（`backend/app/services/node_sector_service.py`，最小侵入）

1. **选择面排 completed**：`find_nodes_needing_backfill` 与
   `ensure_backfill_for_user` 的 candidate 过滤统一加
   `sector_classification_status != 'completed'`（NULL status 用 `is_(None)` 补
   集，不漏存量行）；另加 `deleted_at IS NULL`（软删不占预算）。
   completed-VOID 的存量修正走重放脚本，不走热路径。
2. **在途去重**：新 `_backfill_inflight` / `_mark_backfill_inflight`——投递前查
   Redis 键 `sector_backfill:inflight:{user_id}`，命中即跳过入队；投递成功后
   写键，TTL=`NODE_SECTOR_BACKFILL_DEDUP_TTL`（settings.py:440，默认 600s）。
   只用既有 cache_service，未造新基础设施。
3. **丢弃显式降级**：`enqueue_backfill_for_nodes` 对 dispatch False 显式
   WARNING（含 user/nodes 数与"pending 留待下轮重试"）；丢弃不写在途标记 →
   下轮取图自然重试（丢弃不再无声，也不死锁）。
4. **有界降级**：Redis 去重面自身故障 → 放行入队只记 warning（背压硬顶仍在，
   不存在无界堆积路径）。

**红线面核对**：不改 proto、不改 DB schema、Go 网关零触碰、
`queue_backpressure.py`/`celery_dispatch.py`/`celery_app.py` 零改动（O-07 语义
原样，仅调用方收敛生产量）；容量 200 未动——去重后生产量塌缩到
每用户每 TTL ≤1 任务，上限不再是瓶颈。

### B. 审计 INSERT

1. **模型默认值**（`backend/app/models/audit_log.py:22`）：
   `SecurityAuditLog.id` 加 `default=uuid.uuid4`（客户端默认值，与同文件
   AdminAuditLog 同型）。**无需迁移**——表结构不变，未新增迁移文件，
   合入方无需验 head（当前 head 仍单头 `erridemconc_20260922`）。
2. **SAVEPOINT 隔离 + 降级留痕**（`app/core/security_monitor.py:403`）：
   INSERT 包进 `db.begin_nested()`——失败只回滚审计行自身，外层事务
   （LoginAttempt 等）存活；失败时完整事件 JSON 以 `[SecurityAuditFallback]`
   打 WARNING（loguru 文件 sink 落盘留痕，非静默）；Redis 实时监控面挪入独立
   try，失败仅 warning，不拖垮已落库审计行。原 `db.rollback()` 毒化点移除。

**红线面核对**：分层边界未动（engine 内部行为）；无凭据；audit 语义仍是
"尽力落库 + 失败可观测"。

## ③ 测试矩阵（红线：双向钉死 + 相邻域零新增失败）

新增 13 用例（全绿）：

| 文件 | 钉死点 |
|---|---|
| `backend/tests/unit/test_node_sector_backfill_dedup.py`（7） | completed-VOID/completed 不再被 DB 查询面与 candidate 面重选；pending/failed/未分类仍选中；在途命中不重复入队（不改状态不投递）；投递成功写在途标记；背压丢弃 → 显式 WARNING 留痕 + 不写标记 + 节点保持 pending（满载降级不丢无声）；Redis 探测故障放行（有界降级）；分类完成后节点离开回填池 |
| `backend/tests/unit/test_security_audit_insert.py`（6） | 无显式 id 的 INSERT 成功（flush 时默认值生成）；`_record_security_event` 落库 + Redis 镜像；flush 级 IntegrityError 只回滚 SAVEPOINT（外层 LoginAttempt 存活 + `[SecurityAuditFallback]` 全事件 JSON 落日志）；残缺事件构造失败不外抛不打断调用方；Redis 故障不丢已落库审计行；id 逐行唯一 |

相邻域定向（对比法）：

- `test_o07_queue_backpressure.py`（15）+ `test_batch_worklane.py`（33）+
  `test_admin_audit.py`（3）：**51 passed**；
- galaxy/audit 相邻域 `test_galaxy_grpc_cached_graph` / `test_sprint_galaxy_mastery`
  / `test_task_galaxy_coupling` / `test_glm_batch_adaptive` /
  `test_learning_cutover_audit` / `test_auth_login_empty_credentials` /
  `test_galaxy_learning_graph_operational` / `test_draft_knowledge_nodes_fallback_linkage`
  / `test_guest_seed_service` / `test_expansion_service`：**21 passed**；
- `test_galaxy_concurrency.py` 3F+3E：**基线克隆（/tmp 对照，HEAD dd2be807）
  同样 3F+3E**——asyncpg 密码认证环境性存量失败，与本次改动无关，**零新增失败**。

风格：新增代码 ruff 全绿；black --diff 确认新增行无违例（存量文件本就不
black-clean，未做全文件重排——最小侵入）。

## ④ 存量 VOID 重放方案（活栈重放留主会话）

新增幂等重放脚本：`scripts/devtools/replay_void_sector_backfill.py`
（进程内直接调 `NodeSectorService.classify_nodes_by_ids`，按 user 分组走
`UserNodeStatus` join——与 get_graph_view 同源；每批 commit + 按 user 失效星图
缓存；不经过 glm_batch 队列，不占背压额度，不依赖 worker 在跑；软删排除；
dry-run 只 SELECT）。演示库 dry-run 实证：**92 节点 / 39 用户**命中重放面。

主会话重放序列（活栈执行，本 worker 未动活栈）：

```bash
# 1) 清掉 200 条存量积压（重复任务），或起 worker 让其自然排空
docker exec sparkle_redis redis-cli -a "$REDIS_PASSWORD" DEL glm_batch

# 2) 带引擎真实 env 重启 engine（加载修复后的代码）后，幂等重放：
SECRET_KEY=test DATABASE_URL="postgresql+asyncpg://postgres:<PW>@127.0.0.1:5432/sparkle" \
  LLM_API_KEY=<引擎现网 key 配置> \
  python3.11 scripts/devtools/replay_void_sector_backfill.py --dry-run   # 先看清单
# 去掉 --dry-run 实跑；可 --user-id 限单用户、--batch-size 调批、--no-completed-void 排除
```

幂等性：重跑仅按当前 LLM 判定重写 sector_weights/dominant/坐标
（update_node_classification 对已有非 VOID 坐标 keep_position）；单节点 LLM
失败只标 failed 可再跑。

## ⑤ Worker 五要素

1. **双根因**：见 ①——A) completed-VOID 永久重选 + 无在途去重 +（活栈）worker
   缺位 → 队列恒满 200 → 背压丢弃；B) `security_audit_logs.id` 双侧无默认值 →
   NotNullViolation，失败分支 rollback 毒化整个请求事务。
2. **修法与红线面**：见 ②——选择面排 completed、Redis 在途去重（TTL 600s
   可配）、丢弃显式降级；审计 id 客户端默认值（**无迁移**）+ SAVEPOINT 隔离 +
   `[SecurityAuditFallback]` 留痕。proto/迁移/网关/背压面零改动。
3. **冲突面**：改动文件为 `node_sector_service.py`、`security_monitor.py`、
   `audit_log.py`、`settings.py` + 3 新文件。**wt140（galaxy API 缓存）**：我
   未改 galaxy_service.py/galaxy.py 任何 hunk，仅其调用的
   node_sector_service 内部变化，无 hunk 位置冲突；**wt144（事件消费）**：未触
   celery/consumers；**wt145（l10n）/wt146（安全词库）**：无交集。唯一潜在
   并发点：`settings.py` 单 hunk（QUEUE_BACKPRESSURE 块后追加 4 行），如他卡也
   动 settings.py 建议合入方后写者 rebase。
4. **诚实申报**：
   - DataAccessLog / SystemConfigChangeLog / ComplianceCheckLog 存在同型
     id 缺默认缺陷，但全库检索无任何实例化写入点（仅定义），按最小侵入未改，
     记为潜在债务（如未来接线写入须同修）；
   - 消费提速未做代码改动（属 worker 部署/并发配置，非本卡代码面）；队列容量
     200 未调（去重后无必要，如需可 env 覆盖）；
   - 演示库仅执行 SELECT（含 dry-run）；llm key 未配置环境下 replay 实跑会逐
     节点标 failed——重放须带引擎真实 LLM env（已在 ④ 注明）；
   - worktree 内 `backend/app/gen/` 为从主仓拷贝（任务卡授权，git-ignored，
     不入 patch）。
5. **收工核查**：零 commit/zero push；`git status` 恢复为「4 M + 3 untracked
   （均为交付代码）+ v3-output」；无 .env 落盘（凭据全程 env 内联且不入报告）；
   未起任何长驻进程/模拟器；`/tmp/wt147-baseline` 基线克隆已删；演示库只读。
