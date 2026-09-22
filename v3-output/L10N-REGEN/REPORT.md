# L10N-REGEN 收工报告 — mobile l10n 生成工件格式漂移收口

- Worker: L10N-REGEN (V3 fleet) ｜ worktree: wt145 ｜ 基线: be10d59e
- 日期: 2026-09-23 ｜ 工具链: Flutter 3.41.3 stable (revision 48c32af034, 2026-02-27) / Dart 3.x
- 交付物: `v3-output/L10N-REGEN/REPORT.md` + `changes.patch`（1274 行，6 个文件）

## ① 漂移定性

**结论：真·纯格式漂移存在，本次已用本机工具链全量 regen 收口；另发现并修复一处 B3-CHAT 误删的 en 翻译（内容级，1 key）。**

- 漂移形态：gen-l10n 产出的 dart 工件中，多参数方法签名格式不同——仓内是 dart_style 新式逐参数换行 + 尾逗号，本机工具链产出旧式单续行。约 50 处方法签名，`git diff --stat` 合计 **+131 / -386**（净 ~255 行纯格式，与两张申报卡描述的 "~130 行" 同量级同形态）。无模板 hash、无 getter 集差异（见 ②）。
- 版本线索：`l10n.yaml` 未配置 header，工件无 generated 版本注释；工件格式与 Flutter 3.41.3 捆绑 dart_style 的输出比对为唯一证据。仓内格式是某个旧 dart_style 的产物（a1572cfa CP-01-MOBILE 曾做过一次它本机的 regen，但其工具链格式 ≠ 本机 3.41.3 格式）。
- 实验过程诚实记录：本 worker 第一次 `flutter gen-l10n` 在 fresh worktree（无 `.dart_tool/package_config.json`）产出与仓内**字节级一致**（md5 相同、mtime 已更新，排除 skip）；随后 `flutter analyze` 隐式 pub get 生成 package_config（02:10:07）后，第二次 regen 稳定产出新格式。即 gen-l10n 输出受项目 pub 解析状态影响，**fresh worktree 上第一次 gen-l10n 会对齐仓内旧格式、造成"零漂移"假象**——这解释了为何前序卡（CP-01-MOBILE manual regen + OVERLAY-SMALL 手工追加 getter）各自看到不一致的漂移判断。第三次 regen 复验字节稳定（幂等）。
- 禁区确认：regen 目标 `mobile/lib/l10n/*.dart` 全部 git 管辖内（`git ls-files` 证实）；gitignore 的 `mobile/lib/gen/` 是另一路径（gen-l10n 之外的工具产物），本卡未触碰。

## ② 红线面（regen 后 getter 集与 arb 完全一致）

- `app_zh.arb`（模板）11100 个 message key == `app_localizations.dart` 抽象类 11100 个成员，**双向差集为空**（python 脚本逐 key 比对）。
- `AppLocalizationsZh` / `AppLocalizationsEn` 各实现 11100 成员：missing=NONE，extra=NONE。
- 守卫复验通过：`L10N-REGEN-PARITY OK: 11100 template keys == abstract members; zh/en subclasses complete.`

### 附带发现并修复（内容级，1 行）：B3-CHAT 误删 en 翻译

`b7956f1c`（B3-CHAT，已入基线）重构时从 `app_en.arb` 误删 `"chatPredictionYouCanDoFirst": "You can start with: {action}"`（zh 侧保留），en 用户该串回退显示中文。属 l10n 目录内、与在途卡零冲突，已按 b7956f1c^ 原文恢复 + regen（en getter 从 zh 回退文本恢复为英文本文，`git diff` 中可见该 1 行内容变化）。修复后 gen-l10n 的 "en: 1 untranslated message(s)" 告警消失，守卫 WARN 归零。无测试 pin 该字符串（grep 证实）。

## ③ 冲突面（零交集声明）

在途卡全为 backend。本卡触碰文件仅 6 个：

