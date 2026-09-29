# V4-G07 预备侦察报告（scout, 2026-09-29, main@05ef4816, 只读+仅本目录写入）

> 用途：G07「账号/设置/通知/异常/长尾——四风格商业化完备」（PENDING, implementation, risk=normal, 单审, ui-polish-g07 锁, 非 HEAVY, deps=[]）派单直接引用。卡面 deps 虽空，运营序上**等 U06**（fleet note 30:55 原文「G04 在修、G07 等 U06」）——U06 动账号升级屏，与 G07 账号域屏面重叠。
> 红线声明：本报告为侦察产物非验收证据；未执行 G07 本体；未改任何既有文件；未动 worktree（`git worktree list` 只读清点：wtF583/wtG04/wtQ01）；引用的 fleet notes/测试清单均为 2026-09-29 时点实录，G07 执行时逐条亲验。
> 时点备注：侦察期间 main 由 09cbe541 后推进至 05ef4816（FIX-581 闭账+CI54 双红双修+G04 返 REVIEW_READY）；fleet notes 读至 [2026-09-30 35:40]。

---

## 一、卡面解读与编号勘误

### 1.1 卡面要点（v4/04_tasks/tasks.json V4-G07 原文）

- 与 G04/G06 同模板：objective=四风格任一可作发布默认无风格专属缺陷；work=逐屏×四风格走查（清零 classic-only 硬编码/对比度与 200% 文本/reduce-motion 等价复算/15 态覆盖/每风格 golden+语义钉 F05 判例/缺陷就地修）。
- **modules = auth / user / settings / notification_center / splash**——这是 G07 的边界权威（不含 task/goal/community/error_book）。
- acceptance 三条：①家族内零风格专属缺陷；②四风格各有确定性 golden+语义钉且 CI 可失败；③既有功能测试全绿+analyze 零+repeat 棘轮只降不升。
- path_policy：UI 走 core/design 令牌；RF-06 高危面可改须 diff 叙证；l10n 双语纯增量；风格真源唯一（theme_manager/pixel_preview_theme）。
- stop_conditions：行为语义缺陷超风格面→登记 FIX 不顺手修；三轮不改善写反例归因；preview 通道外需发布面决策项→登记 Q08 待裁。
- 锁 ui-polish-g07 与 G04 的 ui-polish-g04、G06 的 ui-polish-g06 互斥不重叠；单审（risk=normal）、非 HEAVY——是 G 系最轻的收尾卡。

### 1.2 L/C 编号体系与两处勘误（路径实查）

L/C 编号权威 = **v3-output/WT401-Q03-VISUAL/screens.md**（V3 视觉走查屏清单：C01-C13 核心 journey 屏 + L01-L85 长尾屏）。实查后对任务书两处修正：

1. **「通知 L13」系笔误：通知中心 = C13**（`/notification-center` → `notification_center_routes.dart:9` 注册 NotificationCenterScreen）；L13 = `/sprint` 冲刺页，属任务/计划域，不在 G07 家族。
2. **C08（/errors 错题列表）与 L81（/errors/:id）屏本体属「星图/学习/错题/资料」家族 = G04 卡**（modules 含 error_book），L82/L83/L84/L85 分属 goal/task/community 家族（G04/G06 已闭面）。G07 的「异常态」职责按卡面 modules 与 SCREEN_FAMILIES L22 行读作：**异常表面族**（404 errorBuilder/离线/登录失效/模型失败分流 + 深链落对象失效替代页模式）的四风格完备 + unknown-id 逐域接线的裁决登记，**不重写 G04/G06 已验收屏面**（no_duplicate_rule 原文）。

---

## 二、屏面清单 × 四风格完成度粗判 × U06 重叠标注

### 2.1 屏面与文件实查（mobile/lib 路径全部实读）

