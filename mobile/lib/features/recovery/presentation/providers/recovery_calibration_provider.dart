import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart'
    show proposalActionIdempotencyKey;

/// V4-U02 ·「卡住 → 纠正 → 差异确认」校准控制器——recovery sheet 的 V4 垂直交互面。
///
/// 语义铁律（卡面验收，全部可失败）：
/// ① **恒可达**：本面不依赖旅程载荷是否有提案/intervention——系统弃权
///    （abstain / no_action）时纠正输入依然在（I04：no_action 是可纠正
///    状态不是终审）；
/// ② **两写路径分离**：「保存为偏好」只走既有 M-08 理解纠正写面
///    （`POST /experience/understanding-snapshot/corrections`），方法体
///    结构上没有任何 proposal/任务写调用；「仅本次调整」只走 X-03 统一
///    command path 生成提案，不写偏好。取消/关闭 = 零写（原行动不变；
///    未确认提案留在任务既有收件箱里，由既有 U-04 面继续处理）；
/// ③ **回执门**：`committed` 相只在 approve/权威投影返回 COMMITTED 且回执
///    本体（receipt map）在场时进入——成功面孔不得先于回执（CH-R1/F03
///    反面教训在此终结：本文件无 AppFeedback.success 调用，成功呈现是
///    回执驱动的状态相，不是动作驱动的 toast）；409 版本冲突/解析不出
///    的未知态均给出可恢复出口（重看权威投影 / 按最新重调 / 取消提案），
///    绝不呈现为成功。
///
/// 不造第二权威：diff 由服务端 `prepare()` 计算后随投影返回，本面只渲染
/// changed 字段的前后值；approve/cancel 幂等语义在服务端（X-09），重试
/// 复用同一幂等键（重放恰一次）。
enum RecoveryCalibrationPhase {
  /// 纠正输入（恒可达；abstain 时的唯一初始相）。
  input,

  /// 约束/偏好分离选择（两个互斥写路径；也都可以不选）。
  scopeChoice,

  /// 结构化调整（本地 stepper，提案尚未创建，零写）。
  adjusting,

  /// 服务端 diff 在场，等确认（零写）。
  diffReview,

  /// approve 在途——**唯一零成功反馈的在途相**。
  confirming,

  /// 回执在场（唯一允许成功面孔的相）。
  committed,

  /// 409 版本冲突（可恢复：按最新重调 / 取消提案）。
  conflict,

  /// 响应无法解析为已落账——诚实未知，不给成功（可重看权威投影）。
  unknown,

  /// 偏好已保存（中性 ack；**不是**任务成功面孔，任务未改动）。
  preferenceSaved,

  /// 偏好保存失败（如实呈现，可重试；任务未改动）。
  preferenceFailed,
}

/// X-03 投影状态词表（本面消费的封闭子集；其余一律 unknown，不猜）。
const String _kProposalCommitted = 'COMMITTED';

/// 服务端终态词表（`ProposalStatus` 终态封闭：无出边；镜像自 backend
/// `app/core/action_command.py`）。create 重放命中终态 = 这份幂等键已
/// 消耗在新意图之外（一审 B-2）——不得当作可确认对照呈现。
const Set<String> _kTerminalProposalStatuses = <String>{
  'CANCELLED',
  'REJECTED',
  'EXPIRED',
};

/// 服务端提案投影的 fail-closed 解析视图（只保留本面要渲染的字段）。
@immutable
class RecoveryProposalView {
  const RecoveryProposalView({
    required this.proposalId,
    required this.status,
    required this.diffRows,
    this.summary,
    this.receipt,
  });

  /// 从 X-03 投影解析（`{proposal_id, status, diff, summary, receipt, …}`）。
  ///
  /// fail-closed：proposal_id 缺失 → null（调用方按错误处理，不渲染半份）。
  static RecoveryProposalView? fromProjection(Map<String, dynamic> json) {
    final id = (json['proposal_id'] ?? json['id'] ?? '').toString();
    if (id.isEmpty) return null;
    final diffJson = json['diff'];
    final rows = <RecoveryDiffRow>[];
    if (diffJson is Map) {
      final before = diffJson['before'];
      final after = diffJson['after'];
      final changed = diffJson['changed_fields'];
      final beforeMap = before is Map ? Map<String, dynamic>.from(before) : null;
      final afterMap = after is Map ? Map<String, dynamic>.from(after) : null;
      if (changed is List) {
        for (final field in changed) {
          final key = '$field';
          rows.add(RecoveryDiffRow(
            field: key,
            before: _stringify(beforeMap?[key]),
            after: _stringify(afterMap?[key]),
          ),);
        }
      }
    }
    final receipt = json['receipt'];
    return RecoveryProposalView(
      proposalId: id,
      status: (json['status'] ?? '').toString(),
      diffRows: rows,
      summary: (json['summary'] ?? '').toString().isEmpty
          ? null
          : (json['summary'] ?? '').toString(),
      receipt: receipt is Map ? Map<String, dynamic>.from(receipt) : null,
    );
  }

