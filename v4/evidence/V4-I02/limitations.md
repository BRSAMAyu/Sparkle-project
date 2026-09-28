# V4-I02 · limitations（如实申报）

## 1. `resolved_episode +1.0` 正例权重在当前 context_pack 面上是"潜在"权重（本卡最重要限制）

上游 M-03/M-01 既有法则：带 `resolved_at` 的 episodic 行 `derive_status → status:resolved`，在 **L0 预筛即被剔除**（集成实测：`PREFILTER reason_counts={"status:resolved": 1}`）。因此经 `context_pack.build` 进入效用门的候选不含 resolved 正例——冻结权重表的 `resolved_episode`/`decision_relevance` 在该面对现存数据不生效（失败/中性条目的筛选与负迁移抑制完整生效）。

- 本卡边界：不削弱/绕过 M-03 合法性检查（硬规则）；让 resolved 正例重新可选属 M-03 契约变更，应由其单一 owner 另卡裁决。
- D 臂评测含义：四臂对比时"正例召回"当前主要落在 neutral/confirmed 行（confirmed_bonus/relevance 生效），不是 resolved 行。

## 2. 集成面类型锚为保守派生：无结构化类型声明时锚为空 → 硬门不触发（如实登记 anchors_unavailable）

一审 R1（CHALLENGE-1）整改后，`context_pack.build` 经 `derive_current_type_anchors` 从当次任务上下文派生 `current_type_anchors` 传入门：只取**结构化类型声明字段**——`plan_context["plan_type"]`（Plan.type）、`plan_context["task_summary"]["by_type"]` 键（Task.type）、`route_intent`（回退 `intent`）——不做自由文本猜类型。效果分级：

- 集成面（flag on）：有任一结构化声明即武装 → 一审探针形态（essay_writing 失败经验 relevance 0.75/1.0）在 pack 面被**硬拒**（`negative_transfer_cross_type`，回归测 `test_flag_on_high_relevance_cross_type_failure_hard_rejected_at_pack_surface` 钉住）；
- **残留限制**：当 route/intent 与 plan 均无任何类型声明（如 `intent=""` 的裸调用、且无 plan_id）→ 锚为空，硬门条件 `bool(current_type_anchors)` 为 False 不触发，异类型失败只剩软路径。此时 metadata 记 `anchors_unavailable=true` + `current_type_anchors=[]`（`test_flag_on_without_type_anchors_keeps_soft_path_and_records_unavailable`），不静默。生产主链（chat.py）恒传 `route_intent or intent`，实际不会落到空锚；
- 派生锚是**路由/计划类别词表**（chat/learn/sprint/LEARNING…），与候选侧 `task_type:*`/`domain:*` 自由 tag 的交集判定按字面值比对（strip+lower）。写入侧 tag 词汇若不与当次声明值同词，跨类型失败按异类型硬拒（FIX52 语义如此：失败只在声明同类型时放行）；同词表对齐归写入侧卡。

## 3. marker tag 词汇（`wrong_followed_decision`/`question`/`control_intrusion`/`task_type:*`/`domain:*`）当前无写入方

权重表后三项靠显式 tag 生效；现存数据不带这些 tag → 对应惩罚项当前为 0（不发明隐藏推断，宁缺勿假）。需要写入侧卡落地 tag 约定后才在真实数据生效。

## 4. required-memory 全拒的处置是 bypass，不是"注入好历史"

query 命中 required-memory 词表且全拒时：回退 V3 预筛后路径（保召回）+ `bypassed=true` + verdict 登记 miss。这意味着该轮污染条目仍在 prompt（同 V3 行为），但评测侧必须把该轮计 recall/门失败——不包装。若评审认为应改为"拒绝注入也不召回"，属行为语义变更，需评审裁决（本卡取保守回退，符合"不能过门"与回滚条款）。

## 5. 门级 precision 无真值

门不产伪 precision 数（空选择 → None=N/A）。precision/recall 的真实数值归 B03 协议四臂离线评测（配对集 `paired_baseline.jsonl`），本卡零模型调用、零 live 预算，不能宣称 D>A/B/C 的任何效果数字。

## 6. 打分权重是冻结初值，不是被证明的最优

`WEIGHT_*`/`PENALTY_*`/TopK=6/阈 0.0 为开发集冻结点（模块常量 + 证据冻结），待 D 臂基线测量后按证据调整；每次调整需过冻结锚测试与独立评审。

## 7. 环境性事实（非本卡代码问题）

- fresh worktree 缺未跟踪生成物（app/gen、gateway gen、mobile gen）；为跑测试/守卫从主检出复制（git-ignore，不入 commit）。首轮 rule guards K/Z/BG 的失败源于此（symlink 指回主检出 / 生成 Dart/Go 缺失），解引用重拷后 86 规则全绿。
- `business_metrics.py`/`context_pack.py` 存量 black 不达标在主检出同态（pre-existing 债），本卡插行遵循局部风格、未重排版（保持最小差量）。

## 8. 审查状态

风险 high → 需 2 位独立会话审查（未参与实现、看原验收）。`review_receipt.json` 由审查会话产出；当前不存在 = 未审查，不是通过。集成 SHA 复验待 Leader 合并流程。
