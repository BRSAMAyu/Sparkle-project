# WT806 · Q-08 预裁决项②：V3-2 映射预裁备忘

- Worker: wt806 ｜ 分支 `agent/node-b/wt806/v32memo` ｜ 基线 main `3fac2d30`（含 wt802 收编）
- 性质：Q-08（V3 Final Gate Audit）前置预裁输入——只盘点与建议，不改 DoD/台账/tasks.json，不代 Q-08 下最终裁决
- 盘点方式：库内 git log / grep / 产物目录逐面亲证；关键测试套件在**本 worktree HEAD 原地实跑**（sqlite/零 LLM，未触运行栈与 ns001，未 push）

---

## ① V3-2 gate 原文与子项拆解

原文（`v3/V3_DEFINITION_OF_DONE.md` L16-20，逐字）：

> ## Gate V3-2 — Stuck → Useful Action
> - 20 个代表性 friction scenario 中 ≥18 个产生与真实原因一致的 intervention；
> - 输出必须包含 outcome、smallest useful step、为什么现在做、完成证据、人机执行模式；
> - 不允许用无限缩小任务制造完成感；
> - 高风险或信息不足时能 clarify / abstain。

映射「从什么到什么」以原文为准。4 条 bullet 拆为 6 个可裁决子项：

| 子项 | 原文来源 | 内容 |
|---|---|---|
| S1 | bullet1 前半 | 存在固定的「20 个代表性 friction scenario」集合，代表性有依据 |
| S2 | bullet1 中 | 该 20 场景运行判定 ≥18 通过 |
| S3 | bullet1 后半 | intervention 与真实原因一致（friction 归因 ↔ 干预提名匹配） |
| S4 | bullet2 | 输出含五要素：outcome / smallest useful step / 为什么现在做 / 完成证据 / 人机执行模式 |
| S5 | bullet3 | 防无限缩小任务制造完成感 |
| S6 | bullet4 | 高风险或信息不足时 clarify / abstain |

## ② 每子项证据状态（全部 file:line/SHA 亲证 @3fac2d30）

### S1 — 20 场景集合存在且代表性有依据：**有**
- `backend/tests/aurora/fixtures/friction_diagnosis_scenarios.json`：schema `aurora_friction_diagnosis.v1`，**scenarios=20** + hard_family=6（同句三态、预算双路、冷启动闭环，不计入 18/20 容差、必须全过）；描述明示「A-03 canonical stuck scenarios；persona 覆盖 USER_SEGMENTS_AND_JTBD 五类 Builder」。
- 代表性锚：15 类 friction 封闭词表 = USER_SEGMENTS_AND_JTBD §5 V3 统一语义（`test_a03_friction_diagnosis.py::TestVocabularyFreeze` 断言）；词表/证据面/问题库/裁决参数 **sha256 四指纹双钉**（test L89-92），改面必红。
- 这是全库唯一与「20 个代表性 friction scenario」数量与语义精确对应的载体（已 grep v3/ 全文档 + backend 全测试面确认）。

### S2 — ≥18/20 运行判定：**有（规则层）／缺（真模型复验）**
- `backend/tests/unit/test_a03_friction_diagnosis.py`（77 个测试函数）：`_run_scenario` 对 20 场景逐个跑真源 `app.aurora.friction_diagnosis.diagnose_friction`（生产模块，非测试桩），断言 ≥18 合理 + hard_family 全过。**本 worktree HEAD 实跑：112 passed in 9.70s（2026-09-28）。**
- 语义限定：`diagnose_friction` 是确定性规则层。gate 原文未规定必须真模型；真模型面现有 E-04（`58d08c6f`，dual-reviewed）：ai_face_eval `aurora.intervention.json` 5 golden cases（含 A1 无锚点应选 clarify），真模型收敛 15/15（qwen3.8-flash，`tests/ai_face_eval/real_model_converged.json`）。**20 场景全量真模型复验无记录**。

### S3 — intervention 与真实原因一致：**有**
- 同一 rubric 内三重匹配：`outcome` 精确匹配、`friction_in`（归因类型必须落入可接受类型集）、`nomination_first_in`（首要提名必须在可接受集）；`no_action` 出口禁止伪造提名。
- 错分类代价面专项：burnout 语境绝不 practice 优先、skill 语境绝不 pause 优先（错归因→错干预的最小例证，112 passed 内）。

