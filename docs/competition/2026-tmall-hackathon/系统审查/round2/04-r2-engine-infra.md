# 全系统审查·第二轮（R2）— 04 引擎·基础设施层（运行时/集成视角）

- 审查员：4 号（engine-infra 切片）
- 基线：`main@ca86bda8`（R1 修复已集成；F4 = `80f732b8`，协调者补修 audit.py = `b47d17cc` + `28445130`）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt4`（冻结，只读审查）
- R2 主镜头：运行时/集成——FastAPI 启动冒烟与全量路由表、Celery 冷启动三方匹配、消费者毒丸路径、资源生命周期全序列；移交专项为 EI-03 深层（13 调用点逐点诊断）与 EI-07~12 复核。
- 环境注记：R2 后段本机 PG(5432)/Redis(6379)/Docker Desktop 均不可用（疑似宿主机磁盘压力所致，审查未尝试拉起服务）；已执行的测试均不依赖真实服务（mock/fakeredis），结论不受影响。唯一未能完成的是一次"真 PG 跨循环实验"（见 §5 注）。

---

## 1. 修复验证结论（任务 A）

**EI-01 ~ EI-06 全部确认落地且有效；协调者补修的 audit.py readiness 端点同样通过。代码级核对 + 20 个修复验证测试全绿（12 + 8 passed）。**

| 项 | 代码落地核对（ca86bda8 实测） | 测试结果 |
|----|------|------|
| EI-01 policy 任务跨循环 | `app/tasks/policy_tasks.py:18-28` 已改为协程内 `async with AsyncSessionLocal()` + 显式 `await db.commit()`，并留 NOTE 注释禁止回退旧模式 | `tests/core/test_policy_task_event_loop.py` 2 passed |
| EI-02 community 任务注册 | `app/core/celery_app.py:70-72` include 已含 `app.tasks.community_checkin_reminder`（带注释） | `tests/core/test_celery_beat_registration_guard.py` 2 passed；另有本 R2 独立冷启动模拟：67 beat 条目 → 注册表**零缺失**（见 §3） |
| EI-03 异常链保真 | `app/db/session.py:178-203`：rollback/close 各自 try-except + warning（标注 original exception preserved），`raise` 原样穿透；docstring 记录 EI-01/EI-03 约束 | `tests/core/test_db_session_context.py` 5 passed（含异常同一对象穿透断言） |
| EI-04 event_bus 关停排空 | `app/core/event_bus.py:1027-1034` `begin_shutdown()`；`app/main.py:504`（cancel 之前）→ `main.py:698` `await event_bus.close()` → `main.py:704` `cache_service.close()`，顺序正确 | `tests/core/test_event_bus_lifespan_shutdown.py` 3 passed |
| EI-05 图缓存 str/bytes | `app/services/graph_reasoning_service.py:88-96`：`isinstance(raw_cached, str)` → encode 兼容，HMAC/切片逻辑不变 | `tests/test_migrations.py::test_graph_caching_preserved` passed |
| EI-06 readiness 键 | 11 处键名全部修正（含 5 处报告外同类漂移）；`_current_mode()` 缺键返回 `unknown` 并进 blocking_reasons | `tests/unit/test_kill_switch_readiness.py` 6 passed |
| 协调者补修（新发现①） | `app/api/v1/audit.py:117-125`：`await svc.get_readiness_report(settings)`，写法正确（与 admin_dashboard.py 一致）；import 路径已修正 | `tests/api/test_kill_switch_readiness_endpoint.py` passed |

---

## 2. FastAPI 启动冒烟 — 全量路由表（R2-B1）

冒烟方式：真实 import `app.main`（FastAPI 构建期即解析全部 Depends——import 通过 = 无"handler 引用不存在的依赖"）+ 导出全量路由表（933 条）+ 三类异常扫描。

**总体健康**：import 全绿（仅既有噪音：mimo api_key 空告警、MDX 字典缺 lzo）；**重复注册（同 path+method 多 handler）= 0**；**WS/HTTP 同路径冲突 = 0**；无双前缀/错前缀路径（`/api/internal/*` 2 条为有意的内部 webhook；尾斜杠孪生 3 组 `/goals`、`/health/health`、`/release_approvals` 属装饰性冗余，非缺陷）。

**发现 2 条"字面量路由被同级参数化路由遮蔽"的真缺陷**（用 Starlette 实际编译的 `path_regex` 按注册顺序实证 dispatch 目标）：

| ID | 严重度 | 位置 | 实证行为 | 影响 |
|----|--------|------|----------|------|
| **R2-EI-13** | **P1** | `app/api/v1/notification_center.py:281`（`DELETE /notifications/clear-read`，声明在 `:131` `DELETE /notifications/{notification_id}` 之后） | 实证 dispatch 到 `delete_notification`，`notification_id="clear-read"` → FastAPI UUID 校验 → **必 422**。字面量 handler `clear_read_notifications` **永不可达** | **移动端在活跃调用**（`mobile/lib/features/notification_center/data/repositories/notification_center_repository.dart:309`）——"清空已读通知"功能全链路 100% 失败，OpenAPI 还在向客户端宣传该端点。修法：把字面量路由移到参数化路由之前声明（或改用 `notification_id:path` 之外的显式顺序调整），零风险 |
| **R2-EI-14** | P2 | `app/api/v1/seed_libraries.py:642`（`GET /seed-libraries/my-subscriptions` 兼容别名，声明在 `:215` `GET /seed-libraries/{library_id}` 之后） | 实证 dispatch 到 `get_library` → 422。**Go 网关也暴露了它**（`backend/gateway/internal/handler/proxy_routes.go:404`） | 移动端实际使用的是未遮蔽的 `/seed-libraries/subscriptions/me`（`api_endpoints.dart:598`，双段路径不可被单段参数遮蔽），故无主动调用方受损；但网关宣传的别名恒 422，属对外契约破损。同法重排即可 |

顺带排除：`/api/v1/plans/primary`、`/plans/archived` 同为"参数化在前"，但参数带 `:uuid` 转换器，`primary/archived` 不匹配 uuid 正则而穿透到字面量 handler——**不是缺陷**（实证 dispatch 正确）。此模式值得作为团队约定：**字面量路径一律先于参数化路径声明**。

---

## 3. Celery 冷启动三方匹配（R2-B2）

独立模拟 worker 启动（不经 conftest、按生产 WORKDIR 语义加载 include 全部模块 + 触发 `setup_periodic_tasks`）：

- include 8 模块全部加载成功（`workers.signals_learning_worker` 按路径加载，EI-11 现状）；
- `conf.beat_schedule` **67 条目 → 57 个不同任务 → 注册表零缺失**（EI-01/EI-02 修复后的运行时级确认）；
- 反向：注册表 120 任务中 63 个无 beat 引用（手动投递任务，正常）；
- beat 条目队列选项全部落在已声明队列（default/low_priority），无"投递到不存在队列"。

**F4 守卫测试覆盖面评估（变异测试实证，不修改仓库）**：

| 新增 beat 条目的方式 | 守卫是否拦截 |
|------|------|
| 静态 dict（`celery_app.conf.beat_schedule = {...}`）加未注册任务 | **拦下 ✓**（变异实测 AssertionError） |
| `app/celery_schedule.py::setup_periodic_tasks` 内 `add_periodic_task` | **拦截 ✓**（测试显式调用该函数；且实测 `add_periodic_task` 立即写入 `conf.beat_schedule`） |
| 模块级 `CELERYBEAT_SCHEDULE` 死配置（EI-08 已知形态，如 `login_attempt_cleanup.py`） | **盲区**——但生产 beat 同样不执行它，失败模式是"任务静默不跑"而非"消息被丢"，守卫定位（防消息丢失）本身无漏洞 |

结论：**F4 守卫覆盖当前所有真实生效的 beat 注入路径，新增条目不会漏**。建议（P3）补一条"仓库扫描守卫"：grep 所有模块级 `CELERYBEAT_SCHEDULE`/`beat_schedule =` 赋值，非 `app/core/celery_app.py` 与 `app/celery_schedule.py` 位置即报警，封死死配置返潮的口子。

EI-07/08 现状（复核）：task_routes 无效条目由 6 → **3**（`generate_embedding`/`batch_error_analysis`/`cleanup_old_data`，无功能损失）；同任务多 beat 条目 8 组中 5 组为有意设计（早/晚成对、4 门课、日/周胶囊），**真实双频 3 个**：`apply_memory_decay`、`evaluate_routing_outcomes`、`spine_expire_stale_states`——维持 P3，赛前清理即可。

---

## 4. 消费者毒丸路径（R2-B3）与资源生命周期（R2-B4）

### 4.1 毒丸（callback 抛异常的消息）实际行为 —— 语义健全

逐行走读 `_process_stream_message → _handle_failed_message → _requeue_for_retry/_move_to_dlq`（event_bus.py:1177-951）：

1. callback 异常 → `_handle_failed_message`：`retry_count < 3` → **先重投再 ack**（payload 带 `_retry_count/_original_message_id/_last_error`）；`>= 3` → **DLQ 双写（Redis 流 + DB）成功后才 ack**，写失败留 pending 由 `xautoclaim(5s)` 收尸重试——不会丢消息；
2. 重投消息经幂等键 `_original_message_id` 去重，成功才 `idempotency.set + xack`，语义闭环；
3. 垃圾/不可解析消息走 fallback 后被 callback 拒绝 → 3 次重试后进 DLQ，**无无限循环**。

新发现（小）：`_requeue_for_retry`（event_bus.py:897）计算了指数退避 `delay_ms` 但**只写进日志**——重投消息即刻进入流尾被消费，实际是热重试。因有 `max_retries=3` 上限兜底，不构成风暴，定 **R2-EI-15（P3）**：要么实现延迟投递（延迟 stream/定时 claim），要么删掉日志里的 delay 语义防止误读。

### 4.2 资源生命周期全序列 —— F4 修复自洽，附 3 项卫生发现

lifespan 关停实际顺序（main.py:492-708 逐行核对）：

```
stop_sync_worker → stop_expansion_worker
→ event_bus.begin_shutdown()            # F4①：封死 _restart_consume_loop 复活窗口
→ cancel 25 个 *_consumer_task 句柄      # EI-04 已证多为已完成句柄，cancel 空转无害
→ summarization/billing/listener/streaming stop
→ await event_bus.close()               # F4②：排空 bus 内部真实 _consume_loop + 关 bus 自有 Redis
→ cache_service.close() → manager.close_redis()
```

自洽性确认：`begin_shutdown` 先于一切 cancel（复活回调读 `_running=False` 直接放行）；`close()` 排空的是 `subscribe()` 挂进 `self._consumer_tasks` 的**真实循环**；`event_bus.redis` 是 `connect()` 里自建的独立客户端（event_bus.py:1012），先于 `cache_service.close()` 关闭无共享连接风险。**F4 修复与现有 25 处消费者关停代码完全自洽。**

新发现：

| ID | 严重度 | 位置 | 问题 |
|----|--------|------|------|
| R2-EI-16 | P3 | `app/services/scheduler_service.py:81` + `app/main.py:475/492-708` | **进程内 APScheduler 无 `stop()`、lifespan 关停不排空**：`scheduler_service.start()` 注册了每 1 分钟 tick（`run_execution_schedule_tick`）等 15 个 job，关机序列没有任何一步停它——关停窗口内 job 触发会在已取消消费者的 loop 上打一个正在关闭的 DB 池（概率≈关停耗时/60s，低但真实）。修法：给 SchedulerService 加 `stop()` 并插在 `begin_shutdown()` 前后 |
| R2-EI-17 | P3 | `app/main.py:294` | `capsule_consumer_task` 启动后**不在关停 cancel 清单**（其余 25 个句柄均有对应 cancel）——EI-04 修复后排空职责已由 `event_bus.close()` 承担，故无实际泄漏，纯清单不一致；建议补一行保持完整性 |
| R2-EI-18 | P3（卫生） | `app/main.py:492-708` | 关停无 `engine.dispose()`（db/session.py 连接池随进程退出）、`redis_search_client` 不关闭、EpisodeLogger Redis sink 不摘除——优雅关停卫生项，无功能损坏 |

另记录一个极窄竞态（不另立编号）：`event_bus.close()` 第二遍 `for task in self._consumer_tasks: await task` 期间，任务的 done-callback 会 `remove` 改变同一 list，理论上可跳过个别 `await`（任务已被第一遍全部 cancel，仅可能少吞一次 CancelledError 告警）。P3 以下，仅备注。

---

## 5. 移交专项①：EI-03 深层 —— 13 个 `get_db_context` 调用点逐点诊断（任务 C）

**核心结论：R1 遗留担忧（"accountability 全文件 0 内部 commit、依赖危险的外层跨循环 commit"）实测不成立。13 处全部为 Pattern A（同步任务体 + `asyncio.run(coro(db))`），且每一条真实写路径都由服务层/任务协程在 loop L2 内部自提交——外层 `__exit__` 的跨循环 commit 实际只在"干净会话"上运行（无 DB roundtrip），这正是这些任务在 beat 上长期正常的历史原因。EI-01 型（Pattern B：`with get_db_context()` 写进 async 体）已绝迹。**

| # | 文件:行 | 任务 | 协程内写路径 | 自提交位置 | 运行中循环实际风险 | 优先级 |
|---|--------|------|------------|-----------|-------------------|--------|
| 1 | accountability_tasks.py:249 | send_daily_reminders | NotificationService.create（db.add+commit） | 服务内部（L2） | 低：外层 commit 为空转；异常路径已被 F4 兜底 | 偿还性 P3 |
| 2 | :282 | check_partner_progress | 同上（streak 里程碑通知） | 同上 | 低 | P3 |
| 3 | :315 | evaluate_achievements | 同上 | 同上 | 低 | P3 |
| 4 | :348 | send_milestone_notification | 同上 | 同上 | 低 | P3 |
| 5 | :379 | notify_partner_checkin | 同上 | 同上 | 低 | P3 |
| 6 | community_checkin_reminder.py:102 | send_checkin_reminders | NotificationService.create | 服务内部（L2） | 低 | P3 |
| 7 | guest_cleanup.py:40 | cleanup_expired_guests | `await db.commit()`（:119） | 协程内显式（L2） | 低 | P3 |
| 8 | guest_cleanup.py:69 | cleanup_guest_sessions | 只读 SELECT（占位实现） | — | 极低 | P3 |
| 9 | login_attempt_cleanup.py:35 | cleanup_old_login_attempts | `await db.commit()`（:76） | 协程内显式（L2） | 低 | P3 |
| 10 | update_similarities.py:46 | update_all_user_similarities | `await db.commit()`（:251） | 协程内显式（L2） | 低 | P3 |
| 11 | :75 | update_user_learning_profiles | `await db.commit()`（:311） | 同上 | 低 | P3 |
| 12 | :104 | update_item_similarities | `await db.commit()`（:368） | 同上 | 低 | P3 |
| 13 | :135 | expire_old_recommendation_cache | `await db.commit()`（≈:387） | 同上 | 低 | P3 |

残余风险（改造前的真实边界，供排期判断）：

1. **失败路径的池泄漏**：L2 协程半途抛异常留下未提交事务时，F4 修复保证原异常穿透，但 L3 的 rollback 跨循环 RuntimeError 使回滚**实际未执行**、L4 的 close 同样失败 → 该连接未归还池（进程生命周期内泄漏 1 个）。频率 = 该任务异常率，当前全部为 beat 低频任务，可接受；改造后归零。
2. **未来新增调用点的陷阱**：若新任务把真实写依赖在外层 commit（当前 13 处无一如此），commit 将真正跨循环发 SQL → RuntimeError → 任务永久失败。`session.py` docstring 的 NOTE 已写明禁令，建议改造时顺手把这 13 处统一为协程内 `async with AsyncSessionLocal()` 模式（机械替换，每处 ~5 行），一劳永逸。
3. 注：计划中的"真 PG 跨循环实验"因本机 PG 不可用未执行；上表基于全量静态审计（写路径→服务层 commit 链逐一核对到 `notification_service.py:277-278` 的 `db.add + await db.commit()`）+ R1 生产运行证据（accountability 任务在 beat 上无 EI-01 型 100% 失败签名）+ F4 的 5 个 `test_db_session_context.py` mock 测试（已全绿）三重印证。

### 移交专项②：EI-07 ~ EI-12 复核（是否升级）

| 项 | R2 复核结论 | 建议 |
|----|------------|------|
| EI-07 | 无效 task_routes 6 → **3**（已被清理一半），无功能损失 | 维持 P3 |
| EI-08 | 8 组多条目中真实双频 3 个（apply_memory_decay / evaluate_routing_outcomes / spine_expire_stale_states），其余为有意成对 | 维持 P3，赛前顺手清 |
| EI-09 | 无 SlowAPIMiddleware 现状未变；`@limiter.limit` 现有 23 处（auth.py 12、community.py 10、suggestions.py 1）仍受 XFF 伪造影响 | **维持 P3 但加注**：auth 登录端点的按 IP 限流可被伪造 X-Forwarded-For 绕过，若依赖它防爆破需叠加 DB 侧账号级锁（login_attempt 机制已存在，可声明足够） |
| EI-10 | `health.py`/`errors.py` 死 router 仍未注册（`/errors/*` 实际来自 error_book.py） | 维持 P3（删除或登记退役） |
| EI-11 | `backend/workers/` 与 `app/workers/` 双根依旧；守卫测试的 file-path 回退即其现实代偿 | 维持 P3 |
| **EI-12** | **已修复，建议关闭**：`app/models/accountability.py:118-130` 已把 LEAST/GREATEST 索引移出 `__table_args__`、改为 `execute_if(dialect="postgresql")` 的 after_create DDL；实证 `tests/api/test_accountability_system_api.py` **13 passed 0 error**（R1 时代该夹具必炸） | **关闭** |

---

## 6. R2 新发现汇总表

| ID | 严重度 | file:line | 摘要 | 建议 |
|----|--------|-----------|------|------|
| R2-EI-13 | **P1** | `app/api/v1/notification_center.py:281`（对照 ：131） | `DELETE /notifications/clear-read` 被先前声明的 `DELETE /notifications/{notification_id}` 捕获，恒 422；移动端 `notification_center_repository.dart:309` 活跃调用 → "清空已读"功能全链路死亡 | 字面量路由移至参数化之前（重排声明顺序即可） |
| R2-EI-14 | P2 | `app/api/v1/seed_libraries.py:642`（对照 ：215） | `GET /seed-libraries/my-subscriptions` 同理恒 422；Go 网关 `proxy_routes.go:404` 亦暴露该路径；移动端实际用 `/subscriptions/me`（未受损） | 同法重排；网关侧同步核对 |
| R2-EI-15 | P3 | `app/core/event_bus.py:897` | 消费者重试退避 delay 只进日志未实施，重试为热循环（有 3 次上限，无风暴） | 实现延迟投递或删除误导性 delay 日志 |
| R2-EI-16 | P3 | `app/services/scheduler_service.py:81`、`app/main.py:475` | 进程内 APScheduler（含 1 分钟 tick）无 stop、关停不排空 | SchedulerService 加 `stop()` 并接入 lifespan 关停 |
| R2-EI-17 | P3 | `app/main.py:294` | `capsule_consumer_task` 缺关停 cancel（EI-04 后无实际泄漏） | 补一行保持清单完整 |
| R2-EI-18 | P3 | `app/main.py:492-708` | 关停不 dispose DB 引擎/不关 redis_search_client/不摘 EpisodeLogger sink | 优雅关停卫生批处理 |

团队约定建议（非缺陷）：路由声明遵循"字面量先于参数化"（本次 `/plans/{plan_id:uuid}` 因 uuid 转换器侥幸安全，但该转换器救不了 str 型参数——seed/notification 两例即反例）。

---

## 7. 测试执行记录

环境：worktree 内；`SECRET_KEY=rule-guard-secret-… JWT_SECRET=rule-guard-jwt-… REDIS_URL=redis://:sparkle_dev_redis_2026@localhost:6379/1`；`/opt/homebrew/bin/pytest`。PG/Redis 进程在 R2 后段不可用（环境注记见 §0）；所列测试均不依赖真实服务。

| # | 命令（目标文件） | 结果 |
|---|------|------|
| 1 | `pytest tests/core/test_policy_task_event_loop.py tests/core/test_celery_beat_registration_guard.py tests/core/test_db_session_context.py tests/core/test_event_bus_lifespan_shutdown.py -q` | **12 passed**（5.26s） |
| 2 | `pytest tests/unit/test_kill_switch_readiness.py tests/api/test_kill_switch_readiness_endpoint.py "tests/test_migrations.py::test_graph_caching_preserved" -q` | **8 passed**（0.79s） |
| 3 | `pytest tests/api/test_accountability_system_api.py -q`（EI-12 复核） | **13 passed, 0 errors**（6.53s；R1 时代此夹具 98×error） |

脚本化核查（非 pytest，临时脚本置于 /tmp，未入库）：① 全量路由表导出（933 条）+ 重复/WS 冲突/遮蔽扫描 + Starlette path_regex dispatch 实证；② Celery 冷启动三方匹配（67 条目零缺失）+ task_routes/双频条目盘点；③ F4 守卫变异测试（3 种新增方式）；④ 13 调用点写路径→服务层 commit 链静态审计。

本次审查未修改任何仓库文件；报告为本波唯一新增文档。
