# A-SPEC5 · 设计语言第五轮：两新面（表单与输入体验 / 搜索与查找）UX 研究 → 自审 → 辩论 → SPEC v1.5 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡第五轮 ｜ 2026-09-22 ｜ worktree **wt252**（分支 wt252-aspec5，base **4e6109d1**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read），file:line 均为 @4e6109d1 实测。
> 前置读透：`v3-output/A-SPEC4/REPORT.md`（第四轮范本，本卡形制对齐它）+ `v3/FLEET-BRIEF.md`（战役上下文）+ `v3-output/DL-R3/SPEC.md`（v1.0 正文，§4 组件语法/§4.5 四态规范/§7 交互流程为本轮两面的条款挂靠点）。本提案**不推翻 v1.0-v1.4 任何条款**，全部为增量/澄清/存量靶登记，编号接续 v1.4 的 N24（N25 起；A-SPEC4 §4 的「N25」系其台账表格标题、非条目号，本轮正式启用 N25）。
> 对标研究方法声明：本会话外部搜索配额耗尽（web_search 429，与前四轮同况），对标做法基于公开常识 + UX 专业判断（沿用 A-SPEC-V1_1/A-SPEC2/A-SPEC3/A-SPEC4 四轮卡内授权先例）；引用代码均为树内实测。
> 两面范围界定（按卡）：①表单与输入体验=全 app 表单盘点（onboarding/目标创建/错题录入/小队创建/反馈等）的字段-必填-校验时机-错误呈现-键盘适配五维 + 输入摩擦审计（分步/草稿/失败保留/智能默认）；②搜索与查找=全 app 搜索域覆盖盘点（有/该有没有）+ 现有搜索实现质量六维（触发/防抖/空态/无结果态/最近搜索/命中高亮）+ 无搜索域的信息找回成本。

---

## 0. 方法与多轮过程记录

照前四轮四步执行：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 面1 按 HIG/Material 表单通则（blur 即时校验、错误三件套=什么错+怎么改+保留输入、标可选不标必填、正确键盘+掩码+autofill）、B2B 顶级表单（Linear/Stripe 的渐进披露+进度可回退）提五维做法；面2 按 iOS 搜索/HIG（搜索框常驻列表顶、即时结果+防抖）、Gmail/Notion（命中 deep link 到上下文并高亮、最近搜索+建议）、Spotlight（零输入即有建议）提六维做法 | §1 两张对标表 | 两面共性直指北极星：**表单是「录入错题/建计划」的入口，搜索是「找回错题/找回对话」的入口——两者都是备考周的高频刚需动线，摩擦一次=复用意愿降一档**；新增两条面性公约：**错误在字段旁即时说（提交前），失败保留现场（提交后）**；**搜索必须完成最后一步（点结果即达上下文），列结果不跳转=搜索做了一半** |
| R2 自审 | 面1 全库 grep（TextFormField 62/TextField 138/Form 17/autovalidateMode/validator 34/keyboardType 14/inputFormatters/autofillHints/commonRequired）+ 20 个表单屏逐屏走查（auth×4、错题、目标向导、任务、计划×2、小队、帖子、seed、光子、guest 升级、偏好×3、资料）；面2 搜索文件全量（*search*.dart×3 + 分域 TextField 溯源 12 域）+ 六维质量逐域核对 + 后端搜索实现走查（error_book_service/seed_library_service/ILIKE/pgvector） | §2 两张全景表 + 差距清单 16 条（带 file:line） | **全库即时校验为零**（autovalidateMode 0 处，全部提交时才报错）；**必填标记零使用**（l10n `commonRequired`『必填』存在但全库 0 引用）；**inputFormatters 0 处**（数字键盘可粘贴进字母）；**搜索四无**（无最近搜索/无命中高亮/无统一无结果态/群消息搜索结果点按死链） |
| R3 辩论 | 16 条逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：采纳 10 / 改写采纳 3 / 砍 2 / 转台账 1 | 砍单主导理由：增分项无数据支撑（高亮/最近搜索）、存量单屏重构为分步属为分步而分步（task_create/exam_sprint）；转台账：洗 text 22 处并入 N15 批次 |
| R4 成文 | 过关差距 → v1.5 增量条目 N25-N29 + 台账行 + top8 | §4 / §5 | v1.5 共 5 条增量，全部为 v1.0-v1.4 的增补/执行令/存量靶登记，无推翻 |

**结构性结论先行（两条）**：
1. **表单是「合规的砖、缺校验的梁」**：错误呈现通道全库统一（行内 validator errorText，34 处 validator 无一处 toast 报校验错），提交失败无一例清空表单（错误后屏保持挂载，内容天然保留）——A-SPEC 四轮治理在「错误呈现」上是达标先例；但**校验时机全库统一在「提交时」**（autovalidateMode 0 处/62 字段），用户永远在点保存后才知道第 2 个字段格式错了；必填/可选无约定（必填零标记，可选两种写法『可选』『选填』混用）；键盘适配覆盖率 ~10%（keyboardType 14/138）且 inputFormatters 全库为零。
2. **搜索是「有入口、无终局」**：12 个可搜域里 9 个有搜索入口，覆盖不算差；但实现质量四散——同一件事（触发）有四种做法（onChanged 即时/500ms 伪防抖/800ms Timer 正规防抖/onSubmitted 提交式），无结果空态有三种做法（专用 noResults 态/误导性空库态/硬编码英文/静默空白），且**唯一的聊天消息搜索做完最后一步就断了**：群消息搜索结果 tap 只 `Navigator.pop`（group_chat_screen.dart:963），不跳消息上下文——用户搜到了，但到不了。

---

## 1. 两面对标研究表（R1）

### 1.1 表单与输入体验 · 对标：HIG/Material 表单通则 / Linear / Stripe Checkout / Things（公开常识，声明见页眉）

