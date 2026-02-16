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
      return PaginatedResponse<SeedLibrary>.fromShared(
        ApiResponseParser.parsePaginated<SeedLibrary>(
          response.data,
          (json) => SeedLibrary.fromJson(json as Map<String, dynamic>),
          action: 'list libraries',
        ),
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
      return SeedLibrary.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'get library'),
      );
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
      return SeedLibrary.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'create library'),
      );
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
      return SeedLibrary.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'update library'),
      );
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
      return PaginatedResponse<SeedItem>.fromShared(
        ApiResponseParser.parsePaginated<SeedItem>(
          response.data,
          (json) => SeedItem.fromJson(json as Map<String, dynamic>),
          action: 'list library items',
        ),
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
      return SeedItem.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'add library item'),
      );
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
      return SeedItem.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'update library item'),
      );
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
      return UserLibrarySubscription.fromJson(
        ApiResponseParser.unwrapMap(response.data, action: 'subscribe library'),
      );
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
      return PaginatedResponse<UserLibrarySubscription>.fromShared(
        ApiResponseParser.parsePaginated<UserLibrarySubscription>(
          response.data,
          (json) => UserLibrarySubscription.fromJson(json as Map<String, dynamic>),
          action: 'list subscriptions',
        ),
      );
    } on DioException catch (e) {
      final error =
          e.response?.data?['detail'] ?? 'Failed to load subscriptions';
      throw Exception(error.toString());
    }
  }

  /// Query across subscribed libraries
  Future<List<SeedItem>> crossLibraryQuery({
    required String query,
    List<String>? itemTypes,
    List<String>? subjects,
    List<DifficultyLevel>? difficultyLevels,
    List<String>? tags,
    bool useSubscribedOnly = true,
    bool includeOfficial = true,
    int? limit,
  }) async {
    try {
      final payload = <String, dynamic>{
        'query': query,
        'use_subscribed_only': useSubscribedOnly,
        'include_official': includeOfficial,
      };

      if (itemTypes != null && itemTypes.isNotEmpty) {
        payload['item_types'] = itemTypes;
      }
      if (subjects != null && subjects.isNotEmpty) {
        payload['subjects'] = subjects;
      }
      if (difficultyLevels != null && difficultyLevels.isNotEmpty) {
        payload['difficulty_levels'] =
            difficultyLevels.map((e) => e.name).toList();
      }
      if (tags != null && tags.isNotEmpty) {
        payload['tags'] = tags;
      }
      if (limit != null) {
        payload['limit'] = limit;
      }

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryCrossQuery,
        data: payload,
      );

      final data = response.data ?? const <String, dynamic>{};
      final wrapped = data['data'] is Map<String, dynamic>
          ? data['data'] as Map<String, dynamic>
          : data;
      final items = wrapped['items'] as List<dynamic>? ?? const [];
      return items
          .whereType<Map<String, dynamic>>()
          .map((json) => SeedItem.fromJson(json))
          .toList();
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Query failed';
      throw Exception(error.toString());
    }
  }

  /// Get few-shot examples for prompt enhancement
  Future<List<Map<String, dynamic>>> getFewShotExamples({
    String? subject,
    DifficultyLevel? difficultyLevel,
    String? taskType,
    int? limit,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (subject != null) queryParams['subject'] = subject;
      if (difficultyLevel != null) {
        queryParams['difficulty_level'] = difficultyLevel.name;
      }
      if (taskType != null) queryParams['task_type'] = taskType;
      if (limit != null) queryParams['count'] = limit;

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryFewShot,
        queryParameters: queryParams,
      );
      final rawList = response.data is List
          ? response.data as List<dynamic>
          : ApiResponseParser.unwrapList(
              response.data,
              action: 'get few shot examples',
            );
      return rawList
          .whereType<Map<String, dynamic>>()
          .toList();
    } on DioException catch (e) {
      final error =
          e.response?.data?['detail'] ?? 'Failed to get examples';
      throw Exception(error.toString());
    }
  }
}

/// Provider for SeedLibraryRepository
final seedLibraryRepositoryProvider = Provider<SeedLibraryRepository>(
  (ref) => SeedLibraryRepository(ref.watch(apiClientProvider)),
);
