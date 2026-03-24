import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 视觉元素网格组件
class VisualElementGrid extends StatelessWidget {
  const VisualElementGrid({
    required this.elements,
    super.key,
    this.onElementTap,
    this.onElementLongPress,
    this.crossAxisCount,
    this.mainAxisExtent = 180,
    this.isCompact = false,
    this.emptyWidget,
  });

  final List<VisualElementModel> elements;
  final void Function(VisualElementModel)? onElementTap;
  final void Function(VisualElementModel)? onElementLongPress;
  final int? crossAxisCount;
  final double mainAxisExtent;
  final bool isCompact;
  final Widget? emptyWidget;

  @override
  Widget build(BuildContext context) {
    if (elements.isEmpty) {
      return emptyWidget ?? const SizedBox.shrink();
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final calculatedCrossAxisCount = crossAxisCount ??
            _calculateCrossAxisCount(constraints.maxWidth);

        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: calculatedCrossAxisCount,
            mainAxisSpacing: DS.spacing12,
            crossAxisSpacing: DS.spacing12,
            mainAxisExtent: mainAxisExtent,
          ),
          itemCount: elements.length,
          itemBuilder: (context, index) {
            final element = elements[index];
            return VisualElementCard(
              element: element,
              onTap: onElementTap != null ? () => onElementTap!(element) : null,
              onLongPress: onElementLongPress != null
                  ? () => onElementLongPress!(element)
                  : null,
              isCompact: isCompact,
            );
          },
        );
      },
    );
  }

  int _calculateCrossAxisCount(double width) {
    if (width < 360) return 1;
    if (width < 600) return 2;
    if (width < 900) return 3;
    return 4;
  }
}

/// 分类网格组件
class VisualElementCategoryGrid extends StatelessWidget {
  const VisualElementCategoryGrid({
    required this.elementsByCategory,
    super.key,
    this.onElementTap,
    this.onElementLongPress,
    this.categoryOrder,
  });

  final Map<String, List<VisualElementModel>> elementsByCategory;
  final void Function(VisualElementModel)? onElementTap;
  final void Function(VisualElementModel)? onElementLongPress;
  final List<String>? categoryOrder;

  @override
  Widget build(BuildContext context) {
    final categories = categoryOrder ?? elementsByCategory.keys.toList()..sort();

    return CustomScrollView(
      slivers: [
        for (final category in categories)
          if (elementsByCategory[category]?.isNotEmpty ?? false)
            SliverMainAxisGroup(
              slivers: [
                // 分类标题
                SliverToBoxAdapter(
                  child: _CategoryHeader(
                    category: category,
                    count: elementsByCategory[category]!.length,
                  ),
                ),
                // 元素网格
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  sliver: SliverLayoutBuilder(
                    builder: (context, constraints) {
                      final crossAxisCount = _calculateCrossAxisCount(
                        constraints.crossAxisExtent,
                      );

                      return SliverGrid(
                        gridDelegate:
                            SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: crossAxisCount,
                          mainAxisSpacing: DS.spacing12,
                          crossAxisSpacing: DS.spacing12,
                          mainAxisExtent: 180,
                        ),
                        delegate: SliverChildBuilderDelegate(
                          (context, index) {
                            final element = elementsByCategory[category]![index];
                            return VisualElementCard(
                              element: element,
                              onTap: onElementTap != null
                                  ? () => onElementTap!(element)
                                  : null,
                              onLongPress: onElementLongPress != null
                                  ? () => onElementLongPress!(element)
                                  : null,
                            );
                          },
                          childCount: elementsByCategory[category]!.length,
                        ),
                      );
                    },
                  ),
                ),
                // 间距
                const SliverToBoxAdapter(
                  child: SizedBox(height: DS.spacing16),
                ),
              ],
            ),
      ],
    );
  }

  int _calculateCrossAxisCount(double width) {
    if (width < 360) return 1;
    if (width < 600) return 2;
    if (width < 900) return 3;
    return 4;
  }
}

/// 按类型分组的网格
class VisualElementTypeGrid extends StatelessWidget {
  const VisualElementTypeGrid({
    required this.elementsByType,
    super.key,
    this.onElementTap,
    this.onElementLongPress,
    this.showEmptyTypes = false,
  });

  final Map<VisualElementType, List<VisualElementModel>> elementsByType;
  final void Function(VisualElementModel)? onElementTap;
  final void Function(VisualElementModel)? onElementLongPress;
  final bool showEmptyTypes;

