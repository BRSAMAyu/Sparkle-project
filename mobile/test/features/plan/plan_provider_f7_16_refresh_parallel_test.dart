import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

/// F7-16 (round1 07-mobile-features / round2 R2-06) red-green:
/// `refresh()` used to run `await loadPlans(); await loadActivePlans();`
/// serially, so every write operation paid two back-to-back list round
/// trips before the dashboard invalidation chain. The fix fans both loads
/// out with `Future.wait`.
///
/// The cross-gate repository proves parallelism structurally: each load
/// only completes once *both* have been entered. Under serial refresh the
/// first call deadlocks on the second's gate and `refresh()` times out
/// (red); under `Future.wait` both gates are crossed immediately (green).
class _CrossGatePlanRepository implements PlanRepository {
  Completer<void> _enteredPlans = Completer<void>();
  Completer<void> _enteredActive = Completer<void>();

  /// Fresh gates for the call under test, so the constructor's own
  /// initial loads cannot pre-satisfy them.
  void resetGates() {
    _enteredPlans = Completer<void>();
    _enteredActive = Completer<void>();
  }

  bool get plansGateCrossed => _enteredPlans.isCompleted;
  bool get activeGateCrossed => _enteredActive.isCompleted;

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async {
    _enteredPlans.complete();
    await _enteredActive.future;
    return const <PlanModel>[];
  }

  @override
  Future<List<PlanModel>> getActivePlans() async {
    _enteredActive.complete();
    await _enteredPlans.future;
    return const <PlanModel>[];
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName}');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('F7-16: refresh fans plan list loads out in parallel', () async {
    final repo = _CrossGatePlanRepository();
    final container = ProviderContainer(
      overrides: [planRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);

    // Construction fires its own initial load pair; let it settle, then
    // re-arm the gates for the call under test.
    final notifier = container.read(planListProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    repo.resetGates();

    // Serial refresh deadlocks on the cross gate and hits this timeout
    // (red); parallel refresh crosses it (green).
    await notifier.refresh().timeout(const Duration(seconds: 3));

    expect(repo.plansGateCrossed, isTrue);
    expect(repo.activeGateCrossed, isTrue);
  });
}
