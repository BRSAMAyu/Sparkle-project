# V4-F03 · diff_or_evidence_only

## 一句话设计

把既有权威回执（X-03 action_command 回执/终态行）经 D01 冻结投影器接成 `experience_event.v1` 生产流（backend 适配器 + 三个 additive 韧性壳挂点），移动端以统一适配器消费该事件做视觉/声/触决策（去重=内容寻址 event_id、replay 抑制、当前对象 version 校验、subject 语义分层路由），成功视觉唯一经 F02 PixelSuccessBadge 承载、unknown 态绝不借成功视觉。

## 实现面（差量清单）

新增 5 文件 + 改动 3 文件（+31/-1 行，全 additive）：

| 文件 | 性质 | 内容 |
|---|---|---|
| `backend/app/core/experience_copy.py` | 新（契约面） | B05 §3 R1-C5 指定 owner=F03 的**冻结文案表**（17 键逐字冻结）+ 反馈语义分层封闭路由（`SUCCESS_FACE_SUBJECT_TYPES={task,goal,plan}`、committed/kind/error_state 三路由）；全表无「精通/已掌握」类键（结构性：呈现层无词可拼） |
| `backend/app/services/experience_presentation_adapter.py` | 新（服务面） | 回执→事件适配器：`project_action_receipt`（`project_terminal_reason` 生产调用方）/`project_action_error`（`project_error_state` 生产调用方，`ACTION_INVALID_COMMAND` fail-loud 上抛）/`project_feedback_receipt`（证据登记类通用面）；I2 第二门（status=COMMITTED 且 receipt 本体自洽才可产 state_confirmed）；version 锚定（receipt after→before→proposal token，全链缺失拒绝）；发布走既有 `experience.event_projected` 单主题；两个韧性壳 safe 挂点 + by-id 错误面挂点 |
| `backend/tests/services/test_experience_presentation_adapter.py` | 新（测试） | 17 测：三验收面正反 + C-1/C-2 闭合 + 身份重放稳定 + copy 表冻结 |
| `mobile/lib/core/experience/experience_event.dart` | 新（模型面） | `experience_event.v1` 封闭解析（fail-safe：任何结构违规/E1·E2 破坏/词表外→null，调用方忽略+计数）；词表常量与 D01 逐字对齐 |
| `mobile/lib/core/experience/experience_feedback_adapter.dart` | 新（呈现面） | 统一反馈入口：去重集合（event_id）→ replay 抑制（不重复震/音/庆祝、文本仍恢复）；version 校验（未知→unknown 态、不符→过期抑制）；subject 语义分层（成功面孔=task/goal/plan；memory→高亮+轻触；run/intervention→中性；证据登记→「证据已登记」）；失败面（version_conflict→conflict、其余→failed 徽章 + 警示触一次）；冻结文案表 17 键镜像 backend；声/触委托既有 SensoryFeedbackService（无第二路径），视觉唯一经 F02 PixelStateBadge/PixelSuccessBadge |
| `mobile/test/core/experience/`（2 文件） | 新（测试） | 18 测（适配器 14 + 徽章绑定 4） |
| `backend/app/services/action_command_service.py` | 改 +11（二审勘误） | 两个 additive 挂点：`approve` 成功落账后、`expire_stale_proposals` 过期转场后（均韧性壳，宿主语义零变更） |
| `backend/app/api/v1/action_proposals.py` | 改 +8 | `approve` 错误面挂点：ActionCommandError → terminal_failed 呈现事件（HTTP 错误映射原样进行） |
| `backend/app/services/intervention_record_service.py` | 改 +11/-1 | D01 二审 C-2 闭合：`mark_seen` 挂点不再丢弃投影结果——降级 reason 以稳定前缀 `experience_presentation.degraded` 留可观测 warning（转场不受影响） |

