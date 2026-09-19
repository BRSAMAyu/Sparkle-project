# E-02 R2 Delta 复核收据（返修轮）

- 审计员：R2（wt8 独占）｜ 范围：F1/F2 重放 + 新红测 + 变异抽验 + 合入预演，不做全量（按约定）
- 返修自报：REPORT.md §10 + changes.patch（1643 行）
- 方法：原始 R2 探针逐条重放（零 LLM）+ 3 组变异（cp /tmp 备份法，`cmp` 字节级还原校验）+ 主仓克隆 @ 03e23023 apply 预演 + 单一定义点 grep 验证；/tmp 克隆与备份收工即删；树状态与交付一致（6 M + 3 untracked）

## 总 Verdict：**ACCEPT**（R1 收据 REWORK_DELTA 两发现 F1/F2 均闭环，无新发现）

---

## F1（P1 方法建议类劫持）— Verdict: **PASS**

- **重放（R2 原始四探针 + F1b 两条，全部通过）**：

| 消息 | classify | 根修落点（期望=基线） | 结果 |
|---|---|---|---|
| 怎么记住英语单词更有效率？ | None | targeted_source_rag / knowledge_query_targeted_rag | PASS（文档接地恢复） |
| 如何记住复杂的化学公式？ | None | targeted_source_rag | PASS |
| 有什么记住历史年代的好方法 | None | no_retrieval / no_document_retrieval_signal | PASS（误导 receipt 消除） |
| 我记住了老师讲的重点，接下来该做什么 | None | no_retrieval / no_document_retrieval_signal | PASS |
| 我们小组定的汇报主题是什么来着 | None | — | PASS（我(?!们) 生效） |
| 老师问我这道题的答案是什么 | None | — | PASS（排除 问我 生效） |

- **实现**：`_MEMORY_INSTRUCTION_EXCLUDE_RE` 增补 `怎么|如何|怎样|方法|技巧|妙招|更快|更高效|更有效|记住了|记下了|接下来`，与自报一致。
- **新红测实质**：`test_method_advice_question_keeps_document_grounding` 断言 should_retrieve=True + targeted_source_rag + reason≠memory_class_turn（直接钉住基线行为，非空洞）；完成时/第三方事实两族亦有参数化红测。
- **变异 MF1**（删 F1 排除词族，组平衡保持）：**7 failed 必红**（含两条新 F1 红测）——排除族承重确认。
- **核心正样本不回退**：「帮我记住这个」「我喜欢的电影是什么？」「记住我的学号」三正样本仍 classify 命中 + no_retrieval + lane=fast + fast_tier=True（排除词未误伤主修复路径）。

## F2（P2 lane=fast 虚高两形态）— Verdict: **PASS**

- **F2B 重放（R2 原始五探针）**：聊聊我的进度吧 / 看看我的知识星图 / 根据我的情况给点建议 / 查一下我的错题 / 我的画像准不准 → **5/5 lane=deliberate(trigger=personal_data_or_tool_intent) ∧ fast_tier=False**，一致性恢复。
- **F2A 重放**：R2 原 137 字记忆指令（classify=memory_instruction）→ lane=deliberate(default_deliberate) ∧ fast_tier=False，一致；根修侧 no_retrieval 保留（121–200 字仍免 RAG，仅 tier 如实落默认链）——与自报设计一致。
- **同族闭合**：「记住我的进度」→ 根修 memory_class_turn 保留 + lane=deliberate(personal_data_or_tool_intent) + slim 否决交叉验证（红测含三重断言）。
- **实现与同源**：lane step-7（记忆分支）补 `len≤120 ∧ _light_reply_text_allowed`、step-8 补 `_light_reply_text_allowed` 门；`LIGHT_REPLY_TOOL_INTENT_MARKERS`/`LIGHT_REPLY_PERSONAL_DATA_MARKERS` 单一定义于 capability_lane.py（字面量 grep 全仓仅此一处），standard_workflow.py:2509 纯 import 引用（旧内联清单已删，无第二份字面量）——「未抄第二份」声明成立。
- **变异 MF2-step7**（断记忆分支门）：**1 failed 必红**；**MF2-step8**（断 light_reply 分支门）：**6 failed 必红**——两处接入均承重。

## 复跑与合入预演

- `test_capability_lane.py` **61/61**（45→61）；§8 battery 13 文件 **174 passed**、env 形态 **20 passed**——与自报逐字一致（F4 勘误口径本轮可复现）。
- 主仓克隆 @ **03e23023**：`git diff --stat cba29db1 03e23023 -- backend` 为空（A-01 未合入，llm 面零干扰，与协调方预判一致）；`git apply --3way --check` **exit 0**（6 文件 cleanly + 2 新文件）；真实 apply 后 **61/61 绿**。

## 「姓什么」未扩决策记录 — 评估：**可接受，无需再返**

§10 记录明确：漏报侧（「我的导师姓什么来着」判 None）未扩，理由「返修轮只关假阳性，不在无要求下扩 fast-lane 召回面」。评估同意：该漏报方向安全（落默认链 deliberate，无语义错误、无误导 receipt，仅损失 fast-lane 收益）、频次低，且扩 `叫什么→姓什么` 模式会重新加宽 QUERY 侧假阳性面（本轮 F1b 刚收紧）。边界取舍已落档，处置纪律正确。

## 结论

F1/F2 逐项 PASS，变异 MF1/MF2-step7/MF2-step8 全部必红，新红测断言实质非空洞，计数口径可复现，合入预演干净（patch 对 03e23023 自包含且合后 61/61）。**ACCEPT**——建议 Leader 合入后按 REPORT §7-4 将 V3-FIX-12 更新为 FIXED@E-02；F5（providers 健康键型接缝）转台账另卡。
