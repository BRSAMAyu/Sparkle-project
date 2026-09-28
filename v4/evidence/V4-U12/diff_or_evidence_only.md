# V4-U12｜自我锚与光子：保留最新商业决定（diff / evidence only）

分支 `agent/v4/u12`，自 main@c94afbe4 开出（main 头随 state 提交从 6df347b0 前进一格，
两 commit 均为 U11 销账/fleet 状态，无代码差量）。不 push。

## 一句话设计

奖励四家族（leaderboard/photon/achievement/shop）按 D-COMM 最新商业决定**差量收口**：
活路由（`/leaderboards/self-anchor`、`/photon/redeem-pro`、`/photon/history`）已是一致
令牌语法（context.colors/typo/space + DS 组件，与 U11 同判零重写），本卡补齐真实缺口
——①兑换动作幂等重入守卫（双击/重放不产生第二次 POST，服务端月顶屏障之上的客户端
第一道闸）；②自我锚失败面 N9 勘误（{error} 占位泄漏通道关闭，人话固定模板与 redeem
面同纪律）；③三验收面移动端钉（幂等重放钉、付费墙反例钉、庆祝关闭钉、HIDDEN 商店钉、
flame_level 分离钉）。

## 1. 卡面 → 差量裁决总表

| 卡面/验收 | 裁决 | 依据 |
|---|---|---|
| 复用最新 self-anchor 和 photon/redeem-pro 活路由 | **EVIDENCE_ONLY**（零改动差量举证） | 活路由已在：`LeaderboardRoutes.selfAnchor`（D-COMM-1 唯一路由面）+ `PhotonRoutes.redeemPro/transactionHistory`（D-COMM-2 兑换出口，transfer 已撤 PH-G3）；屏面均消费 `context.colors/typo/space` + `GraphiteCardSurface`/`SparkleButton` 等 DS 组件（BATCH6B 后无硬编码） |
| 换成一致像素语法 | **EVIDENCE_ONLY（语法统一已满足）+ 勘误差量（N9 呈现纪律）** | SCREEN_FAMILIES 家族口径=同一令牌体系与呈现纪律（U11 同家族判例：已是 DS 令牌呈现即零重写）；F01 `PixelPreviewProfile.classic` 是发布默认（参考图=提案非批准），PixelFrame 换装会引入 classic 视觉差量、违反「发布默认主题不换」红线，不做（记 limitations #1）。本卡补的呈现一致性=失败面 N9 人话化（self-anchor {error} 通道关闭，勘误差量） |
| 保留受限奖励 | **EVIDENCE_ONLY + 实现差量（幂等守卫）** | D-COMM-2 受限兑换语义全链已在：仅学习所得可兑（transfer_in 不计）、月顶 1 次、访客 403；引擎侧 `photon_redeem_service.redeem_pro` 原子扣减+月顶复查回滚（幂等屏障），后端回归 23 绿内含 `monthly_cap_blocks_second_redeem_and_converges` + `concurrent_redeem_exactly_one_success`。本卡补客户端重入守卫（见 §2-①） |
| 保留免费核心 | **EVIDENCE_ONLY（正反钉入测）** | self-anchor 免费只读（GET 一发，无任何 action 计费）；memory 纠正/隐私面源码零 photon/付费词表（付费墙反例钉 `rewards_family_boundary_u12_test.dart`）；引擎侧 memory_provenance/memory_settings API 零 photon 引用（grep 自证） |
| HIDDEN 商店不打开 | **EVIDENCE_ONLY（钉入测）** | `/shop` 路由仅深链兜底存在（routes.dart 挂载），全仓除 shop feature 与 routes.dart 外零 `ShopRoutes`/`'/shop'` 引用=零入口零推广；奖励四家族源码零 shop 引用已钉入测（MODULE_MATRIX shop 行「维持 HIDDEN」语义保持） |
| 验收 1：不恢复全站综合榜 | **EVIDENCE_ONLY（钉入测）** | COMM-LB 守卫既有（本卡亲跑 PASS）；移动端补路由词表钉：`LeaderboardRoutes.routes` 恰 1 条 GoRoute=`/leaderboards/self-anchor`，域内零全站榜面词（正反判别对在 `self_anchor_boundary_u12_test.dart`） |
| 验收 1：不以 flame_level 冒充付费身份 | **EVIDENCE_ONLY（钉入测）** | 引擎侧既有红线：`users.entitlement` 列注释「禁止用 flame_level 派生权益」（user.py:76-77，D17 冻结）；移动端钉：奖励四家族源码零 flameLevel 引用 + 全 mobile 零 entitlement×flameLevel 同现行（`rewards_family_boundary_u12_test.dart`） |
| 验收 2：余额/兑换来自真账本 | **EVIDENCE_ONLY + 正例钉** | PHOTON-STATUS 服务端快照单源（`getOverview` 零本地推算，客户端 UTC 月窗自算已随该端点移除）；正例钉：服务端数（balance/base/cost/days）上屏且展示常量不覆盖（错开值 4321/1777/9 判别） |
| 验收 2：重复兑换幂等 | **实现差量（重入守卫）+ 幂等重放钉** | 客户端补 `_actionInFlight` 同步守卫（§2-①）：同帧双击只开一个确认面、确认后恰 1 次 `redeem()`；成功终态封口按钮（月顶语义客户端镜像）。服务端屏障回归 23 绿；重放路径钉：成功后按钮禁用、二次触发不产生第二次调用与确认面 |
| 验收 3：可关闭庆祝 | **EVIDENCE_ONLY（正反判别钉）** | 庆祝抑制链路既有且真实：设置→情绪自适应「持续低刺激」→ `EmotionResponsiveConfig.lowStimulus()` → `SparkleConfetti` 整体短路（视觉+粒子+控制器，U-02 既有）；本卡以 mutation 判别对钉在家族最强庆祝面（rare 成就弹窗）：正常档 ConfettiWidget 在场 / 低刺激档缺席（§3） |
| 验收 3：核心记忆纠正/隐私不收费 | **EVIDENCE_ONLY（付费墙反例钉）** | 纠正/忘记/scope 唯一写链路 = `/memory/provenance` 路径族（免费）；memory 域源码零 photon/purchase/entitlement/付费词表已钉；引擎侧 memory API 零 photon 引用（grep 自证，扣减仅存于 admin/redeem-pro/契约押金三处） |

