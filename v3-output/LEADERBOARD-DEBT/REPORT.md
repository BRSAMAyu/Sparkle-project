# LEADERBOARD-DEBT 收工报告（D 纵队·社群线，wt199）

- 基线：`8f97733d`（clean）｜卡：排行榜死代码收口（债账 #3 移动端尾巴，D-COMM-4 收官件）
- 结论：**整链删除**（无抽取复用）。净变化 12 文件，+392 / −1491（净 −1099 行）。
- 交付：本目录 `changes.patch`（git diff 全量，含删除文件与本报告外全部改动）。

## ① 复用价值盘点 + 裁决链

**死链范围核实**：`mobile/lib/features/leaderboard/` 现存 1613 行 = 死链三件套 **1143 行**（`leaderboard_screen.dart` 420 + `leaderboard_provider.dart` 348 + `leaderboard_repository.dart` 375，与债账数字精确吻合）+ 活链 self-anchor 四件（model 84 / repo 52 / provider 20 / screen 289）+ `leaderboard_routes.dart` 25（只挂 `/leaderboards/self-anchor`，D-COMM-1 裁决唯一路由产品面）。

**与 wt167 小队详情榜（`squad_detail_screen.dart::_LeaderboardCard` + `squad_board_models.dart`）逐能力对比**：

| 能力 | 死链（LeaderboardScreen） | 小队详情榜（活） |
| --- | --- | --- |
| 并列名次 1,1,3 | 直接渲染 `entry.rank`，无并列语义、无测试 | 契约级如实渲染不重排（模型注释 + `squad-leaderboard-rank-*` key 测试） |
| 无账本态 | **无**——把缺失伪装成 0 分 | `has_ledger_data=false` → 「无账本数据」，不把 0 伪装成 0% |
| <3 人降级 | **无** | `self_view_only`/`board_valid=false` → 降级文案 + 自我锚交接按钮 |
| 口径 | XP/分数/连胜（`score`/`scoreLabel`/`badge`） | sprint 完成度%（FLEET-BRIEF 反刷分红线唯一合法口径） |
| 比较面 | 领奖台 🥇🥈🥉、我的排名横幅（含 percentile）、好友榜——大池比较 | 队内完成度列表（小池、同目标、completion 单口径） |
| 设计令牌 | 旧 `DS.*` 静态量 + 硬编码 emoji | `context.typo/colors` 令牌（现行规范） |
| 路由 | 未路由（COMM-LB 钉死） | 小队详情屏正式路由面 |

**widget 层复用候选逐一否决**：
1. `_buildPodium`/`_buildPodiumItem`（领奖台视觉）——screen 私有方法，非独立 widget；硬编码 emoji + 旧 DS 令牌；且领奖台=大池异质水平比较的视觉形制，小队榜（完成度列表）与自我锚（自比序列）均无引入理由，引入反而违反 D17 裁决精神。
2. `_buildMyRankBanner`（percentile 横幅）——百分位=典型大池比较面，属被裁决禁入的模式，无可复用场景。
3. 列表行/空态/错误面——小队榜与 self-anchor 屏已有令牌化等价实现，无增量。
4. `LeaderboardEntry/LeaderboardData/MyRankState` 模型——缺 `has_ledger_data`/`self_view_only`/并列名次语义，相比 `SquadLeaderboard*` 是严格子集还带错误口径。
5. repo 的 demo mock 块（约 300 行）——纯死数据，无复用价值。

**裁决：整链删除。** 加固理由：死链的 XP/连胜口径正命中 FLEET-BRIEF §四.2 反刷分红线禁入口径，留着即负资产。

## ② 改动清单

**删（D）**：
- `mobile/lib/features/leaderboard/presentation/screens/leaderboard_screen.dart`（420 行）
- `mobile/lib/features/leaderboard/presentation/providers/leaderboard_provider.dart`（348 行，含 `leaderboardProvider`/`myRankProvider`/`LeaderboardEntry`/`LeaderboardData`/`MyRankState`/`LeaderboardType`/`LeaderboardPeriod` 全部符号）
- `mobile/lib/features/leaderboard/data/repositories/leaderboard_repository.dart`（375 行，含 `StringCapitalize` extension——仅本文件自用，无外部消费）

**改（M）**：
- `mobile/lib/core/services/session_refresh_service.dart`：移除 import + `leaderboardProvider`、`myRankProvider` 两条会话绑定登记（N-4 登记面随符号消灭，登记清单语义不变）
- `mobile/lib/core/network/api_endpoints.dart`：删 6 个死常量（`leaderboards`/`leaderboardsSummary`/`leaderboardsMyRank`/`leaderboardsTypes`/`leaderboardsTopThree`/`leaderboardsRefreshCache`），**保留 `leaderboardsSelfAnchor`**（活）并留销账注释
- `mobile/lib/l10n/app_zh.arb` + `app_en.arb`：删 11 个死键（`leaderboardTitle/Global/Friends/Group/Subject/Weekly/Streak/MyRank/Points/NoData/LoadFailed` 含 @placeholders 块，两文件各 −30 行的连续块 1395-1424）；**保留 `leaderboardSelfAnchor*` 13 键**（活）
- `mobile/lib/l10n/app_localizations*.dart`（3 件）：`flutter gen-l10n` 重生成（守卫 `check_l10n_regen_parity.py` 绿）
- `mobile/lib/app/routes.dart`：两行行尾注 `rule-comm-lb: ignore`（详见 ④-1）
- `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md`：条目 3 移动端尾巴标销账（写明裁决链与删除面）

