import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxySearchPanel extends StatelessWidget {
  const GalaxySearchPanel({
    required this.controller,
    required this.query,
    required this.results,
    required this.isDarkMode,
    required this.onQueryChanged,
    required this.onClose,
    required this.onNodeSelected,
    super.key,
  });

  final TextEditingController controller;
  final String query;
  final List<GalaxyNodeModel> results;
  final bool isDarkMode;
  final ValueChanged<String> onQueryChanged;
  final VoidCallback onClose;
  final ValueChanged<GalaxyNodeModel> onNodeSelected;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final foreground = isDarkMode ? Colors.white : const Color(0xFF111827);
    final secondary = isDarkMode
        ? Colors.white.withValues(alpha: 0.64)
        : Colors.black.withValues(alpha: 0.56);
    final responsiveMaxHeight = MediaQuery.sizeOf(context).height * 0.44;
    final panelMaxHeight =
        responsiveMaxHeight < 360 ? responsiveMaxHeight : 360.0;

    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: isDarkMode
                ? const Color(0xB3141B2B)
                : Colors.white.withValues(alpha: 0.82),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isDarkMode
                  ? Colors.white.withValues(alpha: 0.12)
                  : Colors.black.withValues(alpha: 0.08),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDarkMode ? 0.22 : 0.08),
                blurRadius: 24,
                offset: const Offset(0, 16),
              ),
            ],
          ),
          child: ConstrainedBox(
            constraints:
                BoxConstraints(maxWidth: 360, maxHeight: panelMaxHeight),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          l10n.galaxySearchTitle,
                          style: TextStyle(
                            color: foreground,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: onClose,
                        icon: Icon(Icons.close_rounded, color: secondary),
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: controller,
                    autofocus: true,
                    onChanged: onQueryChanged,
                    style: TextStyle(
                      color: foreground,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                    decoration: InputDecoration(
                      hintText: l10n.galaxySearchHint,
                      hintStyle: TextStyle(color: secondary),
                      prefixIcon: Icon(Icons.search_rounded, color: secondary),
                      filled: true,
                      fillColor: (isDarkMode ? Colors.white : Colors.black)
                          .withValues(alpha: isDarkMode ? 0.05 : 0.035),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 12,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: query.trim().isEmpty
                        ? _SearchHint(isDarkMode: isDarkMode)
                        : results.isEmpty
                            ? Center(
                                child: Text(
                                  l10n.galaxySearchNoResults,
                                  style: TextStyle(
                                    color: secondary,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              )
                            : ListView.separated(
                                padding: EdgeInsets.zero,
                                itemCount: results.length,
                                separatorBuilder: (_, __) => Divider(
                                  height: 1,
                                  color:
                                      (isDarkMode ? Colors.white : Colors.black)
                                          .withValues(alpha: 0.08),
                                ),
                                itemBuilder: (context, index) {
                                  final node = results[index];
                                  final sectorStyle =
                                      SectorConfig.getStyle(node.sector);
                                  final sectorName =
                                      SectorConfig.getLocalizedName(
                                    node.sector,
                                  );
                                  final color = sectorStyle.primaryColorFor(
                                    isDarkMode: isDarkMode,
                                  );

                                  return ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    dense: true,
                                    leading: Container(
                                      width: 12,
                                      height: 12,
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: color.withValues(alpha: 0.92),
                                        boxShadow: [
                                          BoxShadow(
                                            color:
                                                color.withValues(alpha: 0.22),
                                            blurRadius: 8,
                                          ),
                                        ],
                                      ),
                                    ),
                                    title: Text(
                                      node.name,
                                      style: TextStyle(
                                        color: foreground,
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    subtitle: Text(
                                      l10n.galaxySearchResultSubtitle(
                                        sectorName,
                                        node.masteryScore,
                                        node.importance,
                                      ),
                                      style: TextStyle(
                                        color: secondary,
                                        fontSize: 12,
                                      ),
                                    ),
                                    trailing: Icon(
                                      Icons.north_east_rounded,
                                      color: color,
                                      size: 18,
                                    ),
                                    onTap: () => onNodeSelected(node),
                                  );
                                },
                              ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SearchHint extends StatelessWidget {
  const _SearchHint({required this.isDarkMode});

  final bool isDarkMode;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final secondary = isDarkMode
        ? Colors.white.withValues(alpha: 0.62)
        : Colors.black.withValues(alpha: 0.56);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.travel_explore_rounded,
            size: 28,
            color: secondary,
          ),
          const SizedBox(height: 10),
          Text(
            l10n.galaxySearchHintDetail,
            style: TextStyle(
              color: secondary,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
