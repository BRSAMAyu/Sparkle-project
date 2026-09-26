# wt479 · 组员 7 项产品改动主张核验报告

- 工号：wt479（产品核验，只读核验 + 本 worktree 报告，零产品代码改动）
- 基准 SHA：主线 `Sparkle-project` main @ `0184b698`（worktree `wt479-verify`）；cosmos 仓 `agent/node-b/T36/1` @ `aa026357` + **未提交 WIP diff**
- 日期：2026-09-26
- 结论图例：**真实**（问题存在且未修）/ **已做完**（主线已裁决/已修，主张过期）/ **部分真实** / **决策项**（不核真伪）
- 发现的真实缺陷登记：**V3-FIX-181 / 182 / 183**（见 §7，已同步 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`）

---

## 0. 两仓关系认定（核验 T36 diff 的前提）

| 项 | 认定 | 证据 |
|---|---|---|
| 是否同一产品 | **是**，同一产品的两条工作线 | cosmos `git remote -v` 含 `sparkle → BRSAMAyu/Sparkle-project.git`（只读指回主线）；文件族/路径 1:1 对应 |
| git 历史关系 | **无共同祖先**（clean-slate reset）：`git merge-base aa02635 main` 为空；cosmos 对 `sparkle/main` 的 fetch 视图停在旧基线（cosmos 领先 76 / 落后 11，均为陈旧计数） | 两仓各自 `rev-list` |
| cosmos 代码形态 | **v3 修复前的旧形态**：`backend/app/services/user_service.py:208` 仍是 `is_pro=user.flame_level >= 3`（主线 V3-FIX-02 已拆的同一行号同源代码）；leaderboards/shop/photons 全量活跃、无 self-anchor | `git -C cosmos grep "flame_level >= 3"` 命中 user_service.py:208,356 |
| T36 diff 基准 | cosmos `agent/node-b/T36/1`（tip=aa02635）上的**未提交工作区改动**：10 文件 +160/−191，另有未跟踪 `release_flags.py`、250 行测试、`.agents/`、evidence 等 | `git -C cosmos diff --stat` |

**推论（影响多个主张的判定）**：组员的产品感知来自 cosmos 旧代码面。他在 cosmos 里看到的"付费等级混游戏等级""排行榜还在""统计是假的"，在主线分别处于：**已修（V3-FIX-02）/ 已裁决已执行（D-COMM-1/D-COMM-4）/ 已修（D-04，台账陈旧未销）** 三种状态。T36 diff 本身是对旧基线的合理防御，但**多处不能按原样移植主线**（详见 §6）。

---

## 1. 逐主张 verdict

### ① 不做公网部署 — **决策项**（按派卡说明不核）。主线 `v3-output/D-DEPLOY*` 已有部署裁决记录，无代码面可证伪。

### ② 没配 API Key 的功能先藏起来 — **部分真实（机制缺口存在，但归因错位）**

**真的一面：主线确实没有 T36 式"发布域 flag"机制。**
- 主线后端 `backend/app/config/settings.py` 的 40+ 个 `ENABLE_*` 全是**内部功能开关**（memory/context/experiments 等，settings.py:651-927），没有面向"用户可见功能面"的 release flag。
- 主线移动端 `core/constants/app_constants.dart:31-44` `AppFeatureFlags` 只覆盖 memory panel / stage35 卡片，不含 shop/photons/leaderboard/visual-elements 的藏显。
- 后台无 key 的行为盘点（证据file:line）：

| 依赖面 | 缺 key/依赖时行为 | 判定 |
|---|---|---|
| embedding（DASHSCOPE/SILICONFLOW） | **fail-closed**：`EmbeddingNotConfiguredError`，调用方降级词法检索；E-05 已移除零向量静默回退（`backend/app/services/embedding_service.py:10,24,232,312`） | 设计内降级，合格 |
| rerank | 供应商无 key 即 skip，全失败时**静默回退原始序 top_k**（`backend/app/services/rerank_service.py:108-130`） | 降级但无用户面提示（轻微） |
| BERT 意图分类 | 模型缺失→keyword-only 兜底（`backend/app/orchestration/bert_intent_classifier.py:337-339,362`） | 设计内 |
| STT/TTS | 供应商链全未配置→报错；且 **`/stt` `/tts` 在移动端 0 消费**（路由对照 §4-9） | 无用户面，不裸奔 |
| GraphRAG/AGE | 服务不可用返 501（`backend/app/api/v1/graph_monitor.py:78-80`） | 设计内 |
| LLM 主链 | 生产模式强制 ≥1 个 key（`settings.py:1421-1430` validator），dev 无 key=聊天报错（无藏入口机制，靠部署校验拦截） | 部署闸门兜底 |
| **visual-elements LABS 面** | **无任何 flag/守卫**：路由挂载可深链直达 + 后端路由全开（→ §4-1，登记 V3-FIX-182） | **真裸奔面** |

**错位的一面**：T36 四个 flag 盖的 shop/photons/leaderboards **不依赖任何 API key**——它们是"未上线/未验证"问题，不是"没配 key"问题。主张口径应改为「发布域隔离（release scope）」，与"API key"解耦。另注意主线已有同类裁决在途：**V3-FIX-05（OPEN）**= `/shop` 空目录暴露（shop_items 0 行，唯一入口 `streak_details_screen.dart:427`），与 T36 的动机重合，落地时应合并处置而非两套机制。

### ③ 排行榜直接删掉 — **已做完（主线裁决+执行双完成，主张过期）**

- 裁决链：D17（游戏化降权）→ `v3-output/D-COMMUNITY/DESIGN.md` §2.2/§3.2（全站综合榜=「大池+异质水平+静态综合分」反面模式全中，**删面保枚举**）→ D-COMM-1 落地卡 → D-COMM-4 收官。
- 执行证据（主线 @0184b698）：
  - 移动端全站榜三件套 1,143 行**整链已删**（台账 #3 销账记录）；现存 `mobile/lib/features/leaderboard/` 仅 472 行 self-anchor 替代链（routes 25 + repo 52 + model 84 + provider 20 + screen 291），唯一路由 `/leaderboards/self-anchor`（`leaderboard_routes.dart:16`，挂载 `routes.dart:409-411` 带 `rule-comm-lb: ignore` 注）。
  - 守卫固化：`scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py`（mobile 无全站榜挂载 + 网关 leaderboards 组 wildcard-only 两条不变量）。
  - 后端唯一产品面 `GET /leaderboards/self-anchor`（`backend/app/api/v1/leaderboards.py:276-296`）。
- 残余面（如实披露，非回归）：engine 侧 global/subject/streak 榜端点仍在路由表（`router.py:280`）且经网关 wildcard 代理可达——这是守卫 docstring 明文的**已知取舍**（去 wildcard 会断 self-anchor；显式行被 COMM-LB 禁止），有认证门槛、无 UI 入口。T36 的 router 级 flag 是关闭它的更优解，但**必须给 self-anchor 开洞**（§6-C1）。

### ④ 统计数据先下线 — **已修（主张基于陈旧台账；陈旧本身登记为缺陷 V3-FIX-181）**

- 组员引用的"successRate 0.95 硬编码 + mock 进 Isar 长期供 UI"是**真实历史**（台账 P1 #1/#2、V3-FIX-03 登记），但主线已由 **`5ed3d20d feat(D-04): real analytics wiring + mock cache pollution purge (dual-reviewed)`** 修复：
  - 三统计仓库改为真实端点且**无客户端回退**：`agent_statistics_provider.dart`（`GET /agent-stats/user/overview`）、`capsule_statistics_provider.dart`（`GET /capsules/stats`）、`focus_statistics_provider.dart`（`/focus/stats*` 族），注释均明示 D-04「transport failures propagate」；
  - legacy mock 暖缓存**一次性 purge**（`hybrid_statistics_repository.dart:109,135-139,367`）。
  - `v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-03 状态 = `FIXED@D-04`。
