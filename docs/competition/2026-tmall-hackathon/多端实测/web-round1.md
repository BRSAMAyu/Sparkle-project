# Web 浏览器走查 · Round 1

- 日期：2026-09-18 晚
- 走查人：主 agent（ZCode）
- 环境：`flutter run -d web-server --web-port 8321`（debug 构建，Flutter 3.41.3），Chrome 1280×720；后端栈网关 :8080 / FastAPI :8000 / gRPC :50051 / PG / Redis / MinIO 全部在跑
- 方式：Browser Use（CDP 级）+ DOM 解剖 + 网关日志交叉验证

## 结论 TL;DR

**Web 游客旅程断在「认证成功 → 会话持久化/导航」最后一环。** 后端全链路健康（guest 200 + profile 200 + 完整种子画像数据），但前端：登录请求成功后 UI 不跳转，刷新后 `isLoggedIn=false`（token 未持久化或被清除）。另发现后端空凭据登录返回 200/500（应 401）等 6 项缺陷。

## 游客旅程逐步结果

| 步骤 | 结果 | 证据 |
|---|---|---|
| 加载应用 | ✅ 3-5s 出登录页，路由 `/#/login` | 截图 01 |
| 表单渲染 | ⚠️ 可见但语义树残缺（见 F-1） | domSnapshot 仅 1 textbox |
| 后端连通（CORS） | ✅ 页面内 fetch `/auth/guest` 200 + access_token | evaluate fetch |
| 点击 Continue as Guest（坐标） | ❌ 坐标点击全部不达（F-2） | 网关日志零请求 |
| 键盘序列触发 guest | ✅ `POST /auth/guest → 200`（1.4s） | 网关日志 19:44:11 |
| token 持久化 | ❌ localStorage 无 token（secure storage web 实现疑点）；刷新后引导期零 auth 请求 → `isLoggedIn=false` | 纯 reload 日志为空 |
| UI 导航 | ❌ 200 后停留 `/#/login`，无错误提示、无跳转 | 截图 + URL |
| 会话恢复（自动） | ❌ `checkAuthStatus` 判定未登录 | 同上 |

## 发现缺陷清单

### W-1 · P1 · 登录/游客认证成功后 UI 不跳转
- 现象：`POST /auth/guest → 200` 后 URL 钉死 `/#/login`，无错误 Snackbar
- 疑因（按嫌疑排序）：
  1. `saveTokens`（flutter_secure_storage）在 web 平台写入失败/异步未决 → `getAccessToken()` 返回空 → `authGuestTokenFailed` 异常 → `_failedAuthState` 把状态打回未认证（静默）
  2. `login()` 与引导期 `checkAuthStatus()` 状态竞态：login 的 `finally copyWith` / catch `_failedAuthState` 覆盖并发成功态
- 复现：键盘 Tab×3+Enter 于登录页（或修好点击后点 Continue as Guest）→ 观察网络 200 而界面不动
- 定位文件：`mobile/lib/features/auth/presentation/providers/auth_provider.dart`（loginAsGuest 247-273 / checkAuthStatus 105-147）、`auth_repository.dart`（saveTokens/_readToken）

### W-2 · P1 · token 未持久化（或登录后被清除）
- 纯刷新（不按任何键）后引导期零 auth 请求 ⇒ `isLoggedIn()` false ⇒ secure storage 空
- 与 W-1 同根（saveTokens web 失败）或登出清理误触发

### W-3 · P1 · 后端空凭据 login 返回 200（健康时）/ 500（引擎毒化时）
- 19:40:17 空用户名+空密码 `POST /auth/login` → **500**（引擎旧进程状态）→ 引擎重启后同样请求 **200**
- 正确语义应为 400/401；200 意味着凭据校验缺失或兜底用户返回——**安全审查项**
- 另：Android 端实测同窗口撞出 `POST /predictive/realtime-next-step → 500`（另一条独立 500，待 Android 员报告交叉）

### W-4 · P2 · Enter 键双路径触发
- 登录页一次 Enter 同时产生 `login` 与 `guest` 两个 POST（19:44:10/11）
- 疑因：`flt-text-editing-host` 内真实 `<form>`+隐藏 `<input type=submit>` 原生提交与 Flutter `onFieldSubmit` 双通道
- 影响：意外请求、状态竞态放大（W-1 疑因 2）

### W-5 · P2 · Flutter web 语义树残缺（无障碍）
- 整页仅暴露 1 个匿名 textbox + 隐藏 Submit 按钮；焦点遍历才懒生成节点
- 屏幕阅读器完全不可用登录表单；`Semantics(label:)` 缺失（输入框无 accessible name）
- 波及测试自动化（语义点击不可行）

### W-6 · P2 · `flt-glass-pane` 0×0 —— 坐标点击穿透
- CanvasKit 事件层玻璃面板渲染为 0×0，真实指针事件无法命中 Flutter 按钮（自动化点击全落空）
- 用户侧是否受影响待查（真实鼠标事件路径可能与合成事件不同）；至少无障碍/自动化路径被断

### W-7 · P3 · UI/UX（移交 Aurelia 批次 3）
- **界面全英文**（Username/Password/Login/Continue as Guest…）：中文竞赛产品在 en locale 浏览器下无中文回退——需默认 zh 或强制 zh
- 登录表单拉满 1176px 无 max-width 约束（桌面端观感差）
- 登录页无 logo/应用名/品牌标识（仅星云光晕背景）
- 第三方登录按钮（Google/Apple/微信）为死端

### W-8 · 事故记录（非产品缺陷，运维）
- 网关 `go run` stdout 日志无轮转涨至 **7.7GB**，磁盘可用 4.6G 触险；已截断+重启+换新日志
- 引擎 `grpc_server.py` **双进程**（旧进程未杀又起新的）导致 guest 502/profile 401 假象；重启纪律：先 `pkill -f grpc_server` 再启动
- 以上两条已写入 disk_guard 待办与接力日志

## 交叉验证记录（后端健康面）

- `POST /auth/guest?guest_id=*` → 200 + access_token/refresh_token/token/user 四键完整（多次）
- `GET /profile/context`（游客 Bearer）→ 200 + 完整种子画像（偏好/知识摘要/弱点列表）
- CORS preflight OPTIONS → 204 正常
- 结论：**Web 游客模式问题全部在前端会话层，后端零缺陷（除 W-3）**

## 建议修复顺序

1. W-1+W-2（同一专项：web secure storage 落盘诊断 + 登录态竞态收口）——解锁 Web 端全旅程
2. W-3（后端凭据校验 + 500 语义，安全项）
3. W-4（表单双触发）
4. W-5/W-6（a11y + 事件层，可与 Aurelia 批次 3 合并）
5. W-7 随批次 3

## 截图存档

`/Users/brsama/code/GitHub/Sparkle-sysrev/screenshots/web/`（本轮关键帧：01-登录页全览、02-按钮区、03-填写态、04-认证后停留态）
