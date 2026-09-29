// V4-U15 长尾家族清点与风格一致性闭合——守卫棘轮（纯静态面，零 widget）。
//
// 卡面：v4/04_tasks/tasks.json V4-U15；规格：02_design/SCREEN_FAMILIES.md、
// 01_product/MODULE_MATRIX.json（canonical_count=43）、01_master 相关章节。
//
// 五组断言，每组一正（真实仓库现状成立）一反（合成输入必判负，断言非恒真）：
//  A 清点 exact match：features 目录 == 43 矩阵模块 + learning（V4-U10 学习
//    旅程承载目录，SCREEN_FAMILIES「星图/学习/错题/资料」家族邻接； MATRIX
//    onboarding_note 判例同构——历史面有明确承载归属则不另算新模块）。
//  B repeat 棘轮：FIX-569/S01R1 移交基线 = 复跑数 49（S01 自述 48 少记 1）。
//    现存 repeat 文件集 ⊆ 基线集且总数 ≤ 49——只允许清理（出集），
//    不允许新增（入集判负）。清尾优先级见 v4/evidence/V4-U15 登记表。
//  C LABS/HIDDEN 不可达：reflection（HIDDEN）路由零导航调用方；
//    SeedLibraryDashboardCard（内含 /seed-libraries push 的孤儿组件）零
//    lib 消费点——潜在 LABS 入口保持未挂载；CORE 面字面 LABS 路径零 push。
//  D 主题真源单一：U15 八模块零 ThemeExtension/ThemeData/ColorScheme 自建
//    （核心令牌真源仍在 core/design；LABS 域内容调色板见 E 组）。
//  E LABS 调色板消费面冻结：visual_element_palette 的模块外消费方 ⊆ 冻结
//    集合（community 成就分享卡，U11 面）——只允许退出，不允许新增。
//
// 与既有守卫的关系：nav_decontextualization_contract_test（CORE 面符号级
// LABS 入口禁令，12 文件）、check_ui_design_tokens_ratchet.py（UI-TOKENS
// 冻结基线，visual_element_palette 44 色在其内）——本文件不重复其断言，
// 只补它们没盖住的：清点矩阵、repeat 集合棘轮、字面路径级 C 组、主题
// 声明级 D 组、调色板消费面 E 组。
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 当前工作目录 = mobile/（flutter test 惯例，同 nav_decontextualization 契约测试）。
const String kLibRoot = 'lib';

const String kRepeatNeedle = '.repeat(';

/// FIX-569/S01R1 移交基线：S01 base d57a7aa8 复跑数 49（文件级）。
/// U15 在 main@90275dc4 复跑同集合 1:1（零新增/零退出），登记于
/// v4/evidence/V4-U15/run_manifest.json 清点矩阵。
const int kRepeatRatchetMax = 49;

