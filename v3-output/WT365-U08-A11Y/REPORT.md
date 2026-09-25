# WT365-U08-A11Y · REPORT（wt365 / 卡 U-08 Accessibility 全链升级）

- 分支：`wt365-u08-a11y`（worktree wt365-u08-a11y，单提交）
- base SHA：`f644de3a`（main @ U-06 合入点，卡依赖 U-05→U-06 链满足）
- final SHA：本分支 HEAD（单提交 `feat(a11y): wt365 卡 U-08 ...`，含本 REPORT 与 changes.patch；精确 SHA 以返回摘要/git log 为准）
- 状态：**PARTIAL** —— 代码/测试/守卫/analyze 全部完成；定向 flutter test 因内存门 DEFERRED（未达门不虚报执行）

## 验收逐条（卡面 Acceptance）

### 1. GJ01/GJ03/GJ08 核心控件可由辅助技术完成

结构性证据 = 新增 widget 测试 `mobile/test/widget/a11y_u08_state_semantics_test.dart`（6 用例，真实泵入渲染树后断言语义节点，非 mock）：

| 断言面 | 钉住的不变式 |
|---|---|
| 等待族快路径（<500ms） | 骨架退出语义树（整棵语义树恰 1 节点）+「加载中」label 可读 + 不抢播报（liveRegion=false） |
| 等待族升格（>500ms） | stage 文案出现且 loader 根节点 liveRegion=true（WCAG 4.1.3 status messages），2600ms 后推进到下一阶段 |
| compact 形态 | 同为单节点、升格转 liveRegion |
| SurfaceStateView 可恢复错误 | 整块 liveRegion=true；自定义标题可读；「重试」button 角色可达且可触发 |
| offline 横幅 | liveRegion=true；默认词典标题可读；默认下一步「重试」button 角色可达 |
| GJ03 current run 条 | 单节点 button（名字=可见文案）；`SemanticsOwner.performAction(tap)`（TalkBack/VoiceOver 激活等价路径）经 GoRouter 真实跳转 /chat；可点面高 ≥48 |

既有面盘点（本轮审查确认已达标，未重复改造，避免与 U-06 同文件面冲突）：
- **GJ01** `goal_creation_wizard_screen`：步骤指示已有「x/5 + 当前步名」Semantics 与 header 标注（L125-149）。
- **GJ03** `today_cockpit_card`：headline `Semantics(header:true)`（L107）、SparkleButton 自带 button/enabled 语义、唯一 primary CTA 契约不变。
- **GJ08** `contextual_correction_bar`：选项/来源/重校准各 Semantics 已存在（L275/L337/L577-608）。
- 横向 `SparkleIconButton`：N31 语义名（显式>Icon 反推>debug 登记诊断）+ 48 触控下限 + accessibilitySettingsProvider 联动，既有 a11y_batch2~6b 测试在库。

### 2. WCAG AA；不依赖颜色传达关键状态

- 状态三重承载（图标+文字+语义节点）：`_StateBanner`（offline/reconnecting/partial）与失败族（图标+标题+说明+保证非空动作行）本轮补 liveRegion，颜色降级时语义通道完整。
- 触控下限：run 条补齐 `DS.touchTargetMinSize`(48)——仅增高至触控档并垂直居中，非视觉改版、不改交互语义。
- 对比度：零颜色改动；DS 令牌与既有 `a11y_contrast_test` 护栏未动。
- reduced motion：`SparkleSkeleton`/路由过渡/`SparkleContext.reduceMotion` 既有链路未动；本轮语义包装与动画无关。

## 红绿输出摘录

- 守卫：`bash scripts/run_all_rule_guards.sh` → `all rule guards passed (84 rules)`，**EXIT=0**
- analyze：`601 issues found` = **E0/W15/I586 与基线持平**（收敛过程：6 错误→0；2 条自引 pipelineOwner 弃用 warning 已按 SDK 新 API `rootPipelineOwner` 清除；本卡 5 文件最终零贡献）
- 定向 flutter test：**DEFERRED**（见下）

## 改动文件（5）

| 文件 | 变更 |
|---|---|
| `mobile/lib/core/design/widgets/sparkle_skeleton.dart` | SparkleSkeleton 与遗留 _SkeletonBox 家族 ExcludeSemantics：装饰性骨架退出语义树，视觉渲染逐字不变 |
| `mobile/lib/core/state/staged_loading.dart` | 快路径补「加载中」语义 label（零视觉文案噪音契约不变）；升格后整块 liveRegion；compact 单节点化（exclude） |
| `mobile/lib/core/state/surface_state_view.dart` | 失败族 `_failureBodyInner` 与 `_StateBanner` 整块 `Semantics(liveRegion:true)` |
| `mobile/lib/features/home/presentation/widgets/today_cockpit_card.dart` | `_CurrentRunStrip`：单节点 button 语义（label=可见文案 + 语义 onTap）+ 48 触控下限 |
| `mobile/test/widget/a11y_u08_state_semantics_test.dart` | 新增 6 用例（Semantics 树结构性断言） |

## l10n/arb 键变更清单

**零新增、零修改**（未触碰 arb，与 wt363 收割无交叉）。语义文案全部复用既有键：`commonLoading` / `stateStagePreparing` / `stateStageLoading` / `statePhaseOffline` / `retry` / `back`。

## DEFERRED 清单（含补跑面）

1. **定向 widget 测试**：内存门三次复查 swap free 1037M/1045M/1053M 均 <1.2G（§4 硬门），拒跑。补跑命令（门前 `sysctl vm.swapusage` free≥1.2G）：
   ```bash
   cd mobile && flutter test test/widget/a11y_u08_state_semantics_test.dart \
     test/core/state/surface_state_view_test.dart --concurrency=1
   ```
   注意：用例未执行过，补跑时若语义节点计数受宿主组件影响（count==1 断言），按真实语义树修正锚点后须保持不变式（骨架不入树、单节点、liveRegion）。
2. **模拟器/浏览器 screen reader 实测**：本 worker 无模拟器与浏览器权限，以 headless widget 语义树断言替代并如实标注。补跑面 = `v3/04_ux/ACCESSIBILITY.md` 全清单在 Web（NVDA/VoiceOver）+ Android（TalkBack）走查 GJ01/GJ03/GJ08 的记录（含 WCAG AA 抽样取色）。
3. **焦点序（traversal order）系统走查**：本轮以单节点化（run 条/等待族/骨架）收敛乱序面；全表面 traversal 审计待设备门恢复后并入 U-09/后续 a11y 卡。

## Forbidden 自查

未重建真源（无新 provider/状态源，全部挂既有 U-06 渲染面与既有控件）；无视觉改版（仅语义包装与触控档增高）；未改产品交互语义；未动安全/幂等/隔离/审计守卫；测试全部真实渲染泵入，无 mock 冒充；无 arb 触碰。
