import 'dart:async';
import 'dart:io';

import 'package:audioplayers_platform_interface/audioplayers_platform_interface.dart'
    as api;
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/audio_asset_gate.dart';
import 'package:sparkle/core/services/audio_focus_controller.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// V4-S02 · 服务面集成（卡验收 1/2 的调用级证据，每面一正一反）。
///
/// - 验收1「未明确点播无声音」：默认偏好（无任何显式开启）下 emit 不产生
///   任何播放调用；反例：用户显式开启后 emit 发声。
/// - 验收1「重开不自续」：已保存场景 + 已开启背景声的「重开」（dispose 重
///   装载）后，无任何自动播放调用；焦点恒 IDLE；只有显式 playAmbient 才
///   出声（与 U14「开启开关不自动续播」语义对齐）。
/// - 验收2「录音不回录提示音」：录音抢占期间 emit 零播放调用（反例钉），
///   录音结束后恢复。
/// - 验收2「TTS 可 duck/暂停环境床」：TTS 抢占 → 环境床输出音量压低至
///   用户音量 × kTtsAmbientDuckFactor；结束复原。
/// - 两独立音量：sfx 音量与环境音量互不连带（键级隔离钉）。
/// - 一审整改面：D1「耳机拔出后同场景显式重选真实可达」（stoppedByUser 清
///   运行场景态）与 D2「录音中改选场景被拒零残留」（会话获批后才提交
///   _currentScene 写入+持久化）——探针形态复现见对应 group。
///
/// 口径：audioplayers 经平台接口假体逐调用记账（模拟器只认调用与录制证据；
/// 真扬声器未测，DEVICE_UNVERIFIED 归 Q06）。
class _RecordingAudioplayers extends api.AudioplayersPlatformInterface {
  final List<String> calls = <String>[];
  final List<double> volumeCalls = <double>[];
  final Map<String, StreamController<api.AudioEvent>> _eventSinks =
      <String, StreamController<api.AudioEvent>>{};

  void _record(Invocation invocation) {
    final text = invocation.memberName.toString(); // Symbol("play")
    final name = text.startsWith('Symbol("')
        ? text.substring('Symbol("'.length, text.length - 2)
        : text;
    calls.add(name);
    if (invocation.memberName == #setVolume &&
        invocation.positionalArguments.length > 1) {
      // 平台接口方法签名是 setVolume(playerId, volume)：音量在第二个位置。
      final v = invocation.positionalArguments[1];
      if (v is double) {
        volumeCalls.add(v);
      }
    }
    // AudioPlayer.play/setSource 会等平台回 prepared 事件（_completePrepared）：
    // setSource* 调用落地后异步补发 prepared=true，模拟平台就绪。
    if (invocation.memberName == #setSourceUrl ||
        invocation.memberName == #setSourceBytes) {
      final playerId = invocation.positionalArguments.first as String;
      // ignore: close_sinks
      final sink = _eventSinks[playerId];
      if (sink != null && !sink.isClosed) {
        scheduleMicrotask(
          () => sink.add(
            const api.AudioEvent(
              eventType: api.AudioEventType.prepared,
              isPrepared: true,
            ),
          ),
        );
      }
    }
  }

  bool get played => calls.any(
        (c) => c == 'setSourceUrl' || c == 'play' || c == 'resume',
      );

  @override
  Stream<api.AudioEvent> getEventStream(String playerId) => _eventSinks
      .putIfAbsent(
        playerId,
        StreamController<api.AudioEvent>.broadcast,
      )
      .stream;

  @override
  Future<void> create(String playerId) async {
    calls.add('create');
  }

