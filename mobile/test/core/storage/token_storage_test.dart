import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/core/storage/token_storage_web.dart';

/// W-1/W-2 红绿测试：token 存储门面。
///
/// 红（修复前）：TokenStorage/TokenStorageWeb 不存在、AuthRepository 仅接受
/// FlutterSecureStorage —— 本文件无法编译通过；且浏览器实测（web-round1，
/// IndexedDB `user.box` 空盒）证明 secure storage web 并发写全丢。
/// 绿（修复后）：web 后端经 SharedPreferences(localSorage) 落盘，以下全部通过。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('TokenStorageWeb（web 后端：SharedPreferences/localStorage）', () {
    test('write 后 read 取回；delete 后为 null', () async {
      SharedPreferences.setMockInitialValues({});
      final storage = TokenStorageWeb();

      await storage.write('accessToken', 'token-abc');
      expect(await storage.read('accessToken'), 'token-abc');

      await storage.delete('accessToken');
      expect(await storage.read('accessToken'), isNull);
    });

    test('saveTokens 的并发写模式（曾致 secure storage web 全丢）不再丢数据',
        () async {
      SharedPreferences.setMockInitialValues({});
      final storage = TokenStorageWeb();

      // 复刻 saveTokens 的 4 连写形态（access/refresh/legacy-access/legacy-refresh）。
      // round-1 走查实证 flutter_secure_storage web 在此模式下静默全丢。
      await Future.wait<void>([
        storage.write('accessToken', 'access-1'),
        storage.write('refreshToken', 'refresh-1'),
        storage.write('accessTokenLegacy', 'access-1'),
        storage.write('refreshTokenLegacy', 'refresh-1'),
      ]);

      expect(await storage.read('accessToken'), 'access-1');
      expect(await storage.read('refreshToken'), 'refresh-1');
      expect(await storage.read('accessTokenLegacy'), 'access-1');
      expect(await storage.read('refreshTokenLegacy'), 'refresh-1');
    });

    test('read 未命中返回 null（契约语义）', () async {
      SharedPreferences.setMockInitialValues({});
      final storage = TokenStorageWeb();

      expect(await storage.read('never-written'), isNull);
    });
  });

  test('VM（flutter test）下工厂解析到 io/secure 后端而非 web 后端', () {
    final storage = createTokenStorage();
    expect(storage, isA<TokenStorage>());
    expect(storage, isNot(isA<TokenStorageWeb>()));
  });
}
