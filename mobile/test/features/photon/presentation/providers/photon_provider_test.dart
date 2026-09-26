import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/photon/data/repositories/photon_repository.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

class TestPhotonRepository implements PhotonRepository {
  int getBalanceCalls = 0;
  int getTransactionHistoryCalls = 0;
  int getTransactionSummaryCalls = 0;

  Future<PhotonBalance> Function()? getBalanceHandler;
  Future<List<PhotonTransaction>> Function({
    String? transactionType,
    int limit,
    int offset,
  })? getTransactionHistoryHandler;
  Future<TransactionSummary> Function({int days})? getTransactionSummaryHandler;

  @override
  Future<PhotonBalance> getBalance() async {
    getBalanceCalls += 1;
    final handler = getBalanceHandler;
    if (handler != null) {
      return handler();
    }
    throw Exception('No balance handler');
  }

  @override
  Future<List<PhotonTransaction>> getTransactionHistory({
    String? transactionType,
    int limit = 50,
    int offset = 0,
  }) async {
    getTransactionHistoryCalls += 1;
    final handler = getTransactionHistoryHandler;
    if (handler != null) {
      return handler(
        transactionType: transactionType,
        limit: limit,
        offset: offset,
      );
    }
    return [];
  }

  @override
  Future<TransactionSummary> getTransactionSummary({int days = 30}) async {
    getTransactionSummaryCalls += 1;
    final handler = getTransactionSummaryHandler;
    if (handler != null) {
      return handler(days: days);
    }
    return TransactionSummary(
      totalIncome: 0,
      totalExpense: 0,
      netChange: 0,
      transactionCount: 0,
      byType: const {},
    );
  }

  @override
  Future<Map<String, dynamic>> transferPhotons({
    required String recipientId,
    required int amount,
    String? message,
  }) {
    throw UnimplementedError();
  }
}

