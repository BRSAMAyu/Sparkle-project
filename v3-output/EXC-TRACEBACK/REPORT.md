# EXC-TRACEBACK 收工报告 — loguru `exc_info=True` 死参全量迁移

- 卡号：EXC-TRACEBACK（wt187 LOGURU-BATCH 登记项，C 纵队生产级线）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt193`（基线 HEAD `418f3493`）
- 日期：2026-09-23
- 交付物：本报告 + `changes.patch`（同目录）；零 commit、零 push、零凭据

---

## ① 扫描清单（修前全量 + 每处裁决）

**扫描方法**：`/usr/bin/grep -rn "exc_info" --include="*.py"` 全仓（排除 `gen/`、venv）+ AST 精确分类器（解析每个 `.py`，定位所有带 `exc_info` keyword 的 `Call` 节点，按 import 绑定判定 logger 来源、按 ExceptHandler span 判定是否在 except 块内）。

**总量**：grep 命中 269 处（backend + scripts，不含 `tests/`）；AST 判定为**调用点**的共 267 处，裁决如下：

### A. loguru 死参（kwarg 被吞、堆栈从未落日志）→ 全修：234 处 / 53 文件

特征全量核实：全部为 `logger.<level>(..., exc_info=True)`（无非布尔变体、无 `logger.exception`/`logger.log` 形制、`exc_info` 一律是最后一个 kwarg、**全部位于 except 块内（活跃异常保证存在）**）。

| 级别 | 处数 |
|---|---|
| warning | 108 |
| debug | 68 |
| error | 58 |

**wt187 申报的 5 处全部在内并已修**：`api/v1/growth.py:104`、`aurora/runtime_v1/l2_intervention.py:344`、`services/llm_service.py:258`、`signals/low_yield_guard.py:135`、`signals/spine_orchestrator.py:1632`。

53 文件分布（处数）：`signals/spine_orchestrator.py` 80、`services/agent_grpc_service.py` 32、`services/scheduler_service.py` 16、`aurora/runtime_v1/correction_feedback.py` 9、`aurora/runtime_v1/aurora_spine_confluence.py` 8、`learning/self_model_bridge.py` 6、`core/security_monitor.py` 4、`signals/directive_store.py` 4、`signals/self_model.py` 4、`learning/outcome_consumer.py` 4、`core/cost_controller.py` 3、`signals/card_store.py` 3、`services/achievement_engine.py` 3、`services/llm_service.py` 3、`services/nudge_service.py` 3、×2 组 14 文件：`agents/standard_workflow.py`、`api/v1/assets.py`、`api/v1/community.py`、`api/v1/ingestion.py`、`api/v1/simulation.py`、`aurora/runtime_v1/l3_full_core.py`、`aurora/runtime_v1/l4_async.py`、`aurora/runtime_v1/reply_option_injector.py`、`services/chat_signal_collector.py`、`services/fme_l3_closure_bridge.py`、`services/ml/recall_ranker.py`、`services/notification_push_service.py`、`signals/outcome_recorder.py`、`main.py`；其余 24 文件各 1：`agents/enhanced_orchestrator.py`、`agents/graph/nodes/review_nodes.py`、`api/v1/accountability.py`、`api/v1/growth.py`、`api/v1/multi_agent.py`、`api/v1/scenario_packs.py`、`aurora/core_session.py`、`aurora/runtime_v1/l2_intervention.py`、`core/cost_wvpl_metrics.py`、`services/achievement_event_consumer.py`、`services/community_signal_bridge.py`、`services/document_service.py`、`services/fme_strategy_change_emitter.py`、`services/notification_center_service.py`、`signals/aurora_core_session.py`、`signals/causal_trace_store.py`、`signals/low_yield_guard.py`、`signals/skill_lifecycle.py`、`tasks/absence_scan_task.py`、`tools/translation_tool.py`、`backend/grpc_server.py`、`backend/test_grpc_client.py`、`backend/test_grpc_simple.py`、`backend/test_websocket_client.py`。

### B. stdlib logging 正确用法 → 不动：33 处（逐一核实 getLogger 绑定）

| 文件 | 处数 | 核实依据 |
|---|---|---|
| `api/v1/aurora.py` | 10 | `logger = logging.getLogger(__name__)`（:27），无 loguru import |
| `services/theater/prediction_theater_service.py` | 10 | `logging.getLogger`（:43） |
| `services/streak_quality.py` | 5 | `logging.getLogger`（:19） |
| `workers/expansion_worker.py` | 3 | `logging.getLogger`（:17） |
| `api/v1/error_book.py` | 2 | `_log = logging.getLogger`（:60）+ `logging.getLogger(__name__).warning`（:107） |
| `core/pending_actions.py` | 1 | `logging.getLogger`（:11） |
| `core/kill_switch.py` | 1 | `_logger = logging.getLogger`（:10） |
| `core/task_manager.py` | 1（`self._logger`:301） | 模块/实例均 stdlib，原行内注释亦声明"stdlib logging：exc_info 有效" |
| `services/evidence/fusion_engine.py` | 1 | `logging.getLogger`（:18） |
| `tests/unit/test_tracing_export_config.py` | 2 | 测试内构造 stdlib `LogRecord`（`exc_info=(type(exc), exc, None)`），stdlib 语义本身即是测试对象 |
| `models/__init__.py` | 2 | `logging.getLogger(__name__).debug(...)`（直呼，:245/:283） |
| `core/tracing.py` | （非调用） | 读取 `record.exc_info` 字段，非传参 |

### C. 非调用/无关出现 → 不动

- `pytest.raises(...) as exc_info` 测试变量、`__aexit__(self, *exc_info)` 签名参数：约 40 处（tests/ 下），非日志调用。
- `scripts/check_duplicate_code_blocks.py:56`：字符串样板标记 `"exc_info=True)"`，非调用；迁移后其作为重复块标记仍有效。
- `tests/orchestration/test_r2_orchestration_fixes.py`：R2-04 既有守卫（orchestration 包），本卡未触碰 orchestration（其内 exc_info 已清零），守卫继续有效。

## ② 实现清单

1. **迁移形制**：`logger.<level>(..., exc_info=True)` → `logger.opt(exception=True).<level>(...)`，逐处保留原消息形制（f-string、`{}` 占位、`%s` 皆原样——`%s` 形制属 wt187 另册债务，本卡不动消息、只动堆栈语义）。
   - 选 `logger.opt(exception=True)` 而非 `logger.exception`：全部 234 处位于 except 块内（AST ExceptHandler span 全量核实），`opt(exception=True)` 在 warning/debug/error 各级别通用且不改变级别语义；`logger.exception` 会强制 ERROR 级别，不适用。
2. **实现方式**：AST 驱动的文本手术（keyword 节点自带行列坐标 → CPython 一致的 `\n` 行表 + UTF-8 字节列换算为绝对偏移；自底向上逐调用切除 `exc_info=True` 及前置逗号、在 `logger.` 后插入 `opt(exception=True).`），每处 5 重断言（根名必须是 loguru `logger`、kwarg 文本恰为 `exc_info=True`、存在前置逗号、非唯一实参、改后 `ast.parse` 语法守卫），一次通过 234/234。
3. **超长行治理**：迁移净变化 +5 字符/处（去 15 增 20）。全量改后行扫描发现 3 行新越 120（security_monitor ×2：119→124；agent_grpc_service：116→121），已手工折行；另 `aurora/runtime_v1/l2_intervention.py` 1 行修前已 128（本就超限），一并折行至合规。改后新增行 max = 120。
4. **新增测试**：`backend/tests/unit/test_loguru_exc_info_migration.py`（3 用例全过）：
   - `test_no_loguru_exc_info_in_loguru_sources`：全仓守卫（AST 精确判定 loguru 绑定文件，stdlib 文件自动豁免，不会误伤）；
   - `test_migrated_path_attaches_traceback`：行为断言——驱动真实迁移路径（`cost_wvpl_metrics._daily_spend_all_categories` 除道路径，monkeypatch 预算闸门必炸），loguru capture 断言 `record.exception` 非空、`ValueError` 帧出现在 `traceback.format_exception` 输出、渲染文本含 Traceback/异常消息（堆栈确实附加）；
   - `test_dead_kwarg_exc_info_is_swallowed_by_loguru`：死参语义存档——直传 `exc_info=True` 时 `record.exception is None`，钉死旧缺陷语义防回潮。

## ③ 冲突面声明

本卡改动 = 53 个 backend 文件的日志行（+1 个新增测试文件）。对照声明：**wt178=mobile、wt192=eventbus 测试、wt194=纯研究——与本卡零重叠**（本卡不触碰 mobile/、不触碰 eventbus 测试、无研究产物）。52 个改动文件位于 `backend/app/**`，另有 `backend/grpc_server.py` 与 3 个 backend 根部手动联调脚本（`test_grpc_client/simple/websocket_client.py`）；orchestration 包零触碰（`git diff --name-only | grep orchestration` = 0）。

## ④ 诚实申报

1. **行为变化如实定性**：本卡是行为新增（234 处日志在异常时终于会附 traceback）。已评估副作用面：① 量级——这些分支全是异常降级路径，日志量=异常发生量；② 敏感信息——loguru 的 backtrace 只含代码帧与异常链，**不含局部变量值**（loguru 默认 `backtrace=False, diagnose=False` 时帧内变量不展开；本仓 loguru 配置未开启 diagnose），不引入 PII 泄漏面新增；③ 性能——仅在异常路径多渲染一段文本，热路径零改动。
2. **wt187 申报 5 处 vs 实修 234 处**：以我的扫描为准（卡面授权），wt187 的 5 处清单是其卡片触达文件的子集，无矛盾。
3. **`%s` 形制未动**：部分迁移点（如 `growth.py:104`）消息用 `%s` 占位（loguru 下会原样打印占位符），该债属 wt187 LOGURU-BATCH 的 %s 册，本卡严格只动 exc_info，消息逐字保留。
4. **基线对比中的既有失败**（与本卡无关、修前修后逐字节一致）：
   - `tests/unit/test_signal_spine.py` 10 个失败（guide-json/protocol 旧债）；
   - `test_calibration_receipt.py`、`test_r2_orchestration_fixes.py`、`test_prodfix1_monitor_and_userstate.py`、`test_security_audit_insert.py` 4 文件收集错误——本 worktree 未生成 `app/gen`（`make proto-gen` 产物 gitignore），非本卡引入；orchestration 守卫因此无法在本 worktree 执行，但 orchestration 包零改动 + 包内 exc_info 修前已清零（R2-04），风险为零。
5. **一次性迁移脚本未入库**：AST 分类器/迁移器为 /tmp 一次性工具，方法论已在本报告②.2 完整描述，产物由守卫测试永久固化。

## ⑤ 收工核查

- [x] 修后全仓 AST 扫描 = **0** 处 loguru 侧 `exc_info`（含 backend 根部 4 个脚本）
- [x] 新增守卫 + 行为单测 3/3 通过（`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:"` 下执行）
- [x] 对比法零新增：定向两轮（10 文件 1058 项：1048 passed/10 failed/2 errors；5 文件：24 passed/2 errors）基线 vs 修后**逐条一致**，`diff` 为空
- [x] stdlib 33 处 + 非调用出现全部原样保留（`git diff` 不含任一 keeper 文件）
- [x] 改后行宽 ≤120（新增行 max=120）
- [x] 零 commit / 零 push / 零凭据；交付物仅 `v3-output/EXC-TRACEBACK/{REPORT.md, changes.patch}` + 正式代码改动 + 新测试
- [x] 收工清理：`/tmp/exc-traceback-wt193`（含基线克隆、日志、脚本）已删除；worktree 内无构建产物、无遗留进程
