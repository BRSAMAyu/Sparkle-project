# V4-Q06 · 独立审查 R1 receipt

- 审查人：R1（独立未参与会话）
- 审查日期：2026-09-28
- 审查基线：`agent/v4/q06` 证据提交 `83247329`（base `f13a21ef`，state 提交 `2a3c1bd4`）
- 审查方式：矩阵真实复跑 + 零产品码 diff 全量核验 + 3 格 mutation 判别力抽验（改红还原绿）+ 六项预登记挑战逐项裁决 + 证据完整性抽查
- 约束遵守：零产品码改动；探针全部还原（终态工作树干净，测试文件 sha256 与登记一致 `9d052f98…f1c7`）；本提交为分支上唯一追加的 receipt 提交

## VERDICT: PASS_WITH_CHALLENGES

**理由（evidence_verdict 建议值 = PASS_WITH_CHALLENGES，最终回写由 leader 执行）**：三条卡验收在申明层级（调用级/语义级/widget 级）全部可复现通过——矩阵 58/58 复跑 exit 0、services 域 142/142 复跑 exit 0；零产品码 diff 经全量核验属实（仅 1 个新测试文件 + 证据目录，pubspec/lib/backend/gateway/proto/scripts 零 diff，无 ignore 豁免）；3 格独立 mutation 全部"改必红、还原必绿"，证明套件非恒真、逐格可失败成立。未给干净 PASS 的原因：C4 列 9 格中 6 格的可执行断言实质薄弱（靠 M-R1-C4/M-R9-C4 锚点引用 + GAP 登记承载），且集成链缺口本体未清偿；另有个别证据字段映射与 C6 列机制重叠的 P2 项（见发现列表）。缺口披露诚实完整（逐格 boundary_note + limitations L2 + value 不标 PASS），不构成 FAIL 事由。

## 裁决逐项

### R1-C2（C4 列 PASS+GAP_INTEGRATION vs FAIL）——裁决：缺口登记足够，不应改记 FAIL

依据：①卡面 acceptance 三条原文（静音可完成/replay 不重播/DEVICE_UNVERIFIED 口径）均不含 background 列行为；objective 是"全量测六态"，本交付对 C4 列做了真实测量并如实分账——装饰停止面（`AnimationLifecycleMixin` didChangeAppLifecycleState 实测暂停/恢复 + `_BgmLifecycleObserver` 源码锚 + STOPPED_BY_USER 不自续 M-R9-C4 实测）调用级 PASS 属实，事件链可见性门经本审查实证确缺（`present(Map, {String? currentSubjectVersionToken})` 无可见性入参，adapter 内零 AppLifecycle 引用）。②缺口为 S03-L5/D01/B05/FIX-569 预登记的 contract-owner 面，path_policy 明令"契约由单一 owner 单独合并"，验证卡无补实现权限；在该边界内"能测的测、不能测的登记"是唯一合规形态。③披露链完整：9 格逐格 GAP_INTEGRATION、diff 文档脚注、limitations L2、value_claim 不标 PASS。记 FAIL 反而会错划责任面（把集成链缺口记到验证卡头上）。**但保留挑战**：该列不能按"9 格独立证据"计（见 P2-1），集成 SHA 复验时须按台账确认缺口仍在 contract-owner 面待清偿。

### R1-C4（R5 行 progress_delta + evidence.registered copyKey）——裁决：不构成自造第二契约

实证：`evidence.registered` 是冻结文案表既有键（`experience_feedback_adapter.dart:55`，且与 backend `experience_copy.py:58` 逐键镜像——跨栈单一契约）；kind 词表封闭七元集内 progress_delta 为真实 kind；非成功面孔 kind → presentNeutral 是适配器真实路由（adapter:254-257），copyKey 是 `presentation.copyKey` payload 字段经 `kExperienceCopyTable[event.presentation.copyKey]`（adapter:225）取文案。测试只消费既有路径，无词表扩展、无第二表。防御成立。

### R1-C5（无真机且模拟器 App 面 NOT_RUN）——裁决：对验收矩阵卡足够

