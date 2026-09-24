# JWT RS256 非对称签名与密钥轮换

> 适用范围：Go 网关（`backend/gateway`）。Python 引擎侧同构支持见 `backend/app/core/security.py`（`_jwt_verify_keys`，RS256 优先 + HS256 兜底）。

## 当前状态

网关已完成 HS256 → RS256 迁移（双验过渡态）：

- **签发**：`internal/handler/auth.go`（access + refresh）。`JWT_ALGORITHM=RS256` 时用 `JWT_PRIVATE_KEY` 私钥签名，并在 JOSE header 写入 `kid`（取 `JWT_KID`）。
- **验签**：`internal/middleware/auth.go` `validateJWT`（HTTP 与 WebSocket 握手共用的唯一验签 choke point）。RS256 优先公钥验签；HS256 兜底验旧 token（默认开启）；`alg=none` 及其余算法一律拒绝。
- **密钥装载**：支持两种形式，env 内联 PEM（`JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`）或文件挂载（`JWT_PRIVATE_KEY_FILE`/`JWT_PUBLIC_KEY_FILE`，内联为空时生效，冲突时内联优先并告警）。
- **生命周期**：access 默认 30 分钟（`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`），refresh 默认 7 天（`JWT_REFRESH_TOKEN_EXPIRE_DAYS`）。

### 双验过渡开关

| 变量 | 默认 | 含义 |
|------|------|------|
| `JWT_HS256_FALLBACK` | `true` | `true`：RS256 优先 + HS256 兜底（过渡态，不断现有会话）。`false`：只收 RS256，旧 HS256 token 全拒（收紧态）。 |

收紧时机：所有 HS256 token 自然过期后（上界 = refresh token 有效期 7 天）。收紧不需要重启滚动窗口外操作，改 env 重启即可；该开关随时可以改回 `true` 回滚。

## 密钥生成（一次性）

```bash
# 私钥（PKCS8，网关与签发方独占，永不入库/永不下发给验证方）
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt_private.pem
# 公钥（PKIX，分发给所有验证方：网关验签、Python 引擎验签、未来服务）
openssl pkey -in jwt_private.pem -pubout -out jwt_public.pem
```

密钥材料只走部署通道（secret manager / 挂载文件），严禁提交进 git（`.gitignore` 已覆盖 `*.pem` 类敏感文件与 `.env`）。

## 密钥轮换操作（kid 路由，零会话中断）

网关验签按 token 的 `kid` header 路由公钥：`JWT_KID`（现役）→ 匹配 token `kid` 即用现役公钥；`JWT_PREVIOUS_KID` → 用轮换宽限公钥 `JWT_PREVIOUS_PUBLIC_KEY`；无 `kid` 或未知 `kid` 一律回落现役公钥（签名校验仍是唯一权威，伪造 `kid` 无增益）。

轮换四步（每步可独立验证、可回滚）：

1. **准备新钥**：生成新 RSA 密钥对（见上），新 `kid` 建议用日期标记（如 `2027-03`）。
2. **加宽限钥（验签侧先行）**：现网关 env 追加
   `JWT_PREVIOUS_KID=<旧kid>`、`JWT_PREVIOUS_PUBLIC_KEY=<旧公钥PEM>`（或 `JWT_PREVIOUS_PUBLIC_KEY_FILE=<旧公钥路径>`），并把 `JWT_ALGORITHM=RS256` 下的 `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`/`JWT_KID` 换成新钥与新 `kid`，重启。此刻起：新 token 用新钥签 + 带 `kid`，存量旧 token 凭旧 `kid` 走宽限钥验签，会话不断。
3. **等旧 token 自然过期**：上界 = refresh token 有效期（默认 7 天）。引擎侧同步更新其 `JWT_PUBLIC_KEY` 为新公钥。
4. **清宽限钥（收紧）**：确认无旧 `kid` token 残留后，移除 `JWT_PREVIOUS_KID`/`JWT_PREVIOUS_PUBLIC_KEY(_FILE)`，重启。轮换完成。

回滚：任意一步异常，把第 2 步的三个变量指回旧钥即恢复原状（双验窗口本身不受影响）。

## 已知边界

- 引擎（`backend/app`）独立验签（`backend/app/api/deps.py` → `decode_token`），公钥消费方已存在，不止是未来面；引擎的 `ALGORITHM`/`JWT_PUBLIC_KEY` 需与网关签发口径同步（见上表第 3 步）。
- 算法混淆攻击面已钉死并有单测：`alg=none` 拒绝；HS256 用公钥 PEM/DER 当 HMAC 密钥的攻击必拒（`internal/middleware/auth_rs256_test.go`）。
- `kid` 仅做选钥路由，不承载信任；信任边界始终是签名验证。
