# ApiClient 全消费方超时与流式面审计报告（wt273-audit-apitimeout）

> 卡号 wt273 · C 线生产级移动网络面 · 2026-09-22
> 审计面：`mobile/lib/` 全库（dio 5.9.0 / package:http / gRPC / WebSocket 四体系）
> 背景：A11Y-BATCH2 修过 SSE 3 消费方豁免，但 ApiClient 其余消费方未系统盘点。本卡全量收口。

---

## 〇、回执五要素速览

1. **调用点全景计数**：Dio 实例 7（合规 7）｜dio 请求级 Options 9（合规 9）｜SSE/流式消费方 5（豁免到位 5/5，全部 Duration.zero 形态）｜package:http 裸调用面 5（**实锤缺陷 5，已修 5**）｜gRPC per-call 11（全部带超时）｜功能层 .timeout 闸约 15（全部有界）｜CancelToken 全库 **0**（系统性债务，见 §五）。
2. **实锤缺陷与修法**：package:http 直连面 5 处零超时裸调用（dart http 包无任何默认超时 → 弱网 future 永久 pending）——详见 §三；另修正 api_timeouts.dart 头部一处会误导再引入 `receiveTimeout: null` 的过时表述（文档级）。
3. **测试与守卫结果**：N37 守卫升级为 4 维度（新增 dim3 null 覆写陷阱、dim4 http 裸调用无总闸），self-test PASS、实扫 PASS（四维全 0/0，exit=0）；定向回归 `api_client_sse_timeout_test.dart` PASS；改动文件 `flutter analyze` 零新增告警（详见 §六）。
4. **资源峰值**：本卡全程 LIGHT（无模拟器/Gradle/浏览器）；flutter test 单文件单进程串行；swap 门槛前曾两次等待（开工 1288M 瞬时跌破 953M 后恢复再跑）；磁盘稳定 14Gi 空闲；收工清理清单见 §七。
5. **交接建议**：①CancelToken/请求生命周期收口建议立独立卡（SSE 3 面 + 长列表轮询面优先）；②file_upload 重试对 badResponse 全型重试可收窄为 5xx/网络型（低优先）；③chaos_control_dialog 内置硬编码 `X-Admin-Secret` 建议改注入（越界提示，未动）。

---

## 一、全景矩阵：调用点 × 超时来源 × 风险级

### 1.1 Dio 实例（7 个，全部经 ApiTimeouts 注册表）

| # | 实例 | 位置 | connect | receive | 来源 | 风险级 |
|---|---|---|---|---|---|---|
| 1 | ApiClient 主 dio | `core/network/api_client.dart:24` | 10s | 30s | `defaultConnectTimeout`/`defaultReceiveTimeout` | 绿 |
| 2 | auth 401 重放 dio | `core/network/api_interceptor.dart:78` | 10s | 30s | 同上（引用默认） | 绿 |
| 3 | agent 统计兜底 dio | `core/statistics/presentation/providers/agent_statistics_provider.dart:106` | 10s | 30s | 同上 | 绿 |
| 4 | capsule 统计兜底 dio | `.../capsule_statistics_provider.dart:110` | 10s | 30s | 同上 | 绿 |
| 5 | focus 统计兜底 dio | `.../focus_statistics_provider.dart:142` | 10s | 30s | 同上 | 绿 |
| 6 | 文件缓存 dio | `features/file/data/services/file_cache_service.dart:16` | 10s | 30s | 同上 | 绿 |
| 7 | 上传面 dio | `features/file/data/services/file_upload_service.dart:30` | **15s** | 30s | `uploadConnectTimeout` + 默认 receive | 绿 |

### 1.2 dio 请求级 Options 覆写（9 处）

| # | 调用点 | 覆写内容 | 来源 | 风险级 |
|---|---|---|---|---|
| 1 | `api_client.dart:91` getStream | `receiveTimeout: sseReceiveTimeout`（**Duration.zero**） | 注册表 | 绿 |
| 2 | `api_client.dart:169` postStream | 同上 | 注册表 | 绿 |
| 3 | `galaxy_repository.dart:89`（直连 dio 流） | 同上 | 注册表 | 绿 |
| 4 | `file_cache_service.dart:68` | bytes（继承 10s/30s） | 默认 | 绿 |
| 5-6 | `file_upload_service.dart:185,235` | contentType/followRedirects（继承上传面 15s/30s） | 默认 | 绿 |
| 7 | `user_repository.dart:1043`（ZIP 全量导出） | bytes（继承默认） | 默认 | 绿（注：大文件按块间隔计时，30s 为块间上限，语义正确） |
| 8 | `offline_dictionary_service.dart:153`（词典包下载） | bytes（继承默认） | 默认 | 绿（同上） |
| 9 | `client_observability_service.dart:175` | extra 防遥测递归（继承默认） | 默认 | 绿 |

