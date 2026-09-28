import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_accessibility_service.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

import '../../../shared/i18n_test_helper.dart';

/// V4-U05 · 读屏语义通道如实后缀。
///
/// 卡面验收「不开特效仍理解全部信息」的读屏面：掌握度数字单独播报会把
/// 练习足迹/legacy 存量说成已掌握（D04：标签不能叫精通）——通道词跟随
/// 播报，检验状态不依赖视觉环标记也能读。每面一正一反：
/// - 正：verified/practiced 节点播报含对应通道词；
/// - 反：无通道数据节点播报「检验状态未知」，绝不播报「已独立检验」。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  GalaxyNodeModel nodeWith(Map<String, dynamic> extra) =>
      GalaxyNodeModel.fromJson({
        'id': 'node_1',
        'name': 'TCP 流量控制',
        'importance': 3,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 92,
        'study_count': 4,
        ...extra,
      });

  test('正例：verified 节点播报含「已独立检验」', () {
    final node = nodeWith(const {
      'user_status': {
        'mastery_evidence': {'capability_channel': 'verified'},
      },
    });
    final label =
        GalaxyAccessibilityService().getNodeSemanticLabel(node);
    expect(label, contains('掌握度 92'));
    expect(label, contains('已独立检验'));
  });

  test('正例：practiced 节点播报含「练习过，未检验」——高分存量不冒充已掌握', () {
    final node = nodeWith(const {
      'user_status': {
        'mastery_evidence': {'capability_channel': 'practiced'},
      },
    });
    final label =
        GalaxyAccessibilityService().getNodeSemanticLabel(node);
    expect(label, contains('练习过，未检验'));
    expect(label, isNot(contains('已独立检验')));
  });

  test('反例：无通道数据播报「检验状态未知」，绝不声称检验', () {
    final node = nodeWith(const {});
    final label =
        GalaxyAccessibilityService().getNodeSemanticLabel(node);
    expect(label, contains('检验状态未知'));
    expect(label, isNot(contains('已独立检验')));
  });
}