### S4 — 输出五要素：**部分（4/5 有，why-now 契约位缺）**
| 要素 | 状态 | 证据 |
|---|---|---|
| outcome | 有 | X-01 契约 `desired_outcome` 独立列（`43942d23` ACCEPT 合入主干；`backend/app/core/action_plan.py`）。本 HEAD 实跑：契约+迁移+集成 **32+25 passed** |
| smallest useful step | 有 | `SmallestUsefulStep` 类型化（description + useful_because 封闭词表） |
| 完成证据 | 有 | `CompletionEvidenceSpec` 类型化（evidence_kind 封闭枚举 + ref scheme 封闭），非自由文本 |
| 人机执行模式 | 有 | `execution_mode`（human/agent/hybrid，复用 ExecutionMode 词表+归一门）+ `cognitive_ownership`（user_core/shared/delegated）正交 |
| **为什么现在做** | **缺（task 级契约位）** | X-01 REPORT §6.7 亲证：`why_now / friction_addressed / dependencies / fallback / expiry`「字段位未预埋」，属 EXP 级未来项。Aurora 侧主动建议路径**有** why_now（`backend/app/signals/aurora_core_session.py:59`、`orchestration/plan_quality_contract.py:211`；Q-01 proactive 判定词「suggestion has why-now」）——但不在 ActionPlan/task 级输出契约内。mobile 渲染面未逐行核验 why-now 是否可见（`today_cockpit_card.dart` 等有命中，标注待核） |

### S5 — 防无限缩小任务：**有（契约守卫）／缺（系统级 eval）**
- 契约层可执行判据：`action_plan.py:204`「`useful_because` must be non-empty (**伪步骤不合法**)」+ 六判据封闭词表（produces_artifact/reduces_uncertainty/builds_capability/unblocks_dependency/enables_decision/advances_goal）+ 词表外拒绝——「打开 IDE 看一眼」式伪步骤在契约层被拒，多套件覆盖（本 HEAD 实跑绿）。
- 系统级「任务拆分深度 × 完成感伪造」专项 eval：**全库未找到**（grep 无专门面）。

### S6 — clarify / abstain：**有**
- 契约：`backend/app/core/aurora_decision.py`——`clarify` 必带 `clarifying_question`（L331 否则 violation）；`no_action_reason` 仅限 no_action/abstain（L324）；`abstain/no_action` = inert 词表（L170）。
- 策略：A-02 inert 地板——任意因子下 no_action/abstain 恒可行（`test_a02_intervention_policy_engine.py:85,222`）。
- 信息不足面：A-03 充分性两路 + One Best Question（IG>0、决策敏感、已问不重问、session/day 双预算、超限 best-guess+uncertain 或无证据不假诊断）。
- 真模型：E-04 aurora A1 case（无锚点应选 clarify，不凭空 explain/retrieve）。
- **本 HEAD 实跑：`test_a02 + test_a04_joint + aurora_decision_contract` 193 passed。**
- 高风险面（bullet4 前半）：X-10 77 场景 DB 独立判定——high-risk auto=0（不变式覆盖 5 场景）、allocation 高风险需审批（high_risk×4）、`risk_class` 与 run contract 同名对齐（`v3-output/X-10/EVAL_RESULTS.md`，SHA 20f9b200，零真实 LLM 为显式设计）。

### Q-01（260 场景）与 X-01（契约）对 V3-2 的覆盖判定
- **Q-01**：260 库 12 类（first_value/memory/conflict/allocation/agent_runtime/ui_state/proactive/rag/security/journey/community/performance）**无 friction 类目**；proactive 24 例的判定词含 why-now/NO_ACTION/mute、allocation 20 例含 mode justified/high-risk approval——但 model 路为 mock-provider + surrogate 参考机制表（`harnesses.py` `_PROACTIVE_TABLE` 硬编码），verdict 语义显式钉为 `contract-simulation`。**结论：Q-01 对 V3-2 是间接契约级覆盖（期望词表不漂移），不是 S1–S3 的 gate 主证据。** runner 本身本 HEAD 实跑 27 passed。
- **X-01**：直接覆盖 S4 四字段 + S5 契约守卫，合入主干（`43942d23`），交付后修复链（F1/F2 脏行容错 10 回归）在案。**唯一缺口 = why-now 字段位（其 REPORT 自证）。**

## ③ 映射预裁建议

