# BATCH-CAP — MiniMax 车道故障级联 + 队列饱和丢任务修复（收工报告）

- 卡号：BATCH-CAP（北极星全旅程战役 · B×C 纵队 · batch 车道容量线，PROD-LOG2 二轮巡检最重项）
- worktree：`wt211`（基线 `4061644e`，零 commit 零 push，交付物 = 本报告 + `changes.patch`）
- 缺陷依据：主仓 `v3-output/PROD-LOG2/REPORT.md` ②-2
- 测试：**新增 16 用例全绿 + 定向回归 147 用例全绿（0 新增失败）**，全部 `--timeout` + sqlite env

---

## ① 故障链复盘 + 容量算术

### 1.1 代码面结构（读码结论）

MiniMax M3 上有**两条独立进入路径、三个进程副本**：

| 进入路径 | 并发闸 | 排队语义 | 进程 |
|---|---|---|---|
| 通用 LLM 路由（`llm_service` / batch_worklane / 长程预测本地兜底）→ `llm_concurrency` MINIMAX 池 | `MINIMAX_MAX_CONCURRENCY=8` 槽 | **排队等槽，原 45s 超时** | 引擎 + 每个 celery worker 各一份 |
| 直连车道 `minimax_provider.analyze()`（error_book） | 同值 semaphore(8) | **快速拒绝不排队** | 引擎 |

关键事实：`llm_concurrency` 是 asyncio 原语——**每进程各一份 8 槽池，不是全局 8 槽**。

### 1.2 故障链（对齐 PROD-LOG2 实测）

```
batch 车道切 MiniMax M3 + 双 batch worker 上量
  → 需求速率 > 供给速率（见 1.3 算术）
  → celery glm_batch 队列恒顶 cap=200（LLEN 饱和）
      → 103 次派发被背压丢弃（逐条 WARNING，无聚合告警）→ 长程预测静默丢失
  → 引擎内 MINIMAX 池饱和，waiter 排队
      → 45s 等槽到点，asyncio.wait_for 抛【空 str 的 TimeoutError】
      → llm_service.py:731 不接 TimeoutError → 裸抛进 fallback
      → _detect_fallback_reason 只做字符串匹配：str(e)="" 匹配不到任何分支
          → 误判 Non-retryable →【23 条空消息 error（fallback.py:491 + llm_service.py:800）】
          → 45s 白等后连 fallback 都不进，任务硬失败
      → 另一部分经 providers.py 转成 503 → 误计模型失败
          → 熔断 OPEN ×5（failures:9）+ unhealthy ×8 连败
```

### 1.3 容量算术

- **配额（供给）**：MiniMax token plan 并发硬上限 = 8（代码与 settings 同一口径注释）。
- **超订（真实在途上限）**：引擎内双池相加 8+8=16（llm_concurrency 池 + minimax_provider 直连池独立计数）+ 2 个 celery worker 进程各 8 = **峰值 32 并发在途 vs 配额 8 → 超订 4×**。
- **吞吐**：M3 为推理模型，批任务（长程预测/反思/质检）带思维链单调用常 15–60s；以 hold=30s 计，供给 ≈ 8/30 ≈ **0.27 tasks/s ≈ 16 tasks/min**。88 分钟窗口内 103 丢弃 + 队列恒 200 + 34 池超时表明需求持续 > 供给 → 排队深度线性上涨 → 先顶穿 celery 队列 cap（丢弃），后打穿池内 45s 等待（超时）。
- **45s 为什么是错量级**：45s 是**等槽超时**，与请求尾延迟无关。等槽期望 ≈ (排队深度/8)×hold；饱和态深度无界 → **任何固定超时必被打穿**。且本池全部 in-engine 消费者（batch_worklane 3 次重试+死信、长程预测锁释放重投、capsule fallback）都有降级面——排队 45s 不改变结局，只把拥堵传染给事件循环（直连车道模块注释自己就写明了这条设计原则）。实测 p95=2.2s（聊天车道）说明正常占槽是短尾，45s 给错了三个量级。

