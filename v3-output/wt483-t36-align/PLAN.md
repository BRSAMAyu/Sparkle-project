# wt483 · T36 移植主线对齐方案（PLAN）

- 工号：wt483（分析产出，零产品代码改动）
- 基准：主线 `Sparkle-project` main @ `530a980365262ef0e45f3229d3d5418678a01855`（worktree `wt483-t36`）；cosmos 仓 `agent/node-b/T36/1` @ `aa0263573f1a82bb7fbe131aba51e2ebcb75541f` + **未提交 WIP diff**（10 文件 +160/−191 + 未跟踪 release_flags.py / 250 行测试）
- 输入：T36 全量 diff 逐行通读；主线对应面（router.py / leaderboards.py / shop.py / inventory.py / photons.py / visual_elements.py / community.py / settings.py / proxy_routes.go / routes.dart / community_main_screen.dart / photon_routes.dart / shop_routes.dart / visual_elements_routes.dart / leaderboard_routes.dart / visual_element_provider.dart / profile_screen.dart）；裁决面（D-COMM-1/2、D18/D-COMMUNITY R3、S-03、D-MONETIZE、V3-FIX-05/08/182）；wt479 核验报告（三冲突 C1/C2/C3 + 审查注记 C4）
- 日期：2026-09-26

---

## 0. 结论摘要

**逐条裁决：原样采纳 0 ／ 改造采纳 8 ／ 否决 4**（改造 = 保留 T36 的「安全默认藏面」意图与大部分机制，改挂点/粒度/权威；否决项中 2 项给出替代设计）。

**一句话落地顺序**：先落「零行为变化」的后端旗权威（卡 A），再按风险从低到高挂旗——leaderboards（卡 B，D-COMM-1 固化）→ visual_elements+shop（卡 C，合流 wt482 与 V3-FIX-05）→ 移动端旗消费与 community tab（卡 D），每卡独立可回滚，回滚第一层是翻 env 旗而非 revert 代码。

**最关键风险**：双权威脑裂。若照搬 T36 的独立 `ReleaseFlags(BaseSettings)` + 移动端硬编码 `false`，主线将新增一对「治理面开旗、行为面照旧」的分叉权威——与本舰队刚修完的 V3-FIX-21 同族病（legacy bool 旁路三态门，wt480 面）完全同构；同时 router 级旗的机械移植会 403 掉 D-COMM-1 的 self-anchor 和 D-COMM-2 的光子兑 Pro 两张裁决面产品功能。

---

## 1. 事实基（本方案依赖的核验结论，全部本机复核）

