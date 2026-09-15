import 'package:flutter/material.dart';

/// 扩展颜色系统 - 提供语义化颜色访问器以替代硬编码颜色值
///
/// 使用方式:
/// ```dart
/// // 之前:
/// final color = isDark ? const Color(0xFFF1E7DA) : DS.textPrimary;
///
/// // 之后:
/// final color = context.colorExtensions.adaptiveTextPrimary;
/// ```
extension SparkleColorExtensions on BuildContext {
  /// 获取当前主题的颜色扩展
  SemanticColors get colorExtensions {
    final brightness = Theme.of(this).brightness;
    // Note: For high contrast mode, use the ThemeManager().highContrast check
    // or watch highContrastProvider in a widget that needs to rebuild on change
    return brightness == Brightness.light
        ? SemanticColors.light()
        : SemanticColors.dark();
  }

  /// 是否为深色模式
  bool get isDarkMode => Theme.of(this).brightness == Brightness.dark;

  /// 获取高对比度颜色 - 使用更鲜明的对比
  SemanticColors get colorExtensionsHighContrast {
    final brightness = Theme.of(this).brightness;
    return brightness == Brightness.light
        ? SemanticColors.lightHighContrast()
        : SemanticColors.darkHighContrast();
  }
}

/// 语义化颜色容器 - 扩展 SparkleColors 提供额外的语义颜色
@immutable
class SemanticColors {
  const SemanticColors({
    required this.brightness,
    this.isHighContrast = false,
  });

  const SemanticColors._highContrast({
    required this.brightness,
  }) : isHighContrast = true;

  factory SemanticColors.light() => const SemanticColors(
    brightness: Brightness.light,
  );

  factory SemanticColors.dark() => const SemanticColors(
    brightness: Brightness.dark,
  );

  /// 高对比度浅色模式 - 使用更鲜明的颜色对比
  factory SemanticColors.lightHighContrast() => const SemanticColors._highContrast(
    brightness: Brightness.light,
  );

  /// 高对比度深色模式 - 使用更鲜明的颜色对比
  factory SemanticColors.darkHighContrast() => const SemanticColors._highContrast(
    brightness: Brightness.dark,
  );

  final Brightness brightness;

  /// 是否为高对比度模式
  final bool isHighContrast;

  // ========== 通用颜色 ==========

  /// 自适应主文本颜色（深色模式使用浅色，浅色模式使用深色）
  /// 高对比度模式使用纯黑/纯白
  Color get adaptiveTextPrimary {
    if (isHighContrast) {
      return brightness == Brightness.dark ? Colors.white : Colors.black;
    }
    return brightness == Brightness.dark ? const Color(0xFFF4F1EB) : const Color(0xFF171717);
  }

  /// 自适应次级文本颜色
  /// 高对比度模式使用更强的对比
  Color get adaptiveTextSecondary {
    if (isHighContrast) {
      return brightness == Brightness.dark
          ? Colors.white.withValues(alpha: 0.87)
          : Colors.black.withValues(alpha: 0.87);
    }
    return brightness == Brightness.dark ? const Color(0xFFB8B1A6) : const Color(0xFF6C655D);
  }

  /// 自适应前景色（用于在背景上的文本）
  Color get adaptiveForeground {
    if (isHighContrast) {
      return brightness == Brightness.dark ? Colors.white : Colors.black;
    }
    return brightness == Brightness.dark ? Colors.white : const Color(0xFF111827);
  }

  /// 自适应背景色
  Color get adaptiveBackground {
    if (isHighContrast) {
      return brightness == Brightness.dark ? Colors.black : Colors.white;
    }
    return brightness == Brightness.dark ? const Color(0xFF0F1217) : const Color(0xFFF8F4EF);
  }

  // ========== 状态颜色 ==========

  /// 在线状态颜色
  Color get statusOnlineColor => const Color(0xFF2ECC71);

