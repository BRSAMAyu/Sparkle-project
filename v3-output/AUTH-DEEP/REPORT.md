# AUTH-DEEP — auth/session 域系统深审报告

> 2026-09-22 ｜ Worker: wt229-auth-deep ｜ 只读诊断，零代码改动（交付物仅本报告）
> 背景：wt220(d0cbb785) 修 Layer-1（refresh 端点 revoke_session 签名错 TypeError 在 blacklist 之后=毒化窗口）；主会话热修 8f478904 修 Layer-2（轮换复用 sid + decode 自检撞残留 marker 必 401）。两层共同点：单测 mock 掩盖、真环境才炸。本报告对 auth/session 域做第三层体检。

**结论速览**：同型病还有 1 处必炸（P0，users.py:295，与 Layer-1 完全同构）、4 处 P1 边界窗口/语义缺陷、若干 P2 卫生项。移动端三单飞口位置确认（其一不是单飞）。单测黑洞集中在「吊销入口端点」（logout / reset / change-password 全部 0 用例）。

---

## A. 引擎侧（backend/app/api/v1/auth.py + core/security.py + services/auth_session_service.py + api/v1/users.py）

### A-1 同型扫描：吊销写入/清除不对称、签发点自检

#### 【P0】AUTH-A1：change_password 调 `revoke_all_sessions_for_user` 签名错 — 与 Layer-1 同构，端点必 500 且改密不吊销

- 证据：`backend/app/api/v1/users.py:295`
  ```python
  await auth_session_service.revoke_all_sessions_for_user(str(current_user.id))
  ```
  而签名（`backend/app/services/auth_session_service.py:288-294`）为
  `(self, db: AsyncSession, *, user_id: str, ttl_seconds: int)` —— 位置参数填进 `db`，`user_id`/`ttl_seconds` 两个 keyword-only 参数缺失 → **TypeError → 500**。无 try/except 保护（对照同文件 set_password `users.py:318-324`、delete_account `users.py:585-589` 均为正确写法——典型 copy-paste 漏改）。
- 毒化窗口：`users.py:292-294` 密码已改并 **commit 成功**，随后才炸。净效果：
  1. 用户看到 500（接口 100% 不可用）；
  2. `token_revoked_before` 水位未设、Redis watermark 未写、所有 session 未吊销 → **改密后旧 token 全部继续有效至自然过期**。这正是该端点唯一的安全职责，恰好没生效。
- 单测盲区佐证：`grep -rln "change_password|/me/password|revoke_all_sessions_for_user" backend/tests` → **0 命中**。
- 修复（最小，1 行）：`await auth_session_service.revoke_all_sessions_for_user(db, user_id=str(current_user.id), ttl_seconds=SESSION_TTL_SECONDS)`（`SESSION_TTL_SECONDS` 已在 users.py:50 定义）。
- **裁决：立即修**。

#### 【P1】AUTH-A2：logout access-token 路径黑名单写错命名空间 + exp 被当时长 —— jti 黑名单对多数校验面不可见

- 两套黑名单命名空间并存：
  - `token_blacklist:{jti}` — 写：`core/security.py:22,332`（`blacklist_token`，TTL=exp−now）；读：`decode_token`（security.py:164,204）**和 Go 网关**（`backend/gateway/internal/middleware/auth.go:576`）。
  - `token:blacklist:{jti}` — 写：`core/token_revocation.py:19,34-36`；读：**仅** `api/deps.py:37,98`。
