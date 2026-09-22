# A-SPEC-V1_1 · 北极星三面（聊天 / 冲刺仪表盘 / 星图）UX 研究 → 自审 → 辩论 → SPEC v1.1 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡 ｜ 2026-09-22 ｜ worktree wt173（base **5b912dcf**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read），file:line 均为 @5b912dcf 实测；守卫基线数为 `scripts/guards/dl_spec_ratchet_baseline.json`（冻结 @d87d42ea）实测值。
> 前置读透：`v3-output/DL-R3/SPEC.md`（v1.0 定稿全文）+ `REVISION_v1_0.md` + `DL-R4/REVIEW.md` 修订框架。本提案**不推翻 v1.0 任何条款**，全部为增量/澄清条目，形制对齐 v1.0（编号规则 + 依据 + 可验收数字）。
> 对标研究方法声明：对标软件做法基于公开常识 + UX 专业判断（按卡内授权，未做外部浏览）；引用代码均为树内实测。

---

## 0. 方法与多轮过程记录

本卡按使命要求走「研究→自审→辩论→统一规范」四步，实际执行为四轮迭代：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 每面选 2-3 个顶级对标，提炼 IA/节奏/层级/反馈/空态/错误态六维做法 | §1 三张对标表 | 三面对标的最大公约数：**一个主角数字 + 零常驻系统面板 + 单一瞬态等待信号 + 失败保留现场** |
| R2 自审 | 逐面读真实代码（chat_screen 3968 行 / sprint_screen 716 行 / exam_sprint_dashboard_card 1010 行 / galaxy_screen 3968 行 / star_map_painter 2793 行 + 守卫基线） | §2 差距清单 18 条（带 file:line） | chat 是 v1.0 落地最好的面；**冲刺仪表盘是守卫盲区里的最差面**；galaxy 差距全部是 v1.0 已立未落项 |
| R3 辩论 | 逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：18 条 → 采纳 10（含 2 条改写采纳）/ 砍 7 / 转 v1.0 台账 1 | 被砍项的共同特征：北极星加权低或已有 owner 条款，重复立卡制造双 owner |
| R4 成文 | 过关差距 → v1.1 增量条目 + top10 改造清单 | §4 / §5 | v1.1 共 8 条增量（N1-N8），全部为 v1.0 的增补/澄清，无推翻 |

**结构性结论先行**：v1.0 的 9-surface 地图已经落后于产品现实——**冲刺仪表盘（sprint_screen + home 内嵌 exam 卡）是期末一周北极星的主场景，却不在 9 surface 名单里，也不在 UX-COMP 守卫扫描根里**（`scripts/guards/check_ux_component_convention.py:42-52` 扫描根仅 9 面，`features/plan/presentation` 缺席）。这是三面自审中唯一「系统性」级的发现，其余差距皆为点状。

---

## 1. 三面对标研究表（R1）

### 1.1 聊天面 · 对标：ChatGPT / Claude / Character.ai

| 维度 | ChatGPT | Claude | Character.ai | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | 会话流占绝对主体；系统件全部收进设置/抽屉；header 只有模型选择+临时聊天 | 会话流 + Artifacts 侧板（显式呼出，不悬浮遮挡）；header 极简 | 对话流 + 人格状态行（头像+一句话状态），情感存在感靠 header 微件而非面板 | 「会话本体 ≥70%」方向正确；系统件三形态（内联微件/收件箱/阶段胶囊）与三强家做法同构 |
| 节奏 | 用户消息即时回显；等待期为单一瞬态指示；流式逐 token | 等待期为单行微光状态（shimmer 一行，非面板）；完成后即消失 | 秒级回显，人格「正在输入…」制造临场感 | 等待反馈=单源瞬态是品类共识；多源并发动画无先例 |
| 层级 | 消息气泡对比弱、内容最深色；操作钮（复制/重试）收进消息尾部长按/悬停菜单 | 回答正文为绝对主角；引用与免责声明内联小字 | 头像+名字分层，其余全给对话 | 内容最深 + chrome 最低；Sparkle textPrimary 深色原则一致 |
| 反馈 | 失败消息内联「重试」chip，输入框内容永不丢失；停止生成钮常驻等待期 | 「我可能出错」免责内联；改口时明确标注修订 | 打断即停 | 失败保留现场 + 可打断是硬惯例 |
| 空态 | 居中 composer + 建议 chips（≤4，一点填入不直发） | 居中输入框 + 场景化开场建议 | 人格问候 + 开场白 chips | 空态=「一句话入口」，chips 点选填入草稿 |
| 错误态 | 内联重试 + 人话（「出了点问题」），绝不裸异常 | 人话 + 重试，服务过载时明说容量 | —— | 无裸异常是底线 |

### 1.2 冲刺仪表盘 · 对标：Duolingo / Forest / TickTick（+考试倒计时品类惯例）

