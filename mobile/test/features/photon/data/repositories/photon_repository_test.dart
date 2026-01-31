import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/photon/data/repositories/photon_repository.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

class TestApiClient implements ApiClient {
  Future<Response<dynamic>> Function(
    String path,
    Map<String, dynamic>? queryParameters,
  )? getHandler;
  Future<Response<dynamic>> Function(
    String path,
    Object? data,
    Map<String, dynamic>? queryParameters,
  )? postHandler;

  @override
  Dio get dio => throw UnimplementedError();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final handler = getHandler;
    if (handler == null) {
      throw UnimplementedError('No get handler configured');
    }
    final response = await handler(path, queryParameters);
    return Response<T>(
      data: response.data as T,
      requestOptions: response.requestOptions,
      statusCode: response.statusCode,
      statusMessage: response.statusMessage,
      isRedirect: response.isRedirect,
      redirects: response.redirects,
      extra: response.extra,
      headers: response.headers,
    );
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final handler = postHandler;
    if (handler == null) {
      throw UnimplementedError('No post handler configured');
    }
    final response = await handler(path, data, queryParameters);
    return Response<T>(
      data: response.data as T,
      requestOptions: response.requestOptions,
      statusCode: response.statusCode,
      statusMessage: response.statusMessage,
      isRedirect: response.isRedirect,
      redirects: response.redirects,
      extra: response.extra,
      headers: response.headers,
    );
  }

  @override
  Future<Response<T>> put<T>(String path, {Object? data}) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> patch<T>(String path, {Object? data}) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> delete<T>(String path) {
    throw UnimplementedError();
  }

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) {
    throw UnimplementedError();
  }

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) {
    throw UnimplementedError();
  }
}

