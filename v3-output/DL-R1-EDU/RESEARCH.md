# DL-R1-EDU：学习/成长/AI 产品设计语言研究报告（第一轮）

> Sparkle 设计语言头脑风暴 R1 · 学习成长组
> 日期：2026-09-22 ｜ 组别：DL-R1-EDU（与国际工具组、自审组并行，产物供辩论轮）
> 研究方法说明：本轮搜索后端配额受限，改为**一手来源直连抓取**（官网、官方手册、官方博客、论文、维基、官方 App Store 数据、论坛原帖），所有引用链接均为已实际抓取验证的 URL。个别标注「产品知识，未一手验证」的条目需在辩论轮降权处理。

---

## 一、逐产品可迁移机制

### 1. 多邻国 Duolingo —— 留存工程的教科书（也是「反噬面」最全的样本）

它让用户天天来的机制与教训：

1. **连胜（streak）是身份资产，不是计数器**。数据显示连续学习到 10 天的用户流失率骤降；连胜配合日历视图、动画、奖励不断「加重这笔资产」，让用户把中断理解为「损失」而非「偷懒」。长连胜者占 DAU 一半以上（7 天以上连胜用户近三倍增长到超半数 DAU）。
2. **连胜必须配安全网**：streak freeze（连胜冻结）允许用户在缺席日保留连胜，把「 catastrophic loss → 卸载」的流失瞬间转化为「用资产续命 → 继续」。这是挫败保护的核心设计：**允许失败，但不允许失败变成离开的理由**。
3. **连胜双刃剑有明确证据**：growth.design 引述多邻国前增长负责人——连胜把人带回来，但**断掉一次就会导致卸载**；多邻国随后用「宝石下注 7 天连胜」的沉没成本设计把 D7 留存提升 +14%，本质是在风险时刻加注而非回避。
4. ** leagues（联赛）用「同水平分组」做社交比较**：借自 FarmVille 2，按活跃度（而非好友关系）匹配，青铜→黄金递进；自动加入零摩擦、做正常课程即可晋级。结果：学习时长 +17%，高投入学习者（每天 1 小时 × 每周 5 天）翻了三倍。**对比机制成立的条件：先分组，再比较**。
5. **「快乐路径」（Happy Path）**：回流用户的复习课被故意调容易，让失败者第一次点回来就赢。增长复盘里明确写：对回流用户「作弊」一点难度是合理的。
6. **回归时刻三件套**：欢迎回来奖励（100 宝石）+ 未完成目标/连胜的蔡格尼克效应（未完成任务记得更牢）+ 一键开课零犹豫。「复活用户」的留存概率比新用户还低 20%，所以**回归瞬间是全产品最脆弱的时刻，禁止堆功能**。
7. **通知「保护渠道」纪律**：Groupon 因滥发邮件毁掉渠道的前车之鉴 → 多邻国规定推送数量增长需 CEO 批准，放开优化的是时机、文案、图片、本地化，并用 bandit 算法自动学习每个人最佳推送时刻（KDD 2020 论文：A Sleeping, Recovering Bandit Algorithm for Optimizing Recurring Notifications）。
8. **对流失用户自动停发通知**：不打扰已流失者，避免「永久关闭通知」和拉黑——保存「将来一次成功唤回」的可能性。
9. **抄机制要先问为什么成立**：Gardenscapes 的「步数限制」直接照搬完全无效（课程本无策略性，稀缺感变成无聊的累赘）；Uber 式推荐也只带来 +3%。**机制不可移植，成立条件才可移植**。
10. **文案禁止羞辱**：growth.design 把多邻国文案里的轻微 user shaming 列为反模式——「滑向暗黑模式」。丢人不丢分，是文案红线。

链接：
- 增长复盘（一手）：https://www.lennysnewsletter.com/p/how-duolingo-reignited-user-growth
- 8 个留存战术（一手案例研究）：https://growth.design/case-studies/duolingo-user-retention
- 通知 bandit 论文（一手）：https://research.duolingo.com/papers/yancey.kdd20.pdf
- 案例库索引：https://growth.design/case-studies

### 2. Anki —— 间隔重复的「诚实呈现」

