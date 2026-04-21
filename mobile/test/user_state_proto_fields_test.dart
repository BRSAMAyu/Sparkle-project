import 'package:flutter_test/flutter_test.dart';
import 'package:protobuf/protobuf.dart';
import 'package:protobuf/well_known_types/google/protobuf/struct.pb.dart';
import 'package:sparkle/gen/user_state.pb.dart';

void main() {
  test('active skills summary round-trips through UserStateV1', () {
    final state = UserStateV1()
      ..activeSkillsSummary = (ActiveSkillsSummaryField()
        ..value = (ActiveSkillsSummaryValue()
          ..items.add(
            ActiveSkillSummaryItemValue()
              ..skillId = 'skill-1'
              ..name = 'Exam Triage'
              ..activationMatchScore = 0.91,
          )));

    final decoded = UserStateV1.fromBuffer(state.writeToBuffer());
    expect(decoded.hasActiveSkillsSummary(), isTrue);
    expect(decoded.activeSkillsSummary.value.items.single.skillId, 'skill-1');
  });

  test('achievement summary round-trips through UserStateV1', () {
    final state = UserStateV1()
      ..achievementSummary = (AchievementSummaryField()
        ..value = (AchievementSummaryValue()
          ..totalAchievementScore = 4.5
          ..recentUnlocks.add(
            AchievementUnlockSummaryItemValue()
              ..achievementId = 'streak_7'
              ..name = '七日连胜'
              ..rarity = 'rare',
          )));

    final decoded = UserStateV1.fromBuffer(state.writeToBuffer());
    expect(decoded.hasAchievementSummary(), isTrue);
    expect(decoded.achievementSummary.value.totalAchievementScore, 4.5);
  });

  test('calendar context keeps exam urgency struct payload', () {
    final urgency = Struct()
      ..fields['days_left'] = (Value()..numberValue = 9)
      ..fields['urgent'] = (Value()..boolValue = true);
    final state = UserStateV1()
      ..calendarContext = (CalendarContextField()
        ..value = (CalendarContextValue()
          ..workloadDensity = 'medium'
          ..examUrgency = urgency));

    final decoded = UserStateV1.fromBuffer(state.writeToBuffer());
    expect(decoded.hasCalendarContext(), isTrue);
    expect(decoded.calendarContext.value.workloadDensity, 'medium');
    expect(decoded.calendarContext.value.examUrgency.fields['urgent']!.boolValue, isTrue);
  });
}