| 维度 | Duolingo | Forest | TickTick | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | 单主角（今日路径/目标环），社交比较（联赛）收进独立 Tab，不与个人仪表混排 | 单主角（专注计时）；统计历史独立屏 | **Today-first**：今日置顶，未来日期默认折叠，分组按日 | 单主角 + 今日置顶 + 次级入口（社交/历史）收边，是备考场景正确 IA |
| 节奏 | 完成瞬间一次性庆祝（goal ring 单次动画）；连胜火焰常驻但**静态**（非循环动画） | 计时中唯一持续视觉即树生长；完成时单次种植动效 | 完成勾选 ~200ms 单次；无循环装饰 | 一次性庆祝 + 常驻件静态化；常驻循环动画无先例 |
| 层级 | 一个英雄数字（连胜/日目标）；进度只编码课程完成度，奖励（宝石/宝箱）与进度位分离 | 剩余时间即唯一层级 | 进度条中性色，完成态才上语义色 | **进度位不掺奖励编码**（与 v1.0 B-02 两层分离完全同向） |
| 反馈 | 断签有安全网（streak freeze）文案不羞辱；损失预警即时 | 退出专注=树枯死，但给「补种」出口 | 乐观 UI：勾选即时完成 | 安全网+不羞辱与 v1.0 §7.4 T1 同构 |
| 空态 | 无 streak 时「开始今天的课程」单 CTA | 空森林=种第一棵树引导 | 空列表给「添加习惯」CTA | 空态=为何空+单一 CTA |
| 错误态/紧迫感 | —— | —— | —— | 考试倒计时品类惯例：**最终 3 天升级红色**，此前中性/琥珀分级——紧迫感有色阶而非全程红 |

### 1.3 星图 · 对标：Obsidian graph / Duolingo 学习路径 / Stellarium 类星空应用

| 维度 | Obsidian graph | Duolingo 路径 | Stellarium/Sky Guide | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | **local graph 工作视图**（当前笔记+1 跳，深度可调）与全图视图分离；检索/筛选常驻但不遮画布 | 线性路径，当前节点唯一显眼（START 气泡） | 工作观星（搜索/控制半透明暗件）与沉浸漫游（全屏+控制隐入）双模式 | 与 v1.0 D5 双视图裁决完全同构：局部工作 + 全局仪式 |
| 节奏 | 静态为主，交互瞬间才有物理动画 | 点亮节点一次性动画 | 大气闪烁极低频、可关 | 工作视图=静态+交互瞬间动效（v1.0 §2.6 工作视图持续源=0） |
| 层级 | 节点大小=连接数、亮度=活跃；标签按需显示（缩放阈值/悬停），从不全量常驻 | 节点状态用**形状+填充**编码（锁/可学/已完成），非仅颜色 | 控制件与画布同暗色系，不破沉浸 | **标签按需显隐是「噪声汤」的正解**；掌握度编码需形状/亮度冗余，禁色相单通道 |
| 反馈 | 点击节点高亮邻域、淡化其余（spotlight） | 完成+1 即时落点 | 选中西天体高亮十字线 | spotlight 机制正确；galaxy 已有 `_spotlightNodeIds` 基建（galaxy_screen.dart:3120-3126） |
| 空态 | 空库给「创建第一篇笔记」 | —— | 白天模式提示「今晚可见 X」 | 空态指向创建动作 |
| 错误态 | —— | 断网提示重试同步 | —— | 屏级错误=人话+重试 |

**三面共性提炼（作为 v1.1 立条依据）**：
1. **单主角数字 + 单一瞬态等待源 + 零常驻循环动画**是三面顶级软件的最大公约数；
2. **进度位与奖励位物理隔离**（Duolingo 是最强先例）；
3. **紧迫感有色阶**（倒计时分级升级），不是全程红；
4. **预测/估计类数字必带口径**（Claude 免责行、Duolingo 概率的「按你当前进度」小字）；
5. **屏级错误=人话+重试**，无一家裸异常。

---

## 2. 自审差距清单（R2，全部 @5b912dcf 实测）

### 2.1 聊天面（`features/chat/presentation/screens/chat_screen.dart`）

先说到达标项（诚实记录，避免过度自审）：S8 面积重划已落地——常驻系统面板撤出，`chatHeaderPanels` 仅剩事件驱动横幅（chat_screen.dart:1476-1523）；S18 阶段胶囊已落地且含预期时长「通常几秒到十几秒」（arb `chatRunPhaseDurationHint`:10098）+可取消（chat_run_phase_indicator.dart `onCancel` 必填）；三点 `_TypingIndicator` 已退役（chat_screen.dart:1662 注释）；一答建议 chips 每模式 3 条（chat_screen.dart:3223-3245，合 §4.1.4）；收件箱唯一入口在 AppBar（chat_screen.dart:1322，D8-5 注释）。**chat 是三面中 v1.0 执行最好的面，剩余差距 3 条：**

