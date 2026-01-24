enum IntentType { task, capsule, chat }

class IntentClassifier {
  const IntentClassifier._();

  static IntentType? classify(String text) {
    final lower = text.toLowerCase();

    if (lower.contains('提醒') ||
        lower.contains('做') ||
        lower.contains('任务') ||
        lower.contains('task') ||
        lower.contains('remind') ||
        lower.contains('todo')) {
      return IntentType.task;
    }

    if (lower.contains('烦') ||
        lower.contains('想') ||
        lower.contains('！') ||
        lower.contains('feel') ||
        lower.contains('think')) {
      return IntentType.capsule;
    }

    if (lower.length > 10) {
      return IntentType.chat;
    }

    return null;
  }
}
