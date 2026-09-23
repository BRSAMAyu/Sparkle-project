import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/guest_conversion_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// 访客与注册用户的唯一判定口径（与 routes.dart redirect 同源：
/// `registrationSource == 'guest'`），收敛成函数避免各处手写漂移。
bool isGuestUser(UserModel? user) => user?.registrationSource == 'guest';

/// N40 · 访客唯一转化点的会话态。
///
/// - [signalCount]/[dismissedUntilNextSignal] 来自持久层（跨会话事实）；
/// - [dismissedByUserThisSession] 是会话内硬关：点掉或点击注册后，
///   本会话内即使再来了新价值信号也不再出现（「同会话最多一次」红线）。
class GuestConversionState {
  const GuestConversionState({
    this.signalCount = 0,
    this.dismissedUntilNextSignal = false,
    this.dismissedByUserThisSession = false,
  });

  final int signalCount;
  final bool dismissedUntilNextSignal;
  final bool dismissedByUserThisSession;

  /// 访客至少体验过一个价值信号（转化钩子的合法触发前提）。
  bool get hasValueSignal => signalCount > 0;

  /// 硬关闭 = 用户本会话点掉过，或历史挂起尚未被新价值信号清除。
  bool get isHardDismissed =>
      dismissedByUserThisSession || dismissedUntilNextSignal;

  GuestConversionState copyWith({
    int? signalCount,
    bool? dismissedUntilNextSignal,
    bool clearDismissedUntilNextSignal = false,
    bool? dismissedByUserThisSession,
  }) =>
      GuestConversionState(
        signalCount: signalCount ?? this.signalCount,
        dismissedUntilNextSignal: clearDismissedUntilNextSignal
            ? false
            : (dismissedUntilNextSignal ?? this.dismissedUntilNextSignal),
        dismissedByUserThisSession:
            dismissedByUserThisSession ?? this.dismissedByUserThisSession,
      );
}

final guestConversionControllerProvider =
    StateNotifierProvider<GuestConversionController, GuestConversionState>(
  (ref) {
    try {
      return GuestConversionController(
        ref,
        GuestConversionService(ref.watch(sharedPreferencesProvider)),
      );
    } on UnimplementedError {
      // 软降级（合成根未注入 prefs 的测试环境）：转化卡是 best-effort
      // UX，标记退化为进程内（本会话内功能完整、不跨会话持久），绝不
      // 因缺 prefs 而炸掉挂载它的宿主屏（task_execution 完成回调即触达
      // 本 provider，既有用例多数不注入 prefs）。prod 合成根恒注入。
      return GuestConversionController(ref, null);
    }
  },
);

/// N40 · 访客唯一转化点控制器。
///
/// 职责边界：`recordValueSignal` 只**记录**价值信号，绝不直接弹卡——
/// 价值动作发生的当下用户往往仍在任务执行/庆祝/反馈流程内；展示时机
/// 全部交给 [guestConversionVisibleProvider] 的安全窗口派生（home 挂载
/// 点消费），从结构上保证「永不打断进行中任务」。
class GuestConversionController extends StateNotifier<GuestConversionState> {
  GuestConversionController(this._ref, this._service)
      : super(
          _service == null
              ? const GuestConversionState()
              : GuestConversionState(
                  signalCount: _service.signalCount,
                  dismissedUntilNextSignal:
                      _service.isDismissedUntilNextSignal,
                ),
        );

  final Ref _ref;

  /// null = 软降级模式（无持久层，标记仅进程内有效）。
  final GuestConversionService? _service;

  /// 价值信号唯一收口：仅访客记录；注册用户 no-op（免费闭环零变化）。
  /// 下个信号到达时清除历史挂起（重新武装）。
  Future<void> recordValueSignal(GuestValueSignal signal) async {
    if (!isGuestUser(_ref.read(currentUserProvider))) return;
    final service = _service;
    if (service == null) {
      state = state.copyWith(
        signalCount: state.signalCount + 1,
        clearDismissedUntilNextSignal: true,
      );
      return;
    }
    await service.recordValueSignal(signal);
    if (!mounted) return;
    state = state.copyWith(
      signalCount: service.signalCount,
      clearDismissedUntilNextSignal: true,
    );
  }

  /// 点掉：本会话硬关 + 持久挂起，直到下个价值信号。
  Future<void> dismissUntilNextValueSignal() async {
    state = state.copyWith(
      dismissedByUserThisSession: true,
      dismissedUntilNextSignal: true,
    );
    await _service?.dismissUntilNextSignal();
  }

  /// 用户点了注册 CTA：本会话硬关（注册流程本身即转化，不再额外挂起
  /// ——若用户放弃注册，下个会话的新价值信号仍可正当邀请）。
  void markConsumedByRegister() {
    state = state.copyWith(dismissedByUserThisSession: true);
  }
}

/// N40 唯一转化点的派生可见性——克制红线的守门处，四条全部与齐才可见：
/// ① 仅访客（注册用户永不可见，免费闭环零变化）；
/// ② 至少体验过一个价值信号（aha 之后才谈 signup）；
/// ③ 未被点掉/挂起（点掉不再弹直到下个价值信号；同会话最多一次）；
/// ④ 无进行中任务（inProgress/stuck 一律让位，永不打断进行中任务）。
///
/// 唯一消费挂载点 = home（访客落地面）内联卡，非弹窗、非全局 overlay。
final guestConversionVisibleProvider = Provider<bool>((ref) {
  final session = ref.watch(guestConversionControllerProvider);
  final activeTask = ref.watch(activeTaskProvider);
  return isGuestUser(ref.watch(currentUserProvider)) &&
      session.hasValueSignal &&
      !session.isHardDismissed &&
      !_isTaskInFlight(activeTask);
});

bool _isTaskInFlight(TaskModel? task) =>
    task != null &&
    (task.status == TaskStatus.inProgress || task.status == TaskStatus.stuck);
