import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';

void main() {
  test(
    'toggleApplied uses existing subscription even when it is not on the first page',
    () async {
      final repo = _PagedSubscriptionSeedLibraryRepository();
      final container = ProviderContainer(
        overrides: [
          seedLibraryRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);

      final notifier = container.read(
        seedLibraryDetailProvider('seed-lib-1').notifier,
      );

      await notifier.loadLibrary();
      await notifier.toggleApplied();

      final state = container.read(seedLibraryDetailProvider('seed-lib-1'));
      expect(repo.subscribeCalls, 0);
      expect(repo.updateCalls, 1);
      expect(state.subscription?.isEnabled, isTrue);
      expect(state.isSubscribed, isTrue);
    },
  );

  test('markNotSuitable disables the subscription and records explicit feedback',
      () async {
    final repo = _PagedSubscriptionSeedLibraryRepository();
    final container = ProviderContainer(
      overrides: [
        seedLibraryRepositoryProvider.overrideWithValue(repo),
      ],
    );
    addTearDown(container.dispose);

    final notifier = container.read(
      seedLibraryDetailProvider('seed-lib-1').notifier,
    );

    await notifier.loadLibrary();
    await notifier.markNotSuitable();

    final state = container.read(seedLibraryDetailProvider('seed-lib-1'));
    expect(repo.lastNotes, 'not_suitable');
    expect(state.subscription?.isEnabled, isFalse);
  });
}

class _PagedSubscriptionSeedLibraryRepository extends SeedLibraryRepository {
  _PagedSubscriptionSeedLibraryRepository() : super(_UnusedApiClient());

  int subscribeCalls = 0;
  int updateCalls = 0;
  String? lastNotes;

  final SeedLibrary _library = SeedLibrary(
    id: 'seed-lib-1',
    name: '验收知识库',
    description: '用于验证分页订阅命中',
    category: LibraryCategory.teachingContent,
    visibility: LibraryVisibility.official,
    language: 'zh',
    isOfficial: true,
    isFeatured: true,
    usageCount: 12,
    itemCount: 1,
    subscriberCount: 3,
    createdAt: DateTime(2026, 3),
    updatedAt: DateTime(2026, 3),
  );

  UserLibrarySubscription _subscription({required bool enabled}) =>
      UserLibrarySubscription(
        id: 'sub-1',
        userId: 'user-1',
        libraryId: 'seed-lib-1',
        isEnabled: enabled,
        priority: 100,
        subscribedAt: DateTime(2026, 3),
        createdAt: DateTime(2026, 3),
        updatedAt: DateTime(2026, 3),
        notes: 'applied',
      );

  @override
  Future<SeedLibrary> getLibrary(String id) async => _library;

  @override
  Future<PaginatedResponse<UserLibrarySubscription>> getMySubscriptions({
    bool? isEnabled,
    int page = 1,
    int pageSize = 20,
  }) async {
    if (page == 1) {
      return PaginatedResponse<UserLibrarySubscription>(
        items: const [],
        total: 1,
        page: 1,
        pageSize: pageSize,
        totalPages: 2,
      );
    }
    return PaginatedResponse<UserLibrarySubscription>(
      items: [_subscription(enabled: false)],
      total: 1,
      page: 2,
      pageSize: pageSize,
      totalPages: 2,
    );
  }

  @override
  Future<UserLibrarySubscription> subscribeToLibrary(
    String libraryId, {
    int? priority,
    String? notes,
  }) async {
    subscribeCalls += 1;
    throw Exception('should not subscribe again');
  }

  @override
  Future<UserLibrarySubscription> updateSubscription(
    String libraryId,
    UpdateSubscriptionRequest request,
  ) async {
    updateCalls += 1;
    lastNotes = request.notes;
    return _subscription(enabled: request.isEnabled ?? true).copyWith(
      notes: request.notes,
    );
  }

  @override
  Future<PaginatedResponse<SeedItem>> listLibraryItems(
    String libraryId, {
    ItemType? itemType,
    String? subject,
    DifficultyLevel? difficultyLevel,
    String? search,
    int page = 1,
    int pageSize = 20,
  }) async =>
      PaginatedResponse<SeedItem>(
        items: const [],
        total: 0,
        page: 1,
        pageSize: pageSize,
        totalPages: 1,
      );
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
