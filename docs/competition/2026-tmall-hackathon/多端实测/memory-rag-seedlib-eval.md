# 记忆 / RAG / 种子库三域真机实测（memory-rag-seedlib-eval）

- 日期：2026-09-19 01:41–02:30（本机真服务，未主动重启任何进程；测试窗口内引擎被其他会话多次重启，已逐轮记录所跑进程）
- 主仓库 HEAD：任务 brief 为 `10c741a7`；评测期间仓库被并行推进至 `6b0c02db`。实测前逐文件比对，记忆/RAG/种子库关键文件（memory_inferred_write_lane / context_pack / documents / seed_libraries / orchestrator / embedding_service）与主仓库 HEAD **字节级一致**，结论对主仓库有效。
- 运行栈：gateway :8080、引擎 :50051/:8000、PostgreSQL16+pgvector、Redis、MinIO（Docker）。测试中段引擎分别从 `Sparkle-sysrev/wt5`、主仓库根目录启动过（末段 b1–b4 探针为主仓库代码）。
- 凭据：游客 token（`guest_id=memrag01/02`）经 `POST /api/v1/auth/guest`；WS 经 `POST /api/v1/ws/ticket` → `ws://localhost:8080/ws/chat?ticket=…`；HTTP 经 `POST /api/v1/chat`。
- 评测发起 LLM 请求：15 次（另有每轮内部 reviewer/synthesis 调用未计），预算 25 内。

## 三域 × 结果矩阵

| 域 | 测试点 | 结果 | 关键证据 |
|---|---|---|---|
| A 记忆 | A1 跨会话记忆（会话1埋"小明/下周三数据结构期中"→新会话问） | ⛔ **FAIL** | 新会话答"我这边没有可靠线索"；记忆表 0 写入 |
| A 记忆 | A2 跨天记忆（DB 注入 1 天前记忆行后再问） | ⛔ **FAIL** | context pack 取到该行（telemetry `trimmed episodic usage=1181 budget=220`）但 3 次提问均答"没有你的考试日期" |
| A 记忆 | A3 长程压测（5 事实轮+第 6 轮全量提问） | ⛔ **阻断（召回 0/5）** | 捕获通道死路（P1-MR1）+ 注入清空（P1-MR2），机制性不可达 |
| B RAG | B1 上传→解析→切片→embedding→入库 全链 | ⛔ **第 1 步断** | MinIO 凭证漂移：presign 用 `minioadmin`，容器实际 `sparkle_minio` → PUT 403 InvalidAccessKeyId → confirm 409 |
| B RAG | B2 embedding 真实可用性 | ✅ **PASS** | 直 curl DashScope：`qwen3.7-text-embedding-flash` 返回 1024 维向量；引擎 `EmbeddingService.get_embedding` 离线直调同证 |
| B RAG | B1' 检索链（绕过上传、直写 DB+Redis 等价产物） | ⚠️ **半通** | `GraphRAG 检索 … vector=3 fused=3`、`Hydrated document context passed=3`、提示词 `document_chunks usage=354` —— 但模型拒认资料（P1-MR4） |
| C 种子库 | 列表/详情/订阅/订阅列表/退订 全流程 | ✅ **5/5 PASS** | 200/200/200/200/204，退订后 `subscriptions/me` 归零 |
| C 种子库 | 种子语义查询 | ✅ PASS | "解一元二次方程" 命中带完整解题步骤的示例 |
| C 种子库 | 内容质量抽样（5 条人工评估） | ⚠️ **2/3 库可用** | 数学示例库 3 条为真实分步解题/证明；另两库 10 条中 4 条为空壳 |

- **A 域通过率 0/3；记忆 5 事实召回率 0/5（机制性阻断）。**
- **B 域通过率 1/3（embedding 通；上传链断；检索链"管道通、终端拒用"）。**
- **C 域通过率：端点面 5/5 全通；内容面 60% 条目有效。**

## 记忆机制全景（代码梳理 + 实测印证）

- **存储**：`episodic_memories`（pgvector vector(1024)+HNSW、decay_policy、due_at、archived/retracted/revoked 生命周期）、`memory_preferences`、`memory_goals`；工作记忆在 Redis（`working_memory:{user}:{session}:{entry}`，**会话级**，TTL 4h、上限 40 条）。
- **写入通道（3 条）**：
  1. 直捕 lane（orchestrator 轮末）：**仅** `aurora_modeling_complete` / `task_completed` / `error` 三类事件写 episodic——普通聊天陈述**不写**。
  2. 规则推断 lane（stage16.rule_y，`MemoryInferredWriteLaneService`）：从用户消息挑 1 句做规则分类（commitment/person/relationship/self），由 `enqueue_from_session`（gRPC 路径）或 `enqueue_from_chat_turn`（HTTP 路径）在**助手消息持久化之后**触发；stage19 `working_memory_mode=live`（默认）下改入工作记忆，不直接落 LTM。
  3. 固化（consolidation）→ episodic LTM 的条件：`commitment` 且 due_at 可解析（自动）；显式确认短语（"帮我记住/记下来"等）10 分钟窗内；或 mention≥3 且跨≥60s。
  - **实测瓶颈**：工作记忆/固化挂在 `_persist_assistant_message` 之后，而该函数只在 tool-bridge / multi-agent / after-tool 分支被调用；**纯聊天的 standard 流式路径根本不持久化助手消息**（消息由网关 CQRS 直写 `chat_messages`），→ 推断 lane 与固化在主路径**从不执行**。