1. **调度即反馈**：复习间隔的长度直接编码记忆强度（今天 → 3 天 → 15 天 → 45 天），用户每次点「忘记/困难/良好/简单」都是在给算法喂诚实自评——**进度条不是装饰，是记忆状态的真话**。
2. **「用最少必要努力学会」是产品承诺**：手册明确目标是 "with the absolute minimum amount of effort necessary"——不表演勤奋，只展示遗忘曲线的真实形状。
3. **Nielsen：「Anki 让记忆成为一个选择」**——记忆从偶然事件变成可决策、可管理的资产。这句话是记忆类产品价值主张的天花板句式。
4. **Nielsen 对摩擦完全诚实**：他公开自己失败数次才建立习惯、中断 7 个月积压数千张卡——**产品的诚实包含承认「用户会失败，失败会积压」**，界面必须为积压的愧疚感设计（如 Anki 允许无限期搁置、不倒计时逼债）。
5. **卡片制作本身是加工**：Nielsen 建议自建牌组因为制卡过程就是 elaborative encoding——**让用户生产内容比喂内容记得牢**。
6. **「95% 的价值来自 5% 的功能」**：克制是 Anki 的价值观，也暗示了它 UI 粗糙仍有人用——功能诚实可以部分豁免界面粗糙，但仅限刚需工具。
7. **自评诚实是系统的地基**：算法只信用户的手动评分，平台不代用户假装「已掌握」。这是与一切「自动打卡」产品的本质区别。

链接：
- Anki 手册·背景（一手）：https://docs.ankiweb.net/background.html
- Nielsen《Augmenting Long-term Memory》（一手长文）：http://augmentingcognition.com/ltm.html

### 3. Quizlet —— 团队游戏与 AI 教练的两条路

1. **Quizlet Live：团队约束换正确率**——16 年上线的实时组队匹配游戏，规则是「答错一次就归零重计 12 题」，用团队连带责任让「蒙对」没有收益，**把正确率做进了游戏规则而非 UI 提示**。
2. **Q-Chat（2023）：AI 导师化转型**——基于 ChatGPT API 的虚拟导师，方向与 Khanmigo 一致（提问式引导），说明「学习产品的 AI 化」行业共识是导师制而非答案机。
3. **Course-Powered Quizlet（2025）**：按「学校 + 课程」组织内容、LLM 把笔记自动转为学习集与练习——**从「用户找内容」转为「内容从用户材料里长出来」**。
4. **成长侧教训**：创始人 2020 年因与执行团队分歧离开；媒体称其「教育界 growing monopoly」——商业压力把产品从学习工具推向「答案查找器」的临界点，是 Sparkle 要警惕的品类病。
5. （Learn 模式的自适应间隔与进度格子：产品知识，未一手验证，辩论轮降权。）

链接：
- 维基（已抓取核对）：https://en.wikipedia.org/wiki/Quizlet

### 4. Khan Academy —— 掌握式学习 + 能量点 + AI 导师分寸

1. **掌握度分级（mastery levels）让进度语义化**：Familiar → Proficient → Mastered 的分级 + mastery challenges 防止「考完就忘」，进度状态对应真实能力层级而非累计时长。
2. **能量点 + 徽章是「努力奖励」而非「结果奖励」**：答对、看视频、坚持都有点数，对不同水平学生都保持正反馈密度；徽章分流星/月亮/地球/恒星/黑洞等层级制造长期目标感。
3. **自己定义了「补充而非替代」**：Khan 明确说视频课「绝不算完整教育」，定位为把老师时间解放给个体关注——**产品边界声明本身就是品牌资产**。
4. **Khanmigo 的教学分寸是一手可引的**：官网原话 "Khanmigo doesn't just give answers… with limitless patience, it guides learners to find the answer themselves"、"challenges you to think critically and solve problems without giving you direct answers"。
5. **对家长的话术同理**："gently guides your child to discover the answers themselves"——把「不直接给答案」翻译成家长听得懂的放心。
6. **能力下限警告**：2024 年 2 月 WSJ 实测 Khanmigo 出现基础数学错误——**分步引导教学若步子是错的，比直接给错答案更糟**（它教坏了过程）。
7. Sal Khan 的愿景句式：「给每个学生一个私人 AI 导师，给每位老师一个 AI 助教」——AI 补的是 Bloom 2-sigma 的一对一稀缺，不是替代课堂。

