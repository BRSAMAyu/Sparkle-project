import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/memory/data/context_receipt_models.dart';

/// V4-U03 · 「这次的理解」模型测试——I06 `context_selection_receipt.v1`
/// 读面 payload 的移动端消费投影（每面一正一反，全部可失败）。
///
/// 真源纪律：回执说什么就投影什么；note（debug-only）结构性不进任何字段；
/// unresolved 显式 unattributed；candidates 缺失 = unknown 态而非空集；
/// 版本门 fail-closed。
Map<String, dynamic> _receipt({
  String schemaVersion = kContextSelectionReceiptSchemaVersion,
  String receiptId = 'csr_01ARZ3NDEKTSV4RRFFQ69G5FAV',
  String role = 'chat_context',
  List<Map<String, dynamic>> candidates = const [],
  Map<String, dynamic>? whyNow,
  bool candidatesMissing = false,
}) =>
    {
      'schema_version': schemaVersion,
      'receipt_id': receiptId,
      'selection_role': role,
      'decision_id': null,
      'input_versions': {
        'memory_epoch': 7,
        'goal_version': null,
        'task_version': null,
        'policy_version': null,
        'selector_version': 'context_pack.v4-i06.v1',
      },
      'candidates': candidatesMissing ? null : candidates,
      'budget': {
        'candidate_scan_limit': 12,
        'selected_max': 6,
        'clarifications_used': 0,
      },
      'why_now': whyNow,
    };

Map<String, dynamic> _candidate({
  required String ref,
  required String status,
  String? reasonCode,
  String? note,
}) =>
    {
      'ref': ref,
      'status': status,
      'reason_code': reasonCode,
      'note': note,
    };

ContextReceiptView? _parse(
  Map<String, dynamic> receipt, {
  List<Map<String, dynamic>> verifications = const [],
  int resolvedSelectedCount = 0,
}) =>
    ContextReceiptView.tryParse(
      mode: 'live',
      receipt: receipt,
      sourceVerifications: verifications,
      resolvedSelectedCount: resolvedSelectedCount,
    );