| # | 事实 | 证据（主线 @530a9803） |
|---|---|---|
| F1 | 主线 leaderboards 路由 7 端点同挂一个 router，其中 `/self-anchor` 是 D-COMM-1 唯一裁决产品面 | `leaderboards.py:30,96,130,172,218,276,311`；`leaderboard_routes.dart:16`；守卫 `scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py` |
| F2 | 主线 photons 是活产品面：`/photons/redeem-pro`(+`/status`) 是 D-COMM-2 唯一有界消耗出口，balance/transactions 有活消费 | `photons.py:254,310`；`photon_routes.dart`（`/photon/redeem-pro` D-COMM-2 注）；`profile_screen.dart:694-697` 常驻 tile；D-MONETIZE 表 #1 |
| F3 | 主线 community feed 有三类 scope：默认=公共发现（public 帖全池，V3-FIX-08 已排 guest/seed cohort）、squad、goal_mates、following——后三类是 S-03/D18 认可的关系面 | `community.py:322-456`（scope 分支）；S-03 注释（community_main_screen.dart:15-19）；D-COMMUNITY R3「社群不是公共 feed」 |
| F4 | 主线 POST /community/posts 的 visibility 硬编码 `"public"` | `community.py:473-477` |
| F5 | 主线 visual-elements 无闸（V3-FIX-182 OPEN），且**核心流程**直接消费 `/visual-elements/unlock-by-achievement` | `visual_elements.py:28`（裸 APIRouter）；`task_execution_screen.dart:381-393`、`mindfulness_provider.dart:362-375`（两处均 try/catch 降级）；`profile_screen.dart:144-152` prestige 色 null→`DS.brandPrimary` 回退 |
| F6 | 主线 shop 是「降级但活」面：唯一入口深埋 `streak_details_screen.dart:427`，目录 0 行；V3-FIX-05 处方=移除该入口（OPEN） | D-MONETIZE 表 #2 + §3-4；DYNAMIC_ISSUES V3-FIX-05 行 |
| F7 | 主线 settings.py 是 40+ 个 `ENABLE_*` **内部功能旋钮**的单一 BaseSettings 权威（env_file 三路径），无任何 release-scope 旗 | `settings.py:114-130,651-1152` |
| F8 | 移动端经网关访问引擎；网关按显式组注册代理（leaderboards 是 wildcard-only，COMM-LB 守卫不变量），新端点必须显式注册否则移动端不可达 | `proxy_routes.go:1045-1050`（leaderboards 组）、`:1245-1263`（Missing Proxy Routes 列表形制）；NoRoute 仅代理 auth/*（`:814` 注） |
| F9 | T36 移动端重定向 `startsWith('/leaderboard')` 含字面量 `leaderboard`，而 COMM-LB 守卫对 routes.dart 扫 `LeaderboardScreen|leaderboard`（ignore 注豁免）——原样移植既误杀 self-anchor 又**打红守卫** | T36 diff（routes.dart 新增块）；守卫 `LEADERBOARD_UI_RE` + `_scan_mobile_routes` |
| F10 | 主线 community_main_screen 是 S-03 三 tab 协作优先布局 `[Groups, Partners, Feed]`，且历史上有「children 顺序与标签表漏改 desync」前科（41d83f83） | `community_main_screen.dart:15-19,58-64,141-147` |
| F11 | T36 diff 内混入大量与主题无关的 black 风格重排（多行→单行，leaderboards/shop/inventory/photons/visual_elements 五文件）和 git_ledger.py 工具补丁 | T36 diff --stat（+160/−191 中格式行占多数） |
| F12 | V3-FIX 号段：186-189 已占（wt480 集成重编），**190 起空闲**（全仓 grep 零命中） | DYNAMIC_ISSUES.md:137-140 + 本 worktree grep |

---

## 2. 逐条裁决（12 个改动单元）

> 图例：**改造** = 保留意图、修正后移植主线；**否决** = 不移植（替代设计另给）。

### 2.1 `backend/app/config/release_flags.py`（新文件：ReleaseFlags BaseSettings + require_release_flag 工厂）— **改造**

T36 的机制内核值得要：**安全默认 False、FastAPI dependency 工厂、可单测**。但**权威归置必须改**：

- **否掉**：独立第二个 `BaseSettings` 实例（与 Settings 并列读同一批 env 文件）+ `AliasChoices("ENABLE_SHOP", "RELEASE_ENABLE_SHOP")` 双名。这正是 F7 单一权威形制上开双权威——治理面（改哪份配置）与行为面（哪份生效）分叉，是 V3-FIX-21/186-189 刚扫完的同族病。
- **主线形制**（单一权威 + 薄视图）：
  1. 旗字段定义进 `settings.py` 的 `Settings` 类，新增显式注释分节 `# ── Release scope flags（T36 对齐 wt483 PLAN）──`，命名 `RELEASE_ENABLE_SHOP / RELEASE_ENABLE_PHOTON_TRANSFER / RELEASE_ENABLE_PUBLIC_LEADERBOARDS / RELEASE_ENABLE_PUBLIC_COMMUNITY / RELEASE_ENABLE_VISUAL_ELEMENTS`，全部默认 `False`。`RELEASE_` 前缀与既有 40+ 内部 `ENABLE_*` 旋钮显式区隔（语义：用户可见功能面的发布域闸，非内部实验开关）。
  2. `release_flags.py` 保留为**薄视图模块**（不实例化 BaseSettings）：`RELEASE_FLAG_FIELDS: tuple[str, ...]`、`release_flags() -> dict[str, bool]`（从 `get_settings()` 读）、`require_release_flag(flag_name)` dependency 工厂（T36 原样保留 403 `FEATURE_DISABLED` 语义）、`/release-flags` 响应构造函数。
  3. 测试资产（cosmos `test_t36_release_flags.py` 250 行）是资产，卡 A 改造吸收：默认值断言改 `RELEASE_*` 名、403/端点断言保留、feed 断言按 §2.6 的 scope 语义改写。

### 2.2 `shop.py` + `inventory.py` router 级 `RELEASE_ENABLE_SHOP` — **改造（与 V3-FIX-05 合并成一个裁决执行）**

- 冲突（wt479 C3 扩展）：T36 比主线裁决激进——主线立场是「商城降级但活」（D-MONETIZE 表 #2、§3-4 甚至建议未来把它做成第二消耗口），V3-FIX-05 只裁「空目录暴露→移除入口」。三份意志（T36 全关 / D-MONETIZE 降级留活 / V3-FIX-05 摘入口）必须一次裁决收口，不能两套机制。
- **裁决**：采纳旗（默认 False）+ 同卡执行 V3-FIX-05 入口移除（`streak_details_screen.dart:427` 的 `context.push('/shop')`）。目录 0 行（F6）时 403 与空列表对用户无实质差异；入口移除后旗只对深链兜底。D-MONETIZE §3-4 未来重启商城时，翻 `RELEASE_ENABLE_SHOP=True` 即恢复——旗恰好提供「降级/重启」的开关语义，这是 T36 对主线部署面的真增量。
- inventory 随 shop 同旗（equip/owned/consumables 均为商城动线，无独立活消费方——F6 佐证：消费只在 `shop_repository.dart`）。

### 2.3 `photons.py` router 级 `RELEASE_ENABLE_PHOTONS` — **否决（替代：窄旗 `RELEASE_ENABLE_PHOTON_TRANSFER`）**

- router 级旗在主线**直接 403 掉 D-COMM-2 唯一有界出口** `/photons/redeem-pro` 与活消费的 balance/transactions（F2）——与 self-anchor 同级别的误杀，wt479 报告未单列（其 §6-C1 只点了 leaderboards），本方案补正为独立冲突。
- 主线光子面里真正符合 T36「未审计面」定义的只有 `POST /photons/transfer`：移动端路由已撤（PHOTON 卡 #10 反刷裁决，`photon_routes.dart:8-14` 注），后端端点仍在、P2P 转账触反刷敏感区（`transfer_in` 已被排除出可兑换基数）。**替代设计**：窄旗 `RELEASE_ENABLE_PHOTON_TRANSFER`（默认 False）只挂 transfer 一个端点，与已裁决的移动端撤路由同向收紧；其余 photons 端点一律不挂旗（D-MONETIZE 的活出口，挂旗即违约）。`/photons/adjust` 已是 superuser 面，不需要旗。

### 2.4 `leaderboards.py` router 级 `RELEASE_ENABLE_PUBLIC_LEADERBOARDS` — **改造（双 router 拆分，self-anchor 显式豁免）**

- 冲突（wt479 C1）：主线 self-anchor 与全站榜同 router（F1），router 级默认 False = D-COMM-1 唯一产品面一并 403。**不允许**。
- **主线形制**：`leaderboards.py` 内拆两个 APIRouter——`router`（仅 `/self-anchor`，无旗）+ `public_router`（其余 6 端点：`""`/`/summary`/`/my-rank`/`/types`/`/top-three/{type}`/`/refresh-cache`，router 级挂 `require_release_flag("RELEASE_ENABLE_PUBLIC_LEADERBOARDS")`）；`router.py:280` 分别 include（`prefix="/leaderboards"` 两次）。
- 收益：默认 False 正好把 D-COMM-1「全站榜 D17 隐藏」从「无 UI 入口」升级为「UI+网关 wildcard+引擎路由三层一致」，收掉守卫 docstring 明文的网关 wildcard 已知取舍（F8）——这是 T36 对主线最有价值的一项。
- 防回归测试（卡 B 必带）：①旗 off 时 `/leaderboards/self-anchor` 200、`/leaderboards` 403；②AST/反射断言 self-anchor 路由对象 dependencies 为空；③`check_rule_comm_lb_leaderboard_unrouted.py` 重跑绿（该守卫只扫 mobile routes + 网关显式注册，引擎侧双 router 不触它，但必须实证）。

### 2.5 `visual_elements.py` 挂 `ENABLE_SHOP` — **改造（改名归位，与在途 wt482 的 ENABLE_VISUAL_ELEMENTS 合流）**

- T36 把 visual_elements 挂在 SHOP 旗下（cosmos 语境：皮肤=商城物品）。主线已有独立裁决线：V3-FIX-182（P2，OPEN）处方 `T-labs-visual-elements-gate`，且明文「推荐随 T36 release-scope 机制一并裁决」；wt482 在途做 ENABLE_VISUAL_ELEMENTS。
- **合流裁决**：旗名定 `RELEASE_ENABLE_VISUAL_ELEMENTS`（对应 wt482 的主题名；若 wt482 已先在 settings.py 落了无前缀 `ENABLE_VISUAL_ELEMENTS`，则后合并方把它**迁名**进 `RELEASE_*` 段并同步消费点——先到先得，后来者 rebase，禁止两处各一旗）。挂法：`visual_elements.py` router 级 dependency，默认 False（V3-FIX-182 的 0 入边深链面 + 后端全开双面一次关死）。
- **客户端安全性已实证**（本方案补 V3-FIX-182 未盘的执行依赖，→ V3-FIX-190）：两处核心流程调用均有 try/catch 降级（F5），prestige 色 null 回退 `DS.brandPrimary`（F5）；即旗 off 后核心任务/正念/我的页**行为无损**，但客户端仍会持续发起注定 403 的解锁请求——卡 C 须同步在移动端用 release flag 短路 `unlockByAchievement` 调用（§2.9 的 flag provider），并把成就「解锁元素」奖励叙事在 flag off 期从展示面裁掉。
- 连带收口按 wt479 §4-1/§5-B 清单执行（prestige 卡 / shop SKIN 商品（随 2.2 同关）/ 成就解锁元素 / home 三层 layer 随批处置），不在本卡重开盘。

### 2.6 `community.py` `/feed` 挂 `ENABLE_PUBLIC_COMMUNITY` — **改造（scope 级粒度 + 写侧补齐）**

- 冲突（本方案扩充 wt479 C1 的同型问题）：主线 `/feed` 不是纯陌生人 feed——默认 scope=公共发现，但 `squad/goal_mates/following` 是 S-03/D18 认可的关系面（F3）。端点级旗会把关系面一起杀掉，把 D18「社群聚焦小队/伙伴」误伤成「社群没有动态」。
- **主线形制**：旗挂**默认公共分支**——`get_feed` 内 `scope is None` 分支（`community.py:410-414` 的 public 发现路径）改判据：`not settings.RELEASE_ENABLE_PUBLIC_COMMUNITY` 时 403 `FEATURE_DISABLED`（或 400 提示带 scope，取 403 与其他旗一致）；scope 三分支不挂。装饰器级 dependency 粒度不够（区分不了 scope），须在分支内判。
- **写侧补齐（T36 的真缺口，→ V3-FIX-192）**：`POST /posts` visibility 硬编码 `"public"`（F4）——只闸读不闸写 = 用户能发帖但公开流不可见，内容静默堆积。同旗补：flag off 时 `create_post` 403（或强制 visibility=friends，二选一**需产品拍板**，本方案默认建议 403 与读侧对称、最少惊讶）。
- 移动端 tab 隐藏方向（T36 意图）与 D18 一致，见 §2.10。

### 2.7 `router.py` include 后按 path 反查 `_route.dependencies.insert(0, ...)` — **否决**

- wt479 C4-①已点：与 community.py 装饰器**同一检查装两遍**、include 后反查 route 对象手法脆弱。§2.6 的主线形制（分支内判据）使该 hack 完全无必要。相关 import/依赖一并不移植。

### 2.8 `router.py` 新增 `GET /release-flags` 端点 + api_root prefixes 补行 — **改造（端点保留，契约与暴露面修正）**

- 端点方向正确（解 C2 脑裂的移动端读取面），三处修正：
  1. **单一响应形**：T36 返回 `{**flags, "flags": {小写: v}}` 双形冗余。契约定为单一形：`{"shop": bool, "photon_transfer": bool, "public_leaderboards": bool, "public_community": bool, "visual_elements": bool}`（小写 snake_case，去 `RELEASE_ENABLE_` 前缀；键集=移动端 provider 解码面，写进 docs/contracts 快照）。
  2. **网关注册**：主线移动端不经引擎直连（F8）——`proxy_routes.go` Missing Proxy Routes 列表加 `{"/release-flags", "release-flags"}`（带 authMiddleware）。wt479 C4-③ 的「无认证公开配置布尔」随之消解：引擎直连面仅 dev/test 用，生产面经网关认证。此步**不做则整个移动端契约不可达**，是卡 A 验收项不是可选项。
  3. api_root 的 prefixes 列表补 `"/release-flags"`（T36 此行采纳）。
  4. 命名防混淆注记：网关已有 `/api/v1/release_approvals`（admin 审批面）——与 `/release-flags` 无关，proxy 注释里点一句防后人接错。

### 2.9 `mobile/lib/app/routes.dart` 静态重定向块 — **改造（provider 化 + 面裁剪；原样移植有守卫红灯）**

- **否掉原形**的两个理由：①C2 脑裂——静态字面量与后端旗零关系，后端开旗移动端照藏；②F9——`startsWith('/leaderboard')` 字面量**打红 COMM-LB 守卫**（routes.dart 内无 ignore 注即失败），且把 self-anchor 重定向回 home，一石二鸟全打错。
- **主线形制**：
  1. 新增 `releaseFlagsProvider`（FutureProvider，认证成功后 `GET /api/v1/release-flags`；失败/超时 = 全 false **fail-closed**——藏面是安全方向，这与 T36 默认 False 同向）；routes.dart redirect 闭包 `ref.read` 该 provider（GoRouter redirect 内读 provider 是既有形制，authState 同款）。
  2. 重定向面**只保留**：`/shop`、`/shop/*`、`/visual-elements`、`/visual-elements/*` → `/home`。
  3. **显式排除**（写进代码注释 + 本方案背书）：`/leaderboard*`（self-anchor + 守卫）、`/photon/*`（redeem-pro/history 是活面；`/photon/transfer` 路由已撤，深链落 errorBuilder 兜底，无需重定向）。
- 字符串层面规避守卫：redirect 判据写 `/shop`、`/visual-elements` 字面量即可，不出现 `leaderboard` token。

### 2.10 `community_main_screen.dart` flag 化 Feed tab — **改造（按主线 S-03 布局重写 + 生命周期修正）**

- T36 的实现基于 cosmos 旧布局 `[Partners, Feed, Groups]`（Feed 居中、Partners 默认）；主线是 S-03 `[Groups, Partners, Feed]`（Feed 尾位降级，F10），**不能移植 diff 本体**，移植意图：flag off → 不渲染 Feed tab。
- 主线形制：flag false → `TabController(length: 2)`、tabLabels/children 去 `communityTabFeed`/`FeedTabContent`、FAB 判据 `_currentIndex == 2` 改为按「是否含 Feed tab」计算（防 S-03 desync 前科复发：children、标签表、FAB 判据三处同源一个 `hasFeedTab` 派生值，注释更新 S-03 对位锁说明）。
- **生命周期修正**（wt479 C4-②）：cosmos 版在 `build()` 里 dispose+重建 TabController。主线改：tab 数在首帧后不变的场景下，用 `ref.listen(releaseFlagsProvider)` 于 `initState` 后触发一次重建（或把 controller 建立挪 `didChangeDependencies`），禁止 build 期改生命周期状态。
- 产品开放项（不阻卡）：D18 长期方向是关系面动态（squad 内 check-in/成果流已有 D-COMM-3 面），Feed tab 是「全隐」还是「默认选中关系 scope filter」由产品拍板；本方案默认全隐（与 T36、D18「无公共广场」一致），关系 scope 的 API 面保留不关（后端 §2.6 只关公共分支），未来翻旗或重挂 UI 均可。

### 2.11 五文件 black 风格重排（多行→单行 churn）— **否决**

- 与主题无关的格式 diff 是 review 毒药（F11）；主线 black(120) 形制下这些重排大多**不合规**（cosmos 是另一套 line-length）。移植时只取 flag 相关行，格式 churn 一概不带。

### 2.12 `git_ledger.py` remote 名解析补丁 — **否决（拆出本卡）**

- wt479 C4-④：与 T36 主题无关。属 fleet 工具修复，组员可在 Sparkle-project 侧开独立微卡提交（主线 `git_ledger.py` 同病灶需先核）。

---

## 3. 统一形制：单一权威 + 移动端契约（总结）

```
settings.py Settings（唯一 BaseSettings，唯一 env 加载）
  └─ RELEASE_ENABLE_SHOP / RELEASE_ENABLE_PHOTON_TRANSFER /
     RELEASE_ENABLE_PUBLIC_LEADERBOARDS / RELEASE_ENABLE_PUBLIC_COMMUNITY /
     RELEASE_ENABLE_VISUAL_ELEMENTS        （默认全 False）

release_flags.py（薄视图，无第二 BaseSettings）
  ├─ release_flags() -> dict[str, bool]     # 读 get_settings()
  ├─ require_release_flag(name) -> Depends  # 403 FEATURE_DISABLED（T36 语义保留）
  └─ release_flags_response()               # /release-flags 单一响应形

GET /api/v1/release-flags ──网关显式组注册（auth）──> 移动端 releaseFlagsProvider
  （启动认证后拉取一次；失败 fail-closed=全 false；GoRouter redirect / tab 渲染 / 解锁短路三消费点）
```

与主线 `ENABLE_*` 内部旋钮的关系：**不共用命名空间、不共用判据**——`ENABLE_*` 是引擎内部行为旋钮（memory/context/graphrag），`RELEASE_ENABLE_*` 是用户可见功能面的发布域闸，分节注释 + 前缀双重区隔；但**共用同一 Settings 权威与 env 管道**，杜绝第二实例。移动端一律经 `/release-flags` 读，**禁止**在 Dart 侧再硬编码一份默认值表（provider 的 fail-closed 默认是网络失败语义，不是第二权威）。

---

## 4. 落地顺序（4 张执行卡，建议派卡顺序 = 编号序）

### 卡 A（先行）`T-release-flag-authority`：后端旗权威 + 契约端点（零行为变化）✅ 已执行（wt485）
内容：settings.py `RELEASE_*` 分节（默认 False）；release_flags.py 薄视图 + 工厂；`GET /release-flags`（单一形）；api_root 补行；网关 proxy 注册；移植改造 T36 单元测试（§2.1）。
- 验证点：新测试绿（默认值/403 工厂/端点形/网关路由存在）；`make sync-db` 无涉；OpenAPI 契约快照重刷（新端点入快照）；`go test ./...`（网关）；ruff/black/mypy 棘轮零漂移。
- 回滚面：revert 整卡 = 零产品行为变化（旗未挂任何路由）。风险最低，先行无争议。
- ✅ **执行注记（wt485，分支 `wt485-flagauth`，基 04b62940）**：内容全项落地。测试红→绿（先红=模块缺失；终绿 15/15，`backend/tests/unit/test_release_flag_authority.py`，含单一权威 AST 守卫与「卡 A 红线：api_router 无任何路由消费 release-flag 依赖」扫描守卫）。OpenAPI 快照重冻结增量 +26/−0（仅 `/api/v1/release-flags` path 条目，既有漂移未碰；干净 base 重生成零 diff 实证快照冻结态稳定）；`check_openapi_contract.py` exit 0。mypy 恰 1095=基线零漂移；ruff 触达文件全绿；black 触达行合规（base 与 work hunk 数相等 router 3=3 / settings 19=19，纯位移零新增，存量漂移未碰）；网关 `go build`+`go test ./...` 12 包全 ok、gofmt 净。台账新发现：无（未登记新 V3-FIX 号）。

### 卡 B `T-release-gate-public-surfaces`：leaderboards 双 router + community 公共闸 + transfer 窄旗
内容：§2.4 双 router（self-anchor 豁免）+ §2.6 scope 级公共闸（读分支 + POST /posts 写侧，写侧处置若产品未拍板先按 403 落并在 PR 描述标「可改 friends 语义」）+ §2.3 transfer 窄旗。
- 验证点：§2.4 的三条防回归测试；旗 off 时关系 scope（squad/goal_mates/following）200 实证（防误伤 F3）；`check_rule_comm_lb_leaderboard_unrouted.py` 绿；受影响模块 pytest（leaderboards/community/photon）。
- 回滚面：三文件独立小 revert；生产热回滚第一层=env 翻对应旗为 True（不回码）。

### 卡 C `T-release-gate-labs-shop`（合流 wt482 + V3-FIX-05）：visual_elements 闸 + shop/inventory 闸 + 入口移除 + 解锁短路
内容：§2.5 visual_elements router 旗（与 wt482 协调：若其已落旗则本卡只做迁名归权威 + 消费点同步）；§2.2 shop/inventory 旗；`streak_details_screen.dart:427` 入口移除（V3-FIX-05 销账条件）；移动端 `unlockByAchievement` 经 flag 短路（V3-FIX-190 收口）；wt479 §4-1 连带面按清单收口。
- 验证点：旗 off 时任务完成/正念完成流程无 403 请求发出（provider 短路生效）、profile 页 prestige 色回退默认、shop 深链落 /home；V3-FIX-05/182 状态联动更新；flutter test 受影响模块。
- 回滚面：后端两 router 旗独立 revert；入口移除单文件 revert；翻旗热修可先恢复 API 可达。
- 协作注记：**wt482 先到先得**——wt482 若已在途落了旗，本卡以 wt482 为基 rebase，禁止两卡并行各写一版闸。

### 卡 D（最后）`T-release-flag-mobile`：移动端 flag provider + 重定向 + community tab
内容：§2.9 releaseFlagsProvider + routes.dart 重定向（面裁剪版）；§2.10 Feed tab flag 化（S-03 布局、三处同源、生命周期修正）；l10n 无新增键（复用 communityTabFeed 既有键，隐藏即可）。
- 验证点：flag off：/shop、/visual-elements 深链落 /home；`/leaderboards/self-anchor` 直达正常；community 两 tab 模式下三处（children/标签/FAB）对位正确；flag on：全部恢复；断网启动 fail-closed 行为实证；`flutter test` + COMM-LB 守卫绿。
- 回滚面：纯 mobile 面，单卡 revert；不影响后端。

**顺序依赖**：A→B/C 可并行（B/C 均只依赖 A 的权威与工厂）；D 依赖 A（端点契约）+ B/C（旗已挂才有意义）。B 与 C 互相独立。

---

## 5. 新发现缺陷登记（V3-FIX-190 起；186-189 已占，grep 确认 190+ 空闲）

| ID | 严重度 | 内容 | 证据 | 处方 |
|---|---|---|---|---|
| **V3-FIX-190** | P2 | 核心 学习/专注流程每次成就解锁都调 `/visual-elements/unlock-by-achievement`（`task_execution_screen.dart:388`、`mindfulness_provider.dart:367`）——V3-FIX-182 闸若按 router 级 403 落地，旗 off 期每次任务/正念完成都发出注定 403 的请求（客户端 try/catch 吞掉、行为无损，但「闸了还在调」+ 无效网络面 + 403 噪声进监控），是 wt482 落地必处理的隐藏依赖 | 本卡 §2.5/F5 实读 | 随卡 C：移动端经 releaseFlagsProvider 短路解锁调用 + flag off 期裁剪「解锁元素」奖励叙事展示 |
| **V3-FIX-191** | P2 | T36 移动端重定向块移植陷阱：`startsWith('/leaderboard')` 字面量在 routes.dart 会被 COMM-LB 守卫 `LEADERBOARD_UI_RE` 打红（无 ignore 注），且把 `/leaderboards/self-anchor`（D-COMM-1 唯一产品面）重定向回 home——机械移植 cosmos diff 即双踩 | 本卡 F9；T36 diff routes.dart 块 | 随卡 D：重定向面裁剪为 /shop*、/visual-elements*，显式排除 /leaderboard*、/photon/*（注释+测试双固化） |
| **V3-FIX-192** | P3 | `POST /community/posts` visibility 硬编码 `"public"`（`community.py:476`）且无参数——T36 旗只闸读不闸写的不对称面；「发帖即公开、用户无选择权」本身是产品语义债 | 本卡 F4 | 随卡 B：公共旗 off 时写侧 403（或强制 friends，产品拍板二选一） |

已同步追加至 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（同一 docs commit）。

---

## 6. 给组员的协作建议（cosmos 树 vs 切主线）

**切主线。** 理由：

1. cosmos 基线是 v3 修复前旧形态（无共同祖先；`user_service.py:208` flame 派生等病灶在主线已修——wt479 §0），继续在 cosmos 写产品码会持续偏离 D-COMM-1/2、S-03、V3-FIX-05/182 这些他视野外的裁决面；本次 12 单元里 0 个可原样移植就是偏离量的直接度量。
2. 他的机制贡献（release flag + 250 行测试）**已被本方案完整吸收**（卡 A），不是白做；mobile/community 两块因主线布局/裁决面不同须重写，继续在 cosmos 打磨这两块是沉没成本。
3. 具体动作：①读本 PLAN + wt479 REPORT §6；②按派卡流程认领卡 A 或卡 B（在 Sparkle-project worktree、一任务一分支 `agent/<node>/<task>/<fence>`）；③cosmos 的 T36 WIP **冻结不再续写**（含 git_ledger 补丁，另拆微卡）；④格式 churn 习惯改掉——主线 black(120)/ruff，churn 进不了 review。

---

## 7. 最关键风险（重申）

**双权威脑裂 + 裁决面误杀**。本项目刚用 wt480 把 kill-switch 家族收敛到「tri-state 唯一判据」（V3-FIX-21 FIXED，同族扫出 186-189 四件 legacy 直读），T36 原形（独立 BaseSettings + 移动端硬编码 + 双装依赖）是同族病的 release-scope 变体；而 router 级旗的机械移植会在默认 False 下静默 403 掉 self-anchor（D-COMM-1）与光子兑 Pro（D-COMM-2）两张**已裁决上线**的产品面——裁决面回归比功能缺失更难审出。本方案的全部改造点都围绕这两条：单一权威、粒度到不误伤裁决面、移动端只读不藏私。

## 8. 方法与局限

- 全部结论来自两仓工作区静态读取 + 引用图 grep + 守卫/裁决文档对读；未执行 pytest/flutter/守卫套件（本卡为分析产出、零代码改动，符合「纯文档变更不重跑全产品测试」约束）；执行卡的验证点已写入 §4 由执行卡兑现。
- cosmos T36 测试通过性未证（wt479 已声明同样局限）；本方案对该测试只做「改造吸收」规划，通过性由卡 A 落地时兑现。
- 写侧 POST /posts 的 403 vs 强制 friends、Feed tab 全隐 vs 默认关系 scope，两处标了产品开放项，不阻塞工程卡，落地时按默认执行并在 PR 标注可翻转。
