# NORTHSTAR-LOOP2 · NS-001 第二轮真实闭环报告（修复后活栈复跑 + LOOP1 差分）

> C 线北极星场景第二轮**真实驱动**：在主会话 21:09 重启到 main@e43fde1e 的活栈上（gateway :8080 / engine gRPC :50051 / FastAPI :8000，全程未重启服务）复跑 NS-001 压缩轮，重定级全部检查点与增益证据，给出 LOOP1→LOOP2 修复效果差分。
> 本轮性质：**观察/评估卡**——不改产品代码；对驱动器 `real_drive.py` 的改动属测试基设（ns2 前缀/状态文件参数化、新增 B1b/B2b/B3-2/B3-2v/B3-3/B5b/B5b-2/B6-2/B7-2/day1chat/day1settle 步、判卷 confidence 小写修正、C2/C3/D2 措辞纯知识化、双臂 90s 预算、day0fix/day1settle 读模型结算相）。
> 诚实声明：API 压缩轮**永远不能宣称北极星达成**；CP-98/99 按冻结规则一律 unsupported。本轮结论只代表「修复后基线」。

- 运行 ID：`NS001-LOOP2-20260922-131844`；基线 `main@e43fde1e`（wt109）
- 主账号：`northstar_ns2_3bf60665`（user_id `490e5785…`）；对照账号（GP-04 盲臂）：`northstar_ns2_ctrl_7b35d181`；另用一次性账号 `northstar_ns2_probe_*`（2 个）做判别探针后弃置。未触碰 demo_video_* 与任何既有用户；全程仅经 API，未直写 DB。
- 真实 LLM 消息：8 条（预算 24：B1 onboarding、C2 答疑×2（首跑 60s 客户端截止早于引擎回合墙钟，90s 重跑成功）、C3 纠正×2（首跑被确认门截留，重跑成功）、D1a 主臂、D1b 对照臂、D2 追问）。费用在 ~$1 上限内（Qwen）。
- 证据：`evidence/steps/` 44 份 + `evidence/` 快照/gp/probe 18 份 + `run-summary.json`。凭据只存 `/tmp`（600，收工已清）。

## 1. 11 检查点 LOOP1→LOOP2 对照表（人工诚实定级：2 pass / 2 fail / 5 blocked / 2 unsupported）

> 注：`run-summary.json` 里自动表为 1 pass / 2 fail / 6 blocked / 2 unsupported——其 CP-00 fail 来自 B5b（判卷后即时读，被读模型延迟污染）；人工复核以 B5b-2 结算步为准上调。CP-03 同理以结算快照复核维持 pass。两处均已标注。

| 检查点 | LOOP1 | LOOP2 | 变化与归因（→修复卡） |
|---|---|---|---|
| CP-00 摸底分入账且考纲→星图映射 | **fail**（诊断 422，BP-1） | **pass\*\***（有偏差备注） | 离散数学 22 题题包上线：B4 生成 15 题 200、B5 判卷 13.2 分（pass_probability 0.003，瓶颈正确指向「图的基本概念/欧拉图与哈密顿图」）、**8 个考纲主题节点带 mastery 落星图**（命题逻辑 25、二元关系 50，其余 0 解锁）→ **P0-1** 生效。偏差：①落图走「同名节点解析」而非 dm.* 规范 sprint-pack id（`_resolve_node_id_by_name` 命中在前，`_ensure_topic_node` 的 dm.* 路径未触发）；②章级 8-10 节点而非剧本 24 细粒度节点（P0-1 卡已自述留待后续）；③落图读模型有分钟级延迟（见 NBP-4） |
| CP-01 计划定向且经人工确认 | **fail**（intake 非幂等 403+双计划；确认环节缺失） | **fail**（失败面收窄） | 同表单复跑 200 且返回**同一 plan_id**（ad361a54 复用，不 403 不新建）→ **INTAKE** 修复的 intake-vs-intake 幂等生效；但 **goal→intake 双计划仍在**（goal 建的 plan `subject=null`，`_find_reusable_sprint_plan` 按 `Plan.subject` 匹配永不命中→两份 sprint 计划并存，见 NBP-3）；「计划草案→人工确认」端点仍不存在 |
| CP-02 quiz 轨迹非降 | blocked | blocked | 压缩轮仍仅 1 个 quiz 时点（诚实降级，不变） |
| CP-03 错题 100% 落本且触发 mastery 同步 | **fail**（同步半程失败，galaxy 恒 0） | **pass\*\***（备注） | 错题落本 200×2 + review 提交 200；**mastery 同步首次实证移动**：结算星图 4 节点各 +25（二元关系 50→75、命题逻辑 25→50、图的基本概念/谓词逻辑 0→25）、任务节点解锁（unlocked 8→10）→ **P1-5**（吸收器第 4 环）生效。备注：错误 review 的「下修」方向未被隔离验证（与任务完成的上行混在同一窗口）；study_minutes 仍恒 0 |
| CP-04 次日计划自适应 | blocked | blocked | 本轮无 Day2（诚实降级，不变） |
| CP-05 复习命中率 ≥0.7 | blocked | blocked | 仅拉取复习队列（诚实降级，不变） |
| CP-06 加权覆盖 ≥0.8 | blocked | blocked | 需 Day6（诚实降级，不变） |
| CP-07 提分 ≥+15 | blocked | blocked | 需 Day7 模拟考（诚实降级，不变） |
| CP-08 遗忘率 ≤0.2 | blocked | blocked | 需 Day10 重测（诚实降级，不变） |
| CP-98 认知负担自报 | unsupported | unsupported | 冻结规则（不变） |
| CP-99 全真墙钟 | unsupported | unsupported | 冻结规则（不变） |