### 1.4 根因裁决（答卡面问题）

1. **配置错位为主**：不是"8 太小"，而是 ①池没按进程收敛（每 celery worker 进程复制一份 8 槽）；②引擎内双池相加超配额 2×；③等槽超时 45s 与 fast-fail 车道语义割裂。
2. **排队策略问题为辅**：饱和是常态而非瞬态，"长任务占坑 + 无界排队等槽"必然打穿固定超时。
3. **丢弃不可行动**：cap=200 丢弃在 `queue_backpressure._enforce_from_decision`（自定义 choke point，非 celery 原生），有逐条 WARNING + Prometheus 计数，但**无聚合告警**——103 条单条在噪音里等于静默。

---

## ② 修法裁决（每项对齐实测数字）

| # | 裁决 | 对齐的实测数字 | 理由 |
|---|---|---|---|
| 1 | MINIMAX 池等槽超时 **45s → 5s**（settings 化 `MINIMAX_QUEUE_TIMEOUT_SECONDS`，env 可调） | 34 次 45s 超时；p95=2.2s | fast-fail 与直连车道同语义；5s ≈ 2×p95，覆盖正常瞬态排队；饱和时立即失败走既有重试/降级，不再白等 45s 后硬失败 |
| 2 | 信号量超时**源头带诊断消息**（`_acquire_slot` 把 wait_for 的空 TimeoutError 统一转带池快照 limit/active/waiting 的消息） | 23 条空消息 error | 空消息在出生地消灭；池水位快照使"排队超时"与"请求超时"在日志上可区分 |
| 3 | fallback **TimeoutError 类型先行归类 TIMEOUT**（可重试） | 23 条 Non-retryable 空消息 | 45s 等待后必须进 fallback 链而不是硬失败；类型判断对空 str 免疫 |
| 4 | 两站空消息兜底 `str(e).strip() or type(e).__name__` + `logger.opt(exception=True)`（照 wt182 reviewer 先例 + EXC-TRACEBACK 建议） | llm_service.py:800 ×23 + fallback.py:491 ×23 不可诊断 | 保底类型名 + traceback 附加，下一轮巡检可归因 |
| 5 | 队列丢弃升级 **饱和 episode 语义**：首条 ERROR（SATURATION START）+ 每 `QUEUE_BACKPRESSURE_SATURATION_LOG_INTERVAL_SECONDS`（默认 30s）一条 ERROR 汇总（episode 时长+累计丢弃数）+ 恢复 INFO；逐条 WARNING 保留作审计 | 103 条不可行动的单条 WARNING | 丢弃可观测为**速率与时长**（PROD-LOG2 修复思路 b 原文）；不选提高 cap——提高 cap 只会加长陈化延迟，长程预测过期即废 |
| 6 | **可重投**不新增自动重入队：保留既有「丢弃→False→调用方锁释放/下次触发重投 + celery 执行侧 max_retries=2/3」链路，由恢复告警闭环观测 | 长程预测 refresh 锁 300s TTL 自动过期重试 | 往满队列里自动重投只会二次丢弃+翻倍日志噪音；现有重投语义本就存在且诚实 |
| 7 | **不改** MINIMAX_MAX_CONCURRENCY=8 默认值，**不合并**双池 | 配额=8（token plan 口径，零凭据无法实测更多） | 上限对齐配额的方向是**降每进程占用**而非升并发：池已 env 可调；跨进程/跨池收敛需 Redis 分布式信号量，属更大改动面，本卡在报告中申报而非擅动（见 ⑤ 主会话步骤 3） |

---

## ③ 实现清单

