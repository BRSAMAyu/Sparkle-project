# 全系统审查·第一轮修复 — 04 引擎·基础设施层

- 修复员：4 号（engine-infra 切片）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt4`（基线 `90daac8a`，未 commit）
- 对应审查报告：[04-engine-infra.md](./04-engine-infra.md)
- patch：[04-fixes.patch](./04-fixes.patch)
- 结论：**EI-01 ~ EI-06 全部修复**，每项均有红-绿证明。EI-07 ~ EI-12（P3）与两项新发现列入"剩余清单/新发现"，未扩修。

---

## 修复明细

### EI-01（P1）policy 任务跨事件循环 100% 失败

- 修复：`backend/app/tasks/policy_tasks.py:18-31` — 删除「`with get_db_context()` 写在 async 函数体内」的用法（其 `__exit__` 的 `asyncio.run()` 在 `_run_async` 持久循环上必抛 RuntimeError），改为与 `app/core/celery_tasks.py` 一致的模式：`async with AsyncSessionLocal()` 会话生命周期完整位于协程内，`_run_async` 一次性驱动，服务调用后显式 `await db.commit()`（`PolicySchedulerService.process_due_policies` 自身不 commit）。
- 测试：`backend/tests/core/test_policy_task_event_loop.py`
  - `test_process_due_policies_completes_without_loop_error`
  - `test_process_due_policies_survives_repeated_invocations`（模拟 beat 每 30s 连续调度）
- 红：修复前 `RuntimeError: asyncio.run() cannot be called from a running event loop`（`app/db/session.py:178` → `contextlib.__exit__`，traceback 与报告描述完全一致），2 failed。
- 绿：2 passed。

### EI-02（P1）`tasks.community.send_checkin_reminders` 未注册，beat 投递被静默丢弃

- 修复：`backend/app/core/celery_app.py:70-72` — `include` 增补 `"app.tasks.community_checkin_reminder"`（附注释说明原因）。
- 测试：`backend/tests/core/test_celery_beat_registration_guard.py`
  - `test_every_beat_scheduled_task_is_registered_in_worker` — 兜底守卫：导入 `conf.include` 全部模块 + 触发 `setup_periodic_tasks` 模拟 worker 启动，断言 beat_schedule 的 67 个条目引用的任务名全部在注册表中；
  - `test_community_checkin_reminders_task_is_registered` — EI-02 回归锚点。
- 红：`beat 调度引用了未注册任务…{'tasks.community.send_checkin_reminders': ['community-checkin-reminders-morning', 'community-checkin-reminders-evening']}`，2 failed。
- 绿：2 passed。脚本预审（修复前）确认 67 个 beat 条目中**唯一**缺失任务即该任务，与报告一致。
- 注：守卫测试内对 `workers.signals_learning_worker` 按文件路径显式加载 —— pytest 进程中 conftest 把 `backend/app` 插到 sys.path 前排，顶层名 `workers` 会被 `app.workers` 抢占（EI-11 双根歧义的现实再现）；生产 worker（WORKDIR=/app）不受影响。

### EI-03（P2）`get_db_context` 异常路径掩盖原始异常

- 修复：`backend/app/db/session.py:160-203` — `__exit__` 的 rollback / close 各自包 try-except：失败仅 `logger.warning`（标注 original exception preserved），原样 `raise` 内层异常；close 失败在成功路径上也不再使任务失败（事务已终结）。docstring 记录 EI-01 的"禁止在 with 体内嵌套事件循环"约束。文件级 `import asyncio`、新增模块 `logger`。
- 测试：`backend/tests/core/test_db_session_context.py`（5 个）
  - `test_original_exception_preserved_when_rollback_also_fails`（断言异常**同一对象**穿透）
  - `test_original_exception_preserved_when_close_also_fails`
  - `test_commit_failure_triggers_rollback_and_raises_commit_error`
  - `test_close_failure_on_success_path_does_not_mask_result`
  - `test_success_path_commits_and_closes`
- 红：前 3 项 failed —— rollback/close 的 `RuntimeError("attached to a different loop")` / `RuntimeError("loop is closed")` 替换了原始 `ValueError("inner boom")`。
- 绿：5 passed。

### EI-04（P2）event_bus 消费循环游离于 lifespan，`close()` 从未被调用

- 修复：
  - `backend/app/core/event_bus.py:1027-1036` — 新增 `begin_shutdown()`：置 `_running = False`，阻止关机窗口内 `_restart_consume_loop` 复活死亡循环；
  - `backend/app/main.py`（lifespan 关停段，消费任务 cancel 之前 / `cache_service.close()` 之前）— 先 `event_bus.begin_shutdown()`，末尾 `await event_bus.close()` 排空 bus 内部任务（try/except + warning 兜底，不阻断其余关停步骤）。
- 测试：`backend/tests/core/test_event_bus_lifespan_shutdown.py`（3 个）
  - `test_begin_shutdown_prevents_consume_loop_restart`（先证明运行期会复活——现状 F3 行为保留，再证明 begin_shutdown 后不复活）
  - `test_main_lifespan_shuts_down_event_bus`（源码守卫：begin_shutdown → close → cache_service.close 顺序）
  - `test_close_after_begin_shutdown_is_idempotent_enough`
- 红：`AttributeError: 'EventBus' object has no attribute 'begin_shutdown'` ×2 + 守卫 `substring not found`，3 failed。
- 绿：3 passed；既有 `tests/test_event_bus_shutdown.py` 同跑通过（4 passed）。

### EI-05（P2）图缓存读路径 `str.decode` 必 AttributeError，缓存永不命中

- 修复：`backend/app/services/graph_reasoning_service.py:88-100` — 读缓存后 `isinstance(raw_cached, str)` 时 `encode("utf-8")` 兼容 `decode_responses=True` 的 redis client（`app/core/cache.py:42`），签名/JSON 切片逻辑不变。
- 测试：`backend/tests/test_migrations.py::test_graph_caching_preserved` — 原测试喂 pickle 旧格式（报告定性：测试过期但顺带暴露 EI-05）。按生产真实格式重写第二段：服务自身 HMAC helper 构造 `sig + json_payload`，以 **str** 回读，断言命中缓存、UUID relabel 回 UUID、不回源 DB（`mock_db.execute.assert_not_called`）、不重复写缓存。
- 红：修复前 `StopAsyncIteration`（`str.decode("ascii")` AttributeError 被吞 → 回源 DB → mock side_effect 耗尽），与报告"稳定复现"一致。
- 绿：`test_graph_caching_preserved` + `test_graph_cache_invalidation_preserved` + `tests/test_graph_reasoning.py` 共 5 passed。

### EI-06（P2）readiness 报告引用不存在的 settings 键且静默回退

- 修复：`backend/app/services/kill_switch_readiness_service.py`
  - 键名修正 **11 处**（报告列 6 处；对照各 `*_kill_switch_service.py` 的 `settings_attr` 事实来源，另有 5 处同类漂移一并修正）：stage19→`AURORA_STAGE19_WORKING_MEMORY_MODE`、stage21→`AURORA_STAGE21_SKILL_STORE_MODE`、stage24→`AURORA_POLICY_COMPILER_MODE`（注：报告建议的 `AURORA_STAGE24_POLICY_COMPILER_MODE` 同样不存在，正确键以 kill-switch service 为准）、stage25→`AURORA_REFLECTION_WIRE_MODE`、stage26→`AURORA_SCENE_MODE`、stage27→`AURORA_FORESIGHT_MODE`、stage28→`AURORA_TRAITS_MODE`、stage29→`AURORA_SRL_MODE`、stage30→`AURORA_METACOG_MODE`、stage31→`AURORA_IDIOGRAPHIC_MODE`、stage33→`AURORA_STAGE33_MODE`。全部在 `app/config/settings.py` 验证存在。
  - `_current_mode()`（:240-251）：`getattr(..., None)`，缺键返回 `"unknown"`（并在 `_blocking_reasons` 中暴露、阻塞升级判定），不再静默回退到 catalog 预期值；`FeatureReadiness.current_mode` 注释补 `"unknown"` 态。
- 测试：`backend/tests/unit/test_kill_switch_readiness.py` 追加 3 个
  - `test_catalog_settings_keys_all_exist_in_settings_model`（守卫：目录键 ⊆ Settings.model_fields）
  - `test_full_catalog_against_settings_defaults_resolves_every_mode`（全默认值下无 unknown）
  - `test_missing_settings_key_reports_unknown_not_silent_live`（缺键 → unknown + blocking reason，而非假 live）
- 红：`git stash` 还原服务文件后跑：`test_catalog_settings_keys_all_exist_in_settings_model`、`test_missing_settings_key_reports_unknown_not_silent_live` 2 failed。
- 绿：恢复修复后 6 passed（含原有 3 个测试无回归）。

---

## 回归验证

命令（worktree 内；`source` 主 checkout `backend/.env` 仅注入运行时环境，未改仓库文件；`REDIS_URL=redis://:change-me@localhost:6379/1`）：