- 残余小尾巴（不构成"下线"理由）：`watchStatistics` 仍是自述占位实现（`hybrid_statistics_repository.dart:292-304`，单次 yield 包装）；`statistics_card.dart:119` 周趋势为**诚实空态**（明文"禁止回落到伪造数据"）。
- **缺陷在台账侧**：`docs/engineering/KNOWN_CODE_DEBT_LEDGER.md` P1 #1/#2 仍以旧 file:line 挂"未修"，与 V3-FIX-03 FIXED 状态失同步——正是组员误判 ④ 的直接来源（→ V3-FIX-181）。

### ⑤ 付费等级与游戏等级混在一块要拆 — **已做完（数据/网关/引擎三层均已拆；UI 层核验无混排残留）**

- 数据层：`backend/app/models/user.py:74`（flame_level，展示层）与 `:78-85`（`entitlement` 唯一权益判据 + `entitlement_expires_at`，列注释明文「禁止用 flame_level 派生权益」）。
- 引擎：`backend/app/services/user_service.py`（V3-FIX-02 修复点）`is_pro=entitlement_effective_grants_pro(entitlement, expires_at)`，注释引用 D17/O-04/D-REDEEM。
- 网关同语义：`backend/gateway/internal/service/user_context.go:68-86`（`IsProEntitlementEffective`，双侧同步契约）。
- 台账 B-06 补记的两处旧派生（user_service.py:208 / user_context.go:129）均已被上述修复覆盖。
- **UI 层逐面清单（组员没查的部分，本次全查）**：

