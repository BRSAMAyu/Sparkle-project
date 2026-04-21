import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';

/// Seed library list state
class SeedLibraryListState {
  const SeedLibraryListState({
    this.libraries = const [],
    this.isLoading = false,
    this.error,
    this.page = 1,
    this.hasMore = true,
  });
  final List<SeedLibrary> libraries;
  final bool isLoading;
  final String? error;
  final int page;
  final bool hasMore;

  SeedLibraryListState copyWith({
    List<SeedLibrary>? libraries,
    bool? isLoading,
    String? error,
    int? page,
    bool? hasMore,
  }) =>
      SeedLibraryListState(
        libraries: libraries ?? this.libraries,
        isLoading: isLoading ?? this.isLoading,
        error: error,
        page: page ?? this.page,
        hasMore: hasMore ?? this.hasMore,
      );
}

/// Seed library list notifier
class SeedLibraryListNotifier extends StateNotifier<SeedLibraryListState> {
  SeedLibraryListNotifier(this._repository)
      : super(const SeedLibraryListState());

  final SeedLibraryRepository _repository;
  LibraryCategory? _lastCategory;
  LibraryVisibility? _lastVisibility;
  bool? _lastIsOfficial;
  bool? _lastIsFeatured;
  String? _lastSearch;

  Future<void> loadLibraries({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
    bool refresh = false,
  }) async {
    if (state.isLoading) return;

    _lastCategory = category;
    _lastVisibility = visibility;
    _lastIsOfficial = isOfficial;
    _lastIsFeatured = isFeatured;
    _lastSearch = search;

    if (refresh) {
      state = const SeedLibraryListState();
    }

    state = state.copyWith(isLoading: true);

    try {
      final response = await _repository.listLibraries(
        category: category,
        visibility: visibility,
        isOfficial: isOfficial,
        isFeatured: isFeatured,
        search: search,
        page: refresh ? 1 : state.page,
      );

      state = state.copyWith(
        libraries:
            refresh ? response.items : [...state.libraries, ...response.items],
        isLoading: false,
        page: state.page + 1,
        hasMore: response.page < response.totalPages,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadMore() async {
    if (!state.hasMore || state.isLoading) return;
    await loadLibraries(
      category: _lastCategory,
      visibility: _lastVisibility,
      isOfficial: _lastIsOfficial,
      isFeatured: _lastIsFeatured,
      search: _lastSearch,
    );
  }

  Future<void> refresh({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
  }) async {
    await loadLibraries(
      category: category,
      visibility: visibility,
      isOfficial: isOfficial,
      isFeatured: isFeatured,
      search: search,
      refresh: true,
    );
  }
}

/// Single library state
class SeedLibraryDetailState {
  const SeedLibraryDetailState({
    this.library,
    this.items = const [],
    this.isLoadingLibrary = false,
    this.isLoadingItems = false,
    this.error,
    this.isSubscribed = false,
    this.subscription,
    this.activeSubscriptions = const [],
    this.itemsPage = 1,
    this.hasMoreItems = true,
  });
  final SeedLibrary? library;
  final List<SeedItem> items;
  final bool isLoadingLibrary;
  final bool isLoadingItems;
  final String? error;
  final bool isSubscribed;
  final UserLibrarySubscription? subscription;
  final List<UserLibrarySubscription> activeSubscriptions;
  final int itemsPage;
  final bool hasMoreItems;

  SeedLibraryDetailState copyWith({
    SeedLibrary? library,
    List<SeedItem>? items,
    bool? isLoadingLibrary,
    bool? isLoadingItems,
    String? error,
    bool? isSubscribed,
    UserLibrarySubscription? subscription,
    List<UserLibrarySubscription>? activeSubscriptions,
    int? itemsPage,
    bool? hasMoreItems,
  }) =>
      SeedLibraryDetailState(
        library: library ?? this.library,
        items: items ?? this.items,
        isLoadingLibrary: isLoadingLibrary ?? this.isLoadingLibrary,
        isLoadingItems: isLoadingItems ?? this.isLoadingItems,
        error: error,
        isSubscribed: isSubscribed ?? this.isSubscribed,
        subscription: subscription ?? this.subscription,
        activeSubscriptions: activeSubscriptions ?? this.activeSubscriptions,
        itemsPage: itemsPage ?? this.itemsPage,
        hasMoreItems: hasMoreItems ?? this.hasMoreItems,
      );
}

/// Single library notifier
class SeedLibraryDetailNotifier extends StateNotifier<SeedLibraryDetailState> {
  SeedLibraryDetailNotifier(this._repository, this.libraryId)
      : super(const SeedLibraryDetailState()) {
    unawaited(loadLibrary());
    unawaited(loadItems());
  }

  final SeedLibraryRepository _repository;
  final String libraryId;

  String _friendlyError(Object error, String fallback) {
    final raw = error.toString().replaceFirst('Exception: ', '').trim();
    if (raw.isEmpty || raw.toLowerCase() == 'null') {
      return fallback;
    }
    return raw;
  }

  Future<void> loadLibrary() async {
    state = state.copyWith(
      isLoadingLibrary: true,
      error: state.library == null ? null : state.error,
    );

    try {
      final library = await _repository.getLibrary(libraryId);
      state = state.copyWith(
        library: library,
        isLoadingLibrary: false,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingLibrary: false,
        error: _friendlyError(e, '种子库详情加载失败，请稍后再试'),
      );
      return;
    }

    try {
      final matchedSubscription =
          await _repository.findMySubscriptionForLibrary(libraryId);
      final subscriptions = await _repository.getMySubscriptions(
        isEnabled: true,
        pageSize: 100,
      );
      final activeSubscriptions = subscriptions.items
          .where((sub) => sub.isEnabled)
          .toList()
        ..sort((a, b) => b.priority.compareTo(a.priority));
      state = state.copyWith(
        isSubscribed: matchedSubscription != null,
        subscription: matchedSubscription,
        activeSubscriptions: activeSubscriptions,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isSubscribed: false,
        subscription: null,
        activeSubscriptions: const [],
        error:
            state.library == null ? _friendlyError(e, '种子库状态加载失败，请稍后再试') : null,
      );
    }
  }

  Future<void> loadItems({bool refresh = false}) async {
    if (state.isLoadingItems) return;

    if (refresh) {
      state = state.copyWith(itemsPage: 1);
    }

    state = state.copyWith(isLoadingItems: true);

    try {
      final response = await _repository.listLibraryItems(
        libraryId,
        page: refresh ? 1 : state.itemsPage,
      );

      state = state.copyWith(
        items: refresh ? response.items : [...state.items, ...response.items],
        isLoadingItems: false,
        itemsPage: state.itemsPage + 1,
        hasMoreItems: response.page < response.totalPages,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingItems: false,
        error: e.toString(),
      );
    }
  }

  Future<void> toggleSubscription() async {
    if (state.library == null) return;

    final wasSubscribed = state.isSubscribed;

    // Optimistic update
    state = state.copyWith(isSubscribed: !wasSubscribed);

    try {
      if (!wasSubscribed) {
        await _repository.subscribeToLibrary(libraryId);
      } else {
        await _repository.unsubscribeFromLibrary(libraryId);
      }
      await loadLibrary();
    } catch (e) {
      // Revert on error
      state = state.copyWith(isSubscribed: wasSubscribed);
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> toggleApplied() async {
    if (state.library == null) {
      return;
    }
    try {
      await loadLibrary();
      final current = state.subscription ??
          await _repository.findMySubscriptionForLibrary(libraryId);
      if (current == null) {
        final maxPriority = state.activeSubscriptions.isEmpty
            ? 100
            : state.activeSubscriptions.first.priority + 10;
        final subscription = await _repository.subscribeToLibrary(
          libraryId,
          priority: maxPriority,
          notes: 'applied',
        );
        state = state.copyWith(
          subscription: subscription,
          isSubscribed: true,
          activeSubscriptions: [
            subscription,
            ...state.activeSubscriptions.where(
              (item) => item.libraryId != subscription.libraryId,
            ),
          ]..sort((a, b) => b.priority.compareTo(a.priority)),
          error: null,
        );
      } else {
        final updated = await _repository.updateSubscription(
          libraryId,
          UpdateSubscriptionRequest(
            isEnabled: !current.isEnabled,
          ),
        );
        final refreshedSubscriptions = [
          updated,
          ...state.activeSubscriptions.where(
            (item) => item.libraryId != updated.libraryId,
          ),
        ].where((item) => item.isEnabled).toList()
          ..sort((a, b) => b.priority.compareTo(a.priority));
        state = state.copyWith(
          subscription: updated,
          isSubscribed: true,
          activeSubscriptions: refreshedSubscriptions,
          error: null,
        );
      }
    } catch (e) {
      final raw = e.toString().toLowerCase();
      if (raw.contains('already subscribe')) {
        await loadLibrary();
        final existing = state.subscription ??
            await _repository.findMySubscriptionForLibrary(libraryId);
        if (existing != null) {
          final updated = await _repository.updateSubscription(
            libraryId,
            UpdateSubscriptionRequest(
              isEnabled: true,
            ),
          );
          state = state.copyWith(
            subscription: updated,
            isSubscribed: true,
            activeSubscriptions: [
              updated,
              ...state.activeSubscriptions.where(
                (item) => item.libraryId != updated.libraryId,
              ),
            ].where((item) => item.isEnabled).toList()
              ..sort((a, b) => b.priority.compareTo(a.priority)),
            error: null,
          );
          return;
        }
      }
      await loadLibrary();
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<void> setAsPrimaryLibrary() async {
    try {
      final maxPriority = state.activeSubscriptions.isEmpty
          ? 100
          : state.activeSubscriptions.first.priority + 10;
      final current = state.subscription ??
          await _repository.findMySubscriptionForLibrary(libraryId);
      if (current == null) {
        await _repository.subscribeToLibrary(
          libraryId,
          priority: maxPriority,
          notes: 'primary',
        );
      } else {
        await _repository.updateSubscription(
          libraryId,
          UpdateSubscriptionRequest(
            isEnabled: true,
            priority: maxPriority,
            notes: 'primary',
          ),
        );
      }
      await loadLibrary();
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<void> markNotSuitable() async {
    if (state.library == null) {
      return;
    }
    try {
      await loadLibrary();
      final current = state.subscription ??
          await _repository.findMySubscriptionForLibrary(libraryId) ??
          await _repository.subscribeToLibrary(
            libraryId,
            priority: 0,
            notes: 'applied',
          );
      final updated = await _repository.updateSubscription(
        libraryId,
        UpdateSubscriptionRequest(
          isEnabled: false,
          notes: 'not_suitable',
        ),
      );
      state = state.copyWith(
        subscription: updated,
        isSubscribed: true,
        activeSubscriptions: state.activeSubscriptions
            .where((item) => item.libraryId != current.libraryId)
            .toList()
          ..sort((a, b) => b.priority.compareTo(a.priority)),
        error: null,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<void> submitRating({
    required double score,
    String? comment,
  }) async {
    try {
      final updatedLibrary = await _repository.rateLibrary(
        libraryId,
        RateLibraryRequest(score: score, comment: comment),
      );
      state = state.copyWith(library: updatedLibrary);
      await loadLibrary();
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<void> updateLibrary({
    required String name,
    String? description,
  }) async {
    try {
      final updated = await _repository.updateLibrary(
        libraryId,
        UpdateLibraryRequest(name: name, description: description),
      );
      state = state.copyWith(library: updated);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<void> deleteLibrary() async {
    try {
      await _repository.deleteLibrary(libraryId);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<SeedItem> addItem({
    required ItemType itemType,
    String? title,
    String? content,
    Map<String, dynamic>? contentData,
    String? subject,
    DifficultyLevel? difficultyLevel,
    List<String>? tags,
  }) async {
    try {
      final item = await _repository.addItem(
        libraryId,
        itemType: itemType,
        title: title,
        content: content,
        contentData: contentData,
        subject: subject,
        difficultyLevel: difficultyLevel,
        tags: tags,
      );

      // Add to items list
      state = state.copyWith(
        items: [item, ...state.items],
      );

      // Update library item count
      if (state.library != null) {
        state = state.copyWith(
          library: state.library!.copyWith(
            itemCount: state.library!.itemCount + 1,
          ),
        );
      }

      return item;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  Future<Map<String, dynamic>> importItems(
    List<Map<String, dynamic>> items, {
    bool continueOnError = true,
  }) async {
    try {
      final result = await _repository.importItems(
        libraryId,
        items: items,
        continueOnError: continueOnError,
      );
      await loadLibrary();
      await loadItems(refresh: true);
      return result;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }
}

/// Subscriptions state
class SubscriptionsState {
  const SubscriptionsState({
    this.subscriptions = const [],
    this.isLoading = false,
    this.error,
  });
  final List<UserLibrarySubscription> subscriptions;
  final bool isLoading;
  final String? error;

  SubscriptionsState copyWith({
    List<UserLibrarySubscription>? subscriptions,
    bool? isLoading,
    String? error,
  }) =>
      SubscriptionsState(
        subscriptions: subscriptions ?? this.subscriptions,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

/// Subscriptions notifier
class SubscriptionsNotifier extends StateNotifier<SubscriptionsState> {
  SubscriptionsNotifier(this._repository) : super(const SubscriptionsState());

  final SeedLibraryRepository _repository;

  Future<void> loadSubscriptions() async {
    state = state.copyWith(isLoading: true);

    try {
      final response = await _repository.getMySubscriptions();

      // Load library details for each subscription
      final subscriptionsWithLibraries = await Future.wait(
        response.items.map((sub) async {
          try {
            final library = await _repository.getLibrary(sub.libraryId);
            return sub.copyWith(library: library);
          } catch (_) {
            return sub;
          }
        }),
      );

      state = state.copyWith(
        subscriptions: subscriptionsWithLibraries,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> toggleSubscription(String libraryId) async {
    final existingIndex =
        state.subscriptions.indexWhere((sub) => sub.libraryId == libraryId);

    if (existingIndex >= 0) {
      // Unsubscribe
      final subscription = state.subscriptions[existingIndex];
      state = state.copyWith(
        subscriptions: List.from(state.subscriptions)..removeAt(existingIndex),
      );

      try {
        await _repository.unsubscribeFromLibrary(libraryId);
      } catch (e) {
        // Revert on error
        state = state.copyWith(
          subscriptions: List.from(state.subscriptions)
            ..insert(existingIndex, subscription),
        );
        state = state.copyWith(error: e.toString());
      }
    } else {
      // Subscribe
      try {
        final newSubscription = await _repository.subscribeToLibrary(libraryId);
        final library = await _repository.getLibrary(libraryId);
        state = state.copyWith(
          subscriptions: [
            ...state.subscriptions,
            newSubscription.copyWith(library: library),
          ],
        );
      } catch (e) {
        state = state.copyWith(error: e.toString());
      }
    }
  }
}

/// Providers
final seedLibraryListProvider = StateNotifierProvider.family<
    SeedLibraryListNotifier,
    SeedLibraryListState,
    ({
      LibraryCategory? category,
      LibraryVisibility? visibility,
      bool? isOfficial,
      bool? isFeatured,
      String? search,
    })?>(
  (ref, filters) {
    final repository = ref.watch(seedLibraryRepositoryProvider);
    final notifier = SeedLibraryListNotifier(repository);

    if (filters != null) {
      unawaited(
        notifier.loadLibraries(
          category: filters.category,
          visibility: filters.visibility,
          isOfficial: filters.isOfficial,
          isFeatured: filters.isFeatured,
          search: filters.search,
          refresh: true,
        ),
      );
    }

    return notifier;
  },
);

final seedLibraryDetailProvider = StateNotifierProvider.family<
    SeedLibraryDetailNotifier, SeedLibraryDetailState, String>(
  (ref, libraryId) {
    final repository = ref.watch(seedLibraryRepositoryProvider);
    return SeedLibraryDetailNotifier(repository, libraryId);
  },
);

final subscriptionsProvider =
    StateNotifierProvider<SubscriptionsNotifier, SubscriptionsState>(
  (ref) {
    final repository = ref.watch(seedLibraryRepositoryProvider);
    final notifier = SubscriptionsNotifier(repository);
    // Auto-load subscriptions
    unawaited(notifier.loadSubscriptions());
    return notifier;
  },
);
