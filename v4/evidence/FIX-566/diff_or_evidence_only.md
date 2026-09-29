# FIX-566 · diff_or_evidence_only（红线自证）

任务卡：台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-566（P3，U07 一审 C-2/R-1）。
分支 `fix/v4/f566-retry-scroll-jump-latest`（wtF566），基线 `dd4de05a`（main 最新）。

## 产品码 diff（6 文件 +88/−7，`git diff dd4de05a..HEAD --numstat` 可复算）

| 文件 | ± | 内容 |
|---|---|---|
| `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | +72/−7 | ①retry 调用点收拢进 `_retryLastMessage()`（先 `_scrollToBottom(force: true)` 再 `retryLastMessage()`）；②`_showJumpToLatest` 字段 + `_handleScroll` 锚翻转帧同步 + 消息区 Stack 尾部「跳最新」胶囊入口（`Key('chatJumpToLatest')`，贴底/空态零面积） |
| `mobile/lib/l10n/app_en.arb` | +2 | 纯增量键 `chatJumpToLatest`="Back to latest" + `@` 元数据 |
| `mobile/lib/l10n/app_zh.arb` | +2 | 纯增量键 `chatJumpToLatest`="回到最新" + `@` 元数据 |
| `mobile/lib/l10n/app_localizations.dart` | +6 | gen-l10n 产物新增键抽象声明（纯增量） |
| `mobile/lib/l10n/app_localizations_en.dart` | +3 | gen-l10n 产物英文实现（纯增量） |
| `mobile/lib/l10n/app_localizations_zh.dart` | +3 | gen-l10n 产物中文实现（纯增量） |

新增测试 2 文件（+874 行，零既有测试修改）：
`mobile/test/widget/chat_f566_retry_force_scroll_jump_latest_test.dart`（4 测）、
`mobile/test/unit/chat_f566_retry_reuse_path_test.dart`（1 测）。

## 红线自证

1. **不改滚动跟随机制既有语义**：`ChatScrollAnchor`（chat_scroll_anchor.dart）零改动；
   `_scrollToBottom`/`_handleScroll` 的锚更新与 240px 门语义零改动——`_handleScroll`
   仅**新增**锚翻转帧的入口可见性 setState（读取 `shouldFollow`，不改写锚）；
   force 路径复用既有 `_scrollToBottom(force: true) → forceFollow()`，无第二套滚动权威。
   到达性滚动（assistant 到达/组件到达）门控表达式逐字未动（diff 可核）。
2. **arb 纯增量 + gen-l10n 再生且零既有键漂移**：arb×2 各 +2 行（键+元数据），零删改。
   本机 `flutter gen-l10n`（3.41.3/dart_style 2.3.2+）实跑两轮：
   - 裸 main 再生即对既有 gen 产物产生 **144+/50− 格式代差**（dart_style tall-style vs
     入库 short-style；多机车队入库 gen 产物出自旧格式器），**键集合零差**——
     故障为环境格式器代差而非键漂移；
   - 处置：gen 产物恢复 HEAD 后按再生输出摘取纯增量三处入库（+12 行），并用脚本断言
     入库文件与**完整再生输出**的 `String get/方法` 键集合逐文件相等（3/3 equal，见
     run_manifest.json `l10n_verification`）；arb 中英键集合相等（10267=10267）。
   此处置属 FIX-561 同款环境问题代行裁决，供 owner 复核。
3. **`flutter analyze --no-pub` 零 issue**：`No issues found!`（全仓，20.1s）。
4. **不改认证/授权**、无 backend/proto/迁移改动、无 Mock 冒充、密钥零接触。
5. **worktree gitignored 产物**：`mobile/lib/gen/`（proto 生成物）自主仓检出拷入以过
   analyze/test（gitignore 覆盖，不入库）；未改任何 `*/gen/` 受管产物（l10n gen 产物
   为**入库受管**文件，按上述第 2 条处置）。

## 差量举证（新测 5 测，全部真实可失败）

| 测试 | 面 | 钉住差量 |
|---|---|---|
| widget `F566① 正：中段阅读点「重试」强制回最新端` | ①screen 侧 | 播种纯连接失败态（用户消息末位+可重试错误）→ 上滑 600px（pixels=580）→ 点「重试」→ **offset==0**；无重复用户消息；入口隐藏 |
| unit `F566① 纯连接失败后 reuse 重试` | ①provider 侧 | 真实 send→ErrorEvent 失败 → `retryLastMessage()`（reuse=true）→ **用户消息仍恰 1 条**（不追加重复，B-01 语义保持）+ `isSending=true`（新 run 开启）+ 错误清除 |
| widget `F566① 反：到达性滚动不抢滚动` | ①反例 | 中段阅读中助手消息到达 → offset 逐位不变——补 force 未越权到到达路径（U07 核心语义原样） |
| widget `F566② 跳最新入口可见性` | ② | 贴最新端 `findsNothing` → 上滑 600px `findsOneWidget` → 滑回贴底（≤240）再 `findsNothing` |
| widget `F566② 跳最新入口点击` | ② | 点击入口 → offset==0 + 入口消失 + 消息零副作用 |

## mutation 自验（改后跑、录红、还原，未留痕）

- **M-①（精准）**：`_retryLastMessage()` 去掉 `_scrollToBottom(force: true)` 一行 →
  4 测中**仅 ①正红**，红在目标断言 `Expected: <0.0> Actual: <580.0>`（恰为 U07 C-2
  原始缺陷形态：点重试不回最新端）；①反/②×2 保持绿（补 force 不误伤他面）。还原后 5/5 绿。
- **M-全量**：`git stash` 整个产品 diff → 4 widget 测全红（各自断言「入口/force」在场性）；
  stash pop 还原后 5/5 绿。两组红证共同钉死：新测非恒绿、差量真实由本 diff 携带。
