# 批2-工具链 · 设计语言规范机检门禁（DL-SPEC）交付报告

> worktree: `Sparkle-sysrev/wt94 @ d87d42ea` ｜ 日期: 2026-09-22 ｜ 规则名: **DL-SPEC**
> 载体: `scripts/guards/check_dl_spec_ratchet.py` + `scripts/guards/dl_spec_ratchet_baseline.json`
> 登记: `scripts/rule_guard_manifest.tsv` 新增一行（UI-TOKENS/UX-COMP 之后），由 `run_all_rule_guards.sh` 调度
> 性质: 守卫只读扫描；未改任何 `mobile/lib` 代码；未改既有守卫（UX-COMP/UI-TOKENS/I18N 基线与行为零变动）；未 commit/push

---

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| ACCEPTANCE 标注【立即】的条款 | **15 条**（逐条 grep 核实，附录统计表写 14；差异 = A4.7，其条文自declares「跨文件无法静态判→人审 A4.9」，故机检口径为 14） |
| 其中已有守卫覆盖（复验绿、未动） | **4 条**：A1.1 / A3.1 / A4.1 / A4.2 |
| 其中本卡新建机检 | **10 条**：A0.1 / A1.2 / A1.3 / A1.5 / A2.3 / A2.6 / A2.7 / A3.2 / A5.3 / A6.6 → DL-SPEC 12 维中的 10 维 |
| 留人审 | **1 条**：A4.7（确认按钮可见性，条文自declared静态不可判）＋「双庆祝跨文件同屏」半句（A2.6 的跨文件部分） |
| 卡面额外要求、提前落地（ACCEPTANCE 标「批 2·G1」） | **2 维**：A2.1 offLadderDuration / A2.2 bannedCurve（为批 2 令牌迁移开闸，任务卡明列） |
| 基线（冻结于 d87d42ea） | **707 处 pattern 命中 / 214 个带债文件 / 12 维**（明细见 §2） |
| 自测 | `--self-test` 8 个子用例全过（<0.1s）；HEAD 全绿；runner 全量不回归（§4） |

---

## 1. 逐条对照（条款号 → 实现方式 → 基线计数 → 样本验证）

### 1.1 本卡新建的 10 条【立即】条款

