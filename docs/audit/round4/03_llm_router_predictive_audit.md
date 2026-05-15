# LLM Router + Predictive Service 深度架构审计

> 审计范围：`backend/app/core/llm_router.py`（1,231 行）、`backend/app/services/predictive_service.py`（1,970 行）、`backend/app/core/cost_controller.py`（272 行）
> 审计日期：2026-05-15
> 审计人：Claude Agent (独立审计)

---

## 第一部分：架构分析

### 1.1 LLM Router 架构概述

LLM Router 是整个 Sparkle 系统的模型选择中枢，负责将 Agent 角色 + 任务类型 + 推理模式映射到具体的 LLM 端点。

**模型池**：当前注册 23 个模型端点，覆盖 6 家提供商（Xiaomi / DeepSeek / Zhipu / Hunyuan / DashScope / SiliconFlow），分为 12 个 tier 层级。

**选择链路**：
```
AgentRole + TaskType → AgentProfile → ModelPolicy / specific_model / tier
  → complexity_analyzer 动态调整 → health filter → provider avoidance → LLMSelection
```

**Fallback 链**：`TOP → MAX → PRO → PLUS → STANDARD → FAST → FREE_FAST`（7 级，从高到低）

**健康追踪**：`ModelHealthState` 内存数据结构，5 次连续失败标记不健康，300 秒冷却后自动恢复。

### 1.2 Predictive Service 架构概述

Predictive Service 负责用户意图预测，包含四个子能力：

| 子能力 | 方法 | 模型依赖 |
|--------|------|----------|
| 参与度预测 | `predict_engagement()` | 纯规则（统计） |
| 难度预测 | `predict_difficulty()` | 纯规则（前置知识完成度） |
| 最佳时间推荐 | `recommend_optimal_time()` | 纯规则（加权时间模式） |
| 辍学风险检测 | `detect_dropout_risk()` | 纯规则（活跃度/完成率/学习时长） |
| 意图预测 | `get_next_intent_forecast()` | 规则基础 + LLM 增强双层 |
| 实时下一步 | `get_realtime_next_step_forecast()` | 规则关键词 + LLM 增强双层 |

**双层预测策略**：
- **快速规则层**：零延迟，基于 SQL 查询 + 统计计算
- **LLM 增强层**：尝试 3 个 tier 的模型（FREE → FREE_FAST → FAST），超时梯度为 0.25s → 0.45s → 2.2s

**缓存策略**：
- 长期预测：Redis 缓存 6 小时，软过期 30 分钟后触发后台 Celery 刷新
- 实时预测：无缓存（每次请求都重新计算）

### 1.3 Cost Controller 集成

`BudgetCircuitBreaker` 通过 Redis 按日追踪三类开销（LLM / RAG / Aurora），超预算时拒绝或降级操作。

**集成路径**：`llm_service.py` 在 `chat_with_tools()` 和 `stream_chat_with_tools()` 入口处调用 `is_llm_within_budget()` 做前置检查。预算耗尽时直接抛出 HTTP 429 / RuntimeError。

**关键发现**：`llm_router.py` 本身不集成 cost controller。Router 只做模型选择，不做预算判断。预算检查在 `llm_service` 层，意味着 Router 选择模型时完全不考虑当前预算状态。

### 1.4 Circuit Breaker 集成

不存在独立的 `circuit_breaker.py` 文件。断路器模式分布在两个位置：
1. **模型级健康追踪**：`llm_router.py` 中的 `ModelHealthState`（内存）
2. **预算级断路器**：`cost_controller.py` 中的 `BudgetCircuitBreaker`（Redis）

两者独立运行，没有联动机制。

### 1.5 性能特征

| 路径 | 开销 | 瓶颈 |
|------|------|------|
| Router 模型选择 | <1ms（纯内存 + dict 查找） | 无 |
| 参与度预测 | ~50-200ms（3-4 次 SQL 查询） | DB |
| 难度预测 | ~100-400ms（2-6 次 SQL 查询） | DB（N+1 查询） |
| 最佳时间推荐 | ~50-100ms（1 次 SQL 查询） | DB |
| 辍学风险检测 | ~50-150ms（3-4 次 SQL 查询） | DB |
| Foresight Snapshot 全量 | ~500ms-3s（串行聚合上述全部） | 串行 DB + LLM |
| 实时预测（LLM 增强） | 0.25-2.2s（3 次超时梯度尝试） | LLM 延迟 |
| 长期预测（LLM 增强） | 2-8s（GLM_BATCH 链） | LLM 延迟 |

