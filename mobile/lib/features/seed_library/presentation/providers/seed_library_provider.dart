import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';

/// Seed library list state
class SeedLibraryListState {
  final List<SeedLibrary> libraries;
  final bool isLoading;
  final String? error;
  final int page;
  final bool hasMore;

  const SeedLibraryListState({
    this.libraries = const [],
    this.isLoading = false,
    this.error,
    this.page = 1,
    this.hasMore = true,
  });

  SeedLibraryListState copyWith({
    List<SeedLibrary>? libraries,
    bool? isLoading,
    String? error,
    int? page,
    bool? hasMore,
  }) {
    return SeedLibraryListState(
      libraries: libraries ?? this.libraries,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      page: page ?? this.page,
      hasMore: hasMore ?? this.hasMore,
    );
  }
}

/// Seed library list notifier
class SeedLibraryListNotifier extends StateNotifier<SeedLibraryListState> {
  SeedLibraryListNotifier(this._repository) : super(const SeedLibraryListState());

  final SeedLibraryRepository _repository;

  Future<void> loadLibraries({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
    bool refresh = false,
  }) async {
    if (state.isLoading) return;

    if (refresh) {
      state = const SeedLibraryListState();
    }

    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _repository.listLibraries(
        category: category,
        visibility: visibility,
        isOfficial: isOfficial,
        isFeatured: isFeatured,
        search: search,
        page: refresh ? 1 : state.page,
        pageSize: 20,
      );

      state = state.copyWith(
        libraries: refresh ? response.items : [...state.libraries, ...response.items],
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
    await loadLibraries();
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
  final SeedLibrary? library;
  final List<SeedItem> items;
  final bool isLoadingLibrary;
  final bool isLoadingItems;
  final String? error;
  final bool isSubscribed;
  final int itemsPage;
  final bool hasMoreItems;

  const SeedLibraryDetailState({
    this.library,
    this.items = const [],
    this.isLoadingLibrary = false,
    this.isLoadingItems = false,
    this.error,
    this.isSubscribed = false,
    this.itemsPage = 1,
    this.hasMoreItems = true,
  });

  SeedLibraryDetailState copyWith({
    SeedLibrary? library,
    List<SeedItem>? items,
    bool? isLoadingLibrary,
    bool? isLoadingItems,
    String? error,
    bool? isSubscribed,
    int? itemsPage,
    bool? hasMoreItems,
  }) {
    return SeedLibraryDetailState(
      library: library ?? this.library,
      items: items ?? this.items,
      isLoadingLibrary: isLoadingLibrary ?? this.isLoadingLibrary,
      isLoadingItems: isLoadingItems ?? this.isLoadingItems,
      error: error,
      isSubscribed: isSubscribed ?? this.isSubscribed,
      itemsPage: itemsPage ?? this.itemsPage,
      hasMoreItems: hasMoreItems ?? this.hasMoreItems,
    );
  }
}

/// Single library notifier
class SeedLibraryDetailNotifier extends StateNotifier<SeedLibraryDetailState> {
  SeedLibraryDetailNotifier(this._repository, this.libraryId)
      : super(const SeedLibraryDetailState()) {
    loadLibrary();
    loadItems();
  }

  final SeedLibraryRepository _repository;
  final String libraryId;

  Future<void> loadLibrary() async {
    state = state.copyWith(isLoadingLibrary: true, error: null);

    try {
      final library = await _repository.getLibrary(libraryId);
      state = state.copyWith(
        library: library,
        isLoadingLibrary: false,
        isSubscribed: library.isSubscribed ?? false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingLibrary: false,
        error: e.toString(),
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
        pageSize: 20,
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
    } catch (e) {
      // Revert on error
      state = state.copyWith(isSubscribed: wasSubscribed);
      state = state.copyWith(error: e.toString());
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
}

/// Subscriptions state
class SubscriptionsState {
  final List<UserLibrarySubscription> subscriptions;
  final bool isLoading;
  final String? error;

  const SubscriptionsState({
    this.subscriptions = const [],
    this.isLoading = false,
    this.error,
  });

  SubscriptionsState copyWith({
    List<UserLibrarySubscription>? subscriptions,
    bool? isLoading,
    String? error,
  }) {
    return SubscriptionsState(
      subscriptions: subscriptions ?? this.subscriptions,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Subscriptions notifier
class SubscriptionsNotifier extends StateNotifier<SubscriptionsState> {
  SubscriptionsNotifier(this._repository) : super(const SubscriptionsState());

  final SeedLibraryRepository _repository;

  Future<void> loadSubscriptions() async {
    state = state.copyWith(isLoading: true, error: null);

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
          subscriptions: List.from(state.subscriptions)..insert(existingIndex, subscription),
        );
        state = state.copyWith(error: e.toString());
      }
    } else {
      // Subscribe
      try {
        final newSubscription =
            await _repository.subscribeToLibrary(libraryId);
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
final seedLibraryListProvider =
    StateNotifierProvider.family<SeedLibraryListNotifier, SeedLibraryListState, ({
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
      notifier.loadLibraries(
        category: filters.category,
        visibility: filters.visibility,
        isOfficial: filters.isOfficial,
        isFeatured: filters.isFeatured,
        search: filters.search,
        refresh: true,
      );
    }

    return notifier;
  },
);

final seedLibraryDetailProvider =
    StateNotifierProvider.family<SeedLibraryDetailNotifier, SeedLibraryDetailState, String>(
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
    notifier.loadSubscriptions();
    return notifier;
  },
);