| 文件 | 改动 |
|---|---|
| `backend/app/config/settings.py` | +`MINIMAX_QUEUE_TIMEOUT_SECONDS: float = 5.0`；+`QUEUE_BACKPRESSURE_SATURATION_LOG_INTERVAL_SECONDS: float = 30.0`（各带裁决注释） |
| `backend/app/services/llm/concurrency.py` | MINIMAX 池 queue_timeout 接 settings（45→5s）；`_acquire_slot` 捕获 wait_for 空.TimeoutError → 转 `_slot_timeout_message()`（含 provider/limit/active/waiting 快照） |
| `backend/app/services/llm/fallback.py` | `_detect_fallback_reason` 顶部加 `isinstance(error, TimeoutError) → TIMEOUT`（py3.11+ 覆盖 asyncio.TimeoutError）；:491 空消息兜底 + exception 附加 |
| `backend/app/services/llm_service.py` | :800 空消息兜底 + exception 附加 |
| `backend/app/core/queue_backpressure.py` | 饱和 episode 状态（`_SATURATION_STATE` + threading.Lock，async/sync 共用）；`_record_saturation_drop`/`_record_saturation_recovery`；`_depth_decision` 恢复 INFO；`_enforce_from_decision` START/ONGOING ERROR + 逐条 WARNING 保留；探测失败不清 episode（不误报恢复） |
| `backend/tests/unit/test_batch_capacity_fault_chain.py` | **新增 16 用例**（见 ④ 前的验证段） |

### 验证（全部 python3.11 + `--timeout` + sqlite env + SECRET_KEY 测试假值）

| 套件 | 结果 |
|---|---|
| 新增 `test_batch_capacity_fault_chain.py` | **16 passed**（超时消息非空含池快照 / wait_for 到点路径可诊断 / settings 对齐 / 路由名→MINIMAX 池映射钉 / 4 任务抢 2 槽分批成功无唤醒丢失 / 饱和快速失败 / 释放精确唤醒 / 空 TimeoutError 归类 TIMEOUT / 端到端超时→fallback 成功 / Non-retryable 空消息日志含类型名无悬空冒号 / 饱和 START→RECOVERED / 周期汇总 drops_in_episode=3 / 逐条计数 / sync 孪生同语义 / 探测失败不误报恢复） |
| O-07 既有：`test_o07_queue_backpressure.py` + `test_o07_p2dispatch_choke_wiring.py` | **29 passed**（丢弃策略零回归） |
| B-MODEL-SWITCH 守卫面：`test_batch_llm_provider_switch.py` + `test_minimax_batch_routing.py` + `test_minimax_provider.py` | **59 passed，零新增失败** |
| batch_worklane + fallback 序：`test_batch_worklane.py` + `test_llm_same_tier_fallback.py` + `test_llm_tier_fallback_order.py` + `test_llm_timeout_fallback.py` | **48 passed** |
| glm_batch 自适应/去重：`test_glm_batch_adaptive.py` + `test_node_sector_backfill_dedup.py` | **11 passed** |
| ruff | 改动文件全清（余 1 条 C408 在 llm_service.py:1696 为存量，非本卡 hunk，未动）；black 已过 |

---

## ④ 冲突面声明

本卡改动文件：`settings.py` / `llm/concurrency.py` / `llm/fallback.py` / `llm_service.py` / `queue_backpressure.py` / 新增 1 测试文件。

| 兄弟卡 | 实测改动面（只读探查） | 与本卡关系 |
|---|---|---|
| wt207 | `galaxy_bootstrap_service.py` + mobile 四屏两测 | **无交集** |
| wt209 | `backend/app/gen`（生成物）+ `test_goal_backfill_boundary.py` | **无交集** |
| wt210 | 工作树当前干净（同基线 4061644e）；按卡面其将动 **settings.py 小米模型名（:476-477 XIAOMI 区块）+ llm_router 注册（fast_models 链）** | **同文件不同 hunk**：本卡 settings 改动落在 ①:443-450 队列背压区块（+4 行）与 ②:499-508 MiniMax 区块（+4 行），距小米区块约 30 行、无行重叠；本卡**不碰 llm_router**。`git apply --3way` 可干净合并；若 apply 后小米块行号漂移属预期 |
| wt206 | 本 sysrev 目录下不存在该 worktree（可能已合入或未派生） | 无法实测；本卡五文件均非高频共改面（concurrency/fallback/queue_backpressure 上一次实质改动分别是 MM-M3/E-07/O-07 轮），若 wt206 也动 llm_service 日志面请主会话合入时先 apply 本卡或后到者 rebase |