| 维度 | HIG/Material 表单通则 | Linear（B2B 表单标杆） | Stripe Checkout（金融级防错） | Things（最小输入） | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 校验时机 | 字段失焦即校验（on blur），错误在字段旁即时出现；提交只做兜底 | 行内即时，改错即消错 | 先验格式后验业务，逐字段放行 | 单字段表单无此问题 | **校验三段制：即时报格式错、提交时兜底必填错、服务端错 toast**——Sparkle 全库只有第二段 |
| 错误呈现三件套 | 什么错+怎么改+保留输入；禁只红框不说话 | 错误信息含修正动作 | 每个错误都带下一步 | —— | Sparkle 的 validator 文案多数只说「请输入 X」，缺「怎么改」（长度/格式约束在文案里缺失）；**保留输入已达标**（§2.0） |
| 必填标记 | 约定一种：业内多数**标可选、不标必填**（可选是少数），入口处一句话说明 | 同左 | 同左 | 几乎无可选字段 | **标可选是正解**——Sparkle 已在用（『章节（可选）』），但『可选』『选填』两词混用、覆盖不全，应统一单词并约定覆盖面 |
| 输入防错 | 正确键盘（email/number）+ 掩码/formatter + autofill | —— | 数字域掩码是底线，粘贴也拦 | —— | **keyboardType 与 inputFormatters 必须成对**——只有键盘是「建议」，formatter 才是「拦截」；Sparkle formatter 全库为零 |
| 长表单 | ≥7 个输入组或跨类目即分步；分步=进度指示+可回退+步内校验 | 创建流程一律分步，步内即校验 | 单页但分区+渐进披露 | 靠「默认值+少字段」消灭长表单 | Sparkle 已有两个好范本（goal 向导 5 步门控/plan Stepper 5 步可跳）；**规范应立「何时该分步」阈值，而非把存量单屏全部重构** |
| 草稿与脏态 | 离开有未保存输入→确认；长表单跨会话自动草稿 | 草稿自动保存是默认 | —— | —— | 脏态保护与草稿是「输入是劳动」的承认——错题录入是拍照+打字的重劳动，丢一次=用户从此只用拍照通道 |

**面性公约提炼**：①**错误即时说**（格式错即时、必填错提交兜底、服务端错 toast 三段制）；②**错误三件套**（什么错+怎么改+保留现场）；③**可选标记统一**（标可选不标必填，单词唯一）；④**键盘+formatter 成对**；⑤**输入是劳动**（脏态保护+分级草稿）。

### 1.2 搜索与查找 · 对标：iOS HIG 搜索 / Gmail / Notion / Spotlight（公开常识，声明见页眉）

| 维度 | iOS HIG 搜索 | Gmail | Notion/Linear | Spotlight | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 入口与触发 | 搜索框常驻列表顶（`UISearchBar`），下拉即现 | 列表顶常驻 | 顶栏常驻 Cmd+K | 零击可达 | **搜索入口在域内常驻**（藏进 appbar 图标的次之）；Sparkle 的 error_list 搜索藏 appbar 图标（error_list_screen.dart:108-115）、群消息搜索藏成员页菜单——入口深度不一 |
| 即时结果+防抖 | 输入即滤（本地域零延迟），服务端域 200-500ms 防抖 | 即时+服务端防抖 | 200ms 防抖 | 即时 | **分界线按数据所在地**：客户端域 onChanged 即时，服务端域 Timer 防抖 300ms 量级——Sparkle 两类域做法互相渗透（客户端域有提交式、服务端域有伪防抖） |
| 无结果态 | 明确说「无 X 结果」+ 清筛选出口 | 同左 | 同左+改写建议 | —— | 无结果≠空库：**专用 noResults 态（回显关键词+清空动作）**；Sparkle 组件已备好（EmptyState.noResults，empty_state.dart:80-89）但全库仅 task_list 一家用 |
| 命中可达 | 点结果 deep link 到内容上下文 | 跳到邮件并滚动定位+高亮关键词 | 跳到块并高亮 | 直达 app 内位置 | **点结果必达上下文**是搜索的终局条款——列结果然后 pop 是半成品；命中高亮是增分项非底线 |
| 最近与建议 | 零输入即示最近搜索/建议 | 搜索历史 chips | 最近过滤条件 | —— | 属增分项：**在无结果痛感出现前不立项**，但「清空搜索词」的 clear 钮是底线（seed_library/user_search 已有） |
| 域覆盖 | 内容型域必有搜索 | —— | 一切列表可滤可搜 | —— | 备考用户的「找回」刚需排序：错题>聊天（问过的题）>任务>资料；**找回成本=无搜索域靠滚动，成本随条目线性涨**——设置页 3898 行无搜索是最大找回黑洞 |

**面性公约提炼**：①**搜索五件套**（常驻入口/按数据地触发/专用无结果态/clear 钮/点结果必达上下文）；②**找回成本红线**（>50 条目或持续增长的内容域必须有搜索——设置/错题/聊天历史是 Sparkle 的三个存量靶）；③高亮与最近搜索是增分项，不做条款。

---

## 2. 自审差距清单（R2，全部 @4e6109d1 实测）

### 2.0 先说达标项（诚实记录——错误呈现与「保留现场」纪律是本轮最大好消息）

