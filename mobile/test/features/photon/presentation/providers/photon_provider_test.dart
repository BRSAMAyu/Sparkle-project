import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/photon/data/repositories/photon_repository.dart';
import 'package:sparkle/features/photon/presentation/providers/photon_provider.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

class MockPhotonRepository extends Mock implements PhotonRepository {}

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockPhotonRepository mockRepository;
  late ProviderContainer container;

  setUp(() {
    mockRepository = MockPhotonRepository();
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

      when(mockRepository.getBalance())
          .thenAnswer((_) async => balance);

      // Read provider to trigger initialization
      final state = container.read(photonBalanceProvider);

      // Wait for async operation
      await Future.delayed(Duration.zero);

      expect(state.isLoading, isFalse);
      expect(state.balance, balance);
      expect(state.error, isNull);

      verify(mockRepository.getBalance()).called(1);
    });

    test('handles load errors gracefully', () async {
      when(mockRepository.getBalance())
          .thenThrow(Exception('Network error'));

      container.read(photonBalanceProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(photonBalanceProvider);

      expect(state.isLoading, isFalse);
      expect(state.balance, isNull);
      expect(state.error, contains('Network error'));
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
        updatedAt: DateTime(2024, 1, 28, 11, 0),
      );

      when(mockRepository.getBalance())
          .thenAnswer((_) async => initialBalance);

      container.read(photonBalanceProvider);
      await Future.delayed(Duration.zero);

      when(mockRepository.getBalance())
          .thenAnswer((_) async => updatedBalance);

      await container.read(photonBalanceProvider.notifier).refreshBalance();

      await Future.delayed(Duration.zero);

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
          createdAt: DateTime(2024, 1, 28, 11, 0),
        ),
      ];

      when(mockRepository.getTransactionHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => transactions);

      container.read(photonTransactionsProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(photonTransactionsProvider);

      expect(state.isLoading, isFalse);
      expect(state.transactions.length, 2);
      expect(state.transactions[0].amount, 100);
      expect(state.hasMore, isTrue); // Default behavior
    });

    test('loads more transactions when scrolling', () async {
      final firstPage = [
        PhotonTransaction(
          id: 'tx-1',
          transactionType: PhotonTransactionType.grantAchievement,
          amount: 100,
          balanceBefore: 0,
          balanceAfter: 100,
          createdAt: DateTime(2024, 1, 28),
        ),
      ];

      final secondPage = [
        PhotonTransaction(
          id: 'tx-2',
          transactionType: PhotonTransactionType.purchase,
          amount: -50,
          balanceBefore: 100,
          balanceAfter: 50,
          createdAt: DateTime(2024, 1, 28, 11, 0),
        ),
      ];

      when(mockRepository.getTransactionHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => firstPage);

      container.read(photonTransactionsProvider);
      await Future.delayed(Duration.zero);

      when(mockRepository.getTransactionHistory(limit: 20, offset: 1))
          .thenAnswer((_) async => secondPage);

      await container.read(photonTransactionsProvider.notifier).loadTransactions();

      await Future.delayed(Duration.zero);

      final state = container.read(photonTransactionsProvider);

      expect(state.transactions.length, greaterThan(1));
      expect(state.currentOffset, greaterThan(0));
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

      when(mockRepository.getTransactionHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => transactions);

      container.read(photonTransactionsProvider);
      await Future.delayed(Duration.zero);

      final stateBeforeRefresh = container.read(photonTransactionsProvider);
      final txCountBeforeRefresh = stateBeforeRefresh.transactions.length;

      await container.read(photonTransactionsProvider.notifier).refresh();

      await Future.delayed(Duration.zero);

      final stateAfterRefresh = container.read(photonTransactionsProvider);

      expect(stateAfterRefresh.transactions.length, txCountBeforeRefresh);
      expect(stateAfterRefresh.currentOffset, 0);
    });

    test('handles empty transaction list', () async {
      when(mockRepository.getTransactionHistory(limit: 20, offset: 0))
          .thenAnswer((_) async => []);

      container.read(photonTransactionsProvider);

      await Future.delayed(Duration.zero);

      final state = container.read(photonTransactionsProvider);

      expect(state.isLoading, isFalse);
      expect(state.transactions, isEmpty);
      expect(state.hasMore, isFalse); // No items means no more to load
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

      when(mockRepository.getTransactionSummary(days: 30))
          .thenAnswer((_) async => summary);

      final summaryFuture = container.read(transactionSummaryProvider);

      final result = await summaryFuture;

      expect(result.totalIncome, 500);
      expect(result.totalExpense, 150);
      expect(result.netChange, 350);
      expect(result.transactionCount, 10);

      verify(mockRepository.getTransactionSummary(days: 30)).called(1);
    });

    test('caches summary result', () async {
      final summary = TransactionSummary(
        totalIncome: 500,
        totalExpense: 150,
        netChange: 350,
        transactionCount: 10,
        byType: {},
      );

      when(mockRepository.getTransactionSummary(days: 30))
          .thenAnswer((_) async => summary);

      // First read
      container.read(transactionSummaryProvider);
      await Future.delayed(Duration.zero);

      // Second read should use cache
      container.read(transactionSummaryProvider);
      await Future.delayed(Duration.zero);

      // Should only call repository once
      verify(mockRepository.getTransactionSummary(days: 30)).called(1);
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
        isLoading: false,
      );

      final updated = state.copyWith(
        balance: state.balance?.copyWith(balance: 700),
      );

      expect(updated.balance?.balance, 700);
      expect(updated.isLoading, isFalse);
      expect(updated.error, isNull);
    });

    test('copyWith with error sets error and clears loading', () {
      final state = PhotonBalanceState(
        balance: null,
        isLoading: true,
        error: null,
      );

      final updated = state.copyWith(
        error: 'Network error',
        isLoading: false,
      );

      expect(updated.error, 'Network error');
      expect(updated.isLoading, isFalse);
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
        isLoading: false,
        error: null,
        hasMore: true,
        currentOffset: 1,
      );

      final updated = state.copyWith(
        isLoading: true,
        currentOffset: 2,
      );

      expect(updated.transactions, transactions);
      expect(updated.isLoading, isTrue);
      expect(updated.currentOffset, 2);
      expect(updated.hasMore, isTrue); // Unchanged
    });

    test('correctly identifies when no more items to load', () {
      final state = PhotonTransactionsState(
        transactions: [],
        isLoading: false,
        hasMore: false,
        currentOffset: 0,
      );

      expect(state.hasMore, isFalse);
    });
  });

  group('Provider Container Lifecycle', () {
    test('disposes resources properly', () {
      final container = ProviderContainer(
        overrides: [
          photonRepositoryProvider.overrideWithValue(mockRepository),
        ],
      );

      // Read providers to initialize them
      container.read(photonBalanceProvider);
      container.read(photonTransactionsProvider);

      // Should not throw
      expect(() => container.dispose(), returnsNormally);
    });
  });
}
