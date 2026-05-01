import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';

final growthNarrativeRepositoryProvider =
    Provider<GrowthNarrativeRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GrowthNarrativeRepository(apiClient);
});

class GrowthNarrativeRepository {
  GrowthNarrativeRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<WeeklyGrowthNarrative> getWeeklyNarrative() async {
    if (DemoDataService.isDemoMode) {
      return WeeklyGrowthNarrative.placeholder();
    }
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.growthWeeklyNarrative,
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getWeeklyNarrative',
      );
      return WeeklyGrowthNarrative.fromJson(data);
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to load growth story'));
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<WeeklyGrowthNarrative> generateWeeklyNarrative() async {
    if (DemoDataService.isDemoMode) {
      return WeeklyGrowthNarrative.placeholder();
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.growthWeeklyNarrativeGenerate,
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'generateWeeklyNarrative',
      );
      return WeeklyGrowthNarrative.fromJson(data);
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to generate growth story'));
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  String _extractDioMessage(DioException error, String fallbackMessage) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      if (detail is Map<String, dynamic>) {
        final message = detail['message'];
        if (message is String && message.isNotEmpty) {
          return message;
        }
      }
      final message = data['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }
    return fallbackMessage;
  }
}
