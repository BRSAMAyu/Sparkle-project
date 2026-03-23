import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/background_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/effect_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/particle_layer.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 视觉元素预览对话框
class VisualElementPreviewDialog extends StatefulWidget {
  const VisualElementPreviewDialog({
    required this.element,
    super.key,
    this.availableElements = const <VisualElementModel>[],
    this.baseConfig,
    this.onEquip,
    this.onUnequip,
    this.isEquipped = false,
    this.isUnlocked = false,
  });

  final VisualElementModel element;
  final List<VisualElementModel> availableElements;
  final UserVisualConfig? baseConfig;
  final VoidCallback? onEquip;
  final VoidCallback? onUnequip;
  final bool isEquipped;
  final bool isUnlocked;

  static Future<void> show(
    BuildContext context, {
    required VisualElementModel element,
    List<VisualElementModel> availableElements = const <VisualElementModel>[],
    UserVisualConfig? baseConfig,
    VoidCallback? onEquip,
    VoidCallback? onUnequip,
    bool isEquipped = false,
    bool isUnlocked = false,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        builder: (context, scrollController) => VisualElementPreviewDialog(
          element: element,
          availableElements: availableElements,
          baseConfig: baseConfig,
          onEquip: onEquip,
          onUnequip: onUnequip,
          isEquipped: isEquipped,
          isUnlocked: isUnlocked,
        ),
      ),
    );
  }

  @override
  State<VisualElementPreviewDialog> createState() =>
      _VisualElementPreviewDialogState();
}

