# FIX-583 verification —— 挂死机制定性（锁图）+ 修复验证

## 1. 取证定性：Q01 挂死的锁图与真因

### 1.1 证据来源

- `wtQ01/v4/evidence/V4-Q01/limitations.md` §2（pg_stat_activity 锁快照实测记录）
- `wtQ01/v4/evidence/V4-Q01/db/r4…r7_part1_db_evidence.txt`（三僵尸 run 只读快照）
- 代码（Q01 被测版本 `5cbc715f` 是当前 main `3528623a` 的祖先，且
  `hybrid_journey_service.py`/`journey.py` 其间零改动——**读到的代码就是缺陷本体**）

### 1.2 时间线事实（DB 快照钉死）

以 q01up083360 / run `57f4a41f` 为例（r5 快照，三例同构）：

| 事实 | 值 | 推断 |
|---|---|---|
| `agent_runs.created_at` | 10:41:03.326108 | run 创建 |
| `agent_runs.updated_at` | 10:41:03.344481（+18ms） | **RUNNING 迁移是最后一次落库** |
| `agent_tool_calls` | **0 行** | prep 工具账本写**从未提交** |
| `hybrid_journey_artifacts` | **0 行** | prep 产物**从未提交** |
| 网关计时 | prep success 3818ms | 工具本身真实执行并成功（9 chunks 材料在库可检） |

三例同为 `status=RUNNING / current_stage=prep` 永久冻结。

### 1.3 锁图定性（两层拆开，与 pg 快照逐条对上）

**挂点层（事实）**：挂死发生在 **prep 工具成功返回之后、`complete_agent_step`
提交之前**的推进窗口。修前该窗口的全部工作——账本收尾、prep 产物 INSERT、
`complete_agent_step`（`SELECT … FOR UPDATE` agent_runs 行）、`await_user_step`
——全部跑在**请求事务**内（`get_db` 注入的同一 `AsyncSession`；executor
`owns_session=False` 使工具账本写滞留为未提交行）。工具成功后该事务一旦在某
个 await 上永不返回，会话即以**未提交写 + 行锁**的形态被永久占用。

**锁形态层（与快照吻合）**：Q01 锁快照记录僵尸会话 `idle in transaction`
（末语句 `SELECT user_push_opt_in...`）持有该用户 `agent_runs` 行级锁
（transactionid）。定性要点：

1. **不是 DB 行锁互等**（至少不是僵尸会话自身阻塞在锁上）：`idle in
   transaction` 表示 PG 已完成其末语句、等待客户端下一条指令——若是锁等待，
   会话应为 `active` 且 `wait_event=Lock`。即：应用侧在**持有开放事务**时
   await 了一个无超时、不返回的异步操作（应用层挂起，事务与锁被动滞留）。
   「末语句 user_push_opt_in」与当前代码 `start_hybrid_journey` 调用树静态
   不匹配（全仓该表查询点仅在 push/preference 服务，不在本链路）——该语句
   最可能来自同进程并发连接的轮询/推送路径（Q01 无 root 无法 py-spy 取栈，
   行级归因到此为止，如实登记为未决）；**它不改变结构定性**：无论挂哪个
   await，修前形态都是「重活 + 开放事务 + 行锁绑定在请求生命周期上」。
2. **用户级钉死放大器（实测）**：僵尸事务持 `agent_runs` 行锁 +
   每个挂死请求永久占住 1 条主池连接（pool 15+15）；同用户后续 hybrid
   请求实测排队 30s → 网关 503。重试不开新事务路径（幂等 resolve 原样回放
   僵尸 run，或带新幂等键再挂一次）——**一次挂死永久钉死该用户的 Hybrid**。

**排空的候选归因**（预定位的两候选，取证结论）：
- 「外层未提交事务持锁」→ **成立**（未提交的工具账本写 + `complete_agent_step`
  的 FOR UPDATE 滞留在请求事务）；
- 「工具账本写互等」→ **不成立**（账本幂等键按 run 派生 `hybrid_journey:prep:{run_id}`，
  重试必开新 run 新键，无同键互等路径；`agent_tool_calls` 无跨请求锁竞争面）。

## 2. 修复（三件套，按定性裁剪）

`backend/app/services/hybrid_journey_service.py`：

1. **重活出请求事务**：run 记录（`create_run`）+ RUNNING 迁移（`transition`）
   各自内部提交后，`await db.commit()` 显式收口请求事务；prep 真实检索改走
   executor **owned-session** 路径（`db_session=None` → `AsyncSessionLocal`
   独立会话，账本随工具收尾自提交）——prep 挂起最多烧掉工具自己那条连接，
   请求会话零开放事务、零行锁。
2. **显式超时 + FAILED 补偿**：prep 全程 `asyncio.wait_for(…,
   PREP_TOOL_TIMEOUT_SECONDS=20s)`（落在网关 30s 窗口内）；`TimeoutError` →
   wt392 F1 补偿路径（`_compensate_failed_start`，error_category=`prep_timeout`）
   → run 落 FAILED 释放幂等键 → 请求拿到可重试 `HybridJourneyStateError`。
   既有 prep 抛错/零命中补偿分支保留（error_category=`prep_failed`）。
3. **僵尸 run 启动自检回收**：幂等 resolve 命中 `_is_stale_prep_zombie`
   （RUNNING + current_stage=prep + 心跳/启动超 `PREP_ZOMBIE_AFTER_SECONDS=15min`
   ——Q01 僵尸形态的精确判据）时，补偿 FAILED（error_category=
   `prep_zombie_reclaimed`）并开新 attempt，不再原样回放；新鲜 RUNNING/prep
   仍幂等回放（双击/重开语义零回退）。全局 sweep（`recover_stale_runs`，6h
   阈值）保持兜底不变——启动自检把用户可见的解除从 6h 缩到下一次点击。

## 3. 验证

- 既有回归全绿：j06 四段链 + wt392 F1/F2/F3 全家族（含 40 passed 大家族跑与
  23 passed 终跑，见 run_manifest commands）。
- 新增回归钉 3 条（`backend/tests/unit/test_fix583_hybrid_start_hang.py`）：
  1. prep 慢/挂不阻塞启动请求超时窗（0.2s 超时 vs 3s 挂起 → FAILED 补偿 +
     prep 走 owned-session + **调用时刻请求会话 `in_transaction()==False`** +
     重试开新 attempt 成功）；
  2. 僵尸 RUNNING/prep 启动自检回收（超龄僵尸 → FAILED(prep_zombie_reclaimed)
     → 新 attempt 真实 prep）——「僵尸 run 不钉死重试」；
  3. 新鲜 RUNNING/prep 仍幂等回放（防过度回收的反向钉）。
- mutation 双向三连（全部还原后复绿）：
  - MUT-A 拔超时+还原请求会话执行 → 红（DID NOT RAISE）；
  - MUT-B 僵尸判定恒 False → 红（僵尸未被回收）；
  - MUT-C 判定无视新鲜度 → 红（幂等回放被破坏，run_id 不一致）。
- lint：ruff 全绿；black 对改动面收敛（test_j06 的历史非 black-120 格式保持
  原样，未扩大 footprint——HEAD 版本本就不被当前 black 接受，非本卡引入）。
