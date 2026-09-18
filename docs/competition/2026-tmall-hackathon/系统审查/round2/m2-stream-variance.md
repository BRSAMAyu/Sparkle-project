# M-2 起流波动诊断报告 — 偶发 90s 不起流（跨端一致）

- 诊断员：M-2 专项（聊天起流波动）
- 基线：`3f6adce` 链上提交 `3f6acdce`（工作树 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`）
- 方法：引擎日志 `[LATENCY]` 探针画像 → 排队链代码逐点排查 → 真实 WS 复现实验（10 条消息，预算 12）
- 运行栈：gateway `wt2` :8080，引擎（gRPC :50051 + FastAPI :8000）`Sparkle-project/backend`，与 wt5 同 commit 代码

---

## 一、根因定性（结论先行）

**定性：provider 侧首 token 尾延迟（LLM TTFT tail），非引擎侧排队。** 引擎聊天链的全部串行化点均被逐一排除（§3）；`execute_graph` 内首次 LLM 流式调用是首事件耗时的绝对主导（健康样本 5.5–22s，夜间离群 58.3s）。90s 完全不起流 = provider TTFT 尾部（58s+ 已实测）× 三个放大器（openai SDK 隐式重试 ×2、fallback 管理器"首 chunk 前不切换、异常后才切换+退避"、stream_timeout=120s 过长）的叠加，且全链路（引擎→网关→主聊天 UI）无任何首事件守卫，静默窗口被完整放行给用户。

不修复引擎串行化（无实锤串行化点）；给客户端预期管理与可观测性建议（§6）。

## 二、统计画像（首事件分布）

样本：引擎日志 `[LATENCY] probe finish`（`latency_probe.py`，`first_stream_content` = 首个流式内容距请求起点）。

| # | 请求 | 窗口 | total | first_stream | 主导 hop |
|---|---|---|---|---|---|
| 1 | f1verify-001 | 00:23 | 8.0s | 8.0s | check_sufficiency=6.6s（图前） |
| 2 | f1verify-002 | 00:24 | 15.0s | 14.9s | 图前 5.7s + execute_graph |
| 3 | **f1verify-003** | **00:26–00:28** | **86.2s** | **58.3s** | **execute_graph=81.5s**（图前仅 4.5s；route_and_classify=3.6s） |
| 4 | m2-a-001(复跑) | 00:52 | 14.3s | 10.1s | execute_graph=11.6s |
| 5 | m2-a-002(复跑) | 00:53 | 18.9s | 15.1s | execute_graph |
| 6 | m2-a-003(复跑) | 00:53 | 25.0s | 22.2s | execute_graph |
| 7 | m2-b-u1-r1 | 00:53 | 11.5s | 11.0s | execute_graph=10.3s |
| 8 | m2-b-u2-r1 | 00:53 | 7.3s | 5.5s | execute_graph |
| 9 | m2-c-r2 | 00:54 | 13.5s | 11.0s | execute_graph=11.4s |

- **first_stream 分布（n=9）**：5.5 / 8.0 / 10.1 / 11.0 / 11.0 / 14.9 / 15.1 / 22.2 / **58.3**(s)。中位 ≈11s，p90 ≈22s，离群 58.3s（03:00 前夜间窗口，与 M-2 背景的 provider TTFT 5.6–32s 波动同源且更长）。
- **图前编排（debrief→context→spine→aurora→sufficiency→goal→routing→plan）**：全部样本 0.4–4.5s，稳定，73eab280 的首 token 优化未被回归。
- **离群特征**：单请求、无并发（同窗口仅 1–2 个活跃 LLM 调用）、非排队形态——排队会在并发/前序请求维度留痕，未发现。
- 附带异常（实验 A 第一轮 msg2，00:44:02）：客户端 11.3s 收 `unavailable / "Cancelling all calls" / retryable=true` 错误帧，引擎侧零痕迹；2 分钟后（00:45:50）引擎进程被外部（并行会话）重启、旧日志 inode 被截断，服务端证据链丢失。定性：LLM 客户端 teardown/进程重启击杀在途调用——属"重启踩踏"类噪声，与排队无关，但会以 retryable 错误形式被用户感知。

## 三、排队链排查（逐点排除）

| # | 候选串行化点 | 代码位置 | 机制 | 裁决 |
|---|---|---|---|---|
| 1 | 会话分布式锁 | `orchestrator.py:2069`→`state_manager.py:329` | Redis `SET NX EX`，非阻塞；占用中→立即 CONFLICT `retryable=true`；Redis 异常 fail-open | **排除**：实验 C 实测 0.099s 内拒绝（§4），无排队 |
| 2 | llm_security_wrapper 配额互斥 | `llm_security_wrapper.py` | 无 Lock/Semaphore；配额为 check-and-record，非互斥 | **排除** |
| 3 | llm_concurrency 信号量 | `services/llm/concurrency.py:103` DeepSeek `max_concurrent=10, queue_timeout=30s` | 条件变量阻塞队列，30s 超时后抛 "LLM API deepseek is busy" | **排除（本场景）**：实验窗口无 waiting 记录、无 busy 事件； solo 使用远达不到 10 并发。仅高并发批量任务下可能触发 |
| 4 | DeepSeek client 连接池 | `services/llm/providers.py:61` | AsyncOpenAI 单例长连，无自建池上限 | **排除** |
| 5 | 网关 WS/gRPC 桥排队 | `handler/chat_orchestrator_chatflow.go:301` | 总超时 300s，无首事件守卫；gRPC retry 仅 UNAVAILABLE/RESOURCE_EXHAUSTED | **排除（排队）**；但 300s 窗口允许静默挂穿（§5） |
| 6 | SDK 隐式重试（放大器） | `providers.py:61` 未传 `max_retries` → openai `DEFAULT_MAX_RETRIES=2` | 429/连接错误时 SDK 内部指数退避重试 2 次，**用户侧完全不可见、日志不可见** | **确认为放大器**：TTFT 尾部被拉长且不可归因 |
| 7 | fallback 流式回退（放大器） | `services/llm/fallback.py:468` | 首 chunk 前可切模型，但**异常后才切换** + 指数退避 sleep；`llm_service.py:1025` `stream_timeout=120s`（reasoning 300s） | **确认为放大器**：首次尝试可静默挂 120s 才触发回退 |

## 四、复现实验矩阵（真实 WS → :8080，共 10 条消息）

脚本 `/tmp/m2_ws_experiment.py`（guest token → ws ticket → `ws://localhost:8080/ws/chat`）。

