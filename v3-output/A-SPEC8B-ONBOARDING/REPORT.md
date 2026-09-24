# A-SPEC8B · 新手首启路径与首次价值时刻对标研究（对标本 + 全程自审 + 辩论 + 条款/改造提案）

> 卡：wt272-res-onboard（A 线·第八轮研究 B 面）｜ 2026-09-22 ｜ worktree **wt272-res-onboard**（分支同名，base **b9a7da3d**）
> 性质：**纯研究卡（LIGHT），零产品代码改动**。所有代码引用为只读走查（rg/read/sed），file:line 均为 @b9a7da3d 实测。
> 研究面定义（按卡）：从安装到第一次感受到价值的全程——首屏、注册/游客分流、引导模式（渐进式 vs 前置式）、空态即教学、首次 AI 对话时刻、个性化冷启动（画像从零到可用）。北极星场景 = 期末一周备考。
> 前置读透：`v3/FLEET-BRIEF.md`（战役上下文）+ `v3-output/A-SPEC7/REPORT.md`（第七轮范本与本轮直接前置——本卡基线已含其 N39/N40 落地批，见 §2.0）+ `v3-output/V13/REPORT.md` 与 `v3-output/V13-RETEST/REPORT.md`（新用户首飞实测：6-8s / ≤3s / D-07 等）。
> 对标方法声明（诚实分级）：本会话 web_search 实测 429「Weekly/Monthly Limit Exhausted，reset 2026-09-24 16:02」（与 A-SPEC7 同况）；本轮升级做法 = 改用 WebFetch 直接抓取权威 URL，**实抓成功 4 源**（NN/g mobile-app-onboarding 全文、growth.design Headspace 拆解、growth.design Too Good To Go 拆解、lichess.org/about），引文来自抓取正文；**未抓到正文 4 源**（Apple HIG Onboarding/Launching 与 material.io onboarding 均 JS 渲染只回导航壳、NN/g /articles/mobile-onboarding 与 /progressive-onboarding 404、growth.design 无 Duolingo onboarding 案、blog.duolingo.com 无 onboarding 专文）——此部分按公开常识 + UX 专业判断引用并逐条标注【常识】，沿用 A-SPEC-V1_1~A-SPEC7 七轮卡内授权先例。代码引用无此事，全部树内实测。
> 与 A-SPEC7 的关系：不推翻其任何结论；本轮在其后新基线上 (a) 验证 N39/N40 已落地（commit e08feee3「feat(ttv): GUEST-HOOK」），(b) 把镜头从「注册→首任务」前移到「安装→首次 AI 回复」，(c) 对标面升级为带来源的 8 标杆。

---

## 0. 方法与多轮过程记录

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 对标研究 | 8 标杆逐一定位可量化口径（首价值时刻步数/时间、注册墙时机、引导完成率、跳过行为）；实抓 4 源 + 常识 4 源 | §1 对标 top8 表（含来源分级） | 权威口径罕见地一致：**NN/g 头条建议就是「Skip Onboarding Whenever Possible」**（实抓原文）；Headspace 反例被 growth.design 判为「注册表单前置 + 见 app 前付费墙 → 审查者当场流失」；TGTG 反例「aha 晚到第 ~6 屏」。共性=**注册墙押后到价值完成时刻、跳过一等公民、每问附回报** |
| R2 自审 | a) 启动链路由走查（main→splash→redirect 链）；b) guest 全链 grep（30 文件）+ 转化触点实读；c) 首聊前置依赖（chat 空态/发送链/persona-modeling 强制链）；d) 主要面空态逐屏实读；e) 画像冷启动三件套（persona 预览/建模访谈/聊天 daily startup）；并核对 A-SPEC7 的 N39/N40 在新基线的落地状态（git log 定位 e08feee3） | §2 达标清单 + 步数拆解表（每步 file:line）+ 差距 7 条 | 两条结构性结论见 §2 开头。最大变化：**A-SPEC7 时代「访客零转化钩子」已不成立**——N40 唯一转化点全套落地；最大遗留：**价值信号只接线 1/3**，且注册线「引导未完成=全域硬重定向」仍是骨架级前置摩擦 |
| R3 辩论 | 7 条差距逐条过三关（真差距？收益/成本/风险？北极星加权？） | §3 辩论记录：采纳 3 / 改写采纳 3 / 转台账 1 | 主导裁决理由：本卡差距多数是「最后一公里」级（一处接线/一句文案/一个状态持久化），S 级成本即可收割已建成的骨架 |
| R4 成文 | 过关差距 → 条款提案 N46-N50（候选编号，接续 v1.7 的 N45）+ 改造卡面 top6 | §4 / §5 | 度量方式全部落到可测数字（步数/秒数/接线数） |

