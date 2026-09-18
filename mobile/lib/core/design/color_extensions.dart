import 'package:flutter/material.dart';

/// BuildContext 颜色助手。
///
/// batch3 ~76 色处置：全局语义颜色的唯一事实源是
/// `tokens_v2/theme_manager.dart` 的 SparkleColors（`context.colors`）。
/// 原 SemanticColors 类（~70 个孤立 hex：adaptive/status/galaxy/chatMode/
/// agent/intent/template/achievement/sector/panel/渐变）已删除——其中仅
/// adaptiveTextPrimary/adaptiveForeground/chatModeIndigo/panelDarkOverlay
/// 有真实消费，全部迁往单一源（见 round1-batch3.md 案三）。高对比变体
/// 工厂与 `colorExtensionsHighContrast` 一并删除（零消费；P1-9 高对比
/// 贯通时在 SparkleColors 六套工厂内实现）。
extension SparkleColorExtensions on BuildContext {
  /// 是否为深色模式
  bool get isDarkMode => Theme.of(this).brightness == Brightness.dark;
}

/// Galaxy 搜索面板暗色底（仅暗支使用）。值原为 SemanticColors.
/// panelDarkOverlayLighter，batch3 迁移至此——领域装饰色与四组领域调色板
/// 同一收编逻辑：单拷贝、不随亮度档变化，galaxy 模块横扫时重校。
const Color galaxyPanelOverlayDark = Color(0xE6151D30);

/// ============ 领域分类调色板（domain categorical palettes） ============
///
/// 以下 4 个函数是各自领域（Agent 角色 / 意图分类 / 成就稀有度 / 分享
/// 模板）的身份色，属于领域数据而非全局语义令牌：不随亮度/高对比/色盲
/// 档变化（跨档校准归 L1 P1-9 高对比贯通），且强行折入 SparkleColors 六套
/// 工厂需要发明 5×25 个新字面量（违反零新增纪律）。batch3 处置后每个
/// hex 在全仓只剩这一份拷贝（原 SemanticColors 成员副本已随类删除）——
/// 本文件即这四组调色板的单一事实源。
///
/// 消费者：agent_team_sheet / intent_classifier / achievement_progress_card
/// / share_template_selector。

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