| # | 差距 | 证据（file:line @5b912dcf） | 违反条款 |
|---|---|---|---|
| C-G1 | 等待期**双持续动画源**：`_ReasoningBreathOverlay` 3s repeat(reverse) 呼吸叠加 + 阶段胶囊 700ms repeat 脉冲并存 | chat_screen.dart:3845-3849（`Duration(seconds: 3)` + `repeat(reverse: true)`）；chat_run_phase_indicator.dart:80-82（`repeat()`）；两源同现于 `_shouldShowReasoningAtmosphere` 等待窗口（chat_screen.dart:1435-1440） | §2.6 同屏持续源 ≤1；§2.5 D-1 精神（呼吸删除） |
| C-G2 | 呼吸动画为**手写实现**，绕过 D-1 守卫——D-1 只删了 `createBreathingController` 引用，手写 `AnimationController.repeat(reverse:true)` 不被 `breathingController` 维捕获；且门控只有 reduceMotion，无 PerformanceTier/DecorationMode | chat_screen.dart:3860-3863（仅 `context.reduceMotion` 判断） | §2.5 D-1 的守卫盲区；G-4（门控规格同类） |
| C-G3 | 装饰预算超账：chat 屏同时挂 3 层渐变装饰（背景 LinearGradient + 常驻 RadialGradient 氛围 + 呼吸 RadialGradient），DL-SPEC `gradientLiteral` 基线 chat_screen=6 处 | chat_screen.dart:1421-1432（线性背景）、1441-1457（径向氛围常驻）、3864-3881（呼吸径向）；基线 JSON `chat_screen.dart {gradientLiteral: 6, offLadderDuration: 4}` | §5.3 gradient/屏 ≤2 且非核心流程；特效层/屏=1 |

### 2.2 冲刺仪表盘（`features/plan/presentation/screens/sprint_screen.dart` + `features/home/presentation/widgets/exam_sprint_dashboard_card.dart`）

**面级根发现：双文件都不在 UX-COMP 守卫扫描根**（check_ux_component_convention.py:42-52 无 `features/plan`；home 在根内但 exam 卡不在其 9 面清单语义内）。DL-SPEC（全 features 域）能扫到但只管时长/渐变/冷色维度，组件 owner 维度（rawButton/rawChip/parallelClass）完全失明。

| # | 差距 | 证据（file:line @5b912dcf） | 违反条款 |
|---|---|---|---|
| S-G1 | **守卫盲区 + 裸组件群**：`Card(elevation: 2)`（卡带阴影）、裸 `Chip`、裸 `OutlinedButton.icon`、裸 `TextButton.icon`、裸 `FilledButton`、私有 `_MetricPill`/`_ModePill` 全部逃逸 owner 归一 | sprint_screen.dart:373-374（Card elevation:2）、:268-273（Chip）、:277-293（OutlinedButton）；exam_sprint_dashboard_card.dart:156（TextButton）、:374（FilledButton）、:712-748（_MetricPill）、:964-993（_ModePill） | §4.1.1 唯一 owner；§1.2.1 阴影只允许浮起件 |
| S-G2 | **屏级错误态无重试**：plan 详情加载失败只给图标+一句「加载失败」，无重试钮、无影响说明、不留现场 | sprint_screen.dart:195-205（error 分支仅 Icon+Text，无 action） | §4.5 错误态三句式（人话+重试+保留现场） |
| S-G3 | 骨架**不贴最终布局**：骨架画 3 个 80×80 方块，真实内容是成就行（40×40 圆+文字行）与任务卡列表 | sprint_screen.dart:681-689（3×SparkleSkeleton 80×80）vs :361-415（真实成就区为纵列行布局） | §4.4.1 骨架贴布局 |
| S-G4 | 任务空态裸文本：`sprintNoTasks` 一行字居中，无为何空、无 CTA | sprint_screen.dart:175-178 | §4.3 空态三要素 |
| S-G5 | **进度位掺奖励编码**：成就进度条用稀有度色（rare/epic/legendary）作 valueColor，渐变横幅叠在冲刺主内容上方；`_getRarityColor` 私有 helper 重复定义两份 | sprint_screen.dart:503-510 与 :602-610（rarityColor 进度条）、:447-460（渐变横幅）、:538-549 与 :630-641（重复 helper） | §1.5.1/B-02 两层分离（进度位只编码完成度）；§5.3 gradient 预算 |
| S-G6 | **口径双源**：剩余天数客户端自算（`plan.targetDate.difference(DateTime.now())`）而 exam 卡用服务端 `days_left`（provider:36）；总进度 `plan.progress` 来源为 plan 摘要接口，与 exam payload 的 `today_progress.completion_rate` 各出一套 | sprint_screen.dart:216、:256（`toStringAsFixed(0)`）；exam_sprint_dashboard_provider.dart:36（`days_left` 服务端值） | §9.4 口径单一事实源（跨面派生值双算）；§6.3 准入② |
| S-G7 | **紧迫感语义越槽**：`daysLeft <= 3` 时全卡 accent 翻转为 `DS.error`（error 槽定义是失败/错误/逾期，非「临近截止」——那是 warning 槽），且为整卡翻转（header 图标/模式 pill/任务组描边全部染色） | exam_sprint_dashboard_card.dart:41（`accentColor = data.daysLeft <= 3 ? DS.error : DS.brandPrimary`） | §1.5 槽位语义单义（对比 Duolingo 品类惯例的分级色阶） |
| S-G8 | **预测数裸奔**：通过概率百分数直出（无口径一行、无分档文案），红绿灯三色编码未经 CB-safe 变体，入场动画 1200ms 超梯 | exam_sprint_dashboard_card.dart:599（`_formatPercent(value)`）、:644-648（<0.4 error/≤0.6 warning/else success）、:539-543（`Duration(milliseconds: 1200)`）；基线 `exam_sprint_dashboard_card {offLadderDuration: 2}` | §6.3（预测类无子条款，属规范空白）；§1.6 CB 冗余；§2.1 G1（1200∉白名单） |
| S-G9 | 今日进度文案同卡二出（倒计时下一处 + 弧旁一处，同一数字两种措辞） | exam_sprint_dashboard_card.dart:469-470 与 :628-631 | §0.2 必达项面积效率（冗余占面积） |
| S-G10 | 日期手工拼接 `'${group.date!.month}/${group.date!.day}'`，绕开 `date_formatting.dart` 唯一入口 | exam_sprint_dashboard_card.dart:816 | §6.4 时间格式规范/X3 |
| S-G11 | 状态→颜色→标签映射为私有 inline 词典（`_statusLabel` switch + `_TaskRow` 色映射），未进 lexicon 域 | exam_sprint_dashboard_card.dart:897-901、:956-961 | §6.4 组装 owner 登记（轻度，映射本身正确） |
| S-G12 | 考日常驻横幅 3000ms repeat(reverse) 浮动动画（DecorationMode 门控，但 animated 档下为常驻循环源，占 home 屏持续源名额） | exam_sprint_dashboard_card.dart:250-253、:260-268 | §2.1（3000 超梯）/§2.6 持续源；基线 `offLadderDuration: 2` 之一 |