**结构性结论先行（两条）**：
1. **「安装→首次 AI 回复」的骨架已是双轨达标，但快轨没有差异化**。游客线实测代码路径 **3-4 次点击、约 5-6 秒可收到首条 AI 回复**（splash 250ms 品牌窗非闸门 + 访客 ghost 钮 + chat tab + starter chip，TTFT ≤3s 为 V13-RETEST 实测）——步数已进入 Duolingo「60 秒进核心循环」量级；**但访客跳过全部画像引导（settings_provider.dart:984-993 自动置 completed），首聊上下文为空**，首条回复质量趋近通用 LLM，「比裸用 GPT 好」的差异化恰恰在最需要证明的第一分钟不可感知。
2. **注册线是「个性化资产」与「前置摩擦」的复合体，逃生门全在但都不显眼**。完整引导链（表单 7 项输入 + persona 5 步 + 建模访谈 ≥1 轮 ≈13-15 决策点）与 A-SPEC7 基线持平；双层 skip 已存在（persona :70-73 / modeling :140-145），完成访谈后聊天里**自动带着 Aurora 首条开场白落地**（modeling_chat_screen.dart:763-773）——首条 AI 内容比 A-SPEC7 时点更早出现；但 skip 均为次级视觉档（ghost/text），且 persona 中途退出无进度持久化（:32 `_currentStep` 纯本地 state），引导未完成时全域硬重定向回 persona（routes.dart:217-224）。

---

## 1. 对标研究表（R1，8 标杆，来源分级标注）

| # | 标杆 | 关键机制 | 可量化口径 | 来源（分级） | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 1 | **NN/g · Mobile App Onboarding** | 三组件框架：feature promotion（勿在首启做营销）/ customization（收集必答「为何要这数据」）/ instructions（交互化「practice round」优于卡片教程）；头条结论「Skip Onboarding Whenever Possible」 | 教程类引导「didn't improve task performance」；推广式引导「will likely be skipped」（连跳过本身也是交互成本） | 【实抓】nngroup.com/articles/mobile-app-onboarding/ | Sparkle 的 persona+建模属正当 customization（确需信息才能个性化），但 NN/g 的「必答为何要数据」只被预览卡半兑现（§G4）；feature promotion 式引导 Sparkle 首启没有——达标 |
| 2 | **Apple HIG · Onboarding / Launching** | Launch fast「begin using your app immediately」；「Defer as much as possible… Get people to the heart of your app immediately」；sign-in only when essential；权限在上下文中请求 | splash 应「merely gives the impression that your app is fast」，禁广告/品牌秀 | 【常识：官方指南，本轮 JS 渲染未能实抓正文，按公开常识引用】 | Sparkle splash 品牌窗 250ms+落地 220ms≤600ms 且认证并行（cold_start_motion.dart:23）= 高分答卷；「setup 押后」未达标（见 G1） |
| 3 | **Duolingo · 前 60 秒** | 选语言→目标 1 问→**直接进第一课**（先玩再注册）；账号创建押后到「保存进度」时刻；进度条+激励声效的首个会话 2-5 分钟必有产出 | 首个会话 60 秒量级内进核心循环；注册墙在第 1 课结束后的保存时刻 | 【常识：公开公案，growth.design 无此案、blog 无专文，按常识引用】 | Sparkle 游客线 3-4 taps 达标「步数」，但「首分钟必有差异化产出」不达标（G4）；「保存进度」转化时刻已被 N40 补上（§2.0） |
| 4 | **growth.design × Headspace（反例）** | 注册表单前置在个性化之前；splash 即有 signup 钮；**见 app 之前弹付费墙**；通知权限在拿到价值前请求——审查者当场流失 | 拆解结论：early paywall 或抬短期转化但伤长期价值；reciprocity（先给价值再索要）为纲 | 【实抓】growth.design/case-studies/headspace-user-onboarding | Sparkle 免费闭环+光子边界（FLEET-BRIEF 红线 3）天然规避付费墙反例；教训映射到注册线：**表单 7 项全前置 = 同型摩擦**（G1） |
| 5 | **growth.design × Too Good To Go（反例）** | aha 过晚：~6 屏介绍后才在「订一个袋子」时懂价值；开方：**How→Why（先讲为什么值）/ Tell→Show（演示代替描述）/ Ask→Offer（请求捆绑利益）** | aha 出现在第 ~6 屏=太晚；三条修法直接可引用 | 【实抓】growth.design/case-studies/too-good-to-go-onboarding | Sparkle 首屏价值预告是抽象口号「点燃你的学习潜能」（G3）=「How 而非 Why」同病；「Ask→Offer」适用于通知/权限类请求 |
| 6 | **Chess.com / Lichess · 先玩后注册** | Lichess：免费开源、无广告、不注册即可对弈（about 页实抓：free/libre、100% free、无广告无数据买卖——注册可选）；Chess.com 移动端先与 bot 对弈、局末以「保存战绩」请注册 | 注册墙=首局结束后；价值动作（一盘棋）先于账号 | 【半实抓】lichess.org/about（实抓）+ Chess.com 行为【常识/推断】 | 「先玩一个 demo 级动作」的正确形态 Sparkle 已有（home 首目标空态 5 chips 直达聊天 prompt，dashboard_screen.dart:404-497）；缺的是访客首聊的「bot 对局级」托底质量（G4） |
| 7 | **Notion / Linear · 渐进 onboarding** | 打开即得模板化首文档（内容即引导，零配置起步）；深度配置后置到使用场景中渐进披露 | 首个可用产物在第一屏；注册/深度设置不挡内容 | 【常识】 | Sparkle 的「空态即教学」体系（EmptyState typed factory + 首目标空态）同构达标；差距集中在引导链本身的前置程度（G1）与进度可恢复性（G7） |
| 8 | **Google（Android/Play）· 登录摩擦** | 签到提供一键（Google 账号）、内容先行、登录应在能兑现价值时出现 | —— | 【常识：官方指南页本轮 404/JS 壳未能实抓，按公开常识引用】 | Sparkle 三方登录（Google/Apple/WeChat，login_screen.dart:299-324）已建；但三方按钮在「或」分隔线之下、注册 ghost 沉底（V13 D-07 折叠线下）——工具在、次序欠 |

