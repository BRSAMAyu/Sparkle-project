# 免费层模型降级落地报告（free_tier_downgrade：免费用户钳制到轻模型）

- 实现员：免费层模型降级实现员（sysrev wt6）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt6`（b8f4e7d8，未 commit）
- 日期：2026-09-18
- 补丁：[free-tier-model-downgrade.patch](free-tier-model-downgrade.patch)（`git add -A && git diff --cached` 产物，排除自身；`backend/.env` 为 gitignored 未入库未入补丁）
- 验证协议：pytest 定向（`SECRET_KEY=rule-guard-secret-0123456789abcdef JWT_SECRET=rule-guard-jwt-0123456789abcdef REDIS_URL=redis://:sparkle_dev_redis_2026@localhost:6379/1`），禁全量；真实 LLM 验证 1 次（预算 ≤8）；未触碰在跑主仓引擎（:50051）

---

## 0. 总览

挂账项「免费模型跨层降级」（`p3-sweep-gateway.md` §1 语义边界 + 漏洞台账 2026-09-18 产品决策 follow-up）：**免费/低配额用户的 LLM 请求钳制到轻模型（deepseek-flash），付费/高配额（pro）走全能力（deepseek-v4-pro），降级留痕可观测。**

| 交付 | 状态 |
|---|---|
| 分层信号选型：消费既有 `UserProfile.is_pro`（网关已在链路填充，零网关改动） | ✅ |
| 引擎侧钳制：`llm_router.select_model`（force/task/profile/complexity 路径）+ `_select_by_policy`（候选层/允许层/偏好模型三路收敛）+ `resolve_candidate_models`（fallback 链一致性） | ✅ |
| 留痕：`reason` 内嵌 `free_tier_downgrade(max->fast)`、`LLMSelection.free_tier_downgrade` 字段、Prometheus `sparkle_llm_router_free_tier_downgrade_total`、loguru 路由日志 | ✅ |
| 红-绿单测：14 项新增全绿；定向回归 93 passed（3 个基线已有失败，与本改动无关） | ✅ |
| 真实调用验证：free 上下文强制 MAX → 路由 `deepseek-flash`（tier=fast），真实回复成功 | ✅ |
| 治理守卫：`run_all_rule_guards.sh` 结果与基线完全一致（K/Z/BA/BG 四项基线即红，非本改动引入） | ✅ |

---

## 1. 分层信号选型（最小侵入）

调研结论（选型依据）：

| 候选信号 | 现状 | 结论 |
|---|---|---|
| `users` 表 DB 字段 | 无 plan/tier/subscription 列（只有 `flame_level` 游戏化等级、`photon_balance` 虚拟货币、`is_superuser`） | 需 Alembic 迁移，侵入大，弃 |
| 网关 JWT claims | 仅 userID + isAdmin（`middleware/auth.go`） | 需改 token 签发链，弃 |
| 配额服务 | 网关 quota 不分 plan（dd9d62d3 只做有界降级）；引擎 `LLMCostGuard` 全局日限额 | 无分层语义，弃 |
| **proto `UserProfile.is_pro`** | **字段已存在**（`agent_service.proto` 注释原文 "Pro status might determine access to advanced models or tools"）；网关 ws chatflow **已在填充** | ✅ 选定：只消费，零网关改动 |

选定的既有链路（无需任何网关/proto 改动）：

```
Go 网关 chatflow（chat_orchestrator_chatflow.go:653）
  └─ buildAgentUserProfile() ← ChatUserProfileSnapshot.IsPro ← user_context.go:129（user.FlameLevel >= 3）
       └─ ChatRequest.user_profile.is_pro ──gRPC──▶ 引擎 AgentServiceImpl.StreamChat（本次新增消费点）
```

引擎 `GetUserProfile` 的 `is_pro` 同源（`user_service.py:208` `is_pro=user.flame_level >= 3`），两仓语义一致。另支持 `extra_context.user_tier`（free/pro/premium/paid）显式覆盖，供网关未来透传更细分层而**无需改 proto**。

---

## 2. 引擎侧实现

### 2.1 `app/core/llm_router.py`（核心钳制）

