# NBP-6 · WS 声明 fact → 今日面板投影延迟 30-90s 消除（收工报告）

- Worker：V3 舰队 wt128 ｜ 日期：2026-09-22 ｜ 卡别：P2（北极星 LOOP3 C 线「memory 必须真实有用」）
- 交付面：`backend/app/services/working_memory_pipeline_service.py`（唯一修改）+ 新测试 + 探针脚本
- 验证：定向回归 933 用例 **905 passed / 8 failed / 4 errors——12 个非绿项经基线对照全部为存量问题（与修复前逐项一致），零回归**；新测试 4 用例红→绿。

---

## ① 延迟归因（哪一段吃掉 30-90s）

**结论：30-90s 全部吃在写侧投影链带内——`WorkingMemoryPipelineService.process_chat_turn` 把明示事实的 L1 提升排在 LLM 抽取往返之后。读侧（今日面板/画像/账本）零缓存，无需任何缓存失效。**

写链（用户说完话 → fact 落库）：

1. WS 轮次收尾 → `_persist_assistant_message` 直调 `MemoryInferredWriteLaneService.enqueue_from_chat_turn`（response_builder.py:1289 注释，NBP-1 单一事实源）→ `loop.create_task(_run_background)`（memory_inferred_write_lane.py:196）。**进程内后台任务，无队列无 Celery，立即起跑** ✓
2. 后台任务内抽取（确定性正则，~0ms）。LOOP3 实证：occurred_at=15:27:38.13（= enqueue 即抽取）✓
3. `working_memory_enabled` 默认 **live**（settings.py:252）→ 进 pipeline：
   - **pipeline_service.py（修复前 41-54 行）：先 `await self.llm_extractor.dry_run_extract(...)`——真实 LLM 调用**（`llm_extractor_enabled` 默认 live，settings.py:253；模型 `claude-haiku-4-5`，settings.py:851；`llm_service.chat` 的 fallback 链首块超时 45s/推理 90s，llm_service.py:67-70）。供应商拥塞时（LOOP3 恰有单并发 MiniMax 排水 worker 在跑）整段滞留数十秒。**← 30-90s 在此**
   - 之后才进候选循环：upsert working memory → `promote_entry_now` → episodic 落库。LOOP3 实证：created_at=15:28:29.36，**带内滞留 51.2s**。
4. 读面（fact 落库后到用户可见）——**全部直查 DB，零缓存**：
   - `/api/v1/memory/episodic`（memory.py:276）→ `list_recent_episodic`（memory_service.py:776）直查；
   - pending-commitments（memory.py:524 / community_router.py:208）→ `list_pending_commitments`（memory_service.py:1105）直查；
   - `goal_today_view`/`sprint_task_ledger` 读 Task 表（事实不经此面）；
   - `StateAggregatorService` 每请求新实例（memory.py:553 等），进程内 TTL 缓存不跨请求；
   - `ProfileContextService` Redis 缓存（TTL 120s，epoch 门）只编排 calendar/workflow/content/accountability 信号，**不摄取 episodic 明示事实**。
   - 且 `create_episodic_memory` 内部 commit（memory_service.py:963-964 附近 `await self.db.commit()`）——跨进程读立即可见。

**LOOP3 30s 探针扑空复算**：30s 快照 at=15:28:27.7，距写入 15:28:29.36 差 **1.6s**——不是缓存 TTL、不是 beat 周期，就是写侧被 LLM 往返卡住。

## ② 修复方案与 A/B 裁决

**裁决：A（即时投影）的「重排」形态。** 具体做法（唯一修改点，`working_memory_pipeline_service.py::process_chat_turn`）：

- 把 declared 候选的 upsert + `promote_entry_now`（快速道）**移到 `dry_run_extract` 之前**（`wm_mode != "off"` 门内）；
- LLM 抽取面照旧其后运行，规则/LLM 候选处理顺序与语义零变化；
- declared 候选从后置 `effective_candidates` 循环移除（防止双处理虚增 mention_count）；
- wm=off 分支行为保持：LLM dry-run 照跑、pipeline 返回空（有测试锁定）。

效果：明示事实投影延迟与 LLM 健康度解耦——turn 收尾后仅剩 Redis upsert + L1 门禁 + DB 写（亚秒级）。

- **为什么不选 B（缩短周期/TTL）**：此链路上根本没有 Celery beat 任务和读缓存——`enqueue` 是进程内 `create_task`，读面直查 DB。没有周期可缩。
- **为什么不是「缓存失效」形态**：读面无缓存可失效；本卡语境下 A 的正确形态是移除写侧串行 LLM 依赖（即「写后立即可见」）。
- **考虑过并否决**：给 `dry_run_extract` 加 `asyncio.wait_for` 上限——会截断 20-50s 的慢但成功的抽取（质量回归风险），且重排后 declared 已不受影响，规则候选延迟属既有行为，不在本卡范围。
- **已知微小语义位移（如实申报）**：`explicit_confirmation`（同句「记住这个」）取 `accepted_entries[0]` 作 mark_correct 对象，顺序由 [rule, llm, declared] 变为 [declared, rule, llm]——规则候选存在时无变化；无规则候选时，确认会落在 declared 条目而非 LLM 候选上（语义上更合理）。pipeline 返回值在唯一生产调用点被丢弃（memory_inferred_write_lane.py:305-314）。

## ③ 测试矩阵

