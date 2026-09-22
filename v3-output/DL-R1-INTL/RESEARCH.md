# DL-R1-INTL · 国际顶级软件研究组报告

> Sparkle 设计语言头脑风暴 · 第一轮输入
> 研究组：国际顶级软件研究组（INTL）
> 日期：2026-09-22
> 方法：以一手来源为主（Apple HIG 官方 JSON 数据、WWDC18 #803 全文字幕、Linear 官方工程/设计博客、Material 3 官方 token 仓库 material-web 的生成文件、NN/g 实测报告），辅以产品官网与获奖记录。所有带链接论断均经本次实际抓取验证；少数标注「(知识)」的为业界共识、未逐字核对。
> 局限：WebSearch 配额耗尽，部分二手拆解（Things 3 / Telegram 的深度 UI 拆文）未能获取，这两家以官网一手材料 + 共识补足；M3 官网纯 JS 无法直读，改用官方 token 仓库源码（更精确）。
> 本报告零代码改动；主仓与 backup 目录只读。

---

## 0. 现状基线（研究前对齐，只读感知）

- 读了主仓 `mobile/lib/core/design/design_system.dart`（1428 行）与 `motion.dart`、`tokens_v2/animation_token.dart`。
- 看了 B-04 基线 9 张截图（`home__main` / `chat__history` / `galaxy__tree` / `goal__library` / `memory__panel` / `onboarding` / `profile` / `settings` / `task__library`）。
- home 截图直观问题：**约 9 个 UI 簇同屏竞争**（用户卡、Aurora 策略条、"理解你"卡+3 chips+CTA、目标旗、大字计划叙述、"指挥台"卡+2 统计、4 快捷操作行、输入栏、底部导航）；**米色叠米色卡片套卡片**；棕色 accent 同时用于可点击与非可点击元素，颜色失去信息价值；中段超大号加粗叙述文字与卡片标题层级混乱；底部**三层动作区**（快捷行+输入栏+Tab）互相竞争。
- 代码直观问题：`AnimationSystem.spring = Curves.elasticOut`（把弹性动画做成橡皮筋）；`hero = 620ms`；呼吸控制器 4s/圈（0.25Hz）；圆角散布 18/20/24/28 无语义阶梯。

---

## 1. 逐产品分析：它为什么「感觉」好

### 1.1 Things 3（Cultured Code）— 两夺 Apple Design Award 的「安静」

