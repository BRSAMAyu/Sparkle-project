# WT307 · S-03 报告 — Squad/Sprint/Check-in 产品表面收敛（Stream: COMMUNITY）

- **Base SHA**: `61cea765`（main 当时的 HEAD，merge-base 已核实）
- **Final SHA**: `5df339df`（worktree 分支 `wt307-s03-community-convergence`）
- **Patch**: `v3-output/WT307-S03/changes.patch`（`git diff --binary main...HEAD`，49,990 bytes，13 files，+873/−42）

## 一、现状盘点（收敛前的重复/断裂）

社群主屏 `CommunityMainScreen`（`/community`）为 3-tab：[伙伴(默认), 动态, 群组]：

1. **feed 占核心**：公共帖子 feed 原是 Tab 1 且独占发帖 FAB——与 V3 定位「不是公共 feed」直接冲突。
2. **打卡断裂**：群打卡入口只在群聊屏（`group_chat_screen._showCheckinDialog`），社群首页只展示「今日 N 次打卡」计数、无动作入口；伙伴 check-in 藏在 accountability detail。
3. **小队入口孤悬**：`/community/squads`（榜+自习室+错题分享）此前仅靠 Groups tab 内一枚 tile 进入（NAV-IA P-4 补位）。
4. **artifact feedback 无产品面**：`CommunityShareRepository.fetchSharedResources`（`GET /community/resources`，质量分排序）与采纳接口（`adoptResource`）在产线**零调用方**；`SharedResourceCard` 是带测试的孤儿组件。
5. **Flame 语义漂移风险**：群详情以「火力值」直显 `totalFlamePower`，未声明其只代表群活跃。后端已有 entitlement 守卫（`backend/app/core/entitlement.py`：flame_level 永久禁作权益判据），mobile 无 flame→付费耦合残留（已全库 grep 核实）。

## 二、改动清单

| 文件 | 改动 |
|---|---|
| `community_main_screen.dart` | tab 重排为 **[群组协作(默认), 伙伴, 动态]**；FAB 绑定 feed 新索引 2；demo 模式下顶部常驻 `_DemoModeBanner`（演示声明，不可关闭） |
| `groups_hub_view.dart` | 新增 `_TodayCheckinSection`：我的群组今日打卡段（冲刺群排前、真源计数直显、打卡对话框复用群聊同款字段与 `CommunityRepository.checkin`，成功回执「+N 火苗喂进群火堆」把 Flame 锚定群活跃）；新增 `_ArtifactFeedbackSection`：孤儿 `SharedResourceCard` 接回产品面，走既有 resources/adopt 接口，加载/错误/空态诚实分面；新增 `_HubSectionHeader`（语义提示文案承担自解释） |
| `community_providers.dart` | 新增 `sharedResourcesProvider`（autoDispose，读既有 `CommunityShareRepository`，不建新真源） |
| `group_detail_screen.dart` | BonfireWidget 包 `Semantics`（`gdFlameSemantics`：火苗代表群活跃度） |
| `mock_community_repository.dart` | 4 个 demo 群名统一追加「（演示）」后缀（l10n `demoGroupSuffix`） |
| `app_zh.arb` / `app_en.arb` + 3 个 gen dart | 新键 14 个（communityHubCheckin*/communityHubArtifact*/demoModeBanner/demoGroupSuffix/gdFlameSemantics），改写 `communitySubtitle`（协作优先）、`gdFlamePower`（群活跃火苗/Activity Flame）；`flutter gen-l10n` 重生成 |
| 测试 | `groups_hub_view_test.dart` 新增 4 个收敛测试（保留原 NAV-IA P-4 测试）；`main_actions_smoke_test` 更新 tab 索引并断言 demo banner；`main_pages_load_smoke_test` 注释同步 |

卡面与现状冲突记录：卡面 Resource 标 HEAVY，但本卡按舰队纪律全程以 LIGHT 执行（无模拟器/Gradle/全量测试）；Locks=mobile-community，故后端 guest_seed 群的「演示」标示（DB 无 is_demo 列）留给 S-01（其 Work#3 即「标 seed/mock data」），见未尽事项。

