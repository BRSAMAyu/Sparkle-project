# V4-Q03 · diff_or_evidence_only —— 人机分工与学习迁移护栏验收

- 卡：`v4/04_tasks/tasks.json` V4-Q03（kind=**verification** · risk=high · 独立审查 2 位 · heavy_token=false）
- 分支：`agent/v4/q03` @ wtQ03（base = main `a8f46650`，含 24c176cb 的 U04/U10/I07/D04 等全部依赖收口）
- 性质：**验收卡，零产品代码 diff**。产物 = 验收剧本/探针（evidence 内，不入生产测试树）+ 七场景原始记录 + 五件套。
- 证据层级：**L1 可控服务模拟**（真实服务层 + 真实 REST 面 + 真实 sqlite 行；零生产 LLM）。
  模拟器行为与真人认知按卡面分别标记（详见 limitations §1/§2）。

## 1. 一句话

**四护栏在真实旅程路径上复证成立，另揪出两个实现收口缺口**：Agent 代答零掌握（结算门
BLOCK + 星图 NON_HUMAN 零融合，突变自证可失败）；示例/检验答案在全可达面零泄漏（leaf 键
`correct` 含内）；切模式/取消/重连三场景人类步骤一个不跳（幂等键 + owner 纪律双落）；
交付（完成面）与独立能力（星图面）分立报表、真人面全 unknown——**但 example 起点的任务
经 check/enter API 到不了独立检验段（F1，U10 持久化门缺陷），检验旅程的「最后一公里」
只在 attempt 起点通**。

## 2. 分母与场景

7 场景 × 三目的（mastery：S1/S2；deliverable：S3；mixed：S4）+ 护栏三场景（S5 切模式/
S6 取消/S7 重连，generic X-07 run 与 j06 四段旅程双载体）。基线回归：依赖四卡 + 结算面
10 测试文件 **174 passed** @ 同 SHA（exit 0）。原始记录 52 条 JSONL + 运行日志，SHA256
见 run_manifest.artifacts_sha256。

## 3. 四护栏逐条结论（每条含可复现命令/行号锚）

### 护栏1 · Agent 代答不记用户掌握 —— PASS

- **结算门（真实完成路径）**：mastery 任务（human_required=true/false 两形态）以
  `evidence_source="agent"` 走 `TaskService.complete`：任务照常 COMPLETED（行动账本），
  sprint 掌握 **+0.0**；WARN 留痕含 `BLOCK.agent_completed_human_required_mastery` /
  `BLOCK.agent_completed_mastery_step`（backend/app/services/task_service.py:820-841 ←
  core/hybrid_policy.py:311-342）。
- **D04 通道（旅程复证）**：run receipt 吸收 `action=non_human`、不解锁能力面、
  mastery 恒 0（完成路径 spark 解锁=活动足迹，D04 §1 语义）；纯 receipt 升格 ACTUAL 的
  完成行仍 NON_HUMAN、`fusion=None`（capability_channel.py:126-202）。完成路径日志中的
  PG 认证失败为事件总线 DLQ 兜底尝试，零写入。
- **正面对照**：user 证据完成 → `OK.human_authored_settlement` +25.0；quiz 物化 →
  VERIFIED `action=lit` 掌握后验真融合。零掌握不是"全不记"，是**代答不记、独立检验才记**。
- 突变自证 M1（结算门旁路 → S2 红 → 还原绿）。
- 复现：`SECRET_KEY=… python -m pytest ../v4/evidence/V4-Q03/probes/test_q03_acceptance.py::test_s2_agent_answer_never_settles_human_mastery -q`

### 护栏2 · 无示例可见答案污染 —— PASS（附 F1 旅程可达缺陷）

- 示例段 GET：`view.check=None`、全 payload 无 `answer/correct_answer/explanation` 键
  与答案文本；错题简报最小暴露面（无 correct/user_answer）；chat 上下文投影剥除 4 条
  路径、脚手架面单独投影（core/hybrid_policy.py:126-140 键集含 leaf 键 `correct`）。
- 判分面：改述答案→判错（确定性归一，无模型放宽）；精确答案→判对；响应零答案材料、
  出口探针强制（learning_journey_service.py:214-218/355-386）。