**面性公约提炼（本轮新增 4 条）**：
①**注册墙押后令**（aha-before-signup 的执行版：账号请求只出现在价值完成时刻，表单输入能并行/后置的必须并行/后置）；
②**跳过一等公民令**（一切引导面必须有主视觉级 skip；NN/g「连跳过也是交互成本」的反面=「找不到 skip 是双重成本」）；
③**收集换承诺全程兑现令**（对标行 1+6：个性化问题在其存在期间必须持续可见回报，不能只在第 1 步给）；
④**首分钟差异化产出令**（首条 AI 回复必须可感知地「比裸 LLM 懂我」，否则首分钟=竞品裸聊的 worst case）。

---

## 2. 自审（R2，全部 @b9a7da3d 实测）

### 2.0 先说达标项（诚实记录——本基线相对 A-SPEC7 有两笔大额进账）

- **【进账一】A-SPEC7 N40（访客唯一转化点）全套落地**（commit e08feee3「feat(ttv): GUEST-HOOK」）：会话态+持久层+守门派生四条（仅访客/已有价值信号/未被点掉/无进行中任务，guest_conversion_provider.dart:129-143）；价值回顾形内联卡非弹窗（guest_conversion_card.dart:21-100，文案「你的备考进度已保存在本机→注册并同步进度/暂不」，app_zh.arb:2110-2113）；唯一挂载点 home（dashboard_screen.dart:1131）；同会话最多一次+点掉挂起到下个价值信号（guest_conversion_service.dart:72-75）；访客升级独立面 GuestUpgradeScreen（guest_upgrade_screen.dart：邮箱 4 字段 :201/:219/:239/:258 + 三方社交 :364/:376/:389）+ profile 内 guest-only 入口（profile_screen.dart:636-646）+ 路由 /profile/upgrade-guest（user_routes.dart:54/:291-302）。
- **【进账二】A-SPEC7 N39（诊断空态 CTA）落地**：pattern_list_screen.dart:116-176——「图标+标题+副标题」死胡同已补「开始首次诊断」primary CTA，deep link `/chat?prompt=<预填诊断 prompt>`（:163-172），照 home 首目标空态模式。
- **splash 非闸门、认证并行**：品牌窗 250ms（AnimationSystem.normal）+落地转场 220ms=470ms≤600ms 预算，测试守卫钉死（cold_start_motion.dart:23/:29-35/:46-52）；splash 动画本体 400ms 被落地段交叠截断（splash_screen.dart:27-37）；reduce-motion 零等待（cold_start_motion.dart:60-63）。
- **guest 通道顺畅**：login 首屏第二位 ghost 钮「以访客身份继续」（login_screen.dart:274-281；app_zh.arb:107）→ guestLogin 设备唯一 ID（auth_provider.dart:346-361 + guest_service.dart:25-39）→ 跳过全部引导直落 home（routes.dart:168/:226-230）；guest 自动 onboardingCompleted=true（settings_provider.dart:984-993）。
- **首用空态即教学体系完整且全带 CTA**：home 首目标空态 5 个目标 chip 每个 deep-link 进聊天并预填 prompt +「和 AI 开始/快速创建/打开任务列表」三 CTA（dashboard_screen.dart:404-497）+ onboarding welcome 三卡（:500-546）；任务列表（task_list_screen.dart:370-384）、冲刺任务（sprint_screen.dart:191-200，「为何空+影响+单一 CTA」）、错题本含「搜过零命中 vs 空库」分离（error_list_screen.dart:484-505）、种子库（seed_library_list_screen.dart:281）、文档库（document_library_screen.dart:212/:1866）。
- **persona 引导有两处亮点**：①实时 AI 预览卡「AI 已开始理解你的目标」（persona_onboarding_screen.dart:151/:308-343/:345-403；app_zh.arb:12836）——填表即时换承诺， NN/g「为何要数据」的正面解；②appbar「跳过」（:70-73/:279-288）。
- **建模访谈是全链修得最好的段**：自动开场（initState `_onboarding_start_`，modeling_chat_screen.dart:98-108）、首事件看门狗 45s（:46）+中段看门狗 75s（:52）、阶段胶囊、appbar 跳过（:140-145）、完成自动触发规划（:812-858）；**完成即携 Aurora 首条开场白落 /chat**（_finish :763-773，post_onboarding_message→initial_ai_message）——首条 AI 内容零输入出现。
- **主聊天无前置门槛**：chat 空态=快捷建议页（inQuickActionsState，chat_screen.dart:1213-1215）+5 模式×3 prompt starters（:3223-3260）；发送链无科目/画像硬校验（chat_provider.sendMessage 直达）；V13-RETEST 实测发送→AI 回复渲染 ≤3s、引导完成→访谈就绪 6-8s。
- **注册表单较 V13 有改进**：密码强度实时条（register_screen.dart:68-78/:244-281）。

