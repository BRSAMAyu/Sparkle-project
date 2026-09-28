# WT802 J-02 补测批 终报（REPORT）——FIX-539/540/543 双修后全量复测

- 执行会话：wt802 ｜ run_id：`j02retest_macos_20260928_101701_wt802` ｜ 通道：**macOS desktop 集成测试**（runbook §1.1 主通道，J-01/wt792 同款；800x600 逻辑桌面窗 @2x）
- 工作仓库：`/Users/brsama/code/GitHub/Sparkle-project`（主仓直写，无 worktree）｜ 任务书基线 HEAD=`639aaa95`（含「FIX-540 闭账」）｜ 终报时 main HEAD=`4260f645`（轮#310 fleet state，与代码零重叠）
- 改动（未提交、不 push，收编归主会话）：
  - `mobile/integration_test/j02_fastpath_journey_test.dart`（唯一代码文件，harness 侧：FIX-543 shot 锚定 + 纯 UI 注册改造 + 落点分歧恢复 + stale-finder 守卫 + Leg U 加固）
  - `v3-output/WT802-J02-RETEST/`（本证据目录，untracked）
  - 附注：工作树中 `mobile/lib/l10n/app_localizations*.dart` 出现 -30 行 churn（flutter 工具链再生成所致，非本卡手改）——主会话已声明收编时还原
- 结论速览：**四件全部完成——A1a 秒表 6/6 入预算（原 2/6）、FirstActionCard 6/6 浮现（V3-FIX-540 修法端到端实证）、纯 UI 注册 6/6 无 bounce（V3-FIX-539 修法端到端实证）、截图重采集完成（V3-FIX-543 修复实证）**。J-02 从 wt792 降级口径闭环到全量；残留 = R9 UI 确认面文案（WT792 已知缺口，后端 COMMITTED 6/6 实证）与 541 落点分歧（本次获扩展实证）。

## 0. 执行矩阵（8 进程 = 官方 6 + 2 次披露式 harness 迭代）

| 进程 | dart-defines | 定位 | 结果 |
|---|---|---|---|
| px1（11:27） | PASS=0 LEGS=R | **迭代跑①**：shot v1（纯几何锚定）实测 | R0-R9 全链；t_ready=51,347ms ✓；**暴露 05/06 截图为纯背景**（v1 盲区，驱动 543 修法输入） |
| px1_rerun（11:33） | PASS=0 LEGS=R | **迭代跑②**：shot v2 后首次跑 | 中止于 R3：submit 双击重试对已消失按钮 tap→finder 抛错（harness 竞态，加 stale-finder 守卫） |
| px1_rerun2（11:39） | PASS=0 LEGS=R | **迭代跑③** | 注册**成功**但落「我的」tab→被误判 bounce（加落点分歧恢复路径；本跑 04b 截图留证） |
| **px1_rerun3（11:43）** | PASS=0 LEGS=R | **官方跑 1/6** | **t_ready=102,170ms ✓** 首卡✓ 纯UI✓ |
| **px2（11:48）** | PASS=1 LEGS=R | **官方跑 2/6** | **t_ready=98,767ms ✓** |
| **px3（11:51）** | PASS=2 LEGS=R | **官方跑 3/6** | **t_ready=100,735ms ✓** |
| **px4（11:55）** | PASS=3 LEGS=R | **官方跑 4/6** | **t_ready=101,730ms ✓** |
| **px5（11:59）** | PASS=4 LEGS=R | **官方跑 5/6** | **t_ready=99,754ms ✓** |
| **px5_full（12:03）** | PASS=4 LEGS=R,G,U | **官方跑 6/6 + G/U 抽验** | **t_ready=99,948ms ✓**；G/U 采证见 §3 |

- 每 pass 独立进程真·冷启（runbook §2.1 macOS 语义）；timed 跑与 wt801 互避协议全程遵守：E-08 bench（至 11:05）+ Q06 bench（至 11:26）收官后才开跑，每跑前 pgrep gate 复查。
- 工件：`evidence/<run_id>/`——logs/run_macos_*.log ×9（J02_MARK 可对账）、j02_timings.json（9 进程汇总）、verdict.json、steps.json、proposals.json、screenshots/<PASS>/（01-16 全名族）、db_probes 见 §4。

