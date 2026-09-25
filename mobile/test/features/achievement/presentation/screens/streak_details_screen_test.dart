import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/screens/streak_details_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// V3-FIX-59 · 连胜详情概览句「窗与数一致」契约。
///
/// 缺陷（Q-03 视觉审查反例 L48 截图）：模板把「过去7天」硬编码，而
/// totalCheckins 是整个 90 天统计窗的完成天数 → 渲染出
/// 「过去7天你有70天完成了任务」——7 天窗装不下 70 天，一眼不可信。
/// 契约：概览句的窗口值与完成数**同源**（都来自同一段历史日历）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Widget _buildHarness({
    required StreakStats stats,
    required List<StreakDayRecord> days,
  }) {
    final containerOverrides = <Override>[
      streakStatsProvider.overrideWithValue(stats),
      streakHistoryProvider.overrideWith(
        (ref) => StreakHistoryNotifier(_FakeRepository(days)),
      ),
    ];
    return ProviderScope(
      overrides: containerOverrides,
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: const StreakDetailsScreen(),
      ),
    );
  }

  List<StreakDayRecord> _history({required int activeDays, required int totalDays}) {
    final now = DateTime.now();
    final records = <StreakDayRecord>[];
    for (var i = 0; i < totalDays; i++) {
      final day = now.subtract(Duration(days: i));
      records.add(
        StreakDayRecord(
          day: day,
          status: i < activeDays ? StreakDayStatus.active : StreakDayStatus.missed,
        ),
      );
    }
    return records;
  }

  testWidgets('概览句窗口=统计窗（90 天）时，完成数与窗口同源渲染', (tester) async {
    const activeDays = 70;
    const totalDays = 90;
    final stats = StreakStats(
      currentStreak: 7,
      maxStreak: 70,
      longestStreak: 0,
      freezeCharges: 3,
      maxFreezeCharges: 3,
      totalCheckinDays: activeDays,
    );
    await tester.pumpWidget(
      _buildHarness(stats: stats, days: _history(activeDays: activeDays, totalDays: totalDays)),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1700));

    // 反例回归：不得再出现「过去7天你有70天」的自相矛盾句。
    expect(find.textContaining('过去7天你有70天'), findsNothing);
    // 窗与数一致：窗口值 = 历史日历长度（90），完成数 = 同一历史内的完成天数。
    expect(find.textContaining('过去90天你有70天完成了任务'), findsOneWidget);
  });

  testWidgets('小窗口数据（30 天窗 12 天完成）同样窗数一致', (tester) async {
    final stats = StreakStats(
      currentStreak: 2,
      maxStreak: 30,
      longestStreak: 0,
      freezeCharges: 3,
      maxFreezeCharges: 3,
      totalCheckinDays: 12,
    );
    await tester.pumpWidget(
      _buildHarness(stats: stats, days: _history(activeDays: 12, totalDays: 30)),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1700));

    expect(find.textContaining('过去30天你有12天完成了任务'), findsOneWidget);
  });

  testWidgets('历史未加载（空日历）不渲染可能为假的概览句', (tester) async {
    final stats = StreakStats(
      currentStreak: 5,
      maxStreak: 50,
      longestStreak: 0,
      freezeCharges: 3,
      maxFreezeCharges: 3,
      totalCheckinDays: 5,
    );
    await tester.pumpWidget(_buildHarness(stats: stats, days: const []));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1700));

    expect(find.textContaining('完成了任务'), findsNothing);
  });
}

class _FakeRepository implements AchievementRepository {
  _FakeRepository(this.days);

  final List<StreakDayRecord> days;

  @override
  Future<List<StreakDayRecord>> getStreakHistory({int days = 90}) async {
    return this.days;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
