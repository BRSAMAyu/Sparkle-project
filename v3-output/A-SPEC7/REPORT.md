# A-SPEC7 · 设计语言第七轮：两新面（首次价值时刻 TTV / 视觉层级与排版节奏）UX 研究 → 自审 → 辩论 → SPEC v1.7 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡第七轮 ｜ 2026-09-22 ｜ worktree **wt262**（分支 wt262-aspec7，base **7f5d949b**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read/perl 邻近计数），file:line 均为 @7f5d949b 实测（该基线已含 A-SPEC6 后续落地批：GALAXY-A11Y / GALAXY-KEYNAV / OFFLINE-READ）。
> 前置读透：`v3-output/A-SPEC6/REPORT.md`（第六轮范本，本卡形制对齐它）+ `v3/FLEET-BRIEF.md`（战役上下文）+ `v3-output/V13/REPORT.md` 与 `v3-output/V13-RETEST/REPORT.md`（新用户首飞实测数据，本轮 TTV 面的量化底座）+ `v3-output/TOUR/REPORT.md`（价值链后端证据）+ `v3-output/DL-R3/SPEC.md`（v1.0 正文，§3 排版与密度/§7 交互流程/§8 屏级蓝图为本轮两面的条款挂靠点）。本提案**不推翻 v1.0-v1.6 任何条款**，全部为增量/执行令/存量靶登记，编号接续 v1.6 的 N38（N39 起）。
> 对标研究方法声明：本会话外部搜索配额耗尽（web_search 实测 429「Weekly/Monthly Limit Exhausted，reset 2026-09-24」，与前六轮同况），对标做法基于公开常识 + UX 专业判断（沿用 A-SPEC-V1_1/A-SPEC2/3/4/5/6 六轮卡内授权先例）；引用代码均为树内实测。
> 两面范围界定（按卡）：①首次价值时刻=注册→第一次感受到核心价值的路径审计（V13 实测口径延伸到「首个任务完成/首次诊断/首次记忆被引用」三个价值时刻）+ FTUE 分层（首用空态引导质量/首次诊断门槛/访客→注册转化钩子）+ 对标提炼「首日价值密度」规范候选；②视觉层级与排版节奏=DS 字阶令牌实际分布审计（通道/字号/字重/行高四维计数）+ 密度节奏（spacing 令牌分布/卡片内外留白）+ 长文阅读节奏（聊天长回复/知识详情）+ 单屏层级采样。

---

## 0. 方法与多轮过程记录

照前六轮四步执行：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 面1 按 Duolingo 式 FTUE 公案（aha-before-signup：先玩第一课再要账号，60 秒内进核心循环）/ Notion 模板即用（打开即得可用产物）/ 公认 FTUE 公约（空态是第一引导员、注册是价值完成后的动作而非门票）提三维做法；面2 按 Material 3 type scale（15 角色、字号+字重双编码）/ HIG Typography（CJK 行高豁免）/ 编辑排版本常识（模数阶梯、行长 40-60ch、段距是节奏的一半）提四维计数法 | §1 两张对标表 | 两面共性直指北极星：**TTV 是「期末只剩一周的用户根本不会给你第二次机会」——注册后第一个 10 分钟里没见到价值，竞品就是 GPT 裸聊；排版是「疲惫备考者的扫视带宽」——层级拉不开=一切都在喊，等于什么都没说**；新增两条面性公约：**首用空态必答「下一步做什么」**；**层级必须双编码（字号+字重），单靠加粗不构成层级** |
| R2 自审 | 面1 全链代码走查（routes 重定向/auth 三屏/persona 5 步/modeling chat/home 首用空态/各核心面 EmptyState/celebration/receipt 链）+ V13/V13-RETEST/TOUR 三报告实测数据回收 + 访客转化钩子全库 grep；面2 全库四维计数（typo.*/DS shim/textTheme/raw fontSize 四通道逐值分布 + FontWeight + 行高 + DS.spacing 全档 + 卡片家族内边距抽样）+ SparkleMarkdown/ContentConstraint 长文链路实读 | §2 两张全景表 + 差距清单 12 条（带 file:line） | **「人人都是 14px」的卡面假设实测不成立，真实形态更糟：人人都是 12px**（bodySmall 12px 经三通道合计 ~819 处，12px 档占 token 通道用量 ~51%，而 ≥16px 全部加起来仅 ~19%）；**w800×127 的字重通胀**（DS 上限 w700，w400 全库仅 2 处）；**访客是「侧门进客厅但永远没人请你留下」**（零转化钩子，全库 grep 0 命中）；**长文段距缺失**（SparkleMarkdown 未设 pPadding，flutter_markdown 0.6.23 null→0，多段 AI 回复黏连） |
| R3 辩论 | 12 条逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：采纳 5 / 改写采纳 3 / 砍 0 / 转台账 2 / 豁免观察 2 | 主导裁决理由：TTV 面四条采纳里有三条是 S 级成本（基建全在，只差最后一屏/一句话）；排版面全部改写为「登记制+执行令」，**不做大规模数值清洗**（§3.1 数值迁移本就是登记的长尾批，本卡不与之抢道） |
| R4 成文 | 过关差距 → v1.7 增量条目 N39-N44 + 台账 N45 + top8 | §4 / §5 | v1.7 共 6 条增量，全部为 v1.0-v1.6 的增补/执行令/存量靶登记，无推翻 |

**结构性结论先行（两条）**：
1. **TTV 是「骨架已通、第一口价值偏晚」**：链路每一段都有人负责且大部分实测达标（引导完成→访谈就绪 6-8s、主聊天发送→回复渲染 ≤3s、访谈断流 75s 看门狗已落地、首任务完成有 confetti 仪式、记忆引用有 receipt chip）——但把镜头拉远看全程：注册表单 4 字段+2 同意框 → persona 5 步全问完 → 建模访谈 → 聊天里确认 → 冲刺才成立 → 首个任务完成。「第一次真正帮到学习」要跨 **6 个决策站**；而唯一的低门槛路径（访客）却在产品里**没有任何一个转化钩子**——访客跳过全部引导直落 home（routes.dart:168/:227），此后没有任何机制请他注册。
2. **排版是「节奏表已定、乐队没看谱」**：§3.1 已把角色数值重定标并冻结（display 46/headline 28/title 22/subtitle 19/body 17/secondary 15/label 13/caption 12），执行基建超预期（SparkleTypography 单一真相源 + M3 15 角色全映射，Material 组件不再回落第三字阶）——但实际用量分布与节奏表背道而驰：四通道并存（context.typo 421 / DS deprecated shim 760 / textTheme 1361 / 字面量 1278），12px 一档吞掉 token 通道一半用量，正文档（≥16）合计不足两成，标题层级靠 w800 加粗硬撑（127 处，超 DS 上限 w700），同名字段跨通道渲染值还会不一致（DS.titleMedium→19px vs textTheme.titleMedium→16px，§2.1b 实测）。

