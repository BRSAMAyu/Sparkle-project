# A-SPEC2 · 北极星第二轮：四个未深审面（社群 / 光子经济 / 错题本 / 我的画像）UX 研究 → 自审 → 辩论 → SPEC v1.2 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡第二轮 ｜ 2026-09-22 ｜ worktree **wt222**（base **6043725c**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read），file:line 均为 @6043725c 实测；守卫基线数为 `scripts/guards/dl_spec_ratchet_baseline.json`、`ui_design_tokens_baseline.json`、`ux_component_convention_baseline.json` 实测值。
> 前置读透：主仓 `v3-output/A-SPEC-V1_1/REPORT.md`（第一轮范本，本卡形制对齐它）+ `DL-R3/SPEC.md`（v1.0 定稿，含 v1.1 N1-N8 增补回写）。本提案**不推翻 v1.0/v1.1 任何条款**，全部为增量/澄清/存量靶登记，形制对齐 v1.0/v1.1。
> 对标研究方法声明：对标软件做法基于公开常识 + UX 专业判断（按卡内授权，未做外部浏览）；引用代码均为树内实测。
> 四面的范围界定（按卡）：①社群面=小队列表/详情/自习室在场/错题分享（D-COMM-3/4/5，wt167/191 产物）；②光子经济面=余额/兑换/状态/入口（D-COMM-2 + PHOTON-STATUS，wt168/207 产物）；③错题本面=列表/详情/分享入口（error_book 全域，从未深审）；④我的/画像面=onboarding 引导流/个人成长区/统计（wt207 假曲线修复后的现状）。onboarding 与 profile 本体已在 v1.0 §8.7/§8.9 立面，本轮只补增量，不重复立面。

---

## 0. 方法与多轮过程记录

照第一轮四步执行：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 每面 2-3 对标（社群=Discord/Slack/Notion；经济=Duolingo 宝石/Forest/游戏商店惯例；错题本=Anki/Quizlet/GoodNotes 复盘流；画像=Duolingo profile/Strava 年报/Streaks），提炼可迁移做法 | §1 四张对标表 | 四面共性与第一轮三面同源：**诚实是门票**（假零/假曲线/裸异常任何一项就摧毁该面）；新增两条面性公约：**社交面=邀请环即生命线**；**资产面=流水入口是一等公民不是彩蛋** |
| R2 自审 | 逐面读真实代码（squad 双屏 1324 行 + share 对话框 213 行；photon 全域 1970 行 + shop 关联件；error_book presentation 3400+ 行；statistics_card/onboarding/profile 成长区）+ 三份守卫基线核对 | §2 差距清单 19 条（带 file:line） | **wt167-207 新卡产物（squad 双屏/redeem 屏/统计卡）合规度显著高于存量面**——SPEC 立规后建的代码自觉走 owner；但存在一个**系统性新逃逸通道（arb `{error}` 裸异常插值，全 arb 158 处）**和两个**幽灵面（光子流水页不可达、transfer 路由零入口）** |
| R3 辩论 | 19 条逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：采纳 10 / 改写采纳 5 / 砍 4 | 被砍主导理由：ratchet 已管住的存量字面量专项（2 条）、北极星加权低或无用户证据（2 条） |
| R4 成文 | 过关差距 → v1.2 增量条目 N9-N13 + 台账行 + top10 v2 | §4 / §5 | v1.2 共 5 条增量，全部为 v1.0/v1.1 的增补/澄清/扩容登记，无推翻 |

**结构性结论先行（两条，均比第一轮单条结构性发现更「管线级」）**：
1. **裸异常直出长出了第二条逃逸通道**：v1.1 N4 封的是代码内插值（`'$_loadError'`），而 wt167 起的新代码把原始 `Object error` 作为**arb 占位符参数**传入（`squadLoadFailed(error)` → zh 模板「加载失败：{error}」）——守卫模式 `'\$_\w*[eE]rr'` 对此全盲，且全 arb 已有 **158 处 `{error}`**（`lib/l10n/app_zh.arb` grep 实测）。错误文案层变成了裸异常的合法入户门。
2. **治理面地图第二次落后于产品**：v1.1 N1 补了 sprint（第 10 面），但 D 线六卡新建的社群/光子两域与从未入册的错题本域**仍不在 9+1 surface 名单、不在 UX-COMP 扫描根**（`scripts/guards/check_ux_component_convention.py:44-58` 实测：community/photon/error_book 全部缺席；`ux_component_convention_baseline.json` 无任何四域条目）。「新功能免检通道」正在重演第一轮 sprint 的剧本。

---

## 1. 四面对标研究表（R1）

### 1.1 社群面 · 对标：Discord / Slack / Notion（社区与群组惯例）

| 维度 | Discord | Slack | Notion | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | 服务器→频道两层；成员列表常驻右侧，在线状态用「圆点+状态语」 | 工作区→频道；huddle 在场用头像堆叠+绿点，轻量不点名 | 空间→页面；成员管理收进设置，页面分享走「Share」单钮 | 群组面主角是「人+共同目标」，管理件收边；Sparkle 小队详情「榜/自习室/分享」三段式方向正确 |
| 邀请环 | **邀请链接是一等公民**：一键复制/失效期/次数限制，邀请即增长回路的主轴 | 同上（invite link + QR），入群零手输 | Share 按钮 → 复制链接 → 权限说明一句话 | **群组产品的生命线=邀请成本趋近零**；手输 UUID 入群无先例 |
| 在场感 | 语音频道「谁在室」实时名点；离场无惩罚 | huddle 结束自然消散 | —— | 在场=低风险轻信号：显示谁在+可选时长；**绝不惩罚缺席**（Sparkle 已做对） |
| 比较与身份 | 等级榜弱化、身份卡（profile）强化；排行榜类 bot 必带「你自己排第几」高亮 | 无比较文化 | —— | 任何榜的**第一可读问题是「我在哪」**——自我行高亮是全品类默认（Duolingo 联赛同样） |
| 空态/错误 | 无服务器→给「创建/探索」双入口；加载失败给 retry | 空频道给引导 | —— | 空态=为何空+单一 CTA（Sparkle squad 列表已达标） |

