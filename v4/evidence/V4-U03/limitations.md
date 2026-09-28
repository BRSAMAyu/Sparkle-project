# V4-U03 · limitations（如实登记）

1. **scope 并发控制为客户端读前核对 + 后端行锁兜底，非端到端乐观锁**。后端 `PUT /memory/provenance/items/{kind}/{id}/scope` 契约无 `expected_version` 入参（M-08 契约归其 owner；本卡锁 ui-memory 不越界改契约）。写前 GET /scope 核对与写之间理论上存在 TOCTOU 竞窗；硬保证来自后端 `for_update` 行锁 + 终态 409（backend 测试在库），客户端保证「可见漂移必冲突、409 必冲突面、绝不静默覆盖」。真正的 expected_version 乐观锁需 contract-owner 卡增量，本卡已把冲突收敛到 `MemoryScopeConflictError`/`isScopeConflict` 单点，契约到位后零散改动能收口。

2. **F03 呈现事件无 memory 修正生产方**。backend `project_feedback_receipt` 存在但无 memory provenance 变更调用方（grep 零命中），故用户「忘记/纠正」没有 committed ExperienceEvent——本卡遵守 F03 反向面：memory 操作成功只有中性文案确认（永不成功徽章/成功声触，PixelSuccessBadge findsNothing 三处钉死）。待 backend 为 memory mutation 接 experience 事件后，本面板消费面天然经 F03 适配器路由（memory→presentHighlight），无需改本卡结构。

3. **「这次」scope 为显示语义而非可写档位**。用户语言四档（所有场景/仅这个目标/相关话题/仅这次对话）中 session 档来自 derive_scope 投影（working_memory 天然会话域），用户记忆条目无「限定到本次对话」的写动作（后端 scope action 封闭集 pause/resume/link_plan/link_task）。因此「这次」在本卡承载为：回执面板（最近一次实际用到的理解）+ session scope 标签；无第二写契约。

4. **回执候选无内容字段**。`context_selection_receipt.v1` 候选只有 ref/status/reason_code（note 为 debug-only，本卡模型层结构性无此字段）。故「这次用了什么」只显示类型+来源核对态+操作，条目正文仍以四组视图为准（同屏互补）。rejected 候选永远只显示归因标签——这是契约形状使然（不编内容），不是呈现偷工。

5. **回执可用性受 I06 开关调制**。`CONTEXT_SELECTION_RECEIPT_MODE` 默认 shadow：读面返回 receipt=null（modeGated 诚实态「记录中，展示尚未开启」）。本卡不改开关档位（运维面）；live 档下才有真实数据。集成验收若需看到数据面，须先将开关置 live。

6. **证据截图为 Ahem 方块字形**（widget 测试环境无 CJK 字体，F04 证据同先例）；真实文案与操作面以同族 `*_semantics.txt`（元素树口径 dump，坐标即真实 rect）与语义断言测试为准。已预登记审查挑战 CH-6。

7. **键盘可达性为 widget 测试实证口径**（Focus 可达 + Space 激活=点按 + 语义名），未做真机外接键盘/读屏（TalkBack/VoiceOver）实测——无真机触达，与全舰队一致。

8. **附带一处 F03 测试文件格式修复**（expect 加尾逗号，CH-3 互钉 sha256 字面量零变更）：本卡锁外文件，仅为满足「analyze 全绿」交付门槛；分析器在主检出未报该项（缓存态差异），如实登记供审查复核。

9. **认知（cognitive）模块零改动**：卡面覆盖模块含 cognitive，但「我的理解」真实路径收敛在 memory+user 两域（cognitive 侧 pattern/capsule 面无黑话清理点、无回执消费点）；按「最小增量」纪律未触碰，如实登记。
