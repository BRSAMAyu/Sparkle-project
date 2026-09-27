# WT728 · mypy 棘轮烧减批七 notes

分支：`agent/node-b/wt728/mypy7`（main @ e85eec52 起 worktree；接替 wt723 同卡复航）。
口径：`cd backend && ./.venv/bin/python -m mypy app --ignore-missing-imports`（app/gen 在场，自主仓 proto-gen 产物同步拷贝；venv 复用主仓 backend/.venv）。簇选择法学 wt711（批六 5fad1b85，v3-output/WT711-MYPY6/notes.md）。

## 基线漂移（如实记）

- 任务书口径：合并态基线 **146 错**。
- 本卡实测（main HEAD e85eec52 新开 worktree）：**147 错 / 122 文件**。
- 漂移 = **+1**（147 vs 任务书 146），本卡不改 quality 基线文件（沿批六判例，随收尾流程另行降基线）。

## 簇选择（同族 3 小簇，注解/改名为主 + 1 处声明面根修）

1. **异构 payload dict 声明补齐簇 ×8**：dict 字面量被 mypy 按首组值推断过窄（如 `dict[str, str]`），随后写入 dict/list 等异构值报 assignment。修法 = 声明处补 `dict[str, Any]` 精确注解（值域本就是任意 JSON 式载荷，str 键 + str/dict/list 值；8 个文件均已 `from typing import Any`，零新增 import、零运行时变化）。这不是 Any 糊弄：类型是值域的如实描述，未用 cast、未加 ignore、未改任何表达式。
2. **同名变量异型复用改名簇 ×4**：同一函数内同名变量先后绑定不同类型（mypy join 后报后一处）。修法 = 分支内局部改名，作用域不变、求值序不变、值不变，零运行时语义变化。
3. **ModelHealthState.cooldown_seconds 声明面根修 ×2**：字段声明 `float | None = None`（None 哨兵）与 `__post_init__` 充值不变量矛盾——构造后恒为正数（本类内不变量），record_failure 的 `* 2.0` 与 check_recovery 的 `>=` 被 None 位误报 operator。修法 = 声明改 `float = 0.0` + `__post_init__` 守卫 `is None` → `not`（0 为待充值哨兵）。安全性实证：全仓 app+tests 构造点仅 `ModelHealthState()` 无参（llm_router.py:1651/1663 + 4 个测试文件），`cooldown_seconds` 无任何类外读者；无参构造两版可观察行为逐点相同（post_init 均解析到 RECOVERY_SECONDS）。唯一分歧面是显式传 0.0 构造（无任何调用方；旧代码留 0.0 本就会在下一次比较中立即误判 probation）。修后 `:321`、`:357` 两错随声明消除。

## 逐处修法分类（注解=纯声明｜改名=分支局部重命名·零行为变化｜真 bug=0 处）

| # | 文件:行(修后) | 烧减错误位 | 错误码 | 修法 |
|---|---|---|---|---|
| 1 | app/services/plan_state_service.py:575 | :584 | assignment | 注解：`feedback_entry: dict[str, Any]`（后续写入 applied_adjustment dict） |
| 2 | app/orchestration/adaptive_replanner.py:2310 | :2319 | assignment | 注解：`entry: dict[str, Any]`（同款） |
| 3 | app/orchestration/context_sources.py:377 | :386 | assignment | 注解：`payload: dict[str, Any]`（to_dict 内 contenders list 写入） |
| 4 | app/api/v1/plans.py:1682 | :1691 | assignment | 注解：`response: dict[str, Any]`（daily_first_reward dict 写入） |
| 5 | app/orchestration/session_state_mixin.py:327 | :337 | assignment | 注解：`dual_core_snapshot: dict[str, Any] = {}`（空字面量按后续值推断过窄） |
| 6 | app/services/memory_eval_service.py:166 | :176 | assignment | 注解：`metrics: dict[str, Any]`（float 指标 + returned_counts dict；`_case_score(metrics)` 形参 dict[str, float] 与 Any 值兼容，调用面不受影响） |
| 7 | app/tools/companion_tools.py:134 | :144 | assignment | 注解：`data: dict[str, Any]`（relationship_profile/recent_revisions 异构写入） |
| 8 | app/tools/growth_strategy_tools.py:266 | :274 | assignment | 注解：`data: dict[str, Any]`（recent_changes 写入，同款） |
| 9 | app/services/skill_store/service.py:97 | :97 | assignment | 改名：activation_conditions 分支 `normalized` → `normalized_conditions`（分支内 3 处局部） |
| 10 | app/services/skill_store/service.py:103 | :101 | assignment | 改名：examples 分支 `normalized` → `normalized_examples`（同款） |
| 11 | app/services/tool_history_service.py:287 | :287 | assignment | 改名：flash_capsule 分支 `details` → `capsule_details`（前一 notes 分支 details 为 list，两分支互斥 return） |
| 12 | app/orchestration/response_builder.py:1235 | :1248 | assignment | 改名：focused_memory 分支计数 dict `summary` → `focused_memory_counts`（situation_brief 分支的 str `summary` 保留，1248 即后者绑定面） |
| 13 | app/core/llm_router.py:271 | :321 | operator | 根修：`cooldown_seconds: float \| None = None` → `float = 0.0`（0=待 post_init 充值哨兵；构造后恒正不变量落声明） |
| 14 | app/core/llm_router.py:298 | :357 | operator | 根修（同 #13）：守卫 `if self.cooldown_seconds is None:` → `if not self.cooldown_seconds:` |

