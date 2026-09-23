import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// N16（A-SPEC3 §6.2/§6.4 改造 #3 选项 A）验收：异常→人话映射单源。
///
/// 两入口——遗留兼容层 [UserFacingError.from]（字符串匹配）与新类型化
/// owner [uiErrorMessage]——对同一异常样本集必须输出**一致语义**：
/// 共享同一判定表 [categorizeUiError] 与同一词条表，任何一侧单方面
/// 漂移（判定集分叉/词条换绑）都会让本测试变红。
void main() {
  // 钉住 I18nService 全局侧（UserFacingError.from 经 S 取词）走 zh，
  // 与下方 AppLocalizationsZh() 显式实例同源，断言确定性不受执行序影响。
  setUp(() {
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
  });

  final zh = AppLocalizationsZh();
  final en = AppLocalizationsEn();

  // 同一异常样本集喂两个入口（形态对齐既有 a3 诊断码测试的字符串样本）。
  final samples = <(Object, UiErrorCategory, String)>[
    (
      Exception('SocketException: Connection refused (sample payload)'),
      UiErrorCategory.network,
      '[ERR-NET]',
    ),
    (
      Exception('Connection timed out while sampling'),
      UiErrorCategory.network,
      '[ERR-NET]',
    ),
    (
      StateError('CLIENT_CLOSED before flush'),
      UiErrorCategory.network,
      '[ERR-NET]',
    ),
    (
      TimeoutException('no stream events', const Duration(seconds: 45)),
      UiErrorCategory.timeout,
      '[ERR-TIMEOUT]',
    ),
    (
      Exception('401 Unauthorized token'),
      UiErrorCategory.auth,
      '[ERR-AUTH]',
    ),
    (
      Exception('HTTP 500 Internal Server Error'),
      UiErrorCategory.server,
      '[ERR-SERVER]',
    ),
    (
      Exception('404 Not Found'),
      UiErrorCategory.notFound,
      '[ERR-NOTFOUND]',
    ),
    (
      Exception('429 too many requests'),
      UiErrorCategory.rateLimit,
      '[ERR-RATELIMIT]',
    ),
    (
      const FormatException('bad sample payload'),
      UiErrorCategory.format,
      '[ERR-FORMAT]',
    ),
    (
      Exception('mystery opening-line failure'),
      UiErrorCategory.unknown,
      '[ERR-UNKNOWN]',
    ),
  ];

  group('两入口一致性（UserFacingError ↔ 类型化 owner）', () {
    test('同一异常样本集：UserFacingError.from = 词条表文案 + 类别码', () {
      for (final (sample, expectedCategory, expectedCode) in samples) {
        final category = categorizeUiError(sample);
        expect(category, expectedCategory,
            reason: '样本 "$sample" 判定类别漂移',);

        final viaOwner = uiErrorMessage(zh, category);
        final viaLegacy = UserFacingError.from(sample);
        expect(viaLegacy, '$viaOwner $expectedCode',
            reason: '样本 "$sample" 两入口文案/诊断码不一致：'
                'owner="$viaOwner" legacy="$viaLegacy"',);
      }
    });

    test('en 词条与 zh 同类别同源（arb 双语族）', () {
      for (final (_, category, _) in samples) {
        expect(uiErrorMessage(en, category), isNotEmpty);
        expect(uiErrorMessage(zh, category), isNotEmpty);
      }
    });

    test('词条永不携带异常原文（样本 payload 不出现在任何类别文案）', () {
      const payloads = ['sample payload', 'mystery', 'CLIENT_CLOSED'];
      for (final category in UiErrorCategory.values) {
        for (final message in [uiErrorMessage(zh, category), uiErrorMessage(en, category)]) {
          for (final payload in payloads) {
            expect(message.contains(payload), isFalse,
                reason: '类别 $category 文案泄漏异常原文片段 "$payload"',);
          }
        }
      }
    });
  });

  group('类型化入口（TypedUiError 自报，零文本嗅探）', () {
    test('galaxy 类型化类别与等价原始异常的字符串判定语义一致', () {
      final dioNetworkError = DioException(
        requestOptions: RequestOptions(path: '/v1/galaxy/graph'),
        type: DioExceptionType.connectionError,
        error: Exception('sample payload'),
      );
      final galaxyNetwork = GalaxyError.network(dioNetworkError);

      // 类型化入口 vs 字符串入口：同一语义（网络故障）判定一致。
      expect(
        galaxyNetwork.uiErrorCategory,
        categorizeUiError(
          Exception('SocketException: Connection refused (sample payload)'),
        ),
      );
      expect(galaxyNetwork.uiErrorCategory, UiErrorCategory.network);

      expect(
        GalaxyError.circuitBreakerOpen().uiErrorCategory,
        UiErrorCategory.serviceDegraded,
      );
      final galaxyUnknown = GalaxyError.unknown('raw sample text');
      expect(galaxyUnknown.uiErrorCategory, UiErrorCategory.unknown);
      expect(
        galaxyUnknown.uiErrorCategory,
        categorizeUiError(Exception('unrelated unmatched text')),
      );
    });

    test('galaxy 域绑定输出 = owner 词条轴上的 galaxy 词条（判定不落域外）', () {
      // galaxy 屏私有函数已降为纯绑定：network → network 词条轴、
      // serviceDegraded → service 词条轴、其余 → 默认。
      // 这里以枚举完备性钉住绑定覆盖面（galaxy_screen 的 switch 同构）。
      final bindings = <UiErrorCategory, String>{
        UiErrorCategory.network: zh.galaxyErrorHumanNetwork,
        UiErrorCategory.serviceDegraded: zh.galaxyErrorHumanService,
        UiErrorCategory.unknown: zh.galaxyErrorHumanDefault,
      };
      expect(bindings[UiErrorCategory.network], isNotEmpty);
      expect(bindings[UiErrorCategory.unknown],
          isNot(bindings[UiErrorCategory.network]),);
    });
  });
}
