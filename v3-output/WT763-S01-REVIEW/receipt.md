# S-01 Review Receipt · wt763 独立审查

- **审查人**: wt763（node-b，未参与 S-01 实现）
- **日期**: 2026-09-28
- **审查对象**: V3 卡 S-01（Community Realtime/Read-model 真相复测），卡面 `v3/07_tasks/cards/S-01.md`
- **被审交付**: wt760，`v3-output/WT760-S01/`（report.md + evidence.jsonl 75 行 + 驱动脚本 ×2），主仓提交 `5e7a24431766c9162c882d45a2d1b2a6ec0ffc87`（base `d80b602a` 为其祖先，已核）
- **审查方式**: 独立执行关键验收，非读报告签字。主仓只读；worktree `agent/node-b/wt763/s01rev`（本 receipt 所在）。

## 结论：**APPROVE**（验收达成为真，附 3 条轻微备注）

卡面 Acceptance 两条均独立复核成立：
1. **当前状态有可重复 report** —— 成立（见 §1/§2/§3/§4）。
2. **live 失败不 fallback 假 realtime** —— 成立（见 §5）。

## 1. evidence.jsonl ↔ report 数字抽检对账（逐项过）

| 项 | 报告声称 | evidence.jsonl 锚点 | 判定 |
|---|---|---|---|
| 火堆对账 | 12+17=29 | L27 A flame_earned=12、L31 B=17、L45 total_power=29（双火苗在册） | 一致 |
| 重连补齐 | count=5、msg3 在列 | L42（5 条 contents 全列、msg3_present=true） | 一致 |
| A/B 读侧一致 | 逐字节一致 5/5 | L44 same=true a_count=5 | 一致 |
| followup 离线补齐 | count=8、msg6 在列 | L74 count=8 msg6_present=true | 一致 |
| nonce ACK 双通道 | ack_on_personal=true | L65 ack 帧含 nonce wt760s01-n5 / L67 断言 | 一致 |
| WS 握手延迟 | 24.2–64.6ms | L11=28.4 / L12=24.2 / L39=64.6 | 一致（见备注 N2） |
| 打卡实时广播 | 双向 member_checkin | L28/L32/L30/L34（broadcast+echo 四帧） | 一致 |
| typing 注入 user_id | A 实时收到 | L25（frame 含 user_id=uid_b） | 一致 |
| 账号身份 | A=eae2761d…/B=43d9727f… | L4 | 一致（本次审查 re-login 实测同 uid） |

## 2. 驱动脚本静态审查

- **真打 :8080 真栈**：两脚本 `GW="http://localhost:8080"`/`GW_WS="ws://localhost:8080"`，全部 HTTP/WS 走网关路径（`/api/v1/auth/guest`、`/community/groups/...`、`/community/checkin`、`/community/ws/connect`），无 engine :8000 直连、无 sqlite/mock 短路。
- **ns001 零触碰核验**：两脚本唯一账号入口是 `guest_id=wt760s01_a/_b`（前缀过滤即账号边界），群为本脚本新建（gid 52fe48b1…，私有 squad）；全脚本及全部请求体零 ns001 引用；主仓 `backend/app` 与 gateway `internal/` grep ns001 亦零命中（该标识只存在于既有用户数据，不构成脚本可达路径）。无 docker/重启/杀进程操作。
- **诚实记录**：断言结果如实落 JSONL（如 run1 `a_got_ack=false` 未粉饰，后由 followup 钉出设计语义）。
- 备注 N3：members 步骤提取 member_id 因嵌套结构取空串（`[""," "]` 装饰性记录未断言），但原始 resp（L9）完整显示双成员，实质无碍。

## 3. 测试面独立复跑（sqlite 口径，本审查实跑）

