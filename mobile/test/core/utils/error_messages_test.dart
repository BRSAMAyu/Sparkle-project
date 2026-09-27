import 'dart:ui' show Locale;

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// V3-FIX-360（wt672 U-10 登记，wt677 verify4 复验属实，wt692 收口）：
/// ErrorMessages 默认分支（UNKNOWN/default）剥「Exception: 」前缀或原样
/// 直出 technicalMessage——后端技术细节（异常原文/内部地址/栈摘要）直达
/// 用户面。修法对齐 N16 单源词条（error_lexicon）：语义未知一律落
/// [uiErrorMessage] 类别人话兜底，不猜测语义、不透传原文。
///
/// 判定口径：泄漏 = 返回值包含 technicalMessage 的技术性片段；兜底 =
/// 返回值与既有 arb 人话词条同源。
void main() {
  // 钉住 I18nService 全局侧走 zh（getUserFriendlyMessage 无 l10n 参数的
  // 调用面——chat/community provider 与 ErrorWidget.builder——落 zh 口径），
  // 与显式 AppLocalizationsZh() 实例同源，断言不受执行序影响。
  setUp(() {
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
  });

  final zh = AppLocalizationsZh();
  final en = AppLocalizationsEn();

  group('V3-FIX-360 默认分支技术信息不泄漏（getLocalizedMessage）', () {
    test('UNKNOWN + 异常原文（Exception: 前缀）不直出技术细节', () {
      const technical =
          'Exception: gRPC error (status 14): connection to 10.0.0.1:9 '
          'failed, retry_budget exhausted';
      final msg = ErrorMessages.getLocalizedMessage(zh, 'UNKNOWN', technical);

      expect(msg, isNot(contains('gRPC')));
      expect(msg, isNot(contains('10.0.0.1')));
      expect(msg, isNot(contains('Exception')));
      expect(msg, isNot(contains('retry_budget')));
      // 样本命中既有网络模式族（'connection'）→ 网络人话，不落透传。
      expect(msg, zh.errorConnectionFailed);
    });

    test('未知错误码 + 未匹配技术文本不原样透传', () {
      const technical = 'xyzzy invariant violated at handler.dart:88';
      final msg =
          ErrorMessages.getLocalizedMessage(zh, 'SOME_NEW_CODE', technical);

      expect(msg, isNot(equals(technical)));
      expect(msg, isNot(contains('invariant')));
      expect(msg, zh.errorDefaultTitle);
    });

    test('technicalMessage 为 null + UNKNOWN 落兜底词条', () {
      expect(
        ErrorMessages.getLocalizedMessage(zh, 'UNKNOWN', null),
        zh.errorDefaultTitle,
      );
    });

    test('超时族技术文本（旧表漏配）经共享判定表落超时人话', () {
      final msg = ErrorMessages.getLocalizedMessage(
        zh,
        'UNKNOWN',
        'TimeoutException after 30000ms',
      );
      expect(msg, zh.errorTimeoutDetail);
    });

    test('en locale 同口径不泄漏', () {
      final msg = ErrorMessages.getLocalizedMessage(
        en,
        'UNKNOWN',
        'Exception: gRPC error (status 14): 10.0.0.1:9',
      );
      expect(msg, isNot(contains('gRPC')));
      expect(msg, isNot(contains('10.0.0.1')));
      expect(msg, en.errorDefaultTitle);
    });
  });

  group('V3-FIX-360 无 l10n 回退路径不泄漏（getUserFriendlyMessage）', () {
    test('异常原文经全局 l10n 兜底落类别人话，不剥前缀直出', () {
      const technical = 'Exception: stack summary from bootstrap failure';
      final msg = ErrorMessages.getUserFriendlyMessage('UNKNOWN', technical);

      expect(msg, isNot(contains('stack summary')));
      expect(msg, isNot(contains('Exception')));
      expect(msg, zh.errorDefaultTitle);
    });

    test('已知错误码经全局 l10n 出词条（英文私有映射表退役）', () {
      expect(
        ErrorMessages.getUserFriendlyMessage('CONNECTION_ERROR', null),
        zh.errorConnectionFailed,
      );
    });
  });

  group('既有映射族回归 pin（修前即绿）', () {
    test('TOKEN_EXPIRED 错误码映射不受影响', () {
      expect(
        ErrorMessages.getLocalizedMessage(zh, 'TOKEN_EXPIRED', null),
        zh.errorTokenExpired,
      );
    });

    test('中文后端友好文案模式族映射不受影响', () {
      expect(
        ErrorMessages.getLocalizedMessage(zh, 'UNKNOWN', '服务器打盹了一下'),
        zh.errorServerIssue,
      );
      expect(
        ErrorMessages.getLocalizedMessage(zh, 'UNKNOWN', '操作太频繁了'),
        zh.errorRateLimit,
      );
    });

    test('共享判定族：not found 模式仍落 notFound 人话', () {
      expect(
        ErrorMessages.getLocalizedMessage(zh, 'UNKNOWN', '资源不存在'),
        zh.errorNotFound,
      );
    });
  });
}
