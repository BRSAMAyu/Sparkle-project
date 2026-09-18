# deep_analysis 新栈复验（qwen3.8-flash 全 tier · 四路径真调评测）

- 日期：2026-09-19 01:57–02:22（本机真服务，全程未重启任何进程）
- 仓库 HEAD：91f8f1cd（四前置提交均在 HEAD：10c741a7 阿里栈切换 / 918b241d F-1 deep_analysis→MAX / aabc7f1e 免费层钳制 / d859c194 statechart 迭删修复）
- 评测员：deep_analysis 新栈复验（WS 串行真调，实际消耗 LLM 消息 7 条，预算 8 内）
- 凭据：游客 token（`POST /api/v1/auth/guest`）、flame=1 用户 `smoke_android_01`（a36b3431）、flame=20 用户 `spark_friend_3`（9756c943，dev JWT 全 claims 签发，经 ticket+WS 正常链路）；WS 经 `/api/v1/ws/ticket` → `ws://…/ws/chat?ticket=…`
- 引擎运行版本实证：运行中进程的 `_init_with_router:342`（llm_service）与 `_select_by_policy:1105`（llm_router）行号与 HEAD 源码逐行吻合 → **运行代码 = HEAD backend**；日志多实例轮换见附录
- 引擎配置：`LLM_PROVIDER=qwen`，max/plus/standard/fast 四层 `DASHSCOPE_*_MODEL` 全为 `qwen3.8-flash`（27 个 model configs 中仍注册 legacy 的 glm-4.6/deepseek-v4-pro 键，见 P1）

## 路径 × 结果矩阵

| # | 路径 | 用户/档位 | 路由证据（引擎日志） | TTFT/总时长/字数 | 结果 |
|---|---|---|---|---|---|
| 1 | deep_analysis 深度档（B树vsB+树决策框架） | 游客(flame15→is_pro) | `chat_mode=deep_analysis, workflow=deep_analysis_workflow` + `reason=mode_strategy:forced:deep_analysis` + **`generation → qwen3.8-flash (强制tier=max [$0.0010/1k, tier=pro])`** | 23.2s / 37.4s / 307 | ✅ F-1 真实路由 MAX |
| 2 | standard 对照（ACID） | 游客 | `reason=unified:chat \| unified_mode:standard` + **`generation → qwen3.8-flash (强制tier=plus [$0.0004/1k, tier=plus])`**；标准层 `dashscope_standard_thinking` 仅用于回答后_aux（标题/摘要） | 3.5s / 16.8s / 190 | ✅ 通（但主生成是 plus，非 standard_thinking，见 P3） |
| 3 | plan-intent + 工具执行（考研40天计划） | 游客 deep_analysis 档 | `intent=task, confidence=1.00, mode=langgraph` → `Plan ready: create_plan, generate_tasks_for_plan` → `tool_execution`（`create_plan success=True, 31ms`）→ **`execution_review` 节点执行，无迭代删崩溃** | 11.0s / 41.3s / 405 | ✅ d859c194 新栈首验通过；plan 真建、task 未建（确认门控） |
| 4 | 免费层钳制组合（flame=1 + deep_analysis） | smoke_android_01(free) | 策略层钳制齐发：`free_tier_downgrade: pro -> fast (agent=generation)` 等 ×10；**但主生成 `强制tier=max` 未钳制、以 tier=pro 执行** | 27.5s / 41.5s / 296 | ⚠️ 半通：组合存在缺口（见 P2-A） |
| 5 | pro 无钳对照 ×2（B+树 / 微服务vs单体） | spark_friend_3(flame20) | 同 #1，`强制tier=max`，无 downgrade 标记（正确） | 21.2s/35.8s/327；15.3s/29.2s/378 | ✅ 对照成立 |

标准档普通消息补充（g_plan，standard 档"帮我制定考研40天计划"）：`intent=task conf=1.00` 识别成功，但 sufficiency 门控走澄清式追问（43 字反问），工具不触发——与 deep 档行为差异见 P3。

## 四路径结论

