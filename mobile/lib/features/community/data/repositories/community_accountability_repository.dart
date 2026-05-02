import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/community/data/models/community_accountability_hub_model.dart';

final communityAccountabilityRepositoryProvider =
    Provider<CommunityAccountabilityRepository>(
  (ref) => CommunityAccountabilityRepository(ref.watch(apiClientProvider)),
);

class CommunityAccountabilityRepository {
  const CommunityAccountabilityRepository(this._apiClient);

  static const _experienceCommunityAccountability =
      '/experience/community-accountability';

  final ApiClient _apiClient;

  Future<CommunityAccountabilityHub> getHub() async {
    if (DemoDataService.isDemoMode) {
      return _demoHub();
    }

    try {
      final response = await _apiClient.get<dynamic>(
        _experienceCommunityAccountability,
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getCommunityAccountabilityHub',
      );
      return CommunityAccountabilityHub.fromJson(data);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return _demoHub();
      }
      rethrow;
    }
  }

  CommunityAccountabilityHub _demoHub() {
    final zh = I18nService.instance.isChinese;
    final now = DateTime.now();
    return CommunityAccountabilityHub(
      myCommitments: [
        CommitmentCardPayload(
          id: 'demo_commitment_exam_review',
          summary: zh
              ? '今晚 21:30 前完成积分换元错题复盘'
              : 'Finish integration-substitution mistake review before 21:30',
          dueAt: now.add(const Duration(hours: 7)),
          witnessNames: const ['Lena', 'Nora'],
          progress: 0.62,
          status: 'due_soon',
          successCriteria: zh
              ? const ['复盘 5 道错题', '写出下一次避坑规则']
              : const [
                  'Review 5 missed problems',
                  'Write the next avoidance rule',
                ],
          milestones: zh
              ? const ['错题归类', '重新演算', '提交证据']
              : const ['Group mistakes', 'Re-solve', 'Submit evidence'],
          evidenceRefs: const ['demo-evidence-token'],
          allowPartnerReminders: true,
        ),
        CommitmentCardPayload(
          id: 'demo_commitment_speaking',
          summary: zh
              ? '把英语自我介绍缩短到 90 秒版本'
              : 'Trim my English self-intro to a 90-second version',
          dueAt: now.add(const Duration(days: 2)),
          witnessNames: const ['Lena'],
          progress: 0.35,
          status: 'active',
          successCriteria: zh
              ? const ['录音时长 90 秒以内', '伙伴听后能复述重点']
              : const [
                  'Recording is under 90 seconds',
                  'Partner can repeat the key points',
                ],
          milestones: zh
              ? const ['列关键词', '试录']
              : const ['List keywords', 'Draft recording'],
          allowPartnerReminders: false,
        ),
      ],
      partnerProgress: [
        PartnerProgressItem(
          partnershipId: 'demo_core_partner',
          partnerId: 'user_lena',
          partnerName: 'Lena',
          goalSummary: zh
              ? '每天给伙伴一句具体反馈'
              : 'Give one specific partner feedback each day',
          todayDone: true,
          myTodayDone: false,
          weeklyProgress: 0.72,
          lastCheckinAt: now.subtract(const Duration(hours: 2)),
        ),
        PartnerProgressItem(
          partnershipId: 'demo_goal_mate',
          partnerId: 'user_nora',
          partnerName: 'Nora',
          goalSummary: zh ? '稳定周末复盘节奏' : 'Stabilize weekend reflection rhythm',
          todayDone: false,
          myTodayDone: false,
          weeklyProgress: 0.44,
          lastCheckinAt: now.subtract(const Duration(days: 2)),
        ),
      ],
      sharedGoals: [
        SharedGoalItem(
          id: 'demo_shared_exam',
          title: zh ? '本周把微积分薄弱点补齐' : 'Close the calculus weak spots this week',
          progress: 0.58,
          memberNames: const ['Mika', 'Lena', 'Nora'],
          status: 'active',
        ),
      ],
      squadRisks: [
        SquadRiskItem(
          partnershipId: 'demo_goal_mate',
          memberName: 'Nora',
          reason: zh ? '两天没有同步进展' : 'No progress sync for two days',
          severity: 'medium',
          suggestedAction: 'send_gentle_checkin',
        ),
      ],
      helpable: [
        HelpableItem(
          partnershipId: 'demo_goal_mate',
          memberName: 'Nora',
          need: zh
              ? '今天还没打卡，可以发一句轻提醒'
              : 'No check-in yet today, a gentle nudge may help',
          action: 'encourage',
        ),
      ],
    );
  }
}
