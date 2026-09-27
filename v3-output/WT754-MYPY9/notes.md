# WT754 · mypy 棘轮烧减批九 notes

分支：`agent/node-b/wt754/mypy9`（main @ 68dc7e20 起 worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt754-mypy9`；接替 wt745 批八 31d4cf3d，簇选择法学批八/批七）。
口径：`cd backend && python -m mypy app --ignore-missing-imports`（app/gen 在场，主仓 proto-gen 产物 `cp -RL` 拷贝；venv 复用主仓 backend/.venv，mypy 1.20.2；冷缓存 = 每次独立 `--cache-dir` 于 /tmp）。

## 基线确认

- 任务书基线 **113 错**（批八后实测口径）。本卡实测（worktree 冷缓存）：**113 错 / 96 文件**；与 main 同法冷缓存对照，归一化（剥行号）清单 **diff 为空**（逐行一致），确认同基。
- 修后：**94 错 / 83 文件**。

## 簇选择（三族：声明面注解/签名 + 同名异型复用改名 + 安全收窄）

沿批八判例：mypy 1.20.2 注解赋值不发生赋值收窄，有非 Optional 消费面一律改名；本卡新增实证一条——mypy 对 `import websockets` 不解析子模块属性链，`websockets.asyncio.client.ClientConnection` 注解必须显式 `from websockets.asyncio.client import ClientConnection`（首次修法被 mypy 复跑当场否决报 name-defined，改显式 import 后通过；运行时类对象存在性已用 venv python 亲证）。

## 逐处修法分类（注解=纯声明｜改名=局部重命名·零行为变化｜收窄=既有语义内的守卫/别名｜真 bug=0 处顺手修，2 处停手登记）

| # | 文件:行(修后) | 烧减错误位(基线) | 错误码 | 修法 |
|---|---|---|---|---|
| 1 | app/services/llm_service.py:625 | :625 | assignment | 改名：非 str 分支 `role_value` → `enum_role_value`（分支内 6 处局部；isinstance-str 分支首绑保留，与批八 llm_router 同形） |
| 2 | app/services/card_protocol/parameter_compiler.py:249 | :249 | assignment | 改名：compass 约束段 `max_tasks` → `constraint_max_tasks`（3 处局部；:233 `int(params.get(...))` 首绑保留） |
| 3 | app/api/v2/agent_graph.py:18 | :18 | assignment | 注解：`session_id: str \| None = None`（pydantic 默认值本就 None；消费点 :62 `request.session_id or uuid4()` 已容 None，声明面对齐运行时） |
| 4 | app/services/llm_service.py:390 | :505 | assignment | 注解：`_provider_error: str \| RuntimeError \| None`（值域如实：:505 赋 RuntimeError 对象；消费面仅 is-None 判断与 f-string `or` 兜底，三型兼容） |
| 5 | app/services/metacognition_service.py:183 | :183 | valid-type | 注解：`dict[datetime.date, list[float]]` → `dict[date, list[float]]`（`date` 顶部已 import，原写法把 datetime 类的 `.date` 方法当类型） |
| 6 | app/services/stt/providers/xunfei_provider.py:138 | :137 | name-defined | 注解：`websockets.WebSocketClientProtocol`（16.0 已移除的 legacy 名）→ 显式 import `ClientConnection`（websockets.asyncio.client，:182 `websockets.connect` 新实现实际产出型；`_drain_messages` 体仅用 `.recv()`） |
| 7 | app/scenario_packs/registry.py:55 | :54 | valid-type | 注解：`load_from_directory` 返回注解 `list[...]` → `builtins.list[...]`（类内 `def list` 方法名遮蔽内置名，仅类作用域内此签名命中；`__future__ annotations` 下零字节码；`import builtins` 补入） |
| 8 | app/services/translation_service.py:87 | translation_tool:160 | arg-type | 签名放宽：`translate(user_id: UUID \| None)` → `UUID \| str \| None`（下游 `_evaluate_signals` 形参本即 `UUID \| str \| None` 且内部做 UUID 转换；调用方传 str 为既有事实） |
| 9 | app/learning/ab_test_framework_enhanced.py:51/:55 | experiments:168+:342 | arg-type ×2 | 签名放宽：`create_experiment(description: str \| None, created_by: str \| None)`（ABExperiment 模型 `description`/`created_by` 列均 nullable=True，声明面对齐持久层；其余调用方传 str 仍相容） |
| 10 | app/services/tool_history_service.py:58/:86 | :71 | arg-type | 注解：`Callable[[], Awaitable[None]]` → `Callable[[], Coroutine[Any, Any, Any]]`（两处声明；唯一入队点 lambda 包 `async def` 产出协程对象，与 achievement_engine.py:80 既有同模式声明一致） |
| 11 | app/services/exam_sprint_intake_service.py:988 | :832 | arg-type | 注解：`_recommended_mode(...) -> str` → `-> TargetMode`（复用 schemas/exam_sprint 既有 `Literal['pass','hold','high_score']` 别名；函数体仅返回这三个字面量） |
| 12 | app/orchestration/routing_parameter_registry.py:229 | :246 | arg-type | 安全收窄：`_load_experiment_overrides` 入口 `user_id = self._user_id; if user_id is None: return None`，:246 改用局部 `user_id`（调用点 :204 已守 `self._user_id and db`，早退分支不可达，跨方法收窄边界补齐；零行为变化） |
| 13 | app/api/v1/experience/community_router.py:263 | :263 | operator | 安全收窄：`partner_last_checkin = _as_naive_utc(...)` 提局部 + `is None or` 判断（`_as_naive_utc` 非 None 输入恒返非 None（透传/归一化），新 None 分支不可达；与原单行短路逐值相同） |
| 14 | app/aurora/friction_diagnosis.py:1622 | :1623 | index | 安全收窄：`preference is not None and preference in BUDGETS` 前置短路（`None in Mapping` 本为 False，求值序变化结果不变；is-not-None 收窄穿透 `in` 使索引合法） |
| 15 | app/services/error_knowledge_linker.py:363 | :363 | arg-type | 安全收窄：`pack_prefix` 条件表达式改 `pack_key is not None and pack_key in _PACK_PREFIXES` 守卫（与 `scoped` 布尔同语义；`.get` 调用条件不变、值不变；`scoped` 及循环内比较保留） |
| 16 | app/api/v1/plans.py:576 | :625 | operator | 安全收窄：`total = count_result.scalar() or 0`（count(*) 标量恒非 None，`or 0` 实不可达；同文件 :1798 既有同形惯例） |
| 17 | app/api/v1/experience/goal_router.py:348 | :348 | no-any-return | 注解局部：`isoformatted: str = value.isoformat()` 后返回（hasattr 分支保证 isoformat 存在，date/datetime 的 isoformat 返回 str；Any→str 注解赋值收口返回型） |
| 18 | app/services/profile_event_consumer.py:293 | :293 | no-any-return | 注解局部：`library: SeedLibrary \| None = await db.get(...)` 后返回（db: Any 的返回收口到声明返回型） |

**修法分类统计：注解/签名/注解局部 12 处（含 #9 一处双错）｜改名 2 处｜安全收窄 5 处 → 合计烧 19 错｜真 bug 0 处顺手修（另 2 处停手登记 V3-FIX-491/492，见下）｜cast 0 处新增｜新增 type: ignore 0 处｜bare-Any 注解 0 处。**

## 真 bug 停手登记（不顺手修）

1. **V3-FIX-491（P2）**：app/api/internal/auto_degrade.py:152-153——`event_bus.publish(SLOAutoResponseAuditEvent(...))` 单实参误用 `publish(event_type: str, payload: dict)` 签名，运行时 TypeError 被 `except Exception` 吞掉，**SLO 自动响应审计事件从未成功发布**。属运行时行为修复，超出本批注解/改名权限，登记 OPEN。
2. **V3-FIX-492（P3）**：app/orchestration/plan_review_service.py:939——`daily_hours < 3` 缺 None 守卫（:919 `params.get("daily_hours")` 缺键即 None，:934 守卫只护 `<2` 分支），expert/master+文科+缺参路径 TypeError 崩；:948 同类比较已有守卫，:939 漏网。同上登记 OPEN。

（两号按任务书指定备用位 491/492 占用；登记前 grep 复核 v3/ v3-output/ 0 命中、在册最高 481。`ledger_union_merge.py --verify` 通过。）

## 前后清单对照

- 修前清单：113 错（/tmp/wt754_mypy_base.txt，会话产物不入库）；与 main 同法 diff 为空。
- 修后：**94 错 / 83 文件**。
- diff 核验（行号无关）：删除 19 行 = 烧减 19 错，**新增 0 错**（`comm -13` 为空）。
- 净烧减：**113 → 94（-19）**，与选中数（18 处修点 / 19 错）一致。

## 验证

- mypy：94（相对基线 113 严格下降 19，零新增）。
- 受影响模块测试（路径先 find/grep 后跑，分 5 批；SECRET_KEY 沿 scripts/run_all_rule_guards.sh 合成键 `rule-guard-secret-0123456789abcdef`；worktree 无 .env，合规落 sqlite）：
  - 批一 tool_history/translation/ab_test/exam_intake：`tests/unit/services/test_tool_history_service.py tests/core/test_ff_convergence_sites.py tests/services/test_translation_service.py tests/services/test_translation_signals.py tests/unit/test_ab_test_framework.py tests/unit/test_exam_sprint_intake_service.py tests/unit/test_exam_sprint_intake_concurrency.py` → **54 passed**
  - 批二 llm_service/xunfei/error_linker/routing_registry：`tests/test_llm_service_streaming.py tests/services/stt/providers/test_xunfei_provider.py tests/unit/test_error_knowledge_linker.py tests/unit/test_routing_parameter_proposal_service.py` → **22 passed**
  - 批三 agent_graph/friction/scenario_pack/profile_consumer/event_ack：`tests/api/test_agent_graph_api.py tests/unit/test_a03_friction_diagnosis.py tests/unit/test_scenario_pack_names_zh.py tests/unit/services/test_profile_event_consumer.py tests/unit/test_event_ack2_reliability.py` → **132 passed**
  - 批四 plans/goal_router/bias：`tests/api/test_plans_api.py tests/unit/test_goal_router_progress_projection.py tests/unit/test_goal_today_view.py tests/unit/test_b2_criteria_status_endpoint.py tests/unit/test_bias_unify_cold_start.py` → **45 passed**
  - 批五 accountability（community_router 消费面）：`tests/api/test_accountability_system_api.py` → **13 passed**
  - 合计 **266 passed（零失败）**。
- ruff：17 触达文件 `ruff check` **All checks passed**。
- 行长：diff 全部新增行 ≤120 列（awk 逐行实证零超长）。

## 台账

- 新开 2 行（真 bug 登记，非本批顺手修）：V3-FIX-491（P2，auto_degrade 审计事件恒失败）、V3-FIX-492（P3，plan_review daily_hours 未守卫崩），均 OPEN 待有运行时授权的卡片收口。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过：329 行 V3-FIX 行，ID 无重号，状态枚举合法，零 FAIL**。

## 卷宗

- 修前/修后 mypy 全清单存会话 /tmp（wt754_mypy_base.txt / wt754_mypy_base_lines.txt / wt754_mypy_after.txt），不入库；本 notes 前后对照为准。
- diff 自审：47 insertions / 31 deletions，18 文件（17 代码 + 1 台账），逐 hunk 与上表一一对应；无 cast、无新增 ignore、无 bare-Any 注解；安全收窄 5 处均为既有语义内的守卫前置/局部别名，逐处标注值等价论证。
- 遗留观察（不改，供后续批次）：
  - `sufficiency_judge_schema.py:12` `ScoreBucket = Literal[0.0, 0.5, 1.0]`——PEP 586 禁 float 字面量进 Literal，诚实修法需改类型域（枚举/int 桶）= 语义变化，非零语义可修；
  - `int(Any|None)` 族中 try/except 内点位（checkpoint_nudge:587/aurora_control 等）`or 0` 化**不**恒等（0 与 None 分流不同分支），仅 :1211 一处可证恒等未纳入（为控表达式改写面）；
  - `streak_signal_processor.py:46` 传 `date` 给 `recency_weight(observed_at: datetime|None)`——模型 `Mapped[date|None]` 与 `DateTime` 列声明自相矛盾且运行时值域混杂（achievement_engine 写 `.date()`），属模型声明面纠缠，留待统计模块卡片（KNOWN_CODE_DEBT_LEDGER 管辖）。