| 条款 | 维度 id | 实现方式 | 基线计数 | 样本验证（--self-test 用例） |
|---|---|---|---|---|
| **A0.1** 参赛材料叙事 | `competitionNarrative` | `品类空位\|无人占位\|四合一.*事实` 扫 `docs/competition/**/*.md`，逐行（md 无注释概念）；**零容忍**（基线 0，任何命中即 FAIL） | **0**（HEAD 干净） | case3b：fixture 写入「我们验证过的品类空位」→ FAIL 并点名维度 ✅ |
| **A1.2** `Colors.` 禁新增 | `colorsDotNative` | ACCEPTANCE pattern 逐字 `\bColors\.(?!white\|black\|transparent)`（无内层 \b，white70/black54 同样豁免）；扫 `mobile/lib/features`（「同守卫」= UI-TOKENS 根）；ratchet + 新文件零容忍 | **1**（`interactive_onboarding_screen.dart` 的 `Colors.teal.shade400`） | case2：新文件 `Colors.teal` → FAIL 点名 ✅ |
| **A1.3** 冷色准入（启发式） | `coldColorLiteral` | 对 `0xFFRRGGBB` 逐个做 HLS 色相判定：hue∈[165°,310°] 且 sat≥0.15 且 lightness≥0.10（比 ACCEPTANCE 的 7 位示意正则更精确，饱和度/亮度下限排除暖中性盘与近灰）；features 内非 galaxy 文件；ratchet + 新文件零容忍 | **90** / 19 文件（最大户 `visual_element_palette.dart` 31） | case1：注释行 `0xFF5B7CFA` 不计（注释剔除）；case2 冷色字面量 → FAIL ✅ |
| **A1.5** `DS.accent` 禁新增 | `dsAccentAlias` | `\bDS\.accent\b` 扫全 `mobile/lib`（含 core）；ratchet + 新文件零容忍。注：SPEC §1.4.2 要求的 `@Deprecated` 标注尚未落在 design_system.dart:611（那是 mobile 代码改动，超出本卡只读红线）——守卫已先行拦新增调用，标注随批 2 迁移落地 | **12** / 8 文件（大户 `simulation_screen.dart` 3） | case2：新文件 `color: DS.accent` → FAIL 点名 ✅ |
| **A2.3** 呼吸控制器禁新增 | `breathingController` | `\bcreateBreathingController\b` 扫全 `mobile/lib`；ratchet（现存 motion.dart:97 定义=1 钉死，任何新调用即 +1 → FAIL；批 2 删除定义后 `--update-baseline` 降到 0） | **1**（仅定义本身） | case2b：新文件调用 `createBreathingController` → FAIL 点名 ✅ |
| **A2.6** SparkleConfetti 每文件 ≤1 | `confettiPerFile` | `\bSparkleConfetti\(` 按文件计数 ratchet（ACCEPTANCE 指定的 G7 静态口径）；新文件宽容量=1（挂 1 份合法、2 份 FAIL） | **7 文件 × 1**（无一超限） | case3c：新文件挂 1 → PASS；case3d：挂 2 → FAIL 点名 ✅ |
| **A2.7** 粒子旁路 | `particleBypass` | 静态近似：文件内出现粒子发射构造（`\w*Particle\w*\s*\(`）且全文件无 `GlobalParticleCounter` 引用 → 记发射构造数；有 counter 引用（走 `tryAddParticles/canAddParticles/releaseParticles/isOverLimit` 任一闸门）计 0；基础设施文件豁免（global_particle_counter.dart、particle_pool.dart）；ratchet + 新文件零容忍（「新粒子代码立即零容忍」） | **77** / 14 文件（大户 `weather_layer.dart` 17、`particle_layer.dart` 9） | case3e：新文件 `BlueParticle(count: 9)` 无闸门 → FAIL；case3f：补一行 `GlobalParticleCounter.tryAddParticles` → PASS ✅ |
| **A3.2** l10n 硬编码中文 | `textHardcodedZh` | `\bText\(\s*(['"])[^'"]*CJK[^'"]*\1` 扫 features；**零容忍**（HEAD 已 =0）；未改 `check_i18n_coverage.py`（红线：不动既有守卫；该守卫查「中文字符串文件缺 i18n import」，本维查「已接 i18n 仍硬编码 Text('中文')」，互补不重叠） | **0** | case2：新文件 `Text('今日无任务')` → FAIL 点名 ✅ |
| **A5.3** gradient ratchet | `gradientLiteral` | `\bLinearGradient\(\|\bRadialGradient\(` 扫 features；ratchet + 新文件零容忍（「每屏 >2」的人审部分仍归 A5.7/A1.10） | **303** / 96 文件 | case3a：钉死文件 1→2 → FAIL「2 > baseline 1」✅ |
| **A6.6** Oops 英文错误文案 | `errorCopyOops` | ACCEPTANCE rg 逐字 `Oops\|something went wrong`（区分大小写）扫全 `mobile/lib`；ratchet（当前 3 个源行 × 2 备选命中 = 6，见 §3 误报注 4）；批 1 清库后 `--update-baseline` 降 0 | **6 命中**（= 3 源行：l10n en 词典 2 行 + error_widget.dart 回落串 1 行） | case2 系列覆盖新增即 FAIL 语义 ✅ |

### 1.2 已有守卫覆盖的 4 条【立即】条款（复验，未动一行）

| 条款 | 载体 | 本卡动作 | 复验结果 |
|---|---|---|---|
| A1.1 colorLiteral ratchet | `check_ui_design_tokens_ratchet.py`（UI-TOKENS） | 无改动，runner 复验 | PASS（color=239/275，存量还在净降） |
| A3.1 fontSize ratchet | 同上 | 无改动 | PASS（fontSize=721/727） |
| A4.1 parallelClass | `check_ux_component_convention.py`（UX-COMP） | 无改动，基线未动 | PASS（parallelClass=146/146） |
| A4.2 rawChip/rawButton/rawSpinner | 同上 | 无改动 | PASS（rawButton=19/19, rawSpinner=8/8, rawChip=11/11） |

### 1.3 卡面明列、提前落地的 2 维（ACCEPTANCE 标「批 2·G1」，任务卡点名）

