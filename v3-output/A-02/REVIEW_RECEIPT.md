# A-02 · Intervention Catalog + Policy Engine V1 — R1 验收回执

- **Reviewer**：R1（A-02 medium 单验收，R1+R2 合一深度；不信任自报，独立重验）
- **审查树**：wt4 @ `873ba1a4`（detached，未动）｜交付：untracked 5 文件 + `v3-output/A-02/`
- **总 Verdict：✅ ACCEPT**（零必修；3 条建议级备注，均不阻塞合入）
- 真实 LLM 0 次；主仓只读；变异用 /tmp 备份还原法，收工 sha256 校验树未污染

---

## 1. 逐断言 Verdict（Worker 7 项核心声称）

### 声称 1：目录 key 零抄写（import 派生）+ 卡面漂移串 R0 拒绝 — ✅ PASS
- 读码：`intervention_catalog.py` `_build_catalog()` 按契约词表迭代构造，`unknown = set(_ITEM_METADATA) - set(AURORA_INTERVENTION_TYPES)` 与缺项双向 fail-fast（import 期）；模块内无『coexecute/connect』等词表外枚举字面量。契约测试独立 `from app.core.aurora_decision import AURORA_INTERVENTION_TYPES` 双源互检（test_catalog_keys_equal_frozen_contract_vocabulary）。
- **变异 A 实操重放（验收要求 2 原样执行）**：临时从 `app/core/aurora_decision.py` 词表删除 `"practice"`（/tmp 备份）→ 两测试文件 collection error：`InterventionCatalogError: catalog metadata has entries outside the frozen contract vocabulary` → `git checkout --` 还原 sha256 OK。fail-fast 属实。
- 卡面漂移串：fixture `A4_spell_drift_card_typos_rejected` 提名 `coexecute`/`connect` → R0 剔除 + `no_action`（我独立推演复核一致）。

### 声称 2：逐 item 元数据完备 — ✅ PASS
- 17 item 全数携带 capability（7 词表）/permission（6 词表）/expected_outcome/requires_task_context/requires_allocation+allocation_modes/is_proactive/is_inert/nominal_execution_mode；构造期 `_validate_item` 强制词表子集、非空 outcome、inert⟺{no_action,abstain}、inert 无 mode、actionable 有 mode。
- 契约测试 parametrize×17（29 collected 实测）+ capability/permission sha256 双钉（`79cb8cd787feff73`/`1187ca43db517456` 字面钉值独立复算一致）。语义判据（任务锚点/分配要求逐项归属）逐条读判，与 AURORA_V3 §2 及 A-01 契约 inert 域一致，无越权分配 rubric。

### 声称 3：10 守卫 + 16 码双钉；P3-8 硬化；P3-7 预留 — ✅ PASS
- `_guard_reasons` 逐条读判：R1 能力/R2 权限/R3 任务锚/R4 缺分配/R5 mode 冲突/R6 quiet hours/R9 预算（proactive 专属、显式请求可豁免）/R7 冷却（只剔目标且不剔 inert）/R8 materiality（非 inert、显式请求可豁免）——抑制门（R6/R8/R9/X1）与结构守卫（R1-R5）的豁免边界与声称一致。
- 16 码 `INTERVENTION_POLICY_REASONS` 精确集 + sha256 `9264ba28d6af0f64` 字面钉复算一致。
- **独立推演 3+1 条（非 fixture 期望，自推导）**：① delegate 全前提但缺 `allocation_mode` → R4 + no_action/D2；`allocation_mode:"AUTO"` 归 None 同 R4；② `coexecute`/`connect` 提名 → R0；③ 空因子 → no_action 出口 + inert 地板（cooldown 指向 no_action 亦不剔）；④ 附加：缺权限 retrieve 显式请求仍 R2（结构守卫不豁免）、materiality 不足 + 显式请求 → rescope + X1（抑制门豁免）。全部与代码及 fixture 期望吻合。
- P3-7：`build_decision_contract` 先构造后 `validate()`，violations 非空 → `(None, violations)`；clarify 缺 question/词表外 tier/裸 ref/伪造 selected 均有测试。

### 声称 4：no_action 确定性出口；LLM 通道默认关 + S2 + 熔断/限频/超时降级 — ✅ PASS
- `evaluate_intervention_policy` 纯函数、内异常 → `E1.degraded_to_rule_default` 降级；对抗 7 场景（A1-A7）全部确定性路径，无 LLM 兜底分支。
- `InterventionPolicyEngine(semantic_llm=None, semantic_enabled=False)` 缺省恒关（注入 mock 也不调用，测试钉死）；S2 越界拒收不计熔断；熔断 3 次/300s、限频、超时降级规则缺省均有测试。构造器注入、无 settings 依赖 → **真实 LLM 0 次属实**。

