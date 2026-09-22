# TTFT-CFG：思考档分档配置 + 规划链预算收敛（wt131）

> 2026-09-23 ｜ Worker: TTFT-CFG ｜ worktree: `Sparkle-sysrev/wt131`（基线 d19551a0，已含 TTFT-PROBE 代码修复）
> 上游实证：`v3-output/TTFT-PROBE/REPORT.md`（主仓只读）簇 A/B 两根因，本卡落地其全部**配置级/预算级**裁决（主会话已拍板，语义未改）
> 交付物：本报告 + `changes.patch`（11 文件，884 行）

---

## 一、结论（TL;DR）

三处裁决全部落地，14 条新增单测全绿，四条回归线零新增失败：

| # | 裁决 | 落点 | 状态 |
|---|---|---|---|
| 1 | DashScope 思考分档：FAST/STANDARD/PLUS 显式 `enable_thinking=false`；PRO/MAX/TOP 保留思考；GLM 车道 `thinking:{}` 原样 | `llm_router.get_openai_client_kwargs`（统一组包点，流式/非流式/langchain 全覆盖）+ `llm_service` 两个 raw 组包块按 provider 分叉 | ✅ |
| 2 | planner 硬编码超时 10s→3s | `execution_engine.py:58`（常量）+ `plan_review_service.py` / `multi_agent_adapter.py` 两个同链 caller + 钉值测试同步 | ✅ |
| 3 | `check_sufficiency` / `check_goal_quality` 移 FAST 车道 + 5s 预算封顶 | `sufficiency_checker.py`（FAST 服务）+ `goal_quality_evaluator.py`（FAST 服务）+ `validation_engine.py`（suff 预算包装） | ✅ |

预期效果（待主会话活栈复验）：簇 B 主聊天 TTFT 29-43s → 首 token 秒级（M6 旁证：首块 356ms 即可达，纯思考占 13-43s）；簇 A 规划轮首帧前移：suff/goal_quality 单项 35.8s 封顶 5s、planner 10s 税收敛 3s，串行前置链最坏 30.6s → 13s 以内。

---

## 二、任务① 证据复现（改动前）

**DashScope 请求体发的是 GLM 风格 `thinking` 而非 `enable_thinking`，且部分路径什么思考参数都不发：**

1. **raw 流式/非流式组包（主聊天 generation 走这里）**——`backend/app/services/llm_service.py` 改动前 **875-878 行**（`_create_raw_completion`）与 **928-931 行**（`_create_raw_stream`）：

   ```python
   if selection.config.thinking_mode:                      # 不分 provider
       extra_body = dict(params.get("extra_body") or {})
       extra_body["thinking"] = {"type": selection.config.thinking_mode}
       params["extra_body"] = extra_body
   ```

   `dashscope_standard_thinking`（qwen3.8-flash, `thinking_mode="enabled"`, tier=STANDARD）由此发出 `extra_body={"thinking":{"type":"enabled"}}`——GLM 车道参数格式，对 DashScope 兼容模式无效（TTFT-PROBE 簇 B 推断，M6 旁证：参数发了思考却没被控制）。

2. **非流式 `chat()` / cascade 路径**——`llm_service.chat` 走 `current_provider.chat(..., **request_kwargs)`，而改动前 `llm_router.get_openai_client_kwargs`（旧 1705-1736 行）**只对 ZHIPU 组 extra_body**：DashScope 车道在这些路径上**连 `thinking` 都没有**，`enable_thinking` 更无从谈起。探针 M6（`reasoning_mode=fast` → dashscope_fast，无参数）首块 356ms 即 `type=reasoning`、TTFT 33.4s——实锤"不发参数 = qwen3 混合模型默认思考开"。

3. **模型注册面**（`llm_router.py` 701-765 行）：`dashscope_standard_thinking`/`dashscope_reason`/`qwen3_8_max`/`qwen3_8_max_top` 均带 `thinking_mode="enabled"`；`dashscope_fast`/`dashscope_chat` 无任何思考参数。全库 `grep enable_thinking backend/app` 零命中。

**修复后组包断言输出**（真实路由器 + 真实 `get_openai_client_kwargs`）：

```
dashscope_fast               tier=fast     extra_body={'enable_thinking': False}
dashscope_standard_thinking  tier=standard extra_body={'enable_thinking': False}
dashscope_chat               tier=plus     extra_body={'enable_thinking': False}
dashscope_reason             tier=pro      extra_body=None
qwen3_8_max                  tier=max      extra_body=None
qwen3_8_max_top              tier=top      extra_body=None
glm_4_7_no_thinking          extra_body= {'clear_thinking': True, 'thinking': {'type': 'disabled'}}
```

---

## 三、三处裁决实现与断言清单

### 裁决 1：DashScope 思考分档（provider 分叉，非全局替换）