### 1.2 光子经济面 · 对标：Duolingo 宝石 / Forest 金币 / 游戏商店（Steam/Apple 钱包惯例）

| 维度 | Duolingo 宝石 | Forest | 游戏商店/钱包 | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | 余额常驻商店 header；赚取/消费路径分离清晰 | 金币只经真实专注产生；商店独立屏 | 余额+充值+**交易历史**三件套，历史一键可达 | 资产面三件套（余额/流水/出口）是钱包类最低配置；**流水不可达=钱包不可信** |
| 数字诚实 | 余额不足时按钮置灰+差多少明示，绝不显示假零 | 树枯死如实呈现；金币数永远真实 | 购买前确认框=价格+得到什么+不可逆提示 | **「未知≠0」**：加载失败显示「暂不可用」而非 0；Sparkle FLEET-BRIEF #4 同款红线 |
| 消费出口 | 单一消费语义（宝石只买 Streak freeze 等学习向物品） | 金币只买新树种（与核心行为同构） | —— | 价值增量红线：光子只经「学出会员」出口（D-COMM-2 已对齐，本面最强达标项） |
| 反馈 | 购买瞬间一次性确认动画；不足/上限各有专属文案 | 种植动效单次 | 确认→执行→终态三段；上限/不足/成功文案分明 | 有界终态（成功/基数不足/余额不足/月顶/错误）Sparkle redeem 屏已做齐——是全四面对标里**唯一全面达标的面** |
| 透明度 | 宝石账单可查（shop 内） | 金币历史在统计页 | **每一笔都有流水**，含退款/赠送来源 | 「可兑换基数」这类审计口径数字必须能下钻到流水——Sparkle 已有审计重放后端，缺的是 UI 入口 |

### 1.3 错题本面 · 对标：Anki / Quizlet / GoodNotes（复盘流惯例）

| 维度 | Anki | Quizlet | GoodNotes/纸质复盘 | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | 牌组→今日应复习数置顶；「全部/待复习」双视图 | 学习集→掌握进度（「还在学/已掌握」分档） | 错题本=按章节组织的手写册 | 「全部+待复习」双 Tab（Sparkle 已有）方向正确；待复习数=中性信息非告警 |
| 节奏 | 复习反馈 4 级（again/hard/good/easy）但**配人话副标签**；评分即时生效 | 掌握度用分档语言（Mastered/Still learning），**不用裸百分数审判** | 翻页即复盘 | Sparkle 三级（忘/模糊/记得+hint）已是人话化先例；**掌握度百分数应配档位语言与口径** |
| 层级 | 到期数用中性/蓝色徽章；**红色只给 suspension/出错** | 分档色柔和，无惩罚红 | —— | 「待复习」与「低掌握」用 error 红是错位——红色应留给失败/错误（SPEC §1.5 原义）；**连续量的分档色阶需要单一 owner** |
| 反馈 | 复习完成给「今日完成 N 张」结论+数字；无羞辱 | 测试后给鼓励性总结 | —— | 失败不羞辱（§6.1）在错题本场景权重最高——错题天然关联「做错了」，文案必须归因流程不归因人格（Sparkle 文案已达标） |
| 分享 | 导出牌组（.apkg）给同学是常规操作 | 学习集可分享协作 | 拍照/打印错题（小猿等 K12 惯例） | 错题分享到学习小队是真实场景（D-COMM-5 已做）；**对外分享卡暂缓**（见辩论 E-G6） |

### 1.4 我的/画像面 · 对标：Duolingo profile / Strava 年度报告 / Streaks

| 维度 | Duolingo profile | Strava 年报/周报 | Streaks | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 信息架构 | 身份层（头像/称号/成就）与进度层分离；统计块每块有明确口径 | 年报**只在有数据的年份生成**；周报有轴有单位 | 统计网格每格带单位标签 | 身份/进度分层 Sparkle prestige 区已做；**「无数据的统计卡」对标软件的做法是不渲染，不是永久空态占位** |
| 节奏 | 成就解锁一次性动画 | 年报是仪式（M5 级一次性） | 无循环装饰 | 与 v1.0 §2.6 一致，无新增要求 |
| 诚实 | 从「X% 流利度」撤回到诚实单位（他们的自我修正先例） | 不造曲线；空周期如实留白 | —— | wt207 假曲线修复方向与 Duolingo 自我修正完全同构；但**永久空态卡是诚实的另一种浪费** |
| 引导 | ≤3 屏见到第一课；每屏一个动作 | —— | 新手引导可全跳 | onboarding 页数纪律（§8.9 必达② ≤5 步）是品类硬惯例 |

**四面共性提炼（作为 v1.2 立条依据）**：
1. **诚实仍是最大公约数**：假零、假曲线、裸异常、伪可达——四面对标软件零先例；
2. **社交面公约**：邀请环趋零成本 + 榜单自我行高亮 + 在场不惩罚缺席；
3. **资产面公约**：余额/流水/出口三件套齐备 + 未知不显示为 0 + 有界终态；
4. **连续量（掌握度/倒计时）分档色阶须单源**（Anki 分档、v1.1 N5 倒计时先例的泛化）。

---

## 2. 自审差距清单（R2，全部 @6043725c 实测）

### 2.0 先说达标项（诚实记录，四面的新卡产物质量是本轮最大好消息）

