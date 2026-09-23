library;
import 'package:sparkle/l10n/app_localizations.dart';

/// 异常→人话映射单一 owner（N16，A-SPEC3 §6.2/§6.4；SPEC DL-R3 §6.4 词典域）。
///
/// 形制裁决（N16）：**类型化枚举映射为正解**——形制迁自 galaxy 私有的
/// `_galaxyLoadErrorMessage`（`GalaxyErrorType → arb key`，全库唯一不依赖
/// 异常文本形态的正解先例，SPEC-C #4 已验收）。条款（新代码即生效）：
/// - 任何 feature 域**禁再建私有「异常→文案」映射**；异常文本
///   （`toString()` 形态）的模式匹配只允许遗留兼容层 [categorizeUiError]
///   一处持有（判定表，判定集漂移是 §9.4-1 实证差距）；
/// - 类型化错误实现 [TypedUiError] 自报类别（零文本嗅探），文案由
///   [uiErrorMessage] 按类别出 arb 词条；
/// - 域若需本域专属文案（如 galaxy 的数据安全承诺句），只准做
///   「类别 → 本域 arb key」的**纯绑定**（switch 直出，无判定逻辑），
///   判定一律走本文件；
/// - `[ERR-*]` 诊断码（A-3 diagnosability）由 core/errors/user_facing_error.dart
///   附加，降为次级显示（文案尾缀），不与首读文案混排判定。

/// 用户可感知的错误类别（类型化映射的枚举轴）。
enum UiErrorCategory {
  /// 网络不通/连接失败（含对端断开）。
  network,

  /// 服务端过载/熔断/暂不可用（可稍后重试）。
  serviceDegraded,

  /// 超时。
  timeout,

  /// 鉴权失败。
  auth,

  /// 服务端错误。
  server,

  /// 资源不存在。
  notFound,

  /// 限流。
  rateLimit,

  /// 格式/校验错误。
  format,

  /// N35（A-SPEC6）：离线写操作已入队——这不是错误，是「已排队待同步」
  /// 的诚实三态（排队成功必须有排队的样子，禁落 unknown 通用错误通道）。
  offlineQueued,

  /// 未分类。
  unknown,
}

/// 类型化错误自报类别接口（N16 推荐形制：不依赖异常文本形态）。
///
/// 领域错误类型（如 galaxy `GalaxyError`）实现本接口后，即完成
/// 「异常 → 类别」的类型化判定；文案翻译统一走 [uiErrorMessage]。
abstract class TypedUiError {
  /// 本错误的用户可感知类别。
  UiErrorCategory get uiErrorCategory;
}

/// 类别 → arb 人话词条的唯一映射表（首读文案）。
///
/// 词条复用既有 `error*` arb 家族（与 UserFacingError 同源），zh/en 双语
/// 由 arb 纪律保障；`unknown` 落最笼统的兜底句，不猜测语义。
String uiErrorMessage(AppLocalizations l10n, UiErrorCategory category) {
  switch (category) {
    case UiErrorCategory.network:
      return l10n.errorNetworkDetail;
    case UiErrorCategory.serviceDegraded:
      // 服务过载/熔断的通用口径与 server 错误共享词条（「服务器出现问题」）。
      return l10n.errorServerDetail;
    case UiErrorCategory.timeout:
      return l10n.errorTimeoutDetail;
    case UiErrorCategory.auth:
      return l10n.errorAuthDetail;
    case UiErrorCategory.server:
      return l10n.errorServerDetail;
    case UiErrorCategory.notFound:
      return l10n.errorNotFoundDetail;
    case UiErrorCategory.rateLimit:
      return l10n.errorRateLimitDetail;
    case UiErrorCategory.format:
      // 格式/校验错误不向用户暴露技术细节，落通用兜底（与既有口径一致）。
      return l10n.errorUnknownDetail;
    case UiErrorCategory.offlineQueued:
      // N35：入队成功的人话=「什么发生了+接下来会怎样+无需用户动作」。
      return l10n.errorOfflineQueuedDetail;
    case UiErrorCategory.unknown:
      return l10n.errorDefaultTitle;
  }
}

/// 遗留兼容层：非类型化 `Object` 的类别判定（字符串模式匹配）。
///
/// 【全库唯一】字符串判定表——模式集与判定顺序同改造前的
/// `UserFacingError.from` 逐字一致（判定集漂移双写是 A-SPEC3 §2.2 EE-G4
/// 实证差距：`CLIENT_CLOSED` 只在一处、中文模式只在另一处；收敛后
/// 两入口共享本表，一致性由 `error_lexicon_test` 钉住）。
/// 类型化新代码勿入：实现 [TypedUiError] 自报类别即可。
UiErrorCategory categorizeUiError(Object? error) {
  if (error == null) {
    return UiErrorCategory.unknown;
  }
  // 类型化错误自报类别优先（N16 正解形制；N35：OfflineEnqueuedException
  // 据此落 offlineQueued，不再被字符串判定表误判成 unknown 通用错误）。
  if (error is TypedUiError) {
    return error.uiErrorCategory;
  }
  final message = error.toString();

  // Common network patterns
  if (_containsAny(message, [
    'SocketException',
    'Connection refused',
    'Connection timed out',
    'network',
    'Network',
    'CLIENT_CLOSED',
  ])) {
    return UiErrorCategory.network;
  }

  // Auth patterns
  if (_containsAny(message, [
    '401',
    '403',
    'Unauthorized',
    'Forbidden',
    'token',
    'Token expired',
  ])) {
    return UiErrorCategory.auth;
  }

  // Timeout patterns
  if (_containsAny(message, ['TimeoutException', 'timed out', 'timeout'])) {
    return UiErrorCategory.timeout;
  }

  // Server errors
  if (_containsAny(message, ['500', '502', '503', '504', 'Internal Server'])) {
    return UiErrorCategory.server;
  }

  // Not found
  if (_containsAny(message, ['404', 'Not Found', 'not found'])) {
    return UiErrorCategory.notFound;
  }

  // Rate limiting
  if (_containsAny(message, ['429', 'rate limit', 'Rate limit', 'too many'])) {
    return UiErrorCategory.rateLimit;
  }

  // Format/validation errors
  if (_containsAny(message, ['FormatException', 'invalid', 'Invalid'])) {
    return UiErrorCategory.format;
  }

  return UiErrorCategory.unknown;
}

bool _containsAny(String source, List<String> patterns) {
  for (final pattern in patterns) {
    if (source.contains(pattern)) return true;
  }
  return false;
}