- `app/core/llm_router.py`：新增纯函数 `dashscope_enable_thinking_param(tier, thinking_mode)` 三态（False=显式关 / None=不注入 / **永不 True**）+ `get_openai_client_kwargs` 对 `provider==DASHSCOPE` 注入。选统一组包点而非散在 llm_service，是因为 raw 流式、raw 非流式、`chat()` cascade、`switch_model_for_task`、langchain factory 全部经此一孔——一次修复覆盖 probe 报告的"流式组包发了错参数"与"非流式什么都不发"两个半边。
- `app/services/llm_service.py`：两个 raw 组包块加 `provider is not ModelProvider.DASHSCOPE` 条件——DashScope 不再叠加 GLM 风格 `thinking:{}`；GLM/MIMO/DeepSeek 逐字节原样。
- **语义裁决细化（申报）**：
  - **PLUS 一并显式关**：裁决字面只点名 FAST/STANDARD 关、PRO/MAX/TOP 保留；PLUS 未被点名。实现取 `dashscope_chat`（qwen3.7-plus，代码库注册注释即"PLUS 层非思考"）随主链路一并 `false`——主聊天直出层 FAST→STANDARD→PLUS 是同一条降级链，漏掉 PLUS 等于降级时簇 B 复发。
  - **PRO/MAX/TOP 选"不注入"而非"注入 true"**：enable_thinking=true 在非流式/部分非混合模型上有 400 风险；不注入 = provider 默认（流式思考开），思考保留语义自然达成，零新增 400 面。reasoning_mode 显式深思考的调用经 router 落 PRO/MAX/TOP 层（如 dashscope_reason）即保持思考开启——"可覆盖为开"由分层路由承载。
  - tier 取 `config.tier`（模型注册档）而非 `tier_used`（请求档）：模型降级场景（如 M6 请求 plus 落 dashscope_fast）语义跟着真实跑的模型走。

**断言**（`tests/unit/test_ttft_cfg_thinking_and_budget.py`，7 条）：三态纯函数表（含"永不 True"契约）、FAST/STANDARD/PLUS 三车道线上 payload（httpx.MockTransport 捕获真实 wire JSON）含 `enable_thinking:false` 且无 `thinking` 键、PRO/MAX/TOP 无注入、GLM coding 车道 `thinking:{"type":"disabled"}` 原样、非 DashScope（MIMO）`thinking_mode` 车道不受分叉影响、raw 流式路径 DashScope 发 `enable_thinking` 不发 GLM 风格键、raw 非流式 GLM 思考车道原样。

### 裁决 2：planner 超时 10s→3s

- `execution_engine.py:58`（现 60 行附近）：`_LANGGRAPH_PLANNER_TIMEOUT_SECONDS = 3.0`（带注释说明超时走 synthesized fallback 为既有语义，只收敛预算）。
- **同步收敛两个同链 caller**：`plan_review_service.py:2377`、`multi_agent_adapter.py:104` 的 `timeout=10.0 → 3.0`。申报：卡片字面只点名 execution_engine.py:58 一带；但 `tests/test_langgraph_planner_timeout.py::test_timeout_value_matches_execution_engine` 钉死三处必须同值，单独改一处必留红——取"同一 planner 调用、同一预算"的一致语义三处同改并同步钉值测试（10.0→3.0）。
- **断言**（2 条）：常量值 == 3.0；`wait_for` 调用点必须引用常量（防回填裸数字）。行为级超时兜底由存量 `tests/orchestration/test_r2_orchestration_fixes.py`（monkeypatch 常量法）继续覆盖，未动。

### 裁决 3：前置链 FAST 化 + 预算封顶

- **check_goal_quality**（`goal_quality_evaluator.py`）：
  - LLM 服务：`get_configured_llm_service(ORCHESTRATOR, QUICK_QUERY)` → `get_configured_llm_service_for_tier(ORCHESTRATOR, ModelTier.FAST, task_type=QUICK_QUERY)`。`force_tier` 在 `select_model` 短路 profile 策略，FAST 池首 = `dashscope_fast`（与裁决 1 组合：该车道 wire 上 `enable_thinking=false`）。附带收益：原路径经 `switch_model_for_task` 会改写**共享缓存**的 ORCHESTRATOR 服务实例模型（跨调用污染副作用），新路径每次独立实例，副作用消除。
  - 预算：`evaluate()` 内 `async with asyncio.timeout(GOAL_QUALITY_LLM_BUDGET_SECONDS=5.0)` 包 LLM 段，超时 → 既有 `_heuristic_fallback`（兜底契约不变，evaluate 不抛）。
