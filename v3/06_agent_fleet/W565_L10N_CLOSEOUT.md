# W565 L10N 收池报告 — V3-FIX-210 闭账判定（六批收官文书）

- 日期：2026-09-25 ｜ agent：wt565 ｜ 卡：V3-FIX-210 收池评估与闭账判定（文书卡，不碰产品码）
- 核验基线：worktree `wt565-l10nclose` @ 6a771ddb（主仓只读参照，gen 目录 `cp -RL` 引入）
- 结论速览：**总账数字对上了（卡面草案 1237 有误，核对后六批实收 1509）**；**闭账判定成立（可收割域已尽）**；210 行已就地 OPEN→FIXED@346e15f9。

---

## §1 总账核对

### 1.1 六批实收总表（台账批注记 ↔ 本次独立核验双列）

| 阶段 | 提交 | 实收 | 台账批注记依据 | 本次独立核验 |
|---|---|---|---|---|
| 登记基线 | cbc8e8ad | — | 11559 键标识符集；零引用 1502 = FIX-200 已收 38 + 本卡候选 1464 | arb JSON 解析 zh/en 各 **11559** ✓ |
| FIX-200（另卡，不入本卡账） | bd8eb707 | 38 | 该行 FIXED@bd8eb707 | — |
| 批一 wt501 | 1f0293ae（集成 e720416f） | **436**（440 重扫 − bd8eb707 重叠 4；其中 98 系 cbc8e8ad 后窗口期键） | 行内"6937 行纯删除 0 插入" | 1f0293ae numstat **0+/6937−** ✓；集成 e720416f 实测 5 文件 **77 插入**（7/30/19/16/5）=V3-FIX-261 复活 6 死键案 ✓ |
| 批二 wt506 | 0c912a97 | **309/309 零跳过**（simulation 83/exam 74/focus 59/user 47/task 46） | histogram 5023 纯删除；myers +41 伪影已排除 | myers numstat 42+/5083−（与台账记录的 myers 伪影口径一致，行多重集 added=0 判例）✓ |
| 批三 wt522 | 359623d6 | **243/243 零跳过**（predicted 46/dashboard 42/review 38/vocabulary 38/flash 37/achievement 14/goal 27/settingsSynced 1） | 3884 纯删除 | numstat **0+/3884−** ✓ |
| 批四 wt535 | b98c7ca1 | **156/156 零跳过**（home 91/error 23/galaxy 23/knowledge 19；含 V3-FIX-261 复活键顺收 4 + galaxy 谱系漂移窗口键 1） | 2631 纯删除 | numstat **0+/2631−** ✓ |
| 批五 wt540 | d8366f80 | **67/67 零跳过**（share 13/notification 13/chat 9/time 7/streak 6/theater 5/sync/onboarding/skill 各 4/plan 2） | 1019 纯删除 | numstat **0+/1019−** ✓ |
| 批六 wt545 | 346e15f9（主线集成 c2129226） | **298** = zh 域 297（308 可收域收 297 跳 11）+ V3-FIX-246 尾项 en-only 孤儿 1 | en 640 值行含孤儿单文件外科删；5019 纯删除 | numstat **0+/5019−** ✓；分支 arb JSON 解析 zh/en 各 **10117** = 台账"双 arb 各 10117"✓ |
| **六批合计** | | **1509**（含 246 尾项）/ 1508（纯 210 域） | | 436+309+243+156+67+298 |

### 1.2 卡面草案 1237 的错账更正

卡面「六批共收 1237 键（38+436+243+156+297…）」核对后不成立，差 272：
- **漏批二 309**（simulation/exam/focus/user/task 全收族）；
- **漏批五 67**（share/notification/chat/time/streak/theater/sync/onboarding/skill/plan 族）；
- **误并另卡 FIX-200 的 38**（该 38 记在 V3-FIX-200 FIXED@bd8eb707 名下，不在 210 行账内）；
- **批六应为 298 非 297**（297 之外还有 V3-FIX-246 尾项 en-only 孤儿 taskDetailNodeExpansionDescription 的单文件外科删，随批销账）。

