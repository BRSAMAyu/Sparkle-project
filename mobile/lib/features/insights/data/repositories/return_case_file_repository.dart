import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/insights/data/models/return_case_file.dart';

/// GOAL-011: Repository for the ReturnCaseFile.
///
/// Hits /growth/return-case-file. Cache-first by default; pass `rebuild: true`
/// when the user explicitly asks "what do you remember about me?".
final returnCaseFileRepositoryProvider =
    Provider<ReturnCaseFileRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ReturnCaseFileRepository(apiClient);
});

class ReturnCaseFileRepository {
  ReturnCaseFileRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<ReturnCaseFile?> fetch({bool rebuild = false}) async {
    if (DemoDataService.isDemoMode) {
      return null;
    }
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.growthReturnCaseFile,
        queryParameters: rebuild ? {'rebuild': true} : null,
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getReturnCaseFile',
      );
      return ReturnCaseFile.fromJson(data);
    } on DioException catch (e) {
      // Treat 404 / 204 as "no case file yet" rather than user-visible error.
      if (e.response?.statusCode == 404) {
        return null;
      }
      throw Exception(_extractDioMessage(e, 'Failed to load return case file'));
    } catch (_) {
      throw Exception('Unexpected error fetching return case file');
    }
  }

  String _extractDioMessage(DioException error, String fallbackMessage) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      final message = data['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }
    return fallbackMessage;
  }
}
