# FIX-513 调解备忘 — 42 feature portfolio 状态双真源词表分裂裁决材料

- worker：wt786（agent/node-b/wt786/p513memo @ `16ac17b4`）
- 基线对照：B-01 基线 `a2d8a10c192f451a2c11042df8e4f6227cad37f9`（2026-09-19）→ 本 memo 亲证 HEAD `16ac17b4`（main tip，含 `6a289d6a` v0.6 深挖完成 + 1 个 fleet state 提交）
- 用途：Q-08 终门前主会话拍板材料。本 memo 不改 DoD/MODULE_PORTFOLIO/B-01 任何产物。
- 方法：四源全读（DoD V3-0 / v3/00_context/MODULE_PORTFOLIO.md / v3-output/B-01 三件 / v3/00_context/MODULE_MATRIX.csv 模板）+ FIX-513 台账原文 + `git log a2d8a10c..HEAD` 删除面圈定 + 逐项开文件亲证（命令与逐条证据见 notes.md）。

---

## 0. 一句话结论

**唯一真源建议裁给 B-01（`v3-output/B-01/MODULE_MATRIX.csv` + `portfolio.json`），MODULE_PORTFOLIO.md 与 `v3/00_context/MODULE_MATRIX.csv` 模板降级为 desired-role 参考层并加注**；但 **V3-0 现状只能判 FAIL（not-yet）**：除词表分裂外，B-01 基线后的 1509 个提交已造成**全集漂移（features 目录 42→43）与两处状态翻转**（leaderboard/photon 的 HIDDEN 判定证据失效），Q-08 若按旧矩阵放行即过判——FIX-513 ②预言的风险已坐实。

---

## 1. 源清单与性质

| 源 | 词表 | 性质 | 基线以来变更 |
|---|---|---|---|
| `v3/V3_DEFINITION_OF_DONE.md` Gate V3-0 | 五态 CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE | gate 要求（「42 个 feature 有唯一 portfolio 状态」），**无逐 feature 值** | 0 变更 |
| `v3/00_context/MODULE_PORTFOLIO.md` | 扩展 8 词：CORE 15/CONTEXTUAL 15/LABS 5/SECONDARY 3/CORE_OPTIONAL 1/HIDDEN 1/INTERNAL 1/INTERNAL_CAPABILITY 1（FIX-513 行把 INTERNAL+INTERNAL_CAPABILITY 合记为「INTERNAL 2」） | **desired role**（自述「V3 产品方向」，pack 导入 0c7fa4c5）；其头注原文即「B-01 必须用当前 HEAD 填实际状态」 | 0 变更 |
| `v3/00_context/MODULE_MATRIX.csv` | 同 PORTFOLIO（desired_v3_role 列逐值一致） | desired-role **模板**，B-01_current_state 列 42 行全部 TO_VERIFY、从未回填 | 0 变更 |
| `v3-output/B-01/{MODULE_MATRIX.csv, portfolio.json}` + REPORT + REVIEW_RECEIPT | **恰为 DoD 五态**（CORE 15/CONTEXTUAL 18/LABS 5/HIDDEN 4/RETIRE 0，42/42） | **实测实际状态**@a2d8a10c，逐 feature 证据链（路由注册/入口引用/深链/curl/DB 只读），独立复核 verdict ACCEPT | 0 变更（但其描述的现实已漂移，见 §4） |

**关键结构性事实**：desired（PORTFOLIO/模板）与 actual（B-01）的分裂不是事故，是 pack 的分层设计——PORTFOLIO 头注明言「desired role 是 V3 产品方向；B-01 必须用当前 HEAD 填实际状态」；RECEIPT §7 亦认定「v3/00_context/MODULE_MATRIX.csv 是 desired-role 模板……Worker 填充行为正是卡片指令，不构成重建真源」，且已逐条记录状态过渡（achievement SECONDARY→CONTEXTUAL、photon/shop SECONDARY→HIDDEN、reflection CONTEXTUAL→HIDDEN 属授权内偏离、intent INTERNAL→CONTEXTUAL 为枚举所限）。**真正的缺陷是「唯一性」从未被文档层落字：模板回填列没回填、PORTFOLIO 没降级加注，于是两份文件至今同台并对同一 feature 给出不同值。**

---

## 2. 42 feature 三源对照表

DoD 要求态列 = V3-0 对每项的约束（∈五态且唯一），DoD 本身不含逐项值。