### 2.3 星图 galaxy（`features/galaxy/presentation/screens/galaxy_screen.dart` + `widgets/galaxy/star_map_painter.dart`）

| # | 差距 | 证据（file:line @5b912dcf） | 违反条款 |
|---|---|---|---|
| X-G1 | **裸异常直出**：加载失败面板 `message: '$_loadError'` 把 Object 插值直接给用户 | galaxy_screen.dart:158（`Object? _loadError`）、:2870（`message: '$_loadError'`） | §4.5/X6 禁裸异常 |
| X-G2 | D5 双视图未落地（v1.0 §10.3 批 3 已排期）：Tab 默认仍是全局画布，无「局部邻域工作视图」；「下一个建议碰什么」缺单 chip 承载。已有地基：`_spotlightNodeIds`/`_spotlightAnchorId` 聚焦机制与 `reviewUrgencyReason` 推荐理由数据链已存在 | galaxy_screen.dart:3120-3126（spotlight 机制）、:913-918（reviewUrgencyReason→focusPrompt/chatMode 映射） | §7.2/§8.6 必达项①（已知未落，本卡给最小切片） |
| X-G3 | 标签碰撞消隐 pass 未落地：painter 全文仅边-矩形相交检测（`_segmentIntersectsRect`），无标签占位/消隐逻辑 | star_map_painter.dart:2500-2506（唯一 overlaps 用途为边检测） | §7.2 锤内规范 1（已知未落） |
| X-G4 | shell 沉浸化未落地：galaxy Tab 激活时底导航无 dark 变体切换（5 Tab 结构还从 v1.0 时的 4 Tab 变为含 community 的 5 Tab，`shell_navigation.dart:236-242` 为 galaxy 目的地） | core/navigation/shell_navigation.dart:229-249（destinations 无 dark 变体逻辑） | §7.2 锤内规范 2（已知未落，且 Tab 结构漂移 v1.0 未记录） |
| X-G5 | offLadderDuration 基线全 features **单文件最高**：galaxy_screen 21 处（入场编排/展开动画类） | 基线 JSON `galaxy_screen.dart {offLadderDuration: 21, gradientLiteral: 2, particleBypass: 2}` | §2.1（多为一次性入场动画，北极星加权低——辩论见 §3） |
| X-G6 | 「还没有掌握记录」横幅以 `Positioned(top:56)` 叠在画布上方，位于节点密度区顶部；横幅自带硬编码深navy底 `Color(0xE6101929)` | galaxy_screen.dart:3128-3156（Positioned 叠放）、:3799（字面量） | §4.3-4（V24 边界案，辩论见 §3）；E1 豁免内但未登记 |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转 v1.0 台账**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| C-G1 | chat 等待期两源并发，违反 ≤1 铁律 | 蓝方：呼吸是「AI 在思考」的氛围暗示，胶囊脉冲是状态指示，语义不同 | G1 真差距（§2.6 不豁免等待窗口）；G2 收益中/成本 S（删 overlay 或改为事件单脉冲）；G3 高——等待是 chat 最高频时刻，动效噪声直接消耗耐心 | **采纳**：等待期只留胶囊脉冲（事件驱动窗口内恰好 1 源），breath overlay 删除或降为单次入场 |
| C-G2 | D-1 守卫只堵 `createBreathingController` 引用，手写 repeat(reverse) 全部漏网 | 蓝方：守卫扩 repeat 扫描会误伤进度条/物理模拟 | G1 真差距（守卫盲区是系统性风险，home/galaxy 同型已现）；G2 收益高/成本 M（需白名单设计）；G3 中 | **改写采纳**：不扫一切 repeat，只扫「长周期（≥2s）repeat(reverse:) 且无 DecorationMode 门控」模式，白名单登记既有合法件（见 N3） |
| C-G3 | chat 3 层渐变装饰超 §5.3 账本 | 蓝方：渐变是氛围签名（AI 在场感），v1.0 给 galaxy 豁免先例；chat 的 6 处基线已冻结在案 | G1 部分成立（账本确实超，但氛围层是 v1.0 后 B3-CHAT 有意保留的「AI 在场感」设计）；G2 收益低（视觉差异微）/成本 S；G3 低——不影响备考效率 | **砍**（不立 v1.1 新条）；氛围层维持现状，gradientLiteral 基线照 ratchet 只降不升，触碰即治理 |
| S-G1 | sprint 双文件全裸组件 + 守卫失明，是「系统性失控」重现的前兆 | 蓝方：组件工作正常，迁移是纯工艺债 | G1 真差距（北极星主场景不受任何组件门禁约束，等于新债免检通道）；G2 收益高（一劳永逸）/成本 M；G3 高（主场景的每一次后续迭代都在盲区里） | **采纳**：scan roots 扩 `features/plan/presentation`（N1），裸件迁移入改造清单 |
| S-G2 | 错误态无重试是 §4.5 明面违规 | 蓝方：下拉刷新可替代（SparkleRefreshIndicator 在外层） | G1 真差距；G2 收益高/成本 S；G3 高——备考周加载失败无重试=用户流失点，下拉刷新不可发现 | **采纳**（改造 #3） |
| S-G3 | 骨架与真实布局形异，加载完成必跳变 | 蓝方：sprint 屏骨架出现时间极短 | G1 真差距；G2 收益低-中/成本 S；G3 中 | **采纳**（并入改造 #3，同一文件顺手） |
| S-G4 | 空态裸文本 | 蓝方：新冲刺引导在 `_NoActiveSprintView` 已合格（:111-148），任务空态出现概率低 | G1 真差距；G2 成本 S；G3 中（「有冲刺但还没排任务」正是新手第一周状态） | **采纳**（并入改造 #3） |
| S-G5 | 稀有度色进进度条=B-02 两层分离违规（进度位混入奖励编码） | 蓝方：成就区本来就是动机层，稀有度色是身份色合法域（v1.0 §8.7-3 允许稀有度色存在） | G1 真差距（§8.7-3 允许的是「稀有度展示位」，进度条 valueColor 是进度位）；G2 收益中/成本 S；G3 中-高（动机层喧宾夺主把「还差多少」读成「抽卡进度」） | **采纳**：进度条回归中性/success 口径色，稀有度色保留在图标环（身份位） |
| S-G6 | daysLeft 客户端自算与 exam 卡服务端值是 §9.4 双算，期末倒计时差一天就是事故 | 蓝方：targetDate 推算简单确定，不会真差一天（除非时区） | G1 真差距（跨面同值双源正是 §9.4-3 跨账本矛盾的同型）；G2 收益高/成本 S-M（exam payload 已有 days_left，sprint 屏改读即可）；G3 **极高**——倒计时是期末用户的锚点数字 | **采纳**（改造 #1，top1 候选） |
| S-G7 | days≤3 全卡 error 翻转，error 槽语义被挪用 | 蓝方：倒计时变红是考试类 app 强惯例，用户读作「紧急」不读作「出错」；全卡翻转让紧迫感有沉浸力 | G1 半差距（惯例支持红色紧迫感，但无分级、且与 §1.5 槽位定义冲突）；G2 收益中/成本 S；G3 中 | **改写采纳**：保留紧迫感但立色阶——≥7d 中性、≤7d warning、≤1d/考日 error；error 槽在此上下文扩展定义为「不可挽回节点临近」（N5） |
| S-G8 | 通过概率应删（§6.3-2 禁模型自我指标）或至少 band 化 | 红蓝激辩：蓝方激进案=直接删（伪精度）；红方=这是全卡最强动机数字，Duolingo 先例（目标概率）+ 北极星用户最关心「我能不能过」 | G1 真差距（现行裸奔无口径）；但「删」不过 G2——删除损失动机杠杆；G3 高 | **改写采纳**：规范化保留——口径一行+低概率分档文案+CB-safe 色源+时长归 M3（改造 #2，N6 立预测数子条款） |
| S-G9 | 同卡两处今日进度文案 | 蓝方：S 级纯文本问题，不值独立条目 | G1 成立但 G3 低 | **砍**（独立条目）；并入改造 #1 口径归一时顺带处理 |
| S-G10 | 日期拼接绕唯一入口 | 无实质反驳 | 三关全过但体量小 | **采纳**（并入改造 #3 文件同批，X3 防复发） |
| S-G11 | `_statusLabel` 私有组装未登记 owner | 蓝方：映射存在且正确，仅位置问题；动 lexicon 注册要过 §6.5 arb 纪律，成本>收益 | G1 弱差距；G3 低 | **砍**（不立条）；留待 plan 域下次 copy 批顺手登记 |
| S-G12 | DayZero 3000ms 常驻浮动 | 蓝方：考日横幅一生出现一次，浮动是仪式感；已有 DecorationMode 门控 | G1 真差距（仪式感可以单次入场表达，循环浮动无信息量）；G2 成本 S；G3 低-中 | **采纳**（改造 #8：循环改单次入场，门控保留） |
| X-G1 | 裸异常直出，X6 明面违规 | 无实质反驳 | 三关全过，成本 S | **采纳**（改造 #4） |
| X-G2/X-G3/X-G4 | 双视图/消隐/沉浸化未落 | 蓝方：v1.0 批 3 已排期，重复立卡=双 owner | G1 真差距但**已有 owner 条款**（§8.6 Top5/锤内规范） | **转 v1.0 台账**（不立新条）；本卡贡献为：给批 3 主卡补对标依据（Obsidian local graph/Duolingo START 气泡）+ 最小切片建议（改造 #10，避免等 L 级大卡期间北极星颗粒无收成） |
| X-G5 | 21 处 offLadder 专项清偿 | 蓝方：入场编排是一次性动画（M5 narrative 相邻档），强制归梯收益仅数字整洁 | G1 弱；G2 成本 M 收益低；G3 低 | **砍**（专项）；ratchet on touch（基线已冻，只降不升） |
| X-G6 | 掌握空横幅叠画布=V24 | 蓝方：横幅有边界有 CTA，非「空态与数据打架」原罪型；且挂 top:56 安全区，节点密度核心在中部 | G1 弱差距；G2 成本 S；G3 低 | **砍**（撤组件案）；收为锤内规范 3 扩展半句：「统计泡与横幅类覆盖件不遮节点」（N8 台账行），字面量 0xE6101929 随触碰 token 化 |

