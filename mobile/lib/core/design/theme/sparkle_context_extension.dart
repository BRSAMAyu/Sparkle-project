import 'package:flutter/material.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/tokens_v2/state_tokens.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart'
    show SparkleColors, SparkleSpacing, SparkleTypography;

/// BuildContext helpers for Sparkle design tokens.
extension SparkleContextExtension on BuildContext {
  SparkleThemeExtension get sparkle {
    final extension = Theme.of(this).extension<SparkleThemeExtension>();
    assert(
      extension != null,
      'SparkleThemeExtension is not registered on ThemeData.',
    );
    return extension!;
  }

  SparkleColors get colors => sparkle.colors;
  SparkleTypography get typo => sparkle.typography;
  SparkleSpacing get space => sparkle.spacing;
  SparkleRadius get radius => sparkle.radius;
  SparkleMotionTokens get motion => sparkle.motion;

  /// 当前刺激档位（U-02）；低刺激开关见 [lowStimulation]。
  StimulationLevel get stimulationLevel => sparkle.stimulationLevel;

  /// 低刺激档是否生效（主题级真实开关，默认关）。
  bool get lowStimulation => sparkle.lowStimulation;

  /// 按状态取当前档位的装饰预算（U-02 状态令牌访问面）。
  SparkleStateTokens stateTokens(SparkleStateMood mood) =>
      SparkleStateTokens.forMood(mood, level: sparkle.stimulationLevel);

  bool get canBlur => sparkle.enableBlur;
  bool get canGlow => sparkle.enableGlow;
  bool get canComplexAnimate => sparkle.enableComplexAnimation;

  /// Whether the OS requests reduced motion or simplified navigation effects.
  bool get reduceMotion {
    final mediaQuery = MediaQuery.maybeOf(this);
    if (mediaQuery == null) return false;
    return mediaQuery.disableAnimations || mediaQuery.accessibleNavigation;
  }
}

// ═══ 语义别名层（SPEC v1.0 §1；B2-2 合入即 §1.7【批 2 起】门禁段生效）═══
// 纯映射层：只做别名转发——值 owner 仍是 [SparkleColors] 字段（tonal 再
// 生成属后续工作包）。B2-3a 起 text.tertiary 接独立定标槽 textTertiary；
// focus 槽经评审维持 accent（brandPrimary）兼任（证据与建议见
// v3-output/B2-3A/REPORT.md）。
// 【批 2 起】新代码取色只走语义名（context.colors.surface.canvas 等），
// 旧字段名（surfaceAmbient 等）降为只读 owner（SPEC §1.7 替换映射表）。

/// 表面阶语义视图（SPEC §1.2 四级 tonal surface ladder）。
///
/// 相邻级差下界（规则 1.2.1，light 表）由
/// `scripts/design/check_surface_ladder_de.py` 机检（CIEDE2000/ΔE≤2 锚点回归）。
@immutable
class SparkleSurfaceSemantics {
  const SparkleSurfaceSemantics(this._owner);

  final SparkleColors _owner;

  /// S0 canvas（画布）— 页面背景。owner: `surfaceAmbient`。
  Color get canvas => _owner.surfaceAmbient;

  /// S1 base（基础面）— 页内默认卡面。owner: `surfacePrimary`。
  Color get base => _owner.surfacePrimary;

  /// S2 raised（浮起面）— sheet、下拉、拖起卡。owner: `surfaceSecondary`。
  Color get raised => _owner.surfaceSecondary;

  /// S3 elevated（高亮浮起面）— 选中态容器、焦点卡。owner: `surfaceTertiary`。
  Color get elevated => _owner.surfaceTertiary;
}

/// 文字阶语义视图（SPEC §1.3）。三级封顶 + disabled（规则 1.3.1：
/// 禁「透明度压文字」作第四级）。
@immutable
class SparkleTextSemantics {
  const SparkleTextSemantics(this._owner);

  final SparkleColors _owner;

  /// 标题/正文主体（内容永远是最深的颜色）。owner: `textPrimary`。
  Color get primary => _owner.textPrimary;

  /// 次要说明/元数据。owner: `textSecondary`。
  Color get secondary => _owner.textSecondary;

  /// 辅助文字（时间戳、脚注等扫视件）。owner: `textTertiary`（B2-3a 独立
  /// 定标：各变体 >=4.5:1 on S0/S1，强调度严格介于 secondary 与 disabled
  /// 之间；SPEC §1.3【定标待实测】已闭）。
  Color get tertiary => _owner.textTertiary;

  /// 禁用态（状态色，非层级，对比度豁免）。owner: `textDisabled`。
  Color get disabled => _owner.textDisabled;
}

/// SPEC §1 命名的语义访问面，挂在 [SparkleColors] 上使
/// `context.colors.surface.canvas` 等规范路径直接可用（SPEC §1.7 替换映射表）。
/// 旧字段访问零影响（extension 成员不遮蔽实例成员）。
extension SparkleSemanticColorNames on SparkleColors {
  /// 表面阶 S0–S3（SPEC §1.2）。
  SparkleSurfaceSemantics get surface => SparkleSurfaceSemantics(this);

  /// 文字阶 primary/secondary/tertiary/disabled（SPEC §1.3）。
  SparkleTextSemantics get text => SparkleTextSemantics(this);

  /// 唯一交互色（SPEC §1.4.1）= `brandPrimary`。只标可交互控件与品牌时刻；
  /// 禁兼做正文强调（用 text.primary+字重）、图标装饰、非可点标签。
  /// 注意：≠ 已退役别名 `DS.accent`（那是 brandSecondary，SPEC §1.4.2）。
  Color get accent => brandPrimary;

  /// 语义槽 success（SPEC §1.5，灰绿 sage）——完成、达成、在线。
  Color get success => semanticSuccess;

  /// 语义槽 warning（琥珀）——注意、临近截止、降级提示。
  Color get warning => semanticWarning;

  /// 语义槽 error（陶土）——失败、错误、逾期。
  Color get error => semanticError;

  /// 语义槽 info（AI 信息，唯一冷色槽，slate 蓝）——AI 状态/建议/确认请求/
  /// 数据可视化主色；冷色只准经本槽出现（规则 1.5.2）。
  Color get info => semanticInfo;

  /// 语义槽 focus（键盘/无障碍焦点环）＝ `brandPrimary` 兼任。
  /// B2-3a 裁决：维持兼任——全 app 无自绘焦点环渲染点（focusRing 0 处；
  /// 唯一 FocusableActionDetector 仅承载 enter/space 激活语义不绘制环；
  /// Material focus 高亮仅在键盘遍历模式可见，触摸优先场景不渲染；TalkBack/
  /// VoiceOver 焦点框由系统绘制，不消费 app 令牌）。独立槽建议与触发条件
  /// 见 v3-output/B2-3A/REPORT.md（规范修订走 R5）。
  Color get focus => brandPrimary;
}