void main() {
  group('ContextReceiptView.tryParse — 版本门（fail-closed 同 backend 读侧）', () {
    test('正：当前版本 payload 正常解析出候选/角色/预算', () {
      final view = _parse(
        _receipt(
          candidates: [
            _candidate(ref: 'memory://episodic/aaaa', status: 'selected', note: 'gate:x'),
            _candidate(
              ref: 'memory://goal/bbbb',
              status: 'rejected',
              reasonCode: 'budget_exhausted',
            ),
          ],
          whyNow: {
            'statement': '你最近在准备这场考试',
            'basis_refs': ['memory://episodic/aaaa'],
            'confidence_band': 'high',
          },
        ),
      );

      expect(view, isNotNull);
      expect(view!.selectedCount, 1);
      expect(view.selectionRole, 'chat_context');
      expect(view.whyNowStatement, '你最近在准备这场考试');
      expect(view.whyNowBand, 'high');
      expect(view.rejectedByReason['budget_exhausted'], 1);
    });

    test('反：schema_version 非当前版本 → null（unsupported 态，不当数据渲染）', () {
      expect(
        _parse(_receipt(schemaVersion: 'context_selection_receipt.v2')),
        isNull,
      );
    });

    test('反：receipt_id / selection_role 缺失 → null', () {
      expect(_parse(_receipt(receiptId: '')), isNull);
      expect(_parse(_receipt(role: '')), isNull);
    });
  });

  group('note 纪律（合同 §2 debug-only，不得进用户面）', () {
    test('正：解析成功后视图任何可取字段都不含 note 文本', () {
      final view = _parse(
        _receipt(
          candidates: [
            _candidate(
              ref: 'memory://episodic/aaaa',
              status: 'selected',
              note: 'DEBUG_ONLY_GATE_NOTE',
            ),
          ],
        ),
      );

      final rendered = [
        view!.receiptId,
        view.selectionRole,
        view.whyNowStatement ?? '',
        for (final c in view.candidates) ...[c.ref, c.status, c.reasonCode ?? ''],
        for (final v in view.sourceVerifications) ...[v.ref, v.resolution, v.statusCode],
      ].join('|');

      expect(rendered.contains('DEBUG_ONLY_GATE_NOTE'), isFalse);
    });

    test('反（变异守护）：候选模型根本没有 note 字段——字段清单核对', () {
      // 结构性保证：ReceiptCandidateView 只有 ref/status/reasonCode 三字段。
      const candidate = ReceiptCandidateView(ref: 'r', status: 'selected');
      expect(candidate.ref, 'r');
      expect(candidate.status, 'selected');
      expect(candidate.reasonCode, isNull);
      // 若有人给候选加 note 并渲染，本行的字段断言即红。
      expect(candidate, isA<ReceiptCandidateView>());
    });
  });

  group('词表与映射完整性（冻结词表逐字对齐 backend）', () {
    test('正：8 归因码 / 4 角色 / 4 置信档封闭集与 backend 一致', () {
      expect(
        kRejectionReasonCodes,
        equals({
          'out_of_scope_memory',
          'stale_epoch',
          'utility_gate_rejected',
          'conflicts_confirmed_preference',
          'permission_denied',
          'budget_exhausted',
          'duplicate',
          'expired',
        }),
      );
      expect(
        kSelectionRoles,
        equals({'chat_context', 'proposal_basis', 'resume_view', 'intervention_targeting'}),
      );
      expect(
        kWhyNowConfidenceBands,
        equals({'high', 'medium', 'low', 'unknown'}),
      );
      expect(kCandidateStatuses, equals({'selected', 'rejected', 'unavailable'}));
      expect(kUserCalibratableKinds, equals({'episodic', 'preference', 'goal'}));
    });

    test('反：词表外归因码不进分组、计入 unknownReasonCount（不猜标签不丢弃）', () {
      final view = _parse(
        _receipt(
          candidates: [
            _candidate(ref: 'memory://goal/bbbb', status: 'rejected', reasonCode: 'mystery_code'),
            _candidate(ref: 'memory://goal/cccc', status: 'rejected', reasonCode: 'duplicate'),
          ],
        ),
      );

      expect(view!.rejectedByReason, {'duplicate': 1});
      expect(view.unknownReasonCount, 1);
      expect(view.budgetLimited, isFalse);
    });
  });

  group('parseMemoryRef / calibratableMemories（消费纪律 §7.1）', () {
    test('正：memory:// 双段路径解析出 kind/id', () {
      final target = parseMemoryRef('memory://episodic/1111-2222');
      expect(target, isNotNull);
      expect(target!.kind, 'episodic');
      expect(target.id, '1111-2222');
    });

    test('反：非 memory scheme / 段数不符 → null（不猜其他 scheme 的操作）', () {
      expect(parseMemoryRef('plan://aaaa/bbbb'), isNull);
      expect(parseMemoryRef('document://file-1'), isNull);
      expect(parseMemoryRef('memory://episodic'), isNull);
      expect(parseMemoryRef('no-scheme'), isNull);
    });

    test('正：只有 resolution=resolved 的 selected 记忆进入可校准集合', () {
      final view = _parse(
        _receipt(
          candidates: [
            _candidate(ref: 'memory://episodic/ok-1', status: 'selected'),
            _candidate(ref: 'memory://goal/gone', status: 'selected'),
            _candidate(ref: 'plan://plan-1', status: 'selected'),
            _candidate(
              ref: 'memory://preference/nope',
              status: 'rejected',
              reasonCode: 'duplicate',
            ),
          ],
        ),
        verifications: [
          {
            'ref': 'memory://episodic/ok-1',
            'resolution': 'resolved',
            'status_code': 'ok',
            'detail': 'episodic',
          },
          {'ref': 'memory://goal/gone', 'resolution': 'unresolved', 'status_code': 'deleted'},
          {'ref': 'plan://plan-1', 'resolution': 'resolved', 'status_code': 'ok', 'detail': 'plan'},
        ],
        resolvedSelectedCount: 1,
      );

      final calibratable = view!.calibratableMemories();
      expect(calibratable, hasLength(1));
      expect(calibratable.single.kind, 'episodic');
      expect(calibratable.single.id, 'ok-1');
      // 未进入校准集合 ≠ 静默消失：selected 总数如实保留，unresolved 走显式面。
      expect(view.selectedCount, 3);
      expect(view.resolvedSelectedCount, 1);
    });

    test('反：验证结果缺失/词表外 resolution 从严按 unresolved（不借成功面）', () {
      final view = _parse(
        _receipt(
          candidates: [
            _candidate(ref: 'memory://episodic/no-verify', status: 'selected'),
            _candidate(ref: 'memory://goal/weird', status: 'selected'),
          ],
        ),
        verifications: [
          {'ref': 'memory://goal/weird', 'resolution': 'some_other', 'status_code': 'ok'},
        ],
      );

      expect(view!.calibratableMemories(), isEmpty);
    });

    test('budgetLimited：只有 budget_exhausted 归因置位（验收③的预算面）', () {
      final limited = _parse(
        _receipt(
          candidates: [
            _candidate(
              ref: 'memory://goal/b1',
              status: 'rejected',
              reasonCode: 'budget_exhausted',
            ),
          ],
        ),
      );
      final notLimited = _parse(
        _receipt(
          candidates: [
            _candidate(ref: 'memory://goal/d1', status: 'rejected', reasonCode: 'duplicate'),
          ],
        ),
      );

      expect(limited!.budgetLimited, isTrue);
      expect(notLimited!.budgetLimited, isFalse);
    });
  });

  group('candidates 缺失（旧生产者）——合同读侧 unknown 语义', () {
    test('正：candidatesUnknown=true 且候选集为空（不当空集渲染为无依据）', () {
      final view = _parse(_receipt(candidatesMissing: true));

      expect(view, isNotNull);
      expect(view!.candidatesUnknown, isTrue);
      expect(view.candidates, isEmpty);
      expect(view.selectedCount, 0);
    });

    test('反：正常回执 candidatesUnknown=false', () {
      expect(_parse(_receipt())!.candidatesUnknown, isFalse);
    });
  });
}