**辩论统计**：18 条 → 采纳 8 / 改写采纳 3（C-G2、S-G7、S-G8）/ 砍 6（C-G3、S-G9、S-G11、X-G5、X-G6 撤件案、S-G12 反对案中保留案）/ 转 v1.0 台账 1（X-G2/X-G3/X-G4 合并计 1）。砍单主导理由：**北极星加权低**（4 条）与**双 owner 风险**（2 条）。

---

## 4. SPEC v1.1 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0：编号规则 + 依据 + 可验收数字；不推翻 v1.0 任何条款。生效方式建议沿用 v1.0 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。

**N1（§0.2/§8 增补）· surface 登记表 +1：冲刺仪表盘为第 10 治理面**
- 定义：`features/plan/presentation/screens/sprint_screen.dart`（冲刺屏）与 `features/home/presentation/widgets/exam_sprint_dashboard_card.dart`（home 内嵌冲刺仪表卡）合称 sprint surface，期末一周北极星主场景。
- 必达项（≤2，v1.0 第一硬条款同制）：①剩余时间与今日完成度一眼可信（口径走 §9.4 单一事实源）②下一步动作单一 CTA。
- 守卫：`check_ux_component_convention.py` 扫描根增 `features/plan/presentation`（`features/community`、`features/leaderboard` 域另立卡评估，本卡不动）。
- 【依据：§1.2 结构性发现；§0.2 矩阵无 sprint 行的空白；FLEET-BRIEF「冲刺完成度=sprint_task_ledger 唯一定义」】