---

## 第二部分：问题报告

### P0 级问题（数据丢失 / 安全 / 崩溃）

#### P0-01: ModelHealthState 健康上报从未被调用 — 健康机制形同虚设

- **位置**: `llm_router.py:1030-1041`（`report_model_failure` / `report_model_success`）
- **描述**: `report_model_failure()` 和 `report_model_success()` 在整个代码库中从未被调用。`llm_service.py` 不调用，`predictive_service.py` 也不调用。这意味着 `ModelHealthState` 的 `consecutive_failures` 永远为 0，`is_healthy` 永远为 `True`。
- **影响**: 模型健康筛选（`_is_model_healthy()`）永远通过所有模型。当某个模型持续故障时，Router 不会跳过它，每次请求都会打到已知故障的端点，直到调用方超时。整个降级链的入口被架空。
- **修复建议**: 在 `llm_service.py` 的所有 LLM 调用路径（`chat_with_tools`、`stream_chat_with_tools`）中，成功时调用 `llm_router.report_model_success(model_key)`，失败时调用 `llm_router.report_model_failure(model_key)`。同时在 `predictive_service.py` 的 `_request_prediction_payload` 中也添加上报。

---

#### P0-02: Predictive Service 直接调用 LLM 绕过预算检查

- **位置**: `predictive_service.py:847-849`、`predictive_service.py:1249-1251`
- **描述**: `_generate_realtime_llm_prediction` 和 `generate_long_horizon_forecast` 通过 `get_llm_service_for_specific_model()` 获取 LLM 服务实例后直接调用 `llm.chat()`。这个路径不经过 `llm_service.py` 的 `chat_with_tools()` 或 `stream_chat_with_tools()` 入口，因此跳过了 `is_llm_within_budget()` 预算前置检查。
- **影响**: 即使 LLM 每日预算已耗尽，Predictive Service 仍会持续调用 LLM 进行预测，导致实际花费不受预算限制。在极端情况下，预测子系统可能成为成本失控的通道。
- **修复建议**: 在 `_request_prediction_payload()` 方法中添加预算前置检查 `await is_llm_within_budget()`，超预算时直接返回 None，回退到规则预测。

---

### P1 级问题（正确性 / 可靠性）

#### P1-01: get_fallback_model() 链耗尽时返回已知故障模型（静默重用）

- **位置**: `llm_router.py:1128-1171`（`get_fallback_model`）
- **描述**: 当 fallback 链走到末端（`idx >= len(_FALLBACK_TIER_ORDER) - 1`，第 1147-1148 行）或者下一 tier 无健康模型时（第 1155-1156 行），函数直接返回 `failed_selection` —— 即触发降级的那个已知失败的选择。返回的 `LLMSelection` 的 `is_fallback` 标志不会被设为 `True`，调用方无法区分这是有效的降级结果还是无效的原始选择。
- **影响**: 调用方收到一个看似有效的 `LLMSelection`，会尝试再次调用已知失败的模型，导致请求级死循环（调用 → 失败 → fallback → 返回同一个 → 调用 → 失败 ...）。
- **修复建议**: 链耗尽时返回 `None` 或抛出明确异常，而不是返回原选择。调用方应检查返回值为 `None` 后走最终兜底路径（如返回固定错误响应）。同时应将 `is_fallback` 设为 `True` 并在 reason 中标注 "fallback chain exhausted"。

---

#### P1-02: GLM_BATCH / SPECIALIST / FREE / FREE_REASONING tier 不在 Fallback 链中

