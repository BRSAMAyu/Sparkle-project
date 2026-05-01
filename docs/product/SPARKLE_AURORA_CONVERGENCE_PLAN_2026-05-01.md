# Aurora 完全体体感收敛 — 并行实施方案

> **日期**: 2026-05-01
> **版本**: v1.0
> **目标分支**: roadmapv3
> **执行方式**: 10-20 个 code agent 同时开工，每个 agent 领取一个任务号
> **成功定义**: 用户在日常对话、目标推进、卡点、复盘、回归、社群互动中持续感到 Aurora 真的理解我、记得我、会校准自己、会温和推进下一步

---

## 方案总览

本方案将用户方案中的 6 大 Key Changes 拆分为 **18 个并行任务**，分为三波执行：

| 波段 | 任务数 | 聚焦领域 | 依赖 |
|------|--------|---------|------|
| **Wave A** (Day 1-2) | 6 任务 | 全量开启 + 基础设施一致性 | 无依赖，全部并行 |
| **Wave B** (Day 2-4) | 8 任务 | 体验打磨：对话入口、记忆、时间/社群/工具感知、checkpoint | 部分依赖 Wave A |
| **Wave C** (Day 4-5) | 4 任务 | 体验质量标准：朋友感、receipt、统一语言、golden测试 | 依赖 Wave A+B |

每个任务都标注了：
- **并行约束**：哪些任务必须在本任务前完成
- **产出物**：预期这个 agent 交付什么
- **验收标准**：具体可验证的完成条件
- **禁止事项**：明确不能碰的边界

---

## 全局约束（所有 Agent 必须遵守）

### 不改的范围
- PII redaction、LLM safety、kill switch 基础设施 — 只开不关，不修改逻辑
- Proto 定义 — 不新增字段，只在已有字段上调整使用方式
- 数据库 schema — 不新增 migration
- 预算/冷却/rate limit 护栏参数 — 不降低安全阈值
- 用户 opt-out 路径 — 必须保留并确保功能正常

### 代码质量要求
- 每处文案变更必须同时更新中英文 `.arb` 文件
- 每处 UI 变更必须检查暗色模式兼容性（使用 DS token 而非硬编码颜色）
- 每处交互元素必须添加 `Semantics` 标签
- 每处 Aurora 介入必须有可追溯的 `receipt` 数据结构

### 测试要求
- 后端: 核心链路必须补充至少 1 个 pytest（路径: `backend/tests/`）
- Flutter: 交互元素必须补充至少 1 个 widget test（路径: `mobile/test/`）
- 如果修改了已有逻辑，必须先确保已有测试继续通过

---

## Wave A：全量开启 + 基础设施一致性（6 个并行任务）

### 任务 A1：统一配置默认值 —— 全量开启 Aurora & 双核 & 配套基础设施

**并行约束**: 无依赖，可立即开始

**愿景目标**:
让 Sparkle 从"部分模块跑在 shadow/off"变成"所有已实现链路默认 live"。用户不管从哪个入口（.env、compose、settings 默认值）进入，体验到的 Aurora 能力完全一致，不再因为配置入口不同而跑出不同行为。

**当前状态**:
- `.env.example` 中大量 Aurora mode 为 `off`/`shadow`（如 SRL、traits、metacog、foresight、working memory 等）
- `docker-compose.yml` 覆盖了部分为 `live`，造成两个入口默认值不一致
- `settings.py` 中的 defaults 与 `.env.example` 不完全匹配
- `ENABLE_AURORA_RUNTIME_V1` 在 settings.py 的默认值需确认

**需要达到的效果**:

1. `.env.example` 中所有已实现的 Aurora/双核/SPARKLE 配套开关默认值统一为 `live`
   - 唯一允许非 `live` 的例外：明确标记为 deprecated 的项、安全/隐私类开关、用户 opt-out 开关
   - 每个 `off`/`shadow` 项必须附注释说明为什么不是 `live`

2. `settings.py` 中所有 Aurora/双核相关字段的 defaults 与 `.env.example` 一致

3. `docker-compose.yml` 和 `docker-compose.prod.yml` 移除对 `.env.example` 值的覆盖，改为引用环境变量或与 `.env.example` 一致

4. 新增一个配置一致性测试 `backend/tests/unit/test_aurora_config_consistency.py`，验证:
   - `settings.py` defaults == `.env.example` 值（除白名单例外）
   - compose 文件中的 Aurora 环境变量 key 全部存在于 settings.py
   - 没有拼写错误的 Aurora 模式 key 出现在任何配置文件中

5. `enable_aurora_runtime_v1` 默认 `true`

**具体文件**:
- `.env.example`（根目录和 backend/ 目录）
- `backend/app/config/settings.py`（AuroraFlags 段和相关 default 值）
- `docker-compose.yml`（Aurora 环境变量段）
- `docker-compose.prod.yml`（Aurora 环境变量段）
- 新增: `backend/tests/unit/test_aurora_config_consistency.py`

**验收标准**:
- [ ] 运行 `python scripts/check_aurora_config_consistency.py` 或等效检查，所有 Aurora key 在三处（settings defaults、.env.example、compose）一致
- [ ] 白名单例外的 `off`/`shadow` 项有注释说明
- [ ] 新增的配置一致性测试通过
- [ ] 已有测试全部继续通过

**禁止事项**:
- 不修改 kill switch 逻辑本身
- 不修改安全相关开关的默认值（PII redaction、LLM safety 等必须保持 live）
- 不删除任何配置 key

---

### 任务 A2：打通 Aurora Core Session 的完整入口体验

**并行约束**: 可在 A1 完成后开始，或与 A1 并行（因为只改 UI 和后端响应格式，不依赖配置变更）

**愿景目标**:
用户从任何场景触发 Aurora Core Session 时，感受到的不是一个"弹窗功能"，而是一个统一的、温暖的、有自知之明的深度对话入口。Core Session 开场必须让用户瞬间明白三件事：Aurora 观察到了什么、为什么现在值得校准、这次只会占用多短时间。

**当前状态**:
- 后端: `backend/app/signals/aurora_core_session.py` 定义了 AuroraCaseFile、SessionClosure、StatePatch
- 后端: `backend/app/aurora/core_session.py` 定义了完整的 8-stage lifecycle (declare→exit)
- Flutter: `status_awareness_bar.dart` 有 6-state 模型，支持展开和 Core Session 唤醒
- Flutter: `aurora_core_session_sheet.dart` 已有基础 UI
- 但：触发入口分散（状态带、聊天纠错、checkpoint 等各用各的入口，体验不一致）

**需要达到的效果**:

1. **统一入口触发协议** — 无论从哪个场景触发（状态带点击、聊天纠错 chip、checkpoint 深入按钮、任务卡点提示），都调用同一个 `AuroraCoreSessionEntry`，传递标准化的 `entry_reason`（包含 `trigger_source`、`observed_signals`、`suggested_agenda_preview`）

2. **开场三要素** — Session 开场消息必须包含：
   - **观察**: "我注意到你最近[X 个具体观察，用自然语言而非内部 token]"
   - **为什么现在**: "现在聊这个是因为[时间/状态/进度的具体原因]"
   - **时间承诺**: "这大概需要[X]分钟，你也可以随时暂停或跳过"
   - 这三个要素从 `AuroraCaseFile` 的数据字段渲染，不是模板填空

3. **多消息交互支持** — Session 支持：
   - 用户自由文本输入（不只是选 chip）
   - 暂停 → 恢复（通过 `resume_token`）
   - 用户主动打断并切换话题
   - 退出时生成 `user_visible_summary`（"这次我们聊了什么、改变了什么"）