- **check_sufficiency**（`sufficiency_checker.py` + `validation_engine.py`）：
  - LLM 精化/澄清生成走 FAST 车道：模块级惰性单例 `_get_fast_lane_service()`（同 force_tier=FAST 构造；构建失败回退全局服务原链并标记，不阻断检查）。`llm_fallback_utils` 的 `safe_llm_call/safe_llm_json_call/LLMFallbackWrapper.call/json_call` 加 **additive** `service=None` 参数（默认=全局服务，其余调用方零行为变化）。
  - 预算：`validation_engine._check_sufficiency` 对 `sufficiency_checker.check(...)` 整段 `async with asyncio.timeout(SUFFICIENCY_CHECK_BUDGET_SECONDS=5.0)`，超时 → `return False, intent_type`——与既有 `except Exception: "check failed, continuing"` 完全同语义（放弃本轮充分性裁决、继续通用链路）。phase-A preflight 与澄清/确认发射块在预算外，不受影响。
- **预算值取 5s**：裁决带宽 3-5s；suff 历史正常样本 3.2-3.99s，取 5s 保证正常轮不受截断、病态轮（19.2s/35.8s）被斩。planner 单独 3s（裁决 2 字面值）。
- **asyncio.timeout 形态**：全部 `async with asyncio.timeout(N):`（附专项防回归断言：源码中 timeout 行不得出现 `)(` 死码形态——上一卡陷阱）。

**断言**（5 条）：goal_quality FAST tier 三参数捕获、goal_quality 预算超时落启发式兜底（计时 <0.6s + 兜底产物形状）、suff 精化 FAST lane 三参数捕获、suff check 预算超时 `(False, intent)` 继续通用链路（计时 <0.6s）、两处 `async with` 形态防死码。

---

## 四、回归对比（红线）

| 套件 | 改动前基线 | 改动后 | 判定 |
|---|---|---|---|
| **卡片红线**：`pytest tests/unit -q -k "llm_service or llm_router or orchestration or planner or execution_engine"` | 73 passed / 1 skipped / **0 failed** | 75 passed / 1 skipped / **0 failed** | ✅ 节点级 diff：73 存量节点逐一相同，仅 +2 = 本卡新增 planner 单测（被 `-k planner` 选中）。**零新增失败** |
| 同命令节点级对比（`git clone` 克隆基线法，AGENTS.md 纪律） | `/tmp/wt131-baseline`（HEAD d19551a0） | worktree | `diff` = 仅上述 +2，`IDENTICAL` 其余 |
| `tests/core/test_llm_router_glm_thinking.py + test_llm_router_qwen.py + test_minimax_batch_routing.py + tests/test_langgraph_planner_timeout.py` | — | **57 passed** | ✅ GLM 车道/Qwen 路由/MiniMax batch 红线 + 钉值测试全绿 |
| `tests/orchestration` 全量 | 34 failed / 160 passed / 26 errors（与 TTFT-PROBE 报告完全一致） | 34 failed / 160 passed / 26 errors | ✅ FAILED/ERROR **逐名 diff 零差异**（存量债务，非本卡引入） |
| 本卡新增 `tests/unit/test_ttft_cfg_thinking_and_budget.py` | — | **14 passed** | ✅ |

环境备注：worktree 缺 `app/gen/`（首次基线 122 collection errors 的原因），已按规程从主仓拷贝（git-ignored，不入库）。

---

## 五、Worker 五要素

### ① 证据
参数现状行号见 §二（改动前 llm_service.py 875-878 / 928-931 无 provider 分叉、llm_router 旧 get_openai_client_kwargs 仅 ZHIPU 组包、全库无 enable_thinking）；修复后组包断言输出见 §二表（真实路由器冒烟）+ wire 级 MockTransport 捕获断言（单测）。

### ② 红线面（每文件为何不破坏既有车道行为）
- **`core/llm_router.py`**：ZHIPU 的 `clear_thinking`/coding 端点 `thinking:{"type":"disabled"}` 组装逻辑原样在前，DashScope 分支只在其后按 provider 叠加；MINIMAX（GLM_BATCH 车道，provider≠DASHSCOPE）零改动；`qwen3_7_flash_batch` tier=GLM_BATCH → helper 返回 None → 无注入，batch 车道 wire 不变；`glm_effective_max_tokens` 留量逻辑未动。
- **`services/llm_service.py`**：仅两个 raw 块加 `provider is not DASHSCOPE` 前置条件，GLM/MIMO/DeepSeek 的 `thinking:{}` 发送路径逐字节不变；`chat()`/`stream_chat` 主体未动。
- **`services/llm_fallback_utils.py`**：纯 additive `service=None` 参数，默认走全局 `llm_service`——vocabulary/analysis/omnibar 等既有 wrapper 调用方行为不变。
- **`orchestration/goal_quality_evaluator.py`**：`TRIGGER_INTENTS` 短路、`_heuristic_fallback` 契约、"LLM 失败→启发式"路径全部原样，只改 LLM 来源（FAST）与加超时。
- **`orchestration/sufficiency_checker.py`**：`sufficiency_llm` 的 fallback（`{"specific": True}`）/timeout(10s)/retry 语义不变，仅目标服务换 FAST；FAST 服务构建失败自动回退全局服务原链。
- **`orchestration/validation_engine.py`**：仅包裹 `sufficiency_checker.check` 一段；澄清/确认发射与 phase-A preflight 未动；超时返回值与既有异常路径同语义。
- **`execution_engine.py` / `plan_review_service.py` / `multi_agent_adapter.py`**：超时走兜底语义一字未改，只收敛预算数值；`tests/test_langgraph_planner_timeout.py` 钉值同步（10.0→3.0）。