### 声称 5：spine 34 策略串全量投影 — ✅ PASS
- **主仓 grep 实数**：`_RULE_TABLE` primary 唯一值 20 + secondary 唯一值 13 + shadow learning 动态值 `switch_to_worked_example` = 34；与 `SPINE_STRATEGY_TO_INTERVENTION`（34 条）**双向精确零差**（首次 diff 出现的 2 条『多余』系我正则漏数字 `48h`，修正后 missing=[]/extra=[]）。
- 「纯语气策略→no_action」映射存在：`sustain_momentum`/`encourage_partner_observed_morale` → `no_action`；契约测试强制覆盖（`test_spine_rule_table_strategies_fully_mapped` 对 `_RULE_TABLE` 运行时枚举双向断言 + 语义族覆盖测试）。
- **投影是映射表、非运行时接线**：全仓 grep 无任何既有模块 import `intervention_catalog`/`intervention_policy`（仅测试）；spine `_RULE_TABLE` 零改动（349 回归绿佐证）——「未接线 by design」属实。

### 声称 6：106 targeted + 349 回归 + 五种子绿；7 组变异红 — ✅ PASS（实跑复核）
- 106 targeted 实跑绿（29+77 实数吻合）；PYTHONHASHSEED 7/99 两种子实跑绿（抽 2/5）。
- 349 回归**精确复跑**：A-01 契约 30 + A-01 L2 接线 15（`test_a01_aurora_decision_l2_wiring.py`）+ t313 25 + tests/aurora/ 102 + golden 5 + X-02 分配策略 66 + A-02 106 = **349 passed**；另加跑 X-02 eval/guard 46 条亦全绿（380/380）。
- 变异重放（抽 2）：A=删契约词表项（见声称 1，import 红）；B=`intervention_policy.py` R4 append→pass → **6 failed**（S13/S37 fixture + P3-8 参数化）→ 备份还原 sha256 OK → 复跑 106 绿。Worker 报 E1=8 failed，我重放 6 failed：变异形态略异（我保留 R5 elif），红 verdict 一致，无实质出入。

### 声称 7：透明披露（基线偏差 + 变异漏还原事故） — ✅ PASS
- REPORT §开头披露开工树 b9a48bdb≠873ba1a4 并 detach 对齐（现 HEAD 实测 873ba1a4 detached，树全空期操作、无 untracked 损失风险，操作正当）；§4.2 披露 C3 漏还原被终验捕获——披露完整、可信。

## 2. 验收要求逐项核对

| # | 要求 | 结果 |
|---|------|------|
| 1 | 改动面：纯增量 5 文件 | ✅ `git status` 实测恰 5 个 untracked + v3-output/；`git apply --check --reverse` patch↔树逐字节一致；patch 仅含 5 文件；无密钥/夹带（grep 实证） |
| 2 | 拼写地雷验证 | ✅ import 派生 + 变异 A fail-fast 必红（原样重放） |
| 3 | 守卫语义抽验 | ✅ 10 守卫逐条读判 + 3 场景独立推演 + 对抗 7 场景确定性（R0/R4/R5/R6/R7/R8/R9 fixture 全覆盖实证） |
| 4 | spine 投影真实性 | ✅ 34=34 双向精确；映射表非运行时替换；spine 零改动 |
| 5 | 测试实跑 | ✅ 106 + 349 精确复跑 + 2 种子 + 2 变异重放，全符合 |
| 6 | X-02/A-01 边界 | ✅ 零八维 rubric 复制（rubric 字样仅边界声明）；imports 仅 A-01 契约词表 + ExecutionMode；无 action_allocation 模块依赖；allocation_mode 以 flat 因子消费（输入事实，非重算） |
| 7 | A-04 施工就绪度 | ✅ 见 §4 前置清单 |
| 8 | 合入预演 | ✅ 对主仓 873ba1a4 浅克隆 `apply --3way --check` CLEAN（clone 用后即删）；与 wt8/X-05 零路径重叠（见 §3） |

## 3. X-05（wt8）重叠预测
- wt8 在途改动：`api/v1/router.py`、`core/event_registry.py`、`main.py`、gateway proxy_routes、`tests/conftest.py`、mobile + 新增 agent_run 族（models/services/api）。与 A-02 五文件**零路径交集、纯增量对纯增量** → 合并冲突风险：无。
- 唯一注意点：wt8 改 `backend/tests/conftest.py`（全局收集面）——A-02 测试自包含（无 conftest fixture 依赖），预计无干扰；integration HEAD 重跑时以 A-02 106 条作为冒烟即可。

