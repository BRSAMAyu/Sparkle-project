# V3-FIX-17 诊断报告：Web 注册「静默假失败」根因

- 诊断人：V3 Fleet 诊断 Worker（wt6，LIGHT 静态分析 + API 级 curl）
- 基线：wt6 @ `42180162`；主仓只读参照；证据存档（只读）：`wt7/v3-output/B-03/evidence/web_register_defect_probes_20260919/`
- 修复草案：同目录 `fix_draft.patch`（**未 apply**，不改任何 mobile/lib 生产代码）

---

## 1. 结论摘要

**最可能根因（机制链已 100% 锁定，具体抛点待一个栈确认）**：注册 POST 在网关已 200 且建号成功、响应体为合法 JSON（`application/json`，已实测），错误发生在 **Flutter Web Dart 侧 dio 成功管线内部**——某个**非 Dio 异常**（adapter 事件处理 / 响应解码 / 泛型 cast 窗口之一）被 dio 的 `assureDioException` 统一包装为 `DioExceptionType.unknown`（dio 5.9.0 `dio_mixin.dart:440/523/589`），再被 `AppFailureMapper.fromDio` 的 unknown 兜底分支一揽子映射为 `NetworkFailure`（`mobile/lib/core/errors/failures.dart:291-306`），最终以固定文案「网络连接不稳定，这次请求没有完整送达。」+ 错误音效 + 停留注册页呈现。**账号实际已创建，UI 却引导用户重试（必撞「用户名已存在」）。**

**次可能（并存实锤、跨源条件缺陷）**：网关 CORS `Access-Control-Allow-Headers` 白名单**缺 `X-Idempotency-Key`**（`backend/gateway/internal/middleware/cors.go:21`，已 OPTIONS 预检实测确认），而 `IdempotencyInterceptor`（R2-8）给**每个** POST/PUT/PATCH/DELETE 注入该头。任何跨源部署形态下（页面前端与 API 不同源），注册/登录/购买等全部变更类 POST 将**死于预检、POST 根本不发出**，同样表现为 auth 假失败（文案为 Offline 变体）。B-03 五连复现是同源 harness（复现会话零 OPTIONS 预检），故它不是本次五连复现的直接根因，但它是同一症状家族的第二入口，且解释了「回归面」：R2-8（`8ddfe535`）新增头注入时未同步网关白名单。

**置信度**：机制链（unknown→NetworkFailure→固定文案→卡注册页）≈ 95%（排除法闭环，见 §4）；「具体抛点 = adapter XHR 事件/解码族」≈ 50%（静态可审面已穷尽且全部安全，需 E1 抓栈定谳）；H2 跨源预检缺陷存在性 = 100%（实测）。

---

## 2. 注册链路完整调用链（file:line）

