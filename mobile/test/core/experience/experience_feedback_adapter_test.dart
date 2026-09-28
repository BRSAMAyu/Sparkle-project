// V4-F03 · 统一反馈呈现适配器单测（每验收面一正一反 + 去重/version/语义分层）。
//
// 契约：B05 §3（experience_event.v1）+ MOTION_AUDIO_HAPTICS 核心合同
// （缺回执不发成功事件；恢复重放不重复音/震；文本状态仍恢复）。
// 感官出口注入记录器（无插件依赖）；视觉状态断言走 PixelRunState。
import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/experience/experience_event.dart';
import 'package:sparkle/core/experience/experience_feedback_adapter.dart';

/// 记录型感官出口（适配器声/触决策的可观测替身）。
class _RecordingSink implements ExperienceSensorySink {
  final List<String> calls = <String>[];

  @override
  Future<void> success() async => calls.add('success');

  @override
  Future<void> selection() async => calls.add('selection');

  @override
  Future<void> warning() async => calls.add('warning');
}

const String _schema = kExperienceEventSchemaVersion;

Map<String, dynamic> _committedTaskEvent({
  String eventId = 'eev_task_001',
  String versionToken = 'v7',
  String copyKey = 'task.committed',
}) => <String, dynamic>{
      'schema_version': _schema,
      'event_id': eventId,
      'kind': 'state_confirmed',
      'receipt_ref': 'action_command://11111111-1111-1111-1111-111111111111',
      'commit_state': 'committed',
      'error_state': null,
      'subject': <String, dynamic>{'type': 'task', 'id': 'task-1', 'version_token': versionToken},
      'presentation': <String, dynamic>{
        'modalities': <String>['visual', 'audio', 'haptic'],
        'copy_key': copyKey,
      },
      'dedupe_key': 'd-$eventId',
      'issued_at': '2026-09-28T00:00:00',
      'expires_at': null,
    };