**N2（§9.4 增补第 5 条）· 跨面派生值规则**
- 同一派生值（剩余天数/完成度%/进度差）全 app 只准一处计算：**服务端下传值优先，客户端本地 `DateTime.now()` 推算类派生禁新增**；存量靶：`sprint_screen.dart:216`（daysLeft 客户端自算）。
- 验收沿用 A9.5 范式：跨屏断言测试断言 sprint 屏与 exam 卡两处剩余天数同源同值。
- 【依据：§2.2 S-G6；§9.4-3 跨账本对账的同型前移】

**N3（§2.5 D-1/§2.6 澄清）· 呼吸禁令按「实现无关」口径执行**
- D-1 的禁令对象是**模式**（常驻循环呼吸/浮动），不是 `createBreathingController` 一个函数。features 域内任何 `AnimationController.repeat(reverse: true)` 或 ≥2s 周期 `repeat()` 计为持续动画源，必须：①过 DecorationMode/PerformanceTier 门控；②占用 §2.6 唯一名额。
- 等待窗口豁免细则：事件驱动的等待期（阶段胶囊类）允许**恰好 1 个**持续源，窗口结束即归还名额。
- 守卫：`breathingController` 维扩为「长周期 repeat 模式」扫描（含既有合法件白名单登记，防误伤进度环/物理动画）。
- 【依据：§2.1 C-G1/C-G2；§2.5 G-4 门控规格先例；存量靶 chat_screen.dart:3845-3849、exam_sprint_dashboard_card.dart:250-253】

