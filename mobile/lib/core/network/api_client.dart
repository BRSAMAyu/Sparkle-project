import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

import 'package:sparkle/core/network/api_interceptor.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref);
});

class ApiClient {
  final Ref _ref;
  late final Dio _dio;

  ApiClient(this._ref) {
    final options = BaseOptions(
      baseUrl: ApiEndpoints.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      contentType: 'application/json',
    );
    _dio = Dio(options);
    _dio.interceptors.add(_ref.read(authInterceptorProvider));
    _dio.interceptors.add(_ref.read(loggingInterceptorProvider));
  }

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters}) async {
    try {
      return await _dio.get(path, queryParameters: queryParameters);
    } on DioException {
      // Handle error
      rethrow;
    }
  }

  Future<Response<T>> post<T>(String path, {data}) async {
    try {
      return await _dio.post(path, data: data);
    } on DioException {
      // Handle error
      rethrow;
    }
  }

  Future<Response<T>> put<T>(String path, {data}) async {
    try {
      return await _dio.put(path, data: data);
    } on DioException {
      // Handle error
      rethrow;
    }
  }

  Future<Response<T>> delete<T>(String path) async {
    try {
      return await _dio.delete(path);
    } on DioException {
      // Handle error
      rethrow;
    }
  }
}
