# NORTHSTAR-LOOP1 · NS-001 第一轮真实闭环报告（API 级压缩轮 Day0+Day1）

> C 线北极星场景第一轮**真实驱动**：真实网关（Go :8080）→ 真实引擎（gRPC :50051）→ 真实 LLM（Qwen）。
> 本轮性质：**观察/评估卡**——不改产品代码，只落测试基设与证据；发现的 bug 以修复提案上报，本轮不修。
> 诚实声明：API 压缩轮**永远不能宣称北极星达成**；CP-98/99 按冻结规则一律 unsupported。

- 运行 ID：`NS001-LOOP1-20260922-112401`；基线 `main@3fdd34bd`（wt86-v3）
- 主账号：`northstar_ns001_9439e182`（user_id `ed1ee655-…`）；对照账号（GP-04 盲臂）：`northstar_ns001_ctrl_65213571`。未触碰任何非 northstar 账号；全程仅经 API，未直写 DB。
- 真实 LLM 消息：6 条（B1 onboarding、C2 答疑、C3 故意犯错、D1a 主臂、D1b 对照臂、D2 追问）；其中对照臂 1 条在 60s 预算内未完成（仅收到 1 个 delta）。费用在 ~$1 上限内（Qwen）。
- 驱动器：`backend/tests/northstar_eval/real_drive.py`（分相可复跑：setup/day0/day1/day1fix/gain/rejudge/report），单测 `test_real_drive_unit.py` 27 项全过。
- 证据：`evidence/steps/*.json` 38 份（每步请求/响应摘要+时间戳+verdict）+ `evidence/gp-*.json` + 快照 8 份 + `run-summary.json`。

## 1. 旅程检查点表（11 检查点：0 pass / 3 fail / 6 blocked / 2 unsupported）

| 检查点 | 状态 | 依据（证据步） |
|---|---|---|
| CP-00 摸底分入账且考纲→星图映射 | **fail** | 摸底卷生成 422（诊断题包不支持离散数学，见 BP-1）；基线 42 仅以 intake 自报形式入账（sprint-summary `baseline_score=42.0, source=intake`）；星图中不存在 CH1-CH6/欧拉回路等考纲节点（142 个通用种子节点+2 个任务标题节点） |
| CP-01 计划按权重定向且经人工确认 | **fail** | intake 首跑 200 且产出 7 天 backbone（`user_model.weak_chapters=[图论]`，方向正确）；但本轮证据文件被复跑 403 覆盖（intake 非幂等，BP-7），且产品无「计划草案→人工确认」端点可走（人工确认环节缺失） |
| CP-02 quiz 轨迹非降 | blocked | 压缩轮仅 1 个 quiz 时点，3 日滑动窗无法构成（诚实降级） |
| CP-03 错题 100% 落本且触发 mastery 同步 | **fail** | 错题落本 201（C5b）+ review 提交 200（C5c）成立；但 mastery 同步半程失败：galaxy 节点 mastery_score 恒 0、study_minutes 恒 0（见 BP-5） |
| CP-04 次日计划自适应 | blocked | 本轮无 Day2（诚实降级） |
| CP-05 复习命中率 ≥0.7 | blocked | 仅拉取复习队列 200，无重测作答——fetch 成功不构成命中率证据（v2 判定已修正此误报） |
| CP-06 加权覆盖 ≥0.8 | blocked | 需 Day6 末（诚实降级） |
| CP-07 提分 ≥+15 | blocked | 需 Day7 模拟考（诚实降级） |
| CP-08 遗忘率 ≤0.2 | blocked | 需 Day10 重测（诚实降级） |
| CP-98 认知负担自报 | **unsupported** | 冻结规则：需真人 NASA-TLX 量表，API 轮永不折算 pass |
| CP-99 全真墙钟 ≤120min | **unsupported** | 冻结规则：需真实考试墙钟，API 轮永不折算 pass |

## 2. 断点清单（按严重度排序；均为「现象/API 码/根因初判/修复提案一句话」）

### BP-1 · P0：诊断引擎不支持主科目「离散数学」——NS-001 主路径第一步即断
- 现象：`POST /api/v1/exam-sprint/diagnose/generate` → **422** `{"detail": "诊断暂支持的科目：计算机网络、数据结构；「离散数学」暂未内置诊断题包"}`；而 intake 自动生成的 Day1 计划卡恰好是「Day 1 · 诊断分诊」，用户按卡执行必然撞墙。
- 根因初判：`exam_sprint_diagnostic_service` 仅内置计算机网络/数据结构题包；SCENARIO 锚点表宣称的「topic→galaxy node 映射」在比赛主科目上不存在。
- 修复提案：为离散数学补诊断题包（`sprint_packs/mathematics_v1.json` 已有同构样例可对齐），或科目白名单改为配置化 + LLM 出题兜底（判卷保持确定性）。