/// 冻结 repeat 基线集（49 路径，lib 相对）——现存集合必须是其子集。
const Set<String> kRepeatBaseline49 = {
  'lib/core/design/components/molecules/stepper_indicator.dart',
  'lib/core/design/motion.dart',
  'lib/core/design/widgets/animation_lifecycle_mixin.dart',
  'lib/core/design/widgets/flame_indicator.dart',
  'lib/core/design/widgets/rarity_visual_wrapper.dart',
  'lib/core/design/widgets/sparkle_motion_primitives.dart',
  'lib/core/design/widgets/sparkle_skeleton.dart',
  'lib/core/widgets/scene_atmosphere_layer.dart',
  'lib/features/achievement/presentation/screens/achievement_contract_screen.dart',
  'lib/features/achievement/presentation/screens/achievement_detail_screen.dart',
  'lib/features/achievement/presentation/screens/achievement_list_screen.dart',
  'lib/features/achievement/presentation/screens/achievement_map_screen.dart',
  'lib/features/achievement/presentation/screens/streak_details_screen.dart',
  'lib/features/achievement/presentation/widgets/achievement_milestone_badge.dart',
  'lib/features/achievement/presentation/widgets/achievement_unlock_dialog.dart',
  'lib/features/achievement/presentation/widgets/streak_indicator.dart',
  'lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart',
  'lib/features/chat/presentation/screens/chat_screen.dart',
  'lib/features/chat/presentation/widgets/action_card.dart',
  'lib/features/chat/presentation/widgets/agent_avatar_stack.dart',
  'lib/features/chat/presentation/widgets/agent_avatar_switcher.dart',
  'lib/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart',
  'lib/features/chat/presentation/widgets/chat_run_phase_indicator.dart',
  'lib/features/chat/presentation/widgets/collaboration_timeline.dart',
  'lib/features/chat/presentation/widgets/plan_review_card.dart',
  'lib/features/chat/presentation/widgets/regeneration_prompt.dart',
  'lib/features/chat/presentation/widgets/review_appeal_card.dart',
  'lib/features/chat/presentation/widgets/status_awareness_bar.dart',
  'lib/features/chat/widgets/agent_status_indicator.dart',
  'lib/features/chat/widgets/typing_text.dart',
  'lib/features/community/presentation/widgets/bonfire_widget.dart',
  'lib/features/community/presentation/widgets/community_widgets.dart',
  'lib/features/focus/presentation/widgets/flip_clock.dart',
  'lib/features/focus/presentation/widgets/star_background.dart',
  'lib/features/galaxy/data/services/galaxy_edge_animation.dart',
  'lib/features/galaxy/presentation/widgets/galaxy/graphrag_visualizer.dart',
  'lib/features/home/presentation/screens/weather_guide_screen.dart',
  'lib/features/home/presentation/widgets/focus_card.dart',
  'lib/features/home/presentation/widgets/layers/particle_layer.dart',
  'lib/features/home/presentation/widgets/unified_omni_bar.dart',
  'lib/features/home/presentation/widgets/weather_header.dart',
  'lib/features/task/presentation/widgets/execution_status_indicator.dart',
  'lib/features/task/presentation/widgets/task_protocol_panel.dart',
  'lib/features/task/presentation/widgets/timer_widget.dart',
  'lib/features/theater/presentation/screens/knowledge_theater_screen.dart',
  'lib/features/theater/presentation/widgets/knowledge_theater_graph.dart',
  'lib/features/visual_elements/presentation/widgets/visual_element_card.dart',
  'lib/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart',
  'lib/features/visual_elements/presentation/widgets/visual_element_unlock_dialog.dart',
};

/// MODULE_MATRIX.json canonical_count=43 的模块名单（v4/01_product）。
const Set<String> kMatrixModules43 = {
  'achievement', 'aurora', 'auth', 'calendar', 'chat', 'cognitive',
  'community', 'document', 'documents', 'error_book', 'experience', 'file',
  'focus', 'galaxy', 'goal', 'home', 'insights', 'intent', 'journey',
  'knowledge', 'leaderboard', 'memory', 'mirofish', 'notification_center',
  'openclaw', 'photon', 'plan', 'recovery', 'reflection', 'report',
  'reviews', 'seed_library', 'settings', 'shop', 'simulation', 'splash',
  'task', 'theater', 'tools', 'translation', 'user', 'visual_elements',
  'vocabulary',
};

/// 唯一允许的第 44 目录：V4-U10 学习旅程承载（goal 携参进入，
/// 「不会从目标跳入无上下文的工具空页」路由契约在其 routes 文件头）。
const String kLearningCarrierDir = 'learning';

/// U15 本卡八模块（tasks.json modules 字段）。
const Set<String> kU15Modules = {
  'intent', 'mirofish', 'reflection', 'seed_library', 'simulation',
  'theater', 'visual_elements', 'tools',
};

/// CORE 活跃面（与 nav_decontextualization_contract_test 的 coreSurfaces
/// 同源清单）：字面 LABS 路径 push 逐文件为禁令面。
const List<String> kCoreSurfaceFiles = [
  'lib/features/home/presentation/widgets/recent_insights_card.dart',
  'lib/features/home/presentation/widgets/insight_hub_card.dart',
  'lib/features/insights/presentation/screens/learning_insights_overview_screen.dart',
  'lib/features/report/presentation/screens/learning_report_screen.dart',
  'lib/features/chat/presentation/widgets/chat_bubble.dart',
  'lib/features/chat/presentation/screens/chat_settings_screen.dart',
  'lib/features/user/presentation/screens/profile_screen.dart',
  'lib/features/user/presentation/screens/unified_settings_screen.dart',
  'lib/features/tools/tool_registry.dart',
  'lib/features/home/presentation/widgets/dashboard_card_section.dart',
  'lib/features/home/presentation/widgets/dashboard_edit_sheet.dart',
  'lib/features/home/presentation/providers/dashboard_card_config_provider.dart',
];