- **注入**：每轮 `_build_user_context` 合并 `episodic_memories/preferences/goals/…` → `ContextFocusAssembler`（按 intent 预算：episodic 3–5 条）→ `ContextPackBuilder.build`（telemetry 实证会取用并裁剪）→ 提示词。但 `_build_slim_user_context_for_standard_reply` **直接返回 `{}`**——短问句默认走 slim，全部用户上下文（含记忆）被清空。
- **衰减**：读取侧无时间过滤（`list_recent_episodic` 取最近 20 条），衰减靠 `decay_policy`（7d/30d/due_at+7d）+ evidence 健康作业；本次未观测到生效痕迹。

## B 域机制与实测细节

- **上传链**：`POST /documents/upload`（建 stored_files + 预签名 PUT）→ MinIO PUT → `POST /documents/{id}/confirm-upload`（`process_stored_file.delay` → Celery）→ document_chunks + Redis 索引。实测：**本机 Celery worker 未运行**（第二步即无人消费），且 MinIO 凭证漂移使 PUT 403（P1-MR3）——两处断点。
- **检索链（等价产物实测）**：用引擎自身 `EmbeddingService`+`index_document_chunks` 构造 2 份文档（ZB-2049 独有关键词 ×2 块 + 干扰文档"梯度下降"×1 块）入 `document_chunks`（含 1024 维向量）与 Redis。提问显式带 `use_document_context:true` 后：决策 `targeted_source_rag should_retrieve=True` → GraphRAG `vector=3 fused=3` → 水合 passed=3 → assemble_prompt `document_chunks usage=354` tokens 确认进入 system prompt。**但**模型仍答"没有拿到可引用的上传资料正文/不能复述内部检索材料"（b1–b4 四连），复述探针证实块可见但被 grounding 指令压制：提示词内 `user_material_grounding` 段状态为 no_hits/no_scoped_files，含指令"这轮没有拿到足够可用的材料证据"——与 GraphRAG 块**互相矛盾**，模型听从前者。
- **默认关闭**：`use_document_context` 仅 `study_plan` 模式默认 true，其余模式默认 false（`reason=session_use_document_context_false`），普通聊天 RAG 默认完全不参与。

## C 域：种子库

- 端点面（经网关 ：8080 代理）：`GET /seed-libraries`（3 个官方库）、`GET /:id`、`POST /:id/subscribe`、`GET /subscriptions/me`、`POST /query`（语义检索）、`DELETE /:id/unsubscribe` 全部 2xx，退订后归零。官方库 `subscriber_count=0`（含 featured 库），采纳度冷清。
- 对聊天的可见影响：上下文构建日志每轮出现 `Retrieved 3 few-shot examples for user`，且**订阅前就已检索**——订阅状态对注入无门控作用（影响=无差异，仅在"采纳建议"产品语义上）。
- 内容抽样（10 条全量，重点 5 条）：

| 库 | 条目 | 实质内容 | 评估 |
|---|---|---|---|
| 数学基础示例库 | 一元二次方程求解示例 | 248 字分步解题（识别类型→因式分解→验根） | ✅ 真实有用 |
| 数学基础示例库 | 三角形内角和证明示例 | 243 字证明过程 | ✅ 真实有用 |
| 数学基础示例库 | 函数图像分析示例 | 362 字分析 | ✅ 真实有用 |
| Python 编程练习题库 | 阶乘计算/列表操作练习 | 404–542 字 | ✅ 可用 |
| Python 编程练习题库 | Python 字典操作要点 / FAQ 模板×3 / 列表推导式闪卡 | **content_data 仅 4 字节（空）** | ⛔ 空壳，quality_score 却标 8.5–9.0 |

## P1 问题清单（复现步骤）

