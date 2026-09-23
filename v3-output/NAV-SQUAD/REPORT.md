# NAV-SQUAD — 导航可达性 + 小队闭环 改造回执

- 卡：NAV-SQUAD（消费 NAV-IA P-1/P-3/P-4 + A-SPEC2 top10 v2 #3）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt224`（分支 `wt224-nav-squad`，基线 `a025e82a`）
- 性质：代码改造卡。零 commit 零 push，全量 diff 见同目录 `changes.patch`。
- 用户红线自查：四件改动全部为单向增强/断链摘除/落点统一，不改变任何既有可用行为（详见各条验收）。

---

## 1. 盘点（开工前实测，@a025e82a）

| 项 | 实测结论 |
|---|---|
| `/settings/transparency` | `chat_settings_screen.dart:277` push，全库路由注册 **0 条** → 必落 404（复现 NAV-IA A-1） |
| 通知落点 | `home_notification_card.dart:63` push `/notifications`；`/notification-center` 另有 4 入边；`/notification-analytics` 0 入边但挂在路由表（可被任意深链触达） |
| `/notifications` | home_routes 注册为正式 pageBuilder 路由（NotificationListScreen + dashboard 音景） |
| Community tab 内小队入口 | 0（`/community/squads` 仅 sprint_screen:69 与错题分享弹窗两个入边） |
| 小队邀请环 | `SquadInfo.id` 详情屏零显示零复制；`_JoinSquadDialog` 要求手输 ID 但 ID 无处可取 |
| `squad_list_screen._formatDate` | 手工拼接 `'y/m/d'`（:372-373），绕开 `core/display/lexicon/date_formatting.dart` 唯一入口 |
| 榜单 isSelf | `_LeaderboardRow` 无自我行标识；端上有 `currentUserProvider`（既有 Riverpod auth 状态）可比对 |

## 2. 实现（四件全落地）

### 2.1 死链修复（NAV-IA P-1）
- `chat_settings_screen.dart`：移除「打开高级设置」ListTile 整块（GraphiteCardSurface 入口卡）。`TransparencyPreferences` 数据模型仍被本屏使用，`transparency_settings_screen.dart` import 保留；arb 键 `chatSettingsOpenAdvanced*` 保留未删（防回滚），dart 生成物中对应 getter 同步保留（键集必须与 arb 一致，l10n parity 守卫约束）。
- 验收：`grep -rn "settings/transparency" mobile/lib` = **0 条**；新增 widget 测试断言入口不渲染且页面其余区块照常。

### 2.2 通知落点统一（NAV-IA P-3）
- `home_notification_card.dart`：未读通知 banner push 目标 `/notifications` → `/notification-center`（与推送侧 push_navigation_service 一致）。
- `home_routes.dart`：`/notifications` 降级为 **legacy redirect → /notification-center**（照抄 chat_routes.dart legacy redirect 模式，query 参数透传；`name: 'notifications'` 保留，goNamed 调用方不受影响）；NotificationListScreen 摘出 home_routes（屏文件保留）。
- `notification_center_routes.dart`：`/notification-analytics` 从路由表摘除；屏 + provider 文件保留，登记 `KNOWN_CODE_DEBT_LEDGER.md` P3 #11（重新挂载需产品裁决）。
- 验收：全库通知类 push 字面量全部指向 `/notification-center`（grep 实证）；`/notifications` redirect 落同屏（router_smoke_test + 专项测试双覆盖）。

### 2.3 Community tab 补小队入口（NAV-IA P-4）
- `groups_hub_view.dart`（Groups tab 首屏）：首行新增 `_SquadsEntryTile` 一行式入口 → `CommunityRoutes.squads`。样式完全复用既有家族：GraphiteCardSurface + ListTile（照 `_JoinedGroupTile` 同构），sprint 语义 = timer 图标 + warning 0.16 alpha 底（照同文件 sprint 约定），零新样式、零字面量色/字号。
- 文案复用既有 `squadEntryLabel`（「冲刺小队」），仅新增 1 条副标题 key。
- 验收：Community Groups tab 首行可见入口，点击落 `/community/squads`（widget 测试）；sprint 屏既有入口未动（未触碰 sprint_screen.dart）。

