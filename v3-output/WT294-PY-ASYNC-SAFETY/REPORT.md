# WT294-py-async-safety 审查报告

> 2026-09-24 ｜ C 线·Python 引擎异步安全审查（wt291 gateway race 巡检零发现的引擎侧延续）
> 工作树：wt294-py-async-safety ｜ 方法：grep 全量 + AST 扫描器（/tmp 自产，已清）+ 逐站点人工核对 + 变异实验闭环

## 一、四类模式计数

| 模式 | 扫描面 | 疑点 | 人工核对后实锤 |
|---|---|---|---|
| ① 跨 await 共享可变状态无同步 | AST 标记同实例属性被 ≥2 个含 await 的 async 方法写入：21 处 | 21 | **1 处 P0**（fusion_engine，见下）；其余良性（单所有者任务/同步段原子/幂等双载） |
| ② fire-and-forget 任务泄漏 | `asyncio.create_task`/`loop.create_task` 真实调用点（剔除 create_task 工具名字符串误中）：**24 处裸调用无引用** | 24 | 0 处 P0（均有内部 try/except 或自愈机制）；**约 10 处 P1** 缺强引用/done-callback |
| ③ 未等待的协程 | AST 裸调用疑点 49 处 | 49 | **0 实锤**（全部为同名同步方法、协程主动 `.close()`、`asyncio.run` 包装误报） |
| ④ check-then-act 竞窗 | AST 读@await@写 同函数序：29 处 | 29 | 0 处 P0（consumer `_subscribed` 守卫仅 lifespan 单次调用；懒加载/脚本缓存双载幂等；lockout 走 Redis INCR 原子） |

代码库已有多处修复后形态可作规范：`task_feedback_service.spawn_followup_task`（P1-C：强引用集合+done-callback）、`api/deps.py`、`source_lifecycle`、`security_monitor`（持引用+死亡钉回调）、`execution_engine` RB-13 注释、`orchestrator._track_task`、`multi_dimensional_learner._pending_saves`。

## 二、P0 清单与修法（已修）

### P0-1 `EvidenceFusionEngine.update_user_state` 读改写丢更新（已修复+回归测试）

- **位置**：`backend/app/services/evidence/fusion_engine.py` `update_user_state`（修前 L480-510）
- **模式**：①跨 await 读改写 + ④check-then-act 的合体。`load_state`(GET) → `fuse_many`(CPU) → `save_state`(SETEX)，三段之间有 await 点。
- **并发真实性**：三个独立入口写同一用户 belief state——`chat_signal_collector.py:309`（每轮聊天信号）、`task_event_consumer.py:490,573`（任务结局回灌）、`api/v1/cognitive.py:171`（API 直写）。且 `FusionEngine(str(user_id))` **按调用点即席实例化**，实例级锁无效。
- **触发序列推演**：同用户一轮回聊（信号采集）与一条任务完成事件（结局消费）并发 → A GET 到 v1、B GET 到 v1 → A 融合写入 v1+A' → B 融合写入 v1+B' → **A 的证据静默蒸发**。belief state 是双核路由（dual_core_router）的输入，丢证据=路由决策依据失真。
- **复现（修复前实测）**：8 路并发各自提交 1 条不同 target 证据，`setex` 前挂起 10ms 拉宽窗口 → **submitted=8 survived=1 LOST=7**。
- **修法**（小改，12 行语义增量）：模块级 `_user_state_locks: WeakValueDictionary[str, asyncio.Lock]`（等待者协程帧持 Lock 强引用，无持锁无等待时条目自动回收，不泄漏），`update_user_state` 开头按已解析 user_id 取锁串行化整个读改写。user_id 解析口径与 `load_state` 一致（空值同款 ValueError）。
- **测试**：`tests/unit/test_belief_fusion_engine.py::test_concurrent_update_user_state_serializes_per_user_and_keeps_all_evidence`——`RacyFakeRedis`（setex 前挂起）下 8 路并发断言 8 条证据全部存活。**变异实验闭环**：临时去锁→测试红；还原→19 全绿。修复后复现脚本 8/8 LOST=0。
- **边界说明**：本锁在**单引擎进程**部署假设下充分（当前架构即此）。若未来多实例水平扩引擎，需升级为分布式锁（Redis SET NX/Lua）——已列入交接建议。

## 三、P1 清单（只报告，未修）

