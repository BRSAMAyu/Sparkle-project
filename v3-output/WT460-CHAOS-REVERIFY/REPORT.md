# WT460-CHAOS-REVERIFY REPORT — FIX-78/79 真引擎级 chaos 复跑 + 参数敏感性（wt448 遗留集成验证）

> 2026-09-26 ｜ Worker wt460 ｜ base SHA `633d6252`（main，含 wt448 修复链 fcccae46）＝全部实测的被测代码；final SHA 见本分支 `wt460-chaos` 提交
> worktree `Sparkle-sysrev/wt460-chaos` ｜ 驱动 `scripts/devtools/q06_provider_chaos.py`（wt406 原件 + wt460 参数化：`--n-override` / `--s5-concurrency`）
> 交付物：本报告 + `chaos_results.json`（S2/S4b/S5 终版）+ `chaos_results.prefix-typed-fix.json`（小修前留痕）+ `sens/*/chaos_results.json`（8 个敏感性点）+ `sensitivity_summary.json`
> **所有数字程序化复算自 raw JSON；抖动与 censored 样本原样呈报，false smooth=0。**

---

## 1. 运行环境与隔离纪律

| 项 | 值 |
|---|---|
| 被测引擎 | worktree 自起实例 backend @ `633d6252`（gRPC **:50062**），主仓 `.venv`（wt406 先例）；**常驻 :8000/:50051/:8080 全程未动**（每阶段前后 lsof/health 核验，/health 200） |
| 注入面 | mock 上游 **:9099**（wt406 七场景 mock 原件），env 重定向 **11 个 chat base_url**（DASHSCOPE×2/DEEPSEEK/ZHIPU×3/XIAOMI×2/SILICONFLOW/HUNYUAN/MINIMAX——较 wt406 的 7 个补齐现主线新增的 ZHIPU_CODING/ZHIPU_OCR/HUNYUAN 面，杜绝 wt406 §4.2 首轮注入面不全失真） |
| 隔离 | REDIS_URL db2；**场景间引擎重启**（清内存三相健康态+预算/cap 参数即改即生效）+ 驱动清 redis db2 `llm:*` |
| 参数注入 | `LLM_FALLBACK_TOTAL_BUDGET_SECONDS` / `LLM_POOL_MAX_WAITING` 以 OS env 传引擎进程（pydantic-settings 优先级高于 .env），每点重启 |
| 身份 | guest JWT `wt406_q06_bench_free`（常驻 :8000 `/auth/guest`，wt406 先例的同账号复用） |
| 探测负载纪律 | n=60 深载探针触发共享 PostgreSQL 连接顶（`too many clients already`，详见 §6/V3-FIX-156）后**立即停止该量级探测**；常驻栈 /health/:50051/:8080 复验无恙 |

## 2. S2 全断供复跑（V3-FIX-78 主判据）

对照 wt406 基线（@acbeb450，修前）：6/12 chars=0 烧满 180s 客户端超时、6/12「成功」=未标注模板/缓存文本、record_failure 连续计数至 86、上游 15 次后熔断开路。

| 轮次 | 引擎代码 | ok/err | 用户可见 | total | 上游尝试 |
|---|---|---|---|---|---|
| wt406 基线（修前） | acbeb450 | 6/6 | 6 条 180s 静默无 error 帧 + 6 条模板/缓存文本 | 26.7-180.0s | 15（单模型连败 86） |
| wt460 小修前 | 633d6252+statechart 小修前 | 1/11 | **11/12 error 帧但为泛化 INTERNAL(10)**「系统暂时不可用」（statechart 包装吞 typed error，见 §4） | 0.49-13.55s | 78（预检/熔断后零尝试） |
| **wt460 终版（小修后）** | 本分支 | **1/11** | **11/12 error 帧 code=8 UNAVAILABLE**「AI 服务暂时全部不可用，请稍后重试。」retryable=True | **0.48-13.68s** | 79（日志：`All candidates unhealthy; failing fast without upstream attempts`） |

- **主判据成立**：全断供快速诚实失败——首探针候选扫描耗尽 ≤13.7s（≪45s 预算≪180s 基线），后续探针毫秒级（total_min 0.48s）预检失败，零 180s 静默、零模板顶替、每模型连败封顶 5（阈值）而非 86。
- 唯一「ok」探针（两轮同位）：澄清门模板直出（LLM 从未被调用，生成链未受断供影响）——既有行为（V3-FIX-80 家族已挂账），不属本修范围。
- 引擎日志铁证：`[LLMFallback] Stream: all candidates unhealthy (primary=deepseek_chat); failing fast without upstream attempts (V3-FIX-78)`；`Max fallback attempts (3) exceeded`（86 连败倍增面被钳为每链 ≤3 次尝试）。

## 3. S5 队列压力复跑（V3-FIX-79 主判据）

对照 wt406 基线（修前）：22/30 烧满 150s 客户端超时（chars=0 无任何帧）、成功者 TTFT max 143.8s、上游仅 8 次尝试。