1. **MR-1 记忆捕获主路径死路**：WS standard 聊天纯文本轮（无工具分支）不调用 `_persist_assistant_message`（仅 tool-bridge/multi-agent/after-tool 分支调用），`enqueue_from_session`→工作记忆→固化整链**从不执行**；用户陈述的事实 0 落库。复现：游客 WS 发"我最喜欢的电影是《星际穿越》，帮我记住这个。"→ 成功回复后查 Redis `working_memory:*` 与 `episodic_memories`（本人账号）均为 0；换新会话问"我最喜欢的电影是什么？"→"我这边没有可靠线索"。位置：`backend/app/orchestration/execution_engine.py`（persist 调用点）、`backend/app/orchestration/persistence_layer.py:24-52`。
2. **MR-2 slim 路径清空用户上下文（记忆注入断点）**：`_build_slim_user_context_for_standard_reply` 返回 `{}`，短问句（默认命中）时 preferences/goals/episodic 全部不进提示词。复现：给测试账号插入 1 条 episodic 考试记忆（occurred_at=1 天前）→ WS 新会话问"根据你的记忆，我之前提到过什么考试？"→ 答"没有明确写出"。位置：`backend/app/agents/standard_workflow.py:2690`、`:1392`（触发条件）。
3. **MR-3 MinIO 凭证漂移，文档上传链第 1 步断**：引擎 presign 用 `MINIO_ACCESS_KEY=minioadmin`（`backend/.env:136-137`），运行容器 `sparkle_minio` 实际 root user=`sparkle_minio` → PUT 403 `InvalidAccessKeyId`；confirm 返回 409 `Failed to validate uploaded object`（网关侧 502）。叠加：本机无 Celery worker，`process_stored_file.delay` 无人消费。复现：POST /api/v1/documents/upload → 按预签名 PUT 任意文件 → 403。
4. **MR-4 检索证据自相矛盾，模型拒用已检索资料**：`use_document_context:true` 下 GraphRAG 水合成功（passed=3，354 tokens 进提示词），但 spine/L1 `user_material_grounding` 段输出"这轮没有拿到足够可用的材料证据"，模型遵循后者连续 4 轮拒答（含 ZB-2049 独有关键词问句、列目录问句、复述系统提示探针）。复现：按 B1' 构造文档块 → `ws_chat.py … '{"use_document_context": true}'` 问"ZB-2049 是什么？"。位置：`backend/app/orchestration/prompts.py:2370-2407`（grounding 段）、`backend/app/orchestration/orchestrator.py:1832`（水合）。
5. **MR-5 学习类消息高频触发 create_plan 工具链必挂**：DB 缺 `card_lifecycle_enum` 类型（迁移漂移）→ 卡片双写失败 → "Plan aborted at layer N: required step failure" → 前端可见"⚠️ 计划执行中断"污染正文；随后 `execution_review` 节点再抛 `RuntimeError: dictionary keys changed during iteration` 整轮 FAILED。且失败轮仍消耗 plan 配额（3/3 后 layer 0 即败）。复现：游客 WS 发"我下周三有数据结构期中考试，帮我记住"→ 观察回复后缀与日志（`/tmp/m2fix_grpc_5271.log:5314-5331`）。与上一轮 eval 的 F-3（`POST /plans` 500）同属计划链家族缺陷。
6. **MR-6 PII 脱敏使"记住我的名字"产品承诺不可达成**：管线把人名替换为 `[REDACTED_NAME]`（`backend/app/aurora/privacy.py:22,159`），模型如实回答"名字被脱敏，记了也只是占位符"。属隐私设计 vs 记忆能力的正面冲突，需产品决策（本地化存储原名的安全方案）。

## P2/P3

- **幽灵任务记忆污染**：游客演示任务状态使每轮写入 `completed 操作系统 - 死锁处理机制`（task_outcome, confidence .78） episodic 行，挤占 episodic 220-token 预算，真记忆被裁掉（telemetry `trimmed episodic usage=1181 budget=220`）。
- **回复重复 + 审查后缀**：所有近期回复带 `[内容审查: 未通过] 发现 1 个严重问题需要处理` 且正文两遍（delta 流与 full_text 帧重复下发），客户端体验差。
- **HTTP /chat 间歇 500**：`greenlet_spawn has not been called`（后台记忆 lane 疑与请求 AsyncSession 跨任务竞争）；非 UUID `conversation_id` 首调 500、二调 200（自动换 UUID）。
- **use_document_context 默认 false**：普通聊天 RAG 默认不可见（见 B 域）。
- **plan 配额被失败轮耗尽**：`quota exceeded: 3/3` 后所有计划类请求 layer 0 即败，用户无自愈途径。

## 附：受控/未测项

- A3 的 5 埋点+1 提问全量流程未逐条执行：MR-1/MR-2 决定了每条事实 0 落库、提问 0 注入，已用 3 个探针（电影/考试×2）等价证明召回 0/5，不再消耗预算。
- 上传→Celery→切片的真实产物未测（无 worker + 凭证漂移双重阻断）；检索链用引擎自身索引函数构造等价状态验证。
- 引擎 :8000 /metrics 为空响应，memory lane 指标计数未能取证，结论以 DB/Redis/日志为准。
- 评测产物（WS/HTTP 脚本、响应 JSON）在 `/tmp/memrag/`，不入库。