- **请求级分层信号**：模块级 `ContextVar`（`_REQUEST_USER_TIER`）+ `set_request_user_tier()/get_request_user_tier()/reset_request_user_tier()`。选 contextvar 而非函数参数的原因：`select_model` 调用点遍布 llm_service/factory/workflow/graph nodes，逐点穿参侵入过大；且 `llm_service_impl` 为模块级单例、`get_llm_service` 按角色缓存实例，构造期读参无法覆盖每请求语义。asyncio task 上下文随 StreamChat 协程传播，LangGraph 节点/`get_configured_llm_service*` 的每请求 `select_model` 调用全部可见；未标记的调用面（Celery 批量、定时任务、测试）保持现状不钳制。
- **能力层秩表**：`_CAPABILITY_TIER_RANK = {top:0, max:1, pro:2, plus:3, standard:4, fast:5}`。钳制只作用于能力层；`free*/glm_batch/specialist` 非直出层保持原路由。
- **钳制规则**：free 用户且目标 tier 秩 < ceiling 秩 → 压到 ceiling。ceiling 由 `FREE_TIER_MODEL_CEILING` 配置（默认 `fast`，可配 `standard`；非法值回退 fast 并告警）；总开关 `FREE_TIER_DOWNGRADE_ENABLED`（默认 true）。
- **四条路径全覆盖**：
  1. `select_model` 主路径（force_tier / task_type / profile tier / reasoning_mode / complexity 调整之后、候选挑选之前，步骤 2.6）——钳 target_tier + reason 标记 + 计数器 + 日志；
  2. `_select_by_policy` 策略路径——`_adjust_policy_for_free_tier` 三路收敛：候选 `tiers` 剔重、reasoning_mode 的 `allowed_tiers` 重写为 ceiling（否则 deep 模式允许层 {pro,plus,standard} 会把 FAST 候选全滤掉）、`policy.preferred_models` 剔除高于 ceiling 的模型（否则 dashscope_reason 等偏好模型旁路回流）；
  3. `resolve_candidate_models`（policy 与非 policy 两分支）——fallback 候选链不含高于 ceiling 的层，防止主选择被钳后经 fallback 回到重模型；
  4. force_tier 的早退分支同样钳制。
- **留痕**：`LLMSelection` 新增 `free_tier_downgrade: bool`；`reason` 追加 `free_tier_downgrade(<from>-><to>)`（经 `_create_selection` 的 rich reason 进入既有 `[LLMRouter] ... → <model> (...)` 日志行）；新增 `sparkle_llm_router_free_tier_downgrade_total{agent_role,from_tier,to_tier}`（`app/core/metrics.py`）；钳制触发时 loguru INFO 一条 `[LLMRouter] free_tier_downgrade: ...`。

### 2.2 `app/services/agent_grpc_service.py`（入口消费）

- `AgentServiceImpl._resolve_request_user_tier(request)`：`user_profile.is_pro` → free/pro；`extra_context.user_tier` 显式覆盖优先；异常保守回退 free。
- `StreamChat` 入口（最外层 try 之前）`set_request_user_tier(...)`，方法级 `finally` `reset_request_user_tier(token)`（early-return UNAUTHENTICATED 路径亦复位）。
- 与 wt5（首 token 优化）分域核对：wt5 改动 `orchestration/context_builder.py`、`orchestration/orchestrator.py`、`agents/standard_workflow.py`、`orchestration/execution_engine.py`、`orchestration/routing_engine.py`、`agents/standard_workflow.py`；本改动只触碰 `core/llm_router.py`、`core/metrics.py`、`config/settings.py`、`services/agent_grpc_service.py`，无同文件冲突。

### 2.3 `app/config/settings.py`

```python
FREE_TIER_DOWNGRADE_ENABLED: bool = True   # 免费用户能力层请求钳制总开关
FREE_TIER_MODEL_CEILING: str = "fast"      # 免费层允许的最高能力 tier（fast|standard）
```

### 2.4 `llm_security_wrapper` 未改动说明

wrapper 的配额/计量钩子（`_enforce_quota`/`_record_usage`/monitor）按 user_id 计量，与模型层无关；降级留痕在 router 层（reason/counter/日志）+ 既有 `sparkle_llm_router_selection_total{tier=...}` 已可让计费/统计看到「free 用户落在 fast 层」。改动面最小化，wrapper 保持 R2-08-02 收敛契约原样。

---

## 3. 网关侧

**零改动**（任务允许：信号已在链路则只消费）。依据见 §1 链路图；`go vet`/Go 测试均无需执行（无 Go 文件改动）。

---

## 4. 红-绿（单测）

新增 `backend/tests/unit/test_llm_router_free_tier.py`（14 项全绿）：

| 组 | 用例 | 断言要点 |
|---|---|---|
| 核心红绿 | `test_free_user_forced_max_clamps_to_fast_with_reason` | free + 强制 MAX → `model_key=deepseek_fast`（flash）、`tier=fast`、reason 含 `free_tier_downgrade(max->fast)`、`free_tier_downgrade=True`、Prometheus 计数器 +1 |
| 核心红绿 | `test_pro_user_forced_max_unchanged` | pro + 强制 MAX → `deepseek_reason`（v4-pro 位）、tier=max、无标记 |
| 兼容 | `test_unset_tier_keeps_legacy_behavior` | 未标记分层 → MAX 不钳（内部批量/定时任务不受影响） |
| 策略路径 | free/pro × DEEP_ANALYST deep 推理 | free → fast + `free_tier_downgrade(pro->fast)`；pro → pro/plus/max 不变 |
| 普通任务 | free/pro × GENERATION standard | free → fast；pro → standard 不变 |
| 候选链 | free 候选链两项 | fallback 链无重模型；force MAX 链 == FAST 层映射 |
| 配置面 | ceiling=standard / 非法 ceiling / kill-switch | max→standard；非法回退 fast；开关关闭不钳 |
| 入口信号 | `_resolve_request_user_tier` | is_pro→pro；extra_context `user_tier` 覆盖（free 压过 is_pro、premium 提权） |

定向回归（同进程约束下逐文件）：