- **squad 双屏**：CustomErrorWidget/EmptyState/SparkleCardSkeleton/GraphiteCardSurface/SparkleButton 全 owner 化，零 Color 字面量、零 fontSize 字面量、零裸组件（squad_list_screen.dart / squad_detail_screen.dart 全文走查）；三段独立加载/错误面「单面失败不拖垮整屏」（squad_detail_screen.dart:66-91）；<3 人降级 self_view_only→自我锚路由（:177-203）；并列名次 1,1,3 如实直显（:250）；`has_ledger_data=false` 显示「无账本数据」不伪装 0%（:273-277）；在室=success 在线语义、榜=info 数据可视化语义正确（:408/:184）。
- **自习室在场（ROOM-PRESENCE）**：前台 30s 心跳续期 + 后台即停 + 服务端 TTL 90s 诚实衰减 + `is_stale` 只作弱提示（squad_detail_screen.dart:297-353/:588-598）——「看着自习室=在自习室」的诚实信号设计是对标表里最好的那档。
- **photon_redeem_pro 屏**：服务端真值优先链（status 快照→响应揭示→展示常量兜底，photon_redeem_pro_screen.dart:124-137）；余额/可兑换基数两数诚实分列、基数未揭示不产数字（:226-238）；基数<余额差额如实注明转账来源（:244-252）；不足预判与引擎拒绝同序（:139-145）；有界终态五分支（:58-76）；确认对话框+无购买暗示——**D 线价值增量主面的门面是全四面最合规的单屏**。
- **统计卡假曲线修复**：硬编码 FlSpot 已换诚实空态，且在代码注释里写明禁止回落（statistics_card.dart:5-9/:66-67）；光子入口已无条件常驻「我的」成长区（profile_screen.dart:686-695，V13-MAJORS M-03）；profile 数据面错误卡带重试+注销出口理由注释（:78-80）。

### 2.1 社群面

| # | 差距 | 证据（file:line @6043725c） | 违反条款 |
|---|---|---|---|
| CO-G1 | **arb `{error}` 裸异常插值通道（系统性）**：squad 域 11 处调用把原始 `Object error` 传入 l10n 模板，模板直出异常细节（zh「加载失败：{error}」） | squad_list_screen.dart:72/:287/:418；squad_detail_screen.dart:73/:173/:376/:432/:480/:642；share_error_to_squad_dialog.dart:57/:83；arb `app_zh.arb:1429/:1437/:1456/:1510/:1526/:1547/:1556/:1572/:1585`；全 arb 计 **158 处 `{error}`** | §4.5/N4 X6 的 arb 逃逸通道（N4 只堵代码内插值）；§6.2 禁直出清单精神 |
| CO-G2 | **邀请环断裂**：加入小队=手输小队 ID（`_JoinSquadDialog` 单 TextField），但 `SquadInfo.id`（squad_models.dart:85）在全 UI **零显示零复制点**，squad 详情屏无任何邀请/分享小队入口——邀请人自己都拿不到 ID | squad_list_screen.dart:377-466；squad_detail_screen.dart 全文无 invite/clipboard；`/usr/bin/grep invite\|Clipboard` 双屏零命中 | §8 无社群蓝图（结构性）；对标 §1.1 邀请环公约；D 线增长回路的产品级断点 |
| CO-G3 | **榜单无自我行标识**：`_LeaderboardRow` 渲染名次/名字/完成度，无 isSelf 高亮；模型只有 userId（squad_board_models.dart:12/:35），端上也未比对当前用户 | squad_detail_screen.dart:231-288 | 对标 §1.1「我在哪」公约；§0.2 社群面必达项缺失的组成（无蓝图所致） |
| CO-G4 | 日期手工拼接绕唯一入口：`'${date.year}/${date.month}/${date.day}'` | squad_list_screen.dart:372-373（`_formatDate`） | §6.4 时间格式规范/X3（`date_formatting.dart` 唯一入口） |

### 2.2 光子经济面

| # | 差距 | 证据（file:line @6043725c） | 违反条款 |
|---|---|---|---|
| PH-G1 | **光子流水页不可达（幽灵屏）**：`/photon/history` 路由已注册，但唯一 push 点在死代码 `PhotonBalanceCard` 里；兑换屏/资产卡均无流水入口——审计重放口径（FLEET-BRIEF「可兑换基数=审计流水重放」）的数字用户无法下钻核对 | photon_routes.dart:16-23；photon_balance_card.dart:28-31（唯一引用，该组件全仓无挂载）；photon_redeem_pro_screen.dart 全文无流水入口 | §5.1「功能没入口等于不存在」（MOBILE 线共识）；对标 §1.2 资产面三件套 |
| PH-G2 | **PhotonBalanceCard 死代码带病**：渐变卡+glow 阴影、裸 `TextStyle(fontSize:14/20/28)`、加载用裸 `LinearProgressIndicator`、错误文案顶替数字位、`'${balance?.balance ?? 0}'` **失败伪装成 0**、`auto_*` 机器生成 key | photon_balance_card.dart:32-51（gradient+boxShadow）/:79-111（裸 TextStyle）/:86-94（LinearProgressIndicator）/:95-103（error 顶数字位）/:106（`?? 0`）/:78/:97/:146（auto_* keys）；基线 `photon_balance_card {gradientLiteral: 1}` | §1.2.1 阴影/§3.1.4/§4.4.2/FLEET-BRIEF #4（不造默认值）/§6.5-3 key 命名；死代码本身=治理盲资产 |
| PH-G3 | **transfer 幽灵路由**：`/photon/transfer` 注册在路由表但全仓零 push 引用；屏本体为旧栈（`Theme.of`/`DS.xl` 裸 padding/`ActionChip` 带 backgroundColor 直填），且 P2P 转账触反刷敏感区（后端 `transfer_in` 已被排除出可兑换基数） | photon_routes.dart:24-32（注册）；`/usr/bin/grep "PhotonRoutes.transfer"` 全仓零命中；photon_transfer_screen.dart:348-365（ActionChip backgroundColor 直填） | 反刷红线（FLEET-BRIEF #2）相邻；幽灵面=可深链误入的未审入口 |
| PH-G4 | provider 裸异常入 UI 状态：`e.toString().replaceAll('Exception: ', '')` 存为 error 文案，流水页直出 | photon_provider.dart:55/:148；transaction_history_list.dart:69（`state.error!` 直出） | §4.5/N4 X6 |
| PH-G5 | 流水页首屏裸 spinner：首次加载与分页尾均 `CircularProgressIndicator`，无骨架贴布局 | transaction_history_list.dart:52-54/:121-128 | §4.4.1/§4.4.2（photon 不在 UX-COMP 扫描根，rawSpinner 免检中） |
| PH-G6 | 流水时间格式化绕唯一入口：`DateFormat('HH:mm')` 硬编码模式 + `_formatDateHeader` 自算今天/昨天 | transaction_history_list.dart:282/:180-200 | §6.4/X3 |

