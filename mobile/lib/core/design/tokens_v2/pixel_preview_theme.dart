/// V4-F01 · 像素候选主题（preview 通道）—— 纸昼 / 暮色 / 低刺激。
///
/// **PROPOSED_NOT_APPROVED**（状态源：`v4/02_design/TOKENS.proposal.json`
/// `status` 字段；权限源：`v4/README_START_HERE.md`「本版的权限与冻结点」——
/// 参考图是提案不是已批准的全站设计，`pixel.preview` 只在开发预览开放，
/// 默认发布仍沿用已验收主题）。RF-06 视觉合同（sparkle-cosmos
/// `agent/rf06-full-ui` 交接，v4/evidence/V4-B01 盘点）同样把未验收色板
/// 限定为提案口径：本文件全部色值按提案实现并标注 PROPOSED，不冒充已定版。
///
/// 结构约束（V4-F01 卡面 + 02_design/DESIGN_SYSTEM.md）：
/// - **唯一令牌体系**：候选 profile 只生产既有 [SparkleColors] /
///   [SparkleThemeData]（tokens_v2 单一运行时真源），不建第二套颜色/字阶/
///   间距类。像素尺寸与动效按 DESIGN_SYSTEM.md 允许的「极少数新增字段」
///   （pixelStep、cornerCut、accentInk、stateMotion）落在
///   [PixelProfileTheme] ThemeExtension 上，复用既有 theme 通道分发。
/// - **preview 默认 off**：[PixelPreviewProfile.classic] 是唯一默认值，
///   `ThemeManager` 在 classic 下走既有路径（行为与发布面零差量）；
///   只有显式切到候选 profile 才替换主题（classic 随时可回退）。
/// - 色板锚值 = `v4/02_design/TOKENS.proposal.json`（paper_day / dusk /
///   quiet 三个 profile 的 canvas/surface/raised/ink/muted/line/accent/
///   on_accent/info/warning/error/success/decor 13 槽逐值转抄）。
///   派生槽（中性阶梯、task/plan 角色、聊天气泡、galaxy、disabled）按
///   SparkleColors 语义槽映射并注明公式；核心文案对比度已自动测
///   （test/core/design/pixel_preview_theme_test.dart，WCAG ≥4.5:1）。
/// - 与 RF-06 设计语言同源点：奶油纸底承托 + 深墨正文，鼠尾草绿（accent）、
///   灰蓝（info）、陶土（warning/error 族）、柔紫（taskReflection，
///   PROPOSED 字面量 #64558A / #BCAED4）四类少量功能强调；像素概念网格
///   2dp（[PixelProfileTheme.pixelStep]），角切阶梯 4/8/12。
library;

import 'dart:ui' show lerpDouble;

import 'package:flutter/foundation.dart' show listEquals;
import 'package:flutter/material.dart';

import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// 像素候选主题档位（preview 通道）。
///
/// - [classic]：默认值 = preview 关。零差量走既有发布主题（可回退锚点）。
/// - [paperDay]：纸昼（浅色，奶油纸底 + 深墨正文）。
/// - [dusk]：暮色（深色，暗绿纸底 + 暖墨）。
/// - [quiet]：低刺激（浅色，更素的面板/去饱和容器）。
///
/// 三档是同一语义映射的不同呈现（DESIGN_SYSTEM.md「主题和状态」），
/// 不是三个产品；切换语义归 V4-F05 的 preview 面所有，本卡只提供令牌与
/// `ThemeManager` 编程式入口。
enum PixelPreviewProfile { classic, paperDay, dusk, quiet }

// ---------------------------------------------------------------------------
// PROPOSED 色板锚值（转抄自 v4/02_design/TOKENS.proposal.json，未验收）。
// ---------------------------------------------------------------------------

// paper_day（纸昼 · 浅）
const Color _pdCanvas = Color(0xFFF4F0E6); // canvas
const Color _pdSurface = Color(0xFFFFFCF4); // surface
const Color _pdRaised = Color(0xFFE9E5D8); // raised
const Color _pdInk = Color(0xFF29342F); // ink
const Color _pdMuted = Color(0xFF58665C); // muted
const Color _pdLine = Color(0xFF68766A); // line
const Color _pdAccent = Color(0xFF3E6652); // accent（鼠尾草绿）
const Color _pdInfo = Color(0xFF3C607A); // info（灰蓝）
const Color _pdWarning = Color(0xFF805126); // warning（陶土系）
const Color _pdError = Color(0xFF9C3D38); // error（陶土红）
const Color _pdSuccess = Color(0xFF386347); // success
const Color _pdDecor = Color(0xFFD0D8CB); // decor

