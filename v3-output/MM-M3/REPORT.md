# REPORT — MM-M3：glm_batch 车道默认档切换 MiniMax M3（GLM 保留待用）

- worktree：`Sparkle-sysrev/wt79`（branch `wt79-v3`，HEAD `76677063ae27f65555dfffd713f5f57da4b19d66`，未 commit）
- 产物：`v3-output/MM-M3/changes.patch`（6 文件，+206/-47）+ 本报告
- 日期：2026-09-22

## 0. 前置说明（摸底结论）

本 worktree 在此前批次（`95941960` / `42956c11` / `f407823b`）已提交了 MiniMax 基础设施：
`ModelProvider.MINIMAX`、`minimax_m3_batch` 池条目（key 门控注册）、直连车道
`app/services/llm/minimax_provider.py`（`/text/chatcompletion_v2` + semaphore(8) 快速拒绝）、
concurrency minimax 池、glm_batch_service 的 minimax-优先链。**当时的语义是 minimax 优先、
GLM 降级兜底**。本批次按新用户决策完成语义切换：**minimax 注册即唯一默认，GLM batch 条目
默认不启用（保留待用）**。

provider 形态：全部走 OpenAI 兼容抽象（`OpenAICompatibleProvider` / openai SDK），
MiniMax 两种路径均可：`{base}/chat/completions`（llm_service 执行面，openai SDK 自动拼路径）
与 `{base}/text/chatcompletion_v2`（minimax_provider 直连车道）。鉴权均为
`Authorization: Bearer <key>`。模型名 `MiniMax-M3`。

## 1. GLM 使用面清单（切换前）

| 面 | 位置 | 切换前行为 |
|---|---|---|
| 路由真源 GLM_BATCH tier | `app/core/llm_router.py` `_tier_mapping` | `minimax_m3_batch`(有key时) + glm_4_7_no_thinking/glm_4_7_thinking/glm_4_5_air_batch/glm_4_6_batch |
| 池条目注册 | `app/core/llm_router.py` `_load_model_configs` | 4 个 GLM batch 条目恒注册（ZHIPU_API_KEY） |
| 批任务选模 | `app/services/glm_batch_service.py` `_select_batch_model_key` | minimax 优先 → 不健康/无 key 落 glm_* 链 |
| 拥塞/饱和判断 | 同上 `get_runtime_status`/`get_runtime_limit` | 恒读 zhipu_coding 池 |
| 胶囊显式模型链 | `app/services/capsule_generation_service.py` | minimax 显式 key → fallbacks=[glm_4_5_air_batch, glm_4_6_batch]；glm_batch 无显式 key 分支硬编码 glm_* |
| 长时程预测链 | `app/services/predictive_service.py` `_select_long_horizon_model_chain` | 4 组硬编码 glm_* 偏好链（与 registered 交集） |
| batch 车道执行 | `batch_worklane.resolve_selection` → router（force_tier=GLM_BATCH）、`celery_app.resolve_profile_batch_model_key` | 随 router tier 走，无需改 |
| 队列任务 | `generate_capsules_batch` / `analyze_cognitive_fragment_batch` / `classify_node_sector_batch` / `batch_error_analysis`（queue=glm_batch，max_retries=3 指数退避） | model_key 来自上述解析面，无需改 |

## 2. 切换面（本批次改动）

1. **`llm_router.py`**：4 个 GLM batch 条目标注【保留待用】（配置保留，不删）；GLM_BATCH
   默认档 = 有 key 时 `["minimax_m3_batch"]` 唯一候选，无 key 时保持 glm_* 原链（零 key
   环境零行为变化）。回切通道：`LLM_TIER_GLM_BATCH=glm_4_7_no_thinking,...` env 覆盖。
2. **`glm_batch_service.py`**：有 key 时 `_select_batch_model_key` 恒返回 `minimax_m3_batch`
   （**不健康也不偷切 GLM**——批任务失败 → celery max_retries=3 指数退避重试，不静默假成功）；
   dispatch 拥塞/饱和信号改读实际执行池（minimax 注册 → minimax 池，否则 zhipu_coding 池）。
3. **`capsule_generation_service.py`**：minimax 显式 key 的 fallbacks 置空（模型链耗尽 →
   job failed → celery 重试）；`build_execution_plan` glm_batch 无显式 key 分支同样默认
   minimax（有 key）；glm_* 链仅在无 key 环境生效并加【保留待用】注释。
4. **`predictive_service.py`**：minimax 注册且 registered 无 glm_*（未显式 env 加回）时，
   长时程链收敛为 `["minimax_m3_batch"]`，reason 文案如实标注；运维经
   `LLM_TIER_GLM_BATCH` 显式混入 glm_* 时尊重覆盖。
5. **`.env.example`**：MiniMax 段注释写明「配置 key 即切默认档」、留空行为、GLM 回切方式；
   GLM 段标注 batch 档默认不启用。

主流程（fast/standard/plus/pro/max/top/free/specialist）零改动——minimax 条目维持
「永不进主聊天能力层」约束（有单测锁定）。

## 3. 需要的 env 键清单（主会话在主仓 `backend/.env` 填）

主仓 .env 已存在（只读核验过）：

| 键 | 值（主仓现状） | 说明 |
|---|---|---|
| `MINIMAX_API_KEY` | 已填（真实 key） | 唯一必填键；留空 = MiniMax 不注册，glm_batch 走 GLM 原链 |
| `MINIMAX_BASE_URL` | `https://api.minimaxi.com/v1` | 代码默认值相同，可不填 |
| `MINIMAX_CHAT_MODEL` | `MiniMax-M3` | 代码默认值相同，可不填 |
| `MINIMAX_MAX_CONCURRENCY` | 8（默认） | token plan 并发上限，可不填 |

