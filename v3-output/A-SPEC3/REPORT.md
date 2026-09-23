# A-SPEC3 · 设计语言第三轮：两新面（错误与空态全景 / 信息密度与渐进披露）UX 研究 → 自审 → 辩论 → SPEC v1.3 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡第三轮 ｜ 2026-09-23 ｜ worktree **wt233**（base **507070a3**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read），file:line 均为 @507070a3 实测；守卫基线数为 `n9_raw_exception_leak_baseline.json`（冻结 @a025e82a）、`check_n9_raw_exception_leak.py` 实测值。
> 前置读透：`v3-output/A-SPEC2/REPORT.md`（第二轮范本，本卡形制对齐它）+ `v3-output/A-SPEC-V1_1/REPORT.md`（第一轮）+ `v3-output/DL-R3/SPEC.md`（v1.0+v1.1 正文，含 N1-N8 落地回写）+ `v3-output/V13/REPORT.md`、`V13-RETEST/REPORT.md`（截图编号引用）+ `scripts/guards/check_n9_raw_exception_leak.py`（N9 守卫本体）。本提案**不推翻 v1.0/v1.1/v1.2 任何条款**，全部为增量/澄清/存量靶登记，编号接续 v1.2 的 N14（N15 起）。
> 对标研究方法声明：本会话外部搜索配额耗尽（web_search 429），对标做法基于公开常识 + UX 专业判断（沿用前两轮卡内授权先例，A-SPEC-V1_1/A-SPEC2 同款声明）；引用代码均为树内实测，V13 实证均为报告编号实读。
> 两面的范围界定（按卡）：①错误与空态全景=mobile/lib **全功能域**（40 域逐一过守卫 owner 覆盖度 + 重点域读源码）三态呈现盘点；②信息密度与渐进披露=信息最重的三面（galaxy 星图 / chat 主屏 / sprint 冲刺屏）深查。sprint/galaxy/chat 面本体已在 v1.0 §7/§8 与前两轮立面，本轮只补增量，不重复立面。

---

## 0. 方法与多轮过程记录

照前两轮四步执行：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 面1 按 Linear/Notion/Flighty/Arc（+Stripe/HIG 错误文案惯例）提六维做法；面2 按 Obsidian graph/Notion toggle/Linear 折叠/Duolingo 单主角提密度与披露做法 | §1 两张对标表 | 两面共性与前两轮同源：**诚实仍是门票**；新增两条面性公约：**三态不齐=该数据面没做完**；**渐进披露的敌人不是信息多，是「收起的方式不统一」** |
| R2 自审 | 全 40 域 owner 覆盖度扫（EmptyState/SparkleSkeleton/CustomErrorWidget 计数）+ 重点域读源码（galaxy/chat/sprint/seed_library/shop/knowledge/notification_center/aurora/tools/auth）+ N9 守卫本体与基线核对 + V13/V13-RETEST 实证对表 | §2 三态全景矩阵 + 差距清单 10 条（带 file:line） | **裸异常长出第三条逃逸通道（provider-state 通道，90 处/20 文件）**——N9 双维守卫（arb 占位符+l10n 调用参）对它全盲；异常→人话映射已碎片化为**三个 owner** |
| R3 辩论 | 10 条逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：采纳 5 / 改写采纳 4 / 砍 1 / 转台账 1 | 被砍主导理由：修复后无实证危害（galaxy 叠层）；转台账项卡在产品决策（种子数据来源声明） |
| R4 成文 | 过关差距 → v1.3 增量条目 N15-N18 + 台账行 + top7 | §4 / §5 | v1.3 共 4 条增量，全部为 v1.0-v1.2 的增补/澄清/守卫扩维登记，无推翻 |

**结构性结论先行（两条，均为「管线级」）**：
1. **裸异常长出第三条逃逸通道：provider-state 通道**。N4 封了代码内插值（`'$_loadError'`），N9 封了 arb 占位符与 l10n 调用参两条门——但 provider 层把原始异常 `e.toString()` **存进 state 错误字段**再由 UI 渲染的第三条通道完全无人把守：`error: e.toString()` 全库 **90 处、20 个 provider/状态文件**（grep 实测清单见 §2.2）；`notification_list_screen.dart:77` 证明正解已存在（`UserFacingError.from(error)` 先人话化再进 l10n），但它不是义务而是巧合。更隐蔽的是：**owner 组件 `CustomErrorWidget` 被喂原始异常文案**（task_list_screen.dart:332 / marketplace_screen.dart:62 `message: state.error!`）——形式走了 owner，内容仍是裸异常，「owner 面板 ≠ 人话内容」的契约缺口。
2. **异常→人话映射三 owner 并存**：`UserFacingError.from`（core/errors/user_facing_error.dart:34，字符串匹配+`[ERR-*]` 码）、`ErrorMessages.getLocalizedMessage`（core/utils/error_messages.dart:8，另一套字符串匹配 CN+EN）、galaxy 私有 `_galaxyLoadErrorMessage`（galaxy_screen.dart:3793，**类型化枚举映射——三者中唯一不依赖异常文本形态的正解形制**）。同一「网络/超时/鉴权」判定逻辑在 core 两处双写（§9.4-1 同型），判定集不同（一处含 `CLIENT_CLOSED`、一处含中文模式）——同一异常走不同入口给不同文案只是时间问题。

