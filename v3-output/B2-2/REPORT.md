# B2-2 · 色彩语义别名层 + 表面阶 ΔE 校验脚本 交付报告

> worktree: `Sparkle-sysrev/wt113 @ main(1d42786a)` ｜ 日期: 2026-09-22 ｜ 卡: **B2-2**（SPEC v1.0 批 2 首卡，P0-1 门禁时点绑定对象）
> 载体: `mobile/lib/core/design/theme/sparkle_context_extension.dart`（语义别名层）＋ `scripts/design/check_surface_ladder_de.py`（ΔE 机检）＋ `design_system.dart`（DS.accent @Deprecated）＋ `mobile/test/core/design/semantic_color_names_test.dart`（映射回归）
> 性质: 语义层纯映射、零色值改动、零视觉变化；未 commit/push；产物仅落本 worktree
> 门禁效力: **本卡合入即 SPEC §1.7【批 2 起】段生效**（新代码取色只走语义名；旧字段名降为只读 owner）

---

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| 语义别名层 | **已落地**——`SparkleSemanticColorNames` extension 挂 `SparkleColors`，`context.colors.surface.canvas` 等 SPEC §1.7 规范路径直接可用；纯别名转发（测试以 `same()` 同实例断言钉死），全部 6 个主题变体（light/dark × normal/highContrast/colorBlindFriendly）成立 |
| ΔE 脚本 | **已交付**——`scripts/design/check_surface_ladder_de.py`，纯标准库 CIEDE2000（D65/2°）；自测复现 **29 对 Sharma-2005 文献值**（容差 1.5e-4 全过）；light gate 绿、dark 锚点回归绿 |
| DS.accent 退役起步 | **已落地**——`@Deprecated` + 注释指向 SPEC §1.4.2；调用点零改动；存量计数 **12/8 文件**，ratchet 纹丝不动（12/12） |
| 门禁联动 | **核验式落地**——`dsAccentAlias` 维已由 B2-GUARDS@1c2aced1 预落地（新文件零容忍+存量 ratchet），本卡不重复增设、manifest 不加行（并入 DL-SPEC 单行，符合卡面要求） |
| analyze | `flutter analyze` 改动前后 issue 计数**完全一致**（6872=132 error/41 warning/6699 info，error 全部为 third_party_plugins vendored forks 与缺 build_runner 产物的存量 test 文件，`lib/` 本体零 error）；**零新增**（含零新增 deprecation 提示，见 §5.3 工具链发现） |
| 守卫 | DL-SPEC（含 --self-test）/UX-COMP/UI-TOKENS 全绿；全量 `run_all_rule_guards.sh` 结果见 §5.2 |
| 单测 | `mobile/test/core/design/semantic_color_names_test.dart` 已交付；**运行被内存门拦停**（收工时点 swap 空闲 1164M < HEAVY 启动门 1.2G，AGENTS 硬规则优先），待验收方单文件补跑，命令见 §5.4 |

---

## 1. 语义面 API 清单（回执①：映射表全列）

落点：`mobile/lib/core/design/theme/sparkle_context_extension.dart`（SPEC §1.7 指定落点）。
结构：`SparkleSemanticColorNames` extension on `SparkleColors` + 两个语义视图类（`SparkleSurfaceSemantics` / `SparkleTextSemantics`）。挂 owner 类型使 `context.colors.<语义名>` 与 SPEC §1.7 表逐字一致，且 **extension 成员不遮蔽实例成员**——既有 `context.colors.surfacePrimary` 等旧字段消费面零破坏（编译面与视觉面双重零变化）。

### 1.1 表面阶（SPEC §1.2，`context.colors.surface.*`）

| 语义名 | owner（只读值层） | light 值 | dark 值 |
|---|---|---|---|
| `surface.canvas`（S0 画布） | `surfaceAmbient` | `0xFFFCF8F3` | `0xFF0E0E10` |
| `surface.base`（S1 基础面） | `surfacePrimary` | `0xFFF8F4EF` | `0xFF1A1A1E` |
| `surface.raised`（S2 浮起面） | `surfaceSecondary` | `0xFFF1EBE4` | `0xFF222226` |
| `surface.elevated`（S3 高亮浮起面） | `surfaceTertiary` | `0xFFE7DED4` | `0xFF2C2C30` |

### 1.2 文字阶（SPEC §1.3，`context.colors.text.*`）

| 语义名 | owner | light 值 | 备注 |
|---|---|---|---|
| `text.primary` | `textPrimary` | `0xFF171717` | |
| `text.secondary` | `textSecondary` | `0xFF6C655D` | |
| `text.tertiary` | **`textSecondary`** | `0xFF6C655D` | **TODO(B2-3)**：独立槽批 2 定标（SPEC §1.3【定标待实测】）；现按规范原文「现用 textSecondary 兼」映射最近 owner 值，不派生新色 |
| `text.disabled` | `textDisabled` | `0xFFA49B90` | 状态色非层级，对比度豁免 |