**N4（§4.5 错误态增补）· 屏级错误面板三件套硬性 + Object 插值禁令例证**
- 屏级（非组件级）错误面板必须同时具备：人话标题 + 影响一句 + **重试钮**（可发现性不低于屏内首屏可见）。存量靶：`sprint_screen.dart:195-205`。
- `'$_loadError'` / `'$error'` 类 `Object?` 插值直出为 X6 新增例证（机检可扩 `'\$_\w*[eE]rr'` 模式），存量靶：`galaxy_screen.dart:2870`。
- 【依据：§2.2 S-G2；§2.3 X-G1；对标 §1.1-1.3 错误态共性 5】

**N5（§1.5 增补）· 截止临近色阶（倒计时上下文专用）**
- 倒计时类语义分三档：**≥7 天中性层 → ≤7 天 warning → ≤1 天/考日 error**。error 槽语义在本上下文扩展为「不可挽回节点临近」，仅限倒计时位使用，禁泛化为普通过程色；§1.5 原四槽定义不变。
- 现行 `daysLeft <= 3 → error`（exam_sprint_dashboard_card.dart:41）为存量靶，迁移时同步收敛翻转范围（整卡翻转 → header+倒计时数字两处）。
- 【依据：§2.2 S-G7 辩论（惯例采纳+语义修正）；对标 §1.2 考试倒计时品类惯例】

**N6（§6.3 增补预测数子条款）· 模型预测数准入四件**
- 模型预测类数字（通过概率/预估分/覆盖率预测）准入须同时满足：①单一事实源可溯（§9.4）；②**口径一行就地可见**（「按你当前进度估算」级）；③低档分档文案兜底（概率 <0.4 时附「还来得及，先攻高頻考点」类动作语）；④编码色走 theme CB-safe 变体（含 colorBlindFriendly 适配），入场动画 ≤M3（320ms）。
- 【依据：§2.2 S-G8 辩论（规范化保留裁决）；对标 §1.1 Claude 免责行、§1.2 Duolingo 概率小字；存量靶 exam_sprint_dashboard_card.dart:599/:644-648/:539-543】

**N7（§4.1 澄清）· 指标瓦片非 pill**
- 数据展示卡（metric tile：标签+主数+口径小字三段式）不适用 SemanticPill 归一——pill 是扫视件，tile 是读数件。但私有类命名禁用 `*Pill` 后缀（防与 §4.1.1 守卫语义冲突），owner 归 SparkleCard/DashboardSectionShell 家族；存量 `_MetricPill`/`_ModePill` 更名随触碰迁移，不设专项。
- 【依据：§2.2 S-G1 辩论中的部分砍单；防守卫误判】

**N8（§10.5 台账新增行，随 v1.1 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N1 sprint surface 入守卫根 | 未开工 | 改造 #7 |
| N2 daysLeft 双算收敛 | 未开工 | 改造 #1 |
| N3 chat breath overlay + DayZero float | 未开工 | 改造 #6/#8 |
| N4 sprint 错误态重试 / galaxy 裸异常 | 未开工 | 改造 #3/#4 |
| N5 urgency 色阶迁移 | 未开工 | 改造 #9 |
| N6 通过率弧规范化 | 未开工 | 改造 #2 |
| N7 metric tile 更名 | 未开工（触碰即迁） | —— |
| 锤内规范 3 扩展半句（覆盖件不遮节点）+ 0xE6101929 token 化 | 未开工（触碰即迁） | —— |
| v1.0 遗留备忘：shell 底导航已从 4 Tab 变 5 Tab（community 加入），v1.0 §7.2 锤内规范 2 的落点描述需随批 3 主卡更新 | 登记即闭环 | —— |

---