// dusk（暮色 · 深）
const Color _duskCanvas = Color(0xFF19241F); // canvas
const Color _duskSurface = Color(0xFF24322B); // surface
const Color _duskRaised = Color(0xFF2F4036); // raised
const Color _duskInk = Color(0xFFF5F0E3); // ink
const Color _duskMuted = Color(0xFFC2CCBE); // muted
const Color _duskLine = Color(0xFF9DAF9F); // line
const Color _duskAccent = Color(0xFFB9D5B5); // accent
const Color _duskOnAccent = Color(0xFF17261C); // on_accent
const Color _duskInfo = Color(0xFFAFCADC); // info
const Color _duskWarning = Color(0xFFE2BF89); // warning
const Color _duskError = Color(0xFFF1B0A4); // error
const Color _duskSuccess = Color(0xFFB9D5B5); // success
const Color _duskDecor = Color(0xFF344B3B); // decor

// quiet（低刺激 · 浅）
const Color _quietCanvas = Color(0xFFF7F5EF); // canvas
const Color _quietSurface = Color(0xFFFFFFFF); // surface
const Color _quietRaised = Color(0xFFECECE5); // raised
const Color _quietInk = Color(0xFF202A24); // ink
const Color _quietMuted = Color(0xFF536056); // muted
const Color _quietLine = Color(0xFF627063); // line
const Color _quietAccent = Color(0xFF344F3D); // accent
const Color _quietInfo = Color(0xFF36556D); // info
const Color _quietWarning = Color(0xFF795126); // warning
const Color _quietError = Color(0xFF933B35); // error
const Color _quietSuccess = Color(0xFF345C40); // success
const Color _quietDecor = Color(0xFFEAEEE8); // decor

// PROPOSED 派生锚（RF-06 视觉合同「柔紫强调」；两档浅色共用一枚深紫，
// dusk 用亮紫）。非 TOKENS.proposal 槽，标注来源与对比度依据：
// #64558A ≥5.19:1、#BCAED4 ≥4.58:1（三档全部容器面，自动测覆盖）。
const Color _reflectionPurpleLight = Color(0xFF64558A);
const Color _reflectionPurpleDusk = Color(0xFFBCAED4);

// ---------------------------------------------------------------------------
// SparkleColors 组装：候选 profile → 既有语义槽（唯一运行时结构）。
// ---------------------------------------------------------------------------

