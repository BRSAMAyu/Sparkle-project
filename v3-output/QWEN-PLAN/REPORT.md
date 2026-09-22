# QWEN-PLAN · 主力模型切换 GLM → Qwen（通义千问）选型与实施报告

- Worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt80`
- 日期: 2026-09-22 ｜ Worker: Qwen 主力选型 ｜ 代码基线: `76677063` (X-07 P2-1)
- Patch: `v3-output/QWEN-PLAN/changes.patch`（678 行）
- 零真实 API 调用（纯配置级改动 + 单测）；连通性验证留主会话填 key 后执行

---

## 1. 现状表（改动前）

来源：`backend/app/core/llm_router.py`、`agent_profiles.py`、`config/settings.py`、`core/budget_matrix.py`

### 1.1 各用途层模型（改动前）

| 用途层 (ModelTier) | 候选链（首位=实际主力） | 主力模型 | 实际价格锚点 (cost_per_1k, USD) |
|---|---|---|---|
| FAST（轻对话/首token） | deepseek_fast → dashscope_fast → xiaomi_chat → glm_4_7_flash_no_thinking | deepseek-flash | 0.0002 |
| STANDARD（甜点轻思考） | xiaomi_standard_thinking → dashscope_standard_thinking → deepseek_chat* | mimo-v2-flash | 0.0002 |
| PLUS（高质量非思考） | dashscope_chat → glm_4_7_plus | qwen3.8-flash（配置名） | 0.0004 |
| PRO/REASONING（深推理） | dashscope_reason → glm_4_7_pro | qwen3.8-flash（配置名） | 0.001 |
| MAX（显式深档） | deepseek_reason → glm_5_max | deepseek-v4-pro | 0.008 |
| TOP（超高层） | glm_5_1_top（单点） | glm-5.1 | 0.008 |
| FREE_FAST（免费试探） | glm_4_7_flash_thinking → glm_4_5_air_free → siliconflow_free | glm-4.7-flashx | 0.0005 |
| FREE（后台） | siliconflow_free（Qwen/Qwen3.5-4B，$0） | — | 0.0 |
| GLM_BATCH（异步分析车道） | minimax_m3_batch*(key-gated) → glm_4_7_no_thinking → glm_4_7_thinking → glm_4_5_air_batch → glm_4_6_batch | glm-4.7 | 0.001–0.002 |
| SPECIALIST（OCR/翻译） | zhipu_ocr / siliconflow_ocr / hunyuan_translate / siliconflow_translate | — | 0.001/0.0005 |
| 嵌入 | EMBEDDING_PROVIDER=dashscope, text-embedding-v4, dim=1024（已是阿里云现货） | — | — |

\* STANDARD 首位由 `LLM_PROVIDER`（默认 deepseek）经 provider-preference 重排产生；PLUS/PRO 恒为 dashscope 置首。
\* MiniMax 仅在 `MINIMAX_API_KEY` 配置时注册。

### 1.2 Tier 降级链（不变，本次未改）

`TOP → MAX → PRO → PLUS → STANDARD → FAST → FREE_FAST → (FREE_REASONING→FREE_FAST) → GLM_BATCH → SPECIALIST`
（`_FALLBACK_TIER_ORDER` + `get_fallback_model`；FREE_REASONING 归一 FREE_FAST；REASONING 归一 PRO）

### 1.3 预算矩阵（O-07，本次未改限额）

| entitlement | max_total_tokens | max_cost_usd | max_tool_calls | max_duration |
|---|---|---|---|---|
| free | 150,000 tok/run | $0.5 | 50 | 1800s |
| pro | 600,000 tok/run | $2.0 | 200 | 3600s |

免费层能力钳制：`FREE_TIER_MODEL_CEILING=fast`（free 用户最高到 FAST 层）。

---

## 2. Qwen 现货表（2026-09-22 官方页实测，北京地域）

来源：阿里云百炼 help 页（models / text-generation-model / billing / embedding / rate-limit），单位元/百万 Token。

| 模型 | 输入 | 输出 | 上下文 | 思考 | 备注 |
|---|---|---|---|---|---|
| **qwen3.8-max**（旗舰） | 12 | 36 | 1M | 支持（同价） | FC/结构化输出/内置工具全支持；Batch 半价；动态限流；新户免费 100万 tok/90天 |
| **qwen3.7-plus** | 非思考 2（限时8折 1.6） | 2（1.6） | 1M | 混合（**思考=4×非思考**，8/8） | RPM 30,000 / TPM 5M；≤256K 阶梯；Batch 半价 |
| **qwen3.8-flash** | 0.8 | 2.7 | 1M | 混合（**同价**） | 缓存折扣；动态限流；思考不涨价是 flash 系独有 |
| **qwen3.7-flash** | ≤32K: 0.2；32K-256K: 0.6 | 0.8 / 2.4 | 1M | 混合（同价） | 阶梯计价按单请求输入总量；Batch 半价 |
| qwen-turbo（旧版） | 0.3 | 0.6 | 128k | 同价 | 已被 flash 系替代，不选 |
| qwen3.5-plus / 3.5-flash | 0.8 / 阶梯 | — | 1M | 混合 | 上一代，保留为快照可选 |
| text-embedding-v4（嵌入） | 0.5/百万（$0.00007/1k） | — | — | — | 64–2048 维，默认 1024=我们现用；Batch 0.25 |
| qwen3.7-text-embedding | 0.5/百万 | — | — | — | 最高 2560 维（暂不需要） |

**接口**：DashScope OpenAI 兼容模式 `https://dashscope.aliyuncs.com/compatible-mode/v1`（旧域名仍可用）+ `DASHSCOPE_API_KEY`，`/chat/completions` 即用；思考控制官方参数为 `enable_thinking`（见 §7 诚实申报 #3）。

