# A-02 · Intervention Catalog + Policy Engine V1 — Worker 报告

**STATUS: READY_FOR_REVIEW**

- 卡片：`v3/07_tasks/cards/A-02.md`（Stream AURORA，Gate V3-2，risk medium，Reviewers 1，locks aurora-policy，Depends on A-01✓）
- Base SHA：`873ba1a46330146fecc627e8acb0503c3d9c5015`（origin/main，含 A-01 契约与全部 28 卡成果）
- Final SHA：同上（未 commit；交付物 = 本目录 + `changes.patch`，改动文件清单见 §6）
- 真实 LLM 调用：**0 次**（语义参数化通道默认关，mock 测；见 §2.6 与 §4.1-T7）
- 施工图：`v3-output/A-01/RUNTIME_MAP.md`（44 组件全景）；契约真源：`backend/app/core/aurora_decision.py`（`aurora_decision.v1`）

> **工作树基线偏差记录（透明披露）**：开工实测 worktree HEAD 为 `b9a48bdb`（M-05，
> 不含 A-01 文件），与主会话声明的「已 reset 到 origin/main @ 873ba1a4」不符。
> 树为全空（`git status` 干净、零 untracked），故执行 `git checkout --detach 873ba1a4`
> 对齐协调者声明状态——无任何损失风险（纪律禁的是 stash/reset/clean/切分支对
> untracked 交付物的破坏；本操作前树为空、且非分支切换）。全程未再动 HEAD。

---

## 1. 实际解决的问题

AURORA_V3 §2 的 17 项干预此前是**语义清单**（A-01 冻结为词表），但「选择」仍是
散落的自由动作：spine `_RULE_TABLE` 的 26+ 个 `primary_strategy` 自由串仲裁、
L2 模式命中直跳内部干预名、无统一的「本轮哪些干预合法」判定面——LLM 若进场
则无结构边界（提示词边界不是边界，X-02 已论证）。本卡把干预选择机制化为
**可评测的选择空间**：

1. **Catalog**：17 项全部携带声明式元数据（capability/permission/expected_outcome/
   任务锚点要求/分配要求/proactive/inert/标称 mode）——干预从「字符串」变成
   「带结构前提的封闭目录成员」（acceptance ①）。
2. **Policy Engine**：纯函数规则核心先过滤出 **feasible set**（10 条守卫、每条剔除
   附封闭 reason 码），选择层在上游提名序内取第一个合法者，无合法提名 →
   `no_action` + 封闭原因（确定性出口，绝不 LLM 兜底）；LLM 只能作为**默认关闭的
   参数化通道**在 feasible set 内选/参数化（越界代码级拒收）。
3. **policy version + 封闭 reason 码随行**：每次判定携带
   `aurora_intervention_policy.v1` + catalog 指纹 + why 码，并写入契约 annotations
   （acceptance + Work 3）。

与 X-02 的分界（不清重）：**A-02 管「选哪个干预」，X-02 管「谁执行」**——引擎消费
X-02 `AllocationDecision.mode` 镜像作为输入事实：缺 mode（R4）/mode 冲突（R5）→
确定性拒绝；八维分配 rubric 零重复。

## 2. 关键设计决策

1. **词表零抄写（拼写地雷根除）**：目录 key 集结构派生自
   `app.core.aurora_decision.AURORA_INTERVENTION_TYPES`（`_build_catalog` 按契约
   词表迭代构造）；元数据表缺项/多项/词表外值 → import 时
   `InterventionCatalogError` fail-fast。卡面 `coexecute`/`connect` 漂移串在词表外，
   提名即 R0 拒绝（fixture A4 钉死）。
2. **capability 与 permission 分离**（7 能力 × 6 权限封闭词表）：系统「有没有这个
   执行面」vs「有没有获准用」——X-02「工具优势 × 隐私权限」同款纪律（能做 ≠ 被准做）。