**顺带修复（未在预告清单）**：LOOP1 BP-4 跨账本不一致（ledger=2 vs dashboard=0）本轮对账成立 **ledger=1 == dashboard=1**，且 sprint headline 变成真实数据：「你用了 1 天，完成了 1 项任务，二元关系 从 50 分提升到 75 分。」（LOOP1 是「完成了 0 项任务、current_score=0.0、delta=-42.0」）。归因最可能为 **B1-A（S7 今日任务单一事实源）+ P1-5（真实 mastery 数据可供聚合）**，非预告宣称，实测对账成立（`probe-sprint-ledger-reconcile.json`）。

## 2. 四项增益重定级（LOOP1 → LOOP2）

| 靶子 | LOOP1 | LOOP2 | 依据 |
|---|---|---|---|
| **GP-04 检索/记忆信息增量** | 无正向证据（main arm fail；对照臂 60s 不完整，差分不闭合） | **仍无正向证据（本轮差分首次闭合，结论为中性偏负）** | 双臂均在 90s 内完成（预算修复后差分可判）。主臂新会话答：「关于你提到的之前反馈的薄弱点，**当前会话中未保留具体记录**」——私有上下文未 surface（人工复核定 fail；自动启发式判 pass 属反记忆词表漏洞，见 NBP-5）；对照臂为同质量百科回答。双臂内容差 ≈ 0。根因指向 NBP-1（WS 主链路记忆写账断裂）：Day0 事实从未入 episodic，召回侧无可召回 |
| **GP-07 记忆复用（纠正保持）** | fail（纠正被劫持未发生；上轮证据被驱动器污染） | **fail（本轮干净取证，失败模式升级为「纠正成功但不能保持」）** | 纠正本身首次成功：C3（纯知识措辞）获完整纠正——「命题为假」+ 双分离三角形反例 + 完整判定条件（连通+非孤立顶点全偶度）；同会话 D 类回答还能挂接「你 Day0 提到的混淆点」。但跨会话：D1a 明示失忆；D2 追问「我之前和你聊过那条『顶点度数都是偶数与图连通』的结论到底对不对」→ 系统答「这条结论是**正确**的。它是无向图中判定欧拉回路存在的标准充要条件」——**与 C3 的「命题为假」直接矛盾**（系统失去纠正上下文后把用户原始假命题按标准定理解读并确认）。纠正保持失败成立，根因同指 NBP-1 |
| **GP-03 星图不说谎** | 方向性异常：恒 0 而非虚高，无证据资格 | **首次获得正向证据（真实生长 + 不虚报）** | 判卷后 8 节点落图、任务完成后 4 节点各 +25、新增 1 节点（集合及其运算）、unlocked 8→10；dashboard headline 引用真实 mastery 变化；mastered_count=0（25 分未达掌握阈值，不虚报）；账本=仪表盘 1==1。残余缺口：study_minutes 恒 0、下修方向未隔离、读模型延迟（NBP-4）。仍为压缩轮代理证据，不构成最终 PROVEN 定级 |
| **GP-11 画像有效性** | 无效（五段行为零字段写入） | **仍无效（透明画像零字段变化）** | before/after 全量扁平 diff 零字段变化（before_nonempty=1 → after_nonempty=1）。注意：诊断判卷实际调用了 `_persist_profile_diagnostic_summary`，但 transparent 面不可见——与 LOOP1 BP-8 同现象（写入 hidden 层或未接透明面）。BP-8 本轮无修复卡认领，维持原状 |

## 3. 新断点清单（本轮新发现；按严重度排序）