**能力档位结论**：qwen3.8-max=旗舰档（对标 GLM-5.x TOP）；qwen3.7-plus=高质量档（对标 GLM-4.7 Pro/Plus）；qwen3.8-flash=甜点思考档；qwen3.7-flash=轻量快档。全系 1M 上下文，覆盖我们最深 run 的窗口需求。

---

## 3. 选型映射表（改动后）

| 用途层 | 改后候选链（首位=主力） | 选型论证 |
|---|---|---|
| FAST | **dashscope_fast (qwen3.7-flash)** → deepseek_fast → xiaomi_chat → glm_4_7_flash_no_thinking | 轻对话输入占主导，0.2 元/M 输入是全现货最低；比原 deepseek-fast 便宜约 65%；1M 上下文 + 思考不涨价留升级余量 |
| STANDARD | **dashscope_standard_thinking (qwen3.8-flash)** → deepseek_chat → xiaomi_standard_thinking | flash 系「思考同价」独特卖点：轻思考车道 0.8/2.7 无思考溢价，是甜点层最优解 |
| PLUS | **dashscope_chat (qwen3.7-plus 非思考)** → glm_4_7_plus | 高质量非思考 2/2（8折 1.6），较原配置计价 -25%；RPM 30k/TPM 5M 限流宽裕 |
| PRO | **dashscope_reason (qwen3.7-plus 思考)** → glm_4_7_pro | 思考 8/8（$0.0011/1k）深推理档，与原计价持平但能力升级到 3.7 代；1M 上下文利好深分析 |
| MAX | **qwen3_8_max (qwen3.8-max)** → deepseek_reason → glm_5_max | 旗舰 12/36 blended $0.0034，较原 MAX 首位 deepseek-v4-pro($0.008) **-58%**；1M 上下文 |
| TOP | **qwen3_8_max_top (qwen3.8-max)** → glm_5_1_top | TOP 原为 glm-5.1 单点无降级；现在 Qwen 旗舰置首 + GLM 保留，消除单点 |
| FREE_FAST | **dashscope_fast (qwen3.7-flash)** → siliconflow_free(Qwen3.5-4B,$0) → glm_4_7_flash_thinking → glm_4_5_air_free | 免费试探层升级到正牌 3.7-flash（路由 JSON 稳定性 > 4B 小模型），$0 的 siliconflow Qwen4B 作免费兜底；GLM 免费通道保留 |
| FREE_REASONING | glm_4_7_flash_thinking → glm_4_5_air_free | **不动**：Qwen 无对应免费通道，GLM 保留待用正是为此 |
| GLM_BATCH | **qwen3_7_flash_batch (qwen3.7-flash, key-gated)** → minimax_m3_batch(key-gated) → glm_4_7_no_thinking → glm_4_7_thinking → glm_4_5_air_batch → glm_4_6_batch | 异步分析车道 Qwen 置首（主力决策）；MiniMax 免费档保留次位；GLM 池全保留。⚠️ 想免费优先可用 `LLM_TIER_GLM_BATCH=minimax_m3_batch,qwen3_7_flash_batch,glm_4_7_no_thinking,...` 一行 env 回调，零代码 |
| 嵌入 | **不变**：dashscope text-embedding-v4 (1024 维, $0.00007/1k) | 本就是阿里云现货且是 Qwen 家族；无需动 |
| 嵌入 backup | siliconflow Qwen3-Embedding-4B | 不变 |