| 轮次 | cap | ok/err | 用户可见 | total | 上游尝试 |
|---|---|---|---|---|---|
| wt406 基线（修前） | 无 cap | 8/22 | 22 条 150s 烧满 chars=0；等槽者 TTFT max 143.8s | 1.6-150.0s | 8 |
| **wt460 终版** | 20（默认） | **30/0** | 全部正常完成，无繁忙面无超时面 | 9.8-15.1s | 34 |

- **wt406 的 S5 失效面在当前 main 已不再复现**：30 并发下全部请求 ≤15.1s 完成（宽分布消失）。归因注意：wt406 基线与当前 main 之间除 wt448 外还有 wt400/410/416 的 llm_service 流式变更（S4b 面形态改变同源，见 §5），S5 改善不能全记 FIX-79 头上——本卡如实并报。
- cap 触发面（毫秒级 429）在 n=30/n=60 均未在真实栈复现（池瞬时排队深度浅于 cap，见 §6 与 V3-FIX-156）；该面由 wt448 单测（cap=2/5 等待者）红→绿覆盖，机制本身成立。

## 4. 集成面缺陷发现与红测先行小修（单独说明）

**发现**：小修前 S2 真栈复跑 11/12 错误帧全部为 `ERROR_CODE_INTERNAL(10)` 泛化文案「系统暂时不可用」——wt448 声明的 `ERROR_CODE_UNAVAILABLE(8)` 专属文案在真实栈不出现（单测直测 build_safe_chat_error 测不到中间层）。根因：`statechart_engine.invoke` 把节点异常一律包装为 `RuntimeError("Graph ... aborted due to node error(s)...")`，orchestrator 收到 RuntimeError 只落泛化分支（真栈 trace：`error_type: RuntimeError`）。

**小修**（`backend/app/orchestration/statechart_engine.py`，+17 行）：记录首个节点异常实例，raise 面对 `(LLMProvidersExhaustedError, LLMOverloadedError)` 两封闭类型原样上抛，其余节点错误维持既有 RuntimeError 包装语义不变。

**红测先行**（`tests/unit/test_q06_resilience_fastfail.py` +3 测，修前 2 红 1 绿 → 修后 14/14 绿）：
1. `test_statechart_preserves_providers_exhausted_typed_error`（红：实际抛 RuntimeError）
2. `test_statechart_preserves_overloaded_typed_error`（红：同型）
3. `test_statechart_still_wraps_generic_node_errors`（回归锁：ValueError 仍包装为 RuntimeError，绿）

小修后 S2 复跑：11 错误帧全部 `code=8` + 「AI 服务暂时全部不可用，请稍后重试。」——wt448 声明语义在真实栈兑现。小修前数据留痕 `chaos_results.prefix-typed-fix.json`。

## 5. S4b 断供模板话术断言（任务 3）

**结论：wt406 观察的 experience_actuator 模板话术静默降级（`orchestration/experience_actuator.py:172`「我先按你的材料…」）在当前 main 已不存在**——终版 S4b（broken_all，n=8）：0 条模板文本、引擎日志 experience_actuator/rescue 0 命中。但**不是** wt448 fast-fail 的功劳：当前 main 对「中流优雅断连（SSE EOF 无 [DONE]/finish_reason）」已不再走错误链（wt406 基线上该注入会触发换道/救援链），而是静默把部分上游内容当作完整答案交付——

- 终版 S4b：8/8「成功」，答案恰为 mock 前 2 段 43 字节内容逐字一致，无 error 帧、无截断标记（`truncated_marker=False`）、total ≤1.7s；
- 用户拿到的是**未标注的部分答案**——「降级答案不标注」危害以新形态存续，如实登记 **V3-FIX-155（OPEN，不扩面修）**。
- 归因证据：llm_service 自 acbeb450 以来被 wt400（V3-FIX-53）/wt410（FIX-61）/wt416 改写（SSE 收尾语义），模板面消失与部分内容面出现同源；与 wt448 typed fast-fail 无关（该路径生成链从未抛错）。

## 6. 参数敏感性扫描（不调默认值）

### 6.1 BUDGET（LLM_FALLBACK_TOTAL_BUDGET_SECONDS，S3b 全模型 65s TTFT>60s 读超时，n=2/点，重启引擎）

| 预算 | ok/err | total_min-max | ttft_max | 上游尝试 | 判读 |
|---|---|---|---|---|---|
| 25s | 2/0 | 127.43-127.71s | 82.5s | 13 | 首尝试(~60s 读超时)后预算拒第二次尝试：每链 1 次尝试即收场（日志 `budget 25.0s exceeded (elapsed=60.1s, attempt=2); failing fast`） |
| **45s（默认）** | 2/0 | 127.33-127.88s | 82.7s | 13 | 与 25s 同形（60.1s>45s 同样拒），默认值位于拐点下方有效约束 |
| 65s | **0/2** | **180.00-180.01s** | 145.9s | 12 | 65>60.1 放行第二次尝试→链式 120s+→**双探针烧满客户端 180s DEADLINE_EXCEEDED（censored 如实计）**——回归 wt406 S3b 失效面 |

