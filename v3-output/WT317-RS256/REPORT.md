# WT317-RS256 — JWT HS256 → RS256 非对称迁移（双验过渡）

- **base SHA**: `d8a89becac2fa94e59f26dd01fd565f3e1c08156`（main）
- **final SHA**: 见分支 `wt317-rs256-jwt` HEAD（代码提交 `ebccda342ccbbc662846670bc397db6b9a49450d`，报告提交为其后继一个 commit）
- **交付**: 代码 + 测试 + 轮换运维文档 + 本报告与 `changes.patch`（均已 commit 进分支）

## 一、审计现状（file:line，base SHA 下）

### 网关（backend/gateway）
| 项 | 位置 | 现状 |
|---|---|---|
| 签发点（access） | `backend/gateway/internal/handler/auth.go:155-191` | claims: sub/sid/exp/iat/jti/type=access；`JWT_ALGORITHM=RS256` 时走私钥 RS256，否则 HS256+`JWT_SECRET` |
| 签发点（refresh） | `backend/gateway/internal/handler/auth.go:193-234` | 同上，type=refresh，jti 持久化进 user_sessions |
| 验签点（唯一 choke point） | `backend/gateway/internal/middleware/auth.go:490-516`（`validateJWT`） | alg 白名单 switch：RS256 公钥 / HS256 secret / 其余拒绝；HTTP（`middleware/auth.go:399`）与 WS 握手（`middleware/ws_auth.go:52,73`）共用 |
| 密钥来源 | `backend/gateway/internal/config/config.go:50-57`（env）、`config.go:271-311`（PEM 解析 PKCS8/PKIX+PKCS1 回退） | `JWT_SECRET`（含 `SECRET_KEY` 别名回退 `config.go:685-689`）、`JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` 内联 PEM |
| 算法选择/校验 | `config.go:675-682`（默认 dev=HS256/prod=RS256）、`config.go:691-724`（非 dev RS256 双 PEM 必填+解析校验；dev 缺私钥回退 HS256） | |
| 生命周期 | access 默认 30min、refresh 默认 7d（`config.go:548-549`）；exp/iat/nbf+30s 时钟偏移校验在 `middleware/auth.go:661-682`；JTI/用户级/会话级吊销走 Redis+本地缓存 fail-closed | |

**审计结论（base 态缺口）**：RS256 双验骨架已存在，但 ① HS256 兜底无 env 开关、永远开着，无法收紧；② 无 kid header / 轮换面；③ 密钥只支持内联 PEM env，无文件装载；④ 攻击面（alg=none、HS256-公钥当 HMAC 密钥）无专项测试。

### 引擎侧（backend/app）——独立验签已存在，非"未来面"
- `backend/app/api/deps.py:34,97` → `decode_token` 独立验 access token
- `backend/app/core/security.py:50-70`：`_jwt_verify_keys` RS256 优先 + HS256 兜底；`_jwt_signing_key` 按 `ALGORITHM` 选私钥
- `backend/app/config/settings.py:283-285`：`ALGORITHM`（默认 HS256）、`JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`

按卡面"先落网关侧"：本卡全部改动在网关；引擎同构能力已在，仅需部署时同步公钥（运维文档已写明）。

## 二、双验设计（本卡实现）

1. **收紧开关**：`JWT_HS256_FALLBACK`（`*bool`，默认 nil=开）。`config.go` 新增 `HS256FallbackEnabled()`；`middleware/auth.go` HS256 分支先查开关，`false` 直接拒绝旧 token。默认保持双验，不断现有会话；收紧只需改 env 重启，可随时回滚。
2. **kid 轮换面**：签发侧 `handler/auth.go` `stampKid()` 给 RS256 token 写 `kid`（取 `JWT_KID`；HS256 永不带 kid，钉死在 `JWT_SECRET`）；验签侧新增 `rs256VerifyKey()`（`middleware/auth.go`）：token kid==`JWT_PREVIOUS_KID` → 宽限公钥 `JWT_PREVIOUS_PUBLIC_KEY`；无 kid/现役/未知 kid → 现役公钥回落（签名校验仍是唯一权威，未知 kid 无 bypass 增益）。
3. **密钥装载**：新增 `*_FILE` 三件套（`JWT_PRIVATE_KEY_FILE`/`JWT_PUBLIC_KEY_FILE`/`JWT_PREVIOUS_PUBLIC_KEY_FILE`），`loadJWTKeyFiles()` 在 Load 早期物化内联 PEM 字段（内联优先+告警；文件缺失 Fatal，杜绝半装载密钥进签发路径）；轮换公钥解析校验 + kid 成对告警（`config.go` 校验块）。
4. **alg 钉死**：验签 switch 显式枚举 RS256/HS256，`alg=none` 与其余一切算法拒绝（既有行为保留并有测试钉住）。
5. 零新依赖：`golang-jwt/jwt/v5 v5.3.0`（go.mod:9）原生 RS256，底层即标准库 `crypto/rsa`。

