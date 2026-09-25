import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_stage_stabilizer.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_run_phase_indicator.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  Object classOf(String? status) =>
      resolveChatRunStage(ChatRunPhase.sending, status);

  group('AiStageStabilizer 单元（E-03 UI 去抖 ≥300ms 稳定窗）', () {
    test('首个状态立即提交——首反馈不被去抖拖延', () {
      final commits = <String?>[];
      final s = AiStageStabilizer(classify: classOf);
      final applied = s.offer('THINKING', apply: () => commits.add('THINKING'));
      expect(applied, isTrue, reason: '首个状态必须立即生效');
      expect(commits, ['THINKING']);
      s.dispose();
    });

    test('同类状态立即提交（细节刷新不闪段）', () {
      final commits = <String?>[];
      final s = AiStageStabilizer(classify: classOf)
        ..offer('THINKING', apply: () => commits.add('THINKING'));
      final applied = s.offer('REVIEWING', apply: () => commits.add('REVIEWING'));
      expect(applied, isTrue);
      expect(commits, ['THINKING', 'REVIEWING']);
      s.dispose();
    });

    testWidgets('跨类切换需 300ms 稳定窗，窗口内回摆被吞（不闪段）', (tester) async {
      final commits = <String?>[];
      final s = AiStageStabilizer(classify: classOf)
        ..offer('THINKING', apply: () => commits.add('THINKING'));
      final applied = s.offer('SEARCHING', apply: () => commits.add('SEARCHING'));
      expect(
        applied,
        isFalse,
        reason: '跨类状态进入稳定窗，不立即提交',
      );
      await tester.pump(const Duration(milliseconds: 100));
      expect(commits, ['THINKING'], reason: '窗口内不得提交跨类状态');

      s.offer('THINKING', apply: () => commits.add('THINKING(回摆)'));
      await tester.pump(const Duration(milliseconds: 400));
      expect(commits, ['THINKING'], reason: '回摆后 SEARCHING 永不被提交');
      s.dispose();
    });

    testWidgets('跨类状态稳定满 300ms 后提交', (tester) async {
      final commits = <String?>[];
      final s = AiStageStabilizer(classify: classOf)
        ..offer('THINKING', apply: () => commits.add('THINKING'))
        ..offer('EXECUTING_TOOL', apply: () => commits.add('EXECUTING_TOOL'));
      await tester.pump(const Duration(milliseconds: 299));
      expect(commits, ['THINKING']);
      await tester.pump(const Duration(milliseconds: 2));
      expect(commits, ['THINKING', 'EXECUTING_TOOL'], reason: '稳定满 300ms 才提交');
      s.dispose();
    });

    testWidgets('终端冲刷：clear 立即取消待提交并复位', (tester) async {
      final commits = <String?>[];
      final s = AiStageStabilizer(classify: classOf)
        ..offer('THINKING', apply: () => commits.add('THINKING'))
        ..offer('SEARCHING', apply: () => commits.add('SEARCHING'))
        ..clear();
      await tester.pump(const Duration(milliseconds: 400));
      expect(commits, ['THINKING'], reason: 'clear 后不得再提交待决状态');
      // clear 后新一轮首个状态又立即生效
      s.offer('GENERATING', apply: () => commits.add('GENERATING'));
      expect(commits, ['THINKING', 'GENERATING']);
      s.dispose();
    });

    testWidgets('同一待决类持续到来保持原稳定窗起点（chatter 不永久扣留）', (tester) async {
      final commits = <String?>[];
      final s = AiStageStabilizer(classify: classOf)
        ..offer('THINKING', apply: () => commits.add('THINKING'))
        ..offer('SEARCHING', apply: () => commits.add('SEARCHING'));
      await tester.pump(const Duration(milliseconds: 200));
      // 同类（retrieve 段）的另一个状态到来——不重置窗口
      s.offer('EXECUTING_TOOL', apply: () => commits.add('EXECUTING_TOOL'));
      await tester.pump(const Duration(milliseconds: 150));
      expect(
        commits,
        ['THINKING', 'EXECUTING_TOOL'],
        reason: '原窗口期满应提交最新待决状态（EXECUTING_TOOL）',
      );
      s.dispose();
    });
  });

  group('ChatRunPhaseIndicator × AiStageStabilizer 真实渲染（防闪烁 widget 证明）', () {
    testWidgets('THINKING→SEARCHING→THINKING 快速回摆：检索段永不点亮', (tester) async {
      late _StabilizerHostState host;
      String? committed;

      // 与 provider 相同的接线：aiStatus 只吃稳定器提交值。
      await tester.pumpWidget(
        _StabilizerHost(onHostReady: (h) => host = h, onCommitted: (v) => committed = v),
      );
      await tester.pump();

      // 初始：sending + 无状态 → 检索段
      expect(find.bySemanticsLabel('正在检索资料，可取消'), findsOneWidget);

      // THINKING 立即提交 → 思考段
      host.offerStatus('THINKING');
      await tester.pump();
      expect(find.bySemanticsLabel('正在思考中，可取消'), findsOneWidget);

      // 100ms 后 SEARCHING（跨类，进入稳定窗）
      await tester.pump(const Duration(milliseconds: 100));
      host.offerStatus('SEARCHING');
      await tester.pump();
      expect(
        find.bySemanticsLabel('正在思考中，可取消'),
        findsOneWidget,
        reason: '稳定窗内不得切换到检索段',
      );

      // 再 100ms 后回摆 THINKING：SEARCHING 被吞
      await tester.pump(const Duration(milliseconds: 100));
      host.offerStatus('THINKING');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      // 全程检索段从未点亮
      expect(
        find.bySemanticsLabel('正在检索资料，可取消'),
        findsNothing,
        reason: '快速回摆不得造成段落闪烁',
      );
      expect(find.bySemanticsLabel('正在思考中，可取消'), findsOneWidget);
      expect(committed, 'THINKING');
    });

    testWidgets('真实阶段推进（稳定 300ms+）正常切换到检索段', (tester) async {
      late _StabilizerHostState host;
      await tester.pumpWidget(
        _StabilizerHost(onHostReady: (h) => host = h, onCommitted: (_) {}),
      );
      await tester.pump();

      host.offerStatus('THINKING');
      await tester.pump();
      expect(find.bySemanticsLabel('正在思考中，可取消'), findsOneWidget);

      // 真实检索开始并保持稳定
      await tester.pump(const Duration(milliseconds: 350));
      host.offerStatus('SEARCHING');
      await tester.pump();
      expect(
        find.bySemanticsLabel('正在思考中，可取消'),
        findsOneWidget,
        reason: '提交前仍在稳定窗',
      );
      await tester.pump(const Duration(milliseconds: 350));
      expect(
        find.bySemanticsLabel('正在检索资料，可取消'),
        findsOneWidget,
        reason: '稳定满窗后真实阶段必须可见——去抖不得吞掉真实推进',
      );
    });
  });
}