`validateStatus`：全库 **0 处**（无自置状态码放行面）。
`receiveTimeout/sendTimeout/connectTimeout: null`：修复后 **0 处**（dim3 守卫冻结）。

### 1.3 SSE/流式消费方全集（5 面）

| 消费方 | 入口 | 豁免形态 | 存活性表达 | 风险级 |
|---|---|---|---|---|
| task_monitor | `task_monitor_screen.dart:106` → `getStream` | `sseReceiveTimeout`（zero） | 5s 轮询兜底（`startPolling`），流断不致盲 | 绿 |
| simulation run | `simulation_repository.dart:61` → `postStream` | 同上 | 消费方错误事件态 | 绿 |
| simulation continue | `simulation_repository.dart:99` → `postStream` | 同上 | 同上 | 绿 |
| enhanced_galaxy | `enhanced_galaxy_repository.dart:543` → `getStream`（带 Last-Event-ID） | 同上 | galaxy_provider 5s 重连定时器（`galaxy_provider.dart:451`） | 绿 |
| galaxy（旧仓内流） | `galaxy_repository.dart:81` 直连 `dio.get<ResponseBody>` | 同上（请求级覆写） | 上层消费 | 绿 |

**结论**：5/5 全部 `Duration.zero` 形态；全库已无 `receiveTimeout: null`（唯一残留是 api_timeouts.dart 注释里的历史表述，本卡已改写为警示性文字）。回退陷阱由守卫 dim3 冻结。

### 1.4 retry / backoff 面

| 重试点 | 触发条件 | 上限 | 退避 | 幂等性处理 | 风险级 |
|---|---|---|---|---|---|
| `RetryInterceptor`（`api_interceptor.dart:23`） | 502/503/504 | 3 次 | 500ms→1s→2s（有界） | cancel 不重试（`_shouldRetry`）；重放复用原 RequestOptions → **X-Idempotency-Key 随重放保持**，网关可去重 | 绿 |
| `IdempotencyInterceptor` | POST/PUT/PATCH/DELETE 自动加键 | — | — | 已有键不覆盖（重放不换键） | 绿 |
| 上传重试（`file_upload_service.dart:168,210`） | 任意 DioException | 3 次 | 1s→2s→4s（有界） | 预签名 URL 同 key 重传收敛；**注**：对 badResponse（含 4xx 过期）也重试，浪费但有界——建议收窄为网络型+5xx（低优先，未动） | 黄（低） |
| `RetryStrategy`/`CircuitBreakerRetryStrategy`（`core/services/retry_strategy.dart`） | 连接/超时类 + 408/429/5xx | 3 次，退避 clamp 10s | 500ms×1.5ⁿ 有界 | 消费方仅 enhanced_galaxy（断路器 5 连败开 30s） | 绿 |
| chat 发送重试（`chat_provider.dart:1405`） | 首事件守卫救援失败 | 2 次 | — | 重试换新 requestId（`${runId}_r1`），无双提交风险 | 绿 |

### 1.5 功能层超时（非 dio，N37 规则 4「面内语义、触碰即迁」口径，全部有界）

| 面 | 位置 | 值 | 风险级 |
|---|---|---|---|
| chat 流总闸 | `chat_provider.dart:1389` | 8min（超时→ErrorEvent 可重试） | 绿 |
| chat 首事件守卫 | `chat_provider.dart:177` | 30s | 绿 |
| WS 心跳/超时 | `websocket_chat_service_v2.dart:1403-1404` | 30s / 超时定时器 | 绿 |
| WS 重连退避 | 同上 `:1344` | 0.8s→12.2s 封顶表 + max attempts | 绿 |
| channel.ready | 同上 `:1771` | 10s | 绿 |
| plan guide 生成 | `plan_guide_generator.dart:69` | 2min 流总闸 | 绿 |
| modeling skip / planning | `modeling_chat_screen.dart:748,845` | 3s / 75s | 绿 |
| sync ACK | `sync_engine.dart:290,316` | 5s×2（SyncFailure 分类） | 绿 |
| gRPC per-call | `review_grpc_service.dart` ×10（30s；生成面 60s）+ `plan_review_grpc_service.dart:116`（30s） | **11/11 全带 timeout**（awk 括号配平核验无裸 CallOptions） | 绿 |
| openclaw http 探针 | `openclaw_connection_service.dart:849,947` | 8s×2 | 绿 |
| WeChat auth | `social_auth_service.dart:228` | 2min + cancelable | 绿 |
| 杂项 UI 级 | chat_screen 5s/12s、plan_detail 10s、audio 2s 等 | 有界 | 绿 |

