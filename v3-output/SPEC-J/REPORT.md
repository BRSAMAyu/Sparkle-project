# SPEC-J · galaxy 工作视图最小切片（A-SPEC top10 #10，A 线收官项）

> Worker：A 纵队设计语言线 ｜ worktree：`wt195`（基线 95a0af3a）｜ 2026-09-23
> 规范依据：`v3-output/A-SPEC-V1_1/REPORT.md` §5 清单 #10 + §2.3 X-G2 + §4.1.4 ≤1 名额铁律
> 交付物：本报告 + `changes.patch`（7 个文件，+863 行，零凭据）｜ 未 commit / 未 push

## 0. 改造内容一句话

默认进星图不再只落总览：若服务端有复习推荐，先聚**推荐锚点邻域**为工作视野（可见节点 ≤20），并在屏上挂**唯一一枚**「下一个建议碰：X」chip，点击直达既有复习流；无推荐用户诚实保留原总览视野、不挂 chip。

## ① 聚焦锚点选型裁决（复用哪个既有信号源）

**裁决：采用「用户最需复习节点」路径，信号源 = 服务端既有复习推荐字段组**——`GalaxyNodeModel.isReviewRecommended`（`is_review_recommended`）+ `reviewUrgencyScore`（`review_urgency_score`，取全图最高分；同分保持图序首个，稳定）+ `reviewUrgencyReason`（仅用于 chip 点击后的既有理由链映射，见 ②-6）。链路证据：`backend/app/schemas/galaxy.py:330/:415`（服务端计算并下发）、`galaxy_grpc_service.py:114`（gRPC 透传）、`mobile/lib/shared/entities/galaxy_model.dart:316-319`（客户端解析）——与节点预览卡推荐理由链（`galaxy_node_preview_card.dart:423`）**同一数据源，零新造算法**。

**否决「sprint 目标关联节点」路径**：客户端 galaxy 域模型与 plan 域之间不存在 goal→node 关联字段（`goal_graph_overlay_provider` 的 goal-world 模式是另一套覆盖层，不是节点级 goal 关联），自建关联即违反「不自造算法」约束。故锚点 = 服务端推荐信号，sprint 目标关联留待后端补字段后的 D5 大卡。

## ② 实现清单（全部在 `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` + l10n + 测试）

| # | 内容 | 落点（当前 HEAD 行号） |
|---|---|---|
| 1 | 状态与常量：`_workViewMaxVisibleNodes=20`、缩放档位表 `[0.6,0.7,0.8,0.9,1.0,1.25,1.6,2.0]`（上限低于相机 maxScale 2.5）、`_workViewFocusTimer/_workViewAnchorId/_workViewChipHandled/_workViewCameraEngaged` | :215-232，dispose 清理 :405 |
| 2 | 锚点解析 `_resolveWorkViewAnchorNode()`：只信 `isReviewRecommended`，取 `reviewUrgencyScore` 最高；无推荐 → null（诚实降级入口） | :582 |
| 3 | 聚焦调度 `_scheduleWorkViewFocus()`：250ms 轮询等入场编排（相机动画/构建回放/布局收敛）落地后执行；回放未完等回放结束（回放完成会清 spotlight，聚焦必须在其后）；failsafe 40 拍 | :607，由 `_applyGraphData` 仅在非保视野（首次进图）时挂载 :887 |
| 4 | 视野档位裁决 `_countVisibleNodes()`（屏幕投影+48px 光晕容差计数）+ `_workViewScaleFor()`（取「可见 ≤20」的**最宽档**，邻域上下文最多；全档超限取最近档兜底） | :643/:667 |
| 5 | 聚焦执行 `_focusWorkView()`：精确档位落位相机（与 `_focusOnNode` 分离——后者 `max(当前,目标)` 只进不退，无法保证 ≤20 验收语义）+ 复用既有 spotlight 邻域高亮（`_spotlightSetFor`，:3120-3126 地基） | :688 |
| 6 | chip 点击直达复习流 `_startReviewFromWorkViewChip()` → 既有 `_startReviewForNode()`（reviewUrgencyReason→focusPrompt/chatMode 理由链 :917-923 原样复用；`/chat` 既有路由带 prompt/chat_mode/target_node_id） | :760 |
| 7 | 唯一 chip 挂载：`SemanticPill`（design 体系 pill owner，PillTone.brand+icon，DS 令牌面零新造），`ValueKey('galaxy_work_view_chip')`，挂 SafeArea stack 底部（FAB 上方，bottom:92）；构建期数据源 `_workViewChipNode` getter 保证已处理/目标世界模式/节点消失/推荐撤回 → 不挂（§4.1.4 ≤1 名额由「单 widget + 单数据源」结构性保证） | :3432-3456，getter :747 |
| 8 | 布局优化协同：异步布局优化落位后，若用户未接管相机（`_noteInteraction` 打标 :1425），按最终布局重定焦工作视野，防邻域被拉出视野圈 | `_recentreWorkViewCamera` :720，挂 `_scheduleLayoutOptimization` :2355 |
| 9 | l10n 尾部连续块双语：`galaxyWorkViewNextTouch`（zh「下一个建议碰：{name}」/ en "Next up: {name}"）；生成产物以最小 diff 手工落位（见 ⑤-6） | `app_zh.arb`/`app_en.arb` 尾部块 + 3 个生成文件尾部 |
| 10 | 验收测试 `galaxy_work_view_test.dart`（新文件，4 例，见 §验收） | `mobile/test/features/galaxy/widget/` |

