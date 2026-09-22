# P1-5 · 星图 mastery 不生长 —— 断环诊断与修复报告

> Worker: wt101（wt101-v3, 基于 main@2d4a6084）｜2026-09-22｜LIGHT（零模拟器/零构建/零 commit）
> 交付：`changes.patch`（4 文件）+ 本报告 + `scripts/devtools/p15_outcome_absorption_probe.py`（可复跑探针，已登记 devtools README）

## 1. 一句话断环

**G-02 outcome 吸收器的确定性节点解析链对「无显式关联」的完成任务拿不到任何节点**：`outcome.recorded` 事件正常发布（X-08）、消费者正常在跑并正常吃掉（活栈实证 lag=0/pending=0），但 `_resolve_node_ids` 走完 `correlation_node_id → task.knowledge_node_id → TaskKnowledgeLink` 三环后为空 → `action=no_target` → 证据融合从未发生；用户看到的「解锁」只是 DF-5 legacy spark（0 真实时长 → 0 增长）——即 **任务是长在「任务标题星」上的，而吸收器不认识这颗星**。

## 2. 断环图（逐环活栈实证）

```
任务完成(API) ──✅──> task.completed + capture_task_outcome ──✅──> outcome.recorded 落 Redis stream
 (X-08)              task_service.py:806/812                        (stream 实证：outc_9119e1e4… / outc_417e7c29…)
                                                                          │
                                                                          ✅ 消费者在跑：OutcomeAbsorptionConsumer
                                                                          (main.py:451-459 lifespan 接线；非 celery——
                                                                           Redis Stream 消费组 galaxy_outcome_absorber，
                                                                           活栈 consumer galaxy-outcome-absorber-12290
                                                                           idle≈1.3s，entries-read 推进，lag=0, pending=0)
                                                                          │
                                                                          ✅ 消费者调用吸收器
                                                                          │
     ┌────────────────────────────────────────────────────────────────────┘
     │ GalaxyOutcomeAbsorber._resolve_node_ids（修复前）
     ├─✅/⚪ correlation_node_id        ── 事件里没有（task.knowledge_node_id 为 NULL 时 producer 不带，实证）
     ├─⚪ task.knowledge_node_id        ── DB 实证：northstar 任务 5a83a029… = NULL
     ├─⚪ TaskKnowledgeLink prerequisite ── DB 实证：task_knowledge_links 0 行
     └──> resolved=[] → action=no_target（旧代码）→ mastery_audit_log 无 evidence 行（DB 实证 0 行）
     💥 断环：outcome_absorption_service.py:_resolve_node_ids（修复前 L309-328）

并行事实（非断环，但构成「只解锁不生长」的用户观感）：
  task_service.py:733-757（daily-flow DF-5）在完成点击时 ensure_task_node(标题)→spark_node：
  星被确定性创建/解锁 ✅，但 resolve_spark_study_minutes(None)=0（X-04 诚实缺省）→
  legacy 时间公式 0 分钟 = 0 增长 → mastery_score=0/minutes=0（audit 行实证 task_complete 0→0）。
  G-02 的证据融合（TASK_OUTCOME 60×0.8 → 首次完成 0→30）本应在此节点生效，却因上述断环缺席。
```

## 3. 修复面

**唯一改动点：`backend/app/services/galaxy/outcome_absorption_service.py` `_resolve_node_ids` 补第 4 环（DF-5 同源标题锚）**。

- 解析链扩为：`correlation_node_id → task.knowledge_node_id → TaskKnowledgeLink → DF-5 标题锚`；
- 第 4 环**复用完成管线同一个函数** `GalaxyService.ensure_task_node(task.title, task_id)`（惰性导入，与 task_service 同款）：
  归一化标题**精确命中**既有节点优先（「TCP 拥塞控制」任务点亮种子星而非复制），否则物化 `uuid5(title)` 确定性任务星——
  吸收与 legacy spark 从此落**同一颗星**；无任何关键词模糊匹配（模块纪律不变，docstring 已同步更新）；