- 渐隐转移表 8 步真实序列走查：full→reduced→none 渐隐、失败回升一档、**阶段永不回退**。
- **FAIL_F1（如实上交）**：example 起点（默认态）两次显式选择均不持久化——决策面已推进
  attempt 但被误标 `HOLD.evidence_not_supported` 且丢弃（F1 锚点与影响见 limitations §3）。
  单跳 attempt→check 正常。**此缺陷不产生答案泄漏，只阻断旅程可达**；隔离面 PASS 不依赖
  不可达路径。
- 突变自证 M2（剥除分支失效 → S1 红 → 还原绿）。

### 护栏3 · 切模式/取消/重连不跳人类步骤 —— PASS（附 F2 成本缺陷）

- **切模式（S5）**：j06 旅程 judgment（owner=human）awaiting 时，agent 越权完成被 owner
  纪律拒绝（agent_run_service.py:1354-1357）；换设备/模式重入 `start_hybrid_journey` 幂等
  收敛**同一段 run**、判断步原地等待；用户亲自判断是唯一推进路径；冷启动读面回放同 run。
- **取消（S6）**：取消不落人类步骤完成戳、终态归因 `user_cancelled`；迟到确认 409 带终态；
  旅程取消后判断步提交被拒；重启拿新 attempt、判断步从头等用户、旧 run 不复活。
- **重连（S7）**：`x07:<runId>:<stepId>:confirm` 同 key 双发 + 换 key 三发全部 step_replay、
  `run.user_resumed` 恰 1 条；缺幂等键 422；冷启动仅凭 run_id 还原完成戳（不要求重做）；
  交付确认重放不重复完成任务（恰 1 行 COMPLETED）。
- **F2（如实上交）**：judgment 幂等重放仍重跑起草 LLM 并重复落 execute_check 产物行——
  不越人类步骤、不伪造成功，属成本/工件卫生缺陷（hybrid_journey_service.py:713/728-745）。
- 突变自证 M3（owner 纪律失效 → S5 红 → 还原绿）。
- 复现：`python -m pytest ../v4/evidence/V4-Q03/probes/test_q03_acceptance.py -k "s5 or s6 or s7" -q`

### 护栏4 · 交付效率与独立能力分别报；未测真人就 unknown —— PASS（报表纪律面）

- **交付效率（deliverable 完成面）**：agent 合法代办照常结算（`OK.deliverable_delegation_
  settlement`，+25），用户不被强迫手工重做；模拟器口径效率 = agent 12min vs 任务估计
  60min 基线。**真人效率 unknown_not_measured**。
- **独立能力（星图能力面）**：同一交付工作的 receipt 通道恒 NON_HUMAN、能力节点不点亮
  ——完成面与能力面**两个分立报表面**，不互相冒充（S3 记录）。
- 真人学习迁移、真人认知负荷、构造性泄漏红队、L3 UI 旅程、L2 真模型：全 unknown/
  NOT_RUN（limitations §4 全列），未以模拟器结果外推。

## 4. 价值裁决

- implementation：**COMPLETE**（被评实现收口于 `a8f46650`，基线 174 绿）。
- value：**PASS_WITH_FINDINGS** —— 四护栏本体 PASS；`check_journey_reachability`
  子判定 **FAIL_F1**（需 U10 责任面修复后复验 S1④b）；F2 登记不阻断。终门请读本裁决与
  test_results.json 的 defects_filed，不得以「7 场景全绿」抹掉 F1。
- BLOCKED：无（零凭据/预算依赖）。模型用量：生产 0 次；脚本注入计数在案。

## 5. 交付物清单（本分支，全部未 push）

```
v4/evidence/V4-Q03/
  diff_or_evidence_only.md   # 本文
  run_manifest.json          # source_sha/commands/exit codes/分母/哈希/锚点/裁决
  test_results.json          # 七场景逐检查项 + 突变 M1-M3 + 缺陷 F1/F2 + unknown 全列
  review_receipt.json        # 双审占位（独立未参与会话落盘）
  limitations.md             # 模拟器 vs 真人边界 + unknown + 环境口径
  probes/{conftest,test_q03_acceptance}.py   # 验收剧本（复现命令见 manifest）
  probe_run_transcript.txt   # 最终运行转录（7 passed；.log 忽略规则故以 .txt 入库）
  raw_records/S1..S7.jsonl   # 52 条场景原始记录
v4/04_tasks/tasks.json       # V4-Q03 → REVIEW_READY（仅状态行）
```
