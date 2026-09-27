# WT760-S01 · Community Realtime/Read-model 真相复测报告

- **Agent**: wt760（node-b）
- **卡面**: `v3/07_tasks/cards/S-01.md`（Stream COMMUNITY，Gate V3-5，Risk medium）
- **Base SHA**: `d80b602a1b41e174fe6f838fd1b7e99aa6945b5d`（轮#250 派出时 main）
- **Final SHA**: 本分支 `agent/node-b/wt760/s01` 提交（见 commit 行；工作树零源码改动，改动=报告+证据+台账 495 登记）
- **执行时点**: 2026-09-27 深夜（live 栈=主仓 checkout `/Users/brsama/code/GitHub/Sparkle-project` 的 uvicorn :8000 + gRPC :50051 + 网关 :8080 + docker sparkle_db/redis/minio，全程未重启/未触碰任何栈进程与容器）
- **状态**: **READY_FOR_REVIEW**（卡面协议：不自评 DONE，待独立审查）

---

## 1. 结论一句话

两真实测试账号经 :8080 网关走完 join/chat/checkin/reconnect 全环**全部真实通过**；V2.5 快照所述 M-3（社群 WS 502 上游不可达）**在当前栈已不复存在**（群 WS 与个人 WS 双端点实测 24–65ms 握手成功）；CQRS community post 投影面为**零生产者+零读取者的闲置接线**（已登记 V3-FIX-495）；live 失败路径无 mock 回退（移动端 mock 仅受显式 demo 开关门控）。

## 2. 五面逐面证据（卡面 Work 2）

测试账号（guest 登录 API 创建，用户名明标测试身份）：
- A = `wt760s01_a`，user_id `eae2761d-3dde-4a89-a01d-5ae7e4954ce9`，seed_status=seeded
- B = `wt760s01_b`，user_id `43d9727f-093c-424f-b04b-4ba24eafe7bf`，seed_status=seeded
- 测试群 = `52fe48b1-98e7-475f-b3db-135eacb149b7`（"wt760s01 真相复测群(测试)"，squad，is_public=false）
- 证据原始流：`v3-output/WT760-S01/evidence.jsonl`（JSONL 逐帧）+ `live_run1_full.log` + 可重复驱动脚本 `wt760_s01_live.py` / `wt760_s01_followup.py`

| 面 | 路径/对象 | 实测结果 | 证据锚点 |
|---|---|---|---|
| ① WS path | `GET /api/v1/community/groups/:gid/ws`（gateway）→ engine `community.py:1820 websocket_endpoint` | A/B/重连共 5 次握手全 OPEN（24.2–64.6ms）；非成员 4003 闸与 401 鉴权闸在位（未带 token 访问监控面得 401） | evidence.jsonl `ws connect A/B`、`ws connect B-reconnect` |
| ② Gateway 转发 | `WsAuthMiddleware` → `HandleCommunityWS`（websocket_proxy.go:127，UUID 防穿越校验）→ 反向代理 engine；个人通道 `/api/v1/community/ws/connect` 同构 | 双向帧透传真实可达：HTTP 发消息→对端 WS 收到全量 MessageInfo 帧；WS typing→对端实时收到（带 `user_id` 注入）；member_checkin 广播双向可达 | evidence.jsonl `ws frame B tag=msg1-broadcast-to-B`、`typing-broadcast-to-A`、`checkinA/B-broadcast` |
| ③ Projection | `cqrs:stream:community` → CommunitySyncWorker（consumer `community_worker_1`）→ Redis `post:view:*`/`feed:global` | **闲置但健在**：XLEN=0，consumer group `community_projection_group` last-delivered-id **0-0（自建组从未投递）**，pending=0，`post:view:*` 0 键、`feed:global` ZCARD=0。群聊/打卡实时**不经过**该投影（engine 进程内 ConnectionManager + Redis pub/sub 直达）——实时面靠它照常全绿 | redis-cli XLEN/XINFO GROUPS 实录（报告 §4） |
| ④ Outbox | `event_outbox` 表 → gateway OutboxPublisher → Redis bus | 521 行全部 published（galaxy 321 / memory 142 / action 17+14 / run 27），`community.post.*` **0 行**——posts 写路径（engine `POST /community/posts`）不产 event_outbox 行；gateway UnitOfWork 写入方仅 galaxy/task/user_preferences 三服务 | psql GROUP BY 实录（报告 §4） |
| ⑤ DLQ | `cqrs:dlq` stream | XLEN=0，无死信 | redis-cli 实录 |

**PEL/FIX-461/469/481 链的真实状态**（卡面要求的如实声明，不强测崩溃）：正常运行路径下 PEL 恒空（XPENDING pending=0，consumer idle 轮询）、processed_events 表 0 行——即三代修复的耐久/幂等面在 community 流上**没有真实流量可锻炼**，其正确性当前仅由单测承载（`base_pel_redelivery_test.go`、`base_processed_cache_test.go`、`outbox/repository_test.go`，本卡全部点名重跑通过，见 §6）。崩溃恢复语义未做进程内强测（纪律：不重启/不杀栈进程），以文档声明：461 修复覆盖「"0" 起排空自身 PEL 先于读新消息」、469 修复覆盖跨重启 processed_events 等值命中、481 修复覆盖进程内缓存有界化——单测即其回归锚。

