# Web 会话断链修复（Round 2）· W-1/W-2/W-3/W-4

- 日期：2026-09-18
- 执行：Web 会话断链修复专员（worktree `wt7`，基线 `dd9d62d3` = main HEAD）
- 上游依据：[多端实测/web-round1.md](../../多端实测/web-round1.md)（根因实锤：flutter_secure_storage web 并发写静默全丢，IndexedDB `user.box` 空盒实证）
- 红绿纪律：每项先红后绿；红证据均为可复现操作（临时摘除修复/删除新文件后跑定向测试）

## 修复项总览

| 项 | 结论 | 生产代码变更 | 测试 |
|---|---|---|---|
| W-1/W-2 token 持久化（web） | **已修复** | 新增 TokenStorage 门面（conditional import）+ AuthRepository 切换 | 4+4 绿（红=编译失败实证） |
| W-1 竞态（login vs checkAuthStatus 覆盖） | **已修复** | AuthNotifier 会话世代守卫 | 3 绿（摘守卫 3 红） |
| W-4 Enter 双触发 | **已修复** | 登录页 800ms 防重入 + 显式 textInputAction | 2 绿（摘修复 2 红） |
| W-3 后端空凭据 200 | **无需修码，回归锁钉死** | 无（校验器自 initial commit 即存在） | 7 绿（摘校验器 2 红） |

验证命令与结果见文末「验证汇总」。

---

## 1. W-1/W-2 · Token 存储门面（核心）

### 变更

新增 `mobile/lib/core/storage/`（conditional import 先例：`core/offline/local_database_store*.dart`）：

- **`token_storage.dart`** — `TokenStorage` 抽象（`read/write/delete`，key-value 全异步）+ `createTokenStorage()` 工厂 + `tokenStorageProvider`。
- **`token_storage_io.dart`** — `SecureTokenStorage`：转发 FlutterSecureStorage，默认选项与原 `flutterSecureStorageProvider` 完全一致（Android EncryptedSharedPreferences + iOS first_unlock），**原生行为不变**；可注入 storage 供测试。
- **`token_storage_web.dart`** — `TokenStorageWeb`：SharedPreferences（localStorage）。头注释明确「**竞赛/dev 可接受；生产 web 应升级为加密方案（WebCrypto 派生密钥 + IndexedDB 或服务端 HttpOnly Cookie），并迁移既有 key**」。

`auth_repository.dart`：`_storage` 类型 FlutterSecureStorage → `TokenStorage`；`authRepositoryProvider` 改 watch `tokenStorageProvider`。`flutterSecureStorageProvider` **保留**（当前无其他消费方，供未来非 token 敏感小数据使用）。

**全仓 grep 遗漏排查**（结论：无其他 token 持久化点）：
- `FlutterSecureStorage` 在 lib/ 仅存于门面 io 实现、auth_repository 注释/保留 Provider、local_database_store_io 注释；
- `keyAccessToken/keyRefreshToken` 仅 `app_constants.dart`（定义）与 `auth_repository.dart`（唯一读写点）；
- `setString.*token` 类写入仅 push_token_manager（推送 token，非认证会话）。

### 波及修复（15 个既有测试文件的编译适配）

AuthRepository 构造签名变化波及既有测试 fake（`_MemorySecureStorage`/`const FlutterSecureStorage` 直传 super），逐一以 `SecureTokenStorage(storage: …)` 包裹（行为等价），或如 `auth_repository_test.dart` 直接改用 `InMemoryTokenStorage`。其中 `auth_repository_test.dart` 在基线即**无法编译**（其 `TestApiClient.post/put/patch` 覆写缺 `Object? data` 具名参数，与 ApiClient 现签名不符），本次随改随修。

**关键波及**：`dashboard_test_harness.dart` 除包裹外还需**新增 `tokenStorageProvider` override** —— 仪表盘链路（`intent_prediction_provider.dart:85` 等 5 处）会真实调用 `authRepositoryProvider.getAccessToken()`；切门面后该读路径走 `tokenStorageProvider`，harness 若只 override 旧的 `flutterSecureStorageProvider` 会命中真实 secure storage 平台通道（MissingPluginException），导致 briefing 区块缺失。该回归在红绿对照中被捕获并修复（见下）。

### 红绿证据

- **红**（摘除 3 个门面 lib 文件后跑 `token_storage_test.dart`）：
  `Error: 'TokenStorageWeb' isn't a type` / `Method not found: 'setUpI18nForTesting'`… → 编译失败（0 过）。
- **绿**（恢复后）：
  - `token_storage_test.dart` **4/4**：web 后端 write→read 往返、**saveTokens 的 4 连写并发模式不再丢数据**（复刻 round-1 实证丢失形态）、未命中返回 null、VM 下工厂解析到 io 后端。
  - `auth_repository_test.dart` **4/4**：含验收用例 `W-1/W-2: web storage keeps tokens across saveTokens → read`（注入 `TokenStorageWeb`，saveTokens 后 `getAccessToken/getRefreshToken/isLoggedIn` 全部取回，clearTokens 后归零）。

## 2. 竞态收口 · AuthNotifier 会话世代守卫

### 变更（`auth_provider.dart`）

- `_sessionGeneration` 自增令牌：`_beginSessionOp()` / `_isStaleSessionOp(gen)`。
- 覆盖点：`checkAuthStatus` / `login` / `register` / `socialLogin` / `loginAsGuest` 每个 await 之后的**终态写入前**校验世代，过世代写入直接丢弃；`login` 等的 **finally** 同样受守卫；`_resetInvalidStoredSession` 携带世代参数（过世代**不再清 token**，防误杀新会话）；`logout` 开新世代作废在途登录写入。