4. **结束产物可执行** — Session 结束必须产出并展示 `calibration_result`，包含：
   - 具体改变了哪些状态（`state_patches`）
   - 接下来会有哪些可感知的变化（`next_changes`）
   - 用户可点击进入相关行动（"去看看调整后的计划"）

5. **Flutter UI 统一** — 
   - 所有 Core Session 入口使用同一个 `AuroraCoreSessionSheet` widget
   - 支持 3 种尺寸：半屏（默认）、3/4 屏（展开）、全屏（深度模式）
   - 过渡动画：从触发点展开（非突然弹窗），使用 `SparkleStaggerItem` 做渐进式内容浮现
   - 暗色模式、Semantics、i18n 完整

**具体文件**:
- 后端: `backend/app/signals/aurora_core_session.py` — 扩展 AuroraCaseFile 的 `entry_reason` 结构
- 后端: `backend/app/aurora/core_session.py` — 补充 `resume_token`、`user_visible_summary` 生成逻辑
- 后端: `backend/app/orchestration/ux_envelope.py` — 添加 Core Session entry 的 presentation profile
- Flutter: `mobile/lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart` — 改造为统一入口
- Flutter: `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` — 统一触发协议
- Flutter: `mobile/lib/features/chat/presentation/widgets/contextual_correction_bar.dart` — 统一触发协议

**验收标准**:
- [ ] 从状态带、聊天纠错 chip、checkpoint 卡片、任务卡点四种场景触发 Core Session，入口体验一致
- [ ] Session 开场消息包含"观察/为什么现在/时间承诺"三要素，语言自然不模板化
- [ ] 用户可在 Session 中输入自由文本、暂停、恢复、打断、退出
- [ ] 退出时显示 `user_visible_summary`
- [ ] `calibration_result` 包含 `state_patches` 和 `next_changes`
- [ ] Flutter UI 暗色模式、Semantics、i18n 完整
- [ ] 新增至少 4 个 widget test（四种触发场景各一个）
- [ ] 后端新增至少 2 个 pytest（session resume + freeform correction path）

**禁止事项**:
- 不修改 Core Session 的 6-turn/12-message 配额限制
- 不修改 L3 能量级别的预算和冷却逻辑
- 不删除现有任何触发入口

---

### 任务 A3：记忆自然化 —— 让 Aurora"真的记得我"

**并行约束**: 可与 A1、A2 并行

**愿景目标**:
用户在跨会话对话中感受到 Aurora 不是在"复述记忆条目"，而是在"自然引用与我相关的事"。记忆引用应该像朋友聊天时自然想起之前聊过的事，而不是像搜索引擎在返回结果。

**当前状态**:
- 后端: `memory_service.py` 有 episodic + semantic memory
- 后端: `working_memory.py` 有 short-term memory
- 后端: `prompts.py` 的 `format_user_context()` 已将记忆渲染进 prompt
- 但：渲染方式是以 bullet list 形式列出，缺乏"关系上下文"；模型没有收到何时引用、何时不引用的指令

**需要达到的效果**:

1. **记忆 prompt 结构升级** — 从 bullet list 升级为结构化记忆上下文：
   - 每条记忆包含: `content`、`time_ago`（"3天前"、"上周"）、`source`（"你告诉我的"、"从任务完成情况推断的"）、`confidence`、`user_confirmed`（用户显式确认过 / 系统推断）
   - 按相关度排序，最多取 top-5 条（不是所有记忆都塞进去）

2. **引用指令** — 在 system prompt 中给模型明确的记忆引用指令：
   - 只在能推进当前目标或安抚当前状态时引用旧记忆
   - 引用方式是"自然提及"而非"我记得你说过..."
   - 不确定的记忆用试探语气（"我印象中你之前..."）
   - 用户否认后停止引用该记忆

3. **记忆引用 outcome 记录** — 每轮对话中如果引用了记忆：
   - 记录 `memory_reference_outcome`: `accepted`、`corrected`、`ignored`、`denied`
   - 写入 `memory_reference_receipt` 到聊天 metadata
   - Bayesian/self-model 用 outcome 调整后续引用频率

4. **记忆确认闭环** — 如果系统不确定某条记忆（confidence < 0.7），在 Core Session 或状态带中以轻量 chip 形式确认："你之前提到[记忆内容]，对吗？"
   - 用户可以一键确认/否认
   - 确认后的记忆 `user_confirmed = true`，置信度提升，后续引用更确定

5. **Flutter 记忆回执** — 在聊天消息旁显示 `MemoryReferenceReceipt`：
   - 一个小而安静的标记（如"引用了 2 条相关记忆"）
   - 点击可查看引用了什么、为什么引用
   - 用户可以纠正（"这个不对"）

**具体文件**:
- 后端: `backend/app/services/memory_service.py` — 补充 outcome 记录方法
- 后端: `backend/app/orchestration/prompts.py` — 升级记忆 prompt 组装逻辑，添加引用指令
- 后端: `backend/app/orchestration/orchestrator.py` — 在消息处理中记录 memory reference outcome
- Flutter: `mobile/lib/features/chat/presentation/widgets/chat_bubble.dart` — 添加 MemoryReferenceReceipt 展示
- Flutter: 新增 `mobile/lib/features/chat/presentation/widgets/memory_reference_receipt.dart`

**验收标准**:
- [ ] 记忆 prompt 包含 time_ago、source、confidence、user_confirmed 字段
- [ ] 用户说"明天考高数"后新会话中 Aurora 能自然引用，不被拒绝时停止
- [ ] 用户否认某条记忆后，该记忆在后续引用中频率下降
- [ ] MemoryReferenceReceipt 在聊天中安静展示，不喧宾夺主
- [ ] 用户可纠正记忆引用（"不对"按钮）
- [ ] 后端新增至少 3 个 pytest（引用/否认/纠正路径各一个）
- [ ] Flutter 新增至少 2 个 widget test

**禁止事项**:
- 不修改记忆存储的底层 schema
- 不修改 Rule K 写入纪律
- 不增加超过 5 条 top 记忆到 prompt（控制 token 预算）

---

### 任务 A4：时间上下文感知升级 —— Calendar/Timeline 进入 Aurora 决策和 planning

**并行约束**: 可与 A1-A3 并行

**愿景目标**:
Aurora 不只是"知道今天是几号"，而是真正理解用户的时间压力、日程节奏和可用时段，然后在计划调整、任务压缩、每日开场中自然地体现这种理解。用户不需要重复告诉 Aurora"我这周很忙"。

**当前状态**:
- 后端: Calendar context 已有采集路径，能进入聊天 prompt
- 但：calendar 信号没有进入 planning、adaptive_replanner、任务压缩和每日开场
- Flutter: calendar 模块有 provider 和 repository 但无独立屏幕

**需要达到的效果**:

1. **Calendar context 进入 planning** — 当 planner 生成/调整计划时：
   - 读取用户未来 7 天的可用时段（busy/free）
   - 自动避开 busy 时段安排长任务
   - 如果未来 3 天都很忙，自动降低计划强度并附 receipt 说明

2. **Calendar context 进入 adaptive_replanner** — 当 adaptive_replanner 评估"是否需要调整计划"时：
   - 对比计划中的任务时长 vs 用户实际可用时段
   - 如果计划要求每天 3 小时但用户只有 1.5 小时，触发轻量级重规划而非直接标记"执行力差"

