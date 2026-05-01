import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class ExecutionCopy {
  const ExecutionCopy._(this._l10n);

  final AppLocalizations _l10n;

  static ExecutionCopy of(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ExecutionCopy._(l10n!);
  }

  static String engineOfflineQueuedMessage([bool isChinese = false]) =>
      isChinese
          ? 'AI 执行引擎当前离线，任务已加入等待队列'
          : 'AI execution engine is currently offline, the task has been added to the waiting queue';

  static String engineNotConnectedMessage([bool isChinese = false]) =>
      isChinese
          ? 'AI 执行引擎未连接，请先在设置中连接。'
          : 'AI execution engine is not connected. Please connect it in settings first.';

  String get engineTitle => _l10n.executionEngineTitle;

  String get connectionSuccess => _l10n.executionConnectionSuccess;

  String get connectionFailure => _l10n.executionConnectionFailure;

  String get configurationSavedAndConnected =>
      _l10n.executionConfigSavedConnected;

  String get configurationSavedButUnavailable =>
      _l10n.executionConfigSavedUnavailable;

  String get resultPreview => _l10n.executionResultPreview;

  String get executionReplay => _l10n.executionReplay;

  String get selfVerification => _l10n.executionSelfVerification;

  String get selfVerificationHint => _l10n.executionSelfVerificationHint;

  String get resultComparison => _l10n.executionResultComparison;

  String get adoptResult => _l10n.executionAdoptResult;

  String get rejectResult => _l10n.executionRejectResult;

  String get viewDetails => _l10n.executionViewDetails;

  String get collapseDetails => _l10n.executionCollapseDetails;

  String get queueAction => _l10n.executionQueueAction;

  String get connectEngineAction => _l10n.executionConnectEngine;

  String get engineCurrentlyOffline => _l10n.executionEngineOffline;

  String get engineNotConnected => _l10n.executionEngineNotConnected;

  String get offlineQueueTitle => _l10n.executionOfflineQueueTitle;

  String get aboutEngineTitle => _l10n.executionAboutEngineTitle;

  String get aboutEngineBody => _l10n.executionAboutEngineBody;
}
