import 'package:flutter/foundation.dart';
import 'package:isar/isar.dart';

import 'local_database_store.dart';

/// Web 端 no-op 桩（web-unblock 波次）。
///
/// 为什么必须是桩而不是真库：
/// 1. vendored `isar_flutter_libs` 只有 android/ios/linux/macos/windows 原生库，
///    无 web 资产；
/// 2. package:isar 3.1.0+1 自身的 web 分支在 `Isar.open` 时直接
///    `throw IsarError('Please use Isar 2.5.0 ...')`（src/web/open.dart）。
///
/// 语义：init() 为 no-op；`isarOrNull` 恒为 null；门面所有集合访问器在
/// Web 上抛 [UnsupportedError]（带诊断信息）。离线队列 / 翻译历史 /
/// 统计缓存 / galaxy CRDT 快照等依赖 Isar 的能力在 Web 上降级不可用。
///
/// TODO(multi-platform): 后续波次在此接入等价持久层（IndexedDB 或 Hive），
/// 并让跨门面只传 DTO，保持 LocalDatabase 消费方 API 不变。
class LocalDatabaseStoreWeb implements LocalDatabaseStore {
  @override
  Future<void> init(List<CollectionSchema<dynamic>> schemas) async {
    debugPrint(
      'LocalDatabase[web-stub]: Isar unavailable on Web; '
      'offline persistence disabled (TODO: IndexedDB backend).',
    );
  }

  @override
  bool get isReady => false;

  @override
  Isar? get isarOrNull => null;

  @override
  String get kind => 'web-stub';
}

LocalDatabaseStore createLocalDatabaseStoreImpl() => LocalDatabaseStoreWeb();