### 2.4 小队邀请环补全（A-SPEC2 top10 #3）
- `squad_detail_screen.dart`：meta 区新增 `_SquadInviteCard`（邀请段）——小队 ID 直显（`squad-invite-id-value`）+ 一键复制（SparkleButton outline small，Clipboard.setData + SensoryFeedbackService + AppFeedback 反馈，照 universal_share_bottom_sheet 既有惯例）+ 一句话说明（「把小队 ID 发给同学，对方在『加入小队』里粘贴即可入队」）。纯端上：ID 已在下传 payload，零后端改动。
- `squad_detail_screen.dart` 榜单：`_LeaderboardCard` watch 既有 `currentUserProvider`，`_LeaderboardRow` isSelf 行 accent 容器高亮（brandPrimary 0.12 alpha 底 + 0.32 边，唯一 accent；色彩之外配「我」徽标，不依赖纯颜色）——`selfViewOnly` 降级分支与并列名次 1,1,3 逻辑零改动。
- `squad_list_screen.dart`：`_formatDate`（'y/m/d' 手工拼接）删除，截止日改走 `formatSparkleDateOnly`（date_formatting 唯一入口，X3/CO-G4）。
- 验收：widget 测试——复制动作写剪贴板（mock platform channel 断言 clipboard 内容 = 小队 ID）+ 反馈文案出现；isSelf 行样式断言（self-row 容器存在 + 徽标存在 + 无 userId 时不误亮）；日期格式断言（`^\d{1,2}月\d{1,2}日$`，选日不依赖测试机时钟）。

### 2.5 l10n（zh/en 双语）
- 新增 5 key：`squadDetailInviteTitle` / `squadDetailInviteHint` / `squadDetailInviteCopyAction` / `squadDetailSelfBadge` / `communitySquadsEntryHint`；arb 增量 **+5 行/文件**，dart 生成物手工按既有格式同步 +62 行（见 §4 冲突面第 3 条）。
- `check_l10n_regen_parity.py` **绿**（11209 template keys == abstract members）。

## 3. 回归验证（定向，不宽扫描）

| 套件 | 结果 |
|---|---|
| squad_detail_screen_test（5 既有 + 3 新增） | 8/8 绿 |
| squad_list_screen_test（4 既有 + 1 新增） | 5/5 绿 |
| home_notification_card_test（3 新增） | 3/3 绿 |
| groups_hub_view_test（1 新增） | 1/1 绿 |
| chat_settings_screen_test（2 新增） | 2/2 绿 |
| full_route_coverage_test（改 1 断言）+ notification_list + provider | 29/29 绿 |
| router_smoke_test（改 1 断言为 redirect 语义） | 8/8 绿 |
| main_pages_load_smoke / main_actions_smoke（Community tab 所在主旅程） | 6 + 9 全绿 |
| share_error_to_squad_dialog / push_navigation_service / community_401 | 11/11 绿 |

守卫：`check_l10n_regen_parity` 绿；`check_ux_component_convention` 绿（ratchet holds）；`check_dl_spec_ratchet` 绿；`check_rule_aq/bg` 绿（补齐 gitignored 生成物后）；COMM-LB / BA-ROUTES 绿。**遗留红与本次改动无关**：`check_rule_bi`（backend/tests/northstar_eval/feature_tour.py:473）与 `check_ui_design_tokens_ratchet`（group_discover_screen fontSize 3>2、modeling_chat_screen 新文件）在主仓 baseline 同样红，且不涉本卡触碰的任何文件（对比法实证）。

## 4. 冲突面声明（跨域重叠，诚实申报）