- **校验错误全走行内通道**：34 处 validator 全部经 InputDecoration.errorText 行内呈现，**无一处用 toast 报校验错误**；表单失败 toast 只用于服务端提交失败（A-SPEC 前四轮「错误呈现归一」治理在表单域的存量成果）。
- **提交失败内容零丢失**：20 个表单屏逐屏核对，无一例在 catch 里清表单/关屏——错误 toast 后表单原样挂载（add_error_screen.dart:233-241、create_group_screen.dart:135、plan_create_screen.dart:242 等实测）；goal 向导用内联错误横幅（goal_creation_wizard_screen.dart:103-108 `_ErrorBanner`）比 toast 更进一步。
- **智能默认值覆盖好**：task_create 出厂默认（学习类/25 分钟/难度 1/精力 1，task_create_screen.dart:31-41）；add_error 科目默认 math（:46）；goal 向导逐步门控禁用不可继续键（:181-194 `_primaryActionEnabled`）。
- **分步范本在位**：plan_create 用 `Stepper` 5 步可点跳（plan_create_screen.dart:419-423、五步 :473-561）；goal_creation_wizard 5 步+进度条+语义化无障碍标签+步内门控（goal_creation_wizard_screen.dart:42/:95-113/:181-194）。
- **register 密码强度实时反馈**：ValueListenableBuilder 驱动的强度条+文案，输入即变（register_screen.dart:232-269）——全库唯一的「即时反馈」表单元件，N25 的现成范本。
- **auth 四屏 autofill 全配**：autofillHints 全库 9 处全部在 auth 域（register :153/:175/:197、login、forgot、reset），email 键盘 :181——敏感域的正确姿势。
- **textInputAction 链有先例**：add_error 五输入框 next→next→newline→newline→done 且 done 即提交（add_error_screen.dart:469/:485/:499/:521-522）；全库 31 处。
- **对话输入 maxLength 纪律普遍**：chat_input 4000、capsule/memory 200、create_post 500、checkin 500、galaxy 60/240、photon 留言 200（maxLength 全库 10 处，位于高频对话面）。
- **UnsavedChangesGuard 组件在位且已有 3 家采用**：create_library（:117）、add_error（:407）、create_post（:121）——isDirty 驱动的返回确认，组件可用，只是覆盖面没铺开。
- **搜索侧**：task_list 的搜索无结果专用态是全库正解（task_list_screen.dart:349 `EmptyState.noResults(searchQuery:)`）；后端知识节点有 pgvector 语义搜索+关键词兜底双轨（error_book_service.py:584-598 l2_distance、:600-615 fallback）；错题搜索是服务端 API（error_book_repository.dart:74/:89 keyword 参数）不是本地糊弄；群成员列表有搜索（group_members_screen.dart:95-100）；onboarding 有页码记忆（interactive_onboarding_screen.dart:74-90 SharedPreferences 恢复/持久化）——全库唯一的跨会话「草稿」孤例。

### 2.1 面 1 · 表单矩阵（屏 × 五维 × 摩擦判定）

| 表单 | 字段构成 | 必填标记 | 校验时机 | 错误呈现 | 键盘/防错 | 摩擦判定 |
|---|---|---|---|---|---|---|
| 登录（login_screen） | 2 文本 | 无 | 提交时 | 行内 | email 键盘+autofill ✓ | 低 |
| 注册（register_screen） | 3 文本+强度条 | 无 | 提交时（强度实时✓ :232-269） | 行内 | email 键盘+autofill ✓ :153-197 | 中：邮箱格式错在提交后才报 |
| 忘记/重置密码 | 1-2 文本 | 无 | 提交时 | 行内 | autofill ✓ | 低 |
| **错题录入/编辑（add_error_screen，596 行）** | 4 文本+科目 chips+图片上传 | 可选标✓（『章节（可选）』l10n zh:25471） | 提交时（4 组 validator :157-169/:500-531） | 行内+失败 toast（洗 text :238-239） | done 即提交✓ :521；数字域无涉 | **高**：重劳动表单无草稿、题目≥5 字规则提交才知 |
| 目标创建向导（goal_creation_wizard，898 行） | 5 步：意图/类型/动机 3 文本/时程/里程碑 | 步内门控代替标记✓ :181-194 | 步内禁继续键（前置校验）✓ | 内联横幅 :103-108 | 文本域默认 | 低（范本） |
| 任务创建/编辑（task_create，936 行） | 标题+类型+描述+4 下拉+日期+开关 | 无 | 提交时（标题 validator :394） | 行内+失败 toast | AI 建议正规 800ms 防抖 :149-161 | 中：单屏长但默认值好 |
| 计划创建（plan_create，1351 行） | Stepper 5 步（定位/时间/任务蓝图/边界/确认） | 无 | 步内（:668/:694 validator） | 行内+toast（:235/:242） | 日期/时间原生 picker✓ :275/:287 | 低（范本；但 PlanDraft 内存态不落盘） |
| 考试冲刺设置（exam_sprint_setup，740 行） | 名称+chips×4+材料上传+日期+双 slider | 无 | 提交时（:85-92）+提交前置（日期 :492） | 行内+toast（:476-480/:530） | 选择类为主，负担可控 | 中 |
| 小队创建（create_group，339 行） | 名称+类型+简介+标签+冲刺目标 | 可选标✓（『冲刺目标（可选）』zh:4237） | 提交时（:185/:314） | 行内+失败 toast :135 | 文本默认 | 中 |
| guest 升级注册（guest_upgrade） | 4 文本 | 无 | 提交时（:195-253 全 validator） | 行内+info :42 | 无 keyboardType | 中：全文本键入无键盘适配 |
| 光子转账（photon_transfer） | 收件人+数量+留言 | 无 | 提交时（:144/:191） | 行内 | 数量 number 键盘✓ :172，**无 formatter**；留言 maxLength 200 :230 | 中：金融语义域粘贴不拦 |
| 排期偏好（schedule_preferences） | 双 slider+2 文本 | 无 | 提交时 | 行内 | slider 为主✓ | 低 |
| 资料编辑（edit_profile） | 邮箱等 | 无 | 提交时 | 行内 | email 键盘✓ :511、helperText ✓ :518/:708 | 低 |
| 用户画像偏好（user_persona） | 多个对话框内 TextField | 无 | 提交时（空值 info 提示 :1279） | 行内+info/success toast | **动态 keyboardType 映射**✓ :1261/:1655 | 低（正例） |
| 反馈类对话框（task_feedback_dialog/review_appeal/反思等） | 评分+文本 | 选填标✓（zh:4546/:4561） | 提交时/空值即拒 | toast（洗 text :202） | maxLength 200/2000✓ | 低-中 |
| onboarding（interactive_onboarding） | 5 页授权+偏好，无文本表单 | —— | —— | —— | 权限按钮+skip✓；**页码记忆孤例** :74-90 | 低 |