## 1. vs WT792 原测逐项 delta 表（核心交付）

| 维度 | WT792 原测（降级口径） | **WT802 复测** | Δ |
|---|---|---|---|
| **A1a 秒表**（t_action_ready−t_pass_start≤180s） | **2/6**（PX3 121,754 / PX5 114,583；其余 4 跑 R8 被 FIX-540 阻断未测得） | **6/6**：102,170 / 98,767 / 100,735 / 101,730 / 99,754 / 99,948（另有 px1 迭代跑 51,347ms 佐证带宽下限） | **+4 跑入预算，全量达成**（VERDICT：verdict.json） |
| **FirstActionCard 浮现**（540 修法面） | 2/6（4 miss：goal 落库但卡片缺失） | **6/6**（r7_first_action_entry PASS ×6） | **间歇缺失消灭——autoDispose 修法端到端实证** |
| **注册路径**（539 修法面） | 5/5 UI tap bounce→全部 API fallback（不计入 ≤3min 主张） | **6/6 纯 UI 无 bounce**（fallback 已弃用删除；tiles pre-submit=[true,true] ×6；r3 PASS ×6） | **滚动到因+ensureVisible 端到端实证，fallback 清零** |
| t_register_done | 44.0-78.5s（含 fallback 绕行） | 8.9s（px1 直落跑）/ 56.7-58.4s（含落点 walk） | 纯 UI 化 |
| **F3 proposal 差异化** | 2/5 捕获且互异 | **5/5 捕获且两两互异**（proposals.json） | +3 persona |
| F5 生成期 loading 反馈 | 2/2 有效采样 PASS | **6/6 PASS** | 全采样 |
| R9 UI 确认面文案 | 0/2 捕获（60s 窗） | 0/6 捕获（60s 窗；**后端 approve 200 + status=COMMITTED + DB tasks=1 ×6**，log 直证） | **不变**——确认后 UI 回驾驶舱无「已创建」面（WT792 同款已知缺口，如实留证不阻塞） |
| **R9 useful action 端点**（DB 探针） | 2/2 tasks=1 | **6/6 tasks=1 ∧ goals=1**（j02px17077766/27327992/37541451/47753734/57970385/58191211） | 全量 |
| **截图证据**（543 修复面） | shot()=栈底路由——**register 时点截图全是登录屏**（证据失真） | **v2 锚定（全视口+子树含可见文本）**：02-register=真实注册屏 ✓、05-persona=完整画像引导 ✓、07-modeling ✓（目检实证；v1 纯几何版被 persona 屏背景层绕过——px1 首跑实测后改进） | **重采集完成，失真消除** |
| 注册后落点 | /home 软墙 5/5（直接） | **「我的」tab ×6/7 直接落点**（px1 首跑直落 /home）；驱动以真人路径走驾驶舱 tab 恢复→软墙 resume 卡 6/6 达成（`soft_wall_resume_card=True` ×6） | **541 家族扩展实证**：register/auto-login/guest/upgrade 全落 profile tab（原行只记 guest/auto-login）——驱动恢复+分歧如实记录，软墙语义不受阻 |
| A2b guest | 落点分歧+恢复采证 | 同型：g1 dashboard 60s 超时（落 profile tab）→真人路径恢复→g2 种子扫描 PASS（example marker 缺席=测量数据）→g3 发送✓回复未检出（同 WT792） | 一致 |
| A2c upgrade | UI 受 O3 阻断，API 级 instrumented 证明 | **后端翻转活栈实证**：j02up8579134 注册源→email（provider 读出）✓；UI dashboard=false（落点=541 家族，同上）；u3 persona 未达（受同一落点影响） | 后端语义复证 + UI 落点归因到 541（不再盲） |
| **A1b 种子隔离**（活栈） | 双 0 行（未聊天 guest）/ 自身 uid（聊天 guest） | guest_03a6e396305e：memory_goals=**0** ✓ source=guest ✓；episodic=3 行**全部归属其自身 uid**（04:07 与 g3 聊天窗吻合） | 一致复证 |
| F2 首屏 CTA 无滚动 | 4/4 PASS | 7/7 PASS（含 auto-login 泄漏恢复跑） | 一致 |
| wipe 泄漏 auto-login | 3/5 复现（如实记录+ensureAtLogin 恢复） | 6/7 复现（同款披露恢复，旅程继续） | 一致（存量，非本次回归面） |

