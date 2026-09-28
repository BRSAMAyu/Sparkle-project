# V4-F05 一审 receipt（wtF05R1）

- **审查者**：wtF05R1（独立会话，未参与 F05 实现）
- **日期**：2026-09-28
- **对象**：commit `7918a683`（分支 `agent/v4/f05`，base `8458d3c7`）
- **方法**：只读审查 + 独立复跑 + 探针实测；产物除本 receipt 外零落盘（复采集写 `/tmp`，探针测试用后即删）
- **总裁决**：**PASS_WITH_CHALLENGES**（普通风险单审通过；2 项非阻塞挑战 R1-C1a / R1-C3a 随 receipt 登记，不阻塞销账）

---

## 1. 九项审查靶逐项

### 1.1 四档切换状态流（通过）

- `StylePreviewFlowStep` 四步封闭枚举 + `StylePreviewFlowFrame.of` 穷尽 switch（seed 文件 L53-79）——流步投影**可失败性成立**：新增枚举值不改 switch 即编译红；文案一律取 F03 冻结表 `kExperienceCopyTable` 既有键（`state.syncing`/`task.committed`/`memory.saved`/`err.version_conflict`，四键在 `experience_feedback_adapter.dart` L41/44/47/53 亲验存在）。
- **「同一状态流」跨档语义恒等机检自证：亲验通过且超范围**。任务要求重算 2 面×4 档，实算 **6 组（5 单面 + sheet）× 4 档**，每组 4 份语义 dump sha256 收敛为单值且与 run_manifest.json 逐组一致：

| 组 | 恒等 sha256（四档同值） | 与 manifest 一致 |
|---|---|---|
| home | `7878e8d3007215a0…` | ✓ |
| stuckSheet | `d992ed61b60aea5d…` | ✓ |
| memory | `f2a5dd2cc7ed17ca…` | ✓ |
| longAnswer | `f67f55c768a8cf44…` | ✓ |
| starMap | `79852b260492ab47…` | ✓ |
| sheet | `07cc788b6798edb8…` | ✓ |

- 整页四档语义 dump 各异（页头含「像素扩展已挂载/未挂载」状态文本，classic 与三候选本就该不同）——口径自洽。
- 6 个 PNG 抽检 sha256 与 manifest 逐一相符（home_classic/home_quiet/starMap_dusk/longAnswer_paperDay/page_dusk/sheet_quiet）。

### 1.2 真实表面组件（通过）

- 五面 import 目标 6 个生产文件逐一存在（today_cockpit_card/task_stuck_card/memory_evidence_badge/sparkle_markdown/sector_background_painter/galaxy_node_preview_card），测试以 `find.byType` 对生产类断言——非替身非重绘。首页面经真实 `todayCockpitProvider.overrideWithValue(seedVm)` 钉 seed（非 mock 替换组件本体）；卡住 sheet 走真实 `showModalBottomSheet`（faces_test 开/关断言，sheet 内 + 面内 2 枚 TaskStuckCard 计数断言）。
- **冻结 seed 可复现性：全量 56 文件（28 PNG + 28 txt）独立重采 byte-identical**（`cmp` 逐字节，identical=56 png_diff=0 txt_diff=0）——比 limitations 自报的「页面级可能差一帧」更强，实测连页面级也逐字节复现。

### 1.3 flag 默认 false 红线（通过）

- `app_constants.dart` +5 行：`static bool enableStylePreview = false`（带 PROPOSED 注释）；反例测试钉 flag 关 → 入口零节点（tile 与标题文本 findsNothing）；正例 flag 开可进页。
- 入口唯一落点：`profile_screen.dart` 设置区尾部消费 `const StylePreviewEntry()`（+5 行）；gate 判定不复制（profile_screen 只消费组件）。
- 页头「PROPOSED · 未批准」常显；`TOKENS.proposal.json` 不在 diff（status 未被改写）。

### 1.4 C1 静默空白（见 §3 逐判）

### 1.5 C2 流步重挂（见 §3 逐判）

### 1.6 C3/C4/C5（见 §3 逐判）

### 1.7 CH-4 守门（通过）

- 三个新文件 grep `StreamSubscription|WebSocket|Channel|http|dio|\.listen\(|Timer|fetch|Future.delayed` = **零命中**；seed 只读 import 冻结文案表（const Map 消费，不接线 core/experience 运行时）；`core/experience/` diff 为空；五 Tab 路由合同/WS 通道文件不在 diff。「preview 面零事件流订阅/零网络/零新增投递路径」声明成立。

### 1.8 复跑（全部复现）