**摩擦专项审计**：①长表单分步：goal/plan 已分步✓，exam_sprint（740 行单屏）与 task_create（936 行单屏）未分步但字段多为选择类+默认值好；②草稿保存：**全库零持久化**（onboarding 页码是孤例；plan_create 的 PlanDraft 是内存模型 plan_draft.dart，聊天输入 `_draftController` 是会话内控制器 chat_screen.dart:188）；③失败保留：全库达标✓（§2.0）；④智能默认：覆盖好✓（§2.0）。

### 2.1b 面 2 · 搜索覆盖矩阵（域 × 六维 × 判定）

| 域 | 搜索 | 触发 | 无结果态 | 命中可达 | 后端 | 判定 |
|---|---|---|---|---|---|---|
| 错题本 | ✓ 服务端 | 500ms 伪防抖（Future.delayed+文本比对，无 Timer 取消，error_list_screen.dart:313-322）；入口藏 appbar 图标 :108-115 | ✗ 混用空库态（:448 `_buildEmptyState` 不区分 keyword） | ✓ 达条目 | SQL ILIKE question_text+**cast(latest_analysis AS String)**（error_book_service.py:923-931，全扫无索引） | 中-差 |
| 任务列表 | ✓ 客户端 | onChanged 即时（:89-94 title contains） | ✓ **EmptyState.noResults 全库唯一采用**（:349） | ✓ 达卡 | 无需 | **正解** |
| 文档库 | ✓ 客户端 | onChanged 即时（document_library_screen.dart:118-119） | 未验证 | ✓ | matchesQuery 语料 contains（document_library_models.dart:319-324） | 中 |
| seed 库 | ✓ 服务端 ilike | **onSubmitted 唯一触发**（seed_library_list_screen.dart:156-157） | ✗ 硬编码英文 4 句（:255-271 'No seed libraries match this filter' 等） | ✓ | ilike name/description（seed_library_service.py:791-792） | 差（i18n 违 N18 同型） |
| 群消息 | ✓ 服务端 | onSubmitted（group_chat_screen.dart:936-944） | ✗ 空列表静默 | **✗ tap 只 pop**（:963） | 群消息搜索 API | **差（死链）** |
| 私信 | **✗ 无 UI**（private_chat_screen.dart 0 处 search） | —— | —— | —— | 数据链已备（community_provider.dart:2155、repository :792-803 searchPrivateMessages） | 差（有链无面） |
| AI 聊天历史 | ✗（chat_screen 0 处 search） | —— | —— | —— | —— | 缺口（量级观察） |
| 用户搜索 | ✓ | onSubmitted（user_search_screen.dart:123） | ✓ 区分初始/无结果 :136-141 | ✓ 选项 sheet | searchUsers API（community_repository.dart:204） | 中 |
| 小队搜索 | ✓ | onSubmitted（group_search_screen.dart:67） | ✓ CompactEmptyState :80-83 | ✓ | groupsSearch API :262 | 中 |
| 群成员 | ✓ | 客户端（group_members_screen.dart:95-100） | —— | ✓ | 无需 | 中 |
| 词汇查询 | ✓ 本地 | onSubmitted（vocabulary_lookup_tool.dart:537-538/:570-571） | —— | ✓ | 本地词典 | 中 |
| 星图节点 | ✓ 客户端 | onChanged（galaxy_search_panel.dart:106） | ✓ 区分零输入提示/无结果文案 :144-158 | ✓ 达节点 | 另有 pgvector 语义轨 :584-615 | 良 |
| 群知识库文件 | ✓ 客户端滤 | 客户端（group_knowledge_base_view.dart:78-113/:543-546） | —— | ✓ | 无需 | 中 |
| **设置（3898 行）** | **✗（0 处 search）** | —— | —— | —— | —— | **最大找回黑洞** |
| 通知中心/insights/记忆面板 | ✗（各 0 处，有筛选/分组） | —— | —— | —— | —— | 可接受（条目少+已有滤） |
| 全局 | ✗ 无全局搜索 | omni bar 是 AI 意图分发不是搜索（unified_omni_bar.dart:444-478 dispatch；hint『告诉我你现在在想什么...』l10n zh:4424） | —— | —— | —— | 定位如此，不立项 |

**找回成本估算（无搜索域）**：设置页 3898 行单 ListView≈200+ 行目，平均找回=全页滚动估 15-30s 且依赖用户记得分组名；AI 聊天历史按会话尾加载（HISTORY-TAIL 交付），找回 3 天前的问题=逐会话点开，估 30-60s；私信无搜索，找回共享的错题链接=逐条滚动。**备考周「上周问过的那道题」是高频回找动作，30-60s 的找回成本直接替代为「再问一遍 AI」——浪费 token 且打断复习流。**

### 2.2 差距清单（16 条）