## 2. 四件工作逐项结论

1. **修驱动 shot() 锚定（FIX-543）——完成，实证**。修法：DFS 全树遍历中取「全视口(≥90%) 且子树含可见文本(RenderParagraph/RenderEditable)」的**最后一个** RepaintBoundary=栈顶路由边界；无符合者回退首个（日志披露）。v1 纯几何版被 persona 屏「背景层独占全视口边界+子树无文本」绕过（px1 首跑 05/06 同 md5 纯背景图实测发现）→v2 加文本子句后 02/05/07 全部目检正确。已知保真边界（代码注释披露）：小于视口的 dialog/sheet 不以全屏捕获（J-02 规范截图 01-16 全为全屏面，可接受）。
2. **纯 UI 注册复测（539 端到端）——通过**。O3 fallback 从驱动删除；6/6 官方跑提交一次通过、零 bounce；tiles 双勾 6/6（ensureVisible 加固生效，无漏勾）；consentInlineError 归因探针就位（本次未触发——即拦截路径未出现，符合 539 修法预期）。修复边界未见：无「内联错误可见但仍 bounce」样本。
3. **A1a 全量秒表（540 修法）——6/6 达成**。VERDICT：verdict.json（leg_r_runs=8 含迭代跑，官方 6 跑全 in_budget）。首卡浮现 6/6。
4. **证据重采集——完成**。screenshots（18 名族 ×5 persona 目录）+ j02_timings/steps/proposals JSON（logs 权威汇总）+ verdict.json + 本 delta 表；DB 探针只读 psql 直证 R9 端点与种子隔离。

## 3. 新观察（不立新缺陷号，供台账裁量）

- **541 落点分歧扩展**：register 直落（×6）与 upgrade 后落点（×1）均=「我的」tab，与 guest/auto-login 同族——建议 541 行（或并入 536 裁决）把覆盖面从「guest/auto-login」扩为「全部认证后落点」。5 号 grep 复核未占用新号，本次不占。
- R9 确认面：确认 tap 后 UI 回驾驶舱，60s 内无「第一步已在任务账本里/已创建」文案——WT792 已知缺口原样；后端 COMMITTED+task 落库 6/6（approve 响应 receipt 在各跑 log 内）。
- 网关 WS `/community/ws/connect` 429（重连 6 次后放弃）各跑复现——社区 WS 与旅程测量无关，留档不阻塞（疑速率限制对测试通道的既有行为）。
- g3 demo 回复 90s 未检出（同 WT792：可能为检测形制与实际回复名不匹配）；episodic 3 行全自 uid 复证命名空间隔离。

## 4. 诚实披露

- px1/px1_rerun/px1_rerun2 三次迭代跑如实保留于 logs（不删跑）：①暴露 shot v1 盲区 ②暴露 stale-finder 双击竞态 ③暴露落点误判——三次 harness 修复均为披露式（代码注释注明 wt802），且不弱化任何断言（竞态守卫只在按钮已消失时转为等待落点）。
- 官方 6 跑中 5 跑经历 auto-login 泄漏+logout 恢复（存量 wipe 泄漏，WT792 已披露）；t_pass_start 以各 pass 真墙钟起点计，泄漏恢复成本计入测量（无掩饰）。
- 注册 POST 本轮实测偏慢（~15-18s，t_register_done 56-58s）——真实服务时延，未做任何重试美化。
- 落点 walk（驾驶舱 tab）计入 A1a 秒表窗口内（真实用户路径），无排除。
- l10n churn（-30 行 ×3 文件）非本卡意图改动，收编时还原（主会话已认领）。
