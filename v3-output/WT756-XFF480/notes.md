# WT756-XFF480 — V3-FIX-480 forwarded_chain_trusted 判据与网关追加契约对齐

- 会话：wt756（v3 航道实现 Agent）
- 日期：2026-09-27
- 分支：`agent/node-b/wt756/xff480`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt756-xff480`，base main@96275714）
- 修复 commit：`8a20a77c`（代码+测试）；台账 FIXED 登记 + 本 notes 随后一 commit
- 证据输入：v3-output/WT748-REVIEW/verdicts.md §焦点2(a) + probe_proxy.py/log、台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 480 行、Go 钉测 `backend/gateway/cmd/server/setup_proxy_forwarded_test.go`、428 守卫 `backend/tests/api/test_vocabulary_external_base_url.py`
- 纪律：主线仓只读；不碰 docker/运行栈；不 push

---

## 1. 病灶与判据新语义

**修前**（rate_limiting.py:79）：`forwarded_chain_trusted` 判据 = XFF 右起第 `TRUSTED_PROXY_COUNT` 段 == 引擎 TCP 对端（`parts[-n] == peer`）。与网关修后契约（`SetXForwarded` 追加**本跳 client IP**，钉测钉死）**结构互斥**：

- 经网关真实流量：XFF 末段=客户端真 IP ≠ 对端（网关自身 IP）→ 恒 False → 428 的 XFH 可信分支死路，缺省 env `_external_base_url` 恒降级内网 `http://sparkle_api:8000`（坏链+拓扑外泄症状依旧）；
- 引擎直连面：攻击者把自身对端地址写进 XFF 最右段即过闸（fail-open，探针 test_c 同形实证）；
- 428 Python 守卫建模「追加段==对端」拓扑，与 Go 钉测互斥——两守卫各自绿、守不住同一契约。

**修后判据**（与 nginx `real_ip` / uvicorn `--forwarded-allow-ips` / gin `SetTrustedProxies` 同型的引擎侧对位物）：

```
trusted ⇔ peer ∈ TRUSTED_PROXY_CIDRS（可信代理清单）
       且 TRUSTED_PROXY_COUNT > 0
       且 XFF 链长 ≥ N
```

- 新增 `_trusted_proxy_networks()`：解析 `TRUSTED_PROXY_CIDRS` env（逗号分隔 CIDR）；缺省 = 回环（127.0.0.0/8, ::1/128）+ 链路本地（169.254.0.0/16, fe80::/10）+ RFC1918 私网（10/8, 172.16/12, 192.168/16，覆盖 docker 默认地址池与 compose `sparkle_app` 内网）+ IPv6 ULA（fc00::/7）。非法段跳过；显式置空/全非法 = 空表 fail-closed。
- 新增 `_peer_is_trusted_proxy()`：`ipaddress` 解析对端；IPv4-mapped（`::ffff:a.b.c.d`，双栈 socket 真实形态）归一后比对，防止判据 false-negative 复辟死路；解析失败 fail-closed。

**取舍**：择台账方向一（对端∈清单+链长≥N），弃方向二（网关追加可验证自标识）——网关→引擎无既有自标识信道，引入（共享 secret 头等）即新信任面+协议变更；对端地址判定只用引擎既有信息，零协议变更。缺省「私网即可信」的边界：引擎端口在生产 compose 部署仅内网可达（`sparkle_app` internal），能直连引擎者本已在信任边界内；判据只闸 XFH/XFP 采信面（自害面低），需要更严隔离的部署以 `TRUSTED_PROXY_CIDRS` 收窄到网关精确地址（如 `172.20.0.5/32`），docstring 与测试均已钉此口径。

**三要求满足**：
1. 经网关流量可信分支可达（XFH=客户端原始 Host，Go 钉测契约）✓
2. 直连伪造链不过闸（外部对端 ∉ 清单，含「最右段==自身对端」修前 fail-open 形）✓
3. `TRUSTED_PROXY_COUNT=0`/非法值语义不变；缺省 N=1 与文档口径（「匹配本仓部署拓扑——网关追加真实 client IP」）一致——修前代码才是偏离文档方 ✓