---

## 1. 两面对标研究表（R1）

### 1.1 错误与空态全景 · 对标：Linear / Notion / Flighty / Arc（+Stripe 错误文案与 HIG 惯例）

| 维度 | Linear | Notion | Flighty | Arc | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 空态哲学 | 空态=教学时刻：「Create your first issue」单 CTA+一句这里会出现什么 | 空页面直接给可操作模板（empty state 即内容） | 无订阅时如实展示可用面+升级入口，不伪造数据 | 新标签页默认给搜索+最近，绝无「空白死胡同」 | 空态三要素（为何空+单一 CTA+不悬空）是全品类默认；**空态是产品在说话，不是留白** |
| 错误三句式 | 错误 toast 短句+可点动作（retry/undo），不阻断流程 | 断线=顶部黄条一句话+自动重连，正文仍可读 | 航班数据拉不到=明说「暂时拿不到」+下拉刷新，绝不显示假航班 | 出错页保留用户上下文，撤销优先于确认 | what+impact+next 三句式是Stripe/HIG 共识；**重试永远可发现** |
| 裸异常 | 零先例——所有错误都有人话层 | 零先例 | 零先例 | 零先例 | 四家无一裸异常；异常细节→日志/诊断码，用户面永远人话（N9 精神的品类背书） |
| 加载态 | 行内 spinner 只用于小动作，面板级一律骨架/占位 | 块级占位贴布局 | 航班卡先出框架后填数据 | 页面骨架分级渐进 | 骨架贴布局（§4.4.1）是面板级共识；spinner 只该出现在按钮内/行内 |
| 降级与离线 | 乐观 UI+失败回滚提示 | 缓存可读+重连横幅 | 最后已知数据+「最后更新于 X」时间戳 | —— | **「最后已知+时间戳」>「空白」>「假数据」**——Sparkle 离线横幅（V13 步骤14 PASS）已达第一档 |

**面性公约提炼**：①**三态不齐=该数据面没做完**（loading/empty/error/content 缺一即未完成，§4.5 D9 的执行口径）；②错误文案=what+impact+next，异常细节永不入户（N9/N4 的泛化执行令）；③空态=教学时刻，禁裸「暂无」单行居中（有主从之分：屏级空态必须带 CTA，卡内空态可一句话）。

### 1.2 信息密度与渐进披露 · 对标：Obsidian graph / Notion toggle / Linear 折叠 / Duolingo 单主角

| 维度 | Obsidian graph | Notion | Linear | Duolingo | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 密度哲学 | 一屏一主角（当前聚焦邻域），全图是缩出去的另一档 | 全部信息可折叠但默认只开当前层 | 键盘唤起、鼠标悬停才出的二级，默认面极净 | 每屏一个英雄数字，其余收 Tab | **首屏=主角+≤3 支撑**（§3.3 既有条款）；信息不删，只降级（收起≠砍掉） |
| 披露控件 | 缩放阈值驱动（LOD）——同一个控件语义贯穿全图 | toggle 块全站同款（三角+同动画） | 折叠全部同 chevron 同时长 | —— | **收起的方式必须统一**：同一家 app 里「展开」只有一种视觉语法（v1.0 §4.2.2 只定了折叠卡 chevron，未定展开族 owner） |
| 深埋判定 | —— | 页面 >3 层就要侧栏面包屑 | 快捷键直达任意深度 | 奖励位永远 ≤1 跳 | 深埋上限 3 跳（V13 A-03 光子入口 3 层深即反例，已修 @V13-MAJORS） |
| 数字密度 | —— | 数据库视图：密读件带口径行 | —— | 数字永远配单位标签 | §6.3/N6 既有条款，本轮无新增 |