- 证据：logout 的 access 分支 `backend/app/api/v1/auth.py:712` 调 `token_revocation_service.blacklist_token(payload.get("jti"), payload.get("exp"))` —— 写进 `token:blacklist:`。于是：
  1. **覆盖缺口**：`api/middleware.py:72`（幂等中间件）、`api/grpc_auth.py:74`（gRPC 鉴权）、`api/v1/community.py:1740,3057`（SSE）、`api/v1/stt.py:86`、以及 Go 网关全部只经过 `decode_token`（查 `token_blacklist:`）——被 logout 拉黑的 access jti 对它们**不可见**。实际兜底是同分支里 `revoke_session_by_id` 写的 `session_revoked:{sid}` 标记（网关 auth.go:636 也查）；但 sid 缺失、或 DB 会话行不存在时 `revoke_session_by_id` 静默返回 None（auth_session_service.py:264-266），token 活到 exp。
  2. **TTL 语义错**：`token_revocation.py:22` 第二参是 `expires_in`（秒数时长），auth.py:712 传入的是 `exp`（绝对 epoch，如 1.758e9）→ `ttl = expires_in or 3600` ≈ **55 年**。每个 logout 都给 Redis 塞一个准永久 key（内存卫生问题）。
- 修复（最小）：
  1. auth.py:712 改调 `security.blacklist_token`（import 已有同族函数，1 行）；
  2. 立卡：`token_revocation_service` 退役收敛——其 `revoke_refresh_token`/`revoke_all_user_tokens` 全仓无业务调用方（grep 证实），deps.py 两处读取点切到 `security.is_token_revoked` 后整个类可删，消除双命名空间。
- **裁决：1 立即修；2 立卡排期（P1 收敛）**。

#### 【P1】AUTH-A3：watermark 的 naive→epoch 转换用 `.timestamp()` —— 非 UTC 主机上水位偏移整时区

- 证据链：
  - 写入侧 `core/security.py:293`：`ts = int(revoked_before.timestamp())`，而三个调用方（auth.py:798 reset-password、users.py:296/323/587 change/set-password/delete-account）传的都是 **naive UTC** datetime（`datetime.now(UTC).replace(tzinfo=None)`，naive `.timestamp()` 按**本地时区**解释）。
  - 读取侧 DB fallback `security.py:244`：`int(user.token_revoked_before.timestamp())` 同病。
  - 对比面：iat 是真 UTC epoch（python-jose `jwt.encode` 对 iat/exp/nbf 做 `timegm(utctimetuple())`）。
- 后果：本机 TZ=+0800（已实测 `date +%z`）→ 水位 = 真实 epoch − 28800s → **改密/重置前 8 小时内签发的 token `iat >= revoked_before` 全部漏网**，旧 refresh token 在密码重置后仍可轮换。Docker 容器默认 UTC 故 compose 部署暂时无症状；原生跑（本机 `make grpc-server`）必现。另注：`token_revocation.py:96` 的 `revoke_all_user_tokens` 传 aware datetime（结果正确）——同一语义两种传参，证明该边界无约定。
- 修复（最小）：security.py 内统一 `calendar.timegm(revoked_before.utctimetuple())`（或 `int(revoked_before.replace(tzinfo=UTC).timestamp())`），建议封装进 `core/time_utils.py`（该文件已自述统一全仓时间语义，尚缺 naive→epoch helper）。
- 附带边界（P2）：`security.py:176` `iat_ts < revoked_before` 为严格小于，iat 与水位同秒的 token 幸存——修复 A3 时顺手改 `<=` 或水位减 1s 余量。
- **裁决：立即修（一个 helper 两处调用）**。

#### 【P1】AUTH-A4：refresh 轮换毒化窗口仍残留 —— blacklist 仍在签发之前

