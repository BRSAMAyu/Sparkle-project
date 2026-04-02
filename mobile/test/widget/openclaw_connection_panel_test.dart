import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_connection_panel.dart';

const _runRealOpenClawSmoke = bool.fromEnvironment('OPENCLAW_REAL_SMOKE');

class _FakeOpenClawConnectionService extends OpenClawConnectionService {
  _FakeOpenClawConnectionService({
    OpenClawConnectionConfig? config,
    OpenClawConnectionInfo? info,
  })  : _config = config ?? OpenClawConnectionConfig.empty,
        _info = info ?? const OpenClawConnectionInfo();

  OpenClawConnectionConfig _config;
  OpenClawConnectionInfo _info;
  OpenClawPairingSession? _pairingSession;
  List<OpenClawQueuedRequest> _queuedRequests = const [];

  @override
  OpenClawConnectionConfig get config => _config;

  @override
  OpenClawConnectionInfo get info => _info;

  @override
  OpenClawPairingSession? get pairingSession => _pairingSession;

  @override
  List<OpenClawQueuedRequest> get queuedRequests =>
      List<OpenClawQueuedRequest>.unmodifiable(_queuedRequests);

  @override
  bool get isConnected => _info.status == OpenClawConnectionStatus.connected;

  void emitRefresh() => notifyListeners();

  @override
  Future<OpenClawPairingSession> startPairing() async {
    _pairingSession = OpenClawPairingSession(
      code: '123456',
      createdAt: DateTime(2026),
      expiresAt: DateTime(2026, 1, 1, 0, 10),
    );
    notifyListeners();
    return _pairingSession!;
  }

  @override
  Future<void> completePairing(String deviceToken) async {
    _config = _config.copyWith(
      deviceToken: deviceToken,
      pairedAt: DateTime(2026),
    );
    _pairingSession = null;
    notifyListeners();
  }

  @override
  Future<void> cancelPairing() async {
    _pairingSession = null;
    notifyListeners();
  }

  @override
  Future<bool> configure(OpenClawConnectionConfig newConfig) async {
    _config = newConfig;
    notifyListeners();
    return true;
  }

  @override
  Future<bool> testConnection(OpenClawConnectionConfig config) async {
    _info = const OpenClawConnectionInfo(
      status: OpenClawConnectionStatus.connected,
      latencyMs: 120,
      nodeCount: 2,
      capabilities: <String>['模板执行'],
    );
    notifyListeners();
    return true;
  }

  @override
  Future<void> disconnect() async {
    _config = OpenClawConnectionConfig.empty;
    _info = const OpenClawConnectionInfo();
    notifyListeners();
  }

  @override
  Future<void> clearQueuedRequests() async {
    _queuedRequests = const [];
    notifyListeners();
  }
}