## 4. A-04 前置清单（供 Leader，RUNTIME_MAP 视角）
1. **因子装配投影器**（最大缺口，engine 现由测试直供因子）：C-01 pack/SignalSnapshot → `InterventionPolicyFactors`；capabilities/permissions 从 interaction_model_registry + privacy kill switch 派生；materiality 从 `decision_fns/materiality.py`（🔵 读侧即投影）；quiet_hours/budget 从 R-01/R-07 + `policies/v1.0.yaml` 顶层阈值面。⚠️ 投影须供**严格布尔/枚举**（见备注 N3）。
2. **提名通道接线**：L2 命中（R-03 已示范，`L2_INTERVENTION_TO_CATALOG`）→ `nominated`；spine 策略经 `SPINE_STRATEGY_TO_INTERVENTION` → `nominated`；R-08 decision_loop 提名反查目录。
3. **决策投影点（🟡 行逐个落）**：A-01 `safe_route` stay/transition → `build_decision_contract`（RUNTIME_MAP 指定的第二接线点）；A-03 backbone、A-06 escalation、R-02 L1、R-06 EnergyDecision→cognition_tier、R-07 wake、A-11/R-04 L3 会话进入。
4. **P3-7 read 门机制化**：统一 read 门消费 `build_decision_contract` None-通道；A-08 `TransitionDecisionRecord.evidence_refs` 升级契约 scheme（迁移期双写）。
5. **P3-8 升级**：allocation 对象级一致性——`allocation_ref` 回填 + `consistent_with_allocation` 硬规则（rescope→ActionPlan 闭环时）。
6. **语义通道开启**：settings 化开关 + A-17 `llm_bridge` 作 semantic_llm 提供方 + 真实评测；监控 `semantic_eligible` 触发频率作收紧判据（默认关，收紧零成本）。
7. **治理面**：`governance_mode=shadow` 不得作用用户可见行为的 read 门 + A-20 shadow/live `decision_id` 锚点对。
8. **投影同步纪律**（长效）：`_RULE_TABLE` 新增策略 → 契约测试双向断言即红强制补映射；shadow learning 引入新动态切换值需补映射（现仅 `switch_to_worked_example`）。

## 5. 建议级备注（非阻塞，无需返工）
- **N1**：`SPINE_STRATEGY_TO_INTERVENTION` 的**值侧语义**（策略→目录成员的具体归属，如 `nudge_task_start→remind`）未被内容钉死——键集等值 + 值∈目录有测试，但语义重映射不会红。属本次评审人工把关范畴（已逐条读判，归属合理）；建议未来 bump 版本时对全映射 dict 加 sha256 钉（与 reason 词表同款）。
- **N2**：catalog `_INERT_NAMES` 为本地字面量（未 import A-01 私有 `_INERT_INTERVENTIONS`，避免私有符号耦合——合理取舍）；若 A-01 未来扩 inert 域，catalog 不会自动 fail-fast，但 `build_decision_contract` 的 None-通道会在契约面兜住。A-04 接线日在清单 §4.4 中留意即可。
- **N3**：`coerce()` 对 `materiality_sufficient`/`proactive_budget_available` 用宽松 `bool()`（非 None 即取真值；`""`→False 与缺省 True 不对称）。确定性不受影响、fixture 全用真布尔，但 A-04 因子装配须供严格布尔/None（已在 §4.1 标注）。

## 6. 实跑命令清单（R1 独立执行）
```
# 状态与改动面
git -C wt4 status --short / rev-parse HEAD
git apply --check --reverse v3-output/A-02/changes.patch          # patch↔树一致
# 词表/投影实数
grep AURORA_INTERVENTION_TYPES backend/app/core/aurora_decision.py（17 项）
正则提取 _RULE_TABLE primary/secondary + shadow → 与 SPINE_STRATEGY_TO_INTERVENTION 双向 diff（34=34）
# 测试
SECRET_KEY=test python3.11 -m pytest tests/contract/test_intervention_catalog_contract.py tests/unit/test_a02_intervention_policy_engine.py -q   # 106 passed
PYTHONHASHSEED=7 / =99 同上两轮                                                                                    # 106 passed ×2
SECRET_KEY=test python3.11 -m pytest tests/contract/test_aurora_decision_contract.py tests/unit/test_a01_aurora_decision_l2_wiring.py tests/unit/test_t313_l2_intervention.py tests/aurora tests/golden tests/unit/test_action_allocation_policy.py tests/contract/test_intervention_catalog_contract.py tests/unit/test_a02_intervention_policy_engine.py -q   # 349 passed
（另加 X-02 eval/guard 46 条 → 380 passed）
# 变异重放（cp /tmp/a02-review-mut 备份 → 改 → 红 → 还原 → sha256sum -c OK → 复跑 106 绿）
A: 删 app/core/aurora_decision.py 词表 "practice"        → InterventionCatalogError import 红
B: app/aurora/intervention_policy.py R4 append→pass      → 6 failed
# 独立推演（evaluate_intervention_policy 直调，自推导期望）
R4 缺分配/脏分配、R0 漂移串、no_action 出口+inert 地板、结构守卫不豁免、X1 豁免 → 全符合
# 合入预演
git clone 主仓 → checkout 873ba1a4 → git apply --3way --check changes.patch → CLEAN（clone 已删）
# 边界 grep
新模块 imports 清单；rubric/decide_allocation/action_allocation 依赖 → 仅 docstring 边界声明，零代码依赖
零运行时消费者（grep 全仓）→ 纯交付面
```

## 7. 收工状态
- wt4 HEAD 未动（873ba1a4 detached）；`git status --short` 与开工一致（5 untracked + v3-output/，新增本回执）。
- `/tmp/a02-review-mut/` 备份与 `/tmp/a02-merge-rehearsal/` 克隆已清理；两变异文件 sha256 复验还原。
- 真实 LLM 0 次；未 commit/push；主仓与 dev DB 只读未触碰。
