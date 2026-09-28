# 预裁④ 备忘 — 三端条款双口径判定草案（wt808）

> 性质：Q-08 正式执行前的**裁决口径草案**，非终判。不改 DoD/台账/tasks.json。
> 撰写：wt808 ｜ 2026-09-28 ｜ 分支 `agent/wt808/q08prejudge`
> 任务输入：`v3/07_tasks/tasks.json` 中提及「三端」的全部卡 ＋ `v3/V3_DEFINITION_OF_DONE.md` ＋ 证据目录实测。
> 标注纪律：【事实】/【推断】/【建议】三档；每个交点给出可点开的证据路径。

---

## 1. 「三端」指什么：词源考

【事实】项目权威定义（两处独立互证）：

- [U-09/REPORT.md](../U-09/REPORT.md) §「环境现实声明」段原文：「**U-09 三端=Android/Web/macOS**」（且 §根因段记录了 B-04 命名注册表曾只认 android/web/ios 导致 macos 截图会 NamingError 的修正）。
- fleet state 轮#314（`v3/.sparkle_v3_fleet_state.json`）原文：「项目三端=Android/Web/macOS 不含 iOS」。

【事实】`v3/07_tasks/tasks.json` 提「三端」的 7 张卡（全量 grep 实测）：

| 卡 | acceptance/work 原文（摘） | 现状态 |
|---|---|---|
| Q-02「20 Golden Journeys 三端终验」 | 「核心 GJ01/04/06/08/09/14/18/19 **三端或明确平台适用**」 | done |
| U-09「L5 三端视觉/交互一致性 Diff」 | 「核心状态三端无 A/B visual issue；交互语义一致」 | done |
| M-10 | 「GJ08/GJ09 **三端通过**；用户无需知道"Memory"内部结构」 | done |
| X-07 | 「GJ07 **三端通过**；用户操作两次不会 resume 两次」 | done |
| J-02 | 「注册/游客/升级**三端** session 稳定」 | done |
| J-04 | 「GJ01 **三端**；5 Persona action 不模板化；重开存在」 | done |
| B-04 | 「**三端**采集 baseline screenshots，统一命名与 viewport」 | done |

【事实】DoD 侧对应条款是 **Gate V3-7**：「Android/Web/macOS 核心 golden journey 均通过」。Q-line 主底稿（[WT779-DOC-OQ/Q-line.md](../WT779-DOC-OQ/Q-line.md) §V3-7 行）已给出预判原文：「『Android/Web/macOS 核心 GJ 均通过』条款按现状只能判 **BLOCKED（真机）/PASS（API 级+模拟器）双口径**」。

【推断】任务书假说「双口径疑似=本地 sqlite 零 LLM 口径 vs 真模型/公网口径」**经查不成立（作为预裁④的定义）**——那是一条真实存在的另一条轴（见 §5），但 Q-08 预裁④所指的「双口径」在 Q-line/骨架中措辞一致，是**平台证据口径**：口径A＝API 级＋headless/渲染器/桌面集成通道（无真机硬件），口径B＝真机/实机段（物理设备、真实浏览器、屏幕阅读器）。「公网 vs 本地」是第三条正交轴（O-01），一并纳入矩阵。

---

## 2. 三端 × 双口径矩阵（含公网轴）

### 口径A：API 级 + headless/渲染器/桌面集成通道（平台无关语义面为主）

| 端 | 已有证据（事实） | 缺口 |
|---|---|---|
| **平台无关 API 面**（三端共用 gateway 语义，`summary.json` 逐条登记 `three_end_applicable:[android,web,macos]`） | Q-02 首轮 20 GJ 真栈真 LLM headless 全跑：13 PASS/6 FAIL/1 RESTRICTED（[WT394-Q02-GOLDEN/REPORT.md](../WT394-Q02-GOLDEN/REPORT.md) §3 逐条＋`raw/<GJXX>_local.jsonl`）；FIX-53/54/55/56 修复链＋WT400 局部复验（[WT400-FIX53-REVERIFY/summary.json](../WT400-FIX53-REVERIFY/summary.json)：6 GJ 3 PASS——GJ04 翻 PASS、GJ09 翻 PASS、GJ08 FAIL=轮间波动在档 5/6）；服务层随行锁 `backend/tests/golden/test_q02_golden_service_layer.py`（GJ09/12/14 sqlite 直驱）。X-10 77 场景服务层全绿（[X-10/REPORT.md](../X-10/REPORT.md)：allocation 100%、high-risk auto=0、false success=0） | **修后无全 20 GJ 重跑**（Q-line 残差①明文；属预裁⑤三选一，本备忘不裁） |
| **Android** | U-09 headless 契约测试 C1-C7 全绿（flutter test VM，几何/语义断言；[U-09/REPORT.md](../U-09/REPORT.md)）；Q-03 107 屏真实渲染逐屏程序化探针：核心 13 屏 A/B=0、long-tail 85 屏 A=0（[WT401-Q03-VISUAL/rubric_scores.md](../WT401-Q03-VISUAL/rubric_scores.md)——注意渲染形态见 §4 边界注）；G-05 headless frame budget 测试在库可跑（`mobile/test/features/galaxy/performance/g05_galaxy_frame_budget_test.dart`，H-009-2 行引） | 渲染器为 flutter_tester 单档单尺寸（390×844@2x，Q-line Q-03 残差①明文「三端真机尺寸未渲染」） |
| **Web** | U-09 headless 契约＋**C7 几何近似+静态审计补偿**（kIsWeb 分支 VM 不可翻转，[U-09/REPORT.md](../U-09/REPORT.md) 边界注「已在 C7/夹具登记」）；web-round1 既有证据（U-09 report 引用）；Q-02 API 面同上 | web 渲染证据弱于 Android（VM 无法翻转 web 分支，靠近似补偿——U-09 自我披露） |
| **macOS** | **三端中最强**：J-01/J-02 integration test 在 macOS desktop 真应用通道（真窗口非渲染器）：WT802 官方 6/6 跑——A1a 秒表 99.8-102.2s 全 ≤180s、FirstActionCard 6/6、纯 UI 注册 6/6、v2 锚定截图、DB 探针 6/6（[WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md) §0/§1 delta 表；run_id `j02retest_macos_20260928_101701_wt802`）；WT792 原测 10 进程同通道 | 「macOS 真桌面**文字级权威批**」未做（flutter_tester 批有 ENV-1 字形伪影，文字审查权威=真机批——H-009-4 第 5 项）；U-09 矩阵 macOS 两 viewport 未采集 |

