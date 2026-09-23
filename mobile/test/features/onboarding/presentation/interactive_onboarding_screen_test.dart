import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/onboarding/presentation/screens/interactive_onboarding_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const permissionChannel = MethodChannel(
    'flutter.baseflow.com/permissions/methods',
  );

  setUp(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(permissionChannel, (call) async {
      switch (call.method) {
        case 'checkPermissionStatus':
          final permission = call.arguments as int;
          if (permission == Permission.microphone.value) {
            return PermissionStatus.denied.index;
          }
          return PermissionStatus.granted.index;
        case 'requestPermissions':
          final permissions = (call.arguments as List<dynamic>).cast<int>();
          return <int, int>{
            for (final permission in permissions)
              permission: PermissionStatus.granted.index,
          };
      }
      return null;
    });
  });

  tearDown(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(permissionChannel, null);
  });

  testWidgets('completes onboarding flow and triggers onComplete', (
    tester,
  ) async {
    var completed = false;
    await _pumpOnboarding(
      tester,
      onComplete: () => completed = true,
    );

    // A-SPEC2 top10 #6：5 页流程（welcome/architecture/galaxy/ai-help/
    // personalization），4 次「下一步」后到达末页。
    for (var i = 0; i < 4; i++) {
      await _tapLabel(tester, _nextFinder);
    }

    expect(
      _enableButtonFinder,
      findsNWidgets(2),
    );

    await _tapLabel(tester, _getStartedFinder);

    expect(completed, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('totalPages is 5 and last page shows Get started after 4 nexts',
      (tester) async {
    // 页数断言（A-SPEC2 top10 #6 / SPEC §8.9 必达② ≤5 步）。
    expect(InteractiveOnboardingScreen.totalPages, 5);

    await _pumpOnboarding(tester);

    for (var i = 0; i < 4; i++) {
      expect(_getStartedFinder, findsNothing);
      await _tapLabel(tester, _nextFinder);
    }

    // 第 5 页（末页）才出现「开始使用」。
    expect(_getStartedFinder, findsOneWidget);
    expect(_nextFinder, findsNothing);
  });

  testWidgets('merged ai-help page shows chat and tasks one-liner each', (
    tester,
  ) async {
    await _pumpOnboarding(tester);

    // 跳到第 4 页（AI 怎么帮你，chat/task 合并单页）。
    for (var i = 0; i < 3; i++) {
      await _tapLabel(tester, _nextFinder);
    }

    // 一屏两特性：合并页标题 + 两个特性名各一句同屏。
    expect(find.text('AI 怎么帮你'), findsOneWidget);
    expect(find.text('AI 对话'), findsOneWidget);
    expect(find.text('智能任务'), findsOneWidget);
    expect(find.text('智能学习伙伴'), findsOneWidget);
    expect(find.text('个性化学习计划'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('restores saved page breakpoint (page index survives 6->5)', (
    tester,
  ) async {
    // 断点续传：旧档页码 4 在 5 页制下仍合法 → 直接恢复到末页（个性化），
    // 无需任何点击即出现「开始使用」。
    SharedPreferences.setMockInitialValues({'onboarding_current_page': 4});
    await _pumpOnboarding(tester);

    expect(_getStartedFinder, findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            (widget.data == 'Voice Input' || widget.data == '语音输入'),
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('permission page updates notification and microphone state', (
    tester,
  ) async {
    await _pumpOnboarding(tester);

    for (var i = 0; i < 4; i++) {
      await _tapLabel(tester, _nextFinder);
    }

    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            (widget.data == 'Voice Input' || widget.data == '语音输入'),
      ),
      findsOneWidget,
    );

    await _tapLabel(tester, _enableButtonFinder.first);
    await _tapLabel(tester, _enableButtonFinder.first);

    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            (widget.data == 'Enabled' || widget.data == '已开启' || widget.data == '已启用'),
      ),
      findsAtLeastNWidgets(1),
    );
    expect(tester.takeException(), isNull);
  });
}

Future<void> _pumpOnboarding(
  WidgetTester tester, {
  VoidCallback? onComplete,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        notificationServiceProvider.overrideWith(
          _FakeNotificationService.new,
        ),
      ],
      child: MaterialApp(
        locale: const Locale('zh'),
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: InteractiveOnboardingScreen(
          onComplete: onComplete ?? _noop,
        ),
      ),
    ),
  );

  await tester.pump();
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _tapLabel(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 350));
  await tester.pump(const Duration(milliseconds: 150));
}

Finder get _nextFinder => find.byWidgetPredicate(
      (widget) =>
          widget is SparkleButton &&
          (widget.label == 'Next' || widget.label == '下一步'),
    );

Finder get _getStartedFinder => find.byWidgetPredicate(
      (widget) =>
          widget is SparkleButton &&
          (widget.label == 'Get started' || widget.label == '开始使用'),
    );

Finder get _enableButtonFinder => find.byWidgetPredicate(
      (widget) =>
          widget is SparkleButton &&
          (widget.label == 'Enable' || widget.label == '开启' || widget.label == '启用'),
    );

class _FakeNotificationService extends NotificationService {
  _FakeNotificationService(super.ref) : super(autoInitialize: false);

  var _granted = false;

  @override
  Future<NotificationPermissionStatus> checkPermissionStatus() async => _granted
      ? NotificationPermissionStatus.granted()
      : NotificationPermissionStatus.denied(reason: 'not-requested');

  @override
  Future<bool> requestPermission() async {
    _granted = true;
    return true;
  }
}

void _noop() {}