/// C3 字面禁令：CORE 面不得出现的 LABS 路径 push 片段。
const List<String> kForbiddenLiteralPaths = [
  "push('/seed-libraries')",
  "push('/simulation')",
  "push('/theater')",
  "push('/visual-elements')",
  "push('/reflection/summary')",
  "go('/seed-libraries')",
  "go('/simulation')",
  "go('/theater')",
  "go('/visual-elements')",
  "go('/reflection/summary')",
];

/// E 组冻结集：visual_element_palette 允许的模块外消费方（lib 相对路径）。
/// 依据：U11（community 面 APPROVE_CLOSED）既有成就分享卡；新增消费方
/// 须走卡面裁决并扩此集合——棘轮只允许退出。
const Set<String> kPaletteOutsideConsumersAllowed = {
  'lib/features/community/presentation/widgets/share_cards/achievement_share_card.dart',
};

// ---------------------------------------------------------------------------
// 纯函数（正反共用谓词；反例喂合成输入，保证断言非恒真）
// ---------------------------------------------------------------------------

/// 剥除注释行（与 check_ui_design_tokens_ratchet.py 同口径）。
List<String> codeLines(String source) => source
    .split('\n')
    .where((line) {
      final s = line.trimLeft();
      return !s.startsWith('//') && !s.startsWith('*') && !s.startsWith('/*');
    })
    .toList();

/// 从 (路径, 源码) 集合中找含针（如 `.repeat(`）的文件（代码行口径）。
Set<String> filesContainingNeedle(
  Map<String, String> sources,
  String needle,
) =>
    sources.entries
        .where((e) => codeLines(e.value).any((l) => l.contains(needle)))
        .map((e) => e.key)
        .toSet();

/// A 组谓词：目录清点差异（幽灵 = 多出；遗漏 = 少了）。
List<String> inventoryViolations({
  required Set<String> actualDirs,
  required Set<String> matrixModules,
  required String carrierDir,
}) {
  final expected = {...matrixModules, carrierDir};
  final ghosts = actualDirs.difference(expected).toList()..sort();
  final missing = expected.difference(actualDirs).toList()..sort();
  return [
    for (final g in ghosts) '幽灵目录（不在 43 矩阵+承载白名单）: $g',
    for (final m in missing) '遗漏模块（矩阵登记但无目录）: $m',
  ];
}

/// 棘轮谓词（B/E 共用语义）：actual ⊆ allowed 且 total ≤ maxAllowed。
List<String> ratchetViolations({
  required Set<String> actual,
  required Set<String> allowed,
  required int maxAllowed,
  required String label,
}) {
  final violations = <String>[];
  final fresh = actual.difference(allowed).toList()..sort();
  for (final f in fresh) {
    violations.add('$label 新增越基线面（须先裁决扩基线）: $f');
  }
  if (actual.length > maxAllowed) {
    violations.add('$label 总数 ${actual.length} > 棘轮上限 $maxAllowed');
  }
  return violations;
}

/// 不可达谓词（C 组）：在扫描面（已排除注册面）中找违禁符号出现。
List<String> occurrenceViolations({
  required Map<String, String> sources,
  required List<String> needles,
  required String label,
}) {
  final violations = <String>[];
  for (final entry in sources.entries) {
    final lines = codeLines(entry.value);
    for (var i = 0; i < lines.length; i++) {
      for (final needle in needles) {
        if (lines[i].contains(needle)) {
          violations.add('$label @ ${entry.key}:${i + 1} 命中 "$needle"');
        }
      }
    }
  }
  return violations;
}

