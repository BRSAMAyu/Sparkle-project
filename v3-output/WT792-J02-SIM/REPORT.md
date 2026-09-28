# WT792 J-02 Simulator 实测证据报告（REPORT）

- 执行会话：wt792 ｜ run_id：`j02sim_macos_20260928_082714_36a0` ｜ 通道：**macOS desktop 集成测试通道**（runbook §1.1 主通道，J-01 wt398 已证先例）
- base/final SHA：base=main@`7de5e46e`（含 V3-FIX-498 闭账）｜ final=本分支 HEAD（见 git log；工作树改动仅 harness 驱动两处披露式修复 + 本证据目录）
- 验收权威：`v3/07_tasks/tasks.json` id=J-02 + `v3/01_product/FIRST_3_MINUTES.md` 七项清单
- 定位：E3（integration/simulator evidence）——wt772 receipt §6-1 判 PARTIAL 的唯一销账缺口
- 结论速览：**本卡以实测补齐 E3 的可采证面，整体 READY_FOR_REVIEW（非全绿）**；1 项验收入预算实测通过（A1a 口径降级）、1 项活栈双 0 行通过（A1b）、A2 三端中注册端实机通过/游客端稳定性通过落点分歧/升级端 UI 受阻改 API 级证明；工程链未通过面全部如实留证并定位到 3 个新缺陷（V3-FIX-538/539/540，只登记于 notes.md）。

## 0. 执行矩阵与覆盖度（如实）

| 进程 | dart-defines | 结果 |
|---|---|---|
| px1 | PASS=0 LEGS=R,G,U | R0-R7 达（R8 受阻），G 落点分歧（探针✓），U 降级受阻 |
| px2 | PASS=1 LEGS=R | R0-R7 达（R8 受阻） |
| px3 首跑 | PASS=2 LEGS=R | 中止于 R0（auto-login+logout tap 无效；harness 修复前，留证） |
| px3 重跑 | PASS=2 LEGS=R | **R0-R9 全链打通，t_action_ready=121,754ms ≤ 180s**；R9 UI 确认面未捕获（后端 COMMITTED + DB tasks=1） |
| px4 | PASS=3 LEGS=R | R0-R7 达（R8 受阻） |
| px5 | PASS=4 LEGS=R | **R0-R9 全链打通，t_action_ready=114,583ms ≤ 180s**；R9 UI 确认面未捕获（后端 COMMITTED + DB tasks=1） |
| gu ×3 | PASS=0 LEGS=G,U | 3/3 启动期环境失败（`Failed to foreground app; open returned 1`， MaterialApp 不在树）——GU 专用启动路径在本机当前状态确定性失败 |
| px5_full | PASS=4 LEGS=R,G,U | R 腿再遇 539（r7 miss，累计 4/6）；**G 腿完整采证：g1 分歧如实记 FAIL→真人路径恢复→g2 种子扫描 + g3 真实 lane 对话轮（发送✓/回复未检出如实）**；U 腿 O3 受阻 ×2 一致（u1 表单达、u2/u3 未达） |

- 覆盖度 = runbook 允许降级矩阵之上：Leg R ×5 persona（每 persona 独立进程，真·cold start 语义 + 3/5 wipe 泄漏如实记录）+ Leg G 探针/稳定性面 + Leg U API 级 + 全腿进程补充尝试。
- 全产物：`evidence/<run_id>/`（run_manifest.json / j02_timings.json / verdict.json / steps 汇总 / db_probes.jsonl / proposals.json / screenshots/<PASS>/ / logs/run_macos_*.log，J02_MARK 可对账）。

## 1. 验收项逐条映射（A=acceptance，F=FIRST_3_MINUTES 七项，E=required_evidence）

### A1a fresh user ≤3min 到 useful action —— **◐ 口径降级后 PASS（2/5 实测入预算）+ 两项阻塞缺陷**