## 验收对照（A-SPEC #10 验收条款 → 测试证据）

| 条款 | 断言 | 结果 |
|---|---|---|
| 进图默认视野节点 ≤20 | 40 节点图（8×5 网格，间距 110），等入场编排+聚焦落地后读 `StarMapPainter.camera/positions` 实测投影计数 ≤20；且 `spotlightAnchorId == 推荐锚点`、chip 在屏 | PASS（曾 FAIL=30，根因档位表缺近档，补 1.25/1.6/2.0 后过；详 ④） |
| 推荐 chip 同屏 ≤1 | `find.byKey(chip)` findsOneWidget **且** `find.textContaining('下一个建议碰')` findsOneWidget（文案级唯一性，非仅组件级） | PASS |
| chip 点击直达复习流 | GoRouter 挂 `/chat` 捕获：`target_node_id=推荐节点`、`chat_mode=error_diagnosis`（recent_errors 理由链）、prompt 含节点名 | PASS |
| 无目标诚实降级 | 全图无 `is_review_recommended` → chip findsNothing、无推荐文案、`spotlightAnchorId` 为 null（不伪挂聚焦、不造默认值） | PASS |

测试运行：`galaxy_work_view_test.dart` 4/4（连跑 2 次稳定）+ 与 `galaxy_screen_test.dart` 合批 15/15（HEAVY 门禁：运行前 `ps` 查 HEAVY 进程=0、swap 空闲 1564M≥1.2G、load 3.5<8）。

## 回归（对比法）

- `galaxy_screen_test.dart` **11/11 全过**（含 SPEC-C 错误人话 3 例、加载/选择/缩放/mastery 色 8 项）——触碰面零新增失败。
- 同域毗邻件：`galaxy_first_load_empty_state_test` + `galaxy_empty_state_screen_test`（4/4）、`galaxy_node_preview_card_test`（2/2）、`error_card_galaxy_echo_test`（4/4）全过。
- 设计守卫（触碰面）：`check_dl_spec_ratchet.py` PASS（曾报 `galaxy_screen offLadderDuration 23>21(+2)`——新聚焦时长 520ms/轮询 240ms 不在 A2.1 梯内，已改 500ms/250ms 梯内值，复跑 PASS）；`check_ux_component_convention.py` PASS（rawChip=16/16，SemanticPill 非 raw）；`check_l10n_regen_parity.py` OK；`check_i18n_coverage.py` PASS。

## ③ 冲突面声明

