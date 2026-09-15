import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

/// Dio Provider
///
/// 提供配置好的 Dio 实例（带拦截器）
/// 从现有的 ApiClient 中提取
final dioProvider = Provider<Dio>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return apiClient.dio;
});
