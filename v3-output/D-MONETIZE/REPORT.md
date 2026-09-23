# D-MONETIZE · 光子经济闭环审计 + 价值增量型盈利设计 v2 + 分发物料清单

> D 线研究 Worker ｜ 2026-09-22 ｜ worktree wt237（分支 `wt237-d-monetize`）
> 使命：①光子经济闭环审计（文字版闭环图 + 失衡风险 + 调参建议）；②价值增量型盈利设计 v2（兑 Pro 之外 2-4 个付费面候选）；③分发物料清单（海报/二维码/渠道/落地页/自动生成面）。
> 边界申报：**纯文档零代码**；全部 file:line 引用在 wt237 树内真实读文件核实；所有竞品定价为**公开常识级记忆，未一手核实（方法声明见 §5）**；所有自有定价为**估算锚点**（继承 `v3-output/DL-D-R1/MONETIZATION.md` 口径），上线前需按真实转化数据校准。
> 上游依赖：`v3-output/D-REDEEM`（兑换码付费闭环）、`v3-output/D-COMMUNITY/DESIGN.md`（光子定位裁决 §3.1-C）、`v3-output/PHOTON-CALIBRATION`（1500 汇率校准）、`v3-output/TOUR/REPORT.md`（活栈实测数据）、`v3-output/DL-D-R1/GROWTH_ASSETS.md` + `MONETIZATION.md`（R1 研究稿）、`v3-output/D-LANDING`（落地页与海报文案稿）。

---

## 0. 结论速览（TL;DR）

1. **光子经济是带审计、幂等、并发安全的成品系统，但存在一个 P0 级铸币洞**：契约押金（stake）创建时**不预扣、不校验余额、无上限**（`schemas/achievement.py:189` 仅 `ge=10`），完成即发 `stake × 2.0`（`achievement_engine.py:2965-2995`），失败扣款在余额不足时静默失败（`achievement_engine.py:2997-3010` 捕获后仅记日志）——「空手立约、诚实履约、白得双倍」的合成光子路径在语义上成立。建议首优先级关洞（§1.6 建议 1）。
2. **收入-消耗结构单边倾斜**：收入面 5 个来源（首胜/成就/契约/combo/访客种子）中 combo 与契约可被「批量归档任务」放大——TOUR 活栈 10 冲刺 × 7 任务刷出余额 20→5050（`v3-output/TOUR/REPORT.md:24`），是诚实日均收入（30-80）的 **60-160 倍单日脉冲**；消耗面仅 1 个有界出口（兑 Pro，1500/月顶 1 次）+ 已降级商城（唯一入口深埋 `streak_details_screen.dart:415`）。获取 >> 消耗的存量池会持续累积（月顶兜底了兑换面，但堵不住「基数」与商城库存的通胀）。
3. **反刷红线现状健康**：XP/光子/`photon_balance` 确认不在任何在用榜面（光子榜代码仍在引擎但被 `check_rule_comm_lb_leaderboard_unrouted.py` 双钉守卫钉死为不路由）；`transfer_in` 被排除出可兑换基数（`photon_redeem_service.py:72-83`）；移动端 `/photon/transfer` 路由已撤（`photon_routes.dart:8-11`，幽灵屏挂账债务台账 #11）；访客禁转账/禁兑换（`photons.py:143-148、269-275`）。一个语义缝隙：访客种子 1000 光子以 `grant_achievement` 类型入账（`guest_seed_service.py:1522-1533`），升级转正后**计入可兑换基数**，弯曲「学出」口径（§1.5 R3）。
4. **盈利设计 v2 推荐 3 个价值增量 SKU**（期末冲刺周期包 / 深度诊断加油包 / 学期星图年报），全部复用已上线的 entitlement × budget_matrix 骨架——**Pro 与 free 的全部工程差异今天已经存在且可配置**（run 预算 4 倍：`settings.py:432-437`；模型钳制 ceiling：`llm_router.py:408-436`），付费化的工程增量只在「计时权益 + 支付通道」两处；光子永不售卖（R1 裁决维持，写入定价页即是叙事）。
5. **分发物料可即刻从仓内资产组装**：A2 海报文案稿与色值/版式规格已有（`deploy/landing/poster-copy.md`），渠道码纪律已有（`deploy/README.md`），端内海报工坊管线现成（`share_poster_service.dart` + `poster_studio_screen.dart` + 6 张分享卡，自带 `sparkle://` 深链）——**每个用户生成的分享海报本身就是分发物料**；缺口集中在 4 个「人工/流程项」：真二维码成品、APK 直链、ICP 备案域名、印刷成品。

---

## §1 光子经济闭环审计

### 1.1 文字版闭环图

