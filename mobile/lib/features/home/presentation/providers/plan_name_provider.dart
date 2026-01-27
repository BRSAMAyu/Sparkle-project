import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

/// 计划名称映射状态
class PlanNameMap {
  const PlanNameMap({this.map = const {}});
  final Map<String, String> map;

  /// 通过 planId 获取计划名称
  String? operator [](String? planId) => planId == null ? null : map[planId];

  PlanNameMap copyWith(Map<String, String>? map) =>
      PlanNameMap(map: map ?? this.map);
}

/// 计划名称映射通知器
///
/// 监听 planListProvider 的变化，自动维护 planId -> planName 的映射
class PlanNameMapNotifier extends StateNotifier<PlanNameMap> {
  PlanNameMapNotifier(this._ref) : super(const PlanNameMap()) {
    // 同步加载初始数据
    _loadPlanNamesSync();
  }

  final Ref _ref;

  void _loadPlanNamesSync() {
    final planState = _ref.read(planListProvider);
    final nameMap = <String, String>{};

    // 合并所有计划和活跃计划
    for (final plan in [...planState.plans, ...planState.activePlans]) {
      nameMap[plan.id] = plan.name;
    }

    state = PlanNameMap(map: nameMap);
  }

  /// 刷新计划名称映射
  Future<void> refresh() async {
    await _ref.read(planListProvider.notifier).refresh();
    _loadPlanNamesSync();
  }
}

/// 计划名称映射 provider
///
/// 提供全局的计划ID到名称的映射表
final planNameMapProvider =
    StateNotifierProvider<PlanNameMapNotifier, PlanNameMap>(
  PlanNameMapNotifier.new,
);

/// 辅助 provider：通过 planId 获取单个计划名称
///
/// 使用示例：
/// ```dart
/// final planName = ref.watch(planNameProvider(planId));
/// ```
final planNameProvider = Provider.family<String?, String>((ref, planId) {
  if (planId.isEmpty) return null;
  final nameMap = ref.watch(planNameMapProvider);
  return nameMap[planId];
});
