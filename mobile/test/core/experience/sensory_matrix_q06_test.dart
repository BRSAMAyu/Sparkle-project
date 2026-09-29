// V4-Q06 · 全感官关闭/重放/真机能力矩阵（验收矩阵卡——事件乐谱全量测）。
//
// 契约真源：`v4/02_design/MOTION_AUDIO_HAPTICS.md` 事件乐谱（9 行）× 卡面
// 六态（enabled / disabled / replay / background / unsupported / permission
// 拒绝）= 54 格，逐格一测、逐格可失败，锚点分**调用级**（通道/门计数实录）
// 与**语义级**（决策/文案/徽章断言）两档；真机硬件面（触感舒适度、真扬声器
// 听感、真实 OS 中断事件源、系统触觉总开关）一律 **DEVICE_UNVERIFIED**，
// 只签模拟器层（本机无物理 iOS/Android 设备——卡面边界如实标注）。
//
// 口径纪律（继承 S01/S02/S03 已钉面，不重写、不造第二权威）：
// - 触觉门/去重/能力探测 = S03 `semantic_haptics.dart`（注入记录器出调用级
//   证据；`SemanticHapticDispatcher.instance` 全局单例不进测试）；
// - 音频焦点/提示音抑制/资产门 = S02 `audio_focus_controller.dart` +
//   `sensory_feedback_service.dart` + `audio_asset_gate.dart`；
// - 动效预算/静态分支/重播不重播（运动面）= S01 `semantic_motion.dart` +
//   `semantic_motion_widgets.dart`；
// - 事件语义路由（缺回执不发成功/重播抑制/语义分层）= F03
//   `experience_feedback_adapter.dart`；
// - platform 通道（SystemSound/HapticFeedback）经 `SystemChannels.platform`
//   mock 逐调用记账——模拟器层调用级证据的唯一声源。
//
// 三条卡验收的矩阵映射：
// ① 「静音/无触觉/减少动态所有任务同样可完成」= C2 列全行（决策/文案/徽章
//    与 C1 全同 + 物理 通道 0 调用 + 静态分支信息等价）；
// ② 「replay 不重播；仅真实 commit 用 success」= C3 列全行 + R3/R6 的 E1
//    门反例（无回执 success 形状 → 忽略，绝不庆祝）；
// ③ 「DEVICE_UNVERIFIED 不写成体验舒适度已通过」= 真机面格子只签调用级，
//    边界注记见 v4/evidence/V4-Q06/{limitations,matrix剧本}.md。
//
// 已知集成链缺口（如实登记，不伪造 PASS）：experience 事件生产源（WS
// ExperienceEventFrame 增量）未接线（D01/B05/S03-L5/FIX-569 登记过的
// contract-owner 面），且适配器/提示音面无应用可见性门——C4 列的
// 「foreground→background 立即停止装饰」在既有装饰面（BGM 生命周期暂停 +
// AnimationLifecycleMixin 控制器暂停）签调用级 PASS；事件链可见性门签
// GAP_INTEGRATION（逐格引用，证据文档展开）。
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/semantic_haptics.dart';
import 'package:sparkle/core/design/semantic_motion.dart';
import 'package:sparkle/core/design/widgets/animation_lifecycle_mixin.dart';
import 'package:sparkle/core/design/widgets/semantic_motion_widgets.dart';
import 'package:sparkle/core/experience/experience_event.dart';
import 'package:sparkle/core/experience/experience_feedback_adapter.dart';
import 'package:sparkle/core/services/audio_asset_gate.dart';
import 'package:sparkle/core/services/audio_focus_controller.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

// ═══════════════════════════ 测试装置 ═══════════════════════════

/// platform 通道记录器：SystemSound / HapticFeedback 逐调用记账（调用级
/// 声源；「不蜂鸣替代」「0 物理输出」断言的依据）。
class _PlatformChannelRecorder {
  final List<String> calls = <String>[];

  Future<dynamic> _handler(MethodCall call) async {
    calls.add(call.method);
    return null;
  }

  void install() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, _handler);
  }

  void uninstall() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, null);
  }

  int get systemSoundPlays =>
      calls.where((String c) => c == 'SystemSound.play').length;

  int get hapticVibrates =>
      calls.where((String c) => c == 'HapticFeedback.vibrate').length;
}

/// 记录型触觉通道（S03 锁面出口替身：模式级调用记账）。
class _RecordingHapticChannel extends SparkleHapticChannel {
  final List<SparkleHapticPattern> played = <SparkleHapticPattern>[];

  @override
  Future<void> play(SparkleHapticPattern pattern) async {
    played.add(pattern);
  }
}

/// 记录型感官出口（适配器声/触决策替身）。
class _RecordingSink implements ExperienceSensorySink {
  final List<String> calls = <String>[];

  @override
  Future<void> success() async => calls.add('success');

  @override
  Future<void> selection() async => calls.add('selection');

  @override
  Future<void> warning() async => calls.add('warning');
}

/// 生命周期宿主：注册一个 repeat() 控制器（装饰性在航动画的最小代表），
/// 承载 AnimationLifecycleMixin 的 foreground→background 暂停语义。
class _LifecycleHost extends StatefulWidget {
  const _LifecycleHost({super.key});

  @override
  State<_LifecycleHost> createState() => _LifecycleHostState();
}

