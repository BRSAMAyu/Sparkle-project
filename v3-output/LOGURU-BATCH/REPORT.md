# LOGURU-BATCH 收工报告 —— 全仓 loguru `%s` 丢参缺陷批量收口

> C 纵队生产级线 · worktree wt187 · 基线 5588ed0a · 2026-09-22
> 交付物：本报告 + 同目录 `changes.patch`（50 文件，163 处，全为格式串行内改动）。未 commit 未 push，零凭据。

## 0. 结论一句话

全仓 `backend/app/` 下 loguru 调用中 printf 风格传参（loguru 不解析、参数被静默丢弃）共 **163 处 / 50 文件**，全部机械收敛为 loguru `{}` 位置参数形制；修后 AST 重扫 **0 残留**、原始 grep 交叉验证 **loguru 文件 0 残留**、定向对比法测试 **5 组 68 用例双侧全绿零新增失败**、`py_compile` 50 文件全过、ruff 全过、零行越界。

## ① 全仓清单（修前）与修后重扫证据

### 扫描方法（AST 辅助，非裸 grep）

自研扫描器 `_loguru_scan.py`（置于 worktree 根，untracked，不入 patch）：
1. 按文件解析 import：`from loguru import logger`（含函数级与 `as` 别名）→ loguru；`logging.getLogger` → stdlib（**stdlib 的 `%s` 是正确用法，不属缺陷、不扫描**）；
2. AST 定位 `logger.(trace|debug|info|success|warning|error|critical|exception|log)` 调用，支持 `logger.opt(...).warning(...)` 链式接收者；
3. 提取消息实参（`logger.log` 跳过 level 首参）中的字符串常量/f-string 常量片段，匹配 printf 规格 `%[-+ #0]*\d*(?:\.\d+)?[sdrf]`（跳过 `%%` 转义）；
4. 三轮盲区修复后才定稿：链式调用（`base_name` 不穿透 `.opt()` Call，漏 11 处）、`%.1fs` 类单位后缀（尾随字母 negative-lookahead 误杀，验证阶段被占位符/参数计数校验兜出）、`%.2f` 宽度精度规格；
5. 扫描结果与裸 grep（161 行原始命中）逐行交叉核对：**loguru 文件内 grep 命中 100% 被清单覆盖，0 漏报**；清单外的 grep 残留全部属于 stdlib logging 文件（61 行，正确用法，原样保留）。

### 修前全量清单（163 处）

- 分布：`celery_tasks.py` 47（wt182 估 28，AST 实际更多）、`orchestrator.py` 15、`profile_write_service.py` 12（wt182 估 9）、`chat_signal_collector.py` 6、`task_event_consumer.py` 5、其余 45 文件 1-4 处。
- 规格频次：`%s`×252、`%d`×14、`%.0f`×3、`%.2f`×3、`%.1f`×2、`%+.2f`×2、`%r`×1（共 277 个规格实例）。
- **f-string 双重格式与 printf 预格式化（`"..." % args`）在 app/ 下实为 0 例**（wt182 报告推测"部分需甄别假阳性"，AST 甄别结论：无）。
- 163 行完整清单见附录 A。

### 修后重扫 = 0

```
$ python3.11 _loguru_scan.py   （修后同口径重扫）
counts: {'': 1744, 'OK-FSTRING-CLEAN': 2129}   ← 无任何 DEFECT 键，缺陷 0
```
grep 交叉验证：61 行 log 调用 printf 残留全部位于 stdlib `logging.getLogger` 文件（`core/pending_actions.py`、`core/budget_matrix.py`、`core/request_coalescing.py`、`core/llm_security_wrapper.py`、`api/v1/users.py`、`aurora/runtime_v1/__init__.py` 等），属 stdlib 正确用法，**loguru 文件残留 = 0**。

## ② 改动统计

| 维度 | 数值 |
|---|---|
| 改动文件 | 50（全在 `backend/app/`） |
| 改动调用点 | 163 |
| 改动行 | 167 增 / 167 删（4 处为跨两行的隐式拼接字面量），**0 行无 spec 对应** |
| 改动性质 | 只改字符串字面量内的格式规格：`%s`/`%d`→`{}`，`%r`→`{!r}`，`%[flags][w][.p]f`→`{:[flags][w][.p]f}`（精度原样保留）；**参数列表一字未动**（先例形制：位置参数改 {} + 值作参数传，即 wt182 scheduler_service 与 achievement_engine 同款） |

