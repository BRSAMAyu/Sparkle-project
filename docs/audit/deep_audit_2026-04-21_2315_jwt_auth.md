# 深度审计：JWT 认证完整链路

> 日期：2026-04-21 23:15
> 范围：Go Gateway 认证中间件 → WebSocket 认证 → Token 黑名单 → Flutter 客户端认证 → 数据库 Schema

## 审计发现

### P0 — 阻断性问题（3 项）

#### P0-1: Refresh Token 缺少轮换机制
- **位置**: `backend/gateway/internal/handler/auth.go:180-206`
- **问题**: 每次刷新生成新 token 但未作废旧 token，refresh token 泄露后可被长期重放
- **证据**: `createRefreshToken()` 生成新 JTI 但未找到更新 `user_sessions.refresh_token_jti` 或作废旧 JTI 的逻辑
- **影响**: OAuth 2.0 安全最佳实践违规；攻击者获得 refresh token 后可在 7 天内无限续期
- **修复**: 每次刷新时 (1) 将旧 JTI 写入黑名单 (2) 更新 `user_sessions.refresh_token_jti` (3) 检测重复使用已作废 token（标记为泄露）

#### P0-2: WebSocket Token 通过 URL Query Parameter 传输
- **位置**: `backend/gateway/internal/middleware/ws_auth.go:61-78` + `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1357-1362`
- **问题**: 当 `AllowWsQueryToken=true` 或 wsTicket 获取失败时，JWT 直接暴露在 URL 中
- **证据 Go**:
  ```go
  if cfg.AllowWsQueryToken {
      if queryToken := c.Query("token"); queryToken != "" { ... }
  }
  ```
- **证据 Flutter**:
  ```dart
  if (wsTicket != null && wsTicket.isNotEmpty) {
    queryParameters['ticket'] = wsTicket;
  } else if (effectiveToken != null) {
    queryParameters['token'] = effectiveToken;  // fallback 泄露
  }
  ```
- **影响**: URL 被记录在服务器日志、代理日志、浏览器历史中，token 永久泄露
- **修复**: 移除 Flutter fallback 逻辑；Go 侧 `AllowWsQueryToken` 默认 false 且生产环境禁用

#### P1-6: Email 明文存储（原 P0-3，自审降级：需数据库泄露前提，不影响运行时安全）
- **位置**: `backend/gateway/internal/db/schema.sql:4570`
- **问题**: `email character varying(255) NOT NULL` — 明文存储，无加密
- **影响**: 数据库泄露时所有用户邮箱暴露，违反 GDPR 合规要求
- **修复**: 使用 pgcrypto 的 `pgp_sym_encrypt()` 加密存储，或数据库级 TDE

---

### P1 — 重要问题（5 项）

#### P1-1: Token 黑名单 Fail-Open 默认模式
- **位置**: `backend/gateway/internal/config/config.go:462`
- **问题**: `REDIS_FAIL_CLOSED` 默认 false，Redis 不可用时允许请求通过
- **证据**: `auth.go:305-311` — Fail-Open 模式打印 WARNING 但放行
- **修复**: 所有环境默认 true；`IsDevelopment()` 可降级为 false 但需显式配置

#### P1-2: user_revoked_before 无设置端点
- **位置**: `backend/gateway/internal/middleware/auth.go:319-350`
- **问题**: 读取 `user_revoked_before:{userID}` 的逻辑存在，但未找到写入该 key 的端点
- **影响**: 用户无法全局撤销所有 token；密码修改后旧 token 仍有效
- **修复**: 实现 `/api/v1/auth/revoke-all` 端点；密码修改时自动触发

#### P1-3: WebSocket Ticket 无使用频次限制
- **位置**: `backend/gateway/internal/handler/ws_ticket.go:28-65`
- **问题**: 单个 ticket 是一次性删除的，但每用户可无限获取新 ticket
- **修复**: 限制每用户每分钟 ticket 获取数（如 ≤5）；记录 ticket 发放审计日志

#### P1-4: Flutter Logout 状态清理不彻底
- **位置**: `mobile/lib/features/auth/presentation/providers/auth_provider.dart:528-537`
- **问题**: `logout()` 清理了本地数据但未主动断开活跃的 WebSocket 连接
- **修复**: logout 时先调用 `WebSocketChatService.disconnect()` 再清理本地状态

#### P1-5: 本地黑名单缓存集群不同步
- **位置**: `backend/gateway/internal/middleware/auth.go:71-80`
- **问题**: `localBlacklistCache` 是进程内 map，多实例部署时各实例缓存不一致
- **影响**: 在实例 A 撤销的 token 可能在实例 B 的本地缓存中未标记
- **修复**: 文档说明多实例部署限制；考虑 Redis Pub/Sub 同步或增大 Redis 可用性保障

