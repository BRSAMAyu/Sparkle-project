# Reviewer A — E19: 数据导出/可移植性——用户能取回自己的数据吗
Timestamp: 2026-04-26T12:10:00+08:00
Chain Index: 20

## Chain Flow Summary
用户请求导出个人数据或注销账号时：(1) 注销链路——mobile `delete_account_screen.dart` → `auth_repository.deleteAccount()` → Go Gateway proxy → Python `POST /users/me/delete-account` → soft-delete user record，session revoked；(2) 导出链路——仅存在 3 个碎片化导出端点（memory/persona/ai-usage），无统一全量导出，mobile 无导出 UI。合规基础设施（`DeletionProtocol` + `CryptoEraseManager`）代码完整但从未被任何端点调用。

## Critical Issues 🔴

**1. 无统一数据导出端点——GDPR数据可移植权无法履行**
- `backend/app/api/v1/memory.py:620` — `GET /memory/export` 仅导出 preferences + goals + episodic memories
- `backend/app/api/v1/user_persona_batch.py:148` — `POST /persona/export` 仅导出 persona preferences + goals
- `backend/app/api/v1/user_settings.py:115,137` — AI usage / AI ops 导出仅含统计摘要
- **缺失**: chat_messages, plans, tasks, error_records, galaxy nodes + edges, achievements, focus_sessions, calendar_events, community posts/messages, cognitive_fragments, visual_elements, photons, scaffolding_states, strategy_nodes 等全部用户生成内容
- Expected: 一个 `GET /users/me/data-export` 端点聚合所有用户数据。Actual: 不存在。

**2. Mobile 无数据导出 UI**
- `mobile/lib/features/user/presentation/screens/profile_screen.dart:787` — 仅有"注销账户"入口
- 搜索全部 mobile/lib 未发现任何 data export screen、GDPR request screen 或"导出我的数据"按钮
- 用户无法从 app 内请求导出自己的数据

**3. DeletionProtocol + CryptoErase 从未被调用**
- `backend/app/services/compliance/deletion_protocol.py` — 完整的 `request_deletion()` 实现（legal hold 检查 + crypto shredding）
- `backend/app/services/compliance/crypto_erase.py` — AESGCM 用户级 DEK 加密 + destroy_user_key + CryptoShreddingCertificate
- `backend/app/api/v1/users.py:504-558` — `delete_account` 端点直接 soft-delete user record，**不调用** `DeletionProtocol.request_deletion()`
- 搜索全部 `backend/app/api/` 无任何文件 import 或调用 `DeletionProtocol`
- 合规基础设施形同虚设：crypto shredding 从未执行，用户数据即使被"加密存储"也无法被真正抹除

## Major Issues 🟡

**1. 仅 soft-delete，无 hard-delete 或定时清理**
- `backend/app/api/v1/users.py:534-548` — 仅设置 `is_active=False`、`username=deleted_*`、`email=deleted_*`、`soft_delete()`
- 无 Celery task 或后台 job 在保留期后执行 hard-delete
- 用户数据在 DB 中永久保留，不满足"被遗忘权"要求

**2. 60+ 表的用户数据在 hard-delete 时不会被级联清除**
- `backend/gateway/internal/db/schema.sql` — 约 60 个表有 `REFERENCES users(id)` 但无 `ON DELETE CASCADE`
- 关键未级联表：`chat_messages`, `chat_sessions`, `plans`, `tasks`（经 tasks 表间接）, `error_records`, `episodic_memories`, `focus_sessions`, `behavior_patterns`, `cognitive_fragments`, `notifications`, `notification_preferences`, `passive_signals`, `scaffolding_states`, `strategy_nodes`, `posts`, `private_messages`, `friendships` 等
- 即使未来实现 hard-delete，这些数据会成为孤儿记录

**3. 注销确认文案误导用户**
- `mobile/lib/features/user/presentation/screens/delete_account_screen.dart:146-148` — 文案声称"所有与账号绑定的个人数据、偏好和历史记录都将永久移除"
- 实际行为：仅 soft-delete，数据永久保留在 DB 中
- Expected: 文案应反映真实行为，或实现文案承诺的删除行为

## Minor Issues 🟢

**1. Persona export CSV 格式不是真正的 CSV**
- `backend/app/api/v1/user_persona_batch.py:201-204` — CSV 分支仅将 JSON 数据包在 `{"format": "csv", "data": export_data}` 中，未做实际 CSV 转换
- 注释说 "In practice, use a CSV library" 但未实现

**2. Memory export 依赖两个 feature flag 同时开启**
- `backend/app/api/v1/memory.py:36-38,625-626` — 需要 `ENABLE_MEMORY_EXPORT=True` AND `ENABLE_MEMORY_PANEL=True`
- `backend/app/config/settings.py:571` — `ENABLE_MEMORY_EXPORT` 默认 True
- 若 `ENABLE_MEMORY_PANEL` 被关闭，导出端点返回 404 而非明确的"面板已关闭但导出仍可用"

## Working Well ✅

- **Account deletion mobile flow 完整** — `delete_account_screen.dart` 有确认输入、密码/social re-auth、confirmation dialog、loading state、success feedback、navigation to login
- **Session revocation 正确** — `delete_account` 端点正确调用 `revoke_all_sessions_for_user` 和 `set_user_revoked_before`
- **Social re-auth 覆盖完整** — 支持 Google/Apple/WeChat 重新认证后注销
- **Go Gateway 路由通畅** — `/users` group 使用 `users.Any("/*path", ...)` 全透传，delete-account 请求正确代理到 Python
- **合规模型设计完整** — `LegalHold`, `UserPersonaKey`, `CryptoShreddingCertificate`, `PersonaSnapshot` 模型结构合理
- **Master key provider 架构可扩展** — 支持 local/aws_kms/vault 三种 provider

## Files Examined

### Backend
- `backend/app/api/v1/users.py:504-558`
- `backend/app/api/v1/memory.py:36-38,620-668`
- `backend/app/api/v1/user_persona_batch.py:140-220`
- `backend/app/api/v1/user_settings.py:110-145`
- `backend/app/services/compliance/deletion_protocol.py` (全文)
- `backend/app/services/compliance/crypto_erase.py` (全文)
- `backend/app/services/compliance/legal_hold.py` (全文)
- `backend/app/services/compliance/key_provider.py` (全文)
- `backend/app/models/compliance.py` (全文)
- `backend/app/models/base.py:70-95`
- `backend/app/config/settings.py:571`
- `backend/gateway/internal/handler/proxy_routes.go:195-201` (users proxy)
- `backend/gateway/internal/db/schema.sql:11225-12625` (FK constraints)

### Mobile
- `mobile/lib/features/user/presentation/screens/delete_account_screen.dart` (全文)
- `mobile/lib/features/user/presentation/screens/profile_screen.dart:786-790`
- `mobile/lib/features/user/user_routes.dart:16,51`
- `mobile/lib/features/auth/data/repositories/auth_repository.dart:515-534`
- `mobile/lib/core/network/api_endpoints.dart:21`
- `mobile/lib/features/auth/presentation/screens/legal_document_screen.dart:125-145`

## Confidence: High — 搜索覆盖全部 API/Service/Mobile 层，FK 约束完整审计，合规断开连接有明确代码证据
