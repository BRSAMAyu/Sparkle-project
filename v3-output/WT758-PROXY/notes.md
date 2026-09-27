# WT758-PROXY — V3-FIX-482/483/484 proxy 族 P4 三连包收口

- 会话：wt758（v3 航道实现 Agent）
- 日期：2026-09-28
- 分支：`agent/node-b/wt758/proxy`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt758-proxy`，base main@878019fb，含 wt756 的 480 修后判据）
- 修复 commit：`457f2f56`（代码+测试+本 notes）；台账 FIXED 登记 457f2f56 随后一 commit
- 证据输入：v3-output/WT748-REVIEW/verdicts.md §焦点2 (b)(c)(d) + probe_proxy.py/log、台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 482/483/484 行
- 纪律：主线仓只读；不碰 docker/运行栈/.env；不 push；gen/ 以 `cp -RL` 自主线仓补齐（构建产物不入库）

---

## FIX-482 — community/personal WS 代理握手头与 HTTP Rewrite 契约对齐

**修前**（`internal/handler/websocket_proxy.go` `buildBackendWebSocketHeaders`）：入站 `X-Forwarded-For`/`X-Real-IP` 原样 Set 透传、不追加本跳 client IP——与 rate_limiting.py 契约声明（websocket_proxy 在 XFF 尾部追加真实 client IP）相悖，引擎侧右起第 N 段解析对 WS 握手请求会取到客户端任写的最右段（归因可投毒）。

**裁定**：择「追加」路线（台账方向一），弃「维持现状+改契约声明」——现状透传面是活着的伪造链投递信道，未来任何引擎侧 WS IP 消费方接入即复活；追加后契约声明成真，且与 HTTP 路径（setup.go Rewrite / stdlib `SetXForwarded`）单一世界。当前引擎 community WS 端点只读 authorization/sec-websocket-protocol，故本修零行为影响、纯契约收口。

**修后契约**（与 `setup_proxy_forwarded_test.go` 同一世界）：
- XFF：入站链保留 + 恰好追加一次 `SplitHostPort(RemoteAddr)` host（stdlib `SetXForwarded` 同型，含 slice 级 `strings.Join(prior, ", ")` 语义）；`RemoteAddr` 无端口形（SplitHostPort 失败）时**整头不转发**（stdlib 同款 fail-closed，宁缺勿假）；
- X-Real-IP：不透传——引擎 IP 归因单一出口 `get_client_ip` 不读该头（426 既定口径），透传只会制造第二归因信道。

**红 → 绿**：新增 `websocket_proxy_forwarded_test.go` 5 钉测 + 重钉 `websocket_proxy_test.go` 2 用例（原用例钉的是透传旧行为，按修后契约重钉，属修复本体非删断言）。修前实录 6 FAIL（追加缺位×3、X-Real-IP 透传、无端口形透传入站链、旧钉过时）→ 修后全绿，handler 包全量绿。

## FIX-483 — gin ClientIP() dev 缺省 trust-all 收紧

**修前**：`setupRouter` 仅 prod 缺 `TRUSTED_PROXIES` 时 Fatal，dev 不设任何信任面 → gin v1.9.1 缺省 `trustedProxies=0.0.0.0/0,::/0`（trust-all）+ `RemoteIPHeaders` 含 X-Real-IP → 直连 :8080 任写 XFF/X-Real-IP 即任控 `c.ClientIP()`（validateHeader 右起扫描 trust-all 下返回最左段），per-IP 限流键（rate_limit.go 四处）、五条 WS 升级入口共享预鉴权桶（ws_upgrade_rate_limit.go:45）、审计 client_ip（ws_auth.go:42、auth.go:119、stt_handler.go）全部可轮转/投毒。

**裁定**：择 `SetTrustedProxies(nil)`（dev 显式清单方向弃用）——若 dev 缺省清单含回环/私网段，则**所有真实 dev 拓扑的对端（127.0.0.1 联调、LAN 设备、docker 网段）本身都在清单内**，gin 会继续解析其携带的 XFF，伪造轮转原样存在，等于没修；nil（gin 文档语义=ClientIP() 恒取 TCP 对端）是唯一在直连拓扑真正闭合的口径，且一行收口全部消费面（限流键+审计字段），与引擎侧 426/484「宁共桶不伪造」同型。生产 Fatal 闸与显式 `TRUSTED_PROXIES` 路径逐字未动。

**迁移注记（本地联调影响评估）**：本地 nginx/caddy 反代 → gateway 的 dev 拓扑下，`ClientIP()` 退化为代理地址（限流键共享桶、审计记录代理 IP）——需要按真实客户端归因时**显式设 `TRUSTED_PROXIES`**（配置面既有，prod 同款）；直连 :8080 联调（compose 发布端口/本机 flutter run）零影响（对端即真实客户端）。dev 启动加 WARN 日志说明该口径。

**实现**：收口为 `applyTrustedProxies(r, cfg, logger)` 单一出口（先做行为保持的原样抽取，再改 dev 分支），`setupRouter` 调用之。

**红 → 绿**：新增 `setup_trusted_proxies_test.go`——`TestDevDefaultIgnoresSpoofedForwardedHeaders`（修前实录 FAIL：伪造 XFF 最左段 `8.8.8.8` 控制 ClientIP，期望 TCP 对端 `203.0.113.7`）+ `TestExplicitTrustedProxiesStillHonored`（显式清单路径钉住不回退，修前即绿）。gin 内部 `isUnsafeTrustedProxies` 为包私有不可从 main 断言，信任面收口以行为级测试钉住。

## FIX-484 — rate_limiting.py 右起解析族残余

**① X-Real-IP 残留分支删除**：`get_real_ip` 在 XFF 缺席时回退采信 `X-Real-IP`（直连 :8000 面客户端可选头 → 限流键可轮转）——删。修后 XFF 缺席/不可归因一律退回 TCP 对端，与 `get_client_ip`「不读 X-Real-IP」单一出口口径对齐。`_trusted_proxy_count` docstring 的契约声明同步（0=完全不信任 XFF；websocket_proxy 追加声明经 482 修后为真）。

**② XFF 分段 IP 形态校验（fail-closed）**：
- 新增 `_normalize_forwarded_segment()`：逐段 `ipaddress` 解析；容忍并归一三类真实代理形变——`[2001:db8::1]` 括号形、`203.0.113.7:8080`/`[2001:db8::1]:443` 带端口形、`::ffff:a.b.c.d` mapped 形（归裸 IPv4，与 `_peer_is_trusted_proxy` 同口径）；裸 IPv6 先整串解析（`2001:db8::1:40000` 本就是合法 IPv6，按地址收，协议级歧义在 docstring 记录）；`unknown`/截断形等一律 `None`。
- `_forwarded_for_parts()` 返回 `list[str | None]`；新增 `_right_nth_client()`：右起 N 段**窗口**内存在杂质段 → 返回 None（链尾不是代理按契约追加的 IP → fail-closed 退回对端/不可信）；归因取右起**第 N 段** `parts[-n]`。窗口左侧杂质属客户端注入区，不影响右起解析（426 既定语义）。
- `forwarded_chain_trusted` 在 480 判据（对端∈清单 + N>0 + 链长≥N）之上加同款形态闸：窗口含杂质 → XFH 等转发头不可信。

**红 → 绿**：新增 `tests/core/test_forwarded_segment_validation.py`（25 用例：归一矩阵 10 + 消费面 15）+ 重钉 `test_rate_limit_real_ip.py::test_x_real_ip_not_read_single_outlet_aligned`（原 `test_x_real_ip_trusted_only_behind_proxy` 钉的是残留分支，按修后契约重钉）。分两段实录：
1. 惰性加 `_normalize_forwarded_segment`（未接线）后跑 → **11 failed**（X-Real-IP 采信、括号/端口/mapped 原样串归因、杂质串归因、链长单判 True、N=1 X-Real-IP 钉）；
2. 接线后 3 failed（426 既有 N=2 多代理归因钉测抓出 `_right_nth_client` 初版误返最右段 `window[-1]` 而非右起第 N 段 `window[0]`——既有测试面反捉新代码缺陷，正是钉测价值）→ 修为 `window[0]` → 全绿 74。

**与 480 判据协同复核结论**：480 的「链长 ≥ N」在形态闸加入后语义为「右起 N 段窗口全为合法 IP 且窗口左侧杂质不计」——经网关真实流量（无注入/带注入）两形态全部保持可信，18 条 480 守卫零改动零回退。

## 验证汇总（本机亲跑）

| 面 | 结果 |
|----|------|
| pytest 触达面（rate_limiting 四守卫 + vocabulary 守卫 + auth/refresh/guest_seed 邻域，10 文件） | **117 passed** |
| gateway `go test ./...` | **13 包 ok 零 FAIL**（426/428 钉测、480 时代测试、461/469/481 邻域不回退） |
| 触达包 `-race`（cmd/server、internal/handler） | ok（ld LC_DYSYMTAB 为 macOS 工具链噪声，同前记） |
| mypy 触达 `app/core/rate_limiting.py` | 与基线逐条 NO-DIFF：唯一既有 `add_exception_handler` arg-type（行号 199→264 平移，因上方加行），零新增 |
| ruff check（触达 3 文件） | 过 |
| ruff format 漂移 | rate_limiting.py 恒 2 hunks（既有漂移不重排）；新/改测试文件 format-clean |
| gofmt / goimports（internal/handler、cmd/server） | 净（新测试文件曾脏、已 `goimports -w` 收敛） |
| golangci-lint（internal/handler/...、cmd/server/...） | 过（exit 0） |
| 491/492 预占复核 | grep v3/ v3-output/ 全 0 命中空闲；本轮邻域复扫（gateway 其余 XFF 面、引擎 X-Real-IP 读面、applyTrustedProxies 消费面）无新发现，**未占用** |

## 残差/边界（如实记录）

- 482：WS 握手头未转发 XFH/XFP（HTTP Rewrite 有）——引擎 WS 端点零消费面，超出 482 登记面不扩；未来接入再议。
- 482：`httptest` 之外真实 `RemoteAddr` 恒带端口，无端口形分支为防御性 fail-closed，运行级不可达。
- 483：`SetTrustedProxies(nil)` 后 dev 审计 client_ip 记 TCP 对端——直连拓扑即真实值；反代拓扑见迁移注记（显式 TRUSTED_PROXIES）。
- 483：生产缺 TRUSTED_PROXIES 的 Fatal 路径维持原样（zap Fatal 即 os.Exit，测试进程级不可达，与修前一致不测）。
- 484：裸 `v6:port` 无括号形协议级歧义（`2001:db8::1:40000` 合法 IPv6）——按地址收不剥端口，归因串为合法 IP 无安全面。
- 引擎直连面（对端 ∉ 可信清单）XFF 右起第 N 段仍被 `get_client_ip` 采信（426 既定链长启发式，未校验对端可信）——480/484 未改该口径，留档不扩面。

## 产出

- 代码：`backend/gateway/internal/handler/websocket_proxy.go`、`backend/gateway/cmd/server/setup.go`
- 测试：`backend/gateway/internal/handler/websocket_proxy_forwarded_test.go`（新）、`websocket_proxy_test.go`（重钉 2）、`backend/gateway/cmd/server/setup_trusted_proxies_test.go`（新）、`backend/tests/core/test_forwarded_segment_validation.py`（新）、`backend/tests/core/test_rate_limit_real_ip.py`（重钉 1）
- 文档：`backend/app/core/rate_limiting.py` docstring 契约声明（482 修后 websocket_proxy 声明为真；X-Real-IP 残留声明删除）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` 482/483/484 行 OPEN → FIXED@457f2f56（随台账 commit 登记）
