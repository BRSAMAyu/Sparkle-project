# V4-F02 — diff_or_evidence_only

## 结论一句话

`mobile/lib/core/design/pixel/` 新增原生像素组件族（PixelFrame/主次卡/PrimaryAction CTA/状态族/receipt/diff/run/evidence + 2dp 概念网格几何原语）与独立状态故事 preview 页（不接五 Tab 路由），三条验收面以 34 个可失败 widget 测试钉死：DPR 1/1.25/1.5/2/3 轮廓物理像素对齐且文字恒走系统字体路径、四非成功态四元组（令牌槽+字形+轮廓+动效）互异且绝不渲染成功动效元素、装饰层 IgnorePointer/ExcludeSemantics 透传且键盘 Tab 与语义标签可定位操作；classic（preview off）零差量红线由降级测试守护；`flutter analyze` 零 issue，design 套件 160/160 全绿，四条设计棘轮守卫（UI-TOKENS/DL-SPEC/TYPO/SPACING）全 PASS。

## 差量明细（相对 base 5575e38b = 开卡时 main HEAD）

全部为**新增文件**，零修改既有文件（design_system.dart/theme_manager.dart/路由/RF-06 冲突面零触碰）：

产品码 `mobile/lib/core/design/pixel/`（7 文件，~1250 行）：

- `pixel_geometry.dart` — DPR 感知几何原语：`snapToPhysicalGrid`/
  `snapLengthToPhysical`（stroke 中心与填充边缘各自对齐物理像素）、
  `PixelOutlineGeometry.stair`（阶梯切角路径；顶点物理吸附、阶梯步数
  = cut/pixelStep 与 DPR 无关、包围盒偏差 ≤4×0.5 物理像素；radius>0
  走 classic 圆角降级）。纯函数无 widget 依赖，是验收 1 的可失败断言面。
- `pixel_frame.dart` — PixelFrame（合同：仅装饰/Semantics 由 child
  提供/不能吞手势）：装饰层 = `IgnorePointer + ExcludeSemantics +
  CustomPaint(PixelOutlinePainter)`，内容层独立；主卡深墨轮廓 +
  8dp 阶梯角，次卡单线/轻底；`PixelDivider`（厚度物理对齐）。
  classic 降级：`PixelProfileTheme.of == null` → 既有 22dp 圆角。
- `pixel_primary_action.dart` — PrimaryAction CTA（合同：loading 不改
  宽度/重复点击禁写/focus ring 在切角外仍可见）：标签恒参与布局
  （loading 时 Opacity 0 占位，指示器叠加）；press 锁存窗 =
  stateMotion.press；ring = 轮廓外侧 2dp 圆角矩形环
  （`PixelFocusRingPainter` 公开供测试断言），focusNode 单一挂载点
  （TextButton 内部 Focus 持有，State listener 观察）；语义经
  `Text.semanticsLabel` 注入唯一 button 节点（不与内建节点重复）。
- `pixel_state.dart` — 状态族唯一事实源：`PixelRunState`
  （cancelled/unknown/conflict/failed/success）、`PixelStateSpec`
  四元组（令牌槽+字形+轮廓+celebrates 动效位；**只有 success 庆祝**）、
  `PixelStateVisual`（classic 降级 outline=none）、`PixelStateBadge`
  （显式 Semantics label + ExcludeSemantics 子树）、
  `PixelSuccessBadge`（唯一庆祝载体：milestoneMax 上升动效；类型本身
  即反例锚点）。
- `pixel_cards.dart` — 主卡 `PixelPrimaryCard`（单主 CTA 位 + 状态
  徽章）、次卡 `PixelSecondaryCard`、`PixelReceiptCard`（为什么/用了
  哪条经验；refs 空 → 「未引用经验」不伪造；纠正/仅本次/删除恒可达）、
  `PixelDiffCard`（old→new+理由；六态 proposed/approved/applying/
  committed/unknown/conflict；unknown/conflict **无前进入口**=不能
  合同）、`PixelRunCard`（阶段列表 + 继续入口；progress==null 绝不
  渲染百分比=不造假进度）、`PixelEvidenceStamp`（persisted≠validated≠
  mastery 三档；撤回/重算恒可达）。
- `pixel_state_story_page.dart` — 状态故事 preview 页：全部状态徽章、
  四非成功态承载卡、成功对照、组件族、装饰叠按钮透传演示区。
  `kPixelStateStoryRouteName` 仅命名种子，**未注册进正式路由**
  （五 Tab 路由合同零触碰）。
