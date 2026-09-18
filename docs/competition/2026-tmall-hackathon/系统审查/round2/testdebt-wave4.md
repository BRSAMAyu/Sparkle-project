# 测试债第四波清理（testdebt-wave4）

基线：`9b77f7c8`（worktree wt7）。挂账 5 红（4 项，其中 error_mastery_loop 2 红）全部修复，定向邻域全绿。**生产代码仅改 1 处**（ingestion 上传大小检查），其余为测试重写/断言对齐。
环境说明：本 worktree 无 `backend/.env`（按纪律不碰），pytest 以 `SECRET_KEY` 环境变量注入；`backend/app/gen/`（gitignore 的 proto 产物）从主 worktree 等价复制（`git diff 9b77f7c8 HEAD -- proto/ buf* Makefile` 为空，生成产物与基线一致）。

## 逐例台账

### R1 ingestion 上传大小检查 413 → 500（生产真缺陷）

- 测试：`tests/unit/test_ingestion_api.py::test_clean_document_rejects_oversized_upload`
- 症状：期望 413，实得 500；stderr：`UploadFile.seek() takes 2 positional arguments but 3 were given`
- 根因：**生产缺陷（非断言过时）**。`app/api/v1/ingestion.py:98` 的 `await file.seek(0, 2)`（ whence=SEEK_END 定位文件尾量大小）在 Starlette 0.52.1 上非法——`UploadFile.seek(offset)` 签名不含 whence（实测 `inspect.getsource` 确认）。TypeError 被端点兜底 `except Exception` 吞掉转 500。后果：413 拒大文件路径是死代码，生产上任意超限上传一律 500 而非 413。
- 修法（`backend/app/api/v1/ingestion.py`，最小侵入）：改走底层文件对象 `file.file.seek(0, os.SEEK_END)` + `file.file.tell()` 量大小，再 `await file.seek(0)` 复位。底层 SpooledTemporaryFile 支持 whence，且在真正 `read()` 整个文件前完成拒绝（保留原意：先验大小后落盘）。
- 证据：同文件 2 passed（含 semaphore 用例无回归）。

### R2+R3 error mastery loop 2 红（API 已删，测试重写——无需恢复）

- 测试：`tests/unit/test_error_mastery_loop.py::test_update_mastery_from_error_clamps_at_ten_and_publishes_event`、`::test_update_mastery_from_error_returns_none_for_missing_node`
- 症状：`AttributeError: 'GalaxyService' object has no attribute 'update_mastery_from_error'`
- 根因：**测试调已删除 API**。`galaxy_service.py:161` 有 REMOVED 注释：mastery 写入统一移交 `ErrorBookMasterySyncService`，保留 stub 有双重扣减风险，且明确写明 "Tests: update the test to use the new service or remove the test"。旁证：`galaxy_event_consumer.py:78-86` docstring 把"不得调用 update_mastery_from_error"列为 MASTERY GUARD；`test_error_book_mastery_sync_service.py` §20/§21（single-deduction 契约测试）全绿。
- 等价性判定（任务书要求核实 `ensure_sprint_node`/`_persist_node_mastery` 能否覆盖）：这两者是**诊断测验**（exam_sprint_diagnostic_service，781c0280）的节点解析/写回路径，不走错题链。错题→掌握度链路的新 owner 是 `ErrorBookMasterySyncService`：`apply_error_diagnosis`（错因→`ERROR_TYPE_IMPACT` 权重扣分，单节点上限 -10，钳制 [0,100]）→ `GalaxyService.update_node_mastery`（revision 乐观锁 + outbox）→ 延迟 `node_mastery_updated` 事件 + StudyRecord；复习恢复走 `apply_review_feedback`（`error_book_service.py:1245` 实调）。**能力等价且强于旧 API**（旧 API 无审计 StudyRecord、无错误压力→AdaptiveReplanner 直评、无 linking_hint 用户引导），故按 REMOVED 注释指引重写测试，功能无需恢复。
- 修法（仅改 `tests/unit/test_error_mastery_loop.py`，生产零改动）：
  - `test_error_diagnosis_clamps_at_floor_and_defers_mastery_event`：保留原"钳制 + 事件"意图，对齐新契约——mastery=5 遭 knowledge_gap(-10) 钳制在**地板 0**（旧 API 地板是 10，新契约 `MIN_MASTERY_SCORE=0` 已由同套件 `test_safety_limits` 钉死）；事件断言从 `event_bus.publish("mastery_updated_from_error")` 改为结果内 `_pending_event`（topic=`node_mastery_updated`，commit 后由调用方投递）。真实 `db_session` 全链路（含 `GalaxyService.update_node_mastery` revision 落库）。
  - `test_error_diagnosis_without_linked_node_returns_empty_and_hint`：原"返回 None + 不 publish"→ 新契约"返回 `[]` + `latest_analysis.linking_hint`（missing_knowledge_links）+ 不产生任何 UserNodeStatus"。