/// 递归收集 lib 下 dart 文件（lib 相对路径 → 绝对路径）。
Map<String, String> readAllLibSources({String root = kLibRoot}) {
  final out = <String, String>{};
  final dir = Directory(root);
  if (!dir.existsSync()) return out;
  for (final entity in dir.listSync(recursive: true)) {
    if (entity is! File || !entity.path.endsWith('.dart')) continue;
    final rel = entity.path.replaceAll(r'\', '/');
    out[rel] = entity.readAsStringSync();
  }
  return out;
}

Set<String> libFeatureDirs() => Directory('$kLibRoot/features')
    .listSync()
    .whereType<Directory>()
    .map((d) => d.path.split('/').last)
    .toSet();

// ---------------------------------------------------------------------------
// 测试
// ---------------------------------------------------------------------------

void main() {
  group('V4-U15 A｜43+1 模块清点 exact match（SCREEN_FAMILIES/MODULE_MATRIX）',
      () {
    test('A+ features 目录集合 == 43 矩阵模块 + learning 承载（无幽灵无遗漏）',
        () {
      final actual = libFeatureDirs();
      final violations = inventoryViolations(
        actualDirs: actual,
        matrixModules: kMatrixModules43,
        carrierDir: kLearningCarrierDir,
      );
      expect(violations, isEmpty,
          reason: '清点必须 exact match：$violations',);
      expect(actual.length, kMatrixModules43.length + 1,
          reason: 'canonical_count=43 + learning（U10 学习旅程承载，'
              'MATRIX onboarding_note 判例：有明确承载归属不另算新模块）',);
    });

    test('A- 幽灵目录与遗漏模块都被具名判负（断言非恒真）', () {
      final violations = inventoryViolations(
        actualDirs: {...kMatrixModules43, kLearningCarrierDir, 'ghost_pixel'},
        matrixModules: kMatrixModules43,
        carrierDir: kLearningCarrierDir,
      );
      expect(violations, hasLength(1));
      expect(violations.single, contains('ghost_pixel'));
      expect(violations.single, contains('幽灵目录'));

      final missingViolations = inventoryViolations(
        actualDirs: {...kMatrixModules43.where((m) => m != 'task'),
            kLearningCarrierDir,},
        matrixModules: kMatrixModules43,
        carrierDir: kLearningCarrierDir,
      );
      expect(missingViolations, hasLength(1));
      expect(missingViolations.single, contains('遗漏模块'));
      expect(missingViolations.single, contains(': task'));
    });
  });

  group('V4-U15 B｜repeat 动效棘轮（FIX-569：基线=复跑数 49）', () {
    final libSources = readAllLibSources();

    test('B+ 现存 repeat 文件集 ⊆ 冻结基线集 且 ≤ 49（只降不升）', () {
      final current =
          filesContainingNeedle(libSources, kRepeatNeedle)
              .where((p) => p.startsWith('$kLibRoot/'))
              .toSet();
      // 复跑数记录（本次运行实录应 = 49；清理后可 < 49，棘轮允许只降）。
      // ignore: avoid_print
      print('U15 repeat 复跑数 = ${current.length}（基线 49）');
      final violations = ratchetViolations(
        actual: current,
        allowed: kRepeatBaseline49,
        maxAllowed: kRepeatRatchetMax,
        label: 'repeat',
      );
      expect(violations, isEmpty,
          reason: 'FIX-569/S01R1 移交：S01 自述 48 少记 1，复跑数 49 为准；'
              '新增 repeat 面必须先走卡面裁决。差异：$violations',);
      expect(current, isNotEmpty,
          reason: '扫描非空转探针（清尾推进后此断言随基线常量一并下调——'
              '降棘轮 = 显式改 kRepeatBaseline49/kRepeatRatchetMax，diff 可见，'
              '同 UI-TOKENS --update-baseline 流程；S01 limitation #1 无门'
              '清单的清尾优先级见 v4/evidence/V4-U15 登记表，不在此钉死存在性）',);
    });

    test('B- 新增 repeat 文件 / 超基数都被判负（断言非恒真）', () {
      const clean = 'class Ok {\n  void tick(int i) {}\n}\n';
      const withRepeat =
          'class Bad {\n  void loop() {\n    controller.repeat();\n  }\n}\n';
      final sources = <String, String>{
        'lib/features/a.dart': clean,
        'lib/features/b.dart': withRepeat,
      };
      final current = filesContainingNeedle(sources, kRepeatNeedle);
      expect(current, {'lib/features/b.dart'},
          reason: '注释行不计数、代码行命中才计——口径与 UI-TOKENS 棘轮一致',);
      final violations = ratchetViolations(
        actual: current,
        allowed: {'lib/features/b.dart'},
        maxAllowed: 1,
        label: 'repeat',
      );
      expect(violations, isEmpty, reason: '控制组：基线内不误报');

      final freshViolation = ratchetViolations(
        actual: {...current, 'lib/features/c.dart'},
        allowed: {'lib/features/b.dart'},
        maxAllowed: 2,
        label: 'repeat',
      );
      expect(freshViolation, hasLength(1));
      expect(freshViolation.single, contains('lib/features/c.dart'));

      final overMax = ratchetViolations(
        actual: {...current, 'lib/features/c.dart'},
        allowed: {...current, 'lib/features/c.dart'},
        maxAllowed: 1,
        label: 'repeat',
      );
      expect(overMax, hasLength(1));
      expect(overMax.single, contains('2 > 棘轮上限 1'));
    });
  });

  group('V4-U15 C｜LABS/HIDDEN 不可达（不泄露入口）', () {
    test('C1+ reflection（HIDDEN）路由零导航调用方（仅注册面在场）', () {
      final sources = readAllLibSources()
        ..removeWhere(
          (path, _) =>
              path.startsWith('lib/features/reflection/') ||
              path == 'lib/app/routes.dart',
        );
      final violations = occurrenceViolations(
        sources: sources,
        needles: [
          'ReflectionRoutes.summary',
          "push('/reflection/summary')",
          "go('/reflection/summary')",
        ],
        label: 'HIDDEN reflection 导航调用方',
      );
      expect(violations, isEmpty,
          reason: 'HIDDEN 面只可经深链到达，生产导航面零入口（MODULE_MATRIX：'
              '维持 HIDDEN，复盘能力复用活跃报告）。命中：$violations',);
    });

    test('C1- 合成导航调用方被具名判负（断言非恒真）', () {
      final violations = occurrenceViolations(
        sources: {
          'lib/features/home/presentation/screens/home_screen.dart':
              'void f(BuildContext c) => c.push(ReflectionRoutes.summary);\n',
        },
        needles: ['ReflectionRoutes.summary'],
        label: 'HIDDEN reflection 导航调用方',
      );
      expect(violations, hasLength(1));
      expect(violations.single, contains('home_screen.dart'));
    });

    test('C2+ SeedLibraryDashboardCard（孤儿组件，内含 LABS push）零 lib 消费点',
        () {
      final sources = readAllLibSources()
        ..removeWhere(
          (path, _) =>
              path ==
              'lib/features/home/presentation/widgets/seed_library_dashboard_card.dart',
        );
      final violations = occurrenceViolations(
        sources: sources,
        needles: ['SeedLibraryDashboardCard'],
        label: 'LABS 孤儿组件消费点',
      );
      expect(violations, isEmpty,
          reason: 'V3-FIX-360 已将其移出仪表盘配置；本断言钉死其保持未挂载'
              '（潜在 /seed-libraries 入口不复活）。命中：$violations',);
    });

    test('C2- 合成消费点被判负（断言非恒真）', () {
      final violations = occurrenceViolations(
        sources: {
          'lib/features/home/presentation/screens/home_screen.dart':
              "import 'package:sparkle/features/home/presentation/widgets/seed_library_dashboard_card.dart';\n"
                  'Widget build() => const SeedLibraryDashboardCard();\n',
        },
        needles: ['SeedLibraryDashboardCard'],
        label: 'LABS 孤儿组件消费点',
      );
      expect(violations, hasLength(1));
      expect(violations.single, contains('home_screen.dart'));
    });

    test('C3+ CORE 活跃面字面 LABS 路径 push 零命中（符号级守卫的字面补强）', () {
      final violations = <String>[];
      for (final path in kCoreSurfaceFiles) {
        final file = File(path);
        expect(file.existsSync(), isTrue, reason: '守卫清单文件必须在场: $path');
        violations.addAll(occurrenceViolations(
          sources: {path: file.readAsStringSync()},
          needles: kForbiddenLiteralPaths,
          label: 'CORE 面字面 LABS push',
        ),);
      }
      expect(violations, isEmpty, reason: 'U07 已摘除的入口不得以字面路径回流：$violations');
    });

    test('C3- 合成字面 push 被判负（断言非恒真）', () {
      final violations = occurrenceViolations(
        sources: {
          'lib/features/tools/tool_registry.dart':
              "void f(BuildContext c) => c.push('/seed-libraries');\n",
        },
        needles: kForbiddenLiteralPaths,
        label: 'CORE 面字面 LABS push',
      );
      expect(violations, hasLength(1));
      expect(violations.single, contains("push('/seed-libraries')"));
    });
  });

  group('V4-U15 D｜主题真源单一（不新增第二主题权威）', () {
    final themeDeclNeedles = [
      'ThemeExtension<',
      'ThemeData(',
      'ColorScheme(',
    ];

    test('D+ U15 八模块零主题声明（令牌消费 core/design 权威）', () {
      final sources = readAllLibSources();
      final scoped = <String, String>{
        for (final e in sources.entries)
          if (kU15Modules.any((m) => e.key.startsWith('lib/features/$m/')))
            e.key: e.value,
      };
      expect(scoped.length, greaterThanOrEqualTo(50),
          reason: '扫描面覆盖八模块（防白名单写错导致空转）',);
      final violations = occurrenceViolations(
        sources: scoped,
        needles: themeDeclNeedles,
        label: 'U15 模块主题声明',
      );
      expect(violations, isEmpty,
          reason: 'tokens_v2 → theme → context.* 唯一真源（MASTER_DESIGN §4）；'
              'LABS 域内容调色板（非 Theme 语义）另由 E 组+UI-TOKENS 冻结。'
              '命中：$violations',);
    });

    test('D- 合成主题声明被判负（断言非恒真）', () {
      for (final needle in themeDeclNeedles) {
        final violations = occurrenceViolations(
          sources: {
            'lib/features/theater/presentation/screens/x.dart':
                'final th = ThemeData(seedColor: Colors.teal);\n',
            'lib/core/design/theme/authority.dart':
                'class MyEx extends ThemeExtension<MyEx> {}\n',
          },
          needles: [needle],
          label: 'U15 模块主题声明',
        );
        if (needle == 'ThemeData(') {
          expect(violations, hasLength(1));
          expect(violations.single, contains('x.dart'));
        } else if (needle == 'ThemeExtension<') {
          expect(violations, hasLength(1));
          expect(violations.single, contains('authority.dart'));
        } else {
          expect(violations, isEmpty, reason: '控制组：ColorScheme( 无命中时为空');
        }
      }
    });
  });

  group('V4-U15 E｜LABS 调色板消费面冻结（visual_element_palette）', () {
    test('E+ 模块外消费方 ⊆ 冻结集合（只允许退出，不允许新增）', () {
      final sources = readAllLibSources();
      final importers = sources.entries
          .where((e) =>
              codeLines(e.value).any((l) =>
                  l.contains('import') && l.contains('visual_element_palette'),),)
          .map((e) => e.key)
          .toSet();
      final outside = importers
          .where((p) => !p.startsWith('lib/features/visual_elements/'))
          .toSet();
      final violations = ratchetViolations(
        actual: outside,
        allowed: kPaletteOutsideConsumersAllowed,
        maxAllowed: kPaletteOutsideConsumersAllowed.length,
        label: 'LABS 调色板模块外消费',
      );
      expect(violations, isEmpty,
          reason: '44 色本身在 UI-TOKENS 冻结基线内（LABS 域内容资产）；'
              '本断言冻结其溢出面：新增模块外消费须卡面裁决。差异：$violations',);
    });

    test('E- 合成新增消费方被判负（断言非恒真）', () {
      final violations = ratchetViolations(
        actual: {
          ...kPaletteOutsideConsumersAllowed,
          'lib/features/goal/presentation/screens/goal_screen.dart',
        },
        allowed: kPaletteOutsideConsumersAllowed,
        maxAllowed: kPaletteOutsideConsumersAllowed.length,
        label: 'LABS 调色板模块外消费',
      );
      expect(violations, hasLength(2));
      expect(violations.first, contains('goal_screen.dart'));
      expect(violations.last, contains('2 > 棘轮上限 1'));
    });
  });
}
