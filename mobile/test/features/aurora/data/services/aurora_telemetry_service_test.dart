import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';

void main() {
  test('status-band freeform telemetry includes freeform_text', () async {
    final api = _CapturingApiClient();
    final service = AuroraTelemetryService(api);

    await service.recordStatusBandCorrection(
      label: 'Aurora missed that I was sick',
      semanticValue: 'freeform_correction',
      isDisconfirming: true,
      bandStatus: 'needs_confirm',
      isFreeform: true,
      freeformText: 'Aurora missed that I was sick',
    );

    expect(api.path, ApiEndpoints.auroraChipTelemetry);
    expect(api.data, containsPair('is_freeform', true));
    expect(
      api.data,
      containsPair('freeform_text', 'Aurora missed that I was sick'),
    );
  });
}

class _CapturingApiClient extends ApiClient {
  _CapturingApiClient() : super(_UnusedRef());

  String? path;
  late Map<String, dynamic> data;

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    this.path = path;
    this.data = Map<String, dynamic>.from(data! as Map);
    return Response<T>(requestOptions: RequestOptions(path: path));
  }
}

class _UnusedRef implements Ref<Object?> {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported provider read: $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