void main() {
  group('解析面（fail-safe：违规形状永不成事件）', () {
    test('(正) 合法 committed 事件解析成功且身份完整', () {
      final event = ExperienceEventModel.tryParse(_committedTaskEvent());
      expect(event, isNotNull);
      expect(event!.isSuccessKind, isTrue);
      expect(event.eventId, 'eev_task_001');
      expect(event.subject.versionToken, 'v7');
    });

    test('(反1) 未注册 kind → null（B05 §8：忽略 + 计数，绝不当成功）', () {
      final json = _committedTaskEvent()
        ..['kind'] = 'celebration_random';
      expect(ExperienceEventModel.tryParse(json), isNull);
    });

    test('(反2) E1 被破坏：state_confirmed 无 receipt_ref / 带 error → null', () {
      final noRef = _committedTaskEvent()..['receipt_ref'] = null;
      final withError = _committedTaskEvent()
        ..['commit_state'] = 'error'
        ..['error_state'] = 'expired';
      expect(ExperienceEventModel.tryParse(noRef), isNull);
      expect(ExperienceEventModel.tryParse(withError), isNull);
    });

    test('(反3) E2 互斥被破坏：committed 带 error_state / error 缺 error_state → null', () {
      final mixed = _committedTaskEvent()
        ..['error_state'] = 'expired';
      final errorNoState = <String, dynamic>{
        'schema_version': _schema,
        'event_id': 'eev_err',
        'kind': 'terminal_failed',
        'receipt_ref': null,
        'commit_state': 'error',
        'error_state': null,
        'subject': <String, dynamic>{'type': 'task', 'id': 't', 'version_token': 'v'},
        'presentation': <String, dynamic>{
          'modalities': <String>['visual'],
          'copy_key': 'err.expired',
        },
        'dedupe_key': 'd',
        'issued_at': '2026-09-28T00:00:00',
        'expires_at': null,
      };
      expect(ExperienceEventModel.tryParse(mixed), isNull);
      expect(ExperienceEventModel.tryParse(errorNoState), isNull);
    });
  });

  group('验收 1：无 committed 回执不触发成功；同 event 重播不重复震/音', () {
    test('(正) committed 任务事件 → 成功面孔（success 徽章 + 成功声/触一次）', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final outcome = adapter.present(
        _committedTaskEvent(),
        currentSubjectVersionToken: 'v7',
      );

      expect(outcome.action, ExperienceFeedbackAction.presentSuccess);
      expect(outcome.visualState, PixelRunState.success);
      expect(outcome.celebrates, isTrue);
      expect(outcome.copy, '任务已更新');
      await adapter.emitSensory(outcome);
      expect(sink.calls, <String>['success']);
    });

    test('(反) 结构违规事件 → ignoredInvalid：无视觉、无声/触、计数可观测', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final bad = _committedTaskEvent()..['receipt_ref'] = null;

      final outcome = adapter.present(bad, currentSubjectVersionToken: 'v7');

      expect(outcome.action, ExperienceFeedbackAction.ignoredInvalid);
      expect(outcome.celebrates, isFalse);
      expect(outcome.visualState, isNull);
      expect(adapter.ignoredInvalidCount, 1);
      await adapter.emitSensory(outcome);
      expect(sink.calls, isEmpty);
    });

    test('同 event_id 重播 → replaySuppressed：不重复声/触、不重放庆祝，文本仍恢复', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);

      final first = adapter.present(
        _committedTaskEvent(),
        currentSubjectVersionToken: 'v7',
      );
      await adapter.emitSensory(first);
      final replay = adapter.present(
        _committedTaskEvent(),
        currentSubjectVersionToken: 'v7',
      );

      expect(first.action, ExperienceFeedbackAction.presentSuccess);
      expect(replay.action, ExperienceFeedbackAction.replaySuppressed);
      expect(replay.playsSuccessCue, isFalse);
      expect(replay.visualState, isNull, reason: '不重放庆祝动效（PixelSuccessBadge 不再触发）');
      expect(replay.copy, '任务已更新', reason: '文本状态仍恢复');
      await adapter.emitSensory(replay);
      expect(sink.calls, <String>['success'], reason: '同 event 重播不重复震/音');
    });
  });

  group('验收 2：仅保存记忆不显示任务修改完成；证据登记不叫精通', () {
    test('(反) memory committed 事件 → 高亮呈现：无成功徽章、无成功声/触', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final memoryEvent = _committedTaskEvent()
        ..['subject'] = <String, dynamic>{'type': 'memory', 'id': 'm-1', 'version_token': 'v7'}
        ..['presentation'] = <String, dynamic>{
          'modalities': <String>['visual'],
          'copy_key': 'memory.saved',
        };

      final outcome = adapter.present(memoryEvent, currentSubjectVersionToken: 'v7');

      expect(outcome.action, ExperienceFeedbackAction.presentHighlight);
      expect(outcome.copy, '记忆已保存');
      expect(outcome.visualState, isNull, reason: '记忆保存不得渲染成功徽章');
      expect(outcome.celebrates, isFalse);
      expect(outcome.playsSuccessCue, isFalse);
      expect(outcome.playsSelectionCue, isTrue, reason: '可选轻触（MOTION 乐谱行）');
      await adapter.emitSensory(outcome);
      expect(sink.calls, <String>['selection'], reason: '不用任务成功音');
    });

    test('证据登记（progress_delta + outcome://）→「证据已登记」，中性无精通词', () {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      final evidenceEvent = <String, dynamic>{
        'schema_version': _schema,
        'event_id': 'eev_evd_001',
        'kind': 'progress_delta',
        'receipt_ref': 'outcome://out-1',
        'commit_state': 'committed',
        'error_state': null,
        'subject': <String, dynamic>{'type': 'task', 'id': 'task-1', 'version_token': 'v7'},
        'presentation': <String, dynamic>{
          'modalities': <String>['visual'],
          'copy_key': 'evidence.registered',
        },
        'dedupe_key': 'd-evd',
        'issued_at': '2026-09-28T00:00:00',
        'expires_at': null,
      };

      final outcome = adapter.present(evidenceEvent, currentSubjectVersionToken: 'v7');

      expect(outcome.action, ExperienceFeedbackAction.presentNeutral);
      expect(outcome.copy, '证据已登记');
      expect(outcome.celebrates, isFalse);
      expect(outcome.visualState, isNull);
    });

    test('冻结文案表禁词扫描：全表无「精通/已掌握/掌握度」，成功键仅三域', () {
      const forbidden = <String>['精通', '已掌握', '掌握度', 'mastery'];
      kExperienceCopyTable.forEach((String key, String copy) {
        for (final marker in forbidden) {
          expect(key.contains(marker), isFalse, reason: '$key 含禁词 $marker');
          expect(copy.contains(marker), isFalse, reason: '$copy 含禁词 $marker');
        }
      });
      expect(kExperienceCopyTable['memory.saved'], '记忆已保存');
      expect(kSuccessFaceSubjectTypes, <String>{'task', 'goal', 'plan'});
      // 与 backend experience_copy.v1 逐键镜像（17 键）。
      expect(kExperienceCopyTable.length, 17);
    });
  });

  group('验收 3：断网/版本未知仍可查，不渲染为绿色成功', () {
    test('(正) resolveUnknownDisplayState → unknown 徽章态（虚线问号，仍可查）', () {
      expect(
        ExperienceFeedbackAdapter.resolveUnknownDisplayState(),
        PixelRunState.unknown,
      );
      expect(PixelStateSpec.forState(PixelRunState.unknown).celebrates, isFalse);
    });

    test('(反) committed 事件 + 当前版本未知（断网）→ unknown 态，绝不成功视觉', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);

      final outcome = adapter.present(_committedTaskEvent());

      expect(outcome.action, ExperienceFeedbackAction.presentUnknown);
      expect(outcome.visualState, PixelRunState.unknown);
      expect(outcome.celebrates, isFalse);
      expect(outcome.playsSuccessCue, isFalse);
      await adapter.emitSensory(outcome);
      expect(sink.calls, isEmpty, reason: 'unknown 态不成功音/触');
    });

    test('版本不符（对象已前进）→ staleVersionSuppressed：无庆祝，仅中性文本', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);

      final outcome = adapter.present(
        _committedTaskEvent(),
        currentSubjectVersionToken: 'v9',
      );

      expect(outcome.action, ExperienceFeedbackAction.staleVersionSuppressed);
      expect(outcome.celebrates, isFalse);
      expect(outcome.visualState, isNull);
      await adapter.emitSensory(outcome);
      expect(sink.calls, isEmpty);
    });
  });

  group('失败面（terminal_failed）：错误语义永不通成功视觉', () {
    test('version_conflict → conflict 徽章；expired → failed 徽章；警示触一次', () async {
      final sink = _RecordingSink();
      final adapter = ExperienceFeedbackAdapter(sink: sink);
      Map<String, dynamic> errorEvent(String errorState) => <String, dynamic>{
            'schema_version': _schema,
            'event_id': 'eev_err_$errorState',
            'kind': 'terminal_failed',
            'receipt_ref': 'action_command://22222222-2222-2222-2222-222222222222',
            'commit_state': 'error',
            'error_state': errorState,
            'subject': <String, dynamic>{'type': 'task', 'id': 'task-1', 'version_token': 'v7'},
            'presentation': <String, dynamic>{
              'modalities': <String>['visual'],
              'copy_key': 'err.$errorState',
            },
            'dedupe_key': 'd-$errorState',
            'issued_at': '2026-09-28T00:00:00',
            'expires_at': null,
          };

      final conflict = adapter.present(
        errorEvent('version_conflict'),
        currentSubjectVersionToken: 'v7',
      );
      expect(conflict.action, ExperienceFeedbackAction.presentFailure);
      expect(conflict.visualState, PixelRunState.conflict);
      expect(conflict.celebrates, isFalse);
      expect(conflict.copy, '你的设置已更新，需要重新生成');

      final expired = adapter.present(errorEvent('expired'));
      expect(expired.visualState, PixelRunState.failed);
      expect(expired.celebrates, isFalse);

      await adapter.emitSensory(expired);
      expect(sink.calls, <String>['warning'], reason: '明确操作失败警示一次，无连锁蜂鸣');
    });
  });

  test('copy 表跨端互钉：canonical sha256 与 backend 侧一致（F03 二审 CH-3）', () {
    // 与 backend/tests/services/test_experience_presentation_adapter.py 的
    // test_copy_table_canonical_pin_cross_end 互钉同一常量。任一侧单边改字/
    // 增删键即红；双侧协同修改需同步更新两侧钉值。
    final keys = kExperienceCopyTable.keys.toList()..sort();
    final canonical = StringBuffer('{');
    for (var i = 0; i < keys.length; i++) {
      if (i > 0) canonical.write(',');
      canonical.write('"${keys[i]}":"${kExperienceCopyTable[keys[i]]}"');
    }
    canonical.write('}');
    final digest = sha256.convert(utf8.encode(canonical.toString()));
    expect(digest.toString(),
        '949757daf0b81e7c31bad47f5ad4a47d6aa559270fd614ecafe6bf431862b200');
  });
}