### 2.1 首启步数实测拆解（安装→首次 AI 回复，每步 file:line）

**线路 A · 游客快线（aha-first，产品已有的最低摩擦路径）**

| 步 | 动作 | 证据（@b9a7da3d） | 累计 taps |
|---|---|---|---|
| 0 | 启动→splash 品牌窗 250ms 自动放行→未认证 redirect /login | routes.dart:115/:175-177/:194-202；cold_start_motion.dart:32 | 0 |
| 1 | tap「以访客身份继续」（ghost，首屏第二位） | login_screen.dart:274-281 | 1 |
| 2 | guestLogin 自动完成→redirect /home | auth_provider.dart:346-361；routes.dart:205-211 | 1 |
| 3 | tap 底部 chat tab（或 home 空态任一目标 chip 直达聊天并预填 prompt） | routes.dart:288-370；dashboard_screen.dart:428-473 | 2 |
| 4 | tap 任一 prompt starter chip（或键盘输入后 tap 发送） | chat_screen.dart:1213-1215/:3223-3260 | 3 |
| 5 | AI 回复渲染（TTFT ≤3s，V13-RETEST ① 实测；C 线口径 TTFT 1-2s） | V13-RETEST REPORT:17 | **3（有预填）/4（自由输入）** |

**结论 A：游客线 3-4 taps、全程约 5-6 秒（不含打字）收到首条 AI 回复。**

**线路 B1 · 注册线最小路径（连环跳过）**

