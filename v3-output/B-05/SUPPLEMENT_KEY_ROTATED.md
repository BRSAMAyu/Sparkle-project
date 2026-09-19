# B-05b SUPPLEMENT — ZHIPU key 轮换后模型能力复测（2026-09-19）

> 结论先行：**新 ZHIPU_API_KEY 全链路可用**。glm-5.3-flash 双端点 16/16 次 200、并发 4 路 8/8 200；glm-ocr 主路 200 且识别质量高；glm-asr-2512 端点存活且 7.8s 中文语音转写逐字正确；引擎侧 9 个 zhipu registry lane 全部经真实调用验证健康（0 个 4xx/5xx）。**glm 车道可转正式备用**（判断依据与成本备注见 §6）。原始数据：`raw/probe6_glm53flash_matrix.json`、`raw/probe7_glmocr_asr.json`、`raw/probe8_engine_lanes.json`。本文件补齐 `capability_matrix.csv`（B-05，PARTIAL 收编）中所有 `unavailable` 的 zhipu 行；补充行见 `capability_matrix_zhipu.csv`。

- 复测时间：2026-09-19 11:45–12:05（本机）
- 凭据：主仓 `backend/.env` 轮换后的 `ZHIPU_API_KEY`（探测进程外直连，未触碰在跑引擎）
- 模型面：智谱当前仅剩 `glm-5.3-flash` 与 `glm-5.3`；主仓 .env 已把全部 chat lane 统一映射到 `glm-5.3-flash`（OCR 保留 `glm-ocr`，STT backup 为 `glm-asr-2512`）

---

## 1. 直连能力矩阵（glm-5.3-flash，双端点各 8 次流式 + 参数探针 + 并发 4 路）

### 1.1 标准端点 `/api/paas/v4/chat/completions`（8/8 成功）

| 指标 | p50 | p95 |
|---|---|---|
| TTFT（首个 delta，通常为 reasoning_content） | **0.644s** | 0.727s |
| 首个可见 content（思考结束后） | **1.456s** | 2.812s |
| 总时延 | **1.661s** | 2.997s |

- **reasoning 行为：8/8 每次都思考**。思考字符占比均值 **84.5%**（如 run1：reasoning 926 字符 vs content 40 字符）。usage 的 `completion_tokens_details.reasoning_tokens` 稳定返回（60/86、86/117、252/280 completion tokens）。
- 16 次 matrix 调用 finish_reason 全部 `stop`。
- `thinking:{"type":"disabled"}` → **HTTP 400，code 1210**：`"该模型始终思考，不支持关闭思考；请使用 low、high 或 max。"`（标准端点明确定义了错误码，可编程识别）。
- `clear_thinking:true`（我方引擎现状的 extra_body）→ 200，思考照常进行，**参数被静默忽略，无 4xx**。

### 1.2 coding 端点 `/api/coding/paas/v4/chat/completions`（8/8 成功）

| 指标 | p50 | p95 |
|---|---|---|
| TTFT（首个 delta） | **0.699s** | 4.277s |
| 首个可见 content | **4.339s** | 7.560s |
| 总时延 | **4.760s** | 7.828s |

- **reasoning 行为：8/8 每次都思考**，思考字符占比均值 **87.5%**，波动比标准端点大（单次 reasoning 75–1440 字符）。
- **`thinking:{"type":"disabled"}` 在 coding 端点生效**：200、无 reasoning_content、总时延 1.01s（对照同 prompt 默认思考 ~1.5–7.8s）。两次采样均复现。**这是目前唯一能关掉 glm-5.3-flash 思考的通道**；Leader 之前"disabled 被忽略"的观察仅在标准端点成立。
- `clear_thinking:true` → 200，思考照常（静默忽略，同标准端点）。
- 时延结论：coding 端点默认档明显比标准端点慢且尾部更重（p95 7.8s vs 3.0s），**低时延用途应走标准端点**。

### 1.3 并发 4 路（两端点各一波）

| 端点 | 状态 | 波总耗时 | 单请求 total | TTFT_any |
|---|---|---|---|---|
| 标准 | 4/4 200 | 1.434s | 1.06–1.43s | 0.447–0.502s |
| coding | 4/4 200 | 5.883s | 1.86–5.88s | 0.880–0.922s |

无 429、无降速错误；并发 4 路下标准端点几乎无损（TTFT 与串行基本一致），coding 端点排队感明显。

### 1.4 能力基线（标准端点）

