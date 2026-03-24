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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const permissionChannel = MethodChannel(
    'flutter.baseflow.com/permissions/methods',
  );

  setUp(() async {
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

    for (var i = 0; i < 5; i++) {
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

  testWidgets('permission page updates notification and microphone state', (
    tester,
  ) async {
    await _pumpOnboarding(tester);

    for (var i = 0; i < 5; i++) {
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
            (widget.data == 'Enabled' || widget.data == '已开启'),
      ),
      findsNWidgets(2),
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
          (widget.label == 'Enable' || widget.label == '开启'),
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
