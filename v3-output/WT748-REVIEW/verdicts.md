# WT748-REVIEW — streak 三入口收敛一致性 + proxy/幂等族残余猎缺（独立审查裁决）

- 会话：wt748（v3 航道审查 Agent，独立未参与 451/457/467/426/428/427/461 实现）
- 日期：2026-09-27
- 基线：main 合并态 `a1ab24c9`（审查自 `62e75576` 起，被审文件集 `62e75576..a1ab24c9` diff 为空——结论对当前 HEAD 有效）
- 审查对象只读：`/Users/brsama/code/GitHub/Sparkle-project`；登记与本 verdicts 在独立 worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt748-review`（分支 `agent/node-c/wt748/sysrev`）commit，不 push
- 方法：合并态真代码逐行亲读 + sqlite 内存库运行级探针（`DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v`，探针与日志同目录）；PG 级并发不做（纪律：不碰 docker），涉及 PG 并发形态处如实标 SUSPECTED 并引用既有真 PG 复现件

---

## 焦点 1：streak 表三入口收敛一致性（V3-FIX-451 / 457 / 467）

### ① uuid5 派生串同源性 — **PASS / CONFIRMED**

- `backend/app/services/achievement_engine.py:2274`：`uuid5(NAMESPACE_URL, f"achievement-streak-stats:{user_id}")`
- `backend/app/services/inventory_service.py:459`：同上，**逐字符同源**；两处 import 同型（`from uuid import NAMESPACE_URL, uuid5`，engine:18 / inventory:9）
- 两处 `user_id` 形参均为 `str`，调用链实参同源自 `str(user.id)`（inventory `use_consumable(str(...))`、engine `_update_streak_stats(user_id: str)`），不存在 UUID 对象 vs 非规范字符串分叉面
- inventory:444-448 已带跨路径耦合警示注释（"改字符串即重开双行竞态，两处必须同步变更"）——注释在场
- 运行级：探针 `probe_streak.py::test_p1/test_p2/test_p3`——engine 首建 id==期望 uuid5、inventory 首建 id==同一 uuid5、两向交叉读均单行收敛。**6/6 绿**（`probe_streak.log.txt`）

### ② ON CONFLICT 方言分派两处形态 — **PASS / CONFIRMED**

- engine:2275-2292 与 inventory:460-477 逐分支同构：
  - `postgresql` → `pg_insert(UserStreakStats).values(user_id, id).on_conflict_do_nothing()`（目标无关，pkey 仲裁；user_id 无独立唯一约束、指名会 42P10——两处注释同口径）
  - `sqlite` → `sqlite_insert(...).on_conflict_do_nothing()` 同构
  - 其余方言 → `begin_nested()` + `flush()` + `except IntegrityError: pass`
  - 方言探测同为 `self.db.sync_session.get_bind().dialect.name`
- imports：`pg_insert`/`sqlite_insert`/`IntegrityError` 两文件 :17-19/:27-29 同组

### ③ FOR UPDATE 收敛读在"对方未提交"时行为两处同型 — **PASS / CONFIRMED（代码行级）**

- engine:2253-2255 + :2293-2300 与 inventory:455-457 + :478-485 完全同型：初始 `select(...).with_for_update()` + `scalar_one_or_none()` → 缺行走方言化 upsert → **重走同一 query 对象**收敛读 → 防御回退（挂起实例仍带确定性 id 保 pkey 去重）
- PG 未提交窗行为由语句语义唯一决定（ON CONFLICT 在先到方未提交元组上阻塞→先到提交后 DO NOTHING→锁读同行），两处语句形态一致即行为同型；WT742 已有真 PG 16.15 双连接红→绿实证（`v3-output/WT742-INV457/`），本次不重做 PG
- 锁释放面一致：均由调用方事务 commit 释放，覆盖整段读算写（engine=process_event 调用链、inventory=use_consumable commit）

### ④ 451/457 修后读面对 467 未修路径重复行的暴露 — **CONFIRMED（运行级）**；暴露本体即在册 467，本次补运行级证据+触发面收敛修正（新登记 479）

- 运行级（`probe_streak.py::test_p4/test_p5/test_p6`）：同一 `user_id` 双行（一 uuid5 确定性 id + 一随机 uuid4 id，即 467 竞态产物形态）落库后——
  - engine `_get_or_create_streak_stats` 初始 `scalar_one_or_none` 恒 `MultipleResultsFound`（持久 500 面）；
  - inventory 457 修后读面同型炸；
  - 467 `_ensure_user_streak_stats` 自身读面（guest_seed_service.py:857-861）同炸；
  - 顺序形态对照：seed 先建随机 id 行 → 提交 → engine 后读 = **无重复行**，engine 认领 467 的随机 id 行（确定性 id 仲裁面被先到绕开，但不再落第二行）
- **新发现（登记 V3-FIX-479，P4）——467 的触发面比台账登记行所载更宽**：
  - 467 调用点 guest_seed_service.py:2641 操作的是 **6 个全局共享演示用户**（`spark_friend_1..6`，:2482-2491，经 `_ensure_demo_user` 按 username 复用同一批行、跨所有访客账号共享——:1599 注释自证"复用同一批行"）中的 nora/ethan/susu 三人的 streak 行；
  - 种子并非 467 登记行所述"guest→formal 升级单流一次性"——已有访客**每次 `/guest` 登录都重播种子**（auth.py:1041-1052 reseeded 路径，注释"幂等，已有数据会跳过"）；跨**不同**访客的两笔并发 `/guest` 即在共享 friend 行上构成 467 竞态，无需"同用户双端同时重放"；
  - 重复行一旦落地：此后**任何**访客登录的种子都会在 `_ensure_user_streak_stats` 读面 MultipleResultsFound → SAVEPOINT 回滚 → `GuestSeedError` → seed_status 恒 failed（auth.py:994-1013 非致命语义，登录照常 200，演示数据缺失持久化）；
  - 严重度建议 P4（留档不阻塞）：非致命、演示面、fresh-DB 首播窗口窄；但爆炸半径是"全体访客种子持久失败"而非单用户 500。

### 焦点 1 结论

451/457 三件套（确定性 uuid5 同源 / 方言化 ON CONFLICT DO NOTHING / FOR UPDATE 收敛读）在合并态两处**逐行同构、运行级单行收敛**，未发现分叉面。467 未修路径对修后读面的暴露真实存在且已运行级复现（在册 OPEN 维持），触发面/爆炸半径描述需按 479 收敛修正。

---

## 焦点 2：proxy/幂等族残余猎缺（426/428 修后形态上）

### (a) forwarded_chain_trusted 判据与网关追加契约结构互斥 — **CONFIRMED → 登记 V3-FIX-480（P3）**

- 判据 `backend/app/core/rate_limiting.py:79`：`parts[-n] == peer`（XFF 右起第 N 段 == 引擎 TCP 对端）
- 网关修后契约（仓库自身 Go 钉测钉死）`backend/gateway/cmd/server/setup_proxy_forwarded_test.go:79-100`：追加段 = **本跳 client IP**（`SetXForwarded` = `SplitHostPort(In.RemoteAddr)` host；"8.8.8.8, 203.0.113.7" 形态）；引擎视角对端 = **网关自身 IP**——两者对真实客户端**结构上永不相等** → 经网关的真实流量 `forwarded_chain_trusted` 恒 False
- 后果①：`app/api/v1/vocabulary.py:52-58` 的 XFH/XFP 可信分支死路——`DICTIONARY_PACKAGE_BASE_URL`/`GATEWAY_INTERNAL_URL` 缺省空串（settings.py:1132/:1136）时恒降级 `request.base_url`（=内网 `http://sparkle_api:8000/...`），即 428 要修的"客户端不可达坏链+内网拓扑外泄"症状在缺省 env 下依旧（本地 .env:125 有 `GATEWAY_INTERNAL_URL=http://localhost:8080` 掩护，真机客户端仍不可达）
- 后果②：428 的 Python 守卫 `tests/api/test_vocabulary_external_base_url.py:20-53` 建模"追加段==对端（网关自身 IP）"拓扑（XFF `"198.51.100.7, 203.0.113.9"`+peer=203.0.113.9）——与同批 Go 钉测**互斥的两个世界**；两守卫各自绿，合起来守不住同一契约
- 后果③：同一判据在"未追加"的透传路径（见 (c)）上反而可被完全伪造的链打开（伪造最右段=网关 IP 即过闸；探针 `probe_proxy.py::test_c` 实证）——判据在"该追未追"路径 fail-open
- 运行级：`probe_proxy.py::test_a/test_b`——真实网关形态请求（无注入/带注入两形）信任闸恒 False、`_external_base_url` 恒降级；对照面 get_client_ip/get_real_ip 右起归因仍正确（426 本体无损）
- 方向：判据改"对端 ∈ 引擎侧可信代理清单（TRUSTED_PROXY_CIDRS env）+ 链长 ≥ N"；Python 守卫测试拓扑与 Go 契约对齐。fail-closed，无新增安全面

