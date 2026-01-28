import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/photon/data/repositories/photon_repository.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

// ========== Repository Provider ==========

final photonRepositoryProvider = Provider<PhotonRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PhotonRepository(apiClient);
});

// ========== Balance State ==========

class PhotonBalanceState {
  final PhotonBalance? balance;
  final bool isLoading;
  final String? error;

  PhotonBalanceState({
    this.balance,
    this.isLoading = false,
    this.error,
  });

  PhotonBalanceState copyWith({
    PhotonBalance? balance,
    bool? isLoading,
    String? error,
  }) {
    return PhotonBalanceState(
      balance: balance ?? this.balance,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

// ========== Balance Provider ==========

class PhotonBalanceNotifier extends StateNotifier<PhotonBalanceState> {
  PhotonBalanceNotifier(this._repository) : super(PhotonBalanceState()) {
    loadBalance();
  }

  final PhotonRepository _repository;

  Future<void> loadBalance() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final balance = await _repository.getBalance();
      state = state.copyWith(balance: balance, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  void refreshBalance() {
    loadBalance();
  }
}

final photonBalanceProvider =
    StateNotifierProvider<PhotonBalanceNotifier, PhotonBalanceState>((ref) {
  final repository = ref.watch(photonRepositoryProvider);
  return PhotonBalanceNotifier(repository);
});

// ========== Transactions State ==========

class PhotonTransactionsState {
  final List<PhotonTransaction> transactions;
  final bool isLoading;
  final String? error;
  final bool hasMore;
  final int currentOffset;

  PhotonTransactionsState({
    this.transactions = const [],
    this.isLoading = false,
    this.error,
    this.hasMore = true,
    this.currentOffset = 0,
  });

  PhotonTransactionsState copyWith({
    List<PhotonTransaction>? transactions,
    bool? isLoading,
    String? error,
    bool? hasMore,
    int? currentOffset,
  }) {
    return PhotonTransactionsState(
      transactions: transactions ?? this.transactions,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      hasMore: hasMore ?? this.hasMore,
      currentOffset: currentOffset ?? this.currentOffset,
    );
  }
}

// ========== Transactions Provider ==========

class PhotonTransactionsNotifier
    extends StateNotifier<PhotonTransactionsState> {
  PhotonTransactionsNotifier(this._repository)
      : super(PhotonTransactionsState()) {
    loadTransactions();
  }

  final PhotonRepository _repository;
  static const int _limit = 20;

  Future<void> loadTransactions({bool refresh = false}) async {
    if (refresh) {
      state = state.copyWith(
        transactions: [],
        currentOffset: 0,
        hasMore: true,
      );
    }

    if (state.isLoading || !state.hasMore) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final transactions = await _repository.getTransactionHistory(
        limit: _limit,
        offset: state.currentOffset,
      );

      final newTransactions = [
        ...state.transactions,
        ...transactions,
      ];

      state = state.copyWith(
        transactions: newTransactions,
        isLoading: false,
        hasMore: transactions.length >= _limit,
        currentOffset: state.currentOffset + transactions.length,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  void refresh() {
    loadTransactions(refresh: true);
  }
}

final photonTransactionsProvider =
    StateNotifierProvider<PhotonTransactionsNotifier, PhotonTransactionsState>(
        (ref) {
  final repository = ref.watch(photonRepositoryProvider);
  return PhotonTransactionsNotifier(repository);
});

// ========== Summary Provider ==========

final transactionSummaryProvider =
    FutureProvider.autoDispose<TransactionSummary>((ref) async {
  final repository = ref.watch(photonRepositoryProvider);
  return repository.getTransactionSummary(days: 30);
});