```
                              ┌─────────────────────────── 收入面（5 源）───────────────────────────┐
                              │                                                                      │
  学习行为事件                  │  ① 每日首胜 grant_daily_first   30/日（当日幂等）                      │
  （任务完成/归档、契约结算、    │  ② 成就解锁 grant_achievement    一次性词表 32 笔 / 总池 19,210        │
    成就达标、连击）  ────────▶ │  ③ 连击加成 grant_bonus         combo≥3 时 combo×10 / 事件（5min 窗）   │
                              │  ④ 契约完成 grant_contract      stake×2.0（stake 不预扣⚠️，无上限⚠️） │
                              │  ⑤ 访客种子 guest_welcome       1000（typed grant_achievement⚠️）     │
                              │                                                                      │
                              └──────────────────────────────┬───────────────────────────────────────┘
                                                             ▼
                                   users.photon_balance（混桶单字段，无来源分桶）
                                   photon_transaction_history（审计真源，balance_before/after 双列）
                                                             │
                              ┌──────────────────────────────┴───────────────────────────────────────┐
                              ▼                         消耗面（4 去）                                │
  ① 光子兑 Pro redeem_pro：1500/次 × 月顶 1 次 × 7 天，基数=四类学习收入净额（transfer_in 排除）◀─ 唯一「学出会员」出口
  ② 商城购买 purchase：16 个种子商品 50-3000（皮肤/称号/消耗品/加成），面已降级、入口深埋
  ③ 契约失败扣押金 deduct_contract_stake：stake 全额（余额不足时静默失败⚠️）
  ④ P2P 转账 transfer_out：引擎端点仍在（网关 wildcard 代理），移动端路由已撤；transfer_in 不入兑换基数
                                                             │
                                                             ▼
                              可兑换基数（审计流水重放，独立于余额）──▶ 兑 Pro 判定（月顶→基数→余额）
```

经济真源双轨：**余额**（`users.photon_balance`，混桶，`photon_service.py:120-167` 行锁 + 5min TTL 缓存 :556-580）与**可兑换基数**（`photon_redeem_service.get_redeemable_base :121-144` 纯审计流水重放）。两者并列诚实区分，是 PHOTON-STATUS 兑换前快照的同一真源（`api/v1/photons.py:310-354`）。

### 1.2 收入来源全表（金额 / 触发 / 防刷判据 / 上限现状）

| # | 来源 | 交易类型 | 金额 | 触发点 | 防刷判据（现状） | 上限现状 | 证据 |
|---|---|---|---|---|---|---|---|
| 1 | 每日首胜 | `grant_daily_first` | **30/日** | 每日首次达标事件 | Redis 当日标记（24h TTL）+ DB 唯一部分索引（`related_item_id="daily_first:<ISO日期>"`，`ON CONFLICT DO NOTHING` 仲裁并发双发） | **30/日**（结构自限） | `achievement_engine.py:2726-2761`；`photon_service.py:29-39、210-282`（PHOTON-IDEM） |
| 2 | 成就解锁 | `grant_achievement` | 单笔 10-5000，词表 32 笔共 **19,210**（一次性池） | 成就解锁事件（任务完成/契约/打卡驱动） | 成就一次性解锁 + 发放幂等（读侧查重 `related_item_id=achievement_id` + Celery 补偿重试带同键去重） | 一次性（无重复领取面） | `achievement_seeds.py`（32 处 photon quantity）；`achievement_engine.py:1778-1826、1631-1660`（队列背压→本地重试） |
| 3 | 连击加成 | `grant_bonus` | `combo×10`（combo≥3 才发） | 5 分钟窗口内连续解锁 ≥3 个成就 | Redis combo 计数器（5min TTL）；`related_item_id` 每事件唯一（合法重复达标不互吞） | **无日上限**——窗口内每轮连击各发一次 | `achievement_engine.py:2642-2695`（:2658 金额式，:2670-2694 发放+列宽修复注） |
| 4 | 契约完成 | `grant_contract` | `stake × reward_multiplier`（默认 ×2.0） | 契约到期且 `current_days ≥ target_days` | 「押金风险」是唯一行为判据——**但押金不预扣、创建不校验余额、schema 无上限（仅 `ge=10`）** | **无上限** | `achievement_engine.py:2965-2995、2905-2934`；`achievement_engine.py:2876-2895`（create_contract 无托管）；`schemas/achievement.py:189`；`models/achievement.py:273、286` |
| 5 | 访客种子 | `grant_achievement`（source `guest_seed:welcome_bonus`） | **1000 一次性** | 访客体验账号初始化 | 无（onboarding 补贴） | 一次性 | `guest_seed_service.py:1511-1533` |

支出型同步扣减（进基数负项）：`deduct_contract_stake`（契约失败/取消，`achievement_engine.py:2997-3010`；取消路径 `api/v1/achievements.py:397-434`）；`penalty` 类型已声明但**生产代码零调用**（仅出现在基数词表 `photon_redeem_service.py:80-83`）。

### 1.3 消耗去向全表

| # | 去向 | 单价 | 有界性 | 可达性 | 证据 |
|---|---|---|---|---|---|
| 1 | **光子兑 Pro**（「学出会员」） | 1500 光子 / 7 天 Pro（`settings.py:147-148`，2026-09-22 由 3000 校准） | **月顶 1 次**（`settings.py:149`；月顶即幂等屏障 + 扣减行锁串行化复查，`photon_redeem_service.py:255-358`）；基数限四类学习收入（`transfer_in` 排除，:72-83）；访客 403（`photons.py:269-275`） | **1 跳**：「我的」tab 常驻 tile（`profile_screen.dart:683-696`，V13-MAJORS M-03）；商城 appBar 次级入口（`shop_screen.dart:50-62`）；深链 `/photon/redeem-pro`（`photon_routes.dart:12、24-31`） | `photon_redeem_service.py` 全文；`api/v1/photons.py:254-306` |
| 2 | 商城购买（skin/title/consumable/boost/visual_element） | 种子商品 50-3000（皮肤 500/800/1500/3000；称号 200/600/1200/2500；消耗品 100/400/300；加成 80/150/50/1000） | 无个人限购面；扣减走原子条件 UPDATE（负余额拒绝）；流水类型 `purchase` | **降级面**：全 app 唯一入口 = 连续记录详情页按钮（`streak_details_screen.dart:415` → `/shop`，`shop_routes.dart:15`） | `shop_seeds.py`；`shop_service.py:410`（购买流水）；D-COMMUNITY DESIGN §3.2「商城继续降级」 |
| 3 | 契约失败押金 | `stake` 全额 | 「风险」语义本体——但余额不足时 `deduct_photons` 抛 ValueError 被捕获仅记日志，**实际零损失** | 契约创建面在成就域 | `achievement_engine.py:2997-3010`（:3004 deduct；:3006-3009 except 吞掉） |
| 4 | P2P 转账 | 单笔 ≤10000（`schemas/photon.py:88-93`） | 反刷敏感已撤退：移动端路由已撤（幽灵屏 `photon_transfer_screen.dart` 保留未删，债务台账 #11）；引擎端点仍在且网关 wildcard 代理（`proxy_routes.go:1147-1152`）；访客 403（`photons.py:143-148`）；`transfer_in` 不入兑换基数 | 深链落 errorBuilder 兜底 | `photon_routes.dart:8-11`；`photons.py:122-185`；`photon_service.py:600-697`；`docs/engineering/KNOWN_CODE_DEBT_LEDGER.md:49` |