## 3. 两账号全环时间线（run1，串行、步进 ≥1.2s，总 90.5s）

| t(s) | 步骤 | 结果 |
|---|---|---|
| 1.6 / 3.5 | guest 登录 A / B（POST /api/v1/auth/guest?guest_id=wt760s01_a|_b） | 双 200，seeded |
| 4.8 | A 建群（POST /community/groups） | 200，126ms |
| 6.1 | B 加群（POST /groups/:gid/join） | 200 `{"success":true}` |
| 7.4 | 成员核验（GET /groups/:gid/members） | 200，双成员在册（owner+member） |
| 8.6 / 9.8 | A/B 双 WS 经网关握手 | OPEN 28.4ms / 24.2ms |
| 13.9 | A 发消息1（nonce=wt760s01-n1-…，HTTP POST messages） | 200 58.7ms；**B 的 WS 实时收到广播帧**（content 全等） |
| 29.2 | B 发消息2 | 200 89.4ms；**A 实时收到** |
| 47.0 | B WS 发 `{"type":"typing"}` | **A 实时收到** `{"type":"typing","user_id":uid_b}` |
| 54.3 | A 打卡（POST /community/checkin，25min） | 200：streak=1，flame=12，rank=1，count=1；**B 实时收 member_checkin** |
| 64.6 | B 打卡（40min） | 200：flame=17，count=2；**A 实时收 member_checkin** |
| 78.8→86.0 | B 断连→A 发消息3（B 离线）→B 重连 WS | 全 200；重连 OPEN 64.6ms |
| 88.1 | **重连补齐**：B GET messages | **count=5，离线消息3 在列**（含 2 条打卡系统消息） |
| 89.3 | 对账：A GET messages 交叉核验 | **与 B 读到的 5 条内容全等** |
| 90.6 | 火堆权威态（GET /groups/:gid/flame） | total_power=29=12+17，双成员火苗在册，bonfire_level=1 |

followup 轮（`wt760_s01_followup.py`）补两钉：
- **nonce ACK 路由语义**：仅持群 WS 的客户端**收不到** ack（控制组，msg4）；客户端同时持个人通道（移动端 `community_websocket_service.dart:234/309` 的真实双通道形态）时，ack `{"type":"ack","nonce":"wt760s01-n5-…","message_id":…}` **在个人通道实时到达**（断言 ack_on_personal=true）。此为设计语义（`send_personal_message`→Redis `user:{uid}`→`user_connections`，群 WS 不注册该表），非缺陷；ack 落空时被 `_trigger_offline_push` 显式跳过（websocket.py:589 ack 白名单），不污染推送。
- **全离线补齐**：B 双通道全断→A 发消息6→B 重连→history count=8、消息6 在列（msg6_present=true）。

## 4. Read-model 对账表（卡面 Work 2 + 任务书第 3 条）

| 读面 | 权威源（engine API） | 网关读侧 | 对账结论 |
|---|---|---|---|
| 群消息历史 | engine DB（`GET /community/groups/:gid/messages`） | 网关纯代理（proxyWithHeaders，无缓存层） | A/B 两个读者逐字节一致（5/5、8/8）；重连补齐=权威源回放，无假数据 |
| 打卡/火堆 | `POST /checkin` 响应 + `GET /groups/:gid/flame` | 同上代理 | 12+17=29 全等；rank/count 语义随打卡时点一致 |
| 实时帧 | engine ConnectionManager 广播 | 网关双向代理 | 逐帧全等（MessageInfo 原文） |
| posts 投影（`post:view:*`/`feed:global`） | engine feed API 直读 DB | **无任何路由读投影键** | **投影=闲置死接线**（零生产+零读，→ V3-FIX-495）；不影响 chat/checkin 真实性 |
| CQRS 流/PEL/DLQ | —（零流量） | — | stream 空转健康、PEL 空、DLQ 空 |
| 网关 CQRS 健康面 | setup.go:548 outbox pending 计数 | pending=0（521 行全部 published） | 无积压 |

## 5. Seed/Mock 清单（卡面 Work 3；标记修复属 S-03，不在本卡改）

**真源（live 实测真实行为）**：本报告 §2/§3 全部证据链。

