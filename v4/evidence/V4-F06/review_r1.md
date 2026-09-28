# V4-F06 一审 receipt（wtF06R1）

- **审查者**：wtF06R1（独立会话，未参与 F06 实现）
- **日期**：2026-09-29
- **对象**：commit `ecf30872`（分支 `agent/v4/f06`，base `fea3a4aa`，worktree `/Users/brsama/code/GitHub/wtF06`，审查起点工作树干净）
- **方法**：只读审查 + worktree 独立复跑 + 15 对对比度独立验算 + gen-l10n 实证 + 3 处 mutation 抽查（改实现应红、用后即还原）；产物除本 receipt 外零落盘
- **总裁决**：**PASS_WITH_CHALLENGES**（普通风险单审通过；3 项非阻塞挑战 R1-C1a/R1-C1b/R1-C2 随 receipt 登记，不阻塞销账；C2/C3 预登记口径按 §2 裁决为通过+注记）

---

## 1. 验收三条对证据（逐条独立下判）

### 1.1 验收①「关键目标≥48dp项目标准；正文contrast≥4.5:1」— 通过

- **48dp**：`C+`（pixel_a11y_f06_test.dart L191-214）以 `tester.getSemantics()` 对
  PixelPrimaryAction 语义命中面断言宽高均 ≥48，且 flags 断 `isButton`；`C-`
  32dp 控制组被同一探针判负（L216-241）。族级差量举证成立：`DS.touchTargetMinSize == 48.0`、
  SparkleButtonV2 消费 settings 三档（48/56/64）、既有 `a11y_touch_target_test`
  套件在 app+a11y 批 73/238 绿（本审复跑）。
- **对比度 15 对独立验算**：审查从源码直接取 hex（theme_manager.dart
  light/dark normal 档 + pixel_preview_theme.dart 三档 + design_system.dart
  neutral0）用 WCAG 2.1 相对亮度公式独立重算（与被审测试不同实现）：
  全部 15 对 ≥4.5:1，最低 5.24:1（classic-light textSecondary/surfacePrimary）；
  星图白/#101929 = **17.60:1**，与 diff_or_evidence_only.md 自报值逐位一致。
  `E-` 禁用灰控制组实测 **2.50:1** < 4.5 成立（注记 R1-C1b：测试注释写
  「#999999 ≈2.85:1」为旧值，实际 token = #A49B90 = 2.50:1，断言不受影响）。
- 组合计数核对：4 classic + 1 galaxy + 4 chat + 6 pixel = **15 对**，与自述一致。

### 1.2 验收②「screenreader无同义重复朗读；toast不抢持续输入」— 通过

- **无同义重复**：`D+` 对五态徽章在**编译后语义树**上断言 label 逐字相等
  （Semantics(container,label)+ExcludeSemantics 单一来源）；`D-` 拼接控制组
  （container label + 未排除子树文本，F02 失败史形态）被同一探针判负。
  galaxy 连接子句面：`G+` 的 `find.bySemanticsLabel(..., findsOneWidget)` 走
  编译后语义树且唯一命中——dump 文本中每标签 3 行为元素树投影
  （RenderSemanticsAnnotations 嵌套合并进同一语义节点），**非重复朗读节点**，
  与 run_manifest「节点条目×读屏遍历投影」口径自洽。
- **连接文本列表证据**：`galaxy_edge_list_connected_semantics.txt` 实录
  「科技 Node 0（已解锁，掌握度 42 分，已学习 3 次，重要度基础），连接：Node 1」
  与「Node 1 …连接：Node 0、Node 2」（双向展开+图序去重）「艺术 Node 2（未解锁…）
  连接：Node 1」，9 处命中 = 3 节点×3 投影；sha256 与 manifest 一致。
- **toast 不抢输入**：`F+`（app_feedback_a11y_focus_test.dart）composer 持焦 →
  AppFeedback.success → SnackBar 在屏时 `primaryFocus` 同一对象不变 +
  `isLiveRegion` 旗标；`F-` 模态对话框控制组被同一探针判负（焦点确实被夺）。
  差量举证口径成立（现行为已满足，测试钉死防回退）。

### 1.3 验收③「200%和reduced-motion无零 duration崩溃」— 通过（字面口径，见 §2 C3）

- `A+` 故事页全族 TextScaler.linear(2.0) 零异常+五态语义在树；`A-` 溢出探针
  活性（2000dp 盒子同法必报）。`I+` 星图 200%+disableAnimations 整屏零异常、
  摘要与节点语义存活。`H+` 减弱动效入场控制器直落 1.0（模糊 sigma=0），
  `H-` 常规路径 <1.0 在航（探针活性）。
- **PNG/语义五件套**：sha256 五件全部与 manifest 一致（本审 shasum -a 256 复算）；
  200% PNG 布局完整无溢出条纹、换行行为可辨，100% 基线对照成立；Ahem 方块
  为 tester 字体口径，真实文案由同变体语义 dump 承担——与 F02 同限，NOT_RUN
  披露如实。

## 2. 预登记 C1-C5 逐项裁决

### C1 `composeAppTextScaler` 委托等价性 — **判等价（通过）**

