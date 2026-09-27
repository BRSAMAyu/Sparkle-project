# WT736 — V3-FIX-418 信念融合跨进程丢更新收口（P3，复核 CONFIRMED@wt719）

- 分支：`agent/node-b/wt736/fusion418`（base = main@73e05585）
- 修复 commit：`a0d5360e`（fusion_engine.py + 新正式测试）；台账/本 notes 为后续 docs commit
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt736-fusion418`（`backend/app/gen` 按先例主仓 `cp -RL`，不入库）

## 修法（复刻先例，不发明）

`FusionEngine.update_user_state` 原防护 = 模块级 per-user `asyncio.Lock`（进程内）+ Redis GET→fuse→SETEX 读改写；调用面天然跨进程（chat 信号落任意 uvicorn worker、TaskEventConsumer 每 worker lifespan 各起一个 main.py:284、k8s HPA minReplicas=1/maxReplicas=5 消费组分发跨 pod），后写者整块覆盖前写者融合结果。

修法沿 V3-FIX-193/wt705 先例（`git show 10525df2`，最终源头 `batch_worklane._try_claim`，batch_worklane.py:363）：

- 进程内锁保留为快速路径；锁内取 per-user Redis SET NX EX claim：`aurora:belief_state_claim:v1:<uid>`，TTL 10s 盖住读→融→写（global + scoped 两次落盘），持锁进程崩溃残留键到期自清
- 对端持 claim → 有界等待（1.0s 预算 / 0.05s 轮询，`_FUSION_CLAIM_WAIT_SECONDS` / `_FUSION_CLAIM_RETRY_INTERVAL_SECONDS`）；抢到后走既有 load_state 重读，拿到对端已融合状态，本次证据在其上**追加**而非覆盖
- 预算耗尽仍抢不到 → fail-open 放行（batch_worklane/wt705 同款）：残留后写覆盖 = 已定价有界危害（TTL 7d、append_trace 另有账），融合写路径存活不依赖 Redis
- claim 存储即传入的 `redis`（生产各调用方共享 `cache_service.redis`；wt705 的注入/lazy-cache 形态在此不适用——redis 本就是方法参数，测试注入点不变）
- TypeError 降级 get-then-set（无 nx/ex 的 fake 客户端）；其他存储异常 warning + 放行；未抢到不释放对端 claim；释放走 `finally`（仅本方持有时）

## 红先行实录

正式测试 `backend/tests/unit/test_fusion_engine_cross_process_claim.py` 固化 wt713 repro 场景（单事件循环双「进程」：换 `_user_state_locks` 表=换进程，两进程共享同一 fake redis；fake 每个 op `sleep(0)` 让协程交错，`arm_save_gate` 后第一次 `setex` 停车=A 停在已读空态未写回的读改写窗口正中）：

- 修前（base 73e05585）：`test_cross_process_concurrent_updates_do_not_lose_evidence` RED ——
  `AssertionError: cross-process concurrent update_user_state lost evidence (last_evidence_ids=['ev-a'])`，B 的 ev-b 被覆盖丢失，与 `v3-output/WT713-HUNT1/repro_fusion_cross_process.py` 猎缺实录一致
- 修后：4/4 绿
  1. 跨进程并发不丢证据（红→绿核心）
  2. claim 写后释放（claim 键清空，不钉用户）
  3. claim 存储故障 fail-open（`set` 整体 raise RuntimeError，update 照常完成、证据在）
  4. TypeError 降级 get-then-set（无 nx/ex fake + 对端预持 claim：预算耗尽放行且**不删对端 claim 键**）

调试记录：fake 的闸门第一版 `release_save_gate` 判 `self._save_gate is not None`，而闸门事件已被 setex 消费进局部变量 → 永不释放（修前红跑成 TimeoutError 假形）。改为 `self._parked_gate` 单独跟踪停车中的事件后，RED 回到真实丢更新断言形。

## 测试面（find 先行，全绿零回退）

- 新测试：4/4 绿（见上）
- fusion/belief/contract：`test_belief_fusion_engine` + `test_belief_observation_models` + `test_belief_trace_inspector` + `test_belief_recovery_simulator` + `test_event_registry_contract` = 61 绿
- 调用面（五个 update_user_state 调用点族）：`test_chat_signal_collector`×2 + `test_consumer_exception_propagation`（services/）+ `test_s04_community_feedback_evidence`（tests/ 根）+ `test_s04_community_outcome_evidence`（api/）+ `test_s03_surface_convergence`（api/）+ `test_event_ack2_reliability` + `test_event_bus_reliability` + `test_spine_event_bridge` = 66 绿
- cognitive 面：`test_cognitive_api` + `test_cognitive_loop` = 8 绿 + 1 skip（`test_belief_shadow_real_redis` 环境门）
- 真 redis（docker `sparkle_redis`，凭据自主仓 backend/.env 运行时注入，未入库）：
  - `SPARKLE_RUN_REAL_REDIS_TESTS=1` 下 `test_belief_shadow_real_redis` 1 绿（collector→extractor→fusion→真 redis 全链）
  - 一次性探针（已删）：序贯两次 `update_user_state` → claim 键释放（get=None）→ 重抢成功 → ev-1/ev-2 并存，PROBE PASS

## 门禁

- ruff check：触达 2 文件（fusion_engine.py + 新测试）全过
- ruff format：新测试文件已 format 干净；fusion_engine.py 的 `format --diff` 与 main 逐 hunk 同型（既有漂移，本批**零新增**——try 块加深缩进反而消解 main 在 :509 的 scoped load_state 折行 hunk）。此漂移登记为 V3-FIX-455（P4），不在行为批内顺手重排
- mypy：干净缓存全量 `mypy app` —— 本分支 133 = main 133（同命令同环境），逐行 error 集 diff 为空；fusion_engine.py 零 error。注：任务口径「合并态 132」与今日 main 干净缓存实测 133 差 1 系缓存/环境抖动（wt705 同款披露），以「与 main 逐行 diff 为空」为准零回涨

## 披露（不隐藏）

1. **wt713 原 repro 直跑修后代码仍 RED，属预期**：repro 的交错是 `await task_b` 之后才 `set` 放行 A 的闸门——修后 B 的 1s claim 等待预算必然耗尽 → fail-open 放行 → 后写覆盖（正是本修定价的有界危害）。正式测试的交错（B 入等后 0.05s 放行闸门）才落在修法生效面。repro 保留原样作猎缺证据，不回改
2. mypy 133 vs 任务口径 132：见门禁段，逐行 diff 空为准
3. 分支基线 73e05585 早于 main 现 tip（wt732 的 V3-FIX-417/447 台账 commit cbb92145 在我建 worktree 后落 main）；本批台账改动基于基线追加 418 FIXED + 455 新行，455 编号先 grep 空闲（基线与 main 现 tip 均无 455/456），集成合并时与 447/449 行的追加区按行合并即可

## 台账

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：V3-FIX-418 → `FIXED@a0d5360e`（Status 格内追加，OPEN/CONFIRMED 历文保留）；新增 V3-FIX-455（P4，OPEN，ruff format 既有漂移 + ruff 未锁版口径分叉）
- `scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：**verify 通过，零 FAIL**（工具口径 315 行 V3-FIX 行、8 裸管形态合法、ID 无重号、状态枚举合法；grep 行首口径 313→314，本批净增 1 行=455）