  @override
  Future<void> dispose(String playerId) async {
    calls.add('dispose');
    final sink = _eventSinks.remove(playerId);
    unawaited(sink?.close());
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    _record(invocation);
    if (invocation.memberName == #getDuration ||
        invocation.memberName == #getCurrentPosition) {
      return Future<int?>.value(0);
    }
    return Future<void>.value();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final platform = _RecordingAudioplayers();
  var systemSoundPlays = 0;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    api.AudioplayersPlatformInterface.instance = platform;
    api.GlobalAudioplayersPlatformInterface.instance =
        _NoopGlobalAudioplayers();
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    SensoryFeedbackService.forceNativeDebugSoundFallback = true;
    systemSoundPlays = 0;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
      if (call.method == 'SystemSound.play') {
        systemSoundPlays++;
      }
      return null;
    });
    // audioplayers 播 AssetSource 时把资产复制到临时目录（path_provider）。
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      (call) async => Directory.systemTemp.createTempSync('s02_path_').path,
    );
    platform.calls.clear();
    platform.volumeCalls.clear();
    AudioFocusController.instance.debugReset();
    await SensoryFeedbackService.dispose();
  });

  tearDown(() async {
    await SensoryFeedbackService.dispose();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, null);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      null,
    );
    debugDefaultTargetPlatformOverride = null;
    AudioFocusController.instance.debugReset();
  });

  group('S02 验收1 · 未明确点播无声音', () {
    test('正·默认偏好（未点播）emit 零播放调用（提示音默认关闭）', () async {
      expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);

      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
      // 服务面 play 为 fire-and-forget：等一拍让平台调用落地再断言。
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(systemSoundPlays, 0);
      expect(platform.played, isFalse);
    });

    test('反例·用户显式开启提示音后 emit 发声（点播后尊重当前偏好）', () async {
      await SensoryFeedbackService.setSoundEnabled(true);

      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(systemSoundPlays, greaterThan(0));
    });

    test('重开不自续：场景/开关已保存，「重开」（dispose 重装载）零自动播放',
        () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.setAmbientScene(AmbientScene.rain);
      // setAmbientScene 不 autoplay：此刻就不应发声。
      expect(platform.played, isFalse);

      // 「重开 App」：清进程态（含焦点会话）后从持久层重装。
      await SensoryFeedbackService.dispose();
      AudioFocusController.instance.debugReset();
      platform.calls.clear();
      await SensoryFeedbackService.init();

      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.rain,
      );
      expect(await SensoryFeedbackService.isAmbientEnabled(), isTrue);
      // 重开后：播放器初始化（create）可以发生，但零播放调用、焦点 IDLE。
      expect(platform.played, isFalse);
      expect(AudioFocusController.instance.state, AudioFocusState.idle);

      // 对照：用户显式点播（选场景/开始专注）才有播放调用。
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      expect(platform.played, isTrue);
    });
  });

  group('S02 验收2 · 录音不回录提示音', () {
    test('正·录音抢占期间 emit 零播放调用（开启提示音也拦）', () async {
      await SensoryFeedbackService.setSoundEnabled(true);

      AudioFocusController.instance.beginRecording();

      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      // 反例钉（录音回录被拦）：提示音已开启、事件在节流预算内，仍零输出。
      expect(systemSoundPlays, 0);
      expect(platform.played, isFalse);
    });

    test('反演·录音结束后 emit 恢复发声（抑制随抢占解除）', () async {
      await SensoryFeedbackService.setSoundEnabled(true);
      AudioFocusController.instance.beginRecording();
      AudioFocusController.instance.endRecording();

      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(systemSoundPlays, greaterThan(0));
    });

    test('录音抢占暂停环境床；结束按平台惯例恢复（调用级）', () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.init();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      expect(platform.played, isTrue);
      platform.calls.clear();

      AudioFocusController.instance.beginRecording();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.calls, contains('pause'));

      platform.calls.clear();
      AudioFocusController.instance.endRecording();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.calls, contains('resume'));
    });
  });

  group('S02 验收2 · TTS 可 duck/暂停环境床', () {
    test('正·TTS 抢占 → 环境床压低至 用户音量 × duck；结束复原', () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.setAmbientVolume(0.8);
      await SensoryFeedbackService.init();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      platform.volumeCalls.clear();

      AudioFocusController.instance.beginTts();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.volumeCalls.last, closeTo(0.8 * kTtsAmbientDuckFactor, 0.01));

      AudioFocusController.instance.endTts();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.volumeCalls.last, closeTo(0.8, 0.01));
    });

    test('反·duck 改变期间调整环境音量，输出仍含 duck 系数（不越权放大）',
        () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.setAmbientVolume(0.8);
      await SensoryFeedbackService.init();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);

      AudioFocusController.instance.beginTts();
      platform.volumeCalls.clear();
      await SensoryFeedbackService.setAmbientVolume(1.0);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(platform.volumeCalls.last, closeTo(1.0 * kTtsAmbientDuckFactor, 0.01));
    });
  });

  group('S02 · 耳机拔出（调用级）', () {
    test('播放中耳机拔出 → 环境床 stop（不转扬声器续播）；resumeAmbient 拒绝自续',
        () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.init();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      platform.calls.clear();

      AudioFocusController.instance.handleHeadphoneUnplugged();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.calls, contains('stop'));

      // 抢占结束后服务面 resume 也不得复活（MOTION：不转扬声器大声续播）。
      AudioFocusController.instance.endTts();
      await SensoryFeedbackService.resumeAmbient();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(
        platform.calls.where((c) => c == 'resume'),
        isEmpty,
      );

      // 唯一再播路径 = 用户显式点播：停止后**同场景**显式重选必须真实可达。
      // D1 整改（一审 COND-1）：stoppedByUser 分支清空 _currentScene，同场景
      // 早退不再吞掉重选——整改前此处 played=false（原注释声称「rain→none
      // 由 stop 清空后可重播」与实现不符，已随本断言一并修正）。
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.played, isTrue);
      expect(SensoryFeedbackService.currentScene, AmbientScene.rain);
      expect(AudioFocusController.instance.state, AudioFocusState.userPlaying);
    });
  });

  group('S02 · 录音中改选场景（D2 整改：会话被拒零残留）', () {
    test('正·录音抢占中点播新场景被拒：运行态/prefs 零残留，结束恢复同轨',
        () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.init();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.rain,
      );

      AudioFocusController.instance.beginRecording();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      platform.calls.clear();

      // 一审 D2 探针形态复现：录音抢占中改选 ocean。会话被拒——场景运行态
      // 与持久化都不得改写（整改前：currentScene/prefs 已变 ocean）。
      await SensoryFeedbackService.playAmbient(AmbientScene.ocean);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(SensoryFeedbackService.currentScene, AmbientScene.rain);
      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.rain,
      );
      expect(platform.played, isFalse);

      // 结束录音按平台惯例恢复：恢复的音轨与 currentScene 指向一致（整改前
      // 错位：currentScene=ocean 实际 resume 的是 rain 音轨）。
      AudioFocusController.instance.endRecording();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.calls, contains('resume'));
      expect(SensoryFeedbackService.currentScene, AmbientScene.rain);
    });

    test('反例钉·被拒点播零残留，使录音结束后同请求真实换轨可达', () async {
      await SensoryFeedbackService.setAmbientEnabled(true);
      await SensoryFeedbackService.init();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);

      AudioFocusController.instance.beginRecording();
      await Future<void>.delayed(const Duration(milliseconds: 30));
      await SensoryFeedbackService.playAmbient(AmbientScene.ocean);
      AudioFocusController.instance.endRecording();
      await Future<void>.delayed(const Duration(milliseconds: 30));

      // 录音结束后重发同一请求（改选 ocean）：若被拒路径残留了 ocean 态，
      // 这里会被同场景早退吞掉（整改前 played=false 的探针下游实测）。
      platform.calls.clear();
      await SensoryFeedbackService.playAmbient(AmbientScene.ocean);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(platform.played, isTrue);
      expect(SensoryFeedbackService.currentScene, AmbientScene.ocean);
      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.ocean,
      );
      // 换轨：旧音轨被显式停掉再起新轨。
      expect(platform.calls, contains('stop'));
    });
  });

  group('S02 · 两独立音量（键级隔离）', () {
    test('正·setSfxVolume 只写提示音音量轴', () async {
      await SensoryFeedbackService.setAmbientVolume(0.7);
      await SensoryFeedbackService.setSfxVolume(0.2);

      expect(await SensoryFeedbackService.getSfxVolume(), 0.2);
      expect(await SensoryFeedbackService.getAmbientVolume(), 0.7);
    });

    test('反演·setAmbientVolume 不连带提示音音量', () async {
      await SensoryFeedbackService.setSfxVolume(0.3);
      await SensoryFeedbackService.setAmbientVolume(0.9);

      expect(await SensoryFeedbackService.getAmbientVolume(), 0.9);
      expect(await SensoryFeedbackService.getSfxVolume(), 0.3);
    });

    test('提示音音量乘入输出（调用级：pool 路径 setVolume 记账）', () async {
      await SensoryFeedbackService.setSoundEnabled(true);
      SensoryFeedbackService.forceNativeDebugSoundFallback = false;
      await SensoryFeedbackService.setSfxVolume(0.5);

      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      // success 规格音量 0.22 × 用户 0.5 = 0.11（clamp 前合成在服务内完成）。
      expect(
        platform.volumeCalls.any((v) => (v - 0.11).abs() < 0.001),
        isTrue,
      );
    });
  });

  group('S02 · 环境床场景全部持有合法许可（服务面 ⇄ 账本）', () {
    test('正·AmbientScene 全部 assetPath 在许可集内（可播）', () {
      for (final scene in AmbientScene.values) {
        final path = scene.assetPath;
        if (path == null) continue;
        expect(
          AudioAssetGate.isLicensed(path),
          isTrue,
          reason: '$path 必须在 S04 账本 APPROVED∩ship 集（否则不许进 bundle）',
        );
      }
    });
  });
}

class _NoopGlobalAudioplayers extends api.GlobalAudioplayersPlatformInterface {
  @override
  Stream<api.GlobalAudioEvent> getGlobalEventStream() =>
      const Stream<api.GlobalAudioEvent>.empty();

  @override
  dynamic noSuchMethod(Invocation invocation) => Future<void>.value();
}
