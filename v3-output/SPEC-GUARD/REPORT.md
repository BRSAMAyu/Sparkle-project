# SPEC-GUARD · 冲刺面入 UX-COMP 守卫 + sprint 面裸件迁移（A-SPEC 改造 #7 / N1）

> Worktree：`wt184`（基线 78a572c9，开工时 HEAD 已含 wt176/177 合入 = fa9643f0）。
> 规范依据：`v3-output/A-SPEC-V1_1/REPORT.md` §5 改造 #7 + §4 N1。
> 交付物：本报告 + `changes.patch`。零 commit / 零 push / 零凭据。

## 0. 结论速览

- **第 10 治理面入册完成**：`check_ux_component_convention.py` 扫描根 +1 `features/plan/presentation`，守卫跑绿；负向用例（临时裸件文件）确认新文件零容忍生效。
- **sprint 面裸件迁移完成**：当前 HEAD 存量 Chip×2 / Card(elevation:2)×1 / OutlinedButton.icon×1 全部迁入 owner（SemanticPill / GraphiteCardSurface / SparkleButton.outline）；迁移后 sprint_screen 裸 Chip/Card/裸按钮 **清零**，守卫账面从 rawChip=2 降至 0。
- **v1.0 SPEC 增补落地**：`v3-output/DL-R3/SPEC.md` §0.2 / §8（标题+矩阵+新增 §8.10）/ §9.1 四处登记 sprint 第 10 治理面（标记【v1.1 N1 增补 @A-SPEC，落地 @SPEC-GUARD】，不推翻 v1.0 任何条款）。
- **基线 JSON 按 worktree 内现值登记**：共享态处置与合入窗口刷新建议见 §4。
- **验证**：守卫 PASS；`flutter analyze` 本文件净增 lint=0；sprint_screen_test 6 例 + router_smoke_test 8 例 **14/14 全绿**（零新增失败）。

---

## 1. 当前 HEAD 裸件存量清单 + 迁移完成度（①）

> A-SPEC 报告 #7 的行号基于 wt176 重写前的旧 sprint_screen（716 行），**已全部漂移**；下表为按当前 HEAD（fa9643f0）全文件重扫的真实存量。

### 1.1 sprint_screen.dart（本卡迁移对象）

| 存量（当前 HEAD） | 位置（改前行号） | 报告 #7 方向 | 迁移结果 |
|---|---|---|---|
| `Chip(...)` 倒计时（avatar=timelapse，label=剩余 N 天/考日/已结束） | :293 | → SemanticPill | ✅ `SemanticPill(tone: PillTone.brand, icon: Icons.timelapse)`，label 文案与三态分支原样保留（l10n 零新增 key）；tone=brand 理由：倒计时是冲刺身份锚点数字；N5 紧迫色阶属 exam 卡条款，本卡不引入（防双 owner） |
| `Chip(...)` 目标日降级（avatar=timelapse） | :304 | → SemanticPill | ✅ `SemanticPill(tone: PillTone.neutral)`，中性信息位 |
| `Card(elevation: 2, ...)` 成就卡 | :411 | → GraphiteCardSurface（去 elevation） | ✅ `GraphiteCardSurface(surfaceRole: card, padding: DS.md)`，Material elevation 移除，走 owner 描边+表面角色色；内边距保持原 DS.md 密度 |
| `OutlinedButton.icon(...)` 复盘钮（手写 styleFrom：brand 前景+0.4 描边+r14+p12） | :315 | → SparkleButton 家族 | ✅ `SparkleButton.outline(icon, label, expand: true)`，手写样式复刻整体删除，owner 正典样式接管 |
| `TextButton(` / `FilledButton(` | ——（报告旧行号 :156/:374） | → SparkleButton 家族 | ☑️ **wt176 重写后已消失**（当前 HEAD 零存量，如实记录） |
| `_MetricPill` / `_ModePill` 私有 pill 类 | ——（报告旧行号对应旧实现） | 更名入册 | ☑️ **wt176 重写后已消失**（`grep -rn` 全文件确认零定义零引用，无需更名）；exam 卡内同名的 `_MetricPill`(:740)/`_ModePill`(:1006) 属 wt177 已合入并基线登记的存量（parallelClass=2 冻结），不在本卡触碰范围 |

**sprint 面迁移后守卫账面**：rawChip 2→0 ✅；rawButton 0（见 §4-3 盲点申报）；parallelClass 0；colorLiteral 0；**rawSpinner=3 保留**（`LinearProgressIndicator` :277/:561/:652，改造 #5 已规范其色值口径；报告 #7 迁移清单不含 spinner，core/design 亦无进度条 owner 组件——LoadingIndicator 是加载态 owner，非进度位；按 ratchet 现值登记，留待有 owner 后清偿）。

### 1.2 exam_sprint_dashboard_card.dart（N1 sprint 面另一半）

