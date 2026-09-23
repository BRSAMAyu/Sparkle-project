/// N37 超时参数单一事实源（弱网参数登记制）。
///
/// 来源：A-SPEC6 面2 差距③（v3-output/A-SPEC6/REPORT.md OF-G5）——Dio 全局
/// 超时一刀切（connect 10s / receive 30s）且常量四处自立，无单一事实源。
/// 本卡（TIMEOUT-SOURCE）按**数值守恒**收敛：只归一引用，不改任何现行值。
///
/// ## 登记表（现状矩阵 @ 基线 04904b54，全库 grep 实测）
///
/// | 面 | connect | receive | send | 登记点 |
/// |---|---|---|---|---|
/// | 全局默认（ApiClient 全局 Dio） | 10s | 30s | 未设 | `defaultConnectTimeout` / `defaultReceiveTimeout` |
/// | auth 401 重放 Dio（无鉴权拦截器） | 10s | 30s | 未设 | 同上（引用默认） |
/// | 统计三 provider 兜底 Dio | 10s | 30s | 未设 | 同上（引用默认） |
/// | 文件缓存 Dio | 10s | 30s | 未设 | 同上（引用默认） |
/// | 上传面 Dio | **15s** | 30s | 未设 | `uploadConnectTimeout` + 默认 receive |
/// | SSE 流（ApiClient getStream/postStream + galaxy 请求级覆写） | 继承 10s | **Duration.zero（dio 零值=不挂接收看门）** | — | `sseReceiveTimeout` |
///
/// SSE 豁免覆盖面（全库 getStream/postStream/dio.get(stream) 消费方 @ 基线
/// a7733e2a）：task_monitor（`/background-tasks/stream/events`）、simulation
/// （run/stream + sessions/{id}/continue/stream）、enhanced_galaxy（事件流）、
/// galaxy（galaxy_repository 自带同源请求级覆写）。A11Y-BATCH2（wt260）前三方
/// 未接豁免，静默 >30s 会被全局 receiveTimeout 掐断；同卡修正了 null 先例
/// 因 dio compose 合并回落 30s 的无效豁免——详见 v3-output/A11Y-BATCH2/REPORT.md。
///
/// sendTimeout：全库所有 Dio 实例均未设（Dio 默认无限制）——**不存在已生效的
/// sendTimeout 值，故不立常量**；新面若要设，必须先在此登记（见下）。
///
/// ## N37 登记制（新超时面准入口径）
///
/// 1. **登记**：新增/修改网络超时必须在 [ApiTimeouts] 立常量并更新上方登记表，
///    命名 `<face><Slot>Timeout`（face=default/upload/sse/…，Slot=Connect/Receive/Send）；
///    值与默认相同的面直接引用默认常量，不另立同值常量。
/// 2. **流式豁免**：AI 生成/长推理/事件流类**禁依赖 receiveTimeout 表达超时**——
///    流式域以心跳/事件超时为准（先例：galaxy SSE 请求级 `receiveTimeout: null`
///    + ws 心跳 30s/超时 60s）。流式静默期大于 30s 会被全局 receiveTimeout 误杀。
/// 3. **机检**：`scripts/guards/check_n37_timeout_registry.py`（N9 家族形制，
///    基线冻结只降不升）——network 层与全库 Dio 超时命名参数位出现裸
///    `Duration(...)` 字面量即违例，唯一合法写法是引用本文件常量。
/// 4. **非 Dio 超时**（gRPC per-call timeout、ws 心跳/退避、聊天流 8min 总闸、
///    sync ACK 5s 等功能层超时）属面内语义，登记在 REPORT 现状矩阵、触碰即迁，
///    本卡不迁移不冻结。
class ApiTimeouts {
  const ApiTimeouts._();

  /// 分级默认 connect：全库既定事实值 10s（ApiClient / auth 重放 / 统计三
  /// provider / 文件缓存四处同值收敛）。
  static const Duration defaultConnectTimeout = Duration(seconds: 10);

  /// 分级默认 receive：全库既定事实值 30s（同上四处 + 上传面 receive 同值）。
  static const Duration defaultReceiveTimeout = Duration(seconds: 30);

  /// 上传面覆写 connect：大文件上传握手/建连预算放宽为 15s（现状唯一偏离
  /// 默认值的 live 面；file_upload_service.dart）。
  static const Duration uploadConnectTimeout = Duration(seconds: 15);

  /// 流式面请求级关闭 receiveTimeout（dio 零值 = 不挂接收看门）。
  ///
  /// 先例：galaxy 事件流（galaxy_repository.dart）——SSE 事件稀疏，全局 30s
  /// receiveTimeout 会把静默期误判为超时断流（dio 按数据块间隔计时）。存活
  /// 性交给心跳/事件超时表达。现统一收口在 ApiClient.getStream/postStream
  /// （全部 SSE 消费方：task_monitor / simulation / enhanced_galaxy / galaxy）。
  ///
  /// 为什么是 `Duration.zero` 而非 `null`（A11Y-BATCH2/wt260 修正，dio 5.9.0
  /// 实测源码）：`Options.compose` 合并规则是
  /// `receiveTimeout: perRequest ?? baseOptions.receiveTimeout`——请求级传
  /// 显式 `null` 会**回落到全局 30s**（此前 null 先例实为无效豁免的潜伏债，
  /// galaxy 靠引擎 20s 心跳掩盖）；而 dio `handleResponseStream` 对
  /// `receiveTimeout <= Duration.zero` 直接不挂接收超时看门。故「关闭」的
  /// 有效表示是零值。禁止改成裸 `Duration(...)` 字面量（N37 dim1）。
  static const Duration sseReceiveTimeout = Duration.zero;
}
