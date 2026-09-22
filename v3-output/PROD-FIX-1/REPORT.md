# PROD-FIX-1 收工报告 — 两个 P1 级生产缺陷修复（生产级线）

- Worker：C 纵队 PROD-FIX-1（wt179）
- 基线：`a2506361`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt179`）
- 缺陷依据：主仓 `v3-output/PROD-LOG/REPORT.md` ②-1、②-2
- 交付物：本报告 + 同目录 `changes.patch`（对 a2506361 `git apply --check` 通过，含 5 个改动文件 + 1 个新测试文件）
- 红线遵守：零 commit / 零 push / 零凭据；测试全程 `SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest`

---

## ① 两缺陷修法与签名/列名对齐证据

### 缺陷 1：SecurityMonitor 全死（安全面）

**证据对齐**（活栈日志 ↔ 复现异常逐字一致）：

- 活栈：`uvicorn_engine.log:20` `"Failed to initialize Security Monitor: SecurityMonitor.initialize() takes 1 positional argument but 2 were given"`（每次启动必现）
- 红证复现（修复前新测试）：`TypeError: SecurityMonitor.initialize() takes 1 positional argument but 2 were given` —— 与生产日志逐字一致

**签名漂移事实**：调用侧 `backend/app/main.py:203`（改前）`await security_monitor.initialize(cache_service.redis)` 传参；被调侧 `backend/app/core/security_monitor.py:97`（改前）`async def initialize(self):` 无参（redis 在 `__init__:87` 已自取 `cache_service.redis`）。

**修法（以调用侧真实意图为准）**：调用侧意图是**显式注入启动期已就绪的 redis 实例**。故将被调侧签名对齐为 `async def initialize(self, redis: Any | None = None)`：传参则采纳注入（`self.redis = redis`），不传则沿用 `__init__` 自取——双向兼容，无其他调用方破坏（全库 `.initialize(` 调用点已巡检，见 ④-3）。

**启动即验 + 失败不静默**：

1. 成功标记：`self.initialized=True`、`self.initialized_at`、后台任务持引用登记（`self._background_tasks`，防 GC 丢弃）；新增 `get_startup_status()` 健康面；main.py 成功路径结构化日志输出 `Security Monitor initialized successfully: {startup_status}`。
2. 启动失败：`initialized` 保持 False → `sparkle_security_monitor_start_failures_total` 计数 +1 → `logger.exception` ERROR 级 → 异常上抛；main.py 捕获分支由 **warning 升级为 ERROR**（引擎照常起，非致命但可寻）。
3. 运行期死亡：后台协程挂 `add_done_callback`，非取消异常 → `sparkle_security_monitor_background_task_failures_total` +1 + ERROR 日志——监控循环再也不可能静默裸奔。
4. 生命周期收口：新增 `shutdown()`，在 lifespan 关停段（`cache_service.close()` 之前）取消后台协程——此前任务从未真正跑起来，现在会跑了，必须避免关停期 pending-task 告警与 Redis 释放后空转。

### 缺陷 2：`KnowledgeNode.importance` 坏引用 → user_state_v1 整体缺失（核心链路）

**证据对齐**：

- 活栈：`sparkle_fastapi.log` `"Failed to populate user_state_v1 payload: type object 'KnowledgeNode' has no attribute 'importance'"`（50 次）
- 红证复现（修复前新测试）：`AttributeError: type object 'KnowledgeNode' has no attribute 'importance'` —— 逐字一致

**列名对齐证据**：`backend/app/models/galaxy.py:138` `importance_level = Column(Integer, default=1, nullable=False)`（注释：重要性等级 1-5）。坏引用在 `backend/app/services/predictive_service.py` `predict_difficulty` 内两处：

- `KnowledgeNode.importance > topic.importance`（查询构造期即抛 AttributeError）
- `base_hours = topic.importance * 2`（ORM 实例属性访问，同样会炸）

注意混淆源 `models/graph_models.py:38` `KnowledgeNodeVertex.importance` 是另一数据类（AGE 图顶点），与本 ORM 模型无关，未触碰。

**修法（双层防御 + 可观测）**：

1. **L1 列修复**：两处改 `importance_level`，注释同步（1-5 → 2-10 小时，原注释 1-10 是错的）。
2. **L1.5 护栏扩类**：`AttributeError` 加入 `PREDICTION_DATA_ERRORS`（predictive_service 4 处降级护栏共用）。本次事故正是 AttributeError 逃出该护栏炸穿调用方；ORM 属性漂移与既有的 TypeError/ValueError 同属"数据/语义错误"类。降级时仍打 `logger.error`（"难度预测失败"），不是静默。
3. **L2 聚合层降级**：`state_aggregator/service.py::_build_foresight_hint_summary` 包裹 `build_foresight_snapshot`：任何失败 → 返回默认（中性）权重信封 `ForesightHintSummaryValue(hint_text=None, generated_at=None, deviation_count=0, attractor_confidences=())` + `sparkle_user_state_field_build_failures_total{field="foresight_hint"}` 计数 + ERROR 结构化日志。**get_user_state 从此不可能因单字段构建失败而整体缺失**。
4. **payload 层可观测**：`profile_context_service.py::_populate_user_state_v1_payload` 失败分支：`sparkle_user_state_v1_payload_failures_total` 计数 + ERROR 级日志（明示 "user_state_v1 MISSING from context"），替换原一行无指标 warning。

---

## ② 实现清单

| # | 文件 | 改动 |
|---|------|------|
| 1 | `backend/app/core/security_monitor.py` | 模块级新增 2 个 prometheus 计数器（`get_or_create_metric` 约定）；`__init__` 增加 `initialized/initialized_at/_background_tasks`；`initialize(redis=None)` 签名对齐 + try/except（计数+ERROR+上抛）+ 启动成功结构化标记；新增 `get_startup_status()`、`_on_background_task_done()`、`shutdown()` |
| 2 | `backend/app/main.py` | 启动段：成功路径结构化日志含 `get_startup_status()`；失败分支 warning→ERROR（附 `{!r}` 异常）。关停段：`security_monitor.shutdown()` 收口（Redis 释放之前，`cache_service.close` 前插入） |
| 3 | `backend/app/services/predictive_service.py` | `predict_difficulty` 两处 `importance`→`importance_level`（查询 + base_hours，注释修正）；`PREDICTION_DATA_ERRORS` 增加 `AttributeError`（带事故注解） |
| 4 | `backend/app/state_aggregator/service.py` | 新增 import（loguru/prometheus/`get_or_create_metric`）与计数器 `USER_STATE_FIELD_BUILD_FAILURES_TOTAL`；`_build_foresight_hint_summary` 失败降级为默认权重信封+计数+ERROR 日志 |
| 5 | `backend/app/services/profile_context_service.py` | 新增计数器 `USER_STATE_V1_PAYLOAD_FAILURES_TOTAL`；`_populate_user_state_v1_payload` 失败分支 warning→ERROR+计数 |
| 6 | `backend/tests/unit/test_prodfix1_monitor_and_userstate.py` | **新增**，8 个测试（见 ③ 回归节） |

新指标（`/metrics` 出镜，走既有 Instrumentator 通道）：
`sparkle_security_monitor_start_failures_total`、`sparkle_security_monitor_background_task_failures_total`、`sparkle_user_state_field_build_failures_total{field}`、`sparkle_user_state_v1_payload_failures_total`。

---

## ③ 测试与回归（对比法，先基线后改后）

**红证**：新测试 8/8 先跑红，其中两个核心失败异常与生产日志**逐字一致**（见 ①）。

**绿证**：修复后新测试 **8 passed, 0 warnings**：

1. monitor：传参初始化采纳注入 redis + `initialized=True` + 2 后台任务登记 + shutdown 清零；无参兼容；启动失败计数+ERROR+上抛；后台协程运行期死亡计数+ERROR；关停收敛。
2. predictive：正常路径按 `importance_level` 取数（prereq_hi(3) 入选 / prereq_lo(1) 排除 / 时长 4×2.0=8.0 钉死语义）；注入 AttributeError 时降级默认难度（topic_name="Unknown", 0.5）不炸穿。
3. user_state：`build_foresight_snapshot` 抛 AttributeError（模拟原事故）时 `get_user_state` 仍返回完整状态、foresight_hint 为默认权重、计数 +1；`_populate_user_state_v1_payload` 失败计数 +1 + ERROR 日志。

**回归对比法**（同命令同集，改前基线 → 改后）：

- 受影响面 12 个测试文件：`test_state_aggregator_service.py`、`test_predictive_service_productization.py`、`test_predictive_service_extension.py`、`test_predictive_realtime_degrade.py`、`test_foresight_snapshot_schema.py`、`test_foresight_kill_switch.py`、`test_aggregator_schema_v1_8.py`、`test_sqam_predictive_all_dims.py`、`test_security_audit_insert.py`、`test_auth_login_empty_credentials.py`、`test_startup_smoke.py`、`test_profile_context_service.py`
- 基线：**5 failed / 48 passed**（失败清单存 `/tmp/wt179_baseline_failures.txt`，全部为 `test_foresight_snapshot_schema.py::test_foresight_snapshot_hides_hints_when_jitai_not_live` + `test_foresight_kill_switch.py` 4 例——改前即坏，与本卡无关）
- 改后：**5 failed / 60 passed**；失败清单 diff 基线 → **`diff` 输出为空，零新增失败**（`/tmp/wt179_after_failures.txt`）

**静态检查**：改动 5 文件 + 新测试 `ruff check` 全过、`py_compile` 全过。

---

## ④ 冲突面声明与诚实申报

### 冲突面声明（逐个声明零重叠）

| 邻居 | 邻居动土 | 本卡动土 | 结论 |
|------|----------|----------|------|
| wt170 | achievement_engine + Alembic 迁移 + photon 写侧 | main.py / core/security_monitor.py / services/predictive_service.py / services/profile_context_service.py / state_aggregator/service.py + 新测试 | **零重叠**（未触 Alembic、photon、achievement） |
| wt176/177/178 | mobile（Flutter） | 同上（纯 backend） | **零重叠** |
| wt180 | 事件总线 / Go 网关 | 本卡未触 `event_bus.py`、未触 `gateway/`；main.py 仅动 lifespan 的 monitor 启动/关停两段，与 consumer 启动段无交集 | **零重叠** |

### 诚实申报

1. **Sibling 排查（只登记，未扩面修改）**：
   - `backend/app/main.py` lifespan 同型「启动失败吞成 warning」还有三处：PII 加密监听器激活失败（:160 附近，warning）、`_run_working_memory_orphan_cleanup`（warning，一次性清理、非长驻监控）、`redis_search_client.ensure_index`（warning，索引缺失=搜索静默降级）。严重度均低于本卡两缺陷，未动。
   - `backend/app/orchestration/orchestrator.py:373` `create_task(self.langgraph_breaker.initialize())` 为 fire-and-forget 且无 done-callback——启动期失败只会变成 GC 期 "exception was never retrieved"，属同型风险（已核对 `circuit_breaker.py:76` 签名匹配，**非**当前炸法）；`plan_review_service.py:226` 签名匹配无问题。未动。
   - **非 sibling 的同名单（已核实排除，防后来者误报）**：`models/vocabulary.py:34` WordEntry 自有 `importance` 列（合法）；`graph_rag.py:2522` AGE Cypher `node.importance` 与 `graph_sync_worker.py:192` 写入的顶点属性一致（AGE 图顶点属性就叫 `importance`，非 PG 列）；`redis_search_client.py:77` `$.importance` 是 JSON 索引路径（另一数据面）。
2. **PROD-LOG 兄弟线索核对**：报告 ②-9（scheduler loguru %s）、②-7（redis_checkpointer allowlist）为其它卡/噪音类，未动。
3. **行为变更申报**：修复后 SecurityMonitor 两个后台循环（每分钟 `_check_abnormal_patterns`/`_check_system_security`、每小时清理）**首次真正运行**。`_check_system_security` 会在 SECRET_KEY<32 字符或 DEBUG=on 时打 HIGH 告警——生产若配了短 SECRET_KEY，上线后可能出现首波安全告警，**这是预期行为不是回归**。测试环境 `SECRET_KEY=test` 正是该告警的合法对象。
4. **`AttributeError` 进 `PREDICTION_DATA_ERRORS` 的权衡申报**：该扩类作用于 predictive_service 4 个降级护栏，理论上会让未来的 ORM 属性笔误降级为默认值而非上抛；但降级路径带 `logger.error`，且本事故证明该类错误裸奔的代价（user_state_v1 全灭 50 次/无人发现）远高于降级的代价。L2 聚合层计数器可按 field 维度定位。
5. **测试附带说明**：`test_predict_difficulty_uses_importance_level_column` 钉的是当前实现语义（无掌握度记录→mastery 记 0→难度 1.0；时长=importance_level×2×(1+难度)），若产品要改"无记录=中等难度"的语义需另行立项。
6. worktree 内 `backend/app/gen/` 按纪律从主仓拷贝（`git status` 不显示，被 ignore，不入 patch）；收工时保留（随 worktree 生命周期回收）。

---

## ⑤ 收工核查

- [x] 两缺陷修复，红→绿，异常与生产日志逐字对齐
- [x] 启动即验：initialized 标记 + `get_startup_status()` + 结构化成功日志
- [x] 失败不静默：4 个新计数器 + ERROR 级日志（monitor 启动失败 / 后台协程死亡 / 字段构建降级 / user_state_v1 缺失）
- [x] 降级不炸穿：get_user_state 单字段失败 → 完整 user_state_v1 + 默认权重
- [x] 回归对比法零新增（失败清单 diff 为空）
- [x] ruff / py_compile 全过；测试无警告
- [x] 零 commit / 零 push / 零凭据
- [x] 冲突面逐个声明零重叠（wt170 / wt176 / wt177 / wt178 / wt180）
- [x] sibling 只登记未扩面
- [x] 收工清理：`/tmp/wt179-patchcheck`（补丁验证克隆）、`/tmp/wt179_baseline_failures.txt`、`/tmp/wt179_after_failures.txt`、`/tmp/wt179_new_test_backup.py` 已删除；worktree 无遗留进程、无临时产物
- [x] 交付物：`v3-output/PROD-FIX-1/REPORT.md`（本文件）+ `changes.patch`（a2506361 上 `git apply --check` 通过）
