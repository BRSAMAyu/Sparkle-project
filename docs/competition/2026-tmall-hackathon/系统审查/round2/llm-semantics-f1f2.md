# LLM 路由语义修复（F-1：deep_analysis 真实触达 v4-pro）+ 推送解析修复（F-2：静默降级消除）

- 实现员：LLM 路由语义与推送解析修复员（sysrev wt6）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt6`（b97a0674，未 commit）
- 日期：2026-09-19
- 补丁：[llm-semantics-f1f2.patch](llm-semantics-f1f2.patch)（`git add -A && git diff --cached` 产物；`backend/.env` 为 gitignored，未入库未入补丁）
- 验证协议：pytest 定向（`SECRET_KEY=rule-guard-secret-0123456789abcdef JWT_SECRET=rule-guard-jwt-0123456789abcdef REDIS_URL=redis://:sparkle_dev_redis_2026@localhost:6379/1`），禁全量；WS 真实调用 3 次（预算 ≤3）；验证期以主仓同款方式重启引擎（`run_grpc_with_env.sh` + `uvicorn --env-file .env`），验证完已按原方式恢复主仓引擎并确认 :50051/:8000/:8080 全部在位
- 评测输入：`docs/competition/2026-tmall-hackathon/多端实测/ai-functions-real-eval.md` F-1 / F-2 节

---

## 0. 总览

| 挂账项 | 定性 | 修复 |
|---|---|---|
| **F-1**（P2）v4-pro 从未被触达，「reason 档」现网不存在 | **临时性能妥协的语义外溢**：开关本意是 standard 档首答 TTFB 优化，但 deep_analysis 档没有任何一条路径通向 MAX 层，产品核心卖点「深度规划」实际与 standard 同级 | `chat_mode=deep_analysis` 生成阶段显式决策：默认强制 **MAX 层**（deepseek_reason → deepseek-v4-pro）；新增延迟逃生阀 `DEEP_ANALYSIS_FORCE_FAST_TIER`（默认 False=真实路由 v4-pro）；standard 档首触快响语义原样保留 |
| **F-2**（P2）推送文案 LLM 输出 JSON 解析失败 → 静默降级硬编码「学习提醒/该复习了」 | 解析脆弱（naive replace 处理不了散文包裹/空串/异形 fence）+ 无重试 + 无遥测；附带 `LLMMonitor` 属性名漂移导致整个 wrapper 监控记账恒为 no-op | fence 稳健剥离 + 首个平衡 JSON 对象提取；失败后带「只输出 JSON」修正提示重试一次；仍失败保留降级但记 Prometheus 指标 + error 日志；修复监控漂移 |

红绿结果：**新增 14 项单测全绿（red 状态实证：6 errors / collection error）**；定向回归 173 passed，3 个失败经 pristine b97a0674 对照实证为**基线已有问题（测试隔离脆弱），与本改动无关**。真实调用验证：引擎日志实证 `generation → deepseek-v4-pro (强制tier=max [$0.0080/1k, tier=max])`。

---

## 1. F-1 溯源结论

### 1.1 开关从哪来

`STANDARD_CHAT_FORCE_FAST_TIER: bool = True`（settings.py:605）在**仓库清理重启后的 initial commit（1722e6dc）**中即存在；真实引入点经本地镜像备份仓 `~/code/GitHub/Sparkle-archive-20260915/mirror-backup.git` 追溯到 **f4aed946e（2026-03-20，"AI系统全链路修复1.0 目前还需完善"）**，与同批引入的 `FAST_INTERACTION_COPY_ENABLED`、`EARLY_ACK_PROGRESS_ENABLED` 同组——**这是一组首 token 延迟（TTFB）优化开关**，注释原文「标准对话首答强制走 FAST/Flash 层」。docs 侧佐证：`first-token-latency.md`、`V3规划输入-项目全景.md` 均把 `force_fast_first_touch`/ModelTier.FAST 机制记为「轻量消息走非 reasoning 快档」的既定缓解手段。