卡面原文"无真机只签模拟器层"；V4_DONE 判例"音触只测到调用时注明边界"。limitations L1 如实登记模拟器 App 安装面 NOT_RUN 及理由：本卡可验证面（决策/门控/通道计数/静态分支）在 flutter test 层已全覆盖，模拟器 App 上同样只有调用级可观测（无马达/无听感判断位/事件链无生产流量），不存在未覆盖的可证增量面；全部真机硬件面（触感舒适度/扬声器听感/OS 中断事件源/系统总开关/Android<30 平台效果）逐格 DEVICE_UNVERIFIED，全文无"舒适度已通过"表述（验收③口径纪律经全文扫描属实）。矩阵套件即 L3 复验工具。注："模拟器层"在本证据中定义为 flutter test 层口径（L3 明示），严于字面的 iOS 模拟器 App 运行未执行——已登记、有理由、有复验工具，判可接受。

### R1-C3（C6 列口径）——裁决：成立

C6 列的可区别内容经逐格核实：M-R1-C6 nativeFeedbackAlready（框架已有触觉不叠加双震）、M-R3-C6/M-R6-C6 诚实降级位（0 声音不连锁蜂鸣）+ 不连坐（触觉偏好开照发一枚）、M-R9-C6 缺省关=未点播不发声的对偶 + 降级位，M-R2-C6/M-R8-C6 结构性零出口。与 C2 列（显式关闭后决策/文案/徽章全同 + 物理 0 调用）断言面向不同。保留口径注记见 P2-4（R4/R5/R7-C6 与 C2 机制重叠），不构成偷换：产品触觉同意模型即 opt-in，"无同意=偏好未开"是真实拒绝路径，且这些格断言了文本信息不丢（不连坐面）。

### R1-C1（验证卡零产品码是否"没干活"）——裁决：满足 objective

no_duplicate_rule 原文"当前仓库已满足本卡行为时做差量举证，不重写"——乐谱行为面由 S01/S02/S03 已合并实现承载，本卡差量 = 54 格从"各锁面局部已钉"升格为"全矩阵逐格可失败证据"（本审查以 3 处 mutation 独立证实可失败性）+ C4 列缺口暴露 + DEVICE_UNVERIFIED 边界声明。这正是 kind=verification 的本职形态；零产品码是正确形状而非缺位。

### R1-C6（首跑 15 败+1 败后修复装置再全绿）——裁决：无掩盖

raw/matrix_machine.jsonl 经核为最终文件状态复跑实录（59 testDone / 59 success / 0 失败 / 0 跳过 / done success:true），非首跑版本；limitations L8 如实登记修复过程且归因装置侧。本审查 MU3 在事件构造器复现了历史缺陷类别（`??` 吞掉显式 null 回执）→ M-R6-C1 立即红（Expected ignoredInvalid / Actual presentSuccess）——证明修复后的套件对该缺陷类别有真实捕获力；断言零删除（mutation 删除类探针未发现任何格因删断言而失去判别锚）。

## 发现列表

| # | severity | 位置 | 发现 | 复现 |
|---|---|---|---|---|
| 1 | P2 | mobile/test/core/experience/sensory_matrix_q06_test.dart:385-391,504-514,733-737,849-853,992-995 | C4 列 R2–R7 六格可执行断言薄弱（多为预算表合规/结构注记），格的 PASS 实质靠 M-R1-C4（widget 级生命周期）与 M-R9-C4（音频焦点）锚点引用 + GAP_INTEGRATION 登记承载。逐格 boundary_note 已如实标注，非冒充；但集成复验时该列应按"2 格独立行为证据 + 7 格登记"计，不得宣称 9 格独立全证 | `flutter test … --plain-name "M-R3-C4"`（仅预算表断言，缺 GAP 也会绿——GAP 由文档面承载） |
| 2 | P2 | v4/evidence/V4-Q06/run_manifest.json | evidence_required#2 build_id 无显式字段，仅以 toolchain（flutter 3.41.3 / 48c32af034、dart 3.11.1）代偿。零产品码卡无构建产物，代偿可接受，但字段映射宜显式写"build_id=不适用（无构建），以 toolchain 版本标识运行面" | `grep -n build_id v4/evidence/V4-Q06/run_manifest.json`（无命中） |
| 3 | P2 | v4/evidence/V4-Q06/run_manifest.json | evidence_required#7 screenshots_if_ui：无截图。本卡无新 UI 交付物、widget 级用例只消费 S01/F02 既有 UI，条件判不触发可接受；宜显式注记"本卡无 UI 交付物，截图项不适用"以防后续审查误判遗漏 | `ls v4/evidence/V4-Q06/`（无截图文件） |
| 4 | P2 | mobile/test/core/experience/sensory_matrix_q06_test.dart:664-680,754-764,1021-1038 | C6 列 M-R4-C6/M-R5-C6/M-R7-C6 与 C2 列同用 userPreferenceOff 机制，区分度靠"拒绝面/不连坐"框架；因产品同意模型为 opt-in 判成立，但同机制双列计 54 格分母略有口径膨胀（不影响三条验收结论） | 对照 M-R4-C2 与 M-R4-C6 断言面 |