转换示例（真实 diff）：
```diff
-            "Recall scan: %d users × %d triggers = %d tasks dispatched (cap=%d)",
+            "Recall scan: {} users × {} triggers = {} tasks dispatched (cap={})",
-                logger.debug("ErrorReplanBridge: unsupported error_type=%r for error_id=%s", raw_type, error_id)
+                logger.debug("ErrorReplanBridge: unsupported error_type={!r} for error_id={}", raw_type, error_id)
-            "LowYieldGuard: blocked activity=%s yield=%.2f (base=%.2f adj=%+.2f) deadline_hours=%.0f",
+            "LowYieldGuard: blocked activity={} yield={:.2f} (base={:.2f} adj={:+.2f}) deadline_hours={:.0f}",
```

行为等价性依据：loguru 0.7.3 源码 `message.format(*args, **kwargs)`（`loguru/_logger.py` `_log`）——修复即让 format 真正吃到参数；改动前后参数求值顺序与表达式完全一致，f-string 无一改动（0 例）。

## ③ 冲突面声明

50 个改动文件与三张在途卡**零交集**（已对 patch 文件名逐一 grep 验证）：
- **wt178（mobile）**：本卡只动 `backend/app/` Python，0 交叠；
- **wt180（event_bus.py + chat_orchestrator.go + outbox publisher）**：清单无 `event_bus.py`、无 outbox 相关文件、无 Go 文件（`services/task_event_consumer.py` 是消费者服务，非 event_bus 本体），0 交叠；
- **wt186（monitoring + bootstrap + 备份调度）**：清单无 monitoring/bootstrap/备份调度文件，0 交叠；
- **wt182 已修的 `scheduler_service.py`**（基线 5588ed0a 已含）：本卡未触碰该文件（patch 文件名核对），其修复形制与本卡一致，无重复无回退；wt182 新增的 `test_scheduler_execution_tick_log.py`（断言日志含真实数值、不含字面量 %s）在本卡 worktree 重跑 **1 passed**，恰为本次批量修复的回归钉。

## ④ 诚实申报

1. **`exc_info=True` 在 loguru 下本就无效**（loguru 吞掉未知 kwargs，不会附加 traceback；仅 stdlib logging 语义）。本卡有 5 处修复点带 `exc_info=True`（growth:104、l2_intervention:344、llm_service:258、low_yield_guard:135、spine_orchestrator:1632）。**修前修后该 kwarg 都是死参，本次原样保留未动**——改成 `logger.opt(exception=True)` 会给日志新增 traceback 输出，属行为变化，超出本卡"零行为逻辑变化"边界，建议后续卡单独裁决。
2. **两处 `%.0f%%` 的 `%%` 原样保留**（celery_tasks:1952、2018）：printf 从未真正执行过，loguru 直通下 `%%` 今日就显示为两个字面 `%`；format() 同样直通 `%%`，修后显示不变。
3. **`%d`→`{}` 而非 `{:d}`**：`%d` 对非整数在 printf 下会抛 TypeError（在 loguru 下从未执行故从未触发）；`{}` 恒安全且整数渲染相同。清单内 `%d` 全为计数类整数（`dispatched`、`len(...)`），无精度损失场景。
4. **wt182 估算与实扫差异**：celery_tasks 实为 47 处（估 28）、profile_write_service 实为 12 处（估 9）——估算来自抽验，AST 全扫为准。
5. **修前基线语义**：163 处修前全部"值不可见"（消息按字面输出），其中格式串无 `{}` 占位、loguru 检测到 args 仍会执行 format()，故任何一处若消息含裸 `{`/`}` 本会运行时抛错——全量 format 安全校验（163 处逐一 `msg.format(*dummies, **kwargs)` 干跑）通过，说明这些调用点今日线上均在正常直通，无潜在崩溃面被我掩盖。
6. 每处修复均经三重机器校验后才落盘：占位符数==位置参数数、format 干跑无异常、字节级 splice 断言（曾发现 ast col_offset 是 UTF-8 字节偏移、emoji/`×` 导致字符偏移错位，已改字节空间拼接）；任何一重失败即中止不写盘。
7. 测试基建说明：worktree 缺 gitignored 的 `backend/app/gen`，已从主仓拷贝（两侧克隆同放）用于测试导入；不入 patch、不属交付物。
8. 扫描/修复脚本 `_loguru_scan.py`、`_loguru_fix.py` 留在 worktree 根（untracked，不入 patch），随 worktree 生命周期回收；算法已完整记载于本报告 ①/② 节。

