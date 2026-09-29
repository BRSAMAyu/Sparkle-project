# FIX-567 · 已知限制与边界（如实登记）

## 1. WS 帧下发面未做（proto 边界，BLOCKED_CONTRACT 性质）

台账修法原文含「+WS 帧下发面（与 F03 CH-2 WS Frame proto owner 同卡族）」。本卡裁决**不实现**：

- 亲验事实：`backend/gateway` 全域 grep 零 `context_selection_receipt` 引用——receipt 今日**从不过**网关 WS 帧；移动端唯一下发源是 REST `GET /experience/context-receipts/latest`（`episode_resume_provider` → `contextReceiptProvider` → `ApiClient.get`），`selection_role` 是 payload 字段值（`ContextSelectionReceipt.to_payload()` 透传），**非帧结构字段**。
- 因此「生产者补齐 + REST latest 透传」即纯后端可完成的完整闭环（任务书预判路径，亲验成立）；任何 WS 帧主动推送 = `proto/*.proto` 契约变更，触本卡 proto 红线 → 停手，只登记边界。若 fleet 需要 WS 推送面（如 receipt 更新主动下发触发客户端刷新），须 proto owner 卡走 `make proto-gen` + 网关再生成跨层门。

## 2. 首条 resume_view 回执的触发链仍依赖既有调用方（集成间隙，非本卡缺陷）

修复后：**每当** resume view 流真实运行（I01 `GET /episode-resume/tasks/{task_id}` 成功聚合），必落 `resume_view` 角色回执，其后 `latest` 即翻转为 resume_view（新测钉死）。但移动端当前唯一 I01 调用方是 `episodeResumeProvider` 本身——其角色门要求 latest 已是 resume_view 才发起 I01 请求。故「纯移动端自发循环」的首条触发仍需任一外部源（未来 F03 resume_available 主动面 / WS 推送卡 / 深链或 /tasks 账本页等次级入口接入 I01）。本卡交付的是 R1-1 登记的「接续流 receipt 生产者」本体（contract-owner 职责）；**触发面接线**（谁发起首次 I01）属消费/集成侧后续卡，不属生产者缺陷。R1-1 勘误口径据此完整成立：strip 可现条件 = mode=live **且** resume 流 receipt 生产存在（本卡）**且** 有任一触发源发起了 resume 流。

## 3. 下发面测试口径

WS 下发面 NOT_RUN（见 #1）；REST latest 下发面已在本卡测内真实断言（`test_endpoint_produces_resume_view_receipt_in_live_mode` 直接调用 `get_latest_context_receipt` 断言 mode/selection_role/receipt_id/schema_version 透传 + 来源验证双 resolved + resolved_selected_count==2——即移动端 `_project()` 解析的同一 payload 形状）。跨进程/真 PG 面由既有 `test_episode_resume_cross_process.py` 回归覆盖（130 绿内含），未另起真栈演示（无真实凭据/设备，按纪律不伪造）。

## 4. 回执粒度语义（诚实读数，非缺省）

- 每次 I01 成功聚合产生一条新回执（新 ULID）：「同一轮一个 receipt」的「轮」= 一次聚合请求。重复装载首页会追加回执行——与 chat 面每 build 一条同纪律，幂等键防的是同 receipt_id 重放而非跨轮去重；
- 候选集 = task://+goal:// 双 selected：last_confirmed_step 的 subtask:// 与在途 run 的 run:// **不进**候选——前者属 task 聚合内部读（子任务行），后者的 scheme 在 `verify_source_ref` 当前映射中判 unknown（登记「非单行存储投影面」），进候选会在 U03 读面显示「来源已不可定位」的假阴性。若后续卡需要 subtask/run 的可验证性，应扩 `_resolve_scheme` 真源映射（其 docstring 预留的登记路径），而非在生产侧回避；
- `why_now=null`：视图的 why-now（task 字段位投影）随视图本体交付客户端；回执级 why-now（「为什么现在做这次选择」）本面无 Aurora 决策参与 → 合同 null 语义（与 pack 装配面同口径），非字段遗漏。

## 5. 环境口径

worktree 无 .env：全部 pytest 以进程级 `SECRET_KEY=x` + 自然 sqlite 运行（U13 env_discipline 先例）；`backend/app/gen` 为主检出同源复制（gitignored 生成物，test_calibration_receipt 家族收集需要），未入库未手改。mypy 暖缓存 58/59 伪差已定谳为 types-PyYAML stubs 报告序噪声（冷缓存 59=59，逐行 diff 唯一差异为既有 policy_loader 项）——报告如实入 test_results.json，未以「删断言/改口径」取得全绿。

## 6. 验收状态

自报完成 ≠ 完成：按验收模型，本卡 DONE 需独立未参与会话 R1 审查（review_receipt.json 已预登记 scope 与预挑战点）。台账行已置 FIXED@5290e010（指向证据），若 R1 裁决返工，台账按接力机制回翻。

## Errata (leader, 2026-09-30)
- R1 F-2 措辞限定：run_manifest 中「gateway 全域 grep 零引用」应读作「网关**手写面**零引用」——receipt 字样在自动生成物 schema.sql:2077 与 sqlc models.go:2784 存在（生成物随 DB 契约再生成，非逻辑携带）；实质主张（零 WS 帧/零网关逻辑）经 R1 亲验成立。