| 展示面 | 位置 | 内容 | 是否混排 |
|---|---|---|---|
| 首页迷你徽章 | `compact_status_bar.dart:125-126` | `L1/Lv.1`（flameLevel） | 否，纯游戏等级 |
| 专注卡 | `focus_card.dart:116` | `Lv.$flameLevel` | 否 |
| 我的页头部 | `profile_screen.dart:568-571` | `levelPrefix + flameLevel` 药丸 | 否 |
| 我的页入口 | `profile_screen.dart:689-697` | 光子兑 Pro（D-COMM-2 有界出口），独立 tile 独立文案 | 否（相邻但分区，语义分离） |
| 商城 | `shop_screen.dart:52-64` | 兑 Pro tooltip 入口（次级位） | 否 |
| 兑换屏 | `photon_redeem_pro_screen.dart:15,62` | 读 `entitlementExpiresAt` 到期语义 | 否 |
| 社群搜索/好友资料 | `user_search_screen.dart:222`、`friend_profile_screen.dart:163` | `Lv.N` / `Flame Lv.N` | 否 |

**结论**：⑤ 在主线是**已完成态**（V3-FIX-02 FIXED + D-MONETIZE 复核「能力门控唯一判据=entitlement ✅」）；组员感知来自 cosmos 旧代码（`user_service.py:208` 同款病灶在那里还在）。

### ⑥ 半成品模块+文档不清→审查后删 — **真实（方向成立，且本次盘出 3 个台账外新面）**，逐项清单见 §4。

### ⑦ Aurora 黑话多→重设计；特效先删 — **部分真实（黑话重灾区不在 Aurora；特效删除需按 §5-B 定义执行防误伤）**，详见 §5。

---

## 4. 半成品/孤儿面清单（⑥ 深核验产出，按建议处置优先级排序）

方法：a) mobile 43 个 feature 目录 × 后端 114 个 API 文件对照 + 全路由表入边扫描（复核 NAV-IA 测绘：注册路由 139 条）；b) 台账/NAV-IA/D-COMMUNITY/D-MONETIZE/U-07 裁决面回访；c) `TODO/占位/mock` 密度扫描 + 逐条人工证伪（demo 模式 `main.dart:127-129` 统一闸门、`USE_MOCK` 构建开关 `cognitive_repository.dart:88-92`、诚实空态 `statistics_card.dart:119` 均**不是**半成品，已排除）。

