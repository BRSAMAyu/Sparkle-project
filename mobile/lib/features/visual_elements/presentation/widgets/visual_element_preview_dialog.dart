import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/background_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/effect_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/particle_layer.dart';
import 'package:sparkle/features/visual_elements/presentation/shared/visual_element_palette.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 视觉元素预览对话框
class VisualElementPreviewDialog extends StatefulWidget {
  const VisualElementPreviewDialog({
    required this.element,
    super.key,
    this.availableElements = const <VisualElementModel>[],
    this.unlockedElementIds = const <String>{},
    this.scrollController,
    this.baseConfig,
    this.onEquip,
    this.onUnequip,
    this.isEquipped = false,
    this.isUnlocked = false,
  });

  final VisualElementModel element;
  final List<VisualElementModel> availableElements;
  final Set<String> unlockedElementIds;
  final ScrollController? scrollController;
  final UserVisualConfig? baseConfig;
  final VoidCallback? onEquip;
  final VoidCallback? onUnequip;
  final bool isEquipped;
  final bool isUnlocked;

  static Future<void> show(
    BuildContext context, {
    required VisualElementModel element,
    List<VisualElementModel> availableElements = const <VisualElementModel>[],
    Set<String> unlockedElementIds = const <String>{},
    UserVisualConfig? baseConfig,
    VoidCallback? onEquip,
    VoidCallback? onUnequip,
    bool isEquipped = false,
    bool isUnlocked = false,
  }) =>
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => DraggableScrollableSheet(
          initialChildSize: 0.72,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          builder: (context, scrollController) => VisualElementPreviewDialog(
            element: element,
            availableElements: availableElements,
            unlockedElementIds: unlockedElementIds,
            scrollController: scrollController,
            baseConfig: baseConfig,
            onEquip: onEquip,
            onUnequip: onUnequip,
            isEquipped: isEquipped,
            isUnlocked: isUnlocked,
          ),
        ),
      );

  @override
  State<VisualElementPreviewDialog> createState() =>
      _VisualElementPreviewDialogState();
}

