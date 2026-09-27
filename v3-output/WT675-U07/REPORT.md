# WT675-U07 · 长尾 Feature Contextualization 与导航减负（U-07）续做盘点

- 会话：wt675（卡池 U-07）｜2026-09-25｜base=18e3ab98（worktree `agent/node-b/wt675/u07`，不 push）
- 性质：**双证判卡面已完成部分 + 从实际进度续做**。U-07 本体已由 wt356 落地，本卡执行「合并后在 integration HEAD 重跑相关检查」与 wt356 自报 DEFERRED 件的补跑，并处置盘点发现的漏网暴露边一项（V3-FIX-360，当场收口）。

---

## 1. 卡完成双证判定（不重做判据）

| 证据 | 内容 |
|---|---|
| 证 1（提交） | 8ac6bad5「feat(nav): wt356 卡 U-07 长尾导航减负……**U-07 done 解锁 U-10**」——portfolio 分档执行：LABS 走 unlisted、routes.dart 路由真源零 diff、五 Tab 零改动、CORE 面 9 处入口边摘除、CONTEXTUAL 新增 plan→日历 CTA、6 钉契约测试；后随 c8b445b5（洞察枢纽卡失败感知双源修复，U-07 收敛副作用债兑现）与 6161ded7（mirofish 测试改写至 U-07 后契约）收口 |
| 证 2（树内） | `v3-output/WT356-U07-NAV/REPORT.md` 在库；`mobile/test/widget/nav_decontextualization_contract_test.dart` 6 钉在 HEAD 可执行；本卡 HEAD 复核逐钉实跑通过（见 §3） |
| 状态权威注记 | tasks.json U-07 仍标 TODO（规格权威与实际进度脱节）；按本会话执行纪律**不碰 tasks.json**，报请规格权威侧核正（8d4291aa 同款批次）；fleet state done 列表未在本 worktree 验证（coordination 分支不在本地） |

## 2. 卡面验收对照（HEAD=18e3ab98 复核 + 本卡增量后保持）

| 卡面验收 | 判定 | 证据 |
|---|---|---|
| 五 Tab 不增加 | ✅ | shell_navigation.dart 5×NavigationDestination 实测；契约钉 1 持续强制；8ac6bad5 后 routes.dart/shell_navigation 仅 f25cb01c 一触（visual-elements warm refresh 403 噪声短路，非暴露边） |
| CORE journey 不出现无关 feature 入口 | ✅（本卡补齐后才成立） | wt356 摘 9 边后仍漏 home 仪表盘卡族一边——seed_library（LABS）卡 defaultVisible 常驻+编辑面板可加回（=V3-FIX-360，本卡收口）；其余 LABS 路由常量引用面全仓 grep 仅 LABS feature 自身与 routes.dart 挂载（unlisted） |
| HIDDEN 用户不可达 | ✅ | leaderboard 全站榜无路由（D-COMM-1），契约钉 3 固化唯一面=自我锚；COMM-LB 守卫 PASS |
| CONTEXTUAL ≥1 自然 journey | ✅ | plan 详情→日历 CTA（plan_detail_screen.dart:101-111，calendarTitle 复用零新键）+ task→focus + galaxy 节点→知识详情（既有） |

wt356 遗留四项现状：①死 l10n 键收割——已由 wt363/U-10 完成（d85e9a9a，42 键）；②galaxy theater overlay 回路——按 REPORT §五.2 保留（Labs 内部延续，动渲染层超外科边界，不入本卡）；③vocabulary 无 UI 面——如实记录维持（CONTEXTUAL 角色需新功能卡非导航卡）；④MODULE_PORTFOLIO portfolio 权威——未触碰（B-01 权威）。

## 3. wt356 DEFERRED 件补跑（本卡完成）

REPORT §四的定向六文件 flutter test（当时 swap 918M<1.2G 门禁缓）——本卡 swap 空闲 1.6G≥1.2G 窗口内 `--concurrency=1` 串行实跑，**六文件全绿**：

1. nav_decontextualization_contract_test（11 用例，含本卡新钉）
2. dashboard_screen_structure_test（并入第一批共 11）
3. learning_insights_navigation_test ＋ insights_frontend_smoke_test ＋ chat_settings_screen_test ＋ learning_insights_overview_screen_test（第二批共 22）

simulator/integration 证据缺口维持 wt356 移交（LIGHT 纪律禁模拟器，非本卡可闭）；动态证据=可执行 widget 钉全绿。

