# V4-Q03 · 一审 receipt（review_r1）

- 审查会话：wtQ03R1（独立未参与 Q03 验收实现；kind=verification · risk=high · 双审之第一审）
- 审查对象：分支 `agent/v4/q03` @ `13771c0d`（被评实现 = 基线 `a8f46650`，工作树审查期保持干净）
- 审查日期：2026-09-29（UTC 记录时间与提交时间线核对一致，无倒签）
- 审查基线：卡面三条验收 + objective（mastery/deliverable/mixed、用户步骤/示例隔离/提示渐隐/成果核验、模拟器与真人分标记）+ run_manifest.verdict_summary

## 裁决

**APPROVE_WITH_CONDITIONS**

四护栏 PASS 判定全部独立复证成立；F1/F2 缺陷定性、定级与归属均维持原判；
value=PASS_WITH_FINDINGS 与 `check_journey_reachability=FAIL_F1` 的计入方式诚实无掩饰。
**条件**（终门前必须满足，与被审裁决自身的出口一致）：

1. F1 须在 **U10 责任面**修复（`request_independent_check` 中间推进返回 None hold，或
   `enter_check` 持久化门改判 `decision.reason.startswith("OK.")`），修复后**复验本卡
   S1④b**（`defect_F1_enter_stuck_from_example` 检查项翻绿）方可关闭检验旅程可达面。
2. F2 修复前，任何在真模型（L2+）上复跑 j06 旅程的卡须知悉：幂等重放会重复起草并可能
   产出**与用户所判不同版本**的 outline 产物（LLM 非确定性；本次 L1 脚本注入下内容确定，
   未观测到实际漂移）。

## 逐项审查结果（每条给可复现命令或行号锚）

### 1. F1 定性复核（最重靶）——**维持原判：B 级成立，U10 责任面归属正确**

- **源码亲读**：`backend/app/core/learning_journey.py:262-283`——`request_independent_check`
  仅在 `decision.stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK` 时返回 `hold_reason=None`；
  否则一律返回 `HOLD.evidence_not_supported`。而 `next_scaffold_step`
  （`backend/app/core/hybrid_policy.py:388-438`，:421-428）在 user_chose+evidence_supported
  下**单点推进**：example→attempt 返回 `decision.reason="OK.advance_user_chose_with_evidence"`。
  合法中间推进与 HOLD 误标并存，亲读确认。
- **持久化门亲读**：`backend/app/services/learning_journey_service.py:329-333`——
  `if hold_reason is None and decision.stage != scaffold.stage` 才写回
  （`apply_scaffold_decision`）；hold_reason 恒非 None → 中间推进永不写回。
- **无替代推进面（归属关键证据）**：全仓 grep `apply_scaffold_decision`/`next_scaffold_step`
  生产调用链只有 `learning_journey.py → learning_journey_service.enter_check` 一条；
  REST 面（`backend/app/api/v1/learning_journey.py:48-80`）仅 3 端点
  （GET journey / POST check/enter / POST check/submit），无其他可把 scaffold 从 example
  推到 attempt 的产品路径。**故 example 起点（`ScaffoldState()` 默认态，
  hybrid_policy.py:166）经任何 API 序列都到不了检验段**——不只是"两次选择失败"，
  是有界穷举不可达。
- **独立探针复现（非复用验收剧本，自写探针，用后已删）**：example 起点 + 证据支持
  （真实 ErrorRecord review_count=2）连续 8 次 `enter_check`：每次决策面 stage=attempt、
  `scaffold_persisted=False`、`check_available=False`、`hold_reason=HOLD.evidence_not_supported`，
  DB 权威位逐次刷新断言恒 example；同任务带外写 attempt 后单跳一次
  `enter_check` → `check_available=True` + persisted + 题面送达。判定
  **F1_REPRODUCED**。误标直接证据：同一响应中 `decision.reason="OK.advance_user_chose_with_evidence"`
  与 `hold_reason="HOLD.evidence_not_supported"` 并存（证据实际支持却报"证据不支持"）。
- **设计语义裁决**：MASTER_DESIGN §5「目标是掌握时，人必须完成理解/尝试/独立检验」+
  §6 例「生成'示例→自己做→检查'的 Hybrid 计划」——example→attempt→check 是设计旅程，
  中间推进**应**可达。U10 卡验收「答案不泄漏到检验用户可读状态」不要求可达，
  但 U10 交付的旅程链声明 practice(→attempt)→independent_check 为可走链。
  **「合法中间推进误标 HOLD」的定性成立。**
- **「U10 既有测试只覆盖单跳」核**：`backend/tests/services/test_learning_journey_service.py:37`
  `_guide_with_check(..., stage: str = "attempt")`——全部 enter/grade 用例起点为 attempt
  （:206 单跳推进）或 independent_check（幂等/判分）；example 仅作反例（:161-164 GET 不出题、
  :265-268 未 enter 判分拒绝），**无 example→attempt→check 两跳服务级用例**。声明属实。
  补充精确化：纯函数层 `tests/unit/test_hybrid_policy.py:540-543` 逐跳转移有测
  （d1: example→attempt，d2: attempt→check），缺陷纯在旅程服务包装层——与 F1 锚点选择一致。
