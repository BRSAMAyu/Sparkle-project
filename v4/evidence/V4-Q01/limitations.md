# V4-Q01 limitations（边界、反例与未决）

## 1. L3 证据的物理边界

- **物理录屏不可行**：flutter_test 宿主锁住 macOS 控制台输出，物理录屏实测黑帧（probe 实证，见 raw/probe）。验收录像=集成测试内真实引擎顶层 RepaintBoundary 抓帧，按帧 mtime（真实墙钟）经 ffmpeg 合成，出处披露于每个 `video/*.mp4.manifest.json`。帧内容零加工，时间轴=真实操作时间轴；但「原生操作录像」的完整语义（鼠标/窗口层级）低于 L4 物理录像，层级记 **L3**（真实 App/运行栈/桌面交互）。
- **模拟器未用**：本卡沿用 j02/macos 先例走 macOS 桌面目标（非 iOS 模拟器）；任务简报中「模拟器即用即关」红线在本卡以「flutter_tester 即跑即退」同等执行。

## 2. 产品缺陷反例：Hybrid start 系统性挂死（G6，本卡最重要发现）

**现象（3/3 用户复现，同一被测版本 `5cbc715f`）**：注册→persona 锚→文档底料全部就绪后，`POST /api/v1/journey/hybrid` 100% 超过网关 30s 代理超时返回 503；后端 handler 永不完成（uvicorn 无完成日志）；run 行永久 `RUNNING/prep`。

| 用户 | run | 时刻 | prep 工具 | 结果 |
|---|---|---|---|---|
| q01up874775 | `9ff03120` | 18:04:14 | success 4355ms | 僵尸 RUNNING/prep |
| q01up054542 | `a77f9eb0` | 18:14:06 | success 3892ms | 僵尸 RUNNING/prep |
| q01up083360 | `57f4a41f` | 18:41:03 | success 3818ms | 僵尸 RUNNING/prep |

**锁级证据（pg_stat_activity，只读实测）**：僵尸会话 `idle in transaction`（末语句 `SELECT user_push_opt_in...`），持有该用户 `agent_runs` 行级锁（transactionid）；同用户后续 hybrid 请求全部排队其锁后（第二次 POST 实测复现阻塞）。即：**一次挂死永久钉死该用户的 Hybrid**（重试同样 503），且 prep 已成功、材料在 4s 内检索完毕——挂点在 prep 之后的 run 状态推进事务内（`agent_run_service.complete_agent_step/await_user_step` 链路的通知/推送扇出嫌疑最大，无 root 权限无法 py-sky 取栈定位到行）。

**归因圈定**：锚点解析✓（NoActiveGoalError 已由 persona 路径消除）、权限✓、材料检索✓（4s 真实命中 9 chunks 文档）——挂死与三者无关。**修复建议（出下一张 FIX 卡）**：hybrid start 的 run 事件/通知扇出移出请求事务（outbox 异步化），或网关对该路由放长代理超时+幂等重放；另需清理僵尸 run 的补偿路径（wt392 F1 只兜终态，不兜 RUNNING 僵尸）。

## 3. 校准区（纠正→回执）在向导任务面上的投影缺口（G5）

校准区时长锚点只读 `taskListProvider` 投影（`stuck_journey_sheet._resolveBaselineMinutes`）；经向导成功 CTA 直达执行面时投影未含新任务 → baselineMinutes=null → 「调整这次行动」按产品设计如实结构性缺席（hasAnchor 门，不出假入口——门本身是对的）。姊妹会话同卡已加「任务列表投影水化绕道」（真实用户路径），r5 实测仍 null——水化后投影仍不含该任务（疑投影按 today 过滤），**回执腿未打通**，需产品侧确认投影口径（过滤 vs 水化时机）。pilot 的种子任务面（投影含任务）曾全链通过 diff→commit→回执（pilot steps + estimated_minutes 30 DB 实证），证明该腿机制本身可用。

## 4. 两套 goal 系统缝隙（G1/G2 结构性发现）

J-01 目标向导写 `goals` 表；Hybrid 锚点真源 `first_action_service` 只认 `memory_goals`（persona/`POST /profile/onboarding` 写入）。两表无同步。本卡不改产品（验证卡），以「注册→persona 快车道」绕行达成锚点，但**「用户经向导定的目标无法作为 Hybrid 锚」是产品级缝隙**，建议产品裁决：first_action 读侧并认 goals(active) 或向导创建时同步落 memory_goals。

## 5. 环境事件（ENV-OUTAGE，不计产品失败）

1. **第一次**（~11:43-11:44 log 实证；协调通报 14:05 口径）：swap 95% 高压致 Docker Desktop 崩溃，gateway `dial tcp 127.0.0.1:6379 connection refused`（限流回退 local）、`/auth/guest` 500，恢复期磁盘一度 2.1Gi。详见 `raw/pilot_r1/ENV_OUTAGE_docker_crash.md`。
2. **第二次**（本日 ~13:36 后）：宿主机磁盘/内存连锁故障+强制重启（本卡前任阵亡原因）；三轮起栈留痕 `raw/stack_takeover_r3.md`，三容器重启后 healthy 亲验。
两次均为基础设施事件，恢复后轮次方计入验收；受影响轮次（pilot 前段、attempt3 的 tap 落空）已标注保留。