## ⑤ 收工核查

**对比法回归**（基线 = `git clone wt187` → `/tmp/wt187-baseline`，仅含 HEAD 5588ed0a；双侧同集合、同环境 `SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:"`、逐命令显式 cd、一次一个 pytest）：

| 域（受影响文件域） | 基线 | 本卡 worktree | 新增失败 |
|---|---|---|---|
| celery_tasks（47 处）｜4 测试文件 | 9 passed | 9 passed | **0** |
| profile_write_service（12 处）+ chat_signal_collector（6 处）｜3 测试文件 | 17 passed | 17 passed | **0** |
| orchestrator（15 处）｜4 测试文件 | 14 passed | 14 passed | **0** |
| billing_worker（4 处）+ photon_service（3 处）｜2 测试文件 | 15 passed | 15 passed | **0** |
| aurora planning（4 处）+ wt182 scheduler 日志回归钉｜2 测试文件 | 13 passed | 13 passed | **0** |

三域必跑（celery/profile_write/chat_signal）+ 抽样 3 域（orchestrator、billing/photon、aurora planning）共 68 用例，**失败名单双侧 diff 为空**。

**静态校验**：50 文件 `python3.11 -m py_compile` 全过；改动文件 ruff（项目 120 列配置）全过；diff 逐行核验 0 行新增越 120 列（7 条既有 >120 行长度逐字节不变）；patch 中每条删除行都含 printf 规格、每条新增行都含 `{}` 形制。

**行为演示**（loguru 0.7.3 实测）：
```
logger.error("run_counterfactual_evaluations failed: %s", exc)  → "…failed: %s"          （值丢失，修前）
logger.error("run_counterfactual_evaluations failed: {}", exc)  → "…failed: boom"        （值可见，修后）
logger.info("✅ Dispatched {} spaced repetition reminder tasks", 7) → "…Dispatched 7 …"  （值可见，修后）
```

**收工清理**：`/tmp/wt187-baseline`、`/tmp/loguru_*`、`/tmp/raw_grep_hits.txt`、`/tmp/inv_*` 已删；worktree 内未新增 tracked 交付物以外文件（`git status` 仅 2 个 untracked 脚本 + v3-output/LOGURU-BATCH/）；未 commit 未 push；无模拟器/浏览器/Gradle 启停。

## 附录 A：修前全量清单（163 行，`文件:行` 为修前坐标）