| 域 | 屏（WT401 编号） | 文件 | 规模/既有测试 | 四风格完成度粗判 | U06 重叠 |
|----|-----------------|------|--------------|----------------|----------|
| 账号 | C05 /profile 我的 | user/…/profile_screen.dart | 1114 行；1 测 | 零 golden/零钉；B2-3a 已清部分硬编码（routes errorBuilder 同款判例域） | 弱（U06 落点裁决间接相关） |
| 账号 | L34 /profile/edit | edit_profile_screen.dart | 1 处 Colors.transparent（豁免内）；0 专属测试 | 未走查 | 无 |
| 账号 | L43 sessions / L44 security-log / L45 export-data | session_management/security_log/export_data_screen.dart | 仅 export_data 1 测 | 未走查；**account_security_screen.dart:93/102/111/120 四处真实硬编码 hex accentColor（0xFF7A8C64 等）=G07 必修面** | 无 |
| 账号 | 其余 /profile/* 长尾 | delete_account/social_accounts/password_reset/theme_settings/smart_push/system_updates(L39)/bgm_library(L36)/poster_studio(L38)/openclaw_settings(L41)/sync_center(L42)/task_reminders/skills/admin_operations/memory_settings 入口 | 全家族 24 屏 18945 行 | **poster_studio_screen.dart:304/332/352/377 四处 hex accent（0xFFF0C676 等）需甄别：内容调色板（LABS 域 U15-E 冻结判例）vs 令牌外硬编码**；theme_settings:165/smart_push 等仅 transparent/white（A1.2 豁免内） | 无 |
| 账号 | **升级屏** /profile/upgrade-guest | **guest_upgrade_screen.dart** | 1 测（validation_timing） | 未走查 | **最高危单点：U06 :74/:127 两处 `context.go('/profile')` 导航缺陷（U06-prep 实勘，本次复核仍在码）——U06 改落点，G07 改风格面，同文件两线** |
| 认证 | C06 /login、L01 register、L02/L03 forgot/reset、L04/L05 legal | auth/…/login_screen.dart 等 5 屏 | login 3 测（semantics/submit/example_entry）+register 3 测（o3/f539/a5） | 未走查；login:438/splash:101 Colors.white（豁免内）；**U06 改 register 落点断言与 routes redirect——测试文件族重叠** | **中：U06 注册腿落点+routes redirect 回填** |
| 设置 | L35 /profile/settings 统一设置 | unified_settings_screen.dart | **4117 行（全仓最大屏）**；4 测（sfx/bgm/ambient/no_fake_confirm，S01-S03/U14 链） | 四开关面（动效/配乐/提示音/触觉，SCREEN_FAMILIES L22）行为面已验收；风格面零 golden/零钉 | 无 |
| 设置 | accessibility/settings 域 | accessibility_settings_screen.dart + openclaw_settings | accessibility 有 flag 门 golden（ENABLE_ACCESSIBILITY_GOLDEN，旧模式）+1 测 | flag 门 golden ≠ 确定性常态 golden（G 系新口径）——需按 G06 模式重钉 | 无 |
| 通知 | **C13** /notification-center + analytics + list | notification_center_screen.dart（613 行）等 | center 1 测 + list 1 测 + push_card/recall golden（组件级，非屏级） | 屏级四风格零覆盖；U14 L6：深链落真实对象只接了 /tasks/:id/execute | 无 |
| 异常 | 404 errorBuilder | app/routes.dart:117-146 | 已令牌化（B2-3a neutralOutline 快照判例） | 单态在岗、四风格未钉 | **中：U06 同文件改 redirect 段（:157-242），errorBuilder 相距 30 行** |
| 异常 | 失效替代页 | core/design/widgets/object_unavailable_surface.dart（U14 交付，112 行）+ task_execution_deep_link_gate | 5+2 测（U14） | missing/offline/auth 三语义已建；**四风格零钉**；仅 1 消费方 | 无 |
| 异常 | 登录失效第三面 | routes.dart 路由闸兜底 | U14 L4 登记取舍（第二身份系统禁令） | 维持现状，G07 不翻案（登记即可） | 无 |
| 长尾 | splash + 离线 banner | splash_screen.dart（1 测 two_segment）/offline_banner.dart | N20 品牌窗语义已验收 | splash 四风格未钉；U06 modules 含 splash（重定向中转链）——splash 风格面改动低危 | 弱 |

### 2.2 家族级硬缺口（G07 的真实工作量所在）

1. **零四风格 golden**：`find test -path "*goldens*" -name "*.png" | grep -iE "login|settings|notif|splash|profile|auth"` = 空集——家族是 G 系最后一块无 golden 面板。
2. **零家族对比度守卫/零语义钉**（G02/G06 同款 v4_g*_family_contrast_guard_test 在 G07 域无对应物）。
3. 硬编码 hex 8 处待处置（account_security 4 + poster_studio 4）；DL-SPEC A1.2/A1.3 ratchet 未把它们计捉（features 域 0xFF 字面量应被 coldColorLiteral/colorsDotNative 扫描——**实查 DL-SPEC 对 account_security 四处未判负，提示豁免口径或阈值需在 G07 复核**，勿假设守卫已盖）。
4. l10n 已达标（家族内 `Text('中文…')` 字面量零命中，unified_settings l10n 消费 122 处）——A3.2 零容忍压力小。
5. 15 态统一检查表（SCREEN_FAMILIES L25）中家族可 widget 级复现态：default/empty/error/离线/200% 字体/键盘遮挡（L22「品牌框不能遮键盘和勾选」明令）/reduce-motion——现仅散点覆盖。

---

## 三、兄弟卡模式复用清单（G01-G06 已闭 5 卡实证模式）

| 模式 | 载体（实查路径） | G07 复用要点 |
|------|----------------|--------------|
| G06 三层钉结构（最新判例） | ①golden+语义钉：test/goldens/g06_four_style/g06_four_style_golden_test.dart（真实组件+确定性 seed+四 profile 循环+matchesGoldenFile）；②配对层守卫：test/widget/v4_g06_family_contrast_guard_test.dart（token 数学复算 + **E- 控制组判负防探针自证**）；③实现级钉：achievement_map_state_chip_nail_test.dart（泵真实屏断言墨色==DS.textSecondary） | **两层口径不可互替**：G06R1 M-B mutation（回退 white70）在配对层全绿存活（不泵屏），靠实现级钉补杀。G07 对 unified_settings 开关行/notification 卡片/登录按钮等修面对，必须 golden+守卫+至少一处实现级钉三件套 |
| map_state_chip 实现级钉模式 | g06 R1-F2 返修（07c6f31a）：M-B 回退红/还原绿双向亲跑后才算钉死 | G07 硬编码清零（account_security 四 hex）照此办理：mutation 回退旧 hex 必红 |
| B04 容差比较器（FIX-581 后） | test/goldens/golden_family_drift_guard.dart（kGoldenEnvDriftBand=0.005 带界）+ b04_harness.dart（9 surfaces×viewport，G06 golden 即消费方）；**FIX-581@09cbe541 环境感知：本地 0.5% 不变，GITHUB_ACTIONS ×2.0=1.0%**；dusk 异常破案（FlutterError 投递错位→TestFailure 归属） | G07 golden 直接 `b04InstallTolerantComparator`（g06 测试头 import 同款）；**无需自造容差**；CI54 双红已修（e694242d：G05 两枚旧钉对齐 G03 真源——教训：**新钉的方案色真源跟随最新语义演进**，勿抄旧卡 hex） |
| U15 repeat 棘轮 | test/widget/u15_longtail_closure_guard_test.dart B 组：`.repeat(` 文件集 ⊆ kRepeatBaseline49（现 48 路径，FIX-565 后）/上界 49，只降不升；现值 48 文件/90 调用点（G04 记录「48/90 零漂移」） | G07 验收③「repeat 棘轮只降不升」即此 guard；家族新增动效**禁 `.repeat(` 无门引用**（splash 品牌窗/unified_settings 开关动效注意）；顺手清尾按 U15 登记表优先级 |
| DL-SPEC 守卫 | scripts/guards/check_dl_spec_ratchet.py（manifest:76）：colorsDotNative/coldColorLiteral/offLadderDuration/textHardcodedZh 零容忍/gradientLiteral/dsGradientApiCalls 等 ratchet 维度 | G07 新增面新文件零容忍；提交前 `bash scripts/run_all_rule_guards.sh` 全量基线留 run_manifest；G06 闭账标准「DL-SPEC exit 0+analyze 0」照抄 |
| golden 纪律 | EVALUATION_PROTOCOL：基线签发仅基线机（darwin arm64/Flutter 3.41.3）`flutter test --update-goldens`；基线变更独立签理由；G02 系 25 张走 Linux 跳过口径、G03 走 env 门控采集——三口径并存，**FIX-581 审计已收敛比较器面** | G07 用 G06 同款（确定性 PNG+容差比较器常态比对，无 skip 门）；签发机即本机 darwin arm64 |
| 登记不修判例 | G01 weather lerp 白基料（登记待 Q08 类裁决）；U14 L4 登录失效第三面（路由闸兜底，不建第二身份权威） | G07 大概率同类项：poster_studio 内容调色板甄别、L42 sync-center 密集信息——超出风格面的登记不顺手修 |

---

## 四、U06×G07 冲突预案

### 4.1 重叠面实查（文件级）

| 文件 | U06 动作（U06-prep scout §一/§三） | G07 意向动作 | 冲突级 |
|------|-----------------------------------|-------------|--------|
| mobile/lib/features/user/presentation/screens/guest_upgrade_screen.dart | :74/:127 两处 `context.go('/profile')` 改落点（邮箱/社交两腿） | 风格走查+可能的令牌/布局修补 | **高（同文件双线）** |
| mobile/lib/app/routes.dart | redirect 落点裁决回填（pending??'/home' 链，:190-242）+ 纯函数一正一反测试 | errorBuilder 四风格钉（:117-146）——同文件不同段 | 中 |
| mobile/test/features/auth/**、guest_upgrade_*test | 落点断言收紧（目标路由≠/profile）、J02 驱动回填 | 新增 golden/守卫测试落同目录，命名空间可能相撞 | 中 |
| first_action_card / episode_resume_provider / auth_provider（测试） | W2 bootstrap 接线+身份清除链断言 | 零意向 | 无 |
| l10n arb | U06 确认反馈新键 | G07 l10n 纯增量（若有） | 低（U14 L9 判例：并集后 gen-l10n 再生） |

### 4.2 推荐序：U06 先合并（唯一推荐）

1. U06 本就排队：Q01 已返 REVIEW_READY@12b3bdba 待 R1 → R1 过闭卡解锁 U06 → U06（heavy、ui-onboarding 锁、模拟器单槽）→合并。正常节奏下 G07 开卡时 U06 已在 main。
2. G07 开卡动作：基于 U06 合并后 main 开分支；guest_upgrade 升级屏的 golden/走查以 **U06 后落点行为**为基线（升级成功不再落 /profile，落点面语义随 U06 裁决）；家族矩阵把「升级成功反馈面」按 U06 新语义断言，G07 不重复裁决。
3. 顺带收益：U06 修完注册/升级腿后，G07 的 15 态走查（取消/失败/权限失效态）才有稳定行为基线，避免风格返工。

### 4.3 并行预案（不推荐，仅 10/3 EOD 仍未闭时的降级）

- 文件锁清单：guest_upgrade_screen.dart、routes.dart redirect 段（:157-242）**归 U06 全权**；G07 对两文件只读，发现的风格缺陷按 stop_conditions ①「登记 FIX 不顺手修」。
- G07 可先行域（与 U06 触面零交集）：notification_center（C13+analytics+list）、settings 域（unified_settings/accessibility/theme）、异常表面（object_unavailable_surface 四风格钉+404 errorBuilder 的守卫测试可放独立文件不碰 routes.dart 本体）、splash、/profile 子页长尾（L34/L36-L45 中非升级屏）。账号认证屏（login/register）测试目录分片：G07 新测试文件禁用 *_landing_test/guest_upgrade_* 前缀。
- 降级序里 golden 签发分两批：先行域一批、账号域等 U06 合并后补签（基线变更独立签理由条款覆盖分批）。

---

## 五、工作量与 MVP 切面（10/4 时间盒）

### 5.1 全量版（依赖全闭理想轨）

- 家族体量：user 域 24 屏 18945 行 + auth/settings/notification/splash 5 屏 3844 行 ≈ **22.8k 行屏面代码**逐屏×四风格——G06（约 10 屏域）耗 1 实现+2 审查+返修一轮；G07 屏数为其 2 倍以上。
- 估 3-4 个实现会话 + 1 审查（单审）+ 无 HEAVY 槽：①守卫三层搭建+unified_settings/notification/profile 主面 ②auth 域+异常表面+硬编码清零 ③长尾子屏走查+15 态抽查+收口五件套。golden 估 16-24 张（4-6 面×四风格，G06 为 8 张）。

### 5.2 MVP 切面（10/4 内部交付的最小完备）

- **必保**（2 实现会话 + 1 审查）：
  1. 家族守卫三层：v4_g07_family_contrast_guard_test（配对层+E- 控制组）+ 1 个实现级钉（建议 unified_settings 开关行或 account_security hex 清零处）+ 4-6 关键面四风格 golden（unified_settings 代表面 / notification-center / login / splash / object_unavailable_surface 三语义 / 404 errorBuilder）；
  2. 硬编码清零：account_security 四 hex 就地令牌化（mutation 双向验证）+ poster_studio 四 hex 甄别（内容调色板→沿 U15-E 冻结判例登记，或令牌化）；
  3. 验收③三件：既有功能测试全绿+analyze 0+repeat 棘轮 48 只降不升实录；DL-SPEC exit 0。
- **可登记债（不损 MVP 判据）**：24 屏逐屏 15 态全走查（抽查代表态：default/empty/error/离线/200%/键盘遮挡）；L42 sync-center 等低流量长尾屏四风格细走查；U14 L6 深链落对象逐域推广（**超 G07 modules 边界，登记裁决项归 Q08/后续卡，不实施**）；accessibility 旧 flag 门 golden 迁移常态口径（可并入 golden 批次）。
- 单审靶预登记：①golden 分母如实（几面×几风格，缺谁登记谁）；②repeat 棘轮零触碰证明；③poster_studio 甄别是否放行（内容调色板 vs 令牌外）；④新增面 DL-SPEC 零容忍；⑤**U06 合并态核对**——升级屏面断言是否基于 U06 后行为（防风格卡回退导航语义）。

### 5.3 派单前置检查清单（开卡时逐条亲验）

U06 是否已闭账合并（tasks.json 状态）→ main 集成 SHA 测试基线（CI55 守望结果）→ wtG04 是否已闭（G04 闭 = G 系 6/7，G07 是末张）→ 磁盘 df ≥15G → ui-polish-g07 锁经 fleet.py 申领。

---

## 附：本侦察证据基座（全部实查于 main@05ef4816，时点 2026-09-29）

- 卡库：v4/04_tasks/tasks.json（65 卡；G07/U06/G04/G06/Q01 全字段 dump）。
- 编号权威：v3-output/WT401-Q03-VISUAL/screens.md 全表（C01-C13/L01-L85 + §C 参数屏未挂载说明）；v4/01_product/MODULE_MATRIX.json（43 模块 F 编号与 task_ids 映射——与 L/C 编号**无涉**，甄别记录在案）。
- 规范：v4/02_design/{SCREEN_FAMILIES.md（L21-22 本家族行+L25 十五态）,ACCESSIBILITY_ASSETS.md,DESIGN_SYSTEM.md,TOKENS.proposal.json 存在性}。
- 屏面实查：mobile/lib/features/{user（24 屏 18945 行）,auth,settings,notification_center,splash}；app/routes.dart 全 redirect+errorBuilder 实读；user_routes.dart 全子路由实列；guest_upgrade_screen.dart :74/:127 复核在码；硬编码 hex 8 处逐行实读（account_security:93-120、poster_studio:304-377）。
- 测试实查：家族既有测试 ~20 文件逐一定位（login 3/register 3/unified_settings 4/notification 2+组件 golden 2/splash 1/export 1/profile 1 等）；四风格 golden 家族零命中 find 实证；u15_longtail_closure_guard_test.dart 全文（kRepeatRatchetMax=49/基线集 48 路径）；g06 三层钉三文件头注全文；b04_harness/golden_family_drift_guard 实读。
- 台账/运行态：v3/06_agent_fleet/DYNAMIC_ISSUES.md FIX-581 行+notes 至 35:40；v3/.sparkle_v3_fleet_state.json notes 462 条尾 4 条（35:40：G04 REVIEW_READY/G04R1 已派/六槽 U06 预留）；`git log` 09cbe541（F581 闭账）/e694242d（CI54 双红修）/07c6f31a（map_state_chip 钉）实读。
- 前卡移交：V4-U14 limitations.md 全文（L3/L4/L6/L7/L8 为 G07 直接输入）；U14 run_manifest+198d8a09 commit stat（ObjectUnavailableSurface 交付面）；V4-U06-prep / V4-Q05-prep / V4-Q07-prep / V4-Q08-prep scout 交叉引用。
