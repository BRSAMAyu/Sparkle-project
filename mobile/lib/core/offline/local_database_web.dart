// Web implementation of LocalDatabase

class LocalDatabase {
  factory LocalDatabase() => _instance;

  LocalDatabase._internal();
  static final LocalDatabase _instance = LocalDatabase._internal();

  Future<void> init() async {
    // No-op for web platform
  }
}