| 相邻卡 | 触碰面 | 冲突判定 |
|---|---|---|
| wt193（backend loguru exc_info） | backend | 无交集（本卡仅 mobile + l10n + mobile test） |
| wt194（纯研究） | docs | 无交集 |
| wt196（backend 旅程测试） | backend | 无交集 |
| l10n（全舰队共享） | `app_zh.arb`/`app_en.arb` **尾部连续块**（galaxyErrorHuman* 之后追加，各 +9 行）+ 3 个生成文件**尾部**（各 +5/+5/+6 行，最小 diff 无格式抖动） | 合入窗口若他卡同帧追加尾部块，按行序顺延即可；生成文件若他卡先合入，主会话重跑 `flutter gen-l10n` 会重新格式化——届时以 gen-l10n 输出为准即可，我的手工最小化只是为了让**本卡 patch** 不携带 500 行格式噪音 |
| galaxy_screen.dart | 本卡独占（wt178 已合入基线，行号已按当前 HEAD 重扫） | 无并发冲突 |

## ④ 诚实申报（限制与取舍）

1. **超密图兜底**：若优化后布局仍密到 2.0 档（视野世界 400×300）可见节点 >20，档位表穷尽后取最近档兜底——验收语义在极端密度下可能不成立（spotlight 仍高亮真邻域）。本次验收图 40 节点实测 12-20 节点视野，余量充足；超密图属 D5 大卡 LOD/聚合范畴。
2. **refresh 不重算**：pull-to-refresh（preserveCamera 路径）不重新调度聚焦/不换 chip 目标；若服务端撤回推荐，chip 经构建期 getter 诚实隐藏，但不会自动换新目标（需重进）。属最小切片有意收敛。
3. **chip 不设 dismiss**：点击即视为已处理（`_workViewChipHandled`），返回星图不再复现；未点击则持续在屏（推荐仍有效时的诚实呈现）。无「叉掉」交互——D5 大卡再评估。
4. **1.6/2.0 档超出 `_focusOnNode` 既有 1.25 上限**：为兜住 ≤20 验收必须引入；上限仍低于相机 maxScale(2.5)。属新档位登记，非偷偷扩权。
5. **回放期间聚焦延后**：首次进图有构建回放时，工作视野聚焦等回放结束才执行（回放完成会清 spotlight）；大图回放期 chip/聚焦出现较晚——与现有回放体验一致，未改回放本身。
6. **生成文件手工最小化**：本机 gen-l10n 工具链带新式 trailing-comma 格式化，会使 3 个生成文件产生 ~500 行纯格式 diff；为控冲突面改为手工落位（+16 行），`check_l10n_regen_parity` 复验 OK。主会话后续任何人重跑 gen-l10n 都会得到等价超集，无正确性风险。
7. **本 worktree 曾缺 `mobile/lib/gen/`**（gitignore 产物）：已按硬规则在本 worktree 执行 `make proto-gen`（host toolchain 回退路径）再跑测试；gen/ 不入 patch。

## ⑤ 收工核查

- [x] 交付物仅 `v3-output/SPEC-J/REPORT.md` + `changes.patch`；零凭据；**未 commit / 未 push**
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean（仅 3 个生成文件的单文件粒度 `git checkout --` 还原自产格式噪音）
- [x] 改动全部在 worktree 内：galaxy_screen.dart（+245 净增）、l10n 5 文件（+34/-2）、新测试文件 1 个
- [x] 验收 4 条全过；回归 galaxy 域 21 例全过零新增；设计守卫 4 项 PASS
- [x] HEAVY 纪律：flutter 测试串行（--concurrency=1）、定向测试不宽扫、运行前后无模拟器/Gradle/浏览器进程；未动 /tmp 驻留（探针文件已删）
- [x] 清理：`mobile/build`、`.dart_tool` 未产生/已清（见下）、无独立端口进程
- [x] 资源复检：测试后无遗留 flutter_tester/gradle 进程

## 附：关键文件清单

- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`（实现主体）
- `mobile/lib/l10n/app_zh.arb` / `app_en.arb` / `app_localizations{,_en,_zh}.dart`（l10n 尾部块）
- `mobile/test/features/galaxy/widget/galaxy_work_view_test.dart`（验收测试，新）
- `v3-output/SPEC-J/changes.patch`（全量 diff）
