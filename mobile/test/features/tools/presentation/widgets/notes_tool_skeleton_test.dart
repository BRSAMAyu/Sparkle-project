import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/features/tools/presentation/widgets/notes_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

import '../../../../shared/i18n_test_helper.dart';

/// ToolShell 头部的 SparkleIconButton 会 watch accessibilitySettingsProvider，
/// 其真实 notifier 构造即发起服务端同步（Dio）——widget 测试里 stub 掉，
/// 保持骨架断言纯 UI、零网络依赖（否则 fake_async 收尾报 pending Timer）。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// EE-G5（A-SPEC3 §4.4.2 改造 #5）验收：NotesTool 首路径加载期呈现
/// 贴布局骨架（有结构、与内容区块等高），骨架→内容无裸 spinner 过渡。
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('加载期：骨架结构在位（指标行 + 区块卡），无裸 spinner',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          accessibilitySettingsProvider
              .overrideWith(_StubAccessibilitySettingsNotifier.new),
        ],
        child: testMaterialApp(home: const Scaffold(body: NotesTool())),
      ),
    );
    // 首帧断言：_isLoading 初值 true，此刻_必然_处于骨架期。
    expect(find.byType(SparkleSkeleton), findsWidgets);
    expect(find.byType(ToolMetricRow), findsOneWidget);
    expect(find.byType(ToolSectionCard), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.byType(TextField), findsNothing);
  });

  testWidgets('骨架→内容过渡：prefs 到位后骨架退役、编辑器上屏',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          accessibilitySettingsProvider
              .overrideWith(_StubAccessibilitySettingsNotifier.new),
        ],
        child: testMaterialApp(home: const Scaffold(body: NotesTool())),
      ),
    );

    // 让 _loadNotes 的 prefs microtask 完成 → setState 出内容。
    await tester.pump();
    await tester.pump();

    expect(find.byType(SparkleSkeleton), findsNothing);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });
}
