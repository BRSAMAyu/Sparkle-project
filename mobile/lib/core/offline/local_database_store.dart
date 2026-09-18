import 'package:isar/isar.dart';

import 'local_database_store_io.dart'
    if (dart.library.html) 'local_database_store_web.dart';

/// LocalDatabase 门面背后的平台存储后端（multi-platform web-unblock 闸）。
///
/// - `io`（Android / iOS / 桌面）：真实 Isar（isar_flutter_libs）。
/// - `web`：no-op 桩。Isar 3.1.0+1 的 web 路径在 `Isar.open` 时会直接
///   throw（见 package:isar/src/web/open.dart 的 openIsar），因此 Web 端
///   不能触碰 Isar；本波次仅保证 Web 可编译、可启动，持久化语义后续波
///   用 IndexedDB/Hive 等价实现补齐（见 local_database_store_web.dart 的 TODO）。
abstract class LocalDatabaseStore {
  /// 打开后端存储。[schemas] 由门面（local_database.dart）传入，
  /// 使本文件族无需反向依赖门面所在的库。
  Future<void> init(List<CollectionSchema<dynamic>> schemas);

  /// init() 是否已成功完成。
  bool get isReady;

  /// 已打开的 Isar 实例；Web 桩恒为 null。
  Isar? get isarOrNull;

  /// 后端类型标识：'isar' | 'web-stub'。门面用它给出可诊断的报错信息。
  String get kind;
}

LocalDatabaseStore createLocalDatabaseStore() => createLocalDatabaseStoreImpl();
