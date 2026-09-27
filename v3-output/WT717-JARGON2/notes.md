# WT717-JARGON2 · V3-FIX-411 处置实录（范围外残留真黑话 2 键 zh 白话化收口）

- 工号：wt717（2026-09-27，任务来源=台账 V3-FIX-411 行，wt710 登记 2026-09-27）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt717-jargon2`（分支 `agent/node-b/wt717/jargon2`）
- base SHA：`48d5a438`（main）；代码 commit：`b02528fc`
- 方法与验证口径完全复刻 wt710 判例（4ecf5d71，V3-FIX-403）：zh 单边值级替换 + gen 产物外科手改同步 + L10N-REGEN-PARITY 互证
- 触达面：`mobile/lib/l10n/app_zh.arb`（2 值）+ `app_localizations.dart`（2 doc 行）+ `app_localizations_zh.dart`（2 值）——恰 3 文件 6 行改 6 行；en 侧三面零触碰

## 1. 结论 TL;DR

1. 411 两键 zh 值白话化落地，建议词照抄（保义不保喻）；键名/键数/占位符（{target}）零改动；en 侧原值已白话零触碰。
2. 49 冻结键（V3-FIX-182 拍板挂起：aurora*19+visual*30 死键）与两键（studyMaterials*/galaxyUpload* 活键）前缀不相交，零触碰。
3. 连带新发现 1 处：`share_poster_service.dart:304` 硬编码字面量 '知识星点'（非 l10n 键），另立 **V3-FIX-430**，本卡不扩面不触碰。

## 2. 两键 before/after（zh；en 均不动）

| 键 | 消费面（词边界 grep 实录，改前=改后同址） | zh before → after | en（不动） |
|---|---|---|---|
| studyMaterialsHeroSubtitle | document_library_screen.dart:593（1 文件 1 处） | 统一管理你的笔记、课件和 PDF，查看它们**落到哪些知识星点**，并追踪 Aurora 实际引用了多少次。 → 统一管理你的笔记、课件和 PDF，查看它们**关联到哪些知识点**，并追踪 Aurora 实际引用了多少次。 | Manage your notes, slides, and PDFs, see where they land in your star map, and track how often Aurora actually uses them. |
| galaxyUploadHeadingTo | galaxy_document_upload_overlay.dart:386（1 文件 1 处） | **正飞向 {target}** → **正在添加到 {target}** | Heading toward {target} |

- 「知识点」对齐 403 同族 studyMaterialsAttachedNodesTitle/studyMaterialsKnowledgeStarsLabel@bf8b3742 口径；「正在添加到」对齐 403 上传族（AlreadyInProgress→「在处理中/加入」）白话口径，与台账建议词一致。

## 3. grep 归零证据与 gen 同步（真实运行）

- **消费面活性（改前，词边界口径）**：`l10n.<key>` 词边界 grep（48d5a438 基线）各恰 1 消费文件（§2 表第二列），全活，与台账登记一致。
- **词边界口径环境注记**：本机为 macOS BSD grep，无 POSIX `[[:<:]]/[[:>:]]` 扩展（单文件已知命中实测 exit=1）；用等价字符类口径 `l10n\.<key>([^_A-Za-z0-9]|$)`（词字符集取反+行尾断言）复刻，语义同 POSIX 词边界。
- **改后消费面**：改前=改后均恰 2 命中（两键各 1），键名未动故零变化。
- **改后载体面归零**：两键黑话词（知识星点/正飞向）及其族词（飞向）在 arb×2+gen×3 五文件 grep **零命中**（exit=1）。改前同面 6 命中（arb zh×2+gen doc×2+gen zh×2），6/6 归零。
- **gen 同步手法**（照抄 4ecf5d71 判例）：`flutter gen-l10n` 重生成实测产生全量重排噪声（wt710 实录 intl.selectLogic 格式漂移），**弃用重生成产物**、外科手改 gen×2（doc 2 行+zh 2 值；en 侧本卡零改动故 gen en 不动），`check_l10n_regen_parity.py` 10087 键全量过作逐字节语义互证。占位符 `$target` 无花括形与既有 emitter 规则一致。

## 4. 验证记录（真实运行）

- **守卫（改前基线+改后）**：`python3 scripts/guards/check_l10n_regen_parity.py` → 改前 `L10N-REGEN-PARITY OK: 10087 template keys == abstract members; zh/en subclasses complete.`；改后同文重跑 PASS。`check_i18n_coverage.py` → `[i18n-coverage] PASS — all presentation files with Chinese strings import i18n infrastructure`。
- **flutter analyze**：`No issues found! (ran in 30.7s)`，零 issue。
- **受影响测试**：两消费屏（DocumentLibraryScreen/GalaxyDocumentUploadOverlay）在 mobile/test 零直接引用、双键名/新旧值 grep **零钉值**（grep exit=1），无 wt710 式钉值连带；按 wt710 口径跑 galaxy 全族 `flutter test test/features/galaxy` → **154 绿 1 skip 0 红**（与 wt710 基线逐字一致）；documents 侧无独立测试目录（find 零命中）。
- **台账守卫**：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → `verify：300 行 V3-FIX 行，裸管分布 {8: 300}，多数形态 8 / verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法`，exit=0（首跑 411 行 9 裸管 FAIL——本工在状态格里写了含裸管的字符类记号，当场改措辞归 8）。

## 5. 连带新发现：V3-FIX-430（已登记，不阻塞 411 闭账）

- `mobile/lib/core/services/share_poster_service.dart:304`：`ShareableContentType.knowledgeNode => '知识星点'` —— 硬编码字面量，非 l10n 键。
- 发现路径：411 收口的全仓（mobile/lib+test）黑话词 grep；改后唯一残留命中（其余同词命中已随本卡归零）。
- 为何 403/411/wt710 扫面都没拦住：wt710 扫的是 **arb**（键值对），硬编码 Dart 字面量不在其扫面；i18n-coverage 守卫只管 presentation 目录的中文串（core/services 非其辖区）。
- 处置：登记 V3-FIX-430（OPEN），白话方向=「知识点」（可对照 studyMaterialsKnowledgeStarsLabel@bf8b3742 先例），i18n 化或最小改词由执行卡按分享海报语境裁。

## 6. 边界与自查

- 不新增键不删键（两键全为既有键改值）；arb 键名零改；`git diff --stat`=arb×1+gen×2 恰 3 文件 6 行，无双数据库/后端/认证面触达。
- 49 冻结键零重叠：冻结池=aurora*19+visual*30 死键（W565 §3.1），两键均活键，前缀不相交。
- en 侧双侧值+gen en 本卡零字节改动（git diff 实证仅 3 文件）。
- 不 push；gen 拷贝自主仓同基线（copy 后 git status 零差异，证明与基线产物一致）。
