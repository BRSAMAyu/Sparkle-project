import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/data/episode_resume_models.dart';

/// V4-U01 · `episode_resume_view.v1` 移动端消费投影单元测试。
///
/// 每面一正一反（全部可失败）：
/// - 解析正/反（版本门 fail-closed、必需键缺失、未知键容忍、子结构字段级降级）；
/// - 过期判定正/反（新鲜 → null；过期/压线 → `expires_at_passed`）。
Map<String, dynamic> _fullView({
  String schemaVersion = kEpisodeResumeViewSchemaVersion,
  Object? expiresAt,
  Object? freshness = _sentinel,
  Object? lastStep,
  Object? pendingStep,
  Object? outcome,
  Object? whyNow,
}) {
  final expires = expiresAt ?? '2026-09-28T12:30:00';
  return {
    'schema_version': schemaVersion,
    'goal_ref': 'goal://g1',
    'task_ref': 'task://t1',
    'run_ref': 'run://r1',
    'last_valid_outcome':
        outcome ?? {'outcome_ref': 'outcome://o1', 'truth_class': 'actual', 'recorded_at': '2026-09-28T10:00:00'},
    'last_confirmed_step': lastStep ??
        {
          'step_ref': 'subtask://s1',
          'description': '读完第三章前两节',
          'confirmed_at': '2026-09-28T10:05:00',
          'version_token': 'tok-1',
        },
    'pending_human_step': pendingStep ??
        {
          'description': '做第三章末尾的三道练习题',
          'cognitive_ownership': 'user_led',
          'execution_mode': 'assisted',
        },
    'why_now': whyNow,
    'expires_at': expires,
    'freshness': freshness == _sentinel
        ? {
            'context_receipt_ref': 'context_selection://csr_TEST',
            'computed_at': '2026-09-28T12:00:00',
            'memory_epoch_at_compute': 7,
          }
        : freshness,
    // B05 §8 双读纪律：未知键容忍（消费方不依赖冻结集之外的字段）。
    'unknown_future_field': {'nested': true},
  };
}

/// 区分「未提供」与显式 null 的哨兵（显式 null = 缺键反例）。
const Object _sentinel = _Sentinel();

class _Sentinel {
  const _Sentinel();
}

void main() {
  group('EpisodeResumeViewData.tryParse 解析面', () {
    test('正：完整合法视图 → 全字段投影（步骤/待办/结果/新鲜度）', () {
      final view = EpisodeResumeViewData.tryParse(_fullView());

      expect(view, isNotNull);
      expect(view!.goalRef, 'goal://g1');
      expect(view.taskRef, 'task://t1');
      expect(view.taskId, 't1');
      expect(view.runRef, 'run://r1');
      expect(view.lastConfirmedStep?.description, '读完第三章前两节');
      expect(view.lastConfirmedStep?.stepRef, 'subtask://s1');
      expect(view.lastConfirmedStep?.versionToken, 'tok-1');
      expect(view.pendingHumanStep?.description, '做第三章末尾的三道练习题');
      expect(view.lastOutcome?.truthClass, 'actual');
      expect(view.contextReceiptRef, 'context_selection://csr_TEST');
      expect(view.memoryEpochAtCompute, 7);
      expect(view.expiresAt, DateTime.parse('2026-09-28T12:30:00'));
    });

    test('反：schema_version 非当前版本 → null（版本门 fail-closed）', () {
      final view = EpisodeResumeViewData.tryParse(
        _fullView(schemaVersion: 'episode_resume_view.v2'),
      );

      expect(view, isNull);
    });

    test('反：缺 expires_at / freshness 非对象 / ref scheme 越界 → null', () {
      final noExpiry = _fullView()..remove('expires_at');
      expect(EpisodeResumeViewData.tryParse(noExpiry), isNull);

      final noFreshness = _fullView(freshness: null);
      expect(EpisodeResumeViewData.tryParse(noFreshness), isNull);

      final badScheme = _fullView(
        freshness: {
          'context_receipt_ref': 'other_scheme://csr_TEST',
          'computed_at': '2026-09-28T12:00:00',
          'memory_epoch_at_compute': 7,
        },
      );
      expect(EpisodeResumeViewData.tryParse(badScheme), isNull);
    });

    test('子结构词表越界 → 字段级降级不连坐（truth_class/step scheme/pending 空描述）', () {
      final badOutcome = EpisodeResumeViewData.tryParse(
        _fullView(outcome: {'outcome_ref': 'outcome://o1', 'truth_class': 'fabricated'}),
      );
      expect(badOutcome, isNotNull);
      expect(badOutcome!.lastOutcome, isNull);
      expect(badOutcome.lastConfirmedStep, isNotNull);

      final badStep = EpisodeResumeViewData.tryParse(
        _fullView(lastStep: {'step_ref': 'unknown://s9', 'description': 'x'}),
      );
      expect(badStep, isNotNull);
      expect(badStep!.lastConfirmedStep, isNull);

      final emptyPending = EpisodeResumeViewData.tryParse(
        _fullView(pendingStep: {'description': ''}),
      );
      expect(emptyPending, isNotNull);
      expect(emptyPending!.pendingHumanStep, isNull);
    });
  });

  group('episodeResumeStaleReason 过期判定（backend resume_view_stale_reason 客户端子集）', () {
    test('正：expires_at 之前 → null（仍新鲜）', () {
      final view = EpisodeResumeViewData.tryParse(_fullView())!;

      expect(
        episodeResumeStaleReason(view, now: DateTime.parse('2026-09-28T12:29:59')),
        isNull,
      );
    });

    test('反：expires_at 当刻/之后 → expires_at_passed（过期只许说明，不接续）', () {
      final view = EpisodeResumeViewData.tryParse(_fullView())!;

      expect(
        episodeResumeStaleReason(view, now: DateTime.parse('2026-09-28T12:30:00')),
        'expires_at_passed',
      );
      expect(
        episodeResumeStaleReason(view, now: DateTime.parse('2026-09-28T13:00:00')),
        'expires_at_passed',
      );
    });
  });
}
