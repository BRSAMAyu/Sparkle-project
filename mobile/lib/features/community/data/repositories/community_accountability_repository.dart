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
    final l10n = I18nService.instance.l10n;
    final now = DateTime.now();
    return CommunityAccountabilityHub(
      myCommitments: [
        CommitmentCardPayload(
          id: 'demo_commitment_exam_review',
          summary: l10n.demoCommitmentExamSummary,
          dueAt: now.add(const Duration(hours: 7)),
          witnessNames: const ['Lena', 'Nora'],
          progress: 0.62,
          status: 'due_soon',
          successCriteria: [
            l10n.demoCommitmentExamCriteria1,
            l10n.demoCommitmentExamCriteria2,
          ],
          milestones: [
            l10n.demoCommitmentExamMilestone1,
            l10n.demoCommitmentExamMilestone2,
            l10n.demoCommitmentExamMilestone3,
          ],
          evidenceRefs: const ['demo-evidence-token'],
          allowPartnerReminders: true,
        ),
        CommitmentCardPayload(
          id: 'demo_commitment_speaking',
          summary: l10n.demoCommitmentSpeakingSummary,
          dueAt: now.add(const Duration(days: 2)),
          witnessNames: const ['Lena'],
          progress: 0.35,
          status: 'active',
          successCriteria: [
            l10n.demoCommitmentSpeakingCriteria1,
            l10n.demoCommitmentSpeakingCriteria2,
          ],
          milestones: [
            l10n.demoCommitmentSpeakingMilestone1,
            l10n.demoCommitmentSpeakingMilestone2,
          ],
          allowPartnerReminders: false,
        ),
      ],
      partnerProgress: [
        PartnerProgressItem(
          partnershipId: 'demo_core_partner',
          partnerId: 'user_lena',
          partnerName: 'Lena',
          goalSummary: l10n.demoPartnerGoalFeedback,
          todayDone: true,
          myTodayDone: false,
          weeklyProgress: 0.72,
          lastCheckinAt: now.subtract(const Duration(hours: 2)),
        ),
        PartnerProgressItem(
          partnershipId: 'demo_goal_mate',
          partnerId: 'user_nora',
          partnerName: 'Nora',
          goalSummary: l10n.demoPartnerGoalReflection,
          todayDone: false,
          myTodayDone: false,
          weeklyProgress: 0.44,
          lastCheckinAt: now.subtract(const Duration(days: 2)),
        ),
      ],
      sharedGoals: [
        SharedGoalItem(
          id: 'demo_shared_exam',
          title: l10n.demoSharedGoalTitle,
          progress: 0.58,
          memberNames: const ['Mika', 'Lena', 'Nora'],
          status: 'active',
        ),
      ],
      squadRisks: [
        SquadRiskItem(
          partnershipId: 'demo_goal_mate',
          memberName: 'Nora',
          reason: l10n.demoSquadRiskNoSync,
          severity: 'medium',
          suggestedAction: 'send_gentle_checkin',
        ),
      ],
      helpable: [
        HelpableItem(
          partnershipId: 'demo_goal_mate',
          memberName: 'Nora',
          need: l10n.demoHelpableNudge,
          action: 'encourage',
        ),
      ],
    );
  }
}