3. **守卫语义与 A-01 契约对齐**：
   - materiality 门（R8）非 inert 全剔 ⇒ 唯一合法出口 `no_action`+
     `materiality_below_threshold`（RUNTIME_MAP A-04 行的 engine 侧机制化）；
   - quiet_hours（R6）/proactive 预算（R9）只压 proactive 型（remind/connect_peer），
     显式用户请求豁免抑制门（X1）但**永不豁免结构性守卫 R1-R5**（用户主权不高于
     结构边界）；
   - cooldown（R7）只抑制目标成员且**不作用于 inert 出口**——任意因子下
     `no_action`/`abstain` 恒可行是地板性质（测试钉死）。
4. **P3-8 engine 侧硬化**：执行面干预（delegate/execute/co_execute）缺 X-02 分配
   mode（含脏值归 None）→ R4 确定性剔除，绝不静默放行（A-01 REPORT §7.7 的消费侧
   纪律在本引擎落成硬规则；参数化测试 ×3 干预 × 3 形态）。
5. **P3-7 构造门预留**：`build_decision_contract()` 先构造后 `validate()`，
   violations 非空 → `(None, violations)`——绝不静默产出非法契约（clarify 缺
   question / 词表外 tier / 裸 token ref 均有测试）。A-04 read 门可直接复用该
   None-通道做机制化校验。
6. **LLM 参数化通道（默认关）**：`InterventionPolicyEngine(semantic_llm=None,
   semantic_enabled=False)`——仅当选择开放（无合法提名且 feasible 含非 inert）才
   进场；提议必须落 feasible（S2 拒收，不计熔断）；参数化仅采纳 clarify 的
   clarifying_question 与 rationale，其余确定性丢弃；熔断（3 次/300s）/限频/超时
   全降级规则缺省（X-02 ActionAllocationPolicy 同款）。构造器注入、无 settings
   依赖——本卡恒关，真实 LLM 0 次。
7. **既有策略面投影而非重建**：spine `_RULE_TABLE` 仍是 spine 行为真源；
   `SPINE_STRATEGY_TO_INTERVENTION`（34 策略串 → 10 目录成员）是投影映射，契约
   测试对 `_RULE_TABLE` 全量策略（含 shadow learning 动态值 `switch_to_worked_example`
   与 partner secondary 族）**双向精确**强制覆盖——不存在的映射不允许（否则回到
   字符串自由动作）。纯语气/关系面策略（sustain_momentum 等）投影为 `no_action`
   （语气是 response directive 参数，不是控制干预）。
8. **A-01 L2 冻结映射跨卡一致性**：`L2_INTERVENTION_TO_CATALOG` 值 ⊆ 本目录
   （测试钉死）——A-01 接线成果不受本卡影响。

## 3. 交付物

| 文件 | 内容 |
|---|---|
| `backend/app/aurora/intervention_catalog.py` | 目录真源：17 item 声明式元数据（结构派生 key 集）+ 2 封闭词表（能力/权限）+ 指纹 + spine 投影映射 |
| `backend/app/aurora/intervention_policy.py` | 引擎：10 守卫纯函数规则核心 + 确定性选择层 + 16 码封闭 reason 词表 + P3-7 构造门 + LLM 通道（默认关） |
| `backend/tests/contract/test_intervention_catalog_contract.py` | 目录冻结测试 29 条：key 集双源互检 / 逐 item 元数据 parametrize×17 / 词表+指纹 sha256 双钉 / L2 与 spine 投影全覆盖 |
| `backend/tests/unit/test_a02_intervention_policy_engine.py` | 引擎测试 77 条：45 场景仿真 / 词表冻结 / 确定性 / 脏输入韧性 / inert 地板 / 构造门 / P3-8×9 / LLM 通道×10 |
| `backend/tests/aurora/fixtures/intervention_policy_scenarios.json` | 45 场景 fixture（38 基线 S 系列 + 7 对抗 A 系列），每条含 factors + 全字段期望 |
| `v3-output/A-02/changes.patch` | 5 文件完整 patch（已在 HEAD 浅克隆验证 apply clean） |
| `v3-output/A-02/intervention_policy_scenarios.json` | fixture 交付副本 |

