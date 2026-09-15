import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/skill_models.dart';
import 'package:sparkle/core/services/skill_api_service.dart';
import 'package:sparkle/features/user/presentation/screens/skill_management_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

class _FakeSkillApiService implements SkillApiService {
  _FakeSkillApiService();

  final List<SkillItemModel> skills = <SkillItemModel>[
    SkillItemModel(
      id: 'skill_1',
      name: 'Exam Triage',
      patternTemplate: 'Scope first.',
      activationConditions: [
        SkillActivationConditionModel(kind: 'intent_keywords', value: ['exam']),
      ],
      examples: const ['先缩小范围。'],
      privacyLevel: 'private',
      usageCount: 2,
      active: true,
    ),
  ];
  final List<SharedSkillItemModel> sharedSkills = <SharedSkillItemModel>[
    SharedSkillItemModel(
      id: 'shared_1',
      name: 'Study Reset',
      patternTemplate: 'Reset with one tiny step.',
      activationConditions: const [],
      examples: const [],
      authorLabel: 'anonymous',
    ),
  ];
  bool draftAccepted = false;
  bool shareCalled = false;
  bool unshareCalled = false;
  bool forkCalled = false;

  @override
  Future<SkillItemModel> createSkill(Map<String, dynamic> payload) async {
    final item = SkillItemModel(
      id: 'skill_${skills.length + 1}',
      name: payload['name'] as String? ?? '',
      patternTemplate: payload['pattern_template'] as String? ?? '',
      activationConditions:
          (payload['activation_conditions'] as List<dynamic>? ?? [])
              .whereType<Map<String, dynamic>>()
              .map(SkillActivationConditionModel.fromJson)
              .toList(),
      examples: (payload['examples'] as List<dynamic>? ?? [])
          .map((e) => '$e')
          .toList(),
      privacyLevel: 'private',
      usageCount: 0,
      active: payload['active'] as bool? ?? true,
    );
    skills.insert(0, item);
    return item;
  }

  @override
  Future<void> deleteSkill(String id) async {
    skills.removeWhere((item) => item.id == id);
  }

  @override
  Future<SkillDraftModel> extractDraft(Map<String, dynamic> payload) async =>
      SkillDraftModel(
        name: 'Draft Skill',
        patternTemplate: 'Use this pattern next time.',
        activationConditions: [
          SkillActivationConditionModel(
            kind: 'intent_keywords',
            value: ['draft'],
          ),
        ],
        examples: const ['example'],
      );

  @override
  Future<SkillItemModel> forkSharedSkill(String id) async {
    forkCalled = true;
    final item = SkillItemModel(
      id: 'fork_1',
      name: 'Study Reset',
      patternTemplate: 'Reset with one tiny step.',
      activationConditions: const [],
      examples: const [],
      privacyLevel: 'private',
      usageCount: 0,
      active: true,
      forkedFromShareId: id,
      forkedAt: DateTime(2026, 4, 21),
    );
    skills.insert(0, item);
    return item;
  }

  @override
  Future<List<SharedSkillItemModel>> getSharedSkills({
    int page = 1,
    int pageSize = 20,
  }) async =>
      sharedSkills;

  @override
  Future<List<SkillItemModel>> getSkills() async => skills;

  @override
  Future<void> recordDraftOutcome(bool accepted) async {
    draftAccepted = accepted;
  }

  @override
  Future<Map<String, dynamic>> shareSkill(String id) async {
    shareCalled = true;
    final index = skills.indexWhere((item) => item.id == id);
    if (index >= 0) {
      skills[index] = SkillItemModel(
        id: skills[index].id,
        name: skills[index].name,
        patternTemplate: skills[index].patternTemplate,
        activationConditions: skills[index].activationConditions,
        examples: skills[index].examples,
        privacyLevel: 'shared',
        usageCount: skills[index].usageCount,
        active: skills[index].active,
        sharedCatalogId: 'shared_generated',
      );
    }
    return {'status': 'approved', 'shared_skill_id': 'shared_generated'};
  }

  @override
  Future<SkillItemModel> toggleSkill(String id, bool active) async {
    final index = skills.indexWhere((item) => item.id == id);
    final item = skills[index];
    final updated = SkillItemModel(
      id: item.id,
      name: item.name,
      patternTemplate: item.patternTemplate,
      activationConditions: item.activationConditions,
      examples: item.examples,
      privacyLevel: item.privacyLevel,
      usageCount: item.usageCount,
      active: active,
      sharedCatalogId: item.sharedCatalogId,
      forkedFromShareId: item.forkedFromShareId,
      forkedAt: item.forkedAt,
    );
    skills[index] = updated;
    return updated;
  }