3. **Calendar context 进入每日开场** — 每日首次打开聊天时：
   - Aurora 知道今天是什么日子（工作日/周末/考试前 N 天）
   - 根据日程密度调整开场语气（忙日 = 简洁直接，闲日 = 可以多聊）
   - 如果有考试临近，自然提及倒计时

4. **Calendar conflict 触发 Aurora 介入** — 当 calendar event 和 plan deadline 冲突：
   - 生成轻量的 "time_conflict" 信号
   - 在状态带中显示"时间可能不够"，点击可进入快速调整

5. **Flutter 时间感知 UI** — 
   - 状态带增加时间维度显示（"距考试还有 3 天"）
   - 聊天开场增加时间感知问候（非模板化）

**具体文件**:
- 后端: `backend/app/orchestration/planning_workflow.py` — 注入 calendar context
- 后端: `backend/app/orchestration/adaptive_replanner.py` — 读取 calendar 可用时段
- 后端: `backend/app/orchestration/orchestrator.py` — 每日开场注入 calendar context
- 后端: `backend/app/services/calendar_service.py` — 补充 busy/free 查询接口
- Flutter: `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` — 增加时间维度
- Flutter: `mobile/lib/features/home/presentation/screens/dashboard_screen.dart` — 每日开场感知

**验收标准**:
- [ ] planner 生成的计划避开了用户 calendar 中标记为 busy 的时段
- [ ] adaptive_replanner 考虑可用时段而非仅看任务完成率
- [ ] 每日开场根据时间语境变化（考试倒计时/周末/忙碌日）
- [ ] calendar conflict 在状态带中可见
- [ ] 后端新增至少 3 个 pytest
- [ ] Flutter 新增至少 1 个 widget test

**禁止事项**:
- 不创建新的 calendar 数据源，使用已有采集路径
- 不修改 calendar event 的存储 schema
- 不在 UI 中展示用户的具体日历事件（隐私边界）

---

### 任务 A5：社交/Accountability 信号进入 Aurora 教练语气

**并行约束**: 可与 A1-A4 并行

**愿景目标**:
Aurora 了解用户的社群关系（学习伙伴、责任伙伴），并在适当的时机以适当的方式提及——不是监控汇报，而是像一个了解你社交圈的朋友那样，知道你的伙伴在做什么、你们的共同目标是什么。语气调整基于社群信号，但不泄露不该展示的隐私。

**当前状态**:
- 后端: `social_signal_bridge.py` 已把社交信号接入 Router（只读）
- 后端: `community_signal_bridge.py` 已把群组信号桥接到个人上下文
- 后端: Accountability 模块已有 check-in 机制
- 但：社群信号对 Aurora 语气和建议的影响不够明显

**需要达到的效果**:

1. **伙伴活跃感知** — 当用户的责任伙伴刚完成 check-in、分享了进展或有活跃行为：
   - Aurora 在合适时机自然提及（"你的学习伙伴刚完成了今天的 TCP 任务"）
   - 语气是"分享信息"而非"施压比较"
   - 用户可以关闭此功能

2. **Accountability 信号影响语气** — 当用户有活跃的 accountability contract：
   - Aurora 在任务卡点时的语气加入"这不是你一个人的目标"
   - 提醒方式更温和（"你和[X]约好了这周完成第三章"而非"你又拖延了"）

3. **社群聚合信号去噪** — 不是每个社群事件都触发 Aurora 介入：
   - 只对高相关性事件触发（责任伙伴行为、shared goal 进展、@提及）
   - 不触发：群内一般聊天、不相关用户的动态

4. **隐私边界保护** — 
   - Aurora 不主动透露用户自己的行为给其他用户
   - 提及伙伴时只用"你的学习伙伴"而非实名（除非用户显式设置）
   - 所有社群信号引用都有 `social_context_receipt`

5. **Flutter 社交回执** — 当 Aurora 的回复参考了社群信号：
   - 显示 `SocialContextReceipt`（"参考了学习伙伴的动态"）
   - 用户可以拒绝（"不需要参考他的进度"）

**具体文件**:
- 后端: `backend/app/services/social_signal_bridge.py` — 增加信号过滤和相关性排序
- 后端: `backend/app/services/community_signal_bridge.py` — 增加隐私边界检查
- 后端: `backend/app/orchestration/orchestrator.py` — 在 response 生成中注入社交上下文
- 后端: `backend/app/orchestration/ux_envelope.py` — 添加 social context 的 presentation 配置
- Flutter: `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart` — 增加社交回执

**验收标准**:
- [ ] 责任伙伴活跃时 Aurora 的回复语气有可感知的变化（更温和、更有共同体感）
- [ ] 只对高相关性社群事件触发提及，不刷屏
- [ ] 用户可关闭"使用社交信号"
- [ ] SocialContextReceipt 可展示、可点击查看详情、可拒绝
- [ ] 后端新增至少 2 个 pytest
- [ ] Flutter 新增至少 1 个 widget test

**禁止事项**:
- 不在聊天中暴露其他用户的个人数据
- 不新增社群数据采集路径
- 不修改 accountability contract 的数据模型

---

### 任务 A6：工具与资料上下文感知 —— 让 Aurora 知道用户刚刚做了什么

**并行约束**: 可与 A1-A5 并行

**愿景目标**:
用户在 Sparkle 内使用呼吸工具、计算器、词汇查询、翻译、资料上传等工具后，Aurora 能感知这些行为并自然纳入上下文。用户不需要重复告诉 Aurora"我刚刚算过了"或"我查了这个词"。Aurora 的上下文感知让对话更连贯、更省事。

**当前状态**:
- 后端: 工具使用历史已有 API 和 collector（`behavior_signal_collector.py`）
- 后端: Document context injection 已有基础设施
- 但：前端调用点不完整，工具完成后不通知 Aurora；资料注入后无 receipt

**需要达到的效果**:

1. **工具事件写回** — 每次用户使用核心工具（breathing、calculator、translator、vocabulary_lookup、notes、flash_capsule）：
   - 完成后发送轻量 `tool_usage_event` 到 EventBus
   - Aurora nearline collector 消费此事件，记录到 working memory
   - 下一次聊天时 Aurora 可以自然提及（"你刚才算了概率分布，现在做这题应该更容易"）

2. **资料上下文感知** — 当用户上传/打开/使用了文档资料：
   - Document context injection 默认 live
   - 通过 Source Tray/receipt 显示"用了什么资料、没用什么资料、为什么不用"
   - 避免"资料污染"——不是所有上传的资料都自动注入，只注入与当前任务相关的

3. **Flutter 工具完成回执** — 工具完成后显示轻量提示：
   - "已让 Aurora 知道这次[呼吸/计算/查询]"
   - 非侵入式，2 秒后自动消失
   - 用户可点击"不让 Aurora 知道"撤销

4. **Source Tray 可视化** — 在聊天消息旁显示：
   - 当前消息使用了哪些资料/工具结果作为上下文
   - 一个小图标 + 名称
   - 点击可展开查看详情

**具体文件**:
- 后端: `backend/app/services/behavior_signal_collector.py` — 补充工具事件采集
- 后端: `backend/app/core/event_bus.py` — 确保 tool_usage_event 有消费者
- 后端: `backend/app/orchestration/prompts.py` — 在 context 组装中包含工具使用历史
- Flutter: `mobile/lib/features/tools/` 各工具的完成回调中添加 context_effect 写入
- Flutter: `mobile/lib/features/chat/presentation/widgets/source_tray.dart` — 或扩展 context_receipt_bar

