# V4-S01 · 独立审查 receipt（一审）

- 审查 agent：wtS01R1（未参与 S01 实现）
- 审查对象：`agent/v4/s01` @ `47d0f51b`（实现 `e8a6d3f1` + 证据其后；基线 `d57a7aa8`），审查开始时工作树干净
- 卡标准：`v4/04_tasks/tasks.json` → `V4-S01`（normal / 独立审查 1 位 / required_locks: motion-policy / modules: visual_elements, aurora）
- 裁决：**PASS_WITH_CHALLENGES**（R1-1 证据口径勘误 + R1-2 验收③记账口径 + 两项移交条件；无实现阻断）

## 0. 独立复验（全部亲跑，worktree wtS01）

| 项 | 命令/锚点 | 结果 |
|---|---|---|
| 提交链与工作树 | `git status && git log --oneline -3` | clean；d57a7aa8 → e8a6d3f1（实现）→ 47d0f51b（证据），与自述一致 |
| 乐谱↔窗口表逐行对齐 | `v4/02_design/MOTION_AUDIO_HAPTICS.md` L11/12/13/15/16 vs `semantic_motion.dart` L62-70 | 五行 scoreLine 逐字引用原乐谱行；窗口 [80,80]/[160,220]/[160,160]/[160,160]/[0,650] 与乐谱字面一致 |
| 预算表唯一权威 | `grep -rn kSparkleSemanticMotionBudgets lib` | 消费点仅 `sparkle_pressable.dart:107`（press）与 `semantic_motion_widgets.dart`（三组件默认参数）；U02 `resolveSparkleMotionTokens`/`sparkle.motion` 未触碰，正交属实 |
| 里程碑 650 同源 | `pixel_state.dart:317` | `motion?.milestoneMax ?? const Duration(milliseconds: 650)` — 与预算表 650 同源属实（未造第二里程碑载体） |
| reduceMotion 单口径 | `sparkle_context_extension.dart:39-44` | 仅 MediaQuery `disableAnimations ∥ accessibleNavigation`；新码零 `platformDispatcher` 直读（`grep` 三新文件无命中） |
| 新套件 | `flutter test test/core/design/semantic_motion_s01_test.dart semantic_motion_s01_evidence_test.dart` | **23/23 全绿 ×8 次执行**（首次域内跑之外的 4 次独立 + 3 次域内复跑全绿）；G+ 滚帧 avg 19379us<70000、H+ 动画 56.2us vs 静态 25.3us（与自述 18711/57.4/28.4 同量级，门内） |
| design 域 | `flutter test test/core/design/` | 237/237 全绿 ×3 次复跑（见 §4 flake 注记） |
| 消费面回归 | run_manifest 命令 7 同款五套件 | **56/56 全绿** |
| analyze | `flutter analyze --no-pub` | No issues found!（7.7s） |
| 消费点清点 | `grep -rln "SparklePressable(" lib`（排除自身） | **18 文件**（自述"7+"成立且保守）；抽 semantic_pill/task_pill/sprint_card 三处均无本地 Duration 覆盖 → 80ms 真实生效 |
| 静态分支 | `sparkle_pressable.dart` diff + B± 用例 | reduce-motion 不装 AnimatedScale 壳（非 Duration.zero 通配）；常规路径 scale 0.97/曲线不变，唯一差量 = 100ms 字面量→`budgets.press`(80ms)，B+ 在航 40ms scale∈(0.97,1.0) 亲验 |
| 三组件调用点 | `grep -rln "SparkleProposalEnter\|SparkleReceiptSwap\|SparkleEvidenceStamp" lib test` | 零产品调用点（仅组件自身+测试）——limitation #1.4 如实；F03 `ExperienceFeedbackAdapter` 本身亦仅自文件+doc 注记（同如实） |
| repeat 存量清点 | `grep -rln "\.repeat(" lib --include="*.dart"` + 逐文件剥注释复核 | **49 文件全部为代码级命中**（无注释误报）；自述 48 少记 1（方向=债务略大于登记，归 U15 时以复跑数为准） |
| 合并演练 | `git merge-tree --write-tree HEAD origin/main`（main=dbe20f50，merge-base=d57a7aa8） | exit 0 零冲突；S01 五文件与 main 侧增量（39 笔含 U04/U05）**文件级交集为空**——`core/design` 族在 main 侧零触碰，F06/U05 重叠风险不成立；仅 `tasks.json` 双边改动，走舰队并集解惯例 |
| 交付 PNG 哈希 | `shasum -a 256 v4/evidence/V4-S01/*.png && cmp` | 两文件 sha256 同为 a37b9544…、`cmp` 字节级相同——**但见 R1-1** |

