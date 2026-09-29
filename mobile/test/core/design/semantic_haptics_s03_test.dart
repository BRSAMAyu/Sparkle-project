// V4-S03 · 平台语义触觉与去重（haptic-policy 锁面）单测。
//
// 每验收面一正一反 + 反例钉（关闭偏好钉 / 去重窗反例钉 / pending·unknown 反例钉）。
// 两层证据：
// - 门级：纯门 + 注入式派发器（记录通道替身/假时钟/探针替身）——确定性正反。
// - 通道级（模拟器调用证据）：SystemChannels.platform 真方法通道 mock 记录
//   `HapticFeedback.vibrate` 调用——「模拟器只认调用证据」的口径面；
//   硬件触感舒适度不在本套件断言范围（真机面归 Q06，DEVICE_UNVERIFIED）。
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/semantic_haptics.dart';
import 'package:sparkle/core/experience/experience_event.dart';
import 'package:sparkle/core/experience/experience_feedback_adapter.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// 记录型通道替身（门级/派发器级确定性证据）。
class _RecordingChannel extends SparkleHapticChannel {
  final List<SparkleHapticPattern> played = <SparkleHapticPattern>[];

  @override
  Future<void> play(SparkleHapticPattern pattern) async {
    played.add(pattern);
  }
}

/// 假时钟（去重窗推进可控）。
class _FakeClock {
  _FakeClock(this.current);
  DateTime current;
  DateTime call() => current;
  void advance(Duration d) => current = current.add(d);
}

/// 真方法通道记录器（通道级证据：SystemChannels.platform 调用史）。
class _PlatformRecorder {
  final List<String> calls = <String>[];

  void install() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform,
        (call) async {
      final arg = call.arguments;
      calls.add(arg == null ? call.method : '${call.method}:$arg');
      return null;
    });
  }

  void uninstall() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, null);
  }

  /// 触觉通道调用（HapticFeedback.* 家族；音频面 SystemSound 不在此列）。
  List<String> get hapticCalls => calls.where((c) => c.startsWith('HapticFeedback.')).toList();

  int get hapticCount => hapticCalls.length;
}