class _VisualElementPreviewDialogState extends State<VisualElementPreviewDialog>
    with SingleTickerProviderStateMixin {
  final GlobalKey _previewKey = GlobalKey();
  bool _isPreviewing = true;
  bool _isSharing = false;
  bool _showConfetti = false;

  late ConfettiController _confettiController;
  late AnimationController _crossfadeController;
  late Animation<double> _crossfadeAnimation;

  @override
  void initState() {
    super.initState();
    _confettiController = ConfettiController(duration: DS.durationSlow);
    _crossfadeController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _crossfadeAnimation = CurvedAnimation(
      parent: _crossfadeController,
      curve: Curves.easeInOut,
    );
    _crossfadeController.value = 1.0;
  }

  @override
  void dispose() {
    _confettiController.dispose();
    _crossfadeController.dispose();
    super.dispose();
  }

  void _handleEquip() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    setState(() => _showConfetti = true);
    _confettiController.play();
    // Delay callback to let confetti start
    Future.delayed(const Duration(milliseconds: 300), widget.onEquip);
  }

  void _togglePreviewMode() {
    if (_isPreviewing) {
      _crossfadeController.reverse(from: 1.0);
    } else {
      _crossfadeController.forward(from: 0.0);
    }
    setState(() => _isPreviewing = !_isPreviewing);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final palette = VisualElementPalette.of(context);
    final colors = _getRarityColors(widget.element.rarity);

    return Stack(
      children: [
        Container(
          decoration: BoxDecoration(
            color: palette.moonless,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            border: Border(
              top: BorderSide(
                color: colors.border.withValues(alpha: 0.36),
              ),
            ),
          ),
          child: Column(
            children: [
              // 拖动条
              Container(
                margin: const EdgeInsets.only(top: DS.spacing12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: palette.textSecondary.withValues(alpha: 0.38),
                  borderRadius: DS.borderRadiusFull,
                ),
              ),

              Expanded(
                child: CustomScrollView(
                  controller: widget.scrollController,
                  slivers: [
                    // 预览区域 (带交叉淡入淡出)
                    SliverToBoxAdapter(
                      child: RepaintBoundary(
                        key: _previewKey,
                        child: _CrossfadePreviewArea(
                          element: widget.element,
                          availableElements: widget.availableElements,
                          baseConfig: widget.baseConfig,
                          colors: colors,
                          isPreviewing: _isPreviewing,
                          crossfadeAnimation: _crossfadeAnimation,
                          onTogglePreview: _togglePreviewMode,
                        ),
                      ),
                    ),

                    // 信息区域
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.all(DS.spacing16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // 名称和稀有度
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final compact = constraints.maxWidth < 360;
                                if (compact) {
                                  return Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        widget.element.name,
                                        style: TextStyle(
                                          fontSize: DS.fontSizeLg,
                                          fontWeight: DS.fontWeightBold,
                                          color: palette.textPrimary,
                                          height: 1.15,
                                        ),
                                        maxLines: 4,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: DS.spacing8),
                                      _RarityBadge(
                                        rarity: widget.element.rarity,
                                        colors: colors,
                                        l10n: l10n,
                                      ),
                                    ],
                                  );
                                }
                                return Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Expanded(
                                      child: Text(
                                        widget.element.name,
                                        style: TextStyle(
                                          fontSize: DS.fontSizeLg,
                                          fontWeight: DS.fontWeightBold,
                                          color: palette.textPrimary,
                                          height: 1.15,
                                        ),
                                        maxLines: 3,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    const SizedBox(width: DS.spacing8),
                                    _RarityBadge(
                                      rarity: widget.element.rarity,
                                      colors: colors,
                                      l10n: l10n,
                                    ),
                                  ],
                                );
                              },
                            ),

                            if (widget.element.description != null) ...[
                              const SizedBox(height: DS.spacing8),
                              SelectionArea(
                                child: Text(
                                  widget.element.description!,
                                  style: TextStyle(
                                    fontSize: DS.fontSizeSm,
                                    color: palette.textSecondary,
                                    height: 1.5,
                                  ),
                                ),
                              ),
                            ],

                            const SizedBox(height: DS.spacing12),
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                _MetaChip(
                                  label: widget.element.displaySlotLabel,
                                  color: colors.text,
                                ),
                                _MetaChip(
                                  label: widget.element.unlockSourceLabel,
                                  color: colors.border,
                                ),
                                if (widget.element.setId != null)
                                  _MetaChip(
                                    label: widget.element.setId!,
                                    color: DS.brandPrimary,
                                  ),
                              ],
                            ),

                            const SizedBox(height: DS.spacing16),
                            Divider(
                              color: palette.hairline,
                            ),
                            const SizedBox(height: DS.spacing16),

                            // 详细信息
                            _InfoRow(
                              label: l10n.visualElementType,
                              value: _getElementTypeName(
                                widget.element.elementType,
                                l10n,
                              ),
                            ),
                            if (widget.element.category != null)
                              _InfoRow(
                                label: l10n.visualElementCategory,
                                value: _getCategoryName(
                                  widget.element.category!,
                                  l10n,
                                ),
                              ),
                            _InfoRow(
                              label: l10n.visualElementSource,
                              value: _getUnlockSourceText(
                                widget.element.unlockSource,
                                l10n,
                              ),
                            ),
                            _InfoRow(
                              label: context.l10n.visualAffectedScenes,
                              value: widget.element.affectedSurfaceLabels
                                  .join(' · '),
                            ),
                            if (widget.element.isBundle &&
                                widget.element.bundlePieceIds.isNotEmpty)
                              _InfoRow(
                                label: context.l10n.visualCollectionProgress,
                                value: _bundleCompletionText(),
                              ),
                            if (widget.element.isBundle &&
                                widget.element.bundlePieceIds.isNotEmpty)
                              _InfoRow(
                                label: context.l10n.visualSetParts,
                                value: _bundlePieceLabels().join(' · '),
                              ),

                            const SizedBox(height: DS.spacing24),

                            // 解锁条件
                            if (!widget.isUnlocked)
                              _UnlockRequirement(
                                element: widget.element,
                                l10n: l10n,
                              ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // 底部操作按钮
              _buildActionButtons(l10n),
            ],
          ),
        ),

        // Confetti 效果
        if (_showConfetti)
          Align(
            alignment: Alignment.topCenter,
            child: ConfettiWidget(
              confettiController: _confettiController,
              blastDirectionality: BlastDirectionality.explosive,
              colors: [
                DS.brandPrimary,
                DS.brandSecondary,
                DS.warning,
                DS.success,
              ],
              emissionFrequency: 0.05,
              numberOfParticles: 30,
              maxBlastForce: 100,
              minBlastForce: 80,
            ),
          ),
      ],
    );
  }

  Widget _buildActionButtons(AppLocalizations l10n) => Container(
        padding: EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing12,
          DS.spacing16,
          MediaQuery.of(context).padding.bottom + DS.spacing12,
        ),
        decoration: BoxDecoration(
          color: VisualElementPalette.of(context).moonless,
          border: Border(
            top: BorderSide(color: VisualElementPalette.of(context).hairline),
          ),
        ),
        child: SafeArea(
          top: false,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final stackActions = constraints.maxWidth < 520;
              final shareWidth = stackActions ? constraints.maxWidth : 140.0;
              final actionWidth = stackActions
                  ? constraints.maxWidth
                  : constraints.maxWidth - 152;
              return Wrap(
                spacing: DS.spacing12,
                runSpacing: DS.spacing12,
                children: [
                  SizedBox(
                    width: shareWidth,
                    child: _buildShareButton(l10n),
                  ),
                  SizedBox(
                    width: actionWidth,
                    child: widget.isEquipped
                        ? _buildUnequipButton(l10n)
                        : widget.isUnlocked
                            ? _buildEquipButton(l10n)
                            : _buildLockedButton(l10n),
                  ),
                ],
              );
            },
          ),
        ),
      );

  Widget _buildShareButton(AppLocalizations l10n) => SizedBox(
        height: 48,
        child: OutlinedButton.icon(
          onPressed: _isSharing ? null : _sharePreview,
          icon: _isSharing
              ? SizedBox(
                  width: DS.iconSizeSm,
                  height: DS.iconSizeSm,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(DS.brandPrimary),
                  ),
                )
              : const Icon(Icons.share_outlined),
          label: Text(
            l10n.visualElementShare,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          style: OutlinedButton.styleFrom(
            foregroundColor: VisualElementPalette.of(context).textSecondary,
            side: BorderSide(color: VisualElementPalette.of(context).hairline),
            shape: const RoundedRectangleBorder(
              borderRadius: DS.borderRadius12,
            ),
          ),
        ),
      );

  Widget _buildEquipButton(AppLocalizations l10n) {
    final zh = I18nService.instance.isChinese;
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton.icon(
        onPressed: _handleEquip,
        icon: Icon(
          widget.element.isBundle
              ? Icons.auto_awesome_rounded
              : Icons.check_circle_outline,
        ),
        label: Text(
          widget.element.isBundle
              ? (zh ? '一键装备套装' : 'Equip Bundle')
              : l10n.visualElementEquip,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: VisualElementPalette.of(context).gold,
          foregroundColor: VisualElementPalette.of(context).moonless,
          shape: const RoundedRectangleBorder(
            borderRadius: DS.borderRadius12,
          ),
        ),
      ),
    );
  }

  Widget _buildUnequipButton(AppLocalizations l10n) {
    final zh = I18nService.instance.isChinese;
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: OutlinedButton.icon(
        onPressed: widget.onUnequip,
        icon: const Icon(Icons.remove_circle_outline),
        label: Text(
          widget.element.isBundle
              ? (zh ? '卸下整套' : 'Unequip Bundle')
              : l10n.visualElementUnequip,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        style: OutlinedButton.styleFrom(
          foregroundColor: VisualElementPalette.of(context).textSecondary,
          side: BorderSide(color: VisualElementPalette.of(context).hairline),
          shape: const RoundedRectangleBorder(
            borderRadius: DS.borderRadius12,
          ),
        ),
      ),
    );
  }

  Widget _buildLockedButton(AppLocalizations l10n) => SizedBox(
        width: double.infinity,
        height: 48,
        child: ElevatedButton.icon(
          onPressed: null,
          icon: const Icon(Icons.lock_outline),
          label: Text(
            l10n.visualElementLocked,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: VisualElementPalette.of(context).panel,
            foregroundColor: VisualElementPalette.of(context).textSecondary,
            shape: const RoundedRectangleBorder(
              borderRadius: DS.borderRadius12,
            ),
          ),
        ),
      );

  Future<void> _sharePreview() async {
    final boundary = _previewKey.currentContext?.findRenderObject()
        as RenderRepaintBoundary?;
    if (boundary == null) {
      AppFeedback.error(
        context,
        context.l10n.visualElementShareUnavailable,
      );
      return;
    }

    setState(() => _isSharing = true);

    try {
      final image = await boundary.toImage(pixelRatio: 3.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      if (byteData == null) {
        throw Exception('Share image is empty');
      }

      final pngBytes = byteData.buffer.asUint8List();
      final tempDir = await getTemporaryDirectory();
      final file = File(
        '${tempDir.path}/visual_element_${widget.element.id}_${DateTime.now().millisecondsSinceEpoch}.png',
      );
      await file.writeAsBytes(pngBytes, flush: true);

      await share_plus.SharePlus.instance.share(
        share_plus.ShareParams(
          files: [share_plus.XFile(file.path)],
          text: context.l10n.visualElementShareMessage(widget.element.name),
        ),
      );
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.visualElementShareFailed(e.toString()),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSharing = false);
      }
    }
  }

  String _getElementTypeName(
    VisualElementType type,
    AppLocalizations l10n,
  ) {
    switch (type) {
      case VisualElementType.background:
        return l10n.visualElementBackground;
      case VisualElementType.particle:
        return l10n.visualElementParticle;
      case VisualElementType.effect:
        return l10n.visualElementEffect;
      case VisualElementType.bundle:
        return l10n.visualElementBundle;
    }
  }

  String _getCategoryName(String category, AppLocalizations l10n) {
    final names = {
      'space': l10n.visualElementCategorySpace,
      'nature': l10n.visualElementCategoryNature,
      'cyberpunk': l10n.visualElementCategoryCyberpunk,
      'abstract': l10n.visualElementCategoryAbstract,
      'ambient': l10n.visualElementCategoryAmbient,
    };
    return names[category] ?? category;
  }

  VisualElementRarityColors _getRarityColors(VisualElementRarity rarity) =>
      VisualElementPalette.of(context).rarityColors(rarity);

  String _getUnlockSourceText(
    VisualElementUnlockSource source,
    AppLocalizations l10n,
  ) {
    switch (source) {
      case VisualElementUnlockSource.system:
        return l10n.visualElementUnlockSystem;
      case VisualElementUnlockSource.achievement:
        return l10n.visualElementUnlockAchievement;
      case VisualElementUnlockSource.shop:
        return l10n.visualElementUnlockShop;
      case VisualElementUnlockSource.event:
        return l10n.visualElementUnlockEvent;
      case VisualElementUnlockSource.season:
        return l10n.visualElementUnlockSeason;
    }
  }

  List<String> _bundlePieceLabels() {
    if (!widget.element.isBundle) return const [];
    final byId = <String, VisualElementModel>{
      for (final element in widget.availableElements) element.id: element,
    };

    return widget.element.bundlePieceIds
        .map((id) => byId[id]?.name ?? id)
        .toList();
  }

  String _bundleCompletionText() {
    final zh = I18nService.instance.isChinese;
    if (!widget.element.isBundle) {
      return '0 / 0 ${zh ? '已集齐' : 'Collected'}';
    }
    final total = widget.element.bundlePieceIds.length;
    final owned = widget.element.bundlePieceIds
        .where((id) => widget.unlockedElementIds.contains(id))
        .length;
    return '$owned / $total ${zh ? '已集齐' : 'Collected'}';
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width < 360 ? 132 : 180,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.13),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: color.withValues(alpha: 0.24)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: Color.lerp(color, VisualElementPalette.textPrimary, 0.12),
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );
}