1. **LLMService 单例可切换路由状态**（`app/services/llm_service.py:357-560`）：`_current_selection/_explicit_model_override/_provider/chat_model/_extra_body` 是单例上的可变路由状态，`switch_model_for_task/switch_to_specific_model` 有锁但锁不防"切换后到下次切换前"的跨请求串模型。**现状潜伏**：生产无单例调用方（`multi_intent_service` 自建实例），一旦被接入请求路径即翻车。建议：从单例移除切换方法，或改为 per-call selection 参数。
2. **SSE seq 非单调**（`app/core/sse.py:110`）：`seq=int(time.time()*1000)`，同毫秒两事件 seq 相同，重放过滤 `seq > last_seq_int` 会丢第二条——SSE 重放真实丢事件。建议 `max(now, last_seq+1)` 或 Redis INCR。
3. **FF 无强引用无 done-callback 站点簇**（异常被吞至 GC 才打"never retrieved"）：`core/auth_audit_service.py:62`（审计日志写丢失不可见）、`services/job_service.py:84`、`services/community_service.py:80`、`workers/graph_sync_worker.py:61,281`、`aurora/privacy.py:119`（隐私模式刷新丢失）、`services/tool_history_service.py:68`、`services/achievement_engine.py:84`（有回调无强引用）、`core/llm_monitoring.py:185`（ACTIVE_TASKS gauge 漂移）。建议统一收敛到 `spawn_followup_task` P1-C 模式，适合一张机械批量卡。
4. **graph_sync_worker 优雅关停缺失**（`workers/graph_sync_worker.py:61`）：`start()` 内 FF `_consume()` 无引用，`stop()` 只翻 flag 无法 cancel；`_consume` 内部异常处理+退避完整，无静默死亡，但关停面裸奔。
5. **job_service FF 执行体丢失**：job 卡 running 至 `timeout_at`；有 `startup_recovery` 兜底，建议确认 reaper 实际存在。
6. **predictive DEBUG 门控锁释放**（`services/predictive_service.py:1996-2018`）：锁释放依赖 FF 任务存活，TTL 300s 兜底自愈；仅 DEBUG 路径，风险有限。

## 四、P2（简列）

consumer `start()` `_subscribed` 守卫（lifespan 单次）｜懒加载 `_loaded`/quota 脚本 sha/achievement 缓存双载幂等｜CircuitBreaker 双重 OPEN（opened_count 多计 1）｜pending_actions no-redis 模式清理任务双启｜billing_worker `_batch` 单任务所有者安全（at-least-once+request_id 唯一约束去重）｜event_bus `close()` 与在途 publish 关机期竞窗｜AccountLockout TOCTOU（INCR 原子，策略窗口可接受）｜route_cache.invalidate FF（TTL 自愈）。

## 五、测试与守卫结果

- **定向 pytest**（`DATABASE_URL=sqlite+aiosqlite:///:memory:`）：
  - `tests/unit/test_belief_fusion_engine.py`：**19 passed**（含新增回归）
  - evidence 簇 7 文件：**44 passed + 1 failed**
  - 该 1 失败（`test_evidence_resolve.py::...memory_backed_review_payload`，`app.services.error_book_mastery_sync_service` 装配缺失）在**基线克隆同样失败**——存量问题，与本卡无关（建议另开卡）。
- **变异实验**：去锁→红、还原→绿，证明回归测试钉住修复。
- **ruff**：两改动文件 0 问题（0 新增）。
- **守卫**：`run_all_rule_guards.sh` exit=1，失败项 **AQ、BG 在基线克隆同样 exit=1**（worktree 缺 `make proto-gen` 产物/`app.gen` 不可导入，环境红，主仓为准）；其余规则全绿（含 DB-HEAD、COMM-LB、FS-CARRY、N37-TIMEOUT、UX-DUPTITLE）。

## 六、资源峰值

LIGHT 卡全程：无模拟器/Gradle/浏览器/全库测试；pytest 单文件串行；基线克隆与探针脚本均入 /tmp（收工已清）；磁盘无新增负担，swap 无压力（未触发 HEAVY 门）。

## 七、交接建议

1. **合入**：本卡交付 = worktree 两文件改动 + `changes.patch`；主会话合入后跑定向 `pytest tests/unit/test_belief_fusion_engine.py`（对比法）。
2. **另开卡（存量）**：`error_book_mastery_sync_service` 装配缺失致 `test_evidence_resolve` 红。
3. **P1-1（LLMService 单例切换状态）**建议引擎侧小卡拆除或隔离——潜伏的跨请求串模型。
4. **P1-2（SSE seq 单调化）**小改高价值，可随 C 线旅程卡顺带修。
5. **P1-3（FF 收敛 spawn_followup_task）**机械批量卡，一次清 10 处。
6. **多实例前提变化时**：per-user 进程内锁需升级分布式锁（Redis SET NX/Lua）；当前单引擎假设下充分，报告已注明。
