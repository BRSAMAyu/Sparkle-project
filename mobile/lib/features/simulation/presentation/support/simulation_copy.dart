const Map<String, String> simulationScenarioLabels = {
  'study_group': '虚拟学习小组',
  'knowledge_debate': '知识辩论',
  'historical_roleplay': '历史角色扮演',
  'socratic_dialogue': '苏格拉底式对话',
  'case_analysis': '案例拆解',
  'what_if_path': '假设分支推演',
  'concept_map_build': '概念图共建',
  'error_diagnosis': '错因诊断',
};

String localizeSimulationScenario(String key) =>
    simulationScenarioLabels[key] ?? _localizeExact(key);

String localizeSimulationEngineState(String? state) {
  switch ((state ?? '').trim().toUpperCase()) {
    case 'WAITING_FOR_USER':
      return '等待你的判断';
    case 'COMPLETED':
      return '讨论已收束';
    case 'RUNNING':
      return '正在推进讨论';
    case 'PENDING':
      return '正在准备';
    default:
      return (state ?? '').trim().isEmpty ? '准备中' : localizeSimulationText(state!);
  }
}

String localizeSimulationRoleHint(String text) => _localizeFreeText(text);

String localizeSimulationStance(String? text) {
  final value = (text ?? '').trim();
  if (value.isEmpty) {
    return '';
  }
  switch (value.toLowerCase()) {
    case 'supporting':
      return '支持派';
    case 'supportive':
      return '补充支持';
    case 'opposing':
      return '反方质疑';
    case 'moderating':
      return '居中协调';
    case 'probing':
      return '追问推进';
    case 'challenging':
      return '提出质疑';
    case 'immersive':
      return '沉浸代入';
    case 'contextual':
      return '补充背景';
    case 'reflective':
      return '回看反思';
    default:
      return _localizeFreeText(value);
  }
}

String localizeSimulationTurnGoal(String turnGoal) {
  switch (turnGoal.trim().toLowerCase()) {
    case 'challenge':
      return '提出质疑';
    case 'synthesize':
      return '整合观点';
    case 'open':
      return '打开话题';
    case 'guide_user':
      return '邀请你作答';
    case 'probe':
      return '继续追问';
    case 'extend':
      return '展开补充';
    case 'user_response':
      return '你的回应';
    default:
      return _localizeFreeText(turnGoal);
  }
}

String localizeSimulationSource(String source) {
  switch (source.trim().toLowerCase()) {
    case 'galaxy':
      return '知识星图';
    case 'tasks':
      return '任务记录';
    case 'plan':
      return '学习计划';
    case 'starter_graph':
      return '起步图谱';
    case 'knowledge_graph':
      return '知识图谱';
    case 'template':
      return '默认角色模板';
    case 'error_book':
      return '错题记录';
    case 'onboarding_profile':
      return '学习画像';
    default:
      return _localizeExact(source);
  }
}

String localizeSimulationText(String text) => _localizeFreeText(text);

String _localizeExact(String text) {
  final normalized = text.trim();
  if (normalized.isEmpty) {
    return '';
  }
  switch (normalized.toLowerCase()) {
    case 'study_group':
      return '虚拟学习小组';
    case 'knowledge_debate':
      return '知识辩论';
    case 'historical_roleplay':
      return '历史角色扮演';
    case 'socratic_dialogue':
      return '苏格拉底式对话';
    case 'case_analysis':
      return '案例拆解';
    case 'what_if_path':
      return '假设分支推演';
    case 'concept_map_build':
      return '概念图共建';
    case 'error_diagnosis':
      return '错因诊断';
    case 'analyst':
      return '分析者';
    case 'expert':
      return '专家';
    case 'coach':
      return '教练';
    case 'navigator':
      return '导航者';
    case 'challenger':
      return '质疑者';
    case 'supporter':
      return '支持者';
    case 'moderator':
      return '主持协调';
    case 'questioner':
      return '追问者';
    case 'observer':
      return '观察者';
    case 'mentor':
      return '导师';
    case 'builder':
      return '搭建者';
    case 'connector':
      return '连接者';
    case 'practitioner':
      return '实践派';
    default:
      return normalized;
  }
}

String _localizeFreeText(String text) {
  final normalized = text.trim();
  if (normalized.isEmpty) {
    return '';
  }
  if (_containsChinese(normalized)) {
    return normalized;
  }

  var localized = normalized;
  const replacements = <String, String>{
    'study group': '虚拟学习小组',
    'knowledge debate': '知识辩论',
    'historical roleplay': '历史角色扮演',
    'socratic dialogue': '苏格拉底式对话',
    'case analysis': '案例拆解',
    'what-if path': '假设分支推演',
    'what-if': '假设分支',
    'concept map build': '概念图共建',
    'concept map': '概念图',
    'error diagnosis': '错因诊断',
    'supporting': '支持派',
    'supportive': '补充支持',
    'opposing': '反方质疑',
    'moderating': '居中协调',
    'probing': '追问推进',
    'challenging': '提出质疑',
    'immersive': '沉浸代入',
    'contextual': '补充背景',
    'reflective': '回看反思',
    'analyst': '分析者',
    'expert': '专家',
    'coach': '教练',
    'navigator': '导航者',
    'challenger': '质疑者',
    'supporter': '支持者',
    'moderator': '主持协调',
    'questioner': '追问者',
    'observer': '观察者',
    'mentor': '导师',
    'builder': '搭建者',
    'connector': '连接者',
    'practitioner': '实践派',
    'framework': '框架',
    'strategy': '策略',
    'insight': '洞察',
    'summary': '总结',
  };

  for (final entry in replacements.entries) {
    localized = localized.replaceAllMapped(
      RegExp(entry.key, caseSensitive: false),
      (_) => entry.value,
    );
  }

  return localized;
}

bool _containsChinese(String text) =>
    RegExp(r'[\u4e00-\u9fff]').hasMatch(text);