### BP-2 · P0：跨 session 私有上下文丢失，系统自述「没有完整记录」——「memory 必须比裸 GPT 好」当前不成立
- 现象：Day0 对话明示「分不清欧拉/哈密顿、自评 42、弱图论」；Day1 新 session 追问同一点 → 回答「你提到的具体薄弱点**我这里没有完整记录**，只记得你刚完成 Day1 复习任务」；`/memory/episodic` 仅 1 条 task_outcome（来自任务标题），Day0 对话事实零入库。
- 根因初判：episodic 记忆写入只被 task_outcome 类事件触发（`source_lane=direct_capture` 只捕获了任务完成），自由聊天中的用户自述弱点/目标/约束未进记忆写账；或已写入但 chat ContextPack 注入侧未读取。
- 修复提案：chat 出口对「用户自述弱点/目标/约束」句式触发记忆写账（episodic+profile），并在 ChatContextPackBuilder 注入 episodic memories（M-02..M-07 链路对齐）。

### BP-3 · P1：同一 WS 会话连续两问，第二问返回与第一问 99.5% 相同答案（疑似响应重放/会话状态不推进）
- 现象：C2 问「欧拉 vs 哈密顿区别讲解」；C3 问「我认为偶数度⇒连通，请确认」→ 返回与 C2 **99.5% 相同**（difflib ratio 0.995）的讲解，全文未提及用户断言、无任何纠正（`evidence/steps/C3_*.json`）。
- 根因初判：两问共用同一 session_id 的 WS 连接；疑似响应缓存/去重键取 session 而非 (request_id, message)，或 orchestrator 未把新 user turn 推进会话历史（需查 `chat_orchestrator_chatflow` 与 engine StreamChat 会话装配）。
- 修复提案：复现后把缓存/去重键改为 (session_id, request_id, message_hash)，并核对会话历史推进；补一条「同 session 连续异问」回归用例。

### BP-4 · P1：任务账本 completed=2 vs sprint 仪表盘 completed=0（跨账本不一致）
- 现象：`/api/v1/tasks` 有 2 条 COMPLETED（含 intake 推荐卡）；`/exam-sprint/sprint-summary` 却是 headline「你用了 1 天，**完成了 0 项任务**」，`task_stats.total=4`（实际 20），`current_score=0.0, delta=-42.0`（无 quiz 数据时以 0 参与差值）。
- 根因初判：sprint-summary 只统计单条 sprint plan 名下 4 张卡，跨 plan/全量任务完成事件未聚合进 sprint 统计；缺失值用 0 充当真实分数。
- 修复提案：sprint summary 聚合口径按 subject/用户全量任务收敛，current_score 缺数据置 null 而非 0（M9 仪表盘诚实性）。

### BP-5 · P1：星图 mastery 恒 0——完成任务只「解锁」不「生长」
- 现象：完成任务后 `galaxy/user_stats`: unlocked_count=2 / mastered_count=0 / total_study_minutes=0；新增 2 节点即任务标题本身（「来自任务的学习主题：…」），learning_state=weak、`mastery_score=0.0`、`total_study_minutes=0`；错题 review 提交后亦无变化。
- 根初判：task.complete 只创建/解锁 topic 节点，未触发 mastery 生长事件与学习时长回写；`error_book_mastery_sync` 未被 review 触达（或未落到对应节点）。
- 修复提案：task.complete → galaxy 节点 mastery 增量 + study_minutes 回写；error review → 对应章节节点 mastery 下修，均走 galaxy_service 现有生长事件面。

### BP-6 · P2：错题本科目枚举无大学科目
- 现象：`POST /api/v1/errors {"subject":"离散数学"}` → **400** `"'离散数学' is not a valid SubjectEnum"`；枚举仅 K12+computer/other（`app/schemas/error_book.py SubjectEnum`）。
- 修复提案：SubjectEnum 追加大学科目或改 free-text+归一化层（大学场景是产品主场景之一）。

