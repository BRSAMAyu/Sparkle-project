# DIST-SEMAPHORE — 跨进程 MiniMax 并发池（Redis 分布式 RPM 预算闸）+ 配额注释校正（收工报告）

- 卡号：DIST-SEMAPHORE（北极星全旅程战役 · B 纵队 · LLM 并发线）
- worktree：`wt214`（基线 `5437c9c6`，**零 commit 零 push**，交付物 = 本报告 + `changes.patch`）
- 依据：主仓 `v3-output/BATCH-CAP/REPORT.md` 裁决 6/7 与 §⑤ 步骤 3（登记「跨进程收敛需 Redis，超卡面」）；`v3-output/MINIMAX-QUOTA/REPORT.md`（真约束 = **账户级 RPM**：免费 20 / 充值 200，主+子账号共享，无文档化并发数；§4.1 三处注释口径债）
- 测试：**新增 19 用例全绿 + 守卫面回归 75 用例全绿（零新增失败）**，全部 `--timeout` + SECRET_KEY 假值

---

## ① 设计（答 BATCH-CAP 登记的「Redis 分布式信号量」，粒度对齐官方 RPM 口径）

### 核心裁决：按 RPM 而非并发做全局面

MINIMAX-QUOTA 已核实：官方按**账户**限的是每分钟**发起数**（RPM），不是在途并发数。因此本卡不做「跨进程信号量」（在途语义），做**跨进程发起预算桶**——三进程（引擎 + glm_batch worker 容器内 2 个 prefork 子进程）经 Redis 共享一份「每分钟最多 N 次发起」预算：

```
MINIMAX_RPM_BUDGET > 0 时：
  acquire(minimax) ──→ ① Redis 固定窗口 RPM 桶（全局面，60s 窗口，容量=N/分钟）
                          │ 窗口满 → 等到窗口滚动或 timeout 到点（先到者胜）
                          │ Redis 缺席/出错 → 诚实降级放行 + 限频告警
                          ▼
                       ② 本地 asyncio 并发池（第二道防线，MINIMAX_MAX_CONCURRENCY 槽，
                          BATCH-CAP 的 5s fast-fail 契约不变，等待预算=剩余 deadline）
                          ▼
                       发起请求（此刻配额已被真实消费）

MINIMAX_RPM_BUDGET = 0（默认，回滚位）：
  acquire(minimax) ──→ ② 本地池，行为与本卡之前逐字节一致（兼容 BATCH-CAP env 分摊路径）
非 minimax provider：不触达 ①，零变化。
```

### 桶参数与机制（`minimax_rpm_gate.py`）

| 参数 | 值 | 理由 |
|---|---|---|
| 窗口 | 60s 固定窗口，key=`sparkle:llm:minimax:rpm:{window}` | 与官方「每分钟每账户 N 发起」同构；窗口滚动即 refill |
| 原子性 | 事务 pipeline（MULTI/EXEC）：`INCR` + `EXPIRE` 同生共死 | 不依赖 Lua（fakeredis 测试基建无 lupa 也可复验）；Redis 单线程保跨进程原子 |
| 超预算方 | `DECR` 回滚自己的 INCR 后等待 | 不占而退；竞态下最坏「保守误拒」，**永不超发**（对保护性预算是诚实方向） |
| 等待语义 | 睡 `min(窗口剩余, 剩余 deadline, 1s)` 后重读窗口 | 跨窗口自适应；timeout 与 BATCH-CAP 的 queue_timeout 同源 |
| 超时消息 | 非空 TimeoutError，含 `budget/窗口用量/窗口号` 快照 | 对齐 BATCH-CAP 空消息修复；消费端照既有 fallback 链归类 TIMEOUT 可重试 |

### 「TTL 防死锁」怎么成立（卡面 lease 问题的 RPM 答案）

- 信号量的死锁面 = 持有者崩溃后坑位永不释放。**RPM 桶没有持有者**：令牌在**发起时**消费、无释放语义（请求一旦发出，账户配额已被 API 计）——崩溃进程不可能悬空占坑，消费即花费；
- 状态面残留由 TTL 兜底：窗口 key 带 **2×窗口（120s）TTL**，到期自动回收。最坏崩溃残留（INCR 落地、EXPIRE 未及）在 MULTI/EXEC 内已不可达；即便人为造成无 TTL key，下一次任意 acquire 的 EXPIRE 会重新武装（自愈路径有专测）；
- 结论：无需 lease/续租机制即满足「持有者崩溃自动回收」，且比 lease 更简单（无续租定时器、无时钟漂移面）。

### 诚实降级链

Redis 缺席（`cache_service.redis is None`）或命令异常 → **放行**（回退本地池第二道防线）+ WARNING 限频告警（300s 冷却，防多进程日志风暴），告警明示「budget NOT enforced across processes」；Redis 恢复后自动回到分布式预算（不粘滞，有专测）。

---

## ② 实现清单