| 命令 | 实跑结果 | 与自报一致 |
|---|---|---|
| `flutter test test/core/design/style_preview/` | 40/40 绿 | ✓ |
| `flutter test test/core/design/` | 200/200 绿 | ✓ |
| `flutter test test/core/navigation/ test/widget/nav_decontextualization_contract_test.dart` | 42/42 绿 | ✓ |
| `flutter analyze --no-pub` | 1 issue = `experience_feedback_adapter_test.dart:315 require_trailing_commas` | ✓（该文件不在 F05 diff，pre-existing 成立；且 main 已由 CI38 `f6de174c` 修复——合并后 analyze 基线归零） |
| 六守卫（UI-TOKENS/SPACING/TYPO/DL-SPEC/I18N/N18） | 全 PASS，棘轮数与 test_results.json 逐一相符（225/275、634/727、1591/1623、232/234、0/0、6/6、69/118） | ✓ |

- **SPACING「真实拦截修正非豁免」核**：守卫脚本不在 F05 diff（非改守卫过关）；终态新文件零半步档（1591 计数与 main 基线不升、cap 1623 未被动）；棘轮脚本自带拦截自测（`NEW FILE … spacingHalfStep=1 → exit 1` 路径在脚本 L262-319）。瞬时红无法事后取证重建，但「修正非豁免」与终态证据一致，采信。
- **范围注记**：worktree 跑全量 `run_all_rule_guards.sh` 有 AQ/BG 红点——定性为**环境性**（gitignored 生成代码未复制进新 worktree，`backend/app/gen/agent/v1/agent_service_pb2.py` 同样不在 main 检出中存在），与 F05 纯 mobile Dart diff 无关；F05 自报口径即六守卫，未虚报全量。

### 1.9 红线（全部零触碰）

`git diff 8458d3c7 7918a683` 亲核：`app/routes.dart`、`design_system.dart`、`tokens_v2/`（含 theme_manager.dart）、`core/experience/` diff 为空；`features/` 仅 `profile_screen.dart` +5 行（卡面授权的入口消费）；RF-06 冲突面（dashboard_screen/compact_status_bar/task_execution_screen）不在 diff；无 .env/proto/迁移/生成文件。全 commit 非证据文件清单 = 3 新产品码 + 2 修改 + 4 测试 + tasks.json 状态位，与自报完全一致，无夹带。tasks.json 置 `IN_PROGRESS/REVIEW_READY/SELF_CHECK_PASS`，未自评 DONE。

## 2. 合并落差（main 已前进）

main（Sparkle-project）自 base `8458d3c7` 前进 9 commit 至 `f9729cc5`（I04 全链 + CI38 + 心跳）。**对 F05 触达路径（core/design/、app_constants.dart、profile_screen.dart、test/core/design/、core/experience/）的 `git diff 8458d3c7 f9729cc5` = 空**——合并零冲突。唯一交联：CI38 修复的正是 F05 analyze 报告中那条 pre-existing info（同文件 L315），合并后该 info 消失，F05 的 analyze 自报对其分支 base 仍准确。

## 3. C1-C5 逐判

### C1（冻结表键 `?? ''` 静默空白）——**SUSTAIN（按预登记口径成立），非阻塞，附加固建议**

探针实测（临时测试文件，已删，不占库）：
1. 拼错键走同一消费路径（`kExperienceCopyTable['task.commited'] ?? ''`）→ **静默空串，零异常**；页面流步行渲染「状态流：」空尾巴。
2. `StylePreviewFaceCard` 的 `if (frame.copy.isNotEmpty)` 渲染守卫使空文案**连节点都不存在**——未来新增流步若拼错键，任何 find.text 断言无从命中，静默逃逸成立。
3. **但现行四键今天并非裸奔**：faces_test 以逐字文案断言钉死四步（`find.text('同步中'/'任务已更新'/'记忆已保存'/'你的设置已更新，需要重新生成')`），现行键今天拼错即红。风险面收窄为「未来新增流步拼错键」——与预登记 C1 的自我限定完全一致（预登记诚实）。
4. fail-loud 替代实测有效：`containsKey` assert 同场景立刻红且报出键名；现行四键 containsKey 全真，assert 化不误伤。
- **裁决**：挑战按预登记口径成立（非阻塞——flag 门控开发者面 + 封闭 switch + 现行键有逐字钉）。**建议（R1-C1a）**：加一条泛化测试遍历 `kStylePreviewFlowSteps` 断言每步 `copy` 非空（一处测试关闭未来逃逸，无需运行时 assert）；转正前落。

### C2（ProviderScope 按流步重挂 vs 不重启 run）——**REJECT（实现正确，挑战不成立）**