## 2. 红 → 绿

**红**（修前基线跑新增/重模测试面，14 failed / 14 passed）：
- 新增 `tests/core/test_forwarded_chain_trusted.py` 18 用例，修前 10 红：网关形态（无注入/带注入）恒 False×2、直连伪造（最右==对端/全伪造/任意链）恒 True×3、N=2 长链恒 False、回环对端恒 False、收窄 CIDRS 两态、空 CIDRS fail-open、非法 CIDRS 段、IPv4-mapped false-negative；
- 重模 `tests/api/test_vocabulary_external_base_url.py` 10 用例（原「追加段==对端」互斥拓扑 → Go 钉测真实拓扑：对端=网关 172.20.0.5、追加段=client 203.0.113.7、外部直连对端=198.51.100.7），修前 4 红：真实网关形态 XFH 分支死路×2、直连伪造 XFH 被采信（fail-open 钉）、prefix 可信分支死路。

**绿**：判据替换后 28/28 绿；426 既有守卫（`test_rate_limit_real_ip.py` 7、`test_client_ip_attribution.py` 17）零改动零回退；`get_client_ip`/`get_real_ip` 右起解析语义不动（426 本体）。

## 3. 验证实录

- pytest 触达面（grep 全仓 import rate_limiting/_external_base_url 先行收录 9 文件）：**92 passed**（trusted 18 + vocabulary 10 + real_ip 7 + attribution 17 + auth_login_empty_credentials 8 + auth_refresh_rotation 10 + guest_access_ttl 11 + v3_fix286 3 + v3_fix55 2；命令 `SECRET_KEY=v DATABASE_URL=sqlite+aiosqlite:///:memory:`）。
- gateway `go test ./...`：**13 包零 FAIL**（426/428 Go 钉测 `setup_proxy_forwarded_test.go` 不回退）。worktree 缺 gitignored `gen/`，按单一入口 `buf generate --template buf.gen.yaml` 补齐（产物不入库）。
- mypy（1.20.2，backend pyproject 配置）：触达两文件 `app/core/rate_limiting.py`/`app/api/v1/vocabulary.py` 错误清单与基线**逐条 NO-DIFF**（56 errors in 50 files 恒等；唯一差异=既有 `rate_limiting.py add_exception_handler` 错行号 128→199 平移），零新增。
- ruff：check 4 触达文件 **All checks passed**；`ruff format --diff` 漂移 hunks **21=21** 与 main 既有集合结构零新增（`import ipaddress` 仅落入既有 docstring 空行 hunk 的上下文行；既有漂移不重排纪律）。
- 台账 verify：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` **零 FAIL**（修前基线 330 行过，登记后复跑过）。
- 491/492 预占：全仓 v3/ v3-output/ grep **0 命中空闲**；本批收口邻域复扫（rate_limiting 全文件、`_external_base_url` 消费面）**无新发现**，未占用。482/483/484 维持 OPEN（各自登记面，本批未动；`_trusted_proxy_count` docstring :17-18 websocket_proxy 追加声明属 482 修法面，保留）。

## 4. 变更文件

- `backend/app/core/rate_limiting.py`——判据替换 + `_DEFAULT_TRUSTED_PROXY_CIDRS`/`_trusted_proxy_networks()`/`_peer_is_trusted_proxy()` 新增 + docstring 重写（V3-FIX-480 语义与依据）
- `backend/tests/core/test_forwarded_chain_trusted.py`——新增 18 用例
- `backend/tests/api/test_vocabulary_external_base_url.py`——按真实拓扑重模 10 用例 + 模块 docstring 更新（480 重模依据）
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`——480 行 OPEN → FIXED@8a20a77c
- 本 notes