## 2. 实现差量明细（2 屏 + arb 勘误 + N9 基线棘轮下调）

**① 兑换动作幂等重入守卫（`photon_redeem_pro_screen.dart`，+18 行）：**

- `_actionInFlight` 同步守卫包住整个确认→兑换流（`_redeem()` 入口检查+置位，
  `finally` 释放）：同帧双击不再产生第二个确认对话框，重复触发返回即静默；
  取消对话框（confirmed≠true）守卫即时释放，动作可再发起。
- 与服务端月顶屏障（引擎 `redeem_pro` 原子扣减+月顶复查回滚）叠加成双闸：
  客户端不发出第二次动作，服务端对到达的重复请求同样只结算一次。
- 兑换成功终态既有 `capped` 判定（含 `_lastResult.ok`）继续封口按钮——重放路径
  在 UI 不可发（测试钉死）。

**② 自我锚失败面 N9 勘误（`self_anchor_screen.dart`，13 行 ±）：**

- 原失败文案模板 `leaderboardSelfAnchorLoadFailed` 携带 `{error}` 占位、调用面直传
  原始 `Object error`——异常细节直达用户面，与同卡 redeem 面纪律（N9：细节进日志、
  UI 人话固定模板）不一致。本卡勘误：arb zh/en 两份模板改固定人话文案
  （「自我锚加载失败。你的数据没有丢，稍后再试一次。」）、删 `{error}` 占位元数据；
  屏幕改 `debugPrint` 记日志 + 无参 getter 消费。
- **N9 棘轮下调（守卫协议内 cleanup batch）**：arb {error} 260→256、bareCatchVar
  76→72、catchVarToString 78→77；`--update-baseline` 后 PASS（256/256 棘轮持平），
  基线 JSON 差量随本卡入库。

**③ l10n（铁律 6）：**

- arb 源勘误 2 处（zh/en 同步，非手改生成物）+ `flutter gen-l10n` 再生
  （生成 diff = 该键签名 getter 化与双语文案，逐字可再生）；零新增键、零删键。
- 已知调用面唯一（self_anchor_screen），无其他消费方受签名变更影响（grep 自证）。

## 3. 测试差量（3 新文件 14 用例，每验收面一正一反）

- `photon_redeem_idempotency_u12_test.dart`（5）：账本真值正例（服务端数上屏、
  常量不覆盖）/ 幂等正例（确认一次=恰 1 调用+服务端 balance_after 上屏）/
  **幂等重放钉**（同帧双击=1 确认面 1 调用；成功后按钮禁用、二次触发零调用零确认面）/
  不足预判诚实面（基数不足文案+按钮禁用+零调用）。
- `self_anchor_boundary_u12_test.dart`（3）：失败面正例（人话模板+异常细节零直出+
  重试可达）/ 通道关闭反钉（arb 零 {error} 占位+调用面零实参，源扫描）/
  全站榜反钉（路由恰 1 条自我锚+域内零全站榜面词，注释豁免扫描）。
- `rewards_family_boundary_u12_test.dart`（6）：**庆祝关闭正反判别对**（rare 弹窗：
  正常档 ConfettiWidget 在场 / 低刺激档缺席——mutation 判别，非装饰位）+ 光子/自我锚
  零不可关庆祝源 + **HIDDEN 商店钉**（奖励四家族零 shop 入口）+ **flame_level 分离钉**
  （四家族零 flameLevel + 全 mobile 零权益派生同现）+ **付费墙反例钉**（memory 域零
  付费词表+纠正走 /memory/provenance 免费链路正锚）。

## 4. 零触碰面自证

- RF-06 三冲突面（dashboard_screen/compact_status_bar/task_execution_screen）、
  `app/routes.dart`、`tokens_v2`/theme 通道零触碰（`git diff --name-only` grep 自证）。
- `backend/app/api/` 零触碰 → OpenAPI+BA-ROUTES 机械门不触发（BA-ROUTES 亲跑 PASS：
  621 gateway ↔ 1015 engine，169 ledgered diffs 与基线持平）；backend 全域零 diff。
- proto/迁移/生成文件（SQLC、buf 产物）零触碰；`mobile/lib/gen` 为 gitignored 实体
  复制（主检出 cp -R），l10n 变更仅经 arb 源 + gen-l10n 再生。
- HIDDEN 商店零重开：不新增任何 `/shop` 入口/推广位（既有深链兜底路由保持）。
- mock/demo 语义零重写：demo 模式兑换快照诚实空态（既有行为）由
  `photon_surface_norm_test.dart` 既有套件回归覆盖（本卡回归绿）。

## 5. 参考图与令牌

参考图=提案非批准：本卡零参考图移植、零主题切换、零新颜色/新像素资产；UI 全部消费
既有 `core/design` 令牌（DS.* / context.colors/typo/space/radius）。像素 preview 通道
（F01/F02）未在本卡面接入 PixelFrame 换装（classic 零差量红线，见 limitations #1）。
