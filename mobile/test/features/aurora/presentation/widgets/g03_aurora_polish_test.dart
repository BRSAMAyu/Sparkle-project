// V4-G03 · Aurora 家族面打磨钉：reduce-motion 等价 + turns 芯片四风格令牌。
//
// - typing dots：OS 减动效/辅助导航下首帧前不启动循环闪烁（didChangeDependencies
//   门控，非 build 内事后 stop），直落静态三点——「生成中」语义由伴随文案承载；
//   非 reduce-motion 下循环动画照常运行（等价 ≠ 摘功能）。
// - turns chip：V4-G03 前用 borderSubtle 中灰底对 textSecondary 仅 2.03–4.3:1
//   （五档全崩）；钉定 token 身份（surfaceTertiary 底 + textPrimary + 12sp），
//   四档下 DS 令牌各取各值，杜绝 classic-only 硬编码回归。
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/data/services/aurora_core_session_service.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../../core/design/style_preview/style_preview_test_harness.dart';

/// respond 永不完成：把 sheet 稳定停在 _sending（typing dots 常驻）。
class _HangingOnRespondClient implements AuroraCoreSessionClient {
  @override
  Future<AuroraCoreSession> startSession({
    String? conversationId,
    String surface = 'aurora_modeling',
    String sessionType = 'user_initiated',
    String? scope,
    List<String> wakeReasons = const [],
    String bandStatus = 'calibration_available',
    AuroraCoreSessionEntryReason? entryReason,
    String? resumeToken,
  }) async =>
      _session();

  @override
  Future<AuroraCoreSession> respond({
    required String sessionId,
    required String content,
    String? optionId,
    String? semanticValue,
    Map<String, dynamic>? modelWriteEffect,
    bool isFreeform = false,
  }) =>
      Completer<AuroraCoreSession>().future;

  @override
  Future<AuroraCoreSession?> getCurrentSession() async => null;

  @override
  Future<AuroraCoreSession> resumeSession(String resumeToken) async =>
      _session();

  @override
  Future<AuroraCoreSession> pauseSession(
    String sessionId, {
    String reason = 'user_request',
  }) async =>
      _session();

  @override
  Future<AuroraCoreSession> closeSession(String sessionId) async => _session();
}

AuroraCoreSession _session() => const AuroraCoreSession(
      sessionId: 'session-1',
      userId: 'u1',
      conversationId: 'c1',
      surface: 'aurora_modeling',
      status: 'active',
      stage: 'await_user',
      scope: '当前策略与你的实际情况',
      sessionType: 'user_initiated',
      entryReason: null,
      agenda: null,
      resumeToken: 'session-1',
      messages: [
        AuroraCoreMessage(
          role: 'aurora',
          content: '我注意到你最近计划偏离。',
          stage: 'declare',
          timestamp: '2026-05-01T00:00:00',
        ),
      ],
      calibrationResult: null,
      userTurnCount: 0,
      auroraMessageCount: 1,
      pendingOptionGroups: [
        AuroraPredictedReplyGroup(
          groupId: 'simple',
          question: '更接近哪一种？',
          questionType: 'assumption_check',
          contextNote: '',
          options: [
            AuroraPredictedReplyOption(
              id: 'confirm',
              label: '确实如此',
              semanticValue: 'confirm',
              replyType: 'confirm',
              confidence: 1,
              modelWriteEffect: null,
              isDisconfirming: false,
              isFreeform: false,
              contextSource: 'simple',
              telemetryId: 'simple_confirm',
            ),
          ],
        ),
      ],
      createdAt: '2026-05-01T00:00:00',
      lastActivityAt: '2026-05-01T00:00:00',
      expiresAt: '2026-05-01T00:30:00',
    );