| # | 差距 | 证据（file:line @4e6109d1） | 违反/衔接条款 |
|---|---|---|---|
| FR-G1 | **即时校验全库为零**：autovalidateMode 0 处/62 TextFormField——所有格式与长度错误都在提交时一次性爆出；register 强度条 :232-269 是唯一即时反馈孤例 | 同左 | 对标 §1.1 校验时机行；错误三件套缺「即时」维 |
| FR-G2 | **必填标记零约定**：`commonRequired`『必填』（l10n zh:2350）全库 0 引用；可选标记两词混用『可选』（zh:2353/:25471）/『选填』（zh:4546/:4561）；必填靠提交后 validator 报错反向得知 | 同列 | 对标 §1.1 必填标记行（标可选是业内正解，但需单词统一+覆盖约定） |
| FR-G3 | **inputFormatters 全库为 0**：数字域（photon 数量 :172、openclaw prefs :280/:306/:324、achievement contract :995、group_chat 邀请码 :292）有 number 键盘无 formatter——粘贴字母可入；无任何掩码 | grep inputFormatters 0 命中 | 对标 §1.1 输入防错行（键盘+formatter 成对） |
| FR-G4 | **脏态保护仅 3/20+ 表单屏**：UnsavedChangesGuard 仅 create_library :117/add_error :407/create_post :121 采用；task_create/plan_create/goal 向导/create_group/exam_sprint/edit_profile/schedule_preferences 均裸奔——goal 向导退出丢掉已跑的意图分析结果 | grep UnsavedChangesGuard 3 文件 | 对标 §1.1 草稿与脏态行；「重试必须保留用户已输入内容」（§4.5）的前置版 |
| FR-G5 | **草稿零持久化**：除 onboarding 页码（interactive_onboarding_screen.dart:74-90）外无任何跨会话草稿；PlanDraft 内存态（plan_draft.dart）；聊天输入退出即丢（chat_screen.dart:188 仅会话内） | 同列 | 对标 §1.1 草稿行；错题录入重劳动场景直接受损 |
| FR-G6 | **提交失败洗 text 22 处**：`ebAddFailed(e)`『添加失败: $e』（l10n zh:25713-25715）、ebUpdateFailed（:25414-25416）、submitFailedWithError(e)（task_feedback_dialog.dart:202）、sendFailedWithError(e)（unified_omni_bar.dart:476）——N15 同型存量；对照 add_error 自身 :137 已用 UserFacingError.from（同屏两种做法并存） | 同列 | N15（洗 text 禁令）批次续记，不立新条 |
| FR-G7 | **键盘适配覆盖 ~10%**：keyboardType 14/138 TextField；textInputAction 31 处；ScrollViewKeyboardDismissBehavior 仅 6 处；user_persona 动态映射 :1655 是正例孤本 | 同列 | 对标 §1.1 输入防错行（登记制处理，不冻结） |
| FR-G8 | **长表单分步不均**：goal/plan 分步✓；exam_sprint 740 行/task_create 936 行单屏——但字段多为选择类且默认值好 | §2.1 专项审计① | 对标 §1.1 长表单行；蓝方主张见 §3 |
| SR-G1 | **群消息搜索结果死链**：结果 tap 只 `Navigator.pop(context)`（group_chat_screen.dart:963），不跳消息上下文；且 catch 静默吞错 results=[]（:941-943）、无结果空态静默、createdAt 裸时间戳直出（:958-959） | 同列 | 对标 §1.2 命中可达行；§4.3 禁悬空精神的搜索版 |
| SR-G2 | **私信搜索有链无面**：searchPrivateMessages 数据链在（community_provider.dart:2155、repository :792-803），private_chat_screen 0 处 search UI——私信找回靠逐条滚动 | 同列 | 对标 §1.2 域覆盖行；共享错题的社交找回动线断裂 |
| SR-G3 | **AI 聊天历史无搜索**：chat_screen 0 处 search；历史按尾加载——找回历史提问成本 30-60s 量级 | §2.1b 找回估算 | 对标 §1.2 域覆盖行；量级未到、挂观察 |
| SR-G4 | **设置页 3898 行无搜索**：unified_settings_screen.dart 0 处 search；全库最长屏唯一找回手段是滚动 | 同列 | 对标 §1.2 找回成本红线（>50 条目域必须有搜索） |
| SR-G5 | **无结果空态四种四样**：task_list 专用态✓（:349）；error_list 搜索无结果时显示『还没有错题』误导空库态（:448 不区分 keyword）；group chat 静默空白；seed_library 硬编码英文 4 句（:255-271）——组件与 l10n 早已备好（empty_state.dart:80-89、l10n emptyStateNoResults*）就是没人用 | 同列 | §4.3 空态规范（为何空必须真因）+ N18 同型英文直出 |
| SR-G6 | **搜索触发四种四样**：客户端域即时（task :89-94/documents :118/galaxy :106）与提交式（vocab :538、user/group :123/:67）混用；服务端域伪防抖（error_list :313-322 Future.delayed 无取消）与提交式（seed :156、group messages :936）混用；唯一正规 Timer 防抖在 task_create 的 AI 建议（:149-161）不在搜索 | 同列 | 对标 §1.2 即时结果+防抖行（按数据地分界） |
| SR-G7 | **零高亮零最近搜索**：命中高亮 0 处（grep highlight 全为叙事模型字段）；最近搜索词 0 处（translation history 是翻译记录功能非搜索词记忆） | grep 实测 | 增分项，蓝方主张见 §3 |
| SR-G8 | **错题关键词检索打在 JSON cast 上**：error_book_service.py:923-931 `func.cast(latest_analysis, String).ilike(...)`——全表扫+逐行 JSON 序列化，错题过千后必慢；对照知识节点已有 pgvector 双轨（:584-615） | 同列 | 北极星：错题本是备考周最高频回找域，检索慢=找回成本线性恶化（跨线：引擎侧改造） |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转台账**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| FR-G1 | 全库提交时校验=用户必错一轮才知格式错，立「首提交后转即时」三段制 | 蓝方：提交时校验一次到位、错误少打扰；即时校验可能输入中途报错惹恼用户 | G1 真差距（autovalidateMode 0 实锤；蓝方顾虑正是业内共识解法——首提交后才开即时，不提前报错）；G2 成本 S（改 autovalidateMode 枚举+首批 5 屏）；G3 高——错题录入/建任务是备考周最高频输入动线，报错晚一轮=每次录入多付一次往返 | **采纳**（N25 主条：首提交后 autovalidateMode.onUserInteraction 三段制） |
| FR-G2 | 必填/可选立统一约定 | 蓝方：现有『（可选）』后缀已经隐性表达约定，改覆盖面动 l10n 与屏 | G1 真差距（必填 0 标记+两词混用实锤）；G2 成本 S（统一为『（可选）』单词+补齐覆盖，commonRequired 可弃用）；G3 中——录入前知道什么必填减少「填一半被拦」 | **采纳**（N25 子句：标可选不标必填、单词唯一『（可选）』） |
| FR-G3 | 数字域 formatter 成对强制 | 蓝方：光子转账等域后端会再验，前端拦截是重复劳动 | G1 真差距（0 formatter 实锤；键盘只是建议、粘贴必穿透）；G2 成本 S（FilteringTextInputFormatter 一行/域）；G3 中——金融语义域（光子）输错金额的后端报错体验差 | **采纳**（N26 子句：键盘+formatter 成对，金融语义域光子先行） |
| FR-G4 | 脏态保护铺满全表单屏 | 蓝方：3 家已用说明组件可用，但铺开是 7 屏机械活；误触发返回确认也烦人 | G1 真差距（isDirty 判定已模式化，add_error :48-52 可复制）；G2 成本 S/屏；G3 高——goal 向导丢意图分析、错题丢半篇题目，都是「输入是劳动」的直接损害 | **采纳**（N27 主条：可输入屏 isDirty 必挂 guard） |
| FR-G5 | 草稿跨会话持久化 | 蓝方：全量表单草稿工程大（序列化每屏状态），先用者寡 | G1 真差距（零持久化实锤）；G2 改写：分级——聊天输入与错题录入两个高频重劳动先做（聊天输入=纯文本 SharedPreferences 即可），全量缓做；G3 高——「昨天写一半的错题」丢了就是录入通道弃用 | **改写采纳**（N27 子句：草稿分级制，首批聊天输入+错题，改造 #8） |
| FR-G6 | 洗 text 22 处清偿 | 蓝方：N15 批次既有，不属新差距 | G1 非新差距（N15 在案）；G2 随批清偿；G3 低 | **转台账**（N15 批次续记一行：表单提交失败类洗 text 22 处，改造 #2 顺手批带两靶） |
| FR-G7 | 键盘适配全量补齐 | 蓝方：14/138 是长尾，全量补齐无验收边界 | G1 半差距（关键域已配，长尾未配）；G2 改写：立「新域必配+存量随触碰」登记制，不冻结不专项；G3 低-中 | **改写采纳**（N26 子句：登记制——keyboardType/textInputAction/dismissBehavior 新增输入域必查项） |
| FR-G8 | exam_sprint/task_create 重构为分步 | 蓝方：两屏字段多为选择类+默认值好，认知负担可控；task_create 的 AI 建议与单屏结构耦合，分步反而打断建议流 | G1 非硬差距（goal/plan 范本已立，两屏可用性尚可）；G2 成本 M 且破坏既有耦合；G3 低——省的时间可忽略 | **砍**（不立条）；「≥4 文本输入组或跨类目才分步」的设计参照写入 N25 依据行，只约束新表单 |
| SR-G1 | 群消息搜索点结果必达消息上下文 | 蓝方：消息流滚动定位需要时间戳定位协议，工程不小；pop 后用户手动滚也是现状可用 | G1 真差距（tap 只 pop 实锤——搜索的终局动作缺失=半成品）；G2 改写：一期先达「会话内滚动定位」（列表按时间索引可二分），高亮二期；G3 中-高——小队共享错题讨论的回找是小队协作价值的核心回路 | **采纳**（N28 子句：点结果必达上下文；改造 #2 一期滚动定位） |
| SR-G2 | 私信搜索 UI 接线 | 蓝方：数据链在但 UI 需要新 sheet，复用群消息形制即可——恰恰说明成本低 | G1 真差距（有链无面实锤）；G2 成本 S-M（复用 group_chat 搜索 sheet 形制 :930-963）；G3 中——共享错题/资料的私信找回是备考协作动线 | **采纳**（N29 存量靶；改造 #5） |
| SR-G3 | AI 聊天历史加搜索 | 蓝方：历史加载刚交付（HISTORY-TAIL），会话量级未到搜索阈值；先做搜索是过度设计 | G1 疑似差距（找回成本 30-60s 实测估算，但条目量级未证）；G2 成本 M（需引擎侧会话检索接口）；G3 中——「问过的题再找回」是真实动线，但等量级 | **改写采纳**（N29 列「应有未有」观察行：会话数>50 或用户反馈触发时转改造卡） |
| SR-G4 | 设置页加搜索 | 蓝方：设置访问低频，3898 行是分组导航问题不是搜索问题 | G1 真差距（全库最长屏 0 搜索实锤；对标红线>50 条目必有搜索）；G2 成本 M（客户端标题索引即可，无需后端）；G3 中——深学/效率档、静默窗等 SPEC 关键开关的可发现性直接受益 | **采纳**（N29 存量靶；改造 #6） |
| SR-G5 | 无结果空态统一归 EmptyState.noResults | 蓝方：组件在但 l10n 文案与各域语境要逐域校对 | G1 真差距（四种四样实锤，误导性空库态最劣）；G2 成本 S（error_list 加 keyword 分支+seed_library 清硬编码英文同批）；G3 中——「搜了没有」被读成「库里没有」会引发误建重复错题 | **采纳**（N28 主条：无结果专用态强制；改造 #1） |
| SR-G6 | 搜索触发按数据地统一 | 蓝方：onSubmitted 在服务端域是省流量的正当选择，不该一刀切即时 | G1 真差距（四样实锤，error_list 伪防抖无取消是最劣实现）；G2 改写：服务端域统一 300ms Timer 防抖（可复制 task_create :149-161 现成模式），客户端域 onChanged 即时，onSubmitted 仅作显式提交补充不禁；G3 中 | **采纳**（N28 子句：触发分界条款；error_list 防抖随改造 #1 同批） |
| SR-G7 | 命中高亮+最近搜索 | 蓝方：错题/词库条目量级与搜索频次未证明需要；高亮在移动端窄列表增益小 | G1 非底线差距；G2 增分项无数据支撑；G3 低 | **砍**（不立条；登记增分项备忘，无结果痛感出现后再议） |
| SR-G8 | 错题检索去 JSON cast、建索引 | 蓝方：属引擎侧工程，A 线规范管不到实现 | G1 真差距（:923-931 全扫实锤；错题是备考周第一回找域）；G2 跨线协作（C/B 线卡承接，A 线只立体验条款+挂改造）；G3 高——错题找回变慢直接反北极星 | **采纳**（N29 存量靶，跨线标注；改造 #7） |