### 1.2 定性：性能妥协，非语义错误——但外溢成了语义缺失

代码本身只作用于 standard 档（`_should_force_fast_first_touch` 要求 `task_type == STANDARD_RESPONSE` 且 `chat_mode == "standard"`），对 deep_analysis 并不直接生效。**真正的问题在路由链本身**：deep_analysis 的生成选择走 `get_configured_llm_service(generation, DEEP_REASONING, reasoning_mode)` → `select_model` → `_select_by_policy`：

- `_preferred_tiers_for_reasoning_mode` 对 deep+DEEP_REASONING 给出 `[PRO, PLUS, STANDARD]`，**MAX 层只有在 `allow_max=True` 时才追加且永远排在链尾**；而该路径（`switch_model_for_task`）从不传 `allow_max=True`；
- generation 的 `AgentModelPolicy`（preferred_tier=STANDARD，preferred_models=dashscope_chat/deepseek_chat）把候选锁在 STANDARD 层；
- MAX 层唯一映射 `deepseek_reason`（= `DEEPSEEK_REASON_MODEL=deepseek-v4-pro`）在 deep_analysis 全链路 0 个入口可达。

结论：**保留**该开关对 standard 档的 TTFB 价值（性能取向成立）；deep_analysis 档缺 MAX 入口属于路由语义缺失，需要修复而非回滚。

---

## 2. F-1 修复实现

### 2.1 `app/config/settings.py`

```python
STANDARD_CHAT_FORCE_FAST_TIER: bool = True  # 仅 standard 档，F-1 保留其性能取向
DEEP_ANALYSIS_FORCE_FAST_TIER: bool = False  # 逃生阀：True=强制 FAST 换首 token 延迟；False=真实路由 MAX（v4-pro）
```

### 2.2 `app/agents/standard_workflow.py`

- 新增纯函数决策 `_deep_analysis_generation_tier(state)`：`chat_mode == "deep_analysis"` 时按开关返回 `ModelTier.MAX`（默认）或 `ModelTier.FAST`（逃生阀）；其余 chat_mode 返回 None（完全不影响 standard/study_plan/error_diagnosis）。
- `generation_node` 的 LLM 选择链中，该决策插在 **explicit expert（用户显式指定专家）之后、phase_d 成本带偏好与首触快响之前**——用户显式选择「深度分析」档是产品级意图，capability selection 的成本带偏好（`phase_d_forced_model_tier`）不得静默降档。命中后经 `get_configured_llm_service_for_tier(..., ModelTier.MAX, ...)`（其内部 `allow_max=force_tier==MAX`）路由，`state.context_data["deep_analysis_model_tier"]` 留观测标记。
- **与免费层钳制正交**：`select_model` 的 free-clamp（步骤 2.6）在 force_tier 之后仍生效，free 用户 deep_analysis 请求照样被钳到 ceiling（fast）并带 `free_tier_downgrade(max->fast)` 标记。

### 2.3 修复前后对照（离线直调，.env 真实配置）

| 路径 | 修复前 | 修复后 |
|---|---|---|
| deep_analysis 生成（balanced/deep） | `glm_4_7_plus`（plus 层）或 `deepseek_chat`（standard 层，模型名 deepseek-flash）——**永不到 MAX** | `deepseek_reason`（max 层，**deepseek-v4-pro**） |
| deep_analysis + `DEEP_ANALYSIS_FORCE_FAST_TIER=True` | — | `deepseek_fast`（flash，逃生阀） |
| deep_analysis + free 用户 | flash（被钳） | 仍钳 fast：`free_tier_downgrade(max->fast)` + 指标自增 |
| standard 档首触 fast | `强制tier=fast`（原样） | 原样（`_deep_analysis_generation_tier` 返回 None） |

---

## 3. F-2 修复实现

