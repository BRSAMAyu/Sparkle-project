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
  /// **'标准模式'**
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
  /// **'专家直连'**
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
  /// **'问我任何关于学习的问题'**
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
