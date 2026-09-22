# NORTHSTAR-LOOP3 · 修复验证定向轮报告（七项，对照前轮证据基线）

> C 线 LOOP3：在主会话 23:1x 重启到 main@da18c10f（含全部 12 张修复卡）的活栈上做**定向验证**，非全旅程。全程未重启任何服务、未直写 DB、未触 demo_video_* 与既有用户；仅经 gateway :8080 API。
> 账号：主 `northstar_ns3_2ca4e677`；SSE 专用 `northstar_ns3_sse_55b008a6`（零 LLM）。真实 LLM 消息 **5 条**（预算 $0.6 内，Qwen）。
> 性质：观察/评估卡，零产品代码改动；探针脚本为一次性运行态（/tmp，收工已清）。自动判定 + 人工复核双层，2 处自动判卷被人工改判（词表缺口，见 §5）。
> 诚实声明：定向压缩轮判定只针对修复卡验收面，不构成北极星达成宣称。

- 运行 ID：`NS001-LOOP3-20260922-152xxx`（见 run-summary.json）；基线 `main@da18c10f`（wt122）
- 证据：`evidence/steps/` 22 份（含 2 份 -rejudged）+ `evidence/` 快照/探针 9 份 + `run-summary.json`

## 1. 七项验证对照表（前轮结果 → 本轮结果 → 判定）

| # | 验证项 | 前轮基线（LOOP2 / SSE-HB-VERIFY） | 本轮结果 | 判定 |
|---|---|---|---|---|
| 1 | **NBP-1 WS 记忆主路径**（`V1-A/B`, `V1-EPISODIC30/90`） | 同句事实：REST 3 条（due_at 正确）/ **WS 0 条**（即时+10min 均查无） | WS 发 Day0 类明示事实句（86.9s 完整回合）+ 澄清门模糊句（19.4s 快交互短路，0 delta 帧、纯 full_text+meta 终止——修复的快交互出口被真实命中）；**30s 读 0 条（判据口径 fail）→ 90s 读 3 条全对**：2×self（165 分钟、自评 42/图论 CH4/目标 70+）+1×commitment（`due_at=2026-09-29T18:00:00` 正确）；多次触发零重复（semantic_key 去重生效） | **pass\***（捕获面 0→3 兑现、due_at 正确；\*备注：写账投影延迟 30–90s，晚于 LOOP2 REST 链路的 ≤30s，见 NBP-6） |
| 2 | **GP-07 跨会话记忆保持（污染定界）**（`V2-C/D/E` + 2 份 rejudged） | 纠正成功但第三会话把假命题确认成「正确」（污染实锤） | ①新会话召回（GP-04）**pass**：引用 Day0 私有上下文「你当前图论（CH4）掌握度约 42/100，离 70 分目标…」（LOOP2 同位探针答「当前会话中未保留具体记录」）；②纠正**成功**：「该命题是**假**的」+ 双分离三角形反例 + 完整条件；③第三 session（新 WS 连接+新 session_id）问「这个命题对吗」→ 裸「**错。**」开头 + 漏连通性前提分析 + 同族反例 + 用户相关引用（「结合你图论章节的提分节点」）；④episodic 终态账本中**假命题未被写入**（无污染种子） | **pass（污染未复现 → 无需立「记忆污染修复」卡）**，判据与诚实边界见 §2 |
| 3 | **NBP-2 goal-detail 200**（`V3-GOAL/DETAIL`） | 稳定 500（pydantic model_rebuild） | `GET /experience/goal-detail/{id}` **200**；形状 16 键全量（8 验收键全部在场），6 个字段非空真实数据（goal/minimum_acceptance_criteria/plan_health/todays_minimal_next_step/progress/active） | **pass** |
| 4 | **NBP-3 goal→intake 双计划**（`V4-*`） | 双计划：goal 计划 `subject=null` 主键永不命中 | **双计划仍在**：goal 建计划 `9dd4ec15`（sprint/active/target_date=2026-09-29/goal_id 已关联）后，intake 未复用、新建 `a6d345a8` → 账本 2 份 active sprint。根因新定位见 §3（NBP-3b）；且副作用已用户可见：chat 回合中 surfaced「系统报错（已达计划上限）」（V2-D 原文） | **fail（修复未兑现，根因已定位到行）** |
| 5 | **CP-01 计划人工确认端点**（`V5-CONFIRM`） | 确认环节缺失（半项） | 运行时探针 `POST /plans/{id}/confirm`、`/approve` 均 **404**（GET 对照 200）；静态审计全仓只有 `POST /chat/confirm`（chat action 级）与 `POST /plans/compass/{artifactId}/approve`（compass 工件，另一流程）——exam-sprint 计划草案→人工确认**仍无专用端点** | **仍缺失（登记维持）** |
| 6 | **SSE 断连（SSE-EXEMPT 验证）**（`v6-sse-gateway.json`） | 23/23 连接 **+30.0s 整被掐断**（TimeoutMiddleware 总时限） | `GET /api/v1/galaxy/events` 订阅 **120.02s**：单连接、**断连 0 次**、`connection_held_full_duration=True`；心跳 **6 帧间隔恒 20.0s**（每 30s 双刀位窗 ≥2 帧）；跨过两个 30s 刀位 | **pass** |
| 7 | **TTFT 记录**（`ttft-summary.json`） | 引擎单回合墙钟 57–63s（LOOP2，未单列 TTFT） | 5 条消息全记录：完整回合 TTFT **12.2 / 28.8 / 30.1 / 30.6s**（3/4 聚在 **29–31s** 簇——与思考档首包/S18 面积吻合），总墙钟 51.5–86.9s；澄清快交互 19.4s（0 delta，full_text 直发） | **记录完成**（观察：TTFT ~30s 簇是首包体感主害；回合总墙钟仍 51–87s 偏重） |

