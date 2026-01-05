import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

final omniBarRepositoryProvider = Provider<OmniBarRepository>(
    (ref) => OmniBarRepository(ref.read(apiClientProvider)),);

class OmniBarRepository {
  OmniBarRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<Map<String, dynamic>> dispatch(String text) async {
    final response = await _apiClient.post(
      ApiEndpoints.omnibarDispatch,
      data: {'text': text},
    );
    return response.data as Map<String, dynamic>;
  }
}