  /// 离线状态颜色
  Color get statusOfflineColor => const Color(0xFF95A5A6);

  /// 隐身状态颜色
  Color get statusInvisibleColor => const Color(0xFF34495E);

  // ========== 品牌颜色变体 ==========

  /// 品牌橙色（用于登录等强调场景）
  Color get brandOrange => const Color(0xFFD9773A);

  /// 品牌橙色深色变体
  Color get brandOrangeDeep => const Color(0xFFBA5923);

  /// 品牌蓝色（用于次要强调）
  Color get brandBlue => const Color(0xFF4C78B2);

  /// 品牌蓝色深色变体
  Color get brandBlueDeep => const Color(0xFF2F588E);

  // ========== 社交/分享颜色 ==========

  /// 微信绿色
  Color get wechatGreen => const Color(0xFF07C160);

  /// 金色强调（用于成就等）
  Color get goldenAccent => const Color(0xFFFFD700);

  /// 琥珀金色（用于成就徽章）
  Color get amberGold => const Color(0xFFFFB300);

  // ========== 知识图谱颜色 ==========

  /// 银河深色背景
  Color get galaxyDarkBg => const Color(0xFF0A0E17);

  /// 银河深色径向渐变
  Color get galaxyDarkRadial => const Color(0xFF0D1525);

  /// 银河浅色背景
  Color get galaxyLightBg => const Color(0xFFF5F6F8);

  /// 银河浅色径向渐变
  Color get galaxyLightRadial => const Color(0xFFEBEDF2);

  /// 银河节点高亮蓝色
  Color get galaxyHighlightBlue => const Color(0xFF88B4FF);

  /// 银河节点高亮金色
  Color get galaxyHighlightGold => const Color(0xFFFFD700);

  /// 银河链接线颜色（深色模式）
  Color get galaxyLinkDark => Colors.black;

  /// 银河链接线颜色（浅色模式）
  Color get galaxyLinkLight => const Color(0xFFCBD2DD);

  // ========== 聊天模式颜色 ==========

  /// 紫色模式（创造模式）
  Color get chatModePurple => const Color(0xFF9C27B0);

  /// 青色模式（分析模式）
  Color get chatModeTeal => const Color(0xFF00897B);

  /// 蓝色模式（规划模式）
  Color get chatModeBlue => const Color(0xFF1565C0);

  /// 靛蓝模式（默认模式）
  Color get chatModeIndigo => const Color(0xFF5C6BC0);

  // ========== Agent 颜色 ==========

  /// Agent 紫色
  Color get agentPurple => const Color(0xFF6C5CE7);

  /// Agent 橙色
  Color get agentOrange => const Color(0xFFE17055);

  /// Agent 绿色
  Color get agentGreen => const Color(0xFF00B894);

  /// Agent 蓝色
  Color get agentBlue => const Color(0xFF0984E3);

  /// Agent 红色
  Color get agentRed => const Color(0xFFD63031);

  /// Agent 青色
  Color get agentCyan => const Color(0xFF00CEC9);

  /// Agent 粉色
  Color get agentPink => const Color(0xFFE84393);

  /// Agent 灰色
  Color get agentGray => const Color(0xFF636E72);

  /// Agent 黄色
  Color get agentYellow => const Color(0xFFFDCB6E);

  // ========== 意图分类颜色 ==========

  /// 意图蓝色
  Color get intentBlue => const Color(0xFF42A5F5);

  /// 意图绿色
  Color get intentGreen => const Color(0xFF66BB6A);

  /// 意图紫色
  Color get intentPurple => const Color(0xFFAB47BC);

  /// 意图青色
  Color get intentCyan => const Color(0xFF26C6DA);

  /// 意图深紫
  Color get intentDeepPurple => const Color(0xFF7E57C2);

  /// 意图橙色
  Color get intentOrange => const Color(0xFFFFA726);

  /// 意图粉色
  Color get intentPink => const Color(0xFFEC407A);