链接：
- Khanmigo 官网（一手）：https://www.khanmigo.ai/
- 维基（含能量点/徽章/批评）：https://en.wikipedia.org/wiki/Khan_Academy
- TED 演讲页：https://www.ted.com/talks/sal_khan_how_ai_could_save_not_destroy_education/transcript

### 5. Forest —— 把「分心代价」可视化的损失厌恶

1. **核心机制：一棵会死树**——专注时段内离开 app，树就枯死。维基原文确认其设计原则就是 loss aversion（损失厌恶）而非强制锁定：**用虚拟资产的死亡代替说教**。
2. **森林 = 时间轴 + 成就墙合体**：每棵成功的树沉淀为森林视图，记录专注历史并按活动类型打标签——**进度可视化是「空间累积」而非「数字增长」**。
3. **虚拟币 → 真树的出口**：币可兑换成 Trees for the Future 的真实种树（已超 200 万棵）。把内循环奖励接到真实世界意义上，是「奖励出口」的天花板设计。
4. **共同专注（co-focus）**：多人各种各的树但「谁分心谁的树死」连坐，社交契约轻量到只有一个画面。
5. **克制的选择**：不用连胜、不用排行榜——证明专注类产品的损失厌恶**不需要羞辱性比较**也能成立。
6. **提醒反例**：Mashable 评价币奖励「不氪金就感觉太小」——奖励经济失衡会反过来稀释核心机制的诚意。

链接：
- 维基（已抓取核对）：https://en.wikipedia.org/wiki/Forest_(app)

### 6. 小睡眠（Cosleep / Heartide 心潮科技）——「在用户最脆弱的时刻保护体验」

1. **智能闹钟：只在浅睡阶段叫醒**——产品目标（叫醒）让位于用户体验（不被深睡惊醒的挫败感），**自家功能之间互相让路的挫败保护**。
2. **1400+ 声音、可混 4 种、100 级音量**：把「找到适合你的声音」本身做成进度与个性化空间。
3. **AI 哄睡人格（娜娜+星树）与聊天陪伴**：AI 人格承担「陪伴入睡」的任务型情感设计——情感陪伴绑定具体任务（入睡）而非泛聊天。
4. **睡眠报告 widget / 穿戴联动 / HRV 分析**：把不可见的睡眠变成每天早上可见的「收成」，**进度可视化锚定在生物数据上**。
5. **CBTI 数字疗法**：算法个性化失眠改善疗程——把「坚持」包装成疗程进度而非打卡压力。
6. **社区轻闭环**：睡伴匹配、名人哄睡（500+ 明星）、睡前电台 300 个用户故事、解梦分享——**情感类产品的留存来自「人味」而非排行榜**。
7. 专注侧同样内嵌：番茄钟 + 沉浸自习室 + Lofi，与睡眠共享同一套「声音资产」。

链接：
- App Store 官方数据（iTunes Search API 一手）：https://itunes.apple.com/search?term=小睡眠&country=cn&entity=software （或 App Store 搜索「小睡眠」）

### 7. 滴答清单 TickTick —— 生产力工具的「无游戏化」路线

1. **习惯追踪 = 习惯库 + 灵活打卡 + 洞察统计**：官网原话 "A rich habit library, flexible tracking options, and insightful statistics help you build good habits effortlessly"——**用统计洞察替代徽章**。
2. **番茄专注与任务同体**：25 分钟专注直接挂在任务上，专注时长进统计——专注不是独立玩法而是任务的一部分。
3. **「Constant Reminder」：一直响到完成为止**——对真正重要的事允许「烦人」，把打扰的强度交给用户选择。
4. **年视图 / 艾森豪威尔矩阵**：用户评价矩阵 "has been a brilliant innovation"——**把「优先级判断」本身可视化**是最被称道的点。
5. **启示（与 Forest 对照）**：工具类产品不硬加游戏化也能留住人——前提是统计与优先级可视化足够诚实。Sparkle 的任务系统可以走 TickTick 路线：**别为了奖励点数破坏任务语义**。