  @override
  Future<SkillItemModel> unshareSkill(String id) async {
    unshareCalled = true;
    final index = skills.indexWhere((item) => item.id == id);
    final item = skills[index];
    final updated = SkillItemModel(
      id: item.id,
      name: item.name,
      patternTemplate: item.patternTemplate,
      activationConditions: item.activationConditions,
      examples: item.examples,
      privacyLevel: 'private',
      usageCount: item.usageCount,
      active: item.active,
    );
    skills[index] = updated;
    return updated;
  }

  @override
  Future<SkillItemModel> updateSkill(
    String id,
    Map<String, dynamic> payload,
  ) async {
    final index = skills.indexWhere((item) => item.id == id);
    final updated = SkillItemModel(
      id: id,
      name: payload['name'] as String? ?? skills[index].name,
      patternTemplate: payload['pattern_template'] as String? ??
          skills[index].patternTemplate,
      activationConditions:
          (payload['activation_conditions'] as List<dynamic>? ?? [])
              .whereType<Map<String, dynamic>>()
              .map(SkillActivationConditionModel.fromJson)
              .toList(),
      examples: (payload['examples'] as List<dynamic>? ?? [])
          .map((e) => '$e')
          .toList(),
      privacyLevel: skills[index].privacyLevel,
      usageCount: 0,
      active: payload['active'] as bool? ?? skills[index].active,
      sharedCatalogId: skills[index].sharedCatalogId,
      forkedFromShareId: skills[index].forkedFromShareId,
      forkedAt: skills[index].forkedAt,
    );
    skills[index] = updated;
    return updated;
  }
}

void main() {

  setUp(setUpI18nForTesting);
  Widget _buildApp(_FakeSkillApiService api) => ProviderScope(
        overrides: [
          skillApiServiceProvider.overrideWithValue(api),
        ],
        child: testMaterialApp(home: SkillManagementScreen()),
      );

  testWidgets('skill screen renders personal and shared tabs', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    expect(find.text('我的方式'), findsNWidgets(2));
    expect(find.text('Exam Triage'), findsOneWidget);
    expect(find.text('共享目录'), findsOneWidget);
  });

  testWidgets('skill screen creates a new skill from editor', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('新建方式'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, '名称'), 'New Skill');
    await tester.enterText(
      find.widgetWithText(TextField, '处理模板'),
      'Do this in a compact way.',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'intent keywords'),
      'compact',
    );
    await tester.tap(find.text('保存'));
    await tester.pumpAndSettle();

    expect(api.skills.first.name, 'New Skill');
    expect(find.text('New Skill'), findsWidgets);
  });

  testWidgets('skill screen toggles a skill', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(Switch).first);
    await tester.pumpAndSettle();

    expect(api.skills.first.active, isFalse);
  });

  testWidgets('skill screen shares and unshares a skill', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.text('共享'));
    await tester.pumpAndSettle();
    expect(api.shareCalled, isTrue);

    await tester.tap(find.text('撤回共享'));
    await tester.pumpAndSettle();
    expect(api.unshareCalled, isTrue);
  });

  testWidgets('skill screen forks a shared skill from catalog', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.text('共享目录'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Fork 到我的方式'));
    await tester.pumpAndSettle();

    expect(api.forkCalled, isTrue);
  });

  testWidgets('skill screen extracts draft and records accept outcome', (
    tester,
  ) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('从草稿生成'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, '用户原话'), '以后这样做');
    await tester.enterText(find.widgetWithText(TextField, 'AI 回复'), '先压缩范围');
    await tester.tap(find.text('生成草稿'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('保存'));
    await tester.pumpAndSettle();

    expect(api.draftAccepted, isTrue);
    expect(api.skills.first.name, 'Draft Skill');
    expect(find.text('Draft Skill'), findsWidgets);
  });

  testWidgets('skill screen deletes a skill', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.text('删除'));
    await tester.pumpAndSettle();

    expect(find.text('Exam Triage'), findsNothing);
  });

  testWidgets('skill screen edits an existing skill', (tester) async {
    final api = _FakeSkillApiService();
    await tester.pumpWidget(_buildApp(api));
    await tester.pumpAndSettle();

    await tester.tap(find.text('编辑'));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.widgetWithText(TextField, '名称'), 'Edited Skill');
    await tester.tap(find.text('保存'));
    await tester.pumpAndSettle();

    expect(find.text('Edited Skill'), findsOneWidget);
  });
}