- **位置**: `llm_router.py:121-129`（`_FALLBACK_TIER_ORDER`）
- **描述**: `_FALLBACK_TIER_ORDER` 只包含 `[TOP, MAX, PRO, PLUS, STANDARD, FAST, FREE_FAST]`。但系统还有 `FREE`、`FREE_REASONING`、`GLM_BATCH`、`SPECIALIST` 四个 tier。当这些 tier 的模型需要降级时：
  - `get_fallback_model()` 在 `_FALLBACK_TIER_ORDER.index(current_tier)` 处抛出 `ValueError`
  - 被 `except ValueError: return failed_selection` 捕获（第 1145-1146 行）
  - 返回原始失败的模型
- **影响**: Predictive Service 的实时预测使用 `FREE`/`FREE_FAST`/`FAST` tier，长期预测使用 `GLM_BATCH` tier。如果这些模型故障，降级机制完全失效，系统无法自动切换到更便宜的可用模型。
- **修复建议**: 将 `_FALLBACK_TIER_ORDER` 扩展为 `[TOP, MAX, PRO, PLUS, STANDARD, GLM_BATCH, FAST, FREE_FAST, FREE_REASONING, FREE, SPECIALIST]`，或为非标准 tier 定义独立的降级映射表。

---

#### P1-03: 辍学风险中 total_count==0 时 completion_rate 默认 0.5 — 新用户被误判

- **位置**: `predictive_service.py:723-727`（`detect_dropout_risk`）
- **描述**: 当用户在最近 14 天没有任何任务（`total_count == 0`）时，`completion_rate` 默认为 `0.5`（50%）。这个值被送入风险评分：
  - `completion_rate < 0.6` → 加 15 分
  - 结合 `recent_7d_count == 0` → 再加 30 分
  - 总计 45 分 → `risk_level = "medium"`
- **影响**: 所有新注册用户（或 14 天内未创建任务的用户）都会被标记为 "medium" 辍学风险，触发不必要的干预消息。这是一个系统性偏差，将新用户冷启动误判为参与度下降。
- **修复建议**: 当 `total_count == 0` 时，`completion_rate` 应设为 `None` 或 `1.0`（无数据 = 不纳入评分），并在风险评分中跳过完成率维度。同时增加数据充分性检查（如 `total_count < 3` 时不计算完成率）。

---

#### P1-04: predict_difficulty 存在 N+1 查询问题

- **位置**: `predictive_service.py:493-509`（`predict_difficulty`）
- **描述**: 对每个前置知识节点（最多 5 个），都单独执行一次 `select(UserNodeStatus)` 查询。这是典型的 N+1 查询模式。
- **影响**: 每次难度预测执行 2（topic + prerequisites）+ 最多 5（per-prerequisite status）= 7 次 SQL 查询。在 `build_foresight_snapshot` 的串行调用中，这会显著增加总延迟。
- **修复建议**: 将 5 次单独查询合并为一次 `WHERE user_id = ? AND node_id IN (...)` 批量查询。

---

#### P1-05: ModelHealthState 仅内存存储 — 进程重启后健康状态丢失

- **位置**: `llm_router.py:69-97`（`ModelHealthState`）
- **描述**: `ModelHealthState` 存储在 `LLMRouter._model_health` 字典中（`llm_router.py:135`），这是一个纯内存结构。Python gRPC 进程重启后，所有健康状态被重置为 `healthy=True`。
- **影响**: 如果某个模型因为上游服务故障被标记为不健康，进程重启后 Router 会立即将请求路由到这个仍然故障的模型。在滚动部署场景下，每个新实例都会经历一轮 "故障 → 发现 → 标记不健康" 的循环，持续数分钟（5 次连续失败 * 平均延迟）。
- **修复建议**: 将健康状态持久化到 Redis（与 `BudgetCircuitBreaker` 的模式一致），设置 TTL 与现有 `RECOVERY_SECONDS` 一致（300s）。进程启动时从 Redis 恢复状态。

---

#### P1-06: _apply_provider_avoidance 过滤为空时回退到原始列表（含被排除的 provider）

- **位置**: `llm_router.py:946-961`（`_apply_provider_avoidance`）
- **描述**: 当过滤后结果为空（所有候选模型都属于被排除的 provider），函数返回未过滤的原始列表（第 961 行 `return filtered or candidates`）。这意味着 `avoid_providers` 参数在某些情况下会被静默忽略。
- **影响**: 如果调用方明确要求避免某个 provider（如该 provider 已知故障），在极端情况下（所有候选都属于该 provider），Router 仍会选择被排除的 provider 的模型。
- **修复建议**: 过滤为空时返回空列表，由调用方决定如何处理（如走降级路径）。或者在选择逻辑中增加跨 tier 搜索。