- 锚不可得时 fail-soft 记 warning → 诚实 no_target；
- **幂等语义零破坏**：点亮硬门仍是 append-only `mastery_audit_log` 的 `oc=/tk=` 标记段；`tk=` 同因合并跨第 4 环依然成立
  （任务完成 outcome 与其 run receipt outcome 只融合一次，新增单测钉死）。

设计取舍：修在**消费侧**而非 producer——所有 outcome.recorded 产生方（任务完成、X-05 run receipt）一律受益，且不在 X-08 纯函数里引入 IO。

未做（诚实边界）：`total_study_minutes` 仍为 0——X-04 真相链刻意不回填 estimated 时长（不虚报），minutes 生长需真实计时（started_at→completed_at），属诚实性设计而非断环，本卡不动。

## 4. 活栈证据（真实开发库 + 活栈 API，before/after mastery）

活栈拓扑：FastAPI :8000 = **主仓**代码（旧代码，PID 12290，9-21 启动，含 DF-5）；gRPC :50051；网关 :8080；无 celery 进程（absorber 非 celery，接线在 FastAPI lifespan）。

### 4.1 历史事件回放（northstar 首证任务 5a83a029…，账号 ed1ee655…）

| 项 | 值 |
|---|---|
| BEFORE（user_node_status） | 节点 abc4e27f「Day 1 · 诊断分诊 - 诊断分诊」**mastery=0.0**，unlocked=true，minutes=0（与 BP-5 证据逐字段一致） |
| payload 重构 | `build_task_outcome_capture` 派生 `outc_9119e1e4257923cb507d5e1b5f9ba251` —— 与 stream 中真实事件**逐字节同 id**（幂等派生实证）；correlation 仅 task_id/plan_id，无 node_id |
| 修复版吸收 | `action=lit`，**mastery 0 → 30.0** |
| audit 行 | `reason=evidence:task_outcome`，`request_id=obs=60;conf=0.8;oc=9119e1e4…;tk=5a83a029…`（oc=/tk= 标记完整，G-01 可回放） |
| 复跑（跨进程） | `action=duplicate`，mastery 保持 30.0（幂等在真实数据上成立） |

### 4.2 全新 API walkthrough（2026-09-22 当日，探针账号 northstar_p15_1790080378）

逐环走查（旧代码活栈）：

1. ✅ 注册/登录 → 建 LEARNING 任务 `175132b6…`（knowledge_node_id=NULL）→ start → complete 200；
2. ✅ 事件落 stream：`outcome.recorded outc_417e7c29fa5f435da9c3f1635e6196b1`，correlation 仅 `correlation_task_id`；
3. ✅ 消费者吃掉：`galaxy_outcome_absorber` pending=0、entries-read 越过该条（旧代码吸收 → no_target）；
4. 💥 断环复现：节点「P1-5 探针 · 欧拉回路判定练习」unlocked=true 但 **mastery=0、minutes=0**；audit 仅有 legacy `task_complete 0→0` 行，无 evidence 行；
5. ✅ 修复版探针跑同一任务：`action=lit`，**mastery 0 → 30.0**；复跑 `duplicate`；
6. ✅ 用户可见面（`GET /galaxy/graph` 经网关代理读模型）：该节点 `mastery=30.0, learning_state=weak, unlocked=true`，且节点 `graph_event_sources` 出现溯源行 `outcome.recorded / outcome_ledger / outc_417e7c29… / positive`（GJ08 可解释性）。

### 4.3 探针复跑方式

```bash
cd backend && SECRET_KEY=test \
  DATABASE_URL='postgresql+asyncpg://<user>:<pass>@127.0.0.1:5432/sparkle' \
  python3.11 ../scripts/devtools/p15_outcome_absorption_probe.py \
  [--task-id <已完成任务id>]   # 默认 northstar 首证任务
```
幂等安全：重放只产生 duplicate，不重复点亮。

