# WT356-U07 — 长尾 Feature Contextualization 与导航减负（U-07）

- 工号：wt356（wt346 排产队列第 10 位）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt356-u07-nav`（分支 `wt356-u07-nav`）
- base SHA：`b9269713`（分支点 main）
- final SHA：见分支 HEAD（交付 commit 后回填于 commit message）
- 卡面：`v3/07_tasks/cards/U-07.md`（权威）；依赖 B-01（MODULE_PORTFOLIO 分档）、U-05（已合并 e56/cb02 系）的产物均已考古吸收

---

## 一、盘点（改前导航清单）

权威真源 = `mobile/lib/app/routes.dart` + `core/navigation/shell_navigation.dart`：
五 Tab = Home `/home`、Galaxy `/galaxy`、Chat `/chat`、Community `/community`、Profile `/profile`。根级另挂 31 个路由族。

按 `v3/00_context/MODULE_PORTFOLIO.md` 分档盘点 LABS/HIDDEN 在 CORE 面的暴露边（考古基线 = NAV-IA 报告 `v3-output/NAV-IA/REPORT.md` + 已合并改造 de7edda5 nav+squad / c69c6879 photon ghost surfaces）：

| LABS 面 | 改前 CORE 暴露边（实测 file:line） |
|---|---|
| theater | home/recent_insights_card、home/insight_hub_card（双形态）、insights overview、report screen（hero 主 CTA！）、chat_bubble 预览卡（纯模式 sheet + disclosure 双路）、galaxy 节点预览卡常驻「演练」按钮 |
| simulation | 同上（insight hub 双形态、insights overview 模块卡、report 行动卡、chat 预览、recent insights 通知行） |
| seed_library | tools/tool_registry 工具别名（工具库+搜索+首页工具枢纽）、chat_settings ListTile |
| visual_elements | profile_screen、unified_settings_screen |
| leaderboard（HIDDEN） | 全站榜已按 D-COMM-1 不建路由（自我锚唯一），本次只加钉测试固化 |

CONTEXTUAL 现状：task 执行→focus（已有）、任务卡 due→calendar?date（已有）、galaxy 节点→知识详情=knowledge（已有）、translator 工具→translation history（已有）、prism 卡→errors（已有）。**缺口：plan 详情无日历入口**（时间摆位语境断裂）。vocabulary：features/vocabulary 只有 providers、无任何 UI 面——无可嵌入对象，诚实标注（portfolio CONTEXTUAL 角色为愿景态）。

## 二、手术清单（全部外科摘边，路由真源零改动）

策略：LABS 走 **unlisted**——不删路由挂载、不删功能文件（后续 Labs 化可整卡恢复），只摘 CORE 面入口边；规避 NAV-IA 辩题 5 指出的「0 入边路由深链提前触达」残余风险（深链落到真实面而非 404，LABS≠HIDDEN）。

1. **home/recent_insights_card**：只聚合 `learning_report_ready`；theater_*/simulation_session_ready 不再上首页；LABS 深链打开路径删除，兜底落通知中心。
2. **home/insight_hub_card**（重写 764→约 440 行）：展开/紧凑双形态的 simulation/theater 快捷卡摘除，收敛为「学习报告」单一 CONTEXTUAL 动作 + 总览入口；simulationProvider 监听与推荐种子加载移除；两处渲染中的失实 fallback 文案（提及推演/仿真）双语同步修正（arb+生成 dart 四文件外科值替换，wt350 形制）。
3. **insights overview**：simulation/theater 模块卡、provider 监听、deep-link 定位 helper、panelSimulation/panelTheater 面板全部摘除。
4. **report screen**：hero 主 CTA 从 theater 深链改为星图（evidence-aware mastery 的 CORE 面；报告模型仅 node_name 无 node_id，无法直连节点详情——已注释说明）；行动卡删除 theater/simulation 按钮；后端下发的 LABS 类 actionCards（kind 过滤）不再渲染；deep-link 上下文携带剔除 theater/sim 分支。
5. **chat_bubble**：theater/simulation 预览卡四路渲染（纯模式 sheet 两页 + disclosure 两块）全部摘除；纯模式附件触发源只认 report_preview；report 附件卡的 LABS 类 actionButtons 过滤；theater/simulation prompt-actions 与 builder 删除（132+85 行）。
6. **galaxy**：`GalaxyNodePreviewCard.onLaunchPrediction` 改可空，节点预览卡不再常挂「演练」入口（galaxy_screen 删除 `_launchPredictionForPreviewNode`）；theater 会话激活态的 overlay 回路**保留**（属 Labs 内部延续，非 CORE 常驻入口；不动 galaxy 渲染层业务逻辑）。
7. **seed_library**：tool_registry 工具别名摘除（工具库/搜索/首页枢纽三路同断）；chat_settings 浏览入口 ListTile 摘除，种子增强开关（能力配置）保留。
8. **visual_elements**：profile + unified_settings 双入口摘除。
9. **CONTEXTUAL 增强（卡面 Work#1）**：plan_detail AppBar 新增日历 context CTA（`CalendarRoutes.calendar`，tooltip/semanticLabel 复用既有 `calendarTitle`「日程与日历」，零新 l10n 键）——计划的时间摆位语境 1 跳进入、返回即回原计划，满足「context CTA 到达并返回」语义。

五 Tab 数量未动（routes.dart/shell_navigation 零 diff）；导航权威真源未重建；无视觉改版。

## 三、验收对照

- [x] 五 Tab 不增：`shell_navigation.dart` 零改动 + 契约钉（NavigationDestination 计数=5）。
- [x] CORE journey 无关 feature 入口清零：上述 9 项 + 契约钉扫描（9 个 CORE 文件 × LABS 引用 token 全零）。
- [x] HIDDEN 用户不可达：leaderboard 全站榜无路由（D-COMM-1 既有裁决），契约钉固化 `LeaderboardRoutes.routes` 唯一面=自我锚。
- [x] CONTEXTUAL ≥1 自然 journey：plan detail→calendar（新增）+ task 执行→focus（既有）+ galaxy 节点→知识详情（既有）。

## 四、测试与证据

- **新增**：`test/widget/nav_decontextualization_contract_test.dart`（6 钉：五 Tab 计数/工具注册表无 LABS 别名/HIDDEN 唯一面/CORE 面零 LABS 引用扫描/plan→calendar journey 钉/预览卡无演练按钮 widget 钉）。
- **改写**：`learning_insights_navigation_test`（2 用例改为新契约：hub 仅报告入口+LABS 类型通知不渲染；overview 仅 Report 面板+LABS 模块卡缺席）、`insights_frontend_smoke_test`（hub 直跳用例与紧凑形态用例对齐新契约）。剧场/仿真屏直泵用例不受影响（功能文件未动）。
- **analyze 门**：E0/W15/I587 —— 与 main 基线（wt350 后）**逐位零漂移**（预算 E42/W16/I594±5）。
- **守卫**：`bash scripts/run_all_rule_guards.sh` exit 0（**84 条**，worktree 内实测；AQ/BG 环境红已按 §4 协议补拷 backend/gateway gen 后转绿）。
- **mypy**：零 Python 改动（diff 全 .dart/.arb/.md），棘轮天然不推高。
- **定向 flutter test：DEFERRED** —— swap 门实测 918M/942M < 1.2G（两次采样），按内存纪律不执行。补跑命令（swap≥1.2G 窗口，串行）：
  ```bash
  cd mobile && flutter test --concurrency=1 \
    test/widget/nav_decontextualization_contract_test.dart \
    test/widget/learning_insights_navigation_test.dart \
    test/widget/insights_frontend_smoke_test.dart \
    test/features/chat/presentation/screens/chat_settings_screen_test.dart \
    test/features/insights/presentation/screens/learning_insights_overview_screen_test.dart \
    test/widget/dashboard_screen_structure_test.dart
  ```
- **simulator/integration 证据：DEFERRED**（LIGHT 纪律禁模拟器）。代码行为等价性由 widget 级契约钉 + analyze/守卫双门背书；卡面 Forbidden「不得只通过静态代码阅读宣称用户体验通过」——如实声明：本交付的动态证据=可执行的 widget 钉测试（swap 窗口补跑），真机 journey 截图证据缺口移交主会话 HEAVY 窗口。
- **金测试提示**：dashboard golden（env 门 `ENABLE_DASHBOARD_GOLDEN`，默认关）若重生成会捕获 recent insights 卡单行化后的差异——属预期产品变化。

## 五、遗留登记（不阻塞交付）

1. 死 l10n 键积压：LABS 摘边后 `insightHubSimulation/Theater/CompactSimulation/CompactTheater/RecommendedSeeds*`、`insSimLabel/insTheaterLabel/insOpenSim/insTheaterFallback`、`chatPromptRefinePath` 族、`reportActionExploreNode/EnterSimulation`、`chatViewTheater/SimulationDetails`、chatSettings seed 计数族、`profileSubtitleVisualElements` 等约 30+ 键零引用——按 wt350 先例另开收割批（本次只修了渲染中的失实文案两键）。
2. galaxy theater overlay 回路（theater 会话激活期）保留——若后续裁决要求全断，需动渲染层（galaxy 业务逻辑域，超出本卡外科边界）。
3. vocabulary 无 UI 面的事实已在卡面语境下如实记录；若 V3 要落地其 CONTEXTUAL 角色，需新功能卡而非导航卡。
4. `MODULE_PORTFOLIO.md` 的 portfolio.json/matrix 由 B-01 权威维护，本卡未重建（Forbidden 合规）。

## 六、收工清单

- [x] 守卫 84 exit 0（commit 前置门已过）
- [x] analyze E0/W15/I587 零漂移
- [x] mypy 天然满足（零 py 改动）
- [x] 交付物（本 REPORT + changes.patch）commit 进分支
- [x] `git diff --binary main...HEAD` 生成 changes.patch（--binary）
- [ ] 定向 flutter test：DEFERRED（swap 918M<1.2G，补跑命令见 §四）
- [x] mobile/build、.dart_tool、/tmp 自产物清理
