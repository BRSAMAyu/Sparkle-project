# RAG 引用链修复（mr4 断点）：use_document_context 检索不触发 + citation 缺 file_id

基线：`a60d466b`（wt9 worktree）。复现数据：user `b9a9e0a0-2956-47de-86dc-002ee8b835ad`，file_id `393a89d5-8356-4db0-a973-4a29a7019fc9`（chunk 含 "MRV-7749"/"磷光"/"荧光"/"零下"）。

## 一、断点定位

逐段排查结论（a→e）：

| 段 | 状态 | 证据 |
|---|---|---|
| a. 网关 WS → gRPC 透传 | **正常** | `chat_orchestrator_chatflow.go:655` `req.UseDocumentContext = &useDocumentContext`；extraContext 同步注入（:479） |
| b. 引擎 StreamChat → context_data | **正常** | `orchestrator.py:2112-2118` 读 `request.use_document_context`；`:2277` 写入 `user_context_payload["use_document_context"]`，时序先于 `_attach_retrieval_decision` |
| c. retrieval_intent 决策 | **断点 1** | 实测 `build_retrieval_decision("MRV-7749 是什么？请根据我上传的资料回答", context={"use_document_context": True})` → `should_retrieve=False, reason=no_document_retrieval_signal` |
| d. 检索执行 | 正常（决策断了到不了这里） | `_hydrate_document_context` → GraphRAG；Redis 密集检索 + BM25/RRF，user_id 后置过滤 `_redis_doc_matches_user` |
| e. 注入 + citations | **断点 2（轻微）** | `document_context` 注入 prompt 通道存在（`multi_agent_adapter.py:292-295` "## Retrieved Documents"；`prompts.py` MR-4 grounding 段）；但 Redis 检索结果缺 `file_id`，citation 因 `source_file_id=None` 被跳过 |

### 断点 1（主因）：`use_document_context=True` 不产生任何检索拉力

`retrieval_intent.py` 的 `classify()` 只处理了 `False`（强制 no_retrieval），`True` 直接落到启发式模式匹配。而验收消息：

- 不含 `什么是`（是"是什么"）、不含 `资料`（ambiguous 词表只有 `材料/课件/笔记`）；
- prototype 余弦分低于 0.24 阈值。

→ `no_document_retrieval_signal` → `_hydrate_document_context`（orchestrator.py:1862）与 `retrieval_node`（standard_workflow.py:1164）双双跳过 → prompt 无文档段 → 模型答"没看到资料"。用户显式开启的开关被启发式静默否决，语义错误。

### 断点 2（次因）：Redis 密集检索不投影 `file_id`，citation 链断在最后一米

实测探针（`redis_search_client.hybrid_search` 对真实索引）返回字段仅 `id/parent_id/content/parent_name/importance/source_type/user_id/vector_score`——索引 schema 未收录 `file_id/chunk_id/section_title` 等字段（JSON 索引 schema 缺口，属共享 Redis 基础设施，未动）。于是 `_build_filtered_chunk` 得到 `source_file_id=None`：

- `retrieval_node` 的 citation 构造要求 `item.chunk_id and item.source_file_id`（standard_workflow.py:1225）→ 不产出 Citation；
- orchestrator 水合的 `context_receipt.used[].source_file_id` 为 null，网关/端上拿不到引用来源。

## 二、修法

### 修复 1：`backend/app/orchestration/retrieval_intent.py`

`classify()` 中，当 `use_document_context is True` 且 base 结果为 `no_document_retrieval_signal` 时，升级为 `targeted_source_rag`（`citation_required=True`，reason=`session_use_document_context_true`）。守卫保持不变：

- `use_document_context=False` 仍强制 no_retrieval（既有语义）；
- 情绪/社交、简单任务轮次的 short-circuit reason 不同，不受影响（`test_use_document_context_true_keeps_emotional_guard` 锁定）；
- 仅在"启发式完全无信号"的 fallback 分支生效，不改变 knowledge/planning/deep 等既有路由。

### 修复 2：`backend/app/orchestration/graph_rag.py`

`_build_filtered_chunk` 增加 source_file_id 兜底：item 的 `source_type == "document_chunk"` 且 `file_id` 缺失时，取 `parent_id`（`rag_indexing_service.build_document_chunk_document` 契约：document_chunk 的 `parent_id` 即 file_id）。Knowledge-node 条目的 `parent_id` 是 node id，用 source_type 守卫隔离，不误伤。

