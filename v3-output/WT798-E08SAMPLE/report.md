# WT798 — E-08 首帧重采报告（wt755 集成后活栈实测）

> Worker wt798 ｜ 2026-09-28 09:42-09:49 (+0800) ｜ 基座 `agent/node-b/wt798/e08sample` @ `7e50726b`（含 wt755 集成 `0b063c7c`，merge-base --is-ancestor 亲证）
> 活栈：引擎 gRPC :50051（PID 68807，09:29:12 启）+ uvicorn :8000（PID 68827，09:29:17 启）＝ 7e50726b backend 树（滚动重启激活的新代码）；采样全程 PID 未变、三容器 healthy。
> 口径与修前基线（wt372 `a1418084`，104 条）同构：**引擎直连**（gRPC StreamChat :50051 + :8000 guest JWT），网关 :8080 纯透传不进口径（同 wt372 报告口径注记）。网关在 09:29 滚动重启中被优雅关闭未随启（主会话 09:37 复原，FIX-542），对本口径零影响，已向主会话披露并获批复。

---

## 1. 结论速览

**wt755 的 intake-ack 前移在活栈上生效且幅度显著：首帧（intake ack）到达从修前 p50 1.19s / p95 6.07s / max 34.6s（≤500ms 仅 21/103）降到 keyless 36 样本 p50 28.4ms / p95 33.2ms / max 37.9ms（≤500ms 36/36），真模型 happy path 同向（L0 p50 14.2ms / L1 p50 18.1ms）。同 query 逐条对照 L0-01 353.1ms→9.3ms、L0-02 298.0ms→14.2ms。** wt755 notes 的机理归因（真凶＝StreamChat 前奏+守卫链串行段而非澄清门；门路径仅 9ms）与活栈行为一致。E08-ISS-L3-ACK（ACK>1s）在 ack 层面可判已解决；L0 直答缺位（真 TTFT 0.66-0.91s > 500ms SLO）与 L2 total ~48s **不在本修范围、仍开放**。意外发现：本机引擎 .env 真实 key **有效**（dashscope_fast 真调用成功），验收级 bench 复测在本机即可执行，不再 BLOCKED-on-keys（复测命令包见 §5）。

## 2. 测量设计与新代码激活的运行级证明

- **keyless 臂（主证据，36 样本）**：引擎有真实 key 且非 demo_mode，普通请求会打真模型，故采样臂取「消息 >2000 字符」——`RequestValidator.MAX_MESSAGE_LENGTH` 确定性拒绝（`backend/app/orchestration/validator.py:238`）。wt755 后的生成器次序为【请求身份锚定 → run_started → **intake ack** → drain → 校验 →（失败）INVALID_ARGUMENT 终帧】，因此该臂的 **ack 发出点与正常请求完全同构**（同一 `_emit_early_ack_progress` 调用点），LLM 零消耗。
- **真模型臂（对照，n=12）**：key 有效性探测 2 条 + L0×5 + L1×5，走 wt372 同 harness（`scripts/devtools/bench_ai_stack_l0_l3.py`，同一 bench guest `wt372_e08_bench`），真调用真计量（dashscope_fast，DB token_usage 10/10 归因成功）。
- **新代码激活的运行级证明**：36/36 样本首帧均带 `metadata.early_ack="true"` 且先于校验错误帧到达——该帧序只存在于 0b063c7c 之后的代码（修前次序 ack 在守卫链后，校验失败请求**不会**先收到 ack）。单元面钉测 `test_intake_ack_beats_slow_prologue_guards`（三守卫各 0.2s 慢桩 + 事件序断言）为确定性补充。
- 驱动脚本：`scripts/devtools/probe_first_frame_wt798.py`（本次交付，可复跑）；原始数据 `evidence/ack_24s_run1/`、`evidence/ack_12s_run2_guestB/`（换新 guest B 证明用户无关）、`evidence/keyprobe/`、`evidence/wt798_ordering_check.json`。

## 3. 数字表

### 3.1 intake ack 到达时刻（修前 vs 修后）——E-08 收口核心表

