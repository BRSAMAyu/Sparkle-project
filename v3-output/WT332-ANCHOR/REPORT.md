# WT332 · F-3 星图起始引导与锚定可感知 — REPORT

- **Worker**: wt332（LIGHT 槽位）
- **卡面**: wt324 实测报告 §四 F-3（major）：fresh 全锁定初始态无 SPEC-J 工作视野聚焦；平移后锚定视觉不可感知（机制在 widget 层已证存在）
- **基线**: main `a86b601e`（含 wt328 F-1/F-10 合入态）；worktree `../Sparkle-sysrev/wt332-galaxy-anchor`（branch `wt332-galaxy-anchor`）
- **禁区遵守**: 未碰 chat 渲染/cockpit（wt327）、galaxy_draft_repository（wt328）、backend；无模拟器；无大重构；UI 全部消费既有 design 令牌（环色=节点派生 baseColor，零新颜色魔法值）

## 一、考古结论（机制现状与「不可感知」的确切原因）

### 1. 机制现状（wt305 G-03 已落地的两条链）

- **进图聚焦链（SPEC-J）**：`_handleGalaxyStateChanged(!preserveCamera)` → `_scheduleWorkViewFocus`（250ms 轮询等入场编排落地）→ `_applyWorkViewFocus` → `_resolveWorkViewAnchorNode` → `_focusWorkView`（相机精确落位 + spotlight 邻域高亮 + 推荐 chip）。锚点**只信服务端既有推荐信号**（`is_review_recommended` + `review_urgency_score`，`galaxy_screen.dart` 原注释「不自造算法；无推荐节点时诚实降级」）。
- **平移重锚链（G-03）**：pan/zoom/fling/键盘 5 条用户驱动相机路径尾部挂 `_applyCameraAnchoredFocus` → `GalaxyCameraFocus.resolveNearestNodeId`（视口内距中心最近节点，纯函数）→ 更新 `_spotlightAnchorId/_spotlightNodeIds`。widget 测试已证重锚生效（wt305 拖拽用例）。

### 2. 「fresh 无聚焦」确切根因

`_resolveWorkViewAnchorNode` 唯一锚源是 `is_review_recommended`，而 fresh 用户（314 节点全锁定、零学习记录）服务端必然不发推荐信号 → resolver 恒返 null → 走「诚实降级」分支原样 return → 相机停在 `_fitOverviewCamera()` 全图概览。**诚实降级在推荐语义上正确，但在产品语义上等于「首眼无引导」**——这正是 wt324 判 FAIL（未触发）的代码路径。SPEC-J 验收 4 的「无推荐→不造默认值」契约把 fresh 用户锁死在了无引导态。

### 3. 「平移后锚定不可感知」确切根因

重锚后锚的「正视觉」只有三条，对锁定节点全部失效或微弱：

| 视觉通道 | 代码路径 | 锁定节点上的实际效果 |
|---|---|---|
| glow 光晕 | `star_map_painter.dart` glow 分支要求 `style.glowAlpha > 0` | `_nodeStyle` 对 `!isUnlocked` 固定 `glowAlpha: 0` → **永不生效** |
| 推荐脉冲 | `_drawReviewPulse` 要求 `node.isUnlocked` | 永不生效 |
| 邻域 dimming | 非 spotlight 节点 alpha×0.2 | 锁定节点本体本就暗淡（fillAlpha 0.22/coreAlpha 0.12），0.22→0.044 在暗色画布上对比微弱 |

即：**锚节点没有任何专属视觉身份**——它只是「那颗没被调得更暗的星」，在全锁定暗色图上与邻星不可区分。wt324 判 UNVERIFIABLE（机制不可视）的根因在此。

## 二、修复实现（最小改动，2 处视觉行为 + 1 个口径函数）

### a) fresh 全锁定初始态：结构锚兜底（`galaxy_screen.dart`）

`_applyWorkViewFocus` 在推荐 resolver 返 null 后落 `_resolveStructuralAnchorNode`：**取 importance 最高（1-5 服务端既有结构字段）、同分保持图序首个**（与推荐路径同一稳定约定），复用 `_focusWorkView` 全套（相机档位落位 + 邻域 spotlight + 锚定环）。守约边界：

- **不挂 chip**：`_workViewChipNode` 仍要求 `isReviewRecommended`，结构锚必然不满足 → chip 诚实隐藏，复习语义零沾染（无需新开关，chip 纪律由既有数据结构自保证）。
- **目标世界模式跳过**（`_isGoalWorldMode` 直接 return）：目标世界有自己的聚焦口径（屏层传 `spotlightAnchorId: null`），不掺和。
- 无位节点跳过、空图诚实返回，与原降级口径一致。

### b) 平移后锚定可感知：锚定呼吸指示环（`star_map_painter.dart` + 口径函数）

