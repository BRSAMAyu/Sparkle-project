# FIX-581 R1 独立审查 receipt（2026-09-29）

- 审查人：独立审查员 R1（未参与实现；实现为前任 agent 机制层 + leader 配额接管收尾）
- 被审：代码 `09cbe541`（2 代码/测试文件 + 6 证据文件，+457/−21）｜合入 merge `188264fb`｜审查基线 main `3528623a`
- worktree：`/Users/brsama/code/GitHub/Sparkle-project`（main，只读代码 + 本 receipt）
- 资源红线遵守：全部 `flutter test --concurrency=1`；双 mutation 均已 `git checkout --` 还原，审查结束工作树干净（`git status --porcelain` = 0 条目）；盘 34G 充足未清缓存。
- 修后漂移核验：`git diff 09cbe541 HEAD -- mobile/test/goldens/b04_visual_baseline/` 为空——审查对象即当前合入态，无后续提交触碰。

## VERDICT: PASS_WITH_CHALLENGES

七靶全部亲验成立：本地口径零变化红线守住、系数算术全对、双 mutation 红绿亲复现、机制测试牙齿经 mutation 实证、审计兜底结论独立复核为真、CI54 终证第一轮达成（golden 全绿、失败仅 G05 旧钉）。三处挑战（C1 审计扫描方法盲区、C2 审计表点名不全、C3 GITHUB_ACTIONS 本机误设边缘）不推翻修法，转后续观察/流程改进。

## 逐靶结论

1. **本地口径零变化（红线）— PASS**：`git show 09cbe541` 逐 hunk 核：compare() 判定由 `diffPercentTolerance` 改经 `effectiveTolerance` 间接——本地路径取值链 `b04InstallTolerantComparator()` 无参（三消费面 g01:41/g06:147/b04_capture:32 全缺省）→ `localTolerance=diffPercentTolerance` → `b04GoldenTolerance` 非 CI 分支原样返回，本地生效阈值恒 0.005，与 base 逐字节等值（机制测试亲跑打印实证 `本地(local)= 0.005`）。带界含等号语义未动（`<=`）。本地行为实证：g01 golden 本地亲跑 2 组全绿（基线 8 枚在库）。两点如实登记：throw 形态 `FlutterError→TestFailure` 同样作用于本地失败路径——这是声明的附带修复本体（修前本地经 expectLater 同样被吞错位），非隐藏放宽；`GITHUB_ACTIONS` 在本机被误设时本地静默切 CI 带（见 C3）。
2. **系数推导复核 — PASS**：算术全对：锚点 8227px/1,316,640（780×1688）= 0.625% ≈ 0.62%（CI53 原始摘录逐字在案 `v4/evidence/FIX-581/ci53_failure_excerpt_raw.txt`）；下界 0.0062/0.005 = 1.24；1.5× → 0.75%，余量 (0.75−0.62)/0.62 = 20.97% ≈ 21%；2.0× → 1.0%，余量 (1.0−0.62)/0.62 = 61.29% ≈ 61%；V3-FIX-383 判例 49% 布局崩坏被 1.0% CI 粗门拦截成立（49% ≫ 1.0%），0.18% 环境漂移仍在带内。单实锚局限诚实：L1（0.5–1.0% 残留放行带）、L2（单实锚+漂移再红重推条款）、L3（dusk/quiet 暗档未观测，正是弃 1.5 取 2.0 的论据）均在 limitations.md 登记。0.62% 实锚 + 未观测档余量论证链完整。
3. **mutation 亲复现 — PASS**：M1（拔 CI 分支恒本地口径，harness `b04GoldenTolerance` 体改写）→ 机制套件 **+8 −3 红**（常量钉 `Expected:<0.01> Actual:<0.005>`、CI 语义 0.62% 判过、CI 语义 1.0% 等号三红）；M2（`throw TestFailure` 回退 `throw FlutterError`）→ **+6 −5 红**（四处 TestFailure 形态断言 `Expected:<Instance of 'TestFailure'> Actual:<FlutterError:...Pixel test failed...>` + matchesGoldenFile 全链路归属钉）。各 `git checkout --` 还原后树净自证（porcelain 0 条目）、复绿 **+11 All tests passed**。与 run_manifest 声称一致。
4. **机制测试质量 — PASS**：6→11 张 testWidgets（新增 5 张：CI 0.62% 过/本地同帧 0.62% 挂/CI 1.0% 等号过/CI 1.1% 挂/投递归属钉；manifest "+11" 系通过计数非新增数，见 O1）。牙齿实证：两态钉经 M1 命中、形态与归属钉经 M2 命中；带界含等号双覆盖（本地 0.5%/150px 原有保留 + CI 1.0%/300px 新增）。合成消费方式抽查：golden=纯白 `_encodeImage(0)`，候选=白底+N 红像素，diffPercent=N/30000 精确确定，落盘走系统临时区不触碰仓库基线——无 vacuous pass 面。本地口径 0.005 常量钉（`expect(diffPercentTolerance, 0.005)`）原样保留。
5. **审计完备性 — PASS 附 C1/C2**：独立全仓扫（`grep -rl matchesGoldenFile` + 补扫 `screenMatchesGolden`）得 **16 个 golden 消费面**，逐一核保护：B04 比较器家族 4（capture/g01/g06 + harness 基建，本修覆盖）、Linux 显式 skip 4（v4_g02 semantic/chat_golden/p2_07_i18n/chat_design_language_widgets）、env 门控 8（emotion/notification/i18n p2_08/dashboard/accessibility×2/u02/q03 harness）；`golden_family_drift_guard.dart` 为辅助库无直接比对、其单测无真实 golden。**UNPROTECTED=0 独立复核成立**。i18n_p208 定位为 `i18n_batch_p2_08_golden_test.dart`（env 门控）。方法面挑战见 C1，表点名覆盖面见 C2。
6. **CI54 终证定性 — PASS**：`gh run view 36557731278`（head `cb3e4a69`，job 109373005934）全量日志（36511 行）亲读：Flutter Tests 唯一 ❌ = `g05_family_four_style_test.dart`「B｜修复点 widget 级钉（classic 管道）认知定式卡：描述/页脚/方案/类型标签走语义文本槽」颜色钉（:919，Expected 方案色 vs Actual 灰 0x171717）——即「G05 旧钉」，非像素比对，已由 `e694242d` 对齐 G03 真源。golden 面在 Linux runner **全 ✅**：g01 四风格 golden ×2 组、g06 ×2 组、b04 capture 三视口档、b04 机制套件——CI53 红面（g01 paperDay）不再红，**终证条款第一轮达成**。诚实注记：run 整体红另有 Backend Tests shard 1/3（FIX-585 stuck_journey，他卡同批已修），与 golden 终证无关。
7. **遗留条款可执行性 — PASS**：runner 漂移再红重推条款可执行——失败消息自带实测百分数（CI53 摘录 `Pixel test failed, 0.62%, 8227px` 即格式实证），新实锚可直接读取；系数为单命名常量 `kCiGoldenToleranceScale`，机制测试双钉（scale==2.0、CI 界==0.010）强制重推走显式治理变更而非静默改值；L2 终证定义「CI54 及后续自然轮不再红」第一轮已兑现。