## 4. 本卡增量实施：V3-FIX-360 home 种子库 LABS 暴露边摘册（当场收口）

**发现**：`seed_library`（MODULE_PORTFOLIO.md:37=LABS「developer/demo seeds」）以仪表盘卡形态在 home CORE 面三处可达，均为 wt356 首轮盘点/契约钉扫描清单盲区：

- `dashboard_card_config_provider.dart`：seedLibrary 在 `defaultVisible`/`defaultOrder` 双默认清单（旧配置还有 legacy 两清单）
- `dashboard_card_section.dart:125-126`：挂载 `SeedLibraryDashboardCard` 直推 `/seed-libraries`
- `dashboard_edit_sheet.dart:538/565`：编辑面板标题/副题双 case，LABS 可随时加回

**手术**（与 wt356 同形制：摘入口边、不删路由与功能文件）：

1. `DashboardCardIds` 五清单除名 + 除名注记（旧持久化含该 id 由 `fromJson` 的 all 过滤诚实降解；legacy 匹配表同步除名，老用户排序迁移路径保持可用）
2. `dashboard_card_section`：挂载 case + import 摘除
3. `dashboard_edit_sheet`：标题/副题双 case 摘除
4. `seed_library_dashboard_card.dart` 本体保留（LABS 功能文件不删先例；转零引用，Labs 化可恢复）
5. 契约钉补盲区：CORE 面扫描 +3 文件（card_section/edit_sheet/card_config_provider）+3 禁 token（`SeedLibraryDashboardCard`/`DashboardCardIds.seedLibrary`/`dashboardCardSeedLibrary`）
6. 测试 harness（dashboard_test_harness）两处 cardOrder 同步除名（visibleCardIds 未含该卡，渲染面零变化——golden 基线零触碰，wt667 面无撞）

## 5. 验证证据

- **analyze**：`flutter analyze` No issues found（基线 E0/W15/I587 零漂移）
- **定向 test**：三批共 **68/68 全绿**（§3 六文件 + harness 用户面 dashboard_conversion_cards_visibility / dashboard_growth_sections_l2 / progress_consistency_f9 / u09_platform_render_contract / sprint_screen / stuck_journey_entry / today_cockpit_card / predicted_intent_card，--concurrency=1）
- **路由守卫单项**：AO-ROUTER（check_rule_ao_not_in_router）/S28-ROUTER/S29-ROUTER/AX（route_ownership）/BM（dead_routes）/BA-ROUTES（parity）/COMM-LB（leaderboard_unrouted）/S21-HISTORY 全 PASS；AO-Labels（check_rule_ao_no_diagnostic_labels）homebrew 默认 python3 缺 loguru 为环境项，run_all 脚本自解析 python3.11 后 PASS
- **全量守卫**：`bash scripts/run_all_rule_guards.sh` **86 规则 exit 0**（AQ/BG worktree 环境项按 wt369/wt374 先例自主仓补拷 backend app gen + gateway gen，未入库）
- **零触碰**：`.env`、`tasks.json`、arb/gen-l10n（wt672 面）、golden 基线与 visual_baseline（wt667 面）、insight_hub_card 等异步状态注入面（wt673 面）、Semantics 标签面（wt674 面）、backend 四卡声明面

## 6. 移交与登记

| 项 | 去向 |
|---|---|
| V3-FIX-360 | 本卡当场收口（FIXED，详见 DYNAMIC_ISSUES.md 该行；号段 357-359 已占用后顺延，本卡用 **360**） |
| `dashboardCardSeedLibrary`(+Subtitle) 两键转死键 | 归 wt672（U-10）收割批——arb 文案面本卡避开未动 |
| tasks.json U-07 status=TODO 脱节 | 报请规格权威核正（本卡纪律不碰 tasks.json） |
| simulator/integration 截图证据 | 维持移交主会话 HEAVY 窗口（wt356 §四原样） |
| U-01 收敛移交候选（chat parallelClass 62 等） | 属 U-01 视觉收敛卡谱系，非 U-07 导航域，不越界 |

## 7. 收工清单

- [x] 双证判定 + HEAD 复核（不重做）
- [x] V3-FIX-360 摘边手术 + 契约钉补盲区
- [x] analyze No issues + 定向 test 68/68 + 守卫 86 exit 0
- [x] 台账登记（V3-FIX-360，独立 commit）
- [x] worktree 自产物（backend/gen、gateway/gen 为 gitignored 补拷件）不入库
