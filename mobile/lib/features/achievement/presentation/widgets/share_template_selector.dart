import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// Horizontal scrollable template selector for share cards
class ShareTemplateSelector extends StatelessWidget {
  ShareTemplateSelector({
    required this.templates,
    required this.selectedId,
    required this.onSelected,
    super.key,
  });

  final List<ShareTemplateInfo> templates;
  final String selectedId;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 120,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: DS.md),
        itemCount: templates.length,
        separatorBuilder: (context, index) => const SizedBox(width: DS.md),
        itemBuilder: (context, index) {
          final template = templates[index];
          final isSelected = template.id == selectedId;

          return _TemplateCard(
            template: template,
            isSelected: isSelected,
            onTap: () => onSelected(template.id),
          );
        },
      ),
    );
  }
}

class _TemplateCard extends StatelessWidget {
  _TemplateCard({
    required this.template,
    required this.isSelected,
    required this.onTap,
    super.key,
  });

  final ShareTemplateInfo template;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 100,
        decoration: BoxDecoration(
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: isSelected ? DS.brandPrimary : DS.border,
            width: isSelected ? 2 : 1,
          ),
          color: isSelected
              ? DS.brandPrimary.withValues(alpha: 0.1)
              : DS.surfaceSecondary,
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.3),
                    blurRadius: 8,
                    spreadRadius: 1,
                  ),
                ]
              : null,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Template preview icon
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                borderRadius: DS.borderRadius8,
                color: _getTemplateColor(template.id).withValues(alpha: 0.2),
              ),
              child: Icon(
                _getTemplateIcon(template.id),
                color: _getTemplateColor(template.id),
                size: 24,
              ),
            ),
            const SizedBox(height: DS.sm),
            // Template name
            Text(
              template.name,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                fontWeight:
                    isSelected ? DS.fontWeightBold : DS.fontWeightMedium,
                color: isSelected ? DS.brandPrimary : DS.textPrimary,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Color _getTemplateColor(String templateId) {
    return switch (templateId) {
      'cosmic' => const Color(0xFF6366F1), // Indigo
      'minimal' => const Color(0xFF64748B), // Slate
      'neon' => const Color(0xFF22D3EE), // Cyan
      'elegant' => const Color(0xFFD4AF37), // Gold
      _ => DS.brandPrimary,
    };
  }

  IconData _getTemplateIcon(String templateId) {
    return switch (templateId) {
      'cosmic' => Icons.auto_awesome,
      'minimal' => Icons.minimize,
      'neon' => Icons.light_mode,
      'elegant' => Icons.star_outline,
      _ => Icons.image,
    };
  }
}
