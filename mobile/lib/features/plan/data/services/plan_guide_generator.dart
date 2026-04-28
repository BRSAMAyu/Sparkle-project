import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_draft.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/core/services/i18n_service.dart';

final planGuideGeneratorProvider =
    Provider<PlanGuideGenerator>(PlanGuideGenerator.new);

enum PlanGuideAudience { human, ai }

extension PlanGuideAudienceX on PlanGuideAudience {
  String get wireValue => switch (this) {
        PlanGuideAudience.human => 'human',
        PlanGuideAudience.ai => 'ai',
      };
}

class PlanGuideGenerator {
  PlanGuideGenerator(this._ref);

  final Ref _ref;

  Future<String> generate(
    PlanDraft draft, {
    PlanGuideAudience audience = PlanGuideAudience.human,
  }) async {
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
    final prompt = _buildPrompt(draft, audience: audience);
    final buffer = StringBuffer();

    final stream = chatRepository.chatStream(
      prompt,
      null,
      userId: userId,
      nickname: nickname,
      token: token,
      requestId: requestId,
      chatMode: draft.type == PlanType.sprint ? 'study_plan' : 'deep_analysis',
      extraContext: {
        'reasoning_mode': 'fast',
        'guide_audience': audience.wireValue,
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
      throw Exception(S.planGuideAiNotReturn);
    }
    return content;
  }

  String _buildPrompt(
    PlanDraft draft, {
    required PlanGuideAudience audience,
  }) {
    final typeLabel = draft.type == PlanType.growth ? '成长计划' : '冲刺计划';
    final tasks = draft.taskDrafts.isEmpty
        ? '当前还没有预置任务，请输出适合后续拆解任务的执行主线。'
        : draft.taskDrafts
            .map(
              (task) =>
                  '- ${task.title} (${task.estimatedMinutes} 分钟, 难度 ${task.difficulty})',
            )
            .join('\n');

    if (audience == PlanGuideAudience.ai) {
      return '''
你是 Sparkle 内部的任务承接助手。请基于下面这张$typeLabel输出一份**给 AI 使用**的执行版本，供 Sparkle 内部任务助手读取，不是写给普通用户看的长文。

输出要求：
1. 只使用基础 Markdown。
2. 结构固定为：
## objective
## constraints
## execution_plan
## first_reply_style
3. 每个部分 2-4 条，尽量短，不要抒情。
4. 明确这份内容只能在 Sparkle 内部闭环场景中使用，不能把用户甩去外部 AI 产品。
5. 如果信息不足，优先给稳健、低风险、可继续追问的执行骨架。

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

    return '''
你是一名学习规划助手。请为下面这个$typeLabel生成一份**给用户自己看的**简洁执行指南。

输出要求：
1. 只使用基础 Markdown。
2. 结构固定为：
## 推进主线
## 每日节奏
## 风险提醒
## 今日起步动作
3. 每个部分控制在 2-4 条，不要空话。
4. 强调长期持续、节奏安排和执行边界，不要把它写成普通任务卡。
5. 语气要帮助用户直接开始，而不是解释系统自己有多聪明。

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
