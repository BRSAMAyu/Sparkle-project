import 'package:flutter/material.dart';

class ExecutionCopy {
  const ExecutionCopy._(this._isChinese);

  final bool _isChinese;

  static ExecutionCopy of(BuildContext context) {
    final locale = Localizations.localeOf(context);
    return ExecutionCopy._(locale.languageCode.toLowerCase().startsWith('zh'));
  }

  static String get engineOfflineQueuedMessage =>
      'AI执行引擎当前离线，任务已加入等待队列';

  static String get engineNotConnectedMessage =>
      'AI执行引擎未连接，请先在设置中完成连接';

  String get engineTitle =>
      _isChinese ? 'AI执行引擎' : 'AI Execution Engine';

  String get connectionSuccess =>
      _isChinese ? '连接成功' : 'Connection successful';

  String get connectionFailure =>
      _isChinese ? '连接失败' : 'Connection failed';

  String get configurationSavedAndConnected =>
      _isChinese ? '配置已保存并连接成功' : 'Configuration saved and connected';

  String get configurationSavedButUnavailable => _isChinese
      ? '配置已保存，但当前引擎不可达'
      : 'Configuration saved, but the engine is currently unreachable';

  String get resultPreview =>
      _isChinese ? '结果预览' : 'Result Preview';

  String get executionReplay =>
      _isChinese ? '执行回放' : 'Execution Replay';

  String get selfVerification =>
      _isChinese ? '自验证' : 'Self-Verification';

  String get selfVerificationHint =>
      _isChinese ? '自验证提示' : 'Validation Hint';

  String get resultComparison =>
      _isChinese ? '结果对比' : 'Result Comparison';

  String get adoptResult =>
      _isChinese ? '采纳结果' : 'Adopt Result';

  String get rejectResult =>
      _isChinese ? '退回修改' : 'Request Changes';

  String get viewDetails =>
      _isChinese ? '查看详情' : 'View Details';

  String get collapseDetails =>
      _isChinese ? '收起详情' : 'Collapse';

  String get queueAction =>
      _isChinese ? '加入等待队列' : 'Queue for Later';

  String get connectEngineAction => _isChinese
      ? '先连接 AI执行引擎'
      : 'Connect the AI Execution Engine First';

  String get engineCurrentlyOffline =>
      _isChinese ? 'AI执行引擎当前离线' : 'AI execution engine is offline';

  String get engineNotConnected =>
      _isChinese ? 'AI执行引擎尚未连接' : 'AI execution engine is not connected';

  String get offlineQueueTitle =>
      _isChinese ? '离线等待队列' : 'Offline Waiting Queue';

  String get aboutEngineTitle =>
      _isChinese ? '什么是AI执行引擎？' : 'What is the AI Execution Engine?';

  String get aboutEngineBody => _isChinese
      ? 'AI执行引擎（OpenClaw）可以自动完成网页调研、文档整理等任务。你可以在自己的电脑上运行 OpenClaw，然后在这里连接它。'
      : 'The AI execution engine (OpenClaw) can automate web research, document digestion, and similar tasks. Run OpenClaw on your computer and connect it here.';
}
