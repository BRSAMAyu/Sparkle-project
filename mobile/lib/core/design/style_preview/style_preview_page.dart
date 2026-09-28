/// V4-F05 · 可替换设计 Preview 与主题切换 —— 真实 Flutter 内部预览页。
///
/// **PROPOSED_NOT_APPROVED**：本页是候选主题（paper_day / dusk / quiet）
/// 的开发预览通道 UI（F01 让渡面，锁 style-preview 归本卡）。参考图是提案
/// 不是批准——本页只存在于 `AppFeatureFlags.enableStylePreview`（默认
/// **false**）之后的「我的」页开发者入口，不进五 Tab 合同、不在发布面出现；
/// 切档走 F01 唯一编程入口 [ThemeManager.setPixelPreviewProfile]，classic
/// （默认）= preview 关、发布面零差量，随时可回退。
///
/// 三条卡验收的机制面（每条可失败，测试钉死于
/// `test/core/design/style_preview/`）：
///
/// 1. **设计未批准时稳定主题仍可用，preview 不隐性全量上线**——入口 flag
///    默认关（[StylePreviewEntry.gate] 反例钉死）；页面在 classic 下正常
///    渲染且无 PixelProfileTheme 扩展（稳定主题路径零差量）。
/// 2. **切主题不重启 run / 清数据 / 改 token 用量**——切档只调
///    [ThemeManager.setPixelPreviewProfile]（仅写 pixel 键 + notifyListeners，
///    见 F01）；页面用 [AnimatedBuilder] 监听单例，应用根部经
///    themeManagerProvider 同机制重建，页面 State 不重挂（输入框/滚动位
///    置存活），其它 prefs 键零触碰。
/// 3. **五面状态截图附相同 build 与数据 seed**——五面 = [StylePreviewFace]
///    真实表面组件 + [kStylePreviewSeedVersion] 冻结 seed；「同一状态流」
///    = [StylePreviewFlowStep] 四步封闭流（F03 冻结文案表 + F02 徽章族），
///    一个控制器驱动五面；证据采集测试（evidence_test）按 env 落盘
///    5 面 × 4 档（classic + 三候选）截图与语义 dump，同进程同 seed。
library;

import 'package:flutter/material.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/style_preview/style_preview_faces.dart';
import 'package:sparkle/core/design/style_preview/style_preview_seed.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

/// 「我的」页开发者入口 gate：flag 关（默认）→ 零节点（发布面零差量）；
/// flag 开 → 开发者入口 tile。独立组件以便反例测试直接钉 gate 行为
/// （profile_screen.dart 只消费本组件，不复制判定）。
class StylePreviewEntry extends StatelessWidget {
  const StylePreviewEntry({super.key});

  @override
  Widget build(BuildContext context) {
    // 常量读的是 lib/core/constants/app_constants.dart 的静态 flag（默认
    // false）：设计未批准前入口不存在，preview 不隐性全量上线。
    if (!AppFeatureFlags.enableStylePreview) return const SizedBox.shrink();
    return ListTile(
      key: const ValueKey('style-preview-entry-tile'),
      leading: const Icon(Icons.palette_outlined),
      title: const Text('风格预览（开发者）'),
      subtitle: const Text('像素候选主题 · 未批准提案，仅本机预览'),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute<void>(builder: (_) => const StylePreviewPage()),
      ),
    );
  }
}

/// 内部预览页。
class StylePreviewPage extends StatefulWidget {
  const StylePreviewPage({super.key});

  @override
  State<StylePreviewPage> createState() => StylePreviewPageState();
}

@visibleForTesting
class StylePreviewPageState extends State<StylePreviewPage> {
  /// 同一状态流的当前步（一个控制器驱动五面）。
  StylePreviewFlowStep _flowStep = kStylePreviewFlowSteps.first;

  /// 流步推进/重放（重放 = 回到第一步后按序推进的能力由测试/采集面复用）。
  void advanceFlow() {
    final next = kStylePreviewFlowSteps.indexOf(_flowStep) + 1;
    setState(() {
      _flowStep = kStylePreviewFlowSteps[
          next >= kStylePreviewFlowSteps.length ? 0 : next];
    });
  }

  @visibleForTesting
  StylePreviewFlowStep get flowStep => _flowStep;

