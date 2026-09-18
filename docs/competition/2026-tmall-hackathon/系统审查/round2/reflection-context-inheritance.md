# Round2 修复：reflection 上下文继承 + 审查"未通过"噪声根除

> worktree wt6 @ 9b77f7c8 ｜ 2026-09-19 ｜ 状态：已修复，红绿 + 真实链路双验证

## 缺陷回顾（round2 验收实证）

1. **reviewer 几乎每轮判"未通过"**：回复尾部恒带 `[内容审查: 未通过] 发现 1 个严重问题需要处理` 噪声。
2. **reflection_node 重写时没有主生成 system_prompt**：检索材料（Retrieved Documents）、跨会话记忆、用户画像全部丢失，重写"失明"并替换主回复交付用户（mr4 / a2-slim 间歇失败）。
3. 主链其余环节实证健康（决策→检索→水合→prompt 组装→sanitize→纯 LLM A/B 完美引用）。

## 根因（引擎日志实证，非推测）

### 根因 A：审查超时 12s < 审查模型实测延迟 → fail-closed 恒触发

`/tmp/wt1_deep_eval_grpc4.log`（round2 验收引擎日志）逐行证据：

```
04:51:51.859 [ReviewerAgent] Reviewing LLM response: review_fc1bee629b85
04:52:05.647 [ReviewNode] Review complete: decision=needs_refinement, score=0.82, issues=3   ← 13.7s，惊险过线
04:56:08.447 [ReviewerAgent] Reviewing LLM response: review_9acd7e22f072
04:56:21.078 [ReviewNode] Review complete: decision=failed, score=0.45, issues=3             ← 12.6s
04:50:04.346 [ReviewerAgent] Reviewing LLM response: review_8bc138770833
04:50:34.350 [ReviewerAgent] Review failed: TimeoutError:                                    ← 撞 30s 超时
04:50:34.351 [ReviewNode] Review complete: decision=failed, score=0.00, issues=1             ← "1 个严重问题"即此
```

- `REVIEWER_LLM_TIMEOUT_SECONDS` 默认 **12s**（settings.py），而审查模型（qwen3.8-flash）常态延迟 **12-14s**，wt6 实测还出现过 **41.8s**（reasoning 档被路由为审查模型时更慢）。
- 超时 → `asyncio.wait_for` TimeoutError → `review_llm_response` 的 fail-closed 分支（R6-P0-3）：`decision=failed, score=0.00, **恰好 1 个** critical("审查过程出错")、requires_reflection=True`。这与验收里"每轮未通过 + 恒定 1 个严重问题"逐字吻合——**是系统故障，不是内容真有问题**。

### 根因 B：审查 LLM 严重度通胀

审查成功时（score=0.82）也会贴 1 个非 safety 类 critical + 2 个 warning。`_parse_review_result` 的确定性判定要求"无 critical"才 passed → needs_refinement → 永不通过 → 反思重写一条本已合格的回复。

### 根因 C：reflection_node 从未真正执行过（关键新发现）

真实聊天图（`standard_workflow.create_standard_chat_graph`）用的是**自研 `WorkflowState` dataclass**（只有 `messages/context_data/next_step/errors/is_finished/trace_id` 字段），节点返回值被引擎 `_merge_context_data` **合并进 `context_data`**。因此：

- `generation_review_node` 返回的 `review_context` 实际落在 `state.context_data["review_context"]`（`reflection_condition` 早有同类回退读取，行 3312-3316）；
- 但 `review_nodes.reflection_node` 只读 `getattr(state, "review_context")` —— **不存在** → 恒走 `"No review context, ending reflection"` 空转（wt1 与 wt6 实测日志均现此行）；
- 同理 `user_id`/`session_id` 也只在 `context_data`。

即：在本提交上 reflection 链路是**死代码**，"重写失明"的上下文继承问题被上游断点完全遮蔽。

## 修复内容（最小侵入，6 文件）

