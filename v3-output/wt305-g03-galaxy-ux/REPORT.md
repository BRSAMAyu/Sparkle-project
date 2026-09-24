# wt305-g03-galaxy-ux REPORT — G-03 Galaxy Goal-focused UX 重设计

- **状态**: READY_FOR_REVIEW
- **基线**: `deabc1a1` 后代、开工 HEAD `61efb379`；**交付 SHA**: `5692014f`（分支 `wt305-g03-galaxy-ux`，本地 commit 未 push）
- **补丁**: `v3-output/wt305-g03-galaxy-ux/changes.patch`（8 files, +578/−190）
- **Lock**: mobile-galaxy（presentation/交互层）；wt304(J-08) 写入链（galaxy_repository/enhanced_galaxy_repository/galaxy_provider）零接触 ✓

## ① 痛点清单（自审，file:line 以开工 HEAD 为准）

| # | 痛点 | 实证 |
|---|---|---|
| P1 | **焦点不随相机（挂账）**：所有视口移动路径（PanCommand/ZoomCommand :1434-1456、键盘平移缩放 :1404-1429、fling tick :1794-1816）都不更新 `_spotlightAnchorId/_spotlightNodeIds`（:187-188）——平移后锚要么钉在屏外旧节点、要么全图无锚；SPEC-J 工作视野只在进图聚一次，`_noteInteraction`(:1674) 置 engaged 后再无引导 → tech demo 漂泊感 | galaxy_screen.dart |
| P2 | **状态面自成一派（挂账形制）**：`_StatusPanel`(:4108-4252) 无 Semantics liveRegion 整块语义；动作按钮用裸 `FilledButton`，逸出 U-01「按钮 owner 唯一为 SparkleButton」owner 表 | galaxy_screen.dart |
| P3 | **详情触达两跳半**：单点节点要等 420ms 装饰脉冲走完（`:321-324` duration 420ms；`:1607-1622` completed 才 `_openNodeDetailSheet`）→ 面板加载期只有 220px 裸 spinner（sheet :1371-1379），已知节点名不同步展示。触达成本 = 装饰动画 + 网络往返两段纯等待 | galaxy_screen.dart + node_detail_sheet.dart |
| P4 | **en 占位文案 65 条（挂账）**：`galaxyA11y*/Control*/Error*/GraphRag*/Importance*/Overview*/Perf*/Search*/Sector*/Simulation*/OfflineMode/UsingCache/LoadFailed` 的 en 值全是 key 名照抄（如 "Galaxy A11y Action Start Learning"），zh 为真文案 | app_en.arb |
| P5 | 卡面 Work-1「默认当前 Goal 子图 / 节点详情 why/来源/next step」、Work-2 前半「Review now/controls 重叠」：**已在航外由更早卡覆盖**——SPEC-J 工作视野（进图自动聚焦推荐锚+推荐 chip，本树 :611-794）、详情面板 _FocusReasonSection(why)/_SourceMaterialsSection(来源)/动作按钮区(next step)、推荐 chip 经 §4.1.4 单承载不重叠。本卡未重做，只在 P1-P4 补差额 | 见 ② |

## ② 落地项 / 未做项

| 项 | 状态 | 说明 |
|---|---|---|
| a) 焦点随相机 | ✅ | `GalaxyCameraFocus.resolveNearestNodeId` 纯函数（galaxy_camera.dart）+ 屏内 `_applyCameraAnchoredFocus()`（galaxy_screen.dart，`_spotlightSetFor` 后），挂进 5 条用户驱动相机路径（pan/zoom/键盘 pan/键盘 zoom/fling tick）的既有 setState 内，与相机同帧落位零双重建。守约：目标世界模式/_isBuildAnimating/拖节点/预览卡/点按反馈期全跳过；显式选中在视口内不被冲（preferredId）；视口空→诚实无锚；程序化相机动画（聚焦/总览适配）不挂——它们有明确语义目标，中途重定锚只会闪烁 |
| b) 状态面对齐 | ✅ | `_StatusPanel`：+Semantics(container+liveRegion, label=title, value=message)（与 EmptyState 同构）；FilledButton→SparkleButton（owner 归位）；星云 orb 保留——GALAXY.md「保留暗色宇宙作为品牌视觉锤」，形制对齐≠组件整体替换 |
| c) 详情触达减一跳 | ✅ | `_startTapFeedback`：面板随点按立即打开（`_pendingNavigationNodeId` 不再置位，动画完成回调只清理、不二次开面板；脉冲在面板下方播完作视觉延续）；sheet 加载期渲染 `_SheetHeader`（handle+图标+节点名，与 _HistoryContent 头部同形制的唯一实现点）+ 收窄进度区(120px)——首帧回答「点的是哪个节点」 |
| d) en 占位清理 | ✅ | 65 条 key-mirror 值全部替换为与 zh 语义一致的真英文；`app_localizations_en.dart` 同步逐字更新（等价 gen-l10n 产物、零 format churn）；arb 双语 key/占位符 parity 校验通过 |
| 测试 | ✅ | 见 ③ |
| 卡面 A/B 5 screenshots / 跨端 simulator 实测 | ❌ 未做 | 需模拟器（HEAVY 门禁 + 本轮 swap 全程 <1.2G 直至测试窗口才开门，额度给了定向测试）；属 G-05 终验范畴，交接待验收 |