```
cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v ./.venv/bin/python -m pytest tests/test_community_security.py -q
→ 12 passed in 0.95s
cd backend && … pytest tests/test_community_e2e.py -q
→ 14 passed in 6.28s
```
合计 26 passed，与报告 §7 完全一致。
Gateway 抽验：`go test ./internal/cqrs/... ./internal/worker/...` → cqrs / cqrs/event / cqrs/outbox / cqrs/worker / internal/worker 全 ok（含 461/469/481 回归钉所在包），零 FAIL。

## 4. live 只读抽验（2026-09-28，本审查实跑；未做写操作、未碰 ns001、未重启栈）

- 栈态：:8080 /healthz 200；sparkle_db/redis/minio 三容器 Up 16 hours（早于 wt760 执行时点，与其「零重启」声明相容）。
- 以 wt760 同款 guest 账号 `wt760s01_a` re-login（200，返回 uid 与 evidence L4 逐字相同）后只读查询：
  - 群 52fe48b1 在册，members=[wt760s01_a, wt760s01_b]；
  - messages count=8，8 条 content 与 evidence L42/L74 的 nonce 逐一吻合（n1…n6 全链在库）；
  - flame total_power=29、双火苗 17/12 —— 与报告及 evidence 一致。
- CQRS 五面只读探针重放（redis-cli/psql，只读）：`cqrs:stream:community` XLEN=0、consumer group `community_projection_group` last-delivered-id=0-0 pending=0、`cqrs:dlq` XLEN=0、`feed:global` ZCARD=0、`post:view:*` 0 键；psql `event_outbox` 521 行且 `community.post.*`=0（galaxy 321/memory 142/action 17+14 与报告分项一致）、`processed_events`=0。**wt760 §4 read-model 对账全部复现。**
- 代码锚点抽验：`community.py` websocket_endpoint（~:1820）、`websocket_proxy.go` UUID 防穿越闸（:127-134）、`community_websocket_service.dart` 失败路径（:283-291 error/重连/终态）、`guest_seed_service.py` 演示群播种（~:2770 算法冲刺小队等）均如报告所述。
- V3-FIX-495 已在 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 末行在册（OPEN，wt760 登记），与并行批次 491-493 无撞号。

## 5. 「不 fallback 假 realtime」独立核验

`mobile/lib/features/community/data/repositories/community_repository.dart:15-17`：Mock 仅在 `DemoDataService.isDemoMode` 为真时启用；`demo_data_service.dart:135` `static bool isDemoMode = false`（默认关）。WS 失败路径（community_websocket_service.dart:283-291）为 terminal failure 或 error+调度重连，无 mock 回退分支。断网 feed 读回走本地快照且带 fromCache/asOf 标记（诚实降级）。报告 §5 定性准确。

## 备注（不阻塞 APPROVE）

- **N1（证据指针缺口）**：报告 §2 引用的 `v3-output/WT760-S01/live_run1_full.log` 不存在于交付目录、也从未入库（`git show 5e7a2443 --stat` 仅 4 文件）。实质无损——`evidence.jsonl` 75 行即 run1+followup 的完整逐帧记录且已独立抽验；但该指针失实，建议主会话顺手在台账或后续提交中更正报告该行（改为仅引 evidence.jsonl）。
- **N2（计数口径）**：报告 §2①「A/B/重连共 5 次握手」与 evidence 不严格对齐——带延迟实测 3 次（28.4/24.2/64.6ms，均在声称区间内），followup 另有 5 次 OPEN 记录但未记延迟（合计 8 次）。结论方向不受影响。
- **N3（脚本装饰性断言）**：members 提取 bug（§2 末），未影响证据实质。

## 销账判断（给主会话的建议）

S-01 四项 Required evidence 中 base/final SHA、targeted tests、integration 证据三项已齐并经独立复跑；review receipt 由本文件补齐第四项。**建议主会话将 S-01 按「验收达成」销账（tasks.json 置 done，引本 receipt 与 wt760 报告为据）**；备注 N1 的报告指针更正与 V3-FIX-495 的接线/下线裁决不阻塞销账（前者一行文案、后者已独立立项）。