| # | feature | DoD 要求态 | PORTFOLIO（desired） | B-01（actual@a2d8a10c） | 分歧性质 |
|---|---|---|---|---|---|
| F01 | achievement | ∈五态唯一 | SECONDARY | CONTEXTUAL | **实质过渡**（D17 支撑；RECEIPT §7 已录） |
| F02 | aurora | ∈五态唯一 | CORE | CORE | 一致 |
| F03 | auth | ∈五态唯一 | CORE | CORE | 一致 |
| F04 | calendar | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F05 | chat | ∈五态唯一 | CORE | CORE | 一致 |
| F06 | cognitive | ∈五态唯一 | CORE | CORE | 一致 |
| F07 | community | ∈五态唯一 | CORE_OPTIONAL | CONTEXTUAL | **词表分裂**（映射可消解，B-01 注记 CONTEXTUAL(CORE_OPTIONAL)） |
| F08 | document | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F09 | documents | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F10 | error_book | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F11 | experience | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F12 | file | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F13 | focus | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F14 | galaxy | ∈五态唯一 | CORE | CORE | 一致 |
| F15 | goal | ∈五态唯一 | CORE | CORE | 一致 |
| F16 | home | ∈五态唯一 | CORE | CORE | 一致 |
| F17 | insights | ∈五态唯一 | CORE | CORE | 一致 |
| F18 | intent | ∈五态唯一 | INTERNAL | CONTEXTUAL | **词表分裂**（枚举所限折叠；v3_surface 保留 INTERNAL 语义） |
| F19 | knowledge | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F20 | leaderboard | ∈五态唯一 | HIDDEN | HIDDEN | 基线一致；**HEAD 已漂移**（V3-FIX-534，见 §4） |
| F21 | memory | ∈五态唯一 | CORE | CORE | 一致 |
| F22 | mirofish | ∈五态唯一 | LABS | LABS | 一致 |
| F23 | notification_center | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F24 | onboarding | ∈五态唯一 | CORE | CORE | 基线一致；**HEAD 全集漂移**（V3-FIX-533，目录已删，见 §4） |
| F25 | openclaw | ∈五态唯一 | INTERNAL_CAPABILITY | CONTEXTUAL | **实质分歧**：实测可达（/openclaw 注册 + home 卡 + chat delegate 3 处 + 深链）vs desired 内部能力 |
| F26 | photon | ∈五态唯一 | SECONDARY | HIDDEN | **双重**：实质过渡（D17）+ HEAD 已漂移（redeem-pro 可达，见 §4） |
| F27 | plan | ∈五态唯一 | CORE | CORE | 一致 |
| F28 | reflection | ∈五态唯一 | CONTEXTUAL | HIDDEN | **实质分歧**：实测孤儿路由（常量 0 外部引用+字符串导航 0）vs desired；RECEIPT §7 录为授权内偏离 |
| F29 | report | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F30 | reviews | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F31 | seed_library | ∈五态唯一 | LABS | LABS | 一致 |
| F32 | settings | ∈五态唯一 | CORE | CORE | 一致；证据已过时（4 屏→2 屏，见 §4） |
| F33 | shop | ∈五态唯一 | SECONDARY | HIDDEN | **实质过渡**（D17+D20 支撑）；FIX-05 FIXED 后 HIDDEN 完全成立 |
| F34 | simulation | ∈五态唯一 | LABS | LABS | 一致 |
| F35 | splash | ∈五态唯一 | CORE | CORE | 一致 |
| F36 | task | ∈五态唯一 | CORE | CORE | 一致 |
| F37 | theater | ∈五态唯一 | LABS | LABS | 一致 |
| F38 | tools | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F39 | translation | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |
| F40 | user | ∈五态唯一 | CORE | CORE | 一致 |
| F41 | visual_elements | ∈五态唯一 | LABS | LABS | 一致 |
| F42 | vocabulary | ∈五态唯一 | CONTEXTUAL | CONTEXTUAL | 一致 |

**规模**：42/42 对照完成。一致 35；分歧 7（词表分裂-映射可消解 2：community/intent；实质分歧/过渡 5：achievement/openclaw/photon/reflection/shop）。**全部 7 处分歧均已被 B-01 v3_surface 列或 RECEIPT §7 事先记录并给出依据——不存在无出处的静默改值。**

---

## 3. 扩展词表 → 五态映射表（随裁决产出）

裁决语义判据：五态是**实际状态**词表（可达性×产品面），扩展词多为**产品意图/降权语义**；意图信息不丢弃，折叠进注记（沿用 B-01 v3_surface 列的既有实践）。

