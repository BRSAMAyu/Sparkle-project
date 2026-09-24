# wt310-ff-convergence 回执报告（FF 收敛批：backend fire-and-forget → 可追踪 spawn）

> 2026-09-24 ｜ 工作树 wt310-ff-convergence ｜ 交付 = 本 REPORT + changes.patch + 分支本地 commit（未 push）
> 依据：wt299-p1-pair 报告第 ⑤-2 条执行建议（spawn_tracked helper 方案）+ wt294 报告第三节 P1-3 点位清单。

## 0. SHA

- base：`73566bb0`（开工时 main）
- 代码交付 commit：`a293f4f4`（feat(backend): FF 收敛批）
- 分支 final：`d10d3c16`（+ docs 回执 commit；changes.patch = main...HEAD 除 patch 自身）

## 1. Helper 语义（`backend/app/core/background_tasks.py`，新增 116 行）

- `spawn_tracked(coro, *, name=None, on_error=None, registry=None) -> Task`：
  - **强引用**：任务进模块级 `_TRACKED_TASKS` 集合，消除 asyncio 弱引用导致的飞行中 GC 静默回收（P1-C 形态共享化；参考实现 `task_feedback_service.spawn_followup_task` 保持不动，测试 monkeypatch 挂点不受影响）；
  - **异常可见**：done-callback 先 `task.exception()` 取回再 discard——异常必达日志（loguru，带协程 qualname + 任务名），不再走 "Task exception was never retrieved" 静默面；`on_error` 可覆盖；
  - **cancelled 不算失败**：取消路径不触发 on_error；
  - `name` 缺省取协程 qualname；`registry` 可传所有者自备集合。
- `register_tracked_task(task, *, registry, on_error)`：给已创建任务补追踪（`orchestrator._track_task` 的委托面）。
- `tracked_task_count()`：泄漏可见性探针（测试/运维）。
- `shutdown_tracked_tasks(*, timeout=5.0)`：**drain-then-cancel**——pending 任务先给 timeout 秒自然收尾，残留者 cancel 并等待；返回进入时 pending 数。cancelled 路径不触发异常日志。

## 2. 与优雅关停链衔接

`main.py` lifespan 关停段：在 EI-04 `event_bus.close()` **之前**、Redis/DB 释放之前插入 `await background_tasks.shutdown_tracked_tasks()`——短尾 FF 任务（审计写、信号采集、after-commit 发布）先自然收尾，不撞已关闭客户端、不被静默丢弃。此前 wt295 修好的关停链不覆盖任何 FF 任务（不在追踪清单）。

## 3. 点位全清单（迁移 9 点位 + 1 委托改造；行号漂移已按现状对齐）

| wt294/wt299 挂账 | 现状位置 | 处理 | 说明 |
|---|---|---|---|
| core/auth_audit_service.py:62 | L64 | ✅ spawn_tracked | 审计写（最高优先级） |
| aurora/privacy.py:119 | L122 | ✅ spawn_tracked | 隐私模式刷新（最高优先级）；`loop` 变量改 `asyncio.get_running_loop()` 探测 |
| services/job_service.py:84 | L86 | ✅ spawn_tracked | job 执行体；GF 回收曾致卡 RUNNING 至 timeout（wt294 P1-5 面） |
| services/community_service.py:80 | L85 | ✅ spawn_tracked | 社区信号采集 |
| workers/graph_sync_worker.py:61 | L70 | ✅ spawn_tracked + 持引用 | **顺带修 wt294 P1-4**：`start()` 持 `self._consume_task`，`stop()` cancel+await（原 stop 只翻 flag，`_consume` 卡在 xreadgroup 5s 上） |
| workers/graph_sync_worker.py:281 | L297 | ✅ spawn_tracked | start_sync_worker |
| services/tool_history_service.py:68 | L71 | ✅ spawn_tracked | after-commit 事件发布 |
| services/achievement_engine.py:84 | L79 | ✅ spawn_tracked | 有异常回调缺强引用→两者齐备；原 `_make_after_commit_error_handler` 删除（语义并入 helper） |
| core/llm_monitoring.py:185 | L189 | ✅ spawn_tracked | ACTIVE_TASKS 递减必达（见 §4 实锤修复） |
| wt299：orchestrator._track_task | L1650 | ✅ 委托 register_tracked_task | registry 传实例 `_bg_tasks`，`shutdown()` cancel/drain 语义不变，异常日志升级（协程 qualname+任务名） |

**漂移复核**：wt294 行号整体 +4~+6（后续合入所致），点位本体全部健在；`task_feedback_service.spawn_followup_task` 本体未动（P1-C 参考实现 + 2 个测试文件 monkeypatch 其符号）。

