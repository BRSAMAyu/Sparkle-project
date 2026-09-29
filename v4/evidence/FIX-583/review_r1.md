# FIX-583 独立审查 R1（首审，未参与实现）

- 审查人：独立审查会话（非 fix-agent、非 Q01 会话）
- 日期：2026-09-29
- 对象：`agent/v4/f583` @ `8e315237`（树净起点）；修复面 `backend/app/services/hybrid_journey_service.py`（+93/-12）+ 新钉 `test_fix583_hybrid_start_hang.py`（3 测）+ `test_j06_hybrid_journey.py`（+3 行 fixture）
- 方法：主仓 `main:v4/evidence/V4-Q01/` 合并副本亲读 + 活栈只读 pg 快照 + diff 逐 hunk + MUT-A/B/C 亲杀 + 40 家族亲跑 + 两枚追加合成反例；全程对运行栈零写零清理零 kill，对产品码只临时变异即还原（逐次 `git status --porcelain` 空自证）。

## 裁决：PASS_WITH_CHALLENGES

修法定性正确、语义闭合、可失败验证齐备；两处证据表述需收敛（C1/C2），不阻塞 DONE。

---

## 逐靶裁决

### 靶1 定性复核 —— PASS（证据强于自报）

- **Q01 合并副本亲读**（`main:v4/evidence/V4-Q01/db/r5_part1_db_evidence.txt`）：run `57f4a41f` created `10:41:03.326108` / updated `10:41:03.344481`（**+18.37ms 冻结**）、`agent_tool_calls` 0 行、`hybrid_artifacts` 0 行、9 chunks 材料在库——与 verification.md §1.2 时间线逐位一致。
- **活栈只读快照（审查时点实测，比自报更强）**：
  - `agent_runs` 现存 **6 个 RUNNING/prep 僵尸**（Q01 三例 9ff03120/a77f9eb0/57f4a41f 原样在栈 + 3 例同构新增），冻结差 **+9.5~+20.8ms**；六者 `agent_tool_calls` 皆 0 行；`hybrid_journey_artifacts` 全表 0 行。
  - `pg_stat_activity`：6-7 个 `idle in transaction`（wait_event=**ClientRead**）会话；`pg_locks`：僵尸各持**本事务 transactionid ExclusiveLock（granted=t）**；6 个 `active` 会话以 **ShareLock 等待（granted=f）**，被阻塞语句=「`agent_runs … FOR UPDATE`」；`pg_blocking_pids` **1:1 配对**（8794←8864、12557←12598、7026←7007、12560←13683、11585←11580、6995←7025）。「idle in transaction=应用层持开放事务 await 无超时操作（非 DB 锁互等）」+「行锁钉死同用户重试」两定性均获活体证实。
  - **末语句分布**：6×`SELECT document_chunks…`（=prep 检索后、推进提交前挂起，与 18ms 冻结互证）+ 1×`SELECT user_push_opt_in…`（审查窗口内新鲜出现；栈同时服务其他会话验证流量，**无法归因 hybrid 链路**）——支持「末语句不作行级归因、结构定性承重」的处置。
  - 服务进程（uvicorn :8000、grpc_server.py）cwd=**wtQ01/backend（修前代码）**：活栈=未修复缺陷本体的干净运行面，修复未部署栈上（见 C4 复测前提）。

### 靶2 修法语义 —— PASS

- **① commit 边界**：`transition(RUNNING)` 内部提交后 `await db.commit()` 只收口 refresh 遗留的只读快照，无半状态风险；prep 失败（`NoMaterialError`/`HybridJourneyStateError`→`prep_failed`）与超时（`TimeoutError`→`prep_timeout`）两条补偿路径均经 `service.transition` 自带提交闭合，run 不会滞留 RUNNING（极端进程死亡残留由 15min 自检/6h sweep 兜底）。Python 3.11 下 `asyncio.wait_for` 抛内建 `TimeoutError`，`except TimeoutError` 前置且 `(HybridJourneyStateError, NoMaterialError)` 不相交——分支序正确。
- **② owned-session 账本**：`db_session=None` → `async with AsyncSessionLocal()` + `owns_session=True`，`_commit_if_owned` 收尾提交、失败回滚，取消时 `async with` 收口连接。幂等键 `hybrid_journey:prep:{run_id}` 按 run 派生：新 attempt=新 run_id=新键，**无键冲突/无毒化**；账本单写于 owned 会话、请求侧仅读（miss 时 `_ref_of("run",…)` 兜底），**无双写**；start 后段失败遗留的已提交账本行=诚实审计记录，非孤儿阻塞。`complete_agent_step`/`await_user_step` 亲读确认**纯 DB 操作**（FOR UPDATE→盖戳→事件→commit，无推送/HTTP await）——修复后 prep 后窗口仅剩 DB 往返，Q01 的 idle/ClientRead 挂死形态在该窗口结构性不可达。
- **③ 阈值与 race**：15min 对 prep 实测 3.8-4.3s、显式超时 20s 为 45-225 倍余量；误回收需 15min 级 DB 停滞，后果=原请求 ValueError + 重试成功，可接受。并发 resolve 双开：`(user_id, idempotency_key)` 唯一索引（`idx_agent_runs_idem`）兜底，补偿迁移经行锁串行（后至者 InvalidTransition 被 best-effort 捕获），attempt 键竞争输者 resolve 到胜者新 run 幂等回放——**无双 run、无键双写**。
- **wt392 零回退**：新鲜回放反向钉（钉3）+ wt392 家族全绿 + 断言零删改（test_j06 仅 +3 行 fixture 把 `AsyncSessionLocal` 指向测试引擎，属 owned-session 路径的必要装配对齐，非弱化）。