### 2.3 错题本面

| # | 差距 | 证据（file:line @6043725c） | 违反条款 |
|---|---|---|---|
| EB-G1 | **双份裸异常直出**：列表错误态先经 `loadingFailed(error)`（{error} 模板）显示一次，再原样显示 raw `error` 第二次；详情屏传 `error.toString()`；删除失败两处拼 `e`/`e.toString()` | error_list_screen.dart:475+**:483**（同屏两次）；error_detail_screen.dart:122（`error.toString()` 传入）/：913-918（raw 显示）；:549（`'${l10n.errorBookDeleteFailed}: $e'`）/：1009（`errorBookDeleteFailedMessage(e.toString())`，arb:2373 为「删除失败：{error}」） | §4.5/N4 X6（列表屏同时踩 CO-G1 通道+代码内直出双通道） |
| EB-G2 | **raw 组件群（守卫免检中）**：`FilledButton(.icon)`×10（list/detail/review 三屏）、`FilterChip`×2、`ActionChip`×1、裸 `Card`×3 | error_list_screen.dart:491/:647/:605/:615/:413；error_detail_screen.dart:683/:879/:922/:986；review_screen.dart:448/:593/:723/:826/:853；error_card.dart:74/:432；UX-COMP 扫描根不含 error_book（check_ux_component_convention.py:44-58） | §4.1.1/§4.2 owner 唯一；系统性风险同第一轮 S-G1（sprint 入守卫前的形态） |
| EB-G3 | **掌握度分档色阶口径双写 + error 槽挪用**：0.8/0.5 两阈值在两文件各自硬编码；且 `<0.5 → DS.error`——「尚未掌握」不是「失败/错误」，语义槽被连续量挪用 | error_card.dart:281-284（`_getMasteryColor`）vs error_detail_screen.dart:730-734/:757-761（inline 三元，同阈值异实现） | §1.5 槽位语义单义；§9.4-1 同一口径双写（色阶口径的 §9.4 同型）；v1.1 N5 的连续量同型未决 |
| EB-G4 | fontSize 字面量 ~13 处（10-18pt 散布三屏一卡） | error_list_screen.dart:196/:240/:352/:477/:485；error_detail_screen.dart:886/:908/:916；error_card.dart:129；review_screen.dart:286/:579/:812/:820 | §3.1.4（ratchet 已管，ui_design_tokens_baseline 有 error_book 条目——免检断言不成立，仅存量） |
| EB-G5 | review 统计与掌握度百分数裸奔：`'${(masteryLevel*100).toInt()}%'` 无口径行、无档位语言（ Quizlet 对照） | error_detail_screen.dart:728/:755；error_card.dart:206 | §6.3-1③（语义未教）；N6 同型（预测数子条款未覆盖掌握度类） |
| EB-G6 | 错题无对外分享卡：`share_cards/` 家族有 achievement/capsule/learning_report/node/plan/task 六种，独缺 error 卡；错题分享仅对小队（站内） | features/community/presentation/widgets/share_cards/ 目录清点；error_detail_screen.dart:60-72（唯一分享入口=ShareErrorToSquadDialog） | 对标 §1.3 分享惯例；北极星叙事「错题本 2.0」的传播件缺位（辩论裁决见 §3） |

### 2.4 我的/画像面

| # | 差距 | 证据（file:line @6043725c） | 违反条款 |
|---|---|---|---|
| PR-G1 | **永久空态卡占首位**：statistics_card 修复后恒为空态（代码自注「当前该卡无任何真实数据源，恒为空态」），却仍占「我的」页第一卡位+120dp 固定高——诚实但属永久死重；「画像与进度诚实」的必达位被一张永远说不出话的卡占据 | statistics_card.dart:66-67（自注）/:56-58（SizedBox height:120）；profile_screen.dart:69（首位挂载） | §0.2 必达项面积效率；对标 §1.4「无数据不渲染」公约（Strava/Duolingo）；诚实性本身达标（本条是 IA 条非诚实条） |
| PR-G2 | **onboarding 6 页超必达**：`_totalPages = 6`（welcome/architecture/galaxy/chat/task/personalization），SPEC §8.9 必达②「≤5 步到 home」被突破；chat/task 两特性页可合并 | interactive_onboarding_screen.dart:44（`_totalPages = 6`）/:182-187（六页清单） | v1.0 §8.9 必达②（已知条款的直接违反，非空白） |
| PR-G3 | onboarding 动效存量：`Curves.elasticOut`（§2.2.2 全局除名对象）+1s offLadder+architecture_animation 常驻 repeat | interactive_onboarding_screen.dart:242-243；architecture_animation.dart（基线 `persistentRepeatLoop:1, offLadderDuration:2, bannedCurve:1`；主屏基线 `bannedCurve:1, offLadderDuration:1`） | §2.2.2/§2.1/§2.6（基线已冻 ratchet 管，见辩论） |
| PR-G4 | 色字面量零散：engagement_state_badge `Color(0xFFEAF2E8)`、statistics_card 双冷色字面量 | engagement_state_badge.dart:67；statistics_card.dart:16-17（`0xFF94AFD2/0xFF7A93B4`，基线 `coldColorLiteral:3` 已登记） | §1.7【立即】段/§1.5.2（statistics 卡双冷色为趋势线 accent，属数据可视化方向应派生 info 槽） |

