# M-02 REVIEW_RECEIPT — Personalized Storage Gate（该不该记）

- Reviewer：独立 Reviewer（M-02 验收，risk medium / 1 reviewer）
- 日期：2026-09-19 ｜ worktree：`Sparkle-sysrev/wt8`（基线 43942d23 + 8 文件未 commit 改动）
- 交付物核对：`REPORT.md` / `EVAL_RESULTS.md` / `changes.patch` 均在，`changes.patch` 与 worktree 实时 diff 逐字节一致（仅 index 行差异，blob 哈希属 git 元数据）；8 文件（4 改 4 增，1888 insertions）；密钥扫描干净；`backend/.env` 临时副本确认已删（仅剩 `*.example`）。

## 1. 逐条重验结果（Worker 自报 → Reviewer 实证）

| # | 自报 | 重验方式 | 结论 |
|---|---|---|---|
| 1 | gate 模块 + 接入 + kill-switch/指标 + 43 单测 + 64 场景 | 通读 `memory_storage_gate.py`（1038 行，规则层纯 stdlib 首匹配 + 语义层熔断）、`memory_service.py` diff（落点在 `_build_episodic_memory_record` 后、`db.add` 前，veto 短路先于 apply，confirm 静默）、kill-switch 三态绑定、`MEMORY_STORAGE_GATE_TOTAL` 指标；跑 `test_memory_storage_gate.py + test_memory_storage_gate_eval.py` = **43 passed**；fixture 实读 64 场景、五类 15/12/11/14/12 与 EVAL_RESULTS 一致 | ✅ |
| 2 | 修复前任 4 类缺陷 | 3 处漏判单独复跑通过（ev06「6月15日要考四级」→event、cs02「我今天状态不太好」→current_state、ig04「嗯嗯知道了」→ignore）；emo 边界正则实测：「memory summary of this session」不再被 veto、`我要emo了`仍判 current_state、`困难/渴望` 不误伤；settings 注释含模型/超时依据（qwen3.8-flash、3.0s→5.0s） | ✅ |
| 3① | 64 场景 P/R 全 1.0 落盘 + today constraint | 守卫测试亲跑通过（≥50 场景、五类 P/R≥1.0、ev01/ev09 专项）；`test_write_path_event_bounded_scope` 亲跑通过（无 due_at 的 today constraint 落库 decay 压至 7d + `m02:event_bounded` tag） | ✅ |
| 3② | 韧性 + 真实 LLM 冒烟 | 三件套断言逐条读毕且亲跑通过：规则层异常→`error_degraded`/ignore（`test_gate_internal_exception_degrades_to_ignore`）；gate mock RuntimeError→`create_episodic_memory` 返回 None 不上抛（`test_gate_veto_does_not_break_write_path`）；语义层超时/坏 payload/断路器开→规则默认 3 项；`orchestrator.py:1171` 调用点亲查确在 try/except 内且不消费返回值；`memory_inferred_write_lane.py:527` 消费 None→`blocked` 指标 | ✅ |
| 4 | 回归 181 过 / 2 失败基线预存 / 1 环境性 | 受影响域定向回归亲跑：87 passed / 1 failed（`test_two_consecutive_sessions_prompt_includes_inferred_memory`）；**基线对照亲自做**：将 4 个改动文件 checkout 回 HEAD 后两失败用例仍失败（含 achievement_engine 那条），证实与 M-02 无关，随后从备份完整恢复（恢复后 40 gate 测试复跑全绿）；`test_focus_service_memory` 收集错误复现——gen 文件虽在但包不可导入（`ModuleNotFoundError: app.gen.sparkle.inference`，`__init__` 链缺失），环境性成立；M-01 守卫四组亲跑 **26 passed**（epistemic contract/conflict guard 14 + migration sqlite + inference write guard） | ✅ |
| 5 | 残留四项 | 与代码事实相符：语义层默认关（settings `SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED=False`）、fail-open 由 R10+lane 置信度兜底、R8 单进程 TTL-LRU（30min/4096）+ 注释声明 ConflictResolver 为跨进程权威 | ✅ |

本伦理性裁决抽查通过：R2 显式口令 > R4 敏感（st13「帮我记住我有抑郁症」→store，`test_rule_explicit_command_overrides_sensitivity`）；语义层 confirm 不得自授权（降级 store + `S1.semantic_confirm_demoted`）；B2/B3 显式 lane 敏感照写属声明过的设计（治理 UI 可删）。