| 步 | 动作 | 证据 | 累计 |
|---|---|---|---|
| 1 | tap「还没有账号？」（ghost，首屏末位，V13 D-07 折叠线下） | login_screen.dart:326-331 | 1 tap |
| 2 | 填 username/email/password/confirm 4 字段 + 勾 TOS/隐私 2 框 | register_screen.dart:157-303/:307-344 | 7 项输入 |
| 3 | tap「注册」→ 自动登录 → redirect persona（非 guest 且 completed==false） | register_screen.dart:356-363；routes.dart:217-224 | 2 taps |
| 4 | tap appbar「跳过」→ 直达建模访谈 | persona_onboarding_screen.dart:70-73/:279-288 | 3 taps |
| 5 | 访谈自动开场（0 输入）；tap「跳过」→ setCompleted(true) → /chat **携 Aurora 首条开场白** | modeling_chat_screen.dart:98-108/:140-145/:708-761/:763-773 | **4 taps+7 输入即见首条 AI 内容** |
| 6 | （若口径=用户主动发出后的回复）tap starter/输入+发送 → ≤3s 回复 | chat_screen.dart:3223-3260 | 5-6 taps |

**线路 B2 · 注册线完整引导（个性化全收）**：B1 第 4 步改为 persona 5 步逐页（4×下一步+5 组选择/滑杆，persona_onboarding_screen.dart:129-238）+ 完成提交（:405-439）+ 访谈 ≥1 轮真实回复——**≈13-15 个决策点**（对齐 A-SPEC7 ≈13 基线：表单 6+persona 5+访谈 1+确认 1），换 complete 画像与建模输出注入后续聊天。

### 2.2 差距清单（按痛感降序，7 条）

