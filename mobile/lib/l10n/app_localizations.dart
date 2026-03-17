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
  /// **'功能开发中...'**
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

  /// No description provided for @aiStatusThinking.
  ///
  /// In zh, this message translates to:
  /// **'思考中...'**
  String get aiStatusThinking;

  /// No description provided for @aiStatusGenerating.
  ///
  /// In zh, this message translates to:
  /// **'正在生成回复...'**
  String get aiStatusGenerating;

  /// No description provided for @aiStatusExecutingTool.
  ///
  /// In zh, this message translates to:
  /// **'正在使用工具...'**
  String get aiStatusExecutingTool;

  /// No description provided for @aiStatusSearching.
  ///
  /// In zh, this message translates to:
  /// **'正在搜索...'**
  String get aiStatusSearching;

  /// No description provided for @aiStatusProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中...'**
  String get aiStatusProcessing;

  /// No description provided for @aiStatusAnalyzing.
  ///
  /// In zh, this message translates to:
  /// **'分析中...'**
  String get aiStatusAnalyzing;

  /// No description provided for @aiStatusPlanning.
  ///
  /// In zh, this message translates to:
  /// **'规划中...'**
  String get aiStatusPlanning;

  /// No description provided for @aiStatusReviewing.
  ///
  /// In zh, this message translates to:
  /// **'审核中...'**
  String get aiStatusReviewing;

  /// No description provided for @aiStatusWaiting.
  ///
  /// In zh, this message translates to:
  /// **'等待输入...'**
  String get aiStatusWaiting;

  /// No description provided for @aiStatusReady.
  ///
  /// In zh, this message translates to:
  /// **'就绪'**
  String get aiStatusReady;

  /// No description provided for @aiStatusError.
  ///
  /// In zh, this message translates to:
  /// **'发生错误'**
  String get aiStatusError;

  /// No description provided for @aiStatusIdle.
  ///
  /// In zh, this message translates to:
  /// **'空闲'**
  String get aiStatusIdle;

  /// No description provided for @aiStatusConnecting.
  ///
  /// In zh, this message translates to:
  /// **'连接中...'**
  String get aiStatusConnecting;

  /// No description provided for @aiStatusReconnecting.
  ///
  /// In zh, this message translates to:
  /// **'重新连接...'**
  String get aiStatusReconnecting;

  /// No description provided for @aiStatusDisconnected.
  ///
  /// In zh, this message translates to:
  /// **'已断开连接'**
  String get aiStatusDisconnected;

  /// No description provided for @levelPrefix.
  ///
  /// In zh, this message translates to:
  /// **'Lv.'**
  String get levelPrefix;

  /// No description provided for @toolsSpeechToTextTitle.
  ///
  /// In zh, this message translates to:
  /// **'语音转文字'**
  String get toolsSpeechToTextTitle;

  /// No description provided for @toolsSpeechToTextDesc.
  ///
  /// In zh, this message translates to:
  /// **'实时语音转录'**
  String get toolsSpeechToTextDesc;

  /// No description provided for @toolsCalculatorTitle.
  ///
  /// In zh, this message translates to:
  /// **'计算器'**
  String get toolsCalculatorTitle;

  /// No description provided for @toolsCalculatorDesc.
  ///
  /// In zh, this message translates to:
  /// **'快速计算和数学运算'**
  String get toolsCalculatorDesc;

  /// No description provided for @toolsFocusTimerTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注计时器'**
  String get toolsFocusTimerTitle;

  /// No description provided for @toolsFocusTimerDesc.
  ///
  /// In zh, this message translates to:
  /// **'番茄钟式专注会话'**
  String get toolsFocusTimerDesc;

  /// No description provided for @toolsNotesTitle.
  ///
  /// In zh, this message translates to:
  /// **'快速笔记'**
  String get toolsNotesTitle;

  /// No description provided for @toolsNotesDesc.
  ///
  /// In zh, this message translates to:
  /// **'即时记录想法'**
  String get toolsNotesDesc;

  /// No description provided for @toolsTranslatorTitle.
  ///
  /// In zh, this message translates to:
  /// **'翻译器'**
  String get toolsTranslatorTitle;

  /// No description provided for @toolsTranslatorDesc.
  ///
  /// In zh, this message translates to:
  /// **'多语言翻译'**
  String get toolsTranslatorDesc;

  /// No description provided for @toolsFlashCapsuleTitle.
  ///
  /// In zh, this message translates to:
  /// **'闪电胶囊'**
  String get toolsFlashCapsuleTitle;

  /// No description provided for @toolsFlashCapsuleDesc.
  ///
  /// In zh, this message translates to:
  /// **'快速学习胶囊'**
  String get toolsFlashCapsuleDesc;

  /// No description provided for @toolsFocusStatsTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注统计'**
  String get toolsFocusStatsTitle;

  /// No description provided for @toolsFocusStatsDesc.
  ///
  /// In zh, this message translates to:
  /// **'追踪你的专注会话'**
  String get toolsFocusStatsDesc;

  /// No description provided for @toolsVocabularyLookupTitle.
  ///
  /// In zh, this message translates to:
  /// **'词汇查询'**
  String get toolsVocabularyLookupTitle;

  /// No description provided for @toolsVocabularyLookupDesc.
  ///
  /// In zh, this message translates to:
  /// **'查询单词定义'**
  String get toolsVocabularyLookupDesc;

  /// No description provided for @toolsWordbookTitle.
  ///
  /// In zh, this message translates to:
  /// **'单词本'**
  String get toolsWordbookTitle;

  /// No description provided for @toolsWordbookDesc.
  ///
  /// In zh, this message translates to:
  /// **'你的个人词汇库'**
  String get toolsWordbookDesc;

  /// No description provided for @toolsBreathingTitle.
  ///
  /// In zh, this message translates to:
  /// **'呼吸练习'**
  String get toolsBreathingTitle;

  /// No description provided for @toolsBreathingDesc.
  ///
  /// In zh, this message translates to:
  /// **'引导式呼吸放松'**
  String get toolsBreathingDesc;

  /// No description provided for @toolsDocumentCleanerTitle.
  ///
  /// In zh, this message translates to:
  /// **'文档清理'**
  String get toolsDocumentCleanerTitle;

  /// No description provided for @toolsDocumentCleanerDesc.
  ///
  /// In zh, this message translates to:
  /// **'清理和格式化文档'**
  String get toolsDocumentCleanerDesc;

  /// No description provided for @toolsPatternListTitle.
  ///
  /// In zh, this message translates to:
  /// **'模式列表'**
  String get toolsPatternListTitle;

  /// No description provided for @toolsPatternListDesc.
  ///
  /// In zh, this message translates to:
  /// **'查看学习模式'**
  String get toolsPatternListDesc;

  /// No description provided for @toolsCuriosityCapsuleTitle.
  ///
  /// In zh, this message translates to:
  /// **'好奇心胶囊'**
  String get toolsCuriosityCapsuleTitle;

  /// No description provided for @toolsCuriosityCapsuleDesc.
  ///
  /// In zh, this message translates to:
  /// **'AI生成的好奇心内容'**
  String get toolsCuriosityCapsuleDesc;

  /// No description provided for @toolsCognitiveHubTitle.
  ///
  /// In zh, this message translates to:
  /// **'认知工具'**
  String get toolsCognitiveHubTitle;

  /// No description provided for @toolsCognitiveHubDesc.
  ///
  /// In zh, this message translates to:
  /// **'探索认知工具'**
  String get toolsCognitiveHubDesc;

  /// No description provided for @toolsSearchPlaceholder.
  ///
  /// In zh, this message translates to:
  /// **'搜索工具...'**
  String get toolsSearchPlaceholder;

  /// No description provided for @toolsFocusModeTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注模式'**
  String get toolsFocusModeTitle;

  /// No description provided for @toolsFocusModeDesc.
  ///
  /// In zh, this message translates to:
  /// **'进入任务专注主界面'**
  String get toolsFocusModeDesc;

  /// No description provided for @toolsPomodoroTitle.
  ///
  /// In zh, this message translates to:
  /// **'番茄钟'**
  String get toolsPomodoroTitle;

  /// No description provided for @toolsPomodoroDesc.
  ///
  /// In zh, this message translates to:
  /// **'25分钟工作周期'**
  String get toolsPomodoroDesc;

  /// No description provided for @toolsErrorBookTitle.
  ///
  /// In zh, this message translates to:
  /// **'错题本'**
  String get toolsErrorBookTitle;

  /// No description provided for @toolsErrorBookDesc.
  ///
  /// In zh, this message translates to:
  /// **'浏览与管理错题记录'**
  String get toolsErrorBookDesc;

  /// No description provided for @toolsReviewPlanTitle.
  ///
  /// In zh, this message translates to:
  /// **'复习计划'**
  String get toolsReviewPlanTitle;

  /// No description provided for @toolsReviewPlanDesc.
  ///
  /// In zh, this message translates to:
  /// **'进入今日复习计划页'**
  String get toolsReviewPlanDesc;

  /// No description provided for @toolsLearningForecastTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习预测'**
  String get toolsLearningForecastTitle;

  /// No description provided for @toolsLearningForecastDesc.
  ///
  /// In zh, this message translates to:
  /// **'查看学习趋势与风险'**
  String get toolsLearningForecastDesc;

  /// No description provided for @toolsCognitivePatternsTitle.
  ///
  /// In zh, this message translates to:
  /// **'认知模式'**
  String get toolsCognitivePatternsTitle;

  /// No description provided for @toolsCognitivePatternsDesc.
  ///
  /// In zh, this message translates to:
  /// **'查看行为定式与认知洞察'**
  String get toolsCognitivePatternsDesc;

  /// No description provided for @chatModeStandard.
  ///
  /// In zh, this message translates to:
  /// **'标准对话'**
  String get chatModeStandard;

  /// No description provided for @chatModeDeep.
  ///
  /// In zh, this message translates to:
  /// **'深度专注'**
  String get chatModeDeep;

  /// No description provided for @chatModeCreative.
  ///
  /// In zh, this message translates to:
  /// **'创意模式'**
  String get chatModeCreative;

  /// No description provided for @chatModeAnalytical.
  ///
  /// In zh, this message translates to:
  /// **'分析模式'**
  String get chatModeAnalytical;

  /// No description provided for @chatModeStandardDesc.
  ///
  /// In zh, this message translates to:
  /// **'标准 AI 对话模式'**
  String get chatModeStandardDesc;

  /// No description provided for @chatModeDeepAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'深度分析'**
  String get chatModeDeepAnalysis;

  /// No description provided for @chatModeDeepAnalysisDesc.
  ///
  /// In zh, this message translates to:
  /// **'多专家协作分析'**
  String get chatModeDeepAnalysisDesc;

  /// No description provided for @chatModeStudyPlan.
  ///
  /// In zh, this message translates to:
  /// **'学习计划'**
  String get chatModeStudyPlan;

  /// No description provided for @chatModeStudyPlanDesc.
  ///
  /// In zh, this message translates to:
  /// **'任务拆解与学习计划'**
  String get chatModeStudyPlanDesc;

  /// No description provided for @chatModeErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'错误诊断'**
  String get chatModeErrorDiagnosis;

  /// No description provided for @chatModeErrorDiagnosisDesc.
  ///
  /// In zh, this message translates to:
  /// **'错误诊断与分析闭环'**
  String get chatModeErrorDiagnosisDesc;

  /// No description provided for @chatModeExpertAuto.
  ///
  /// In zh, this message translates to:
  /// **'专家自动'**
  String get chatModeExpertAuto;

  /// No description provided for @chatModeExpertAutoDesc.
  ///
  /// In zh, this message translates to:
  /// **'自动选择最佳专家'**
  String get chatModeExpertAutoDesc;

  /// No description provided for @chatModeExpertDirect.
  ///
  /// In zh, this message translates to:
  /// **'专家直达'**
  String get chatModeExpertDirect;

  /// No description provided for @chatModeExpertDirectDesc.
  ///
  /// In zh, this message translates to:
  /// **'直连专家咨询'**
  String get chatModeExpertDirectDesc;

  /// No description provided for @chatModeSelectorTitle.
  ///
  /// In zh, this message translates to:
  /// **'选择 AI 协作模式'**
  String get chatModeSelectorTitle;

  /// No description provided for @chatModeActivated.
  ///
  /// In zh, this message translates to:
  /// **'{mode} 模式已激活'**
  String chatModeActivated(Object mode);

  /// No description provided for @chatPlanContextSwitched.
  ///
  /// In zh, this message translates to:
  /// **'已切换到计划上下文'**
  String get chatPlanContextSwitched;

  /// No description provided for @chatPlanSwitchTitle.
  ///
  /// In zh, this message translates to:
  /// **'切换计划上下文'**
  String get chatPlanSwitchTitle;

  /// No description provided for @chatPlanSwitchMessage.
  ///
  /// In zh, this message translates to:
  /// **'切换计划将清空当前对话记录，是否继续？'**
  String get chatPlanSwitchMessage;

  /// No description provided for @chatPlanSwitchUnsavedCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条未保存的消息'**
  String chatPlanSwitchUnsavedCount(Object count);

  /// No description provided for @chatReconnecting.
  ///
  /// In zh, this message translates to:
  /// **'正在重新连接...'**
  String get chatReconnecting;

  /// No description provided for @chatReconnected.
  ///
  /// In zh, this message translates to:
  /// **'已重新连接'**
  String get chatReconnected;

  /// No description provided for @chatConnectionFailed.
  ///
  /// In zh, this message translates to:
  /// **'连接失败'**
  String get chatConnectionFailed;

  /// No description provided for @aiCollabModeTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 协作'**
  String get aiCollabModeTitle;

  /// No description provided for @switchAgentModeSemantics.
  ///
  /// In zh, this message translates to:
  /// **'切换 Agent 模式'**
  String get switchAgentModeSemantics;

  /// No description provided for @chatDagLayerProgress.
  ///
  /// In zh, this message translates to:
  /// **'第 {current}/{total} 层'**
  String chatDagLayerProgress(Object current, Object total);

  /// No description provided for @chatDagProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理依赖关系中...'**
  String get chatDagProcessing;

  /// No description provided for @chatDagCompleted.
  ///
  /// In zh, this message translates to:
  /// **'分析完成'**
  String get chatDagCompleted;

  /// No description provided for @chatInputPlaceholder.
  ///
  /// In zh, this message translates to:
  /// **'输入消息...'**
  String get chatInputPlaceholder;

  /// No description provided for @chatInputAttachment.
  ///
  /// In zh, this message translates to:
  /// **'附件'**
  String get chatInputAttachment;

  /// No description provided for @chatInputVoice.
  ///
  /// In zh, this message translates to:
  /// **'语音'**
  String get chatInputVoice;

  /// No description provided for @chatInputShare.
  ///
  /// In zh, this message translates to:
  /// **'分享'**
  String get chatInputShare;

  /// No description provided for @chatInputTapToShare.
  ///
  /// In zh, this message translates to:
  /// **'点击选择分享内容'**
  String get chatInputTapToShare;

  /// No description provided for @chatVoiceInput.
  ///
  /// In zh, this message translates to:
  /// **'语音输入'**
  String get chatVoiceInput;

  /// No description provided for @chatAttachment.
  ///
  /// In zh, this message translates to:
  /// **'附件'**
  String get chatAttachment;

  /// No description provided for @chatEmoji.
  ///
  /// In zh, this message translates to:
  /// **'表情'**
  String get chatEmoji;

  /// No description provided for @chatSend.
  ///
  /// In zh, this message translates to:
  /// **'发送'**
  String get chatSend;

  /// No description provided for @chatTyping.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在输入...'**
  String get chatTyping;

  /// No description provided for @chatOnline.
  ///
  /// In zh, this message translates to:
  /// **'在线'**
  String get chatOnline;

  /// No description provided for @chatOffline.
  ///
  /// In zh, this message translates to:
  /// **'离线'**
  String get chatOffline;

  /// No description provided for @chatReconnect.
  ///
  /// In zh, this message translates to:
  /// **'重新连接'**
  String get chatReconnect;

  /// No description provided for @chatClearHistory.
  ///
  /// In zh, this message translates to:
  /// **'清空历史'**
  String get chatClearHistory;

  /// No description provided for @chatExportChat.
  ///
  /// In zh, this message translates to:
  /// **'导出对话'**
  String get chatExportChat;

  /// No description provided for @chatNewChat.
  ///
  /// In zh, this message translates to:
  /// **'新对话'**
  String get chatNewChat;

  /// No description provided for @chatHistory.
  ///
  /// In zh, this message translates to:
  /// **'对话历史'**
  String get chatHistory;

  /// No description provided for @chatNoHistory.
  ///
  /// In zh, this message translates to:
  /// **'暂无对话历史'**
  String get chatNoHistory;

  /// No description provided for @chatDeleteConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定删除此对话？'**
  String get chatDeleteConfirm;

  /// No description provided for @chatDeleted.
  ///
  /// In zh, this message translates to:
  /// **'对话已删除'**
  String get chatDeleted;

  /// No description provided for @chatCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制到剪贴板'**
  String get chatCopied;

  /// No description provided for @chatRegenerate.
  ///
  /// In zh, this message translates to:
  /// **'重新生成'**
  String get chatRegenerate;

  /// No description provided for @chatCopy.
  ///
  /// In zh, this message translates to:
  /// **'复制'**
  String get chatCopy;

  /// No description provided for @chatShare.
  ///
  /// In zh, this message translates to:
  /// **'分享'**
  String get chatShare;

  /// No description provided for @chatFeedback.
  ///
  /// In zh, this message translates to:
  /// **'反馈'**
  String get chatFeedback;

  /// No description provided for @chatReportIssue.
  ///
  /// In zh, this message translates to:
  /// **'报告问题'**
  String get chatReportIssue;

  /// No description provided for @chatMessageTooLong.
  ///
  /// In zh, this message translates to:
  /// **'消息过长'**
  String get chatMessageTooLong;

  /// No description provided for @chatEmptyMessage.
  ///
  /// In zh, this message translates to:
  /// **'不能发送空消息'**
  String get chatEmptyMessage;

  /// No description provided for @chatConnectionLost.
  ///
  /// In zh, this message translates to:
  /// **'连接断开，正在重试...'**
  String get chatConnectionLost;

  /// No description provided for @chatConnectionRestored.
  ///
  /// In zh, this message translates to:
  /// **'连接已恢复'**
  String get chatConnectionRestored;

  /// No description provided for @chatWelcome.
  ///
  /// In zh, this message translates to:
  /// **'你好！今天我能帮你什么？'**
  String get chatWelcome;

  /// No description provided for @chatWelcomeSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'今天想做点什么？'**
  String get chatWelcomeSubtitle;

  /// No description provided for @chatSuggestion1.
  ///
  /// In zh, this message translates to:
  /// **'帮我规划学习'**
  String get chatSuggestion1;

  /// No description provided for @chatSuggestion2.
  ///
  /// In zh, this message translates to:
  /// **'解释一个概念'**
  String get chatSuggestion2;

  /// No description provided for @chatSuggestion3.
  ///
  /// In zh, this message translates to:
  /// **'查看我的进度'**
  String get chatSuggestion3;

  /// No description provided for @chatSuggestion4.
  ///
  /// In zh, this message translates to:
  /// **'推荐学习资源'**
  String get chatSuggestion4;

  /// No description provided for @chatAgentSwitched.
  ///
  /// In zh, this message translates to:
  /// **'已切换到 {agent}'**
  String chatAgentSwitched(Object agent);

  /// No description provided for @achievementTitle.
  ///
  /// In zh, this message translates to:
  /// **'成就'**
  String get achievementTitle;

  /// No description provided for @achievementUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'成就解锁！'**
  String get achievementUnlocked;

  /// No description provided for @achievementLocked.
  ///
  /// In zh, this message translates to:
  /// **'未解锁'**
  String get achievementLocked;

  /// No description provided for @achievementProgress.
  ///
  /// In zh, this message translates to:
  /// **'进度'**
  String get achievementProgress;

  /// No description provided for @achievementRarityCommon.
  ///
  /// In zh, this message translates to:
  /// **'普通'**
  String get achievementRarityCommon;

  /// No description provided for @achievementRarityRare.
  ///
  /// In zh, this message translates to:
  /// **'稀有'**
  String get achievementRarityRare;

  /// No description provided for @achievementRarityEpic.
  ///
  /// In zh, this message translates to:
  /// **'史诗'**
  String get achievementRarityEpic;

  /// No description provided for @achievementRarityLegendary.
  ///
  /// In zh, this message translates to:
  /// **'传说'**
  String get achievementRarityLegendary;

  /// No description provided for @achievementTypeStreak.
  ///
  /// In zh, this message translates to:
  /// **'连续'**
  String get achievementTypeStreak;

  /// No description provided for @achievementTypeMilestone.
  ///
  /// In zh, this message translates to:
  /// **'里程碑'**
  String get achievementTypeMilestone;

  /// No description provided for @achievementTypeChallenge.
  ///
  /// In zh, this message translates to:
  /// **'挑战'**
  String get achievementTypeChallenge;

  /// No description provided for @achievementTypeHidden.
  ///
  /// In zh, this message translates to:
  /// **'隐藏'**
  String get achievementTypeHidden;

  /// No description provided for @achievementTypeSpecial.
  ///
  /// In zh, this message translates to:
  /// **'特殊'**
  String get achievementTypeSpecial;

  /// No description provided for @achievementPoints.
  ///
  /// In zh, this message translates to:
  /// **'{points} 积分'**
  String achievementPoints(Object points);

  /// No description provided for @achievementEarned.
  ///
  /// In zh, this message translates to:
  /// **'获得于 {date}'**
  String achievementEarned(Object date);

  /// No description provided for @achievementClose.
  ///
  /// In zh, this message translates to:
  /// **'关闭'**
  String get achievementClose;

  /// No description provided for @achievementShare.
  ///
  /// In zh, this message translates to:
  /// **'分享'**
  String get achievementShare;

  /// No description provided for @achievementViewAll.
  ///
  /// In zh, this message translates to:
  /// **'查看全部'**
  String get achievementViewAll;

  /// No description provided for @achievementNoUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'还没有解锁成就'**
  String get achievementNoUnlocked;

  /// No description provided for @achievementKeepGoing.
  ///
  /// In zh, this message translates to:
  /// **'继续努力解锁更多成就！'**
  String get achievementKeepGoing;

  /// No description provided for @achievementStatsTotal.
  ///
  /// In zh, this message translates to:
  /// **'总数'**
  String get achievementStatsTotal;

  /// No description provided for @achievementStatsUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'已解锁'**
  String get achievementStatsUnlocked;

  /// No description provided for @achievementStatsPoints.
  ///
  /// In zh, this message translates to:
  /// **'积分'**
  String get achievementStatsPoints;

  /// No description provided for @achievementStatsStreak.
  ///
  /// In zh, this message translates to:
  /// **'连续天数'**
  String get achievementStatsStreak;

  /// No description provided for @achievementNew.
  ///
  /// In zh, this message translates to:
  /// **'新！'**
  String get achievementNew;

  /// No description provided for @achievementSearch.
  ///
  /// In zh, this message translates to:
  /// **'搜索成就'**
  String get achievementSearch;

  /// No description provided for @achievementFilter.
  ///
  /// In zh, this message translates to:
  /// **'筛选'**
  String get achievementFilter;

  /// No description provided for @achievementFilterActive.
  ///
  /// In zh, this message translates to:
  /// **'筛选中'**
  String get achievementFilterActive;

  /// No description provided for @achievementAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get achievementAll;

  /// No description provided for @achievementStatusUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'已解锁'**
  String get achievementStatusUnlocked;

  /// No description provided for @achievementStatusLocked.
  ///
  /// In zh, this message translates to:
  /// **'未解锁'**
  String get achievementStatusLocked;

  /// No description provided for @achievementStatusInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get achievementStatusInProgress;

  /// No description provided for @achievementCategoryStreak.
  ///
  /// In zh, this message translates to:
  /// **'连胜'**
  String get achievementCategoryStreak;

  /// No description provided for @achievementCategoryMilestone.
  ///
  /// In zh, this message translates to:
  /// **'里程碑'**
  String get achievementCategoryMilestone;

  /// No description provided for @achievementCategoryMastery.
  ///
  /// In zh, this message translates to:
  /// **'精通'**
  String get achievementCategoryMastery;

  /// No description provided for @achievementCategoryExploration.
  ///
  /// In zh, this message translates to:
  /// **'探索'**
  String get achievementCategoryExploration;

  /// No description provided for @achievementCategoryTask.
  ///
  /// In zh, this message translates to:
  /// **'任务'**
  String get achievementCategoryTask;

  /// No description provided for @achievementNoMatch.
  ///
  /// In zh, this message translates to:
  /// **'没有找到匹配的成就'**
  String get achievementNoMatch;

  /// No description provided for @achievementAdjustFilter.
  ///
  /// In zh, this message translates to:
  /// **'试试调整筛选条件'**
  String get achievementAdjustFilter;

  /// No description provided for @achievementFilterSheet.
  ///
  /// In zh, this message translates to:
  /// **'筛选成就'**
  String get achievementFilterSheet;

  /// No description provided for @achievementRarity.
  ///
  /// In zh, this message translates to:
  /// **'稀有度'**
  String get achievementRarity;

  /// No description provided for @achievementStatus.
  ///
  /// In zh, this message translates to:
  /// **'状态'**
  String get achievementStatus;

  /// No description provided for @achievementApplyFilter.
  ///
  /// In zh, this message translates to:
  /// **'应用筛选'**
  String get achievementApplyFilter;

  /// No description provided for @achievementDescription.
  ///
  /// In zh, this message translates to:
  /// **'描述'**
  String get achievementDescription;

  /// No description provided for @achievementNoDescription.
  ///
  /// In zh, this message translates to:
  /// **'暂无描述'**
  String get achievementNoDescription;

  /// No description provided for @achievementPrerequisites.
  ///
  /// In zh, this message translates to:
  /// **'前置成就'**
  String get achievementPrerequisites;

  /// No description provided for @achievementPrerequisitesHint.
  ///
  /// In zh, this message translates to:
  /// **'需要先完成以下成就：'**
  String get achievementPrerequisitesHint;

  /// No description provided for @achievementRewards.
  ///
  /// In zh, this message translates to:
  /// **'奖励'**
  String get achievementRewards;

  /// No description provided for @achievementUnlockRewards.
  ///
  /// In zh, this message translates to:
  /// **'解锁奖励'**
  String get achievementUnlockRewards;

  /// No description provided for @achievementRewardPhotons.
  ///
  /// In zh, this message translates to:
  /// **'{count} 光子'**
  String achievementRewardPhotons(Object count);

  /// No description provided for @achievementRewardTitle.
  ///
  /// In zh, this message translates to:
  /// **'称号'**
  String get achievementRewardTitle;

  /// No description provided for @achievementRewardSkin.
  ///
  /// In zh, this message translates to:
  /// **'星系皮肤'**
  String get achievementRewardSkin;

  /// No description provided for @achievementRewardXp.
  ///
  /// In zh, this message translates to:
  /// **'{count} 经验'**
  String achievementRewardXp(Object count);

  /// No description provided for @achievementRewardMystery.
  ///
  /// In zh, this message translates to:
  /// **'神秘奖励'**
  String get achievementRewardMystery;

  /// No description provided for @achievementStatType.
  ///
  /// In zh, this message translates to:
  /// **'类型'**
  String get achievementStatType;

  /// No description provided for @achievementCategory.
  ///
  /// In zh, this message translates to:
  /// **'分类'**
  String get achievementCategory;

  /// No description provided for @achievementUnlockedAt.
  ///
  /// In zh, this message translates to:
  /// **'解锁时间'**
  String get achievementUnlockedAt;

  /// No description provided for @achievementShareCount.
  ///
  /// In zh, this message translates to:
  /// **'分享次数'**
  String get achievementShareCount;

  /// No description provided for @achievementUnlockRank.
  ///
  /// In zh, this message translates to:
  /// **'解锁排名'**
  String get achievementUnlockRank;

  /// No description provided for @achievementFirstUnlocker.
  ///
  /// In zh, this message translates to:
  /// **'首位解锁者'**
  String get achievementFirstUnlocker;

  /// No description provided for @achievementNotFound.
  ///
  /// In zh, this message translates to:
  /// **'成就未找到'**
  String get achievementNotFound;

  /// No description provided for @achievementShareLocked.
  ///
  /// In zh, this message translates to:
  /// **'解锁后才可以分享这个成就'**
  String get achievementShareLocked;

  /// No description provided for @achievementCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get achievementCompletionRate;

  /// No description provided for @achievementTotalLabel.
  ///
  /// In zh, this message translates to:
  /// **'总成就'**
  String get achievementTotalLabel;

  /// No description provided for @achievementPhotons.
  ///
  /// In zh, this message translates to:
  /// **'光子'**
  String get achievementPhotons;

  /// No description provided for @achievementOverallProgress.
  ///
  /// In zh, this message translates to:
  /// **'总体进度'**
  String get achievementOverallProgress;

  /// No description provided for @achievementRarityDistribution.
  ///
  /// In zh, this message translates to:
  /// **'稀有度分布'**
  String get achievementRarityDistribution;

  /// No description provided for @achievementHiddenCount.
  ///
  /// In zh, this message translates to:
  /// **'隐藏: {count}'**
  String achievementHiddenCount(Object count);

  /// No description provided for @achievementTypeMastery.
  ///
  /// In zh, this message translates to:
  /// **'精通'**
  String get achievementTypeMastery;

  /// No description provided for @achievementTypeTaskComplete.
  ///
  /// In zh, this message translates to:
  /// **'任务'**
  String get achievementTypeTaskComplete;

  /// No description provided for @achievementTypeNodeExplore.
  ///
  /// In zh, this message translates to:
  /// **'探索'**
  String get achievementTypeNodeExplore;

  /// No description provided for @achievementTypeStudyTime.
  ///
  /// In zh, this message translates to:
  /// **'学习时长'**
  String get achievementTypeStudyTime;

  /// No description provided for @achievementTypeSocial.
  ///
  /// In zh, this message translates to:
  /// **'社交'**
  String get achievementTypeSocial;

  /// No description provided for @achievementTypeContract.
  ///
  /// In zh, this message translates to:
  /// **'契约'**
  String get achievementTypeContract;

  /// No description provided for @achievementTypeSprint.
  ///
  /// In zh, this message translates to:
  /// **'冲刺'**
  String get achievementTypeSprint;

  /// No description provided for @achievementAlmostThere.
  ///
  /// In zh, this message translates to:
  /// **'即将解锁'**
  String get achievementAlmostThere;

  /// No description provided for @achievementNeedMore.
  ///
  /// In zh, this message translates to:
  /// **'再{action}即可解锁'**
  String achievementNeedMore(Object action);

  /// No description provided for @achievementCompleteTasks.
  ///
  /// In zh, this message translates to:
  /// **'完成{count}个任务'**
  String achievementCompleteTasks(Object count);

  /// No description provided for @achievementUnlockNodes.
  ///
  /// In zh, this message translates to:
  /// **'解锁{count}个知识点'**
  String achievementUnlockNodes(Object count);

  /// No description provided for @achievementChatCount.
  ///
  /// In zh, this message translates to:
  /// **'聊天{count}次'**
  String achievementChatCount(Object count);

  /// No description provided for @achievementCheckinDays.
  ///
  /// In zh, this message translates to:
  /// **'连续签到{count}天'**
  String achievementCheckinDays(Object count);

  /// No description provided for @achievementCreatePlans.
  ///
  /// In zh, this message translates to:
  /// **'创建{count}个计划'**
  String achievementCreatePlans(Object count);

  /// No description provided for @achievementProgressGeneric.
  ///
  /// In zh, this message translates to:
  /// **'进度{count}%'**
  String achievementProgressGeneric(Object count);

  /// No description provided for @achievementLimitedTitle.
  ///
  /// In zh, this message translates to:
  /// **'限时活动'**
  String get achievementLimitedTitle;

  /// No description provided for @achievementLimitedSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'活动期间可获得'**
  String get achievementLimitedSubtitle;

  /// No description provided for @achievementLimitedTime.
  ///
  /// In zh, this message translates to:
  /// **'限时'**
  String get achievementLimitedTime;

  /// No description provided for @achievementEventWindow.
  ///
  /// In zh, this message translates to:
  /// **'活动时间'**
  String get achievementEventWindow;

  /// No description provided for @achievementEventStatusUpcoming.
  ///
  /// In zh, this message translates to:
  /// **'即将开始'**
  String get achievementEventStatusUpcoming;

  /// No description provided for @achievementEventStatusLive.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get achievementEventStatusLive;

  /// No description provided for @achievementEventStatusEnded.
  ///
  /// In zh, this message translates to:
  /// **'已结束'**
  String get achievementEventStatusEnded;

  /// No description provided for @achievementEventStartsAt.
  ///
  /// In zh, this message translates to:
  /// **'开始于{time}'**
  String achievementEventStartsAt(String time);

  /// No description provided for @achievementEventEndsAt.
  ///
  /// In zh, this message translates to:
  /// **'结束于{time}'**
  String achievementEventEndsAt(String time);

  /// No description provided for @achievementEventEndsIn.
  ///
  /// In zh, this message translates to:
  /// **'将于{time}结束'**
  String achievementEventEndsIn(String time);

  /// No description provided for @achievementEventEnded.
  ///
  /// In zh, this message translates to:
  /// **'活动已结束'**
  String get achievementEventEnded;

  /// No description provided for @achievementRewardVisualElement.
  ///
  /// In zh, this message translates to:
  /// **'视觉元素'**
  String get achievementRewardVisualElement;

  /// No description provided for @achievementUnlockToEquip.
  ///
  /// In zh, this message translates to:
  /// **'解锁后可装备'**
  String get achievementUnlockToEquip;

  /// No description provided for @achievementEquipAction.
  ///
  /// In zh, this message translates to:
  /// **'装备'**
  String get achievementEquipAction;

  /// No description provided for @achievementEquipped.
  ///
  /// In zh, this message translates to:
  /// **'已装备'**
  String get achievementEquipped;

  /// No description provided for @achievementMapTitle.
  ///
  /// In zh, this message translates to:
  /// **'成就地图'**
  String get achievementMapTitle;

  /// No description provided for @achievementMapSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'探索成就路径'**
  String get achievementMapSubtitle;

  /// No description provided for @achievementMapEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无成就节点'**
  String get achievementMapEmpty;

  /// No description provided for @contractEntryTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习契约'**
  String get contractEntryTitle;

  /// No description provided for @contractEntrySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'创建学习挑战'**
  String get contractEntrySubtitle;

  /// No description provided for @contractTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习契约'**
  String get contractTitle;

  /// No description provided for @contractCreateTitle.
  ///
  /// In zh, this message translates to:
  /// **'创建契约'**
  String get contractCreateTitle;

  /// No description provided for @contractCreateSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'设定连续目标并投入光子'**
  String get contractCreateSubtitle;

  /// No description provided for @contractTargetMinutes.
  ///
  /// In zh, this message translates to:
  /// **'每日分钟'**
  String get contractTargetMinutes;

  /// No description provided for @contractTargetDays.
  ///
  /// In zh, this message translates to:
  /// **'目标天数'**
  String get contractTargetDays;

  /// No description provided for @contractPhotonStake.
  ///
  /// In zh, this message translates to:
  /// **'投入光子'**
  String get contractPhotonStake;

  /// No description provided for @contractCreateAction.
  ///
  /// In zh, this message translates to:
  /// **'创建契约'**
  String get contractCreateAction;

  /// No description provided for @contractActiveTitle.
  ///
  /// In zh, this message translates to:
  /// **'当前契约'**
  String get contractActiveTitle;

  /// No description provided for @contractProgressLabel.
  ///
  /// In zh, this message translates to:
  /// **'已完成{current}/{target}天'**
  String contractProgressLabel(int current, int target);

  /// No description provided for @contractDailyTarget.
  ///
  /// In zh, this message translates to:
  /// **'每日目标'**
  String get contractDailyTarget;

  /// No description provided for @contractMinutesTarget.
  ///
  /// In zh, this message translates to:
  /// **'{current}/{target}分钟'**
  String contractMinutesTarget(int current, int target);

  /// No description provided for @contractEndsAt.
  ///
  /// In zh, this message translates to:
  /// **'结束时间'**
  String get contractEndsAt;

  /// No description provided for @contractCancelAction.
  ///
  /// In zh, this message translates to:
  /// **'取消契约'**
  String get contractCancelAction;

  /// No description provided for @contractInputInvalid.
  ///
  /// In zh, this message translates to:
  /// **'请输入有效的契约数值'**
  String get contractInputInvalid;

  /// No description provided for @contractCreateFailed.
  ///
  /// In zh, this message translates to:
  /// **'创建契约失败'**
  String get contractCreateFailed;

  /// No description provided for @contractCreateSuccess.
  ///
  /// In zh, this message translates to:
  /// **'契约创建成功'**
  String get contractCreateSuccess;

  /// No description provided for @contractCancelSuccess.
  ///
  /// In zh, this message translates to:
  /// **'契约已取消'**
  String get contractCancelSuccess;

  /// No description provided for @contractCancelFailed.
  ///
  /// In zh, this message translates to:
  /// **'取消契约失败'**
  String get contractCancelFailed;

  /// No description provided for @contractCountdown.
  ///
  /// In zh, this message translates to:
  /// **'倒计时'**
  String get contractCountdown;

  /// No description provided for @contractDaysRemaining.
  ///
  /// In zh, this message translates to:
  /// **'还剩{days}天'**
  String contractDaysRemaining(int days);

  /// No description provided for @contractDeadlineReached.
  ///
  /// In zh, this message translates to:
  /// **'已到截止日期'**
  String get contractDeadlineReached;

  /// No description provided for @contractRewardMultiplier.
  ///
  /// In zh, this message translates to:
  /// **'奖励倍率'**
  String get contractRewardMultiplier;

  /// No description provided for @contractCreatedCelebration.
  ///
  /// In zh, this message translates to:
  /// **'契约创建成功！'**
  String get contractCreatedCelebration;

  /// No description provided for @streakCurrentLabel.
  ///
  /// In zh, this message translates to:
  /// **'当前连胜'**
  String get streakCurrentLabel;

  /// No description provided for @streakBestRecord.
  ///
  /// In zh, this message translates to:
  /// **'最高记录'**
  String get streakBestRecord;

  /// No description provided for @streakTotalCheckin.
  ///
  /// In zh, this message translates to:
  /// **'总签到'**
  String get streakTotalCheckin;

  /// No description provided for @streakFreezeUsed.
  ///
  /// In zh, this message translates to:
  /// **'冻结使用'**
  String get streakFreezeUsed;

  /// No description provided for @streakCalendarTitle.
  ///
  /// In zh, this message translates to:
  /// **'连胜日历'**
  String get streakCalendarTitle;

  /// No description provided for @streakCalendarRange.
  ///
  /// In zh, this message translates to:
  /// **'最近{days}天'**
  String streakCalendarRange(int days);

  /// No description provided for @streakHistoryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无连胜记录'**
  String get streakHistoryEmpty;

  /// No description provided for @streakStatusActive.
  ///
  /// In zh, this message translates to:
  /// **'学习日'**
  String get streakStatusActive;

  /// No description provided for @streakStatusFrozen.
  ///
  /// In zh, this message translates to:
  /// **'冻结'**
  String get streakStatusFrozen;

  /// No description provided for @streakStatusMissed.
  ///
  /// In zh, this message translates to:
  /// **'中断'**
  String get streakStatusMissed;

  /// No description provided for @streakRiskNoFreeze.
  ///
  /// In zh, this message translates to:
  /// **'冻结卡已用完，断签将中断连胜。'**
  String get streakRiskNoFreeze;

  /// No description provided for @streakRiskLowFreeze.
  ///
  /// In zh, this message translates to:
  /// **'仅剩1次冻结卡，建议及时补充。'**
  String get streakRiskLowFreeze;

  /// No description provided for @streakShopTitle.
  ///
  /// In zh, this message translates to:
  /// **'需要冻结卡保护？'**
  String get streakShopTitle;

  /// No description provided for @streakShopSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'前往光子商城获取补给'**
  String get streakShopSubtitle;

  /// No description provided for @streakShopAction.
  ///
  /// In zh, this message translates to:
  /// **'打开商城'**
  String get streakShopAction;

  /// No description provided for @streakDetails.
  ///
  /// In zh, this message translates to:
  /// **'连胜详情'**
  String get streakDetails;

  /// No description provided for @dashboardCustomizeCards.
  ///
  /// In zh, this message translates to:
  /// **'可定制卡片区'**
  String get dashboardCustomizeCards;

  /// No description provided for @dashboardEmptyHint.
  ///
  /// In zh, this message translates to:
  /// **'至少保留一张卡片，编辑后会立即保存到本地配置。'**
  String get dashboardEmptyHint;

  /// No description provided for @achievementViewStreakStatus.
  ///
  /// In zh, this message translates to:
  /// **'查看成就与连续学习状态'**
  String get achievementViewStreakStatus;

  /// No description provided for @taskStatusPending.
  ///
  /// In zh, this message translates to:
  /// **'待处理'**
  String get taskStatusPending;

  /// No description provided for @taskStatusInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get taskStatusInProgress;

  /// No description provided for @taskStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get taskStatusCompleted;

  /// No description provided for @taskStatusAbandoned.
  ///
  /// In zh, this message translates to:
  /// **'已放弃'**
  String get taskStatusAbandoned;

  /// No description provided for @taskStatusPaused.
  ///
  /// In zh, this message translates to:
  /// **'已暂停'**
  String get taskStatusPaused;

  /// No description provided for @taskActionStart.
  ///
  /// In zh, this message translates to:
  /// **'开始'**
  String get taskActionStart;

  /// No description provided for @taskActionPause.
  ///
  /// In zh, this message translates to:
  /// **'暂停'**
  String get taskActionPause;

  /// No description provided for @taskActionResume.
  ///
  /// In zh, this message translates to:
  /// **'继续'**
  String get taskActionResume;

  /// No description provided for @taskActionComplete.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get taskActionComplete;

  /// No description provided for @taskActionAbandon.
  ///
  /// In zh, this message translates to:
  /// **'放弃'**
  String get taskActionAbandon;

  /// No description provided for @taskActionEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑'**
  String get taskActionEdit;

  /// No description provided for @taskActionDelete.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get taskActionDelete;

  /// No description provided for @taskPriorityHigh.
  ///
  /// In zh, this message translates to:
  /// **'高优先级'**
  String get taskPriorityHigh;

  /// No description provided for @taskPriorityMedium.
  ///
  /// In zh, this message translates to:
  /// **'中优先级'**
  String get taskPriorityMedium;

  /// No description provided for @taskPriorityLow.
  ///
  /// In zh, this message translates to:
  /// **'低优先级'**
  String get taskPriorityLow;

  /// No description provided for @taskNoTasks.
  ///
  /// In zh, this message translates to:
  /// **'暂无任务'**
  String get taskNoTasks;

  /// No description provided for @taskAddNew.
  ///
  /// In zh, this message translates to:
  /// **'添加任务'**
  String get taskAddNew;

  /// No description provided for @taskDueDate.
  ///
  /// In zh, this message translates to:
  /// **'截止 {date}'**
  String taskDueDate(Object date);

  /// No description provided for @taskOverdue.
  ///
  /// In zh, this message translates to:
  /// **'已逾期'**
  String get taskOverdue;

  /// No description provided for @taskDueToday.
  ///
  /// In zh, this message translates to:
  /// **'今天截止'**
  String get taskDueToday;

  /// No description provided for @taskDueTomorrow.
  ///
  /// In zh, this message translates to:
  /// **'明天截止'**
  String get taskDueTomorrow;

  /// No description provided for @taskDueThisWeek.
  ///
  /// In zh, this message translates to:
  /// **'本周截止'**
  String get taskDueThisWeek;

  /// No description provided for @taskCategoryWork.
  ///
  /// In zh, this message translates to:
  /// **'工作'**
  String get taskCategoryWork;

  /// No description provided for @taskCategoryStudy.
  ///
  /// In zh, this message translates to:
  /// **'学习'**
  String get taskCategoryStudy;

  /// No description provided for @taskCategoryPersonal.
  ///
  /// In zh, this message translates to:
  /// **'个人'**
  String get taskCategoryPersonal;

  /// No description provided for @taskCategoryHealth.
  ///
  /// In zh, this message translates to:
  /// **'健康'**
  String get taskCategoryHealth;

  /// No description provided for @taskCategoryOther.
  ///
  /// In zh, this message translates to:
  /// **'其他'**
  String get taskCategoryOther;

  /// No description provided for @taskFilterAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get taskFilterAll;

  /// No description provided for @taskFilterToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get taskFilterToday;

  /// No description provided for @taskFilterWeek.
  ///
  /// In zh, this message translates to:
  /// **'本周'**
  String get taskFilterWeek;

  /// No description provided for @taskFilterCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get taskFilterCompleted;

  /// No description provided for @taskSortByDate.
  ///
  /// In zh, this message translates to:
  /// **'按日期排序'**
  String get taskSortByDate;

  /// No description provided for @taskSortByPriority.
  ///
  /// In zh, this message translates to:
  /// **'按优先级排序'**
  String get taskSortByPriority;

  /// No description provided for @taskSortByName.
  ///
  /// In zh, this message translates to:
  /// **'按名称排序'**
  String get taskSortByName;

  /// No description provided for @taskCount.
  ///
  /// In zh, this message translates to:
  /// **'{count, plural, =0{无任务} =1{1个任务} other{{count}个任务}}'**
  String taskCount(num count);

  /// No description provided for @focusTimerTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注计时'**
  String get focusTimerTitle;

  /// No description provided for @focusTimerStart.
  ///
  /// In zh, this message translates to:
  /// **'开始专注'**
  String get focusTimerStart;

  /// No description provided for @focusTimerPause.
  ///
  /// In zh, this message translates to:
  /// **'暂停'**
  String get focusTimerPause;

  /// No description provided for @focusTimerResume.
  ///
  /// In zh, this message translates to:
  /// **'继续'**
  String get focusTimerResume;

  /// No description provided for @focusTimerStop.
  ///
  /// In zh, this message translates to:
  /// **'停止'**
  String get focusTimerStop;

  /// No description provided for @focusTimerReset.
  ///
  /// In zh, this message translates to:
  /// **'重置'**
  String get focusTimerReset;

  /// No description provided for @focusTimerComplete.
  ///
  /// In zh, this message translates to:
  /// **'会话完成！'**
  String get focusTimerComplete;

  /// No description provided for @focusTimerRemaining.
  ///
  /// In zh, this message translates to:
  /// **'剩余时间'**
  String get focusTimerRemaining;

  /// No description provided for @focusTimerElapsed.
  ///
  /// In zh, this message translates to:
  /// **'已用时间'**
  String get focusTimerElapsed;

  /// No description provided for @focusTimerSession.
  ///
  /// In zh, this message translates to:
  /// **'第 {current}/{total} 节'**
  String focusTimerSession(Object current, Object total);

  /// No description provided for @focusTimerBreak.
  ///
  /// In zh, this message translates to:
  /// **'休息时间'**
  String get focusTimerBreak;

  /// No description provided for @focusTimerShortBreak.
  ///
  /// In zh, this message translates to:
  /// **'短休息'**
  String get focusTimerShortBreak;

  /// No description provided for @focusTimerLongBreak.
  ///
  /// In zh, this message translates to:
  /// **'长休息'**
  String get focusTimerLongBreak;

  /// No description provided for @focusTimerNextSession.
  ///
  /// In zh, this message translates to:
  /// **'{time}后开始下一节'**
  String focusTimerNextSession(Object time);

  /// No description provided for @focusTimerAutoStart.
  ///
  /// In zh, this message translates to:
  /// **'自动开始下一节'**
  String get focusTimerAutoStart;

  /// No description provided for @focusTimerSound.
  ///
  /// In zh, this message translates to:
  /// **'提示音'**
  String get focusTimerSound;

  /// No description provided for @focusTimerVolume.
  ///
  /// In zh, this message translates to:
  /// **'音量'**
  String get focusTimerVolume;

  /// No description provided for @focusTimerDuration.
  ///
  /// In zh, this message translates to:
  /// **'时长'**
  String get focusTimerDuration;

  /// No description provided for @focusTimerPreset25.
  ///
  /// In zh, this message translates to:
  /// **'25分钟（番茄钟）'**
  String get focusTimerPreset25;

  /// No description provided for @focusTimerPreset45.
  ///
  /// In zh, this message translates to:
  /// **'45分钟（深度专注）'**
  String get focusTimerPreset45;

  /// No description provided for @focusTimerPreset60.
  ///
  /// In zh, this message translates to:
  /// **'60分钟（延长）'**
  String get focusTimerPreset60;

  /// No description provided for @focusTimerCustom.
  ///
  /// In zh, this message translates to:
  /// **'自定义'**
  String get focusTimerCustom;

  /// No description provided for @focusStatsToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get focusStatsToday;

  /// No description provided for @focusStatsWeek.
  ///
  /// In zh, this message translates to:
  /// **'本周'**
  String get focusStatsWeek;

  /// No description provided for @focusStatsMonth.
  ///
  /// In zh, this message translates to:
  /// **'本月'**
  String get focusStatsMonth;

  /// No description provided for @focusStatsTotal.
  ///
  /// In zh, this message translates to:
  /// **'总计'**
  String get focusStatsTotal;

  /// No description provided for @focusStatsSessions.
  ///
  /// In zh, this message translates to:
  /// **'{count} 次会话'**
  String focusStatsSessions(Object count);

  /// No description provided for @focusStatsMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count} 分钟'**
  String focusStatsMinutes(Object count);

  /// No description provided for @focusStatsHours.
  ///
  /// In zh, this message translates to:
  /// **'{count} 小时'**
  String focusStatsHours(Object count);

  /// No description provided for @focusStatsStreak.
  ///
  /// In zh, this message translates to:
  /// **'连续 {count} 天'**
  String focusStatsStreak(Object count);

  /// No description provided for @focusStatsBestDay.
  ///
  /// In zh, this message translates to:
  /// **'最佳：{time}'**
  String focusStatsBestDay(Object time);

  /// No description provided for @focusStatsScreenTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注统计'**
  String get focusStatsScreenTitle;

  /// No description provided for @focusStatsTrendTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注趋势'**
  String get focusStatsTrendTitle;

  /// No description provided for @focusStatsHeatmapRange.
  ///
  /// In zh, this message translates to:
  /// **'活跃热力图（{days}天）'**
  String focusStatsHeatmapRange(Object days);

  /// No description provided for @focusStatsRecentSessionsTitle.
  ///
  /// In zh, this message translates to:
  /// **'最近会话'**
  String get focusStatsRecentSessionsTitle;

  /// No description provided for @focusStatsNoSessions.
  ///
  /// In zh, this message translates to:
  /// **'暂无专注记录'**
  String get focusStatsNoSessions;

  /// No description provided for @focusStatsLoadMore.
  ///
  /// In zh, this message translates to:
  /// **'查看更多'**
  String get focusStatsLoadMore;

  /// No description provided for @focusStatsDurationTooltip.
  ///
  /// In zh, this message translates to:
  /// **'专注时长：{minutes}分钟'**
  String focusStatsDurationTooltip(Object minutes);

  /// No description provided for @focusStatsLegendLow.
  ///
  /// In zh, this message translates to:
  /// **'低'**
  String get focusStatsLegendLow;

  /// No description provided for @focusStatsLegendHigh.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get focusStatsLegendHigh;

  /// No description provided for @focusStatsPomodoroLabel.
  ///
  /// In zh, this message translates to:
  /// **'番茄'**
  String get focusStatsPomodoroLabel;

  /// No description provided for @focusStatsStopwatchLabel.
  ///
  /// In zh, this message translates to:
  /// **'正计'**
  String get focusStatsStopwatchLabel;

  /// No description provided for @focusSelectTaskTitle.
  ///
  /// In zh, this message translates to:
  /// **'选择专注任务'**
  String get focusSelectTaskTitle;

  /// No description provided for @focusReadyPrompt.
  ///
  /// In zh, this message translates to:
  /// **'准备好开始专注了吗？'**
  String get focusReadyPrompt;

  /// No description provided for @focusNoPendingTasks.
  ///
  /// In zh, this message translates to:
  /// **'没有待办任务'**
  String get focusNoPendingTasks;

  /// No description provided for @focusNoTasksButCanFocus.
  ///
  /// In zh, this message translates to:
  /// **'不过你依然可以直接开始专注!'**
  String get focusNoTasksButCanFocus;

  /// No description provided for @focusFreeFocus.
  ///
  /// In zh, this message translates to:
  /// **'自由专注'**
  String get focusFreeFocus;

  /// No description provided for @focusStartNow.
  ///
  /// In zh, this message translates to:
  /// **'立即开始'**
  String get focusStartNow;

  /// No description provided for @focusCreateTask.
  ///
  /// In zh, this message translates to:
  /// **'或者创建一个新任务'**
  String get focusCreateTask;

  /// No description provided for @focusQuickStart.
  ///
  /// In zh, this message translates to:
  /// **'快速开启专注 (25min)'**
  String get focusQuickStart;

  /// No description provided for @focusEstimated.
  ///
  /// In zh, this message translates to:
  /// **'预计 {minutes} 分钟'**
  String focusEstimated(Object minutes);

  /// No description provided for @focusCoachTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI专注教练'**
  String get focusCoachTitle;

  /// No description provided for @focusCoachSummary.
  ///
  /// In zh, this message translates to:
  /// **'任务：{task} · 已专注 {minutes} 分钟'**
  String focusCoachSummary(Object minutes, Object task);

  /// No description provided for @focusCoachPromptBreakdown.
  ///
  /// In zh, this message translates to:
  /// **'拆解接下来15分钟'**
  String get focusCoachPromptBreakdown;

  /// No description provided for @focusCoachPromptRefocus.
  ///
  /// In zh, this message translates to:
  /// **'分心提醒'**
  String get focusCoachPromptRefocus;

  /// No description provided for @focusCoachPromptNextAction.
  ///
  /// In zh, this message translates to:
  /// **'下一步行动'**
  String get focusCoachPromptNextAction;

  /// No description provided for @focusCoachPromptBreakdownMessage.
  ///
  /// In zh, this message translates to:
  /// **'请根据任务「{task}」，帮我拆解接下来15分钟的专注计划。'**
  String focusCoachPromptBreakdownMessage(Object task);

  /// No description provided for @focusCoachPromptRefocusMessage.
  ///
  /// In zh, this message translates to:
  /// **'我刚刚有些分心，请给我一句简短的回归提示。'**
  String get focusCoachPromptRefocusMessage;

  /// No description provided for @focusCoachPromptNextActionMessage.
  ///
  /// In zh, this message translates to:
  /// **'请总结当前任务的下一步行动，保持简洁明确。'**
  String get focusCoachPromptNextActionMessage;

  /// No description provided for @focusCoachEmpty.
  ///
  /// In zh, this message translates to:
  /// **'需要帮助就问我。'**
  String get focusCoachEmpty;

  /// No description provided for @focusCoachHint.
  ///
  /// In zh, this message translates to:
  /// **'问我：如何保持专注、拆解步骤...'**
  String get focusCoachHint;

  /// No description provided for @focusCandidateTitle.
  ///
  /// In zh, this message translates to:
  /// **'智能建议'**
  String get focusCandidateTitle;

  /// No description provided for @focusCandidateSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'基于你的学习状态预测'**
  String get focusCandidateSubtitle;

  /// No description provided for @focusCandidateFooterHint.
  ///
  /// In zh, this message translates to:
  /// **'轻扫关闭 · 不感兴趣可以忽略'**
  String get focusCandidateFooterHint;

  /// No description provided for @focusCandidateDismiss.
  ///
  /// In zh, this message translates to:
  /// **'不感兴趣'**
  String get focusCandidateDismiss;

  /// No description provided for @focusCandidateAccept.
  ///
  /// In zh, this message translates to:
  /// **'试试看'**
  String get focusCandidateAccept;

  /// No description provided for @focusInterruptionDetected.
  ///
  /// In zh, this message translates to:
  /// **'检测到分心行为（第 {count} 次）'**
  String focusInterruptionDetected(Object count);

  /// No description provided for @focusMindfulnessTitle.
  ///
  /// In zh, this message translates to:
  /// **'正念模式'**
  String get focusMindfulnessTitle;

  /// No description provided for @focusLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String focusLoadFailed(Object error);

  /// No description provided for @focusReturnToTask.
  ///
  /// In zh, this message translates to:
  /// **'返回任务'**
  String get focusReturnToTask;

  /// No description provided for @focusReturnToTaskTitle.
  ///
  /// In zh, this message translates to:
  /// **'返回任务执行'**
  String get focusReturnToTaskTitle;

  /// No description provided for @focusReturnToTaskMessage.
  ///
  /// In zh, this message translates to:
  /// **'专注记录会暂停，并返回任务执行页面。'**
  String get focusReturnToTaskMessage;

  /// No description provided for @focusReturnToTaskConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认返回'**
  String get focusReturnToTaskConfirm;

  /// No description provided for @focusExitMindfulness.
  ///
  /// In zh, this message translates to:
  /// **'退出正念模式'**
  String get focusExitMindfulness;

  /// No description provided for @focusDockMindfulness.
  ///
  /// In zh, this message translates to:
  /// **'正念模式'**
  String get focusDockMindfulness;

  /// No description provided for @focusDockToolbox.
  ///
  /// In zh, this message translates to:
  /// **'工具箱'**
  String get focusDockToolbox;

  /// No description provided for @focusReflectionTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注结束'**
  String get focusReflectionTitle;

  /// No description provided for @focusReflectionPrompt.
  ///
  /// In zh, this message translates to:
  /// **'这次专注的感觉如何？'**
  String get focusReflectionPrompt;

  /// No description provided for @focusReflectionNoteHint.
  ///
  /// In zh, this message translates to:
  /// **'有什么值得记录的吗？（可选）'**
  String get focusReflectionNoteHint;

  /// No description provided for @focusReflectionSaved.
  ///
  /// In zh, this message translates to:
  /// **'复盘已保存到 Cognitive Prism'**
  String get focusReflectionSaved;

  /// No description provided for @focusReflectionSaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存失败：{error}'**
  String focusReflectionSaveFailed(Object error);

  /// No description provided for @focusReflectionSummary.
  ///
  /// In zh, this message translates to:
  /// **'专注复盘：本次状态 {feeling}。\n{note}'**
  String focusReflectionSummary(Object feeling, Object note);

  /// No description provided for @focusReflectionMoodFlow.
  ///
  /// In zh, this message translates to:
  /// **'🔥 心流'**
  String get focusReflectionMoodFlow;

  /// No description provided for @focusReflectionMoodFocused.
  ///
  /// In zh, this message translates to:
  /// **'🙂 专注'**
  String get focusReflectionMoodFocused;

  /// No description provided for @focusReflectionMoodOkay.
  ///
  /// In zh, this message translates to:
  /// **'😐 一般'**
  String get focusReflectionMoodOkay;

  /// No description provided for @focusReflectionMoodDistracted.
  ///
  /// In zh, this message translates to:
  /// **'😖 分心'**
  String get focusReflectionMoodDistracted;

  /// No description provided for @focusReflectionMoodTired.
  ///
  /// In zh, this message translates to:
  /// **'😫 疲惫'**
  String get focusReflectionMoodTired;

  /// No description provided for @focusExitTitleStep1.
  ///
  /// In zh, this message translates to:
  /// **'确定要退出正念模式吗？'**
  String get focusExitTitleStep1;

  /// No description provided for @focusExitTitleStep2.
  ///
  /// In zh, this message translates to:
  /// **'即将退出'**
  String get focusExitTitleStep2;

  /// No description provided for @focusExitTitleStep3.
  ///
  /// In zh, this message translates to:
  /// **'最后确认'**
  String get focusExitTitleStep3;

  /// No description provided for @focusExitMessageStep1.
  ///
  /// In zh, this message translates to:
  /// **'你正处于专注状态，退出可能会影响专注效果。'**
  String get focusExitMessageStep1;

  /// No description provided for @focusExitMessageStep2.
  ///
  /// In zh, this message translates to:
  /// **'你已经专注了 {minutes} 分钟，确定要离开吗？'**
  String focusExitMessageStep2(Object minutes);

  /// No description provided for @focusExitMessageStep3.
  ///
  /// In zh, this message translates to:
  /// **'再坚持一下！放弃会中断你的专注记录。'**
  String get focusExitMessageStep3;

  /// No description provided for @focusExitCancelStep1.
  ///
  /// In zh, this message translates to:
  /// **'继续专注'**
  String get focusExitCancelStep1;

  /// No description provided for @focusExitConfirmStep1.
  ///
  /// In zh, this message translates to:
  /// **'确认退出'**
  String get focusExitConfirmStep1;

  /// No description provided for @focusExitConfirmStep2.
  ///
  /// In zh, this message translates to:
  /// **'继续退出'**
  String get focusExitConfirmStep2;

  /// No description provided for @focusExitConfirmStep3.
  ///
  /// In zh, this message translates to:
  /// **'确定退出'**
  String get focusExitConfirmStep3;

  /// No description provided for @streakTitle.
  ///
  /// In zh, this message translates to:
  /// **'连续学习'**
  String get streakTitle;

  /// No description provided for @streakDays.
  ///
  /// In zh, this message translates to:
  /// **'{count, plural, =1{1天} other{{count}天}}'**
  String streakDays(num count);

  /// No description provided for @streakMaxLabel.
  ///
  /// In zh, this message translates to:
  /// **'最高'**
  String get streakMaxLabel;

  /// No description provided for @streakMax.
  ///
  /// In zh, this message translates to:
  /// **'最高{count}'**
  String streakMax(Object count);

  /// No description provided for @streakTotalLabel.
  ///
  /// In zh, this message translates to:
  /// **'累计'**
  String get streakTotalLabel;

  /// No description provided for @streakTotal.
  ///
  /// In zh, this message translates to:
  /// **'累计{count}'**
  String streakTotal(Object count);

  /// No description provided for @streakStartChallenge.
  ///
  /// In zh, this message translates to:
  /// **'开始'**
  String get streakStartChallenge;

  /// No description provided for @streakChallenge.
  ///
  /// In zh, this message translates to:
  /// **'挑战'**
  String get streakChallenge;

  /// No description provided for @streakFreezeCharges.
  ///
  /// In zh, this message translates to:
  /// **'冻结次数'**
  String get streakFreezeCharges;

  /// No description provided for @errorNetwork.
  ///
  /// In zh, this message translates to:
  /// **'网络错误'**
  String get errorNetwork;

  /// No description provided for @errorNetworkDetail.
  ///
  /// In zh, this message translates to:
  /// **'请检查您的网络连接'**
  String get errorNetworkDetail;

  /// No description provided for @errorServer.
  ///
  /// In zh, this message translates to:
  /// **'服务器错误'**
  String get errorServer;

  /// No description provided for @errorServerDetail.
  ///
  /// In zh, this message translates to:
  /// **'服务器出现问题'**
  String get errorServerDetail;

  /// No description provided for @errorUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知错误'**
  String get errorUnknown;

  /// No description provided for @errorUnknownDetail.
  ///
  /// In zh, this message translates to:
  /// **'发生了意外错误'**
  String get errorUnknownDetail;

  /// No description provided for @errorValidation.
  ///
  /// In zh, this message translates to:
  /// **'验证错误'**
  String get errorValidation;

  /// No description provided for @errorValidationDetail.
  ///
  /// In zh, this message translates to:
  /// **'请检查您的输入'**
  String get errorValidationDetail;

  /// No description provided for @errorPermission.
  ///
  /// In zh, this message translates to:
  /// **'权限不足'**
  String get errorPermission;

  /// No description provided for @errorPermissionDetail.
  ///
  /// In zh, this message translates to:
  /// **'您没有权限执行此操作'**
  String get errorPermissionDetail;

  /// No description provided for @errorNotFoundTitle.
  ///
  /// In zh, this message translates to:
  /// **'未找到'**
  String get errorNotFoundTitle;

  /// No description provided for @errorNotFoundDetail.
  ///
  /// In zh, this message translates to:
  /// **'请求的资源不存在'**
  String get errorNotFoundDetail;

  /// No description provided for @errorTimeout.
  ///
  /// In zh, this message translates to:
  /// **'请求超时'**
  String get errorTimeout;

  /// No description provided for @errorTimeoutDetail.
  ///
  /// In zh, this message translates to:
  /// **'请求处理时间过长'**
  String get errorTimeoutDetail;

  /// No description provided for @errorCancelled.
  ///
  /// In zh, this message translates to:
  /// **'已取消'**
  String get errorCancelled;

  /// No description provided for @errorCancelledDetail.
  ///
  /// In zh, this message translates to:
  /// **'操作已取消'**
  String get errorCancelledDetail;

  /// No description provided for @errorStorage.
  ///
  /// In zh, this message translates to:
  /// **'存储错误'**
  String get errorStorage;

  /// No description provided for @errorStorageDetail.
  ///
  /// In zh, this message translates to:
  /// **'保存数据失败'**
  String get errorStorageDetail;

  /// No description provided for @errorSync.
  ///
  /// In zh, this message translates to:
  /// **'同步错误'**
  String get errorSync;

  /// No description provided for @errorSyncDetail.
  ///
  /// In zh, this message translates to:
  /// **'同步数据失败'**
  String get errorSyncDetail;

  /// No description provided for @errorAuth.
  ///
  /// In zh, this message translates to:
  /// **'认证错误'**
  String get errorAuth;

  /// No description provided for @errorAuthDetail.
  ///
  /// In zh, this message translates to:
  /// **'请重新登录'**
  String get errorAuthDetail;

  /// No description provided for @errorRateLimitTitle.
  ///
  /// In zh, this message translates to:
  /// **'请求过于频繁'**
  String get errorRateLimitTitle;

  /// No description provided for @errorRateLimitDetail.
  ///
  /// In zh, this message translates to:
  /// **'请稍后再试'**
  String get errorRateLimitDetail;

  /// No description provided for @errorMaintenance.
  ///
  /// In zh, this message translates to:
  /// **'系统维护中'**
  String get errorMaintenance;

  /// No description provided for @errorMaintenanceDetail.
  ///
  /// In zh, this message translates to:
  /// **'系统正在升级，请稍后再来'**
  String get errorMaintenanceDetail;

  /// No description provided for @timeJustNow.
  ///
  /// In zh, this message translates to:
  /// **'刚刚'**
  String get timeJustNow;

  /// No description provided for @timeMinutesAgo.
  ///
  /// In zh, this message translates to:
  /// **'{count}分钟前'**
  String timeMinutesAgo(num count);

  /// No description provided for @timeHoursAgo.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时前'**
  String timeHoursAgo(num count);

  /// No description provided for @timeDaysAgo.
  ///
  /// In zh, this message translates to:
  /// **'{count}天前'**
  String timeDaysAgo(num count);

  /// No description provided for @timeWeeksAgo.
  ///
  /// In zh, this message translates to:
  /// **'{count}周前'**
  String timeWeeksAgo(num count);

  /// No description provided for @timeMonthsAgo.
  ///
  /// In zh, this message translates to:
  /// **'{count}个月前'**
  String timeMonthsAgo(num count);

  /// No description provided for @timeYearsAgo.
  ///
  /// In zh, this message translates to:
  /// **'{count}年前'**
  String timeYearsAgo(num count);

  /// No description provided for @timeInMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count}分钟后'**
  String timeInMinutes(num count);

  /// No description provided for @timeInHours.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时后'**
  String timeInHours(num count);

  /// No description provided for @timeInDays.
  ///
  /// In zh, this message translates to:
  /// **'{count}天后'**
  String timeInDays(num count);

  /// No description provided for @timeInWeeks.
  ///
  /// In zh, this message translates to:
  /// **'{count}周后'**
  String timeInWeeks(num count);

  /// No description provided for @timeInMonths.
  ///
  /// In zh, this message translates to:
  /// **'{count}个月后'**
  String timeInMonths(num count);

  /// No description provided for @timeInYears.
  ///
  /// In zh, this message translates to:
  /// **'{count}年后'**
  String timeInYears(num count);

  /// No description provided for @timeToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get timeToday;

  /// No description provided for @timeYesterday.
  ///
  /// In zh, this message translates to:
  /// **'昨天'**
  String get timeYesterday;

  /// No description provided for @timeTomorrow.
  ///
  /// In zh, this message translates to:
  /// **'明天'**
  String get timeTomorrow;

  /// No description provided for @timeThisWeek.
  ///
  /// In zh, this message translates to:
  /// **'本周'**
  String get timeThisWeek;

  /// No description provided for @timeNextWeek.
  ///
  /// In zh, this message translates to:
  /// **'下周'**
  String get timeNextWeek;

  /// No description provided for @timeThisMonth.
  ///
  /// In zh, this message translates to:
  /// **'本月'**
  String get timeThisMonth;

  /// No description provided for @timeLastMonth.
  ///
  /// In zh, this message translates to:
  /// **'上月'**
  String get timeLastMonth;

  /// No description provided for @durationHours.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时'**
  String durationHours(Object count);

  /// No description provided for @durationMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count}分钟'**
  String durationMinutes(Object count);

  /// No description provided for @durationSeconds.
  ///
  /// In zh, this message translates to:
  /// **'{count}秒'**
  String durationSeconds(Object count);

  /// No description provided for @durationHoursMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{hours}小时{minutes}分钟'**
  String durationHoursMinutes(Object hours, Object minutes);

  /// No description provided for @durationMinutesSeconds.
  ///
  /// In zh, this message translates to:
  /// **'{minutes}分{seconds}秒'**
  String durationMinutesSeconds(Object minutes, Object seconds);

  /// No description provided for @numberCount.
  ///
  /// In zh, this message translates to:
  /// **'{count, plural, =0{无} =1{1项} other{{count}项}}'**
  String numberCount(num count);

  /// No description provided for @numberSelected.
  ///
  /// In zh, this message translates to:
  /// **'已选择 {count} 项'**
  String numberSelected(Object count);

  /// No description provided for @numberTotal.
  ///
  /// In zh, this message translates to:
  /// **'{current}/{total}'**
  String numberTotal(Object current, Object total);

  /// No description provided for @numberPercent.
  ///
  /// In zh, this message translates to:
  /// **'{value}%'**
  String numberPercent(Object value);

  /// No description provided for @numberProgress.
  ///
  /// In zh, this message translates to:
  /// **'完成 {value}%'**
  String numberProgress(Object value);

  /// No description provided for @numberK.
  ///
  /// In zh, this message translates to:
  /// **'{value}K'**
  String numberK(Object value);

  /// No description provided for @numberM.
  ///
  /// In zh, this message translates to:
  /// **'{value}M'**
  String numberM(Object value);

  /// No description provided for @numberB.
  ///
  /// In zh, this message translates to:
  /// **'{value}B'**
  String numberB(Object value);

  /// No description provided for @commonYes.
  ///
  /// In zh, this message translates to:
  /// **'是'**
  String get commonYes;

  /// No description provided for @commonNo.
  ///
  /// In zh, this message translates to:
  /// **'否'**
  String get commonNo;

  /// No description provided for @commonOk.
  ///
  /// In zh, this message translates to:
  /// **'确定'**
  String get commonOk;

  /// No description provided for @commonCancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get commonCancel;

  /// No description provided for @commonSave.
  ///
  /// In zh, this message translates to:
  /// **'保存'**
  String get commonSave;

  /// No description provided for @commonDelete.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get commonDelete;

  /// No description provided for @commonEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑'**
  String get commonEdit;

  /// No description provided for @commonAdd.
  ///
  /// In zh, this message translates to:
  /// **'添加'**
  String get commonAdd;

  /// No description provided for @commonRemove.
  ///
  /// In zh, this message translates to:
  /// **'移除'**
  String get commonRemove;

  /// No description provided for @commonClear.
  ///
  /// In zh, this message translates to:
  /// **'清除'**
  String get commonClear;

  /// No description provided for @commonReset.
  ///
  /// In zh, this message translates to:
  /// **'重置'**
  String get commonReset;

  /// No description provided for @commonRefresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新'**
  String get commonRefresh;

  /// No description provided for @commonSearch.
  ///
  /// In zh, this message translates to:
  /// **'搜索'**
  String get commonSearch;

  /// No description provided for @commonFilter.
  ///
  /// In zh, this message translates to:
  /// **'筛选'**
  String get commonFilter;

  /// No description provided for @commonSort.
  ///
  /// In zh, this message translates to:
  /// **'排序'**
  String get commonSort;

  /// No description provided for @commonClose.
  ///
  /// In zh, this message translates to:
  /// **'关闭'**
  String get commonClose;

  /// No description provided for @commonDismiss.
  ///
  /// In zh, this message translates to:
  /// **'忽略'**
  String get commonDismiss;

  /// No description provided for @commonApply.
  ///
  /// In zh, this message translates to:
  /// **'应用'**
  String get commonApply;

  /// No description provided for @commonSubmit.
  ///
  /// In zh, this message translates to:
  /// **'提交'**
  String get commonSubmit;

  /// No description provided for @commonContinue.
  ///
  /// In zh, this message translates to:
  /// **'继续'**
  String get commonContinue;

  /// No description provided for @commonSkip.
  ///
  /// In zh, this message translates to:
  /// **'跳过'**
  String get commonSkip;

  /// No description provided for @commonNext.
  ///
  /// In zh, this message translates to:
  /// **'下一步'**
  String get commonNext;

  /// No description provided for @commonPrevious.
  ///
  /// In zh, this message translates to:
  /// **'上一步'**
  String get commonPrevious;

  /// No description provided for @commonDone.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get commonDone;

  /// No description provided for @commonLoading.
  ///
  /// In zh, this message translates to:
  /// **'加载中...'**
  String get commonLoading;

  /// No description provided for @commonSaving.
  ///
  /// In zh, this message translates to:
  /// **'保存中...'**
  String get commonSaving;

  /// No description provided for @commonProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中...'**
  String get commonProcessing;

  /// No description provided for @commonSuccess.
  ///
  /// In zh, this message translates to:
  /// **'成功'**
  String get commonSuccess;

  /// No description provided for @commonError.
  ///
  /// In zh, this message translates to:
  /// **'错误'**
  String get commonError;

  /// No description provided for @commonWarning.
  ///
  /// In zh, this message translates to:
  /// **'警告'**
  String get commonWarning;

  /// No description provided for @commonInfo.
  ///
  /// In zh, this message translates to:
  /// **'信息'**
  String get commonInfo;

  /// No description provided for @commonNoData.
  ///
  /// In zh, this message translates to:
  /// **'暂无数据'**
  String get commonNoData;

  /// No description provided for @commonNoResults.
  ///
  /// In zh, this message translates to:
  /// **'未找到结果'**
  String get commonNoResults;

  /// No description provided for @commonTryAgain.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get commonTryAgain;

  /// No description provided for @commonLearnMore.
  ///
  /// In zh, this message translates to:
  /// **'了解更多'**
  String get commonLearnMore;

  /// No description provided for @commonSeeAll.
  ///
  /// In zh, this message translates to:
  /// **'查看全部'**
  String get commonSeeAll;

  /// No description provided for @operationPreview.
  ///
  /// In zh, this message translates to:
  /// **'操作预览：'**
  String get operationPreview;

  /// No description provided for @commonShowLess.
  ///
  /// In zh, this message translates to:
  /// **'收起'**
  String get commonShowLess;

  /// No description provided for @commonShowMore.
  ///
  /// In zh, this message translates to:
  /// **'展开更多'**
  String get commonShowMore;

  /// No description provided for @commonCollapse.
  ///
  /// In zh, this message translates to:
  /// **'折叠'**
  String get commonCollapse;

  /// No description provided for @commonExpand.
  ///
  /// In zh, this message translates to:
  /// **'展开'**
  String get commonExpand;

  /// No description provided for @commonRequired.
  ///
  /// In zh, this message translates to:
  /// **'必填'**
  String get commonRequired;

  /// No description provided for @commonOptional.
  ///
  /// In zh, this message translates to:
  /// **'可选'**
  String get commonOptional;

  /// No description provided for @commonEnabled.
  ///
  /// In zh, this message translates to:
  /// **'已启用'**
  String get commonEnabled;

  /// No description provided for @commonDisabled.
  ///
  /// In zh, this message translates to:
  /// **'已禁用'**
  String get commonDisabled;

  /// No description provided for @commonOn.
  ///
  /// In zh, this message translates to:
  /// **'开'**
  String get commonOn;

  /// No description provided for @commonOff.
  ///
  /// In zh, this message translates to:
  /// **'关'**
  String get commonOff;

  /// No description provided for @commonActive.
  ///
  /// In zh, this message translates to:
  /// **'活跃'**
  String get commonActive;

  /// No description provided for @commonInactive.
  ///
  /// In zh, this message translates to:
  /// **'未激活'**
  String get commonInactive;

  /// No description provided for @commonConnected.
  ///
  /// In zh, this message translates to:
  /// **'已连接'**
  String get commonConnected;

  /// No description provided for @commonDisconnected.
  ///
  /// In zh, this message translates to:
  /// **'已断开'**
  String get commonDisconnected;

  /// No description provided for @commonSyncing.
  ///
  /// In zh, this message translates to:
  /// **'同步中...'**
  String get commonSyncing;

  /// No description provided for @commonSynced.
  ///
  /// In zh, this message translates to:
  /// **'已同步'**
  String get commonSynced;

  /// No description provided for @commonOffline.
  ///
  /// In zh, this message translates to:
  /// **'离线'**
  String get commonOffline;

  /// No description provided for @commonOnline.
  ///
  /// In zh, this message translates to:
  /// **'在线'**
  String get commonOnline;

  /// No description provided for @commonOperationWarning.
  ///
  /// In zh, this message translates to:
  /// **'操作可能未成功'**
  String get commonOperationWarning;

  /// No description provided for @emptyStateNoTasksTitle.
  ///
  /// In zh, this message translates to:
  /// **'还没有任务'**
  String get emptyStateNoTasksTitle;

  /// No description provided for @emptyStateNoTasksDescription.
  ///
  /// In zh, this message translates to:
  /// **'创建你的第一个学习任务，马上开始。'**
  String get emptyStateNoTasksDescription;

  /// No description provided for @emptyStateNoChatsTitle.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle 已就绪'**
  String get emptyStateNoChatsTitle;

  /// No description provided for @emptyStateNoChatsDescription.
  ///
  /// In zh, this message translates to:
  /// **'随时开口，我们开始对话。'**
  String get emptyStateNoChatsDescription;

  /// No description provided for @emptyStateNoPlansTitle.
  ///
  /// In zh, this message translates to:
  /// **'还没有学习计划'**
  String get emptyStateNoPlansTitle;

  /// No description provided for @emptyStateNoPlansDescription.
  ///
  /// In zh, this message translates to:
  /// **'制定一个计划，让 AI 帮你规划路线。'**
  String get emptyStateNoPlansDescription;

  /// No description provided for @emptyStateNoErrorsTitle.
  ///
  /// In zh, this message translates to:
  /// **'状态不错'**
  String get emptyStateNoErrorsTitle;

  /// No description provided for @emptyStateNoErrorsDescription.
  ///
  /// In zh, this message translates to:
  /// **'你还没有错题记录。'**
  String get emptyStateNoErrorsDescription;

  /// No description provided for @emptyStateNoResultsTitle.
  ///
  /// In zh, this message translates to:
  /// **'没有找到结果'**
  String get emptyStateNoResultsTitle;

  /// No description provided for @emptyStateNoResultsDescription.
  ///
  /// In zh, this message translates to:
  /// **'试试其他关键词。'**
  String get emptyStateNoResultsDescription;

  /// No description provided for @emptyStateNoResultsQuery.
  ///
  /// In zh, this message translates to:
  /// **'没有找到与“{query}”相关的内容'**
  String emptyStateNoResultsQuery(Object query);

  /// No description provided for @emptyStateGeneralTitle.
  ///
  /// In zh, this message translates to:
  /// **'这里还没有内容'**
  String get emptyStateGeneralTitle;

  /// No description provided for @emptyStateGeneralDescription.
  ///
  /// In zh, this message translates to:
  /// **'先添加一些内容吧。'**
  String get emptyStateGeneralDescription;

  /// No description provided for @emptyStateStartChatAction.
  ///
  /// In zh, this message translates to:
  /// **'开始对话'**
  String get emptyStateStartChatAction;

  /// No description provided for @emptyStateCreatePlanAction.
  ///
  /// In zh, this message translates to:
  /// **'创建计划'**
  String get emptyStateCreatePlanAction;

  /// No description provided for @voiceInputPermissionTitle.
  ///
  /// In zh, this message translates to:
  /// **'需要麦克风权限'**
  String get voiceInputPermissionTitle;

  /// No description provided for @voiceInputPermissionContent.
  ///
  /// In zh, this message translates to:
  /// **'开启麦克风权限后即可使用语音输入。'**
  String get voiceInputPermissionContent;

  /// No description provided for @voiceInputOpenSettings.
  ///
  /// In zh, this message translates to:
  /// **'去设置'**
  String get voiceInputOpenSettings;

  /// No description provided for @voiceInputNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'需要麦克风权限才能使用语音输入。'**
  String get voiceInputNoPermission;

  /// No description provided for @voiceInputLoginRequired.
  ///
  /// In zh, this message translates to:
  /// **'请先登录后再使用语音输入。'**
  String get voiceInputLoginRequired;

  /// No description provided for @voiceInputStartFailed.
  ///
  /// In zh, this message translates to:
  /// **'开始录音失败：{error}'**
  String voiceInputStartFailed(Object error);

  /// No description provided for @quickReplyTodayPlanLabel.
  ///
  /// In zh, this message translates to:
  /// **'今日计划'**
  String get quickReplyTodayPlanLabel;

  /// No description provided for @quickReplyTodayPlanMessage.
  ///
  /// In zh, this message translates to:
  /// **'我今天的计划是什么？'**
  String get quickReplyTodayPlanMessage;

  /// No description provided for @quickReplyReviewPlanLabel.
  ///
  /// In zh, this message translates to:
  /// **'复盘计划'**
  String get quickReplyReviewPlanLabel;

  /// No description provided for @quickReplyReviewPlanMessage.
  ///
  /// In zh, this message translates to:
  /// **'帮我复盘一下今天的计划。'**
  String get quickReplyReviewPlanMessage;

  /// No description provided for @quickReplyStartFocusLabel.
  ///
  /// In zh, this message translates to:
  /// **'开始专注'**
  String get quickReplyStartFocusLabel;

  /// No description provided for @quickReplyStartFocusMessage.
  ///
  /// In zh, this message translates to:
  /// **'帮我开始一次专注。'**
  String get quickReplyStartFocusMessage;

  /// No description provided for @quickReplyAnalyzeErrorsLabel.
  ///
  /// In zh, this message translates to:
  /// **'分析错题'**
  String get quickReplyAnalyzeErrorsLabel;

  /// No description provided for @quickReplyAnalyzeErrorsMessage.
  ///
  /// In zh, this message translates to:
  /// **'分析一下我最近的错题。'**
  String get quickReplyAnalyzeErrorsMessage;

  /// No description provided for @quickReplyLearningProgressLabel.
  ///
  /// In zh, this message translates to:
  /// **'学习进度'**
  String get quickReplyLearningProgressLabel;

  /// No description provided for @quickReplyLearningProgressMessage.
  ///
  /// In zh, this message translates to:
  /// **'我最近的学习进度怎么样？'**
  String get quickReplyLearningProgressMessage;

  /// No description provided for @quickReplyAddErrorLabel.
  ///
  /// In zh, this message translates to:
  /// **'添加错题'**
  String get quickReplyAddErrorLabel;

  /// No description provided for @quickReplyAddErrorMessage.
  ///
  /// In zh, this message translates to:
  /// **'帮我添加一条新的错题记录。'**
  String get quickReplyAddErrorMessage;

  /// No description provided for @quickReplyReviewErrorsLabel.
  ///
  /// In zh, this message translates to:
  /// **'复习错题'**
  String get quickReplyReviewErrorsLabel;

  /// No description provided for @quickReplyReviewErrorsMessage.
  ///
  /// In zh, this message translates to:
  /// **'我们来复习一下错题本。'**
  String get quickReplyReviewErrorsMessage;

  /// No description provided for @quickReplyErrorStatsLabel.
  ///
  /// In zh, this message translates to:
  /// **'错题统计'**
  String get quickReplyErrorStatsLabel;

  /// No description provided for @quickReplyErrorStatsMessage.
  ///
  /// In zh, this message translates to:
  /// **'给我看看错题统计。'**
  String get quickReplyErrorStatsMessage;

  /// No description provided for @quickReplyWeakSubjectsLabel.
  ///
  /// In zh, this message translates to:
  /// **'薄弱点'**
  String get quickReplyWeakSubjectsLabel;

  /// No description provided for @quickReplyWeakSubjectsMessage.
  ///
  /// In zh, this message translates to:
  /// **'我现在最薄弱的科目是什么？'**
  String get quickReplyWeakSubjectsMessage;

  /// No description provided for @quickReplyExploreGalaxyLabel.
  ///
  /// In zh, this message translates to:
  /// **'探索星图'**
  String get quickReplyExploreGalaxyLabel;

  /// No description provided for @quickReplyExploreGalaxyMessage.
  ///
  /// In zh, this message translates to:
  /// **'带我去看看知识星图。'**
  String get quickReplyExploreGalaxyMessage;

  /// No description provided for @quickReplyAddKnowledgeLabel.
  ///
  /// In zh, this message translates to:
  /// **'添加知识点'**
  String get quickReplyAddKnowledgeLabel;

  /// No description provided for @quickReplyAddKnowledgeMessage.
  ///
  /// In zh, this message translates to:
  /// **'帮我添加一个新的知识点。'**
  String get quickReplyAddKnowledgeMessage;

  /// No description provided for @quickReplyFindGapsLabel.
  ///
  /// In zh, this message translates to:
  /// **'查找缺口'**
  String get quickReplyFindGapsLabel;

  /// No description provided for @quickReplyFindGapsMessage.
  ///
  /// In zh, this message translates to:
  /// **'帮我找找知识图谱里的缺口。'**
  String get quickReplyFindGapsMessage;

  /// No description provided for @quickReplyGreetingLateNight.
  ///
  /// In zh, this message translates to:
  /// **'还没睡呀？需要我陪你收个尾吗？'**
  String get quickReplyGreetingLateNight;

  /// No description provided for @quickReplyGreetingMorning.
  ///
  /// In zh, this message translates to:
  /// **'早上好！今天想从哪件事开始？'**
  String get quickReplyGreetingMorning;

  /// No description provided for @quickReplyGreetingNoon.
  ///
  /// In zh, this message translates to:
  /// **'中午了，想整理一下今天的节奏吗？'**
  String get quickReplyGreetingNoon;

  /// No description provided for @quickReplyGreetingAfternoon.
  ///
  /// In zh, this message translates to:
  /// **'下午好，继续推进还是先复盘一下？'**
  String get quickReplyGreetingAfternoon;

  /// No description provided for @quickReplyGreetingEvening.
  ///
  /// In zh, this message translates to:
  /// **'晚上好，想做个总结还是安排明天？'**
  String get quickReplyGreetingEvening;

  /// No description provided for @quickReplyGreetingNight.
  ///
  /// In zh, this message translates to:
  /// **'夜深了，想快速收个尾还是放松一下？'**
  String get quickReplyGreetingNight;

  /// No description provided for @privateChatDefaultTitle.
  ///
  /// In zh, this message translates to:
  /// **'聊天'**
  String get privateChatDefaultTitle;

  /// No description provided for @privateChatEmptyPrompt.
  ///
  /// In zh, this message translates to:
  /// **'开始对话吧！'**
  String get privateChatEmptyPrompt;

  /// No description provided for @chatDefaultGroupName.
  ///
  /// In zh, this message translates to:
  /// **'群聊'**
  String get chatDefaultGroupName;

  /// No description provided for @chatDefaultFriendName.
  ///
  /// In zh, this message translates to:
  /// **'好友'**
  String get chatDefaultFriendName;

  /// No description provided for @shopTitle.
  ///
  /// In zh, this message translates to:
  /// **'光子商城'**
  String get shopTitle;

  /// No description provided for @shopCategoryAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get shopCategoryAll;

  /// No description provided for @shopCategorySkin.
  ///
  /// In zh, this message translates to:
  /// **'皮肤'**
  String get shopCategorySkin;

  /// No description provided for @shopCategoryTitle.
  ///
  /// In zh, this message translates to:
  /// **'称号'**
  String get shopCategoryTitle;

  /// No description provided for @shopCategoryConsumable.
  ///
  /// In zh, this message translates to:
  /// **'消耗品'**
  String get shopCategoryConsumable;

  /// No description provided for @shopCategoryBoost.
  ///
  /// In zh, this message translates to:
  /// **'加成'**
  String get shopCategoryBoost;

  /// No description provided for @shopCategoryVisualElement.
  ///
  /// In zh, this message translates to:
  /// **'视觉元素'**
  String get shopCategoryVisualElement;

  /// No description provided for @shopEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无物品'**
  String get shopEmpty;

  /// No description provided for @shopPurchaseSuccess.
  ///
  /// In zh, this message translates to:
  /// **'成功购买 {name}'**
  String shopPurchaseSuccess(Object name);

  /// No description provided for @shopPurchaseFailed.
  ///
  /// In zh, this message translates to:
  /// **'购买失败'**
  String get shopPurchaseFailed;

  /// No description provided for @purchaseConfirmTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认购买'**
  String get purchaseConfirmTitle;

  /// No description provided for @shopPriceLabel.
  ///
  /// In zh, this message translates to:
  /// **'价格'**
  String get shopPriceLabel;

  /// No description provided for @shopBalanceLabel.
  ///
  /// In zh, this message translates to:
  /// **'当前余额'**
  String get shopBalanceLabel;

  /// No description provided for @shopBalanceAfterPurchase.
  ///
  /// In zh, this message translates to:
  /// **'购买后余额'**
  String get shopBalanceAfterPurchase;

  /// No description provided for @shopInsufficientPhotons.
  ///
  /// In zh, this message translates to:
  /// **'光子不足'**
  String get shopInsufficientPhotons;

  /// No description provided for @shopConfirmPurchase.
  ///
  /// In zh, this message translates to:
  /// **'确认购买'**
  String get shopConfirmPurchase;

  /// No description provided for @shopItemSemantics.
  ///
  /// In zh, this message translates to:
  /// **'{name}，价格 {price} 光子'**
  String shopItemSemantics(Object name, Object price);

  /// No description provided for @shopOwned.
  ///
  /// In zh, this message translates to:
  /// **'已拥有'**
  String get shopOwned;

  /// No description provided for @shopLimitedStock.
  ///
  /// In zh, this message translates to:
  /// **'限量 {count}'**
  String shopLimitedStock(Object count);

  /// No description provided for @userTitlesEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无称号'**
  String get userTitlesEmpty;

  /// No description provided for @userTitleUnequippedOption.
  ///
  /// In zh, this message translates to:
  /// **'不装备称号'**
  String get userTitleUnequippedOption;

  /// No description provided for @notificationCenterTitle.
  ///
  /// In zh, this message translates to:
  /// **'通知中心'**
  String get notificationCenterTitle;

  /// No description provided for @notificationMarkAllRead.
  ///
  /// In zh, this message translates to:
  /// **'全部已读（{count}）'**
  String notificationMarkAllRead(Object count);

  /// No description provided for @notificationClearRead.
  ///
  /// In zh, this message translates to:
  /// **'清除已读'**
  String get notificationClearRead;

  /// No description provided for @notificationEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'暂无通知'**
  String get notificationEmptyTitle;

  /// No description provided for @notificationEmptyDescription.
  ///
  /// In zh, this message translates to:
  /// **'有新通知时会显示在这里。'**
  String get notificationEmptyDescription;

  /// No description provided for @notificationFilterAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get notificationFilterAll;

  /// No description provided for @notificationFilterUnread.
  ///
  /// In zh, this message translates to:
  /// **'未读'**
  String get notificationFilterUnread;

  /// No description provided for @notificationFilterRead.
  ///
  /// In zh, this message translates to:
  /// **'已读'**
  String get notificationFilterRead;

  /// No description provided for @notificationSourceAll.
  ///
  /// In zh, this message translates to:
  /// **'所有类型'**
  String get notificationSourceAll;

  /// No description provided for @notificationSourceSystem.
  ///
  /// In zh, this message translates to:
  /// **'系统通知'**
  String get notificationSourceSystem;

  /// No description provided for @notificationSourceIntervention.
  ///
  /// In zh, this message translates to:
  /// **'干预通知'**
  String get notificationSourceIntervention;

  /// No description provided for @notificationMarkedAllRead.
  ///
  /// In zh, this message translates to:
  /// **'已标记所有通知为已读'**
  String get notificationMarkedAllRead;

  /// No description provided for @notificationClearReadTitle.
  ///
  /// In zh, this message translates to:
  /// **'清除已读通知'**
  String get notificationClearReadTitle;

  /// No description provided for @notificationClearReadMessage.
  ///
  /// In zh, this message translates to:
  /// **'确定要清除所有已读通知吗？'**
  String get notificationClearReadMessage;

  /// No description provided for @notificationClearReadSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已清除已读通知'**
  String get notificationClearReadSuccess;

  /// No description provided for @notificationAnalyticsTitle.
  ///
  /// In zh, this message translates to:
  /// **'通知统计'**
  String get notificationAnalyticsTitle;

  /// No description provided for @notificationAnalyticsNoData.
  ///
  /// In zh, this message translates to:
  /// **'暂无数据'**
  String get notificationAnalyticsNoData;

  /// No description provided for @notificationAnalyticsLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String notificationAnalyticsLoadFailed(Object error);

  /// No description provided for @notificationAnalyticsSummary.
  ///
  /// In zh, this message translates to:
  /// **'汇总统计'**
  String get notificationAnalyticsSummary;

  /// No description provided for @notificationAnalyticsTotalSent.
  ///
  /// In zh, this message translates to:
  /// **'发送总数'**
  String get notificationAnalyticsTotalSent;

  /// No description provided for @notificationAnalyticsTotalViewed.
  ///
  /// In zh, this message translates to:
  /// **'查看数'**
  String get notificationAnalyticsTotalViewed;

  /// No description provided for @notificationAnalyticsTotalClicked.
  ///
  /// In zh, this message translates to:
  /// **'点击数'**
  String get notificationAnalyticsTotalClicked;

  /// No description provided for @notificationAnalyticsViewRate.
  ///
  /// In zh, this message translates to:
  /// **'查看率'**
  String get notificationAnalyticsViewRate;

  /// No description provided for @notificationAnalyticsByType.
  ///
  /// In zh, this message translates to:
  /// **'按类型统计'**
  String get notificationAnalyticsByType;

  /// No description provided for @notificationAnalyticsSent.
  ///
  /// In zh, this message translates to:
  /// **'发送'**
  String get notificationAnalyticsSent;

  /// No description provided for @notificationAnalyticsViewed.
  ///
  /// In zh, this message translates to:
  /// **'查看'**
  String get notificationAnalyticsViewed;

  /// No description provided for @notificationAnalyticsTrends.
  ///
  /// In zh, this message translates to:
  /// **'趋势分析'**
  String get notificationAnalyticsTrends;

  /// No description provided for @notificationAnalyticsNoTrends.
  ///
  /// In zh, this message translates to:
  /// **'暂无趋势数据'**
  String get notificationAnalyticsNoTrends;

  /// No description provided for @notificationAnalyticsHourlyDistribution.
  ///
  /// In zh, this message translates to:
  /// **'24小时分布'**
  String get notificationAnalyticsHourlyDistribution;

  /// No description provided for @notificationAnalyticsPeriod1d.
  ///
  /// In zh, this message translates to:
  /// **'1天'**
  String get notificationAnalyticsPeriod1d;

  /// No description provided for @notificationAnalyticsPeriod7d.
  ///
  /// In zh, this message translates to:
  /// **'7天'**
  String get notificationAnalyticsPeriod7d;

  /// No description provided for @notificationAnalyticsPeriod30d.
  ///
  /// In zh, this message translates to:
  /// **'30天'**
  String get notificationAnalyticsPeriod30d;

  /// No description provided for @notificationAnalyticsPeriodAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get notificationAnalyticsPeriodAll;

  /// No description provided for @intentAnalysisLabel.
  ///
  /// In zh, this message translates to:
  /// **'分析意图'**
  String get intentAnalysisLabel;

  /// No description provided for @intentAnalysisInProgress.
  ///
  /// In zh, this message translates to:
  /// **'分析中...'**
  String get intentAnalysisInProgress;

  /// No description provided for @intentAnalysisMultiIntent.
  ///
  /// In zh, this message translates to:
  /// **'多意图'**
  String get intentAnalysisMultiIntent;

  /// No description provided for @intentAnalysisFailed.
  ///
  /// In zh, this message translates to:
  /// **'意图分析失败：{error}'**
  String intentAnalysisFailed(Object error);

  /// No description provided for @intentPreviewTitle.
  ///
  /// In zh, this message translates to:
  /// **'意图分析'**
  String get intentPreviewTitle;

  /// No description provided for @intentPreviewAnalyzing.
  ///
  /// In zh, this message translates to:
  /// **'正在分析意图...'**
  String get intentPreviewAnalyzing;

  /// No description provided for @intentPreviewSingleIntent.
  ///
  /// In zh, this message translates to:
  /// **'识别到单一意图'**
  String get intentPreviewSingleIntent;

  /// No description provided for @intentPreviewDetectedCount.
  ///
  /// In zh, this message translates to:
  /// **'识别到 {count} 个意图：'**
  String intentPreviewDetectedCount(Object count);

  /// No description provided for @intentPreviewAssistantRole.
  ///
  /// In zh, this message translates to:
  /// **'助手：{role}'**
  String intentPreviewAssistantRole(Object role);

  /// No description provided for @intentPreviewExecutionPlan.
  ///
  /// In zh, this message translates to:
  /// **'执行计划'**
  String get intentPreviewExecutionPlan;

  /// No description provided for @intentPreviewExecutionPlanWithTime.
  ///
  /// In zh, this message translates to:
  /// **'执行计划（约 {seconds} 秒）'**
  String intentPreviewExecutionPlanWithTime(Object seconds);

  /// No description provided for @intentPreviewConfirmExecute.
  ///
  /// In zh, this message translates to:
  /// **'确认执行'**
  String get intentPreviewConfirmExecute;

  /// No description provided for @intentPreviewDirectExecute.
  ///
  /// In zh, this message translates to:
  /// **'直接执行'**
  String get intentPreviewDirectExecute;

  /// No description provided for @intentExecutionFailed.
  ///
  /// In zh, this message translates to:
  /// **'执行失败，请重试'**
  String get intentExecutionFailed;

  /// No description provided for @intentExecutionFailedWithDetail.
  ///
  /// In zh, this message translates to:
  /// **'执行失败：{error}'**
  String intentExecutionFailedWithDetail(Object error);

  /// No description provided for @intentTypeTaskManagement.
  ///
  /// In zh, this message translates to:
  /// **'任务管理'**
  String get intentTypeTaskManagement;

  /// No description provided for @intentTypeKnowledgeQuery.
  ///
  /// In zh, this message translates to:
  /// **'知识查询'**
  String get intentTypeKnowledgeQuery;

  /// No description provided for @intentTypeTimePlanning.
  ///
  /// In zh, this message translates to:
  /// **'时间规划'**
  String get intentTypeTimePlanning;

  /// No description provided for @intentTypeSocial.
  ///
  /// In zh, this message translates to:
  /// **'社交互动'**
  String get intentTypeSocial;

  /// No description provided for @intentTypeLearning.
  ///
  /// In zh, this message translates to:
  /// **'学习内容'**
  String get intentTypeLearning;

  /// No description provided for @intentTypeReflection.
  ///
  /// In zh, this message translates to:
  /// **'复习反思'**
  String get intentTypeReflection;

  /// No description provided for @intentTypeToolCall.
  ///
  /// In zh, this message translates to:
  /// **'工具调用'**
  String get intentTypeToolCall;

  /// No description provided for @intentTypeUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知'**
  String get intentTypeUnknown;

  /// No description provided for @intentAgentGalaxyGuide.
  ///
  /// In zh, this message translates to:
  /// **'星图向导'**
  String get intentAgentGalaxyGuide;

  /// No description provided for @intentAgentTimeTutor.
  ///
  /// In zh, this message translates to:
  /// **'时间导师'**
  String get intentAgentTimeTutor;

  /// No description provided for @intentAgentExamOracle.
  ///
  /// In zh, this message translates to:
  /// **'考试预言家'**
  String get intentAgentExamOracle;

  /// No description provided for @intentAgentStudyBuddy.
  ///
  /// In zh, this message translates to:
  /// **'学习伙伴'**
  String get intentAgentStudyBuddy;

  /// No description provided for @avatarSelectTitle.
  ///
  /// In zh, this message translates to:
  /// **'选择系统头像'**
  String get avatarSelectTitle;

  /// No description provided for @avatarPresetGeek.
  ///
  /// In zh, this message translates to:
  /// **'极客'**
  String get avatarPresetGeek;

  /// No description provided for @avatarPresetArtist.
  ///
  /// In zh, this message translates to:
  /// **'艺术家'**
  String get avatarPresetArtist;

  /// No description provided for @avatarPresetExplorer.
  ///
  /// In zh, this message translates to:
  /// **'探险家'**
  String get avatarPresetExplorer;

  /// No description provided for @avatarPresetScholar.
  ///
  /// In zh, this message translates to:
  /// **'学者'**
  String get avatarPresetScholar;

  /// No description provided for @avatarPresetEnergy.
  ///
  /// In zh, this message translates to:
  /// **'元气'**
  String get avatarPresetEnergy;

  /// No description provided for @avatarPresetPet.
  ///
  /// In zh, this message translates to:
  /// **'萌友'**
  String get avatarPresetPet;

  /// No description provided for @statisticsWeeklyGrowthTrend.
  ///
  /// In zh, this message translates to:
  /// **'本周成长趋势'**
  String get statisticsWeeklyGrowthTrend;

  /// No description provided for @statisticsLearningIndex.
  ///
  /// In zh, this message translates to:
  /// **'学习指数 {value}'**
  String statisticsLearningIndex(Object value);

  /// No description provided for @learningModeDepthHigh.
  ///
  /// In zh, this message translates to:
  /// **'深度+'**
  String get learningModeDepthHigh;

  /// No description provided for @learningModeDepthLow.
  ///
  /// In zh, this message translates to:
  /// **'深度-'**
  String get learningModeDepthLow;

  /// No description provided for @learningModeCuriosityHigh.
  ///
  /// In zh, this message translates to:
  /// **'好奇+'**
  String get learningModeCuriosityHigh;

  /// No description provided for @learningModeCuriosityLow.
  ///
  /// In zh, this message translates to:
  /// **'好奇-'**
  String get learningModeCuriosityLow;

  /// No description provided for @learningModeDepthValue.
  ///
  /// In zh, this message translates to:
  /// **'深度：{value}%'**
  String learningModeDepthValue(Object value);

  /// No description provided for @learningModeCuriosityValue.
  ///
  /// In zh, this message translates to:
  /// **'好奇：{value}%'**
  String learningModeCuriosityValue(Object value);

  /// No description provided for @learningModeSaved.
  ///
  /// In zh, this message translates to:
  /// **'学习偏好保存成功'**
  String get learningModeSaved;

  /// No description provided for @learningModeSaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存失败：{error}'**
  String learningModeSaveFailed(Object error);

  /// No description provided for @learningModeSettingsTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习模式设置'**
  String get learningModeSettingsTitle;

  /// No description provided for @learningModeDragHint.
  ///
  /// In zh, this message translates to:
  /// **'拖动火苗调整你的学习偏好'**
  String get learningModeDragHint;

  /// No description provided for @learningModeDepthAxisValue.
  ///
  /// In zh, this message translates to:
  /// **'深度偏好（Y轴）：{value}%'**
  String learningModeDepthAxisValue(Object value);

  /// No description provided for @learningModeCuriosityAxisValue.
  ///
  /// In zh, this message translates to:
  /// **'好奇心偏好（X轴）：{value}%'**
  String learningModeCuriosityAxisValue(Object value);

  /// No description provided for @learningModeSave.
  ///
  /// In zh, this message translates to:
  /// **'保存偏好'**
  String get learningModeSave;

  /// No description provided for @notificationReceiveSmartPush.
  ///
  /// In zh, this message translates to:
  /// **'接收智能推送和学习提醒'**
  String get notificationReceiveSmartPush;

  /// No description provided for @schedulePreferencesHint.
  ///
  /// In zh, this message translates to:
  /// **'设置你的碎片时间段，接收主动任务建议。'**
  String get schedulePreferencesHint;

  /// No description provided for @scheduleCommuteTime.
  ///
  /// In zh, this message translates to:
  /// **'通勤时间'**
  String get scheduleCommuteTime;

  /// No description provided for @scheduleLunchBreak.
  ///
  /// In zh, this message translates to:
  /// **'午休时间'**
  String get scheduleLunchBreak;

  /// No description provided for @scheduleStartTime.
  ///
  /// In zh, this message translates to:
  /// **'开始时间'**
  String get scheduleStartTime;

  /// No description provided for @scheduleEndTime.
  ///
  /// In zh, this message translates to:
  /// **'结束时间'**
  String get scheduleEndTime;

  /// No description provided for @schedulePreferencesSaved.
  ///
  /// In zh, this message translates to:
  /// **'偏好已保存'**
  String get schedulePreferencesSaved;

  /// No description provided for @schedulePreferencesSaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存偏好失败：{error}'**
  String schedulePreferencesSaveFailed(Object error);

  /// No description provided for @syncCenterRetryAll.
  ///
  /// In zh, this message translates to:
  /// **'立即重试全部'**
  String get syncCenterRetryAll;

  /// No description provided for @syncCenterRetryAllTriggered.
  ///
  /// In zh, this message translates to:
  /// **'已触发全量重试'**
  String get syncCenterRetryAllTriggered;

  /// No description provided for @syncCenterTabAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get syncCenterTabAll;

  /// No description provided for @syncCenterTabFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get syncCenterTabFailed;

  /// No description provided for @syncCenterTabWaitingAck.
  ///
  /// In zh, this message translates to:
  /// **'等待 ACK'**
  String get syncCenterTabWaitingAck;

  /// No description provided for @syncCenterTabPending.
  ///
  /// In zh, this message translates to:
  /// **'待发送'**
  String get syncCenterTabPending;

  /// No description provided for @syncCenterLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String syncCenterLoadFailed(Object error);

  /// No description provided for @syncCenterCopyDiagnostics.
  ///
  /// In zh, this message translates to:
  /// **'复制诊断信息'**
  String get syncCenterCopyDiagnostics;

  /// No description provided for @syncCenterDiagnosticsCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制诊断信息'**
  String get syncCenterDiagnosticsCopied;

  /// No description provided for @syncCenterDisplayLimit.
  ///
  /// In zh, this message translates to:
  /// **'最多展示 {limit} 条'**
  String syncCenterDisplayLimit(Object limit);

  /// No description provided for @syncCenterRetryFailedTriggered.
  ///
  /// In zh, this message translates to:
  /// **'已触发失败重试'**
  String get syncCenterRetryFailedTriggered;

  /// No description provided for @syncCenterRetryFailed.
  ///
  /// In zh, this message translates to:
  /// **'重试失败项'**
  String get syncCenterRetryFailed;

  /// No description provided for @syncCenterNeverSynced.
  ///
  /// In zh, this message translates to:
  /// **'未同步'**
  String get syncCenterNeverSynced;

  /// No description provided for @syncCenterTotalPending.
  ///
  /// In zh, this message translates to:
  /// **'待同步总数：{count}'**
  String syncCenterTotalPending(Object count);

  /// No description provided for @syncCenterLastSync.
  ///
  /// In zh, this message translates to:
  /// **'最近同步：{value}'**
  String syncCenterLastSync(Object value);

  /// No description provided for @syncCenterByTopic.
  ///
  /// In zh, this message translates to:
  /// **'按主题统计'**
  String get syncCenterByTopic;

  /// No description provided for @syncCenterNoPendingItems.
  ///
  /// In zh, this message translates to:
  /// **'暂无待同步项'**
  String get syncCenterNoPendingItems;

  /// No description provided for @syncCenterTopicLabel.
  ///
  /// In zh, this message translates to:
  /// **'主题'**
  String get syncCenterTopicLabel;

  /// No description provided for @syncCenterTopicAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get syncCenterTopicAll;

  /// No description provided for @syncCenterTopicCognitive.
  ///
  /// In zh, this message translates to:
  /// **'认知碎片'**
  String get syncCenterTopicCognitive;

  /// No description provided for @syncCenterTopicKnowledge.
  ///
  /// In zh, this message translates to:
  /// **'知识图谱'**
  String get syncCenterTopicKnowledge;

  /// No description provided for @syncCenterTopicCollab.
  ///
  /// In zh, this message translates to:
  /// **'协同'**
  String get syncCenterTopicCollab;

  /// No description provided for @syncCenterTopicAnalytics.
  ///
  /// In zh, this message translates to:
  /// **'分析'**
  String get syncCenterTopicAnalytics;

  /// No description provided for @syncCenterTopicLegacy.
  ///
  /// In zh, this message translates to:
  /// **'Legacy'**
  String get syncCenterTopicLegacy;

  /// No description provided for @syncCenterNoRecords.
  ///
  /// In zh, this message translates to:
  /// **'暂无记录'**
  String get syncCenterNoRecords;

  /// No description provided for @syncCenterRetryTriggered.
  ///
  /// In zh, this message translates to:
  /// **'已触发重试'**
  String get syncCenterRetryTriggered;

  /// No description provided for @syncCenterTraceCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制 TraceId'**
  String get syncCenterTraceCopied;

  /// No description provided for @syncCenterEntityCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制实体 ID'**
  String get syncCenterEntityCopied;

  /// No description provided for @syncCenterEntityValue.
  ///
  /// In zh, this message translates to:
  /// **'{entityType}：{entityId}'**
  String syncCenterEntityValue(Object entityId, Object entityType);

  /// No description provided for @syncCenterAttemptValue.
  ///
  /// In zh, this message translates to:
  /// **'重试次数：{count}'**
  String syncCenterAttemptValue(Object count);

  /// No description provided for @syncCenterLastErrorValue.
  ///
  /// In zh, this message translates to:
  /// **'最近错误：{value}'**
  String syncCenterLastErrorValue(Object value);

  /// No description provided for @syncCenterNextAttemptValue.
  ///
  /// In zh, this message translates to:
  /// **'下次重试：{value}'**
  String syncCenterNextAttemptValue(Object value);

  /// No description provided for @syncCenterTraceIdValue.
  ///
  /// In zh, this message translates to:
  /// **'TraceId：{value}'**
  String syncCenterTraceIdValue(Object value);

  /// No description provided for @syncCenterRetryThis.
  ///
  /// In zh, this message translates to:
  /// **'重试此项'**
  String get syncCenterRetryThis;

  /// No description provided for @syncCenterStatusPending.
  ///
  /// In zh, this message translates to:
  /// **'待发送'**
  String get syncCenterStatusPending;

  /// No description provided for @syncCenterStatusFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get syncCenterStatusFailed;

  /// No description provided for @syncCenterStatusWaitingAck.
  ///
  /// In zh, this message translates to:
  /// **'等待 ACK'**
  String get syncCenterStatusWaitingAck;

  /// No description provided for @shareAchievement.
  ///
  /// In zh, this message translates to:
  /// **'分享成就'**
  String get shareAchievement;

  /// No description provided for @sharePreparingCard.
  ///
  /// In zh, this message translates to:
  /// **'正在准备分享卡片...'**
  String get sharePreparingCard;

  /// No description provided for @shareToSocialMedia.
  ///
  /// In zh, this message translates to:
  /// **'分享到社交媒体'**
  String get shareToSocialMedia;

  /// No description provided for @saveToGallery.
  ///
  /// In zh, this message translates to:
  /// **'保存到相册'**
  String get saveToGallery;

  /// No description provided for @close.
  ///
  /// In zh, this message translates to:
  /// **'关闭'**
  String get close;

  /// No description provided for @shareCardGenerateFailed.
  ///
  /// In zh, this message translates to:
  /// **'分享卡生成失败，请稍后重试'**
  String get shareCardGenerateFailed;

  /// No description provided for @shareCardPrepareFailed.
  ///
  /// In zh, this message translates to:
  /// **'分享卡准备失败: {error}'**
  String shareCardPrepareFailed(Object error);

  /// No description provided for @shareFailed.
  ///
  /// In zh, this message translates to:
  /// **'分享失败: {error}'**
  String shareFailed(Object error);

  /// No description provided for @saveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存失败: {error}'**
  String saveFailed(Object error);

  /// No description provided for @savedToGallery.
  ///
  /// In zh, this message translates to:
  /// **'已保存到相册'**
  String get savedToGallery;

  /// No description provided for @shareCardUrlEmpty.
  ///
  /// In zh, this message translates to:
  /// **'分享卡地址为空'**
  String get shareCardUrlEmpty;

  /// No description provided for @shareCardDownloadFailed.
  ///
  /// In zh, this message translates to:
  /// **'下载分享卡失败 ({statusCode})'**
  String shareCardDownloadFailed(Object statusCode);

  /// No description provided for @noGalleryPermission.
  ///
  /// In zh, this message translates to:
  /// **'没有相册写入权限'**
  String get noGalleryPermission;

  /// No description provided for @saveResultEmpty.
  ///
  /// In zh, this message translates to:
  /// **'保存结果为空'**
  String get saveResultEmpty;

  /// No description provided for @gallerySaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存到相册失败'**
  String get gallerySaveFailed;

  /// No description provided for @shareUnlockMessage.
  ///
  /// In zh, this message translates to:
  /// **'我在 Sparkle 解锁了「{achievementName}」'**
  String shareUnlockMessage(Object achievementName);

  /// No description provided for @achievementMilestone.
  ///
  /// In zh, this message translates to:
  /// **'学习里程碑'**
  String get achievementMilestone;

  /// No description provided for @achievementKnowledgePoints.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个知识点'**
  String achievementKnowledgePoints(Object count);

  /// No description provided for @achievementMilestoneDesc.
  ///
  /// In zh, this message translates to:
  /// **'恭喜你已掌握 {count} 个知识点\n知识之光照亮前行之路'**
  String achievementMilestoneDesc(Object count);

  /// No description provided for @achievementStreakRecord.
  ///
  /// In zh, this message translates to:
  /// **'连续学习记录'**
  String get achievementStreakRecord;

  /// No description provided for @achievementStreakDays.
  ///
  /// In zh, this message translates to:
  /// **'{days} 天'**
  String achievementStreakDays(Object days);

  /// No description provided for @achievementStreakDesc.
  ///
  /// In zh, this message translates to:
  /// **'{username} 已连续学习 {days} 天\n坚持的力量无可阻挡！'**
  String achievementStreakDesc(Object days, Object username);

  /// No description provided for @achievementMasteryTitle.
  ///
  /// In zh, this message translates to:
  /// **'领域精通'**
  String get achievementMasteryTitle;

  /// No description provided for @achievementMasteryPercent.
  ///
  /// In zh, this message translates to:
  /// **'{percent}% 掌握度'**
  String achievementMasteryPercent(Object percent);

  /// No description provided for @achievementMasteryDesc.
  ///
  /// In zh, this message translates to:
  /// **'{username} 在 {domain} 领域已达到精通水平\n继续保持！'**
  String achievementMasteryDesc(Object domain, Object username);

  /// No description provided for @achievementTaskComplete.
  ///
  /// In zh, this message translates to:
  /// **'任务圆满完成'**
  String get achievementTaskComplete;

  /// No description provided for @achievementTaskCount.
  ///
  /// In zh, this message translates to:
  /// **'完成 {count} 项任务'**
  String achievementTaskCount(Object count);

  /// No description provided for @achievementTaskDesc.
  ///
  /// In zh, this message translates to:
  /// **'{username} 在本次冲刺中表现卓越\n效率之星实至名归！'**
  String achievementTaskDesc(Object username);

  /// No description provided for @personaGuide.
  ///
  /// In zh, this message translates to:
  /// **'画像引导'**
  String get personaGuide;

  /// No description provided for @personaMyProfile.
  ///
  /// In zh, this message translates to:
  /// **'我的画像'**
  String get personaMyProfile;

  /// No description provided for @personaLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String personaLoadFailed(Object error);

  /// No description provided for @personaL1Title.
  ///
  /// In zh, this message translates to:
  /// **'L1 用户声明'**
  String get personaL1Title;

  /// No description provided for @personaL2Title.
  ///
  /// In zh, this message translates to:
  /// **'L2 协作校准'**
  String get personaL2Title;

  /// No description provided for @personaL3Title.
  ///
  /// In zh, this message translates to:
  /// **'L3 系统推断'**
  String get personaL3Title;

  /// No description provided for @personaL3Hint.
  ///
  /// In zh, this message translates to:
  /// **'以下内容来自系统分析，仅供参考'**
  String get personaL3Hint;

  /// No description provided for @personaPreferences.
  ///
  /// In zh, this message translates to:
  /// **'偏好'**
  String get personaPreferences;

  /// No description provided for @personaGoals.
  ///
  /// In zh, this message translates to:
  /// **'目标'**
  String get personaGoals;

  /// No description provided for @personaTags.
  ///
  /// In zh, this message translates to:
  /// **'标签'**
  String get personaTags;

  /// No description provided for @personaCapabilities.
  ///
  /// In zh, this message translates to:
  /// **'能力'**
  String get personaCapabilities;

  /// No description provided for @personaPatterns.
  ///
  /// In zh, this message translates to:
  /// **'行为模式'**
  String get personaPatterns;

  /// No description provided for @personaFragments.
  ///
  /// In zh, this message translates to:
  /// **'认知碎片'**
  String get personaFragments;

  /// No description provided for @personaNoData.
  ///
  /// In zh, this message translates to:
  /// **'暂无数据'**
  String get personaNoData;

  /// No description provided for @personaCompleted.
  ///
  /// In zh, this message translates to:
  /// **'画像已完善，可随时重新填写'**
  String get personaCompleted;

  /// No description provided for @personaIncomplete.
  ///
  /// In zh, this message translates to:
  /// **'完善画像，提升个性化体验'**
  String get personaIncomplete;

  /// No description provided for @personaRefill.
  ///
  /// In zh, this message translates to:
  /// **'再次填写'**
  String get personaRefill;

  /// No description provided for @personaStart.
  ///
  /// In zh, this message translates to:
  /// **'开始'**
  String get personaStart;

  /// No description provided for @personaLevelEditable.
  ///
  /// In zh, this message translates to:
  /// **'可编辑'**
  String get personaLevelEditable;

  /// No description provided for @personaLevelWarn.
  ///
  /// In zh, this message translates to:
  /// **'建议修正'**
  String get personaLevelWarn;

  /// No description provided for @personaLevelReadonly.
  ///
  /// In zh, this message translates to:
  /// **'只读'**
  String get personaLevelReadonly;

  /// No description provided for @personaConfidence.
  ///
  /// In zh, this message translates to:
  /// **'置信度 {value}'**
  String personaConfidence(Object value);

  /// No description provided for @personaEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑'**
  String get personaEdit;

  /// No description provided for @personaRollback.
  ///
  /// In zh, this message translates to:
  /// **'回滚'**
  String get personaRollback;

  /// No description provided for @personaSuggestCorrection.
  ///
  /// In zh, this message translates to:
  /// **'建议修正'**
  String get personaSuggestCorrection;

  /// No description provided for @personaCorrectionDialogTitle.
  ///
  /// In zh, this message translates to:
  /// **'建议修正'**
  String get personaCorrectionDialogTitle;

  /// No description provided for @personaCorrectionHint.
  ///
  /// In zh, this message translates to:
  /// **'提交后系统会评估并逐步调整画像，可能影响推荐策略。'**
  String get personaCorrectionHint;

  /// No description provided for @personaCorrectionValue.
  ///
  /// In zh, this message translates to:
  /// **'你建议的内容'**
  String get personaCorrectionValue;

  /// No description provided for @personaCorrectionReason.
  ///
  /// In zh, this message translates to:
  /// **'原因（可选）'**
  String get personaCorrectionReason;

  /// No description provided for @personaCorrectionSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'已提交修正建议'**
  String get personaCorrectionSubmitted;

  /// No description provided for @personaEditPreference.
  ///
  /// In zh, this message translates to:
  /// **'编辑偏好'**
  String get personaEditPreference;

  /// No description provided for @personaNewPreferenceValue.
  ///
  /// In zh, this message translates to:
  /// **'新的偏好值'**
  String get personaNewPreferenceValue;

  /// No description provided for @personaPleaseEnterValue.
  ///
  /// In zh, this message translates to:
  /// **'请输入偏好值'**
  String get personaPleaseEnterValue;

  /// No description provided for @personaRollbackTitle.
  ///
  /// In zh, this message translates to:
  /// **'回滚偏好'**
  String get personaRollbackTitle;

  /// No description provided for @personaRollbackConfirm.
  ///
  /// In zh, this message translates to:
  /// **'将偏好回滚到上一个版本，可能影响推荐效果。'**
  String get personaRollbackConfirm;

  /// No description provided for @personaConfirmRollback.
  ///
  /// In zh, this message translates to:
  /// **'确认回滚'**
  String get personaConfirmRollback;

  /// No description provided for @personaEditGoal.
  ///
  /// In zh, this message translates to:
  /// **'编辑目标'**
  String get personaEditGoal;

  /// No description provided for @personaGoalContent.
  ///
  /// In zh, this message translates to:
  /// **'目标内容'**
  String get personaGoalContent;

  /// No description provided for @personaGoalStatus.
  ///
  /// In zh, this message translates to:
  /// **'状态'**
  String get personaGoalStatus;

  /// No description provided for @personaStatusActive.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get personaStatusActive;

  /// No description provided for @personaStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get personaStatusCompleted;

  /// No description provided for @personaStatusPaused.
  ///
  /// In zh, this message translates to:
  /// **'暂停'**
  String get personaStatusPaused;

  /// No description provided for @personaPleaseEnterGoal.
  ///
  /// In zh, this message translates to:
  /// **'请输入目标内容'**
  String get personaPleaseEnterGoal;

  /// No description provided for @personaLearningGoal.
  ///
  /// In zh, this message translates to:
  /// **'学习目标'**
  String get personaLearningGoal;

  /// No description provided for @personaGoalTypeExam.
  ///
  /// In zh, this message translates to:
  /// **'考试'**
  String get personaGoalTypeExam;

  /// No description provided for @personaGoalTypeSkill.
  ///
  /// In zh, this message translates to:
  /// **'技能'**
  String get personaGoalTypeSkill;

  /// No description provided for @personaGoalTypeInterest.
  ///
  /// In zh, this message translates to:
  /// **'兴趣'**
  String get personaGoalTypeInterest;

  /// No description provided for @personaGoalHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：备考期末 / 学会Flutter'**
  String get personaGoalHint;

  /// No description provided for @personaLearningStyle.
  ///
  /// In zh, this message translates to:
  /// **'学习风格'**
  String get personaLearningStyle;

  /// No description provided for @personaStyleBalanced.
  ///
  /// In zh, this message translates to:
  /// **'平衡'**
  String get personaStyleBalanced;

  /// No description provided for @personaStyleVisual.
  ///
  /// In zh, this message translates to:
  /// **'视觉'**
  String get personaStyleVisual;

  /// No description provided for @personaStylePractice.
  ///
  /// In zh, this message translates to:
  /// **'实践'**
  String get personaStylePractice;

  /// No description provided for @personaStyleLogic.
  ///
  /// In zh, this message translates to:
  /// **'逻辑'**
  String get personaStyleLogic;

  /// No description provided for @personaDailyStudyTime.
  ///
  /// In zh, this message translates to:
  /// **'每日学习时长'**
  String get personaDailyStudyTime;

  /// No description provided for @personaMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String personaMinutes(Object minutes);

  /// No description provided for @personaKnowledgeLevel.
  ///
  /// In zh, this message translates to:
  /// **'知识水平'**
  String get personaKnowledgeLevel;

  /// No description provided for @personaLevelBeginner.
  ///
  /// In zh, this message translates to:
  /// **'入门'**
  String get personaLevelBeginner;

  /// No description provided for @personaLevelIntermediate.
  ///
  /// In zh, this message translates to:
  /// **'进阶'**
  String get personaLevelIntermediate;

  /// No description provided for @personaLevelAdvanced.
  ///
  /// In zh, this message translates to:
  /// **'高级'**
  String get personaLevelAdvanced;

  /// No description provided for @personaResponsePreference.
  ///
  /// In zh, this message translates to:
  /// **'回答偏好'**
  String get personaResponsePreference;

  /// No description provided for @personaResponseDepth.
  ///
  /// In zh, this message translates to:
  /// **'回答详细程度'**
  String get personaResponseDepth;

  /// No description provided for @personaCuriosityExtension.
  ///
  /// In zh, this message translates to:
  /// **'好奇心扩展程度'**
  String get personaCuriosityExtension;

  /// No description provided for @personaNextStep.
  ///
  /// In zh, this message translates to:
  /// **'下一步'**
  String get personaNextStep;

  /// No description provided for @personaPreviousStep.
  ///
  /// In zh, this message translates to:
  /// **'上一步'**
  String get personaPreviousStep;

  /// No description provided for @personaComplete.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get personaComplete;

  /// No description provided for @editProfile.
  ///
  /// In zh, this message translates to:
  /// **'编辑资料'**
  String get editProfile;

  /// No description provided for @editProfileSave.
  ///
  /// In zh, this message translates to:
  /// **'保存'**
  String get editProfileSave;

  /// No description provided for @editProfileChangeAvatar.
  ///
  /// In zh, this message translates to:
  /// **'更换头像'**
  String get editProfileChangeAvatar;

  /// No description provided for @editProfileChooseFromPresets.
  ///
  /// In zh, this message translates to:
  /// **'从系统推荐中选择'**
  String get editProfileChooseFromPresets;

  /// No description provided for @editProfileTakePhoto.
  ///
  /// In zh, this message translates to:
  /// **'拍照'**
  String get editProfileTakePhoto;

  /// No description provided for @editProfileChooseFromGallery.
  ///
  /// In zh, this message translates to:
  /// **'从相册选择'**
  String get editProfileChooseFromGallery;

  /// No description provided for @editProfileAvatarUpdated.
  ///
  /// In zh, this message translates to:
  /// **'头像更新成功'**
  String get editProfileAvatarUpdated;

  /// No description provided for @editProfileUpdateFailed.
  ///
  /// In zh, this message translates to:
  /// **'更新失败: {error}'**
  String editProfileUpdateFailed(Object error);

  /// No description provided for @editProfileUploadFailed.
  ///
  /// In zh, this message translates to:
  /// **'上传失败: {error}'**
  String editProfileUploadFailed(Object error);

  /// No description provided for @editProfileNicknameLabel.
  ///
  /// In zh, this message translates to:
  /// **'昵称'**
  String get editProfileNicknameLabel;

  /// No description provided for @editProfileNicknameHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入昵称'**
  String get editProfileNicknameHint;

  /// No description provided for @editProfileNicknameEmpty.
  ///
  /// In zh, this message translates to:
  /// **'昵称不能为空'**
  String get editProfileNicknameEmpty;

  /// No description provided for @editProfileEmailLabel.
  ///
  /// In zh, this message translates to:
  /// **'邮箱'**
  String get editProfileEmailLabel;

  /// No description provided for @editProfileEmailHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入邮箱'**
  String get editProfileEmailHint;

  /// No description provided for @editProfileEmailInvalid.
  ///
  /// In zh, this message translates to:
  /// **'请输入有效的邮箱地址'**
  String get editProfileEmailInvalid;

  /// No description provided for @editProfileUsernameLabel.
  ///
  /// In zh, this message translates to:
  /// **'用户名'**
  String get editProfileUsernameLabel;

  /// No description provided for @editProfileUsernameReadonly.
  ///
  /// In zh, this message translates to:
  /// **'用户名不可修改'**
  String get editProfileUsernameReadonly;

  /// No description provided for @editProfileAccountSecurity.
  ///
  /// In zh, this message translates to:
  /// **'账户安全'**
  String get editProfileAccountSecurity;

  /// No description provided for @editProfileResetPassword.
  ///
  /// In zh, this message translates to:
  /// **'重置密码'**
  String get editProfileResetPassword;

  /// No description provided for @editProfileAccountInfo.
  ///
  /// In zh, this message translates to:
  /// **'账户信息'**
  String get editProfileAccountInfo;

  /// No description provided for @editProfileFlameLevel.
  ///
  /// In zh, this message translates to:
  /// **'火焰等级'**
  String get editProfileFlameLevel;

  /// No description provided for @editProfileFlameBrightness.
  ///
  /// In zh, this message translates to:
  /// **'火焰亮度'**
  String get editProfileFlameBrightness;

  /// No description provided for @editProfileAccountType.
  ///
  /// In zh, this message translates to:
  /// **'账户类型'**
  String get editProfileAccountType;

  /// No description provided for @editProfileGuestAccount.
  ///
  /// In zh, this message translates to:
  /// **'游客账户'**
  String get editProfileGuestAccount;

  /// No description provided for @editProfileFullAccount.
  ///
  /// In zh, this message translates to:
  /// **'正式账户'**
  String get editProfileFullAccount;

  /// No description provided for @editProfileProfileUpdated.
  ///
  /// In zh, this message translates to:
  /// **'资料更新成功'**
  String get editProfileProfileUpdated;

  /// No description provided for @editProfileNewAvatarPending.
  ///
  /// In zh, this message translates to:
  /// **'新头像正在审核中...'**
  String get editProfileNewAvatarPending;

  /// No description provided for @passwordReset.
  ///
  /// In zh, this message translates to:
  /// **'重置密码'**
  String get passwordReset;

  /// No description provided for @passwordResetHint.
  ///
  /// In zh, this message translates to:
  /// **'请确保您的新密码包含至少 8 个字符。'**
  String get passwordResetHint;

  /// No description provided for @passwordResetCurrentLabel.
  ///
  /// In zh, this message translates to:
  /// **'当前密码'**
  String get passwordResetCurrentLabel;

  /// No description provided for @passwordResetCurrentRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入当前密码'**
  String get passwordResetCurrentRequired;

  /// No description provided for @passwordResetNewLabel.
  ///
  /// In zh, this message translates to:
  /// **'新密码'**
  String get passwordResetNewLabel;

  /// No description provided for @passwordResetNewRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入新密码'**
  String get passwordResetNewRequired;

  /// No description provided for @passwordResetNewMinLength.
  ///
  /// In zh, this message translates to:
  /// **'密码长度至少为 8 位'**
  String get passwordResetNewMinLength;

  /// No description provided for @passwordResetConfirmLabel.
  ///
  /// In zh, this message translates to:
  /// **'确认新密码'**
  String get passwordResetConfirmLabel;

  /// No description provided for @passwordResetConfirmMismatch.
  ///
  /// In zh, this message translates to:
  /// **'两次输入的密码不一致'**
  String get passwordResetConfirmMismatch;

  /// No description provided for @passwordResetButton.
  ///
  /// In zh, this message translates to:
  /// **'更新密码'**
  String get passwordResetButton;

  /// No description provided for @passwordResetSuccess.
  ///
  /// In zh, this message translates to:
  /// **'密码修改成功'**
  String get passwordResetSuccess;

  /// No description provided for @passwordResetFailed.
  ///
  /// In zh, this message translates to:
  /// **'修改失败: {error}'**
  String passwordResetFailed(Object error);

  /// No description provided for @smartPushSettings.
  ///
  /// In zh, this message translates to:
  /// **'智能推送设置'**
  String get smartPushSettings;

  /// No description provided for @smartPushPersonaSection.
  ///
  /// In zh, this message translates to:
  /// **'角色设定 (Persona)'**
  String get smartPushPersonaSection;

  /// No description provided for @smartPushFrequencySection.
  ///
  /// In zh, this message translates to:
  /// **'频控设置 (每日上限)'**
  String get smartPushFrequencySection;

  /// No description provided for @smartPushActiveSlotsSection.
  ///
  /// In zh, this message translates to:
  /// **'活跃时间段 (Active Slots)'**
  String get smartPushActiveSlotsSection;

  /// No description provided for @smartPushActiveSlotsHint.
  ///
  /// In zh, this message translates to:
  /// **'仅在这些时间段内发送推送，避开休息时间。'**
  String get smartPushActiveSlotsHint;

  /// No description provided for @smartPushAddTimeSlot.
  ///
  /// In zh, this message translates to:
  /// **'添加时间段'**
  String get smartPushAddTimeSlot;

  /// No description provided for @smartPushTestNotification.
  ///
  /// In zh, this message translates to:
  /// **'发送测试通知 (Dev)'**
  String get smartPushTestNotification;

  /// No description provided for @smartPushTestNotificationSent.
  ///
  /// In zh, this message translates to:
  /// **'测试通知已发送 (需退回桌面查看)'**
  String get smartPushTestNotificationSent;

  /// No description provided for @smartPushPersonaCoach.
  ///
  /// In zh, this message translates to:
  /// **'严厉教练'**
  String get smartPushPersonaCoach;

  /// No description provided for @smartPushPersonaCoachDesc.
  ///
  /// In zh, this message translates to:
  /// **'督促、强调纪律'**
  String get smartPushPersonaCoachDesc;

  /// No description provided for @smartPushPersonaAnime.
  ///
  /// In zh, this message translates to:
  /// **'二次元助手'**
  String get smartPushPersonaAnime;

  /// No description provided for @smartPushPersonaAnimeDesc.
  ///
  /// In zh, this message translates to:
  /// **'温柔、卖萌鼓励'**
  String get smartPushPersonaAnimeDesc;

  /// No description provided for @smartPushFrequencyLabel.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条/天'**
  String smartPushFrequencyLabel(Object count);

  /// No description provided for @smartPushNoSlots.
  ///
  /// In zh, this message translates to:
  /// **'暂无设置，建议添加活跃时间'**
  String get smartPushNoSlots;

  /// No description provided for @smartPushSettingsSaved.
  ///
  /// In zh, this message translates to:
  /// **'设置已保存'**
  String get smartPushSettingsSaved;

  /// No description provided for @smartPushSaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存失败: {error}'**
  String smartPushSaveFailed(Object error);

  /// No description provided for @themeSettings.
  ///
  /// In zh, this message translates to:
  /// **'主题设置'**
  String get themeSettings;

  /// No description provided for @themeModeSection.
  ///
  /// In zh, this message translates to:
  /// **'主题模式'**
  String get themeModeSection;

  /// No description provided for @themeModeLight.
  ///
  /// In zh, this message translates to:
  /// **'浅色'**
  String get themeModeLight;

  /// No description provided for @themeModeDark.
  ///
  /// In zh, this message translates to:
  /// **'深色'**
  String get themeModeDark;

  /// No description provided for @themeModeSystem.
  ///
  /// In zh, this message translates to:
  /// **'跟随系统'**
  String get themeModeSystem;

  /// No description provided for @brandPresetSection.
  ///
  /// In zh, this message translates to:
  /// **'品牌预设'**
  String get brandPresetSection;

  /// No description provided for @highContrastSection.
  ///
  /// In zh, this message translates to:
  /// **'高对比度模式'**
  String get highContrastSection;

  /// No description provided for @highContrastDesc.
  ///
  /// In zh, this message translates to:
  /// **'增强文字和背景的对比度'**
  String get highContrastDesc;

  /// No description provided for @resetDefaults.
  ///
  /// In zh, this message translates to:
  /// **'恢复默认设置'**
  String get resetDefaults;

  /// No description provided for @colorPreviewSection.
  ///
  /// In zh, this message translates to:
  /// **'颜色预览'**
  String get colorPreviewSection;

  /// No description provided for @colorPrimary.
  ///
  /// In zh, this message translates to:
  /// **'主色'**
  String get colorPrimary;

  /// No description provided for @colorSecondary.
  ///
  /// In zh, this message translates to:
  /// **'次色'**
  String get colorSecondary;

  /// No description provided for @colorSuccess.
  ///
  /// In zh, this message translates to:
  /// **'成功'**
  String get colorSuccess;

  /// No description provided for @colorWarning.
  ///
  /// In zh, this message translates to:
  /// **'警告'**
  String get colorWarning;

  /// No description provided for @colorError.
  ///
  /// In zh, this message translates to:
  /// **'错误'**
  String get colorError;

  /// No description provided for @taskTypeColors.
  ///
  /// In zh, this message translates to:
  /// **'任务类型颜色'**
  String get taskTypeColors;

  /// No description provided for @taskTypeLearning.
  ///
  /// In zh, this message translates to:
  /// **'学习'**
  String get taskTypeLearning;

  /// No description provided for @taskTypeTraining.
  ///
  /// In zh, this message translates to:
  /// **'训练'**
  String get taskTypeTraining;

  /// No description provided for @taskTypeFix.
  ///
  /// In zh, this message translates to:
  /// **'修复'**
  String get taskTypeFix;

  /// No description provided for @taskTypeReflection.
  ///
  /// In zh, this message translates to:
  /// **'反思'**
  String get taskTypeReflection;

  /// No description provided for @taskTypeSocial.
  ///
  /// In zh, this message translates to:
  /// **'社交'**
  String get taskTypeSocial;

  /// No description provided for @taskTypePlanning.
  ///
  /// In zh, this message translates to:
  /// **'规划'**
  String get taskTypePlanning;

  /// No description provided for @themeResetSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已恢复为默认设置'**
  String get themeResetSuccess;

  /// No description provided for @systemUpdates.
  ///
  /// In zh, this message translates to:
  /// **'系统活动'**
  String get systemUpdates;

  /// No description provided for @systemUpdatesLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String systemUpdatesLoadFailed(Object error);

  /// No description provided for @systemUpdatesSearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索标题或描述'**
  String get systemUpdatesSearchHint;

  /// No description provided for @systemUpdatesTypeFilter.
  ///
  /// In zh, this message translates to:
  /// **'类型'**
  String get systemUpdatesTypeFilter;

  /// No description provided for @systemUpdatesPriorityFilter.
  ///
  /// In zh, this message translates to:
  /// **'优先级'**
  String get systemUpdatesPriorityFilter;

  /// No description provided for @systemUpdatesCount.
  ///
  /// In zh, this message translates to:
  /// **'共 {count} 条'**
  String systemUpdatesCount(Object count);

  /// No description provided for @systemUpdatesNoItems.
  ///
  /// In zh, this message translates to:
  /// **'暂无系统更新'**
  String get systemUpdatesNoItems;

  /// No description provided for @systemUpdatesAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get systemUpdatesAll;

  /// No description provided for @systemUpdatesConfidence.
  ///
  /// In zh, this message translates to:
  /// **'置信度 {value}%'**
  String systemUpdatesConfidence(Object value);

  /// No description provided for @systemUpdatesNextWeekAdjust.
  ///
  /// In zh, this message translates to:
  /// **'下周继续适配：{value}'**
  String systemUpdatesNextWeekAdjust(Object value);

  /// No description provided for @systemUpdatesBeforeLabel.
  ///
  /// In zh, this message translates to:
  /// **'之前'**
  String get systemUpdatesBeforeLabel;

  /// No description provided for @systemUpdatesAfterLabel.
  ///
  /// In zh, this message translates to:
  /// **'现在'**
  String get systemUpdatesAfterLabel;

  /// No description provided for @systemUpdatesAlignmentScore.
  ///
  /// In zh, this message translates to:
  /// **'画像对齐度 {value}%'**
  String systemUpdatesAlignmentScore(Object value);

  /// No description provided for @contentReviewCardTitle.
  ///
  /// In zh, this message translates to:
  /// **'内容审查'**
  String get contentReviewCardTitle;

  /// No description provided for @contentReviewPassed.
  ///
  /// In zh, this message translates to:
  /// **'内容已通过审查'**
  String get contentReviewPassed;

  /// No description provided for @contentReviewFailed.
  ///
  /// In zh, this message translates to:
  /// **'内容未通过审查'**
  String get contentReviewFailed;

  /// No description provided for @contentReviewNeedsRefinement.
  ///
  /// In zh, this message translates to:
  /// **'内容需要优化'**
  String get contentReviewNeedsRefinement;

  /// No description provided for @contentReviewScoreLabel.
  ///
  /// In zh, this message translates to:
  /// **'评分'**
  String get contentReviewScoreLabel;

  /// No description provided for @contentReviewOverallScore.
  ///
  /// In zh, this message translates to:
  /// **'综合评分'**
  String get contentReviewOverallScore;

  /// No description provided for @contentReviewMetrics.
  ///
  /// In zh, this message translates to:
  /// **'评估指标'**
  String get contentReviewMetrics;

  /// No description provided for @contentReviewIssues.
  ///
  /// In zh, this message translates to:
  /// **'发现问题'**
  String get contentReviewIssues;

  /// No description provided for @contentReviewSuggestions.
  ///
  /// In zh, this message translates to:
  /// **'改进建议'**
  String get contentReviewSuggestions;

  /// No description provided for @contentReviewCriticalIssues.
  ///
  /// In zh, this message translates to:
  /// **'严重问题'**
  String get contentReviewCriticalIssues;

  /// No description provided for @contentReviewWarnings.
  ///
  /// In zh, this message translates to:
  /// **'警告'**
  String get contentReviewWarnings;

  /// No description provided for @contentReviewTips.
  ///
  /// In zh, this message translates to:
  /// **'提示'**
  String get contentReviewTips;

  /// No description provided for @contentReviewAccept.
  ///
  /// In zh, this message translates to:
  /// **'接受'**
  String get contentReviewAccept;

  /// No description provided for @contentReviewReject.
  ///
  /// In zh, this message translates to:
  /// **'拒绝'**
  String get contentReviewReject;

  /// No description provided for @contentReviewRequestManual.
  ///
  /// In zh, this message translates to:
  /// **'人工审查'**
  String get contentReviewRequestManual;

  /// No description provided for @contentReviewRegenerate.
  ///
  /// In zh, this message translates to:
  /// **'重新生成'**
  String get contentReviewRegenerate;

  /// No description provided for @contentReviewWaitOptimization.
  ///
  /// In zh, this message translates to:
  /// **'等待优化...'**
  String get contentReviewWaitOptimization;

  /// No description provided for @contentReviewOptimizing.
  ///
  /// In zh, this message translates to:
  /// **'正在优化内容...'**
  String get contentReviewOptimizing;

  /// No description provided for @contentReviewOptimized.
  ///
  /// In zh, this message translates to:
  /// **'优化完成'**
  String get contentReviewOptimized;

  /// No description provided for @contentReviewOptimizationFailed.
  ///
  /// In zh, this message translates to:
  /// **'优化失败'**
  String get contentReviewOptimizationFailed;

  /// No description provided for @contentReviewProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中...'**
  String get contentReviewProcessing;

  /// No description provided for @contentReviewAgreePassed.
  ///
  /// In zh, this message translates to:
  /// **'我认为应该通过'**
  String get contentReviewAgreePassed;

  /// No description provided for @contentReviewDisagreePassed.
  ///
  /// In zh, this message translates to:
  /// **'我不同意这个结果'**
  String get contentReviewDisagreePassed;

  /// No description provided for @contentReviewReportProblem.
  ///
  /// In zh, this message translates to:
  /// **'报告审查问题'**
  String get contentReviewReportProblem;

  /// No description provided for @contentReviewOverrideDialogTitle.
  ///
  /// In zh, this message translates to:
  /// **'覆盖审查决策'**
  String get contentReviewOverrideDialogTitle;

  /// No description provided for @contentReviewDisagreeWithResult.
  ///
  /// In zh, this message translates to:
  /// **'我不同意这个审查结果'**
  String get contentReviewDisagreeWithResult;

  /// No description provided for @contentReviewAgreeShouldPass.
  ///
  /// In zh, this message translates to:
  /// **'我认为内容应该通过审查'**
  String get contentReviewAgreeShouldPass;

  /// No description provided for @contentReviewReasonHint.
  ///
  /// In zh, this message translates to:
  /// **'输入您的理由...'**
  String get contentReviewReasonHint;

  /// No description provided for @contentReviewReasonRequired.
  ///
  /// In zh, this message translates to:
  /// **'请填写理由'**
  String get contentReviewReasonRequired;

  /// No description provided for @contentReviewAppealDialogTitle.
  ///
  /// In zh, this message translates to:
  /// **'报告审查问题'**
  String get contentReviewAppealDialogTitle;

  /// No description provided for @contentReviewSelectIssuesHint.
  ///
  /// In zh, this message translates to:
  /// **'选择问题类型（可多选）'**
  String get contentReviewSelectIssuesHint;

  /// No description provided for @contentReviewDetailHint.
  ///
  /// In zh, this message translates to:
  /// **'详细说明： '**
  String get contentReviewDetailHint;

  /// No description provided for @contentReviewDetailPlaceholder.
  ///
  /// In zh, this message translates to:
  /// **'请描述审查结果存在的问题...'**
  String get contentReviewDetailPlaceholder;

  /// No description provided for @contentReviewDetailRequired.
  ///
  /// In zh, this message translates to:
  /// **'请填写详细说明'**
  String get contentReviewDetailRequired;

  /// No description provided for @contentReviewSelectAtLeastOne.
  ///
  /// In zh, this message translates to:
  /// **'请至少选择一个问题类型'**
  String get contentReviewSelectAtLeastOne;

  /// No description provided for @contentReviewIssueUnfairStandards.
  ///
  /// In zh, this message translates to:
  /// **'审查标准不合理'**
  String get contentReviewIssueUnfairStandards;

  /// No description provided for @contentReviewIssueScoreCalculation.
  ///
  /// In zh, this message translates to:
  /// **'评分计算有误'**
  String get contentReviewIssueScoreCalculation;

  /// No description provided for @contentReviewIssueMissingContext.
  ///
  /// In zh, this message translates to:
  /// **'忽略了重要上下文'**
  String get contentReviewIssueMissingContext;

  /// No description provided for @contentReviewIssueInaccurateDescription.
  ///
  /// In zh, this message translates to:
  /// **'问题描述不准确'**
  String get contentReviewIssueInaccurateDescription;

  /// No description provided for @contentReviewIssueUnfeasibleSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'建议不可行'**
  String get contentReviewIssueUnfeasibleSuggestion;

  /// No description provided for @contentReviewMetricAccuracy.
  ///
  /// In zh, this message translates to:
  /// **'准确性'**
  String get contentReviewMetricAccuracy;

  /// No description provided for @contentReviewMetricCompleteness.
  ///
  /// In zh, this message translates to:
  /// **'完整性'**
  String get contentReviewMetricCompleteness;

  /// No description provided for @contentReviewMetricRelevance.
  ///
  /// In zh, this message translates to:
  /// **'相关性'**
  String get contentReviewMetricRelevance;

  /// No description provided for @contentReviewMetricClarity.
  ///
  /// In zh, this message translates to:
  /// **'清晰度'**
  String get contentReviewMetricClarity;

  /// No description provided for @contentReviewMetricSafety.
  ///
  /// In zh, this message translates to:
  /// **'安全性'**
  String get contentReviewMetricSafety;

  /// No description provided for @contentReviewMetricFeasibility.
  ///
  /// In zh, this message translates to:
  /// **'可行性'**
  String get contentReviewMetricFeasibility;

  /// No description provided for @contentReviewMetricEfficiency.
  ///
  /// In zh, this message translates to:
  /// **'效率性'**
  String get contentReviewMetricEfficiency;

  /// No description provided for @contentReviewMetricHelpfulness.
  ///
  /// In zh, this message translates to:
  /// **'有用性'**
  String get contentReviewMetricHelpfulness;

  /// No description provided for @contentReviewMetricTone.
  ///
  /// In zh, this message translates to:
  /// **'语气适当'**
  String get contentReviewMetricTone;

  /// No description provided for @contentReviewScoreExcellent.
  ///
  /// In zh, this message translates to:
  /// **'优秀'**
  String get contentReviewScoreExcellent;

  /// No description provided for @contentReviewScoreGood.
  ///
  /// In zh, this message translates to:
  /// **'良好'**
  String get contentReviewScoreGood;

  /// No description provided for @contentReviewScorePass.
  ///
  /// In zh, this message translates to:
  /// **'及格'**
  String get contentReviewScorePass;

  /// No description provided for @contentReviewScoreNeedsWork.
  ///
  /// In zh, this message translates to:
  /// **'需改进'**
  String get contentReviewScoreNeedsWork;

  /// No description provided for @contentReviewSeverityCritical.
  ///
  /// In zh, this message translates to:
  /// **'严重'**
  String get contentReviewSeverityCritical;

  /// No description provided for @contentReviewSeverityWarning.
  ///
  /// In zh, this message translates to:
  /// **'警告'**
  String get contentReviewSeverityWarning;

  /// No description provided for @contentReviewSeverityInfo.
  ///
  /// In zh, this message translates to:
  /// **'提示'**
  String get contentReviewSeverityInfo;

  /// No description provided for @contentReviewHints.
  ///
  /// In zh, this message translates to:
  /// **'提示'**
  String get contentReviewHints;

  /// No description provided for @contentReviewSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'建议: {suggestion}'**
  String contentReviewSuggestion(Object suggestion);

  /// No description provided for @contentReviewSuggestionDesc.
  ///
  /// In zh, this message translates to:
  /// **'建议'**
  String get contentReviewSuggestionDesc;

  /// No description provided for @contentReviewReflectionPending.
  ///
  /// In zh, this message translates to:
  /// **'等待优化...'**
  String get contentReviewReflectionPending;

  /// No description provided for @contentReviewReflectionInProgress.
  ///
  /// In zh, this message translates to:
  /// **'正在优化内容...'**
  String get contentReviewReflectionInProgress;

  /// No description provided for @contentReviewReflectionCompleted.
  ///
  /// In zh, this message translates to:
  /// **'优化完成'**
  String get contentReviewReflectionCompleted;

  /// No description provided for @contentReviewReflectionFailed.
  ///
  /// In zh, this message translates to:
  /// **'优化失败'**
  String get contentReviewReflectionFailed;

  /// No description provided for @contentReviewReflectionProcessing.
  ///
  /// In zh, this message translates to:
  /// **'反思处理中...'**
  String get contentReviewReflectionProcessing;

  /// No description provided for @contentReviewReflectionPendingShort.
  ///
  /// In zh, this message translates to:
  /// **'等待优化'**
  String get contentReviewReflectionPendingShort;

  /// No description provided for @contentReviewReflectionInProgressShort.
  ///
  /// In zh, this message translates to:
  /// **'优化中...'**
  String get contentReviewReflectionInProgressShort;

  /// No description provided for @contentReviewReflectionCompletedShort.
  ///
  /// In zh, this message translates to:
  /// **'已优化'**
  String get contentReviewReflectionCompletedShort;

  /// No description provided for @contentReviewReflectionFailedShort.
  ///
  /// In zh, this message translates to:
  /// **'优化失败'**
  String get contentReviewReflectionFailedShort;

  /// No description provided for @contentReviewReflectionProcessingShort.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get contentReviewReflectionProcessingShort;

  /// No description provided for @contentReviewManualReview.
  ///
  /// In zh, this message translates to:
  /// **'人工审查'**
  String get contentReviewManualReview;

  /// No description provided for @contentReviewDisagreePass.
  ///
  /// In zh, this message translates to:
  /// **'不同意通过'**
  String get contentReviewDisagreePass;

  /// No description provided for @contentReviewAgreePass.
  ///
  /// In zh, this message translates to:
  /// **'我认为应该通过'**
  String get contentReviewAgreePass;

  /// No description provided for @contentReviewReportIssue.
  ///
  /// In zh, this message translates to:
  /// **'报告审查问题'**
  String get contentReviewReportIssue;

  /// No description provided for @contentReviewDisagreePassTitle.
  ///
  /// In zh, this message translates to:
  /// **'不同意审查通过'**
  String get contentReviewDisagreePassTitle;

  /// No description provided for @contentReviewAgreePassTitle.
  ///
  /// In zh, this message translates to:
  /// **'我认为内容应该通过审查'**
  String get contentReviewAgreePassTitle;

  /// No description provided for @contentReviewReasonPrompt.
  ///
  /// In zh, this message translates to:
  /// **'请说明您的理由：'**
  String get contentReviewReasonPrompt;

  /// No description provided for @contentReviewCancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get contentReviewCancel;

  /// No description provided for @contentReviewConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认'**
  String get contentReviewConfirm;

  /// No description provided for @contentReviewAppealSelectType.
  ///
  /// In zh, this message translates to:
  /// **'选择问题类型：'**
  String get contentReviewAppealSelectType;

  /// No description provided for @contentReviewAppealDetail.
  ///
  /// In zh, this message translates to:
  /// **'详细说明：'**
  String get contentReviewAppealDetail;

  /// No description provided for @contentReviewAppealDetailHint.
  ///
  /// In zh, this message translates to:
  /// **'请描述审查结果存在的问题...'**
  String get contentReviewAppealDetailHint;

  /// No description provided for @contentReviewAppealDetailRequired.
  ///
  /// In zh, this message translates to:
  /// **'请填写详细说明'**
  String get contentReviewAppealDetailRequired;

  /// No description provided for @contentReviewAppealTypeRequired.
  ///
  /// In zh, this message translates to:
  /// **'请至少选择一个问题类型'**
  String get contentReviewAppealTypeRequired;

  /// No description provided for @contentReviewAppealUnreasonableStandard.
  ///
  /// In zh, this message translates to:
  /// **'审查标准不合理'**
  String get contentReviewAppealUnreasonableStandard;

  /// No description provided for @contentReviewAppealScoreError.
  ///
  /// In zh, this message translates to:
  /// **'评分计算有误'**
  String get contentReviewAppealScoreError;

  /// No description provided for @contentReviewAppealContextIgnored.
  ///
  /// In zh, this message translates to:
  /// **'忽略了重要上下文'**
  String get contentReviewAppealContextIgnored;

  /// No description provided for @contentReviewAppealDescriptionInaccurate.
  ///
  /// In zh, this message translates to:
  /// **'问题描述不准确'**
  String get contentReviewAppealDescriptionInaccurate;

  /// No description provided for @contentReviewAppealSuggestionNotFeasible.
  ///
  /// In zh, this message translates to:
  /// **'建议不可行'**
  String get contentReviewAppealSuggestionNotFeasible;

  /// No description provided for @contentReviewAppealSubmit.
  ///
  /// In zh, this message translates to:
  /// **'提交申诉'**
  String get contentReviewAppealSubmit;

  /// No description provided for @commonSubmitting.
  ///
  /// In zh, this message translates to:
  /// **'提交中...'**
  String get commonSubmitting;

  /// No description provided for @brandPresetSparkle.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle'**
  String get brandPresetSparkle;

  /// No description provided for @brandPresetOcean.
  ///
  /// In zh, this message translates to:
  /// **'Ocean'**
  String get brandPresetOcean;

  /// No description provided for @brandPresetForest.
  ///
  /// In zh, this message translates to:
  /// **'Forest'**
  String get brandPresetForest;

  /// No description provided for @smartPushDebugTitle.
  ///
  /// In zh, this message translates to:
  /// **'调试：记忆临界点'**
  String get smartPushDebugTitle;

  /// No description provided for @smartPushDebugBody.
  ///
  /// In zh, this message translates to:
  /// **'你的 [线性代数] 正在遗忘，点击立即复习！'**
  String get smartPushDebugBody;

  /// No description provided for @reviewAppealPendingTitle.
  ///
  /// In zh, this message translates to:
  /// **'申诉待处理'**
  String get reviewAppealPendingTitle;

  /// No description provided for @reviewAppealPendingDesc.
  ///
  /// In zh, this message translates to:
  /// **'你的申诉已提交，正在等待处理。'**
  String get reviewAppealPendingDesc;

  /// No description provided for @reviewAppealInReviewTitle.
  ///
  /// In zh, this message translates to:
  /// **'二次审查中'**
  String get reviewAppealInReviewTitle;

  /// No description provided for @reviewAppealInReviewDesc.
  ///
  /// In zh, this message translates to:
  /// **'系统正在使用不同模型进行二次审查。'**
  String get reviewAppealInReviewDesc;

  /// No description provided for @reviewAppealResolvedTitle.
  ///
  /// In zh, this message translates to:
  /// **'申诉已通过'**
  String get reviewAppealResolvedTitle;

  /// No description provided for @reviewAppealResolvedDesc.
  ///
  /// In zh, this message translates to:
  /// **'申诉已通过，原审查结果已更新。'**
  String get reviewAppealResolvedDesc;

  /// No description provided for @reviewAppealRejectedTitle.
  ///
  /// In zh, this message translates to:
  /// **'申诉已拒绝'**
  String get reviewAppealRejectedTitle;

  /// No description provided for @reviewAppealRejectedDesc.
  ///
  /// In zh, this message translates to:
  /// **'申诉被拒绝，维持原审查结果。'**
  String get reviewAppealRejectedDesc;

  /// No description provided for @reviewAppealEscalatedTitle.
  ///
  /// In zh, this message translates to:
  /// **'已升级人工处理'**
  String get reviewAppealEscalatedTitle;

  /// No description provided for @reviewAppealEscalatedDesc.
  ///
  /// In zh, this message translates to:
  /// **'需要人工审核，请耐心等待。'**
  String get reviewAppealEscalatedDesc;

  /// No description provided for @reviewAppealId.
  ///
  /// In zh, this message translates to:
  /// **'申诉 #{id}'**
  String reviewAppealId(Object id);

  /// No description provided for @reviewAppealTimelineSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'提交申诉'**
  String get reviewAppealTimelineSubmitted;

  /// No description provided for @reviewAppealTimelineReviewed.
  ///
  /// In zh, this message translates to:
  /// **'二次审查完成'**
  String get reviewAppealTimelineReviewed;

  /// No description provided for @reviewAppealTimelineApproved.
  ///
  /// In zh, this message translates to:
  /// **'申诉通过'**
  String get reviewAppealTimelineApproved;

  /// No description provided for @reviewAppealTimelineRejected.
  ///
  /// In zh, this message translates to:
  /// **'申诉拒绝'**
  String get reviewAppealTimelineRejected;

  /// No description provided for @reviewAppealScore.
  ///
  /// In zh, this message translates to:
  /// **'评分：{value}%'**
  String reviewAppealScore(Object value);

  /// No description provided for @reviewAppealSecondaryScore.
  ///
  /// In zh, this message translates to:
  /// **'二次审查评分：{value}%'**
  String reviewAppealSecondaryScore(Object value);

  /// No description provided for @reviewAppealMinReason.
  ///
  /// In zh, this message translates to:
  /// **'请提供更详细的说明（至少 10 个字符）'**
  String get reviewAppealMinReason;

  /// No description provided for @reviewAppealOtherIssue.
  ///
  /// In zh, this message translates to:
  /// **'其他问题'**
  String get reviewAppealOtherIssue;

  /// No description provided for @transparencySettingsTitle.
  ///
  /// In zh, this message translates to:
  /// **'透明模式设置'**
  String get transparencySettingsTitle;

  /// No description provided for @transparencyEnable.
  ///
  /// In zh, this message translates to:
  /// **'启用透明模式'**
  String get transparencyEnable;

  /// No description provided for @transparencyEnableDesc.
  ///
  /// In zh, this message translates to:
  /// **'显示 AI 处理步骤、Agent 切换和 Token 使用情况。'**
  String get transparencyEnableDesc;

  /// No description provided for @transparencyDisplayOptions.
  ///
  /// In zh, this message translates to:
  /// **'显示选项'**
  String get transparencyDisplayOptions;

  /// No description provided for @transparencyTokenUsage.
  ///
  /// In zh, this message translates to:
  /// **'Token 使用情况'**
  String get transparencyTokenUsage;

  /// No description provided for @transparencyTokenUsageDesc.
  ///
  /// In zh, this message translates to:
  /// **'显示每次对话的 Token 消耗和成本估算。'**
  String get transparencyTokenUsageDesc;

  /// No description provided for @transparencyAgentSwitching.
  ///
  /// In zh, this message translates to:
  /// **'Agent 切换'**
  String get transparencyAgentSwitching;

  /// No description provided for @transparencyAgentSwitchingDesc.
  ///
  /// In zh, this message translates to:
  /// **'显示不同 Agent 之间的切换过程。'**
  String get transparencyAgentSwitchingDesc;

  /// No description provided for @transparencyReasoningSteps.
  ///
  /// In zh, this message translates to:
  /// **'推理步骤'**
  String get transparencyReasoningSteps;

  /// No description provided for @transparencyReasoningStepsDesc.
  ///
  /// In zh, this message translates to:
  /// **'显示模型的详细推理过程。'**
  String get transparencyReasoningStepsDesc;

  /// No description provided for @transparencyWarning.
  ///
  /// In zh, this message translates to:
  /// **'启用详细透明选项可能会略微增加响应延迟。'**
  String get transparencyWarning;

  /// No description provided for @transparencyLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载设置失败'**
  String get transparencyLoadFailed;

  /// No description provided for @nightlyReviewPending.
  ///
  /// In zh, this message translates to:
  /// **'今日复盘待完成'**
  String get nightlyReviewPending;

  /// No description provided for @nightlyReviewStart.
  ///
  /// In zh, this message translates to:
  /// **'开始'**
  String get nightlyReviewStart;

  /// No description provided for @thoughtCapsuleTitle.
  ///
  /// In zh, this message translates to:
  /// **'闪念胶囊'**
  String get thoughtCapsuleTitle;

  /// No description provided for @thoughtCapsulePrompt.
  ///
  /// In zh, this message translates to:
  /// **'此刻是什么拦住了你？或者有什么想吐槽的？'**
  String get thoughtCapsulePrompt;

  /// No description provided for @thoughtCapsuleHint.
  ///
  /// In zh, this message translates to:
  /// **'输入你的想法...'**
  String get thoughtCapsuleHint;

  /// No description provided for @thoughtCapsuleCaptured.
  ///
  /// In zh, this message translates to:
  /// **'闪念已捕捉'**
  String get thoughtCapsuleCaptured;

  /// No description provided for @thoughtCapsuleCaptureFailed.
  ///
  /// In zh, this message translates to:
  /// **'捕捉失败：{error}'**
  String thoughtCapsuleCaptureFailed(Object error);

  /// No description provided for @leaderboardTitle.
  ///
  /// In zh, this message translates to:
  /// **'排行榜'**
  String get leaderboardTitle;

  /// No description provided for @leaderboardGlobal.
  ///
  /// In zh, this message translates to:
  /// **'全局榜'**
  String get leaderboardGlobal;

  /// No description provided for @leaderboardFriends.
  ///
  /// In zh, this message translates to:
  /// **'好友榜'**
  String get leaderboardFriends;

  /// No description provided for @leaderboardGroup.
  ///
  /// In zh, this message translates to:
  /// **'群组榜'**
  String get leaderboardGroup;

  /// No description provided for @leaderboardSubject.
  ///
  /// In zh, this message translates to:
  /// **'学科榜'**
  String get leaderboardSubject;

  /// No description provided for @leaderboardWeekly.
  ///
  /// In zh, this message translates to:
  /// **'本周榜'**
  String get leaderboardWeekly;

  /// No description provided for @leaderboardStreak.
  ///
  /// In zh, this message translates to:
  /// **'连胜榜'**
  String get leaderboardStreak;

  /// No description provided for @leaderboardMyRank.
  ///
  /// In zh, this message translates to:
  /// **'我的排名：{rank}'**
  String leaderboardMyRank(int rank);

  /// No description provided for @leaderboardPoints.
  ///
  /// In zh, this message translates to:
  /// **'{value}分'**
  String leaderboardPoints(int value);

  /// No description provided for @leaderboardNoData.
  ///
  /// In zh, this message translates to:
  /// **'暂无{label}数据'**
  String leaderboardNoData(Object label);

  /// No description provided for @leaderboardLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'排行榜加载失败，请重试'**
  String get leaderboardLoadFailed;

  /// No description provided for @omnibarListeningHint.
  ///
  /// In zh, this message translates to:
  /// **'正在聆听...'**
  String get omnibarListeningHint;

  /// No description provided for @omnibarDefaultHint.
  ///
  /// In zh, this message translates to:
  /// **'告诉我你现在在想什么...'**
  String get omnibarDefaultHint;

  /// No description provided for @voiceInputAction.
  ///
  /// In zh, this message translates to:
  /// **'语音输入'**
  String get voiceInputAction;

  /// No description provided for @voiceInputStopAction.
  ///
  /// In zh, this message translates to:
  /// **'停止录音'**
  String get voiceInputStopAction;

  /// No description provided for @voiceInputSpeechFailed.
  ///
  /// In zh, this message translates to:
  /// **'语音识别失败：{error}'**
  String voiceInputSpeechFailed(Object error);

  /// No description provided for @sendFailedWithError.
  ///
  /// In zh, this message translates to:
  /// **'发送失败：{error}'**
  String sendFailedWithError(Object error);

  /// No description provided for @submitFailedWithError.
  ///
  /// In zh, this message translates to:
  /// **'提交失败：{error}'**
  String submitFailedWithError(Object error);

  /// No description provided for @loadingFailedWithError.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String loadingFailedWithError(Object error);

  /// No description provided for @delete.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get delete;

  /// No description provided for @blockingReasonEfficiency.
  ///
  /// In zh, this message translates to:
  /// **'高估了自己的效率'**
  String get blockingReasonEfficiency;

  /// No description provided for @blockingReasonInterrupted.
  ///
  /// In zh, this message translates to:
  /// **'中途被消息打断'**
  String get blockingReasonInterrupted;

  /// No description provided for @blockingReasonPerfectionism.
  ///
  /// In zh, this message translates to:
  /// **'追求完美导致卡壳'**
  String get blockingReasonPerfectionism;

  /// No description provided for @blockingReasonTooHard.
  ///
  /// In zh, this message translates to:
  /// **'任务太难，不知道怎么开始'**
  String get blockingReasonTooHard;

  /// No description provided for @blockingReasonNoMood.
  ///
  /// In zh, this message translates to:
  /// **'心情不好，不想做'**
  String get blockingReasonNoMood;

  /// No description provided for @blockingSelectReason.
  ///
  /// In zh, this message translates to:
  /// **'请选择原因或输入想法'**
  String get blockingSelectReason;

  /// No description provided for @blockingTitle.
  ///
  /// In zh, this message translates to:
  /// **'遇到阻碍了吗？'**
  String get blockingTitle;

  /// No description provided for @blockingDescription.
  ///
  /// In zh, this message translates to:
  /// **'记录下原因，AI 会帮你分析行为定式，下次做得更好。'**
  String get blockingDescription;

  /// No description provided for @blockingOtherReason.
  ///
  /// In zh, this message translates to:
  /// **'其他原因...'**
  String get blockingOtherReason;

  /// No description provided for @blockingReasonHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入具体原因'**
  String get blockingReasonHint;

  /// No description provided for @blockingConfirmAbandon.
  ///
  /// In zh, this message translates to:
  /// **'确认放弃'**
  String get blockingConfirmAbandon;

  /// No description provided for @subtaskAddHint.
  ///
  /// In zh, this message translates to:
  /// **'添加子任务...'**
  String get subtaskAddHint;

  /// No description provided for @subtaskAddTooltip.
  ///
  /// In zh, this message translates to:
  /// **'添加子任务'**
  String get subtaskAddTooltip;

  /// No description provided for @subtaskEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无子任务'**
  String get subtaskEmpty;

  /// No description provided for @subtaskTitle.
  ///
  /// In zh, this message translates to:
  /// **'子任务'**
  String get subtaskTitle;

  /// No description provided for @taskFeedbackSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'反馈已提交'**
  String get taskFeedbackSubmitted;

  /// No description provided for @taskFeedbackPreferenceUpdated.
  ///
  /// In zh, this message translates to:
  /// **'偏好已更新'**
  String get taskFeedbackPreferenceUpdated;

  /// No description provided for @taskFeedbackView.
  ///
  /// In zh, this message translates to:
  /// **'查看'**
  String get taskFeedbackView;

  /// No description provided for @taskFeedbackPreferenceDialogTitle.
  ///
  /// In zh, this message translates to:
  /// **'偏好更新'**
  String get taskFeedbackPreferenceDialogTitle;

  /// No description provided for @taskFeedbackDepthPreference.
  ///
  /// In zh, this message translates to:
  /// **'深度偏好：{value}'**
  String taskFeedbackDepthPreference(Object value);

  /// No description provided for @taskFeedbackDifficultyPreference.
  ///
  /// In zh, this message translates to:
  /// **'难度偏好：{value}'**
  String taskFeedbackDifficultyPreference(Object value);

  /// No description provided for @taskFeedbackPreferenceDialogDesc.
  ///
  /// In zh, this message translates to:
  /// **'这些偏好将用于个性化推荐你的下一步学习内容。'**
  String get taskFeedbackPreferenceDialogDesc;

  /// No description provided for @taskFeedbackGotIt.
  ///
  /// In zh, this message translates to:
  /// **'知道了'**
  String get taskFeedbackGotIt;

  /// No description provided for @taskFeedbackCompletedTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务完成！'**
  String get taskFeedbackCompletedTitle;

  /// No description provided for @taskFeedbackCompletedSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'任务已完成，继续保持。'**
  String get taskFeedbackCompletedSubtitle;

  /// No description provided for @taskFeedbackBrightness.
  ///
  /// In zh, this message translates to:
  /// **'亮度'**
  String get taskFeedbackBrightness;

  /// No description provided for @taskFeedbackStreak.
  ///
  /// In zh, this message translates to:
  /// **'连胜'**
  String get taskFeedbackStreak;

  /// No description provided for @taskFeedbackStreakDays.
  ///
  /// In zh, this message translates to:
  /// **'{count}天'**
  String taskFeedbackStreakDays(int count);

  /// No description provided for @taskFeedbackOptionalRating.
  ///
  /// In zh, this message translates to:
  /// **'满意度评分（选填）'**
  String get taskFeedbackOptionalRating;

  /// No description provided for @taskFeedbackDifficultyQuestion.
  ///
  /// In zh, this message translates to:
  /// **'这次的难度感觉怎么样？'**
  String get taskFeedbackDifficultyQuestion;

  /// No description provided for @taskFeedbackCategoryJustRight.
  ///
  /// In zh, this message translates to:
  /// **'刚好'**
  String get taskFeedbackCategoryJustRight;

  /// No description provided for @taskFeedbackCategoryStillHard.
  ///
  /// In zh, this message translates to:
  /// **'还是难'**
  String get taskFeedbackCategoryStillHard;

  /// No description provided for @taskFeedbackCategoryTooEasy.
  ///
  /// In zh, this message translates to:
  /// **'太简单'**
  String get taskFeedbackCategoryTooEasy;

  /// No description provided for @taskFeedbackOptionalComment.
  ///
  /// In zh, this message translates to:
  /// **'有什么想说的？（选填）'**
  String get taskFeedbackOptionalComment;

  /// No description provided for @taskFeedbackCommentHint.
  ///
  /// In zh, this message translates to:
  /// **'记录一些心得...'**
  String get taskFeedbackCommentHint;

  /// No description provided for @taskFeedbackNextSteps.
  ///
  /// In zh, this message translates to:
  /// **'下一步建议'**
  String get taskFeedbackNextSteps;

  /// No description provided for @taskFeedbackSkip.
  ///
  /// In zh, this message translates to:
  /// **'跳过'**
  String get taskFeedbackSkip;

  /// No description provided for @taskFeedbackComplete.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get taskFeedbackComplete;

  /// No description provided for @taskFeedbackReason.
  ///
  /// In zh, this message translates to:
  /// **'理由：{reason}'**
  String taskFeedbackReason(Object reason);

  /// No description provided for @communityQuote.
  ///
  /// In zh, this message translates to:
  /// **'引用'**
  String get communityQuote;

  /// No description provided for @communityCopy.
  ///
  /// In zh, this message translates to:
  /// **'复制'**
  String get communityCopy;

  /// No description provided for @communityCopiedToClipboard.
  ///
  /// In zh, this message translates to:
  /// **'已复制到剪贴板'**
  String get communityCopiedToClipboard;

  /// No description provided for @communityThreadReply.
  ///
  /// In zh, this message translates to:
  /// **'串联回复'**
  String get communityThreadReply;

  /// No description provided for @communityEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑'**
  String get communityEdit;

  /// No description provided for @communityRevoke.
  ///
  /// In zh, this message translates to:
  /// **'撤回'**
  String get communityRevoke;

  /// No description provided for @communityRevokedOwnMessage.
  ///
  /// In zh, this message translates to:
  /// **'你撤回了一条消息'**
  String get communityRevokedOwnMessage;

  /// No description provided for @communityRevokedUserMessage.
  ///
  /// In zh, this message translates to:
  /// **'{sender}撤回了一条消息'**
  String communityRevokedUserMessage(Object sender);

  /// No description provided for @communityMemberFallback.
  ///
  /// In zh, this message translates to:
  /// **'成员'**
  String get communityMemberFallback;

  /// No description provided for @communityReadByCount.
  ///
  /// In zh, this message translates to:
  /// **'{count}人已读'**
  String communityReadByCount(int count);

  /// No description provided for @communityQuotedMessageFallback.
  ///
  /// In zh, this message translates to:
  /// **'引用的消息'**
  String get communityQuotedMessageFallback;

  /// No description provided for @communityDailyCheckIn.
  ///
  /// In zh, this message translates to:
  /// **'每日打卡'**
  String get communityDailyCheckIn;

  /// No description provided for @communityDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'时长'**
  String get communityDurationLabel;

  /// No description provided for @communityFlameLabel.
  ///
  /// In zh, this message translates to:
  /// **'火花'**
  String get communityFlameLabel;

  /// No description provided for @communityStreakLabel.
  ///
  /// In zh, this message translates to:
  /// **'连胜'**
  String get communityStreakLabel;

  /// No description provided for @communitySharedTask.
  ///
  /// In zh, this message translates to:
  /// **'分享了一个任务'**
  String get communitySharedTask;

  /// No description provided for @shareResourceTitle.
  ///
  /// In zh, this message translates to:
  /// **'分享到社群'**
  String get shareResourceTitle;

  /// No description provided for @shareResourceTabFriends.
  ///
  /// In zh, this message translates to:
  /// **'好友'**
  String get shareResourceTabFriends;

  /// No description provided for @shareResourceTabGroups.
  ///
  /// In zh, this message translates to:
  /// **'群组'**
  String get shareResourceTabGroups;

  /// No description provided for @shareResourceCommentHint.
  ///
  /// In zh, this message translates to:
  /// **'添加分享留言（可选）'**
  String get shareResourceCommentHint;

  /// No description provided for @shareResourceNow.
  ///
  /// In zh, this message translates to:
  /// **'立即分享'**
  String get shareResourceNow;

  /// No description provided for @shareResourceNoFriends.
  ///
  /// In zh, this message translates to:
  /// **'暂无好友'**
  String get shareResourceNoFriends;

  /// No description provided for @shareResourceNoGroups.
  ///
  /// In zh, this message translates to:
  /// **'暂无群组'**
  String get shareResourceNoGroups;

  /// No description provided for @shareResourceGroupMembers.
  ///
  /// In zh, this message translates to:
  /// **'{count}名成员'**
  String shareResourceGroupMembers(int count);

  /// No description provided for @shareResourceSelectTarget.
  ///
  /// In zh, this message translates to:
  /// **'请选择好友或群组'**
  String get shareResourceSelectTarget;

  /// No description provided for @shareResourceSuccess.
  ///
  /// In zh, this message translates to:
  /// **'分享成功'**
  String get shareResourceSuccess;

  /// No description provided for @shareResourceFailed.
  ///
  /// In zh, this message translates to:
  /// **'分享失败：{error}'**
  String shareResourceFailed(Object error);

  /// No description provided for @shareTypeNotSupportedYet.
  ///
  /// In zh, this message translates to:
  /// **'该类型暂不支持分享到社群，请使用图片分享'**
  String get shareTypeNotSupportedYet;

  /// No description provided for @threadDiscussion.
  ///
  /// In zh, this message translates to:
  /// **'线程讨论'**
  String get threadDiscussion;

  /// No description provided for @threadReplyHint.
  ///
  /// In zh, this message translates to:
  /// **'回复线程...'**
  String get threadReplyHint;

  /// No description provided for @calendarSetDueDateTitle.
  ///
  /// In zh, this message translates to:
  /// **'设置任务截止日期'**
  String get calendarSetDueDateTitle;

  /// No description provided for @calendarSetDueDateMessage.
  ///
  /// In zh, this message translates to:
  /// **'将“{task}”设为 {date} 到期？'**
  String calendarSetDueDateMessage(Object task, Object date);

  /// No description provided for @calendarTitle.
  ///
  /// In zh, this message translates to:
  /// **'日程与日历'**
  String get calendarTitle;

  /// No description provided for @calendarMonthView.
  ///
  /// In zh, this message translates to:
  /// **'月视图'**
  String get calendarMonthView;

  /// No description provided for @calendarTwoWeekView.
  ///
  /// In zh, this message translates to:
  /// **'双周'**
  String get calendarTwoWeekView;

  /// No description provided for @calendarYearView.
  ///
  /// In zh, this message translates to:
  /// **'年视图'**
  String get calendarYearView;

  /// No description provided for @calendarDayScheduleTitle.
  ///
  /// In zh, this message translates to:
  /// **'{date} 日程'**
  String calendarDayScheduleTitle(Object date);

  /// No description provided for @calendarViewDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看详情'**
  String get calendarViewDetails;

  /// No description provided for @calendarNoEvents.
  ///
  /// In zh, this message translates to:
  /// **'暂无日程'**
  String get calendarNoEvents;

  /// No description provided for @calendarAllDay.
  ///
  /// In zh, this message translates to:
  /// **'全天'**
  String get calendarAllDay;

  /// No description provided for @calendarCreateEvent.
  ///
  /// In zh, this message translates to:
  /// **'新建日程'**
  String get calendarCreateEvent;

  /// No description provided for @calendarSave.
  ///
  /// In zh, this message translates to:
  /// **'保存'**
  String get calendarSave;

  /// No description provided for @calendarTitleHint.
  ///
  /// In zh, this message translates to:
  /// **'标题'**
  String get calendarTitleHint;

  /// No description provided for @calendarLocationHint.
  ///
  /// In zh, this message translates to:
  /// **'地点'**
  String get calendarLocationHint;

  /// No description provided for @calendarDescriptionHint.
  ///
  /// In zh, this message translates to:
  /// **'描述'**
  String get calendarDescriptionHint;

  /// No description provided for @calendarStartTime.
  ///
  /// In zh, this message translates to:
  /// **'开始时间'**
  String get calendarStartTime;

  /// No description provided for @calendarEndTime.
  ///
  /// In zh, this message translates to:
  /// **'结束时间'**
  String get calendarEndTime;

  /// No description provided for @calendarReminder.
  ///
  /// In zh, this message translates to:
  /// **'提醒'**
  String get calendarReminder;

  /// No description provided for @calendarReminderAtStart.
  ///
  /// In zh, this message translates to:
  /// **'日程开始时'**
  String get calendarReminderAtStart;

  /// No description provided for @calendarReminderMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count}分钟前'**
  String calendarReminderMinutes(int count);

  /// No description provided for @calendarReminderHours.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时前'**
  String calendarReminderHours(int count);

  /// No description provided for @calendarReminderDays.
  ///
  /// In zh, this message translates to:
  /// **'{count}天前'**
  String calendarReminderDays(int count);

  /// No description provided for @calendarRepeat.
  ///
  /// In zh, this message translates to:
  /// **'重复'**
  String get calendarRepeat;

  /// No description provided for @calendarRepeatNone.
  ///
  /// In zh, this message translates to:
  /// **'不重复'**
  String get calendarRepeatNone;

  /// No description provided for @calendarRepeatDaily.
  ///
  /// In zh, this message translates to:
  /// **'每天'**
  String get calendarRepeatDaily;

  /// No description provided for @calendarRepeatWeekly.
  ///
  /// In zh, this message translates to:
  /// **'每周'**
  String get calendarRepeatWeekly;

  /// No description provided for @calendarRepeatMonthly.
  ///
  /// In zh, this message translates to:
  /// **'每月'**
  String get calendarRepeatMonthly;

  /// No description provided for @calendarTitleRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入标题'**
  String get calendarTitleRequired;

  /// No description provided for @dailyDetailEventsSection.
  ///
  /// In zh, this message translates to:
  /// **'日程事件'**
  String get dailyDetailEventsSection;

  /// No description provided for @dailyDetailTasksSection.
  ///
  /// In zh, this message translates to:
  /// **'任务清单'**
  String get dailyDetailTasksSection;

  /// No description provided for @dailyDetailFlame.
  ///
  /// In zh, this message translates to:
  /// **'火花强度'**
  String get dailyDetailFlame;

  /// No description provided for @dailyDetailFocusTime.
  ///
  /// In zh, this message translates to:
  /// **'专注时长'**
  String get dailyDetailFocusTime;

  /// No description provided for @dailyDetailTasksDone.
  ///
  /// In zh, this message translates to:
  /// **'完成任务'**
  String get dailyDetailTasksDone;

  /// No description provided for @dailyDetailPrismTitle.
  ///
  /// In zh, this message translates to:
  /// **'当日认知棱镜'**
  String get dailyDetailPrismTitle;

  /// No description provided for @dailyDetailPrismFallback.
  ///
  /// In zh, this message translates to:
  /// **'今日思维清晰，状态良好'**
  String get dailyDetailPrismFallback;

  /// No description provided for @dailyDetailNoTasks.
  ///
  /// In zh, this message translates to:
  /// **'暂无任务'**
  String get dailyDetailNoTasks;

  /// No description provided for @onboardingSkip.
  ///
  /// In zh, this message translates to:
  /// **'跳过'**
  String get onboardingSkip;

  /// No description provided for @onboardingGetStarted.
  ///
  /// In zh, this message translates to:
  /// **'开始使用'**
  String get onboardingGetStarted;

  /// No description provided for @onboardingNext.
  ///
  /// In zh, this message translates to:
  /// **'下一步'**
  String get onboardingNext;

  /// No description provided for @onboardingWelcomeTitle.
  ///
  /// In zh, this message translates to:
  /// **'欢迎来到 Sparkle'**
  String get onboardingWelcomeTitle;

  /// No description provided for @onboardingWelcomeSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'你的 AI 学习助手\n让知识点亮智慧之光'**
  String get onboardingWelcomeSubtitle;

  /// No description provided for @onboardingFeatureGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'知识星图'**
  String get onboardingFeatureGalaxy;

  /// No description provided for @onboardingFeatureGalaxyDesc.
  ///
  /// In zh, this message translates to:
  /// **'可视化学习网络'**
  String get onboardingFeatureGalaxyDesc;

  /// No description provided for @onboardingFeatureChat.
  ///
  /// In zh, this message translates to:
  /// **'AI 对话'**
  String get onboardingFeatureChat;

  /// No description provided for @onboardingFeatureChatDesc.
  ///
  /// In zh, this message translates to:
  /// **'智能学习伙伴'**
  String get onboardingFeatureChatDesc;

  /// No description provided for @onboardingFeatureTasks.
  ///
  /// In zh, this message translates to:
  /// **'智能任务'**
  String get onboardingFeatureTasks;

  /// No description provided for @onboardingFeatureTasksDesc.
  ///
  /// In zh, this message translates to:
  /// **'个性化学习计划'**
  String get onboardingFeatureTasksDesc;

  /// No description provided for @onboardingArchitectureTitle.
  ///
  /// In zh, this message translates to:
  /// **'系统架构'**
  String get onboardingArchitectureTitle;

  /// No description provided for @onboardingArchitectureSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'了解 Sparkle 如何工作'**
  String get onboardingArchitectureSubtitle;

  /// No description provided for @onboardingGalaxyTitle.
  ///
  /// In zh, this message translates to:
  /// **'知识星图'**
  String get onboardingGalaxyTitle;

  /// No description provided for @onboardingGalaxyDescription.
  ///
  /// In zh, this message translates to:
  /// **'将你的知识可视化为一张星图'**
  String get onboardingGalaxyDescription;

  /// No description provided for @onboardingGalaxyFeature1.
  ///
  /// In zh, this message translates to:
  /// **'6大知识星域：理性、造物、灵感、文明、生活、精神'**
  String get onboardingGalaxyFeature1;

  /// No description provided for @onboardingGalaxyFeature2.
  ///
  /// In zh, this message translates to:
  /// **'实时衰减预测：了解知识遗忘曲线'**
  String get onboardingGalaxyFeature2;

  /// No description provided for @onboardingGalaxyFeature3.
  ///
  /// In zh, this message translates to:
  /// **'交互式时间机器：预测未来学习状态'**
  String get onboardingGalaxyFeature3;

  /// No description provided for @onboardingGalaxyFeature4.
  ///
  /// In zh, this message translates to:
  /// **'智能推荐：基于知识图谱的学习路径'**
  String get onboardingGalaxyFeature4;

  /// No description provided for @onboardingChatTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 对话'**
  String get onboardingChatTitle;

  /// No description provided for @onboardingChatDescription.
  ///
  /// In zh, this message translates to:
  /// **'你的智能学习伙伴'**
  String get onboardingChatDescription;

  /// No description provided for @onboardingChatFeature1.
  ///
  /// In zh, this message translates to:
  /// **'多智能体协作：数学、代码、写作、科学专家'**
  String get onboardingChatFeature1;

  /// No description provided for @onboardingChatFeature2.
  ///
  /// In zh, this message translates to:
  /// **'GraphRAG 检索：实时显示知识检索过程'**
  String get onboardingChatFeature2;

  /// No description provided for @onboardingChatFeature3.
  ///
  /// In zh, this message translates to:
  /// **'上下文理解：记住你的学习历史'**
  String get onboardingChatFeature3;

  /// No description provided for @onboardingChatFeature4.
  ///
  /// In zh, this message translates to:
  /// **'工具调用：执行任务、查询知识、管理计划'**
  String get onboardingChatFeature4;

  /// No description provided for @onboardingTasksTitle.
  ///
  /// In zh, this message translates to:
  /// **'智能任务'**
  String get onboardingTasksTitle;

  /// No description provided for @onboardingTasksDescription.
  ///
  /// In zh, this message translates to:
  /// **'个性化学习计划'**
  String get onboardingTasksDescription;

  /// No description provided for @onboardingTasksFeature1.
  ///
  /// In zh, this message translates to:
  /// **'6种任务类型：学习、训练、纠错、反思、社交、规划'**
  String get onboardingTasksFeature1;

  /// No description provided for @onboardingTasksFeature2.
  ///
  /// In zh, this message translates to:
  /// **'智能推送：基于学习状态的提醒'**
  String get onboardingTasksFeature2;

  /// No description provided for @onboardingTasksFeature3.
  ///
  /// In zh, this message translates to:
  /// **'Sprint 计划：短期冲刺目标'**
  String get onboardingTasksFeature3;

  /// No description provided for @onboardingTasksFeature4.
  ///
  /// In zh, this message translates to:
  /// **'Growth Plan：长期成长规划'**
  String get onboardingTasksFeature4;

  /// No description provided for @onboardingPersonalizationTitle.
  ///
  /// In zh, this message translates to:
  /// **'个性化设置'**
  String get onboardingPersonalizationTitle;

  /// No description provided for @onboardingPersonalizationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'让 Sparkle 更懂你'**
  String get onboardingPersonalizationSubtitle;

  /// No description provided for @onboardingSettingReminders.
  ///
  /// In zh, this message translates to:
  /// **'学习提醒'**
  String get onboardingSettingReminders;

  /// No description provided for @onboardingSettingRemindersDesc.
  ///
  /// In zh, this message translates to:
  /// **'在最佳时间推送学习建议'**
  String get onboardingSettingRemindersDesc;

  /// No description provided for @onboardingSettingAnalytics.
  ///
  /// In zh, this message translates to:
  /// **'学习分析'**
  String get onboardingSettingAnalytics;

  /// No description provided for @onboardingSettingAnalyticsDesc.
  ///
  /// In zh, this message translates to:
  /// **'生成个性化学习报告'**
  String get onboardingSettingAnalyticsDesc;

  /// No description provided for @onboardingSettingAssistant.
  ///
  /// In zh, this message translates to:
  /// **'AI 助手'**
  String get onboardingSettingAssistant;

  /// No description provided for @onboardingSettingAssistantDesc.
  ///
  /// In zh, this message translates to:
  /// **'自动创建学习任务'**
  String get onboardingSettingAssistantDesc;

  /// No description provided for @onboardingChatDemo1.
  ///
  /// In zh, this message translates to:
  /// **'你好！我能帮你什么？'**
  String get onboardingChatDemo1;

  /// No description provided for @onboardingChatDemo2.
  ///
  /// In zh, this message translates to:
  /// **'解释一下微积分的基本原理'**
  String get onboardingChatDemo2;

  /// No description provided for @onboardingChatDemo3.
  ///
  /// In zh, this message translates to:
  /// **'微积分研究函数的变化率...'**
  String get onboardingChatDemo3;

  /// No description provided for @onboardingTaskTypeLearning.
  ///
  /// In zh, this message translates to:
  /// **'学习任务'**
  String get onboardingTaskTypeLearning;

  /// No description provided for @onboardingTaskTypePractice.
  ///
  /// In zh, this message translates to:
  /// **'训练任务'**
  String get onboardingTaskTypePractice;

  /// No description provided for @onboardingTaskTypeReflection.
  ///
  /// In zh, this message translates to:
  /// **'反思任务'**
  String get onboardingTaskTypeReflection;

  /// No description provided for @onboardingTaskDemo1.
  ///
  /// In zh, this message translates to:
  /// **'完成微积分第一章'**
  String get onboardingTaskDemo1;

  /// No description provided for @onboardingTaskDemo2.
  ///
  /// In zh, this message translates to:
  /// **'完成10道练习题'**
  String get onboardingTaskDemo2;

  /// No description provided for @onboardingTaskDemo3.
  ///
  /// In zh, this message translates to:
  /// **'总结本周学习收获'**
  String get onboardingTaskDemo3;

  /// No description provided for @onboardingArchitectureStep1Title.
  ///
  /// In zh, this message translates to:
  /// **'移动端'**
  String get onboardingArchitectureStep1Title;

  /// No description provided for @onboardingArchitectureStep1Desc.
  ///
  /// In zh, this message translates to:
  /// **'Flutter 跨平台应用\n提供流畅的用户体验'**
  String get onboardingArchitectureStep1Desc;

  /// No description provided for @onboardingArchitectureStep2Title.
  ///
  /// In zh, this message translates to:
  /// **'WebSocket 连接'**
  String get onboardingArchitectureStep2Title;

  /// No description provided for @onboardingArchitectureStep2Desc.
  ///
  /// In zh, this message translates to:
  /// **'Go Gateway 提供实时双向通信\n高性能、低延迟'**
  String get onboardingArchitectureStep2Desc;

  /// No description provided for @onboardingArchitectureStep3Title.
  ///
  /// In zh, this message translates to:
  /// **'AI 引擎'**
  String get onboardingArchitectureStep3Title;

  /// No description provided for @onboardingArchitectureStep3Desc.
  ///
  /// In zh, this message translates to:
  /// **'Python Agent Engine\n强大的推理和工具调用能力'**
  String get onboardingArchitectureStep3Desc;

  /// No description provided for @onboardingArchitectureStep4Title.
  ///
  /// In zh, this message translates to:
  /// **'数据存储'**
  String get onboardingArchitectureStep4Title;

  /// No description provided for @onboardingArchitectureStep4Desc.
  ///
  /// In zh, this message translates to:
  /// **'PostgreSQL + pgvector\n向量检索 + 图谱存储'**
  String get onboardingArchitectureStep4Desc;

  /// No description provided for @onboardingArchitectureStep5Title.
  ///
  /// In zh, this message translates to:
  /// **'完整链路'**
  String get onboardingArchitectureStep5Title;

  /// No description provided for @onboardingArchitectureStep5Desc.
  ///
  /// In zh, this message translates to:
  /// **'从提问到回答\n毫秒级响应体验'**
  String get onboardingArchitectureStep5Desc;

  /// No description provided for @capsuleQualityUnrated.
  ///
  /// In zh, this message translates to:
  /// **'未评级'**
  String get capsuleQualityUnrated;

  /// No description provided for @capsuleQualityExcellent.
  ///
  /// In zh, this message translates to:
  /// **'优秀'**
  String get capsuleQualityExcellent;

  /// No description provided for @capsuleQualityGood.
  ///
  /// In zh, this message translates to:
  /// **'良好'**
  String get capsuleQualityGood;

  /// No description provided for @capsuleQualityFair.
  ///
  /// In zh, this message translates to:
  /// **'一般'**
  String get capsuleQualityFair;

  /// No description provided for @capsuleQualityNeedsWork.
  ///
  /// In zh, this message translates to:
  /// **'待改进'**
  String get capsuleQualityNeedsWork;

  /// No description provided for @capsuleJobStatusPending.
  ///
  /// In zh, this message translates to:
  /// **'等待中'**
  String get capsuleJobStatusPending;

  /// No description provided for @capsuleJobStatusGenerating.
  ///
  /// In zh, this message translates to:
  /// **'生成中'**
  String get capsuleJobStatusGenerating;

  /// No description provided for @capsuleJobStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get capsuleJobStatusCompleted;

  /// No description provided for @capsuleJobStatusFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get capsuleJobStatusFailed;

  /// No description provided for @capsuleGenerationTypeDaily.
  ///
  /// In zh, this message translates to:
  /// **'每日胶囊'**
  String get capsuleGenerationTypeDaily;

  /// No description provided for @capsuleGenerationTypeWeekly.
  ///
  /// In zh, this message translates to:
  /// **'每周胶囊'**
  String get capsuleGenerationTypeWeekly;

  /// No description provided for @capsuleGenerationTypeManual.
  ///
  /// In zh, this message translates to:
  /// **'手动生成'**
  String get capsuleGenerationTypeManual;

  /// No description provided for @capsuleGenerationTypePushTriggered.
  ///
  /// In zh, this message translates to:
  /// **'推送触发'**
  String get capsuleGenerationTypePushTriggered;

  /// No description provided for @capsuleFeedbackTooLong.
  ///
  /// In zh, this message translates to:
  /// **'太长了'**
  String get capsuleFeedbackTooLong;

  /// No description provided for @capsuleFeedbackTooShort.
  ///
  /// In zh, this message translates to:
  /// **'太短了'**
  String get capsuleFeedbackTooShort;

  /// No description provided for @capsuleFeedbackJustRight.
  ///
  /// In zh, this message translates to:
  /// **'刚刚好'**
  String get capsuleFeedbackJustRight;

  /// No description provided for @capsuleFeedbackTooComplex.
  ///
  /// In zh, this message translates to:
  /// **'太复杂'**
  String get capsuleFeedbackTooComplex;

  /// No description provided for @capsuleFeedbackTooSimple.
  ///
  /// In zh, this message translates to:
  /// **'太简单'**
  String get capsuleFeedbackTooSimple;

  /// No description provided for @capsuleFeedbackIrrelevant.
  ///
  /// In zh, this message translates to:
  /// **'不相关'**
  String get capsuleFeedbackIrrelevant;

  /// No description provided for @capsuleFeedbackOther.
  ///
  /// In zh, this message translates to:
  /// **'其他'**
  String get capsuleFeedbackOther;

  /// No description provided for @capsuleFeedbackCategoryLabel.
  ///
  /// In zh, this message translates to:
  /// **'想让我们改进哪一点？'**
  String get capsuleFeedbackCategoryLabel;

  /// No description provided for @capsuleDepthShallow.
  ///
  /// In zh, this message translates to:
  /// **'浅度'**
  String get capsuleDepthShallow;

  /// No description provided for @capsuleDepthMedium.
  ///
  /// In zh, this message translates to:
  /// **'中度'**
  String get capsuleDepthMedium;

  /// No description provided for @capsuleDepthDeep.
  ///
  /// In zh, this message translates to:
  /// **'深度'**
  String get capsuleDepthDeep;

  /// No description provided for @capsulePersonalizationTitle.
  ///
  /// In zh, this message translates to:
  /// **'为什么推荐给你'**
  String get capsulePersonalizationTitle;

  /// No description provided for @capsulePersonalizationBadge.
  ///
  /// In zh, this message translates to:
  /// **'基于你的{pattern}模式'**
  String capsulePersonalizationBadge(String pattern);

  /// No description provided for @capsulePersonalizationExplanation.
  ///
  /// In zh, this message translates to:
  /// **'基于你最近的{patterns}行为模式，AI为你精选了这个知识点。'**
  String capsulePersonalizationExplanation(String patterns);

  /// No description provided for @patternPlanningOptimism.
  ///
  /// In zh, this message translates to:
  /// **'计划乐观偏差'**
  String get patternPlanningOptimism;

  /// No description provided for @patternFocusDecay.
  ///
  /// In zh, this message translates to:
  /// **'专注力衰减'**
  String get patternFocusDecay;

  /// No description provided for @patternProcrastination.
  ///
  /// In zh, this message translates to:
  /// **'拖延倾向'**
  String get patternProcrastination;

  /// No description provided for @cognitiveSelectGalaxyNodes.
  ///
  /// In zh, this message translates to:
  /// **'请先在 Galaxy 中选择要复习的节点'**
  String get cognitiveSelectGalaxyNodes;

  /// No description provided for @cognitiveTimeMachine.
  ///
  /// In zh, this message translates to:
  /// **'知识时光机'**
  String get cognitiveTimeMachine;

  /// No description provided for @cognitiveFutureDays.
  ///
  /// In zh, this message translates to:
  /// **'未来 {count} 天'**
  String cognitiveFutureDays(int count);

  /// No description provided for @cognitiveDaysLater.
  ///
  /// In zh, this message translates to:
  /// **'{count} 天后'**
  String cognitiveDaysLater(int count);

  /// No description provided for @cognitiveToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get cognitiveToday;

  /// No description provided for @cognitiveDayTick.
  ///
  /// In zh, this message translates to:
  /// **'{count}天'**
  String cognitiveDayTick(int count);

  /// No description provided for @cognitiveHealthy.
  ///
  /// In zh, this message translates to:
  /// **'健康'**
  String get cognitiveHealthy;

  /// No description provided for @cognitiveDecaying.
  ///
  /// In zh, this message translates to:
  /// **'衰减中'**
  String get cognitiveDecaying;

  /// No description provided for @cognitiveRisk.
  ///
  /// In zh, this message translates to:
  /// **'危险'**
  String get cognitiveRisk;

  /// No description provided for @cognitiveSimulating.
  ///
  /// In zh, this message translates to:
  /// **'模拟中...'**
  String get cognitiveSimulating;

  /// No description provided for @cognitiveReviewNow.
  ///
  /// In zh, this message translates to:
  /// **'如果现在复习？（{count} 个节点）'**
  String cognitiveReviewNow(int count);

  /// No description provided for @prismCognitivePatterns.
  ///
  /// In zh, this message translates to:
  /// **'认知模式'**
  String get prismCognitivePatterns;

  /// No description provided for @prismEmotionalPatterns.
  ///
  /// In zh, this message translates to:
  /// **'情绪模式'**
  String get prismEmotionalPatterns;

  /// No description provided for @prismExecutionPatterns.
  ///
  /// In zh, this message translates to:
  /// **'执行模式'**
  String get prismExecutionPatterns;

  /// No description provided for @prismTitle.
  ///
  /// In zh, this message translates to:
  /// **'认知棱镜'**
  String get prismTitle;

  /// No description provided for @prismNoData.
  ///
  /// In zh, this message translates to:
  /// **'暂无行为模式数据'**
  String get prismNoData;

  /// No description provided for @prismHint.
  ///
  /// In zh, this message translates to:
  /// **'继续学习和复盘后，认知棱镜会越来越准确地识别你的学习模式。'**
  String get prismHint;

  /// No description provided for @prismTotalPatterns.
  ///
  /// In zh, this message translates to:
  /// **'共 {count} 个模式'**
  String prismTotalPatterns(int count);

  /// No description provided for @capsuleScreenTitle.
  ///
  /// In zh, this message translates to:
  /// **'好奇心胶囊'**
  String get capsuleScreenTitle;

  /// No description provided for @capsuleCurrentTab.
  ///
  /// In zh, this message translates to:
  /// **'当前胶囊 {count}'**
  String capsuleCurrentTab(int count);

  /// No description provided for @capsuleArchiveTab.
  ///
  /// In zh, this message translates to:
  /// **'历史归档 {count}'**
  String capsuleArchiveTab(int count);

  /// No description provided for @capsuleArchiveEmpty.
  ///
  /// In zh, this message translates to:
  /// **'还没有归档胶囊'**
  String get capsuleArchiveEmpty;

  /// No description provided for @capsuleEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'今天还没有新的好奇心胶囊'**
  String get capsuleEmptyTitle;

  /// No description provided for @capsuleEmptySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'继续学习，激发更多灵感吧！'**
  String get capsuleEmptySubtitle;

  /// No description provided for @capsuleGenerationPreviewTitle.
  ///
  /// In zh, this message translates to:
  /// **'生成预览'**
  String get capsuleGenerationPreviewTitle;

  /// No description provided for @capsuleGenerationPreviewCountLabel.
  ///
  /// In zh, this message translates to:
  /// **'预计生成'**
  String get capsuleGenerationPreviewCountLabel;

  /// No description provided for @capsuleGenerationPreviewCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个胶囊'**
  String capsuleGenerationPreviewCount(int count);

  /// No description provided for @capsuleGenerationPreviewDepthLabel.
  ///
  /// In zh, this message translates to:
  /// **'深度级别'**
  String get capsuleGenerationPreviewDepthLabel;

  /// No description provided for @capsuleGenerationPreviewModelLabel.
  ///
  /// In zh, this message translates to:
  /// **'使用模型'**
  String get capsuleGenerationPreviewModelLabel;

  /// No description provided for @patternCardSolutionLabel.
  ///
  /// In zh, this message translates to:
  /// **'破解咒语'**
  String get patternCardSolutionLabel;

  /// No description provided for @patternCardCreatedAt.
  ///
  /// In zh, this message translates to:
  /// **'创建于：{date}'**
  String patternCardCreatedAt(String date);

  /// No description provided for @capsuleDetailTitle.
  ///
  /// In zh, this message translates to:
  /// **'胶囊详情'**
  String get capsuleDetailTitle;

  /// No description provided for @capsuleMissing.
  ///
  /// In zh, this message translates to:
  /// **'胶囊不存在'**
  String get capsuleMissing;

  /// No description provided for @capsuleLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String capsuleLoadFailed(String error);

  /// No description provided for @capsuleQualityLabel.
  ///
  /// In zh, this message translates to:
  /// **'质量评分：{rating}'**
  String capsuleQualityLabel(String rating);

  /// No description provided for @capsuleFeedbackCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 反馈'**
  String capsuleFeedbackCount(int count);

  /// No description provided for @capsuleShareCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 分享'**
  String capsuleShareCount(int count);

  /// No description provided for @capsuleSubmitFeedback.
  ///
  /// In zh, this message translates to:
  /// **'提交反馈'**
  String get capsuleSubmitFeedback;

  /// No description provided for @capsuleShare.
  ///
  /// In zh, this message translates to:
  /// **'分享胶囊'**
  String get capsuleShare;

  /// No description provided for @capsuleCopyLink.
  ///
  /// In zh, this message translates to:
  /// **'复制链接'**
  String get capsuleCopyLink;

  /// No description provided for @capsuleShareToGroup.
  ///
  /// In zh, this message translates to:
  /// **'分享到群组'**
  String get capsuleShareToGroup;

  /// No description provided for @capsuleRateFirst.
  ///
  /// In zh, this message translates to:
  /// **'请先评分'**
  String get capsuleRateFirst;

  /// No description provided for @capsuleFeedbackThanks.
  ///
  /// In zh, this message translates to:
  /// **'感谢你的反馈'**
  String get capsuleFeedbackThanks;

  /// No description provided for @capsuleSubmitFailed.
  ///
  /// In zh, this message translates to:
  /// **'提交失败：{error}'**
  String capsuleSubmitFailed(String error);

  /// No description provided for @capsuleFeedbackQuestion.
  ///
  /// In zh, this message translates to:
  /// **'这个胶囊对你有帮助吗？'**
  String get capsuleFeedbackQuestion;

  /// No description provided for @capsuleFeedbackHint.
  ///
  /// In zh, this message translates to:
  /// **'说说你的想法（可选）'**
  String get capsuleFeedbackHint;

  /// No description provided for @capsuleSubmit.
  ///
  /// In zh, this message translates to:
  /// **'提交'**
  String get capsuleSubmit;

  /// No description provided for @capsuleJobsTitle.
  ///
  /// In zh, this message translates to:
  /// **'生成任务'**
  String get capsuleJobsTitle;

  /// No description provided for @capsuleNoJobs.
  ///
  /// In zh, this message translates to:
  /// **'还没有生成任务'**
  String get capsuleNoJobs;

  /// No description provided for @capsuleNoJobsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'在设置页面调整偏好并生成胶囊'**
  String get capsuleNoJobsSubtitle;

  /// No description provided for @capsuleGeneratingProgress.
  ///
  /// In zh, this message translates to:
  /// **'生成中... {progress}%'**
  String capsuleGeneratingProgress(int progress);

  /// No description provided for @capsuleDepthPercent.
  ///
  /// In zh, this message translates to:
  /// **'深度：{percent}%'**
  String capsuleDepthPercent(int percent);

  /// No description provided for @capsuleCuriosityPercent.
  ///
  /// In zh, this message translates to:
  /// **'好奇：{percent}%'**
  String capsuleCuriosityPercent(int percent);

  /// No description provided for @capsuleRequestedCount.
  ///
  /// In zh, this message translates to:
  /// **'请求数量：{count}'**
  String capsuleRequestedCount(int count);

  /// No description provided for @capsuleActualCount.
  ///
  /// In zh, this message translates to:
  /// **'实际数量：{count}'**
  String capsuleActualCount(int count);

  /// No description provided for @capsuleChipLabel.
  ///
  /// In zh, this message translates to:
  /// **'胶囊 {id}'**
  String capsuleChipLabel(String id);

  /// No description provided for @commonRetry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get commonRetry;

  /// No description provided for @capsuleViewCapsules.
  ///
  /// In zh, this message translates to:
  /// **'查看胶囊'**
  String get capsuleViewCapsules;

  /// No description provided for @capsuleNewDiscovery.
  ///
  /// In zh, this message translates to:
  /// **'新发现'**
  String get capsuleNewDiscovery;

  /// No description provided for @capsuleRestoreCurrent.
  ///
  /// In zh, this message translates to:
  /// **'恢复到当前列表'**
  String get capsuleRestoreCurrent;

  /// No description provided for @capsuleArchiveAction.
  ///
  /// In zh, this message translates to:
  /// **'归档这条胶囊'**
  String get capsuleArchiveAction;

  /// No description provided for @capsuleRestored.
  ///
  /// In zh, this message translates to:
  /// **'已恢复到当前列表'**
  String get capsuleRestored;

  /// No description provided for @capsuleArchivedInfo.
  ///
  /// In zh, this message translates to:
  /// **'已归档，可在历史中查看'**
  String get capsuleArchivedInfo;

  /// No description provided for @patternListTitle.
  ///
  /// In zh, this message translates to:
  /// **'认知棱镜'**
  String get patternListTitle;

  /// No description provided for @patternListEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'还没有生成真实行为定式'**
  String get patternListEmptyTitle;

  /// No description provided for @patternListEmptySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'继续记录想法和复盘后，这里会把这些信号整理成真正有用的行为模式。'**
  String get patternListEmptySubtitle;

  /// No description provided for @patternArchived.
  ///
  /// In zh, this message translates to:
  /// **'已克服'**
  String get patternArchived;

  /// No description provided for @patternTakeAction.
  ///
  /// In zh, this message translates to:
  /// **'立即行动'**
  String get patternTakeAction;

  /// No description provided for @patternDiscoveredOn.
  ///
  /// In zh, this message translates to:
  /// **'发现于 {date}'**
  String patternDiscoveredOn(String date);

  /// No description provided for @patternTypeCognitive.
  ///
  /// In zh, this message translates to:
  /// **'认知偏差'**
  String get patternTypeCognitive;

  /// No description provided for @patternTypeEmotional.
  ///
  /// In zh, this message translates to:
  /// **'情绪模式'**
  String get patternTypeEmotional;

  /// No description provided for @patternTypeExecution.
  ///
  /// In zh, this message translates to:
  /// **'执行习惯'**
  String get patternTypeExecution;

  /// No description provided for @patternTypeDefault.
  ///
  /// In zh, this message translates to:
  /// **'行为模式'**
  String get patternTypeDefault;

  /// No description provided for @chatTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI学习助手'**
  String get chatTitle;

  /// No description provided for @chatSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'随时为你解答'**
  String get chatSubtitle;

  /// No description provided for @chatHistoryTitle.
  ///
  /// In zh, this message translates to:
  /// **'历史对话'**
  String get chatHistoryTitle;

  /// No description provided for @chatNewConversation.
  ///
  /// In zh, this message translates to:
  /// **'新建对话'**
  String get chatNewConversation;

  /// No description provided for @chatHistoryLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String chatHistoryLoadFailed(String error);

  /// No description provided for @chatHistoryLoadMoreFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载更多失败：{error}'**
  String chatHistoryLoadMoreFailed(String error);

  /// No description provided for @chatHistoryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无历史记录'**
  String get chatHistoryEmpty;

  /// No description provided for @chatSessionUntitled.
  ///
  /// In zh, this message translates to:
  /// **'未命名会话'**
  String get chatSessionUntitled;

  /// No description provided for @chatInvalidNavigationTarget.
  ///
  /// In zh, this message translates to:
  /// **'无法识别跳转地址'**
  String get chatInvalidNavigationTarget;

  /// No description provided for @chatNavigationFailed.
  ///
  /// In zh, this message translates to:
  /// **'页面跳转失败，请重试'**
  String get chatNavigationFailed;

  /// No description provided for @chatSessionDataError.
  ///
  /// In zh, this message translates to:
  /// **'会话数据异常，请重试'**
  String get chatSessionDataError;

  /// No description provided for @chatWelcomeTitle.
  ///
  /// In zh, this message translates to:
  /// **'你好，我是你的 AI 导师'**
  String get chatWelcomeTitle;

  /// No description provided for @chatQuickActionNewTask.
  ///
  /// In zh, this message translates to:
  /// **'新建微任务'**
  String get chatQuickActionNewTask;

  /// No description provided for @chatQuickActionNewTaskPrompt.
  ///
  /// In zh, this message translates to:
  /// **'帮我创建一个新的微任务'**
  String get chatQuickActionNewTaskPrompt;

  /// No description provided for @chatQuickActionLongPlan.
  ///
  /// In zh, this message translates to:
  /// **'生成长期计划'**
  String get chatQuickActionLongPlan;

  /// No description provided for @chatQuickActionLongPlanPrompt.
  ///
  /// In zh, this message translates to:
  /// **'帮我生成一个长期学习计划'**
  String get chatQuickActionLongPlanPrompt;

  /// No description provided for @chatQuickActionErrorAttribution.
  ///
  /// In zh, this message translates to:
  /// **'错误归因'**
  String get chatQuickActionErrorAttribution;

  /// No description provided for @chatQuickActionErrorAttributionPrompt.
  ///
  /// In zh, this message translates to:
  /// **'我想分析一下最近的错误原因'**
  String get chatQuickActionErrorAttributionPrompt;

  /// No description provided for @chatPlanUnbound.
  ///
  /// In zh, this message translates to:
  /// **'未绑定计划'**
  String get chatPlanUnbound;

  /// No description provided for @chatFileProcessing.
  ///
  /// In zh, this message translates to:
  /// **'文件处理中，完成后可用于对话'**
  String get chatFileProcessing;

  /// No description provided for @chatPromptDeepAnalysis1.
  ///
  /// In zh, this message translates to:
  /// **'先给综合判断，再展开依据'**
  String get chatPromptDeepAnalysis1;

  /// No description provided for @chatPromptDeepAnalysis2.
  ///
  /// In zh, this message translates to:
  /// **'只看关键结论和风险'**
  String get chatPromptDeepAnalysis2;

  /// No description provided for @chatPromptDeepAnalysis3.
  ///
  /// In zh, this message translates to:
  /// **'补一个反方观点帮我校准'**
  String get chatPromptDeepAnalysis3;

  /// No description provided for @chatPromptStudyPlan1.
  ///
  /// In zh, this message translates to:
  /// **'先按今天能开始的节奏排'**
  String get chatPromptStudyPlan1;

  /// No description provided for @chatPromptStudyPlan2.
  ///
  /// In zh, this message translates to:
  /// **'拆成今天/本周两个层级'**
  String get chatPromptStudyPlan2;

  /// No description provided for @chatPromptStudyPlan3.
  ///
  /// In zh, this message translates to:
  /// **'按我现在水平再降一点难度'**
  String get chatPromptStudyPlan3;

  /// No description provided for @chatPromptErrorDiagnosis1.
  ///
  /// In zh, this message translates to:
  /// **'先定位错因和证据'**
  String get chatPromptErrorDiagnosis1;

  /// No description provided for @chatPromptErrorDiagnosis2.
  ///
  /// In zh, this message translates to:
  /// **'给我一条针对性修复练习'**
  String get chatPromptErrorDiagnosis2;

  /// No description provided for @chatPromptErrorDiagnosis3.
  ///
  /// In zh, this message translates to:
  /// **'告诉我下次怎么避免再错'**
  String get chatPromptErrorDiagnosis3;

  /// No description provided for @chatPromptExpertAuto1.
  ///
  /// In zh, this message translates to:
  /// **'自动选专家给我综合结论'**
  String get chatPromptExpertAuto1;

  /// No description provided for @chatPromptExpertAuto2.
  ///
  /// In zh, this message translates to:
  /// **'先告诉我这轮请了谁'**
  String get chatPromptExpertAuto2;

  /// No description provided for @chatPromptExpertAuto3.
  ///
  /// In zh, this message translates to:
  /// **'把专家结果压成执行清单'**
  String get chatPromptExpertAuto3;

  /// No description provided for @chatPromptDefault1.
  ///
  /// In zh, this message translates to:
  /// **'直接回答我的当前问题'**
  String get chatPromptDefault1;

  /// No description provided for @chatPromptDefault2.
  ///
  /// In zh, this message translates to:
  /// **'先给我 3 步执行清单'**
  String get chatPromptDefault2;

  /// No description provided for @chatPromptDefault3.
  ///
  /// In zh, this message translates to:
  /// **'结合我当前计划继续推进'**
  String get chatPromptDefault3;

  /// No description provided for @chatHelpful.
  ///
  /// In zh, this message translates to:
  /// **'有帮助'**
  String get chatHelpful;

  /// No description provided for @chatNotHelpful.
  ///
  /// In zh, this message translates to:
  /// **'没帮助'**
  String get chatNotHelpful;

  /// No description provided for @chatQuote.
  ///
  /// In zh, this message translates to:
  /// **'引用'**
  String get chatQuote;

  /// No description provided for @chatUndo.
  ///
  /// In zh, this message translates to:
  /// **'撤销'**
  String get chatUndo;

  /// No description provided for @chatRecalledSelf.
  ///
  /// In zh, this message translates to:
  /// **'你撤回了一条消息'**
  String get chatRecalledSelf;

  /// No description provided for @chatRecalledPeer.
  ///
  /// In zh, this message translates to:
  /// **'对方撤回了一条消息'**
  String get chatRecalledPeer;

  /// No description provided for @chatRead.
  ///
  /// In zh, this message translates to:
  /// **'已读'**
  String get chatRead;

  /// No description provided for @chatAgentNavigator.
  ///
  /// In zh, this message translates to:
  /// **'星图导航'**
  String get chatAgentNavigator;

  /// No description provided for @chatAgentExamStrategist.
  ///
  /// In zh, this message translates to:
  /// **'考试策略师'**
  String get chatAgentExamStrategist;

  /// No description provided for @chatAgentTimeCoach.
  ///
  /// In zh, this message translates to:
  /// **'时间教练'**
  String get chatAgentTimeCoach;

  /// No description provided for @chatAgentDeepAnalyst.
  ///
  /// In zh, this message translates to:
  /// **'深度分析师'**
  String get chatAgentDeepAnalyst;

  /// No description provided for @chatAgentCorrectionExpert.
  ///
  /// In zh, this message translates to:
  /// **'纠错专家'**
  String get chatAgentCorrectionExpert;

  /// No description provided for @chatAgentLearningBuddy.
  ///
  /// In zh, this message translates to:
  /// **'学伴'**
  String get chatAgentLearningBuddy;

  /// No description provided for @chatAgentMathExpert.
  ///
  /// In zh, this message translates to:
  /// **'数学专家'**
  String get chatAgentMathExpert;

  /// No description provided for @chatAgentCodingExpert.
  ///
  /// In zh, this message translates to:
  /// **'编程专家'**
  String get chatAgentCodingExpert;

  /// No description provided for @chatAgentWritingExpert.
  ///
  /// In zh, this message translates to:
  /// **'写作专家'**
  String get chatAgentWritingExpert;

  /// No description provided for @chatAgentScienceExpert.
  ///
  /// In zh, this message translates to:
  /// **'理科专家'**
  String get chatAgentScienceExpert;

  /// No description provided for @chatAgentSearchExpert.
  ///
  /// In zh, this message translates to:
  /// **'搜索专家'**
  String get chatAgentSearchExpert;

  /// No description provided for @chatCollabParallel.
  ///
  /// In zh, this message translates to:
  /// **'并行协作'**
  String get chatCollabParallel;

  /// No description provided for @chatCollabDebate.
  ///
  /// In zh, this message translates to:
  /// **'辩论协作'**
  String get chatCollabDebate;

  /// No description provided for @chatCollabDelegation.
  ///
  /// In zh, this message translates to:
  /// **'委派协作'**
  String get chatCollabDelegation;

  /// No description provided for @chatCollabSequential.
  ///
  /// In zh, this message translates to:
  /// **'分步协作'**
  String get chatCollabSequential;

  /// No description provided for @chatCollabExpert.
  ///
  /// In zh, this message translates to:
  /// **'专家协作'**
  String get chatCollabExpert;

  /// No description provided for @chatTeamSheetTitle.
  ///
  /// In zh, this message translates to:
  /// **'组建你的专家团队'**
  String get chatTeamSheetTitle;

  /// No description provided for @chatTeamSheetAvailableExperts.
  ///
  /// In zh, this message translates to:
  /// **'可选专家'**
  String get chatTeamSheetAvailableExperts;

  /// No description provided for @chatTeamSheetNoExperts.
  ///
  /// In zh, this message translates to:
  /// **'暂无可用专家'**
  String get chatTeamSheetNoExperts;

  /// No description provided for @chatTeamSheetLoading.
  ///
  /// In zh, this message translates to:
  /// **'专家目录加载中…'**
  String get chatTeamSheetLoading;

  /// No description provided for @chatTeamSheetLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败，请稍后重试'**
  String get chatTeamSheetLoadFailed;

  /// No description provided for @chatTeamSheetCollaborationMode.
  ///
  /// In zh, this message translates to:
  /// **'协作方式'**
  String get chatTeamSheetCollaborationMode;

  /// No description provided for @chatTeamSheetSelectedExperts.
  ///
  /// In zh, this message translates to:
  /// **'已选 {count} 位专家'**
  String chatTeamSheetSelectedExperts(int count);

  /// No description provided for @chatTeamSheetEnterExpert.
  ///
  /// In zh, this message translates to:
  /// **'进入专家直达'**
  String get chatTeamSheetEnterExpert;

  /// No description provided for @chatTeamSheetStartCollaboration.
  ///
  /// In zh, this message translates to:
  /// **'开始协作'**
  String get chatTeamSheetStartCollaboration;

  /// No description provided for @chatCollabAuto.
  ///
  /// In zh, this message translates to:
  /// **'自动'**
  String get chatCollabAuto;

  /// No description provided for @chatCollabAutoDesc.
  ///
  /// In zh, this message translates to:
  /// **'系统根据问题类型自动选择最佳协作方式'**
  String get chatCollabAutoDesc;

  /// No description provided for @chatCollabSequentialShort.
  ///
  /// In zh, this message translates to:
  /// **'分步'**
  String get chatCollabSequentialShort;

  /// No description provided for @chatCollabSequentialDesc.
  ///
  /// In zh, this message translates to:
  /// **'专家按顺序依次分析，后者可参考前者结论'**
  String get chatCollabSequentialDesc;

  /// No description provided for @chatCollabParallelShort.
  ///
  /// In zh, this message translates to:
  /// **'并行'**
  String get chatCollabParallelShort;

  /// No description provided for @chatCollabParallelDesc.
  ///
  /// In zh, this message translates to:
  /// **'所有专家同时分析，最后汇总各方观点'**
  String get chatCollabParallelDesc;

  /// No description provided for @chatCollabDebateShort.
  ///
  /// In zh, this message translates to:
  /// **'辩论'**
  String get chatCollabDebateShort;

  /// No description provided for @chatCollabDebateDesc.
  ///
  /// In zh, this message translates to:
  /// **'专家独立分析后交叉审阅，最终给出共识结论'**
  String get chatCollabDebateDesc;

  /// No description provided for @chatCollabDelegationShort.
  ///
  /// In zh, this message translates to:
  /// **'委派'**
  String get chatCollabDelegationShort;

  /// No description provided for @chatCollabDelegationDesc.
  ///
  /// In zh, this message translates to:
  /// **'主专家拆解任务后分派给其他专家执行'**
  String get chatCollabDelegationDesc;

  /// No description provided for @chatLabelMe.
  ///
  /// In zh, this message translates to:
  /// **'我'**
  String get chatLabelMe;

  /// No description provided for @chatLabelAssistant.
  ///
  /// In zh, this message translates to:
  /// **'AI助手'**
  String get chatLabelAssistant;

  /// No description provided for @chatNoContent.
  ///
  /// In zh, this message translates to:
  /// **'无内容'**
  String get chatNoContent;

  /// No description provided for @chatTransparencyTitle.
  ///
  /// In zh, this message translates to:
  /// **'透明模式'**
  String get chatTransparencyTitle;

  /// No description provided for @chatActiveToolsCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个工具'**
  String chatActiveToolsCount(int count);

  /// No description provided for @chatActiveTools.
  ///
  /// In zh, this message translates to:
  /// **'活跃工具'**
  String get chatActiveTools;

  /// No description provided for @chatTokenStats.
  ///
  /// In zh, this message translates to:
  /// **'Token 统计'**
  String get chatTokenStats;

  /// No description provided for @chatPromptTokens.
  ///
  /// In zh, this message translates to:
  /// **'提示词 Token'**
  String get chatPromptTokens;

  /// No description provided for @chatCompletionTokens.
  ///
  /// In zh, this message translates to:
  /// **'补全 Token'**
  String get chatCompletionTokens;

  /// No description provided for @chatTokenUsageToday.
  ///
  /// In zh, this message translates to:
  /// **'今日使用'**
  String get chatTokenUsageToday;

  /// No description provided for @chatTokenCostEstimate.
  ///
  /// In zh, this message translates to:
  /// **'成本估算'**
  String get chatTokenCostEstimate;

  /// No description provided for @chatExecutionSteps.
  ///
  /// In zh, this message translates to:
  /// **'执行步骤'**
  String get chatExecutionSteps;

  /// No description provided for @chatExecutionStepsCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个步骤'**
  String chatExecutionStepsCount(int count);

  /// No description provided for @chatModeSelect.
  ///
  /// In zh, this message translates to:
  /// **'选择模式'**
  String get chatModeSelect;

  /// No description provided for @chatModeTeamSummary.
  ///
  /// In zh, this message translates to:
  /// **'{count}位专家·{mode}'**
  String chatModeTeamSummary(int count, String mode);

  /// No description provided for @chatModeCustomTeamLabel.
  ///
  /// In zh, this message translates to:
  /// **'自定义团队'**
  String get chatModeCustomTeamLabel;

  /// No description provided for @chatModeCustomTeamTitle.
  ///
  /// In zh, this message translates to:
  /// **'自定义专家团队'**
  String get chatModeCustomTeamTitle;

  /// No description provided for @chatModeCustomTeamSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'选择参与专家和协作方式'**
  String get chatModeCustomTeamSubtitle;

  /// No description provided for @chatMetadataContinuity.
  ///
  /// In zh, this message translates to:
  /// **'承接上文'**
  String get chatMetadataContinuity;

  /// No description provided for @chatMetadataEvidence.
  ///
  /// In zh, this message translates to:
  /// **'依据'**
  String get chatMetadataEvidence;

  /// No description provided for @chatMetadataNext.
  ///
  /// In zh, this message translates to:
  /// **'下一步'**
  String get chatMetadataNext;

  /// No description provided for @chatMetadataCollaboration.
  ///
  /// In zh, this message translates to:
  /// **'协作'**
  String get chatMetadataCollaboration;

  /// No description provided for @chatLoginRequired.
  ///
  /// In zh, this message translates to:
  /// **'请先登录'**
  String get chatLoginRequired;

  /// No description provided for @chatReviewRegenerationRequested.
  ///
  /// In zh, this message translates to:
  /// **'已请求重新生成'**
  String get chatReviewRegenerationRequested;

  /// No description provided for @chatReviewHumanReviewRequested.
  ///
  /// In zh, this message translates to:
  /// **'已提交人工审查请求'**
  String get chatReviewHumanReviewRequested;

  /// No description provided for @chatReviewOverrideAcceptedEvenFail.
  ///
  /// In zh, this message translates to:
  /// **'已接受内容（尽管未通过审查）'**
  String get chatReviewOverrideAcceptedEvenFail;

  /// No description provided for @chatReviewOverrideRejectedEvenPass.
  ///
  /// In zh, this message translates to:
  /// **'已拒绝内容（尽管审查通过）'**
  String get chatReviewOverrideRejectedEvenPass;

  /// No description provided for @chatSubmitFailedRetry.
  ///
  /// In zh, this message translates to:
  /// **'提交失败，请重试'**
  String get chatSubmitFailedRetry;

  /// No description provided for @chatAppealSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'申诉已提交，正在处理...'**
  String get chatAppealSubmitted;

  /// No description provided for @commonBack.
  ///
  /// In zh, this message translates to:
  /// **'返回'**
  String get commonBack;

  /// No description provided for @noData.
  ///
  /// In zh, this message translates to:
  /// **'暂无数据'**
  String get noData;

  /// No description provided for @operationSuccess.
  ///
  /// In zh, this message translates to:
  /// **'操作成功'**
  String get operationSuccess;

  /// No description provided for @operationFailed.
  ///
  /// In zh, this message translates to:
  /// **'操作失败'**
  String get operationFailed;

  /// No description provided for @confirmDeleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认删除'**
  String get confirmDeleteTitle;

  /// No description provided for @confirmDeleteMessage.
  ///
  /// In zh, this message translates to:
  /// **'此操作无法撤销'**
  String get confirmDeleteMessage;

  /// No description provided for @errorBookTitle.
  ///
  /// In zh, this message translates to:
  /// **'错题档案'**
  String get errorBookTitle;

  /// No description provided for @errorBookTabAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get errorBookTabAll;

  /// No description provided for @errorBookTabNeedReview.
  ///
  /// In zh, this message translates to:
  /// **'待复习'**
  String get errorBookTabNeedReview;

  /// No description provided for @errorBookAddError.
  ///
  /// In zh, this message translates to:
  /// **'添加错题'**
  String get errorBookAddError;

  /// No description provided for @errorBookAddFirst.
  ///
  /// In zh, this message translates to:
  /// **'添加第一道错题'**
  String get errorBookAddFirst;

  /// No description provided for @errorBookFilterTitle.
  ///
  /// In zh, this message translates to:
  /// **'筛选选项'**
  String get errorBookFilterTitle;

  /// No description provided for @errorBookSearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索题目内容...'**
  String get errorBookSearchHint;

  /// No description provided for @errorBookNoErrors.
  ///
  /// In zh, this message translates to:
  /// **'还没有错题记录'**
  String get errorBookNoErrors;

  /// No description provided for @errorBookNoErrorsHint.
  ///
  /// In zh, this message translates to:
  /// **'点击右下角 + 按钮添加错题'**
  String get errorBookNoErrorsHint;

  /// No description provided for @errorBookNoReview.
  ///
  /// In zh, this message translates to:
  /// **'暂无需要复习的错题'**
  String get errorBookNoReview;

  /// No description provided for @errorBookNoReviewHint.
  ///
  /// In zh, this message translates to:
  /// **'做得很好！继续保持'**
  String get errorBookNoReviewHint;

  /// No description provided for @errorBookDeleteSuccess.
  ///
  /// In zh, this message translates to:
  /// **'删除成功'**
  String get errorBookDeleteSuccess;

  /// No description provided for @errorBookDeleteFailed.
  ///
  /// In zh, this message translates to:
  /// **'删除失败'**
  String get errorBookDeleteFailed;

  /// No description provided for @errorBookDeleteConfirmTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认删除'**
  String get errorBookDeleteConfirmTitle;

  /// No description provided for @errorBookDeleteConfirmMessage.
  ///
  /// In zh, this message translates to:
  /// **'删除后无法恢复，确定要删除这道错题吗？'**
  String get errorBookDeleteConfirmMessage;

  /// No description provided for @errorBookDetailTitle.
  ///
  /// In zh, this message translates to:
  /// **'错题详情'**
  String get errorBookDetailTitle;

  /// No description provided for @errorBookEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑'**
  String get errorBookEdit;

  /// No description provided for @errorBookReanalyze.
  ///
  /// In zh, this message translates to:
  /// **'重新分析'**
  String get errorBookReanalyze;

  /// No description provided for @errorBookDelete.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get errorBookDelete;

  /// No description provided for @errorBookCreatedAt.
  ///
  /// In zh, this message translates to:
  /// **'创建于 {date}'**
  String errorBookCreatedAt(String date);

  /// No description provided for @errorBookMasteryPercent.
  ///
  /// In zh, this message translates to:
  /// **'{percent}%掌握'**
  String errorBookMasteryPercent(int percent);

  /// No description provided for @errorBookSimilarSummary.
  ///
  /// In zh, this message translates to:
  /// **'同类错因分析'**
  String get errorBookSimilarSummary;

  /// No description provided for @errorBookRootCause.
  ///
  /// In zh, this message translates to:
  /// **'根本原因'**
  String get errorBookRootCause;

  /// No description provided for @errorBookStrategySuggestions.
  ///
  /// In zh, this message translates to:
  /// **'策略建议'**
  String get errorBookStrategySuggestions;

  /// No description provided for @errorBookSimilarErrors.
  ///
  /// In zh, this message translates to:
  /// **'相似错误'**
  String get errorBookSimilarErrors;

  /// No description provided for @errorBookSimilarCauseFallback.
  ///
  /// In zh, this message translates to:
  /// **'未分类'**
  String get errorBookSimilarCauseFallback;

  /// No description provided for @errorBookQuestionContent.
  ///
  /// In zh, this message translates to:
  /// **'题目内容'**
  String get errorBookQuestionContent;

  /// No description provided for @errorBookImageLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'图片加载失败'**
  String get errorBookImageLoadFailed;

  /// No description provided for @errorBookAnswerComparison.
  ///
  /// In zh, this message translates to:
  /// **'答案对比'**
  String get errorBookAnswerComparison;

  /// No description provided for @errorBookYourAnswer.
  ///
  /// In zh, this message translates to:
  /// **'你的答案'**
  String get errorBookYourAnswer;

  /// No description provided for @errorBookCorrectAnswer.
  ///
  /// In zh, this message translates to:
  /// **'正确答案'**
  String get errorBookCorrectAnswer;

  /// No description provided for @errorBookAiAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'AI 分析'**
  String get errorBookAiAnalysis;

  /// No description provided for @errorBookKnowledgeLinks.
  ///
  /// In zh, this message translates to:
  /// **'关联知识点'**
  String get errorBookKnowledgeLinks;

  /// No description provided for @errorBookKnowledgeLinkTooltip.
  ///
  /// In zh, this message translates to:
  /// **'查看学习路径'**
  String get errorBookKnowledgeLinkTooltip;

  /// No description provided for @errorBookKnowledgeLinkSnack.
  ///
  /// In zh, this message translates to:
  /// **'即将跳转到 {nodeName} 知识点'**
  String errorBookKnowledgeLinkSnack(String nodeName);

  /// No description provided for @errorBookReviewStats.
  ///
  /// In zh, this message translates to:
  /// **'复习统计'**
  String get errorBookReviewStats;

  /// No description provided for @errorBookLastReview.
  ///
  /// In zh, this message translates to:
  /// **'上次复习'**
  String get errorBookLastReview;

  /// No description provided for @errorBookNextReview.
  ///
  /// In zh, this message translates to:
  /// **'下次复习'**
  String get errorBookNextReview;

  /// No description provided for @errorBookStartReview.
  ///
  /// In zh, this message translates to:
  /// **'开始复习'**
  String get errorBookStartReview;

  /// No description provided for @errorBookLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败'**
  String get errorBookLoadFailed;

  /// No description provided for @errorBookEditInProgress.
  ///
  /// In zh, this message translates to:
  /// **'编辑功能即将上线'**
  String get errorBookEditInProgress;

  /// No description provided for @errorBookReanalyzing.
  ///
  /// In zh, this message translates to:
  /// **'正在重新分析...'**
  String get errorBookReanalyzing;

  /// No description provided for @errorBookReviewInProgress.
  ///
  /// In zh, this message translates to:
  /// **'复习功能即将上线'**
  String get errorBookReviewInProgress;

  /// No description provided for @errorBookDeleteFailedMessage.
  ///
  /// In zh, this message translates to:
  /// **'删除失败：{error}'**
  String errorBookDeleteFailedMessage(String error);

  /// No description provided for @errorBookCognitiveFilter.
  ///
  /// In zh, this message translates to:
  /// **'正针对 \"{dimension}\" 维度进行针对性复习'**
  String errorBookCognitiveFilter(String dimension);

  /// No description provided for @errorBookReviewCount.
  ///
  /// In zh, this message translates to:
  /// **'复习 {count} 次'**
  String errorBookReviewCount(int count);

  /// No description provided for @errorBookAIAnalyzed.
  ///
  /// In zh, this message translates to:
  /// **'AI已分析'**
  String get errorBookAIAnalyzed;

  /// No description provided for @errorBookTimeAgoMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count}分钟前'**
  String errorBookTimeAgoMinutes(int count);

  /// No description provided for @errorBookTimeAgoHours.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时前'**
  String errorBookTimeAgoHours(int count);

  /// No description provided for @errorBookTimeAgoDays.
  ///
  /// In zh, this message translates to:
  /// **'{count}天前'**
  String errorBookTimeAgoDays(int count);

  /// No description provided for @reviewModeToday.
  ///
  /// In zh, this message translates to:
  /// **'今日复习'**
  String get reviewModeToday;

  /// No description provided for @reviewModeTodayDesc.
  ///
  /// In zh, this message translates to:
  /// **'完成今天到期的所有错题'**
  String get reviewModeTodayDesc;

  /// No description provided for @reviewModeBySubject.
  ///
  /// In zh, this message translates to:
  /// **'按科目'**
  String get reviewModeBySubject;

  /// No description provided for @reviewModeBySubjectDesc.
  ///
  /// In zh, this message translates to:
  /// **'选择一个科目进行专项复习'**
  String get reviewModeBySubjectDesc;

  /// No description provided for @reviewModeWeakest.
  ///
  /// In zh, this message translates to:
  /// **'薄弱专攻'**
  String get reviewModeWeakest;

  /// No description provided for @reviewModeWeakestDesc.
  ///
  /// In zh, this message translates to:
  /// **'优先复习掌握度最低的错题'**
  String get reviewModeWeakestDesc;

  /// No description provided for @reviewModeRandom.
  ///
  /// In zh, this message translates to:
  /// **'随机抽查'**
  String get reviewModeRandom;

  /// No description provided for @reviewModeRandomDesc.
  ///
  /// In zh, this message translates to:
  /// **'随机抽取错题进行复习'**
  String get reviewModeRandomDesc;

  /// No description provided for @reviewProgress.
  ///
  /// In zh, this message translates to:
  /// **'进度: {current}/{total}'**
  String reviewProgress(int current, int total);

  /// No description provided for @reviewQuestion.
  ///
  /// In zh, this message translates to:
  /// **'题目'**
  String get reviewQuestion;

  /// No description provided for @reviewYourAnswer.
  ///
  /// In zh, this message translates to:
  /// **'你的答案'**
  String get reviewYourAnswer;

  /// No description provided for @reviewCorrectAnswer.
  ///
  /// In zh, this message translates to:
  /// **'正确答案'**
  String get reviewCorrectAnswer;

  /// No description provided for @reviewAIAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'AI 分析'**
  String get reviewAIAnalysis;

  /// No description provided for @reviewHideAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'隐藏'**
  String get reviewHideAnalysis;

  /// No description provided for @reviewViewAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'查看 AI 分析'**
  String get reviewViewAnalysis;

  /// No description provided for @reviewViewAnswer.
  ///
  /// In zh, this message translates to:
  /// **'查看答案'**
  String get reviewViewAnswer;

  /// No description provided for @reviewViewAnswerHint.
  ///
  /// In zh, this message translates to:
  /// **'先思考答案，再点击查看'**
  String get reviewViewAnswerHint;

  /// No description provided for @reviewSubmitFailed.
  ///
  /// In zh, this message translates to:
  /// **'提交失败: {error}'**
  String reviewSubmitFailed(String error);

  /// No description provided for @reviewNoErrorsToday.
  ///
  /// In zh, this message translates to:
  /// **'暂无需要复习的错题'**
  String get reviewNoErrorsToday;

  /// No description provided for @reviewKeepGoing.
  ///
  /// In zh, this message translates to:
  /// **'做得很好！继续保持'**
  String get reviewKeepGoing;

  /// No description provided for @reviewComplete.
  ///
  /// In zh, this message translates to:
  /// **'复习完成！'**
  String get reviewComplete;

  /// No description provided for @reviewTotalReviewed.
  ///
  /// In zh, this message translates to:
  /// **'本次共复习 {count} 道题'**
  String reviewTotalReviewed(int count);

  /// No description provided for @reviewResults.
  ///
  /// In zh, this message translates to:
  /// **'复习成果'**
  String get reviewResults;

  /// No description provided for @reviewRemembered.
  ///
  /// In zh, this message translates to:
  /// **'记住了'**
  String get reviewRemembered;

  /// No description provided for @reviewFuzzy.
  ///
  /// In zh, this message translates to:
  /// **'模糊'**
  String get reviewFuzzy;

  /// No description provided for @reviewForgotten.
  ///
  /// In zh, this message translates to:
  /// **'忘记了'**
  String get reviewForgotten;

  /// No description provided for @reviewEncourageExcellent.
  ///
  /// In zh, this message translates to:
  /// **'太棒了！掌握得非常扎实 🎉'**
  String get reviewEncourageExcellent;

  /// No description provided for @reviewEncourageGood.
  ///
  /// In zh, this message translates to:
  /// **'很好！继续保持这个势头 💪'**
  String get reviewEncourageGood;

  /// No description provided for @reviewEncourageFair.
  ///
  /// In zh, this message translates to:
  /// **'不错！再多复习几次会更好 📚'**
  String get reviewEncourageFair;

  /// No description provided for @reviewEncourageNeedsWork.
  ///
  /// In zh, this message translates to:
  /// **'加油！多复习几次就能记住了 🌟'**
  String get reviewEncourageNeedsWork;

  /// No description provided for @reviewBackToList.
  ///
  /// In zh, this message translates to:
  /// **'返回列表'**
  String get reviewBackToList;

  /// No description provided for @reviewAnotherRound.
  ///
  /// In zh, this message translates to:
  /// **'再来一轮'**
  String get reviewAnotherRound;

  /// No description provided for @reviewConfirmExitTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认退出'**
  String get reviewConfirmExitTitle;

  /// No description provided for @reviewConfirmExitMessage.
  ///
  /// In zh, this message translates to:
  /// **'复习还未完成，确定要退出吗？'**
  String get reviewConfirmExitMessage;

  /// No description provided for @reviewContinue.
  ///
  /// In zh, this message translates to:
  /// **'继续复习'**
  String get reviewContinue;

  /// No description provided for @reviewExit.
  ///
  /// In zh, this message translates to:
  /// **'退出'**
  String get reviewExit;

  /// No description provided for @reviewNoMatchingErrors.
  ///
  /// In zh, this message translates to:
  /// **'没有符合条件的错题'**
  String get reviewNoMatchingErrors;

  /// No description provided for @communityTitle.
  ///
  /// In zh, this message translates to:
  /// **'星火社群'**
  String get communityTitle;

  /// No description provided for @communitySearch.
  ///
  /// In zh, this message translates to:
  /// **'搜索'**
  String get communitySearch;

  /// No description provided for @communitySearchUsers.
  ///
  /// In zh, this message translates to:
  /// **'搜索用户'**
  String get communitySearchUsers;

  /// No description provided for @communitySearchGroups.
  ///
  /// In zh, this message translates to:
  /// **'搜索群组'**
  String get communitySearchGroups;

  /// No description provided for @communityDiscoverFriends.
  ///
  /// In zh, this message translates to:
  /// **'发现新好友'**
  String get communityDiscoverFriends;

  /// No description provided for @communityDiscoverFriendsHint.
  ///
  /// In zh, this message translates to:
  /// **'查看推荐的好友'**
  String get communityDiscoverFriendsHint;

  /// No description provided for @communityCreateGroup.
  ///
  /// In zh, this message translates to:
  /// **'创建群组'**
  String get communityCreateGroup;

  /// No description provided for @communityCreateGroupHint.
  ///
  /// In zh, this message translates to:
  /// **'创建一个新的学习群组'**
  String get communityCreateGroupHint;

  /// No description provided for @communityActions.
  ///
  /// In zh, this message translates to:
  /// **'社群操作'**
  String get communityActions;

  /// No description provided for @communityNoFriends.
  ///
  /// In zh, this message translates to:
  /// **'还没有好友'**
  String get communityNoFriends;

  /// No description provided for @communityNoGroups.
  ///
  /// In zh, this message translates to:
  /// **'还没有加入群组'**
  String get communityNoGroups;

  /// No description provided for @communityStatusOnline.
  ///
  /// In zh, this message translates to:
  /// **'在线'**
  String get communityStatusOnline;

  /// No description provided for @communityStatusOffline.
  ///
  /// In zh, this message translates to:
  /// **'离线'**
  String get communityStatusOffline;

  /// No description provided for @communityFocusModeOn.
  ///
  /// In zh, this message translates to:
  /// **'专注模式开启中'**
  String get communityFocusModeOn;

  /// No description provided for @communityFocusModeOff.
  ///
  /// In zh, this message translates to:
  /// **'开启专注模式'**
  String get communityFocusModeOff;

  /// No description provided for @communityFocusModeEnabled.
  ///
  /// In zh, this message translates to:
  /// **'已开启专注模式，消息将不会打扰您'**
  String get communityFocusModeEnabled;

  /// No description provided for @communityFocusModeDisabled.
  ///
  /// In zh, this message translates to:
  /// **'已关闭专注模式'**
  String get communityFocusModeDisabled;

  /// No description provided for @communityTabFriends.
  ///
  /// In zh, this message translates to:
  /// **'好友'**
  String get communityTabFriends;

  /// No description provided for @communityTabGroups.
  ///
  /// In zh, this message translates to:
  /// **'群组'**
  String get communityTabGroups;

  /// No description provided for @communityAddFriend.
  ///
  /// In zh, this message translates to:
  /// **'添加好友'**
  String get communityAddFriend;

  /// No description provided for @communityMembers.
  ///
  /// In zh, this message translates to:
  /// **'{count} 成员'**
  String communityMembers(int count);

  /// No description provided for @taskMonitorTitle.
  ///
  /// In zh, this message translates to:
  /// **'后台任务监控'**
  String get taskMonitorTitle;

  /// No description provided for @taskMonitorFilterAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get taskMonitorFilterAll;

  /// No description provided for @taskMonitorFilterRunning.
  ///
  /// In zh, this message translates to:
  /// **'运行中'**
  String get taskMonitorFilterRunning;

  /// No description provided for @taskMonitorFilterCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get taskMonitorFilterCompleted;

  /// No description provided for @taskMonitorFilterFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get taskMonitorFilterFailed;

  /// No description provided for @taskMonitorEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无后台任务'**
  String get taskMonitorEmpty;

  /// No description provided for @taskMonitorStatusPending.
  ///
  /// In zh, this message translates to:
  /// **'等待中'**
  String get taskMonitorStatusPending;

  /// No description provided for @taskMonitorStatusCancelled.
  ///
  /// In zh, this message translates to:
  /// **'已取消'**
  String get taskMonitorStatusCancelled;

  /// No description provided for @planHistoryTitle.
  ///
  /// In zh, this message translates to:
  /// **'历史计划'**
  String get planHistoryTitle;

  /// No description provided for @planHistoryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无历史计划'**
  String get planHistoryEmpty;

  /// No description provided for @planHistoryRestore.
  ///
  /// In zh, this message translates to:
  /// **'恢复计划'**
  String get planHistoryRestore;

  /// No description provided for @planHistoryRestoreSuccess.
  ///
  /// In zh, this message translates to:
  /// **'计划已恢复'**
  String get planHistoryRestoreSuccess;

  /// No description provided for @planHistoryDeleteConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定要删除这个历史计划吗？'**
  String get planHistoryDeleteConfirm;

  /// No description provided for @planTypeSprint.
  ///
  /// In zh, this message translates to:
  /// **'冲刺计划'**
  String get planTypeSprint;

  /// No description provided for @planTypeGrowth.
  ///
  /// In zh, this message translates to:
  /// **'成长计划'**
  String get planTypeGrowth;

  /// No description provided for @planProgressPercent.
  ///
  /// In zh, this message translates to:
  /// **'{percent}% 完成'**
  String planProgressPercent(String percent);

  /// No description provided for @authForgotPassword.
  ///
  /// In zh, this message translates to:
  /// **'忘记密码？'**
  String get authForgotPassword;

  /// No description provided for @authUserAgreement.
  ///
  /// In zh, this message translates to:
  /// **'用户协议'**
  String get authUserAgreement;

  /// No description provided for @authPrivacyPolicy.
  ///
  /// In zh, this message translates to:
  /// **'隐私政策'**
  String get authPrivacyPolicy;

  /// No description provided for @authLoginAgreement.
  ///
  /// In zh, this message translates to:
  /// **'登录即表示你同意'**
  String get authLoginAgreement;

  /// No description provided for @authAnd.
  ///
  /// In zh, this message translates to:
  /// **'和'**
  String get authAnd;

  /// No description provided for @authDemoLogin.
  ///
  /// In zh, this message translates to:
  /// **'演示账号登录'**
  String get authDemoLogin;

  /// No description provided for @authResetPassword.
  ///
  /// In zh, this message translates to:
  /// **'重置密码'**
  String get authResetPassword;

  /// No description provided for @authResetPasswordHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入您的邮箱，我们将发送重置密码链接'**
  String get authResetPasswordHint;

  /// No description provided for @authSendResetEmail.
  ///
  /// In zh, this message translates to:
  /// **'发送重置邮件'**
  String get authSendResetEmail;

  /// No description provided for @authResetEmailSent.
  ///
  /// In zh, this message translates to:
  /// **'重置邮件已发送'**
  String get authResetEmailSent;

  /// No description provided for @authBackToLogin.
  ///
  /// In zh, this message translates to:
  /// **'返回登录'**
  String get authBackToLogin;

  /// No description provided for @authForgotPasswordTitle.
  ///
  /// In zh, this message translates to:
  /// **'忘记密码'**
  String get authForgotPasswordTitle;

  /// No description provided for @authForgotPasswordHint.
  ///
  /// In zh, this message translates to:
  /// **'输入注册邮箱，我们会发送一封包含重置码的邮件给你。'**
  String get authForgotPasswordHint;

  /// No description provided for @authInvalidEmail.
  ///
  /// In zh, this message translates to:
  /// **'请输入有效邮箱'**
  String get authInvalidEmail;

  /// No description provided for @authHaveResetCode.
  ///
  /// In zh, this message translates to:
  /// **'我已经有重置码'**
  String get authHaveResetCode;

  /// No description provided for @toolsLibraryTitle.
  ///
  /// In zh, this message translates to:
  /// **'工具库'**
  String get toolsLibraryTitle;

  /// No description provided for @toolsTabBrowse.
  ///
  /// In zh, this message translates to:
  /// **'浏览'**
  String get toolsTabBrowse;

  /// No description provided for @toolsTabManage.
  ///
  /// In zh, this message translates to:
  /// **'管理'**
  String get toolsTabManage;

  /// No description provided for @toolsSearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索工具、能力或关键词'**
  String get toolsSearchHint;

  /// No description provided for @toolsRecentTitle.
  ///
  /// In zh, this message translates to:
  /// **'最近使用'**
  String get toolsRecentTitle;

  /// No description provided for @toolsManagePinned.
  ///
  /// In zh, this message translates to:
  /// **'管理固定'**
  String get toolsManagePinned;

  /// No description provided for @toolsCategoryInput.
  ///
  /// In zh, this message translates to:
  /// **'输入处理'**
  String get toolsCategoryInput;

  /// No description provided for @toolsCategoryStudy.
  ///
  /// In zh, this message translates to:
  /// **'学习辅助'**
  String get toolsCategoryStudy;

  /// No description provided for @toolsCategoryEfficiency.
  ///
  /// In zh, this message translates to:
  /// **'效率辅助'**
  String get toolsCategoryEfficiency;

  /// No description provided for @toolsCategoryCognition.
  ///
  /// In zh, this message translates to:
  /// **'认知洞察'**
  String get toolsCategoryCognition;

  /// No description provided for @toolsNoTools.
  ///
  /// In zh, this message translates to:
  /// **'暂无工具'**
  String get toolsNoTools;

  /// No description provided for @toolsPinnedEmpty.
  ///
  /// In zh, this message translates to:
  /// **'还没有固定的工具'**
  String get toolsPinnedEmpty;

  /// No description provided for @toolsManageHint.
  ///
  /// In zh, this message translates to:
  /// **'首页首屏显示前 4 个，展开显示前 8 个。拖动可调整顺序。'**
  String get toolsManageHint;

  /// No description provided for @toolsBackToBrowse.
  ///
  /// In zh, this message translates to:
  /// **'回到浏览'**
  String get toolsBackToBrowse;

  /// No description provided for @toolsPositionFirstScreen.
  ///
  /// In zh, this message translates to:
  /// **'首屏'**
  String get toolsPositionFirstScreen;

  /// No description provided for @toolsPositionExpanded.
  ///
  /// In zh, this message translates to:
  /// **'展开区'**
  String get toolsPositionExpanded;

  /// No description provided for @toolsPositionMore.
  ///
  /// In zh, this message translates to:
  /// **'更多页'**
  String get toolsPositionMore;

  /// No description provided for @knowledgeLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'知识节点加载失败'**
  String get knowledgeLoadFailed;

  /// No description provided for @knowledgeReload.
  ///
  /// In zh, this message translates to:
  /// **'重新加载'**
  String get knowledgeReload;

  /// No description provided for @knowledgeGeneratePath.
  ///
  /// In zh, this message translates to:
  /// **'生成学习路径'**
  String get knowledgeGeneratePath;

  /// No description provided for @knowledgeDescription.
  ///
  /// In zh, this message translates to:
  /// **'描述'**
  String get knowledgeDescription;

  /// No description provided for @knowledgeNoDescription.
  ///
  /// In zh, this message translates to:
  /// **'暂无描述'**
  String get knowledgeNoDescription;

  /// No description provided for @knowledgeRelatedNodes.
  ///
  /// In zh, this message translates to:
  /// **'相关节点'**
  String get knowledgeRelatedNodes;

  /// No description provided for @knowledgePrerequisites.
  ///
  /// In zh, this message translates to:
  /// **'前置知识'**
  String get knowledgePrerequisites;

  /// No description provided for @knowledgeMasteryProgress.
  ///
  /// In zh, this message translates to:
  /// **'掌握进度'**
  String get knowledgeMasteryProgress;

  /// No description provided for @knowledgeKeywords.
  ///
  /// In zh, this message translates to:
  /// **'关键词'**
  String get knowledgeKeywords;

  /// No description provided for @knowledgeEstimated.
  ///
  /// In zh, this message translates to:
  /// **'预计'**
  String get knowledgeEstimated;

  /// No description provided for @knowledgeMinutes.
  ///
  /// In zh, this message translates to:
  /// **'分钟'**
  String get knowledgeMinutes;

  /// No description provided for @knowledgeRelatedTasks.
  ///
  /// In zh, this message translates to:
  /// **'相关任务'**
  String get knowledgeRelatedTasks;

  /// No description provided for @knowledgeRelatedPlans.
  ///
  /// In zh, this message translates to:
  /// **'相关计划'**
  String get knowledgeRelatedPlans;

  /// No description provided for @knowledgeMastery.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get knowledgeMastery;

  /// No description provided for @knowledgeStudyMinutes.
  ///
  /// In zh, this message translates to:
  /// **'学习分钟'**
  String get knowledgeStudyMinutes;

  /// No description provided for @knowledgeStudyCount.
  ///
  /// In zh, this message translates to:
  /// **'学习次数'**
  String get knowledgeStudyCount;

  /// No description provided for @knowledgeNextReview.
  ///
  /// In zh, this message translates to:
  /// **'下次复习'**
  String get knowledgeNextReview;

  /// No description provided for @knowledgeDecayPaused.
  ///
  /// In zh, this message translates to:
  /// **'遗忘衰减已暂停'**
  String get knowledgeDecayPaused;

  /// No description provided for @knowledgeToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get knowledgeToday;

  /// No description provided for @knowledgeTomorrow.
  ///
  /// In zh, this message translates to:
  /// **'明天'**
  String get knowledgeTomorrow;

  /// No description provided for @knowledgeDaysLater.
  ///
  /// In zh, this message translates to:
  /// **'{days}天后'**
  String knowledgeDaysLater(int days);

  /// No description provided for @knowledgeWeeksLater.
  ///
  /// In zh, this message translates to:
  /// **'{weeks}周后'**
  String knowledgeWeeksLater(int weeks);

  /// No description provided for @seedLibraryTitle.
  ///
  /// In zh, this message translates to:
  /// **'种子库'**
  String get seedLibraryTitle;

  /// No description provided for @seedLibrarySearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索种子库...'**
  String get seedLibrarySearchHint;

  /// No description provided for @seedLibraryCreate.
  ///
  /// In zh, this message translates to:
  /// **'创建种子库'**
  String get seedLibraryCreate;

  /// No description provided for @seedLibraryNotFound.
  ///
  /// In zh, this message translates to:
  /// **'种子库不存在'**
  String get seedLibraryNotFound;

  /// No description provided for @seedLibraryDeleteConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定要删除这个种子库吗？此操作不可撤销。'**
  String get seedLibraryDeleteConfirm;

  /// No description provided for @seedLibraryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'还没有创建种子库'**
  String get seedLibraryEmpty;

  /// No description provided for @seedLibraryCreateFirst.
  ///
  /// In zh, this message translates to:
  /// **'创建一个新的种子库开始使用'**
  String get seedLibraryCreateFirst;

  /// No description provided for @seedLibraryItemCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个条目'**
  String seedLibraryItemCount(int count);

  /// No description provided for @seedLibraryLastUpdated.
  ///
  /// In zh, this message translates to:
  /// **'最后更新: {date}'**
  String seedLibraryLastUpdated(String date);

  /// No description provided for @seedLibraryDetail.
  ///
  /// In zh, this message translates to:
  /// **'种子库详情'**
  String get seedLibraryDetail;

  /// No description provided for @seedLibraryFilter.
  ///
  /// In zh, this message translates to:
  /// **'筛选'**
  String get seedLibraryFilter;

  /// No description provided for @seedLibraryCategory.
  ///
  /// In zh, this message translates to:
  /// **'分类'**
  String get seedLibraryCategory;

  /// No description provided for @seedLibraryVisibility.
  ///
  /// In zh, this message translates to:
  /// **'可见性'**
  String get seedLibraryVisibility;

  /// No description provided for @seedLibraryClear.
  ///
  /// In zh, this message translates to:
  /// **'清除'**
  String get seedLibraryClear;

  /// No description provided for @seedLibraryApply.
  ///
  /// In zh, this message translates to:
  /// **'应用'**
  String get seedLibraryApply;

  /// No description provided for @seedLibrarySubscribe.
  ///
  /// In zh, this message translates to:
  /// **'订阅'**
  String get seedLibrarySubscribe;

  /// No description provided for @seedLibraryUnsubscribe.
  ///
  /// In zh, this message translates to:
  /// **'取消订阅'**
  String get seedLibraryUnsubscribe;

  /// No description provided for @seedLibraryContentItems.
  ///
  /// In zh, this message translates to:
  /// **'内容项'**
  String get seedLibraryContentItems;

  /// No description provided for @seedLibraryNoContent.
  ///
  /// In zh, this message translates to:
  /// **'暂无内容'**
  String get seedLibraryNoContent;

  /// No description provided for @seedLibraryContent.
  ///
  /// In zh, this message translates to:
  /// **'内容'**
  String get seedLibraryContent;

  /// No description provided for @seedLibrarySubscribers.
  ///
  /// In zh, this message translates to:
  /// **'订阅者'**
  String get seedLibrarySubscribers;

  /// No description provided for @seedLibraryUsage.
  ///
  /// In zh, this message translates to:
  /// **'使用'**
  String get seedLibraryUsage;

  /// No description provided for @seedLibraryQualityScore.
  ///
  /// In zh, this message translates to:
  /// **'质量分'**
  String get seedLibraryQualityScore;

  /// No description provided for @seedLibraryDeleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'删除种子库'**
  String get seedLibraryDeleteTitle;

  /// No description provided for @seedLibraryDeleteFailed.
  ///
  /// In zh, this message translates to:
  /// **'删除失败：{error}'**
  String seedLibraryDeleteFailed(String error);

  /// No description provided for @translationHistoryTitle.
  ///
  /// In zh, this message translates to:
  /// **'翻译历史'**
  String get translationHistoryTitle;

  /// No description provided for @translationClearHistory.
  ///
  /// In zh, this message translates to:
  /// **'清空历史'**
  String get translationClearHistory;

  /// No description provided for @translationTranslating.
  ///
  /// In zh, this message translates to:
  /// **'翻译中...'**
  String get translationTranslating;

  /// No description provided for @translationSaveToVocabulary.
  ///
  /// In zh, this message translates to:
  /// **'保存到生词卡'**
  String get translationSaveToVocabulary;

  /// No description provided for @translationCopy.
  ///
  /// In zh, this message translates to:
  /// **'复制'**
  String get translationCopy;

  /// No description provided for @translationCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制'**
  String get translationCopied;

  /// No description provided for @translationSearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索翻译记录...'**
  String get translationSearchHint;

  /// No description provided for @translationNoHistory.
  ///
  /// In zh, this message translates to:
  /// **'暂无翻译记录'**
  String get translationNoHistory;

  /// No description provided for @translationStartTranslate.
  ///
  /// In zh, this message translates to:
  /// **'开始翻译文本后会显示在这里'**
  String get translationStartTranslate;

  /// No description provided for @translationClearConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定要清空所有翻译历史吗？'**
  String get translationClearConfirm;

  /// No description provided for @translationClearConfirmDetail.
  ///
  /// In zh, this message translates to:
  /// **'此操作不可撤销'**
  String get translationClearConfirmDetail;

  /// No description provided for @translationClearAll.
  ///
  /// In zh, this message translates to:
  /// **'清空历史'**
  String get translationClearAll;

  /// No description provided for @translationFilterAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get translationFilterAll;

  /// No description provided for @translationFilterFavorites.
  ///
  /// In zh, this message translates to:
  /// **'收藏'**
  String get translationFilterFavorites;

  /// No description provided for @translationFilterImportant.
  ///
  /// In zh, this message translates to:
  /// **'重要'**
  String get translationFilterImportant;

  /// No description provided for @translationFilterRecent.
  ///
  /// In zh, this message translates to:
  /// **'最近'**
  String get translationFilterRecent;

  /// No description provided for @translationNoSearchResults.
  ///
  /// In zh, this message translates to:
  /// **'未找到结果'**
  String get translationNoSearchResults;

  /// No description provided for @translationTryOtherKeywords.
  ///
  /// In zh, this message translates to:
  /// **'尝试其他关键词'**
  String get translationTryOtherKeywords;

  /// No description provided for @translationNoFavorites.
  ///
  /// In zh, this message translates to:
  /// **'暂无收藏'**
  String get translationNoFavorites;

  /// No description provided for @translationNoFavoritesHint.
  ///
  /// In zh, this message translates to:
  /// **'给翻译打星标收藏起来'**
  String get translationNoFavoritesHint;

  /// No description provided for @translationNoImportant.
  ///
  /// In zh, this message translates to:
  /// **'暂无重要翻译'**
  String get translationNoImportant;

  /// No description provided for @translationNoImportantHint.
  ///
  /// In zh, this message translates to:
  /// **'给4星及以上的翻译会显示在这里'**
  String get translationNoImportantHint;

  /// No description provided for @translationNoRecordsHint.
  ///
  /// In zh, this message translates to:
  /// **'使用翻译功能后会自动保存'**
  String get translationNoRecordsHint;

  /// No description provided for @translationRating.
  ///
  /// In zh, this message translates to:
  /// **'评分'**
  String get translationRating;

  /// No description provided for @translationSelectImportance.
  ///
  /// In zh, this message translates to:
  /// **'选择重要程度'**
  String get translationSelectImportance;

  /// No description provided for @translationDelete.
  ///
  /// In zh, this message translates to:
  /// **'删除翻译'**
  String get translationDelete;

  /// No description provided for @translationDeleteConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定要删除这条翻译记录吗？'**
  String get translationDeleteConfirm;

  /// No description provided for @translationOriginal.
  ///
  /// In zh, this message translates to:
  /// **'原文'**
  String get translationOriginal;

  /// No description provided for @translationTranslated.
  ///
  /// In zh, this message translates to:
  /// **'译文'**
  String get translationTranslated;

  /// No description provided for @translationHistorySessionOnly.
  ///
  /// In zh, this message translates to:
  /// **'历史记录仅在当前会话有效'**
  String get translationHistorySessionOnly;

  /// No description provided for @translationJustNow.
  ///
  /// In zh, this message translates to:
  /// **'刚刚'**
  String get translationJustNow;

  /// No description provided for @translationMinutesAgo.
  ///
  /// In zh, this message translates to:
  /// **'{minutes}分钟前'**
  String translationMinutesAgo(int minutes);

  /// No description provided for @translationHoursAgo.
  ///
  /// In zh, this message translates to:
  /// **'{hours}小时前'**
  String translationHoursAgo(int hours);

  /// No description provided for @translationToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get translationToday;

  /// No description provided for @translationYesterday.
  ///
  /// In zh, this message translates to:
  /// **'昨天'**
  String get translationYesterday;

  /// No description provided for @translationDaysAgo.
  ///
  /// In zh, this message translates to:
  /// **'{days}天前'**
  String translationDaysAgo(int days);

  /// No description provided for @translationSourceLanguage.
  ///
  /// In zh, this message translates to:
  /// **'源语言'**
  String get translationSourceLanguage;

  /// No description provided for @translationTargetLanguage.
  ///
  /// In zh, this message translates to:
  /// **'目标语言'**
  String get translationTargetLanguage;

  /// No description provided for @translationSwapLanguages.
  ///
  /// In zh, this message translates to:
  /// **'交换语言'**
  String get translationSwapLanguages;

  /// No description provided for @translationDetectLanguage.
  ///
  /// In zh, this message translates to:
  /// **'检测语言'**
  String get translationDetectLanguage;

  /// No description provided for @translationHistoryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无翻译历史'**
  String get translationHistoryEmpty;

  /// No description provided for @memoryEvidenceChain.
  ///
  /// In zh, this message translates to:
  /// **'证据链'**
  String get memoryEvidenceChain;

  /// No description provided for @memoryNoEvidence.
  ///
  /// In zh, this message translates to:
  /// **'暂无证据'**
  String get memoryNoEvidence;

  /// No description provided for @memoryCurrentVersion.
  ///
  /// In zh, this message translates to:
  /// **'当前版本'**
  String get memoryCurrentVersion;

  /// No description provided for @memoryVersionHistory.
  ///
  /// In zh, this message translates to:
  /// **'版本历史'**
  String get memoryVersionHistory;

  /// No description provided for @memorySortNewest.
  ///
  /// In zh, this message translates to:
  /// **'最新'**
  String get memorySortNewest;

  /// No description provided for @memorySortOldest.
  ///
  /// In zh, this message translates to:
  /// **'最旧'**
  String get memorySortOldest;

  /// No description provided for @memorySortImportance.
  ///
  /// In zh, this message translates to:
  /// **'重要度'**
  String get memorySortImportance;

  /// No description provided for @memoryEvidenceResolveFailed.
  ///
  /// In zh, this message translates to:
  /// **'证据解析失败'**
  String get memoryEvidenceResolveFailed;

  /// No description provided for @memoryStatus.
  ///
  /// In zh, this message translates to:
  /// **'状态'**
  String get memoryStatus;

  /// No description provided for @memoryGoalDate.
  ///
  /// In zh, this message translates to:
  /// **'目标日期'**
  String get memoryGoalDate;

  /// No description provided for @memoryDeadline.
  ///
  /// In zh, this message translates to:
  /// **'截止时间'**
  String get memoryDeadline;

  /// No description provided for @memoryLastUpdated.
  ///
  /// In zh, this message translates to:
  /// **'最后更新'**
  String get memoryLastUpdated;

  /// No description provided for @memorySource.
  ///
  /// In zh, this message translates to:
  /// **'来源'**
  String get memorySource;

  /// No description provided for @memoryOccurredAt.
  ///
  /// In zh, this message translates to:
  /// **'发生时间'**
  String get memoryOccurredAt;

  /// No description provided for @memoryImportanceScore.
  ///
  /// In zh, this message translates to:
  /// **'重要度'**
  String get memoryImportanceScore;

  /// No description provided for @memoryRetractedAt.
  ///
  /// In zh, this message translates to:
  /// **'撤回时间'**
  String get memoryRetractedAt;

  /// No description provided for @memoryUpdate.
  ///
  /// In zh, this message translates to:
  /// **'更新'**
  String get memoryUpdate;

  /// No description provided for @memoryConfidence.
  ///
  /// In zh, this message translates to:
  /// **'置信度'**
  String get memoryConfidence;

  /// No description provided for @memoryDiff.
  ///
  /// In zh, this message translates to:
  /// **'Diff'**
  String get memoryDiff;

  /// No description provided for @memoryRevertToVersion.
  ///
  /// In zh, this message translates to:
  /// **'撤回到此版本'**
  String get memoryRevertToVersion;

  /// No description provided for @memoryNeedEnableRetraction.
  ///
  /// In zh, this message translates to:
  /// **'需要开启 ENABLE_MEMORY_RETRACTION'**
  String get memoryNeedEnableRetraction;

  /// No description provided for @memoryInitialVersion.
  ///
  /// In zh, this message translates to:
  /// **'初始版本'**
  String get memoryInitialVersion;

  /// No description provided for @memoryNoChanges.
  ///
  /// In zh, this message translates to:
  /// **'无变化'**
  String get memoryNoChanges;

  /// No description provided for @memoryRevertNotEnabled.
  ///
  /// In zh, this message translates to:
  /// **'Revert 功能尚未启用'**
  String get memoryRevertNotEnabled;

  /// No description provided for @memoryWhyThisMemory.
  ///
  /// In zh, this message translates to:
  /// **'为什么有这条记忆？'**
  String get memoryWhyThisMemory;

  /// No description provided for @memoryEvidenceCount.
  ///
  /// In zh, this message translates to:
  /// **'证据数'**
  String get memoryEvidenceCount;

  /// No description provided for @memoryVersions.
  ///
  /// In zh, this message translates to:
  /// **'版本数'**
  String get memoryVersions;

  /// No description provided for @memoryBudget.
  ///
  /// In zh, this message translates to:
  /// **'预算'**
  String get memoryBudget;

  /// No description provided for @memoryViewEvidence.
  ///
  /// In zh, this message translates to:
  /// **'查看证据'**
  String get memoryViewEvidence;

  /// No description provided for @memoryAllowedCapture.
  ///
  /// In zh, this message translates to:
  /// **'已允许捕获'**
  String get memoryAllowedCapture;

  /// No description provided for @memoryCaptureLevel.
  ///
  /// In zh, this message translates to:
  /// **'捕获级别'**
  String get memoryCaptureLevel;

  /// No description provided for @memoryTypeNone.
  ///
  /// In zh, this message translates to:
  /// **'无'**
  String get memoryTypeNone;

  /// No description provided for @memoryTypePreference.
  ///
  /// In zh, this message translates to:
  /// **'偏好'**
  String get memoryTypePreference;

  /// No description provided for @memoryTypeGoal.
  ///
  /// In zh, this message translates to:
  /// **'目标'**
  String get memoryTypeGoal;

  /// No description provided for @memoryTypeEpisodic.
  ///
  /// In zh, this message translates to:
  /// **'经历'**
  String get memoryTypeEpisodic;

  /// No description provided for @memoryDisabledHint.
  ///
  /// In zh, this message translates to:
  /// **'当前已关闭长期记忆，后续不会记录此类记忆。'**
  String get memoryDisabledHint;

  /// No description provided for @memoryPreferenceDisabledHint.
  ///
  /// In zh, this message translates to:
  /// **'当前设置已关闭偏好捕获，后续不会记录此类记忆。'**
  String get memoryPreferenceDisabledHint;

  /// No description provided for @memoryGoalDisabledHint.
  ///
  /// In zh, this message translates to:
  /// **'当前设置已关闭目标捕获，后续不会记录此类记忆。'**
  String get memoryGoalDisabledHint;

  /// No description provided for @memoryEpisodicDisabledHint.
  ///
  /// In zh, this message translates to:
  /// **'当前设置已关闭经历捕获，后续不会记录此类记忆。'**
  String get memoryEpisodicDisabledHint;

  /// No description provided for @memorySourceBlockedHint.
  ///
  /// In zh, this message translates to:
  /// **'该来源已被屏蔽，后续不会记录此类记忆。'**
  String get memorySourceBlockedHint;

  /// No description provided for @memoryKeyBlockedHint.
  ///
  /// In zh, this message translates to:
  /// **'该偏好已被屏蔽，后续不会记录此类记忆。'**
  String get memoryKeyBlockedHint;

  /// No description provided for @memoryExplanationPreference.
  ///
  /// In zh, this message translates to:
  /// **'已记录，因为您的偏好最近更新了。'**
  String get memoryExplanationPreference;

  /// No description provided for @memoryExplanationEpisodic.
  ///
  /// In zh, this message translates to:
  /// **'已记录，因为这段经历被标记为重要。'**
  String get memoryExplanationEpisodic;

  /// No description provided for @memoryExplanationGoal.
  ///
  /// In zh, this message translates to:
  /// **'已记录，以保持您的活跃目标可见。'**
  String get memoryExplanationGoal;

  /// No description provided for @memoryCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制记忆内容'**
  String get memoryCopied;

  /// No description provided for @memoryExportView.
  ///
  /// In zh, this message translates to:
  /// **'导出视图'**
  String get memoryExportView;

  /// No description provided for @memoryCorrectionActions.
  ///
  /// In zh, this message translates to:
  /// **'纠错操作'**
  String get memoryCorrectionActions;

  /// No description provided for @memoryCorrectionReject.
  ///
  /// In zh, this message translates to:
  /// **'不正确'**
  String get memoryCorrectionReject;

  /// No description provided for @memoryCorrectionNoLongerApplies.
  ///
  /// In zh, this message translates to:
  /// **'不再适用'**
  String get memoryCorrectionNoLongerApplies;

  /// No description provided for @memoryCorrectionLowerConfidence.
  ///
  /// In zh, this message translates to:
  /// **'置信度较低'**
  String get memoryCorrectionLowerConfidence;

  /// No description provided for @memoryCorrectionMerge.
  ///
  /// In zh, this message translates to:
  /// **'合并'**
  String get memoryCorrectionMerge;

  /// No description provided for @memoryMergeComingSoon.
  ///
  /// In zh, this message translates to:
  /// **'合并功能即将上线'**
  String get memoryMergeComingSoon;

  /// No description provided for @memoryCorrectionSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'已提交纠错'**
  String get memoryCorrectionSubmitted;

  /// No description provided for @memoryCorrectionFailed.
  ///
  /// In zh, this message translates to:
  /// **'纠错失败'**
  String get memoryCorrectionFailed;

  /// No description provided for @memoryHistoryLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'历史记录加载失败'**
  String get memoryHistoryLoadFailed;

  /// No description provided for @memorySettingsLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载记忆设置失败'**
  String get memorySettingsLoadFailed;

  /// No description provided for @memoryAddEvidence.
  ///
  /// In zh, this message translates to:
  /// **'添加证据'**
  String get memoryAddEvidence;

  /// No description provided for @memoryEvidenceType.
  ///
  /// In zh, this message translates to:
  /// **'证据类型'**
  String get memoryEvidenceType;

  /// No description provided for @memoryEvidenceSource.
  ///
  /// In zh, this message translates to:
  /// **'来源'**
  String get memoryEvidenceSource;

  /// No description provided for @memoryEvidenceContent.
  ///
  /// In zh, this message translates to:
  /// **'内容'**
  String get memoryEvidenceContent;

  /// No description provided for @shareOptionsTitle.
  ///
  /// In zh, this message translates to:
  /// **'分享成就'**
  String get shareOptionsTitle;

  /// No description provided for @shareToWeChatFriends.
  ///
  /// In zh, this message translates to:
  /// **'分享到微信好友'**
  String get shareToWeChatFriends;

  /// No description provided for @shareToWeChatMoments.
  ///
  /// In zh, this message translates to:
  /// **'分享到朋友圈'**
  String get shareToWeChatMoments;

  /// No description provided for @shareToSystem.
  ///
  /// In zh, this message translates to:
  /// **'系统分享'**
  String get shareToSystem;

  /// No description provided for @shareToCommunity.
  ///
  /// In zh, this message translates to:
  /// **'分享到社群'**
  String get shareToCommunity;

  /// No description provided for @saveImageToGallery.
  ///
  /// In zh, this message translates to:
  /// **'保存图片'**
  String get saveImageToGallery;

  /// No description provided for @copyDeepLink.
  ///
  /// In zh, this message translates to:
  /// **'复制链接'**
  String get copyDeepLink;

  /// No description provided for @linkCopied.
  ///
  /// In zh, this message translates to:
  /// **'链接已复制'**
  String get linkCopied;

  /// No description provided for @wechatNotInstalled.
  ///
  /// In zh, this message translates to:
  /// **'请先安装微信'**
  String get wechatNotInstalled;

  /// No description provided for @shareTemplateTitle.
  ///
  /// In zh, this message translates to:
  /// **'选择模板'**
  String get shareTemplateTitle;

  /// No description provided for @shareTemplateCosmic.
  ///
  /// In zh, this message translates to:
  /// **'星空'**
  String get shareTemplateCosmic;

  /// No description provided for @shareTemplateMinimal.
  ///
  /// In zh, this message translates to:
  /// **'简约'**
  String get shareTemplateMinimal;

  /// No description provided for @shareTemplateNeon.
  ///
  /// In zh, this message translates to:
  /// **'霓虹'**
  String get shareTemplateNeon;

  /// No description provided for @shareTemplateElegant.
  ///
  /// In zh, this message translates to:
  /// **'典雅'**
  String get shareTemplateElegant;

  /// No description provided for @shareTemplateCosmicDesc.
  ///
  /// In zh, this message translates to:
  /// **'深蓝渐变，金色粒子漂浮，柔和光晕'**
  String get shareTemplateCosmicDesc;

  /// No description provided for @shareTemplateMinimalDesc.
  ///
  /// In zh, this message translates to:
  /// **'纯色背景，极简线条，黑色主文字'**
  String get shareTemplateMinimalDesc;

  /// No description provided for @shareTemplateNeonDesc.
  ///
  /// In zh, this message translates to:
  /// **'纯黑背景，霓虹发光，赛博朋克配色'**
  String get shareTemplateNeonDesc;

  /// No description provided for @shareTemplateElegantDesc.
  ///
  /// In zh, this message translates to:
  /// **'米色金色背景，优雅衬线字体，金色装饰'**
  String get shareTemplateElegantDesc;

  /// No description provided for @sharePrivacyTitle.
  ///
  /// In zh, this message translates to:
  /// **'隐私设置'**
  String get sharePrivacyTitle;

  /// No description provided for @sharePrivacyDisplayName.
  ///
  /// In zh, this message translates to:
  /// **'显示名称'**
  String get sharePrivacyDisplayName;

  /// No description provided for @sharePrivacyDisplayNameHint.
  ///
  /// In zh, this message translates to:
  /// **'使用默认昵称'**
  String get sharePrivacyDisplayNameHint;

  /// No description provided for @sharePrivacyDisplayNameNote.
  ///
  /// In zh, this message translates to:
  /// **'留空则使用您的默认昵称'**
  String get sharePrivacyDisplayNameNote;

  /// No description provided for @sharePrivacyShowAvatar.
  ///
  /// In zh, this message translates to:
  /// **'显示头像'**
  String get sharePrivacyShowAvatar;

  /// No description provided for @sharePrivacyShowAvatarDesc.
  ///
  /// In zh, this message translates to:
  /// **'在分享卡上显示您的头像'**
  String get sharePrivacyShowAvatarDesc;

  /// No description provided for @sharePrivacyShowDate.
  ///
  /// In zh, this message translates to:
  /// **'显示解锁日期'**
  String get sharePrivacyShowDate;

  /// No description provided for @sharePrivacyShowDateDesc.
  ///
  /// In zh, this message translates to:
  /// **'显示成就解锁的具体日期'**
  String get sharePrivacyShowDateDesc;

  /// No description provided for @sharePrivacyShowStats.
  ///
  /// In zh, this message translates to:
  /// **'显示进度统计'**
  String get sharePrivacyShowStats;

  /// No description provided for @sharePrivacyShowStatsDesc.
  ///
  /// In zh, this message translates to:
  /// **'显示进度条和统计数据'**
  String get sharePrivacyShowStatsDesc;

  /// No description provided for @sharePrivacyShowFirstBadge.
  ///
  /// In zh, this message translates to:
  /// **'首位解锁者徽章'**
  String get sharePrivacyShowFirstBadge;

  /// No description provided for @sharePrivacyShowFirstBadgeDesc.
  ///
  /// In zh, this message translates to:
  /// **'如您是首位解锁者，显示专属徽章'**
  String get sharePrivacyShowFirstBadgeDesc;

  /// No description provided for @sharePreviewLoading.
  ///
  /// In zh, this message translates to:
  /// **'正在生成预览...'**
  String get sharePreviewLoading;

  /// No description provided for @sharePreviewError.
  ///
  /// In zh, this message translates to:
  /// **'预览生成失败'**
  String get sharePreviewError;

  /// No description provided for @shareRegenerateCard.
  ///
  /// In zh, this message translates to:
  /// **'重新生成'**
  String get shareRegenerateCard;

  /// No description provided for @notificationPermissionStatus.
  ///
  /// In zh, this message translates to:
  /// **'通知权限状态'**
  String get notificationPermissionStatus;

  /// No description provided for @notificationPermissionGranted.
  ///
  /// In zh, this message translates to:
  /// **'已授权'**
  String get notificationPermissionGranted;

  /// No description provided for @notificationPermissionDenied.
  ///
  /// In zh, this message translates to:
  /// **'未授权'**
  String get notificationPermissionDenied;

  /// No description provided for @notificationPermissionPartial.
  ///
  /// In zh, this message translates to:
  /// **'部分授权'**
  String get notificationPermissionPartial;

  /// No description provided for @notificationPermissionRequest.
  ///
  /// In zh, this message translates to:
  /// **'请求权限'**
  String get notificationPermissionRequest;

  /// No description provided for @notificationPermissionOpenSettings.
  ///
  /// In zh, this message translates to:
  /// **'打开设置'**
  String get notificationPermissionOpenSettings;

  /// No description provided for @notificationPermissionDeniedHint.
  ///
  /// In zh, this message translates to:
  /// **'通知权限被拒绝，请在系统设置中开启'**
  String get notificationPermissionDeniedHint;

  /// No description provided for @notificationPermissionPartialHint.
  ///
  /// In zh, this message translates to:
  /// **'部分通知功能受限，建议开启完整权限'**
  String get notificationPermissionPartialHint;

  /// No description provided for @visualElementsTitle.
  ///
  /// In zh, this message translates to:
  /// **'视觉元素'**
  String get visualElementsTitle;

  /// No description provided for @visualElementsUnlockProgress.
  ///
  /// In zh, this message translates to:
  /// **'解锁进度'**
  String get visualElementsUnlockProgress;

  /// No description provided for @visualElementsEquipped.
  ///
  /// In zh, this message translates to:
  /// **'已装备'**
  String get visualElementsEquipped;

  /// No description provided for @visualElementsRecommended.
  ///
  /// In zh, this message translates to:
  /// **'为你推荐'**
  String get visualElementsRecommended;

  /// No description provided for @visualRecommendationFocus.
  ///
  /// In zh, this message translates to:
  /// **'适合专注学习'**
  String get visualRecommendationFocus;

  /// No description provided for @visualRecommendationRelax.
  ///
  /// In zh, this message translates to:
  /// **'适合休息放松'**
  String get visualRecommendationRelax;

  /// No description provided for @visualRecommendationSprint.
  ///
  /// In zh, this message translates to:
  /// **'适合冲刺模式'**
  String get visualRecommendationSprint;

  /// No description provided for @visualRecommendationNight.
  ///
  /// In zh, this message translates to:
  /// **'夜间护眼'**
  String get visualRecommendationNight;

  /// No description provided for @visualRecommendationStreak.
  ///
  /// In zh, this message translates to:
  /// **'连胜加成'**
  String get visualRecommendationStreak;

  /// No description provided for @visualElementTabAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get visualElementTabAll;

  /// No description provided for @visualElementTabBackground.
  ///
  /// In zh, this message translates to:
  /// **'背景'**
  String get visualElementTabBackground;

  /// No description provided for @visualElementTabParticle.
  ///
  /// In zh, this message translates to:
  /// **'粒子'**
  String get visualElementTabParticle;

  /// No description provided for @visualElementTabEffect.
  ///
  /// In zh, this message translates to:
  /// **'特效'**
  String get visualElementTabEffect;

  /// No description provided for @visualElementTabUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'已解锁'**
  String get visualElementTabUnlocked;

  /// No description provided for @visualElementEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无视觉元素'**
  String get visualElementEmpty;

  /// No description provided for @visualElementFilter.
  ///
  /// In zh, this message translates to:
  /// **'筛选'**
  String get visualElementFilter;

  /// No description provided for @visualElementApplyFilter.
  ///
  /// In zh, this message translates to:
  /// **'应用筛选'**
  String get visualElementApplyFilter;

  /// No description provided for @visualElementType.
  ///
  /// In zh, this message translates to:
  /// **'类型'**
  String get visualElementType;

  /// No description provided for @visualElementCategory.
  ///
  /// In zh, this message translates to:
  /// **'分类'**
  String get visualElementCategory;

  /// No description provided for @visualElementSource.
  ///
  /// In zh, this message translates to:
  /// **'来源'**
  String get visualElementSource;

  /// No description provided for @visualElementRarity.
  ///
  /// In zh, this message translates to:
  /// **'稀有度'**
  String get visualElementRarity;

  /// No description provided for @visualElementEquipped.
  ///
  /// In zh, this message translates to:
  /// **'已装备'**
  String get visualElementEquipped;

  /// No description provided for @visualElementUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'已解锁'**
  String get visualElementUnlocked;

  /// No description provided for @visualElementLocked.
  ///
  /// In zh, this message translates to:
  /// **'未解锁'**
  String get visualElementLocked;

  /// No description provided for @visualElementEquip.
  ///
  /// In zh, this message translates to:
  /// **'装备'**
  String get visualElementEquip;

  /// No description provided for @visualElementUnequip.
  ///
  /// In zh, this message translates to:
  /// **'卸下'**
  String get visualElementUnequip;

  /// No description provided for @visualElementEquipSuccess.
  ///
  /// In zh, this message translates to:
  /// **'装备成功'**
  String get visualElementEquipSuccess;

  /// No description provided for @visualElementEquipFailed.
  ///
  /// In zh, this message translates to:
  /// **'装备失败'**
  String get visualElementEquipFailed;

  /// No description provided for @visualElementUnequipSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已卸下'**
  String get visualElementUnequipSuccess;

  /// No description provided for @visualElementUnequipFailed.
  ///
  /// In zh, this message translates to:
  /// **'卸下失败'**
  String get visualElementUnequipFailed;

  /// No description provided for @visualElementUnlockSystem.
  ///
  /// In zh, this message translates to:
  /// **'系统赠送'**
  String get visualElementUnlockSystem;

  /// No description provided for @visualElementUnlockAchievement.
  ///
  /// In zh, this message translates to:
  /// **'成就解锁'**
  String get visualElementUnlockAchievement;

  /// No description provided for @visualElementUnlockShop.
  ///
  /// In zh, this message translates to:
  /// **'商城购买'**
  String get visualElementUnlockShop;

  /// No description provided for @visualElementUnlockEvent.
  ///
  /// In zh, this message translates to:
  /// **'活动获取'**
  String get visualElementUnlockEvent;

  /// No description provided for @visualElementUnlockSeason.
  ///
  /// In zh, this message translates to:
  /// **'赛季奖励'**
  String get visualElementUnlockSeason;

  /// No description provided for @visualElementUnlockHintSystem.
  ///
  /// In zh, this message translates to:
  /// **'系统自动赠送'**
  String get visualElementUnlockHintSystem;

  /// No description provided for @visualElementUnlockHintAchievement.
  ///
  /// In zh, this message translates to:
  /// **'完成成就「{achievement}」解锁'**
  String visualElementUnlockHintAchievement(Object achievement);

  /// No description provided for @visualElementUnlockHintAchievementDefault.
  ///
  /// In zh, this message translates to:
  /// **'完成指定成就解锁'**
  String get visualElementUnlockHintAchievementDefault;

  /// No description provided for @visualElementUnlockHintShop.
  ///
  /// In zh, this message translates to:
  /// **'在商城花费 {price} 光子购买'**
  String visualElementUnlockHintShop(Object price);

  /// No description provided for @visualElementUnlockHintShopDefault.
  ///
  /// In zh, this message translates to:
  /// **'在商城购买'**
  String get visualElementUnlockHintShopDefault;

  /// No description provided for @visualElementUnlockHintEvent.
  ///
  /// In zh, this message translates to:
  /// **'参与限时活动获取'**
  String get visualElementUnlockHintEvent;

  /// No description provided for @visualElementUnlockHintSeason.
  ///
  /// In zh, this message translates to:
  /// **'赛季奖励解锁'**
  String get visualElementUnlockHintSeason;

  /// No description provided for @visualElementBackground.
  ///
  /// In zh, this message translates to:
  /// **'背景'**
  String get visualElementBackground;

  /// No description provided for @visualElementParticle.
  ///
  /// In zh, this message translates to:
  /// **'粒子'**
  String get visualElementParticle;

  /// No description provided for @visualElementEffect.
  ///
  /// In zh, this message translates to:
  /// **'特效'**
  String get visualElementEffect;

  /// No description provided for @visualElementBundle.
  ///
  /// In zh, this message translates to:
  /// **'套装'**
  String get visualElementBundle;

  /// No description provided for @visualElementsEntrySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'自定义你的场景'**
  String get visualElementsEntrySubtitle;

  /// No description provided for @visualElementShare.
  ///
  /// In zh, this message translates to:
  /// **'分享'**
  String get visualElementShare;

  /// No description provided for @visualElementShareMessage.
  ///
  /// In zh, this message translates to:
  /// **'我在 Sparkle 使用了「{name}」的视觉元素！'**
  String visualElementShareMessage(Object name);

  /// No description provided for @visualElementShareFailed.
  ///
  /// In zh, this message translates to:
  /// **'分享失败：{error}'**
  String visualElementShareFailed(Object error);

  /// No description provided for @visualElementShareUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'预览尚未就绪'**
  String get visualElementShareUnavailable;

  /// No description provided for @visualElementEventTitle.
  ///
  /// In zh, this message translates to:
  /// **'限时活动'**
  String get visualElementEventTitle;

  /// No description provided for @visualElementEventEndsIn.
  ///
  /// In zh, this message translates to:
  /// **'距离结束 {time}'**
  String visualElementEventEndsIn(Object time);

  /// No description provided for @visualElementEventEnded.
  ///
  /// In zh, this message translates to:
  /// **'活动已结束'**
  String get visualElementEventEnded;

  /// No description provided for @visualElementEventCountdownDays.
  ///
  /// In zh, this message translates to:
  /// **'{days}天 {hours}小时'**
  String visualElementEventCountdownDays(Object days, Object hours);

  /// No description provided for @visualElementEventCountdownHours.
  ///
  /// In zh, this message translates to:
  /// **'{hours}小时 {minutes}分钟'**
  String visualElementEventCountdownHours(Object hours, Object minutes);

  /// No description provided for @visualElementEventCountdownMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{minutes}分钟'**
  String visualElementEventCountdownMinutes(Object minutes);

  /// No description provided for @visualElementCategorySpace.
  ///
  /// In zh, this message translates to:
  /// **'太空'**
  String get visualElementCategorySpace;

  /// No description provided for @visualElementCategoryNature.
  ///
  /// In zh, this message translates to:
  /// **'自然'**
  String get visualElementCategoryNature;

  /// No description provided for @visualElementCategoryCyberpunk.
  ///
  /// In zh, this message translates to:
  /// **'赛博朋克'**
  String get visualElementCategoryCyberpunk;

  /// No description provided for @visualElementCategoryAbstract.
  ///
  /// In zh, this message translates to:
  /// **'抽象'**
  String get visualElementCategoryAbstract;

  /// No description provided for @visualElementCategoryAmbient.
  ///
  /// In zh, this message translates to:
  /// **'氛围'**
  String get visualElementCategoryAmbient;

  /// No description provided for @visualElementEmptyType.
  ///
  /// In zh, this message translates to:
  /// **'暂无{type}'**
  String visualElementEmptyType(Object type);

  /// No description provided for @visualElementStatus.
  ///
  /// In zh, this message translates to:
  /// **'状态'**
  String get visualElementStatus;

  /// No description provided for @visualElementSort.
  ///
  /// In zh, this message translates to:
  /// **'排序'**
  String get visualElementSort;

  /// No description provided for @visualElementSortDefault.
  ///
  /// In zh, this message translates to:
  /// **'默认'**
  String get visualElementSortDefault;

  /// No description provided for @visualElementSortName.
  ///
  /// In zh, this message translates to:
  /// **'名称'**
  String get visualElementSortName;

  /// No description provided for @visualElementSortRarity.
  ///
  /// In zh, this message translates to:
  /// **'稀有度'**
  String get visualElementSortRarity;

  /// No description provided for @visualElementSortUnlockDate.
  ///
  /// In zh, this message translates to:
  /// **'解锁时间'**
  String get visualElementSortUnlockDate;

  /// No description provided for @visualElementUnlockTitle.
  ///
  /// In zh, this message translates to:
  /// **'解锁视觉元素'**
  String get visualElementUnlockTitle;

  /// No description provided for @visualElementUnlockSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'恭喜获得新的视觉元素！'**
  String get visualElementUnlockSubtitle;

  /// No description provided for @visualElementViewCollection.
  ///
  /// In zh, this message translates to:
  /// **'查看收藏'**
  String get visualElementViewCollection;

  /// No description provided for @achievementMapFocusTooltip.
  ///
  /// In zh, this message translates to:
  /// **'定位到最近的成就'**
  String get achievementMapFocusTooltip;

  /// No description provided for @achievementMapFocusHint.
  ///
  /// In zh, this message translates to:
  /// **'尝试解锁：{name}'**
  String achievementMapFocusHint(Object name);

  /// No description provided for @cognitiveDimensionMemory.
  ///
  /// In zh, this message translates to:
  /// **'记忆'**
  String get cognitiveDimensionMemory;

  /// No description provided for @cognitiveDimensionUnderstanding.
  ///
  /// In zh, this message translates to:
  /// **'理解'**
  String get cognitiveDimensionUnderstanding;

  /// No description provided for @cognitiveDimensionApplication.
  ///
  /// In zh, this message translates to:
  /// **'应用'**
  String get cognitiveDimensionApplication;

  /// No description provided for @cognitiveDimensionAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'分析'**
  String get cognitiveDimensionAnalysis;

  /// No description provided for @cognitiveDimensionEvaluation.
  ///
  /// In zh, this message translates to:
  /// **'评价'**
  String get cognitiveDimensionEvaluation;

  /// No description provided for @cognitiveDimensionCreation.
  ///
  /// In zh, this message translates to:
  /// **'创造'**
  String get cognitiveDimensionCreation;

  /// No description provided for @photonTransactionGrantAchievement.
  ///
  /// In zh, this message translates to:
  /// **'成就奖励'**
  String get photonTransactionGrantAchievement;

  /// No description provided for @photonTransactionGrantDailyFirst.
  ///
  /// In zh, this message translates to:
  /// **'每日首成奖励'**
  String get photonTransactionGrantDailyFirst;

  /// No description provided for @photonTransactionGrantContract.
  ///
  /// In zh, this message translates to:
  /// **'契约奖励'**
  String get photonTransactionGrantContract;

  /// No description provided for @photonTransactionGrantContractBonus.
  ///
  /// In zh, this message translates to:
  /// **'契约加成'**
  String get photonTransactionGrantContractBonus;

  /// No description provided for @photonTransactionDeductContractStake.
  ///
  /// In zh, this message translates to:
  /// **'契约押注'**
  String get photonTransactionDeductContractStake;

  /// No description provided for @photonTransactionPurchase.
  ///
  /// In zh, this message translates to:
  /// **'购买'**
  String get photonTransactionPurchase;

  /// No description provided for @photonTransactionTransferOut.
  ///
  /// In zh, this message translates to:
  /// **'转出'**
  String get photonTransactionTransferOut;

  /// No description provided for @photonTransactionTransferIn.
  ///
  /// In zh, this message translates to:
  /// **'转入'**
  String get photonTransactionTransferIn;

  /// No description provided for @photonTransactionRefund.
  ///
  /// In zh, this message translates to:
  /// **'退款'**
  String get photonTransactionRefund;

  /// No description provided for @photonTransactionPenalty.
  ///
  /// In zh, this message translates to:
  /// **'惩罚'**
  String get photonTransactionPenalty;

  /// No description provided for @photonTransactionAdminAdjustment.
  ///
  /// In zh, this message translates to:
  /// **'管理员调整'**
  String get photonTransactionAdminAdjustment;

  /// No description provided for @shopItemTypeSkin.
  ///
  /// In zh, this message translates to:
  /// **'皮肤'**
  String get shopItemTypeSkin;

  /// No description provided for @shopItemTypeTitle.
  ///
  /// In zh, this message translates to:
  /// **'称号'**
  String get shopItemTypeTitle;

  /// No description provided for @shopItemTypeConsumable.
  ///
  /// In zh, this message translates to:
  /// **'消耗品'**
  String get shopItemTypeConsumable;

  /// No description provided for @shopItemTypeBoost.
  ///
  /// In zh, this message translates to:
  /// **'增益'**
  String get shopItemTypeBoost;

  /// No description provided for @shopItemTypeVisualElement.
  ///
  /// In zh, this message translates to:
  /// **'视觉元素'**
  String get shopItemTypeVisualElement;

  /// No description provided for @taskDueDateUnset.
  ///
  /// In zh, this message translates to:
  /// **'无截止日期'**
  String get taskDueDateUnset;

  /// No description provided for @chatAchievementUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAchievementUnlocked(Object arg0);

  /// No description provided for @chatActionErrorSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatActionErrorSuggestion(Object arg0);

  /// No description provided for @chatActionErrorTitle.
  ///
  /// In zh, this message translates to:
  /// **'操作错误'**
  String get chatActionErrorTitle;

  /// No description provided for @chatActionIgnore.
  ///
  /// In zh, this message translates to:
  /// **'忽略'**
  String get chatActionIgnore;

  /// No description provided for @chatActionLater.
  ///
  /// In zh, this message translates to:
  /// **'稍后'**
  String get chatActionLater;

  /// No description provided for @chatActionReviewed.
  ///
  /// In zh, this message translates to:
  /// **'已审阅'**
  String get chatActionReviewed;

  /// No description provided for @chatActionStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get chatActionStatusCompleted;

  /// No description provided for @chatActionStatusConfirmed.
  ///
  /// In zh, this message translates to:
  /// **'已确认'**
  String get chatActionStatusConfirmed;

  /// No description provided for @chatActionStatusDismissed.
  ///
  /// In zh, this message translates to:
  /// **'已忽略'**
  String get chatActionStatusDismissed;

  /// No description provided for @chatActionStatusFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get chatActionStatusFailed;

  /// No description provided for @chatActionStatusProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get chatActionStatusProcessing;

  /// No description provided for @chatActionStatusUpdate.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatActionStatusUpdate(Object arg0);

  /// No description provided for @chatActionSuggestedActions.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatActionSuggestedActions(Object arg0);

  /// No description provided for @chatActionTitleAddError.
  ///
  /// In zh, this message translates to:
  /// **'添加错误'**
  String get chatActionTitleAddError;

  /// No description provided for @chatActionTitleBlockedInput.
  ///
  /// In zh, this message translates to:
  /// **'输入被阻止'**
  String get chatActionTitleBlockedInput;

  /// No description provided for @chatActionTitleContinuity.
  ///
  /// In zh, this message translates to:
  /// **'延续性'**
  String get chatActionTitleContinuity;

  /// No description provided for @chatActionTitleCreatePlan.
  ///
  /// In zh, this message translates to:
  /// **'创建计划'**
  String get chatActionTitleCreatePlan;

  /// No description provided for @chatActionTitleCreateTask.
  ///
  /// In zh, this message translates to:
  /// **'创建任务'**
  String get chatActionTitleCreateTask;

  /// No description provided for @chatActionTitleDefault.
  ///
  /// In zh, this message translates to:
  /// **'默认标题'**
  String get chatActionTitleDefault;

  /// No description provided for @chatActionTitleEvolution.
  ///
  /// In zh, this message translates to:
  /// **'演进'**
  String get chatActionTitleEvolution;

  /// No description provided for @chatActionTitleExecutionSummary.
  ///
  /// In zh, this message translates to:
  /// **'执行摘要'**
  String get chatActionTitleExecutionSummary;

  /// No description provided for @chatActionTitleFocusSprint.
  ///
  /// In zh, this message translates to:
  /// **'专注冲刺'**
  String get chatActionTitleFocusSprint;

  /// No description provided for @chatActionTitleModeExplanation.
  ///
  /// In zh, this message translates to:
  /// **'模式说明'**
  String get chatActionTitleModeExplanation;

  /// No description provided for @chatActionTitleNextActions.
  ///
  /// In zh, this message translates to:
  /// **'下一步行动'**
  String get chatActionTitleNextActions;

  /// No description provided for @chatActionTitleNightlyReview.
  ///
  /// In zh, this message translates to:
  /// **'夜间回顾'**
  String get chatActionTitleNightlyReview;

  /// No description provided for @chatActionTitleProgress.
  ///
  /// In zh, this message translates to:
  /// **'进度'**
  String get chatActionTitleProgress;

  /// No description provided for @chatActionTitleReflection.
  ///
  /// In zh, this message translates to:
  /// **'反思'**
  String get chatActionTitleReflection;

  /// No description provided for @chatActionTitleSourceSummary.
  ///
  /// In zh, this message translates to:
  /// **'来源摘要'**
  String get chatActionTitleSourceSummary;

  /// No description provided for @chatActionTitleSystemUpdate.
  ///
  /// In zh, this message translates to:
  /// **'系统更新'**
  String get chatActionTitleSystemUpdate;

  /// No description provided for @chatActionTitleTaskList.
  ///
  /// In zh, this message translates to:
  /// **'任务列表'**
  String get chatActionTitleTaskList;

  /// No description provided for @chatActionTitleUpdatePreference.
  ///
  /// In zh, this message translates to:
  /// **'更新偏好'**
  String get chatActionTitleUpdatePreference;

  /// No description provided for @chatActionViewNextSteps.
  ///
  /// In zh, this message translates to:
  /// **'查看下一步'**
  String get chatActionViewNextSteps;

  /// No description provided for @chatActionViewSources.
  ///
  /// In zh, this message translates to:
  /// **'查看来源'**
  String get chatActionViewSources;

  /// No description provided for @chatAgentRouting.
  ///
  /// In zh, this message translates to:
  /// **'智能路由'**
  String get chatAgentRouting;

  /// No description provided for @chatAgentRoutingFallback.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAgentRoutingFallback(Object arg0);

  /// No description provided for @chatAgentRoutingStrategy.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAgentRoutingStrategy(Object arg0);

  /// No description provided for @chatAlignmentScoreLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAlignmentScoreLabel(Object arg0);

  /// No description provided for @chatAudioParseFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAudioParseFailed(Object arg0);

  /// No description provided for @chatAudioRecordFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAudioRecordFailed(Object arg0);

  /// No description provided for @chatAudioStartFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAudioStartFailed(Object arg0);

  /// No description provided for @chatAudioWsConnectFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatAudioWsConnectFailed(Object arg0);

  /// No description provided for @chatAuthExpired.
  ///
  /// In zh, this message translates to:
  /// **'认证已过期'**
  String get chatAuthExpired;

  /// No description provided for @chatAuthRefreshing.
  ///
  /// In zh, this message translates to:
  /// **'正在刷新认证'**
  String get chatAuthRefreshing;

  /// No description provided for @chatBlockedInputTitle.
  ///
  /// In zh, this message translates to:
  /// **'输入已阻止'**
  String get chatBlockedInputTitle;

  /// No description provided for @chatCitationLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatCitationLabel(Object arg0);

  /// No description provided for @chatCitationRelevance.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatCitationRelevance(Object arg0);

  /// No description provided for @chatCitationSourcesCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatCitationSourcesCount(Object arg0);

  /// No description provided for @chatCollabTimelineTitle.
  ///
  /// In zh, this message translates to:
  /// **'协作时间线'**
  String get chatCollabTimelineTitle;

  /// No description provided for @chatComparisonAfter.
  ///
  /// In zh, this message translates to:
  /// **'之后'**
  String get chatComparisonAfter;

  /// No description provided for @chatComparisonBefore.
  ///
  /// In zh, this message translates to:
  /// **'之前'**
  String get chatComparisonBefore;

  /// No description provided for @chatComparisonCurrentPrevious.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatComparisonCurrentPrevious(Object arg0, Object arg1);

  /// No description provided for @chatCompletionBlocked.
  ///
  /// In zh, this message translates to:
  /// **'补全已阻止'**
  String get chatCompletionBlocked;

  /// No description provided for @chatCompletionDone.
  ///
  /// In zh, this message translates to:
  /// **'补全完成'**
  String get chatCompletionDone;

  /// No description provided for @chatCompletionNeedsInput.
  ///
  /// In zh, this message translates to:
  /// **'需要输入'**
  String get chatCompletionNeedsInput;

  /// No description provided for @chatCompletionPartial.
  ///
  /// In zh, this message translates to:
  /// **'部分完成'**
  String get chatCompletionPartial;

  /// No description provided for @chatCompletionProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get chatCompletionProcessing;

  /// No description provided for @chatConfidenceCautious.
  ///
  /// In zh, this message translates to:
  /// **'谨慎'**
  String get chatConfidenceCautious;

  /// No description provided for @chatConfidenceHigh.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get chatConfidenceHigh;

  /// No description provided for @chatConfidenceLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatConfidenceLabel(Object arg0);

  /// No description provided for @chatConfidenceMedium.
  ///
  /// In zh, this message translates to:
  /// **'中'**
  String get chatConfidenceMedium;

  /// No description provided for @chatConfirmationActionDefault.
  ///
  /// In zh, this message translates to:
  /// **'确认操作'**
  String get chatConfirmationActionDefault;

  /// No description provided for @chatConfirmationConfirmUpdate.
  ///
  /// In zh, this message translates to:
  /// **'确认更新'**
  String get chatConfirmationConfirmUpdate;

  /// No description provided for @chatConfirmationTitleDefault.
  ///
  /// In zh, this message translates to:
  /// **'确认'**
  String get chatConfirmationTitleDefault;

  /// No description provided for @chatConfirmationTitleUpdatePreference.
  ///
  /// In zh, this message translates to:
  /// **'确认更新偏好'**
  String get chatConfirmationTitleUpdatePreference;

  /// No description provided for @chatConfirmationUpdatePreferenceGeneric.
  ///
  /// In zh, this message translates to:
  /// **'更新偏好设置'**
  String get chatConfirmationUpdatePreferenceGeneric;

  /// No description provided for @chatConfirmationUpdatePreferenceKeyOnly.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatConfirmationUpdatePreferenceKeyOnly(Object arg0);

  /// No description provided for @chatConfirmationUpdatePreferenceWithValue.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatConfirmationUpdatePreferenceWithValue(Object arg0, Object arg1);

  /// No description provided for @chatCopiedToClipboard.
  ///
  /// In zh, this message translates to:
  /// **'已复制到剪贴板'**
  String get chatCopiedToClipboard;

  /// No description provided for @chatDagExecutionAbortedDefault.
  ///
  /// In zh, this message translates to:
  /// **'执行已中止'**
  String get chatDagExecutionAbortedDefault;

  /// No description provided for @chatDagExecutionCompleted.
  ///
  /// In zh, this message translates to:
  /// **'执行已完成'**
  String get chatDagExecutionCompleted;

  /// No description provided for @chatDagExecutionEndAbortedDefault.
  ///
  /// In zh, this message translates to:
  /// **'执行已中止'**
  String get chatDagExecutionEndAbortedDefault;

  /// No description provided for @chatDagLayerAborted.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatDagLayerAborted(Object arg0);

  /// No description provided for @chatDagLayerCompleted.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatDagLayerCompleted(Object arg0);

  /// No description provided for @chatDagLayerStart.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1} {arg2}'**
  String chatDagLayerStart(Object arg0, Object arg1, Object arg2);

  /// No description provided for @chatDagStepCompleted.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatDagStepCompleted(Object arg0);

  /// No description provided for @chatDagStepCompletedWithDuration.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatDagStepCompletedWithDuration(Object arg0, Object arg1);

  /// No description provided for @chatDagStepFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatDagStepFailed(Object arg0);

  /// No description provided for @chatDagStepFallback.
  ///
  /// In zh, this message translates to:
  /// **'步骤回退'**
  String get chatDagStepFallback;

  /// No description provided for @chatDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatDurationLabel(Object arg0);

  /// No description provided for @chatErrorWithSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatErrorWithSuggestion(Object arg0, Object arg1);

  /// No description provided for @chatEvolutionExpectedEffect.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatEvolutionExpectedEffect(Object arg0);

  /// No description provided for @chatEvolutionHeadlineDefault.
  ///
  /// In zh, this message translates to:
  /// **'演进过程'**
  String get chatEvolutionHeadlineDefault;

  /// No description provided for @chatEvolutionNextWeekPlan.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatEvolutionNextWeekPlan(Object arg0);

  /// No description provided for @chatEvolutionWhy.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatEvolutionWhy(Object arg0);

  /// No description provided for @chatExecutionCompleted.
  ///
  /// In zh, this message translates to:
  /// **'执行完成'**
  String get chatExecutionCompleted;

  /// No description provided for @chatExecutionFailed.
  ///
  /// In zh, this message translates to:
  /// **'执行失败'**
  String get chatExecutionFailed;

  /// No description provided for @chatExecutionPartial.
  ///
  /// In zh, this message translates to:
  /// **'部分执行'**
  String get chatExecutionPartial;

  /// No description provided for @chatFeedbackThanks.
  ///
  /// In zh, this message translates to:
  /// **'感谢您的反馈！'**
  String get chatFeedbackThanks;

  /// No description provided for @chatFocusSprintDefaultTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注冲刺'**
  String get chatFocusSprintDefaultTitle;

  /// No description provided for @chatFocusStart.
  ///
  /// In zh, this message translates to:
  /// **'开始专注'**
  String get chatFocusStart;

  /// No description provided for @chatInputDocumentClean.
  ///
  /// In zh, this message translates to:
  /// **'清理文档'**
  String get chatInputDocumentClean;

  /// No description provided for @chatInterventionViewPlan.
  ///
  /// In zh, this message translates to:
  /// **'查看计划'**
  String get chatInterventionViewPlan;

  /// No description provided for @chatInterventionViewSettings.
  ///
  /// In zh, this message translates to:
  /// **'查看设置'**
  String get chatInterventionViewSettings;

  /// No description provided for @chatKnowledgeCitationBody.
  ///
  /// In zh, this message translates to:
  /// **'知识引用'**
  String get chatKnowledgeCitationBody;

  /// No description provided for @chatKnowledgeCitationTitle.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatKnowledgeCitationTitle(Object arg0);

  /// No description provided for @chatModeCustomTeam.
  ///
  /// In zh, this message translates to:
  /// **'自定义团队'**
  String get chatModeCustomTeam;

  /// No description provided for @chatModeCustomTeamDesc.
  ///
  /// In zh, this message translates to:
  /// **'选择特定的 AI 助手组成您的专属团队'**
  String get chatModeCustomTeamDesc;

  /// No description provided for @chatModeKeepCurrent.
  ///
  /// In zh, this message translates to:
  /// **'保持当前模式'**
  String get chatModeKeepCurrent;

  /// No description provided for @chatModeSuggestionTitle.
  ///
  /// In zh, this message translates to:
  /// **'模式建议'**
  String get chatModeSuggestionTitle;

  /// No description provided for @chatModeSwitch.
  ///
  /// In zh, this message translates to:
  /// **'切换模式'**
  String get chatModeSwitch;

  /// No description provided for @chatMultiAgentCollab.
  ///
  /// In zh, this message translates to:
  /// **'多智能体协作'**
  String get chatMultiAgentCollab;

  /// No description provided for @chatNextActionLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatNextActionLabel(Object arg0);

  /// No description provided for @chatNextActionsRetryHint.
  ///
  /// In zh, this message translates to:
  /// **'点击重试'**
  String get chatNextActionsRetryHint;

  /// No description provided for @chatNextActionsTitle.
  ///
  /// In zh, this message translates to:
  /// **'下一步行动'**
  String get chatNextActionsTitle;

  /// No description provided for @chatNightlyReviewTodos.
  ///
  /// In zh, this message translates to:
  /// **'夜间待办'**
  String get chatNightlyReviewTodos;

  /// No description provided for @chatNotificationGroupMessage.
  ///
  /// In zh, this message translates to:
  /// **'群组消息'**
  String get chatNotificationGroupMessage;

  /// No description provided for @chatNotificationMention.
  ///
  /// In zh, this message translates to:
  /// **'有人@我'**
  String get chatNotificationMention;

  /// No description provided for @chatOptionalNotesHint.
  ///
  /// In zh, this message translates to:
  /// **'可选备注...'**
  String get chatOptionalNotesHint;

  /// No description provided for @chatOrchestrationTraceStep.
  ///
  /// In zh, this message translates to:
  /// **'编排步骤'**
  String get chatOrchestrationTraceStep;

  /// No description provided for @chatOrchestrationTraceTitle.
  ///
  /// In zh, this message translates to:
  /// **'编排追踪'**
  String get chatOrchestrationTraceTitle;

  /// No description provided for @chatPendingMessagesFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatPendingMessagesFailed(Object arg0);

  /// No description provided for @chatPlanContextClear.
  ///
  /// In zh, this message translates to:
  /// **'清除上下文'**
  String get chatPlanContextClear;

  /// No description provided for @chatPlanContextSelect.
  ///
  /// In zh, this message translates to:
  /// **'选择计划上下文'**
  String get chatPlanContextSelect;

  /// No description provided for @chatPlanEmptySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'还没有计划，开始创建一个吧'**
  String get chatPlanEmptySubtitle;

  /// No description provided for @chatPlanEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'暂无计划'**
  String get chatPlanEmptyTitle;

  /// No description provided for @chatPlanReviewAcknowledged.
  ///
  /// In zh, this message translates to:
  /// **'已确认'**
  String get chatPlanReviewAcknowledged;

  /// No description provided for @chatPlanReviewApproved.
  ///
  /// In zh, this message translates to:
  /// **'已批准'**
  String get chatPlanReviewApproved;

  /// No description provided for @chatPlanReviewModifyRequested.
  ///
  /// In zh, this message translates to:
  /// **'请求修改'**
  String get chatPlanReviewModifyRequested;

  /// No description provided for @chatPlanReviewRejected.
  ///
  /// In zh, this message translates to:
  /// **'已拒绝'**
  String get chatPlanReviewRejected;

  /// No description provided for @chatPlanReviewStatusUpdate.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatPlanReviewStatusUpdate(Object arg0);

  /// No description provided for @chatPlanSelect.
  ///
  /// In zh, this message translates to:
  /// **'选择计划'**
  String get chatPlanSelect;

  /// No description provided for @chatQuotePrefix.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatQuotePrefix(Object arg0);

  /// No description provided for @chatReasoningProcess.
  ///
  /// In zh, this message translates to:
  /// **'推理过程'**
  String get chatReasoningProcess;

  /// No description provided for @chatReasoningStatusAnalyzing.
  ///
  /// In zh, this message translates to:
  /// **'正在分析...'**
  String get chatReasoningStatusAnalyzing;

  /// No description provided for @chatReasoningStatusAudioProcessing.
  ///
  /// In zh, this message translates to:
  /// **'正在处理音频...'**
  String get chatReasoningStatusAudioProcessing;

  /// No description provided for @chatReasoningStatusCalculating.
  ///
  /// In zh, this message translates to:
  /// **'正在计算...'**
  String get chatReasoningStatusCalculating;

  /// No description provided for @chatReasoningStatusCoding.
  ///
  /// In zh, this message translates to:
  /// **'正在编程...'**
  String get chatReasoningStatusCoding;

  /// No description provided for @chatReasoningStatusDataAnalyzing.
  ///
  /// In zh, this message translates to:
  /// **'正在分析数据...'**
  String get chatReasoningStatusDataAnalyzing;

  /// No description provided for @chatReasoningStatusDone.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get chatReasoningStatusDone;

  /// No description provided for @chatReasoningStatusImageProcessing.
  ///
  /// In zh, this message translates to:
  /// **'正在处理图像...'**
  String get chatReasoningStatusImageProcessing;

  /// No description provided for @chatReasoningStatusPlanning.
  ///
  /// In zh, this message translates to:
  /// **'正在规划...'**
  String get chatReasoningStatusPlanning;

  /// No description provided for @chatReasoningStatusPreparing.
  ///
  /// In zh, this message translates to:
  /// **'正在准备...'**
  String get chatReasoningStatusPreparing;

  /// No description provided for @chatReasoningStatusReasoning.
  ///
  /// In zh, this message translates to:
  /// **'正在推理...'**
  String get chatReasoningStatusReasoning;

  /// No description provided for @chatReasoningStatusRetrieving.
  ///
  /// In zh, this message translates to:
  /// **'正在检索...'**
  String get chatReasoningStatusRetrieving;

  /// No description provided for @chatReasoningStatusSearching.
  ///
  /// In zh, this message translates to:
  /// **'正在搜索...'**
  String get chatReasoningStatusSearching;

  /// No description provided for @chatReasoningStatusTranslating.
  ///
  /// In zh, this message translates to:
  /// **'正在翻译...'**
  String get chatReasoningStatusTranslating;

  /// No description provided for @chatReasoningStatusWriting.
  ///
  /// In zh, this message translates to:
  /// **'正在撰写...'**
  String get chatReasoningStatusWriting;

  /// No description provided for @chatReasoningStepsCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatReasoningStepsCount(Object arg0);

  /// No description provided for @chatReasoningSummary.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatReasoningSummary(Object arg0, Object arg1);

  /// No description provided for @chatReflectionDegraded.
  ///
  /// In zh, this message translates to:
  /// **'反思质量下降'**
  String get chatReflectionDegraded;

  /// No description provided for @chatReflectionFailed.
  ///
  /// In zh, this message translates to:
  /// **'反思失败'**
  String get chatReflectionFailed;

  /// No description provided for @chatReflectionFixed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatReflectionFixed(Object arg0, Object arg1);

  /// No description provided for @chatReflectionImproved.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatReflectionImproved(Object arg0, Object arg1);

  /// No description provided for @chatReflectionNoChange.
  ///
  /// In zh, this message translates to:
  /// **'无需变更'**
  String get chatReflectionNoChange;

  /// No description provided for @chatReflectionStatusUpdate.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatReflectionStatusUpdate(Object arg0);

  /// No description provided for @chatRoundsInfo.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatRoundsInfo(Object arg0);

  /// No description provided for @chatSourceUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知来源'**
  String get chatSourceUnknown;

  /// No description provided for @chatSourceUntitled.
  ///
  /// In zh, this message translates to:
  /// **'无标题'**
  String get chatSourceUntitled;

  /// No description provided for @chatSourcesAvailable.
  ///
  /// In zh, this message translates to:
  /// **'有可用来源'**
  String get chatSourcesAvailable;

  /// No description provided for @chatSourcesUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'无可用来源'**
  String get chatSourcesUnavailable;

  /// No description provided for @chatStreakSummary.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String chatStreakSummary(Object arg0, Object arg1);

  /// No description provided for @chatSubmitFeedback.
  ///
  /// In zh, this message translates to:
  /// **'提交反馈'**
  String get chatSubmitFeedback;

  /// No description provided for @chatSynthesisSuggestions.
  ///
  /// In zh, this message translates to:
  /// **'综合建议'**
  String get chatSynthesisSuggestions;

  /// No description provided for @chatTaskDataInvalid.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatTaskDataInvalid(Object arg0);

  /// No description provided for @chatTaskListMoreCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatTaskListMoreCount(Object arg0);

  /// No description provided for @chatTeamExpertsCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatTeamExpertsCount(Object arg0);

  /// No description provided for @chatUnknownWidgetType.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatUnknownWidgetType(Object arg0);

  /// No description provided for @chatUsingTool.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatUsingTool(Object arg0);

  /// No description provided for @chatViewComparisonData.
  ///
  /// In zh, this message translates to:
  /// **'查看对比数据'**
  String get chatViewComparisonData;

  /// No description provided for @chatViewPlanRationale.
  ///
  /// In zh, this message translates to:
  /// **'查看计划依据'**
  String get chatViewPlanRationale;

  /// No description provided for @chatVoiceNoMicPermission.
  ///
  /// In zh, this message translates to:
  /// **'没有麦克风权限'**
  String get chatVoiceNoMicPermission;

  /// No description provided for @chatVoiceStartFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatVoiceStartFailed(Object arg0);

  /// No description provided for @chatWhyThisAnswer.
  ///
  /// In zh, this message translates to:
  /// **'为什么是这个答案？'**
  String get chatWhyThisAnswer;

  /// No description provided for @chatWorkflowDebateProcessing.
  ///
  /// In zh, this message translates to:
  /// **'辩论处理中...'**
  String get chatWorkflowDebateProcessing;

  /// No description provided for @chatWorkflowDebateSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'多角度探讨'**
  String get chatWorkflowDebateSubtitle;

  /// No description provided for @chatWorkflowDebateTitle.
  ///
  /// In zh, this message translates to:
  /// **'辩论模式'**
  String get chatWorkflowDebateTitle;

  /// No description provided for @chatWorkflowDefault.
  ///
  /// In zh, this message translates to:
  /// **'默认工作流'**
  String get chatWorkflowDefault;

  /// No description provided for @chatWorkflowDelegationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'委派给专业助手'**
  String get chatWorkflowDelegationSubtitle;

  /// No description provided for @chatWorkflowDelegationTitle.
  ///
  /// In zh, this message translates to:
  /// **'委派模式'**
  String get chatWorkflowDelegationTitle;

  /// No description provided for @chatWorkflowErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'错误诊断'**
  String get chatWorkflowErrorDiagnosis;

  /// No description provided for @chatWorkflowExpertRouting.
  ///
  /// In zh, this message translates to:
  /// **'专家路由'**
  String get chatWorkflowExpertRouting;

  /// No description provided for @chatWorkflowExpertsCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatWorkflowExpertsCount(Object arg0);

  /// No description provided for @chatWorkflowParallelCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatWorkflowParallelCount(Object arg0);

  /// No description provided for @chatWorkflowParallelSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'并行处理多个任务'**
  String get chatWorkflowParallelSubtitle;

  /// No description provided for @chatWorkflowPhaseLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String chatWorkflowPhaseLabel(Object arg0);

  /// No description provided for @chatWorkflowProgressiveExploration.
  ///
  /// In zh, this message translates to:
  /// **'渐进式探索'**
  String get chatWorkflowProgressiveExploration;

  /// No description provided for @chatWorkflowStatusActive.
  ///
  /// In zh, this message translates to:
  /// **'活跃'**
  String get chatWorkflowStatusActive;

  /// No description provided for @chatWorkflowStatusDone.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get chatWorkflowStatusDone;

  /// No description provided for @chatWorkflowStatusError.
  ///
  /// In zh, this message translates to:
  /// **'错误'**
  String get chatWorkflowStatusError;

  /// No description provided for @chatWorkflowStatusWaiting.
  ///
  /// In zh, this message translates to:
  /// **'等待中'**
  String get chatWorkflowStatusWaiting;

  /// No description provided for @chatWorkflowTaskDecomposition.
  ///
  /// In zh, this message translates to:
  /// **'任务分解'**
  String get chatWorkflowTaskDecomposition;

  /// No description provided for @commonMinutesShort.
  ///
  /// In zh, this message translates to:
  /// **'分钟'**
  String get commonMinutesShort;

  /// No description provided for @commonUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知'**
  String get commonUnknown;

  /// No description provided for @communityAgentCollabOff.
  ///
  /// In zh, this message translates to:
  /// **'AI 协作已关闭'**
  String get communityAgentCollabOff;

  /// No description provided for @communityAgentCollabOn.
  ///
  /// In zh, this message translates to:
  /// **'AI 协作已开启'**
  String get communityAgentCollabOn;

  /// No description provided for @communityAgentName.
  ///
  /// In zh, this message translates to:
  /// **'星火AI'**
  String get communityAgentName;

  /// No description provided for @communityAgentOnlyYou.
  ///
  /// In zh, this message translates to:
  /// **'只有你在群里'**
  String get communityAgentOnlyYou;

  /// No description provided for @communityAgentProcessing.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在处理...'**
  String get communityAgentProcessing;

  /// No description provided for @communityAgentPromptHint.
  ///
  /// In zh, this message translates to:
  /// **'输入提示词...'**
  String get communityAgentPromptHint;

  /// No description provided for @communityAgentQuickConsensus.
  ///
  /// In zh, this message translates to:
  /// **'快速共识'**
  String get communityAgentQuickConsensus;

  /// No description provided for @communityAgentQuickConsensusPrompt.
  ///
  /// In zh, this message translates to:
  /// **'帮我快速总结群内共识'**
  String get communityAgentQuickConsensusPrompt;

  /// No description provided for @communityAgentQuickReminder.
  ///
  /// In zh, this message translates to:
  /// **'快速提醒'**
  String get communityAgentQuickReminder;

  /// No description provided for @communityAgentQuickReminderPrompt.
  ///
  /// In zh, this message translates to:
  /// **'帮我设置一个提醒'**
  String get communityAgentQuickReminderPrompt;

  /// No description provided for @communityAgentQuickSummary.
  ///
  /// In zh, this message translates to:
  /// **'快速总结'**
  String get communityAgentQuickSummary;

  /// No description provided for @communityAgentQuickSummaryPrompt.
  ///
  /// In zh, this message translates to:
  /// **'帮我总结最近的讨论'**
  String get communityAgentQuickSummaryPrompt;

  /// No description provided for @communityAgentThinking.
  ///
  /// In zh, this message translates to:
  /// **'AI 思考中...'**
  String get communityAgentThinking;

  /// No description provided for @communityChatEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无消息'**
  String get communityChatEmpty;

  /// No description provided for @communityChatTitle.
  ///
  /// In zh, this message translates to:
  /// **'社群聊天'**
  String get communityChatTitle;

  /// No description provided for @communityCheckInAction.
  ///
  /// In zh, this message translates to:
  /// **'打卡'**
  String get communityCheckInAction;

  /// No description provided for @communityCheckInDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'时长'**
  String get communityCheckInDurationLabel;

  /// No description provided for @communityCheckInFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String communityCheckInFailed(Object arg0);

  /// No description provided for @communityCheckInMessageHint.
  ///
  /// In zh, this message translates to:
  /// **'分享你的心得...'**
  String get communityCheckInMessageHint;

  /// No description provided for @communityCheckInMessageLabel.
  ///
  /// In zh, this message translates to:
  /// **'打卡内容'**
  String get communityCheckInMessageLabel;

  /// No description provided for @communityCheckInSuccess.
  ///
  /// In zh, this message translates to:
  /// **'打卡成功！'**
  String get communityCheckInSuccess;

  /// No description provided for @communityCheckInTitle.
  ///
  /// In zh, this message translates to:
  /// **'每日打卡'**
  String get communityCheckInTitle;

  /// No description provided for @communityFileSharedFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String communityFileSharedFailed(Object arg0);

  /// No description provided for @communityFileSharedSuccess.
  ///
  /// In zh, this message translates to:
  /// **'文件分享成功'**
  String get communityFileSharedSuccess;

  /// No description provided for @communityGroupFiles.
  ///
  /// In zh, this message translates to:
  /// **'群文件'**
  String get communityGroupFiles;

  /// No description provided for @communityGroupMembersCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String communityGroupMembersCount(Object arg0);

  /// No description provided for @communityMessageFallback.
  ///
  /// In zh, this message translates to:
  /// **'消息加载中...'**
  String get communityMessageFallback;

  /// No description provided for @communityMessageInputHint.
  ///
  /// In zh, this message translates to:
  /// **'输入消息...'**
  String get communityMessageInputHint;

  /// No description provided for @communitySearchGroupMessages.
  ///
  /// In zh, this message translates to:
  /// **'搜索群消息'**
  String get communitySearchGroupMessages;

  /// No description provided for @deleteAccountChecklistItem1.
  ///
  /// In zh, this message translates to:
  /// **'您的所有个人数据将被永久删除'**
  String get deleteAccountChecklistItem1;

  /// No description provided for @deleteAccountChecklistItem2.
  ///
  /// In zh, this message translates to:
  /// **'删除后将无法恢复账户'**
  String get deleteAccountChecklistItem2;

  /// No description provided for @deleteAccountChecklistItem3.
  ///
  /// In zh, this message translates to:
  /// **'您的所有有效订阅将自动取消'**
  String get deleteAccountChecklistItem3;

  /// No description provided for @deleteAccountChecklistTitle.
  ///
  /// In zh, this message translates to:
  /// **'请仔细阅读以下注意事项：'**
  String get deleteAccountChecklistTitle;

  /// No description provided for @deleteAccountConfirmButton.
  ///
  /// In zh, this message translates to:
  /// **'确认注销账户'**
  String get deleteAccountConfirmButton;

  /// No description provided for @deleteAccountConfirmInputHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入 \"DELETE\" 以确认'**
  String get deleteAccountConfirmInputHint;

  /// No description provided for @deleteAccountConfirmInputTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认注销'**
  String get deleteAccountConfirmInputTitle;

  /// No description provided for @deleteAccountNoSocialProvider.
  ///
  /// In zh, this message translates to:
  /// **'未找到关联的第三方账户'**
  String get deleteAccountNoSocialProvider;

  /// No description provided for @deleteAccountPasswordHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入您的密码'**
  String get deleteAccountPasswordHint;

  /// No description provided for @deleteAccountPasswordLabel.
  ///
  /// In zh, this message translates to:
  /// **'密码'**
  String get deleteAccountPasswordLabel;

  /// No description provided for @deleteAccountReauthButton.
  ///
  /// In zh, this message translates to:
  /// **'验证'**
  String get deleteAccountReauthButton;

  /// No description provided for @deleteAccountReauthDone.
  ///
  /// In zh, this message translates to:
  /// **'验证完成'**
  String get deleteAccountReauthDone;

  /// No description provided for @deleteAccountReauthSuccess.
  ///
  /// In zh, this message translates to:
  /// **'身份验证成功'**
  String get deleteAccountReauthSuccess;

  /// No description provided for @deleteAccountRequireDeleteInput.
  ///
  /// In zh, this message translates to:
  /// **'请输入 DELETE 以确认操作'**
  String get deleteAccountRequireDeleteInput;

  /// No description provided for @deleteAccountRequirePassword.
  ///
  /// In zh, this message translates to:
  /// **'请输入密码'**
  String get deleteAccountRequirePassword;

  /// No description provided for @deleteAccountRequireReauth.
  ///
  /// In zh, this message translates to:
  /// **'需要进行身份验证'**
  String get deleteAccountRequireReauth;

  /// No description provided for @deleteAccountSocialProvider.
  ///
  /// In zh, this message translates to:
  /// **'第三方账户'**
  String get deleteAccountSocialProvider;

  /// No description provided for @deleteAccountSocialReauthNotice.
  ///
  /// In zh, this message translates to:
  /// **'请使用 {arg0} 进行身份验证'**
  String deleteAccountSocialReauthNotice(Object arg0);

  /// No description provided for @deleteAccountSuccess.
  ///
  /// In zh, this message translates to:
  /// **'账户已成功注销'**
  String get deleteAccountSuccess;

  /// No description provided for @deleteAccountTitle.
  ///
  /// In zh, this message translates to:
  /// **'注销账户'**
  String get deleteAccountTitle;

  /// No description provided for @deleteAccountWeChatUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'微信暂不可用'**
  String get deleteAccountWeChatUnavailable;

  /// No description provided for @editProfileEmailUnverified.
  ///
  /// In zh, this message translates to:
  /// **'未验证'**
  String get editProfileEmailUnverified;

  /// No description provided for @editProfileEmailUnverifiedDesc.
  ///
  /// In zh, this message translates to:
  /// **'请验证您的邮箱地址以确保账号安全'**
  String get editProfileEmailUnverifiedDesc;

  /// No description provided for @editProfileEmailVerified.
  ///
  /// In zh, this message translates to:
  /// **'已验证'**
  String get editProfileEmailVerified;

  /// No description provided for @editProfileEmailVerifiedDesc.
  ///
  /// In zh, this message translates to:
  /// **'您的邮箱地址已通过验证'**
  String get editProfileEmailVerifiedDesc;

  /// No description provided for @editProfileEnterCode.
  ///
  /// In zh, this message translates to:
  /// **'输入验证码'**
  String get editProfileEnterCode;

  /// No description provided for @editProfileRegistrationMethod.
  ///
  /// In zh, this message translates to:
  /// **'注册方式'**
  String get editProfileRegistrationMethod;

  /// No description provided for @editProfileSendEmail.
  ///
  /// In zh, this message translates to:
  /// **'发送验证邮件'**
  String get editProfileSendEmail;

  /// No description provided for @editProfileSetPassword.
  ///
  /// In zh, this message translates to:
  /// **'设置密码'**
  String get editProfileSetPassword;

  /// No description provided for @editProfileSetPasswordHint.
  ///
  /// In zh, this message translates to:
  /// **'为您的账户设置一个安全密码'**
  String get editProfileSetPasswordHint;

  /// No description provided for @editProfileVerifyEmailConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认'**
  String get editProfileVerifyEmailConfirm;

  /// No description provided for @editProfileVerifyEmailHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入邮件中的验证码'**
  String get editProfileVerifyEmailHint;

  /// No description provided for @editProfileVerifyEmailTitle.
  ///
  /// In zh, this message translates to:
  /// **'验证邮箱'**
  String get editProfileVerifyEmailTitle;

  /// No description provided for @fileStatusFailed.
  ///
  /// In zh, this message translates to:
  /// **'上传失败'**
  String get fileStatusFailed;

  /// No description provided for @fileStatusProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get fileStatusProcessing;

  /// No description provided for @fileStatusReady.
  ///
  /// In zh, this message translates to:
  /// **'就绪'**
  String get fileStatusReady;

  /// No description provided for @fileStatusUploaded.
  ///
  /// In zh, this message translates to:
  /// **'已上传'**
  String get fileStatusUploaded;

  /// No description provided for @galaxyA11yActionStartLearning.
  ///
  /// In zh, this message translates to:
  /// **'开始学习'**
  String get galaxyA11yActionStartLearning;

  /// No description provided for @galaxyA11yActionUnlockNode.
  ///
  /// In zh, this message translates to:
  /// **'解锁节点'**
  String get galaxyA11yActionUnlockNode;

  /// No description provided for @galaxyA11yClusterLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1} {arg2}'**
  String galaxyA11yClusterLabel(Object arg0, Object arg1, Object arg2);

  /// No description provided for @galaxyA11yHintStartLearning.
  ///
  /// In zh, this message translates to:
  /// **'点击开始学习此知识点'**
  String get galaxyA11yHintStartLearning;

  /// No description provided for @galaxyA11yHintUnlockNode.
  ///
  /// In zh, this message translates to:
  /// **'点击解锁此节点'**
  String get galaxyA11yHintUnlockNode;

  /// No description provided for @galaxyA11yNavigateTo.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyA11yNavigateTo(Object arg0);

  /// No description provided for @galaxyA11yNavigationHint.
  ///
  /// In zh, this message translates to:
  /// **'使用手势导航知识星图'**
  String get galaxyA11yNavigationHint;

  /// No description provided for @galaxyA11yNodeImportance.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyA11yNodeImportance(Object arg0);

  /// No description provided for @galaxyA11yNodeLocked.
  ///
  /// In zh, this message translates to:
  /// **'节点已锁定'**
  String get galaxyA11yNodeLocked;

  /// No description provided for @galaxyA11yNodeMastery.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyA11yNodeMastery(Object arg0);

  /// No description provided for @galaxyA11yNodePrefix.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String galaxyA11yNodePrefix(Object arg0, Object arg1);

  /// No description provided for @galaxyA11yNodeStudyCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyA11yNodeStudyCount(Object arg0);

  /// No description provided for @galaxyA11yNodeUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'节点已解锁'**
  String get galaxyA11yNodeUnlocked;

  /// No description provided for @galaxyA11ySectorLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String galaxyA11ySectorLabel(Object arg0, Object arg1);

  /// No description provided for @galaxyA11yZoomLevel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyA11yZoomLevel(Object arg0);

  /// No description provided for @galaxyControlOverview.
  ///
  /// In zh, this message translates to:
  /// **'概览'**
  String get galaxyControlOverview;

  /// No description provided for @galaxyControlReplayStart.
  ///
  /// In zh, this message translates to:
  /// **'开始回放'**
  String get galaxyControlReplayStart;

  /// No description provided for @galaxyControlReplayStop.
  ///
  /// In zh, this message translates to:
  /// **'停止回放'**
  String get galaxyControlReplayStop;

  /// No description provided for @galaxyControlSearchClose.
  ///
  /// In zh, this message translates to:
  /// **'关闭搜索'**
  String get galaxyControlSearchClose;

  /// No description provided for @galaxyControlSearchOpen.
  ///
  /// In zh, this message translates to:
  /// **'打开搜索'**
  String get galaxyControlSearchOpen;

  /// No description provided for @galaxyControlSettings.
  ///
  /// In zh, this message translates to:
  /// **'设置'**
  String get galaxyControlSettings;

  /// No description provided for @galaxyControlZoomIn.
  ///
  /// In zh, this message translates to:
  /// **'放大'**
  String get galaxyControlZoomIn;

  /// No description provided for @galaxyControlZoomOut.
  ///
  /// In zh, this message translates to:
  /// **'缩小'**
  String get galaxyControlZoomOut;

  /// No description provided for @galaxyEmptyMessage.
  ///
  /// In zh, this message translates to:
  /// **'开始探索，点亮你的知识星图'**
  String get galaxyEmptyMessage;

  /// No description provided for @galaxyEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'星图空空如也'**
  String get galaxyEmptyTitle;

  /// No description provided for @galaxyErrorConnectionFailed.
  ///
  /// In zh, this message translates to:
  /// **'连接失败'**
  String get galaxyErrorConnectionFailed;

  /// No description provided for @galaxyErrorConnectionTimeout.
  ///
  /// In zh, this message translates to:
  /// **'连接超时'**
  String get galaxyErrorConnectionTimeout;

  /// No description provided for @galaxyErrorLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败'**
  String get galaxyErrorLoadFailed;

  /// No description provided for @galaxyErrorNetwork.
  ///
  /// In zh, this message translates to:
  /// **'网络错误'**
  String get galaxyErrorNetwork;

  /// No description provided for @galaxyErrorNetworkFailed.
  ///
  /// In zh, this message translates to:
  /// **'网络请求失败'**
  String get galaxyErrorNetworkFailed;

  /// No description provided for @galaxyErrorRequestFailed.
  ///
  /// In zh, this message translates to:
  /// **'请求失败'**
  String get galaxyErrorRequestFailed;

  /// No description provided for @galaxyErrorResponseTimeout.
  ///
  /// In zh, this message translates to:
  /// **'响应超时'**
  String get galaxyErrorResponseTimeout;

  /// No description provided for @galaxyErrorRetryHint.
  ///
  /// In zh, this message translates to:
  /// **'点击重试'**
  String get galaxyErrorRetryHint;

  /// No description provided for @galaxyErrorServiceTemporarilyUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'服务暂时不可用'**
  String get galaxyErrorServiceTemporarilyUnavailable;

  /// No description provided for @galaxyErrorServiceUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'服务不可用'**
  String get galaxyErrorServiceUnavailable;

  /// No description provided for @galaxyErrorUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知错误'**
  String get galaxyErrorUnknown;

  /// No description provided for @galaxyGraphRagGraph.
  ///
  /// In zh, this message translates to:
  /// **'图谱检索'**
  String get galaxyGraphRagGraph;

  /// No description provided for @galaxyGraphRagSearching.
  ///
  /// In zh, this message translates to:
  /// **'正在检索...'**
  String get galaxyGraphRagSearching;

  /// No description provided for @galaxyGraphRagTime.
  ///
  /// In zh, this message translates to:
  /// **'时间'**
  String get galaxyGraphRagTime;

  /// No description provided for @galaxyGraphRagVector.
  ///
  /// In zh, this message translates to:
  /// **'向量检索'**
  String get galaxyGraphRagVector;

  /// No description provided for @galaxyImportanceAdvanced.
  ///
  /// In zh, this message translates to:
  /// **'进阶'**
  String get galaxyImportanceAdvanced;

  /// No description provided for @galaxyImportanceBasic.
  ///
  /// In zh, this message translates to:
  /// **'基础'**
  String get galaxyImportanceBasic;

  /// No description provided for @galaxyImportanceCore.
  ///
  /// In zh, this message translates to:
  /// **'核心'**
  String get galaxyImportanceCore;

  /// No description provided for @galaxyImportanceEntry.
  ///
  /// In zh, this message translates to:
  /// **'入门'**
  String get galaxyImportanceEntry;

  /// No description provided for @galaxyImportanceIntermediate.
  ///
  /// In zh, this message translates to:
  /// **'中级'**
  String get galaxyImportanceIntermediate;

  /// No description provided for @galaxyImportanceNormal.
  ///
  /// In zh, this message translates to:
  /// **'普通'**
  String get galaxyImportanceNormal;

  /// No description provided for @galaxyLLMActionFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyLLMActionFailed(Object arg0);

  /// No description provided for @galaxyLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载失败'**
  String get galaxyLoadFailed;

  /// No description provided for @galaxyLoadFailedTitle.
  ///
  /// In zh, this message translates to:
  /// **'星图加载失败'**
  String get galaxyLoadFailedTitle;

  /// No description provided for @galaxyLoadingMessage.
  ///
  /// In zh, this message translates to:
  /// **'正在加载星图...'**
  String get galaxyLoadingMessage;

  /// No description provided for @galaxyLoadingTitle.
  ///
  /// In zh, this message translates to:
  /// **'加载中'**
  String get galaxyLoadingTitle;

  /// No description provided for @galaxyNodeFocus.
  ///
  /// In zh, this message translates to:
  /// **'聚焦节点'**
  String get galaxyNodeFocus;

  /// No description provided for @galaxyNodeInspectConnections.
  ///
  /// In zh, this message translates to:
  /// **'查看连接'**
  String get galaxyNodeInspectConnections;

  /// No description provided for @galaxyNodeLocked.
  ///
  /// In zh, this message translates to:
  /// **'已锁定'**
  String get galaxyNodeLocked;

  /// No description provided for @galaxyNodePreviewSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String galaxyNodePreviewSubtitle(Object arg0, Object arg1);

  /// No description provided for @galaxyNodeUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'已解锁'**
  String get galaxyNodeUnlocked;

  /// No description provided for @galaxyOfflineMode.
  ///
  /// In zh, this message translates to:
  /// **'离线模式'**
  String get galaxyOfflineMode;

  /// No description provided for @galaxyOverviewMastery.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get galaxyOverviewMastery;

  /// No description provided for @galaxyOverviewNodes.
  ///
  /// In zh, this message translates to:
  /// **'节点数'**
  String get galaxyOverviewNodes;

  /// No description provided for @galaxyOverviewUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'已解锁'**
  String get galaxyOverviewUnlocked;

  /// No description provided for @galaxyPerfHighJank.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyPerfHighJank(Object arg0);

  /// No description provided for @galaxyPerfLowFpsCritical.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyPerfLowFpsCritical(Object arg0);

  /// No description provided for @galaxyPerfLowFpsWarning.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyPerfLowFpsWarning(Object arg0);

  /// No description provided for @galaxyPerfRecommendationDisableParticles.
  ///
  /// In zh, this message translates to:
  /// **'禁用粒子效果'**
  String get galaxyPerfRecommendationDisableParticles;

  /// No description provided for @galaxyPerfRecommendationLowQualityMode.
  ///
  /// In zh, this message translates to:
  /// **'低质量模式'**
  String get galaxyPerfRecommendationLowQualityMode;

  /// No description provided for @galaxyPerfRecommendationOptimizeLayout.
  ///
  /// In zh, this message translates to:
  /// **'优化布局'**
  String get galaxyPerfRecommendationOptimizeLayout;

  /// No description provided for @galaxyPerfRecommendationReduceNodes.
  ///
  /// In zh, this message translates to:
  /// **'减少显示节点'**
  String get galaxyPerfRecommendationReduceNodes;

  /// No description provided for @galaxyPerfSlowRender.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String galaxyPerfSlowRender(Object arg0);

  /// No description provided for @galaxyPerfStatusCritical.
  ///
  /// In zh, this message translates to:
  /// **'性能严重不足'**
  String get galaxyPerfStatusCritical;

  /// No description provided for @galaxyPerfStatusDegraded.
  ///
  /// In zh, this message translates to:
  /// **'性能下降'**
  String get galaxyPerfStatusDegraded;

  /// No description provided for @galaxyPerfStatusOptimal.
  ///
  /// In zh, this message translates to:
  /// **'性能最佳'**
  String get galaxyPerfStatusOptimal;

  /// No description provided for @galaxyReload.
  ///
  /// In zh, this message translates to:
  /// **'重新加载'**
  String get galaxyReload;

  /// No description provided for @galaxySearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索知识节点...'**
  String get galaxySearchHint;

  /// No description provided for @galaxySearchHintDetail.
  ///
  /// In zh, this message translates to:
  /// **'输入关键词搜索'**
  String get galaxySearchHintDetail;

  /// No description provided for @galaxySearchNoResults.
  ///
  /// In zh, this message translates to:
  /// **'未找到相关节点'**
  String get galaxySearchNoResults;

  /// No description provided for @galaxySearchResultSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1} {arg2}'**
  String galaxySearchResultSubtitle(Object arg0, Object arg1, Object arg2);

  /// No description provided for @galaxySearchTitle.
  ///
  /// In zh, this message translates to:
  /// **'搜索星图'**
  String get galaxySearchTitle;

  /// No description provided for @galaxySectorArt.
  ///
  /// In zh, this message translates to:
  /// **'艺术'**
  String get galaxySectorArt;

  /// No description provided for @galaxySectorCivilization.
  ///
  /// In zh, this message translates to:
  /// **'文明'**
  String get galaxySectorCivilization;

  /// No description provided for @galaxySectorCosmos.
  ///
  /// In zh, this message translates to:
  /// **'宇宙'**
  String get galaxySectorCosmos;

  /// No description provided for @galaxySectorLife.
  ///
  /// In zh, this message translates to:
  /// **'生命'**
  String get galaxySectorLife;

  /// No description provided for @galaxySectorTech.
  ///
  /// In zh, this message translates to:
  /// **'科技'**
  String get galaxySectorTech;

  /// No description provided for @galaxySectorVoid.
  ///
  /// In zh, this message translates to:
  /// **'虚空'**
  String get galaxySectorVoid;

  /// No description provided for @galaxySectorWisdom.
  ///
  /// In zh, this message translates to:
  /// **'智慧'**
  String get galaxySectorWisdom;

  /// No description provided for @galaxySimulationCenterGravity.
  ///
  /// In zh, this message translates to:
  /// **'中心引力'**
  String get galaxySimulationCenterGravity;

  /// No description provided for @galaxySimulationGravity.
  ///
  /// In zh, this message translates to:
  /// **'引力'**
  String get galaxySimulationGravity;

  /// No description provided for @galaxySimulationReplaySpeed.
  ///
  /// In zh, this message translates to:
  /// **'回放速度'**
  String get galaxySimulationReplaySpeed;

  /// No description provided for @galaxySimulationRepulsion.
  ///
  /// In zh, this message translates to:
  /// **'斥力'**
  String get galaxySimulationRepulsion;

  /// No description provided for @galaxySimulationReset.
  ///
  /// In zh, this message translates to:
  /// **'重置'**
  String get galaxySimulationReset;

  /// No description provided for @galaxySimulationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'调整物理参数'**
  String get galaxySimulationSubtitle;

  /// No description provided for @galaxySimulationTitle.
  ///
  /// In zh, this message translates to:
  /// **'模拟设置'**
  String get galaxySimulationTitle;

  /// No description provided for @galaxyUsingCache.
  ///
  /// In zh, this message translates to:
  /// **'使用缓存数据'**
  String get galaxyUsingCache;

  /// No description provided for @guestUpgradeAcceptPoliciesRequired.
  ///
  /// In zh, this message translates to:
  /// **'请先阅读并同意用户协议与隐私政策'**
  String get guestUpgradeAcceptPoliciesRequired;

  /// No description provided for @guestUpgradeAgreePrivacy.
  ///
  /// In zh, this message translates to:
  /// **'我已阅读并同意《隐私政策》'**
  String get guestUpgradeAgreePrivacy;

  /// No description provided for @guestUpgradeAgreeTerms.
  ///
  /// In zh, this message translates to:
  /// **'我已阅读并同意《用户协议》'**
  String get guestUpgradeAgreeTerms;

  /// No description provided for @guestUpgradeIntro.
  ///
  /// In zh, this message translates to:
  /// **'升级您的游客账户，以确保数据安全并享受多设备同步等完整功能。'**
  String get guestUpgradeIntro;

  /// No description provided for @guestUpgradePasswordMinLength.
  ///
  /// In zh, this message translates to:
  /// **'密码至少需要8个字符'**
  String get guestUpgradePasswordMinLength;

  /// No description provided for @guestUpgradeSocialSectionTitle.
  ///
  /// In zh, this message translates to:
  /// **'或使用第三方账户升级'**
  String get guestUpgradeSocialSectionTitle;

  /// No description provided for @guestUpgradeSocialSuccess.
  ///
  /// In zh, this message translates to:
  /// **'账户升级成功'**
  String get guestUpgradeSocialSuccess;

  /// No description provided for @guestUpgradeSuccess.
  ///
  /// In zh, this message translates to:
  /// **'账户升级成功'**
  String get guestUpgradeSuccess;

  /// No description provided for @guestUpgradeTitle.
  ///
  /// In zh, this message translates to:
  /// **'升级账户'**
  String get guestUpgradeTitle;

  /// No description provided for @guestUpgradeUsernameMinLength.
  ///
  /// In zh, this message translates to:
  /// **'用户名至少需要3个字符'**
  String get guestUpgradeUsernameMinLength;

  /// No description provided for @guestUpgradeViewPrivacy.
  ///
  /// In zh, this message translates to:
  /// **'查看隐私政策'**
  String get guestUpgradeViewPrivacy;

  /// No description provided for @guestUpgradeViewTerms.
  ///
  /// In zh, this message translates to:
  /// **'查看用户协议'**
  String get guestUpgradeViewTerms;

  /// No description provided for @guestUpgradeWithApple.
  ///
  /// In zh, this message translates to:
  /// **'使用 Apple 升级'**
  String get guestUpgradeWithApple;

  /// No description provided for @guestUpgradeWithEmail.
  ///
  /// In zh, this message translates to:
  /// **'使用邮箱升级'**
  String get guestUpgradeWithEmail;

  /// No description provided for @guestUpgradeWithGoogle.
  ///
  /// In zh, this message translates to:
  /// **'使用 Google 升级'**
  String get guestUpgradeWithGoogle;

  /// No description provided for @guestUpgradeWithWeChat.
  ///
  /// In zh, this message translates to:
  /// **'使用微信升级'**
  String get guestUpgradeWithWeChat;

  /// No description provided for @passwordSetConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认设置密码'**
  String get passwordSetConfirm;

  /// No description provided for @passwordSetHint.
  ///
  /// In zh, this message translates to:
  /// **'请输入至少8位密码'**
  String get passwordSetHint;

  /// No description provided for @passwordSetLabel.
  ///
  /// In zh, this message translates to:
  /// **'设置密码'**
  String get passwordSetLabel;

  /// No description provided for @passwordSetSuccess.
  ///
  /// In zh, this message translates to:
  /// **'密码设置成功'**
  String get passwordSetSuccess;

  /// No description provided for @passwordSetTitle.
  ///
  /// In zh, this message translates to:
  /// **'设置密码'**
  String get passwordSetTitle;

  /// No description provided for @planArchive.
  ///
  /// In zh, this message translates to:
  /// **'归档计划'**
  String get planArchive;

  /// No description provided for @planArchiveConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认归档'**
  String get planArchiveConfirm;

  /// No description provided for @planArchiveMessage.
  ///
  /// In zh, this message translates to:
  /// **'归档后计划将移至历史记录，确定要归档吗？'**
  String get planArchiveMessage;

  /// No description provided for @planArchiveTitle.
  ///
  /// In zh, this message translates to:
  /// **'归档计划'**
  String get planArchiveTitle;

  /// No description provided for @planArchivedSuccess.
  ///
  /// In zh, this message translates to:
  /// **'计划已归档'**
  String get planArchivedSuccess;

  /// No description provided for @planContextTitle.
  ///
  /// In zh, this message translates to:
  /// **'计划上下文'**
  String get planContextTitle;

  /// No description provided for @planDaysRemaining.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planDaysRemaining(Object arg0);

  /// No description provided for @planDetailTitle.
  ///
  /// In zh, this message translates to:
  /// **'计划详情'**
  String get planDetailTitle;

  /// No description provided for @planDueToday.
  ///
  /// In zh, this message translates to:
  /// **'今日到期'**
  String get planDueToday;

  /// No description provided for @planFactsFeedbackSummary.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String planFactsFeedbackSummary(Object arg0, Object arg1);

  /// No description provided for @planKeyFacts.
  ///
  /// In zh, this message translates to:
  /// **'关键事实'**
  String get planKeyFacts;

  /// No description provided for @planLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planLoadFailed(Object arg0);

  /// No description provided for @planNoContent.
  ///
  /// In zh, this message translates to:
  /// **'暂无内容'**
  String get planNoContent;

  /// No description provided for @planNoTasks.
  ///
  /// In zh, this message translates to:
  /// **'暂无任务'**
  String get planNoTasks;

  /// No description provided for @planNoVisualizationData.
  ///
  /// In zh, this message translates to:
  /// **'暂无可视化数据'**
  String get planNoVisualizationData;

  /// No description provided for @planOverdueDays.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planOverdueDays(Object arg0);

  /// No description provided for @planProgressLabel.
  ///
  /// In zh, this message translates to:
  /// **'计划进度'**
  String get planProgressLabel;

  /// No description provided for @planRecentFeedback.
  ///
  /// In zh, this message translates to:
  /// **'最近反馈'**
  String get planRecentFeedback;

  /// No description provided for @planRelatedTasks.
  ///
  /// In zh, this message translates to:
  /// **'相关任务'**
  String get planRelatedTasks;

  /// No description provided for @planRestore.
  ///
  /// In zh, this message translates to:
  /// **'恢复计划'**
  String get planRestore;

  /// No description provided for @planRestoredSuccess.
  ///
  /// In zh, this message translates to:
  /// **'计划已恢复'**
  String get planRestoredSuccess;

  /// No description provided for @planReviewAdditionalNotesHint.
  ///
  /// In zh, this message translates to:
  /// **'添加备注（可选）...'**
  String get planReviewAdditionalNotesHint;

  /// No description provided for @planReviewAdditionalNotesRequired.
  ///
  /// In zh, this message translates to:
  /// **'请填写备注'**
  String get planReviewAdditionalNotesRequired;

  /// No description provided for @planReviewApproveExecute.
  ///
  /// In zh, this message translates to:
  /// **'批准并执行'**
  String get planReviewApproveExecute;

  /// No description provided for @planReviewConfidenceTierLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planReviewConfidenceTierLabel(Object arg0);

  /// No description provided for @planReviewConfidenceTitle.
  ///
  /// In zh, this message translates to:
  /// **'置信度评估'**
  String get planReviewConfidenceTitle;

  /// No description provided for @planReviewDecisionApproved.
  ///
  /// In zh, this message translates to:
  /// **'已批准'**
  String get planReviewDecisionApproved;

  /// No description provided for @planReviewDecisionNeedsModification.
  ///
  /// In zh, this message translates to:
  /// **'需要修改'**
  String get planReviewDecisionNeedsModification;

  /// No description provided for @planReviewDecisionRejected.
  ///
  /// In zh, this message translates to:
  /// **'已拒绝'**
  String get planReviewDecisionRejected;

  /// No description provided for @planReviewDecisionRequiresConfirmation.
  ///
  /// In zh, this message translates to:
  /// **'需要确认'**
  String get planReviewDecisionRequiresConfirmation;

  /// No description provided for @planReviewEvidenceLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planReviewEvidenceLabel(Object arg0);

  /// No description provided for @planReviewImpactLabel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planReviewImpactLabel(Object arg0);

  /// No description provided for @planReviewModifyPlan.
  ///
  /// In zh, this message translates to:
  /// **'修改计划'**
  String get planReviewModifyPlan;

  /// No description provided for @planReviewReasonDifficultyTooHigh.
  ///
  /// In zh, this message translates to:
  /// **'难度过高'**
  String get planReviewReasonDifficultyTooHigh;

  /// No description provided for @planReviewReasonDifficultyTooLow.
  ///
  /// In zh, this message translates to:
  /// **'难度过低'**
  String get planReviewReasonDifficultyTooLow;

  /// No description provided for @planReviewReasonMissingKeyTask.
  ///
  /// In zh, this message translates to:
  /// **'缺少关键任务'**
  String get planReviewReasonMissingKeyTask;

  /// No description provided for @planReviewReasonOther.
  ///
  /// In zh, this message translates to:
  /// **'其他原因'**
  String get planReviewReasonOther;

  /// No description provided for @planReviewReasonScheduleUnreasonable.
  ///
  /// In zh, this message translates to:
  /// **'时间安排不合理'**
  String get planReviewReasonScheduleUnreasonable;

  /// No description provided for @planReviewReasonTasksTooFew.
  ///
  /// In zh, this message translates to:
  /// **'任务太少'**
  String get planReviewReasonTasksTooFew;

  /// No description provided for @planReviewReasonTasksTooMany.
  ///
  /// In zh, this message translates to:
  /// **'任务太多'**
  String get planReviewReasonTasksTooMany;

  /// No description provided for @planReviewRejectReasonTitle.
  ///
  /// In zh, this message translates to:
  /// **'拒绝原因'**
  String get planReviewRejectReasonTitle;

  /// No description provided for @planReviewRejectWithFeedback.
  ///
  /// In zh, this message translates to:
  /// **'拒绝并反馈'**
  String get planReviewRejectWithFeedback;

  /// No description provided for @planReviewSelectReasonRequired.
  ///
  /// In zh, this message translates to:
  /// **'请选择原因'**
  String get planReviewSelectReasonRequired;

  /// No description provided for @planReviewSubmitFeedback.
  ///
  /// In zh, this message translates to:
  /// **'提交反馈'**
  String get planReviewSubmitFeedback;

  /// No description provided for @planReviewSummaryApproved.
  ///
  /// In zh, this message translates to:
  /// **'计划已批准'**
  String get planReviewSummaryApproved;

  /// No description provided for @planReviewSummaryNeedsModification.
  ///
  /// In zh, this message translates to:
  /// **'计划需要修改'**
  String get planReviewSummaryNeedsModification;

  /// No description provided for @planReviewSummaryRejected.
  ///
  /// In zh, this message translates to:
  /// **'计划已拒绝'**
  String get planReviewSummaryRejected;

  /// No description provided for @planReviewSummaryRequiresConfirmation.
  ///
  /// In zh, this message translates to:
  /// **'计划需要确认'**
  String get planReviewSummaryRequiresConfirmation;

  /// No description provided for @planSectionCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get planSectionCompletionRate;

  /// No description provided for @planSectionDailyCompletion.
  ///
  /// In zh, this message translates to:
  /// **'每日完成情况'**
  String get planSectionDailyCompletion;

  /// No description provided for @planSectionTaskTypeDistribution.
  ///
  /// In zh, this message translates to:
  /// **'任务类型分布'**
  String get planSectionTaskTypeDistribution;

  /// No description provided for @planShare.
  ///
  /// In zh, this message translates to:
  /// **'分享计划'**
  String get planShare;

  /// No description provided for @planStatusActive.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get planStatusActive;

  /// No description provided for @planStatusArchived.
  ///
  /// In zh, this message translates to:
  /// **'已归档'**
  String get planStatusArchived;

  /// No description provided for @planStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get planStatusCompleted;

  /// No description provided for @planStatusPaused.
  ///
  /// In zh, this message translates to:
  /// **'已暂停'**
  String get planStatusPaused;

  /// No description provided for @planStatusUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知状态'**
  String get planStatusUnknown;

  /// No description provided for @planTabOverview.
  ///
  /// In zh, this message translates to:
  /// **'概览'**
  String get planTabOverview;

  /// No description provided for @planTabProgress.
  ///
  /// In zh, this message translates to:
  /// **'进度'**
  String get planTabProgress;

  /// No description provided for @planTargetDate.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planTargetDate(Object arg0);

  /// No description provided for @planTargetMastery.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String planTargetMastery(Object arg0);

  /// No description provided for @planTaskProgress.
  ///
  /// In zh, this message translates to:
  /// **'任务进度'**
  String get planTaskProgress;

  /// No description provided for @planUpcomingTasks.
  ///
  /// In zh, this message translates to:
  /// **'即将到来的任务'**
  String get planUpcomingTasks;

  /// No description provided for @pomodoroBreakFinished.
  ///
  /// In zh, this message translates to:
  /// **'休息结束！'**
  String get pomodoroBreakFinished;

  /// No description provided for @pomodoroWorkFinished.
  ///
  /// In zh, this message translates to:
  /// **'工作完成！'**
  String get pomodoroWorkFinished;

  /// No description provided for @account.
  ///
  /// In zh, this message translates to:
  /// **'账户'**
  String get account;

  /// No description provided for @accountSecurity.
  ///
  /// In zh, this message translates to:
  /// **'账户与安全'**
  String get accountSecurity;

  /// No description provided for @accountSecurityIntro.
  ///
  /// In zh, this message translates to:
  /// **'管理您的关联账户、登录设备和安全日志'**
  String get accountSecurityIntro;

  /// No description provided for @personalGrowth.
  ///
  /// In zh, this message translates to:
  /// **'个人成长'**
  String get personalGrowth;

  /// No description provided for @profileDeleteAccount.
  ///
  /// In zh, this message translates to:
  /// **'注销账户'**
  String get profileDeleteAccount;

  /// No description provided for @profileLinkedAccounts.
  ///
  /// In zh, this message translates to:
  /// **'关联账户'**
  String get profileLinkedAccounts;

  /// No description provided for @profilePersonalInfo.
  ///
  /// In zh, this message translates to:
  /// **'个人信息'**
  String get profilePersonalInfo;

  /// No description provided for @profileSecurityLog.
  ///
  /// In zh, this message translates to:
  /// **'安全日志'**
  String get profileSecurityLog;

  /// No description provided for @profileSessionManagement.
  ///
  /// In zh, this message translates to:
  /// **'设备管理'**
  String get profileSessionManagement;

  /// No description provided for @profileUpgradeGuest.
  ///
  /// In zh, this message translates to:
  /// **'升级账户'**
  String get profileUpgradeGuest;

  /// No description provided for @regenCustomHint.
  ///
  /// In zh, this message translates to:
  /// **'描述你想要的修改...'**
  String get regenCustomHint;

  /// No description provided for @regenDescCompleted.
  ///
  /// In zh, this message translates to:
  /// **'重新生成完成'**
  String get regenDescCompleted;

  /// No description provided for @regenDescFailed.
  ///
  /// In zh, this message translates to:
  /// **'重新生成失败'**
  String get regenDescFailed;

  /// No description provided for @regenDescInProgress.
  ///
  /// In zh, this message translates to:
  /// **'正在重新生成...'**
  String get regenDescInProgress;

  /// No description provided for @regenDescPending.
  ///
  /// In zh, this message translates to:
  /// **'等待重新生成'**
  String get regenDescPending;

  /// No description provided for @regenHintAddExamples.
  ///
  /// In zh, this message translates to:
  /// **'添加更多示例'**
  String get regenHintAddExamples;

  /// No description provided for @regenHintFixErrors.
  ///
  /// In zh, this message translates to:
  /// **'修正错误'**
  String get regenHintFixErrors;

  /// No description provided for @regenHintFriendlierTone.
  ///
  /// In zh, this message translates to:
  /// **'更友好的语气'**
  String get regenHintFriendlierTone;

  /// No description provided for @regenHintMoreAccurate.
  ///
  /// In zh, this message translates to:
  /// **'更准确'**
  String get regenHintMoreAccurate;

  /// No description provided for @regenHintMoreConcise.
  ///
  /// In zh, this message translates to:
  /// **'更简洁'**
  String get regenHintMoreConcise;

  /// No description provided for @regenHintMoreDetailed.
  ///
  /// In zh, this message translates to:
  /// **'更详细'**
  String get regenHintMoreDetailed;

  /// No description provided for @regenHintsOptional.
  ///
  /// In zh, this message translates to:
  /// **'可选提示'**
  String get regenHintsOptional;

  /// No description provided for @regenImprovementsTitle.
  ///
  /// In zh, this message translates to:
  /// **'改进建议'**
  String get regenImprovementsTitle;

  /// No description provided for @regenProgressTitle.
  ///
  /// In zh, this message translates to:
  /// **'重新生成进度'**
  String get regenProgressTitle;

  /// No description provided for @regenQualityImprovement.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String regenQualityImprovement(Object arg0);

  /// No description provided for @regenResultFailed.
  ///
  /// In zh, this message translates to:
  /// **'生成失败'**
  String get regenResultFailed;

  /// No description provided for @regenResultSuccess.
  ///
  /// In zh, this message translates to:
  /// **'生成成功'**
  String get regenResultSuccess;

  /// No description provided for @regenRetryMessage.
  ///
  /// In zh, this message translates to:
  /// **'点击重试'**
  String get regenRetryMessage;

  /// No description provided for @regenSelectType.
  ///
  /// In zh, this message translates to:
  /// **'选择类型'**
  String get regenSelectType;

  /// No description provided for @regenStart.
  ///
  /// In zh, this message translates to:
  /// **'开始重新生成'**
  String get regenStart;

  /// No description provided for @regenTitleCompleted.
  ///
  /// In zh, this message translates to:
  /// **'重新生成完成'**
  String get regenTitleCompleted;

  /// No description provided for @regenTitleFailed.
  ///
  /// In zh, this message translates to:
  /// **'重新生成失败'**
  String get regenTitleFailed;

  /// No description provided for @regenTitleIdle.
  ///
  /// In zh, this message translates to:
  /// **'等待操作'**
  String get regenTitleIdle;

  /// No description provided for @regenTitleInProgress.
  ///
  /// In zh, this message translates to:
  /// **'正在生成...'**
  String get regenTitleInProgress;

  /// No description provided for @regenTitlePending.
  ///
  /// In zh, this message translates to:
  /// **'等待中'**
  String get regenTitlePending;

  /// No description provided for @regenTypeAddDetails.
  ///
  /// In zh, this message translates to:
  /// **'添加细节'**
  String get regenTypeAddDetails;

  /// No description provided for @regenTypeChangeStyle.
  ///
  /// In zh, this message translates to:
  /// **'改变风格'**
  String get regenTypeChangeStyle;

  /// No description provided for @regenTypeCustom.
  ///
  /// In zh, this message translates to:
  /// **'自定义'**
  String get regenTypeCustom;

  /// No description provided for @regenTypeFixIssues.
  ///
  /// In zh, this message translates to:
  /// **'修复问题'**
  String get regenTypeFixIssues;

  /// No description provided for @regenTypeImproveQuality.
  ///
  /// In zh, this message translates to:
  /// **'提高质量'**
  String get regenTypeImproveQuality;

  /// No description provided for @regenTypeSimplify.
  ///
  /// In zh, this message translates to:
  /// **'简化'**
  String get regenTypeSimplify;

  /// No description provided for @reviewRatingAccuracyTitle.
  ///
  /// In zh, this message translates to:
  /// **'准确性评价'**
  String get reviewRatingAccuracyTitle;

  /// No description provided for @reviewRatingAccurate.
  ///
  /// In zh, this message translates to:
  /// **'准确'**
  String get reviewRatingAccurate;

  /// No description provided for @reviewRatingAddInaccuratePoint.
  ///
  /// In zh, this message translates to:
  /// **'添加不准确点'**
  String get reviewRatingAddInaccuratePoint;

  /// No description provided for @reviewRatingCommentsHint.
  ///
  /// In zh, this message translates to:
  /// **'输入您的评价...'**
  String get reviewRatingCommentsHint;

  /// No description provided for @reviewRatingCommentsTitle.
  ///
  /// In zh, this message translates to:
  /// **'评价内容'**
  String get reviewRatingCommentsTitle;

  /// No description provided for @reviewRatingHelpful.
  ///
  /// In zh, this message translates to:
  /// **'有帮助'**
  String get reviewRatingHelpful;

  /// No description provided for @reviewRatingInaccurate.
  ///
  /// In zh, this message translates to:
  /// **'不准确'**
  String get reviewRatingInaccurate;

  /// No description provided for @reviewRatingInaccuratePointHint.
  ///
  /// In zh, this message translates to:
  /// **'描述不准确的地方...'**
  String get reviewRatingInaccuratePointHint;

  /// No description provided for @reviewRatingInaccuratePointsTitle.
  ///
  /// In zh, this message translates to:
  /// **'不准确之处'**
  String get reviewRatingInaccuratePointsTitle;

  /// No description provided for @reviewRatingLessOptions.
  ///
  /// In zh, this message translates to:
  /// **'收起选项'**
  String get reviewRatingLessOptions;

  /// No description provided for @reviewRatingMoreOptions.
  ///
  /// In zh, this message translates to:
  /// **'更多选项'**
  String get reviewRatingMoreOptions;

  /// No description provided for @reviewRatingNotHelpful.
  ///
  /// In zh, this message translates to:
  /// **'没帮助'**
  String get reviewRatingNotHelpful;

  /// No description provided for @reviewRatingSpecificityTitle.
  ///
  /// In zh, this message translates to:
  /// **'具体性评价'**
  String get reviewRatingSpecificityTitle;

  /// No description provided for @reviewRatingSubmit.
  ///
  /// In zh, this message translates to:
  /// **'提交评价'**
  String get reviewRatingSubmit;

  /// No description provided for @reviewRatingSubmitFailed.
  ///
  /// In zh, this message translates to:
  /// **'提交失败'**
  String get reviewRatingSubmitFailed;

  /// No description provided for @reviewRatingSubmitSuccess.
  ///
  /// In zh, this message translates to:
  /// **'评价提交成功'**
  String get reviewRatingSubmitSuccess;

  /// No description provided for @reviewRatingSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'您的反馈将帮助我们改进'**
  String get reviewRatingSubtitle;

  /// No description provided for @reviewRatingTagsTitle.
  ///
  /// In zh, this message translates to:
  /// **'选择标签'**
  String get reviewRatingTagsTitle;

  /// No description provided for @reviewRatingTitle.
  ///
  /// In zh, this message translates to:
  /// **'评价回复'**
  String get reviewRatingTitle;

  /// No description provided for @reviewSpecificityAppropriate.
  ///
  /// In zh, this message translates to:
  /// **'恰当'**
  String get reviewSpecificityAppropriate;

  /// No description provided for @reviewSpecificityTooDetailed.
  ///
  /// In zh, this message translates to:
  /// **'太详细'**
  String get reviewSpecificityTooDetailed;

  /// No description provided for @reviewSpecificityTooVague.
  ///
  /// In zh, this message translates to:
  /// **'太模糊'**
  String get reviewSpecificityTooVague;

  /// No description provided for @reviewTagAccurate.
  ///
  /// In zh, this message translates to:
  /// **'准确'**
  String get reviewTagAccurate;

  /// No description provided for @reviewTagClear.
  ///
  /// In zh, this message translates to:
  /// **'清晰'**
  String get reviewTagClear;

  /// No description provided for @reviewTagNeedsImprovement.
  ///
  /// In zh, this message translates to:
  /// **'需要改进'**
  String get reviewTagNeedsImprovement;

  /// No description provided for @reviewTagPractical.
  ///
  /// In zh, this message translates to:
  /// **'实用'**
  String get reviewTagPractical;

  /// No description provided for @reviewTagTooLenient.
  ///
  /// In zh, this message translates to:
  /// **'太宽松'**
  String get reviewTagTooLenient;

  /// No description provided for @reviewTagTooStrict.
  ///
  /// In zh, this message translates to:
  /// **'太严格'**
  String get reviewTagTooStrict;

  /// No description provided for @securityLogActionAccountDelete.
  ///
  /// In zh, this message translates to:
  /// **'注销账户'**
  String get securityLogActionAccountDelete;

  /// No description provided for @securityLogActionEmailVerify.
  ///
  /// In zh, this message translates to:
  /// **'验证邮箱'**
  String get securityLogActionEmailVerify;

  /// No description provided for @securityLogActionGuestUpgrade.
  ///
  /// In zh, this message translates to:
  /// **'游客升级'**
  String get securityLogActionGuestUpgrade;

  /// No description provided for @securityLogActionLoginFailed.
  ///
  /// In zh, this message translates to:
  /// **'登录失败'**
  String get securityLogActionLoginFailed;

  /// No description provided for @securityLogActionLoginSuccess.
  ///
  /// In zh, this message translates to:
  /// **'登录成功'**
  String get securityLogActionLoginSuccess;

  /// No description provided for @securityLogActionLogout.
  ///
  /// In zh, this message translates to:
  /// **'登出'**
  String get securityLogActionLogout;

  /// No description provided for @securityLogActionPasswordChange.
  ///
  /// In zh, this message translates to:
  /// **'修改密码'**
  String get securityLogActionPasswordChange;

  /// No description provided for @securityLogActionPasswordReset.
  ///
  /// In zh, this message translates to:
  /// **'重置密码'**
  String get securityLogActionPasswordReset;

  /// No description provided for @securityLogActionRegister.
  ///
  /// In zh, this message translates to:
  /// **'注册'**
  String get securityLogActionRegister;

  /// No description provided for @securityLogActionSocialLink.
  ///
  /// In zh, this message translates to:
  /// **'绑定第三方账户'**
  String get securityLogActionSocialLink;

  /// No description provided for @securityLogActionSocialUnlink.
  ///
  /// In zh, this message translates to:
  /// **'解绑第三方账户'**
  String get securityLogActionSocialUnlink;

  /// No description provided for @securityLogActionTokenRefresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新令牌'**
  String get securityLogActionTokenRefresh;

  /// No description provided for @securityLogAdditionalInfo.
  ///
  /// In zh, this message translates to:
  /// **'详细信息: {arg0}'**
  String securityLogAdditionalInfo(Object arg0);

  /// No description provided for @securityLogEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无安全日志记录'**
  String get securityLogEmpty;

  /// No description provided for @securityLogIntro.
  ///
  /// In zh, this message translates to:
  /// **'最近的账户安全相关活动记录'**
  String get securityLogIntro;

  /// No description provided for @securityLogOccurredAt.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String securityLogOccurredAt(Object arg0);

  /// No description provided for @securityLogTitle.
  ///
  /// In zh, this message translates to:
  /// **'安全日志'**
  String get securityLogTitle;

  /// No description provided for @sessionManagementCurrent.
  ///
  /// In zh, this message translates to:
  /// **'当前设备'**
  String get sessionManagementCurrent;

  /// No description provided for @sessionManagementEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无活动设备'**
  String get sessionManagementEmpty;

  /// No description provided for @sessionManagementFirstLogin.
  ///
  /// In zh, this message translates to:
  /// **'首次登录: {arg0}'**
  String sessionManagementFirstLogin(Object arg0);

  /// No description provided for @sessionManagementIntro.
  ///
  /// In zh, this message translates to:
  /// **'管理您已登录的设备与会话。若发现异常活动，请及时注销相关设备。'**
  String get sessionManagementIntro;

  /// No description provided for @sessionManagementLastActive.
  ///
  /// In zh, this message translates to:
  /// **'最后活跃: {arg0}'**
  String sessionManagementLastActive(Object arg0);

  /// No description provided for @sessionManagementRevokeOthers.
  ///
  /// In zh, this message translates to:
  /// **'注销其他设备'**
  String get sessionManagementRevokeOthers;

  /// No description provided for @sessionManagementRevokeThis.
  ///
  /// In zh, this message translates to:
  /// **'注销'**
  String get sessionManagementRevokeThis;

  /// No description provided for @sessionManagementTitle.
  ///
  /// In zh, this message translates to:
  /// **'设备管理'**
  String get sessionManagementTitle;

  /// No description provided for @sessionManagementUnknownDevice.
  ///
  /// In zh, this message translates to:
  /// **'未知设备'**
  String get sessionManagementUnknownDevice;

  /// No description provided for @socialAccountsIntro.
  ///
  /// In zh, this message translates to:
  /// **'关联第三方账户以便快速登录'**
  String get socialAccountsIntro;

  /// No description provided for @socialAccountsLink.
  ///
  /// In zh, this message translates to:
  /// **'绑定'**
  String get socialAccountsLink;

  /// No description provided for @socialAccountsLinked.
  ///
  /// In zh, this message translates to:
  /// **'已绑定'**
  String get socialAccountsLinked;

  /// No description provided for @socialAccountsTitle.
  ///
  /// In zh, this message translates to:
  /// **'关联账户'**
  String get socialAccountsTitle;

  /// No description provided for @socialAccountsUnlink.
  ///
  /// In zh, this message translates to:
  /// **'解绑'**
  String get socialAccountsUnlink;

  /// No description provided for @socialAccountsUnlinkConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认解绑'**
  String get socialAccountsUnlinkConfirm;

  /// No description provided for @socialAccountsUnlinkMessage.
  ///
  /// In zh, this message translates to:
  /// **'解绑后您将无法使用该账号登录'**
  String get socialAccountsUnlinkMessage;

  /// No description provided for @socialAccountsUnlinkTitle.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String socialAccountsUnlinkTitle(Object arg0);

  /// No description provided for @socialAccountsUnlinkedHint.
  ///
  /// In zh, this message translates to:
  /// **'未绑定'**
  String get socialAccountsUnlinkedHint;

  /// No description provided for @socialAccountsWeChatPending.
  ///
  /// In zh, this message translates to:
  /// **'微信绑定处理中'**
  String get socialAccountsWeChatPending;

  /// No description provided for @socialAccountsWeChatUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'微信暂不可用'**
  String get socialAccountsWeChatUnavailable;

  /// No description provided for @sprintActionAbandonButton.
  ///
  /// In zh, this message translates to:
  /// **'放弃冲刺'**
  String get sprintActionAbandonButton;

  /// No description provided for @sprintActionAbandonSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'放弃当前冲刺'**
  String get sprintActionAbandonSubtitle;

  /// No description provided for @sprintActionAbandonTitle.
  ///
  /// In zh, this message translates to:
  /// **'放弃冲刺'**
  String get sprintActionAbandonTitle;

  /// No description provided for @sprintActionCompleteButton.
  ///
  /// In zh, this message translates to:
  /// **'完成冲刺'**
  String get sprintActionCompleteButton;

  /// No description provided for @sprintActionCompleteSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'标记冲刺为完成'**
  String get sprintActionCompleteSubtitle;

  /// No description provided for @sprintActionCompleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'完成冲刺'**
  String get sprintActionCompleteTitle;

  /// No description provided for @sprintActionExtendSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'延长冲刺时间'**
  String get sprintActionExtendSubtitle;

  /// No description provided for @sprintActionExtendTitle.
  ///
  /// In zh, this message translates to:
  /// **'延长冲刺'**
  String get sprintActionExtendTitle;

  /// No description provided for @sprintActionsTitle.
  ///
  /// In zh, this message translates to:
  /// **'冲刺操作'**
  String get sprintActionsTitle;

  /// No description provided for @sprintCompletedTasks.
  ///
  /// In zh, this message translates to:
  /// **'已完成任务'**
  String get sprintCompletedTasks;

  /// No description provided for @sprintCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get sprintCompletionRate;

  /// No description provided for @sprintConfirmAbandonDesc.
  ///
  /// In zh, this message translates to:
  /// **'确定要放弃这个冲刺吗？未完成的任务将保留。'**
  String get sprintConfirmAbandonDesc;

  /// No description provided for @sprintConfirmAbandonMessage.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintConfirmAbandonMessage(Object arg0);

  /// No description provided for @sprintConfirmAbandonTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认放弃'**
  String get sprintConfirmAbandonTitle;

  /// No description provided for @sprintConfirmCompleteDesc.
  ///
  /// In zh, this message translates to:
  /// **'恭喜完成冲刺！确定要标记为完成吗？'**
  String get sprintConfirmCompleteDesc;

  /// No description provided for @sprintConfirmCompleteMessage.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintConfirmCompleteMessage(Object arg0);

  /// No description provided for @sprintConfirmCompleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认完成'**
  String get sprintConfirmCompleteTitle;

  /// No description provided for @sprintDailyCompletion.
  ///
  /// In zh, this message translates to:
  /// **'每日完成情况'**
  String get sprintDailyCompletion;

  /// No description provided for @sprintDurationDaysLabel.
  ///
  /// In zh, this message translates to:
  /// **'持续天数'**
  String get sprintDurationDaysLabel;

  /// No description provided for @sprintDurationDaysValue.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintDurationDaysValue(Object arg0);

  /// No description provided for @sprintDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'持续时间'**
  String get sprintDurationLabel;

  /// No description provided for @sprintEndDateLabel.
  ///
  /// In zh, this message translates to:
  /// **'结束日期'**
  String get sprintEndDateLabel;

  /// No description provided for @sprintExtendConfirm.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintExtendConfirm(Object arg0);

  /// No description provided for @sprintExtendMessage.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintExtendMessage(Object arg0);

  /// No description provided for @sprintExtendOptionDays.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintExtendOptionDays(Object arg0);

  /// No description provided for @sprintExtendSelectDays.
  ///
  /// In zh, this message translates to:
  /// **'选择延长天数'**
  String get sprintExtendSelectDays;

  /// No description provided for @sprintExtendTitle.
  ///
  /// In zh, this message translates to:
  /// **'延长冲刺'**
  String get sprintExtendTitle;

  /// No description provided for @sprintIncompleteTasks.
  ///
  /// In zh, this message translates to:
  /// **'未完成任务'**
  String get sprintIncompleteTasks;

  /// No description provided for @sprintInfoTitle.
  ///
  /// In zh, this message translates to:
  /// **'冲刺信息'**
  String get sprintInfoTitle;

  /// No description provided for @sprintOngoing.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get sprintOngoing;

  /// No description provided for @sprintProgressTitle.
  ///
  /// In zh, this message translates to:
  /// **'冲刺进度'**
  String get sprintProgressTitle;

  /// No description provided for @sprintRemainingTasks.
  ///
  /// In zh, this message translates to:
  /// **'剩余任务'**
  String get sprintRemainingTasks;

  /// No description provided for @sprintStartDateLabel.
  ///
  /// In zh, this message translates to:
  /// **'开始日期'**
  String get sprintStartDateLabel;

  /// No description provided for @sprintStatsEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无统计数据'**
  String get sprintStatsEmpty;

  /// No description provided for @sprintStatsTitle.
  ///
  /// In zh, this message translates to:
  /// **'冲刺统计'**
  String get sprintStatsTitle;

  /// No description provided for @sprintStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get sprintStatusCompleted;

  /// No description provided for @sprintStatusInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get sprintStatusInProgress;

  /// No description provided for @sprintStatusLabel.
  ///
  /// In zh, this message translates to:
  /// **'冲刺状态'**
  String get sprintStatusLabel;

  /// No description provided for @sprintStatusTodo.
  ///
  /// In zh, this message translates to:
  /// **'待开始'**
  String get sprintStatusTodo;

  /// No description provided for @sprintTaskCount.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String sprintTaskCount(Object arg0);

  /// No description provided for @sprintTaskSummaryTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务摘要'**
  String get sprintTaskSummaryTitle;

  /// No description provided for @sprintTotalTasks.
  ///
  /// In zh, this message translates to:
  /// **'总任务数'**
  String get sprintTotalTasks;

  /// No description provided for @statusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get statusCompleted;

  /// No description provided for @statusFailed.
  ///
  /// In zh, this message translates to:
  /// **'失败'**
  String get statusFailed;

  /// No description provided for @statusInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get statusInProgress;

  /// No description provided for @statusPending.
  ///
  /// In zh, this message translates to:
  /// **'待处理'**
  String get statusPending;

  /// No description provided for @taskBatchCreateTitle.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskBatchCreateTitle(Object arg0);

  /// No description provided for @taskChatAssistantTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务助手'**
  String get taskChatAssistantTitle;

  /// No description provided for @taskChatEmptyPrompt.
  ///
  /// In zh, this message translates to:
  /// **'有什么可以帮你的？'**
  String get taskChatEmptyPrompt;

  /// No description provided for @taskChatInputHint.
  ///
  /// In zh, this message translates to:
  /// **'输入消息...'**
  String get taskChatInputHint;

  /// No description provided for @taskCreateAction.
  ///
  /// In zh, this message translates to:
  /// **'创建任务'**
  String get taskCreateAction;

  /// No description provided for @taskCreateFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskCreateFailed(Object arg0);

  /// No description provided for @taskCreateSuccess.
  ///
  /// In zh, this message translates to:
  /// **'任务创建成功'**
  String get taskCreateSuccess;

  /// No description provided for @taskCreateTitle.
  ///
  /// In zh, this message translates to:
  /// **'创建任务'**
  String get taskCreateTitle;

  /// No description provided for @taskCreatedWithSuggestions.
  ///
  /// In zh, this message translates to:
  /// **'已根据建议创建任务'**
  String get taskCreatedWithSuggestions;

  /// No description provided for @taskCreating.
  ///
  /// In zh, this message translates to:
  /// **'正在创建任务...'**
  String get taskCreating;

  /// No description provided for @taskDeadline.
  ///
  /// In zh, this message translates to:
  /// **'截止时间'**
  String get taskDeadline;

  /// No description provided for @taskDeadlineLabel.
  ///
  /// In zh, this message translates to:
  /// **'截止时间'**
  String get taskDeadlineLabel;

  /// No description provided for @taskDeleteConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定要删除这个任务吗？'**
  String get taskDeleteConfirm;

  /// No description provided for @taskDeleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'删除任务'**
  String get taskDeleteTitle;

  /// No description provided for @taskDetailLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskDetailLoadFailed(Object arg0);

  /// No description provided for @taskDetailLoading.
  ///
  /// In zh, this message translates to:
  /// **'加载任务详情...'**
  String get taskDetailLoading;

  /// No description provided for @taskDifficulty.
  ///
  /// In zh, this message translates to:
  /// **'难度'**
  String get taskDifficulty;

  /// No description provided for @taskDifficultyLabel.
  ///
  /// In zh, this message translates to:
  /// **'难度'**
  String get taskDifficultyLabel;

  /// No description provided for @taskDifficultyLevel.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskDifficultyLevel(Object arg0);

  /// No description provided for @taskEnergyCost.
  ///
  /// In zh, this message translates to:
  /// **'精力消耗'**
  String get taskEnergyCost;

  /// No description provided for @taskEnergyCostLabel.
  ///
  /// In zh, this message translates to:
  /// **'精力消耗'**
  String get taskEnergyCostLabel;

  /// No description provided for @taskEnergyCostValue.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskEnergyCostValue(Object arg0);

  /// No description provided for @taskEstimatedDuration.
  ///
  /// In zh, this message translates to:
  /// **'预计时长'**
  String get taskEstimatedDuration;

  /// No description provided for @taskEstimatedDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'预计时长'**
  String get taskEstimatedDurationLabel;

  /// No description provided for @taskExecutionAbandon.
  ///
  /// In zh, this message translates to:
  /// **'放弃执行'**
  String get taskExecutionAbandon;

  /// No description provided for @taskExecutionCompleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'完成任务'**
  String get taskExecutionCompleteTitle;

  /// No description provided for @taskExecutionCompletedTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务已完成'**
  String get taskExecutionCompletedTitle;

  /// No description provided for @taskExecutionConfirmComplete.
  ///
  /// In zh, this message translates to:
  /// **'确认完成'**
  String get taskExecutionConfirmComplete;

  /// No description provided for @taskExecutionElapsedMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskExecutionElapsedMinutes(Object arg0);

  /// No description provided for @taskExecutionEnterFocus.
  ///
  /// In zh, this message translates to:
  /// **'进入专注模式'**
  String get taskExecutionEnterFocus;

  /// No description provided for @taskExecutionExpGained.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskExecutionExpGained(Object arg0);

  /// No description provided for @taskExecutionFeatureCoach.
  ///
  /// In zh, this message translates to:
  /// **'专注教练'**
  String get taskExecutionFeatureCoach;

  /// No description provided for @taskExecutionFeatureDistraction.
  ///
  /// In zh, this message translates to:
  /// **'分心检测'**
  String get taskExecutionFeatureDistraction;

  /// No description provided for @taskExecutionFeatureFlipClock.
  ///
  /// In zh, this message translates to:
  /// **'翻页时钟'**
  String get taskExecutionFeatureFlipClock;

  /// No description provided for @taskExecutionFeatureFullscreen.
  ///
  /// In zh, this message translates to:
  /// **'全屏模式'**
  String get taskExecutionFeatureFullscreen;

  /// No description provided for @taskExecutionFeatureReward.
  ///
  /// In zh, this message translates to:
  /// **'完成奖励'**
  String get taskExecutionFeatureReward;

  /// No description provided for @taskExecutionFeatureStarfield.
  ///
  /// In zh, this message translates to:
  /// **'星空背景'**
  String get taskExecutionFeatureStarfield;

  /// No description provided for @taskExecutionGuideEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无执行指南'**
  String get taskExecutionGuideEmpty;

  /// No description provided for @taskExecutionGuideTitle.
  ///
  /// In zh, this message translates to:
  /// **'执行指南'**
  String get taskExecutionGuideTitle;

  /// No description provided for @taskExecutionNoTask.
  ///
  /// In zh, this message translates to:
  /// **'当前没有执行中的任务'**
  String get taskExecutionNoTask;

  /// No description provided for @taskExecutionNoteHint.
  ///
  /// In zh, this message translates to:
  /// **'添加执行笔记...'**
  String get taskExecutionNoteHint;

  /// No description provided for @taskExecutionNoteLabel.
  ///
  /// In zh, this message translates to:
  /// **'执行笔记'**
  String get taskExecutionNoteLabel;

  /// No description provided for @taskExecutionSkipAnimation.
  ///
  /// In zh, this message translates to:
  /// **'跳过动画'**
  String get taskExecutionSkipAnimation;

  /// No description provided for @taskExecutionStartFailed.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskExecutionStartFailed(Object arg0);

  /// No description provided for @taskExecutionStartNow.
  ///
  /// In zh, this message translates to:
  /// **'立即开始'**
  String get taskExecutionStartNow;

  /// No description provided for @taskExecutionSyncFailed.
  ///
  /// In zh, this message translates to:
  /// **'同步失败'**
  String get taskExecutionSyncFailed;

  /// No description provided for @taskExecutionTapToContinue.
  ///
  /// In zh, this message translates to:
  /// **'点击继续'**
  String get taskExecutionTapToContinue;

  /// No description provided for @taskExecutionTimerLabel.
  ///
  /// In zh, this message translates to:
  /// **'计时器'**
  String get taskExecutionTimerLabel;

  /// No description provided for @taskExitCancelStep1.
  ///
  /// In zh, this message translates to:
  /// **'取消退出'**
  String get taskExitCancelStep1;

  /// No description provided for @taskExitCancelStep2.
  ///
  /// In zh, this message translates to:
  /// **'继续取消'**
  String get taskExitCancelStep2;

  /// No description provided for @taskExitCancelStep3.
  ///
  /// In zh, this message translates to:
  /// **'保留任务'**
  String get taskExitCancelStep3;

  /// No description provided for @taskExitConfirmStep1.
  ///
  /// In zh, this message translates to:
  /// **'确认退出'**
  String get taskExitConfirmStep1;

  /// No description provided for @taskExitConfirmStep2.
  ///
  /// In zh, this message translates to:
  /// **'再次确认'**
  String get taskExitConfirmStep2;

  /// No description provided for @taskExitConfirmStep3.
  ///
  /// In zh, this message translates to:
  /// **'放弃任务'**
  String get taskExitConfirmStep3;

  /// No description provided for @taskExitMessageStep1.
  ///
  /// In zh, this message translates to:
  /// **'确定要退出吗？进度将丢失。'**
  String get taskExitMessageStep1;

  /// No description provided for @taskExitMessageStep2.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1}'**
  String taskExitMessageStep2(Object arg0, Object arg1);

  /// No description provided for @taskExitMessageStep3.
  ///
  /// In zh, this message translates to:
  /// **'任务已放弃，下次继续加油！'**
  String get taskExitMessageStep3;

  /// No description provided for @taskExitTitleStep1.
  ///
  /// In zh, this message translates to:
  /// **'退出任务'**
  String get taskExitTitleStep1;

  /// No description provided for @taskExitTitleStep2.
  ///
  /// In zh, this message translates to:
  /// **'再次确认'**
  String get taskExitTitleStep2;

  /// No description provided for @taskExitTitleStep3.
  ///
  /// In zh, this message translates to:
  /// **'已放弃'**
  String get taskExitTitleStep3;

  /// No description provided for @taskGenerateGuideSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在生成执行指南...'**
  String get taskGenerateGuideSubtitle;

  /// No description provided for @taskGenerateGuideTitle.
  ///
  /// In zh, this message translates to:
  /// **'生成执行指南'**
  String get taskGenerateGuideTitle;

  /// No description provided for @taskGuideEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无指南'**
  String get taskGuideEmpty;

  /// No description provided for @taskGuideTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务指南'**
  String get taskGuideTitle;

  /// No description provided for @taskListLoading.
  ///
  /// In zh, this message translates to:
  /// **'加载任务列表...'**
  String get taskListLoading;

  /// No description provided for @taskListTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务列表'**
  String get taskListTitle;

  /// No description provided for @taskMinutesOption.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskMinutesOption(Object arg0);

  /// No description provided for @taskNudgeApplied.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskNudgeApplied(Object arg0);

  /// No description provided for @taskNudgeApply.
  ///
  /// In zh, this message translates to:
  /// **'应用建议'**
  String get taskNudgeApply;

  /// No description provided for @taskNudgeConfidence.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskNudgeConfidence(Object arg0);

  /// No description provided for @taskNudgeDismiss.
  ///
  /// In zh, this message translates to:
  /// **'忽略'**
  String get taskNudgeDismiss;

  /// No description provided for @taskNudgeTitle.
  ///
  /// In zh, this message translates to:
  /// **'任务建议'**
  String get taskNudgeTitle;

  /// No description provided for @taskReminderEnableSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'开启任务提醒功能'**
  String get taskReminderEnableSubtitle;

  /// No description provided for @taskReminderEnableTitle.
  ///
  /// In zh, this message translates to:
  /// **'开启提醒'**
  String get taskReminderEnableTitle;

  /// No description provided for @taskReminderInfoBody.
  ///
  /// In zh, this message translates to:
  /// **'任务提醒会在截止时间前通知您'**
  String get taskReminderInfoBody;

  /// No description provided for @taskReminderInfoTitle.
  ///
  /// In zh, this message translates to:
  /// **'提醒说明'**
  String get taskReminderInfoTitle;

  /// No description provided for @taskReminderPermissionDenied.
  ///
  /// In zh, this message translates to:
  /// **'没有通知权限'**
  String get taskReminderPermissionDenied;

  /// No description provided for @taskReminderRefreshAll.
  ///
  /// In zh, this message translates to:
  /// **'刷新所有提醒'**
  String get taskReminderRefreshAll;

  /// No description provided for @taskReminderRefreshSuccess.
  ///
  /// In zh, this message translates to:
  /// **'提醒已刷新'**
  String get taskReminderRefreshSuccess;

  /// No description provided for @taskReminderSettingsTitle.
  ///
  /// In zh, this message translates to:
  /// **'提醒设置'**
  String get taskReminderSettingsTitle;

  /// No description provided for @taskReminderTimesTitle.
  ///
  /// In zh, this message translates to:
  /// **'提醒时间'**
  String get taskReminderTimesTitle;

  /// No description provided for @taskSearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索任务...'**
  String get taskSearchHint;

  /// No description provided for @taskStart.
  ///
  /// In zh, this message translates to:
  /// **'开始任务'**
  String get taskStart;

  /// No description provided for @taskSuggestedKnowledge.
  ///
  /// In zh, this message translates to:
  /// **'推荐知识'**
  String get taskSuggestedKnowledge;

  /// No description provided for @taskTagsHint.
  ///
  /// In zh, this message translates to:
  /// **'添加标签...'**
  String get taskTagsHint;

  /// No description provided for @taskTagsLabel.
  ///
  /// In zh, this message translates to:
  /// **'标签'**
  String get taskTagsLabel;

  /// No description provided for @taskTimerMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{arg0}'**
  String taskTimerMinutes(Object arg0);

  /// No description provided for @taskTimerPomodoro.
  ///
  /// In zh, this message translates to:
  /// **'番茄钟'**
  String get taskTimerPomodoro;

  /// No description provided for @taskTitleHint.
  ///
  /// In zh, this message translates to:
  /// **'输入任务标题...'**
  String get taskTitleHint;

  /// No description provided for @taskTitleLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务标题'**
  String get taskTitleLabel;

  /// No description provided for @taskTitleRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入任务标题'**
  String get taskTitleRequired;

  /// No description provided for @taskTypeLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务类型'**
  String get taskTypeLabel;

  /// No description provided for @taskTypeOcr.
  ///
  /// In zh, this message translates to:
  /// **'OCR识别'**
  String get taskTypeOcr;

  /// No description provided for @taskUntitled.
  ///
  /// In zh, this message translates to:
  /// **'未命名任务'**
  String get taskUntitled;

  /// No description provided for @taskViewAll.
  ///
  /// In zh, this message translates to:
  /// **'查看全部'**
  String get taskViewAll;

  /// No description provided for @weeklyAgendaCollapsedHint.
  ///
  /// In zh, this message translates to:
  /// **'展开查看完整周日程'**
  String get weeklyAgendaCollapsedHint;

  /// No description provided for @weeklyAgendaEmptyHint.
  ///
  /// In zh, this message translates to:
  /// **'本周暂无日程安排'**
  String get weeklyAgendaEmptyHint;

  /// No description provided for @weeklyAgendaSummary.
  ///
  /// In zh, this message translates to:
  /// **'{arg0} {arg1} {arg2}'**
  String weeklyAgendaSummary(Object arg0, Object arg1, Object arg2);

  /// No description provided for @securityLogDevice.
  ///
  /// In zh, this message translates to:
  /// **'设备: {arg0}'**
  String securityLogDevice(Object arg0);

  /// No description provided for @sessionManagementCurrentHint.
  ///
  /// In zh, this message translates to:
  /// **'这是您当前正在使用的设备'**
  String get sessionManagementCurrentHint;

  /// No description provided for @personaAdjustInferredPreference.
  ///
  /// In zh, this message translates to:
  /// **'调整推断偏好'**
  String get personaAdjustInferredPreference;

  /// No description provided for @personaNewValue.
  ///
  /// In zh, this message translates to:
  /// **'新值'**
  String get personaNewValue;

  /// No description provided for @personaAdjustInferredPreferenceTitle.
  ///
  /// In zh, this message translates to:
  /// **'调整推断偏好'**
  String get personaAdjustInferredPreferenceTitle;
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