  static String? _stringify(Object? value) {
    if (value == null) return null;
    final text = '$value';
    return text.isEmpty ? null : text;
  }

  final String proposalId;
  final String status;

  /// 可读前后对照（只含 changed 字段；服务端 diff 权威，本地只投影）。
  final List<RecoveryDiffRow> diffRows;

  final String? summary;

  /// 权威回执本体（仅 COMMITTED 投影携带）。
  final Map<String, dynamic>? receipt;

  bool get isCommitted => status == _kProposalCommitted;
}

/// 一行可读 diff（field 的 before → after；值原文渲染，不脑补）。
@immutable
class RecoveryDiffRow {
  const RecoveryDiffRow({
    required this.field,
    this.before,
    this.after,
  });

  final String field;
  final String? before;
  final String? after;
}

class RecoveryCalibrationState {
  const RecoveryCalibrationState({
    this.phase = RecoveryCalibrationPhase.input,
    this.constraintText = '',
    this.baselineMinutes,
    this.adjustedMinutes,
    this.proposal,
    this.busy = false,
    this.transientError = false,
  });

  final RecoveryCalibrationPhase phase;

  /// 用户纠正原话（本次约束的载体；随提案 summary 持久进审计）。
  final String constraintText;

  /// 锚点任务当前预计时长（进入调整前的值；null = 无任务锚点）。
  final int? baselineMinutes;

  /// 本次约束生效后的预计时长（stepper 值）。
  final int? adjustedMinutes;

  /// 已创建的提案（服务端权威投影解析视图；null = 尚无提案）。
  final RecoveryProposalView? proposal;

  /// 命令在途（创建/确认/取消/偏好写）。
  final bool busy;

  /// 瞬时失败（网络等）——如实一行，可重试；不清用户输入。
  final bool transientError;

  /// 回执门：唯一允许成功面孔的相（committed）。
  bool get showsSuccessFace => phase == RecoveryCalibrationPhase.committed;

  RecoveryCalibrationState copyWith({
    RecoveryCalibrationPhase? phase,
    String? constraintText,
    Object? baselineMinutes = _sentinel,
    Object? adjustedMinutes = _sentinel,
    Object? proposal = _sentinel,
    bool? busy,
    bool? transientError,
  }) =>
      RecoveryCalibrationState(
        phase: phase ?? this.phase,
        constraintText: constraintText ?? this.constraintText,
        baselineMinutes: baselineMinutes == _sentinel
            ? this.baselineMinutes
            : baselineMinutes as int?,
        adjustedMinutes: adjustedMinutes == _sentinel
            ? this.adjustedMinutes
            : adjustedMinutes as int?,
        proposal: proposal == _sentinel ? this.proposal : proposal as RecoveryProposalView?,
        busy: busy ?? this.busy,
        transientError: transientError ?? this.transientError,
      );

  static const Object _sentinel = Object();
}