**种子（seed，明确标注）**：
1. guest 登录播种：`backend/app/services/guest_seed_service.py`——新 guest 自动播种演示面；本卡两账号 seed_status=seeded。社群面种子物：6 个演示群（`算法冲刺小队`/`期末自习室`/`英语口语晨读营`/`产品设计共学社`/`考研政治夜航团`/`AIGC 创作实验室`，guest_seed_service.py:2770-2867，含虚构 total_flame_power/today_checkin_count/announcement，按名共享给所有 guest）、演示用户（`_ensure_demo_user`：阿泽/Nora 等）、群消息/任务/好友。**缺口（→S-03）**：演示群无 `is_demo` 类标记， COMMUNITY.md「seed group 明确标示演示」与 S-03 验收「seed/demo group 明确标演示」未满足；对照 O1（J-01）仅计划面带「示例」来源标记。
2. guest 个体种子痕迹：昵称 `访客体验01_x`、dicebear 头像、flame_level=15 起步（种子预设非真实 earned）。

**桩（mock，明确标注）**：
1. `mobile/lib/features/community/data/repositories/mock_community_repository.dart`——仅当 `DemoDataService.isDemoMode=true`（默认 false，demo_data_service.dart:135）时经 `communityRepositoryProvider` 启用；**live 失败不回退 mock**：WS 失败走 error 态+调度重连或终态失败（community_websocket_service.dart:283-291），feed 断网回退走 N34 本地快照且带 `fromCache/asOf` 时点标记（诚实降级，非冒充实时）。
2. `accountability_repository.dart` 有 `_demoCurrentUserId=MockCommunityRepository.currentUserId` 引用（demo 路径专用）。
3. 无网关/引擎侧社群 mock 桩（community 链路两端均为真实现）。

## 6. 发现与处置

| # | 发现 | 定性 | 处置 |
|---|---|---|---|
| 1 | M-3：社群 WS 502（V2.5 快照遗留疑项） | **已消解** | 群/个人双 WS 端点 live 实测全通（本报告 §2①②）；无需修复 |
| 2 | community post CQRS 面零生产者+零读取者；461/469/481 链 community 流真实流量零覆盖 | 真缺陷（架构闲置面，P3） | **范围外**（卡面明示「不直接重写」）→ 登记 **V3-FIX-495** OPEN（DYNAMIC_ISSUES.md 末行；495 预分配号复核空闲——本 base 台账在册最高 490；集成 main 已前进至 6164cfae 含并行批次 491/492/493，无撞号） |
| 3 | 演示群无 demo 标记 | 既有欠账 | **S-03 验收项明确承接**（S-03.md:27），不重复立项；本报告 §5 提供清单输入 |
| 4 | nonce ACK 仅个人通道可达 | 设计语义（非缺陷） | 实测双向钉死（§3 followup），移动端双通道形态下成立；报告留档 |
| 5 | 卡面范围内缺陷 | 无 | live 全环绿，无红可返 |

## 7. 验证实录（任务书第 6 条）

- **pytest**（worktree 隔离环境，SECRET_KEY 最小注入，无 DATABASE_URL→sqlite 内存库，未触 live 库——dbguard 正确拒绝过一次误用 live 库的尝试）：
  `tests/test_community_security.py` 12 passed + `tests/test_community_e2e.py` 14 passed = **26 passed, 0 failed**
- **gateway go test**（触达包）：`internal/cqrs`、`internal/cqrs/event`、`internal/cqrs/outbox`、`internal/cqrs/worker`（含 461/469/481 回归钉）、`internal/worker`、`internal/handler`（WS 代理族）——**全 ok 零 FAIL**
- **mypy**：`app/api/v1/community.py` 自身 **0 错误**（依赖链 60 条为 54 个未触碰文件的既有基线；本卡 Python 零改动→零新增）
- **ruff**：`community.py`/`community_service.py`/`guest_seed_service.py`/`websocket.py` **All checks passed**
- **台账 verify**：`ledger_union_merge.py --verify` → 334 行 V3-FIX、无重号、状态枚举合法、**零 FAIL**
- worktree 内 `make proto-gen`（PROTO_USE_DOCKER=0）仅为让隔离测试环境补齐 gitignored 生成物，未触 proto 契约源

## 8. 可重复性声明

重跑路径：①`/opt/homebrew/bin/python3.11 v3-output/WT760-S01/wt760_s01_live.py`（需 live 栈，guest_id 前缀 wt760s01 可改）→ 产出同构 JSONL；②`.../wt760_s01_followup.py` 复现 ACK 双通道与全离线补齐钉；③§4 Redis/psql 只读探针命令逐一可重放（截至本报告时点同态）。测试群与账号均带 wt760s01 明标，留在库中可查证、可清理，未触碰 ns001 或任何其他用户数据（全程未对 ns001 发出任何请求）。

## 9. 验收对照（卡面 Acceptance）

- [x] 当前状态有可重复 report（本文件 + evidence.jsonl + 驱动脚本）
- [x] live 失败不 fallback 假 realtime（§5 桩清单第 1 条：WS 失败→error/重连/终态，mock 仅显式 demo 开关门控）
- [x] base/final SHA、targeted tests、integration 证据齐备（§头部、§7、v3-output/WT760-S01/）
- [ ] review receipt —— **待独立审查人签署（故状态 READY_FOR_REVIEW，非 DONE）**
