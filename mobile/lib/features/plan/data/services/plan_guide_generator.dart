import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_draft.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';

final planGuideGeneratorProvider =
    Provider<PlanGuideGenerator>(PlanGuideGenerator.new);

class PlanGuideGenerator {
  PlanGuideGenerator(this._ref);

  final Ref _ref;

  Future<String> generate(PlanDraft draft) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    final authRepository = _ref.read(authRepositoryProvider);
    final chatRepository = _ref.read(chatRepositoryProvider);

    final token = await authRepository.getAccessToken();
    String userId;
    String nickname;
    if (user != null) {
      userId = user.id;
      nickname =
          (user.nickname?.isNotEmpty ?? false) ? user.nickname! : user.username;
    } else {
      final guestService = _ref.read(guestServiceProvider);
      userId = await guestService.getGuestId();
      nickname = guestService.getGuestNickname();
    }

    final requestId = 'plan_guide_${DateTime.now().millisecondsSinceEpoch}';
    final prompt = _buildPrompt(draft);
    final buffer = StringBuffer();

    final stream = chatRepository.chatStream(
      prompt,
      null,
      userId: userId,
      nickname: nickname,
      token: token,
      requestId: requestId,
      chatMode: draft.type == PlanType.sprint ? 'study_plan' : 'deep_analysis',
      extraContext: const {
        'reasoning_mode': 'fast',
      },
    );

    await for (final event in stream.timeout(const Duration(minutes: 2))) {
      if (event is TextEvent) {
        buffer.write(event.content);
      }
      if (event is DoneEvent) {
        break;
      }
      if (event is ErrorEvent) {
        throw Exception(event.message);
      }
    }

    final content = buffer.toString().trim();
    if (content.isEmpty) {
      throw Exception('AI 未返回计划指南');
    }
    return content;
  }

  String _buildPrompt(PlanDraft draft) {
    final typeLabel = draft.type == PlanType.growth ? '成长计划' : '冲刺计划';
    final tasks = draft.taskDrafts.isEmpty
        ? '当前还没有预置任务，请输出适合后续拆解任务的执行主线。'
        : draft.taskDrafts
            .map(
              (task) =>
                  '- ${task.title} (${task.estimatedMinutes} 分钟, 难度 ${task.difficulty})',
            )
            .join('\n');

    return '''
你是一名学习规划助手。请为下面这个$typeLabel生成一份简洁但可执行的计划指南。

输出要求：
1. 只使用基础 Markdown。
2. 结构固定为：
## 推进主线
## 每日节奏
## 风险提醒
## 今日起步动作
3. 每个部分控制在 2-4 条，不要空话。
4. 强调长期持续、节奏安排和执行边界，不要把它写成普通任务卡。

计划名称：${draft.name}
计划目标：${draft.goal}
主题方向：${draft.subject}
每日投入：${draft.dailyMinutes} 分钟
总预估：${draft.totalEstimatedHours.toStringAsFixed(1)} 小时
每日提醒：${draft.reminderTimeLabel}
节奏偏好：${draft.scheduleLabel}
范围说明：${draft.scopeNotes}

预置任务：
$tasks
''';
  }
}