- 现状顺序（`auth.py:645-671`）：`revoke_session_by_id`（写 Redis marker）→ `blacklist_token(old jti)`（:657，写 Redis）→ `_issue_auth_tokens`（:665，内部 upsert 清 marker + commit）。
- wt220 修复只保证了「revoke 失败不 blacklist」（有测试钉住，test_auth_refresh_rotation.py:135-181）；但 **blacklist → 签发之间**的失败无保护：upsert 阶段任何异常（DB 抖动、`cache_service.delete` 抛错——cache.py:163-167 的 delete 无容错）→ 端点 401、get_db 回滚 DB，而 **Redis 已落两个标记（old jti 黑名单 + session_revoked）**。客户端重试 decode 直接 "Token revoked" → 强登出。形态与 Layer-1/2 同类，只是触发面从「必现」缩到「基础设施抖动」。
- 叠加：`security.blacklist_token` 重试 3 次耗尽后**吞错返回**（security.py:334-344，H4 修复的副作用）——黑名单写失败静默放行，方向安全但无告警面（P2 登记）。
- 修复（最小，~5 行）：把 `blacklist_token(old jti)` 移到 `_issue_auth_tokens` 成功返回**之后**作为最后一步写 Redis（失败仅 log，fail-open 的复用窗口由 refresh rate limit 10/15min 兜底）。顺序换位后「任何失败都不消耗已呈递的 token」成为不变量。注意同步更新 test_auth_refresh_rotation.py:50-55 的顺序 pin。
- **裁决：立即修**。

#### 【P2】AUTH-A5：logout vs refresh 竞态 —— refresh 的 upsert 复活已登出会话

- logout（:691-699）与并发 refresh 都过 decode 后：refresh 的 `upsert_session`（auth_session_service.py:87-108）复位 `is_active=True/revoked_at=None` 并**删除 session_revoked marker** → logout 的会话吊销被静默撤销，且产出新 token 对。危害限同用户自有设备（低危），但「logout 后会话必须死」的不变量不成立。
- 修复：A4 的 blacklist 后置 + 输者检测（签发前复查 `is_token_revoked(old jti)`，见 A-4 建议）可关闭主要窗口；彻底关闭需 rotation intent 标记，**立卡排期**。
- 同源小窗口（P2）：轮换的 revoke→upsert 之间（ms 级，含两次 Redis RTT），同 sid 在途 access 请求 decode 撞 marker → 偶发 401，自愈。8f478904 的 `check_session_revocation` 参数只豁免了签发点自身，未豁免并发在途请求——已知代价，接受即可，建议注释登记。

#### 【P2】AUTH-A6：并发双 refresh 无 reuse-detection / token-family 撤销

- 双 tab 同时 refresh：两者都在对方 blacklist 前通过 decode → 都成功，同 sid 产生两份有效 refresh jti，DB `refresh_token_jti` 只剩最后写者；若一方 decode 落在另一方 blacklist 之后 → 401 → 移动端 `clearTokens` 强登出（结局随机，取决于时序）。JTI GET/SET 无原子性（security.py:204-207 vs 332）。安全上非洞（同用户同会话），UX 上是双 tab 随机登出源。
- **裁决：立卡排期**（设计决策：sid 级 rotation version 或 family-jti 链式撤销，需与网关侧 local blacklist 缓存联动评估）。

#### 【P2】AUTH-A7：guest access token 刷新后 7 天 → 30 分钟

- `auth.py:976` guest 签发 `access_expires_delta=timedelta(days=7)`；refresh（:665）不透传该 delta，走默认 30min。访客首次刷新后 access 缩水 99.4%，401→refresh 循环压力徒增。`is_guest` claim 已透传（:664），顺手带一个 `access_ttl` claim 即可。
- **裁决：立卡排期**。

#### 设计确认（落档，无缺陷）

- **轮换后旧 access token 仍有效 30 分钟是 intended**：access 无状态、轮换只吊销 refresh jti，网关靠 Redis 三查（jti/水位/session）兜底且 token TTL 短。logout 是例外（要杀 access），其有效性当前依赖 sid 墙而非 jti 墙（见 A2）。

### A-2 跨存储一致性：三处状态的全部写入/清除点