| 套件 | 结果 |
|---|---|
| 新增 `tests/unit/test_nbp6_declared_fact_projection_latency.py`（4 用例） | **4 passed** |
| ├ declared_fact_written_before_llm_extractor_call（红→绿核心：抽取被调时刻 declared 必须已落库；还原旧码实测 FAILED） | 红→绿 ✓ |
| ├ declared_candidates_not_double_processed_after_reorder（promote 恰好 N 次 + upsert 总数 = declared+rule） | ✓ |
| ├ today_surfaces_visible_immediately_after_write（写完无 sleep 直查 `list_recent_episodic`/pending-commitments，due_at 正确） | ✓ |
| └ working_memory_off_keeps_legacy_behavior（wm=off：dry-run 照跑/返回空/零写入） | ✓ |
| 定向回归 `-k "memory or today or profile or fact" --ignore=tests/northstar_eval`（933 用例） | 905 passed / 20 skipped / **8 failed + 4 errors 全部与基线逐项一致（存量）** |

存量非绿项成因（基线复跑确认，与本卡无关）：
- `test_memory_admin_api` 4 例 + `test_memory_working_memory_api` 1 例：kill-switch 写入需 Redis（"write_mode called without Redis"），本机测试无 Redis；
- `test_preference_to_plan_e2e` / `test_user_insight_compiler` / `test_outcome_promotion_governor` 3 例：profile 域存量断言失败（基线一致）；
- 4 个 integration ERROR：需活 Postgres（`asyncpg InvalidPasswordError`）。

**Celery 影响申报**：本修复未动任何 Celery 配置/任务（该链路无 Celery 参与）；default/glm_batch 队列零影响。

## ④ verify_probe.py 用法（活栈验证留给主会话）

```bash
python3 v3-output/NBP6-PROJECTION/verify_probe.py                       # 默认 127.0.0.1:8080
python3 v3-output/NBP6-PROJECTION/verify_probe.py --assert-under 5      # 延迟≥5s 退出码 1（验收判据）
```

流程：注册/登录（经 gateway，凭据复用 `/tmp/nbp6_probe_creds.json`，收工自清）→ WS `/ws/chat` 发「提醒一下：我有一门 量子引力动力学<hex6> 期末考试在 7 天后，目标 85 分。」→ 终止帧到达立即轮询 `/api/v1/memory/episodic?limit=50`（0.5s 间隔，上限 180s）→ 输出 `turn_seconds`、`latency_from_turn_end_s`、`latency_from_send_s`、JSON summary。依赖 stdlib + websocket-client（本机已装 1.9.0）。预期修复后 latency_from_turn_end 为亚秒~秒级；修复前预期 30-90s。

## ⑤ Worker 五要素

**① 基线**：见上节 ①——带内 51.2s 实证（occurred_at 15:27:38.13 → created_at 15:28:29.36），30s 探针差 1.6s 扑空；延迟段 = pipeline 内 `dry_run_extract` 串行阻塞（45s/90s 首块超时 + fallback 重试）。

**② 红线面（触碰文件逐一说明）**：
- `backend/app/services/working_memory_pipeline_service.py`（唯一修改）：只重排 `process_chat_turn` 内部顺序。LLM 抽取仍被调用（测试锁定）；wm=off 行为零变化（测试锁定）；declared 不双处理（测试锁定）；规则/LLM 候选的 upsert/promote 语义不变（`effective_candidates` 构成仅少了 declared——它们已在快速道处理）。proto 未动；无迁移；无 Celery 配置变更。
- `backend/tests/unit/test_nbp6_declared_fact_projection_latency.py`（新增，纯增量）。
- `v3-output/NBP6-PROJECTION/{verify_probe.py,REPORT.md,changes.patch}`（新增，规范目录）。
- 环境注记：worktree 缺 gitignored 的 `backend/app/gen/`（buf 生成物），为使测试可收集从主仓拷贝（proto/ 两树一致，仅 .DS_Store 差异；未入 git，随 worktree 生命周期回收）。

**③ 冲突面**：CP-01（确认端点，wt125 动 plans API）——本卡只动 working-memory pipeline（Python 引擎 memory 域），与 plans API 零交集。未发现其他在途改动触碰 `working_memory_pipeline_service.py`。

**④ 诚实申报**：
- 修复只解除 declared 事实的串行阻塞；**规则候选/LLM 候选仍排在 LLM 抽取之后**（既有行为，若也要解卡需单独评估抽取质量代价）；
- `accepted_entries[0]` 顺序位移一处（见 ②），生产返回值被丢弃、唯一可见影响面是同句显式确认的 mark_correct 目标；
- 主会话活栈实测未跑（本卡纪律：不重启活栈）；延迟结论来自代码归因 + LOOP3 证据复算 + 单测红绿，活栈数值待主会话用 verify_probe.py 落证。

**⑤ 收工核查**：
- `/tmp`：已清 `wt128_pipeline_fixed.py`（红/基线对照临时件）与探针凭据（探针自身收尾自删 `nbp6_probe_creds.json`，本次未实跑故本就不存在）；无其他遗留。
- 进程：无 pytest/模拟器/浏览器残留（后台回归已结束）。
- `git status --short` 交付清单比对：`M backend/app/services/working_memory_pipeline_service.py` + `?? backend/tests/unit/test_nbp6_declared_fact_projection_latency.py` + `?? v3-output/NBP6-PROJECTION/` 三项，与交付物一一对应；未 commit/push；index 已还原（`git reset -q`）。
