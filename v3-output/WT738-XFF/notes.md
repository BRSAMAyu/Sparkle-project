# WT738-XFF — V3-FIX-426（P2）+ V3-FIX-428（P3）批量修复 notes

- Agent: wt738 ｜ 分支: `agent/node-b/wt738/xff`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt738-xff`，基线 main@fc8fb47b）
- 日期: 2026-09-27 ｜ 主线仓库只读，gen/（backend/app/gen、backend/gateway/gen）按先例 cp -RL 不入库
- 两卡同触网关 Director，按复核@wt735 同批执行；台账两行各置 FIXED@f72934f2（engine 半 028f6ff0）

## 修什么

### V3-FIX-426（P2）XFF 首段伪造 → 三消费方右起第 N 段 + Director 双追加收拢

- **engine 半**：`app/core/rate_limiting.py` 新增 `get_client_ip(request)`（IP 归因单一出口：右起第 `TRUSTED_PROXY_COUNT` 段，链条短于 N/N=0 退 TCP 对端；与 `get_real_ip` 差异=不带路径后缀、不读 `X-Real-IP`——历史归因面未采信该头，不引入新信任面）。三消费方 `_client_ip`（行号执行前亲证：`auth_audit_service.py:23`、`auth_session_service.py:37`、`research_consent.py:47`，第三处为 `split(",", 1)[0]` 变体）收拢委托，伪造 XFF 首段不再落入审计取证/设备会话基线/合规同意存证（含 `grant/revoke_ip_hash` 哈希投毒面）。`get_real_ip` 改用共享 `_forwarded_for_parts` 规范化，逐分支语义等价（限流面零变化）。
- **gateway 半（426-连带 双追加收拢）**：`setup.go` Director → Rewrite 单一出口。Rewrite 模式下 stdlib 先剥入站 Forwarded/X-Forwarded-\*，随后 `SetURL` + **入站 XFF 链复制回 Out** + `SetXForwarded()`——恰追加一次本跳 client IP，右起解析既定语义不变（N≥2 扩信任层不再被双追加段干扰）。

### V3-FIX-428（P3）XFH 恒内网主机 → XFH 取原始 Host + engine 可信判断

- **gateway 半**：Rewrite 模式 `SetXForwarded()` 无条件 XFH=In.Host（客户端原始 Host）——旧 Director `req.Host` 先覆写后兜底的顺序缺陷闭合；客户端自带伪造 XFH 随 Rewrite 剥头不再透传（旧行为为可伪造面）。XFP 保留入站值（上游 TLS 终止方写入的 https 不回退），缺省 http 与原 Director 一致。
- **engine 半**：`vocabulary._external_base_url` 对 XFH/XFP 增加 `rate_limiting.forwarded_chain_trusted` 可信判断（XFF 右起第 N 段==TCP 对端，EI-09 同源判据；N=0/无 XFF/短链/最右段≠对端均不可信），不可信降级 `request.base_url`——纵深防御不依赖网关版本，词典包坏链+内网拓扑外泄+伪造 XFH 采信三面闭合。

## 红先行（双端，终形态测试 × stash 对照修前源码实录）

- **Go**（`backend/gateway/cmd/server/setup_proxy_forwarded_test.go`，6 测全部过真实 `setupProxy` 到 httptest 后端）：修前 **4 红**——
  - `TestProxyAppendsClientIPToXFFExactlyOnce`：后端实收 `"8.8.8.8, 203.0.113.7, 203.0.113.7"`（双追加，与 wt735 探针一致）；
  - `TestProxySetsXFFToClientIPWhenAbsent`：`"203.0.113.7, 203.0.113.7"`；
  - `TestProxyPreservesOriginalHostInXForwardedHost`：XFH=`127.0.0.1:<port>`（内网 host，原始 Host 丢失）；
  - `TestProxyStripsForgedClientXFH`：后端实收 `evil.example.com`（伪造透传）。
  修后全绿；`TestProxyPreservesUpstreamXForwardedProto`/`TestProxySetsXForwardedProtoDefault` 两 XFP 钉测双向绿（语义不回退守卫）。
- **Python**：`tests/core/test_client_ip_attribution.py` 25 测（8 参数化 ×3 消费方 + None 签名 1）修前 **18 红**；`tests/api/test_vocabulary_external_base_url.py` 8 测修前 **4 红**（伪造 XFH 出现在返回 URL、零信任档/短链档仍采信）。修后两文件全绿。
- 诚实注记（测试场景订正）：初版用例以「单段 XFF `8.8.8.8` 期望归因对端」起红——该期望违背 EI-09 既定边界（单段链右起第 1 段=该段本身，`get_real_ip` 同形；网关在场时链恒为「伪造段, 网关追加段」两段）。用例已订正为部署实态链形态（`"8.8.8.8, <peer>"`），该边界非缺陷、不加宽。

## stdlib 现行语义实测（实现期发现，落注释防漂移）

Go 1.25.7 `net/http/httputil`：

1. **`SetXForwarded` 从 Out（非 In）读既有 XFF**——Rewrite 模式 stdlib 已剥 Out 的 X-Forwarded-\*，裸调 `SetXForwarded` 会**丢弃**入站链、XFF 仅剩单跳 IP。stdlib 文档明示复制处方 `r.Out.Header["X-Forwarded-For"] = r.In.Header["X-Forwarded-For"]`，本修照做以保「入站链完整+恰一次追加」。
2. **`SetXForwarded` XFH 无条件取 In.Host**（非「客户端自带 XFH 则透传」）——伪造 XFH 天然被剥，比旧 Director 透传行为更严，恰为台账修法草案「Rewrite 走 SetXForwarded 取 In.Host」的本义。
3. **`SetXForwarded` XFP 无条件按 In.TLS 置值**——网关内为明文段（In.TLS=nil 恒 http），若不补一手会把上游 nginx/ingress 写入的 `https` 覆盖回 `http`（scheme 降级回退）。本修在 `SetXForwarded` 后保留入站 XFP 值，与原 Director「有则保留、无则 http」逐路径一致，并有双向钉测。

## 验证门禁

- **Go**：`go test ./...` 13 包 ok 0 FAIL；`go vet ./...` 零输出；`gofmt -l` 零输出。
- **Python**：新测两文件 33 测全绿；既有面合跑 `tests/core/test_rate_limit_real_ip.py`+`tests/api/test_vocabulary_api.py`+`tests/unit/test_auth_session_touch.py`+`tests/unit/test_research_consent_tracker.py`+`tests/unit/test_auth_refresh_rotation.py`+`tests/unit/test_guest_access_ttl_refresh.py`+`tests/api/test_auth_login_empty_credentials.py`+`tests/core/test_ff_convergence_sites.py` = 98 绿；次批 `test_cache_security_prefix_failclosed`+`test_stage33_journey_events`+`spine/test_e2e_pipeline`+`spine/test_specialized_features`（grep 命中触达模块的全量）= 82 绿。合计 180 既有绿零回归。tests_e2e 需在航容器栈，本机未起栈未跑（无伪造）。
- **mypy**：`mypy app --ignore-missing-imports` 冷缓存双清对照（stash 修前 vs 修后，独立 MYPY_CACHE_DIR）：**133=133 错误清单逐条 NO-DIFF**。台账引 132 经证为暖缓存既有差（同 wt730/147、wt733 判例），本卡未回涨。
- **ruff/black**：触达 7 文件 ruff All checks passed；black 漂移 4 文件为 base 既有（stash 对照 base 同红），diff hunks 与新增行零重叠，新文件全净。
- **台账 verify**：`scripts/devtools/ledger_union_merge.py --verify` → `verify：315 行 V3-FIX 行，裸管分布 {8: 315}…verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法`——**零 FAIL**；diff 恰 2 行（426/428），行数 359 不变、重号 0。
- 测试环境：worktree 无 DB 配置（TEST-DBGUARD 裸 worktree 常态），backend/.env 仅含 gitignored 测试 SECRET_KEY、零 DB 键。

## 范围外观察（不立卡，留档）

1. **galaxy_handler.go:51 Director**：仅覆写 scheme/host，不触 XFF/XFH/XFP（其 stdlib 默认追加一次 client IP、XFH 原样透传）——属 wt735-VERIFY3 卫生观察 #3「代理头转发卫生」同族（authed 面现无 IP 归因消费方误信点），若后续 galaxy 面出现 XFF/XFH 消费方需按本卡同款右起+可信判断收拢，暂不立卡。
2. **XFF 单段链边界**：`forwarded_chain_trusted`/`get_client_ip` 对「直连引擎且 XFF 最右段恰为自身 IP」的模仿链按 EI-09 同款边界放行（部署面引擎不对公网直暴露，网关恒在场；两侧文档已如实注明边界）。
3. 台账「mypy 132」口径为暖缓存差，冷缓存实为 133（本卡与 wt733 双卡独立复证），后续卡引用时建议直书 133/冷缓存。

## 产出与提交

- `f72934f2` fix(gateway): V3-FIX-426/428 Rewrite 单一出口 + Go 守卫 6 测
- `028f6ff0` fix(engine): V3-FIX-426/428 三消费方右起收拢 + vocabulary 可信判断 + Python 守卫 33 测
- 本 docs commit: 台账 426/428 两行 FIXED@f72934f2 + 本 notes
- 新发现立卡：无（V3-FIX-459/460 执行前 grep 复核空闲、本卡未占用）
- 未 push；主线仓库零改动