**GLM 条目处置**：全部 11 个 glm_* ModelConfig 条目 + tier 链位置**保留不删**，代码内标注「保留待用」；回切 = `.env` 设 `LLM_PROVIDER=zhipu` / `LLM_TIER_*` 覆盖，零代码。

---

## 4. 预算影响估算（对照 O-07 限额）

计价假设：CNY/USD=7.1；blended = (输入+输出)/2 等权；qwen3.7-plus 按原价（8 折是限时窗口，保守记账）。

### 4.1 各车道 cost_per_1k 变化（USD/1k）

| 层 | 改前主力 | 改后主力 | Δ |
|---|---|---|---|
| FAST | deepseek_fast 0.0002 | qwen3.7-flash 0.0001 | **-50%** |
| STANDARD | xiaomi_standard 0.0002 | qwen3.8-flash 0.00025 | +25% |
| PLUS | dashscope_chat 0.0004 | qwen3.7-plus 0.0003 | **-25%** |
| PRO | dashscope_reason 0.001 | qwen3.7-plus思考 0.0012 | +20% |
| MAX | deepseek_reason 0.008 | qwen3.8-max 0.0034 | **-58%** |
| TOP | glm_5_1_top 0.008 | qwen3.8-max 0.0034 | **-58%** |
| BATCH | glm-4.7 0.001 | qwen3.7-flash 0.0001 | **-90%**（Batch API 半价后还可再低） |

### 4.2 对照 O-07 限额的饱和分析

**free run（150k tok / $0.5）单模型饱和成本：**

| 跑满 150k 的车道 | 改后 | 改前（改前首位） |
|---|---|---|
| FAST（=free 用户天花板） | **$0.015** | $0.030（deepseek_fast） |
| STANDARD | $0.038 | $0.030 |
| PLUS | $0.045 | $0.060 |
| PRO | $0.18 | $0.15 |
| MAX | $0.51（略超 $0.5 闸） | $1.20（deepseek_reason） |

- 免费用户被 `FREE_TIER_MODEL_CEILING=fast` 钳制，free 饱和 run 成本 **$0.03 → $0.015（-50%）**。
- 付费主航道（FAST/STANDARD/PLUS/PRO）饱和均 ≤ $0.18，安全边际 ≥ 2.7×。
- MAX 饱和 $0.51 略超 $0.5：由 `max_cost_usd` 硬闸截断（设计语义），且较改前 $1.20 大幅改善；`max_total_tokens` 150k 与 `$0.5` 在 MAX 层不再互相矛盾到失控。
- pro run（600k/$2.0）：PRO 层饱和 $0.72、MAX 层 $2.04 ≈ 闸口，同样由 max_cost_usd 兜底。

