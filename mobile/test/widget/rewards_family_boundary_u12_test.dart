import 'dart:io';

import 'package:confetti/confetti.dart' show ConfettiWidget;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

import '../shared/i18n_test_helper.dart';

/// V4-U12 家族边界钉（SCREEN_FAMILIES「小队/自我锚/光子/成就」+ MODULE_MATRIX
/// leaderboard/photon/achievement/shop 四行处置）。
///
/// - 可关闭庆祝（正反判别对）：低刺激档下家族最强庆祝面（成就解锁弹窗的
///   彩带粒子）被真实抑制；正常档呈现——证明开关真生效而非装饰位。
/// - HIDDEN 商店不打开（B01/MODULE_MATRIX「维持 HIDDEN」）：shop 路由在
///   奖励域四家族（photon/leaderboard/achievement）零入口、零推广位。
/// - 不以 flame_level 冒充付费身份（D-COMM R1/R2）：奖励域四家族源码
///   零 flameLevel 引用；全 mobile 零「entitlement 派生自 flameLevel」同现。
/// - 核心记忆纠正/隐私不收费（付费墙反例钉）：memory 域源码零 photon/
///   付费/权益门词表，纠正面走 /memory/provenance 免费链路。
void main() {
  setUp(setUpI18nForTesting);

  group('可关闭庆祝（庆祝开关真实生效）', () {
    testWidgets('正例：正常档下 rare 成就弹窗呈现彩带粒子（庆祝存在）', (tester) async {
      await _pumpUnlockDialog(tester, lowStimulus: false);

      expect(find.byType(AchievementUnlockDialog), findsOneWidget);
      expect(find.byType(ConfettiWidget), findsOneWidget);
    });

    testWidgets('反例钉：低刺激档下同一弹窗彩带粒子被抑制（庆祝可关闭）', (tester) async {
      await _pumpUnlockDialog(tester, lowStimulus: true);

      expect(find.byType(AchievementUnlockDialog), findsOneWidget);
      expect(
        find.byType(ConfettiWidget),
        findsNothing,
        reason: '低刺激档必须真实关闭庆祝粒子（SparkleConfetti 整体短路）',
      );
    });

    test('光子/自我锚/流水面零不可关庆祝源（无直连彩带/粒子引用）', () {
      final offenders = <String>[];
      for (final dir in ['lib/features/photon', 'lib/features/leaderboard']) {
        _walkDartFiles(Directory(dir)).forEach((file) {
          final source = file.readAsStringSync();
          if (source.contains('SparkleConfetti') ||
              source.contains('ConfettiWidget')) {
            offenders.add(file.path);
          }
        });
      }
      expect(offenders, isEmpty);
    });
  });

  group('HIDDEN 商店不打开（B01 portfolio 语义）', () {
    test('奖励域四家族零 shop 入口（路由引用/深链推广零命中）', () {
      final offenders = <String>[];
      for (final dir in [
        'lib/features/photon',
        'lib/features/leaderboard',
        'lib/features/achievement',
        'lib/features/memory',
      ]) {
        _walkDartFiles(Directory(dir)).forEach((file) {
          final code = file
              .readAsLinesSync()
              .map((line) => line.split('//').first)
              .join('\n');
          if (code.contains('ShopRoutes') || code.contains("'/shop'")) {
            offenders.add(file.path);
          }
        });
      }
      expect(
        offenders,
        isEmpty,
        reason: 'shop 维持 HIDDEN：奖励域不得到商店的任何新入口/推广位',
      );
    });
  });

  group('不以 flame_level 冒充付费身份（D-COMM R1/R2）', () {
    test('奖励域四家族源码零 flameLevel 引用；全 mobile 零权益派生同现', () {
      final offenders = <String>[];
      for (final dir in [
        'lib/features/photon',
        'lib/features/leaderboard',
        'lib/features/achievement',
        'lib/features/shop',
      ]) {
        _walkDartFiles(Directory(dir)).forEach((file) {
          final code = file
              .readAsLinesSync()
              .map((line) => line.split('//').first)
              .join('\n');
          if (code.contains('flameLevel') || code.contains('flame_level')) {
            offenders.add(file.path);
          }
        });
      }
      expect(
        offenders,
        isEmpty,
        reason: '付费/权益语义与 flame_level 视觉等级严格分离',
      );

      // 全 mobile 扫描：任何一行同时出现 entitlement 与 flameLevel
      // （派生/赋值同现）即违规——权益唯一判据是服务端 entitlement 列。
      final derivation = <String>[];
      _walkDartFiles(Directory('lib')).forEach((file) {
        for (final line in file.readAsLinesSync()) {
          final codeOnly = line.split('//').first;
          if (codeOnly.contains('entitlement') &&
              codeOnly.contains('flameLevel')) {
            derivation.add('${file.path}: $codeOnly');
          }
        }
      });
      expect(derivation, isEmpty);
    });
  });

  group('核心记忆纠正/隐私不收费（付费墙反例钉）', () {
    test('memory 域源码零 photon/付费/权益门词表；纠正走 /memory/provenance 免费链路', () {
      final offenders = <String>[];
      _walkDartFiles(Directory('lib/features/memory')).forEach((file) {
        final code = file
            .readAsLinesSync()
            .map((line) => line.split('//').first)
            .join('\n');
        if (code.contains('photon') ||
            code.contains('Photon') ||
            code.contains('purchase') ||
            code.contains('entitlement') ||
            code.contains('paywall') ||
            code.contains('付费')) {
          offenders.add(file.path);
        }
      });
      expect(
        offenders,
        isEmpty,
        reason: '核心记忆纠正/隐私操作零付费门（MASTER_DESIGN §7 商业红线）',
      );

      // 正例锚：纠正/忘记/scope 的唯一写链路 = memory provenance 仓库的
      // /memory/provenance 路径族（与 photon 结算面零交集）。
      final repoSource = File(
        'lib/features/memory/data/memory_provenance_repository.dart',
      ).readAsStringSync();
      expect(repoSource.contains('/memory/provenance'), isTrue);
    });
  });
}