| 实验 | 设计 | 发送→首事件(ack) | →done/error | 结论 |
|---|---|---|---|---|
| A1 单用户同会话连发×3（第一轮，旧进程） | 会话内排队 | #1 21.5s done(30帧)；#2 **11.3s error "Cancelling all calls"**；#3 29.9s done | — | 出现一次在途 LLM 调用被击杀（进程重启前噪声）；引擎探针：#3 total=27.1s / first_stream=25.1s / execute_graph=25.6s |
| A2 同设计复跑（新进程） | 会话内排队 | ack 均 ≈0.01s | 14.9s / 19.0s / 25.2s 全 done | 同会话**串行复用无病态排队**；first_stream 10.1/15.1/22.2s 阶梯 = provider TTFT 波动 |
| B 双用户并发各 1 条 | 跨用户争用 | ack 均 ≈0.01s | u1 11.5s done / u2 7.3s done | **无跨用户争用**：双请求同时进行，双双健康完成 |
| C 同用户双连接同会话并发 | 会话锁 | 后到者 **0.099s** 收 `conflict "Session is busy processing another request, please wait." retryable=true` | 先到者 13.6s done | **会话锁 fail-fast 实锤**：立即拒绝，绝不静默排队 |

服务端探针交叉验证（复跑窗口）：图前 hop 稳定 0.9–2.1s（build_full_context 为主），`route_and_classify/dual_core_routing` ≈4–45ms，波动全部落在 `execute_graph` 首流。