**修法分类统计：注解 8 处｜改名 4 处｜声明面根修 2 处｜真 bug 0 处｜cast 0 处｜新增 type: ignore 0 处。**

## 前后清单对照

- 修前清单：147 错（/tmp/wt728_mypy_base.txt，会话产物不入库）。
- 修后：**133 错 / 114 文件**。
- diff 核验（行号无关归一后）：删除 14 行 = 烧减 14 错，**新增 0 错**（0 行添加）；无行号平移残留（本卡全部 hunk 均不新增/删除可移动行，仅 skill_store 包行 +2 使既有长行 149→151 平移，错误清单无移位项）。
- 净烧减：**147 → 133（-14）**，达成 <146 棘轮目标。

## 验证

- mypy：133（<146 棘轮目标达成，且相对实测基线 147 严格下降）。
- 受影响模块测试（路径先 find/grep 后跑，SECRET_KEY 沿 scripts/run_all_rule_guards.sh 合成键 `rule-guard-secret-0123456789abcdef`；worktree 无 .env，DBG 合规落 sqlite）：
  - 批一 llm_router 健康面：`tests/unit/test_llm_router_health_tracking.py tests/unit/test_e07_health_hysteresis.py tests/unit/test_llm_health_dual_source_reset.py tests/services/test_capability_claims_realism.py tests/core/test_llm_router_policy.py tests/unit/test_e07_adaptive_routing.py` → **72 passed**
  - 批二 plan_state/skill_store/tool_history/memory_eval：`tests/services/test_plan_state_service.py tests/unit/test_plan_state_service_jsonb.py tests/services/test_plan_feedback_decision_vocab.py tests/unit/test_skill_store_service.py tests/unit/services/test_tool_history_service.py tests/unit/test_memory_eval_service.py tests/memory_eval/test_memory_eval_gate.py` → **77 passed**
  - 批三 response_builder/session_state_mixin/context_sources：`tests/orchestration/test_response_builder_semantic_meta.py tests/unit/orchestrator/mixins/test_response_builder_mixin.py tests/unit/orchestrator/mixins/test_session_state_mixin.py tests/unit/test_context_sources.py tests/unit/test_context_source_contract.py tests/unit/test_context_pack_sources.py` → **77 passed**
  - 批四 tools/adaptive_replanner：`tests/tools/test_companion_tools.py tests/tools/test_growth_tools.py tests/unit/test_adaptive_replanner_cognitive_trigger.py tests/unit/test_adaptive_replanner_evolution.py tests/unit/test_adaptive_replanner_stage34.py tests/unit/test_c03_adaptive_replanner_wiring.py tests/services/test_adaptive_replanner_seed_cohort_filter.py` → **43 passed**
  - 批五 plans API + llm_router 路由族：`tests/api/test_plans_api.py tests/unit/test_plan_archive_days_ahead_local_day.py tests/unit/test_llm_router_free_tier.py tests/unit/test_llm_same_tier_fallback.py tests/unit/test_llm_tier_fallback_order.py tests/unit/test_credential_routing.py` → **57 passed**
  - 收尾格式包行后复跑触达面：`test_skill_store_service + test_llm_router_health_tracking + test_e07_health_hysteresis` → **26 passed**
  - 合计 **352 passed（含复跑），零失败**。
- ruff：12 触达文件 `ruff check` **All checks passed**（格式包行后复检 2 文件仍全绿）。
- black(120)：触达文件逐文件 Python 字符级 >120 行与 HEAD 对照——**零新增超长行**（唯一差异为 skill_store 既有 123 字符行因包行 +2 平移 149→151）；新增 hunk 全部 ≤120 列（首版 2 处超长已当场包行/缩短注释）。

## 台账

- 未新开 FIX 行：本卡 14 处全部为注解/改名/声明面校正，**零运行时语义变化、零真类型 bug**（V3-FIX-441/442 不占）。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → **verify 通过：311 行 V3-FIX 行，8 裸管形态合法，ID 无重号，状态枚举合法，零 FAIL**。

## 卷宗

- 修前/修后 mypy 全清单存会话 /tmp（wt728_mypy_base.txt / wt728_mypy_after.txt），不入库；本 notes 前后对照为准。
- diff 自审：20 insertions / 20 deletions，12 文件，逐 hunk 与上表一一对应；无 cast、无新增 ignore、无 Any 表达式改写。