---

#### P1-07: build_foresight_snapshot 串行执行所有预测 — 无并行化

- **位置**: `predictive_service.py:188-194`（`build_foresight_snapshot`）
- **描述**: `engagement`、`optimal_time`、`dropout_risk`、`next_intent`、`subject_difficulty` 五个预测任务完全串行执行，每个都涉及独立的 SQL 查询。
- **影响**: Foresight Snapshot 的总延迟等于所有子预测延迟之和。从性能分析来看，可能在 500ms-3s 之间。对于需要低延迟返回的场景（如 dashboard 加载），这是一个显著瓶颈。
- **修复建议**: 使用 `asyncio.gather()` 并行执行 `predict_engagement`、`recommend_optimal_time`、`detect_dropout_risk`、`get_next_intent_forecast`、`_build_subject_difficulty_projection`。注意需要为每个任务使用独立的 DB session 或确保共享 session 的并发安全性。

---

#### P1-08: _adjust_to_pattern 只向前调整，可能预测到 7 天后

- **位置**: `predictive_service.py:432-454`（`_adjust_to_pattern`）
- **描述**: 当预测时间不是最常见的星期时，`(most_common_weekday - current_weekday) % 7` 只做正向偏移。如果当前是周四（3），最常见是周一（0），偏移量 = `(0 - 3) % 7 = 4`，预测到 4 天后。但用户可能本周一已经过去，合理的预测应该是下周一（仍然 4 天后，但语义上可能不合理——如果用户已经 5 天不活跃，预测 4 天后再活跃没有意义）。
- **影响**: 参与度预测可能在用户已经不活跃多天的情况下，仍预测到较远的未来日期，导致系统误判"还有时间"而不及时干预。
- **修复建议**: 增加对 "已经超过平均间隔" 场景的处理。当距离上次活动已超过平均间隔时，应优先预测最近的可用时间窗口，而不是等待最常见模式。

---

### P2 级问题（性能 / 质量）

#### P2-01: 实时预测关键词匹配仅支持中文 — 多语言不覆盖

- **位置**: `predictive_service.py:1132-1182`（`_build_rule_based_realtime_next_step`）
- **描述**: 关键词匹配硬编码了中文关键词（`"任务"、"待办"、"计划"、"复习"、"报错"、"错题"、"翻译"` 等），只有 `"why"、"error"、"bug"、"todo"、"task"、"study"、"plan"、"translate"` 等少量英文关键词。
- **影响**: 用户使用英文输入时（如 "I want to review my progress"），无法匹配到 "复盘/review" 语义，默认回退到 `continue_chat`。在 i18n 场景下，非中英文用户完全没有关键词覆盖。
- **修复建议**: 将关键词映射抽取为可配置的多语言映射表，或使用 i18n ARB 文件中的语义标签。

---

#### P2-02: LLM Router 不集成 Cost Controller — 无法做预算感知路由

- **位置**: `llm_router.py` 全文
- **描述**: `LLMRouter.select_model()` 完全不考虑当前预算状态。即使 LLM 日预算已消耗 95%，Router 仍会选择 TOP/MAX tier 的高成本模型。预算检查只在 `llm_service.py` 的入口处做 "是/否" 二元判断（要么允许，要么 429）。
- **影响**: 缺少渐进式成本控制。合理的做法是：预算 >80% 时自动降级到 FAST tier，>95% 时降级到 FREE_FAST，100% 时拒绝。当前的二元策略导致成本控制粒度过粗。
- **修复建议**: 在 `select_model()` 中增加可选的 `budget_utilization` 参数（由调用方从 `cost_controller` 获取），当利用率超过阈值时自动降级 tier。

---

#### P2-03: 预测置信度评分缺乏校准

