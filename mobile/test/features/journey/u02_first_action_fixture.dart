import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/journey/data/repositories/first_action_repository.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';

/// U-02 journey/first-action 截图与 rubric 用确定性状态夹具
/// （first_action_card_test 同款记录型仓库口径：PENDING 提案 +
/// 三字段 action_plan，屏代码零改动）。
List<Override> firstActionFixtureOverrides() {
  const state = FirstActionState(
    goal: FirstActionGoal(
      goalId: 'g-u02',
      title: '两周内完成高数第三章首轮复习',
      goalType: 'exam',
    ),
    proposal: <String, dynamic>{
      'proposal_id': 'p-u02',
      'status': 'PENDING',
      'payload': {
        'tasks': [
          {
            'title': '做 2023 年测验卷的特征值大题',
            'estimated_minutes': 25,
            'action_plan': {
              'desired_outcome': '一份带订正的特征值大题答卷',
              'smallest_useful_step': {
                'description': '只做第 1 题，写完整过程',
                'useful_because': ['produces_artifact'],
              },
              'completion_evidence': [
                {'evidence_kind': 'artifact'},
              ],
              'execution_mode': 'hybrid',
              'cognitive_ownership': 'user_core',
            },
          },
        ],
      },
    },
  );
  return [
    firstActionRepositoryProvider.overrideWithValue(_U02FirstActionRepository()),
    firstActionStateProvider.overrideWith((ref) async => state),
  ];
}

class _U02FirstActionRepository extends FirstActionRepository {
  _U02FirstActionRepository()
      : super(_U02FakeApiClient(), _U02FakeProposalRepository());
}

class _U02FakeApiClient extends Fake implements ApiClient {}

class _U02FakeProposalRepository extends Fake
    implements ActionProposalRepository {}
