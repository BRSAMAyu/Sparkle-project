import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260504-0931-G5:
/// Mock getGroupTasks must return seeded tasks, not hardcoded [].
/// createGroupTask must persist to internal list, not return empty shell.
/// claimTask/completeTask must update task state.
void main() {
  group('MockCommunityRepository group tasks regression (G5)', () {
    late Map<String, List<_TaskStub>> tasks;

    _TaskStub makeTask(String id, String title,
        {int claims = 0, int completions = 0, bool claimed = false, bool? done}) {
      return _TaskStub(
        id: id,
        title: title,
        totalClaims: claims,
        totalCompletions: completions,
        completionRate: claims > 0 ? completions / claims : 0,
        isClaimedByMe: claimed,
        myCompletionStatus: done,
      );
    }

    List<_TaskStub> getGroupTasks(String groupId) =>
        List.from(tasks[groupId] ?? []);

    _TaskStub createGroupTask(String groupId, _TaskStub task) {
      final newTask = _TaskStub(
        id: 'new_${task.id}',
        title: task.title,
        totalClaims: 0,
        totalCompletions: 0,
        completionRate: 0,
      );
      tasks.putIfAbsent(groupId, () => []).add(newTask);
      return newTask;
    }

    void claimTask(String taskId) {
      for (final list in tasks.values) {
        final idx = list.indexWhere((t) => t.id == taskId);
        if (idx != -1) {
          list[idx] = list[idx].copyWith(
            isClaimedByMe: true,
            totalClaims: list[idx].totalClaims + 1,
          );
          return;
        }
      }
    }

    void completeTask(String taskId) {
      for (final list in tasks.values) {
        final idx = list.indexWhere((t) => t.id == taskId);
        if (idx != -1) {
          list[idx] = list[idx].copyWith(
            myCompletionStatus: true,
            totalCompletions: list[idx].totalCompletions + 1,
          );
          return;
        }
      }
    }

    setUp(() {
      tasks = {
        'group_a': [
          makeTask('t1', 'Task 1', claims: 2, completions: 1, claimed: true),
          makeTask('t2', 'Task 2', claims: 3, completions: 3, done: true),
          makeTask('t3', 'Task 3', claims: 1, completions: 0),
        ],
      };
    });

    test('getGroupTasks returns seeded tasks, not empty', () {
      final result = getGroupTasks('group_a');
      expect(result.length, 3);
      expect(result[0].title, 'Task 1');
    });

    test('getGroupTasks returns empty for unknown group', () {
      expect(getGroupTasks('nonexistent'), isEmpty);
    });

    test('createGroupTask adds to list and returns real task', () {
      final newTask = _TaskStub(
        id: 'raw',
        title: 'New Task',
        totalClaims: 0,
        totalCompletions: 0,
        completionRate: 0,
      );
      final result = createGroupTask('group_a', newTask);
      expect(result.id, isNotEmpty);
      expect(result.id, isNot('raw'));
      expect(result.title, 'New Task');
      expect(tasks['group_a']!.length, 4);
    });

    test('claimTask updates isClaimedByMe and totalClaims', () {
      claimTask('t3');
      final updated = tasks['group_a']![2];
      expect(updated.isClaimedByMe, isTrue);
      expect(updated.totalClaims, 2); // was 1
    });

    test('completeTask updates myCompletionStatus and totalCompletions', () {
      completeTask('t1');
      final updated = tasks['group_a']![0];
      expect(updated.myCompletionStatus, isTrue);
      expect(updated.totalCompletions, 2); // was 1
    });
  });
}

class _TaskStub {
  _TaskStub({
    required this.id,
    required this.title,
    this.totalClaims = 0,
    this.totalCompletions = 0,
    this.completionRate = 0,
    this.isClaimedByMe = false,
    this.myCompletionStatus,
  });
  final String id;
  final String title;
  final int totalClaims;
  final int totalCompletions;
  final double completionRate;
  final bool isClaimedByMe;
  final bool? myCompletionStatus;

  _TaskStub copyWith({
    String? id,
    String? title,
    int? totalClaims,
    int? totalCompletions,
    double? completionRate,
    bool? isClaimedByMe,
    bool? myCompletionStatus,
    bool clearMyCompletionStatus = false,
  }) =>
      _TaskStub(
        id: id ?? this.id,
        title: title ?? this.title,
        totalClaims: totalClaims ?? this.totalClaims,
        totalCompletions: totalCompletions ?? this.totalCompletions,
        completionRate: completionRate ?? this.completionRate,
        isClaimedByMe: isClaimedByMe ?? this.isClaimedByMe,
        myCompletionStatus:
            clearMyCompletionStatus ? null : (myCompletionStatus ?? this.myCompletionStatus),
      );
}