| # | 面 | 证据（file:line / 行数） | 状态 | 爆炸半径（依赖方） | 建议 |
|---|---|---|---|---|---|
| 1 | **visual-elements LABS 孤儿链** | 路由挂载 `routes.dart:434`；入口已摘（U-07，`profile_screen.dart:709-710` 注释）⇒ **0 应用内入边、可深链直达**；feature 8,197 行；后端 `api/v1/visual_elements.py` 路由全开、无 flag | **台账外新发现**（登记 V3-FIX-182） | ③ prestige 卡读 equipped 色（`profile_screen.dart:44,146-148`）、shop SKIN 商品、成就解锁元素（后端 unlock_by_achievement）、`ApiEndpoints.visualElements`（api_endpoints.dart:713） | **藏或删**：与 T36 旗子天然对齐（T36 已把 `/visual-elements` 列入移动端重定向）。若删 prestige 卡的 equipped 色回退 `DS.brandPrimary` 即可 |
| 2 | **transparency_settings_screen 703 行孤儿屏** | `settings/presentation/screens/transparency_settings_screen.dart`（703 行 + .g.dart）：**0 路由注册、0 push、0 实例化**；`chat_screen.dart:84` import 后**未使用任何符号**（死 import）；NAV-IA A-1 辩题3 当时裁「删按钮」，此后屏体反而长出 | **台账外新发现**（登记 V3-FIX-183） | 悬浮胶囊/设置开关（`chat_settings_screen.dart:195-196`）已独立接线，删屏不伤 | 按 NAV-IA 精神**删屏**或补产品裁决后再挂路由 |
| 3 | accountability_hub_screen 762 行 0 挂载 | `community/presentation/pages/accountability_hub_screen.dart`（NAV-IA 已列） | 已登记未处置 | 0 入边 | 删（git 留史） |
| 4 | photon_transfer 幽灵屏 | `photon_transfer_screen.dart` 476 行，路由已撤（台账 #11，P2P 转账反刷裁决） | 已登记、裁决「保留未删」 | 0 push 引用；`pt*` l10n 键 | **维持不动**（重做需先过反刷审计） |
| 5 | notification_analytics 孤儿面 | 屏 745 + provider 113 行（台账 #12，NAV-IA P-3 摘除挂载） | 已登记、裁决「保留文件」 | barrel 导出未动 | 挂 admin-operations 或删 |
| 6 | `/community/feed` legacy 别名路由 | `community_routes.dart:33,62-76`（渲染同一 CommunityScreen；NAV-IA 列为 0 入边孤儿路由） | 已列 | 深 D-COMMUNITY R3「无公共广场」精神下应收敛 | 低危：摘挂载 |
| 7 | `watchStatistics` 占位实现 | `hybrid_statistics_repository.dart:292-304` | D-04 残余 | 0 生产消费（仅 domain 接口） | follow-up 小卡 |
| 8 | 后端无移动端消费面的路由 | `/stt` `/tts` `/analytics` `/experiments` `/ingestion` `/monitor/graph` `/admin` `/safe-experiments`（路由对照脚本输出） | API-first/运营面，非半成品 | 移动端 0 引用 | 不动作；在 docs/contracts 说明受众即可 |
| 9 | 台账陈旧（文档不清的真样本） | `KNOWN_CODE_DEBT_LEDGER.md` P1 #1/#2/#3 vs V3-FIX-03 FIXED@D-04 / D-COMM-4 | **登记 V3-FIX-181** | 误导产品判断（本次 ③④ 误判直接来源） | 销账/交叉标注 |

---

## 5. Aurora 黑话盘点 + 特效删除面（⑦ 深核验产出）

### 5-A 黑话表

盘点面：mobile 22 个非生成 aurora dart 文件（core 3 + features 19；派卡写 23，差的 1 个为生成文件口径差）+ l10n `aurora*` 键 **167 个**（app_zh.arb）。

