import 'package:flutter/material.dart';

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

  static const List<Subject> all = [
    Subject(code: 'math', label: '数学', icon: Icons.calculate, color: Color(0xFF2196F3)),
    Subject(code: 'physics', label: '物理', icon: Icons.science, color: Color(0xFF9C27B0)),
    Subject(code: 'chemistry', label: '化学', icon: Icons.science_outlined, color: Color(0xFFFF9800)),
    Subject(code: 'biology', label: '生物', icon: Icons.park, color: Color(0xFF4CAF50)),
    Subject(code: 'english', label: '英语', icon: Icons.language, color: Color(0xFFF44336)),
    Subject(code: 'chinese', label: '语文', icon: Icons.menu_book, color: Color(0xFF795548)),
    Subject(code: 'other', label: '其他', icon: Icons.more_horiz, color: Color(0xFF607D8B)),
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
    required this.onSelected, super.key,
    this.selectedSubject,
  });
  final String? selectedSubject;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          // 全部
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: const Text('全部'),
              selected: selectedSubject == null,
              onSelected: (_) => onSelected(null),
            ),
          ),
          // 各科目
          ...Subject.all.map((subject) => Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              avatar: Icon(subject.icon, size: 16),
              label: Text(subject.label),
              selected: selectedSubject == subject.code,
              onSelected: (_) => onSelected(subject.code),
              backgroundColor: subject.color.withOpacity(0.1),
              selectedColor: subject.color.withOpacity(0.3),
            ),
          ),),
        ],
      ),
    );
}

/// 科目标签（只读显示）
class SubjectChip extends StatelessWidget {

  const SubjectChip({
    required this.subjectCode, super.key,
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
        horizontal: compact ? 6 : 8,
        vertical: compact ? 2 : 4,
      ),
      decoration: BoxDecoration(
        color: subject.color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: subject.color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(subject.icon, size: compact ? 12 : 14, color: subject.color),
          SizedBox(width: compact ? 2 : 4),
          Text(
            subject.label,
            style: TextStyle(
              fontSize: compact ? 10 : 12,
              fontWeight: FontWeight.w500,
              color: subject.color,
            ),
          ),
        ],
      ),
    );
  }
}