## 五、"90s 不起流"的构成与 45s 守卫交互

静默窗口构成（用户视角，主聊天路径）：

```
网关 ack（≈0s，非首token）→ 图前编排 0.4–4.5s → execute_graph 首个 LLM 流
  ├─ provider TTFT：中位 11s，夜间尾部 58s（实测）
  ├─ openai SDK 隐式重试 ×2（429/连接错误，指数退避，完全不可见）
  ├─ stream_timeout=120s：挂死也等到 120s 才回退
  └─ fallback 切换仅在异常后 + 退避 sleep
→ 全链路无首事件守卫（网关 300s 总超时；引擎 120s；主聊天 UI 无守卫）
```

- 中位情形 ≈15–25s 起流（与 M-1 残余 ~24s 一致）；尾部情形 58s+（实测）×放大器即可解释 **90s 完全静默**，无需假设引擎排队。
- **45s 守卫交互核对**：A-3 的 `_firstEventTimeout=45s` 仅存在于 `modeling_chat_screen.dart:43`（`mobile/lib/features/user/presentation/screens/`）；**主聊天链（`websocket_chat_service_v2.dart` + chat feature）无首事件守卫**——只有连接级重连调度（800ms/1.2s/2.2s…），不对内容静默计时。因此：主聊天 90s 死等成立；modeling 聊天 45s 报错且**不自动重试**（`_handleStreamError` 单次提示后收尾），无"双重等待循环"；但客户端放弃后引擎会继续把 graph 跑完（一次性 LLM 浪费，会话锁随流终止释放）。

## 六、建议（定性 provider 侧 → 预期管理 + 可观测性，未改码）

**P1 客户端预期管理**
1. 主聊天链补 A-3 同款首事件守卫（45s 建议降至 30s + 立即给"AI 排队中，正在重试"文案），超时后带退避的一次自动重发（利用 `request_id` 幂等缓存 `orchestrator.py:2052`，引擎侧已支持防重）。
2. 起流后不再需要守卫——metadata/status_update 帧即算存活（modeling 屏已如此，主聊天照搬）。

**P2 引擎可观测性与护栏（微小改动，建议后续 PR，本次未动码）**
3. `providers.py:61` 显式 `AsyncOpenAI(..., max_retries=0)`：把隐式重试收敛为显式（fallback 管理器已有重试职责，SDK 层重试只会叠加不可见延迟）。
4. `llm_service.py:1025` `stream_timeout` 120s→45s（首 chunk 前），超时即触发既有 fallback 换模型路径；配合 `stream_chat` 已有 `FIRST_CHUNK` 日志（仅 `_current_selection` 分支打点，两分支补齐）。
5. 在 `providers.stream_chat` 打 provider 级 TTFT 探针（connect→首 chunk），归因 DeepSeek/智谱夜间限流；现有 `[LATENCY]` 探针已可区分图前/图内，无需改。

**P3 治理提示**：诊断期间引擎进程被外部重启（00:45:50，PID 36038→47185）且日志以截断方式复用同一路径 `/tmp/engine_server.log`（`>` 而非 `>>`），在途请求被击杀并以 `unavailable/retryable` 透传用户。建议多会话并行时约定重启前互认，且日志追加写/按 PID 分文件。

## 七、产出与边界

- 本次**未产出代码 patch**：无实锤引擎串行化点（判定标准"实锤才修"）；建议项 P2-3/4 为最小修复候选，留待下一轮红绿验证。
- 真实 LLM 消息消耗：10 条（预算 12）；实验脚本与原始输出 `/tmp/m2_ws_experiment.py`（RESULT 行含逐帧类型统计）。
- 日志快照：本次诊断读到的旧引擎日志（含 f1verify-003 86.2s 样本）已被外部重启截断，本报告数字为读取时的即时记录。
