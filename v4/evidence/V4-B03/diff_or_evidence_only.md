# V4-B03 · diff_or_evidence_only — 冻结负结果与配对评测基线

- 会话：wtB03（分支 `agent/v4/b03`，基于 main `3c4618cc`，不 push）
- 性质：**纯 fixtures/证据交付，产品代码零改动**；**零模型调用**
- 卡：`v4/04_tasks/cards/V4-B03.md`｜锁：v4-eval-fixtures

## 1. 做了什么（最小增量）

V3 已有四组诚实负结果资产，本卡将其「已知负结果 + 可证伪判据」冻结为 V4 评测基线 fixtures（`v4/evidence/V4-B03/`），并从 `v4/06_evaluation/scenarios.jsonl` 选定配对集、核对逐对可运行性。**不重建 V3、不重置已 DONE 任务的证据。**

### 1.1 冻结负结果台账 `negative_results.jsonl`（5 行）

| id | 一句话 | 冻结判定 | 可证伪判据（探针） |
|---|---|---|---|
| V3-NEG-A08-PREFIX-FULL-0.65 | A-08 修前 full 0.65（13/20）系 pre-fix 历史数字 | HISTORICAL_PRE_FIX | 复算 raw=13/20；引用作最新基线即违规 |
| V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL | 修后 no_memory 11/20=0.55 反超 full 9/20=0.45（utility -9.2 vs 0.0）：记忆面净贡献未证明为正 | FAIL（V4 起点负基线） | 复算 raw=9/20 与 11/20 逐数一致（验收第1条） |
| V3-NEG-Q04-DASHBOARD-NOT_REMEASURED | Q-04 首轮 FAIL（precision 0.0/invalid 10 硬门/过个性化 41.67%/uplift 0.0pp）；FIX-67/68/69/70 修后未全量重跑 | FAIL + NOT_REMEASURED | 复算 dashboard 四统计量；重跑驱动在库，达标才可解除 |
| V3-NEG-E08-SLO-2F | E-08 修后六项 SLO=4 PASS/2 FAIL（L0 TTFT p95 1781ms；L2 total p95 65.4s 较修前上行） | FAIL（V4 LAT 输入） | harness 同款 _pct 复算 raw 逐数吻合 |
| V3-NEG-FIX545-FALLBACK-METERING-BLINDSPOT | 18 条 no_generation_model 中 7 条带 token（L3-06/08/15/18/21/23/26），换标签未解决、成本低估 | OPEN（V4 追踪） | 复算 raw 行集恰为冻结 7 qid |

每行带源产物 sha256 钉扎、证据层级（L1 服务模拟 vs 真模型活栈）与「模拟非 live」边界（验收第1条要求）。

### 1.2 冻结 utility 与范围 `frozen_utility.json`

- 权重冻结：resolved+1 / unresolved−1 / wrong−0.4 / question−0.15 / intrusion−0.6（与 A-08 `aurora_ablation_metrics.v1` 逐项一致，探针⑥核对）
- 四臂 A/B/C/D 定义与共享约束（不能给 D 更多历史后称算法更好）
- 分母政策：0 分母=N/A（不是 0% 也不是 100%）；未解决/缺失样本计入不得排除（验收第3条）
- 基线规则：**最新基线=修后 9/20 与 11/20；禁止拿旧 pre-fix 0.65 作最新基线**（卡面原话与 CLAIMS_LEDGER 对齐）
- 重算与运行分开记账：本卡全部为 RECOMPUTE，零 RUN

### 1.3 配对评测基线 `paired_baseline.jsonl`（20 对）

选配原则：配对集必须能区分「无记忆(B)/V3(A)/V4(C,D) 各臂」（验收第2条）并覆盖负结果的判据面。

- **配对核心 16**：CTX-01..08（scope与效用 → M08/M09/M11/M12/M14）+ COR-01..08（纠正通路 → M13，COR-07 邻接 M17）
- **计量负例对照 4**：LAT-05..08（隐藏分类调用/no_gen带token/unknown价格/失败取消算成本 → M22，判据直接引用 FIX-545/E-08 冻结行）
- 逐对可运行性（如实标注，全部 execution_status=**NOT_RUN**）：
  - V3 臂执行器 **IN_REPO**：`scripts/devtools/a08_run_aurora_ablation_eval.py`、`scripts/devtools/q04_run_personalization_redteam.py`、`scripts/devtools/bench_ai_stack_l0_l3.py` 及对应 backend/tests 目录均在库（已核实存在）
  - V4 C/D 臂执行器 **MISSING**：依赖的 V4-I02/I06/I04/U02/U03/I09/I10 全部 PENDING/NOT_STARTED
  - runner_binding：scenarios.jsonl 原文即「由B04/对应Q卡绑定现仓库」→ 本卡 SPEC_ONLY_UNBOUND，不宣称执行通过

### 1.4 开发/独立 holdout 模板 `dev_holdout_template.json`

TEMPLATE_ONLY（未生成任何 episode 数据）：30 开发 episode 找协议错误→冻结后独立生成 ≥30 profile×4 episode=120 holdout；防泄漏规则（holdout 不给实现 Agent、臂标签不进 AUT 输入、盲评映射分房）按协议与 WT404 blind 先例成文。

### 1.5 可证伪探针 `recompute_baselines.py` + `test_results.json`

六探针确定性复算（纯 stdlib、可重复执行、供独立审查直接运行）：**exit 0，all_ok=true**。要点：

- 探针①：raw 复算 full=9/20、no_memory=11/20，与 summary.json/EVAL_RESULTS.md 一致；no_memory>full 负结果方向成立（验收第1条 ✓）
- 探针②：修前 13/20=0.65 与修后不同——旧数字只作历史锚点（防「拿旧 pre-fix 0.65 作最新基线」✓）
- 探针③：FIX-545 七 qid 实锤复现
- 探针④：E-08 4 PASS/2 FAIL 逐项复现（L0 1781ms、L2 total 65.36s）
- 探针⑤：Q-04 首轮 FAIL 四统计量复现，failed_cases_preserved=true
- 探针⑥：冻结权重与 A-08 一致；0 分母=N/A；未解决计入（验收第3条 ✓）

## 2. 验收对照（卡面三条）

| 卡面验收 | 证据 |
|---|---|
| 重算9/20与11/20一致，记录模拟非live边界 | 探针① all arms 逐数一致；每探针带 evidence_layer+boundary 字段 |
| 无记忆、V3、V4各臂可区分，holdout不泄漏给实现Agent | frozen_utility.json scope_frozen.distinguishability_criterion + paired_baseline.jsonl 臂设计；dev_holdout_template.json 隔离规则（holdout 数据本身未生成，无从泄漏） |
| 0分母为N/A，未解决/缺失样本不能被排除 | frozen_utility.json denominator_policy + 探针⑥断言 |

## 3. tasks.json 状态

V4-B03：`status=IN_PROGRESS`、`implementation_state=REVIEW_READY`、`evidence_verdict=RECOMPUTE_PASS_PENDING_REVIEW`（独立审查与集成 SHA 复验未发生，不自称 DONE）。

## 4. 未做（越界不做）

- 不绑定 V4 场景 runner（B04/对应 Q 卡职权）；不实现 C/D 臂；不重跑 Q-04/A-08（需另立预算卡）；不动 `v4/06_evaluation/` 权威文件（只读引用）。