**面性公约提炼**：①渐进披露的敌人不是信息多，是**收起的方式不统一**（用户要重新学每个折叠件）；②LOD/缩放门控是画布类信息密度正解（galaxy 已达标，见 §2.0）；③深埋以 3 跳为红线（MOBILE 线共识「功能没入口等于不存在」的密度侧表达）。

---

## 2. 自审差距清单（R2，全部 @507070a3 实测）

### 2.0 先说达标项（诚实记录——本轮最大好消息是前两轮改造的落地痕迹遍布三面）

- **galaxy 三态全景是全 app 最完整的单屏**：loading=`_StatusPanel`（带三 highlights+loader，galaxy_screen.dart:3078-3091）、error=人话映射+重试（:3093-3108，`_galaxyLoadErrorMessage` 类型化映射 :3793-3805，SPEC-C #4 修复注释在案）、empty=带三 highlights+「去排任务」CTA（:3109-3125）。画布侧 LOD 五级（`resolveGalaxyLod` star_map_painter.dart:17-27）+标签密度函数 `_labelAlpha`（:2051-2072）=画布类渐进披露正解。
- **sprint surface 前两轮改造全部落地**：服务端 daysLeft 单算+口径就地标注（sprint_screen.dart:224-242/:263-267 注释在案）、任务空态三要素 EmptyState（:197-204）、屏级错误三件套（:206-211）、倒计时三档 pill（:300-306，SPEC-FIX N5 口径统一）、成就 take(3)+viewAll 截断（:463-468）、裸件全迁 owner（:408-410/:283-287 注释在案）。
- **chat 消息面渐进披露体系成熟**：助手消息周边件全部 disclosure 化——`CollapsibleWidgetWrapper` 默认收起为 chip、横排 2-3 枚/行（chat_bubble.dart:1595-1616 注释「saving significant viewport space」）；纠正条事件门控（仅最新助手消息且无活跃 run，chat_screen.dart:1702-1704）；metadata tray 单选展开（assistant_message_metadata_tray.dart:34/:239）；全族受 `chatPureMode`+transparency 偏好门控（chat_bubble.dart:849-853）。V13 后 RETEST-MINORS 又修掉阶段胶囊 14px 溢出与流式/历史渲染分叉（commit 09d311cc）。
- **notification_center 三分支齐全**：loading 骨架/空态/筛选空态三分（notification_center_screen.dart:186-200）。
- **V13 实测空态四连 PASS**：驾驶舱空态「诚实空态+引导卡」（截图 50/63）、断网横幅+缓存不裸崩（67）、伙伴空态 CTA（56）、小队聊天空态（61）。
- **V13 密度缺陷已修**：D-10 统计卡入纵向流（galaxy_screen.dart:3356-3364 修复注释在案）、D-11 扇区标签 96px 控制列让位（RETEST-MINORS）、A-03 光子入口 1 跳达（profile tile，@V13-MAJORS）。
- **N9 守卫已落地且 ratchet 生效**：arb `{error}` 现值 zh+en 各 155（=310），低于基线 316；守卫自检含注释行豁免与模型字段防误伤（check_n9_raw_exception_leak.py:77-79/:209）。

### 2.1 三态全景矩阵（40 域 owner 覆盖度扫 + 重点域读源码）

> 覆盖度=域内引用 owner 的文件数（grep 实测，非人工清点）；「直出」=本轮实锤的裸异常/裸 spinner 渲染点。