### 3.1 `app/services/llm_service.py` — `generate_push_content` 解析链

- 新增 `_extract_json_payload(text)`：先剥 markdown fence（语言标注大小写/省略均兼容），再从剩余文本中提取**首个花括号平衡的 JSON 对象**（字符串内 `{}`/引号/转义感知）。覆盖评测发现的三种失败形态：空串（`Expecting value: line 1 column 1`）、散文包裹、异形 fence。
- 解析失败（含缺 title/body、非 dict）→ 记 `stage=initial` 指标 + warning 日志（带输出 preview）→ **以「只输出一个 JSON 对象…不要 markdown 代码块/解释文字」修正提示重试恰好一次**；
- 重试仍失败 → `stage=retry` 指标 + **error 日志（persona/trigger/user 上下文齐全，不再静默）** + 保留原静态降级文案；
- LLM 调用层异常（网络等）单独分支：可重试一次但不计入解析失败指标，避免遥测语义混淆；系统 prompt 与首条 user 消息同步声明「Respond with a single JSON object」，降低首试失败率。
- 新指标：`sparkle_llm_push_content_parse_failure_total{stage=initial|retry}`（`app/core/metrics.py`）。

### 3.2 `app/core/llm_security_wrapper.py` — LLMMonitor 属性名漂移

`LLM_CALLS_TOTAL` / `LLM_LATENCY_SECONDS` / `TASK_FAILURES` 是 `llm_monitoring` 的**模块级**指标而非 `LLMMonitor` 实例属性；`_record_call_metrics` 首行即抛 `AttributeError` 且被自身 `except` 吞掉——**整个 wrapper 的调用记账（含成本估算）一直是 no-op**。修复：直接从模块导入三个指标使用，`self.monitor.estimate_and_record_cost` 等实例方法保持不变。评测报告捕获的 `LLMMonitor object has no attribute 'LLM_CALLS_TOTAL'` 即此。

---

## 4. 红-绿验证（pytest 定向）

新增测试：

| 文件 | 覆盖 |
|---|---|
| `backend/tests/unit/test_deep_analysis_tier_routing.py`（6 项） | 决策函数默认 MAX / 逃生阀 FAST / standard 返回 None 且首触快响原样；selection 落 `deepseek_reason`（v4-pro 位）/ 逃生阀落 `deepseek_fast`；**组合测试**：free 用户 deep_analysis 决策仍为 MAX 但 selection 被钳 fast + `free_tier_downgrade` 标记 + 指标自增 |
| `backend/tests/unit/test_push_content_parsing.py`（8 项） | fence JSON 单次解析成功；纯文本→重试一次（修正提示在 payload 中）→成功；两次纯文本→降级文案保留 + `initial`/`retry` 指标各自增；空串→重试→`JSON` 成功；散文包裹提取；**监控漂移**：`_record_call_metrics`/`_record_call_failure` 后 `llm_calls_total`/`llm_task_failures_total` 样本真实自增 |

红实证：stash 生产改动后，F-1 套件 6 errors（决策函数不存在）、F-2 套件 collection error（`_extract_json_payload` 不存在）；恢复后全绿。

绿：**14/14 passed**。定向回归（free_tier、generation_routing、llm_security_wrapper×3、router_policy、llm_parser、llm_service_streaming、stage38_d3_persistence）：**173 passed / 3 failed**，3 个失败（`test_generation_node_batches_stream_deltas` + free_tier 两个 `test_streamchat_entry_*`）在 **pristine b97a0674 同组合下完全一致复现**，为基线测试隔离脆弱，非本改动引入。其中 `test_generation_node_batches_stream_deltas` 单测意图（delta 合批）按其同文件相邻用例模式补充 mock `get_configured_llm_service_for_tier` 以适配 deep_analysis 新路由（该用例在 pristine 单跑同样红）。

---

## 5. 真实调用验证（WS 全链路，预算内 3 次）