// ========== harness ==========

/// 成就解锁弹窗泵装（rare：家族内最强庆祝面）。
///
/// [lowStimulus] 控制 EmotionResponsiveTheme 注入档位——低刺激 =
/// EmotionResponsiveConfig.lowStimulus()（设置「持续低刺激」的真实效果）。
Future<void> _pumpUnlockDialog(
  WidgetTester tester, {
  required bool lowStimulus,
}) async {
  final emotionConfig = lowStimulus
      ? const EmotionResponsiveConfig.lowStimulus()
      : const EmotionResponsiveConfig.normal();

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        apiClientProvider.overrideWithValue(_ThrowingApiClient()),
        releaseFlagsProvider.overrideWith(
          (ref) => ReleaseFlagsNotifier(_ThrowingApiClient())
            ..seed(const ReleaseFlags()),
        ),
      ],
      child: EmotionResponsiveTheme(
        config: emotionConfig,
        child: testMaterialApp(
          home: Builder(
            builder: (context) => Scaffold(
              body: Center(
                child: FilledButton(
                  onPressed: () => showDialog<void>(
                    context: context,
                    builder: (_) => AchievementUnlockDialog(
                      event: _rareEvent(),
                    ),
                  ),
                  child: const Text('open'),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  // 定长泵进：弹窗转场 600ms；庆祝粒子为循环动效，不做 pumpAndSettle。
  await tester.pump(const Duration(milliseconds: 700));
}

AchievementUnlockEvent _rareEvent() => AchievementUnlockEvent(
      achievementId: 'u12_celebration_probe',
      name: '稀有成就',
      rarity: AchievementRarity.rare,
      unlockedAt: DateTime(2026, 9, 28, 12),
      gloryLines: const <String>['一次真实的独立检验通过。'],
    );

/// 测试封闭：旗值拉取快速失败（无网络）。
class _ThrowingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in u12 boundary test');
}

Iterable<File> _walkDartFiles(Directory dir) sync* {
  if (!dir.existsSync()) {
    return;
  }
  for (final entity in dir.listSync(recursive: true)) {
    if (entity is File && entity.path.endsWith('.dart')) {
      yield entity;
    }
  }
}