wt177（SPEC-B）改造已合入且该文件本就在 `features/home/presentation` 守卫根内：基线与现值一致（rawButton=1 / parallelClass=2，冻结态）。本卡零改动、零新增违反。其剩余裸件按「ratchet 只降不升、触碰即迁」由后续卡清偿。

### 1.3 plan/presentation 其余文件（随扫描根入册的新 governed 面）

**本卡只登记、不迁移**（超出 #7 的 sprint 面范围，ratchet-on-touch）。新增 governed 存量（已冻结进基线）：

| 文件 | rawButton | rawSpinner | rawChip | parallelClass | colorLiteral |
|---|---|---|---|---|---|
| screens/diagnostic_quiz_screen.dart | 1 | 1 | 1 | 2 | 0 |
| screens/exam_sprint_setup_screen.dart | 0 | 0 | 4 | 0 | 0 |
| screens/growth_screen.dart | 0 | 1 | 0 | 1 | 0 |
| screens/learning_portfolio_screen.dart | 0 | 0 | 0 | 4 | 15 |
| screens/plan_create_screen.dart | 1 | 0 | 0 | 1 | 0 |
| screens/plan_detail_screen.dart | 4 | 3 | 0 | 4 | 0 |
| screens/post_exam_review_screen.dart | 0 | 0 | 0 | 0 | 6 |
| screens/sprint_history_screen.dart | 0 | 0 | 0 | 1 | 0 |
| screens/sprint_review_screen.dart | 3 | 1 | 0 | 1 | 0 |
| **screens/sprint_screen.dart（本卡迁后）** | 0 | 3 | 0 | 0 | 0 |
| widgets/plan_card.dart | 0 | 1 | 0 | 0 | 0 |
| widgets/plan_context_summary.dart | 0 | 3 | 0 | 0 | 0 |
| widgets/sprint_actions_dialog.dart | 3 | 0 | 0 | 0 | 0 |
| widgets/sprint_history_detail.dart | 0 | 1 | 0 | 0 | 0 |

（plan_edit/plan_history/sprint_completion 三文件与 learning_path_progress_bar.dart 零存量，不入 JSON。）

---

## 2. 守卫 / manifest / SPEC 文档改动（②）

| 文件 | 改动 |
|---|---|
| `scripts/guards/check_ux_component_convention.py` | ① SCAN_ROOTS +1 `"features/plan/presentation"`（带 N1/改造#7 依据注释）；② 模块 docstring「9 V3 canonical surfaces」→「9 + sprint 第 10 治理面（A-SPEC V1.1 N1 / 改造#7）」并同步扫描根描述 |
| `scripts/rule_guard_manifest.tsv` | **零改动**——UX-COMP 行（:75）按脚本路径调用，扫描根内聚在脚本里，manifest 无需刷新（已核） |
| `scripts/guards/ux_component_convention_baseline.json` | `--update-baseline` 现值登记：+14 个 plan 文件条目（§1.3 表）；sprint_screen 登记为迁后值（rawSpinner=3）；**既有条目逐一 diff 校验 = 零变化**；另有一处 stale 条目坠落，见 §4-2 |
| `v3-output/DL-R3/SPEC.md` | §0.2 增补第 10 治理面定义段（含必达项 ≤2 与守卫落点）；§8 标题注记 + 必达项矩阵 +sprint 行 + 新增 **§8.10 sprint**（两文件合称结构说明/必达/守卫/验收）；§9.1 守卫底座描述同步「10 治理面」 |

---

## 3. 冲突面声明（③）

本卡改动面 = `scripts/guards/check_ux_component_convention.py` + `scripts/guards/ux_component_convention_baseline.json` + `v3-output/DL-R3/SPEC.md` + `mobile/lib/features/plan/presentation/screens/sprint_screen.dart` + 新增 `v3-output/SPEC-GUARD/{REPORT.md,changes.patch}`。逐卡声明：

- **wt178（galaxy_screen/chat_screen + l10n）**：我不动 galaxy/chat 任何文件；**l10n 零新增 key**（复用既有 sprintDaysLeft/examDay/sprintEnded/sprintEndsOn/sprintReviewBtn），arb 零改动 → 文件级零重叠。间接交界面 = 基线 JSON（他们改 chat/galaxy 会使 counts 变化）与 DL-R3/SPEC.md（若他们同步 SPEC 文档），均按 §4 共享态纪律合并窗口统一定夺。
- **wt180（event_bus + 网关 Go + outbox）**：纯 backend/gateway 域，与我全部文件零重叠。
- **wt181（community + 迁移）**：community 文件与 DB 迁移均不在我改动面；community/leaderboard 不在 UX-COMP 扫描根（N1 明文「另立卡评估，本卡不动」），基线 JSON 不受其影响 → 零重叠。
- **wt182（reviewer/checkpoint/lifespan/scheduler）**：backend Python 域，零重叠。
- **wt183（纯研究）**：无代码交付，零重叠。

