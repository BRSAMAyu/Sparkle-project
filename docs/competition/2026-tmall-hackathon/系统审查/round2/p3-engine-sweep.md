# P3 引擎清扫批 — 修复记录（p3-engine-sweep）

- 修复员：P3 引擎清扫批（wt6，main detached @ `47db4816`，未 commit）
- 任务书：EI-07..EI-11（04-r2-engine-infra.md §5 移交专项② + round1/04-engine-infra.md §剩余清单）、RB-06 follow-up（round1/01-fixes.md + 01-r2-engine-orchestration.md R2-09）、R2-P3-06（02-r2-engine-planning.md §2）
- 方法：红-绿证明（新守卫/行为测试先在冻结代码跑红，修复后跑绿）；pytest 只跑目标文件，单进程
- 环境：`SECRET_KEY/JWT_SECRET/REDIS_URL` 按规注入，`/opt/homebrew/bin/python3.11 -m pytest`；PG/Redis 栈健康未重启

## 条目对应关系（任务书编号 → 报告实际位置）

| 任务书编号 | 报告实际条目 | 处置 |
|---|---|---|
| EI-07 | round1/04-engine-infra.md 剩余清单 + 04-r2 §3/§5（task_routes 无效条目 6→3） | ✅ 本波修复 |
| EI-08 | round1/04 同上 + 04-r2 §3（真实双频 3~4 个 + 死配置 + 扫描守卫建议） | ✅ 本波修复 |
| EI-09 | round1/04 + 04-r2 §5"维持 P3 但加注"（XFF 伪造绕过） | ✅ 本波修复（可信代理解析 + 加注） |
| EI-10 | round1/04 + 04-r2 §5（health.py/errors.py 死 router） | ✅ 本波修复 |
| EI-11 | round1/04 + 04-r2 §5（backend/workers 与 app/workers 双根） | ✅ 本波修复 |
| EI-12 | 04-r2 §5"已修复，建议关闭" | 按报告结论关闭，不动 |
| RB-06 | round1/01-fixes.md RB-06(follow-up)："全仓审计其余中途 commit() 共享 session 的点"；R2-09 给出 context_builder 坐标 | ✅ 审计 + 修 2 点 |
| R2-P3-06 | 02-r2-engine-planning.md §2（P2-2 副作用：零变更轮无节流） | ✅ 本波修复 |

---

## EI-07：task_routes 无效条目（3 条）

**问题**：`celery_app.conf.task_routes` 中 3 条键带 `app.core.celery_tasks.` 模块前缀，但任务实际注册名是短名（`@celery_app.task(name="generate_embedding")` 等）。Celery 路由按任务名精确匹配（无通配符），键永不命中 → 路由静默失效，任务落 default 队列：`generate_embedding`（应 high_priority）、`batch_error_analysis`、`cleanup_old_data`（应 low_priority）。运行时冷启动探针实证：include 全量导入后注册表 120 任务，36 条路由键中 3 条无效（与 R2 报告一致）。

**修复**：`backend/app/core/celery_app.py` — 3 条键改为真实短名，路由意图（high_priority/default/low_priority）保持不变。

**红绿**：新守卫 `tests/core/test_celery_route_beat_hygiene.py::test_every_task_route_key_is_a_registered_task_name`（模拟 worker 冷启动导入 include 全部模块后断言路由键 ⊆ 注册表）。
红（冻结代码）：**FAILED**，报出 3 条无效键；绿（修复后）：**passed**。

## EI-08：beat 双频条目 + 模块级死配置 + 仓库扫描守卫

