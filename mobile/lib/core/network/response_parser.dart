import 'package:sparkle/shared/models/api_response_model.dart';

/// 统一的API响应解析工具
/// 支持后端的所有响应格式，向后兼容
class ApiResponseParser {
  /// 解析可能被包裹的对象响应
  ///
  /// 支持格式：
  /// 1. 直接对象: {...}
  /// 2. 包裹对象: {data: {...}}
  static Map<String, dynamic> unwrapMap(
    dynamic response, {
    String? action,
  }) {
    if (response == null) {
      throw Exception('${action ?? "Operation"} response is empty');
    }

    if (response is Map<String, dynamic>) {
      // 检查 {data: {...}} 包裹
      if (response.containsKey('data')) {
        final data = response['data'];
        if (data is Map<String, dynamic>) {
          return data;
        }
      }
      // 直接格式
      if (!response.containsKey('success')) {
        return response;
      }
    }

    throw Exception(
      'Unexpected response format for ${action ?? "operation"}: '
      'expected Map, got ${response.runtimeType}'
    );
  }

  /// 解析可能被包裹的列表响应
  ///
  /// 支持格式：
  /// 1. 直接列表: [...]
  /// 2. 包裹列表: {data: [...]}
  static List<dynamic> unwrapList(
    dynamic response, {
    String? action,
  }) {
    if (response == null) {
      return [];
    }

    if (response is List) {
      return response;
    }

    if (response is Map<String, dynamic>) {
      if (response.containsKey('data')) {
        final data = response['data'];
        if (data is List) {
          return data;
        }
        return [];
      }
    }

    if (action != null) {
      throw Exception('Unexpected response format for $action');
    }
    return [];
  }

  /// 解析分页响应（灵活格式支持）
  ///
  /// 支持格式：
  /// 1. {data: [...], meta: {total, page, page_size}}
  /// 2. {data: [...], total: 50, page: 1}
  /// 3. {items: [...], total: 50, page: 1} (PaginatedResponse标准格式)
  static PaginatedResponse<T> parsePaginated<T>(
    dynamic response,
    T Function(Object?) fromJson, {
    String? action,
  }) {
    if (response == null) {
      throw Exception('${action ?? "Operation"} response is empty');
    }

    if (response is! Map<String, dynamic>) {
      throw Exception('Expected Map for paginated response');
    }

    final json = response;

    // 已经是PaginatedResponse格式
    if (json.containsKey('items')) {
      return PaginatedResponse.fromJson(json, fromJson);
    }

    // 提取data字段
    final dataList = json['data'] as List<dynamic>?;
    if (dataList == null) {
      throw Exception('Paginated response missing "data" or "items"');
    }

    // 提取元数据 - 优先meta，其次扁平格式
    final meta = json['meta'] as Map<String, dynamic>?;
    final total = (meta?['total'] as num?) ??
                 (json['total'] as num?) ??
                 dataList.length;
    final page = (meta?['page'] as num?) ??
                (json['page'] as num?) ??
                1;
    final pageSize = (meta?['page_size'] as num?) ??
                    (json['page_size'] as num?) ??
                    (json['pageSize'] as num?) ??
                    dataList.length;

    final items = dataList
        .map((item) => fromJson(item))
        .toList();

    return PaginatedResponse<T>(
      items: items,
      total: total.toInt(),
      page: page.toInt(),
      pageSize: pageSize.toInt(),
    );
  }
}