| # | 差距 | 痛感 | 证据（file:line @b9a7da3d） | 违反/衔接 |
|---|---|---|---|---|
| G1 | **注册墙前置 + 引导未完成=全域硬重定向**：非 guest 在 onboardingCompleted==false 时访问任何路由都被弹回 persona（跳过逃生门存在但为 ghost/text 次级视觉）；注册表单 7 项输入全前置在一切价值之前 | 高（期末用户注册当晚时间最贵） | routes.dart:217-224；register_screen.dart:157-344；skip：persona_onboarding_screen.dart:70-73、modeling_chat_screen.dart:140-145 | 对标 §1 行 2/4（Apple defer setup；Headspace 反例）；公约①② |
| G2 | **价值信号接线 1/3，转化时刻覆盖率低**：N40 钩子只认「首个任务完成」（已接线）；「首次诊断产出」「首次记忆被引用」是预留常量未接线——访客完成这两类价值动作的当下产品仍失声；且转化卡仅挂 home，访客停留在 chat 时不可见 | 高（转化点=增长命脉，建成的系统只用了 1/3） | guest_conversion_service.dart:16-24（firstDiagnosisOutput/firstMemoryReferenced 标注「预留常量」）；唯一接线 task_execution_screen.dart:291-299；挂载唯一点 dashboard_screen.dart:1131 | §2.0 进账一的下半句；A-SPEC7 N40 主条的完整意图 |
| G3 | **首启价值预告抽象化**：login 副标题「点燃你的学习潜能」、splash 副标题「从第一秒开始，进入更聪明也更有温度的学习旅程」均无北极星场景词（期末/备考/提分）——首屏未回答「进来能得到什么」 | 中-高（首屏是全漏斗最便宜的一段） | app_zh.arb:103（welcomeSubtitle）、:8537（splashSubtitle）；login_screen.dart:192-196、splash_screen.dart:122-130 | 对标 §1 行 5（TGTG How→Why）；A-SPEC7 TV-G1 的后半句在本基线仍未解 |
| G4 | **访客首聊=零画像冷启动，首分钟差异化不可感知**：guest 自动 completed 跳过 persona+建模（无画像上下文注入），首条回复质量趋近通用 LLM；连带：persona 预览卡只在第 1 步渲染（后续 4 步调整时 _loadPreview 照跑但卡片不在场，「收集换承诺」只在第 1 步兑现） | 高（北极星=比裸 GPT 好；第一分钟正是决胜时刻） | settings_provider.dart:984-993；预览卡仅 step0 content：persona_onboarding_screen.dart:151；首聊注入缺口的链路实测未做，标注**推断** | 公约④；对标 §1 行 3/6（Duolingo 首课必有产出 / bot 对局托底） |
| G5 | **modeling 屏回退可能触发「弹回 persona 环」**：RouteResilienceScope fallback=home（:131-132），但未完成引导者到 home 又被 redirect 回 persona——从 modeling 返回的用户可能被送回引导起点而非上一层 | 中（边缘路径，未实测，标注推断） | modeling_chat_screen.dart:131-132 × routes.dart:217-224 | 引导链状态机缺口 |
| G6 | **星图首见仪式三瑕疵遗留**：D-10 首用引导卡遮压统计、D-11 扇区标签截断、D-12 零上传用户被 OS.pdf 弹窗困惑——V13-RETEST ⑥b 证实仍在（「首见惊艳是品牌资产」的第 2-5 秒在打折） | 中 | V13-RETEST REPORT:23/:81；galaxy_contribution_banner.dart:7-26 | V13 缺陷线既辖；本轮登记防双立项 |
| G7 | **persona 引导进度不可恢复**：_currentStep 为纯本地 state，中途退出/杀进程后重进从第 0 步重填（已填内容全丢）；对 13-15 决策点的长链是复利性摩擦 | 中 | persona_onboarding_screen.dart:32（`int _currentStep = 0` 无持久化；对照：onboarding 完成态有 per-user 持久化 settings_provider.dart:957-1004） | 对标 §1 行 7（渐进式=可中断可续） |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考）加权值不值？** 红方=主张改造；蓝方=主张维持/砍。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| G1 | 注册线改「先体验后注册」：允许跳过表单直接进访客式体验，注册押后到首个价值时刻 | 蓝方：注册线选择个性化是产品资产（A-SPEC7 TV-G3 已裁定 persona 内容不裁减）；双层 skip 已是合理折中 | G1 半差距（资产论成立，但「7 项输入全前置+skip 次级视觉」是摩擦实锤）；G2 改写：不动表单内容与 redirect 骨架，立**双线 SLA 度量**（快线 ≤4 taps / 注册线 skip 链 ≤5 taps，登记只降）+ skip 可见性升级；G3 高——秒针级口径与 C 线 TTFT 同事 | **改写采纳**（N46 双线 SLA+决策站登记；N50 skip 可见性子令） |
| G2 | 把 firstDiagnosisOutput/firstMemoryReferenced 两条预留信号接线，转化卡增挂 chat 落点 | 蓝方：接线点（pattern 首产出/receipt 首渲染回调）在引擎侧时序里不易抓；挂 chat 可能打断对话 | G1 真差距（预留常量既写即欠）；蓝方部分成立——挂载纪律已有先例（provider 派生可见性四条守门，「永不打断进行中任务」）；G2 成本 S-M（两个回调收口+一个挂载点，守门全复用）；G3 高——诊断与记忆恰是「AI 懂我」差异化时刻，转化话术最强 | **采纳**（N47：信号接线令——预留常量必须限期接线或删除，禁长期悬空） |
| G3 | login/splash 副标题换北极星场景句（如「期末一周，把分拿回来」），l10n 化 | 蓝方：品牌口号是既定资产；两句文案动不动无所谓 | G1 真差距（抽象口号实锤）但收益依赖文案质量，存在主观性；G2 成本 S（两词条+l10n 注册）；G3 中-高——首屏是漏斗口径最便宜的一段 | **采纳**（N48：具象令——首启副标题必须含可感场景，候选文案 A/B 后定稿） |
| G4 | 访客首聊注入轻量上下文（设备 locale+「访客首聊」标记）+ Aurora 首条主动破冰问句（替代被跳过的 persona）；预览卡改为 persona 全程可见 | 蓝方：访客就是要零摩擦，加任何前置问询都违 aha-first；首聊质量是后端问题不归前端 | G1 真差距（差异化在最宝贵的第一分钟不可感知——北极星直接命中）；蓝方后半句不成立（破冰句与预览卡都是前端改动）；改写：**零问询方案**——不问任何问题，只注入隐式上下文+首条 AI 破冰问句（把 persona 第一问搬进聊天里问，答案顺流入画像）= 对标行 6「bot 对局托底」的聊天版；G2 成本 M（需引擎 extraContext 配合，跨层卡）；G3 高 | **改写采纳**（N49：访客首聊破冰令——零问询、隐式上下文、AI 先开口；预览卡全程可见子令并入） |
| G5 | 修 modeling 回退环 | 蓝方：边缘路径，用户几乎不会走 | G1 待实测（本轮只静态推断，未首飞验证）；G2 修法存疑（fallback 指向 home 是 resilience 本意，改指向可能引入新环）；G3 低 | **转台账**（登记待 V 系列下轮首飞实测后再裁） |
| G6 | 修星图三瑕疵 | 蓝方：V13 已登记，双立项浪费 | 同 A-SPEC7 TV-G5 裁决：已有归属 | **转台账**（N45 家族登记行，引 V13 D-10/11/12） |
| G7 | persona 进度持久化（每步落 prefs per-user key，重进续步） | 蓝方：5 步不长，重填成本可忍 | G1 真差距但痛感中（13-15 决策点链上单页 5 步不是最长段——建模访谈才是）；G2 成本 S（对照 onboarding 完成态的 per-user prefs 形制现成，settings_provider.dart:957-958）；G3 中 | **采纳**（N50 前半：进度 resume 令，S 级） |