**验收标准**:
- [ ] 使用 breathing/calculator/translator 后，下一次聊天 Aurora 能感知
- [ ] Document context 注入后显示 Source Tray
- [ ] 用户可看到"Aurora 用了什么资料"
- [ ] 工具完成的 context_effect 提示非侵入式、可撤销
- [ ] 后端新增至少 2 个 pytest
- [ ] Flutter 新增至少 2 个 widget test

**禁止事项**:
- 不在工具使用期间打断用户
- 不自动注入与当前任务无关的资料
- 不修改工具本身的业务逻辑

---

## Wave B：体验打磨（8 个并行任务）

### 任务 B1：Checkpoint 去脚本化 —— 个性化长期陪跑体验

**并行约束**: 依赖 A3（记忆自然化）和 A4（时间感知）完成后开始

**愿景目标**:
Checkpoint（每日开场、回归、复盘）不再像固定模板的"三轮对话脚本"。Aurora 根据 checkpoint state 生成个性化 debrief：先承认真实进展、再问最小必要问题、最后给出下一步改动。第 4 周和第 12 周的用户感受到的是不同的对话，不是一个模板。

**当前状态**:
- 后端: checkpoint 机制存在，但开场和问题生成有模板化倾向
- 需要: 读取 previous_runtime_state、open_threads、上次未闭合的问题

**需要达到的效果**:

1. **Checkpoint 个性化开场** — 根据 `previous_runtime_state_summary` 生成开场：
   - 包含上次会话的关键主题（"上次我们聊到 TCP 拥塞控制，你当时觉得..."）
   - 包含上次未闭合的问题（"你提到想试一下 worked example，后来试了吗？"）
   - 包含真实进展（"这周你完成了 5/7 天的任务，TCP 那章的正确率从 50% 提到 70%"）

2. **去除三轮脚本感** — 
   - 不再硬编码"第一轮问进展、第二轮问困难、第三轮给建议"的模式
   - 改为 Aurora 根据 checkpoint state 动态决定问什么、问几个问题
   - 最少问 1 个问题，最多问 3 个，每个问题必须有明确的"为什么要问这个"的解释

3. **叙事去重** — 长期用户的多周推送/复盘使用叙事去重：
   - 检测本周内容与之前推送的相似度
   - 如果相似度 > 0.7，换一种表达方式或聚焦点
   - 避免"这周你也很努力"连续出现 8 周

4. **Follow-up wake 消息渲染** — 
   - Checkpoint 产出的 `follow_up_render_action` 进入 mobile 可渲染路径
   - 能显示为 Aurora 延续上次会话的自然提醒
   - 不套用推送通知模板，而是像"继续上次聊的..."的自然延续

**具体文件**:
- 后端: `backend/app/orchestration/orchestrator.py` — checkpoint 开场个性化
- 后端: `backend/app/services/checkpoint_service.py` — 如果存在；否则在 orchestrator 中实现
- 后端: `backend/app/orchestration/prompts.py` — checkpoint prompt 模板去脚本化
- Flutter: `mobile/lib/features/home/presentation/screens/dashboard_screen.dart` — follow-up 渲染
- Flutter: `mobile/lib/features/chat/presentation/widgets/checkpoint_card.dart` — 如果存在

**验收标准**:
- [ ] 连续 checkpoint 不会出现相同开场文案（验证方法: 跑 5 次 checkpoint，检查文本相似度）
- [ ] Checkpoint 开场包含上次未闭合问题的引用
- [ ] 问题数量动态（1-3 个），不固定 3 个
- [ ] Follow-up wake 消息可渲染为自然对话延续
- [ ] 长期用户（模拟 12 周）的推送不会出现模板重复
- [ ] 后端新增至少 3 个 pytest（个性化开场、问题动态数量、叙事去重）
- [ ] 新增至少 2 个 golden/文本快照测试

**禁止事项**:
- 不删除 checkpoint 的硬时间触发机制
- 不修改 checkpoint 的存储方式

---

### 任务 B2：聊天纠错芯片体验升级 —— 从内部 token 到自然语言

**并行约束**: 可与 B1 并行

**愿景目标**:
用户在使用聊天纠错 chip 时，看到的是自然、有温度、有解释的语言，而不是内部的语义 token（如 `risk_false_positive`、`strategy_adjust_needed`）。每个纠错选项都让用户理解"Aurora 为什么觉得可能需要纠正"和"纠正后会有什么变化"。

**当前状态**:
- Flutter: `contextual_correction_bar.dart` 已有纠错 chip UI
- 已知问题: correction chip 使用了 `semanticValue`（内部 machine token）而非自然语言标签
- Codex R14 已标记此问题

**需要达到的效果**:

1. **纠错 chip 自然语言化** — 每个 chip 显示：
   - 自然语言标签（如"我其实不焦虑，只是忙"而非 `risk_false_positive`）
   - 简短的解释 subtitle（12 字以内，如"这次判断不太准"）
   - 可选的 icon 表示纠正类型（信息纠正 / 状态纠正 / 计划纠正）

2. **纠错反馈闭环可视化** — 用户点击纠错 chip 后：
   - 即时显示"已收到，Aurora 正在更新理解"
   - 下一轮对话中 Aurora 明显改判（如上一轮错误判断用户焦虑，这一轮不再用安抚语气）
   - 在状态带中显示"上次纠正已生效"

3. **自由文本纠正增强** — 
   - 除了预设 chip，用户可输入自由文本解释
   - 自由文本纠正入口更可见（输入框旁有小按钮"Aurora 理解错了？"）
   - 提交后不走一般聊天流程，直接进入 User Correction 独立通道

4. **纠正历史可追溯** — 用户可查看"我纠正过 Aurora 什么"：
   - 在设置/画像页面显示最近 N 条纠正
   - 用户可撤销纠正（"之前说错了，恢复原来的判断"）

**具体文件**:
- Flutter: `mobile/lib/features/chat/presentation/widgets/contextual_correction_bar.dart` — 核心改造
- 后端: `backend/app/orchestration/orchestrator.py` — 确保 CorrectionFeedback 消费并改判
- 后端: `backend/app/services/correction_feedback_processor.py` — 如果存在

**验收标准**:
- [ ] 所有纠错 chip 使用自然语言标签 + subtitle，无内部 token 暴露
- [ ] 纠错后下一轮对话 Aurora 明显改判（可自动化测试验证）
- [ ] 自由文本纠正入口可见可用
- [ ] 纠正历史可查看、可撤销
- [ ] Flutter 新增至少 3 个 widget test（chip 点击、自由文本纠正、纠正历史）
- [ ] 后端新增至少 1 个 pytest（纠正→改判验证）

**禁止事项**:
- 不修改 User Correction 独立通道的写入纪律（Rule K）
- 不改变纠错数据的存储格式

---

### 任务 B3：状态带三层扩展完整体验

**并行约束**: 依赖 A2（Core Session 入口）完成

**愿景目标**:
状态带（StatusAwarenessBar）是用户在聊天中最常看到的 Aurora 存在信号。它从简单的"一句话状态"变成三层渐进式信息：第一层一句话（all users）、第二层可纠正判断（interested users）、第三层深度展开（engaged users）。每一层都让用户觉得有用、可信、不打扰。

**当前状态**:
- Flutter: `status_awareness_bar.dart` 已定义三层结构（collapsed/light/deep）
- 后端: status band 6-state 模型已就绪
- 但：三层内容不够丰富，可纠正判断只展示了状态未展示证据，深度展开不够"深"

**需要达到的效果**:

1. **Layer 1 — 一句话状态（collapsed）**
   - 7 字以内，自然语言
   - 如: "感觉你有点卡住了"、"今天节奏不错"
   - 不用内部术语（不用"risk_detected"，用"可能需要调整"）
   - 右侧有一个小箭头暗示可以展开

2. **Layer 2 — 可纠正判断（light expansion）**
   - 包含: 状态判断 + 简短证据 + 纠正入口
   - 如: "我觉得你可能有点压力（最近 3 天任务都超时了）。是因为[时间不够 / 内容太难 / 最近状态不好 / 都不是]"
   - 用户点击任一原因即完成纠正
   - 有一个"进入深度对话"按钮

3. **Layer 3 — 深度展开（deep expansion）**
   - 四张卡片: 
     - 当前状态（详细证据链）
     - 记忆引用（最近的相关记忆）
     - 下一步建议（可执行的最小行动）
     - Aurora 自评（对当前判断的自信度 + "为什么这么判断"）
   - 每张卡片独立可折叠
   - 有"唤醒 Aurora 深度对话"的 CTA

4. **6-state 之间的过渡动画** — 状态切换不是瞬时跳变：
   - 使用渐变色过渡（如绿色→黄色→红色）
   - 状态文字 fade in/out
   - 过渡时长约 300ms

**具体文件**:
- Flutter: `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` — 三层内容扩展
- Flutter: 新增 `mobile/lib/features/chat/presentation/widgets/aurora_status_layer_card.dart` — 深度展开卡片
- 后端: `backend/app/orchestration/ux_envelope.py` — 确保 status band 数据包含证据链和自评

**验收标准**:
- [ ] Layer 1 文案 7 字以内、自然语言、不用内部术语
- [ ] Layer 2 包含证据和纠正入口
- [ ] Layer 3 四张卡片内容完整、可独立折叠
- [ ] 6-state 过渡有动画
- [ ] 暗色模式、Semantics、i18n 完整
- [ ] Flutter 新增至少 4 个 widget test（三层各自渲染 + 状态切换动画）

**禁止事项**:
- 不修改 6-state 模型本身
- 不修改状态带的触发/刷新频率

---

### 任务 B4：消息 Receipt 体系 —— 让用户知道 Aurora 为什么改变了什么

**并行约束**: 依赖 A3（记忆）、A5（社交）、A6（工具资料）的 receipt 数据结构

**愿景目标**:
每一次 Aurora 介入改变了下游行为（任务、语气、资料、提醒、计划），用户都能看到一个安静但清晰的 receipt。Receipt 不是干扰，而是信任的基础——让用户知道"系统为什么这么做"和"我如何纠正"。

**当前状态**:
- Flutter: `context_receipt_bar.dart` 已有基础 receipt UI
- 后端: 部分元数据已经在聊天 metadata 中返回
- 但：receipt 种类不完整、展示不一致、部分场景缺失

**需要达到的效果**:

1. **统一 4 类 Receipt**:
   - `aurora_experience_receipt`: Aurora 介入决策（为什么进入/退出 Core Session、为什么改变状态）
   - `memory_reference_receipt`: 记忆引用（引用了哪些记忆、为什么引用）
   - `source_context_receipt`: 资料/工具上下文（用了什么资料、为什么用）
   - `next_action_changed_by_aurora`: 行动变更（计划/任务被 Aurora 调整的原因）
   - 每类 receipt 有统一的视觉语言（小图标 + 一句话 + 可展开详情）

2. **Receipt 展示时机**:
   - 在相关消息旁以 inline chip 形式展示
   - 不抢占主对话流的注意力
   - 用户可直接忽略，不影响对话
   - 点击展开后显示完整解释 + 纠正入口

3. **Receipt 纠正机制**:
   - 每类 receipt 都包含纠正入口
   - 如: "这个记忆引用不对"、"不需要考虑我的社交动态"、"这个调整不合理"
   - 纠正后 Aurora 下一轮明显改判

4. **Receipt 可配置**:
   - 用户可在设置中关闭某类 receipt 的展示
   - 默认全部开启
   - 关闭后 receipt 仍在后台记录，只是不展示

**具体文件**:
- Flutter: `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart` — 改造为统一 receipt 容器
- Flutter: 新增 `mobile/lib/features/chat/presentation/widgets/aurora_receipt_chip.dart` — 单类 receipt chip
- 后端: `backend/app/orchestration/ux_envelope.py` — 统一 receipt 数据结构
- 后端: `backend/app/orchestration/orchestrator.py` — 确保各场景产出 receipt

**验收标准**:
- [ ] 4 类 receipt 在聊天中正确展示，视觉语言一致
- [ ] 每类 receipt 有纠正入口
- [ ] 用户可在设置中关闭某类 receipt
- [ ] 暗色模式、Semantics、i18n 完整
- [ ] Flutter 新增至少 4 个 widget test（4 类 receipt 各一个）
- [ ] 后端新增至少 2 个 pytest

**禁止事项**:
- 不修改 receipt 的底层存储
- 不在首次使用时弹窗引导（receipt 应该自然融入）

---

### 任务 B5：跨会话上下文连续性 —— 打开 App 时"一切都在"

**并行约束**: 依赖 A3（记忆）、A4（时间感知）

**愿景目标**:
用户关闭 App 后重新打开，Sparkle 不只是"从零开始的新对话"。而是像一个持续存在的朋友——还记得上次聊到什么、还有什么没解决、现在可能需要什么。冷启动时不是空白屏幕，而是温暖的回归。

**当前状态**:
- WebSocket 重连有 `session_id` 恢复
- 聊天历史有缓存（Redis + cache invalidation 已修复）
- 但：回归体验没有"温暖感"，缺乏上下文延续

**需要达到的效果**:

1. **回归开场（Comeback Message）** — 用户重新打开 App 后进入聊天：
   - 如果距上次活跃 < 30 分钟，直接显示上次对话位置（不打招呼）
   - 如果距上次活跃 30 分钟 ~ 8 小时，显示轻量回归提示（"继续上次的..." + 上次主题摘要）
   - 如果距上次活跃 > 8 小时，显示个性化回归问候（结合时间、当日安排、未完成任务）
   - 如果距上次活跃 > 3 天，显示 checkpoint 式回归 debrief

2. **未完成事项延续** — 回归时主动提及：
   - 上次未完成的 Core Session（提供 resume 入口）
   - 上次未回复的 Aurora 问题（"你上次说想一下，现在有答案了吗？"）
   - 上次看了一半的资料/任务

3. **聊天位置恢复** — 
   - 用户不需要手动滚动找上次的位置
   - App 自动滚动到上次对话的最后一条未读消息
   - 如果有新消息，以"新消息分隔线"区分之前和之后

4. **Flutter 冷启动动画** — 从 splash 到聊天首屏的过渡：
   - 不是生硬的跳转，而是从 splash 的标志淡出到聊天界面
   - 如果有回归消息，使用微妙的入场动画

**具体文件**:
- Flutter: `mobile/lib/features/chat/presentation/screens/chat_screen.dart` — 回归体验
- Flutter: `mobile/lib/app/app.dart` — 冷启动过渡
- 后端: `backend/app/orchestration/orchestrator.py` — comeback message 生成逻辑
- Flutter: `mobile/lib/features/chat/presentation/widgets/comeback_banner.dart` — 回归横幅

**验收标准**:
- [ ] 不同时间间隔的回归体验有差异（<30min / 30min-8h / >8h / >3d）
- [ ] 未完成 Core Session 提供 resume 入口
- [ ] 聊天位置自动恢复到上次未读
- [ ] 冷启动过渡动画自然流畅
- [ ] Flutter 新增至少 3 个 widget test
- [ ] 后端新增至少 2 个 pytest

