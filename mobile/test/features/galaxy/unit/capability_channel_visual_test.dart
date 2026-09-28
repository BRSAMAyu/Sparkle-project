import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/domain/capability_channel.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// V4-U05 · 星图能力通道视觉分层（纯函数面）。
///
/// 卡面验收钉（每面一正一反）：
/// - 「轨迹视觉区分 D04 四态」：verified/practiced/non_human/trace_only
///   各有互异的环标记与亮度档（正）；unknown/无数据 fail-closed 不声称
///   检验（反）。
/// - 「PRACTICED 星绝不渲染为已掌握亮度」：legacy/练习高分存量（92 分）
///   封顶 SHINING 档，无光晕无脉冲（反例钉）；verified 同分可达掌握档
///   （正例对照）。
/// - 「不开特效仍理解全部信息」：通道身份由环标记形状承载，封顶档
///   glowAlpha=0 时标记仍互异（形状区分不依赖特效）。
/// - 「无数据不造进度」：缺 user_status 快照 → unknown + 无投影版本，
///   绝不编造检验状态或版本号（反）。
void main() {
  group('GalaxyCapabilityChannel.fromWire（D04 词表消费）', () {
    test('四值线值逐一如实解析（正）', () {
      expect(
        GalaxyCapabilityChannel.fromWire('verified'),
        GalaxyCapabilityChannel.verified,
      );
      expect(
        GalaxyCapabilityChannel.fromWire('practiced'),
        GalaxyCapabilityChannel.practiced,
      );
      expect(
        GalaxyCapabilityChannel.fromWire('non_human'),
        GalaxyCapabilityChannel.nonHuman,
      );
      expect(
        GalaxyCapabilityChannel.fromWire('trace_only'),
        GalaxyCapabilityChannel.traceOnly,
      );
    });

    test('未知线值/缺数据 fail-closed 归 unknown，绝不声称检验（反）', () {
      expect(
        GalaxyCapabilityChannel.fromWire('super_verified'),
        GalaxyCapabilityChannel.unknown,
      );
      expect(
        GalaxyCapabilityChannel.fromWire(null),
        GalaxyCapabilityChannel.unknown,
      );
      expect(
        GalaxyCapabilityChannel.unknown.allowsMasteredBrightness,
        isFalse,
        reason: 'unknown 通道绝不允许掌握档视觉',
      );
    });
  });

  group('resolveGalaxyStarVisualStyle · PRACTICED≠已掌握亮度（核心反例钉）', () {
    test('反例钉：practiced 92 分存量封顶 SHINING 档，零光晕零脉冲', () {
      final style = resolveGalaxyStarVisualStyle(
        isUnlocked: true,
        masteryScore: 92,
        channel: GalaxyCapabilityChannel.practiced,
      );
      expect(
        style.fillAlpha,
        kGalaxyUnverifiedFillAlphaCap,
        reason: '练习星亮度封顶 SHINING 档（0.82），绝不进掌握档（0.94）',
      );
      expect(style.fillAlpha, lessThan(0.94));
      expect(style.masteryRingAlpha, kGalaxyUnverifiedRingAlphaCap);
      expect(style.glowAlpha, 0, reason: '掌握档光晕对非 verified 恒零');
      expect(
        style.allowMasteredPulse,
        isFalse,
        reason: '掌握档呼吸脉冲是「已掌握」庆祝语言，练习星绝不使用',
      );
      expect(style.allowMasteredHalo, isFalse);
    });

    test('正例对照：verified 92 分（独立检验）可达掌握档', () {
      final style = resolveGalaxyStarVisualStyle(
        isUnlocked: true,
        masteryScore: 92,
        channel: GalaxyCapabilityChannel.verified,
      );
      expect(style.fillAlpha, 0.94);
      expect(style.masteryRingAlpha, 0.72);
      expect(style.glowAlpha, 0.18);
      expect(style.allowMasteredPulse, isTrue);
      expect(style.allowMasteredHalo, isTrue);
    });

    for (final channel in GalaxyCapabilityChannel.values) {
      final label = channel.name;
      if (channel == GalaxyCapabilityChannel.verified) {
        continue;
      }
      test('$label 高分存量同样封顶（四态逐一钉）', () {
        final style = resolveGalaxyStarVisualStyle(
          isUnlocked: true,
          masteryScore: 95,
          channel: channel,
        );
        expect(
          style.fillAlpha,
          lessThanOrEqualTo(0.82),
          reason: '$label 不得进掌握档亮度',
        );
        expect(style.glowAlpha, 0);
        expect(style.allowMasteredPulse, isFalse);
        expect(style.allowMasteredHalo, isFalse);
      });
    }
  });

  group('resolveGalaxyStarVisualStyle · 四态环标记（不开特效可读）', () {
    test('环标记四态互异（正）：双环=verified / 单环=practiced / 虚线=痕迹面', () {
      GalaxyStarRingMark markOf(GalaxyCapabilityChannel channel) =>
          resolveGalaxyStarVisualStyle(
            isUnlocked: true,
            masteryScore: 50,
            channel: channel,
          ).ringMark;

      expect(
        markOf(GalaxyCapabilityChannel.verified),
        GalaxyStarRingMark.double,
      );
      expect(
        markOf(GalaxyCapabilityChannel.practiced),
        GalaxyStarRingMark.single,
      );
      expect(
        markOf(GalaxyCapabilityChannel.traceOnly),
        GalaxyStarRingMark.dashed,
      );
      expect(
        markOf(GalaxyCapabilityChannel.nonHuman),
        GalaxyStarRingMark.dashed,
      );
      expect(
        markOf(GalaxyCapabilityChannel.unknown),
        GalaxyStarRingMark.dashed,
        reason: '无数据与痕迹同用虚线（不确定性可视化），但绝不双环',
      );
    });

    test('反例：封顶档零特效时形状标记仍在（特效不承载通道信息）', () {
      final style = resolveGalaxyStarVisualStyle(
        isUnlocked: true,
        masteryScore: 92,
        channel: GalaxyCapabilityChannel.practiced,
      );
      expect(style.glowAlpha, 0);
      expect(
        style.ringMark,
        isNot(GalaxyStarRingMark.none),
        reason: '光晕为零时通道身份仍由环标记形状承载',
      );
    });

    test('锁定节点无通道标记（沿用虚线问号语言，不叠环）', () {
      final style = resolveGalaxyStarVisualStyle(
        isUnlocked: false,
        masteryScore: 0,
        channel: GalaxyCapabilityChannel.verified,
      );
      expect(style.ringMark, GalaxyStarRingMark.none);
      expect(style.fillAlpha, 0.22);
      expect(style.allowMasteredPulse, isFalse);
    });
  });

  group('GalaxyNodeCapabilityEvidence.fromJson（图快照消费）', () {
    test('正例：user_status 全量解析（通道/版本/证据计数/legacy 旗）', () {
      final evidence = GalaxyNodeCapabilityEvidence.fromJson(const {
        'id': 'n1',
        'user_status': {
          'mastery_score': 92,
          'projection_version': 7,
          'mastery_evidence': {
            'capability_channel': 'verified',
            'evidence_count': 3,
            'is_legacy_estimate': false,
          },
        },
      });
      expect(evidence.channel, GalaxyCapabilityChannel.verified);
      expect(evidence.hasChannelData, isTrue);
      expect(evidence.projectionVersion, 7);
      expect(evidence.evidenceCount, 3);
      expect(evidence.isLegacyEstimate, isFalse);
      expect(evidence.claimsVerification, isTrue);
    });

    test('反例：缺 user_status（gateway gRPC 形状/旧缓存）诚实降级，无编造', () {
      final evidence = GalaxyNodeCapabilityEvidence.fromJson(const {
        'id': 'n1',
        'mastery_score': 92,
      });
      expect(evidence.channel, GalaxyCapabilityChannel.unknown);
      expect(evidence.hasChannelData, isFalse);
      expect(evidence.projectionVersion, isNull, reason: '无数据不造版本号');
      expect(evidence.claimsVerification, isFalse);
    });

    test('反例：通道线值漂移（词表外）fail-closed 为 unknown', () {
      final evidence = GalaxyNodeCapabilityEvidence.fromJson(const {
        'user_status': {
          'projection_version': 3,
          'mastery_evidence': {
            'capability_channel': 'mastered_v2',
          },
        },
      });
      expect(evidence.channel, GalaxyCapabilityChannel.unknown);
      expect(evidence.hasChannelData, isTrue);
      expect(evidence.claimsVerification, isFalse);
      expect(evidence.projectionVersion, 3, reason: '版本字段独立于通道词表照实透传');
    });
  });

  group('GalaxyNodeModel 消费（端到端 fromJson）', () {
    test('正例：图响应 user_status.mastery_evidence 进节点模型', () {
      final node = GalaxyNodeModel.fromJson(const {
        'id': 'node_1',
        'name': 'TCP 流量控制',
        'importance': 3,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 92,
        'user_status': {
          'mastery_evidence': {'capability_channel': 'practiced'},
          'projection_version': 11,
        },
      });
      expect(node.capability.channel, GalaxyCapabilityChannel.practiced);
      expect(node.capability.projectionVersion, 11);
    });

    test('正例：copyWith 保留能力证据投影', () {
      final node = GalaxyNodeModel.fromJson(const {
        'id': 'node_1',
        'name': 'TCP 流量控制',
        'importance': 3,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 50,
        'user_status': {
          'mastery_evidence': {'capability_channel': 'verified'},
          'projection_version': 2,
        },
      });
      final moved = node.copyWith(positionX: 12.0, positionY: 8.0);
      expect(moved.capability.channel, GalaxyCapabilityChannel.verified);
      expect(moved.capability.projectionVersion, 2);
    });

    test('反例：无 user_status 的节点 → unknown（视觉按未检验渲染）', () {
      final node = GalaxyNodeModel.fromJson(const {
        'id': 'node_2',
        'name': '孤立节点',
        'importance': 1,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 99,
      });
      expect(node.capability.claimsVerification, isFalse);
      final style = resolveGalaxyStarVisualStyle(
        isUnlocked: node.isUnlocked,
        masteryScore: node.masteryScore,
        channel: node.capability.channel,
      );
      expect(
        style.fillAlpha,
        lessThanOrEqualTo(0.82),
        reason: '99 分存量在无通道数据时也不渲染掌握档亮度',
      );
    });
  });
}