/// committed 成功事件（F03 适配器集成面输入；形状同 B05 契约）。
Map<String, dynamic> _committedTaskEvent({
  String eventId = 'eev_s03_001',
  String versionToken = 'v7',
}) =>
    <String, dynamic>{
      'schema_version': kExperienceEventSchemaVersion,
      'event_id': eventId,
      'kind': 'state_confirmed',
      'receipt_ref': 'action_command://22222222-2222-2222-2222-222222222222',
      'commit_state': 'committed',
      'error_state': null,
      'subject': <String, dynamic>{
        'type': 'task',
        'id': 'task-1',
        'version_token': versionToken,
      },
      'presentation': <String, dynamic>{
        'modalities': <String>['visual', 'audio', 'haptic'],
        'copy_key': 'task.committed',
      },
      'dedupe_key': 'd-$eventId',
      'issued_at': '2026-09-28T00:00:00',
      'expires_at': null,
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final recorder = _PlatformRecorder();
  late _RecordingChannel recording;
  late SemanticHapticDispatcher dispatcher;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await SensoryFeedbackService.dispose();
    // 门级确定性实例：记录通道 + 假时钟默认起点 + 探针默认 android（supported）；
    // 偏好不注入 = 默认走 U14 权威（SensoryFeedbackService）——装配真实性自证。
    recording = _RecordingChannel();
    dispatcher = SemanticHapticDispatcher(
      channel: recording,
      clock: _FakeClock(DateTime(2026, 9, 28, 12)).call,
      capabilityProbe: (_) => SparkleHapticCapability.supported,
    );
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    recorder.calls.clear();
    recorder.install();
  });

  tearDown(() async {
    debugDefaultTargetPlatformOverride = null;
    recorder.uninstall();
    await SensoryFeedbackService.dispose();
  });

  group('A 偏好门（验收1：无用户同意/已关闭 = 0 触觉调用）', () {
    test('正：U14 偏好开启 → 派发一次 successNotification（默认读取器=服务权威）', () async {
      await SensoryFeedbackService.setHapticEnabled(true);
      final decision = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
        ),
      );

      expect(decision.allowed, isTrue);
      expect(decision.pattern, SparkleHapticPattern.successNotification);
      expect(recording.played, [SparkleHapticPattern.successNotification]);
      expect(dispatcher.firedCount, 1);
    });

    test('反例钉：U14 偏好关闭 → 0 通道调用 + 具名抑制（关闭后零触觉调用）', () async {
      await SensoryFeedbackService.setHapticEnabled(false);
      final decision = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
        ),
      );

      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.userPreferenceOff);
      expect(decision.pattern, isNull);
      expect(recording.played, isEmpty);
      expect(dispatcher.suppressedBy[SparkleHapticSuppression.userPreferenceOff], 1);
      // 去重窗不因被抑制调用而占用（关→开翻转后立即可震——钉住门的顺序语义）。
      await SensoryFeedbackService.setHapticEnabled(true);
      final reopen = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
        ),
      );
      expect(reopen.allowed, isTrue);
    });
  });

  group('B 重播门（事件重播不震）', () {
    test('正：首派发放行一次', () async {
      final decision = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.selection,
          phase: SparkleHapticPhase.userInitiated,
        ),
      );

      expect(decision.allowed, isTrue);
      expect(decision.pattern, SparkleHapticPattern.selectionClick);
      expect(recording.played.length, 1);
    });

    test('反例钉：isReplay=true → 0 调用 + eventReplay（恢复重放不重复震）', () async {
      final first = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
        ),
      );
      expect(first.allowed, isTrue);

      final replay = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
          isReplay: true,
        ),
      );

      expect(replay.allowed, isFalse);
      expect(replay.suppression, SparkleHapticSuppression.eventReplay);
      expect(recording.played.length, 1, reason: '重播后总调用仍为首次那一次');
      expect(dispatcher.suppressedBy[SparkleHapticSuppression.eventReplay], 1);
    });
  });

  group('C 相位门（验收2：pending/unknown 不误用 success pattern）', () {
    test('正：终态成功 → successNotification；终态失败 → warningNotification', () async {
      final ok = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
        ),
      );
      final warn = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.warning,
          phase: SparkleHapticPhase.terminalFailure,
        ),
      );

      expect(ok.pattern, SparkleHapticPattern.successNotification);
      expect(warn.pattern, SparkleHapticPattern.warningNotification);
      expect(recording.played.length, 2);
    });

    test('反例钉：pending 相位 → 任何槽 0 调用（success pattern 不可借用）', () async {
      for (final slot in SparkleSemanticHapticSlot.values) {
        final decision = await dispatcher.dispatch(
          SparkleSemanticHapticRequest(
            slot: slot,
            phase: SparkleHapticPhase.pending,
          ),
        );
        expect(decision.allowed, isFalse, reason: '$slot 在 pending 相不放行');
        expect(decision.suppression, SparkleHapticSuppression.phaseNotHapticEligible, reason: '$slot');
      }
      expect(recording.played, isEmpty);
    });

    test('反例钉：unknown 相位 → 任何槽 0 调用（未知不是失败也不是成功）', () async {
      for (final slot in SparkleSemanticHapticSlot.values) {
        final decision = await dispatcher.dispatch(
          SparkleSemanticHapticRequest(
            slot: slot,
            phase: SparkleHapticPhase.unknown,
          ),
        );
        expect(decision.allowed, isFalse, reason: '$slot 在 unknown 相不放行');
      }
      expect(recording.played, isEmpty);
    });

    test('反例钉：成功槽配 userInitiated 相 = 槽/相不符 → 拒（结构性防误用）', () async {
      final decision = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.userInitiated,
        ),
      );

      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.phaseNotHapticEligible);
      expect(recording.played, isEmpty);
    });
  });

  group('D 能力探测门（不支持时静默保持文本，不蜂鸣替代）', () {
    test('正：iOS/Android 判支持 → 放行（纯函数全表断言）', () {
      expect(resolveSparkleHapticCapability(TargetPlatform.iOS), SparkleHapticCapability.supported);
      expect(resolveSparkleHapticCapability(TargetPlatform.android), SparkleHapticCapability.supported);
    });

    test('反例钉：桌面/web 全判不支持 → 0 调用 + platformUnsupported', () async {
      for (final platform in <TargetPlatform>[
        TargetPlatform.macOS,
        TargetPlatform.windows,
        TargetPlatform.linux,
        TargetPlatform.fuchsia,
      ]) {
        final channel = _RecordingChannel();
        final d = SemanticHapticDispatcher(
          channel: channel,
          preferenceReader: () async => true,
          capabilityProbe: (_) => resolveSparkleHapticCapability(platform),
          clock: _FakeClock(DateTime(2026, 9, 28, 12)).call,
        );
        final decision = await d.dispatch(
          const SparkleSemanticHapticRequest(
            slot: SparkleSemanticHapticSlot.success,
            phase: SparkleHapticPhase.terminalSuccess,
          ),
        );
        expect(decision.allowed, isFalse, reason: '$platform 不支持');
        expect(decision.suppression, SparkleHapticSuppression.platformUnsupported, reason: '$platform');
        expect(decision.pattern, isNull, reason: '不支持时无任何替代模式（不蜂鸣）');
        expect(channel.played, isEmpty, reason: '$platform 零触觉调用');
      }
    });
  });

  group('E native 双震门（native已有反馈避免双震）', () {
    test('正：nativeHandled=false 放行一次', () async {
      final decision = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.selection,
          phase: SparkleHapticPhase.userInitiated,
        ),
      );

      expect(decision.allowed, isTrue);
      expect(recording.played.length, 1);
    });

    test(
        '反例钉：nativeHandled=true → 0 调用（框架 enableFeedback/选择器滚轮/'
        '文本选择已有系统触觉处不叠加）', () async {
      final decision = await dispatcher.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.selection,
          phase: SparkleHapticPhase.userInitiated,
          nativeHandled: true,
        ),
      );

      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.nativeFeedbackAlready);
      expect(recording.played, isEmpty);
      expect(dispatcher.suppressedBy[SparkleHapticSuppression.nativeFeedbackAlready], 1);
    });
  });

  group('F 同槽去重窗（同类事件短窗不重复触发）', () {
    test('正：窗外再次派发 → 再次放行（去重不是禁震）', () async {
      final clock = _FakeClock(DateTime(2026, 9, 28, 12));
      final channel = _RecordingChannel();
      final d = SemanticHapticDispatcher(
        channel: channel,
        preferenceReader: () async => true,
        capabilityProbe: (_) => SparkleHapticCapability.supported,
        clock: clock.call,
      );
      const req = SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      );

      expect((await d.dispatch(req)).allowed, isTrue);
      clock.advance(const Duration(milliseconds: 500));
      expect((await d.dispatch(req)).allowed, isTrue);
      expect(channel.played.length, 2);
      expect(d.suppressedBy[SparkleHapticSuppression.dedupedWithinWindow], isNull);
    });

    test('反例钉：窗内同槽二次派发 → 抑制（共 1 次调用）', () async {
      final clock = _FakeClock(DateTime(2026, 9, 28, 12));
      final channel = _RecordingChannel();
      final d = SemanticHapticDispatcher(
        channel: channel,
        preferenceReader: () async => true,
        capabilityProbe: (_) => SparkleHapticCapability.supported,
        clock: clock.call,
      );
      const req = SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      );

      expect((await d.dispatch(req)).allowed, isTrue);
      clock.advance(const Duration(milliseconds: 499));
      final second = await d.dispatch(req);

      expect(second.allowed, isFalse);
      expect(second.suppression, SparkleHapticSuppression.dedupedWithinWindow);
      expect(channel.played.length, 1);
      expect(d.firedCount, 1);
    });

    test(
        '去重按槽隔离：selection 后窗内紧跟 success → 都放行'
        '（按压/成功不可合并——乐谱「两者不可合并」）', () async {
      final clock = _FakeClock(DateTime(2026, 9, 28, 12));
      final channel = _RecordingChannel();
      final d = SemanticHapticDispatcher(
        channel: channel,
        preferenceReader: () async => true,
        capabilityProbe: (_) => SparkleHapticCapability.supported,
        clock: clock.call,
      );

      await d.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.selection,
          phase: SparkleHapticPhase.userInitiated,
        ),
      );
      final ok = await d.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.terminalSuccess,
        ),
      );

      expect(ok.allowed, isTrue);
      expect(channel.played, const [
        SparkleHapticPattern.selectionClick,
        SparkleHapticPattern.successNotification,
      ]);
    });
  });

  group('G 平台语义映射（不造自定义震动语言）', () {
    test('映射表：每槽恰一枚官方模式，成功/警示/选择/轻触各归其位', () {
      expect(kSparkleSemanticHapticPatterns, hasLength(SparkleSemanticHapticSlot.values.length));
      expect(
        kSparkleSemanticHapticPatterns,
        allOf(
          containsPair(SparkleSemanticHapticSlot.selection, SparkleHapticPattern.selectionClick),
          containsPair(SparkleSemanticHapticSlot.lightImpact, SparkleHapticPattern.lightImpact),
          containsPair(SparkleSemanticHapticSlot.success, SparkleHapticPattern.successNotification),
          containsPair(SparkleSemanticHapticSlot.warning, SparkleHapticPattern.warningNotification),
        ),
      );
      // 官方 API 面封闭：模式集合 ⊆ HapticFeedback 七官方语义（每槽一枚，
      // 无组合、无自定义波形概念——表值类型即官方方法直引）。
      expect(
        kSparkleSemanticHapticPatterns.values.toSet().length,
        kSparkleSemanticHapticPatterns.length,
        reason: '无两个槽共用同一枚（每槽语义独立）',
      );
    });

    test(
        '相位表：pending/unknown 不在任何槽的放行集（结构性反例钉）；'
        'success 放行集恒 {terminalSuccess}', () {
      for (final phases in kSparkleHapticSlotPhases.values) {
        expect(phases, isNot(contains(SparkleHapticPhase.pending)), reason: 'pending 不可放行');
        expect(phases, isNot(contains(SparkleHapticPhase.unknown)), reason: 'unknown 不可放行');
      }
      expect(
        kSparkleHapticSlotPhases[SparkleSemanticHapticSlot.success],
        <SparkleHapticPhase>{SparkleHapticPhase.terminalSuccess},
      );
      expect(
        kSparkleHapticSlotPhases[SparkleSemanticHapticSlot.warning],
        <SparkleHapticPhase>{SparkleHapticPhase.terminalFailure},
      );
    });

    test('源码棘轮：锁面文件禁组合脉冲/禁蜂鸣替代/禁原始通道直调', () {
      final source = File('lib/core/design/semantic_haptics.dart').readAsStringSync();
      final stripped = source
          .replaceAll(RegExp(r'///[^\n]*'), '')
          .replaceAll(RegExp(r'//[^\n]*'), '')
          .replaceAll(RegExp(r'/\*[\s\S]*?\*/'), '');
      expect(stripped.contains('Future.delayed'), isFalse, reason: '禁 Future.delayed 组合脉冲（每次派发至多一枚官方模式）');
      expect(stripped.contains('SystemSound'), isFalse, reason: '禁蜂鸣替代（不支持则静默保持文本）');
      expect(stripped.contains("'HapticFeedback"), isFalse, reason: '禁原始方法通道字符串直调（模式只经官方 API 直引枚举）');
    });
  });

  group('H 集成面（F03 适配器 × 默认出口 × 真方法通道——模拟器调用证据）', () {
    late ExperienceFeedbackAdapter adapter;

    setUp(() {
      SemanticHapticDispatcher.instance.resetForTest();
      adapter = ExperienceFeedbackAdapter();
    });

    test('正：committed 任务事件 → 通道恰一次 successNotification', () async {
      final outcome = adapter.present(_committedTaskEvent(), currentSubjectVersionToken: 'v7');
      expect(outcome.action, ExperienceFeedbackAction.presentSuccess);
      await adapter.emitSensory(outcome);

      expect(recorder.hapticCalls, ['HapticFeedback.vibrate:HapticFeedbackType.successNotification']);
    });

    test('反例钉：同 event 重播 → replaySuppressed 且 0 新增触觉调用', () async {
      final first = adapter.present(_committedTaskEvent(), currentSubjectVersionToken: 'v7');
      await adapter.emitSensory(first);

      final replay = adapter.present(_committedTaskEvent(), currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.playsSuccessCue, isFalse);
      await adapter.emitSensory(replay);

      expect(recorder.hapticCount, 1, reason: '重播不震——总调用仍为首次那一次');
    });

    test(
        '反例钉：版本未知（断网未对账）→ presentUnknown 且 0 触觉调用'
        '（不误用 success pattern，通道级）', () async {
      // 显式传 null 是本反例钉的语义锚（断网未对账面），非冗余默认值。
      final outcome = adapter.present(
        _committedTaskEvent(),
        // ignore: avoid_redundant_argument_values
        currentSubjectVersionToken: null,
      );
      expect(outcome.action, ExperienceFeedbackAction.presentUnknown);
      expect(outcome.playsSuccessCue, isFalse);
      await adapter.emitSensory(outcome);

      expect(recorder.hapticCount, 0);
    });

    test(
        '反例钉：U14 关闭触觉偏好 → committed 事件视觉照常、触觉 0 调用'
        '（关闭偏好真实生效——通道级）', () async {
      await SensoryFeedbackService.setHapticEnabled(false);
      final outcome = adapter.present(_committedTaskEvent(eventId: 'eev_s03_off'), currentSubjectVersionToken: 'v7');
      expect(outcome.action, ExperienceFeedbackAction.presentSuccess, reason: '视觉呈现不受触觉偏好影响');
      await adapter.emitSensory(outcome);

      expect(recorder.hapticCount, 0);
      expect(SemanticHapticDispatcher.instance.suppressedBy[SparkleHapticSuppression.userPreferenceOff], 1);
    });
  });
}
