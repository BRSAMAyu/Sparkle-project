import 'package:flutter/material.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';

class PlanTaskDraft {
  const PlanTaskDraft({
    required this.title,
    required this.estimatedMinutes,
    required this.difficulty,
    this.dueDate,
    this.generateGuide = true,
  });

  final String title;
  final int estimatedMinutes;
  final int difficulty;
  final DateTime? dueDate;
  final bool generateGuide;

  PlanTaskDraft copyWith({
    String? title,
    int? estimatedMinutes,
    int? difficulty,
    DateTime? dueDate,
    bool? generateGuide,
  }) =>
      PlanTaskDraft(
        title: title ?? this.title,
        estimatedMinutes: estimatedMinutes ?? this.estimatedMinutes,
        difficulty: difficulty ?? this.difficulty,
        dueDate: dueDate ?? this.dueDate,
        generateGuide: generateGuide ?? this.generateGuide,
      );
}

class PlanDraft {
  PlanDraft({
    required this.name,
    required this.type,
    required this.dailyMinutes,
    required this.priority,
    required this.subject,
    required this.goal,
    required this.totalEstimatedHours,
    required this.planStage,
    required this.reminderTime,
    required this.scheduleLabel,
    required this.scopeNotes,
    required this.taskBlueprint,
    required this.aiGuide,
    required this.taskDrafts,
    this.targetDate,
  });

  final String name;
  final PlanType type;
  final int dailyMinutes;
  final PlanPriority priority;
  final String subject;
  final String goal;
  final double totalEstimatedHours;
  final PlanStage planStage;
  final DateTime? targetDate;
  final TimeOfDay reminderTime;
  final String scheduleLabel;
  final String scopeNotes;
  final String taskBlueprint;
  final String aiGuide;
  final List<PlanTaskDraft> taskDrafts;

  bool get hasStructuredContent =>
      goal.trim().isNotEmpty ||
      scheduleLabel.trim().isNotEmpty ||
      scopeNotes.trim().isNotEmpty ||
      taskBlueprint.trim().isNotEmpty ||
      aiGuide.trim().isNotEmpty ||
      taskDrafts.isNotEmpty;

  String get reminderTimeLabel {
    final hour = reminderTime.hour.toString().padLeft(2, '0');
    final minute = reminderTime.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }
}