| 文件 | 改动 |
|---|---|
| `backend/app/services/llm/minimax_rpm_gate.py` | **新增**：`MinimaxRpmGate`（桶实现：固定窗口 INCR/DECR + TTL + 事务 pipeline + 降级链 + 观测计数）；`get_minimax_rpm_gate()`（settings 判读单例，budget≤0 → None）；构造器留 `redis_getter` DI 缝供单测注入独立连接模拟多进程 |
| `backend/app/services/llm/concurrency.py` | `_ConcurrencyLimiter.__aenter__` 前置挂钩：仅 `ProviderType.MINIMAX` 且 gate 非 None 时先过 RPM 桶，**剩余 deadline 交给本地池**（总等待 ≤ queue_timeout，不放宽 BATCH-CAP fast-fail）；gate 为 None 路径逐字节等价原逻辑 |
| `backend/app/config/settings.py` | +`MINIMAX_RPM_BUDGET: int = 0`（0=禁用回滚位，env 路径兼容 BATCH-CAP）；校验器钳制负值→0 |
| `backend/app/services/llm/minimax_provider.py` | P3 注释校正：并发语义段改写为官方 RPM/TPM 真口径（并注明本直连 lane 不经 RPM 桶路径） |
| `backend/app/config/settings.py`（同上文件） | P3 注释校正：MiniMax 通道块「并发钳制 = token plan 并发上限」→ 官方按账户限 RPM/TPM 口径 |
| `backend/app/services/llm/concurrency.py`（同上文件） | P3 注释校正：MINIMAX 池块「token plan 并发硬上限」→ 官方 RPM/TPM 口径 + 指向 MINIMAX_RPM_BUDGET |
| `backend/.env.example` | 登记 `MINIMAX_RPM_BUDGET=0` + 档位说明一行（MINIMAX-QUOTA §4.1 申报项，主会话旋钮可见） |
| `backend/tests/unit/test_minimax_rpm_gate.py` | **新增 19 用例**（见 ④） |

---

## ③ 验证（全部 python3.11 + `--timeout` + SECRET_KEY 测试假值）

### 新增 `test_minimax_rpm_gate.py`（19 passed，≈1s）

| 卡面验收 | 用例 |
|---|---|
| 多"进程"恰 N/分钟窗口 | 双 gate 实例 × **独立 fakeredis 连接**（共享 FakeServer）× 12 并发 claimant → 恰 3 成功 9 超时；窗口计数回落恰 3（DECR 不吞预算）；窗口滚动后预算 refill；超时消息非空含 budget/窗口用量快照 |
| 持有者崩溃/TTL 回收 | 窗口 key 恒带 TTL（0<TTL≤120）；EXPIRE 丢失（persist 模拟最坏残留）→ 下次 acquire 自愈重武装；崩溃进程不悬空占坑、新窗口不受旧窗口影响；budget≤0 拒绝构造 |
| Redis 缺席降级 | redis=None → 放行+降级计数；redis 命令异常 → 降级+**限频告警恰 1 条**（含 NOT enforced）；恢复后自动回到预算执行（不粘滞） |
| 非 minimax 零变化 | 预算启用下 zhipu acquire **零 Redis 接触**；默认 budget=0 时 minimax acquire 零 Redis 痕（禁用位=回滚兼容）；gate 通过后剩余预算交给本地池（spy 钉 `0<timeout≤queue_timeout`）；端到端预算 1 时第 2 个 acquire 超时且消息指 RPM 而非槽位；单例随 settings 改值重建/禁用 |

### 守卫面回归（零新增失败）

| 套件 | 结果 |
|---|---|
| BATCH-CAP 面：`test_batch_capacity_fault_chain.py` | 16 passed |
| B-MODEL-SWITCH 面：`test_batch_llm_provider_switch.py` + `test_minimax_batch_routing.py` + `test_minimax_provider.py` | 59 passed（含钉死 `MINIMAX_MAX_CONCURRENCY==8` 的 `test_settings_expose_minimax_lane_config`——本卡未动该默认值，不受 MINIMAX-QUOTA §4.3 坑位影响；`MINIMAX_RPM_BUDGET` 默认 0 同理安全） |
| lint | ruff + black 改动文件全清 |

---

## ④ 冲突面声明

本卡改动：`settings.py` / `llm/concurrency.py` / `llm/minimax_provider.py` / `.env.example` / 新增 2 文件（gate + 测试）。

| 兄弟卡 | 实测改动面（只读 `git status` 探查） | 与本卡关系 |
|---|---|---|
| wt207 | 该 worktree 在本 sysrev 目录**不存在**（可能已合入或未派生） | 无法实测；按卡面其面为 onboarding/趋势/光子（mobile + 后端服务层），与本卡 llm 并发文件无预期交集 |
| wt215 | `backend/app/core/metrics.py` + `backend/app/orchestration/context_builder.py` + 2 新测试 | **零重叠**（无共同文件） |
| （额外）wt216 | 工作树当前干净 | 无交集 |

