import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('zh')
  ];

  /// No description provided for @appTitle.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle 星火'**
  String get appTitle;

  /// No description provided for @home.
  ///
  /// In zh, this message translates to:
  /// **'驾驶舱'**
  String get home;

  /// No description provided for @community.
  ///
  /// In zh, this message translates to:
  /// **'社群'**
  String get community;

  /// No description provided for @knowledgeGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'知识星图'**
  String get knowledgeGalaxy;

  /// No description provided for @profile.
  ///
  /// In zh, this message translates to:
  /// **'我的'**
  String get profile;

  /// No description provided for @tasks.
  ///
  /// In zh, this message translates to:
  /// **'任务'**
  String get tasks;

  /// No description provided for @chat.
  ///
  /// In zh, this message translates to:
  /// **'对话'**
  String get chat;

  /// No description provided for @plans.
  ///
  /// In zh, this message translates to:
  /// **'计划'**
  String get plans;

  /// No description provided for @galaxy.
  ///
  /// In zh, this message translates to:
  /// **'星图'**
  String get galaxy;

  /// No description provided for @login.
  ///
  /// In zh, this message translates to:
  /// **'登录'**
  String get login;

  /// No description provided for @register.
  ///
  /// In zh, this message translates to:
  /// **'注册'**
  String get register;

  /// No description provided for @username.
  ///
  /// In zh, this message translates to:
  /// **'用户名'**
  String get username;

  /// No description provided for @password.
  ///
  /// In zh, this message translates to:
  /// **'密码'**
  String get password;

  /// No description provided for @email.
  ///
  /// In zh, this message translates to:
  /// **'邮箱'**
  String get email;

  /// No description provided for @nickname.
  ///
  /// In zh, this message translates to:
  /// **'昵称'**
  String get nickname;

  /// No description provided for @noAccount.
  ///
  /// In zh, this message translates to:
  /// **'还没有账号？'**
  String get noAccount;

  /// No description provided for @hasAccount.
  ///
  /// In zh, this message translates to:
  /// **'已有账号？'**
  String get hasAccount;

  /// No description provided for @loginFailed.
  ///
  /// In zh, this message translates to:
  /// **'登录失败'**
  String get loginFailed;

  /// No description provided for @registerFailed.
  ///
  /// In zh, this message translates to:
  /// **'注册失败'**
  String get registerFailed;

  /// No description provided for @weeklyAgenda.
  ///
  /// In zh, this message translates to:
  /// **'每周日程'**
  String get weeklyAgenda;

  /// No description provided for @agendaBusy.
  ///
  /// In zh, this message translates to:
  /// **'繁忙'**
  String get agendaBusy;

  /// No description provided for @agendaFragmented.
  ///
  /// In zh, this message translates to:
  /// **'碎片'**
  String get agendaFragmented;

  /// No description provided for @agendaRelax.
  ///
  /// In zh, this message translates to:
  /// **'放松'**
  String get agendaRelax;

  /// No description provided for @learningMode.
  ///
  /// In zh, this message translates to:
  /// **'学习模式'**
  String get learningMode;

  /// No description provided for @depthPreference.
  ///
  /// In zh, this message translates to:
  /// **'深度偏好'**
  String get depthPreference;

  /// No description provided for @curiosityPreference.
  ///
  /// In zh, this message translates to:
  /// **'好奇偏好'**
  String get curiosityPreference;

  /// No description provided for @settings.
  ///
  /// In zh, this message translates to:
  /// **'设置'**
  String get settings;

  /// No description provided for @language.
  ///
  /// In zh, this message translates to:
  /// **'语言切换'**
  String get language;

  /// No description provided for @languageChinese.
  ///
  /// In zh, this message translates to:
  /// **'简体中文'**
  String get languageChinese;

  /// No description provided for @languageEnglish.
  ///
  /// In zh, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @schedulePreferences.
  ///
  /// In zh, this message translates to:
  /// **'个人偏好'**
  String get schedulePreferences;

  /// No description provided for @notificationSettings.
  ///
  /// In zh, this message translates to:
  /// **'通知设置'**
  String get notificationSettings;

  /// No description provided for @theme.
  ///
  /// In zh, this message translates to:
  /// **'主题样式'**
  String get theme;

  /// No description provided for @darkMode.
  ///
  /// In zh, this message translates to:
  /// **'深色模式'**
  String get darkMode;

  /// No description provided for @lightMode.
  ///
  /// In zh, this message translates to:
  /// **'浅色模式'**
  String get lightMode;

  /// No description provided for @followSystem.
  ///
  /// In zh, this message translates to:
  /// **'跟随系统'**
  String get followSystem;

  /// No description provided for @interactionSettings.
  ///
  /// In zh, this message translates to:
  /// **'交互设置'**
  String get interactionSettings;

  /// No description provided for @enterToSend.
  ///
  /// In zh, this message translates to:
  /// **'回车发送消息'**
  String get enterToSend;

  /// No description provided for @enterToSendDescription.
  ///
  /// In zh, this message translates to:
  /// **'在对话框中按回车键直接发送'**
  String get enterToSendDescription;

  /// No description provided for @taskCard.
  ///
  /// In zh, this message translates to:
  /// **'任务卡片'**
  String get taskCard;

  /// No description provided for @planCard.
  ///
  /// In zh, this message translates to:
  /// **'计划卡片'**
  String get planCard;

  /// No description provided for @startTask.
  ///
  /// In zh, this message translates to:
  /// **'开始任务'**
  String get startTask;

  /// No description provided for @viewDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看详情'**
  String get viewDetails;

  /// No description provided for @finishTask.
  ///
  /// In zh, this message translates to:
  /// **'完成任务'**
  String get finishTask;

  /// No description provided for @abandonTask.
  ///
  /// In zh, this message translates to:
  /// **'放弃任务'**
  String get abandonTask;

  /// No description provided for @estimatedTime.
  ///
  /// In zh, this message translates to:
  /// **'预计耗时'**
  String get estimatedTime;

  /// No description provided for @difficulty.
  ///
  /// In zh, this message translates to:
  /// **'难度'**
  String get difficulty;

  /// No description provided for @exploreGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'探索星图'**
  String get exploreGalaxy;

  /// No description provided for @searchNodes.
  ///
  /// In zh, this message translates to:
  /// **'搜索知识节点'**
  String get searchNodes;

  /// No description provided for @sparkNode.
  ///
  /// In zh, this message translates to:
  /// **'点燃星火'**
  String get sparkNode;

  /// No description provided for @masteryScore.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get masteryScore;

  /// No description provided for @reviewSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'复习建议'**
  String get reviewSuggestion;

  /// No description provided for @aiTutor.
  ///
  /// In zh, this message translates to:
  /// **'AI 导师'**
  String get aiTutor;

  /// No description provided for @send.
  ///
  /// In zh, this message translates to:
  /// **'发送'**
  String get send;

  /// No description provided for @typeMessage.
  ///
  /// In zh, this message translates to:
  /// **'输入消息...'**
  String get typeMessage;

  /// No description provided for @logout.
  ///
  /// In zh, this message translates to:
  /// **'退出登录'**
  String get logout;

  /// No description provided for @confirmLogout.
  ///
  /// In zh, this message translates to:
  /// **'确定要退出登录吗？'**
  String get confirmLogout;

  /// No description provided for @cancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get cancel;

  /// No description provided for @confirm.
  ///
  /// In zh, this message translates to:
  /// **'确定'**
  String get confirm;

  /// No description provided for @errorConnectionFailed.
  ///
  /// In zh, this message translates to:
  /// **'网络似乎有些不给力，请检查一下连接~'**
  String get errorConnectionFailed;

  /// No description provided for @errorConnectionTimeout.
  ///
  /// In zh, this message translates to:
  /// **'连接超时啦，请稍后再试'**
  String get errorConnectionTimeout;

  /// No description provided for @errorServerIssue.
  ///
  /// In zh, this message translates to:
  /// **'服务器正在打盹，请稍后再试'**
  String get errorServerIssue;

  /// No description provided for @errorRateLimit.
  ///
  /// In zh, this message translates to:
  /// **'操作太频繁啦，休息一下再试吧~'**
  String get errorRateLimit;

  /// No description provided for @errorAuthRequired.
  ///
  /// In zh, this message translates to:
  /// **'请先登录后再使用这个功能哦'**
  String get errorAuthRequired;

  /// No description provided for @errorTokenExpired.
  ///
  /// In zh, this message translates to:
  /// **'登录信息已过期，请重新登录~'**
  String get errorTokenExpired;

  /// No description provided for @errorNotFound.
  ///
  /// In zh, this message translates to:
  /// **'没有找到相关内容，试试其他关键词？'**
  String get errorNotFound;

  /// No description provided for @errorEmptyState.
  ///
  /// In zh, this message translates to:
  /// **'这里空空如也，快去添加内容吧'**
  String get errorEmptyState;

  /// No description provided for @retry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get retry;

  /// No description provided for @back.
  ///
  /// In zh, this message translates to:
  /// **'返回'**
  String get back;

  /// No description provided for @welcomeSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'点燃你的学习潜能'**
  String get welcomeSubtitle;

  /// No description provided for @pleaseEnterUsername.
  ///
  /// In zh, this message translates to:
  /// **'请输入用户名或邮箱'**
  String get pleaseEnterUsername;

  /// No description provided for @pleaseEnterPassword.
  ///
  /// In zh, this message translates to:
  /// **'请输入密码'**
  String get pleaseEnterPassword;

  /// No description provided for @orText.
  ///
  /// In zh, this message translates to:
  /// **'或'**
  String get orText;

  /// No description provided for @continueAsGuest.
  ///
  /// In zh, this message translates to:
  /// **'以访客身份继续'**
  String get continueAsGuest;

  /// No description provided for @joinSparkle.
  ///
  /// In zh, this message translates to:
  /// **'加入 Sparkle'**
  String get joinSparkle;

  /// No description provided for @usernameMinLength.
  ///
  /// In zh, this message translates to:
  /// **'用户名至少需要3个字符'**
  String get usernameMinLength;

  /// No description provided for @invalidEmail.
  ///
  /// In zh, this message translates to:
  /// **'请输入有效的邮箱地址'**
  String get invalidEmail;

  /// No description provided for @passwordMinLength.
  ///
  /// In zh, this message translates to:
  /// **'密码至少需要6个字符'**
  String get passwordMinLength;

  /// No description provided for @confirmPassword.
  ///
  /// In zh, this message translates to:
  /// **'确认密码'**
  String get confirmPassword;

  /// No description provided for @passwordsDoNotMatch.
  ///
  /// In zh, this message translates to:
  /// **'两次输入的密码不一致'**
  String get passwordsDoNotMatch;

  /// No description provided for @google.
  ///
  /// In zh, this message translates to:
  /// **'Google'**
  String get google;

  /// No description provided for @apple.
  ///
  /// In zh, this message translates to:
  /// **'Apple'**
  String get apple;

  /// No description provided for @wechat.
  ///
  /// In zh, this message translates to:
  /// **'微信'**
  String get wechat;

  /// No description provided for @createGrowthPlan.
  ///
  /// In zh, this message translates to:
  /// **'创建成长计划'**
  String get createGrowthPlan;

  /// No description provided for @createSprintPlan.
  ///
  /// In zh, this message translates to:
  /// **'创建冲刺计划'**
  String get createSprintPlan;

  /// No description provided for @featureComingSoon.
  ///
  /// In zh, this message translates to:
  /// **'精彩功能即将登场'**
  String get featureComingSoon;

  /// No description provided for @stayTuned.
  ///
  /// In zh, this message translates to:
  /// **'敬请期待~'**
  String get stayTuned;

  /// No description provided for @aiNudgeGentle.
  ///
  /// In zh, this message translates to:
  /// **'休息一下吧，效率会更高哦'**
  String get aiNudgeGentle;

  /// No description provided for @aiNudgeFocus.
  ///
  /// In zh, this message translates to:
  /// **'保持专注，你正在状态！'**
  String get aiNudgeFocus;

  /// No description provided for @qwen3CognitiveStatus.
  ///
  /// In zh, this message translates to:
  /// **'Qwen3 认知状态'**
  String get qwen3CognitiveStatus;

  /// No description provided for @winStreak.
  ///
  /// In zh, this message translates to:
  /// **'连胜'**
  String get winStreak;

  /// No description provided for @myPersona.
  ///
  /// In zh, this message translates to:
  /// **'我的画像'**
  String get myPersona;

  /// No description provided for @systemActivity.
  ///
  /// In zh, this message translates to:
  /// **'系统活动'**
  String get systemActivity;

  /// No description provided for @memoryControl.
  ///
  /// In zh, this message translates to:
  /// **'记忆控制'**
  String get memoryControl;

  /// No description provided for @brightness.
  ///
  /// In zh, this message translates to:
  /// **'亮度'**
  String get brightness;

  /// No description provided for @dragToAdjust.
  ///
  /// In zh, this message translates to:
  /// **'拖动控制点，调整你的AI辅导风格'**
  String get dragToAdjust;

  /// No description provided for @capsuleGeneration.
  ///
  /// In zh, this message translates to:
  /// **'胶囊生成'**
  String get capsuleGeneration;

  /// No description provided for @adjustAndGenerate.
  ///
  /// In zh, this message translates to:
  /// **'调整偏好并生成专属好奇心胶囊'**
  String get adjustAndGenerate;

  /// No description provided for @generateNow.
  ///
  /// In zh, this message translates to:
  /// **'立即生成胶囊'**
  String get generateNow;

  /// No description provided for @generating.
  ///
  /// In zh, this message translates to:
  /// **'生成中...'**
  String get generating;

  /// No description provided for @selectTimeSlots.
  ///
  /// In zh, this message translates to:
  /// **'框选时间段：红色繁忙，绿色碎片(AI提醒)，蓝色休息'**
  String get selectTimeSlots;

  /// No description provided for @enableNotifications.
  ///
  /// In zh, this message translates to:
  /// **'启用通知'**
  String get enableNotifications;

  /// No description provided for @smartReminders.
  ///
  /// In zh, this message translates to:
  /// **'智能碎片时间提醒'**
  String get smartReminders;

  /// No description provided for @pushMicroTasks.
  ///
  /// In zh, this message translates to:
  /// **'在绿色时间段主动推送微任务'**
  String get pushMicroTasks;

  /// No description provided for @transparentMode.
  ///
  /// In zh, this message translates to:
  /// **'透明模式'**
  String get transparentMode;

  /// No description provided for @enableTransparentMode.
  ///
  /// In zh, this message translates to:
  /// **'启用透明模式'**
  String get enableTransparentMode;

  /// No description provided for @showStatusOverview.
  ///
  /// In zh, this message translates to:
  /// **'显示状态与资源消耗概览'**
  String get showStatusOverview;

  /// No description provided for @transparencyLevel.
  ///
  /// In zh, this message translates to:
  /// **'透明度级别'**
  String get transparencyLevel;

  /// No description provided for @basic.
  ///
  /// In zh, this message translates to:
  /// **'基础'**
  String get basic;

  /// No description provided for @standard.
  ///
  /// In zh, this message translates to:
  /// **'标准'**
  String get standard;

  /// No description provided for @advanced.
  ///
  /// In zh, this message translates to:
  /// **'高级'**
  String get advanced;

  /// No description provided for @systemFeedback.
  ///
  /// In zh, this message translates to:
  /// **'系统反馈级别'**
  String get systemFeedback;

  /// No description provided for @controlUpdateDetails.
  ///
  /// In zh, this message translates to:
  /// **'控制系统更新提示的详细程度'**
  String get controlUpdateDetails;

  /// No description provided for @silent.
  ///
  /// In zh, this message translates to:
  /// **'静默'**
  String get silent;

  /// No description provided for @summary.
  ///
  /// In zh, this message translates to:
  /// **'摘要'**
  String get summary;

  /// No description provided for @detailed.
  ///
  /// In zh, this message translates to:
  /// **'详细'**
  String get detailed;

  /// No description provided for @sync.
  ///
  /// In zh, this message translates to:
  /// **'同步'**
  String get sync;

  /// No description provided for @syncCenter.
  ///
  /// In zh, this message translates to:
  /// **'同步中心'**
  String get syncCenter;

  /// No description provided for @viewOfflineQueue.
  ///
  /// In zh, this message translates to:
  /// **'查看离线队列状态与重试'**
  String get viewOfflineQueue;

  /// No description provided for @capsuleTaskCreated.
  ///
  /// In zh, this message translates to:
  /// **'✨ 胶囊生成任务已创建'**
  String get capsuleTaskCreated;

  /// No description provided for @generationFailed.
  ///
  /// In zh, this message translates to:
  /// **'生成失败，请稍后重试'**
  String get generationFailed;

  /// No description provided for @generationFailedWithDetail.
  ///
  /// In zh, this message translates to:
  /// **'生成失败: {error}'**
  String generationFailedWithDetail(Object error);

  /// No description provided for @version.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle v2.1.0-stable\n© 2025 Sparkle Team'**
  String get version;

  /// No description provided for @editPlan.
  ///
  /// In zh, this message translates to:
  /// **'编辑计划'**
  String get editPlan;

  /// No description provided for @planEditInProgress.
  ///
  /// In zh, this message translates to:
  /// **'计划编辑功能开发中'**
  String get planEditInProgress;

  /// No description provided for @planId.
  ///
  /// In zh, this message translates to:
  /// **'计划ID'**
  String get planId;

  /// No description provided for @featureInDevelopment.
  ///
  /// In zh, this message translates to:
  /// **'此功能正在开发中，即将推出'**
  String get featureInDevelopment;

  /// No description provided for @sprintHistory.
  ///
  /// In zh, this message translates to:
  /// **'冲刺历史'**
  String get sprintHistory;

  /// No description provided for @noSprintHistory.
  ///
  /// In zh, this message translates to:
  /// **'暂无冲刺历史'**
  String get noSprintHistory;

  /// No description provided for @loadingFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败'**
  String get loadingFailed;

  /// No description provided for @completionProgress.
  ///
  /// In zh, this message translates to:
  /// **'完成进度'**
  String get completionProgress;

  /// No description provided for @tasksCompleted.
  ///
  /// In zh, this message translates to:
  /// **'{completed}/{total} 任务'**
  String tasksCompleted(Object completed, Object total);

  /// No description provided for @sprintCompleted.
  ///
  /// In zh, this message translates to:
  /// **'✅ 冲刺已完成并归档'**
  String get sprintCompleted;

  /// No description provided for @sprintExtended.
  ///
  /// In zh, this message translates to:
  /// **'冲刺已延长 {days} 天'**
  String sprintExtended(Object days);

  /// No description provided for @sprintAbandoned.
  ///
  /// In zh, this message translates to:
  /// **'冲刺已放弃'**
  String get sprintAbandoned;

  /// No description provided for @noActiveSprint.
  ///
  /// In zh, this message translates to:
  /// **'没有活跃的冲刺'**
  String get noActiveSprint;

  /// No description provided for @networkErrorRetry.
  ///
  /// In zh, this message translates to:
  /// **'网络错误，请重试'**
  String get networkErrorRetry;

  /// No description provided for @submitFailed.
  ///
  /// In zh, this message translates to:
  /// **'提交失败，请重试'**
  String get submitFailed;

  /// No description provided for @loadHistoryFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载历史失败'**
  String get loadHistoryFailed;

  /// No description provided for @loadMoreFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载更多消息失败'**
  String get loadMoreFailed;

  /// No description provided for @sendFailed.
  ///
  /// In zh, this message translates to:
  /// **'发送失败，请重试'**
  String get sendFailed;

  /// No description provided for @view.
  ///
  /// In zh, this message translates to:
  /// **'查看'**
  String get view;

  /// No description provided for @ongoing.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get ongoing;

  /// No description provided for @errorTitle.
  ///
  /// In zh, this message translates to:
  /// **'哎呀，出错了'**
  String get errorTitle;

  /// No description provided for @warningTitle.
  ///
  /// In zh, this message translates to:
  /// **'温馨提示'**
  String get warningTitle;

  /// No description provided for @infoTitle.
  ///
  /// In zh, this message translates to:
  /// **'小提示'**
  String get infoTitle;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