## 1. 等价性双证复核（最重靶）

**结论：降低动态等价成立，且经独立重采以更强口径复现；但交付物中「PNG 同 sha256」一项的证据口径须勘误（R1-1）。**

1. **R1-1｜PNG 同哈希是写出入口 artifact，非独立证据**：`semantic_motion_s01_evidence_test.dart:188-192` 将**同一个** baseline 变体的 PNG buffer `writeAsBytesSync` 到两个文件名——两文件字节相同是必然结果，本身不含等价信息。代码注释（L171「等价已由 RGBA 断言」）如实，但 `diff_or_evidence_only.md`/`run_manifest.json` 把「两文件 sha256 相同」与 RGBA 断言并列表述，读起来像双重独立印证——**须勘误为「单一采集、双路径写出；等价证据仅 RGBA 逐字节断言」**。
2. **真正的等价机器断言为真且恒执行**：L154-164 对**两次独立采集**的 `rawStraightRgba`（baseline pumpAndSettle 终态 vs 静态分支）逐字节比对，常规跑非落盘模式也执行；本审查 8 次套件执行全绿。语义面：两变体各自在场时 label findsOneWidget 分别断言（L92-94 / L116-118），`getSemantics().label` 逐字相等断言（L140-145）；`semantic_motion_semantics.txt` 落盘内容与断言一致（注：txt 两节 rect 均采自静态树——dump 循环在变体 2 之后执行，属轻微证据口径损耗，不影响 label 等价结论，两变体在场断言已分立）。
3. **审查独立重采探针（已删）**：临时探针将两变体**各自独立**采集并各自 PNG 编码后逐字节比对 → 3132 字节 **0 diff**。即等价结论在「两 PNG 各自独立编码」的更强口径下同样成立——R1-1 勘误后证据链无缺口。
4. **「settle 后零 ticker」探针活性**：F-/G- repeat 探针（`_RepeatProbe`，`AnimationController.repeat()`）同法判 `transientCallbackCount ≥1`，判别方向正确（repeat → 瞬态回调持续在册）；F+ 追加 3 空转帧仍 0、H- 静态基线在航期 0——三向（正/反/基线）闭合，非恒真。G- 控制组证明列表混入 repeat 行时 settle 后 ≥1，反向成立。

## 2. 预登记 C1-C5 逐项裁决

- **C1（验收①口径）→ 裁决：S01 面口径成立**。卡 work 文本限定「按语义乐谱实现按压/提案/回执/证据动效」；全 app 清尾归 U15（卡库分工），S04/F06 有同款「本卡面 vs 全 app」判例。本卡面（组件族+按压面）零无限零粒子有机器证据+反例探针。**移交条件①：U15 取用本卡清点基线时以复跑数 49 为准（自述 48 少记 1），并按 limitation #1 的无门清单（stepper_indicator/flame_indicator/weather_guide_screen 等）排优先级。**
- **C2（按压 100→80ms 未会签）→ 裁决：保留，风险=低-中（真实可见但卡面授权内）**。行为差量真实（B+ 在航可测 + diff 唯一差量=常量替换）；授权链 = 卡 objective「按语义乐谱实现按压动效」+ motion-policy 乐谱行字面「80ms轻压」；DS 原子节奏单域、18 消费文件继承、消费面 56/56 回归绿。锁租约 NOT_RUN 已披露（无 coordination remote），diff 自证替代成立。**记账要求：销账 summary 载明「全局按压节奏 100→80ms 用户可见差量」；如任一消费面 owner 事后反对，回退仅动 `sparkle_pressable.dart:107` 一处。**
- **C3（三组件零调用点）→ 裁决：卡面实现完整，集成债登记为移交条件②**。objective 是「实现」三行动效（此前无任何实现），F02/F06「组件+机器证据先行、集成随后」先例成立；不并线 1680 行在航 aurora/chat 面是正确取舍。**移交条件②：三组件接线必须挂进 F03 集成链或新小卡并在卡库登记，V4 收口前不允许「已实现未接线」无主态；若集成时改契约（如 replacementKey 语义），按卡面 path_policy 回本卡修订。**
- **C4（点值零容差）→ 裁决：成立，维持**。乐谱字面 80/160/160 为点值，[80,80]/[160,160] 严格窗口=「预算即契约」的有意摩擦；proposalEnter 保留乐谱自带区间 [160,220]。A- 变异判负 ×3 亲验（改值出窗具名显形，违例信息回引乐谱原文）。需要容差属规范 owner 修订乐谱的域，窗口表单点可改，本卡结构不受影响。
- **C5（帧对照口径强度）→ 裁决：验收③记「代理对照 PASS + 真机 profile NOT_RUN」，不得记整面 PASS（R1-2）**。卡面字面「profile下帧时间」= profile 模式帧统计，本卡无设备 → NOT_RUN（limitation #1.2 如实，符合 AGENTS.md「无设备交付阻塞证据不伪造」与 V4_DONE 设备面判例），不阻 REVIEW。已交付的 H 组是有效但弱的代理：H+ 60 帧墙钟均值中动画仅前 ~13 帧在航（200ms/16ms），「动画 avg 56.2us」被 ~47 空闲帧稀释——它证明的是「动画路径成本有界 + 基线确为静止路径（H- 零 ticker）」，**不是每动画帧成本**。记账口径照此写；真机 profile 缺口随设备面卡（与音触同族）收口。