静态逐项核对 app.dart 委托（diff −10/+9）与 accessibility_provider.dart 新函数：
夹窗参数 [0.85, 1.35] 同值；`.scale(16) / 16 * fontScale` 运算次序同（Dart
`/`与`*`同优先级左结合，两侧均为 `(x/16)*fontScale`）；`composeDisableAnimations`/
`composeAccessibleNavigation` 均 `system || inApp` 与旧内联 OR 律同值；
未装载分支 clamp 原样未动。叠加 I+ 五点字阶断言（1.0/1.56/0.85 托底/1.35 夹顶/
1.89 叠加）与本审 Mutation-1（见 §4）——委托重构行为等价成立，非仅自述。

### C2 连接子句粒度 — **判实现口径成立（通过+注记）**

规范原文（ACCESSIBILITY_ASSETS.md:5）：「星图的可选节点逐一标角色/名称/状态、
**连接有文本列表**」——要求的是连接关系以文本列表可读，**未规定逐边语义条目**。
实现为节点条目内连接名列举（复用物理引擎同源 `_buildAdjacency`，图序去重、
未知名端点跳过、空邻接不造子句），G± 双向断言钉死。审查认可其依据：节点已是
独立语义边界（GALAXY-A11Y 容器纪律），逐边清单会引入第二套 N-1 条目与遍历序
仲裁而无规范字面依据。**注记**：若后续读屏动线评估要求边粒度导航，属规范
owner 增量，非本卡缺口。

### C3 200% 夹窗保留 vs 验收③字面 — **无违反（通过+转注记）**

按卡文本裁决：验收③字面 = 「无零 duration 崩溃」，**非**「200% 全穿透」。
实现面（a）组件族/星图在直加 2.0 字阶下零异常已断言（A+/I+）；（b）app 壳夹窗
[0.85,1.35] 为开卡前已注册决策（A-SPEC6 REPORT.md N32：叠加律条目存档；旧
app.dart 代码同夹窗，本卡按「沿用V3已有实现只补缺口」原样保留）；（c）有效
上限 1.89× 在 doc 注记与组合测试上限点双登记。**注记转 R5**：若产品面要求
200% 全通路穿透，需规范 owner 裁决夹窗调整（布局安全预算），已由 limitations
§2.1 如实登记，不构成本卡实现缺口。

### C4 typing_text 0 消费点改动 — **判保留（通过+挑战 R1-C1a）**

保留依据成立：A-SPEC6 N32 明令 platformDispatcher 直读为「存量债登记制——
**触碰即迁，不专项**」，且 typing_text 被点名为存量七文件之一；本卡触碰该
文件即触发迁移令。行为核对：animate 主路径等价（initState 照常起打字，
didChangeDependencies 在首帧前命中减弱即停并直落全文，Timer 首跳在 charDelay
之后不露帧）；`_BlinkingCursor`/`TypingRichText` 同口径。0 产品调用点本审
grep 复核属实（lib/ 零命中）。**挑战 R1-C1a（非阻塞）**：该文件改动现为
**零测试覆盖**——test/ 无 TypingText/TypingRichText 引用，chat_golden_test 的
「typing indicator」为 harness 自建组件（L254/271 `_buildTypingIndicator`），
非本组件。处置建议：接线时补 reduce-motion 微测，或届时一并裁决摘除；
本卡不阻塞。

### C5 l10n gen×3 手改同步 — **判如实（实证通过）**

本审在 worktree 实跑 `flutter gen-l10n`：churn = 3 个 gen 文件 **−90 行纯空行**
差异（与 run_manifest「-90 行既有现象，F02/F04 同现象」逐字吻合），且 regen
diff 对 `galaxyA11yNodeConnections` **零触碰**——手改三件与新键 gen 产物字节
一致。L10N-REGEN-PARITY 复跑 PASS（10034 键 == 抽象成员；zh/en 完整）。
跑后已 `git checkout` 还原，工作树复零。判例引用属实，未跑全量再生成是正确
处置。

## 3. 行为红线

- **reduce-motion 真零 ticker**：不以自写探针验证，而以 Mutation-2 证实——
  将 `_reduceMotion` 恒 false（旁路静态分支）后 `pixel_a11y_f06_test` 的 B+
  （transientCallbackCount==0）/B2（accessibleNavigation 同享）**2 例红**；
  B- 常规分支 ticker>0 探针活性同文件在航。红线成立且无探针残留。
- **组装律真值表**：I+ 4 组合×2 函数全表 + 字阶五点 + I-（AND/替换两错误实现
  被同一探针判负）；Mutation-1（`||`→`&&`）后 2 例红。
- **无边图 V3 标签字节不变**：服务层默认参 `const []` 不追加（diff L191-227）；
  `G-` 断言完整标签逐字相等（「科技 Node 0（已解锁，掌握度 42 分，已学习 3 次，
  重要度基础）」）；V3 `galaxy_screen_semantics_test`（bc0187a7，先于本卡）
  在 galaxy 域 159+~1 复跑绿。