| 域 | 空态 owner | 骨架 owner | 错误 owner | 三态判定 | 要点 |
|---|---|---|---|---|---|
| galaxy | 1 | 0（用 _StatusPanel 面板） | 0（用 _StatusPanel） | **优** | 三态全+LOD；贡献横幅 error 分支无形的半缺口（PD-G2） |
| chat | 2 | 1 | 3 | **优** | 披露体系成熟；无直出 |
| plan(sprint) | 6 | 6 | 3 | **优** | 前两轮改造全落地 |
| community | 16 | 15 | 10 | 良 | A-SPEC2 已立面，N9 遗留调用在冻 |
| home | 10 | 3 | 3 | 良 | notification_list:77 是人话化正解示范位 |
| task | 3 | 2 | 3 | 良 | task_list:332 owner 面板喂裸文案（EE-G1 组成） |
| error_book | 2 | 4 | 3 | 良 | N12 色阶单源已落地（commit e7cf28e1） |
| notification_center | 0（内联三分支） | 2 | 0 | 良，但 :266 双份直出（EE-G2） |
| seed_library | 1 | 2 | 2 | **差** | provider 14 处 toString+detail:151 直出+destructive 重试（EE-G1/G2） |
| knowledge | 0 | 0 | 0 | **差** | detail:50 `'$error'` 直出+:842/:886 toString 存 state（EE-G1/G3） |
| shop | 0 | 0 | 0 | **差** | 空态分支内混排 error 红字（:128，EE-G6） |
| simulation | 1 | 0 | 0 | 差 | :977 `_InlineErrorBanner(state.error!)`（EE-G1 组成） |
| aurora | 0 | 0 | 1 | 差 | 会话 sheet:877 `Text(_error!)`（EE-G3） |
| tools | 8（私有 ToolEmptyState） | 0 | 0 | 中 | 两 tool body 级裸 spinner 首路径（EE-G5）；ToolEmptyState 形制合格（icon+title+description+action 四件齐，tool_shell.dart:831-840） |
| insights/leaderboard/plan_history 等 | 各 1-6 | — | — | 良 | 抽样合格（self_anchor:74/learning_dashboard:70） |
| 其余 24 域（auth/cognitive/calendar/memory/goal/documents…） | 有 | 有 | 有 | 抽样未见图 2.2 类直出 | 覆盖度数据在案；auth 错误链走 ErrorMessages 人话（login_screen.dart:139-146） |

### 2.2 差距清单（10 条）