### 1.4 反刷红线现状盘点（结论：在用面全绿，三处登记在案）

| 红线 | 现状 | 证据 |
|---|---|---|
| XP/光子/flame 禁入榜 | ✅ 在用榜面（自我锚 7 日视图 + 小队完成度榜）只用 sprint-completion 口径；引擎残留 `PHOTON/PHOTON_WEEKLY` 榜型代码（`leaderboard_service.py:98-100、769-826`）但**不路由**：mobile 路由文件不挂 LeaderboardScreen + 网关 leaderboards 组 wildcard-only，两不变量由守卫钉死 | `scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py`（全两扫描 + escape hatch）；TOUR 实证「XP/光子/时长未入榜」（`v3-output/TOUR/REPORT.md:53`） |
| 能力门控唯一判据 = entitlement | ✅ O-04 冻结：`flame_level` 永不参与判级；模型钳制与 run 预算派生只读 `users.entitlement`（+`entitlement_expires_at` 惰性到期降级），未知一律 free 宁降不升 | `core/entitlement.py:39-66`；`llm_router.py:84-104、408-436`；`budget_matrix.py:44-49、76-97`；网关同语义双侧 `user_context.go`（D-REDEEM §1） |
| 光子不可人民币直购 | ✅ 全仓无光子充值面；`POST /photons/adjust` 为 admin 专属（`get_current_active_superuser` + Idempotency-Key 强制，`photons.py:188-250`） | D-COMMUNITY DESIGN §3.1-B 否决裁决（「禁止任何能力门控读 photon_balance」立为新守卫） |
| 兑换基数封堵小号互转 | ✅ 收入词表白名单（四类 grant + combo）天然排除 `transfer_in`；`transfer_out` 也不返还基数 | `photon_redeem_service.py:72-83、121-144` |
| 访客隔离 | ✅ 访客禁转账（:143-148）禁兑换（:269-275），以 JWT `is_guest` 声明为准（修复过旧演示常量绕过） | `api/v1/photons.py` |

### 1.5 经济失衡风险点

**R1（P0）契约押金三无 = 合成铸币洞。**
`ContractCreateRequest.photon_stake` 仅 `ge=10` 无上限（`schemas/achievement.py:189`）；`create_contract` 不预扣押金、不校验余额、无押金托管（`achievement_engine.py:2876-2895`——只查「无活跃契约」即落库）；完成时发 `stake×2.0`（:2965-2995）；失败/取消时扣款对余额不足者**静默豁免**（:2997-3010 except 仅日志；取消路径 `achievements.py:397-434` 同型）。净效果：余额 0 的用户立 `stake=10^6` 契约并履约，即无中生有 2×10^6 光子——**「押金风险」这一唯一行为判据对穷人失真，光子与学习行为的锚定被打开无限印钞口**。它同时污染可兑换基数（`grant_contract` 在收入词表内）。当前无变现出口直连现金，月顶 1 次兜住了兑换面，但商城库存与「基数」叙事即刻通胀。

**R2（P1）burst 收入与诚实收入差 2 个数量级，激励指向「归档吞吐」而非「学习效果」。**
TOUR 实测：诚实日均 30-80（`v3-output/TOUR/REPORT.md:78`）；同一报告中 10 冲刺 × 7 任务批量归档（`actual_minutes≈0`，未等真实学习时长）余额 20→5050（:24）。放大器是 ③combo（5 分钟窗口可多轮各发）+ ②成就批量解锁 + ④契约（冲刺叙事天然鼓励立约）。收入数量由**任务归档计数**驱动，与北极星「学习效果」（后测增益/复习命中率，CP-04~08 口径）无耦合——「刷得快 = 赚得多」与「学得好 = 赚得多」是两条激励曲线，当前系统在前者。

**R3（P1）访客种子混入「学出」基数。**
种子 1000 以 `grant_achievement` 类型入账（`guest_seed_service.py:1522-1533`），`related_item_id="guest_welcome"` 但**类型在收入词表内**；游客转正改写同一用户行（`api/v1/auth.py:1036-1060`），故这 1000 直接进入可兑换基数（1500 的 2/3）。PHOTON-CALIBRATION 的 1500 定价依据是「诚实学习收入 30-80/日」，种子补贴未计入模型——转正用户达标时长被系统性低估。量级小（≤1000/人、一次性），但破坏的是**口径纯度**：「仅合同/首胜/成就所得可兑」的用户可见承诺（`photons.py:283` 拒绝文案）与实现不符。