---

## ⑤ 收工核查 + 主会话压测步骤

### 收工核查（已执行）

- [x] 零 commit 零 push；工作树 = 5 modified + 1 untracked 测试文件 + v3-output/BATCH-CAP/{REPORT.md, changes.patch}
- [x] `changes.patch` 含全部 6 个 diff（`git diff` + `--no-index` 补新文件，676 行）
- [x] 零凭据（测试用 SECRET_KEY 为假值 `test-only-not-a-secret-batchcap`，不入库）
- [x] 未动主仓、未动兄弟 worktree（仅只读 `git status` 探查）
- [x] /tmp 零本卡产物；未起模拟器/浏览器/gradle；无独立端口进程残留
- [x] worktree 内 `__pycache__`/`.pytest_cache` 为 pytest 运行副产物（不入库、不属交付物，见下方清理）
- [x] 磁盘/内存：本卡全程 LIGHT（pytest 单进程串行定向跑，无 HEAVY）

### 主会话压测步骤（本卡按卡面**未真起双 worker 压测**，建议合入后执行）

1. **部署面**：合入后 `make sync-db`（无迁移，本卡零迁移）→ 重启引擎 + 确认 2 个 celery batch worker 在跑（`BATCH_LLM_PROVIDER=minimax`、`MINIMAX_API_KEY` 已配的活栈）。
2. **消息面冒烟**：触发一条长程预测（probe 账户行为即可）→ 确认任务落 glm_batch 执行成功；日志出现 `LLMConcurrencyManager initialized`（无异常）。
3. **容量对齐确认（需主会话权限）**：向 MiniMax 侧核实 token plan 真实并发上限；若非 8，改 `.env` `MINIMAX_MAX_CONCURRENCY=<实测值>` 并**按进程分摊**（如引擎 4 + 每 worker 2），重启生效。若决定收敛双池/跨进程池（Redis 信号量），另开卡（涉及 minimax_provider 与 llm_concurrency 合并，改动面大于本卡）。
4. **双 worker 压测脚本（LIGHT 级，非 HEAVY）**：以 2×并发向 glm_batch 投 N=50 条假任务（mock LLM 或 sleep 5s 的 stub 任务），观察：
   - 队列深度贴 cap 时日志出现 `SATURATION START`（ERROR），停止投喂后出现 `SATURATION RECOVERED`（INFO，含 episode 时长+drops）；
   - Prometheus `sparkle_queue_backpressure_drops_total{queue="glm_batch"}` 增量 = 丢弃数 = episode 汇总数；
   - 人为把 `MINIMAX_MAX_CONCURRENCY` 调 1 + 慢任务制造池饱和 → 应看到 5s 内 `Timeout acquiring semaphore`/`is busy: no free concurrency slot within 5.0s (limit=1, active=1, waiting=...)` 带快照消息，**且不再出现空 `LLM Chat Error:` / 空 `Non-retryable error:`**；
   - 若 MiniMax 侧真实 429 → `_detect_fallback_reason` 照常归 RATE_LIMIT；空 TimeoutError → 归 TIMEOUT 走 fallback 链（对照修复前 45s 后直接硬失败）。
5. **观察窗口验收**：下一个 PROD-LOG 轮应看到——空消息 error 0 条；batch 车道 ERROR 由 57 条级降至个位；队列丢弃以 SATURATION 汇总行呈现（88 分钟 103 条 WARNING → ≤ 2×时长/30s + 2 条）。

### 遗留申报（本卡不修，已对齐卡面边界）

- 跨进程/跨池的 MiniMax 配额收敛（Redis 分布式信号量）——见主会话步骤 3；
- `minimax_provider` 直连池与 llm_concurrency 池相加超订（当前直连池仅 error_book 一个消费者，实际风险窗口小）；
- `asyncio loop exception: Task exception was never retrieved` ×11（PROD-LOG2 ⑧ 观察项，或与 fire-and-forget 本地兜底相关，属 predictive_service 域）。