| # | 差距 | 证据（file:line @507070a3） | 违反条款 |
|---|---|---|---|
| EE-G1 | **provider-state 裸异常通道（系统性，90 处/20 文件）**：`error: e.toString()` 存入 state 后由 UI 渲染。存量头部：auth_provider 15 / seed_library_provider 14 / notification_center_provider 14 / subtask_provider 6 / shop_provider 6 / error_book_provider 5 / simulation_provider 4。直出实锤 9 处：seed_library_detail_screen.dart:151（`Text(state.error!)`）、marketplace_screen.dart:62 与 task_list_screen.dart:332（owner 面板 `message: state.error!`）、simulation_screen.dart:977（`_InlineErrorBanner(message: state.error!)`）、shop_screen.dart:128、knowledge_detail_screen.dart:50（`'$error'`）+ :842/:886（`_error = e.toString().replaceFirst(...)`，PH-G4 同型存活）、aurora_core_session_sheet.dart:877、diagnostic_quiz_screen.dart:110（`SnackBar(Text(error.toString()))`，且裸 SnackBar 非 SparkleSnackBar）、admin_operations_screen.dart:416 | §4.5/N4 X6 精神；N9 守卫双维全盲（dim1 只扫 arb、dim2 只扫 `l10n.\w+(` 调用参——provider 状态字段是第三条通道） |
| EE-G2 | **双份错误显示残留**：通知中心错误态先 `loadingFailed(error)` 一行再裸 `Text(error)` 第二行 | notification_center_screen.dart:261-268（:266 裸行）；与 A-SPEC2 EB-G1（error_list 同屏两次）同型 | §4.5/N4（A-SPEC2 EB-G1 裁决的同型未清项） |
| EE-G3 | **重试钮错用 destructive 样式**：加载失败重试是恢复性动作，却用 `ButtonVariant.destructive`（红=破坏语义） | seed_library_detail_screen.dart:154-159 | §1.5 槽位语义单义（error 槽原义=失败/错误呈现，非「恢复动作」着色）；§4.2 控件层级语法 |
| EE-G4 | **异常→人话映射三 owner 并存（结构性 #2）**：UserFacingError（字符串匹配+`[ERR-*]` 码拼进首读文案）vs ErrorMessages（另一套字符串匹配，CN+EN 集）双写判定逻辑；galaxy `_galaxyLoadErrorMessage` 类型化映射是正解形制但私有 | core/errors/user_facing_error.dart:34-102；core/utils/error_messages.dart:8-60+；galaxy_screen.dart:3793-3805；调用面：UserFacingError ≈10 文件、ErrorMessages 4 文件+auth 链 | §9.4-1 同一口径双写（判定集漂移风险）；§6.5 owner 登记制（映射 owner 未登记） |
| EE-G5 | **tools 两 tool body 级裸 spinner 首路径**：整屏加载=居中转圈，无骨架无阶段感 | focus_stats_tool.dart:86-88、notes_tool.dart:218-220；同类 diagnostic_quiz_screen.dart:141 | §4.4.2（裸 spinner 禁新增于首屏主路径） |
| EE-G6 | **shop 空态分支混排错误直出**：空态（Icon+「暂无物品」）内嵌 `if (state.error != null)` 红字 raw error——空态与错误态不互斥，违反四态分工；shop 域三类 owner 全零使用 | shop_screen.dart:112-131（:128） | §4.5 D9 分工矩阵（状态互斥分支）；§4.3/§4.4.1 |
| EE-G7 | **贡献横幅 error 无形**：GalaxyContributionBanner 有 `.loading` 形却无 error 形——出错即 `SizedBox.shrink()` 静默消失（有 loading 态=用户预期它存在，「不显示」造成「坏了但不说」） | galaxy_screen.dart:3380-3390（:3386-3390 error 分支）；对照 loading 形 :3384-3385 | §4.5 四态完整性（回归/降级为一等状态的精神）；对标 §1.1 Flighty「明说暂时拿不到」 |
| EE-G8 | **D-12 残项：种子数据来源不明**：「我们从 OS.pdf 里找到了 5 颗知识星」对零上传新用户出现且不解释来源；RETEST-MINORS 已修 InkWell 热区并诚实披露「source copy needs backend seed flag」未修 | V13 REPORT D-12（截图 51）；V13-RETEST REPORT:81；commit 09d311cc message「Honest disclosure: D-12 'OS.pdf source copy' not fixed」 | §4.3 空态诚实性（首用面出现不明数据=伪首用空态）；FLEET-BRIEF #4 精神 |
| PD-G1 | **渐进披露控件三制并存**：chat 私有 `CollapsibleWidgetWrapper`（AnimatedSize+chip 行）与 core organism `ExpandableSection`（全库仅 2 处使用：transparency_panel/accountability_detail）并行注册；另 AnimatedSize 裸用 18 处、showModalBottomSheet 15 处各自为政。「展开」无唯一 owner 与统一语法（chevron 方向/动画时长/展开态样式） | collapsible_widget_wrapper.dart:13-66；core/design/components/organisms/expandable_section.dart；grep：ExpandableSection( 全库 2 处 / AnimatedSize( 18 处 / showModalBottomSheet 15 处 | §4.2.2 精神的展开族空白（折叠卡已定，披露件未定）；§6.4 组装 owner 登记制 |
| PD-G2 | **galaxy 顶叠层纵排密度**：D-10 修复后 stats（scale<0.32 门控）+贡献横幅+掌握空横幅+draft 卡+draft 指示器同列纵排，理论最多 5 件叠画布上部 | galaxy_screen.dart:3352-3433（:3367 scale 门控/:3392/:3400/:3417 各条件分支） | ——（有门控+条件渲染，实际同现 ≤3；列作对照项非违规，辩论见 §3） |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转台账**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| EE-G1 | provider 通道是 N9 封口后的主漏斗，90 处存量+9 处直出实锤，必须立第三维守卫 | 蓝方：90 处多在次级域；CustomErrorWidget 面板已给「人话外壳」，内容粗糙但可用；全量清偿动 20 文件成本高 | G1 真差距（V25「Unsupported operation」类直出通道仍开：诊断 quiz SnackBar 直出 toString、knowledge `'$error'` 全是实弹；owner 面板喂裸文案=契约缺口非风格）；G2 收益高/成本 M 分批（守卫维 ratchet 冻结 90 起只降不升，主路径域 task/plan/auth/seed_library 先行）；G3 高——备考周任何一次加载失败都是信任时刻，「Exception: …」直出毁诚实签名 | **采纳**（N15 立条；改造 #1 首批+#2 直出点清零；存量分批 ratchet） |
| EE-G2 | 通知中心双份错误显示 | 蓝方：一处 S 级 | G1 成立；G2 成本 S（删一行）；G3 中 | **采纳**（并入改造 #2 同批） |
| EE-G3 | 重试钮 destructive 语义错位 | 蓝方：红色重试=醒目，用户找得到 | G1 真差距（§1.5 槽位单义：destructive 红=「此动作有破坏性」，重试恰好相反；且同屏 error 图标已用 error 红——双红竞争）；G2 成本 S；G3 低-中 | **采纳**（并入改造 #2 同批，一行改 variant） |
| EE-G4 | 映射三 owner 双写判定集，必须单源 | 蓝方：两个 core 类各有场景（UserFacingError 吃 Object、ErrorMessages 吃 errorCode+技术串），合并要梳理 14 文件调用面；galaxy mapper 私有但正确 | G1 真差距（判定集已漂移：`CLIENT_CLOSED` 只在 UserFacingError、中文模式只在 ErrorMessages——同一异常两入口两文案）；G2 全量合并=M-L 但**唯一入口条款+新调用禁新增**=S；G3 中——错误文案一致性是信任的次级支撑 | **改写采纳**：N16 立条款（映射逻辑单源+类型化形制为推荐 owner，新域禁私有映射）；两 core 类物理合并转台账 M 选项（改造 #3 的选项 B） |
| EE-G5 | tools 两 tool 首路径裸 spinner | 蓝方：tool 面板秒开，骨架出现时间极短 | G1 真差距（§4.4.2 明面条款；弱网下秒开不成立——备考场景地铁/宿舍 Wi-Fi 常态弱网）；G2 成本 S（骨架贴 ToolMetricRow 布局）；G3 中 | **采纳**（改造 #6，与 EE-G5 同文件批） |
| EE-G6 | shop 空态混排错误+域零 owner | 蓝方：shop 兑换主面在 photon redeem（已达标），shop 屏本身低频 | G1 真差距（四态互斥是 D9 铁律；混排=用户同时读「暂无物品」和一串异常）；G2 成本 S（拆分支+走 CustomErrorWidget）；G3 低-中 | **采纳**（并入改造 #2 同批） |
| EE-G7 | 贡献横幅 error 静默消失 | 蓝方：装饰统计，消失无害于诚实（不显示≠撒谎） | G1 半差距（有 loading 形=立了「我会出现」的预期，error 形缺失=预期违背；但信息价值低）；G2 成本 S（补一个「暂不可见」形）；G3 低 | **改写采纳**：并入改造 #7 galaxy 同文件批（补 error 微文案形），不占独立条款 |
| EE-G8 | 种子数据来源声明 | 蓝方：RETEST-MINORS 已裁定需后端 seed source flag，本卡零代码；UI 补一句是掩盖数据层语义问题 | G1 真差距（实证在 V13 截图 51）；G2 修复在 C 线数据面（D8 依赖）；G3 低-中（新用户首用困惑，一次性） | **转台账**（观察行：后端 seed source flag 落地后 UI 随批补来源一句） |
| PD-G1 | 披露控件三制并存，展开语法不统一 | 蓝方：CollapsibleWidgetWrapper 在 chat 内自洽；ExpandableSection 仅 2 处不成气候；强迁=工艺债 | G1 真差距（展开族 owner 空白属实——§4.2.2 管了折叠卡没管披露件；但存量 18 处 AnimatedSize 多为布局动画非披露门面，不全是违规）；G2 条款+S（新披露件必须走唯一 owner，AnimatedSize 限布局动画），存量触碰即迁；G3 低-中（扫描效率，长尾） | **改写采纳**（N17 立条款+新代码生效；无专项清偿） |
| PD-G2 | galaxy 叠层纵排 5 件太多 | 蓝方：D-10 修复后已是受控纵流+scale 门控+全条件渲染，实际同现 ≤3；无任何用户实证说「塞太多」 | G1 非差距（修复后的形态正是对标 §1.2 Obsidian 分档披露的正解；无实证不定罪）；G3 低 | **砍**（不立条）；贡献横幅 error 形缺失另案（EE-G7 已采纳） |

**辩论统计**：10 条 → 采纳 5（EE-G1/EE-G2/EE-G3/EE-G5/EE-G6）/ 改写采纳 3（EE-G4/EE-G7/PD-G1）/ 砍 1（PD-G2）/ 转台账 1（EE-G8）。砍单主导理由：**修复后无实证危害**（galaxy 叠层）；转台账项卡在**跨线产品决策**（种子数据 flag）。

---

## 4. SPEC v1.3 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0-v1.2：编号规则 + 依据 + 可验收数字；不推翻 v1.0/v1.1/v1.2 任何条款。生效方式建议沿用 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。编号接续 v1.2 的 N14。

**N15（§4.5/N4/N9 扩展）· provider 错误状态零异常文本（第三逃逸通道封堵）**
- state/provider 的 UI 可达错误字段（`error`/`errorMessage` 类）**禁存异常文本**（`e.toString()`/`'$e'`/`replaceFirst('Exception: ', '')` 洗.text 类），只允许三类值：`null` / arb 人话 key 的本地化结果 / 类型化错误码（交给唯一映射 owner 翻译，见 N16）。渲染侧 `Text(state.error!)`、`CustomErrorWidget.page(message: state.error!)`、SnackBar 直出 `error.toString()` 同禁——**owner 面板不豁免内容契约**。
- 机检第三维（并入 `check_n9_raw_exception_leak.py`）：`error:\s*(e|err|error|ex)\.toString\(\)` 赋值面扫描 ratchet，现值 **90 处/20 文件**冻结只降不升（清单：auth_provider 15/seed_library 14/notification_center 14/subtask 6/shop 6/error_book 5/simulation 4/task 3/sprint_actions 3/cognitive 3/其余 11 文件各 1-2）；直出 9 靶随首批清偿。
- 存量清偿顺序：主路径域（task/plan/auth/seed_library/shop/simulation）先行 → 次级域分批。正解示范位：notification_list_screen.dart:77（`UserFacingError.from` 先行）。
- 【依据：§2.2 EE-G1/G2/G3/G6；§0 结构性发现 1；N4/N9 的通道封堵同型；对标 §1.1 裸异常零先例】

**N16（§6.2/§6.4 增补）· 异常→人话映射单一 owner（类型化优先）**
- 全 app 异常→用户文案的映射逻辑**单源**：core 层唯一 owner（现状双写靶 `UserFacingError` 与 `ErrorMessages` 收敛，物理合并转台账 M 选项；过渡期两者至少共享同一判定表）——**新域禁再建私有映射**。
- 形制裁决：**类型化枚举映射为正解**（galaxy `_galaxyLoadErrorMessage` 的 `GalaxyErrorType → arb key` 形制迁入 core 作为推荐实现），字符串模式匹配为遗留兼容层；`[ERR-*]` 诊断码保留（A-3 diagnosability 设计），但降为次级显示（消息尾小字/长按详情），不与首读文案混排。
- 【依据：§2.2 EE-G4；§0 结构性发现 2；§9.4-1 双写禁令的映射域同型；galaxy 类型化先例（SPEC-C #4 已验收）】

**N17（§4.2 增补）· 渐进披露控件形制（展开族唯一 owner）**
- 「收起一段内容、点开展开」类披露件的 owner 收敛为**一个** core organism（`ExpandableSection` 为现名，`CollapsibleWidgetWrapper` 收编为其 chat 域特化或参数化变体）；统一语法：折叠态=chip/标题行+chevron（旋转动画 M1，§4.2.2 同款）、展开动画统一时长档、展开态样式单源。
- `AnimatedSize` 降级为**布局动画原语**（容器高度过渡），禁再作披露门面（自装折叠态）；`showModalBottomSheet` 维持「二级面」定位不属披露件。新披露件零容忍，存量 18 处 AnimatedSize 触碰即迁，无专项。
- 【依据：§2.2 PD-G1；§4.2.2 折叠卡先例的展开族补全；对标 §1.2 Notion/Linear「同一家只有一种展开」公约】

**N18（§6.5/§9.1 守卫增补）· presentation 层双语内联零新增（`zh ? '…' : '…'` ratchet）**
- 文案唯一入口是 arb（§6.5 既有条款）的机检落地：presentation 层 `zh ? '中文' : 'English'` 式双语内联三元 **禁新增**；扫描维冻结现值（presentation 层代表靶：goal_detail_l10n.dart 31 处/evidence_drawer 11 处/task_preview_panel 12 处/today_growth_status_card 11 处；全库 253 处，其中 data/mock 层占大头另列白名单评估）。
- 本条是登记令非清偿令：存量分批迁 arb 转台账，新代码零容忍即生效。
- 【依据：§2.1 矩阵「暂无」10 处直填+grep `zh ? '` 全库 253 处实测；§6.5 arb 纪律既有条款的守卫化；N11 扫描根扩维同制】

**N19（§10.5 台账新增行，随 v1.3 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N15 provider 通道 ratchet（90 冻结）+直出 9 靶 | 未开工 | 改造 #1/#2 |
| N16 映射单源（条款即生效） | 未开工（物理合并转台账） | 改造 #3 |
| N17 披露控件 owner（新代码生效） | 未开工（登记即生效） | 触碰即迁 |
| N18 presentation 双语 ratchet | 未开工 | 改造 #4 |
| N9 存量清偿进度（上轮台账行续记） | 守卫在冻：arb 310/316（zh+en 各 155）、调用面 bareCatchVar 80+catchVarToString 79 共 82 文件未动 | A-SPEC2 改造 #2 批 |
| V13 D-12 种子来源声明 | 观察行（待后端 seed source flag） | EE-G8 |
| ErrorMessages/UserFacingError 物理合并 | 观察行（M 选项） | 改造 #3 选项 B |

---

## 5. 改造清单（按北极星收益排序 top7，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。与 v1.1/v1.2 清单关系：本表为两新面的 v3 批次，前轮未清偿项不受影响。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **provider 通道封堵·主路径批（N15 首批）** | task/sprint_actions/seed_library/simulation/shop providers 的 `error: e.toString()` 赋值点（约 30 处）；`check_n9_raw_exception_leak.py` 增 dim3 赋值面 ratchet（90 冻结） | 主路径域错误字段改存人话 key 或类型码；渲染点改经 UserFacingError/映射 owner；dim3 守卫落地+manifest 登记 | dim3 ratchet 跑绿；主路径域 `Text(state.error!)` 模式清零；新赋值零容忍 | M |
| 2 | **直出 9 靶清零批（含 EE-G2/G3/G6）** | knowledge_detail_screen.dart:50/:842/:886；aurora_core_session_sheet.dart:877；diagnostic_quiz_screen.dart:110（改 SparkleSnackBar.error）；notification_center_screen.dart:266（删裸行）；seed_library_detail_screen.dart:151+:157（文案人话化+variant.destructive→outline/secondary）；shop_screen.dart:112-131（空/错拆互斥分支）；marketplace_screen.dart:62/task_list_screen.dart:332（message 经人话化） | 全部直出点改三句式或经映射 owner；重试钮样式归位 | 各直出靶 grep 清零；widget test：Object/toString 产物不出现于 Text | S-M |
| 3 | **映射单源（N16）** | 选项 A（S）：新条款生效+galaxy `_galaxyLoadErrorMessage` 迁 core 作类型化 owner 实现；选项 B（M，转台账）：UserFacingError 吸收 ErrorMessages 判定表，14 文件调用面收编 | 判定表单源；新域禁私有映射写入 §6.4 owner 登记表 | 两入口对同一异常样本集输出一致文案的断言测试；新映射 PR 守卫提示 | S（A）/ M（B） |
| 4 | **presentation 双语 ratchet（N18）** | 守卫新增 `zh ? '` 扫描维（presentation 根，白名单：data/mock 层）；首批清 goal_detail_l10n.dart（31 处，域内聚合文件天然适合批量迁 arb） | ratchet 冻结+首批迁移 | 守卫跑绿+manifest；goal_detail_l10n 迁后 l10n coverage 守卫不回退 | S（守卫+首批）/ M（全量，转台账） |
| 5 | **tools 加载骨架** | focus_stats_tool.dart:86-88、notes_tool.dart:218-220 | body 级裸 spinner→贴布局骨架（ToolMetricRow 形状）或最小占位件 | 骨架→内容无布局跳变（手测/ golden）；弱网模拟首帧有结构 | S |
| 6 | **披露控件 owner 登记（N17 落地）** | core/design/components/organisms/expandable_section.dart 语法补全（chevron 旋转+动画档）；CollapsibleWidgetWrapper 标注为 chat 域特化并在 §6.4 owner 表登记 | 条款生效：新披露件走唯一 owner；AnimatedSize 只作布局动画 | owner 表登记行；新披露件 PR 审查口径一条 | S |
| 7 | **galaxy 贡献横幅 error 形（EE-G7）** | galaxy_screen.dart:3386-3390 + GalaxyContributionBanner 补 error 构造 | error→「贡献数据暂不可见」单行微形（与 .loading 同高度，防布局跳变） | error 态有可见形且不跳变（手测） | S |

**被砍项备忘**（防后续卡重复立项）：galaxy 顶叠层纵排密度专项（D-10 修复后已是受控纵流+scale 门控，无实证危害，PD-G2 裁决）；贡献横幅撤件案（error 形补齐即可，EE-G7 改写采纳替代）；`CollapsibleWidgetWrapper` 强迁 ExpandableSection 物理合并（chat 域特化登记即可，N17 触碰即迁）；admin_operations_screen.dart:416 裸 error 专项（管理面，随 N15 次级域批次顺带）；arb `{error}` 310 处与调用面 159 处专项清偿（N9 台账已有 owner，本卡只续记进度不重复立项）；seed 数据弹窗 UI 单侧补文案（EE-G8 转台账，等后端 flag）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC3/REPORT.md`（本文件，位于 worktree wt233）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作；未 commit / 未 push
- [x] /tmp 无驻留（全程未写 /tmp）；无启动进程/模拟器/浏览器，无 HEAVY 资源占用
- [x] 引用代码均为 @507070a3 实测（rg/read）；N9 基线数为 `n9_raw_exception_leak_baseline.json` 实测解析（arb 316/调用面 159）；arb 现值 155+155 为 grep 实测；V13 引用为报告编号实读；RETEST-MINORS 修正以 commit 09d311cc message 为证；无编造引用
- [x] 对标研究未做外部浏览（搜索配额 429），方法声明已按前两轮先例如实标注