**R4（P2）消耗面太浅 + 商城效果虚标。**
唯一有界出口（兑 Pro）月吞 1500；商城 16 商品合计标价 19,290 但入口深埋（全 app 仅 1 个按钮）且五类效果中 consumable/boost 的实际效果是**桩**：`use_consumable` 返回效果字典但未接线任何乘数（`inventory_service.py:404-429` 全部 `TRACKED(TD-006)`——「光子加成卡 ×1.5」在发放路径无任何读取点）。若商品 UI 承诺了效果，属诚实性缺口；经济面上消耗萎缩 → 存量池单调上涨（获取 >> 消耗）。

**R5（P2）死亡螺旋评估：不成立，但要盯两个前置指标。**
「获取>消耗 → 贬值 → 停赚」螺旋的古典触发条件（赚了没处花）被月顶兑换的部分对冲：强投入用户达标后每月稳定烧掉 1500。真正要盯的是：①**兑换后剩余存量**的边际效用（兑完 Pro 后多出来的光子只能买失效的商城道具）——若「达标 → 兑换 → 余额归零」循环中断，光子叙事随之失效；②收入构成占比（契约类若因 R1 被刷而占比畸高，1500 定价的可信叙事崩塌）。两项都可从 `photon_transaction_history` 直出（PHOTON-CALIBRATION §⑤ 数据钩子已登记，status 端点聚合即可，零新埋点）。

**R6（对齐度）激励与北极星的耦合点盘点。**
耦合良好的：首胜（每日回到学习动作）、契约（承诺机制，押金-倍率的损失厌恶结构）、成就（里程碑正反馈）。耦合缺陷的：金额全部锚定**计数**（次数/连击数/stake 数），无一锚定**效果**（掌握度增量、复习命中、后测提升——北极星战役 C 线正在验证的量）。方向上不需要推翻，需要在加成权重里引入效果门槛（见建议 2）。

### 1.6 调参 / 机制建议（5 条，不动代码；每条含预期效果与衡量指标）

| # | 建议 | 预期效果 | 衡量指标（数据落点现成） |
|---|---|---|---|
| 1 | **契约押金托管化**：创建即预扣 stake（退还是完成结算的一部分），schema 加上限（如 `le=500` 或 `le=余额`），取消/失败照实扣。若暂不动代码，先在产品面把「押金」文案改口径为「目标承诺金（完成双倍返还）」并在定价页披露 | 关闭 R1 铸币洞；恢复「押金=真实风险」的承诺语义；契约类收入重获反刷判据 | ①契约类收入占可兑换基数比（`by_type` 重放，`photon_service.py:828-889`）；②stake 分布 p95（`spark_contracts.photon_stake`）；③失败契约实际扣款成功率（现状静默豁免率=失败数-`deduct_contract_stake` 流水数，两表对账） |
| 2 | **combo/加成收入引入效果门槛**：连击加成只对带真实学习时长（`actual_minutes>0`）或掌握度增量的任务归档发放；可将 combo 金额改锚「当日效果增量」分档而非纯计数 | 压缩 R2 脉冲（5050 级 burst → 数百级）；把「学得好=赚得多」写进汇率 | ①日均收入分布 p50/p95（status 端点聚合，`photons.py:310-354`）；②burst:honest 比（单日 >500 的账户占比）；③收入-后测增益相关性（CP-04~08 数据 join 流水） |
| 3 | **访客种子出表**：`guest_welcome` 从可兑换基数词表移出（或种子改用非词表类型），营销预算与学习收入分账 | 修复 R3 口径纯度；1500 定价依据（PHOTON-CALIBRATION §0）重新成立；「仅学习所得可兑」文案与实现一致 | ①转正用户基数中种子占比（流水重放 `source='guest_seed:welcome_bonus'`）；②达标时长分布（首笔 1500 累计天数）修复前后对比 |
| 4 | **开第二个经常性消耗口（光子侧）**：优先把商城 `streak_freeze/hint_reveal` 两类真实接线（其余五类先下架止血），并给商城一个不深埋的入口（如「我的」页光子 tile 旁二级入口）；皮肤/称号维持低频装点定位 | 存量池获得非通胀消耗；「赚→花→再赚」循环在两次兑换窗口之间不断流；效果虚标缺口（R4）同步消除 | ①商城月购买渗透（`purchase` 流水户数/活跃数）；②人均月消耗/人均月收入比（健康区间建议 0.5-1.0，>1 消耗通缩、<0.3 池子膨胀）；③`use_consumable` 效果领取率 |
| 5 | **经济健康仪表三指标 + 校准节奏**（合并 PHOTON-CALIBRATION §⑤ 钩子）：收入构成占比、兑换渗透率（redeem_pro 户/活跃户）、达标天数分布；30 天复议一次 1500/7d/月顶三元组，规则预写死：强投入达成 <50% → 降价或加收入面；休闲面出现可达路径 → 收紧词表而非涨价 | 经济调参从「一次性校准」变成可运维循环；任何 R1/R2 类漏洞进入构成占比告警视野 | 三指标阈值：兑换渗透 5-15%（健康）；契约类收入占比 >40% 即告警（R1 前兆）；p95 日收入 >10×p50 即告警（R2 前兆）——数据全在 `photon_transaction_history`，零新埋点 |

---

