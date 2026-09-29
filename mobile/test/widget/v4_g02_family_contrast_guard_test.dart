// V4-G02 · 对话/卡住/Hybrid/运行台 家族四风格对比度守卫。
//
// 规格权威：v4/02_design/ACCESSIBILITY_ASSETS.md（正文 ≥4.5:1，大字/非文字
// 关键部件 ≥3:1）+ SCREEN_FAMILIES.md「对话/卡住/Hybrid/运行台」行。判例同
// pixel_preview_theme_test.dart（WCAG 2.x 相对亮度对比度，F01 落法）与
// F06 判例（pixel_a11y_f06_test.dart）。
//
// 走查面 = 家族关键屏的真实配对（对话气泡/流式·落定代码块/跳最新胶囊/
// Aurora 状态行胶囊/Hybrid 状态徽章/卡住 QuietChip/资料前门徽章/运行台
// tone 胶囊），classic/paperDay/dusk/quiet 逐对复算。半透明面按 alpha
// 解析合成到最近不透明宿主面后计算（与像素采样等价）。
import 'dart:io' as io;
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';

double _srgbChannelToF(int v) {
  final c = v / 255.0;
  return c <= 0.04045
      ? c / 12.92
      : math.pow((c + 0.055) / 1.055, 2.4).toDouble();
}

double _relativeLuminance(Color c) =>
    0.2126 * _srgbChannelToF((c.r * 255.0).round()) +
    0.7152 * _srgbChannelToF((c.g * 255.0).round()) +
    0.0722 * _srgbChannelToF((c.b * 255.0).round());