以主仓同款方式将引擎切换到 wt6 代码（`bash backend/scripts/run_grpc_with_env.sh` + `uvicorn app.main:app --env-file .env`，确认 :50051/:8000 监听、cwd=wt6/backend），经网关 :8080 走 游客token → `/api/v1/ws/ticket` → `ws://…/ws/chat?ticket=` 全链路：

| # | 消息 | 结果 |
|---|---|---|
| 1 | deep_analysis + 信息不足（「制定考研40天冲刺计划」） | 通，但 clarify 阶段短路追问（缺每日时长），未到 generation——与评测 F-1 现象同源；`orchestrator 强制tier=fast` 为澄清文案的既定设计（`FAST_INTERACTION_COPY_ENABLED`） |
| 2 | deep_analysis + intent=plan 富信息消息 | 状态图在 `execution_review` 节点崩（`dictionary keys changed during iteration`，`statechart_engine._merge_context_data` 对别名 dict 迭代中删除——**基线已有缺陷**，与本次改动无关，generation 因 plan-intent 走工具执行被跳过）；已记入 §7 遗留 |
| 3 | deep_analysis + 分析型消息（记忆/认知科学三角度） | **✅ 全链路通**：1716 字回答完整流出，引擎日志实证（`logs/grpc_server_2026-09-19_00-22-00_288376.log:577`）：`📍 Executing node: generation` → **`[LLMRouter] generation → deepseek-v4-pro (强制tier=max [$0.0080/1k, tier=max])`** → 首块 1565ms（type=reasoning，v4-pro 思考流）→ `generation_review` 审校 1716 chars |

**「reason 档不存在」的现网事实已被推翻：deep_analysis 档真实路由 v4-pro。** 验证完引擎已按原方式切回主仓代码，:50051/:8000/:8080 全部确认在位。

---

## 6. 变更清单

```
M  backend/app/config/settings.py                                # DEEP_ANALYSIS_FORCE_FAST_TIER（默认 False）+ 注释
M  backend/app/agents/standard_workflow.py                      # _deep_analysis_generation_tier + generation_node 决策分支
M  backend/app/services/llm_service.py                          # _extract_json_payload + generate_push_content 解析/重试/遥测链
M  backend/app/core/llm_security_wrapper.py                     # LLMMonitor 属性名漂移修复（模块级指标直用）
M  backend/app/core/metrics.py                                  # sparkle_llm_push_content_parse_failure_total
M  backend/tests/unit/test_standard_workflow_generation_routing.py  # 合批用例适配新路由（补 mock，意图不变）
A  backend/tests/unit/test_deep_analysis_tier_routing.py        # F-1 红绿 6 项
A  backend/tests/unit/test_push_content_parsing.py              # F-2 红绿 8 项
A  docs/competition/2026-tmall-hackathon/系统审查/round2/llm-semantics-f1f2.md + .patch
```

## 7. 遗留与建议（本次不动）

1. **`execution_review` 别名 dict 崩溃**（`statechart_engine.py:116 _merge_context_data`，plan-intent 的 deep_analysis 消息可稳定触发裸 internal error）：节点返回的 `context_data` 与图状态同对象时，迭代中 `del` 必崩。建议 `_merge_context_data` 入口对 `new_data is target` 做防御（跳过或拷贝），或审计 `review_nodes` 返回值别名——独立挂账。
2. plan-intent 的 deep_analysis 消息会绕过 generation（LangGraph plan → 工具执行），属于规划档正确行为，但意味着 deep_analysis 的「深度回答」与「计划生成」按 intent 分流——产品口径可明确。
3. `test_generation_node_batches_stream_deltas` 与 free_tier 两个 `test_streamchat_entry_*` 的基线隔离脆弱（组合跑互相污染）建议独立修复。
4. v4-pro 首块延迟实测约 1.6s（reasoning 首 chunk），若逃生阀仍不够可再评估澄清文案与深度回答的分层提示。