  Future<void> _selectProfile(PixelPreviewProfile profile) =>
      ThemeManager().setPixelPreviewProfile(profile);

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
      animation: ThemeManager(),
      builder: (context, _) {
        final manager = ThemeManager();
        final pixel = PixelProfileTheme.of(context);
        return Scaffold(
          appBar: AppBar(
            title: const Text('风格预览'),
            actions: [
              // 提案状态常显（不冒充已定版）。
              Padding(
                padding: const EdgeInsets.only(right: DS.spacing12),
                child: Chip(
                  avatar: Icon(
                    Icons.warning_amber_rounded,
                    size: 16,
                    color: Theme.of(context).colorScheme.error,
                  ),
                  label: Text(
                    'PROPOSED · 未批准',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
          body: ListView(
            key: const ValueKey('style-preview-list'),
            padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                ),
                child: Text(
                  '候选主题只在 preview 通道生效；classic = 关（发布默认）。'
                  'seed ${kStylePreviewSeedVersion.split('-').take(2).join('-')} · '
                  '${pixel == null ? '像素扩展未挂载' : '像素扩展已挂载'}',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: context.sparkle.colors.textSecondary,
                      ),
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                child: SegmentedButton<PixelPreviewProfile>(
                  key: const ValueKey('style-preview-profile-switcher'),
                  segments: const [
                    ButtonSegment(
                      value: PixelPreviewProfile.classic,
                      label: Text('classic'),
                      icon: Icon(Icons.toggle_off_outlined),
                    ),
                    ButtonSegment(
                      value: PixelPreviewProfile.paperDay,
                      label: Text('纸昼'),
                      icon: Icon(Icons.light_mode_outlined),
                    ),
                    ButtonSegment(
                      value: PixelPreviewProfile.dusk,
                      label: Text('暮色'),
                      icon: Icon(Icons.dark_mode_outlined),
                    ),
                    ButtonSegment(
                      value: PixelPreviewProfile.quiet,
                      label: Text('低刺激'),
                      icon: Icon(Icons.volume_off_outlined),
                    ),
                  ],
                  selected: {manager.pixelPreviewProfile},
                  onSelectionChanged: (selection) =>
                      _selectProfile(selection.first),
                ),
              ),
              const SizedBox(height: DS.spacing8),
              // 同一状态流控制器（五面共用；文案 = F03 冻结表）。
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                child: Row(
                  children: [
                    Text(
                      '状态流：${StylePreviewFlowFrame.of(_flowStep).copy}',
                      style: Theme.of(context).textTheme.labelMedium,
                    ),
                    const Spacer(),
                    TextButton.icon(
                      key: const ValueKey('style-preview-flow-advance'),
                      onPressed: advanceFlow,
                      icon: const Icon(Icons.play_arrow, size: 16),
                      label: const Text('推进'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing4),
              // 五面（真实表面组件 + seed；证据采集逐面截图同源）。
              StylePreviewFaceCard(
                key: const ValueKey('style-preview-face-home'),
                face: StylePreviewFace.home,
                frame: StylePreviewFlowFrame.of(_flowStep),
                child: StylePreviewHomeFace(step: _flowStep),
              ),
              StylePreviewFaceCard(
                key: const ValueKey('style-preview-face-stuckSheet'),
                face: StylePreviewFace.stuckSheet,
                frame: StylePreviewFlowFrame.of(_flowStep),
                child: const StylePreviewStuckSheetFace(),
              ),
              StylePreviewFaceCard(
                key: const ValueKey('style-preview-face-memory'),
                face: StylePreviewFace.memory,
                frame: StylePreviewFlowFrame.of(_flowStep),
                child: StylePreviewMemoryFace(step: _flowStep),
              ),
              StylePreviewFaceCard(
                key: const ValueKey('style-preview-face-longAnswer'),
                face: StylePreviewFace.longAnswer,
                frame: StylePreviewFlowFrame.of(_flowStep),
                child: StylePreviewLongAnswerFace(step: _flowStep),
              ),
              StylePreviewFaceCard(
                key: const ValueKey('style-preview-face-starMap'),
                face: StylePreviewFace.starMap,
                frame: StylePreviewFlowFrame.of(_flowStep),
                child: StylePreviewStarMapFace(step: _flowStep),
              ),
            ],
          ),
        );
      },
    );
}