/// 模拟 provider 接线的宿主：aiStatus 只吃稳定器提交值
/// （offer 的 apply 在提交时 setState，被吞的事件不触发任何渲染）。
class _StabilizerHost extends StatefulWidget {
  const _StabilizerHost({
    required this.onHostReady,
    required this.onCommitted,
  });

  final void Function(_StabilizerHostState) onHostReady;
  final ValueChanged<String?> onCommitted;

  @override
  State<_StabilizerHost> createState() => _StabilizerHostState();
}

class _StabilizerHostState extends State<_StabilizerHost> {
  late final AiStageStabilizer _stabilizer;
  String? _aiStatus;

  @override
  void initState() {
    super.initState();
    _stabilizer = AiStageStabilizer(
      classify: (status) => resolveChatRunStage(ChatRunPhase.sending, status),
    );
    widget.onHostReady(this);
  }

  @override
  void dispose() {
    _stabilizer.dispose();
    super.dispose();
  }

  void offerStatus(String status) {
    _stabilizer.offer(
      status,
      apply: () {
        widget.onCommitted(status);
        setState(() => _aiStatus = status);
      },
    );
  }

  @override
  Widget build(BuildContext context) => ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: Center(
              child: ChatRunPhaseIndicator(
                phase: ChatRunPhase.sending,
                aiStatus: _aiStatus,
                onCancel: () {},
              ),
            ),
          ),
        ),
      );
}