链接：
- 官网（一手）：https://ticktick.com/

### 8. Pi —— 对话人格与节奏的天花板

1. **使命即人格**：官方博客原话 "Our mission is to firmly align your AI with you, and your interests, above all else"、"in your corner, always on your team"——**立场先行**：AI 的对话人格先回答「你为谁说话」。
2. **反注意力经济的姿态是产品语言**：Pi 明确反对广告驱动科技「在你疲惫时攫取注意力」，宣称优化你的 wellbeing——这句话应写进 Sparkle 对话 AI 的设计宪法。
3. **维基确认的气质配方**：kindness（善意）+ diplomatic（敏感话题圆滑）+ humor（幽默），定位「personal intelligence / 情感支持型」。
4. **倾听的边界（批评一手可引）**：Fortune 2023——Pi 是很好的倾听者，「但这够吗？」——纯情感陪伴的学习产品会撞上「有用性天花板」。
5. **节奏启示**：Pi 的短句、追问、不打分不对错——对话节奏的「陪伴感」来自把评价体系关掉。学习对话需要相反的分寸：何时关闭评价、何时打开，是 Sparkle 双核路由的体验学问题。

链接：
- 官方博客（一手）：https://inflection.ai/blog/why-create-personal-ai
- 维基：https://en.wikipedia.org/wiki/Pi_(chatbot)

### 9. Character.AI —— 参与度上限的危险面（反面教材主矿）

1. **参与度数据惊人**：350 万日访客（2024-01），App 上线一周 170 万下载——对话陪伴的需求真实性无可置疑。
2. **星星评分塑造角色**：用户 1-4 星评价回复，塑造单个角色与整体模型——反馈循环简单、用户有「养育感」。
3. **群聊、游戏、微短剧**：多角色群聊 + 文字游戏 + AI 微短剧——参与度外扩的全家桶。
4. **危险面（一手维基）**：被诉「lacks proper safeguards and uses addictive design features to increase engagement」；两起青少年自杀诉讼；2024-12 安全响应包含 60 分钟使用提醒与未成年专属模型，2025-11 起禁止未满 18 岁用户聊天——**engagement maximization 与用户福祉冲突时，监管和诉讼会替你做决定**。
5. **对 Sparkle 的直接推论**：学习产品的对话人格必须内置「结束权」与「学习目标参照」，否则就是在向被诉讼验证过的失败模式滑动。

链接：
- 维基（含诉讼与安全时间线）：https://en.wikipedia.org/wiki/Character.AI

### 10. 豆包 —— 中国市场 AI 助手的规模化样本 + 豆包爱学

1. **规模**：MAU 1.72 亿、DAU 破亿（QuestMobile 2025Q3/Q4），中国 AI 应用第一。
2. **语气资产**：维基描述其对话「自然、亲和力强」——字节把「说人话」做成了全国民的默认预期。
3. **豆包爱学（教育子品牌，评分 4.8 / 43 万+ 评分）**：AI 老师分步讲题、拍题答疑、作业批改与错题分析、作文辅导、沉浸式 AI 视频课——**注意它也有「情绪陪伴」功能，但挂在讲题主线上**：情感是学习产品的佐料，不是主菜。
4. **语音即入口**：「先进语音输入与语音通话，识别准确、输出自然且接近人声」+ 拍照识图——中国用户的 AI 默认交互是语音+相机，不是键盘。
5. **反例**：智能体功能因「赌博预测、一键脱衣」等乱象随新规下架；AI 手机因隐私与微信兼容问题翻车——**Agent 能力开放必须与安全边界同步**。
6. **诚信细节**：App 明示「AI 可能出错，建议结合其他来源参考」——错误提示的诚实陈述是可抄的低成本信任设计。

链接：
- 中文维基：https://zh.wikipedia.org/wiki/豆包_(聊天机器人)
- App Store 官方数据（iTunes Search API 一手）：https://itunes.apple.com/search?term=豆包&country=cn&entity=software

### 11. DeepSeek App —— 「过程可见」的胜利