- 实测（t_pass_start=进程冷启起点，真墙钟 fullyLive；判据=runbook §3-R8 `t_action_ready − t_pass_start ≤ 180,000ms`）：
  - **PX3：121,754ms ✓** ｜ **PX5：114,583ms ✓**（verdict.json）
  - PX1/PX2/PX4/px5_full：R8 未达（V3-FIX-539 FirstActionCard 间歇性缺失，R 腿 6 跑 4 miss）→ 无法计测，如实记 FAIL-not-measured
- useful action 终点（R9 确认）：两 pass 后端 approve API 均 ok、proposal status=COMMITTED、**DB tasks 表各落 1 行**（j02px36697702 / j02px57325767，db_probes.jsonl）；UI 确认面文案 60s 内未出现（r9 断言 FAIL，已留证）——「useful action 已产生」以 DB+后端双证据成立，UI 面文案未捕获如实记录。
- 口径披露（runbook §6-2）：5/5 pass 的 UI 注册 tap 均弹回（V3-FIX-538，O3 家族复现 ×5），全部走了 fallback（真实 register API 200 + UI 登录）。**fallback 段不计入 ≤3min 主张**——即上述入预算数字含 fallback 绕行成本仍 ≤180s（保守口径：真实纯 UI 路径只会更快，但纯 UI 注册在本通道当前不可走通，主张本身按降级口径成立）。t_registered 有 fallback 的 pass：47.3s/44.0s/78.5s(auto-login 绕行)/77.8s/77.8s。
- 旅程分段实测（PX3 重跑为例）：首屏 2.1s → persona 步1 91.7s（含注册绕行）→ goal CTA 99.5s → fastpath 提交 104.1s → skip 落 /chat 109.3s → 生成中 119.4s → **proposal 就绪 121.8s**。纯注册后旅程（步1→proposal）≈30s。

### A1b seed 不进入真实 Memory —— **✅ 活栈级通过（双 0 行 + demo 短路面为既有后端 pin）**

- G4 探针（db_probes.jsonl，只读 psql 活栈）：guest `guest_09788ed34e71`（uid 93f2f78d，08:31:53 本机时创建）→ `memory_goals`=**0** ∧ `episodic_memories`=**0** ∧ `users.registration_source`=`guest` ✓
- G3 demo 对话轮未采证（G 腿 UI 面受阻，见 A2b/F 覆盖度）——demo 轮不进记忆的机制面由 wt764 后端 pin 4/4（`test_j02_seed_memory_namespace.py`，V3-FIX-258 短路）+ 本卡活栈双 0 行共同承担。

### A2a 注册端 session 稳定 —— **✅ 实机通过（5/5）**

- 5/5 pass 注册后落 **/home 软墙**：Dashboard + OnboardingResumeCard（「完成引导，让 AI 更懂你」+ CTA「继续引导」，`soft_wall_resume_card=True` ×5）——wt282 软墙语义实机复现；截图 `04-home-softwall.png` ×5。

### A2b 游客端 session 稳定 —— **◐ 稳定性通过；落点分歧如实（V3-FIX-540）；G2/G3 已补采（全腿进程）**

- guest session 建立且 60s+ 停留无 persona 引导循环（`9x-g1_guest_home-timeout.png` + TEXTDUMP n=84 全量 UI 文本）；种子身份/等级/画像面渲染正常。
- **落点分歧**：实际落「我的」tab（profile 面），非 J-01 先例的 dashboard——驱动 DashboardScreen 断言超时（g1 FAIL 留证）；router 代码语义（guest→/home）与实测不符，根因未归因。auto-login 场景同型落点 ×3，佐证为系统行为。
- **G2 种子扫描（全腿进程补采）**：经驾驶舱 tab 真人路径恢复到 dashboard 后完成（`12-guest-seed-scan.png`；恢复路径披露于 notes/manifest，g1 分歧仍记 FAIL 不抹除）。
- **G3 demo 对话轮（全腿进程补采）**：真实 lane 发送成功（loginAsGuest 为 isDemoMode=false 真后端 token；`13-guest-demo-chat.png`）——**回复未检出**（90s 内无 Aurora 名增量/「输入中」，TEXTDUMP `[g3-no-reply]` 留证；种子对话历史「上次聊到这里」等正常渲染）。回复未达是否有产品问题无法在本卡归因（可能为检测形制与实际回复名不匹配），如实记录。
- **G4 探针（最强形态，含聊天后的 guest）**：新 guest `guest_d2f70de3b47c` 聊天后 `memory_goals`=**0** 恒成立；`episodic_memories`=2 行——**经核验均归属该 guest 自己的 uid**（chat_turn「操作系统-死锁」源自其自身种子会话史 + analysis「Goal Ambiguity」），由**真实聊天 lane**写入自身 namespace，非种子泄漏、非跨 namespace（V3-FIX-258 短路只作用于 demo lane，与本次实测一致）；未聊天 guest `guest_09788ed34e71` 严格 0/0（对齐 wt764 pin 语义）。