### 1.6 package:http 直连面（本卡实锤缺陷所在，修复前 5 处零超时）

| # | 调用点 | 修复前 | 修复后 | 风险级 |
|---|---|---|---|---|
| 1 | `core/services/universal_share_service.dart:361` | **零超时** | `.timeout(shareCardDownloadTimeout)` | 红→绿 |
| 2 | `features/achievement/presentation/widgets/achievement_share_bottom_sheet.dart:195` | **零超时** | 同上 | 红→绿 |
| 3 | `features/user/presentation/widgets/achievement_share_dialog.dart:329` | **零超时** | 同上 | 红→绿 |
| 4 | `core/utils/chaos/chaos_control_dialog.dart:30`（dev） | **零超时** | `.timeout(chaosAdminCallTimeout)` | 黄→绿 |
| 5 | `core/utils/chaos/chaos_control_dialog.dart:54`（dev） | **零超时** | 同上 | 黄→绿 |

---

## 二、缺陷机理解释（为什么 dio 体系外的面全部漏网）

N37 守卫 dim1/dim2 只扫 dio 命名参数与 core/network 层；`package:http` 直连面既不出现 `receiveTimeout:` 字样也不在 network 层，天然绕过登记制。而 dart http 包 `IOClient` **没有任何默认超时**（连接、TLS、响应头、body 全程无看门）——dio 至少还有全局 10s/30s 兜底，http 包是真正的裸奔。这正是「守卫维度盲区=缺陷聚集地」的又一实例，故本卡把该模式本身固化为 dim4。

## 三、实锤缺陷清单（修复记录，全部 Read+Edit 逐处改，未用 shell sed）

### D1 分享面板永久 loading（生产面，用户必经路径）
- **位置**：`mobile/lib/core/services/universal_share_service.dart:361`（`downloadCardImage`）
- **复现逻辑**：打开 universal share 底部面板且 payload 带 `cardImageUrl` → `initState` → `_prepareShareCard` → `await downloadCardImage(...)` → 裸 `http.get`。弱网/服务端 accept 后 stall 时 future 永不完成 → `_isLoading` 永真 → 面板卡死，无任何错误呈现。
- **修法**：`.timeout(ApiTimeouts.shareCardDownloadTimeout)`（新登记常量 30s 整请求总闸）；TimeoutException 落入既有 `catch` → 返回 null → UI 走「Failed to download card」既有失败态。行为语义与下载失败完全同路。

### D2 成就分享底部面板下载悬挂（生产面）
- **位置**：`mobile/lib/features/achievement/presentation/widgets/achievement_share_bottom_sheet.dart:195`
- **复现逻辑**：同 D1 机理；调用方 `:172 await _downloadCardToTempFile(...)` 悬挂 → 分享流程停滞。
- **修法**：同常量；TimeoutException → 调用方 `:181 catch` → `_errorMessage` 用户可见失败态（与非 2xx throw 同路）。

### D3 成就分享对话框下载悬挂（生产面）
- **位置**：`mobile/lib/features/user/presentation/widgets/achievement_share_dialog.dart:329`
- **修法**：同常量；调用方 `:71-87 try/catch` 收敛为失败提示。

### D4 混沌面板 status 探测零超时（dev 面）
- **位置**：`mobile/lib/core/utils/chaos/chaos_control_dialog.dart:30`
- **修法**：`.timeout(chaosAdminCallTimeout)`；超时落既有 catch → debugPrint（dev 工具语义不变）。

### D5 混沌面板 config 设置零超时（dev 面）
- **位置**：`mobile/lib/core/utils/chaos/chaos_control_dialog.dart:54`
- **复现逻辑**：裸 `http.post` 悬挂 → `finally` 永不执行 → `_isLoading` 永真（按钮永久禁用）。
- **修法**：同常量；超时 → catch → 失败 SnackBar → finally 复位 loading。

### D6（文档级）api_timeouts.dart 头部过时先例表述
- **位置**：`mobile/lib/core/network/api_timeouts.dart` §流式豁免规则 2
- **问题**：仍以「先例：galaxy SSE 请求级 `receiveTimeout: null`」作为范型引用——该先例已被 A11Y-BATCH2 判为**无效豁免**（dio compose 回落 30s），原文照抄会误导后来者重新引入 null。
- **修法**：改写为警示性表述（「唯一合法写法是引用 sseReceiveTimeout 零值，禁写 null，守卫 dim3 冻结」）。纯注释，零行为。

