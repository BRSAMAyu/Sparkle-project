# Sparkle 国际化全面修复工作文档

> **日期**: 2026-04-28
> **目标**: 确保中文为默认状态时所有文本地道中文；英文模式下零中文残留，体验完整地道
> **原则**: 不破坏现有逻辑和流程；每阶段独立可验证；并行 agent 最多 3 个

---

## 1. 审计结果

### 1.1 ARB 文件状态
- `app_zh.arb`: 5565 个键（含新增 16 个）
- `app_en.arb`: 5565 个键（含新增 16 个）
- 键完全匹配，无遗漏

### 1.2 硬编码中文分布（用户可见字符串，排除注释和 ARB 文件）

| 层级 | 文件数 | 硬编码处数 | 严重程度 |
|------|--------|-----------|---------|
| core/utils/ | 3 | ~40 | 高 |
| core/services/ | 3 | ~80 | 高 |
| core/design/ | 2 | ~20 | 高 |
| features/auth/ | 2 | ~10 | 高 |
| features/chat/ | 5 | ~30 | 高 |
| features/community/ | 5 | ~40 | 中 |
| features/tools/ | 6 | ~30 | 中 |
| features/user/ | 4 | ~50 | 中 |
| features/plan/ | 5 | ~25 | 中 |
| features/task/ | 3 | ~15 | 中 |
| features/error_book/ | 1 | ~2 | 低 |
| features/visual_elements/ | 1 | ~5 | 低 |
| features/seed_library/ | 1 | ~5 | 低 |
| features/photon/ | 1 | ~3 | 低 |
| **合计** | **~42** | **~355** | — |

### 1.3 已完成的修改

#### 初始修改（会话前半段）
- [x] ARB 文件新增 16 个键（errorAction* 和 syncError*）
- [x] `error_messages.dart` 的 `getActionSuggestion` 方法支持 l10n 参数
- [x] `error_messages.dart` 的 `getUserFriendlyMessage` 清理了不合理的中文检测逻辑（`contains('~')`, `contains('啦')`）
- [x] `error_widget.dart` 的 `_getDefaultTitle` 和 `_getRetryText` 消除硬编码中文回退值，改用 `AppLocalizations.of(context)` + `lookupAppLocalizations` 双重保障
- [x] 英文翻译质量修复 5 处：去除 ~ 波浪号、消除 "sleepy"/"nap" 等过于随意的表达
- [x] 英文翻译质量审计完成：无未翻译内容、无中式英语、placeholder 格式正确

#### Wave 1 完成（Batch G/H/I，3 个并行 agent）
- [x] Batch G: 10 个大文件 i18n 修复（achievement_card, next_actions_card, heatmap 等）
- [x] Batch H: 21 个中文件 i18n 修复（calculator, profile_front_door, review_buttons 等）
- [x] Batch I: 202 个中小文件 i18n 修复（statistics, calendar, aurora 等）
- [x] ARB 键从 5549 增长到 6115，中英完全匹配
- [!] 质量问题: Batch I 生成 545 个非语义键名（statisXXXX）+ 566 个 EN 键仍含中文值

#### Wave 2 进行中（3 个并行 agent）
- [ ] EN 翻译修复: 替换 566 个 EN ARB 中的中文值为地道英文
- [ ] Community/Home/Chat 模块: ~1488 行剩余硬编码中文
- [ ] Tools/User/Plan/Other 模块: ~1485 行剩余硬编码中文
- [ ] core/ 层用户可见字符串（~200 行，等 Wave 2 完成后处理）

#### 待完成
- [ ] core/ 层用户可见字符串修复
- [ ] gen-l10n + flutter analyze 验证
- [ ] 全量硬编码中文复查

---

## 2. 修复策略

### 2.1 分阶段计划

| Phase | 范围 | 文件数 | 状态 |
|-------|------|--------|------|
| Wave 1 | Batch G/H/I 全模块 | 233 Dart + ARB | 完成 |
| Wave 2a | EN 翻译修复 566 键 | ARB only | 进行中 |
| Wave 2b | Community/Home/Chat | ~50 | 进行中 |
| Wave 2c | Tools/User/Plan/Other | ~70 | 进行中 |
| Wave 3 | core/ 用户可见字符串 | ~15 | 待开始 |
| Wave 4 | gen-l10n + 全量验证 | — | 待开始 |

### 2.2 并行策略
- Phase 1/2/3 可并行执行（最多 3 个 agent 同时）
- Phase 4 必须等 Phase 1-3 完成后执行
- Phase 5 必须等 Phase 4 完成后执行

### 2.3 修改原则
1. **不改变业务逻辑** — 只替换字符串，不改控制流
2. **保留中文 fallback** — 无 l10n 时仍返回中文（因为中文是默认）
3. **英文翻译标准** — 自然地道，不含中式英语
4. **键命名规范** — camelCase，语义明确，如 `chatMessageCopied`, `loginAgreeTerms`

---

## 3. 变更记录

### 2026-04-28 — 初始修改

**ARB 文件变更**:
- `app_zh.arb`: +16 键
- `app_en.arb`: +16 键 + 5 处翻译质量修复

新增键列表:
```
errorActionCheckNetwork, errorActionRelogin, errorActionRetryLater,
errorActionNewChat, errorActionRetrySimple,
syncErrorConnectionLost, syncErrorTimeout, syncErrorMaxRetries,
syncErrorUnauthorized, syncErrorTokenExpired, syncErrorServer,
syncErrorServiceUnavailable, syncErrorRateLimit, syncErrorLLM,
syncErrorContextLength, syncErrorUnknown
```

英文翻译质量修复:
```
errorConnectionFailed: ~ → 自然表达
errorRateLimit: ~ → 自然表达
errorTokenExpired: ~ → 自然表达
stayTuned: ~ → !
errorServerIssue: "taking a small nap" → "temporarily unavailable"
```

**代码变更**:
- `error_messages.dart`:
  - `getActionSuggestion` 新增 l10n 参数，优先使用 l10n 键
  - `getUserFriendlyMessage` 清理不合理的中文检测逻辑
  - 保留无 l10n 时的中文 fallback（中文为默认语言）
- `error_widget.dart`:
  - `_getDefaultTitle(BuildContext context)` 消除硬编码中文回退
  - `_getRetryText(BuildContext context)` 消除硬编码中文回退
  - 使用 `AppLocalizations.of(context)` + `lookupAppLocalizations` 双重保障

### 2026-04-28 — Phase 1/2/3 (3 个并行 agent 进行中)

等待 agent 完成后更新此部分。

---

## 4. Git 提交计划

| 提交点 | 内容 | 消息模板 |
|--------|------|---------|
| commit 1 | Phase 1: core 层 i18n 修复 | `fix(i18n): internationalize core layer hardcoded Chinese strings` |
| commit 2 | Phase 2: auth/chat/community i18n 修复 | `fix(i18n): internationalize auth/chat/community module strings` |
| commit 3 | Phase 3: 剩余模块 i18n 修复 | `fix(i18n): internationalize remaining module strings` |
| commit 4 | Phase 4: 英文翻译质量提升 | `fix(i18n): improve English translation quality and naturalness` |
| commit 5 | Phase 5: 全量验证 + ARB 同步 | `fix(i18n): regenerate l10n code and verify complete coverage` |