修正式：1237 − 38 + 309 + 67 + 1 = **1509**。**以台账核对后数字为准：六批 1509 键。**

### 1.3arb/Gen 交叉验证（当前 HEAD 6a771ddb 实测）

| 项目 | 数值 | 互证 |
|---|---|---|
| app_zh.arb / app_en.arb 值键 | **10129 / 10129**（JSON 解析；en−zh 孤儿差 = 0，V3-FIX-246 已销账） | — |
| gen×3 成员 | 8740 getter + 1389 参数化方法 = **10129** | 恰等于双 arb 值键数 ✓ |
| `flutter gen-l10n`（3.41.3） | exit 0；regen 后 `git status`/`git diff` **全空** | 与入库 gen×3 逐字节一致（L10N-REGEN-PARITY OK）✓ |
| 全库 10129 键 identifier-set 词边界重扫（consumer 面 = mobile lib+test+integration_test 剔 gen×3） | dead 池恰 **60** | 与批六账面（留池 11 + 冻结 49）**集合全等**，零漂移、零窗口期新增 ✓ |

### 1.4 池闭合等式（逐项可追）

- 登记域：1464（登记候选）− 1404（∈登记已收：338+309+243+151+67+296）= **60 剩**（11 留池 + 49 冻结，均∈原登记）✓
- 超登记已收 105 = 批一窗口 98 + 批四 galaxy 窗口 1 + 批四复活顺收 4 + 批六复活顺收 1（chatMemoryReferenceReceiptLabel）+ 批六 en-only 孤儿 1；1404 + 105 = **1509** ✓
- 全战役（含 FIX-200）：11559 − 1547 + 期间特性净增 = 10117@346e15f9 ✓；分支→主线集成（c2129226）10125、再至 HEAD 10129 的 +8/+4 均为在途特性键，不入死键池。

## §2 留池 11 键定案文书

批六跳过原因（台账原文）：11 键全系 `l10n.<key>` 前缀碰撞活长键，宁漏勿错整键留池。本次逐键复验（词边界 `rg -w` consumer 面零引用 = 死亡确证；`rg -i "l10n.<key>\w*"` 列碰撞活键）：

| # | 留池键 | 碰撞活键（本次实测） | 词边界引用 | 判定 |
|---|---|---|---|---|
| 1 | auto_unknownerror | auto_unknownerrorpleaseretry | 0 | 精割解锁 |
| 2 | bgmSectionSubtitle | bgmSectionSubtitleDefault / WithCount | 0 | 精割解锁 |
| 3 | commonNo | commonNoData | 0 | 精割解锁 |
| 4 | ebLoadError | ebLoadErrorFailed | 0 | 精割解锁 |
| 5 | generationFailed | generationFailedWithDetail | 0 | 精割解锁 |
| 6 | groupAdmin | groupAdminCount | 0 | 精割解锁 |
| 7 | groupMember | groupMemberCount / groupMembersInvite | 0 | 精割解锁 |
| 8 | groupOwner | groupOwnerCount | 0 | 精割解锁 |
| 9 | personaLoadFailed | personaLoadFailedError | 0 | 精割解锁 |
| 10 | sendFailed | sendFailedWithError | 0 | 精割解锁 |
| 11 | studyMaterialsDate | studyMaterialsDateAll / 7d / 30d / **90d（批六后新增活键，碰撞面扩大）** | 0 | 精割解锁 |