/// 槽映射口径（三档一致，值随档）：
/// - proposal surface → surfaceAmbient + surfaceSecondary（纸卡比页面亮，
///   反转 classic 的「次面更暗」梯度——纸感视觉合同的意图，PROPOSED）；
/// - proposal canvas → surfacePrimary（页面底，scaffold 背景）；
/// - proposal raised → surfaceTertiary（深一档容器）；
/// - proposal ink/muted → textPrimary/textSecondary；textTertiary=muted、
///   textDisabled=lerp(line, decor, 0.35)（dusk 向 canvas），PROPOSED 简化；
/// - 中性阶梯：n200=decor、n300=line（描边 ≥3:1 图形线）、
///   n400/500/600=lerp(line, ink, .35/.6/.8)（dusk 从 raised 出发）；
/// - task/plan 角色沿用 classic 收敛口径（learning=info、training=warning、
///   errorFix/sprint=error、social/growth=success）；planning=
///   lerp(info, accent, 0.5)、ocr=lerp(muted, ink, 0.3)、reflection=柔紫。
SparkleColors pixelPreviewColors(PixelPreviewProfile profile) {
  switch (profile) {
    case PixelPreviewProfile.paperDay:
      return const SparkleColors(
        brandPrimary: _pdAccent,
        brandSecondary: _pdInfo,
        semanticSuccess: _pdSuccess,
        semanticWarning: _pdWarning,
        semanticError: _pdError,
        semanticInfo: _pdInfo,
        surfacePrimary: _pdCanvas,
        surfaceSecondary: _pdSurface,
        surfaceTertiary: _pdRaised,
        surfaceAmbient: _pdSurface,
        rimLight: Color(0x99FFFFFF),
        glowPrimary: Color(0x243E6652),
        noiseColor: Color(0x0D000000),
        textPrimary: _pdInk,
        textSecondary: _pdMuted,
        textTertiary: _pdMuted,
        textDisabled: Color(0xFF8C988C), // lerp(_pdLine, _pdDecor, 0.35)
        brightness: Brightness.light,
        taskLearning: _pdInfo,
        taskTraining: _pdWarning,
        taskErrorFix: _pdError,
        taskReflection: _reflectionPurpleLight,
        taskSocial: _pdSuccess,
        taskPlanning: Color(0xFF3D6366), // lerp(_pdInfo, _pdAccent, 0.5)
        taskOcr: Color(0xFF4A574E), // lerp(_pdMuted, _pdInk, 0.3)
        planSprint: _pdError,
        planGrowth: _pdSuccess,
        statusOnline: _pdSuccess,
        statusOffline: _pdLine,
        statusInvisible: _pdMuted,
        neutral200: _pdDecor,
        neutral300: _pdLine,
        neutral400: Color(0xFF525F55), // lerp(_pdLine, _pdInk, 0.35)
        neutral500: Color(0xFF424E47), // lerp(_pdLine, _pdInk, 0.6)
        neutral600: Color(0xFF36413B), // lerp(_pdLine, _pdInk, 0.8)
        neutralOutline: Color(0xFF9E9E9E),
        chatBubbleUser: _pdInfo,
        chatBubbleUserText: Colors.white,
        chatBubbleOther: _pdSurface,
        chatBubbleOtherText: _pdInk,
        galaxyBackground: _pdDecor,
        galaxyShadow: Color(0xFFE6E6DB), // lerp(_pdDecor, _pdCanvas, 0.6)
      );
    case PixelPreviewProfile.dusk:
      return const SparkleColors(
        brandPrimary: _duskAccent,
        brandSecondary: _duskInfo,
        semanticSuccess: _duskSuccess,
        semanticWarning: _duskWarning,
        semanticError: _duskError,
        semanticInfo: _duskInfo,
        surfacePrimary: _duskSurface,
        surfaceSecondary: _duskRaised,
        surfaceTertiary: _duskDecor,
        surfaceAmbient: _duskCanvas,
        rimLight: Color(0x33FFFFFF),
        glowPrimary: Color(0x42B9D5B5),
        noiseColor: Color(0x08FFFFFF),
        textPrimary: _duskInk,
        textSecondary: _duskMuted,
        textTertiary: _duskMuted,
        textDisabled: Color(0xFF627065), // lerp(_duskLine, _duskCanvas, 0.45)
        brightness: Brightness.dark,
        taskLearning: _duskInfo,
        taskTraining: _duskWarning,
        taskErrorFix: _duskError,
        taskReflection: _reflectionPurpleDusk,
        taskSocial: _duskSuccess,
        taskPlanning: Color(0xFFB4D0C8), // lerp(_duskInfo, _duskAccent, 0.5)
        taskOcr: Color(0xFFD1D7C9), // lerp(_duskMuted, _duskInk, 0.3)
        planSprint: _duskError,
        planGrowth: _duskSuccess,
        statusOnline: _duskSuccess,
        statusOffline: _duskLine,
        statusInvisible: _duskMuted,
        neutral200: Color(0xFF2A3930), // lerp(_duskSurface, _duskRaised, 0.5)
        neutral300: _duskRaised,
        neutral400: Color(0xFF66786A), // lerp(_duskRaised, _duskLine, 0.5)
        neutral500: Color(0xFF829385), // lerp(_duskRaised, _duskLine, 0.75)
        neutral600: _duskLine,
        neutralOutline: Color(0xFF9E9E9E),
        chatBubbleUser: _duskInfo,
        chatBubbleUserText: _duskOnAccent,
        chatBubbleOther: _duskRaised,
        chatBubbleOtherText: _duskInk,
        galaxyBackground: _duskCanvas,
        galaxyShadow: Color(0xFF101714), // lerp(_duskCanvas, black, 0.35)
      );
    case PixelPreviewProfile.quiet:
      return const SparkleColors(
        brandPrimary: _quietAccent,
        brandSecondary: _quietInfo,
        semanticSuccess: _quietSuccess,
        semanticWarning: _quietWarning,
        semanticError: _quietError,
        semanticInfo: _quietInfo,
        surfacePrimary: _quietCanvas,
        surfaceSecondary: _quietSurface,
        surfaceTertiary: _quietRaised,
        surfaceAmbient: _quietSurface,
        rimLight: Color(0x99FFFFFF),
        glowPrimary: Color(0x24344F3D),
        noiseColor: Color(0x0D000000),
        textPrimary: _quietInk,
        textSecondary: _quietMuted,
        textTertiary: _quietMuted,
        textDisabled: Color(0xFF929C92), // lerp(_quietLine, _quietDecor, 0.35)
        brightness: Brightness.light,
        taskLearning: _quietInfo,
        taskTraining: _quietWarning,
        taskErrorFix: _quietError,
        taskReflection: _reflectionPurpleLight,
        taskSocial: _quietSuccess,
        taskPlanning: Color(0xFF355255), // lerp(_quietInfo, _quietAccent, 0.5)
        taskOcr: Color(0xFF445047), // lerp(_quietMuted, _quietInk, 0.3)
        planSprint: _quietError,
        planGrowth: _quietSuccess,
        statusOnline: _quietSuccess,
        statusOffline: _quietLine,
        statusInvisible: _quietMuted,
        neutral200: _quietDecor,
        neutral300: _quietLine,
        neutral400: Color(0xFF4B584D), // lerp(_quietLine, _quietInk, 0.35)
        neutral500: Color(0xFF3A463D), // lerp(_quietLine, _quietInk, 0.6)
        neutral600: Color(0xFF2D3831), // lerp(_quietLine, _quietInk, 0.8)
        neutralOutline: Color(0xFF9E9E9E),
        chatBubbleUser: _quietInfo,
        chatBubbleUserText: Colors.white,
        chatBubbleOther: _quietSurface,
        chatBubbleOtherText: _quietInk,
        galaxyBackground: _quietDecor,
        galaxyShadow: Color(0xFFF2F2EC), // lerp(_quietDecor, _quietCanvas, 0.6)
      );
    case PixelPreviewProfile.classic:
      // classic 不是像素档：调用方应走既有工厂。防御性回落 light。
      return SparkleColors.light();
  }
}