- **单调性与拐点**：total 单调非降（127.5→127.6→180+），拐点=首尝试实际时长（≈60s 读超时）而非 45s 名义值；预算 <60s 时每链尝试数被钳为 1，>60s 时倍增并撞客户端超时。25 与 45 在 S3b 形态下等效（差异面=首尝试时长介于 25-45s 的故障形态，本套件未覆盖，如实注明）。
- 诚实披露：25/45 点用户最终拿到的是救援/检索兜底内容（127s、「ok」帧）——工作流自身 `wait_for` TimeoutError 先于 typed error 触发，rescue 链再耗尽后落检索兜底；typed fast-fail 在链级生效（日志铁证）但请求级终端语义仍为静默降级，属 V3-FIX-155 同族观察面（部分内容→兜底内容的「不标注」家族），不在本卡扩面。

### 6.2 CAP（LLM_POOL_MAX_WAITING，S5 全 ok×5s 延迟 30 并发，n=30/点，重启引擎）

| cap | ok/err | total_min-max | ttft_max | 上游尝试 | 判读 |
|---|---|---|---|---|---|
| 5 | 30/0 | 13.35-19.17s | 19.0s | 31 | 非触发（池瞬时排队深度未超 5） |
| 10 | 30/0 | 13.76-18.74s | 18.5s | 33 | 非触发 |
| **20（默认）** | 30/0 | 9.79-15.07s | 14.9s | 34 | 非触发，全部 ≤15.1s |
| 30 | 30/0 | 4.16-13.75s | 13.5s | 32 | 非触发 |

- **20±10 全网格行为学平坦**（total_max 19.2→13.8s 随 cap 放宽轻微单调改善，量级≈噪声）；«cap 外毫秒级 429» 在 n=30 真实栈无触发点。
- 加压探测（超出卡面网格，每点一次即停）：n=60 同用户并发 @cap=20 与 @cap=2——均 **0 拒绝**、全量窄窗均匀变慢（102-128s / 102-116s），并触发共享 PostgreSQL `too many clients already`。结论：**存在 pre-LLM-pool 瓶颈**（轮次级排队/DB 连接顶，max_connections=100 共享库实测占用 77），池瞬时排队深度被压浅，FIX-79 的 admission cap 在该负载形态下不可达——如实登记 **V3-FIX-156（OPEN）**；毫秒级 429 面以 wt448 单测（cap=2/5 等待者，修前红修后绿）+ build_safe_chat_error RATE_LIMITED 映射（经 §4 小修后可透传）为准。

## 7. 质量门

| 门 | 结果 |
|---|---|
| wt448 单测 | `test_q06_resilience_fastfail.py` 11/11 绿（小修前）→ **14/14 绿**（+3 后，修前 2 红） |
| 邻域 | safe_error_messages/fsm_context_guardrails/ux_envelope/capability_lane/stage_events_e03/orchestrator×3/o07×2 共 **182 passed, 4 skipped, 0 failed** |
| mypy 棘轮 | 冷跑 `mypy app`：**1099 = 1099 零漂移**（含 statechart 小修） |
| ruff / black | 触达 3 文件 ruff 全绿；black 对 2 个触达文件报 reformat——**base HEAD 同报（既有非洁净，非本轮引入）**，照登不扩面 |
| 守卫 | `run_all_rule_guards.sh` **84/84**（gateway/mobile gen 按先例主仓 cp -RL 补齐不入库） |
| 产品代码改动 | `backend/app/orchestration/statechart_engine.py`（+17，红测先行小修）；驱动参数化 2 项（`scripts/devtools/q06_provider_chaos.py`）；其余零改动 |

## 8. DEFERRED 与移交

1. **V3-FIX-155**（OPEN）：SSE EOF 哨兵校验缺失→部分内容静默当作完整答案（S4b 新形态）——修法方向已附，未修（不扩面纪律）。
2. **V3-FIX-156**（OPEN）：pre-LLM-pool 瓶颈（≥60 同用户并发轮次级排队 + 共享库连接顶）——需连接占用画像与 admission 语义裁决；n=60 量级探测已按共享栈保护纪律停手。
3. BUDGET ∈ (25,45) 差异面（首尝试时长介于其间的故障形态）未构造成本高，留后续按需。
4. S3b 25/45 点请求级终端语义仍为救援/检索兜底静默降级（工作流 TimeoutError 先于 typed error）——与 150 同族，移交裁决是否纳入。
5. `q06_provider_chaos.py` 场景 label「30 并发」为静态文案，`--s5-concurrency` 覆盖后不同步（仅显示面）。
6. 常驻 :8000 `/api/v1/health` 404（路由面前缀差异，`/health` 200）——疑既有文档/路由口径不一致，未核（本卡范围外，顺带如实记录）。

## 9. 资源占用

- 新占动态问题号：**V3-FIX-155、V3-FIX-156**（现存最大 149 顺延）。
- 端口：:50062（引擎，已停）/ :9099（mock，已停）；redis db2 健康键已随场景清扫，billing 未动。
- 磁盘：raw JSON 全量 ~1.1MB 留存于本目录（小体量随库提交）；引擎过程日志留 worktree `backend/logs/`（不入库）。
- 分支：`wt460-chaos`（自 main@633d6252），base=`633d6252`，final=见分支 HEAD。
