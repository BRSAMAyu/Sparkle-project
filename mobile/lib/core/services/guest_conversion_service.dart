import 'package:shared_preferences/shared_preferences.dart';

/// N40（A-SPEC7 §4）· 访客唯一转化点 · 价值信号常量与一次性标记持久层。
///
/// 设计口径（aha-before-signup）：访客先体验，注册是价值完成后的动作。
/// 本层只持久化两类事实：
/// 1. **价值信号**（[GuestValueSignal]）——访客体验过「产品真的帮到我」的
///    时刻，累计只增；是转化钩子唯一的正当触发源。
/// 2. **挂起标记**——用户点掉引导卡后「不再弹，直到下个价值信号」。
///
/// 克制红线（同会话最多一次 / 永不打断进行中任务）不在本层守门，由
/// `guest_conversion_provider` 的派生可见性统一裁决；本层保持无 UI 语义。
enum GuestValueSignal {
  /// 首个任务完成——「第一次真正帮到学习」的价值时刻（旅程 S6）。
  /// 接线点：task_execution 完成回调收口（task_execution_screen.dart）。
  firstTaskCompleted('first_task_completed'),

  /// 首次诊断产出——认知棱镜长出第一条行为定式（旅程 S7）。
  /// 接线点：聊天内规划类 AI 输出落点（引擎 requires_review →
  /// PlanReviewCard，chat_notifier_actions 的 plan review 处理收口）。
  firstDiagnosisOutput('first_diagnosis_output'),

  /// 首次记忆被引用——「它记得我」receipt 时刻（旅程 S8）。
  /// 接线点：AI 回复收口处（chat_provider finalizeRun）——引擎仅在确有
  /// 被引用记忆时才产出 memory_reference_receipt，与 ContextReceiptBar
  /// 渲染芯片同源；收口计数而非按渲染帧计数（避免重建重复累加）。
  firstMemoryReferenced('first_memory_referenced');

  const GuestValueSignal(this.key);

  /// 持久化用的稳定标识（与 UI 文案无关，文案迭代不影响语义）。
  final String key;
}

/// 访客转化一次性标记的 SharedPreferences 适配（与 GuestService 同形制）。
class GuestConversionService {
  GuestConversionService(this._prefs)
      : _signalCount = _prefs.getInt(_signalCountKey) ?? 0,
        _lastSignalKey = _prefs.getString(_lastSignalKeyKey),
        _dismissedUntilNextSignal = _prefs.getBool(_dismissedKey) ?? false;

  static const String _signalCountKey = 'guest_conversion_signal_count';
  static const String _lastSignalKeyKey = 'guest_conversion_last_signal';
  static const String _dismissedKey =
      'guest_conversion_dismissed_until_next_signal';

  final SharedPreferences _prefs;
  int _signalCount;
  String? _lastSignalKey;
  bool _dismissedUntilNextSignal;

  /// 访客累计体验过的价值信号次数（跨信号累计，只增不减）。
  int get signalCount => _signalCount;

  /// 最近一次价值信号标识（诊断/埋点用，不参与守门逻辑）。
  String? get lastSignalKey => _lastSignalKey;

  /// 是否处于「点掉不再弹」挂起态（直到下一个价值信号）。
  bool get isDismissedUntilNextSignal => _dismissedUntilNextSignal;

  /// 价值信号唯一收口：计数 +1、记录信号标识，并清除挂起标记
  /// （「下个价值信号重新武装」的语义落点）。
  Future<void> recordValueSignal(GuestValueSignal signal) async {
    _signalCount += 1;
    _lastSignalKey = signal.key;
    await _prefs.setInt(_signalCountKey, _signalCount);
    await _prefs.setString(_lastSignalKeyKey, signal.key);
    if (_dismissedUntilNextSignal) {
      _dismissedUntilNextSignal = false;
      await _prefs.remove(_dismissedKey);
    }
  }

  /// 点掉：挂起直到下一个价值信号（持久，跨会话生效）。
  Future<void> dismissUntilNextSignal() async {
    _dismissedUntilNextSignal = true;
    await _prefs.setBool(_dismissedKey, true);
  }
}