---

## 1. 两面对标研究表（R1）

### 1.1 首次价值时刻 · 对标：Duolingo FTUE / Notion 模板 / 公认 TTV 公约（公开常识，声明见页眉）

| 维度 | Duolingo（TTV 公案） | Notion（模板即用） | 公认 FTUE 公约 | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 价值先行 | 选完语言**先玩第一课**，60 秒内进核心循环；账号创建押后到「保存进度」时刻 | 打开即套模板，首个可用文档在第一屏 | **aha-before-signup**：注册是价值完成后的动作，不是体验的门票 | Sparkle 已有访客态（guest login），但访客被剥夺了全部个性化引导又没有转化时刻——「侧门」开了却没设计 |
| 首日价值密度 | 首个会话 2-5 分钟内可完成且必有产出（XP/反馈声效） | 第一屏就有可交互产物 | **首个会话必有可带走的价值物**（完成一课/建成一页） | Sparkle 的价值物=确认后的冲刺任务卡；它押在「聊天确认」这个单一咽喉上（TOUR S2：confirm→today 出任务），任何一段迟滞=首日零价值 |
| 空态即引导员 | 每屏下一步唯一且可见 | 空页面推荐模板 | **空态必须回答「我现在该做什么」**，且 CTA 直达价值动作而非菜单 | home 首目标空态是满分答案（5 个目标 chip 直达聊天 prompt）；但认知诊断空态无 CTA、galaxy 首用卡与统计互相遮挡（V13 D-10 遗留） |
| 个性化即承诺 | 2-3 问带进度条，「正在为你生成计划」 | 模板即承诺 | **收集前先给承诺**：问题越靠前，越要说明「答案将换 来什么」 | persona 5 步问完才放行，问题与回报的关联只在最后一步的建模访谈里兑现；访客则 0 问 0 承诺 |
| 摩擦位置 | 摩擦全部放在价值之后 | 零配置起步 | **决策步计数**：注册到首个价值动作之间的用户决策次数是 TTV 的真实度量 | 注册 6 次输入/勾选 + persona 5 步 + 访谈 ≥1 轮 + 确认 1 次 ≈ **13 个决策点**才见首任务；其中一半可以后置或并行 |

**面性公约提炼**：①**首日价值密度红线**（注册→首个价值动作的决策步必须可数且 ≤3 站为佳，超出即 IA 债）；②**空态必答下一步**（首用空态 CTA 直达价值动作，禁只有解释没有动作）；③**转化钩子挂在价值时刻后**（访客完成第一个价值动作的当下是唯一正当注册请求时机，禁全域骚扰）；④**收集换承诺**（每问一段个性化问题必须预告它换来什么）。

### 1.2 视觉层级与排版节奏 · 对标：Material 3 type scale / HIG Typography / 编辑排版常识（公开常识，声明见页眉）

| 维度 | Material 3 | HIG | 编辑排版本常识 | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 字阶结构 | 15 角色固定档（display 57→label 11），档间差 ≥3-5px | Text Styles 全量语义角色 | 模数阶梯（1.125-1.25 比率），**档间差必须可感知** | 档间差 <3px 等于没分层；Sparkle 中段 19/16/14/12 相邻差 3/2/2px——中段天然拥挤，必须靠字重/颜色补偿（但实测补偿过度：w800） |
| 层级编码 | 字号+字重**双编码**（titleLarge 22/w400-500 体系） | Dynamic Type 全角色传导 | 大小、粗细、颜色、留白**四通道协同**；单通道强调=喊 | 实测单通道加粗通胀（w800×127、w400×2）——层级退化成「谁喊得响」；3.1.2 已禁「加大加粗连排」，w800 是其变体逃逸 |
| 行高节奏 | display 紧（1.0-1.2）→ body 松（1.5-1.6）随字号反比 | CJK 正文行高放宽至 ~1.5+ | 行高是节奏的骨架：**正文松、标签紧，全局成体系**；段距≈0.5-0.75×行高 | SparkleMarkdown 角色化行高（1.45-1.7）方向正确；但全库字面量行高 1.1-1.6 七档散布与角色锚定脱钩；**段距缺席**（pPadding 0）是长文节奏最大缺口 |
| 密度节奏 | 4dp 基栅格 | 8pt 体系 | 留白分层：**组内 < 组间 < 组块间**，三档可辨 | DS.spacing 八档 4-64 主力集中 8/12/16（66.6%），半格档（2/6/10/14/18）占 18% 侵蚀栅格语义；卡内边距三档并存（16/12/10）致「卡片家族」无一致呼吸 |
| 长文体验 | body 16/1.5、行长移动端全宽即可 | 正文 ≥17pt 级（INTL 硬条款本源） | 行长 40-60ch、**段距必须显式**、标题脱行（避免孤行） | 移动端全宽+ContentConstraint tablet 720 已达标；缺的是段距与「聊天正文/面板元数据」的角色区分（气泡正文 10-13px 五档字面量混用） |

**面性公约提炼**：①**层级双编码**（新文本样式必须同时声明档位与字重，禁 w800+ 逃逸档）；②**12px 是元数据专用地板**（正文/可读内容禁降入 12px 及以下）；③**通道归一**（新代码唯一通道=context.typo/textTheme——二者同值；shim 与字面量为冻结存量只降不升）；④**长文段距显式化**（段距是排版节奏的一半，不设=黏连）。

---

## 2. 自审差距清单（R2，全部 @7f5d949b 实测）

### 2.0 先说达标项（诚实记录——TTV 链路与排版基建是本轮最大好消息）