**现状 grep 新发现、不在 wt294 清单、本卡未动（建议下一张机械卡用同一 helper 清理）**：`api/v1/assets.py` ×5（_refresh_asset_review_signals）、`api/v1/community.py:3125`（_refresh_streak_signals）、`api/v1/error_book.py:105`（OCR 回写）、`services/expansion_service.py:667`、`services/agent_grpc_service.py:1100`、`services/analytics/cognitive_stream_worker.py:56`、`aurora/core_session.py:752`、`services/predictive_service.py:2018`（wt294 P1-6，维持原建议另卡）、`routing/route_cache.py:74`（wt294 P2 豁免，TTL 自愈）。持引用/有 owner 的（main.py 消费者群、security_monitor、event_bus、task_manager、learning/*）不需迁移。

## 4. 顺带实锤修复（计划外）

`app/core/llm_monitoring.py` **模块级从未 import asyncio**：旧代码在 `wrapper.finally` 内局部 `import asyncio` 后 `create_task(_decrement_active_tasks())`，但 `_decrement_active_tasks` 协程体内的 `await asyncio.sleep(0.001)` 引用的是模块命名空间 → **每次装饰器调用递减任务必然 NameError，ACTIVE_TASKS gauge 递减从未真正执行过**（wt294 观察到的"漂移"实为必然漂移）。补模块级 `import asyncio` 修复；新测试钉住 success/error 两路径 gauge 回基线。旧路径下该 NameError 被吞（无人取回异常）；迁移后由 helper 日志可见——这正是本卡价值的现场演示。

## 5. 测试证据（DATABASE_URL="sqlite+aiosqlite:///:memory:" SECRET_KEY=…，worktree 无 .env）

- 新增 `tests/core/test_background_tasks.py`（**12 用例全绿**）：强引用注册/完成 discard、缺省名/自定义名、异常→自定义 on_error、异常→默认 handler 检索、cancelled 不触发 on_error、registry 隔离、pre-created 任务注册、drain 自然收尾、超时 cancel straggler、空集快路径、异常任务不算 pending、默认 handler 不抛。
- 新增 `tests/core/test_ff_convergence_sites.py`（**12 用例全绿**）：6 点位「FF 泄漏可见性」断言（tracked 计数增→任务真执行→discard 归零）+ graph_sync stop() 真 cancel + after-commit 钩子无 loop 分支 warning 跳过（线程内验证）+ gauge 双路径回基线。
- 定向回归批（改域+消费方+wt294 域）：`107 passed, 0 failed`（81s）——privacy_kill_switch_gauge、event_ack_reliability（graph_sync）、tool_history_service、llm_cost_monitoring、task_feedback submit/async_reflection（monkeypatch 挂点无回归）、auth_login_empty_credentials、x09_failure_recovery、post_commit_retrieval_invalidation、achievement_engine_regression。
- `import app.main` 冒烟通过（关停链衔接无 import 环）。
- 基线对照（协议第 6 条，主仓只读跑同款）：`test_round1_p2_fixes::test_rb05_get_top_users_handles_str_keys` 在 main 同红（内存 sqlite 存量限制），与本卡无关。
- ruff：14 改动文件 **0 问题**。black：新文件 3 个全 clean；存量文件主仓基线本就不 black-clean（对照验证），不做全文件重排避免噪声 diff。
- **mypy 棘轮：1802 ≤ 1803**（`mypy app` 全量口径），净降 1，已把 `quality/mypy_baseline.txt` 降为 1802；新模块单测文件 mypy 0 error。

## 6. 守卫

`bash scripts/run_all_rule_guards.sh` → **exit 0，83 规则全绿**。
环境坑（已解决）：主仓 `app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 内含指向主仓文件的 symlink，直接 `cp -R` 会把 symlink 带进 worktree，令 Rule K/Z 的 `relative_to(repo_root)` 崩溃——改用 `cp -RL`（解引用）+ 清 `.DS_Store`/`__pycache__` 后全绿。gen 三目录均 gitignored，不入 commit。

## 7. 风险与边界

- **graph_sync_worker.stop() 语义增强**：从"只翻 flag"变为 cancel+await；`_consume` 已有 `except asyncio.CancelledError: break`，取消安全。与 `shutdown_tracked_tasks` 双保险（重复 cancel 幂等）。
- **drain 宽限 5s**：FF 任务均为短尾 followup；极端阻塞任务超时后被 cancel（at-most-once 丢弃面与关停丢任务同性质，但现在**可见**——日志记录 drained 数量）。
- **tool_history/achievement after-commit**：从裸 spawn 改追踪 spawn，时序不变（仍是 commit 后下一拍调度）；无 loop 分支行为保持（warning 跳过，回调按原语义 pop 丢弃）。
- **main.py 关停顺序**：drain 插在 event_bus.close() 之前——tool_history after-commit 发布走 event_bus，先 drain 才不撞关闭中的 bus。
- llm_monitoring gauge 语义本身（finally 里 inc+延迟 dec = "活跃任务"口径可疑）超出本卡范围，未动；递减必达已修复。

## 8. 资源

LIGHT 卡全程：无模拟器/Gradle/浏览器/flutter；pytest 串行定向批（最大 107 用例/82s）；/tmp 守卫日志收工即清；磁盘净增 <1MB（patch+报告+测试）。