**结论：切换后预算面整体更优——贵层大降（MAX/TOP -58%、批处理 -90%）、免费层减半；唯一上涨的 PRO(+20%)/STANDARD(+25%) 换取代际能力升级且远在限额内。**

---

## 5. .env 键清单（真实 key 主会话填）

```bash
# ===== 必填（Qwen 主力切换）=====
DASHSCOPE_API_KEY=sk-__________________   # 阿里云百炼 API-KEY（百炼控制台 → API-KEY 管理）

# ===== 可选覆盖（以下全部已有代码内默认值，无需配置即生效）=====
# LLM_PROVIDER=qwen                        # 默认已切 qwen
# DASHSCOPE_FAST_MODEL=qwen3.7-flash        # FAST/免费层
# DASHSCOPE_STANDARD_MODEL=qwen3.8-flash    # STANDARD 甜点层
# DASHSCOPE_CHAT_MODEL=qwen3.7-plus         # PLUS 层（非思考）
# DASHSCOPE_REASON_MODEL=qwen3.7-plus       # PRO 层（思考）
# DASHSCOPE_MAX_MODEL=qwen3.8-max           # MAX 层
# DASHSCOPE_TOP_MODEL=qwen3.8-max           # TOP 层
# DASHSCOPE_BATCH_MODEL=qwen3.7-flash       # glm_batch 异步车道（key-gated）
# EMBEDDING_PROVIDER=dashscope              # 已是默认
# EMBEDDING_MODEL=text-embedding-v4         # 已是默认（dim=1024，EMBEDDING_DIM 不变）

# ===== GLM 回切（保留待用，需要时启用，零代码）=====
# ZHIPU_API_KEY=__________________          # GLM 车道 key（可留作降级/回切）
# LLM_PROVIDER=zhipu
# LLM_TIER_GLM_BATCH=minimax_m3_batch,qwen3_7_flash_batch,glm_4_7_no_thinking,...  # 车道优先级回调
```

连通性验证清单（主会话填 key 后）：① 网关→引擎 chat 链路走 `dashscope_standard_thinking`；② STREAM 首 token 延迟（qwen3.7-flash 应 <400ms）；③ PRO 思考车道思维链可见性（见 §7 #3）；④ batch 车道 `lane_available` 探针；⑤ embedding 1024 维回归。

---

## 6. 代码改动与测试统计

### 6.1 改动清单（`git diff` = changes.patch）

| 文件 | 改动 |
|---|---|
| `backend/app/config/settings.py` | `LLM_PROVIDER` 默认 deepseek→**qwen**；DASHSCOPE 5 个模型默认值切 2026 现货（CHAT/REASON→qwen3.7-plus，FAST→qwen3.7-flash，STANDARD 保持 qwen3.8-flash）；**新增** `DASHSCOPE_MAX_MODEL/DASHSCOPE_TOP_MODEL/DASHSCOPE_BATCH_MODEL`；生产启动闸 `_llm_keys` 增补 `DASHSCOPE_API_KEY` |
| `backend/app/core/llm_router.py` | 新增 `qwen3_8_max`(MAX)、`qwen3_8_max_top`(TOP) 条目；新增 key-gated `qwen3_7_flash_batch`(GLM_BATCH，MiniMax 同款 gate 先例)；dashscope 4 条目价格刷新为 2026 实价；tier 链重排：FAST/FREE_FAST/MAX/TOP/GLM_BATCH Qwen 置首；GLM 条目全部保留并加「保留待用」注释 |
| `backend/app/core/agent_profiles.py` | 4 个 FREE_FAST profile（ROUTER/RETRIEVAL/SEARCH_AGENT/STUDY_BUDDY）preferred_models Qwen 置首、GLM 保留；模块头注明 dashscope 键=Qwen 车道 |
| `backend/app/services/capsule_generation_service.py` | `_normalize_explicit_model` 接受 `qwen3_7_flash_batch`（GLM fallback，MiniMax 同款先例） |
| `backend/tests/core/test_llm_router_qwen.py` | **新增** 25 例（见 6.2） |
| `backend/tests/unit/test_llm_router_free_tier.py` | 契约锚点更新：FAST 首位→dashscope_fast、MAX 首位→qwen3_8_max |
| `backend/tests/unit/test_deep_analysis_tier_routing.py` | 契约锚点更新：deep_analysis MAX→qwen3_8_max、逃生阀 FAST→dashscope_fast（4 处断言+文档） |
| `backend/tests/unit/test_e07_adaptive_routing.py` | HEAD/RIVAL 常量随 FAST 首位互换 |

