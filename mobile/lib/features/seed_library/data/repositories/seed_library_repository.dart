import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';

/// Seed Library Repository
/// Handles all seed library API calls
class SeedLibraryRepository {
  SeedLibraryRepository(this._apiClient);

  final ApiClient _apiClient;

  /// List libraries with optional filtering
  Future<PaginatedResponse<SeedLibrary>> listLibraries({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    String? language,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
    int page = 1,
    int pageSize = 20,
    String? sortBy,
    String? sortOrder,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
      };

      if (category != null) {
        queryParams['category'] = category.name;
      }
      if (visibility != null) {
        queryParams['visibility'] = visibility.name;
      }
      if (language != null) {
        queryParams['language'] = language;
      }
      if (isOfficial != null) {
        queryParams['is_official'] = isOfficial;
      }
      if (isFeatured != null) {
        queryParams['is_featured'] = isFeatured;
      }
      if (search != null && search.isNotEmpty) {
        queryParams['search'] = search;
      }
      if (sortBy != null) {
        queryParams['sort_by'] = sortBy;
      }
      if (sortOrder != null) {
        queryParams['sort_order'] = sortOrder;
      }

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibraries,
        queryParameters: queryParams,
      );

      final payload = response.data ?? const <String, dynamic>{};
      final itemsJson = ApiResponseParser.unwrapList(
        payload,
        action: 'listLibraries',
      );
      final meta = (payload['meta'] as Map<String, dynamic>?) ?? payload;
      return PaginatedResponse<SeedLibrary>(
        items: itemsJson
            .map((json) => SeedLibrary.fromJson(json as Map<String, dynamic>))
            .toList(),
        total: (meta['total'] as num?)?.toInt() ?? itemsJson.length,
        page: (meta['page'] as num?)?.toInt() ?? 1,
        pageSize: (meta['page_size'] as num?)?.toInt() ?? itemsJson.length,
        totalPages: (meta['total_pages'] as num?)?.toInt() ?? 1,
      );
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to load libraries';
      throw Exception(error.toString());
    }
  }

  /// Get library by ID
  Future<SeedLibrary> getLibrary(String id) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibrary(id),
      );

      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'getLibrary');
      return SeedLibrary.fromJson(data);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to load library';
      throw Exception(error.toString());
    }
  }

  /// Create a new library
  Future<SeedLibrary> createLibrary(CreateLibraryRequest request) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibraries,
        data: request.toJson(),
      );

      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'createLibrary');
      return SeedLibrary.fromJson(data);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to create library';
      throw Exception(error.toString());
    }
  }

  /// Update library
  Future<SeedLibrary> updateLibrary(
    String id,
    UpdateLibraryRequest request,
  ) async {
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.seedLibrary(id),
        data: request.toJson(),
      );

      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'updateLibrary');
      return SeedLibrary.fromJson(data);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to update library';
      throw Exception(error.toString());
    }
  }

  /// Delete library
  Future<void> deleteLibrary(String id) async {
    try {
      await _apiClient.delete<dynamic>(ApiEndpoints.seedLibrary(id));
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to delete library';
      throw Exception(error.toString());
    }
  }

  /// List library items
  Future<PaginatedResponse<SeedItem>> listLibraryItems(
    String libraryId, {
    ItemType? itemType,
    String? subject,
    DifficultyLevel? difficultyLevel,
    String? search,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
      };

      if (itemType != null) {
        queryParams['item_type'] = itemType.name;
      }
      if (subject != null && subject.isNotEmpty) {
        queryParams['subject'] = subject;
      }
      if (difficultyLevel != null) {
        queryParams['difficulty_level'] = difficultyLevel.name;
      }
      if (search != null && search.isNotEmpty) {
        queryParams['search'] = search;
      }

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryItems(libraryId),
        queryParameters: queryParams,
      );

      final payload = response.data ?? const <String, dynamic>{};
      final itemsJson = ApiResponseParser.unwrapList(
        payload,
        action: 'listLibraryItems',
      );
      final meta = (payload['meta'] as Map<String, dynamic>?) ?? payload;
      return PaginatedResponse<SeedItem>(
        items: itemsJson
            .map((json) => SeedItem.fromJson(json as Map<String, dynamic>))
            .toList(),
        total: (meta['total'] as num?)?.toInt() ?? itemsJson.length,
        page: (meta['page'] as num?)?.toInt() ?? 1,
        pageSize: (meta['page_size'] as num?)?.toInt() ?? itemsJson.length,
        totalPages: (meta['total_pages'] as num?)?.toInt() ?? 1,
      );
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to load items';
      throw Exception(error.toString());
    }
  }

  /// Add item to library
  Future<SeedItem> addItem(
    String libraryId, {
    required ItemType itemType,
    String? title,
    String? content,
    Map<String, dynamic>? contentData,
    String? subject,
    DifficultyLevel? difficultyLevel,
    List<String>? tags,
  }) async {
    try {
      final data = <String, dynamic>{
        'item_type': itemType.name,
      };

      if (title != null) data['title'] = title;
      if (content != null) data['content'] = content;
      if (contentData != null) data['content_data'] = contentData;
      if (subject != null) data['subject'] = subject;
      if (difficultyLevel != null) {
        data['difficulty_level'] = difficultyLevel.name;
      }
      if (tags != null) data['tags'] = tags;

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryItems(libraryId),
        data: data,
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'addItem');
      return SeedItem.fromJson(payload);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to add item';
      throw Exception(error.toString());
    }
  }

  /// Update item
  Future<SeedItem> updateItem(
    String libraryId,
    String itemId, {
    String? title,
    String? content,
    Map<String, dynamic>? contentData,
    String? subject,
    DifficultyLevel? difficultyLevel,
    List<String>? tags,
    bool? isActive,
  }) async {
    try {
      final data = <String, dynamic>{};

      if (title != null) data['title'] = title;
      if (content != null) data['content'] = content;
      if (contentData != null) data['content_data'] = contentData;
      if (subject != null) data['subject'] = subject;
      if (difficultyLevel != null) {
        data['difficulty_level'] = difficultyLevel.name;
      }
      if (tags != null) data['tags'] = tags;
      if (isActive != null) data['is_active'] = isActive;

      final response = await _apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryItem(libraryId, itemId),
        data: data,
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'updateItem');
      return SeedItem.fromJson(payload);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to update item';
      throw Exception(error.toString());
    }
  }

  /// Delete item
  Future<void> deleteItem(String libraryId, String itemId) async {
    try {
      await _apiClient.delete<dynamic>(
        ApiEndpoints.seedLibraryItem(libraryId, itemId),
      );
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to delete item';
      throw Exception(error.toString());
    }
  }

  /// Subscribe to library
  Future<UserLibrarySubscription> subscribeToLibrary(
    String libraryId, {
    int? priority,
    String? notes,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (priority != null) data['priority'] = priority;
      if (notes != null) data['notes'] = notes;

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibrarySubscribe(libraryId),
        data: data,
      );

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'subscribeToLibrary',
      );
      return UserLibrarySubscription.fromJson(payload);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to subscribe';
      throw Exception(error.toString());
    }
  }

  /// Unsubscribe from library
  Future<void> unsubscribeFromLibrary(String libraryId) async {
    try {
      await _apiClient.delete<dynamic>(
        ApiEndpoints.seedLibraryUnsubscribe(libraryId),
      );
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to unsubscribe';
      throw Exception(error.toString());
    }
  }

  Future<UserLibrarySubscription> updateSubscription(
    String libraryId,
    UpdateSubscriptionRequest request,
  ) async {
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.seedLibrarySubscription(libraryId),
        data: request.toJson(),
      );
      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'updateSubscription',
      );
      return UserLibrarySubscription.fromJson(payload);
    } on DioException catch (e) {
      final error =
          e.response?.data?['detail'] ?? 'Failed to update subscription';
      throw Exception(error.toString());
    }
  }

  Future<SeedLibrary> rateLibrary(
    String libraryId,
    RateLibraryRequest request,
  ) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryRating(libraryId),
        data: request.toJson(),
      );
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'rateLibrary');
      return SeedLibrary.fromJson(data);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to rate library';
      throw Exception(error.toString());
    }
  }

  /// Get user's subscriptions
  Future<PaginatedResponse<UserLibrarySubscription>> getMySubscriptions({
    bool? isEnabled,
    int page = 1,
    int pageSize = 20,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
      };

      if (isEnabled != null) {
        queryParams['is_enabled'] = isEnabled;
      }

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibrarySubscriptions,
        queryParameters: queryParams,
      );

      final payload = response.data ?? const <String, dynamic>{};
      final itemsJson = ApiResponseParser.unwrapList(
        payload,
        action: 'getMySubscriptions',
      );
      final meta = (payload['meta'] as Map<String, dynamic>?) ?? payload;
      return PaginatedResponse<UserLibrarySubscription>(
        items: itemsJson
            .map(
              (json) => UserLibrarySubscription.fromJson(
                json as Map<String, dynamic>,
              ),
            )
            .toList(),
        total: (meta['total'] as num?)?.toInt() ?? itemsJson.length,
        page: (meta['page'] as num?)?.toInt() ?? 1,
        pageSize: (meta['page_size'] as num?)?.toInt() ?? itemsJson.length,
        totalPages: (meta['total_pages'] as num?)?.toInt() ?? 1,
      );
    } on DioException catch (e) {
      final error =
          e.response?.data?['detail'] ?? 'Failed to load subscriptions';
      throw Exception(error.toString());
    }
  }

  /// Query across subscribed libraries
  Future<Map<String, List<SeedItem>>> crossLibraryQuery({
    required String query,
    List<String>? itemTypes,
    List<String>? subjects,
    List<DifficultyLevel>? difficultyLevels,
    List<String>? tags,
    int? limit,
  }) async {
    try {
      final data = <String, dynamic>{
        'query': query,
      };

      if (itemTypes != null && itemTypes.isNotEmpty) {
        data['item_types'] = itemTypes;
      }
      if (subjects != null && subjects.isNotEmpty) {
        data['subjects'] = subjects;
      }
      if (difficultyLevels != null && difficultyLevels.isNotEmpty) {
        data['difficulty_levels'] =
            difficultyLevels.map((e) => e.name).toList();
      }
      if (tags != null && tags.isNotEmpty) {
        data['tags'] = tags;
      }
      if (limit != null) {
        data['limit'] = limit;
      }

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryCrossQuery,
        data: data,
      );

      final payload = response.data ?? const <String, dynamic>{};
      final items = ApiResponseParser.unwrapList(
        payload['items'],
        action: 'crossLibraryQuery.items',
      );
      return {
        'items': items
            .map((json) => SeedItem.fromJson(json as Map<String, dynamic>))
            .toList(),
      };
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Query failed';
      throw Exception(error.toString());
    }
  }

  /// Get few-shot examples for prompt enhancement
  Future<List<Map<String, dynamic>>> getFewShotExamples({
    String? subject,
    int? limit,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (subject != null) queryParams['subject'] = subject;
      if (limit != null) queryParams['limit'] = limit;

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryFewShot,
        queryParameters: queryParams,
      );

      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getFewShotExamples',
      );
      return data
          .whereType<Map<String, dynamic>>()
          .toList();
    } on DioException catch (e) {
      final error =
          e.response?.data?['detail'] ?? 'Failed to get examples';
      throw Exception(error.toString());
    }
  }

  Future<Map<String, dynamic>> importItems(
    String libraryId, {
    required List<Map<String, dynamic>> items,
    bool continueOnError = true,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryImportItems(libraryId),
        data: {
          'items': items,
          'continue_on_error': continueOnError,
        },
      );
      return response.data ?? const <String, dynamic>{};
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to import items';
      throw Exception(error.toString());
    }
  }
}

/// Provider for SeedLibraryRepository
final seedLibraryRepositoryProvider = Provider<SeedLibraryRepository>(
  (ref) => SeedLibraryRepository(ref.watch(apiClientProvider)),
);