/// 候选 profile 的完整 [SparkleThemeData]（唯一令牌结构，非第二体系）。
///
/// 注意：候选 profile 各自钉死亮度（paperDay/quiet = 浅、dusk = 深），
/// 不随系统亮度翻转——preview 语义是「整档候选主题」，亮暗切换 UX 归
/// V4-F05 裁决。classic 传入时返回既有 light 工厂（防御路径）。
SparkleThemeData pixelPreviewThemeData(PixelPreviewProfile profile) {
  final isDusk = profile == PixelPreviewProfile.dusk;
  return SparkleThemeData(
    colors: pixelPreviewColors(profile),
    typography: SparkleTypography.standard(),
    spacing: const SparkleSpacing(),
    animations: const SparkleAnimations(),
    shadows: isDusk ? SparkleShadows.dark() : SparkleShadows.light(),
  );
}

/// 像素档动效映射（TOKENS.proposal `motion_ms`：press 80 / state 160 /
/// enter 220 / milestone_max 650）。落在扩展字段上，不改写既有
/// [SparkleAnimations]/AnimationSystem——滚动/点击/正文时长不受影响
/// （DESIGN_SYSTEM.md 验收节）。
@immutable
class PixelStateMotion {
  const PixelStateMotion({
    this.press = const Duration(milliseconds: 80),
    this.state = const Duration(milliseconds: 160),
    this.enter = const Duration(milliseconds: 220),
    this.milestoneMax = const Duration(milliseconds: 650),
  });

  final Duration press;
  final Duration state;
  final Duration enter;
  final Duration milestoneMax;

