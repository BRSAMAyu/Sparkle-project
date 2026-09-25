import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/settings/data/repositories/action_permission_repository.dart';
import 'package:sparkle/features/settings/presentation/widgets/action_auto_execute_section.dart';

import '../../../shared/i18n_test_helper.dart';

/// P-04 · 授权设置面（ActionAutoExecuteSection）headless 验收.
///
/// 覆盖（卡面 acceptance 的 mobile 投影面）：
/// 1. **状态投影诚实**：逐类别开关 = 服务端合成真值（master ∧ category）；
///    不可预授权类别显式标注（不藏在开关后面）；总开关未开有明确提示；
/// 2. **grant/revoke 转发**：开/关分别下发对应类别的 grant/revoke（真源在
///    引擎，UI 不本地合成授权），变更后重读真源刷新；
/// 3. **失败诚实**：422（不可授）→ 用户可懂提示，开关随重读回退，零乐观残留。
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  late _RecordingRepository repository;

  Widget host() => ProviderScope(
        overrides: [
          actionPermissionRepositoryProvider.overrideWithValue(repository),
        ],
        child: testMaterialApp(
          theme: ThemeData.light()
              .copyWith(extensions: [SparkleThemeExtension.light()]),
          home: const Scaffold(
            body: SingleChildScrollView(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: ActionAutoExecuteSection(),
              ),
            ),
          ),
        ),
      );

  ActionPermissionState stateFrom(
    List<Map<String, dynamic>> categories, {
    bool master = true,
  }) =>
      ActionPermissionState.fromJson(<String, dynamic>{
        'master_grant': master,
        'categories': categories,
      });

  Map<String, dynamic> category(
    String name, {
    bool eligible = true,
    bool allowed = false,
  }) =>
      <String, dynamic>{
        'category': name,
        'eligible': eligible,
        'allowed': allowed,
      };

  testWidgets('状态投影：合成真值上开关、不可授权标注、总开关提示', (tester) async {
    repository = _RecordingRepository()
      ..nextState = stateFrom([
        category('task.update_status', allowed: true),
        category('task.update_fields'),
        category('task.create_batch', eligible: false),
      ], master: false,);

    await tester.pumpWidget(host());
    await tester.pumpAndSettle();

    // 可授予类别逐项渲染：granted → on / 未授予 → off
    final switches = tester.widgetList<SwitchListTile>(
      find.byType(SwitchListTile),
    );
    final values = switches.map((s) => s.value).toList();
    expect(values, hasLength(2), reason: '仅 eligible 类别出开关');
    expect(values, contains(true));
    expect(values, contains(false));

    // 不可预授权类别显式标注 + 总开关未开提示（诚实呈现，不藏）
    expect(find.text('不可逆操作（如批量建任务、完成任务）不支持预授权'), findsOneWidget);
    expect(find.text('自动执行总开关未开启：当前任何类别都不会自动执行。'), findsOneWidget);
    // 类别人类标签（非裸命令域名）
    expect(find.text('任务状态调整（开始/暂停/恢复/卡住）'), findsOneWidget);
    expect(find.text('任务信息修改（标题/优先级等）'), findsOneWidget);
  });

  testWidgets('toggle 转发：开 → grant、关 → revoke，类别名精确', (tester) async {
    repository = _RecordingRepository()
      ..nextState = stateFrom([
        category('task.update_status', allowed: true),
        category('task.update_fields'),
      ]);

    await tester.pumpWidget(host());
    await tester.pumpAndSettle();

    // 开「任务信息修改」→ grant(task.update_fields)
    await tester.tap(find.text('任务信息修改（标题/优先级等）'));
    await tester.pumpAndSettle();
    expect(repository.granted, ['task.update_fields']);
    expect(repository.revoked, isEmpty);
    // 重读真源后开关刷新为 on（stateful fake 已翻转 allowed）
    final grantedTile = tester.widget<SwitchListTile>(
      find.widgetWithText(SwitchListTile, '任务信息修改（标题/优先级等）'),
    );
    expect(grantedTile.value, isTrue);

    // 关「任务状态调整」→ revoke(task.update_status)
    await tester.tap(find.text('任务状态调整（开始/暂停/恢复/卡住）'));
    await tester.pumpAndSettle();
    expect(repository.granted, ['task.update_fields']);
    expect(repository.revoked, ['task.update_status']);
  });

  testWidgets('422 拒绝诚实呈现：SnackBar + 重读回退（零乐观残留）', (tester) async {
    repository = _RecordingRepository()
      ..nextState = stateFrom([
        category('task.update_fields'),
      ])
      ..grantException = DioException(
        requestOptions: RequestOptions(path: '/action-permissions'),
        response: Response<void>(
          requestOptions: RequestOptions(path: '/action-permissions'),
          statusCode: 422,
        ),
      );

    await tester.pumpWidget(host());
    await tester.pumpAndSettle();

    await tester.tap(find.text('任务信息修改（标题/优先级等）'));
    await tester.pumpAndSettle();

    expect(repository.granted, ['task.update_fields'], reason: '调用确实发生');
    expect(find.text('该类别不支持预授权'), findsOneWidget);
    // 重读回退：开关仍为 off（服务端真值），无乐观残留
    final tile = tester.widget<SwitchListTile>(
      find.widgetWithText(SwitchListTile, '任务信息修改（标题/优先级等）'),
    );
    expect(tile.value, isFalse);
  });
}

/// 记录型假仓库（测试夹具，非生产行为）：脚本化状态/失败/调用记录.
///
/// **stateful**：grant/revoke 翻转脚本态的 allowed——与服务端真源同构
/// （变更后 UI 重读得到新状态，测试断言「重读刷新」而非本地合成）。
class _RecordingRepository extends ActionPermissionRepository {
  _RecordingRepository() : super(_FakeApiClient());

  ActionPermissionState? nextState;
  DioException? grantException;
  DioException? revokeException;

  final granted = <String>[];
  final revoked = <String>[];

  @override
  Future<ActionPermissionState> getState() async {
    final state = nextState;
    if (state == null) {
      throw DioException(requestOptions: RequestOptions(path: '/x'));
    }
    return state;
  }

  @override
  Future<ActionPermissionState> grant(String category) async {
    granted.add(category);
    final exception = grantException;
    if (exception != null) {
      throw exception;
    }
    _flip(category, true);
    return getState();
  }

  @override
  Future<ActionPermissionState> revoke(String category) async {
    revoked.add(category);
    final exception = revokeException;
    if (exception != null) {
      throw exception;
    }
    _flip(category, false);
    return getState();
  }

  void _flip(String category, bool allowed) {
    final state = nextState;
    if (state == null) return;
    nextState = ActionPermissionState.fromJson(<String, dynamic>{
      'master_grant': state.masterGrant,
      'categories': state.categories
          .map(
            (c) => <String, dynamic>{
              'category': c.category,
              'eligible': c.eligible,
              'allowed': c.category == category ? allowed : c.allowed,
            },
          )
          .toList(),
    });
  }
}

class _FakeApiClient extends Fake implements ApiClient {}
