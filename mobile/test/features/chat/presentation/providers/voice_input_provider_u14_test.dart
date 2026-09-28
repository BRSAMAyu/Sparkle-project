import 'package:flutter_test/flutter_test.dart';
import 'package:permission_handler_platform_interface/permission_handler_platform_interface.dart';
import 'package:sparkle/features/chat/presentation/providers/voice_input_provider.dart';

/// V4-U14 · 录音权限拒绝只降该能力（卡验收 2）。
///
/// 一正一反：
/// - 正：授权后 checkPermissions 通过，provider 可进入录音流；
/// - 反：本次拒绝/永久拒绝 → checkPermissions 拒绝且永久拒绝分类如实
///   上浮（永久拒绝 = 去系统设置才可恢复），provider 状态可 reset 复位
///   （语音输入只是聊天目标的一个模态，权限拒绝不锁死 provider）。
class _FakePermissionPlatform extends PermissionHandlerPlatform {
  _FakePermissionPlatform(this._status);

  final PermissionStatus _status;

  @override
  Future<Map<Permission, PermissionStatus>> requestPermissions(
    List<Permission> permissions,
  ) async =>
      {for (final p in permissions) p: _status};

  @override
  Future<PermissionStatus> checkPermissionStatus(Permission permission) async =>
      _status;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('U14 录音权限分类', () {
    setUp(() {
      PermissionHandlerPlatform.instance = _FakePermissionPlatform(
        PermissionStatus.granted,
      );
    });

    tearDown(() {
      PermissionHandlerPlatform.instance = _FakePermissionPlatform(
        PermissionStatus.granted,
      );
    });

    test('正·授权：checkPermissions 通过且无永久拒绝标记', () async {
      final provider = VoiceInputNotifier();
      addTearDown(provider.dispose);

      final granted = await provider.checkPermissions();

      expect(granted, isTrue);
      expect(provider.isPermanentlyDenied, isFalse);
      expect(provider.hasError, isFalse);
    });

    test('反·本次拒绝：checkPermissions 拒绝，非永久拒绝（可再次请求）', () async {
      PermissionHandlerPlatform.instance = _FakePermissionPlatform(
        PermissionStatus.denied,
      );
      final provider = VoiceInputNotifier();
      addTearDown(provider.dispose);

      final granted = await provider.checkPermissions();

      expect(granted, isFalse);
      expect(provider.isPermanentlyDenied, isFalse);
    });

    test('反·永久拒绝：如实上浮分类（引导面据此选「去系统设置」）', () async {
      PermissionHandlerPlatform.instance = _FakePermissionPlatform(
        PermissionStatus.permanentlyDenied,
      );
      final provider = VoiceInputNotifier();
      addTearDown(provider.dispose);

      final granted = await provider.checkPermissions();

      expect(granted, isFalse);
      expect(provider.isPermanentlyDenied, isTrue);
      // 拒绝后 provider 可复位复用（该能力降级不拖垮整个输入面）。
      provider.reset();
      expect(provider.isPermanentlyDenied, isFalse);
      expect(provider.state, VoiceInputState.idle);
    });
  });
}