- **冲突面**：`git diff fea3a4aa --name-only -- mobile/` = **16 文件**
  （6 产品码+5 l10n+5 测试），RF-06 三文件/app/routes.dart/tokens_v2/backend/
  proto 零命中；AQ/BG 守卫在主检出（Sparkle-project）复跑 **PASS**（Rule AQ
  PASS + Rule BG PASS 7 proto 0 staleness），与自述一致；sparkle-cosmos 检出
  同脚本因生成目录缺位 FAIL，属环境性——实现者环境声明核实为真。

## 4. Mutation 抽查（3 处，全部改实现应红、用后即还原）

| # | 变异点 | 变异 | 结果 | 还原 |
|---|---|---|---|---|
| M1 | accessibility_provider.dart L53 | `system \|\| inApp` → `&&` | composition 4 例中 **2 红**（I+ 真值表/I- 判负） | ✓ 0 残留 |
| M2 | pixel_state.dart L294 | `_reduceMotion` 恒 false（静态分支旁路） | pixel_a11y 11 例中 **2 红**（B+/B2 零 ticker） | ✓ 0 残留 |
| M3 | galaxy_accessibility_service.dart L225 | 连接子句条件恒 false | galaxy 5 例中 **1 红**（G+）/G- 保持绿（判别精确） | ✓ 0 残留 |

`git status` 复核三处还原后均 0 变更。测试面探针活性控制组（A-/B-/C-/D-/E-/
F-/H-/I-）逐个核对均为真实反例面，非恒真断言。

## 5. DoD 集成面复验（worktree 内独立复跑）

| 项 | 本审实跑 | 与自报一致 |
|---|---|---|
| `flutter analyze --no-pub` | No issues found!（68.1s） | ✓ |
| 24 新测（5 套件合跑） | 24/24 绿 | ✓ |
| `test/core/design/` | +214 绿 | ✓ |
| `test/core/navigation/` | +36 绿 | ✓ |
| `test/core/widgets/` | +28 绿 | ✓ |
| `test/features/galaxy/` | +159 ~1 绿 | ✓ |
| `test/features/settings/` | +11 ~1 绿 | ✓ |
| app+a11y 批（test/app+7 文件） | +73 绿 | ✓ |
| goldens（分母外补跑） | +84 ~15 绿（chat golden 的 typing indicator 非 TypingText，见 R1-C1a） | 补充面关闭 |
| 四棘轮 | UI-TOKENS 225/275·634/727；SPACING 1591/1623；TYPO 232/234·0/0·6/6；DL-SPEC offLadderDuration=177/181 全 PASS | ✓ |
| L10N-REGEN-PARITY / I18N | PASS 10034 / PASS | ✓ |
| AQ/BG（主检出） | PASS / PASS | ✓ |

## 6. 数字诚实性

- diff 短统计 **27 files, +3630/−62** 与自报逐字一致；24 新测 = 11+2+2+5+4
  （grep 逐文件计数）；15 对对比度；回归域计数全部复现。
- 五件套 sha256 全部相符；tasks.json 仅置 `in_progress/REVIEW_READY` 未自我
  销账；diff 零 print/F06_DEBUG 残留；limitations §1 五项 NOT_RUN（真机读屏/
  真实字形/帧率/租约/AQ-BG worktree 环境）披露如实无冒充。
- **勘误（R1-C1b，非阻塞）**：diff_or_evidence_only.md §红线首句「全量 15 文件
  = 6 产品码 + 5 l10n + 4 测试」计数错误——实际 **16 文件、5 个测试文件**
  （同文档 §测试自述「5 新文件」正确；属少计非虚报）。测试注释 hex 旧值
  （§1.1）；limitations §2.5「像素成功徽章同理」措辞不精确——徽章减弱→恢复
  实际会补播上升动效（didChangeDependencies 重建控制器），与光标「不重启」
  不同理，行为本身合理。

## 7. 挑战清单（全部非阻塞）

- **R1-C1a**：typing_text.dart 迁移零测试覆盖（0 调用点+golden 未覆盖）；
  接线时补 reduce-motion 微测或届时裁决摘除（§2 C4）。
- **R1-C1b**：三处文档/注释勘误（15→16 文件计数；E- 注释 hex 旧值；§2.5
  「同理」措辞）——后续 docs commit 顺手清偿即可，不另开卡。
- **R1-C2（注记）**：C2 节点粒度口径与 C3 夹窗保留均判通过并注记在案
  （§2）；两者如需推翻均属规范 owner（R5）裁决面，非实现缺口。

## 8. 结论

三条卡面验收均有机器可失败断言背书并经独立复跑/独立验算/mutation 三重证实；
四棘轮与 l10n/i18n 守卫复现；AQ/BG 主检出 PASS 核实；NOT_RUN 面披露诚实；
预登记 C1-C5 全部裁决通过（C4 附零覆盖挑战、C2/C3 附注记）。**维持
PASS_WITH_CHALLENGES**，可按接力机制进入销账（挑战项随卡面遗留登记，不阻塞
DONE_REVIEWED）。

— wtF06R1，2026-09-29（本 receipt 为唯一落盘产物；mutation 与 gen-l10n 实证
均已还原，worktree 复核 0 残留）