  /// 意图靛蓝
  Color get intentIndigo => const Color(0xFF5C6BC0);

  // ========== 分享模板颜色 ==========

  /// 模板宇宙靛蓝
  Color get templateCosmic => const Color(0xFF6366F1);

  /// 模板极简灰
  Color get templateMinimal => const Color(0xFF64748B);

  /// 模板霓虹青
  Color get templateNeon => const Color(0xFF22D3EE);

  /// 模板优雅金
  Color get templateElegant => const Color(0xFFD4AF37);

  // ========== 成就颜色 ==========

  /// 成就橙色（学习）
  Color get achievementOrange => const Color(0xFFFFB347);

  /// 成就紫色（里程碑）
  Color get achievementPurple => const Color(0xFFB04AFF);

  /// 成就蓝色（社交）
  Color get achievementBlue => const Color(0xFF4A9EFF);

  /// 成就绿色（坚持）
  Color get achievementGreen => const Color(0xFF78C778);

  // ========== 扇区颜色（知识图谱） ==========

  /// 扇区蓝色（技术）
  Color get sectorTechDark => const Color(0xFF78A3D1);
  Color get sectorTechLight => const Color(0xFF386494);

  /// 扇区青色（科学）
  Color get sectorScienceDark => const Color(0xFF5AB8CC);
  Color get sectorScienceLight => const Color(0xFF356E7B);

  /// 扇区粉色（艺术）
  Color get sectorArtDark => const Color(0xFFC97C8F);
  Color get sectorArtLight => const Color(0xFF955061);

  /// 扇区金色（人文）
  Color get sectorHumanityDark => const Color(0xFFD0A05F);
  Color get sectorHumanityLight => const Color(0xFFA16B2A);

  /// 扇区绿色（生活）
  Color get sectorLifeDark => const Color(0xFF5FAF80);
  Color get sectorLifeLight => const Color(0xFF3A8552);

  /// 扇区紫罗兰（哲学）
  Color get sectorPhilosophyDark => const Color(0xFFA181C8);
  Color get sectorPhilosophyLight => const Color(0xFF67478F);

  /// 扇区灰色（其他）
  Color get sectorOtherDark => const Color(0xFF70798B);
  Color get sectorOtherLight => const Color(0xFF8A93A8);

  // ========== 面板/卡片颜色 ==========

  /// 半透明深色面板背景
  Color get panelDarkOverlay => const Color(0xAA101722);

  /// 半透明深色面板背景（更透明）
  Color get panelDarkOverlayLight => const Color(0xCC101929);

  /// 半透明深色面板背景（最透明）
  Color get panelDarkOverlayLighter => const Color(0xE6151D30);

  /// 浅色面板背景
  Color get panelLightOverlay => Colors.white;

  // ========== 渐变色 ==========

  /// 深色模式背景渐变
  List<Color> get darkBackgroundGradient => const [
        Color(0xFF0a0a1a),
        Color(0xFF1a1a2e),
        Color(0xFF16213e),
      ];

  /// 浅色模式背景渐变 - 使用 DS 中的 surface 颜色
  List<Color> get lightBackgroundGradient => [
        const Color(0xFFF8F4EF),
        const Color(0xFFF1EBE4),
        const Color(0xFFE7DED4),
      ];

  // ========== 统计卡片渐变 ==========

  /// 统计卡片蓝色渐变
  List<Color> get statisticsBlueGradient => brightness == Brightness.dark
      ? [const Color(0xFF94AFD2), const Color(0xFF7A93B4)]
      : [const Color(0xFF7A93B4), const Color(0xFF6A83A4)];

  /// 统计卡片绿色渐变
  List<Color> get statisticsGreenGradient => brightness == Brightness.dark
      ? [const Color(0xFF8EA18E), const Color(0xFF7A9A83)]
      : [const Color(0xFF9DB1C9), const Color(0xFF8DA1B9)];
}

