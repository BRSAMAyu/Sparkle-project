import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

String localizeSimulationScenario(String key, [AppLocalizations? l10n]) {
  if (l10n != null) {
    switch (key) {
      case 'study_group': return l10n.simulationSceneStudyGroup;
      case 'knowledge_debate': return l10n.simulationSceneKnowledgeDebate;
      case 'historical_roleplay': return l10n.simulationSceneHistoricalRoleplay;
      case 'socratic_dialogue': return l10n.simulationSceneSocraticDialogue;
      case 'case_analysis': return l10n.simulationSceneCaseAnalysis;
      case 'what_if_path': return l10n.simulationSceneWhatIfPath;
      case 'concept_map_build': return l10n.simulationSceneConceptMapBuild;
      case 'error_diagnosis': return l10n.simulationSceneErrorDiagnosis;
    }
  }
  return _localizeExact(key);
}

String localizeSimulationEngineState(String? state, [AppLocalizations? l10n]) {
  switch ((state ?? '').trim().toUpperCase()) {
    case 'WAITING_FOR_USER':
      return l10n?.simulationStateWaiting ?? '等待你的判断';
    case 'COMPLETED':
      return l10n?.simulationStateCompleted ?? '讨论已收束';
    case 'RUNNING':
      return l10n?.simulationStateRunning ?? '正在推进讨论';
    case 'PENDING':
      return l10n?.simulationStatePending ?? '正在准备';
    default:
      return (state ?? '').trim().isEmpty
          ? (l10n?.simulationStateReady ?? '准备中')
          : localizeSimulationText(state!, l10n);
  }
}

String localizeSimulationRoleHint(String text, [AppLocalizations? l10n]) => _localizeFreeText(text, l10n);

String localizeSimulationStance(String? text, [AppLocalizations? l10n]) {
  final value = (text ?? '').trim();
  if (value.isEmpty) {
    return '';
  }
  if (l10n != null) {
    switch (value.toLowerCase()) {
      case 'supporting': return l10n.simulationStanceSupporting;
      case 'supportive': return l10n.simulationStanceSupportive;
      case 'opposing': return l10n.simulationStanceOpposing;
      case 'moderating': return l10n.simulationStanceModerating;
      case 'probing': return l10n.simulationStanceProbing;
      case 'challenging': return l10n.simulationStanceChallenging;
      case 'immersive': return l10n.simulationStanceImmersive;
      case 'contextual': return l10n.simulationStanceContextual;
      case 'reflective': return l10n.simulationStanceReflective;
    }
  }
  return _localizeFreeText(value, l10n);
}

String localizeSimulationTurnGoal(String turnGoal, [AppLocalizations? l10n]) {
  if (l10n != null) {
    switch (turnGoal.trim().toLowerCase()) {
      case 'challenge': return l10n.simulationActionChallenge;
      case 'synthesize': return l10n.simulationActionSynthesize;
      case 'open': return l10n.simulationActionOpen;
      case 'guide_user': return l10n.simulationActionGuideUser;
      case 'probe': return l10n.simulationActionProbe;
      case 'extend': return l10n.simulationActionExtend;
      case 'user_response': return l10n.simulationActionUserResponse;
    }
  }
  return _localizeFreeText(turnGoal, l10n);
}

String localizeSimulationSource(String source, [AppLocalizations? l10n]) {
  if (l10n != null) {
    switch (source.trim().toLowerCase()) {
      case 'galaxy': return l10n.simulationSourceGalaxy;
      case 'tasks': return l10n.simulationSourceTasks;
      case 'plan': return l10n.simulationSourcePlan;
      case 'starter_graph': return l10n.simulationSourceStarterGraph;
      case 'knowledge_graph': return l10n.simulationSourceKnowledgeGraph;
      case 'template': return l10n.simulationSourceTemplate;
      case 'error_book': return l10n.simulationSourceErrorBook;
      case 'onboarding_profile': return l10n.simulationSourceOnboardingProfile;
    }
  }
  return _localizeExact(source);
}

String localizeSimulationText(String text, [AppLocalizations? l10n]) => _localizeFreeText(text, l10n);

String _localizeExact(String text) {
  final normalized = text.trim();
  if (normalized.isEmpty) {
    return '';
  }
  switch (normalized.toLowerCase()) {
    case 'study_group': return '虚拟学习小组';
    case 'knowledge_debate': return '知识辩论';
    case 'historical_roleplay': return '历史角色扮演';
    case 'socratic_dialogue': return context.l10n.simSocraticCopy;
    case 'case_analysis': return '案例拆解';
    case 'what_if_path': return '假设分支推演';
    case 'concept_map_build': return '概念图共建';
    case 'error_diagnosis': return context.l10n.simErrorDiagCopy;
    case 'analyst': return '分析者';
    case 'expert': return '专家';
    case 'coach': return '教练';
    case 'navigator': return '导航者';
    case 'challenger': return '质疑者';
    case 'supporter': return '支持者';
    case 'moderator': return '主持协调';
    case 'questioner': return '追问者';
    case 'observer': return '观察者';
    case 'mentor': return '导师';
    case 'builder': return '搭建者';
    case 'connector': return '连接者';
    case 'practitioner': return '实践派';
    default: return normalized;
  }
}

String _localizeFreeText(String text, [AppLocalizations? l10n]) {
  final normalized = text.trim();
  if (normalized.isEmpty) {
    return '';
  }
  if (_containsChinese(normalized)) {
    return normalized;
  }
  return _localizeExact(normalized);
}

bool _containsChinese(String text) =>
    RegExp(r'[\u4e00-\u9fff]').hasMatch(text);