| 状态 | 写入点 | 清除/复位点 | TTL | 不对称风险 |
|---|---|---|---|---|
| Redis `session_revoked:{sid}` | `auth_session_service.py:250`（revoke_session，revoke_by_id/revoke_all_other/revoke_all_for_user 共用） | `auth_session_service.py:108`（仅 upsert_session） | 7d（SESSION_TTL_SECONDS） | upsert 的 `cache_service.delete` 抛错 → 端点 401、DB 回滚但 Redis marker 留存（→A4）；**写 Redis 在 db.flush 之前**（:250→:251），事务回滚时 marker 已出去（方向安全：多杀不多放） |
| Redis `token_blacklist:{jti}` | `security.py:332`（refresh 轮换 :657、logout refresh 分支 :692） | 无（靠 TTL=exp−now） | ≤ token 余寿 | 重试耗尽吞错（:334-344）；exp≤0 跳过（:323-324，已过期 token 不必拉黑，正确） |
| Redis `token:blacklist:{jti}` | `token_revocation.py:36`（仅 logout access 分支 auth.py:712） | 无 | **≈55 年（exp 误作时长）** | 命名空间 + TTL 双错（→A2） |
| Redis `user_revoked_before:{uid}` | `security.py:300`（reset-password :798、users 三入口、`token_revocation.py:96`） | 无 | 7d | naive TZ 偏移（→A3）；**网关无 DB fallback**（auth.go:606 只读 Redis），7d 后网关遗忘水位——因 access 寿命 30min ≪ 7d 暂不构成窗口，但「marker TTL(7d) > access TTL(30min)」是网关吊销有效性的**承重不变量**，无测试钉住、无配置校验（若有人把 ACCESS_TOKEN_EXPIRE_MINUTES 调到 >7 天即静默失效） |
| DB `UserSession.is_active/revoked_at` | revoke_*（flush 随 get_db commit） | upsert_session conflict-update 复位（:87-108）；touch_session **不复位**（:114-181，A1 修复保持 ✔） | 永久 | 「upsert 复位但 marker 残留」：复位与 marker 清除同函数但顺序为 DB 写→Redis 删→flush，Redis 删失败即错位（→A4）；无清理任务 → 行只增不减（live 探针：`SELECT count(*) FROM user_sessions` = 500，12 行 revoked，P2 卫生，建议加过期清理 Celery 任务） |
| DB `users.token_revoked_before` | reset/change/set-password/delete-account | 无 | 永久 | 有 Redis→DB fallback（security.py:236-251）✔；naive TZ 转换病（→A3） |

**专项发现【P1】cache_service 的进程内兜底污染安全存储**（`core/cache.py:119-129,138-151`）：`init_redis` 失败时 `self.redis=None`，此后黑名单/水位/吊销标记的读写全部落到**进程内 dict**——多 worker/多实例下互不可见（实例 A 拉黑的 token 在实例 B 有效）；且因为本地路径不抛异常，`is_token_revoked` 的 prod fail-closed（security.py:209-219）与 `is_token_blacklisted` 的 fail-closed（token_revocation.py:57-60）**都不会触发**，静默降级为 fail-open。运行期 Redis 断连（init 成功后）则相反：读写直接抛错 → 触发 fail-closed。两种降级行为不一致且不可观测。
最小改法：`init_redis` 失败在 prod 直接 raise（fail-fast 启动）；或对 `token_blacklist/session_revoked/user_revoked_before` 三个前缀禁用本地兜底并显式抛错。**裁决：立卡排期（P1）**。

### A-3 异常兜底吞噬：refresh 端点全 401 化

- 证据：`auth.py:672-674` `except Exception → 401「刷新令牌无效」`。DB down（`db.get` 抛 OperationalError）、Redis down（叠加 `is_token_revoked` prod fail-closed：**Redis 抖动=所有 token 判为 revoked**）、限流器异常，一律 401，与真无效 token 不可区分。
- 跨层放大（与 B 节联动）：后端 401 化 × 移动端「refresh 收到任何 DioException → `clearTokens()`」（auth_repository.dart:236-244）= **一次基础设施抖动 → 全舰队强制重登**。这正是今日 COMMUNITY-401 事故的完整机制链，wt220 只修了「必现」环节，「抖动→401→清 token」的放大链仍在。
- 分级方案（最小，~10 行）：refresh 的 except 白名单化——`JWTError`、已有 `HTTPException` 原样抛；`sqlalchemy.exc.OperationalError`、`redis.exceptions.(ConnectionError|TimeoutError)`、`asyncio.TimeoutError` → `HTTPException(503, detail=…retryable…)`。移动端配合见 B-3。`deps.get_current_user_id:45-50` 的全 401 匹配套子（P2，401 语义上尚可接受但建议同法分级）。
- **裁决：立即修（与 B-3 同一张卡，两端一起改才有意义）**。