| 条款 | 维度 id | 实现方式 | 基线计数 | 样本验证 |
|---|---|---|---|---|
| **A2.1** 时长阶梯外字面量 | `offLadderDuration` | `Duration(milliseconds: N)`，N∉白名单 {50,80,100,120,150,200,250,300,320,350,400,450,480,500,600,650,700}；扫 features；ratchet + **新文件零容忍**（SPEC G1 原文口径） | **186** / 96 文件 | case2：新文件 `Duration(milliseconds: 260)` → FAIL；case1：阶梯内 250 → PASS ✅ |
| **A2.2** 禁曲线引用 | `bannedCurve` | `\bCurves\.(elasticOut\|bounceOut\|elasticInOut)\b` 扫全 `mobile/lib`（注释行剔除）；ratchet（animation_token.dart 退役标记行也在钉死集合内，批 2 删除后降基线） | **24** / 11 文件 | case2：新文件 `Curves.elasticOut` → FAIL 点名 ✅ |

### 1.4 留人审清单（不硬凑）

| 条款 | 原因 |
|---|---|
| **A4.7** 确认按钮可见性 | 条文自declares「跨文件无法静态判，批 1 用 A4.3 覆盖 + 人审 A4.9」——从本卡机检清单剔除，归人审 |
| **A2.6 跨文件半句** | 「task_execution_screen + feedback_dialog 双庆祝同屏」的历史形态是两个文件各挂 1 份——按文件计数不可见跨文件叠加；单文件口径（ACCEPTANCE 给定的 G7 静态替代）已机检，跨文件同屏归人审/批 2 G7 |
| A2.7 运行时半句 | 「发射不超 maxParticles」的运行时数值正确性属批 2 审计；本卡只拦「旁路结构」（不引用 counter 的发射文件） |

---

## 2. ratchet 基线（冻结于 main@d87d42ea）

`scripts/guards/dl_spec_ratchet_baseline.json`，与 UX-COMP 同构（per-file per-dim 计数，`--update-baseline` 显式刷新）。

| 维度 | 基线 | 维度 | 基线 |
|---|---|---|---|
| competitionNarrative | 0 | confettiPerFile | 7（7 文件×1） |
| colorsDotNative | 1 | particleBypass | 77（14 文件） |
| coldColorLiteral | 90 | textHardcodedZh | 0 |
| dsAccentAlias | 12 | gradientLiteral | 303 |
| offLadderDuration | 186 | errorCopyOops | 6 |
| bannedCurve | 24 | breathingController | 1 |
| **合计** | **707 处命中 / 214 个带债文件** | | |

FAIL 条件 = ①任一已钉文件计数**上升**；②**新文件**超出该维宽容量（除 confetti=1 外全部为 0，即新文件零容忍）；③零容忍维（A0.1/A3.2）任何非零命中。
基线纪律升级：`--update-baseline` 若会使任一维**总数上升**则拒绝执行（需显式 `--allow-raise`，正常永远用不到）——把 ACCEPTANCE A9.3「只降不升」⛔ 从流程纪律固化为代码行为。

---

## 3. 误报/漏报风险评估（正则扫描的边界）

1. **coldColorLiteral**：hue 启发式。漏报：低饱和冷色（sat<0.15）逃逸；误报：数据可视化/AI 状态的合法冷色（A1.8 允许项）会被钉进基线，批 2 palette 迁移时应以 token 替换后降基线，而非投诉守卫。galaxy 豁免按路径名匹配（`features/galaxy/**`）。
2. **particleBypass**：文件粒度近似。漏报：同一文件内「闸门 + 旁路」混合发射（有任一 counter 引用即整文件计 0）；误报：仅注释提及 counter 的文件（注释行已剔除，风险低）。
3. **textHardcodedZh**：漏报：跨行字符串、`text:` 命名参数、相邻字符串隐式拼接。HEAD=0 故零容忍无存量争议。
4. **errorCopyOops**：计 match 数不计行数——`'Oops, something went wrong'` 一行同时命中两个备选计 2，故基线 6 = 3 源行（rg 报 3 行）；区分大小写按 ACCEPTANCE 原文，`Something went wrong on our end`（l10n en :2042，大写 S）**不在**基线内——批 1 清库时应一并清掉，属漏报已申报项。
5. **offLadderDuration**：仅 `Duration(milliseconds:`；`Duration(seconds:)` 与常量算术（`250 * 2`）不在条款范围，未扫。
6. **colorsDotNative 作用域缺口（已申报）**：按「同守卫」口径扫 features；`mobile/lib/app/routes.dart:64` 存在一处 `Colors.grey` 在域外——批 2 如需全覆盖，把 scope 换成 mobile/lib 并重刷基线即可（守卫已参数化）。
7. **E5 测试目录白名单（A1.2）未落地**：全仓检索（v3-output/docs/mobile）未找到「E5 测试目录」对应路径（E-05 是后端检索包，无关）；`mobile/test` 天然在扫描域外，等效豁免。若后续 E5 目录落地，在守卫 `exempt_files` 登记即可。
8. 通用：注释行剔除（与 UX-COMP 同规则）；`.g.dart`/`.freezed.dart` 排除；`app_localizations_*.dart`（生成但入库）保留在 A6.6 域内——这是该维仅有的命中源，ratchet 语义不受 regen 影响（只要不新增命中）。