**禁止事项**:
- 不修改 splash screen 的认证逻辑
- 不修改 WebSocket 重连的核心机制

---

### 任务 B6：Core Session resume 与跨会话状态保留

**并行约束**: 依赖 A2（Core Session 入口）

**愿景目标**:
用户在一个 Core Session 中如果临时离开（关闭 App、切换到其他页面），再次回来时可以无缝 resume——不是重新开始，而是从上次中断的地方继续。Session 状态在合理时间内保留，过期后给出友好提示。

**当前状态**:
- 后端: `aurora/core_session.py` 有 `IDLE_TTL_SECONDS = 10 * 60`
- 后端: Session 存储在 Redis 中
- 但：resume 的前端路径和体验未完善

**需要达到的效果**:

1. **Session resume** — 用户离开后再回来：
   - 如果在 TTL 内，显示"继续上次的深度对话"按钮
   - 点击后恢复到上次的 stage 和消息历史
   - Aurora 开场说"继续我们刚才聊的..."而非重新自我介绍

2. **Session 过期处理** — 如果 Session 已过期：
   - 不显示错误，而是显示"上次的深度对话已结束"
   - 用户可选择"开始新的深度对话"或"只是聊天"
   - 保留上次 Session 的 `user_visible_summary` 供用户查看

3. **Session 状态在 Flutter 侧的持久化** — 
   - Session 状态不只在 Redis（后端），也在 Flutter 侧通过 provider 管理
   - 用户切换 Tab 再回来，Session 状态不丢失
   - 用户关闭 App 再打开，如果有活跃 Session 提供 resume 入口

4. **Resume token 机制** — 
   - 每次 Session 交互生成 `resume_token`
   - 前端持有 token，用于恢复
   - Token 在 Session 过期后失效

**具体文件**:
- 后端: `backend/app/aurora/core_session.py` — resume token 生成和校验
- 后端: `backend/app/signals/aurora_core_session.py` — 补充 resume 逻辑
- Flutter: `mobile/lib/features/aurora/data/services/aurora_core_session_service.dart` — resume API
- Flutter: `mobile/lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart` — resume UI

**验收标准**:
- [ ] 离开 Session 后 TTL 内可 resume
- [ ] Resume 后消息历史和 stage 完整恢复
- [ ] Session 过期后有友好提示而非错误
- [ ] 切换 Tab 再回来 Session 状态不丢失
- [ ] Flutter 新增至少 2 个 widget test
- [ ] 后端新增至少 2 个 pytest

**禁止事项**:
- 不修改 Session 的配额限制（6 turns / 12 messages）
- 不修改 Redis TTL 的底层逻辑

---

### 任务 B7：多感官反馈与 Aurora 状态的联动

**并行约束**: 可与 B1-B6 并行

**愿景目标**:
Sparkle 的多感官系统（BGM、触觉、动效、庆祝）不只是独立的美学层，而是与 Aurora 状态联动——当 Aurora 检测到用户卡住时音乐变舒缓，当用户突破瓶颈时触发庆祝动效，当进入深度对话时环境音变化。感官层成为 Aurora 存在感的延伸。

**当前状态**:
- Flutter: `bgm_service.dart`、`sensory_feedback_service.dart`、`scene_audio_scope.dart` 均已就绪
- `sparkle_confetti.dart` 和 `sparkle_motion_primitives.dart` 存在
- 但：感官系统与 Aurora 状态之间没有联动逻辑

**需要达到的效果**:

1. **Aurora 状态 → BGM 联动**:
   - `sensing` → ambient 保持当前
   - `calibrated` → 轻快的氛围音
   - `risk_found` → 更舒缓、降低 BGM 音量
   - `needs_confirm` → 淡出 BGM，集中注意力
   - `calibration_available` → 微妙的高亮点缀音
   - `cooling_down` → 安静的环境音

2. **Aurora 事件 → 触觉/动效联动**:
   - Core Session 开启 → 微妙的入场触觉
   - 用户完成纠正 → 轻柔的确认触觉
   - 状态带状态切换 → `SparkleStaggerItem` 动画
   - 成就解锁 → `SparkleConfetti`
   - 每日连续打卡 → 微妙的庆祝音效

3. **场景音频 Scope 扩展** — `SceneAudioScope` 不仅听路由变化，也听 Aurora 状态：
   - 路由切换 + Aurora 状态 = 复合音频策略
   - 例如：进入 Galaxy + risk_found = 保持探索感但降低音乐复杂性

4. **感官预算尊重** — 
   - 遵循已有的感官预算限制（每秒最多 5 个音效、3 次触觉）
   - 不因 Aurora 状态变化而突破预算

**具体文件**:
- Flutter: `mobile/lib/core/services/bgm_service.dart` — Aurora 状态联动
- Flutter: `mobile/lib/core/services/sensory_feedback_service.dart` — Aurora 事件联动
- Flutter: `mobile/lib/core/widgets/scene_audio_scope.dart` — 复合策略
- Flutter: `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` — 触发感官事件

**验收标准**:
- [ ] 6 种 Aurora 状态各有对应的 BGM 策略
- [ ] Core Session 开启/纠正/成就各有触觉/动效联动
- [ ] SceneAudioScope 处理复合策略（路由 + Aurora 状态）
- [ ] 感官预算不被突破
- [ ] 用户可关闭感官联动（设置中）
- [ ] Flutter 新增至少 2 个 widget test

**禁止事项**:
- 不修改 BGM 播放器核心逻辑
- 不修改感官预算限制的数值
- 不自动下载新的音频资源

---

### 任务 B8：任务卡点 Aurora 介入体验

**并行约束**: 依赖 A2（Core Session）、A4（时间感知）

**愿景目标**:
当用户的执行行为出现值得注意的模式时（连续超时、连续放弃、连续跳过），Aurora 不是直接弹出一个"你可能有问题"的通知，而是以温和的、有上下文的方式提供帮助。用户感到的是"有人注意到我了"而不是"系统在监控我"。

**当前状态**:
- 后端: 任务超时/放弃事件已有 EventBus 消费
- 后端: AdaptiveReplanner 有调整逻辑
- 但：Flutter 侧的任务卡点介入 UI 不完整

**需要达到的效果**:

1. **卡点检测后的温和介入** — 不是弹窗，而是在聊天中以 Aurora 消息的形式出现：
   - "我注意到最近[具体卡点描述]。要不要聊一下？大概 2 分钟。"
   - 用户可选择"聊聊"、"稍后"、"不需要"
   - 如果选择"稍后"，Aurora 在下次对话开场时提及

2. **任务卡点 Core Session 轻量版** — 
   - 如果用户选择"聊聊"，进入一个简化版 Core Session（非完整 L3）
   - 只针对当前卡点，3 轮对话内完成
   - 产出：具体的任务调整建议 + 下一张任务卡的修改

3. **卡点可视化** — 在状态带中显示：
   - 任务系统的健康状态（"3 张任务中有 1 张超时了"）
   - 趋势指示（"比上周好" / "需要关注"）

4. **卡点恢复后正向反馈** — 
   - 当卡点解除后（用户恢复正常节奏），Aurora 主动提及
   - "你最近的任务节奏恢复了。之前调整的任务大小看来起作用了。"
   - 不是炫耀 Aurora 自己的"功劳"，而是承认用户的努力