### 红绿证据（`auth_session_generation_test.dart`）

- **红**（`git checkout -- auth_provider.dart` 摘除守卫后）：**3/3 红** ——
  1) 过世代 `checkAuthStatus` 的未认证写入覆盖 login 成功态（isAuthenticated→false）；
  2) 过世代 login 的 catch/finally 覆盖新 `checkAuthStatus` 成功态；
  3) logout 后在途 login 仍写入已认证态。
- **绿**（守卫在场）：**3/3 绿**。

## 3. W-4 · Enter 双触发（登录页）

### 变更（`login_screen.dart`）

- `_consumeSubmitTicket()`：**同一提交 800ms 去重窗口**（`_submitDedupWindow`），`_submit` 与 `_submitAsGuest` 共用——直接封杀 round-1 实测的「一次手势序列 login+guest 双 POST」。
- TextField 显式 IME 语义：username `textInputAction: TextInputAction.next` + `onFieldSubmitted → nextFocus`；password `TextInputAction.done` + `onFieldSubmitted → _submit`。明确唯一 Flutter 侧提交通道，web 原生 form submit 通道即使并发触发也被防重入窗口吸收。

### 红绿证据（`login_screen_submit_test.dart`，视口 800×2200 保证按钮同屏可达）

- **红**（`git checkout -- login_screen.dart` 摘除修复后）：**2/2 红** ——
  1) 同帧双击登录按钮 → `loginCalls == 2`（期望 1）；
  2) 点登录后同帧点访客 → `guestCalls == 1`（期望 0）。
- **绿**（修复在场）：**2/2 绿**。
- 注：计数桩在 repository 入口计数后走失败路径，避免 fake-async 下 SessionRefresh→WebSocket warmUp 挂起 timer 干扰断言。

## 4. W-3 · 后端空凭据 login（复现 → 结论修正 → 回归锁）

### 现场复现矩阵（走查同栈：网关 :8080 / 引擎 :8000，引擎 cwd=主仓 backend@dd9d62d3）

| 请求体 | 网关 | 引擎直连 |
|---|---|---|
| `{"username":"","password":""}` | **400** | **400**（`username or email is required`） |
| `{"username":null,"email":null,"password":""}` | 400 | — |
| `{}`（缺 password） | 400 | — |
| `{"username":" ","password":" "}` | 401 | — |
| `{"username":"x","password":""}` | 401 | — |

**结论修正**：W-3 的「200」为 **W-8 双进程事故的旧进程假象**（round-1 报告已记录引擎双进程）；现行代码自 initial commit（1722e6dc）即含 `UserLogin._validate_identifier` 模型校验器（`schemas/user.py:65`，空 username+email 抛 ValueError → RequestValidationError → main.py 映射 **400**）+ login 端点 `if not login_id` 兜底 + `verify_password` 对空口令恒 False → **401**。当前单进程引擎（PID 2918）现场实证 400/401，无生产码缺口，**网关与引擎均未改动**。

### 红绿证据（新增 `backend/tests/api/test_auth_login_empty_credentials.py`，TestClient 直连路由、无网关/DB/Redis 依赖）

- **绿**：**7/7** —— 空 username+password 400、双标识符 null 400、缺 password 400、空白用户名 401、存在用户空口令 401、错误口令 401、**正确凭据对照 200**（防过度拦截；`_issue_auth_tokens` 桩掉，锁 200 语义）。
- **红**（临时摘除 `_validate_identifier` 校验器）：空凭据两用例回落 **422（≠400 契约）** → `test_empty_username_and_password_returns_400`、`test_all_identifiers_null_returns_400` 红；恢复后全绿。证明 400 语义确由该校验器保证。

---

## 验证汇总

- **backend pytest**（SECRET_KEY/JWT_SECRET/REDIS_URL 按规程注入）：
  `tests/api/test_auth_login_empty_credentials.py` → **7 passed**。
- **flutter test**（定向文件，`--concurrency=4`）：
  - 本轮新增/重写：`auth_repository_test`(4) + `token_storage_test`(4) + `auth_session_generation_test`(3) + `login_screen_submit_test`(2) + `auth_session_restore_test`(3) → **16/16 绿**；
  - 波及适配套件：app 四件（router_smoke 7+1-、router_deep_link 4 绿、main_pages_load 5+1-、main_actions 7+2-）**与基线逐项一致**（基线亦为 -1/-0/-1/-2，均为先在失败：主题扩展未注册等，非本轮引入）；widget/user/achievement/shop/unit 批 **48 绿 + 3 失败**（3 失败与基线逐项一致）；dashboard 批在 harness 补 `tokenStorageProvider` override 后恢复基线（3 失败=基线先在项）。
- **flutter analyze**：非 third_party_plugins 错误 **0**（vendored fork 先在错误不计）。
- **不重启任何服务**：全程未动 :8000/:8080/:50051 进程；`lib/gen`、`backend/gateway/gen` 未手改（worktree 缺失部分自主仓 cp，内容与提交版本一致，git 状态干净）。

## 遗留与建议

1. web token 明文落 localStorage 为竞赛期临时方案，生产前按 `token_storage_web.dart` 头注释升级加密方案（建议独立工单）。
2. round-1 W-5（语义树残缺）/W-6（glass-pane 0×0）/W-7（i18n+品牌）未在本轮范围，按原批次计划移交。
3. 仪表盘链路 5 处 `authRepositoryProvider.getAccessToken` 消费点在单测中需 override `tokenStorageProvider`（dashboard_test_harness 已示范），后续新测试注意。