  PixelStateMotion lerp(PixelStateMotion other, double t) {
    Duration lerpMs(Duration a, Duration b) => Duration(
          milliseconds:
              lerpDouble(a.inMilliseconds, b.inMilliseconds, t)!.round(),
        );
    return PixelStateMotion(
      press: lerpMs(press, other.press),
      state: lerpMs(state, other.state),
      enter: lerpMs(enter, other.enter),
      milestoneMax: lerpMs(milestoneMax, other.milestoneMax),
    );
  }
}

/// 像素候选主题的 ThemeExtension——DESIGN_SYSTEM.md 允许的极少数新增字段：
/// `pixelStep`（2dp 概念网格）、`cornerCut`（4/8/12 角切阶梯）、
/// `accentInk`（accent 容器之上的墨色 = on_accent）、`stateMotion`。
///
/// 只在 preview 开启时由 `design_system.dart` 挂载；classic（默认发布面）
/// 的 ThemeData 不携带本扩展，`of` 返回 null，消费方按 null 回落既有令牌。
@immutable
class PixelProfileTheme extends ThemeExtension<PixelProfileTheme> {
  const PixelProfileTheme({
    required this.profile,
    required this.accentInk,
    this.pixelStep = 2.0,
    this.cornerCut = const [4.0, 8.0, 12.0],
    this.stateMotion = const PixelStateMotion(),
  });

  /// 按 profile 组装（accentInk = proposal `on_accent` 槽：浅档白墨、
  /// dusk 深墨 #17261C；classic 防御路径用 classic textPrimary）。
  factory PixelProfileTheme.forProfile(PixelPreviewProfile profile) =>
      PixelProfileTheme(
        profile: profile,
        accentInk: switch (profile) {
          PixelPreviewProfile.dusk => _duskOnAccent,
          PixelPreviewProfile.classic => const Color(0xFF171717),
          PixelPreviewProfile.paperDay ||
          PixelPreviewProfile.quiet =>
            Colors.white,
        },
      );

  final PixelPreviewProfile profile;

  /// 像素概念网格（TOKENS.proposal `pixel_step_dp`）。
  final double pixelStep;

  /// 角切阶梯（TOKENS.proposal `corner_cut_dp`）。
  final List<double> cornerCut;

  /// accent 容器之上的墨色（on_accent）。
  final Color accentInk;

  /// 像素档动效预算。
  final PixelStateMotion stateMotion;

  /// 读取当前档扩展；classic/未挂载时为 null（消费方回落既有令牌）。
  static PixelProfileTheme? of(BuildContext context) =>
      Theme.of(context).extension<PixelProfileTheme>();

  @override
  PixelProfileTheme copyWith({
    PixelPreviewProfile? profile,
    Color? accentInk,
    double? pixelStep,
    List<double>? cornerCut,
    PixelStateMotion? stateMotion,
  }) =>
      PixelProfileTheme(
        profile: profile ?? this.profile,
        accentInk: accentInk ?? this.accentInk,
        pixelStep: pixelStep ?? this.pixelStep,
        cornerCut: cornerCut ?? this.cornerCut,
        stateMotion: stateMotion ?? this.stateMotion,
      );

  @override
  PixelProfileTheme lerp(ThemeExtension<PixelProfileTheme>? other, double t) {
    if (other is! PixelProfileTheme) return this;
    return PixelProfileTheme(
      profile: t < 0.5 ? profile : other.profile,
      accentInk: Color.lerp(accentInk, other.accentInk, t)!,
      pixelStep: lerpDouble(pixelStep, other.pixelStep, t)!,
      cornerCut: List<double>.generate(
        cornerCut.length,
        (i) => lerpDouble(
          cornerCut[i],
          other.cornerCut[i % other.cornerCut.length],
          t,
        )!,
      ),
      stateMotion: stateMotion.lerp(other.stateMotion, t),
    );
  }

  @override
  bool operator ==(Object other) =>
      other is PixelProfileTheme &&
      other.profile == profile &&
      other.pixelStep == pixelStep &&
      other.accentInk == accentInk &&
      other.stateMotion == stateMotion &&
      listEquals(other.cornerCut, cornerCut);

  @override
  int get hashCode => Object.hash(
        profile,
        pixelStep,
        accentInk,
        stateMotion,
        Object.hashAll(cornerCut),
      );
}