**问题**：
1. **双源双频**：`app/celery_schedule.py::setup_periodic_tasks`（add_periodic_task）与 `app/core/celery_app.conf.beat_schedule`（static dict）对同一任务注册两份计划，side-effect 型任务双跑、浪费配额。运行时实证 4 组（比 R2 报告多 1 组）：`evaluate_routing_outcomes`（1800s+args × 3600s）、`spine_expire_stale_states`（*/6h@:30+args=500 × 21600s）、`spine_auto_deprecate_skills`（04:00+args=500 × 86400s，R1 曾点名、R2 计数遗漏）、`apply_memory_decay`（03:30+args=200 × 86400s）。
2. **模块级死配置**：模块级 `CELERYBEAT_SCHEDULE` 从未被生产 beat 读取（生产只读 celery_app.py 的 static dict + celery_schedule.py 的 add_periodic_task）。实证 4 个文件：`tasks/login_attempt_cleanup.py`（任务名还写错为 `tasks.login_attempt_cleanup.*`，真实名 `tasks.cleanup_old_login_attempts`）、`tasks/accountability_tasks.py`（与活计划完全重复）、`tasks/guest_cleanup.py`、`tasks/update_similarities.py`——后两者任务甚至未在 include 列表。守卫红跑时全部抓出（R2 §3 建议的"仓库扫描守卫"落地）。

**修复**：
- `app/celery_schedule.py`：删除 4 条与 static 计划重复的 interval 条目（保留带 crontab + args 的确定性条目），留注释指明权威接线位置；
- `app/tasks/{login_attempt_cleanup,accountability_tasks,guest_cleanup,update_similarities}.py`：删除模块级 `CELERYBEAT_SCHEDULE` 死配置及残余 `crontab` 导入；
- 守卫新增 2 条：`test_beat_entries_have_no_accidental_duplicate_frequency`（多 beat 条目仅允许"有意多频"白名单：日/周胶囊、4 门课错峰、早/晚成对×2，即 R2 §3 判定的 5 组有意设计）、`test_no_module_level_beat_config_outside_authoritative_sources`（全仓扫描，死配置只允许出现在两个权威位置）。

**红绿**：红（冻结代码）：双频断言 **FAILED**（报出 4 组）、死配置扫描 **FAILED**（报出 4 文件）；绿（修复后）：`test_celery_route_beat_hygiene.py` **3 passed**。既有 F4 守卫 `test_celery_beat_registration_guard.py` 回归 **2 passed**（beat→注册表匹配不回退）。

## EI-09：get_real_ip 按可信代理数解析（XFF 伪造绕过）

**问题**：`app/core/rate_limiting.py::get_real_ip` 无条件信任 `X-Forwarded-For` 首段，客户端可伪造该头绕过按 IP 限流（auth 登录端点爆破防护；代码有 SECURITY NOTE 但无实现）。R2 复核加注：若依赖它防爆破需叠加 DB 侧账号级锁（login_attempt 机制已在）。

**修复**（R1 建议的"从可信代理数推算真实 client IP"）：
- 新增 `_trusted_proxy_count()`：读 `TRUSTED_PROXY_COUNT` 环境变量（默认 **1**，匹配本仓部署拓扑——Go 网关 `httputil.ReverseProxy` 会把真实 client IP 追加到 XFF 尾部，故取**右起第 N 段**；N=0 完全不信任该头；链条短于 N 说明有代理未追加、右段可能是客户端注入，退回 TCP 对端地址——宁退化为共享桶不可被伪造）；
- `get_real_ip` 重写为右起 N 位解析；路径隔离 key 语义不变；
- docstring 落 R2 要求的两条加注：`default_limits` 未挂 SlowAPIMiddleware 不生效（仅 `@limiter.limit` 的 23 处生效）；登录爆破防护以 DB 侧 login_attempt 账号级锁为准。

**红绿**：新守卫 `tests/core/test_rate_limit_real_ip.py`（6 用例：伪造首段被弃、右起 1 段可信、链短于 N 回退对端、X-Real-IP 仅代理后可信、无头用对端、非法 env 回退 0）。
红：**ImportError**（`_trusted_proxy_count` 不存在，收集期失败）；绿：**6 passed**。`tests/security/test_security.py` 回归 35 passed。

## EI-10：health.py / errors.py 死 router