## 2. 评测集难度审视（Reviewer 独立评估）

64 场景五类分布均衡，但**易题占比约 1/3**：ignore 类 14 例中 11 例为单 token 噪声（好的/哈哈/再见/嗯…）；store 类 15 例中 5 例由 B2/B3 元数据旁路直接判定（与内容无关）；event/current_state/confirm 三类质量较好。真正边界题约 10-12/64（ev12 混合句、cf10 敏感>事件、ig11a/b 去重对、cs11 焦虑≠焦虑症、ev06/cs02/ig04 三个修复位）。**注意：P/R=1.0 是规则与同一 fixture 共同迭代的结果**（3 处修复本就是 fixture 场景），泛化性证据来自 fixture 外 13 例单测负例 + 本 Reviewer 13 例探针（见 §3）——1.0 应读作"回归守卫下限"而非"通用精度"。总量与验收口径（50+）满足，分布可接受。

## 3. Reviewer 自造对抗探针（fixture 外，13 例，如实记录）

| 探针 | 预期直觉 | 实测 | 评价 |
|---|---|---|---|
| 「周五再看看」 | 非事件 | store (R10, semantic_eligible) | 可接受： deliberative 无事件语义，语义层开时精化 |
| 「周五要交实验报告」 | event | event (R5) | ✅ 轻动词路径正确 |
| **「明天不用去考试了」** | 非 event | **event (R5)** | ❌ **假阳**：`(?<!不)` 只锚定动词紧邻位，「不用去X」经模态前缀绕过否定守卫；bounded scope 限制了危害，建议后续修 |
| 「明天不用提醒我」 | ignore | store (R10 fail-open) | 边界：属报告已声明的 R10 残留类（语义层开时覆盖） |
| 「明天我不考四级了，改下个月」 | 非 store-global | store (R10) | 同上，R10 残留 |
| **「以后每天早上八点背单词」（真重复）** | store/global，**不得误判 oneshot** | **store (R10)** | ✅ **关键边界通过**：「每天早上」不匹配 oneshot 锚点，未被压 7d |
| 「每周三下午有实验课」（真重复） | store | store (R10) | ✅ 未误判 event；但注意系「裸周三非锚点」所致（见下） |
| 「我每次考前一晚才复习」 | store | store (R9) | ✅ |
| 「哦豁又挂了，真是太好了」（反讽） | current_state/ignore | store (R10) | 残留，如实记录 |
| 「真是绝了，图书馆抢了个寂寞」（反讽） | ignore | store (R10) | 残留，如实记录 |
| 「我周三下午有组会」 | event | store (R10) | 边界：裸工作日锚点不对称——周五/六/日为裸锚点，周一~周四仅带钟点才命中 |
| 「我要emo了 / 我今天很emo」 | current_state | current_state (R6) | ✅ emo 边界修复生效 |
| 「刚开始很困难，但我渴望学会」 | store | store | ✅ 困/渴 无误伤 |

探针结论：三处修复位+emo 修复全部实证；today-constraint 语义（瞬时短窗 vs 真重复不误判）通过；发现的 1 个假阳（模态前缀否定）与 2 类锚点/词表覆盖缺口均落入已声明的 R10/语义层设计包络，**不破坏验收标准**，建议随下轮词表演进修（否定守卫扩展到模态前缀之前、裸工作日锚点补齐、「每天/每周」入稳定性词表可让真重复显式走 R9）。

## 4. 文档小出入（不影响验收）

1. REPORT 称 `test_memory_storage_gate.py`「共 43 项」——实际该文件 40 项，43 为与 eval 测试合计（自报口径混乱，总数正确）。
2. 自报「gate 997 行」已过期，实际 1038 行（REPORT 写 ~1030，正确）。
3. M-01 守卫「15 项」与我实跑四组 26 项不一致（统计口径差异；全绿事实无争议）。

## 5. 结论

验收①（50+ 场景 P/R 落盘 + 可复现守卫 + today constraint 不默认 global，且真重复不误判 oneshot）与验收②（gate 任意故障降级不炸写路径、orchestrator 主链 try 包裹实证）均独立复核通过；接续修复的 4 类缺陷、2 处基线预存失败（stash 对照亲自复现）、patch 一致性与收工清理均属实。对抗探针发现的边界缺口已在 §3 如实记录，属后续打磨项。

VERDICT: ACCEPT
