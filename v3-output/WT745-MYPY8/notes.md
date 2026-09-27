# WT745 · mypy 棘轮烧减批八 notes

分支：`agent/node-b/wt745/mypy8`（main @ c4f4d59f 起 worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt745-mypy8`；接替 wt728 批七 1b20a18d，簇选择法学批七/批六）。
口径：`cd backend && python -m mypy app --ignore-missing-imports`（app/gen 在场，自主仓 proto-gen 产物 `cp -RL` 拷贝；venv 复用主仓 backend/.venv，mypy 1.20.2；冷缓存 = 每次独立 `--cache-dir` 于 /tmp）。

## 基线漂移（如实记）

- 任务书口径：合并态基线 **132 错**（环境噪声 ±1）。
- 本卡实测（worktree 冷缓存）：**133 错 / 114 文件**；与 main 同法冷缓存对照 **错误清单 diff 为空**（逐行一致），确认同基。
- 漂移 = **+1**（133 vs 132，落在噪声带内），本卡不改 quality 基线文件（沿批六/批七判例，随收尾流程另行降基线）。

## 簇选择（同族 2 簇：声明面注解 + 同名变量异型复用改名）

**环境实证（本卡新增判例）**：mypy 1.20.2 下「带注解赋值 `x: T | None = <非 Optional 表达式>`」**不发生赋值收窄**——赋值后变量类型即声明类型（用 /tmp 独立 snippet 双例证确认：注解赋值报 union-attr，无注解首绑按右值推断）。故凡后续有非 Optional 消费面的变量，一律走**改名**而非 Optional 注解（中途 3 处首版注解修法被 mypy 复跑当场否决，已改改名并复验）。

1. **声明面 None/Optional 补齐簇（注解为主）**：字段/变量声明与构造不变量矛盾（`= None` 哨兵 + post_init 充值、Optional 载荷流）被 mypy 报 assignment。修法 = 声明处补如实注解或 `field(default_factory=...)`；全部为纯声明/局部改名，零运行时语义变化。其中 security_monitor `timestamp: datetime = None` 为**声明面根修**：改 `field(default_factory=_utcnow)` 并保留 post_init 兜底守卫——全仓 app+tests 构造点 6 处均不显式传 timestamp（grep 实证），默认构造/显式传值/显式传 None 三面行为逐点相同（factory 在 `__init__` 充值 vs post_init 充值，观测面无差）。
2. **同名变量异型复用改名簇**：同一函数内同名变量先后绑定不同类型（互斥分支或先后阶段），mypy 按首绑推断后报后一处 assignment。修法 = 后绑局部改名，作用域不变、求值序不变、值不变。

## 逐处修法分类（注解=纯声明｜改名=局部重命名·零行为变化｜真 bug=0 处）

| # | 文件:行(修后) | 烧减错误位(基线) | 错误码 | 修法 |
|---|---|---|---|---|
| 1 | app/services/jpush_sender_service.py:84 | :97 | assignment | 注解：`self._settings: JPushSettings \| None = None`（补 import JPushSettings；:266/:499 `not x` 守卫早退收窄） |
| 2 | app/core/security_monitor.py:83 | :82 | assignment | 根修：`timestamp: datetime = field(default_factory=_utcnow)`（+import field；post_init 守卫保留；6 构造点均不传 timestamp） |
| 3 | app/orchestration/state_manager.py:86 | :86 | assignment | 注解：`tool_calls_in_progress: list[Any] \| None = None`（post_init 充值；全仓无类外读者） |
| 4 | app/services/plan_progress_service.py:134 | :134 | assignment | 改名：critical 阶段 `lag` → `critical_lag: float \| None = None`（:138 守卫收窄；warning 阶段首绑 `lag` 保留） |
| 5 | app/core/llm_security_wrapper.py:440 | :455 | assignment | 注解：`safe_history: list[dict[str, Any]] \| None = None`（:459 `if safe_history:` 守卫；下游 chat_with_tools 形参 `list[dict] \| None` 相容） |
| 6 | app/services/plan_state_service.py:123 | :123 | assignment | 改名：DB 路径 `state` → `db_state`（缓存路径首绑保留；:125 None 守卫后 3 处消费面随改） |
| 7 | app/orchestration/executor.py:502 | :502 | assignment | 改名+拆绑：else 支 `ctx_permissions = ctx.get(...)`（首绑 Any\|None 不再消费）+ `ctx_run_permissions = ... if isinstance(...) else {}`（按右值推断 dict，2 处 .get 随改；运行时同值同序） |
| 8 | app/api/v1/plans.py:2052 | :2064 | assignment | 注解：`total_mastery: float = 0`（int 字面量 mypy 提升；运行时值不变） |
| 9 | app/services/persona_service.py:75 | :81 | assignment | 注解：`capabilities: dict[str, Any]`（值域如实：float + subjects list / 查询结果 dict；返回 dict[str, Any] 消费面） |
| 10 | app/services/intervention_lifecycle_service.py:420 | :423 | assignment | 注解：`scope: tuple[str, ...] = ("user", ...)`（sink 形参 :654 即 `tuple[str, ...]`） |
| 11 | app/services/share_card_service.py:534 | :540 | assignment | 注解：`current_top: float = top`（textbbox 返回 float；PIL 坐标本就 float 域） |
| 12 | app/signals/aurora_core_session.py:299 | :302 | assignment | 注解提升：bare 声明 `normalized_entry_reason: AuroraCoreSessionEntryReason \| None`（函数局部 bare 注解零字节码；:303 from_context 兜底后 :346 消费面收窄不变） |
| 13 | app/core/llm_router.py:1776 | :1776 | assignment | 改名：非 str 分支 `role_value` → `enum_role_value`（分支内 6 处局部；与 isinstance-str 分支互斥） |
| 14 | app/aurora/runtime_v1/control_surface.py:235 | :235 | assignment | 改名：模型重校后复查 `agenda_priority` → `final_agenda_priority`（3 处局部） |
| 15 | app/aurora/runtime_v1/chat_adapter.py:388 | :388 | assignment | 改名：回退取值 `subject` → `fallback_subject`（3 处局部；pack_id 主路径首绑保留） |
| 16 | app/services/routing_parameter_effectiveness_service.py:111 | :111 | assignment | 改名：gauge 循环 `row` → `eff_row`（8 处局部；首绑 RoutingDecisionLog 循环保留；cache 推导式用 `r` 不受影响） |
| 17 | app/services/policy_patch_service.py:157 | :157 | assignment | 改名：allocation_preference 分支 `mode` → `preferred_mode`（3 处局部；clarification 分支首绑保留） |
| 18 | app/services/exam_sprint_review_service.py:788 | :788 | assignment | 改名：underprepared_topics 循环 `label` → `topic_label`（3 处局部；`_first_non_empty -> str \| None` 与 `_strip -> str` 异型） |
| 19 | app/services/profile_context_service.py:661 | :661 | assignment | 改名：fallback timeline 块 `delta` → `timeline_delta`（3 处局部；:592 首绑保留） |
| 20 | app/services/outcome_ledger_service.py:829 | :829 | assignment | 改名：第二循环 `refs` → `task_refs`（3 处局部；:776 首绑 `refs: list[tuple[str, str, str]]` 注解面保留为真） |

**修法分类统计：注解/bare 声明提升 9 处｜改名/局部拆绑 11 处（含 1 处声明面根修 default_factory）｜真 bug 0 处｜cast 0 处｜新增 type: ignore 0 处｜bare-Any 注解 0 处。**

## 前后清单对照

- 修前清单：133 错（/tmp/wt745_mypy_base.txt，会话产物不入库）；与 main 同法 diff 为空。
- 修后：**113 错 / 96 文件**。
- diff 核验（行号无关）：删除 20 行 = 烧减 20 错，**新增 0 错**（0 行添加）。
- 净烧减：**133 → 113（-20）**。

## 验证

- mypy：113（相对实测基线 133 严格下降 20，零新增）。
- 受影响模块测试（路径先 find/grep 后跑，SECRET_KEY 沿 scripts/run_all_rule_guards.sh 合成键 `rule-guard-secret-0123456789abcdef`；worktree 无 .env，DBG 合规落 sqlite）：
  - 批一 jpush/security_monitor/FSMState/security_wrapper：`tests/unit/test_jpush_sender_service.py tests/unit/test_security_audit_insert.py tests/unit/test_prodfix1_monitor_and_userstate.py tests/orchestration/test_fsm_state_real.py tests/unit/test_state_manager_concurrency.py tests/contract/test_state_manager_contract.py tests/unit/test_llm_security_wrapper.py tests/unit/test_llm_security_wrapper_forwarding.py tests/unit/test_llm_wrapper_signature_contract.py` → **89 passed**
  - 批二 plan_state/plans API/persona/lifecycle/share_card/aurora_core_session：`tests/services/test_plan_state_service.py tests/unit/test_plan_state_service_jsonb.py tests/api/test_plans_api.py tests/services/test_persona_service.py tests/services/test_intervention_lifecycle_service.py tests/contract/test_intervention_lifecycle_contract.py tests/unit/test_share_card_service.py tests/unit/test_aurora_core_session_entry.py` → **149 passed**
  - 批三 llm_router/aurora_runtime/policy_patch/exam_sprint/profile_context/outcome_ledger：`tests/core/test_llm_router_policy.py tests/unit/test_aurora_runtime_v1.py tests/unit/test_routing_parameter_proposal_service.py tests/services/test_policy_patch_service.py tests/contract/test_policy_patch_contract.py tests/unit/test_exam_sprint_review_service.py tests/services/test_profile_context_service.py tests/services/test_outcome_ledger_service.py tests/unit/test_outcome_ledger_contract.py` → **218 passed**
  - 批四 executor/失败恢复/phase_b（plan_progress 消费面）：`tests/unit/test_tool_executor_observability.py tests/unit/test_x09_failure_recovery.py tests/unit/test_x06_tool_call_safety.py tests/unit/test_executor_execution_observer.py tests/unit/test_executor_tool_locale_signature.py tests/unit/test_phase_b_revision_summary.py` → **69 passed**
  - 合计 **525 passed（零失败）**。
- ruff：20 触达文件 `ruff check` **All checks passed**。
- 行长：diff 全部新增行 ≤120 列（脚本实证零超长）。

## 台账

- 未新开 FIX 行：本卡 20 处全部为注解/改名/声明面校正，**零运行时语义变化、零真类型 bug**（V3-FIX-473/474 保持空闲，grep 实证 0 占用）。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过：320 行 V3-FIX 行，8 裸管形态合法，ID 无重号，状态枚举合法，零 FAIL**。

## 卷宗

- 修前/修后 mypy 全清单存会话 /tmp（wt745_mypy_base.txt / wt745_mypy_after.txt / wt745_mypy_main.txt），不入库；本 notes 前后对照为准。
- diff 自审：56 insertions / 55 deletions，20 文件，逐 hunk 与上表一一对应；无 cast、无新增 ignore、无 bare-Any 注解、无表达式改写。
- 遗留观察（不改，供后续批次）：executor.py:1687 `asyncio.sleep(delay)`（retry_decision 返回 `(bool, float | None)`，should_retry⟺delay 非 None 的关联性 mypy 不可达，诚实修法需运行时面改动）与 error_book_signal_processor.py:101（Counter 值域 float 与 Counter[str] 默认 int 值型冲突，诚实修法需换容器类型=运行时变化）均非零语义可修，留待有运行时授权的卡片。
