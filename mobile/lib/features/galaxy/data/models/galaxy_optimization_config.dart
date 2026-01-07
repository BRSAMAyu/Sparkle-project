
enum GalaxyPerformanceTier {
  lite,
  standard,
  ultra,
}

/// 星图性能优化配置
class GalaxyOptimizationConfig {
  const GalaxyOptimizationConfig({
    required this.tier,
    required this.enableShader,
    required this.enableGlow,
    required this.enableBlur,
    required this.enableParticles,
    required this.enableTransitionAnimations,
    required this.maxParticleCount,
    required this.targetFps,
    required this.renderBackgroundImages,
    required this.lodThresholds,
    required this.enableAntiAlias,
  });

  final GalaxyPerformanceTier tier;
  
  // 渲染特效开关
  final bool enableShader;
  final bool enableGlow;
  final bool enableBlur;
  final bool enableParticles;
  final bool enableTransitionAnimations;
  final bool enableAntiAlias;
  
  // 数量限制
  final int maxParticleCount;
  final int targetFps;
  
  // 绘制策略
  final bool renderBackgroundImages; // Lite模式下可能简化背景

  // LOD 阈值 (全局统一)
  final GalaxyLODThresholds lodThresholds;

  static const GalaxyLODThresholds _defaultLOD = GalaxyLODThresholds();

  /// Lite (基础版) - 目标 30 FPS
  /// RAM < 4GB, CPU < 6核
  static const GalaxyOptimizationConfig lite = GalaxyOptimizationConfig(
    tier: GalaxyPerformanceTier.lite,
    enableShader: false,
    enableGlow: false,
    enableBlur: false,
    enableParticles: false,
    enableTransitionAnimations: false, // 极简过渡
    enableAntiAlias: false,
    maxParticleCount: 0,
    targetFps: 30,
    renderBackgroundImages: false, // 简化背景
    lodThresholds: _defaultLOD,
  );

  /// Standard (标准版) - 目标 60 FPS
  /// RAM 4-8GB, 中端芯片
  static const GalaxyOptimizationConfig standard = GalaxyOptimizationConfig(
    tier: GalaxyPerformanceTier.standard,
    enableShader: true, // 简化版Shader (Painter内部处理)
    enableGlow: true, // 仅高亮节点
    enableBlur: true, // 仅静态层
    enableParticles: true,
    enableTransitionAnimations: true,
    enableAntiAlias: true,
    maxParticleCount: 20,
    targetFps: 60,
    renderBackgroundImages: true,
    lodThresholds: _defaultLOD,
  );

  /// Ultra (极致版) - 目标 60/120 FPS
  /// RAM > 8GB, 旗舰芯片
  static const GalaxyOptimizationConfig ultra = GalaxyOptimizationConfig(
    tier: GalaxyPerformanceTier.ultra,
    enableShader: true, // 全特效
    enableGlow: true, // 全局动态辉光
    enableBlur: true, // 全局高斯模糊
    enableParticles: true,
    enableTransitionAnimations: true, // 物理弹簧
    enableAntiAlias: true,
    maxParticleCount: 100,
    targetFps: 120, // 尝试高刷
    renderBackgroundImages: true,
    lodThresholds: _defaultLOD,
  );
  
  /// 获取指定Tier的配置
  static GalaxyOptimizationConfig fromTier(GalaxyPerformanceTier tier) {
    switch (tier) {
      case GalaxyPerformanceTier.lite:
        return lite;
      case GalaxyPerformanceTier.standard:
        return standard;
      case GalaxyPerformanceTier.ultra:
        return ultra;
    }
  }
}

/// LOD (Level of Detail) 阈值定义
/// 全局统一，不随Tier改变
class GalaxyLODThresholds {
  const GalaxyLODThresholds({
    this.l0_universe = 0.2,
    this.l1_galaxy = 0.4,
    this.l2_sector = 0.6,
    this.l3_nebula = 0.8,
  });

  // L0 < 0.2: Universe (仅质心)
  final double l0_universe;
  
  // 0.2 <= L1 < 0.4: Galaxy (大节点)
  final double l1_galaxy;
  
  // 0.4 <= L2 < 0.6: Sector (全节点+父子连线)
  final double l2_sector;
  
  // 0.6 <= L3 < 0.8: Nebula (关联连线+Glow)
  final double l3_nebula;
  
  // L4 >= 0.8: Node (全细节+粒子)
  
  /// 获取当前LOD级别
  int getLevel(double scale) {
    if (scale < l0_universe) return 0;
    if (scale < l1_galaxy) return 1;
    if (scale < l2_sector) return 2;
    if (scale < l3_nebula) return 3;
    return 4;
  }
}