class RecoveryCalibrationController
    extends StateNotifier<RecoveryCalibrationState> {
  RecoveryCalibrationController(
    this._ref, {
    required String taskId,
    int? baselineMinutes,
  })  : _taskId = taskId,
        // 幂等键盐（一审 B-2 返修）：**每次提案意图**一盐——同键重试
        // （网络失败后重试、confirming 回 diffReview 重试）保持同键，
        // 服务端 X-09 恰一次；显式取消一份提案（终态）后重建 = 新意图，
        // 必换新键——否则服务端 `_resume_or_replay` 原样重放终态提案，
        // 客户端拿到 CANCELLED 投影，真实新建从未发生（重放死端）。
        _createKeySalt = _newCreateKeySalt(),
        super(RecoveryCalibrationState(baselineMinutes: baselineMinutes)) {
    if (baselineMinutes != null) {
      state = state.copyWith(adjustedMinutes: baselineMinutes);
    }
  }

  final Ref _ref;
  final String _taskId;
  String _createKeySalt;

  /// 新盐（毫秒级时钟 + 微秒位；同 sheet 内多次重建不撞键）。
  static String _newCreateKeySalt() => DateTime.now().microsecondsSinceEpoch.toString();

  /// 终态之后重建 = 新意图 → 换键（重试绝不走到这里：重试不经过取消）。
  void _rotateCreateKeySalt() {
    _createKeySalt = _newCreateKeySalt();
  }

  static const int _minutesMin = 5;
  static const int _minutesMax = 240;

  static const String _defaultClaim = '卡住时的处理方式';

  // ------------------------------------------------------------------
  // 输入与选择（零写）
  // ------------------------------------------------------------------

  /// 提交纠正原话 → 进入分离选择相。
  void submitConstraint(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    state = state.copyWith(
      phase: RecoveryCalibrationPhase.scopeChoice,
      constraintText: trimmed,
      transientError: false,
    );
  }

  /// 「仅本次」→ 结构化调整（仍零写：提案未创建）。
  /// 无任务锚点时结构性不可达（widget 不出该入口；这里双保险再挡）。
  void chooseThisTime() {
    if (state.baselineMinutes == null) return;
    state = state.copyWith(
      phase: RecoveryCalibrationPhase.adjusting,
      adjustedMinutes: state.baselineMinutes,
      transientError: false,
    );
  }

  void setAdjustedMinutes(int minutes) {
    if (state.phase != RecoveryCalibrationPhase.adjusting) return;
    state = state.copyWith(
      adjustedMinutes: minutes.clamp(_minutesMin, _minutesMax),
      transientError: false,
    );
  }

  /// 回到输入相（已建提案**不**随之取消——取消提案需要显式命令；
  /// 关闭 sheet 同理零写）。
  void resetToInput() {
    state = RecoveryCalibrationState(
      baselineMinutes: state.baselineMinutes,
      adjustedMinutes: state.baselineMinutes,
    );
  }

  // ------------------------------------------------------------------
  // 写路径 A：保存为偏好（M-08 理解纠正写面；结构上不触任务）
  // ------------------------------------------------------------------

  /// 「保存为偏好」：只写理解纠正面（effect_scope=routing_policy），**永不**
  /// 创建提案/改任务（本方法体没有任何 proposal 调用——反例测试钉死）。
  /// 成功呈现是中性 ack（preferenceSaved 相），不是任务成功面孔。
  Future<void> savePreference({
    required String claim,
    required String correction,
  }) async {
    if (state.busy) return;
    final text = correction.trim();
    if (text.isEmpty) return;
    state = state.copyWith(busy: true, transientError: false);
    try {
      final api = _ref.read(apiClientProvider);
      await api.post<dynamic>(
        ApiEndpoints.understandingSnapshotCorrections,
        data: <String, dynamic>{
          'claim': claim.trim().isEmpty ? _defaultClaim : claim.trim(),
          'correction': text,
          'effect_scope': 'routing_policy',
        },
      );
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.preferenceSaved,
        busy: false,
      );
    } on Exception catch (error) {
      debugPrint('[recovery-calibration] preference save failed: $error');
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.preferenceFailed,
        busy: false,
      );
    }
  }

  // ------------------------------------------------------------------
  // 写路径 B：仅本次 → 调整提案（X-03 统一 command path）
  // ------------------------------------------------------------------

  /// 创建调整提案：服务端权威 diff 随投影返回；成功进 diffReview（零写，
  /// 等 confirm）。失败如实留在 adjusting（用户输入不清）。
  Future<void> buildAdjustment() async {
    if (state.busy ||
        state.phase != RecoveryCalibrationPhase.adjusting ||
        _taskId.isEmpty ||
        state.adjustedMinutes == null) {
      return;
    }
    final minutes = state.adjustedMinutes!;
    state = state.copyWith(busy: true, transientError: false);
    try {
      final repository = _ref.read(actionProposalRepositoryProvider);
      final projection = await repository.createAdjustmentProposal(
        taskId: _taskId,
        fields: <String, dynamic>{'estimated_minutes': minutes},
        idempotencyKey: 'u02:$_taskId:est:$minutes:$_createKeySalt',
        summary: state.constraintText.isEmpty
            ? null
            : '仅本次：${state.constraintText}',
      );
      final view = RecoveryProposalView.fromProjection(projection);
      if (view == null) {
        // 投影缺标识：不渲染半份提案（fail-closed），如实报错可重试。
        state = state.copyWith(busy: false, transientError: true);
        return;
      }
      if (_kTerminalProposalStatuses.contains(view.status)) {
        // 一审 B-2 防线：create 重放命中终态（CANCELLED/REJECTED/EXPIRED）
        // = 这份幂等键指向的提案已死，真实新建没有发生——绝不把死提案
        // 当作可确认对照渲染（fail-closed）。换新键，如实一行报错留在
        // 调整相（输入不清），用户可立即重试（重试用新键 = 真新建）。
        _rotateCreateKeySalt();
        state = state.copyWith(busy: false, transientError: true);
        return;
      }
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.diffReview,
        proposal: view,
        busy: false,
      );
    } on Exception catch (error) {
      debugPrint('[recovery-calibration] create proposal failed: $error');
      state = state.copyWith(busy: false, transientError: true);
    }
  }

  /// 确认调整 → approve。**回执门**：
  /// - COMMITTED + 回执本体在场 → `committed`（唯一成功相）；
  /// - 409 → `conflict`（可恢复）；
  /// - 网络/服务错 → 回 diffReview + 瞬时错误行（幂等键不变，重试安全）；
  /// - 响应缺失/词表外/状态 committed 但回执缺席 → `unknown`（诚实未知）。
  ///
  /// confirming 相内零任何成功反馈（时序反例测试钉死）。
  Future<void> confirmAdjustment() async {
    final proposal = state.proposal;
    if (state.busy ||
        proposal == null ||
        (state.phase != RecoveryCalibrationPhase.diffReview &&
            state.phase != RecoveryCalibrationPhase.conflict)) {
      return;
    }
    state = state.copyWith(
      phase: RecoveryCalibrationPhase.confirming,
      busy: true,
      transientError: false,
    );
    try {
      final repository = _ref.read(actionProposalRepositoryProvider);
      final response = await repository.approve(
        proposal.proposalId,
        proposalActionIdempotencyKey(proposal.proposalId, 'approve'),
      );
      _applyVerdict(_parseMutationResponse(response));
    } on DioException catch (error) {
      if (error.response?.statusCode == 409) {
        state = state.copyWith(
          phase: RecoveryCalibrationPhase.conflict,
          busy: false,
        );
        return;
      }
      debugPrint('[recovery-calibration] approve failed: $error');
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.diffReview,
        busy: false,
        transientError: true,
      );
    } on Exception catch (error) {
      debugPrint('[recovery-calibration] approve failed: $error');
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.diffReview,
        busy: false,
        transientError: true,
      );
    }
  }

  /// 「重新查看结果」（unknown / conflict 复核出口）：读权威投影拿真实状态。
  /// 已落账（回执在场）→ 补进 committed（真相赢，不重复写）；仍在等确认
  /// → 回 diffReview（重试确认安全：服务端幂等）；提案不存在 → 回输入相。
  Future<void> refreshFromAuthority() async {
    final proposal = state.proposal;
    if (state.busy || proposal == null || proposal.proposalId.isEmpty) return;
    state = state.copyWith(busy: true, transientError: false);
    try {
      final repository = _ref.read(actionProposalRepositoryProvider);
      final fresh = await repository.getProposal(proposal.proposalId);
      if (fresh == null) {
        state = state.copyWith(busy: false);
        resetToInput();
        return;
      }
      _applyVerdict(_parseProjection(fresh));
    } on Exception catch (error) {
      debugPrint('[recovery-calibration] refresh failed: $error');
      state = state.copyWith(busy: false, transientError: true);
    }
  }

  /// 冲突恢复：按最新状态重调 = 显式取消过期提案（审计面留痕）→ 回调整相。
  /// 取消失败则留在冲突相（不出半恢复态）。
  Future<void> reAdjustAfterConflict() async {
    final proposal = state.proposal;
    if (state.busy ||
        proposal == null ||
        _taskId.isEmpty ||
        state.baselineMinutes == null) {
      return;
    }
    state = state.copyWith(busy: true, transientError: false);
    try {
      final repository = _ref.read(actionProposalRepositoryProvider);
      await repository.cancel(
        proposal.proposalId,
        proposalActionIdempotencyKey(proposal.proposalId, 'cancel'),
      );
      // 一审 B-2：这份提案已终态（user_cancelled）——重建换新键，
      // 否则同值重建被服务端按幂等键重放成 CANCELLED 死提案。
      _rotateCreateKeySalt();
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.adjusting,
        proposal: null,
        adjustedMinutes: state.baselineMinutes,
        busy: false,
      );
    } on Exception catch (error) {
      debugPrint('[recovery-calibration] cancel for readjust failed: $error');
      state = state.copyWith(
        phase: RecoveryCalibrationPhase.conflict,
        busy: false,
        transientError: true,
      );
    }
  }

  /// 显式取消已建提案（diffReview / conflict 通用出口）→ 回输入相。
  /// 任务本体零触碰（取消的是提案，不是行动）。
  Future<void> cancelAdjustment() async {
    final proposal = state.proposal;
    if (state.busy) return;
    if (proposal == null || proposal.proposalId.isEmpty) {
      resetToInput();
      return;
    }
    state = state.copyWith(busy: true, transientError: false);
    try {
      final repository = _ref.read(actionProposalRepositoryProvider);
      await repository.cancel(
        proposal.proposalId,
        proposalActionIdempotencyKey(proposal.proposalId, 'cancel'),
      );
      // 一审 B-2：显式取消 = 这份提案终态——之后重建同值提案必须换新键
      //（重放终态死端防线，见 buildAdjustment 内终态守卫）。
      _rotateCreateKeySalt();
      state = state.copyWith(busy: false);
      resetToInput();
    } on Exception catch (error) {
      debugPrint('[recovery-calibration] cancel proposal failed: $error');
      state = state.copyWith(busy: false, transientError: true);
    }
  }

  // ------------------------------------------------------------------
  // 回执解析（fail-closed：解析不出 = unknown，绝不 = 成功）
  // ------------------------------------------------------------------

  void _applyVerdict(_Verdict verdict) {
    switch (verdict.phase) {
      case RecoveryCalibrationPhase.committed:
        state = state.copyWith(
          phase: RecoveryCalibrationPhase.committed,
          proposal: verdict.proposal,
          busy: false,
        );
      case RecoveryCalibrationPhase.diffReview:
      case RecoveryCalibrationPhase.conflict:
        state = state.copyWith(
          phase: verdict.phase,
          proposal: verdict.proposal,
          busy: false,
        );
      default:
        state = state.copyWith(
          phase: RecoveryCalibrationPhase.unknown,
          busy: false,
        );
    }
  }

  _Verdict _parseMutationResponse(Map<String, dynamic>? response) {
    if (response == null) return const _Verdict.unknown();
    final proposalJson = response['proposal'];
    if (proposalJson is! Map) return const _Verdict.unknown();
    return _parseProjection(Map<String, dynamic>.from(proposalJson));
  }

  /// 投影解析门：COMMITTED 必须携带回执本体才算成功；词表外/回执缺席
  /// 一律 unknown（不猜、不假成功）。
  _Verdict _parseProjection(Map<String, dynamic> projection) {
    final view = RecoveryProposalView.fromProjection(projection);
    if (view == null) return const _Verdict.unknown();
    if (view.status == _kProposalCommitted) {
      if (view.receipt == null || view.receipt!.isEmpty) {
        return const _Verdict.unknown();
      }
      return _Verdict.committed(view);
    }
    switch (view.status) {
      case 'PENDING':
        return _Verdict.pending(view);
      case 'CANCELLED':
      case 'REJECTED':
      case 'EXPIRED':
        return _Verdict.terminal(view);
      default:
        return const _Verdict.unknown();
    }
  }
}