class _StageChip extends StatelessWidget {
  const _StageChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: DS.borderRadiusFull,
        child: BackdropFilter(
          filter: ui.ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing10,
              vertical: DS.spacing6,
            ),
            decoration: BoxDecoration(
              color: VisualElementPalette.moonless.withValues(alpha: 0.58),
              borderRadius: DS.borderRadiusFull,
              border: Border.all(color: color.withValues(alpha: 0.28)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: DS.iconSizeXs, color: color),
                const SizedBox(width: DS.spacing4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: Color.lerp(
                        color, VisualElementPalette.textPrimary, 0.18),
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _PreviewSurfaceMock extends StatelessWidget {
  const _PreviewSurfaceMock({
    required this.element,
    required this.colors,
    required this.isPreviewing,
  });

  final VisualElementModel element;
  final VisualElementRarityColors colors;
  final bool isPreviewing;

  @override
  Widget build(BuildContext context) {
    final compactStage = MediaQuery.sizeOf(context).width < 380;
    final zh = I18nService.instance.isChinese;
    return Positioned.fill(
      child: IgnorePointer(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            compactStage ? DS.spacing12 : DS.spacing18,
            compactStage ? 58 : 72,
            compactStage ? DS.spacing12 : DS.spacing18,
            compactStage ? DS.spacing12 : DS.spacing18,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              ClipRRect(
                borderRadius: DS.borderRadius16,
                child: BackdropFilter(
                  filter: ui.ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                  child: Container(
                    width: double.infinity,
                    padding: EdgeInsets.all(
                      compactStage ? DS.spacing10 : DS.spacing14,
                    ),
                    decoration: BoxDecoration(
                      color:
                          VisualElementPalette.moonless.withValues(alpha: 0.52),
                      borderRadius: DS.borderRadius16,
                      border: Border.all(
                        color: colors.border.withValues(alpha: 0.22),
                      ),
                    ),
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final compact = constraints.maxWidth < 320;
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  width: compactStage ? 34 : 42,
                                  height: compactStage ? 34 : 42,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: RadialGradient(
                                      colors: [
                                        colors.border.withValues(alpha: 0.85),
                                        colors.border.withValues(alpha: 0.16),
                                        Colors.transparent,
                                      ],
                                    ),
                                    border: Border.all(
                                      color:
                                          colors.text.withValues(alpha: 0.42),
                                    ),
                                  ),
                                  child: Icon(
                                    Icons.person_outline_rounded,
                                    color: VisualElementPalette.textPrimary,
                                    size: DS.iconSizeSm,
                                  ),
                                ),
                                SizedBox(
                                  width:
                                      compactStage ? DS.spacing8 : DS.spacing10,
                                ),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        element.name,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontSize: DS.fontSizeSm,
                                          fontWeight: DS.fontWeightBold,
                                          color:
                                              VisualElementPalette.textPrimary,
                                        ),
                                      ),
                                      const SizedBox(height: DS.spacing4),
                                      Text(
                                        element.affectedSurfaceLabels
                                            .take(2)
                                            .join(' · '),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontSize: DS.fontSizeXs,
                                          color: VisualElementPalette
                                              .textSecondary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(
                              height: compactStage ? DS.spacing8 : DS.spacing12,
                            ),
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                _surfacePill(Icons.home_rounded,
                                    zh ? '主页' : 'Home', colors),
                                _surfacePill(
                                  Icons.account_tree_rounded,
                                  zh ? '星图' : 'Galaxy',
                                  colors,
                                ),
                                if (!compact && !compactStage)
                                  _surfacePill(
                                    Icons.emoji_events_rounded,
                                    zh ? '成就' : 'Achievements',
                                    colors,
                                  ),
                                _surfacePill(
                                  isPreviewing
                                      ? Icons.flash_on_rounded
                                      : Icons.pause_circle_outline_rounded,
                                  isPreviewing
                                      ? (zh ? '即时预览' : 'Live Preview')
                                      : (zh ? '当前配置' : 'Current'),
                                  colors,
                                ),
                              ],
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _surfacePill(
          IconData icon, String label, VisualElementRarityColors colors) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: colors.border.withValues(alpha: 0.13),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: colors.border.withValues(alpha: 0.22)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: DS.iconSizeXs, color: colors.text),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: colors.text,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      );
}

/// 预览区域
class _PreviewArea extends StatefulWidget {
  const _PreviewArea({
    required this.element,
    required this.availableElements,
    required this.baseConfig,
    required this.colors,
    required this.isPreviewing,
    required this.onTogglePreview,
  });

  final VisualElementModel element;
  final List<VisualElementModel> availableElements;
  final UserVisualConfig? baseConfig;
  final VisualElementRarityColors colors;
  final bool isPreviewing;
  final VoidCallback onTogglePreview;

  @override
  State<_PreviewArea> createState() => _PreviewAreaState();
}

class _PreviewAreaState extends State<_PreviewArea>
    with TickerProviderStateMixin {
  late AnimationController _mainController;
  late AnimationController _particleController;

  @override
  void initState() {
    super.initState();
    _mainController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();
  }

  @override
  void dispose() {
    _mainController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final previewConfig = _resolvePreviewConfig();

    return Container(
      height: MediaQuery.sizeOf(context).width < 380 ? 300 : 340,
      margin: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            widget.colors.border.withValues(alpha: 0.24),
            VisualElementPalette.panel,
            VisualElementPalette.surface,
          ],
        ),
        border: Border.all(
          color: widget.colors.border.withValues(alpha: 0.42),
          width: 1.4,
        ),
        boxShadow: [
          BoxShadow(
            color: widget.colors.border.withValues(alpha: 0.14),
            blurRadius: 28,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: Stack(
        children: [
          ClipRRect(
            borderRadius: DS.borderRadius12,
            child: Stack(
              fit: StackFit.expand,
              children: [
                BackgroundLayer(
                  element: previewConfig.equippedBackground,
                  mainAnimation: _mainController,
                ),
                ParticleLayer(
                  element: previewConfig.equippedParticle,
                  particleAnimation: _particleController,
                  mainAnimation: _mainController,
                ),
                EffectLayer(
                  element: previewConfig.equippedEffect,
                  mainAnimation: _mainController,
                ),
              ],
            ),
          ),
          Positioned(
            right: DS.spacing12,
            bottom: DS.spacing12,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: widget.onTogglePreview,
                borderRadius: DS.borderRadius8,
                child: Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    color:
                        VisualElementPalette.moonless.withValues(alpha: 0.72),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    widget.isPreviewing
                        ? Icons.visibility_off
                        : Icons.visibility,
                    size: DS.iconSizeSm,
                    color: VisualElementPalette.textSecondary,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  UserVisualConfig _resolvePreviewConfig() {
    final base = widget.baseConfig;
    if (!widget.isPreviewing) {
      return base ?? UserVisualConfig();
    }

    switch (widget.element.elementType) {
      case VisualElementType.background:
        return UserVisualConfig(
          equippedBackground: widget.element,
          equippedParticle: base?.equippedParticle,
          equippedEffect: base?.equippedEffect,
        );
      case VisualElementType.particle:
        return UserVisualConfig(
          equippedBackground: base?.equippedBackground,
          equippedParticle: widget.element,
          equippedEffect: base?.equippedEffect,
        );
      case VisualElementType.effect:
        return UserVisualConfig(
          equippedBackground: base?.equippedBackground,
          equippedParticle: base?.equippedParticle,
          equippedEffect: widget.element,
        );
      case VisualElementType.bundle:
        return _buildBundlePreviewConfig(base);
    }
  }

  UserVisualConfig _buildBundlePreviewConfig(UserVisualConfig? base) {
    final byId = <String, VisualElementModel>{
      for (final element in widget.availableElements) element.id: element,
    };
    return UserVisualConfig(
      equippedBackground: byId[widget.element.config['background_id']] ??
          base?.equippedBackground,
      equippedParticle:
          byId[widget.element.config['particle_id']] ?? base?.equippedParticle,
      equippedEffect:
          byId[widget.element.config['effect_id']] ?? base?.equippedEffect,
    );
  }
}

/// 带交叉淡入淡出的预览区域
class _CrossfadePreviewArea extends StatefulWidget {
  const _CrossfadePreviewArea({
    required this.element,
    required this.availableElements,
    required this.baseConfig,
    required this.colors,
    required this.isPreviewing,
    required this.crossfadeAnimation,
    required this.onTogglePreview,
  });

  final VisualElementModel element;
  final List<VisualElementModel> availableElements;
  final UserVisualConfig? baseConfig;
  final VisualElementRarityColors colors;
  final bool isPreviewing;
  final Animation<double> crossfadeAnimation;
  final VoidCallback onTogglePreview;

  @override
  State<_CrossfadePreviewArea> createState() => _CrossfadePreviewAreaState();
}

class _CrossfadePreviewAreaState extends State<_CrossfadePreviewArea>
    with TickerProviderStateMixin {
  late AnimationController _mainController;
  late AnimationController _particleController;

  @override
  void initState() {
    super.initState();
    _mainController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();
  }

  @override
  void dispose() {
    _mainController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final previewConfig = _resolvePreviewConfig(true);
    final baseConfig = _resolvePreviewConfig(false);

    return Container(
      height: MediaQuery.sizeOf(context).width < 380 ? 300 : 340,
      margin: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius16,
        border: Border.all(color: widget.colors.border, width: 2),
      ),
      child: Stack(
        children: [
          ClipRRect(
            borderRadius: DS.borderRadius12,
            child: Stack(
              fit: StackFit.expand,
              children: [
                // 底层：当前配置
                FadeTransition(
                  opacity: Tween<double>(begin: 1.0, end: 0.0).animate(
                    widget.crossfadeAnimation,
                  ),
                  child: _buildPreviewLayers(baseConfig),
                ),
                // 顶层：预览配置
                FadeTransition(
                  opacity: Tween<double>(begin: 0.0, end: 1.0).animate(
                    widget.crossfadeAnimation,
                  ),
                  child: _buildPreviewLayers(previewConfig),
                ),
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.transparent,
                          VisualElementPalette.moonless.withValues(alpha: 0.10),
                          VisualElementPalette.moonless.withValues(alpha: 0.42),
                        ],
                        stops: const [0.0, 0.58, 1.0],
                      ),
                    ),
                  ),
                ),
                _PreviewSurfaceMock(
                  element: widget.element,
                  colors: widget.colors,
                  isPreviewing: widget.isPreviewing,
                ),
              ],
            ),
          ),
          Positioned(
            left: DS.spacing12,
            top: DS.spacing12,
            right: DS.spacing12,
            child: Row(
              children: [
                _StageChip(
                  icon: widget.isPreviewing
                      ? Icons.auto_awesome_rounded
                      : Icons.dashboard_customize_outlined,
                  label: widget.isPreviewing
                      ? context.l10n.visualPreviewing
                      : context.l10n.visualCurrentLook,
                  color: widget.isPreviewing
                      ? widget.colors.border
                      : VisualElementPalette.textSecondary,
                ),
                const Spacer(),
                _StageChip(
                  icon: Icons.touch_app_rounded,
                  label: context.l10n.visualTapToggle,
                  color: VisualElementPalette.gold,
                ),
              ],
            ),
          ),
          Positioned(
            right: DS.spacing12,
            bottom: DS.spacing12,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: widget.onTogglePreview,
                borderRadius: DS.borderRadius8,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing12,
                    vertical: DS.spacing8,
                  ),
                  decoration: BoxDecoration(
                    color:
                        VisualElementPalette.moonless.withValues(alpha: 0.72),
                    borderRadius: DS.borderRadiusFull,
                    border: Border.all(
                      color: widget.colors.border.withValues(alpha: 0.32),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        widget.isPreviewing
                            ? Icons.visibility_off
                            : Icons.visibility,
                        size: DS.iconSizeSm,
                        color: VisualElementPalette.textPrimary,
                      ),
                      const SizedBox(width: DS.spacing6),
                      Text(
                        I18nService.instance.isChinese
                            ? (widget.isPreviewing ? '查看当前' : '体验此装扮')
                            : (widget.isPreviewing
                                ? 'View Current'
                                : 'Try This Look'),
                        style: const TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: VisualElementPalette.textPrimary,
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreviewLayers(UserVisualConfig config) => Stack(
        fit: StackFit.expand,
        children: [
          BackgroundLayer(
            element: config.equippedBackground,
            mainAnimation: _mainController,
            tint: VisualElementPalette.moonless,
            tintOpacity: 0.06,
          ),
          ParticleLayer(
            element: config.equippedParticle,
            particleAnimation: _particleController,
            mainAnimation: _mainController,
            density: 1.25,
            speedMultiplier: 0.9,
          ),
          EffectLayer(
            element: config.equippedEffect,
            mainAnimation: _mainController,
          ),
        ],
      );

  UserVisualConfig _resolvePreviewConfig(bool isPreviewing) {
    final base = widget.baseConfig;
    if (!isPreviewing) {
      return base ?? UserVisualConfig();
    }

    switch (widget.element.elementType) {
      case VisualElementType.background:
        return UserVisualConfig(
          equippedBackground: widget.element,
          equippedParticle: base?.equippedParticle,
          equippedEffect: base?.equippedEffect,
        );
      case VisualElementType.particle:
        return UserVisualConfig(
          equippedBackground: base?.equippedBackground,
          equippedParticle: widget.element,
          equippedEffect: base?.equippedEffect,
        );
      case VisualElementType.effect:
        return UserVisualConfig(
          equippedBackground: base?.equippedBackground,
          equippedParticle: base?.equippedParticle,
          equippedEffect: widget.element,
        );
      case VisualElementType.bundle:
        return _buildBundlePreviewConfig(base);
    }
  }

  UserVisualConfig _buildBundlePreviewConfig(UserVisualConfig? base) {
    final byId = <String, VisualElementModel>{
      for (final element in widget.availableElements) element.id: element,
    };
    return UserVisualConfig(
      equippedBackground: byId[widget.element.config['background_id']] ??
          base?.equippedBackground,
      equippedParticle:
          byId[widget.element.config['particle_id']] ?? base?.equippedParticle,
      equippedEffect:
          byId[widget.element.config['effect_id']] ?? base?.equippedEffect,
    );
  }
}

/// 稀有度徽章
class _RarityBadge extends StatelessWidget {
  const _RarityBadge({
    required this.rarity,
    required this.colors,
    required this.l10n,
  });

  final VisualElementRarity rarity;
  final VisualElementRarityColors colors;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: colors.background.withValues(alpha: 0.92),
          borderRadius: DS.borderRadius8,
          border: Border.all(color: colors.border.withValues(alpha: 0.55)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getRarityIcon(rarity),
              size: DS.iconSizeXs,
              color: colors.text,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              _getRarityName(rarity),
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
                color: colors.text,
              ),
            ),
          ],
        ),
      );

  IconData _getRarityIcon(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return Icons.circle_outlined;
      case VisualElementRarity.rare:
        return Icons.star_border;
      case VisualElementRarity.epic:
        return Icons.auto_awesome;
      case VisualElementRarity.legendary:
        return Icons.diamond_outlined;
    }
  }

  String _getRarityName(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return l10n.achievementRarityCommon;
      case VisualElementRarity.rare:
        return l10n.achievementRarityRare;
      case VisualElementRarity.epic:
        return l10n.achievementRarityEpic;
      case VisualElementRarity.legendary:
        return l10n.achievementRarityLegendary;
    }
  }
}

/// 信息行
class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 4,
              child: Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: VisualElementPalette.textSecondary,
                ),
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              flex: 6,
              child: Text(
                value,
                textAlign: TextAlign.right,
                softWrap: true,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightMedium,
                  color: VisualElementPalette.textPrimary,
                ),
              ),
            ),
          ],
        ),
      );
}