| 文件 | 变更 |
|---|---|
| `mobile/lib/l10n/app_en.arb` | +1 行（复原 B3-CHAT 误删 key） |
| `mobile/lib/l10n/app_localizations.dart` | 纯格式重置（多参数签名紧凑化） |
| `mobile/lib/l10n/app_localizations_en.dart` | 格式重置 + 1 getter 文本复原 |
| `mobile/lib/l10n/app_localizations_zh.dart` | 纯格式重置 |
| `scripts/guards/check_l10n_regen_parity.py` | 新增守卫（纯 stdlib） |
| `scripts/rule_guard_manifest.tsv` | +1 行注册 `L10N-PARITY` |

## 防回退守卫（任务 3）

项目守卫体系有现成挂点（`scripts/guards/` + `rule_guard_manifest.tsv`，guards 以 `cd REPO_ROOT && PYTHON_BIN check_x.py` 运行，exit 0/1），故加了**轻量纯 stdlib 守卫** `check_l10n_regen_parity.py`，注册码 `L10N-PARITY`：

- 查：三工件存在；模板 arb keys == 抽象类成员；zh/en 子类实现完整。堵住"改 arb 不 regen"与"手工追加 getter 无 arb key"这两类语义漂移（正是前两张卡的劳损点）。
- 不查（诚实边界）：字节级格式同一需 `flutter gen-l10n`，超出守卫套件的纯静态依赖面——已在守卫 docstring 与本报告登记 CI 建议：CI 有 Flutter SDK 的 job 加一步 `flutter gen-l10n && git diff --exit-code -- mobile/lib/l10n`。
- 附带：非模板 arb 缺译打 WARN 不 FAIL（未译回退是合法 gen-l10n 行为）。
- 验证：直跑 + `run_all_rule_guards.sh --rule L10N-PARITY` 双通过；双变异测试（删 arb key → FAIL "abstract member without template arb key"；改子类成员名 → FAIL），单文件粒度改动 + `git checkout --` 还原，树状态前后比对无残留。

## 验证汇总（任务 2/4）

- `flutter analyze lib/l10n/`：**No issues found**（regen 后复跑仍 0）。
- 定向 l10n 测试（未跑全量，内存纪律）：`test/unit/i18n_service_test.dart` + `test/core/services/i18n_service_p2_10_test.dart`，`--concurrency=1`，**13/13 passed**（regen 后复跑仍绿）。
- regen 幂等：同状态下第三次 gen-l10n，三工件 md5 不变。
- 守卫：见上，全绿。

## ④ 诚实申报

1. 第一次 gen-l10n 的"字节级零漂移"结论是**假象**（fresh worktree 无 package_config 时输出对齐仓内旧格式），本报告以最终稳定态为准；该行为本身值得 flutter 层面留意。
2. en 翻译复原虽在授权面内（lib/l10n），但属计划外内容变更——已单列并给出来源 commit 证据（b7956f1c diff 的 `-` 行），主会话可选择只采纳格式重置部分。
3. 守卫堵语义漂移，不堵格式漂移；格式幂等守卫需 CI 带 Flutter SDK，未强行塞进本地守卫套件。
4. 未跑全量 `flutter test`（内存纪律）；格式变化理论上不影响运行时语义（纯签名排布），但未做 UI 级验证。

## ⑤ 收工核查

- [x] 主仓零写入（全程只读）
- [x] 无 git commit / push（交付 = patch + 报告）
- [x] `mobile/.dart_tool`、`/tmp/m3a`、`/tmp/m3b`、`/tmp/l10n_md5_*` 已清；`mobile/build` 未产生
- [x] 无模拟器/HEAVY 进程（全程 LIGHT：gen-l10n、analyze、2 个定向测试文件串行）
- [x] 变异实验均单文件粒度并已还原（`git status` 前后比对）
- [x] 未新增文档（仅本卡 `v3-output/L10N-REGEN/` 目录交付物）
