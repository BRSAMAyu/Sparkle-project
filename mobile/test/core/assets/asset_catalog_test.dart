import 'dart:io' show File;

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/assets/asset_catalog.dart';

// V4-S04 验收3：
// - 资产引用经 AssetCatalog 间接层；替换芽/星光角色 = 只改映射，业务零改动。
// - 未批准（proposed）资源自动落程序生成占位，不进发布面。
// 验收2 佐证：占位 PNG 的 NN 整数倍 DPR 变体在文件层可校验。

void main() {
  setUp(AssetCatalog.debugReset);

  group('AssetCatalog PROPOSED → 占位回退', () {
    test('全部种子 key 当前无批准素材，resolve 落占位', () {
      for (final key in SparkleAssetKey.values) {
        final slot = AssetCatalog.slotFor(key);
        expect(
          slot.status,
          AssetApprovalStatus.proposed,
          reason: '${key.id} 账本无 APPROVED 素材时必须保持 proposed',
        );
        expect(slot.showsPlaceholder, isTrue);
        expect(AssetCatalog.resolve(key), slot.placeholderPath);
        expect(AssetCatalog.resolve(key), startsWith('assets/placeholders/'));
      }
    });

    test('resolve 永不返回空/真实未批准素材路径', () {
      expect(AssetCatalog.resolve(SparkleAssetKey.seedSprite), isNotEmpty);
      // 即便错误映射 approvedAssetPath，proposed 状态也必须忽略它。
      AssetCatalog.debugOverrideSlots({
        SparkleAssetKey.seedSprite: const AssetSlot(
          key: SparkleAssetKey.seedSprite,
          status: AssetApprovalStatus.proposed,
          approvedAssetPath: 'assets/sprites/unapproved_seed.png',
          placeholderPath: 'assets/placeholders/placeholder_pixel_block.png',
        ),
      });
      expect(
        AssetCatalog.resolve(SparkleAssetKey.seedSprite),
        'assets/placeholders/placeholder_pixel_block.png',
        reason: '未批准资源必须自动落占位（验收3）',
      );
    });

    test('替换角色资源 = 只改映射，业务侧 API 不变（零业务协议改动）', () {
      final before = AssetCatalog.resolve(SparkleAssetKey.starlightSprite);
      AssetCatalog.debugOverrideSlots({
        SparkleAssetKey.starlightSprite: const AssetSlot(
          key: SparkleAssetKey.starlightSprite,
          status: AssetApprovalStatus.approved,
          approvedAssetPath: 'assets/sprites/starlight_v2.png',
          placeholderPath: 'assets/placeholders/placeholder_pixel_block.png',
        ),
      });
      final after = AssetCatalog.resolve(SparkleAssetKey.starlightSprite);
      expect(before, 'assets/placeholders/placeholder_pixel_block.png');
      expect(after, 'assets/sprites/starlight_v2.png');
      // 业务调用方式（resolve/slotFor/PixelAssetImage）保持不变。
      expect(
        AssetCatalog.slotFor(SparkleAssetKey.starlightSprite).showsPlaceholder,
        isFalse,
      );
    });
  });

  group('占位资源文件层校验（NN 整数倍 DPR 导出）', () {
    final mainPng = File('assets/placeholders/placeholder_pixel_block.png');

    test('占位主资源与其 2.0x/3.0x 变体存在于发布面声明目录', () {
      expect(mainPng.existsSync(), isTrue);
      expect(
        File('assets/placeholders/2.0x/placeholder_pixel_block.png').existsSync(),
        isTrue,
      );
      expect(
        File('assets/placeholders/3.0x/placeholder_pixel_block.png').existsSync(),
        isTrue,
      );
    });

    test('变体尺寸 = 主资源 × 精确整数倍（nearest-neighbor 导出不变量）', () {
      final base = readPngSize(mainPng);
      expect(base, isNotNull);
      final (bw, bh) = base!;
      const variants = [('2.0x', 2), ('3.0x', 3)];
      for (final entry in variants) {
        final size = readPngSize(
          File('assets/placeholders/${entry.$1}/placeholder_pixel_block.png'),
        );
        expect(size, isNotNull);
        final (w, h) = size!;
        expect(w, bw * entry.$2, reason: '${entry.$1} 宽非 NN 整数倍');
        expect(h, bh * entry.$2, reason: '${entry.$1} 高非 NN 整数倍');
      }
    });
  });
}