class _VisualElementPreviewDialogState
    extends State<VisualElementPreviewDialog>
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

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colors = _getRarityColors(widget.element.rarity);

    return Stack(
      children: [
        Container(
          decoration: BoxDecoration(
            color: DS.surfacePrimary,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // 拖动条
              Container(
                margin: const EdgeInsets.only(top: DS.spacing12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.neutral300,
                  borderRadius: DS.borderRadiusFull,
                ),
              ),

              Expanded(
                child: CustomScrollView(
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
                          onTogglePreview: () {
                            _crossfadeController.forward(from: 0);
                            setState(() => _isPreviewing = !_isPreviewing);
                          },
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
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                ConstrainedBox(
                                  constraints: const BoxConstraints(
                                    minWidth: 0,
                                    maxWidth: 320,
                                  ),
                                  child: Text(
                                    widget.element.name,
                                    style: TextStyle(
                                      fontSize: DS.fontSizeXl,
                                      fontWeight: DS.fontWeightBold,
                                      color: DS.textPrimary,
                                    ),
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                _RarityBadge(
                                  rarity: widget.element.rarity,
                                  colors: colors,
                                  l10n: l10n,
                                ),
                              ],
                            ),

                            if (widget.element.description != null) ...[
                              const SizedBox(height: DS.spacing8),
                              Text(
                                widget.element.description!,
                                style: TextStyle(
                                  fontSize: DS.fontSizeSm,
                                  color: DS.textSecondary,
                                  height: 1.5,
                                ),
                                maxLines: 6,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],

                            const SizedBox(height: DS.spacing16),
                            const Divider(),
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
              gravity: 0.2,
              emissionFrequency: 0.05,
              numberOfParticles: 30,
              maxBlastForce: 100,
              minBlastForce: 80,
            ),
          ),
      ],
    );
  }

  Widget _buildActionButtons(AppLocalizations l10n) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        DS.spacing16,
        DS.spacing12,
        DS.spacing16,
        MediaQuery.of(context).padding.bottom + DS.spacing12,
      ),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        border: Border(
          top: BorderSide(color: DS.border.withValues(alpha: 0.5)),
        ),
      ),
      child: SafeArea(
        top: false,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final actionWidth = constraints.maxWidth > 420
                ? constraints.maxWidth - 152
                : constraints.maxWidth;
            return Wrap(
              spacing: DS.spacing12,
              runSpacing: DS.spacing12,
              children: [
                SizedBox(
                  width: constraints.maxWidth > 420 ? 140 : constraints.maxWidth,
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
  }

  Widget _buildShareButton(AppLocalizations l10n) {
    return SizedBox(
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
        label: Flexible(
          child: Text(
            l10n.visualElementShare,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        style: OutlinedButton.styleFrom(
          foregroundColor: DS.textSecondary,
          side: BorderSide(color: DS.border),
          shape: RoundedRectangleBorder(
            borderRadius: DS.borderRadius12,
          ),
        ),
      ),
    );
  }

  Widget _buildEquipButton(AppLocalizations l10n) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton.icon(
        onPressed: _handleEquip,
        icon: const Icon(Icons.check_circle_outline),
        label: Text(l10n.visualElementEquip),
        style: ElevatedButton.styleFrom(
          backgroundColor: DS.brandPrimary,
          foregroundColor: DS.textOnPrimary,
          shape: RoundedRectangleBorder(
            borderRadius: DS.borderRadius12,
          ),
        ),
      ),
    );
  }

  Widget _buildUnequipButton(AppLocalizations l10n) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: OutlinedButton.icon(
        onPressed: widget.onUnequip,
        icon: const Icon(Icons.remove_circle_outline),
        label: Text(l10n.visualElementUnequip),
        style: OutlinedButton.styleFrom(
          foregroundColor: DS.textSecondary,
          side: BorderSide(color: DS.border),
          shape: RoundedRectangleBorder(
            borderRadius: DS.borderRadius12,
          ),
        ),
      ),
    );
  }

  Widget _buildLockedButton(AppLocalizations l10n) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton.icon(
        onPressed: null,
        icon: const Icon(Icons.lock_outline),
        label: Text(l10n.visualElementLocked),
        style: ElevatedButton.styleFrom(
          backgroundColor: DS.surfaceTertiary,
          foregroundColor: DS.textTertiary,
          shape: RoundedRectangleBorder(
            borderRadius: DS.borderRadius12,
          ),
        ),
      ),
    );
  }

  Future<void> _sharePreview() async {
    final boundary =
        _previewKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
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

  _RarityColors _getRarityColors(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return _RarityColors(
          background: DS.rarityCommonBg,
          border: DS.rarityCommon,
          text: DS.rarityCommonText,
        );
      case VisualElementRarity.rare:
        return _RarityColors(
          background: DS.rarityRareBg,
          border: DS.rarityRare,
          text: DS.rarityRareText,
        );
      case VisualElementRarity.epic:
        return _RarityColors(
          background: DS.rarityEpicBg,
          border: DS.rarityEpic,
          text: DS.rarityEpicText,
        );
      case VisualElementRarity.legendary:
        return _RarityColors(
          background: DS.rarityLegendaryBg,
          border: DS.rarityLegendary,
          text: DS.rarityLegendaryText,
        );
    }
  }

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
  final _RarityColors colors;
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
      height: 240,
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
                    color: DS.surfacePrimary.withValues(alpha: 0.9),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    widget.isPreviewing
                        ? Icons.visibility_off
                        : Icons.visibility,
                    size: DS.iconSizeSm,
                    color: DS.textSecondary,
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
      equippedParticle: byId[widget.element.config['particle_id']] ??
          base?.equippedParticle,
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
  final _RarityColors colors;
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
      height: 240,
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
                    color: DS.surfacePrimary.withValues(alpha: 0.9),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    widget.isPreviewing
                        ? Icons.visibility_off
                        : Icons.visibility,
                    size: DS.iconSizeSm,
                    color: DS.textSecondary,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreviewLayers(UserVisualConfig config) {
    return Stack(
      fit: StackFit.expand,
      children: [
        BackgroundLayer(
          element: config.equippedBackground,
          mainAnimation: _mainController,
        ),
        ParticleLayer(
          element: config.equippedParticle,
          particleAnimation: _particleController,
          mainAnimation: _mainController,
        ),
        EffectLayer(
          element: config.equippedEffect,
          mainAnimation: _mainController,
        ),
      ],
    );
  }

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
      equippedParticle: byId[widget.element.config['particle_id']] ??
          base?.equippedParticle,
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
  final _RarityColors colors;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: DS.borderRadius8,
        border: Border.all(color: colors.border),
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
  }

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
  Widget build(BuildContext context) {
    return Padding(
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
                color: DS.textSecondary,
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
                color: DS.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
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
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.border.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Icon(
            Icons.lock_outline,
            size: DS.iconSizeSm,
            color: DS.textTertiary,
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Text(
              _getRequirementText(),
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _getRequirementText() {
    switch (element.unlockSource) {
      case VisualElementUnlockSource.system:
        return l10n.visualElementUnlockHintSystem;
      case VisualElementUnlockSource.achievement:
        final achievementId = element.unlockRequirement?['achievement_id'];
        if (achievementId != null) {
          return l10n.visualElementUnlockHintAchievement(achievementId as Object);
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

class _RarityColors {
  _RarityColors({
    required this.background,
    required this.border,
    required this.text,
  });

  final Color background;
  final Color border;
  final Color text;
}
