# WT793-F530 — V3-FIX-530 billing 消费循环 Redis 断连韧性壳

> 2026-09-28 ｜ worker wt793 ｜ worktree `Sparkle-sysrev/wt793-f530`（分支 `agent/node-b/wt793/f530`，base=main@7de5e46e，含 V3-FIX-498 闭账）
> 约束遵守：未重启/未触碰运行栈（运行中 engine 为旧代码，不受本修影响，滚动归主会话择机）；未 push；未改台账（闭账归主会话）。

## 1. 死因链（实录复核）

证据：`/tmp/uvicorn_day6b.log` :1306500 起（2026-09-28 03:02:55）。

```
redis.exceptions.ConnectionError: Error while reading from 127.0.0.1:6379 : (54, 'Connection reset by peer')
  ↑ blpop（billing_worker.py:94，BLPOP queue:billing timeout=1）
  ↑ BillingWorker.start() `except Exception: raise`（旧 :114-116）——致命上抛点
  ↑ main.py:797 lifespan 关停段 `await billing_worker_task`（仅 suppress CancelledError）
  ↑ lifespan __aexit__ 失败 → ERROR: Application shutdown failed. Exiting → 整 uvicorn 进程退出
```

Redis 容器同窗 18h healthy（台账行可查），死因=瞬时断连而非 Redis 宕机；进程死亡后 ~30 分钟 engine 缺位，03:31 心跳才发现。

## 2. 修法（唯一生产码文件 `backend/app/services/billing_worker.py`）

韧性壳包裹消费循环，**业务语义零改动**（blpop 消费/批量聚合/flush/逐条重试/死信逻辑逐行原样，仅移入 try 体内）：

1. **RedisError/ConnectionError/OSError 分支**：记 warning + 退避重试后 `continue`。退避序列 `REDIS_RECONNECT_BACKOFF_SECONDS=(1.0, 5.0, 30.0)` 按 1s/5s/30s 封顶（`_reconnect_delay` 纯函数，空序列为 0）；**成功消费一轮即归零**连续失败计数（下次断连重新从 1s 起步）。redis-py 客户端下轮命令自动重连，无需重建连接池（event_bus 消费循环同型先例 `app/core/event_bus.py:1365-1373`）。
2. **非预期异常兜底分支**：`logger.exception` 记录 + 退避后继续，循环永不向上抛致命异常（CancelledError 除外——Python 3.11 属 BaseException，上方显式 `raise` 放行保证正常关停）。
3. **旧 `except Exception: raise` 删除**——该 re-raise 正是实录死因链的致命上抛点，由内层兜底分支取代。
4. **finally 清理防上抛**：`redis.aclose()`/`engine.dispose()` 各自 try/except 记 warning——关停清理异常曾沿同一 lifespan 面传播，一并闭合。

`app/main.py` 零改动：worker 不再上抛后，`await billing_worker_task`（suppress CancelledError）天然安全；独立运行入口 `backend/scripts/start_billing_worker.py` 同路径受益，无需另改。

## 3. 红→绿实录

测试：`backend/tests/unit/test_billing_worker.py` 追加 4 测 + `_ConnectionResetFakeRedis`（复刻实录异常文本，前 N 次 blpop 抛 `redis.exceptions.ConnectionError: Error while reading from 127.0.0.1:6379 : (54, 'Connection reset by peer')` 后恢复；先例=同文件既有 `_FakeRedis`）。

命令：`cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v ./.venv/bin/python -m pytest tests/unit/test_billing_worker.py -q`

- **修前红（4 failed, 3 passed）**：
  - `test_start_survives_redis_connection_reset_v3_fix_530` — **task 携实录同款 ConnectionError 死亡**（`billing_worker.py:94 in start → raise self._error`，与 03:02 生产 traceback 逐字同型）——真红非恒真钉；
  - `test_reconnect_backoff_sequence_caps_at_max_v3_fix_530` — `_reconnect_delay`/`REDIS_RECONNECT_BACKOFF_SECONDS` API 缺失 AttributeError；
  - `test_reconnect_backoff_resets_after_successful_poll_v3_fix_530` / `test_unexpected_loop_exception_does_not_kill_worker_v3_fix_530` — task 带异常提前死亡。
- **修后绿（7 passed）**：3 次断连存活续消费、退避 1/5/30 封顶 + 成功归零、RuntimeError 非预期异常不杀进程，全部转绿；既有 B1/B2 三测零回退。

## 4. 触达面与静态面

- **billing 触达面**（grep 实证，非猜）：`tests/unit/test_billing_worker.py` + `tests/core/test_pool_governance_v3fix156.py` + `tests/test_llm_service_streaming.py` + `tests/unit/test_rd01_redeem_loop.py` → **36 passed, 1 skipped**（skip=pool governance 真 PG 探针需 postgres *_test 库，既有条件跳过与本修无关）。
- **ruff**：`ruff check` + `ruff format --check` 双文件 `app/services/billing_worker.py`、`tests/unit/test_billing_worker.py` 全过（3 处新增 `asyncio.TimeoutError` 别名 UP041 已按 --fix 收敛为 `TimeoutError`）。
- **mypy 冷缓存**（独立 MYPY_CACHE_DIR，global mypy）：
  - 触达面 A/B：`mypy app/services/billing_worker.py` 冷跑 base(main@7de5e46e)=31 errors : 分支=31 errors，行号归一化 `diff` **逐行为空（零新增）**；
  - 全量：分支冷跑 `mypy app` = **Found 55 errors in 51 files (checked 1387 source files)**——与主干预期基线（V3-FIX-498 集成收口实录「mypy 55 零漂移」）**精确同值**，零新增。

## 5. 进程面守护建议（提案，本卡不实现）

**现状**：`/tmp/engine_watchdog.sh` 已作临时守护在跑（30s 轮询 `/health` + gRPC :50051 tcp 探活；3 连败拉起 `make api-server`/`make grpc-server`；两次拉起间隔 ≥90s 防循环；升栈黑窗 07:25-08:15 只观察不干预）。属进程外临时脚本，重启机器即失。

**提案**（归 ops 卡，另行派发）：将「探活 + 3 连败 + 防抖 + 黑窗」语义正式化为 launchd（macOS 本机）/supervisord（Linux 交付环境）托管——KeepAlive+ThrottleInterval 原生防抖，日志轮转入 `/var/log` 级目录；同时考虑 uvicorn `--workers N` 多进程与 systemd 拉起链（gRPC 同理）。**注意**：本卡修的是「进程不该被单循环异常杀死」的内因，守护是外因兜底，两者互补缺一不可（内存泄漏/OOM/机器重启仍需外层拉起）。

## 6. 改动清单

- `backend/app/services/billing_worker.py`（唯一生产码：import RedisError、类常量 REDIS_RECONNECT_BACKOFF_SECONDS、`__init__` 两实例态、`_reconnect_delay` 静态助手、`start()` 韧性壳重写、finally 清理防上抛）
- `backend/tests/unit/test_billing_worker.py`（`_ConnectionResetFakeRedis` + 4 新测 + import time/redis.exceptions）
- `v3-output/WT793-F530/notes.md`（本文件）
