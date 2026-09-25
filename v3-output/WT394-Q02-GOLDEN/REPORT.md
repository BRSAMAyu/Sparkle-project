# WT394 · 卡 Q-02 REPORT — 20 Golden Journeys 三端终验

- base SHA: `60366592`（worktree `wt394-q02-golden` 起点，clean）
- final SHA: 见单提交（`test(golden): wt394 卡 Q-02 …`）
- 状态：**READY_FOR_REVIEW**（Worker 不自报 DONE；6 条 FAIL 已逐条开动态卡，0 waive）
- 权威清单：`v3/05_metrics_eval/GOLDEN_JOURNEYS.md`（GJ01-20）；三端口径按 U-09 允许差异表（`v3/04_ux/MULTIPLATFORM.md`）+ 两段交付分界

## 1. 结论

**20 条黄金旅程在常驻栈（引擎 :8000 + 网关 :8080 双 200、真实 LLM、真实 MinIO/Redis/Postgres）上 headless API 级真跑：13 PASS / 6 FAIL / 1 RESTRICTED。**

- 6 条 FAIL 同一产品级根因（V3-FIX-53，P1）：`/api/v1/chat/stream` 上凡 LLM 走工具调用分支的轮次，流在首 yield 前死亡（200+空体或 ECONNRESET）；纯文本轮稳定正常。终验轮 13/13 chat 拍全空。
- GJ10 叠加第二个独立缺口（V3-FIX-54，P2）：用户文档删除无任何 HTTP 出口（`DELETE /documents/{id}` 404；`/documents/clean` 为 ingestion 独立 multipart 子系统）。
- GJ19 remote HTTPS 口径如实 RESTRICTED（本环境无云端，不伪造）；其 local 段 6/6 全绿（设备注册/列表隔离/登出）。
- 核心 8 条逐条结论见 §3；语义层不被 chat 缺陷遮蔽的旅程，另以 sqlite 隔离真服务直驱链（wt384/wt393 手法）交叉锁死，3/3 绿。

## 2. 证据与复跑

- 证据目录：`v3-output/WT394-Q02-GOLDEN/`
  - `raw/<GJXX>_local.jsonl` × 20：逐步请求/响应摘要/断言链/耗时，旅程末 `seq:"verdict"` 行含 verdict+notes（无手填数字，全部程序化落盘）
  - `summary.json`：20 条汇总（由 raw 程序化汇总生成）
  - `HUMAN_INBOX.md`：视觉/真机/远程采集清单（不伪造截图录屏）
- 复跑（可 `--help`）：
  ```
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py                # 20 条全跑（local）
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py --gj GJ04,GJ06 # 子集
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py --env remote --remote-url https://<host>  # remote 口径（无 URL 则如实 RESTRICTED）
  ```
- service 层随行锁：`backend/tests/golden/test_q02_golden_service_layer.py`（GJ09/12/14 真服务 sqlite 直驱）
  ```
  cd backend && SECRET_KEY=q02-golden-test-key EVENT_BUS_MAX_RETRIES=0 .venv/bin/python -m pytest tests/golden/test_q02_golden_service_layer.py -q
  ```
- fresh state：每条旅程独立 fresh guest（`q02_<gj>_<tag>_<hex>`），不在他人数据上跑；chat 请求体 raw UTF-8（与 Flutter dart:convert 同语义），空流/重置重试一次且两次尝试全量落 raw（判定取最后，不作 waive）。

## 3. 20 条旅程逐条结论