---

### P2 — 改进建议（5 项）

#### P2-1: STT WebSocket Origin 检查缺失
- **位置**: `backend/gateway/internal/handler/stt_handler.go:19-21`
- **问题**: `CheckOrigin: return true` 允许所有来源，未复用 `WebSocketFactory` 的安全验证
- **修复**: 统一使用 `WebSocketFactory` 创建所有 WebSocket upgrader

#### P2-2: JWT 密钥最小长度未验证
- **位置**: `backend/gateway/internal/handler/auth.go:176,204`
- **问题**: `[]byte(h.cfg.JWTSecret)` 直接使用，未校验密钥长度 ≥32 字节
- **修复**: 启动时 `if len(cfg.JWTSecret) < 32 { log.Fatal(...) }`

#### P2-3: Flutter Token 过期无预刷新
- **位置**: `mobile/lib/features/auth/data/models/token_model.dart:23-24`
- **问题**: 后端返回 `expiresIn` 但客户端未用于预刷新，只在 401 时才刷新
- **修复**: 拦截器中检查 token 剩余时间 <5min 时主动刷新

#### P2-4: auth_audit_log 无清理机制
- **位置**: `backend/gateway/internal/db/schema.sql:68-86`
- **问题**: 审计日志表无分区、无 TTL、无清理任务，将无限增长
- **修复**: 按 `occurred_at` 范围分区 + Celery 定期清理 >180 天数据

#### P2-5: 配置示例含弱密钥
- **位置**: `backend/gateway/.env.example:28`, `.env.local.example:28`
- **问题**: `JWT_SECRET=your_jwt_secret` / `dev_jwt_secret_change_me` 长度不足
- **修复**: 使用 `openssl rand -hex 32` 生成占位值，标注必须替换

---

### ✅ 合规项（6 项）

1. **密码哈希**: `backend/app/core/security.py:22` — bcrypt + passlib，12 rounds ✅
2. **Admin Secret 时序攻击防护**: `auth.go:209` — `subtle.ConstantTimeCompare` ✅
3. **JWT 签名算法锁定**: `auth.go:238-239` — 强制验证 HS256 ✅
4. **Token 类型校验**: `auth.go:257-259` — 验证 `type=access` ✅
5. **Flutter 安全存储**: `auth_repository.dart:735-742` — `flutter_secure_storage` + `encryptedSharedPreferences` ✅
6. **数据库索引完整**: `schema.sql:10921-10970` — user_sessions 8 个索引覆盖所有查询模式 ✅

---

## 关键代码引用

### Go Gateway 认证流程
```
请求 → cors.go → security.go → timeout.go → rate_limit.go → auth.go
                                                            ↓
                                                    validateJWT()
                                                    ├── 解析 token
                                                    ├── 验证 HS256 签名
                                                    ├── 检查 exp/iat/type
                                                    ├── 本地缓存查黑名单
                                                    ├── Redis 查 JTI 黑名单
                                                    └── Redis 查 user_revoked_before
```

### WebSocket 认证流程
```
Flutter → ws_ticket API (POST /api/v1/ws/ticket) → 获取一次性 ticket
       → WebSocket 连接 (GET /ws?ticket=xxx)
       → ws_auth.go → Redis GETDEL ticket → validateJWT()
```

### Flutter Token 管理
```
登录 → SecureStorage 存储 access/refresh token
请求 → ApiInterceptor 检查 401 → refreshToken() (Completer 防并发)
刷新 → SecureStorage 更新 → 重放失败请求
登出 → SecureStorage.deleteAll → 清理本地缓存
```

---

## 建议修复方案（按优先级）

| 优先级 | 问题 | 修复方案 | 预估工作量 |
|--------|------|---------|-----------|
| P0-1 | Refresh Token 无轮换 | 刷新时作废旧 JTI + 更新 sessions 表 + 泄露检测 | 中（~100 行 Go） |
| P0-2 | WS Query Token 泄露 | Flutter 移除 fallback + Go 默认禁用 query token | 低（~20 行） |
| P0-3 | Email 明文存储 | pgcrypto 加密 + 迁移脚本 | 中（迁移 + 读写改造） |
| P1-1 | Fail-Open 默认 | 配置默认值改 true | 低（1 行） |
| P1-2 | 无全局撤销端点 | 新增 /auth/revoke-all + 密码修改触发 | 中（~80 行） |
