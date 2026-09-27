# WT724-HONEST421 notes — V3-FIX-421 修案 C 文案诚实化（按 wt721 复核裁决执行）

- Agent: wt724（node-b 实现卡；主线仓库只读，本分支 `agent/node-b/wt724/honest421`，base main@5d3808cf = wt721 复核提交，worktree `Sparkle-sysrev/wt724-honest421`）
- 日期: 2026-09-27
- 代码 commit: **7ee8d61c**（arb×2+gen×3+消费点 1 行；台账/notes 见后续 docs commit）
- 裁决依据: 台账 V3-FIX-421 行「复核@wt721」注记 + v3-output/WT721-VERIFY2/notes.md（DOWNGRADED P2→P3 + 推荐修法 C 文案诚实化）

## 1. 改前/改后对照（3 处，全部值级/显示文本，零行为变更）

| # | 位置 | 改前 | 改后 |
|---|---|---|---|
| 1 | `enableTransparentMode` 标题（arb:134 / gen zh:405 / gen en:427 / 消费 unified_settings_screen.dart:1947） | zh「启用透明模式」/ en "Enable Transparent Mode" | zh「画像透明度」/ en "Profile Transparency" |
| 2 | `showStatusOverview` 副标（arb:135 / gen zh:408 / gen en:430-431 / 消费 :1948） | zh「显示状态与资源消耗概览」/ en "Show status and resource consumption overview" | zh「控制你的画像与洞察披露的详细程度」/ en "Controls how much of your profile and insights is disclosed" |
| 3 | 等级下拉 0 值标签（unified_settings_screen.dart:1969） | `Text(l10n.cancel)`（「取消」） | `Text(l10n.close)`（「关闭」） |

- 另：抽象类 `app_localizations.dart` 两键 doc echo（:890/:896）同步手改（gen-l10n 重写面）。
- 措辞打磨说明（不扩面、不引入新承诺）：裁决建议词「控制你的画像与洞察对外披露的详细程度」中的「对外」撤下——wt721 实证 gating 发生在用户**自有**画像/洞察视图（GET /profile/transparent、/profile/context、/profile/insights 三端点 payload 裁剪），非对他人披露；用「对外」会制造新失真。en 侧同口径（disclosed 不指明对象）。
- `transparencyLevel`（透明度级别/Transparency Level，:136）值准确不动；`transparentMode`（:133）零消费不动（见 §4）。

## 2. 判例执行（wt710 4ecf5d71 / wt717 b02528fc）

- arb×2 + gen×3 外科手改：共 6 文件 11 行改 11 行 + 消费点 1 行改 1 行；键名/键数/占位符零改动。
- `flutter gen-l10n` 重生成弃用（intl.selectLogic 格式漂移全量噪声，wt363 判例一脉），gen 手改与 arb 逐值同步，L10N-REGEN-PARITY 互证通过。
- 49 冻结键（FIX-182 aurora\*19 + visual\*30）与改动键（enableTransparentMode/showStatusOverview）前缀不相交：diff 全文 grep aurora|visual 零命中，零触碰。

## 3. 前后 grep 对照（归零证据）

改后（7ee8d61c 工作区实录）：

- 失真承诺句 `显示状态与资源消耗概览|Show status and resource consumption overview`：mobile 全仓（lib+test+gen 含 doc echo）**0 命中**（改前 4 处：arb×2+gen zh/en+抽象类 doc echo）。
- 旧标题 `启用透明模式|Enable Transparent Mode`：mobile 全仓 **0 命中**。
- `l10n.cancel` 误用：unified_settings_screen.dart 内现仅 2 处 `l10n.close|l10n.cancel`——:1969 已改 `l10n.close`，:2339 为真取消语义不动（裁决范围外）。

## 4. 范围外新发现（不扩面，登记 V3-FIX-437）

死 l10n 键 `transparentMode`（透明模式/Transparent Mode，arb:133）：`l10n.transparentMode` 全仓 0 消费。unified_settings_screen.dart:1949/:1955 的 `transparentMode` 是同名本地变量（transparentModeProvider 派生），非 l10n 读者；mobile/test「透明模式」钉值仅 chat_settings_screen_test.dart:36 负断言（异字符串）。已按备用号规则登记 V3-FIX-437（P4，437 亲证台账空闲，438 未动）。

## 5. 验证（全部真实运行）

```
cd mobile && flutter analyze
  → No issues found! (ran in 28.6s)

python3 scripts/guards/check_l10n_regen_parity.py
  → L10N-REGEN-PARITY OK: 10087 template keys == abstract members; zh/en subclasses complete. (exit 0)

python3 scripts/guards/check_i18n_coverage.py
  → [i18n-coverage] PASS — all presentation files with Chinese strings import i18n infrastructure (exit 0)

flutter test test/widget/unified_settings_bgm_test.dart test/widget/unified_settings_no_fake_confirm_test.dart \
  test/features/user/presentation/providers/settings_provider_test.dart test/widget/user_persona_screen_test.dart
  → 00:02 +14: All tests passed!

flutter test test/app/router_smoke_test.dart
  → 00:05 +8: All tests passed!
```

设置屏钉值预检：mobile/test 对旧值四串（显示状态与资源消耗概览/Show status.../启用透明模式/Enable Transparent Mode）改前 grep 0 命中——纯文案零测试连带，实录与预判一致。

## 6. 残留与移交

- 本地 `transparencyLevelProvider` int 值仍无本地读者（仅服务端同步载体+显隐派生）——架构双轨 known debt，wt721 已声明，不另立卡。
- V3-FIX-437（transparentMode 死键）OPEN 待排。
- 本分支未 push；集成收账时按「集成即纠指针」惯例补集成 SHA。
- 台账 verify：`ledger_union_merge.py --verify` 通过（310 行 V3-FIX，8 裸管形态合法，零冲突零重号）。
