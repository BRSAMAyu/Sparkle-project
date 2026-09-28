# V4-B03 · limitations — 边界与限制

## 证据层级边界

- A-08（修前/修后）与 Q-04 产物均为 **L1 可控服务模拟**（sqlite 隔离 + fakeredis + 可控时钟；A-08 零真实 LLM，Q-04 零模型 judge）。冻结结论只覆盖模拟面，**不是 live/真人证据**，不外推真实学习效果或商业结果。
- E-08 产物为真模型活栈测量（run `cdc547be`，145 次调用）。本卡只对其 raw 做 RECOMPUTE，未发起新调用；V4 复测需另立预算卡。
- 本卡全部产出层级为 RECOMPUTE（对既有 raw 的确定性复算）+ TEMPLATE（模板）。**没有任何新 RUN**；`paired_baseline.jsonl` 全部 execution_status=NOT_RUN，不得被引用为「已执行」。

## 覆盖边界

- 配对集 20 对是从 72 场景中按「四臂可区分 + 负结果判据面」选出的**基线种子**，不是全集；VIS/SEN/DAT/RUN/SOC/RET 家族未纳入本卡（它们绑定 V4-B04 视觉 harness 或其他 Q 卡，届时可增补配对行，增补需走同目录新行而非改写冻结行）。
- holdout 数据未生成（TEMPLATE_ONLY）：30/120 episode 的实际生成、seed 敏感性检查、bootstrap 区间属后续执行卡（需模型预算授权）。B03 只冻结 schema、隔离规则与分母政策。
- Q-04 的「NOT_REMEASURED」状态以 B03 冻结时点为准；若并行会话在集成前完成全量重跑，应以其新证据更新状态而非引用本行（本行冻结的是首轮+修而未复跑事实）。

## 已知偏差与不确定性

- A-08 修前→修后对照跨多个主干变更（非单变量归因）；冻结的 9/20、11/20 是「修后叠加态」读数，机制归因见 wt412 报告。
- PYTHONHASHSEED 依赖：A-08 harness 自述 argmax 次序依赖字符串哈希序（已登记引擎问题）；复算不受影响（只数 episode_end/episode_fail），但重跑复现需固定 seed。
- WT404 dashboard.json 的 generated_at/git_sha 时间戳字段每次生成会变；本卡钉的是文件内容 sha256，审查复算时应比对统计量而非时间戳。
- E-08 percentile 复算使用 harness 同款线性插值 `_pct`；若未来 harness 改 percentile 算法，探针④需同步口径（探针已内置与报告数字的绝对值断言，会显式失败而非静默漂移）。

## 防伪造声明

- review_receipt.json 置 NOT_SIGNED：独立审查未发生。审查者请直接运行 `python3 v4/evidence/V4-B03/recompute_baselines.py`（预期 exit 0），并抽查源产物 sha256。
- 本目录任何文件不构成「自适应优于不用记忆」「越用越懂」类主张的正面证据；相反，冻结的负结果要求上述主张在 M08–M14 联合通过前保持不可用（CLAIMS_LEDGER）。
- 零分母=N/A 政策冻结后，任何以「0/0=100%」形态出现的下游汇总都应视为违反本基线。
