# B-05 脱敏探针样本（2026-09-19）

所有请求均从 `backend/.env` 真实凭据运行；本文件与 raw/ 下任何文件均不含 key/签名 URL。
原始逐次样本：`raw/probe1..5_*.json`（探针进程内注入凭据，落盘前无凭据字段）。

## 1. DashScope qwen3.8-flash —— tier fast（thinking off）

请求（compatible-mode `/chat/completions`，stream）：
```json
{"model": "qwen3.8-flash", "stream": true, "max_tokens": 400,
 "messages": [{"role": "user", "content": "用一句话解释什么是间隔重复记忆。"}],
 "enable_thinking": false, "stream_options": {"include_usage": true}}
```
响应尾块（脱敏）：
```json
{"usage": {"completion_tokens": 32, "prompt_tokens": 33,
           "prompt_tokens_details": {"cached_tokens": 0, "text_tokens": 33}, "total_tokens": 65}}
```
时延样本（4 次）：TTFT 404.6–623.7ms（p50 474.7），总时延 p50 1063.5ms，`reasoning_content` 无 → **thinking 关闭生效**。

## 2. tier standard_thinking（enable_thinking=true）

- 首 chunk p50 423.4ms，**首段 `reasoning_content` 先到，首个正文 content p50 1079.9ms**
- usage 出现 `completion_tokens_details.reasoning_tokens`（22–46/次）
- prompt_tokens 33 → 69：thinking 模式服务端附加提示词（计费口径需注意）
- tier reason 与 standard_thinking **实际同一模型同一行为**（p50 总时延 1718.8 vs 1546.0，同分布）

## 3. thinking 开关双向 + JSON 模式

- fast + `enable_thinking=true`：出现 reasoning stream（51–52 chars）→ **开关双向生效**
- `response_format={"type":"json_object"}` + thinking off：3/3 合法 JSON（含 stream 模式）：
  `{"text": "我爱在清晨跑步。", "lang": "zh"}`

## 4. MiniMax-M3（glm_batch 池）

流式请求同 OpenAI 兼容；`content` 以 **`<think>…` 内联前缀**开头（与 llm_router 注释一致）：
```
ttft p50 1280.5ms / total p50 2462.1ms
usage: {"prompt_tokens": 184, "completion_tokens": 73, "total_tokens": 257,
        "prompt_tokens_details": {"cached_tokens": 128}}
```
12 并发一波（钳制上限 8 的服务端行为观测）：**12/12 全 200，0 次 429**；单请求 p50 1238.5ms / max 2501.1ms，波总 2505.5ms。客户端 `llm_concurrency` minimax lane=8 钳制仍应保留（服务端余量未知）。

## 5. Zhipu（glm_batch 池候选 / TOP / OCR 主路 / STT backup）—— 全线不可用

```
POST https://open.bigmodel.cn/api/coding/paas/v4/chat/completions  → 401
POST https://open.bigmodel.cn/api/paas/v4/chat/completions         → 401
POST https://open.bigmodel.cn/api/paas/v4/layout_parsing           → 401
{"error": {"code": "1000", "message": "身份验证失败。"}}   # 7/7 + 2 端点复验 + OCR，全部一致
```
**ZHIPU_API_KEY 失效**：`glm_4_7_no_thinking / glm_4_7_thinking / glm_4_5_air_batch / glm_4_6_batch / glm_5_1_top(LLM_TIER_TOP) / zhipu_ocr(OCR 主路) / STT_BACKUP=zhipu` 全部不可用。glm_batch 池实际只剩 `minimax_m3_batch`。

## 6. Embedding

```
POST /compatible-mode/v1/embeddings {"model": "qwen3.7-text-embedding-flash", "input": ["间隔重复记忆法的核心原理是什么"]}
→ 200, dim=1024（=EMBEDDING_DIM），single p50 128ms；batch8: 8 vectors, p50 203–293ms, usage 按 prompt_tokens
text-embedding-v4: dim=1024, single p50 124ms
siliconflow Qwen/Qwen3-Embedding-4B: dim=2560（跨 provider 混用需重嵌入）
```

## 7. TTS → ASR 闭环（真实音频）

```
TTS: POST /api/v1/services/aigc/multimodal-generation/generation
     {"model":"qwen3-tts-instruct-flash","input":{"text":"你好，我是星火，你的学习伙伴。今天也要加油哦。","voice":"Cherry"}}
→ 200 p50 1613ms；音频经签名 URL 下发，RIFF wav 24kHz 268844B；usage={"characters": 42}
     instructions="用轻快活泼的语气朗读" → 生效

ASR: wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-asr-flash-realtime
     session.update(pcm/24k, turn_detection=null) → append(3200B/chunk) → commit → finish
→ transcript '你好，我是星火，你的学习伙伴，今天也要加油哦。'（与 TTS 原文逐字一致，2/2）
     ws open 45–53ms，transcript completed 376–662ms；低幅 440Hz 音调 sanity → '嗯。'
```

## 8. OCR / 多模态

| 路径 | 结果 |
|---|---|
| qwen3.8-flash + image_url（合成位图 "SAMPLE 128.99 CNY"） | **200，逐字正确** `SAMPLE 128.99 CNY` —— 主聊天模型原生视觉可用 |
| siliconflow deepseek-ai/DeepSeek-OCR | 200 可用，但两次合成图探针近形误读（123.99/128.99），usage 正常 |
| zhipu glm-ocr（OCR 主路） | 401（key 失效） |

## 9. 成本口径对比（详见 capability_matrix.csv cost 段）

- qwen3.8-flash 公开价参考（2026-08-27 调价，IT之家/知乎转述阿里云公告）：**¥0.8/M 输入、¥2.7/M 输出**
- `llm_router.py` 配置口径 `cost_per_1k_tokens`：fast=0.0001 / standard=0.0002 / chat=0.0004 / reason=0.001（币种未标注、不分输入输出）
- 实测典型单次调用按公开价折算 ≈ ¥0.0001–0.0002/次（fast）；**config 口径把 reason 定为 5×standard，但实测两者同模型同单价 —— 路由成本表与真实计费维度（输入/输出/reasoning 分列）不符，需要重建**
- MiniMax-M3：token plan 套餐内边际成本≈0（config=0.0 正确）；公开 list 价 ¥4.2/M 入、¥16.8/M 出仅作 fallback 参考
- embedding/TTS/STT 无 config 成本项（usage 分别按 prompt_tokens / characters / 音频时长计）
