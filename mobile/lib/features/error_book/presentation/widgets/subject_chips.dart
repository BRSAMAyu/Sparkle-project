import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 科目定义
class Subject {
  const Subject({
    required this.code,
    required this.label,
    required this.icon,
    required this.color,
  });
  final String code;
  final String label;
  final IconData icon;
  final Color color;

  static final List<Subject> all = [
    Subject(
      code: 'math',
      label: context.l10n.ebMath,
      icon: Icons.calculate,
      color: DS.info,
    ),
    Subject(
      code: 'physics',
      label: context.l10n.ebPhysics,
      icon: Icons.science,
      color: DS.brandSecondary,
    ),
    Subject(
      code: 'chemistry',
      label: context.l10n.ebChemistry,
      icon: Icons.science_outlined,
      color: DS.warningLight,
    ),
    Subject(
      code: 'biology',
      label: context.l10n.ebBiology,
      icon: Icons.park,
      color: DS.success,
    ),
    Subject(
      code: 'english',
      label: context.l10n.ebEnglish,
      icon: Icons.language,
      color: DS.error,
    ),
    Subject(
      code: 'chinese',
      label: context.l10n.ebChinese,
      icon: Icons.menu_book,
      color: DS.warning,
    ),
    Subject(
      code: 'other',
      label: context.l10n.ebOther,
      icon: Icons.more_horiz,
      color: DS.textSecondary,
    ),
  ];

  static Subject? findByCode(String code) {
    try {
      return all.firstWhere((s) => s.code == code);
    } catch (_) {
      return null;
    }
  }
}

/// 科目筛选 Chips
///
/// 用于错题列表页的科目筛选
class SubjectFilterChips extends StatelessWidget {
  const SubjectFilterChips({
    required this.onSelected,
    super.key,
    this.selectedSubject,
  });
  final String? selectedSubject;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: Row(
          children: [
            // 全部
            Padding(
              padding: const EdgeInsets.only(right: DS.spacing8),
              child: FilterChip(
                label: const Text(context.l10n.ebAll),
                selected: selectedSubject == null,
                onSelected: (_) => onSelected(null),
              ),
            ),
            // 各科目
            ...Subject.all.map(
              (subject) => Padding(
                padding: const EdgeInsets.only(right: DS.spacing8),
                child: FilterChip(
                  avatar: Icon(subject.icon, size: DS.iconSizeXs),
                  label: Text(subject.label),
                  selected: selectedSubject == subject.code,
                  onSelected: (_) => onSelected(subject.code),
                  backgroundColor: subject.color.withValues(alpha: 0.1),
                  selectedColor: subject.color.withValues(alpha: 0.3),
                ),
              ),
            ),
          ],
        ),
      );
}

/// 科目标签（只读显示）
class SubjectChip extends StatelessWidget {
  const SubjectChip({
    required this.subjectCode,
    super.key,
    this.compact = false,
  });
  final String subjectCode;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final subject = Subject.findByCode(subjectCode);
    if (subject == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? DS.spacing6 : DS.spacing8,
        vertical: compact ? 2 : DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: subject.color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: subject.color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(subject.icon,
              size: compact ? DS.spacing12 : 14, color: subject.color,),
          SizedBox(width: compact ? 2 : DS.spacing4),
          Text(
            subject.label,
            style: TextStyle(
              fontSize: compact ? 10 : DS.fontSizeXs,
              fontWeight: DS.fontWeightMedium,
              color: subject.color,
            ),
          ),
        ],
      ),
    );
  }
}