### (b) community WS 代理路径 XFF/X-Real-IP 原样透传不追加 — **CONFIRMED（代码行级）→ 登记 V3-FIX-482（P4）**

- `backend/gateway/internal/handler/websocket_proxy.go:673-693` `buildBackendWebSocketHeaders`：入站 `X-Forwarded-For`/`X-Real-IP` **原样 Set 透传**，不追加本跳 client IP；唯一调用点 :245 `proxyWebSocket`（gorilla `dialer.Dial`），服务 HandleCommunityWS/HandlePersonalWS（setup.go:513-517 `/api/v1/community/groups/:id/ws`、`/api/v1/community/ws/connect`）
- 与 `rate_limiting.py:17-18` 声明契约（"Go 网关（httputil.ReverseProxy / **websocket_proxy**）在 X-Forwarded-For 尾部追加真实 client IP"）**相悖**——websocket_proxy 实际不追加
- 后果：引擎侧对该 WS 握手请求做右起第 N 段解析时取到客户端任写的最右段（归因可投毒）；**当前**引擎 community WS 端点（app/api/v1/community.py:1820-1890）只读 `authorization`/`sec-websocket-protocol`，IP 消费面为零 → P4 留档 + 契约文档修正，未来任何消费方接入即复活
- 排除面（逐行亲证）：`/ws/chat`（chat_orchestrator.go:227-258 网关本地 upgrade，引擎走 gRPC）、`/ws/files`（file_events.go:63-96 网关本地 upgrade + Redis hub）、`/ws/stt` 同型——均不经 websocket_proxy，无此问题
- 方向：build 标头时同 Rewrite 契约（入站链 + 恰一次追加 `SplitHostPort(r.RemoteAddr)` host），或修正 rate_limiting.py 契约声明