**辩论统计**：16 条 → 采纳 10（FR-G1/FR-G2/FR-G3/FR-G4/SR-G1/SR-G2/SR-G4/SR-G5/SR-G6/SR-G8；其中 FR-G2/FR-G3 为子句并入 N25/N26，SR-G1/SR-G6 为子句并入 N28）/ 改写采纳 3（FR-G5/FR-G7/SR-G3）/ 砍 2（FR-G8/SR-G7）/ 转台账 1（FR-G6）。砍单主导理由：**增分项无数据支撑、存量单屏重构破坏既有耦合**；转台账主导理由：**既有批次条款已在**（N15）。

---

## 4. SPEC v1.5 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0-v1.4：编号规则 + 依据 + 可验收数字；不推翻 v1.0/v1.1/v1.2/v1.3/v1.4 任何条款。编号接续 v1.4 的 N24。生效方式建议沿用 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。

**N25（§4 增补）· 表单校验三段制与可选标记统一**
- **校验三段制**：①格式/长度类错误**即时报**——表单首次提交后转 `autovalidateMode.onUserInteraction`（首提交前不提前报错，规避输入中途打扰）；②必填类错误提交时兜底；③服务端错误走 toast/横幅。行内 errorText 是校验错误唯一呈现通道（存量已达标，守卫禁新增 toast 报校验错）。
- **错误文案三件套**：什么错+怎么改（长度/格式约束进文案）+保留现场；禁裸『请输入 X』式无修正指引文案新增。
- **可选标记统一**：标可选不标必填；单词唯一为『（可选）』（『选填』存量靶：l10n zh:4546/:4561，随触碰统一）；新表单设计参照：≥4 个文本输入组或跨类目才分步（goal/plan 向导为范本）。
- 首批靶（改造 #3）：auth 三屏+add_error+guest_upgrade。
- 【依据：§2.2 FR-G1/FR-G2；§2.0 register 强度条孤例；对标 §1.1 校验时机/必填标记行；§4.5 错误态三句式同源】