**定案**：
- **0/11 适用「待重命名解锁」**。「改名消除碰撞」两条路均不通：改死键 = 自败（改名后仍是死键，等价于删但多绕一步）；改活键 = 为工具口径零收益扰动活屏消费面（groupAdminCount/studyMaterialsDate90d 等均在用），违反最小扰动。碰撞是朴素子串 grep 的工具伪影，不是语义纠缠——**解锁工具是词边界精割（rg -w / -w -f），不是改名**。卡面"若某键改名即可消除碰撞且键本身已死"的分支经逐键检验为空集。
- **0/11 是永久留池**。无任何在途特性占位证据（无 fix-182 关联、无 gated UI 等待接线），批六词边界复核+本报告复验均零引用，属"纯尾差"。
- **11/11 判定为「词边界精割可解锁」**：与冻结 49 合并为「终扫 60 键」单卡最经济（预案见 §3，流程同款 30 分钟内）；11 键不依赖 FIX-182 拍板，可先行。本卡为文书卡，不执行收割/改名，留下一卡。

## §3 冻结区处置路径文书（visual* 30 + aurora* 49 联动 FIX-182）

### 3.1 冻结区构成与现状

- 构成：**aurora\* 19 + visual\* 30 = 49**。本次于 HEAD 6a771ddb 全量重扫复核：两族共 311 键中恰 49 零引用，清单与批六账面全等（49 键全清单见 §3.4，可直接喂 `rg -w -f`）。族内其余 262 键全部活跃（visual-elements 屏/aurora 校准面板等在用）。
- 闸的现状：V3-FIX-182 后端闸已落地（FIXED@471ab19a：`ENABLE_VISUAL_ELEMENTS` 默认 False + 路由组级 403）；release 五旗单一权威已落（router.py:311 `require_release_flag(RELEASE_ENABLE_VISUAL_ELEMENTS)`）；移动端 `releaseFlagsProvider` 短路已落（V3-FIX-190 FIXED@82ce8214）。**剩余待拍板的是 release-scope 决策本身：旗随发布开，还是常关。**

### 3.2 旗常关时这 49 键的价值判定

**「未来开旗即用的现货」不成立**：49 键在 consumer 面词边界零引用——它们不在任何 gated 代码路径上（开旗后真正亮灯的 UI 消费的是族内另外 262 个活键）。这 49 键是旧状态带/旧主题/旧版式的**随葬文案池**：开旗路线也需要按 V3-FIX-200 行内处方"先过文案替换"重新接线。因此两向处置：
- **旗常关/删 feature** → 49 键零成本随葬，按 §3.3 预案收割，l10n 面闭池；
- **发布开旗** → 文案替换属特性工作；替换时这批键名语义仍准确，可优先回收键名（重新接线），未被回收者随当批收割流程一并清。拍板后无论哪个方向，**收割动作本身都在 30 分钟内可完成**（见 §3.3），不构成发布路径上的阻塞债。

### 3.3 「随 182 拍板后 30 分钟可收割」预案

1. （2 min）重扫确证：本报告 §3.4 清单（+§2 的 11 键若同批）喂 `rg -w -f`，consumer 面零引用复验（误删活键在此拦下）。
2. （5 min）arb×2 外科删：49 值行 + 对应 @ 元数据块；en/zh 行差按 en-only 规则单文件处理（V3-FIX-246 判例）。
3. （5 min）gen×3 外科删（参数化键按换行感知跨度，V3-FIX-261/批六判例）→ `flutter gen-l10n`：G0=HEAD regen 基线 MD5、Proof-A=G0↔G1 diff 纯删除 added=0 且移除成员恰=批次、Proof-B=外科 gen 与 regen G1 MD5 全等。
4. （8 min）analyze 同环境 HEAD 双跑对照：E/W/I 三计数零漂移（analyze 全量即编译门，误删活键必炸 undefined getter）。
5. （5 min）触达测试：wt422 l10n harvest smoke + i18n_service + 相邻屏抽验（unified_settings/visual_elements/aurora 校准面板向）。
6. （3 min）n9 棘轮复跑：预期容忍下降恰=基线键×2（冻结 49 中 auroraFeedbackFailed 在 n9 基线 2 处 → 1 键×2 块；若 11 键同批则 personaLoadFailed 再 −2）。全仓外部命中面仅：arb×2 自身、台账自引、v3-output 历史会话工件（wt488/wt479/B3-CHAT）、n9 基线 2 键——均为非消费面不动键。
7. （2 min）**numstat insertions=0 硬自检**（V3-FIX-261 判例：只验删除计数不算数）+ 台账销账。

