# A-01 · R1 标准验收回执（含 R2 两轮结论背书 + 返修 delta 背书）

- Reviewer: R1（wt9 独占，标准验收路线）
- 对象: wt9 HEAD `cba29db1` + 交付（1 M + 3 A + `v3-output/A-01/` 四件套）
- 主仓参照: 只读。任务书下发 `690541e3`（E-02 合入点）；实际验收时主仓 HEAD 已推进至 `b9a48bdb`（M-05 亦已合入）——**两点均做了合入预演**（见 §6）
- 方法: patch 双端校验 + 词表对照真源 + 变异重放 1 组（M-A）+ 映射抽检 3 组件（跨 3 层级）+ 目标套件双种子实跑 + 预存失败只读归因 + 边界四声明字段级 grep 对照 + R2 delta 亲验 3 处
- 纪律: wt9 树零 stash/reset/clean/切分支；探针全部 /tmp 即删；真实 LLM 0 次；未 commit/push

---

## 1. 改动面核对 — **PASS**

- `git apply --check --reverse changes.patch`（wt9 内）: **exit 0**，patch↔工作树一致。
- patch 文件清单 = `l2_intervention.py`(M) + `aurora_decision.py`/`test_aurora_decision_contract.py`/`test_a01_aurora_decision_l2_wiring.py`(A)，与 REPORT §6 声明一致，不含 v3-output 自身，无夹带文件。
- 密钥/敏感串扫描（api_key/secret/password/PRIVATE KEY/sk- 模式）: **0 命中**。
- 格式化噪声: 唯一 M 文件的 3 行删除均为 legacy `logger.info` 参数列表扩展（P2-3 返修内容，日志前缀 `L2 escalation: user={} pattern={} intervention={}` 逐字保留），其余 154 行为纯追加。diff 集中在契约+接线+测试四面，零无关重排。
- patch 保真复验: /tmp 浅克隆（HEAD cba29db1）apply 后与 wt9 工作树 **4/4 文件逐字节 IDENTICAL**。

## 2. 卡面对照 — **PASS**

**契约冻结（卡 Work 2/3 + Acceptance）**:

- 词表对照真源 `v3/02_core_systems/AURORA_V3.md` §2 逐项核对: 干预目录 **17/17 精确一致**（CLARIFY…NO_ACTION ↔ snake_case，含 `co_execute`/`connect_peer`）；uncertainty 6 类 / tier 6 档 / no-action 7 项 / governance {live,shadow} 与卡面三态规则一致；**`off` = 无契约实例**在词表与 docstring 双处落地（`aurora_decision.py:44-50,131-132,145-146`）。
- 版本戳 `AURORA_DECISION_SCHEMA_VERSION = "aurora_decision.v1"` + extend-only 纪律 + validate() 违规制（与 C-01 同约定）均在。
- 契约测试存在性: `test_aurora_decision_contract.py` **30 tests**（词表精确集+sha256 双钉/字段指纹/交叉规则/往返/确定性 id/X-02 一致性）+ `test_a01_aurora_decision_l2_wiring.py` **15 tests**（含映射全员覆盖纪律 `test_every_escalation_pattern_has_catalog_mapping`、2 条 decision_id 日志观测 `:198/:221`），计数与 REPORT 一致；单独复跑 **45 passed**。
- **变异重放 1 组（R1 独立执行，M-A）**: 目录加第 18 项 `escalate_emergency_18th` → `2 failed`（`test_intervention_catalog_is_aurora_v3_section2` 精确集 + `test_vocab_sha256_pins` 双钉）→ 还原 diff 校验通过。变异必红声明属实。

**Runtime 映射 44 组件（卡 Work 1）**——抽检 3 个，跨 3 层级，全部与真实代码一致:

| 抽检 | RUNTIME_MAP 行 | 实勘 |
|---|---|---|
| aurora 层 | A-01 `engine.py` 四方法 | `materiality_check:54 / decide_backbone_route:59 / dispatch_trigger:91 / safe_route:219` 全在 |
| runtime_v1 层 | R-06 `energy_controller.py` + R-01 `l0_rules.py` | `EnergyDecision:25 / EnergyLevelDecider:45`；`deadline_pressure/quiet_hours` 属实 |
| orchestration 层 | O-01 `routing_engine.py` | `SufficiencyJudgeService` 引用（:58/:1110）+ `detect_escalation`（:2462/:2479）属实 |

计数自洽复核: 表行 22(A)+14(R)+6(O)+1(S)=43 + §4 治理家族计 1 组 = 44 ✓；决策点 9+10+5+1=**25**（P3-5 勘误后值）✓；**kill switch 23 个经 R1 独立 Python 类名统计证实**（AuroraStage18..40 共 20 + dual_core_router + privacy + doc_context，逐一对上枚举）✓。

**示范接线（卡 Acceptance）**: `check_escalation` legacy dict 五键逐字保留+附加 `aurora_decision` 载荷；`decide()` 纯决策面（只读 `_is_cooled_down`，无 `_mark_intervention`）；非 UUID user_id 走纯 legacy；L2 legacy 面 `test_t313_l2_intervention.py` **25 tests** 全绿（含于 177）+ 2 条新观测测试在位。卡 Acceptance「现有聊天不退化 / shadow-live 可对比 / 契约可追踪 source refs」三项由 legacy 全绿 + `test_shadow_and_live_same_decision_share_id` + 封闭 scheme（裸 token 拒绝有测试）支撑。

## 3. 测试实跑 — **PASS**

| 轮次 | 命令（backend/ 下） | 结果 |
|---|---|---|
| 种子 1 | `PYTHONHASHSEED=1 SECRET_KEY=test python3.11 -m pytest tests/contract/test_aurora_decision_contract.py tests/unit/test_a01_aurora_decision_l2_wiring.py tests/unit/test_t313_l2_intervention.py tests/aurora/ tests/golden/test_aurora_experience_golden.py -q` | **177 passed, 7.79s** |
| 种子 42 | 同上，`PYTHONHASHSEED=42` | **177 passed, 7.82s** |

P2-1 返修（三处 sorted 等价断言 `:69/:84/:144`）实证有效，CI 随机红防线成立。

**预存失败抽 1 归因**: `tests/unit/test_aurora_runtime_decision_loop.py` 在交付树 2 failed / 89 passed。/tmp 基线 clone 因缺 `app.gen`（gRPC 生成代码不入库）无法直接复跑，改用**只读依赖闭包证明**: 失败断言为纯 prompt 文本（`assert 'current_streak_days >= 5' in prompt_rules`）；该测试 import 闭包（chat_adapter/control_surface/dashboard/decision_loop/service/skills/telemetry/write_pipeline/planning_workflow）对 A-01 四文件**零触碰**（全仓仅 `l2_intervention.py` import 契约；`spine_orchestrator`→L2 与 `planning_workflow`→spine 均为函数内延迟 import 且不在该测试路径）。HEAD 与交付树在该闭包内逐字节相同 ⇒ 2 failed **预存归因成立**，与 REPORT §4.3 一致。

## 4. R2 两轮结论背书 — **背书成立**

首轮 Verdict CHANGES 的三大 P2 与 delta 三项 PASS，R1 亲验 3 处（超出抽 1 处要求）:

1. **P2-3 decision_id 日志**: `l2_intervention.py:131-138`（check_escalation，`aurora_decision_id={} catalog={}`，contract=None 记 `-`）与 `:170-176`（decide fired 分支）实勘在位，legacy 日志前缀逐字保留；对应观测测试 2 条绿。
2. **P2-2 归因文本**: 契约 `aurora_decision.py:148-155` 勘正后与 R2 引述的 yaml 事实一致（parameter_write_authority 仅 {ux_intent, aurora_presence}；capability_gate 仅 writable_policy_scope 2/4 变体按变体生效；intervention_preference 为 §4 规格层）；REPORT §2.2 与 RUNTIME_MAP A-10 同步勘正；契约测试 30 全绿证实词表集合值未动。
3. **P2-1 种子修复**: 三处 sorted 断言实勘 + 本轮双种子 177 全绿复证。