## 三、攻击面测试结果（23 个新用例，全绿）

新增文件：`internal/middleware/auth_rs256_test.go`（12）、`internal/handler/auth_rs256_test.go`（4）、`internal/config/config_jwt_rs256_test.go`（7）。

| 攻击面/路径 | 用例 | 结果 |
|---|---|---|
| alg=none | `TestValidateJWT_AlgNoneRejected_UnderRS256Config` | 拒绝 ✅ |
| HS256 用公钥 PEM 当 HMAC 密钥（经典混淆） | `TestValidateJWT_HS256WithPublicKeyAsHMACSecretRejected` | 拒绝 ✅ |
| HS256 用公钥 DER 当 HMAC 密钥 | 同上 | 拒绝 ✅ |
| 未注册密钥签名 | `TestValidateJWT_RS256SignedByUnregisteredKeyRejected` | 拒绝 ✅ |
| 篡改签名 | `TestValidateJWT_RS256TamperedSignatureRejected` | 拒绝 ✅ |
| 过期 | `TestValidateJWT_RS256ExpiredRejected` | 拒绝 ✅ |
| refresh 冒充 access | `TestValidateJWT_RS256RefreshTokenTypeRejected` | 拒绝 ✅ |
| 未知 kid 绕签名 | `TestValidateJWT_RS256UnknownKidCannotBypassSignature` | 拒绝 ✅ |
| 旧 HS256 token 兼容（双验默认） | `TestValidateJWT_HS256LegacyTokenAccepted_DualVerify` | 通过 ✅ |
| 收紧路径（fallback=false） | `TestValidateJWT_HS256Rejected_WhenFallbackTightened`（HS256 拒 + RS256 留通） | ✅ |
| 轮换宽限（kid 路由旧钥） | `TestValidateJWT_RS256Rotation_PreviousKidVerifiesWithPreviousKey` | 通过 ✅ |
| 签发 alg/kid header | `TestCreateAccessToken_RS256_AlgAndKidHeader` 等 4 例 | ✅ |
| 文件装载/内联优先/缺文件 Fatal/开关三态/轮换钥解析 | config 7 例 | ✅ |

## 四、测试证据（命令+数字）

```
CGO_ENABLED=0 go build ./...                                   # OK
CGO_ENABLED=0 go test ./internal/config/ -run "TestParseJWT|TestLoadJWTKeyFiles|TestHS256Fallback" -v
  → 7/7 PASS (1.024s)
CGO_ENABLED=0 go test ./internal/middleware/ -run "RS256|HS256|AlgNone" -v
  → 12/12 PASS (0.646s)
CGO_ENABLED=0 go test ./internal/handler/ -run "RS256|HS256_NoKid" -v
  → 4/4 PASS (0.754s)
CGO_ENABLED=0 go test ./internal/middleware/ ./internal/handler/ ./internal/config/
  → ok 7.96s / ok 28.45s / ok 0.89s（既有 auth 测试回归全绿）
CGO_ENABLED=0 go test ./...   （网关全仓）
  → 全部 ok，exit 0
bash scripts/run_all_rule_guards.sh → all rule guards passed (83 rules)
```
（AQ/BG 初跑假红系 worktree 缺 gitignored gen 产物，按卡面协议 `cp -RL` 主仓解引用拷贝 backend/gateway/gen、backend/app/gen、mobile/lib/gen 后转绿；gen 不入库。）

## 五、密钥轮换操作说明

完整 runbook 已入库：`docs/05_部署与运维/backend_JWT_RS256_KEY_ROTATION.md`（已登记目录 README）。要点：

1. 生成：`openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048` + `openssl pkey -pubout`；私钥永不下发验证方。
2. 轮换四步：加宽限钥（`JWT_PREVIOUS_KID`+`JWT_PREVIOUS_PUBLIC_KEY(_FILE)`）→ 换现役三件套（`JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`/`JWT_KID`）重启 → 等旧 token 过期（上界=refresh 7 天；引擎侧同步 `JWT_PUBLIC_KEY`）→ 清宽限钥。每步可独立回滚。
3. 收紧：`JWT_HS256_FALLBACK=false`（在所有 HS256 token 过期后执行）。

## 六、风险与边界

- **引擎收紧无开关**：引擎 `security.py` 双验恒开（RS256 优先），无独立 tighten env；网关收紧后引擎仍收旧 HS256 token 直至过期——公钥消费方语义以网关为权威，风险有界（≤ refresh 生命周期）。建议后续卡给引擎补同构开关。
- **无 kid 的存量 RS256 token**（若有早于本卡签发者）：回落现役钥；轮换此类 token 不走 kid 路由，需等其自然过期（文档已注明窗口=7 天）。
- **kid 不承载信任**：仅选钥路由，未知 kid 回落现役钥，已用测试钉死无 bypass。
- 磁盘/内存纪律：纯 LIGHT（无模拟器/Gradle/flutter/浏览器）；未产生 /tmp 产物；gen 副本为 gitignored 环境补齐，随 worktree 生命周期回收。