```
pytest tests/test_migrations.py tests/test_event_bus_shutdown.py tests/test_preference_consumer_safety.py tests/api tests/core tests/unit/test_kill_switch_readiness.py -q
```

| 指标 | 修复前（报告基线） | 修复后 |
|------|------|------|
| failed | 1（test_graph_caching_preserved） | **0** |
| passed | 96 | 115（含新增 15 个测试） |
| skipped | 4 | 4 |
| errors | 134（98×SQLite `Least` 夹具 + 36×缺 AutoTokenizer 权重） | 134（**同两类环境性错误，逐类核对无新增**） |

冒烟：`app.main` 及 13 个改动关联模块 `importlib` 全绿；`tasks.community.send_checkin_reminders` 已进注册表。

代码风格：新增 4 个测试文件 black(120) 全部 clean；ruff 对全部触碰文件无新增告警（`tests/test_migrations.py` 的 I001 为基线已有）。部分存量文件（main.py / celery_app.py / event_bus.py 等）基线即不符 black，为避免噪音 diff 未做全文件重排。

---

## 剩余清单（未修，属 P3 或超出本波切片授权）

- **EI-07**：`celery_app.py` task_routes 6 条指向不存在任务名（无功能损失）。
- **EI-08**：celery_app / celery_schedule 双份 beat 计划（4 个任务双频执行）；`login_attempt_cleanup.py` 死配置。
- **EI-09**：`default_limits` 未挂 SlowAPIMiddleware；`get_real_ip` 无条件信任 XFF。
- **EI-10**：`api/v1/health.py`、`api/v1/errors.py` 死 router。
- **EI-11**：顶层 `workers/` 包与 `app/workers/` 平行（守卫测试中已实测其歧义性，见 EI-02 注）。
- **EI-12**：SQLite 夹具缺 `Least/Greatest` 编译规则（134 errors 的 98 个）。
- **EI-03 深层项**：`get_db_context` 各阶段仍在独立短命 loop 上驱动（本波保留既有语义、只修异常链）；根治需按报告建议改造 `accountability_tasks.py` 等 6 个任务文件（13 个调用点）为协程内自管会话模式。

## 新发现（记录不扩修）

1. **`app/api/v1/audit.py:117` readiness 端点必炸**：`report = svc.get_readiness_report()` 少传 `settings` 参数且未 `await`（服务签名为 `async def get_readiness_report(self, settings)`）→ 该管理员端点一调用就 TypeError。EI-06 修复后报告数据已可信，但此入口仍打不通；`admin_dashboard.py:222` 的调用是正确写法可参照。属 api/ 切片，留待对应修复员。
2. **审查报告勘误**：EI-06 报告建议的 `AURORA_STAGE24_POLICY_COMPILER_MODE`、`AURORA_STAGE25_REFLECTION_WIRE_MODE`、`AURORA_STAGE19_WORKING_MEMORY_MODE` 中，前者实际不存在（正确为 `AURORA_POLICY_COMPILER_MODE`）；且同类漂移实际共 11 处而非 6 处（见上）。
3. **pytest 进程的 `workers` 名字歧义**：tests/conftest.py 将 `backend/app` 插入 sys.path 前排后，顶层 `import workers` 解析到 `app.workers` 而非 `backend/workers`（EI-11 的衍生陷阱，任何在测试进程 import celery include 的测试都会踩到）。