## 5. 红→绿回归

| 套件 | 结果 |
|---|---|
| 新增 2 测（无显式关联 → 标题锚点亮既有星 / 物化确定性任务星 + receipt 同因合并） | **HEAD（无修复）= 红**（`lit` vs 实际 `no_target`，单文件还原法取红证，随即恢复）→ **修复后 = 绿** |
| `tests/services/galaxy/test_outcome_absorption.py` 全量 | 14/14 绿（12 既有全保持：幂等/NEGATIVE/NEUTRAL/翻转防御/溯源/无目标防御） |
| 联合回归：galaxy 全目录 + task_galaxy_coupling + x08_outcome_ledger_gj + outcome_ledger_service + error_book_mastery_sync×3（unit/loop/500fix/integration） | **230 passed, 0 failed** |
| ruff / black(120) | 全过（探针脚本已格式化） |

## 6. CP-03 分界（错题 review mastery 同步半程失败——查明，未改）

- review 同步**已接线且会执行**：`error_book_service.py:1245` 提交 review 后调 `ErrorBookMasterySyncService.apply_review_feedback`；
- 「半程失败」真因：同步依赖 `error_record.linked_knowledge_node_ids`，该字段由 `analyze_and_link`（LLM 分析面）产出；链接为空时同步**合法 no-op**（附 `missing_knowledge_links` hint，`error_book_mastery_sync_service.py:112-115/179-182`）。northstar 轮的错题恰好无链接节点 → 星图无反应；
- 这是**错题→知识节点链接的上游缺口**（BP-6 SubjectEnum 无大学科目 + analyze_and_link LLM 链路），与任务完成链不同源，且 wt97/wt98 面另有归属——本卡不改，如实分界。既有 error-mastery 测试 4 套全绿，说明同步服务本体健康。

## 7. 需长时运行观察的项

1. **修复代码进活栈**：wt101 patch 合入主仓并重启 :8000 lifespan 后，outcome.recorded → 标题锚吸收才会全自动化。当前活栈仍跑旧代码（探针已证明同一 DB 上修复版行为）。
2. **celery beat/周期任务**：本链路无 beat 依赖（absorber 为常驻 Stream 消费者，随 FastAPI lifespan 起）。若运维面需要独立进程形态，`OutcomeAbsorptionConsumer` 可独立 `start()`（与 TaskEventListener 同款），无需 celery worker。
3. **Kalman 收敛观感**：单次完成 0→30（weak→…），连续完成同主题星会继续收敛（60 渐近封顶，永不合格性宣称 mastered——需 quiz 级证据）。建议下次北极星轮用 GP-03 复测 mastered/覆盖宣称。

## 8. 收工核查声明

- [x] 起过的进程：**无常驻进程**（探针为一次性脚本，跑完即退；未起任何 celery/consumer/服务实例，未占用独立端口）；
- [x] 共享设施只读使用：Redis/Postgres 容器仅查询 + 探针幂等写入（northstar_p15_* 探针账号与任务星 mastery，属测试账号面，与既有 northstar 驱动轮同口径）；
- [x] /tmp 自清：`p15-absorber-fixed.py`、`p15_probe_user.txt`、`p15_probe_token.txt`（600 凭据）删除；
- [x] 主仓零写入（活栈 FastAPI 为主仓进程，全程只观测）；
- [x] 未碰 wt97（memory）/wt98（题包）任何文件；改动面仅 wt101 内 4 文件（2 改 2 新）；
- [x] 红线遵守：G-02 `oc=/tk=` 幂等语义未破坏（单测+真实数据复跑双证）；无 commit/push；
- [x] worktree 内构建产物 `backend/app/gen/`（proto-gen 生成，gitignored，不进 patch）留存于本 worktree，随 worktree 生命周期回收。