- **定级核**：阻断设计核心旅程（默认起点全量 mastery 任务命中）但不涉权限/跨用户/
  数据丢失/假成功（停止条件 A 面），隔离/判分面不依赖该路径 → **B 级恰当**。

### 2. 四护栏独立复证——**全部维持 PASS**

- **护栏①（S2）亲跑**：`SECRET_KEY=… ENVIRONMENT=test backend/.venv/bin/python -m pytest
  ../v4/evidence/V4-Q03/probes/test_q03_acceptance.py::test_s2_agent_answer_never_settles_human_mastery -q`
  → **1 passed**（43.1s）。agent 完成 COMPLETED 但 sprint mastery 0.0；WARN 留痕；
  receipt NON_HUMAN + fusion None；正面对照 user `OK.human_authored_settlement` +25.0、
  quiz `action=lit` mastery 30.0（raw_records/S2 第 2/3 条亲读与断言一致）。
- **护栏③（S5/S6/S7）亲跑**：`-k "s5 or s6 or s7"` → **3 passed**（43.5s）。S5 记录亲读：
  agent 越权被拒（ValueError 文本与 agent_run_service.py:1354-1357 owner 纪律一致、
  judgment 完成戳 null）、模式重入收敛同 run（new_run_created=false）；S7：同 key+换 key
  双发均 replay、`resume_events=1`、缺键 422、交付确认重放 task_completed_rows=1。
- **S1/S3/S4 补跑**：S1 → 1 passed（F1 断言=缺陷存在性自证）；`-k "s3 or s4"` → 2 passed。
  **7/7 场景审查侧全绿。**
- **护栏② leaf 键核**：`hybrid_policy.py:126-140` `INDEPENDENT_CHECK_ANSWER_KEYS` 含
  `"correct"`（:134，叶子键注释明示 grading.correct 判分结论）。S1 探针 :255/:374 对
  GET/enter/submit 三面做 `answer`/答案文本/"μN" 子串断言。成立。
- **护栏④分报核**：raw_records/S3 三条亲读——完成面 `OK.deliverable_delegation_settlement`
  +25 与星图面 `channel=non_human, capability_lit=false, mastery_score=0.0` 分立；
  `real_human_efficiency="unknown_not_measured"` 显式在记录内。成立。

### 3. 突变自证抽验——**M1 亲放复证成立**

- `sed task_service.py :826 'if settlement is not None and not settlement.allowed' → 'if False and …'`
  → 复跑 S2 **1 failed**（agent 掌握被冒记，红线断言触发）→ `git checkout` 还原 → 绿。
  还原后 `git status` 干净，`task_service.py` 无残留。M2/M3 未亲放（抽 1 约定），
  以 test_results.json 申报 + 探针断言结构核（M2 对应 S1 :255 剥除断言、M3 对应 S5
  :755 越权断言，靶点真实存在）作替代核验。

### 4. 分母与基线——**映射完整，174 亲证**

- 卡验收 3 条 → 场景映射：①「Agent 代答不记掌握；无示例答案污染」= S2+S1（G1+G2）；
  ②「切模式/取消/重连不跳人类步」= S5+S6+S7（G3）；③「效率与独立能力分报、未测真人
  unknown」= S3 分报记录 + limitations §2/§4（G4，manifest 已诚实披露其无独立 pass/fail
  分母）。objective 三目的 = S1/S2（mastery）+S3（deliverable）+S4（mixed）；渐隐=S1③、
  成果核验=S1⑤。**无验收条目悬空。**
- 基线亲跑：manifest 同一 10 文件命令 → **174 passed in 120.10s**（exit 0）@ 本 worktree。
  174/174/exit0 与申报逐项一致。
- 记录数交叉印证：52 条（9+9+3+17+5+4+5）与 manifest raw_record_counts 一致；审查复跑的
  追加行数（S1=9/S5=5/S6=4/S7=5，S3=3/S4=17）与申报逐场景吻合（复跑后已 `git checkout`
  还原，工作树恢复干净，哈希复验不变）。

### 5. F2 定级——**维持 C 级（附 wrinkle）**

- 锚点亲读：`hybrid_journey_service.py:677`（replay 判定）→ 重放跳过
  `complete_user_step` 但 **:713 无条件 `_execute_and_check`（LLM 面）+ :724-740 无条件
  新增 execute_check 产物行**。S7 记录：llm_calls 1→2、产物 3→4、
  `human_step_skipped=false`、`judgment_stamp_duplicated=false`、run 不进 SUCCEEDED、
  交付确认仍留待用户。