### 靶3 mutation 亲杀 —— PASS

- MUT-A（拔 `wait_for`+还原请求会话执行）：红 **DID NOT RAISE**（1 failed）；还原绿。
- MUT-B（`_is_stale_prep_zombie` 恒 False）：红 **`assert 'RUNNING' == 'FAILED'`**（1 failed）；还原绿。
- MUT-C（判定无视新鲜度 `return True`）：红 **幂等回放 run_id 不一致**（1 failed）；还原绿。
- 每次还原后 `git status --porcelain` 空 + 3 passed 复绿，逐次记录；审查终态树净。

### 靶4 回归亲跑 —— PASS

`cd backend && DATABASE_URL=sqlite:// SECRET_KEY=x python3.11 -m pytest` 六文件家族（j06 + wt392_r2v3 + fix583 + j06_migration + hybrid_run_steps + hybrid_run_steps_api）：**40 passed, 75.81s，exit 0**——与 run_manifest 口径一致。

### 靶5 新钉牙口 —— PASS（两枚追加合成反例）

- MUT-D（保留超时、仅还原请求会话执行）：钉1 红于 `db_session_is_none is True` 断言——会话归属断言独立咬合，不依赖 DID NOT RAISE 路径。
- MUT-E（保留 owned-session+超时、仅拔 `await db.commit()` 收口）：钉1 红于 `request_txn_open is False` 断言——`in_transaction()` 采样断言独立咬合。
- 三钉各自仅被对应变异打红（A→钉1、B→钉2、C→钉3），靶向无串扰。

### 靶6 未决面裁决 —— PASS（py-spy 挂账可接受）

- 结构定性（开放事务+无超时 await+行锁绑定请求生命周期）不被行级归因阻塞：修法针对**形态**而非行；活栈证据表明挂起形态为可取消的 suspended await（多僵尸并发、ClientRead、服务进程仍响应=事件循环未阻塞），落在 `wait_for` 可达域。limitations §2 对不可取消 await 的理论边界论证诚实且后果评估正确（最坏烧工具自有连接，不钉请求会话）。
- 但 limitations §1「三件套修复对任意挂点均成立」系**过度表述**——见挑战 C1。

### 靶7 证据五件套 —— PASS

`run_manifest.json`（命令/exit code/环境披露齐）+ `verification.md`（锁图定性）+ `limitations.md` + `summary.md` + `audit.md` 齐；ruff 三文件亲跑 All checks passed；台账 `DYNAMIC_ISSUES.md` FIX-583 行在。既有声明抽查：`_LLM_TIMEOUT_SECONDS=12.0`（judgment 段两处 wait_for）属实，numstat 与 footprint 基本吻合（C3 一处小误）。

---

## 挑战分级

- **C1（MEDIUM）**：`limitations.md` §1「三件套修复对任意挂点均成立」过度表述。prep 后完成窗口（artifacts INSERT → complete_agent_step → await_user_step → 收尾 commit）仍在请求事务内且无显式超时；若该窗口可挂死将复现持锁僵尸形态，且**活连接僵尸**的 15min 回收路径自身 FOR UPDATE 会被僵尸行锁阻塞——「下一次点击解除」仅对无锁僵尸（连接已亡）成立。缓解事实：complete/await_user_step 纯 DB 操作，其挂死形态为 active/Lock 而非 Q01 的 idle/ClientRead（该形态修复后在完成窗口结构性不可达）；6h sweep 与连接消亡后回收兜底。**要求**：表述收敛为「对 prep 窗口挂死形态成立；完成窗口依赖纯 DB await 的结构不可达论证 + 兜底」，并把「活连接僵尸回收被锁阻塞」登记为已知边界。
- **C2（LOW）**：30s 窗口归属错误。fix 注释/commit message/summary/verification 沿用「网关 30s 代理超时 503」；Q01 R1 勘误 LOW-2 + 本审亲验（`gateway/cmd/server/main.go` 明确不设 Read/WriteTimeout、无代理响应超时；真源=mobile `ApiTimeouts.defaultReceiveTimeout` 30s Dio receiveTimeout）。余量数学不受影响（20s<30s 任一口径成立，409 确定性失败仍落在客户端窗内），但勘误后立卡不应回传勘误前口径，四处措辞应更正。
- **C3（LOW）**：cosmetic——audit.md footprint 写 service `+96/-12`，numstat 实为 `+93/-12`；台账时间戳 `[2026-09-30 35:00]` 非法时刻。
- **C4（INFO，复测操作前提）**：当前栈两服务进程跑 wtQ01 修前代码；真端复测前须以修复代码重启进程（连接消亡→僵尸事务回滚→退为无锁形态→自检可收）。现存 6 僵尸中活连接者持行锁，未重启前修复代码的回收路径对其仍会被阻塞——这是复测环境准备项，非修复缺陷。

## 审查者追加验证记录（本审产生，零栈写入）

1. 活栈只读快照 ×3（pg_stat_activity / pg_locks / pg_blocking_pids / agent_runs 僵尸行 / agent_tool_calls 六 run 计数 / hybrid_journey_artifacts 全表计数）。
2. MUT-A/B/C 亲杀 + 还原复绿；MUT-D/MUT-E 合成反例 + 还原复绿；40 家族基线绿。
3. ruff 三文件亲跑绿；`gateway main.go` / `api_timeouts.dart` / `executor.py` owned-session / `agent_run_service` complete/await 亲读。

**结论：PASS_WITH_CHALLENGES——C1/C2 措辞收敛后可闭账；代码语义与验证面无需返工。**
