# MOBILE-GAP-3 收工报告：小队系三件套入口（冲刺小队 + 小队榜/自习室 + 错题分享）

- Worker: MOBILE 纵队第三棒 ｜ worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt167` ｜ 基线 `8daa8508`（含自我锚先例 4d2a385a）
- 交付物: `v3-output/MOBILE-GAP-3/REPORT.md`（本文）+ `changes.patch`（21 文件：9 改 + 12 新；新文件带 `--- /dev/null` 头，已在基线克隆验证 apply 干净）
- 状态: **未 commit / 未 push**（纪律遵守）｜ 零凭据 ｜ 后端契约（wt162/wt165/wt166 已合入面）零改动

---

## ① 屏结构与必达项分配表（上限 3 屏，实际 2 屏 + 详情内 1 段）

| # | 屏 / 段 | 路由 | 必达项（≤2/屏） | 数据面 | 语义槽 |
|---|---|---|---|---|---|
| 1 | **小队列表屏** `squad_list_screen.dart` | `/community/squads` | ① 我的小队列表（`GET /community/squads`；空态诚实：无小队≠报错，EmptyState 引导创建）② 创建/加入入口（AppBar 次级动作：`+` 创建（name+deadline 必填，照后端契约）、`group_add` 凭小队 ID 加入；空态下入口仍可达） | `squadListProvider` + create/join 动作 | 唯一 accent（brandPrimary） |
| 2 | **小队详情屏** `squad_detail_screen.dart` | `/community/squads/:id` | ① **成员完成度榜**：completion 百分比 + 并列名次**如实渲染（1,1,3 不重排不去重）**；`has_ledger_data=false` 显示「无账本数据」而非伪装 0%（D-COMM-3 空数据诚实语义）；`self_view_only`/`board_valid=false`（<3 人）→ 降级提示 + 「查看我的自我锚」按钮切既有 `/leaderboards/self-anchor` 路由，**不渲染残缺榜** ② **在室状态**：心跳端点诚实上报本人 in_room（不在场绝不自动重开，进出以显式按钮为准）→ enter/exit 按钮 + 今日累计分钟 + 全员在场列表（未入场如实列 0，不惩罚缺席；is_stale 仅弱提示不降级） | `squadLeaderboardProvider` / `squadPresenceProvider` / `squadMyRoomStatusProvider` | 榜 = `colors.info` 数据可视化；在室 = `colors.success` 在线语义；时长/完成度数字全部令牌样式 |
| 3 | **错题分享段**（详情屏内第三段，非独立屏） | — | 列表（新→旧）+ 诚实空态（引导去错题本）；白名单投影如实渲染：分享者/题目（可空不渲染该行）/知识点/错因/掌握度快照/附言；**契约无答案字段 → 不渲染任何「答案」类内容**（模型层即不建模 correct_answer/user_answer） | `squadSharedErrorsProvider` | info 语义标题；空态 EmptyState 风格引导 |

**入口**：Sprint 仪表盘 AppBar 次级 ghost 按钮「冲刺小队」（照自我锚 4d2a385a 先例逐字复刻，不占内容主面积；无冲刺时按钮仍在）。**分享动作入口**：错题详情屏 AppBar 可见分享按钮（`error_detail_screen.dart` 小改）→ 选队弹窗 → **只传 error_id**（+用户选定的 squad 路径参数；note 不传）。

三段（详情屏内）各自独立 loading/error 面：单面失败不拖垮整屏，段内重试只 invalidate 该段 provider。

## ② 实现清单（9 改 + 12 新）

| 文件 | 类型 | 说明 |
|---|---|---|
| `mobile/lib/core/network/api_endpoints.dart` | 改（+19 行） | squads 域 10 条端点常量（detail/join/leaderboard/study-room×4/shared-errors），带 D-COMM-3/4/5 注释锚点 |
| `mobile/lib/features/community/community_routes.dart` | 改（+50 行） | `squads` 常量 + `squadDetailPath(id)` 构造器 + 2 条 GoRoute（socialWarm 场景音 + SparkleTransition，照群组域 house style；详情注册在列表精确路径之后） |
| `mobile/lib/features/plan/presentation/screens/sprint_screen.dart` | 改（+10 行） | AppBar 次级「冲刺小队」ghost 入口（自我锚先例模式） |
| `mobile/lib/features/error_book/presentation/screens/error_detail_screen.dart` | 改（+21 行） | AppBar 可见「分享到小队」按钮 + `_shareToSquad` 弹窗调用（只传 error_id） |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` | 改 | `squad*` 57 键 ×2（字母序插入、`@` placeholder 元数据照 leaderboardSelfAnchor 块风格；模板 zh） |
| `mobile/lib/l10n/app_localizations*.dart`（3 个） | 改 | `flutter gen-l10n` 产物（diff 仅含新键） |
| `mobile/lib/features/community/data/models/squad_models.dart` | **新** | `SquadListItem`/`SquadInfo`/`SquadCreateInput`，手写 fromJson（SelfAnchorView 先例风格，不进 build_runner） |
| `mobile/lib/features/community/data/models/squad_board_models.dart` | **新** | `SquadLeaderboardEntry`（rank 并列名次 + percentile + has_ledger_data）`/SquadLeaderboard`（board_valid/self_view_only） |
| `mobile/lib/features/community/data/models/study_room_models.dart` | **新** | `StudyRoomPresenceEntry`/`StudyRoomPresence`/`StudyRoomMyStatus` |
| `mobile/lib/features/community/data/models/shared_error_models.dart` | **新** | `SharedErrorEntry`/`SharedErrorList`/`SharedKnowledgeNode`——**无答案字段可建模**（契约即白名单投影） |
| `mobile/lib/features/community/data/repositories/squad_repository.dart` | **新** | 全小队面只读 + 动作仓库；`unwrapList`/`unwrapMap` house style（兼容包裹/直接两种格式，照 community_repository 惯例）；enter/exit 幂等语义注释；demo 分支同走诚实空态（空列表，不造假队） |
| `mobile/lib/features/community/presentation/providers/squad_provider.dart` | **新** | `autoDispose` 全家桶：列表 + 4 个 `FutureProvider.autoDispose.family<.., String>`（groupId 参数化）；动作走 repository + invalidate，不设 notifier 状态机（照自我锚「看一眼型快照面」先例） |
| `mobile/lib/features/community/presentation/screens/squad_list_screen.dart` | **新** | 列表屏（含创建/加入两个最小对话框：名称+目标+截止日期选择；凭 ID 加入） |
| `mobile/lib/features/community/presentation/screens/squad_detail_screen.dart` | **新** | 详情屏（榜卡 + 自习室卡 + 错题分享段；段级独立错误面） |
| `mobile/lib/features/community/presentation/widgets/share_error_to_squad_dialog.dart` | **新** | 选队分享弹窗（0 队诚实引导去小队列表；RadioListTile 弃用 API 规避，用 InkWell 选择行） |
| `mobile/test/features/community/presentation/screens/squad_list_screen_test.dart` | **新** | 4 测试：数据态字段直显 / 空态诚实引导 / 错误态重试 / 路由可达 |
| `mobile/test/features/community/presentation/screens/squad_detail_screen_test.dart` | **新** | 4 测试：**并列名次 1,1,3 如实** + 无账本数据不伪装 0% / **在室状态 + enter 动作调 API**（repo 调用计数=1 且状态翻转）/ 降级提示 + 切自我锚按钮且不渲染残缺榜 / 分享段空态诚实 + 快照卡如实且无「答案」字样 |
| `mobile/test/features/community/presentation/widgets/share_error_to_squad_dialog_test.dart` | **新** | 3 测试：**分享动作调 API 断言（squadId+errorId 精确记录）** / 0 队诚实引导且确认钮不可用 / 分享失败诚实报错 |