- 定级：不越人类步、不伪造成功、无答案泄漏 → 不是 B；重复产物行当前消费面
  （`_latest_stage_artifact` 取最新、冷启动回放）不会重复计入人类步完成 → 不到升级依据。
  **C（成本/工件卫生）成立**。wrinkle（升级观察项，非现状缺陷）：真模型下重放重起草
  可能产出与用户所判不同的 outline 版本，修复 F2 时应一并消解。

### 6. unknown/BLOCKED 诚实性 + 隔离核——**无虚报**

- 四 unknown（test_results.json:134-139）与 limitations §4 六项对照一致（§4 多出的
  构造性泄漏红队/L2 真模型两项为超卡面补充披露，非掩盖）；limitations §2 逐验收面
  「模拟器行为 vs 真人认知」分标记表落实卡面 objective。
- BLOCKED=无：核实为纯 verification 卡（零凭据/预算依赖），成立。
- 探针隔离核：`probes/conftest.py:48-57` 独立 `sqlite+aiosqlite:///:memory:`（StaticPool），
  无 .env/DATABASE_URL；审查复跑环境未注入任何 DB URL，全部通过 → 与演示库零接触成立。
  outbox stub（:65-76）与 mastery_audit_log DDL 默认值（:22-38）两处 sqlite 方言注记
  与 limitations §5 一致，且明示不计产品缺陷——处理诚实。
- 零生产 LLM：探针以脚本函数注入 execute_check 起草段；审查复跑仅见启动期
  「api_key is empty → demo mode」初始化日志，无任何模型请求发出。申报一致。

### 7. 数字诚实性——**通过**

- 52 条记录：行数、逐场景分布与 manifest 一致（见 §4）。
- sha256 全验（非抽验）：7 个 raw_records + 2 个 probes 文件 + transcript 共 10 件，
  `shasum -a 256` 与 run_manifest.artifacts_sha256 **逐件一致**。
- 抽 3 条记录对照：S2 `user_completed_settlement`（+25.0/OK.human_authored_settlement）、
  S5 `agent_bypass_rejected`（错误文本与 owner 纪律源码一致）、S7 `double_fire`
  （双发均 replay、resume_events=1、422）——与探针断言及源码锚点逐项吻合。
- 时间线：记录 ts=2026-09-28T20:37-20:38Z，提交 2026-09-29T04:51+0800（=20:51Z）——
  记录先于提交，无倒签。

## 发现的次要问题（不改变裁决，供二审与 owner 参考）

1. **N-r1-1（记录面，C-）**：run_manifest `commands_and_exit_codes` 中三条 pytest 命令
   写作 `cd /Users/brsama/code/GitHub/Sparkle-project && … ../v4/evidence/...`——该绝对路径
   与相对路径组合不自洽（证据实际位于 worktree wtQ03，真实 cwd 应为 `wtQ03/backend`）。
   审查已从 `wtQ03/backend` 以相同相对命令复现成功，可复现性未受损；建议终门前勘误该路径行。
2. **N-r1-2（锚点精度，-info）**：F1 持久化门实际行幅 `learning_journey_service.py:329-333`
  （manifest 写 330-333/322-333，偏差 1-8 行，语义所指无误）。
3. **N-r1-3（观察项）**：S1 判分「改述答案判错」为确定性归一设计行为（limitations §5 已记），
   真人宽谅判分归后续教学卡——维持非缺陷结论。

## 审查动作清单（可复现）

| 动作 | 命令/锚点 | 结果 |
|---|---|---|
| S1 亲跑 | `pytest ../v4/evidence/V4-Q03/probes/test_q03_acceptance.py::test_s1_example_isolation_and_hint_fading` | 1 passed |
| S2 亲跑 | `…::test_s2_agent_answer_never_settles_human_mastery` | 1 passed |
| S5-S7 亲跑 | `… -k "s5 or s6 or s7"` | 3 passed |
| S3/S4 补跑 | `… -k "s3 or s4"` | 2 passed |
| F1 独立探针 | 自写 8 连击可达性探针（/tmp，用后即删） | F1_REPRODUCED |
| 突变 M1 | `sed :826 'if False and …' → S2 RED → checkout 还原 GREEN` | 复证 |
| 基线 | manifest 同命令 10 文件 | 174 passed, exit 0 |
| 哈希 | `shasum -a 256` 10 件 | 与 manifest 一致 |
| 记录还原 | 复跑追加后 `git checkout -- v4/evidence/V4-Q03/raw_records/` | 工作树干净 |

（环境：`SECRET_KEY=… ENVIRONMENT=test`，解释器 `Sparkle-project/backend/.venv` Python 3.11.15，
无 .env/DATABASE_URL；临时探针与复跑追加记录均已清除，本 receipt 提交后工作树仅新增本文件。）

## 终门指引

Q03 的 DONE 不被本审阻断，但终门裁决须携带本审条件：**F1 修复（U10 责任面）+ S1④b
复验**是检验旅程可达面的关闭前提；「7 场景全绿」不得读作「F1 已消解」。