| GJ | 旅程 | 结论 | steps | 结论要点 |
|---|---|---|---|---|
| GJ01 | fresh user → goal → first useful action | **PASS** | 9/9 | onboarding→goal 持久→任务 start→complete(evidence)→状态 COMPLETED→dashboard 反映，全链真 200 |
| GJ02 | example mode → exit demo → own goal | **PASS** | 5/5 | guest 种子演示计划可见→upgrade-guest 真转正（username 换名+token 重发）→自有 goal 建成可见 |
| GJ03 | existing user → Today → action → outcome | **PASS** | 11/11 | Today/dashboard→统一 command path（task.update_status proposal→approve）→complete+feedback→COMPLETED 真值复核 |
| GJ04 | 「我卡住了」→ one clarification → rescope | **FAIL** | 6/9 | stuck 标记/rescope(字段收缩 200)/too-hard 面全绿；**chat 拍两轮全空（V3-FIX-53）**——「一次澄清」用户拍缺失 |
| GJ05 | human action → evidence → Galaxy | **PASS** | 7/7 | complete(artifact evidence)→feedback→galaxy graph/contribution 可读；节点孵化为异步链（X-10 GJ05 服务层锁背书） |
| GJ06 | agent action → approval → run → receipt | **PASS** | 10/10 | proposal(aurora 源)→approve 落账→receipt/transitions 审计→subject 字段真改→execution run 建成+agent step 完成 |
| GJ07 | hybrid → agent prep → awaiting → resume | **PASS** | 8/8 | 双 owner run 建成→agent 步 agent-complete→run 状态可读→用户步 complete+同键重放幂等（await/complete 的 400/409 语义如实记录：await 需 prompt，重放拒绝二次生效） |
| GJ08 | correction → memory scope → next-session adaptation | **FAIL** | 4/6 | 校准卡/aurora correction HTTP 面绿；**两轮 chat 全空（V3-FIX-53）**，「下轮适配」的用户可感知拍缺失；机制面由 wt388 A-06 GJ08 17 用例（本轮复跑全绿）钉死 |
| GJ09 | memory delete → cache invalidation → no reuse | **FAIL** | 3/5 | 记忆 list/delete 排除面 HTTP 绿；**chat 存取拍全空（V3-FIX-53）**；删除→召回排除→幂等重删语义由 service 层随行锁（`test_q02_gj09_…`，绿）钉死 |
| GJ10 | RAG material → cited answer → document delete | **FAIL** | 12/14 | 上传→MinIO 预签名 PUT→confirm→status 全绿；**引用拍空（V3-FIX-53）+删除无出口（V3-FIX-54）** |
| GJ11 | return after stale plan → recovery | **PASS** | 5/5 | 过期计划建成→comeback-context 200→重锚 target_date→读回生效（stale 呈现为 wt303 客户端面） |
| GJ12 | proactive suggestion → accept/reject/mute/cooldown | **PASS** | 5/5 | 通知中心/偏好/建议反馈端点/comeback 真源全 200；mute→抑制→跨类型隔离语义由 service 层随行锁（绿）+wt384 P-05 契约锁背书 |
| GJ13 | offline → reconnect → no duplicate | **PASS** | 8/8 | 同幂等键双投→同一 proposal 无重复；approve 后完成→重放 200 幂等→today 单实例 |
| GJ14 | agent worker restart → run recovery | **PASS** | 6/6 | run 留部分进度→`/runs/recover` 对普通用户 403（admin-gated=安全语义正确）→run 状态可读→resume 200；recover_stale/inflight 双语义由 service 层随行锁（`test_q02_gj14_…`，绿：orphan→UNKNOWN_OUTCOME/queue_stale→CANCELLED/wait_expired→TIMED_OUT/新鲜不误伤）+X-10 run_r10 背书 |
| GJ15 | conflict: explicit new preference vs old observation | **FAIL** | 3/5 | 冲突读面/偏好面 200；**两条 chat 铺垫轮一空一被熔断级联 502（V3-FIX-53/52）**，冲突无法经真实对话管线浮现；resolver 语义由既有服务测试钉死 |
| GJ16 | community squad check-in → artifact feedback | **PASS** | 11/11 | 双账号→squad→join→study-room enter/heartbeat→真实错题工件创建→共享→列表读回→leaderboard |
| GJ17 | low-stimulation mode | **PASS** | 6/6 | aurora preferences 持久化（low/gentle）→control-surface 可读；策略语义由 stimulation_policy 服务测试背书 |
| GJ18 | account switch → zero cross-user leak | **PASS** | 12/14 | **核心隔离拍全绿**：B 读 A 的 task/goal 404、B 的 goals/today/chat sessions/memory/export 全部零 A 内容；chat 两轮受 FIX-49 影响 best-effort（A 私密话术未入库，该泄漏向量本身不成立，如实记录） |
| GJ19 | remote HTTPS fresh device | **RESTRICTED** | 6/6 | remote 口径无云端→如实受限；local 段 6/6：设备注册/owner 列表/第二设备隔离/登出全绿；解除条件见 HUMAN_INBOX D |
| GJ20 | full competition-quality demo cold start | **FAIL** | 12/13 | onboarding/goal/任务完成/反馈/dashboard/today/galaxy/growth/streak 全绿；**冷启动 chat 拍空（V3-FIX-53）**——竞赛演示链在 chat 处断流 |

