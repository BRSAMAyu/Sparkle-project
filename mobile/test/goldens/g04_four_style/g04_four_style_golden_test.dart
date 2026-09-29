// V4-G04 · 家族关键面四风格确定性 golden 钉（CI 可失败）。
//
// 面 = 真实表面 + 确定性 seed（F05 判例）；比较 = B04 容差比较器
// （0.5% 分数口径带界，V3-FIX-383 钉死单位；跨机环境漂移实测 ~0.18%
// 落带内，真实回归 ≥0.6% 硬失败——「CI 可失败」由常态比对路径保证，
// 无 skip 门）。基线签发：`G04_GOLDEN_CAPTURE=true flutter test
// --update-goldens test/goldens/g04_four_style/`（仅基线机执行）。
//
// 钉面（G04 家族修复面代表性载体）：
// 1. 星图面（TiledSectorBackground + GalaxyNodePreviewCard，F05 starMap
//    face 同款真实组件）——G04 恒暗画布身份 + preview 卡修复墨载体；
// 2. 资料库屏（DocumentLibraryScreen 真实屏 + 冻结文档 seed）——hero 墨
//    随画布亮度 + 文件类型 glyph 语义槽收敛的修复载体。
// 各 × classic/paperDay/dusk/quiet 四档。
library;

import 'package:dio/dio.dart' as dio;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/data/repositories/document_library_repository.dart';
import 'package:sparkle/features/documents/presentation/screens/document_library_screen.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_background_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

import '../../core/design/style_preview/style_preview_test_harness.dart';
import '../../goldens/b04_visual_baseline/b04_harness.dart'
    show b04InstallTolerantComparator;
import '../../shared/i18n_test_helper.dart';

const List<PixelPreviewProfile> _kProfiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

void main() {
  setUpAll(b04InstallTolerantComparator);
  setUp(setUpI18nForTesting);
  setUp(() {
    // 资料库链路外围（auth 拦截链/连接状态）在测试 binding 下打桩
    //（G01 golden 宿主同款）：读令牌返回空，按离线路径降级，golden
    // 只钉渲染面。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      )
      ..setMockMethodCallHandler(
        const MethodChannel('dev.fluttercommunity.plus/connectivity_status'),
        (call) async => null,
      );
  });

  Future<void> pumpProfiled(
    WidgetTester tester,
    PixelPreviewProfile profile,
    Widget build(), {
    List<Override> overrides = const <Override>[],
  }) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
    final manager = await freshThemeManager();
    await manager.setPixelPreviewProfile(profile);
    await tester.pumpWidget(
      KeyedSubtree(
        key: ValueKey('g04-golden-${profile.name}'),
        child: AnimatedBuilder(
          animation: ThemeManager(),
          builder: (context, _) => ProviderScope(
            overrides: overrides,
            child: MaterialApp(
              debugShowCheckedModeBanner: false,
              theme: AppThemes.lightTheme,
              locale: const Locale('zh'),
              localizationsDelegates: const [
                AppLocalizations.delegate,
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              supportedLocales: AppLocalizations.supportedLocales,
              home: build(),
            ),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 300));
  }

  Widget starMapFace() => Scaffold(
        body: Center(
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                  child: const SizedBox(
                    height: 120,
                    width: double.infinity,
                    child: TiledSectorBackground(width: 720, height: 240),
                  ),
                ),
                GalaxyNodePreviewCard(
                  node: GalaxyNodeModel(
                    id: 'g04-node-1',
                    name: '特征值与对角化',
                    importance: 72,
                    sector: SectorEnum.cosmos,
                    isUnlocked: true,
                    masteryScore: 64,
                  ),
                  onFocus: () {},
                  onInspectConnections: () {},
                  onViewDetails: () {},
                  onStartReview: () {},
                ),
              ],
            ),
          ),
        ),
      );

  testWidgets('星图面 × 四风格 golden（基线机签发，常态容差比对）', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(720, 1280);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    for (final profile in _kProfiles) {
      await pumpProfiled(tester, profile, starMapFace);
      expect(tester.takeException(), isNull, reason: '$profile 渲染异常');
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/g04_starmap_face_${profile.name}.png'),
      );
    }
  });

  testWidgets('资料库屏 × 四风格 golden（hero/glyph 修复面载体）', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(750, 1600);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final seedDoc = DocumentLibraryItem.fromJson(<String, dynamic>{
      'id': 'g04-doc-1',
      'file_name': '线性代数讲义.pdf',
      'mime_type': 'application/pdf',
      'status': 'ready',
      'created_at': '2026-09-20T10:00:00Z',
    });

    for (final profile in _kProfiles) {
      await pumpProfiled(
        tester,
        profile,
        () => const DocumentLibraryScreen(),
        overrides: [
          sharedPreferencesProvider.overrideWithValue(
            await SharedPreferences.getInstance(),
          ),
          documentLibraryRepositoryProvider.overrideWithValue(
            _G04GoldenDocumentRepository(seedDoc),
          ),
          communityRepositoryProvider.overrideWithValue(
            _StubCommunityRepository(),
          ),
        ],
      );
      expect(tester.takeException(), isNull, reason: '$profile 渲染异常');
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/g04_document_library_${profile.name}.png'),
      );
    }
  });
}

/// 资料库替身（冻结 seed，单文档 ready 态；无网络面）。
class _G04GoldenDocumentRepository extends DocumentLibraryRepository {
  _G04GoldenDocumentRepository(this.seedDocument) : super(dio.Dio());

  final DocumentLibraryItem seedDocument;

  @override
  Future<List<DocumentLibraryItem>> listDocuments({
    int limit = 100,
    int offset = 0,
  }) async =>
      <DocumentLibraryItem>[seedDocument];

  @override
  Future<DocumentProcessingStatus?> getDocumentStatus(String fileId) async =>
      null;

  @override
  Future<List<DocumentGalaxyNode>> listDocumentNodes(String fileId) async =>
      const <DocumentGalaxyNode>[];

  @override
  Future<Map<String, String>> loadNodeSectorCodes() async =>
      const <String, String>{};

  @override
  Future<Map<String, DocumentCitationInsight>> loadCitationInsights({
    int maxConversations = 12,
  }) async =>
      const <String, DocumentCitationInsight>{};
}


class _StubCommunityRepository extends CommunityRepository {
  _StubCommunityRepository() : super(_UnusedApiClient());

  @override
  Future<List<GroupListItem>> getMyGroups() async => const <GroupListItem>[];
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