**零事件/零 DB/零 runtime 改动**：纯增量（5 个新文件），未触碰任何既有模块
（A-01 接线面、spine、orchestrator 均不动——消费接线归 A-04）。

## 4. 证据

### 4.1 目标测试（全绿）

```
SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/contract/test_intervention_catalog_contract.py \
  tests/unit/test_a02_intervention_policy_engine.py -q
→ 106 passed
```

- T1 场景仿真：45/45（卡面 acceptance ②「至少 30 基础」→ 38 基线 + 7 对抗）；
- T2 每场景可投影合法契约（`build_decision_contract` 全 45 条 violations==()）；
- T3 哈希种子无关：`PYTHONHASHSEED ∈ {1,7,42,99,12345}` 五种子 106 passed
  （A-01 P2-1 教训前置化：全部集合断言 sorted/子集语义）；
- T4 回归：A-01 契约 30 + A-01 L2 接线 15 + t313 legacy 25 + tests/aurora/ 102
  + golden 5 + X-02 分配策略 66 → **349 passed**（基线一致，见 4.3）；
- T5 P3-8：delegate/execute/co_execute ×（缺分配/脏分配/匹配分配）三形态
  （3 parametrized × 三段断言）；
- T6 P3-7：构造门 4 类非法输入 → (None, violations) 显式拒绝；
- T7 LLM 通道：默认关（注入 mock 也不调用）/ 非开放选择不调用 / feasible 内
  S1 精化（含 clarify 参数化直达契约）/ 越界 S2（不计熔断）/ 目录外串双保险 /
  失败/超时降级 / 熔断打开后不再调用 / 限频。

### 4.2 变异必红（7 组，单文件粒度改动→红→还原；备份 /tmp/a02-mut/，diff 校验）

| # | 变异 | 结果 |
|---|------|------|
| C1 | 删 practice 元数据条目 | collection error：`InterventionCatalogError: catalog metadata missing for frozen intervention 'practice'`（import fail-fast，模块级红） |
| C2 | 删 remind 的 expected_outcome 字段 | collection error（构造校验红） |
| C3 | practice `requires_task_context` True→False | 4 failed（指纹钉 + S10/S29 场景 + 严格布尔） |
| E1 | 删 R4 守卫（P3-8 静默放行变异） | 8 failed |
| E2 | 删 R0 检查（自由串提名放行） | 6 failed |
| E3 | 删构造门 clarify 检查 | 4 failed |
| W1 | R4 reason 码改名（词表漂移） | 9 failed（词表 sha256 + 场景双红） |

变异纪律事故记录（透明披露）：C3 全输出验证轮漏了一次还原，被**终验红**当场
捕获（4 failed），用最初备份恢复后 106 passed 复绿——终验必跑的价值实证。

### 4.3 基线

基线 = A-01 目标套件在本卡开工前 177 passed（152+t313 25，与 A-01 REPORT §4.1
一致）；本卡改动后同一扩集（+A-02 106 +X-02 46+）= 349 passed，零回归。
A-01 REPORT §4.3 的预存失败集（spine-17/event_registry-1/decision_loop-2 等）
不在本卡目标集内、未触碰。

## 5. 验收对照

- [x] **每个 catalog item 有 capability/permission/expected outcome；无「字符串自由动作」**
  （逐 item parametrize×17 + 词表封闭 + selected 恒目录成员断言（45 场景）+
  目录外提名/卡面漂移串 R0 拒绝（A1/A2/A4）；变异 C1-C3 必红）
- [x] **至少 30 基础 scenario 可输出合法决策**（38 基线 + 7 对抗 = 45，每条输出
  合法决策且可投影合法契约；对抗面：非法组合/权限不足/上下文缺失/分配缺失/
  预算耗尽/静默时段 → 全部确定性拒绝而非 LLM 兜底）