1. **R1 一手文档确认思维链对用户可见**："before outputting the final answer, the model will first output a chain-of-thought reasoning to improve the accuracy of the final response"，思考内容经 `reasoning_content` 单独返回——**把推理过程作为一等公民展示**，2025 年 1 月 R1 上线即登顶美区 App Store 超越 ChatGPT。
2. **免费 + 开源策略**：R1 免费（iOS/Android 同步）、MIT 许可——体验公平性（不设付费墙的能力）本身就是体验。
3. **思考模式的工程分寸**：官方文档规定 reasoning_content 默认不回传上下文（除非带工具调用）——**过程给人看，结论进历史**，这是「过程透明不污染对话」的实现层参照。
4. **警示数据点**：App Store 评分 3.87（同期豆包 4.65）——过程透明赢得了关注度，但 App 级体验（稳定性、交互打磨）拖后腿，**模型光晕 ≠ 产品体验**。
5. 争议注意：Anthropic 指控其抓取训练数据、多国政府限制——快速崛起的品牌同样需要边界叙事。

链接：
- 官方 Thinking Mode 文档（一手）：https://api-docs.deepseek.com/guides/thinking_mode
- 维基：https://en.wikipedia.org/wiki/DeepSeek

### 12. Obsidian Graph View —— 「好看但没人用」的一手证据

论坛原帖（thread 71316）用户原话：

1. **原帖主**：图谱就是 "nothing than a bunch of dots which represent notes and tags, but you can't actually do anything with it"（一堆点，你拿它什么都做不了）。
2. **毛球（hairball）化**：笔记一多就成 chaotic、不可读的团；有用户承认「调图谱过滤器的时间比改进笔记库还多」——**装饰性可视化的维护成本倒挂**。
3. **视觉/非视觉思维者分裂**：多人直接关掉；「可能是视觉思维与非视觉思维的差异」——同一功能对一半用户是噪音。
4. **技术细节杀体验**：节点位置每次加载重排、不能钉住、无方向性——对流程型任务完全不可用，要靠插件（Persistent Graph、ExcaliBrain）补。
5. **真正有用的例外**：局部图（local graph）+ 过滤。实际用例都是「回答一个具体问题」：写作时看当前笔记的邻域、找未打标签的孤立笔记（外圈孤点）、用搜索过滤看某关键词的分布——**可视化有效当且仅当它在回答用户的某个当下问题**。全局图只配承担「仪式感」（打招呼、年度回顾）。
6. 相关佐证帖：82382「怎么『正确』用 graph view？我完全 get 不到任何灵感」、2785「你怎么用 graph view？」。

链接：
- 主帖（一手）：https://forum.obsidian.md/t/whats-the-point-of-the-graph-view-how-are-you-using-it/71316
- 论坛搜索 API 验证的其他主题：
  - https://forum.obsidian.md/t/q-how-should-i-use-graph-view-correctly-because-im-not-getting-any-ideas/82382
  - https://forum.obsidian.md/t/how-do-you-use-the-graph-view/2785

### 13. Readwise —— 重访即复习的最低摩擦形态

1. **痛点句式可直抄**：官网原话 "How often do you finish a book, only to forget the key ideas two weeks later?"、"We don't remember things by just reading them once"——记忆面板的使命陈述模板。
2. **Daily Review = 间隔重复的零压力版**："We surface your best highlights back to you at the right times, and let you review them every day with the daily email and app"——**不逼自评、不做卡片，只做「在恰当的时间重现最好的东西」**。这是比 Anki 低门槛一个数量级的重访设计。
3. **三步叙事**：Import → Review → Remember——把复杂机制压成三个动词。
4. **资产管理而非信息流**：tag、note、search + 同步 Notion/Roam——重访的产品必须同时是「值得重访内容」的家。
5. **启示**：Sparkle 记忆面板的第一形态应该是 Readwise 式「每日重现」，第二形态才是 Anki 式「自评调度」；用户成熟度分层供给。

链接：
- 官网（一手）：https://readwise.io/

---

## 二、学习场景特有原则（15 条，注明印证者）

> 与「国际工具组」的通用工具原则互补：这些原则只在「学习成长」语境下成立或特别重要。