## §2 价值增量型盈利设计 v2

### 2.0 现状与边界

- **唯一现金付费面 = 兑换码**（D-REDEEM：`SPARK-XXXX-…` 批次铸造 + 原子核销 + `entitlement_expires_at` 到期惰性降级，引擎/网关四读点全接）——它证明的是**核销链路**，不是定价面；第 1 期微信支付未建（`DL-D-R1/MONETIZATION.md` §5 分期裁决）。
- **唯一非现金付费面 = 光子兑 Pro**（§1.3-1）——它是「时间换价值」的第三条路，不产生现金。
- **Pro 与 free 的全部产品差异今天已工程化且可配置**（这是 v2 设计能落地的地基，file:line 实测）：
  - run 预算 4 倍：free `{150k tokens, $0.5, 50 tool calls, 30min}` vs pro `{600k, $2.0, 200, 60min}`（`settings.py:432-437`，派生面 `budget_matrix.py:76-97`，O-07）；
  - 模型钳制：free 钉 ceiling=fast（`settings.py:765-766` `FREE_TIER_MODEL_CEILING="fast"`；钳制实现 `llm_router.py:408-441`，判级真源 `users.entitlement` :84-90）；
  - 到期自动落 free：`entitlement_effective`（`core/entitlement.py:50-66`）双端四读点（引擎 user context/run budget、网关 chat snapshot/chatflow fallback，D-REDEEM §2）。
- **继承的裁决红线**（FLEET-BRIEF §四.3 + COMMERCIAL_MODEL.md + MONETIZATION §1）：免费闭环行为零变化；不搞阉割胁迫（进度/数据永属用户，额度用尽=诚实终态非恐吓）；光子不卖；学生锚点=奶茶价；按学期制周期不按月薪订阅。

### 2.1 候选 SKU（3 个；每个含目标人群/价值主张/定价锚/期末备考增益路径/防伤害判据/架构衔接）

#### SKU-A · 期末冲刺周期包（Exam Sprint Pass）—— 主推

| 维度 | 内容 |
|---|---|
| 目标人群 | 北极星画像本体：期末只剩 1-6 周的大学生；已用过免费主线完成至少一次冲刺/契约（有行为数据基座） |
| 价值主张 | 「冲刺这两周，让它开全力」——深度讲解（模型放开到 fast 以上全层）、单次问答更深（run 预算 4 倍）、错题诊断/拆解不限次到日常预算上限。卖的是**冲刺期的深度与吞吐**，不是「解锁完整版」 |
| 定价锚（估算） | **¥19.9 / 期末窗口 6 周**（继承 MONETIZATION §3.4）；窗口真实对应考试季限售，不做假稀缺；学生无感区间（奶茶价 ×2） |
| 期末一周备考增益路径 | 期末周 → 建冲刺/契约（exam_sprint 面已齐）→ 立即生效 pro 判级（`entitlement_expires_at` 设窗口末日）→ 模型层全档可用（`llm_router` 钳制放行）+ run 预算 4 倍（`budget_matrix` 读同一判级，零新代码路径）→ 错题/薄弱点深拆与 60min 级 agent run 承载整章复习 → 考完窗口到期自动落回 free（惰性判级，无 job 也不降错） |
| 防伤害判据 | ①免费主线零变化：free 的 ceiling/预算默认值不动，本 SKU 只是临时提额；②到期降级方向恒 pro→free、免费用户永不看到「倒计时逼单」；③不与光子兑换互斥——已用光子兑 Pro 的用户买包按日顺延叠加（复用 D-REDEEM `_grant_pro` 叠加语义，`redeem_service` 核 + 永久 pro 保护） |
| 架构衔接（file:line） | 判级与叠加：`services/redeem_service.py:_grant_pro`（D-REDEEM 产物）；到期降级：`core/entitlement.py:50-66`；生效无需新表：`entitlement_expires_at` 单列即可承载（窗口=一次长 duration 授予）；支付缺口期可用兑换码 SKU 形制预售（`api/v1/redeem.py` admin 批量铸码） |
| 对标（方法声明见 §5） | Quizlet Plus 考季包装（学期折扣）、Duolingo Super 的「周期性限时促销」节奏——共同点是**把订阅切成学期心理账户**；差异点是我们按真实考试窗口限售而非自动续订 |

#### SKU-B · 深度诊断加油包（次卡，非订阅）

| 维度 | 内容 |
|---|---|
| 目标人群 | 免费主力用户中撞到 ceiling 的活跃者：`FREE_TIER_DOWNGRADE` 触发过降级、或 BUDGET_EXCEEDED 终态出现过的用户 |
| 价值主张 | 「这份错题值得一次深度拆解」——按次购买单次/包日深度档，平时完全免费的产品，偶尔需要一次开挂 |
| 定价锚（估算） | **¥6 / 7 天深度档**（一杯奶茶锚点，MONETIZATION §3.2）；可叠 3 次包 ¥15 |
| 期末一周备考增益路径 | 刷题/模考周 → 免费档深度用尽出现诚实终态（BUDGET_EXCEEDED 明确终态 UX 已上线，`chat.py:517`、`run_state_machine`，不进自我修正循环）→ 「加油包」入口在此刻出现（价值已兑现时刻触达，MONETIZATION §4.2 纪律：永不在打断时刻弹窗）→ 7 天内 ceiling 放开 + run 预算提升 → 期末过自动回落 |
| 防伤害判据 | ①免费额度**永久存在且不缩水**（加油包是增量不是赎回）；②终态文案诚实列「免费额度已用完」而非「再不付费学习进度将丢失」（MONETIZATION §1.3 红线）；③不设首购优惠倒计时/限时弹窗类转化施压 |
| 架构衔接 | 计时生效复用 SKU-A 的 `entitlement_expires_at` 路径（短窗口授予）；触达点挂 BUDGET_EXCEEDED 终态；「因额度无法完成的 high-value intent」计数已在观测清单（COMMERCIAL_MODEL §4），即本 SKU 的需求数据源 |
| 对标 | Khanmigo 低价学习者档、Duolingo 体力/宝石的「临时续力」心理——但我们卖**算力时长**不卖体力（无体力系统，不制造人为疲劳） |

