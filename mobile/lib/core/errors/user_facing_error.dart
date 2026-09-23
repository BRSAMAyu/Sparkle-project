import 'package:flutter/foundation.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Strips internal error details and returns a user-safe error message.
///
/// Use this instead of `e.toString()` in catch blocks to prevent
/// stack traces, class names, and internal details from reaching the UI.
///
/// All user-facing messages are localized via ARB keys (error*).
///
/// **N16（A-SPEC3 §6.2/§6.4）映射单源条款**：异常→人话映射的唯一 owner 是
/// core/display/lexicon/error_lexicon.dart（类型化枚举映射 = 正解形制，
/// 判定表 [categorizeUiError] / 文案表 [uiErrorMessage]）。本类降为
/// **遗留兼容层**——吃任意 `Object` 的入口：判定走共享判定表、文案走
/// 共享词条表，仅额外附加 `[ERR-*]` 类别码。新域禁再建私有映射；
/// 类型化错误请实现 `TypedUiError` 自报类别。
///
/// A-3 diagnosability (client-side aid): every mapped message carries a
/// stable `[ERR-*]` category code so field reports — even a bare
/// screenshot of a release build — can be traced to a failure category.
/// The original exception is additionally surfaced via [debugPrint] in
/// debug builds only (silent in release), e.g. into logcat during
/// on-device testing.
class UserFacingError {
  UserFacingError._();

  /// Stable short category codes appended to the localized copy.
  ///
  /// Keep these terse and stable: they are the join key between field
  /// reports and the error taxonomy above.
  static const String _codeNetwork = 'ERR-NET';
  static const String _codeAuth = 'ERR-AUTH';
  static const String _codeTimeout = 'ERR-TIMEOUT';
  static const String _codeServer = 'ERR-SERVER';
  static const String _codeNotFound = 'ERR-NOTFOUND';
  static const String _codeRateLimit = 'ERR-RATELIMIT';
  static const String _codeFormat = 'ERR-FORMAT';
  static const String _codeUnknown = 'ERR-UNKNOWN';

  /// Categories of errors that map to user-friendly messages.
  ///
  /// N16：判定与文案均单源自 error_lexicon（共享判定表，两入口一致性由
  /// `mobile/test/core/display/lexicon/error_lexicon_test.dart` 钉住）；
  /// 本方法只保留「文案 + `[ERR-*]` 码」拼装职责。
  static String from(Object error) {
    // Debug-only root-cause aid: the raw exception never reaches the UI,
    // but a developer/tester running a debug build gets it in the log.
    if (kDebugMode) {
      debugPrint('[UserFacingError] ${error.runtimeType}: $error');
    }
    final category = categorizeUiError(error);
    return _withCode(uiErrorMessage(S, category), _codeFor(category));
  }

  /// 类别 → `[ERR-*]` 稳定码（A-3）。`serviceDegraded` 仅由类型化错误
  /// 自报产生（字符串判定表不产出），归入服务端故障同码。
  static String _codeFor(UiErrorCategory category) => switch (category) {
        UiErrorCategory.network => _codeNetwork,
        UiErrorCategory.auth => _codeAuth,
        UiErrorCategory.timeout => _codeTimeout,
        UiErrorCategory.server => _codeServer,
        UiErrorCategory.serviceDegraded => _codeServer,
        UiErrorCategory.notFound => _codeNotFound,
        UiErrorCategory.rateLimit => _codeRateLimit,
        UiErrorCategory.format => _codeFormat,
        UiErrorCategory.unknown => _codeUnknown,
      };

  static String _withCode(String message, String code) => '$message [$code]';
}