- **引导链全通且实测达标**：注册→直跳画像引导（routes.dart:217-224 非访客且 onboardingCompleted==false 强制进 persona）；引导完成→建模访谈就绪 **6-8s**（V13-RETEST ③ Major-1 通过，2s 粒度帧轮询实测）；主聊天发送→AI 回复渲染 **≤3s**（V13-RETEST ①，B-01 修复生效，重复发送已由 in-flight 禁发杜绝）；访谈中段断流 **75s 看门狗**（modeling_chat_screen.dart:48-50，V13 B-02 修复落地）+ 阶段胶囊常驻（V13-RETEST ②通过）。
- **访客通道存在且顺畅**：login 页「以访客身份继续」与登录钮同级（login_screen.dart:273-277，ghost 变体）；guest 走独立 guestLogin（auth_provider.dart:195-206），**跳过全部引导直落 home**（routes.dart:168/:226-230 `isGuestUser` 分支）——0 摩擦进核心面，是 aha-before-signup 的正确起点（虽然缺转化钩子，见 TV-G2）。
- **home 首用空态是全库 TTV 最佳实践**：`_buildFirstGoalEmptyState`（dashboard_screen.dart:404-498）——触发条件严谨（无 nextActions+无 sprint+无 growth 才显，:209-216）；5 个目标 chip **每个都 deep-link 进聊天并预填 prompt**（:438-473，如 `dashboardGoalExamSprintPrompt`）+「和 AI 开始」/「快速创建」/「打开任务列表」三 CTA（:480-492）；附 `_buildOnboardingWelcome` 欢迎壳（:500+）。这就是「空态必答下一步」的满分答案。
- **EmptyState 组件体系建成且核心面接线**：typed factory（noTasks/noChats/noPlans/noErrors/noResults）全带 action CTA（empty_state.dart:34-95）；任务列表空态→直达 `/tasks/new`（task_list_screen.dart:376-384）；错题本空态→直达录错题、且「搜过零命中」与「空库」分离防误建重复错题（error_list_screen.dart:477-505，N28-③ 已立）。
- **首个任务完成有仪式**：TaskCompletionCelebration（SparkleConfetti + 目标对照 criteria 列表，task_completion_celebration.dart:62-160）由 task_execution_screen.dart:1182 挂载——「第一次帮到学习」的时刻有可感知的正反馈。
- **首次记忆被引用可见**：AI 引用记忆时消息元数据携带 `memory_reference_receipt`，由 context_receipt_bar.dart:90 解码渲染——「它记得我」的时刻有 UI 承接。
- **SparkleMarkdown 长文引擎角色化行高**：五内容角色各锚定行高（chatBubble 1.45/taskGuide 1.65/seedBody 1.7/knowledgeSummary 1.55/standard 1.5，sparkle_markdown.dart:22-27）；h1-h6 相对 base 阶梯（fontSize+8/+6/+4/+2/+1，:199-205）；代码块独立卡渲染、链接外跳白名单 http/https（:260+/:246-256）；21 处调用点按域选角色（chat 用 chatBubble、胶囊详情 1.65+selectable、知识详情用 knowledgeSummary）。
- **行宽响应式约束已建**：ContentConstraintSystem maxWidth phone ∞/tablet 720/desktop 1200（responsive_system.dart:466-483），chat 屏与知识详情/首页内容卡均已包 ContentConstraint（chat_screen.dart:1462、knowledge_detail_screen.dart:217-371）。
- **排版 SSOT 裁定完成、M3 15 角色全映射**：SparkleTypography 单一真相源（theme_manager.dart:1116-1225，锚定档 46/30/24/19/16/14/14/12 + bodySmall 派生 12/1.52 + M3 派生角色 :1202-1224）；_buildTextTheme 全 15 角色映射进 Material TextTheme（design_system.dart:341-368，batch4 注释自证「Material 组件不再回落第三字阶」）；§3.1.4 字面量棘轮在跑（SPEC 登记存量 1293 → 本轮实测 features 口径 1278，未新增破口）。
- **星图首见仪式受规范保护**：§7.2 已把「onboarding 首见」列为仪式模式三类合法触发之一（「首见惊艳是品牌资产」），TTV 的品牌时刻有条款依托。

### 2.1 面 1 · TTV 路径图（段 × 实测 × 摩擦）

| # | 段 | 触发链证据（@7f5d949b） | 实测/状态 | 摩擦判定 |
|---|---|---|---|---|
| S1 | 首屏→注册 | splash 品牌窗并行认证（routes.dart:170-177 N20）；login 首屏四入口次序：登录→**访客**→三方×3→**注册（ghost，:326-331）** | V13 D-07：注册入口折叠线以下 | **摩擦：注册是首屏最后一项**；访客反而在第二位——产品对「先体验后注册」的真实排序与视觉排序相反 |
| S2 | 注册表单 | 4 文本字段（register_screen.dart:155/:177/:198/:275）+2 同意框（:297/:321） | V13 D-01 错误不随修正消失/D-02 返回丢表单/D-06 必填校验后置+热区位移/D-09 Enter 不跳字段 | **摩擦：6 决策点全前置**，且四条 Minor 实测缺陷均未清偿 |
| S3 | persona 5 步 | 目标/风格/时长滑杆/知识水平/回答偏好（persona_onboarding_screen.dart:129-202，5×Step） | V13 步骤 4 PASS；完成后→访谈 6-8s（V13-RETEST Major-1） | 摩擦中：5 问连续无中途价值预告（「答案换什么」只在访谈兑现）；M-01 29s 静默超时已修（V13-MAJORS） |
| S4 | 建模访谈 | Aurora LLM 多轮 + 75s 看门狗 + 跳过通道（modeling_chat_screen.dart:48-50/:707-758） | V13-RETEST ②通过；访谈→主聊天衔接已修（session 头 ensure） | 摩擦低（可跳过、有看门狗、有胶囊）——**全链修得最好的段** |
| S5 | 首个北极星 prompt→确认 | 发送→≤3s 渲染→AI 出确认卡→confirm→`GET /plans/{id}/today` 出任务（TOUR S2） | V13-RETEST ①通过；TOUR S2 pass | **咽喉确认**：冲刺成立押在用户看懂确认卡并点击；确认卡缺失/忽略=首日零价值（V13 曾因此全程阻塞） |
| S6 | **首个任务完成（第一次真正帮到学习）** | 出任务→execute→complete→celebration（task_execution_screen.dart:1182） | 代码链完整；V13 因 B-01 阻塞未达此步，复测后链路通 | 到达成本：**S1-S6 累计 ~13 个用户决策点**（6 表单+5 persona+1 访谈+1 确认）；首胜光子收入存在（TOUR S7）但新用户旅程无预告 |
| S7 | 首次诊断 | pattern 列表空态=图标+标题+副标题，**无 CTA**（pattern_list_screen.dart:117-157）；胶囊生成入口在设置（unified_settings_screen.dart:2038） | 空态诚实但「死胡同」 | **摩擦：诊断空态不告诉用户如何促成第一次诊断** |
| S8 | 首次记忆被引用 | memory_reference_receipt chip（context_receipt_bar.dart:90） | 链路在 | 达标（承接面已建） |
| G | **访客全程** | guest 跳过 S2/S3/S4（routes.dart:168/:226-230）；转化钩子全库 grep：**0 命中** | —— | **最大缺口：访客没有任何「注册保存进度」时刻**；且访客与注册用户在同一 home 空态汇合，产品无法在价值时刻请求转化 |

