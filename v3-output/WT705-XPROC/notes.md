# WT705-XPROC · V3-FIX-193 收口笔记（2026-09-27）

- 分支：`agent/node-b/wt705/xproc`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt705-xproc`，base = main tip b6f0cacc）
- 修复 commit：`0cd043d1`；台账 commit：见本目录所在分支末笔
- 任务卡：V3-FIX-193（wt484 登记，wt695 日终盘点 A1 队列项）——`state_estimator` 防抖原子化只做了进程内 per-user `asyncio.Lock`（V3-FIX-14 ③），部署形态是 FastAPI 多 worker × Celery（`cognitive_stream_worker` 同调 `update_state`）：两进程各过各锁、各过 freshness check 即双 mint snapshot。危害有界（TELEMETRY_DERIVED_*_CAP + 窗口界 + 读侧取最新行），代价=冗余计算+重复行

## 1. 定位（先 find 后动手）

| 面 | 事实 |
|---|---|
| 锁实现 | `backend/app/services/state_estimator_service.py:34` `_DEBOUNCE_LOCKS: defaultdict[UUID, asyncio.Lock]`——模块级（`StateEstimatorService` 每请求新建实例，events.py:65/161/465 + cognitive_stream_worker.py:156，锁必须在模块级才有效）；文件头注释自认「Process-local scope: cross-process duplicates remain theoretically possible but are bounded harm」 |
| 仓内先例 | `backend/app/services/batch_worklane.py` `_try_claim`/`_release_claim`/`_get_store`（:328-383）：store 构造注入（测试替身）→ None 惰性取 `cache_service.redis` → `set(key,"1",nx=True,ex=ttl)`（True=抢到/NoneFalse=被占）→ TypeError 降级 get-then-set（无 nx/ex 的 fake）→ 其他异常 warn+fail-open；`backend/app/core/cache.py` 另有 `distributed_lock` 上下文管理器（token+Lua 原子释放）——本卡选 batch_worklane claim 形制：防抖是「恰一次重算」语义而非硬互斥，fail-open 语义与既有危害定价一致，且台账修法方向点名该先例 |
| Redis 可用性 | `cache_service.redis` 由 `init_redis()` 建立、失败置 None 并 warn——部署形态有 Redis 基建（make dev-up），None 是降级态而非常态 |

## 2. 修复 diff（commit 0cd043d1，2 文件 +383/−23）

| 文件 | 改动 |
|---|---|
| `backend/app/services/state_estimator_service.py` | ① `__init__` 增 `claim_store: Any \| None = None` 注入口（优先）+ `_get_claim_store()` 惰性取 `cache_service.redis`；② `_try_claim`：SET NX EX（键 `state_estimator:claim:<uid>`，TTL 10s 只须盖「取数→计算→提交」，持锁进程崩溃残留到期自清不卡死用户）——store None 返 True（Redis 缺席退化进程内锁，估算存活不依赖 Redis）；③ `_await_claim`：对端持 claim 时有界等待（预算 1.0s / 0.05s 轮询，模块常量可 monkeypatch）；④ `_release_claim`：delete 吞错；⑤ `update_state`：进程内 `async with _DEBOUNCE_LOCKS[user_id]` 保留为快速路径，其内先 claim——未抢到则有界等待，抢到后落入**既有 freshness 检查**（对端已提交→debounce 返回其快照，语义与进程内串行完全一致）；预算耗尽仍抢不到→放行（fail-open，与 batch_worklane 先例一致：「对端已提交」被 freshness 吸收，残余双写即 V3-FIX-11 已定价的有界危害）；`finally` 中仅 `claimed` 时释放——**未抢到不释放对端的 claim**；⑥ docstring/常量注释同步 V3-FIX-193 |
| `backend/tests/unit/test_state_estimator_cross_process_debounce.py` | 新增 5 测（见 §3） |

语义零迁移：debounce 窗口、cap、`force` 旁路 freshness（仍吃 claim 串行）、返回值（对端快照本体）全部不变；全量调用面（events API×3 + cognitive_stream_worker）零改动——构造签名只增可选参数。

## 3. 红→绿实录

测法：单事件循环扮演两「进程」——**换 `_DEBOUNCE_LOCKS` 表即换进程**（跨进程=互不可见的进程内锁表）+ 两进程共享一个 DB 会话替身（现实中只有一个 PostgreSQL；READ COMMITTED 语义：未提交行对另一进程不可见）+ A 停在 commit 闸门内时放 B 跑。共享跨进程存储 = FakeRedis 挂 `cache_service.redis`（生产查取路径；修前无人读它=无害 no-op，故红测走真实双写行为而非 TypeError）。

修前（真实输出）：

```
tests/unit/test_state_estimator_cross_process_debounce.py F..FF          [100%]
_________ test_cross_process_concurrent_updates_mint_only_one_snapshot _________
E   AssertionError: cross-process concurrent update_state minted 2 snapshots
    (FastAPI worker + Celery worker double write); the debounce must hold
    across processes via a shared claim, not only the process-local asyncio.Lock