#### SKU-C · 学期星图年报（免费摘要卡 + Pro 完整版）

| 维度 | 内容 |
|---|---|
| 目标人群 | 全量学期活跃用户（含免费）；二次目标：收到分享卡的非用户（分发面，接 §3） |
| 价值主张 | 「这学期你点亮了 217 颗星」——星图生长轨迹、知识点征服路径、契约履约史、Aurora 观察到的习惯演变；免费给 1 张可分享摘要卡，Pro 给完整交互式年报 |
| 定价锚（估算） | **¥9.9 / 份** 或并入 Pro/期末包（MONETIZATION §3.5）；生成成本可控（数据导出面现成 `data_export.py:55`，celery 离线批渲染，LLM 排版文案约 3k tokens ≈ ¥0.1-0.3/份——估算） |
| 期末一周备考增益路径 | 期末周是「复盘叙事」最强时刻：年报把一学期的星图变成可晒物料 → 分享卡自带 `sparkle://` 深链回流（同现有成就卡机制，`achievement_share_bottom_sheet.dart:696`）→ 同学扫码进落地页 → 游客体验 → 转正；对付费者，年报在备考周提供「复习优先级」的过去-现在对照（最暗的星），有真实备考功用而不只是纪念品 |
| 防伤害判据 | ①免费摘要卡必须是**完整可晒的一张图**（不是打码预览）——免费用户获得社交货币，Pro 获得深度；②年报数据全部来自用户自己的真实流水（诚实性红线：仪表数字必须有真源，FLEET-BRIEF §四.4）；③不设「分享解锁」裂变胁迫 |
| 架构衔接 | 端内海报管线现成（§3.4）；批量渲染走 celery（beat/队列拓扑现成，`celery_app.py:1020-1060` 区间）；数据导出 `data_export.py`；分享卡模板族直接复用 6 张 share_cards 的 RepaintBoundary 管线 |
| 对标 | Spotify Wrapped / 网易云年度报告范式（年度叙事 = 天然分发事件）；Quizlet 的学习进度统计页 |

**落选/延后备案**（继承 R1 裁决，v2 不翻案）：光子直购能力（D-COMMUNITY §3.1-B 否决：刷学习量换算力必催生刷分）；长期记忆扩容单卖（MONETIZATION §3.3：并入 Pro，单卖=「记忆要丢了」恐吓式付费）；团队/班级版（转化效率最高的校内渠道，延后到有真实用户后，MONETIZATION §3.7）。

### 2.2 组合与节奏

1. **第 0 期（已落地）**：兑换码（D-REDEEM）+ 光子兑 Pro（D-COMM-2 + PHOTON-CALIBRATION）——核销与判级骨架全通，零支付通道。
2. **第 1 期（v2 首推）**：SKU-A 期末包以**兑换码形制**预售/线下发放（评委、种子群、社团合作），验证「有人愿意为冲刺期深度付钱/换取」——零支付工程量，先校准需求。
3. **第 2 期**：微信支付 APP 支付 + 订单表 + 到期 job（beat 拓扑现成；估算 1-2 人周，MONETIZATION §5）→ SKU-A/B 现金化。
4. **第 3 期（期终事件）**：SKU-C 年报（2-3 人日，MONETIZATION §3.5/GROWTH_ASSETS §5 估算），同时点亮分发闭环。

### 2.3 升级触达与观测（每 SKU 共用）

- **触达纪律**：只在「价值已兑现时刻」（BUDGET_EXCEEDED 终态、冲刺完成结算页、年报生成完成页）出现入口；免费用户全程可见 pro 数值差异但无弹窗打扰；文案不贬损免费档。
- **统一观测面**（COMMERCIAL_MODEL §4 继承 + 本卡补充）：
  | 指标 | 定义 | 健康阈值（首版建议） |
  |---|---|---|
  | free 能力降级触发率 | 触发 `_clamp_tier_for_free_tier` 降级的请求占比 | 观测基线（不设阈值，用于 SKU-B 需求测算） |
  | high-value intent 受阻数 | 因额度/ceiling 无法完成的会话数 | 环比下降 = 防伤害成立 |
  | SKU 渗透率 | 付费/兑换用户数 ÷ 期活跃 | SKU-A 首期 3-8%（估算） |
  | 光子兑换 vs 现金互食 | redeem_pro 户中现金购买者占比 | 若互食显著 → 两面差异化定价（兑 Pro 7 天 vs 周期包 6 周，天然错位） |
  | 试后留存 | 期末包到期后 30 天回访率 | ≥ 免费基线（证明「体验过 Pro」未抬高不满） |
  | 每 WVPL 模型成本 | pro 侧增量成本 vs SKU 毛利 | pro 用户月成本 < 定价 30%（估算红线） |

---

## §3 分发物料清单

