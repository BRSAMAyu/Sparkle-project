import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const _OpenClawSmokeApp());
}

class _OpenClawSmokeApp extends StatefulWidget {
  const _OpenClawSmokeApp();

  @override
  State<_OpenClawSmokeApp> createState() => _OpenClawSmokeAppState();
}

class _OpenClawSmokeAppState extends State<_OpenClawSmokeApp> {
  String _status = 'running';

  @override
  void initState() {
    super.initState();
    unawaited(_runSmoke());
  }

  Future<void> _runSmoke() async {
    final service = OpenClawConnectionService();
    const config = OpenClawConnectionConfig(
      gatewayUrl: 'http://127.0.0.1:18789',
      authToken: 'd1c836b87e26db7e164522b01bf346a2d7226b17',
      transport: 'responses_http',
    );

    final ok = await service.testConnection(config);
    final info = service.info;

    debugPrint('openclaw_smoke.ok=$ok');
    debugPrint('openclaw_smoke.status=${info.status.name}');
    debugPrint('openclaw_smoke.latency_ms=${info.latencyMs}');
    debugPrint('openclaw_smoke.node_count=${info.nodeCount}');
    debugPrint(
      'openclaw_smoke.capabilities=${(info.capabilities ?? const []).join(",")}',
    );
    if ((info.errorMessage ?? '').isNotEmpty) {
      debugPrint('openclaw_smoke.error=${info.errorMessage}');
    }

    if (!mounted) {
      exit(ok ? 0 : 1);
    }
    setState(() {
      _status = ok ? 'success' : 'failure';
    });
    await Future<void>.delayed(const Duration(milliseconds: 250));
    exit(ok ? 0 : 1);
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.ltr,
      child: ColoredBox(
        color: Colors.white,
        child: Center(
          child: Text('openclaw-smoke: $_status'),
        ),
      ),
    );
  }
}