### A-4 并发竞态

- 双 refresh 竞态：见 A6。输者检测（签发前复查 old jti 是否已被拉黑）可把「都成功」收敛为「恰一成功」，是 single-use 语义的最低成本实现（~3 行，随 A4 顺序调整一起落）。
- 旧 access 轮换后仍有效：intended（见 A-1 末）。
- logout 期间在途 refresh：见 A5。
- `touch_session` freshness-skip（auth_session_service.py:138-148）的读-判-写非原子：并发 touch 可能双双跳过或双写，后果仅 last_active_at 精度，无害，不立项。

---

## B. 移动端（mobile/lib/core/network/ + auth 相关）

### B-1 三个 refresh 单飞口精确位置

| # | 文件:行 | 机制 | 单飞真实性 |
|---|---|---|---|
| 1 | `mobile/lib/core/network/api_interceptor.dart:66`（声明），:170-215（等待/启动/清理） | `Completer<String>? _refreshCompleter` | 真·单飞：并发 401 排队等同一 future |
| 2 | `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1424`（声明），:2182-2312（处理块） | 独立的 `Completer<String>? _refreshCompleter` | 真·单飞，但与 #1 互不感知 |
| 3 | `mobile/lib/features/community/presentation/providers/community_provider.dart:1080`（`bool _isRefreshingToken`），:1156-1196（处理块） | 布尔旗标 | **不是单飞**：并发调用者在 :1157 直接 `return`——不等待、不重试、请求悄悄丢 |

`grep -rn "refreshToken()" mobile/lib` 全量证实调用点恰为三处：api_interceptor.dart:188、websocket_chat_service_v2.dart:2254、community_provider.dart:1179，其余全走 #1。

**收敛方案**：新建 `TokenRefreshCoordinator`（Riverpod provider 单例）：内部一个 Completer + try/finally 清理，对外 `Future<TokenResponse> refreshOnce()`。三处调用点全部改为 `ref.read(tokenRefreshCoordinatorProvider).refreshOnce()`，删除三份本地 Completer/旗标与重复的「失败→logout」分支（登出决策也统一进 coordinator 的失败回调，带 context 参数区分 HTTP/WS/Community 的善后差异）。附带消灭 #3 的丢请求问题。

### B-2 wt220 修复面与另外两处行为差异矩阵

| 维度 | #1 api_interceptor（wt220 修） | #2 ws_chat_v2 | #3 community |
|---|---|---|---|
| 触发 | HTTP 401（onError） | WS 401 帧 | WS 401 错误流 |
| 无 session 早退 | ✔ :153-157（不制造登出循环） | ✘ 直接进刷新（refreshToken 内部再拦） | ✘ 同左 |
| 并发 401 | 排队等 future，成功后带新 token 重放请求 | 排队等 future，**等完直接 return**（不重放，靠重连） | **静默丢弃** |
| 刷新失败善后 | `logout(keepDemoMode)` + 原样放行 401 | `logout(keepDemoMode)` + 置 failed/禁重连 + pending 消息定向失败提示 | `logout()`（**不保 demo 模式**）+ 置 maxRetry |
| 重试上限 | 无上限（每轮新 Completer，靠 rate limit 兜底） | `_max401Retries = 1`（:1426，成功后复位） | `_max401Retries = 1`（:1082） |
| 401 判定 | 精确 status==401 | 字符串匹配（`' 401 '`/`unauthorized`…，:2165-2178） | 同款字符串匹配（:1122-1133） |
| token 持久化 | 三者同源：`AuthRepository.refreshToken()` 内 `saveTokens`（双 key：新 key + legacy key，:639-653；clearTokens 双删 :657-663 ✔） | 同 | 同 |