### 2.5 守卫基线核对（结构性证据）

- `check_ux_component_convention.py:44-58`：SCAN_ROOTS 无 `features/community`、`features/photon`、`features/error_book`（user 域仅 3 个点名文件）→ **CO-G2/EB-G2/PH-G5 的 raw 件全部免检**；
- `ux_component_convention_baseline.json`：四域零条目（与扫描根缺席一致）；
- `dl_spec_ratchet_baseline.json`：community 26 文件在册（gradient 为主）、photon 仅 `photon_balance_card {gradientLiteral:1}`、shop 仅 `user_title_widget {gradientLiteral:1}`、**error_book 零条目**（实测无违规，是好状态，但入根前无制度保证）；
- `ui_design_tokens_baseline.json`：error_book/photon/statistics_card/engagement_state_badge 在册（fontSize/colorLiteral 存量已纳管）；squad 双屏**不在册**（实测零字面量，干净）。

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转台账**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| CO-G1 | arb `{error}` 是 N4 的逃逸通道，必须封 | 蓝方：开发期排错有用；158 处清偿动 arb 是全舰队最高冲突文件，成本高 | G1 真差距（X6 明面违规换个门进来，且用户侧首因）；G2 收益高/成本 S-M 分批（arb 串行纪律 §6.5-4 已有，四张新面 12 处先行，存量分批）；G3 高——错误时刻是信任时刻，裸异常直出毁「诚实」签名特性 | **采纳**（N9 立条；改造 #2，先新面后存量 ratchet） |
| CO-G2 | 邀请环断裂=D 线增长回路断点 | 蓝方：小队功能刚上线，等 D 线价值评估（D-COMM-5/6）出结果再投入 | G1 真差距（产品级：功能存在但无法完成社交闭环，手输 ID 连 ID 来源都没有）；G2 收益高/成本 S-M（详情屏加「邀请」段：显示 ID+一键复制，无需后端改动——ID 已在下传 payload 里）；G3 高——期末组队互盯是冲刺完成度的已知杠杆，环路断=功能白建 | **采纳**（改造 #3，N10 社群面必达项②的组成） |
| CO-G3 | 榜单自我行高亮缺失 | 蓝方：3-8 人小队一眼能找到自己，高亮是锦上添花 | G1 真差距但弱（小队规模小，扫视成本低——与 Duolingo 千人联赛场景不可比）；G2 收益低/成本 S（端上有 userId 可比对）；G3 中-低 | **改写采纳**：随触碰顺带（实现 isSelf 比对成本 S，但不立专项；并入改造 #3 同文件批） |
| CO-G4 | `_formatDate` 绕唯一入口 | 无实质反驳 | 三关过，体量 S | **采纳**（并入改造 #3 文件同批，X3 防复发） |
| PH-G1 | 流水页不可达，兑换屏应挂流水入口 | 蓝方：光子消费单一（只兑 Pro），流水场景少；等真实用量再说 | G1 真差距（「可兑换基数」是审计重放口径——给用户看了一个审计数字却不给账本，透明性自断；且路由已存在只差入口，成本极低）；G2 收益中-高/成本 S（redeem 屏加一行次级入口或资产卡点击）；G3 中-高——钱包透明是对「光子=学习所得」信任的支撑，D 线主面的可信度问题 | **采纳**（改造 #4，N13 资产面三件套条款的组成） |
| PH-G2 | PhotonBalanceCard 死代码：删或治 | 蓝方：留着以后挂 | G1 真差距（死代码+带病+`?? 0` 假零样本，谁挂谁上线违规件）；G2 收益中/成本 S（删）或 M（重构复活——但 redeem 屏资产卡已覆盖余额显示，复活冗余）；G3 低-中 | **采纳（删）**：删 PhotonBalanceCard（余额显示已有 redeem 屏 owner）；若未来需要独立余额位，按 N13 规格重写（改造 #10 的一半） |
| PH-G3 | transfer 幽灵路由：下线 | 蓝方：路由注册可能为将来 P2P 预留；删了可惜 | G1 真差距（可深链误入的未审面+反刷敏感区+旧栈实现三重问题）；G2 收益中/成本 S（删路由+屏）；G3 低（转账非备考功能）；反刷红线一票权重 | **采纳（下线）**：路由+屏撤除或至少 flag 关断，留 git 历史；未来真做 P2P 再按 D 线裁决重建（改造 #10 的另一半） |
| PH-G4 | provider 裸异常 | 无实质反驳（同 CO-G1 通道） | 三关过 | **采纳**（并入改造 #2 批次） |
| PH-G5 | 流水页裸 spinner→骨架 | 蓝方：页面本身在 PH-G1 前不可达，改了没人看 | G1 真差距；G2 成本 S；G3 低（随 #4 入口打通后才有意义——**顺序绑定**） | **改写采纳**：与改造 #4 绑定同批（先有入口再治四态，避免治理不可达面） |
| PH-G6 | 流水日期绕唯一入口 | 无实质反驳 | 三关过，S | **采纳**（并入改造 #7 同批） |
| EB-G1 | 错题本双份裸异常 | 无实质反驳（北极星核心面的信任问题） | 三关全过 | **采纳**（并入改造 #2；列表屏 :483 raw 行删除、详情 :122/:549/:1009 人话化） |
| EB-G2 | error_book 入 UX-COMP 扫描根+基线登记 | 蓝方：迁移 10+ 裸件是工艺债，等 copy 批顺带 | G1 真差距（第一轮 S-G1 同型：主场景不受门禁=新债免检通道，error_book 是「错题本 2.0」叙事本体）；G2 收益高（一劳永逸）/成本 M（扫描根+1、基线登记现值、裸件迁移随批）；G3 高 | **采纳**（N11 立条；改造 #5） |
| EB-G3 | 掌握度色阶单源 + error 槽退出「尚未掌握」 | 蓝方：红黄绿三档是全 app 直觉语言，改中性会弱化「该复习了」的紧迫感；两处阈值目前一致，无实害 | G1 半差距（双写是 §9.4 同型隐患——改一处漏一处只是时间问题；error 槽挪用是 §1.5 明面冲突但「学习类红=需行动」也有品类先例）；G2 收益中/成本 S-M（建单一 helper+两处改引用）；G3 中——错题本主力色语义影响「不羞辱」红线（低掌握=红色=审判感） | **改写采纳**：立单一 owner（`mastery_band_color` 类 helper 入 core/display lexicon 域）+阈值单源；error→warning 档迁移（「该行动」语义），低档配档位文案补语义（N12；改造 #1） |
| EB-G4/G4' | fontSize 字面量专项清偿 | 蓝方：ratchet 已管（ui_design_tokens_baseline 在册），专项=第一轮 X-G5 同型重复立项 | G1 弱；G3 低 | **砍**（专项）；ratchet on touch |
| EB-G5 | 掌握度百分数配口径/档位语言 | 蓝方：百分数自明；加口径行占面积 | G1 半差距（§6.3-1③「语义被 UI 教过」未满足——60% 意味着什么没人教过）；G2 成本 S（label 加档位词）；G3 中 | **改写采纳**：并入改造 #1（档位语言随色阶单源一起落，百分数保留为次级显示） |
| EB-G6 | 错题对外分享卡 | 蓝方：叙事传播件属参赛材料层；app 内价值未验证（H2 未做）；M 成本 | G1 非差距（无用户证据）；G3 低-中 | **砍**（转 §10.5 台账观察行：H2 若验证「错题协作」买单再立卡） |
| PR-G1 | 永久空态统计卡：折叠或接真源 | 蓝方：接真源是 C 线口径工程（7 日序列端点不存在），本卡零代码不能做；折叠又浪费已修好的诚实件 | G1 真差距（必达位死重，对标先例=不渲染）；G2 折叠=S/接线=M（后者归 C 线卡池）；G3 中——「我的」页第一卡位给谁很重要 | **改写采纳**：短期 v1.2 只立「空态卡不占必达位」原则（折叠为可展开行或移位，S）；接线为改造 #8 的 M 选项交卡池（与 C 线 goal_today 式 SSOT 同构） |
| PR-G2 | onboarding 6→5 页 | 蓝方：6 页是特性宣传需要，skip 可跳；改页数动文案与埋点 | G1 真差距（§8.9 必达②明面违反，v1.0 已知条款非新立）；G2 成本 S-M（chat/task 两特性页合并为「AI 怎么帮你」一页）；G3 高——首见漏斗每多一页掉一档，期末用户时间最贵 | **采纳**（改造 #6；回写 §8.9 台账行） |
| PR-G3 | onboarding elasticOut/1s/常驻 repeat 清偿 | 蓝方：基线已冻、onboarding 在扫描根内、ratchet 只降不升；M5 叙事档本就是 onboarding 豁免档 | G1 弱（存量已管）；G2 成本 M 收益低；G3 低 | **砍**（专项）；ratchet on touch（同第一轮 X-G5 裁决） |
| PR-G4 | 零散色字面量 token 化 | 蓝方：statistics_card 双冷色已在 coldColorLiteral 基线，批 2 B2-2 palette 迁移统一清 | G1 弱；G3 低 | **砍**（专项）；随批 2 清偿（engagement badge 1 处触碰即迁） |

