import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_connection_panel.dart';

class _FakeOpenClawConnectionService extends OpenClawConnectionService {
  _FakeOpenClawConnectionService({
    OpenClawConnectionConfig? config,
    OpenClawConnectionInfo? info,
  })  : _config = config ?? const OpenClawConnectionConfig(gatewayUrl: ''),
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
      createdAt: DateTime(2026, 1, 1),
      expiresAt: DateTime(2026, 1, 1, 0, 10),
    );
    notifyListeners();
    return _pairingSession!;
  }

  @override
  Future<void> completePairing(String deviceToken) async {
    _config = _config.copyWith(
      deviceToken: deviceToken,
      pairedAt: DateTime(2026, 1, 1),
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
    _config = const OpenClawConnectionConfig(gatewayUrl: '');
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

  testWidgets(
    'OpenClaw connection panel preserves auth and transport selection across rebuilds',
    (tester) async {
      final service = _FakeOpenClawConnectionService(
        config: const OpenClawConnectionConfig(
          gatewayUrl: 'http://localhost:8080',
          authToken: 'seed-token',
          transport: 'responses_http',
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            openClawConnectionProvider.overrideWith((ref) => service),
          ],
          child: MaterialApp(
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
}
