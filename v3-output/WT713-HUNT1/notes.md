# WT713-HUNT1 — 后端写路径数据正确性专项猎缺（第一轮）

- Agent: wt713（双轮审查机制第一轮）
- 日期: 2026-09-27
- 分支: `agent/node-b/wt713/hunt1`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt713-hunt1`，base main@9b30fb32）
- 主仓只读；本 worktree 仅动台账（`v3/06_agent_fleet/DYNAMIC_ISSUES.md`）与本目录产物
- 环境: 主仓 venv `/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python`（3.11.15）；`app/gen` 按先例主仓 `cp -RL` 拷贝不入库；探针均以 `SECRET_KEY=x` 直跑（非 pytest），跑完即删，副本存本目录

## 0. 结论速览

- 存活登记 4 条：V3-FIX-417（P2，幂等洗白，运行级实证）、418（P3，融合状态跨进程丢更新，运行级实证）、419（P3，社区写面漏软删/拉黑闸，运行级实证）、420（P3，连胜跨日并发窗口，推理链）
- 台账 verify：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → 300 行全 8 裸管、零冲突标记、零重号、状态枚举合法，exit 0 零 FAIL
- 排查未成立/暂缓 9 项见 §3（帮第二轮省力）

## 1. 猎场走查图

### 猎场2 幂等与重试语义（FIX-336/389 旁路扫描）→ **V3-FIX-417**

executor 闸门本体（executor.py:515-663，FIX-336/223 修后形态）经运行探针确认正确：无键拒、同键 replay 恰一次、in_progress 恒拒 Conflict、interrupted 恒拒 Interrupted。旁路不在闸门、在**重试环**：

- `AgentErrorHandler.should_retry`（error_handler.py:230-263）：三类幂等拒绝的消息不含 permission/validation/not found 关键词 → 走默认 `return True`。运行探针实录三连 True。
- `handle_tool_error`（error_handler.py:87-93）：修正轮以 LLM 新 id 重调 executor、**不带 idempotency_key** → executor.py:517 `key = idempotency_key or tool_call_id` → 新键无账本行 → 写副作用放行。
- 喂入口 4 个，全在 `app/api/v1/chat.py`：:583（/task 批量自修正，排除集只有 BudgetExceeded/IdempotencyInterrupted）、:804（/stream，同排除集）、:935 与 :967（/confirm，**无过滤**且首轮意图键 `hitl:{action_id}:{tool_name}` 在修正轮被丢）。
- X-09 注释的排除理由「确定结局，修正轮只会再发起注定被拒的调用」对 Conflict 恰不成立——修正轮换新键反而**被放行**，比被排除的两类更危险。
- 主链（standard_workflow/orchestrator）不经过 error_handler（grep 零命中），wt699 修的 chat 轨不受影响——本发现是 REST 面独立缺口。

运行级 e2e（真 executor 闸门+真账本唯一索引+stub write 工具+LLM 桩）：

```
attempt1: True error: None count: 1            # 键 K 真执行
attempt2 (same key): False error_type: IdempotencyConflict count: 1   # 闸门正确拒绝
entered correction: True final.success: True
tool execute_count after correction: 2          # 冲突拒绝被洗成第二次真执行
RED: IdempotencyConflict laundered into a second real execution (count=2)
```

复现件：`repro_idem_launder.py`（e2e）+ `repro_idem_launder.log.txt`；单元级前置探针（should_retry 三连 True）并入 e2e 脚本注释。

### 猎场4 per-user 进程内锁普查（FIX-193 同型）→ **V3-FIX-418**

全仓 `asyncio.Lock` 普查（grep 15 处）逐一定性：

| 点位 | 模式 | 定性 |
|---|---|---|
| `services/state_estimator_service.py:38` | per-user 进程内 | FIX-193 已修（Redis SET NX claim，wt705） |
| `services/evidence/fusion_engine.py:28` | per-user 进程内（模块级 WeakValueDictionary） | **同型未修 → V3-FIX-418** |
| `services/srl_phase_tracker_service.py:73` | per-key 进程内 | 健康：:141-142 local+distributed 双锁（Redis 故障 fail-open 有 metric） |
| `aurora/proactive/autoexec.py:773` | 进程内 inflight set | 无生产调用面（见 §3-N1） |
| 其余（age_client/execution_service/galaxy_grpc/cognitive_service/llm_service/achievement_engine/llm concurrency/cognitive_stream_worker） | 进程内单例资源保护（缓存/连接/模块 dict） | 非跨进程共享写态，不适用 |

跨进程论证：FusionEngine 调用面四写方——chat 请求路径（任意 worker）、cognitive API、community_feedback_service、TaskEventConsumer（main.py:284 每 worker lifespan 各起一个，`sparkle_events` 消费组按 consumer 组分发）——多 worker 部署下同用户两写方落不同进程即互不可见锁。部署拓扑沿 FIX-193 行既裁口径（wt705 已把同款推定升级为双进程模拟实测）。

运行级实证（单事件循环双「进程」模拟，换 `_user_state_locks` 表=换进程，共享同一 fake redis）：

```
last_evidence_ids: ['ev-a']
RED: cross-process lost update — ev-a present=True, ev-b present=False
```

A 在 gated setex 停车（已读空态、未写回）→ B 完整读-融-写 → 放行 A → A 基于空态的写回覆盖 B → B 的证据静默丢失。对照同表锁（单进程语义）双证据并存 GREEN，排除非锁表解释。复现件：`repro_fusion_cross_process.py` + `repro_fusion_cross_process.log.txt`。

### 猎场5 软删/可见性/黑名单写侧对偶（FIX-192/08/20 家族）→ **V3-FIX-419**

- 读面护栏清单：feed `Post.not_deleted_filter()`（community.py:418）+ 双向 block 排除（:420-431）+ cohort 子句（:310）；群目录四谓词（V3-FIX-20 修）。
- 写面对照：`create_post_comment`（:604-614）与 `like_post`（:509-518）帖定位**只有 cohort 子句**——软删帖可评论/点赞且 `comment_count`/`like_count` 在已删行上继续自增（:626-628）；任一向拉黑关系不闸写（读面隐藏但按 id 直写绕过）。
- 运行级实证（sqlite 探针）：软删 + 活跃 UserBlock 在场时，写端点同型查询命中（True）、feed 同型查询为空（False）——读写不对称坐实：

```
deleted+blocked post visible to comment/like write path: True
active block relationship in place: True
same post visible to feed read face: False
RED: write face accepts soft-deleted + block-hidden posts the read face filters
```

复现件：`repro_softdel_block_gate.py` + `repro_softdel_block_gate.log.txt`。

### 猎场1 聚合计数器一致性 → **V3-FIX-420**（推理链）+ 健康面清单

- 连胜计数（`achievement_engine._update_streak_stats` :2049-2171）：增量式，`_get_or_create_streak_stats`（:2243）无 `with_for_update`（对照同文件成就解锁 :1470/:1478 有锁）。分析结论：**同日并发无害**（双侧从同基值同值计算，后写覆盖=正确值）；**跨本地日 straddle 并发有害**（见台账 420 行推理链①②③：stale delta=2 → 断签分支覆写 current_streak=1 + day0 误记 MISSED，或冻结分支白烧卡+day0 误记 FROZEN）。未运行级复现（sqlite 无法忠实模拟 PG READ COMMITTED 双连接写锁时序），台账行已如实标注，留第二轮真 PG 红测固化。
- sprint 账本（sprint_task_ledger.py）：单一事实源+随取随算重算模式，无增量/重算分叉面。健康。
- outcome 账本（outcome_ledger_service.py）：纯读模型、derive_outcome_id 确定性、自述「无写入面即无写侧幂等负担」。健康。
- 工具调用账本（tool_call_ledger_service.reconcile_stale_in_progress）：单向收敛（in_progress→interrupted 永不回退、already_resolved 幂等）。健康。
- UserDailyMetric（models/analytics.py）：生产零写入方（V3-FIX-353 已裁），无写侧害。
- photon 账（photon_service.py）：`with_for_update`（:83/:148）+ 原子条件 UPDATE（:187-195 `WHERE balance >= amount`）+ unique index 幂等仲裁（:408 日首发竞态）。货币级护栏在位。健康。
- streak_quality.compute_quality 有 24h 缓存（当日完成会读到陈旧 today_quality），属读/展示面，本轮不展开。

### 猎场3 事务边界

- 任务完成主链（task_service.complete :688-940）：:738 commit 后全部副作用（card 投影/plan 进度/galaxy spark/sprint mastery/event 发布/outcome 捕获/self model/SRL 事件/north star）逐项 try-except-warning 留痕；`event_bus_reliable.publish` 自带重试+DB DLQ（运行日志亲见 retry 1/3→DLQ persist 路径），未发现无痕副作用。健康（best-effort 隔离契约 + test_consumer_exception_propagation 白名单）。
- `create_post_comment`（community.py:626-628）comment INSERT + 计数自增同事务单 commit、通知 push 在 commit 后 try 包裹——事务边界正确（其闸门缺失已由 419 覆盖）。
- `process_event`（achievement_engine :397-401）外部事务托管时 begin_nested、否则 nullcontext——边界声明清晰。
- 未发现「commit 后副作用失败无补偿亦无留痕」的存活面；未新登记。

## 2. 登记清单（台账行全文见 DYNAMIC_ISSUES.md :341-344）

| ID | Severity | 一句话 | 证据 |
|---|---|---|---|
| V3-FIX-417 | P2 | AgentErrorHandler 自修正环把三类幂等闸门拒绝洗白成新键真执行（chat.py 四 REST 面喂入，HITL 意图键修正轮被丢） | e2e 运行级：真闸门下 Conflict→correction→execute_count=2（repro_idem_launder.log.txt） |
| V3-FIX-418 | P3 | FusionEngine.update_user_state per-user 进程内锁跨进程互不可见，Redis GET->fuse->SETEX 后写覆盖前写（FIX-193 同型） | 双进程模拟运行级：ev-b 丢失 RED / 同表锁 GREEN（repro_fusion_cross_process.log.txt） |
| V3-FIX-419 | P3 | community 评论/点赞写面缺软删+拉黑双闸（feed 读面有两闸），计数器在已删行上自增 | sqlite 探针运行级：写面命中 True / 读面过滤 False（repro_softdel_block_gate.log.txt） |
| V3-FIX-420 | P3 | 连胜统计无行锁，跨本地日 straddle 并发以 stale 计算覆写（断签毁连胜/白烧冻结卡/day0 误记） | 推理链（PG READ COMMITTED 三环），未运行级复现已如实标注 |

## 3. 排查未成立 / 暂缓清单（帮第二轮省力）

- **N1 autoexec inflight 跨进程 TOCTOU（暂缓）**：`aurora/proactive/autoexec.py:822-848` inflight 去重是进程内 set，find→execute→record 间无跨进程 claim，理论 TOCTOU 与 418 同族；但全仓 grep `handle_operation` 生产调用面为零（门未接线），危害暂无活性载体。接线卡落地时同批处理。
- **N2 连胜同日并发（不成立）**：两请求并发同日首事件，双方从同基值同值计算（S+1/T+1），后写覆盖=正确值；冻结分支扣减同理收敛。只有跨日 straddle 才分叉（已登记 420）。
- **N3 fusion_engine append_trace/record_trace_loss（不成立）**：lpush+ltrim+expire 非读改写计数；丢失路径有 incr 留痕（BELIEF_TRACE_LOST_KEY）。
- **N4 executor 闸门本体（不成立）**：FIX-336/223 修后形态运行级亲证正确（同键 replay 恰一次/Conflict/Interrupted/ArgsMismatch/InvalidUserIdentity/LedgerUnavailable 各分支按类拒）。
- **N5 execute_tool_calls 批量面（不成立）**：`call.get("id")`（executor.py:1397）透传模型 id 作键，REST 批量面写工具有键（键源尝试唯一属 336 已裁语义）。
- **N6 srl_phase_tracker（不成立）**：local+distributed 双锁在位，Redis 缺席 fail-open 有 `SRL_TRACKER_LOCK_CONTENTION_TOTAL` 计数，模式正确。
- **N7 photon/redeem 计数（不成立）**：行锁+条件原子 UPDATE+唯一索引幂等仲裁三层在位（见 §1）。
- **N8 任务完成 commit 后副作用（不成立）**：全部 best-effort try-warning 留痕 + event_bus_reliable 重试/DB DLQ，无无痕面。
- **N9 UserDailyMetric/sprint 账本/outcome 账本（不成立）**：分别=零写入方（FIX-353）、纯重算单一事实源、纯读模型——三者无写侧害。

## 4. 复现件索引

| 文件 | 内容 |
|---|---|
| `repro_idem_launder.py` | 真 executor 闸门 e2e：Conflict 拒绝→自修正环→fresh 键第二次真执行（count=2 RED） |
| `repro_idem_launder.log.txt` | 上项运行实录 |
| `repro_should_retry_unit.py` | 前置单元探针：should_retry 对三类幂等拒绝三连 True + 修正轮 fresh-key 无意图键实录 |
| `repro_fusion_cross_process.py` | FusionEngine 双「进程」模拟：换锁表+共享 fake redis+gated setex 停车 |
| `repro_fusion_cross_process.log.txt` | 上项运行实录（RED） |
| `repro_softdel_block_gate.py` | community 写面 vs feed 读面谓词不对称探针（含 `_cohort_visible_post_clause` 逐字拷贝） |
| `repro_softdel_block_gate.log.txt` | 上项运行实录（RED） |

运行口径：`cd backend && SECRET_KEY=x <venv-python> tests/unit/test_wt713_*_tmp.py`（探针已按纪律跑后即删 tests/ 下副本，本目录存档为准）。

## 5. 边界与诚实声明

- 主仓只读；本 worktree 未改任何生产代码；探针在 tests/ 下运行后已删除。
- 420 号为推理链证据（非运行级），已在台账行内与本章双处如实标注；其余三条均为运行级实证。
- 读侧/展示面问题（如 streak_quality 当日缓存陈旧）不在本轮范围，未展开未登记。
- 部署拓扑假设（uvicorn 多 worker + 每 worker lifespan 起消费者）沿 FIX-193/wt705 既裁口径。
