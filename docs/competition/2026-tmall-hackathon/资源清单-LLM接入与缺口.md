# 资源清单 · 真 LLM 接入现状与缺口（2026-09-18 夜）

## ✅ 已接入（DeepSeek，用户提供 key，实测全通）

| 用途 | 模型 | 状态 |
|---|---|---|
| 日常对话/生成（chat/generation/standard tier） | `deepseek-flash` | ✅ 真 API 实测：WS 全链路 ack→编排→流式 12 chunks→full_text 真实中文回复→usage/done；编排链真实工作（spine/plan 切换） |
| 推理/规划（reason/max tier） | `deepseek-v4-pro` | ✅ 模型存在（/models 列出）；编排 reason 路径已配，等端到端长流程实测 |

实测命令链：`POST /auth/guest` → `POST /ws/ticket` → `WS /ws/chat` → 发消息 → 流式回复（first_token 53s，见优化项）。

配置落点：`backend/.env`（不入库）+ `settings.py`/`.env.example` 默认值已钉（81af6fe7）。

## ⚠️ 性能/产品观察（非阻塞）

1. **first_token 53 秒**：编排多跳（规划+spine+生成）叠加 flash 为推理模型（reasoning_content 耗时）。演示前建议：预热会话、或编排层对简单问候短路（已见「通用知识问答优先直接回答」路由生效）、或 reason 链并行化。可派专项优化
2. `spine_degraded=true` 元数据：spine 服务降级运行（对应已挂账的 spine 死 schema 12 表），不阻断对话
3. DeepSeek flash 返回 `reasoning_content`+`content` 双通道：客户端只消费 content（正确）；若后续想展示「思考中」可消费 reasoning 增量

## ❌ 缺口清单（需要用户提供/决策）

| # | 项目 | 影响面 | 说明 |
|---|---|---|---|
| 1 | **多 provider 新凭据或砍掉** | fallback 链深层 | `llm_router` 池里 dashscope(qwen-plus)/xiaomi(mimo-v2-flash)/glm-4.7 系/**siliconflow** 模型名全部过时且 key 旧。**建议：演示期统一 DeepSeek 单 provider**（把 dashscope/xiaomi/glm 池条目移出 fallback tiers）——需要你确认；若保留多厂商冗余，请提供各家新 key+新模型名 |
| 2 | **Embedding API** | 知识库/RAG/相似度 | 引擎 embedding 调用现无有效凭据（DeepSeek 不提供 embedding 端点）。需要：阿里 text-embedding-v4 / 智谱 embedding-3 / siliconflow bge 等任一 key |
| 3 | **STT/TTS 语音** | 语音输入/朗读 | `stt_service` 初始化了 zhipu(主)+xunfei(备) 但凭据过时。需要新 key 或砍语音功能演示 |
| 4 | **OCR** | 拍照识题 | ocr_primary=zhipu，同上需新 key |
| 5 | **翻译链** | ingestion 翻译 | translation hunyuan(主)+siliconflow(备)，凭据过时 |
| 6 | **推送（JPush/Firebase）** | 移动推送 | jpush_config/firebase_config 存在但无演示凭据；「生成式推送」演示可降级为应用内通知 |
| 7 | **线上部署域名/HTTPS** | 多端公网演示 | 当前全 localhost。竞赛演示若需评委扫码/远程访问：需一台公网机（2C4G 起）+ 域名 + TLS；栈为 docker-compose 一键起 |
| 8 | **CI billing** | GitHub Actions | flutter-test/go-test/py-test 三 job 需 Actions 分钟数（公开仓库免费额度大概率够） |

## 立即可做的决策建议

- **A（推荐）**：演示收敛 DeepSeek 单 LLM + 关闭语音/OCR/翻译入口（UI 已有降级路径），缺口 1/3/4/5 全部消解
- **B**：你补 embedding 一家的 key（缺口 2），RAG 演示解锁
- **C**：提供公网机，我派员做 docker 化部署演练（缺口 7）
