# B-05 COMPLETION_RECEIPT

- **Task**: B-05 · 当前模型、Embedding、语音/OCR 与成本能力 Probe
- **Stream/Gate**: BASELINE / V3-0（Locks: ai-provider）
- **Status**: **PARTIAL**
- **Base SHA**: `46f46a1d`（worktree wt4，detached HEAD）
- **Final SHA**: 工作树停留在 `46f46a1d`，**无代码改动、未 commit**；产出全部为未跟踪文件：
  - `v3-output/B-05/capability_matrix.csv`（21 能力行 + 10 成本行）
  - `v3-output/B-05/capability_matrix.json`（同构 + latency_stats 聚合）
  - `v3-output/B-05/latency_samples.csv`（59 行逐次原始样本：probe/lane/status/TTFT/total/tokens/error）
  - `v3-output/B-05/raw/probe1..5_*.json`（探针原始落盘，凭据字段不出进程）
  - `v3-output/B-05/SAMPLES_SANITIZED.md`（脱敏请求/响应样本）
  - `v3-output/B-05/COMPLETION_RECEIPT.md`（本文件）

## Must-read 覆盖
- `v3/02_core_systems/AI_ROUTING_LATENCY.md`（Cognition Ladder / fast-first / Observability / Cost Principle）
- `v3/V3_DEFINITION_OF_DONE.md`（Gate V3-0「能力由 runtime probe 得到，不凭配置文件宣称可用」、Gate V3-8 SLO 候选校准）
- 路径种子：`backend/app/core`（llm_router.py 全读：tier 映射、cost_per_1k 配置口径、MiniMax 池约束）、`backend/app/services/stt/providers/bailian_provider.py`、`tts_service.py`、`ocr_service.py`、`backend/app/config/settings.py`；`.env`（主仓真实副本，只读）

## 实测结论（2026-09-19，真实凭据，无 fixture）
1. **qwen3.8-flash 三档全部真实可用且为同一模型**：fast=standard=reason（env 四个 DASHSCOPE_*_MODEL 同名），差异仅 `enable_thinking` 请求级开关 —— 双向生效、reasoning_content 流式返回、reasoning_tokens 入 usage。
   - fast：TTFT p50 474.7ms（p95 623.7），总时延 p50 1063.5ms，无 reasoning
   - standard_thinking：首 chunk p50 423.4ms，首正文 p50 1079.9ms，总 p50 1546.0ms
   - reason：总 p50 1718.8ms（p95 1976.8）
   - JSON 模式（json_object + thinking off）3/3 合法（含 stream）
   - thinking 模式 prompt_tokens 33→69（服务端附加提示，计费口径注意）
2. **MiniMax-M3（glm_batch 池首位）可用**：流式 200，`<think>` 内联前缀确认，TTFT p50 1280ms / 总 p50 2462ms；**12 并发一波 12/12 全 200、0 次 429**（服务端未见 8 硬限，客户端 lane=8 钳制仍保留）。
3. **ZHIPU_API_KEY 失效（重大发现）**：coding paas v4 与标准 paas v4 双端点、chat/OCR 全部 401 code 1000。受影响：glm_batch 池 4 个 zhipu 候选、`LLM_TIER_TOP=glm_5_1_top`、`zhipu_ocr` 主路、`STT_BACKUP_PROVIDER=zhipu`。**glm_batch 池实际只剩 minimax_m3_batch，TOP 层为死配置。**
4. **Embedding**：qwen3.7-text-embedding-flash dim=1024（=EMBEDDING_DIM），single p50 128ms、batch8 p50 203ms、dimensions 参数可用；text-embedding-v4 同 1024 维可用；siliconflow Qwen3-Embedding-4B 2560 维（跨 provider 混用需重嵌入）。
5. **语音**：qwen3-tts-instruct-flash 2/2 真实合成（RIFF wav 24kHz，p50 1613ms，instructions 生效，usage 按 characters）；qwen3-asr-flash-realtime WS manual-commit 协议 2/2 成功，**TTS→ASR round-trip 转写逐字正确**（completed 376–662ms）。
6. **OCR/多模态**：**qwen3.8-flash 原生视觉可用**（合成位图文本逐字正确）——OCR 可路由主模型；siliconflow DeepSeek-OCR 端点可用但合成图近形误读；zhipu glm-ocr 401。rerank（qwen3-rerank）与 Hunyuan 翻译不在本卡范围，标 unknown。
7. **成本矩阵（实测 vs 配置口径）**：qwen3.8-flash 公开价参考 ¥0.8/M 入、¥2.7/M 出（2026-08-27 调价，二手来源转述阿里云公告，未在控制台验证）；`llm_router.cost_per_1k_tokens` 币种未标注、不分输入/输出/reasoning，且 reason=5×standard 与实测同模型同价矛盾 —— **路由成本表需按真实计费维度重建**；MiniMax token plan 边际成本≈0（config=0.0 正确）。embedding/TTS/STT 无 config 成本项。