## 三、红绿证据

`backend/tests/unit/test_rag_cite_chain.py`（新建，6 条）：

| 测试 | 修复前 | 修复后 |
|---|---|---|
| `test_use_document_context_true_forces_retrieval_for_unknown_keyword` | 红 | 绿 |
| `test_use_document_context_false_still_blocks_retrieval` | 绿 | 绿 |
| `test_use_document_context_true_keeps_emotional_guard` | 绿 | 绿 |
| `test_document_chunk_parent_id_fills_missing_source_file_id` | 红 | 绿 |
| `test_hydrate_document_context_injects_chunk_content`（mock GraphRAG → `_hydrate_document_context` 断言 document_context 含 "MRV-7749/磷光/零下" + receipt 含 chunk_id/source_file_id） | 红 | 绿 |
| `test_retrieval_node_emits_citations_with_chunk_content`（mock 检索 → retrieval_node 断言 CitationBlock.content 含 chunk 内容、file_id 正确） | 红 | 绿 |

回归：`test_signal_spine` + `spine/*` + `test_unified_intent_router_*` + `test_execution_intent_model` + `test_retrieval_fallback` + `test_multi_intent_service` + graphrag 系列共 **1017+ passed**，零回归。`test_retrieval_intent_classifier.py` 中 `compare paging and segmentation` 一例在**未修改的 HEAD 上同样失败**（P1-9 引入 deep_source_synthesis 后期望值过期），与本次改动无关。

ruff 全部通过；新增/改动代码块 black(120) 干净（两文件 black 基线本身不通过，属既有状态，未顺手重格式化以免污染 patch）。

## 四、实测（worktree 独立引擎，gRPC :50052，杀净）

以 `GRPC_PORT=50052` 起 worktree 引擎（避开主仓 :50051），gRPC 直连 `StreamChat`（`x-internal-api-key` + `user-id` 元数据，等价网关调用），带 `use_document_context=true` + `include_references=true`，消息即验收消息，fresh session：

- **回复命中全部三个关键词**「磷光」「荧光」「零下」（含"零下 20 摄氏度保存""蓝色荧光晶体""星轨状磷光"等 chunk 正文细节）；
- 响应 metadata `document_context_retrieval.context_receipt`：`used_count=1`，`chunk_id=sparkle:doc_chunk:393a89d5…:0`，`source_file_id=393a89d5-…`（修复 2 后非空），`relevance_score=1.0`，`decision_reason="参考了你上传的资料来回答"`（修复 1 的新 reason，证明决策链生效）；
- 修复 2 生效的一轮：`CitationBlock` 实际产出 1 条 citation，`file_id=393a89d5-…`，content 为 chunk 正文预览。

收工已确认 :50052 无监听、无残留进程；主仓 :50051 未受影响。未 commit。

## 五、剩余风险

1. **模型偶发拒用已注入材料**：个别轮次模型（qwen3.8-flash）即便 prompt 含文档段仍称"只看到文件名"。prompts.py 已有 MR-4 mitigation（material grounding 口径翻转），该问题为已知模型行为债务，非链路断裂——链路正确性以水合日志（`Hydrated document context … passed=1`）、receipt 与实测命中为准。
2. **水合超时回退**：`_hydrate_document_context` 的 7.5s wait_for 在 HyDE/embedding 慢时会超时失败，由 `retrieval_node` 二次检索兜底（citation 反而由这条路产出）；代价是该轮 `context_receipt` 元数据缺失。可考虑后续把 HyDE 探测移出水合关键路径。
3. **Redis 索引 schema 缺口**：`file_id/chunk_id/section_title/page_numbers` 等字段未被索引投影，`chunk_id` 退化为 redis key 格式（`sparkle:doc_chunk:<file_id>:<idx>`，仍稳定可溯）。彻底修复需改索引 schema 并重建共享 Redis 索引，超出本次范围。
4. **study_plan 会话默认 True**：网关 `defaultUseDocumentContextForMode("study_plan")` 默认 True，修复后该模式下原本无信号的消息也会触发文档检索（语义即"会话开启资料检索"），检索成本略升；若需省成本可在网关侧区分"会话默认"与"用户显式开启"。
5. 本 patch 生成时排除了 worktree 中他人未跟踪文件（minimax-async-lane.md），仅含本次四个文件。