---

## 4. 验证证据

1. **HEAD 全绿（基线=现状）**：
   `python3 scripts/guards/check_dl_spec_ratchet.py` →
   `PASS — ratchet holds: competitionNarrative=0/0, colorsDotNative=1/1, coldColorLiteral=90/90, dsAccentAlias=12/12, offLadderDuration=186/186, bannedCurve=24/24, breathingController=1/1, confettiPerFile=7/7, particleBypass=77/77, textHardcodedZh=0/0, gradientLiteral=303/303, errorCopyOops=6/6 (214 files)`；耗时 **1.9s**。
2. **故意违规样本**：`--self-test` 8 子用例全过（干净 fixture PASS / 新文件 6 维连犯逐维点名 / 呼吸调用 / 钉死文件抬升 / A0.1 零容忍 / confetti 1 过 2 抓 / 粒子旁路抓+闸门后过），全程临时目录自动回收，<0.1s。
3. **全量守卫不回归**：
   - HEAD+本卡改动：`bash scripts/run_all_rule_guards.sh` → 失败集合 = `AS AQ BG BI GOV-DATA-MIN BJ BA-ROUTES`；
   - **纯净 HEAD 对照**（`git clone` worktree 至 /tmp，天然只含 d87d42ea）：同命令 → 失败集合**逐字相同**；
   - 即这 7 条为 **d87d42ea 上的既有失败**（gateway↔engine 路由 parity 漂移等，属批 1 功能面债务，非本卡范围）；设计链相关守卫 **DL-SPEC / UX-COMP / UI-TOKENS / I18N / BN / BM 全绿**，零回归。
4. 守卫自身测试 LIGHT：无构建、无模拟器、扫描纯文本。

---

## 5. 与批 1-B（wt93 l10n 词典）的不冲突面声明

- 本卡**不触碰任何 l10n/arb 文件**；`errorCopyOops`/`textHardcodedZh` 为只读扫描。
- wt93 若净删 "Oops|something went wrong" 命中（预期方向）→ ratchet 只会更绿，无需动基线。
- wt93 若新增 en 词典行含 banned 文案 → DL-SPEC 会正确拦截（这正是 A6.6 的意图：错误文案走中性三句式表）。
- 基线冻结于 d87d42ea，与 wt93 无共享文件、无锁竞争；两卡合并顺序不影响 DL-SPEC 判定。

---

## 6. 批 2 交棒说明

- 批 2 令牌迁移每清偿一类存量（如删 elasticOut 24 处、DS.accent 12 处、呼吸定义），跑
  `python3 scripts/guards/check_dl_spec_ratchet.py --update-baseline` 并提交 JSON diff（A9.3：diff 审阅只降不升，守卫已内置拒绝抬升）。
- `DS.accent` 的 `@Deprecated` 注标（SPEC §1.4.2）请在批 2 design_system.dart 改造中随迁；本守卫的 ratchet 已先行封住新增调用面。

## 7. 收工核查声明

- [x] 一切修改仅在 wt94 worktree 内；主仓只读
- [x] 未 commit / 未 push；交付 = `v3-output/B2-GUARDS/changes.patch` + 本报告 + worktree 内未提交变更
- [x] /tmp 已自清（基线对照 clone、self-test 临时目录均已回收）
- [x] 零构建、零模拟器、无独立端口进程残留
- [x] mobile/lib 零改动；既有守卫（UX-COMP/UI-TOKENS/I18N 及全部 manifest 既有行）零改动

*报告完。*