- `pixel.dart` — barrel（唯一导出面）。

测试 `mobile/test/core/design/pixel/`（5 文件，34 用例，每验收面一正一反）：

- `pixel_geometry_dpr_test.dart`（9）— 验收 1：五档 DPR 纯几何吸附 +
  widget 渲染盒/路径顶点物理对齐 + 文字不点阵化（fontSize 逻辑值跨
  DPR 恒等、无 RawImage、无 Transform 画布缩放）+ 反例（未吸附顶点
  必须判负）+ classic 降级。
- `pixel_state_story_test.dart`（11）— 验收 2：四元组两两互异 +
  浅/深两档渲染色逐对不等 + 每非成功态「绝不含 PixelSuccessBadge/
  check 字形/已完成语义」反例钉死 + 控制组（含成功徽章的树必须命中
  =可失败性证明）+ 故事页全组件就位。
- `pixel_frame_hit_focus_test.dart`（6）— 验收 3：装饰覆盖按钮点击
  仍达 + 控制组（吞手势层必须吞掉=判别力）+ Tab 遍历两 CTA + ring
  出现 + receipt 三操作语义 tap 可触发 + 控制组（回调为空时 tap 动作
  必须为 0）+ button 标志断言。
- `pixel_primary_action_test.dart`（5）— loading 宽度恒等、同帧双击
  单次触发、loading 禁写、ring 外扩几何、classic 可用性。
- `pixel_story_evidence_test.dart`（3）— 三 profile 真实渲染 + 按
  `PIXEL_STORY_EVIDENCE_DIR` 落盘 PNG/语义 dump（本卡证据由此生成）。

证据 `v4/evidence/V4-F02/`：五件套 + 三档截图/语义 dump（见
run_manifest.json artifacts）。

## 验收对照

| 卡面验收 | 结果 |
|---|---|
| DPR1/1.25/1.5/2/3 主要轮廓稳定，文字不点阵化 | 满足：五档 `tester.view.devicePixelRatio` 注入（physical=logical×dpr 固定约束），路径顶点全部物理像素对齐、阶梯步数恒 4、渲染盒逻辑尺寸恒等；文字 RenderParagraph fontSize 逻辑值与文本盒跨 DPR 恒等、无 RawImage/无 Transform（pixel_geometry_dpr_test.dart；反例=未吸附顶点判负） |
| 取消/unknown/conflict/失败均有区分且无成功动效 | 满足：四态（令牌槽/字形/轮廓/动效）四元组两两互异（浅/深两档渲染色逐对复证）；每态组件树反例钉死无 PixelSuccessBadge/check 字形/「已完成」语义，celebrates 只有 success 为 true（pixel_state_story_test.dart；控制组证明查找器活性） |
| 装饰不吞点击，键盘与屏幕阅读器可定位操作 | 满足：切角装饰叠按钮点击仍达（IgnorePointer/ExcludeSemantics 实现面有断言）；Tab 顺序聚焦两 CTA 且 ring 出现；receipt 纠正/仅本次/删除语义 tap 真实触发（pixel_frame_hit_focus_test.dart；双控制组证明判别力） |
| classic 行为零差量（发布面红线） | 满足：classic 下 PixelFrame 走 22dp 圆角（stairSteps=0）、无像素扩展挂载、PixelPrimaryAction 正常可用、无任何像素装饰类型渗漏（两条专门测试） |

## 保持不动（红线核验）

- RF-06 冲突面（dashboard_screen/compact_status_bar/task_execution_
  screen）：diff 不含任何 features/ 文件，零触碰。
- 五 Tab 路由合同：零触碰（故事页不注册路由）。
- 既有令牌体系：组件只消费 `context.sparkleTheme.colors` /
  `SparkleTypography` / `PixelProfileTheme`（F01 产物），无第二套
  颜色/字阶/间距类，无新增 `Color(0x…)` 字面量（UI-TOKENS PASS 且
  本目录不在 features 扫描面也主动遵守）；间距全取 4 基栅格档
  （SPACING-RHYTHM PASS，首跑 FAIL 已修）。
- 生成文件：零触碰（mobile/lib/gen 为 gitignored 实体目录，自主检出
  复制进 worktree，未入库）。
- 系统语义：CTA/徽章均用原生 TextButton/Semantics/Focus 系统，
  不造第二套输入通道。
