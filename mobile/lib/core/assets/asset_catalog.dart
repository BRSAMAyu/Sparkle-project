/// V4-S04 资产 key → 资源 间接层（单一入口）。
///
/// 设计合同（v4/02_design/ACCESSIBILITY_ASSETS.md）：
/// - 业务/UI 只引用 [SparkleAssetKey]，永不硬编码 `assets/` 路径；
///   替换芽/星光角色资源 = 只改本文件 [kAssetSlots] 映射，业务协议零改动。
/// - 未批准（PROPOSED / 权利未知）资源绝不返回真实路径，
///   [AssetCatalog.resolve] 自动落到程序生成的占位资源（最小像素方块），
///   占位文件由 scripts/devtools/generate_placeholder_sprites.py 生成并可复现。
/// - 权威账本：mobile/assets/asset_ledger.json；
///   守卫 scripts/guards/check_asset_release_surface.py 校验本文件与账本一致
///   （路径必须账本 APPROVED，越过硬编码即 L007/L008 红）。
///
/// 像素资产渲染规约：占位/像素类资产一律 [FilterQuality.none]（最近邻采样），
/// DPR 变体由 Flutter 按 devicePixelRatio 自动选择 assets/placeholders/2.0x|3.0x/
/// 的整数倍导出（nearest-neighbor 生成，见 DPR 守卫 P002/P003）。
library;

import 'dart:io' show File;
import 'dart:typed_data' show ByteData;

import 'package:flutter/widgets.dart';

/// 资产 slot 的语义 key（导航种子集：芽/星光/环境背景；随 F02 像素组件按需扩充）。
enum SparkleAssetKey {
  seedSprite('seed_sprite', '成长芽角色'),
  starlightSprite('starlight_sprite', '星光角色'),
  environmentBackdrop('environment_backdrop', '环境背景图');

  const SparkleAssetKey(this.id, this.semanticLabel);

  /// 稳定 id（日志/账本对账用，不参与资源寻址）。
  final String id;

  /// 无障碍语义标签（占位显示时同样生效）。
  final String semanticLabel;
}

/// 账本审批状态（与 asset_ledger.json 的 status 对齐，经守卫校验）。
enum AssetApprovalStatus {
  /// 已批准，可直接进发布面。
  approved,

  /// 未批准（来源/权利未确认），resolve 必须落占位。
  proposed,
}

@immutable
class AssetSlot {
  const AssetSlot({
    required this.key,
    required this.status,
    required this.placeholderPath,
    this.approvedAssetPath,
    this.fallbackLabel = 'placeholder_pixel_block',
  });

  final SparkleAssetKey key;

  /// 账本 status 镜像；PROPOSED 时 [resolve] 忽略 approvedAssetPath。
  final AssetApprovalStatus status;

  /// 已批准真实资源（账本 APPROVED 才允许填；PROPOSED 保持 null）。
  final String? approvedAssetPath;

  /// 程序生成占位（最小像素方块，NN DPR 变体齐全）。
  final String placeholderPath;

  /// 账本 fallback 字段镜像（六要素之一）。
  final String fallbackLabel;

  String get effectivePath => status == AssetApprovalStatus.approved
      ? (approvedAssetPath ?? placeholderPath)
      : placeholderPath;

  bool get showsPlaceholder => effectivePath == placeholderPath;
}

/// 单一权威映射表：替换角色 = 只改这里（验收3：业务协议零改动）。
const Map<SparkleAssetKey, AssetSlot> kAssetSlots = {
  // 芽/星光真实原创资产归后续卡生产；账本当前无 APPROVED sprite，
  // 全部走占位（PROPOSED 语义由账本承载，此处以 proposed 保守默认）。
  SparkleAssetKey.seedSprite: AssetSlot(
    key: SparkleAssetKey.seedSprite,
    status: AssetApprovalStatus.proposed,
    placeholderPath: 'assets/placeholders/placeholder_pixel_block.png',
  ),
  SparkleAssetKey.starlightSprite: AssetSlot(
    key: SparkleAssetKey.starlightSprite,
    status: AssetApprovalStatus.proposed,
    placeholderPath: 'assets/placeholders/placeholder_pixel_block.png',
  ),
  SparkleAssetKey.environmentBackdrop: AssetSlot(
    key: SparkleAssetKey.environmentBackdrop,
    status: AssetApprovalStatus.proposed,
    placeholderPath: 'assets/placeholders/placeholder_pixel_block.png',
  ),
};

class AssetCatalog {
  const AssetCatalog._();

  static Map<SparkleAssetKey, AssetSlot> _slots = _copyOf(kAssetSlots);

  static Map<SparkleAssetKey, AssetSlot> _copyOf(
    Map<SparkleAssetKey, AssetSlot> source,
  ) =>
      Map<SparkleAssetKey, AssetSlot>.unmodifiable(source);

  /// 资产 key → 实际资源路径。未批准资源自动落占位，绝不返回真实素材。
  static String resolve(SparkleAssetKey key) {
    final slot = _slots[key];
    if (slot == null) {
      return kAssetSlots.values.first.placeholderPath;
    }
    return slot.effectivePath;
  }

  static AssetSlot slotFor(SparkleAssetKey key) =>
      _slots[key] ?? kAssetSlots.values.first;

  /// 测试专用：模拟“替换角色资源”——只改映射，业务零感知。
  @visibleForTesting
  static void debugOverrideSlots(Map<SparkleAssetKey, AssetSlot> override) {
    _slots = _copyOf(override);
  }

  @visibleForTesting
  static void debugReset() {
    _slots = _copyOf(kAssetSlots);
  }
}

/// 像素资产统一渲染入口：最近邻采样（FilterQuality.none），
/// 禁止双线性/mental 光滑破坏像素边界（DPR 守卫 P003 的代码面声明）。
class PixelAssetImage extends StatelessWidget {
  const PixelAssetImage({
    required this.assetKey,
    super.key,
    this.width,
    this.height,
    this.fit = BoxFit.contain,
    this.semanticLabel,
  });

  final SparkleAssetKey assetKey;
  final double? width;
  final double? height;
  final BoxFit fit;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final slot = AssetCatalog.slotFor(assetKey);
    return Image.asset(
      AssetCatalog.resolve(assetKey),
      width: width,
      height: height,
      fit: fit,
      filterQuality: FilterQuality.none,
      semanticLabel: semanticLabel ?? slot.key.semanticLabel,
    );
  }
}

/// 测试/守卫辅助：IHDR 尺寸读取（校验 NN 整数倍导出）。
(int, int)? readPngSize(File file) {
  final bytes = file.readAsBytesSync();
  const pngMagic = <int>[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
  if (bytes.length < 24) {
    return null;
  }
  for (var i = 0; i < pngMagic.length; i++) {
    if (bytes[i] != pngMagic[i]) {
      return null;
    }
  }
  final view = ByteData.view(bytes.buffer, bytes.offsetInBytes, bytes.lengthInBytes);
  return (view.getUint32(16), view.getUint32(20));
}