### 1.3 唯一交互 accent 与语义槽（SPEC §1.4/§1.5，`context.colors.<槽名>`）

| 语义名 | owner | light 值 | 备注 |
|---|---|---|---|
| `accent` | `brandPrimary` | `0xFF825D49` | 唯一交互色（§1.4.1）；**≠ 退役别名 DS.accent（=brandSecondary）** |
| `success` | `semanticSuccess` | `0xFF456E52` | 灰绿 sage |
| `warning` | `semanticWarning` | `0xFF7D5C26` | 琥珀 |
| `error` | `semanticError` | `0xFFA0483E` | 陶土 |
| `info` | `semanticInfo` | `0xFF48678D` | slate 蓝，唯一冷色槽（§1.5.2 冷色准入） |
| `focus` | **`brandPrimary`** | `0xFF825D49` | **TODO(B2-3)**：SPEC §1.5「批 2 评审是否独立」；现由 accent 兼任（规范现状） |

> 命名冲突核验：`SparkleColors` 全部实例成员（字段 + `ctaAccent/border*/surface*/glass*/brand*Deep` 等派生 getter）与全仓 extension 扫描（`extension … on SparkleColors` 此前为 0 个）均无 `surface/text/accent/success/warning/error/info/focus` 占用，语义名零遮蔽、零撞名。

---

## 2. ΔE 脚本与实测值（回执②：四级逐对实测值）

### 2.1 脚本规格（SPEC §1.2.2 / ACCEPTANCE A1.6，R4 P0-2）

- 落点 `scripts/design/check_surface_ladder_de.py`（新目录 `scripts/design/`）；纯标准库，只读扫描。
- 度量：**CIEDE2000**（kL=kC=kH=1，Sharma et al. 2005 实现口径）；Lab 由 sRGB 线性化（D65/2°，IEC 矩阵 + D65 白点 95.047/100/108.883）。
- 输入：默认读 `theme_manager.dart` 各 factory 内**最后一个** `surface*:` 字面量（= CB-safe/highContrast 早退后的 normal palette）；`--current S0,S1,S2,S3` 可注入未来 tonal 管线输出；`--mode light|dark`。
- 校验：①相邻级亮度差下界（规则 1.2.1：3%/3%/4%）；②锚点等价 ΔE≤2（规则 1.2.2，锚点=脚本内常量快照）。`--report` 输出逐对 ΔE 表；`--self-test` 跑 Sharma-2005 文献数据集。
- 退出码：**0**=PASS；**1**=违规（或自测失败）；**2**=环境/用法错误（文件缺失、hex 不可解析）。
- 自测：**29 对** Sharma-2005 补充测试数据（含全部 hue-branch 病态对：#1-3、#7-16、#21-24 等）± **1.5e-4** 全数复现；另测白点 Lab=(100,0,0)、锚点自 ΔE=0、锚点自跑 gate 绿。

### 2.2 口径裁决（两条，需主会话/设计评审知悉）

1. **「亮度差」= WCAG 相对亮度 Y 之差（百分点，0–100 尺度）**。SPEC §1.2.1 自我断言「当前值已满足」，而 light 阶在 **CIE L\* 口径下 S0/S1 仅 ≈1.39**（不满足 ≥3%）——与该断言矛盾；相对亮度口径是唯一与之自洽的读法（3.41/7.17/9.73）。已在脚本 docstring 与输出中固化此口径。
2. **规则 1.2.1 下界只对 light 阶执行门禁**。§1.2 级表与 A1.6 锚点均只有 light 值，「当前值已满足」也仅对 light 表成立（dark 阶同口径实测 0.61/0.57/0.93pp，若对 dark 强制该下界则现网立即违规——反证该条不是全模式条款）。dark 阶只做锚点 ΔE≤2 回归，相邻值 informational 展示。

### 2.3 light 阶实测（source=theme_manager.dart，2026-09-22 快照）

锚点：SPEC §1.2 表 / A1.6 verbatim（`FCF8F3/F8F4EF/F1EBE4/E7DED4`）。

| 级 | current | anchor | Y(rel) | L* | ΔE00(vs anchor) | ≤2 |
|---|---|---|---|---|---|---|
| S0 | FCF8F3 | FCF8F3 | 94.30 | 97.75 | 0.0000 | PASS |
| S1 | F8F4EF | F8F4EF | 90.89 | 96.36 | 0.0000 | PASS |
| S2 | F1EBE4 | F1EBE4 | 83.72 | 93.33 | 0.0000 | PASS |
| S3 | E7DED4 | E7DED4 | 73.99 | 88.92 | 0.0000 | PASS |

