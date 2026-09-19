# V3-FIX-04 REPORT — glm 车道 thinking 控制 + max_tokens 留量（P1）

> 执行：V3 Fleet Worker（wt4，base 1083f4f5）｜日期：2026-09-19｜依据：B-05b `v3-output/B-05/SUPPLEMENT_KEY_ROTATED.md` + `REVIEW_RECEIPT.md`

## 0. 结论

**READY**。zhipu 请求构造已按候选 `base_url` 分流：coding 端点 + `clear_thinking=True` → 线上 payload 附 `thinking:{"type":"disabled"}`（B-05b 证实的唯一真关思考通道）；标准端点不发该参数（会 400 code 1210）。同时为思考仍会进行的 zhipu 车道加 max_tokens 留量保护。红测（`KeyError: 'thinking'`）→ 6/6 绿；llm 相关定向测试与基线零回归；**真实 API 验证 2 次调用确认端到端生效**（no_thinking 车道 `reasoning_tokens=0`，对照思考车道 108/134 tokens 思考）。

## 1. 改动文件

| 文件 | 改动 |
|---|---|
| `backend/app/core/llm_router.py` | 新增 3 个模块级纯函数（`is_zhipu_coding_endpoint` / `glm_thinking_disabled_on_wire` / `glm_effective_max_tokens`）+ 常量；`get_openai_client_kwargs` 接线：extra_body 按 base_url 附 `thinking`，`max_tokens` 过留量函数 |
| `backend/app/services/llm_service.py` | `_create_raw_completion` 与 `_create_raw_stream` 装配点（caller 显式传参合并后）应用 `glm_effective_max_tokens`；import 更新 |
| `backend/tests/core/test_llm_router_glm_thinking.py` | 新增单测（mock 传输，零真实请求），6 个用例 |

实现位置取舍：`get_openai_client_kwargs` 是 router→`OpenAICompatibleProvider`/LangChain 及 `llm_service` 全部请求 kwargs 的**单一构造点**（`_init_with_router` / `switch_model_for_task` / `switch_to_specific_model` / `_build_provider_for_selection` 均经它），fallback manager 复用同一 selection 回调，无需改动 Go 网关与 providers.py。

### 1.1 thinking 参数设计

- 保留 `extra_body["clear_thinking"]` 原样发送（客户端侧语义标记，被智谱静默忽略无 4xx；`llm_service.is_thinking_mode` 与 `custom_expert_service` 依赖它判断）。
- 仅当 `provider==ZHIPU and clear_thinking and base_url 含 /api/coding/` 时**追加** `thinking:{"type":"disabled"}`。
- 标准端点：不发 `thinking`（400 code 1210 "该模型始终思考"）；`clear_thinking=False` 的思考车道：不发（默认思考保持）。
- 按 base_url 字符串判断而非 settings 字段名，env 改写 `ZHIPU_BASE_URL` 指向 coding 端点时自动生效。

### 1.2 max_tokens 留量——方案与取舍

任务给了两个候选方案，选择**前者的变体（比例上浮）**，因它可被单测精确断言：

- **规则**：思考仍会进行的车道（标准端点，或 `clear_thinking=False`），`effective = ceil(requested × 0.15 / (1 − 0.88)) = ceil(1.25 × requested)`，即 1024→1280。数学含义：按实测最坏思考占比 88%，上浮后可见输出 ≥ 配置值的 15%（1280 × 12% = 154 ≥ 1024 × 15%）。思考已关闭（coding + clear_thinking=True）或非 zhipu → 原样返回；`None` 不注入。
- **为什么不选"上调默认 max_tokens"**：zhipu 全部 registry lane 的 `ModelConfig.max_tokens` 现为 `None`（不传 → 模型默认上限），上调默认值反而会给原本不设限的车道引入新上限；且caller 显式传入的小预算（实测空回复的来源，如 1024）在 `params.setdefault` 语义下不会被配置值覆盖，必须在实际请求装配处保护。
- **为什么不选 "min(配置值, 预算上限)" 单独使用**：glm-5.3-flash 输出上限未知（未核实），单侧压低会加剧空回复；留量方向必须向上。
- **成本备注**：上浮仅 +25%；思考车道 reasoning 与 content 同预算，账单影响与思考本身同量级（B-05b 已标注单价 TBD）。

## 2. 红绿证据

### 2.1 RED（实现前）

mock 传输单测断言 `body["thinking"] == {"type":"disabled"}`（走 `select_specific_model("glm_4_7_no_thinking")` → `get_openai_client_kwargs` → AsyncOpenAI/httpx.MockTransport 捕获线上 JSON）：