**FTUE 分层盘点（各核心面首用空态质量）**：home **优**（目标 chip 直达聊天 prompt）；任务 **良**（EmptyState+CTA）；错题本 **良**（CTA+搜索态分离）；社群 **良**（V13 步骤 16/17：设定承诺/发现伙伴 CTA；D-14 开发口吻文案遗留）；星图 **中**（贡献横幅「开始你的第一次学习」CTA 在位 galaxy_contribution_banner.dart:124，但 V13-RETEST ⑥b 证实 D-10 统计被引导卡遮压/D-11 标签截断/D-12 零上传用户被 OS.pdf 种子弹窗困惑三条**仍在**）；认知诊断 **差**（空态无 CTA 死胡同，:117-157）。

### 2.1b 面 2 · 排版分布矩阵（四通道 × 字号 × 字重 × 行高，全库计数实测）

**通道矩阵**（style 决策点总量 ≈ 3820+3010 个间距字面量）：

| 通道 | 用量 | 解析去向 | 12px 档占比 | 备注 |
|---|---|---|---|---|
| `context.typo.*`（新 SSOT 推荐通道） | 421 | SparkleTypography 直读 | 49%（labelSmall 153+bodySmall 46+labelMedium 8） | labelSmall 是该通道第一大角色 |
| `DS.*` deprecated shim | 760 | 转发 SparkleTypography（design_system.dart:1125-1151） | **68%**（bodySmall 360+labelSmall 156） | 注释自证存量约 740 处暂不迁移；**同名字段漂移实锤：DS.titleMedium→titleLarge（19px，:1140-1141）而 textTheme.titleMedium→16px w500**——同名不同值 |
| `Theme.of(context).textTheme.*` | 1361 | _buildTextTheme 全 15 角色映射（design_system.dart:346-368），与 SSOT 同值 | 43%（bodySmall 413+labelSmall 95+labelMedium 71） | 事实上的第一大通道；titleMedium(198)/titleSmall(138) 是 M3 映射后才可用 |
| 裸 `TextStyle(fontSize: …)` 字面量 | **1278 处 / 253 个文件**（features 口径，占 921 个 feature 文件的 27%） | 不经任何角色 | 峰值即 12（200 处）；**sub-12 共 238 处**（11×122、10×101、9×9、8×6） | §3.1.4 棘轮已冻结（SPEC 登记存量 1293→现 1278），但**冻结≠合规：sub-12 直接击穿 §3.1「caption 12 全 app 最小字号」地板** |

**字号档实际分布**（三 token 通道合计 2542 处，按解析后渲染字号归档）：**12px ≈ 51%**（bodySmall 819 + labelSmall 404 + labelMedium 79）｜14px ≈ 29%（bodyMedium 436+labelLarge 168+titleSmall 139）｜16px ≈ 10%（bodyLarge 60+titleMedium 200）｜19px ≈ 7%（titleLarge 134+DS.titleMedium 39）｜24px ≈ 1.7%（headlineSmall 32 等）｜30px ≈ 0.5%｜46px ≈ 0.3%。**可读正文档（≥16）合计不足两成**——「人人都是 14px」的假设不成立，真实形态是 **12px 主导的中段压缩**。

**字重分布**（features+shared+app 裸 FontWeight）：w800×**127**、w700×81、w600×61、w500×20、w900×6、w400×**2**、w300×1——≥w600 占 92%；w800 超出 §3.1 角色表上限（w700），最重户：knowledge_theater_screen 24 处、simulation_screen 17、learning_report_screen 17。**层级退化成单通道加粗**（对标 §1.2 双编码行）。

**行高分布**（TextStyle 内字面量）：1.4×113、1.5×65、1.6×17、1.3×11、1.2×8、1.1×4、1.0×4——与角色锚定行高（1.10-1.68 九档，theme_manager.dart:1128-1185）脱钩的自由档；SparkleMarkdown 角色化行高（1.45-1.7）是唯一成体系的子系。

**密度节奏**：DS.spacing 全 15 档用量——spacing8×1957、spacing12×1559、spacing16×1221、spacing4×612、spacing10×611、spacing6×550、spacing20×201、spacing24×178、spacing14×62、spacing32×44、spacing2×33、spacing18×29、spacing40×19、spacing64×15、spacing56×2（合计 7113）：**前三档（8/12/16）占 66.6%**；**半格档（2/6/10/14/18，非 4 基栅）合计 1285 处 = 18%**；SparkleSpacing 基四档体系（4/8/16/24/32/48/64，theme_manager.dart:1231-1237）全库仅 138 处消费——**两套间距哲学并存，DS 一套独大且自身带半格**。裸 EdgeInsets 字面量 3010 处（all 1145/symmetric 971/only 634/fromLTRB 259）作对照。

**卡片内外留白一致性**（抽样）：SparkleCard 默认内边距 = context.space.md = 16（sparkle_card.dart:34）；dashboard 区块壳 20/24（dashboard_screen.dart:414/:510）；task_card 10（task_card.dart）、错题列表卡 12（error_list_screen.dart）、feed 卡 16/12+8/4（feed_post_card.dart）——**同屏「卡片家族」内边距 10/12/16 三档并存**，与 §3.3「卡内边距 16dp」单向条款三方脱节（列表卡统一 16 会伤密度，见 TY-G5 辩论）。

**长文体验**：SparkleMarkdown 默认 fontSize 16（:50）、聊天域调用 chatBubble 1.45 行高（private_chat_screen.dart:567-572）、知识详情 knowledgeSummary 1.55+selectable（knowledge_detail_screen.dart:371-377）、胶囊详情 1.65（capsule_detail_screen.dart:167-172）——行高角色化达标；**但 styleSheet 未设 pPadding/h\*Padding（sparkle_markdown.dart:193-258 全无），flutter_markdown 0.6.23 构造缺省 null→零（style_sheet.dart:14）——段距=0，多段 AI 回复/长文段落黏连**；聊天域靠 aurora 分组按空行拆气泡补了段距（aurora_message_group.dart:48-50，组间 spacing6），**知识详情/胶囊详情/任务攻略等一 BLOCK 到底的长文无此补偿**。聊天正文档：气泡内文字 10/11/11.5/12/13 五档字面量混用（chat_bubble.dart），零 token——聊天域是「正文像元数据」的集中区。