/// 获取知识图谱扇区颜色
Color getSectorColor(String sectorId, {bool isDark = true}) {
  final colors = isDark ? SemanticColors.dark() : SemanticColors.light();
  switch (sectorId.toLowerCase()) {
    case 'tech':
    case 'technology':
      return isDark ? colors.sectorTechDark : colors.sectorTechLight;
    case 'science':
      return isDark ? colors.sectorScienceDark : colors.sectorScienceLight;
    case 'art':
    case 'arts':
      return isDark ? colors.sectorArtDark : colors.sectorArtLight;
    case 'humanity':
    case 'humanities':
      return isDark ? colors.sectorHumanityDark : colors.sectorHumanityLight;
    case 'life':
      return isDark ? colors.sectorLifeDark : colors.sectorLifeLight;
    case 'philosophy':
      return isDark ? colors.sectorPhilosophyDark : colors.sectorPhilosophyLight;
    default:
      return isDark ? colors.sectorOtherDark : colors.sectorOtherLight;
  }
}

/// 获取 Agent 颜色
Color getAgentColor(String agentId) {
  switch (agentId.toLowerCase()) {
    case 'purple':
    case 'mentor':
      return const Color(0xFF6C5CE7);
    case 'orange':
    case 'coach':
      return const Color(0xFFE17055);
    case 'green':
    case 'guide':
      return const Color(0xFF00B894);
    case 'blue':
    case 'analyst':
      return const Color(0xFF0984E3);
    case 'red':
    case 'critic':
      return const Color(0xFFD63031);
    case 'cyan':
    case 'explorer':
      return const Color(0xFF00CEC9);
    case 'pink':
    case 'companion':
      return const Color(0xFFE84393);
    case 'yellow':
    case 'cheerleader':
      return const Color(0xFFFDCB6E);
    case 'gray':
    case 'neutral':
    default:
      return const Color(0xFF636E72);
  }
}

/// 获取意图分类颜色
Color getIntentColor(String intentType) {
  switch (intentType.toLowerCase()) {
    case 'create':
      return const Color(0xFF42A5F5);
    case 'learn':
      return const Color(0xFF66BB6A);
    case 'reflect':
      return const Color(0xFFAB47BC);
    case 'explore':
      return const Color(0xFF26C6DA);
    case 'deep_think':
      return const Color(0xFF7E57C2);
    case 'plan':
      return const Color(0xFFFFA726);
    case 'social':
      return const Color(0xFFEC407A);
    case 'review':
    case 'chat':
    default:
      return const Color(0xFF5C6BC0);
  }
}

/// 获取成就颜色
Color getAchievementColor(String achievementType) {
  switch (achievementType.toLowerCase()) {
    case 'learning':
    case 'learn':
    case 'legendary':
      return const Color(0xFFFFB347);
    case 'milestone':
    case 'epic':
      return const Color(0xFFB04AFF);
    case 'social':
    case 'rare':
      return const Color(0xFF4A9EFF);
    case 'persistence':
    case 'streak':
    case 'common':
    default:
      return const Color(0xFF78C778);
  }
}

/// 获取分享模板颜色
Color getTemplateColor(String templateId) {
  switch (templateId.toLowerCase()) {
    case 'cosmic':
      return const Color(0xFF6366F1);
    case 'minimal':
      return const Color(0xFF64748B);
    case 'neon':
      return const Color(0xFF22D3EE);
    case 'elegant':
      return const Color(0xFFD4AF37);
    default:
      return const Color(0xFF6366F1);
  }
}

/// 获取聊天模式颜色
Color getChatModeColor(String modeId) {
  switch (modeId.toLowerCase()) {
    case 'creative':
    case 'create':
      return const Color(0xFF9C27B0);
    case 'analyze':
    case 'analysis':
      return const Color(0xFF00897B);
    case 'plan':
    case 'planning':
      return const Color(0xFF1565C0);
    case 'default':
    default:
      return const Color(0xFF5C6BC0);
  }
}