### ③ 冲突面
改动文件：`core/llm_router.py`、`services/llm_service.py`、`services/llm_fallback_utils.py`、`orchestration/{execution_engine,goal_quality_evaluator,sufficiency_checker,validation_engine,plan_review_service,multi_agent_adapter}.py`、`tests/test_langgraph_planner_timeout.py`、新增 `tests/unit/test_ttft_cfg_thinking_and_budget.py`。
- **wt123（mobile chat UI）**：零交集（本卡全在 backend）。
- **wt125（plans API）**：API/CRUD 层零交集；唯一理论交叠 `plan_review_service.py` 仅 1 行超时值变更（+1 注释行），语义独立。
- **wt129（error 吸收）**：未碰任何 error handler/吸收面，零交集。
- **wt130（驱动器）**：零交集。
- 提示：`llm_service.py`/`llm_router.py` 是共享热点，若同窗有其他卡改组包面，合入顺序以主会话裁断；本卡改动均为"新增 helper + 局部条件分叉"，文本冲突面小。

### ④ 诚实申报
1. **`enable_thinking=false` 对 DashScope 的真实生效性无法离线证明**：MockTransport 只证明 wire 形态正确（发出的 JSON 含 `enable_thinking:false`、无 GLM 风格 `thinking`）；模型侧真实关思考效果、以及 `DASHSCOPE_*_MODEL` 若被 env 钉到非混合模型时对该参数的接受度，需主会话合入并重启引擎后活栈复验（剧本沿用 TTFT-PROBE §4.4 探针，预期 M2/M4/M6 类消息 TTFT 从 29-43s 塌缩到秒级、M1/M7 规划轮首帧从 11.3/39.8s 前移到 ≈13s 内）。凭证一律向主会话索取（不落库）。
2. **PLUS 档是语义扩展**（裁决未点名）：理由见 §三；若主会话不认可，删 `ModelTier.PLUS` 于 `_DASHSCOPE_THINKING_OFF_TIERS` 一行即可回退（有独立断言）。
3. **PRO/MAX/TOP"保留思考"实现为"不注入"**（依赖 provider 流式默认思考开），未显式发 `enable_thinking:true`（防非流式 400）；reasoning_mode 显式深思考经 tier 路由落 PRO 层保持思考——该链路未逐条实测。
4. **planner 预算同步改了 plan_review_service/multi_agent_adapter 两处**（卡片字面仅点名 execution_engine）：驱动因素是钉值测试三处一致性约束，见 §三申报。
5. 前置链预算只在单测层验证（计时断言）；活栈上 5s 是否足够覆盖 FAST 车道 P99 延迟（含重试）未实测。
6. suff 预算包裹的是 `sufficiency_checker.check` 整段（含其内部启发式+LLM 精化），`predict_intent_only` 上游 hop 未纳入预算（探针未将其单独计时，保守不动）。

### ⑤ 收工核查
- **git**：零 commit / 零 push（交付物 = 本 REPORT.md + changes.patch；`git add -N` 后已 `git reset -q` 还原 index，patch 新文件头 `--- /dev/null` 自查 = 1 处）。
- **凭据**：patch 与报告经 `grep -inE "api[_-]?key|password|secret|token|bearer|sk-"` 扫描，仅命中代码上下文行（`settings.DASHSCOPE_API_KEY` 引用、max_tokens 注释），无任何凭据值。
- **主仓/DB 只读**：主仓仅读取 PROBE 报告与拷贝 git-ignored 的 `app/gen/`；演示 DB 零连接。
- **/tmp 清理**：`wt131-baseline`（克隆）、`wt131_base/post_unit.log`、`wt131_base/post_orch.log`、`base/post_fe.txt`、`base/post_nodes.txt`、`wt131_tracked.patch` 全部删除（见收工命令）。
- **进程**：无残留（全部 pytest 单进程顺序跑，无服务/模拟器/浏览器）。
- **worktree 内 `backend/app/gen/`**：git-ignored，随 worktree 生命周期回收，不入库。