---

## 4. 诚实申报（④）

1. **基线 JSON 共享态处置**：按卡指令「worktree 内按 worktree 内基线登记，主会话合入时统一定夺刷新」执行——本 worktree 的 baseline JSON 已含 plan 根现值登记并跑绿；**主会话合入本卡后、且在 wt178 等 mobile 卡合入后，应在合并窗口重跑一次 `--update-baseline` 统一刷新**（与 A-SPEC 报告 #7「基线 JSON 按共享态纪律由合并窗口刷新」一致）。我登记的既有条目零变化已逐条 diff 校验，合并窗口重跑只会叠加各卡自己的 ratchet-down，不会冲突。
2. **--update-baseline 的一个副作用**：旧基线中 `chat/presentation/screens/chat_screen.dart` 条目被坠落——其在当前 HEAD 实测 counts 已全零（前序批次清偿后基线从未刷新，属 stale 条目）。坠落等价于「按零登记」，对该文件的守卫语义**严格更强**（回归即 NEW FILE 零容忍拦截）。该文件属 wt178 声明域，合并窗口刷新时以刷新时点现值为准即可。
3. **守卫 rawButton 正则盲点（发现未修，留后续卡）**：pattern 匹配 `OutlinedButton(` 但**不匹配 `OutlinedButton.icon(` / `.styleFrom`**——本次迁移的 :315 裸件在守卫账面上本就是 0（盲飞状态）。我已把该实例迁掉，但**未扩正则**：扩了会使全仓多面 counts 上涨、需动既有基线，超出本卡边界（且会撞 wt178 域）。建议后续卡池立一条「rawButton pattern 扩 `.icon` 变体 + 全基线刷新」。
4. **dart format 事故已自愈**：迁移后曾跑 `dart format`，新 SDK tall-style 把整文件重排（diff 膨胀到 448 行、且引入 1 条 require_trailing_commas 新 lint）。已 `git checkout -- <单文件>` 还原 HEAD 后手工重放三处迁移，最终 diff = +35/-40 干净面；文件内剩 2 条 analyze info（prefer_expression_function_bodies :120 / discarded_futures :321）**均为 wt176 既有同型代码**（:120 的 build 与 :321 的 `SensoryFeedbackService.emit` 闭包在 HEAD 原样存在），非本卡引入。
5. **fresh worktree 环境债**：wt184 首次跑测需 `flutter pub get` + `make proto-gen`（`mobile/lib/gen/` 为 gitignored 产物，proto 定义含 `GetArbitrationQueueStatsRequest` 而本地无生成物导致首跑编译失败）。均为 ignored 产物，未污染 tracked 面；主会话知悉即可。
6. **HEAVY 纪律**：单批定向测试（sprint_screen_test + router_smoke_test 一次 `flutter test --concurrency=1`），跑前 ps 实查 flutter/gradle 进程 = 0；未起任何模拟器；无 commit/push。

## 5. 验证记录

- `python3 scripts/guards/check_ux_component_convention.py` → **PASS** `rawButton=31/31, rawSpinner=22/22, rawChip=16/16, parallelClass=159/159, colorLiteral=121/121 (111 files)`（入册前为 FAIL 14 NEW FILE，符合预期路径）。
- 负向用例：向 plan/presentation 临时投放含 `Chip(` + `OutlinedButton(` 的 `_guard_probe_tmp.dart` → 守卫 FAIL 并点名 `NEW FILE ... rawButton=1, rawChip=1` → 已删除。
- `flutter analyze`（pub get 后）sprint_screen.dart：2 条 info，均为 wt176 既有同型（§4-4），净增 0。
- `flutter test --concurrency=1 sprint_screen_test.dart router_smoke_test.dart` → **+14 全绿**（6+8，零新增失败）。
- 邻近守卫无副作用：`check_ui_design_tokens_ratchet.py` PASS；`check_dl_spec_ratchet.py` PASS（其账面 offLadderDuration 182/184、gradientLiteral 302/303 的富余是既有基线态，与本卡无关）。

## 6. 收工核查（⑤）

- [x] 守卫跑绿 + 负向用例验证后探针文件已删（`_guard_probe_tmp.dart` 不存在）
- [x] `git status` 仅 4 个 tracked 修改 + 2 个新交付文件（本目录），无其它游离产物
- [x] `mobile/build`、`.dart_tool`、`/tmp` 探针与备份（`ux_baseline_before.json`、`sprint_screen_migrated_backup.dart`）收工删除
- [x] 未起模拟器、无残留进程、无 commit/push、主仓只读未动
- [x] 持久产物仅两类：本目录报告/patch + 正式代码改动（guards 脚本/基线/SPEC/sprint 面）
