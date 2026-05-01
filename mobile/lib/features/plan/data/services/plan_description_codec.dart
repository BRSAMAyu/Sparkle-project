import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/plan/data/models/plan_draft.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class ParsedPlanDescription {
  const ParsedPlanDescription({
    required this.overview,
    required this.schedule,
    required this.scope,
    required this.taskBlueprint,
    required this.guide,
    required this.taskDrafts,
    required this.rawDescription,
    this.reminderTime,
  });

  final String overview;
  final String schedule;
  final String scope;
  final String taskBlueprint;
  final String guide;
  final List<String> taskDrafts;
  final String rawDescription;
  final String? reminderTime;

  bool get hasStructuredSections =>
      overview.isNotEmpty ||
      schedule.isNotEmpty ||
      scope.isNotEmpty ||
      taskBlueprint.isNotEmpty ||
      guide.isNotEmpty ||
      taskDrafts.isNotEmpty;
}

class PlanDescriptionCodec {
  static const _overviewHeading = '## 计划概览';
  static const _scheduleHeading = '## 每日节奏';
  static const _scopeHeading = '## 计划边界';
  static const _taskHeading = '## 任务编排';
  static const _guideHeading = '## AI执行指南';

  static String encode(PlanDraft draft, {String? fallbackDescription}) {
    final buffer = StringBuffer();
    final trimmedFallback = fallbackDescription?.trim() ?? '';
    if (trimmedFallback.isNotEmpty) {
      buffer
        ..writeln(trimmedFallback)
        ..writeln();
    }

    buffer
      ..writeln(_overviewHeading)
      ..writeln('- 计划类型：${draft.type == PlanType.growth ? S.planExamReviewNoSubject : '冲刺计划'}')
      ..writeln('- 每日投入：${draft.dailyMinutes} 分钟')
      ..writeln(
        '- 总预估：${draft.totalEstimatedHours.toStringAsFixed(draft.totalEstimatedHours.truncateToDouble() == draft.totalEstimatedHours ? 0 : 1)} 小时',
      )
      ..writeln('- 当前阶段：${_planStageLabel(draft.planStage)}');
    if (draft.subject.trim().isNotEmpty) {
      buffer.writeln('- 主题方向：${draft.subject.trim()}');
    }
    if (draft.targetDate != null) {
      buffer
          .writeln('- 目标日期：${Formatters.formatDateMedium(draft.targetDate!)}');
    }
    if (draft.goal.trim().isNotEmpty) {
      buffer
        ..writeln()
        ..writeln(draft.goal.trim());
    }
    buffer
      ..writeln()
      ..writeln(_scheduleHeading)
      ..writeln('- 每日提醒：${draft.reminderTimeLabel}');
    if (draft.scheduleLabel.trim().isNotEmpty) {
      buffer.writeln('- 节奏说明：${draft.scheduleLabel.trim()}');
    }
    buffer
      ..writeln()
      ..writeln(_scopeHeading);

    if (draft.scopeNotes.trim().isNotEmpty) {
      buffer.writeln(draft.scopeNotes.trim());
    } else {
      buffer.writeln('- 保持计划目标清晰，优先服务主线推进。');
    }
    buffer
      ..writeln()
      ..writeln(_taskHeading);

    if (draft.taskBlueprint.trim().isNotEmpty) {
      buffer
        ..writeln(draft.taskBlueprint.trim())
        ..writeln();
    }
    if (draft.taskDrafts.isNotEmpty) {
      for (final task in draft.taskDrafts) {
        final dueLabel = task.dueDate != null
            ? ' · 截止 ${Formatters.formatDateShort(task.dueDate!)}'
            : '';
        buffer.writeln(
          '- ${task.title} · ${task.estimatedMinutes} 分钟 · 难度 ${task.difficulty}$dueLabel',
        );
      }
    } else {
      buffer.writeln('- 暂未拆入具体任务，请在执行前补齐关键动作。');
    }
    buffer
      ..writeln()
      ..writeln(_guideHeading);

    if (draft.aiGuide.trim().isNotEmpty) {
      buffer.writeln(draft.aiGuide.trim());
    } else {
      buffer
        ..writeln('1. 先明确今天最重要的一步。')
        ..writeln('2. 用固定时段推进计划主线。')
        ..writeln('3. 每天结束前做一次简短复盘。');
    }

    return buffer.toString().trim();
  }

  static ParsedPlanDescription parse(String? description) {
    final raw = description?.trim() ?? '';
    if (raw.isEmpty) {
      return const ParsedPlanDescription(
        overview: '',
        schedule: '',
        scope: '',
        taskBlueprint: '',
        guide: '',
        taskDrafts: <String>[],
        rawDescription: '',
      );
    }

    final headings = <String>[
      _overviewHeading,
      _scheduleHeading,
      _scopeHeading,
      _taskHeading,
      _guideHeading,
    ];
    final sectionMap = <String, String>{};
    for (var i = 0; i < headings.length; i++) {
      final heading = headings[i];
      final start = raw.indexOf(heading);
      if (start == -1) {
        continue;
      }
      final contentStart = start + heading.length;
      final end = headings
          .skip(i + 1)
          .map(raw.indexOf)
          .where((index) => index != -1 && index > contentStart)
          .fold<int?>(
            null,
            (best, index) => best == null || index < best ? index : best,
          );
      sectionMap[heading] =
          raw.substring(contentStart, end ?? raw.length).trim();
    }

    final taskSection = sectionMap[_taskHeading] ?? '';
    final taskLines = taskSection
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.startsWith('- '))
        .map((line) => line.substring(2).trim())
        .toList();
    final schedule = sectionMap[_scheduleHeading] ?? '';
    final reminderLine =
        schedule.split('\n').map((line) => line.trim()).firstWhere(
              (line) => line.startsWith('- 每日提醒：'),
              orElse: () => '',
            );

    return ParsedPlanDescription(
      overview: sectionMap[_overviewHeading] ?? '',
      schedule: schedule,
      scope: sectionMap[_scopeHeading] ?? '',
      taskBlueprint: taskSection,
      guide: sectionMap[_guideHeading] ?? '',
      taskDrafts: taskLines,
      rawDescription: raw,
      reminderTime: reminderLine.isEmpty
          ? null
          : reminderLine.replaceFirst('- 每日提醒：', '').trim(),
    );
  }

  static String summarize(ParsedPlanDescription parsed) {
    if (parsed.overview.isNotEmpty) {
      final firstLine = parsed.overview
          .split('\n')
          .map((line) => line.trim())
          .firstWhere((line) => line.isNotEmpty, orElse: () => '');
      if (firstLine.isNotEmpty) {
        return firstLine.replaceFirst(RegExp('^- '), '');
      }
    }
    return parsed.rawDescription
        .split('\n')
        .map((line) => line.trim())
        .firstWhere((line) => line.isNotEmpty, orElse: () => '');
  }

  static String _planStageLabel(PlanStage stage) {
    switch (stage) {
      case PlanStage.sprint:
        return '冲刺推进';
      case PlanStage.daily:
        return '日常执行';
      case PlanStage.review:
        return '复盘调优';
      case PlanStage.paused:
        return '暂停中';
    }
  }
}