### A2c 升级端 session 稳定 —— **◐ UI 受阻（O3+门控）；API 级原位翻转证明（instrumented 披露）**

- UI 面：GuestConversionCard CTA 在访客 dashboard 不可见（价值信号门控，N40 四守门——如实记 `card-visibility claim=false`，属测量数据非失败）；降级路径走 login 注册链，被 V3-FIX-538 阻断（u2 未达）。U3 未达。
- **API 级 instrumented 证据**（upgrade_probe_*.json + db_probes.jsonl）：新 guest `guest_01710f43`（uid `866e3203`）→ guest token 直调 `POST /api/v1/auth/upgrade-guest` → **同一 uid** `registration_source: guest→email`、username 翻转，无登出/换会话（转正事务语义，V3-FIX-205 家族）——后端语义活栈证明；UI 面证据待 V3-FIX-538 修复后补走。

### F1 fresh install / cleared state —— **◐ 语义已声明；wipe 泄漏 3/5 如实**

- 语义 = 每 persona 独立驱动进程 + 进程起点 `wipeLocalState()`（secure storage+prefs，runbook §2.1 macOS 行），manifest 记录。
- **实测泄漏**：前序进程以登录态结束时（PX2/PX3/PX4/PX5 结尾），下一进程 wipe 后 auto-login 复活 3/3 次（PX1→PX2 无泄漏：前序以登出态结束）。产品与驱动两侧 `useDataProtectionKeyChain:false` 一致，根因未归因（notes.md harness 注记）。泄漏后果 = auto-login 绕行（披露式 logout 后旅程继续），旅程测量诚实性不受影响。

### F2 首屏 primary CTA 无滚动可见 —— **✅ 4/4 有效采样 PASS**

- `login_cta_no_scroll_visible=True` + welcomeSubtitle 在场（PX1/PX2/PX3重跑/PX4/PX5；px3 首跑 False 系 logout 未达时的错误表面，已被重跑取代留证）。截图 `01-first-surface.png` ×5。
- 首屏时延（冷启→首屏）：7.4s/4.4s/2.1s/1.8s/1.6s（J-01 先例 9.5-23s 内，且逐次递减为 OS 文件缓存效应，如实记录）。

### F3 5 persona 非模板化 action —— **◐ 2/5 捕获且互异；3/5 未捕获（V3-FIX-539，R 腿 6 跑 4 miss；含 px5_full 重跑）**

- 已捕获 proposal（proposals.json）：PX3（React 作品集→「初始化项目并渲染Hello World / 终端运行 npx create-react-app…」）vs PX5（播客→「确定首期播客选题并撰写300字大纲…」）——**两两非同文 ✓**，且与各自 persona 目标强绑定。
- PX1/PX2/PX4 的 proposal 未生成（R8 未达，px5_full 亦 miss）；5/5 全量观感对比留待缺陷修复后补测。J-04 后端差异化断言（既有）不受影响。

### F4 3 分钟脚本内到 Action —— **◐ 同 A1a：2/5 入预算 ✓（121.7s / 114.6s），3/5 未测得**

### F5 loading >500ms 有反馈 —— **✅ 2/2 有效采样 PASS**

