import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';

final accountabilityRepositoryProvider =
    Provider<AccountabilityRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AccountabilityRepository(apiClient);
});

class AccountabilityRepository {
  AccountabilityRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<AccountabilityPartnershipInfo> requestPartnership({
    required String partnerId,
    required String initiatorGoal,
    int checkInDays = 1,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityRequest,
      data: {
        'partner_id': partnerId,
        'initiator_goal': initiatorGoal,
        'check_in_days': checkInDays,
      },
    );
    if (response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
          response.data, action: 'requestPartnership',);
      return AccountabilityPartnershipInfo.fromJson(data);
    }
    throw Exception('Failed to request partnership');
  }

  Future<AccountabilityPartnershipInfo> respondToPartnership(
    String partnershipId, {
    required bool accept,
    String? partnerGoal,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityRespond(partnershipId),
      data: {
        'accept': accept,
        if (partnerGoal != null && partnerGoal.isNotEmpty)
          'partner_goal': partnerGoal,
      },
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapMap(
          response.data, action: 'respondToPartnership',);
      return AccountabilityPartnershipInfo.fromJson(data);
    }
    throw Exception('Failed to respond to partnership');
  }

  Future<List<AccountabilityPartnershipInfo>> getMyPartnerships() async {
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.accountabilityMine);
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
          response.data, action: 'getMyPartnerships',);
      return data
          .map((e) =>
              AccountabilityPartnershipInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load partnerships');
  }

  Future<void> endPartnership(String partnershipId) async {
    await _apiClient.delete<dynamic>(
        ApiEndpoints.accountabilityEnd(partnershipId),);
  }

  Future<AccountabilityCheckinInfo> dailyCheckin(
    String partnershipId, {
    required String content,
    required int mood,
    required int minutes,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityCheckin(partnershipId),
      data: {
        'content': content,
        'mood': mood,
        'minutes': minutes,
      },
    );
    if (response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
          response.data, action: 'dailyCheckin',);
      return AccountabilityCheckinInfo.fromJson(data);
    }
    throw Exception('Failed to check in');
  }

  Future<AccountabilityStatsInfo> getStats(String partnershipId) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityStats(partnershipId),
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'getStats');
      return AccountabilityStatsInfo.fromJson(data);
    }
    throw Exception('Failed to load stats');
  }

  Future<List<AccountabilityCheckinInfo>> getTimeline(
    String partnershipId, {
    int limit = 30,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityTimeline(partnershipId),
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
          response.data, action: 'getTimeline',);
      return data
          .map((e) =>
              AccountabilityCheckinInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    throw Exception('Failed to load timeline');
  }
}
