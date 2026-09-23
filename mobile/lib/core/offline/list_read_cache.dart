import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/cached_list_snapshot.dart';

/// N34（A-SPEC6）：缓存感知的读结果。
///
/// [data] 为领域数据；[fromCache] 表示本次结果来自本地 warm 快照
/// （离线/网络失败回读，UI 侧据此挂「截至 X」stale 标记）；[asOf] 为
/// 数据时点戳（N36 口径的真源，仅缓存命中时有值）。
class CacheAwareResult<T> {
  const CacheAwareResult(this.data, {this.fromCache = false, this.asOf});

  final T data;
  final bool fromCache;
  final DateTime? asOf;
}

/// 一次快照回读的原始载荷与数据时点。
class SnapshotData {
  const SnapshotData({required this.payload, required this.fetchedAt});

  /// 原始响应 JSON（put 时未经改动的形状，由响应域自行解析）。
  final Object? payload;
  final DateTime fetchedAt;
}

/// N34（A-SPEC6）：备考资产「列表型响应」的本地读缓存服务。
///
/// 机制照统计域 HybridStatisticsRepository warm 层先例（Isar + 时点戳 +
/// 版本化溯源），通用化为三读域（task / error_book / community）共用：
/// - **只缓存真实 API 响应**：调用方仅在请求成功后调用 [put]——demo/mock
///   数据与本地乐观态永不入库（B-02 口径：不造第二事实源）；
/// - **只读不写**：快照回读只服务「网络不可达时的兜底」，写路径仍走唯一
///   后端口径；
/// - **失败不伤害主链路**：缓存读写在 Isar 不可用（未初始化/web 桩）时
///   静默降级，绝不抛出掩盖原始错误。
class ListReadCache {
  ListReadCache(this._db);

  final LocalDatabase _db;

  /// 判定一次失败是否属于「网络不可达」类（可安全回退本地快照）。
  ///
  /// 口径与 task_repository 的 `_isOfflineError`（TASK-013）一致：
  /// 连接类错误才回退；4xx/5xx 等服务端语义错误照常上抛，绝不用旧快照
  /// 掩盖服务端真实响应。
  static bool isNetworkFailure(Object error) {
    if (error is DioException) {
      return error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.sendTimeout ||
          error.type == DioExceptionType.receiveTimeout;
    }
    return false;
  }

  /// 落一条快照。[payload] 必须是 JSON 可编码的原始响应体。
  /// cacheKey 有唯一索引：同键重写必须复用旧 id（否则触发唯一冲突）。
  Future<void> put(String cacheKey, Object? payload) async {
    final isar = _db.isarOrNull;
    if (isar == null || !isar.isOpen) return;
    try {
      final bytes = utf8.encode(jsonEncode(payload));
      final existing = await _db.cachedListSnapshots
          .filter()
          .cacheKeyEqualTo(cacheKey)
          .findFirst();
      await isar.writeTxn(() async {
        await _db.cachedListSnapshots.put(
          CachedListSnapshot()
            ..id = existing?.id ?? Isar.autoIncrement
            ..cacheKey = cacheKey
            ..jsonData = bytes
            ..fetchedAt = DateTime.now()
            ..version = CachedListSnapshot.cacheVersion,
        );
      });
    } on Exception {
      // 缓存写入失败不影响本次成功响应的正常返回。
    }
  }

  /// 回读一条快照；无条目 / 版本不符 / 存储不可用时返回 null。
  Future<SnapshotData?> get(String cacheKey) async {
    final isar = _db.isarOrNull;
    if (isar == null || !isar.isOpen) return null;
    try {
      final entry = await _db.cachedListSnapshots
          .filter()
          .cacheKeyEqualTo(cacheKey)
          .findFirst();
      if (entry == null) return null;
      if (entry.version != CachedListSnapshot.cacheVersion) {
        // 旧版本条目永不服务（照统计域 legacy purge 先例）。
        await isar.writeTxn(() async {
          await _db.cachedListSnapshots.delete(entry.id);
        });
        return null;
      }
      return SnapshotData(
        payload: jsonDecode(utf8.decode(entry.jsonData)),
        fetchedAt: entry.fetchedAt,
      );
    } on Exception {
      return null;
    }
  }

  /// 按前缀失效（写操作后由调用方按需清理同域快照，可选）。
  Future<void> invalidatePrefix(String prefix) async {
    final isar = _db.isarOrNull;
    if (isar == null || !isar.isOpen) return;
    try {
      final entries = await _db.cachedListSnapshots
          .filter()
          .cacheKeyStartsWith(prefix)
          .findAll();
      if (entries.isEmpty) return;
      await isar.writeTxn(() async {
        for (final entry in entries) {
          await _db.cachedListSnapshots.delete(entry.id);
        }
      });
    } on Exception {
      // 失效失败只影响下次回读新鲜度，不上抛。
    }
  }
}

/// N34：全局读缓存服务提供者。
final listReadCacheProvider =
    Provider<ListReadCache>((ref) => ListReadCache(ref.watch(localDatabaseProvider)));