/// 带 builder 的宿主：builder 内 copyWith 注入全局 MediaQuery——MaterialApp
/// 会自建 MediaQuery（直包外层会被丢弃），builder 注入才能到达 modal sheet
/// 内的 MediaQuery.disableAnimationsOf 读取点（与 OS 减动效注入同管道）。
Widget _hostWithMediaQuery({
  bool disableAnimations = false,
  bool accessibleNavigation = false,
}) =>
    ProviderScope(
      overrides: [
        auroraCoreSessionServiceProvider
            .overrideWithValue(_HangingOnRespondClient()),
      ],
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppThemes.lightTheme,
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(
            disableAnimations: disableAnimations,
            accessibleNavigation: accessibleNavigation,
          ),
          child: child ?? const SizedBox.shrink(),
        ),
        home: Scaffold(
          body: Builder(
            builder: (context) => Center(
              child: TextButton(
                onPressed: () => showAuroraCoreSession(
                  context: context,
                  bandStatus: 'risk_found',
                  wakeReasons: const ['task_time_overrun'],
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

/// 读取 typing dots 三点当前透明度（非 reduce-motion 下逐帧变化）。
List<double> _dotOpacities(WidgetTester tester) {
  final dots = find.descendant(
    of: find
        .byWidgetPredicate((w) => w.runtimeType.toString() == '_TypingDots'),
    matching: find.byType(Opacity),
  );
  return tester.widgetList<Opacity>(dots).map((o) => o.opacity).toList();
}

Future<void> _openSheetToTyping(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});
  await tester.pumpWidget(_hostWithMediaQuery());
  await tester.tap(find.text('open'));
  // sheet 进场 + startSession 异步落定（不 pumpAndSettle：非 reduce 档
  // 打字点为无限动画）。
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 200));
  // 点确认项 → respond 挂起 → _sending=true → typing dots 常驻。
  await tester.tap(find.text('确实如此'));
  await tester.pump(const Duration(milliseconds: 100));
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('V4-G03 · typing dots reduce-motion 等价（S01 判例「禁动效不装壳」）', () {
    testWidgets('reduce-motion：首帧前不启动动画，静态三点信息等价', (tester) async {
      SharedPreferences.setMockInitialValues({});
      await tester.pumpWidget(
        _hostWithMediaQuery(
          disableAnimations: true,
          accessibleNavigation: true,
        ),
      );
      await tester.tap(find.text('open'));
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 200));
      await tester.tap(find.text('确实如此'));
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      final first = _dotOpacities(tester);
      expect(first, hasLength(3), reason: 'typing dots 未出现（_sending 未触发）');
      expect(
        first,
        orderedEquals([1.0, 0.6, 0.35]),
        reason: '减动效档应直落静态三点（G03 约定梯度）',
      );
      // 静默推进两拍：数值零漂移 = 无循环动画在跑。
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
      expect(
        _dotOpacities(tester),
        orderedEquals(first),
        reason: 'reduce-motion 下打字点必须静止（首帧前不 repeat，非事后 stop）',
      );
    });

    testWidgets('非 reduce-motion：循环动画照常运行（等价 ≠ 摘功能）', (tester) async {
      await _openSheetToTyping(tester);

      final first = _dotOpacities(tester);
      expect(first, hasLength(3));
      await tester.pump(const Duration(milliseconds: 300));
      final second = _dotOpacities(tester);
      expect(
        second,
        isNot(orderedEquals(first)),
        reason: '非减动效档打字点必须仍在循环动画（不放松既有行为语义）',
      );
    });
  });

  group('V4-G03 · turns chip 四风格令牌钉（borderSubtle 中灰底全档崩的收口）', () {
    for (final profile in PixelPreviewProfile.values) {
      testWidgets(
          '[$profile] turns chip = surfaceTertiary 底 + textPrimary '
          '12sp（token 身份，禁 classic-only 硬编码回归）', (tester) async {
        tester.view.devicePixelRatio = 2.0;
        tester.view.physicalSize = const Size(720, 1600);
        addTearDown(() {
          tester.view.resetDevicePixelRatio();
          tester.view.resetPhysicalSize();
        });
        final manager = await freshThemeManager();
        await manager.setPixelPreviewProfile(profile);

        // ProviderScope 必须包住 buildPreviewHost（MaterialApp 的根导航）：
        // modal sheet 经根导航 push，挂在 home 内的 override 到不了 sheet。
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              auroraCoreSessionServiceProvider
                  .overrideWithValue(_HangingOnRespondClient()),
            ],
            child: buildPreviewHost(
              body: Builder(
                builder: (context) => Scaffold(
                  body: Center(
                    child: TextButton(
                      onPressed: () => showAuroraCoreSession(
                        context: context,
                        bandStatus: 'risk_found',
                        wakeReasons: const ['task_time_overrun'],
                      ),
                      child: const Text('open'),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
        await settlePreview(tester);
        await tester.tap(find.text('open'));
        await tester.pump(const Duration(milliseconds: 400));
        await tester.pump(const Duration(milliseconds: 200));

        final chipText = find.text('剩余 6 轮');
        expect(
          chipText,
          findsOneWidget,
          reason: '[$profile] active session 的 turns chip 未上屏',
        );

        // token 身份钉：底=DS.surfaceTertiary、字=DS.textPrimary、
        // 字号=DS.fontSizeXs（DS 经 ThemeManager 取当前档值——钉的是
        // 「走令牌」而非「走某一硬编码」）。
        final text = tester.widget<Text>(chipText);
        expect(
          text.style?.color,
          DS.textPrimary,
          reason: '[$profile] turns chip 文字必须走 DS.textPrimary 令牌',
        );
        expect(
          text.style?.fontSize,
          DS.fontSizeXs,
          reason: '[$profile] turns chip 字号必须达 12sp 字阶下限',
        );
        final container = tester.widget<Container>(
          find
              .ancestor(
                of: chipText,
                matching: find.byType(Container),
              )
              .first,
        );
        final decoration = container.decoration as BoxDecoration;
        expect(
          decoration.color,
          DS.surfaceTertiary,
          reason: '[$profile] turns chip 底色必须走 DS.surfaceTertiary 令牌'
              '（borderSubtle 中灰底对任意墨色双向失配）',
        );
      });
    }
  });
}