### NBP-1 · P0：WS 主链路记忆写账断裂——MEM-AMNESIA 修复只在 REST 链路生效，移动端主路径仍失忆
- 现象：同一句 B1 明示事实（科目/7 天后/自评 42/弱图论/每天 165 分钟），经 **REST `POST /api/v1/chat`** 发送 → **3 条 declared facts 正确入账**（exam commitment 带 `due_at: 2026-09-29T18:00`，weakness、constraint 各 1 条，见 `evidence/probe-rest-memory-write.json`）；经 **WS `/ws/chat`**（gateway → gRPC StreamChat，即 mobile 主路径）发送 → **0 条**（判卷后即时查 + 10 分钟后复查均 0，排除异步延迟）。
- 归因：MEM-AMNESIA（aba3f6d4）的抽取/固化逻辑在进程内单测 18/18 绿（以 B1 原句为夹具）；写账接线在 orchestrator `process_stream` 的 fire-and-forget 收尾（`orchestrator.py:3781` 创建 `_finalize_turn_after_done` → :1262 调 `_write_turn_end_episodic_memory` → :1183 fallback `enqueue_from_chat_turn`）。REST 面（`api/v1/chat.py:1131`）同步调同一服务且成功 → 断点收敛在 **WS/gRPC 流式路径的收尾任务未生效或静默失败**（收尾 catch-all 只 logger.warning，需引擎日志定位；本轮无法读取引擎 stdout）。
- 修复提案：核查 `_finalize_turn_after_done` 在 StreamChat gRPC 路径的可达性与后台任务异常日志；给 WS 收尾加与 REST 同款的确定性直写兜底；补「同句 REST 写/WS 必须写」的链路级回归。

### NBP-2 · P0：goal 详情端点运行时 500——GOAL-ROUTER 修复卡自身在活栈断裂（单测绿/运行红）
- 现象：`GET /api/v1/experience/goal-detail/{goal_id}`（含 `current` 别名）稳定 500：`` `MinimumAcceptanceCriteriaPayload` is not fully defined; you should define `CriteriaThresholdPayload`, then call `MinimumAcceptanceCriteriaPayload.model_rebuild()` ``（pydantic v2 前向引用未解析；`goal_router.py:56/66/117` + 路由 :140）。
- 根因初判：守卫测试 `test_goal_detail_route_shadowing.py` 全部直调 handler/断言注册面，**未走 FastAPI `response_model` 校验路径**，故运行时才炸的 pydantic model_rebuild 问题在单测全绿下上线即 500。mobile goal 详情屏与 home 卡在活栈上仍拿不到数据（该端点修好后才是「GOAL-ROUTER 真实数据」的可验收态）。
- 修复提案：模块尾补 `model_rebuild()`（或修类定义顺序/引用），守卫补一条 TestClient 形状的端到端用例。

### NBP-3 · P1：goal→intake 双计划残余（BP-7b 未覆盖）
- 现象：账本并存两份 active sprint 计划：`069bc4f9`（goal 创建，「离散数学期末 7 天冲刺：及格冲 70+」，**subject=null**）与 `ad361a54`（intake 创建，「7天离散数学冲刺」）。intake 幂等修复的匹配键是 `Plan.subject == request.subject AND target_date == exam_date`（`exam_sprint_intake_service.py` `_find_reusable_sprint_plan`），goal 驱动计划 subject 为 null 永不命中。
- 修复提案：匹配键加「同名/同 target_date 的 goal 关联 sprint 计划」分支，或 goal 建计划时回填 subject。

### NBP-4 · P2：galaxy 读模型分钟级延迟（评测障碍 + 产品一致性风险）
- 现象：判卷后 2 秒、任务完成后数秒的即时读（B5b/C7b/C8a 三处）均返回陈旧值（touched=0）；150 秒后结算读全部到位（8→10 节点、mastery +25×4）。写侧真实（判卷响应自带 8 条 node_mastery_updates），读投影滞后。
- 影响：用户「完成任务立刻看星图」会看到毫无生长的假象（与 GP-03 的「不说谎」宣称相悖）；评测侧必须等结算才能定级。
- 修复提案：galaxy 读走主库或动作后失效缓存；至少在完成类动作的响应里内联最新节点状态。

### NBP-5 · P2（测试基设债）：反记忆词表漏「未保留」变体
- 现象：D1a「当前会话中**未保留**具体记录」未被 `MEMORY_ANTI_RECALL_MARKERS` 命中（词表只有「没有完整记录/未记录/…」），导致自动启发式误判 pass。人工复核已在本报告改正；词表扩充留作驱动器下轮维护（属测试基设，未在本轮中途改判定口径）。

