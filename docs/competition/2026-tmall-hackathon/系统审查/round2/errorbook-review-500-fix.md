# 错题 review 端点基线双 500 修复报告

- 日期：2026-09-19 凌晨
- 基线：main HEAD `efb1567a`（fix(files): SSRF guard trusted-host exemption）
- 任务来源：`exam-p1-fixes.md` 遗留项 —— 网关错题本 gRPC 桥 401 修通后暴露的两路 500（基线即红）
- 结论：**两路 500 同根同源，均已修复并实测验证**。根因是 `ErrorBookService.submit_review`
  在「错题无关联知识节点」这条最常见路径上同时踩了两个雷：
  1. `_attach_no_linked_node_hint` 往 `latest_analysis` 写**只有 `linking_hint` 的局部 JSONB** 并落库；
  2. 这次落库的 `UPDATE ... updated_at=now()`（服务端生成列）使 ORM 实例的 `updated_at` 属性
     在 flush 后被 SQLAlchemy **过期**，而 `submit_review` 返回前不再 refresh，调用方的同步
     序列化（gRPC `_map_to_proto` / FastAPI 响应模型）在无 greenlet 上下文读它 → `MissingGreenlet`。

---

## 一、红证据（基线实测复现，非猜测）

对运行中的 main@efb1567a 引擎（进程 03:34 启动）直接打点：

### 路径 1：网关 gRPC 桥 500 MissingGreenlet

游客账号 → 创建错题（无关联节点）→ `SubmitReview`（带 `user-id` metadata 直连 :50051，
与网关桥同参数）：

```
GRPC ERROR code=StatusCode.INTERNAL
details: greenlet_spawn has not been called; can't call await_only() here.
         Was IO attempted in an unexpected place? (Background on this error at:
         https://sqlalche.me/e/20/xd2s)
```

引擎侧 `_map_to_proto(error)` 读 `error.updated_at` 时触发同步刷新 IO。
与 exam-p1-fixes.md 观测到的「网关桥 500 MissingGreenlet」一致（网关把 gRPC INTERNAL
映射为 HTTP 500，message 即该 greenlet 报错文本）。

### 路径 2：引擎直连 HTTP 500 response 校验失败

同一错题 `POST /api/v1/errors/{id}/review` 直连 :8000：

```
HTTP:500 {"error_code":"INTERNAL_ERROR","detail":"6 validation errors:
  {'type': 'missing', 'loc': ('response', 'latest_analysis', 'error_type'), 'msg': 'Field required',
   'input': {'linking_hint': {'code': 'missing_knowledge_links', ...}}}
  {'type': 'missing', 'loc': ('response', 'latest_analysis', 'error_type_label'), ...}
  {'type': 'get_attribute_error', 'loc': ('response', 'updated_at'),
   'msg': \"Error extracting attribute: MissingGreenlet: greenlet_spawn has not been called; ...\")
  ..."}
```

**注意两条路径在同一次请求里同时出现**：校验失败的 input 就是毒化 JSONB
（只有 `linking_hint`），而 `updated_at` 的 `get_attribute_error` 就是路径 1 的
MissingGreenlet——引擎日志（`/private/tmp/engine_api.log` 03:43:25 一条）可交叉印证。

### 附带数据损伤（毒化行）

基线代码 review 无关联节点的错题后，该行 `latest_analysis` 被提交为
`{"linking_hint": {...}}`，**此后所有读取（列表/详情/review）全部 500**，属持久化损坏。
实测复现：基线 review 后 `jsonb_object_keys(latest_analysis)` 仅剩 `linking_hint`。

### 追责

非本波 diff 引入。写入点 `_attach_no_linked_node_hint`（断点2 mastery sync 落地时引入）
与 `submit_review` 的双 commit 结构早于 164a1cd6；此前 200 的原因是该路径恰好没被
「无关联节点 + review」组合踩中（如 review 的错题已有完整 analysis 或已关联节点时，
`setdefault` 式合并不脏、或无 error_records UPDATE，属性不过期）。401 掩盖修通后
该组合成为新用户首刷 review 的必经路径，故「基线即红」。

---

## 二、修复方式（三层，proto 零改动）

### A. 写入点补齐 —— `backend/app/services/error_book_mastery_sync_service.py`

`_attach_no_linked_node_hint` 注入 `linking_hint` 前补齐 `ErrorAnalysisResult` 必填字段
（`error_type`/`error_type_label`/`root_cause`/`correct_approach`/`study_suggestion`，
用 `setdefault` 保留已有分析），保证落库 JSONB 永远 schema-complete，保留前端引导功能。

### B. 过期属性兜底 —— `backend/app/services/error_book_service.py`

