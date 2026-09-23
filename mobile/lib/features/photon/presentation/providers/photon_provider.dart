import 'package:flutter/foundation.dart';
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

/// 余额状态（N9/N4：异常对象不进 UI 状态——失败只是 isLoading=false +
/// balance 保持 null 的诚实「暂不可见」，细节只进日志）。
class PhotonBalanceState {

  PhotonBalanceState({
    this.balance,
    this.isLoading = false,
  });
  final PhotonBalance? balance;
  final bool isLoading;

  PhotonBalanceState copyWith({
    PhotonBalance? balance,
    bool? isLoading,
  }) => PhotonBalanceState(
      balance: balance ?? this.balance,
      isLoading: isLoading ?? this.isLoading,
    );
}

// ========== Balance Provider ==========

class PhotonBalanceNotifier extends StateNotifier<PhotonBalanceState> {
  PhotonBalanceNotifier(this._repository) : super(PhotonBalanceState()) {
    loadBalance();
  }

  final PhotonRepository _repository;

  Future<void> loadBalance() async {
    state = state.copyWith(isLoading: true);

    try {
      final balance = await _repository.getBalance();
      state = state.copyWith(balance: balance, isLoading: false);
    } catch (e) {
      // 异常细节只进日志，不进 UI 状态（N9）。
      debugPrint('[PhotonBalance] load failed: $e');
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> refreshBalance() async {
    await loadBalance();
  }
}

final photonBalanceProvider =
    StateNotifierProvider<PhotonBalanceNotifier, PhotonBalanceState>((ref) {
  final repository = ref.watch(photonRepositoryProvider);
  return PhotonBalanceNotifier(repository);
});

// ========== Transactions State ==========

/// 流水状态。失败是「有界的布尔终态」（N9：原 `String? error` 携带异常
/// 文案直出 UI，已退役）；人话模板由展示层按 loadFailed 渲染，异常细节
/// 只进日志。每次发起新加载即复位。
class PhotonTransactionsState {

  PhotonTransactionsState({
    this.transactions = const [],
    this.isLoading = false,
    this.loadFailed = false,
    this.hasMore = true,
    this.currentOffset = 0,
  });
  final List<PhotonTransaction> transactions;
  final bool isLoading;
  final bool loadFailed;
  final bool hasMore;
  final int currentOffset;

  PhotonTransactionsState copyWith({
    List<PhotonTransaction>? transactions,
    bool? isLoading,
    bool? loadFailed,
    bool? hasMore,
    int? currentOffset,
  }) => PhotonTransactionsState(
      transactions: transactions ?? this.transactions,
      isLoading: isLoading ?? this.isLoading,
      loadFailed: loadFailed ?? this.loadFailed,
      hasMore: hasMore ?? this.hasMore,
      currentOffset: currentOffset ?? this.currentOffset,
    );
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

    // 新加载即复位失败终态（顺带修掉旧实现 error 粘滞：刷新成功后
    // 空列表仍误显错误的边角）。
    state = state.copyWith(isLoading: true, loadFailed: false);

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
      // 异常细节只进日志，UI 渲染人话模板（N9）。
      debugPrint('[PhotonTransactions] load failed: $e');
      state = state.copyWith(
        isLoading: false,
        loadFailed: true,
      );
    }
  }

  Future<void> refresh() async {
    await loadTransactions(refresh: true);
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
  return repository.getTransactionSummary();
});
