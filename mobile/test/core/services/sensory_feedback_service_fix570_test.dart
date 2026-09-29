import 'dart:async';
import 'dart:io';

import 'package:audioplayers_platform_interface/audioplayers_platform_interface.dart'
    as api;
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/audio_focus_controller.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// V3-FIX-570 ② · U14 一审 CH-2 `playAmbient` 门拒状态残留回归钉。
///
/// U14R1 审查（v4/evidence/V4-U14/review_r1.md §7 CH-2）：彼时
/// `playAmbient` 在 ambient 门**之前**写 `_currentScene`（并持久化场景），
/// release-only 可达——`_ambientPlayer` 仅由 `_playSound` 懒初始化（生产
/// release 播过任一提示音后非空；debug 走 SystemSound 早退构造不出来）。
/// 残留后果：门拒调用后 `setAmbientEnabled(true)` 不复位运行态 → 用户
/// 显式重选**同场景**被 `scene == _currentScene` 早退吞掉。
///
/// 本卡核验：main HEAD 的 `playAmbient` 已由 S02 一审 D2 整改（ef0901a5）
/// 把 `_currentScene` 写入 + `_saveAmbientScene` 持久化移到**全部门之后**
/// （资产门 → U14 ambient 门 → 焦点会话获批，sensory_feedback_service.dart
/// 提交点 :624 之后的形态）——「门拒零残留」以更强形式（先不写，无需回滚）
/// 成立。缺的是可失败测试钉：本文件两钉 pin 住该不变量，任何把写入挪回
/// 门前的合并（CH-2 形态回归）立即使其一/其二变红。
///
/// 口径与 harness 与 sensory_feedback_service_s02_test.dart 同形制：
/// audioplayers 经平台接口假体逐调用记账。
class _RecordingAudioplayers extends api.AudioplayersPlatformInterface {
  final List<String> calls = <String>[];
  final Map<String, StreamController<api.AudioEvent>> _eventSinks =
      <String, StreamController<api.AudioEvent>>{};

  void _record(Invocation invocation) {
    final text = invocation.memberName.toString();
    final name = text.startsWith('Symbol("')
        ? text.substring('Symbol("'.length, text.length - 2)
        : text;
    calls.add(name);
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

class _NoopGlobalAudioplayers extends api.GlobalAudioplayersPlatformInterface {
  @override
  Stream<api.GlobalAudioEvent> getGlobalEventStream() =>
      const Stream<api.GlobalAudioEvent>.empty();

  @override
  dynamic noSuchMethod(Invocation invocation) => Future<void>.value();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final platform = _RecordingAudioplayers();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    api.AudioplayersPlatformInterface.instance = platform;
    api.GlobalAudioplayersPlatformInterface.instance =
        _NoopGlobalAudioplayers();
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    SensoryFeedbackService.forceNativeDebugSoundFallback = true;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      (call) async => Directory.systemTemp.createTempSync('f570_path_').path,
    );
    platform.calls.clear();
    AudioFocusController.instance.debugReset();
    await SensoryFeedbackService.dispose();
    // release 形态：播放器非空（生产 release 播过任一提示音后即此形态）。
    await SensoryFeedbackService.init();
  });

  tearDown(() async {
    await SensoryFeedbackService.dispose();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.flutter.io/path_provider'),
      null,
    );
    debugDefaultTargetPlatformOverride = null;
    AudioFocusController.instance.debugReset();
  });

  group('FIX-570 ② · U14 ambient 门拒零残留（CH-2 反演钉）', () {
    test('反·开关关闭时点播被门拒：运行场景态与持久化零残留', () async {
      // 前置恒真：背景声开关缺省关闭（U14 绝对缺省）。
      expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);

      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      // CH-2 残留不变量：被拒调用不得改写运行场景态（整改前形态此处为
      // rain）；也不得改写持久化场景（污染重开缺省）。
      expect(
        SensoryFeedbackService.currentScene,
        AmbientScene.none,
        reason: '门拒调用不得留下 _currentScene 残留（CH-2）',
      );
      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.none,
        reason: '门拒调用不得改写持久化场景偏好',
      );
      expect(platform.played, isFalse);
    });

    test('反·门拒→重开开关→同场景显式重放：不被同场景早退吞掉', () async {
      // 第一击：门拒（开关关）。CH-2 形态下此处留下 currentScene=rain。
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.played, isFalse);

      // 重开开关：不自动续播（U14 语义），也不得复位/残留运行态。
      await SensoryFeedbackService.setAmbientEnabled(true);
      await Future<void>.delayed(const Duration(milliseconds: 30));
      expect(platform.played, isFalse);

      // 同场景显式重放（设置 pill autoplay 路径同形态）：唯一再播路径。
      // CH-2 形态下被 scene==_currentScene 早退吞掉（played=false）。
      platform.calls.clear();
      await SensoryFeedbackService.playAmbient(AmbientScene.rain);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(
        platform.played,
        isTrue,
        reason: '门拒后同场景显式重放必须真实可达（被早退吞掉即 CH-2 回归）',
      );
      expect(SensoryFeedbackService.currentScene, AmbientScene.rain);
      expect(
        await SensoryFeedbackService.getSavedAmbientScene(),
        AmbientScene.rain,
      );
    });
  });
}