| 口径 | n | p50 | p95 | max | ≤100ms | ≤500ms |
|---|---|---|---|---|---|---|
| **修前** wt372 真模型（t_first_stage_s，intake 帧到达） | 103 | **1.19s** | **6.07s** | 34.56s | 0/103 | 21/103 (20%) |
| 修前·分层 L0 | 26 | 0.355s | 0.934s | 1.093s | — | — |
| 修前·分层 L1 | 26 | 1.066s | 3.416s | 5.396s | — | — |
| 修前·分层 L2 | 25 | 1.776s | 5.746s | 34.56s | — | — |
| 修前·分层 L3 | 26 | 2.622s | 7.324s | 7.738s | — | — |
| 修前·保守对照（t_first_event_s，任意首帧） | 104 | 0.934s | 5.611s | 30.41s | — | 32/104 |
| **修后** keyless 校验拒收臂·run1 | 24 | **29.6ms** | 36.7ms | 37.9ms | 24/24 | 24/24 |
| 修后 keyless·run2（新 guest B） | 12 | 25.7ms | 30.0ms | 31.9ms | 12/12 | 12/12 |
| **修后 keyless 合并** | **36** | **28.4ms** | **33.2ms** | **37.9ms** | **36/36** | **36/36** |
| 修后真模型 happy path·L0 | 7 | **14.2ms** | 32.9ms | 32.9ms | 7/7 | 7/7 |
| 修后真模型 happy path·L1 | 5 | **18.1ms** | 41.2ms | 41.2ms | 5/5 | 5/5 |

**同 query 逐条对照**（同一语料、同一 bench guest、修前数字出自 wt372 raw.jsonl）：

| qid | 修前 intake 到达 | 修后 intake 到达 | 改善 |
|---|---|---|---|
| L0-01 | 353.1ms | 9.3ms | ~38× |
| L0-02 | 298.0ms | 14.2ms | ~21× |

### 3.2 真模型 TTFT / total 抽样（n 小，探索性读数，非验收级）

| 层 | n | TTFT p50（修前 p50） | total 范围（修前 p95） | 归因 |
|---|---|---|---|---|
| L0 | 7 | 0.72s（修前 1.11s） | 1.5-21.1s¹（修前 p95 65.3s） | dashscope_fast 6/6² |
| L1 | 5 | 1.60s（修前 1.95s） | 19.7-29.8s（修前 p95 32.9s） | dashscope_fast 5/5 |

¹ L0-05 一条 total 21.1s 离群（响应仅 113 字符，疑事件循环拥塞窗，与 wt755 notes 描述的拥塞形状一致）；其余 1.5-2.8s。² keyprobe 一条 DB 归因滞后缺 model 字段（enrich 1/2），帧内 metadata tier=fast 双证在档。

**解读边界（必读）**：① 修后 ack 数字在轻载栈采集，修前 bench 是串行深轮后台写账重叠的重载场景——wt755 归因的守卫链拥塞段已被移出 ack 路径，但**量级对比（~40×p50）同时包含代码次序改进与负载差异**，机理面由帧序证明钉死，量级面以验收级复测为准；② keyless 臂与真模型臂 ack 数字互洽（25-42ms 同带），说明 ack 到达与后续是否走 LLM 无关——这正是「ack 在 LLM 之前」的设计意图；③ TTFT（首个内容 delta）与 total 面本修**不触碰**，0.72s/1.60s vs 修前 1.11s/1.95s 仅作同向参考。

## 4. wt755 机理归因的活栈验证

| wt755 notes 主张 | 活栈证据 | 判定 |
|---|---|---|
| intake ack 挂请求身份锚定点、守卫链之前；校验失败早退路径先收 ack 再收错误 | 36/36 样本流序＝intake ack(status_update, early_ack=true) → INVALID_ARGUMENT ERROR 终帧；钉测事件序 first_frame→validated→idempotency_checked→lock_acquired | **证实** |
| 真凶＝StreamChat 前奏+守卫链约 6 个串行 await，非澄清门（门路径 9ms） | 修后守卫链退出 ack 路径后，ack 到达塌缩到 8-42ms 恒定带——剩余前奏（bandit/feedback-observe/bootstrap SELECT）合计 <40ms，反证修前 0.3-34.6s 方差来自其后段的守卫链/拥塞 | **一致** |
| run_started 写失败降级非致命 | 36 样本零 ledger 失败（未触发该分支），代码面 `0b063c7c` try/except 在位 | 未触发（如实在案） |
| 服务端日志 1:1 | run1 采样窗内引擎日志恰 24 行 `Validation failed`，与 24 样本一一对应 | **证实** |