1. **进步必须可见且诚实**——进度状态必须编码真实能力/记忆状态，不做「时长表演」。印证：Anki 间隔=记忆强度（Anki 手册）、Khan mastery 分级、Nielsen「memory becomes a choice」。
2. **失败不羞辱**——错误的呈现是信息不是审判；文案红线。印证：growth.design 把 user shaming 列为多邻国反模式；Khanmigo "limitless patience"；Anki 对中断积压不倒计时逼债。
3. **AI 给台阶不给答案**——AI 导师的价值在引导过程，不在最快交付结论。印证：Khanmigo 官网双句（见上）、豆包爱学分步讲题、Sal Khan「私人 AI 导师」愿景；反例警示：WSJ 实测 Khanmigo 算错——**台阶本身必须踩得实**。
4. **连胜要配安全网**——凡引入连胜/连续机制，必须同时提供冻结、补签或宽限；断签时刻的用户体验优先于连胜数字本身。印证：多邻国 streak freeze（Lenny's 增长复盘）、「断一次就卸载」的增长负责人原话（growth.design）。
5. **回归时刻比开始时刻更脆弱**——回流用户见到的第一屏必须「容易赢 + 少东西 + 有礼物」，禁止堆高级功能。印证：多邻国 happy path、回流三件套、resurrected 用户留存反低 20%（growth.design）。
6. **挫败保护先于激励设计**——先把「用户会失败、会累、会缺席」设计进去，再加激励。印证：多邻国快乐路径+冻结+自动停推；小睡眠浅睡闹钟（自家功能为体验让路）。
7. **反馈即时，但渠道有纪律**——学习反馈可以毫秒级（点数、树、动画），但打扰必须克制且越学越懂时机。印证：多邻国通知 bandit（KDD 2020）+「保护渠道」CEO 审批制 + 对流失者自动静默；Character.AI 60 分钟提醒是被诉讼逼出来的补课。
8. **退出要有完成感**——产品要允许用户「体面地学完今天」，不留无尽列表；参与度最大化是学习产品的伦理红区。印证：growth.design「providing exit points」；Character.AI 诉讼原文。
9. **可视化要回答「我现在该干什么」**——能回答当下问题的图（局部图、过滤视图、掌握度树）有人用；回答不了的全局图是装饰。印证：Obsidian 论坛 71316 全帖共识（local graph 有用、global graph eye candy）。
10. **社交比较先分组、后比较、可退出**——和同水平的人比才有激励意义，和全体比是羞辱装置。印证：多邻国联赛按活跃度分组+青铜到黄金+零摩擦自动加入（Lenny's）。
11. **温度换不来能力，倾听有边界**——情感陪伴是学习产品的留存佐料，效用才是主菜；纯倾听人格会撞有用性天花板。印证：Fortune 对 Pi 的批评、豆包爱学「情绪陪伴挂在讲题线上」、Pi 官方使命的反面自证。
12. **过程可见是信任与教学的双重杠杆**——展示思考过程既建立信任又示范思维，但「过程给人看，结论进历史」。印证：DeepSeek thinking_mode 官方文档（reasoning_content 独立返回、默认不入上下文）；与 Khanmigo 的分步引导同构。
13. **把记忆变成选择，把遗忘正常化**——记忆是可管理的资产，「忘了」是机制输入而非道德污点。印证：Nielsen「Anki makes memory a choice」+ 对积压愧疚的诚实处理；Readwise 痛点句式。
14. **损失厌恶比奖励更利，方向必须指向学习本身**——可失去的东西（树、连胜、宝石）驱动力强于获得，但要防止它异化为付费焦虑。印证：Forest 枯树（维基确认 loss aversion 为设计原则）、多邻国宝石下注 +14% D7（growth.design）、Forest 币奖励失衡的 Mashable 批评。
15. **低摩擦重启决定长期留存**——回到学习状态的路径要短到无意识（一键开课、开屏即问、语音直接说）。印证：多邻国一键开课（growth.design friction 战术）、豆包「打开即问」、DeepSeek 秒级思维链开跑。

---

## 三、对 Sparkle 三大面的映射

### 知识星图

- **正面对标**：
  - **Khan mastery 分级**（节点状态 = 真实掌握度层级，星图上「亮」的节点必须真的亮）；
  - **Obsidian local graph**（星图的默认视角应是「当前学习内容的邻域」——回答「我在学的东西和什么相连、下一个该碰什么」，而非展示全局毛球）；
  - **Forest 空间累积**（星图生长的「空间感」比数字增长更有情绪价值，节点可视为已验证的「树」）。
