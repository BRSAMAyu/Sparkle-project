import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_board_models.dart';
import 'package:sparkle/features/community/data/repositories/mock_community_repository.dart';
import 'package:sparkle/features/community/data/repositories/squad_repository.dart';
import '../../../shared/i18n_test_helper.dart';

/// V4-U11 边界钉（差量举证：后端 AST/行为断言已在
/// tests/unit/test_community_shared_errors.py 等钉死，本套钉移动端面）：
///
/// 1. sprint 排序不混量纲（验收 2 反例面）：榜模型零 XP/光子/私人画像
///    词表；塞进 JSON 的 xp/photon_balance/persona 键被 fromJson 静默
///    丢弃（契约外字段不存在、不渲染、不透传）；
/// 2. 私人 Memory 不进群（隐私红线移动端面）：对外分享词表
///    [ShareableContentType] 无 memory/profile 族；错题卡模型零答案
///    字段；撤回端点按 share 定位（软删腿）；
/// 3. demo 诚实（验收 3 单人行动 + demo 标记）：demo 模式小队列表返回
///    真实空态不造假队；mock 仓库 seed 群名带「（演示）」后缀。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('sprint board keeps single metric vocabulary (no XP/photon/profile)',
      () {
    test('entry parses completion fields from whitelist projection', () {
      final entry = SquadLeaderboardEntry.fromJson(const {
        'rank': 2,
        'user_id': 'u9',
        'display_name': '阿黄',
        'task_total': 10,
        'task_completed': 4,
        'completion_rate': 0.4,
        'has_ledger_data': true,
        'percentile': 33,
      });
      expect(entry.rank, 2);
      expect(entry.completionRate, 0.4);
      expect(entry.hasLedgerData, isTrue);
      expect(entry.percentile, 33);
    });

    test('injected xp/photon/persona keys are silently dropped, never surfaced',
        () {
      // 反例钉：往 payload 里塞三种被禁量纲，模型不读、不存、不崩——
      // 排序口径只可能来自 completion/ledger 字段（后端服务层唯一排序键，
      // AST 断言 test_dcomm5_modules_import_scan_no_xp_photon 的移动端镜像）。
      final entry = SquadLeaderboardEntry.fromJson(const {
        'rank': 1,
        'user_id': 'u1',
        'completion_rate': 0.9,
        'has_ledger_data': true,
        'percentile': 80,
        'xp': 99999,
        'photon_balance': 88888,
        'photon_weekly': 777,
        'persona_profile': {
          'traits': ['grinder'],
        },
        'flame_power': 12345,
      });
      expect(entry.rank, 1);
      expect(entry.completionRate, 0.9);
      // 契约外字段没有归属：任务计数仍来自白名单键（缺失=0），塞入值无处落地。
      expect(entry.taskTotal, 0);
      expect(entry.taskCompleted, 0);
    });

    test('source pin: squad model files never reference xp/photon/persona',
        () {
      // 结构断言：移动端榜/小队模型源码零 XP/光子/私人画像词表——量纲
      // 混排不可能从渲染面发生（词表冻结，混入即测试红）。
      final files = [
        File('lib/features/community/data/models/squad_board_models.dart'),
        File('lib/features/community/data/models/squad_models.dart'),
      ];
      for (final file in files) {
        expect(file.existsSync(), isTrue, reason: '${file.path} missing');
        final source = file.readAsStringSync().toLowerCase();
        for (final banned in ['xp', 'photon', 'persona']) {
          expect(
            source.contains(banned),
            isFalse,
            reason: '${file.path} must not reference "$banned" '
                '(sprint board is completion-only, D20 红线)',
          );
        }
      }
    });
  });

  group('private memory never enters the group (mobile share vocabulary)', () {
    test('ShareableContentType has no private-memory/profile kind', () {
      final names = ShareableContentType.values.map((v) => v.name).toSet();
      // 隐私红线：私人记忆/画像族不可成为对外分享载体——对外可分享的
      // 只有成就/计划/任务/知识节点等用户主动选择的成果面。
      for (final banned in [
        'memory',
        'privateMemory',
        'profile',
        'memoryEntry',
        'contextReceipt',
      ]) {
        expect(
          names.contains(banned),
          isFalse,
          reason: 'ShareableContentType must not expose "$banned" '
              '(私人 Memory 不进群=硬边界)',
        );
      }
    });

    test('shared error card model has no answer fields (white-list projection)',
        () {
      final source = File(
        'lib/features/community/data/models/shared_error_models.dart',
      ).readAsStringSync();
      // 备考互助≠抄答案：契约不含答案字段——fromJson 不得读取答案键
      // （doc 注释里「不含 correct_answer」是排除声明，不算读取面）。
      for (final banned in [
        "json['correct_answer']",
        "json['user_answer']",
        "json['solution']",
      ]) {
        expect(
          source.contains(banned),
          isFalse,
          reason: 'shared error model fromJson must not read "$banned"',
        );
      }
      // 行为面：塞入答案字段也不被解析进任何字段。
      final entry = SharedErrorEntry.fromJson(const {
        'share_id': 's1',
        'sharer_id': 'u1',
        'error_id': 'e1',
        'subject_code': 'math',
        'mastery_level': 0.5,
        'review_count': 0,
        'correct_answer': 'x=42',
        'user_answer': 'x=7',
      });
      expect(entry.shareId, 's1');
      expect(entry.questionText, isNull);
      expect(entry.note, isNull);
    });

    test('retract endpoint path is scoped per share (soft-delete leg)', () {
      expect(
        ApiEndpoints.squadSharedErrorRetract('sq-1', 'share-9'),
        '/community/squads/sq-1/shared-errors/share-9',
      );
    });
  });

  group('demo mode is honest for squads (single-user full action, marked)',
      () {
    test('demo squad list returns real empty state, no fabricated squads',
        () async {
      final previous = DemoDataService.isDemoMode;
      DemoDataService.isDemoMode = true;
      addTearDown(() => DemoDataService.isDemoMode = previous);

      // 仓库直接构造即可（demo 分支在 API 调用前短路，无需网络）。
      final repository = SquadRepository(_UnusedApiClient());
      final squads = await repository.listMySquads();
      // demo 模式不造假队（S-03 同口径：seed/demo 一律明确标记或诚实为空）。
      expect(squads, isEmpty);
    });

    test('mock community repo seeds are explicitly marked as demo', () async {
      final repository = MockCommunityRepository();
      final groups = await repository.getMyGroups();
      expect(groups, isNotEmpty);
      for (final group in groups) {
        expect(
          group.name.contains('（演示）') || group.name.contains('(demo)'),
          isTrue,
          reason: 'demo seed group "${group.name}" must carry demo marking '
              '(不冒充真人/真实群)',
        );
      }
    });
  });
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