## 3. 测试质量与计数

- **23 分解吻合**：A2 + B3 + C3 + D4 + E3 + F3 + G2 + H2 = 22 主套 + 1 证据采集；与 run_manifest/test_results.json 逐字一致；零 skip。
- **亲跑抽一（design 237）**：3 次复跑 237/237；消费面 56/56；analyze 0 issue。
- **源码棘轮真实**：F+ 剥注释行后禁 `.repeat(`/`AnimationController`，覆盖两新 lib 文件；棘轮范围不含 `sparkle_pressable.dart`（其 AnimatedScale 为一次性，无 repeat/controller，不构成缺口）。
- **flaky 注记**：本审查第一次 design 域全量跑出现 1 败（+236 -1，tail 截留未捕获用例名）；随后 3 次域内全量 + 4 次套件独立跑共 8 次执行全绿，未复现。design 域内唯一墙钟敏感面是本卡 G/H 组（u02 无墙钟断言）；按 U01 判例记负载型 flake 观察，不作回归、不作为通过证据引用（与实现者 performance 域首试 1 败同族披露口径一致）。

## 4. 移交与记账清单（非阻断）

1. **R1-1 勘误**：证据文档（diff_or_evidence_only.md / run_manifest.json）中「PNG 两文件 sha256 相同」表述改为「单一采集双路径写出；等价证据 = 两变体独立采集 RGBA 逐字节断言（恒执行）」。可在销账 summary 一句话完成，不重开证据。
2. **R1-2 记账**：验收③ = 「测试环境 CPU 代理对照 PASS + 真机 profile NOT_RUN」；验收① = S01 面口径（全 app 清尾归 U15）。
3. **条件①**：U15 取 49 文件复跑清点（自述 48 少记 1）。
4. **条件②**：三组件接线归属（F03 集成链 or 新小卡）登记进卡库，V4 收口前不得无主。
5. 锁租约补登：任一有 sparkle-coordination-v2 remote 的会话为 motion-policy 补租约登记（limitation #1.3 已自报）。

## 5. 裁决

**PASS_WITH_CHALLENGES** —— 实现与机器证据达到 S01 卡面要求（预算表↔乐谱逐行机器校验一正一反、组件族四纪律每面有正反+控制组、降低动态等价经独立重采以更强口径复现、按压 80ms 对齐有在航证据且 18 消费点回归绿）；无实现阻断。两项勘误（R1-1 证据口径、R1-2 验收③记账）、两项移交条件（U15 清点 49、三组件接线归属）随本 receipt 入账，由销账与对应 owner 落实。

- 审查人：wtS01R1（独立未参与会话）
- 日期：2026-09-29
- 临时探针已删（`tmp_wts01r1_probe_test.dart` 用后即删）；实现 commit 未触碰；未 push