无需新增键；`.env.example` 已含全部 4 键 + 注释。回切 GLM 用现有
`LLM_TIER_GLM_BATCH` 键。

## 4. 真测结果（真实 MiniMax M3 调用 ×6，经生产代码路径）

| # | 路径 | 场景 | 延迟 | 结果 |
|---|---|---|---|---|
| 1 | `/text/chatcompletion_v2`（minimax_provider.analyze） | 中文问答 | 3342ms | 成功，content 干净中文回答（54 字） |
| 2 | 同上 | JSON 分析 + `response_format=json_object` | 2289ms | HTTP 200，content 非 bare JSON（**M3 思维链/markdown 变体**）→ 必须走生产 `<think>` 剥离解析器 |
| 2b | 同上（细化复测，`_parse_json_payload`） | 同上 | 1395ms | 成功：```` ```json ```` fenced → 生产解析器解析出 `{"sentiment":"positive","confidence":0.95}` |
| 3 | `/chat/completions`（openai SDK，llm_service 执行面同构） | 中文问答 | 1881ms | 成功：`<think>…</think>\n\n答案` 内联、finish=stop、usage 报数（prompt 11 / completion 217） |
| 4 | `/text/chatcompletion_v2` | **坏 key 错误路径** | 446ms | 正确失败：MiniMax 用 **HTTP 200 + body `base_resp.status_code=1004`** 报错 → 车道 shape 检查捕获 → `MinimaxLaneError`（不静默假成功） |
| 5 | `/text/chatcompletion_v2` | `max_tokens=16` 挤占 | 1028ms | 正确失败：empty content + `finish_reason=length` + `has_reasoning_content=True` → `MinimaxLaneError` 带明确诊断（M3 推理预算被思维链耗尽的已知形状） |

**结论**：
- 两种端点路径均连通可用；简单任务延迟 1.4–3.3s（均值 ~2s），对异步 batch 车道充裕。
- 响应形状：成功 = `choices[0].message.content`（可能带 `<think>` 内联或 markdown fenced
  JSON）；失败 = HTTP 200 + `base_resp.status_code!=0`。两条非正常形状都被车道转成
  `MinimaxLaneError` → batch lane 有界重试/批任务 celery 重试，**无静默假成功路径**。
- `llm_router.py` 旧注释称车道走 `{base}/chat/completions`、`minimax_provider.py` 称
  「非 /chat/completions」——实测**两条路径都 200 OK**，文档矛盾如实记录，行为不受影响。

## 5. 回归统计（pytest 串行，≤3 文件/批，SECRET_KEY 走 env 无 .env 落盘）

| 批 | 文件 | 结果 |
|---|---|---|
| 1 | `tests/core/test_minimax_batch_routing.py`（重写+扩展 20 用例）+ `test_llm_router_glm_thinking.py` + `test_llm_router_policy.py` | 33 passed |
| 2 | `tests/unit/test_batch_worklane.py` + `test_llm_same_tier_fallback.py` + `test_llm_tier_fallback_order.py` | 44 passed |
| 3 | `tests/services/test_minimax_provider.py` + `tests/unit/test_credential_routing.py` + `test_glm_batch_adaptive.py` | 28 passed |
| 4 | `tests/unit/test_predictive_service_extension.py` + `test_predictive_service_productization.py` + `tests/services/test_predictive_realtime_degrade.py` | 12 passed |
| 5 | `tests/unit/test_dailyflow_p2_capsule_today_window.py` + `test_o07_queue_backpressure.py` + `test_glm_batch_adaptive.py` | 23 passed |
| **合计** | | **140 passed, 0 failed** |

新增/更新用例（`tests/core/test_minimax_batch_routing.py`，20 个）：GLM_BATCH 唯一默认档、
GLM 条目保留注册但不在默认档、env 覆盖回切、无 key 原链不变、能力层永不混入 minimax、
glm_batch_service 三模式选模 + 不健康仍锁 minimax、dispatch 池切换（minimax/zhipu_coding）、
capsule 显式/缺省链、预测链收敛/保留，及原有 think 剥离/demo 模式/并发池回归。

## 6. 诚实申报

1. **主仓只读**：未改主仓任何文件；真测 key 经进程环境变量注入（`grep` 主仓 .env → export），
   未在 worktree 落 .env、未打印 key 值。测试用 SECRET_KEY 为 env 内联哑值。
2. **禁 commit**：改动以 `changes.patch` 交付（`git add -N && git diff`），HEAD 未动。
3. **真调范围**：仅 MiniMax（6 次小请求）；GLM/主流程模型（dashscope 等）零真调。
4. **既有语义变更点**：`test_minimax_batch_routing.py` 原 3 个用例锁定「minimax 不健康落
   GLM」的旧语义，已按新决策改写为「不健康仍锁 minimax」——这是任务要求的语义反转，
   非回归。
5. **遗留矛盾（未改代码）**：`llm_router.py` L787 注释（chat/completions 实测 200 OK）与
   `minimax_provider.py` 模块注释（「非 /chat/completions」）表述矛盾，实测两者皆可用；
   不在本批次范围内统一，留待主会话裁决以哪条路径为准。
6. **端到端限制**：未跑真实 celery worker 的 glm_batch 队列任务（需 broker + DB 栈）；
   执行面正确性由 `test_batch_worklane.py`（33 用例）+ 路由单测 + 真实 API 形状验证拼接覆盖。
7. **预存债务**：所触 5 文件在 HEAD 即不满足 black 格式、测试文件原有 2 处 ruff I001——
   均为预存状态，本批次仅保证不新增（新增代码 ruff 干净，B007 已修）。
8. **收工清理**：/tmp 探针脚本与结果 JSON 已删；无进程/模拟器残留；无构建产物。