**问题**：`app/api/v1/health.py` 的 router 从未被 include（DB 健康实现被 health_production.py 顶替，main.py 只借用 `set_start_time`）；`app/api/v1/errors.py` 同样从未 include（`/errors` 的真实实现是 error_book.py，prefix="/errors"）。死 router 的端点列表误导维护者并向客户端宣传不存在的契约。AST 全量扫描（101 个定义模块级 router 的文件 − router.py 导入）确认仅 `health`/`errors` 真死（`_experience` 经 experience 包 `__init__` 间接注册、`router` 为聚合器自身，均活）。

**修复**：
- `set_start_time` 迁入 `app/api/v1/health_production.py`（复用其 `START_TIME` 全局，启动时间戳与真实健康端点共用同一来源）；`app/main.py:29` 改从 `health_production` 导入；
- 删除 `app/api/v1/health.py`、`app/api/v1/errors.py`，连带删除仅被 errors.py 引用的死 schema `app/schemas/error.py`（全仓零引用实证）；
- 守卫 `tests/api/test_no_unregistered_routers.py`：①死文件已删断言；②set_start_time 归属与 main 导入断言；③**全仓扫描守卫**——v1 包内定义模块级 router 的文件必须被 router.py 导入或进白名单（白名单仅 `router`/`_experience`，均注明理由），防死 router 返潮。

**红绿**：红（冻结代码）：**3 FAILED**（死文件存在、set_start_time 在 health.py、未注册扫描报 health/errors）；绿：**3 passed**。`tests/contract/test_api_health_contract.py` + `test_api_router_openapi_contract.py` + kill-switch readiness 4 文件回归 **14 passed**（`/health/*`、`/errors` 契约不回退）。

## EI-11：backend/workers 顶层包并入 app/workers/

**问题**：`backend/workers/signals_learning_worker.py`（436 行，无 `__init__.py` 的命名空间包）与 `app/workers/` 平行，靠 Docker WORKDIR=/app 同时可导入两根；pytest 进程内 conftest 把 `backend/app` 插入 sys.path 前排，顶层 `import workers` 解析到 `app.workers`——守卫测试的 file-path 回退即其现实代偿。

**修复**：`git mv backend/workers/signals_learning_worker.py backend/app/workers/`，删除顶层 `workers/` 目录；`celery_app.conf.include` 改 `"app.workers.signals_learning_worker"` 全路径（附 EI-11 注释）；文件内 docstring 的示例命令同步改；`tests/core/test_celery_beat_registration_guard.py` 的过时"已知债务"注释更新（file-path 回退保留作安全网）。

**红绿**：新守卫 `tests/core/test_workers_package_location.py`（3 用例：顶层包已删、文件在 app/workers、include 用全路径）。
红：**3 FAILED**；绿：**3 passed**。EI-02 守卫回归通过（include 模块全量导入 + beat 零缺失语义不变）。

## RB-06 follow-up：中途 commit 共享会话 — 全仓审计 + 修 2 点

**审计范围与结论**（orchestration/ 全量 `.commit()` 逐点核对会话所有权；流路径 = `agent_grpc_service.StreamChat` 的 `db_session`，提交所有权在 :354-399——stream 结束统一 commit、异常 rollback）：

| # | 位置 | 会话 | 判定 | 处置 |
|---|---|---|---|---|
| 1 | `context_builder.py:1506`（`_build_full_context` 持久化用户消息） | **gRPC 流共享 `active_db`** | 同族损坏：中途 commit 破坏"一轮一事务"原子性，用户消息已提交而后续失败时外层 rollback 无法回滚（R2-09 坐标） | ✅ 抽取为 `_persist_user_message` 并改 `flush` |
| 2 | `persistence_layer.py:43`（`_persist_assistant_message` 持久化助手消息） | **gRPC 流共享 `active_db`**（orchestrator/execution_engine 5 处调用） | 同族损坏（审计新增，报告外） | ✅ 改 `flush`（PK 由 flush 分配，写 lane 的 `assistant_message_id` 语义不变） |
| 3 | `session_state_mixin.py`（R1 RB-06 原修点） | 流共享 | R1 已修（flush），本轮复核维持 | 无需动 |
| 4 | `adaptive_replanner.py:873`（`_write_compressed_sprint_day`，`self.db`） | 调用方为 task_event_consumer（每事件独立会话）/ api 请求级会话 | 非 gRPC 流共享会话；消费者/端点各自拥有事务边界 | 不动（审计留档） |
| 5 | `planning_workflow.py:1244/1380/1412`（db 为参数传入） | 规划/修复链调用方自有会话 | 非 gRPC 流共享会话 | 不动（审计留档） |
| 6 | `executor.py:587/615` | 587 独立 `history_session`；615 已是 flush + `_commit_if_owned` | 正确 | 无需动 |

