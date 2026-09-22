# P1-3 · 疑似响应重放调查报告（BP-3 复盘）

- 任务卡：P1-3（同会话连续两问，第二问返回与第一问 99.5% 相同答案，用户故意犯错求纠正未获纠正）
- 工作树：wt100（wt100-v3，基于 main@5daea225）
- 结论先行：**不存在服务端响应重放。LOOP1 BP-3 的「99.5% 重放」是评测驱动器
  `real_drive.py` 的两处帧处理缺陷叠加造成的取证假象**；真栈复现矩阵证明第二问
  始终被独立处理。修复落在评测驱动器（产品代码零改动），红→绿测试落地。
- 交付物：`changes.patch`（仅 2 个测试基建文件）、`evidence/replay-matrix.json`、
  `evidence/followup-probe.json`、本报告。

---

## 1. 复现矩阵（真栈，修复后驱动器，账号 northstar_p13_a / northstar_p13_b）

LLM 消耗：7 条 WS 消息（远低于 $0.5 护栏）。每步 deadline 60s（`WS_RECV_TIMEOUT_S`，
纪律上限）；本栈图论讲解类回合实测普遍 >60s（LOOP1 报告 D1b「超 60s 预算未完成」同源），
超时按诚实契约原样记录。

| 场景 | 设计 | 结果 | 判定 |
|---|---|---|---|
| **A 同 session 连续两问**（第二问含明确纠正请求） | S1: Q1「欧拉 vs 哈密顿区别讲解」→ Q2「偶数度⇒连通，对吧？请指出错误」 | `ratio(A1,A2)=0.035`（LOOP1 实测 0.995）；A2 被独立处理，且 A2 排干了 **3 个上一回合残帧**（`stale_full_text`/`stale_meta`/`stale_done`——即 BP-3 误归因陷阱在野外重现并被修复拦截） | **重放不存在** |
| **B 同 session 同问两次** | S2: 同一文本连发两次 | `ratio(B1,B2)=0.6904`，非字节级相同（网关语义缓存 `sessionHasHistory` 跳过 + 引擎幂等键含 request_id，双层均不命中） | 无合法缓存假象，基线成立 |
| **C 新 session 首问即 Q2** | S3: Q2 文本作为新会话第一条消息 | 正常应答（`ratio(A2,C1)=0.1678`），与 A2 同样触发澄清快速通道 | 会话无关、行为正常 |

完整帧级证据：`evidence/replay-matrix.json`（含每次的 request_id/session_id/event_types/
stale_frames_drained/elapsed_s/答案全文）。

## 2. 根因（file:line 级）

证据链：C2/C3 probe JSON 的事件形状差异（C2=`delta×42+usage`，C3=`full_text×1` 且无
ack）→ 引擎日志（`Sparkle-project/backend/logs/grpc_server_2026-09-21_20-39-15_619204.log`
行 518-736，session `ns001-ddf9d2513d6a`）→ 逐层排除（引擎幂等缓存
`state_manager.py:123` 键=(session,request) 双键不碰撞；网关语义缓存
`chat_orchestrator_chatflow.go:526` 有历史即跳过；网关 fallback 无重放
`agent/client.go:329`）。

事故时间线（UTC，与 probe 时间戳逐毫秒对齐）：

1. 11:28:58.657 C2 的 StreamChat 启动（request `44ed2442…`），**graph 执行 71.9s**。
2. 11:29:25.848（恰为 C2 probe 的 elapsed 27.21s 处）C2 自己的 generation LLM hop 完成
   （26.5s，completion_tokens=1203），引擎按设计发出**中途 usage 计量事件**（网关据其做
   流内配额分段，`chat_orchestrator_chatflow.go:797-820`）；graph 随后进 generation_review
   等节点继续。
3. **缺陷①**：`real_drive.py` 旧 recv 循环把任何 `usage` 事件当回合终止（旧 379-381 行
   `usage>0 → break`）→ C2 探针提前返回、答案按 27s 处的 delta 截断，socket 里留下 C2
   未读的 meta/done 及其后继帧。
4. 网关 WS 读泵按连接**串行**处理消息（`chat_orchestrator.go:579` 在读循环内同步
   `return h.handleChatMessage(...)`）：C3 的消息排队 45s，直到 C2 流于 11:30:11.16 EOF。
5. 11:30:11.15 C2 流末 `final_compose` 发出**单一 full_text**（`**结论**`+正文，
   `orchestrator.py:2348` 同型路径），网关照转——被仍在 recv 循环里的 C3 探针读到。
6. **缺陷②**：旧 recv 循环对帧不做 request_id 归因（首个 full_text 即收）→ C2 的
   final full_text 被记成 C3 的答案（`**结论**` 前缀即 difflib 0.995 的全部差异来源）。
7. C3 的真实处理（request `2acd5471…`，11:30:11.19 起，`Sufficiency short-circuit`
   14.2s，日志行 733-736）发生在探针退出之后，**从未被读取**。

根因定位：
- `backend/tests/northstar_eval/real_drive.py` 旧 `WSChatSession.send_message`：
  usage 误判为终止（旧 379-381 行）+ 帧无 request_id 归因（旧 365-371 行）。
- 促成条件（设计内行为，非缺陷）：网关读泵串行 `chat_orchestrator.go:579`；引擎中途
  usage 事件（配额分段依赖）；`final_compose` 单帧 full_text 终局。