**N26（§4 增补）· 输入防错基线（键盘+formatter 成对，登记制）**
- 数字/邮箱/URL/电话语义域的 `keyboardType` 与 `inputFormatters` **必须成对**（键盘是建议、formatter 是拦截，粘贴必穿透）；金融/积分语义域（光子）先行（存量靶：photon_transfer_screen.dart:172）。
- 新增输入域 PR 审查口径（登记制，不冻结基线）：keyboardType / textInputAction / ScrollViewKeyboardDismissBehavior 三项必查；多输入框表单 textInputAction 成链且末位 done 提交（先例：add_error_screen.dart:469-522）。
- 【依据：§2.2 FR-G3/FR-G7；对标 §1.1 输入防错行；§2.0 user_persona 动态键盘正例】

**N27（§4.5 增补）· 表单脏态保护与分级草稿（输入是劳动）**
- **脏态保护**：一切含用户输入的屏（Form 屏/输入对话框除外）必须挂 `UnsavedChangesGuard`（isDirty 判定照 add_error_screen.dart:48-52 模式），返回/切域时确认。存量靶（改造 #4）：task_create/plan_create/goal_creation_wizard/create_group/exam_sprint_setup。
- **分级草稿**：跨会话草稿按输入劳动强度分级——一级（聊天输入框、错题录入正文）自动持久化本地、返回即恢复、发送/保存成功即清；二级（长表单其余字段）随触碰补；草稿条目必须在恢复时可见（恢复提示或高亮），禁静默注入。
- 【依据：§2.2 FR-G4/FR-G5；§4.5「重试必须保留用户已输入内容」的前置延伸；对标 §1.1 草稿与脏态行；onboarding 页码记忆（interactive_onboarding_screen.dart:74-90）为机制先例】

**N28（§4 增补）· 搜索面五件套**
- ①**常驻入口**：内容型域搜索入口在列表顶/appbar 常驻可见（藏二级菜单为存量债，随触碰上移）；②**触发分界**：客户端域 onChanged 即时滤；服务端域 ≥300ms Timer 防抖（模式照 task_create_screen.dart:149-161，**禁 Future.delayed 文本比对式伪防抖**，存量靶 error_list_screen.dart:313-322）；onSubmitted 仅作显式提交补充；③**无结果专用态**：搜索无结果一律 `EmptyState.noResults(searchQuery:)`（回显关键词+清空动作），**禁与空库态混用、禁硬编码英文、禁静默空白**（存量靶：error_list_screen.dart:448、seed_library_list_screen.dart:255-271、group_chat_screen.dart:951）；④**clear 钮**：有词即显（seed_library/user_search 已达标）；⑤**命中可达**：点结果必达内容上下文（一期允许滚动定位，高亮为增分项）——**禁 pop-only 死链**（存量靶：group_chat_screen.dart:963）。
- 【依据：§2.2 SR-G1/SR-G5/SR-G6；§4.3 空态规范「为何空」真因要求；对标 §1.2 搜索五件套；EmptyState.noResults 组件与 l10n 已备（empty_state.dart:80-89）】

**N29（§7 增补）· 搜索覆盖红线（找回成本）**
- 条目 >50 且持续增长的内容域必须有搜索；按备考回找频次排序的存量靶与观察行：
  - 设置（unified_settings_screen.dart，3898 行 0 搜索）→ 改造 #6；
  - 私信（数据链已备 community_repository.dart:792-803，UI 缺）→ 改造 #5；
  - 错题检索质量（error_book_service.py:923-931 JSON cast 全扫，跨线：引擎侧去 cast+索引）→ 改造 #7；
  - AI 聊天历史搜索 → **观察行**（会话数 >50 或用户反馈触发时转改造卡）。