`submit_review` 尾部（mastery sync commit 之后、return 之前）`await self.db.refresh(error)`：
服务端生成的 `updated_at` 在最后一次 flush 后会过期，refresh 保证返回的 ORM 实例在
gRPC/FastAPI 的同步序列化下不再触发隐式 IO（MissingGreenlet 根治）。附 warn 级日志兜底。

### C. 存量数据容错 —— `backend/app/schemas/error_book.py`

`ErrorAnalysisResult` 增加 `model_validator(mode="before")`：
- 非法/缺失 `error_type` → 归一为 `other`（非法枚举同理）；
- 缺失 `error_type_label` → 按枚举静态映射补中文标签；
- 缺失 `root_cause`/`correct_approach`/`study_suggestion` → 补「暂无…」默认文案；
- 非 dict（如历史 LLM 返回的 list）不在本层处理，由 D 兜住。
修复前已写进 DB 的毒化行因此可直接读（200），不再需要数据订正脚本。

### D. 写入面收敛 —— `backend/app/services/error_book_service.py`

`analyze_and_link` 落库前经 `_normalize_analysis_result`：LLM `json_object` 输出此前
未校验直接写 `latest_analysis`（残缺 dict / 非 dict 均可能），现统一走 `ErrorAnalysisResult`
容错校验后 `model_dump(mode="json")` 落库；非 dict 输入降级为 schema-complete 空 dict。

---

## 三、红绿证据

### 单测（`backend/tests/unit/test_errorbook_review_500_fix.py`，新增 7 例）

红（修复前，5 失败 = 两路 500 各自的机制，2 个语义对照本就绿）：

```
$ /opt/homebrew/bin/python3.11 -m pytest tests/unit/test_errorbook_review_500_fix.py -q
FAILED test_submit_review_returns_instance_without_expired_attributes      # MissingGreenlet 机制
FAILED test_no_linked_node_hint_persists_schema_complete_analysis          # 写入点毒化
FAILED test_error_analysis_result_tolerates_partial_legacy_rows[poisoned0] # 实测毒化行
FAILED test_error_analysis_result_tolerates_partial_legacy_rows[poisoned1] # 非法枚举行
FAILED test_error_analysis_result_tolerates_partial_legacy_rows[poisoned2] # 缺必填行
5 failed, 2 passed
```

绿（修复后同套件 + 邻接回归）：

```
$ /opt/homebrew/bin/python3.11 -m pytest tests/unit/test_errorbook_review_500_fix.py -q
7 passed

$ ... tests/unit/test_error_book_mastery_sync_service.py tests/unit/test_error_mastery_loop.py \
      tests/services/test_error_book_service.py tests/services/test_error_loop.py \
      tests/unit/test_error_replan_bridge.py -q
68 passed（4 failed 为基线既有红，见下「边界说明」）

$ ... tests/unit/test_evidence_resolve.py tests/unit/test_g14_recurring_error_patterns.py \
      tests/unit/test_progress_narrative_service.py tests/aurora/test_signal_pipeline.py -q
18 passed
```

### 实测（worktree 代码起独立端口实例 :50052/:8001，共享 sparkle_db，收工杀净）

| 场景 | 基线（:50051/:8000） | 修复后（:50052/:8001） |
| --- | --- | --- |
| gRPC `SubmitReview`，无关联节点错题 | 500 `greenlet_spawn has not been called` | **200**（mastery/proto 正常） |
| HTTP 直连 review 同错题 | 500 `6 validation errors` | **200**，`latest_analysis` schema-complete（`error_type: other` + 默认文案 + `linking_hint` 保留） |
| 已毒化行（SQL 置为仅 `linking_hint`）GET 详情 | 500 | **200**，`error_type: other`、默认文案、`linking_hint` 保留 |
| 毒化行 review 后落库值 | 持续毒化 | 回写 schema-complete JSONB（自愈） |

边界说明（非本单范围）：邻接套件中 `test_review_performance_impact_matches_spec`、
`test_update_mastery_from_error_*`×2、`test_error_replan_bridge_inserts_next_day_first_repair_task_*`
在 `git stash` 后的纯净 efb1567a 上同样红（已复核），属存量基线红，与本次改动无交集。

## 四、验证过程纪律

- 复现与验证用一次性游客账号（`guest_ebfix` 前缀）+ 自建错题/计划行，收工后随账号级联清除，
  并显式清理 `study_records`/`user_node_status`（NO ACTION 外键）等残留，复查 0 行；
- 修复后验证起独立端口实例（`GRPC_PORT=50052` / uvicorn :8001，进程级隔离），完成后进程已杀净、端口已释放；
- `latest_analysis` 修复语义对「无关联节点」路径保留 linking_hint 引导，前端无感。