### 观察项（不计断点）
- **BP-3b（仍在修未上栈）再观察**：C3 首跑（纯知识措辞）仍被「这一步需要你确认后才能继续」确认门截留（tool_result×2 + 单 delta），重跑才通过——确认/澄清快速通道对纠正探针的门控不稳，措辞规避不彻底，BP-3b 修复仍必要。
- **CTX-PACK 召回静默（预告在修）**：本轮未观察到「引擎无 embedding provider」型静默；记忆面为空的实际根因是 NBP-1（写侧为空），与 CTX-PACK 嫌疑区分如前。
- **WS 回合墙钟**：引擎单回合 57-63s（agentic 工具流 tool_result 多达 12 帧），贴近并多次超出 60s 评测预算；移动端用户体感与评测预算都指向同一优化点。

## 4. 诚实判定（CP-98/99 与轮级边界）

1. CP-98/99 frozen unsupported：无真人自报、无真实考试墙钟，永不折算 pass。
2. 轮级诚实：API 压缩轮（Day0+Day1）即使全绿也不能宣称北极星。本轮人工定级 **2 pass / 2 fail / 5 blocked / 2 unsupported**（自动表 1/2/6/2，差异两处均为已知证据伪影，见 §1 注）。
3. 「pass」两枚均为**压缩轮内可判的最小语义**：CP-00=「诊断入账+章级节点落图」（非 24 节点全映射），CP-03=「落本+同步移动」（非 6 天 0 漏记+方向隔离）。不构成对「7 天提分」叙事的证明。
4. 证据完整性披露：①驱动器在轮内发现并修正 3 处自身缺陷（判卷 confidence 枚举大小写、B4 证据恢复少取一层、B3-2v 状态读取），修正均以补跑相落地，首轮失败证据保留未删（`B5_…graph-theory-weak.json` 首版为 400 FUZZY，被补跑覆盖前已留档于过程记录）；②C2/C3 首跑 60s 截止的 blocked 证据保留，90s 重跑覆盖文件，两次差异在 §NBP 观察；③B5b/B6/B7 与 C8a 的即时读被 day0fix/day1settle 结算快照覆盖——**快照文件以结算值为准**，即时读证据保留在 B5b/C7b/C8a 步文件中；④D1a 启发式 pass 已人工复核改判 fail（NBP-5），全部原文存于证据文件供复核；⑤REST/WS 判别探针使用 2 个一次性 `northstar_ns2_probe_*` 账号，仅注册+1 条聊天。
5. 零自评红线：全部结论基于 API 响应与账本对账；两处人工复核（D1a、CP-00/03 自动表伪影）均附原文引用。

## 5. 修复效果差分总结（一句话）

五张上栈修复卡实测 **P0-1（诊断+落图）、P1-5（mastery 真实生长）、INTAKE（intake 幂等复用）三张兑现**，P1-3（驱动器终止语义）使本轮证据首次干净可用，顺带证实 BP-4 对账修复；但 **GOAL-ROUTER 修复卡自身在运行时 500（NBP-2）**，**MEM-AMNESIA 修复只在 REST 链路生效、WS 移动主链路仍失忆（NBP-1）**——「记忆必须比裸 GPT 好」这条北极星核心宣称在主路径上仍未兑现。

## 6. 交付物与复跑

- 驱动器：`backend/tests/northstar_eval/real_drive.py`（新增相：`day0fix`/`day1chat`/`day1settle`；账号前缀、状态文件、轮次标签经 `NORTHSTAR_USERNAME_PREFIX`/`NORTHSTAR_CONTROL_PREFIX`/`NORTHSTAR_STATE_PATH`/`NORTHSTAR_LOOP_TAG` 注入，缺省保持 LOOP1 兼容；单测 `test_real_drive_unit.py` 19 项全过）
- 证据：`v3-output/NORTHSTAR-LOOP2/evidence/`（steps 44 + 快照/gp/probe 18 + run-summary.json）
- 复跑：栈在跑前提下
  ```bash
  cd backend && NORTHSTAR_USERNAME_PREFIX=northstar_ns2_ \
    NORTHSTAR_CONTROL_PREFIX=northstar_ns2_ctrl_ NORTHSTAR_LOOP_TAG=LOOP2 \
    NORTHSTAR_STATE_PATH=/tmp/northstar_ns2_real_drive_state.json \
    SECRET_KEY=test python3.11 -m tests.northstar_eval.real_drive --phase setup \
    --out ../v3-output/NORTHSTAR-LOOP2
  # 之后依相：day0 → day0fix → day1 → day1chat → day1fix → day1settle → gain → rejudge → report
  ```
- 判别探针：`/tmp/ns2_probe1.py`、`/tmp/ns2_probe2_rest_mem.py`（运行态，收工已清；REST 写账成功输出已摘录进 `evidence/probe-rest-memory-write.json`）
