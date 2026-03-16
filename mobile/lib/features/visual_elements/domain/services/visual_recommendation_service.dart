import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

enum UserActivityState {
  focus,
  relax,
  sprint,
  night,
  streak,
}

enum VisualRecommendationReason {
  focus,
  relax,
  sprint,
  night,
  streak,
}

class VisualRecommendation {
  VisualRecommendation({
    required this.element,
    required this.reason,
    required this.score,
  });

  final VisualElementModel element;
  final VisualRecommendationReason reason;
  final int score;
}

class VisualRecommendationService {
  /// 获取基于用户状态的推荐
  Future<List<VisualRecommendation>> getRecommendations({
    required UserActivityState state,
    required TimeOfDay timeOfDay,
    required List<VisualElementModel> availableElements,
  }) async {
    final effectiveState = _applyTimeOfDay(state, timeOfDay);
    final reason = _reasonForState(effectiveState);

    final scored = availableElements
        .map((element) => VisualRecommendation(
              element: element,
              reason: reason,
              score: getRecommendationScore(element, effectiveState),
            ))
        .toList()
      ..sort((a, b) => b.score.compareTo(a.score));

    return scored.where((r) => r.score > 0).take(5).toList();
  }

  /// 获取当前推荐分数（0-100）
  int getRecommendationScore(
    VisualElementModel element,
    UserActivityState state,
  ) {
    var score = 0;
    final text = _searchText(element);

    switch (state) {
      case UserActivityState.focus:
        score += _scoreByType(
          element.elementType,
          background: 35,
          particle: 20,
          effect: -5,
          bundle: 8,
        );
        score += _keywordScore(text, _focusKeywords);
        break;
      case UserActivityState.relax:
        score += _scoreByType(
          element.elementType,
          background: 20,
          particle: 35,
          effect: 8,
          bundle: 6,
        );
        score += _keywordScore(text, _relaxKeywords);
        break;
      case UserActivityState.sprint:
        score += _scoreByType(
          element.elementType,
          background: 30,
          particle: 12,
          effect: 20,
          bundle: 10,
        );
        score += _keywordScore(text, _sprintKeywords);
        break;
      case UserActivityState.night:
        score += _scoreByType(
          element.elementType,
          background: 35,
          particle: 15,
          effect: 5,
          bundle: 8,
        );
        score += _keywordScore(text, _nightKeywords);
        break;
      case UserActivityState.streak:
        score += _scoreByType(
          element.elementType,
          background: 10,
          particle: 22,
          effect: 30,
          bundle: 12,
        );
        score += _keywordScore(text, _streakKeywords);
        break;
    }

    if (element.isUnlocked) {
      score += 15;
    }
    if (element.isEquipped) {
      score += 6;
    }
    if (element.rarity.index >= VisualElementRarity.epic.index) {
      score += 5;
    }

    if (score < 0) return 0;
    if (score > 100) return 100;
    return score;
  }

  int _scoreByType(
    VisualElementType type, {
    required int background,
    required int particle,
    required int effect,
    required int bundle,
  }) {
    return switch (type) {
      VisualElementType.background => background,
      VisualElementType.particle => particle,
      VisualElementType.effect => effect,
      VisualElementType.bundle => bundle,
    };
  }

  int _keywordScore(String text, List<String> keywords) {
    if (text.isEmpty) return 0;
    for (final keyword in keywords) {
      if (text.contains(keyword)) {
        return 20;
      }
    }
    return 0;
  }

  String _searchText(VisualElementModel element) {
    final buffer = StringBuffer(element.name.toLowerCase());
    if (element.category != null) {
      buffer.write(' ${element.category!.toLowerCase()}');
    }
    if (element.description != null) {
      buffer.write(' ${element.description!.toLowerCase()}');
    }
    return buffer.toString();
  }

  UserActivityState _applyTimeOfDay(
    UserActivityState state,
    TimeOfDay timeOfDay,
  ) {
    final isNight = timeOfDay.hour >= 21 || timeOfDay.hour < 6;
    if (isNight && state != UserActivityState.sprint) {
      return UserActivityState.night;
    }
    return state;
  }

  VisualRecommendationReason _reasonForState(UserActivityState state) {
    switch (state) {
      case UserActivityState.focus:
        return VisualRecommendationReason.focus;
      case UserActivityState.relax:
        return VisualRecommendationReason.relax;
      case UserActivityState.sprint:
        return VisualRecommendationReason.sprint;
      case UserActivityState.night:
        return VisualRecommendationReason.night;
      case UserActivityState.streak:
        return VisualRecommendationReason.streak;
    }
  }
}

const List<String> _focusKeywords = [
  'focus',
  'calm',
  'quiet',
  'zen',
  'soft',
  'minimal',
  'cool',
  'clear',
  '专注',
  '安静',
  '宁静',
  '冷',
  '清爽',
];

const List<String> _relaxKeywords = [
  'relax',
  'warm',
  'sunset',
  'dream',
  'gentle',
  'soft',
  'chill',
  'rest',
  '暖',
  '柔',
  '治愈',
  '舒缓',
  '轻松',
];

const List<String> _sprintKeywords = [
  'sprint',
  'energy',
  'boost',
  'speed',
  'neon',
  'vivid',
  'contrast',
  '冲刺',
  '高能',
  '激励',
  '速度',
  '高对比',
];

const List<String> _nightKeywords = [
  'night',
  'dark',
  'midnight',
  'moon',
  'star',
  'shadow',
  '夜',
  '暗',
  '月',
  '星',
  '暮',
];

const List<String> _streakKeywords = [
  'flame',
  'fire',
  'spark',
  'streak',
  'blaze',
  'ember',
  '焰',
  '火',
  '光',
  '耀',
];
