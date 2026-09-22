# D-COMMUNITY · 光子系统 / 排行榜 / 社群整合方案设计

> 2026-09-22 ｜ Worker D-COMMUNITY ｜ worktree wt154（基线 `6f647323`）｜ **零代码改动，纯调研设计**
> 交付物：本文 + [REPORT.md](./REPORT.md)。所有断言标注证据（`文件:行号` 或外链）。

---

## 0. 红线对表（设计前置约束）

本方案是 D 线（商业化）的一部分，红线是「**价值增量型盈利，不阉割免费体验**」。落笔前先与仓内已冻结决策对表——三条硬约束：

| # | 约束 | 出处 |
|---|---|---|
| R1 | **Entitlement 独立**：`paid_plan/entitlement/quota` 与 `flame_level/photon/streak` 完全分离；免费用户必须体验完整核心价值闭环，可限制的只有 deep reasoning / agent runtime 次数、大文件与长期历史、高成本 run、高级 analytics/export | `v3/01_product/COMMERCIAL_MODEL.md` §1-2 |
| R2 | **D17 游戏化降权**：Achievement 保留安静反馈；**Shop/Photon 从核心旅程降级**；**Leaderboard 默认隐藏**；`is_pro=flame_level>=3` 拆除（已落地：`backend/app/models/user.py:73-77` 列注释明文「禁止用 flame_level 派生权益——权益唯一判据是本列」） | `v3/00_context/DECISIONS_V3.md` D17 |
| R3 | **D18 社群不是公共 feed**：V3 社群聚焦**小队/冲刺/成果 check-in/反馈**；私人 Memory 与画像默认不可共享。另 NON_GOALS #10「不为『社交』建设公共广场」 | `DECISIONS_V3.md` D18；`v3/00_context/NON_GOALS.md:14` |

辅助约束：D20 数据真实性（mock 不进真实表面）、D21 UI 气质（calm，核心流程减少 gradient/particle/glow/confetti）。

**本文的核心立场**：D17 已把「游戏化作为留存钩子」这条老路封死，D 线对这三个模块的正确用法不是重新包装激励、而是**让它们为「期末一周冲刺」这个北极星场景提供价值增量**——它们卖的不是虚荣，是冲刺周的确定性。

---

## 1. 现状盘点（只读走查）

### 1.1 光子系统 —— 结论：生产级闭环已存在，问题是定位而非缺件

| 层 | 现状 | 证据 |
|---|---|---|
| 数据模型 | `users.photon_balance`（默认 0）；交易全量审计表 `photon_transaction_history`（balance_before/after 双列）；商城四表（ShopItem/ShopPurchase/UserConsumable + 交易枚举） | `backend/app/models/user.py:130`；`backend/app/models/shop.py:61-84,87-190` |
| 获取途径 | 成就奖励、每日首胜、契约完成（含加成）；**契约失败扣光子押金**（`create_contract(study_minutes, days, photon_stake)` → 完成 `stake*reward_multiplier` / 失败 `lost stake`） | `backend/app/models/shop.py:19-31`（枚举含 `deduct_contract_stake`）；`backend/app/services/achievement_engine.py:2856,2906-2919`；`backend/app/models/achievement.py:273`（押金默认 100） |
| 消耗途径 | 商城五类：skin/title/consumable/boost/visual_element；消耗品效果含 exp_boost、photon_boost、streak_freeze、hint_reveal、energy_restore | `backend/app/models/shop.py:34-58` |
| 转账 | 用户间转账（单笔上限 10000），行锁按 id 排序防死锁，双边流水 | `backend/app/schemas/photon.py:81-115`；`backend/app/services/photon_service.py:424-521` |
| 工程质量 | FOR UPDATE 行锁、重复发放幂等去重（`deduplicated` 返回）、原子条件 UPDATE 扣减防负余额、Redis 缓存 5min TTL + 写前失效 | `photon_service.py:57-68,196-259,155-194,391-402` |
| 奖励可靠性 | 成就光子奖励失败有 Celery 补偿重试（队列背压兜底→本地重试） | `achievement_engine.py:1630-1716,1810-1836` |
| 移动端 | 光子功能**已挂路由**（余额卡/流水/转账页），商城已挂路由 | `mobile/lib/app/routes.dart:403,409`；`mobile/lib/features/photon/photon_routes.dart:25` |
| 与 streak/成就/mastery 关系 | 光子是成就系统的**结算货币**（合同押金+奖励），且榜上有 PHOTON/PHOTON_WEEKLY 两类光子榜；flame_level 与 streak 是独立维度；mastery 在 galaxy sprint rollup，与光子无直接耦合 | `backend/app/services/leaderboard_service.py:97-100`；`backend/app/services/galaxy_service.py:206,2794` |