**单屏信息层级采样**：dashboard（titleLarge×2+labelSmall 主导，主角-支撑结构成立但 19px 对 12px 的 7px 差靠 w500/w400 弱对比维持）；galaxy 屏字面量六档散布（20/15/14/13/12/11，零角色引用）；chat_bubble 全字面量（上）；对比 §3.1 节奏表的「每屏 1 主角+≤3 支撑」——**主角档（≥24）全库 token 用量仅 2%，实际主角感靠 w800 硬顶**。

### 2.2 差距清单（12 条）

| # | 差距 | 证据（file:line @7f5d949b） | 违反/衔接条款 |
|---|---|---|---|
| TV-G1 | **注册入口沉底+首屏无价值预告**：login 首屏入口次序 登录→访客→三方×3→注册（ghost 末位，login_screen.dart:326-331），首屏文案全部围绕「进入」，无一字回答「进来能得到什么」 | 同列；V13 D-07 实测折叠线以下 | 对标 §1.1 价值先行行；§8 onboarding 蓝图「有温度」精神的首屏前移 |
| TV-G2 | **访客零转化钩子**：guest 跳过全部引导直落 home（routes.dart:168/:226-230），此后全库无任何「注册保存进度」时刻（grep 0 命中）；访客完成价值动作与注册用户 UI 完全同质，产品在最该请求注册的时机失声 | 同列 | 对标 §1.1 aha-before-signup 行——aha 之后的 signup 缺席 |
| TV-G3 | **首日价值密度未成条款**：注册→首个任务完成 ~13 个决策点（S1-S6 累计），决策站分布无规范约束；§8 仅有「onboarding ≤5 步到 home」一条，覆盖不了引导之后到首个价值物的后半程 | §2.1 路径图；TOUR S2 确认咽喉 | §8 蓝图延伸；北极星「期末一周用户没有第二周」 |
| TV-G4 | **首次诊断空态死胡同**：图标+标题+副标题、无任何 CTA（pattern_list_screen.dart:117-157）——不告诉用户「多聊几次/建冲刺后这里会长出什么」 | 同列 | 对标 §1.1 空态即引导员行；公约①的反例 |
| TV-G5 | **星图首用三瑕疵遗留**：D-10 首用引导卡遮压顶部统计、D-11 扇区标签截断、D-12 零上传用户被 OS.pdf 种子弹窗困惑——V13-RETEST 证实三条仍在（V13 已登记，修复归 bug 线） | V13-RETEST ⑥b；galaxy_contribution_banner.dart:124 | V13 缺陷清单既辖；本轮登记防双立项 |
| TV-G6 | **注册表单四 Minor 未清偿**：D-01 错误陈旧态/D-02 返回丢表单/D-06 必填校验后置+热区位移/D-09 Enter 不跳字段（register_screen.dart:155-321） | V13 Minor 清单；A-SPEC5 表单轮覆盖了现场保留但未触及此四条 | V13 既辖；转台账 |
| TY-G1 | **四通道并存且同名字段漂移**：typo 421/DS shim 760/textTheme 1361/字面量 1278；DS.titleMedium 渲染 19px 而 textTheme.titleMedium 渲染 16px（design_system.dart:1140-1141 vs :357-358）——同名不同值是通道分裂的最尖锐证据 | §2.1b 通道矩阵 | §3.1 Owner 已裁定（SparkleTypography）；「唯一通道」未成文，shim 存量未登记基线 |
| TY-G2 | **12px 主导 + sub-12 击穿地板**：12px 占 token 通道 51%（bodySmall 819 处为全库第一大角色）；**sub-12 字面量 238 处**（10/11/9/8px）直接违反 §3.1「caption 12 全 app 最小字号」；chat 气泡正文 10-13px 五档混用（chat_bubble.dart）——「正文像元数据」 | §2.1b 字号矩阵 | §3.1 caption 地板条款；§3.1.3「chat 消息必须 body 档」的执行缺口（待 §3.1 数值迁移批落地时兑现） |
| TY-G3 | **字重通胀 w800×127**：超 §3.1 角色表上限 w700，w400 全库仅 2 处——层级靠加粗单通道硬撑，与 3.1.2「禁加大加粗连排」精神相悖的变体逃逸 | §2.1b 字重分布 | §3.1 角色表；§3.1.2 |
| TY-G4 | **行高自由档**：字面量行高 1.0-1.6 七档散布（1.4×113/1.5×65/…），不经角色锚定；角色锚定行高九档已成（theme_manager.dart:1128-1185）但字面量绕行 | §2.1b 行高分布 | §3.1 角色表「行高」列的执行通道 |
| TY-G5 | **间距半格侵蚀+卡内边距三档**：半格档（2/6/10/14/18）1285 处=18%；卡内边距 10/12/16 三档并存（SparkleCard 16/task_card 10/错题卡 12/feed 12）；SparkleSpacing 基四体系仅 138 处消费——且 §3.3「卡内边距 16dp」对列表卡过重，条款本身需两档化修订 | §2.1b 密度节奏 | §3.3；「栅格语义」 |
| TY-G6 | **长文段距=0**：SparkleMarkdown styleSheet 无 pPadding/h\*Padding（sparkle_markdown.dart:193-258），flutter_markdown 0.6.23 缺省 null→零（style_sheet.dart:14）——多段 AI 回复与知识/胶囊长文段落黏连；聊天域被 aurora 分组补偿（aurora_message_group.dart:48-50），其余长文面裸奔 | 同列 | 对标 §1.2 行高节奏行「段距必须显式」；§3.1.1 行高正典的段距延伸 |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转台账+观察**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| TV-G1 | 注册入口上移+首屏价值预告句 | 蓝方：登录页是转化漏斗成熟形，动布局动全身；「还没账号」ghost 末位是刻意降权 | G1 真差距（V13 D-07 实测+代码次序实锤——但蓝方指出「降权」是意图成立）；G2 改写：**不动布局，先补价值预告**——首屏加一句「备考周提升最有感知」（§6 文案三件套），注册钮上移一位至三方登录前（S）；G3 中-高——首屏是全漏斗口径最便宜的一段 | **改写采纳**（N39 前置条款） |
| TV-G2 | 访客转化钩子：首个价值动作完成后一次「注册保存进度」 | 蓝方：弹注册伤体验；访客态本身是低成本试用的诚意 | G1 真差距（0 钩子实锤——访客侧门是**漏桶**）；蓝方「伤体验」被公约③吸收：只在价值时刻后、只一次、可永久关闭；G2 成本 S-M（一个条件组件+一条深链，guest→register 数据保留是后端既有 guestLogin 逆操作需对齐，风险登记）；G3 高——期末用户试用即决胜负，流失在沉默里 | **采纳**（N40 主条：价值时刻转化点+禁骚扰令） |
| TV-G3 | 立首日价值密度条款：决策站计数红线 | 蓝方：13 个决策点是产品选择（个性化诊断是核心资产），不是债 | G1 半差距（个性化深度是资产成立；「不可数、无约束」才是债）；G2 改写：不砍 persona/注册内容，立**度量与豁免制**——新面 PR 必答「首用空态有无下一步」，注册→首个价值物的决策站总数登记进台账逐季只降；G3 高——北极星战役的 C 线已把 TTFT 压到秒级，用户面的「首日秒针」是同一件事 | **改写采纳**（N39 主条：首日价值密度登记制+空态必答令） |
| TV-G4 | 诊断空态补 CTA | 蓝方：诊断是引擎产物，空态没有可承诺的动作 | G1 真差距（死胡同实锤）；蓝方被反驳：可承诺的动作存在——「和 Aurora 聊一次学习现状」（聊天即诊断输入，S4 建模访谈已证）；G2 成本 S（EmptyState 化+一条 deep link，复用 home 空态模式）；G3 中-高——诊断是「第一次感到 AI 懂我」的时刻，承载差异化 | **采纳**（N39 子句） |
| TV-G5 | 修星图首用三瑕疵 | 蓝方：V13 已登记，双立项浪费 | G1 真差距但**已有归属**（V13 缺陷清单）；G2 重复立项成本为负；G3 依 V13 排期 | **转台账**（N45 登记行，引 V13 D-10/11/12） |
| TV-G6 | 修注册表单四 Minor | 蓝方：同上，V13 已登记且 A-SPEC5 已覆盖表单域 | 同上（D-01/02/06/09 均在 V13 清单）；A-SPEC5 的表单规范（现场保留/三件套文案）未覆盖此四条行为细节 | **转台账**（N45 登记行，引 V13+标记 A-SPEC5 边界） |
| TY-G1 | 立通道归一条：新代码唯一通道，shim/字面量登记只降 | 蓝方：三通道解析同值（除 titleMedium），归一是洁癖 | G1 真差距——蓝方「同值」论被 **DS.titleMedium 19px vs textTheme.titleMedium 16px** 直接击穿：同名不同值不是洁癖是正确性 bug 温床；G2 改写：不动存量（§3.1 迁移批既辖），立「新代码唯一通道=context.typo/textTheme」+ shim 基线 760/sub-floor 238 双登记只降（并入 §3.1.4 棘轮家族）；G3 中 | **改写采纳**（N41 主条） |
| TY-G2 | sub-12 清零令+正文档执行令 | 蓝方：10-11px 是热力图/日历格子微标签，合理；清零会误伤 | G1 真差距（地板条款 §3.1 白纸黑字）；蓝方部分成立：微标签场景（heatmap 格内数字）确有 9-10px 需求——裁决细化为 **sub-12 默认禁、微标签白名单制**（heatmap/calendar 类格内数字豁免登记）；chat 正文档执行令与 §3.1.3（chat 必须 body）对齐，待数值迁移批时 chat 先行；G3 中-高（疲惫用户的可读性） | **改写采纳**（N41 子令：sub-12 禁新增+白名单豁免；N41 子句：chat 域随迁移批先行） |
| TY-G3 | 字重封顶 w700，w800/w900 登记清偿 | 蓝方：展示型屏（theater/report/simulation）就是要重；w800 是设计选择 | G1 真差距（角色表无 w800 档是实锤；但「展示屏要重」部分成立）；G2 改写：**新字重禁 w800+ 硬条款+存量 133 处登记只降**，展示型屏豁免申请制；层级规范补「双编码」正面条款（新样式必须同时声明档位与字重）；G3 中 | **改写采纳**（N42：封顶+登记+双编码正面条款） |
| TY-G4 | 行高必经角色 | 蓝方：字面量行高多数与锚定值接近，清洗收益低 | G1 半差距（散档 1.4/1.5 与锚定 1.52/1.62 数值近——但「近」会随重定标漂移成错）；G2 改写：只立**新代码行高必来自角色或角色.copyWith**，存量随 §3.1.4 字面量棘轮家族顺带（字面量棘轮脚本可扩展 height 维，登记制不专项）；G3 低-中 | **改写采纳**（N43 前半） |
| TY-G5 | 间距归一基四栅格+卡内边距两档制 | 蓝方：半格 1285 处存量清洗是大工程；§3.3 的 16dp 是 v1.0 冻结条款 | G1 真差距（半格侵蚀栅格语义+三档并存实锤——但**§3.3 本身要改**：列表卡 16dp 在 3 行列表实测过松，条款单向是源头问题）；G2 改写：**§3.3 修订为两档（列表卡 12/内容卡 16）+新组件基四档硬条款+半格存量登记不清洗**；G3 中（密度一致性是扫视效率的底座） | **改写采纳**（N43 后半：两档制修订 §3.3+半格登记制） |
| TY-G6 | SparkleMarkdown 补段距令 | 蓝方：段距缺失从未被抱怨；聊天域已补偿 | G1 真差距（pPadding=0 实锤，flutter_markdown 源码双证——「没被抱怨」恰因用户没见过不黏连的长文）；聊天域补偿论恰说明**其他长文面裸奔**；G2 成本 S（一处 styleSheet 加 pPadding/h2+h3Padding≈0.5×行高，附 knowledgeSummary/seedBody 角色验收）；G3 中-高——知识详情是考前最后一晚的高频面 | **采纳**（N44：段距显式令，S 级首案） |