**辩论统计**：7 条 → 采纳 3（G2/G3/G7）+ 改写采纳 2（G1/G4）+ 转台账 2（G5/G6）。砍单 0（R2 已过滤）。本回合最大的「改写」是 G4：红方原案（加问询）被自家公约①（注册墙押后/零摩擦）否决，改为零问询破冰——**引导的后置不等于问询的后置，而是问询的对话化**。

---

## 4. 条款提案（候选编号 N46-N50，接续 v1.7 的 N45，待主会话采纳；若与其他卡编号冲突以主会话裁定为准）

**N46（§7 增补）· 首启双线 SLA（步数口径钉死）**
- 「安装→首次 AI 回复」双基线登记：**游客线 ≤4 taps 且 ≤6s**（现值 3-4 taps/5-6s，@b9a7da3d §2.1 线路 A）；**注册线跳过链 ≤6 taps**（现值 5-6 taps，§2.1 线路 B1）。新面/新 redirect/新表单 PR 必答「本改动使两线各 +几 tap」，基线只降不升。完整引导线决策站总数（现值 ≈13-15）沿 A-SPEC7 N39 登记制，本轮复核现值不变。
- 【依据：§2.1 拆解；§3 G1 辩论；C 线 TTFT 口径（FLEET-BRIEF §三）为秒级底座】

**N47（§7 增补）· 价值信号接线令（禁预留常量悬空）**
- GuestValueSignal 三信号必须全部接线或删除：firstTaskCompleted（已接线，task_execution_screen.dart:296）；**firstDiagnosisOutput 接线点=pattern 首产出回调；firstMemoryReferenced 接线点=memory_reference_receipt 首渲染回调**（guest_conversion_service.dart:18-24 自注释既定）；限期接线，届时转化卡增补 chat 落点（守门四条全复用，禁新增弹窗形态）。改造 #2。
- 【依据：§2.2 G2；A-SPEC7 N40 主条完整意图；§3 G2 辩论】

**N48（§6 增补）· 首启价值预告具象令**
- 首启两级副标题（splash splashSubtitle / login welcomeSubtitle）必须含北极星可感场景（期末/备考/提分类词），禁纯抽象口号；候选文案 l10n 双语 + A/B 后定稿。改造 #3。
- 【依据：§2.2 G3（app_zh.arb:103/:8537）；对标 §1 行 5 How→Why；§3 G3 辩论】

**N49（§7 增补）· 访客首聊破冰令（零问询差异化）**
- 访客首聊：①不新增任何前置问询；②注入隐式轻量上下文（访客标记+locale，走既有 extraContext 通道）；③Aurora 首条消息为主动破冰问句（把 persona 第一问对话化，答案顺流入画像——画像冷启动从「表单」移到「对话」）；④persona AI 预览卡改为 5 步全程可见（persona_onboarding_screen.dart:151 移出 step0 content）。跨层卡（需引擎 extraContext 契约配合）。改造 #4。
- 【依据：§2.2 G4；公约④首分钟差异化产出令；§3 G4 改写辩论】

**N50（§7 增补）· 引导可恢复与 skip 一等公民令**
- persona 引导进度 per-user 持久化（对照 settings_provider.dart:957-958 形制），中断重进续步不重填；两层 skip（persona :70-73 / modeling :140-145）视觉升级为主级可见档（登记制：skip 隐藏度不得深于「同屏次按钮」）。改造 #5。
- 【依据：§2.2 G7；§3 G1/G7 辩论；公约②】
- **台账登记（防双立项）**：G5 modeling 回退环（待 V 系列首飞实测后裁）；G6 星图三瑕疵（V13 缺陷线既辖）。

---

## 5. 改造清单（卡面提案，按北极星收益排序 top6，供卡池直接取用）

> 量级：S≤半天，M≈1 天，L≈2 天+。度量方式=每条卡面的验收数字。

