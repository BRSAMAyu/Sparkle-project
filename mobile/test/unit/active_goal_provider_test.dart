import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

void main() {
  test('MultiGoalOverview resolves the selected goal by id', () {
    const overview = MultiGoalOverview(
      selectedGoalId: 'goal-2',
      goals: [
        ActiveGoalSnapshot(
          id: 'goal-1',
          title: 'Exam sprint',
          goalType: 'exam',
          healthScore: 0.86,
          weeklyConflictCount: 1,
        ),
        ActiveGoalSnapshot(
          id: 'goal-2',
          title: 'Portfolio project',
          goalType: 'project',
          healthScore: 0.58,
          weeklyConflictCount: 0,
        ),
      ],
    );

    expect(overview.selectedGoal?.id, 'goal-2');
    expect(overview.selectedGoal?.title, 'Portfolio project');
  });

  test('MultiGoalOverview falls back to the first goal', () {
    const overview = MultiGoalOverview(
      selectedGoalId: 'missing',
      goals: [
        ActiveGoalSnapshot(
          id: 'goal-1',
          title: 'Exam sprint',
          goalType: 'exam',
          healthScore: 0.86,
          weeklyConflictCount: 1,
        ),
      ],
    );

    expect(overview.selectedGoal?.id, 'goal-1');
  });

  test('GoalArbitrationSuggestion flags conflicts', () {
    const suggestion = GoalArbitrationSuggestion(
      primaryGoalId: 'goal-1',
      primaryGoalTitle: 'Exam sprint',
      rationale: 'Deadline pressure is highest.',
      conflicts: ['time_overlap'],
    );

    expect(suggestion.hasConflict, isTrue);
  });
}