- **反面教材（本组主判例）**：**Obsidian 全局 Graph View**——论坛一手证据链完整：好看、截图传播、多数人拿它什么都做不了、维护过滤器的时间倒挂、非视觉思维者直接关闭。**Sparkle 知识星图若不能点击回答「我现在该学什么」，就只是壁纸**。允许它存在，但必须给它一个仪式性场景（如阶段性回顾/成就时刻），禁止它承担导航职责。
- **设计推论**：星图双视图——「工作视图」（局部、可操作、绑定掌握度与推荐动作）+「仪式视图」（全局、华美、只在成就/回顾时刻出现）。

### 记忆面板

- **正面对标**：
  - **Readwise Daily Review**（第一形态：零压力每日重现，「在恰当的时间重现最好的东西」，邮件+App 双通道的仪式感）；
  - **Anki 诚实调度**（第二形态：成熟用户的自评与间隔真话）；
  - **Nielsen「记忆是选择」**（面板的信息架构：遗忘不是红字警告，是待办输入）。
- **反面教材**：**Quizlet 滑向「答案查找器」**（商业压力 + 内容众包让「学习工具」被当成「抄答案工具」，创始人出走、媒体定调垄断批评）——Sparkle 记忆面板如果只展示「存了什么」而不驱动「重访与自测」，就是在培养查询习惯而非记忆习惯。
- **设计推论**：记忆面板每天给一个「今日重现」入口（Readwise 式），重现项可一键升级为 Anki 式自测卡；遗忘统计用「诚实曲线」而非打卡绿格。

### 主动推送

- **正面对标**：
  - **多邻国通知 bandit**（推送时机个人化学习 + 数量纪律 + 对流失者自动静默——KDD 2020 论文给了算法层直接参照，Sparkle 有 gRPC 实时链路，条件更好）；
  - **streak-saver 通知**（在「将要失去」前的瞬间提醒，价值密度最高——推送的黄金时刻是损失预警，不是每日问安）；
  - **小睡眠浅睡闹钟**（推送/打扰要挑用户最可接受的生理与情境窗口——Sparkle 的状态聚合器正是为此而生）；
  - **Pi 反注意力经济使命**（推送宪法级原则：不利用疲惫攫取注意力）。
- **反面教材**：
  - **Groupon 式渠道自杀**（滥发毁掉通知渠道，多邻国因此立 CEO 审批制）；
  - **Character.AI 的 engagement maximization**（60 分钟提醒是被诉讼逼出来的补课）；
  - **多邻国 Gardenscapes 步数照搬失败**（推送内容抄机制不抄成立条件）。
- **设计推论**：推送三律——①只推「损失预警 + 恰当时机 + 与当前学习状态相关」三类；②用户连续不响应即自动降频至静默；③每次推送可一键直达「完成它」的最小动作。

---

## 四、「AI 学习伴侣」品类：体验上限谁定的，差距在哪

**上限被四家分头划定，且互不兼容：**

| 维度 | 上限制定者 | 上限内容 | 未被复制的部分 |
|---|---|---|---|
| 留存工程上限 | 多邻国 | bandit 推送、连胜+安全网、联赛分组、回流设计 | 它不是对话式 AI，学习内容浅 |
| 教学法上限 | Khanmigo / Sal Khan | 苏格拉底分步 + 掌握式学习 + 无限耐心 | 模型能力不足（WSJ 实测算错），留存设计平庸 |
| 情感上限 | Pi | 立场先行（"on your team"）、反注意力经济、善意-幽默-圆滑配方 | Fortune 之问：光倾听不够用 |
| 过程透明上限 | DeepSeek | 思维链可见、免费开源、即时开跑 | App 工艺粗糙（3.87 分），无学习场景闭环 |
| 参与度危险上限 | Character.AI | 证明了对话陪伴的参与度天花板与它的诉讼价 | ——它是禁区划定者，不是标杆 |

**差距在哪：**