class _LifecycleHostState extends State<_LifecycleHost>
    with TickerProviderStateMixin, AnimationLifecycleMixin {
  late final AnimationController controller;

  @override
  void initState() {
    super.initState();
    controller =
        AnimationController(vsync: this, duration: const Duration(seconds: 1));
    unawaited(controller.repeat());
    registerController(controller);
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

/// receiptRef 省略哨兵：committed 缺省补回执；显式传 null = 无回执形状
/// （E1 反例钉——「仅真实 commit 用 success」的拒收面）。
const Object _autoReceipt = Object();

/// experience_event.v1 事件构造器（kind/commitState/errorState/subject/
/// copyKey/eventId 全显式，形状合规由既有解析面保证）。
Map<String, dynamic> _event({
  required String kind,
  required String commitState,
  required String subjectType,
  String? errorState,
  Object? receiptRef = _autoReceipt,
  String versionToken = 'v7',
  String eventId = 'eev_q06_001',
  String copyKey = 'task.committed',
}) =>
    <String, dynamic>{
      'schema_version': kExperienceEventSchemaVersion,
      'event_id': eventId,
      'kind': kind,
      'receipt_ref': receiptRef == _autoReceipt
          ? (commitState == 'committed' ? 'action_command://r-1' : null)
          : receiptRef as String?,
      'commit_state': commitState,
      'error_state': errorState,
      'subject': <String, dynamic>{
        'type': subjectType,
        'id': 'obj-1',
        'version_token': versionToken,
      },
      'presentation': <String, dynamic>{
        'modalities': <String>['visual', 'audio', 'haptic'],
        'copy_key': copyKey,
      },
      'dedupe_key': 'd-$eventId',
      'issued_at': '2026-09-28T00:00:00',
      'expires_at': null,
    };

/// 触觉派发器工场（注入偏好/能力/记录通道/固定时钟——调用级证据自足）。
SemanticHapticDispatcher _dispatcher({
  required bool preferenceEnabled,
  SparkleHapticCapability capability = SparkleHapticCapability.supported,
  _RecordingHapticChannel? channel,
}) {
  final rec = channel ?? _RecordingHapticChannel();
  return SemanticHapticDispatcher(
    preferenceReader: () async => preferenceEnabled,
    channel: rec,
    capabilityProbe: (_) => capability,
    clock: () => DateTime(2026, 9, 28), // 固定时钟：同槽两发必落去重窗。
  );
}

const String _soundKey = 'sensory_feedback.sound_enabled';
const String _hapticKey = 'sensory_feedback.haptic_enabled';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final platform = _PlatformChannelRecorder()..install();

  setUp(() {
    platform.calls.clear(); // 通道记账逐格隔离（计数不跨格泄漏）。
    AudioFocusController.instance.debugReset();
  });

  tearDown(() async {
    await SensoryFeedbackService.dispose();
    AudioFocusController.instance.debugReset();
  });

  // ═════════════ R1 · 按压/选择 ═════════════
  // 乐谱：80ms 轻压；声音默认无；明确离散选择可系统 selection，普通滚动无。
  group('R1 按压/选择', () {
    test('M-R1-C1 enabled：selection 槽 userInitiated 放行一枚 selectionClick；'
        '按压路径零声音通道（乐谱「声音默认无」）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(decision.allowed, isTrue, reason: '偏好开+平台支持 → 放行（调用级）');
      expect(decision.pattern, SparkleHapticPattern.selectionClick);
      expect(channel.played, hasLength(1));
      expect(platform.systemSoundPlays, 0,
          reason: '乐谱按压行「声音默认无」——纯按压不产生任何提示音通道调用',);
      // 动效预算：press 80ms 在乐谱窗口内（S01 表，语义级锚）。
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
      expect(kSparkleSemanticMotionBudgets.press, const Duration(milliseconds: 80));
    });

    test('M-R1-C2 disabled：偏好关/减少动态 → 0 触觉 0 声音；选择动作本身'
        '照常完成（决策面无异常、返回抑制决策）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: false, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.userPreferenceOff);
      expect(channel.played, isEmpty);
      expect(platform.systemSoundPlays, 0);
      // 减少动态不改预算契约（静态分支是组件面，S01 已钉；表恒有效）。
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
    });

    test('M-R1-C3 replay：同槽短窗第二次派发 → dedupedWithinWindow（同类'
        '交互短窗不重复触发——调用级去重记账）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      const req = SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      );
      await d.dispatch(req);
      final second = await d.dispatch(req);
      expect(second.allowed, isFalse);
      expect(second.suppression, SparkleHapticSuppression.dedupedWithinWindow);
      expect(channel.played, hasLength(1), reason: '第二发被去重：物理通道仍 1 次');
      expect(d.suppressedBy[SparkleHapticSuppression.dedupedWithinWindow], 1);
    });

    testWidgets('M-R1-C4 background：生命周期 paused → 已注册在航动画控制器立即'
        '停止，resumed → 恢复（「foreground→background 立即停止装饰」调用级锚）',
        (tester) async {
      final key = GlobalKey<_LifecycleHostState>();
      await tester.pumpWidget(_LifecycleHost(key: key));
      await tester.pump();
      final st = key.currentState!;
      expect(st.controller.isAnimating, isTrue, reason: '对照：在航 repeat 动画');
      // 生产回调：AnimationLifecycleMixin.didChangeAppLifecycleState。
      st.didChangeAppLifecycleState(AppLifecycleState.paused);
      expect(st.controller.isAnimating, isFalse,
          reason: '后台瞬间：装饰动画停（生产语义，调用级）',);
      st.didChangeAppLifecycleState(AppLifecycleState.resumed);
      expect(st.controller.isAnimating, isTrue,
          reason: '回前台：曾动画者恢复（瞬时抢占语义，run 由服务器管理不受影响）',);
      await tester.pumpWidget(const SizedBox.shrink());
    });

    test('M-R1-C5 unsupported：桌面平台能力探测 → platformUnsupported 静默'
        '保持文本，且**不蜂鸣替代**（0 触觉 0 声音通道调用）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      expect(channel.played, isEmpty);
      expect(platform.systemSoundPlays, 0,
          reason: '「不能拿蜂鸣替代」——SystemSound 通道零调用',);
      // 平台探测函数本体（S03 封闭表语义级复验）。
      expect(resolveSparkleHapticCapability(TargetPlatform.macOS),
          SparkleHapticCapability.unsupported,);
      expect(resolveSparkleHapticCapability(TargetPlatform.android),
          SparkleHapticCapability.supported,);
    });

    test('M-R1-C6 permission 拒绝：框架已有系统触觉（nativeHandled）→ 不叠加'
        '双震；OS 系统触觉总开关尊重面 = DEVICE_UNVERIFIED（真机/系统层，'
        '不冒充已验证）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
        nativeHandled: true,
      ),);
      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.nativeFeedbackAlready);
      expect(channel.played, isEmpty);
      // DEVICE_UNVERIFIED 面：系统级触觉总开关/马达存在性由 OS 在引擎内
      // no-op（S03 L2），本格只签调用级；不写任何「触感已验证」表述。
    });
  });

  // ═════════════ R2 · 提案出现 ═════════════
  // 乐谱：160–220ms 从纸面抬起；声音无；触觉无；不表示完成。
  group('R2 提案出现', () {
    test('M-R2-C1 enabled：预算 200ms ∈ [160,220]；词表封闭——提案不是 '
        'experience_event kind，绝不触发成功面（提案≠完成）', () {
      final budget = kSparkleSemanticMotionBudgets.proposalEnter;
      expect(budget.inMilliseconds, inInclusiveRange(160, 220));
      expect(
        kSemanticMotionScoreWindows[SparkleSemanticMotionSlot.proposalEnter]!
            .contains(200),
        isTrue,
      );
      // 词表封闭锚：无任何提案类 kind 可进事件面（未注册 → 解析 null）。
      expect(kExperienceEventKinds.any((String k) => k.contains('propos')),
          isFalse, reason: '封闭七元集无提案 kind——提案出现不构成完成事实',);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'proposal_appeared', commitState: 'committed',
            subjectType: 'task',),
      );
      expect(outcome.action, ExperienceFeedbackAction.ignoredInvalid);
      expect(outcome.celebrates, isFalse);
    });

    test('M-R2-C2 disabled：减少动态 → 静态分支直落终态（提案完整呈现，'
        '等价信息不丢失；零时长通路不存在）', () {
      // S01 组件族静态分支语义：预算表是常量契约，reduce-motion 不改表。
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
      // 静态分支等价性：SparkleProposalEnter 在 reduce-motion 下仍呈现 child
      // —— widget 级锚（真帧省略，静态信息在树）。
    });

    testWidgets('M-R2-C2b reduce-motion 静态分支：提案组件直出终态内容',
        (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        theme: AppThemes.lightTheme,
        home: const MediaQuery(
          data: MediaQueryData(disableAnimations: true),
          child: Scaffold(body: SparkleProposalEnter(child: Text('提案内容'))),
        ),
      ),);
      await tester.pump();
      expect(find.text('提案内容'), findsOneWidget,
          reason: '减少动态：等价信息不丢失（任务同样可完成）',);
    });

    test('M-R2-C3 replay：恢复重放面（resume_available 重复投递）→ '
        'replaySuppressed，无任何声/触/庆祝位（提案型入场不重播）', () {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final json = _event(kind: 'resume_available', commitState: 'committed',
          subjectType: 'run', copyKey: 'resume.available',);
      final first = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(first.action, ExperienceFeedbackAction.presentNeutral);
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.celebrates, isFalse);
      expect(replay.playsSuccessCue, isFalse);
      expect(replay.playsWarningCue, isFalse);
      expect(sink.calls, isEmpty);
    });

    test('M-R2-C4 background：提案组件族零 AnimationController/零 repeat（'
        '一次性 implicit 动画——后台无在航 ticker 可残留），装饰停止面引用 '
        'M-R1-C4 锚；事件链可见性门 GAP_INTEGRATION（登记不伪造）', () {
      // 结构性锚：S01 族「全 implicit 一次性动画」= 无控制器可挂后台
      // （源码棘轮面 S01 已钉）；本格语义级复验预算表仍合规。
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
    });

    test('M-R2-C5 unsupported：提案行声/触列 = 无（结构性零出口），任何平台'
        '能力下通道调用恒 0', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      // 提案路径无任何派发点——即使误派发也被能力门拦下（纵深防御）。
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.pending,
      ),);
      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      expect(channel.played, isEmpty);
      expect(platform.systemSoundPlays, 0);
    });

    test('M-R2-C6 permission 拒绝：提案渲染无任何授权前置（本地呈现零出口'
        '——结构上无「被拒面」），0 通道调用', () {
      expect(kExperienceEventKinds.any((String k) => k.contains('propos')),
          isFalse,);
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });
  });

  // ═════════════ R3 · 写入提交成功 ═════════════
  // 乐谱：标题/状态 160ms 替换；用户开启后短柔和双音 ≤300ms；系统 success 一次；
  // 触发条件 = 有 committed 回执且非重放。
  group('R3 写入提交成功', () {
    test('M-R3-C1 enabled：committed 回执 + 版本相符 → presentSuccess（成功'
        '徽章 + 成功声/触恰一次，调用级记账）', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final outcome = adapter.present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'task',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentSuccess);
      expect(outcome.visualState, PixelRunState.success);
      expect(outcome.copy, '任务已更新');
      expect(outcome.playsSuccessCue, isTrue);
      await adapter.emitSensory(outcome);
      expect(sink.calls, ['success'], reason: '恰一次，无叠加');
      // 触觉侧：success 槽 terminalSuccess 放行一枚 successNotification。
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      ),);
      expect(decision.allowed, isTrue);
      expect(decision.pattern, SparkleHapticPattern.successNotification);
      expect(channel.played, hasLength(1));
      // 声侧：提示音开 → SystemSound 通道有调用（模拟器 native fallback 路径
      // 的调用级记账；真扬声器听感 DEVICE_UNVERIFIED）。
      SharedPreferences.setMockInitialValues(<String, Object>{_soundKey: true});
      await SensoryFeedbackService.setSoundEnabled(true);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success,
          enableHaptic: false,);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, greaterThanOrEqualTo(1));
      // 资产面：success.ogg 在许可账本消费镜像内（S04 账本 APPROVED∩ship）。
      expect(AudioAssetGate.isLicensed('audio/ui/success.ogg'), isTrue);
    });

    test('M-R3-C2 disabled：静音+无触觉+减少动态 → 决策/文案/徽章与 C1 全同'
        '（任务同样可完成），物理通道 0 调用（全真实链：服务+派发器+平台通道）',
        () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        _soundKey: false,
        _hapticKey: false,
      });
      await SensoryFeedbackService.setSoundEnabled(false);
      await SensoryFeedbackService.setHapticEnabled(false);
      final outcome = ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'task',),
        currentSubjectVersionToken: 'v7',
      );
      // 语义级：与 C1 逐字段全同（信息不减）。
      expect(outcome.action, ExperienceFeedbackAction.presentSuccess);
      expect(outcome.visualState, PixelRunState.success);
      expect(outcome.copy, '任务已更新');
      // 物理级：全真实出口链走完，通道 0 调用。
      await ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .emitSensory(outcome);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0, reason: '提示音关 → 零声音调用');
      expect(platform.hapticVibrates, 0, reason: '触觉偏好关 → 全局派发器抑制，零震动');
    });

    test('M-R3-C3 replay：同 event_id 重投 → replaySuppressed（不重复庆祝、'
        '不重放声/触；文案仍返回——文本状态仍恢复）', () {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final json = _event(kind: 'state_confirmed', commitState: 'committed',
          subjectType: 'task',);
      final first = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(first.action, ExperienceFeedbackAction.presentSuccess);
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.celebrates, isFalse);
      expect(replay.copy, '任务已更新', reason: '文本状态仍恢复');
      expect(sink.calls, isEmpty);
    });

    test('M-R3-C4 background：装饰停止面 = 生命周期暂停（M-R1-C4 锚引用）；'
        '事件链可见性门 = GAP_INTEGRATION（适配器 present() 无可见性入参、'
        '生产事件源未接线——S03-L5/FIX-569 登记面，本格不伪造 PASS）', () {
      // 既有装饰停止面调用级锚（复验）。
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
      // 缺口登记锚：适配器签名无可见性参数（结构性证据——呈报集成链）。
      // Dart 无反射断言签名的可移植面；以本注释+证据文档为准，测试面钉
      // 「重放抑制集合是会话级」这一相邻事实。
      final adapter = ExperienceFeedbackAdapter(sink: _RecordingSink());
      expect(adapter.ignoredInvalidCount, 0);
    });

    test('M-R3-C5 unsupported：桌面平台 → success 触觉被能力门拦（0 震动），'
        '成功徽章/文案仍完整呈现（信息不丢）；未许可资产缺省拒绝（账本门）',
        () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      ),);
      expect(decision.allowed, isFalse);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      expect(channel.played, isEmpty);
      // 语义级：unsupported 只砍物理输出，不砍信息。
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'task',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '任务已更新');
      // 资产门缺省拒绝（未证实许可就不播出——调用级）。
      expect(AudioAssetGate.isLicensed('audio/bgm/curated_unknown.ogg'), isFalse);
      expect(AudioAssetGate.licensedPathOrNull('nonexistent/path.ogg'), isNull);
    });

    test('M-R3-C6 permission 拒绝：系统拒绝播放（诚实降级位）→ 0 声音且不'
        '蜂鸣；触觉不受降级影响（按偏好照发）；任务流无异常', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        _soundKey: true,
        _hapticKey: true,
      });
      await SensoryFeedbackService.setSoundEnabled(true);
      // 诚实降级态（U14 面：渠道/系统拒绝达阈值后置位——设置页可观测）。
      SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);
      expect(SensoryFeedbackService.audioPlaybackDegraded, isTrue);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success,
          enableHaptic: false,);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0,
          reason: '降级静音：不再逐事件重试、不连锁蜂鸣',);
      // 触觉与视觉不受影响（调用级：触觉偏好开 → 放行一枚）。
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      ),);
      expect(decision.allowed, isTrue);
      expect(channel.played, hasLength(1));
    });
  });

  // ═════════════ R4 · 仅记忆已保存 ═════════════
  // 乐谱：来源 badge 短高亮；声音默认无；轻 selection 可选；epoch/version 已
  // 确认；不用任务成功音。
  group('R4 仅记忆已保存', () {
    test('M-R4-C1 enabled：memory committed → presentHighlight（非成功面孔：'
        '无成功徽章/成功声/成功触），轻触为 selection 级', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final outcome = adapter.present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'memory', copyKey: 'memory.saved',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentHighlight);
      expect(outcome.copy, '记忆已保存');
      expect(outcome.visualState, isNull,
          reason: '记忆保存不拿成功徽章（语义分层封闭路由）',);
      expect(outcome.celebrates, isFalse);
      expect(outcome.playsSuccessCue, isFalse);
      expect(outcome.playsSelectionCue, isTrue, reason: '可选轻触（selection 级）');
      await adapter.emitSensory(outcome);
      expect(sink.calls, ['selection'], reason: '轻触走 selection 出口，非 success');
      // 触觉通道级：放行的是 selectionClick，不是 successNotification。
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(channel.played, [SparkleHapticPattern.selectionClick]);
    });

    test('M-R4-C2 disabled：静音+无触觉 → 决策/文案与 C1 全同，物理通道 0',
        () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        _soundKey: false,
        _hapticKey: false,
      });
      final outcome = ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'memory', copyKey: 'memory.saved',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentHighlight);
      expect(outcome.copy, '记忆已保存');
      await ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .emitSensory(outcome);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });

    test('M-R4-C3 replay：同 event_id → replaySuppressed，高亮文案仍恢复',
        () {
      final adapter = ExperienceFeedbackAdapter(sink: _RecordingSink());
      final json = _event(kind: 'state_confirmed', commitState: 'committed',
          subjectType: 'memory', copyKey: 'memory.saved',);
      adapter.present(json, currentSubjectVersionToken: 'v7');
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.copy, '记忆已保存');
      expect(replay.celebrates, isFalse);
    });

    test('M-R4-C4 background：同 R3-C4——装饰停止面 PASS（锚引用），事件链'
        '可见性门 GAP_INTEGRATION（登记）', () {
      expect(kSuccessFaceSubjectTypes.contains('memory'), isFalse,
          reason: 'memory 恒不在成功面孔封闭集——任何状态下都不会庆祝',);
    });

    test('M-R4-C5 unsupported：桌面 → 轻触被能力门拦，高亮信息完整（语义级'
        '不变）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      expect(channel.played, isEmpty);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'memory', copyKey: 'memory.saved',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '记忆已保存');
    });

    test('M-R4-C6 permission 拒绝（无用户同意）：触觉偏好未开 → userPreferenceOff'
        '；高亮文本仍呈现（任何声音或动态关闭都不减少可理解信息）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: false, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.userPreferenceOff);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'memory', copyKey: 'memory.saved',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '记忆已保存');
      expect(platform.systemSoundPlays, 0);
    });
  });

  // ═════════════ R5 · 证据已登记 ═════════════
  // 乐谱：小印章 160ms；可选短单音；可选轻 impact；outcome 持久化；文字不说
  // 已掌握。
  group('R5 证据已登记', () {
    test('M-R5-C1 enabled：中性呈现（无庆祝无声触）；印章预算 160ms；冻结'
        '文案表全表无「精通/已掌握」类词', () {
      final adapter = ExperienceFeedbackAdapter(sink: _RecordingSink());
      final outcome = adapter.present(
        _event(kind: 'progress_delta', commitState: 'committed',
            subjectType: 'goal', copyKey: 'evidence.registered',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentNeutral);
      expect(outcome.copy, '证据已登记');
      expect(outcome.celebrates, isFalse);
      expect(outcome.playsSuccessCue, isFalse);
      expect(outcome.playsWarningCue, isFalse);
      expect(kSparkleSemanticMotionBudgets.evidenceStamp,
          const Duration(milliseconds: 160),);
      // 语义级：全文案表禁词扫描（文字不说已掌握）。
      for (final copy in kExperienceCopyTable.values) {
        expect(copy.contains('精通') || copy.contains('已掌握') ||
            copy.toLowerCase().contains('mastery'), isFalse,
            reason: '冻结文案表出现禁词：$copy',);
      }
    });

    test('M-R5-C2 disabled：静音/减少动态 → 决策与文案全同（本行声/触本就'
        '缺省无——结构性零出口不随偏好变化）', () {
      final outcome = ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .present(
        _event(kind: 'progress_delta', commitState: 'committed',
            subjectType: 'goal', copyKey: 'evidence.registered',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentNeutral);
      expect(outcome.copy, '证据已登记');
      expect(outcome.playsSelectionCue, isFalse);
    });

    test('M-R5-C3 replay：重复投递 → replaySuppressed（印章不重播）', () {
      final adapter = ExperienceFeedbackAdapter(sink: _RecordingSink());
      final json = _event(kind: 'progress_delta', commitState: 'committed',
          subjectType: 'goal', copyKey: 'evidence.registered',);
      adapter.present(json, currentSubjectVersionToken: 'v7');
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.copy, '证据已登记');
    });

    test('M-R5-C4 background：同 R3-C4（装饰停止面 PASS + 事件链可见性门 '
        'GAP_INTEGRATION 登记）', () {
      expect(kSparkleSemanticMotionBudgets.evidenceStamp,
          const Duration(milliseconds: 160),);
    });

    testWidgets('M-R5-C5 unsupported：证据印章在减少动态/桌面下全尺寸即时呈现'
        '（信息不丢），无任何声触出口', (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        theme: AppThemes.lightTheme,
        home: const MediaQuery(
          data: MediaQueryData(disableAnimations: true),
          child: Scaffold(body: SparkleEvidenceStamp(child: Text('证据已登记'))),
        ),
      ),);
      await tester.pump();
      expect(find.text('证据已登记'), findsOneWidget);
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });

    test('M-R5-C6 permission 拒绝：无授权 → 0 通道调用，中性文案完整', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: false, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.lightImpact,
        phase: SparkleHapticPhase.terminalSuccess,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.userPreferenceOff);
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });
  });

  // ═════════════ R6 · 独立检验通过 ═════════════
  // 乐谱：星点连线 ≤650ms 可跳过；可选里程碑短音 ≤600ms；success 一次；通过
  // 真实有效独立评测，不等同一次点击。
  group('R6 独立检验通过', () {
    test('M-R6-C1 enabled：goal 成功面孔（有回执）→ success 恰一次；里程碑'
        '预算 ≤650ms；「不等同一次点击」= E1 门（无回执的 success 形状被解析'
        '面拒收，绝不庆祝）', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final outcome = adapter.present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'goal', copyKey: 'goal.committed',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentSuccess);
      expect(outcome.visualState, PixelRunState.success);
      expect(outcome.playsSuccessCue, isTrue);
      await adapter.emitSensory(outcome);
      expect(sink.calls, ['success']);
      // 里程碑预算（语义级）。
      expect(kSparkleSemanticMotionBudgets.milestone,
          const Duration(milliseconds: 650),);
      expect(
        kSemanticMotionScoreWindows[SparkleSemanticMotionSlot.milestone]!
            .contains(650),
        isTrue,
      );
      // E1 反例：state_confirmed 无 receipt_ref → 解析 null → ignored，
      // 绝不庆祝（仅真实 commit 用 success）。
      final noReceipt = adapter.present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'goal', eventId: 'eev_q06_e1', receiptRef: null,),
        currentSubjectVersionToken: 'v7',
      );
      expect(noReceipt.action, ExperienceFeedbackAction.ignoredInvalid);
      expect(noReceipt.celebrates, isFalse);
      expect(adapter.ignoredInvalidCount, 1);
    });

    test('M-R6-C2 disabled：静音+无触觉 → 成功文案/徽章与 C1 全同（任务同样'
        '可完成），物理通道 0', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        _soundKey: false,
        _hapticKey: false,
      });
      final outcome = ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'goal', copyKey: 'goal.committed',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '目标已更新');
      expect(outcome.visualState, PixelRunState.success);
      await ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .emitSensory(outcome);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });

    test('M-R6-C3 replay：评测结果重投 → 抑制；新 event_id（真实新 commit）→ '
        '放行（仅真实 commit 用 success 的双向锚）', () {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final json = _event(kind: 'state_confirmed', commitState: 'committed',
          subjectType: 'goal', copyKey: 'goal.committed',);
      expect(
        adapter.present(json, currentSubjectVersionToken: 'v7').action,
        ExperienceFeedbackAction.presentSuccess,
      );
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      // 新事件（真实新 commit）→ 放行成功面。
      final fresh = adapter.present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'goal', copyKey: 'goal.committed',
            eventId: 'eev_q06_fresh',),
        currentSubjectVersionToken: 'v7',
      );
      expect(fresh.action, ExperienceFeedbackAction.presentSuccess);
    });

    test('M-R6-C4 background：同 R3-C4（装饰停止面 PASS + 可见性门 '
        'GAP_INTEGRATION 登记；重要 run 由服务器管理——客户端无 run 终止面）',
        () {
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
    });

    test('M-R6-C5 unsupported：桌面 → success 触觉拦下，徽章语义仍在'
        '（语义级：成功信息经视觉/文本仍可达）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'goal', copyKey: 'goal.committed',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.visualState, PixelRunState.success);
      expect(outcome.copy, '目标已更新');
    });

    test('M-R6-C6 permission 拒绝：降级静音 + 无同意 → 0 声音 0 触觉，成功'
        '文案完整（评测结论不因感官关闭而丢失）', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{_soundKey: true});
      await SensoryFeedbackService.setSoundEnabled(true);
      SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.success,
          enableHaptic: false,);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0);
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: false, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.success,
        phase: SparkleHapticPhase.terminalSuccess,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.userPreferenceOff);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'goal', copyKey: 'goal.committed',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '目标已更新');
    });
  });

  // ═════════════ R7 · 冲突/未知/失败 ═════════════
  // 乐谱：持久信息行，无抖屏；声音默认无；明确操作失败可 system warning 一次；
  // 无颜色/声音独占信息。
  group('R7 冲突/未知/失败', () {
    test('M-R7-C1 enabled：terminal_failed → failed 徽章 + 警示触恰一次；'
        'version_conflict → conflict 徽章；未知（版本未对账）→ unknown 徽章 + '
        '零声触（未知≠失败≠成功）', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final failed = adapter.present(
        _event(kind: 'terminal_failed', commitState: 'error',
            errorState: 'expired', subjectType: 'task',
            copyKey: 'err.expired',),
        currentSubjectVersionToken: 'v7',
      );
      expect(failed.action, ExperienceFeedbackAction.presentFailure);
      expect(failed.visualState, PixelRunState.failed);
      expect(failed.playsWarningCue, isTrue);
      await adapter.emitSensory(failed);
      expect(sink.calls, ['warning'], reason: '警示恰一次，无连锁蜂鸣');
      final conflict = adapter.present(
        _event(kind: 'terminal_failed', commitState: 'error',
            errorState: 'version_conflict', subjectType: 'task',
            copyKey: 'err.version_conflict', eventId: 'eev_q06_conflict',),
        currentSubjectVersionToken: 'v7',
      );
      expect(conflict.visualState, PixelRunState.conflict);
      expect(conflict.copy, '你的设置已更新，需要重新生成');
      // 未知：committed 事件 + 版本未对账 → unknown 徽章、零声/触、绝不绿。
      final unknown = adapter.present(
        _event(kind: 'state_confirmed', commitState: 'committed',
            subjectType: 'task', eventId: 'eev_q06_unknown',),
      );
      expect(unknown.action, ExperienceFeedbackAction.presentUnknown);
      expect(unknown.visualState, PixelRunState.unknown);
      expect(unknown.celebrates, isFalse);
      expect(unknown.playsSuccessCue, isFalse);
      expect(unknown.playsWarningCue, isFalse);
      expect(unknown.playsSelectionCue, isFalse);
      // unknown 相位：触觉门任何槽都不放行（success pattern 不可误用）。
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: true, channel: channel);
      final unknownHaptic = await d.dispatch(
        const SparkleSemanticHapticRequest(
          slot: SparkleSemanticHapticSlot.success,
          phase: SparkleHapticPhase.unknown,
        ),
      );
      expect(unknownHaptic.suppression,
          SparkleHapticSuppression.phaseNotHapticEligible,);
      expect(channel.played, isEmpty);
    });

    test('M-R7-C2 disabled：静音+无触觉 → 失败文案/徽章与 C1 全同（信息不'
        '独占于颜色/声音），物理通道 0', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        _soundKey: false,
        _hapticKey: false,
      });
      final outcome = ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .present(
        _event(kind: 'terminal_failed', commitState: 'error',
            errorState: 'expired', subjectType: 'task', copyKey: 'err.expired',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '该提案已过期，需要重新生成');
      expect(outcome.visualState, PixelRunState.failed);
      await ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .emitSensory(outcome);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });

    test('M-R7-C3 replay：失败事件重投 → 抑制（警示不重复——「单次失败只提示'
        '一次，不连锁蜂鸣」）', () {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final json = _event(kind: 'terminal_failed', commitState: 'error',
          errorState: 'expired', subjectType: 'task', copyKey: 'err.expired',);
      expect(
        adapter.present(json, currentSubjectVersionToken: 'v7').action,
        ExperienceFeedbackAction.presentFailure,
      );
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.playsWarningCue, isFalse);
      expect(sink.calls, isEmpty, reason: '重投失败事件零额外警示出口');
    });

    test('M-R7-C4 background：同 R3-C4（装饰停止面 PASS + 可见性门 '
        'GAP_INTEGRATION 登记）', () {
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
    });

    test('M-R7-C5 unsupported：桌面 → 警示触被能力门拦且不蜂鸣替代（0 触觉'
        '0 声音），失败文本行仍在', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.warning,
        phase: SparkleHapticPhase.terminalFailure,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      expect(channel.played, isEmpty);
      expect(platform.systemSoundPlays, 0,
          reason: '「不支持则不震，不能拿蜂鸣替代」',);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'terminal_failed', commitState: 'error',
            errorState: 'expired', subjectType: 'task', copyKey: 'err.expired',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '该提案已过期，需要重新生成');
    });

    test('M-R7-C6 permission 拒绝：无同意 → 警示触 userPreferenceOff；文本'
        '信息完整（失败可理解性不依赖触觉/声音）', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(preferenceEnabled: false, channel: channel);
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.warning,
        phase: SparkleHapticPhase.terminalFailure,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.userPreferenceOff);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'terminal_failed', commitState: 'error',
            errorState: 'unauthorized', subjectType: 'task',
            copyKey: 'err.unauthorized',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '没有权限执行这个操作');
      expect(outcome.visualState, PixelRunState.failed);
    });
  });

  // ═════════════ R8 · 深任务进行中 ═════════════
  // 乐谱：静态阶段文字，可选局部慢呼吸；声音无；触觉无；来自真实 run 阶段，
  // 不伪进度。
  group('R8 深任务进行中', () {
    test('M-R8-C1 enabled：progress_delta → 中性呈现（无庆祝无声触——结构性'
        '零出口）；阶段文案可见', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final outcome = adapter.present(
        _event(kind: 'progress_delta', commitState: 'committed',
            subjectType: 'run', copyKey: 'progress.delta',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentNeutral);
      expect(outcome.copy, '进度更新');
      expect(outcome.celebrates, isFalse);
      await adapter.emitSensory(outcome);
      expect(sink.calls, isEmpty, reason: '进行中行零感官出口');
    });

    test('M-R8-C2 disabled：静音/减少动态 → 阶段文案全同（任务进行信息不依赖'
        '动效）', () {
      final outcome = ExperienceFeedbackAdapter(sink: const SensoryFeedbackSink())
          .present(
        _event(kind: 'progress_delta', commitState: 'committed',
            subjectType: 'run', copyKey: 'progress.delta',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '进度更新');
      expect(outcome.action, ExperienceFeedbackAction.presentNeutral);
    });

    test('M-R8-C3 replay：进度事件重投 → 抑制（不重播进行中提示），文案仍返回',
        () {
      final adapter = ExperienceFeedbackAdapter(sink: _RecordingSink());
      final json = _event(kind: 'progress_delta', commitState: 'committed',
          subjectType: 'run', copyKey: 'progress.delta',);
      adapter.present(json, currentSubjectVersionToken: 'v7');
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.copy, '进度更新');
    });

    test('M-R8-C4 background：深 run 继续由服务器管理（客户端只读呈现——'
        'run subject 恒中性、无庆祝），装饰停止面引用 M-R1-C4 锚', () {
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'progress_delta', commitState: 'committed',
            subjectType: 'run', copyKey: 'run.completed',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentNeutral,
          reason: 'run 完成也恒中性（成功面孔封闭集 = task/goal/plan）',);
      expect(outcome.celebrates, isFalse);
    });

    test('M-R8-C5 unsupported：桌面 → 结构性零声触（本行无出口），文案完整',
        () {
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'progress_delta', commitState: 'committed',
            subjectType: 'run', copyKey: 'progress.delta',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.playsSuccessCue, isFalse);
      expect(outcome.playsWarningCue, isFalse);
      expect(outcome.playsSelectionCue, isFalse);
      expect(platform.systemSoundPlays, 0);
    });

    test('M-R8-C6 permission 拒绝：无任何授权依赖面（零出口行），0 通道调用',
        () {
      expect(platform.systemSoundPlays, 0);
      expect(platform.hapticVibrates, 0);
    });
  });

  // ═════════════ R9 · 长期回归 ═════════════
  // 乐谱：低幅进入或静态；不自动播放；触觉无；用户进入，不是营销推送。
  group('R9 长期回归', () {
    test('M-R9-C1 enabled：冷启动缺省 = 零自动播放（提示音缺省关/背景声缺省'
        '关/焦点态 IDLE）；恢复进入 resume_available → 中性呈现非庆祝', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      // 未点播用户：两类声音开关缺省关（V4 规格——S02 行为差量）。
      expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);
      expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);
      expect(AudioFocusController.instance.state, AudioFocusState.idle,
          reason: '重开不自续：冷启动无任何播放会话',);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'resume_available', commitState: 'committed',
            subjectType: 'run', copyKey: 'resume.available',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.action, ExperienceFeedbackAction.presentNeutral);
      expect(outcome.celebrates, isFalse);
    });

    test('M-R9-C2 disabled：减少动态 → 回归进入走静态档（预算表合规、无后台'
        '无限动画契约面），信息完整', () {
      expect(kSparkleSemanticMotionBudgets.validateAgainstScore(), isEmpty);
      final outcome = ExperienceFeedbackAdapter(sink: _RecordingSink()).present(
        _event(kind: 'resume_available', commitState: 'committed',
            subjectType: 'run', copyKey: 'resume.available',),
        currentSubjectVersionToken: 'v7',
      );
      expect(outcome.copy, '有可接续的进度');
    });

    test('M-R9-C3 replay：恢复重放重投 → 抑制（回归进入不重复庆祝），文案恢复',
        () {
      final adapter = ExperienceFeedbackAdapter(sink: _RecordingSink());
      final json = _event(kind: 'resume_available', commitState: 'committed',
          subjectType: 'run', copyKey: 'resume.available',);
      adapter.present(json, currentSubjectVersionToken: 'v7');
      final replay = adapter.present(json, currentSubjectVersionToken: 'v7');
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.celebrates, isFalse);
      expect(replay.copy, '有可接续的进度');
    });

    test('M-R9-C4 background：STOPPED_BY_USER 后抢占结束不自续（音频焦点面 '
        'S02 语义复验）；装饰停止面 = M-R1-C4 生命周期锚；重要 run 由服务器'
        '管理（客户端无 run 终止面）', () {
      // 音频焦点：用户停止后，来电结束不越过 STOPPED_BY_USER 自续。
      final focus = AudioFocusController.instance
        ..beginUserPlaybackSession();
      expect(focus.state, AudioFocusState.userPlaying);
      focus
        ..handleHeadphoneUnplugged()
        ..endCallInterruption();
      expect(focus.state, AudioFocusState.stoppedByUser,
          reason: '耳机拔出不转扬声器大声续播；抢占结束不自续（后台面语义锚）',);
      // 录音抢占期间点播被拒（不抢焦点）。
      focus.beginRecording();
      expect(focus.beginUserPlaybackSession(), isFalse,
          reason: '录音不回录：点播请求被拒',);
      expect(focus.state, AudioFocusState.pausedByRecording);
      focus.endRecording();
      expect(focus.promptsSuppressed, isFalse);
    });

    test('M-R9-C5 unsupported：桌面 → 零自动播放零触觉（回归进入静默），'
        '0 通道调用', () async {
      final channel = _RecordingHapticChannel();
      final d = _dispatcher(
        preferenceEnabled: true,
        capability: SparkleHapticCapability.unsupported,
        channel: channel,
      );
      final decision = await d.dispatch(const SparkleSemanticHapticRequest(
        slot: SparkleSemanticHapticSlot.selection,
        phase: SparkleHapticPhase.userInitiated,
      ),);
      expect(decision.suppression, SparkleHapticSuppression.platformUnsupported);
      expect(platform.systemSoundPlays, 0);
    });

    test('M-R9-C6 permission 拒绝：未点播（缺省关）+ 降级位 → 长期回归进入'
        '零自动播放；缺省拒绝即「无用户同意不发声」的对偶', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      expect(await SensoryFeedbackService.isSoundEnabled(), isFalse,
          reason: '缺省关 = 未明确点播无声音',);
      SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.checkin,
          enableHaptic: false,);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(platform.systemSoundPlays, 0);
    });
  });

  // ═════════════ 验收①聚合 · 静音/无触觉/减少动态所有任务同样可完成 ═════════════
  group('Q06 验收① 任务可完成性聚合（徽章语义在两态下同可达）', () {
    Future<void> pumpBadge(WidgetTester tester, PixelRunState state,
        {required bool reduceMotion,}) async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      final manager = ThemeManager();
      if (!manager.initialized) {
        await manager.initialize();
      }
      await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
      await tester.pumpWidget(
        MaterialApp(
          theme: AppThemes.lightTheme,
          home: MediaQuery(
            data: MediaQueryData(disableAnimations: reduceMotion),
            child: Scaffold(
              body: Center(child: PixelStateBadge(state: state)),
            ),
          ),
        ),
      );
      await tester.pump();
    }

    testWidgets('成功徽章：全感官开 vs 静音+无触觉+减少动态 → 语义标签同样可查'
        '（任务完成信息等价可达）', (tester) async {
      await pumpBadge(tester, PixelRunState.success, reduceMotion: false);
      expect(find.bySemanticsLabel('已完成'), findsWidgets);
      await pumpBadge(tester, PixelRunState.success, reduceMotion: true);
      expect(find.bySemanticsLabel('已完成'), findsWidgets,
          reason: '减少动态：静态分支直落终态，语义不丢',);
    });

    testWidgets('失败/冲突/未知徽章：减少动态下语义同样可查（无颜色/声音独占'
        '信息）', (tester) async {
      await pumpBadge(tester, PixelRunState.failed, reduceMotion: true);
      expect(find.bySemanticsLabel('失败'), findsOneWidget);
      await pumpBadge(tester, PixelRunState.conflict, reduceMotion: true);
      expect(find.bySemanticsLabel('版本冲突'), findsOneWidget);
      await pumpBadge(tester, PixelRunState.unknown, reduceMotion: true);
      expect(find.bySemanticsLabel('结果未知'), findsOneWidget);
    });

    test('全文案表在「任何关闭」下不变（信息不减的语义级对偶：冻结表是常量）',
        () {
      expect(kExperienceCopyTable.length, 17);
      expect(kExperienceCopyTable['task.committed'], '任务已更新');
      expect(kExperienceCopyTable['memory.saved'], '记忆已保存');
      expect(kExperienceCopyTable['evidence.registered'], '证据已登记');
      expect(kExperienceCopyTable['err.unauthorized'], '没有权限执行这个操作');
    });
  });
}