### 设计决策申报

1. **必达项分配**：详情屏严格 2 必达（榜 + 在室）；小队头部仅保留一行成员规模/剩余天数/目标的定位性元信息（非卡片非必达项）；错题分享按任务书「tab/段」落为详情内第三段，不另开第 4 屏——总屏数 2 + 1 段 < 上限 3。
2. **本人不在场判定用心跳而非轮询 presence**：`POST study-room/heartbeat` 是幂等兜底端点，不在场时诚实 `in_room=false` 且绝不自动重开——屏加载时调用一次兼作「我的状态查询」，进出后 invalidate 刷新。**未加后台定时心跳**（功耗决策，登记打磨项：可在室时以屏内 Timer 周期刷新，退屏即停）。
3. **has_ledger_data=false 的榜行显示「无账本数据」**而非 0%——D-COMM-3 schema 注释明确「不把 0 伪装成 0% 完成率」，展示层忠实执行；错题图片引用（question_image_ref）本期不渲染（需 MinIO 鉴权面取图，登记打磨项），题目文本为空时如实跳过该行。
4. **完成度/掌握度百分比展示层 `round()` 取整**（后端给 0.0-1.0 浮点）；分钟数原样直显不自算——数字真源全部在引擎侧。
5. **provider 风格**：只读快照 `FutureProvider.autoDispose(.family)` + 动作直调 repository——与自我锚 autoDispose 语义一致；未用 riverpod_generator 注解风格（error_book 域风格），保持与排行榜域先例统一。

## ③ 冲突面申报（对 wt162 backend / wt165 mobile 光子面 / wt166 backend）