## 编号发现

- **C1（MEDIUM，流程改进）**：audit.md 兜底扫描**方法面盲区**——只 grep `matchesGoldenFile`，golden_toolkit 系 `screenMatchesGolden` 辅助不落该 pattern。本轮结果不受影响（R1 补扫：3 个 screenMatchesGolden 用户 emotion/p2_08/accessibility 全 env 门控，UNPROTECTED=0 不变），但未来新增 screenMatchesGolden 消费面会从兜底网漏过。建议后续审计双 pattern 并扫。
- **C2（LOW）**：audit.md 表格逐名点 11/16 消费面；5 个受保护文件未单独列行（accessibility_settings_screen_test、accessibility_settings_golden_test、u02_dual_mode_evidence、q03_visual_qa/q03_harness、chat_design_language_widgets），依赖兜底语句兜住。结论正确，登记粒度建议补齐。
- **C3（LOW）**：`b04RunningOnCi` 以 `GITHUB_ACTIONS` 变量存在性检测——本机误设（act 容器、复制 CI env）时本地语义静默切 CI 带 1.0%。F579 同型检测先例、文档已声明语义，登记为已知边界即可。
- **O1（INFO）**：run_manifest "0 (×2, +11)" 的 "+11" 是 flutter test 通过计数（6→11，实际新增 5 张 testWidgets），易误读为增量数。
- **O2（INFO）**：M1 红在 CI 测试内 `effectiveTolerance` 钉层触发（`expect(effectiveTolerance, 0.010)` 先于像素判定）而非像素判定层——构造上判定与钉同源常量（kCiGoldenToleranceScale），无「钉过判定不过」的逃逸面。
- **O3（INFO）**：审查期间独立复算 analyze = 6 issues，与 run_manifest「6 issues（基线 8，新增 0）」当前值一致。

## 最大风险判断

残留最大风险是 **L1 的 0.5–1.0% 真实微回归在 CI 放行带**（本地签发机 0.5% 严门是唯一补偿，依赖签发纪律），叠加 runner/Flutter 版本漂移把跨机差推过 1.0% 的再红面（每轮成本 = 全舰队银行推送阻塞）。两者均有登记条款且重推路径可执行（失败消息自带新实锚），当前无产品码缺陷，无阻塞性发现。

## 命令与 exit code 清单（R1 亲跑，2026-09-29，main worktree/mobile）

| # | 命令 | 结果 | exit |
|---|---|---|---|
| 1 | `git status` / `git log` / `df -h` | clean；head `3528623a`；盘 34G | 0 |
| 2 | `git show 09cbe541`（harness + 机制测试全 diff） | 逐 hunk 核毕 | 0 |
| 3 | `grep -rn b04InstallTolerantComparator` / `grep -rl matchesGoldenFile|screenMatchesGolden` 全仓 | 消费面 3 + 全仓 16 面全保护 | 0 |
| 4 | `flutter test b04_tolerant_comparator_test --concurrency=1` | **+11 All tests passed**；打印本地 0.005/CI 0.01 | 0 |
| 5 | `flutter test g01_four_style_golden_test --concurrency=1` | **+2 All tests passed**（本地严格口径不变） | 0 |
| 6 | MUTATION-M1（拔 CI 分支）→ 同 #4 | **+8 −3 红**（常量钉/CI0.62%/CI1.0%） | 1 |
| 7 | `git checkout -- b04_harness.dart` + porcelain | 树净 0 条目 | 0 |
| 8 | MUTATION-M2（TestFailure→FlutterError）→ 同 #4 | **+6 −5 红**（形态+归属钉） | 1 |
| 9 | 还原 + 复跑 #4 | **+11 复绿**；porcelain 0 | 0 |
| 10 | `flutter analyze test/goldens/b04_visual_baseline/` | 6 issues（与 manifest 一致） | 0 |
| 11 | `gh run view 36557731278 --json jobs` + job 109373005934 全量日志 | 唯一 ❌ G05 旧钉；golden 全 ✅ | 0 |
| 12 | `git diff 09cbe541 HEAD -- …/b04_visual_baseline/` | 空（无修后漂移） | 0 |