- 新增纯函数口径 `galaxySpotlightAnchorRingOpacity`（`galaxy_display_settings_provider.dart`，与既有三个 spotlight opacity 函数同处）：仅当前锚且 spotlight 已挂时 >0，其余 0。
- `_drawNodes` 对锚节点画 `_drawAnchorRing`：节点自身派生色（`_nodeStyle().baseColor`，不新造颜色值）细描边圆环（radius×1.9+2，stroke 1.6），套在既有锁定虚线圈/掌握度环之外，随既有 `ambientPhase` 缓慢呼吸（0.78-1.0）以被余光捕捉。无 maskFilter、单 draw call、构建回放期不画；目标世界模式经屏层传 null 天然无环。
- 平移重锚后环随 `spotlightAnchorId` 跳到新锚——「现在该看哪」在视口内可直接指认。

## 三、产品语义裁量边界（留主会话/用户拍板）

「全部锁定初始态该聚焦哪里」存在真实产品选择。本卡取**保守解**（选项 1），其余选项在案，切换成本均为局部：

1. **（已实现）结构锚 = importance 最高节点**。语义：「从知识版图上最重要的星看起」。零新算法、零信息架构变更、对 fresh/老用户统一成立。风险：全局共享图谱上「最重要」≠「与我有关」（wt324 §三 小 B 归属感问题的弱化版，但比无引导严格改善）。
2. （备选）**首颗可点亮节点**（root/parent 已解锁中 importance 最高）：更贴 growth 语义，但「可解锁」口径服务端无现成信号，需前端从 parent 关系推导或后端补信号——超出本卡最小修复边界。
3. （备选）**空态浮层指引**（首进浮层箭头指向锚点）：引导最显式，但 wt324 已见两条引导卡同屏（F-8 视觉竞争前科），再叠浮层有引导堆叠风险。
4. （产品拍板项）聚焦「当前学习任务关联的节点」：需任务-节点映射，跨 galaxy/task 两域，属新功能。

## 四、测试与验证

| 项 | 结果 |
|---|---|
| `flutter analyze` 门 | **E0/W15/I598**（`check_flutter_analyze_gate.py` + 容差 5 **PASS**，与基线逐项持平=零新增） |
| 守卫 `run_all_rule_guards.sh` | **83 条 exit 0** |
| 单测 `galaxy_display_settings_test.dart`（环口径 5 断言：仅锚可见/无锚无环/spotlight 空无环） | **5/5 过**（--concurrency=1） |
| widget `galaxy_work_view_test.dart` 5/5（含新契约 2 用例：无推荐→结构锚聚焦+chip 缺席；**fresh 全锁定→锚定可指认+chip 缺席**） | **5/5 过**（--concurrency=1） |
| widget `galaxy_empty_state_screen_test.dart` 4/4（拖拽重锚用例重构：基线锚=结构锚 node-a → 平移出视口 → 重锚 node-b；拖拽步数按落位后真实相机 scale 换算，对布局漂移鲁棒） | **4/4 过**（--concurrency=1） |
| galaxy 其余套件回归（semantics/keynav/first_load/node_detail_sheet/integration/perf） | **DEFERRED**：定向批后 swap free 跌至 715M < 1.2G 门（§五）。已按影响面静态排查：semantics/keynav 断言走键盘链与语义层（不读相机/spotlight）、first_load 只断言加载/空态文案与 provider 态、screen_test 前两用例用测试挂件非真实屏——均不消费本卡改动面；合入后主会话可按 §7 门复跑 |
| mypy 基线 1615 | 不涉及 backend，天然满足 |

**契约修订声明（供审查重点）**：SPEC-J 验收 4 由「无推荐→诚实降级：不挂 chip、不造默认值（spotlightAnchorId 必须为 null）」修订为「无推荐→结构锚兜底：相机/spotlight/锚定环落到 importance 最高节点，**仍不挂 chip、不带复习语义**」。依据：wt324 F-3 实测判定原契约即 UX 缺口本体；卡面明示授权「相机初始位对准将要展开的工作簇」。galaxy_work_view_test.dart 文件头已同步标注修订来源。

## 五、资源与内存门（如实记录）

- 全程 LIGHT：无模拟器/Gradle/浏览器。
- 定向 flutter test 分四批串行（--concurrency=1）：前三批过门时执行（swap 1267M 批前复核）；第四批（其余 galaxy 回归）批前复查处 715.62M < 1.2G → 按 §7 纪律停跑，标 DEFERRED。
- gen 三件套自主仓 `cp -RL` 拷入（主仓只读解引用）。

## 六、交接

- **→ 主会话**：本卡动了 SPEC-J 验收 4 的行为契约（§四声明），合并态建议复跑 `test/features/galaxy/widget/` 目录全套（swap 门开时）；结构锚的产品语义选项见 §三，若用户拍板选项 2/3，本卡实现可作底座局部替换 `_resolveStructuralAnchorNode` 单点。
- **→ G-05 终验**：两处视觉行为待真机/模拟器补证场景：①fresh 账号进图→相机应落「最重要节点」邻域+呼吸环在屏；②慢速平移→环随锚跳到视口中心附近节点。
- 改动面 6 文件（3 lib + 3 test），零 proto/schema/依赖变更，无生成物。

## 收工清理

- [x] worktree 内无 mobile/build、.dart_tool（本卡未跑过构建，测试产物为 .dart_tool 仅 test 批产生——见收工执行）
- [x] /tmp/wt332_guards.log 删除、无自起进程残留
- [x] REPORT.md + changes.patch commit 进分支