double contrastRatio(Color a, Color b) {
  final la = _relativeLuminance(a);
  final lb = _relativeLuminance(b);
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

/// alpha 前景合成到不透明底（等价于像素采样）。
Color composite(Color fg, Color bg) => Color.fromARGB(
      255,
      ((fg.r * 255.0 * fg.a) + (bg.r * 255.0 * (1 - fg.a))).round(),
      ((fg.g * 255.0 * fg.a) + (bg.g * 255.0 * (1 - fg.a))).round(),
      ((fg.b * 255.0 * fg.a) + (bg.b * 255.0 * (1 - fg.a))).round(),
    );

const List<PixelPreviewProfile> _profiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

String _label(PixelPreviewProfile p) => switch (p) {
      PixelPreviewProfile.classic => 'classic',
      PixelPreviewProfile.paperDay => 'paperDay',
      PixelPreviewProfile.dusk => 'dusk',
      PixelPreviewProfile.quiet => 'quiet',
    };

/// 家族配对表：每组 (名, 前景, 底, 阈值)。
/// 家族状态行/胶囊文本均为 12sp 元数据级 → 全部按正文阈 4.5；
/// 描边按非文字关键部件阈 3.0（ACCESSIBILITY_ASSETS.md）。
List<(String, Color, Color, double)> _familyPairs(PixelPreviewProfile profile) {
  final scaffold = DS.surfacePrimary; // 家族屏宿主面（scaffold 同源）
  final sheetCard = DS.surfaceSecondary; // 卡住 sheet / 状态卡不透明宿主
  final isDark = _relativeLuminance(DS.surfacePrimary) < 0.5;

  // 跳最新胶囊面（chat_screen：surfaceOverlay 0.92 叠列表宿主面）。
  final capsuleFace = composite(DS.surfaceOverlay, scaffold);
  // 卡住卡 QuietChip 面（task_stuck_card：surfaceSecondary@0.7 叠卡面）。
  // G02-D3 修后：描边升级 border 槽（borderSubtle classic 1.22:1 不达阈）。
  final quietChipFace = composite(
    DS.surfaceSecondary.withValues(alpha: 0.7),
    sheetCard,
  );
  // Aurora 状态行容器两端（status_awareness_bar _BarContainer 渐变）。
  final barFaceToneEnd = composite(DS.info.withValues(alpha: 0.10), scaffold);
  final barFaceMainEnd = composite(
    DS.surfaceSecondary.withValues(alpha: 0.96),
    scaffold,
  );
  // 流式代码块面（chat_screen _StreamingBubble：浅档 ink@6% 叠气泡面；
  // 深档与落定路径同源 surfaceTertiary——G02-D1 修正后口径）。
  final streamingCodeFace = isDark
      ? DS.surfaceTertiary
      : composite(
          DS.chatBubbleOtherText.withValues(alpha: 0.06),
          DS.chatBubbleOther,
        );

  // 胶囊/徽章 tone 文本所在面：tone@10% 叠宿主（家族统一低透 tint 律；
  // 取最小 alpha 端 = 对比最不利端）。文字色 = DS.toneOnTint(tone)，
  // 与家族出厂配对一致（status_awareness_bar/agent_workflow_panel/
  // profile_front_door_card/openclaw_primitives 均走该收敛槽）。
  Color tintFace(Color tone, Color host) =>
      composite(tone.withValues(alpha: 0.10), host);

  Color toneText(Color tone) => DS.toneOnTint(tone);

  final bandTones = <String, Color>{
    'success': DS.semanticSuccess,
    'warning': DS.semanticWarning,
    'info': DS.info,
    'accent': DS.brandPrimary,
    'muted': DS.textSecondary,
  };

  return [
    // ── 对话（chat_screen/chat_bubble）──────────────────────────────
    (
      '对话·用户气泡文/气泡面',
      DS.chatBubbleUserText,
      DS.chatBubbleUser,
      4.5,
    ),
    (
      '对话·助手气泡文/气泡面',
      DS.chatBubbleOtherText,
      DS.chatBubbleOther,
      4.5,
    ),
    (
      '对话·落定代码块文/码面',
      DS.chatBubbleOtherText,
      DS.surfaceTertiary,
      4.5,
    ),
    (
      '对话·流式代码块文/码面',
      DS.chatBubbleOtherText,
      streamingCodeFace,
      4.5,
    ),
    (
      '对话·跳最新胶囊文/胶囊面',
      DS.textSecondary,
      capsuleFace,
      4.5,
    ),
    // ── 卡住 sheet（task_stuck_card）────────────────────────────────
    ('卡住·正文/卡面', DS.textPrimary, sheetCard, 4.5),
    ('卡住·QuietChip 文/胶囊面', DS.textSecondary, quietChipFace, 4.5),
    // G02-D3：描边升 neutral600（border/borderSubtle/neutral500 classic
    // 1.22-2.85:1 递进不足）。
    ('卡住·QuietChip 描边/胶囊面', DS.neutral600, quietChipFace, 3.0),
    // ── Aurora 状态行（status_awareness_bar，工具阶段辨识度）────────
    ('状态行·判定文/tint端面', DS.textPrimary, barFaceToneEnd, 4.5),
    ('状态行·次级文/主段面', DS.textSecondary, barFaceMainEnd, 4.5),
    for (final entry in bandTones.entries)
      (
        '状态行·Band 胶囊 ${entry.key} 文/胶囊面',
        toneText(entry.value),
        tintFace(entry.value, barFaceMainEnd),
        4.5,
      ),
    // ── Hybrid 工作流（agent_workflow_panel）───────────────────────
    (
      'Hybrid·页脚横幅文/横幅面',
      AppThemes.lightTheme.colorScheme.primary,
      composite(
        AppThemes.lightTheme.colorScheme.primary.withValues(alpha: 0.06),
        sheetCard,
      ),
      4.5,
    ),
    (
      'Hybrid·错误状态徽章文/徽章面',
      toneText(DS.semanticError),
      composite(DS.semanticError.withValues(alpha: 0.10), sheetCard),
      4.5,
    ),
    // ── 资料前门（profile_front_door_card，G02 修后令牌对）──────────
    (
      '前门·确认区标题文/确认面',
      DS.textPrimary,
      composite(DS.semanticSuccess.withValues(alpha: 0.10), sheetCard),
      4.5,
    ),
    (
      '前门·预测徽章文/徽章面',
      toneText(DS.taskReflection),
      composite(DS.taskReflection.withValues(alpha: 0.08), sheetCard),
      4.5,
    ),
    // ── 运行台（openclaw_primitives：tone 胶囊族）───────────────────
    for (final tone in <Color>[
      DS.semanticSuccess,
      DS.semanticWarning,
      DS.info,
      DS.brandPrimary,
    ]) ...[
      (
        '运行台·tone #${tone.toARGB32().toRadixString(16)} 标题文/胶囊面',
        toneText(tone),
        tintFace(tone, scaffold),
        4.5,
      ),
      (
        '运行台·tone #${tone.toARGB32().toRadixString(16)} 次级文/胶囊面',
        DS.textSecondary,
        tintFace(tone, scaffold),
        4.5,
      ),
    ],
  ];
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  for (final profile in _profiles) {
    group('V4-G02 四风格对比度 · ${_label(profile)}', () {
      setUp(() async {
        SharedPreferences.setMockInitialValues(<String, Object>{});
        final manager = ThemeManager();
        await manager.reset();
        await manager.initialize();
        await manager.setPixelPreviewProfile(profile);
      });

      test('家族关键配对全部达阈（文本≥4.5 / 描边≥3）', () {
        final failures = <String>[];
        for (final (name, fg, bg, min) in _familyPairs(profile)) {
          final ratio = contrastRatio(fg, bg);
          if (ratio < min) {
            failures.add(
              '$name = ${ratio.toStringAsFixed(2)}:1 < $min:1 '
              '(fg=#${fg.toARGB32().toRadixString(16)}, '
              'bg=#${bg.toARGB32().toRadixString(16)})',
            );
          }
        }
        expect(
          failures,
          isEmpty,
          reason:
              '${_label(profile)} 风格下家族对比度缺陷：\n${failures.join('\n')}',
        );
      });
    });
  }

  test('透明度压文字禁令（SPEC §1.3.1）：家族呈现层零 alpha 衰减文本槽', () {
    // 家族呈现层源扫描：textSecondary/textTertiary 不允许再叠 withValues
    // alpha 压灰（第四文字级禁令；G02 修掉的 5 处回归钉）。扫描口径与
    // UI-TOKENS 棘轮同（注释行剔除）。
    const familyRoots = [
      'lib/features/chat/presentation',
      'lib/features/aurora/presentation',
      'lib/features/openclaw/presentation',
    ];
    final pattern = RegExp(
      r'(DS\.textSecondary|DS\.textTertiary)\.withValues\(alpha:',
    );
    final hits = <String>[];
    for (final root in familyRoots) {
      final dir = io.Directory(root);
      if (!dir.existsSync()) continue;
      for (final entity in dir.listSync(recursive: true)) {
        if (entity is! io.File || !entity.path.endsWith('.dart')) continue;
        final lines = entity.readAsStringSync().split('\n');
        for (var i = 0; i < lines.length; i++) {
          final s = lines[i].trim();
          if (s.startsWith('//') || s.startsWith('*')) continue;
          if (pattern.hasMatch(lines[i])) {
            hits.add('${entity.path} 第${i + 1}行: $s');
          }
        }
      }
    }
    expect(hits, isEmpty, reason: '透明度压文字回归：\n${hits.join('\n')}');
  });
}