void main() {
  test('dashboard cards include OpenClaw by default', () {
    final defaults = DashboardCardConfigState.defaults();
    expect(defaults.visibleCardIds, contains(DashboardCardIds.openClaw));
    expect(defaults.cardOrder, contains(DashboardCardIds.openClaw));
  });

  test(
    'OpenClaw connection service can reach the real local gateway',
    () async {
      final service = OpenClawConnectionService();
      final ok = await service.testConnection(
        const OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:18789',
          authToken: 'd1c836b87e26db7e164522b01bf346a2d7226b17',
        ),
      );

      expect(ok, isTrue);
      expect(service.info.status, OpenClawConnectionStatus.connected);
    },
    skip: !_runRealOpenClawSmoke,
  );

  testWidgets(
    'OpenClaw connection panel preserves auth and transport selection across rebuilds',
    (tester) async {
      final service = _FakeOpenClawConnectionService(
        config: const OpenClawConnectionConfig(
          gatewayUrl: 'http://localhost:8080',
          authToken: 'seed-token',
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            openClawConnectionProvider.overrideWith((ref) => service),
          ],
          child: const MaterialApp(
            locale: Locale('zh'),
            supportedLocales: <Locale>[Locale('zh')],
            localizationsDelegates: GlobalMaterialLocalizations.delegates,
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 640,
                  child: OpenClawConnectionPanel(),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.ensureVisible(find.text('设备配对'));
      await tester.tap(find.text('设备配对'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(find.text('设备令牌'), findsOneWidget);
      expect(find.text('未保存更改'), findsOneWidget);

      service.emitRefresh();
      await tester.pump();
      expect(find.text('设备令牌'), findsOneWidget);

      await tester.ensureVisible(find.text('WebSocket'));
      await tester.tap(find.text('WebSocket'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(find.textContaining('WebSocket 更适合保持持续连接'), findsOneWidget);

      service.emitRefresh();
      await tester.pump();
      expect(find.textContaining('WebSocket 更适合保持持续连接'), findsOneWidget);
    },
  );

  testWidgets(
    'OpenClaw connection panel supports guest preset without exposing details',
    (tester) async {
      final service = _FakeOpenClawConnectionService();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            openClawConnectionProvider.overrideWith((ref) => service),
          ],
          child: const MaterialApp(
            locale: Locale('zh'),
            supportedLocales: <Locale>[Locale('zh')],
            localizationsDelegates: GlobalMaterialLocalizations.delegates,
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 640,
                  child: OpenClawConnectionPanel(),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('访客模式默认引擎'));
      await tester.pumpAndSettle();

      expect(find.textContaining('已选中“访客模式默认引擎”'), findsOneWidget);
      expect(find.text('网关地址'), findsNothing);
      expect(find.text('认证方式'), findsNothing);
    },
  );

  testWidgets(
    'OpenClaw connection panel surfaces pairing countdown and save highlight',
    (tester) async {
      final service = _FakeOpenClawConnectionService(
        config: const OpenClawConnectionConfig(
          gatewayUrl: 'http://localhost:8080',
          authToken: 'seed-token',
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            openClawConnectionProvider.overrideWith((ref) => service),
          ],
          child: const MaterialApp(
            locale: Locale('zh'),
            supportedLocales: <Locale>[Locale('zh')],
            localizationsDelegates: GlobalMaterialLocalizations.delegates,
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 640,
                  child: OpenClawConnectionPanel(),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('设备配对'), warnIfMissed: false);
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('生成配对码'));
      await tester.tap(find.text('生成配对码'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(find.textContaining('完成配对'), findsWidgets);

      await tester.enterText(find.byType(TextField).at(1), 'device-token-1');
      await tester.ensureVisible(find.text('完成配对'));
      await tester.tap(find.text('完成配对'));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('保存配置'));
      await tester.tap(find.text('保存配置'));
      await tester.pumpAndSettle();

      expect(find.textContaining('配置已保存'), findsWidgets);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    },
  );

  testWidgets(
    'OpenClaw connection panel explains missing execution scope clearly',
    (tester) async {
      final service = _FakeOpenClawConnectionService(
        config: const OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:18789',
          authToken: 'seed-token',
        ),
        info: const OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.error,
          errorMessage: 'missing scope: operator.write',
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            openClawConnectionProvider.overrideWith((ref) => service),
          ],
          child: const MaterialApp(
            locale: Locale('zh'),
            supportedLocales: <Locale>[Locale('zh')],
            localizationsDelegates: GlobalMaterialLocalizations.delegates,
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 640,
                  child: OpenClawConnectionPanel(),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('网关在线，但没有执行权限'), findsOneWidget);
      expect(find.textContaining('operator.write'), findsWidgets);
      expect(find.textContaining('设备配对 + WebSocket'), findsOneWidget);
    },
  );

  testWidgets(
    'OpenClaw connection panel imports pairing payload from clipboard',
    (tester) async {
      final service = _FakeOpenClawConnectionService();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            openClawConnectionProvider.overrideWith((ref) => service),
          ],
          child: const MaterialApp(
            locale: Locale('zh'),
            supportedLocales: <Locale>[Locale('zh')],
            localizationsDelegates: GlobalMaterialLocalizations.delegates,
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 640,
                  child: OpenClawConnectionPanel(),
                ),
              ),
            ),
          ),
        ),
      );

      await Clipboard.setData(
        const ClipboardData(
          text:
              '{"gateway_url":"ws://demo.openclaw.local:18789","pair_token":"pair-secret","device_name":"Demo MacBook"}',
        ),
      );

      await tester.ensureVisible(find.text('从剪贴板导入'));
      await tester.tap(find.text('从剪贴板导入'));
      await tester.pumpAndSettle();

      expect(service.config.gatewayUrl, 'http://demo.openclaw.local:18789');
      expect(service.config.wsUrl, 'ws://demo.openclaw.local:18789');
      expect(service.config.authToken, 'pair-secret');
      expect(service.config.transport, 'gateway_ws');
      expect(find.textContaining('已连接到 Demo MacBook'), findsOneWidget);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    },
  );
}
