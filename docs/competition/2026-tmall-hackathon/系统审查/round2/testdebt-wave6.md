# 测试债清理第六波（wave6）——reflection 族最后 2 红

> worktree wt7 @ 27a65fd0 ｜ 2026-09-19 ｜ 状态：2/2 红绿 + 邻域 61/61 绿，生产代码零改动

## 范围

承 wave5 移交的 2 个已诊断红例，全部落在 reflection 族：

1. `tests/unit/test_reflection_trigger_extension.py::test_reflection_service_exposes_all_six_categories`
2. `tests/unit/test_reflection_context_injection.py::test_build_reflection_context_respects_token_budget`

## 处置明细

### 1. 六类断言 → 对齐现行八类（断言过时，改断言）

生产 `TaskReflectionService.ELIGIBLE_CATEGORIES`（`app/services/task_reflection_service.py:91`）已从 6 个负向触发扩到 **8 类**：原 `too_difficult / unclear / abandoned / intervention_ineffective / plan_stall / overload` + 新增正向触发 `plan_completed / milestone_reached`（PROMPT_TEMPLATES 与 TRIGGER_PROMPT_VERSIONS 同套件均已注册，wave5 已确认这部分测试是过的）。

修复：测试改名 `..._exposes_all_eight_categories`，集合断言补齐 `plan_completed`、`milestone_reached` 两项，并注释说明 8 类构成。

### 2. token 截断 truncated=False —— 定性：**测试数据时间炸弹（断言/夹具过时），生产截断逻辑健康**

**定性过程（临时诊断用例双场景实证，已删）**：

- `test_build_reflection_context_respects_token_budget` 以硬编码 `decided_at=2026-04-21` 灌 5 条决策，而 `_build_reflection_context`（task_reflection_service.py:941-946）默认按 `window_days=14` 以 `decided_at >= now-14d` 过滤——4 月日期距今 151 天，**全部老化出窗** → `entries` 为空 → 走 fallback 行（"no recent decisions found"）。fallback 分支会把行截到预算内（tokens=24≤24，故第二条断言其实能过）但不置 `truncated` 标志——它截的是常量短文案，不丢任何用户数据，语义合理。这正是红例指纹：`truncated is True` 失败、`tokens <= 24` 不失败。
- 同场景仅把日期改为 1 小时前：首行 ~38 tokens > 24 → 首行截断 + `truncated=True`，`tokens=24` —— **生产截断逻辑（首行超限截断、累计超限断流）完全正常**。

**5416b1d3 排除**：该提交只动了 chat 侧 reflection 重写链（`app/agents/reflection_agent.py` 继承 ~5.9KB 主生成 system_prompt 等 6 文件），对 `TaskReflectionService._build_reflection_context` 的 token 数学零触碰；reflection_agent 仅在 `reflection_agent.py:559` **消费** `route_history_context_truncated` 标志，不回写。本测试是纯 DB 夹具 + 服务层路径，不经 LLM。结论：与 5416b1d3 无交互，纯属夹具日期老化。

修复：夹具日期改为相对当前时间（`now - 1h` 起、逐条 +1min），并注释说明出窗失效机理，测试意图（预算截断 + 标志置位）恢复且不再随时间复发。

## 红绿证据

| 阶段 | 命令 | 结果 |
|---|---|---|
| 红（修前） | `pytest test_reflection_trigger_extension.py::test_reflection_service_exposes_all_six_categories test_reflection_context_injection.py::test_build_reflection_context_respects_token_budget` | 2 failed（集合差 2 项；`assert False is True`） |
| 诊断 | 临时双场景用例（aged vs fresh） | aged: entries=0/fallback/truncated=False；fresh: truncated=True, tokens=24 |
| 绿（修后） | 两文件全量 | **14/14 passed** |
| 邻域 | reflection 族全跑（trigger_extension / context_injection / task_reflection_service / reflection_agent×3 / kill_switch / rule_y_gate / review_reflection_fix_r2 / review_skip_logic / reviewer_agent / route_history×3） | **61/61 passed**（含 wave5 修过的 review_skip_logic、reflection_agent_user_id） |

## 产物

- 本文档 + `testdebt-wave6.patch`（`git add -A && git diff --cached` 生成，**未 commit**）
- 变更面：2 个测试文件 + 本文档；生产代码零改动

## 遗留与移交

1. 同文件 `test_build_reflection_context_includes_rule_y_evidence_markers` 与 `..._caps_recent_decisions_to_twenty` 仍用 2026-04-21 硬编码日期，当前**绿但已退化为假阳性**（出窗后命中 fallback 行，标记断言/上限断言被平凡满足）——本波按"轻量定向"纪律不动绿例，建议 wave7 顺手做同款日期相对化。
2. reflection 族单测红例至此清零。
