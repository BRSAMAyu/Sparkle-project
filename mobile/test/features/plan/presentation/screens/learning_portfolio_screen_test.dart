import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/presentation/screens/learning_portfolio_screen.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  testWidgets('learning portfolio renders grouped sprint sections',
      (WidgetTester tester) async {
    await _useTallSurface(tester);
    await tester.pumpWidget(
      _buildApp(
        repository: _FakeExamSprintRepository(
          result: _mockPortfolio(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump();

    expect(find.text('我的学习档案'), findsOneWidget);
    expect(find.text('所有科目累计掌握节点'), findsOneWidget);
    expect(find.text('50'), findsOneWidget);
    expect(find.text('进行中'), findsOneWidget);
    expect(find.text('已完成'), findsOneWidget);
    expect(find.text('计划中'), findsOneWidget);
    expect(find.text('操作系统'), findsOneWidget);
    expect(find.text('计算机网络'), findsOneWidget);
    expect(find.text('高等数学'), findsOneWidget);
    expect(find.text('14天冲刺 · 进行中（第 4 天，还剩 10 天）'), findsOneWidget);
    expect(find.text('7天冲刺（已完成，2026-04-10）'), findsOneWidget);
    expect(find.text('标准冲刺 · 计划中'), findsOneWidget);

    await tester.tap(find.text('计算机网络'));
    await tester.pumpAndSettle();

    expect(find.text('Galaxy 掌握度摘要'), findsOneWidget);
    expect(find.text('最薄弱的点'), findsOneWidget);
    expect(find.text('值得引以为豪的节点'), findsOneWidget);
    expect(find.text('TCP 拥塞控制'), findsWidgets);
    expect(find.text('子网划分'), findsWidgets);
    expect(find.text('估计 82 分'), findsWidgets);
  });

  testWidgets('learning portfolio empty state shows onboarding copy',
      (WidgetTester tester) async {
    await _useTallSurface(tester);
    await tester.pumpWidget(
      _buildApp(
        repository: _FakeExamSprintRepository(
          result: const LearningPortfolioResult(
            entries: <LearningPortfolioEntry>[],
            totalMasteredNodes: 0,
            activeCount: 0,
            completedCount: 0,
            plannedCount: 0,
          ),
        ),
      ),
    );

    await tester.pump();
    await tester.pump();

    expect(find.text('你的学习档案还没有任何冲刺记录'), findsOneWidget);
    expect(find.text('去创建考试冲刺'), findsOneWidget);
  });
}

Future<void> _useTallSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(900, 1800));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Widget _buildApp({
  required _FakeExamSprintRepository repository,
}) {
  return ProviderScope(
    overrides: [
      examSprintRepositoryProvider.overrideWithValue(repository),
      currentUserProvider.overrideWithValue(_mockUser()),
    ],
    child: MaterialApp(
      theme: AppThemes.lightTheme,
      home: const LearningPortfolioScreen(),
    ),
  );
}

LearningPortfolioResult _mockPortfolio() {
  return LearningPortfolioResult(
    totalMasteredNodes: 50,
    activeCount: 1,
    completedCount: 1,
    plannedCount: 1,
    entries: <LearningPortfolioEntry>[
      LearningPortfolioEntry(
        planId: 'plan-active',
        planName: '14天操作系统冲刺',
        subject: '操作系统',
        sprintMode: 'fourteen_day_build_and_retrieve',
        status: 'active',
        masteredNodesCount: 18,
        startedAt: DateTime(2026, 4, 17, 9),
        targetDate: DateTime(2026, 4, 30),
        progress: 0.3,
        headline: '进行到第 4 天，还剩 10 天。',
        weakestPoints: const <String>['死锁'],
        proudNodes: const <String>['完成 4 / 14 天'],
      ),
      LearningPortfolioEntry(
        planId: 'plan-completed',
        planName: '7天计网冲刺',
        subject: '计算机网络',
        sprintMode: 'seven_day_survival',
        status: 'completed',
        masteredNodesCount: 32,
        startedAt: DateTime(2026, 4, 4, 9),
        completedAt: DateTime(2026, 4, 10, 20),
        targetDate: DateTime(2026, 4, 10),
        progress: 1,
        strongestArea: 'TCP 拥塞控制',
        growthArea: '子网划分',
        resultRating: 4,
        resultDescription: '估计 82 分',
        headline: '7 天内补齐了高频保底点。',
        currentScore: 82,
        weakestPoints: const <String>['子网划分'],
        proudNodes: const <String>['TCP 拥塞控制'],
      ),
      LearningPortfolioEntry(
        planId: 'plan-planned',
        planName: '高等数学冲刺',
        subject: '高等数学',
        sprintMode: 'standard_exam_sprint',
        status: 'planned',
        masteredNodesCount: 0,
        startedAt: DateTime(2026, 5, 1, 9),
        targetDate: DateTime(2026, 5, 14),
        progress: 0,
        weakestPoints: const <String>['积分中值定理'],
      ),
    ],
  );
}

UserModel _mockUser() {
  final now = DateTime(2026, 4, 25, 9);
  return UserModel(
    id: 'user-1',
    username: 'tester',
    email: 'tester@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    createdAt: now,
    updatedAt: now,
  );
}

class _FakeExamSprintRepository extends ExamSprintRepository {
  _FakeExamSprintRepository({required this.result}) : super(_NoopApiClient());

  final LearningPortfolioResult result;

  @override
  Future<LearningPortfolioResult> fetchLearningPortfolio({
    String? userId,
  }) async {
    return result;
  }
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