### 6.2 新增测试（25 例，全程 mock 零真实请求）

`tests/core/test_llm_router_qwen.py`：
- **TestQwenModelEntries (3)**：旗舰条目注册/定价锚点/四车道模型名、GLM 11 条目保留不删
- **TestQwenPrimaryRouting (5)**：能力层 Qwen 置首、GENERATION→dashscope_standard_thinking、DEEP_ANALYST→PRO 思考车道、force MAX/TOP→旗舰、GLM 仍可显式选中（回切演练面）
- **TestQwenFallbackChain (4)**：TOP→MAX→PRO 逐级回落落点、MAX 链保留 deepseek/glm、旗舰熔断 10 次后链内回落
- **TestQwenBatchLane (4)**：key-gate 注册/不注册两态、永不进主聊天能力层、双 key 时 Qwen>MiniMax>GLM
- **TestBudgetMatrixQwen (4)**：O-07 free 150k/$0.5 限额不变、四主航道饱和 < $0.5、MAX 饱和 $0.51 边际场景受硬闸语义保护
- **TestQwenProfiles (2)**：FREE_FAST profile 首选 qwen 且 GLM 保留、tier 链同构
- **TestQwenClientKwargs (2)**：Qwen selection 不带 zhipu extra_body、GLM 车道 wire 语义不受切换影响

### 6.3 回归运行（串行 10 批，全部绿）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | router_policy / minimax_batch_routing / glm_thinking | 26 passed |
| 2 | llm_router_free_tier / deep_analysis_tier_routing / e07_adaptive_routing | 39 passed |
| 3 | o04_entitlement / standard_workflow_generation / capability_lane | 100 passed |
| 4 | batch_worklane / glm_batch_adaptive / llm_router_health_tracking | 48 passed |
| 5 | llm_same_tier_fallback / llm_explicit_temperature / e07_health_hysteresis | 22 passed |
| 6 | o07_budget_matrix_and_ux / x06_run_budget / agent_profiles_catalog | 57 passed |
| 7 | llm_tier_fallback_order / llm_prediction_routing / reviewer_agent_phase62 | 9 passed |
| 8 | reviewer_system_error / review_error_skips / llm_wrapper_signature | 45 passed |
| 9 | review_reflection_r2 / memory_commitment / prompt_preference / ai_ops_dashboard | 39 passed |
| 10 | credential_routing（含新增 Qwen 启动闸用例）/ capability_selection_policy / mimo_integration | 29 passed |
| — | **test_llm_router_qwen.py（含 batch/capsule 例后重跑）** | **25 passed** |
| 附 | embedding_fail_closed / predictive_realtime_degrade | 21 passed |

合计 **~460 assertions-level 用例全绿，0 failed**。`git status` 干净（改动=上表文件），未 commit/push。

---

## 7. 诚实申报