```
tests/core/test_llm_router_policy.py           7 passed
tests/unit/test_llm_router_health_tracking.py  7 passed
tests/unit/test_llm_same_tier_fallback.py      passed
tests/unit/test_llm_tier_fallback_order.py     passed
tests/unit/test_llm_explicit_temperature.py    passed
tests/unit/test_credential_routing.py          passed
tests/unit/test_glm_batch_adaptive.py          passed
tests/core/test_agent_profiles_catalog.py      passed
tests/unit/test_llm_security_wrapper.py        passed
tests/unit/test_llm_security_wrapper_forwarding.py  passed
tests/unit/services/test_agent_grpc_service.py 5 passed / 3 FAILED（基线即红）
tests/unit/test_calibration_receipt.py、test_proto_dual_stack_service.py  passed
合计：93 passed, 3 failed
```

3 个失败（`test_stream_chat_errors_set_grpc_internal_and_error_finish_reason` / `test_stream_chat_timeout_sets_deadline_exceeded` / `test_stream_chat_empty_request_session_generates_single_fallback_and_metric`）经 `git stash` 基线复跑确认为 **b8f4e7d8 既有失败**，与本改动无关。

治理守卫：`run_all_rule_guards.sh` 结果 K/Z/BA/BG 四红，基线复跑逐一确认为既有红（另：守卫运行会改写 `docs/product/stage22_prompt_coverage_baseline.md`，已 `git checkout` 复原，不含入补丁）。

---

## 5. 真实调用行为验证（1 次真实请求）

free 上下文 + 强制 MAX + deep 模式（`.env` 真实 DeepSeek key，`DEEPSEEK_CHAT_MODEL=deepseek-flash`、`DEEPSEEK_REASON_MODEL=deepseek-v4-pro`）：

```text
[LLMRouter] free_tier_downgrade: max -> fast (agent=generation, task=None)
[LLMRouter] generation → deepseek-flash (强制tier=max | free_tier_downgrade(max->fast) [$0.0002/1k, tier=fast])
[LLMFallback] Attempt 1/3: model=deepseek-flash, reason=强制tier=max | free_tier_downgrade(max->fast) [..., tier=fast]
SEL_MODEL_KEY: deepseek_fast
SEL_TIER: fast
SEL_MODEL_NAME: deepseek-flash
SEL_REASON: 强制tier=max | free_tier_downgrade(max->fast) [$0.0002/1k, tier=fast]
SEL_FLAG: True
REPLY: 1+1等于2。
```

确认：路由日志 tier=fast、模型落 deepseek-flash（轻模型）、reason 留痕、真实调用成功。premium 路径（v4-pro 不变）由单测 `test_pro_user_forced_max_unchanged` 钉死，不再消耗真实请求预算。

---

## 6. 边界、配置与移交

**已知边界（记录在案，不阻塞）**：
1. `select_specific_model`（显式 model_key，如自定义专家 `get_llm_service_for_specific_model`）不钳——显式 key 是明确的人工选择，保留其语义；如需覆盖可后续在 workflow 侧按 is_pro 收敛自定义专家可选层。
2. REST SSE 路径（`chat.py` → wrapper `chat_stream_with_tools`）不经 gRPC StreamChat 入口，本设计只覆盖核心链路（Flutter → /ws/chat → 网关 → StreamChat）；REST 路径如需钳制，可由网关在 REST 透传 `user_tier` 后在 wrapper 层消费 `user_context`（已在 extra_context 覆盖通道上预留）。
3. proto3 未设 `user_profile` 的 StreamChat 调用方按 free 处理（默认分层=free 的产品语义）；网关 ws chatflow 恒填 profile，行为符合预期；如需对内网调用豁免，用 `FREE_TIER_DOWNGRADE_ENABLED=false` 熔断。
4. ceiling=fast 意味着免费用户全部能力层请求（含深度推理）落 flash；产品如需给免费用户保留甜点层，置 `FREE_TIER_MODEL_CEILING=standard` 即可，无需改码。

**文档更新建议（对应任务 5，未直接改动以防跨 worktree 冲突，请主控采纳后落笔）**：
- `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md`：新增条目「免费层降级只覆盖 gRPC StreamChat 链路；REST SSE 与显式 model_key 路径未钳制（§6.1/6.2）」。
- `backend/README.md`（或 env 配置清单）：登记 `FREE_TIER_DOWNGRADE_ENABLED`、`FREE_TIER_MODEL_CEILING` 两个新配置及默认值。
- 监控面板建议：`sparkle_llm_router_free_tier_downgrade_total` 按 `from_tier` 聚合，可回答「免费用户被降级掉的推理量」——商业上可直接用作 Pro 卖点转化漏斗。

**文件清单**：
- `backend/app/core/llm_router.py`（钳制核心 + contextvar + 留痕）
- `backend/app/core/metrics.py`（新计数器）
- `backend/app/config/settings.py`（2 个新配置）
- `backend/app/services/agent_grpc_service.py`（入口信号消费 + finally 复位）
- `backend/tests/unit/test_llm_router_free_tier.py`（新增 14 测）
- 本报告 + 补丁
