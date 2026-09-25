# WT361-S01-READMODEL · Community Realtime/Read-model 真相复测（段一）

- **卡**：S-01 段一（读模审计 + 可重复 report；live 双账号证据 DEFERRED 为段二）
- **Worker**：wt361 ｜ **基线 SHA**：`90cda638`（main）｜ **分支**：`wt361-s01-readmodel`
- **日期**：2026-09-25 ｜ **模式**：LIGHT（审计 + API 级验证；零模拟器/零 flutter/零应用库 PG 连接）
- **战区协调**：backend 改动仅 1 文件（`backend/app/api/v1/community.py`，7 行级外科改动）；不碰 `task_event_consumer`/task_event 族（wt360 战区），task 投影侧只登记。

---

## 1. 一句话结论

**当前 CQRS 社区读模投影是一条双向死链（静态考古 + live Redis 双重实证），而真正承担产品面的是 PG 直读（强一致、无投影参与）+ 群聊真 WS（进程内 + Redis pub/sub）+ mobile 诚实离线快照回落（asOf 标记，无假 realtime）。** 全部结论可由一条命令复现（§4），live 失败按卡面口径如实记录、绝不 fallback 假 realtime。

## 2. 读模投影真相表（每投影一行）

| 名称 | 来源 | 新鲜度机制 | 一致性风险 | live 可测性 |
|---|---|---|---|---|
| **community.post_view_projection**（gateway Redis：`post:view:*`/`feed:global`/`post:likes:*`） | event_outbox → Redis stream `cqrs:stream:community` → CommunitySyncWorker / CommunityProjectionHandler | 设计=事件驱动最终一致；**实际=永为空** | **DEAD_CHAIN（双向死链）**：① 写侧 `outbox.PostgresRepository.Insert` 全仓零非测试调用方→流饥饿；② 读侧无任何 HTTP handler 消费这些键→即使有值也无人读。admin `/cqrs/projections` 显示 status=active 属注册期 upsert，为观测面误导 | Redis 只读探测（本次已测：三流 XLEN=0、last-delivered-id=0-0、投影键 0 个、consumer 1 个在线等待）；段二可加 admin JWT 读 projection_metadata |
| **community.feed/posts/comments/messages**（engine） | PG 直读（SQLAlchemy：Post+PostLike+GroupMessage…；visibility/cohort/block/软删全在 SQL 谓词） | read-your-writes（无缓存层，写后立即可读） | 深分页 offset 语义（并发写翻页漂移）；无投影参与故无投影不一致 | `GET /api/v1/community/feed`（需 JWT）；本段已探 gateway/engine 200 |
| **community.post_write_event_face** | **无**——create_post/toggle_like/delete_post 不发布任何事件（无 outbox、无 event_bus、无 WS） | 纯拉取：写后靠客户端刷新 | 多端视图无推送收敛，存在陈旧窗口（如实现状，不 mock 补齐） | API 级双账号写读比对（段二） |
| **community.group_realtime**（群聊 WS） | mobile → gateway `:8080/api/v1/community/groups/{id}/ws`（票+JWT+升级限流+双向代理）→ engine FastAPI WS → 进程内 ConnectionManager + Redis pub/sub `group:{id}` 扇出 | 推送即时 | Redis 不可用时 broadcast 回落**本进程**广播（多 worker 静默丢跨进程推送——是限定性降级，非假送达）；`send_personal_message` 在 Redis 开启且接收方全实例离线时不触发离线推送（触发点仅本进程未命中分支）【登记 P2，段二 live 量化】 | 段二双账号 join/chat/reconnect（DEFERRED）；段一已验证网关升级路由在位且鉴权/限流前置 |
| **community.checkin** | PG（squad service）+ manager.broadcast 群 WS 推送 + event_bus `community.checkin_recorded`（无订阅者=纯事件流记录，代码注释如实声明） | 广播即时；无投影落地 | 离线成员靠重连后 HTTP 读收敛 | 段二双账号：A 打卡 B 在群 WS 收推送（DEFERRED） |
| **task_projection / galaxy_projection**（gateway Redis） | 与上同一 outbox 死链模式 | 永为空 | 同上；**task 事件族属 wt360 战区，本卡只登记不触碰** | 同上（三流本次全测：XLEN=0） |
| **mobile.community_read_cache** | ListReadCache 本地快照（成功落快照，连接类失败回读） | 回读=陈旧快照，UI 强制挂 fromCache/asOf「截至 X」时点标记 | 窗口由时点标记如实暴露——**诚实回落，非假 realtime**（卡面验收点） | 定向 flutter test（本段 LIGHT 不执行；命令见 §6） |
| **seed/demo 数据标记面** | V3-FIX-08：cohort（guest/seed）作者帖对真实用户在 feed 与 like 双面按不存在处理（本人除外）；mobile Mock 仓储仅 `DemoDataService.isDemoMode`（静态默认 False）启用 | 随查询实时判定 | 新增读/写面若漏用 `_cohort_visible_post_clause` 会出现可见性漂移 | API 级（段二双账号）；本段静态确认双面共用同一谓词函数 |

## 3. 发现与修复