## 3. 修复面与统计

仅评测驱动器，**产品代码零改动**（流式协议/事件形状/V13 citations 链/预算面均未触碰）：

- `backend/tests/northstar_eval/real_drive.py` `WSChatSession.send_message` 重写终止语义：
  1. `usage`/`status_update`/`metadata`/`tool_result` 一律过程帧，只计数不终止；
  2. 终止帧 = 本 request_id 的 `full_text`（后到覆盖，与网关持久化 last-wins 语义一致）、
     `error`/`message_nack`/`nack`、或网关流末必发的 `meta`/`done`（缺 full_text 时在
     此锚点降级聚合 delta——原降级路径修正到正确位置）；
  3. request_id 归因：他人 rid 的帧、ack 前的无主帧计入 `stale_*` 排干，返回值新增
     `stale_frames_drained` 供证据审计；
  4. `_chat_step` 证据落盘补充 `request_id`/`stale_frames_drained`（本次调查的最大障碍
     就是 LOOP1 证据缺 request_id）。
- `backend/tests/northstar_eval/test_real_drive_unit.py` +4 项确定性桩测试（复刻事故帧
  序列），合计统计：patch 233 行，+4 测试。

## 4. 红绿证明

```
修复前（红）: 3 failed, 1 passed
  FAILED test_send_message_does_not_misattribute_previous_turn_frames   ← BP-3 复刻，返回 C2 答案
  FAILED test_send_message_usage_is_not_terminal_before_full_text       ← usage 截断
  FAILED test_send_message_delta_fallback_only_at_true_turn_end         ← 降级过早
修复后（绿）: 19 passed（含 4 项新增）
回归: tests/northstar_eval/test_real_drive_unit.py 19 passed
      tests/northstar_eval/test_northstar_eval_gate.py 12 passed
说明: 本 worktree 未生成 app/gen（proto-gen 未跑过的预置状态），tests/orchestration
      收集失败为既有环境缺口、与本改动无关；主仓同族 tests/test_orchestrator_fsm.py
      2 passed 作旁证。产品代码零触碰，回归面结构化为零。
命令: cd backend && SECRET_KEY=test python3.11 -m pytest tests/northstar_eval/ -q
```

真栈验证 A 场景：A1/A2 独立应答（ratio 0.035），残帧陷阱被排干（stale_frames_drained=3），
第二问不再吞掉第一问答案——**重放缺陷修复实证通过**。

## 5. 新发现（超出本卡范围，建议立卡）

### BP-3b · P2：含规划词汇的纠正请求被「规划澄清」快速通道劫持（GP-07 相关）

- 现象：A2/C1（「我复习时总结了一条……对吧？请指出错误」，含 复习/总结 词汇）→ 15-16s
  返回单帧 full_text：「…请确认一下：你是希望我先判断这个图论结论是否正确，还是帮你把它
  安排进复习时间？」——纠正诉求未获直接响应。事件形状（status_update×2+metadata×2+
  full_text×1）与 `_check_sufficiency` 短路路径吻合：
  `backend/app/orchestration/validation_engine.py:234-357`（`_check_sufficiency` →
  NEED_CLARIFICATION/CONFIRMATION → `_emit_fast_interaction` :87-119 单帧 full_text+STOP），
  意图来自 `shadow_prediction_service.predict_intent_only`。新会话同样触发（C1），
  与会话无关、纯意图/措辞驱动。
- 对照：纯知识问法（去掉规划词汇，语义不变，`followup-probe.json` P1）→ 纠正完整送达：
  「错误一：偶数度推不出连通；错误二：欧拉回路还要求连通；反例：两个不相连的三角形」。
  **纠正能力存在，劫持是措辞/意图依赖的。**
- 影响重估：LOOP1 GP-07 fail（「纠正未被记住」）的证据基础（C3/D2 probe）同为本报告
  所述驱动器缺陷污染——C3 的真实回复（澄清问句）从未被读取；D2 的 0.02s 秒回应疑为
  残帧误读。GP-07 的最终定级应在修复后的驱动器上重测。
- 建议：意图分类对「事实断言求确认」类消息降权 planning 信号（复习/总结词面），或澄清
  文案内联直接回答知识判断。涉及意图引擎，风险面大，未在本卡动手。

### 附带观察

- 本栈图论讲解类回合实测 60-82s（A1 81.7s、P1 66.9s、LOOP1 C2 72.5s），60s 步预算
  频繁截断评测答案——评测纪律与栈延迟不匹配，建议北极星轮调高步预算或接受截断并
  全量记录。
- P1 答案文本首尾混入「这一步需要你确认…」「[内容审查: 未通过] 发现 2 个严重问题需要
  处理」片段，疑似多段文案拼接受控但观感差，可另行核查 standard_workflow 的输出装配。

## 6. 收工核查声明

- 已删 `/tmp/p13_matrix.py`、`/tmp/p13_followup.py`（见下）及运行态凭据（本就未落盘，
  密码仅存在于已退出的进程内存）。
- 测试账号 `northstar_p13_a` / `northstar_p13_b` 及其会话数据留在共享开发库——为避免
  对共享活栈做级联删除，未清理（评估：2 个空账号+数条会话行，无害；如需清理可按
  username 前缀 `northstar_p13_` 定位）。
- 无模拟器、无构建产物；主仓未写入任何文件（仅读日志）；改动全部在 wt100 树内；
  未 commit / 未 push。