**判定**：光子不是概念稿，是带审计、幂等、并发安全的成品经济系统。与 D17 的张力在于**它挂在核心旅程的深度**（合同押金失败扣钱、商城 boost 可影响学习体验项如 streak_freeze/hint_reveal），而非它存在本身。

### 1.2 排行榜 —— 结论：后端全量就绪 + 移动端 1143 行死代码，卡在产品决策上

| 层 | 现状 | 证据 |
|---|---|---|
| 后端 | 9 种榜型：global/friends/group/subject/weekly/streak/group_flame/**photon/photon_weekly**；综合分公式 = 知识点×1.0 + 打卡天×0.5 + 成就×2.0 + 最长连胜×1.5；guest/seed cohort 已排除出排名面（V3-FIX-01） | `backend/app/schemas/leaderboard.py:17-27`；`backend/app/services/leaderboard_service.py:49-65` |
| API | 6 端点：列表/summary/my-rank/types/top-three/refresh-cache，全部鉴权 | `backend/app/api/v1/leaderboards.py:29-120`；端点常量 `mobile/lib/core/network/api_endpoints.dart:610-616` |
| 移动端 | **完整实现但未挂路由**：screen 420 行 + provider 348 行 + repo 375 行，全仓无 `LeaderboardScreen` 外部引用；l10n 20 键就绪 | `KNOWN_CODE_DEBT_LEDGER.md:30`（P1 #3）；本卡 grep 复核：仅三个文件自引用 |
| 债务台账处置建议 | 「产品决策：要么挂路由上线，要么整链删除（含端点常量与 l10n 键）」 | `KNOWN_CODE_DEBT_LEDGER.md:30` |
| 已知隐患 | `get_my_rank` 拉全量榜（limit 100）找自己——规模化需改 COUNT 查询（代码内已留注释）；全站综合榜对中尾部用户天然挫败（见 §2） | `leaderboard_service.py:121-127` |

### 1.3 社群 —— 结论：全仓最大的超配模块，督促/小队/火堆与北极星天然对齐

| 层 | 现状 | 证据 |
|---|---|---|
| 后端体量 | `community.py` **5111 行**（feed/帖子/好友/群组/群消息/群文件/打卡/火堆/群任务/资源共享/E2E 公钥/群管理，约 80 端点）；service 3354 行；督促（accountability）1739 行；好友匹配推荐 831 行（Jaccard 兴趣 + 互补性 + 反馈调参 + 缓存） | `backend/app/api/v1/community.py`；`services/community_service.py`；`api/v1/accountability.py`；`services/friend_match_service.py:97-104` |
| 数据模型 | Group（`total_flame_power` 火苗总能量）、GroupMember（`flame_contribution`）；督促搭档 AccountabilityPartnership/Checkin（时区感知打卡日界、双 slot、连续计数） | `backend/app/models/community.py:169-268,314`；`backend/app/models/accountability.py:43-131`；`api/v1/accountability.py:217-261,410` |
| 移动端 | **20 个屏幕已挂路由**（feed/好友/群组/督促等），5 个仓库层；demo 模式 mock 兜底是**有意设计**（台账 P3 #7） | `mobile/lib/features/community/presentation/screens/`（清单见 §5.3）；`mobile/lib/features/community/community_routes.dart:352-368`；`KNOWN_CODE_DEBT_LEDGER.md:45` |
| 网关 | community_sync.go 等三个投影消费者是「活跃社群路径本体」，死代码已于 2026-09-08 清理 | `KNOWN_CODE_DEBT_LEDGER.md:12-13,53` |
| 隐私 | 社群聚合信号模型 + 隐私策略模块已存在（聚合不暴露个体） | `backend/app/models/community_privacy.py:9`；`api/v1/community_aggregates.py` |
| 提醒 | 打卡提醒 Celery 任务已就绪 | `backend/app/tasks/community_checkin_reminder.py` |

**判定**：社群不缺功能，缺的是**从「广场式全量」收敛到 D18 的「冲刺小队」场景聚焦**。督促（accountability）+ 群打卡 + 火堆是全仓最贴合「期末一周冲刺」的既有资产，但目前与 `exam_sprint`（intake/dashboard/diagnose/sprint-summary 等 8 端点，`backend/app/api/v1/exam_sprint.py:32-129`；路由注册 `api/v1/router.py:222`）**零联动**——这是最大的整合空白点。

---

## 2. 对标研究

> 取证说明：本机 WebSearch 周配额耗尽（429，2026-09-24 重置），对标以 WebFetch 直接取源为准；以下每条均标注来源链接。R 站点情绪类二手结论已尽量回避或降级为「待验证」。

### 2.1 Duolingo 联赛（Leagues）——「随机 30 人小池」的成与败

- 机制：每周 XP 榜，**随机分组、每组最多 30 人**，10 个段位（Bronze→Diamond）；排名只看周 XP。另有 Friend Streak（最多 5 人共享连胜）。货币 Gems + 体力系统（付费订阅无限体力）。([Wikipedia: Duolingo](https://en.wikipedia.org/wiki/Duolingo))
- **翻车点**：用户报告游戏化「导致作弊、外挂与激励出与真实学习冲突的刷分策略」（XP farming）；语言教育专业人士批评游戏化设计。([Wikipedia: Duolingo](https://en.wikipedia.org/wiki/Duolingo))
- 可取点：**30 人小池**是联赛体系里最值得抄的参数——池子小到「榜上都是像我的人」，大到有竞争感；段位升降提供周期性重置，避免「永恒羞辱榜」。
- 争议教训：**把行为量（XP）当榜分，必然催生刷量**——这与 D20「不能用 token 消耗当产品价值」同构。

### 2.2 排行榜心理学——「打击中等生」的经典反面模式有研究背书

- Werbach & Hunter（《For the Win》）：排行榜**只对「接近上一名」的玩家有激励，对榜底玩家是去激励器**；竞争只在**水平相近**的参与者之间产生正效应，否则社会压力损害参与。([Wikipedia: Gamification](https://en.wikipedia.org/wiki/Gamification))
- 高校微积分课实验：排行榜**提升了学习成绩，但没有提升动机与自我效能**——「产出指标变好、心理指标不动」，设计者须补足反馈与自主性。([Wikipedia: Gamification of learning](https://en.wikipedia.org/wiki/Gamification_of_learning))
- 2025 年 BJET 元分析（22 项实验）：游戏化总体正效应（g=0.782）但**完全由情境与设计中介**；PBL 三件套（点数/徽章/排行榜）孤立使用「不必然有效」，Ian Bogost 批评其为「人工成就感」。([Wikipedia: Gamification of learning](https://en.wikipedia.org/wiki/Gamification_of_learning)；[Wikipedia: Gamification](https://en.wikipedia.org/wiki/Gamification))
- 过度合理化效应（Deci 线）：外部奖励框架会挤占内在动机——对「本来就为期末而学」的用户，额外物质化奖励是风险的，不是免费的。([Wikipedia: Gamification](https://en.wikipedia.org/wiki/Gamification))

> 对 Sparkle 的直接推论：全站综合榜（现 global 榜公式）恰好命中全部反面模式——大池、异质水平、静态综合分、无周期重置。D17「Leaderboard 默认隐藏」不是保守，是对的。

### 2.3 Kahoot / 课堂竞技——同期同步 + 自制内容是正效应条件

- 93 研究综述（Wang & Tahir 2020）：对课堂氛围、学习与焦虑「整体正效应」；2023 元分析（41 研究，n≈5071）g=0.822。注意其正效应场景是**同期同步、教师主持、短时局**，不是 7×24 常驻榜。([Wikipedia: Kahoot!](https://en.wikipedia.org/wiki/Kahoot!))
- 教育价值最高的形态是**学生自己出题**（创造性使用）。([Wikipedia: Kahoot!](https://en.wikipedia.org/wiki/Kahoot!))
- 推论：「冲刺周限时局 + 同伴同质」比「常驻天梯」更可能复现正效应。

### 2.4 Forest / B 站自习室——损失厌恶 + 共学临在感的可抄结构

- Forest：专注计时种树，**中途弃用则树枯死**（损失厌恶，不限制自由）；**多人共种**（co-focus 群体临在）；虚拟币可兑换**真实种树**（与 Trees for the Future 合作，超 200 万棵真树）——虚拟努力兑现为真实世界价值的最干净范例。([Wikipedia: Forest (app)](https://en.wikipedia.org/wiki/Forest_(app)))
- 争议点：不付费则币奖励偏小（Mashable 批评）——**免费/付费奖励梯度**是这类产品最容易伤免费体验的地方。([Wikipedia: Forest (app)](https://en.wikipedia.org/wiki/Forest_(app)))
- B 站自习室（直播自习/Study with me）：无强机制，靠「被看见的临在感」维系；对 Sparkle 的启示是**共学不必做重内容，做「在场证明」即可**（本条为通识补充，未及溯源到具体研究，见 §6 诚实申报）。

### 2.5 对标小结

| 对标 | 可取 | 翻车点 | 对 Sparkle |
|---|---|---|---|
| Duolingo 联赛 | 30 人小池、周期重置 | XP 刷分、作弊、榜底挫败 | 榜分必须绑定**结果性**而非行为量 |
| Werbach 研究 | 近距激励 | 榜底去激励、异质竞争 | 只做同质小群体榜，永远附带自我对比锚 |
| Kahoot | 限时局、自制内容 | 常驻天梯化 | 冲刺周限定，非永久设施 |
| Forest | 损失厌恶、共种、虚拟→真实价值 | 免费/付费奖励梯度 | 兑换通道必须对免费用户完整开放 |
| B 站自习室 | 在场临在感 | 内容空心化 | MVP 只做「在场证明」 |

---

## 3. 三模块方案设计

### 3.1 光子：三条可能定位逐一评估（价值增量红线贯穿）

| 定位 | 内容 | 红线评估 | 结论 |
|---|---|---|---|
| A. 纯装饰 | 现状商城（skin/title/visual_element）为核心消耗去向 | ✅ 合规：不触及核心闭环；❌ 对 D 线无营收贡献，且 D17 要求它「降级出核心旅程」 | **保留为沉没池，不再投入**；顺手按 D21 降噪（商城 UI 目前有 gradient 风格项，`mobile/lib/features/shop/` 走查有 boost/加成类文案，属 D21 收敛对象） |
| B. 解锁增值功能 | 光子买 deep reasoning / agent run / 高级 analytics | ❌ **红线违规**：a) 与 R1 冲突——能力门控唯一依据是 entitlement，光子购买力等于「免费用户可刷光子绕过付费」，重演 `is_pro=flame_level>=3` 式语义混用（`user.py:73-77` 刚拆完的债）；b) 「刷学习量换算力」必催生刷分（Duolingo 教训） | **否决，并立为新守卫**：禁止任何能力门控读 photon_balance |
| C. 兑换特权（价值兑换通道） | 光子按**有界汇率**兑换 Pro 天数/权益凭证，桥接 D-REDEEM 已建的 `redeem_codes` + `users.entitlement_expires_at` 原子核销链路 | ✅ 合规且是 D 线最优解：a) 免费核心闭环不受影响（兑换是增量福利不是解锁前提）；b) 「学习赚会员」把游戏化产物兑现为**真实世界价值**（Forest 真树范式）；c) 审计面现成（`photon_transaction_history` 全流水）；d) 有界性可控（月度上限 + 排除转账收入） | **推荐主定位**，见 MVP |

**3.1-推荐 ·「学出会员」光子兑换通道（Photon→Pro-days Redemption）**

- **价值假设**：把冲刺周的密集使用沉淀为「下个月的 Pro 天数」，提高次月留存与口碑分发（「我在 Sparkle 学习赚出了会员」是可传播叙事）；对不愿付费的学生，给出不阉割体验的第三条路（时间换价值）。
- **MVP 范围**：
  1. 新服务 `photon_redeem_service`：仅允许消费 `transaction_type IN (grant_achievement, grant_daily_first, grant_contract, grant_contract_bonus)` 的累计净收入作为兑换额度基数（**transfer_in 一律不计入**——封堵「小号互转刷会员」，转账机制本身保留原样）；`DEDUCT_CONTRACT_STAKE/PENALTY` 同步扣减基数。
  2. 兑换汇率与上限：如 3000 光子 = 7 天 Pro，**每自然月上限 1 次**（硬顶，防套利与营收蚕食失控）；兑换产出直接复用 D-REDEEM 的 `entitlement_expires_at` 叠加语义与原子核销模式（`v3-output/D-REDEEM/REPORT.md` §0）。
  3. 每笔兑换双写流水：photon 侧 `deduct`（`record_history=True`）+ billing 侧复用 D-REDEEM 的审计注记。
  4. 移动端：设置页兑换码入口旁加「光子兑换」卡（复用 `redeem_code_dialog.dart` 交互骨架与 DS 令牌规范，见 D-REDEEM 交付面）。
- **风险**：刷分（堵：只认合同/成就/首胜三类**带行为审计**的收入 + 月顶）；营收蚕食（量级小、可观测，见下）；负余额竞态（堵：复用 `_deduct_balance_atomically` 条件 UPDATE，`photon_service.py:155-194`）。
- **必须观测**（R1 附表）：兑换渗透率、兑换者次月留存 vs 未兑换、兑换者付费转化、光子收入构成（确保合同类占比健康，防刷）。
- **衔接点**：`services/photon_service.py`（扣减）、`services/redeem_service.py` + `models/redeem_code.py`（D-REDEEM 产物，授予侧）、`api/v1/redeem.py`（端点模式）、`core/entitlement.py`（到期降级已闭环）。
- **优先级：P1（D 线唯一新增商业机制，成本低——链路两端都已存在，本卡只补中间桥）。**

**3.1-附：契约押金机制定性**：`create_contract` 押金-奖惩（`achievement_engine.py:2856-2919`）是行为承诺装置（Forest 枯树同构），**不是商业化面**。保留但按 D17 维持在「成就安静反馈」层：不弹窗、不进核心路径、失败扣款有醒目前置告知（现 UI 已有 stake 输入，`achievement_contract_screen.dart:128,341`）。不建议扩成「押真钱」——支付合规是另一条战线。

### 3.2 排行榜：同侪小队榜 vs 全站榜 vs 自我历史对比

| 维度 | 全站榜（现 global/weekly） | 小队同侪榜（cohort） | 自我历史对比 |
|---|---|---|---|
| 动机价值 | 研究明证榜底/中尾去激励（§2.2）；guest 排除后样本进一步失真 | 30 人内、冲刺同侪水平相近——唯一有正效应证据的形态（Duolingo 30 人池 + Werbach 同质条件） | 零社交伤害；契合「长期成长」叙事；数据源即 D-03 五维度量 |
| 北极星契合 | 无场景绑定 | **期末冲刺周 = 天然的同质 cohort + 有限周期**（Kahoot「限时局」条件） | 全周期可用，冲刺周作为对比基线 |
| 操纵/作弊风险 | 高（综合分可刷：知识点数/打卡天皆可量刷） | 中（小队内可见性自带社会监督；榜分绑定冲刺结果性指标） | 无 |
| 实现成本 | 已建成但需隐藏（沉没） | 中：后端 `GROUP` 榜型已有（`leaderboard_service.py:89-90`），缺「冲刺小队」聚合口径 | 低：读既有统计 |
| 与 D17 关系 | 违（默认隐藏） | 合（默认不展示全局，仅小队/自己两视图，且只在冲刺周期内出现） | 合 |

**3.2-推荐 ·「冲刺小队榜」+「自我锚」双视图，全站榜下线**

- **价值假设**：期末周的真实痛点是「不知道自己复习进度相对成败的位置」。小队榜回答「像我的人到哪了」（规范性信息，不是攀比），自我锚回答「我比昨天好在哪」。二者合起来才构成动机价值，单拿排行榜出来是负资产。
- **MVP 范围**：
  1. **下线/隐藏全站榜**：不路由 global/subject/streak/photon 榜（D17 执行化）；P1 债务 #3 的「挂或删」裁决为：**删 global 综合榜链路面，保留后端榜型枚举中 weekly/group 两种供小队榜复用**。
  2. 小队榜口径 = 冲刺完成度（`exam_sprint` 的 dashboard/sprint-summary 真实数据）+ 每日打卡布尔，**不使用**光子/XP 等行为量做榜分（防 Duolingo 式刷分）。
  3. 每个榜视图强制并列「我的近 7 日自我曲线」锚点；榜尾不标红、无降级动画（D21 calm）。
  4. 仅冲刺周期可见（intake→考后 review 之间），非冲刺用户看不到任何榜入口。
- **风险**：小队人数不足时榜单失真（兜底：不足 3 人自动切纯自我视图）；相对位置焦虑（兜底：默认展示「区间」而非名次，如「你的节奏在前 40%」——实现上读 percentile 即可，`MyRankResponse.percentile` 已存在，`schemas/leaderboard.py`）。
- **衔接点**：`leaderboard_service.py`（GROUP 查询路径复用 + 新口径聚合）、`exam_sprint.py:47 dashboard`、`MyRankResponse.percentile`、移动端 `features/leaderboard/` 三文件改造后挂路由（或仅复用其 widget 层）。
- **优先级：P2（依赖 3.3 的冲刺小队先存在；但 P1 债务 #3 的裁决本身应随 D-COMM-1 卡先行落地）。**

### 3.3 社群：共学自习室 vs 错题互助 vs 朋友星图互访

| 维度 | 共学自习室 | 错题互助 | 朋友星图互访 |
|---|---|---|---|
| 期末周契合 | **强**：冲刺期的共同在场是刚需（Forest 共种 + B 站自习室双验证） | 强（考前刷错题是高频动作，`error_book` 已有模块） | 弱（身份/好奇驱动，与冲刺弱相关） |
| 实现成本 | **中低**：督促 partnership/打卡/在线状态 API 全在（`accountability.py` 全套 + `community.py:3021` 在线状态），缺的只是「群组级共读会话」聚合层 | 中：分享通道现成（群资源 `community.py:3550` + 群文件），缺错题卡 → 群分享的桥 | **低**：galaxy 数据 + 好友资料页都在（`friend_profile_screen.dart` 已路由），加「访问星图」入口即可 |
| 操纵/审核风险 | 低（无内容生产，仅在场证明） | **中高**：UGC 错题内容质量与搬运版权；需走群管理审核（`community.py:4328` moderation 已有钩子） | 低 |
| D18 合规 | 合（小队内、非公共广场） | 合（限定小队分享，不开公共题库） | 合（好友双向可见） |
| 数据真实 | 高（focus 会话真实计时） | 中（错题质量参差） | 高 |

**3.3-推荐组合（按优先级）**：
1. **共学自习室（P1）**：群组内发起限时共学局（25/45min Pomodoro 档），成员进出场写「在场证明」，结束聚合每人真实 focus 时长入小队榜口径。**MVP 不做视频/语音**，纯状态同步——成本最低、临在感已有（Forest 证明纯图标临在足够）。
2. **错题卡互助分享（P2）**：`error_book` 单卡 → 小队分享（复用群资源权限模型 + moderation 钩子），收「讲给别人听」的完成度反馈——契合「教是最好的学」，且 Kahoot 证明**用户自制内容**是教育价值最高形态。
3. **朋友星图互访（P3，可砍）**：轻量访客视图 + 留言。与冲刺无关，属留存调味，待前三者验证后再说。

**共学自习室 MVP 细则**：
- 价值假设：冲刺周最大摩擦是「独自学习的启动成本」；共同在场降低启动摩擦并给打卡提供社会承诺（督促 partnership 的群组化泛化）。
- 范围：仅已存在的群组可发起（不新增公共房间——NON_GOALS #10）；会话状态 Redis 存活 + 落库最小记录；离开会话**不惩罚**（不用 Forest 枯死机制——校园场景下网络抖动误伤率高，用「在场时长如实记录」替代）。
- 风险：多端状态同步（复用现有 presence/在线状态接口）；「挂机刷时长」（榜分绑定 sprint 完成度而非时长，时长仅展示不排名——见 3.2）。
- 衔接点：`api/v1/accountability.py`（打卡/时区/连续计数）、`community.py:3021`（在线状态）、`community.py:3288`（火堆可视化口径可复用为共学局余温展示）、`tasks/community_checkin_reminder.py`（开场提醒）。
- **诚实注记**：现有群消息链路带 E2E 公钥注册端点（`community.py:4235-4283`），共学局若需要广播消息须确认与既有加密语义的兼容性——本卡未深查，列为实施卡前置核查项。

---

## 4. 推荐组合拳：「期末冲刺周」价值包

三个模块不是三个独立功能，是同一个 D 线卖点的三个面：

> **卖点**：期末这一周，Sparkle 给你一支真实同侪小队、一张只跟自己和队友比的进度图、以及一周后可兑现的真实权益。

```
冲刺小队（社群·3.3）        进度双视图（排行榜·3.2）      学出会员（光子·3.1）
─────────────────          ─────────────────           ─────────────────
共学自习室（在场）    ──▶    小队榜=冲刺完成度     ──▶    合同/首胜/成就光子
群打卡+火堆（承诺）           +自我7日锚                 （仅审计面收入）
督促搭档（兜底）          （无 XP/光子分）                ↓ 有界兑换（月顶1次）
                                                        Pro 7天（D-REDEEM 链路）
```

- **闭环逻辑**：社群提供「人来」（冲刺小队是 cohort 天然同质），排行榜提供「比得健康」（完成度+自我锚，规避打击中尾生），光子提供「留下真实价值」（冲刺收入兑现 Pro 天数 → 次月留存 → 口碑分发 → D-LANDING 渠道进新客）。
- **对红线的自检**：免费用户全程可用小队/自习室/自我视图/光子获取与兑换（R1 ✅）；全站榜继续隐藏、商城继续降级（R2 ✅）；一切限定小队、无公共广场（R3 ✅）；榜分不用行为量（D20 精神 ✅）；光子兑换走 entitlement 唯一判据（不复活 flame 派生债 ✅）。
- **营收贡献直估**：光子兑换本身不直接产生现金收入（是留存/口碑投资）；直接营收仍由 D-REDEEM 兑换码 + 未来订阅承担。本组合拳的商业价值在**降低付费墙的心理阻力**——先让用户用「时间+努力」体验过 Pro 增量价值，转化与定价叙事都有据可依（对照 `COMMERCIAL_MODEL.md` §3「按用户价值售卖」）。

---

## 5. 拆卡建议清单（供主会话裁决后派卡）

> 每卡：范围 / 关键衔接 / 验收判据（判据均可机器或脚本验证）。优先级基于依赖关系：D-COMM-1 可立即做且顺手清 P1 债务；-2/-3 并行；-4 依赖 -3；-5 依赖 -3；-6 收尾。

### D-COMM-1（P0，卡最小）· 排行榜 P1 债务裁决落地
- 范围：移动端 `features/leaderboard/` 改造为「自我视图」挂路由（或按本方案仅保留 widget 层供 D-COMM-4 复用），**全站/学科/光子榜不路由**；后端不动。
- 验收：`grep -r "LeaderboardScreen" mobile/lib/app/routes.dart` 有唯一挂载（或 feature 目录删除后全仓零引用）；global/subject/photon 榜型在移动端无任何入口；`bash scripts/run_all_rule_guards.sh` 绿；P1 #3 从 `KNOWN_CODE_DEBT_LEDGER.md` 销账。
- 关键衔接：`routes.dart`、`api_endpoints.dart:610-616`（保留，后端端点不变）。

### D-COMM-2（P1）· 光子→Pro 天数有界兑换通道
- 范围：`photon_redeem_service`（收入基数口径 + 月度硬顶）+ engine 端点 + 移动端兑换卡；复用 D-REDEEM 全链路。
- 验收：①兑换原子性——并发同用户兑换不超月顶（条件 UPDATE + 唯一约束，模式同 D-REDEEM §0）；②`transfer_in` 不计入兑换基数（构造转账后兑换用例，预期拒绝）；③兑换后 `entitlement_expires_at` 正确叠加且到期降 free（复用 `core/entitlement.py` 既有测试模式）；④**免费闭环回归**：零光子新用户走通核心链路无任何新阻断；⑤全流水双写可审计（photon 侧 + billing 侧各一条）；⑥守卫绿。
- 关键衔接：`photon_service.py:155-194,196-301`；`redeem_service.py`；`entitlement.py`；`redeem_code_dialog.dart`。

### D-COMM-3（P1）· 期末冲刺小队 MVP（社群×exam_sprint 首次联动）
- 范围：群组挂「冲刺小队」标记 + 成员冲刺状态聚合（intake 完成/每日打卡/冲刺完成度）+ 小队页聚合视图；数据全部走真实 API（D20）。
- 验收：①建队→绑 sprint→成员加入→聚合视图返回真实数据（断言无 mock 兜底路径：生产模式下 `mock_community_repository` 不可达）；②非成员不可见（权限回归）；③`/exam-sprint/dashboard` 数据出现在小队页且字段对齐；④打卡连续计数复用 accountability 现有实现（时区用例通过）。
- 关键衔接：`community.py:2003`（join）、`accountability.py`、`exam_sprint.py:47,101`、`community_checkin_reminder.py`。

### D-COMM-4（P2，依赖 -3/-1）· 共学自习室 + 小队双视图榜
- 范围：群组限时共学局（创建/加入/在场记录/结束聚合）+ 小队榜（完成度口径）+ 自我 7 日锚视图；榜名次默认显示区间（percentile）。
- 验收：①会话周期内进出场记录与真实 focus 数据一致；②榜分 = sprint 完成度（单测断言不读 photon/XP）；③<3 人自动切纯自我视图；④非冲刺周期无榜入口；⑤榜单 UI 无 confetti/降级动画（D21，`tool/ui_lint.sh` 过）；⑥**前置核查项**：与群消息 E2E 公钥语义兼容性结论落档。
- 关键衔接：`accountability.py:217-261,410`、`community.py:3021,3288`、`leaderboard_service.py:89-90`（GROUP 路径）、`MyRankResponse.percentile`。

### D-COMM-5（P2，依赖 -3）· 错题卡小队互助分享
- 范围：`error_book` 单卡 → 小队分享（复用群资源权限模型）+ 「讲一遍」完成度反馈。
- 验收：①分享→群资源列表可见且权限继承正确；②moderation 钩子接入（违规内容可下架）；③仅小队范围（断言无公共目录泄露）；④原卡删除后分享视图降级处理不炸。
- 关键衔接：`error_book.py`、`community.py:3358,3550,4328`。

### D-COMM-6（P3，可选收尾）· 光子装饰沉没池 D21 降噪
- 范围：商城/光子 UI 按 D21 收敛（去 confetti 风格项、boost 类文案降调），确认商城不出现在核心旅程导航。
- 验收：ui-lint 绿；核心旅程任何页面无商城入口（walkthrough 脚本断言）；光子相关 l10n 无诱导性文案（人工清单）。

---

## 6. 诚实申报（拿不准的假设）

1. **兑换通道的营收蚕食无实测数据**：月顶 1 次 Pro 7 天是拍脑袋的保守值；真实弹性要靠「必须观测」四指标上线后校准。若兑换者付费转化显著为负，应砍兑换上限或改兑换「Pro 功能体验券」而非天数。
2. **「30 人小队」参数是类比移植**：Duolingo 30 人是语言学习日活场景；期末小队天然规模可能是 3-8 人（室友/同班），本方案按「<3 人自动切自我视图」兜底，但上限参数需实测定。
3. **B 站自习室条目取证弱**：WebSearch 配额耗尽，该条为通识性补充，未溯源到具体研究或报道；Forest/Duolingo/Kahoot/心理学四条均有 Wikipedia 一手页面背书（链接见 §2）。建议配额恢复后补一轮 R/Duolingo 与「study with me」实证文献检索，验证「共学临在感」效应量。
4. **社群 E2E 加密与共学局广播的兼容性未深查**：`community.py:4235-4283` 有公钥注册/撤销端点，但群消息链路实际加密程度（强制 or 可选）本卡未走查，已列为 D-COMM-4 前置核查项。
5. **好友匹配推荐（`friend_match_service.py`）成色未实测**：代码结构完整（含反馈调参与缓存），但推荐质量、冷启动行为无运行时证据；冲刺小队的「匹配建队 vs 邀请建队」路线选择留待 D-COMM-3 实施时以真实数据定，本方案默认邀请制优先（冷启动更稳）。
6. **`community.py` 5111 行单文件本身是结构性债务**：本卡不改代码，但拆卡实施时任何增改都在这个文件上操作，建议 D-COMM-3 起按新路由文件（如 `api/v1/sprint_squad.py`）挂新端点，不继续膨胀 `community.py`。
7. **全站榜「删」的裁决不可逆**：若产品后期反悔要 global 榜，重写成本中等（service 层保留）。本文按 D17 + 研究证据推荐删面保枚举，最终裁决权在主会话。

---

## 7. 收工核查（Worker 五要素之⑤）

- **零代码改动**：本卡仅新增 `v3-output/D-COMMUNITY/DESIGN.md` + `REPORT.md` 两个文档，未触碰任何 `backend/`、`mobile/`、`gateway/`、`proto/`、`scripts/` 代码与配置；未执行 git commit/push。
- **无凭据**：全程未接触任何密钥/token/生产配置；无 `.env` 副本；未在仓库根/家目录创建文件。
- **主仓只读**：所有读操作在 wt154 worktree 内完成；未做任何树变更操作（无 stash/reset/clean/切分支）。
- **临时产物**：本卡无 /tmp 产物、无进程启动、无构建产物；LIGHT 级任务全程（grep + 读文件 + WebFetch）。