```
用户点击注册按钮
└─ mobile/lib/features/auth/presentation/screens/register_screen.dart:40-60  _submit()
   ├─ :41  Form.validate()（仅本地校验；确认密码不一致仍可发出 POST —— B-03 次级发现）
   ├─ :48  SensoryFeedbackService.emit(confirm)           ← confirm.ogg（probe2 可见，先于 POST）
   └─ :50  authProvider.notifier.register(...)
      └─ mobile/lib/features/auth/presentation/providers/auth_provider.dart:245-290  register()
         ├─ :256  state.copyWith(isLoading: true)          ← 注册按钮进入 loading
         ├─ :259-264  DemoMode 关闭 + _clearUserScopedLocalData()（POST 之前）
         ├─ :265  _authRepository.register(...)
         │  └─ mobile/lib/features/auth/data/repositories/auth_repository.dart:33-74  register()
         │     ├─ :47-59  _apiClient.post<Map<String,dynamic>>(ApiEndpoints.register, data:{...})
         │     │  └─ mobile/lib/core/network/api_client.dart:42-48  post<T> → _dio.post
         │     │     └─ Dio(BaseOptions{ baseUrl=ApiConstants.baseUrl+'/api/v1',
         │     │        connectTimeout 10s, receiveTimeout 30s, contentType:'application/json' })
         │     │        api_client.dart:16-28 构造；拦截器顺序：Auth → Retry → Logging → Idempotency
         │     │        ├─ api_interceptor.dart:96-119   AuthInterceptor.onRequest：注入 X-Device-Id/
         │     │        │                                X-Device-Platform/X-Device-Name（:104-105），
         │     │        │                                有 token 才加 Authorization（web 注册时无）
         │     │        ├─ idempotency_interceptor.dart:14-25  POST 注入 X-Idempotency-Key (uuid)
         │     │        ├─ http_client_pinning.dart:2    web 编 ribbons = stub（no-op，无自定义 adapter）
         │     │        └─ Web adapter = dio_web_adapter 2.1.1（pubspec.lock 锁定；dio 5.9.0）
         │     │           BrowserHttpClientAdapter（XMLHttpRequest, responseType=arraybuffer,
         │     │           xhr.timeout = connect+receive = 40s）
         │     ├─ :62  data['token'] as Map<String,dynamic>? ?? data（响应含嵌套 token，命中前者）
         │     ├─ :63-64  TokenResponse.fromJson + saveTokens（web 走 token_storage_web.dart →
         │     │          SharedPreferences/localStorage；W-1/W-2 修复后通道）
         │     ├─ :65  UserModel.fromJson(data['user'])
         │     ├─ :66-67  on DioException → AppFailureMapper.fromDio(e)   ← ★错误映射入口
         │     └─ :68-73  catch(e) → AppFailureMapper.from(e)            ← 非 Dio 异常兜底
         ├─ :275  成功：isAuthenticated=true + SessionRefreshService
         └─ :278-280  失败：_failedAuthState(e, isAuthenticated:false)
            └─ :77  AppFailureMapper.from(error)（error 已是 AppFailure → 原样透传）

错误呈现
└─ register_screen.dart:86-100  ref.listen(authProvider)：next.error 非空 →
   :89-97  AppFeedback.error(context, failure?.userMessage)
   ├─ failure.userMessage → NetworkFailure ⇒ failures.dart:97-99 固定文案
   │  「网络连接不稳定，这次请求没有完整送达。」          ← ★全库该文案唯一来源
   └─ app_feedback.dart:74  SparkleFeedbackRole.error → SensoryFeedbackEvent.error
      └─ sensory_feedback_service.dart:565-567  播放 assets/audio/ui/error.ogg  ← probe2 实证
```

网关侧：`/api/v1/auth/register` 走 **NoRoute 反向代理**到 Python 引擎（`backend/gateway/cmd/server/setup.go:869-890, 904`），非网关原生 handler。

---

## 3. 错误映射链（观察文案的证明）

`AppFailureMapper.fromDio`（`failures.dart:224-308`）分支顺序：401/403→Auth；400/422→Validation；≥500→Server；然后按 `error.type`：

| DioExceptionType | 映射 | SnackBar 实际文案 |
|---|---|---|
| connectionTimeout/sendTimeout/receiveTimeout | `NetworkFailure('CONNECTION_TIMEOUT')` | 「网络连接不稳定…」（:97-99 固定） |
| connectionError | **`OfflineFailure('OFFLINE')`** | 「当前像是离线状态。已保留本地内容…」（:87-89） |
| badCertificate/badResponse | ServerFailure | 服务不稳定文案 |
| cancel | `NetworkFailure('REQUEST_CANCELLED')` | 「网络连接不稳定…」 |
| **unknown**（无 offline 特征） | **`NetworkFailure('NETWORK_ERROR')`**（:291-306） | 「网络连接不稳定…」 |

关键事实（可证伪性核验完毕）：
1. 观察文案「网络连接不稳定，这次请求没有完整送达。」全库**唯一**来源 = `failures.dart:98`（grep 证实）⇒ 失败对象必为 `kind=network` ⇒ **NetworkFailure**；
2. `NetworkFailure` 全库**唯一构造点** = `fromDio`（grep 证实）⇒ 抛出物必为 DioException 且 type ∈ {三超时, cancel, unknown}；
3. `auth_provider._failedAuthState` 用 `AppFailureMapper.from`，但 `from` 对已是 AppFailure 的 error 原样透传（`failures.dart:183-185`），且 `from()` 本身**不可能产出 NetworkFailure**（只产 Auth/Offline/Server/Validation/Unknown）——这同时排除了「管线外的普通异常被误标为网络错误」的可能；
4. unknown 的产生机制：dio 对**非 DioException** 的异常一律 `assureDioException` 包装为 `type=unknown, error=原始异常`（dio 5.9.0 `dio_mixin.dart:723-731`），包装点覆盖：请求/响应拦截器抛错（:440）、fetch 尾部 try（:523）、`_dispatchRequest` 整体 try（:589，覆盖 adapter fetch、`transformer.transformResponse`、`assureResponse` 泛型 cast `dio_mixin.dart:740`）。

