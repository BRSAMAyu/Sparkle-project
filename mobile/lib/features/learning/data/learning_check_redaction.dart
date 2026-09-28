/// V4-U10 · 检验答案红化门（移动端消费侧镜像；I07 hybrid-policy 的 Dart 面）。
///
/// 权威在服务端：`backend/app/core/hybrid_policy.py` 的
/// `INDEPENDENT_CHECK_ANSWER_KEYS`（冻结集，扩展 = contract-owner bump）。
/// 本文件是**消费侧镜像**——任何载荷进入检验用户可读状态（Riverpod state /
/// Widget 树 / 日志）之前必须过 [redactIndependentCheck]；服务端契约变更时
/// 此处必须同步跟随（审查锚：tests/features/learning 的键集钉死测试）。
///
/// 纪律（与 SCREEN_FAMILIES「测试命题不能把答案塞进可被用户读出的UI状态」对齐）：
/// - 触发面：`kind == 'independent_check'` 或 `independent_check == true` 的
///   节点（含整棵子树）；
/// - 非标记节点内的同名字段**不动**（用户自有错题材料如 correct_answer 不在
///   本门语义内——与服务端判定一致）；
/// - 纯函数：不改输入，返回深拷贝 + 剥除路径（供降级判定与观测）。
library;

/// 检验答案键封闭集（I07 `INDEPENDENT_CHECK_ANSWER_KEYS` v1 逐键镜像）。
const Set<String> kIndependentCheckAnswerKeys = {
  'answer',
  'correct_answer',
  'expected_answer',
  'reference_answer',
  'model_answer',
  'solution',
  'solution_steps',
  'answer_key',
  'explanation',
  'correct_option',
  'correct',
};

/// 检验节点标记键/值（与服务端 `INDEPENDENT_CHECK_KIND`/`_FLAG_KEY` 同词）。
const String kIndependentCheckKind = 'independent_check';
const String kIndependentCheckFlagKey = 'independent_check';

bool _isIndependentCheckNode(Object? node) {
  if (node is Map) {
    if (node['kind'] == kIndependentCheckKind) {
      return true;
    }
    return identical(node[kIndependentCheckFlagKey], true);
  }
  return false;
}

Object? _stripAnswers(Object? node, String prefix, bool inCheck, List<String> removed) {
  if (node is Map) {
    final active = inCheck || _isIndependentCheckNode(node);
    final clean = <String, Object?>{};
    node.forEach((Object? key, Object? value) {
      final path = prefix.isEmpty ? '$key' : '$prefix.$key';
      if (active && kIndependentCheckAnswerKeys.contains(key)) {
        removed.add(path);
        return;
      }
      clean['$key'] = _stripAnswers(value, path, active, removed);
    });
    return clean;
  }
  if (node is List) {
    final clean = <Object?>[];
    for (var i = 0; i < node.length; i++) {
      clean.add(_stripAnswers(node[i], '$prefix[$i]', inCheck, removed));
    }
    return clean;
  }
  return node;
}

/// 剥除载荷中 independent_check 节点内的答案键，返回 `(干净载荷, 移除路径)`。
///
/// 返回的是深拷贝新容器；调用方不得把原始载荷再投递给任何用户可读面。
(Object?, List<String>) redactIndependentCheck(Object? payload) {
  final removed = <String>[];
  final clean = _stripAnswers(payload, '', false, removed);
  return (clean, List<String>.unmodifiable(removed));
}

/// 泄漏探针：载荷中 independent_check 节点内是否残留答案键（守卫/测试用）。
bool containsIndependentCheckAnswer(Object? payload) {
  final (_, removed) = redactIndependentCheck(payload);
  return removed.isNotEmpty;
}