### (c) 网关自有限流/审计面 gin ClientIP() dev 缺省 trust-all 可伪造 — **CONFIRMED（源码行级）→ 登记 V3-FIX-483（P4）**

- 消费点：`internal/middleware/rate_limit.go:179/:219/:277/:394`、`ws_upgrade_rate_limit.go:45`（五条 WS 升级入口的共享预鉴权 per-IP 桶）、`ws_auth.go:42`（审计日志 `client_ip` 字段）均键 `c.ClientIP()`
- gin v1.9.1 库源码 `gin.go:458-475` `validateHeader`：右起扫描 `if (i == 0) || !isTrustedProxy(ip) { return ipStr }`——缺省 trust-all（`setup.go:468-479` 仅 prod 缺 `TRUSTED_PROXIES` Fatal，dev 分支不设）下全段 trusted，返回**最左段**；且 `RemoteIPHeaders` 缺省含 `X-Real-IP`（gin.go:196）——直连 :8080 请求任写 `X-Forwarded-For`/`X-Real-IP` 即任控限流桶键（轮转头绕过 per-IP 限流与 WS 升级预鉴权桶）与审计 client_ip
- prod 由 TRUSTED_PROXIES 强制闸闭合（setup.go:476-479 Fatal）；dev/直连 :8080 拓扑暴露
- 方向：dev 亦显式 `SetTrustedProxies`（缺省回环+网关容器网段），或限流键改 `RemoteIP()`

### (d) rate_limiting.py 右起解析族残余 — **CONFIRMED（运行级）→ 登记 V3-FIX-484（P4）**

