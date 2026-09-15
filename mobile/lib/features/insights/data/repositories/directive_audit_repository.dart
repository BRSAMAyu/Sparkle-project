import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/insights/data/models/directive_audit_entry.dart';

class DirectiveAuditRepository {
  const DirectiveAuditRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<DirectiveAuditEntry>> fetchRecent({
    int limit = 20,
    String? directiveType,
    int? hours,
  }) async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.insightsRecentDirectives,
      queryParameters: {
        'limit': limit,
        if (directiveType != null && directiveType.isNotEmpty)
          'directive_type': directiveType,
        if (hours != null) 'hours': hours,
      },
    );
    final data = ApiResponseParser.unwrapList(
      response.data,
      action: 'fetchRecentDirectives',
    );
    return data
        .whereType<Map<String, dynamic>>()
        .map(DirectiveAuditEntry.fromJson)
        .toList();
  }
}

final directiveAuditRepositoryProvider = Provider<DirectiveAuditRepository>(
  (ref) => DirectiveAuditRepository(ref.watch(apiClientProvider)),
);
