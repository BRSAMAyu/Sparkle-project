import 'package:isar/isar.dart';
import 'package:path_provider/path_provider.dart';

import 'local_database_store.dart';

/// 原生平台（Android / iOS / Linux / macOS / Windows）的真实 Isar 后端。
///
/// 注意：集合/索引名已在 multi-platform web-unblock 波次显式 @Name 化
/// （xxh3 id |v| < 2^53，dart2js 可精确表示）。名字变化意味着既有 native
/// 库文件与旧 schema 不兼容——演示/开发环境直接清库即可。
class LocalDatabaseStoreIsar implements LocalDatabaseStore {
  Isar? _isar;

  @override
  bool get isReady => _isar != null;

  @override
  Isar? get isarOrNull => _isar;

  @override
  String get kind => 'isar';

  @override
  Future<void> init(List<CollectionSchema<dynamic>> schemas) async {
    if (isReady) return;
    final dir = await getApplicationDocumentsDirectory();
    // In production, you would fetch a secure key from SecureStorage
    // final secureStorage = const FlutterSecureStorage();
    // final encryptionKey = await secureStorage.read(key: 'db_key');

    _isar = await Isar.open(schemas, directory: dir.path);
  }
}

LocalDatabaseStore createLocalDatabaseStoreImpl() => LocalDatabaseStoreIsar();
