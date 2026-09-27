# WT735-VERIFY3 — 猎缺第三轮（wt716 网关契约面）三条独立复核

- Agent: wt735 ｜ 分支: `agent/node-b/wt735/verify3`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt735-verify3`，基线 main@dfc19e63）
- 日期: 2026-09-27 ｜ 主线仓库只读，零产品代码改动 ｜ 接替 wt722（额度阵亡零产出）
- 方法: 三条全部不信原行号独立走查（行号有微小漂移均实测订正）+ worktree 等价小实验（Go 临时 _test.go 跑后删，`go vet` 复归零告警）+ 消费面全仓 grep 交叉验证。

## 三裁决（全 CONFIRMED，零 DOWNGRADED/REFUTED）

### 1. V3-FIX-426 (P2) XFF 首段伪造 — CONFIRMED
- **亲证**：Director 追加语义（setup.go:973-979 `prior+", "+clientIP`）与三消费方首段解析（行号订正：auth_audit_service.py:23、auth_session_service.py:37、research_consent.py:47，登记写 21-23/33-39/44-48 为函数区间，同指一处）。EI-09 右起先例实锤（rate_limiting.py:49-63 `parts[-n]`，docstring 自述「历史实现无条件信任 XFF 首段——客户端可伪造」＝同病已修先例）。
- **调用链补全**（超出原登记）：审计面 auth.py 11 处 + users.py 2 处 `schedule_log` → `AuthAuditLog.ip_address`；会话面 auth.py:177 `upsert_session` → `UserSession.ip_address`；同意存证面 research_consent.py:105 `revoke_consent_async(ip_address=…)` → research_mode.py:904-909 sha256 落 `grant/revoke_ip_hash`（合规存证哈希同样被投毒，危害口径加强）。NoRoute 公开 auth 代理面（setup.go:904-916 含 /auth/guest）+ Director 未剥客户端 XFF＝未登录方可投毒成立。
- **实验**（过真实 `setupProxy`，非复刻逻辑）：带 `X-Forwarded-For: 8.8.8.8`、`RemoteAddr=203.0.113.7:*` 的请求，后端实收 `"8.8.8.8, 203.0.113.7, 203.0.113.7"`——伪造段恒居首段。**新事实：真实 IP 出现两次**——除 Director 手工追加外，Go 标准库 ReverseProxy 默认行为（reverseproxy.go Director 字段文档 + ServeHTTP）对已存在 XFF 再追加一次 clientIP；两值相同，故右起第 N 段解析不失真，但 N≥2 扩信任层时双追加段会干扰段序语义。Python 侧等价解析验证：三处 `[0]` 解析均得 `8.8.8.8`，`get_real_ip` 右 1 段得 `203.0.113.7`。
- **危害一句话**：任意未登录请求自带 XFF 即可让爆破取证、新设备风控基线、合规同意存证（含 sha256 哈希）三类 IP 消费面记录攻击者选定值。
- **修法草案一句话**：三处 `_client_ip` 统一改 `get_real_ip` 同款右起第 TRUSTED_PROXY_COUNT 段（缺省 1 与拓扑匹配，已核）；修时顺带收拢 Director 手工追加与 stdlib 默认追加的冗余双写（改 Rewrite+SetXForwarded 或删手工段）。

### 2. V3-FIX-427 (P2) ChatHistoryPersister 关停丢消息 — CONFIRMED
- **亲证**：关停序八点全对上——main.go:89 bgCtx（注释明示关停 cancel）、:142 `bgCancel()` 先于全部 drain（Phase1-4 走满最长 shutdownTimeout 秒）、:105 `defer Stop()` 殿后于 main 返回、:103 Run(bgCtx)；persister :167-174 ctx.Done 分支以已取消 ctx 调 flushWithRetry、:278-279 批换出局部变量、:285-298 attempt≥1 backoff select 命中 ctx.Done → :290 `return ctx.Err()`、:312-315 requeue 挂同一取消 ctx、:416 `p.rdb.LPush(ctx,…)` 返回值整体丢弃。与 :176-178/:312 注释「failures are logged and the batch is re-queued」矛盾属实。stopCh 分支无幸免成立（bgCancel 必先行，且 ctx.Done 分支先返）。
- **实验**（坏 DSN pgxpool + miniredis，零真库依赖）双 PASS：
  - 路径①：预填 1 条批 → cancel → `flushWithRetry` 返回 `context canceled`，日志实录 `Write failed (attempt 1): failed to acquire connection: context canceled`，队列长度 0→0——**批未写库未 requeue**。
  - 路径②：`requeueMessages(取消ctx)` 调用后队列长度不变——LPush 静默失败。
- **量级判断**：「每次部署丢 ≤100 条」成立（PersisterBatchSize=100 + 5s flush 窗；仅内存在途批丢，队列驻留消息跨重启存活）。P2 定价恰当：SQL 注释 :28-31 自证引擎为主写者（RB-06），本队列系引擎漏写兜底，损失=引擎同样未落库的轮次。
- **修法草案一句话**：ctx.Done/stopCh 的最终 flush+requeue 改挂 `context.WithTimeout(context.WithoutCancel(bgCtx), 短超时)`（chatflow.go:117-124 `detachedPersistCtx` 仓内先例），`requeueMessages` 逐条查 LPush 错误并留指标。

### 3. V3-FIX-428 (P3) X-Forwarded-Host 恒内网主机 — CONFIRMED
- **亲证**：两半均实证——①Go 探针过真实 Director：不带 XFH 的请求后端收 XFH=覆写后 target host（:970 `req.Host = targetURL.Host` 先行 → :984-985 读 req.Host），客户端原始 Host 完全丢失（对照 stdlib `SetXForwarded()` 取 `In.Host` 即原始 Host，恰为正确修法原语）；②客户端自带 XFH 原样透传（后端实收 `evil.example.com`）反向可伪造。消费方 vocabulary.py:35-54 `_external_base_url` 与 :265 绝对 URL 拼接亲读成立。
- **默认活路径核实**：`DICTIONARY_PACKAGE_BASE_URL`/`GATEWAY_INTERNAL_URL` 缺省均 `""`（settings.py:1132/1136），deploy/ 与 docker-compose*.yml 全 grep 零设置——XFH fallback 是缺省路径，坏链+内网外泄非边角配置才触发。Python 全仓 XFH 无其他消费方（XFH 仅 vocabulary 一处）。
- **诚实注记（行题引用瑕疵，不影响本体）**：「与已修 301↔307 内网泄漏同类」的先例在现行台账（DYNAMIC_ISSUES.md 全 312 行）与 git log 均未定位到原登记；最近似 V3-FIX-141 是 307 尾斜杠移动端不跟随（已修 FIXED@5aaf2c1a），属不同病。同型性按结构判断成立（同为网关覆写 Host 致内网主机抵达客户端可见面），建议执行卡落笔时按本条证据独立表述，不引用未定位先例。
- **修法草案一句话**：Director 覆写 req.Host 前先保存原始 Host 设 XFH（或改 `Rewrite` func 走 `SetXForwarded()`，stdlib 取 In.Host 语义即客户端原始 Host）；engine 侧 `_external_base_url` 对 XFH 增加可信白名单或降级 `request.base_url`。

## 派发优先级建议

1. **V3-FIX-426 先行（P2，安全/合规取证面，修法小而封闭）**：三处 `_client_ip` 收拢单一出口，Go/Python 两端独立可测，回退零成本。
2. **V3-FIX-427 次之（P2，数据丢失面，修复含 ctx 生命周期改动需回归 drain 序）**：修法模式有仓内先例（detachedPersistCtx），单测判据 wt716 已给（预填批→cancel→断言队列长度与 DB 行），实验口径本卡已验证可直用。
3. **V3-FIX-428 收尾（P3，坏链+拓扑外泄，功能影响在词典包下载面）**：Go 侧 Director 顺序改动会触碰全部代理面，建议与 426 的 Director 收拢同卡或同批执行避免两次触碰同一函数；engine 侧 fallback 收紧独立小改。

## 新发现

**无立卡级新发现。V3-FIX-453/454 已 grep 亲证空闲**（全仓 v3/、v3-output/、git log --all 均无 446-454 占用；台账最高在册=wt731 世线 445）。本复核三条卫生级观察不立卡、留档：

1. **Director XFF 双追加**（并入 426 修法补注）：setup.go 手工追加 × stdlib ReverseProxy 默认追加叠加，当前同值无害、N≥2 扩展时干扰段序语义。
2. **rate_limiting.py:18 docstring 与代码不符**：docstring 称「websocket_proxy 在 X-Forwarded-For 尾部追加真实 client IP」，实测 websocket_proxy.go:681-682 仅原样透传客户端 XFF 不追加；当前 WS 面无 Python XFF 消费方（全仓 grep 恰四处：限流+426 三处），属文档失真非活体缺陷。
3. **websocket_proxy XFF/X-Real-IP 原样透传**：与 wt716 未成立清单 #7（X-User-ID 死面）同族的未来漂移陷阱，若后续 WS 端点误信即成仿冒洞；并入 428 代理头卫生修向即可。

## verify 自检

- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 三行（426/427/428）状态格各追加「复核@wt735：CONFIRMED+理由」；基线 312 行、重号 0、裸管 12（与基线 dfc19e63 完全一致，本次追加零新增行零新增裸管）。
- 基线注记：main 检出工作树台账现处 UU 未合并态（wt731 世线 V3-FIX-445 FIXED 注记，73e05585 非本基线祖先）——系主线在航会话中间态，与本卡无关，本卡基于 dfc19e63 干净基线。
- Go 实验：临时 _test.go 2+2 用例全 PASS 后已删，`go vet ./cmd/server/ ./internal/service/` 零告警复归；gen/ 按先例 cp -RL 不入库。
- 产出：本 notes `v3-output/WT735-VERIFY3/notes.md`；commit 于 `agent/node-b/wt735/verify3`；未 push。