/// 解锁条件显示
class _UnlockRequirement extends StatelessWidget {
  const _UnlockRequirement({
    required this.element,
    required this.l10n,
  });

  final VisualElementModel element;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: VisualElementPalette.panel,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: VisualElementPalette.hairline),
        ),
        child: Row(
          children: [
            Icon(
              Icons.lock_outline,
              size: DS.iconSizeSm,
              color: VisualElementPalette.textSecondary,
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                _getRequirementText(),
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: VisualElementPalette.textSecondary,
                ),
              ),
            ),
          ],
        ),
      );

  String _getRequirementText() {
    switch (element.unlockSource) {
      case VisualElementUnlockSource.system:
        return l10n.visualElementUnlockHintSystem;
      case VisualElementUnlockSource.achievement:
        final achievementId = element.unlockRequirement?['achievement_id'];
        if (achievementId != null) {
          return l10n
              .visualElementUnlockHintAchievement(achievementId as Object);
        }
        return l10n.visualElementUnlockHintAchievementDefault;
      case VisualElementUnlockSource.shop:
        final price = element.unlockRequirement?['price_photons'];
        if (price != null) {
          return l10n.visualElementUnlockHintShop(price as Object);
        }
        return l10n.visualElementUnlockHintShopDefault;
      case VisualElementUnlockSource.event:
        return l10n.visualElementUnlockHintEvent;
      case VisualElementUnlockSource.season:
        return l10n.visualElementUnlockHintSeason;
    }
  }
}