| # | 改造 | 文件与落点 | 改什么 | 验收（度量） | 量 |
|---|---|---|---|---|---|
| 1 | **价值信号 2/3 接线（N47）** | pattern 首产出回调 + memory_reference_receipt 首渲染回调收口 recordValueSignal（照 task_execution_screen.dart:291-299 形制）；转化卡增 chat 落点（守门复用 guest_conversion_provider.dart:136-143） | 访客完成首次诊断/首次记忆引用时转化时刻不再失声 | 访客首诊产出→signalCount+1 断言；chat 内首诊→回到 home 卡可见；注册用户全程不可见（零变化） | S-M |
| 2 | **首启副标题具象化（N48）** | app_zh/app_en arb welcomeSubtitle+splashSubtitle 两词条；login_screen.dart:192-196、splash_screen.dart:122-130 零布局改动 | 首屏回答「进来能得到什么」 | 词条含场景词断言；l10n 全量通过；A/B 留双候选 | S |
| 3 | **persona 进度 resume（N50 前半）** | persona_onboarding_screen.dart:32 _currentStep 落 per-user prefs（形制照 settings_provider.dart:957-958）；initState 恢复 | 中断重进续步不重填 | 杀进程重进断言续步；完成态清除；5 步各验收 1 次 | S |
| 4 | **访客首聊破冰（N49 主条）** | 前端：chat 首条 initial_ai_message 对访客走破冰文案通道；引擎：extraContext 增访客标记（跨层契约，proto 不动、engine 侧 extraContext 透传既有通道）；persona 预览卡移出 step0（:151） | 首分钟回复可感知「懂我」；画像冷启动对话化 | 访客首聊注入字段经网关到达引擎断言；破冰句出现率 100%；预览卡 5 步可见 golden | M-L |
| 5 | **skip 一等公民（N50 后半）** | persona_onboarding_screen.dart:70-73 ghost→primary 次级档；modeling_chat_screen.dart:140-145 text→同屏次按钮档 | 跳过不必被找 | 首飞走查：skip 首屏可见性标记；两屏 golden 更新 | S |
| 6 | **双线 SLA 守卫（N46）** | 路由层步数守卫脚本（redirect 链静态计数）+ 首飞 checklist 登记进 V 系列模板 | 步数基线钉死只降 | 守卫：游客线 redirect 链 taps 计数 ≤4 断言；首飞报告含两线实测步数 | S |

**被砍/备忘**（防重复立项）：注册表单内容与 persona 五问**不裁减**（A-SPEC7 TV-G3 + 本轮 G1 辩论两度裁定：个性化是资产，压缩靠后置/对话化）；转化卡**禁弹窗形态**（N40 守门既辖）；**G5 回退环不动手**（先实测）；星图三瑕疵与注册表单四 Minor **不在本线施工**（V13 既辖，N45 家族已登记）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC8B-ONBOARDING/REPORT.md`（本文件，worktree wt272-res-onboard 内本地 commit，不 push）；零产品代码改动（mobile/lib、backend、scripts 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean/push 类操作
- [x] /tmp 无驻留（全程未写 /tmp）；无构建/测试/模拟器/浏览器实例（LIGHT 卡）；worktree 内无 build/.dart_tool 产生
- [x] 引用代码均为 @b9a7da3d 实读（routes/main/cold_start_motion/splash/login/register/persona_onboarding/modeling_chat/settings_provider/guest 三件套/dashboard/task_execution/task_list/error_list/sprint/seed_library/pattern_list/profile/user_routes/chat_screen 节选 + l10n app_zh.arb 七词条行号实测）；计数与步数表每步有 file:line；两处未实测结论显式标注「推断」（G4 首聊上下文缺口链路、G5 回退环）
- [x] V13/V13-RETEST 数据引自对应 REPORT.md 原文行号（V13-RETEST :17 ≤3s、:19/:66 6-8s、:23/:81 D-07/D-10/11/12 仍在）；N39/N40 落地经 git log 定位（e08feee3）+ 代码在位双证
- [x] 对标来源分级如实：实抓 4（nngroup.com/articles/mobile-app-onboarding/ 全文引文、growth.design headspace-user-onboarding、growth.design too-good-to-go-onboarding、lichess.org/about）+ 常识 4（Apple HIG/material.io/Duolingo/Chess.com+Notion/Google，JS 渲染或 404 未抓到正文，逐条标注）；web_search 429 已声明（reset 2026-09-24 16:02）
