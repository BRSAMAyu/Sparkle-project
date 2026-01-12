import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/reviews/data/models/nightly_review_payload.dart';

final nightlyReviewRepositoryProvider =
    Provider<NightlyReviewRepository>((ref) => NightlyReviewRepository(ref.watch(apiClientProvider)));

class NightlyReviewRepository {
  NightlyReviewRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<NightlyReviewPayload?> getLatest() async {
    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>(ApiEndpoints.nightlyReviewLatest);
      final data = response.data;
      if (data == null) {
        return null;
      }
      return NightlyReviewPayload.fromJson(data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  Future<NightlyReviewPayload> markReviewed(String reviewId) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.nightlyReviewFeedback(reviewId),
      data: {'action': 'reviewed', 'source': 'mobile'},
    );
    return NightlyReviewPayload.fromJson(
        response.data ?? <String, dynamic>{},);
  }
}
