import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/audio_asset_gate.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// V4-S02 · 合法资产门 ⇄ S04 许可账本对账（卡验收「合法资产才进 bundle，
/// 默认关闭」的反例钉面）。
///
/// 权威关系（不造第二权威）：唯一权威是 `mobile/assets/asset_ledger.json`
/// （S04 产物；打包面由 scripts/guards/check_asset_release_surface.py 的
/// L003/L004 拦截）。本文件消费账本原文逐键对账：
/// - 门内集合 == 账本 APPROVED∩ship_in_product 的 sfx+ambient 集（双向）；
/// - 反例钉：无许可（PROPOSED/未知）资产**必被拒**（缺省拒绝）；
/// - 服务面引用路径（提示音规格表 + 环境床枚举）全部持证。
///
/// 单边漂移即红：改账本不改编译集（或反之）→ 本测试失败。
void main() {
  // flutter test 的 CWD 是 mobile/，账本按仓库布局定位。
  final ledgerFile = File(
    '${Directory.current.path}/assets/asset_ledger.json',
  );
  final ledger = jsonDecode(ledgerFile.readAsStringSync())
      as Map<String, dynamic>;

  /// 从账本原文重算「许可音频集」（不信任任何编译期常量）。
  final ledgerLicensedAudio = <String>{
    for (final entry in (ledger['entries'] as List).cast<Map<String, dynamic>>())
      if (entry['status'] == 'APPROVED' &&
          entry['ship_in_product'] == true &&
          (entry['asset_id'] as String).startsWith('audio/') &&
          entry['kind'] != 'config' &&
          entry['kind'] != 'bgm_track')
        entry['asset_id'] as String,
  };

  group('S02 资产门 ⇄ 账本（APPROVED ∩ ship）', () {
    test('正·账本 APPROVED∩ship 的每个音频资产都在门内（账本→门）', () {
      expect(ledgerLicensedAudio, isNotEmpty);
      for (final assetId in ledgerLicensedAudio) {
        expect(
          AudioAssetGate.isLicensed(assetId),
          isTrue,
          reason: '账本已批准资产 $assetId 必须可播（门缺键 = 误伤合法资产）',
        );
      }
    });

    test('反演·门内每个键都在账本 APPROVED∩ship 集（门→账本，无私货）', () {
      for (final assetId in kLicensedAudioAssets) {
        expect(
          ledgerLicensedAudio.contains(assetId),
          isTrue,
          reason: '门内 $assetId 不在账本批准集 = 门自造权威（禁止）',
        );
      }
      expect(kLicensedAudioAssets.length, ledgerLicensedAudio.length);
    });
  });

  group('S02 反例钉 · 无许可资产被拦', () {
    test('PROPOSED 的 curated BGM（商用许可未证实）必被拒', () {
      final proposedBgm = (ledger['entries'] as List)
          .cast<Map<String, dynamic>>()
          .where((e) => e['status'] == 'PROPOSED' && e['ship_in_product'] == false)
          .map((e) => e['asset_id'] as String)
          .where((id) => id.startsWith('audio/'))
          .toList(growable: false);
      expect(proposedBgm, isNotEmpty, reason: '账本须保有 PROPOSED 反例样本');

      for (final assetId in proposedBgm.take(3)) {
        expect(
          AudioAssetGate.isLicensed(assetId),
          isFalse,
          reason: '无许可资产 $assetId 必须被运行时门拦下（fallback=silent）',
        );
        expect(
          AudioAssetGate.licensedPathOrNull(assetId),
          isNull,
          reason: '未许可路径不得被放行',
        );
      }
    });

    test('未知路径缺省拒绝（未证实许可就不播出）', () {
      expect(AudioAssetGate.isLicensed('audio/ui/never_registered.ogg'), isFalse);
      expect(AudioAssetGate.isLicensed('audio/bgm/some_random_track.m4a'), isFalse);
      expect(AudioAssetGate.licensedPathOrNull(''), isNull);
    });
  });

  group('S02 服务面引用路径全部持证', () {
    test('提示音规格表引用的每个资产都在许可集（lib 面无未持证引用）', () {
      final referenced = <String>{
        for (final event in SensoryFeedbackEvent.values)
          SensoryFeedbackService.debugAssetPathFor(event),
      };
      expect(referenced, isNotEmpty);
      for (final path in referenced) {
        expect(
          AudioAssetGate.isLicensed(path),
          isTrue,
          reason: '提示音规格表引用 $path 未持证——先入账本审批，再进规格表',
        );
      }
    });
  });
}