独立辨析：验收 2 的「run」= 用户会话/数据 run，非 widget 身份。重挂仅由**流步推进**（ValueKey 以 step 为键）触发——这是 preview 取证语义（Riverpod 覆写集合不可变下的确定性重渲染），且只发生在 flag 门控隐藏页内的面卡；**切主题路径零重挂有测试实证**：探针 `mountedCount==1` + 页面流步 index 跨三档存活 + 探针内部状态存活（switching_test 正例三连断言）。主题切换走 AnimatedBuilder 同 key 重建，ProviderScope element 存活。语义辨析与测试证据一致，无违反验收。

### C3（固定 700ms 两拍泵）——**JUSTIFY（正当），一处数字注记（非阻塞）**

- shimmer 无限性亲验：`TodayCockpitCard` isLoading 分支渲染 `SparkleSkeleton` 族，其 `_controller.repeat()`（sparkle_skeleton.dart L36）+ `Shimmer.fromColors` period 1200ms——`pumpAndSettle` 确实永不落定，固定拍长是**产品真实行为的必然选择**，非测试绕行。
- 成功徽章单次动效亲验：`milestoneMax ?? 650ms`、仅 `forward()`（pixel_state.dart L294-299）≤650ms；星图两组件无 AnimationController。700ms > 全部单次动画，两拍覆盖成立。
- **注记（R1-C3a）**：harness 注释称「主题过渡 280ms」——实查 motion tokens 上限 260ms（theme_manager.dart L1302-1304），MaterialApp 默认主题动画 200ms；数字不精确但方向不变（均 <700ms），结论不受影响，建议顺手改正注释。
- 实证：本审 40 + 27 证据全量重跑零 flake。

### C4（语义恒等仅结构层的口径）——**ACCEPT（预登记口径准确，主张在该口径下成立）**

亲验 dump 格式：仅 `label/value/isButton/rect`，**零颜色字段**；跨四档 byte-identical 同时钉住结构+文案+布局不变量；视觉差量由每面 4 份 PNG 承载（sha256 两两相异已验）。「切主题不改语义结构」在**结构/文案/布局层**是机检为真的强命题；不含颜色/对比度语义的限定（C4 自我登记）必须随主张传播。任何地方去掉该限定引用此自证即为过度主张——本 receipt 采信限定版。

### C5（push 路由不触 routes.dart）——**ACCEPT（正确取舍）**

命名路由必须改 `app/routes.dart`（五 Tab 合同，本卡红线禁触）。`Navigator.push(MaterialPageRoute)` 是红线内的最小实现；代价（深链/路由级测试不可直达）对 flag 门控开发者预览页可接受，且转正路径已在 limitations 写明（届时重走五 Tab 合同评审）。核实入口确实零触 routes.dart。

## 4. CHALLENGED 清单（非阻塞）

| ID | 对象 | 内容 | 处置建议 |
|---|---|---|---|
| R1-C1a | seed `?? ''` | 未来新增流步拼错键静默逃逸（现行四键有逐字钉，今天安全） | 加泛化测试遍历流步断言 copy 非空；转正前落 |
| R1-C3a | harness 注释 | 「主题过渡 280ms」实为 ≤260ms（motion token）/200ms（kThemeAnimationDuration）；不改结论 | 注释顺手修正 |

无阻塞挑战；无停止条件命中（无权限/跨用户/假成功情形）。

## 5. 复跑命令与环境

- 环境：darwin 25.6.0 arm64；Flutter 3.41.3 stable（revision 48c32af034）——与 run_manifest 一致
- `flutter test test/core/design/style_preview/` → 40/40（exit 0）
- `flutter test test/core/design/` → 200/200（exit 0）
- `flutter test test/core/navigation/ test/widget/nav_decontextualization_contract_test.dart` → 42/42（exit 0）
- `flutter analyze --no-pub` → 1 issue（pre-existing，同自报；exit 0）
- 六守卫逐条 → 全 PASS（exit 0，棘轮数与自报一致）
- `STYLE_PREVIEW_EVIDENCE_DIR=/tmp/f05r1_repro flutter test …/style_preview_evidence_test.dart` → 28 用例绿，56 文件全 byte-identical（exit 0）
- C1 探针（`_review_c1_probe_test.dart`，3 用例）→ 静默空串/渲染守卫吞掉/fail-loud 立红全部按预期，用后已删

## 6. 结论

三条卡验收全部有可失败测试 + 可复现证据支撑且经独立复跑；红线零触碰；CH-4 守门声明属实；证据可复现性实测优于自报。**总裁决：PASS_WITH_CHALLENGES**——F05 可销账 DONE_REVIEWED（1/1 独立审查通过），R1-C1a 随转正前增量落，R1-C3a 顺手修。本 receipt 落账后 `review_receipt.json` 的 PENDING 状态由台账销账流程翻转。
