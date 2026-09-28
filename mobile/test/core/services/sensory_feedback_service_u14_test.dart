import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// V4-U14 · 背景声/提示音独立偏好 + 音频诚实降级（卡验收 1/2 机制面）。
///
/// 每个验收面一正一反：
/// - 独立性：关提示音不停背景声（正）；关背景声不停提示音（反演对称）。
/// - 向后兼容：无 ambient 键时继承提示音开关（老用户不被升级悄悄打开）。
/// - 重开保持：偏好写入持久层后，「重启」（dispose 重载）后仍可读回。
/// - 诚实降级：系统拒绝播放 → 降级位（后续事件不再逐次重试）；用户显式
///   重开提示音 → 降级位清除（显式重试）；触觉不受降级影响。
void main() {
  // 降级用例直接 emit（触觉走 HapticFeedback 平台通道），需先初始化 binding。
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    // dispose 清空静态缓存（玩家池/prefs/降级位）→ 每个用例都是一次
    // 「冷启动」：_getPrefs 从当前 mock store 重新装载，验证真实持久化。
    await SensoryFeedbackService.dispose();
  });

  tearDown(() async {
    await SensoryFeedbackService.dispose();
  });

  group('U14 背景声独立偏好', () {
    test('正：显式开启背景声后，关闭提示音不影响背景声偏好', () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.setSoundEnabled(false);

      expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);
      expect(await SensoryFeedbackService.isAmbientEnabled(), isTrue);
    });

    test('反演：关闭背景声不影响提示音偏好', () async {
      await SensoryFeedbackService.setSoundEnabled(true);
      await SensoryFeedbackService.setAmbientEnabled(false);

      expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);
      expect(await SensoryFeedbackService.isSoundEnabled(), isTrue);
    });

    test('向后兼容：无 ambient 键时缺省关闭（老用户不被升级悄悄打开；'
        'V4-S02 收紧缺省为绝对关闭，比继承更强——见卡验收1「未明确点播无声音」）',
        () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        'sensory_feedback.sound_enabled': false,
      });
      await SensoryFeedbackService.dispose();

      expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);
    });

    test('V4-S02 缺省收紧：即使提示音开着，无 ambient 键也缺省关闭', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        'sensory_feedback.sound_enabled': true,
      });
      await SensoryFeedbackService.dispose();

      expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);
    });

    test('向后兼容：显式 ambient 键优先于继承（首次切换后即独立）', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        'sensory_feedback.sound_enabled': false,
        'sensory_feedback.ambient_enabled': true,
      });
      await SensoryFeedbackService.dispose();

      expect(await SensoryFeedbackService.isAmbientEnabled(), isTrue);
      expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);
    });

    test('重开保持：偏好落持久层，重启（dispose 重载）后读回一致', () async {
      await SensoryFeedbackService.setAmbientEnabled(false);
      await SensoryFeedbackService.setSoundEnabled(false);
      await SensoryFeedbackService.setHapticEnabled(false);

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getBool('sensory_feedback.ambient_enabled'), isFalse);
      expect(prefs.getBool('sensory_feedback.sound_enabled'), isFalse);
      expect(prefs.getBool('sensory_feedback.haptic_enabled'), isFalse);

      // 「重启」：清静态缓存后从持久层重载（setUp 的 dispose 等价路径）。
      await SensoryFeedbackService.dispose();
      expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);
      expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);
      expect(await SensoryFeedbackService.isHapticEnabled(), isFalse);
    });

    test('关闭提示音不清除已保存的背景声场景（重开背景声后场景仍在）', () async {
      await SensoryFeedbackService.setAmbientScene(AmbientScene.rain);
      await SensoryFeedbackService.setSoundEnabled(false);

      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.rain,
      );
    });
  });

  group('U14 音频诚实降级', () {
    test('降级位可读；不向任务流抛错（emit 恒安全）', () async {
      expect(SensoryFeedbackService.audioPlaybackDegraded, isFalse);

      SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);
      expect(SensoryFeedbackService.audioPlaybackDegraded, isTrue);

      // 降级态下 emit 不抛异常、不影响调用方（任务/提醒流程照常）。
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
    });

    test('用户显式重开提示音 = 显式重试 → 降级位清除', () async {
      SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);
      expect(SensoryFeedbackService.audioPlaybackDegraded, isTrue);

      await SensoryFeedbackService.setSoundEnabled(true);
      expect(SensoryFeedbackService.audioPlaybackDegraded, isFalse);
    });

    test('降级只作用于提示音，不吞掉触觉通道开关', () async {
      SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);
      await SensoryFeedbackService.setHapticEnabled(false);

      expect(await SensoryFeedbackService.isHapticEnabled(), isFalse);
      expect(SensoryFeedbackService.audioPlaybackDegraded, isTrue);
    });
  });
}