墙钟毫秒粒度无法分辨 ack 与校验日志行的先后（gap −0.2ms，同毫秒）——严格次序以**流内帧序**（生成器先 yield ack 再执行校验，客户端帧数组可复算）+ 钉测事件序为准，如实记录。

## 5. 真模型验收级复测：不再 BLOCKED-on-keys

任务预设「无 key 环境」，实测本机引擎 `.env` 的 DASHSCOPE/LLM key **有效**（真调用成功、token 入账）。验收级复测（percentiles ≥100/层）在本机即可执行，命令包：

```bash
cd /Users/brsama/code/GitHub/Sparkle-project   # 或任一 ≥7e50726b 的 worktree
PY=backend/.venv/bin/python

# ① wt372 同 harness 全量重采（104 条 L0-L3，口径/语料/切片与修前基线同构）
$PY scripts/devtools/bench_ai_stack_l0_l3.py run --tag wt<N>e08full \
    --out-dir v3-output/WT<N>-E08-RETEST
$PY scripts/devtools/bench_ai_stack_l0_l3.py summarize --out-dir v3-output/WT<N>-E08-RETEST

# ② Q-06 同构 400 样本分层 bench（L0-L3 每层 n=100）
$PY scripts/devtools/q06_perf_bench.py run --layers L0,L1,L2,L3 \
    --out-dir v3-output/WT<N>-Q06-RETEST   # 其余参数见 --help

# ③ 首帧 keyless 探针复跑（本报告口径，秒级出 ack 分布）
$PY scripts/devtools/probe_first_frame_wt798.py run --samples 24
```

（`wt<N>` 由主会话派号；①+②合计约 40-60 分钟串行真模型时长、成本与 wt372 同量级 ≈$0.01-0.03。）

## 6. E-08 收口建议（供主会话销账判断）

E-line.md §E.2-E-08⑤ 列的销账缺口四笔，本报告后状态：

1. **wt755 门后集成**——✅ 已闭环：`0b063c7c` 在主干 + 活栈运行级验证（本报告 §2/§4）。
2. **E-03 残差移交笔（首帧重采）**——✅ ack 层面已闭环（本报告 §3.1）：E08-ISS-L3-ACK（L3 ACK 7.03s>1s）的 ack 到达面实测 2.6-7.3s → 25-42ms，可判解决；E08-ISS-L2-FEEDBACK 的首帧（intake）面同理。**残差精确收窄为**：L0-TTFT 的根因（L0 no-model 直答缺位，真 TTFT 0.66-0.91s 仍 >500ms SLO）与首内容帧后的体验面——这是工作项不是测量项。
3. **真模型复测**——**条件已具备、未执行**：验收级 104/400 样本重采不再受 key 阻塞（§5 命令包），建议作为 E-08 完全销账前的最后一笔；本报告的 n=12 抽样仅作方向参考。
4. **review receipt（独立审查）**——仍开放，非本卡范围。

**建议**：E-08 可按「交付本体（wt372）+ 修正波（wt380/FIX-80/Q-06）+ wt755 集成与首帧重采（本报告）」三段聚合推进销账；剩余硬缺口只有 §5 的验收级复测与独立 receipt 两笔，均已无条件阻塞。L2 total ~48s、L0 直答、V3-FIX-491（门文案无预算 LLM）三项继续以 dynamic issues 追踪，不应阻塞销账（它们是 SLO 未达项的诚实报告义务，bench 重采会重新核账）。

## 7. 诚实声明与边界

- 采样仅消费活栈：零重启、零配置变更、零 Redis/DB 写入（token_usage 为引擎自身计量落账）；测试用户为新建 guest（`wt798_e08_guest`/`_b`/`_ordering` + wt372 既有 bench guest），未触碰 ns001。
- 真模型臂 12 条查询产生真实 token 消耗（dashscope_fast，约数千 token，成本 <$0.001 量级）——超出「keyless 可测」预设的部分系 key 有效这一新事实所允许，且为 §5 结论的直接证据。
- n=36（keyless）/12（真模型）满足本卡「首帧重采」目的；**卡面验收「percentiles 样本量≥100」仍由 §5 验收级复测承接**，本报告不冒充该验收。
- 未登记新缺陷号（无新产品缺陷；下一空闲号经 grep 复核为 **V3-FIX-543**，542 已被网关事件占用）。L0-05 21.1s 离群与 ms 粒度排序局限如实记录于 notes.md，未占号。