**红绿**：新测试 `tests/core/test_rb06_followup_no_midstream_commit.py`（3 用例，假 session 记录调用序列）：用户消息 flush 不 commit、flush 失败回滚、助手消息 flush 后写 lane 仍触发。
红（冻结代码）：**3 FAILED**（`'commit' in ['add','commit']`，`_persist_user_message` 尚不存在）；绿：**3 passed**。

## R2-P3-06：零变更轮节流 + feedback_log 窗口上限

**问题**：P2-2 修复副作用——零任务级变更轮不武装 `last_adjustment_at` → 2h 调整冷却对"参数写了但没落地"的轮次永久失效（唯一闸门 `adaptive_replanner.py:1729`）；每个新健康信号都重写 plan_state（bump_version + feedback_log 追加 + snapshots 追加）并向用户 enqueue 一条"本轮没有任务级调整"，无节流。

**修复**（报告建议第一选项）：
1. `adaptive_replanner.py`：新增 `AUTO_NOOP_ADJUSTMENT_THROTTLE = timedelta(minutes=30)`；零变更分支（applier 无 affected/inserted/hidden ids）fresh-read 深合并写轻量 `adaptive_meta.last_noop_adjustment_at`（`bump_version=False`，不动 `last_adjustment_at`——P2-2"落地才武装冷却"语义保持，既有测试 `test_noop_patch_does_not_arm_adjustment_cooldown` 继续绿）；
2. `_handle_report` adjust 分支新增闸门：noop 窗口内跳过整轮重评估（不写参数、不追加 feedback_log、不打扰用户），`action_taken="noop_adjustment_throttled"`；**`task_feedback_struggle` 豁免**（用户挣扎必须被响应，与 replan 冷却旁路同一哲学）；
3. `plan_state_service.py`：新增 `FEEDBACK_LOG_WINDOW_LIMIT = 200`，`upsert_plan_state` 追加 feedback_log 后钳制保留最近 200 条（对齐 recent_adaptations ≤10 / snapshots ≤3 的既有窗口惯例）。

**红绿**：新测试 `tests/unit/test_r2p306_noop_throttle.py`（5 用例：零变更轮写节流戳且不写 last_adjustment_at、窗口内重复信号整轮跳过、struggle 豁免、窗口过期恢复、feedback_log 钳制到 200 且保最新）。
红（冻结代码）：**ImportError**（`FEEDBACK_LOG_WINDOW_LIMIT` 不存在）+ 行为红（冻结 `_handle_report` 对窗口内重复信号照常进 applier）；绿：**5 passed**。

---

## 测试执行记录（单进程，逐批单命令）