- **中文指令遵循（2/2 通过）**：三重约束（≤20 字 + 必含"星火"+ 无标点）→ `瑞利散射使蓝光如星火布满天空`（14 字，全部满足）；"只输出数字" → `5040`。注意约束题的思考开销大（556 reasoning tokens 换 14 字答案）。
- **JSON 输出（2/2 有效）**：`response_format={"type":"json_object"}` 被**接受**（200，返回合法 JSON，前置换行需 strip）；纯 prompt 约束同样返回合法且语义正确的 `{"names":["小明","小红"],"cities":["上海","北京"]}`。
- **长上下文（8K 输入）**：约 1.8 万字符 filler + needle，实测 `prompt_tokens=8338`（≥8K），needle `萤火计划` 正确抽出，总时延 2.608s。
- **⚠️ 关键操作注意**：同构造 5570-token 输入、`max_tokens=1024` 时返回**空 content**——completion 1024 中 1022 全是 reasoning tokens，思考把 max_tokens 预算吃光。**我方给 glm 车道的 max_tokens 必须为思考预留额度**（短答案场景建议 ≥1024，复杂任务 ≥2048），否则用户收到空气回复且 finish=length。

## 2. 视觉探测（glm-5.3-flash + image_url）

- 输入：主仓 `.fieldtest-shots/round3/24_chat_reply1.png`（1080×2400，331KB PNG，base64 data URI）。
- **接受 image_url，200 OK**，不是纯文本模型。总时延 10.438s，图像折算 `prompt_tokens=3385`。
- 内容还原准确：识别出应用名 "Aurora"、Flutter 溢出调试横幅、`AI currently remembers / 0 current session memories` 等中英混排 UI 文本。
- 结论：glm-5.3-flash 原生视觉可用，紧急时 OCR 可兜底路由到主聊天模型（同 dashscope qwen3.8-flash 已验证的行为）。未见错误码场景（探测即成功）。

## 3. glm-ocr 主路实测（`/api/paas/v4/layout_parsing`）

- 同一张含真实文字的截图，`{"model":"glm-ocr","file":"data:image/png;base64,..."}` → **200，0.743s**。
- `md_results` 质量高：版面 bbox + 中英混排文本全部还原（`AI currently remembers`、`0 current session memories`、`Aurora`、`最近2张任务中有1张超时·轻度关注`、`Current self-model 5 correctable claims` 等），与我方 `ocr_service._extract_text` 的解析契约（md_results / layout_details）兼容。
- usage：prompt 580 / completion 92 tokens。**OCR 主路端到端可用**（B-05 时的 401 已消除）。

## 4. glm-asr-2512 探测（STT_BACKUP=zhipu 主路模型，`/api/paas/v4/audio/transcriptions`）

| 输入 | 结果 | 时延 |
|---|---|---|
| 1s 静音 wav（16kHz mono PCM16） | 200，`text:""`（空转写，语义正确） | 0.206s |
| 7.8s 中文语音 wav（macOS `say` Tingting 生成） | 200，`text:"你好，今天是9月19日，星火项目语音链路测试，请把这句话转成文字。"`（逐字正确） | **0.441s** |

- 端点存活判定：**200 = 模型活**（非 401/404）。usage 159 prompt / 25 completion tokens。
- 对照 B-05 的 `stt_backup_zhipu=unavailable`：**STT backup 主路恢复可用**。备注：早期一次 0.83s 截断语音转出乱语 `F dash`，说明模型对超短/截断音频会硬编，流式分段的段长下限（我方 4s）是合理配置。

## 5. 引擎侧 lane 验证（真实调用，我方客户端栈）

脚本：`scripts/devtools/probe_zhipu_lanes_b05b.py`（进 patch）。走真实引擎路径：`llm_router.select_specific_model` → `get_openai_client_kwargs`（含 `extra_body={"clear_thinking":...}`）→ `OpenAICompatibleProvider.chat`。worktree `backend/.env` 临时拷贝自主仓（**收工已删，未进 patch**）。

| registry key | model_name | base_url | 结果 | 时延 |
|---|---|---|---|---|
| glm_5_1_top | glm-5.3-flash | coding | OK | 3.649s |
| glm_4_7_no_thinking | glm-5.3-flash | coding | OK | 2.455s |
| glm_4_7_thinking | glm-5.3-flash | coding | OK | 2.090s |
| glm_4_5_air_batch | glm-5.3-flash | coding | OK | 1.994s |
| glm_4_6_batch | glm-5.3-flash | coding | OK | 2.576s |
| glm_4_7_flash_no_thinking | glm-5.3-flash | 标准 | OK | 1.569s |
| glm_4_7_flash_thinking | glm-5.3-flash | 标准 | OK | 1.693s |
| glm_5_max | glm-5.3-flash | coding | OK | 5.752s |
| glm_4_5_air_free | glm-5.3-flash | coding | OK | 6.179s |