### 3.1 物料总表（尺寸 / 内容要素 / 二维码指向）

| 物料 | 尺寸/形态 | 内容要素（都已定稿或有仓内源） | 二维码指向 | 状态 |
|---|---|---|---|---|
| A2 竖版海报 | 420×594mm，三段式版式 | 主标语 3 选 1（推荐「错题本 2.0：从静态收录，到状态引擎」）+ 副标 + 三特性（记得住/会教/星图生长，顺序即权重）+ 底部码区；色值 10 令牌表全对照（`#FCF8F3/#825D49/#48678D` 等）；码 ≥12×12cm（2m 可扫）、引导语 ≥60pt；截图纪律：只用星图画面（AUDIT S1-S3 罪状截图禁用） | → 落地页 `https://<域名>/landing/?src=<渠道码>` | **文案稿+版式规格已定稿**（`deploy/landing/poster-copy.md` 全文；色值对照 `D-LANDING/REPORT.md §2`），缺设计成品 |
| 桌卡（现场） | A6 双面 | 正面：星图视觉 +「扫码即玩，免注册」；背面：30 秒演示动线 + 现场专码 + Wi-Fi 信息位 | → 落地页 `?src=expo0926`（现场专码版文案已在 poster-copy §四） | 要素已定稿，缺成品 |
| 易拉宝 | 80×200cm | A2 海报要素竖向放大版 + 团队/比赛信息位 | → 落地页（渠道码区分） | 同上 |
| 渠道二维码 ×N | PNG ≥1024px | 每渠道独立码，`?src=` 区分（社团/课程群/线上贴文）；落地页按 `CONFIG.channelCopy` 显示渠道专属文案 | → 落地页（**码不直接指 APK**：码不可变、APK 常新，`GROWTH_ASSETS §1.2` 裁决） | 生成 0.5h/渠道（估算，任意生成器）；渠道清单与打法 `GROWTH_ASSETS §3` 五渠道已排序 |
| APK 直链码（备用） | PNG | 仅限现场 Wi-Fi 秒下场景的备用码 | → APK 直链（`CONFIG.apkUrl`） | 按需 |
| 演示机 | 实体手机 ×2-3 | 预装 APK + `--with-demo-seed` 种子数据（`bootstrap.sh:539-566`）+ 兑换码现铸 5 枚（`generate_demo_redeem_codes.py`，D-REDEEM §5 playbook） | — | 脚本/流程全备 |
| 端内分享卡（用户自产） | 1188×2112px（396×704 逻辑 @3x） | 6 类：achievement/capsule/learning_report/node/plan/task（`share_cards/` 目录），自带 `sparkle://` 深链 | 卡内深链 → 已装用户直达对应屏；卡外二维码位（年报卡，SKU-C）→ 落地页 | **管线现成，零新增** |

**渠道码运营纪律**（继承 `deploy/README.md` + GROWTH_ASSETS §3）：每渠道独立码；每周复盘「扫码→游客创建→次日回访」三级数据（后端日志 + `business_metrics.py` 指标面可承接）；连续两周低于阈值的渠道撤码。

### 3.2 兑 Pro 屏可达路径与深链现状（二维码「最后一步」审计）

- **App 内可达性（已修好，1 跳）**：底部常驻「我的」tab → 「光子/学出会员」tile（`profile_screen.dart:683-696`，空态新用户也渲染）→ `PhotonRedeemProScreen`（资产卡两数并列 + 兑换动作卡，SPEC v1.0 必达项 2 合规，`photon_redeem_pro_screen.dart:15-19` 文档注）。次级入口：商城 appBar（`shop_screen.dart:50-62`）。
- **深链现状**：`DeepLinkService._routeMapping` 现有 10 个 host 映射，**无 photon host**（`deep_link_service.dart:14-25`）；但 `resolveRoute` 对 `/` 开头字符串直通路由（:66-69），且 `/photon/redeem-pro` 本身是已注册 GoRoute（`photon_routes.dart:12`）——即 **`sparkle://` 直连形态可用但未登记语义 host**；`/photon/transfer` 深链落 errorBuilder 兜底（路由已撤，`photon_routes.dart:8-11`）。
- **物料侧结论**：面向**已装用户**的物料（群公告/分享卡附文）可写「打开 App 的：我的 → 学出会员」路径（零开发）；若要在印刷/线上物料放「扫码直达兑 Pro」，需一张小卡登记 photon host 映射（一行代码级，属代码卡不在本卡）——本期物料一律**码 → 落地页**统一落点，不走深链，避免「未装用户扫码落空」的漏斗断点。

### 3.3 落地页最小内容结构（已交付，验收清单式复核）

`deploy/landing/index.html`（D-LANDING 交付，单文件自包含、零外链、离线可开）已具备的最小结构：①CONFIG 注释块（apkUrl/双二维码/logo/联系方式/渠道文案，全占位）；②品牌头（唯一 accent 星标）；③hero 主叙事 + 三特性卡（权重序）；④行动区：主 CTA「下载 APK」+ **游客体验指引（免注册直玩，可转正）** + 双码占位；⑤数据主权页脚（一键导出/删除 + 法务占位）。**参展前人工项 checklist**：真二维码成品 ×N（每渠道一码）、APK 直链 URL、ICP 备案域名（D-DEPLOY G6：提前 2-3 周启动）、联系方式填充、`?src=` 渠道文案逐渠道配置。部署：nginx `location /landing/`（`deploy/README.md:26-30` snippet）。

### 3.4 可自动生成的物料（仓内管线实测）