void main() {
  late TestPhotonRepository mockRepository;
  late ProviderContainer container;

  setUp(() {
    mockRepository = TestPhotonRepository();
    container = ProviderContainer(
      overrides: [
        photonRepositoryProvider.overrideWithValue(mockRepository),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('PhotonBalanceProvider', () {
    test('loads balance on initialization', () async {
      final balance = PhotonBalance(
        userId: 'user-123',
        balance: 500,
        updatedAt: DateTime(2024, 1, 28),
      );

      mockRepository.getBalanceHandler = () async => balance;

      // Read provider to trigger initialization
      container.read(photonBalanceProvider);
      await container.read(photonBalanceProvider.notifier).loadBalance();

      final state = container.read(photonBalanceProvider);

      expect(state.isLoading, isFalse);
      expect(state.balance, balance);

      expect(mockRepository.getBalanceCalls, 2);
    });

    test('handles load errors gracefully (N9: 诚实地「暂不可见」，异常不进状态)',
        () async {
      mockRepository.getBalanceHandler = () async {
        throw Exception('Network error');
      };

      container.read(photonBalanceProvider);
      await container.read(photonBalanceProvider.notifier).loadBalance();

      final state = container.read(photonBalanceProvider);

      expect(state.isLoading, isFalse);
      expect(state.balance, isNull);
    });

    test('refreshBalance updates balance', () async {
      final initialBalance = PhotonBalance(
        userId: 'user-123',
        balance: 500,
        updatedAt: DateTime(2024, 1, 28),
      );

      final updatedBalance = PhotonBalance(
        userId: 'user-123',
        balance: 700,
        updatedAt: DateTime(2024, 1, 28, 11),
      );

      mockRepository.getBalanceHandler = () async => initialBalance;

      container.read(photonBalanceProvider);
      await container.read(photonBalanceProvider.notifier).loadBalance();

      mockRepository.getBalanceHandler = () async => updatedBalance;

      await container.read(photonBalanceProvider.notifier).refreshBalance();

      final state = container.read(photonBalanceProvider);

      expect(state.balance?.balance, 700);
    });
  });

  group('PhotonTransactionsProvider', () {
    test('loads transactions on initialization', () async {
      final transactions = [
        PhotonTransaction(
          id: 'tx-1',
          transactionType: PhotonTransactionType.grantAchievement,
          amount: 100,
          balanceBefore: 0,
          balanceAfter: 100,
          source: 'achievement:test',
          createdAt: DateTime(2024, 1, 28),
        ),
        PhotonTransaction(
          id: 'tx-2',
          transactionType: PhotonTransactionType.purchase,
          amount: -50,
          balanceBefore: 100,
          balanceAfter: 50,
          source: 'shop:purchase',
          createdAt: DateTime(2024, 1, 28, 11),
        ),
      ];

      mockRepository.getTransactionHistoryHandler = ({
        String? transactionType,
        int limit = 20,
        int offset = 0,
      }) async => transactions;

      container.read(photonTransactionsProvider);
      await container.read(photonTransactionsProvider.notifier)
          .loadTransactions(refresh: true);

      final state = container.read(photonTransactionsProvider);

      expect(state.isLoading, isFalse);
      expect(state.transactions.length, 2);
      expect(state.transactions[0].amount, 100);
      expect(state.hasMore, isFalse);
    });

    test('loads more transactions when scrolling', () async {
      final firstPage = List.generate(
        20,
        (index) => PhotonTransaction(
          id: 'tx-${index + 1}',
          transactionType: PhotonTransactionType.grantAchievement,
          amount: 100,
          balanceBefore: 0,
          balanceAfter: 100,
          createdAt: DateTime(2024, 1, 28),
        ),
      );

      final secondPage = [
        PhotonTransaction(
          id: 'tx-2',
          transactionType: PhotonTransactionType.purchase,
          amount: -50,
          balanceBefore: 100,
          balanceAfter: 50,
          createdAt: DateTime(2024, 1, 28, 11),
        ),
      ];

      mockRepository.getTransactionHistoryHandler = ({
        String? transactionType,
        int limit = 20,
        int offset = 0,
      }) async {
        if (offset == 0) {
          return firstPage;
        }
        return secondPage;
      };

      container.read(photonTransactionsProvider);
      await container.read(photonTransactionsProvider.notifier)
          .loadTransactions(refresh: true);
      await container.read(photonTransactionsProvider.notifier).loadTransactions();

      await Future<void>.delayed(Duration.zero);

      final state = container.read(photonTransactionsProvider);

      expect(state.transactions.length, 21);
      expect(state.currentOffset, 21);
    });

    test('refresh clears and reloads transactions', () async {
      final transactions = [
        PhotonTransaction(
          id: 'tx-1',
          transactionType: PhotonTransactionType.grantAchievement,
          amount: 100,
          balanceBefore: 0,
          balanceAfter: 100,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      mockRepository.getTransactionHistoryHandler = ({
        String? transactionType,
        int limit = 20,
        int offset = 0,
      }) async => transactions;

      container.read(photonTransactionsProvider);
      await container.read(photonTransactionsProvider.notifier)
          .loadTransactions(refresh: true);

      final stateBeforeRefresh = container.read(photonTransactionsProvider);
      final txCountBeforeRefresh = stateBeforeRefresh.transactions.length;

      await container.read(photonTransactionsProvider.notifier).refresh();

      await Future<void>.delayed(Duration.zero);

      final stateAfterRefresh = container.read(photonTransactionsProvider);

      expect(stateAfterRefresh.transactions.length, txCountBeforeRefresh);
      expect(stateAfterRefresh.currentOffset, 1);
    });

    test('handles empty transaction list', () async {
      mockRepository.getTransactionHistoryHandler = ({
        String? transactionType,
        int limit = 20,
        int offset = 0,
      }) async => [];

      container.read(photonTransactionsProvider);
      await container.read(photonTransactionsProvider.notifier)
          .loadTransactions(refresh: true);

      final state = container.read(photonTransactionsProvider);

      expect(state.isLoading, isFalse);
      expect(state.transactions, isEmpty);
      expect(state.loadFailed, isFalse); // 空列表 ≠ 失败，两态互斥
      expect(state.hasMore, isFalse); // No items means no more to load
    });

    test('load failure is a bounded flag, exception text never enters state '
        '(N9)', () async {
      mockRepository.getTransactionHistoryHandler = ({
        String? transactionType,
        int limit = 20,
        int offset = 0,
      }) async =>
          throw Exception('boom-secret-detail');

      container.read(photonTransactionsProvider);
      await container.read(photonTransactionsProvider.notifier)
          .loadTransactions(refresh: true);

      final state = container.read(photonTransactionsProvider);

      expect(state.isLoading, isFalse);
      expect(state.loadFailed, isTrue);
      expect(state.transactions, isEmpty);
    });

    test('loadFailed resets when a new load starts (旧 error 粘滞边角修复)',
        () async {
      var shouldFail = true;
      mockRepository.getTransactionHistoryHandler = ({
        String? transactionType,
        int limit = 20,
        int offset = 0,
      }) async {
        if (shouldFail) {
          throw Exception('boom');
        }
        return [
          PhotonTransaction(
            id: 'tx-1',
            transactionType: PhotonTransactionType.grantAchievement,
            amount: 100,
            balanceBefore: 0,
            balanceAfter: 100,
            createdAt: DateTime(2024, 1, 28),
          ),
        ];
      };

      container.read(photonTransactionsProvider);
      await container.read(photonTransactionsProvider.notifier)
          .loadTransactions(refresh: true);
      expect(container.read(photonTransactionsProvider).loadFailed, isTrue);

      shouldFail = false;
      await container.read(photonTransactionsProvider.notifier).refresh();
      await Future<void>.delayed(Duration.zero);

      final recovered = container.read(photonTransactionsProvider);
      expect(recovered.loadFailed, isFalse);
      expect(recovered.transactions.length, 1);
    });
  });

  group('TransactionSummaryProvider', () {
    test('loads transaction summary', () async {
      final summary = TransactionSummary(
        totalIncome: 500,
        totalExpense: 150,
        netChange: 350,
        transactionCount: 10,
        byType: {
          'grant_achievement': 300,
          'purchase': -150,
        },
      );

      mockRepository.getTransactionSummaryHandler = ({int days = 30}) async => summary;

      final result = await container.read(transactionSummaryProvider.future);

      expect(result.totalIncome, 500);
      expect(result.totalExpense, 150);
      expect(result.netChange, 350);
      expect(result.transactionCount, 10);

      expect(mockRepository.getTransactionSummaryCalls, 1);
    });

    test('caches summary result', () async {
      final summary = TransactionSummary(
        totalIncome: 500,
        totalExpense: 150,
        netChange: 350,
        transactionCount: 10,
        byType: {},
      );

      mockRepository.getTransactionSummaryHandler = ({int days = 30}) async => summary;

      final sub = container.listen(transactionSummaryProvider, (_, __) {});

      // First read
      await container.read(transactionSummaryProvider.future);
      // Second read should use cache
      await container.read(transactionSummaryProvider.future);

      expect(mockRepository.getTransactionSummaryCalls, 1);
      sub.close();
    });
  });

  group('PhotonBalanceState', () {
    test('copyWith creates new state with updated values', () {
      final state = PhotonBalanceState(
        balance: PhotonBalance(
          userId: 'user-123',
          balance: 500,
          updatedAt: DateTime(2024, 1, 28),
        ),
      );

      final updated = state.copyWith(
        balance: state.balance?.copyWith(balance: 700),
      );

      expect(updated.balance?.balance, 700);
      expect(updated.isLoading, isFalse);
    });

    test('copyWith clears loading only (N9: error 字段已退役，状态无异常载体)',
        () {
      final state = PhotonBalanceState(
        isLoading: true,
      );

      final updated = state.copyWith(isLoading: false);

      expect(updated.isLoading, isFalse);
      expect(updated.balance, isNull); // 失败即「暂不可见」，不造默认值
    });
  });

  group('PhotonTransactionsState', () {
    test('copyWith updates all fields correctly', () {
      final transactions = [
        PhotonTransaction(
          id: 'tx-1',
          transactionType: PhotonTransactionType.grantAchievement,
          amount: 100,
          balanceBefore: 0,
          balanceAfter: 100,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      final state = PhotonTransactionsState(
        transactions: transactions,
        currentOffset: 1,
      );

      final updated = state.copyWith(
        isLoading: true,
        currentOffset: 2,
        loadFailed: true,
      );

      expect(updated.transactions, transactions);
      expect(updated.isLoading, isTrue);
      expect(updated.currentOffset, 2);
      expect(updated.hasMore, isTrue); // Unchanged
      expect(updated.loadFailed, isTrue);
    });

    test('correctly identifies when no more items to load', () {
      final state = PhotonTransactionsState(
        transactions: [],
        hasMore: false,
      );

      expect(state.hasMore, isFalse);
    });
  });

  group('Provider Container Lifecycle', () {
    test('disposes resources properly', () async {
      final container = ProviderContainer(
        overrides: [
          photonRepositoryProvider.overrideWithValue(mockRepository),
        ],
      )
        // Read providers to initialize them
        ..read(photonBalanceProvider)
        ..read(photonTransactionsProvider);

      await Future<void>.delayed(Duration.zero);

      // Should not throw
      expect(container.dispose, returnsNormally);
    });
  });
}