| 扩展词 | 出现项 | → 五态映射（推荐） | B-01 先例 | 判据 |
|---|---|---|---|---|
| SECONDARY | achievement, photon, shop | **可达且产品面活→CONTEXTUAL；不可达/孤儿/空目录→HIDDEN** | achievement→CONTEXTUAL（6 路由+深链+入口）；photon/shop→HIDDEN（孤儿/空目录） | 五态无「次级」档；「可选轻量/非核心」是产品规则不是状态，留 v3_surface 注记（D17 降权语义） |
| CORE_OPTIONAL | community | **CONTEXTUAL** | CONTEXTUAL(CORE_OPTIONAL) 注记 | 「可选但 Tab 级可达」=CONTEXTUAL；「solo 产品完整」规则留注记（D18） |
| INTERNAL | intent | **CONTEXTUAL + 注记「INTERNAL 能力，无用户面」** | intent CONTEXTUAL（枚举所限，已注明） | 数据层被 chat 活消费：非 RETIRE（活着）、非 HIDDEN（本就不是产品面）；五态枚举所限折叠是 B-01 已实践且被 RECEIPT 接受的口径 |
| INTERNAL_CAPABILITY | openclaw | **按可达性证据定档：实测可达→CONTEXTUAL** | openclaw CONTEXTUAL（路由+入口+深链实证） | 可达性证据优先于产品意图；「不做第二 AI 中心」意图留注记（D16） |
| （RETIRE） | — | 维持五态原生档 | RETIRE=0；leaderboard 死屏曾有 RETIRE 倾向建议 | 见 §4：死链已删但自我锚可达，RETIRE 判定需 B-01Δ 复核后再定 |

**注记格式建议**（供主会话加注时取用，一行式）：`gate 权威口径=B-01 五态；本表 desired role 语义折叠规则：SECONDARY→按可达性 CONTEXTUAL/HIDDEN，CORE_OPTIONAL/INTERNAL/INTERNAL_CAPABILITY→CONTEXTUAL+注记；过渡记录见 v3-output/B-01/REVIEW_RECEIPT.md §7。`

---

## 4. 漂移清单（a2d8a10c → 16ac17b4 亲证）

`git log a2d8a10c..HEAD` = **1509 commits**；粗粒度触文件不可用（42 目录全被触及），以下为**删除面+路由/入口开文件亲证**后的漂移全集。

### A 类：状态翻转（B-01 判定证据已失效，过判风险本体）

| feature | B-01 册载 | HEAD 实测（亲证） | 关键证据 |
|---|---|---|---|
| leaderboard | HIDDEN（死屏：screen 0 引用、路由未注册、RETIRE 倾向） | **不再是死屏**：死链三件套已删（`4d353132`，D-COMM-1/D-COMM-4 销账见 KNOWN_CODE_DEBT_LEDGER #3）；feature 转型为「自我锚」唯一路由面 `/leaderboards/self-anchor`（leaderboard_routes.dart:22，routes.dart:411 挂载），**2 处真实入口**：plan/sprint_screen.dart:64、community/squad_detail_screen.dart:295 | 全站综合榜仍不路由（COMM-LB 守卫固化），D17 对「榜」的禁令仍在；但「feature 目录=死代码」的 B-01 前提已翻 |
| photon | HIDDEN（孤儿：余额卡 0 消费者、transfer 0 入口） | **不再是孤儿**：`/photon/transfer` 删除、PhotonBalanceCard 删（交易历史屏迁出后删除，`c69c6879`）；`/photon/redeem-pro` 注册（routes.dart:429）+ **2 处真实入口**（user/profile_screen.dart:697、shop/shop_screen.dart:64）+ redeem 屏内二级入口进交易历史 | B-01 的三项 HIDDEN 证据（孤儿卡/transfer 0 入口/history 仅孤儿引用）全部消失 |

### B 类：全集漂移（「42」本身已不成立）

| 项 | HEAD 实测（亲证） | 关键证据 |
|---|---|---|
| onboarding 目录删除 | `mobile/lib/features/onboarding/` **已不存在**（`e610853e` FIX-342 删 interactive 4 屏连 barrel 清空）；但 onboarding 功能本体未死：`/onboarding/persona` `/onboarding/modeling-chat` 常量与 GoRoute 活在 user/user_routes.dart:35-36,76-77 | B-01 的 module_path 失效；CORE 判定的功能实质仍在（经 user feature 承载） |
| journey 新增未入册 | 2026-09-25 新建（J-04 `02b82cd2`、J-06 `7bd6ade3`）；FirstActionCard 挂 home dashboard 可达；后端 /journey 组落地 | **不在 DoD 42 册、不在 PORTFOLIO、不在 B-01**——三个真源都没有它 |
| recovery 新增未入册 | 2026-09-25 新建（J-05 `c4c36ead`）；StuckJourneySheet 三处真实入口（home cockpit 卡住 CTA/goal 详情卡住键/任务执行屏帮助） | 同上 |
| **目录计数** | `ls mobile/lib/features/` = **43**（基线 diff：+journey +recovery −onboarding） | DoD「42 个 feature 有唯一状态」字面已破坏 |