**留（未动）**：self-anchor 全链、`leaderboard_routes.dart`（自我锚路由装配）、`fpStreakLeaderboard` l10n 键（app_en.arb:11911 附近，非 leaderboard 前缀、非本卡范围）、网关 wildcard 代理（未触碰）。

## ③ 冲突面声明

- **与 wt195（galaxy_screen + l10n）**：同文件 `app_zh.arb`/`app_en.arb`。我的删除**严格限定 `leaderboard` 死键连续块（原 1395-1424）**，未触碰文件尾部块与任何 `galaxy`/`fp` 键；wt195 若在尾部追加新键，apply --3way 无交叠（中段删块 vs 尾部加块）。dart gen 三件我做了全量重生成——若 wt195 也加了 arb 键，**合入顺序在后者必须重跑 `flutter gen-l10n`**（或由主会话在 apply 后统一重生成），否则 parity 守卫会拦下。
- 与 wt197（compose）、wt198（northstar_eval）：无文件交叠。
- `session_refresh_service.dart`/`api_endpoints.dart`/`routes.dart`：本 worktree 内无其他卡触碰迹象（基线 clean 起步），但若有并行卡同样动登记清单/端点常量，apply 时以语义核对为准。

## ④ 诚实申报

1. **基线 COMM-LB 守卫在 8f97733d 上本来就是红的**：`routes.dart:27`（import）与 `:387`（routes spread）的 self-anchor 接线命中守卫的宽正则（`LeaderboardScreen|leaderboard` 大小写不敏感）——守卫成文时预期自我锚「走独立 widget」，实际落地成了路由。修复方式＝守卫自身设计的 escape hatch：两行行尾注 `// rule-comm-lb: ignore D-COMM-1 自我锚=唯一裁决路由面，非全站榜`（同行注释，`IGNORE_RE` 才能命中）。守卫对其余行的不变量（不挂 LeaderboardScreen、网关 wildcard-only）原样保留且更强——`LeaderboardScreen` 符号现已全仓不存在。**未改守卫脚本本身。**
2. **l10n dart gen 的 diff 大于键删除本身**（每件约 ±200 行）：被合入的 dart 产物与当前 gen-l10n 版本存在既有格式漂移（守卫 docstring 记载的 L10N-REGEN 债），我的重生成顺带把格式规范化为当前工具链正典；语义面由 `check_l10n_regen_parity.py`（11203 template keys == abstract members）背书。
3. **worktree 环境噪声（非本次改动引入）**：`flutter analyze` 的 error 级报告全部是 `package:sparkle/gen/*.pb.dart` 缺失（gen 产物 gitignored、本 worktree 未生成）；我按正典流程 `make proto-gen`（docker 工具链镜像 pull 失败自动 fallback host 工具链）在 worktree 内生成后，定向测试全绿。触碰文件仅剩既有 info 级 lint（routes.dart:6 directives_ordering 等，改动前即存在）。
4. 测试发现零新增：router smoke/深链/全路由覆盖/squad 详情+列表/self-anchor/N4 跨账号隔离共 **52 用例全绿（--concurrency=1）**；community 域对比法零新增行为面（squad 测试未改一行仍绿＝无回归）。
5. `mobile/lib/gen/`（1.4M，gitignored 环境产物）留在了 worktree 内，随 worktree 生命周期回收；`build/`(129M)/`.dart_tool`(132K) 已删；/tmp 无我产生的文件；未起过模拟器/浏览器；收工时无本卡进程。

## ⑤ 收工核查

| 核查项 | 结果 |
| --- | --- |
| `check_rule_comm_lb_leaderboard_unrouted.py` | **PASS**（基线红 → 修复后绿） |
| `check_l10n_regen_parity.py` | **PASS**（11203 keys，zh/en subclasses complete） |
| `check_i18n_coverage.py` | PASS |
| `flutter analyze`（触碰文件） | 无新增告警（error 级均为缺 gen 的基线环境噪声，见 ④-3） |
| 定向测试 7 文件 52 用例 | **All passed**（router_smoke / router_deep_link / full_route_coverage / squad_detail / squad_list / self_anchor / N4 隔离） |
| 死符号残留扫描 | `leaderboardTitle`/`LeaderboardScreen`/`leaderboardProvider`/`myRankProvider`/6 死常量全仓零命中（`ApiEndpoints.leaderboard*` 仅剩 `leaderboardsSelfAnchor`） |
| 纪律 | 零 commit / 零 push / 零凭据；改动全部在 wt199 内 |
| 债账 #3 | 已在 worktree 内 `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md` 标销账 |

**给主会话的合入提示**：apply 后若 wt195 的 arb 键同窗口合入，记得在最终态重跑 `flutter gen-l10n` + `check_l10n_regen_parity.py`；COMM-LB 守卫现在依赖 routes.dart 两行的行尾 ignore 注解，合入冲突时勿丢注释。