R2 首轮 6 组独立变异与 delta 的 M-A 抽检记录与 R1 重放结果（2 failed）一致，**两轮结论均可背书**。

## 5. 边界四声明 — **PASS**

- 契约 docstring 四边界（C-01 证据装配 / X-01 任务结构 / X-02 执行分配 / Aurora 控制决策）+ 命名消歧 + 三态规则完整（`aurora_decision.py:15-54`）。
- **字段级重叠 grep**: `intervention_type / governance_mode / no_action_reason / cognition_tier / rationale_summary` 五个 A-01 独占字段在 `decision_context.py` / `action_plan.py` / `action_allocation_policy.py` 三契约模块 dataclass 字段中**零定义**——无 A-01 侵占已合入契约字段，反向亦无重复定义。`AllocationDecision.mode`（:324，str 词表）与 `consistent_with_allocation` 的 `ExecutionMode.value` 比较语义一致。
- **边界 scheme 测试存在**: `test_boundary_ref_schemes`（contract 测试 :311-322）双向钉——`action_proposal_ref="goal://…"` 必报 `task:// scheme` 违规、`allocation_ref="task://…"` 必报 `decision:// scheme` 违规；另有 `test_unknown_ref_scheme_rejected` 钉裸 token 拒绝。

## 6. 合入预演 — **PASS（双点）**

- 对 **690541e3**（E-02 合入点，任务书指定）: `/tmp` clone `git apply --3way --check changes.patch` → **exit 0**（l2_intervention.py 3way 干净，3 新文件直加）。
- 对 **b9a48bdb**（主仓当前 HEAD，M-05 已合入）: 同命令 **exit 0**。
- 与 R2 首轮（对 03e23023）三点连成基线漂移链，均干净——E-02（llm/orchestration/workflow 面）与 M-05 未触碰 A-01 四文件，理论零交集**实证**。
- **X-05 重叠预测**: wt8 当前在途面实测 = `backend/app/core/run_state_machine.py`(新) + `v3-output/X-05/`，与 A-01 四文件零交集；按任务书 X-05 将触 agents/services/models 面，A-01 patch 全在 aurora/core-contract/tests 面——**预测零冲突**。唯一注意点: 同在 `app/core/` 目录（不同文件），git 合并无冲突语义。

## 7. A-02 施工准备：拼写对齐表（卡面 :12 17 项 vs 契约 `AURORA_INTERVENTION_TYPES`）

真源裁定: **契约与 AURORA_V3 §2 一致，A-02 卡面 2 处漂移**（与 R2 P3-6 一致，R1 逐项复核证实）:

| # | A-02 卡面 | 契约真源（aurora_decision.v1） | 状态 |
|---|---|---|---|
| 1-10 | clarify/explain/retrieve/rescope/split/schedule/practice/review/delegate/execute | 同左（逐项一致） | ✓ |
| 11 | `coexecute` | **`co_execute`** | ✗ 漂移 |
| 12 | reflect | reflect | ✓ |
| 13 | `connect` | **`connect_peer`** | ✗ 漂移 |
| 14-17 | pause/remind/abstain/no_action | 同左（逐项一致） | ✓ |

