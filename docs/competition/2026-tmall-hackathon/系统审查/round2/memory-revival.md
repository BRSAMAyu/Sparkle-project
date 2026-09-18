# AI 记忆链复活（MR-1/2/3/4：跨会话记忆 + slim 记忆窗口 + MinIO 凭证 + grounding 自洽）

- 实现员：AI 记忆链复活专员（sysrev wt5）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`（基线 32d2ebe3，未 commit）
- 日期：2026-09-19
- 补丁：[memory-revival.patch](memory-revival.patch)（`git diff --cached` 产物；`backend/.env` 为 gitignored，只改运行时未入补丁）
- 评测输入：`docs/competition/2026-tmall-hackathon/多端实测/memory-rag-seedlib-eval.md` MR-1..MR-4 节
- 红绿协议：pytest 定向（基线红 9 failed → 修复后 14/14 green）；黑名单/护栏测试同批落地；3 个定向回归失败经 pristine 32d2ebe3 stash 对照实证为**基线已有问题**，与本改动无关（见 §6）
- 分域说明：只动 memory write lane / standard_workflow slim 上下文 / prompts grounding 段 / MinIO 配置与 Celery runbook；MR-5（card_lifecycle_enum 迁移漂移）、MR-6（PII 脱敏）不在本波

---

## 0. 总览

| 挂账项 | 实测定性 | 本波修复 |
|---|---|---|
| **MR-1** 记忆捕获主路径死路 | **部分修正 eval 归因**（§1.1）：persist→enqueue 接线在 happy path 是通的（RB-06 测试钉死、DB 有 148 条 assistant 行）；真正的机制性死点是**规则候选器把"显式记忆口令"句整句丢弃**——lane 空转，工作记忆/固化链无事可做；叠加 MR-5 计划链崩轮时整轮零捕获 | write lane 新增**显式口令 fallback 候选**（"帮我记住/记下来…"剥离口令取事实，confidence 0.92 越过 L1 直写门槛，硬禁止话题护栏）；live 配置下同轮即走 WM→固化→episodic LTM |
| **MR-2** slim 路径清空用户上下文 | 属实：`_build_slim_user_context_for_standard_reply` 返回 `{}`，短问句记忆/画像全不进提示词 | slim 保留**记忆最小说集**：top-3 episodic + 核心画像（preferences 截 8 键 / goals top-1 / llm_profile），`~500 token` 硬预算逐级收缩；slim 自带 `context_focus`（episodic cap=3，破默认 light 只渲染 1 条）；slim 提示词后缀显式允许"用户问记忆时依据【近期相关记忆】回答" |
| **MR-4** grounding 自相矛盾 | 属实：GraphRAG 水合（`document_context`/document_chunks 进提示词）与 `user_material_grounding` 预取是**两条独立通道**，后者 no_hits/no_scoped_files 时提示词宣称"没拿到材料"，模型听从前者拒用真实证据 | `_format_user_material_grounding_section` 与本轮实际检索产物对账：`document_context` 非空（且 total_passed>0 或无该字段）时，no_* 口径翻转为"已命中材料 + 列出 used_names + 优先引用"；真无材料时保留诚实口径 |
| **MR-3** MinIO 凭证漂移 + 无 Celery worker | 属实且比 eval 更深一层（§4）：引擎读 `MINIO_ACCESS_KEY/SECRET_KEY`（.env **两行都缺**→空凭证）；`.env` 只有 compose 层 `MINIO_ROOT_USER/PASSWORD=minioadmin`；而运行容器实际 root=`sparkle_minio`。minioadmin 403 与对齐后 200 均已实测复现/修复 | `.env` 对齐运行容器 + 补 `MINIO_ACCESS_KEY/SECRET_KEY` 两行（运行时改动，未入补丁）；`.env.local.example` 登记四行防再漂移；Celery worker 新增 `scripts/devtools/start_celery_worker_dev.sh`（nohup 方式，已启动 pid 见 §4.3），runbook 见 §5 |

红绿结果：**新增 14 项单测（capture 5 + slim/grounding 9），red 实证 9 failed → green 14/14**。定向回归 `test_two_consecutive_sessions_prompt_includes_inferred_memory` 在基线上是红的、本改动后转绿（其夹具句子正含"帮我记住"）。端到端验收（≤5 次聊天 LLM）脚本已备好：[scripts/devtools/acceptance_memory_revival.py](../../../scripts/devtools/acceptance_memory_revival.py)，**待协调者 apply patch + 重启引擎后执行**（§7）。

---

## 1. MR-1 记忆捕获主路径

### 1.1 溯源：比 eval 报告多走了一层

eval 的归因是"标准流式路径不调用 `_persist_assistant_message`"。在基线 32d2ebe3 上逐点核实：

- `orchestrator.process_stream` Step 14（`orchestrator.py:3532`）对**每个成功完成的图轮**调用 `_build_final_response`，其中 `response_builder.py:1291` 无条件调用 `_persist_assistant_message`；
- `persistence_layer.py:48` flush 后 `MemoryInferredWriteLaneService.enqueue_from_session`（后台 task，不阻塞流式）；
- wiring 已有 RB-06 测试钉死（`tests/core/test_rb06_followup_no_midstream_commit.py:90`）；
- 实证：`chat_messages` 中 148 条 assistant 行带 `model_name=qwen3.8-flash`（引擎写），eval 窗口的 working_memory Redis 键也存在（B1' 探针轮的候选写入成功）。

**真正的死点在 lane 的候选提取**（`memory_inferred_write_lane.py::extract_candidate`）：

- A1 电影探针句「我最喜欢的电影是《星际穿越》，帮我记住这个。」——`_pick_candidate_sentence` 产句后 `_classify_subject_type` 全链不命中（无时间锚/动作词"记住"不在动作 token 表/无社交词），`_looks_like_safe_context=False` → 返回 None → lane 空转：工作记忆 0 条、固化 0 对象、episodic 0 行。**"帮我记住 X"这一产品主承诺在主聊天路径整链失活**；
- A1 考试探针句「我下周三有数据结构期中考试，帮我记住」本可产候选（self+temporal），但该句同时高优触发 create_plan 工具链 → MR-5 卡片双写崩轮，`_execute_graph` 抛异常直接跳过 Step 14 → 0 捕获（该轮修复依赖 MR-5 域 + d859c194 已修 execution_review 崩溃，本波不改）。

### 1.2 修复：显式口令 fallback 候选（`memory_inferred_write_lane.py`）

- `EXPLICIT_MEMORY_COMMAND_PHRASES`（帮我记住/记住这个/记下来/把这个记住/就记这个/记一下这个）与 `EXPLICIT_COMMAND_HARD_BANNED_TOKENS`（人格判定/负面自我标签——口令也不得越过的硬护栏）；
- `_extract_explicit_command_fact`：剥离口令短语 → 按分隔符切分取最长事实段（≥6 字符）；
- `_build_explicit_command_candidate`：subject=self、confidence=0.92（> `MEMORY_INFERRED_MIN_CONFIDENCE=0.9`，保证 legacy 直写路径与 WM 固化路径都放行）、decay=30d、`schema_version=stage16.explicit_command.v1`；
- 挂点在 `extract_candidate` 的 `_pick_candidate_sentence` 为 None 分支——正常规则候选优先，口令 fallback 只兜底，精度夹具（`memory_inferred_cold_dataset.json`，negative 样本零口令词）不受影响。

live 配置（stage19 working_memory=live）下的同轮闭环：候选 → WM `upsert_entry` → 同句命中 `is_explicit_confirmation` → `maybe_consolidate_recent_entries`（10 分钟窗）→ `write_candidate_to_l1(force_write=True)` → **episodic LTM 当轮落行**。kill-switch off 时走 legacy 直写路径，同样落行（单测覆盖）。

### 1.3 红绿

| 测试（tests/unit/test_memory_revival_capture.py） | red | green |
|---|---|---|
| `test_explicit_memory_command_yields_candidate` | extract_candidate → None（MR-1 死点实证） | ✅ |
| `test_explicit_memory_command_writes_episodic_ltm_row`（enqueue_from_session 语义：user_message=None 回读库） | 0 行 | ✅ 1 行，summary 含"星际穿越" |
| `test_explicit_memory_command_not_duplicated` | —（依赖 fallback） | ✅ 重复口令去重 |
| `test_explicit_memory_command_still_respects_user_disabled` | —（护栏） | ✅ 用户关闭记忆不落库 |
| `test_explicit_command_fallback_respects_hard_banned_topics` | 方法不存在 | ✅ "我就是很笨"类口令句拒绝捕获 |

---

## 2. MR-2 slim 路径记忆窗口

### 2.1 溯源

`standard_workflow.py` 原实现一行 `return {}`。短问句（"根据你的记忆，我之前提到过什么考试？"）默认命中 `_should_use_slim_standard_context`（无工具意图、无文档检索、无专家）→ `prompt_user_context={}` → episodic/preferences/goals 全部不进 `build_system_prompt`。同时 `knowledge_context`/`document_context` 在 slim 分支也被清空（这两处是防泄漏的合理设计，保留）。

### 2.2 修复（`standard_workflow.py`）

- `_build_slim_user_context_for_standard_reply` 重写：episodic **top-3**（保留上游已排序的 `_attach_stage34_memory_context` 产物）+ goals top-1 + preferences 截 8 键 + llm_profile + preference_version + current_query；任务/统计/计划噪音（next_actions/focus_stats/active_plans/recent_tool_usage）照旧不进；
- `_truncate_slim_user_context_to_budget`：`estimate_tokens` 超 500 逐级收缩（丢 preferences → 记忆窗口收到 1 条）；
- **渲染对齐**：默认 light 档 episodic 只渲染 1 条（`section_caps.get("episodic") or (1 if light else 5)`）——slim 载荷自带最小 `context_focus{focus_mode:general_focus, section_caps:{episodic:3, goals:1}}`（`build_system_prompt` 会从 user_context 回读 focus），保证 top-3 真的可见；
- slim 提示词后缀新增一句：记忆问句（考试/偏好/约定等）必须优先依据【近期相关记忆】回答，记忆未覆盖才如实说没有——防止"别引入画像"的通用约束压制记忆召回。

### 2.3 红绿（tests/unit/test_memory_revival_slim_and_grounding.py）

red 3 failed（is_not_empty / keeps_top3 / prompt_renders_memory）→ green 6/6：非空、top-3 且含"数据结构期中"、噪音仍被裁剪、token 预算（实测 <600）、`build_system_prompt` light 档渲染出记忆内容、honest 分支不受影响。

---

## 3. MR-4 grounding 段与实际检索对账

### 3.1 溯源

两条独立通道：① `experience_actuator._ground_with_user_materials`（需 grounding_priority==user_materials，产出 `user_material_grounding{status,results}`）；② orchestrator `_hydrate_document_context` GraphRAG（`document_context` + `document_context_retrieval{total_passed, context_receipt.used_names}`）。eval 的 B1' 场景里 ②水合了 3 块（document_chunks usage=354）而 ①报 no_scoped_files/no_hits → `_format_user_material_grounding_section` 渲染"这轮没有拿到足够可用的材料证据"，模型服从后者连续 4 轮拒答。

### 3.2 修复（`prompts.py::_format_user_material_grounding_section`）

对账规则：`document_context` 非空 且（total_passed>0 或检索元数据缺失）→ no_hits/no_scoped_files/retrieval_failed/file_resolution_failed 的口径翻转为"本轮检索已命中用户材料（见下方文档片段）：{used_names top3}。回答时优先引用这些材料片段校准概念与事实，材料未覆盖的部分再补通用知识"；无水合产物时保留原"没拿到材料"诚实口径；grounded 分支原样不动。

### 3.3 红绿

red 2 failed（contradiction/build_system_prompt 端到端）→ green 3/3：有水合证据时段落引用 ZB-2049 且不再出现"没有拿到"；真无材料时保留诚实口径；grounded 分支快照回归。

---

## 4. MR-3 MinIO 凭证与 Celery worker

### 4.1 凭证漂移的完整链条（比 eval 多一层）

| 层 | 键 | 实际值 | 用途 |
|---|---|---|---|
| 运行容器 `sparkle_minio` | MINIO_ROOT_USER/PASSWORD | `sparkle_minio` / `sparkle_dev_minio_2026` | 容器创建时固化 |
| `backend/.env`（修复前） | MINIO_ROOT_USER/PASSWORD | `minioadmin/minioadmin` | docker-compose 建容器变量（引擎**不读**） |
| `backend/.env`（修复前） | MINIO_ACCESS_KEY/SECRET_KEY | **两行缺失** → settings 默认 `""` | **引擎 presign 实际读取**（`document_upload_storage.py:41`） |

即：不只是 minioadmin vs sparkle_minio 漂移，引擎侧根本拿不到任何键——presign 出的 URL 带空凭证/陈旧凭证，PUT 必 403（`InvalidAccessKeyId`），confirm 409。本机复现/修复双向验证：

```
minioadmin/minioadmin  → presigned PUT → 403（预期漂移失败）
sparkle_minio/sparkle_dev_minio_2026 → presigned PUT → 200，head_object 18 bytes ✅
```

### 4.2 配置处置

- 主仓 `backend/.env`（运行时文件，gitignored，不入补丁）：`MINIO_ROOT_USER/PASSWORD` 对齐运行容器，**新增** `MINIO_ACCESS_KEY/MINIO_SECRET_KEY=sparkle_minio/sparkle_dev_minio_2026`；附带效果：`production_readiness_check.sh` 的"minioadmin 默认凭证"检查由 fail 转 pass；
- 补丁内：`backend/.env.local.example` 登记四行并注明"ROOT_* 供 compose 建容器、ACCESS_*/SECRET_* 供引擎 presign，两者必须与运行容器一致"；
- 代码默认值检查：`settings.MINIO_ACCESS_KEY: str = ""` 无 minioadmin 硬编码（干净）；风险在静默空串——由 runbook 验证步骤兜底；
- 注意：在跑引擎（重启前）仍持旧环境，**重启后才吃到新 .env**（§7 交接）。

### 4.3 Celery worker

- `make celery-up` 已存在（docker 方式，依赖 sparkle_backend 镜像，容器网络 sparkle-project_default）；
- 新增 nohup 方式 `scripts/devtools/start_celery_worker_dev.sh`（start/stop/status，读 backend/.env，队列 high_priority,default,low_priority，PID/日志落 /tmp）——**已启动**：pid 34450，`celery@Mac-mini-2.local ready`，`process_stored_file` 已注册；
- 验证：上传链第 2 步不再 409-无消费者（验收脚本 mr3.confirm-queued / mr3.processed 步骤把关）。

---

## 5. Runbook（dev 环境上传链/记忆链每日自检）

```bash
# 1) 基础设施（PostgreSQL16/Redis/MinIO）
make dev-up
# 2) Celery worker（二选一）
bash scripts/devtools/start_celery_worker_dev.sh     # 本机 nohup；status/stop 同脚本
make celery-up                                       # docker 方式（需 sparkle_backend 镜像）
# 3) MinIO 凭证对齐自检（凭证来自 backend/.env，须与容器 root 一致）
docker exec sparkle_minio env | grep MINIO_ROOT_USER   # 应输出 backend/.env 里 MINIO_ACCESS_KEY 同值
# 4) 引擎（改代码/.env 后重启才生效）
pkill -f grpc_server.py && make grpc-server          # :50051
# 5) 记忆链/上传链端到端验收
/opt/homebrew/bin/python3.11 scripts/devtools/acceptance_memory_revival.py
```

---

## 6. 定向回归与基线对照

- 定向绿：`test_memory_revival_*`（14）+ `test_memory_inferred_write_lane.py`（除下述 1 条基线红）+ `test_rb06_followup_no_midstream_commit.py` + `test_standard_workflow_generation_routing.py` + `test_orchestrator_real_engine.py`（42）+ stage5/stage39/signal/session 套件（983 passed）；
- **pristine 32d2ebe3 stash 对照**证明以下失败为基线已有、与本改动无关：
  - `test_memory_inferred_write_lane.py::test_memory_inferred_revoke_hides_from_prompt_read_path`（非口令句候选未进提示词——正是本波能力缺口的一部分，但该测试句不含显式口令，属规则候选器召回面问题，留台账）
  - `test_context_focusing.py::test_context_pack_semantic_gating_filters_irrelevant_memory`
  - `test_stage5_intervention_language_contract.py` 2 条
- **基线红转绿**：`test_two_consecutive_sessions_prompt_includes_inferred_memory`（夹具句含"帮我记住"，被本波 fallback 捕获）。

---

## 7. 交接：端到端验收执行步骤（协调者）

1. 主仓 apply 补丁：`git apply docs/competition/2026-tmall-hackathon/系统审查/round2/memory-revival.patch`（主仓 backend/.env 已由本员对齐 MinIO，无需再动）；
2. 重启引擎（吃 .env 新 MinIO 键 + 补丁代码）：`pkill -f grpc_server.py` 后按主仓方式重启 ：50051（:8080 网关不动）；
3. 确认 Celery worker 存活：`bash scripts/devtools/start_celery_worker_dev.sh status`（已启动 pid 34450；不在则 start）；
4. 跑验收（预算：**5 次聊天 LLM** + 1 次 embedding）：`/opt/homebrew/bin/python3.11 scripts/devtools/acceptance_memory_revival.py`；
5. 通过标准：脚本退出码 0，8 步全 PASS——
   - a1.seeded-exam / a1.seeded-movie（会话1埋点）
   - **mr1.episodic-written（聊天一轮后记忆表有写入，DB 断言零 LLM）**
   - **a2.cross-session-recall（新会话2问考试 → 含"数据结构"）**
   - **a2.slim-short-recall（新会话3短问句"我最喜欢的电影" → 含"星际穿越"，slim 路径）**
   - mr3.presigned-put / mr3.confirm-queued / mr3.processed（上传链，MR-3）
   - **mr4.rag-cited（use_document_context:true 问 MRV-7749 → 引用性状/保存要求，无拒认话术，MR-4）**

已知残留风险（如实记录）：① 考试埋点句高优触发 create_plan（MR-5 域），若计划链仍中断该轮则 a1.seeded-exam 失败——但电影埋点（纯显式口令）不受影响，mr1/a2 断言仍应通过；② 若网关 CQRS 用户消息落库晚于 lane 后台读取，`_load_latest_user_turn` 会拿不到当前轮（实测 eval 窗口未见此竞态输过，B1' 轮候选均成功写入 WM）。

---

## 附：验收脚本

全量脚本见补丁内 `scripts/devtools/acceptance_memory_revival.py`（含逐步 PASS/FAIL、JSON 摘要、DB 断言），核心断言逻辑：

```python
# MR-1：聊天一轮后记忆表有写入（DB 断言，不耗 LLM）
lanes = db_scalar(f"SELECT count(*) FROM episodic_memories WHERE user_id='{user_id}' "
                  "AND source_lane='inferred_extraction' AND deleted_at IS NULL")
assert lanes >= 1  # 会话1 两条"帮我记住"埋点后，异步 lane 最长等 30s

# MR-2/跨会话：新会话问考试
q1 = ws_chat(token, str(uuid4()), "根据你的记忆，我之前提到过什么考试？")
assert "数据结构" in q1["text"]
# MR-2/slim：新会话超短问句
q2 = ws_chat(token, str(uuid4()), "我最喜欢的电影是什么？")
assert "星际穿越" in q2["text"]

# MR-3：presigned PUT 直传（凭证对齐后 200）→ confirm → 轮询 processed
# MR-4：use_document_context:true 问 RAG_KEYWORD → 回答含性状/保存要求且无"没有拿到/不能复述"
```