**登记修正**：wt220 卡面「失败不清 token」在**仓库层不成立**——`AuthRepository.refreshToken()`（auth_repository.dart:212-247）对任何异常 `await clearTokens()` 后才抛。拦截器层的 `logout(keepDemoMode:)` 只是二次善后。「不清」仅指「无 refresh token 时不再触发 logout 循环」这一早退分支。

### B-3 401 重试风暴边界

- #1 重放经 `_getRetryDio()`（无 AuthInterceptor，:73-94）→ 无递归；一轮 401 只刷一次。
- 真正的风暴源在**失败侧**：三处失败都会清 token + 触发登出 UI，没有任何退避/分级。叠加后端 A-3 的全 401 化：Redis/DB 抖动 N 秒 = 在线用户全部被登出，重登洪峰反向打登录/refresh 接口（prod 限流 5-10/15min/IP 会把重登也拒掉，雪上加霜）。
- 修复（最小）：`AuthRepository.refreshToken()` 仅对 `status 400/401` 清 token；408/5xx/DioExceptionType.connectionError 等保留 token 并抛「可重试」类型失败。三处善后据此区分：可重试失败 → 不 logout、走各自连接级退避（#2/#3 已有重连退避；#1 原请求直接以 5xx 放行给业务层）。**裁决：立即修，与后端 A-3 同卡**。三单飞口收敛（B-1）**立卡排期**。

---

## C. 单测盲区结构化

### C-1 auth 域 mock 边界地图

| 测试文件 | 覆盖 | mock 了什么 | 边界外暴露 |
|---|---|---|---|
| `tests/unit/test_auth_refresh_rotation.py` | wt220/Layer-2 回归（6 用例） | `decode_token`（fake 返回裸 dict，绕过真实 blacklist/水位/session 三查）、`revoke_session_by_id`、`blacklist_token`、`upsert_session` 全 monkeypatch；`_FakeDB` 仅 `.get`；末条用例再 mock 掉 `is_session_revoked/is_token_revoked/get_user_revoked_before` | **cache_service 零触达**、真 JWT→decode 链路零触达；两个用例是源码字符串顺序 pin（防「特定行被删」，不防行为） |
| `tests/unit/test_auth_session_touch.py` | touch 不复活会话（A1） | `cache_service` → `_FakeCache`（手写 dict 仿品，无 TTL/无 Redis 语义） | marker 的 TTL 过期语义、SET/DEL 时序 |
| `tests/api/test_auth_login_empty_credentials.py` | 登录参数校验（7 用例） | 无状态校验 | — |
| `tests/integration/test_auth_flow_integration.py` | 真 JWT/WS/gRPC 流 | 不 mock，但**依赖 make dev-all 全家桶，基础设施缺席即 skip** → CI 实际盲跑 | 一旦跑起来是唯一真链路 |
| **覆盖黑洞** | logout、reset-password、change-password、set-password、delete-account、users.py 全部会话管理端点：**0 用例**（grep 证实） | — | 两个已实锤缺陷（users.py:295、logout 命名空间）恰在黑洞正中 |

**盲区规律**：全部 auth 单测止步于 `cache_service`（Redis 的 TTL/时序/跨实例语义）与真 DB。Layer-2（marker 残留自检）死在 cache mock；Layer-1（签名错 TypeError）死在 service mock——mock 桩替身永远签名正确。移动端 `test/core/network/api_interceptor_community401_regression_test.dart` 同理用 SharedPreferences mock + 桩 repo，未钉「refresh 5xx 不得清 token」（当前行为也确实不满足，见 B-3）。

### C-2 最小真组合测试方案（按性价比排序）