- [x] **Work 1 映射现有 adaptive_replanner/predicted_reply/policies**（§1 + §2.7 +
  spine 投影全量覆盖测试；RUNTIME_MAP 角色沿用不重判）
- [x] **Work 2 规则先过滤，LLM 只在合法集合内选/参数化**（feasible set 代码边界 +
  S2 拒收 + 默认关；X-02 同构）
- [x] **Work 3 记录 policy version 与选择理由**（封闭 16 码 reason 词表 sha256 双钉；
  version+指纹+why 进 evaluation.to_dict() 与契约 annotations）
- [x] Forbidden 全项：不重建真源（词表 import 派生/分配 rubric 归 X-02/spine 表
  不动）；无 mock 冒充（mock 仅测试边界）；真实 LLM 0 次；不弱化守卫（零既有
  模块改动，349 回归绿）

## 6. 改动文件清单（收工 status 比对基线）

```
?? backend/app/aurora/intervention_catalog.py                    （目录，新）
?? backend/app/aurora/intervention_policy.py                     （引擎，新）
?? backend/tests/aurora/fixtures/intervention_policy_scenarios.json（fixture，新）
?? backend/tests/contract/test_intervention_catalog_contract.py （契约测试，新）
?? backend/tests/unit/test_a02_intervention_policy_engine.py     （引擎测试，新）
?? v3-output/A-02/{REPORT.md, changes.patch, intervention_policy_scenarios.json}（交付物）
```

（零修改文件：纯增量卡。）

## 7. 风险与限制

1. **未接线运行时（by design）**：引擎与目录是 A-04 联合接线日的消费面
   （RUNTIME_MAP 全部 🟡 行）；本卡交付的是可评测选择空间 + 构造门，接线前对
   用户行为零影响。
2. **因子面为 flat 投影**：quiet_hours/materiality_sufficient/proactive 预算等因子
   目前由测试直接供值；生产装配（从 policies/v1.0.yaml 的 proactive_policy/
   materiality_threshold 与 L0/spine 状态投影）属 A-04——policy 版本真源仍是
   `aurora_policy@v1.0`（policy_loader），本引擎版本 `aurora_intervention_policy.v1`
   只管选择规则自身。
3. **nominal_execution_mode 是标称镜像**（hybrid 居多：计划变更经用户确认——对齐
   A-01 L2 接线先例）：X-02 分配事实存在时以分配 mode 为准；A-04 若让标称值与
   分配面冲突，走 `consistent_with_allocation`，不得另立第三套判定。
4. **语义层灰区定义较宽**：`semantic_eligible` = 无合法提名 + feasible 含非 inert。
   若实践中发现开放选择过频（LLM 进场过多），A-04 可收紧（如要求不确定度信号）；
   通道默认关，收紧无兼容性成本。
5. **spine 投影映射是静态快照**：`_RULE_TABLE` 新增策略而未同步映射 → 契约测试
   双向精确断言即红（强制同步的机制已就位）；shadow learning 若引入第三种动态
   切换值需补映射（当前仅 `switch_to_worked_example` 一种，已覆盖）。
6. 预存失败集（A-01 §4.3）不在本卡范围，未修。

## 8. 后续（非本卡，A-04 接线日清单）

- 因子装配：DecisionContext（C-01 pack）→ InterventionPolicyFactors 投影器
  （capabilities/permissions 从 interaction_model_registry 与 kill switch 态派生）；
- L2 提名接入：`L2_INTERVENTION_TO_CATALOG` 命中值经 `nominated` 进入引擎；
  spine 策略经 `SPINE_STRATEGY_TO_INTERVENTION` 投影提名；
- P3-7 机制化：A-04 read 门消费 `build_decision_contract` 的 None-通道；
- P3-8 升级：allocation 对象级一致性（`allocation_ref` 回填 + 
  `consistent_with_allocation`）在 rescope→ActionPlan 闭环时落硬规则；
- 语义层开启的 settings 化与真实评测（本卡 0 次 LLM，开启属 A-04+）。