唯一同文件敏感点：`settings.py` 的 MINIMAX 区块——本卡改动落在 ：501-511 注释改写 + `MINIMAX_RPM_BUDGET` 新增（+17 行）与校验器 ：1376 附近（+2 行）；`git apply --3way` 可干净合并。

---

## ⑤ 诚实申报

1. **固定窗口的边界突发**：最坏跨窗口边界 1s 内可达 2×N 发起（旧窗口尾 + 新窗口头）。这是固定窗口的已知算术，选它的理由是原子性不依赖 Lua/事务重试、且与官方「每分钟」窗口同构；对保护性预算（20/200 RPM，本卡建议值带安全系数）可接受。若未来要平滑，滑窗 log（ZSET）或令牌桶需 Lua（fakeredis 需 lupa，测试基建要先补依赖）——另开卡再议。
2. **保守误拒**：超发方先 INCR 后 DECR，竞态下他进程可能看到膨胀计数被误拒（方向=永不超发）。多进程规模=3，误拒窗口微秒级，概率可忽略。
3. **直连 lane 不经 RPM 桶**：`minimax_provider.analyze`（error_book 唯一消费者）按卡面「只挂 concurrency.py acquire 路径」未接入——其量小（BATCH-CAP/MINIMAX-QUOTA 双卡同判「风险窗口小」），且其本地 semaphore 保留为自保护阀。若未来 error_book 上量，把直连池并入主池或直连路径同挂 gate 即可（注释已指路）。
4. **固定窗口按真实时钟对齐**：窗口号取 `int(time.time()//60)`，三进程跨机也天然同窗（不依赖本地时区/对齐协议）。
5. **单测模拟"多进程"**：独立 fakeredis 连接 + 共享 FakeServer 复现跨连接竞争语义，非真 fork 多进程；卡面明示「不真起多进程压测」，真实多进程语义由 Redis 原子性保证（生产 redis 与 fakeredis 同守单线程命令序语义）。
6. **零凭据**：测试 SECRET_KEY 为假值 `test-only-not-a-secret-distsem`（命令行注入，不入库）；patch 与报告无任何 key。

## ⑥ 收工核查 + 主会话步骤

### 收工核查（已执行）

- [x] 零 commit 零 push；工作树 = 4 modified + 2 untracked + `v3-output/DIST-SEMAPHORE/{REPORT.md, changes.patch}`
- [x] `changes.patch` 含全部 6 个 diff（`git diff` + `--no-index` 补新文件，672 行）
- [x] 零凭据；未动主仓、未动兄弟 worktree（仅只读 `git status` 探查）
- [x] 全程 LIGHT（pytest 单进程串行定向，无模拟器/浏览器/gradle/独立端口进程）
- [x] /tmp 零本卡产物；worktree 内 `__pycache__`/`.pytest_cache` 为 pytest 副产物（不入库，见清理）

### 主会话合入后步骤（本卡按卡面未真起多进程压测）

1. **合入**：`git apply --3way changes.patch` → 跑 ④ 同套定向测试（对比法）→ commit。零迁移、零 proto、零网关改动。
2. **定档后配 env**（衔接 MINIMAX-QUOTA §2 定档结论）：
   - 充值档（200 RPM）：`MINIMAX_RPM_BUDGET=160`（0.8× 安全系数；`MINIMAX_MAX_CONCURRENCY=8` 维持）；
   - 免费档（20 RPM）：`MINIMAX_RPM_BUDGET=16`（0.8×；并发阀建议同时按 QUOTA 方案 F 下调 env=2，两机制叠加）；
   - 暂不确定：先不动（默认 0=禁用，行为与本卡之前完全一致，零风险合入）。
3. **多进程真压测**（LIGHT 级）：引擎 + 2 个 glm_batch worker 同配上述 env，以 2×预算速率向 glm_batch 投假任务 3 分钟，观察：
   - Redis `sparkle:llm:minimax:rpm:*` 窗口值 ≤ budget（`redis-cli get`）；
   - 引擎与 worker 日志出现 `MiniMax account RPM budget exhausted`（非空消息）且走既有 fallback/重试链，无空消息 error；
   - 停 Redis 容器 30s：日志出现限频 WARNING（NOT enforced）且**任务不阻断**；恢复 Redis 后窗口 key 重新出现；
   - 崩溃演练：kill -9 一个 worker 后预算不悬空（60s 窗口滚动即自愈）。
4. **观察窗口**：下一 PROD-LOG 轮核对 MiniMax 侧 1002（rate limit）是否归零/显著下降——本闸生效的直接证据。

### 遗留申报（本卡不修）

- 直连 lane（error_book）未入全局预算（见 ⑤-3，量小，注释已指路）；
- MINIMAX 池 429 自适应（QUOTA §4.3 已申报另开卡；本闸把 1002 消灭在源头后，其优先级进一步下降）；
- 固定窗口边界突发平滑化（见 ⑤-1，需 Lua/测试基建先行）。
