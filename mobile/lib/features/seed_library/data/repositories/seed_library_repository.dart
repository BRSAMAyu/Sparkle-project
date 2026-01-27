import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
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

      final data = response.data!;
      return PaginatedResponse<SeedLibrary>.fromJson(
        data,
        (json) => SeedLibrary.fromJson(json as Map<String, dynamic>),
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

      return SeedLibrary.fromJson(response.data!);
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

      return SeedLibrary.fromJson(response.data!);
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

      return SeedLibrary.fromJson(response.data!);
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

      final data = response.data!;
      return PaginatedResponse<SeedItem>.fromJson(
        data,
        (json) => SeedItem.fromJson(json as Map<String, dynamic>),
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

      return SeedItem.fromJson(response.data!);
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

      return SeedItem.fromJson(response.data!);
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

      return UserLibrarySubscription.fromJson(response.data!);
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Failed to subscribe';
      throw Exception(error.toString());
    }
  }

  /// Unsubscribe from library
  Future<void> unsubscribeFromLibrary(String libraryId) async {
    try {
      await _apiClient.post<dynamic>(
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

      final data = response.data!;
      return PaginatedResponse<UserLibrarySubscription>.fromJson(
        data,
        (json) => UserLibrarySubscription.fromJson(json as Map<String, dynamic>),
      );
    } on DioException catch (e) {
      final error =
          e.response?.data?['detail'] ?? 'Failed to load subscriptions';
      throw Exception(error.toString());
    }
  }

  /// Query across subscribed libraries
  Future<Map<String, List<SeedItem>>> crossLibraryQuery({
    List<String>? itemTypes,
    List<String>? subjects,
    List<DifficultyLevel>? difficultyLevels,
    List<String>? tags,
    int? limit,
  }) async {
    try {
      final queryParams = <String, dynamic>{};

      if (itemTypes != null && itemTypes.isNotEmpty) {
        queryParams['item_types'] = itemTypes;
      }
      if (subjects != null && subjects.isNotEmpty) {
        queryParams['subjects'] = subjects;
      }
      if (difficultyLevels != null && difficultyLevels.isNotEmpty) {
        queryParams['difficulty_levels'] =
            difficultyLevels.map((e) => e.name).toList();
      }
      if (tags != null && tags.isNotEmpty) {
        queryParams['tags'] = tags;
      }
      if (limit != null) {
        queryParams['limit'] = limit;
      }

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.seedLibraryCrossQuery,
        queryParameters: queryParams,
      );

      final data = response.data!;
      final result = <String, List<SeedItem>>{};

      for (final entry in data.entries) {
        final itemsList = entry.value as List;
        result[entry.key] = itemsList
            .map((json) => SeedItem.fromJson(json as Map<String, dynamic>))
            .toList();
      }

      return result;
    } on DioException catch (e) {
      final error = e.response?.data?['detail'] ?? 'Query failed';
      throw Exception(error.toString());
    }
  }

  /// Get few-shot examples for prompt enhancement
  Future<List<SeedItem>> getFewShotExamples({
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

      final data = response.data!['items'] as List;
      return data
          .map((json) => SeedItem.fromJson(json as Map<String, dynamic>))
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