1. **fakeredis 带 TTL 语义注入 cache_service**（防 Layer-2 类）：conftest 加 fixture，`cache_service.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)`（TTL/EXPIRE 语义为真），半天工作量。可钉：marker 先写后删时序、blacklist TTL、watermark 到期、以及「Redis 写成功但后续失败」的 A4 场景。单测速度保留。
2. **真链路冒烟（防 Layer-1 类）**：testcontainers-python（postgres+redis）或直接复用 `make dev-up`，标 `@pytest.mark.integration` 单独 CI job（不 skip 而是失败）。只保三条链：refresh 轮换全链（真签发→真 decode→真 DB upsert/revoke→真 Redis）、logout 全链、change-password 全链。规则：**会话域写路径新增/修改必须配一条真链路测试**。
3. **签名契约 pin**（最便宜的 Layer-1 防疫）：`test_service_signatures.py` 用 `inspect.signature` pin 住 `AuthSessionService` 全部公开方法签名，任何调用点漂移在 import 期即红；或直接给 users.py change-password 补一条 httpx ASGITransport 测试（真 service + fakeredis，不 mock service 层）——P0 修复时顺手带上。
4. 移动端：在 community401 回归测试补「refresh 返回 503 → token 保留 → 不调 logout」断言（与 B-3 修复同 PR）。

---

## 裁决清单

### 立即修（本周，均为小改）
| # | 项 | 位置 | 量级 |
|---|---|---|---|
| 1 | P0：change_password 签名错 | users.py:295 | 1 行 |
| 2 | P1：logout access 黑名单换 `security.blacklist_token` | auth.py:712 | 1 行 |
| 3 | P1：watermark naive→epoch helper（timegm） | security.py:244,293（+time_utils） | ~6 行 |
| 4 | P1：refresh 内 blacklist 后置到签发成功后（+顺序 pin 测试同步） | auth.py:657→签发后 | ~5 行 |
| 5 | P1：refresh/refreshToken 分级 503 + 移动端 5xx 不清 token（同卡两端） | auth.py:672-674；auth_repository.dart:236-244 | ~20 行 |
| 6 | P0 配套：缺陷 1 的真链路回归测试（方案 C-2.3） | tests/ | 1 个测试 |

### 立卡排期
| # | 项 | 级别 |
|---|---|---|
| 1 | TokenRefreshCoordinator 三单飞口收敛（B-1 方案） | P1 |
| 2 | `token_revocation_service` 退役、黑名单双命名空间收敛（A-2.2） | P1 |
| 3 | cache_service 安全键禁本地 dict 兜底 / prod 启动 fail-fast（A-2 专项） | P1 |
| 4 | 并发 refresh 输者检测 + reuse-detection/family 撤销（A4/A6） | P2 |
| 5 | logout vs refresh 复活窗口的 rotation intent（A5） | P2 |
| 6 | guest access TTL 轮换保持（A7）；watermark 严格不等号边界 | P2 |
| 7 | user_sessions 过期清理任务；`blacklist_token` 吞错加告警面；`schedule_log` 的 create_task 无强引用可被 GC（auth_audit_service.py:62，对照 deps.py:76-82 有守护——审计日志可能静默丢失） | P2 |
| 8 | 测试基建：fakeredis fixture + integration CI job + 签名契约 pin（C-2） | P1 |
| 9 | 承重不变量防护：REFRESH 天数 > ACCESS 分钟数的配置校验 + 一条钉住测试（A-2 表末行） | P2 |

---

## 收工核查

- [x] 只读声明：本次任务零代码改动；唯一产物为本报告（v3-output/AUTH-DEEP/REPORT.md）
- [x] git status 干净（除 v3-output/ 新增交付物；开工时工作树已验证 clean）
- [x] 只读探针：`redis-cli --scan`（无写）、`docker exec sparkle_db psql -c "SELECT count(...)"`（纯 SELECT）；未跑任何写库脚本
- [x] /tmp 无残留产物；未启动模拟器/浏览器实例
- [x] 主仓与其它 worktree 全程未写