| 管线 | 产物 | 证据 | 复用方式 |
|---|---|---|---|
| 端内海报工坊（已上线） | 用户身份/成就/计划/胶囊四类 preset 海报，3 套模板，1188×2112px PNG | `share_poster_service.dart:17-19`（RepaintBoundary 396×704 @3x 捕获）+ `poster_studio_screen.dart`（presets/templates）+ 6 张 share card 组件族 | SKU-C 年报摘要卡 = 新 preset + 年报数据 payload，管线零新增（新代码属后续卡） |
| 分享深链注入（已上线） | 每张分享卡自动携带 `sparkle://achievement/<id>` 等深链 | `universal_share_service.dart:61-67`；`achievement_share_bottom_sheet.dart:696` | 用户自产海报即分发物料（每个分享 = 一次带深链的曝光）；SKU-C 摘要卡继承 |
| 渠道二维码 | 各渠道 PNG 码 | 任意生成器 + 落地页 `?src=`（`GROWTH_ASSETS §5`：0.5h/渠道 估算） | 半自动：码体生成自动化，渠道登记人工 |
| 展会兑换码现铸 | `SPARK-XXXX-…` 批次 | `scripts/devtools/generate_demo_redeem_codes.py`（D-REDEEM §5 playbook：`--count 5 --tier pro --duration-days 30`） | 现场物料（演示机 + 码卡）自动生成 |
| 年报批量渲染（待建，SKU-C 第 3 期） | 全员学期报告（图文） | 数据导出 `data_export.py:55` + celery 离线批（MONETIZATION §3.5：2-3 人日 估算） | 期终事件，非参展阻塞项 |

印刷成品（A2 海报/易拉宝/桌卡）是**设计组人工工作**——仓内提供的是定稿文案稿、色值令牌表、版式 ASCII 图、码尺寸/字号下限与截图纪律（`poster-copy.md` 全部要素），设计可直接照稿出图。

---

## §4 衡量指标汇总（三节共用仪表）

| 域 | 指标 | 健康信号 | 数据落点（现成，零新埋点） |
|---|---|---|---|
| 经济 | 收入构成占比（四类 grant 各占基数比） | 契约类 <40%；单类畸高即告警 | `photon_transaction_history` 重放 |
| 经济 | 日均收入 p50/p95、burst:honest 比 | p95 < 10×p50 | status 端点聚合（`photons.py:310`）+ 流水 |
| 经济 | 人均月消耗/收入比 | 0.5-1.0 | `purchase`/`redeem_pro`/`deduct_*` 流水 ÷ grant 流水 |
| 经济 | 兑换渗透率 / 达标天数分布 | 渗透 5-15%；强投入达成 ≥50% | `redeem_pro` 流水 ÷ 活跃；首笔 1500 累计天数 |
| 付费 | SKU 渗透 / 光子-现金互食 / 试后留存 | §2.3 表 | entitlement 列 + 订单面（第 2 期起） |
| 分发 | 渠道三级漏斗：扫码→游客创建→次日回访 | 每渠道周复盘，连续两周低于阈值撤码 | 落地页 `?src=` + 后端日志 + `business_metrics.py` |

---

## §5 诚实申报与方法声明

1. **竞品定价方法声明**：§2 对标（Duolingo Super / Quizlet Plus / Khanmigo / B 站大会员 / 网易云学生价）为**公开常识级记忆**（2024-2025 公开页面口径），本卡未做一手核实（零外部调用纪律）；引用目的仅为**数量级锚定**（订阅制心理价位带），任何 SKU 定价上线前必须按当期真实公开价与转化数据重新校准。
2. **自有定价全部为估算锚点**，继承 `DL-D-R1/MONETIZATION.md` 同一口径申报。
3. R1「铸币洞」为**代码路径语义推演**（create 无托管 → grant 无前置 → deduct 静默豁免三处 file:line 链），未做活栈攻击验证（零代码纪律，不构造攻击流量）；触发前提是用户真实履约（契约完成判定仍要求真实天数推进），实际风险量级取决于契约完成率，但**结构上必须关**。
4. TOUR 数据（5050 / 30-80）引自 `v3-output/TOUR/REPORT.md:24、78`，其口径限定（批量归档剧情、actual_minutes≈0）见该报告 §4 诚实申报 ①③。
5. 本轮**零代码改动**：worktree 内仅新增本报告于 `v3-output/D-MONETIZE/`；未跑测试/服务/模拟器/浏览器；/tmp 零产物（研究全程只读命令与管道）。
6. 引用的行号为 wt237 树 @ 撰写时点快照；`achievement_engine.py` 等热区文件行号可能在后续合入中漂移，引用语义以函数/常量名为准。

## §6 收工核查

- [x] 零代码/零测试改动：`git status --short` 仅新增 `v3-output/D-MONETIZE/REPORT.md`（交付物本体，v3-output 为 git 跟踪的交付目录）
- [x] 主仓只读：全程未写 `/Users/brsama/code/GitHub/Sparkle-project`；一切修改限于 wt237 worktree
- [x] /tmp 自清：本卡未产生 /tmp 文件（只读命令 + 管道）
- [x] 零进程/零模拟器/零浏览器（LIGHT 文档任务）
- [x] 无 .env / 凭据 / 真实联系方式写入；报告内占位符形式（`<域名>/<渠道码>`）
- [x] 交付物：本 REPORT.md（三节完整；纯研究卡无 changes.patch，同 D-DEPLOY 先例）