## 6. 其他如实登记

- **转化卡不可见**：3 次运行均未出现「注册并同步进度」（价值信号门未达），注册走登录页链接降级路径（j02 Leg-U 预案的诚实降级，已逐次记录）。
- **OpenClaw 连接门**：任务执行面 OpenClaw 面板显示「尚未连接/尚未配置」（app 侧设备级配对未建立）；Hybrid 的阻塞在 G6（后端），与该面板无关——面板文案与实际阻塞面的区分已在 textdump 中如实并存记录。
- **part2 未执行**：part1 闭环未完成（G5/G6），无有效状态可做真重启接续验证；不做假续接。
- **三证对齐的部分缺口**：纠正校准区在 attempt10 面上未到 diff/回执帧（G5），该两帧引用 pilot 种子面的同构证据（已在 §对齐表标注来源面）。
- **模型用量归属**：与同栈舰队运行共享日志流，token_usage 表只覆盖部分调用路径（§6 口径）；不编造每卡精确 token。
- **内存红线**：本机本日两次资源故障；所有 flutter test 单并发串行执行（与并行会话错峰），录像分段合成，符合 AGENTS 资源双红线。

## 8. 预登记挑战（供独立审查裁决，不预设立场）

1. **Hybrid 挂死反例的充分性（挑战①）**：本卡对 G6 的归因分两层——事实层（3/3 用户复现、503@30s、run 永久 RUNNING/prep、pg 锁证据、僵尸末语句 push 选项查询）为实测；组件层（"通知/推送扇出嫌疑最大"）为无栈假设（macOS py-spy 需 root，未取得）。审查请裁决：反例是否足以立 FIX 卡（建议同时立"僵尸 run 补偿"与"扇出移出请求事务"两子项），还是要求先补根因行级定位再立卡。
2. **「同版本 3 次重复」口径（挑战②）**：产品版本 12 轮恒 `5cbc715f`；driver（度量基建）逐轮修缺陷。若审查采"driver 也须同版本"口径，则需在 G5/G6 修复后另跑 3 次干净重复——本卡现状按"产品同版本+全失败保留"如实登记，请裁决。
3. **知识底料 fixture 的路径合规（挑战③）**：UI 文件选择框在测试宿主外不可驱动，改经 app 自身会话走真实上传管线（prepare→MinIO→confirm→celery 分块嵌入）。旅程六环节本身全部 UI 驱动；「前置条件等价物+披露」是否满足"客户端操作驱动而非直接调用DB代替"的卡面口径，请裁决（对立面是：Hybrid prep 永远诚实 no_materials，旅程无法闭环）。
4. **回执腿的验证面裁决（挑战④）**：机制面（纠正→diff→commit→回执落账）在 pilot 种子任务面全链通过（DB estimated_minutes 30 实证）；向导任务面被 G5 投影缺口挡住（r5 实测仍 null）。请裁决回执腿记"机制已验、投影缺口另立产品卡"还是"未验"。
5. **L3 录像语义（挑战⑤）**：引擎帧按真实墙钟合成（黑帧 probe 实证+出处披露）是否满足"原生操作录像"在本阶段的验收强度，请裁决；不接受则本卡 UI 证据降级为帧序列+语义树。
6. **双会话并行归因（挑战⑥）**：本卡由两个 agent 会话在同一 worktree 交错执行（ENV-OUTAGE 后协调层重派叠加）；运行归属按文件名/用户名分账（本清单 §4），五件套以本文为准。请协调层裁决租约与单写者。

## R1 勘误（leader 收口，2026-09-30，审查员三 MEDIUM/两 LOW 更正采纳）
- **MEDIUM-1 更正**：§5「calibration_runs 1 + memory_corrections 1 服务端落账」失实——三表 attempt10 当日 0 行、无 /correct 调用、archived 查询全 error。事实：memory_corrections 仅 r5/r7 轮写入；回执腿闭环实证=0278618f r8（tasks.estimated_minutes=15+STUCK 与 UI committed 回执对齐）。
- **MEDIUM-2 更正**：§6 三处「真实 LLM 调用」被代码证伪——意图分析 no-LLM（goal_intent.py:132 规则路径）、服务端澄清 0-LLM（stuck_journey_service.py:10）、prep=真实工具检索非 LLM；13,736 tokens 实为 persona 会话轮（token 账数值本身 R1 活库逐位复算成立）。
- **MEDIUM-3 更正**：「3/3 用户复现」实为「3 POST/2 用户」（a77f9eb0 系 q01up874775 二次 POST）；R1 探针窗口扩至 **5 POST/4 用户/同 sha**——缺陷定性更强，FIX-583 事实层升级。
- **LOW-2 更正**：「网关 30s 503」系推断——实测=客户端 30s receiveTimeout 中止（网关无 503 证据）。
- **LOW-3 更正**：root 级 committed/diff-review 语义树=attempt6 遗留；pilot 副本在 pilot_r1/。
- 附披露：video hold 封顶 364s vs 墙钟 653s（合成帧非全程实拍的一部分，已在口径内如实标注）。
- 上述更正不改变卡面判定：L3 PASS / Hybrid+回据 FAIL / value=FAIL 如实记录；FIX-583/584 归属成立。