官方与获奖佐证：[culturedcode.com/things](https://culturedcode.com/things/)（"Honored twice with the prestigious Apple Design Award… a joy to use and beautiful to look at"）；[The Sweet Setup 长期评为首选 to-do](https://thesweetsetup.com/things-3/)。

可迁移机制：
1. **近单色 + 唯一 accent**：界面近乎黑白灰，蓝色只留给「可交互/品牌时刻」。checkbox、分隔线、元数据全部退成低对比灰，**任务内容永远是最深的颜色** → 颜色=交互性的编码不被稀释。
2. **大标题 + 宽松行距的「安静排版」**：Today/项目页用系统字体大标题开场，行距与字距刻意放宽，密度低于同类（Todoist/TickTick），第一印象是「呼吸感」而非信息量。
3. **标志性微交互即品牌**：勾选完成的动画、Magic Plus 按钮展开、拖拽排序——把「完成一件事」这个学习场景里最高频的正反馈做成全 app 最好的一个动画，其他一切从简。
4. **渐进披露**：详情用 peek 面板/右侧栏，不跳屏；导航层级极浅，任何操作 1 步可达。
5. **完全原生**：SF 字体、系统控件、系统触觉、系统暗色——「像长在平台上」本身就是质感来源。
6. **每屏一个主角**：任何时刻只有一个视觉焦点（今天列表 / 某项目），其余 UI 全部同色系退后。

### 1.2 Linear — 「性能即设计」与 2026 刷新的两条命名原则

官方一手材料（本次已抓全文）：
- [A calmer interface for a product in motion](https://linear.app/now/behind-the-latest-design-refresh)（2026-03，Charlie Aufmann & Maxime Heckel）
- [Design is more than code](https://linear.app/now/design-is-more-than-code)（Karri Saarinen）
- [A Linear spin on Liquid Glass](https://linear.app/now/linear-liquid-glass)（Robb Böhnke）
- [Linear Method](https://linear.app/method)
- 技术拆解（二手但极详尽）：[How's Linear so fast? A technical breakdown](https://performance.dev/how-is-linear-so-fast-a-technical-breakdown)

可迁移机制：
1. **刷新报告的两条命名原则（原文）**：
   - **"Don't compete for attention you haven't earned"（不争夺你还没赢得的注意力）**——信息密集产品里，不是每个元素都该有同等视觉权重；侧栏比内容区「暗几档」，tabs 更紧凑，图标减量、降尺寸、去掉彩色底。**→ 对 Sparkle 首页 9 簇竞争是最直接的解药。**
   - **"Structure should be felt not seen"（结构应被感受而非被看见）**——边框与分隔线曾悄悄增殖，刷新时把直角改圆角、降对比，让结构「在而不吵」。**→ 对 Sparkle 卡片套卡片、每卡带边框的现状是直接对应。**
   - 该文开头一句也应贴在 Sparkle 每个工位：**"Software rarely gets worse all at once. It contorts out of shape one useful feature at a time."**（软件很少一下子变坏，是一个有用的小功能一次一次把它挤变形的）——这正是 U-01 账本「157 平行组件史」的病理描述。
2. **乐观 UI / 本地优先（无 spinners）**：`issue.title = ...; issue.save()`——UI 同步基于本地内存渲染，网络请求被藏到后台。「你越能避免 loading 态，感觉越快」。spinner 被视为设计失败而非技术必需。
3. **键盘优先 + ⌘K**：高频操作全部键盘可达，命令面板让「找功能」变成「打字」。移动端对应物是「全局搜索/快捷动作入口」。
4. **色彩系统用 LCH/OKLCH 思维管理暖灰**：默认主题从冷蓝灰调向「更暖但不浑」的灰，靠内部 token 调色工具反复迭代——中性色是需要像 accent 一样认真调的。(知识，刷新文中有叙述)
5. **动效克制且服务空间感**：Linear 的移动端自研 Liquid Glass 只用于**导航/控制层**，内容层保持不透明——材质=层级语义（与 Apple HIG 一致）。
6. **刷新方法论**：feature flag 开关新旧 UI 一键对比、内置取色器直接改 design token、token→Figma 插件闭环——**设计系统不是文档，是可实验的工具链**。

### 1.3 Arc Browser（The Browser Company）— 「性格」与减负

一手/获奖佐证：[arc.net](https://arc.net/)（"Clean and calm, Arc shapes itself to how you use the internet"）；[Inverse 设计评述](https://www.inverse.com/tech/arc-mobile-companion-app-design-review-the-browser-company)。

可迁移机制：
1. **信息架构优先于视觉**：Arc 的「感觉好」一半来自 Spaces/Pinned Tabs 把浏览器混乱的模型**重组**了——先给用户一个新的心智模型，皮肤只是模型的表达。**界面丑的根因常是 IA 没想清，不是 CSS 没调好。**
2. **Chrome 退后到近乎隐形**：地址栏/工具条只在需要时出现；内容占据全部。
3. **「玩味」被约束在固定容器里**：主题、彩蛋、每日壁纸都有统一容器，不侵入内容区——个性与秩序共存。
4. **空态即导览**：新 Space 的空状态教你「这里该放什么」。
5. 反例教训（对 Sparkle 也有用）：Arc 移动版是「伴侣 app」而不是缩小的桌面版——**同一产品在不同屏幕上敢于做不同信息架构**，而不是把桌面结构塞进手机。

### 1.4 Fantastical（Flexibits）— 「把复杂输入变成一句话」

一手佐证：[flexibits.com/fantastical](https://flexibits.com/fantastical/)（用户原话："The design is clean, the layout is intuitive, and adding events feels effortless. I love how I can just type 'Meeting with…'"）。

可迁移机制：
1. **自然语言输入 = 把表单做成一句台词**：新建事件的全部字段（时间/地点/参与者/重复）被压缩成一行自然语言解析，回车即建——**AI 学习产品最该抄的一条**：学生说「周五晚上复习图论两小时」，就应当直接成为任务，而不是 7 个输入框。
2. **日历视图是唯一主角**：所有功能（任务、天气、可用性）都作为日历格子的叠加层出现，不另开页面。
3. **颜色 = 日历身份**：每个日历一个稳定颜色，颜色承载身份信息而非装饰——与「同一颜色不表达两种含义」的 HIG 原则互证。
4. **细节一致性**：菜单/快捷键/Widget 全平台同一套心智。

### 1.5 Flighty — 「通知即内容」与实时态的确定性

一手佐证：[flighty.com](https://www.flighty.com/)（Apple Design Award Winner 2023；"Get the truth when you travel"；通知示例 "Mom landed in New York — 6:32am (22m early)"）。

可迁移机制：
1. **状态通知写得像人话**：每条推送 = 一个确定的结论 + 一个数字（早 22 分钟），不是 "您的航班状态已更新"。**学习场景直接映射**：「图论概念梳理已完成，计划进度 41%→44%」，而不是「任务状态改变」。
2. **延迟预测 = 把不确定性变成可执行的确定**：Flighty 敢在航司发布前预测延误——Sparkle 的 AI 预测（过载风险、健康度）应该同样**给出结论和建议动作**，而不是展示原始指标。
3. **全程无死角的时间线**：Preflight→At airport→After landing 的分段时间线，用户在任何时刻都知道「现在在哪、下一步是什么」——学习计划时间线可完全类比。
4. **图标/颜色语义高度一致**：绿=准点、黄=注意、红=变化，全局统一绝不混用。

### 1.6 Bear / Craft — 「字体节奏就是编辑器的一切」

一手佐证：[bear.app](https://bear.app/)（Apple Design Award 2017；"A polished, minimal interface stays out of your way"）；[craft.do](https://www.craft.do/)。

可迁移机制：
1. **Bear：markdown 符号「渲染即消失」**：输入 `#` 后立即变成样式标题——语法噪声不驻留，输入成本与视觉噪声同时降到最低。AI 对话里 Markdown 的渲染同理。
2. **Bear：排版层级用字号+字重+颜色深浅三轴表达**，行内标签用「小胶囊+色相」区分层级——标签系统（Sparkle 的 chips 很多）可以学它：**chips 颜色数量有上限，语义固定**。
3. **Craft：块级文档的「结构显形于交互」**：拖拽手柄/块选中时才显出结构线，静态时近乎纯文档——「结构应被感受而非被看见」的编辑器版。
4. **两者共同点：编辑区永远占满宽度的 60-70%，两侧大量留白**——内容工作区（学习笔记/对话）应比导航区拥有绝对的空间特权。

### 1.7 Apple HIG + WWDC18《Designing Fluid Interfaces》— 动效与触觉的物理法则（本次最大信息量来源）

一手材料（本次实际抓取）：
- HIG 官方 JSON 全文：[Motion](https://developer.apple.com/design/human-interface-guidelines/motion)、[Materials](https://developer.apple.com/design/human-interface-guidelines/materials)、[Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback)、[Playing haptics](https://developer.apple.com/design/human-interface-guidelines/playing-haptics)、[Typography](https://developer.apple.com/design/human-interface-guidelines/typography)、[Color](https://developer.apple.com/design/human-interface-guidelines/color)、[Layout](https://developer.apple.com/design/human-interface-guidelines/layout)
- WWDC18 #803 全文字幕：[Designing Fluid Interfaces](https://developer.apple.com/videos/play/wwdc2018/803/)

**Motion（原文摘译）**：
- "Add motion purposefully, supporting the experience without overshadowing it."（动效要有目的，支持体验而非抢戏；滥用动效让人分心甚至不适。）
- **"Let people cancel motion. As much as possible, don't make people wait for an animation to complete."**（尽量别让人等动画播完。）
- "Aim for brevity and precision in feedback animations"——反馈动画要**短而准**；"generally avoid adding motion to UI interactions that occur frequently"——**高频交互不要加动效**。
- **HIG 明确警告持续振荡**："avoid showing objects that oscillate in a sustained way. In particular… a frequency of around 0.2 Hz because people can be very sensitive to this frequency."（visionOS 节，但生理机制通用）→ **Sparkle 4s/圈的呼吸动画=0.25Hz，正落在人类最敏感的振荡频带**；224 处 particle + 113 处 glow 若含持续脉动，属于同类风险。

**Materials（原文要点）**：Liquid Glass/材质是**功能层与内容层的分界**——"forms a distinct functional layer for controls and navigation… Don't use Liquid Glass in the content layer… **Use Liquid Glass effects sparingly**."（材质用多=层级混乱+干扰内容。）材质/opaque 的选择应基于语义而不是它好看的颜色。

**Feedback（原文要点）**：反馈强度要匹配信息重要性；状态类反馈就地内联（如 Mail 未读数放工具栏）；"people typically expect their action to succeed, they only need to know when it doesn't"（成功是预期，只需要报忧）→ **成功确认要克制，失败才值得打扰**。

**Playing haptics（原文要点）**：用系统触觉的**文档化语义**（Success/Warning/Error、Light/Medium/Heavy/Rigid/Soft、Selection）；"If a haptic doesn't reinforce a cause-and-effect relationship, it can be confusing and seem gratuitous."；**"Often, the best haptic experience is one that people may not be conscious of, but miss when it's turned off."**（最好的触觉是用户没意识到、关掉却会想念的。）→ 触觉=因果对，不是彩蛋。

**Typography（原文要点）**：iOS 默认 17pt / 最小 11pt；**避免细字重**（"avoid Ultralight, Thin, and Light"）；「最小化字体家族数量」；**Dynamic Type 响应时只放大用户关心的内容**；text styles 本身就是官方「排版节奏表」。

**Color（原文要点）**：**"Avoid using the same color to mean different things."**（同一颜色不得表达两种含义——Sparkle 棕色既做 accent 又做普通文字的现状违反此条。）

**Layout（原文要点）**：按阅读顺序排重要性；**对齐与缩进表达从属**；「相关内容用留白/容器/分隔线分组」；**progressive disclosure（渐进披露）让布局更干净**。

**WWDC803（金句级原则，均为演讲原文）**：
1. **"Response"**：一切交互瞬时响应；"look for delays everywhere"——延迟是渗进来的，要主动猎杀。
2. **"Constant redirection and interruption. This one's big."**——界面必须**永远可被打断/改向**，包括动画进行中。"don't make people wait for an animation to complete… it feels alive."
3. **"Spatial consistency"**：从哪来回哪去；slide-in 就要 slide-out，"it feels like I'm sending it somewhere" 是 bug 不是风格。
4. **阻尼规则**：手势**有动量→给一点 overshoot（80% damping）**；**tap 驱动（无动量）→100% damping 不许弹**。"if a gesture has momentum, and there isn't any overshoot, it can often feel broken"（反过来：tap 也弹就是错的）。**→ Sparkle 把 `elasticOut` 当全局 spring、按钮也弹，正违反此条。**
5. **Bounciness 可当教学信号**：手电筒按钮轻拍回弹 = 暗示「再用力按」。弹跳是**有含义的提示**，不是默认口味。
6. **"Stay in character"**：同一物件在不同交互（滚动/回顶）里要表现得像同一种材料；全 app 一套性格，「学会一个行为就会另一个」。
7. **Endpoint alignment**：手势落点要对齐意图（速度参与决策，不只看位置）。
8. **触摸可反悔**：手指移出按钮=取消，移回=高亮确认；"create an extra margin around the tap area"。
9. **并发手势**：从触摸开始就识别所有可能手势，意图确定后再取消其他——绝不先锁死一种。

### 1.8 Material You / Material 3 — 令牌化动态色与动效阶梯（数值级一手来源）

一手材料：
- [material-web 官方 token 仓库：md-sys-motion v0.192](https://github.com/material-components/material-web/blob/main/tokens/versions/v0_192/_md-sys-motion.scss)（本次抓取原始 SCSS）
- 同仓库 [md-sys-shape](https://github.com/material-components/material-web/blob/main/tokens/versions/v0_192/_md-sys-shape.scss)
- [material-color-utilities README](https://github.com/material-foundation/material-color-utilities)（动态色官方算法库，含 Dart 实现）
- 文档入口：[m3.material.io/styles/color/system](https://m3.material.io/styles/color/system/overview)、[m3.material.io/styles/motion](https://m3.material.io/styles/motion/easing-and-duration/applying-easing-and-duration)（站点 JS 化，数值以仓库源码为准）

**M3 官方时长阶梯（源码值）**：
- short: 50/100/150/**200ms**（图标、checkbox、ripple 等微交互）
- medium: 250/300/350/**400ms**（卡片展开、菜单）
- long: 450/500/550/**600ms**（大区域转场）
- extra-long: 700/800/900/**1000ms**（仅整屏级叙事）
**→ M3 一切常规转场上限 600ms；Sparkle 的 `hero=620ms`、`pageTransition=350ms` 落点本身尚可，但 620ms 的「英雄动画」若无手势驱动就是超预算。**

**M3 官方缓动（源码值）**：
- standard: `cubic-bezier(0.2, 0, 0, 1)`（默认，绝大多数场景）
- emphasized-decelerate: `cubic-bezier(0.05, 0.7, 0.1, 1)`（入场）
- emphasized-accelerate: `cubic-bezier(0.3, 0, 0.8, 0.15)`（退场）
- **没有任何「elasticOut/反复震荡」曲线**。M3 的「强调」= 非对称减速（快出缓停），不是弹。

**M3 官方圆角阶梯（源码值）**：extra-small 4 / small 8 / medium 12 / large 16 / extra-large 28 / full=药丸。**→ 五级语义半径 vs Sparkle 散布的 18/20/24/28。**

**动态色（Material You）**：从一张源色（用户壁纸/品牌色）算法生成全套 tonal palette（色调- Chroma-亮度三轴），再映射到语义角色（primary/onPrimary/surface/onSurface…），**所有角色都有对比度保证**；深浅色/高对比自动变体。「用户只配一个色，得到一套永远协调、永远可读的界面」——对 Sparkle 的直接启示：**中性色（背景/分隔/文字灰阶）必须由算法/令牌生成，不允许手挑**。

### 1.9 Telegram / Apple 过渡与手势 — 手势驱动的连续性

Telegram 一手材料较薄（官网 blog 可读但少有设计哲学专文；[Chat Folders 发布](https://telegram.org/blog/folders)展示了滑动手势切换文件夹夹层的模式）。以下机制为业界共识（标注：知识）：
1. **一切过渡由手势驱动而非按钮驱动**：滑一滑、拖一拖完成 90% 导航；动画只是手指的影子（进度随手势，松手才补完）。
2. **速度接管决策**：快速轻扫=切换到底，慢拖=跟随——同一手势因速度产生两种结果，界面「接住」用户动量（与 WWDC803 endpoint alignment 完全同源）。
3. **转场共享元素连续**：聊天头像在列表→对话→大图三个尺度上是同一个元素在移动，无跳变。
4. **即时反馈永远先于结果**：按下即有视觉/触觉反应，不等网络、不等逻辑。

### 1.10 乐观 UI 与加载态（横向补充）

- 概念正典：Meteor 团队 [Optimistic UI with Meteor: Latency Compensation](http://info.meteor.com/blog/optimistic-ui-with-meteor-latency-compensation)（HN 134 分）——「先把结果画出来，网络在后台追上」的最早系统阐述。
- Linear 实践细节见 §1.2：**本地状态是唯一渲染源；loading 态数量是设计质量指标**。
- 对 AI 产品的推论：流式输出（token 流）本身就是乐观 UI 的一种——**与其转圈 3 秒出全文，不如 300ms 内出第一个字**。骨架屏只用于「结构已知、内容未知」；「结构未知」就该先出布局框架而不是统一灰块。(知识)

---

## 2. 跨产品共性原则（16 条，附印证）

> 每条标注印证来源。✦ = 与 Sparkle 现状强相关。

1. ✦ **内容优先，chrome 退后**：内容是颜色最深/面积最大/唯一的主角；导航、工具条、状态条降 2-3 档明度让位。
   （Linear 刷新原则原文、Things 3、Bear、Arc、HIG Layout）
2. ✦ **结构应被感受而非被看见**：容器/边框/分隔线是最后手段；优先用留白与对齐分组；结构线出现时低对比、圆角化。卡片不套卡片。
   （Linear 刷新原则原文、HIG Layout "group with negative space"、Bear、M3 tonal surface 分层）
3. ✦ **颜色只编码一种含义**：accent 色 = 可交互/品牌时刻，绝不兼做普通文字与装饰；每个色相有固定语义（Flighty 绿准点红延误、Fantastical 日历身份色、HIG Color 原文）。
4. ✦ **动效 200-400ms、可打断、服务空间一致**：微交互 100-200ms、常规过渡 250-400ms、整屏叙事才 >600ms；一切动画进行中可被新意图打断（HIG Motion 原文、WWDC803、M3 token 阶梯）。
5. ✦ **弹跳是含义不是口味**：手势有动量才给 overshoot；tap 驱动的动效 100% 阻尼；弹跳可作为「教用户更深交互」的信号。弹性曲线绝不全局默认。
   （WWDC803 阻尼规则原文、M3 无弹性曲线、HIG "avoid motion for frequent interactions"）
6. ✦ **高频操作零动效化+零等待**：越常发生的事越不该有动画、越不该有 spinner；乐观 UI/本地优先，把网络藏起来。
   （HIG Motion 原文、Linear/performance.dev、Meteor 乐观 UI）
7. **速度是一种感觉，先于视觉**：响应 <100ms 是底线性感受（WWDC803 "look for delays everywhere"）；Linear 把 sync 引擎当作第一行代码。**卡顿本身就是丑。**
8. ✦ **中性色由系统生成，不手挑**：surface/描边/文字灰阶走 tonal palette 算法或令牌阶梯，深浅色与高对比自动成套。
   （M3 动态色、HIG Color "provide light/dark/increased-contrast variants"、Linear 暖灰迭代）
9. **排版节奏 = 少数字号 × 少数字重 × 大留白**：一个 text-style 阶梯走天下（SF text styles、M3 typescale）；避免细字重；正文默认 17pt 级。排版乱=层级乱的根源。
   （HIG Typography、Things 3、Bear、Craft）
10. ✦ **空态、错误态有「人格」且可执行**：空态教用户下一步，错误态说人话+给动作；成功不必庆祝，失败必须解释。
   （HIG Feedback 原文 "people only need to know when it doesn't"、Flighty 人话通知、Arc 空态导览）
11. **输入越少越好：把表单变成一句话**：自然语言/默认值/一步完成。
    （Fantastical NLP 输入、Linear 键盘优先 ⌘K、Things Magic Plus）
12. ✦ **状态反馈内联就地**：状态长在被描述的对象旁边，不打断不弹窗；实时结论+数字，拒绝"已更新"废话。
    （HIG Feedback Mail 例、Flighty、Linear 面包屑状态）
13. **触觉与声音是因果对，不是彩蛋**：用系统语义触觉，强度与视觉反馈强度匹配，好触觉=意识不到但想念；必须可关。
    （HIG Playing haptics 原文、WWDC803 motion+haptics+sound 联动）
14. ✦ **持续振荡是生理级禁忌**：0.2Hz 附近人类最敏感；呼吸/脉动/glow 类循环动画要审查频率、幅度，或干脆只在状态变化瞬间出现一次。
    （HIG Motion visionOS 节原文、NN/g Liquid Glass 批评）
15. ✦ **装饰性材质/glass/粒子必须「用量纪律」**：材质只给功能层；装饰与内容抢分辨率=可用性实测受损（NN/g 对 iOS 26 的批评与 Apple 自家 "use sparingly" 原文互证）。
    （HIG Materials "sparingly"、NN/g 2025 实测报告、Arc 玩味约束在容器内）
16. **设计系统=可实验工具链，不是文档**：token 可在真机/工具里即时调参对比（Linear 内置取色器+feature flag 一键新旧对比；M3 token 机读源码）。**新阶段该先造「调参工具」再刷 UI。**

---

## 3. 对 Sparkle 的直接映射建议

结合主仓 `design_system.dart`/`motion.dart`/`animation_token.dart` 现状与 B-04 截图（均只读），按「最切学习场景」排序：

1. **首页做「减法重构」而非「加法美化」（原则 1/2）**：home 的 9 个 UI 簇按 Linear 「不争夺未赢得的注意力」重排：
   - 唯一主角 = 今日指挥台（当前任务 + 下一步）；Aurora 策略/理解度卡降为可折叠次要层；快捷操作行与输入栏合并（输入栏本身就是万能入口，4 个快捷 pill 是它的降级重复）。
   - 卡片套卡片全部解除：一层 surface 分组（留白分组优先），卡片内 chips 数量上限 2-3。
2. **动效令牌对齐 M3/HIG 阶梯（原则 4/5）**：
   - `AnimationSystem.spring: elasticOut` → 改为 `Curves.easeOutBack`-级轻微过冲（仅手势驱动）或 `Cubic(0.2,0,0,1)` standard；按钮 tap 用 `easeOut` 100-150ms 无弹。
   - `hero: 620ms` 仅保留给真正的整屏叙事（onboarding 入场）；页面转场 250-350ms standard；`micro=120ms` 以下管高频控件。
   - 所有转场接入「可打断」：动画中途新手势可接管（Flutter 侧即 `AnimationController` 可反向/重定向，而非 ignore 新输入）。
3. **呼吸/粒子/glow 全量审计（原则 14/15，直接对应 U-01）**：
   - 4s 呼吸（0.25Hz）落在 HIG 警告的 0.2Hz 敏感带，且 224 处 particle、113 处 glow 意味着同屏多源振荡叠加 → 先做频率/面积预算：**同屏持续动画源 ≤1**；粒子只在「完成时刻」单次爆发（如 Things 勾选），不做常驻环境动画；glow 只给「当前唯一焦点」。
   - 这同时是性能修复（卡顿投诉）：常驻动画是掉帧第一嫌疑。
4. **色彩系统重铸（原则 3/8）**：棕色 accent 现在既当按钮又当正文又当图标。改为：**中性灰阶由 seed 色算法生成 tonal palette（Flutter 有 `material_color_utilities` 包，官方 Dart 实现）**；accent 只标可交互；AI 状态/健康度/稀有度各有独立色相且数量封顶（≤5 个语义色）；浅色下正文用 ≥17pt 级深灰，检查对比度。
5. **学习场景专属的三条「把复杂变一句话」（原则 11/12）**：
   - 任务创建支持自然语言一句话（Fantastical 式），AI 引擎已有理解能力，缺的是 UI 承诺。
   - 进度通知/反馈说人话+带数字（Flighty 式）：「离散数学还剩 12 天，今天完成图论梳理后健康度 91%→94%」。
   - AI 回复流式输出 + 骨架屏只在结构已知时用（原则 6/§1.10）。
6. **圆角/间距语义化（M3 shape 阶梯）**：现散布 18/20/24/28 → 收敛为 5 级（如 4/8/12/16/28），并把「圆角大小=层级」文档化（越浮层越圆）。
7. **触觉语义表（原则 13）**：完成=Success、进入专注=Light、错误=Error、选择器滑动=Selection，全 app 一张表；默认强度低、可在设置关。
8. **先造调参工具再动 UI（原则 16）**：仿 Linear：debug 面板一键切换新旧主题/token、真机即时改色；迁移期 feature flag 并行。这与本仓库「157 平行组件」债务的化解路径吻合：新令牌层并行但可一键对比验收。

---

## 4. 我们最可能违反的前 5 条（基于 U-01 账本 + 代码 + 截图证据）

1. **原则 14/15（持续振荡与装饰纪律）——证据最强**：U-01：home particle 224 处、glow 113 处；代码 `createBreathingController` 4s 周期（0.25Hz，恰在 HIG 点名的 0.2Hz 敏感带附近）。同屏多源常驻动画既违反「同屏持续动画源 ≤1」，也解释「卡顿」投诉（性能与美学的同一个病）。
2. **原则 5（弹跳是含义不是口味）**：`AnimationSystem.spring = Curves.elasticOut` 作为全局 spring，`bounce: elasticOut`、`overshoot: easeOutBack` 可用于任意卡片入场——tap 驱动也弹，违反 WWDC803 阻尼规则原文。
3. **原则 3（颜色只编码一种含义）**：截图证实棕色/米色同时承担「品牌 accent、可交互按钮、正文强调、图标装饰」四种角色；违反 HIG Color 原文与 Flighty/Fantastical 的语义色纪律。
4. **原则 2（结构被感受而非被看见）+ 原则 1（内容优先）**：首页卡片套卡片、边框分隔线密集、9 簇同屏、双层圆角叠圆角——与 Linear 刷新前状态逐条对应（他们原文承认 "borders had quietly proliferated"）。
5. **原则 4（动效时长与打断性）**：`hero=620ms`、`deliberate=600ms`、`pageTransition=350ms easeInOutCubic`（对称曲线起停都拖）超 M3 语义预算；`AnimationConfig` 无打断/反向重定向语义，loading 用 1000ms 线性旋转属「长时间不可打断的等待」——与 HIG "let people cancel motion" 相悖。

（次级嫌疑：三层动作区互相竞争违反原则 1；成功反馈可能过度庆祝违反 HIG Feedback——需 U 组实测确认。）

---

## 5. 逐产品机制速查表

| 产品 | 核心机制关键词 | 最强出处 |
|---|---|---|
| Things 3 | 单色+唯一accent；安静排版；勾选仪式感；浅导航 | culturedcode.com（ADA×2） |
| Linear | 未赢得的注意力不争夺；结构被感受；乐观UI无spinner；token工具链 | linear.app/now 两篇+刷新文 |
| Arc | IA先行；chrome隐形；玩味约束在容器 | arc.net + Inverse |
| Fantastical | 一句话建事件；颜色=身份 | flexibits.com |
| Flighty | 人话通知+数字；延迟预测；时间线分段 | flighty.com（ADA 2023） |
| Bear/Craft | markdown即渲染；chips色语义封顶；结构显形于交互 | bear.app（ADA 2017）、craft.do |
| Apple HIG/WWDC803 | 阻尼规则；可打断；空间一致；0.2Hz禁忌；材质sparingly；触觉因果对 | HIG JSON全文+WWDC字幕 |
| Material You/M3 | tonal palette算法色；时长阶梯50-1000ms；cubic-bezier(0.2,0,0,1)；5级圆角 | material-web token源码 |
| Telegram | 手势驱动+速度接管；共享元素连续 | （知识为主，标注弱源） |
| 乐观UI | 本地状态=唯一渲染源；loading数=质量指标 | Meteor原文+performance.dev |

---

*报告完。产物路径：`v3-output/DL-R1-INTL/RESEARCH.md`。未 commit/push。/tmp 中间产物已计划清理。*
