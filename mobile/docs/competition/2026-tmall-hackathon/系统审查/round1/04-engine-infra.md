# 全系统审查·第一轮 — 04 引擎·基础设施层（API/Celery/消费者/DB/配置）

- 审查员：4 号（engine-infra 切片）
- 基线：`main@90daac8a`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt4`，只读审查）
- 范围：`backend/app/` 顶层非 services 部分（main.py、api/、config/、core/、db/、models/、middleware/、consumers/、workers/、tasks/、celery_schedule.py、event_publishers/、adapters/、signals/（抽查）、routing/、data/（抽查）、schemas/（抽查）、checkpoint/、tools/（抽查）、utils/）+ 两项专项（aurora kill-switch 家族一致性、card_protocol 快速面审）
- 方法：main.py / config / db / consumers / celery_schedule / celery_app / event_bus 逐行深读；api/v1/router.py 注册完整性用脚本 diff；beat_schedule 与 task_routes 用「导入 celery app + 对照任务注册表」脚本自动化核对；alembic 链用 `alembic heads` 离线验证；kill-switch 家族 25 文件全量 grep 比对。

---

## 1. 总评

**骨架总体健康，但 Celery 侧有一个「每次必失败」的任务和一个「永远不会被消费」的 beat 任务——都是调度层消息丢失/功能静默失效级别的缺陷。** 配置层（production 校验、CORS 禁通配、SECRET_KEY 快速失败）与事件总线（先处理后 ack、DLQ 双写、幂等去重、xautoclaim 索赔）质量明显好于平均水平；kill-switch 家族 24 个服务全部走 `app/core/kill_switch.py` 单一引擎，无签名漂移。主要风险集中在三处：① `get_db_context` 的跨 event-loop 设计使 policy 任务 100% 失败并形成重试风暴（P1）；② `tasks.community.send_checkin_reminders` 不在 worker `include` 里，beat 每天两次投递的消息被 worker 以 unregistered task 丢弃（P1，属消息丢失类）；③ event_bus 的消费循环任务游离在 lifespan 管理之外，关机不优雅（P2）。DB 会话层、models 索引、alembic 链（heads=1）均验证通过。

---

## 2. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|----|--------|-----------|----------|----------|----------|
| EI-01 | **P1** | `backend/app/tasks/policy_tasks.py:20`（根因 `app/db/session.py:169`） | beat `policy-compiler-due-scan` 每 30s 触发 `tasks.policy.process_due_policies`；`with get_db_context()` 写在 async 函数体内，`__exit__` 里的 `asyncio.run()` 在运行中的事件循环上被调用 → `RuntimeError: asyncio.run() cannot be called from a running event loop`。任务 100% 失败，`autoretry_for=(Exception,) max_retries=3` × 每 30s 一发 = 常态化重试风暴；**PolicyCompiler 的到期策略扫描从未执行过** | `async def _run()…: with get_db_context() as db: return await PolicySchedulerService(db).process_due_policies()` 外层 `_run_async(_run())`（celery_app.py:39 持久循环） | 与其他任务统一为同步体模式： |
| EI-02 | **P1** | `app/core/celery_app.py:63-71`（include 表）+ `:1153-1163`（beat 两条目）+ `app/tasks/community_checkin_reminder.py:86` | beat 每天 10:00/20:00 投递 `tasks.community.send_checkin_reminders`，但该模块**不在 celery `include` 列表**、celery_schedule 也不导入它 → worker 启动时不加载，任务未注册 → beat 消息到达 worker 后按 unregistered task **直接丢弃**（acks_late 也救不回）。群组打卡提醒功能全链路静默死亡。已用脚本实证：注册表中查无此任务（模块单独 import 可注册，唯独没人 import 它） | `include=["app.core.celery_tasks", "app.tasks.accountability_tasks", "app.tasks.absence_scan_task", "app.tasks.checkpoint_nudge_task", "app.tasks.policy_tasks", "workers.signals_learning_worker", "app.aurora.tasks"]`（无 community_checkin_reminder） | include 增补一行（P0 类消息丢失，附 diff）： |
| EI-03 | P2 | `app/db/session.py:150-178` | `get_db_context` 在 `__exit__` 用**三次独立的 `asyncio.run()`**（commit/rollback/close）驱动同一个 AsyncSession：内层协程在 loop L2 建立的连接/事务，到 L3/L4 上 commit/rollback。正常路径靠「服务层内部已 commit + 干会话上 commit 是 logical 事务」侥幸成立；一旦内层协程半途抛异常留下未提交事务，L3 上的 rollback 会立即 `RuntimeError … attached to a different loop`，**掩盖原始异常**并可能把死循环连接留在池里 | `asyncio.run(_commit_session(session)) … asyncio.run(_rollback_session(session)) … asyncio.run(_close_session(session))` | 让 `get_db_context` 只做同步 yield、由调用方在**同一个** loop 里完成 commit/rollback/close（即删除 exit 中的三次 `asyncio.run`，改为要求任务体内自提交，或提供 `async with` 版本）；同族 `app/tasks/accountability_tasks.py`（全文件 0 个内部 commit，依赖这个危险的外层 commit）优先改造 |
| EI-04 | P2 | `app/core/event_bus.py:1122-1133` + `app/main.py:501-681` | `event_bus.subscribe()` 把真正的 `_consume_loop` 用 `asyncio.create_task` 挂在 bus 内部后**立即返回**；各消费者的 `start()` 随之结束。lifespan 里保存并 cancel 的 `*_consumer_task` 是**已完成的句柄**，cancel 全部空转；`event_bus.close()`（唯一会取消 `_consumer_tasks` 的入口）在 main.py 关机流程中**从未被调用**。后果：关机不排空、在途消息处理被打断（靠 pending 重投兜底）、关机窗口内 loop 死亡还会被 `_restart_consume_loop` 复活（`_running` 仍为 True）、退出时 "Task was destroyed but it is pending" 刷屏 | `task = asyncio.create_task(self._consume_loop(...)); … self._consumer_tasks.append(task)`（subscribe 内）；shutdown 段只有各 `getattr(app.state, …).cancel()` | shutdown 末尾（cache_service.close() 之前）补 `await event_bus.close()`；并在关机一开始 `event_bus._running = False` 阻止重启回调 |
| EI-05 | P2 | `app/services/graph_reasoning_service.py:91`（由本切片验证测试 `tests/test_migrations.py::test_graph_caching_preserved` 稳定复现） | 图缓存放进 Redis 后**永远读不回来**：`cache_service.redis` 以 `decode_responses=True` 创建（`app/core/cache.py:42`），`get` 返回 `str`，代码却对它调 `.decode("ascii")` → `AttributeError` → except 吞掉 → 每次 `_load_graph` 都回源 DB。缓存写路径正常打日志，读路径 100% 失效，纯性能损失且无告警（日志级别 warning 被淹没） | `stored_sig = raw_cached[:64].decode("ascii")` | ```diff
-                    stored_sig = raw_cached[:64].decode("ascii")
-                    json_payload = raw_cached[64:]
+                    if isinstance(raw_cached, str):
+                        raw_cached = raw_cached.encode("utf-8")
+                    stored_sig = raw_cached[:64].decode("ascii")
+                    json_payload = raw_cached[64:]
``` |
| EI-06 | P2 | `app/services/kill_switch_readiness_service.py:37,46,65,74,119,128` | 就绪度报告（经 `api/v1/admin_dashboard.py`、`api/v1/audit.py` 暴露给运维）引用 6 个**不存在的 settings 键**：`AURORA_STAGE19_WM_MODE`（实际 `AURORA_STAGE19_WORKING_MEMORY_MODE`）、`AURORA_STAGE21_SKILL_MODE`（实际 `…_SKILL_STORE_MODE`）、`AURORA_STAGE24_POLICY_MODE`（实际 `…_POLICY_COMPILER_MODE`）、`AURORA_STAGE25_REFLECTION_MODE`（实际 `…_REFLECTION_WIRE_MODE`）、`AURORA_STAGE30_METACOGNITION_MODE`（实际 `AURORA_METACOG_MODE`）、`AURORA_STAGE31_IDIOGRAPHIC_MODE`（实际 `AURORA_IDIOGRAPHIC_MODE`）。`_current_mode` 的 `getattr(settings, key, fallback=catalog["current"])` 使假键永远回退到"live"——运维若把真实开关拨到 off，报告仍显示 live，升级决策失真 | `"settings_key": "AURORA_STAGE19_WM_MODE",` 等 | 修正 6 个键名；`getattr` 缺键时应报错/标注 unknown 而非静默回退 |
| EI-07 | P3 | `app/core/celery_app.py:118-160` vs 任务注册表（脚本实证） | 6 条 task_routes 指向不存在的任务名，永不生效（无功能损失，因相关任务用 `send_task(queue=…)` 显式指队或落 default）：`app.core.celery_tasks.generate_embedding`（实际名 `generate_embedding`/`generate_node_embedding`）、`…batch_error_analysis`、`…cleanup_old_data`、`tasks.policy.process_due_policies`、`tasks.checkpoint_nudge.scan_daily_checkpoints`、`tasks.checkpoint_nudge.run_due_checkpoint_wakes` | 路由键与任务实际 `name=` 对齐，或删掉无效条目 |
| EI-08 | P3 | `app/core/celery_app.py:952-1221` vs `app/celery_schedule.py:140-164` | 同一任务被注册两份 beat 计划：`spine_expire_stale_states`（crontab */6h@:30 + 每 6h 起算）、`spine_auto_deprecate_skills`、`apply_memory_decay`、`evaluate_routing_outcomes`（1800s 带 args + 3600s 不带）→ 各自双频执行。均有默认参数所以不炸，但浪费配额且 side-effect 型任务双跑 | 二选一保留；`app/tasks/login_attempt_cleanup.py:84-89` 的模块级 `CELERYBEAT_SCHEDULE` 死配置（从未接线）一并删除 |
| EI-09 | P3 | `app/core/rate_limiting.py:31-34` | `default_limits=["600 per minute"]` 声明了默认限流，但项目**未挂 SlowAPIMiddleware**，仅 3 个文件用 `@limiter.limit` 装饰 → default_limits 从不生效，未装饰端点（绝大多数）实际无速率限制。另 `get_real_ip` 无条件信任 `X-Forwarded-For`（代码有 SECURITY NOTE 但无实现），客户端可伪造 IP 绕过按 IP 的 429 | 加 `SlowAPIMiddleware` 或明确移除 default_limits 防止虚假安全感；从可信代理数推算真实 client IP |
| EI-10 | P3 | `app/api/v1/health.py`（router 未注册）、`app/api/v1/errors.py`（router 未注册） | 两个完整 router 文件从未被 `router.py` include：`health.py` 的 DB 健康检查版本被 `health_production.py` 顶替（main.py 只借用它的 `set_start_time`）；`errors.py` 的错题 v2.1 端点与 `error_book.py` 重叠。均为死代码，且 api_root 端点列表还向客户端宣传 `/errors` | 删除或在 README 登记为已退役 |
| EI-11 | P3 | `backend/workers/signals_learning_worker.py`（顶层包） | celery include 以 `"workers.signals_learning_worker"`（无 `app.` 前缀）引用一个游离在 `backend/` 根的顶层包——与 `app/workers/` 平行存在，靠 Docker WORKDIR=/app 同时可导入两个根。能跑，但违反仓库分层直觉，新人极易改错文件 | 移入 `app/workers/` 并同步修改 include 字符串 |
| EI-12 | P3 | `app/models/accountability.py`（`uq_partnership_active_pair_bidirectional` 用 `Least/Greatest`） | 该索引表达式在 Postgres 合法，但 SQLite 测试夹具建表直接崩（`sqlite3.OperationalError: no such function: Least`），导致 134 个测试 error（见 §4）——accountability API 的测试防线形同虚设 | 模型层为 SQLite 注册 Least/Greatest 编译规则，或测试夹具改用 Postgres |

补充说明（非缺陷）：
- `conf.task_queues` 以 plain dict 传入在 Celery 5.6.3 下可正常展开（脚本实证 `amqp.queues` = default/glm_batch/high_priority/low_priority 四队齐全），且 `task_create_missing_queues=True` 兜底，不存在「投到未声明队列静默丢失」问题；beat 实际只产出 default/low_priority，glm_batch 队列由专用 worker 消费。
- 工作树缺 `backend/app/gen/`（gitignore 的 proto 产物，26 个文件引用）属环境性缺失，非仓库缺陷；本次审查已从主 checkout 复制一份仅用于跑测试。

---

## 3. 验证良好清单

1. **config/settings.py 生产防线完整**：`ENVIRONMENT=production` 强制非 DEBUG、`SPARKLE_RBAC_ENABLED`、`GRPC_REQUIRE_TLS`、PRODUCTION_URL 必须 HTTPS、CORS 禁 `*` 且仅 HTTPS、6 项关键密钥非空非占位、至少一个 LLM key——全部在 `model_validator` 快速失败（settings.py:1001-1146）。
2. **event_bus 可靠性语义正确**：先 `callback` → `idempotency.set` → `xack`（先处理后确认）；重试路径「先重投再 ack」；DLQ「先写 Redis 流 + DB 双落再 ack」、写失败则留 pending；`xautoclaim(min_idle=5s)` 收尸僵死消费者；消费循环异常自动重启（event_bus.py:863-951, 1143-1298）。
3. **幂等中间件**：键限长 256B、body hash 冲突返回 409、SSE 用包装 iterator 边收边缓存（上限 1MB）、锁 token 用 Lua 原子释放（api/middleware.py:46-220, cache.py:69-110）。
4. **kill-switch 家族一致性（专项①）**：24 个 `*_kill_switch_service.py` 全部走 `app/core/kill_switch.py` 的 `read_mode/write_mode/KillSwitchBinding`（grep 实证 core=1、raw redis get=0）；方法签名/三态归一/Redis-失败回退 settings 的行为无漂移；stage29/34 深读无样本外分支。仅 readiness catalog 键名漂移（EI-06）与 PREFIX 命名风格不一（纯装饰）。
5. **alembic 链**：`alembic heads` = `0150e391736a`（唯一 head），134 个迁移、19 个 merge 节点、无悬停 down_revision。
6. **models 高频查询字段索引**：`LoginAttempt.attempted_at/username/ip_address`、`IdempotencyKey.expires_at/key(PK)`、`EventBusDLQEntry.stream/event_type/message_id/failure_stage` 均有索引。
7. **路由注册**：显式 import 100+ 模块 + `_include_experience_routers()` 自动发现 `api/v1/experience/*_router.py`（router.py:201 确有调用）+ 去重保护；`app.main` 与关键模块全量 import 通过（除环境性 app.gen）。
8. **配置默认值安全性**：AuroraFlags 默认全关/休眠（config/aurora.py）、CORS 默认 `[]`、`DEBUG` 派生自 ENVIRONMENT、`WS_ALLOW_QUERY_TOKEN` 生产强制 False。
9. **middleware 顺序**（外→内）：Idempotency → CORS → AdminAudit → RequestContext → SecurityHeaders → slowapi 装饰器。OPTIONS 预请求不会被幂等中间件拦截（非 POST 直接放行），RequestContext 在最内层保证 request_id 在日志和异常响应中都可用。
10. **card_protocol 快速面审（专项②）**：`outcome_verifier.py`（celery 4h sweep + nightly full + main.py 内循环三方共用的入口）逐行读毕——Phase3/E 的每个外呼都有 non-fatal try/except + logger.debug 兜底，无未捕获的 `.value`/None 解引用路径；全目录无 mutable default args；consistency_validator.py 实际已不存在（Rule AT 例外清单过期，建议顺手清理文档）。未发现新的运行时级 bug。

---

## 4. 测试执行记录

命令（worktree 内；DB/Redis 为共享环境）：

```
cd /Users/brsama/code/GitHub/Sparkle-sysrev/wt4/backend && pytest tests/test_migrations.py tests/test_event_bus_shutdown.py tests/api tests/core tests/test_preference_consumer_safety.py -q
```

- 预处理：worktree 无 gitignored 的 `backend/app/gen/`（proto 产物）→ 从主 checkout 复制仅作测试缓存；无 `.env` → 运行时 source 主 checkout 的 `backend/.env`（未改任何仓库文件）。
- 结果：**1 failed, 96 passed, 4 skipped, 134 errors**（61.9s）。
- 134 errors 定性（按报错分类，均为 setup/夹具层）：
  - 98 × `sqlite3.OperationalError: no such function: Least`（EI-12，模型索引表达式不兼容 SQLite 夹具）；
  - 36 × `AttributeError: …bert_intent_classifier does not have the attribute 'AutoTokenizer'`（本机缺 transformers 模型权重，环境性）；
  - 其余 2 × StopIteration/StopAsyncIteration（下条）。
- 1 failed：`tests/test_migrations.py::test_graph_caching_preserved` — 单独重跑 2 次均失败（非共享环境抖动）。定性：**测试过期而非生产 bug**——生产代码已从 pickle 缓存升级为 JSON+HMAC（graph_reasoning_service.py:148-154），测试仍向读路径喂 `pickle.dumps(...)`（test_migrations.py:204）→ 读侧 UnicodeDecodeError → mock DB side_effect 耗尽 → StopAsyncIteration。但该测试顺带暴露了真实的 EI-05（str.decode bug，生产读缓存同样必失败）。
- `tests/test_event_bus_shutdown.py` 单独重跑：**passed**（注意：它验证的是 event_bus.close() 自身语义，并未覆盖 main.py 从不调用它的事实，即 EI-04）。
- 额外自动化核对（脚本，非 pytest）：celery 注册表审计（EI-01/02/07/08 证据）、`alembic heads`（唯一 head）、`importlib` 冒烟导入 app.main 与 13 个关键模块全绿（含 app.gen 后）。

---

## 5. P0/P1 修复参考块

EI-01（policy 任务，`app/tasks/policy_tasks.py`）：

```diff
@@ def process_due_policies() -> dict[str, int]:
-    async def _run() -> dict[str, int]:
-        with get_db_context() as db:
-            return await PolicySchedulerService(db).process_due_policies()
-
-    return _run_async(_run())
+    async def _run() -> dict[str, int]:
+        async with AsyncSessionLocal() as db:
+            result = await PolicySchedulerService(db).process_due_policies()
+            await db.commit()
+            return result
+
+    return _run_async(_run())
```

（`_run_async` 使用持久事件循环，会话从建到提交都在同一 loop 上；与 `app/core/celery_tasks.py` 现行模式一致。）

EI-02（community 任务注册，`app/core/celery_app.py`）：

```diff
     include=[
         "app.core.celery_tasks",
         "app.tasks.accountability_tasks",
         "app.tasks.absence_scan_task",
         "app.tasks.checkpoint_nudge_task",
+        "app.tasks.community_checkin_reminder",
         "app.tasks.policy_tasks",
         "workers.signals_learning_worker",
         "app.aurora.tasks",
     ],
```