| 相邻对 | ΔE00 | \|ΔY\| pp | 下界 | 判定 |
|---|---|---|---|---|
| S0→S1 | 0.8156 | **3.41** | ≥3 | PASS |
| S1→S2 | 2.1519 | **7.17** | ≥3 | PASS |
| S2→S3 | 3.2014 | **9.73** | ≥4 | PASS |

全矩阵（rows=current × cols=anchor，ΔE00）：S0 行 0.0000/0.8156/2.8775/6.0626；S1 行 0.8156/0.0000/2.1519/5.3507；S2 行 2.8775/2.1519/0.0000/3.2014；S3 行 6.0626/5.3507/3.2014/0.0000。

### 2.4 dark 阶实测（锚点=本卡合入时点快照，非 A1.6 锚）

锚点快照（B2-2）：`0E0E10/1A1A1E/222226/2C2C30`（surfaceAmbient/Primary/Secondary/Tertiary）。锚点逐对 ΔE00 全部 0.0000（≤2 PASS）；相邻 |ΔY| 0.61/0.57/0.93pp（informational，不门禁，见 §2.2-2）。

### 2.5 拦截能力抽查（注入实验）

- `--current FCF7F2,F8F4EF,F1EBE4,E7DED4`（S0 微调一档）：锚点 ΔE 0.5172 仍≤2，但相邻亮度 2.74pp<3 → **FAIL(exit 1)**，规则 1.2.1 拦截有效；
- `--current 'BADHEX,…'` → **exit 2**（用法错误）。

---

## 3. DS.accent 别名退役起步（回执③：存量计数）

- `design_system.dart` `DS.accent`（=> brandSecondary）已加 `@Deprecated` + doc 注释指向 SPEC §1.4.2 与迁移去向（`context.colors.accent` = brandPrimary）；**调用点零改动**（迁移属 B2-3+）。
- **存量计数：`dsAccentAlias` = 12 处 / 8 文件**（DL-SPEC 基线，冻结 @d87d42ea）：flame_indicator 2、sparkle_confetti 1、dashboard_curiosity_card 1、insight_hub_card 2、learning_insights_overview_screen 1、predictive_insights_card 1、simulation_screen 3、simulation_chat_bubble 1。本卡后实测 **12/12 纹丝不动**（注释行不计，守卫跳过 `///`）。

---

## 4. 门禁联动（item 4 处置说明）

卡面要求「DL-SPEC 守卫新增一维：新文件禁 DS.accent 引用（ratchet 存量计数，只降不升），登记不新增 manifest 行」。核验结论：**该维已存在且语义逐字吻合，无需亦不应重复增设**——

- `check_dl_spec_ratchet.py` `Dimension("dsAccentAlias", "A1.5", "mobile-lib", pattern \bDS\.accent\b)`：new-file allowance=0（**新文件零容忍**）+ 存量 per-file ratchet 只降不升 + `--update-baseline` 拒绝抬升；
- 落地记录：B2-GUARDS @1c2aced1（SPEC §1.4.2 原文亦载「守卫已执行，基线 12 只降不升」）；
- manifest：DL-SPEC 已是单行注册（rule_guard_manifest.tsv:75），本卡零 manifest 变更；
- 守卫 `--self-test`（case2 新文件堆叠违规含 dsAccentAlias）复验 PASS。

## 5. 验证与证明（回执④）

### 5.1 flutter analyze（改动前/后对比）

| 时点 | error | warning | info | 合计 |
|---|---|---|---|---|
| 改动前（worktree @1d42786a，flutter 3.41.3） | 132 | 41 | 6699 | 6872 |
| 改动后（本卡全部落盘） | **132** | **41** | **6699** | **6872** |

- 132 个 error 全部为**存量**：third_party_plugins vendored forks（flutter_local_notifications/jpush_flutter 的 dynamic 赋值面）＋ test/ 缺 build_runner 生成物（UserStateV1 等）；**`lib/` 本体零 error**，本卡零新增（三码严格相等）。`quality/flutter_analyze_allowlist.json` 预算未动（无新增 issue 可入账）。

### 5.2 守卫

- `check_dl_spec_ratchet.py`：**PASS**——`dsAccentAlias=12/12`、coldColorLiteral=90/90、colorsDotNative=1/1、offLadderDuration=186/186、bannedCurve=24/24、breathingController=1/1、confettiPerFile=7/7、particleBypass=77/77、textHardcodedZh=0/0、gradientLiteral=303/303、errorCopyOops=6/6、competitionNarrative=0/0；`--self-test` PASS。
- `check_ux_component_convention.py`：**PASS**（rawButton=19/19 rawSpinner=8/8 rawChip=11/11 parallelClass=146/146 colorLiteral=100/100）。
- `check_ui_design_tokens_ratchet.py`：**PASS**（color=239/275 fontSize=721/727）。
- 全量 `bash scripts/run_all_rule_guards.sh --jobs 4`：见本次交付随附日志摘录（§5.5）。