## ③ 测试与验证（全绿）

- 单元（galaxy_camera_test.dart）：resolver 5 用例——最近锚/优选保留/出视口重定/视口空 null/空 positions null（+既有 2 用例）→ **7/7**
- widget（node_detail_sheet_test.dart）：+1「加载期节点身份可见+spinner 在场+动作区不出现」（never-completing repo fake 固化 loading 形态）→ **4/4**
- widget（galaxy_empty_state_screen_test.dart）：+1 错误态（星图加载失败/重试/SparkleButton owner）+1 真实屏拖拽重定锚（三稳定坐标节点铺开，缓速拖拽 24×30px<420px/s fling 阈值，断言 `debugSpotlightAnchorId: null→'node-a'`）→ **4/4**
- widget（galaxy_screen_semantics_test.dart 回归）：**4/4**（真实屏语义链未受 a/b 影响）
- 合计定向 19 测试；单文件单进程错峰跑
- analyze：改动 6 文件仅存 4 条开工前既有 info（galaxy_screen:2004、node_detail_sheet:260、sheet_test:175 的 cascade/discarded_futures，均 HEAD 已在）→ **零新增**
- 守卫：`run_all_rule_guards.sh` **exit 0（83 rules 全过）**（AQ/BG 曾因 worktree 缺 gen 产物失败——已从主仓拷 `backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen`（`cp -RL` 解引用，主仓内 gen 含指向 Sparkle-project 的绝对 symlink）；K/Z 曾因此连带崩溃，拷后自愈）

## ④ 资源峰值

- HEAVY 门口全程排队：swap 774M→1204M 才放行定向测试（本卡无模拟器/Gradle/浏览器）；测试窗口内单文件串行
- 磁盘：gen 拷贝 ~15MB 级；收工清理 mobile/build、.dart_tool、/tmp 探针（见收工记录）
- 无并发 HEAVY 叠加

## ⑤ 交接

- **→ G-04（一致性）**：①galaxy 状态面已归位 SparkleButton owner + liveRegion 语义，动作 owner 表无需再豁免 galaxy 状态面；②galaxy spotlight 语义现在含「相机被动锚」（无选中态的常驻高亮），若 A 线做 glow/spotlight 预算盘点，相机锚占的是原 spotlight 名额、未新增光源；③en arb 65 条已真文案，双语一致性抽检可从 galaxyA11y*/galaxyPerf* 入手
- **→ G-05（终验）**：①本卡无模拟器 A/B 截图，卡面「新用户能解释星图/缩放点击跨端稳定」需真机/模拟器实测补证（建议场景：进图→工作视野聚焦→平移看锚随相机→点节点看面板首帧身份→弱网看加载形态→空图/断网看状态面）；②焦点锚定行为基线见本报告 ③ 的拖拽用例（纯几何、无新状态机，跨端手势行为不受影响——只在既有 pan/zoom 命令后追加一次 O(n) 视口内最近点查询）
- **给主会话**：wt304 合入若动 galaxy_screen.dart（当前其写入链不含该文件），`_applyCameraAnchoredFocus` 与 `_startTapFeedback` 两处改动可能需 rebase 确认

## 收工清理

- [x] mobile/build、.dart_tool 删除（测试后）
- [x] /tmp：wt305-guards*.log、wt305-baseline-check/、wt305_statuspanel.txt 删除
- [x] 无模拟器、无残留进程
- [x] 分支本地 commit `5692014f`，未 push