/// approve/投影解析结论（closed 词表）。
class _Verdict {
  const _Verdict.committed(this.proposal)
      : phase = RecoveryCalibrationPhase.committed;

  const _Verdict.pending(this.proposal)
      : phase = RecoveryCalibrationPhase.diffReview;

  const _Verdict.terminal(this.proposal)
      : phase = RecoveryCalibrationPhase.input;

  const _Verdict.unknown()
      : phase = RecoveryCalibrationPhase.unknown,
        proposal = null;

  final RecoveryCalibrationPhase phase;
  final RecoveryProposalView? proposal;
}

/// family：按锚点任务上下文开一张校准面（sheet 打开期内生命周期）。
final recoveryCalibrationProvider = StateNotifierProvider.family
    .autoDispose<RecoveryCalibrationController, RecoveryCalibrationState,
        RecoveryCalibrationArgs>(
  (ref, args) => RecoveryCalibrationController(
    ref,
    taskId: args.taskId,
    baselineMinutes: args.baselineMinutes,
  ),
);

class RecoveryCalibrationArgs {
  const RecoveryCalibrationArgs({
    required this.taskId,
    this.baselineMinutes,
  });

  final String taskId;
  final int? baselineMinutes;

  @override
  bool operator ==(Object other) =>
      other is RecoveryCalibrationArgs &&
      other.taskId == taskId &&
      other.baselineMinutes == baselineMinutes;

  @override
  int get hashCode => Object.hash(taskId, baselineMinutes);
}