三端适用性：后端共享语义段对 android/web/macos 平台不变（网关统一入口，summary.json 逐条登记 `three_end_applicable`）；平台差异全部是客户端段且已在 U-09 允许差异表登记，headless 渲染契约由 U-09 测试钉死；视觉/真机/远程段转 `HUMAN_INBOX.md`（A/B/D 三节）。

## 4. 失败动态卡（DYNAMIC_ISSUES.md 已追加，不动他人条目）

| ID | Severity | 一句话 | 波及旅程 |
|---|---|---|---|
| V3-FIX-53 | P1 | chat 工具意图轮次流中断（工具分支在首 yield 前死亡；200 空体/ECONNRESET；纯文本轮正常；跨编码×跨入口×双客户端 10+ 次复现；/ws/chat 异构实现未定界） | GJ04/08/09/10/15/20 |
| V3-FIX-54 | P2 | 用户文档删除无 HTTP 出口（DELETE 404；clean 为 ingestion 独立面） | GJ10 |
| V3-FIX-55 | P3 | guest 演示种子 best-effort 静默失败无观测（最终一致补种） | GJ02 观察项 |
| V3-FIX-56 | P3 | 网关在 chat 流崩溃后熔断冷却级联 502（12-30s 自愈；驱动以固定间隔吸收，如实登记） | GJ05/08/09/19 顺位 |

## 5. 质量门

- pytest（sqlite 口径）：本卡新测 **3/3 绿**（GJ09/12/14 service 链）；邻域 **agent_run 33 + memory_invalidation 11 + proactive_suggestion 12 + a06_gj08 17 = 73 绿**（含既有失败：无新增；`app.gen` 缺失的收集 ERROR 为 worktree 环境项，已按先例自主仓 `cp -RL` 补齐不入库）
- 冷 mypy：**1103 = 基线 1103 零漂移**（`mypy app/`，1383 文件）
- 守卫：**84/84 PASS**（gen 生成物补齐后）
- ruff：本卡两个新 .py 文件 **All checks passed**（I001 零容忍口径）
- OpenAPI：**零漂移**（本卡零 `app/` 改动，git status 可证：仅测试/脚本/文档/证据四类文件）

## 6. 改动清单

- `scripts/devtools/q02_run_golden_journeys.py`（新增：20 GJ headless 驱动，--gj/--env/--remote-url/--help 可复跑；断言链逐步落 raw）
- `backend/tests/golden/test_q02_golden_service_layer.py`（新增：GJ09/12/14 真服务 sqlite 直驱随行锁）
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（追加 V3-FIX-53..52 四行）
- `v3-output/WT394-Q02-GOLDEN/`（raw/*.jsonl ×20 + summary.json + HUMAN_INBOX.md + 本 REPORT）
- 环境项（不入库，按先例）：`backend/app/gen`、`backend/gateway/gen`、`mobile/lib/gen` 自主仓 cp -RL 补齐

## 7. DEFERRED

- /ws/chat（gRPC 编排）对工具意图消息的文本帧行为未定界——已列 V3-FIX-53 修复卡输入 + HUMAN_INBOX C 节。
- remote HTTPS 口径（GJ19 RESTRICTED）待云端部署后以 `--env remote --remote-url` 复跑解除。
- 视觉/真机/推送通道段全部转 HUMAN_INBOX（A/B 节清单），本环境不伪造。
- GJ05 的 galaxy 节点级出现为异步 outbox 链，HTTP 面只钉 graph/contribution 可读+完成落账；节点级真值以 X-10 GJ05 判定器锁为准（本卡不重建）。
- GJ15 冲突浮现依赖真实对话管线节奏，chat 修复后应复跑并复核 unresolved-conflicts 仲裁拍（当前 RESTRICTED-FAIL 如实保留）。