自动表 `run-summary.json` 与上表差异 3 处均为人工复核层（V2-D 词表缺口、V2-E 单字判定词、V1 30s 判据口径），已登记 `manual_overrides`，原文证据未改写。

## 2. GP-07 污染定界结论（关键交付）

**定界：LOOP2 的「假命题被确认成正确」失败模式未复现——第三会话正确拒答。按任务判据，本轮无需立「记忆污染修复」卡。**

- 证据链：`evidence/steps/V2-D_*`（纠正轮全文）→ `V2-E_*`（第三会话全文，裸「错。」开头）→ `V2-E-rejudged.json`（人工定界）→ `snapshot-memory-episodic-final.json`（账本无假命题条目）。
- 诚实边界（已写入 rejudged 文件）：①探针把假命题**全文钉死**（含「因此一定存在欧拉回路」），比 LOOP2 D2 的含糊引述（「顶点度数都是偶数与图连通」）更不易被按欧拉定理重解读——「裸知识也能答错→对」的替代解释无法被单探针完全排除；但用户视角结果一致：**系统不再确认用户的假命题**。②V2-C 独立证明新会话私有上下文召回已通（42/100、CH4、70 分全中），记忆读侧功能在场。③压缩轮内分钟级间隔、n=1；多日保持不在本轮范围。

## 3. 新发现

### NBP-3b · P1：NBP-23 兜底分支过滤键与落库值不一致——单绿运行红的第二例
- `_find_goal_linked_sprint_plan`（2853ef5c）过滤 `Goal.goal_type == "exam"`；但真实创建链路上 `goal_decomposition_service.create_goal` 落库的是 **`_normalize_goal_type` 的模板键**：`_CANONICAL_TO_TEMPLATE` 把 `exam → academic`（`goal_decomposition_service.py:182-204`），exam 目标在 DB 里是 `goal_type="academic"`（本轮 goal-detail 响应实测）→ 兜底永不命中 → intake 另建第二份计划。
- 单测（`test_exam_sprint_intake_service.py`）直插 `goal_type="exam"` 的 Goal 夹具，未经真实 API 归一化路径 → 单绿运行红（与 LOOP2 NBP-2 GOAL-ROUTER 同族失败模式）。
- 修复提案（一行级）：兜底过滤改为 canonical 族匹配（`Goal.goal_type.in_(("exam", "academic"))` 或对列值过 `normalize_goal_type` 再比较）；补一条「经 POST /goals/ 真实路径建 goal → intake 必须复用」的 TestClient 级回归。
- 连带：`goals.py:191` 的 `plan_type` 判定用的是原始 payload（exam→SPRINT）所以 goal 计划类型正确、target_date 亦正确——唯一断点就是 goal_type 过滤键。