| 子项 | 预裁建议 | 理由 |
|---|---|---|
| S1 | **映射成立**（A-03 固定 20 场景即原文载体） | 数量、rubric、代表性锚、防篡改指纹全齐 |
| S2 | **映射成立，附裁决条件**：按规则层判定 PASS；是否要求 20 场景真模型复验由 Q-08 显式裁定（现有真模型证据仅 E-04 intervention face 5 例） | 原文未规定模型口径；规则层测试在本 HEAD 亲证绿 |
| S3 | **映射成立** | rubric 三重匹配 + 错分类代价面 |
| S4 | **Q-08 必须先裁口径**：①「输出=intervention/proposal 输出」→ Aurora 侧 why-now 已有，映射成立（task 级缺位登记后续卡，不阻塞 gate）；②「输出=ActionPlan/task 级输出」→ why-now 缺字段位，该子项 FAIL/BLOCKED（需新证据卡：加列/bump 契约+UI 渲染核验） | X-01 §6.7 自证缺位；两种口径裁决结果相反，不可含糊 |
| S5 | **映射成立（契约层）**：以「伪步骤不合法」判据为 PASS 口径；系统级拆分深度 eval 登记为增强项不阻塞 | 契约守卫可执行、多套件钉死 |
| S6 | **映射成立** | 契约+策略+预算+真模型四层证据齐，本 HEAD 实跑绿 |

一句话：**6 子项中 5 个映射成立（S4 附口径前置裁决），无子项需要直接判 FAIL；唯一真实缺口是 task 级 why-now 字段位与 20 场景真模型复验记录，均为「需新证据或显式口径」而非「能力不存在」。**

## ④ 对 Q-08 的输入（可直贴 gate 骨架的裁决槽）

```
## Gate V3-2 — Stuck → Useful Action（预裁输入 wt806 @3fac2d30）

[V3-2.S1] 20 场景集合存在且代表性有依据
  裁决槽: PASS
  证据: backend/tests/aurora/fixtures/friction_diagnosis_scenarios.json
        (scenarios=20, hard_family=6, persona×5, sha256 四指纹钉)
        backend/tests/unit/test_a03_friction_diagnosis.py (112 passed @3fac2d30)

[V3-2.S2] ≥18/20 产生 intervention
  裁决槽: PASS_(规则层) / 待裁: 是否要求真模型复验
  证据: 同上 test_a03_friction_diagnosis.py::_run_scenario (生产 diagnose_friction 直跑)
  条件: 真模型现证仅 E-04 aurora.intervention 5 例 (15/15, 58d08c6f)；
        若裁"须真模型"→ 升级 BLOCKED(需新证据: 20 场景 real-model run)

[V3-2.S3] intervention 与真实原因一致
  裁决槽: PASS
  证据: 同上 rubric (outcome 精确 + friction_in + nomination_first_in +
        burnout/skill 错分类代价面), 112 passed @3fac2d30

[V3-2.S4] 输出含 outcome/step/why-now/evidence/mode 五要素
  裁决槽: 二选一口径后 PASS 或 FAIL
  证据(4/5 有): backend/app/core/action_plan.py (X-01, 43942d23 合入;
        契约+迁移+集成 57 项 @本 HEAD 实跑 32+25 passed)
  缺口: why-now 无 task 级契约字段位 (X-01 REPORT §6.7 自证);
        Aurora 侧有 why_now (signals/aurora_core_session.py:59,
        plan_quality_contract.py:211)
  口径A 干预/proposal 输出=载体 → PASS(task 级缺位登记后续卡)
  口径B task 级 ActionPlan=载体 → FAIL/BLOCKED(需新证据卡:
        契约加列 bump + mobile 渲染核验)

[V3-2.S5] 不允许无限缩小任务制造完成感
  裁决槽: PASS_(契约层)
  证据: action_plan.py:204 伪步骤不合法(useful_because 空集拒绝)+
        六判据封闭词表; 系统级拆分深度 eval 缺→登记增强项不阻塞

[V3-2.S6] 高风险或信息不足时 clarify/abstain
  裁决槽: PASS
  证据: app/core/aurora_decision.py:324,331,170 (clarify 必带问句/
        abstain inert); test_a02+test_a04+aurora_decision_contract
        193 passed @3fac2d30; A-03 One Best Question 预算面;
        E-04 A1 clarify 真模型 case; X-10 high-risk auto=0 (77 场景)
```

## ⑤ 如实声明

- 本 memo 全部测试为 worktree 本地 sqlite/零 LLM 实跑；`.env` 未复制（真库守卫按设计拦截后即删），借入 `app/gen` 生成物跑完集成套件后已删（gitignored，不入库）。
- mobile 端 why-now 渲染面只到 grep 命中层面，未逐行核验——S4 口径 A 若被采纳，建议 Q-08 证据链补一次 UI 面核验。
- tasks.json 中 J-05（V3-2 旗舰卡）标 done，但其 REPORT（v3-output/wt302-j05-stuck-recovery）为 mobile 回流承接最小闭环，**不含** 20 friction scenario 评测证据——V3-2 的 gate 主证据在 A-03 测试面而非 J-05 产物，Q-08 读证据时应以本 memo §② 指针为准，不以 J-05 status 为准。
