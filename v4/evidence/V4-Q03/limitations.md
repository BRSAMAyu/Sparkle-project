# V4-Q03 · limitations —— 模拟器/真人边界、unknown 项与缺陷登记

卡：`v4/04_tasks/tasks.json` V4-Q03（kind=verification · risk=high · 双审）
被评对象：main @ `a8f46650`（含 U10/U04/I07/D04 合并收口）。本卡零产品代码改动。

## 1. 证据层级：本 run 是 L1，不是真人

- 全部七场景运行在 **L1（可控服务模拟）**：真实服务层 + 真实 REST/TestClient + 真实 sqlite 行
  （独立内存引擎，非演示库）。按 `06_evaluation/EVALUATION_PROTOCOL.md` §五层证据：
  **L1 全绿不能替 L3/L4**。
- 「用户步骤」「我来做/带我做/交给 Sparkle」在本 run 中由**探针代码扮演**（模拟器行为），
  不是真人认知：真人会不会理解 awaiting 提示、会不会在被拒后重试、判断质量如何——全部
  **NOT_MEASURED_HUMAN**。凡本报告写「用户完成」处，语义是「以 user 身份证据走完整 API 面」，
  不是「真实人类学习者做到了」。
- 真人学习迁移（护栏 4 的「独立能力」面）、真人交付效率对比、像素界面上的认知负荷：
  本阶段无人工任务授权，一律 unknown，不冒充（协议 §不能自动证明的事）。

## 2. 模拟器行为 vs 真人认知的分标记（卡面要求逐条）

| 验收面 | 模拟器行为（本 run 实证） | 真人认知 | 判定 |
|---|---|---|---|
| Agent 代答不记用户掌握 | 结算门 BLOCK + NON_HUMAN 零融合，全链 PASS | 真人是否因代答产生「我学会了」错觉 | unknown（未测） |
| 示例/答案隔离 | 全部可达面零答案材料（机械探针） | 真人是否可从题面+提示构造性还原答案 | unknown（本题面+泛化反馈不含解析；深度构造性泄漏未做红队） |
| 切模式/取消/重连不跳人类步骤 | 状态机/幂等键/owner 纪律三场景 PASS | 真人断连后的实际操作序列分布 | unknown（取了最常见重连序列：同 key 双发+换 key 重试） |
| 交付效率 | 模拟器口径：agent 路径 12min vs 任务估计 60min 基线 | 真人手工完成同交付的实际用时/质量 | unknown_not_measured |

## 3. 缺陷登记（验收产物，随卡交付；不在本卡修）

- **F1（severity B，阻断「检验旅程可达」子判定）**：`request_independent_check`
  （backend/app/core/learning_journey.py:262-283）对 example→attempt 的**合法中间推进**
  也返回 `HOLD.evidence_not_supported`（函数只对直达 independent_check 返回 None）；
  `enter_check` 的持久化门 `if hold_reason is None and decision.stage != scaffold.stage`
  （backend/app/services/learning_journey_service.py:330-333）因此永不写回。后果：
  **example 起点（默认 ScaffoldState）经旅程 check/enter API 永远到不了独立检验段**，
  已推进的决策被丢弃且响应携带误导性 hold_reason。单跳 attempt→check 正常（U10 既有
  测试恰好只覆盖该跳——`_guide_with_check` 默认 stage="attempt"）。修复建议：中间推进
  返回 None hold（或在 enter_check 判 `decision.reason.startswith("OK.")` 决定持久化）；
  修复后需复验本卡 S1④b。
- **F2（severity C，成本/工件卫生）**：`submit_judgment` 幂等重放路径
  （backend/app/services/hybrid_journey_service.py:713）无条件重跑 `_execute_and_check`
  （脚本注入下观测到 LLM 2 次调用）并无条件新增 execute_check 产物行（:728-745）。
  不越人类步骤：判断戳不重复、run 不进 SUCCEEDED、交付确认仍留待用户。
- 两项均为**实现卡（U10/U04-j06）责任面**的收口缺口；本卡按 verification 卡面只举证不修码。
  评测 FAIL 面已如实计入 verdict（`check_journey_reachability=FAIL_F1`），其余护栏判定
  不受其污染——隔离面/归属面的 PASS 不依赖该不可达路径。

## 4. unknown 项全列

1. 真人学习迁移/掌握真实性 —— NOT_MEASURED_HUMAN
2. 真人交付效率（含 agent 代办的真实省时比例）—— NOT_MEASURED_HUMAN
3. 移动端真机/模拟器 UI 旅程（L3：工作台页面实际点按）—— NOT_RUN（U04 已交 widget 级
   截图/语义证据；本卡验证的是其后端状态机与 REST 契约面）
4. 真实模型出题/判分 —— NOT_RUN（本卡零 LLM；判分权威=服务端 guide_json 预置答案）
5. 构造性答案泄漏红队（跨节点拼图、prompt injection 逼答案）—— NOT_RUN（超出卡面三条）
6. L2 真模型层 —— 无授权不发（heavy_token_required=false；本卡亦无此需要）

## 5. 环境与口径备注

- 探针 sqlite 引擎与演示库零接触（无 .env、无 DATABASE_URL；TEST-DBGUARD 判据未触发）。
  事件总线 DLQ 兜底对 PG 的认证失败尝试 = 预期噪声，零写入。
- `mastery_audit_log.created_at` 探针 DDL 带 DEFAULT：生产写路径（spark/update 的 INSERT）
  不供给 created_at（PG server default 覆盖）；house 版 DDL 无默认，会误伤完成面结算写入
  成假阴性——已在 probes/conftest.py 注释说明。
- `GalaxyService._write_mastery_outbox_event` 以裸 text() 绑 UUID（asyncpg 原生支持、
  aiosqlite 不支持）：探针因 runs 面需要建了 outbox 表而暴露该 bind 错误，会导致整个掌握
  写事务回滚。**生产 PG 路径不受影响**；探针侧按 house 总线桩纪律 stub 该 transport
  （掌握状态行 + 审计行保持真实写）。此项属 sqlite 测试方言，不计产品缺陷；若后续卡在
  sqlite 上复跑完整结算链，需知悉。
- 「探针用后即删」口径：探针/剧本**未加入 backend/tests/ 生产测试树**；副本保留于
  `v4/evidence/V4-Q03/probes/` 供双审按 run_manifest 命令复现（Q02 `reproduce_counterexample.py`
  先例）。审查会话可自行删除或继续沿用。
- S2 中「spark 解锁可见、mastery 恒 0」为 D04 设计语义（参与足迹 vs 能力面），非泄漏；
  红线断言锚定在 mastery==0 与 fusion==None。
- S1 判分为确定性归一精确比对：改述答案判错是**设计行为**（无模型放宽），已作为边界
  记录（submit_paraphrase_graded_incorrect），不构成缺陷。