| # | 位置 | 规格 | 调用（原文首行） |
|---|---|---|---|
| 1 | `agents/standard_workflow.py:496` | %s,%.1f | `logger.warning(` |
| 2 | `agents/standard_workflow.py:506` | %s,%s | `logger.warning(` |
| 3 | `agents/standard_workflow.py:620` | %s,%.1f | `logger.warning(` |
| 4 | `agents/standard_workflow.py:634` | %s | `logger.warning("Explicit expert collaboration synthesis degraded: %s", exc)` |
| 5 | `api/v1/experiments.py:414` | %s | `logger.warning(` |
| 6 | `api/v1/experiments.py:457` | %s,%s | `logger.warning(` |
| 7 | `api/v1/growth.py:104` | %s | `logger.warning("growth: cache write failed for user_key=%s", user_key, exc_info=True)` |
| 8 | `aurora/core_session.py:414` | %s | `logger.warning("Failed to deserialize AuroraCoreSession from JSON: %s", exc)` |
| 9 | `aurora/core_session.py:550` | %s | `logger.warning("Failed to deserialize AuroraCoreSession from record payload: %s", exc)` |
| 10 | `aurora/runtime_v1/l2_intervention.py:344` | %s,%s | `logger.warning("L2 intervention cooldown write failed for user=%s pattern=%s", user_id, pattern_name, exc_info` |
| 11 | `aurora/runtime_v1/planning.py:371` | %s,%s | `logger.warning(` |
| 12 | `aurora/runtime_v1/planning.py:383` | %s,%s | `logger.warning("Failed to load Aurora planning snapshot for user=%s error=%s", user_id, exc)` |
| 13 | `aurora/runtime_v1/planning.py:1127` | %s,%s | `logger.warning("Failed to persist Aurora planning snapshot for user=%s error=%s", state.user_id, exc)` |
| 14 | `core/celery_tasks.py:1112` | %s | `logger.error("run_counterfactual_evaluations failed: %s", exc)` |
| 15 | `core/celery_tasks.py:1654` | %s,%s | `logger.info(` |
| 16 | `core/celery_tasks.py:1676` | %s,%s,%s | `logger.error(` |
| 17 | `core/celery_tasks.py:1843` | %s,%s | `logger.info("✅ Spaced repetition reminder task finished for user %s: %s", user_id, result)` |
| 18 | `core/celery_tasks.py:1846` | %s,%s | `logger.error("❌ spaced_repetition_reminder_task failed for user %s: %s", user_id, exc)` |
| 19 | `core/celery_tasks.py:1896` | %d | `logger.info("✅ Dispatched %d spaced repetition reminder tasks", dispatched)` |
| 20 | `core/celery_tasks.py:1902` | %s | `logger.error("❌ scan_spaced_repetition_reminders failed: %s", exc)` |
| 21 | `core/celery_tasks.py:1936` | %s | `logger.debug(` |
| 22 | `core/celery_tasks.py:1943` | %s | `logger.debug(` |
| 23 | `core/celery_tasks.py:1951` | %.0f,%s | `logger.debug(` |
| 24 | `core/celery_tasks.py:1980` | %s,%s | `logger.debug(` |
| 25 | `core/celery_tasks.py:2018` | %s,%s,%.0f | `logger.info(` |
| 26 | `core/celery_tasks.py:2035` | %s,%s | `logger.error("❌ daily_sprint_reminder_task failed for user %s: %s", user_id, exc)` |
| 27 | `core/celery_tasks.py:2077` | %d | `logger.info("✅ Dispatched %d sprint reminder tasks", dispatched)` |
| 28 | `core/celery_tasks.py:2083` | %s | `logger.error("❌ scan_daily_sprint_reminders failed: %s", exc)` |
| 29 | `core/celery_tasks.py:2126` | %s | `logger.debug("comeback_nudge_task: duplicate reminder suppressed for user %s", user_id)` |
| 30 | `core/celery_tasks.py:2155` | %s,%s,%d | `logger.info(` |
| 31 | `core/celery_tasks.py:2171` | %s,%s | `logger.error("❌ comeback_nudge_task failed for user %s: %s", user_id, exc)` |
| 32 | `core/celery_tasks.py:2232` | %d | `logger.info("✅ Dispatched %d comeback nudge tasks", dispatched)` |
| 33 | `core/celery_tasks.py:2238` | %s | `logger.error("❌ scan_comeback_nudges failed: %s", exc)` |
| 34 | `core/celery_tasks.py:2322` | %s | `logger.debug("weekly_growth_narrative_task: duplicate narrative suppressed for user %s", user_id)` |
| 35 | `core/celery_tasks.py:2355` | %s,%s | `logger.info(` |
| 36 | `core/celery_tasks.py:2372` | %s,%s | `logger.error("❌ weekly_growth_narrative_task failed for user %s: %s", user_id, exc)` |
| 37 | `core/celery_tasks.py:2446` | %d | `logger.info("✅ Dispatched %d weekly growth narrative tasks", dispatched)` |
| 38 | `core/celery_tasks.py:2452` | %s | `logger.error("❌ scan_weekly_growth_narratives failed: %s", exc)` |
| 39 | `core/celery_tasks.py:2646` | %s,%s,%s | `logger.info(` |
| 40 | `core/celery_tasks.py:2657` | %s,%s | `logger.error("aurora_wake_deliver_task failed for wake %s: %s", wake_id, exc)` |
| 41 | `core/celery_tasks.py:2682` | %d,%d | `logger.info(` |
| 42 | `core/celery_tasks.py:2692` | %s | `logger.error("scan_aurora_scheduled_wakes failed: %s", exc)` |
| 43 | `core/celery_tasks.py:2733` | %s | `logger.debug("Spine on_recall_check skipped for user=%s", user_id)` |
| 44 | `core/celery_tasks.py:2770` | %s,%s,%s | `logger.info(` |
| 45 | `core/celery_tasks.py:2781` | %s,%s | `logger.error("recall_notification_task failed for user %s: %s", user_id, exc)` |
| 46 | `core/celery_tasks.py:2865` | %d,%d,%d,%d | `logger.info(` |
| 47 | `core/celery_tasks.py:2877` | %s | `logger.error("scan_recall_notifications failed: %s", exc)` |
| 48 | `core/celery_tasks.py:2927` | %s,%s | `logger.error("spine_snapshot_task failed for user %s: %s", user_id, exc)` |
| 49 | `core/celery_tasks.py:2984` | %d,%d | `logger.info("Spine snapshot scan: %d users, %d tasks dispatched", len(user_ids), dispatched)` |
| 50 | `core/celery_tasks.py:2990` | %s | `logger.error("scan_spine_snapshots failed: %s", exc)` |
| 51 | `core/celery_tasks.py:3017` | %s,%s | `logger.error("compact_user_traces failed for user %s: %s", user_id, exc)` |
| 52 | `core/celery_tasks.py:3056` | %d | `logger.info("Trace compaction scan: %d users dispatched", dispatched)` |
| 53 | `core/celery_tasks.py:3062` | %s | `logger.error("scan_trace_compaction failed: %s", exc)` |
| 54 | `core/celery_tasks.py:3108` | %s | `logger.error("community_cohort_signal_task failed: %s", exc)` |
| 55 | `core/celery_tasks.py:3156` | %s | `logger.error("scan_community_cohort_signals failed: %s", exc)` |
| 56 | `core/celery_tasks.py:3187` | %s | `logger.error("spine_expire_stale_states failed: %s", exc)` |
| 57 | `core/celery_tasks.py:3213` | %s | `logger.error("spine_auto_deprecate_skills failed: %s", exc)` |
| 58 | `core/celery_tasks.py:3243` | %s | `logger.error("apply_memory_decay failed: %s", exc)` |
| 59 | `core/celery_tasks.py:3269` | %s | `logger.error("run_weekly_benchmark failed: %s", exc)` |
| 60 | `core/celery_tasks.py:3356` | %s | `logger.error("monitor_safe_experiment_guardrails failed: %s", exc)` |
| 61 | `learning/prompt_bandit.py:85` | %s | `logger.warning("PromptBandit received invalid reward=%s", reward)` |
| 62 | `orchestration/adaptive_replanner.py:1989` | %s,%s | `logger.error("R2-03: PlanAdjustmentApplier failed for plan %s: %s", report.plan_id, exc)` |
| 63 | `orchestration/adaptive_replanner.py:2007` | %s,%s | `logger.error("R2-03: Card protocol writeback failed for plan %s: %s", report.plan_id, exc)` |
| 64 | `orchestration/execution_engine.py:2240` | %s,%s | `logger.warning(` |
| 65 | `orchestration/execution_engine.py:2304` | %s | `logger.warning(` |
| 66 | `orchestration/execution_engine.py:2503` | %s | `logger.info(` |
| 67 | `orchestration/orchestrator.py:1448` | %s,%s | `logger.opt(exception=True).warning(` |
| 68 | `orchestration/orchestrator.py:1505` | %s | `logger.debug("Non-standard session_id format, using uuid5 fallback: %s", raw[:50])` |
| 69 | `orchestration/orchestrator.py:2140` | %s,%s | `logger.opt(exception=True).warning(` |
| 70 | `orchestration/orchestrator.py:2569` | %s | `logger.opt(exception=True).warning("Redis/spine get_response_directive failed for user=%s", user_id)` |
| 71 | `orchestration/orchestrator.py:2575` | %s | `logger.opt(exception=True).warning("Redis/spine get_retrieval_directive failed for user=%s", user_id)` |
| 72 | `orchestration/orchestrator.py:2585` | %s | `logger.opt(exception=True).warning(` |
| 73 | `orchestration/orchestrator.py:2603` | %s | `logger.opt(exception=True).warning(` |
| 74 | `orchestration/orchestrator.py:2612` | %s | `logger.opt(exception=True).warning("Redis/spine get_ux_directive failed for user=%s", user_id)` |
| 75 | `orchestration/orchestrator.py:2618` | %s | `logger.opt(exception=True).warning("Redis/spine get_community_directive failed for user=%s", user_id)` |
| 76 | `orchestration/orchestrator.py:2624` | %s | `logger.opt(exception=True).warning("Redis/spine get_skill_directive failed for user=%s", user_id)` |
| 77 | `orchestration/orchestrator.py:2900` | %s | `logger.debug(` |
| 78 | `orchestration/orchestrator.py:3934` | %s,%s | `logger.info(` |
| 79 | `orchestration/orchestrator.py:3940` | %s,%s | `logger.debug("Skill extract skipped for user=%s: %s", user_id, _ve)` |
| 80 | `orchestration/orchestrator.py:3943` | %s,%s | `logger.warning(` |
| 81 | `orchestration/orchestrator.py:3957` | %s | `logger.warning("Failed to schedule chat signal collection: %s", exc)` |
| 82 | `orchestration/plan_review_service.py:1926` | %s,%s | `logger.info("Retrieving stored plan %s for user %s", plan_id, user_id)` |
| 83 | `orchestration/plan_review_service.py:2293` | %s | `logger.opt(exception=task.exception()).error(` |
| 84 | `orchestration/planning_workflow.py:3369` | %s,%s | `logger.warning("Failed to load previous exam weak nodes for user=%s error=%s", user_id, exc)` |
| 85 | `orchestration/prompts.py:1309` | %s | `logger.opt(exception=True).debug("Failed to resolve model tier for key=%s", model_key)` |
| 86 | `orchestration/session_state_mixin.py:985` | %s,%s | `logger.info("Context self-heal versions user=%s healed=%s", user_id, healed)` |
| 87 | `orchestration/summarization_worker.py:221` | %s,%s | `logger.warning(` |
| 88 | `orchestration/summarization_worker.py:232` | %s | `logger.warning(` |
| 89 | `services/agent_grpc_service.py:213` | %s,%s | `logger.error(` |
| 90 | `services/agent_grpc_service.py:222` | %s | `logger.error(` |
| 91 | `services/agent_grpc_service.py:411` | %s | `logger.info(` |
| 92 | `services/analysis/unified_analysis_service.py:92` | %s | `logger.info("Episodic memory write blocked for analysis task %s", result.task_id)` |
| 93 | `services/asset_review_signal_processor.py:107` | %s | `logger.warning("AssetReviewSignalProcessor failed to update inferred prefs: %s", exc)` |
| 94 | `services/billing_worker.py:208` | %s,%s | `logger.error(` |
| 95 | `services/billing_worker.py:229` | %s,%s | `logger.error(` |
| 96 | `services/billing_worker.py:237` | %s,%s | `logger.error(` |
| 97 | `services/billing_worker.py:252` | %s,%s | `logger.warning(` |
| 98 | `services/chat_signal_collector.py:228` | %s | `logger.warning("ChatSignalCollector evidence extraction failed: %s", exc)` |
| 99 | `services/chat_signal_collector.py:369` | %s | `logger.warning("ChatSignalCollector belief shadow fusion failed: %s", exc)` |
| 100 | `services/chat_signal_collector.py:416` | %s,%s | `logger.warning("ChatSignalCollector failed to persist %s: %s", label, exc)` |
| 101 | `services/chat_signal_collector.py:425` | %s | `logger.warning("Failed to cache chat signal entry: %s", exc)` |
| 102 | `services/chat_signal_collector.py:448` | %s | `logger.warning("Failed to increment chat signal counter: %s", exc)` |
| 103 | `services/chat_signal_collector.py:456` | %s | `logger.warning("Failed to load chat signal entries: %s", exc)` |
| 104 | `services/community_signal_collector.py:71` | %s | `logger.warning("CommunitySignalCollector failed to persist updates: %s", exc)` |
| 105 | `services/community_signal_collector.py:80` | %s | `logger.warning("Failed to cache community signal entry: %s", exc)` |
| 106 | `services/community_signal_collector.py:89` | %s | `logger.warning("Failed to increment community signal counter: %s", exc)` |
| 107 | `services/community_signal_collector.py:97` | %s | `logger.warning("Failed to load community signal entries: %s", exc)` |
| 108 | `services/community_strategy_service.py:43` | %s,%s,%s,%s | `logger.info(` |
| 109 | `services/error_book_grpc_service.py:46` | %s,%s | `logger.error(` |
| 110 | `services/error_book_grpc_service.py:54` | %s | `logger.error(` |
| 111 | `services/error_book_signal_processor.py:74` | %s | `logger.warning("ErrorBookSignalProcessor failed to update inferred prefs: %s", exc)` |
| 112 | `services/error_replan_bridge.py:210` | %r,%s | `logger.debug("ErrorReplanBridge: unsupported error_type=%r for error_id=%s", raw_type, error_id)` |
| 113 | `services/execution_learning_service.py:484` | %s,%s | `logger.warning("Execution learning fragment creation failed for %s: %s", intent.id, exc)` |
| 114 | `services/execution_learning_service.py:782` | %s,%s | `logger.warning("Execution learning replanner trigger failed for plan %s: %s", plan_id, exc)` |
| 115 | `services/execution_service.py:1379` | %s | `logger.warning("dispatch_batch timed out after 300s for batch %s", batch_id)` |
| 116 | `services/execution_service.py:3218` | %s,%s | `logger.warning("Failed to record token usage for failed intent %s: %s", intent.id, exc)` |
| 117 | `services/focus_signal_processor.py:161` | %s | `logger.warning("Failed to create focus completion fragment: %s", exc)` |
| 118 | `services/galaxy/retrieval_service.py:307` | %s | `logger.warning("Redis hybrid search timed out, fallback_enabled=%s", settings.ENABLE_REDIS_HYBRID_FALLBACK)` |
| 119 | `services/galaxy_feedback_signal_processor.py:63` | %s | `logger.warning("GalaxyFeedbackSignalProcessor failed to update inferred prefs: %s", exc)` |
| 120 | `services/galaxy_grpc_service.py:145` | %s,%s | `logger.error(` |
| 121 | `services/galaxy_grpc_service.py:153` | %s | `logger.error(` |
| 122 | `services/gateway_client.py:43` | %s,%s | `logger.warning("Gateway push failed: %s %s", resp.status_code, resp.text)` |
| 123 | `services/graphrag_trace_store.py:82` | %s | `logger.warning("GraphRAG trace too large to cache trace_id=%s", trace.trace_id)` |
| 124 | `services/job_service.py:200` | %s | `logger.warning(` |
| 125 | `services/job_service.py:215` | %s | `logger.warning(` |
| 126 | `services/job_service.py:230` | %s | `logger.warning(` |
| 127 | `services/llm_service.py:258` | %s | `logger.warning("_record_token_usage: monitoring failed for model=%s", model, exc_info=True)` |
| 128 | `services/notification_center_service.py:101` | %s | `logger.info("Skipped spaced repetition reminder for user %s: disabled by preferences", user_id)` |
| 129 | `services/photon_service.py:354` | %s,%s,%s,%s | `logger.info(` |
| 130 | `services/photon_service.py:400` | %s,%s | `logger.info(` |
| 131 | `services/photon_service.py:416` | %s,%s | `logger.warning(` |
| 132 | `services/profile_context_service.py:163` | %s,%s,%s,%s,%s,%s | `logger.info(` |
| 133 | `services/profile_context_service.py:438` | %s,%s,%s | `logger.info(` |
| 134 | `services/profile_event_consumer.py:295` | %s,%s | `logger.warning("Failed to load SeedLibrary %s: %s", library_id, db_exc)` |
| 135 | `services/profile_write_service.py:105` | %s,%s,%s | `logger.warning(` |
| 136 | `services/profile_write_service.py:144` | %s,%s,%s | `logger.warning(` |
| 137 | `services/profile_write_service.py:184` | %s,%s | `logger.debug("Inferred pref %s blocked by memory policy: %s", key, decision.reason)` |
| 138 | `services/profile_write_service.py:197` | %s | `logger.debug("Skipping inferred pref %s: explicit override exists", key)` |
| 139 | `services/profile_write_service.py:221` | %s,%s,%s | `logger.warning(` |
| 140 | `services/profile_write_service.py:386` | %s,%s | `logger.warning("Failed to list inferred backups for %s: %s", user_id, exc)` |
| 141 | `services/profile_write_service.py:472` | %s,%s | `logger.error("R2-02: ProfilePreferenceUpdated publish failed for user %s: %s", user_id, exc)` |
| 142 | `services/profile_write_service.py:490` | %s,%s,%s | `logger.error("R2-02: ProfilePreferenceDeleted publish failed for user %s key %s: %s", user_id, pref_key, exc)` |
| 143 | `services/profile_write_service.py:532` | %s,%s | `logger.warning("Failed to backup inferred preference %s: %s", pref_key, exc)` |
| 144 | `services/profile_write_service.py:540` | %s,%s | `logger.warning("Failed to load inferred backup %s: %s", pref_key, exc)` |
| 145 | `services/profile_write_service.py:547` | %s,%s | `logger.warning("Failed to parse inferred backup %s: %s", pref_key, json_exc)` |
| 146 | `services/profile_write_service.py:559` | %s,%s | `logger.warning("Failed to delete inferred backup %s: %s", pref_key, exc)` |
| 147 | `services/push_feedback_service.py:48` | %s,%s | `logger.warning("Unknown push interaction action=%s user_id=%s", action, user_id)` |
| 148 | `services/push_feedback_service.py:151` | %s | `logger.warning("Failed to cache push interaction: %s", exc)` |
| 149 | `services/push_feedback_service.py:164` | %s | `logger.warning("Failed to load push interactions: %s", exc)` |
| 150 | `services/response_feedback_service.py:217` | %s,%s,%s,%s | `logger.info(` |
| 151 | `services/streak_signal_processor.py:83` | %s | `logger.warning("StreakSignalProcessor failed to update inferred prefs: %s", exc)` |
| 152 | `services/task_event_consumer.py:52` | %s,%s,%s | `logger.warning("%s failed for %s: %s", label, ctx_id, exc)` |
| 153 | `services/task_event_consumer.py:224` | %s,%s | `logger.warning("Failed to fetch plan_id for task %s: %s", task_id, exc)` |
| 154 | `services/task_event_consumer.py:238` | %s,%s | `logger.warning("AdaptiveReplanner failed for plan %s: %s", plan_id, exc)` |
| 155 | `services/task_event_consumer.py:268` | %s,%.2f | `logger.debug("Updated Goal %s progress to %.2f", goal.id, goal.progress)` |
| 156 | `services/task_event_consumer.py:270` | %s | `logger.warning("Failed to update goal progress: %s", goal_exc)` |
| 157 | `services/user_service.py:169` | %s,%s,%s | `logger.info(` |
| 158 | `signals/community_loops.py:265` | %s,%s,%s | `logger.info(` |
| 159 | `signals/low_yield_guard.py:129` | %s,%s,%s,%+.2f | `logger.debug(` |
| 160 | `signals/low_yield_guard.py:135` | %s | `logger.debug("LowYieldGuard: personalization lookup failed user=%s", user_id, exc_info=True)` |
| 161 | `signals/low_yield_guard.py:182` | %s,%.2f,%.2f,%+.2f,%.0f | `logger.info(` |
| 162 | `signals/safety_degradation.py:76` | %s,%s,%s | `logger.warning(` |
| 163 | `signals/spine_orchestrator.py:1632` | %s | `logger.warning("build_context_receipt failed for user=%s", user_id, exc_info=True)` |