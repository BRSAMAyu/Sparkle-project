# V4-Q01｜核心像素×AI 垂直旅程真端验收（diff/evidence only）

执行：wtQ01（分支 `agent/v4/q01` @ `5cbc715f`）· 2026-09-29 · 验证卡（HEAVY），无产品代码变更；`mobile/integration_test/v4_q01_vertical_journey_test.dart` 与 `scripts/devtools/q01_{synth_video,db_evidence}.py` 为本卡 test-only 度量基建。断点续跑：前任因宿主机磁盘/内存连锁故障+强制重启阵亡，worktree 未提交改动（driver 草稿+证据目录）幸存并续用。本日宿主机共两次 ENV-OUTAGE（见 limitations §5），均不计产品失败。

## 1. 版本与栈

| 项 | 值 |
|---|---|
| 被测代码 | `agent/v4/q01` @ `5cbc715f63deaeb7872a9650ce44efaef6d07f4b`（worktree `/Users/brsama/code/GitHub/wtQ01`） |
| 栈（第三轮起，本卡 HEAVY 授权接管） | gRPC :50051 + FastAPI :8000 + Gateway :8080 + celery worker（default/high/low 队列，fixture 摄入所需），全部自 wtQ01 起；provenance：`raw/stack_takeover_r3.md` |
| gateway 二进制 sha256 | `711997d0fd1a809da352186ef6cdd08eacf68cf044b3b9c775ee8fb012e4dde4`（与第二轮一致，同版本连续性） |
| 数据面 | sparkle_db/redis/minio（cosmos 仓属主，FIX-557）全 healthy；alembic head `i06_20260928`（迁移无变化） |
| 设备 | macOS 桌面（`flutter test -d macos`，j02/macos 先例同族；非 iOS 模拟器） |
| LLM | LLMRouter 31 模型配置加载（grpc_server.log）；真模型调用见 §4 |

## 2. 旅程设计（客户端操作驱动，实测演进后的最终形态）

产品真实路径六环节：**接续 → 卡住 → 纠正 → Hybrid → 回执 → 结果**。fresh guest 进入后：

1. 会话隔离：UI 驱动 app 自身「退出登录」（profile→瓦片→确认）；tester 进程内 wipe 清不到 app 侧 keychain（attempt2 实证复用旧会话），UI 登出是唯一可靠且诚实的清场。
2. 锚点前置：注册转化（转化卡「注册并同步进度」有价值信号门，缺席时诚实降级：登录页「还没有账号？」注册链，j02 Leg-U 同径）→ **persona J-02 快车道**（继续引导→目标输入→`j02-fast-path-cta`→建模访谈→跳过）→ `POST /profile/onboarding` 落 **memory_goals(active)**——Hybrid 锚点真源。
3. 知识底料 fixture（唯一披露例外）：prep 检索只认用户文档 chunks，fresh 用户零文档必诚实 no_materials（不编造引用是产品设计）；macOS 原生文件选择框在 flutter_test 宿主外无法客户端驱动，故以 app 自身会话走真实上传管线（prepare→MinIO 预签名 PUT→confirm→celery `process_stored_file` 分块嵌入，实测 48s/9 chunks）。不手插 DB、不伪造分块；旅程步骤本身全部 UI 驱动。
4. 任务与执行面：注册后首页 cockpit noGoal 态露出「和 AI 定目标」→ **J-01 向导**（真实 LLM 意图分析+计划 preview→创建，attempt6 用户 DB 实证计划生成任务）→ 成功弹窗「开始第一个任务」直达执行面（stuck FAB 在场）。
5. 卡住→恢复旅程：卡住 FAB（markTaskStuck）→ StuckHelpSheet → 统一恢复旅程 → 澄清问（服务端真模型派生）→ 校准区纠正「不是不会，今天只有十五分钟」→ 仅本次 → 时长对照 → 服务端 diff → 确认 → committed 回执。
6. Hybrid：入口「和 Sparkle 一起推进」→ 备料（真实工具检索）→ 你研判（用户选来源）→ 起草核对 → 确认交付 → 结果。part2：真重启进程后的接续可见性（目标/任务/纠正后时长）。