## 证据完整性核验记录

- artifacts_sha256.txt 抽 3 项亲核一致：测试文件 `9d052f98…`、test_results.json `709b8c7a…`、matrix_machine.jsonl `558d4f15…`（shasum -a 256 实测 = 登记）。
- matrix_machine.jsonl 为最终态复跑：0 失败、0 跳过、`"success":true,"type":"done"` 收尾；与 limitations L8"最终文件状态复跑"声明一致。
- evidence_required 八字段逐项对 tasks.json 卡面核验：source_sha ✓（base 全 SHA+实测注；head 见台账）、build_id（见发现 2）、commands_and_exit_codes ✓（9 条命令带 exit code）、scope_and_denominator ✓（9×6=54，逐格 cells）、artifacts_sha256 ✓、actual_model_and_usage_if_llm ✓（NOT_EXPOSED 如实）、screenshots_if_ui（见发现 3）、physical_device_scope_if_sensory ✓（五项 DEVICE_UNVERIFIED 面枚举 + physical_device=无）。锁 qa-sensory NOT_RUN 如实登记（L6：协调远端本机未配置），无伪造。
- 零产品码核验：`git diff --stat f13a21ef..83247329` 全量 = 1 测试文件 + 11 证据文件，4004 insertions、0 deletions；`git diff f13a21ef..83247329 -- mobile/pubspec.lock mobile/pubspec.yaml mobile/lib backend gateway proto scripts` = 空；测试文件无 `// ignore:` 豁免。

## 命令与 exit code 清单（R1 实录）

| # | 命令 | exit code | 结果 |
|---|---|---|---|
| 1 | `git status` / `git log --oneline -5`（wtQ06） | 0 | 树干净，HEAD=2a3c1bd4 |
| 2 | `git diff --stat f13a21ef..83247329` | 0 | 12 文件全为测试+证据 |
| 3 | `flutter test test/core/experience/sensory_matrix_q06_test.dart` | 0 | 58/58 全绿（复跑） |
| 4 | `flutter test test/core/services/` | 0 | 142/142 全绿（回归抽验） |
| 5 | MU1（记录器删 SystemSound 记账）`flutter test … --plain-name "M-R3"` | 1 | 红：M-R3-C1 Expected ≥1 / Actual 0 |
| 6 | MU1 还原 `git checkout -- <测试文件>` + sha256 复核 | 0 | 与登记一致 |
| 7 | MU2（R6-C3 删新事件独立 event_id）`flutter test … --plain-name "M-R6-C3"` | 1 | 红：Expected presentSuccess / Actual replaySuppressed（:846） |
| 8 | MU2 还原 | 0 | 树干净 |
| 9 | MU3（构造器 `??` 吞显式 null，复现历史装置缺陷）`flutter test … --plain-name "M-R6-C1"` | 1 | 红：Expected ignoredInvalid / Actual presentSuccess（:801） |
| 10 | MU3 还原 + 终态全量 `flutter test test/core/experience/sensory_matrix_q06_test.dart` | 0 | 58/58 全绿；`git status` 干净；sha256 `9d052f98…` 与 artifacts_sha256.txt 一致 |
| 11 | `shasum -a 256`（3 证据原件） | 0 | 与 artifacts_sha256.txt 逐字一致 |

## 移交 leader 的回写项

1. evidence_verdict 建议 = **PASS_WITH_CHALLENGES**（本文件为唯一依据源；review_receipt.json review_state 由 leader 回写 REVIEWED）。
2. 4 项 P2 均不阻塞销账；P2-1 须转记到集成 SHA 复验清单：C4 列按"缺口在 contract-owner 面（FIX-569）待清偿、矩阵套件零改动复验"跟踪。
3. state.json 中 V4-Q06 的销账条件不变：本 receipt + 集成 SHA 可失败复验。