## PARTIAL 原因（未达部分）
- zhipu 全 lane 因凭据失效无法实测（glm_batch zhipu 候选 / TOP / OCR 主路 / STT backup）——需项目方轮换 `ZHIPU_API_KEY` 后按本卡 raw 脚本重测
- DeepSeek-OCR 仅合成图探针（近形误读），真实文档样本补测待后续卡
- rerank / 翻译 / json_schema strict / MiniMax 服务端并发真实上限：未在范围或未探测，保持 unknown

## 给 E 系列卡的 SLO 基线输入（真实实测，非配置宣称）
- fast 档 TTFT p95 624ms / 总 p95 1276ms → L1 fast semantic「first meaningful feedback p50≤2.5s / p95≤5s」**当前模型可满足且余量大**
- standard/reason 档首正文 p50 1080–1212ms / 总 p95 ≤1977ms → L2 阶段反馈 <500ms 不可由模型 TTFT 保证（thinking 首 chunk ~423ms 仅是事件流），需等待 UX 用阶段事件而非最终答案
- glm_batch 异步分析按 MiniMax-M3 总时延 p50 2.46s / 12 并发无拒绝对异步队列容量建模
- embedding single p95 <200ms：检索链路预算充足

## 验收对照（卡 Acceptance）
- [x] capability_matrix.json + latency raw samples（另附 csv 版）
- [x] LIVE 缺 key/模型失败不命中 fixture：zhipu 401 原样记录为 unavailable，未以任何 fixture 充数
- [x] 为 E 系列卡给出真实 SLO 基线（见上节）
- [x] 记录 provider/model_request/model_actual/error/fallback/cost（capability_matrix + samples 列）
- [x] 每实时路径 ≥10 样本：qwen3.8-flash 全档合计 17 次（fast 4 + fast+thinking 2 + standard 4 + reason 4 + json 3）；MiniMax 15 次（3 流式 + 12 并发）

## Reviewer 独立复核入口
- 重放脚本（/tmp 已清，需重建）：探针协议全部记录于 `SAMPLES_SANITIZED.md` §1–§8，可与 `raw/*.json` 逐字段对照
- zhipu 401 复现：`curl -s -o /dev/null -w "%{http_code}" https://open.bigmodel.cn/api/paas/v4/chat/completions -H "Authorization: Bearer $ZHIPU_API_KEY" -d '{"model":"glm-4.7","messages":[{"role":"user","content":"hi"}]}'`（凭据由 reviewer 自行注入主仓 .env）
- 本仓代码口径：`backend/app/core/llm_router.py`（tier/cost 表）、`ocr_service.py`（layout_parsing 主路）

## 纪律
- 全部修改仅在本 worktree（未 commit）；探针脚本/venv/原始音频在 /tmp/b05，收工自清；未动主仓；无模拟器/常驻进程；密钥零落盘零输出（探针 redact 校验：raw/*.json 经 key/token 模式扫描无命中）