**辩论统计**：12 条 → 采纳 3（TV-G2/TV-G4/TY-G6）+ 改写采纳 5（TV-G1/TV-G3/TY-G1/TY-G2/TY-G3；其中 TY-G4/TY-G5 亦为改写，计入则为 7）——按主条计：**采纳 3 / 改写采纳 5 / 砍 0 / 转台账 2（TV-G5/TV-G6）+ 豁免观察 2（微标签白名单/chatBubble 1.45 豁免，并入条目）**。本轮砍单为 0：因为全部差距在 R2 已被过滤为实测实锤，辩论重心在**改写为登记制/豁免制以避免与 §3.1 数值迁移批、V13 缺陷线重复施工**。

---

## 4. SPEC v1.7 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0-v1.6：编号规则 + 依据 + 可验收数字；不推翻 v1.0/v1.1/v1.2/v1.3/v1.4/v1.5/v1.6 任何条款。编号接续 v1.6 的 N38。生效方式建议沿用 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。

**N39（§7 增补 7.x）· 首日价值密度（决策站登记制+空态必答令）**
- **决策站登记**：注册→首个价值物（首个任务完成）的用户决策链登记为基线（现值 **≈13 站**：表单 6+persona 5+访谈 ≥1+确认 1，persona/访谈内容为产品资产**不裁减**，登记只降不升——后续靠后置/并行压缩，如同意框并入提交时校验反馈、滑杆类问题并入访谈对话）；新增引导类面 PR 必答「本面使决策站 +几」。
- **空态必答令**：一切核心面首用空态必须含「下一步做什么」CTA 且直达价值动作（正解登记：home 首目标空态 dashboard_screen.dart:404-498、EmptyState typed factory 体系）；存量靶（改造 #3）：认知诊断空态（pattern_list_screen.dart:117-157）补 EmptyState 化+「和 Aurora 聊一次学习现状」deep link。
- 【依据：§2.2 TV-G3/TV-G4；§2.1 路径图；对标 §1.1 空态即引导员/首日价值密度行；§8「≤5 步到 home」的后半程延伸】