- **本卡触碰面（全部 mobile）**：新增文件 12 个（community 域 squad 三件套 + 测试×3）；修改 4 个功能文件（`api_endpoints.dart` +19 行 squads 段、`community_routes.dart` 文件尾 +2 条路由、`sprint_screen.dart` AppBar +1 入口、`error_detail_screen.dart` AppBar +1 按钮 +1 方法 +1 import）+ l10n 5 文件（arb 新键块紧贴 `leaderboardSelfAnchorViewEntry` 之后、连续整块，`--3way` trivial）。
- **wt165（mobile 光子面）**：其面 photon 域 + 光子钱包/商店屏；与本卡零文件交集。若同轮也动 `api_endpoints.dart`/arb/l10n 生成文件，均为「各自区段追加」，`git apply --3way` 可解。
- **wt162/wt166（backend）**：本卡零 backend 改动、零迁移、零网关改动——后端四件套契约面只读消费。
- **v3-output/MOBILE-GAP-3/**：本卡专属输出目录，无他卡使用。

## ④ 诚实申报

1. **「错题本屏加分享入口」落位为错题详情屏**（`error_detail_screen.dart` AppBar 按钮）而非错题列表屏——分享需要单张错题上下文；列表屏卡片无逐卡动作位（ErrorCard 为多域共用组件，改动面大）。按钮可见（非藏于菜单），满足「分享入口按钮」意图；若产品要求列表卡片级入口，加 `ErrorCard.onShare` 可选回调即可，属一处小改。
2. **加入小队目前凭小队 ID 输入**（最小诚实入口：无公开发现/搜索面消费——后端 `is_public` 字段在但无公开列表端点被本卡消费）；邀请链接/二维码属后续产品化。
3. **分享附言（note）本期不传**：契约可空；弹窗保持一选一确认的最小面。附言输入框是弹窗内 +1 字段的小改，登记打磨项。
4. **createSquad 的 max_members 固定走后端默认 8**：SquadCreate schema 允许 3-8，UI 未暴露人数选择（期末互助场景 8 人上限是合理默认），未擅自加配置面。
5. **date picker 只选日期、提交取当日 23:59**：保证「未来时间」校验语义（服务端仍会再校验）；时区以本机本地时区 ISO 直传，服务端归一化 tzinfo（SquadCreate validator 已防御 aware/naive）。
6. **详情屏 AppBar 标题在小队加载完成前置为通用「冲刺小队」**，加载后换真名——非占位文案，是加载态如实呈现。
7. 测试对「并列名次」断言 `findsNWidgets(2) '1'`——后端契约保证 rank 并列语义，客户端不重算名次（也不校验服务端名次正确性——那是 wt158 的 13 用例职责）。
8. 未跑全库测试（资源纪律：新测试 11/11 + 三批定向回归 41 例全绿 + 路由装配冒烟/深链已覆盖改动可达面）。
9. **环境修复申报（非代码改动）**：worktree 缺未入库 `mobile/lib/gen/`（27 个 `*.pb*.dart`），已 `buf generate --template buf.gen.dart.yaml` 补齐（.gitignore 内，不入 patch）；`/tmp/wt167-baseline` 克隆仅用于 patch apply 验证，收工即删。

## ⑤ 回归与守卫结果

### 新测试（串行 `--concurrency=1`，3 文件一批）**11/11 全绿**

覆盖：三面渲染 / 列表空态诚实 / 榜并列名次 1,1,3 / 无账本数据诚实 / 降级提示 + 自我锚切换 / 在室状态 + **enter 动作 API 调用断言** / **分享动作 API 参数断言（squadId + errorId）** / 分享空态诚实 + 失败诚实 / 路由注册可达。

### 既有测试定向回归（全部串行，逐批，批后清 build/.dart_tool）

| 批次 | 文件 | 结果 |
|---|---|---|
| 1 | `app/router_smoke_test` + `app/router_deep_link_test`（全量路由装配，含新 squad 路由） | **12/12 绿** |
| 2 | `sprint_completion_screen_test`（sprint 入口改动相邻）+ `error_list_screen_test` + `error_book_provider_test`（错题详情改动同域） | **14/14 绿** |
| 3 | `widget/community_remaining_closure_test` + `unit/community_provider_security_test`（community 域既有面回归） | **15/15 绿** |

### analyze 与守卫

- 新文件 + 触碰文件 `flutter analyze`：**0 error / 0 warning**，新测试文件同样 0/0（逐条 info 清零或确认为存量行——sprint_screen/error_detail_screen 余下 info 均在我改动行号之外）。
- `check_ux_component_convention.py`：**PASS**（rawButton 19/19、rawSpinner 8/8、rawChip 11/11、colorLiteral 100/100 ratchet holds——新代码零新增违规）。
- `check_ui_design_tokens_ratchet.py`：**PASS**（color 239/275、fontSize 719/727）。
- **patch 基线验证**：`git clone` 基线 8daa8508 → `git apply --check` 干净通过。

## ⑥ 收工核查

- [x] `mobile/build`、`mobile/.dart_tool`：每批测试/analyze 后即删，最终已清
- [x] `/tmp/wt167-baseline`（patch 验证克隆）：已删
- [x] 未 commit / 未 push；主仓只读；零凭据
- [x] 交付物齐：`v3-output/MOBILE-GAP-3/REPORT.md` + `changes.patch`（21 文件，apply 验证通过）
