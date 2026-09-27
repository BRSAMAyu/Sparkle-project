# WT762-ORPHAN — V3-FIX-489/490 mobile 孤儿屏处置（wt753 猎缺移交）

- Agent: wt762 ｜ 分支: `agent/node-b/wt762/orphan`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt762-orphan`，基线 main@db2bc8ff）
- 日期: 2026-09-27（本机时钟）｜ 主线仓库只读 ｜ 证据输入: `v3-output/WT753-HUNT-MOBILE/findings.md` F1/F2
- 产物: 修码 commit `c5279fc4`（FIX-490）+ `050aa1fd`（FIX-489）+ 台账/notes docs commit（本分支第三 commit）
- 纪律: 删码面 100% 纯删 0 增（490=667 行、489=2636 行）；每子项独立"验证型红→绿"（删后全库 grep 零残留 + analyze 零告警 + 触达测试绿）；gen×3 手改同步（wt729 判例，理由见 §3）

---

## 1. V3-FIX-490（P4）处置=PURGE：`/settings/learning-mode` 孤儿路由全链删除

**登记面复核（全部对上，db2bc8ff 基线亲证）**：路由 `user_routes.dart:304` 注册即零入口；`git log -S "settings/learning-mode" -- mobile/` 仅 initial commit；类名 `LearningModeScreen` 全 lib 消费仅 barrel+routes；深链/间接导航/test 四向零命中。

**删除面（667 行纯删）**：

| 对象 | 行数 | 独占性证据 |
|---|---|---|
| `presentation/screens/learning_mode_screen.dart` | 166 | 登记面四向亲证零消费者 |
| `presentation/widgets/preference_controller_2d.dart`（级联孤儿） | 393 | 唯一 lib 消费者=被删屏 :112；唯一其他引用=a11y 守卫 allowlist 行（见下） |
| `user_routes.dart` 路由块 + import | ~15 | — |
| `user.dart` barrel export | 1 | — |
| a11y 守卫 allowlist 行（`a11y_semantics_label_quality_guard_test.dart`） | 3 | 该守卫第三用例"allowlist 条目仍真实存在"对已删文件直接 FAIL（防僵尸豁免），必须同步摘行 |
| 独占 l10n 键 7 枚 ×2 arb + gen×3 | 90 | learningModeSaved/SaveFailed/SettingsTitle/DragHint/DepthAxisValue/CuriosityAxisValue/Save 逐键 grep 零外部消费者 |

**保留面亲证（共享面零伤）**：`updateUserPreferences`（settings_provider.dart:597 活消费）、`UserPreferences` 实体（settings_provider/user_model）、`UserRoutes.popOrGoProfile`（4 屏消费）；`learningMode`/`learningModeSubtitle`（统一设置内联卡 :739-740）与 `learningModeDepthHigh/Low/CuriosityHigh/Low/DepthValue/CuriosityValue`（`learning_mode_control.dart`，被 unified_settings_screen.dart:758 挂载）全部保留——**产品等价面（统一设置内联学习模式卡）不受影响**。无 widget test 需删（test/integration_test 零引用亲证）。

## 2. V3-FIX-489（P3）wire-or-purge 裁决=**PURGE**：WS6 透明画像孤儿屏全链删除

**裁决证据链（四条，按任务要求的"设计文档+git 历史"双源）**：

1. **接线半步在两代仓库中从未发生**。本仓 `git log -S "profile/transparent" -- user_routes.dart` 空（wt753 亲证）；pre-reset 归档 `Sparkle-archive-20260915/mirror-backup.git` 全分支同零命中。flag 历史实证：归档提交 `31812c944` 引入 `kWs6ProfileSurfaceEnabled = false` → `831e79007`（2026-04-20，"feat(stage7): land WS-V2 transparency surface consumption"）翻 `true`——该提交 files touched 仅 screen/provider/models/repository/tests，**不含任何 routes/导航文件**。"落地消费"只到 provider+widget-test 层（widget test 直接挂载证明屏本身功能完好），导航可达层从未存在。
2. **WS-V2 设计意图已由另一张已接线屏承担**。归档设计文档 `docs/product/SPARKLE_AURORA_STAGE7_DISPATCH_PLAN_2026-04-19.md` §7.2 定义 WS-V2 目标="Turn the Stage 6 backend transparency loop into a real user-facing read/write surface on mobile"，验收=live mobile read path + correction/control submission path + tests proving the **visible** frontend loop。现行仓库中该意图由 `UserPersonaScreen`（`/profile/persona`，1724 行，user_routes.dart:142 挂载）承担：`transparentProfileProvider` 读 + `submitProfileCorrection` 纠正提交 + `updateTransparentPreference` 偏好更新 + `rollbackTransparentPreference` 回滚——读/写/回滚三面齐备。且**现行**设计文档 `docs/01_核心模块文档/用户画像系统深度对齐.md:511` 明指"产品页里的 `UserPersonaScreen`：透明画像总页"。WS6 屏是同能力的**第二套平行实现**；stage7 plan 原文 out-of-scope 恰好写着 "inventing a brand-new transparency product surface"。
3. **屏内文案自证未接线**。zh arb 原文 `userTransparentNotEnabledHint`="WS6 目前保持 inert，等后续路由或后端绑定补齐后再启用"——作者自己把接线列为未决前提。
4. **终门前保守取向**（任务明示）：10/7 截止前，"有 handler 无入口"的承诺控制面（标错/仅考试模式/回滚 UI 全套真实 POST）比死代码更伤；wire 一套重复透明画像面=赛前扩张 QA 面与叙事面（两处"透明画像"入口互相稀释）。

**删除面（2636 行纯删 0 增）**：屏 671（profile_transparent_screen.dart）+ ws6_profile_mirror_provider.dart + ws6_profile_mirror_models.dart + mirror_bar.dart（237）+ ws6_flags.dart + 2 测试文件（profile_transparent_screen_test.dart / ws6_profile_mirror_test.dart，9 用例）+ `user_repository.dart` `submitInsightControl` 方法（唯一消费者即该屏；其 fake override 在 user_persona_screen_test.dart 同步摘除，否则 `@override` 悬空编译失败）+ 独占 l10n 键 23 枚 ×2 arb（profTrans* 3 + userVisibleProfile/userMediatedProfile/userRevertible*/userCorrectionHistory*/userTransparent*/userSummary/userCurrentUnknowns/userNoContent/userExamModeOnly/userMarkInaccurate/userMarkNeedsRecalibration 等，逐键 grep 零外部消费者）+ gen×3 手改同步。

**保留面亲证（数据链活源不动）**：`transparentProfileProvider`/`profileInsightsProvider`（persona_view_provider.dart——UserPersonaScreen、session_refresh_service.dart:82、understanding_overview_provider.dart:335、persona_onboarding_screen.dart 活消费）；`fetchTransparentProfile`（GET `/profile/transparent`，user_repository.dart:71，transparentProfileProvider 数据源）；后端 `/profile/transparent`（profile_transparency.py:939）与 `/profile/insights/control`（:1596）端点原样（后端 API 面超本卡边界，POST 端点留作重做路径的写通道）；`ClientObservabilityService`（7 处他消费者）。**观测污染收口**：幻影路由遥测（`route: '/user/profile/transparent'` metadata）随 provider 一并删除——注意该遥测的真实触发条件是 provider 被 watch，而唯一 watcher 是不可达屏，故线上实为"污染配置"而非持续流量，登记面的"持续产出"按配置面理解收口。

**重做路径（留档，若产品将来要 WS6 镜像条透明视图）**：本修复提交原子包含屏+provider+models+mirror_bar+flags+tests 全套，`git checkout 050aa1fd^ -- <路径>` 即可整链恢复；随后 ①注册路由（建议 `/profile/transparent`，挂 user_routes + SceneAudioScope 同款姿势）②从统一设置"画像透明度"卡或 UserPersonaScreen 补导航入口 ③`ws6_profile_mirror_provider.dart` 遥测 route 串改真路径 ④`submitInsightControl` 从同提交恢复 ⑤恢复 2 测试文件。backend POST `/profile/insights/control` 端点健在，写通道无需后端改动。

## 3. l10n 同步方式取舍（对任务默认指令的一处偏离，附证据）

任务默认"动 arb 则 gen-l10n 再生"；本卡实跑 `flutter gen-l10n`（in-place，worktree 真项目）验证：重生成 diff = 删除键之外**另含全量 formatter 风格翻搅**（app_localizations.dart 241 行块、en 566、zh 287——checked-in gen 为旧版 dart format 风格，当前 SDK 重排缩进/尾逗号），与内容无关的 churn 会污染 diff 并与并行分支制造无谓冲突。按 wt729（V3-FIX-440，GOV-015 判例）"gen×3 手改同步、弃 gen-l10n 重生成"先例执行手改同步：两卡合计 abstract -150 行 / en -78 / zh -74，0 插入，i18n coverage 100% + gen 签名一致性由 analyze+测试背书。**留档**：gen×3 与当前 dart format 产出存在风格代差，未来若要做"重生成一次到位"需独立卡全量格式化收口（本卡不扩面）。

## 4. 验证实录（两提交后终态）

- `flutter analyze`：**No issues found**（两提交各跑一次）；gate `check_flutter_analyze_gate.py`：ERROR=0 / WARNING=0 / INFO=0 PASS——删除面零 lint 预算占用，allowlist 无需下调。
- 触达测试：a11y 守卫（3）+ full_route_coverage（116 路由，user routes ≥15 阈值内）+ wt422 l10n smoke + unified_settings×2 + features/user 全目录 57 用例 + user_persona_screen_test（fake 摘 override 后）+ understanding_overview_provider（transparentProfileProvider 消费方回归）7 用例——全绿零 FAIL。
- l10n 面：`i18n_coverage_check.dart` 100%（en/zh 双向）；`check_i18n_coverage.py` PASS；双 arb 删键后 JSON 合法；gen×3 与 arb 键集逐一对照零缺失（grep 0 残留）。
- 残留 grep：`learning-mode`/`LearningModeScreen`/`preference_controller_2d`/7 键名；`ProfileTransparentScreen`/ws6 全家/`MirrorBar`/`submitInsightControl`/`profile_transparency_binding`/`/user/profile/transparent`/23 键名——lib+test+integration_test+arb 全零命中。
- 台账：`ledger_union_merge.py --verify` → **336 行 V3-FIX 行，零 FAIL**（8 裸管形态合法、无重号、状态枚举合法）；489/490 置 FIXED@c5279fc4 / FIXED@050aa1fd。
- 新发现：**本卡零新缺陷登记**。499/500 预占号 grep 复核空闲（49x 在册 489-493），但执行全程（含删除面四向残留扫描与共享面逐键复核）未发现新缺陷，不虚占号；wt753 findings F3/F4（死资产/死 token，该卡明示"未占号"）仍留给收割批。

## 5. 环境注记（如实）

- worktree 新建后 `mobile/lib/gen/`（gitignore 的 protobuf 产物）缺失导致 analyze 25 errors（uri_has_not_been_generated 等）——从主线 checkout 同基线 cp gen 产物补齐（wt369/J-05 先例），非代码缺陷、不入库。
- 本机 darwin/arm64 未跑模拟器/真机；widget test 层面（含 9 个被删用例的功能等价性）由既有测试套件背书，与 wt753 同纪律：未跑真机如实标注。