**辩论统计**：19 条 → 采纳 10（CO-G1/CO-G2/CO-G4/PH-G1/PH-G2/PH-G3/PH-G4/EB-G1/EB-G2/PR-G2）/ 改写采纳 5（CO-G3、PH-G5、EB-G3、EB-G5、PR-G1）/ 砍 4（EB-G4、EB-G6、PR-G3、PR-G4）。砍单主导理由：**ratchet 已管住的存量专项**（2 条）、**北极星加权低或无用户证据**（2 条）。
（注：PH-G5/PH-G6/EB-G5/CO-G4 类 S 级条目以「并入同文件批次」形态采纳或改写采纳，不占独立改造名额——与第一轮 S-G3/S-G4/S-G10 处置同制。）

---

## 4. SPEC v1.2 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0/v1.1：编号规则 + 依据 + 可验收数字；不推翻 v1.0/v1.1 任何条款。生效方式建议沿用 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。编号接续 v1.1 的 N8。

**N9（§4.5/N4 扩展 + §6.5 arb 纪律衔接）· l10n 错误模板零异常细节（arb 逃逸通道封堵）**
- N4 的禁令对象扩展到 **arb 模板层**：错误类模板禁携带 `{error}` 类原始异常占位符——用户侧错误文案=人话模板（发生了什么+影响+重试指引），异常细节只进日志（`debugPrint`/上报），不进 `Text`。
- 机检双维：①arb 侧 `\{error\}` 计数 ratchet（现值 **158**，`app_zh.arb` 实测，只降不升）；②代码侧 `l10n.\w+Failed\((error|e)\)` 调用面扫描 ratchet。arb 编辑走 §6.5-4 串行窗口纪律。
- 存量清偿顺序：四张新面（squad 11 处/photon 2 处/error_book 4 处）先行 → 全 arb 158 处分批 ratchet 下降。
- 【依据：§2.1 CO-G1/§2.2 PH-G4/§2.3 EB-G1；§1 共性 1；v1.1 N4 的实现无关化精神同型（N3 先例：禁模式不禁函数）】