E   assert 2 == 1
========================= 3 failed, 2 passed in 0.73s ==========================
```

- 行为红 1 个：**双写实锤**（A 未提交时 B 过双检直 mint，闸门放行后双双落库 → `committed=[a, b]`）
- 接口红 2 个：`_ESTIMATOR_CLAIM_WAIT_SECONDS` 常量与 `claim_store` 参数尚不存在（AttributeError）
- 修前即绿 2 个（规格钉子）：redis 缺席退化（=修前行为本体）、claim 释放（修前 vacuously 真）

修后：

```
tests/unit/test_state_estimator_cross_process_debounce.py .....          [100%]
============================== 5 passed in 0.88s ===============================
```

| 用例 | 钉什么 |
|---|---|
| `test_cross_process_concurrent_updates_mint_only_one_snapshot` | 主红→绿：恰 1 snapshot、恰 1 commit、败者收到胜者快照本体（debounce 语义保持） |
| `test_cross_process_claim_released_after_completion` | claim 键写后即清（不残留钉死用户） |
| `test_redis_absent_degrades_to_inprocess_debounce` | fail-open：Redis None 时行为=修前，存活不依赖 Redis |
| `test_claim_store_injection_overrides_cache_service` | 注入优先于单例；预算耗尽 fail-open mint 且**不碰对端 claim 键** |
| `test_typeerror_fallback_get_then_set_still_failopen` | 无 nx/ex 的 fake 客户端走 get-then-set 降级不崩 |

## 4. 既有面与门禁（真实运行）

```
tests/unit/test_state_estimator_cross_process_debounce.py .....   [ 19%]
tests/unit/test_state_estimator_service.py .                      [ 23%]
tests/unit/test_state_estimator_telemetry_bounds.py .........     [ 57%]
tests/services/test_event_idempotency_isolation.py .........      [ 92%]
tests/integration/test_event_pipeline_integration.py ss           [100%]
======================== 24 passed, 2 skipped in 3.98s =========================
```

- 2 skip = `SPARKLE_INTEGRATION not enabled`（既有环境门，非本次引入）；cognitive_stream_sentiment_intercept + state_aggregator_emotion_telemetry_filter 邻域另 9 passed
- ruff：`ruff check` 触达 2 文件 All checks passed；`ruff format` 一处行合拢后 2 文件 formatted
- mypy：`mypy app --ignore-missing-imports` 干净缓存逐行 diff（`error:` 行去行号排序比对）**对 main 为空=零新增**。表观 158→159 之谜：主仓 `.mypy_cache` 热缓存掩盖了未触碰文件 `app/aurora/policy_loader.py:9` 的 yaml stubs 报错，冷缓存跑主仓同为 159——非本次回涨
- gen/ 按先例主仓 `cp -RL` 不入库（.gitignore:246）；backend/.venv 软链主仓同款不入库（.gitignore:58）

## 5. 台账

`v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-193 置 `FIXED@0cd043d1`（状态列全实录：实测升级、修法、红绿数字、门禁、集成重编号注保留）。
`python3 scripts/devtools/ledger_union_merge.py --verify` → `verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法`（294 行 V3-FIX 行，裸管分布 {8: 294}）。

## 6. 残留与边界

- fail-open 下（Redis 故障 + 对端等待预算耗尽）残余双写仍可能——这是 V3-FIX-11 已定价的有界危害，本卡把「常态拓扑下防抖失效」收敛为「Redis 故障窗内的有界残留」，与 batch_worklane 幂等面同一取舍
- claim 用 plain delete 非 token+Lua 原子释放（cache.distributed_lock 形制）：极端下 A 的 claim 过期→B 抢到→A 迟到 delete 掉 B 的 claim→第三进程可提前抢入→双写。该链需要 TTL 10s 内计算+提交仍未完成这一前提，落入有界危害覆盖域；如需硬互斥再升级 token 形制
- DB 级 INSERT 守卫（修法方向备选）未采用：需 schema/迁移介入，与「最小修边界」及先例一致性不符
