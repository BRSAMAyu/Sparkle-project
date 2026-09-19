# C-01 REVIEW RECEIPT 2 — DeepAudit（第二路 Reviewer，深层缺陷与长程风险）

- Reviewer: DeepAudit (wt6 @ e79eed0e)，只读审计 wt5 未 commit 改动 + v3-output/C-01/
- 对象: C-01「DecisionContext / ContextPack 契约冻结」（base 2f52a972）
- 日期: 2026-09-19
- 方法: 主仓只读对照（f01f4ae8 注入位置语义已核）；wt5 内定向 pytest 复跑；/tmp 一次性探针（未触碰 wt5 任何文件）；禁改 Worker 代码
- 复核证据: 契约测试 15/15 通过（独立复跑）；消费者回归 26/26 通过（test_context_focusing + test_memory_eval_service + test_context_pack，独立复跑）；changes.patch 与工作树 diff 逐字节一致

## 裁决: ACCEPT（附下方登记条件；无 P0/P1，4×P2 + 4×P3）

## 发现清单

| # | 级 | 结论 | 摘要 |
|---|---|---|---|
| F1 | P2 | 探针实锤 | degraded_fields 把「治理模式」冒充「降级」：aggregator kill-switch=shadow/off 时三信号全降级、validate() 通过、零日志零指标 |
| F2 | P2 | 代码+测试核对 | 信号 value 投影形状冻结不对称：仅 engagement_state.value keys 被钉死，emotion_hint/srl_phase 未冻结（最短静默漂移路径） |
| F3 | P2 | 探针实锤 | frozen dataclass 内 mutable value dict：DecisionStateSignal.value 可被进程内消费者突变（omitted_counts 有 MappingProxyType、value 漏保护） |
| F4 | P2 | 代码链核对 | omitted_counts 候选集定义偏窄（diversity/semantic-gate/conflict 剔除不可见），语义未写入契约文档 |
| F5 | P2/P3 | 双端复现 | plan_context↔prompts 循环 import：单独 import plan_context / prompts / **context_pack** 三者皆炸（基底即存在，非 C-01 引入；Worker 低报爆炸半径） |
| F6 | P3 | 探针实锤 | _default_signal_projection 非 JSON-safe（UUID/Decimal 穿透）→ v2 扩字段+落库时 to_dict 炸 |
| F7 | P3 | 代码核对 | SituationBrief.decision_context（dict）与 ContextPack.decision_context（契约对象）同名异义，同链路流动 |
| F8 | P3 | 原文件行号核对 | telemetry 遮蔽修复确认零行为变化（shadowing 发生在所有 dict 消费点之后，无下游依赖旧错误值）——干净 |

## 六项审计焦点结论

1. 平行真源漂移：TTL 动态比对（真源流动，设计正确）；字段重命名会被 builder 集成测试抓住（真实聚合器路径）；真正缺口 = F2 + F4。signal TTL==FIELD_TTLS_SECONDS 动态比对是正确取舍。
2. 降级污染：整段降级(None)/逐字段降级/partially-filled 三态可区分度不足（F1）；omitted_counts 在两种降级下均准确（candidates 与信号无关）。
3. 快照反脆弱性：三重摩擦（常量钉死+字段名序+sha256 字面量）足以拦截静默演化；v2 消费者语义未定义但纯进程内无 mixed-version 窗口，可接受。
4. 遮蔽修复：惰性修复，无「突然正确」风险面（F8）。
5. 长链：prompt 面 key 集被测试钉死，token 预算零影响；ContextPack 唯一构造点=builder；热路径 3×get_user_state 与 stage33 先例同量级（instance cache 不跨 build 复用属预存在模式）。
6. 循环 import：F5，必须开 KNOWN_CODE_DEBT_LEDGER 卡。

## 登记条件（合入/后续）

- 必须: F5 开 debt ledger 卡（含三模块单独 import 皆炸的复现命令与触发路径）
- 强烈建议随卡: F2 补 emotion/srl value keys 断言（约 3 行）
- 接入卡前: F1（降级原因编码或观测）、F3（value 只读化）、F4（候选集定义写入契约 docstring）
- 顺手: F6（_convert 加 UUID/Decimal）、F7（命名冲突登记）

## 审计过程产物

/tmp/c01_probe/（探针脚本+diff 比对临时文件）已按 AGENTS.md 收工清理。
