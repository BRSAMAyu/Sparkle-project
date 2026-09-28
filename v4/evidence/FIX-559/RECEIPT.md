# V3-FIX-559 Receipt — FastAPI /docs CSP 自锁修复（自托管 swagger-ui/redoc）

- 卡号：V3-FIX-559（P3）｜分支：`agent/v4/fix559`（wtF559，基于 main@5a00ee3d）｜日期：2026-09-28
- 缺陷（V4-B04 2026-09-28 发现）：FastAPI /docs、/redoc 引用 jsdelivr CDN 资产并被本应用
  自身 CSP（`script-src`/`style-src 'self'`）拦截，页面对任何访客不可渲染；B04 只能以
  setBypassCSP + 逐字节相同本地副本完成采集。

## 1. 定位

- CSP 设置面：`backend/app/main.py` `SecurityHeadersMiddleware`（全响应施加；
  DEBUG 分支 `script-src 'self' 'unsafe-inline' 'unsafe-eval'`，非 DEBUG
  `script-src 'self'`——两分支都不含 jsdelivr，故两种模式均自锁）。
- 受影响资产清单（修前 `/docs`/`/redoc` 实捕，见 `docs_html_before_fix.html`）：
  | 页面 | 引用 | 被哪条指令拦截 |
  | --- | --- | --- |
  | /docs | `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css` | style-src 'self' |
  | /docs | `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js` | script-src 'self' |
  | /docs | `https://fastapi.tiangolo.com/img/favicon.png` | img-src 'self' data: |
  | /docs | 模板内联 `<script>`（SwaggerUIBundle 初始化） | script-src（非 DEBUG 无 unsafe-inline） |
  | /redoc | `https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js` | script-src 'self' |
  | /redoc | `https://fonts.googleapis.com/css?family=Montserrat…` | style-src 'self' |
  | /redoc | `https://fastapi.tiangolo.com/img/favicon.png` | img-src 'self' data: |

## 2. 修法选择：自托管（方案 A 的加强版：初始化脚本外置）

选择**自托管全部文档资产 + 外置初始化脚本**，CSP 一字未动、中间件零修改。

理由：
1. 任务优先级明示优先自托管（保 CSP 严格、离线可用）。实测发现仅自托管 css/js 不够——
   FastAPI 内置模板还有页面内联 `<script>` 初始化，非 DEBUG CSP 同样拦它；若为它放行
   `unsafe-inline`（哪怕仅 /docs 路由）就是削弱安全口径。故把初始化逻辑外置为同源静态
   `swagger-init.js`，动态参数经 `<script type="application/json">` 数据块传入
   （非执行型数据块不受 script-src 约束），页面在 `script-src 'self'` 下完整可渲染。
2. jsdelivr 收窄放行方案（备选）会引入永久第三方 script 来源（供应链/离线双风险），
   且 /redoc 还有 fonts.googleapis.com 需要二次放行——放行面不成比例，弃用。
3. ReDoc 默认模板的 Google Fonts 外链随自托管一并移除（回退系统字体，纯外观差异，
   换取 style-src 不放行第三方字体源）——已在本 receipt 如实披露。

改动面（全部新增为主，最小侵入）：
- 新增 `backend/app/static/docs/`：swagger-ui.css、swagger-ui-bundle.js、
  redoc.standalone.js、favicon.png（sha256 与来源见该目录 `LICENSES.md`；其中
  swagger-ui 两件资产与 V4-B04 逐字节核验副本 sha256 完全一致，构成字节锚）、
  swagger-init.js（手写外置初始化）、LICENSES.md。
- 新增 `backend/app/api/docs_pages.py`：/docs、/redoc 页面模板（自托管资产 +
  JSON 数据块传参 + 无内联可执行脚本）。
- 修改 `backend/app/main.py`：`docs_url=None, redoc_url=None`，改挂自定义路由
  `/docs`、`/docs/oauth2-redirect`（保留上游默认路由面）、`/redoc` + `/static`
  StaticFiles 挂载；CSP 中间件未动。
- 新增回归钉 `backend/tests/unit/test_docs_csp_selfhost.py`（14 用例）。
- 未触碰：.env、密钥、backend/app/gen（worktree 内经 `make proto-gen` 按正规入口
  重新生成、保持 gitignored 不入库）、proto/迁移。