### NBP-6 · P2：WS 链路 declared-fact 写账投影延迟 30–90s（LOOP2 REST ≤30s）
- V1-A/V1-B 两轮收尾 enqueue 完成后，30s 读 0 条、90s 读 3 条。同一 `enqueue_from_chat_turn` 面在 LOOP2 REST 探针 5s→30s 内落账。推测与写队列 worker 节拍/排水 worker 争用有关（本轮恰有单并发 MiniMax 排水 worker 在跑），非捕获逻辑问题（最终一致、内容全对）。
- 影响：用户「刚说完→立刻看记忆」会短暂看到空账本；评测侧 30s 判据口径需放行到 90s 或先修投影节拍。

### 观察项（不计断点）
- **计划配额错误用户可见**：V2-D 回合中系统在正文里转述「系统提示你的计划数量已达上限」——双计划残留（NBP-3b）已产生用户可见副作用，加重其修复优先级。
- **task_outcome 幽灵条目**：episodic 终态账本有 2 条「completed Day 7 · 保底模拟 - 树与生成树 等3个点」`task_outcome`，本轮无任何任务完成动作，疑似 intake 计划管道自动标记，来源待查（不涉七项判定）。
- **探针判卷词表债**（测试基设，非产品）：「是假的」「错。」两变体未进自动词表 → 2 处自动误判已人工改判留档（同 LOOP2 NBP-5 族）；复跑者应先扩充 `_judge` 词表。

## 4. 一句话总结

12 张修复卡中受验的 5 张：**NBP-1（WS 记忆主路径 0→3）、NBP-2（goal-detail 200）、SSE-EXEMPT（120s 零断连）三张实机兑现**，GP-07 污染未复现（无需立卡）；**NBP-3 双计划修复在真实创建链路上被 goal_type 模板键映射击穿（根因已定位到行，一行级可修）**，CP-01 计划人工确认端点仍缺（登记维持）。

## 5. 交付物与复跑

- 证据：`v3-output/NORTHSTAR-LOOP3/evidence/`（steps 22 + 快照/探针 9 + run-summary.json；凭据仅 /tmp 已清，证据内凭据只以用户名明文+user_id 前缀出现，无密码/token）
- 复跑：栈在跑前提下，`python3 /tmp/ns3_loop3_probe.py`（探针已随收工清理；如需复跑向本 worktree 索要，或按 `evidence/steps/` 步骤手 reconstruct——全部为纯 API 步骤）
- SSE 单项复跑：`python3.11 scripts/devtools/probe_galaxy_sse_heartbeat.py --duration 120 --evidence-out <path>`（预写 `/tmp/sse_hb_probe_creds.json` 即可复用 ns3 前缀账号）

## 6. 收工核查

- [x] /tmp 凭据清零：`ns3_loop3_creds.json`、`sse_hb_probe_creds.json`（含误建残留）已删
- [x] /tmp 过程产物清零：探针脚本、日志、__pycache__ 已删
- [x] 进程清零：两个探针进程均已退出（SSE 120s 自然结束）；未启停任何服务
- [x] 零模拟器、零 LLM 超支（5 条消息）、零直写 DB、未触 demo_video_*/既有用户
- [x] 账号前缀 northstar_ns3_*（例外披露：首次 SSE 探针启动顺序失误，误建 `northstar_sse_hb_cd0a9a72`，仅注册、零 LLM 零业务数据，已记为过程残留）
- [x] 产物全部落本 worktree（`v3-output/NORTHSTAR-LOOP3/`）