## 3. 实测根因链（六道门，全部留证）

| # | 门 | 现象 | 根因（代码锚） | 处置 |
|---|---|---|---|---|
| G1 | Hybrid 500 | `/journey/hybrid` 500 NoActiveGoalError | 种子 demo 世界只建 tasks 不建 `memory_goals`；`first_action_service.collect_first_action_context:169` 只认 `memory_goals.status='active'` | G2 路径解决 |
| G2 | J-01 向导建锚无效 | 向导成功弹窗但 memory_goals 仍 0 行 | 向导写 `goals` 表；锚点读侧只认 `memory_goals`（两套 goal 系统缝隙） | 弃 J-01 建锚，改 persona 快车道（唯一全 UI 路径；guest 被路由守卫挡在 persona 外——`routes.dart` isGuestUser 恒重定向） |
| G3 | tester wipe 无效 | 登出后重进复用旧用户 | tester 进程 wipe ≠ app 侧 keychain | UI 登出（产品自身清会话） |
| G4 | 登录后落在非驾驶舱 tab | dashboard 判定失败 | StatefulShellRoute.indexedStack 恢复登出前 tab（attempt4 实证：数据 200 但驾驶舱未选中） | 显式点回驾驶舱 |
| G5 | 校准区 baselineMinutes=null | 「调整这次行动」结构性缺席 | 校准锚点只读 taskListProvider 投影，向导直达执行面时投影未含新任务（runB lesson；产品 hasAnchor 门如实不出假入口） | 真实用户绕道：任务列表投影水化后回执行面（姊妹会话同卡补 hydration detour；r5 仍 null，见 limitations §3） |
| G6 | **Hybrid start 系统性挂死** | POST /journey/hybrid 100% 超网关 30s→503；run 永久 RUNNING/prep | **产品缺陷反例**（见 limitations §2：3/3 用户复现，pg 锁证据） | 不修产品（验证卡边界）；反例+日志+锁证据交付 |

## 4. 运行台账（同版本 3 重复 + 失败/重试全保留）

被测产品版本恒为 `5cbc715f`；driver 为度量基建，其缺陷修正如实分层（运行名→steps json 为准，全部保留于 `raw/pilot_r1/` 与 `db/`）：

| 运行 | 结果摘要 | 证据 |
|---|---|---|
| pilot（13:03，前任） | 16 PASS / 2 FAIL（minutes 循环 12 次不够；hybrid G1 500） | `raw/pilot_r1/`（帧 15+console+steps+语义树 7 份） |
| attempt2 | wipe 失效复用旧会话；hybrid 500（G1）；minutes 30≠15 | `raw/pilot_r1/attempt2/` |
| attempt3 | 访客 tap 落空（内存高压渲染 >12s）；hybrid G1 | `raw/pilot_r1/attempt3/` |
| attempt4 | tab 恢复 G4；hybrid 503 首现 | `raw/pilot_r1/attempt4/` |
| attempt5 | 向导误判 stall（分类过粗）；hybrid G1 | `raw/pilot_r1/attempt5/` |
| attempt6 | **向导实际创建成功**（「你的成长计划已就绪」帧证）但 G2 判据缺失误报 | `raw/pilot_r1/attempt6/` |
| attempt7 | 降级注册链 tap 出屏；锚点失败后旅程雪崩（无恢复） | `raw/pilot_r1/attempt7/` |
| attempt8 | **锚点 PASS**（注册 q01up054542→persona）；fixture 超时（status 'done'≠'processed' 判据）；注册后首页无种子任务（G-新user 实证） | `raw/pilot_r1/attempt8/` |
| attempt9 | fixture PASS；/tasks 兜底无候选（升级=新 user_id，tasks=0 DB 实证） | `raw/pilot_r1/attempt9/` |
| **attempt10（=r1 主证）** | **16 PASS**：登出/访客/锚点/fixture/向导/意图分析/计划创建/执行面/卡住/澄清/纠正全绿；scope_this_time+minutes+diff+commit FAIL（G5，当时未修）；hybrid FAIL（G6 503） | `raw/pilot_r1/attempt10/`（24 帧+console+steps）+ `video/r1_attempt10_part1.mp4` + `db/r1_attempt10_db_evidence.json` |
| r4（姊妹会话 18:16） | 10 PASS 后 flutter_tools 通道崩溃（`Cannot close sink while adding stream`，runner 层非产品）；hybrid 503（G6 第二例） | `/tmp/q01_run_r4_console.log`（6629 行，待归档） |
| r5（姊妹会话） | 锚点/fixture/向导/执行/卡住 PASS；校准区 G5 仍 FAIL；**hybrid 503（G6 第三例，18:41:33）** | `/tmp/q01_run_r5_console.log` + `db/r5_part1_db_evidence.json` |