**具体文件**:
- 后端: `backend/app/services/adaptive_replanner.py` — 卡点检测与信号发射
- 后端: `backend/app/orchestration/orchestrator.py` — 卡点介入消息生成
- Flutter: `mobile/lib/features/chat/presentation/widgets/task_stuck_card.dart` — 如果存在则改造
- Flutter: `mobile/lib/features/home/presentation/widgets/exam_sprint_dashboard_card.dart` — 任务健康

**验收标准**:
- [ ] 连续 3 张任务超时/放弃后触发 Aurora 温和介入
- [ ] 卡点介入消息包含"聊聊/稍后/不需要"三个选项
- [ ] 轻量版 Core Session 3 轮内产出具体调整建议
- [ ] 卡点恢复后有正向反馈
- [ ] 状态带显示任务健康度
- [ ] 后端新增至少 2 个 pytest
- [ ] Flutter 新增至少 2 个 widget test

**禁止事项**:
- 不修改任务执行的底层 FSM
- 不修改 AdaptiveReplanner 的核心算法
- 不在用户明确拒绝后继续推送同主题

---

## Wave C：体验质量标准与收尾（4 个并行任务）

### 任务 C1：朋友感语言体系 —— 统一 Aurora 的表达方式

**并行约束**: 依赖 Wave A+B 核心链路完成后开始

**愿景目标**:
Aurora 与用户的交互语言在全场景下有统一的人格：像一个真诚、在乎、但不审判的朋友。每一次温柔表达都绑定一个真实观察、一个可纠正判断、一个低成本下一步。不假装人类，不滥用内部术语，不模板化安慰。

**当前状态**:
- 各处 prompt 中的 tone 指令分散在多个文件中
- 部分文案仍有内部 token 泄露
- 部分场景语气不一致（有的过于客服，有的过于学术）

**需要达到的效果**:

1. **统一的 Aurora 语言原则文件** — 创建 `backend/app/orchestration/aurora_language_principles.py`：
   - 7 条核心语言原则（从愿景文档 §3.3 提取）
   - 每条原则有正面示例和反面示例
   - 作为所有 prompt 组装时的参考源

2. **跨场景语言一致性检查** — 
   - 审计所有 prompt 中的 tone instruction（聊天、checkpoint、Core Session、每日开场、推送）
   - 确保每个指令的用词符合统一语言原则
   - 消除互相矛盾的 tone 指令

3. **禁用表达黑名单** — 
   - 列出禁止使用的表达模式（如"我相信你一定能"、"你真棒"、"又失败了"）
   - 在 prompt 中明确告知模型避免这些表达
   - 黑名单有"为什么不能用"的解释

4. **场景特定语言微调** — 
   - 不同场景允许语气差异（如 Core Session 更直接，每日开场更轻盈）
   - 但核心人格（朋友感）始终保持一致
   - 差异是"程度"差异而非"人格"差异

**具体文件**:
- 新增: `backend/app/orchestration/aurora_language_principles.py`
- `backend/app/orchestration/prompts.py` — 统一 tone instruction
- `backend/app/orchestration/orchestrator.py` — 统一场景内 tone 设置
- `backend/app/orchestration/ux_envelope.py` — tone 配置参数化

**验收标准**:
- [ ] 语言原则文件定义了至少 7 条原则 + 示例
- [ ] 所有 prompt tone instruction 经过一致性审计
- [ ] 禁用表达黑名单已建立并在 prompt 中引用
- [ ] Golden 测试覆盖 5 个场景（聊天、checkpoint、Core Session、每日开场、推送）
- [ ] Golden 测试验证：无禁用表达、无内部 token、无模板化安慰
- [ ] 后端新增至少 5 个 golden/文本快照测试

**禁止事项**:
- 不修改 LLM 调用逻辑
- 不添加新的 prompt 模板（只修改已有模板的 tone instruction）

---

### 任务 C2：统一设计语言 —— 视觉、动效、无障碍收尾

**并行约束**: 可与 C1 并行

**愿景目标**:
Sparkle 的 Flutter 端在全模块、全场景下有一致的视觉语言。暗色模式下所有页面都能正确渲染，所有交互元素都有无障碍标签，设计 token（而非硬编码颜色）被全局使用。用户在不同功能间切换时感受到的是同一个产品，而不是"拼凑的多个功能"。

**当前状态**:
- 87 个文件中 353 处使用硬编码 `Colors.*` 绕过设计系统
- `Semantics` 标签只在 31/1068 个文件中出现
- `bgm_service.dart` 为 3494 行单体文件
- `core/errors/failures.dart` 为空文件（C16 已部分修复）

**需要达到的效果**:

1. **硬编码颜色清理** — 
   - 优先清理 galaxy、chat、community 三个核心模块的硬编码颜色
   - 替换为对应的 `DS.*` token
   - 验证暗色模式下视觉正确

2. **无障碍 Semantics 补充** — 
   - 优先为所有交互元素（按钮、chip、卡片、列表项）添加 `Semantics` 标签
   - 优先模块: chat、home、galaxy、plan、task
   - 标签使用 i18n 化的文案

3. **核心 Widget 代码质量** — 
   - `chat_screen.dart` 拆分巨型 widget 树为可复用子 widget
   - `bgm_service.dart` 不要求拆分（属于后续重构），但确保当前逻辑不影响

4. **暗色模式一致性** — 
   - 所有使用 `DS.*` token 的页面暗色模式自动正确
   - 运行暗色模式 test，确保 0 处渲染异常

**具体文件**:
- galaxy 模块 `*.dart`（最高优先级 — 约 60 处硬编码颜色）
- chat 模块 `*.dart`（约 30 处）
- community 模块 `*.dart`（约 25 处）
- 所有交互式 widget 的 Semantics 补充

**验收标准**:
- [ ] galaxy、chat、community 三个模块 0 处硬编码 `Colors.white/black`
- [ ] 核心交互元素（按钮、chip、卡片）Semantics 覆盖率 ≥ 80%
- [ ] `chat_screen.dart` 拆分为至少 5 个可复用子 widget
- [ ] 暗色模式 test 通过（新增至少 1 个 golden test）
- [ ] Flutter analyze 0 errors
- [ ] Flutter 新增至少 3 个 widget test

**禁止事项**:
- 不修改 `DS.*` token 的定义值
- 不拆分 `bgm_service.dart`（后续专门处理）
- 不修改业务逻辑

---

### 任务 C3：Golden 测试体系 —— 防止 Aurora 体感退化

**并行约束**: 依赖 Wave A+B 完成后开始

**愿景目标**:
建立一套 golden/文本快照测试体系，确保 Aurora 的核心体验不会随着后续开发而退化。每次修改 prompt、tone instruction、或 Aurora 逻辑时，CI 能自动检测文案质量的变化——包括模板化检测、禁用表达检测、内部 token 泄露检测。

**当前状态**:
- 有基础的 pytest 和 widget test，但无 golden 测试
- 验收清单中提到需要 golden 测试但未实施

**需要达到的效果**:

1. **Golden 测试框架** — 
   - 创建 `backend/tests/golden/` 目录
   - 定义至少 10 个场景输入（各场景的代表性输入）
   - 对每个场景生成 Aurora 响应文本
   - 将响应文本存储为 golden snapshot
   - CI 中运行测试，检测 drift

2. **文案质量自动检测** — 
   - 模板化检测: 连续 3 次以上同样场景的文本相似度 < 0.6
   - 禁用表达检测: 出现黑名单中的表达 = 测试失败
   - 内部 token 检测: 出现 `risk_false_positive` 等语义 token = 测试失败
   - 长度检测: 过长或过短的响应产生 warning