1. **没有一家同时拥有「状态」与「分寸」**：多邻国知道你什么时候学但不懂深教；Khanmigo 懂教但不知道你全天的学习状态；Pi 懂情绪但不懂学习。**「懂状态 + 会教 + 有温度 + 过程透明」四合一尚无产品做到**——这是品类公认的空位。
2. **学习产品的「结束设计」全面缺位**：所有竞品都在优化「多学一点」，没人把「今天到此为止，且你今天赢了」做成一等体验（只有 growth.design 把它列为多邻国的改进项）。Character.AI 的诉讼证明了参与度无上限的代价。
3. **中国市场特有差距**：豆包爱学证明了「分步讲题 + 情绪陪伴」可以规模化为 4.8 分产品，但它的记忆与成长可视化几乎空白、推送仍是工业化的「催学」；DeepSeek 证明了过程透明对中国用户的吸引力，但没人为学习场景重排它。**中文语境下「AI 学习成长伴侣」的诚实-温度-过程三合一，无人占位。**
4. **对 Sparkle 的结论**：Sparkle 的架构（ChatOrchestrator 双核路由 + 状态聚合器 + 证据融合）恰好长在空位上：**对话有分寸的潜在条件（Khanmigo 式）、状态有一手全景（多邻国 bandit 式推送的更好燃料）、过程可以透明（DeepSeek 式思维链）**。设计语言的使命是把这四个上限焊进一套体验纪律——本组第二节 15 条原则即为焊点清单。

---

## 附：本轮已验证一手来源清单

| 来源 | URL |
|---|---|
| Duolingo 增长复盘（Jorge Mazal） | https://www.lennysnewsletter.com/p/how-duolingo-reignited-user-growth |
| growth.design Duolingo 8 战术 | https://growth.design/case-studies/duolingo-user-retention |
| Duolingo 通知 bandit 论文 KDD'20 | https://research.duolingo.com/papers/yancey.kdd20.pdf |
| Anki 手册·背景 | https://docs.ankiweb.net/background.html |
| Nielsen《Augmenting Long-term Memory》 | http://augmentingcognition.com/ltm.html |
| Quizlet 维基 | https://en.wikipedia.org/wiki/Quizlet |
| Khanmigo 官网 | https://www.khanmigo.ai/ |
| Khan Academy 维基 | https://en.wikipedia.org/wiki/Khan_Academy |
| Sal Khan TED 页 | https://www.ted.com/talks/sal_khan_how_ai_could_save_not_destroy_education/transcript |
| Forest 维基 | https://en.wikipedia.org/wiki/Forest_(app) |
| 小睡眠 App Store 数据 | https://itunes.apple.com/search?term=小睡眠&country=cn&entity=software |
| TickTick 官网 | https://ticktick.com/ |
| Pi 官方博客 | https://inflection.ai/blog/why-create-personal-ai |
| Pi/Inflection 维基 | https://en.wikipedia.org/wiki/Pi_(chatbot) |
| Character.AI 维基 | https://en.wikipedia.org/wiki/Character.AI |
| 豆包中文维基 | https://zh.wikipedia.org/wiki/豆包_(聊天机器人) |
| 豆包 App Store 数据 | https://itunes.apple.com/search?term=豆包&country=cn&entity=software |
| DeepSeek Thinking Mode 文档 | https://api-docs.deepseek.com/guides/thinking_mode |
| DeepSeek 维基 | https://en.wikipedia.org/wiki/DeepSeek |
| Obsidian 论坛 graph view 主帖 | https://forum.obsidian.md/t/whats-the-point-of-the-graph-view-how-are-you-using-it/71316 |
| Obsidian 论坛相关帖 82382 / 2785 | https://forum.obsidian.md/t/q-how-should-i-use-graph-view-correctly-because-im-not-getting-any-ideas/82382 ・ https://forum.obsidian.md/t/how-do-you-use-the-graph-view/2785 |
| Readwise 官网 | https://readwise.io/ |
| growth.design 案例库（含 Spotify Wrapped 等待辩论轮引用） | https://growth.design/case-studies |

*（已知缺口：Quizlet Learn 模式细节、Pi 的语音节奏细节未获一手来源，文中已标注；搜索通道配额 2026-09-24 重置后可补。）*
