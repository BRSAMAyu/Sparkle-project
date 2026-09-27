# WT725 — V3-FIX-437 处置笔记（死 l10n 键 transparentMode 删键）

- 日期：2026-09-27
- 分支：`agent/node-b/wt725/deadkey`（base main@670b06ca）
- 处置：**A 删键**（登记复核成立，未触发 B）
- 代码 commit：`bdd64e4b`（fix(V3-FIX-437)）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-437 → FIXED@bdd64e4b

## 1. 处置前 grep 亲证（登记复核）

工作树 = main@670b06ca + cp gen（wt724 判例同款流程）。改动前全仓实查：

```
$ grep -rn "transparentMode" --include="*.arb" mobile/
mobile/lib/l10n/app_zh.arb:133:  "transparentMode": "透明模式",
mobile/lib/l10n/app_en.arb:133:  "transparentMode": "Transparent Mode",

$ grep -rn "transparentMode" mobile/lib mobile/test
（仅 6 类命中：arb×2 自身、gen×3 自身定义、settings_provider.dart:625 transparentModeProvider、
 unified_settings_screen.dart:515/:1949/:1955 —— 后者全是本地变量与 provider 名，非 l10n 读者）

$ grep -rn "\.transparentMode\b" mobile/lib mobile/test   # l10n 读者模式（排除 transparentModeProvider 词形）
0 命中
```

- `unified_settings_screen.dart:515`：`final transparentMode = ref.watch(transparentModeProvider);` —— 本地 Dart 变量；`:1949/:1955` 消费的是该变量。该屏真用的 l10n 键是 `enableTransparentMode`/`showStatusOverview`/`transparencyLevel`（FIX-421 已诚实化），与被删键无关。
- 测试钉值：`mobile/test` 唯一「透明模式」提及在 `chat_settings_screen_test.dart:36`，是 `find.text('进入透明模式的详细配置页面。')` 的**负断言 findsNothing**（异字符串，非本键值），不受影响。
- 结论：登记成立，纯死键，走处置 A。

## 2. 冻结键核验

49 冻结键 = FIX-182 `aurora*19 + visual*30`（W565_L10N_CLOSEOUT.md §3）。`transparentMode` 两前缀均不相交；§3.4 全清单 grep 无此键。零触碰。

## 3. 改动（bdd64e4b，14 行纯删 0 增）

| 文件 | 删除内容 |
| --- | --- |
| `mobile/lib/l10n/app_zh.arb` | :133 键值行 `"transparentMode": "透明模式",` |
| `mobile/lib/l10n/app_en.arb` | :133 键值行 `"transparentMode": "Transparent Mode",` |
| `mobile/lib/l10n/app_localizations.dart` | 抽象类 doc echo 5 行 + `String get transparentMode;` |
| `mobile/lib/l10n/app_localizations_zh.dart` | `@override` + getter |
| `mobile/lib/l10n/app_localizations_en.dart` | `@override` + getter |

gen 手改按 wt363/wt710/wt717/wt724 判例（gen-l10n 重生成会引入 intl 格式漂移全量噪声，弃用产物、手改与 arb 逐值同步）。无 `@transparentMode` 元数据键需删。

## 4. 验证（全部真实运行）

```
改后残留：grep "transparentMode" mobile/lib/l10n/          → 0 命中
         grep "\.transparentMode\b" lib+test+integration_test → 0 命中
键数：    app_zh.arb / app_en.arb  →  10086（= 10087 − 1，10087 口径随删键 −1）
analyze： flutter analyze → No issues found! (ran in 24.9s)
守卫：    L10N-REGEN-PARITY OK: 10086 template keys == abstract members; zh/en subclasses complete.
         [i18n-coverage] PASS — all presentation files with Chinese strings import i18n infrastructure
测试：    unified_settings_bgm + unified_settings_no_fake_confirm + settings_provider
         + chat_settings_screen + wt422_l10n_harvest_smoke 共 15 用例 → All tests passed!
```

- 无测试钉键数（wt422_l10n_harvest_smoke 不断言总量），无钉被删键值。
- 零行为变更：被删键无任何运行时读者。

## 5. 台账与收尾

- DYNAMIC_ISSUES.md V3-FIX-437 状态列：`OPEN` → `FIXED@bdd64e4b`（含验证实录）。
- 新发现：无（未占用 V3-FIX-439/440）。verify 守卫零 FAIL。
- 不 push；未碰主线仓库工作区。