**N10（§0.2/§8 增补）· surface 登记表 +3：社群 / 光子 / 错题本为第 11-13 治理面**
- **community surface**（`features/community/presentation` 内 squad 域：squad_list_screen + squad_detail_screen + share_error_to_squad_dialog）：必达项（≤2）——①成员完成度榜与在室状态一眼可信（榜只准 sprint-completion 口径，FLEET-BRIEF #2 红线沿用）②邀请/组队一步可达（ID 可见可复制）。四角归属：懂状态+有温度（社群动机）。
- **photon surface**（`features/photon/presentation`：photon_redeem_pro_screen + transaction_history_list；PhotonBalanceCard/transfer 按 §5 改造 #10 处置后不在面内）：必达项（≤2）——①余额与可兑换基数两数诚实分列（§9.4 服务端真值优先）②兑换三要素+有界终态。四角归属：过程透明。
- **error_book surface**（`features/error_book/presentation`）：必达项（≤2）——①今日该复习的错题一眼可达（待复习数=中性信息）②掌握度状态诚实分档（色阶单源，N12）。四角归属：懂状态（「错题本 2.0：静态收录→状态引擎」叙事本体面）。
- 【依据：§2.5 结构性发现 2；v1.1 N1 sprint 先例同制；§1 四面对标表】

**N11（§9.1 守卫表增补）· UX-COMP 扫描根 +3 与基线登记**
- `check_ux_component_convention.py` SCAN_ROOTS 增 `features/community/presentation`、`features/photon/presentation`、`features/error_book/presentation`；基线登记现值（error_book 现值≈10+ raw 件、photon≈3、community squad 域≈0），ratchet 只降不升、新文件零容忍；基线 JSON 共享态纪律照 §9.1（合并窗口统一刷）。
- 【依据：§2.5 守卫基线核对；第一轮 S-G1/改造 #7 同型裁决；§9.1 G 维扩充先例】

**N12（§1.5 增补）· 连续量分档色阶单一 owner（N5 的泛化）**
- 掌握度/熟练度类连续量分档色阶，全 app 单一 owner（core/display lexicon 域公开 helper，如 `masteryBandColor(double)`）；阈值 0.8/0.5 单源，存量双写靶：error_card.dart:281-284 与 error_detail_screen.dart:730-734。
- 档位语义：**高=success / 中=warning / 低=warning 或中性层+档位文案，error 槽退出「尚未掌握」**——error 只留给失败/错误/逾期（§1.5 原义）与 N5 倒计时扩展义；低档必须配档位语言（「还在学/已掌握」级，Quizlet 惯例），百分数降为次级显示。
- 【依据：§2.3 EB-G3/EB-G5 辩论改写采纳；v1.1 N5 倒计时色阶先例的连续量泛化；对标 §1.3 Anki/Quizlet 分档语言】

**N13（§6.3 增补资产面子条款）· 钱包类资产面三件套 + 禁伪装零**
- 货币化资产面（光子及未来任何积分/权益）准入四件：①余额/流水/出口三入口齐备——**流水页是必达件不是彩蛋**，任一资产数字展示位必须有可达的流水下钻；②「未知≠0」：加载失败/数据未至时显示「暂不可见」级诚实态，**禁 `?? 0` 类默认值直出**（FLEET-BRIEF #4 的 UI 层执行）；③消费动作必经确认对话框（价格+所得+不可逆提示）；④状态只走文字层级不作第二色（D-COMM-2 既有裁决升格为通用条款）。
- 存量靶：`photon_balance_card.dart:106`（`?? 0`，随改造 #10 删除）、transaction_history 无入口（改造 #4）。
- 【依据：§2.2 PH-G1/PH-G2 辩论；对标 §1.2 游戏商店/钱包惯例；FLEET-BRIEF 价值增量红线与诚实性条款】

**N14（§10.5 台账新增行，随 v1.2 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N9 arb `{error}` ratchet+新面清偿 | 未开工 | 改造 #2 |
| N10 三面登记（蓝图文字） | 未开工（本提案即蓝图） | —— |
| N11 扫描根+3 | 未开工 | 改造 #5 |
| N12 掌握度色阶单源+档位语言 | 未开工 | 改造 #1 |
| N13 流水入口+死代码处置 | 未开工 | 改造 #4/#10 |
| 小队邀请环（CO-G2） | 未开工 | 改造 #3 |
| onboarding ≤5 步回写 §8.9 | 未开工 | 改造 #6 |
| 错题对外分享卡（EB-G6） | 观察行（H2 验证「错题协作」买单后议） | —— |
| statistics_card 真源接线 | 观察行（M 选项，交 C 线卡池与 goal_today 同构评估） | 改造 #8 选项 B |
| transfer/PhotonBalanceCard 处置 | 未开工 | 改造 #10 |

---