**N40（§7 增补）· 访客价值保全与唯一转化点（aha 之后的 signup）**
- 访客态保留现有零摩擦进 core（routes.dart:168/:226-230 不动）；**新增唯一正当转化点**：访客完成第一个价值动作（首个任务完成/首次诊断产出/首次记忆被引用任一）的当下，呈现一次「注册保存你的备考进度」卡（一次会话最多一次、可永久关闭，禁全域骚扰式注册弹窗）；guest→注册的数据承接（guestId 对齐，auth_provider.dart:195-206 既有通道）需后端确认保留策略，风险登记。
- 【依据：§2.2 TV-G2；对标 §1.1 aha-before-signup 行；§1.1 公约③】

**N41（§3.1 增补执行令）· 字阶通道归一与字号地板（新代码唯一通道；sub-12 禁新增）**
- **通道归一**：新代码文本样式唯一通道 = `context.typo.*` 或 `Theme.of(context).textTheme.*`（二者经 _buildTextTheme 同值）；`DS.*` 排版 shim（存量 **760** 处冻结只降不升）与裸 `TextStyle(fontSize:)`（§3.1.4 棘轮既辖，features 现值 **1278**）为登记存量，触碰即迁不专项。**同名字段漂移修正靶**：DS.titleMedium（design_system.dart:1140-1141 → 19px）与 textTheme.titleMedium（16px w500）收敛为同值（改造 #1，随 shim 批）。
- **字号地板**：sub-12px（<12）文本 **禁新增**；微标签白名单制（heatmap/日历格内数字等确需 9-10px 的场景逐处登记豁免，存量 **238** 处登记只降，白名单外清零）；chat 域正文档（§3.1.3「chat 消息必须 body」）随 §3.1 数值迁移批**首批执行**，气泡面板元数据与正文角色分离（chat_bubble.dart 现状 10-13px 五档混用为存量靶）。
- 【依据：§2.2 TY-G1/TY-G2；§2.1b 通道矩阵；§3.1 caption 地板与 §3.1.3 既辖】

**N42（§3.1 增补）· 字重封顶与层级双编码（禁 w800+ 逃逸档）**
- 新文本样式字重上限 **w700**（§3.1 角色表既定档位）；`FontWeight.w800/w900` **禁新增**，存量 **133** 处（w800×127+w900×6）登记只降不升，展示型屏（theater/simulation/report 类）豁免需单条申请登记。
- **层级双编码正面条款**：新建层级必须同时声明字阶档位与字重（及 textPrimary/textSecondary 颜色档），**禁仅靠加粗制造层级**（3.1.2「禁加大加粗连排」的执行细则）。
- 【依据：§2.2 TY-G3；§2.1b 字重分布（w800×127/w400×2）；§3.1.2】

**N43（§3.1/§3.3 增补）· 行高锚定与卡内边距两档制（§3.3 修订）**
- **行高锚定**：新代码行高必须来自角色定义或 `角色.copyWith(height:)`；裸 `height:` 字面量禁新增（存量七档散布随 §3.1.4 棘轮家族扩展 height 维登记，不专项清洗）；SparkleMarkdown 内容角色行高（1.45-1.7）登记为合法子系。
- **§3.3 修订（两段门禁）**：卡内边距由单向「16dp」修订为两档——**列表卡 12dp / 内容卡 16dp**（v1.0 冻结值的条款内修订，依据本轮实测三档并存 10/12/16 与列表密度需要）；**新组件间距必须取 4 基栅格档**（4/8/12/16/20/24/32/40/48/64）；半格档（2/6/10/14/18，存量 **1285** 处=18%）登记只降不升；同屏卡片家族必须同档（审查口径，登记制）。
- 【依据：§2.2 TY-G4/TY-G5；§2.1b 密度节奏与卡片家族抽样；§3.3 原条款】

**N44（§3 增补）· 长文段距显式令（段距是节奏的一半）**
- SparkleMarkdown styleSheet 必须显式设定段距：`pPadding ≈ 0.5×角色行高对应值`、`h2/h3Padding 上下 ≈ 0.75×/0.5×`（改造 #2，sparkle_markdown.dart:193-258 一处修复，knowledgeSummary/seedBody/taskGuide 三角色受益验收）；聊天域 aurora 分组补偿（aurora_message_group.dart:48-50）保持不变（气泡间 spacing6 即聊天段距，豁免本条）。
- 行高豁免登记：chatBubble 1.45 相对 §3.1 body 1.6 正典为聊天气泡密集场景的合理取舍，登记豁免观察行（若 §3.1 迁移批重定标，随批复核）。
- 【依据：§2.2 TY-G6；sparkle_markdown.dart:193-258 + flutter_markdown-0.6.23 style_sheet.dart:14 双证；对标 §1.2 行高节奏行】

**N45（§10.5 台账新增行，随 v1.7 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N39 首日价值密度（决策站基线 ≈13 登记） | 未开工（登记即生效） | 改造 #3 |
| N40 访客唯一转化点 | 未开工（后端 guest 数据承接待确认） | 改造 #4 |
| N41 通道归一+sub-12 禁新增（shim 760/字面量 1278/sub-12 238 三基线冻结） | 未开工（登记即生效） | 改造 #1/#5 |
| N42 字重封顶 w700（w800/900 存量 133 登记） | 未开工（登记即生效） | 随触碰批 |
| N43 行高锚定+卡内边距两档制（半格 1285 登记） | 未开工（含 §3.3 条款修订） | 随触碰批 |
| N44 长文段距显式令 | 未开工 | 改造 #2 |
| TV-G5 星图首用三瑕疵（D-10/D-11/D-12） | 台账登记（V13 缺陷线既辖，防双立项） | —— |
| TV-G6 注册表单四 Minor（D-01/02/06/09） | 台账登记（V13 既辖；A-SPEC5 表单轮边界外） | —— |
| chatBubble 1.45 行高豁免 | 观察行（§3.1 迁移批时复核） | —— |
| 微标签 sub-12 白名单（heatmap/日历格内数字） | 登记制（逐处豁免，白名单外禁新增） | —— |