## 4. 假设逐条排除/存活（对照 B-03 证据 + 本次新增实测）

B-03 证据锚点：probe2（CDP 网络事件全量：register POST→RESP 200→紧接 error.ogg，**之后零 API 请求**；全会话**零 OPTIONS 预检**，含同样带 X-Device-* 头的 `GET /api/v1/user/settings→401`）；probe3（T+1s UI 快照中 SnackBar「关闭」**已出现**）；probe4（页面内 fetch 对照 200 + 完整 JSON）；probe5（`Runtime.exceptionThrown` 无 JS 异常）；proxy_trace（网关 200 + 完整响应体）。本次新增实测：网关在线，`POST register`（探针账号，见 §7）200 + `Content-Type: application/json`（uvicorn 透传，合法 JSON）；`OPTIONS` 预检 204 但 `Allow-Headers` 缺 `x-idempotency-key`。

| # | 假设 | 判定 | 依据 |
|---|---|---|---|
| a | 注册成功后**链式请求**失败被同一 SnackBar 展示 | **排除** | probe2：200 后零 API 请求即播 error.ogg；且链式请求（`GET /user/settings` 等）失败本应各走各的 SnackBar 通道，不会经 `fromDio` 进入 register 的 catch |
| b | 响应管线对 200 响应**解析/校验抛非 Dio 异常 → unknown** | **存活（第一）** | 机制完全吻合：assureDioException 覆盖窗口（§3.4）；观察文案=NetworkFailure=unknown 兜底；T+1s 快照证明错误在秒级（三超时地板 10s/30s/40s 全被排除）；静态已审：4 个响应拦截器、transformer（content-type 实测 application/json ⇒ 走 jsonDecode）、`assureResponse` cast、`Headers.fromMap`、adapter `onLoad→ResponseBody.fromBytes`、`getResponseHeaders`（防御式实现）——**均安全**。具体抛点需 E1 栈（候选：adapter XHR 事件互操作窗口、构建产物与源码差异） |
| c | Web adapter 差异（XHR 状态/超时包装） | **变体被排除** | dio_web_adapter 2.1.1 中 XHR `onError` → `DioExceptionType.**connectionError**`（`adapter_impl.dart:210-223`）→ 映射 **Offline 文案 ≠ 观察**；超时地板 10s/30s/40s vs T+1s。注意：dio <5.7 旧版 adapter 的 onError 曾产 unknown('XMLHttpRequest error.')——pubspec.lock 已锁 5.9.0+2.1.1，不适用 |
| d | 成功回调里后续状态写入抛异常被全局捕获为网络错误 | **排除** | 此类异常走 `from()`（非 DioException 路径），`from()` 不可能产出 NetworkFailure（§3.3）；且 saveTokens/UserModel.fromJson 在 repo 层、文案会是原始异常文本 |
| e | CORS/credentials 某一跳在 Web 失败 | **对本次复现排除；跨源条件缺陷实锤（第二）** | 复现会话零 OPTIONS（settings GET 与 register POST 都带自定义头）⇒ 同源 ⇒ CORS 未参与；且预检失败/CORS 响应头缺失路径都走 XHR onError ⇒ connectionError ⇒ Offline 文案 ≠ 观察。**但**：实测预检 `Allow-Headers` 缺 `x-idempotency-key`（`cors.go:21`，也无 `X-Current-Goal-ID`）⇒ 任何跨源部署（生产形态）下 R2-8 之后所有变更类 POST 死于预检 |

**综合排序**：H1 = (b) dio 成功管线非 Dio 异常被包装为 unknown（机制实证，抛点待栈）→ H2 = (e) 跨源预检缺陷（存在性实证，非本次复现根因）→ (a)(c)(d) 排除。

---

## 5. 判别实验（两个，均 LIGHT）

### E1（判别 H1 具体抛点）：fromDio/register catch 埋点抓栈 —— 一锤定音

在以下位置加 4 行临时日志（详见 fix_draft.patch 第 5 段，已含代码）：

1. `failures.dart:224` `fromDio` 入口：
   `debugPrint('[V3FIX17] fromDio type=${error.type} status=${error.response?.statusCode} error=${error.error} msg=${error.message}');`
   加 `Error.dumpStackTrace`/`StackTrace.current` 或在调用侧传入 stackTrace；