## 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- 未重建 V3/D01/F02：投影器零复制（`project_terminal_reason`/`project_error_state` 直接 import）；无新表/迁移/proto/事件总线（发布走 D01 同主题）；mobile 声/触委托既有 `SensoryFeedbackService`，视觉走既有 F02 组件族——**无第二视觉/发声路径**。
- 复用既有权威 6 处：D01 投影器与 `ExperienceEventService` 主题、X-03 `ActionCommandError.error_code`/`ProposalStatus` 词表、F02 `PixelStateBadge`/`PixelSuccessBadge`/`PixelRunState`、既有 `SensoryFeedbackService` 出口。
- C-1（D01 二审挑战）**属本卡卡面并已落**：卡面「接既有业务receipt到ExperienceEvent」的 X-03 回执面 + 协调方指名移交；`project_terminal_reason`（approve/过期清扫）与 `project_error_state`（approve 错误面）现均有生产调用方，fail-loud 从生产路径可达且有测试。
- C-2 **属本卡卡面并已落**：D01 二审明文「建议 F03 接线消费方时把降级 reason 纳入其可观测面」；`mark_seen` 挂点捕获返回值 + 结构化 warning，测试断言日志内容。

## 与验收逐条对照（每面一正一反，全部可失败）

1. **无committed回执不能触发成功；同event重播不重复震/音**——backend：PENDING/状态谎报无回执本体/回执体不自洽三路拒绝（`no_authoritative_receipt` 等），user_cancelled/rejected 不产事件，version 全链缺失拒绝不猜；mobile：解析层 E1 门（state_confirmed 无 receipt_ref → ignore）、`ignoredInvalid` 零感官；同 event_id 重播 `replaySuppressed`（sink 调用数恒 1、无庆祝、copy 仍在——文本状态仍恢复）。
2. **仅保存记忆不显示任务修改完成；证据登记不叫精通**——冻结文案表结构性分层：memory 路由→`memory.saved`（「记忆已保存」）永不映射任务成功文案/成功模态（成功面孔封闭集 {task,goal,plan}）；证据登记→`evidence.registered`（「证据已登记」）；**全表禁词扫描**（精通/已掌握/掌握度/mastery 零命中——mastery/deliverable 目的约束归 I07 锁面，本卡只落「不叫精通」的呈现纪律）；mobile 同构路由 + 徽章红线（memory 树中无 PixelSuccessBadge、无成功声触）。
3. **断网未知状态仍可查，不渲染为绿色成功**——`resolveUnknownDisplayState()`=PixelRunState.unknown（虚线+问号+中性槽，语义「结果未知」）；committed 事件+当前版本未知→`presentUnknown`（unknown 徽章、零感官）；版本不符→`staleVersionSuppressed`；失败面 version_conflict→conflict 徽章/其余→failed；widget 反例：unknown/failed/conflict 树中 `PixelSuccessBadge findsNothing`，正例控制组（成功面孔）证明断言判别力。

## 生产接线（呈现事件从今天起有真实生产流）

- `approve` 成功 → `state_confirmed`（task.committed，成功模态）；
- `approve` 失败（版本冲突/过期/非 pending/未授权/不存在）→ `terminal_failed` + 对应 error_state（中性模态）；
- 过期清扫 → 同上（与懒转同 dedupe 身份，双投影被内容寻址幂等吸收）；
- 用户取消/拒绝 → 零事件（契约 §6）；
- `mark_seen` 真实转场 → D01 rendered exposure（既有）+ 降级 reason 可观测（C-2）。

## 红线自查

- 不碰 .env/proto/迁移/生成文件（`backend/app/gen`、`mobile/lib/gen` 为 gitignored 实体复制，不入库）；不碰 metrics.py（D03/I04/I08 在航冲突面）、experience_readouts.py（I08 在航）、RF-06 令牌面、五 Tab 路由。
- 纯 additive 挂点：X-03 commit 链路、HTTP 错误映射、SEEN 转场语义零变更（X-03 服务 29 测（二审 C-1 勘误：原记 32） + API 16 测 + f507 9 测 + D01 44 测原样全绿）。
- 无权限语义字段进入事件与适配器表面（消费方不得由 kind/subject 推导写资格——I1）；无 Mock/人工改库冒充模型结果；零模型调用。
- 不碰 I07 锁面（hybrid-policy）：未实现 mastery/deliverable 机制，只保证呈现层无精通词、无掌握度声明。