## 三、测试证据（命令 + 数字）

| 检查 | 命令 | 结果 |
|---|---|---|
| Analyze gate | `flutter analyze --no-pub` + `check_flutter_analyze_gate.py` | ✅ ERROR=37 (≤42) / WARNING=17 (≤16+5) / INFO=598 (≤594+5) |
| Rule guards | `bash scripts/run_all_rule_guards.sh` | ✅ **83 rules 全过，exit 0**（含 COMM-LB / N9 / UI-TOKENS / SPACING / l10n 双守卫 / K / Z） |
| 收敛测试 | `flutter test --concurrency=1 test/features/community/presentation/widgets/groups_hub_view_test.dart` | ✅ 5/5（4 新增：打卡段 sprint 排序+真源计数、打卡动作+火苗回执、成果反馈段渲染、无群组诚实空态） |
| 主屏冒烟 | `flutter test --concurrency=1 test/app/main_actions_smoke_test.dart test/app/main_pages_load_smoke_test.dart` | ✅ 15/15（含 demo banner 断言、feed 降级后 FAB 在 Tab2） |
| 回归 | `flutter test --concurrency=1 mock_community_repository_test.dart squad_list_screen_test.dart shared_resource_card_test.dart` | ✅ 16/16 |
| 内存门 | 每次 test 前 `sysctl vm.swapusage` | ✅ 首批 1713MB ≥1.2G 放行；末批后 916MB，即止不再加跑 |

集成/simulator evidence：按内存纪律禁用模拟器，**未执行**——以真实接口契约级 widget 测试（fake repo 走真实 repository/接口形状）替代，见风险与 UNVERIFIED。

## 四、验收对照

- [x] 单人核心 journey 不受依赖：社群改 gyr 动仅限 mobile/community 表面层；单人功能（聊天/首页/任务）零触碰；社群各段失败互不拖垮（段级错误面）。
- [x] 小组 journey 自解释：收敛段标题+一句语义提示（打卡喂火堆/采纳进知识库）；空态给引导动作。
- [x] seed/demo group 明确标演示：demo 模式常驻 banner + 4 个 mock 群名「（演示）」后缀（双重标示）。
- [x] feed 降级：末位 tab，不再默认曝光。
- [x] Flame 不与付费绑定：Semantics+文案锚定「群活跃」；核实后端 entitlement 守卫在位，mobile 无耦合。
- [x] 不重建权威真源：全部读/写走既有 repository 与接口（myGroups 计数、checkin、/community/resources、adopt）。
- [x] 不弱化守卫：baseline JSON 零改动；新代码按守卫要求整改（DS 令牌、4pt 栅格、N9 固定话术+debugPrint）。
- [x] 不以 mock 冒充真实：demo 数据显式声明；产品动作全部走真实接口。

## 五、风险

1. **tab 重排**改变默认落点（伙伴→群组协作）：现有全站导航/深链均指 `/community` 根，无 index 级依赖；主要 smoke 测试已同步。真实用户习惯迁移风险留待验收。
2. **成果反馈段首屏多一路网络请求**（/community/resources）：失败仅段内错误卡，不影响其他段。
3. demo banner 文案与 mock 群名后缀使 demo 快照类断言（如有外部）需同步——仓内测试已全绿。

## 六、未尽事项 / 移交

1. **后端 guest_seed 群（算法冲刺小队等 6 群）的演示标示**：Group 表无 is_demo 列，标示需 seed 文案层改动或 schema 演进，超出 `Locks: mobile-community`，移交 **S-01（Work#3 标 seed/mock data）**。真实 guest 用户视角的群组标示在 S-01 落地前依赖名称语义。
2. **两账户 realtime/重连/撤回实测**（COMMUNITY.md Acceptance）：属 S-01 卡面，本卡未覆盖；UNVERIFIED。
3. 依赖卡 S-01 / U-05 的产出在本次执行期间未见 v3-output 回执（并行窗口），未阻塞本卡面层收敛。
4. 收工清理：/tmp 下 analyze 中间产物已删；worktree 内无 build/.dart_tool 入库项（gitignored）；无模拟器/浏览器进程遗留。
