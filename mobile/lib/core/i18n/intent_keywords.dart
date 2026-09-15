enum IntentKeywordType {
  chat,
  learning,
  task,
  capsule,
  galaxy,
  knowledge,
  tools,
  user,
}

class IntentKeywords {
  static Map<String, double> getTaskKeywords() {
    return {
      // Chinese
      '创建任务': 1.0,
      '新建任务': 1.0,
      '提醒我': 1.0,
      '创建一个提醒': 1.0,
      '任务': 0.85,
      '做': 0.5,
      '提醒': 0.8,
      '创建': 0.7,
      '新建': 0.7,
      '创建一个': 0.8,
      '添加任务': 0.8,
      // English
      'create task': 1.0,
      'new task': 1.0,
      'remind me': 1.0,
      'set a reminder': 1.0,
      'task': 0.85,
      'todo': 0.85,
      'reminder': 0.85,
      'create': 0.7,
      'new': 0.6,
      'add task': 0.8,
      'schedule': 0.8,
    };
  }

  static List<String> getTaskBaseKeywords() {
    return [
      '任务', '提醒', '创建', '新建', '做', '创建一个', '添加任务',
      'task', 'todo', 'remind', 'create', 'new task', 'add task', 'reminder',
      'schedule', 'set a reminder',
    ];
  }

  static Map<String, double> getCapsuleKeywords() {
    return {
      // Chinese
      '烦': 0.9,
      '感觉': 0.7,
      '觉得': 0.6,
      '好奇': 0.95,
      '想知道': 0.85,
      '疑惑': 0.85,
      '困惑': 0.85,
      '不明白': 0.85,
      // English
      'frustrated': 0.9,
      'annoyed': 0.9,
      'feeling': 0.7,
      'curious': 0.95,
      'wonder': 0.85,
      'wondering': 0.85,
      'confused': 0.85,
      "don't understand": 0.85,
      "can't figure out": 0.85,
      'not sure': 0.8,
    };
  }

  static List<String> getCapsuleBaseKeywords() {
    return [
      '烦', '感觉', '觉得', '好奇', '想知道', '疑惑', '不明白', '困惑',
      'curious', 'wonder', 'confused', 'frustrated', 'annoyed', 'not sure',
      "don't understand", "can't figure out", 'feeling', 'wondering',
    ];
  }

  static Map<String, double> getSprintKeywords() {
    return {
      '冲刺': 1.0,
      'sprint': 1.0,
      '专注模式': 0.95,
      'focus mode': 0.95,
      'deep focus': 0.95,
      '突击': 0.9,
      '专注': 0.88,
      'start sprint': 0.9,
      'enter focus': 0.9,
      'pomodoro': 0.85,
      'focus session': 0.85,
      'deep work': 0.85,
    };
  }

  static List<String> getSprintBaseKeywords() {
    return [
      '冲刺', '专注模式', '突击', '进入冲刺', '开始专注', '专注',
      'sprint', 'focus mode', 'deep focus', 'start sprint', 'enter focus',
      'pomodoro', 'focus session', 'deep work',
    ];
  }

  static Map<String, double> getReviewKeywords() {
    return {
      '复习': 1.0,
      'review': 1.0,
      '回顾': 0.9,
      'go over': 0.9,
      '过一遍': 0.85,
      '温习': 0.9,
      'revise': 0.85,
      'refresh': 0.85,
      'recap': 0.85,
    };
  }

  static List<String> getReviewBaseKeywords() {
    return [
      '复习', '回顾', '过一遍', '温习',
      'review', 'go over', 'revise', 'refresh', 'recap',
    ];
  }

  static Map<String, double> getLearnKeywords() {
    return {
      '学习': 0.9,
      'learn': 0.9,
      'study': 0.9,
      '学一下': 0.85,
      'teach me': 0.85,
      'explain': 0.8,
      'show me how': 0.8,
    };
  }

  static List<String> getLearnBaseKeywords() {
    return [
      '学习', '学一下', '了解一下', '学学',
      'learn', 'study', 'teach me', 'explain', 'show me how',
    ];
  }

  static Map<String, double> getTranslationKeywords() {
    return {
      '翻译': 1.0,
      'translate': 1.0,
      'translation': 0.95,
      '翻译成': 0.95,
      '是什么意思': 0.9,
      'what does this mean': 0.9,
      '怎么说': 0.85,
      'how do you say': 0.85,
      'in english': 0.85,
      'in chinese': 0.85,
      'to english': 0.85,
      'to chinese': 0.85,
    };
  }

  static List<String> getTranslationBaseKeywords() {
    return [
      '翻译', '翻译成', '怎么说', '是什么意思', '什么意思',
      'translate', 'translation', 'how do you say', 'what does this mean',
      'in english', 'in chinese', 'to english', 'to chinese',
    ];
  }

  static Map<String, double> getPrismKeywords() {
    return {
      '认知棱镜': 1.0,
      'cognitive prism': 1.0,
      '行为分析': 1.0,
      'behavior analysis': 1.0,
      '学习习惯': 0.95,
      'learning habit': 0.95,
      '我的画像': 0.9,
      'my profile': 0.9,
      'persona': 0.9,
      '周报': 0.85,
      'weekly report': 0.85,
      '学习分析': 0.85,
      'learning analysis': 0.85,
      'insight': 0.8,
    };
  }

  static List<String> getPrismBaseKeywords() {
    return [
      '认知棱镜', '行为分析', '学习习惯', '我的画像', '周报', '学习分析',
      'cognitive prism', 'behavior analysis', 'learning habit', 'my profile',
      'weekly report', 'learning analysis', 'persona', 'insight',
    ];
  }

  // Add other types as needed
}