## 5. 改造清单（按北极星收益排序 top10 v2，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。与 v1.1 top10 的关系：本表为**新增四面**的 v2 批次，v1.1 清单未清偿项不受影响。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **错题掌握度状态引擎规范化** | error_card.dart:281-284；error_detail_screen.dart:730-734/:757-761/:728/:755；core/display lexicon 域新建 helper + arb 新 key（§6.5-3 领前缀 `errorBook*`） | `masteryBandColor` 单一 owner（0.8/0.5 单源）；两文件改引用；error→warning 档迁移；低/中档配档位语言（「还在学」级）+百分数降次级 | 双文件色值断言测试（同输入同色）；error 槽在掌握度位不再出现；档位文案 widget test | S-M |
| 2 | **`{error}` 裸异常封堵（新面先行批）** | squad 双屏 11 处 + photon 2 处 + error_book 4 处调用点；arb 对应 9+ key；守卫扩双维（arb `\{error\}` ratchet=158 起冻 + 代码调用面 ratchet） | 错误模板改人话（「加载失败，你的数据没有丢」级，对齐 v1.1 改造 #4 模板）；异常细节进日志；新面 17 处清零后全 arb 分批 | 守卫跑绿+manifest 登记；四新面 `Failed(error)` 调用清零；arb `{error}` 基线冻结后只降不升 | 首批 S，全量 M |
| 3 | **小队邀请环补全** | squad_detail_screen.dart（AppBar 或 meta 区加「邀请」段：ID 展示+一键复制+一句话说明）；squad_list_screen.dart:372-373（`_formatDate` 走 date_formatting）；:231-288（isSelf 行高亮，端上比对当前 userId） | 邀请人可一键复制小队 ID；加入方凭 ID 入社的既有流程打通；榜单自我行 accent 容器高亮（§1.4.3 规格） | widget test：复制动作写入 clipboard；isSelf 行样式断言；日期格式断言 | S-M |
| 4 | **光子流水入口打通（与 #7 绑定）** | photon_redeem_pro_screen.dart（资产卡区加「查看光子流水」次级入口→`PhotonRoutes.transactionHistory`） | 兑换屏→流水页一步可达；「可兑换基数」数字可下钻核对（N13-①） | widget test：入口存在且路由可达；手测流水往返 | S |
| 5 | **三域入 UX-COMP 守卫** | scripts/guards/check_ux_component_convention.py:44-58 + 三份基线 JSON 登记 | 扫描根 +3（community/photon/error_book presentation）；error_book 10+ 裸件分批迁移（FilledButton→SparkleButton 家族、FilterChip→SemanticPill、Card→GraphiteCardSurface、ActionChip:683→SemanticPill）；photon ActionChip:348 随 #10 处置 | 守卫跑绿+manifest 登记；新文件零容忍；基线共享态纪律由合并窗口刷新 | M |
| 6 | **onboarding 收敛 ≤5 步** | interactive_onboarding_screen.dart:44（`_totalPages = 6`→5）/:182-187/:426-455（chat/task 特性页合并为「AI 怎么帮你」单页） | 6→5 页达 §8.9 必达②；合并页文案一屏两特性（各一句）；skip 与页断点续传保持 | 页数断言测试；文案角色登记（§3.2.4 后缀）；手测断点恢复 | S-M |
| 7 | **流水页四态规范化（绑定 #4）** | transaction_history_list.dart:52-54/:121-128（spinner→SparkleListSkeleton）；:69（裸错误→CustomErrorWidget 三句式）；:282/:180-200（时间走 date_formatting.dart）；photon_provider.dart:55/:148（异常不再进 UI 状态） | 骨架贴布局；错误人话+重试；日期唯一入口；provider error 字段退役或改 enum | 首载骨架 golden；Object 不出现于 Text 断言；日期格式断言 | S |
| 8 | **statistics_card 去死重** | profile_screen.dart:69；statistics_card.dart | 选项 A（S）：首卡位折叠为单行可展开（标题+「接入后可见」），或移位至成长区尾部；选项 B（M，交 C 线卡池）：接 7 日真实序列（goal_today_view 式 SSOT）按 has_data 分支渲染 | 选项 A：首屏高度回收断言；选项 B：has_data=false 不渲染曲线的 widget test + 口径来源登记（§9.4 三问） | S（A）/ M（B） |
| 9 | **squad/redeem 屏错误面与守卫衔接收尾** | squad_detail_screen.dart:73/:173/:376/:432/:480/:642（在 #2 中清）；本条为：三域入根后的首轮回扫，把 squad 域「零基线」状态登记冻结 | 防回归登记：squad 域现值（raw=0/字面量=0）作为高水位基线冻住 | ux_component_convention_baseline.json 出现 squad 条目且全零 | S |
| 10 | **幽灵光子面处置** | photon_routes.dart:24-32 + photon_transfer_screen.dart（466 行）；photon_balance_card.dart（152 行） | transfer：路由撤除或 feature flag 关断（反刷敏感区未审面不应对深链开放），屏留 git 历史；PhotonBalanceCard：删除（余额显示 owner 已是 redeem 屏 `_PhotonAssetCard`） | `PhotonRoutes.transfer` 引用清零；`grep PhotonBalanceCard` 清零；深链 `/photon/transfer` 返回 404 型路由兜底 | S |

**被砍项备忘**（防后续卡重复立项）：error_book/onboarding fontSize 与色字面量专项清偿（ratchet 在册只降不升，触碰即迁）；错题对外分享卡（H2 验证后再议，台账观察行）；squad 30s 在场心跳轮询（数据轮询非动画源，ROOM-PRESENCE 设计保持）；presence 全员列表含离场成员（诚实特性非差距）；squad AppBar 3 actions（≤5 合规）；prestige showcase 渐变（身份层 §8.7-3 先例，基线在册）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC2/REPORT.md`（本文件，位于 worktree wt222）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作
- [x] /tmp 无驻留（全程未写 /tmp）
- [x] 未 commit / 未 push
- [x] 引用代码均为 @6043725c 实测（rg/read）；守卫基线数为三份冻结 JSON 实测值；arb `{error}` 计数 158 为 grep 实测；无编造引用