### 1. deep_analysis 深度档（F-1 复验）— ✅ 已修复
- 918b241d 前的 F-1 缺陷（reason 档 0 次触达 v4-pro）在新栈复验为**已修复**：`chat_mode=deep_analysis` 显式走 `workflow=deep_analysis_workflow`，主生成强制 `tier=max`（4/4 次 deep_analysis 消息一致）。
- `DEEP_ANALYSIS_FORCE_FAST_TIER=False`（settings.py:609），逃生阀未启用；tier 元数据 max=$0.0010/1k（模型字符串同为 qwen3.8-flash，分层为纯路由/计费元数据）。
- 质量人工评分：**7/10**（B+树题，3 个身份三次作答结构一致）——五段式（关键结论/类比/反例/易混淆点/口诀）技术正确、可操作；扣分：篇幅 ~300 字，无对比矩阵/复杂度量化，"深度"体现为框架化而非纵深。微服务 vs 单体题 **7.5/10**（六项判断框架+明确默认选型，贴合毕设场景）。
- statechart 轨迹：context_builder → retrieval → router → generation → generation_review → reflection → __end__。

### 2. standard 档对照 — ✅ 通，⚠️ 层路径与预期不同
- 主生成强制 **plus 层**（非任务书预期的 standard_thinking）：同为 qwen3.8-flash，但 tier 路径差异清晰可辨：deep_analysis→max($0.0010/1k) vs standard→plus($0.0004/1k)；`dashscope_standard_thinking`(standard 层) 只承担回答完成后的标题/摘要 _aux 调用。
- TTFT 3.5s / 总 16.8s，与 deep 档（21-28s TTFT）差 6-8 倍——档位延迟分层明显。
- 质量 **7/10**：ACID 四要素准确、结构清楚、按"简单说明"收敛篇幅；与 deep 档的质感差异主要在决策框架而非事实密度。

### 3. plan-intent + 工具执行路径（d859c194 新栈首验）— ✅ 无崩溃，工具真建 plan
- 触发形态：plan-intent 消息 **必须叠加 deep_analysis 档**才进工具执行路径（standard 档同消息只澄清，符合 sufficiency 设计）。`intent=task, confidence=1.00, risk=medium, mode=langgraph`。
- 执行链：`Plan ready: create_plan, generate_tasks_for_plan`（2 tool calls）→ `tool_execution` → `Recorded tool execution: tool=create_plan, success=True, time=31ms` → `execution_review_node invoked` → 路由 generation(max) → 完成。**全程无 "dictionary keys changed during iteration"、无 RuntimeError**——d859c194 修复后 execution_review 合并路径首次真调验证通过。
- 工具落库实证：plans 表新增 `50489226-677e-…`（"帮我 一个考研40天 并创建任务 英语386分学习计划"，created_at 18:09:15.914 UTC ≡ 02:09:15.914 本地，与日志 `02:09:15.940 success=True` 吻合）。**task 0 条**：第二个工具 `generate_tasks_for_plan` 未执行，回复以"回复'确认创建'我就落地"收尾——任务创建是用户确认门控，单条消息内不闭环（见 P3）。

### 4. 免费层钳制组合行为 — ⚠️ 半通（组合缺口）
- 钳制标记真实出现（aabc7f1e 生效证据）：`[LLMRouter] free_tier_downgrade: pro -> glm_batch (agent=code_agent)`、`pro -> fast (agent=deep_analyst/error_analyst/exam_oracle/galaxy_guide/generation…)`、`plus -> fast (execution_assistant)` —— `_select_by_policy` 策略候选层钳制全量生效。
- **缺口**：同请求内 deep_analysis 主生成 `强制tier=max` 未被钳制，以 tier=pro 真实执行。离线直调 HEAD 同一代码路径：`FREE + force MAX => 强制tier=max | free_tier_downgrade(max->fast) [tier=fast]`——**钳制逻辑本身正确（与上轮 aabc7f1e 直调结论一致），WS 全链路上 contextvar `request_user_tier` 在状态图节点执行上下文中未达/失效**（策略层钳制发生在请求上下文 02:12:19.885，节点内 LLMService init 在 02:12:20.266，两层行为不一致）。三修复组合行为在真实链路上**未完全成立**。
- 附带重要口径发现：**"游客"≠免费层**。新游客种子直接 flame_level=15（93/115 用户为 15）→ 网关 `IsPro = flame_level>=3` → 引擎收到 is_pro=true，钳制被正确跳过。免费层信号与游客身份解耦，is_pro=false 需 flame<3（现库仅 14 个 flame=1 账号）。

