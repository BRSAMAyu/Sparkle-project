# V4-F02 — limitations

## 如实未测 / 未做

1. **真机/物理屏面 NOT_RUN**：本机无 iOS/Android 真机或模拟器。验收 1 的
   DPR 面以 `tester.view`（TestFlutterView）注入五档 devicePixelRatio
   （1/1.25/1.5/2/3）覆盖，断言的是几何/布局/文本的**逻辑与物理对齐契约**；
   物理屏上的实际字形抗锯齿、真机 60Hz 帧统计（DESIGN_SYSTEM.md：
   frame 统计在 profile/release 测）均未测，不得声称已验证。
2. **截图文字为方块**：widget 测试环境用 Ahem 兜底字体、无 CJK 字形，
   三档 PNG 中文字渲染为方框。截图证据的有效面是**轮廓/色板/状态
   形状/布局**；中文真实字形属设备面。语义树 dump（87 节点/档）不受
   此影响，label 为真实中文。
3. **sparkle-coordination-v2 租约登记 NOT_RUN**：本机未配置该私有远端
   （git fetch 无此 remote）。冲突面以 diff 自证：零 features/ 文件、
   零 dashboard_screen/compact_status_bar/task_execution_screen 触碰、
   零路由文件。若舰队状态分支需要本卡状态，请有远端配置的会话补登。
4. **组件尚未接入任何正式页面**：本卡交付设计目录内的组件族与故事页，
   页面家族替换是后续卡的事（DESIGN_SYSTEM.md 迁移办法：先适配组件
   故事页）。因此「classic 零差量」在产品面自动成立（无调用点），
   组件级由两条降级测试守护。
5. **PixelStateSpec 的语义词表为组件面初版**：「已取消/结果未知/版本
   冲突/失败/已完成」五词为本卡落地值；若 V4 后续有产品文案权威
   （l10n 词表），接入时需对齐（当前无 l10n 依赖，硬编码中文与既有
   core/design 组件同口径）。

## 已知取舍

- **CTA 锁存窗用 Future.delayed**：非动画驱动的真实 Timer。这是
  「重复点击禁写」的最小实现；widget 测试需 pump 走完窗（已在测试
  注明）。若后续卡要求可中断取消，应升级为可 cancel 的 Timer。
- **PixelDiffCard 的 unknown/conflict 无前进入口**：是「不能合并」
  合同的 UI 面（保守侧）；真实冲突解决流（如二选一确认）属业务卡，
  不在本卡视觉组件职责内。
- **PixelRunCard 恢复入口恒显**：「离开后恢复」合同要求入口可达；
  是否显隐由业务卡后续决定。
- **RunCard running 态徽章**：故事页用 unknown 族演示 RunCard 状态位；
  running（进行中）态的专属徽章未单独设计（非验收四态范围），后续卡
  如需可在 PixelRunState 扩展。
- **测试环境的 focus ring 宽度断言耦合呼吸位常量（3dp）**：若组件
  调整呼吸位需同步测试——已在测试中以注释标明关系。

## 审查挑战点预登记（给独立审查）

1. **验收 1 的「轮廓稳定」口径**：本卡以「顶点物理像素对齐 + 阶梯
   步数 DPR 无关 + 逻辑盒恒等」定义稳定（DESIGN_SYSTEM.md「stroke
   中心与填充边缘各自对齐物理像素」的机器化），不是逐像素 golden。
   挑战点：是否需要补 golden 图对比？——golden 跨宿主字体/抗锯齿
   不稳，未采用；如审查认为必须，建议只在真机面补。
2. **验收 2 的「动效区分」**：四非成功态动效维均为「无动效」，区分
   由令牌/字形/轮廓承担，成功态独占上升动效。挑战点：「各有专属
   token/形状/动效组合」是否要求非成功态各有微动效？——本卡读法：
   合同原文「错误、撤回和未知不能用庆祝视觉」优先，非成功态静态是
   特性不是缺失；若裁决需要微动效（如 conflict 双线脉冲），应先改
   DESIGN_SYSTEM.md 口径再改码。
3. **控制组的有效性**：三处反例各带控制组（吞手势层必须吞、成功树
   必须命中、空回调必须无 tap），证明断言非恒真。请审查控制组本身
   是否会被实现变化误伤。
4. **`PixelOutlinePainter` 读 dpr 的通道**：paint() 内取
   `platformDispatcher.views.first.devicePixelRatio`（painter 无
   context）。多视图（MultiView）场景下 first 未必是本视图——当前
   App 单视图无影响；若 V4 后续上多视图（桌面分屏），此处需改为
   MediaQuery 传入。已登记，不在本卡修。