---

## 5. 改造清单（按北极星收益排序 top8，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。与前轮清单关系：本表为两新面的 v7 批次，前轮未清偿项不受影响。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **DS.titleMedium 同名漂移收敛（N41 首案）** | design_system.dart:1140-1141 shim 转发目标改为 M3 titleMedium（16/w500）或登记 39 处调用点按 19px 显式化 | 同名同值，消灭静默漂移 | widget test：DS.titleMedium 与 textTheme.titleMedium fontSize 断言相等；grep 39 处调用点视觉回归 | S |
| 2 | **长文段距（N44 首案）** | sparkle_markdown.dart:193-258 styleSheet 补 pPadding/h2+h3Padding（按角色行高比例）；golden 快照更新 | 知识详情/胶囊详情多段内容段落分明 | golden：多段 markdown 段距可见断言；chat 域回归不受影响 | S |
| 3 | **诊断空态 CTA+首用空态审查（N39）** | pattern_list_screen.dart:117-157 改 EmptyState+「和 Aurora 聊一次学习现状」deep link（prompt 预填，照 home 首目标空态模式 :438-473） | 诊断空态有下一步且直达 | widget test：空态渲染 CTA+点击落聊天路由断言；四核心面空态 CTA 存在性测试 | S |
| 4 | **访客唯一转化点（N40）** | 价值动作完成回调处（task_completion_celebration/pattern 首产出）挂一次性「注册保存进度」卡（guest 判定走 registrationSource）；永久关闭偏好入本地 | 访客在价值时刻被邀请注册且仅一次 | widget test：访客完成首任务→卡可见；关闭后不再现；注册用户不可见 | S-M |
| 5 | **sub-12 清零首批+白名单（N41）** | 238 处中非白名单高频户先行（chat_bubble 面板字/status_awareness_bar/agent_workflow_panel——各 11-12 处）；heatmap/calendar 格内数字入白名单登记 | 非 micro 场景 sub-12 清零 | 守卫脚本：sub-12 计数基线 238 只降；白名单文件清单入库 | S-M |
| 6 | **login 首屏价值预告+注册位次（N39 前置）** | login_screen.dart:283-331：分隔区上方加一句价值预告（§6 三件套文案，l10n 化）；注册 ghost 上移至三方登录行之前 | 首屏回答「进来能得到什么」 | 手测折叠线：注册入口可见性；l10n 断言 | S |
| 7 | **w800 首批降档（N42）** | knowledge_theater_screen（24 处）/simulation_screen（17）/learning_report_screen（17）三展示屏申请豁免或降 w700；非展示屏存量随触碰降 | 新 w800=0，存量 133 只降 | 守卫计数登记；三屏视觉走查 | S |
| 8 | **§3.3 两档制落地首验（N43）** | task_card.dart（10→12）/error_list 列表卡（12 保持）/SparkleCard 默认（16 保持内容卡档）；同屏家族对齐 | 列表卡 12/内容卡 16 两档成立 | 布局走查+golden（列表密度不降）；§3.3 文本修订随 v1.7 合入 | S |

**被砍项备忘**（防后续卡重复立项）：本轮无砍单；两个**观察/豁免行**防重复立项——chatBubble 1.45 行高豁免（随 §3.1 迁移批复核）；heatmap/日历微标签 sub-12 白名单（逐处豁免而非清零）。另：**persona 5 步/注册字段内容不裁减**（TV-G3 辩论定论：个性化深度是产品资产，压缩靠后置与并行，不靠删问）；**galaxy 三瑕疵与注册表单四 Minor 不在本线施工**（V13 缺陷线既辖，N45 已登记防双立项）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC7/REPORT.md`（本文件，位于 worktree wt262）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作；未 commit / 未 push
- [x] /tmp 无驻留（全程未写 /tmp）；无启动进程/模拟器/浏览器，无 HEAVY 资源占用；worktree 内无 build/.dart_tool 产生
- [x] 引用代码均为 @7f5d949b 实测（rg/read/perl 邻近计数）；计数类结论（typo.* 421＝labelSmall 153+labelLarge 87+bodyMedium 72+bodySmall 46+其余 63、DS shim 760＝bodySmall 360+labelSmall 156+bodyMedium 123+titleMedium 39+titleLarge 36+labelLarge 24+bodyLarge 18+headingLarge 3+displayLarge 1、textTheme 1361、fontSize 字面量 features 1278 处/253 文件及分档直方图、sub-12 238＝11×122+10×101+9×9+8×6、FontWeight w800×127/w900×6/w400×2、行高字面量 1.4×113/1.5×65/1.6×17/1.3×11/1.2×8/1.1×4/1.0×4、DS.spacing 15 档全量 7113＝8×1957+12×1559+16×1221+4×612+10×611+6×550+20×201+24×178+14×62+32×44+2×33+18×29+40×19+64×15+56×2、半格 1285、EdgeInsets 3010、SparkleSpacing 138、persona 5×Step、SparkleMarkdown 21 调用点、访客转化钩子 0 命中）均为 grep/perl 实测；关键文件（design_system、theme_manager、sparkle_card、responsive_system、sparkle_markdown、routes、login/register、persona_onboarding、modeling_chat、dashboard_screen、task_list、error_list、pattern_list、task_completion_celebration、galaxy_contribution_banner、context_receipt_bar 节选）为文件实读；flutter_markdown-0.6.23 pPadding 缺省读 pub-cache 包源实测（只读）；无编造引用
- [x] V13/V13-RETEST/TOUR 实测数据均引自对应 REPORT.md 原文（V13-RETEST ③ 6-8s、① ≤3s、② 75s 看门狗通过、⑥b D-10/11/12 仍在；TOUR S2/S7）——V13-RETEST 数据产生于基线 0886aaff，本轮在 @7f5d949b 树内核实了对应修复代码在位（modeling_chat_screen.dart:48-50 看门狗等）
- [x] 对标研究未做外部浏览（web_search 实测 429「Limit Exhausted reset 2026-09-24」），方法声明已按前六轮先例如实标注