【推断】口径A 整体＝骨架 V3-7 预判的 **PASS 候选**：核心旅程 A/B 视觉（渲染器口径）清零、20 GJ 的 API 语义面「首轮＋逐 FIX 闭账＋局部复验」链式成立、macOS 有真应用集成级证据。弱点两条：GJ08 复验 5/6 轮间波动在档、无全量重跑（并入预裁⑤）；web/Android 渲染证据非真机形态（并入口径B）。

### 口径B：真机/实机段（设备、真实浏览器、屏幕阅读器）

【事实】**三端整段未采集，中央箱零覆盖**——台账 V3-FIX-511（wt775 登记）＋ [HUMAN_INBOX](../../v3/08_operations/HUMAN_INBOX.md) H-009（wt783 回填明细 10 子项，行 25-34）：

| 端 | 未采集项（H-009 子项） | 阻塞原因 |
|---|---|---|
| Android | U-09 45 行矩阵 android 行（1080×2400@3）；G-05 真机截图 5 张＋FPS/latency（50/500 节点 ≥55fps 交互档）；TalkBack 走查 GJ01/GJ03/GJ08；Q-02 B 段真机交互（含 10.0.2.2 宿主别名验证）；X/J 线实机走查族 | 无 AVD/真机权限（wt390/wt676 两轮如实转出，不伪造） |
| Web | 双宽采集（1280×720＋360×720）；NVDA 走查＋WCAG AA 取色＋焦点序全表 | 无浏览器自动化权限（wt365 以 headless 语义树断言替代并如实标注） |
| macOS | U-09 矩阵 macOS 两 viewport（800×600@2、1280×800@2）；VoiceOver 走查；B-04 文字级权威批 | 无 macOS 桌面 app 真机批环境（H-009-4） |

【事实】解除成本已在 H-009 逐行评估（H-009-1 约 0.5-1 天、合计约 2-4 天量级，「成本在采集执行而非代码」）；先例豁免通道也存在——H-009-7 行原文：「**或由 fleet owner 显式裁决豁免并转 HUMAN_INBOX 首飞清单，豁免须记账**」。

### 公网轴（与平台正交，O-01 域）

【事实】GJ19 remote HTTPS 口径如实 RESTRICTED（local 段 6/6 全绿，[WT394-Q02-GOLDEN/REPORT.md](../WT394-Q02-GOLDEN/REPORT.md) §3 GJ19 行）；O-01 公网 Staging 部署 TODO 卡用户凭据（H-002 阿里云 TCC 开关＋ZCode 重启）；Q-02 HUMAN_INBOX D 段远程 2 项未采。

---

## 3. 缺口两分法：O-01 部署后可补 vs 只能如实标注

【推断】Q-08 需要在 BLOCKED 注记里区分两类解锁条件，避免把「等 O-01」和「等设备」混写：

**O-01 部署后即可补（远程端点类，无需新硬件）**：
- GJ19 remote fresh-device 段（复跑命令在卡：`python scripts/devtools/q02_run_golden_journeys.py --env remote --remote-url https://<host>`，WT394 §2 原文）；
- Q-02 HUMAN_INBOX D 段远程 2 项；
- DoD V3-9 的「移动/Web 可配置远端 endpoint」「密钥只在服务端」远程验证段（骨架 V3-9 已判 BLOCKED 挂 H-002）。