- 遗留语义提示（非决策项，已定契约仅备案）：错题扣分地板从 10 收紧为 0、事件从即时 publish 改为延迟投递，均为 clean-slate 已落地的现行契约，本波仅对齐不做产品变更。
- 证据：`test_error_mastery_loop.py` 13 passed。

### R4 error book 复习影响权重 spec 红（断言过时）

- 测试：`tests/unit/test_error_book_mastery_sync_service.py::test_review_performance_impact_matches_spec`
- 症状：`REVIEW_PERFORMANCE_IMPACT` 实际多出 `{'forgotten': -2}` 一项
- 根因：**测试断言过时**。API 规范枚举 `ReviewPerformanceEnum`（`app/schemas/error_book.py:50-54`）只有 `remembered/fuzzy/forgotten`，没有 doc §5.4 时代的拼写 `forgot`；生产 `REVIEW_PERFORMANCE_IMPACT` 为兼容历史落库 payload 同时保留两拼写（`apply_review_feedback` 的压力判定集合 `{forgotten, forgot, fuzzy}` 亦双拼写）。去掉 `forgotten` 会让 API 主路径复习恢复完全失效——生产映射是对的，断言没跟上。
- 修法：断言更新为四键契约（`remembered:4, fuzzy:1, forgotten:-2, forgot:-2`），注释写明 enum 权威来源与 legacy alias 理由。生产零改动。
- 证据：同文件 39 passed。

### R5 retrieval intent diverse 消息分类红（断言过时，附产品语义备案）

- 测试：`tests/unit/test_retrieval_intent_classifier.py::test_retrieval_intent_classifier_diverse_messages[compare paging and segmentation-targeted_source_rag]`
- 症状：`"compare paging and segmentation"` 期望 `targeted_source_rag`，实得 `deep_source_synthesis`
- 根因：**测试断言过时**，与 6c2fea5d 无关（该提交只改 `use_document_context=True` 显式开关的兜底升级，本用例不传 context，实测排除嫌疑）。clean-slate 基线里 P1-9 `_DEEP_RESEARCH_PATTERNS` 含裸词 `\bcompare\b`，且在 `_classify_without_overrides` 中先于 `knowledge_signal` 判定（retrieval_intent.py:413 早于 :439），故"compare …"自基线起即路由 `deep_source_synthesis`（P1-9 已在 orchestrator.py:1915-1920 接线：depth=3 深读）。词表本身也自洽：`_KNOWLEDGE_PATTERNS` 与 knowledge 原型同样收录 "compare"，两个表争抢同一词、深读表优先——快照固有的表间次序，生产行为连贯非故障。
- 修法：断言对齐现行 P1-9 语义（`deep_source_synthesis`），行内注释说明缘由。生产零改动。
- **产品语义备案（未硬修，建议挂账评估）**：裸比较动词（compare/contrast/对比/比较）直接触发 `deep_source_synthesis`（budget.deep=3200、goal_bound、depth=3 多源深读）对"compare paging and segmentation"这类**双概念基础题**是否过重，属产品调优 knob：若产品倾向简单概念比较走 `targeted_source_rag`（strict guard、citation、depth=1），应收紧 `_DEEP_RESEARCH_PATTERNS` 为 multi-source 短语（如保留 "compare and contrast"/"across sources"，去掉裸词）。本波不动生产路由。
- 证据：同文件 27 passed。

## 邻域回归核验（最终树，定向）

- 4 个挂账文件合跑：**81 passed**（ingestion 2 + error_mastery_loop 13 + error_book_mastery_sync 39 + retrieval_intent 27）
- RAG 邻域：`test_rag_cite_chain.py` + `test_retrieval_fallback.py` **11 passed**（6c2fea5d 新增契约不受影响）
- 错题/星图邻域：`test_error_replan_bridge.py` + `test_error_replan_bridge_stage34.py` + `test_errorbook_review_500_fix.py` **passed**；`test_galaxy_document_review_api.py` + `test_retrieval_keyword_search.py` **2 passed**
- 环境性既存红（非本波范围、与本波改动无关，备案不动）：`test_galaxy_concurrency.py` 3 例需真实 PostgreSQL（直连 `app.db.session.engine`，本 worktree 无 `.env` 凭据 → `asyncpg InvalidPasswordError`）；主 worktree 带正确 env 时不受影响。

## 产物

- 本文档 + `testdebt-wave4.patch`（`git add -A && git diff --cached` 生成，未 commit）
- 变更面：`backend/app/api/v1/ingestion.py`（1 处生产修复）+ 3 个测试文件重写/对齐