## 四、登记表变更（ApiTimeouts）

新增两个常量（值与全局 receive 家族对齐取 30s，命名遵 `<face><Slot>Timeout` 制）：

| 常量 | 值 | 面 |
|---|---|---|
| `shareCardDownloadTimeout` | 30s（整请求） | 分享卡片图下载 ×3（package:http） |
| `chaosAdminCallTimeout` | 30s（整请求） | 混沌管理面 ×2（dev，package:http） |

说明：package:http 无 per-phase 拆分，只能以 `.timeout()` 表达整请求预算，故登记表 Slot 记为「整请求总闸」。头部矩阵已补两行。

## 五、系统性发现（未在本卡修，建议立卡）

1. **CancelToken 全库为零**（`grep -r CancelToken mobile/lib` = 0 处）：页面离开不取消在飞请求。现状缓解：SSE 消费方靠 stream subscription cancel（task_monitor `stopPolling`、galaxy_provider dispose :400-402）传导至 dio 关连接；chat 靠 `isCurrentRequest()` 丢弃迟到事件。但普通 REST（统计三 provider、列表拉取等）离开页面后仍跑满 30s 并可能把陈旧响应写进新页面状态。建议独立卡：ApiClient 增加 `cancelToken:` 透传 + 页面路由生命周期接线，优先统计三 provider 与列表轮询面。
2. **file_upload 重试全型重试**：对 badResponse（含预签名过期 4xx）也退避重试 3 次，浪费但对齐幂等语义（同 key 收敛），建议收窄重试类型集合。
3. **chaos_control_dialog 硬编码 `X-Admin-Secret: 'sparkle_2025'`**：dev 工具内嵌凭据，建议改构建注入（越界提示，本卡未动）。
4. **auth 401 重放 dio 不带 Retry/Idempotency 拦截器**：重放遇 502 不重试（可接受——避免刷新风暴叠加重试风暴），仅记录口径。

## 六、守卫补强与验证结果

### N37 守卫升级（`scripts/guards/check_n37_timeout_registry.py`）
- **dim3 `nullTimeoutOverrideLiterals`**：`(connect|receive|send)Timeout: null` 全库冻结为零——把 dio 5.9.0 `Options.compose` 的「显式 null 回落全局默认」陷阱机检化（A11Y-BATCH2 前车之鉴）。
- **dim4 `unboundedHttpPackageCalls`**：`http.<verb>(` 语句窗（括号配平→首个 depth-0 `;`，2000 字符防御帽）内无 `.timeout(` 即违例——把 package:http 裸奔模式机检化。基线（修复后实测）双维登记为零。
- self-test 新增 clean（带 .timeout 的 http.get、注释行豁免）/dirty（null 覆写 ×1、裸 http ×2）用例，PASS。
- 基线 `n37_timeout_registry_baseline.json` 扩展为 4 维（`--update-baseline` 同步支持）。

### 验证记录
| 项 | 结果 |
|---|---|
| `check_n37_timeout_registry.py --self-test` | PASS（exit=0，`; echo exit=$?` 判定，未用 tail 吞码） |
| `check_n37_timeout_registry.py` 实扫 | PASS：四维 0/0, 0/0, 0/0, 0/0（exit=0） |
| 定向回归 `flutter test test/core/network/api_client_sse_timeout_test.dart` | PASS 5/5（单文件单进程 `--concurrency=1`；真实 exit code 经 `${pipestatus[1]}` 判定——首次因 worktree 缺 `lib/gen/` 生成物编译失败，在**工作树内** `make proto-gen` 后通过；产物 gitignore 不入库） |
| `flutter analyze` 改动 dart 文件（5 个） | 零新增告警：HEAD 克隆基线对照法（`git clone <worktree> /tmp/<名字>-baseline`，同口径 analyze），前后均 26 条既有 info，逐条同规则仅行号平移 |
| 回归对比法 | 修复仅新增 `.timeout()` 包裹 + 常量登记：成功路径行为不变；失败路径从「永久悬挂」变为「30s 后走既有失败分支」，无既有测试依赖悬挂行为 |

## 七、资源与收工清理

- 全程 LIGHT：无模拟器/Gradle/浏览器；`flutter test` 串行单文件；swap <1.2G 时两度暂缓 flutter 步骤，恢复后执行。
- 收工删除：`mobile/build`、`mobile/.dart_tool`（flutter test/analyze 产物）、`/tmp` 本卡自产物（无遗留进程）。
- 保留：本 REPORT.md（v3-output 规范目录）、正式代码改动、守卫与基线改动；`changes.patch` 由主会话合入管线生成。
