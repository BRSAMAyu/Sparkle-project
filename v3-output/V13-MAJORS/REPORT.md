# V13-MAJORS — B-02 停摆 + 三 Major 修复报告（北极星实测收尾件）

- **执行人**：C 纵队修复 Worker（生产级线）
- **Worktree**：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt207`（基线 `7e17a068`）
- **缺陷依据**：主仓 `v3-output/V13/REPORT.md` 的 B-02 + M-01/M-02/M-03
- **交付物**：本报告 + 同目录 `changes.patch`（未 commit / 未 push，零凭据）

---

## 一、四项修法（各一段）

### 1. B-02 建模访谈多消息回合停摆（mobile 面）

**根因（mobile）**：此前 A-3 只立了「首事件 45s 看门狗」——第一条消息到达后看门狗即撤销；V13 实测的停摆发生在**多消息回合的中段**（Aurora 发出「我先把瓶颈整理出来…」后，下一条消息生成期间 50s+ 无任何帧），此窗口内：无 typing 指示、无超时反馈、无重试，用户唯一出路是「跳过」。
**修法**：① 复用 SPEC-C §5.2 单行阶段胶囊（`ChatRunPhaseIndicator`，S18 已立组件）——run 在跑且无流式草稿时停在「思考中」（中段静默窗口可见），流式输出时切「生成回答」，并常驻**可取消**（取消保留已生成消息、输入框立即可用）；② 新增**中段活动看门狗（75s）**——任何帧（含 meta/status）都会重置，触发即把静默死流升级为**可见错误 + 重试**；③ 错误/超时的「重试」= 重发最近一条用户消息（`_onboarding_start_` 初始 run 无用户消息，只提示不提供重发）。75s 取值依据：V13 实测停摆 50s+，留余量避免对慢 LLM 误报。
**引擎心跳面（查证结论，未动代码）**：协议无需扩展——`ChatResponse.status_update`（`AgentStatus.THINKING`）已存在，orchestrator 已在回合开始发 `_emit_early_ack_progress`；但多消息回合**中段**（建模 StateGraph 内部长 LLM 调用）无帧可发。补中段心跳要动建模图编排——该面属 wt205 冲突域（backend chat），按冲突纪律**不下手**，作为移交注记（见 §四）。

### 2. Major-1 onboarding 29s（engine 慢点 + mobile 静默）

**定位（实测，非猜测）**：对活栈隔离测量——`PUT /profile/preferences`（同一 ProfileWriteService 写路径）仅 0.35s；onboarding 服务端实测：网关 30s 处 503、引擎直连（无 goal、无 LLM first_message 路径）**仍 160s+**（同账号双请求行锁放大）；活引擎日志显示 5 个种子节点的 `create_node` 彼此间隔 ~9-12s，且节点间穿插 LLM 调用日志。**根因**：`GalaxyBootstrapService.seed_from_goal` 的 5 个脚手架种子不带 `sector_weights` → `ExpansionService._resolve_visual_data` 逐节点走 `NodeSectorService.classify_payload → llm.chat_json` **同步 LLM 星域分类（无超时）**，5 × ~5-6s ≈ 25-30s = 29s 的主项。
**修法（砍同步等，最小面）**：给种子模板**逐条 curated `sector_weights`**（考试=智慧主导、技能=科技主导、兴趣=混合、默认=智慧主导）——`sector_weights_provided=True` 且主星域≠VOID 时 `_resolve_visual_data` 走确定性 `build_sector_visuals`，**不调 LLM**。脚手架标题本是模板常量，模板级确定性分类诚实且即时；用户自建节点仍走 LLM 分类器（该路径未动）。`first_message` 的 LLM 调用保留（8s 有界、个性化开场白有真实价值）。预期落点：prefs ~1s + 种子节点 <1s + first_message ≤8s ≈ **最坏 ~10s、常态 3-5s**。
**mobile 连带面**：提交原先只有 try/finally——30s receive timeout 后按钮原地复活、零反馈（V13 步骤 5 实测）。加 catch-UI：`SparkleSnackBar.error` + 「重试」动作（重试=重新提交，服务端写路径为 upsert 幂等），文案诚实说明「设置可能已保存，可重试或跳过」（新 l10n `userOnboardingSubmitFailed`）。

### 3. Major-2 成长趋势假曲线（诚实红线）

**根因**：`statistics_card.dart` 的 `_WeeklyTrendChart` 硬编码 `FlSpot(3,5,2,8,4,7,9)` ——纯装饰假曲线，零行为新用户也显示完整 7 天波动（V13 截图 64）。
**裁决**：该卡**没有任何真实数据源**——后端仅有聚合口径（`/statistics/weekly` 总完成数/分钟数），无 7 日日粒度学习指数序列；自造「学习指数」口径违反「口径单一事实源/禁止自算一套」约束，新建聚合管道超出本卡（过度工程）。故按卡片给出的第一选项落**诚实空态**：头部保留，曲线区替换为「还没有学习记录——完成第一次学习后，你的成长曲线会出现在这里。」（新 l10n `statisticsTrendEmptyHint`）。未来接入真实日粒度序列时在 `_WeeklyTrendBody` 按数据有无分支，注释已钉死「禁止回落伪造数据」。

### 4. Major-3 光子面 UI 不可达

**裁决（入口选面）**：加在**「我的」页 · 个人成长区**（`profile_screen.dart` 设置 tile），1 跳直达 `PhotonRoutes.redeemPro`。理由：① V13 报告自身修复建议即「光子钱包入口进我的」；② 我的页是底部常驻 tab 且个人成长区**无条件渲染**（零数据新用户也在场—— unlike 驾驶舱 metrics_row 空态不渲染，正是 V13 判定「实际不可达」的原因）；③ 沿 MOBILE-GAP-2 自我锚/光子兑先例的次级入口模式；④ 相比给驾驶舱无 AppBar 的自绘头加 ghost 图标，tile 完全复用本页既有设计语言（accent 复用 `DS.profileAccentAchievementEntry` 金色 token、文案复用既有 `photonRedeemProTitle/Subtitle` l10n——**零新增 l10n、零新颜色**），改动面最小。
**说明**：D 线红线（光子只经「学出会员」出口变现）不受影响——入口直达的就是 redeem-pro（学出会员兑换出口）本身，余额=0 的诚实空态（V13 已实测 can_redeem=false 渲染正常）。

---

## 二、实现清单

**后端（1 文件 + 1 新测试）**
- `backend/app/services/galaxy_bootstrap_service.py`：3 组 goal-type 种子 + 默认种子各加 curated `sector_weights`；`seed_from_goal` 透传给 `create_node`（签名本就支持，零接口变更）。
- `backend/tests/test_galaxy_bootstrap_seed_weights.py`（新）：8 用例——种子模板全部带非 VOID 主星域权重；`_resolve_visual_data` 带权重时**不调** LLM 分类器（tripwire monkeypatch）；无权重时分类器仍被调用（防误伤其它建点路径）。

**mobile（4 屏件 + l10n + 4 测试文件）**
- `mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart`：阶段胶囊（复用 `ChatRunPhaseIndicator`）+ 75s 中段活动看门狗（`_activityTimers`，任意帧重置）+ 错误可见化带「重试」（重发 `_lastUserMessage`）+ `_cancelActiveRuns` 胶囊取消。
- `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart`：`_handleContinue` 补 catch → `SparkleSnackBar.error(文案, onRetry: 重新提交, retryLabel: l10n.retry)`。
- `mobile/lib/features/user/presentation/widgets/statistics_card.dart`：删伪造 FlSpot 曲线（fl_chart 依赖一并移除），换诚实空态 `_WeeklyTrendBody`。
- `mobile/lib/features/user/presentation/screens/profile_screen.dart`：个人成长区新增「光子兑换」tile → `PhotonRoutes.redeemPro`（icon `Icons.diamond_outlined`，accent/文案全复用既有 token/l10n）。
- `mobile/lib/l10n/app_zh.arb` / `app_en.arb`：+2 键（`userOnboardingSubmitFailed`、`statisticsTrendEmptyHint`），dart 文件 `flutter gen-l10n` 再生（diff 纯增量）。
- 测试：`mobile/test/widget/modeling_chat_screen_test.dart` +2 用例（胶囊在场/可取消；75s 静默→可见错误→重试重发）；新文件 `mobile/test/features/user/statistics_card_honest_empty_test.dart`（无折线图断言）、`profile_photon_entry_test.dart`（空态新用户可见 tile、点击 1 跳到 /photon/redeem-pro）、`persona_onboarding_submit_feedback_test.dart`（提交抛错→反馈条→重试再提交）。

**验证（定向，对比法零新增回归）**
- 后端：`pytest tests/test_galaxy_bootstrap_seed_weights.py` 8/8 绿；邻域回归 `test_phase4_galaxy_services.py`+`test_f16_galaxy_weak_node_injection.py` 35/35 绿。
- mobile：`flutter test` 定向——modeling_chat_screen_test 6/6（含存量 4 例回归）、profile_screen_rarity_accent_test 8/8（存量回归）、statistics_card 2/2、photon_entry 1/1、persona_onboarding feedback 1/1；`flutter analyze` 触达文件零 error/warning（全仓 analyze 仅存 2 处**基线已有**错误：`user_persona_screen_test.dart` 缺 `redeemCode` 实现、third_party_plugins vendored 噪声——均与本卡无关，git show 基线可比对）。
- 红证（基线 `git show 7e17a068` 取证）：种子无 `sector_weights`（LLM 必调）；`FlSpot(3,5,2,8,4,7,9)` 硬编码；persona 提交 try/finally 无 catch；profile_screen 0 处 Photon 引用；modeling screen 0 处胶囊/中段看门狗。
- 活栈取证（M-1 定位）：probe 账号实测网关 503@30s、引擎直连 160s（同账号锁放大）、单偏好写 0.35s、节点间 9-12s 日志间隔。

---

## 三、冲突面声明

本卡触达：**onboarding（backend galaxy bootstrap + mobile persona 屏）、成长趋势卡（我的页）、光子入口（我的页）、建模访谈屏 typing/超时面（mobile）**。
- **wt204（exam/sprint/prism）**：无交集。
- **wt205（backend context/prompts/chat 红旗）**：我**未动** backend chat/orchestration/prompt 任何文件；B-02 的引擎心跳移交其裁决（见下）。唯一 backend 文件是 `galaxy_bootstrap_service.py`（onboarding 引导服务，非 wt205 声明域）。
- **wt206（chat session 断裂）**：同屏关系=**modeling_chat_screen.dart**。wt206 修 session 建链/历史加载；本卡只加胶囊+看门狗+错误重试，不改 `chatStream` 调用参数、不改 `_conversationId` 语义、不动消息持久化路径。hunk 关系：本卡改动集中在 state 字段/`_startModelingStream` 尾部定时器/`_handleStreamEvent` 头部重置/`_handleStreamError`/build 底部输入区；wt206 若同屏，预计集中在 stream 建立参数与 `_applyMetadata`/session 恢复——无重叠行域，`apply --3way` 应可干净合入；若撞 `_handleStreamEvent` 头部两行（看门狗重置），以先合入者为准、后合入方保留两行即可。
- **A 线（SPEC-C 胶囊）**：仅复用 `ChatRunPhaseIndicator`，未改组件本身。

---

## 四、诚实申报

1. **M-1 服务端修复未做活栈端到端计时验证**：单测证明「种子不再触发 LLM 分类器」机制，活栈 29s 复现数据与日志归因链条完整；但修复后的端到端耗时需主会话按合入管线重启引擎探针后复测（本机不重启主会话引擎、不在 16G 内存压力下再起第二引擎实例——swap 空闲已跌破 1.2G HEAVY 门）。
2. **B-02 引擎中段心跳未实施**：机制存在（`AgentStatus` 帧可复用）但补帧点在建模图编排内，属 wt205 冲突域，按纪律未下手。当前客户端看门狗（75s）保证用户不再无限晾着，但 50-75s 窗口内只有胶囊「思考中」、无服务端真实进度。
3. **M-2 是「诚实空态」而非「真数据曲线」**：本卡无真实 7 日序列数据源，按卡片选项一执行；「只有今天一个点」选项因需新定义学习指数口径（违反口径单一约束）被否决。空态是永久态直到有人接真数据——卡片注释已钉住。
4. **M-3 只加了一个入口（我的页）**：驾驶舱自绘头未加 ghost 图标（无 AppBar、自绘头手术面大）；若产品要求驾驶舱也挂，另卡。
5. **重试语义**：onboarding 重试=幂等重提交（upsert），但 `create_goal` 重复提交可能产生重复目标行（首次提交实际已成功但响应超时的场景）；建模「重试」=重发用户消息，若原消息服务端实际已受理，可能收到两条回复。均为低频边缘场景，UI 文案已提示「设置可能已保存」。
6. **测试基建让步**：persona 屏 Stepper 的隐藏步控件在测试树中不可靠命中，走步逻辑采用「逐候选尝试+currentStep 探针」的稳健写法（`Stepper.currentStep` 是公开字段）。

## 五、收工核查

- [x] 无 git commit / push；交付物=本报告 + `changes.patch`（`git add -N` 仅意图登记，未提交）
- [x] 零凭据入库存（probe 账号密码为一次性 `Probe!2026x`，不入任何文件；.env 未复制，仅 shell 内联 source 读主仓）
- [x] `/tmp` 清理：`wt207_reg*.json`、`wt207_onb*.json`、`wt207_pref.json`、`wt207_token.txt` 已删
- [x] worktree 构建产物：`mobile/build`、`.dart_tool` 已删；`backend/app/gen` 为 proto 生成产物（不入库，构建必需）
- [x] 无独立端口进程残留（未起任何服务/模拟器；活栈进程属主会话，未触碰）
- [x] HEAVY=0（全程 pytest/flutter test 单并发 + curl，未起模拟器/浏览器/gradle）