### 3.4 冻结区 49 键全清单（HEAD 6a771ddb 复核，供下卡直接消费）

aurora\*（19）：auroraActionConfirm, auroraActionRecalibrate, auroraBandCalibrationAvailable, auroraFacetAboutGoal, auroraFacetAboutJudgment, auroraFacetAboutNow, auroraFacetAboutYou, auroraFacetMissing, auroraFacetPartial, auroraFacetReady, auroraFacetRecalibrating, auroraFeedbackFailed, auroraFreshnessLabel, auroraInputHint, auroraPhaseCheckpoint, auroraPhaseDiagnosis, auroraPhaseExecution, auroraPhaseStrategy, auroraWakeViewUpdates

visual\*（30）：visualAmberDesc, visualAmberEcho, visualColdTrail, visualDefaultBgDesc, visualDefaultLight, visualElementRarity, visualElementsEntrySubtitle, visualEnergyDesc, visualFirefly, visualGalaxy, visualGalaxyConqueror, visualGlowDesc, visualInkBlue, visualInkGlow, visualMeteor, visualMeteorDesc, visualNeonDesc, visualNightRing, visualObsidian, visualPetalDesc, visualPulseRingDesc, visualRippleDesc, visualScholar, visualSlotConquestTrail, visualSlotHomeAtmo, visualSlotHomePage, visualSlotHomeParticle, visualSnowDesc, visualStarCore, visualStarDefault

## §4 闭账判定

**判定：成立——可收割域已尽。** 依据三支柱：
1. **留池有据**（§2）：11 键全部词边界零引用（死亡确证），碰撞逐键列证全为活长键前缀；非"死活不明"，是工具口径下的精割尾差，解锁路径明确且不依赖任何外部拍板。
2. **冻结有闸**（§3）：49 键处置权清晰挂在 V3-FIX-182 release-scope 拍板，闸体（后端 flag + 移动端短路）均已落地，拍板后 30 分钟预案可收割；非无主键。
3. **零新增**（§1.3/§1.4）：HEAD 全库 10129 键重扫 dead 池恰 = 60 与批六账面集合全等；批六后特性工作（+12 键）零死键流入；池闭合等式逐项对上。

**已执行**：210 行就地 OPEN→FIXED@346e15f9（批六分支 SHA；六批均经 squash 集成，批六主线对应 c2129226），行尾注明核对后总数与报告指引。**新发现登记：本次收池独立核验未产生新缺陷**（无新死键、60 键无新增镜像/守卫引用、无漂移），**284 号段未消耗**，留待后续。

**顺带留证（不销他卡账）**：V3-FIX-261 残留处置已随批六完结——chatMemoryReferenceReceiptLabel 实测已不在 arb×2/gen×3（批六收讫），planPortfolioRetry 实测已转活（learning_portfolio_screen.dart 消费）；该行销账由原卡责任人/审查完成。

## 附：本次核验的可复现命令面

- arb 键数：`git show <sha>:mobile/lib/l10n/app_{zh,en}.arb` + JSON 解析非 `@` 键（行级正则会因 arb 多行字符串虚高，勿用）
- 全池重扫：`rg -w -o -f <keys.txt> lib test integration_test -g '*.dart' -g '!lib/l10n/app_localizations*'`（注意 gen 产物在 `lib/l10n/app_localizations*`，不在 `lib/gen/`——后者是 protobuf）
- gen 成员：getter `String get x` 8740 + 参数化方法 `String x(...)` 1389 = 10129；`flutter pub get && flutter gen-l10n` 后 `git diff` 空 = parity
- 批提交纯删除自检：`git show --numstat --format= <sha> | awk '{a+=$1;b+=$2} END{print a,b}'`
