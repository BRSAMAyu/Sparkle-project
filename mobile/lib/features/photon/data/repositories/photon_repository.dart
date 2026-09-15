import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

/// Photon Repository
/// 光子积分数据仓库
class PhotonRepository {
  PhotonRepository(this._apiClient);
  final ApiClient _apiClient;

  /// Handle Dio exceptions
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ??
        'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Map<String, dynamic> _unwrapResponseMap(dynamic data, {String? action}) {
    if (data is Map<String, dynamic>) {
      return data;
    }
    if (data == null) {
      throw Exception('${action ?? "Operation"} response is empty');
    }
    throw Exception('Unexpected response format');
  }

  /// Get photon balance
  /// 获取光子余额
  Future<PhotonBalance> getBalance() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.photonBalance,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getBalance');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        throw Exception('getBalance: data field is missing');
      }

      return PhotonBalance.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError<PhotonBalance>(e, 'getBalance');
    }
  }

  /// Get transaction history
  /// 获取交易历史
  Future<List<PhotonTransaction>> getTransactionHistory({
    String? transactionType,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
        if (transactionType != null) 'transaction_type': transactionType,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.photonTransactions,
        queryParameters: queryParams,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getTransactionHistory');
      final dataList = payload['data'] as List<dynamic>?;

      if (dataList == null) {
        return [];
      }

      return dataList
          .map((json) => PhotonTransaction.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      return _handleDioError<List<PhotonTransaction>>(e, 'getTransactionHistory');
    }
  }

  /// Get transaction summary
  /// 获取交易汇总统计
  Future<TransactionSummary> getTransactionSummary({
    int days = 30,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'days': days,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        '${ApiEndpoints.photonTransactions}/summary',
        queryParameters: queryParams,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getTransactionSummary');
      final data = payload['data'] as Map<String, dynamic>?;

      if (data == null) {
        throw Exception('getTransactionSummary: data field is missing');
      }

      return TransactionSummary.fromJson(data);
    } on DioException catch (e) {
      return _handleDioError<TransactionSummary>(e, 'getTransactionSummary');
    }
  }

  /// Transfer photons to another user
  /// 转账光子给其他用户
  Future<Map<String, dynamic>> transferPhotons({
    required String recipientId,
    required int amount,
    String? message,
  }) async {
    try {
      final requestData = <String, dynamic>{
        'recipient_id': recipientId,
        'amount': amount,
        if (message != null) 'message': message,
      };

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.photonTransfer,
        data: requestData,
      );

      final payload = _unwrapResponseMap(response.data, action: 'transferPhotons');

      return payload['data'] as Map<String, dynamic>? ?? payload;
    } on DioException catch (e) {
      return _handleDioError<Map<String, dynamic>>(e, 'transferPhotons');
    }
  }
}