### 5.3 工具链发现（供 B2-3/主会话参考，非本卡义务）

本项目工具链（flutter 3.41.3 / dart analyze）对**同包** `@Deprecated` 的使用点**不产出任何诊断**（三次全量 analyze + 单文件探针 + touch 强制摘要失效后复跑，均零 deprecation 提示；既有 27 条 deprecation 提示全在 third_party_plugins 的他包 API）。因此「新代码禁用 DS.accent」的可执行面即 SPEC §1.4.2 指定的 **DL-SPEC dsAccentAlias 守卫**（已绿）；`@Deprecated` 的价值在 IDE 语义与迁移期标注，不产生 analyze 噪声，allowlist 预算无需扩容。

### 5.4 单测

- 文件：`mobile/test/core/design/semantic_color_names_test.dart`——13 组断言：四变体×表面阶/文字阶 `same()` 同实例转发、tertiary/focus 缺口槽映射、accent=brandPrimary 且 ≠brandSecondary、语义槽/表面阶 Dart 侧锚点值钉死（与 ΔE 脚本锚点互为镜像）。
- **运行状态：被内存门拦停**——收工时点 `vm.swapusage` 空闲 **1164.38M < HEAVY 启动门 1.2G**（AGENTS 硬规则第 2 条，优先于本卡回归项），`flutter test` 未启动。验收补跑命令（单文件、串行）：
  `cd mobile && flutter test test/core/design/semantic_color_names_test.dart --concurrency=1`

### 5.5 全量守卫套件

`bash scripts/run_all_rule_guards.sh --jobs 4`：**72 规则，70 绿，2 失败（AQ/BG）——均为域外环境项，与本卡无关**，且已在纯 HEAD 克隆基线（`git clone <worktree> /tmp/b22-baseline`，AGENTS 纪律方法）上复现同样失败：

| 规则 | 失败形态 | 定性 |
|---|---|---|
| AQ（python/proto parity） | `ModuleNotFoundError: No module named 'app.gen'` | worktree 未跑 `make proto-gen`，Python gRPC 生成物缺失；HEAD 基线同败 |
| BG（proto 跨语言 parity） | galaxy/stt/user_state/websocket 等的 Dart/Go/Python 生成文件 missing | 同上，proto 生成物缺失；HEAD 基线同败（清单逐条一致） |

本卡触碰面（mobile design 两文件、新增 scripts/design/ 与 test/ 文件、v3-output 报告）不在这两守卫的扫描与依赖路径上；其余 70 规则（含 DL-SPEC/UX-COMP/UI-TOKENS/DB-HEAD 等全部 mobile 相关项）带本卡改动全绿。

---

## 6. 回执⑤：收工核查清单

| 项 | 状态 |
|---|---|
| 修改只落本 worktree（wt113） | ✅ git status 仅 2 M + 2 新路径（extension/design_system、test、scripts/design/） |
| 零 commit/push、主仓只读 | ✅ 未触碰主仓与 index（patch 用 no-index 生成，未 add） |
| 零色值改动/零视觉变化 | ✅ 语义层纯转发（`same()` 断言）；owner 字段零改动；DS.accent 值不变 |
| 临时产物清理 | ✅ /tmp 下 `b22_analyze_*.txt`、`b22_guards_full.log`、探针文件（已即时删除）、`mobile/.dart_tool`（worktree 内，随 worktree 回收）、无模拟器/无独立端口进程 |
| 交付物 | `v3-output/B2-2/changes.patch` ＋ 本 REPORT.md ＋ 代码/测试/脚本改动 |

> 遗留给 B2-3：text.tertiary 与 focus 独立定标（两处 TODO(B2-3)）；DS.accent 12 处存量迁移；§1.7【批 2 起】段的新代码「只走语义名」守卫维度（属 B2-3 门禁收尾包）。
>
> **SPEC §1.5.2「routes.dart:113 Colors.grey 单点随 B2-2 顺手清」未执行**（有意跳过）：该处是 404 页图标色（`Colors.grey` = `0xFF9E9E9E`），palette 内无等值 token，任何替换都是真实视觉变化，与本卡「零视觉变化」红线直接冲突，且不在本卡五要素清单内。建议随 B2-3 冷色归槽批按语义重评处置（错误态图标应走 error 槽或中性层，非 grey 兜底）。