**给 Leader 的 A-02 任务书建议**:
1. 卡面 Product objective 勘正两处拼写（`coexecute→co_execute`、`connect→connect_peer`），或在任务书显式声明「卡面字面非权威，以契约词表为唯一真源」。
2. **施工纪律（强烈建议写死）**: A-02 policy engine 不得重抄字面目录，直接 `from app.core.aurora_decision import AURORA_INTERVENTION_TYPES`——词表带 sha256 双钉（`test_vocab_sha256_pins`），任何漂移在契约测试即红，从机制上消灭本次这类卡面漂移。
3. A-02 locks=`aurora-policy`，但若施工中发现词表必须扩项，则触碰 `aurora-contract` lock：须 bump `AURORA_DECISION_SCHEMA_VERSION` + 双 reviewer（A-01 契约冻结声明已写死此纪律）。
4. L2 已有先例可复用: `L2_INTERVENTION_TO_CATALOG` 的「映射全员覆盖」wiring 测试（`test_every_escalation_pattern_has_catalog_mapping`）模式值得 A-02 对 capability/permission 表复用。

## 发现清单（R1 新增）

| # | 级别 | 发现 | 处置 |
|---|---|---|---|
| R1-N1 | 备忘 | 主仓 HEAD 已推进至 b9a48bdb（M-05 合入），超出任务书参照点 690541e3 一格 | 已双点预演均干净，无需动作 |
| R1-N2 | 备忘 | /tmp 浅克隆基线缺 `app.gen` 无法跑依赖 gRPC 生成代码的测试，归因改走只读依赖闭包证明（结论不变） | 记录方法论，供后续验收员参考 |

无 P1/P2 新发现；R2 首轮 3×P2 返修项 delta 全部亲验落地。

---

## 总 Verdict: **ACCEPT（可合入）**

R1 标准面七项全 PASS：patch 双端保真、词表 17/17 对照真源、变异重放红、映射抽检 3/3 准确、双种子 177 全绿、边界四声明零重叠、双点 3way 干净 + X-05 零交集。R2 两轮结论（首轮 CHANGES 三 P2 → 返修 → delta ACCEPT）经 R1 三处亲验**背书成立**。契约本体冻结质量与接线纪律（sha256 双钉、全员覆盖测试、legacy 逐字保留）经两条独立验收路线交叉证实。**建议 Leader 合入并立即派 A-02**（施工时按 §7 对齐表处理卡面拼写，接线日 A-04 注意事项已被 S-01/A-10/REPORT §7.6-7.7 承接）。

---

## 附：R1 实跑命令清单

```bash
# 改动面
git apply --check --reverse v3-output/A-01/changes.patch                    # exit 0
grep -ciE "(密钥模式)" v3-output/A-01/changes.patch                          # 0

# 测试（backend/ 下）
PYTHONHASHSEED=1  SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest \
  tests/contract/test_aurora_decision_contract.py tests/unit/test_a01_aurora_decision_l2_wiring.py \
  tests/unit/test_t313_l2_intervention.py tests/aurora/ tests/golden/test_aurora_experience_golden.py -q   # 177 passed 7.79s
PYTHONHASHSEED=42 SECRET_KEY=test ... 同上 -q                                                              # 177 passed 7.82s
SECRET_KEY=test ... -m pytest tests/contract/test_aurora_decision_contract.py tests/unit/test_a01_aurora_decision_l2_wiring.py -q  # 45 passed
SECRET_KEY=test ... -m pytest tests/unit/test_aurora_runtime_decision_loop.py -q   # 2 failed（预存，归因见 §3）

# 变异重放（单文件粒度，备份→红→还原→diff 校验）
# M-A: aurora_decision.py 目录 +escalate_emergency_18th → 契约测试 2 failed → 还原 OK

# 合入预演（/tmp 浅克隆）
git clone /Users/brsama/code/GitHub/Sparkle-sysrev/wt9 /tmp/r1-a01-baseline
git fetch /Users/brsama/code/GitHub/Sparkle-project main
git checkout 690541e3 -- backend/ && git apply --3way --check changes.patch   # exit 0
git checkout b9a48bdb -- backend/ && git apply --3way --check changes.patch   # exit 0
git apply changes.patch && diff 四文件 vs wt9 工作树                           # 4/4 IDENTICAL
```

（收工：/tmp/r1-a01-baseline 已删；wt9 树状态 5 项与交付一致；未 commit/push）