- ① `get_real_ip` :103/:112-113：XFF 缺席时回退采信 `X-Real-IP`（直连 :8000 面=客户端可选头 → 限流键可轮转；探针 `test_d` 实证），与 426 单一出口 `get_client_ip`"不读 X-Real-IP"既定口径相悖；经网关面 XFF 恒在场，该分支仅直连/剥 XFF 代理拓扑可达
- ② `_forwarded_for_parts` :29-34：纯文本切分不校验 IP 形态——括号形 `[2001:db8::1]`、带端口 `2001:db8::1:40000` 以原样串参与归因与 `==` 比较（探针 `test_e` 实证）；IPv4-mapped（`::ffff:a.b.c.d`）与裸形不等价 → `forwarded_chain_trusted` false-negative。偏差方向 fail-closed，无 false-positive 安全面；属归因杂质/鲁棒性备忘
- 方向：①删 X-Real-IP 分支与 get_client_ip 对齐；②分段后 `ipaddress` 解析校验+括号剥离归一

### 零发现查证面（逐行亲证无语义偏差）

- **gRPC 桥 metadata**：网关仅注 `x-internal-api-key`/`user-id`/`x-trace-id`（internal/agent/client.go:343-357 `injectMetadata`）与 `authorization`/`user-id`（internal/handler/error_book.go:30-49）——**无任何转发头/client IP 进 metadata**；Python 侧 servicer（app/api/grpc_auth.py、agent/error_book/galaxy_grpc_service.py）零 `x-forwarded`/`x-real-ip`/client-ip 消费——gRPC 面无 XFF 语义可偏差
- **HTTP Rewrite 本体**（setup.go:987-996）：XFF 恰一次追加（std 处方：Out 复制入站链+SetXForwarded 读 Out 既有链追加）、XFH 恒 In.Host（伪造不透传）、XFP 保留入站——与其钉测一致，未发现新偏差（判据消费侧问题已归 (a)）
- **426 归因/限流键本体**（get_client_ip / get_real_ip 右起取段）：经网关形态归因正确（探针 test_b 对照）——仅 (d) 两残余

---

## 登记汇总（台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`，worktree 分支 commit，不 push；登记前 grep 复核 479/480/482/483/484 全 0 命中，471 行尾登记为 481 行）

| 号 | 严重度建议 | 一句话 | 证据级 |
|----|-----------|--------|--------|
| V3-FIX-479 | P4 | 467 触发面收敛修正：共享演示 friend 行 + 每次访客登录重播 → 跨访客并发即可竞态；爆炸面=全体访客种子持久 failed | 运行级（sqlite 6 探针）+ 代码行级；竞态并发形 SUSPECTED（同表 451/457 真 PG 先例） |
| V3-FIX-480 | P3 | forwarded_chain_trusted 判据 `parts[-n]==peer` 与网关"追加 client IP"契约结构互斥——经网关恒 False（428 XFH 分支死路）；透传路径伪造链可过闸 | CONFIRMED（两侧仓库钉测互证 + sqlite 面探针） |
| V3-FIX-482 | P4 | community WS 代理 XFF/X-Real-IP 原样透传不追加，与 rate_limiting.py:17-18 契约声明相悖；当前引擎消费面为零 | CONFIRMED（代码行级） |
| V3-FIX-483 | P4 | 网关自有限流/审计面 gin ClientIP dev trust-all 返回 XFF 最左段/X-Real-IP，可轮转绕过 | CONFIRMED（网关源码+gin v1.9.1 库源码行级） |
| V3-FIX-484 | P4 | get_real_ip X-Real-IP 残留分支 + XFF 分段无 IP 形态校验（括号/带端口/映射形 fail-closed） | CONFIRMED（运行级探针） |

## 测试执行汇总（本次亲跑）

- `probe_streak.py`：6/6 绿（确定性 id 同源/两向交叉读单行收敛/双行三读面 MultipleResultsFound/顺序形态认领随机 id 行）——`probe_streak.log.txt`
- `probe_proxy.py`：5/5 绿（网关形态信任闸恒 False+坏链降级/归因对照正确/WS 透传形伪造归因+伪造链过闸/X-Real-IP 残留分支/IPv6 形态 fail-closed）——`probe_proxy.log.txt`
- PG 级并发不做（纪律）；现有 PG 复现件引用：`v3-output/WT737-FIRST451/`、`v3-output/WT742-INV457/`