## max 档 TTFT 分布（qwen3.8-flash）

| 样本 | 档位 | 客户端 TTFT（首内容 delta） | 总时长 | 引擎 first_chunk_after（reasoning） |
|---|---|---|---|---|
| g_deep1 | max | 23.17s | 37.39s | 666ms |
| f_deep1 | max（未被钳，见 P2-A） | 27.54s | 41.54s | 746ms |
| p_deep1 | max | 21.21s | 35.83s | ~0.7s |
| p_deep2 | max | 15.29s | 29.22s | 686ms |

- n=4 分布：**15.3 / 21.2 / 23.2 / 27.5s，中位 ≈22.2s**，极差 12.2s——**无 M-2 式 >60s 尾暴**；provider 层首 reasoning 块稳定 0.67-0.75s（全窗口 8 个样本 0.67-1.2s）。
- 客户端 TTFT 与引擎首块相差 20s+：差额 = qwen3.8-flash 思考期（reasoning 流不转发为内容 delta）+ review 链。系统性尾巴另有来源：**每轮 deep_analysis 固定烧 ~12s 在注定失败的 reviewer 调用上**（见 P1），总时长被抬 12-20s。

## 问题清单

### P1
- **R-1 reviewer 仍路由已退役的 deepseek-v4-pro**：`reviewer → deepseek-v4-pro (Agent策略路由: reviewer -> deepseek_reason [tier=max])`，4/4 次 deep_analysis 全部 `Review failed: (空)`（恒 ~12s）→ `decision=failed, score=0.00` → reflection。10c741a7 栈切换只清了 `.env` 模型名（LLM_REASON_MODEL_NAME=qwen3.8-flash），reviewer agent 策略/27 个 model configs 注册表中的 legacy `deepseek_reason` 键未清。代价：每深度轮 +12s 死延迟、质量门形同虚设、review 元数据污染前端。

### P2
- **P2-A 免费钳制 × F-1 组合缺口**：强制 tier 路径在 WS 状态图节点上下文中绕过 `request_user_tier` 钳制（离线直调同代码钳制正确）——免费用户 deep_analysis 实际以 max 层执行，成本护栏对最贵路径失效。
- **P2-B 免费层信号口径**：游客种子 flame_level=15 → is_pro=true，"游客=免费层"不成立；若比赛叙事依赖"游客被降级保护"，当前现网行为相反。

### P3
- **P3-A standard 档主生成强制 plus**，standard_thinking 仅做回答后 _aux——"standard=standard_thinking"的预期口径不成立（可能与首触快响/平衡策略有关，建议对齐文档或配置）。
- **P3-B plan-intent 任务一步不闭环**：`generate_tasks_for_plan` 不执行，需用户二次确认；"制定计划并创建任务"单轮语义未满足（产品上或为有意门控，建议确认）。

## 附录：评测窗口环境扰动（非本评测所为，全程未重启服务）
- 引擎被外部 restore 循环轮换 3 次（01:48 实例→01:53:25 实例→02:04:39 实例；另存在并行 wt2 实例），日志分散于 `backend/logs/`、`logs/`（仓库根）、`/tmp/wt2_grpc.log`。
- 网关重启 ≥1 次（02:04 前后 502 一次 + guest_id→user 映射churn：同一 guest_id 先后映射 5940c05a/8f733b17/9c77b5c6/12f62e32 四个用户）。
- 并行评测员（memrag02-* 会话，user 07ced89c）同窗运行；本报告全部路由证据按 **session_id + user_id + 时间戳**三重归属核验。
- 本评测 WS 消息 7 条（另 2 次票据/网关层失败不计 LLM 消耗），日志 grep 控制在每路径 ≤20 行。