1. **调研通道降级**：WebSearch 后端配额耗尽（2026-09-24 重置），改用 WebFetch 直读阿里云百炼官方 help 页（models/text-generation-model/billing/embedding/rate-limit），均为一手来源；价格以北京地域为准，**未做跨区域比价**。
2. **qwen3.7-plus 限时 8 折**：成本按**原价**保守记账（2/2 非思考、8/8 思考）；8 折窗口内实际成本更低（PRO 车道约再 -20%）。非思考输出价官方页未单列，按与输入同价假设——填 key 后以账单核对。
3. **思考 wire 参数存疑（重要）**：官方文档思考控制为 `enable_thinking`；但仓库现有 DashScope 车道（dashscope_standard_thinking/dashscope_reason）早已通过 `llm_service` 统一注入 `thinking:{"type":...}`（Zhipu/MIMO 形状）且为现网已发布配置。**本次未改 wire 行为**（避免对已在跑车道引入回归）。连通性验证时若 DashScope 拒收该参数，回退 = 将 `dashscope_reason/standard_thinking` 的 `thinking_mode` 置 None（混合模型非思考默认合法，纯配置改动）；是否新增 DASHSCOPE 专用 `enable_thinking` 注入分支，建议单独立卡。
4. **零真实 API 调用**（按任务约束）：模型可用性/延迟/质量均为官方页与档位推断，未实测；连通性验证清单见 §5。
5. **capsule 默认计划链仍为 GLM 硬编码**（`build_execution_plan` 的 glm_batch 分支）：与 MiniMax 接入时相同处理（只开 explicit-model 面）。因 `qwen3_7_flash_batch` 是 key-gated，若默认链硬切 Qwen，无 key 环境（dev/测试）会静默退化到 default(deepseek)。建议后续单独立卡把该分支改为经 `batch_worklane.resolve_batch_model_key` 路由真源解析。
6. **GLM_BATCH 优先序决策**：Qwen 置首、MiniMax 免费档（$0）次之——执行的是「主力切 Qwen」决策而非纯成本最优；如需免费优先，`LLM_TIER_GLM_BATCH` 一行 env 即可回调（§3）。
7. **契约测试锚点更新（4 个文件）**属本次切换的**有意契约变更**（FAST/MAX 首位换了），非迁就性放水；每处均留注释说明切换背景。
8. **`app/gen`（gitignored 构建产物）从主仓复制进 worktree** 用于跑测试（只读复制，不污染主仓），随 worktree 生命周期回收；未计入 changes.patch。
9. **生产启动闸扩展**（`DASHSCOPE_API_KEY` 计入合法 LLM key）是有意行为变更：纯 Qwen 部署不再被强制要求配 ZHIPU/DEEPSEEK key；对应测试已更新并新增正向用例。
10. MAX/TOP 旗舰条目未做 key-gate（与既有 dashscope 条目一致）：无 key 环境这些候选空 key 在链，由既有 demo-mode/降级语义兜底（现有 dashscope_chat 等同此行为，测试环境已验证无回归）。

---

## 8. 回执一行版

- **分层选型**：FAST=qwen3.7-flash ｜ STANDARD=qwen3.8-flash(轻思考) ｜ PLUS=qwen3.7-plus ｜ PRO=qwen3.7-plus(思考) ｜ MAX/TOP=qwen3.8-max ｜ BATCH=qwen3.7-flash(key-gated) ｜ EMBEDDING=text-embedding-v4(不变) ｜ GLM 全保留待用
- **预算影响**：贵层 -58%（MAX/TOP）、批处理 -90%、免费层饱和 -50%；PRO/STANDARD +20~25% 换代际升级；O-07 free 150k/$0.5 限额全部受控（MAX 饱和 $0.51 由硬闸兜底，较前 $1.20 改善）
- **env 键**：`DASHSCOPE_API_KEY`（唯一必填）；其余 8 个 DASHSCOPE_* 模型键均有代码默认值可选配
- **测试统计**：新增 25 例 + 契约锚点更新 4 文件，串行 10 批回归 ~460 例全绿 0 failed
- **申报**：见 §7 共 10 条（重点 #3 思考 wire 参数、#5 capsule 默认链、#8 折扣价保守记账）
