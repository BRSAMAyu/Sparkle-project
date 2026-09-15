import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/skill_models.dart';

void main() {
  test('skill item model parses fork and share metadata', () {
    final item = SkillItemModel.fromJson({
      'id': 'skill_1',
      'name': 'Exam Triage',
      'pattern_template': 'Scope first.',
      'activation_conditions': [
        {
          'kind': 'intent_keywords',
          'value': ['exam']
        }
      ],
      'examples': ['a'],
      'privacy_level': 'shared',
      'usage_count': 3,
      'active': true,
      'forked_from_share_id': 'shared_1',
      'shared_catalog_id': 'shared_live',
    });

    expect(item.isForked, isTrue);
    expect(item.isShared, isTrue);
    expect(item.activationConditions.first.value.first, 'exam');
  });
}