## 5. 改造清单（按北极星收益排序 top10，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **冲刺倒计时与进度口径归一** | sprint_screen.dart:216/:256；exam_sprint_dashboard_provider.dart:36 | sprint 屏 daysLeft 改读 exam payload（或统一 plan 域服务）服务端值；`plan.progress` 标注口径来源或替换为 ledger 口径；顺带删 S-G9 重复文案 | 跨屏断言测试（A9.5 范本）：两处剩余天数同源同值；客户端无 `DateTime.now()` 推算派生值 | M |
| 2 | **通过率弧规范化** | exam_sprint_dashboard_card.dart:599/:644-648/:539-543 + arb 新 key | 加口径一行（「按当前进度估算」）；<0.4 档附动作文案；色源改走 theme CB-safe 变体；动画 1200→320ms（M3） | widget test：口径文案存在、低档文案触发、时长 ∈ 正典集；CB 变体切换无红绿依赖 | M |
| 3 | **sprint 屏三态补齐** | sprint_screen.dart:195-205（error）/ :175-178（empty）/ :644-716（skeleton）/ exam card:816 | 错误态改 CustomErrorWidget 三件套（人话+影响+重试）；任务空态改 EmptyState（为何空+去排任务 CTA）；骨架按真实布局重拼（header 卡+成就行+任务行）；日期拼接走 date_formatting | 三态 widget test 各 1；骨架→内容无布局跳变（golden 前后帧）；`'${group.date!` 模式清零 | S-M |
| 4 | **galaxy 错误态人话** | galaxy_screen.dart:2870（+158 存储类型） | `'$_loadError'` 改人话模板（「星图加载失败，你的数据没有丢」级）+ 保留既有 retry action；error→人话映射可先局部函数后收 lexicon | widget test：Object 值不出现于 Text；快照断言文案为人话模板输出 | S |
| 5 | **sprint 进度位诚实编码** | sprint_screen.dart:503-510/:602-610/:447-460/:538/:630 | 进度条 valueColor 回归中性/success 口径色（稀有度色保留在图标环身份位）；渐变横幅降级为 S2 色阶+描边；两份 `_getRarityColor` 合一 | 进度位色值断言（仅中性层/语义槽派生）；gradient 基线 -1；重复 helper 清零 | S |
| 6 | **chat 等待期持续源裁 1** | chat_screen.dart:3845-3849（+1435-1440 挂载点） | breath overlay 删除或改单次入场脉冲；阶段胶囊脉冲（事件窗口内）为唯一持续源 | 等待态活跃 repeat 源计数=1（widget test 或 PulseScope 断言）；reduce-motion 行为不回退 | S |
| 7 | **sprint surface 入守卫** | scripts/guards/check_ux_component_convention.py:42-52 + 裸件迁移 | scan roots 增 `features/plan/presentation`；基线登记现值；裸件迁移：Chip:268→SemanticPill/TaskPill、Card:373→GraphiteCardSurface（去 elevation）、OutlinedButton:277/FilledButton:374/TextButton:156→SparkleButton 家族、`_MetricPill`/`_ModePill` 更名 | 守卫跑绿+manifest 登记；新文件零容忍生效；基线 JSON 按共享态纪律由合并窗口刷新 | M |
| 8 | **DayZero 浮动降级** | exam_sprint_dashboard_card.dart:250-268 | repeat(reverse) 改单次入场（M3 一次）+ 静止定帧；DecorationMode 门控保留 | 常驻件无循环 controller；offLadder 基线 -1 | S |
| 9 | **urgency 色阶迁移** | exam_sprint_dashboard_card.dart:41 + arb | N5 三档落地（≥7d 中性 / ≤7d warning / ≤1d error）；翻转范围收敛至 header+倒计时数字 | 三档色值断言测试；error 槽在 ≤7d 档不出现 | S |
| 10 | **galaxy 工作视图最小切片**（衔接 v1.0 批 3 主卡的前置颗粒） | galaxy_screen.dart:3120-3126（spotlight 地基）/:913-918（推荐理由链） | 不等 D5 大卡：默认进图先聚当前目标锚点邻域（复用 spotlight），挂「下一个建议碰：X」单 chip（§4.1.4 ≤1 名额） | 进图默认视野节点 ≤20；推荐 chip 同屏 ≤1；chip 点击直达复习流 | L→切片 M |

**被砍项备忘**（防后续卡重复立项）：chat 渐变氛围层保留现状（基线 ratchet 管住）；sprint AppBar 5 actions 收编（P2 观察，chat S15 有先例再做）；`_statusLabel` lexicon 登记（plan 域下次 copy 批顺带）；galaxy 21 处 offLadder 专项清偿（ratchet on touch）；掌握空横幅撤除（收为锤内规范半句）；chat 顶栏标题 2 行（v1.0 §8.2-4 已有条款，勿双立）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC-V1_1/REPORT.md`（本文件）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作
- [x] /tmp 无驻留（全程未写 /tmp）
- [x] 未 commit / 未 push
- [x] 引用代码均为 @5b912dcf 实测（rg/read），守卫基线数为冻结 JSON 实测值；无编造引用