### BP-7 · P2：goal 与 intake 各建一条并行计划，且 intake 非幂等（复跑 403）
- 现象：B2 goal 创建后出现 plan 228093d7「离散数学期末 7 天冲刺：及格冲 70+」（goal 驱动）；B3 intake 又生成 plan 46ef9462「7天离散数学冲刺」；`/plans/active` 只返回前者；intake 第二次调用 → **403**。
- 修复提案：intake/goal 检测同科目活跃 sprint plan 时复用而非新建；403 改为 409+可恢复语义（本轮靠 `GET /plans/active` 恢复，已落 B3r 步骤）。

### BP-8 · P2：画像全程空壳（Day1 五段行为零写入）
- 现象：`/profile/transparent` before/after **逐字段全等**：preferences/goals/tags/patterns 全空，hidden_item_count=16，transparency disabled。
- 根因初判：chat/task/error 路径未触发 `profile_write_service`；或写入了 hidden 层而 transparent 面无任何变化可见。
- 修复提案：打通 Day1 五段事件 → profile 写入，并在 transparent 面暴露 hidden 层计数变化以便验证。

## 3. 四项增益取证结论（一句话版；详见 evidence/gp-*.json）

| 靶子 | 判定 | 一句话结论 |
|---|---|---|
| **GP-04 检索/记忆信息增量** | **本轮无正向证据（main arm fail；对照臂因 60s 预算不完整，差分不可判）** | 主臂回答显式承认「我这里没有完整记录」私有上下文，个性化 marker 均来自任务标题等系统侧数据而非 Day0 对话记忆；对照臂（全新账号）同问 60s 内未完成，盲差分本轮无法闭合——且严格 GP-04（真料/盲选引用答对率）需完整三臂协议，本轮仅为压缩代理。 |
| **GP-07 记忆复用（纠正保持）** | **fail** | 故意犯错未获纠正（BP-3，返回上一问答案）；追问「我之前的理解对不对」时系统自述「没有完整记录」并重新泛泛讲解——纠正未被记住，反例成立（首轮，单账号）。 |
| **GP-03 星图不说谎** | **方向性异常：恒 0 而非虚高** | 星图未虚报掌握（无「假点亮」），但真实完成的事件也完全不体现在 mastery/时长上（unlocked=2 全是任务标题节点、mastered=0、minutes=0），且 sprint 仪表盘与任务账本矛盾（0 vs 2）——校准误差无从计算，「覆盖/掌握」宣称暂无证据资格。 |
| **GP-11 画像有效性** | **无效（本路径）** | Day0→Day1 全量扁平 diff 零字段变化（画像服务在五段真实行为下完全未写入），画像无法进入决策，开/关无差。 |

补充：上述均为 **API 压缩轮单账号首轮观察**，不构成对靶子的最终 `PROVEN_*` 定级（按 GAIN_PROOFS 规则需差分协议）；但 BP-1/BP-2/BP-4 属「宣称路径断裂」级反例，建议北极星材料在修复前避免引用「诊断/记忆/仪表盘」三项宣称。

## 4. 诚实判定（CP-98/99 与轮级边界）

1. CP-98/99 frozen unsupported：本轮无真人自报、无真实考试墙钟，永不折算 pass。
2. 轮级诚实：API 压缩轮（Day0+Day1）即使全绿也不能宣称北极星；本轮实际 0 pass / 3 fail / 6 blocked / 2 unsupported。
3. 证据完整性披露：①B3 首跑 200 的证据被复跑 403 覆盖（驱动器缺陷已修正：现以 B3r 恢复路径记录）；②对照臂 D1b 超 60s 预算未完成，GP-04 盲差分不闭合；③CP-05 判定 v1 曾误把「fetch 200」当 pass，v2（anti-recall + fetch≠hit）已修正并落 `*-rejudged.json`；④关键词启发式判定均标注 heuristic，全文已存证据供人工复核。
4. 零自评红线：全部结论基于 API 响应与账本对账，无 LLM-as-judge。

## 5. 交付物与复跑

- 驱动器：`backend/tests/northstar_eval/real_drive.py`（`--phase check/setup/day0/day1/day1fix/gain/rejudge/report`，分相幂等守卫；凭据仅存 `/tmp` 运行态文件（600，收工已清，复跑即全新账号重建）），证据中凭据仅 sha256 前缀）
- 单测：`backend/tests/northstar_eval/test_real_drive_unit.py`（27 项，含反记忆指称判定回归）
- 证据：`v3-output/NORTHSTAR-LOOP1/evidence/`（steps 38 份 + gp/probe/snapshot + run-summary.json）
- 复跑方式：栈在跑前提下 `cd backend && SECRET_KEY=test python3.11 -m tests.northstar_eval.real_drive --phase setup` 起步依相执行；每步 60s 上限、LLM 24 条硬预算。