- **位置**: `predictive_service.py` 多处
- **描述**:
  - `predict_engagement`: 置信度基于 `1.0 - (std / avg)` 的数学公式，但没有与实际预测准确率做校准
  - `_build_rule_based_next_intent`: 硬编码 `0.78`/`0.68`/`0.61`
  - `_build_rule_based_realtime_next_step`: 硬编码 `0.66`-`0.82`
  - 这些值不是从数据中学习的，而是工程估算
- **影响**: 置信度分数无法反映真实预测质量。硬编码的 0.78 可能让系统误以为预测很可靠，而实际准确率可能很低。下游逻辑（如 JITAI 触发、干预消息发送）依赖这些置信度做决策。
- **修复建议**: 接入 `get_prediction_analytics()` 的 CTR 数据，定期校准置信度阈值。至少应在置信度旁标注来源（"statistical" vs "heuristic" vs "llm"），便于下游区分。

---

#### P2-04: predict_engagement 的 _adjust_to_pattern 使用简单 max 投票

- **位置**: `predictive_service.py:440-441`
- **描述**: `max(weekday_pattern, key=weekday_pattern.get)` 选择出现次数最多的星期，但如果多个星期并列最高（例如周一和周三各出现 5 次），`max()` 只返回字典序靠前的一个。对于 hour_pattern 同理。
- **影响**: 预测时间可能系统性偏向字典序靠前的星期/小时，而不是真正最可能的时间窗口。
- **修复建议**: 对并列最高值做随机选择或选择距离当前最近的。

---

#### P2-05: LLM Router 的 _lock 使用 threading.RLock 但所有调用来自 async 上下文

- **位置**: `llm_router.py:132`（`self._lock = threading.RLock()`）
- **描述**: `LLMRouter` 使用 `threading.RLock` 保护 `_available_models` 和 `_model_health`。但 Python 的 async 事件循环是单线程的，`RLock` 在 async 上下文中不提供实际的并发保护（它只防止线程级竞争，不防止协程级让步竞争）。
- **影响**: 如果有多个协程并发调用 `select_model()` + `report_model_failure()`（通过 `await` 让步），`RLock` 无法保证原子性。在当前单线程 asyncio 模型下实际不会出问题，但如果未来引入多线程（如 gRPC 的线程池），可能产生竞争。
- **修复建议**: 如果确定只在 asyncio 事件循环中使用，可以移除 `RLock`（减少不必要的锁开销）。如果需要支持多线程，应使用 `asyncio.Lock` 或确保在多线程路径中正确使用 `RLock`。

---

#### P2-06: 长期预测后台刷新的 lock TTL 过长

- **位置**: `predictive_service.py:1915`（`set(lock_key, "1", ex=300, nx=True)`）
- **描述**: Celery 任务触发后，Redis lock 的 TTL 设为 300 秒（5 分钟）。如果 Celery worker 处理延迟或任务排队，这个 lock 可能过期后被另一个请求重新获取，导致同一用户触发多个并行长期预测任务。
- **影响**: 同一用户可能产生 2-3 个并行的 LLM 调用（GLM_BATCH tier），浪费预算且可能产生缓存竞争。
- **修复建议**: lock TTL 应与实际预测耗时匹配（建议 60 秒），或使用 Celery task deduplication 机制替代 Redis lock。

---

#### P2-07: Token 计费使用混合费率而非分输入/输出

- **位置**: `cost_controller.py:89-101`（`_LLM_TIER_PRICING_PER_1K`）
- **描述**: LLM 成本估算使用 `(prompt_tokens + completion_tokens) / 1000 * blended_rate` 的混合费率。实际上大多数 LLM 提供商的 input/output 价格差异可达 3-5 倍（如 DeepSeek Reasoner: input $3/M, output $15/M）。
- **影响**: 成本估算偏差大。对于长上下文 + 短回复的场景（如 RAG），混合费率会高估成本；对于短输入 + 长输出的场景（如计划生成），会低估成本。
- **修复建议**: 将 `_LLM_TIER_PRICING_PER_1K` 拆分为 `_LLM_TIER_INPUT_PRICING` 和 `_LLM_TIER_OUTPUT_PRICING`，按实际 token 类型计费。

---

#### P2-08: Tier 到成本的映射（cost_controller）与 Router 的 tier 名称通过字符串子串匹配