2. `auth_repository.dart:66` `on DioException catch`：同上打印 `e.type/e.error/e.response?.statusCode/e.stackTrace`；
3. `auth_repository.dart:68` 通用 `catch (e)`：打印 `e.runtimeType/$e`（若这里被命中即推翻 H1）；
4. `api_interceptor.dart:115` `AuthInterceptor.onRequest` 的 catch（当前只捕 StateError）：打印非 StateError 异常。

以 `flutter run -d chrome --profile` 复跑一次注册（B-03 同款 harness 亦可）。判读表：
- `error.error` 为 `TypeError`（type 'X' is not a subtype...）→ 解码/cast 族：栈会直接指向 `assureResponse`（dio_mixin.dart:740）或 repo 侧模型 fromJson ⇒ H1-cast 确认；
- `error.error` 为 `ClientException`/字符串 'XMLHttpRequest error.' ⇒ adapter 事件族（此时需复查构建产物 dio 版本是否被 lock 漂移）；
- `type=receiveTimeout/connectionTimeout` ⇒ 推翻「T+1s」读数，回到超时族（probe3 锚点需复核）；
- 通用 catch 被命中 ⇒ 推翻 fromDio 前提，转查模型解析。

### E2（判别 H2 跨源预检缺陷）：纯 curl 预检探测（本次已执行，结论可复现）

```bash
curl -sD - -o /dev/null -X OPTIONS "http://localhost:8080/api/v1/auth/register" \
  -H "Origin: http://127.0.0.1:8437" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type, x-device-id, x-device-name, x-device-platform, x-idempotency-key"
```
实测返回 204，但 `Access-Control-Allow-Headers: Authorization, Content-Type, ..., X-Device-Name, Accept, Accept-Language` **不含 `x-idempotency-key`**。判读：浏览器预检请求头集合 ⊄ Allow-Headers ⇒ 预检被浏览器本地拒绝 ⇒ POST 不发出（服务端零痕迹、无建号）⇒ 与 B-03 五连复现「POST 已达网关+建号」矛盾 ⇒ **证明它不是本次根因**；同时证明任何跨源部署必踩。修复见 patch 第 4 段（网关一行）。

---

## 6. 修复方案（详见 fix_draft.patch，未 apply）

1. **failures.dart**：unknown 分支不再一揽子映射 NetworkFailure——`error.error is TypeError/FormatException/ArgumentError` → `UnknownFailure(code:'PARSE_ERROR')`（保留原始错误）；`statusCode != null`（服务器已应答仍抛 unknown）→ `UnknownFailure`；仅无响应的真网络层异常保留 NetworkFailure。**效果**：即便管线异常复现，SnackBar 也不再谎报「网络不稳定」。
2. **auth_repository.register**：成功判定 = HTTP 2xx + `user` 可解析；`saveTokens` 降级为尽力而为（失败仅记日志，不抛）——**注册成功后续步骤失败不回滚 UI 到注册页**（用户可凭已建账号登录/进入应用，而不是重试撞「用户名已存在」）。`token` 解析因模型全 nullable 不会失败，防御分支保留。
3. **gateway cors.go**：allow-list 追加 `X-Idempotency-Key, X-Current-Goal-ID`（一行，网关侧；跨源部署 P1）。
4. **埋点**：§5-E1 四处日志（随 patch 交付，联调后可摘）。

---

## 7. 附：本次诊断留痕与说明

- 收尾 curl 探测时误发了一个真实注册 POST（`username=__ct_probe_nonexistent__`，响应 200/2475B ⇒ dev 库已建该探针账号）。属可弃测试数据，无后续请求；如需清理由主会话决定（C 档数据不在本 worker 删除权限内）。
- 证据目录中的 `b03_register_probe*.py` 脚本在本次诊断中途已被归档/移出（收尾时 `ls` 仅剩 .log）；本文对其行为的引用基于日志文件内容与诊断早期对 probe4 脚本的直接读取（页面内 fetch 用**相对路径** `/api/v1/auth/register` ⇒ 对照实验走页面同源，与 Dio 走 `ApiConstants.baseUrl` 不同源的事实已纳入拓扑推断）。
- 本 worktree 未改任何 mobile/lib 生产代码；未 commit；/tmp 无本任务产物。