3. **覆盖场景**:
   - 每日开场（3 种时间语境）
   - Checkpoint 回归（3 种间隔时间）
   - Core Session 开场（4 种触发场景）
   - 记忆引用（3 种记忆类型）
   - 任务卡点介入（2 种卡点类型）
   - 推送文案（2 种推送类型）
   - 纠正回复（2 种纠正类型）

4. **CI 集成** — golden 测试在 CI 中运行：
   - 首次运行生成 baseline
   - 后续运行对比 baseline
   - drift 超过阈值 = CI 失败
   - 有意修改时提供 `--update-goldens` 更新 baseline

**具体文件**:
- 新增: `backend/tests/golden/` 目录 + 框架
- 新增: `backend/tests/golden/test_aurora_experience_golden.py`
- 新增: 各场景的 input fixture 文件
- CI: `.github/workflows/ci.yml` 中增加 golden test step

**验收标准**:
- [ ] 10 个以上场景有 golden snapshot
- [ ] 文案质量自动检测 3 项全部实现
- [ ] CI 中 golden 测试可运行
- [ ] 至少一个 golden test 验证: 修改 prompt 后 drift 被检测到

**禁止事项**:
- 不修改现有测试框架
- golden 测试不调用真实 LLM（使用 mock/fixture）

---

### 任务 C4：端到端体验走查与收尾

**并行约束**: 在所有 Wave A+B+C 任务完成后执行

**愿景目标**:
在所有模块改造完成后，进行一次完整的端到端体验走查。追踪关键用户旅程，确保没有体验断点、没有死胡同、没有"这个功能怎么没法用"的时刻。产出体验走查报告和修复清单。

**当前状态**:
- E2E acceptance checklist 已定义 30 个场景
- 许多场景标注为 Manual only

**需要达到的效果**:

1. **追踪 7 条核心旅程**:
   - 新用户入职 → 设目标 → 生成计划 → 执行首张任务 → 首次反思
   - 用户卡住 → Aurora 检测 → 温和介入 → Core Session → 调整计划 → 恢复
   - 用户纠正 Aurora → 纠错 chip → Aurora 改判 → 下一轮验证
   - 跨会话记忆 → 输入信息 → 关闭 App → 重新打开 → Aurora 自然引用
   - 社群互动 → 伙伴活跃 → Aurora 感知 → 温和提及
   - 工具使用 → 呼吸/计算 → Aurora 感知 → 下一次聊天引用
   - Checkpoint 回归 → 个性化 debrief → follow-up → 行动

2. **体验断点检测** — 每条旅程检查：
   - 是否有 UI 阻断（无法返回、无法跳过）
   - 是否有文案泄露内部术语
   - 是否有暗色模式渲染问题
   - 是否有 Semantics 缺失
   - 是否有 i18n 缺失（显示为中文在英文模式下）

3. **产出物**:
   - 7 条旅程的体验走查报告（通过/不通过 + 截图 + 问题描述）
   - 修复优先级建议
   - 体验评分（每条旅程 1-5 分）

**具体文件**:
- 新增: `docs/product/SPARKLE_AURORA_CONVERGENCE_WALKTHROUGH_2026-05-05.md`

**验收标准**:
- [ ] 7 条核心旅程全部追踪完毕
- [ ] 每条旅程的体验被评分
- [ ] 发现的体验断点被记录和分类
- [ ] 走查报告交付

**禁止事项**:
- 此任务只做走查和报告，不修改代码
- 发现的代码问题应转为新任务而非在此任务中修复

---

## 任务依赖关系图

```
Wave A (可全部并行):
  A1: 配置统一        ← 无依赖
  A2: Core Session入口 ← 无依赖
  A3: 记忆自然化       ← 无依赖
  A4: 时间感知         ← 无依赖
  A5: 社交感知         ← 无依赖
  A6: 工具资料感知     ← 无依赖

Wave B (部分依赖 Wave A):
  B1: Checkpoint个性化 ← 依赖 A3, A4
  B2: 纠错芯片升级     ← 无依赖（可并行）
  B3: 状态带三层       ← 依赖 A2
  B4: Receipt体系      ← 依赖 A3, A5, A6
  B5: 跨会话连续性     ← 依赖 A3, A4
  B6: Session resume   ← 依赖 A2
  B7: 多感官联动       ← 无依赖（可并行）
  B8: 任务卡点介入     ← 依赖 A2, A4

Wave C (依赖 Wave A+B):
  C1: 朋友感语言体系   ← 依赖 A+B 核心链路
  C2: 设计语言收尾     ← 无依赖（可并行）
  C3: Golden测试体系   ← 依赖 A+B 核心链路
  C4: E2E走查          ← 依赖 A+B+C 全部
```

## 并行执行建议

### 第一批（10 个 Agent 同时开工）
A1, A2, A3, A4, A5, A6, B2, B7, C2（这 9 个任务无依赖或依赖很少）

### 第二批（8 个 Agent 在第一批部分完成后开工）
B1（等 A3+A4）, B3（等 A2）, B4（等 A3+A5+A6）, B5（等 A3+A4）, B6（等 A2）, B8（等 A2+A4）

### 第三批（3 个 Agent 在前两批完成后开工）
C1, C3, C4

---

## 全局成功标准

完成全部 18 个任务后，应达到以下效果：

1. **用户在日常对话中感到 Aurora 理解自己**: 
   - 记忆引用自然、可纠正
   - 状态带准确、可交互
   - 语言一致、朋友感

2. **用户在卡点时得到温和帮助**: 
   - 卡点检测及时但不打扰
   - Core Session 有深度但省时间
   - 介入产物可执行、可追溯

3. **用户在跨会话中感到连续性**: 
   - 回归体验温暖
   - Checkpoint 个性化不模板化
   - 未完成事项不丢失

4. **用户知道 Aurora 为什么这么做**: 
   - Receipt 体系完整
   - 纠正机制可用
   - 所有 Aurora 介入可解释

5. **体验质量可度量**: 
   - Golden 测试防退化
   - 文案质量自动检测
   - 端到端走查覆盖

---

## 附录：关键文件速查表

| 编号 | 文件 | 角色 |
|------|------|------|
| F1 | `backend/app/orchestration/orchestrator.py` | 主 FSM，聊天流控制 |
| F2 | `backend/app/orchestration/dual_core_router.py` | 双核路由决策 |
| F3 | `backend/app/orchestration/prompts.py` | Prompt 组装 |
| F4 | `backend/app/orchestration/ux_envelope.py` | UX 呈现配置 |
| F5 | `backend/app/aurora/core_session.py` | Core Session FSM |
| F6 | `backend/app/signals/aurora_core_session.py` | Core Session 数据结构 |
| F7 | `backend/app/services/memory_service.py` | 长期/短期记忆 |
| F8 | `backend/app/core/event_bus.py` | 事件总线 |
| F9 | `backend/app/config/settings.py` | 所有配置定义 |
| F10 | `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | 聊天主屏 |
| F11 | `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` | 状态带 |
| F12 | `mobile/lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart` | Core Session UI |
| F13 | `mobile/lib/features/chat/presentation/widgets/contextual_correction_bar.dart` | 纠错 chip |
| F14 | `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart` | Receipt 展示 |
| F15 | `mobile/lib/core/design/design_system.dart` | 设计 token |
| F16 | `mobile/lib/core/services/bgm_service.dart` | BGM 服务 |
| F17 | `mobile/lib/core/services/sensory_feedback_service.dart` | 感官反馈 |
| F18 | `mobile/lib/features/home/presentation/screens/dashboard_screen.dart` | 仪表盘/回归 |