- PX3/PX5 的 FirstActionCard 生成期 Circular 进度指示器实机观测到（`loading_feedback_observed=True`，150ms ×6 探测窗）；其余 pass 未到该面。 注册/聊天等长操作均有 loading 面（全程截图族无骨架悬置反例）。

### F6 错误不回空白页 —— **◐ 全程无空白错误页；但 O3 即「零反馈」反例（如实两记）**

- 正例：引擎「服务器正在打盹」503 节流（px2 log）时 UI 保留完整内容面；各 timeout TEXTDUMP 均见全量 UI 文本（无空白）；R8 失败重试面（wt371）本卡未触发（无生成失败样本）。
- 反例如实：**V3-FIX-538 注册 tap 弹回 = 字面意义的「零反馈」（无错误文案无跳转）**——这正是 F6 要防的产品缺陷，实机复现 5/5（R 腿 6 跑全 bounce），已作为缺陷登记而非掩饰。

### F7 截图由视觉 Reviewer 按 rubric 打分 —— **⏳ 待独立审查（非本会话职责）**

- 产物已齐备：18 步命名模板截图 ×5 persona + G/U/timeout 族（`screenshots/<PASS>/NN-*.png`，可按 rubric 打分）。

### E1/E2/E4 —— 不属本卡（wt764 `787bc973` / wt772 receipt `7bbaf092` 既有），本卡仅补 E3。

## 2. 与 FIRST_3_MINUTES「快车道」语义的对照（W1/W2/W3 实机面）

- **W1 两入口+最小 goal capture**：goal 输入后 `j02-fast-path-cta` 出现、空目标时**不**出现（`fast_path_cta_absent_when_goal_empty=True` ×5，wt764 负门控活栈复现）+ hint「只回答目标这一个问题」在场 ×5 ✓
- **W2 只问改变 first action 的问题**：goal-only 提交后直达 modeling、persona 步 2-5 未问（r6；「树残留」注记见 notes）+ skip 即终（`onboardingCompleted` 翻转由 resume 卡消失实证）✓
- **W3 guest/real namespace 隔离**：A1b 双 0 行活栈 ✓

## 3. 新缺陷（执行中发现，只登记 notes.md，编辑权归集成会话）

| # | 摘要 | 证据 |
|---|---|---|
| V3-FIX-538 | macOS desktop 注册提交 tap 系统性无效零反馈（O3 家族复现 5/5；J-01 7-run 先例至今无 FIX 号） | 各 pass log `J02_FINDING` + after-register-submit TEXTDUMP |
| V3-FIX-539 | J-02 快车道 skip 后 FirstActionCard 间歇性缺失（3/5 miss；goal 已落库、resume 卡正确消失；R8 秒表核被阻） | px1/2/4 log + `9x-r7-no-action-card.png` vs px3/5 成功对照 |
| V3-FIX-540 | guest/auto-login 落点为「我的」tab 非 dashboard（session 稳定；router 语义 /home 与实测不符） | `9x-g1_guest_home-timeout.png` + px3/4/5 auto-login 落点 |

另有环境/ harness 注记（GU 专用启动 `open returned 1` ×3、wipe 泄漏、`open` 前台失败致 MaterialApp 不在树）——均记录于 notes.md，非产品缺陷。

## 4. 给销账/审查的建议口径

- **E3 已从「无实测」变为「有实测 + 缺口清单」**：J-02 的销账判断建议为 PARTIAL→按 A1a 降级口径 + A1b/A2a 全过 + V3-FIX-538/539 阻断面综合裁定；539 直接卡在「快车道最后一公里」，若集成会话认可「action COMMIT 以 DB+后端证据成立」，则 A1a 可按 2/5 persona 入预算 + 5/5 软墙 + 透明 fallback 的口径收。
- F7 rubric 打分与 V3-FIX-538/539 修复后复测（尤其纯 UI 注册路径的 ≤3min）是残留工作。
- 本卡不自勾验收框：状态 **READY_FOR_REVIEW**（独立未参与会话审查）。