### C 类：证据过时、状态不变（CORE/CONTEXTUAL 判定不受影响，但 B-01 证据行需勘误）

| feature（状态不变） | 漂移 | 证据 |
|---|---|---|
| settings（CORE） | B-01「4 屏」→现 2 屏：transparency_settings_screen 删（`aa6a9667` FIX-182/183）、data_usage_dashboard_screen 删（`8e837e8a` FIX-440/GOV-015） | find 亲证余 openclaw/accessibility 两屏 |
| user（CORE） | WS6 profile_transparent_screen 全链删（`4a7c3414` FIX-489，2636 行）、learning_mode_screen+preference_controller_2d 删（`a29ed3f1` FIX-490） | 孤儿屏摘除，CORE 不动 |
| insights（CORE） | PredictiveInsightsCard 假精确面删除（`667001e6`） | CORE 不动 |
| home（CORE） | omnibar/visual_renderer 装饰降级删除（`7729f5a1`） | CORE 不动；连带 intent 证据文字过时 |
| intent（CONTEXTUAL） | omnibar 消费者消失，但 chat 直连消费仍在：intent_preview_dialog.dart:9-10、intent_analysis_button.dart:8-9 import intent repository/models | CONTEXTUAL 站得住，仅证据行需改 |
| task（CORE） | streak_details_screen 迁至 achievement feature（原 B-01 引用它作 shop 唯一入口） | CORE 不动 |

### D 类：向合规漂移（B-01 遗留张力已消除）

| 项 | 漂移 | 证据 |
|---|---|---|
| shop（HIDDEN） | B-01/RECEIPT E11 的 gate 张力（「可达但孤立」1 条真实入口）**已消除**：入口整块移除+后端 RELEASE_ENABLE_SHOP 旗默认 False→403 先于鉴权 | V3-FIX-05 FIXED@`e3ff2df9`（台账原文）；HEAD grep `push('/shop')` 外部 0 命中、streak_details 无 shop 引用 |
| visual_elements（LABS） | 后端 RELEASE_ENABLE_VISUAL_ELEMENTS 旗控（backend/app/api/v1/router.py:306） | LABS 语义强化，状态不变 |

**三份真源文件（DoD/PORTFOLIO/模板 CSV）自 a2d8a10c 起 0 变更**（git log 亲证）——分裂与漂移在 HEAD 上均未消费。

---

## 5. 裁决建议

### 5.1 唯一真源：B-01（理由）

1. **词表合规**：B-01 恰为 DoD 五态；PORTFOLIO 扩展 8 词字面不可能满足 V3-0。裁 PORTFOLIO 为真源则 gate 永远无法按原文判。
2. **分层自洽**：PORTFOLIO 自述 desired role，且其头注钦定「B-01 必须用当前 HEAD 填实际状态」；模板 CSV 的 B-01_current_state 列本就是为 B-01 回填设计的（未回填是实现缺口，不是设计否定）。裁 B-01 不是改架构，是把 pack 的既定分层落字。
3. **证据与复核**：B-01 逐 feature 证据链（路由/入口/深链/curl/DB）+ 独立复核 ACCEPT（含 11 项勘误全记录）；PORTFOLIO 是无复核的 pack 导入。
4. **分歧已有出处**：7 处分歧全部被 v3_surface/RECEIPT §7 记录——裁 B-01 为准只是追认既有记录的过渡，无一项是静默改值。

### 5.2 另一个如何降级加注（供主会话执行，本 worker 未动文件）

- `MODULE_PORTFOLIO.md`：头注下一行加「**gate 权威口径见 `v3-output/B-01/`（五态）；本表为 desired-role 参考，词表折叠规则见 FIX-513 裁决（SECONDARY→按可达性 CONTEXTUAL/HIDDEN；CORE_OPTIONAL/INTERNAL/INTERNAL_CAPABILITY→CONTEXTUAL+注记）；过渡记录见 B-01 REVIEW_RECEIPT §7**」。表体不改。
- `v3/00_context/MODULE_MATRIX.csv`：同样加注「B-01_current_state 列废弃 TO_VERIFY 语义，实际状态以 v3-output/B-01 为准」；或直接声明该文件与 PORTFOLIO 同为 desired 层、不再承担回填职责。
- DoD 不改（V3-0 五态表述本身没有缺陷）。