| 用户可见术语 | 代表键/位置 | 新手首见可懂？ | 评估 |
|---|---|---|---|
| "Aurora"（助手名直接前置） | `auroraStatusReady="Aurora 已校准"`、`auroraActionViewDetails="查看 Aurora 详情"`、`auroraNeedsAttention` 族（arb:9042-9081） | **否**——onboarding/chat 引导文案 grep 不到任何"Aurora 是谁"的介绍 | **主要黑话源**：不是词深，是**名字未引入**。修法是加 1 次命名介绍（首次对话/启动卡），不是重写 167 键 |
| 校准/重校准/初始化中 | `auroraStatusRecalibrating/Partial/Missing` | 中（"校准"半透明） | 可保留，配一句副标题即可 |
| 已连通/补全中/未形成（facet 态） | `auroraFacetReady/Partial/Missing`（arb:9051-9054） | 中偏低（"facet"概念未解释） | 建议换「我知道你 / 还在了解你」类口语 |
| 把握 {percent}% / 看起来对 / 不太对 | `auroraConfidenceLabel`、`auroraActionConfirm/Disagree` | **好**（已是刻意去黑话化的白话） | 保留 |
| 冷却中 Xs 后恢复 | `auroraCooldownSec/Min/Hr` | 中（游戏化借词） | 可保留 |
| ——以下**非 Aurora 域**的真黑话—— ||||
| 暗物质（galaxy 星区名） | `galaxySectorDarkMatter`（arb:14108） | 低 | galaxy 隐喻面，随 §5-B-1 一并评估 |
| 静星轨迹 / 征服引力（视觉主题名+描述） | `visualStarTrack`(10680)、`visualGravity="征服引力"`、`visualGalaxyConquerorDesc`（10694-10699） | 低（且属 LABS 面） | 随 visual-elements 删除自然消失 |
| 中心引力/连线牵引力（仿真控制） | `galaxySimulationCenterGravity/Gravity`、`galaxySimCenterGravity/LinkTension`（3991-3992, 11960-11962） | 低（图形仿真控制项） | galaxy 面单独小卡，不动核心 |

**⑦ 前半 verdict**：「Aurora 黑话多」**部分真实**——重灾区是 galaxy/visual_elements 的天文隐喻与"Aurora 名字未引入"，Aurora 交互文案本体（把握%/看起来对/需要你确认）已相当白话；"重设计"应聚焦 1 次命名引入 + facet 状态词白话化，**不是**推倒 167 键。

### 5-B 「删特效」可执行定义（粒度到文件；防误伤核心状态展示）

| 圈层 | 文件（行数） | 消费方 | 判定 |
|---|---|---|---|
| **B-1 可删（LABS 视觉链）** | `features/visual_elements/`（8,197 行）+ `routes.dart:434` 挂载 + `api_endpoints.dart:713` + 后端 `visual_elements.py`+service+router include | 见 §4-1 爆炸半径（prestige 卡配色回退默认色、shop SKIN、成就解锁元素需同步收口） | **删/藏**（对齐 V3-FIX-182 与 T36） |
| **B-1' 随葬** | home 三层 `background_layer/particle_layer/effect_layer.dart`（480+487 行等） | 生产中**仅** `visual_element_preview_dialog.dart:1005-1014,1289-1302` 引用（weather_guide 用 WeatherLayer 不受影响） | 删 visual_elements 后即成死代码，同批删 |
| **B-1'' 收编** | `core/design/widgets/rarity_visual_wrapper.dart`（728 行） | 仅 `achievement_card.dart`、`visual_element_card.dart` | 后者随 B-1 删；前者降级为 `rarity_badge` 纯色徽章即可，无需 728 行动效壳 |
| **B-2 必须保留（核心状态/奖励时刻）** | `sparkle_confetti.dart`（270 行）→ 8 个消费方（`success_animation`、`task_completion_celebration`、`goal_step_completion`、`sprint_completion`、`milestone_celebration`、`achievement_unlock_dialog`、post_exam、theater） | 奖励反馈是 D17 保留的「安静反馈」主通道 | **不删** |
| **B-2' 必须保留（设计系统基座）** | `core/design/tokens_v2/state_tokens.dart`（103 行） | `design_system.dart`、`sparkle_theme_extension.dart`、`surface_state.dart` 等核心 | **严禁删**（这是状态色令牌，不是特效） |
| **B-3 中性基建** | `particle_pool.dart`(306)、`global_particle_counter.dart`(49) | B-1/B-1' 的底层 | 随上层去留；单独保留无意义 |

**⑦ 后半 verdict**：「特效先删」**方向可执行但必须按圈层切**——删 B-1/B-1'/B-1''（≈9.6k 行 LABS 视觉链）零核心伤害；把 B-2/B-2' 一并划进"特效"会打断任务完成庆祝与设计令牌体系（误伤核心状态展示）。

---

## 6. T36 WIP diff 对照结论

### 6-A 与主张的对应关系