1. **mobile/lib/features/chat**：仅动 `chat_settings_screen.dart`（本卡 P-1 唯一落点）。与在航的 B3-CHAT/批4（wt160 收件箱桥）无文件重叠；arb `chatSettings*` 键未增未删。
2. **mobile/lib/features/notification_center + home**：动了 `home_routes.dart`、`home_notification_card.dart`、`notification_center_routes.dart` 三个文件。与 A 线批4 收件箱桥（D8-5 裁决 chat 收件箱为 sheet 形态、无路由）不冲突——本卡未触碰 chat 收件箱。**`/notification-analytics` 摘除会与任何「通知分析」方向的在航卡相撞**：若后续要挂回，走 LEDGER #11 的产品裁决路径。
3. **mobile/lib/l10n（arb 三件套为全舰队最高冲突文件）**：本卡 arb 增量 +5 key/文件（squad/community 段内插入，位置 zh/en 镜像）。本地 Flutter SDK（3.41.3 homebrew）`flutter gen-l10n` 产物与仓内既有 dart 生成物存在 ~130 行格式漂移（trailing comma/缩进/doc comment，SDK 模板差异，即 L10N-REGEN 守卫文档所述历史问题）——为守住「增量最小」与仓内格式一致（最近次 l10n 合入 0886aaff 同为纯增量格式），dart 三件采用**手工按既有产物格式同步 5 个 getter**（arb 为准、键集完整），parity 守卫语义校验绿。字节级 `gen-l10n && git diff --exit-code` 需与仓内产物同版本 SDK，本机不具备，如实登记。
4. **mobile/lib/features/community**：动 squad 双屏 + groups_hub_view。与错题本 2.0（error_book N12 色阶已在主仓 e7cf28e1 合入，本卡未触碰 error_book）零重叠；`share_error_to_squad_dialog.dart` 未动。
5. **docs/engineering/KNOWN_CODE_DEBT_LEDGER.md**：P3 表新增 #11 一行（notification-analytics 孤儿面登记）。

## 5. 没做到什么（如实）

- NAV-IA P-4 附带项「AccountabilityHubScreen（约 700 行成品屏）挂载与否」属产品二选一裁决，**本卡未处理**（零引用状态保持原样，未登记台账——它先于本卡存在，避免越权代裁决）。
- NAV-IA P-5 孤儿路由清点（learning-path/favorites/search 等 redirect 化）、P-2 光子面闭合、P-6/P-7 均不在本卡清单，未动。
- 通知数据层合并（/notifications 屏与 notification-center 数据双源）仍是 NAV-IA B-3 的另立卡项；本卡只做了落点统一第一刀。NotificationListScreen 现为 0 入边屏（redirect 不再经它），**未删文件**——它是「通知数据层合并」另立卡的现成物料，暂留（若主会话倾向删除请指示）。
- isSelf 徽标用「我」文本而非图例说明（§1.4.3 规格原文未在本仓 DL-SPEC 文档中找到成文条款，按 A-SPEC2 REPORT §1.1「排行榜 bot 必带你自己排第几高亮」公约做了容器+徽标双保险实现）。

## 6. 收工核查清单

- [x] 全部改动在 wt224 worktree 内；主仓与其它 worktree 只读（仅读取主仓 gitignored 生成物 protobuf/gen 复制到本 worktree，补齐本地编译环境）
- [x] 无 stash / reset / clean / 分支切换
- [x] 零 commit 零 push；`changes.patch` 为 `git diff` 全量（新文件以 intent-to-add 纳入 diff）
- [x] 新增用户可见文案全部走 arb zh/en；parity 守卫绿
- [x] UI 全部消费既有组件家族与 DS 令牌（GraphiteCardSurface/SparkleButton/ListTile/DS.* 令牌），零新裸组件、零字面量色/字号（ux-convention 守卫绿）
- [x] 回归测试全绿（上表 8 个套件，含所在域既有测试零破坏）
- [ ] 收工清理：删 worktree 内 `mobile/build`、`mobile/.dart_tool`（见下）
- [x] 无遗留进程（flutter test 串行跑完即退；`ps` 复核 0 残留）
- [x] /tmp 无驻留（调试用临时测试文件已删）