```
FAILED tests/core/test_llm_router_glm_thinking.py::test_coding_lane_clear_thinking_sends_thinking_disabled
FAILED tests/core/test_llm_router_glm_thinking.py::test_get_openai_client_kwargs_applies_max_tokens_headroom
FAILED tests/core/test_llm_router_glm_thinking.py::test_raw_completion_glm_max_tokens_headroom_applied
3 failed, 3 passed
核心断言：assert body["thinking"] == {"type": "disabled"} → E   KeyError: 'thinking'
```

（基线行为探针：`kwargs extra_body: {'clear_thinking': True}`，无 `thinking` 键——与机制事实③一致。另 3 个用例为回归护栏：标准端点不发参数、思考车道不发参数、helper 纯函数，实现前后均须绿。）

### 2.2 GREEN（实现后）

```
tests/core/test_llm_router_glm_thinking.py ......  [100%]  6 passed
```

### 2.3 定向回归（串行，`-p no:randomly`）

| 套件 | 结果 | 基线对照 |
|---|---|---|
| `tests/core/test_llm_router_glm_thinking.py` | 6 passed | —（新增） |
| `tests/unit/test_llm_same_tier_fallback.py`（断言非 coding URL extra_body 精确等于 `{"clear_thinking": True}`） | passed | 无回归 |
| `tests/core/test_llm_router_policy.py`、`tests/unit/test_llm_router_health_tracking.py` | passed | 无回归 |
| `tests/test_llm_service_streaming.py`、`tests/unit/test_llm_service_security.py`、`tests/core/test_minimax_batch_routing.py` | passed | 无回归 |
| `tests/unit/test_llm_router_free_tier.py`（4F）、`tests/unit/test_stage37_llm_safety_kill_switch.py`（2F）、`tests/unit/test_deep_analysis_tier_routing.py` 等 7 套件（6F） | 失败 | **基线 stash 对照完全相同**（缺 `app.gen` 生成物、deepseek/dashscope 模型键漂移；预存环境问题，与本改动无关） |

## 3. 真实验证（2 次调用，≤2 上限内）

方法：主仓 `backend/.env` 临时拷入 worktree（已删，未进 patch/日志），`/opt/homebrew/bin/python3.11` 小脚本走真实引擎路径 `select_specific_model → get_openai_client_kwargs → AsyncOpenAI(coding)`，prompt"用一句话说明什么是光合作用"：

| 车道 | 线上 extra_body | finish | reasoning_content | usage | 时延 |
|---|---|---|---|---|---|
| `glm_4_7_no_thinking`（coding, clear_thinking=True） | `{"clear_thinking": true, "thinking": {"type": "disabled"}}` | stop | **无**（reasoning_tokens=0） | 26 completion 全为可见内容 | 1.262s |
| `glm_4_7_thinking` 对照（coding, clear_thinking=False） | `{"clear_thinking": false}`（不发 thinking） | stop | **有**（449 字符，108/134 tokens=81%） | 与 B-05b 84-88% 量级一致 | 2.804s |

结论：接线在真实链路生效——唯一差异变量是 `thinking` 参数，no_thinking 车道思考被真关闭（0 reasoning tokens、时延减半），对照车道思考照常。

## 4. 范围外观察（不阻塞，供后续任务）

1. `core/llm_client.py`（httpx 直连路径，`LLM_PROVIDER=zhipu` 分支默认休眠）无 clear_thinking 概念、也不发 thinking；其调用方（summarization 等）走 coding 端点会白白思考。建议后续接入同一 helper。
2. 标准端点 no_thinking 车道（`glm_4_7_flash_no_thinking`/`glm_4_7_flash_thinking`，registry 指向 `ZHIPU_BASE_URL`）现状思考无法关闭（B-05b 机制事实①），留量保护已兜住空回复风险；若要省 reasoning tokens 需把这两条 lane 切到 coding 端点（env 层即可，未动）。
3. 全部 chat lane 模型已统一 `glm-5.3-flash`（.env），registry 中 `avg_latency_ms`/`cost_per_1k_tokens` 旧值失真（B-05b §6 已记），非本任务范围。
4. 预存测试债：`app.gen` 缺失（worktree 未跑 `make proto-gen`）与 deepseek/dashscope 漂移导致 12 个定向用例在基线即红，建议主会话另行派单。

## 5. 收工清理确认

- [x] worktree `backend/.env` 副本已删（真实验证后立即删除，未进 patch/日志）
- [x] `/tmp/v3fix04_probe.py` 探针已删
- [x] 无模拟器/Gradle/flutter/浏览器进程（LIGHT 任务）；未重启主仓引擎；未 commit/push
- [x] `v3-output/B-02/REVIEW_RECEIPT_2.md` 为他人遗留 untracked 文件，未触碰、未入 patch

## 6. 变更清单（patch 内）

- `backend/app/core/llm_router.py`
- `backend/app/services/llm_service.py`
- `backend/tests/core/test_llm_router_glm_thinking.py`
- `v3-output/V3-FIX-04/REPORT.md`（本文件）