| 文件 | 变更 |
|---|---|
| `app/config/settings.py` | `REVIEWER_LLM_TIMEOUT_SECONDS` 12 → **45**（对齐 `ReviewerAgent.DEFAULT_LLM_TIMEOUT_SECONDS`，覆盖实测 41.8s P95+） |
| `app/agents/reviewer_agent.py` | ① `_parse_review_result` 显式处理 `chat_json` 返回 `None`（此前 AttributeError 掩盖真因，仍 fail-closed 但错误可读）；② **严重度通胀校准**：总分 ≥ 0.7（通过线）时非 safety 类 critical 降级 warning——0.82 分与"必须修复的严重问题"自相矛盾；**safety 类 critical 永不降级** |
| `app/agents/graph/state.py` | `ReviewContext` 增加 `generation_system_prompt` 键 |
| `app/agents/standard_workflow.py` | `generation_node` 在 context budget 组装完成后持久化 `state.context_data["generation_system_prompt"]`（含检索材料 + 跨会话记忆 + 画像的最终 system_prompt） |
| `app/agents/graph/nodes/review_nodes.py` | ① `generation_review_node` 把 `generation_system_prompt` 随 review_context 携带；② **reflection_node 桥接**：review_context / user_id / session_id 从 `context_data` 回退读取（对齐 reflection_condition 的既有回退模式）——reflection 首次在真实图上可执行；③ reflect 调用的 `context` 增加 `generation_system_prompt` |
| `app/agents/reflection_agent.py` | `_execute_fix` 组装 system 消息时，若 context 带 `generation_system_prompt` 则以"原始生成上下文（修正时必须继承，禁止丢弃）"段落注入，并明令禁止"没有看到资料正文/没有相关记忆记录"式拒答 |

## 红绿证据（`backend/tests/unit/test_review_reflection_fix_r2.py`，9 用例）

- **红**（stash 修复后跑）：5-6 failed —— 含注入断言、context_data 桥接断言、通胀校准断言、超时默认断言、None payload 显式 fail-closed 断言；3 个回归守卫（safety critical 不降级、低分仍 failed、无继承上下文时不注入空段）基线即绿。
- **绿**（恢复修复后跑）：**9/9 passed**；相邻回归 `test_reflection_agent_chat_binding / test_reviewer_agent_phase62 / test_reflection_kill_switch` 等 **17/17 passed**（`test_review_skip_logic`、`test_reflection_agent_user_id` 的 4 个失败在基线 9b77f7c8 上同样失败，与本修复无关）。

## 真实链路验证（独立栈 :8005 API + :50052 gRPC + :8081 网关，收工已杀净）

1. **WS 全链（guest → 上传 → confirm → processed → 提问）**：
   - 检索水合正常：`GraphRAG 完成: vector=1`，`Hydrated document context: passed=1`，system_prompt 5634 chars；
   - **审查通过无噪声**：`Review complete: decision=passed, score=0.86`（审查耗时 **41.8s**——旧 12s 配置下必然又是一轮"未通过+1 个严重问题"噪声）；回复尾部无 `[内容审查` 噪声（修复前同链路 100% 复现噪声）；
   - DB 取证：chunk 含全部材料正文（环状磷光/18 摄氏度/避光保存），主生成仍偶发"未看到正文"属 HEAD 提交自身在修的 qwen3.8-flash 注入材料无视问题（mr4 残留），不在本修复范围。
2. **真实 LLM reflection 重写探测**（`reflect_and_fix` + 真实 generator，复现"失明重写"场景）：
   - 修复前形态：重写调用 system 仅有内容优化专家模板，材料不可达；
   - 修复后：重写**逐字引用材料原文**，5 个材料关键词全命中（磷光/荧光/450/18 摄氏度/避光），`still_blind=False`；
   - 第 2 轮复审撞 45s 超时（score 0.00）触发 degraded-revert 保护，`final_content` 保留第 1 轮有据重写——best-content 保护有效。

## 遗留与移交

1. `fixed_response` 在本提交上**无交付消费者**（`_build_final_response` 只取最后一条 assistant 消息）：reflection 修正结果落在 `context_data/review_context` 但不替换交付内容。若主仓（a755e09d+）已有交付接线，无需处理；否则需在交付层把 review_context.status=passed 且 reviewed_content 非空的情况写回消息流。
2. 审查延迟高（12-42s）且在生成完成后同步执行，是回复尾部延迟的主要来源；后续可考虑异步审查或流式后置。
3. `test_review_skip_logic` / `test_reflection_agent_user_id` 4 个失败为基线既有，建议另行清偿。