### 5.3 漂移处置：**scoped delta 审计（B-01Δ）+ 显式钉时点注记，二者都要**；不建议全量重跑

- **立即（Q-08 文字层裁决同步）**：在 gate 记录层钉注记「B-01 矩阵=状态@a2d8a10c（RECEIPT ACCEPT）；a2d8a10c 之后的现实以 B-01Δ 为准」。没有这条注记，B-01 与 HEAD 的错位在 Q-08 判定里就是隐形过判。
- **B-01Δ 卡范围（约 5 项 reachable 面+全集问题，非 42 项全跑）**：①leaderboard 五态重定（HIDDEN 已失效：死链删+self-anchor 可达；候选 CONTEXTUAL+「全站榜禁令不变」注记，或按产品裁决）；②photon 五态重定（HIDDEN 已失效：redeem-pro 双入口；候选 CONTEXTUAL/SECONDARY 语义→CONTEXTUAL）；③onboarding 全集定位（目录并入 user 后，feature 身份与 module_path 如何登记）；④journey/recovery 入册（新 feature 定态+改「42」计数口径为「N=43」或把二者并入 host feature 的子面）；⑤shop/reflection 复核确认（预期维持 HIDDEN，shop 的 FIX-05 已 FIXED 使其比基线更干净）。
- **不建议全量重跑 B-01**：33/42 状态稳定且证据类型未变（本 memo 已对删除面全覆盖核查）；全量重跑比例失调。**也不建议只钉注记**：A/B 类漂移若不入册，V3-0「42 有唯一状态」字面与精神双不过——两处可达面翻转+两个未入册可达 feature 正是「用户可达的半成品入口」条款要抓的形态。

---

## 6. 对 Q-08 V3-0 gate 判定的影响面

**无论真源裁决如何，V3-0 现状只能判 FAIL（not-yet）**，理由四条按阻塞力排序：

1. **全集破坏（硬阻塞）**：HEAD features 目录=43，journey/recovery 可达未入册、onboarding 目录消失——「42 个 feature 有唯一 portfolio 状态」对当前代码库字面不可满足，且未入册可达面直接踩「不存在用户可达的半成品入口」（journey/recovery 虽是成品卡交付，但产品状态无裁决=词表外状态）。
2. **状态翻转未裁决（硬阻塞）**：leaderboard/photon 的 B-01 HIDDEN 值已不描述现实；按旧矩阵判=过判（FIX-513 ②预言命中）。
3. **双真源未消除（文档阻塞）**：三份文件 0 变更@HEAD，唯一性裁决+降级加注动作尚未执行。
4. **基线后 1509 commits 仅做了删除面+可达性 delta 复核（残余风险）**：非删除类的入口增删（如新增入口使某 LABS 可达）未逐项穷举，B-01Δ 才能闭。

**采纳本 memo 建议后的闭账路径**：①主会话拍板 §5.1/5.2（唯一真源+加注，1 commit 文字层）；②映射表（§3）随裁决入册；③开 B-01Δ scoped 审计卡（§5.3 范围）；④B-01Δ 交回后 V3-0 才具备判 PASS 的证据基础。①②不阻塞于③④，可先行——它们解决的是「唯一真源」缺陷本体（FIX-513 ①）；③④解决的是漂移缺陷（FIX-513 ②）。

---

## 7. 本 memo 的边界与诚实声明

- 只读调解：未改 DoD/MODULE_PORTFOLIO/模板 CSV/B-01 四源任何一个字节；未动台账；未 push；未碰运行栈（无 docker/:50051/:8000/:8080 操作——漂移亲证全部基于 git 树+开文件 grep，DB 行数/curl 未复测，B-01Δ 应含）。
- 漂移亲证覆盖删除面全量（`--diff-filter=D` 圈定 8 个 feature 的 20 个删除 dart 文件逐一归因）+ 可达性抽查（路由挂载/外部引用/深链映射逐项 grep）；未做模拟器运行时巡检（B-01 原册 retest_needed 5 项仍开放）。
- HEAD 取样点为 `16ac17b4`（分支时 main tip）；main 若继续前进，A/B 类结论仍稳（均由历史提交因果支撑），C 类证据行数可能再漂。
