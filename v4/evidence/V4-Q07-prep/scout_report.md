# V4-Q07 预备侦察报告（scout, 2026-09-30, main@ee8f18db, 只读+仅本目录写入）

> 用途：Q07「长期接续、离线与多账号组合回归」（PENDING, verification, risk=high, HEAVY, 双审, qa-soak 锁, deps=Q01✗在航/P01✓/P02✓/P03✓/U05✓/U06✗/U09✓/U11✓）派单直接引用。
> 红线声明：本报告为侦察产物非验收证据；未执行 Q07 本体；未改任何既有文件；未动 worktree（`git worktree list` 只读清点）；wtQ01 脏文件清单为 2026-09-30 时点实录，Q07 执行时逐条亲验。
> 时点备注：侦察期间 main 由 edb4333b 推进至 ee8f18db（G06 闭账，G 系 5/7）；fleet notes 读至 [2026-09-30 30:20]。

---

## 一、卡面与协议解读（三维度验收判据 × 组合矩阵定义）

### 1.1 卡面要点（v4/04_tasks/tasks.json V4-Q07 原文）

- **objective/work**：控制钟模拟14日与真实跨进程/多端会话**分开运行**；注入撤回/离线/副作用unknown/小队退出/音频中断五族；保留原V3发布回归。
- **acceptance 三条**：①不同版本和时间机制不混成14日真人验证；②同账号多端与不同账号缓存不混；③可用已完成V3证据，但本次触达链必须新复验。
- **outputs 五件套**：diff_or_evidence_only.md / run_manifest.json / test_results.json / review_receipt.json / limitations.md。
- **evidence_required**：source_sha/build_id/commands_exit_codes/scope_denominator/artifacts_sha256/**actual_model_and_usage_if_llm**/screenshots_ui/**physical_device_scope_if_sensory** 全 true——真实模型腿与设备范围声明是硬字段。
- **stop_conditions**：权限/跨用户/删除复活/假成功→立即隔离不绕门；预算或外部授权缺失→BLOCKED_EXPLICIT；三轮不改善→反例归因，不降阈值。
- **rollback/no_duplicate**：保留V3路径与数据向后兼容；V3 已 DONE 证据不重置，满足处做差量举证。

### 1.2 规范层判据映射（EVALUATION_PROTOCOL + V4_DONE + MASTER_DESIGN）

| 维度 | 判据来源 | 判据内容 |
|------|----------|----------|
| A 长期接续（14日控制钟） | 协议 §原始证据「真实/控制钟」字段 + §五层证据 L0-L5 分层 + V4_DONE「不能替代完成的东西：**7日控制钟**」 | 控制钟模拟与真实会话必须**分开标注、分开运行**（卡面原文），控制钟证据不能冒充 14 日真人验证（协议 §不能自动证明的事：「长期离不开」= NOT_MEASURED_HUMAN）；指标面 = **M02 回归接续**（≤3次；30 个含过期/目标改变用例，UI_LIVE）+ **M26 回退和继承**（触达回归全通过） |
| B 离线 | 协议 §UI/UX闭环矩阵「各主旅程至少默认/离线/失败/取消/未知/过期/重开」 | 离线是六态之一，旅程层用风险组合覆盖不必全笛卡尔；恢复后状态一致 = V4_DONE 问5「断线恢复后仍一致」 |
| C 多账号/多端 | 卡面验收② + 协议 stop「跨用户」红线 + V4_DONE 问9「相同状态跨模块同一含义」 | 同账号多端（effect 去重/状态一致）与不同账号（缓存/记忆/群共享隔离）是**两个不同断言面**；指标面 = M10（硬边界违反=0，≥60 独立负例）+ M17（删除传播，≥30 并发序列） |

**组合矩阵定义**（从卡面可推出的最小正交轴）：`5 注入族（撤回/离线/副作用unknown/小队退出/音频中断） × 2 时间机制（控制钟模拟14日｜真实跨进程/多端会话） × 2 账号拓扑（同账号多端｜多账号隔离）` + 1 条独立基线（原 V3 发布回归新复验）。30 格全跑不现实也不要求——协议允许「旅程层风险组合/成对覆盖减少笛卡尔爆炸」，Q07 应在 run_manifest 的 scope_and_denominator 里**声明选了哪些格、为何**。

### 1.3 关键判例（防误读）

- V4_DONE 把「7日控制钟」列进**不能替代完成的东西**——即控制钟模拟跑得再绿也不产生 VALUE/真人结论；Q07 的产出定位是 ENGINEERING 层韧性行为证据。
- V4_DONE 问5（成功状态真有 receipt，断线恢复后仍一致）与问9（跨模块同语义）是 Q07 的 oracle 源。
- P03 limitations #1 **明文移交**：「对真实栈的混沌级演练属 V4-Q07/原 Q-07 终验，不在本卡代跑」——Q07 有一笔 P03 的正式移交义务（真实栈失联/恢复演练），不只是自选动作。

---

## 二、依赖就绪矩阵（8 依赖 × 状态 × 对 Q07 的输入面）

| 依赖 | 状态（tasks.json） | 对 Q07 的输入面 | Q07 可先行 / 必须等 |
|------|--------------------|------------------|---------------------|
| V4-Q01 | **PENDING 在航**（wtQ01 脏 4 项：`mobile/integration_test/v4_q01_vertical_journey_test.dart`、`scripts/devtools/q01_db_evidence.py`、`scripts/devtools/q01_synth_video.py`、`v4/evidence/V4-Q01/raw/` 已积累 r1 steps/semantics/stack takeover 日志；fleet note 29:00 记「Q01重」重启过会话） | 真实运行栈垂直旅程驱动器 + 只读 DB 探针 + 合成录像脚本——正是 Q07 验收③「本次触达链新复验」要复验的链本体；其验收「同版本3次重复、失败与重试全部保留」= Q07 run_manifest 的失败保留纪律模板 | 先行：无（链定义未冻结）。等：触达链复验腿、3 次重复口径。**但 Q01 的栈起停脚本与探针模式可先抄形** |
| V4-P01 | done APPROVE_WITH_CONDITIONS_CLOSED | 验收③「同一提示多端一次effect，预算与因果来源可追」= 同账号多端 face 的行为基准；FIX-48 打扰冷却为已知债（P01 #3 引用，老 OPEN 不入新裁决） | 先行：多端 effect 去重断言可直接写。无等待 |
| V4-P02 | done PASS_WITH_FINDINGS_OPEN | redteam_playbook.md（注入方法论）+ 跨账号 cache/群AI/后台job 隔离负例。**关键缺口移交**：limitations 明记「本地存储隔离不在本轮（卡面 modules 均有 backend 对应面，gateway 无 AI 推理职责）」+「后台job未逐 job 建负例，代表性抽样」——**「不同账号缓存不混」的移动端本地缓存面 P02 没做**，是 Q07 的应做差量 | 先行：playbook 注入族全可复用；本地缓存隔离新夹具可开工。无等待 |
| V4-P03 | done PASS_WITH_CHALLENGES_X2 | 进程监督器（decoy 真实进程等价证明）+ FIX-530/542 启动路径 + gateway readyz 分离探测 + CWD 无关资源路径；**混沌演练正式移交 Q07**（limitations #1 原文见 §1.3） | 先行：离线/恢复腿的监督器工具链全可复用。等：真实栈演练 HEAVY 窗口（FIX-582 未修前见 §四 R1） |
| V4-U05 | done PASS_WITH_CHALLENGES | 星图轨迹节点「点开来源与投影version一致」= 接续呈现面的版本一致性锚；「无数据不造进度」= 14 日回填数据的呈现诚实性判据 | 先行。无等待（耦合最弱的一个） |
| V4-U06 | **PENDING**（heavy，ui-onboarding 锁；deps F04✓U01✓ 已全闭，唯一等 Q01 模拟器槽——U06-prep 实勘「U06 等 Q01 闭后再占模拟器」） | **最重输入**：U06-prep §二 W2 bootstrap（首卡 approve→一次性 I01→latest 翻转 resume_view→/home 接续条浮现）= 接续卡的生产触发链，Q07 的长期接续腿回归的就是它；guest→真实升级隔离（auth_provider 清除链）= 多账号 face 的移动端锚 | 先行：离线/多账号/后端隔离腿零依赖 U06。等：接续触达链复验（bootstrap 不存在则无生产流量可复验）；账号升级腿 |
| V4-U09 | done APPROVE_WITH_CONDITIONS_CLOSED | 「切后台/重开不重置或重复结算」「中断计时不假保存」= 中断族（音频中断同族）行为基准；夹具 `u09_focus_outcome_flow_test` + `audio_focus_controller_s02_test` + `bgm_service_test` | 先行。无等待 |
| V4-U11 | done APPROVE_CLOSED | **多账号配方**：真实双测试账号 HTTP/WS 场景 + 「本地双引擎进程+共享 sparkle_redis 跨实例扇出」（S19/S20）；移动端钉 `squad_boundary_u11_test.dart`（8 测）；**小队退出端点在库**（`api_endpoints.dart:439 squadStudyRoomExit` / `:462 groupLeave`）= 注入族④的调用面已备；limitations：重连腿用群 WS typing 广播等价、群聊 send 面未入场景（S-05 33 用例兜底） | 先行：双账号/双进程拓扑全可复用。无等待 |

**U06 未闭前的切面结论**：Q07 的 B 离线、C 多账号、V3 回归基线三条腿**零依赖 U06/Q01 可先行**（fixture 级+后端级）；A 长期接续腿的「新复验」必须等 Q01（链定义）+U06（bootstrap 生产触发）。若 10/3 EOD 降级启动，接续腿是唯一合理 NOT_RUN→BLOCKED 候选（见 §五）。

---

## 三、测试策略提案（可复用资产实查 + 缺口 + 资源最省方案）

### 3.1 可复用资产清单（路径全实查，非猜测）

**离线/同步族（最厚）**：
- `mobile/test/core/offline/` 5 件：crdt_sync_manager_p2_10 / offline_crdt_document / offline_queue_indicator_model / sync_engine_crdt_ack / sync_engine_p2_10
- `mobile/test/unit/offline/` 2 件（crdt_sync_manager / task_offline_queue）+ `mobile/test/unit/{offline_sync,sync_engine,sync_cognitive_repository}_test.dart`
- 功能面：`websocket_chat_service_v2_a2_offline_queue_test.dart`（chat 离线队列）、`task_offline_wiring/queued/complete_sync_test`（任务离线三件）、`stale_snapshot_banner_test`、`offline_queue_indicator(_compact)_test`、`widget/sync_center_screen_test`
- 集成：`mobile/integration_test/offline_error_test.dart`（无白屏；注释自认真离线需 env 配置——**E2E_TEST_MODE 全仓只有注释无实现**，实查 grep 零命中 lib）

**接续族**：`episode_resume_models/provider_test`（9 测含角色门反例）、`today_cockpit_resume_{evidence,integration}_test`（7 测）、`onboarding_resume_card_test`、`comeback_banner_test`、`aurora_comeback_context_test`、`stuck_recovery_card_test`；后端 `test_episode_resume_api.py`（:232 latest 翻转）等（U06-prep §三全表）。

**多账号/隔离族**：`squad_boundary_u11_test.dart`（8 测）、后端 `test_community_shared_errors.py`、记忆治理族（memory_correction/governance_panel/settings/auto_memory_panel 等 8+ 件）、auth 身份隔离五件（n4_session_user_state_isolation 等，U06-prep §三）、`learning_journey_api` 跨用户 404。

**中断/音频族**：`u09_focus_outcome_flow_test`、`audio_focus_controller_s02_test`、`notification_interrupt_policy_test`、`bgm_service_test`、`sensory_matrix_q06_test`（58/58 矩阵）。

**撤回/副作用族**：`tool_context_effect_feedback_test`（副作用反馈面）、S-05 WS 33 用例（读回执/乱序/撤回传播，U11 limitations 引）、`unified_notification_push_card_test`。

**V3 发布回归载体**：`mobile/integration_test/` 13 文件（regression_core_flow / app_launch / auth_flow / goal_creation / task_card_flow / plan_generation / checkin_feedback / offline_error / j02_fastpath_journey / macos_journey / first3_measurement / knowledge_preview / app_test）+ `Makefile.test` test-e2e-flutter 目标 + Go integration tags。**这就是「保留原V3发布回归」的既有容器，Q07 差量=新 SHA 下全量复跑+留证。**

**数据构造杠杆**：`backend/app/services/guest_seed_service.py`（uuid5 确定性 seed、sqlite/pg 双方言、timedelta 回填日期）= 合成账号与 14 日历史分布的现成模式；Q04 的 bench guest 账号惯例（wtQ04_bench）；P02 `redteam_playbook.md` 注入方法论；wtQ01 在航的 `q01_db_evidence.py`（只读探针模式，抄形不引用未提交文件）。

**死资产警告**：`tests_e2e/test_offline_sync_e2e.py` **整文件 pytest.mark.skip**（依赖未实现的 backend sync models）——不得计入离线覆盖分母，Q07 run_manifest 应显式排除。

### 3.2 缺口（需新测试/夹具，按优先级）

1. **14日控制钟 harness（最大缺口）**：backend 无 freezegun 依赖（实查 pyproject/requirements 零命中；既有测试注释「免 freezegun」绕行）；`time_utils.utcnow()` ~286 调用点无注入点。可行三案：(a) **数据回填种子**（guest_seed_service timedelta 模式扩 14 天分布+只读断言）——零新依赖、不动产品码，推荐主案；(b) freezegun/time-machine 引入=新依赖需 leader 裁决，建议 NOT_RUN 登记；(c) Flutter 层 fakeAsync/widget 时间推进（接续条过期态等 UI 面）辅案。**注意双钟陷阱**（§四 R7）。
2. **移动本地多账号缓存隔离夹具**（P02 移交差量）：双账号串行登录的本地 cache namespace 断言，扩展 auth_provider 清除链 N-4 夹具（U06-prep §一③同源）。
3. **同账号真双端腿**：U11 双进程+共享 Redis 拓扑扩展出「同账号双端 effect 一次」断言（接 P01 验收③）。
4. **V3 触达回归新复验批**：13 文件全量复跑 + 真模型核心流程（协议要求关键路径 UI 操作，不用 API 造态）+ run_manifest 绑新 SHA。
5. **音频中断真实抢占**：电话/闹钟抢占不可控，沿 V4_DONE「音触只测到调用时注明边界」判例做调用级断言+边界登记，不造假抢占。

### 3.3 模拟器/真机与资源最省（HEAVY 约束下）

- 现状约束：全舰队 DEVICE_UNVERIFIED；Q06 记数据卷余 **6.7Gi**；U06-prep 记 Q01 工作集 2.9G+CoreSimulator 6.4G+swap 95%；模拟器**单槽纪律**（U06 等 Q01）。Q07 开卡时 df 核验，<15G 先清缓存（红线）。
- 最省配比：**LIVE_STACK 双进程腿（无 GUI）为主力**（U11 已证等价路径）+ flutter test 层全矩阵；模拟器只烧**一条最小真腿**——「真实跨进程会话接续」（单模拟器，build 复用 Q01 产物，Q01 闭后窗口）；真机 NOT_RUN 如实登记（evidence_required 的 physical_device_scope 字段显式 false 并引用 Q06 判例「本矩阵套件可原样作为复验工具」）。
- 锁：qa-soak 经 fleet.py；sparkle-coordination-v2 远端本机未配置（U11 run_manifest 同状实录）——冲突面自证口径沿 F05/U11 判例。

---

## 四、风险清单（按杀伤力排序）

| # | 雷面 | 依据 | 影响/缓解 |
|---|------|------|-----------|
| R1 | **FIX-582 运行栈事故三联未修**（共享 PG host 侧鉴权 09-28 起损坏+计费死信 152 吞/58 恢复+MinIO/Redis 凭据三方漂移；台账 :465 OPEN 排队等槽） | V4-Q04 limitations §2 全节实录；Q08-scout §一.B8 | Q07 的 LIVE_STACK 面（真实跨进程腿、真实栈接续、M18 计费完整性复验）全撞墙。缓解：①栈自起隔离端口模式沿 Q04 判例（8081/50052/8001，凭据 cosmos 仓只读注入零回显）；②要求 leader 在 Q07 派单前显式处置 F582（修或对 Q07 相关格预登记 BLOCKED）；M18 的 unattributed 占比面在 F582 修复前必然难看，如实报 |
| R2 | **Q01 在航产出未定**：wtQ01 脏 4 项未提交且会话重启过一次（note 29:00「Q01重」），触达链断言口径未冻结 | wtQ01 实查；fleet notes | 验收③「本次触达链必须新复验」直接消费 Q01 链定义——Q01 返修扩面则 Q07 复验分母跟变。缓解：Q07 开卡冻结 Q01 evidence SHA；不依赖 Q01 的 B/C 腿先跑 |
| R3 | **U06 重轨竞争**：Q01→U06→Q05 与 Q01→Q07 双 heavy 链共享 Q01 与模拟器单槽；U06 未闭则接续卡无生产流量 | U06-prep §四；tasks.json | 接续腿置后等 Q01+U06 双闭；降级场景下接续腿是第一 NOT_RUN 候选（§五 MVP） |
| R4 | **10/3 EOD 决策点**：leader 预决策①=Q05/Q07 未闭则 Q08 显式降级启动（对应层 NOT_RUN→BLOCKED，leader 留痕，Q08 不得自行豁免） | fleet note 30:20 原文 | Q07 需在 10/3 EOD 前给出可交付切面（§五 MVP），让 leader 有真实选项而非被迫全弃 |
| R5 | **HEAVY 单槽+磁盘**：Q07=high+heavy+双审+qa-soak，全 V4 最重卡之一；数据卷 6.7Gi 紧张 | Q06 limitations #10 | 14 日模拟**绝不能真实跑 14 天**——控制钟=数据回填（§3.2 案a），真实腿只跨进程不跨天；开卡清缓存红线 |
| R6 | **双钟混样（验收①最易造假阳性处）**：仓库双钟并存——UTC naive（服务端 utcnow）与用户本地墙上时间 naive（客户端 FocusSession 等）；日界换算 `local_midnight_as_utc_naive`/`local_midnight_wall`（time_utils.py:15-16/:103，V3-FIX-37） | backend/app/core/time_utils.py 实读 | 14 日回填数据若不按「用户本地日界」对齐，M02 的 30 用例与控制钟口径混样=假接续/假过期。Q07 夹具必须显式声明用哪口钟、回填时间戳经 time_utils 换算函数生成 |
| R7 | **审查槽**：双审（risk=high）需预约；Q05/Q07 双 heavy 返修波谷挤兑风险 | fleet notes 29:40 六槽模型 | 返修波谷插审；双审靶预登记（§五） |
| R8 | **死资产误计**：test_offline_sync_e2e.py 全 skip | §3.1 | run_manifest 分母显式排除；计入即虚报离线覆盖 |

---

## 五、工作量与切面估计（全量版 vs MVP 版）

### 5.1 全量版（依赖全闭的理想轨）

| 腿 | 内容 | 会话 | HEAVY 槽 |
|----|------|------|----------|
| 1 V3 触达回归新复验 | 13 集成文件+真模型核心流程+M26 全通过留证 | 1 heavy | 1 |
| 2 14日控制钟模拟 | 回填 harness（0.5）+M02 30 用例（过期/目标改变）+接续条/摘要诚实性 | 1 heavy | 1 |
| 3 离线腿 | 既有 CRDT/queue 套件集成复跑+恢复链+六态旅程离线态 | 1 轻-中 | 0-1 |
| 4 多账号+多端 | 双进程/双账号后端腿+移动本地缓存新夹具+同账号双端 effect | 1-1.5 heavy | 1 |
| 5 收口 | 五族交叉矩阵 scope 声明+五件套证据 | 0.5 | 0 |
| 审查 | 双审 ×2（预约在返修波谷） | 2 轻 | 0 |

合计 ~5-6 实现+2 审查会话，HEAVY 槽 3-4 次。**10/4 前不可行**（Q01/U06 未闭+双 heavy 链竞争），只能走 MVP。

### 5.2 MVP 切面（10/3 EOD 降级启动时的最小可交付）

- **必保（MVP=3 实现+2 审查会话，HEAVY 槽 2 次）**：
  1. V3 触达回归新复验（M26）——复用 Q01 栈与 integration 套件，1 heavy；
  2. 离线腿集成复跑+恢复链（既有套件为主）——1 会话；
  3. 多账号后端隔离负例复验（沿 U11 双进程配方+P02 playbook 差量）——1 会话；
  4. 五件套证据+scope_and_denominator 显式声明「跑了哪些格/NOT_RUN 哪些格/为何」。
- **可 NOT_RUN/BLOCKED 登记（不损 MVP 判据核心）**：14日控制钟全矩阵（harness 未搭则降为 7 日种子样本或整格 NOT_RUN——V4_DONE 明令控制钟不产生真人结论，NOT_RUN 不削弱 ENGINEERING 主张）；同账号真双端模拟器腿（双进程 LIVE_STACK 等价替代，等价声明沿 U11 判例）；音频中断真实抢占（调用级边界登记判例既有）；移动本地缓存新夹具（来不及则登记 P02 移交债）；真实栈混沌演练（FIX-582 未修则 BLOCKED_EXPLICIT 引 R1）。
- **双审靶预登记**：①控制钟腿是否被措辞成真人验证（验收①红线）；②skip 死资产是否混入分母；③NOT_RUN 格是否都有解阻条件；④双钟口径是否在 run_manifest 声明。

---

## 附：本侦察证据基座（全部实查于 main@ee8f18db，时点 2026-09-30）

- 卡库：v4/04_tasks/tasks.json（65 卡=57 done+8 PENDING；Q07 卡全字段 dump；8 依赖逐卡验收/outputs 读取）。
- 规范：v4/06_evaluation/EVALUATION_PROTOCOL.md（30 行全文）、v4/V4_DONE.md（31 行全文）、v4/MASTER_DESIGN.md（59 行全文）、v4/06_evaluation/METRICS.json（M01-M26 全表）、v4/08_release/ROLLOUT_AND_OPERATIONS.md（五旗标+发布工件段）。
- 台账/运行态：v3/06_agent_fleet/DYNAMIC_ISSUES.md:465（FIX-582 OPEN）；v3/.sparkle_v3_fleet_state.json notes 457 条（读至 30:20，Q01 提及 50 处择要）；`git worktree list`（wtF581/wtG04/wtG06/wtQ01 只读清点）；wtQ01 `git status`（脏 4 项）与 evidence/raw 清单。
- 测试实查：`find mobile/test -name "*_test.dart"` = 612 件；offline/sync/crdt 族 find+grep 全列；multi-account/cross-user/隔离/retract/interrupt/squad-exit/控制钟 grep 多轮；`mobile/integration_test/` 13 文件实列；`tests_e2e/` 目录实列+test_offline_sync_e2e.py skip 头实读；`api_endpoints.dart:439/:462` 小队退出端点；backend freezegun 零依赖实查；time_utils.py 双钟实读；guest_seed_service.py 头部实读。
- 依赖证据：V4-P02/{limitations,redteam_playbook.md 存在性}、V4-P03/limitations（混沌移交 #1 原文）、V4-U11/{limitations 全节,run_manifest 双进程配方}、V4-Q04/limitations §2（事故三联全节）、V4-Q06/limitations #10（6.7Gi+模拟器 NOT_RUN）、V4-Q02/（reproduce_counterexample.py 存在性）。
- 兄弟侦察交叉引用：v4/evidence/V4-Q08-prep/scout_report.md（§一.B8/§四 R1/R4 沿用其聚合，Q07 侧换算）、v4/evidence/V4-Q05-prep/scout_report.md、v4/evidence/V4-U06-prep/scout_report.md（W2 bootstrap/模拟器单槽/auth 清除链）。