## 3. 可失败性验证（真实访客视角，无任何 CSP bypass）

环境：`SECRET_KEY=dummy DATABASE_URL=sqlite+aiosqlite:///./.fix559_docs_probe.db DEBUG=false`
uvicorn :8777（exit code 0，启动成功）。

逐项断言（全录 `verification_guest_view.txt`，exit code 0）：
1. `GET /docs` → 200；CSP 头保持 `script-src 'self'; style-src 'self'` 严格原样；
2. HTML 资产引用全部同源：`http(s)` 外链数 = **0**；可执行内联 `<script>` 数 = **0**；
3. `/redoc` 同口径（外链 0、无内联可执行脚本）；
4. 页面引用的全部 8 个目标（5 资产 + /openapi.json + /redoc + /docs/oauth2-redirect）
   逐个 curl → 全部 **200**；
5. 服务端出的 swagger-ui.css / swagger-ui-bundle.js / redoc.standalone.js sha256
   与 B04 字节锚完全一致（`1ac324f7…9aa6321` / `62df5415…a63edc2f` / `dcaf7661…f89500b`）；
6. DEBUG=true 模式复核：`script-src 'self' 'unsafe-inline' 'unsafe-eval'` 下页面同版式
   加载，资产同路径 200（外置脚本不依赖 unsafe-inline，两分支皆兼容）。

局限（如实披露）：本会话 subagent 无浏览器工具，未能做像素级截图复验；按卡面给定的
验收口径（curl 拉 HTML 断言资产指向本地 + CSP 头不再拦截 + 资产 200 可达）已全数满足，
且 B04 截图流程所依赖的「逐字节相同本地副本」即本次入库的同一字节锚。

## 4. 测试与静态检查（exit code 均 0）

- 新增回归钉：`SECRET_KEY=ci-test-key DATABASE_URL=sqlite:// pytest tests/unit/test_docs_csp_selfhost.py -q`
  → **14 passed**（页面同源断言、无可执行内联脚本、CSP 保持严格、资产 200、
  sha256 字节锚、oauth2-redirect 路由面）。
- 影响面测试（同一环境变量口径，全部绿）：
  | 批次 | 命令 | 结果 |
  | --- | --- | --- |
  | 回归钉 | `pytest tests/unit/test_docs_csp_selfhost.py -q` | **14 passed** |
  | import app.main 的 unit 测试 | `pytest tests/unit/test_startup_smoke.py tests/unit/test_theater_idor.py tests/unit/test_logging_file_sink.py -q` | **26 passed** |
  | 同族（theater seed + lifespan bus） | `pytest tests/core/test_lifespan_event_bus_redis_unavailable.py tests/unit/test_theater_seed_and_accuracy.py -q` | **50 passed** |
  | lifespan/core 装配面 | `pytest tests/core/test_shutdown_invalidation_drain_wiring.py tests/core/test_event_bus_lifespan_shutdown.py tests/core/test_lifespan_event_bus_redis_unavailable.py -q` | **7 passed** |
  | API + 契约面 | `pytest tests/api tests/contract -q` | **753 passed, 5 skipped**（6m02s） |
  - 合计影响面：**850 passed, 5 skipped, 0 failed**（lifespan bus 文件在两批各跑一次，去重后计入一次）。
- 范围声明（如实）：`tests/unit` 全目录 958 个测试文件，量级为数小时，超出小卡
  成比例边界，未整体跑完（尝试 45 分钟后按边界停跑）；影响面收敛口径取
  「import app.main 的全部测试文件 + tests/api + tests/contract + 新增回归钉」，
  均绿。无既有失败被本卡引入或掩盖。
- `ruff check`（main.py + docs_pages.py + 测试）→ All checks passed；
- `black --check` → 本卡新增/修改行全过。main.py 既有行存在先于本卡的黑格式漂移
  （lifespan 等处），不属本卡范围、未顺手重排，保持 diff 最小。

## 5. 测试计数与提交

- 新增用例：14；影响面合计 850 passed / 5 skipped / 0 failed。
- commit：见分支 `agent/v4/fix559`（不 push）；台账 DYNAMIC_ISSUES.md 的
  V3-FIX-559 行状态列改 `FIXED@<sha>`（sha 见下方回填）。

**Commit（代码+资产+receipt）：见 git log；台账回填 sha：见 v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-559 行。**