void main() {
  late TestApiClient mockApiClient;
  late PhotonRepository repository;

  setUp(() {
    mockApiClient = TestApiClient();
    repository = PhotonRepository(mockApiClient);
  });

  group('PhotonRepository - getBalance', () {
    test('returns photon balance from API', () async {
      final responseData = {
        'success': true,
        'data': {
          'user_id': 'user-123',
          'balance': 500,
          'updated_at': '2024-01-28T10:00:00.000Z',
        },
      };

      mockApiClient.getHandler = (path, queryParameters) async {
        expect(path, '/photons/balance');
        return Response(
          requestOptions: RequestOptions(path: '/photons/balance'),
          data: responseData,
        );
      };

      final result = await repository.getBalance();

      expect(result.userId, 'user-123');
      expect(result.balance, 500);
      expect(result.updatedAt, isNotNull);
    });

    test('throws exception on API error', () async {
      mockApiClient.getHandler = (path, queryParameters) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/photons/balance'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/photons/balance'),
            data: {'detail': 'Unauthorized'},
            statusCode: 401,
          ),
        );
      };

      expect(
        () => repository.getBalance(),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Unauthorized'),
        ),),
      );
    });
  });

  group('PhotonRepository - getTransactionHistory', () {
    test('returns transaction list from API', () async {
      final responseData = {
        'success': true,
        'data': [
          {
            'id': 'tx-1',
            'transaction_type': 'grant_achievement',
            'amount': 100,
            'balance_before': 0,
            'balance_after': 100,
            'source': 'achievement:test_achievement',
            'related_item_id': 'test_achievement',
            'extra_data': {'achievement_name': 'Test Achievement'},
            'created_at': '2024-01-28T10:00:00.000Z',
          },
          {
            'id': 'tx-2',
            'transaction_type': 'purchase',
            'amount': -50,
            'balance_before': 100,
            'balance_after': 50,
            'source': 'shop:purchase',
            'related_item_id': 'item_123',
            'extra_data': null,
            'created_at': '2024-01-28T11:00:00.000Z',
          },
        ],
        'meta': {
          'total_count': 2,
          'limit': 50,
          'offset': 0,
        },
      };

      mockApiClient.getHandler = (path, queryParameters) async {
        expect(path, '/photons/transactions');
        expect(queryParameters, {
          'limit': 50,
          'offset': 0,
        });
        return Response(
          requestOptions: RequestOptions(path: '/photons/transactions'),
          data: responseData,
        );
      };

      final result = await repository.getTransactionHistory();

      expect(result.length, 2);
      expect(result[0].transactionType, PhotonTransactionType.grantAchievement);
      expect(result[0].amount, 100);
      expect(result[0].isIncome, isTrue);
      expect(result[0].metadata, {'achievement_name': 'Test Achievement'});  // Verify extra_data → metadata mapping
      expect(result[1].transactionType, PhotonTransactionType.purchase);
      expect(result[1].amount, -50);
      expect(result[1].isExpense, isTrue);
      expect(result[1].metadata, null);  // Verify null handling
    });

    test('filters by transaction type', () async {
      mockApiClient.getHandler = (path, queryParameters) async {
        expect(path, '/photons/transactions');
        expect(queryParameters?['transaction_type'], 'grant_achievement');
        return Response(
          requestOptions: RequestOptions(path: '/photons/transactions'),
          data: {
            'success': true,
            'data': [
              {
                'id': 'tx-1',
                'transaction_type': 'grant_achievement',
                'amount': 100,
                'balance_before': 0,
                'balance_after': 100,
                'source': 'test',
                'created_at': '2024-01-28T10:00:00.000Z',
              },
            ],
          },
        );
      };

      final result = await repository.getTransactionHistory(
        transactionType: 'grant_achievement',
      );

      expect(result.length, 1);
      expect(result[0].transactionType, PhotonTransactionType.grantAchievement);
    });

    test('returns empty list when no transactions', () async {
      mockApiClient.getHandler = (path, queryParameters) async {
        expect(path, '/photons/transactions');
        return Response(
          requestOptions: RequestOptions(path: '/photons/transactions'),
          data: {
            'success': true,
            'data': [],
          },
        );
      };

      final result = await repository.getTransactionHistory();

      expect(result, isEmpty);
    });
  });

  group('PhotonRepository - getTransactionSummary', () {
    test('returns transaction summary', () async {
      final responseData = {
        'success': true,
        'data': {
          'total_income': 500,
          'total_expense': 150,
          'net_change': 350,
          'transaction_count': 5,
          'by_type': {
            'grant_achievement': 300,
            'purchase': -150,
          },
        },
        'meta': {
          'period_days': 30,
        },
      };

      mockApiClient.getHandler = (path, queryParameters) async {
        expect(path, '/photons/transactions/summary');
        expect(queryParameters, {'days': 30});
        return Response(
          requestOptions: RequestOptions(path: '/photons/transactions/summary'),
          data: responseData,
        );
      };

      final result = await repository.getTransactionSummary();

      expect(result.totalIncome, 500);
      expect(result.totalExpense, 150);
      expect(result.netChange, 350);
      expect(result.transactionCount, 5);
      expect(result.byType['grant_achievement'], 300);
    });
  });

  group('PhotonRepository - transferPhotons', () {
    test('successfully transfers photons', () async {
      const recipientId = 'user-456';
      const amount = 100;
      const message = 'Good luck!';

      final responseData = {
        'success': true,
        'message': 'Transfer successful',
        'data': {
          'from_user_id': 'user-123',
          'to_user_id': recipientId,
          'amount': amount,
          'from_balance': 400,
          'to_balance': 100,
        },
        'amount_transferred': amount,
        'recipient_username': 'test_user',
      };

      mockApiClient.postHandler = (path, data, queryParameters) async {
        expect(path, '/photons/transfer');
        final payload = data as Map<String, dynamic>;
        expect(payload['recipient_id'], recipientId);
        expect(payload['amount'], amount);
        expect(payload['message'], message);
        return Response(
          requestOptions: RequestOptions(path: '/photons/transfer'),
          data: responseData,
        );
      };

      final result = await repository.transferPhotons(
        recipientId: recipientId,
        amount: amount,
        message: message,
      );

      expect(result['amount'], amount);
      expect(result['from_balance'], 400);
      expect(result['to_balance'], 100);
    });

    test('throws exception on insufficient balance', () async {
      mockApiClient.postHandler = (path, data, queryParameters) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/photons/transfer'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/photons/transfer'),
            data: {'detail': 'Insufficient photon balance'},
            statusCode: 400,
          ),
        );
      };

      expect(
        () => repository.transferPhotons(
          recipientId: 'user-456',
          amount: 1000,
        ),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Insufficient photon balance'),
        ),),
      );
    });
  });

  group('PhotonTransactionModel', () {
    test('correctly identifies income transactions', () {
      final transaction = PhotonTransaction(
        id: 'tx-1',
        transactionType: PhotonTransactionType.grantAchievement,
        amount: 100,
        balanceBefore: 0,
        balanceAfter: 100,
        createdAt: DateTime(2024, 1, 28),
      );

      expect(transaction.isIncome, isTrue);
      expect(transaction.isExpense, isFalse);
      expect(transaction.transactionTypeName, '成就奖励');
    });

    test('correctly identifies expense transactions', () {
      final transaction = PhotonTransaction(
        id: 'tx-2',
        transactionType: PhotonTransactionType.purchase,
        amount: -50,
        balanceBefore: 100,
        balanceAfter: 50,
        createdAt: DateTime(2024, 1, 28),
      );

      expect(transaction.isIncome, isFalse);
      expect(transaction.isExpense, isTrue);
      expect(transaction.transactionTypeName, '商城购买');
    });

    test('returns correct display name for all transaction types', () {
      expect(
        PhotonTransaction(
          id: '1',
          transactionType: PhotonTransactionType.grantDailyFirst,
          amount: 30,
          balanceBefore: 0,
          balanceAfter: 30,
          createdAt: DateTime(2024, 1, 28),
        ).transactionTypeName,
        '每日首胜',
      );

      expect(
        PhotonTransaction(
          id: '2',
          transactionType: PhotonTransactionType.transferOut,
          amount: -100,
          balanceBefore: 500,
          balanceAfter: 400,
          createdAt: DateTime(2024, 1, 28),
        ).transactionTypeName,
        '转账-转出',
      );

      expect(
        PhotonTransaction(
          id: '3',
          transactionType: PhotonTransactionType.transferIn,
          amount: 100,
          balanceBefore: 0,
          balanceAfter: 100,
          createdAt: DateTime(2024, 1, 28),
        ).transactionTypeName,
        '转账-转入',
      );
    });
  });

  group('TransactionSummaryModel', () {
    test('correctly calculates net change', () {
      final summary = TransactionSummary(
        totalIncome: 500,
        totalExpense: 200,
        netChange: 300,
        transactionCount: 10,
        byType: {},
      );

      expect(summary.netChange, 300);
      expect(summary.toString(), contains('income: 500'));
      expect(summary.toString(), contains('expense: 200'));
      expect(summary.toString(), contains('net: 300'));
    });

    test('copyWith creates new instance with updated values', () {
      final original = TransactionSummary(
        totalIncome: 500,
        totalExpense: 200,
        netChange: 300,
        transactionCount: 10,
        byType: {},
      );

      final copy = original.copyWith(
        totalIncome: 600,
        transactionCount: 11,
      );

      expect(copy.totalIncome, 600);
      expect(copy.totalExpense, 200); // Unchanged
      expect(copy.transactionCount, 11);
    });
  });

  group('PhotonBalanceModel', () {
    test('correctly serializes to/from JSON', () {
      final balance = PhotonBalance(
        userId: 'user-123',
        balance: 500,
        updatedAt: DateTime(2024, 1, 28, 10),
      );

      final json = balance.toJson();
      final deserialized = PhotonBalance.fromJson(json);

      expect(deserialized.userId, balance.userId);
      expect(deserialized.balance, balance.balance);
      expect(deserialized.updatedAt, balance.updatedAt);
    });

    test('copyWith creates new instance with updated balance', () {
      final original = PhotonBalance(
        userId: 'user-123',
        balance: 500,
        updatedAt: DateTime(2024, 1, 28),
      );

      final updated = original.copyWith(balance: 600);

      expect(updated.userId, original.userId);
      expect(updated.balance, 600);
      expect(updated.updatedAt, original.updatedAt);
    });
  });
}
