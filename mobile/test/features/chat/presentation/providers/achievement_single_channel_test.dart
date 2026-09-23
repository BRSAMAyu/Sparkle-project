import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// IR-G4/N22 · 成就解锁单通道（dialog 保留、toast 去除）+ 专注豁免 机检。
///
/// 行为裁决（A-SPEC4 §3 IR-G4 辩论：庆典保留最强通道 dialog，toast 冗余；
/// N22 条款：庆典类打断受 focusMode 豁免约束，与消息横幅同制）：
/// - chat_notifier_actions 的成就解锁处理必须仍写 pending（dialog 通道），
///   且不再写 'achievement_unlocked' lastAction（toast 通道）；
/// - shell_navigation 的 dialog 触发必须带 focusMode 否决 + 专注结束补放。
void main() {
  final chatActionsSource = File(
    '${Directory.current.path}/lib/features/chat/presentation/providers/'
    'chat_notifier_actions.dart',
  ).readAsStringSync();

  final shellSource = File(
    '${Directory.current.path}/lib/core/navigation/shell_navigation.dart',
  ).readAsStringSync();

  test('成就解锁仍走 dialog 通道（pendingAchievementUnlockProvider.setPending）', () {
    final unlockSection = chatActionsSource
        .split('处理成就解锁事件')
        .skip(1)
        .first
        .split('处理成就里程碑事件')
        .first;
    expect(
      unlockSection,
      contains('pendingAchievementUnlockProvider.notifier).setPending'),
      reason: 'dialog 是庆典单一通道，不得误删',
    );
  });

  test('成就解锁不再写 toast 通道（achievement_unlocked lastAction 已删）', () {
    expect(
      chatActionsSource,
      isNot(contains("lastActionStatus: 'achievement_unlocked'")),
      reason: 'IR-G4：同一事件 dialog+toast 双通道重复打断',
    );
  });

  test('成就里程碑不再写 toast 通道（milestone_reached 已删，只进中心）', () {
    final milestoneSection = chatActionsSource
        .split('处理成就里程碑事件')
        .skip(1)
        .first
        .split('void dismissStaleCard')
        .first;
    expect(
      milestoneSection,
      isNot(contains("lastActionStatus: 'milestone_reached'")),
      reason: 'N22：里程碑 priority=medium 摘要档，只进中心',
    );
    expect(
      milestoneSection,
      contains('handleNewNotification'),
      reason: '中心落点保留（摘要档全量进中心）',
    );
  });

  test('shell 的 dialog 触发受 focusMode 一票否决 + 专注结束补放', () {
    expect(
      shellSource,
      contains('!ref.read(focusModeProvider)'),
      reason: 'N22：庆典类打断受 focusMode 豁免约束（与消息横幅同制）',
    );
    expect(
      shellSource,
      contains('..listenManual(\n        focusModeProvider,'),
      reason: '专注结束时补放挂起的成就庆典',
    );
  });
}
