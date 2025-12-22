
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

final omniBarRepositoryProvider = Provider<OmniBarRepository>((ref) {
  return OmniBarRepository(ref.read(apiClientProvider));
});

class OmniBarRepository {
  final ApiClient _apiClient;

  OmniBarRepository(this._apiClient);

  Future<Map<String, dynamic>> dispatch(String text) async {
    final response = await _apiClient.post(
      ApiEndpoints.omnibarDispatch,
      data: {'text': text},
    );
    return response.data as Map<String, dynamic>;
  }
}