### 3.1 登记不修（卡面 Forbidden 不重建读模；wt360 战区不碰）
- **F-DEADCHAIN**：社区/任务/星图三条 CQRS 投影链无事件生产者（`backend/gateway/internal/cqrs/outbox/repository.go#Insert` 零非测试调用方）→ 流饥饿、投影恒空、读侧零消费者。**证据**：a) 静态 grep 全仓调用面；b) live Redis 只读探测：三流 `XLEN=0`、`last-delivered-id=0-0`、`post:view:*`/`task:view:*`/`galaxy:node:*` 键数 0、`feed:global` 不存在、三个 consumer group 各 1 消费者在线等待（workers 活着但永远没有输入）。
- **F-POSTNOEVENT**：帖子写路径零事件面（见 §2 表）。现状如实报告，不补建。
- **P2（登记段二量化）**：`core/websocket.py#send_personal_message` 离线推送盲区 + `broadcast` 的 Redis-缺失单进程回落。

### 3.2 真缺陷红测先行修（本次唯一 backend 改动）
- **F-WSPPOOL（已修）**：群聊 WS 端点 `websocket_endpoint` 经 `Depends(get_db)` 注入请求级会话——会员校验 SELECT 的隐式事务连接被占住直到 handler 返回（=客户端断开），即**每个在线群成员长占一条池连接**；`DB_POOL_SIZE+max_overflow` 之下群聊在线即池耗尽，拖垮引擎全库访问面。属 realtime 面真缺陷，与段一审计直接相关。
- **修法（最小外科）**：会员校验改用短生命周期 `AsyncSessionLocal` 上下文，会话在 `manager.connect` 之前关闭、连接归还池；handler 签名去掉 `db` 参数。行为语义不变（成员放行/非成员 4003/断开清理全保留）。
- **红测证据**：`backend/tests/unit/test_community_ws_session_lifecycle.py` 3 用例（依赖面断言 get_db 不在路由依赖列表；成员路径事件序「session_close < manager_connect」；非成员 4003 拒绝不 connect）。修前 3/3 FAILED（复现 `'Depends' object has no attribute 'execute'` + 依赖断言红），修后 3/3 PASSED。
- **改动文件清单（wt349 mypy 协调面）**：
  1. `backend/app/api/v1/community.py`（唯一产品代码改动：websocket_endpoint 一个函数）
  2. `backend/tests/unit/test_community_ws_session_lifecycle.py`（新增测试）
  3. `scripts/devtools/audit_community_readmodel.py`（新增审计脚本，纯 stdlib）
  4. `scripts/devtools/README.md`（登记一行，仓库整洁规范）
  5. `v3-output/WT361-S01-READMODEL/`（REPORT + changes.patch 交付物）

## 4. 可重复报告（一条命令）

```bash
# 静态审计 + 锚点复核（零网络、零 DB，commit 级可重复）
python3 scripts/devtools/audit_community_readmodel.py --repo . --verify-anchors
# + 只读 live 探测（gateway/engine/Redis；失败如实记录；默认零 PG）
python3 scripts/devtools/audit_community_readmodel.py --repo . --live
# 结构化 JSON：追加 --format json --out <path>；live 失败即失败：--strict-live（exit 2）
```

本次基线采样（2026-09-25，dev 栈在跑）：gateway `/api/v1/health`=200、engine `/health`=200、Redis 三流 XLEN=0 + 投影键 0（死链 live 实证）；17/17 代码锚点命中。原始 JSON 已归档本目录 `audit_baseline_20260925.json`。

## 5. 段二 live 双账号证据面（DEFERRED 交付清单）

需要：2 个真实测试账号（JWT 各一，`accepted_tos/privacy` 注册探针同款）+ 同群组成员资格 + 可选 1 台真机/模拟器（mobile 侧 UI 面；纯 API 级证据则免）。执行面：
1. **join/chat/reconnect**：A、B 先 `POST /groups/{id}/join`，各开群 WS（网关 `:8080/api/v1/community/groups/{id}/ws`，票面），A `POST /groups/{id}/messages` → 断言 B WS 收到 broadcast；B 断网重连（新票）→ `GET /groups/{id}/messages` 收敛断言。
2. **checkin 推送**：A `POST /checkin` → B WS 收打卡推送 + `community.checkin_recorded` 事件落 bus。
3. **写读一致**：A `POST /posts` → B `GET /feed` 断言出现（并如实记录「无推送、靠刷新」的陈旧窗口时长）。
4. **seed 标记**：cohort 种子帖对真实账号不可见断言（feed + like 双面）。
5. **P2 量化**：双 worker 下跨进程推送丢失复现（如部署条件允许）。

## 6. 验证记录（本 worktree 内）

- 定向 pytest（sqlite in-memory 口径）：新增 3 用例 + 社区回归批 `tests/test_community_security.py tests/test_community_e2e.py tests/test_s04_community_feedback_evidence.py + 8 个 unit/api 社区套件` = **109 passed**；另 `tests/integration/test_community_integration.py + 2 unit` = 16 passed / 2 skipped。
- 定向 flutter test（mobile 回落缓存）：DEFERRED（LIGHT 限制；§5 段二面含 UI 证据补口）。
- 守卫 / 冷 mypy / 合并态复验：见 §7（收工门数据）。

## 7. 收工门（结果回填）

- 守卫：`bash scripts/run_all_rule_guards.sh` → 84 条 exit **0**（见 commit 前回执）
- 冷 mypy：`rm -rf .mypy_cache && mypy app --ignore-missing-imports --no-error-summary | grep -c 'error:'` → **≤1278** 棘轮内（见 commit 前回执）
- 交付物已 commit 进分支；`git diff --binary main...HEAD > changes.patch`