**9/9 无 4xx/5xx**，全部返回正确应答（"在线"）。`clear_thinking` extra_body 被智谱静默忽略但不报错——我方客户端栈零改动即可工作。

## 6. 结论：glm 车道能否转正式备用

**判断：可以转正式备用（available），并建议做两个小配置改造后效果更佳。**

依据：
1. 双端点 16/16 + 并发 8/8 全 200，标准端点 TTFT_any p50 0.64s / total p50 1.66s，达到主力 lane 水准；
2. OCR 主路与 STT backup 主路双双从 unavailable 恢复为端到端可用，且有质量证据（OCR 中英混排还原、ASR 逐字转写）；
3. 引擎侧 9 个 registry lane 全部健康，客户端栈无需改动。

建议改造（非阻塞）：
- **`clear_thinking` 改为 `thinking:{"type":"disabled"}` 并把 *_no_thinking lane 切到 coding 端点**：coding 端点支持真关闭思考（1.01s vs 默认 4.7s p50），标准端点该参数会 400（code 1210）。现状静默忽略虽不报错，但"no_thinking" lane 实际都在思考，白白多花 reasoning tokens 与时延。
- **glm lane 的 max_tokens 预算为思考留量**（默认思考吃掉 84–88% 的 completion 预算；实测 1024 预算可被思考清空导致空回复）。
- 批量池（LLM_TIER_GLM_BATCH）时延按 coding 端点实测值校准（p50 ~4.8s / p95 ~7.8s，registry 里 avg_latency_ms=250–400 的旧值严重失真）。

成本备注（不编造，未实测到定价）：
- glm-5.3-flash 单价：**TBD**（公开页未在本次探测中核实，智谱后台计费口径未知）。usage 结构已确认：输入 tokens + 输出 tokens，且**输出中 reasoning_tokens 占比 84–88%**，定价若对 reasoning 与 content 同价，则思考会显著放大账单，标 TBD 待核。
- registry `cost_per_1k_tokens`（glm lane 0.0001–0.008 USD）与 `glm_5_1_top=0.008` 的配置值均基于旧模型命名，**与当前"全部 lane=glm-5.3-flash"的现实不符，成本估算暂不可信**，待定价核实后统一校准。
- glm-ocr：本次实测 580 prompt + 92 completion tokens/张；glm-asr-2512：159+25 tokens/7.8s 音频。单价均 TBD。
- coding 端点是否单独计费：未知（TBD），若与标准端点同价则无成本差异。

## 变更清单

- `v3-output/B-05/SUPPLEMENT_KEY_ROTATED.md` — 本报告
- `v3-output/B-05/capability_matrix_zhipu.csv` — 对 `capability_matrix.csv` 的 zhipu 补充行（同 schema；B-05 原文件保持不动，本文件行覆盖其 zhipu 行状态）
- `v3-output/B-05/raw/probe6_glm53flash_matrix.json` — 双端点 8×2 + 参数探针 + 并发 + 基线原始数据
- `v3-output/B-05/raw/probe7_glmocr_asr.json` — OCR + ASR 原始数据
- `v3-output/B-05/raw/probe8_engine_lanes.json` — 引擎 9 lane 原始数据
- `v3-output/B-05/changes.patch` — 上述文件与 devtools 脚本 diff
- `scripts/devtools/probe_zhipu_lanes_b05b.py` — 引擎侧 lane 探测脚本（一次性，归 devtools）

清理声明：worktree `backend/.env` 副本已删除；`/tmp/b05b-probe/`（wav、脚本、结果）已清；无进程、无模拟器残留。


---

## 复核附注（2026-09-19，独立 Reviewer verdict ACCEPT）

5 项自报结论全部独立复现（含 400 code 1210 逐字一致、coding 端点无 reasoning、时延量级吻合、OCR/ASR 重测一致、9/9 lane 零错）；安全审查 0 key 泄漏。2 处非阻塞瑕疵如实记录：§1.1「926 字符」示例与 raw 不符；§1.4「全部满足」与 raw 中 constraint2_pass=false 不一致（检查器误报，非模型缺陷）。