  @override
  Widget build(BuildContext context) {
    final types = VisualElementType.values.where((type) => showEmptyTypes || (elementsByType[type]?.isNotEmpty ?? false)).toList();

    return CustomScrollView(
      slivers: [
        for (final type in types)
          SliverMainAxisGroup(
            slivers: [
              // 类型标题
              SliverToBoxAdapter(
                child: _TypeHeader(
                  type: type,
                  count: elementsByType[type]?.length ?? 0,
                ),
              ),
              // 元素网格
              if (elementsByType[type]?.isNotEmpty ?? false)
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  sliver: SliverLayoutBuilder(
                    builder: (context, constraints) {
                      final crossAxisCount = _calculateCrossAxisCount(
                        constraints.crossAxisExtent,
                      );

                      return SliverGrid(
                        gridDelegate:
                            SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: crossAxisCount,
                          mainAxisSpacing: DS.spacing12,
                          crossAxisSpacing: DS.spacing12,
                          mainAxisExtent: 180,
                        ),
                        delegate: SliverChildBuilderDelegate(
                          (context, index) {
                            final element = elementsByType[type]![index];
                            return VisualElementCard(
                              element: element,
                              onTap: onElementTap != null
                                  ? () => onElementTap!(element)
                                  : null,
                              onLongPress: onElementLongPress != null
                                  ? () => onElementLongPress!(element)
                                  : null,
                            );
                          },
                          childCount: elementsByType[type]!.length,
                        ),
                      );
                    },
                  ),
                )
              else
                SliverToBoxAdapter(
                  child: _EmptyTypePlaceholder(type: type),
                ),
              // 间距
              const SliverToBoxAdapter(
                child: SizedBox(height: DS.spacing16),
              ),
            ],
          ),
      ],
    );
  }

  int _calculateCrossAxisCount(double width) {
    if (width < 360) return 1;
    if (width < 600) return 2;
    if (width < 900) return 3;
    return 4;
  }
}

/// 分类标题
class _CategoryHeader extends StatelessWidget {
  const _CategoryHeader({
    required this.category,
    required this.count,
  });

  final String category;
  final int count;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing12,
      ),
      child: Row(
        children: [
          Text(
            _getCategoryDisplayName(category, l10n),
            style: TextStyle(
              fontSize: DS.fontSizeLg,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing8,
              vertical: DS.spacing2,
            ),
            decoration: BoxDecoration(
              color: DS.brandPrimary10,
              borderRadius: DS.borderRadius8,
            ),
            child: Text(
              '$count',
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
                color: DS.brandPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _getCategoryDisplayName(String category, AppLocalizations l10n) {
    final displayNames = {
      'space': l10n.visualElementCategorySpace,
      'nature': l10n.visualElementCategoryNature,
      'cyberpunk': l10n.visualElementCategoryCyberpunk,
      'abstract': l10n.visualElementCategoryAbstract,
      'ambient': l10n.visualElementCategoryAmbient,
    };
    return displayNames[category] ?? category;
  }
}

/// 类型标题
class _TypeHeader extends StatelessWidget {
  const _TypeHeader({
    required this.type,
    required this.count,
  });

  final VisualElementType type;
  final int count;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing12,
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing8),
            decoration: BoxDecoration(
              color: DS.brandPrimary10,
              borderRadius: DS.borderRadius8,
            ),
            child: Icon(
              _getTypeIcon(type),
              size: DS.iconSizeSm,
              color: DS.brandPrimary,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Text(
            _getTypeDisplayName(type, l10n),
            style: TextStyle(
              fontSize: DS.fontSizeLg,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing8,
              vertical: DS.spacing2,
            ),
            decoration: BoxDecoration(
              color: DS.surfaceTertiary,
              borderRadius: DS.borderRadius8,
            ),
            child: Text(
              '$count',
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
                color: DS.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  IconData _getTypeIcon(VisualElementType type) {
    switch (type) {
      case VisualElementType.background:
        return Icons.gradient;
      case VisualElementType.particle:
        return Icons.auto_awesome;
      case VisualElementType.effect:
        return Icons.blur_on;
      case VisualElementType.bundle:
        return Icons.inventory_2;
    }
  }

  String _getTypeDisplayName(VisualElementType type, AppLocalizations l10n) {
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
}

/// 空类型占位符
class _EmptyTypePlaceholder extends StatelessWidget {
  const _EmptyTypePlaceholder({required this.type});

  final VisualElementType type;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.all(DS.spacing24),
      child: Center(
        child: Column(
          children: [
            Icon(
              _getTypeIcon(type),
              size: DS.iconSizeXl,
              color: DS.textTertiary,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.visualElementEmptyType(_getTypeDisplayName(type, l10n)),
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textTertiary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getTypeIcon(VisualElementType type) {
    switch (type) {
      case VisualElementType.background:
        return Icons.gradient;
      case VisualElementType.particle:
        return Icons.auto_awesome;
      case VisualElementType.effect:
        return Icons.blur_on;
      case VisualElementType.bundle:
        return Icons.inventory_2;
    }
  }

  String _getTypeDisplayName(VisualElementType type, AppLocalizations l10n) {
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
}