| 主张 | T36 diff 承载 | 说明 |
|---|---|---|
| ② | `release_flags.py`（4 flag 默认 False）+ 6 路由挂 403 依赖 + `/release-flags` 只读端点 + 移动端重定向/隐藏 | 机制本体在 cosmos 落地且自带 250 行测试（默认值/403/端点/feed 隐藏），**本核验未在 cosmos 环境执行测试，通过性未证** |
| ③ | leaderboards 整 router 挂 `ENABLE_PUBLIC_LEADERBOARDS` | cosmos 无 self-anchor，故其"整 router 关"在**cosmos 内自洽** |
| ④ | **无对应改动** | 统计面 T36 零触碰（主张④在主线已是 FIXED 态，无需做） |
| ①⑤⑥⑦ | 无对应改动 | 决策项/已在主线完成/本次报告覆盖 |

### 6-C 冲突与移植风险（组员没想到的）

- **C1（最重要）｜self-anchor 误杀**：主线 self-anchor 唯一路由是 `/leaderboards/self-anchor`（与全站榜**同 router**）。T36 的 router 级 `require_release_flag("ENABLE_PUBLIC_LEADERBOARDS")` 移植主线后，默认 False 会把 D-COMM-1 唯一允许的产品面一并 403。移动端 T36 重定向 `startsWith('/leaderboard')`（cosmos routes.dart 新增块）同样命中 self-anchor 路径。**修法**：flag 挂到全站榜各端点级（或 self-anchor 独立子路由豁免）。
- **C2｜双旗脑裂**：移动端 `publicCommunityFlagProvider` 硬编码 `false`、routes.dart 重定向为**静态字面量**，与后端 `/release-flags` 无读取关系——后端开旗后移动端依旧藏。需定义"编译期默认 + 启动拉取缓存"或明示这是单向安全闸。
- **C3｜产品裁决冲突**：T36 把 `/shop` 重定向回 home + router 403，比主线裁决更激进：D-MONETIZE 维持"商城降级但 streak_details 深埋入口可达"，V3-FIX-05 只裁"空目录暴露→移除该入口"。应将 T36 的 shop 部分与 V3-FIX-05 合并成一个裁决执行，避免两处机制。
- **C4（代码审查注记，非阻塞）**：① `/community/feed` 依赖被装了两遍（`community.py` 装饰器 + `router.py` 对 path=="/feed" 再 `insert(0,...)`，同一检查执行两次，冗余；且 include 后按 path 反查的手法脆弱）；② `community_main_screen.dart` 在 `build()` 内 `dispose()` 旧 TabController 再重建——build 期改生命周期状态有 flakes 风险，应移入 `didChangeDependencies`/listener；③ `/release-flags` 端点无认证，公开返回配置布尔（低危信息暴露，建议挂认证或并入既有 status 面）；④ `git_ledger.py` 的 remote 名解析补丁与 T36 主题无关，宜拆开提交。

---

## 7. 台账登记（本轮新缺陷）

> 编号从 V3-FIX-181 起（177-180 为在途派发卡预留；`grep` 确认 1xx 段现最高在册 = V3-FIX-176）。已同步写入 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`。

- **V3-FIX-181（P2·文档失同步）**：`KNOWN_CODE_DEBT_LEDGER.md` P1 #1/#2/#3 未随 V3-FIX-03 FIXED@D-04（`5ed3d20d`）与 D-COMM-4 销账，陈旧 file:line 直接导致组员产品主张 ③④ 误判。
- **V3-FIX-182（P2·孤儿暴露面）**：visual-elements LABS 链 0 入边可深链直达 + 后端路由无 flag 全开（§4-1/§5-B-1）。
- **V3-FIX-183（P3·孤儿屏+死 import）**：`transparency_settings_screen.dart` 703 行 0 挂载 0 实例化；`chat_screen.dart:84` 未使用 import（§4-2）。

## 8. 方法与局限

- 证据全部来自两仓工作区静态读取 + 引用图 grep；cosmos 侧 T36 测试（250 行）与 Flutter/pytest 套件**未执行**（本卡只读核验、无 cosmos 写权限、环境归组员），其通过性声明不算完成。
- 主线守卫基线未在本 worktree 重跑（无代码变更，符合"纯文档变更不重跑全产品测试"约束）。
- 后端前缀对照用脚本（router prefix × mobile 字面量路径）存在深链模板漏计可能，已对判"无消费"的 8 个前缀逐个抽查确认。