**O-01 部署后仍不可补（设备/真人类，只能如实标注或豁免记账）**：
- H-009-1（45 张三端矩阵）、H-009-2（真机 FPS）、H-009-3（TalkBack/VoiceOver/NVDA 辅助技术走查）、H-009-4（文字级权威批）、H-009-8/9（X/J 线实机族）——阻塞原因是**设备与浏览器权限**，与公网部署无关；
- H-009-9 尾项 J-07 真实用户回访行为学——需要真实用户，属长期面，V3 内只能如实标注。

---

## 4. 判定口径草案与边界注记

【建议】采纳骨架既有方向（Q-line 明文、骨架 V3-7 裁决槽引用），并补三条执行细则：

1. **双口径并行标注，不得互相替代**：V3-7 三端条款记为「**PASS 候选（口径A：API 级＋渲染器/桌面集成通道证据，锚=Q-03 核心 13 屏 A/B=0＋Q-02 修复链＋U-09 headless 契约＋J-02 macOS 6/6）/ BLOCKED（口径B：真机段，锚=V3-FIX-511＋H-009 全表）**」。BLOCKED 单列不并入 FAIL 计数（骨架判定规则 3），逐项附 H-009 指针与解锁条件。
2. **「三端通过」字样卡（M-10/X-07/J-02/J-04）的 done 状态按「三端或明确平台适用」口径解释**：tasks.json 唯一给出口径出口的是 Q-02 卡面原文「核心 GJ01/04/06/08/09/14/18/19 **三端或明确平台适用**」——即 API 语义面三端共用＋平台差异按 U-09 允许差异表（`v3/04_ux/MULTIPLATFORM.md` §允许差异登记）登记即算适用。此解释使「done 状态」与「gate 双口径」不矛盾：卡验收=口径A 成立，gate 报告仍须如实标注口径B BLOCKED。【事实】该允许差异表确已登记 API 主机别名/IME 视觉/enter-to-send 三类平台差异并给 reason（MULTIPLATFORM.md 15-27 行）。
3. **可证伪判据（BLOCKED 解除条件与豁免条件二选一)**：
   - **解除**：H-009 批次采集完成——45 行矩阵全采＋`visual_baseline.py manifest/verify/diff` 链跑通（harness 在 `scripts/devtools/visual_baseline/`）＋DIFF_REPORT 无新增 A/B（核心行）→ 口径B 翻 PASS 候选。
   - **豁免**：fleet owner 显式裁决「V3 收口以口径A 为准，真机批转 V4 首飞清单」并记账（先例=H-009-7 行明文豁免通道）→ 口径B 维持 BLOCKED 标注但 FINAL 状态不再被其阻塞。
   - 禁止形态：无豁免记账而把口径B 项标 NOT_RUN 或 PASS——骨架判定规则 4 明文「不得用 NOT_RUN 掩盖 FAIL」，真机段是「未执行的必做项」的边界情形，标注为 BLOCKED（外部依赖未解锁）而非 NOT_RUN（Q-line/骨架既有口径，维持）。

**边界注记（如实带上的两点）**：

【事实】①Q-03 的 107 屏渲染形态=flutter_tester 390×844@2x 单档（`rubric_scores.md` 头部自述＋Q-line 残差①），它支撑「视觉审查完成」但**不是**三端渲染证据——把它计入口径A 的 Android 列是「移动视口渲染」语义，报告引用时须保留这个限定，不可写成「Android 端已渲染验证」。②J-02 的 macOS desktop integration 通道是真应用窗口（非模拟器非渲染器），是三端中唯一的「真应用」级证据；但 H-009-7 仍把「J-02 三端实机走查＋截图视觉核」列为 OPEN（审查方无权豁免，需 fleet owner 裁决）——即 macOS 通道内 J-02 本身已 6/6 全量（WT802），欠的是 Android/Web 端的对应走查。

---

## 5. 附：另一条真实存在的「口径轴」辨析（回答任务假说）

【事实】「本地 sqlite 零 LLM vs 真模型/公网」轴在项目中的真实落点（供 Q-08 报告引用时不错置）：

- 零 LLM 服务层口径：X-10 判定器强制断言 `real_llm_calls=0`（[X-10/REPORT.md](../X-10/REPORT.md) §2「禁止 mock 冒充的落实」节原文）；Q-02 服务层随行锁（sqlite 直驱 GJ09/12/14）；Q-01 260 场景 contract-simulation。
- 真模型口径：WT394 Q-02（真实 LLM，GJ04 修后 chat1_len=431 实文在 `WT400 summary.json`）；WT801 E-08 104 条真模型 bench。
- 公网口径：GJ19 remote（RESTRICTED→O-01）。

【推断】这条轴与预裁④的平台双口径**正交**：同一条 GJ 可以在三种执行介质上各有一份证据。Q-08 报告若引用「X 线 100% 符合」，须按 X-10 自我声明标注 real_llm_calls=0（零 LLM 口径）；若引用「chat 拍通过」，须用真模型口径的 WT394/WT400 数据。两轴不要混写进同一个 PASS。