- 全局搜索不立条（omni bar 定位为 AI 意图分发，unified_omni_bar.dart:444-478，不与搜索混轨）。
- 【依据：§2.2 SR-G2/SR-G3/SR-G4/SR-G8；对标 §1.2 域覆盖/找回成本行；北极星「错题是第一回找资产」】

**N30（§10.5 台账新增行，随 v1.5 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N25 校验三段制+可选标记 | 未开工 | 改造 #3 |
| N26 键盘+formatter 成对 | 未开工（登记即生效） | 改造 #2 顺手批 |
| N27 脏态保护+分级草稿 | 未开工 | 改造 #4/#8 |
| N28 搜索五件套 | 未开工 | 改造 #1/#2 |
| N29 搜索覆盖红线 | 未开工 | 改造 #5/#6/#7 |
| FR-G6 表单提交失败洗 text 22 处 | 台账续记（N15 批次，本卡不重复立项） | 随改造 #2 顺手批 |
| FR-G8 exam_sprint/task_create 分步化 | **砍**（防重复立项：字段选择类为主+默认值好，不重构） | —— |
| SR-G7 命中高亮/最近搜索 | **砍**（增分项备忘：无结果痛感出现后再议） | —— |
| AI 聊天历史搜索 | 观察行（量级触发） | N29 |

---

## 5. 改造清单（按北极星收益排序 top8，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。与前轮清单关系：本表为两新面的 v5 批次，前轮未清偿项不受影响。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **搜索无结果态归一（N28 首案）** | error_list_screen.dart:448 加 keyword 非空分支走 EmptyState.noResults；:313-322 伪防抖改 Timer 防抖；seed_library_list_screen.dart:255-271 硬编码英文 4 句迁 l10n 并改用 noResults 态 | 错题「搜了没有」不再读作「库里没有」 | 手测：搜不存在词出现带关键词的专用态；l10n 键无英文直出 | S |
| 2 | **群消息搜索命中可达（N28 子句）** | group_chat_screen.dart:963 tap 改为关 sheet 后按 msg.createdAt 在消息列表滚动定位（一期）；:941-943 catch 改 UserFacingError 提示；:958-959 时间戳走既有格式化 | 搜到即到；禁 pop-only | 手测：搜索→点结果→列表滚至该消息附近；错误路径有人话 toast | S-M |
| 3 | **首批即时校验（N25 主条）** | login/register/forgot/reset + add_error + guest_upgrade 六屏：提交失败后置 autovalidateMode.onUserInteraction；校验文案补「怎么改」（长度/格式约束入文案） | 首提交后改错即时消错；错误文案含修正指引 | widget test：提交后输入合法值错误即消；手测六屏 | S-M |
| 4 | **脏态保护补齐（N27 主条）** | UnsavedChangesGuard 补挂 task_create/plan_create/goal_creation_wizard/create_group/exam_sprint_setup 五屏（isDirty 模式照 add_error_screen.dart:48-52） | 半填表单返回必确认 | 手测：五屏填入内容后返回弹确认；空表单返回不弹 | S |
| 5 | **私信搜索接线（N29）** | private_chat_screen 复用 group_chat 搜索 sheet 形制（:930-963），数据链用现成 searchPrivateMessages（community_provider.dart:2155）；命中可达按改造 #2 同制 | 私信可搜可回找 | 手测：私信搜关键词出结果且点达上下文 | M |
| 6 | **设置页搜索（N29）** | unified_settings_screen.dart 加顶部搜索框：客户端标题/分组索引即时滤（照 documents onChanged 模式 :118-119），无结果走 noResults 态 | SPEC 关键开关（深学/效率、静默窗）可搜达 | 手测：搜「静默」直达推送设置分区 | M |
| 7 | **错题检索去 JSON cast（N29，跨线）** | backend/app/services/error_book_service.py:923-931：keyword 检索限定 question_text+ai_analysis_summary 具名列并评估 pg_trgm/全文索引；latest_analysis JSON cast 列退出检索或物化 | 错题千条级检索毫秒级 | 引擎测试：1k 错题 keyword 查询 <50ms；走 C/B 线卡承接 | M |
| 8 | **草稿首批（N27 子句）** | 聊天输入框（chat_screen.dart:188 `_draftController`）与 add_error 正文四控按会话/编辑态为 key 持久化本地；恢复时提示「已恢复上次未发送内容」；发送成功即清 | 重劳动输入跨会话不丢 | widget test：杀屏重进草稿恢复且发送后清空 | M |

**被砍项备忘**（防后续卡重复立项）：exam_sprint_setup/task_create 分步化重构（FR-G8——字段选择类为主+默认值好，goal/plan 向导已是分步范本，单屏不动）；命中高亮与最近搜索词专项（SR-G7——增分项，登记无结果痛感触发条件后再议）；全局搜索入口（omni bar 定位为 AI 意图分发，与搜索分轨，N29 已明示不混轨）；设置页信息架构重构（3898 行分组问题是 M 级 UI 工程，搜索是 S-M 级止痛，先止痛）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC5/REPORT.md`（本文件，位于 worktree wt252）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作；未 commit / 未 push
- [x] /tmp 无驻留（全程未写 /tmp）；无启动进程/模拟器/浏览器，无 HEAVY 资源占用；worktree 内无 build/.dart_tool 产生
- [x] 引用代码均为 @4e6109d1 实测（rg/read）；计数类结论（TextFormField 62/TextField 138/Form 17/validator 34/autovalidateMode 0/inputFormatters 0/autofillHints 9@auth4 屏/keyboardType 14/textInputAction 31/maxLength 10/UnsavedChangesGuard 3 屏/commonRequired 0 引用/EmptyState.noResults 全库唯一采用 task_list/private_chat_screen 0 处 search/unified_settings_screen 3898 行 0 search）均为 grep 实测；backend 引用（error_book_service.py:584-615/:887-931、seed_library_service.py:791-792）为文件实读；无编造引用
- [x] 对标研究未做外部浏览（搜索配额 429），方法声明已按前四轮先例如实标注