part2（真重启接续可见性）：未执行——part1 闭环未完成前无有效状态可接续（无假成功）。

## 5. 三证对齐（录像 × 语义树 × 只读 DB，attempt10 主证）

| 环节 | 引擎帧/录像 | 语义树 | 只读 DB（用户 `q01up874775`） |
|---|---|---|---|
| 接续面 | 01-dashboard/02-home-resume | `semantics_*_home-cold/home-seeded`（pilot；attempt10 同面） | users 1 行（email 源） |
| 锚点 | 06-persona-step1/07-modeling-deferred | textdump `wizard-intent-result` | **memory_goals 1 行 active**（persona 快车道写入） |
| 底料 | （管线在幕后）— | — | **stored_files 1（processed）+ document_chunks 9** |
| 向导/任务 | 09-13-wizard-* + 11-task-execution | textdump `wizard-intent-result` | tasks 4（计划生成） |
| 卡住/澄清/纠正 | 12-15-stuck/help/clarification/correction | `semantics_r1_*_task-execution/stuck-journey`（pilot 同构面） | **calibration_runs 1 + memory_corrections 1**（纠正提交服务端落账） |
| Hybrid | 21-hybrid-sheet/22-hybrid-judgment | textdump `hybrid-open/hybrid-judgment` | agent_runs 2（RUNNING/prep 僵尸行=反例本体）；hybrid_journey_artifacts 0（prep 产物未到提交点） |
| 回执/结果 | 18-20-minutes/diff/committed（pilot 面） | `semantics_r1_pilot_*_diff-review/committed` | pilot 用户 TCP 任务 estimated_minutes 30（commit 版本） |

## 6. 真模型用量（实测）

- 向导意图分析、恢复旅程澄清问、Hybrid prep 检索均为真实 LLM 调用（LLMRouter 31 配置；路由日志：`dashscope_standard_thinking` 为主力档）。
- `token_usage` 表（只读）：本卡升级用户路径 10 次 / 13,736 tokens（dashscope_fast，明细在 `db/*_db_evidence.json`）。语义纠正/澄清派生的调用经 grpc ChatOrchestrator，token 计量与同栈其他舰队运行共享日志流，无法按卡精确切分——按协议如实记 shared-infra attribution，不编造每卡 token 数。

## 7. 提交物与不入库说明

- 本目录 `diff_or_evidence_only.md` / `run_manifest.json` / `test_results.json` / `review_receipt.json` / `limitations.md` 五件套 + `raw/`（栈留痕、各运行 console/steps/帧、语义树）+ `db/`（只读 DB 证据）+ `video/`（引擎帧合成录像，出处披露见 manifest）。
- `scripts/devtools/q01_synth_video.py`、`scripts/devtools/q01_db_evidence.py` 为可复跑工具（一性脚本入 devtools 目录规范）。
- 原始帧与录像大文件按资源红线归档外置盘（sha256 见 run_manifest §artifacts），主盘保留证据清单与压缩件。