| # | 批次 | 结果 |
|---|---|---|
| 1 | `tests/core/test_celery_route_beat_hygiene.py`（冻结基线） | **3 failed**（红） |
| 2 | 同上（修复后） | **3 passed** |
| 3 | `tests/core/test_rate_limit_real_ip.py` | 红=ImportError → **6 passed** |
| 4 | `tests/api/test_no_unregistered_routers.py`（冻结基线） | **3 failed**（红）→ 修复后 **3 passed** |
| 5 | `tests/core/test_workers_package_location.py` + 旧守卫 `test_celery_beat_registration_guard.py` | 红=3 failed → **5 passed** |
| 6 | `tests/core/test_rb06_followup_no_midstream_commit.py` | **3 failed**（红）→ **3 passed** |
| 7 | `tests/unit/test_r2p306_noop_throttle.py` | 红=ImportError+行为红 → **5 passed** |
| 8 | 回归：`test_context_builder_mixin.py` + `test_adaptive_replanner_stage34.py` + `test_plan_state_service_jsonb.py` | 16 passed / 2 failed——**2 failed 经 git stash 实证为冻结基线固有**（memory mock 缺 awaitable，与本波无关） |
| 9 | 回归：health/openapi 契约 + kill-switch readiness 4 文件 | **14 passed** |
| 10 | 回归：`test_feedback_adjustment_delete_task.py` + `test_plan_adjustment_applier.py` | **37 passed** |
| 11 | 回归：`test_plan_state_jsonb_pg.py` + `test_policy_task_event_loop.py` + `test_event_bus_lifespan_shutdown.py` | **5 passed, 3 skipped**（skip 为真 PG 腿环境开关未开，属 G2 用例非本波范围） |
| 12 | 回归：orchestrator wiring 3 文件 | 37 passed / 1 failed——**经 stash 实证为冻结基线固有**（behavior_signal_collector 的 mock 缺 `scalars`） |
| 13 | 回归：`tests/security/test_security.py` | **35 passed** |

**新增测试 25 个用例（6 文件）全绿；红绿证明齐备；无新增基线失败。**

## 改动文件清单（24 文件，+751/−399）

**代码（14）**：`backend/app/core/celery_app.py`、`backend/app/celery_schedule.py`、`backend/app/tasks/{login_attempt_cleanup,accountability_tasks,guest_cleanup,update_similarities}.py`、`backend/app/core/rate_limiting.py`、`backend/app/main.py`、`backend/app/api/v1/health_production.py`、`backend/app/orchestration/{context_builder,persistence_layer,adaptive_replanner}.py`、`backend/app/services/plan_state_service.py`、`backend/app/workers/signals_learning_worker.py`（自 `backend/workers/` 移入）＋删除 `backend/app/api/v1/health.py`、`backend/app/api/v1/errors.py`、`backend/app/schemas/error.py`、`backend/workers/`（空目录移除）

**测试（6 新 + 1 改）**：`backend/tests/core/{test_celery_route_beat_hygiene,test_rate_limit_real_ip,test_rb06_followup_no_midstream_commit,test_workers_package_location}.py`、`backend/tests/api/test_no_unregistered_routers.py`、`backend/tests/unit/test_r2p306_noop_throttle.py`、`backend/tests/core/test_celery_beat_registration_guard.py`（注释更新）

## 遗留风险与移交

1. **TRUSTED_PROXY_COUNT 默认 1 的前提**：引擎必须部署在会追加 XFF 的可信代理之后（本仓 Go 网关满足；websocket_proxy 仅透传不追加，但 WS 不经 FastAPI limiter）。若拓扑变更（多级 CDN 等）需同步 env；直连暴露时置 0。
2. **限流覆盖面本身未扩大**：`default_limits` 仍未挂 SlowAPIMiddleware（按 R2 结论"维持 P3 + 加注"处理，未引入全局限流的行为变更）；按 IP 限流只是纵深一层，爆破防护以 login_attempt 账号级锁为准。
3. **`_experience.py` / experience 包并存**：活代码（经包 `__init__` 间接注册），非本波处置对象；命名易误导，建议后续波正名。
4. **RB-06 审计第 4/5 类**（consumer/request 级会话的服务内 commit）是本仓请求路径的主导约定，未改；若未来统一"服务层只 flush"，再立项。
5. **noop 节流 30min 的取舍**：零变更后的真实参数调整最多延迟 30min（struggle 旁路不受限）；如产品侧需要更快响应，可调常量或改信号服务层按 signature 聚合。
6. **基线固有失败 3 个**（context_builder mixin 2 + c03 wiring 1）经 stash 实证与本波无关，建议单独立项（mock 缺 awaitable/scalars）。