- **位置**: `cost_controller.py:248-253`（`record_llm_cost`）
- **描述**: `record_llm_cost` 通过遍历 `_LLM_TIER_PRICING_PER_1K` 的 key 做 `if tier_key in model_lower` 子串匹配来确定 tier。例如 model_key = "glm_4_7_flash_thinking"，匹配 "fast" 会命中（model_lower 包含 "flash" 但不包含 "fast"）。
- **影响**: 实际上 "glm_4_7_flash_thinking" 的 tier 是 `FREE_FAST`，但 `model_lower = "glm_4_7_flash_thinking"`，遍历 tier key 时不会匹配 "free_fast"（因为 model_lower 不包含 "free_fast"），也不会匹配 "free"（因为不包含 "free"）。最终会匹配到 "standard"（默认值），导致这个免费模型被按 standard 费率计费。
- **修复建议**: 改为从 `LLMSelection.config.tier` 直接获取 tier 值，而不是从 model_key 字符串猜测。在 `record_llm_cost` 中增加 `tier` 参数。

---

## 问题汇总

| 编号 | 级别 | 位置 | 摘要 |
|------|------|------|------|
| P0-01 | P0 | llm_router.py:1030-1041 | ModelHealthState 健康上报从未被调用，健康筛选机制完全失效 |
| P0-02 | P0 | predictive_service.py:847,1249 | Predictive Service 绕过 LLM 预算检查，成本不受控 |
| P1-01 | P1 | llm_router.py:1128-1171 | fallback 链耗尽时返回已知故障模型，无信号告知调用方 |
| P1-02 | P1 | llm_router.py:121-129 | GLM_BATCH/SPECIALIST/FREE/FREE_REASONING 不在 fallback 链中 |
| P1-03 | P1 | predictive_service.py:723-727 | 辍学风险 completion_rate 默认 0.5 导致新用户被误判 |
| P1-04 | P1 | predictive_service.py:493-509 | predict_difficulty N+1 查询 |
| P1-05 | P1 | llm_router.py:69-97 | ModelHealthState 仅内存，进程重启后丢失 |
| P1-06 | P1 | llm_router.py:946-961 | provider avoidance 过滤为空时回退到包含被排除 provider 的列表 |
| P1-07 | P1 | predictive_service.py:188-194 | foresight snapshot 串行执行，延迟叠加 |
| P1-08 | P1 | predictive_service.py:432-454 | 参与度预测只向前调整，不处理已超期场景 |
| P2-01 | P2 | predictive_service.py:1132-1182 | 实时预测关键词仅覆盖中英文，多语言不覆盖 |
| P2-02 | P2 | llm_router.py 全文 | Router 不集成 Cost Controller，无法做预算感知路由 |
| P2-03 | P2 | predictive_service.py 多处 | 置信度评分缺乏校准，硬编码值不反映真实准确率 |
| P2-04 | P2 | predictive_service.py:440-441 | 时间模式 max 投票对并列最高值处理不当 |
| P2-05 | P2 | llm_router.py:132 | threading.RLock 在 async 上下文中可能不提供实际保护 |
| P2-06 | P2 | predictive_service.py:1915 | 长期预测后台刷新 lock TTL 过长（300s） |
| P2-07 | P2 | cost_controller.py:89-101 | Token 计费使用混合费率，与实际 input/output 差价偏差大 |
| P2-08 | P2 | cost_controller.py:248-253 | tier 到费率通过字符串子串匹配，存在误匹配风险 |

**总计**：P0 × 2，P1 × 8，P2 × 8

---

## 关键已知问题验证结果

| 已知问题 | 验证结果 |
|---------|---------|
| `get_fallback_model()` line 1128 返回原始失败选择 | **已确认**。链耗尽和 tier 不在链中两种情况都会返回 `failed_selection`。 |
| `ModelHealthState` 仅内存 | **已确认**。无 Redis/DB 持久化，进程重启即丢失。 |
| `detect_dropout_risk` line 726 `completion_rate` 默认 0.5 | **已确认**。新用户/无任务用户会被误判为 medium 风险。 |
| （补充发现）`report_model_failure`/`report_model_success` 从未被调用 | **已确认**。全代码库搜索无调用点，健康机制完全失效。 |
