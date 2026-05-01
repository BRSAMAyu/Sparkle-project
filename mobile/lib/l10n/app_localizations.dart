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

  /// No description provided for @refresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新'**
  String get refresh;

  /// No description provided for @chatAiSystemSettings.
  ///
  /// In zh, this message translates to:
  /// **'AI 系统设置'**
  String get chatAiSystemSettings;

  /// No description provided for @sensoryFeedbackSectionTitle.
  ///
  /// In zh, this message translates to:
  /// **'感官反馈'**
  String get sensoryFeedbackSectionTitle;

  /// No description provided for @sensoryFeedbackSectionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'统一控制操作音效、成就反馈和触觉回馈'**
  String get sensoryFeedbackSectionSubtitle;

  /// No description provided for @sensoryFeedbackLoadingSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'正在读取感官反馈偏好...'**
  String get sensoryFeedbackLoadingSubtitle;

  /// No description provided for @sensorySoundTitle.
  ///
  /// In zh, this message translates to:
  /// **'音效反馈'**
  String get sensorySoundTitle;

  /// No description provided for @sensorySoundSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'关闭后，所有 Sensory 音效与环境音将静默'**
  String get sensorySoundSubtitle;

  /// No description provided for @sensoryHapticTitle.
  ///
  /// In zh, this message translates to:
  /// **'触控反馈'**
  String get sensoryHapticTitle;

  /// No description provided for @sensoryHapticSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'关闭后，成就、星图等所有触感反馈都会停止'**
  String get sensoryHapticSubtitle;

  /// No description provided for @sensoryAmbientSceneTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注环境音'**
  String get sensoryAmbientSceneTitle;

  /// No description provided for @sensoryAmbientVolumeTitle.
  ///
  /// In zh, this message translates to:
  /// **'环境音音量'**
  String get sensoryAmbientVolumeTitle;

  /// No description provided for @bgmSectionTitle.
  ///
  /// In zh, this message translates to:
  /// **'背景音乐'**
  String get bgmSectionTitle;

  /// No description provided for @bgmSectionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'按页面自动切换氛围，也支持你偏向钢琴、空灵或温暖风格'**
  String get bgmSectionSubtitle;

  /// No description provided for @bgmLoadingSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'正在读取音乐偏好...'**
  String get bgmLoadingSubtitle;

  /// No description provided for @bgmEnabledTitle.
  ///
  /// In zh, this message translates to:
  /// **'启用背景音乐'**
  String get bgmEnabledTitle;

  /// No description provided for @bgmEnabledSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'进入不同页面时自动切换对应的 BGM'**
  String get bgmEnabledSubtitle;

  /// No description provided for @bgmPlaybackStrategyTitle.
  ///
  /// In zh, this message translates to:
  /// **'播放策略'**
  String get bgmPlaybackStrategyTitle;

  /// No description provided for @themeAiSectionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'主题、对话选项、AI 档位与动效强度'**
  String get themeAiSectionSubtitle;

  /// No description provided for @aiReasoningTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 档位'**
  String get aiReasoningTitle;

  /// No description provided for @aiReasoningSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'敏捷更快，均衡推荐，深思更强分析'**
  String get aiReasoningSubtitle;

  /// No description provided for @aiReasoningFastLabel.
  ///
  /// In zh, this message translates to:
  /// **'敏捷'**
  String get aiReasoningFastLabel;

  /// No description provided for @aiReasoningBalancedLabel.
  ///
  /// In zh, this message translates to:
  /// **'均衡'**
  String get aiReasoningBalancedLabel;

  /// No description provided for @aiReasoningDeepLabel.
  ///
  /// In zh, this message translates to:
  /// **'深思'**
  String get aiReasoningDeepLabel;

  /// No description provided for @showChatContextToggleTitle.
  ///
  /// In zh, this message translates to:
  /// **'显示聊天顶部选择条'**
  String get showChatContextToggleTitle;

  /// No description provided for @showChatContextToggleSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制聊天页里可展开的计划/档位选择组件'**
  String get showChatContextToggleSubtitle;

  /// No description provided for @showChatPredictionDockTitle.
  ///
  /// In zh, this message translates to:
  /// **'显示聊天预测组件'**
  String get showChatPredictionDockTitle;

  /// No description provided for @showChatPredictionDockSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制输入框上方的用户行为预测与快捷建议'**
  String get showChatPredictionDockSubtitle;

  /// No description provided for @showChatTransparencyCapsuleTitle.
  ///
  /// In zh, this message translates to:
  /// **'显示 AI 透明胶囊'**
  String get showChatTransparencyCapsuleTitle;

  /// No description provided for @showChatTransparencyCapsuleSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制聊天页底部的 AI 系统完成情况与透明化浮层'**
  String get showChatTransparencyCapsuleSubtitle;

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

  /// No description provided for @planCreateTitle.
  ///
  /// In zh, this message translates to:
  /// **'创建计划'**
  String get planCreateTitle;

  /// No description provided for @planCreateSuccess.
  ///
  /// In zh, this message translates to:
  /// **'计划创建成功'**
  String get planCreateSuccess;

  /// No description provided for @planCreateFailed.
  ///
  /// In zh, this message translates to:
  /// **'创建计划失败: {error}'**
  String planCreateFailed(Object error);

  /// No description provided for @planNameLabel.
  ///
  /// In zh, this message translates to:
  /// **'计划名称'**
  String get planNameLabel;

  /// No description provided for @planNameHint.
  ///
  /// In zh, this message translates to:
  /// **'输入计划名称...'**
  String get planNameHint;

  /// No description provided for @planNameRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入计划名称'**
  String get planNameRequired;

  /// No description provided for @planDescLabel.
  ///
  /// In zh, this message translates to:
  /// **'计划描述'**
  String get planDescLabel;

  /// No description provided for @planDescHint.
  ///
  /// In zh, this message translates to:
  /// **'描述你的计划目标...'**
  String get planDescHint;

  /// No description provided for @planSubjectLabel.
  ///
  /// In zh, this message translates to:
  /// **'主题/学科'**
  String get planSubjectLabel;

  /// No description provided for @planSubjectHint.
  ///
  /// In zh, this message translates to:
  /// **'如：计算机科学、英语...'**
  String get planSubjectHint;

  /// No description provided for @planTargetDateLabel.
  ///
  /// In zh, this message translates to:
  /// **'目标日期'**
  String get planTargetDateLabel;

  /// No description provided for @planTargetDateUnset.
  ///
  /// In zh, this message translates to:
  /// **'未设置目标日期'**
  String get planTargetDateUnset;

  /// No description provided for @planDailyMinutesLabel.
  ///
  /// In zh, this message translates to:
  /// **'每日可用时间'**
  String get planDailyMinutesLabel;

  /// No description provided for @planDailyMinutesHint.
  ///
  /// In zh, this message translates to:
  /// **'每天计划投入多少分钟'**
  String get planDailyMinutesHint;

  /// No description provided for @planPriorityLabel.
  ///
  /// In zh, this message translates to:
  /// **'优先级'**
  String get planPriorityLabel;

  /// No description provided for @planPriorityCritical.
  ///
  /// In zh, this message translates to:
  /// **'紧急'**
  String get planPriorityCritical;

  /// No description provided for @planPriorityHigh.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get planPriorityHigh;

  /// No description provided for @planPriorityNormal.
  ///
  /// In zh, this message translates to:
  /// **'普通'**
  String get planPriorityNormal;

  /// No description provided for @planPriorityLow.
  ///
  /// In zh, this message translates to:
  /// **'低'**
  String get planPriorityLow;

  /// No description provided for @planCreating.
  ///
  /// In zh, this message translates to:
  /// **'创建中...'**
  String get planCreating;

  /// No description provided for @planCreateAction.
  ///
  /// In zh, this message translates to:
  /// **'创建计划'**
  String get planCreateAction;

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
  /// **'加载失败: {error}'**
  String loadingFailed(Object error);

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

  /// No description provided for @chatCharacters.
  ///
  /// In zh, this message translates to:
  /// **'字'**
  String get chatCharacters;

  /// No description provided for @chatWords.
  ///
  /// In zh, this message translates to:
  /// **'词'**
  String get chatWords;

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
  String achievementEventStartsAt(Object time);

  /// No description provided for @achievementEventEndsAt.
  ///
  /// In zh, this message translates to:
  /// **'结束于{time}'**
  String achievementEventEndsAt(Object time);

  /// No description provided for @achievementEventEndsIn.
  ///
  /// In zh, this message translates to:
  /// **'将于{time}结束'**
  String achievementEventEndsIn(Object time);

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
  String contractProgressLabel(Object current, Object target);

  /// No description provided for @contractDailyTarget.
  ///
  /// In zh, this message translates to:
  /// **'每日目标'**
  String get contractDailyTarget;

  /// No description provided for @contractMinutesTarget.
  ///
  /// In zh, this message translates to:
  /// **'{current}/{target}分钟'**
  String contractMinutesTarget(Object current, Object target);

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
  String contractDaysRemaining(Object days);

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
  String streakCalendarRange(Object days);

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

  /// No description provided for @taskStatusStuck.
  ///
  /// In zh, this message translates to:
  /// **'卡住了'**
  String get taskStatusStuck;

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

  /// No description provided for @taskPriorityHighShort.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get taskPriorityHighShort;

  /// No description provided for @taskPriorityMediumShort.
  ///
  /// In zh, this message translates to:
  /// **'中'**
  String get taskPriorityMediumShort;

  /// No description provided for @taskPriorityLowShort.
  ///
  /// In zh, this message translates to:
  /// **'低'**
  String get taskPriorityLowShort;

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

  /// No description provided for @taskListEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'今天还没有待办事项'**
  String get taskListEmptyTitle;

  /// No description provided for @taskListEmptyDescription.
  ///
  /// In zh, this message translates to:
  /// **'先放进一件最想推进的小事，系统会帮你把今天逐步铺开。'**
  String get taskListEmptyDescription;

  /// No description provided for @taskListEmptyAction.
  ///
  /// In zh, this message translates to:
  /// **'创建第一项任务'**
  String get taskListEmptyAction;

  /// No description provided for @taskListReorderDisabledHint.
  ///
  /// In zh, this message translates to:
  /// **'拖拽排序仅在「全部任务」列表中可用。'**
  String get taskListReorderDisabledHint;

  /// No description provided for @taskListPartialErrorHint.
  ///
  /// In zh, this message translates to:
  /// **'部分数据刷新失败，当前先显示已加载的任务。'**
  String get taskListPartialErrorHint;

  /// No description provided for @taskListFilterTooltip.
  ///
  /// In zh, this message translates to:
  /// **'优先级筛选'**
  String get taskListFilterTooltip;

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

  /// No description provided for @statisticsAggregationNone.
  ///
  /// In zh, this message translates to:
  /// **'原始数据'**
  String get statisticsAggregationNone;

  /// No description provided for @statisticsAggregationHourly.
  ///
  /// In zh, this message translates to:
  /// **'按小时'**
  String get statisticsAggregationHourly;

  /// No description provided for @statisticsAggregationDaily.
  ///
  /// In zh, this message translates to:
  /// **'按天'**
  String get statisticsAggregationDaily;

  /// No description provided for @statisticsAggregationWeekly.
  ///
  /// In zh, this message translates to:
  /// **'按周'**
  String get statisticsAggregationWeekly;

  /// No description provided for @statisticsAggregationMonthly.
  ///
  /// In zh, this message translates to:
  /// **'按月'**
  String get statisticsAggregationMonthly;

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
  String leaderboardMyRank(Object rank);

  /// No description provided for @leaderboardPoints.
  ///
  /// In zh, this message translates to:
  /// **'{value}分'**
  String leaderboardPoints(Object value);

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
  String taskFeedbackStreakDays(Object count);

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
  String communityReadByCount(Object count);

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
  String shareResourceGroupMembers(Object count);

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
  String calendarReminderMinutes(Object count);

  /// No description provided for @calendarReminderHours.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时前'**
  String calendarReminderHours(Object count);

  /// No description provided for @calendarReminderDays.
  ///
  /// In zh, this message translates to:
  /// **'{count}天前'**
  String calendarReminderDays(Object count);

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
  String capsulePersonalizationBadge(Object pattern);

  /// No description provided for @capsulePersonalizationExplanation.
  ///
  /// In zh, this message translates to:
  /// **'基于你最近的{patterns}行为模式，AI为你精选了这个知识点。'**
  String capsulePersonalizationExplanation(Object patterns);

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
  String cognitiveFutureDays(Object count);

  /// No description provided for @cognitiveDaysLater.
  ///
  /// In zh, this message translates to:
  /// **'{count} 天后'**
  String cognitiveDaysLater(Object count);

  /// No description provided for @cognitiveToday.
  ///
  /// In zh, this message translates to:
  /// **'今天'**
  String get cognitiveToday;

  /// No description provided for @cognitiveDayTick.
  ///
  /// In zh, this message translates to:
  /// **'{count}天'**
  String cognitiveDayTick(Object count);

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
  String cognitiveReviewNow(Object count);

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
  String prismTotalPatterns(Object count);

  /// No description provided for @capsuleScreenTitle.
  ///
  /// In zh, this message translates to:
  /// **'好奇心胶囊'**
  String get capsuleScreenTitle;

  /// No description provided for @capsuleCurrentTab.
  ///
  /// In zh, this message translates to:
  /// **'当前胶囊 {count}'**
  String capsuleCurrentTab(Object count);

  /// No description provided for @capsuleArchiveTab.
  ///
  /// In zh, this message translates to:
  /// **'历史归档 {count}'**
  String capsuleArchiveTab(Object count);

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
  String capsuleGenerationPreviewCount(Object count);

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
  String patternCardCreatedAt(Object date);

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
  String capsuleLoadFailed(Object error);

  /// No description provided for @capsuleQualityLabel.
  ///
  /// In zh, this message translates to:
  /// **'质量评分：{rating}'**
  String capsuleQualityLabel(Object rating);

  /// No description provided for @capsuleFeedbackCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 反馈'**
  String capsuleFeedbackCount(Object count);

  /// No description provided for @capsuleShareCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 分享'**
  String capsuleShareCount(Object count);

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
  String capsuleSubmitFailed(Object error);

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
  String capsuleGeneratingProgress(Object progress);

  /// No description provided for @capsuleDepthPercent.
  ///
  /// In zh, this message translates to:
  /// **'深度：{percent}%'**
  String capsuleDepthPercent(Object percent);

  /// No description provided for @capsuleCuriosityPercent.
  ///
  /// In zh, this message translates to:
  /// **'好奇：{percent}%'**
  String capsuleCuriosityPercent(Object percent);

  /// No description provided for @capsuleRequestedCount.
  ///
  /// In zh, this message translates to:
  /// **'请求数量：{count}'**
  String capsuleRequestedCount(Object count);

  /// No description provided for @capsuleActualCount.
  ///
  /// In zh, this message translates to:
  /// **'实际数量：{count}'**
  String capsuleActualCount(Object count);

  /// No description provided for @capsuleChipLabel.
  ///
  /// In zh, this message translates to:
  /// **'胶囊 {id}'**
  String capsuleChipLabel(Object id);

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
  String patternDiscoveredOn(Object date);

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
  String chatHistoryLoadFailed(Object error);

  /// No description provided for @chatHistoryLoadMoreFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载更多失败：{error}'**
  String chatHistoryLoadMoreFailed(Object error);

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

  /// No description provided for @chatCitationExcerptUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'这条引用暂时还没有可展示的原文摘录。'**
  String get chatCitationExcerptUnavailable;

  /// No description provided for @chatCitationHelpfulPrompt.
  ///
  /// In zh, this message translates to:
  /// **'这条引用对你有帮助吗？'**
  String get chatCitationHelpfulPrompt;

  /// No description provided for @chatCitationOpenDocument.
  ///
  /// In zh, this message translates to:
  /// **'前往文档'**
  String get chatCitationOpenDocument;

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
  String chatTeamSheetSelectedExperts(Object count);

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
  String chatActiveToolsCount(Object count);

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
  String chatExecutionStepsCount(Object count);

  /// No description provided for @chatModeSelect.
  ///
  /// In zh, this message translates to:
  /// **'选择模式'**
  String get chatModeSelect;

  /// No description provided for @chatModeTeamSummary.
  ///
  /// In zh, this message translates to:
  /// **'{count}位专家·{mode}'**
  String chatModeTeamSummary(Object count, Object mode);

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
  String errorBookCreatedAt(Object date);

  /// No description provided for @errorBookMasteryPercent.
  ///
  /// In zh, this message translates to:
  /// **'{percent}%掌握'**
  String errorBookMasteryPercent(Object percent);

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
  String errorBookKnowledgeLinkSnack(Object nodeName);

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
  String errorBookDeleteFailedMessage(Object error);

  /// No description provided for @errorBookCognitiveFilter.
  ///
  /// In zh, this message translates to:
  /// **'正针对 \"{dimension}\" 维度进行针对性复习'**
  String errorBookCognitiveFilter(Object dimension);

  /// No description provided for @errorBookReviewCount.
  ///
  /// In zh, this message translates to:
  /// **'复习 {count} 次'**
  String errorBookReviewCount(Object count);

  /// No description provided for @errorBookAIAnalyzed.
  ///
  /// In zh, this message translates to:
  /// **'AI已分析'**
  String get errorBookAIAnalyzed;

  /// No description provided for @errorBookTimeAgoMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count}分钟前'**
  String errorBookTimeAgoMinutes(Object count);

  /// No description provided for @errorBookTimeAgoHours.
  ///
  /// In zh, this message translates to:
  /// **'{count}小时前'**
  String errorBookTimeAgoHours(Object count);

  /// No description provided for @errorBookTimeAgoDays.
  ///
  /// In zh, this message translates to:
  /// **'{count}天前'**
  String errorBookTimeAgoDays(Object count);

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
  String reviewProgress(Object current, Object total);

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
  String reviewSubmitFailed(Object error);

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
  String reviewTotalReviewed(Object count);

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
  String communityMembers(Object count);

  /// No description provided for @friendsMyFriends.
  ///
  /// In zh, this message translates to:
  /// **'我的好友'**
  String get friendsMyFriends;

  /// No description provided for @friendsFriendRequests.
  ///
  /// In zh, this message translates to:
  /// **'好友请求'**
  String get friendsFriendRequests;

  /// No description provided for @friendsDiscoverFriends.
  ///
  /// In zh, this message translates to:
  /// **'发现好友'**
  String get friendsDiscoverFriends;

  /// No description provided for @friendsDeleteFriend.
  ///
  /// In zh, this message translates to:
  /// **'删除好友'**
  String get friendsDeleteFriend;

  /// No description provided for @friendsConfirmDeleteFriend.
  ///
  /// In zh, this message translates to:
  /// **'确定要删除好友 {name} 吗？'**
  String friendsConfirmDeleteFriend(Object name);

  /// No description provided for @friendsCancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get friendsCancel;

  /// No description provided for @friendsDelete.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get friendsDelete;

  /// No description provided for @friendsFriendDeleted.
  ///
  /// In zh, this message translates to:
  /// **'已将 {name} 从好友列表中移除'**
  String friendsFriendDeleted(Object name);

  /// No description provided for @friendsDeleteFailed.
  ///
  /// In zh, this message translates to:
  /// **'删除好友失败：{error}'**
  String friendsDeleteFailed(Object error);

  /// No description provided for @friendsBlockUser.
  ///
  /// In zh, this message translates to:
  /// **'拉黑用户'**
  String get friendsBlockUser;

  /// No description provided for @friendsAfterBlockingHint.
  ///
  /// In zh, this message translates to:
  /// **'拉黑 {name} 后：'**
  String friendsAfterBlockingHint(Object name);

  /// No description provided for @friendsRemoveFromFriendList.
  ///
  /// In zh, this message translates to:
  /// **'将从你的好友列表中移除'**
  String get friendsRemoveFromFriendList;

  /// No description provided for @friendsCannotMessageYou.
  ///
  /// In zh, this message translates to:
  /// **'无法给你发送消息'**
  String get friendsCannotMessageYou;

  /// No description provided for @friendsCannotSendRequest.
  ///
  /// In zh, this message translates to:
  /// **'无法向你发送好友请求'**
  String get friendsCannotSendRequest;

  /// No description provided for @friendsBlock.
  ///
  /// In zh, this message translates to:
  /// **'拉黑'**
  String get friendsBlock;

  /// No description provided for @friendsBlockedSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已拉黑 {name}'**
  String friendsBlockedSuccess(Object name);

  /// No description provided for @friendsBlockFailed.
  ///
  /// In zh, this message translates to:
  /// **'拉黑用户失败：{error}'**
  String friendsBlockFailed(Object error);

  /// No description provided for @friendsBlockedUsersManagement.
  ///
  /// In zh, this message translates to:
  /// **'管理黑名单'**
  String get friendsBlockedUsersManagement;

  /// No description provided for @friendsNoPendingRequests.
  ///
  /// In zh, this message translates to:
  /// **'暂无待处理请求'**
  String get friendsNoPendingRequests;

  /// No description provided for @friendsWantsToBeYourFriend.
  ///
  /// In zh, this message translates to:
  /// **'想成为你的好友'**
  String get friendsWantsToBeYourFriend;

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
  String planProgressPercent(Object percent);

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

  /// No description provided for @knowledgeSourceMaterialsTitle.
  ///
  /// In zh, this message translates to:
  /// **'来源资料'**
  String get knowledgeSourceMaterialsTitle;

  /// No description provided for @knowledgeSourceMaterialsSummary.
  ///
  /// In zh, this message translates to:
  /// **'{documents} 份文档 · {chunks} 个知识片段'**
  String knowledgeSourceMaterialsSummary(Object documents, Object chunks);

  /// No description provided for @knowledgeSourceMaterialsPersonalBadge.
  ///
  /// In zh, this message translates to:
  /// **'我的上传'**
  String get knowledgeSourceMaterialsPersonalBadge;

  /// No description provided for @knowledgeSourceMaterialsSystemBadge.
  ///
  /// In zh, this message translates to:
  /// **'暂未附带个人笔记'**
  String get knowledgeSourceMaterialsSystemBadge;

  /// No description provided for @knowledgeSourceMaterialsUploadDate.
  ///
  /// In zh, this message translates to:
  /// **'上传于 {date}'**
  String knowledgeSourceMaterialsUploadDate(Object date);

  /// No description provided for @knowledgeSourceMaterialsChunkUnit.
  ///
  /// In zh, this message translates to:
  /// **'片段'**
  String get knowledgeSourceMaterialsChunkUnit;

  /// No description provided for @knowledgeSourceMaterialsEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'让这个节点回到你的真实资料里'**
  String get knowledgeSourceMaterialsEmptyTitle;

  /// No description provided for @knowledgeSourceMaterialsEmptyBody.
  ///
  /// In zh, this message translates to:
  /// **'为「{topic}」补充自己的讲义或笔记，让这条知识真正可追溯。'**
  String knowledgeSourceMaterialsEmptyBody(Object topic);

  /// No description provided for @knowledgeSourceMaterialsAddNotes.
  ///
  /// In zh, this message translates to:
  /// **'添加关于「{topic}」的笔记'**
  String knowledgeSourceMaterialsAddNotes(Object topic);

  /// No description provided for @knowledgeSourceMaterialsReadMore.
  ///
  /// In zh, this message translates to:
  /// **'阅读更多'**
  String get knowledgeSourceMaterialsReadMore;

  /// No description provided for @knowledgeSourceMaterialsNoPreview.
  ///
  /// In zh, this message translates to:
  /// **'这份资料暂时还没有可展示的片段。'**
  String get knowledgeSourceMaterialsNoPreview;

  /// No description provided for @knowledgeSourceMaterialsOpenFailed.
  ///
  /// In zh, this message translates to:
  /// **'暂时无法打开来源资料。'**
  String get knowledgeSourceMaterialsOpenFailed;

  /// No description provided for @knowledgeSourceMaterialsUploadSaved.
  ///
  /// In zh, this message translates to:
  /// **'{filename} 已上传，处理并挂接后会显示在这里。'**
  String knowledgeSourceMaterialsUploadSaved(Object filename);

  /// No description provided for @knowledgeSourceMaterialsPage.
  ///
  /// In zh, this message translates to:
  /// **'第 {page} 页'**
  String knowledgeSourceMaterialsPage(Object page);

  /// No description provided for @knowledgeSourceMaterialsPages.
  ///
  /// In zh, this message translates to:
  /// **'第 {pages} 页'**
  String knowledgeSourceMaterialsPages(Object pages);

  /// No description provided for @knowledgeSourceMaterialsChunk.
  ///
  /// In zh, this message translates to:
  /// **'片段 {index}'**
  String knowledgeSourceMaterialsChunk(Object index);

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
  String knowledgeDaysLater(Object days);

  /// No description provided for @knowledgeWeeksLater.
  ///
  /// In zh, this message translates to:
  /// **'{weeks}周后'**
  String knowledgeWeeksLater(Object weeks);

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
  String seedLibraryItemCount(Object count);

  /// No description provided for @seedLibraryLastUpdated.
  ///
  /// In zh, this message translates to:
  /// **'最后更新: {date}'**
  String seedLibraryLastUpdated(Object date);

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
  String seedLibraryDeleteFailed(Object error);

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
  String translationMinutesAgo(Object minutes);

  /// No description provided for @translationHoursAgo.
  ///
  /// In zh, this message translates to:
  /// **'{hours}小时前'**
  String translationHoursAgo(Object hours);

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
  String translationDaysAgo(Object days);

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
  /// **'通知权限被拒绝，请在系统设置中开启'**
  String get notificationPermissionDenied;

  /// No description provided for @notificationPermissionPartial.
  ///
  /// In zh, this message translates to:
  /// **'部分通知功能受限，建议开启完整权限'**
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

  /// No description provided for @chatOpenStudyMaterialsLibrary.
  ///
  /// In zh, this message translates to:
  /// **'打开学习资料库'**
  String get chatOpenStudyMaterialsLibrary;

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

  /// No description provided for @chatModeSectionQuickChat.
  ///
  /// In zh, this message translates to:
  /// **'快速对话'**
  String get chatModeSectionQuickChat;

  /// No description provided for @chatModeSectionDeepWork.
  ///
  /// In zh, this message translates to:
  /// **'深度工作流'**
  String get chatModeSectionDeepWork;

  /// No description provided for @chatModeSectionExpertAccess.
  ///
  /// In zh, this message translates to:
  /// **'专家协助'**
  String get chatModeSectionExpertAccess;

  /// No description provided for @chatModeTransitionToWorkflow.
  ///
  /// In zh, this message translates to:
  /// **'已切换至{mode}，多专家将协作分析'**
  String chatModeTransitionToWorkflow(Object mode);

  /// No description provided for @chatModeTransitionToDirect.
  ///
  /// In zh, this message translates to:
  /// **'已回到标准对话模式'**
  String get chatModeTransitionToDirect;

  /// No description provided for @chatModeTransitionSwitched.
  ///
  /// In zh, this message translates to:
  /// **'已切换至{mode}'**
  String chatModeTransitionSwitched(Object mode);

  /// No description provided for @capabilityCeilingTitle.
  ///
  /// In zh, this message translates to:
  /// **'能力边界提示'**
  String get capabilityCeilingTitle;

  /// No description provided for @capabilityCeilingDefault.
  ///
  /// In zh, this message translates to:
  /// **'当前模式可能无法完全解决此问题'**
  String get capabilityCeilingDefault;

  /// No description provided for @capabilityCeilingAlternatives.
  ///
  /// In zh, this message translates to:
  /// **'试试更强的模式：'**
  String get capabilityCeilingAlternatives;

  /// No description provided for @capabilityCeilingContinue.
  ///
  /// In zh, this message translates to:
  /// **'仍然继续'**
  String get capabilityCeilingContinue;

  /// No description provided for @guidanceModeAi.
  ///
  /// In zh, this message translates to:
  /// **'AI 引导'**
  String get guidanceModeAi;

  /// No description provided for @guidanceModeSelf.
  ///
  /// In zh, this message translates to:
  /// **'自主探索'**
  String get guidanceModeSelf;

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

  /// No description provided for @chatStudyMaterialsEmptySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'上传你的笔记、课件或 PDF 后，就能在聊天里作为学习资料使用。'**
  String get chatStudyMaterialsEmptySubtitle;

  /// No description provided for @chatStudyMaterialsAvailable.
  ///
  /// In zh, this message translates to:
  /// **'{count} 份资料可用'**
  String chatStudyMaterialsAvailable(Object count);

  /// No description provided for @chatStudyMaterialsKnowledgeNodes.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个知识节点'**
  String chatStudyMaterialsKnowledgeNodes(Object count);

  /// No description provided for @chatStudyMaterialsLabel.
  ///
  /// In zh, this message translates to:
  /// **'学习资料'**
  String get chatStudyMaterialsLabel;

  /// No description provided for @chatStudyMaterialsPaused.
  ///
  /// In zh, this message translates to:
  /// **'学习资料已暂停'**
  String get chatStudyMaterialsPaused;

  /// No description provided for @chatStudyMaterialsPausedDescription.
  ///
  /// In zh, this message translates to:
  /// **'下一轮对话将暂停文档检索。'**
  String get chatStudyMaterialsPausedDescription;

  /// No description provided for @chatStudyMaterialsReady.
  ///
  /// In zh, this message translates to:
  /// **'已就绪'**
  String get chatStudyMaterialsReady;

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

  /// No description provided for @groupKnowledgeBase.
  ///
  /// In zh, this message translates to:
  /// **'知识库'**
  String get groupKnowledgeBase;

  /// No description provided for @groupFiles.
  ///
  /// In zh, this message translates to:
  /// **'学习资料'**
  String get groupFiles;

  /// No description provided for @saveToMyLibrary.
  ///
  /// In zh, this message translates to:
  /// **'保存到我的库'**
  String get saveToMyLibrary;

  /// No description provided for @savedToLibrary.
  ///
  /// In zh, this message translates to:
  /// **'已保存到你的库'**
  String get savedToLibrary;

  /// No description provided for @markAsOfficial.
  ///
  /// In zh, this message translates to:
  /// **'标记为官方'**
  String get markAsOfficial;

  /// No description provided for @officialResource.
  ///
  /// In zh, this message translates to:
  /// **'官方'**
  String get officialResource;

  /// No description provided for @noGroupFiles.
  ///
  /// In zh, this message translates to:
  /// **'暂无学习资料'**
  String get noGroupFiles;

  /// No description provided for @noGroupFilesSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'分享你的笔记，帮助群组成员！'**
  String get noGroupFilesSubtitle;

  /// No description provided for @shareFile.
  ///
  /// In zh, this message translates to:
  /// **'分享文件'**
  String get shareFile;

  /// No description provided for @groupFilesCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个文件'**
  String groupFilesCount(Object count);

  /// No description provided for @studyMaterialsTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习资料库'**
  String get studyMaterialsTitle;

  /// No description provided for @studyMaterialsEntrySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'查看上传资料、处理进度，并管理知识来源'**
  String get studyMaterialsEntrySubtitle;

  /// No description provided for @studyMaterialsHeroEyebrow.
  ///
  /// In zh, this message translates to:
  /// **'个人知识资料馆'**
  String get studyMaterialsHeroEyebrow;

  /// No description provided for @studyMaterialsHeroTitle.
  ///
  /// In zh, this message translates to:
  /// **'把每一次上传都变成可调用的学习上下文'**
  String get studyMaterialsHeroTitle;

  /// No description provided for @studyMaterialsHeroSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'统一管理你的笔记、课件和 PDF，查看它们落到哪些知识星点，并追踪 Aurora 实际引用了多少次。'**
  String get studyMaterialsHeroSubtitle;

  /// No description provided for @studyMaterialsMetricDocs.
  ///
  /// In zh, this message translates to:
  /// **'资料数'**
  String get studyMaterialsMetricDocs;

  /// No description provided for @studyMaterialsMetricReady.
  ///
  /// In zh, this message translates to:
  /// **'已就绪'**
  String get studyMaterialsMetricReady;

  /// No description provided for @studyMaterialsMetricInMotion.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get studyMaterialsMetricInMotion;

  /// No description provided for @studyMaterialsMetricWeeklyRefs.
  ///
  /// In zh, this message translates to:
  /// **'周引用'**
  String get studyMaterialsMetricWeeklyRefs;

  /// No description provided for @studyMaterialsSearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索文件名、知识节点或引用片段'**
  String get studyMaterialsSearchHint;

  /// No description provided for @studyMaterialsFilterTitle.
  ///
  /// In zh, this message translates to:
  /// **'筛选'**
  String get studyMaterialsFilterTitle;

  /// No description provided for @studyMaterialsFilterAllStatus.
  ///
  /// In zh, this message translates to:
  /// **'全部状态'**
  String get studyMaterialsFilterAllStatus;

  /// No description provided for @studyMaterialsFilterHighlyCited.
  ///
  /// In zh, this message translates to:
  /// **'高引用'**
  String get studyMaterialsFilterHighlyCited;

  /// No description provided for @studyMaterialsFilterAllSubjects.
  ///
  /// In zh, this message translates to:
  /// **'全部学域'**
  String get studyMaterialsFilterAllSubjects;

  /// No description provided for @studyMaterialsFilterNode.
  ///
  /// In zh, this message translates to:
  /// **'当前节点：{nodeName}'**
  String studyMaterialsFilterNode(Object nodeName);

  /// No description provided for @studyMaterialsFilterClearNode.
  ///
  /// In zh, this message translates to:
  /// **'清除节点筛选'**
  String get studyMaterialsFilterClearNode;

  /// No description provided for @studyMaterialsDate.
  ///
  /// In zh, this message translates to:
  /// **'时间'**
  String get studyMaterialsDate;

  /// No description provided for @studyMaterialsDateAll.
  ///
  /// In zh, this message translates to:
  /// **'不限时间'**
  String get studyMaterialsDateAll;

  /// No description provided for @studyMaterialsDate7d.
  ///
  /// In zh, this message translates to:
  /// **'近 7 天'**
  String get studyMaterialsDate7d;

  /// No description provided for @studyMaterialsDate30d.
  ///
  /// In zh, this message translates to:
  /// **'近 30 天'**
  String get studyMaterialsDate30d;

  /// No description provided for @studyMaterialsDate90d.
  ///
  /// In zh, this message translates to:
  /// **'近 90 天'**
  String get studyMaterialsDate90d;

  /// No description provided for @studyMaterialsLoadError.
  ///
  /// In zh, this message translates to:
  /// **'暂时无法加载学习资料。'**
  String get studyMaterialsLoadError;

  /// No description provided for @studyMaterialsRefreshCta.
  ///
  /// In zh, this message translates to:
  /// **'重新加载'**
  String get studyMaterialsRefreshCta;

  /// No description provided for @studyMaterialsUploadCta.
  ///
  /// In zh, this message translates to:
  /// **'上传学习资料'**
  String get studyMaterialsUploadCta;

  /// No description provided for @studyMaterialsUploadCtaShort.
  ///
  /// In zh, this message translates to:
  /// **'上传'**
  String get studyMaterialsUploadCtaShort;

  /// No description provided for @studyMaterialsUploadSuccess.
  ///
  /// In zh, this message translates to:
  /// **'上传已开始，我们会很快把它映射进你的知识星图。'**
  String get studyMaterialsUploadSuccess;

  /// No description provided for @studyMaterialsDeleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'删除这份学习资料？'**
  String get studyMaterialsDeleteTitle;

  /// No description provided for @studyMaterialsDeleteMessage.
  ///
  /// In zh, this message translates to:
  /// **'要从资料库中删除 {filename} 吗？这会将它从你的个人资料中移除。'**
  String studyMaterialsDeleteMessage(Object filename);

  /// No description provided for @studyMaterialsDeleteSuccess.
  ///
  /// In zh, this message translates to:
  /// **'学习资料已删除'**
  String get studyMaterialsDeleteSuccess;

  /// No description provided for @studyMaterialsDeleteFailure.
  ///
  /// In zh, this message translates to:
  /// **'删除学习资料失败：{error}'**
  String studyMaterialsDeleteFailure(Object error);

  /// No description provided for @studyMaterialsShareSheetTitle.
  ///
  /// In zh, this message translates to:
  /// **'分享到群组'**
  String get studyMaterialsShareSheetTitle;

  /// No description provided for @studyMaterialsShareGroupSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{count} 位成员'**
  String studyMaterialsShareGroupSubtitle(Object count);

  /// No description provided for @studyMaterialsShareEmptyGroups.
  ///
  /// In zh, this message translates to:
  /// **'请先加入或创建群组，再分享学习资料。'**
  String get studyMaterialsShareEmptyGroups;

  /// No description provided for @studyMaterialsShareLoadGroupsError.
  ///
  /// In zh, this message translates to:
  /// **'暂时无法加载你的群组列表。'**
  String get studyMaterialsShareLoadGroupsError;

  /// No description provided for @studyMaterialsShareSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已分享到 {groupName}'**
  String studyMaterialsShareSuccess(Object groupName);

  /// No description provided for @studyMaterialsShareFailure.
  ///
  /// In zh, this message translates to:
  /// **'分享学习资料失败：{error}'**
  String studyMaterialsShareFailure(Object error);

  /// No description provided for @studyMaterialsVisibilityGroup.
  ///
  /// In zh, this message translates to:
  /// **'群组可见'**
  String get studyMaterialsVisibilityGroup;

  /// No description provided for @studyMaterialsVisibilityPrivate.
  ///
  /// In zh, this message translates to:
  /// **'仅自己可见'**
  String get studyMaterialsVisibilityPrivate;

  /// No description provided for @studyMaterialsAttachedNodesTitle.
  ///
  /// In zh, this message translates to:
  /// **'挂载的知识星点'**
  String get studyMaterialsAttachedNodesTitle;

  /// No description provided for @studyMaterialsNodesPending.
  ///
  /// In zh, this message translates to:
  /// **'这份资料还在映射到你的知识星图节点中。'**
  String get studyMaterialsNodesPending;

  /// No description provided for @studyMaterialsNodesEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂时还没有挂载到任何知识节点。'**
  String get studyMaterialsNodesEmpty;

  /// No description provided for @studyMaterialsTopChunksTitle.
  ///
  /// In zh, this message translates to:
  /// **'高频引用片段'**
  String get studyMaterialsTopChunksTitle;

  /// No description provided for @studyMaterialsTopChunksEmpty.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 还没有引用过这份资料。'**
  String get studyMaterialsTopChunksEmpty;

  /// No description provided for @studyMaterialsConversationCountLabel.
  ///
  /// In zh, this message translates to:
  /// **'对话数'**
  String get studyMaterialsConversationCountLabel;

  /// No description provided for @studyMaterialsReferenceCountLabel.
  ///
  /// In zh, this message translates to:
  /// **'引用次数'**
  String get studyMaterialsReferenceCountLabel;

  /// No description provided for @studyMaterialsKnowledgeStarsLabel.
  ///
  /// In zh, this message translates to:
  /// **'知识星点'**
  String get studyMaterialsKnowledgeStarsLabel;

  /// No description provided for @studyMaterialsShareAction.
  ///
  /// In zh, this message translates to:
  /// **'分享'**
  String get studyMaterialsShareAction;

  /// No description provided for @studyMaterialsDeleteAction.
  ///
  /// In zh, this message translates to:
  /// **'删除'**
  String get studyMaterialsDeleteAction;

  /// No description provided for @studyMaterialsRefreshAction.
  ///
  /// In zh, this message translates to:
  /// **'重新处理'**
  String get studyMaterialsRefreshAction;

  /// No description provided for @studyMaterialsSubjectCosmos.
  ///
  /// In zh, this message translates to:
  /// **'宇宙'**
  String get studyMaterialsSubjectCosmos;

  /// No description provided for @studyMaterialsSubjectTech.
  ///
  /// In zh, this message translates to:
  /// **'技术'**
  String get studyMaterialsSubjectTech;

  /// No description provided for @studyMaterialsSubjectArt.
  ///
  /// In zh, this message translates to:
  /// **'艺术'**
  String get studyMaterialsSubjectArt;

  /// No description provided for @studyMaterialsSubjectCivilization.
  ///
  /// In zh, this message translates to:
  /// **'文明'**
  String get studyMaterialsSubjectCivilization;

  /// No description provided for @studyMaterialsSubjectLife.
  ///
  /// In zh, this message translates to:
  /// **'生命'**
  String get studyMaterialsSubjectLife;

  /// No description provided for @studyMaterialsSubjectWisdom.
  ///
  /// In zh, this message translates to:
  /// **'智慧'**
  String get studyMaterialsSubjectWisdom;

  /// No description provided for @studyMaterialsSubjectGeneral.
  ///
  /// In zh, this message translates to:
  /// **'通用'**
  String get studyMaterialsSubjectGeneral;

  /// No description provided for @studyMaterialsUsageWeekly.
  ///
  /// In zh, this message translates to:
  /// **'本周已被引用 {count} 次'**
  String studyMaterialsUsageWeekly(Object count);

  /// No description provided for @studyMaterialsUsageTotal.
  ///
  /// In zh, this message translates to:
  /// **'累计已被引用 {count} 次'**
  String studyMaterialsUsageTotal(Object count);

  /// No description provided for @studyMaterialsUsageEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂未在对话中被引用'**
  String get studyMaterialsUsageEmpty;

  /// No description provided for @studyMaterialsUploadedDays.
  ///
  /// In zh, this message translates to:
  /// **'{count} 天前'**
  String studyMaterialsUploadedDays(Object count);

  /// No description provided for @studyMaterialsUploadedHours.
  ///
  /// In zh, this message translates to:
  /// **'{count} 小时前'**
  String studyMaterialsUploadedHours(Object count);

  /// No description provided for @studyMaterialsUploadedMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count} 分钟前'**
  String studyMaterialsUploadedMinutes(Object count);

  /// No description provided for @studyMaterialsStatusProcessingPercent.
  ///
  /// In zh, this message translates to:
  /// **'处理中 {percent}%'**
  String studyMaterialsStatusProcessingPercent(Object percent);

  /// No description provided for @studyMaterialsStatusProcessing.
  ///
  /// In zh, this message translates to:
  /// **'处理中'**
  String get studyMaterialsStatusProcessing;

  /// No description provided for @studyMaterialsStatusKnowledgeStars.
  ///
  /// In zh, this message translates to:
  /// **'已映射 {count} 个星点'**
  String studyMaterialsStatusKnowledgeStars(Object count);

  /// No description provided for @studyMaterialsStatusReady.
  ///
  /// In zh, this message translates to:
  /// **'已就绪'**
  String get studyMaterialsStatusReady;

  /// No description provided for @studyMaterialsStatusFailed.
  ///
  /// In zh, this message translates to:
  /// **'处理失败'**
  String get studyMaterialsStatusFailed;

  /// No description provided for @studyMaterialsChunkHitCount.
  ///
  /// In zh, this message translates to:
  /// **'命中 {count} 次'**
  String studyMaterialsChunkHitCount(Object count);

  /// No description provided for @studyMaterialsNoResultsTitle.
  ///
  /// In zh, this message translates to:
  /// **'没有匹配的学习资料'**
  String get studyMaterialsNoResultsTitle;

  /// No description provided for @studyMaterialsEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'你的学习宇宙正等待点亮'**
  String get studyMaterialsEmptyTitle;

  /// No description provided for @studyMaterialsNoResultsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'换个搜索词，或清空筛选条件，看看更多资料。'**
  String get studyMaterialsNoResultsSubtitle;

  /// No description provided for @studyMaterialsEmptySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'上传你的第一份笔记、课件或教材，Sparkle 会把它们转成可搜索的知识星图。'**
  String get studyMaterialsEmptySubtitle;

  /// No description provided for @studyMaterialsResetFilters.
  ///
  /// In zh, this message translates to:
  /// **'重置筛选'**
  String get studyMaterialsResetFilters;

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

  /// No description provided for @galaxyNodeLaunchPrediction.
  ///
  /// In zh, this message translates to:
  /// **'推演此节点'**
  String get galaxyNodeLaunchPrediction;

  /// No description provided for @galaxyNodeLocked.
  ///
  /// In zh, this message translates to:
  /// **'已锁定'**
  String get galaxyNodeLocked;

  /// No description provided for @galaxyNodeLockedHint.
  ///
  /// In zh, this message translates to:
  /// **'可先查看详情了解前置关系，再决定如何解锁这个节点。'**
  String get galaxyNodeLockedHint;

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

  /// No description provided for @planDetailAddExistingTask.
  ///
  /// In zh, this message translates to:
  /// **'添加已有'**
  String get planDetailAddExistingTask;

  /// No description provided for @planDetailAddNewTask.
  ///
  /// In zh, this message translates to:
  /// **'新增任务'**
  String get planDetailAddNewTask;

  /// No description provided for @planDetailAddPhase.
  ///
  /// In zh, this message translates to:
  /// **'新增阶段'**
  String get planDetailAddPhase;

  /// No description provided for @planDetailAiGuide.
  ///
  /// In zh, this message translates to:
  /// **'AI执行指南'**
  String get planDetailAiGuide;

  /// No description provided for @planDetailCompressionDesc.
  ///
  /// In zh, this message translates to:
  /// **'今天只保留 {taskCount} 个任务 / {totalMinutes} 分钟，先把主线接回来。'**
  String planDetailCompressionDesc(Object taskCount, Object totalMinutes);

  /// No description provided for @planDetailCompressionTitle.
  ///
  /// In zh, this message translates to:
  /// **'已为你精简今日计划'**
  String get planDetailCompressionTitle;

  /// No description provided for @planDetailCommonMistakes.
  ///
  /// In zh, this message translates to:
  /// **'⚠️ 常见误区'**
  String get planDetailCommonMistakes;

  /// No description provided for @planDetailDailyRhythm.
  ///
  /// In zh, this message translates to:
  /// **'每日节奏'**
  String get planDetailDailyRhythm;

  /// No description provided for @planDetailDayGroupSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{count} 件 · {minutes} 分钟'**
  String planDetailDayGroupSubtitle(Object count, Object minutes);

  /// No description provided for @planDetailDefaultRecommendation.
  ///
  /// In zh, this message translates to:
  /// **'今天不再学新内容，只做高频知识点速览、错题错因回看和 30 分钟短模拟。'**
  String get planDetailDefaultRecommendation;

  /// No description provided for @planDetailEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑计划'**
  String get planDetailEdit;

  /// No description provided for @planDetailFullPlan.
  ///
  /// In zh, this message translates to:
  /// **'完整计划'**
  String get planDetailFullPlan;

  /// No description provided for @planDetailHealthNeedAttention.
  ///
  /// In zh, this message translates to:
  /// **'需要关注'**
  String get planDetailHealthNeedAttention;

  /// No description provided for @planDetailHealthNeedReplan.
  ///
  /// In zh, this message translates to:
  /// **'需要重排'**
  String get planDetailHealthNeedReplan;

  /// No description provided for @planDetailHealthReasonDefault.
  ///
  /// In zh, this message translates to:
  /// **'暂无明确风险原因'**
  String get planDetailHealthReasonDefault;

  /// No description provided for @planDetailHealthReasonProgressLag.
  ///
  /// In zh, this message translates to:
  /// **'当前进度落后于时间线，建议优先处理高收益任务。'**
  String get planDetailHealthReasonProgressLag;

  /// No description provided for @planDetailHealthReasonTimeOverrun.
  ///
  /// In zh, this message translates to:
  /// **'最近任务用时偏长，可以考虑压缩下一步。'**
  String get planDetailHealthReasonTimeOverrun;

  /// No description provided for @planDetailHealthReasonTooEasy.
  ///
  /// In zh, this message translates to:
  /// **'最近反馈偏简单，可以适当提高挑战度。'**
  String get planDetailHealthReasonTooEasy;

  /// No description provided for @planDetailHealthReasonTooHard.
  ///
  /// In zh, this message translates to:
  /// **'最近反馈偏难，适合先拆小或补一个前置概念。'**
  String get planDetailHealthReasonTooHard;

  /// No description provided for @planDetailHealthScore.
  ///
  /// In zh, this message translates to:
  /// **'计划健康度 {score}% · {label}'**
  String planDetailHealthScore(Object score, Object label);

  /// No description provided for @planDetailHealthStable.
  ///
  /// In zh, this message translates to:
  /// **'稳定'**
  String get planDetailHealthStable;

  /// No description provided for @planDetailLearningPathLoadError.
  ///
  /// In zh, this message translates to:
  /// **'学习路径进度加载失败：{error}'**
  String planDetailLearningPathLoadError(Object error);

  /// No description provided for @planDetailLoadError.
  ///
  /// In zh, this message translates to:
  /// **'计划加载失败'**
  String get planDetailLoadError;

  /// No description provided for @planDetailLoadError404.
  ///
  /// In zh, this message translates to:
  /// **'计划刚生成完成，详情可能还在同步。点\"重试\"继续加载就好。'**
  String get planDetailLoadError404;

  /// No description provided for @planDetailLoadErrorEmpty.
  ///
  /// In zh, this message translates to:
  /// **'计划详情暂时没加载出来，请重试一次。'**
  String get planDetailLoadErrorEmpty;

  /// No description provided for @planDetailLoadErrorGeneric.
  ///
  /// In zh, this message translates to:
  /// **'计划详情暂时没加载出来：{error}'**
  String planDetailLoadErrorGeneric(Object error);

  /// No description provided for @planDetailLoadErrorTimeout.
  ///
  /// In zh, this message translates to:
  /// **'加载计划超时了，请检查网络后再试一次。'**
  String get planDetailLoadErrorTimeout;

  /// No description provided for @planDetailMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String planDetailMinutes(Object minutes);

  /// No description provided for @planDetailNoPhasesYet.
  ///
  /// In zh, this message translates to:
  /// **'还没有真实阶段，先创建第一个 phase，把长期计划拆成可执行的小段。'**
  String get planDetailNoPhasesYet;

  /// No description provided for @planDetailPhasesLoadError.
  ///
  /// In zh, this message translates to:
  /// **'阶段加载失败：{error}'**
  String planDetailPhasesLoadError(Object error);

  /// No description provided for @planDetailPhasesTitle.
  ///
  /// In zh, this message translates to:
  /// **'计划阶段'**
  String get planDetailPhasesTitle;

  /// No description provided for @planDetailPlanScope.
  ///
  /// In zh, this message translates to:
  /// **'计划边界'**
  String get planDetailPlanScope;

  /// No description provided for @planDetailRecommendationDay1.
  ///
  /// In zh, this message translates to:
  /// **'今天先做好{thingLabel}，你已经走在正确路上了。'**
  String planDetailRecommendationDay1(Object thingLabel);

  /// No description provided for @planDetailRecommendationDayN.
  ///
  /// In zh, this message translates to:
  /// **'先看 Day {day} 的{thingLabel}，把节奏稳稳接上。'**
  String planDetailRecommendationDayN(Object day, Object thingLabel);

  /// No description provided for @planDetailSprintMode7Day.
  ///
  /// In zh, this message translates to:
  /// **'7 天冲刺模式'**
  String get planDetailSprintMode7Day;

  /// No description provided for @planDetailSprintModeExam.
  ///
  /// In zh, this message translates to:
  /// **'考试冲刺模式'**
  String get planDetailSprintModeExam;

  /// No description provided for @planDetailSprintModeLabel.
  ///
  /// In zh, this message translates to:
  /// **'考前冲刺模式'**
  String get planDetailSprintModeLabel;

  /// No description provided for @planDetailSprintNodesLoading.
  ///
  /// In zh, this message translates to:
  /// **'冲刺节点还在整理中。'**
  String get planDetailSprintNodesLoading;

  /// No description provided for @planDetailSprintPackDesc.
  ///
  /// In zh, this message translates to:
  /// **'今天先把这些高收益节点接稳，任务完成后对应圆点会点亮。'**
  String get planDetailSprintPackDesc;

  /// No description provided for @planDetailSprintPackNodes.
  ///
  /// In zh, this message translates to:
  /// **'Sprint Pack 节点'**
  String get planDetailSprintPackNodes;

  /// No description provided for @planDetailStatusAbandoned.
  ///
  /// In zh, this message translates to:
  /// **'已放弃'**
  String get planDetailStatusAbandoned;

  /// No description provided for @planDetailStatusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get planDetailStatusCompleted;

  /// No description provided for @planDetailStatusInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get planDetailStatusInProgress;

  /// No description provided for @planDetailStatusPending.
  ///
  /// In zh, this message translates to:
  /// **'待开始'**
  String get planDetailStatusPending;

  /// No description provided for @planDetailStatusStuck.
  ///
  /// In zh, this message translates to:
  /// **'卡住了'**
  String get planDetailStatusStuck;

  /// No description provided for @planDetailTaskBlueprint.
  ///
  /// In zh, this message translates to:
  /// **'任务编排'**
  String get planDetailTaskBlueprint;

  /// No description provided for @planDetailTaskCount.
  ///
  /// In zh, this message translates to:
  /// **'{completed}/{total} 任务'**
  String planDetailTaskCount(Object completed, Object total);

  /// No description provided for @planDetailTaskDifficulty.
  ///
  /// In zh, this message translates to:
  /// **'难度 {difficulty}'**
  String planDetailTaskDifficulty(Object difficulty);

  /// No description provided for @planDetailTagErrorRepair.
  ///
  /// In zh, this message translates to:
  /// **'错题补强'**
  String get planDetailTagErrorRepair;

  /// No description provided for @planDetailTagNoNewContent.
  ///
  /// In zh, this message translates to:
  /// **'不学新内容'**
  String get planDetailTagNoNewContent;

  /// No description provided for @planDetailThingCount1.
  ///
  /// In zh, this message translates to:
  /// **'这 1 件事'**
  String get planDetailThingCount1;

  /// No description provided for @planDetailThingCountN.
  ///
  /// In zh, this message translates to:
  /// **'这 {count} 件事'**
  String planDetailThingCountN(Object count);

  /// No description provided for @planDetailTodayFocus.
  ///
  /// In zh, this message translates to:
  /// **'今日聚焦'**
  String get planDetailTodayFocus;

  /// No description provided for @planDetailSprintFocus.
  ///
  /// In zh, this message translates to:
  /// **'冲刺聚焦'**
  String get planDetailSprintFocus;

  /// No description provided for @planDetailWhyNowErrorFix.
  ///
  /// In zh, this message translates to:
  /// **'现在修这个错因，能避免后面的任务被同一个漏洞反复拖住。'**
  String get planDetailWhyNowErrorFix;

  /// No description provided for @planDetailWhyNowLearning.
  ///
  /// In zh, this message translates to:
  /// **'现在先处理它，是为了把今天的学习推进变成一个看得见的输出。'**
  String get planDetailWhyNowLearning;

  /// No description provided for @planDetailWhyNowOcr.
  ///
  /// In zh, this message translates to:
  /// **'现在处理资料，能先把可用信息变成后续任务的入口。'**
  String get planDetailWhyNowOcr;

  /// No description provided for @planDetailWhyNowPlanning.
  ///
  /// In zh, this message translates to:
  /// **'现在整理计划，能让下一步执行少一点犹豫。'**
  String get planDetailWhyNowPlanning;

  /// No description provided for @planDetailWhyNowReflection.
  ///
  /// In zh, this message translates to:
  /// **'现在复盘，能把今天的结果转成明天更轻的选择。'**
  String get planDetailWhyNowReflection;

  /// No description provided for @planDetailWhyNowSocial.
  ///
  /// In zh, this message translates to:
  /// **'现在完成协作动作，能让外部反馈及时接进你的学习节奏。'**
  String get planDetailWhyNowSocial;

  /// No description provided for @planDetailWhyNowTraining.
  ///
  /// In zh, this message translates to:
  /// **'现在做练习，能尽快确认刚学的内容是不是真的会用。'**
  String get planDetailWhyNowTraining;

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

  /// No description provided for @taskConfirmCompleteTitle.
  ///
  /// In zh, this message translates to:
  /// **'确认完成任务？'**
  String get taskConfirmCompleteTitle;

  /// No description provided for @taskConfirmCompleteBody.
  ///
  /// In zh, this message translates to:
  /// **'将「{title}」标记为已完成。'**
  String taskConfirmCompleteBody(Object title);

  /// No description provided for @taskEstimatedMinutesValue.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String taskEstimatedMinutesValue(Object minutes);

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

  /// No description provided for @taskExecutionFreeFocusCompleted.
  ///
  /// In zh, this message translates to:
  /// **'自由专注已完成'**
  String get taskExecutionFreeFocusCompleted;

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

  /// No description provided for @taskDetailNoteSection.
  ///
  /// In zh, this message translates to:
  /// **'任务说明'**
  String get taskDetailNoteSection;

  /// No description provided for @taskDetailSubtasks.
  ///
  /// In zh, this message translates to:
  /// **'子任务 ({completed}/{total})'**
  String taskDetailSubtasks(Object completed, Object total);

  /// No description provided for @taskDetailSubtaskLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'子任务加载失败：{error}'**
  String taskDetailSubtaskLoadFailed(Object error);

  /// No description provided for @taskDetailAiExpansionTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 拓展相关节点'**
  String get taskDetailAiExpansionTitle;

  /// No description provided for @taskDetailAiExpansionDescription.
  ///
  /// In zh, this message translates to:
  /// **'基于当前节点生成 3 个候选相关节点。你可以不选，也可以任选 1 到 3 个真正写入知识星图。'**
  String get taskDetailAiExpansionDescription;

  /// No description provided for @taskDetailGenerateCandidates.
  ///
  /// In zh, this message translates to:
  /// **'生成候选节点'**
  String get taskDetailGenerateCandidates;

  /// No description provided for @taskDetailUnknownNode.
  ///
  /// In zh, this message translates to:
  /// **'未知节点'**
  String get taskDetailUnknownNode;

  /// No description provided for @taskDetailNodeCleanedUp.
  ///
  /// In zh, this message translates to:
  /// **'这个节点已被清理，星图会在下次刷新后同步。'**
  String get taskDetailNodeCleanedUp;

  /// No description provided for @taskDetailRecentLearningPath.
  ///
  /// In zh, this message translates to:
  /// **'最近生成的学习路径'**
  String get taskDetailRecentLearningPath;

  /// No description provided for @taskDetailLightweightPath.
  ///
  /// In zh, this message translates to:
  /// **'当前为轻量任务路径，不占用计划额度。'**
  String get taskDetailLightweightPath;

  /// No description provided for @taskDetailFullPath.
  ///
  /// In zh, this message translates to:
  /// **'当前为完整学习计划路径。'**
  String get taskDetailFullPath;

  /// No description provided for @taskDetailGeneratedTasks.
  ///
  /// In zh, this message translates to:
  /// **'已生成任务'**
  String get taskDetailGeneratedTasks;

  /// No description provided for @taskDetailPlanContext.
  ///
  /// In zh, this message translates to:
  /// **'所属计划'**
  String get taskDetailPlanContext;

  /// No description provided for @taskDetailPlanContextLoading.
  ///
  /// In zh, this message translates to:
  /// **'正在加载所属计划...'**
  String get taskDetailPlanContextLoading;

  /// No description provided for @taskDetailCopyAiPromptSuccess.
  ///
  /// In zh, this message translates to:
  /// **'AI 提示词已复制'**
  String get taskDetailCopyAiPromptSuccess;

  /// No description provided for @taskDetailGuideGenerated.
  ///
  /// In zh, this message translates to:
  /// **'任务指南已生成'**
  String get taskDetailGuideGenerated;

  /// No description provided for @taskDetailGuideGenerateFailed.
  ///
  /// In zh, this message translates to:
  /// **'生成失败: {error}'**
  String taskDetailGuideGenerateFailed(Object error);

  /// No description provided for @taskDetailRelationPrerequisite.
  ///
  /// In zh, this message translates to:
  /// **'前置'**
  String get taskDetailRelationPrerequisite;

  /// No description provided for @taskDetailRelationApplication.
  ///
  /// In zh, this message translates to:
  /// **'应用'**
  String get taskDetailRelationApplication;

  /// No description provided for @taskDetailRelationEvolution.
  ///
  /// In zh, this message translates to:
  /// **'进阶'**
  String get taskDetailRelationEvolution;

  /// No description provided for @taskDetailRelationRelated.
  ///
  /// In zh, this message translates to:
  /// **'相关'**
  String get taskDetailRelationRelated;

  /// No description provided for @taskDetailCandidatesProcessed.
  ///
  /// In zh, this message translates to:
  /// **'候选节点已处理。'**
  String get taskDetailCandidatesProcessed;

  /// No description provided for @taskDetailCandidatesApplied.
  ///
  /// In zh, this message translates to:
  /// **'已处理 {count} 个候选节点，新增 {created} 个，复用 {reused} 个已有节点。'**
  String taskDetailCandidatesApplied(
      Object count, Object created, Object reused);

  /// No description provided for @taskDetailCandidatesReused.
  ///
  /// In zh, this message translates to:
  /// **'已处理 {count} 个候选节点，复用 {reused} 个已有节点。'**
  String taskDetailCandidatesReused(Object count, Object reused);

  /// No description provided for @taskDetailCandidatesAccepted.
  ///
  /// In zh, this message translates to:
  /// **'已将 {count} 个节点纳入星图。'**
  String taskDetailCandidatesAccepted(Object count);

  /// No description provided for @taskDetailNodeExpansionDescription.
  ///
  /// In zh, this message translates to:
  /// **'围绕「{name}」生成 3 个候选节点，再由你决定哪些真正写入知识星图。'**
  String taskDetailNodeExpansionDescription(Object name);

  /// No description provided for @taskDetailGenerateThreeCandidates.
  ///
  /// In zh, this message translates to:
  /// **'生成 3 个候选节点'**
  String get taskDetailGenerateThreeCandidates;

  /// No description provided for @taskDetailSelectedCount.
  ///
  /// In zh, this message translates to:
  /// **'已选 {selected} / {total} 个候选节点'**
  String taskDetailSelectedCount(Object selected, Object total);

  /// No description provided for @taskDetailImportanceLevel.
  ///
  /// In zh, this message translates to:
  /// **'重要度 {level}'**
  String taskDetailImportanceLevel(Object level);

  /// No description provided for @taskDetailRegenerate.
  ///
  /// In zh, this message translates to:
  /// **'重新生成'**
  String get taskDetailRegenerate;

  /// No description provided for @taskDetailSkipAll.
  ///
  /// In zh, this message translates to:
  /// **'本次不纳入'**
  String get taskDetailSkipAll;

  /// No description provided for @taskDetailAcceptIntoGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'纳入星图（{count}）'**
  String taskDetailAcceptIntoGalaxy(Object count);

  /// No description provided for @taskDetailStepMinutesValue.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String taskDetailStepMinutesValue(Object minutes);

  /// No description provided for @taskDetailStepMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{minutes}分钟'**
  String taskDetailStepMinutes(Object minutes);

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

  /// No description provided for @languageDialogDescription.
  ///
  /// In zh, this message translates to:
  /// **'选择你更习惯的阅读与交互语言，界面与系统文案会一起切换。'**
  String get languageDialogDescription;

  /// No description provided for @languageChineseDescription.
  ///
  /// In zh, this message translates to:
  /// **'更适合中文阅读与本地化表达。'**
  String get languageChineseDescription;

  /// No description provided for @languageEnglishDescription.
  ///
  /// In zh, this message translates to:
  /// **'适合英文界面与更国际化的内容环境。'**
  String get languageEnglishDescription;

  /// No description provided for @learningModeSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'调整深度与好奇心偏好'**
  String get learningModeSubtitle;

  /// No description provided for @learningPreferenceSaving.
  ///
  /// In zh, this message translates to:
  /// **'保存中…'**
  String get learningPreferenceSaving;

  /// No description provided for @learningPreferenceSaved.
  ///
  /// In zh, this message translates to:
  /// **'学习模式偏好已保存'**
  String get learningPreferenceSaved;

  /// No description provided for @learningPreferenceSaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'保存失败：{error}'**
  String learningPreferenceSaveFailed(Object error);

  /// No description provided for @learningPreferenceAutoSaveHint.
  ///
  /// In zh, this message translates to:
  /// **'拖动后会自动保存到后端'**
  String get learningPreferenceAutoSaveHint;

  /// No description provided for @bgmVolume.
  ///
  /// In zh, this message translates to:
  /// **'音乐音量'**
  String get bgmVolume;

  /// No description provided for @bgmScenePreference.
  ///
  /// In zh, this message translates to:
  /// **'场景偏好'**
  String get bgmScenePreference;

  /// No description provided for @bgmPreviewTooltip.
  ///
  /// In zh, this message translates to:
  /// **'试听 {palette}'**
  String bgmPreviewTooltip(Object palette);

  /// No description provided for @bgmAdvancedControls.
  ///
  /// In zh, this message translates to:
  /// **'高级控制'**
  String get bgmAdvancedControls;

  /// No description provided for @bgmAdvancedControlsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制音乐浓度、轮换频率、阅读保护、专注优先与锁定当前风格'**
  String get bgmAdvancedControlsSubtitle;

  /// No description provided for @chatPureMode.
  ///
  /// In zh, this message translates to:
  /// **'纯净模式'**
  String get chatPureMode;

  /// No description provided for @chatPureModeSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'聊天中只保留文字消息，隐藏附加信息卡片与消息下方组件。'**
  String get chatPureModeSubtitle;

  /// No description provided for @motionIntensity.
  ///
  /// In zh, this message translates to:
  /// **'动效强度'**
  String get motionIntensity;

  /// No description provided for @aiUsagePanelUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'额度面板暂时不可用，但档位切换仍可正常生效。'**
  String get aiUsagePanelUnavailable;

  /// No description provided for @aiOpsPanelUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'运营面板暂时不可用，但 AI 档位和使用统计仍可继续使用。'**
  String get aiOpsPanelUnavailable;

  /// No description provided for @notificationManageSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'统一管理系统通知、干预通知、免打扰时段与任务提醒。'**
  String get notificationManageSubtitle;

  /// No description provided for @notificationLoadingPrefs.
  ///
  /// In zh, this message translates to:
  /// **'正在加载通知偏好...'**
  String get notificationLoadingPrefs;

  /// No description provided for @notificationSystem.
  ///
  /// In zh, this message translates to:
  /// **'系统通知'**
  String get notificationSystem;

  /// No description provided for @notificationSystemSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制任务提醒、成就、系统消息等站内通知'**
  String get notificationSystemSubtitle;

  /// No description provided for @notificationInterventions.
  ///
  /// In zh, this message translates to:
  /// **'干预通知'**
  String get notificationInterventions;

  /// No description provided for @notificationInterventionsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制教练/代理的干预和引导提醒'**
  String get notificationInterventionsSubtitle;

  /// No description provided for @notificationReminders.
  ///
  /// In zh, this message translates to:
  /// **'提醒'**
  String get notificationReminders;

  /// No description provided for @notificationRemindersSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制任务、计划进度和回归提醒'**
  String get notificationRemindersSubtitle;

  /// No description provided for @notificationSpacedRepetition.
  ///
  /// In zh, this message translates to:
  /// **'复习'**
  String get notificationSpacedRepetition;

  /// No description provided for @notificationSpacedRepetitionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制 Galaxy 间隔复习节点提醒'**
  String get notificationSpacedRepetitionSubtitle;

  /// No description provided for @notificationWeeklyReport.
  ///
  /// In zh, this message translates to:
  /// **'周报'**
  String get notificationWeeklyReport;

  /// No description provided for @notificationWeeklyReportSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制每周成长报告和学习摘要通知'**
  String get notificationWeeklyReportSubtitle;

  /// No description provided for @notificationMilestone.
  ///
  /// In zh, this message translates to:
  /// **'里程碑'**
  String get notificationMilestone;

  /// No description provided for @notificationMilestoneSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'控制成就、阶段达成和进度里程碑通知'**
  String get notificationMilestoneSubtitle;

  /// No description provided for @notificationLevel.
  ///
  /// In zh, this message translates to:
  /// **'通知级别'**
  String get notificationLevel;

  /// No description provided for @notificationLevelSwitched.
  ///
  /// In zh, this message translates to:
  /// **'通知级别已切换为{level}'**
  String notificationLevelSwitched(Object level);

  /// No description provided for @notificationLevelMinimal.
  ///
  /// In zh, this message translates to:
  /// **'简洁'**
  String get notificationLevelMinimal;

  /// No description provided for @notificationLevelStandard.
  ///
  /// In zh, this message translates to:
  /// **'标准'**
  String get notificationLevelStandard;

  /// No description provided for @notificationLevelVerbose.
  ///
  /// In zh, this message translates to:
  /// **'详细'**
  String get notificationLevelVerbose;

  /// No description provided for @notificationLevelMinimalDesc.
  ///
  /// In zh, this message translates to:
  /// **'只保留最必要的提醒，减少打扰。'**
  String get notificationLevelMinimalDesc;

  /// No description provided for @notificationLevelStandardDesc.
  ///
  /// In zh, this message translates to:
  /// **'在信息量和打扰频率之间保持平衡。'**
  String get notificationLevelStandardDesc;

  /// No description provided for @notificationLevelVerboseDesc.
  ///
  /// In zh, this message translates to:
  /// **'展示更完整的背景信息和提醒内容。'**
  String get notificationLevelVerboseDesc;

  /// No description provided for @notificationLevelMinimalPreview.
  ///
  /// In zh, this message translates to:
  /// **'只保留关键提醒，例如任务即将到期、需要立即处理的系统通知。'**
  String get notificationLevelMinimalPreview;

  /// No description provided for @notificationLevelStandardPreview.
  ///
  /// In zh, this message translates to:
  /// **'保留主要提醒，并在必要时补充简短背景说明，适合大多数场景。'**
  String get notificationLevelStandardPreview;

  /// No description provided for @notificationLevelVerbosePreview.
  ///
  /// In zh, this message translates to:
  /// **'会附带更多上下文，例如为什么提醒你、下一步建议和补充说明。'**
  String get notificationLevelVerbosePreview;

  /// No description provided for @notificationLevelPreviewTitle.
  ///
  /// In zh, this message translates to:
  /// **'{level}通知'**
  String notificationLevelPreviewTitle(Object level);

  /// No description provided for @notificationQuietHours.
  ///
  /// In zh, this message translates to:
  /// **'免打扰时段'**
  String get notificationQuietHours;

  /// No description provided for @notificationQuietHoursSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'关闭后，系统会按正常节奏推送通知'**
  String get notificationQuietHoursSubtitle;

  /// No description provided for @notificationQuietHoursStart.
  ///
  /// In zh, this message translates to:
  /// **'开始时间'**
  String get notificationQuietHoursStart;

  /// No description provided for @notificationQuietHoursEnd.
  ///
  /// In zh, this message translates to:
  /// **'结束时间'**
  String get notificationQuietHoursEnd;

  /// No description provided for @notificationQuietHoursHint.
  ///
  /// In zh, this message translates to:
  /// **'支持跨午夜，例如 22:00 - 08:00；开始和结束时间不能相同。'**
  String get notificationQuietHoursHint;

  /// No description provided for @notificationQuietHoursSameTimeError.
  ///
  /// In zh, this message translates to:
  /// **'开始和结束时间不能相同'**
  String get notificationQuietHoursSameTimeError;

  /// No description provided for @notificationQuietHoursStartUpdated.
  ///
  /// In zh, this message translates to:
  /// **'免打扰开始时间已更新'**
  String get notificationQuietHoursStartUpdated;

  /// No description provided for @notificationQuietHoursEndUpdated.
  ///
  /// In zh, this message translates to:
  /// **'免打扰结束时间已更新'**
  String get notificationQuietHoursEndUpdated;

  /// No description provided for @notificationUpdateFailed.
  ///
  /// In zh, this message translates to:
  /// **'通知设置更新失败：{error}'**
  String notificationUpdateFailed(Object error);

  /// No description provided for @aiExecutionEngine.
  ///
  /// In zh, this message translates to:
  /// **'AI执行引擎'**
  String get aiExecutionEngine;

  /// No description provided for @aiExecutionEngineSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'连接你的 OpenClaw 实例并监控健康状态'**
  String get aiExecutionEngineSubtitle;

  /// No description provided for @capsuleGenerated.
  ///
  /// In zh, this message translates to:
  /// **'新的好奇心胶囊已生成'**
  String get capsuleGenerated;

  /// No description provided for @capsuleGeneratedEmpty.
  ///
  /// In zh, this message translates to:
  /// **'已生成新的胶囊，点击下方即可查看完整内容。'**
  String get capsuleGeneratedEmpty;

  /// No description provided for @capsuleViewNew.
  ///
  /// In zh, this message translates to:
  /// **'查看新胶囊'**
  String get capsuleViewNew;

  /// No description provided for @capsulePreviewFailed.
  ///
  /// In zh, this message translates to:
  /// **'试听失败，请检查音频文件'**
  String get capsulePreviewFailed;

  /// No description provided for @capsuleScenePreviewFailed.
  ///
  /// In zh, this message translates to:
  /// **'当前场景试听失败，请检查音频文件'**
  String get capsuleScenePreviewFailed;

  /// No description provided for @aiReasoningModeSwitched.
  ///
  /// In zh, this message translates to:
  /// **'AI 推理模式已切换为{mode}'**
  String aiReasoningModeSwitched(Object mode);

  /// No description provided for @aiReasoningModeSwitchFailed.
  ///
  /// In zh, this message translates to:
  /// **'AI 推理模式切换失败，请稍后重试'**
  String get aiReasoningModeSwitchFailed;

  /// No description provided for @aiReasoningFastDesc.
  ///
  /// In zh, this message translates to:
  /// **'优先更快给出结果，适合短问答、轻量查询和低延迟场景。'**
  String get aiReasoningFastDesc;

  /// No description provided for @aiReasoningBalancedDesc.
  ///
  /// In zh, this message translates to:
  /// **'在速度和推理深度之间保持平衡，适合大多数日常使用。'**
  String get aiReasoningBalancedDesc;

  /// No description provided for @aiReasoningDeepDesc.
  ///
  /// In zh, this message translates to:
  /// **'会投入更多推理预算，适合复杂问题、规划和高精度解释。'**
  String get aiReasoningDeepDesc;

  /// No description provided for @taskReminderDisabled.
  ///
  /// In zh, this message translates to:
  /// **'已关闭'**
  String get taskReminderDisabled;

  /// No description provided for @taskReminderEnabledNoTime.
  ///
  /// In zh, this message translates to:
  /// **'已开启，但暂未选择提醒时间'**
  String get taskReminderEnabledNoTime;

  /// No description provided for @taskReminderEnabledWithTimes.
  ///
  /// In zh, this message translates to:
  /// **'已开启'**
  String get taskReminderEnabledWithTimes;

  /// No description provided for @taskReminderDaysAgo.
  ///
  /// In zh, this message translates to:
  /// **'{days}天前'**
  String taskReminderDaysAgo(Object days);

  /// No description provided for @taskReminderHoursAgo.
  ///
  /// In zh, this message translates to:
  /// **'{hours}小时前'**
  String taskReminderHoursAgo(Object hours);

  /// No description provided for @taskReminderMinutesAgo.
  ///
  /// In zh, this message translates to:
  /// **'{minutes}分钟前'**
  String taskReminderMinutesAgo(Object minutes);

  /// No description provided for @notificationPermissionDeniedTitle.
  ///
  /// In zh, this message translates to:
  /// **'未授权: {error}'**
  String notificationPermissionDeniedTitle(Object error);

  /// No description provided for @notificationRequestPermission.
  ///
  /// In zh, this message translates to:
  /// **'请求权限'**
  String get notificationRequestPermission;

  /// No description provided for @notificationOpenSettings.
  ///
  /// In zh, this message translates to:
  /// **'打开设置'**
  String get notificationOpenSettings;

  /// No description provided for @notificationPermissionDialogTitle.
  ///
  /// In zh, this message translates to:
  /// **'通知权限状态'**
  String get notificationPermissionDialogTitle;

  /// No description provided for @notificationPermissionDialogContent.
  ///
  /// In zh, this message translates to:
  /// **'通知权限被拒绝，请在系统设置中开启'**
  String get notificationPermissionDialogContent;

  /// No description provided for @bgmPaletteAdaptive.
  ///
  /// In zh, this message translates to:
  /// **'自适应'**
  String get bgmPaletteAdaptive;

  /// No description provided for @bgmPaletteClassical.
  ///
  /// In zh, this message translates to:
  /// **'精选古典'**
  String get bgmPaletteClassical;

  /// No description provided for @bgmPalettePiano.
  ///
  /// In zh, this message translates to:
  /// **'钢琴优先'**
  String get bgmPalettePiano;

  /// No description provided for @bgmPaletteAiry.
  ///
  /// In zh, this message translates to:
  /// **'空灵氛围'**
  String get bgmPaletteAiry;

  /// No description provided for @bgmPaletteWarm.
  ///
  /// In zh, this message translates to:
  /// **'温暖轻快'**
  String get bgmPaletteWarm;

  /// No description provided for @bgmPaletteAdaptiveDesc.
  ///
  /// In zh, this message translates to:
  /// **'系统会按页面功能自动挑选最合适的背景音乐。'**
  String get bgmPaletteAdaptiveDesc;

  /// No description provided for @bgmPaletteClassicalDesc.
  ///
  /// In zh, this message translates to:
  /// **'精选古典钢琴与弦乐，会优先使用你本机准备的古典乐库做场景切换。'**
  String get bgmPaletteClassicalDesc;

  /// No description provided for @bgmPalettePianoDesc.
  ///
  /// In zh, this message translates to:
  /// **'整体更偏轻钢琴与安静旋律，适合长时间陪伴。'**
  String get bgmPalettePianoDesc;

  /// No description provided for @bgmPaletteAiryDesc.
  ///
  /// In zh, this message translates to:
  /// **'整体更偏空灵、梦幻和空间感更强的氛围。'**
  String get bgmPaletteAiryDesc;

  /// No description provided for @bgmPaletteWarmDesc.
  ///
  /// In zh, this message translates to:
  /// **'整体更偏温暖、柔和、有人味的轻快底色。'**
  String get bgmPaletteWarmDesc;

  /// No description provided for @bgmIntensityGentle.
  ///
  /// In zh, this message translates to:
  /// **'柔和'**
  String get bgmIntensityGentle;

  /// No description provided for @bgmIntensityBalanced.
  ///
  /// In zh, this message translates to:
  /// **'平衡'**
  String get bgmIntensityBalanced;

  /// No description provided for @bgmIntensityLush.
  ///
  /// In zh, this message translates to:
  /// **'丰盈'**
  String get bgmIntensityLush;

  /// No description provided for @bgmIntensityGentleDesc.
  ///
  /// In zh, this message translates to:
  /// **'更适合长时间陪伴，优先轻密度、低干扰和慢切换。'**
  String get bgmIntensityGentleDesc;

  /// No description provided for @bgmIntensityBalancedDesc.
  ///
  /// In zh, this message translates to:
  /// **'保留舒适度的同时增加一点层次和存在感。'**
  String get bgmIntensityBalancedDesc;

  /// No description provided for @bgmIntensityLushDesc.
  ///
  /// In zh, this message translates to:
  /// **'让同一场景更有氛围和包裹感，但仍避免明显突兀。'**
  String get bgmIntensityLushDesc;

  /// No description provided for @bgmVarietySteady.
  ///
  /// In zh, this message translates to:
  /// **'稳定'**
  String get bgmVarietySteady;

  /// No description provided for @bgmVarietyBalanced.
  ///
  /// In zh, this message translates to:
  /// **'均衡'**
  String get bgmVarietyBalanced;

  /// No description provided for @bgmVarietyDynamic.
  ///
  /// In zh, this message translates to:
  /// **'灵动'**
  String get bgmVarietyDynamic;

  /// No description provided for @bgmVarietySteadyDesc.
  ///
  /// In zh, this message translates to:
  /// **'尽量减少跳曲和重复变化，让氛围更连贯。'**
  String get bgmVarietySteadyDesc;

  /// No description provided for @bgmVarietyBalancedDesc.
  ///
  /// In zh, this message translates to:
  /// **'在连贯和新鲜之间保持中间值。'**
  String get bgmVarietyBalancedDesc;

  /// No description provided for @bgmVarietyDynamicDesc.
  ///
  /// In zh, this message translates to:
  /// **'降低重复率，让同类页面也能更常听到新变化。'**
  String get bgmVarietyDynamicDesc;

  /// No description provided for @bgmModeAdaptive.
  ///
  /// In zh, this message translates to:
  /// **'跟随页面'**
  String get bgmModeAdaptive;

  /// No description provided for @bgmModeContinuous.
  ///
  /// In zh, this message translates to:
  /// **'播放器模式'**
  String get bgmModeContinuous;

  /// No description provided for @bgmModeFocusOnly.
  ///
  /// In zh, this message translates to:
  /// **'仅专注开启'**
  String get bgmModeFocusOnly;

  /// No description provided for @bgmModeSilent.
  ///
  /// In zh, this message translates to:
  /// **'全局静音'**
  String get bgmModeSilent;

  /// No description provided for @bgmModeAdaptiveDesc.
  ///
  /// In zh, this message translates to:
  /// **'首页、聊天、任务、成就等页面会自动切换到对应氛围音乐。'**
  String get bgmModeAdaptiveDesc;

  /// No description provided for @bgmModeContinuousDesc.
  ///
  /// In zh, this message translates to:
  /// **'当前曲目会持续播放，不会因为你跳转到别的页面而被打断，适合把 App 当成舒缓音乐播放器。'**
  String get bgmModeContinuousDesc;

  /// No description provided for @bgmModeFocusOnlyDesc.
  ///
  /// In zh, this message translates to:
  /// **'只有专注开始、沉浸和执行任务时才会播放背景音乐，日常页面保持安静。'**
  String get bgmModeFocusOnlyDesc;

  /// No description provided for @bgmModeSilentDesc.
  ///
  /// In zh, this message translates to:
  /// **'保留音效和触感反馈，但所有背景音乐都不会自动播放。'**
  String get bgmModeSilentDesc;

  /// No description provided for @motionIntensityUltra.
  ///
  /// In zh, this message translates to:
  /// **'超强'**
  String get motionIntensityUltra;

  /// No description provided for @motionIntensityHigh.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get motionIntensityHigh;

  /// No description provided for @motionIntensityMedium.
  ///
  /// In zh, this message translates to:
  /// **'中'**
  String get motionIntensityMedium;

  /// No description provided for @motionIntensityOff.
  ///
  /// In zh, this message translates to:
  /// **'关闭'**
  String get motionIntensityOff;

  /// No description provided for @motionIntensityUltraDesc.
  ///
  /// In zh, this message translates to:
  /// **'保留完整粒子、辉光与复杂动效，适合高性能设备。'**
  String get motionIntensityUltraDesc;

  /// No description provided for @motionIntensityHighDesc.
  ///
  /// In zh, this message translates to:
  /// **'维持大部分视觉层，同时允许系统按帧率自动降级。'**
  String get motionIntensityHighDesc;

  /// No description provided for @motionIntensityMediumDesc.
  ///
  /// In zh, this message translates to:
  /// **'收敛粒子与辉光，优先稳定和省电，仍保留基础层次感。'**
  String get motionIntensityMediumDesc;

  /// No description provided for @motionIntensityOffDesc.
  ///
  /// In zh, this message translates to:
  /// **'尽量关闭强动效与粒子层，适合偏静态、低刺激或低性能场景。'**
  String get motionIntensityOffDesc;

  /// No description provided for @bgmSectionSubtitleDefault.
  ///
  /// In zh, this message translates to:
  /// **'按页面与播放器模式管理背景音乐'**
  String get bgmSectionSubtitleDefault;

  /// No description provided for @bgmSectionSubtitleWithCount.
  ///
  /// In zh, this message translates to:
  /// **'当前共 {count} 首，可在页面策略和播放器模式之间自由切换'**
  String bgmSectionSubtitleWithCount(Object count);

  /// No description provided for @bgmLibraryUpdated.
  ///
  /// In zh, this message translates to:
  /// **'曲库已更新为 {count} 首'**
  String bgmLibraryUpdated(Object count);

  /// No description provided for @bgmOpenLibrary.
  ///
  /// In zh, this message translates to:
  /// **'打开曲库'**
  String get bgmOpenLibrary;

  /// No description provided for @bgmCurated.
  ///
  /// In zh, this message translates to:
  /// **'精选'**
  String get bgmCurated;

  /// No description provided for @bgmImported.
  ///
  /// In zh, this message translates to:
  /// **'本地导入'**
  String get bgmImported;

  /// No description provided for @bgmBundled.
  ///
  /// In zh, this message translates to:
  /// **'系统兜底'**
  String get bgmBundled;

  /// No description provided for @bgmModeLabel.
  ///
  /// In zh, this message translates to:
  /// **'模式'**
  String get bgmModeLabel;

  /// No description provided for @bgmPlayerMode.
  ///
  /// In zh, this message translates to:
  /// **'播放器模式'**
  String get bgmPlayerMode;

  /// No description provided for @bgmPageStrategyMode.
  ///
  /// In zh, this message translates to:
  /// **'页面策略模式'**
  String get bgmPageStrategyMode;

  /// No description provided for @bgmLibraryHint.
  ///
  /// In zh, this message translates to:
  /// **'新页面里可以点播曲库、导入自己的音乐，并启用「播放器模式」让 BGM 跨页面持续不中断。'**
  String get bgmLibraryHint;

  /// No description provided for @bgmNotPlaying.
  ///
  /// In zh, this message translates to:
  /// **'当前未播放'**
  String get bgmNotPlaying;

  /// No description provided for @bgmBundledTrack.
  ///
  /// In zh, this message translates to:
  /// **'内置场景曲目'**
  String get bgmBundledTrack;

  /// No description provided for @bgmWaitingPlayback.
  ///
  /// In zh, this message translates to:
  /// **'等待播放信息'**
  String get bgmWaitingPlayback;

  /// No description provided for @bgmDisabled.
  ///
  /// In zh, this message translates to:
  /// **'背景音乐已关闭'**
  String get bgmDisabled;

  /// No description provided for @bgmGlobalSilent.
  ///
  /// In zh, this message translates to:
  /// **'当前处于全局静音'**
  String get bgmGlobalSilent;

  /// No description provided for @bgmContinuousPlaying.
  ///
  /// In zh, this message translates to:
  /// **'播放器模式持续播放中'**
  String get bgmContinuousPlaying;

  /// No description provided for @bgmNowPlaying.
  ///
  /// In zh, this message translates to:
  /// **'当前播放'**
  String get bgmNowPlaying;

  /// No description provided for @bgmPreviewCurrentScene.
  ///
  /// In zh, this message translates to:
  /// **'试听当前场景'**
  String get bgmPreviewCurrentScene;

  /// No description provided for @bgmTrackLabel.
  ///
  /// In zh, this message translates to:
  /// **'曲目: {name}'**
  String bgmTrackLabel(Object name);

  /// No description provided for @bgmSourceLabel.
  ///
  /// In zh, this message translates to:
  /// **'来源: {label}'**
  String bgmSourceLabel(Object label);

  /// No description provided for @bgmIntensityLabel.
  ///
  /// In zh, this message translates to:
  /// **'强度'**
  String get bgmIntensityLabel;

  /// No description provided for @bgmVarietyLabel.
  ///
  /// In zh, this message translates to:
  /// **'轮换'**
  String get bgmVarietyLabel;

  /// No description provided for @bgmReadingProtection.
  ///
  /// In zh, this message translates to:
  /// **'阅读保护'**
  String get bgmReadingProtection;

  /// No description provided for @bgmFocusPriority.
  ///
  /// In zh, this message translates to:
  /// **'专注优先'**
  String get bgmFocusPriority;

  /// No description provided for @bgmStyleLocked.
  ///
  /// In zh, this message translates to:
  /// **'锁定风格'**
  String get bgmStyleLocked;

  /// No description provided for @bgmReadingProtectionTitle.
  ///
  /// In zh, this message translates to:
  /// **'阅读保护'**
  String get bgmReadingProtectionTitle;

  /// No description provided for @bgmReadingProtectionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'聊天、洞察、个人页优先保留低刺激与轻混音'**
  String get bgmReadingProtectionSubtitle;

  /// No description provided for @bgmFocusPriorityTitle.
  ///
  /// In zh, this message translates to:
  /// **'专注优先'**
  String get bgmFocusPriorityTitle;

  /// No description provided for @bgmFocusPrioritySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'专注与执行阶段优先选择更纯净、更稳定的曲目'**
  String get bgmFocusPrioritySubtitle;

  /// No description provided for @bgmLockStyleTitle.
  ///
  /// In zh, this message translates to:
  /// **'锁定当前风格'**
  String get bgmLockStyleTitle;

  /// No description provided for @bgmLockStyleSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'跨普通页面时尽量延续当前气质，不覆盖专注和庆祝场景'**
  String get bgmLockStyleSubtitle;

  /// No description provided for @bgmAtmosphereIntensity.
  ///
  /// In zh, this message translates to:
  /// **'氛围强度'**
  String get bgmAtmosphereIntensity;

  /// No description provided for @bgmVarietyFrequency.
  ///
  /// In zh, this message translates to:
  /// **'曲目变化频率'**
  String get bgmVarietyFrequency;

  /// No description provided for @aiUsageTodayPreparing.
  ///
  /// In zh, this message translates to:
  /// **'今日额度统计准备中。'**
  String get aiUsageTodayPreparing;

  /// No description provided for @aiUsageTodayTitle.
  ///
  /// In zh, this message translates to:
  /// **'今日 AI 额度与消耗'**
  String get aiUsageTodayTitle;

  /// No description provided for @aiUsageRequests.
  ///
  /// In zh, this message translates to:
  /// **'{used}/{limit} 次'**
  String aiUsageRequests(Object used, Object limit);

  /// No description provided for @aiUsageLatency.
  ///
  /// In zh, this message translates to:
  /// **'平均首 token {firstToken}ms · 平均总耗时 {totalMs}ms'**
  String aiUsageLatency(Object firstToken, Object totalMs);

  /// No description provided for @aiOpsModesAccumulating.
  ///
  /// In zh, this message translates to:
  /// **'模式级运营指标还在累积中。'**
  String get aiOpsModesAccumulating;

  /// No description provided for @aiOpsTopChatModeStandard.
  ///
  /// In zh, this message translates to:
  /// **'标准对话'**
  String get aiOpsTopChatModeStandard;

  /// No description provided for @aiOpsTopChatModeStudyPlan.
  ///
  /// In zh, this message translates to:
  /// **'学习规划'**
  String get aiOpsTopChatModeStudyPlan;

  /// No description provided for @aiOpsTopChatModeDeepAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'深度分析'**
  String get aiOpsTopChatModeDeepAnalysis;

  /// No description provided for @aiOpsTopChatModeErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'诊断纠错'**
  String get aiOpsTopChatModeErrorDiagnosis;

  /// No description provided for @aiOpsTopChatModeExpertAuto.
  ///
  /// In zh, this message translates to:
  /// **'专家协作'**
  String get aiOpsTopChatModeExpertAuto;

  /// No description provided for @aiOpsUserViewTitle.
  ///
  /// In zh, this message translates to:
  /// **'用户视角'**
  String get aiOpsUserViewTitle;

  /// No description provided for @aiOpsUserViewDesc.
  ///
  /// In zh, this message translates to:
  /// **'重点看 AI 是否回得快、够稳、能把建议真正推成执行，而不是只看模型层参数。'**
  String get aiOpsUserViewDesc;

  /// No description provided for @aiOpsSuccessRate.
  ///
  /// In zh, this message translates to:
  /// **'成功率'**
  String get aiOpsSuccessRate;

  /// No description provided for @aiOpsAvgFirstToken.
  ///
  /// In zh, this message translates to:
  /// **'平均首包'**
  String get aiOpsAvgFirstToken;

  /// No description provided for @aiOpsAvgTotalDuration.
  ///
  /// In zh, this message translates to:
  /// **'平均总耗时'**
  String get aiOpsAvgTotalDuration;

  /// No description provided for @aiOpsExecutionConversion.
  ///
  /// In zh, this message translates to:
  /// **'执行转化'**
  String get aiOpsExecutionConversion;

  /// No description provided for @aiOpsPredictedAcceptExec.
  ///
  /// In zh, this message translates to:
  /// **'预测接受后执行'**
  String get aiOpsPredictedAcceptExec;

  /// No description provided for @aiOpsTopModeSummary.
  ///
  /// In zh, this message translates to:
  /// **'最近最常用的是「{topMode}」这条链，说明它已经是用户日常体验里的主力工作流。'**
  String aiOpsTopModeSummary(Object topMode);

  /// No description provided for @aiOpsDevViewTitle.
  ///
  /// In zh, this message translates to:
  /// **'开发运营视角'**
  String get aiOpsDevViewTitle;

  /// No description provided for @aiOpsDevViewDesc.
  ///
  /// In zh, this message translates to:
  /// **'这里专门看速度、成本、fallback 和预测转化，用来决定下一轮要优化哪条模式链。'**
  String get aiOpsDevViewDesc;

  /// No description provided for @aiOpsMonitoringModes.
  ///
  /// In zh, this message translates to:
  /// **'监控模式'**
  String get aiOpsMonitoringModes;

  /// No description provided for @aiOpsTotalRequests.
  ///
  /// In zh, this message translates to:
  /// **'请求总量'**
  String get aiOpsTotalRequests;

  /// No description provided for @aiOpsFallback.
  ///
  /// In zh, this message translates to:
  /// **'fallback'**
  String get aiOpsFallback;

  /// No description provided for @aiOpsTotalCost.
  ///
  /// In zh, this message translates to:
  /// **'总成本'**
  String get aiOpsTotalCost;

  /// No description provided for @aiOpsPromptHit.
  ///
  /// In zh, this message translates to:
  /// **'prompt 命中'**
  String get aiOpsPromptHit;

  /// No description provided for @aiOpsInferenceHit.
  ///
  /// In zh, this message translates to:
  /// **'推理命中'**
  String get aiOpsInferenceHit;

  /// No description provided for @aiOpsPredictionSummary.
  ///
  /// In zh, this message translates to:
  /// **'近 {days} 天里，当前最值得继续盯的预测动作是「{topAction}」；同时 prompt / inference 命中率分别是 {promptUtil}%/{inferenceUtil}%。'**
  String aiOpsPredictionSummary(
      Object days, Object topAction, Object promptUtil, Object inferenceUtil);

  /// No description provided for @aiOpsOpenAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'打开 AI 运营分析页'**
  String get aiOpsOpenAnalysis;

  /// No description provided for @aiOpsOpenAdminPanel.
  ///
  /// In zh, this message translates to:
  /// **'打开管理员运营面板'**
  String get aiOpsOpenAdminPanel;

  /// No description provided for @memoryDeclaration.
  ///
  /// In zh, this message translates to:
  /// **'声明'**
  String get memoryDeclaration;

  /// No description provided for @memoryEvidenceToken.
  ///
  /// In zh, this message translates to:
  /// **'证据 Token'**
  String get memoryEvidenceToken;

  /// No description provided for @memoryDecayPolicy.
  ///
  /// In zh, this message translates to:
  /// **'衰减策略'**
  String get memoryDecayPolicy;

  /// No description provided for @memoryUpdateValue.
  ///
  /// In zh, this message translates to:
  /// **'更新: {date}'**
  String memoryUpdateValue(Object date);

  /// No description provided for @memoryConfidenceValue.
  ///
  /// In zh, this message translates to:
  /// **'置信度: {value}'**
  String memoryConfidenceValue(Object value);

  /// No description provided for @memoryAllowedCaptureSummary.
  ///
  /// In zh, this message translates to:
  /// **'已允许捕获：{types}\n捕获级别：{level}'**
  String memoryAllowedCaptureSummary(Object types, Object level);

  /// No description provided for @memoryAiInferredDisabledHint.
  ///
  /// In zh, this message translates to:
  /// **'当前已关闭 AI 自动记忆，后续不会继续写入此类推断。'**
  String get memoryAiInferredDisabledHint;

  /// No description provided for @memoryExplanationInferredEpisodic.
  ///
  /// In zh, this message translates to:
  /// **'这条经历由 AI 从聊天中推断，并保留了证据 token、置信度与撤销路径。'**
  String get memoryExplanationInferredEpisodic;

  /// No description provided for @memoryCorrectionSubmittedWithAction.
  ///
  /// In zh, this message translates to:
  /// **'已提交纠错: {action}'**
  String memoryCorrectionSubmittedWithAction(Object action);

  /// No description provided for @memoryCorrectionFailedWithDetail.
  ///
  /// In zh, this message translates to:
  /// **'纠错失败: {error}'**
  String memoryCorrectionFailedWithDetail(Object error);

  /// No description provided for @tracksCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 首'**
  String tracksCount(Object count);

  /// No description provided for @profilePrestigeIdentity.
  ///
  /// In zh, this message translates to:
  /// **'荣耀身份'**
  String get profilePrestigeIdentity;

  /// No description provided for @profileNoTitleEquipped.
  ///
  /// In zh, this message translates to:
  /// **'未装备称号'**
  String get profileNoTitleEquipped;

  /// No description provided for @profileRecentHighlights.
  ///
  /// In zh, this message translates to:
  /// **'近期高光成就'**
  String get profileRecentHighlights;

  /// No description provided for @profileNoHighlightsHint.
  ///
  /// In zh, this message translates to:
  /// **'继续完成学习与冲刺，你的荣耀陈列柜会在这里逐步点亮。'**
  String get profileNoHighlightsHint;

  /// No description provided for @profileTraitQ1Title.
  ///
  /// In zh, this message translates to:
  /// **'开始新目标时，你更像哪种方式？'**
  String get profileTraitQ1Title;

  /// No description provided for @profileTraitQ1Structured.
  ///
  /// In zh, this message translates to:
  /// **'先搭结构再行动'**
  String get profileTraitQ1Structured;

  /// No description provided for @profileTraitQ1Mixed.
  ///
  /// In zh, this message translates to:
  /// **'先有框架，再边做边调'**
  String get profileTraitQ1Mixed;

  /// No description provided for @profileTraitQ1Explore.
  ///
  /// In zh, this message translates to:
  /// **'先试试看，让方向自己浮现'**
  String get profileTraitQ1Explore;

  /// No description provided for @profileTraitSkip.
  ///
  /// In zh, this message translates to:
  /// **'跳过'**
  String get profileTraitSkip;

  /// No description provided for @profileTraitQ2Title.
  ///
  /// In zh, this message translates to:
  /// **'遇到难题时，你更容易从哪里补能量？'**
  String get profileTraitQ2Title;

  /// No description provided for @profileTraitQ2Solo.
  ///
  /// In zh, this message translates to:
  /// **'先自己想清楚'**
  String get profileTraitQ2Solo;

  /// No description provided for @profileTraitQ2SmallGroup.
  ///
  /// In zh, this message translates to:
  /// **'找一两个人讨论'**
  String get profileTraitQ2SmallGroup;

  /// No description provided for @profileTraitQ2Group.
  ///
  /// In zh, this message translates to:
  /// **'边聊边想最有感觉'**
  String get profileTraitQ2Group;

  /// No description provided for @profileTraitQ3Title.
  ///
  /// In zh, this message translates to:
  /// **'当计划被打乱时，你通常最先出现什么反应？'**
  String get profileTraitQ3Title;

  /// No description provided for @profileTraitQ3Replan.
  ///
  /// In zh, this message translates to:
  /// **'马上重排，尽快回正'**
  String get profileTraitQ3Replan;

  /// No description provided for @profileTraitQ3Pause.
  ///
  /// In zh, this message translates to:
  /// **'会卡一下，但能慢慢拉回来'**
  String get profileTraitQ3Pause;

  /// No description provided for @profileTraitQ3Swing.
  ///
  /// In zh, this message translates to:
  /// **'情绪和节奏都会受影响'**
  String get profileTraitQ3Swing;

  /// No description provided for @profileLearningPortfolio.
  ///
  /// In zh, this message translates to:
  /// **'学习档案'**
  String get profileLearningPortfolio;

  /// No description provided for @profileLearningPortfolioSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'查看所有科目的冲刺历史、进行中与计划中记录'**
  String get profileLearningPortfolioSubtitle;

  /// No description provided for @profilePosterStudio.
  ///
  /// In zh, this message translates to:
  /// **'海报工坊'**
  String get profilePosterStudio;

  /// No description provided for @profilePosterStudioSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把成长、计划与灵感做成高质感分享海报'**
  String get profilePosterStudioSubtitle;

  /// No description provided for @profileMyWay.
  ///
  /// In zh, this message translates to:
  /// **'我的方式'**
  String get profileMyWay;

  /// No description provided for @profileMetacognitionPanel.
  ///
  /// In zh, this message translates to:
  /// **'自我认识面板'**
  String get profileMetacognitionPanel;

  /// No description provided for @profileMetacognitionHidden.
  ///
  /// In zh, this message translates to:
  /// **'已隐藏，后台仍会继续计算'**
  String get profileMetacognitionHidden;

  /// No description provided for @profileMetacognitionVisible.
  ///
  /// In zh, this message translates to:
  /// **'显示过去样本里的判断偏差摘要'**
  String get profileMetacognitionVisible;

  /// No description provided for @profileExportData.
  ///
  /// In zh, this message translates to:
  /// **'导出我的数据'**
  String get profileExportData;

  /// No description provided for @profileExportPreparing.
  ///
  /// In zh, this message translates to:
  /// **'正在准备数据，请稍候…'**
  String get profileExportPreparing;

  /// No description provided for @profileExportEmptyFile.
  ///
  /// In zh, this message translates to:
  /// **'空文件'**
  String get profileExportEmptyFile;

  /// No description provided for @profileExportShareSubject.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle 数据导出'**
  String get profileExportShareSubject;

  /// No description provided for @profileExportFailed.
  ///
  /// In zh, this message translates to:
  /// **'导出失败：{error}'**
  String profileExportFailed(Object error);

  /// No description provided for @profileSubtitleAchievements.
  ///
  /// In zh, this message translates to:
  /// **'查看已解锁的里程碑与荣誉进度'**
  String get profileSubtitleAchievements;

  /// No description provided for @profileSubtitleVisualElements.
  ///
  /// In zh, this message translates to:
  /// **'管理背景、粒子和视觉奖励'**
  String get profileSubtitleVisualElements;

  /// No description provided for @profileSubtitlePersona.
  ///
  /// In zh, this message translates to:
  /// **'查看系统理解到的学习特征与偏好'**
  String get profileSubtitlePersona;

  /// No description provided for @profileSubtitlePersonalInfo.
  ///
  /// In zh, this message translates to:
  /// **'编辑头像、昵称和基础资料'**
  String get profileSubtitlePersonalInfo;

  /// No description provided for @profileSubtitlePreferences.
  ///
  /// In zh, this message translates to:
  /// **'管理感官反馈、学习模式与推送偏好'**
  String get profileSubtitlePreferences;

  /// No description provided for @profileSubtitleMyWay.
  ///
  /// In zh, this message translates to:
  /// **'管理私有 Skill、共享与匿名 fork'**
  String get profileSubtitleMyWay;

  /// No description provided for @profileSubtitleSecurity.
  ///
  /// In zh, this message translates to:
  /// **'查看安全信息、设备与隐私控制'**
  String get profileSubtitleSecurity;

  /// No description provided for @profileSubtitleMemory.
  ///
  /// In zh, this message translates to:
  /// **'调整长期记忆与上下文保留策略'**
  String get profileSubtitleMemory;

  /// No description provided for @profileSubtitleLogout.
  ///
  /// In zh, this message translates to:
  /// **'安全退出当前账号'**
  String get profileSubtitleLogout;

  /// No description provided for @profileSubtitleDeleteAccount.
  ///
  /// In zh, this message translates to:
  /// **'永久移除账号与相关数据'**
  String get profileSubtitleDeleteAccount;

  /// No description provided for @profileSubtitleDefault.
  ///
  /// In zh, this message translates to:
  /// **'进入此页面继续调整详细设置'**
  String get profileSubtitleDefault;

  /// No description provided for @chatSelfVisibleOnly.
  ///
  /// In zh, this message translates to:
  /// **'仅自己可见'**
  String get chatSelfVisibleOnly;

  /// No description provided for @chatSelfVisibleDraftDesc.
  ///
  /// In zh, this message translates to:
  /// **'这条 AI 草稿只保存在你的当前私聊视图里。'**
  String get chatSelfVisibleDraftDesc;

  /// No description provided for @chatPromoteToBothVisible.
  ///
  /// In zh, this message translates to:
  /// **'改为双方都可见'**
  String get chatPromoteToBothVisible;

  /// No description provided for @chatPromoteToBothDesc.
  ///
  /// In zh, this message translates to:
  /// **'把这条草稿放回输入框，由你确认后发送给对方。'**
  String get chatPromoteToBothDesc;

  /// No description provided for @chatViewAccessoryContent.
  ///
  /// In zh, this message translates to:
  /// **'查看附加内容'**
  String get chatViewAccessoryContent;

  /// No description provided for @chatViewAccessoryContentDesc.
  ///
  /// In zh, this message translates to:
  /// **'在纯净模式下临时展开任务卡和快捷入口'**
  String get chatViewAccessoryContentDesc;

  /// No description provided for @chatActionSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'行动建议'**
  String get chatActionSuggestion;

  /// No description provided for @chatActionSuggestionDesc.
  ///
  /// In zh, this message translates to:
  /// **'继续完成这一步，或者先确认任务和计划。'**
  String get chatActionSuggestionDesc;

  /// No description provided for @chatTheaterTitle.
  ///
  /// In zh, this message translates to:
  /// **'推演剧场'**
  String get chatTheaterTitle;

  /// No description provided for @chatTheaterDesc.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先看的是哪条路径，以及它为什么更适合你。'**
  String get chatTheaterDesc;

  /// No description provided for @chatSimulationTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习仿真'**
  String get chatSimulationTitle;

  /// No description provided for @chatSimulationDesc.
  ///
  /// In zh, this message translates to:
  /// **'先看这一轮最关键的观点碰撞，再决定要不要进入完整模拟。'**
  String get chatSimulationDesc;

  /// No description provided for @chatReportTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习报告'**
  String get chatReportTitle;

  /// No description provided for @chatReportDesc.
  ///
  /// In zh, this message translates to:
  /// **'先看最核心的诊断和下一步动作，再决定是否进入完整报告页。'**
  String get chatReportDesc;

  /// No description provided for @chatAccessoryContent.
  ///
  /// In zh, this message translates to:
  /// **'附加内容'**
  String get chatAccessoryContent;

  /// No description provided for @chatContinueExploring.
  ///
  /// In zh, this message translates to:
  /// **'继续探索'**
  String get chatContinueExploring;

  /// No description provided for @chatSwipeToSwitch.
  ///
  /// In zh, this message translates to:
  /// **'左右滑动切换不同入口'**
  String get chatSwipeToSwitch;

  /// No description provided for @chatViewTheaterDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看推演详情'**
  String get chatViewTheaterDetails;

  /// No description provided for @chatCurrentLearningTopic.
  ///
  /// In zh, this message translates to:
  /// **'当前学习主题'**
  String get chatCurrentLearningTopic;

  /// No description provided for @chatViewSimulationDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看模拟详情'**
  String get chatViewSimulationDetails;

  /// No description provided for @chatCollaborationProcess.
  ///
  /// In zh, this message translates to:
  /// **'协作过程'**
  String get chatCollaborationProcess;

  /// No description provided for @chatPlanContext.
  ///
  /// In zh, this message translates to:
  /// **'计划上下文'**
  String get chatPlanContext;

  /// No description provided for @chatPlanStatus.
  ///
  /// In zh, this message translates to:
  /// **'计划状态'**
  String get chatPlanStatus;

  /// No description provided for @chatContinueFromConversation.
  ///
  /// In zh, this message translates to:
  /// **'承接刚才的对话'**
  String get chatContinueFromConversation;

  /// No description provided for @chatReviewFirstThenExpand.
  ///
  /// In zh, this message translates to:
  /// **'先看重点，再决定要不要展开完整体验'**
  String get chatReviewFirstThenExpand;

  /// No description provided for @chatPathLabel.
  ///
  /// In zh, this message translates to:
  /// **'路径'**
  String get chatPathLabel;

  /// No description provided for @chatMasteryLabel.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get chatMasteryLabel;

  /// No description provided for @chatOpenFullExperience.
  ///
  /// In zh, this message translates to:
  /// **'打开完整体验'**
  String get chatOpenFullExperience;

  /// No description provided for @chatContinueInChat.
  ///
  /// In zh, this message translates to:
  /// **'继续在对话里'**
  String get chatContinueInChat;

  /// No description provided for @chatViewLatestReport.
  ///
  /// In zh, this message translates to:
  /// **'查看最新学习报告'**
  String get chatViewLatestReport;

  /// No description provided for @chatViewLearningReport.
  ///
  /// In zh, this message translates to:
  /// **'查看学习报告'**
  String get chatViewLearningReport;

  /// No description provided for @chatKeyFocusLabel.
  ///
  /// In zh, this message translates to:
  /// **'重点关注'**
  String get chatKeyFocusLabel;

  /// No description provided for @chatShareResourceInvalidId.
  ///
  /// In zh, this message translates to:
  /// **'分享资源 ID 无效，无法采纳'**
  String get chatShareResourceInvalidId;

  /// No description provided for @chatShareResourceAdopted.
  ///
  /// In zh, this message translates to:
  /// **'已采纳，跳转中...'**
  String get chatShareResourceAdopted;

  /// No description provided for @chatShareResourceAdoptError.
  ///
  /// In zh, this message translates to:
  /// **'采纳失败: {error}'**
  String chatShareResourceAdoptError(Object error);

  /// No description provided for @chatTaskConfirmedMessage.
  ///
  /// In zh, this message translates to:
  /// **'已确认 {count} 个任务，开始执行！'**
  String chatTaskConfirmedMessage(Object count);

  /// No description provided for @chatViewPlan.
  ///
  /// In zh, this message translates to:
  /// **'查看计划'**
  String get chatViewPlan;

  /// No description provided for @chatGoToTaskList.
  ///
  /// In zh, this message translates to:
  /// **'去任务列表'**
  String get chatGoToTaskList;

  /// No description provided for @chatConfirmFailed.
  ///
  /// In zh, this message translates to:
  /// **'确认失败: {error}'**
  String chatConfirmFailed(Object error);

  /// No description provided for @chatTaskCompletedDoneMinutes.
  ///
  /// In zh, this message translates to:
  /// **'已完成 · {minutes}分钟'**
  String chatTaskCompletedDoneMinutes(Object minutes);

  /// No description provided for @chatTaskCompletedDone.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get chatTaskCompletedDone;

  /// No description provided for @chatPlanProgressLabel.
  ///
  /// In zh, this message translates to:
  /// **'进度: {percent}%'**
  String chatPlanProgressLabel(Object percent);

  /// No description provided for @chatPromptPreviewCancel.
  ///
  /// In zh, this message translates to:
  /// **'先不发'**
  String get chatPromptPreviewCancel;

  /// No description provided for @chatPromptPreviewSend.
  ///
  /// In zh, this message translates to:
  /// **'直接发送'**
  String get chatPromptPreviewSend;

  /// No description provided for @chatParticipantLabel.
  ///
  /// In zh, this message translates to:
  /// **'参与者'**
  String get chatParticipantLabel;

  /// No description provided for @chatPromptRefinePath.
  ///
  /// In zh, this message translates to:
  /// **'继续细化这条路径'**
  String get chatPromptRefinePath;

  /// No description provided for @chatPromptRefinePathMessage.
  ///
  /// In zh, this message translates to:
  /// **'继续围绕「{topic}」细化第一周最该先做的步骤。'**
  String chatPromptRefinePathMessage(Object topic);

  /// No description provided for @chatPromptComparePaths.
  ///
  /// In zh, this message translates to:
  /// **'比较两条路线'**
  String get chatPromptComparePaths;

  /// No description provided for @chatPromptComparePathsMessage.
  ///
  /// In zh, this message translates to:
  /// **'比较一下「{pathA}」和「{pathB}」的取舍。'**
  String chatPromptComparePathsMessage(Object pathA, Object pathB);

  /// No description provided for @chatPromptDefaultPathA.
  ///
  /// In zh, this message translates to:
  /// **'路线 A'**
  String get chatPromptDefaultPathA;

  /// No description provided for @chatPromptDefaultPathB.
  ///
  /// In zh, this message translates to:
  /// **'路线 B'**
  String get chatPromptDefaultPathB;

  /// No description provided for @chatPromptPrerequisites.
  ///
  /// In zh, this message translates to:
  /// **'先补什么前置'**
  String get chatPromptPrerequisites;

  /// No description provided for @chatPromptPrerequisitesMessage.
  ///
  /// In zh, this message translates to:
  /// **'如果我现在就开始学「{topic}」，最该先补的前置是什么？'**
  String chatPromptPrerequisitesMessage(Object topic);

  /// No description provided for @chatPromptExamFocus.
  ///
  /// In zh, this message translates to:
  /// **'考试重点是什么'**
  String get chatPromptExamFocus;

  /// No description provided for @chatPromptExamFocusMessage.
  ///
  /// In zh, this message translates to:
  /// **'围绕「{topic}」，告诉我最容易成为考试重点的部分和原因。'**
  String chatPromptExamFocusMessage(Object topic);

  /// No description provided for @chatPromptMakePlan.
  ///
  /// In zh, this message translates to:
  /// **'给我排成计划'**
  String get chatPromptMakePlan;

  /// No description provided for @chatPromptMakePlanMessage.
  ///
  /// In zh, this message translates to:
  /// **'把「{topic}」这条路径改写成 7 天可执行的小计划。'**
  String chatPromptMakePlanMessage(Object topic);

  /// No description provided for @chatPromptSimulateRound.
  ///
  /// In zh, this message translates to:
  /// **'继续模拟一轮'**
  String get chatPromptSimulateRound;

  /// No description provided for @chatPromptSimulateRoundMessage.
  ///
  /// In zh, this message translates to:
  /// **'继续围绕「{topic}」模拟一轮，我想继续跟进这个学习场景。'**
  String chatPromptSimulateRoundMessage(Object topic);

  /// No description provided for @chatOneOfTheRoles.
  ///
  /// In zh, this message translates to:
  /// **'其中一个角色'**
  String get chatOneOfTheRoles;

  /// No description provided for @chatPromptLetMeAnswer.
  ///
  /// In zh, this message translates to:
  /// **'让我来回答'**
  String get chatPromptLetMeAnswer;

  /// No description provided for @chatPromptLetMeAnswerMessage.
  ///
  /// In zh, this message translates to:
  /// **'让 {speaker} 围绕「{topic}」继续追问我一个关键问题，我来回答。'**
  String chatPromptLetMeAnswerMessage(Object speaker, Object topic);

  /// No description provided for @chatPromptPracticeExplain.
  ///
  /// In zh, this message translates to:
  /// **'练习讲给别人听'**
  String get chatPromptPracticeExplain;

  /// No description provided for @chatPromptPracticeExplainMessage.
  ///
  /// In zh, this message translates to:
  /// **'围绕「{topic}」安排一轮需要我讲给别人听的仿真。'**
  String chatPromptPracticeExplainMessage(Object topic);

  /// No description provided for @chatPromptErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'换成错因诊断'**
  String get chatPromptErrorDiagnosis;

  /// No description provided for @chatPromptErrorDiagnosisMessage.
  ///
  /// In zh, this message translates to:
  /// **'把「{topic}」切到错因诊断模式，帮我定位真正的卡点。'**
  String chatPromptErrorDiagnosisMessage(Object topic);

  /// No description provided for @chatPromptOrderActions.
  ///
  /// In zh, this message translates to:
  /// **'排今天行动顺序'**
  String get chatPromptOrderActions;

  /// No description provided for @chatPromptOrderActionsMessage.
  ///
  /// In zh, this message translates to:
  /// **'根据这份学习报告，帮我排一个今天就能开始的行动顺序。'**
  String get chatPromptOrderActionsMessage;

  /// No description provided for @chatPromptExpandKeyIssue.
  ///
  /// In zh, this message translates to:
  /// **'展开重点问题'**
  String get chatPromptExpandKeyIssue;

  /// No description provided for @chatPromptExpandKeyIssueMessage.
  ///
  /// In zh, this message translates to:
  /// **'展开讲讲为什么「{highlight}」最值得先处理。'**
  String chatPromptExpandKeyIssueMessage(Object highlight);

  /// No description provided for @chatPromptPrioritizeArea.
  ///
  /// In zh, this message translates to:
  /// **'先补哪一块'**
  String get chatPromptPrioritizeArea;

  /// No description provided for @chatPromptPrioritizeAreaMessage.
  ///
  /// In zh, this message translates to:
  /// **'根据这份报告，先帮我解释为什么「{area}」应该优先处理。'**
  String chatPromptPrioritizeAreaMessage(Object area);

  /// No description provided for @chatPromptConvertToPlan.
  ///
  /// In zh, this message translates to:
  /// **'转成 7 天计划'**
  String get chatPromptConvertToPlan;

  /// No description provided for @chatPromptConvertToPlanMessage.
  ///
  /// In zh, this message translates to:
  /// **'把这份学习报告改写成我接下来 7 天的执行顺序。'**
  String get chatPromptConvertToPlanMessage;

  /// No description provided for @chatPromptReviewOutline.
  ///
  /// In zh, this message translates to:
  /// **'帮我做复盘提纲'**
  String get chatPromptReviewOutline;

  /// No description provided for @chatPromptReviewOutlineMessage.
  ///
  /// In zh, this message translates to:
  /// **'根据这份学习报告，给我一份今晚就能用的复盘提纲。'**
  String get chatPromptReviewOutlineMessage;

  /// No description provided for @dashboardBottleneckPrompt.
  ///
  /// In zh, this message translates to:
  /// **'我想换个方式理解{topic}。请结合这个卡点，帮我调整接下来的学习路径。'**
  String dashboardBottleneckPrompt(Object topic);

  /// No description provided for @dashboardSetFirstGoal.
  ///
  /// In zh, this message translates to:
  /// **'先定下你的第一个目标'**
  String get dashboardSetFirstGoal;

  /// No description provided for @dashboardSetFirstGoalSummary.
  ///
  /// In zh, this message translates to:
  /// **'告诉我你最近最想推进的一件事，我会立刻帮你拆成可执行的计划。'**
  String get dashboardSetFirstGoalSummary;

  /// No description provided for @dashboardStartWithAI.
  ///
  /// In zh, this message translates to:
  /// **'和 AI 定目标'**
  String get dashboardStartWithAI;

  /// No description provided for @dashboardOpenTaskList.
  ///
  /// In zh, this message translates to:
  /// **'查看任务列表'**
  String get dashboardOpenTaskList;

  /// No description provided for @dashboardDueToday.
  ///
  /// In zh, this message translates to:
  /// **'今天截止'**
  String get dashboardDueToday;

  /// No description provided for @dashboardOverdueDays.
  ///
  /// In zh, this message translates to:
  /// **'已逾期 {days} 天'**
  String dashboardOverdueDays(Object days);

  /// No description provided for @dashboardDaysLeft.
  ///
  /// In zh, this message translates to:
  /// **'还有 {days} 天'**
  String dashboardDaysLeft(Object days);

  /// No description provided for @dashboardMainMove.
  ///
  /// In zh, this message translates to:
  /// **'1 个重点动作'**
  String get dashboardMainMove;

  /// No description provided for @dashboardMoreQueued.
  ///
  /// In zh, this message translates to:
  /// **'另有 {count} 项待推进'**
  String dashboardMoreQueued(Object count);

  /// No description provided for @dashboardProgress.
  ///
  /// In zh, this message translates to:
  /// **'{percent}% 进度'**
  String dashboardProgress(Object percent);

  /// No description provided for @dashboardTodayBriefing.
  ///
  /// In zh, this message translates to:
  /// **'今日总览'**
  String get dashboardTodayBriefing;

  /// No description provided for @dashboardBriefingSummary.
  ///
  /// In zh, this message translates to:
  /// **'把最重要的事情压缩成一张卡'**
  String get dashboardBriefingSummary;

  /// No description provided for @dashboardSparkleObservation.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle 的观察'**
  String get dashboardSparkleObservation;

  /// No description provided for @dashboardStartWithThis.
  ///
  /// In zh, this message translates to:
  /// **'今天先做这一步'**
  String get dashboardStartWithThis;

  /// No description provided for @dashboardGrowthSignal.
  ///
  /// In zh, this message translates to:
  /// **'最近最明显的变化'**
  String get dashboardGrowthSignal;

  /// No description provided for @dashboardMoreTasksQueued.
  ///
  /// In zh, this message translates to:
  /// **'除了当前重点，还有 {count} 项任务在队列中。'**
  String dashboardMoreTasksQueued(Object count);

  /// No description provided for @dashboardStartFocus.
  ///
  /// In zh, this message translates to:
  /// **'开始专注'**
  String get dashboardStartFocus;

  /// No description provided for @dashboardStartHere.
  ///
  /// In zh, this message translates to:
  /// **'先做这个'**
  String get dashboardStartHere;

  /// No description provided for @dashboardOpenTasks.
  ///
  /// In zh, this message translates to:
  /// **'查看任务'**
  String get dashboardOpenTasks;

  /// No description provided for @dashboardTaskList.
  ///
  /// In zh, this message translates to:
  /// **'任务列表'**
  String get dashboardTaskList;

  /// No description provided for @dashboardActivePlan.
  ///
  /// In zh, this message translates to:
  /// **'当前主计划'**
  String get dashboardActivePlan;

  /// No description provided for @dashboardPhaseLabel.
  ///
  /// In zh, this message translates to:
  /// **'阶段：{phase}'**
  String dashboardPhaseLabel(Object phase);

  /// No description provided for @dashboardPhaseInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get dashboardPhaseInProgress;

  /// No description provided for @dashboardDaysToDeadline.
  ///
  /// In zh, this message translates to:
  /// **'距离截止还有 {days} 天'**
  String dashboardDaysToDeadline(Object days);

  /// No description provided for @dashboardPrediction.
  ///
  /// In zh, this message translates to:
  /// **'预测建议'**
  String get dashboardPrediction;

  /// No description provided for @dashboardMessagesCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条消息'**
  String dashboardMessagesCount(Object count);

  /// No description provided for @dashboardAlertsCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条通知'**
  String dashboardAlertsCount(Object count);

  /// No description provided for @dashboardInsightsCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条洞察'**
  String dashboardInsightsCount(Object count);

  /// No description provided for @dashboardReviewPending.
  ///
  /// In zh, this message translates to:
  /// **'夜间复盘待处理'**
  String get dashboardReviewPending;

  /// No description provided for @dashboardUpdatesInsights.
  ///
  /// In zh, this message translates to:
  /// **'更新与洞察'**
  String get dashboardUpdatesInsights;

  /// No description provided for @planEditTypeTitle.
  ///
  /// In zh, this message translates to:
  /// **'编辑{type}'**
  String planEditTypeTitle(Object type);

  /// No description provided for @planUpdated.
  ///
  /// In zh, this message translates to:
  /// **'计划已更新'**
  String get planUpdated;

  /// No description provided for @planGuideFillNameAndGoalFirst.
  ///
  /// In zh, this message translates to:
  /// **'先填写计划名称和计划目标，再生成 AI 指南'**
  String get planGuideFillNameAndGoalFirst;

  /// No description provided for @planGuideGeneratedHuman.
  ///
  /// In zh, this message translates to:
  /// **'已生成给用户看的执行指南'**
  String get planGuideGeneratedHuman;

  /// No description provided for @planGuideGeneratedAi.
  ///
  /// In zh, this message translates to:
  /// **'已生成给 AI 使用的执行版本'**
  String get planGuideGeneratedAi;

  /// No description provided for @planGuideGenerationFailed.
  ///
  /// In zh, this message translates to:
  /// **'计划指南生成失败：{error}'**
  String planGuideGenerationFailed(Object error);

  /// No description provided for @planSuggestedGrowthTask1.
  ///
  /// In zh, this message translates to:
  /// **'建立本周主线推进清单'**
  String get planSuggestedGrowthTask1;

  /// No description provided for @planSuggestedGrowthTask2.
  ///
  /// In zh, this message translates to:
  /// **'完成一次阶段复盘'**
  String get planSuggestedGrowthTask2;

  /// No description provided for @planSuggestedSprintTask1.
  ///
  /// In zh, this message translates to:
  /// **'确认冲刺目标与验收标准'**
  String get planSuggestedSprintTask1;

  /// No description provided for @planSuggestedSprintTask2.
  ///
  /// In zh, this message translates to:
  /// **'完成冲刺关键里程碑'**
  String get planSuggestedSprintTask2;

  /// No description provided for @planSave.
  ///
  /// In zh, this message translates to:
  /// **'保存计划'**
  String get planSave;

  /// No description provided for @planStepBasics.
  ///
  /// In zh, this message translates to:
  /// **'计划定位'**
  String get planStepBasics;

  /// No description provided for @planStepSchedule.
  ///
  /// In zh, this message translates to:
  /// **'时间结构'**
  String get planStepSchedule;

  /// No description provided for @planStepTasks.
  ///
  /// In zh, this message translates to:
  /// **'任务编排'**
  String get planStepTasks;

  /// No description provided for @planStepGuide.
  ///
  /// In zh, this message translates to:
  /// **'计划边界与指南'**
  String get planStepGuide;

  /// No description provided for @planStepReview.
  ///
  /// In zh, this message translates to:
  /// **'确认预览'**
  String get planStepReview;

  /// No description provided for @planAiVersionCopied.
  ///
  /// In zh, this message translates to:
  /// **'AI 版本已复制'**
  String get planAiVersionCopied;

  /// No description provided for @planBasicsDescription.
  ///
  /// In zh, this message translates to:
  /// **'先定义这是一张真正的计划卡，而不是普通任务。'**
  String get planBasicsDescription;

  /// No description provided for @planBasicsNameHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：6 周英语口语提升 / 期中冲刺收束'**
  String get planBasicsNameHint;

  /// No description provided for @planBasicsNameRequired.
  ///
  /// In zh, this message translates to:
  /// **'请先填写计划名称'**
  String get planBasicsNameRequired;

  /// No description provided for @planBasicsSubjectLabel.
  ///
  /// In zh, this message translates to:
  /// **'主题方向'**
  String get planBasicsSubjectLabel;

  /// No description provided for @planBasicsSubjectHint.
  ///
  /// In zh, this message translates to:
  /// **'英语、Flutter、考研数学、论文阅读...'**
  String get planBasicsSubjectHint;

  /// No description provided for @planBasicsGoalLabelGrowth.
  ///
  /// In zh, this message translates to:
  /// **'长期目标'**
  String get planBasicsGoalLabelGrowth;

  /// No description provided for @planBasicsGoalLabelSprint.
  ///
  /// In zh, this message translates to:
  /// **'冲刺目标'**
  String get planBasicsGoalLabelSprint;

  /// No description provided for @planBasicsGoalHintGrowth.
  ///
  /// In zh, this message translates to:
  /// **'写清楚这个成长计划最终想形成什么能力、习惯或成果。'**
  String get planBasicsGoalHintGrowth;

  /// No description provided for @planBasicsGoalHintSprint.
  ///
  /// In zh, this message translates to:
  /// **'写清楚这次冲刺的结果、验收标准和不能偏离的主线。'**
  String get planBasicsGoalHintSprint;

  /// No description provided for @planBasicsGoalRequired.
  ///
  /// In zh, this message translates to:
  /// **'请写出这张计划卡的目标'**
  String get planBasicsGoalRequired;

  /// No description provided for @planBasicsPriorityLabel.
  ///
  /// In zh, this message translates to:
  /// **'计划优先级'**
  String get planBasicsPriorityLabel;

  /// No description provided for @planPriorityNormalValue.
  ///
  /// In zh, this message translates to:
  /// **'正常'**
  String get planPriorityNormalValue;

  /// No description provided for @planPriorityCriticalValue.
  ///
  /// In zh, this message translates to:
  /// **'关键'**
  String get planPriorityCriticalValue;

  /// No description provided for @planScheduleDescription.
  ///
  /// In zh, this message translates to:
  /// **'把持续时间、每日投入和提醒节奏一次性定清楚。'**
  String get planScheduleDescription;

  /// No description provided for @planScheduleDailyMinutesLabel.
  ///
  /// In zh, this message translates to:
  /// **'每日可投入时长'**
  String get planScheduleDailyMinutesLabel;

  /// No description provided for @planScheduleMinutesUnit.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String planScheduleMinutesUnit(Object minutes);

  /// No description provided for @planScheduleTotalHours.
  ///
  /// In zh, this message translates to:
  /// **'总预估工时 {hours} 小时'**
  String planScheduleTotalHours(Object hours);

  /// No description provided for @planScheduleTargetDateUnset.
  ///
  /// In zh, this message translates to:
  /// **'暂未设置'**
  String get planScheduleTargetDateUnset;

  /// No description provided for @planScheduleReminderTime.
  ///
  /// In zh, this message translates to:
  /// **'每日提醒时间'**
  String get planScheduleReminderTime;

  /// No description provided for @planScheduleStageLabel.
  ///
  /// In zh, this message translates to:
  /// **'当前计划阶段'**
  String get planScheduleStageLabel;

  /// No description provided for @planScheduleStageSprint.
  ///
  /// In zh, this message translates to:
  /// **'冲刺推进'**
  String get planScheduleStageSprint;

  /// No description provided for @planScheduleStageDaily.
  ///
  /// In zh, this message translates to:
  /// **'日常执行'**
  String get planScheduleStageDaily;

  /// No description provided for @planScheduleStageReview.
  ///
  /// In zh, this message translates to:
  /// **'复盘调优'**
  String get planScheduleStageReview;

  /// No description provided for @planScheduleStagePaused.
  ///
  /// In zh, this message translates to:
  /// **'暂时暂停'**
  String get planScheduleStagePaused;

  /// No description provided for @planScheduleChipWeekday.
  ///
  /// In zh, this message translates to:
  /// **'工作日推进，周末复盘'**
  String get planScheduleChipWeekday;

  /// No description provided for @planScheduleChipMorning.
  ///
  /// In zh, this message translates to:
  /// **'早晨启动，晚上收束'**
  String get planScheduleChipMorning;

  /// No description provided for @planScheduleChipAfternoon.
  ///
  /// In zh, this message translates to:
  /// **'午后主攻，夜间轻复盘'**
  String get planScheduleChipAfternoon;

  /// No description provided for @planScheduleRhythmLabel.
  ///
  /// In zh, this message translates to:
  /// **'节奏说明'**
  String get planScheduleRhythmLabel;

  /// No description provided for @planScheduleRhythmHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：周一到周五推进，周六复盘，周日补缺'**
  String get planScheduleRhythmHint;

  /// No description provided for @planTasksDescription.
  ///
  /// In zh, this message translates to:
  /// **'这一步决定计划实际会承载哪些动作。已有任务先做参考，新任务会真正归属到计划下。'**
  String get planTasksDescription;

  /// No description provided for @planTasksBlueprintLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务编排说明'**
  String get planTasksBlueprintLabel;

  /// No description provided for @planTasksBlueprintHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：先搭框架，再每天推进主线，最后统一复盘补漏。'**
  String get planTasksBlueprintHint;

  /// No description provided for @planTasksRefExisting.
  ///
  /// In zh, this message translates to:
  /// **'参考已有任务'**
  String get planTasksRefExisting;

  /// No description provided for @planTasksMinutesDifficulty.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟 · 难度 {difficulty}'**
  String planTasksMinutesDifficulty(Object minutes, Object difficulty);

  /// No description provided for @planTasksCopyToPlan.
  ///
  /// In zh, this message translates to:
  /// **'复制进计划'**
  String get planTasksCopyToPlan;

  /// No description provided for @planTasksNewTaskLabel.
  ///
  /// In zh, this message translates to:
  /// **'新增计划任务'**
  String get planTasksNewTaskLabel;

  /// No description provided for @planTasksNewTaskHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：完成一轮章节梳理'**
  String get planTasksNewTaskHint;

  /// No description provided for @planTasksDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'时长'**
  String get planTasksDurationLabel;

  /// No description provided for @planTasksAddToPlan.
  ///
  /// In zh, this message translates to:
  /// **'加入计划任务'**
  String get planTasksAddToPlan;

  /// No description provided for @planTasksEmpty.
  ///
  /// In zh, this message translates to:
  /// **'当前还没有计划任务'**
  String get planTasksEmpty;

  /// No description provided for @planGuideScopeLabel.
  ///
  /// In zh, this message translates to:
  /// **'计划边界与注意事项'**
  String get planGuideScopeLabel;

  /// No description provided for @planGuideScopeHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：本计划不承担临时杂事，只关注考试主线；每天只推进一条主线动作。'**
  String get planGuideScopeHint;

  /// No description provided for @planGuidePerspectiveLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务指南视角'**
  String get planGuidePerspectiveLabel;

  /// No description provided for @planGuideForHuman.
  ///
  /// In zh, this message translates to:
  /// **'给自己看'**
  String get planGuideForHuman;

  /// No description provided for @planGuideForAi.
  ///
  /// In zh, this message translates to:
  /// **'给 AI 用'**
  String get planGuideForAi;

  /// No description provided for @planGuideHumanInfo.
  ///
  /// In zh, this message translates to:
  /// **'用户版会默认作为计划卡上的执行指南保存，帮助用户自己直接推进。'**
  String get planGuideHumanInfo;

  /// No description provided for @planGuideAiInfo.
  ///
  /// In zh, this message translates to:
  /// **'AI 版本只在需要时生成，用于 Sparkle 内部任务助手，不作为默认持久化内容。'**
  String get planGuideAiInfo;

  /// No description provided for @planGuideHumanTitle.
  ///
  /// In zh, this message translates to:
  /// **'用户版执行指南'**
  String get planGuideHumanTitle;

  /// No description provided for @planGuideAiTitle.
  ///
  /// In zh, this message translates to:
  /// **'给 AI 的执行版本'**
  String get planGuideAiTitle;

  /// No description provided for @planGuideGenerating.
  ///
  /// In zh, this message translates to:
  /// **'生成中'**
  String get planGuideGenerating;

  /// No description provided for @planGuideGenerateHuman.
  ///
  /// In zh, this message translates to:
  /// **'生成用户版'**
  String get planGuideGenerateHuman;

  /// No description provided for @planGuideGenerateAi.
  ///
  /// In zh, this message translates to:
  /// **'生成 AI 版'**
  String get planGuideGenerateAi;

  /// No description provided for @planGuideHumanHint.
  ///
  /// In zh, this message translates to:
  /// **'生成后会在这里看到计划推进主线、每日节奏、风险提醒和今日起步动作。'**
  String get planGuideHumanHint;

  /// No description provided for @planGuideAiEmpty.
  ///
  /// In zh, this message translates to:
  /// **'还没有 AI 版本。只有明确需要时才生成，避免无意义耗 token。'**
  String get planGuideAiEmpty;

  /// No description provided for @planGuideCopyAi.
  ///
  /// In zh, this message translates to:
  /// **'复制 AI 版'**
  String get planGuideCopyAi;

  /// No description provided for @planReviewSummary.
  ///
  /// In zh, this message translates to:
  /// **'{planType} · {minutes} 分钟/天 · {hours} 小时'**
  String planReviewSummary(Object planType, Object minutes, Object hours);

  /// No description provided for @planReviewEditInfo.
  ///
  /// In zh, this message translates to:
  /// **'保存后会更新计划描述，并为新增草案创建新的计划任务。'**
  String get planReviewEditInfo;

  /// No description provided for @planReviewCreateInfo.
  ///
  /// In zh, this message translates to:
  /// **'创建后会生成一张更完整的计划卡，并同步创建计划任务。'**
  String get planReviewCreateInfo;

  /// No description provided for @planReviewFinalDescription.
  ///
  /// In zh, this message translates to:
  /// **'最终写入的计划描述'**
  String get planReviewFinalDescription;

  /// No description provided for @taskExecutionChatAboutStuckPoint.
  ///
  /// In zh, this message translates to:
  /// **'和 Sparkle 聊聊这个卡点'**
  String get taskExecutionChatAboutStuckPoint;

  /// No description provided for @taskExecutionSentToAurora.
  ///
  /// In zh, this message translates to:
  /// **'已发送给 Aurora'**
  String get taskExecutionSentToAurora;

  /// No description provided for @taskExecutionStuckPromptIntro.
  ///
  /// In zh, this message translates to:
  /// **'我在做这个任务时卡住了，想和你一起拆一下具体卡点。'**
  String get taskExecutionStuckPromptIntro;

  /// No description provided for @taskExecutionStuckTaskLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务：{title}'**
  String taskExecutionStuckTaskLabel(Object title);

  /// No description provided for @taskExecutionStuckEstimatedTime.
  ///
  /// In zh, this message translates to:
  /// **'预估时间：{minutes}分钟'**
  String taskExecutionStuckEstimatedTime(Object minutes);

  /// No description provided for @taskExecutionStuckFocusCue.
  ///
  /// In zh, this message translates to:
  /// **'今日焦点：{cue}'**
  String taskExecutionStuckFocusCue(Object cue);

  /// No description provided for @taskExecutionStuckSteps.
  ///
  /// In zh, this message translates to:
  /// **'任务步骤：{steps}'**
  String taskExecutionStuckSteps(Object steps);

  /// No description provided for @taskExecutionStuckCriteria.
  ///
  /// In zh, this message translates to:
  /// **'完成标准：{criteria}'**
  String taskExecutionStuckCriteria(Object criteria);

  /// No description provided for @taskExecutionStuckSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'卡住时建议：{suggestion}'**
  String taskExecutionStuckSuggestion(Object suggestion);

  /// No description provided for @taskExecutionStuckClarifyPrompt.
  ///
  /// In zh, this message translates to:
  /// **'请先问我一个最关键的澄清问题，然后把下一步缩小到5分钟内能开始。'**
  String get taskExecutionStuckClarifyPrompt;

  /// No description provided for @taskExecutionStuckTooltip.
  ///
  /// In zh, this message translates to:
  /// **'卡住了？'**
  String get taskExecutionStuckTooltip;

  /// No description provided for @taskExecutionStuckLabel.
  ///
  /// In zh, this message translates to:
  /// **'卡住了?'**
  String get taskExecutionStuckLabel;

  /// No description provided for @taskExecutionAuroraDiagnosticUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 诊断暂时不可用：{error}'**
  String taskExecutionAuroraDiagnosticUnavailable(Object error);

  /// No description provided for @taskExecutionResetTimer.
  ///
  /// In zh, this message translates to:
  /// **'重置'**
  String get taskExecutionResetTimer;

  /// No description provided for @taskExecutionAiHandoffFailed.
  ///
  /// In zh, this message translates to:
  /// **'AI 执行发起失败'**
  String get taskExecutionAiHandoffFailed;

  /// No description provided for @taskExecutionAiCompleted.
  ///
  /// In zh, this message translates to:
  /// **'AI 已完成本次执行'**
  String get taskExecutionAiCompleted;

  /// No description provided for @taskExecutionAiPartial.
  ///
  /// In zh, this message translates to:
  /// **'AI 已完成部分内容，请继续查看'**
  String get taskExecutionAiPartial;

  /// No description provided for @taskExecutionAiFailed.
  ///
  /// In zh, this message translates to:
  /// **'AI 执行失败'**
  String get taskExecutionAiFailed;

  /// No description provided for @taskExecutionAiWaitingApproval.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在等待你的确认'**
  String get taskExecutionAiWaitingApproval;

  /// No description provided for @taskExecutionAiHandedOff.
  ///
  /// In zh, this message translates to:
  /// **'任务已交给 AI，当前状态：{status}'**
  String taskExecutionAiHandedOff(Object status);

  /// No description provided for @taskExecutionPermissionInsufficientQueued.
  ///
  /// In zh, this message translates to:
  /// **'当前执行权限不足，任务已加入等待队列。补齐权限后可统一重试。'**
  String get taskExecutionPermissionInsufficientQueued;

  /// No description provided for @taskExecutionAiConfirmFailed.
  ///
  /// In zh, this message translates to:
  /// **'AI 结果确认失败'**
  String get taskExecutionAiConfirmFailed;

  /// No description provided for @taskExecutionAiResultConfirmed.
  ///
  /// In zh, this message translates to:
  /// **'AI 结果已确认，任务状态已同步'**
  String get taskExecutionAiResultConfirmed;

  /// No description provided for @taskExecutionRejectFailed.
  ///
  /// In zh, this message translates to:
  /// **'取回任务失败'**
  String get taskExecutionRejectFailed;

  /// No description provided for @taskExecutionTaskReturned.
  ///
  /// In zh, this message translates to:
  /// **'任务已交还给你继续处理'**
  String get taskExecutionTaskReturned;

  /// No description provided for @taskExecutionAiTakingOver.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在接管这个任务'**
  String get taskExecutionAiTakingOver;

  /// No description provided for @taskExecutionAiNotStarted.
  ///
  /// In zh, this message translates to:
  /// **'AI 执行尚未开始'**
  String get taskExecutionAiNotStarted;

  /// No description provided for @taskExecutionAiStatusLabel.
  ///
  /// In zh, this message translates to:
  /// **'AI 状态：{status}'**
  String taskExecutionAiStatusLabel(Object status);

  /// No description provided for @taskExecutionSendingToOpenclaw.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle 正在把任务发送给 OpenClaw。'**
  String get taskExecutionSendingToOpenclaw;

  /// No description provided for @taskExecutionDigitalTaskHint.
  ///
  /// In zh, this message translates to:
  /// **'适合数字执行的任务可以在这里一键转交。'**
  String get taskExecutionDigitalTaskHint;

  /// No description provided for @taskExecutionValidationLabel.
  ///
  /// In zh, this message translates to:
  /// **'校验 {passed}/{total}'**
  String taskExecutionValidationLabel(Object passed, Object total);

  /// No description provided for @taskExecutionResultLabel.
  ///
  /// In zh, this message translates to:
  /// **'结果：{text}'**
  String taskExecutionResultLabel(Object text);

  /// No description provided for @taskExecutionApprovalRequestLabel.
  ///
  /// In zh, this message translates to:
  /// **' · 审批请求 {count}'**
  String taskExecutionApprovalRequestLabel(Object count);

  /// No description provided for @taskExecutionGoalWithTrust.
  ///
  /// In zh, this message translates to:
  /// **'目标：{goal} · {trust}'**
  String taskExecutionGoalWithTrust(Object goal, Object trust);

  /// No description provided for @taskExecutionResultTrust.
  ///
  /// In zh, this message translates to:
  /// **'结果信任：{trust}'**
  String taskExecutionResultTrust(Object trust);

  /// No description provided for @taskExecutionTemplateLabel.
  ///
  /// In zh, this message translates to:
  /// **'模板 {name}'**
  String taskExecutionTemplateLabel(Object name);

  /// No description provided for @taskExecutionStrategyLabel.
  ///
  /// In zh, this message translates to:
  /// **'策略 {variant}'**
  String taskExecutionStrategyLabel(Object variant);

  /// No description provided for @taskExecutionNodeLabel.
  ///
  /// In zh, this message translates to:
  /// **'节点 {label}'**
  String taskExecutionNodeLabel(Object label);

  /// No description provided for @taskExecutionAiTakingOverLoading.
  ///
  /// In zh, this message translates to:
  /// **'AI 接管中...'**
  String get taskExecutionAiTakingOverLoading;

  /// No description provided for @taskExecutionRehandoffToAi.
  ///
  /// In zh, this message translates to:
  /// **'重新交给 AI'**
  String get taskExecutionRehandoffToAi;

  /// No description provided for @taskExecutionHandoffToAiAgain.
  ///
  /// In zh, this message translates to:
  /// **'再次交给 AI'**
  String get taskExecutionHandoffToAiAgain;

  /// No description provided for @taskExecutionWaitingConfirm.
  ///
  /// In zh, this message translates to:
  /// **'等待确认'**
  String get taskExecutionWaitingConfirm;

  /// No description provided for @taskExecutionAiRunning.
  ///
  /// In zh, this message translates to:
  /// **'AI 执行中'**
  String get taskExecutionAiRunning;

  /// No description provided for @taskExecutionHandoffToAi.
  ///
  /// In zh, this message translates to:
  /// **'交给 AI 执行'**
  String get taskExecutionHandoffToAi;

  /// No description provided for @taskExecutionRecommendedTemplates.
  ///
  /// In zh, this message translates to:
  /// **'推荐执行模板'**
  String get taskExecutionRecommendedTemplates;

  /// No description provided for @taskExecutionOpenclawConnectedNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 能连上，但当前没有执行权限'**
  String get taskExecutionOpenclawConnectedNoPermission;

  /// No description provided for @taskExecutionOpenclawOfflineQueued.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 当前离线，可先加入等待队列'**
  String get taskExecutionOpenclawOfflineQueued;

  /// No description provided for @taskExecutionOpenclawNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 尚未连接'**
  String get taskExecutionOpenclawNotConnected;

  /// No description provided for @taskExecutionOpenclawPermissionHint.
  ///
  /// In zh, this message translates to:
  /// **'当前令牌能访问网关，但执行会被权限拦住。你可以先把任务排队，等权限修好后统一重试。'**
  String get taskExecutionOpenclawPermissionHint;

  /// No description provided for @taskExecutionOpenclawOfflineHint.
  ///
  /// In zh, this message translates to:
  /// **'你可以先继续委派，等引擎恢复后再统一重试，不需要在这个任务页停住。'**
  String get taskExecutionOpenclawOfflineHint;

  /// No description provided for @taskExecutionOpenclawNotConnectedHint.
  ///
  /// In zh, this message translates to:
  /// **'先完成一次连接，之后任务页和聊天页都会把它当成同一个执行入口来使用。'**
  String get taskExecutionOpenclawNotConnectedHint;

  /// No description provided for @taskExecutionViewAction.
  ///
  /// In zh, this message translates to:
  /// **'查看'**
  String get taskExecutionViewAction;

  /// No description provided for @taskExecutionConnectAction.
  ///
  /// In zh, this message translates to:
  /// **'连接'**
  String get taskExecutionConnectAction;

  /// No description provided for @taskExecutionDismissHint.
  ///
  /// In zh, this message translates to:
  /// **'关闭提示'**
  String get taskExecutionDismissHint;

  /// No description provided for @taskExecutionMetricConnectedNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'已连到网关但无执行权限'**
  String get taskExecutionMetricConnectedNoPermission;

  /// No description provided for @taskExecutionMetricConfiguredOffline.
  ///
  /// In zh, this message translates to:
  /// **'已配置但离线'**
  String get taskExecutionMetricConfiguredOffline;

  /// No description provided for @taskExecutionMetricNotConfigured.
  ///
  /// In zh, this message translates to:
  /// **'尚未配置'**
  String get taskExecutionMetricNotConfigured;

  /// No description provided for @taskExecutionMetricQueuedTasks.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个任务已排队'**
  String taskExecutionMetricQueuedTasks(Object count);

  /// No description provided for @taskExecutionSuggestionFixPermission.
  ///
  /// In zh, this message translates to:
  /// **'建议先修权限再重试'**
  String get taskExecutionSuggestionFixPermission;

  /// No description provided for @taskExecutionSuggestionQueueFirst.
  ///
  /// In zh, this message translates to:
  /// **'建议先排队再统一重试'**
  String get taskExecutionSuggestionQueueFirst;

  /// No description provided for @taskExecutionSuggestionConnectFirst.
  ///
  /// In zh, this message translates to:
  /// **'建议先连接再委派'**
  String get taskExecutionSuggestionConnectFirst;

  /// No description provided for @taskExecutionNudgeCurrentStatus.
  ///
  /// In zh, this message translates to:
  /// **'当前状态'**
  String get taskExecutionNudgeCurrentStatus;

  /// No description provided for @taskExecutionNudgeStatusPermissionIssue.
  ///
  /// In zh, this message translates to:
  /// **'这台设备已经能访问 OpenClaw 网关，但当前认证没有真正发起执行的权限。'**
  String get taskExecutionNudgeStatusPermissionIssue;

  /// No description provided for @taskExecutionNudgeStatusOffline.
  ///
  /// In zh, this message translates to:
  /// **'连接信息还在，但引擎暂时不在线。'**
  String get taskExecutionNudgeStatusOffline;

  /// No description provided for @taskExecutionNudgeStatusNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'这台设备还没有接入 OpenClaw。'**
  String get taskExecutionNudgeStatusNotConnected;

  /// No description provided for @taskExecutionNudgeWhyThisPrompt.
  ///
  /// In zh, this message translates to:
  /// **'为什么现在看到这个提示'**
  String get taskExecutionNudgeWhyThisPrompt;

  /// No description provided for @taskExecutionNudgeWhyThisPromptValue.
  ///
  /// In zh, this message translates to:
  /// **'你正在一个支持 AI 委派的任务里，而且当前执行入口还没有准备好。'**
  String get taskExecutionNudgeWhyThisPromptValue;

  /// No description provided for @taskExecutionNudgeNextAction.
  ///
  /// In zh, this message translates to:
  /// **'下一步动作'**
  String get taskExecutionNudgeNextAction;

  /// No description provided for @taskExecutionNudgeNextActionPermissionIssue.
  ///
  /// In zh, this message translates to:
  /// **'打开 OpenClaw Hub 更换具备执行权限的令牌，或切到已配对的 WebSocket 连接；修好后再统一重试队列。'**
  String get taskExecutionNudgeNextActionPermissionIssue;

  /// No description provided for @taskExecutionNudgeNextActionOffline.
  ///
  /// In zh, this message translates to:
  /// **'继续把任务加入等待队列，或去 OpenClaw Hub 恢复连接后统一重试。'**
  String get taskExecutionNudgeNextActionOffline;

  /// No description provided for @taskExecutionNudgeNextActionNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'打开 OpenClaw Hub 完成连接，之后再回到这里发起委派。'**
  String get taskExecutionNudgeNextActionNotConnected;

  /// No description provided for @taskExecutionCompletedToday.
  ///
  /// In zh, this message translates to:
  /// **'今天完成了！'**
  String get taskExecutionCompletedToday;

  /// No description provided for @taskExecutionCompletionCheckHint.
  ///
  /// In zh, this message translates to:
  /// **'先对照完成标准看一眼。符合了就收下这次完成；还差一点也没关系，继续拆小就好。'**
  String get taskExecutionCompletionCheckHint;

  /// No description provided for @taskExecutionCompletionCriteria.
  ///
  /// In zh, this message translates to:
  /// **'完成标准'**
  String get taskExecutionCompletionCriteria;

  /// No description provided for @taskExecutionNoCriteriaHint.
  ///
  /// In zh, this message translates to:
  /// **'这张卡没有写明确完成标准，就按你今天最小可交付的一步来判断。'**
  String get taskExecutionNoCriteriaHint;

  /// No description provided for @taskExecutionCriteriaMatchQuestion.
  ///
  /// In zh, this message translates to:
  /// **'对照标准，是否符合？'**
  String get taskExecutionCriteriaMatchQuestion;

  /// No description provided for @taskExecutionCriteriaNotMet.
  ///
  /// In zh, this message translates to:
  /// **'还不符合'**
  String get taskExecutionCriteriaNotMet;

  /// No description provided for @taskExecutionContinueOrRetryTomorrow.
  ///
  /// In zh, this message translates to:
  /// **'那就继续，或者标记明天重新做'**
  String get taskExecutionContinueOrRetryTomorrow;

  /// No description provided for @taskExecutionCriteriaMetComplete.
  ///
  /// In zh, this message translates to:
  /// **'符合，完成'**
  String get taskExecutionCriteriaMetComplete;

  /// No description provided for @taskExecutionRejectReasonInaccurate.
  ///
  /// In zh, this message translates to:
  /// **'结果不准确'**
  String get taskExecutionRejectReasonInaccurate;

  /// No description provided for @taskExecutionRejectReasonIncomplete.
  ///
  /// In zh, this message translates to:
  /// **'结果不完整'**
  String get taskExecutionRejectReasonIncomplete;

  /// No description provided for @taskExecutionRejectReasonSafety.
  ///
  /// In zh, this message translates to:
  /// **'安全顾虑'**
  String get taskExecutionRejectReasonSafety;

  /// No description provided for @taskExecutionRejectReasonSelfDo.
  ///
  /// In zh, this message translates to:
  /// **'我想自己做'**
  String get taskExecutionRejectReasonSelfDo;

  /// No description provided for @taskExecutionRejectReasonTitle.
  ///
  /// In zh, this message translates to:
  /// **'退回原因'**
  String get taskExecutionRejectReasonTitle;

  /// No description provided for @taskExecutionRejectDescription.
  ///
  /// In zh, this message translates to:
  /// **'告诉 Sparkle 为什么这次结果不适合直接采纳，后续会据此调整执行方式。'**
  String get taskExecutionRejectDescription;

  /// No description provided for @taskExecutionRejectAdditionalNote.
  ///
  /// In zh, this message translates to:
  /// **'补充说明'**
  String get taskExecutionRejectAdditionalNote;

  /// No description provided for @taskExecutionRejectNoteHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：缺少来源、结论太武断、我想保留自己的表达方式'**
  String get taskExecutionRejectNoteHint;

  /// No description provided for @taskExecutionRejectConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认退回'**
  String get taskExecutionRejectConfirm;

  /// No description provided for @taskExecutionUserRetrievedTask.
  ///
  /// In zh, this message translates to:
  /// **'用户取回任务'**
  String get taskExecutionUserRetrievedTask;

  /// No description provided for @planDetailTaskLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'加载任务失败: {error}'**
  String planDetailTaskLoadFailed(Object error);

  /// No description provided for @planDetailNoExternalTasks.
  ///
  /// In zh, this message translates to:
  /// **'没有可添加的外部任务'**
  String get planDetailNoExternalTasks;

  /// No description provided for @planDetailAddExistingTaskTitle.
  ///
  /// In zh, this message translates to:
  /// **'将已有任务添加到本计划'**
  String get planDetailAddExistingTaskTitle;

  /// No description provided for @planDetailTaskUnassigned.
  ///
  /// In zh, this message translates to:
  /// **'未分配'**
  String get planDetailTaskUnassigned;

  /// No description provided for @planDetailTaskInAnotherPlan.
  ///
  /// In zh, this message translates to:
  /// **'当前在其他计划中'**
  String get planDetailTaskInAnotherPlan;

  /// No description provided for @planDetailGroupUnassigned.
  ///
  /// In zh, this message translates to:
  /// **'未分配的任务'**
  String get planDetailGroupUnassigned;

  /// No description provided for @planDetailGroupOtherPlans.
  ///
  /// In zh, this message translates to:
  /// **'来自其他计划的任务'**
  String get planDetailGroupOtherPlans;

  /// No description provided for @planDetailTaskAdded.
  ///
  /// In zh, this message translates to:
  /// **'任务已添加到计划'**
  String get planDetailTaskAdded;

  /// No description provided for @planDetailAddTaskFailed.
  ///
  /// In zh, this message translates to:
  /// **'添加任务失败: {error}'**
  String planDetailAddTaskFailed(Object error);

  /// No description provided for @planDetailDayLabel.
  ///
  /// In zh, this message translates to:
  /// **'第 {day} 天'**
  String planDetailDayLabel(Object day);

  /// No description provided for @planDetailWeightedProgress.
  ///
  /// In zh, this message translates to:
  /// **'加权进度 {percent}%'**
  String planDetailWeightedProgress(Object percent);

  /// No description provided for @planDetailCreatePhaseTitle.
  ///
  /// In zh, this message translates to:
  /// **'创建阶段'**
  String get planDetailCreatePhaseTitle;

  /// No description provided for @planDetailPhaseNameLabel.
  ///
  /// In zh, this message translates to:
  /// **'阶段名称'**
  String get planDetailPhaseNameLabel;

  /// No description provided for @planDetailPhaseNameHint.
  ///
  /// In zh, this message translates to:
  /// **'基础 / 构建 / 复习'**
  String get planDetailPhaseNameHint;

  /// No description provided for @planDetailPhaseCreated.
  ///
  /// In zh, this message translates to:
  /// **'阶段已创建'**
  String get planDetailPhaseCreated;

  /// No description provided for @planDetailCreatePhaseFailed.
  ///
  /// In zh, this message translates to:
  /// **'创建阶段失败: {error}'**
  String planDetailCreatePhaseFailed(Object error);

  /// No description provided for @planDetailPhaseActivated.
  ///
  /// In zh, this message translates to:
  /// **'阶段已激活'**
  String get planDetailPhaseActivated;

  /// No description provided for @planDetailActivatePhaseFailed.
  ///
  /// In zh, this message translates to:
  /// **'激活失败: {error}'**
  String planDetailActivatePhaseFailed(Object error);

  /// No description provided for @planDetailPhaseNeedsFeedback.
  ///
  /// In zh, this message translates to:
  /// **'此阶段需要反馈后才能推进'**
  String get planDetailPhaseNeedsFeedback;

  /// No description provided for @planDetailPhaseCompleted.
  ///
  /// In zh, this message translates to:
  /// **'阶段已完成'**
  String get planDetailPhaseCompleted;

  /// No description provided for @planDetailCompletePhaseFailed.
  ///
  /// In zh, this message translates to:
  /// **'完成阶段失败: {error}'**
  String planDetailCompletePhaseFailed(Object error);

  /// No description provided for @planDetailPhaseFeedbackTitle.
  ///
  /// In zh, this message translates to:
  /// **'阶段反馈 · {title}'**
  String planDetailPhaseFeedbackTitle(Object title);

  /// No description provided for @planDetailPhaseAlignmentQuestion.
  ///
  /// In zh, this message translates to:
  /// **'你觉得这个阶段的契合度如何？'**
  String get planDetailPhaseAlignmentQuestion;

  /// No description provided for @planDetailPhaseReflectionLabel.
  ///
  /// In zh, this message translates to:
  /// **'反思'**
  String get planDetailPhaseReflectionLabel;

  /// No description provided for @planDetailPhaseReflectionHint.
  ///
  /// In zh, this message translates to:
  /// **'哪些做得好，哪些失败了，发生了什么变化？'**
  String get planDetailPhaseReflectionHint;

  /// No description provided for @planDetailPhaseBlocked.
  ///
  /// In zh, this message translates to:
  /// **'我在这个阶段遇到了阻碍'**
  String get planDetailPhaseBlocked;

  /// No description provided for @planDetailPhaseLifeChanged.
  ///
  /// In zh, this message translates to:
  /// **'我的生活状况发生了变化'**
  String get planDetailPhaseLifeChanged;

  /// No description provided for @planDetailPhaseRequestReview.
  ///
  /// In zh, this message translates to:
  /// **'请求 compass 审阅'**
  String get planDetailPhaseRequestReview;

  /// No description provided for @planDetailPhaseActivate.
  ///
  /// In zh, this message translates to:
  /// **'激活'**
  String get planDetailPhaseActivate;

  /// No description provided for @planDetailPhaseComplete.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get planDetailPhaseComplete;

  /// No description provided for @planDetailPhaseFeedback.
  ///
  /// In zh, this message translates to:
  /// **'反馈'**
  String get planDetailPhaseFeedback;

  /// No description provided for @planDetailFeedbackSavedWithReview.
  ///
  /// In zh, this message translates to:
  /// **'反馈已保存，已建议 compass 审阅'**
  String get planDetailFeedbackSavedWithReview;

  /// No description provided for @planDetailFeedbackSaved.
  ///
  /// In zh, this message translates to:
  /// **'反馈已保存'**
  String get planDetailFeedbackSaved;

  /// No description provided for @planDetailSubmitFeedbackFailed.
  ///
  /// In zh, this message translates to:
  /// **'提交反馈失败: {error}'**
  String planDetailSubmitFeedbackFailed(Object error);

  /// No description provided for @planDetailPhaseStats.
  ///
  /// In zh, this message translates to:
  /// **'{progress}% · {completed}/{occurrences} 次发生 · {tasks} 个任务'**
  String planDetailPhaseStats(
      Object progress, Object completed, Object occurrences, Object tasks);

  /// No description provided for @theaterTitle.
  ///
  /// In zh, this message translates to:
  /// **'知识推演剧场'**
  String get theaterTitle;

  /// No description provided for @theaterContinuityBanner.
  ///
  /// In zh, this message translates to:
  /// **'这次推演承接了你刚才的探索流程。你可以随时回到原对话，继续追问路径、风险和具体行动。'**
  String get theaterContinuityBanner;

  /// No description provided for @theaterShareTopic.
  ///
  /// In zh, this message translates to:
  /// **'推演主题：{topic}'**
  String theaterShareTopic(Object topic);

  /// No description provided for @theaterShareMessage.
  ///
  /// In zh, this message translates to:
  /// **'我刚在 Sparkle 推演了一条学习路径：{topic}\n{route}\n{suggestion}'**
  String theaterShareMessage(Object route, Object suggestion, Object topic);

  /// No description provided for @theaterShareSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'先把关键节点和风险看清楚，再决定怎么学。'**
  String get theaterShareSuggestion;

  /// No description provided for @theaterRecordActualTitle.
  ///
  /// In zh, this message translates to:
  /// **'记录 7 天后的真实表现'**
  String get theaterRecordActualTitle;

  /// No description provided for @theaterRecordActualDesc.
  ///
  /// In zh, this message translates to:
  /// **'回填真实完成率和掌握度后，剧场会给你一份预测校准反馈。'**
  String get theaterRecordActualDesc;

  /// No description provided for @theaterActualCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'真实完成率'**
  String get theaterActualCompletionRate;

  /// No description provided for @theaterActualMastery.
  ///
  /// In zh, this message translates to:
  /// **'真实掌握度'**
  String get theaterActualMastery;

  /// No description provided for @theaterSubmitCalibration.
  ///
  /// In zh, this message translates to:
  /// **'提交校准'**
  String get theaterSubmitCalibration;

  /// No description provided for @theaterNodeDescriptionFallback.
  ///
  /// In zh, this message translates to:
  /// **'这个节点是当前推演中的关键知识点。'**
  String get theaterNodeDescriptionFallback;

  /// No description provided for @theaterNodeCurrentMastery.
  ///
  /// In zh, this message translates to:
  /// **'当前掌握度'**
  String get theaterNodeCurrentMastery;

  /// No description provided for @theaterNodePredictedMastery.
  ///
  /// In zh, this message translates to:
  /// **'预测掌握度'**
  String get theaterNodePredictedMastery;

  /// No description provided for @theaterNodeDelta.
  ///
  /// In zh, this message translates to:
  /// **'变化'**
  String get theaterNodeDelta;

  /// No description provided for @theaterNodeRisk.
  ///
  /// In zh, this message translates to:
  /// **'风险'**
  String get theaterNodeRisk;

  /// No description provided for @theaterNodeRoleInPath.
  ///
  /// In zh, this message translates to:
  /// **'它在当前路径里的作用'**
  String get theaterNodeRoleInPath;

  /// No description provided for @theaterNodeStepLabel.
  ///
  /// In zh, this message translates to:
  /// **'{dayLabel} · 第 {index} 步'**
  String theaterNodeStepLabel(Object dayLabel, Object index);

  /// No description provided for @theaterNodeNextAction.
  ///
  /// In zh, this message translates to:
  /// **'下一步动作：先用约 {minutes} 分钟处理这个节点，再进入后续步骤。'**
  String theaterNodeNextAction(Object minutes);

  /// No description provided for @theaterWhatIfStart.
  ///
  /// In zh, this message translates to:
  /// **'开始假设推演'**
  String get theaterWhatIfStart;

  /// No description provided for @theaterViewGalaxyRef.
  ///
  /// In zh, this message translates to:
  /// **'查看星图参考'**
  String get theaterViewGalaxyRef;

  /// No description provided for @theaterNodeNotInWhatIfPath.
  ///
  /// In zh, this message translates to:
  /// **'这个节点当前不在已选路径的可推演步骤里，所以暂时不能直接做假设推演。'**
  String get theaterNodeNotInWhatIfPath;

  /// No description provided for @theaterNodeNoGalaxyRef.
  ///
  /// In zh, this message translates to:
  /// **'这个节点目前是剧场里的自由节点，还没有可跳转的知识星图参考项。'**
  String get theaterNodeNoGalaxyRef;

  /// No description provided for @theaterPromoteNodeFailed.
  ///
  /// In zh, this message translates to:
  /// **'加入知识星图失败，请稍后再试。'**
  String get theaterPromoteNodeFailed;

  /// No description provided for @theaterPromoteNodeCreated.
  ///
  /// In zh, this message translates to:
  /// **'已将「{nodeName}」加入知识星图，可以继续完善节点内容。'**
  String theaterPromoteNodeCreated(Object nodeName);

  /// No description provided for @theaterPromoteNodeFound.
  ///
  /// In zh, this message translates to:
  /// **'已定位到知识星图中的「{nodeName}」，你可以继续完善节点内容。'**
  String theaterPromoteNodeFound(Object nodeName);

  /// No description provided for @theaterGoImprove.
  ///
  /// In zh, this message translates to:
  /// **'去完善'**
  String get theaterGoImprove;

  /// No description provided for @theaterEdgeStrength.
  ///
  /// In zh, this message translates to:
  /// **'关系强度 {strength}%'**
  String theaterEdgeStrength(Object strength);

  /// No description provided for @theaterRiskHigh.
  ///
  /// In zh, this message translates to:
  /// **'高风险'**
  String get theaterRiskHigh;

  /// No description provided for @theaterRiskMedium.
  ///
  /// In zh, this message translates to:
  /// **'中风险'**
  String get theaterRiskMedium;

  /// No description provided for @theaterRiskLow.
  ///
  /// In zh, this message translates to:
  /// **'低风险'**
  String get theaterRiskLow;

  /// No description provided for @theaterRelationPrerequisite.
  ///
  /// In zh, this message translates to:
  /// **'前置依赖'**
  String get theaterRelationPrerequisite;

  /// No description provided for @theaterRelationExplains.
  ///
  /// In zh, this message translates to:
  /// **'解释关系'**
  String get theaterRelationExplains;

  /// No description provided for @theaterRelationSupports.
  ///
  /// In zh, this message translates to:
  /// **'支持关系'**
  String get theaterRelationSupports;

  /// No description provided for @theaterRelationContradicts.
  ///
  /// In zh, this message translates to:
  /// **'矛盾关系'**
  String get theaterRelationContradicts;

  /// No description provided for @theaterSelectedNode.
  ///
  /// In zh, this message translates to:
  /// **'已选节点 · {nodeName}'**
  String theaterSelectedNode(Object nodeName);

  /// No description provided for @theaterNodeTapHint.
  ///
  /// In zh, this message translates to:
  /// **'点击节点可查看详细推演说明。'**
  String get theaterNodeTapHint;

  /// No description provided for @theaterNodeStatCurrent.
  ///
  /// In zh, this message translates to:
  /// **'当前'**
  String get theaterNodeStatCurrent;

  /// No description provided for @theaterNodeStatPredicted.
  ///
  /// In zh, this message translates to:
  /// **'预测'**
  String get theaterNodeStatPredicted;

  /// No description provided for @theaterNodeStatLift.
  ///
  /// In zh, this message translates to:
  /// **'提升'**
  String get theaterNodeStatLift;

  /// No description provided for @theaterNodeStatSource.
  ///
  /// In zh, this message translates to:
  /// **'来源'**
  String get theaterNodeStatSource;

  /// No description provided for @theaterComposerEyebrow.
  ///
  /// In zh, this message translates to:
  /// **'推演决策面板'**
  String get theaterComposerEyebrow;

  /// No description provided for @theaterComposerTitle.
  ///
  /// In zh, this message translates to:
  /// **'先定目标，再看清多条路径'**
  String get theaterComposerTitle;

  /// No description provided for @theaterComposerSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'先确定想推进的目标，再比较切入方式、主要风险和每日投入，最后决定要不要采纳这条路径。'**
  String get theaterComposerSubtitle;

  /// No description provided for @theaterComposerCurrentTarget.
  ///
  /// In zh, this message translates to:
  /// **'当前目标'**
  String get theaterComposerCurrentTarget;

  /// No description provided for @theaterComposerWaitingInput.
  ///
  /// In zh, this message translates to:
  /// **'等待输入'**
  String get theaterComposerWaitingInput;

  /// No description provided for @theaterComposerRecommendedEntry.
  ///
  /// In zh, this message translates to:
  /// **'推荐切入'**
  String get theaterComposerRecommendedEntry;

  /// No description provided for @theaterComposerInputPrompt.
  ///
  /// In zh, this message translates to:
  /// **'输入后即可开始'**
  String get theaterComposerInputPrompt;

  /// No description provided for @theaterComposerOutput.
  ///
  /// In zh, this message translates to:
  /// **'输出结果'**
  String get theaterComposerOutput;

  /// No description provided for @theaterComposerOutputDesc.
  ///
  /// In zh, this message translates to:
  /// **'路径 + 风险 + 检查点'**
  String get theaterComposerOutputDesc;

  /// No description provided for @theaterComposerLoading.
  ///
  /// In zh, this message translates to:
  /// **'推演中...'**
  String get theaterComposerLoading;

  /// No description provided for @theaterComposerStart.
  ///
  /// In zh, this message translates to:
  /// **'开始推演'**
  String get theaterComposerStart;

  /// No description provided for @theaterComposerTrySuggestion.
  ///
  /// In zh, this message translates to:
  /// **'试试 {topic}'**
  String theaterComposerTrySuggestion(Object topic);

  /// No description provided for @theaterComposerHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：两周内掌握线性代数的特征值部分'**
  String get theaterComposerHint;

  /// No description provided for @theaterComposerGenerating.
  ///
  /// In zh, this message translates to:
  /// **'生成'**
  String get theaterComposerGenerating;

  /// No description provided for @theaterTopBarAdjustTarget.
  ///
  /// In zh, this message translates to:
  /// **'调整目标'**
  String get theaterTopBarAdjustTarget;

  /// No description provided for @theaterTopBarShare.
  ///
  /// In zh, this message translates to:
  /// **'分享推演'**
  String get theaterTopBarShare;

  /// No description provided for @theaterTopBarNoGalaxyRef.
  ///
  /// In zh, this message translates to:
  /// **'当前没有可打开的知识星图参考节点'**
  String get theaterTopBarNoGalaxyRef;

  /// No description provided for @theaterTopBarViewGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'查看知识星图'**
  String get theaterTopBarViewGalaxy;

  /// No description provided for @theaterTopBarTarget.
  ///
  /// In zh, this message translates to:
  /// **'目标 · {name}'**
  String theaterTopBarTarget(Object name);

  /// No description provided for @theaterTopBarPath.
  ///
  /// In zh, this message translates to:
  /// **'路径 · {title}'**
  String theaterTopBarPath(Object title);

  /// No description provided for @theaterTopBarMode.
  ///
  /// In zh, this message translates to:
  /// **'模式 · {mode}'**
  String theaterTopBarMode(Object mode);

  /// No description provided for @theaterTopBarRefMap.
  ///
  /// In zh, this message translates to:
  /// **'参考映射 {count}'**
  String theaterTopBarRefMap(Object count);

  /// No description provided for @theaterTopBarFreeForm.
  ///
  /// In zh, this message translates to:
  /// **'纯自由推演'**
  String get theaterTopBarFreeForm;

  /// No description provided for @theaterTopBarMastery.
  ///
  /// In zh, this message translates to:
  /// **'掌握度 {value}%'**
  String theaterTopBarMastery(Object value);

  /// No description provided for @theaterSettingsTitle.
  ///
  /// In zh, this message translates to:
  /// **'调整推演目标'**
  String get theaterSettingsTitle;

  /// No description provided for @theaterSettingsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'这里可以重新设定目标和建议起点，收起后会把舞台空间完整还给关系图谱与讨论流。'**
  String get theaterSettingsSubtitle;

  /// No description provided for @theaterSettingsContinuity.
  ///
  /// In zh, this message translates to:
  /// **'这次推演仍然承接你刚才的对话上下文。'**
  String get theaterSettingsContinuity;

  /// No description provided for @theaterSettingsCurrentTarget.
  ///
  /// In zh, this message translates to:
  /// **'当前目标：{name}'**
  String theaterSettingsCurrentTarget(Object name);

  /// No description provided for @theaterSettingsLabel.
  ///
  /// In zh, this message translates to:
  /// **'重新设定推演目标'**
  String get theaterSettingsLabel;

  /// No description provided for @theaterSettingsHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：两周内掌握线性代数的特征值部分'**
  String get theaterSettingsHint;

  /// No description provided for @theaterSettingsGenerate.
  ///
  /// In zh, this message translates to:
  /// **'生成新推演'**
  String get theaterSettingsGenerate;

  /// No description provided for @theaterSettingsSuggestions.
  ///
  /// In zh, this message translates to:
  /// **'建议起点'**
  String get theaterSettingsSuggestions;

  /// No description provided for @theaterTabGraph.
  ///
  /// In zh, this message translates to:
  /// **'图谱'**
  String get theaterTabGraph;

  /// No description provided for @theaterTabPaths.
  ///
  /// In zh, this message translates to:
  /// **'路径'**
  String get theaterTabPaths;

  /// No description provided for @theaterTabDiscussion.
  ///
  /// In zh, this message translates to:
  /// **'讨论'**
  String get theaterTabDiscussion;

  /// No description provided for @theaterTabCalibration.
  ///
  /// In zh, this message translates to:
  /// **'校准'**
  String get theaterTabCalibration;

  /// No description provided for @theaterIntroChangeTarget.
  ///
  /// In zh, this message translates to:
  /// **'换个目标'**
  String get theaterIntroChangeTarget;

  /// No description provided for @theaterIntroTitle.
  ///
  /// In zh, this message translates to:
  /// **'选一个目标，AI 帮你看清多条路径'**
  String get theaterIntroTitle;

  /// No description provided for @theaterIntroSteps.
  ///
  /// In zh, this message translates to:
  /// **'1. 选择一个目标\n2. AI 推演多条学习路径\n3. 采纳最适合你的方案并同步到 Sprint'**
  String get theaterIntroSteps;

  /// No description provided for @theaterIntroStartFirst.
  ///
  /// In zh, this message translates to:
  /// **'开始第一次推演'**
  String get theaterIntroStartFirst;

  /// No description provided for @theaterIntroLastSnapshot.
  ///
  /// In zh, this message translates to:
  /// **'最近一次推演'**
  String get theaterIntroLastSnapshot;

  /// No description provided for @theaterIntroSuggestions.
  ///
  /// In zh, this message translates to:
  /// **'从这些主题开始更顺手'**
  String get theaterIntroSuggestions;

  /// No description provided for @theaterEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'这次还没生成可采纳路径'**
  String get theaterEmptyTitle;

  /// No description provided for @theaterEmptyMessage.
  ///
  /// In zh, this message translates to:
  /// **'系统完成了主题解析，但暂时没能收束出可执行路线。你可以换个更具体的目标，或者稍后再试一次。'**
  String get theaterEmptyMessage;

  /// No description provided for @theaterGraphRecommended.
  ///
  /// In zh, this message translates to:
  /// **'推荐路径 · {title}'**
  String theaterGraphRecommended(Object title);

  /// No description provided for @theaterGraphEstimatedMastery.
  ///
  /// In zh, this message translates to:
  /// **'预计掌握 {value}%'**
  String theaterGraphEstimatedMastery(Object value);

  /// No description provided for @theaterGraphRisk.
  ///
  /// In zh, this message translates to:
  /// **'风险 · {risk}'**
  String theaterGraphRisk(Object risk);

  /// No description provided for @theaterGraphMode.
  ///
  /// In zh, this message translates to:
  /// **'模式 · {mode}'**
  String theaterGraphMode(Object mode);

  /// No description provided for @theaterGraphRefCount.
  ///
  /// In zh, this message translates to:
  /// **'映射参考 {count}'**
  String theaterGraphRefCount(Object count);

  /// No description provided for @theaterGraphPendingEntry.
  ///
  /// In zh, this message translates to:
  /// **'候选待入图'**
  String get theaterGraphPendingEntry;

  /// No description provided for @theaterGraphNodeCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个节点'**
  String theaterGraphNodeCount(Object count);

  /// No description provided for @theaterGraphMainStage.
  ///
  /// In zh, this message translates to:
  /// **'关系图谱主舞台'**
  String get theaterGraphMainStage;

  /// No description provided for @theaterGraphWithGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'含星图参考'**
  String get theaterGraphWithGalaxy;

  /// No description provided for @theaterGraphStandalone.
  ///
  /// In zh, this message translates to:
  /// **'独立自由图谱'**
  String get theaterGraphStandalone;

  /// No description provided for @theaterGraphInstructions.
  ///
  /// In zh, this message translates to:
  /// **'单指拖动画布，双指缩放，双击可回正，点按节点可查看详情并加入知识星图。'**
  String get theaterGraphInstructions;

  /// No description provided for @theaterCalibrationTitle.
  ///
  /// In zh, this message translates to:
  /// **'校准与落地'**
  String get theaterCalibrationTitle;

  /// No description provided for @theaterCalibrationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把推演变成计划、快照和真实反馈，形成闭环。'**
  String get theaterCalibrationSubtitle;

  /// No description provided for @theaterRetry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get theaterRetry;

  /// No description provided for @theaterGotIt.
  ///
  /// In zh, this message translates to:
  /// **'知道了'**
  String get theaterGotIt;

  /// No description provided for @theaterSemanticMatchTitle.
  ///
  /// In zh, this message translates to:
  /// **'自由节点与星图参考'**
  String get theaterSemanticMatchTitle;

  /// No description provided for @theaterSemanticMatchItem.
  ///
  /// In zh, this message translates to:
  /// **'{freeform} 对应参考 {galaxy}'**
  String theaterSemanticMatchItem(Object freeform, Object galaxy);

  /// No description provided for @theaterLoadingTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在搭建这场推演...'**
  String get theaterLoadingTitle;

  /// No description provided for @theaterLoadingSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'图谱、路径和风险判断会按阶段依次完成，你可以先看它推进到哪一步了。'**
  String get theaterLoadingSubtitle;

  /// No description provided for @theaterStageBuildGraph.
  ///
  /// In zh, this message translates to:
  /// **'构建知识图谱'**
  String get theaterStageBuildGraph;

  /// No description provided for @theaterStageAnalyzePaths.
  ///
  /// In zh, this message translates to:
  /// **'分析学习路径'**
  String get theaterStageAnalyzePaths;

  /// No description provided for @theaterStageGenerateRisk.
  ///
  /// In zh, this message translates to:
  /// **'生成风险预测'**
  String get theaterStageGenerateRisk;

  /// No description provided for @theaterStagePrepare.
  ///
  /// In zh, this message translates to:
  /// **'准备推演完成'**
  String get theaterStagePrepare;

  /// No description provided for @theaterTimelineTitle.
  ///
  /// In zh, this message translates to:
  /// **'推演时间轴'**
  String get theaterTimelineTitle;

  /// No description provided for @theaterTimelineSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'现在可以按天拖动预测进度，直接对比基线路径和假设分支的差异。'**
  String get theaterTimelineSubtitle;

  /// No description provided for @theaterTimelinePause.
  ///
  /// In zh, this message translates to:
  /// **'暂停播放'**
  String get theaterTimelinePause;

  /// No description provided for @theaterTimelineAutoPlay.
  ///
  /// In zh, this message translates to:
  /// **'自动播放'**
  String get theaterTimelineAutoPlay;

  /// No description provided for @theaterTimelineReset.
  ///
  /// In zh, this message translates to:
  /// **'回到起点'**
  String get theaterTimelineReset;

  /// No description provided for @theaterTimelineCurrentPhase.
  ///
  /// In zh, this message translates to:
  /// **'当前阶段'**
  String get theaterTimelineCurrentPhase;

  /// No description provided for @theaterTimelineWaitingPath.
  ///
  /// In zh, this message translates to:
  /// **'等待路径生成'**
  String get theaterTimelineWaitingPath;

  /// No description provided for @theaterTimelineBaseline.
  ///
  /// In zh, this message translates to:
  /// **'基线预测'**
  String get theaterTimelineBaseline;

  /// No description provided for @theaterTimelineDiscussionHere.
  ///
  /// In zh, this message translates to:
  /// **'讲到这里'**
  String get theaterTimelineDiscussionHere;

  /// No description provided for @theaterTimelineMastery.
  ///
  /// In zh, this message translates to:
  /// **'当前预测掌握度'**
  String get theaterTimelineMastery;

  /// No description provided for @theaterTimelineCompletion.
  ///
  /// In zh, this message translates to:
  /// **'当前预测完成率'**
  String get theaterTimelineCompletion;

  /// No description provided for @theaterTimelinePhaseWithSteps.
  ///
  /// In zh, this message translates to:
  /// **'当前阶段：{label} · {step} · {compare}'**
  String theaterTimelinePhaseWithSteps(
      Object compare, Object label, Object step);

  /// No description provided for @theaterTimelineWaitingDeduction.
  ///
  /// In zh, this message translates to:
  /// **'等待推演'**
  String get theaterTimelineWaitingDeduction;

  /// No description provided for @theaterRouteList.
  ///
  /// In zh, this message translates to:
  /// **'列表'**
  String get theaterRouteList;

  /// No description provided for @theaterRouteCompare.
  ///
  /// In zh, this message translates to:
  /// **'对比'**
  String get theaterRouteCompare;

  /// No description provided for @theaterRouteComparisonTitle.
  ///
  /// In zh, this message translates to:
  /// **'路径对比'**
  String get theaterRouteComparisonTitle;

  /// No description provided for @theaterRouteAdoptedPlan.
  ///
  /// In zh, this message translates to:
  /// **'已创建计划：{planName}'**
  String theaterRouteAdoptedPlan(Object planName);

  /// No description provided for @theaterRouteFirstWeekTasks.
  ///
  /// In zh, this message translates to:
  /// **'首周任务：{tasks}'**
  String theaterRouteFirstWeekTasks(Object tasks);

  /// No description provided for @theaterRouteRiskControllable.
  ///
  /// In zh, this message translates to:
  /// **'整体可控'**
  String get theaterRouteRiskControllable;

  /// No description provided for @theaterRouteRiskPacing.
  ///
  /// In zh, this message translates to:
  /// **'需要留意节奏'**
  String get theaterRouteRiskPacing;

  /// No description provided for @theaterRouteEstimatedRange.
  ///
  /// In zh, this message translates to:
  /// **'预估 {low}-{high}%'**
  String theaterRouteEstimatedRange(Object high, Object low);

  /// No description provided for @theaterRouteDataQualityLow.
  ///
  /// In zh, this message translates to:
  /// **'参考估算'**
  String get theaterRouteDataQualityLow;

  /// No description provided for @theaterRouteDataQualityMedium.
  ///
  /// In zh, this message translates to:
  /// **'基于有限数据'**
  String get theaterRouteDataQualityMedium;

  /// No description provided for @theaterRouteDataQualityHigh.
  ///
  /// In zh, this message translates to:
  /// **'数据充分度 {score}%'**
  String theaterRouteDataQualityHigh(Object score);

  /// No description provided for @theaterRouteDataQualityFallback.
  ///
  /// In zh, this message translates to:
  /// **'数据参考'**
  String get theaterRouteDataQualityFallback;

  /// No description provided for @theaterRouteDataNoteLow.
  ///
  /// In zh, this message translates to:
  /// **'当前缺少该主题的真实学习记录，建议把区间估算当作参考，而不是精确预测。'**
  String get theaterRouteDataNoteLow;

  /// No description provided for @theaterRouteDataNoteMedium.
  ///
  /// In zh, this message translates to:
  /// **'当前只覆盖到部分图谱与校准数据，百分比判断仍需要继续观察。'**
  String get theaterRouteDataNoteMedium;

  /// No description provided for @theaterRouteModeAnchored.
  ///
  /// In zh, this message translates to:
  /// **'图谱锚定'**
  String get theaterRouteModeAnchored;

  /// No description provided for @theaterRouteModeHybrid.
  ///
  /// In zh, this message translates to:
  /// **'智能混合'**
  String get theaterRouteModeHybrid;

  /// No description provided for @theaterRouteModeFree.
  ///
  /// In zh, this message translates to:
  /// **'自由推演'**
  String get theaterRouteModeFree;

  /// No description provided for @theaterRouteModeDeducing.
  ///
  /// In zh, this message translates to:
  /// **'推演中'**
  String get theaterRouteModeDeducing;

  /// No description provided for @theaterNodeGalaxySyncing.
  ///
  /// In zh, this message translates to:
  /// **'同步中...'**
  String get theaterNodeGalaxySyncing;

  /// No description provided for @theaterNodeOpenGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'打开知识星图'**
  String get theaterNodeOpenGalaxy;

  /// No description provided for @theaterNodeAddToGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'加入知识星图'**
  String get theaterNodeAddToGalaxy;

  /// No description provided for @theaterNodeSourceExplicit.
  ///
  /// In zh, this message translates to:
  /// **'星图节点'**
  String get theaterNodeSourceExplicit;

  /// No description provided for @theaterNodeSourceHybrid.
  ///
  /// In zh, this message translates to:
  /// **'参考映射'**
  String get theaterNodeSourceHybrid;

  /// No description provided for @theaterNodeSourcePending.
  ///
  /// In zh, this message translates to:
  /// **'候选节点'**
  String get theaterNodeSourcePending;

  /// No description provided for @theaterNodeSourceFree.
  ///
  /// In zh, this message translates to:
  /// **'自由节点'**
  String get theaterNodeSourceFree;

  /// No description provided for @theaterNodeBannerOpenGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'这个节点已经对应到知识星图里的正式节点，可以直接打开并继续拓展。'**
  String get theaterNodeBannerOpenGalaxy;

  /// No description provided for @theaterNodeBannerHasMapping.
  ///
  /// In zh, this message translates to:
  /// **'这个自由节点已经找到星图参考，加入时会走统一创建链路，并补齐标准节点信息。'**
  String get theaterNodeBannerHasMapping;

  /// No description provided for @theaterNodeBannerFreeform.
  ///
  /// In zh, this message translates to:
  /// **'这个自由节点还未正式入图，加入后会自动补齐星域、位置、关系和解锁状态。'**
  String get theaterNodeBannerFreeform;

  /// No description provided for @theaterRouteRecommended.
  ///
  /// In zh, this message translates to:
  /// **'推荐'**
  String get theaterRouteRecommended;

  /// No description provided for @theaterRouteAdopting.
  ///
  /// In zh, this message translates to:
  /// **'采纳中'**
  String get theaterRouteAdopting;

  /// No description provided for @theaterRouteAdopt.
  ///
  /// In zh, this message translates to:
  /// **'采纳此路径'**
  String get theaterRouteAdopt;

  /// No description provided for @theaterRouteSimulate.
  ///
  /// In zh, this message translates to:
  /// **'带去模拟'**
  String get theaterRouteSimulate;

  /// No description provided for @theaterRouteCompletion.
  ///
  /// In zh, this message translates to:
  /// **'完成率 {value}'**
  String theaterRouteCompletion(Object value);

  /// No description provided for @theaterRouteMasteryLabel.
  ///
  /// In zh, this message translates to:
  /// **'掌握度 {value}'**
  String theaterRouteMasteryLabel(Object value);

  /// No description provided for @theaterRouteDailyMinutes.
  ///
  /// In zh, this message translates to:
  /// **'日均 {minutes} 分钟'**
  String theaterRouteDailyMinutes(Object minutes);

  /// No description provided for @theaterRouteRiskCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个风险点'**
  String theaterRouteRiskCount(Object count);

  /// No description provided for @theaterRouteScore.
  ///
  /// In zh, this message translates to:
  /// **'综合 {score} 分'**
  String theaterRouteScore(Object score);

  /// No description provided for @theaterRouteRangePrediction.
  ///
  /// In zh, this message translates to:
  /// **'区间预测：完成率 {completionLow}%-{completionHigh}%， 掌握度 {masteryLow}%-{masteryHigh}%'**
  String theaterRouteRangePrediction(Object completionHigh,
      Object completionLow, Object masteryHigh, Object masteryLow);

  /// No description provided for @theaterRouteRecommendedBaseline.
  ///
  /// In zh, this message translates to:
  /// **'推荐基线'**
  String get theaterRouteRecommendedBaseline;

  /// No description provided for @theaterRouteCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get theaterRouteCompletionRate;

  /// No description provided for @theaterRouteMasteryRate.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get theaterRouteMasteryRate;

  /// No description provided for @theaterRouteDailyTime.
  ///
  /// In zh, this message translates to:
  /// **'日均时间'**
  String get theaterRouteDailyTime;

  /// No description provided for @theaterRouteRiskLevel.
  ///
  /// In zh, this message translates to:
  /// **'风险数'**
  String get theaterRouteRiskLevel;

  /// No description provided for @theaterRouteOverallScore.
  ///
  /// In zh, this message translates to:
  /// **'综合分'**
  String get theaterRouteOverallScore;

  /// No description provided for @theaterRouteDataNote.
  ///
  /// In zh, this message translates to:
  /// **'数据说明'**
  String get theaterRouteDataNote;

  /// No description provided for @theaterRouteCompletionRange.
  ///
  /// In zh, this message translates to:
  /// **'完成率区间 {low}%-{high}%'**
  String theaterRouteCompletionRange(Object high, Object low);

  /// No description provided for @theaterRouteMasteryRange.
  ///
  /// In zh, this message translates to:
  /// **'掌握度区间 {low}%-{high}%'**
  String theaterRouteMasteryRange(Object high, Object low);

  /// No description provided for @theaterRouteSimulateFromCurrent.
  ///
  /// In zh, this message translates to:
  /// **'带去模拟'**
  String get theaterRouteSimulateFromCurrent;

  /// No description provided for @theaterRouteSimulateAfterSwitch.
  ///
  /// In zh, this message translates to:
  /// **'切换后模拟'**
  String get theaterRouteSimulateAfterSwitch;

  /// No description provided for @theaterRouteSwitchToThis.
  ///
  /// In zh, this message translates to:
  /// **'切换到此路径'**
  String get theaterRouteSwitchToThis;

  /// No description provided for @theaterRouteStepMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{dayLabel} · {minutes} 分钟'**
  String theaterRouteStepMinutes(Object dayLabel, Object minutes);

  /// No description provided for @theaterDismissTooltip.
  ///
  /// In zh, this message translates to:
  /// **'关闭提示'**
  String get theaterDismissTooltip;

  /// No description provided for @theaterCompactComparisonTitle.
  ///
  /// In zh, this message translates to:
  /// **'路径对比'**
  String get theaterCompactComparisonTitle;

  /// No description provided for @theaterCompactComparisonSummary.
  ///
  /// In zh, this message translates to:
  /// **'对照路径：{summary}'**
  String theaterCompactComparisonSummary(Object summary);

  /// No description provided for @theaterCompactComparisonCurrent.
  ///
  /// In zh, this message translates to:
  /// **'当前 · {title}'**
  String theaterCompactComparisonCurrent(Object title);

  /// No description provided for @theaterCompactComparisonMastery.
  ///
  /// In zh, this message translates to:
  /// **'掌握 {value}%'**
  String theaterCompactComparisonMastery(Object value);

  /// No description provided for @theaterCompactComparisonTime.
  ///
  /// In zh, this message translates to:
  /// **'时间 {minutes} 分/天'**
  String theaterCompactComparisonTime(Object minutes);

  /// No description provided for @theaterCompactComparisonAlt.
  ///
  /// In zh, this message translates to:
  /// **'对照 · {title}'**
  String theaterCompactComparisonAlt(Object title);

  /// No description provided for @theaterCompactOpenDetail.
  ///
  /// In zh, this message translates to:
  /// **'进入路径页细比'**
  String get theaterCompactOpenDetail;

  /// No description provided for @theaterCompactFallbackSingle.
  ///
  /// In zh, this message translates to:
  /// **'先聚焦 {name}。'**
  String theaterCompactFallbackSingle(Object name);

  /// No description provided for @theaterCompactFallbackMulti.
  ///
  /// In zh, this message translates to:
  /// **'先补 {first}，再推进 {last}。'**
  String theaterCompactFallbackMulti(Object first, Object last);

  /// No description provided for @theaterComparisonTitle.
  ///
  /// In zh, this message translates to:
  /// **'路径对比'**
  String get theaterComparisonTitle;

  /// No description provided for @theaterComparisonSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把当前方案和另一条代表性路径放在一起比较，更容易判断该走稳一点还是快一点。'**
  String get theaterComparisonSubtitle;

  /// No description provided for @theaterComparisonMetric.
  ///
  /// In zh, this message translates to:
  /// **'指标'**
  String get theaterComparisonMetric;

  /// No description provided for @theaterComparisonEstimatedMastery.
  ///
  /// In zh, this message translates to:
  /// **'预计掌握度'**
  String get theaterComparisonEstimatedMastery;

  /// No description provided for @theaterComparisonTimeInvestment.
  ///
  /// In zh, this message translates to:
  /// **'时间投入'**
  String get theaterComparisonTimeInvestment;

  /// No description provided for @theaterComparisonRiskLevel.
  ///
  /// In zh, this message translates to:
  /// **'风险等级'**
  String get theaterComparisonRiskLevel;

  /// No description provided for @theaterComparisonRiskLow.
  ///
  /// In zh, this message translates to:
  /// **'低'**
  String get theaterComparisonRiskLow;

  /// No description provided for @theaterComparisonRiskMediumHigh.
  ///
  /// In zh, this message translates to:
  /// **'中高'**
  String get theaterComparisonRiskMediumHigh;

  /// No description provided for @theaterComparisonRiskMedium.
  ///
  /// In zh, this message translates to:
  /// **'中'**
  String get theaterComparisonRiskMedium;

  /// No description provided for @theaterBranchDeltaTitle.
  ///
  /// In zh, this message translates to:
  /// **'假设分支对比'**
  String get theaterBranchDeltaTitle;

  /// No description provided for @theaterBranchDeltaPath.
  ///
  /// In zh, this message translates to:
  /// **'分支路径'**
  String get theaterBranchDeltaPath;

  /// No description provided for @theaterBranchDeltaWhatIf.
  ///
  /// In zh, this message translates to:
  /// **'假设推演'**
  String get theaterBranchDeltaWhatIf;

  /// No description provided for @theaterWhatIfTitle.
  ///
  /// In zh, this message translates to:
  /// **'What-if 沙盘'**
  String get theaterWhatIfTitle;

  /// No description provided for @theaterWhatIfSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'点选想跳过的节点，先看预计影响，再生成完整推演结果。'**
  String get theaterWhatIfSubtitle;

  /// No description provided for @theaterWhatIfPreviewTitle.
  ///
  /// In zh, this message translates to:
  /// **'预计影响预览'**
  String get theaterWhatIfPreviewTitle;

  /// No description provided for @theaterWhatIfPreviewMastery.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get theaterWhatIfPreviewMastery;

  /// No description provided for @theaterWhatIfPreviewCompletion.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get theaterWhatIfPreviewCompletion;

  /// No description provided for @theaterWhatIfNoNodesSelected.
  ///
  /// In zh, this message translates to:
  /// **'当前没有标记跳过节点，保持原始路径。'**
  String get theaterWhatIfNoNodesSelected;

  /// No description provided for @theaterWhatIfNodesSkipped.
  ///
  /// In zh, this message translates to:
  /// **'你已标记跳过 {nodes}。'**
  String theaterWhatIfNodesSkipped(Object nodes);

  /// No description provided for @theaterWhatIfSelectFirst.
  ///
  /// In zh, this message translates to:
  /// **'先选择一个节点'**
  String get theaterWhatIfSelectFirst;

  /// No description provided for @theaterWhatIfGenerateFull.
  ///
  /// In zh, this message translates to:
  /// **'生成完整假设推演结果'**
  String get theaterWhatIfGenerateFull;

  /// No description provided for @theaterWhatIfOriginal.
  ///
  /// In zh, this message translates to:
  /// **'原始 {original}'**
  String theaterWhatIfOriginal(Object original);

  /// No description provided for @theaterWhatIfAdjusted.
  ///
  /// In zh, this message translates to:
  /// **'调整后 {adjusted}'**
  String theaterWhatIfAdjusted(Object adjusted);

  /// No description provided for @theaterWhatIfRemainingPath.
  ///
  /// In zh, this message translates to:
  /// **'分支剩余路径：{path}'**
  String theaterWhatIfRemainingPath(Object path);

  /// No description provided for @theaterDiscussionTitle.
  ///
  /// In zh, this message translates to:
  /// **'专家圆桌'**
  String get theaterDiscussionTitle;

  /// No description provided for @theaterSnapshotSaving.
  ///
  /// In zh, this message translates to:
  /// **'保存中'**
  String get theaterSnapshotSaving;

  /// No description provided for @theaterSnapshotSave.
  ///
  /// In zh, this message translates to:
  /// **'保存当前快照'**
  String get theaterSnapshotSave;

  /// No description provided for @theaterSnapshotTitle.
  ///
  /// In zh, this message translates to:
  /// **'保存当前快照'**
  String get theaterSnapshotTitle;

  /// No description provided for @theaterSnapshotNoSnapshot.
  ///
  /// In zh, this message translates to:
  /// **'把当前推演保存下来，稍后可以继续回看。'**
  String get theaterSnapshotNoSnapshot;

  /// No description provided for @theaterSnapshotSaved.
  ///
  /// In zh, this message translates to:
  /// **'已保存：{title}'**
  String theaterSnapshotSaved(Object title);

  /// No description provided for @theaterAccuracyTitle.
  ///
  /// In zh, this message translates to:
  /// **'预测校准'**
  String get theaterAccuracyTitle;

  /// No description provided for @theaterAccuracyWithinRange.
  ///
  /// In zh, this message translates to:
  /// **'这次真实结果落在预测区间内，当前模型区间覆盖命中。'**
  String get theaterAccuracyWithinRange;

  /// No description provided for @theaterAccuracyOutsideRange.
  ///
  /// In zh, this message translates to:
  /// **'这次真实结果落在预测区间外，系统会用这次偏差继续校准后续预测。'**
  String get theaterAccuracyOutsideRange;

  /// No description provided for @theaterAccuracyDueDate.
  ///
  /// In zh, this message translates to:
  /// **'建议回填日期：{date}'**
  String theaterAccuracyDueDate(Object date);

  /// No description provided for @theaterAccuracyRecordActual.
  ///
  /// In zh, this message translates to:
  /// **'记录实际表现'**
  String get theaterAccuracyRecordActual;

  /// No description provided for @theaterAccuracySampleCount.
  ///
  /// In zh, this message translates to:
  /// **'样本 {count}'**
  String theaterAccuracySampleCount(Object count);

  /// No description provided for @theaterAccuracyAvgScore.
  ///
  /// In zh, this message translates to:
  /// **'平均准确度 {score}%'**
  String theaterAccuracyAvgScore(Object score);

  /// No description provided for @theaterAccuracyConfidenceScore.
  ///
  /// In zh, this message translates to:
  /// **'数据充分度 {score}%'**
  String theaterAccuracyConfidenceScore(Object score);

  /// No description provided for @theaterAccuracyCoverageRate.
  ///
  /// In zh, this message translates to:
  /// **'区间命中 {rate}%'**
  String theaterAccuracyCoverageRate(Object rate);

  /// No description provided for @theaterAccuracyScoreNote.
  ///
  /// In zh, this message translates to:
  /// **'数据充分度反映当前预测所依据的数据量和校准次数，不是预测准确度。'**
  String get theaterAccuracyScoreNote;

  /// No description provided for @theaterAccuracyNoSamples.
  ///
  /// In zh, this message translates to:
  /// **'还没有历史回填样本，当前预测会优先展示区间而不是绝对值。'**
  String get theaterAccuracyNoSamples;

  /// No description provided for @theaterAccuracyHistoryBias.
  ///
  /// In zh, this message translates to:
  /// **'历史偏差：完成率 {completionBias}%， 掌握度 {masteryBias}%。'**
  String theaterAccuracyHistoryBias(Object completionBias, Object masteryBias);

  /// No description provided for @theaterAdoptionSynced.
  ///
  /// In zh, this message translates to:
  /// **'已同步到你的 Sprint'**
  String get theaterAdoptionSynced;

  /// No description provided for @theaterAdoptionFirstWeekTasks.
  ///
  /// In zh, this message translates to:
  /// **'首周任务'**
  String get theaterAdoptionFirstWeekTasks;

  /// No description provided for @theaterAdoptionCheckpoints.
  ///
  /// In zh, this message translates to:
  /// **'检查点：{dates}'**
  String theaterAdoptionCheckpoints(Object dates);

  /// No description provided for @theaterAdoptionViewPlan.
  ///
  /// In zh, this message translates to:
  /// **'查看计划'**
  String get theaterAdoptionViewPlan;

  /// No description provided for @theaterAdoptionContinueExploring.
  ///
  /// In zh, this message translates to:
  /// **'继续探索'**
  String get theaterAdoptionContinueExploring;

  /// No description provided for @planCreateEditingGrowth.
  ///
  /// In zh, this message translates to:
  /// **'编辑成长计划'**
  String get planCreateEditingGrowth;

  /// No description provided for @planCreateEditingSprint.
  ///
  /// In zh, this message translates to:
  /// **'编辑冲刺计划'**
  String get planCreateEditingSprint;

  /// No description provided for @planCreateSavePlan.
  ///
  /// In zh, this message translates to:
  /// **'保存计划'**
  String get planCreateSavePlan;

  /// No description provided for @planCreateStepPositioning.
  ///
  /// In zh, this message translates to:
  /// **'计划定位'**
  String get planCreateStepPositioning;

  /// No description provided for @planCreateStepTimeStructure.
  ///
  /// In zh, this message translates to:
  /// **'时间结构'**
  String get planCreateStepTimeStructure;

  /// No description provided for @planCreateStepTaskBlueprint.
  ///
  /// In zh, this message translates to:
  /// **'任务编排'**
  String get planCreateStepTaskBlueprint;

  /// No description provided for @planCreateStepBoundariesGuide.
  ///
  /// In zh, this message translates to:
  /// **'计划边界与指南'**
  String get planCreateStepBoundariesGuide;

  /// No description provided for @planCreateStepReviewConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确认预览'**
  String get planCreateStepReviewConfirm;

  /// No description provided for @planCreateBasicsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'先定义这是一张真正的计划卡，而不是普通任务。'**
  String get planCreateBasicsSubtitle;

  /// No description provided for @planCreateNameHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：6 周英语口语提升 / 期中冲刺收束'**
  String get planCreateNameHint;

  /// No description provided for @planCreateSubjectLabel.
  ///
  /// In zh, this message translates to:
  /// **'主题方向'**
  String get planCreateSubjectLabel;

  /// No description provided for @planCreateSubjectHint.
  ///
  /// In zh, this message translates to:
  /// **'英语、Flutter、考研数学、论文阅读...'**
  String get planCreateSubjectHint;

  /// No description provided for @planCreateGrowthGoalLabel.
  ///
  /// In zh, this message translates to:
  /// **'长期目标'**
  String get planCreateGrowthGoalLabel;

  /// No description provided for @planCreateSprintGoalLabel.
  ///
  /// In zh, this message translates to:
  /// **'冲刺目标'**
  String get planCreateSprintGoalLabel;

  /// No description provided for @planCreateGrowthGoalHint.
  ///
  /// In zh, this message translates to:
  /// **'写清楚这个成长计划最终想形成什么能力、习惯或成果。'**
  String get planCreateGrowthGoalHint;

  /// No description provided for @planCreateSprintGoalHint.
  ///
  /// In zh, this message translates to:
  /// **'写清楚这次冲刺的结果、验收标准和不能偏离的主线。'**
  String get planCreateSprintGoalHint;

  /// No description provided for @planCreateGoalRequired.
  ///
  /// In zh, this message translates to:
  /// **'请写出这张计划卡的目标'**
  String get planCreateGoalRequired;

  /// No description provided for @planCreateScheduleSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把持续时间、每日投入和提醒节奏一次性定清楚。'**
  String get planCreateScheduleSubtitle;

  /// No description provided for @planCreateDailyMinutesLabel.
  ///
  /// In zh, this message translates to:
  /// **'每日可投入时长'**
  String get planCreateDailyMinutesLabel;

  /// No description provided for @planCreateTotalEstimatedHours.
  ///
  /// In zh, this message translates to:
  /// **'总预估工时 {hours} 小时'**
  String planCreateTotalEstimatedHours(Object hours);

  /// No description provided for @planCreateDailyReminderTime.
  ///
  /// In zh, this message translates to:
  /// **'每日提醒时间'**
  String get planCreateDailyReminderTime;

  /// No description provided for @planCreatePlanStageLabel.
  ///
  /// In zh, this message translates to:
  /// **'当前计划阶段'**
  String get planCreatePlanStageLabel;

  /// No description provided for @planCreateStageSprint.
  ///
  /// In zh, this message translates to:
  /// **'冲刺推进'**
  String get planCreateStageSprint;

  /// No description provided for @planCreateStageDaily.
  ///
  /// In zh, this message translates to:
  /// **'日常执行'**
  String get planCreateStageDaily;

  /// No description provided for @planCreateStageReview.
  ///
  /// In zh, this message translates to:
  /// **'复盘调优'**
  String get planCreateStageReview;

  /// No description provided for @planCreateStagePaused.
  ///
  /// In zh, this message translates to:
  /// **'暂时暂停'**
  String get planCreateStagePaused;

  /// No description provided for @planCreateScheduleChipWorkday.
  ///
  /// In zh, this message translates to:
  /// **'工作日推进，周末复盘'**
  String get planCreateScheduleChipWorkday;

  /// No description provided for @planCreateScheduleChipMorning.
  ///
  /// In zh, this message translates to:
  /// **'早晨启动，晚上收束'**
  String get planCreateScheduleChipMorning;

  /// No description provided for @planCreateScheduleChipAfternoon.
  ///
  /// In zh, this message translates to:
  /// **'午后主攻，夜间轻复盘'**
  String get planCreateScheduleChipAfternoon;

  /// No description provided for @planCreateScheduleLabel.
  ///
  /// In zh, this message translates to:
  /// **'节奏说明'**
  String get planCreateScheduleLabel;

  /// No description provided for @planCreateScheduleHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：周一到周五推进，周六复盘，周日补缺'**
  String get planCreateScheduleHint;

  /// No description provided for @planCreateTasksSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'这一步决定计划实际会承载哪些动作。已有任务先做参考，新任务会真正归属到计划下。'**
  String get planCreateTasksSubtitle;

  /// No description provided for @planCreateTaskBlueprintLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务编排说明'**
  String get planCreateTaskBlueprintLabel;

  /// No description provided for @planCreateTaskBlueprintHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：先搭框架，再每天推进主线，最后统一复盘补漏。'**
  String get planCreateTaskBlueprintHint;

  /// No description provided for @planCreateReferenceExistingTasks.
  ///
  /// In zh, this message translates to:
  /// **'参考已有任务'**
  String get planCreateReferenceExistingTasks;

  /// No description provided for @planCreateCopyToPlan.
  ///
  /// In zh, this message translates to:
  /// **'复制进计划'**
  String get planCreateCopyToPlan;

  /// No description provided for @planCreateNewTaskLabel.
  ///
  /// In zh, this message translates to:
  /// **'新增计划任务'**
  String get planCreateNewTaskLabel;

  /// No description provided for @planCreateNewTaskHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：完成一轮章节梳理'**
  String get planCreateNewTaskHint;

  /// No description provided for @planCreateDurationLabel.
  ///
  /// In zh, this message translates to:
  /// **'时长'**
  String get planCreateDurationLabel;

  /// No description provided for @planCreateDifficultyLabel.
  ///
  /// In zh, this message translates to:
  /// **'难度'**
  String get planCreateDifficultyLabel;

  /// No description provided for @planCreateAddTaskToPlan.
  ///
  /// In zh, this message translates to:
  /// **'加入计划任务'**
  String get planCreateAddTaskToPlan;

  /// No description provided for @planCreateNoTasks.
  ///
  /// In zh, this message translates to:
  /// **'当前还没有计划任务'**
  String get planCreateNoTasks;

  /// No description provided for @planCreateScopeLabel.
  ///
  /// In zh, this message translates to:
  /// **'计划边界与注意事项'**
  String get planCreateScopeLabel;

  /// No description provided for @planCreateScopeHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：本计划不承担临时杂事，只关注考试主线；每天只推进一条主线动作。'**
  String get planCreateScopeHint;

  /// No description provided for @planCreateGuidePerspective.
  ///
  /// In zh, this message translates to:
  /// **'任务指南视角'**
  String get planCreateGuidePerspective;

  /// No description provided for @planCreateGuideForSelf.
  ///
  /// In zh, this message translates to:
  /// **'给自己看'**
  String get planCreateGuideForSelf;

  /// No description provided for @planCreateGuideForAi.
  ///
  /// In zh, this message translates to:
  /// **'给 AI 用'**
  String get planCreateGuideForAi;

  /// No description provided for @planCreateGuideHumanDescription.
  ///
  /// In zh, this message translates to:
  /// **'用户版会默认作为计划卡上的执行指南保存，帮助用户自己直接推进。'**
  String get planCreateGuideHumanDescription;

  /// No description provided for @planCreateGuideAiDescription.
  ///
  /// In zh, this message translates to:
  /// **'AI 版本只在需要时生成，用于 Sparkle 内部任务助手，不作为默认持久化内容。'**
  String get planCreateGuideAiDescription;

  /// No description provided for @planCreateGuideHumanTitle.
  ///
  /// In zh, this message translates to:
  /// **'用户版执行指南'**
  String get planCreateGuideHumanTitle;

  /// No description provided for @planCreateGuideAiTitle.
  ///
  /// In zh, this message translates to:
  /// **'给 AI 的执行版本'**
  String get planCreateGuideAiTitle;

  /// No description provided for @planCreateGenerateHumanGuide.
  ///
  /// In zh, this message translates to:
  /// **'生成用户版'**
  String get planCreateGenerateHumanGuide;

  /// No description provided for @planCreateGenerateAiGuide.
  ///
  /// In zh, this message translates to:
  /// **'生成 AI 版'**
  String get planCreateGenerateAiGuide;

  /// No description provided for @planCreateGuideHint.
  ///
  /// In zh, this message translates to:
  /// **'生成后会在这里看到计划推进主线、每日节奏、风险提醒和今日起步动作。'**
  String get planCreateGuideHint;

  /// No description provided for @planCreateAiGuideEmpty.
  ///
  /// In zh, this message translates to:
  /// **'还没有 AI 版本。只有明确需要时才生成，避免无意义耗 token。'**
  String get planCreateAiGuideEmpty;

  /// No description provided for @planCreateCopyAiGuide.
  ///
  /// In zh, this message translates to:
  /// **'复制 AI 版'**
  String get planCreateCopyAiGuide;

  /// No description provided for @planCreateAiGuideCopied.
  ///
  /// In zh, this message translates to:
  /// **'AI 版本已复制'**
  String get planCreateAiGuideCopied;

  /// No description provided for @planCreateReviewSummary.
  ///
  /// In zh, this message translates to:
  /// **'{type} · {dailyMinutes} 分钟/天 · {hours} 小时'**
  String planCreateReviewSummary(
      Object dailyMinutes, Object hours, Object type);

  /// No description provided for @planCreateReviewEditDescription.
  ///
  /// In zh, this message translates to:
  /// **'保存后会更新计划描述，并为新增草案创建新的计划任务。'**
  String get planCreateReviewEditDescription;

  /// No description provided for @planCreateReviewCreateDescription.
  ///
  /// In zh, this message translates to:
  /// **'创建后会生成一张更完整的计划卡，并同步创建计划任务。'**
  String get planCreateReviewCreateDescription;

  /// No description provided for @planCreateFinalDescription.
  ///
  /// In zh, this message translates to:
  /// **'最终写入的计划描述'**
  String get planCreateFinalDescription;

  /// No description provided for @planCreateMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{value} 分钟'**
  String planCreateMinutes(Object value);

  /// No description provided for @planCreateTaskSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟 · 难度 {difficulty}'**
  String planCreateTaskSubtitle(Object difficulty, Object minutes);

  /// No description provided for @predictedIntentTitle.
  ///
  /// In zh, this message translates to:
  /// **'系统预测'**
  String get predictedIntentTitle;

  /// No description provided for @predictedIntentCollapsedTitle.
  ///
  /// In zh, this message translates to:
  /// **'系统预测已收起'**
  String get predictedIntentCollapsedTitle;

  /// No description provided for @predictedIntentCollapsedExpand.
  ///
  /// In zh, this message translates to:
  /// **'需要时再展开查看建议'**
  String get predictedIntentCollapsedExpand;

  /// No description provided for @predictedIntentCollapsedUpdated.
  ///
  /// In zh, this message translates to:
  /// **'上次更新于'**
  String get predictedIntentCollapsedUpdated;

  /// No description provided for @predictedIntentSummary.
  ///
  /// In zh, this message translates to:
  /// **'基于画像、最近 24 小时行为与任务节奏'**
  String get predictedIntentSummary;

  /// No description provided for @predictedIntentSuggestedCont.
  ///
  /// In zh, this message translates to:
  /// **'建议接续'**
  String get predictedIntentSuggestedCont;

  /// No description provided for @predictedIntentWaiting.
  ///
  /// In zh, this message translates to:
  /// **'预测结果已生成，等待可继续指令'**
  String get predictedIntentWaiting;

  /// No description provided for @predictedIntentConfidence.
  ///
  /// In zh, this message translates to:
  /// **'可信度 {percent}%'**
  String predictedIntentConfidence(Object percent);

  /// No description provided for @predictedIntentWhy.
  ///
  /// In zh, this message translates to:
  /// **'为什么这样预测'**
  String get predictedIntentWhy;

  /// No description provided for @predictedIntentContinuing.
  ///
  /// In zh, this message translates to:
  /// **'正在衔接…'**
  String get predictedIntentContinuing;

  /// No description provided for @predictedIntentContinue.
  ///
  /// In zh, this message translates to:
  /// **'按这个继续'**
  String get predictedIntentContinue;

  /// No description provided for @predictedIntentError.
  ///
  /// In zh, this message translates to:
  /// **'继续对话时出现问题，请稍后重试'**
  String get predictedIntentError;

  /// No description provided for @predictedActionResumePriority.
  ///
  /// In zh, this message translates to:
  /// **'继续重点任务'**
  String get predictedActionResumePriority;

  /// No description provided for @predictedActionStudyPlan.
  ///
  /// In zh, this message translates to:
  /// **'生成学习计划'**
  String get predictedActionStudyPlan;

  /// No description provided for @predictedActionDiagnose.
  ///
  /// In zh, this message translates to:
  /// **'问题诊断'**
  String get predictedActionDiagnose;

  /// No description provided for @predictedActionCreateTask.
  ///
  /// In zh, this message translates to:
  /// **'落成任务'**
  String get predictedActionCreateTask;

  /// No description provided for @predictedActionInstantResult.
  ///
  /// In zh, this message translates to:
  /// **'即时结果'**
  String get predictedActionInstantResult;

  /// No description provided for @predictedActionReviewProgress.
  ///
  /// In zh, this message translates to:
  /// **'复盘进展'**
  String get predictedActionReviewProgress;

  /// No description provided for @predictedActionPlanNext.
  ///
  /// In zh, this message translates to:
  /// **'规划下一步'**
  String get predictedActionPlanNext;

  /// No description provided for @predictedActionReflection.
  ///
  /// In zh, this message translates to:
  /// **'快速反思'**
  String get predictedActionReflection;

  /// No description provided for @predictedActionDefault.
  ///
  /// In zh, this message translates to:
  /// **'预测意图'**
  String get predictedActionDefault;

  /// No description provided for @predictedWindowNow.
  ///
  /// In zh, this message translates to:
  /// **'就是现在'**
  String get predictedWindowNow;

  /// No description provided for @predictedWindow30m.
  ///
  /// In zh, this message translates to:
  /// **'未来 30 分钟'**
  String get predictedWindow30m;

  /// No description provided for @predictedWindow1h.
  ///
  /// In zh, this message translates to:
  /// **'未来 1 小时'**
  String get predictedWindow1h;

  /// No description provided for @predictedWindow2h.
  ///
  /// In zh, this message translates to:
  /// **'未来 2 小时'**
  String get predictedWindow2h;

  /// No description provided for @predictedWindow6h.
  ///
  /// In zh, this message translates to:
  /// **'未来 6 小时'**
  String get predictedWindow6h;

  /// No description provided for @predictedWindowToday.
  ///
  /// In zh, this message translates to:
  /// **'今天内'**
  String get predictedWindowToday;

  /// No description provided for @predictedSourceLongRange.
  ///
  /// In zh, this message translates to:
  /// **'长期预测'**
  String get predictedSourceLongRange;

  /// No description provided for @predictedSourceRules.
  ///
  /// In zh, this message translates to:
  /// **'规则兜底'**
  String get predictedSourceRules;

  /// No description provided for @predictedFreshnessJustNow.
  ///
  /// In zh, this message translates to:
  /// **'刚刚更新'**
  String get predictedFreshnessJustNow;

  /// No description provided for @predictedFreshnessMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{count} 分钟前'**
  String predictedFreshnessMinutes(Object count);

  /// No description provided for @predictedFreshnessHours.
  ///
  /// In zh, this message translates to:
  /// **'{count} 小时前'**
  String predictedFreshnessHours(Object count);

  /// No description provided for @predictedFreshnessDays.
  ///
  /// In zh, this message translates to:
  /// **'{count} 天前'**
  String predictedFreshnessDays(Object count);

  /// No description provided for @predictedCategoryPrefTitle.
  ///
  /// In zh, this message translates to:
  /// **'同类请求里的近期偏好'**
  String get predictedCategoryPrefTitle;

  /// No description provided for @predictedCategoryPrefHint.
  ///
  /// In zh, this message translates to:
  /// **'在{category}里，近期结果更常把「{tool}」推到前面。'**
  String predictedCategoryPrefHint(Object category, Object tool);

  /// No description provided for @predictedCategoryPrefCaveat.
  ///
  /// In zh, this message translates to:
  /// **'仅基于同类请求里的近期结果，不代表 Sparkle 理解了你的完整工作流。'**
  String get predictedCategoryPrefCaveat;

  /// No description provided for @predictedCategoryPlan.
  ///
  /// In zh, this message translates to:
  /// **'规划类请求'**
  String get predictedCategoryPlan;

  /// No description provided for @predictedCategoryTask.
  ///
  /// In zh, this message translates to:
  /// **'任务类请求'**
  String get predictedCategoryTask;

  /// No description provided for @predictedCategoryFocus.
  ///
  /// In zh, this message translates to:
  /// **'专注支持类请求'**
  String get predictedCategoryFocus;

  /// No description provided for @predictedCategoryGrowth.
  ///
  /// In zh, this message translates to:
  /// **'成长推进类请求'**
  String get predictedCategoryGrowth;

  /// No description provided for @predictedCategoryQuery.
  ///
  /// In zh, this message translates to:
  /// **'查询类请求'**
  String get predictedCategoryQuery;

  /// No description provided for @predictedCategoryKnowledge.
  ///
  /// In zh, this message translates to:
  /// **'知识类请求'**
  String get predictedCategoryKnowledge;

  /// No description provided for @predictedCategoryReview.
  ///
  /// In zh, this message translates to:
  /// **'复盘类请求'**
  String get predictedCategoryReview;

  /// No description provided for @predictedCategoryResearch.
  ///
  /// In zh, this message translates to:
  /// **'研究类请求'**
  String get predictedCategoryResearch;

  /// No description provided for @predictedCategoryMemory.
  ///
  /// In zh, this message translates to:
  /// **'记忆整理类请求'**
  String get predictedCategoryMemory;

  /// No description provided for @predictedCategoryCognitive.
  ///
  /// In zh, this message translates to:
  /// **'认知整理类请求'**
  String get predictedCategoryCognitive;

  /// No description provided for @predictedCategoryDefault.
  ///
  /// In zh, this message translates to:
  /// **'同类请求'**
  String get predictedCategoryDefault;

  /// No description provided for @predictedToolCreatePlan.
  ///
  /// In zh, this message translates to:
  /// **'生成计划'**
  String get predictedToolCreatePlan;

  /// No description provided for @predictedToolGenerateTasks.
  ///
  /// In zh, this message translates to:
  /// **'展开计划步骤'**
  String get predictedToolGenerateTasks;

  /// No description provided for @predictedToolCreateTask.
  ///
  /// In zh, this message translates to:
  /// **'落成任务'**
  String get predictedToolCreateTask;

  /// No description provided for @predictedToolListTasks.
  ///
  /// In zh, this message translates to:
  /// **'查看任务列表'**
  String get predictedToolListTasks;

  /// No description provided for @predictedToolUpdateTask.
  ///
  /// In zh, this message translates to:
  /// **'更新任务'**
  String get predictedToolUpdateTask;

  /// No description provided for @predictedToolQueryKnowledge.
  ///
  /// In zh, this message translates to:
  /// **'查询知识'**
  String get predictedToolQueryKnowledge;

  /// No description provided for @predictedToolExplainConcept.
  ///
  /// In zh, this message translates to:
  /// **'解释概念'**
  String get predictedToolExplainConcept;

  /// No description provided for @predictedToolReviewProgress.
  ///
  /// In zh, this message translates to:
  /// **'复盘进度'**
  String get predictedToolReviewProgress;

  /// No description provided for @predictedToolGenerateSummary.
  ///
  /// In zh, this message translates to:
  /// **'生成总结'**
  String get predictedToolGenerateSummary;

  /// No description provided for @predictedToolSuggestSchedule.
  ///
  /// In zh, this message translates to:
  /// **'建议排期'**
  String get predictedToolSuggestSchedule;

  /// No description provided for @examSprintHighFreqCoverage.
  ///
  /// In zh, this message translates to:
  /// **'高频考点覆盖率'**
  String get examSprintHighFreqCoverage;

  /// No description provided for @examSprintMistakeRepair.
  ///
  /// In zh, this message translates to:
  /// **'错题修复率'**
  String get examSprintMistakeRepair;

  /// No description provided for @examSprintStudyStreak.
  ///
  /// In zh, this message translates to:
  /// **'连续学习天数'**
  String get examSprintStudyStreak;

  /// No description provided for @examSprintStreakDays.
  ///
  /// In zh, this message translates to:
  /// **'{days} 天'**
  String examSprintStreakDays(Object days);

  /// No description provided for @examSprintKeepRhythm.
  ///
  /// In zh, this message translates to:
  /// **'保持节奏'**
  String get examSprintKeepRhythm;

  /// No description provided for @examSprintHighYieldWeak.
  ///
  /// In zh, this message translates to:
  /// **'高收益低掌握：{topics}'**
  String examSprintHighYieldWeak(Object topics);

  /// No description provided for @examSprintNoTasksToday.
  ///
  /// In zh, this message translates to:
  /// **'今天还没有排入冲刺任务。'**
  String get examSprintNoTasksToday;

  /// No description provided for @examSprintExamDayReady.
  ///
  /// In zh, this message translates to:
  /// **'今天考试 · 你已经准备好了 🎓'**
  String get examSprintExamDayReady;

  /// No description provided for @examSprintExamTips.
  ///
  /// In zh, this message translates to:
  /// **'考场建议'**
  String get examSprintExamTips;

  /// No description provided for @examSprintRecordResult.
  ///
  /// In zh, this message translates to:
  /// **'记录考试结果'**
  String get examSprintRecordResult;

  /// No description provided for @examSprintDashboardTitle.
  ///
  /// In zh, this message translates to:
  /// **'考试冲刺仪表盘'**
  String get examSprintDashboardTitle;

  /// No description provided for @examSprintModeHighScore.
  ///
  /// In zh, this message translates to:
  /// **'冲高模式'**
  String get examSprintModeHighScore;

  /// No description provided for @examSprintModeHold.
  ///
  /// In zh, this message translates to:
  /// **'稳分模式'**
  String get examSprintModeHold;

  /// No description provided for @examSprintModePass.
  ///
  /// In zh, this message translates to:
  /// **'保过模式'**
  String get examSprintModePass;

  /// No description provided for @examSprintModeDefault.
  ///
  /// In zh, this message translates to:
  /// **'冲刺模式'**
  String get examSprintModeDefault;

  /// No description provided for @examSprintExamDay.
  ///
  /// In zh, this message translates to:
  /// **'今天考试'**
  String get examSprintExamDay;

  /// No description provided for @examSprintCountdown.
  ///
  /// In zh, this message translates to:
  /// **'距考试还有 {days} 天'**
  String examSprintCountdown(Object days);

  /// No description provided for @examSprintTodayTasks.
  ///
  /// In zh, this message translates to:
  /// **'今天已完成 {completed}/{total} 项任务'**
  String examSprintTodayTasks(Object completed, Object total);

  /// No description provided for @examSprintDaysLeft.
  ///
  /// In zh, this message translates to:
  /// **'离考试还有 {days}'**
  String examSprintDaysLeft(Object days);

  /// No description provided for @examSprintTodayDone.
  ///
  /// In zh, this message translates to:
  /// **'今日 {completed}/{total} 完成'**
  String examSprintTodayDone(Object completed, Object total);

  /// No description provided for @examSprintTodaySprintTasks.
  ///
  /// In zh, this message translates to:
  /// **'今日冲刺任务'**
  String get examSprintTodaySprintTasks;

  /// No description provided for @examSprintHideLater.
  ///
  /// In zh, this message translates to:
  /// **'收起后续天'**
  String get examSprintHideLater;

  /// No description provided for @examSprintShowLater.
  ///
  /// In zh, this message translates to:
  /// **'展开后续 {count} 天'**
  String examSprintShowLater(Object count);

  /// No description provided for @examSprintDayIndex.
  ///
  /// In zh, this message translates to:
  /// **'第 {index} 天'**
  String examSprintDayIndex(Object index);

  /// No description provided for @examSprintDateFormat.
  ///
  /// In zh, this message translates to:
  /// **'{month}月{day}日'**
  String examSprintDateFormat(Object month, Object day);

  /// No description provided for @examSprintNoSprintTasks.
  ///
  /// In zh, this message translates to:
  /// **'今天还没有排入任务'**
  String get examSprintNoSprintTasks;

  /// No description provided for @examSprintMinLabel.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟 · {status}'**
  String examSprintMinLabel(Object minutes, Object status);

  /// No description provided for @examSprintStatusDone.
  ///
  /// In zh, this message translates to:
  /// **'已完成'**
  String get examSprintStatusDone;

  /// No description provided for @examSprintStatusInProgress.
  ///
  /// In zh, this message translates to:
  /// **'进行中'**
  String get examSprintStatusInProgress;

  /// No description provided for @examSprintStatusPending.
  ///
  /// In zh, this message translates to:
  /// **'待开始'**
  String get examSprintStatusPending;

  /// No description provided for @insightHubTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习洞察'**
  String get insightHubTitle;

  /// No description provided for @insightHubRecommendedSeeds.
  ///
  /// In zh, this message translates to:
  /// **'现在有 {count} 个推荐场景可以直接开始模拟。'**
  String insightHubRecommendedSeeds(Object count);

  /// No description provided for @insightHubFallbackSummary.
  ///
  /// In zh, this message translates to:
  /// **'把推演、仿真和报告收进一条更轻量的学习动线。'**
  String get insightHubFallbackSummary;

  /// No description provided for @insightHubSimulation.
  ///
  /// In zh, this message translates to:
  /// **'学习仿真'**
  String get insightHubSimulation;

  /// No description provided for @insightHubTheater.
  ///
  /// In zh, this message translates to:
  /// **'推演剧场'**
  String get insightHubTheater;

  /// No description provided for @insightHubReport.
  ///
  /// In zh, this message translates to:
  /// **'学习报告'**
  String get insightHubReport;

  /// No description provided for @insightHubEnterOverview.
  ///
  /// In zh, this message translates to:
  /// **'进入洞察总览'**
  String get insightHubEnterOverview;

  /// No description provided for @insightHubCompactSimulation.
  ///
  /// In zh, this message translates to:
  /// **'仿真'**
  String get insightHubCompactSimulation;

  /// No description provided for @insightHubCompactTheater.
  ///
  /// In zh, this message translates to:
  /// **'推演'**
  String get insightHubCompactTheater;

  /// No description provided for @insightHubCompactReport.
  ///
  /// In zh, this message translates to:
  /// **'报告'**
  String get insightHubCompactReport;

  /// No description provided for @insightHubRefreshWarning.
  ///
  /// In zh, this message translates to:
  /// **'部分洞察数据尚未刷新，点击后会继续显示已有内容。'**
  String get insightHubRefreshWarning;

  /// No description provided for @insightHubSeedsToExplore.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个推荐场景待探索'**
  String insightHubSeedsToExplore(Object count);

  /// No description provided for @insightHubCompactFallback.
  ///
  /// In zh, this message translates to:
  /// **'仿真、推演和报告现在收在同一张卡里'**
  String get insightHubCompactFallback;

  /// No description provided for @insightHubNoRecentTheater.
  ///
  /// In zh, this message translates to:
  /// **'最近暂无推演'**
  String get insightHubNoRecentTheater;

  /// No description provided for @insightHubContinueLastTheater.
  ///
  /// In zh, this message translates to:
  /// **'继续上次推演'**
  String get insightHubContinueLastTheater;

  /// No description provided for @insightHubContinueTopic.
  ///
  /// In zh, this message translates to:
  /// **'继续 {topic}'**
  String insightHubContinueTopic(Object topic);

  /// No description provided for @insightHubContinueLastSimulation.
  ///
  /// In zh, this message translates to:
  /// **'继续上次仿真'**
  String get insightHubContinueLastSimulation;

  /// No description provided for @insightHubRecommendedSeedsCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个推荐场景'**
  String insightHubRecommendedSeedsCount(Object count);

  /// No description provided for @insightHubContinueSession.
  ///
  /// In zh, this message translates to:
  /// **'继续 {topic}'**
  String insightHubContinueSession(Object topic);

  /// No description provided for @insightHubStartSimulation.
  ///
  /// In zh, this message translates to:
  /// **'开始一轮新模拟'**
  String get insightHubStartSimulation;

  /// No description provided for @insightHubNoRecentReport.
  ///
  /// In zh, this message translates to:
  /// **'最近暂无报告'**
  String get insightHubNoRecentReport;

  /// No description provided for @insightHubMasteryPercent.
  ///
  /// In zh, this message translates to:
  /// **'掌握度 {percent}%'**
  String insightHubMasteryPercent(Object percent);

  /// No description provided for @insightHubRefreshFailed.
  ///
  /// In zh, this message translates to:
  /// **'洞察内容暂时没有刷新成功，当前先显示已有内容。'**
  String get insightHubRefreshFailed;

  /// No description provided for @insightHubRetry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get insightHubRetry;

  /// No description provided for @memoryPanel.
  ///
  /// In zh, this message translates to:
  /// **'记忆面板'**
  String get memoryPanel;

  /// No description provided for @memoryPanelAdjust.
  ///
  /// In zh, this message translates to:
  /// **'调整'**
  String get memoryPanelAdjust;

  /// No description provided for @memoryPanelAiAutoMemories.
  ///
  /// In zh, this message translates to:
  /// **'AI 自动记忆'**
  String get memoryPanelAiAutoMemories;

  /// No description provided for @memoryPanelAiInferredDescription.
  ///
  /// In zh, this message translates to:
  /// **'AI 推断自聊天，默认仅作记忆展示，不参与下游决策。'**
  String get memoryPanelAiInferredDescription;

  /// No description provided for @memoryPanelClearFilter.
  ///
  /// In zh, this message translates to:
  /// **'清空筛选'**
  String get memoryPanelClearFilter;

  /// No description provided for @memoryPanelCommitmentDismissed.
  ///
  /// In zh, this message translates to:
  /// **'已忽略该承诺'**
  String get memoryPanelCommitmentDismissed;

  /// No description provided for @memoryPanelConfidenceValue.
  ///
  /// In zh, this message translates to:
  /// **'置信度 {value}'**
  String memoryPanelConfidenceValue(Object value);

  /// No description provided for @memoryPanelConflictFailed.
  ///
  /// In zh, this message translates to:
  /// **'处理冲突失败: {error}'**
  String memoryPanelConflictFailed(Object error);

  /// No description provided for @memoryPanelConflictResolvedA.
  ///
  /// In zh, this message translates to:
  /// **'已按候选 A 处理'**
  String get memoryPanelConflictResolvedA;

  /// No description provided for @memoryPanelConflictResolvedB.
  ///
  /// In zh, this message translates to:
  /// **'已按候选 B 处理'**
  String get memoryPanelConflictResolvedB;

  /// No description provided for @memoryPanelConflictResolvedNone.
  ///
  /// In zh, this message translates to:
  /// **'已撤销这组冲突候选'**
  String get memoryPanelConflictResolvedNone;

  /// No description provided for @memoryPanelCorrectionCount.
  ///
  /// In zh, this message translates to:
  /// **'纠错 {count}'**
  String memoryPanelCorrectionCount(Object count);

  /// No description provided for @memoryPanelDate.
  ///
  /// In zh, this message translates to:
  /// **'日期'**
  String get memoryPanelDate;

  /// No description provided for @memoryPanelDeviationsDetected.
  ///
  /// In zh, this message translates to:
  /// **'检测到 {count} 个偏离'**
  String memoryPanelDeviationsDetected(Object count);

  /// No description provided for @memoryPanelDimCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get memoryPanelDimCompletionRate;

  /// No description provided for @memoryPanelDimEngagement.
  ///
  /// In zh, this message translates to:
  /// **'投入度'**
  String get memoryPanelDimEngagement;

  /// No description provided for @memoryPanelDimMood.
  ///
  /// In zh, this message translates to:
  /// **'情绪'**
  String get memoryPanelDimMood;

  /// No description provided for @memoryPanelDimPace.
  ///
  /// In zh, this message translates to:
  /// **'节奏'**
  String get memoryPanelDimPace;

  /// No description provided for @memoryPanelDimPlanAdherence.
  ///
  /// In zh, this message translates to:
  /// **'计划跟随'**
  String get memoryPanelDimPlanAdherence;

  /// No description provided for @memoryPanelDismissFailed.
  ///
  /// In zh, this message translates to:
  /// **'忽略失败: {error}'**
  String memoryPanelDismissFailed(Object error);

  /// No description provided for @memoryPanelEmptyDescription.
  ///
  /// In zh, this message translates to:
  /// **'先聊一聊你的目标、偏好或刚完成的学习动作，系统才会开始在这里整理长期记忆。'**
  String get memoryPanelEmptyDescription;

  /// No description provided for @memoryPanelEmptyFilterDescription.
  ///
  /// In zh, this message translates to:
  /// **'试试清空筛选条件，重新查看所有已整理的记忆。'**
  String get memoryPanelEmptyFilterDescription;

  /// No description provided for @memoryPanelEmptyFilterTitle.
  ///
  /// In zh, this message translates to:
  /// **'暂无符合条件的记忆'**
  String get memoryPanelEmptyFilterTitle;

  /// No description provided for @memoryPanelEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'记忆面板还没有内容'**
  String get memoryPanelEmptyTitle;

  /// No description provided for @memoryPanelEvidenceAll.
  ///
  /// In zh, this message translates to:
  /// **'证据全部'**
  String get memoryPanelEvidenceAll;

  /// No description provided for @memoryPanelEvidenceMissing.
  ///
  /// In zh, this message translates to:
  /// **'缺失'**
  String get memoryPanelEvidenceMissing;

  /// No description provided for @memoryPanelEvidenceOk.
  ///
  /// In zh, this message translates to:
  /// **'OK'**
  String get memoryPanelEvidenceOk;

  /// No description provided for @memoryPanelEvidenceRedacted.
  ///
  /// In zh, this message translates to:
  /// **'已隐藏'**
  String get memoryPanelEvidenceRedacted;

  /// No description provided for @memoryPanelForesightHint.
  ///
  /// In zh, this message translates to:
  /// **'前瞻提示'**
  String get memoryPanelForesightHint;

  /// No description provided for @memoryPanelImportanceValue.
  ///
  /// In zh, this message translates to:
  /// **'重要度 {value}'**
  String memoryPanelImportanceValue(Object value);

  /// No description provided for @memoryPanelItemCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条'**
  String memoryPanelItemCount(Object count);

  /// No description provided for @memoryPanelLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'记忆面板加载失败: {error}'**
  String memoryPanelLoadFailed(Object error);

  /// No description provided for @memoryPanelMarkFailed.
  ///
  /// In zh, this message translates to:
  /// **'标记失败: {error}'**
  String memoryPanelMarkFailed(Object error);

  /// No description provided for @memoryPanelMarkedComplete.
  ///
  /// In zh, this message translates to:
  /// **'已标记为完成'**
  String get memoryPanelMarkedComplete;

  /// No description provided for @memoryPanelMetricsNone.
  ///
  /// In zh, this message translates to:
  /// **'指标: -'**
  String get memoryPanelMetricsNone;

  /// No description provided for @memoryPanelNotUpdated.
  ///
  /// In zh, this message translates to:
  /// **'未更新'**
  String get memoryPanelNotUpdated;

  /// No description provided for @memoryPanelRecentScenes.
  ///
  /// In zh, this message translates to:
  /// **'最近场景'**
  String get memoryPanelRecentScenes;

  /// No description provided for @memoryPanelRevoke.
  ///
  /// In zh, this message translates to:
  /// **'撤销'**
  String get memoryPanelRevoke;

  /// No description provided for @memoryPanelRevokeFailed.
  ///
  /// In zh, this message translates to:
  /// **'撤销失败: {error}'**
  String memoryPanelRevokeFailed(Object error);

  /// No description provided for @memoryPanelRevokeThis.
  ///
  /// In zh, this message translates to:
  /// **'撤销此条'**
  String get memoryPanelRevokeThis;

  /// No description provided for @memoryPanelRevokedAutoMemory.
  ///
  /// In zh, this message translates to:
  /// **'已撤销 AI 自动记忆'**
  String get memoryPanelRevokedAutoMemory;

  /// No description provided for @memoryPanelRevoking.
  ///
  /// In zh, this message translates to:
  /// **'撤销中'**
  String get memoryPanelRevoking;

  /// No description provided for @memoryPanelSceneMemories.
  ///
  /// In zh, this message translates to:
  /// **'{time} · {count} 条记忆'**
  String memoryPanelSceneMemories(Object time, Object count);

  /// No description provided for @memoryPanelUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'记忆面板不可用'**
  String get memoryPanelUnavailable;

  /// No description provided for @memoryPanelValidUntil.
  ///
  /// In zh, this message translates to:
  /// **'有效期 {policy}'**
  String memoryPanelValidUntil(Object policy);

  /// No description provided for @theaterComposerDeducing.
  ///
  /// In zh, this message translates to:
  /// **'推演中'**
  String get theaterComposerDeducing;

  /// No description provided for @theaterWhatIfCombinedResult.
  ///
  /// In zh, this message translates to:
  /// **'原始 {originalMastery}% / {originalCompletion}%  →  调整后 {predictedMastery}% / {predictedCompletion}%'**
  String theaterWhatIfCombinedResult(
      Object originalMastery,
      Object originalCompletion,
      Object predictedMastery,
      Object predictedCompletion);

  /// No description provided for @theaterAccuracyPredictedActual.
  ///
  /// In zh, this message translates to:
  /// **'预测 {predictedCompletion}% / {predictedMastery}%， 实际 {actualCompletion}% / {actualMastery}%'**
  String theaterAccuracyPredictedActual(Object predictedCompletion,
      Object predictedMastery, Object actualCompletion, Object actualMastery);

  /// No description provided for @theaterPerDayUnit.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分/天'**
  String theaterPerDayUnit(Object minutes);

  /// No description provided for @simulationTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习场景模拟'**
  String get simulationTitle;

  /// No description provided for @simulationCurrentSimulation.
  ///
  /// In zh, this message translates to:
  /// **'当前模拟'**
  String get simulationCurrentSimulation;

  /// No description provided for @simulationBackToTheater.
  ///
  /// In zh, this message translates to:
  /// **'回到剧场'**
  String get simulationBackToTheater;

  /// No description provided for @simulationRunning.
  ///
  /// In zh, this message translates to:
  /// **'模拟进行中...'**
  String get simulationRunning;

  /// No description provided for @simulationStartSimulation.
  ///
  /// In zh, this message translates to:
  /// **'开始这场模拟'**
  String get simulationStartSimulation;

  /// No description provided for @simulationAwaitingInput.
  ///
  /// In zh, this message translates to:
  /// **'等待输入'**
  String get simulationAwaitingInput;

  /// No description provided for @simulationClearTopic.
  ///
  /// In zh, this message translates to:
  /// **'清空主题'**
  String get simulationClearTopic;

  /// No description provided for @simulationRecommendedScenarios.
  ///
  /// In zh, this message translates to:
  /// **'推荐场景'**
  String get simulationRecommendedScenarios;

  /// No description provided for @simulationGenerate.
  ///
  /// In zh, this message translates to:
  /// **'生成'**
  String get simulationGenerate;

  /// No description provided for @simulationRefresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新'**
  String get simulationRefresh;

  /// No description provided for @simulationStartSimButton.
  ///
  /// In zh, this message translates to:
  /// **'开始模拟'**
  String get simulationStartSimButton;

  /// No description provided for @simulationGoToTheater.
  ///
  /// In zh, this message translates to:
  /// **'去推演'**
  String get simulationGoToTheater;

  /// No description provided for @simulationContinueSim.
  ///
  /// In zh, this message translates to:
  /// **'继续模拟'**
  String get simulationContinueSim;

  /// No description provided for @simulationPauseSim.
  ///
  /// In zh, this message translates to:
  /// **'暂停模拟'**
  String get simulationPauseSim;

  /// No description provided for @simulationCollapseInsight.
  ///
  /// In zh, this message translates to:
  /// **'收起洞察'**
  String get simulationCollapseInsight;

  /// No description provided for @simulationViewInsight.
  ///
  /// In zh, this message translates to:
  /// **'查看洞察'**
  String get simulationViewInsight;

  /// No description provided for @simulationCollapseSettings.
  ///
  /// In zh, this message translates to:
  /// **'收起设置'**
  String get simulationCollapseSettings;

  /// No description provided for @simulationSimSettings.
  ///
  /// In zh, this message translates to:
  /// **'模拟设置'**
  String get simulationSimSettings;

  /// No description provided for @simulationYourTurnTitle.
  ///
  /// In zh, this message translates to:
  /// **'轮到你回应'**
  String get simulationYourTurnTitle;

  /// No description provided for @simulationYourResponseArea.
  ///
  /// In zh, this message translates to:
  /// **'你的回应区'**
  String get simulationYourResponseArea;

  /// No description provided for @simulationCollapse.
  ///
  /// In zh, this message translates to:
  /// **'收起'**
  String get simulationCollapse;

  /// No description provided for @simulationJoinDiscussion.
  ///
  /// In zh, this message translates to:
  /// **'轮到你加入这场讨论'**
  String get simulationJoinDiscussion;

  /// No description provided for @simulationOrInputJudgment.
  ///
  /// In zh, this message translates to:
  /// **'或者输入你的判断'**
  String get simulationOrInputJudgment;

  /// No description provided for @simulationSubmitting.
  ///
  /// In zh, this message translates to:
  /// **'提交中...'**
  String get simulationSubmitting;

  /// No description provided for @simulationSubmitJudgment.
  ///
  /// In zh, this message translates to:
  /// **'提交我的判断'**
  String get simulationSubmitJudgment;

  /// No description provided for @simulationContinueInChat.
  ///
  /// In zh, this message translates to:
  /// **'带回聊天继续'**
  String get simulationContinueInChat;

  /// No description provided for @simulationAdjustSimulation.
  ///
  /// In zh, this message translates to:
  /// **'调整这场模拟'**
  String get simulationAdjustSimulation;

  /// No description provided for @simulationDiscussionRounds.
  ///
  /// In zh, this message translates to:
  /// **'讨论轮数'**
  String get simulationDiscussionRounds;

  /// No description provided for @simulationFacilitationStyleTitle.
  ///
  /// In zh, this message translates to:
  /// **'展开方式'**
  String get simulationFacilitationStyleTitle;

  /// No description provided for @simulationParticipantsTitle.
  ///
  /// In zh, this message translates to:
  /// **'参与角色'**
  String get simulationParticipantsTitle;

  /// No description provided for @simulationRestoreDefault.
  ///
  /// In zh, this message translates to:
  /// **'恢复推荐'**
  String get simulationRestoreDefault;

  /// No description provided for @simulationCustomHistoricalRole.
  ///
  /// In zh, this message translates to:
  /// **'自定义历史人物'**
  String get simulationCustomHistoricalRole;

  /// No description provided for @simulationAdd.
  ///
  /// In zh, this message translates to:
  /// **'添加'**
  String get simulationAdd;

  /// No description provided for @simulationRestartSim.
  ///
  /// In zh, this message translates to:
  /// **'重新开始这场模拟'**
  String get simulationRestartSim;

  /// No description provided for @simulationContinue.
  ///
  /// In zh, this message translates to:
  /// **'继续'**
  String get simulationContinue;

  /// No description provided for @simulationPause.
  ///
  /// In zh, this message translates to:
  /// **'暂停'**
  String get simulationPause;

  /// No description provided for @simulationAwaitingStart.
  ///
  /// In zh, this message translates to:
  /// **'等待开始'**
  String get simulationAwaitingStart;

  /// No description provided for @simulationGatheringParticipants.
  ///
  /// In zh, this message translates to:
  /// **'正在召集参与者'**
  String get simulationGatheringParticipants;

  /// No description provided for @simulationWaitingFirstRound.
  ///
  /// In zh, this message translates to:
  /// **'等待首轮'**
  String get simulationWaitingFirstRound;

  /// No description provided for @simulationRolesPending.
  ///
  /// In zh, this message translates to:
  /// **'角色待加入'**
  String get simulationRolesPending;

  /// No description provided for @simulationGeneratingInBackground.
  ///
  /// In zh, this message translates to:
  /// **'后台仍在继续生成'**
  String get simulationGeneratingInBackground;

  /// No description provided for @simulationPausedForeground.
  ///
  /// In zh, this message translates to:
  /// **'前台已暂停播放'**
  String get simulationPausedForeground;

  /// No description provided for @simulationImmersiveDiscussion.
  ///
  /// In zh, this message translates to:
  /// **'沉浸讨论流'**
  String get simulationImmersiveDiscussion;

  /// No description provided for @simulationCurrentDiscussion.
  ///
  /// In zh, this message translates to:
  /// **'当前讨论流'**
  String get simulationCurrentDiscussion;

  /// No description provided for @simulationWillAppearLive.
  ///
  /// In zh, this message translates to:
  /// **'开始后会实时出现每一轮讨论。'**
  String get simulationWillAppearLive;

  /// No description provided for @simulationNoInsightYet.
  ///
  /// In zh, this message translates to:
  /// **'暂未生成洞察总结。'**
  String get simulationNoInsightYet;

  /// No description provided for @simulationInsightSummaryTitle.
  ///
  /// In zh, this message translates to:
  /// **'洞察总结'**
  String get simulationInsightSummaryTitle;

  /// No description provided for @simulationGeneratingReport.
  ///
  /// In zh, this message translates to:
  /// **'生成中...'**
  String get simulationGeneratingReport;

  /// No description provided for @simulationGenerateLearningReport.
  ///
  /// In zh, this message translates to:
  /// **'生成学习报告'**
  String get simulationGenerateLearningReport;

  /// No description provided for @simulationContinueToTheater.
  ///
  /// In zh, this message translates to:
  /// **'以此推演'**
  String get simulationContinueToTheater;

  /// No description provided for @simulationShareInsight.
  ///
  /// In zh, this message translates to:
  /// **'分享洞察'**
  String get simulationShareInsight;

  /// No description provided for @simulationCoreArguments.
  ///
  /// In zh, this message translates to:
  /// **'核心论点'**
  String get simulationCoreArguments;

  /// No description provided for @simulationUnresolvedDisagreements.
  ///
  /// In zh, this message translates to:
  /// **'未解决的分歧'**
  String get simulationUnresolvedDisagreements;

  /// No description provided for @simulationYourContribution.
  ///
  /// In zh, this message translates to:
  /// **'你的贡献'**
  String get simulationYourContribution;

  /// No description provided for @simulationExposedKnowledgeGaps.
  ///
  /// In zh, this message translates to:
  /// **'暴露的知识盲区'**
  String get simulationExposedKnowledgeGaps;

  /// No description provided for @simulationSuggestedNextSteps.
  ///
  /// In zh, this message translates to:
  /// **'建议下一步'**
  String get simulationSuggestedNextSteps;

  /// No description provided for @simulationStructuredInsightGenerated.
  ///
  /// In zh, this message translates to:
  /// **'已生成结构化洞察总结。'**
  String get simulationStructuredInsightGenerated;

  /// No description provided for @simulationEmptyGenerating.
  ///
  /// In zh, this message translates to:
  /// **'模拟正在生成中...'**
  String get simulationEmptyGenerating;

  /// No description provided for @simulationEmptyStartPrompt.
  ///
  /// In zh, this message translates to:
  /// **'开始一次学习场景模拟，让角色逐轮讨论这个主题。'**
  String get simulationEmptyStartPrompt;

  /// No description provided for @simulationCurrentScene.
  ///
  /// In zh, this message translates to:
  /// **'当前场景'**
  String get simulationCurrentScene;

  /// No description provided for @simulationCurrentGoal.
  ///
  /// In zh, this message translates to:
  /// **'当前目标'**
  String get simulationCurrentGoal;

  /// No description provided for @simulationInteractionStyle.
  ///
  /// In zh, this message translates to:
  /// **'互动方式'**
  String get simulationInteractionStyle;

  /// No description provided for @simulationRoleDiscussionUserJoin.
  ///
  /// In zh, this message translates to:
  /// **'角色讨论 + 你来接话'**
  String get simulationRoleDiscussionUserJoin;

  /// No description provided for @simulationTopicHint.
  ///
  /// In zh, this message translates to:
  /// **'输入一个知识点或主题'**
  String get simulationTopicHint;

  /// No description provided for @simulationTopicHintExample.
  ///
  /// In zh, this message translates to:
  /// **'例如：特征值与特征向量'**
  String get simulationTopicHintExample;

  /// No description provided for @simulationStartSimulationTopicAction.
  ///
  /// In zh, this message translates to:
  /// **'开始围绕这个问题模拟'**
  String get simulationStartSimulationTopicAction;

  /// No description provided for @simulationUserInputTopicHint.
  ///
  /// In zh, this message translates to:
  /// **'输入你想要讨论的学习主题或问题'**
  String get simulationUserInputTopicHint;

  /// No description provided for @simulationUserInputTopicHelper.
  ///
  /// In zh, this message translates to:
  /// **'完成更多学习任务后，系统将基于你的真实学习数据推荐讨论主题'**
  String get simulationUserInputTopicHelper;

  /// No description provided for @simulationRecommendedEmptyHint.
  ///
  /// In zh, this message translates to:
  /// **'还没有推荐种子，你可以先手动输入主题开始。'**
  String get simulationRecommendedEmptyHint;

  /// No description provided for @simulationRecommendedUserInputHint.
  ///
  /// In zh, this message translates to:
  /// **'现在先从你最想讨论的具体问题开始。等积累更多真实学习记录后，系统会再给出基于数据的推荐主题。'**
  String get simulationRecommendedUserInputHint;

  /// No description provided for @simulationRecommendedPickHint.
  ///
  /// In zh, this message translates to:
  /// **'先挑一个最顺手的起点，开始后推荐卡会自动收起，不打断正式讨论。'**
  String get simulationRecommendedPickHint;

  /// No description provided for @simulationScenarioAdjustHint.
  ///
  /// In zh, this message translates to:
  /// **'调整场景后，讨论的角色关系与推进方式也会一起变化。'**
  String get simulationScenarioAdjustHint;

  /// No description provided for @simulationFacilitationFitHint.
  ///
  /// In zh, this message translates to:
  /// **'让讨论更贴合当前主题。'**
  String get simulationFacilitationFitHint;

  /// No description provided for @simulationDiscussionNote.
  ///
  /// In zh, this message translates to:
  /// **'这里可以完整调整主题、场景、轮数、展开方式和参与角色，开始后讨论会按这套设置运行。'**
  String get simulationDiscussionNote;

  /// No description provided for @simulationParticipantHint.
  ///
  /// In zh, this message translates to:
  /// **'你可以明确指定想邀请谁参与这场讨论。至少保留 1 位，最多 6 位角色。'**
  String get simulationParticipantHint;

  /// No description provided for @simulationRunningStatusHint.
  ///
  /// In zh, this message translates to:
  /// **'模拟进行中，新的轮次会实时出现在下方。'**
  String get simulationRunningStatusHint;

  /// No description provided for @simulationScenarioEyebrow.
  ///
  /// In zh, this message translates to:
  /// **'学习场景模拟'**
  String get simulationScenarioEyebrow;

  /// No description provided for @simulationScenarioTitle.
  ///
  /// In zh, this message translates to:
  /// **'开始这场学习模拟'**
  String get simulationScenarioTitle;

  /// No description provided for @simulationScenarioSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'先选讨论场景，再输入一个你想推开的主题。开始后会自动收束成沉浸式讨论界面。'**
  String get simulationScenarioSubtitle;

  /// No description provided for @simulationRoleDiscussionValue.
  ///
  /// In zh, this message translates to:
  /// **'角色讨论 + 你来接话'**
  String get simulationRoleDiscussionValue;

  /// No description provided for @simulationJudgeExampleHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：我会先补几何直觉，再回来刷一道题验证'**
  String get simulationJudgeExampleHint;

  /// No description provided for @simulationInteractionExplain.
  ///
  /// In zh, this message translates to:
  /// **'先给出你的判断，下一轮才会真正围绕你的想法继续展开。'**
  String get simulationInteractionExplain;

  /// No description provided for @simulationInteractionHint.
  ///
  /// In zh, this message translates to:
  /// **'建议先在这里接住一轮，让角色回应你的判断；如果你想回到主对话，也可以把这一步带回聊天继续。'**
  String get simulationInteractionHint;

  /// No description provided for @simulationContinuitySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'这一轮模拟承接了你刚才的探索流程。你可以随时带着上下文回到原对话，继续追问判断和下一步行动。'**
  String get simulationContinuitySubtitle;

  /// No description provided for @simulationBridgeCurrentlyVerifyingFormat.
  ///
  /// In zh, this message translates to:
  /// **'正在验证路径「{routeTitle}」'**
  String simulationBridgeCurrentlyVerifyingFormat(Object routeTitle);

  /// No description provided for @simulationBridgeVerifyingRoute.
  ///
  /// In zh, this message translates to:
  /// **'正在验证一条推演路径'**
  String get simulationBridgeVerifyingRoute;

  /// No description provided for @simulationBridgeVerificationDescWithTarget.
  ///
  /// In zh, this message translates to:
  /// **'这轮模拟来自知识剧场，目标是 {targetName}。你可以随时带着当前进度回到剧场继续采纳或校准。'**
  String simulationBridgeVerificationDescWithTarget(Object targetName);

  /// No description provided for @simulationBridgeVerificationContext.
  ///
  /// In zh, this message translates to:
  /// **'这轮模拟来自知识剧场，当前上下文会和原推演保持关联。'**
  String get simulationBridgeVerificationContext;

  /// No description provided for @simulationInteractionModeFormat.
  ///
  /// In zh, this message translates to:
  /// **'互动模式：{mode}'**
  String simulationInteractionModeFormat(Object mode);

  /// No description provided for @simulationInteractionOpenQuestion.
  ///
  /// In zh, this message translates to:
  /// **'开放追问'**
  String get simulationInteractionOpenQuestion;

  /// No description provided for @simulationInteractionViewpointChallenge.
  ///
  /// In zh, this message translates to:
  /// **'观点挑战'**
  String get simulationInteractionViewpointChallenge;

  /// No description provided for @simulationInteractionBinaryChoice.
  ///
  /// In zh, this message translates to:
  /// **'二选一判断'**
  String get simulationInteractionBinaryChoice;

  /// No description provided for @simulationInteractionChoice.
  ///
  /// In zh, this message translates to:
  /// **'选择判断'**
  String get simulationInteractionChoice;

  /// No description provided for @simulationCurrentFocusFormat.
  ///
  /// In zh, this message translates to:
  /// **'当前焦点：{speaker}'**
  String simulationCurrentFocusFormat(Object speaker);

  /// No description provided for @simulationTopicFormat.
  ///
  /// In zh, this message translates to:
  /// **'主题：{topic}'**
  String simulationTopicFormat(Object topic);

  /// No description provided for @simulationTopicAndSpeakerFormat.
  ///
  /// In zh, this message translates to:
  /// **'主题：{topic} · 当前发言 {speaker}'**
  String simulationTopicAndSpeakerFormat(Object topic, Object speaker);

  /// No description provided for @simulationRoundN.
  ///
  /// In zh, this message translates to:
  /// **'第 {round} 轮'**
  String simulationRoundN(Object round);

  /// No description provided for @simulationRoleCountFormat.
  ///
  /// In zh, this message translates to:
  /// **'{count} 角色'**
  String simulationRoleCountFormat(Object count);

  /// No description provided for @simulationRunningRoundN.
  ///
  /// In zh, this message translates to:
  /// **'正在第 {round}/{total} 轮'**
  String simulationRunningRoundN(Object round, Object total);

  /// No description provided for @simulationRoundViewpoints.
  ///
  /// In zh, this message translates to:
  /// **'{count} 轮观点'**
  String simulationRoundViewpoints(Object count);

  /// No description provided for @simulationRoleCountLong.
  ///
  /// In zh, this message translates to:
  /// **'{count} 位角色'**
  String simulationRoleCountLong(Object count);

  /// No description provided for @simulationRoundFormatLabel.
  ///
  /// In zh, this message translates to:
  /// **'{current} / {max} 轮'**
  String simulationRoundFormatLabel(Object current, Object max);

  /// No description provided for @simulationRoundSliderLabel.
  ///
  /// In zh, this message translates to:
  /// **'{count} 轮'**
  String simulationRoundSliderLabel(Object count);

  /// No description provided for @simulationParticipantDefaultStatus.
  ///
  /// In zh, this message translates to:
  /// **'当前将按系统默认角色运行。'**
  String get simulationParticipantDefaultStatus;

  /// No description provided for @simulationParticipantCurrentStatus.
  ///
  /// In zh, this message translates to:
  /// **'当前参与：{names}'**
  String simulationParticipantCurrentStatus(Object names);

  /// No description provided for @simulationBulletParticipants.
  ///
  /// In zh, this message translates to:
  /// **'参与者：{names}'**
  String simulationBulletParticipants(Object names);

  /// No description provided for @simulationBulletRounds.
  ///
  /// In zh, this message translates to:
  /// **'总轮次：{count} 轮，适合沉淀为下一步推演或复盘报告。'**
  String simulationBulletRounds(Object count);

  /// No description provided for @simulationBulletOpening.
  ///
  /// In zh, this message translates to:
  /// **'开场重点：{message}'**
  String simulationBulletOpening(Object message);

  /// No description provided for @simulationRoundFormatShort.
  ///
  /// In zh, this message translates to:
  /// **'{current}/{total} 轮'**
  String simulationRoundFormatShort(Object current, Object total);

  /// No description provided for @simulationContinueInChatContext.
  ///
  /// In zh, this message translates to:
  /// **'继续刚才的学习模拟。'**
  String get simulationContinueInChatContext;

  /// No description provided for @simulationContinueTopicLabel.
  ///
  /// In zh, this message translates to:
  /// **'主题：{topic}'**
  String simulationContinueTopicLabel(Object topic);

  /// No description provided for @simulationContinueScenarioLabel.
  ///
  /// In zh, this message translates to:
  /// **'场景：{label}'**
  String simulationContinueScenarioLabel(Object label);

  /// No description provided for @simulationContinueCurrentQuestion.
  ///
  /// In zh, this message translates to:
  /// **'当前问题：{question}'**
  String simulationContinueCurrentQuestion(Object question);

  /// No description provided for @simulationContinueMyResponse.
  ///
  /// In zh, this message translates to:
  /// **'我的回应：{reply}'**
  String simulationContinueMyResponse(Object reply);

  /// No description provided for @simulationBalancedPush.
  ///
  /// In zh, this message translates to:
  /// **'平衡推进'**
  String get simulationBalancedPush;

  /// No description provided for @simulationDebateClash.
  ///
  /// In zh, this message translates to:
  /// **'分歧碰撞'**
  String get simulationDebateClash;

  /// No description provided for @simulationGuidedBreakdown.
  ///
  /// In zh, this message translates to:
  /// **'引导拆解'**
  String get simulationGuidedBreakdown;

  /// No description provided for @simulationPracticalApply.
  ///
  /// In zh, this message translates to:
  /// **'应用落地'**
  String get simulationPracticalApply;

  /// No description provided for @simulationReportReturnException.
  ///
  /// In zh, this message translates to:
  /// **'学习报告返回格式异常'**
  String get simulationReportReturnException;

  /// No description provided for @simulationReportGenerationFailed.
  ///
  /// In zh, this message translates to:
  /// **'生成学习报告失败：{error}'**
  String simulationReportGenerationFailed(Object error);

  /// No description provided for @simulationReportTitle.
  ///
  /// In zh, this message translates to:
  /// **'这份报告已接收本次模拟中暴露的问题'**
  String get simulationReportTitle;

  /// No description provided for @simulationReportSummary.
  ///
  /// In zh, this message translates to:
  /// **'你在模拟里暴露出的分歧和知识盲区，已经被带入这份正式报告。'**
  String get simulationReportSummary;

  /// No description provided for @simulationShareCreated.
  ///
  /// In zh, this message translates to:
  /// **'我刚在 Sparkle 跑了一场学习仿真：{topic}\n场景：{scenario}\n洞察：{insight}'**
  String simulationShareCreated(Object topic, Object scenario, Object insight);

  /// No description provided for @simulationShareTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习场景模拟 · {topic}'**
  String simulationShareTitle(Object topic);

  /// No description provided for @simulationShareRawText.
  ///
  /// In zh, this message translates to:
  /// **'学习场景模拟\n主题：{topic}\n场景：{scenario}\n洞察：{insight}'**
  String simulationShareRawText(Object topic, Object scenario, Object insight);

  /// No description provided for @simulationCustomFigureHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：张居正 / 俾斯麦'**
  String get simulationCustomFigureHint;

  /// No description provided for @simulationTopicCurrentFocusFormat.
  ///
  /// In zh, this message translates to:
  /// **'主题：{topic} · 当前发言 {speaker}'**
  String simulationTopicCurrentFocusFormat(Object topic, Object speaker);

  /// No description provided for @simulationCurrentFocusLabel.
  ///
  /// In zh, this message translates to:
  /// **'当前焦点：{speaker}'**
  String simulationCurrentFocusLabel(Object speaker);

  /// No description provided for @simulationImmersiveTopicAndFocus.
  ///
  /// In zh, this message translates to:
  /// **'主题：{topic} · 当前发言 {speaker}'**
  String simulationImmersiveTopicAndFocus(Object topic, Object speaker);

  /// No description provided for @simulationWaitingInput.
  ///
  /// In zh, this message translates to:
  /// **'等待输入'**
  String get simulationWaitingInput;

  /// No description provided for @simulationScenarioDescStudyGroup.
  ///
  /// In zh, this message translates to:
  /// **'围绕一个主题做多角色共学，适合把概念、例题和误区一起讲透。'**
  String get simulationScenarioDescStudyGroup;

  /// No description provided for @simulationScenarioDescKnowledgeDebate.
  ///
  /// In zh, this message translates to:
  /// **'让不同立场直接碰撞，适合验证观点、证据和边界条件。'**
  String get simulationScenarioDescKnowledgeDebate;

  /// No description provided for @simulationScenarioDescHistoricalRoleplay.
  ///
  /// In zh, this message translates to:
  /// **'带入人物与时代约束，让讨论像真实历史现场一样推进。'**
  String get simulationScenarioDescHistoricalRoleplay;

  /// No description provided for @simulationScenarioDescSocraticDialogue.
  ///
  /// In zh, this message translates to:
  /// **'通过连续追问拆解前提，适合澄清模糊概念与推理漏洞。'**
  String get simulationScenarioDescSocraticDialogue;

  /// No description provided for @simulationScenarioDescCaseAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'围绕具体案例做拆解、诊断和决策，适合实务型主题。'**
  String get simulationScenarioDescCaseAnalysis;

  /// No description provided for @simulationScenarioDescWhatIfPath.
  ///
  /// In zh, this message translates to:
  /// **'比较不同学习或行动路线，适合规划、取舍与资源分配。'**
  String get simulationScenarioDescWhatIfPath;

  /// No description provided for @simulationScenarioDescConceptMapBuild.
  ///
  /// In zh, this message translates to:
  /// **'把知识点织成结构图，适合建立全局框架与连接关系。'**
  String get simulationScenarioDescConceptMapBuild;

  /// No description provided for @simulationScenarioDescErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'专注识别错因、纠偏路径与验证方式，适合查漏补缺。'**
  String get simulationScenarioDescErrorDiagnosis;

  /// No description provided for @simulationFacilitationDescBalanced.
  ///
  /// In zh, this message translates to:
  /// **'适合大多数主题，强调多角色平衡推进，不让任何一方压住全场。'**
  String get simulationFacilitationDescBalanced;

  /// No description provided for @simulationFacilitationDescDebate.
  ///
  /// In zh, this message translates to:
  /// **'主动放大争议和证据冲突，更适合需要碰撞观点的主题。'**
  String get simulationFacilitationDescDebate;

  /// No description provided for @simulationFacilitationDescGuided.
  ///
  /// In zh, this message translates to:
  /// **'更像导师带讨论，强调澄清前提、逐步拆解和用户可跟上。'**
  String get simulationFacilitationDescGuided;

  /// No description provided for @simulationFacilitationDescPractical.
  ///
  /// In zh, this message translates to:
  /// **'优先讨论行动、验证和现实约束，适合技能与方案推演。'**
  String get simulationFacilitationDescPractical;

  /// No description provided for @simulationRoleHonorsStudent.
  ///
  /// In zh, this message translates to:
  /// **'优等生'**
  String get simulationRoleHonorsStudent;

  /// No description provided for @simulationRoleMidStudent.
  ///
  /// In zh, this message translates to:
  /// **'中等生'**
  String get simulationRoleMidStudent;

  /// No description provided for @simulationRoleQuestioner.
  ///
  /// In zh, this message translates to:
  /// **'追问者'**
  String get simulationRoleQuestioner;

  /// No description provided for @simulationRoleSummarizer.
  ///
  /// In zh, this message translates to:
  /// **'总结者'**
  String get simulationRoleSummarizer;

  /// No description provided for @simulationRolePracticeCoach.
  ///
  /// In zh, this message translates to:
  /// **'练习教练'**
  String get simulationRolePracticeCoach;

  /// No description provided for @simulationRoleProExpert.
  ///
  /// In zh, this message translates to:
  /// **'正方专家'**
  String get simulationRoleProExpert;

  /// No description provided for @simulationRoleConExpert.
  ///
  /// In zh, this message translates to:
  /// **'反方专家'**
  String get simulationRoleConExpert;

  /// No description provided for @simulationRoleModerator.
  ///
  /// In zh, this message translates to:
  /// **'主持协调'**
  String get simulationRoleModerator;

  /// No description provided for @simulationRoleEvidenceReviewer.
  ///
  /// In zh, this message translates to:
  /// **'证据审查员'**
  String get simulationRoleEvidenceReviewer;

  /// No description provided for @simulationRolePursuer.
  ///
  /// In zh, this message translates to:
  /// **'追问者'**
  String get simulationRolePursuer;

  /// No description provided for @simulationRoleHistoryMentor.
  ///
  /// In zh, this message translates to:
  /// **'历史导师'**
  String get simulationRoleHistoryMentor;

  /// No description provided for @simulationRoleKeyFigure.
  ///
  /// In zh, this message translates to:
  /// **'关键人物'**
  String get simulationRoleKeyFigure;

  /// No description provided for @simulationRoleEraObserver.
  ///
  /// In zh, this message translates to:
  /// **'时代观察者'**
  String get simulationRoleEraObserver;

  /// No description provided for @simulationRoleStrategyAdvisor.
  ///
  /// In zh, this message translates to:
  /// **'策略顾问'**
  String get simulationRoleStrategyAdvisor;

  /// No description provided for @simulationRoleRecorder.
  ///
  /// In zh, this message translates to:
  /// **'记录官'**
  String get simulationRoleRecorder;

  /// No description provided for @simulationRoleSocrates.
  ///
  /// In zh, this message translates to:
  /// **'苏格拉底'**
  String get simulationRoleSocrates;

  /// No description provided for @simulationRoleSkeptic.
  ///
  /// In zh, this message translates to:
  /// **'怀疑者'**
  String get simulationRoleSkeptic;

  /// No description provided for @simulationRoleDeconstructor.
  ///
  /// In zh, this message translates to:
  /// **'拆解者'**
  String get simulationRoleDeconstructor;

  /// No description provided for @simulationRoleApplier.
  ///
  /// In zh, this message translates to:
  /// **'应用者'**
  String get simulationRoleApplier;

  /// No description provided for @simulationRoleCaseMentor.
  ///
  /// In zh, this message translates to:
  /// **'案例导师'**
  String get simulationRoleCaseMentor;

  /// No description provided for @simulationRoleDiagnostician.
  ///
  /// In zh, this message translates to:
  /// **'诊断官'**
  String get simulationRoleDiagnostician;

  /// No description provided for @simulationRolePractitioner.
  ///
  /// In zh, this message translates to:
  /// **'实践派'**
  String get simulationRolePractitioner;

  /// No description provided for @simulationRoleCounterExample.
  ///
  /// In zh, this message translates to:
  /// **'反例提出者'**
  String get simulationRoleCounterExample;

  /// No description provided for @simulationRoleDecisionRecorder.
  ///
  /// In zh, this message translates to:
  /// **'决策记录官'**
  String get simulationRoleDecisionRecorder;

  /// No description provided for @simulationRoleCurrentRoute.
  ///
  /// In zh, this message translates to:
  /// **'当前路线'**
  String get simulationRoleCurrentRoute;

  /// No description provided for @simulationRoleRadicalRoute.
  ///
  /// In zh, this message translates to:
  /// **'激进路线'**
  String get simulationRoleRadicalRoute;

  /// No description provided for @simulationRoleRiskObserver.
  ///
  /// In zh, this message translates to:
  /// **'风险观察者'**
  String get simulationRoleRiskObserver;

  /// No description provided for @simulationRoleResourceScheduler.
  ///
  /// In zh, this message translates to:
  /// **'资源调度者'**
  String get simulationRoleResourceScheduler;

  /// No description provided for @simulationRoleVerifier.
  ///
  /// In zh, this message translates to:
  /// **'验证者'**
  String get simulationRoleVerifier;

  /// No description provided for @simulationRoleStructurer.
  ///
  /// In zh, this message translates to:
  /// **'结构师'**
  String get simulationRoleStructurer;

  /// No description provided for @simulationRoleConnector.
  ///
  /// In zh, this message translates to:
  /// **'连接者'**
  String get simulationRoleConnector;

  /// No description provided for @simulationRoleCounterExampleChecker.
  ///
  /// In zh, this message translates to:
  /// **'反例检查员'**
  String get simulationRoleCounterExampleChecker;

  /// No description provided for @simulationRoleBridgeBuilder.
  ///
  /// In zh, this message translates to:
  /// **'桥梁构建者'**
  String get simulationRoleBridgeBuilder;

  /// No description provided for @simulationRoleErrorAnalyst.
  ///
  /// In zh, this message translates to:
  /// **'错因分析师'**
  String get simulationRoleErrorAnalyst;

  /// No description provided for @simulationRoleCorrectionCoach.
  ///
  /// In zh, this message translates to:
  /// **'纠偏教练'**
  String get simulationRoleCorrectionCoach;

  /// No description provided for @simulationRoleQuestionDeconstructor.
  ///
  /// In zh, this message translates to:
  /// **'题面解构者'**
  String get simulationRoleQuestionDeconstructor;

  /// No description provided for @simulationRoleMigrationCoach.
  ///
  /// In zh, this message translates to:
  /// **'迁移教练'**
  String get simulationRoleMigrationCoach;

  /// No description provided for @simulationRoleStudyBuddy.
  ///
  /// In zh, this message translates to:
  /// **'学习伙伴'**
  String get simulationRoleStudyBuddy;

  /// No description provided for @simulationRoleCurrentDiscussionTitle.
  ///
  /// In zh, this message translates to:
  /// **'当前讨论流'**
  String get simulationRoleCurrentDiscussionTitle;

  /// No description provided for @simulationBulletOpeningFormat.
  ///
  /// In zh, this message translates to:
  /// **'开场重点：{message}'**
  String simulationBulletOpeningFormat(Object message);

  /// No description provided for @simulationScenarioParticipantOptionsDefault0.
  ///
  /// In zh, this message translates to:
  /// **'学习伙伴'**
  String get simulationScenarioParticipantOptionsDefault0;

  /// No description provided for @simulationScenarioParticipantOptionsDefault1.
  ///
  /// In zh, this message translates to:
  /// **'提问者'**
  String get simulationScenarioParticipantOptionsDefault1;

  /// No description provided for @simulationScenarioParticipantOptionsDefault2.
  ///
  /// In zh, this message translates to:
  /// **'总结者'**
  String get simulationScenarioParticipantOptionsDefault2;

  /// No description provided for @simulationScenarioLabelStudyGroup.
  ///
  /// In zh, this message translates to:
  /// **'学习小组'**
  String get simulationScenarioLabelStudyGroup;

  /// No description provided for @simulationScenarioLabelKnowledgeDebate.
  ///
  /// In zh, this message translates to:
  /// **'知识辩论'**
  String get simulationScenarioLabelKnowledgeDebate;

  /// No description provided for @simulationScenarioLabelHistoricalRoleplay.
  ///
  /// In zh, this message translates to:
  /// **'历史角色扮演'**
  String get simulationScenarioLabelHistoricalRoleplay;

  /// No description provided for @simulationScenarioLabelSocraticDialogue.
  ///
  /// In zh, this message translates to:
  /// **'苏格拉底对话'**
  String get simulationScenarioLabelSocraticDialogue;

  /// No description provided for @simulationScenarioLabelCaseAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'案例分析'**
  String get simulationScenarioLabelCaseAnalysis;

  /// No description provided for @simulationScenarioLabelWhatIfPath.
  ///
  /// In zh, this message translates to:
  /// **'如果路径'**
  String get simulationScenarioLabelWhatIfPath;

  /// No description provided for @simulationScenarioLabelConceptMapBuild.
  ///
  /// In zh, this message translates to:
  /// **'概念图构建'**
  String get simulationScenarioLabelConceptMapBuild;

  /// No description provided for @simulationScenarioLabelErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'错误诊断'**
  String get simulationScenarioLabelErrorDiagnosis;

  /// No description provided for @openclawPairImportedSaved.
  ///
  /// In zh, this message translates to:
  /// **'已导入并保存 OpenClaw 配对配置'**
  String get openclawPairImportedSaved;

  /// No description provided for @openclawPairImportedVerifyFailed.
  ///
  /// In zh, this message translates to:
  /// **'配对配置已导入，但当前连接验证失败'**
  String get openclawPairImportedVerifyFailed;

  /// No description provided for @openclawClipboardNoPairingPayload.
  ///
  /// In zh, this message translates to:
  /// **'剪贴板里没有识别到 OpenClaw 配对串或二维码 JSON'**
  String get openclawClipboardNoPairingPayload;

  /// No description provided for @openclawImportedFromClipboard.
  ///
  /// In zh, this message translates to:
  /// **'已从剪贴板导入 OpenClaw 配对配置'**
  String get openclawImportedFromClipboard;

  /// No description provided for @openclawConnectedToDevice.
  ///
  /// In zh, this message translates to:
  /// **'已连接到 {deviceName}'**
  String openclawConnectedToDevice(Object deviceName);

  /// No description provided for @openclawImportedDevicePairing.
  ///
  /// In zh, this message translates to:
  /// **'已导入 {deviceName} 的配对配置'**
  String openclawImportedDevicePairing(Object deviceName);

  /// No description provided for @openclawScannedPairingImported.
  ///
  /// In zh, this message translates to:
  /// **'已扫码导入 OpenClaw 配对配置'**
  String get openclawScannedPairingImported;

  /// No description provided for @openclawScannedConnectedToDevice.
  ///
  /// In zh, this message translates to:
  /// **'已扫码连接到 {deviceName}'**
  String openclawScannedConnectedToDevice(Object deviceName);

  /// No description provided for @openclawUnrecognizedContent.
  ///
  /// In zh, this message translates to:
  /// **'无法识别这段内容，请检查是否包含 gateway_url 与 token'**
  String get openclawUnrecognizedContent;

  /// No description provided for @openclawCameraPermissionNeeded.
  ///
  /// In zh, this message translates to:
  /// **'需要相机权限才能扫码配对。你也可以改用\"从剪贴板导入\"或\"粘贴配对串\"。'**
  String get openclawCameraPermissionNeeded;

  /// No description provided for @openclawQrNotPairingContent.
  ///
  /// In zh, this message translates to:
  /// **'扫到的二维码不是可识别的 OpenClaw 配对内容'**
  String get openclawQrNotPairingContent;

  /// No description provided for @openclawRemoteTemplateFilled.
  ///
  /// In zh, this message translates to:
  /// **'已填入远程连接模板，接下来补入授权令牌或导入配对串即可'**
  String get openclawRemoteTemplateFilled;

  /// No description provided for @openclawPairingCodeExpired.
  ///
  /// In zh, this message translates to:
  /// **'配对码已过期'**
  String get openclawPairingCodeExpired;

  /// No description provided for @openclawPairingExpiresSeconds.
  ///
  /// In zh, this message translates to:
  /// **'请在 {seconds} 秒内完成配对'**
  String openclawPairingExpiresSeconds(Object seconds);

  /// No description provided for @openclawPairingExpiresMinutes.
  ///
  /// In zh, this message translates to:
  /// **'请在 {minutes} 分 {seconds} 秒内完成配对'**
  String openclawPairingExpiresMinutes(Object minutes, Object seconds);

  /// No description provided for @openclawInvalidUrlFormat.
  ///
  /// In zh, this message translates to:
  /// **'请输入以 http://、https://、ws:// 或 wss:// 开头的地址'**
  String get openclawInvalidUrlFormat;

  /// No description provided for @openclawValidAddressRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入有效的 OpenClaw 地址'**
  String get openclawValidAddressRequired;

  /// No description provided for @openclawDisconnected.
  ///
  /// In zh, this message translates to:
  /// **'已断开 OpenClaw 连接'**
  String get openclawDisconnected;

  /// No description provided for @openclawPairingCodeGenerated.
  ///
  /// In zh, this message translates to:
  /// **'已生成配对码 {code}'**
  String openclawPairingCodeGenerated(Object code);

  /// No description provided for @openclawDeviceTokenRequired.
  ///
  /// In zh, this message translates to:
  /// **'请输入设备令牌后再完成配对'**
  String get openclawDeviceTokenRequired;

  /// No description provided for @openclawDevicePairingComplete.
  ///
  /// In zh, this message translates to:
  /// **'设备配对已完成'**
  String get openclawDevicePairingComplete;

  /// No description provided for @openclawNoExecutionPermission.
  ///
  /// In zh, this message translates to:
  /// **'当前网关可访问，但没有执行权限，暂时无法重试队列'**
  String get openclawNoExecutionPermission;

  /// No description provided for @openclawExecutionEndpointUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'当前网关可访问，但执行入口不可用，暂时无法重试队列'**
  String get openclawExecutionEndpointUnavailable;

  /// No description provided for @openclawExecutionEngineNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'执行引擎尚未连接，暂时无法重试队列'**
  String get openclawExecutionEngineNotConnected;

  /// No description provided for @openclawQueuedTasksResubmitted.
  ///
  /// In zh, this message translates to:
  /// **'已重新提交 {count} 个排队任务'**
  String openclawQueuedTasksResubmitted(Object count);

  /// No description provided for @openclawNoRetryableTasks.
  ///
  /// In zh, this message translates to:
  /// **'当前没有可重试的排队任务'**
  String get openclawNoRetryableTasks;

  /// No description provided for @openclawPairingCodeCopied.
  ///
  /// In zh, this message translates to:
  /// **'配对码已复制'**
  String get openclawPairingCodeCopied;

  /// No description provided for @openclawImportPairingString.
  ///
  /// In zh, this message translates to:
  /// **'导入配对串'**
  String get openclawImportPairingString;

  /// No description provided for @openclawPairingOrQrLabel.
  ///
  /// In zh, this message translates to:
  /// **'配对串或二维码内容'**
  String get openclawPairingOrQrLabel;

  /// No description provided for @openclawPairingPasteHint.
  ///
  /// In zh, this message translates to:
  /// **'粘贴 OpenClaw 桌面端分享的 JSON、openclaw://pair?... 链接，或包含 gateway_url / pair_token 的文本'**
  String get openclawPairingPasteHint;

  /// No description provided for @openclawImportAndSave.
  ///
  /// In zh, this message translates to:
  /// **'导入并保存'**
  String get openclawImportAndSave;

  /// No description provided for @openclawApplyWizard.
  ///
  /// In zh, this message translates to:
  /// **'应用向导'**
  String get openclawApplyWizard;

  /// No description provided for @openclawDisconnect.
  ///
  /// In zh, this message translates to:
  /// **'断开连接'**
  String get openclawDisconnect;

  /// No description provided for @openclawDisconnectConfirmBody.
  ///
  /// In zh, this message translates to:
  /// **'这会清除本地保存的 OpenClaw 连接配置。'**
  String get openclawDisconnectConfirmBody;

  /// No description provided for @openclawDisconnectAction.
  ///
  /// In zh, this message translates to:
  /// **'断开'**
  String get openclawDisconnectAction;

  /// No description provided for @openclawGatewayOnlineNoExecPermission.
  ///
  /// In zh, this message translates to:
  /// **'网关在线，但当前令牌没有执行权限'**
  String get openclawGatewayOnlineNoExecPermission;

  /// No description provided for @openclawGatewayOnlineExecNotReady.
  ///
  /// In zh, this message translates to:
  /// **'网关在线，但执行接口没有准备好'**
  String get openclawGatewayOnlineExecNotReady;

  /// No description provided for @openclawNeedExecutionChainCheck.
  ///
  /// In zh, this message translates to:
  /// **'需要补一层执行链路排查'**
  String get openclawNeedExecutionChainCheck;

  /// No description provided for @openclawTroubleshootNoPermissionBody.
  ///
  /// In zh, this message translates to:
  /// **'当前状态说明健康检查能通过，但真正发起执行会被拒绝。优先更换具备 `operator.write` scope 的令牌，或改用设备配对 + WebSocket。'**
  String get openclawTroubleshootNoPermissionBody;

  /// No description provided for @openclawTroubleshootMissingEndpointBody.
  ///
  /// In zh, this message translates to:
  /// **'当前地址可访问，但缺少 `/v1/responses` 执行入口。请确认 OpenClaw 网关版本、代理转发和 transport 选择是否一致。'**
  String get openclawTroubleshootMissingEndpointBody;

  /// No description provided for @openclawTroubleshootGenericBody.
  ///
  /// In zh, this message translates to:
  /// **'建议先重新测试连接，再检查网关地址、认证方式和 transport 是否与 OpenClaw 当前实例一致。'**
  String get openclawTroubleshootGenericBody;

  /// No description provided for @openclawStatusReadyForTasks.
  ///
  /// In zh, this message translates to:
  /// **'已准备好接手任务'**
  String get openclawStatusReadyForTasks;

  /// No description provided for @openclawStatusConfirmingConnection.
  ///
  /// In zh, this message translates to:
  /// **'正在确认连接状态'**
  String get openclawStatusConfirmingConnection;

  /// No description provided for @openclawStatusOnlineNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'网关在线，但没有执行权限'**
  String get openclawStatusOnlineNoPermission;

  /// No description provided for @openclawStatusNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'暂时还没连上'**
  String get openclawStatusNotConnected;

  /// No description provided for @openclawStatusNotConfigured.
  ///
  /// In zh, this message translates to:
  /// **'还没有接入 OpenClaw'**
  String get openclawStatusNotConfigured;

  /// No description provided for @openclawStatusConnectedSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'连接保持正常，你可以直接从任务页或聊天页把工作交给 OpenClaw。'**
  String get openclawStatusConnectedSubtitle;

  /// No description provided for @openclawStatusConnectingSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'我们正在确认引擎状态，保存后的结果会同步显示在这里。'**
  String get openclawStatusConnectingSubtitle;

  /// No description provided for @openclawStatusNoPermissionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'当前令牌能访问网关，但真正执行会被拒绝。这里需要处理权限，而不是单纯重填地址。'**
  String get openclawStatusNoPermissionSubtitle;

  /// No description provided for @openclawStatusErrorSubtitleFallback.
  ///
  /// In zh, this message translates to:
  /// **'先检查地址、认证方式和传输协议，再重新测试连接。'**
  String get openclawStatusErrorSubtitleFallback;

  /// No description provided for @openclawStatusDisconnectedSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'完成一次连接后，之后的委派、排队和最近活动都会在各入口自动联动。'**
  String get openclawStatusDisconnectedSubtitle;

  /// No description provided for @openclawUnsavedChanges.
  ///
  /// In zh, this message translates to:
  /// **'未保存更改'**
  String get openclawUnsavedChanges;

  /// No description provided for @openclawDevicePairing.
  ///
  /// In zh, this message translates to:
  /// **'设备配对'**
  String get openclawDevicePairing;

  /// No description provided for @openclawTokenAuth.
  ///
  /// In zh, this message translates to:
  /// **'令牌认证'**
  String get openclawTokenAuth;

  /// No description provided for @openclawQueuedRequestCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个待处理'**
  String openclawQueuedRequestCount(Object count);

  /// No description provided for @openclawQuickConnect.
  ///
  /// In zh, this message translates to:
  /// **'快速接入'**
  String get openclawQuickConnect;

  /// No description provided for @openclawCustomConfig.
  ///
  /// In zh, this message translates to:
  /// **'自定义配置'**
  String get openclawCustomConfig;

  /// No description provided for @openclawCustomConfigDesc.
  ///
  /// In zh, this message translates to:
  /// **'使用自定义网关地址和令牌连接'**
  String get openclawCustomConfigDesc;

  /// No description provided for @openclawGuestMainDesc.
  ///
  /// In zh, this message translates to:
  /// **'使用本地网关直连'**
  String get openclawGuestMainDesc;

  /// No description provided for @openclawGuestMainLabel.
  ///
  /// In zh, this message translates to:
  /// **'本地网关'**
  String get openclawGuestMainLabel;

  /// No description provided for @openclawImportFromClipboard.
  ///
  /// In zh, this message translates to:
  /// **'从剪贴板导入'**
  String get openclawImportFromClipboard;

  /// No description provided for @openclawPastePairingString.
  ///
  /// In zh, this message translates to:
  /// **'粘贴配对串'**
  String get openclawPastePairingString;

  /// No description provided for @openclawScanToPair.
  ///
  /// In zh, this message translates to:
  /// **'扫码配对'**
  String get openclawScanToPair;

  /// No description provided for @openclawTailscaleRemoteNode.
  ///
  /// In zh, this message translates to:
  /// **'Tailscale 远程节点'**
  String get openclawTailscaleRemoteNode;

  /// No description provided for @openclawTailscaleIpOrDomain.
  ///
  /// In zh, this message translates to:
  /// **'Tailscale IP 或域名'**
  String get openclawTailscaleIpOrDomain;

  /// No description provided for @openclawTailscaleHint.
  ///
  /// In zh, this message translates to:
  /// **'例如 100.88.1.24 或 devbox.tail123.ts.net'**
  String get openclawTailscaleHint;

  /// No description provided for @openclawTailscaleHelperText.
  ///
  /// In zh, this message translates to:
  /// **'如果你的 OpenClaw 暴露在 Tailscale 上，这里只需要填节点 IP 或 MagicDNS 域名，Sparkle 会自动补上标准端口与 WebSocket 连接方式。'**
  String get openclawTailscaleHelperText;

  /// No description provided for @openclawTailscaleLabel.
  ///
  /// In zh, this message translates to:
  /// **'Tailscale'**
  String get openclawTailscaleLabel;

  /// No description provided for @openclawCloudflareTunnel.
  ///
  /// In zh, this message translates to:
  /// **'Cloudflare Tunnel'**
  String get openclawCloudflareTunnel;

  /// No description provided for @openclawTunnelDomain.
  ///
  /// In zh, this message translates to:
  /// **'Tunnel 域名'**
  String get openclawTunnelDomain;

  /// No description provided for @openclawCloudflareHint.
  ///
  /// In zh, this message translates to:
  /// **'例如 openclaw.example.com'**
  String get openclawCloudflareHint;

  /// No description provided for @openclawCloudflareHelperText.
  ///
  /// In zh, this message translates to:
  /// **'如果你通过 Cloudflare Tunnel 暴露 OpenClaw，这里填入域名即可。Sparkle 会按 HTTPS/WSS 方式生成连接配置。'**
  String get openclawCloudflareHelperText;

  /// No description provided for @openclawCloudflareLabel.
  ///
  /// In zh, this message translates to:
  /// **'Cloudflare'**
  String get openclawCloudflareLabel;

  /// No description provided for @openclawPresetSelected.
  ///
  /// In zh, this message translates to:
  /// **'已选中\"{label}\"。连接细节会自动填入；如果随后提示缺执行权限，优先更换具备 `operator.write` scope 的令牌，或改用设备配对。'**
  String openclawPresetSelected(Object label);

  /// No description provided for @openclawGatewayAddress.
  ///
  /// In zh, this message translates to:
  /// **'网关地址'**
  String get openclawGatewayAddress;

  /// No description provided for @openclawGatewayHint.
  ///
  /// In zh, this message translates to:
  /// **'例如 http://localhost:8080'**
  String get openclawGatewayHint;

  /// No description provided for @openclawAuthMode.
  ///
  /// In zh, this message translates to:
  /// **'认证方式'**
  String get openclawAuthMode;

  /// No description provided for @openclawAuthToken.
  ///
  /// In zh, this message translates to:
  /// **'认证令牌'**
  String get openclawAuthToken;

  /// No description provided for @openclawAuthTokenHint.
  ///
  /// In zh, this message translates to:
  /// **'粘贴 OpenClaw 网关令牌'**
  String get openclawAuthTokenHint;

  /// No description provided for @openclawDeviceToken.
  ///
  /// In zh, this message translates to:
  /// **'设备令牌'**
  String get openclawDeviceToken;

  /// No description provided for @openclawDeviceTokenHint.
  ///
  /// In zh, this message translates to:
  /// **'配对完成后粘贴设备令牌'**
  String get openclawDeviceTokenHint;

  /// No description provided for @openclawPairingCode.
  ///
  /// In zh, this message translates to:
  /// **'配对码'**
  String get openclawPairingCode;

  /// No description provided for @openclawPairingCodeInstructions.
  ///
  /// In zh, this message translates to:
  /// **'请在 OpenClaw 桌面端输入这 6 位配对码，然后把返回的设备令牌粘贴到上方。'**
  String get openclawPairingCodeInstructions;

  /// No description provided for @openclawGeneratePairingCode.
  ///
  /// In zh, this message translates to:
  /// **'生成配对码'**
  String get openclawGeneratePairingCode;

  /// No description provided for @openclawCompletePairing.
  ///
  /// In zh, this message translates to:
  /// **'完成配对'**
  String get openclawCompletePairing;

  /// No description provided for @openclawCancelPairing.
  ///
  /// In zh, this message translates to:
  /// **'取消配对'**
  String get openclawCancelPairing;

  /// No description provided for @openclawTransportProtocol.
  ///
  /// In zh, this message translates to:
  /// **'传输协议'**
  String get openclawTransportProtocol;

  /// No description provided for @openclawDeviceAuthDesc.
  ///
  /// In zh, this message translates to:
  /// **'适合与本机 OpenClaw 配对，一次完成后后续连接会更顺手。'**
  String get openclawDeviceAuthDesc;

  /// No description provided for @openclawTokenAuthDesc.
  ///
  /// In zh, this message translates to:
  /// **'适合你已经有现成的网关令牌，需要快速验证或切换环境时使用。'**
  String get openclawTokenAuthDesc;

  /// No description provided for @openclawWebSocketTransportDesc.
  ///
  /// In zh, this message translates to:
  /// **'WebSocket 更适合保持持续连接，适合频繁委派和状态回推。'**
  String get openclawWebSocketTransportDesc;

  /// No description provided for @openclawHttpTransportDesc.
  ///
  /// In zh, this message translates to:
  /// **'HTTP 更适合手动验证和快速测试连接。'**
  String get openclawHttpTransportDesc;

  /// No description provided for @openclawDefaultConnectionReady.
  ///
  /// In zh, this message translates to:
  /// **'已为你准备好默认连接细节'**
  String get openclawDefaultConnectionReady;

  /// No description provided for @openclawTestConnection.
  ///
  /// In zh, this message translates to:
  /// **'测试连接'**
  String get openclawTestConnection;

  /// No description provided for @openclawSaveConfig.
  ///
  /// In zh, this message translates to:
  /// **'保存配置'**
  String get openclawSaveConfig;

  /// No description provided for @openclawRetryQueue.
  ///
  /// In zh, this message translates to:
  /// **'重试队列'**
  String get openclawRetryQueue;

  /// No description provided for @accountabilityPartnerDefault.
  ///
  /// In zh, this message translates to:
  /// **'责任伙伴'**
  String get accountabilityPartnerDefault;

  /// No description provided for @accountabilityEndPartnership.
  ///
  /// In zh, this message translates to:
  /// **'结束伙伴关系'**
  String get accountabilityEndPartnership;

  /// No description provided for @accountabilityDashboardLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'伙伴工作台加载失败'**
  String get accountabilityDashboardLoadFailed;

  /// No description provided for @accountabilityNudgeSentDefault.
  ///
  /// In zh, this message translates to:
  /// **'已通过站内提醒发送，对方在线时会实时看到'**
  String get accountabilityNudgeSentDefault;

  /// No description provided for @accountabilityNudgeCooldown.
  ///
  /// In zh, this message translates to:
  /// **'刚提醒过，冷却期内不会重复发送。提醒会以站内提示的形式送达，对方在线时会实时看到。'**
  String get accountabilityNudgeCooldown;

  /// No description provided for @accountabilityNudgeFailed.
  ///
  /// In zh, this message translates to:
  /// **'提醒发送失败，请稍后再试'**
  String get accountabilityNudgeFailed;

  /// No description provided for @accountabilityEndPartnershipConfirm.
  ///
  /// In zh, this message translates to:
  /// **'确定要结束这段责任伙伴关系吗？'**
  String get accountabilityEndPartnershipConfirm;

  /// No description provided for @accountabilityPartnershipEnded.
  ///
  /// In zh, this message translates to:
  /// **'伙伴关系已结束'**
  String get accountabilityPartnershipEnded;

  /// No description provided for @accountabilityMyGoal.
  ///
  /// In zh, this message translates to:
  /// **'我的目标'**
  String get accountabilityMyGoal;

  /// No description provided for @accountabilityGoalNotSet.
  ///
  /// In zh, this message translates to:
  /// **'还没有填写目标'**
  String get accountabilityGoalNotSet;

  /// No description provided for @accountabilityGrowingTogether.
  ///
  /// In zh, this message translates to:
  /// **'伙伴共成长'**
  String get accountabilityGrowingTogether;

  /// No description provided for @accountabilityRecentShares.
  ///
  /// In zh, this message translates to:
  /// **'最近分享'**
  String get accountabilityRecentShares;

  /// No description provided for @accountabilitySharedItem.
  ///
  /// In zh, this message translates to:
  /// **'已分享内容'**
  String get accountabilitySharedItem;

  /// No description provided for @accountabilityMonthlyHeatmap.
  ///
  /// In zh, this message translates to:
  /// **'月度打卡热力图'**
  String get accountabilityMonthlyHeatmap;

  /// No description provided for @accountabilityPartnerAchievements.
  ///
  /// In zh, this message translates to:
  /// **'伙伴成就'**
  String get accountabilityPartnerAchievements;

  /// No description provided for @accountabilityPartnerNoAchievements.
  ///
  /// In zh, this message translates to:
  /// **'伙伴还没有解锁专属成就，先互相打卡一轮试试看。'**
  String get accountabilityPartnerNoAchievements;

  /// No description provided for @accountabilityRecentCheckins.
  ///
  /// In zh, this message translates to:
  /// **'最近打卡'**
  String get accountabilityRecentCheckins;

  /// No description provided for @accountabilityNoCheckinRecords.
  ///
  /// In zh, this message translates to:
  /// **'还没有打卡记录'**
  String get accountabilityNoCheckinRecords;

  /// No description provided for @accountabilityNoCheckinHint.
  ///
  /// In zh, this message translates to:
  /// **'今天先发一条简短进展，伙伴关系就会开始有温度。'**
  String get accountabilityNoCheckinHint;

  /// No description provided for @accountabilityCheckedInToday.
  ///
  /// In zh, this message translates to:
  /// **'今天已打卡'**
  String get accountabilityCheckedInToday;

  /// No description provided for @accountabilityCheckInToday.
  ///
  /// In zh, this message translates to:
  /// **'今日打卡'**
  String get accountabilityCheckInToday;

  /// No description provided for @accountabilityTotalCheckins.
  ///
  /// In zh, this message translates to:
  /// **'总打卡'**
  String get accountabilityTotalCheckins;

  /// No description provided for @accountabilityCheckedIn.
  ///
  /// In zh, this message translates to:
  /// **'已打卡'**
  String get accountabilityCheckedIn;

  /// No description provided for @accountabilityCheckin.
  ///
  /// In zh, this message translates to:
  /// **'打卡'**
  String get accountabilityCheckin;

  /// No description provided for @accountabilityNudge.
  ///
  /// In zh, this message translates to:
  /// **'提醒'**
  String get accountabilityNudge;

  /// No description provided for @accountabilityShare.
  ///
  /// In zh, this message translates to:
  /// **'分享'**
  String get accountabilityShare;

  /// No description provided for @accountabilityChat.
  ///
  /// In zh, this message translates to:
  /// **'聊天'**
  String get accountabilityChat;

  /// No description provided for @accountabilityInviteSentWait.
  ///
  /// In zh, this message translates to:
  /// **'邀请已发出，等待对方确认后才能进入伙伴工作台。'**
  String get accountabilityInviteSentWait;

  /// No description provided for @accountabilityInvitePendingConfirm.
  ///
  /// In zh, this message translates to:
  /// **'这条伙伴邀请还待你确认，先去邀请页处理后再回来。'**
  String get accountabilityInvitePendingConfirm;

  /// No description provided for @accountabilityDashboardNotAvailable.
  ///
  /// In zh, this message translates to:
  /// **'当前伙伴关系暂时不可进入完整工作台。'**
  String get accountabilityDashboardNotAvailable;

  /// No description provided for @accountabilityInvitePending.
  ///
  /// In zh, this message translates to:
  /// **'伙伴邀请待处理'**
  String get accountabilityInvitePending;

  /// No description provided for @accountabilityDashboardUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'伙伴工作台暂不可用'**
  String get accountabilityDashboardUnavailable;

  /// No description provided for @accountabilityViewStatus.
  ///
  /// In zh, this message translates to:
  /// **'查看状态'**
  String get accountabilityViewStatus;

  /// No description provided for @accountabilityHandleInvite.
  ///
  /// In zh, this message translates to:
  /// **'去处理邀请'**
  String get accountabilityHandleInvite;

  /// No description provided for @accountabilityContinueChat.
  ///
  /// In zh, this message translates to:
  /// **'继续聊天'**
  String get accountabilityContinueChat;

  /// No description provided for @accountabilityNoPendingPolicies.
  ///
  /// In zh, this message translates to:
  /// **'当前没有待执行的问责策略。'**
  String get accountabilityNoPendingPolicies;

  /// No description provided for @accountabilityPendingPolicies.
  ///
  /// In zh, this message translates to:
  /// **'待执行策略'**
  String get accountabilityPendingPolicies;

  /// No description provided for @accountabilityNoRecentReflections.
  ///
  /// In zh, this message translates to:
  /// **'最近还没有新的跨事件反思。'**
  String get accountabilityNoRecentReflections;

  /// No description provided for @accountabilityRecentReflections.
  ///
  /// In zh, this message translates to:
  /// **'近期反思'**
  String get accountabilityRecentReflections;

  /// No description provided for @accountabilityForesightHint.
  ///
  /// In zh, this message translates to:
  /// **'前瞻提示'**
  String get accountabilityForesightHint;

  /// No description provided for @accountabilityNoForesightHint.
  ///
  /// In zh, this message translates to:
  /// **'暂无前瞻提示。'**
  String get accountabilityNoForesightHint;

  /// No description provided for @accountabilityInterventionIneffective.
  ///
  /// In zh, this message translates to:
  /// **'干预未奏效'**
  String get accountabilityInterventionIneffective;

  /// No description provided for @accountabilityPlanStall.
  ///
  /// In zh, this message translates to:
  /// **'计划停滞'**
  String get accountabilityPlanStall;

  /// No description provided for @accountabilityOverload.
  ///
  /// In zh, this message translates to:
  /// **'负荷过载'**
  String get accountabilityOverload;

  /// No description provided for @accountabilityTooDifficult.
  ///
  /// In zh, this message translates to:
  /// **'任务过难'**
  String get accountabilityTooDifficult;

  /// No description provided for @accountabilityUnclear.
  ///
  /// In zh, this message translates to:
  /// **'任务不清晰'**
  String get accountabilityUnclear;

  /// No description provided for @accountabilityAbandoned.
  ///
  /// In zh, this message translates to:
  /// **'中途放下'**
  String get accountabilityAbandoned;

  /// No description provided for @accountabilityReflectionSummary.
  ///
  /// In zh, this message translates to:
  /// **'反思摘要'**
  String get accountabilityReflectionSummary;

  /// No description provided for @accountabilityDimPace.
  ///
  /// In zh, this message translates to:
  /// **'节奏'**
  String get accountabilityDimPace;

  /// No description provided for @accountabilityDimCompletionRate.
  ///
  /// In zh, this message translates to:
  /// **'完成率'**
  String get accountabilityDimCompletionRate;

  /// No description provided for @accountabilityDimEngagement.
  ///
  /// In zh, this message translates to:
  /// **'投入度'**
  String get accountabilityDimEngagement;

  /// No description provided for @accountabilityDimMood.
  ///
  /// In zh, this message translates to:
  /// **'情绪'**
  String get accountabilityDimMood;

  /// No description provided for @accountabilityDimPlanAdherence.
  ///
  /// In zh, this message translates to:
  /// **'计划跟随'**
  String get accountabilityDimPlanAdherence;

  /// No description provided for @accountabilityMoodLow.
  ///
  /// In zh, this message translates to:
  /// **'低落'**
  String get accountabilityMoodLow;

  /// No description provided for @accountabilityMoodOkay.
  ///
  /// In zh, this message translates to:
  /// **'一般'**
  String get accountabilityMoodOkay;

  /// No description provided for @accountabilityMoodSteady.
  ///
  /// In zh, this message translates to:
  /// **'平稳'**
  String get accountabilityMoodSteady;

  /// No description provided for @accountabilityMoodGood.
  ///
  /// In zh, this message translates to:
  /// **'不错'**
  String get accountabilityMoodGood;

  /// No description provided for @accountabilityMoodGreat.
  ///
  /// In zh, this message translates to:
  /// **'很棒'**
  String get accountabilityMoodGreat;

  /// No description provided for @accountabilityPartner.
  ///
  /// In zh, this message translates to:
  /// **'伙伴'**
  String get accountabilityPartner;

  /// No description provided for @accountabilityLike.
  ///
  /// In zh, this message translates to:
  /// **'点赞'**
  String get accountabilityLike;

  /// No description provided for @accountabilityEncourage.
  ///
  /// In zh, this message translates to:
  /// **'鼓励'**
  String get accountabilityEncourage;

  /// No description provided for @accountabilityEncourageSent.
  ///
  /// In zh, this message translates to:
  /// **'已为伙伴点亮鼓励'**
  String get accountabilityEncourageSent;

  /// No description provided for @accountabilitySendEncourage.
  ///
  /// In zh, this message translates to:
  /// **'发送鼓励'**
  String get accountabilitySendEncourage;

  /// No description provided for @accountabilityEncourageHint.
  ///
  /// In zh, this message translates to:
  /// **'写一句你想对伙伴说的话'**
  String get accountabilityEncourageHint;

  /// No description provided for @accountabilitySend.
  ///
  /// In zh, this message translates to:
  /// **'发送'**
  String get accountabilitySend;

  /// No description provided for @accountabilityEncourageDelivered.
  ///
  /// In zh, this message translates to:
  /// **'鼓励已送达'**
  String get accountabilityEncourageDelivered;

  /// No description provided for @accountabilityTodayProgressHint.
  ///
  /// In zh, this message translates to:
  /// **'今日进展...'**
  String get accountabilityTodayProgressHint;

  /// No description provided for @accountabilityTodayMood.
  ///
  /// In zh, this message translates to:
  /// **'今日心情:'**
  String get accountabilityTodayMood;

  /// No description provided for @accountabilityPublishCheckin.
  ///
  /// In zh, this message translates to:
  /// **'发布打卡'**
  String get accountabilityPublishCheckin;

  /// No description provided for @accountabilityProgressRequired.
  ///
  /// In zh, this message translates to:
  /// **'请写一句今天的进展'**
  String get accountabilityProgressRequired;

  /// No description provided for @accountabilityCheckinSuccess.
  ///
  /// In zh, this message translates to:
  /// **'打卡成功，伙伴已经能看到了'**
  String get accountabilityCheckinSuccess;

  /// No description provided for @openclawImportedPairing.
  ///
  /// In zh, this message translates to:
  /// **'已导入 OpenClaw 配对配置'**
  String get openclawImportedPairing;

  /// No description provided for @accountabilityPartnerGoal.
  ///
  /// In zh, this message translates to:
  /// **'{partnerName} 的目标'**
  String accountabilityPartnerGoal(Object partnerName);

  /// No description provided for @accountabilityPartnerGoalNotSet.
  ///
  /// In zh, this message translates to:
  /// **'对方还没填写目标'**
  String get accountabilityPartnerGoalNotSet;

  /// No description provided for @accountabilityMe.
  ///
  /// In zh, this message translates to:
  /// **'我'**
  String get accountabilityMe;

  /// No description provided for @accountabilityThem.
  ///
  /// In zh, this message translates to:
  /// **'TA'**
  String get accountabilityThem;

  /// No description provided for @accountabilityStreakDays.
  ///
  /// In zh, this message translates to:
  /// **'{days} 天'**
  String accountabilityStreakDays(Object days);

  /// No description provided for @accountabilityCheckinMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{minutes}分钟'**
  String accountabilityCheckinMinutes(Object minutes);

  /// No description provided for @accountabilityDaysTogether.
  ///
  /// In zh, this message translates to:
  /// **'一起坚持了 {days} 天'**
  String accountabilityDaysTogether(Object days);

  /// No description provided for @accountabilityMyStreakDays.
  ///
  /// In zh, this message translates to:
  /// **'我 {days} 天'**
  String accountabilityMyStreakDays(Object days);

  /// No description provided for @accountabilityPartnerStreakDays.
  ///
  /// In zh, this message translates to:
  /// **'TA {days} 天'**
  String accountabilityPartnerStreakDays(Object days);

  /// No description provided for @accountabilityMyAchievementsUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'我解锁 {count} 个成就'**
  String accountabilityMyAchievementsUnlocked(Object count);

  /// No description provided for @accountabilityPartnerAchievementsUnlocked.
  ///
  /// In zh, this message translates to:
  /// **'TA 解锁 {count} 个成就'**
  String accountabilityPartnerAchievementsUnlocked(Object count);

  /// No description provided for @accountabilityStreakRank.
  ///
  /// In zh, this message translates to:
  /// **'连续打卡榜：你第 {myRank}，伙伴第 {partnerRank}'**
  String accountabilityStreakRank(Object myRank, Object partnerRank);

  /// No description provided for @accountabilityDeviationsDetected.
  ///
  /// In zh, this message translates to:
  /// **'检测到 {count} 个偏离'**
  String accountabilityDeviationsDetected(Object count);

  /// No description provided for @accountabilityUpdatedAt.
  ///
  /// In zh, this message translates to:
  /// **'更新时间 {time}'**
  String accountabilityUpdatedAt(Object time);

  /// No description provided for @accountabilityZeroItems.
  ///
  /// In zh, this message translates to:
  /// **'0 条'**
  String get accountabilityZeroItems;

  /// No description provided for @accountabilityItemCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条'**
  String accountabilityItemCount(Object count);

  /// No description provided for @accountabilityPoliciesReady.
  ///
  /// In zh, this message translates to:
  /// **'已有 {count} 条策略就绪，等待事件触发。'**
  String accountabilityPoliciesReady(Object count);

  /// No description provided for @accountabilityReflectionsGenerated.
  ///
  /// In zh, this message translates to:
  /// **'最近已生成 {count} 条反思摘要。'**
  String accountabilityReflectionsGenerated(Object count);

  /// No description provided for @accountabilityPoliciesPending.
  ///
  /// In zh, this message translates to:
  /// **'已有 {count} 条策略待执行，下一次触发在 {time}。'**
  String accountabilityPoliciesPending(Object count, Object time);

  /// No description provided for @accountabilityReflectionsLatest.
  ///
  /// In zh, this message translates to:
  /// **'最近一次聚焦 {category}，更新时间 {time}。'**
  String accountabilityReflectionsLatest(Object category, Object time);

  /// No description provided for @accountabilityInvestedTime.
  ///
  /// In zh, this message translates to:
  /// **'投入时长: {minutes} 分钟'**
  String accountabilityInvestedTime(Object minutes);

  /// No description provided for @accountabilityMinutes.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String accountabilityMinutes(Object minutes);

  /// No description provided for @accountabilityEnd.
  ///
  /// In zh, this message translates to:
  /// **'结束'**
  String get accountabilityEnd;

  /// No description provided for @accountabilityOperationFailed.
  ///
  /// In zh, this message translates to:
  /// **'操作失败'**
  String get accountabilityOperationFailed;

  /// No description provided for @accountabilityLikeFailed.
  ///
  /// In zh, this message translates to:
  /// **'点赞失败'**
  String get accountabilityLikeFailed;

  /// No description provided for @accountabilitySendFailed.
  ///
  /// In zh, this message translates to:
  /// **'发送失败'**
  String get accountabilitySendFailed;

  /// No description provided for @accountabilityCheckinFailed.
  ///
  /// In zh, this message translates to:
  /// **'打卡失败'**
  String get accountabilityCheckinFailed;

  /// No description provided for @openclawHubGatewayNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'当前网关可访问，但没有执行权限，暂时无法重试队列'**
  String get openclawHubGatewayNoPermission;

  /// No description provided for @openclawHubEndpointUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'当前网关可访问，但执行入口不可用，暂时无法重试队列'**
  String get openclawHubEndpointUnavailable;

  /// No description provided for @openclawHubEngineNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'执行引擎尚未连接，暂时无法重试队列'**
  String get openclawHubEngineNotConnected;

  /// No description provided for @openclawHubNoRetryQueuedItems.
  ///
  /// In zh, this message translates to:
  /// **'当前没有可重试的排队任务'**
  String get openclawHubNoRetryQueuedItems;

  /// No description provided for @openclawHubQueueCleared.
  ///
  /// In zh, this message translates to:
  /// **'等待队列已清空'**
  String get openclawHubQueueCleared;

  /// No description provided for @openclawHubConnectedDiagnostics.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 已连接，点击查看诊断'**
  String get openclawHubConnectedDiagnostics;

  /// No description provided for @openclawHubGatewayNoPermissionDiagnostics.
  ///
  /// In zh, this message translates to:
  /// **'网关可达但缺少执行权限，点击查看诊断'**
  String get openclawHubGatewayNoPermissionDiagnostics;

  /// No description provided for @openclawHubEndpointIssueDiagnostics.
  ///
  /// In zh, this message translates to:
  /// **'网关可达但执行入口异常，点击查看诊断'**
  String get openclawHubEndpointIssueDiagnostics;

  /// No description provided for @openclawHubQueuedTasksDiagnostics.
  ///
  /// In zh, this message translates to:
  /// **'当前有排队任务，点击查看诊断'**
  String get openclawHubQueuedTasksDiagnostics;

  /// No description provided for @openclawHubNotConnectedDiagnostics.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 连接未完成，点击查看诊断'**
  String get openclawHubNotConnectedDiagnostics;

  /// No description provided for @openclawHubOverviewGatewayNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'网关在线，但没有执行权限'**
  String get openclawHubOverviewGatewayNoPermission;

  /// No description provided for @openclawHubOverviewEndpointIssue.
  ///
  /// In zh, this message translates to:
  /// **'网关在线，但执行入口不可用'**
  String get openclawHubOverviewEndpointIssue;

  /// No description provided for @openclawHubOverviewReady.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 已准备好接手'**
  String get openclawHubOverviewReady;

  /// No description provided for @openclawHubOverviewTasksWaiting.
  ///
  /// In zh, this message translates to:
  /// **'已有任务在等它恢复'**
  String get openclawHubOverviewTasksWaiting;

  /// No description provided for @openclawHubOverviewConfigSaved.
  ///
  /// In zh, this message translates to:
  /// **'连接信息已保存，当前还没连上'**
  String get openclawHubOverviewConfigSaved;

  /// No description provided for @openclawHubOverviewConnectFirst.
  ///
  /// In zh, this message translates to:
  /// **'先接入 OpenClaw，再开始稳定委派'**
  String get openclawHubOverviewConnectFirst;

  /// No description provided for @openclawHubOverviewGatewayNoPermissionDesc.
  ///
  /// In zh, this message translates to:
  /// **'当前这台网关可以访问，但真正执行会被权限拦住。先补可写 scope，或改用设备配对 + WebSocket，才算闭环接通。'**
  String get openclawHubOverviewGatewayNoPermissionDesc;

  /// No description provided for @openclawHubOverviewEndpointIssueDesc.
  ///
  /// In zh, this message translates to:
  /// **'当前地址本身可访问，但执行接口还没准备好。优先检查 `/v1/responses`、代理转发和 transport 选择是否一致。'**
  String get openclawHubOverviewEndpointIssueDesc;

  /// No description provided for @openclawHubOverviewConnectedDesc.
  ///
  /// In zh, this message translates to:
  /// **'连接保持正常，适合从任务页或聊天页直接把网页调研、整理和抓取类任务交给它。'**
  String get openclawHubOverviewConnectedDesc;

  /// No description provided for @openclawHubOverviewDefaultDesc.
  ///
  /// In zh, this message translates to:
  /// **'连接完成后，首页、聊天和任务页会共享同一个执行中心，不再四处寻找入口。'**
  String get openclawHubOverviewDefaultDesc;

  /// No description provided for @openclawHubActionHintPermission.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先做的是更换具备执行权限的令牌，或切到已配对的 WebSocket 连接。'**
  String get openclawHubActionHintPermission;

  /// No description provided for @openclawHubActionHintEndpoint.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先做的是检查执行接口与 transport，让网关从“可达”变成“可执行”。'**
  String get openclawHubActionHintEndpoint;

  /// No description provided for @openclawHubActionHintRetryQueue.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先做的是把等待队列重新提交。'**
  String get openclawHubActionHintRetryQueue;

  /// No description provided for @openclawHubActionHintReconnect.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先做的是恢复连接，让已排队的任务继续执行。'**
  String get openclawHubActionHintReconnect;

  /// No description provided for @openclawHubActionHintNewDelegation.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先做的是回到聊天或任务页发起新的委派。'**
  String get openclawHubActionHintNewDelegation;

  /// No description provided for @openclawHubActionHintCompleteConnection.
  ///
  /// In zh, this message translates to:
  /// **'现在最值得先做的是完成连接，让 OpenClaw 真正成为你的执行伴侣。'**
  String get openclawHubActionHintCompleteConnection;

  /// No description provided for @openclawHubAppBarTitle.
  ///
  /// In zh, this message translates to:
  /// **'OpenClaw 执行中心'**
  String get openclawHubAppBarTitle;

  /// No description provided for @openclawHubMetricConnectedNoPermission.
  ///
  /// In zh, this message translates to:
  /// **'已连接但无执行权限'**
  String get openclawHubMetricConnectedNoPermission;

  /// No description provided for @openclawHubMetricConnectedEndpointIssue.
  ///
  /// In zh, this message translates to:
  /// **'已连接但执行入口异常'**
  String get openclawHubMetricConnectedEndpointIssue;

  /// No description provided for @openclawHubMetricConnected.
  ///
  /// In zh, this message translates to:
  /// **'已连接'**
  String get openclawHubMetricConnected;

  /// No description provided for @openclawHubMetricNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'未连接'**
  String get openclawHubMetricNotConnected;

  /// No description provided for @openclawHubMetricPairedDevice.
  ///
  /// In zh, this message translates to:
  /// **'已配对设备'**
  String get openclawHubMetricPairedDevice;

  /// No description provided for @openclawHubMetricTokenAuth.
  ///
  /// In zh, this message translates to:
  /// **'令牌认证'**
  String get openclawHubMetricTokenAuth;

  /// No description provided for @openclawHubButtonContinueSetup.
  ///
  /// In zh, this message translates to:
  /// **'继续设置'**
  String get openclawHubButtonContinueSetup;

  /// No description provided for @openclawHubButtonViewQueue.
  ///
  /// In zh, this message translates to:
  /// **'查看队列'**
  String get openclawHubButtonViewQueue;

  /// No description provided for @openclawHubButtonAutomation.
  ///
  /// In zh, this message translates to:
  /// **'自动化'**
  String get openclawHubButtonAutomation;

  /// No description provided for @openclawHubButtonEnterChat.
  ///
  /// In zh, this message translates to:
  /// **'进入聊天'**
  String get openclawHubButtonEnterChat;

  /// No description provided for @openclawHubButtonViewTasks.
  ///
  /// In zh, this message translates to:
  /// **'查看任务'**
  String get openclawHubButtonViewTasks;

  /// No description provided for @openclawHubSectionConnectionTitle.
  ///
  /// In zh, this message translates to:
  /// **'连接与控制'**
  String get openclawHubSectionConnectionTitle;

  /// No description provided for @openclawHubSectionConnectionSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'先用摘要看清当前连接，再决定是否展开编辑，避免一进来就被整张表单打断。'**
  String get openclawHubSectionConnectionSubtitle;

  /// No description provided for @openclawHubCollapseConnectionEdit.
  ///
  /// In zh, this message translates to:
  /// **'收起连接编辑'**
  String get openclawHubCollapseConnectionEdit;

  /// No description provided for @openclawHubExpandConnectionEdit.
  ///
  /// In zh, this message translates to:
  /// **'编辑连接方式'**
  String get openclawHubExpandConnectionEdit;

  /// No description provided for @openclawHubGatewayUrlEmpty.
  ///
  /// In zh, this message translates to:
  /// **'尚未填写网关地址'**
  String get openclawHubGatewayUrlEmpty;

  /// No description provided for @openclawHubConnectionSummaryPermission.
  ///
  /// In zh, this message translates to:
  /// **'这台网关已经能访问，但当前认证没有真正发起执行的权限；更适合先修权限，再统一重试队列。'**
  String get openclawHubConnectionSummaryPermission;

  /// No description provided for @openclawHubConnectionSummaryEndpoint.
  ///
  /// In zh, this message translates to:
  /// **'网关本身可达，但执行接口还没准备好；先检查 transport 和 `/v1/responses` 会更有效。'**
  String get openclawHubConnectionSummaryEndpoint;

  /// No description provided for @openclawHubConnectionSummaryConnected.
  ///
  /// In zh, this message translates to:
  /// **'当前连接保持稳定，适合继续使用现有方式直接委派。'**
  String get openclawHubConnectionSummaryConnected;

  /// No description provided for @openclawHubConnectionSummaryConfigured.
  ///
  /// In zh, this message translates to:
  /// **'配置已经在本地保存好，展开后可以微调认证方式、协议和配对流程。'**
  String get openclawHubConnectionSummaryConfigured;

  /// No description provided for @openclawHubConnectionSummaryFirstTime.
  ///
  /// In zh, this message translates to:
  /// **'第一次接入通常只需要填地址，再选择令牌认证或设备配对中的一种。'**
  String get openclawHubConnectionSummaryFirstTime;

  /// No description provided for @openclawHubSectionDevicesTitle.
  ///
  /// In zh, this message translates to:
  /// **'设备与亲和性'**
  String get openclawHubSectionDevicesTitle;

  /// No description provided for @openclawHubSectionDevicesSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把“哪类任务优先发到哪台设备”显式配置出来，避免每次都让系统猜你的偏好。'**
  String get openclawHubSectionDevicesSubtitle;

  /// No description provided for @openclawHubCollapseDeviceDetails.
  ///
  /// In zh, this message translates to:
  /// **'收起设备详情'**
  String get openclawHubCollapseDeviceDetails;

  /// No description provided for @openclawHubExpandDeviceDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看设备与偏好'**
  String get openclawHubExpandDeviceDetails;

  /// No description provided for @openclawHubDevicesSummaryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'节点列表会在成功接入 OpenClaw 后自动出现。设备越清晰，后面的多节点调度和降级体验就越稳定。'**
  String get openclawHubDevicesSummaryEmpty;

  /// No description provided for @openclawHubSectionQueueTitle.
  ///
  /// In zh, this message translates to:
  /// **'队列与委派'**
  String get openclawHubSectionQueueTitle;

  /// No description provided for @openclawHubSectionQueueSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'让你先知道现在最该做什么，再决定是否展开看完整队列和模板能力。'**
  String get openclawHubSectionQueueSubtitle;

  /// No description provided for @openclawHubCollapseQueueDetails.
  ///
  /// In zh, this message translates to:
  /// **'收起队列详情'**
  String get openclawHubCollapseQueueDetails;

  /// No description provided for @openclawHubExpandQueueDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看全部队列'**
  String get openclawHubExpandQueueDetails;

  /// No description provided for @openclawHubQueueSummaryConnected.
  ///
  /// In zh, this message translates to:
  /// **'你现在最适合先把排队任务重新提交，等引擎把积压处理完再发起新的委派。'**
  String get openclawHubQueueSummaryConnected;

  /// No description provided for @openclawHubQueueSummaryNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'你已经把任务排好了，下一步先恢复连接，之后就能一口气继续执行。'**
  String get openclawHubQueueSummaryNotConnected;

  /// No description provided for @openclawHubQueueSummaryConnectedEmpty.
  ///
  /// In zh, this message translates to:
  /// **'当前没有等待中的任务，最适合回到聊天或任务页发起新的委派。'**
  String get openclawHubQueueSummaryConnectedEmpty;

  /// No description provided for @openclawHubQueueSummaryNotConnectedEmpty.
  ///
  /// In zh, this message translates to:
  /// **'当前也没有排队任务，可以先完成连接，再决定要不要开始第一笔委派。'**
  String get openclawHubQueueSummaryNotConnectedEmpty;

  /// No description provided for @openclawHubQueueEmptyLabel.
  ///
  /// In zh, this message translates to:
  /// **'等待队列当前为空'**
  String get openclawHubQueueEmptyLabel;

  /// No description provided for @openclawHubButtonRetryQueue.
  ///
  /// In zh, this message translates to:
  /// **'重试队列'**
  String get openclawHubButtonRetryQueue;

  /// No description provided for @openclawHubButtonClearQueue.
  ///
  /// In zh, this message translates to:
  /// **'清空队列'**
  String get openclawHubButtonClearQueue;

  /// No description provided for @openclawHubAvailableTemplates.
  ///
  /// In zh, this message translates to:
  /// **'可用模板 / 能力说明'**
  String get openclawHubAvailableTemplates;

  /// No description provided for @openclawHubTemplatesEmptyHint.
  ///
  /// In zh, this message translates to:
  /// **'模板会在你打开具体任务后按需加载；现在可以先把连接、队列和最近活动整理顺，再回到具体任务开始委派。'**
  String get openclawHubTemplatesEmptyHint;

  /// No description provided for @openclawHubSectionAutomationTitle.
  ///
  /// In zh, this message translates to:
  /// **'自动化与批量'**
  String get openclawHubSectionAutomationTitle;

  /// No description provided for @openclawHubSectionAutomationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把一次性的批量执行和长期的定时/条件执行放进同一个操作台，避免执行能力只停留在单次点击。'**
  String get openclawHubSectionAutomationSubtitle;

  /// No description provided for @openclawHubCollapseAutomationDetails.
  ///
  /// In zh, this message translates to:
  /// **'收起自动化详情'**
  String get openclawHubCollapseAutomationDetails;

  /// No description provided for @openclawHubExpandAutomationDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看自动化能力'**
  String get openclawHubExpandAutomationDetails;

  /// No description provided for @openclawHubAutomationSummaryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'你还没有任何自动化。展开后可以创建每天定时执行、事件触发或条件轮询，并直接从这里发起批量委派。'**
  String get openclawHubAutomationSummaryEmpty;

  /// No description provided for @openclawHubSectionActivityTitle.
  ///
  /// In zh, this message translates to:
  /// **'最近活动'**
  String get openclawHubSectionActivityTitle;

  /// No description provided for @openclawHubSectionActivitySubtitle.
  ///
  /// In zh, this message translates to:
  /// **'用高密度时间线看最近的委派，不需要再在不同任务页之间来回翻找。'**
  String get openclawHubSectionActivitySubtitle;

  /// No description provided for @openclawHubCollapseActivityDetails.
  ///
  /// In zh, this message translates to:
  /// **'收起活动详情'**
  String get openclawHubCollapseActivityDetails;

  /// No description provided for @openclawHubExpandActivityDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看全部活动'**
  String get openclawHubExpandActivityDetails;

  /// No description provided for @openclawHubActivityEmptyHint.
  ///
  /// In zh, this message translates to:
  /// **'暂时还没有最近执行。你可以从首页卡牌、任务执行页或聊天入口发起第一笔委派。'**
  String get openclawHubActivityEmptyHint;

  /// No description provided for @openclawHubActivityHint.
  ///
  /// In zh, this message translates to:
  /// **'可继续查看该任务的执行详情。'**
  String get openclawHubActivityHint;

  /// No description provided for @openclawHubActivityOpenTask.
  ///
  /// In zh, this message translates to:
  /// **'打开任务执行'**
  String get openclawHubActivityOpenTask;

  /// No description provided for @openclawHubStatusRecorded.
  ///
  /// In zh, this message translates to:
  /// **'已记录'**
  String get openclawHubStatusRecorded;

  /// No description provided for @openclawHubRetryQueuedSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已重新提交 {count} 个排队任务'**
  String openclawHubRetryQueuedSuccess(Object count);

  /// No description provided for @openclawHubLastExecutionStatus.
  ///
  /// In zh, this message translates to:
  /// **'最近一次执行状态是“{status}”，你可以从这里继续查看连接、队列和活动。'**
  String openclawHubLastExecutionStatus(Object status);

  /// No description provided for @openclawHubPendingDelegationsDesc.
  ///
  /// In zh, this message translates to:
  /// **'你已经有 {count} 个委派在等待恢复连接，先把引擎重新连上会最有效。'**
  String openclawHubPendingDelegationsDesc(Object count);

  /// No description provided for @openclawHubQueuedTasksCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个排队任务'**
  String openclawHubQueuedTasksCount(Object count);

  /// No description provided for @openclawHubNodeCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个节点'**
  String openclawHubNodeCount(Object count);

  /// No description provided for @openclawHubAutomationCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条自动化'**
  String openclawHubAutomationCount(Object count);

  /// No description provided for @openclawHubLatestBatch.
  ///
  /// In zh, this message translates to:
  /// **'最近批量 {completed}/{total}'**
  String openclawHubLatestBatch(Object completed, Object total);

  /// No description provided for @openclawHubLastTrustLabel.
  ///
  /// In zh, this message translates to:
  /// **'最近一次信任判断：{label}'**
  String openclawHubLastTrustLabel(Object label);

  /// No description provided for @openclawHubDevicesSummaryActiveWithCount.
  ///
  /// In zh, this message translates to:
  /// **'当前已发现 {count} 台节点。你可以在这里为浏览器、终端、文档和接口任务指定偏好设备，离线时 Sparkle 会自动找备用节点。'**
  String openclawHubDevicesSummaryActiveWithCount(Object count);

  /// No description provided for @openclawHubAutomationSummaryActiveWithCount.
  ///
  /// In zh, this message translates to:
  /// **'当前已有 {count} 条自动化在运行。批量委派摘要和定时任务状态也会持续在这里汇总。'**
  String openclawHubAutomationSummaryActiveWithCount(Object count);

  /// No description provided for @openclawHubTaskLabel.
  ///
  /// In zh, this message translates to:
  /// **'任务 {taskId}'**
  String openclawHubTaskLabel(Object taskId);

  /// No description provided for @openclawHubTaskLabelTemplate.
  ///
  /// In zh, this message translates to:
  /// **'模板 {templateId}'**
  String openclawHubTaskLabelTemplate(Object templateId);

  /// No description provided for @openclawHubTaskLabelSource.
  ///
  /// In zh, this message translates to:
  /// **'来源 {source}'**
  String openclawHubTaskLabelSource(Object source);

  /// No description provided for @seedLibraryDetailFriendlyError.
  ///
  /// In zh, this message translates to:
  /// **'系统暂时没能完成这次应用，请稍后再试'**
  String get seedLibraryDetailFriendlyError;

  /// No description provided for @seedLibraryDetailUserRatings.
  ///
  /// In zh, this message translates to:
  /// **'用户评分'**
  String get seedLibraryDetailUserRatings;

  /// No description provided for @seedLibraryDetailQualityBreakdown.
  ///
  /// In zh, this message translates to:
  /// **'质量评分拆解'**
  String get seedLibraryDetailQualityBreakdown;

  /// No description provided for @seedLibraryDetailQualityBreakdownDesc.
  ///
  /// In zh, this message translates to:
  /// **'列表中展示的是综合质量分，这里会同时展示系统基础分和用户评分均值，帮助你判断这个种子库是否值得长期启用。'**
  String get seedLibraryDetailQualityBreakdownDesc;

  /// No description provided for @seedLibraryDetailQualityComprehensive.
  ///
  /// In zh, this message translates to:
  /// **'综合'**
  String get seedLibraryDetailQualityComprehensive;

  /// No description provided for @seedLibraryDetailQualitySystem.
  ///
  /// In zh, this message translates to:
  /// **'系统'**
  String get seedLibraryDetailQualitySystem;

  /// No description provided for @seedLibraryDetailQualityUser.
  ///
  /// In zh, this message translates to:
  /// **'用户'**
  String get seedLibraryDetailQualityUser;

  /// No description provided for @seedLibraryDetailApplyToSystem.
  ///
  /// In zh, this message translates to:
  /// **'应用到系统'**
  String get seedLibraryDetailApplyToSystem;

  /// No description provided for @seedLibraryDetailAppliedSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已应用到系统'**
  String get seedLibraryDetailAppliedSuccess;

  /// No description provided for @seedLibraryDetailPausedSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已暂停使用该种子库'**
  String get seedLibraryDetailPausedSuccess;

  /// No description provided for @seedLibraryDetailStatusUpdated.
  ///
  /// In zh, this message translates to:
  /// **'种子库状态已更新'**
  String get seedLibraryDetailStatusUpdated;

  /// No description provided for @seedLibraryDetailPauseUse.
  ///
  /// In zh, this message translates to:
  /// **'暂停使用'**
  String get seedLibraryDetailPauseUse;

  /// No description provided for @seedLibraryDetailApplyLibrary.
  ///
  /// In zh, this message translates to:
  /// **'应用种子库'**
  String get seedLibraryDetailApplyLibrary;

  /// No description provided for @seedLibraryDetailSetPrimarySuccess.
  ///
  /// In zh, this message translates to:
  /// **'已设为优先使用'**
  String get seedLibraryDetailSetPrimarySuccess;

  /// No description provided for @seedLibraryDetailSetPrimary.
  ///
  /// In zh, this message translates to:
  /// **'设为主用'**
  String get seedLibraryDetailSetPrimary;

  /// No description provided for @seedLibraryDetailMarkedNotSuitableSuccess.
  ///
  /// In zh, this message translates to:
  /// **'已记录“此种子不适合我”'**
  String get seedLibraryDetailMarkedNotSuitableSuccess;

  /// No description provided for @seedLibraryDetailMarkNotSuitable.
  ///
  /// In zh, this message translates to:
  /// **'此种子不适合我'**
  String get seedLibraryDetailMarkNotSuitable;

  /// No description provided for @seedLibraryDetailEditRating.
  ///
  /// In zh, this message translates to:
  /// **'修改评分'**
  String get seedLibraryDetailEditRating;

  /// No description provided for @seedLibraryDetailGiveRating.
  ///
  /// In zh, this message translates to:
  /// **'给个评分'**
  String get seedLibraryDetailGiveRating;

  /// No description provided for @seedLibraryDetailSubscriptionStatusEnabled.
  ///
  /// In zh, this message translates to:
  /// **'已启用'**
  String get seedLibraryDetailSubscriptionStatusEnabled;

  /// No description provided for @seedLibraryDetailSubscriptionStatusDisabled.
  ///
  /// In zh, this message translates to:
  /// **'已订阅未启用'**
  String get seedLibraryDetailSubscriptionStatusDisabled;

  /// No description provided for @seedLibraryDetailActiveSubscriptions.
  ///
  /// In zh, this message translates to:
  /// **'协同中的种子库'**
  String get seedLibraryDetailActiveSubscriptions;

  /// No description provided for @seedLibraryDetailActiveSubscriptionsDesc.
  ///
  /// In zh, this message translates to:
  /// **'你可以同时启用多个种子库。系统会优先使用高优先级种子库，再融合其他已启用种子库的内容。'**
  String get seedLibraryDetailActiveSubscriptionsDesc;

  /// No description provided for @seedLibraryDetailFallbackName.
  ///
  /// In zh, this message translates to:
  /// **'种子库'**
  String get seedLibraryDetailFallbackName;

  /// No description provided for @seedLibraryDetailNoResultsUnderFilter.
  ///
  /// In zh, this message translates to:
  /// **'当前筛选条件下没有内容'**
  String get seedLibraryDetailNoResultsUnderFilter;

  /// No description provided for @seedLibraryDetailUsageFewShot.
  ///
  /// In zh, this message translates to:
  /// **'用于增强 AI 在相似任务中的回答风格和示例质量'**
  String get seedLibraryDetailUsageFewShot;

  /// No description provided for @seedLibraryDetailUsageTeachingContent.
  ///
  /// In zh, this message translates to:
  /// **'用于给学习计划、任务说明和知识讲解提供高质量教学内容'**
  String get seedLibraryDetailUsageTeachingContent;

  /// No description provided for @seedLibraryDetailUsageReplyTemplate.
  ///
  /// In zh, this message translates to:
  /// **'用于改善系统回复模板和表达稳定性'**
  String get seedLibraryDetailUsageReplyTemplate;

  /// No description provided for @seedLibraryDetailUsageCustom.
  ///
  /// In zh, this message translates to:
  /// **'用于你自己的内容偏好和专属示例沉淀'**
  String get seedLibraryDetailUsageCustom;

  /// No description provided for @seedLibraryDetailFilterTitle.
  ///
  /// In zh, this message translates to:
  /// **'筛选内容'**
  String get seedLibraryDetailFilterTitle;

  /// No description provided for @seedLibraryDetailFilterDesc.
  ///
  /// In zh, this message translates to:
  /// **'按内容类型、难度和启用状态筛选当前种子库里的条目。'**
  String get seedLibraryDetailFilterDesc;

  /// No description provided for @seedLibraryDetailFilterContentType.
  ///
  /// In zh, this message translates to:
  /// **'内容类型'**
  String get seedLibraryDetailFilterContentType;

  /// No description provided for @seedLibraryDetailFilterAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get seedLibraryDetailFilterAll;

  /// No description provided for @seedLibraryDetailFilterDifficulty.
  ///
  /// In zh, this message translates to:
  /// **'难度'**
  String get seedLibraryDetailFilterDifficulty;

  /// No description provided for @seedLibraryDetailFilterShowInactive.
  ///
  /// In zh, this message translates to:
  /// **'显示已停用内容'**
  String get seedLibraryDetailFilterShowInactive;

  /// No description provided for @seedLibraryDetailFilterShowInactiveDesc.
  ///
  /// In zh, this message translates to:
  /// **'关闭时仅展示当前仍在使用的条目'**
  String get seedLibraryDetailFilterShowInactiveDesc;

  /// No description provided for @seedLibraryDetailFilterReset.
  ///
  /// In zh, this message translates to:
  /// **'重置'**
  String get seedLibraryDetailFilterReset;

  /// No description provided for @seedLibraryDetailFilterDone.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get seedLibraryDetailFilterDone;

  /// No description provided for @seedLibraryDetailRatingTitle.
  ///
  /// In zh, this message translates to:
  /// **'给这个种子库评分'**
  String get seedLibraryDetailRatingTitle;

  /// No description provided for @seedLibraryDetailRatingDescription.
  ///
  /// In zh, this message translates to:
  /// **'你的评分会影响这个种子库的展示质量分。'**
  String get seedLibraryDetailRatingDescription;

  /// No description provided for @seedLibraryDetailRatingCommentLabel.
  ///
  /// In zh, this message translates to:
  /// **'评价说明（可选）'**
  String get seedLibraryDetailRatingCommentLabel;

  /// No description provided for @seedLibraryDetailRatingSubmitted.
  ///
  /// In zh, this message translates to:
  /// **'评分已提交'**
  String get seedLibraryDetailRatingSubmitted;

  /// No description provided for @seedLibraryDetailSubmitRating.
  ///
  /// In zh, this message translates to:
  /// **'提交评分'**
  String get seedLibraryDetailSubmitRating;

  /// No description provided for @seedLibraryDetailContentBody.
  ///
  /// In zh, this message translates to:
  /// **'正文'**
  String get seedLibraryDetailContentBody;

  /// No description provided for @seedLibraryDetailStructuredContent.
  ///
  /// In zh, this message translates to:
  /// **'结构化内容'**
  String get seedLibraryDetailStructuredContent;

  /// No description provided for @seedLibraryDetailEditLibrary.
  ///
  /// In zh, this message translates to:
  /// **'编辑种子库'**
  String get seedLibraryDetailEditLibrary;

  /// No description provided for @seedLibraryDetailEditName.
  ///
  /// In zh, this message translates to:
  /// **'名称'**
  String get seedLibraryDetailEditName;

  /// No description provided for @seedLibraryDetailEditNameEmpty.
  ///
  /// In zh, this message translates to:
  /// **'名称不能为空'**
  String get seedLibraryDetailEditNameEmpty;

  /// No description provided for @seedLibraryDetailEditDescriptionOptional.
  ///
  /// In zh, this message translates to:
  /// **'描述（可选）'**
  String get seedLibraryDetailEditDescriptionOptional;

  /// No description provided for @seedLibraryDetailEditCancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get seedLibraryDetailEditCancel;

  /// No description provided for @seedLibraryDetailEditSave.
  ///
  /// In zh, this message translates to:
  /// **'保存'**
  String get seedLibraryDetailEditSave;

  /// No description provided for @seedLibraryDetailLibraryUpdated.
  ///
  /// In zh, this message translates to:
  /// **'种子库已更新'**
  String get seedLibraryDetailLibraryUpdated;

  /// No description provided for @seedLibraryDetailAddItem.
  ///
  /// In zh, this message translates to:
  /// **'添加种子内容'**
  String get seedLibraryDetailAddItem;

  /// No description provided for @seedLibraryDetailAddItemType.
  ///
  /// In zh, this message translates to:
  /// **'内容类型'**
  String get seedLibraryDetailAddItemType;

  /// No description provided for @seedLibraryDetailAddItemTitle.
  ///
  /// In zh, this message translates to:
  /// **'标题'**
  String get seedLibraryDetailAddItemTitle;

  /// No description provided for @seedLibraryDetailAddItemContent.
  ///
  /// In zh, this message translates to:
  /// **'内容'**
  String get seedLibraryDetailAddItemContent;

  /// No description provided for @seedLibraryDetailAddItemSubject.
  ///
  /// In zh, this message translates to:
  /// **'主题/学科'**
  String get seedLibraryDetailAddItemSubject;

  /// No description provided for @seedLibraryDetailAddItemDifficulty.
  ///
  /// In zh, this message translates to:
  /// **'难度'**
  String get seedLibraryDetailAddItemDifficulty;

  /// No description provided for @seedLibraryDetailAddItemUnset.
  ///
  /// In zh, this message translates to:
  /// **'未设置'**
  String get seedLibraryDetailAddItemUnset;

  /// No description provided for @seedLibraryDetailAddItemTags.
  ///
  /// In zh, this message translates to:
  /// **'标签（逗号分隔）'**
  String get seedLibraryDetailAddItemTags;

  /// No description provided for @seedLibraryDetailAddItemSave.
  ///
  /// In zh, this message translates to:
  /// **'保存内容'**
  String get seedLibraryDetailAddItemSave;

  /// No description provided for @seedLibraryDetailAddItemSuccess.
  ///
  /// In zh, this message translates to:
  /// **'种子内容已添加'**
  String get seedLibraryDetailAddItemSuccess;

  /// No description provided for @seedLibraryDetailImportCannotRead.
  ///
  /// In zh, this message translates to:
  /// **'无法读取文件内容'**
  String get seedLibraryDetailImportCannotRead;

  /// No description provided for @seedLibraryDetailImportInvalidJson.
  ///
  /// In zh, this message translates to:
  /// **'JSON 格式无效，需为数组或 [items:[...]]'**
  String get seedLibraryDetailImportInvalidJson;

  /// No description provided for @seedLibraryDetailImportNoItems.
  ///
  /// In zh, this message translates to:
  /// **'文件中没有可导入的内容项'**
  String get seedLibraryDetailImportNoItems;

  /// No description provided for @seedLibraryDetailApplyFailed.
  ///
  /// In zh, this message translates to:
  /// **'应用失败：{error}'**
  String seedLibraryDetailApplyFailed(Object error);

  /// No description provided for @seedLibraryDetailSetPrimaryFailed.
  ///
  /// In zh, this message translates to:
  /// **'设置失败：{error}'**
  String seedLibraryDetailSetPrimaryFailed(Object error);

  /// No description provided for @seedLibraryDetailMarkNotSuitableFailed.
  ///
  /// In zh, this message translates to:
  /// **'记录失败：{error}'**
  String seedLibraryDetailMarkNotSuitableFailed(Object error);

  /// No description provided for @seedLibraryDetailCurrentStatus.
  ///
  /// In zh, this message translates to:
  /// **'当前状态：{status} · 优先级 {priority}'**
  String seedLibraryDetailCurrentStatus(Object status, Object priority);

  /// No description provided for @seedLibraryDetailUsageAppliedEnabled.
  ///
  /// In zh, this message translates to:
  /// **'当前已生效。{hint}；系统会按优先级把它与其他启用中的种子库一起使用。'**
  String seedLibraryDetailUsageAppliedEnabled(Object hint);

  /// No description provided for @seedLibraryDetailUsageSubscribedNotEnabled.
  ///
  /// In zh, this message translates to:
  /// **'当前已订阅但未启用。启用后，{hint}。'**
  String seedLibraryDetailUsageSubscribedNotEnabled(Object hint);

  /// No description provided for @seedLibraryDetailUsageNotApplied.
  ///
  /// In zh, this message translates to:
  /// **'当前尚未应用。应用后，{hint}。'**
  String seedLibraryDetailUsageNotApplied(Object hint);

  /// No description provided for @seedLibraryDetailCurrentRating.
  ///
  /// In zh, this message translates to:
  /// **'当前评分：{score} / 10'**
  String seedLibraryDetailCurrentRating(Object score);

  /// No description provided for @seedLibraryDetailRatingFailed.
  ///
  /// In zh, this message translates to:
  /// **'评分失败：{error}'**
  String seedLibraryDetailRatingFailed(Object error);

  /// No description provided for @seedLibraryDetailAddItemFailed.
  ///
  /// In zh, this message translates to:
  /// **'添加失败：{error}'**
  String seedLibraryDetailAddItemFailed(Object error);

  /// No description provided for @seedLibraryDetailImportResult.
  ///
  /// In zh, this message translates to:
  /// **'导入完成：成功 {imported} 条，失败 {failed} 条'**
  String seedLibraryDetailImportResult(Object imported, Object failed);

  /// No description provided for @seedLibraryDetailImportFailed.
  ///
  /// In zh, this message translates to:
  /// **'导入失败：{error}'**
  String seedLibraryDetailImportFailed(Object error);

  /// No description provided for @recommendationTargetFallback.
  ///
  /// In zh, this message translates to:
  /// **'推荐对象'**
  String get recommendationTargetFallback;

  /// No description provided for @recommendationThisItem.
  ///
  /// In zh, this message translates to:
  /// **'这条推荐'**
  String get recommendationThisItem;

  /// No description provided for @recommendationFeedbackAbout.
  ///
  /// In zh, this message translates to:
  /// **'关于 {target} 的{stage}反馈'**
  String recommendationFeedbackAbout(Object target, Object stage);

  /// No description provided for @recommendationFeedbackHint.
  ///
  /// In zh, this message translates to:
  /// **'你的反馈会直接更新下一轮推荐权重'**
  String get recommendationFeedbackHint;

  /// No description provided for @recommendationStartCalibration.
  ///
  /// In zh, this message translates to:
  /// **'开始校准'**
  String get recommendationStartCalibration;

  /// No description provided for @recommendationFriendPreferenceTitle.
  ///
  /// In zh, this message translates to:
  /// **'你的伙伴匹配偏好'**
  String get recommendationFriendPreferenceTitle;

  /// No description provided for @recommendationGroupPreferenceTitle.
  ///
  /// In zh, this message translates to:
  /// **'你的社群推荐偏好'**
  String get recommendationGroupPreferenceTitle;

  /// No description provided for @recommendationRecentCount.
  ///
  /// In zh, this message translates to:
  /// **'近 {count} 次'**
  String recommendationRecentCount(Object count);

  /// No description provided for @recommendationFriendLearningHint.
  ///
  /// In zh, this message translates to:
  /// **'系统正在学习你更看重相似度、互补性还是合作舒适度。'**
  String get recommendationFriendLearningHint;

  /// No description provided for @recommendationGroupLearningHint.
  ///
  /// In zh, this message translates to:
  /// **'系统正在学习你更偏好兴趣对口、活跃氛围还是新鲜发现。'**
  String get recommendationGroupLearningHint;

  /// No description provided for @recommendationSystemAvoiding.
  ///
  /// In zh, this message translates to:
  /// **'系统在回避：{signals}'**
  String recommendationSystemAvoiding(Object signals);

  /// No description provided for @recommendationCurrentlyBiasing.
  ///
  /// In zh, this message translates to:
  /// **'当前更偏向：{metrics}'**
  String recommendationCurrentlyBiasing(Object metrics);

  /// No description provided for @recommendationListSeparator.
  ///
  /// In zh, this message translates to:
  /// **'、'**
  String get recommendationListSeparator;

  /// No description provided for @recommendationCalibrateTitle.
  ///
  /// In zh, this message translates to:
  /// **'帮我们校准推荐'**
  String get recommendationCalibrateTitle;

  /// No description provided for @recommendationFeedbackSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'你对 {subject} 的评价会直接作用到接下来的推荐算法。'**
  String recommendationFeedbackSubtitle(Object subject);

  /// No description provided for @recommendationScoreOverall.
  ///
  /// In zh, this message translates to:
  /// **'整体感受'**
  String get recommendationScoreOverall;

  /// No description provided for @recommendationScoreExplanationClarity.
  ///
  /// In zh, this message translates to:
  /// **'推荐理由清晰度'**
  String get recommendationScoreExplanationClarity;

  /// No description provided for @recommendationScoreActionability.
  ///
  /// In zh, this message translates to:
  /// **'采取行动的意愿'**
  String get recommendationScoreActionability;

  /// No description provided for @recommendationScoreRelevance.
  ///
  /// In zh, this message translates to:
  /// **'契合度'**
  String get recommendationScoreRelevance;

  /// No description provided for @recommendationScoreSimilarity.
  ///
  /// In zh, this message translates to:
  /// **'相似度是否到位'**
  String get recommendationScoreSimilarity;

  /// No description provided for @recommendationScoreComplementary.
  ///
  /// In zh, this message translates to:
  /// **'互补性是否成立'**
  String get recommendationScoreComplementary;

  /// No description provided for @recommendationScoreComfort.
  ///
  /// In zh, this message translates to:
  /// **'合作舒适度'**
  String get recommendationScoreComfort;

  /// No description provided for @recommendationScoreInterestMatch.
  ///
  /// In zh, this message translates to:
  /// **'兴趣匹配度'**
  String get recommendationScoreInterestMatch;

  /// No description provided for @recommendationScoreActivity.
  ///
  /// In zh, this message translates to:
  /// **'活跃度是否合适'**
  String get recommendationScoreActivity;

  /// No description provided for @recommendationScoreAtmosphere.
  ///
  /// In zh, this message translates to:
  /// **'社群氛围'**
  String get recommendationScoreAtmosphere;

  /// No description provided for @recommendationIssuesTitle.
  ///
  /// In zh, this message translates to:
  /// **'哪里不够对味'**
  String get recommendationIssuesTitle;

  /// No description provided for @recommendationStrengthsTitle.
  ///
  /// In zh, this message translates to:
  /// **'哪些地方做得好'**
  String get recommendationStrengthsTitle;

  /// No description provided for @recommendationFreeTextLabel.
  ///
  /// In zh, this message translates to:
  /// **'自然语言补充'**
  String get recommendationFreeTextLabel;

  /// No description provided for @recommendationFriendHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：我更希望责任伙伴跟我节奏接近，但也能在拖延时推我一把。'**
  String get recommendationFriendHint;

  /// No description provided for @recommendationGroupHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：我想找更对口的小组，最好活跃但不要太嘈杂。'**
  String get recommendationGroupHint;

  /// No description provided for @recommendationPrivacyNotice.
  ///
  /// In zh, this message translates to:
  /// **'我们只使用你填写的分数和总结来优化推荐，不会把私密原始数据直接暴露给其他用户。'**
  String get recommendationPrivacyNotice;

  /// No description provided for @recommendationLater.
  ///
  /// In zh, this message translates to:
  /// **'稍后再说'**
  String get recommendationLater;

  /// No description provided for @recommendationSubmitFeedback.
  ///
  /// In zh, this message translates to:
  /// **'提交反馈'**
  String get recommendationSubmitFeedback;

  /// No description provided for @recommendationMatchingStrategy.
  ///
  /// In zh, this message translates to:
  /// **'匹配策略：{name}'**
  String recommendationMatchingStrategy(Object name);

  /// No description provided for @recommendationGroupSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{count} 人 · {tags}'**
  String recommendationGroupSubtitle(Object count, Object tags);

  /// No description provided for @recommendationPublicGroup.
  ///
  /// In zh, this message translates to:
  /// **'公开社群'**
  String get recommendationPublicGroup;

  /// No description provided for @recommendationStageImmediate.
  ///
  /// In zh, this message translates to:
  /// **'即时'**
  String get recommendationStageImmediate;

  /// No description provided for @recommendationStageFollowUp.
  ///
  /// In zh, this message translates to:
  /// **'跟进'**
  String get recommendationStageFollowUp;

  /// No description provided for @recommendationStageOutcome.
  ///
  /// In zh, this message translates to:
  /// **'结果'**
  String get recommendationStageOutcome;

  /// No description provided for @recommendationReasonSubjectOverlap.
  ///
  /// In zh, this message translates to:
  /// **'主题重合'**
  String get recommendationReasonSubjectOverlap;

  /// No description provided for @recommendationReasonPreferenceAlignment.
  ///
  /// In zh, this message translates to:
  /// **'学习节奏接近'**
  String get recommendationReasonPreferenceAlignment;

  /// No description provided for @recommendationReasonTagOverlap.
  ///
  /// In zh, this message translates to:
  /// **'兴趣命中'**
  String get recommendationReasonTagOverlap;

  /// No description provided for @recommendationReasonTrending.
  ///
  /// In zh, this message translates to:
  /// **'近期活跃'**
  String get recommendationReasonTrending;

  /// No description provided for @recommendationMetricOverall.
  ///
  /// In zh, this message translates to:
  /// **'整体'**
  String get recommendationMetricOverall;

  /// No description provided for @recommendationMetricSimilarity.
  ///
  /// In zh, this message translates to:
  /// **'相似度'**
  String get recommendationMetricSimilarity;

  /// No description provided for @recommendationMetricComfort.
  ///
  /// In zh, this message translates to:
  /// **'舒适度'**
  String get recommendationMetricComfort;

  /// No description provided for @recommendationMetricInterestMatch.
  ///
  /// In zh, this message translates to:
  /// **'兴趣匹配'**
  String get recommendationMetricInterestMatch;

  /// No description provided for @recommendationMetricActivity.
  ///
  /// In zh, this message translates to:
  /// **'活跃度'**
  String get recommendationMetricActivity;

  /// No description provided for @recommendationMetricSubjectSimilarity.
  ///
  /// In zh, this message translates to:
  /// **'主题相似'**
  String get recommendationMetricSubjectSimilarity;

  /// No description provided for @recommendationMetricRelationshipReadiness.
  ///
  /// In zh, this message translates to:
  /// **'关系熟悉度'**
  String get recommendationMetricRelationshipReadiness;

  /// No description provided for @recommendationMetricTagMatch.
  ///
  /// In zh, this message translates to:
  /// **'标签匹配'**
  String get recommendationMetricTagMatch;

  /// No description provided for @recommendationMetricQuality.
  ///
  /// In zh, this message translates to:
  /// **'质量'**
  String get recommendationMetricQuality;

  /// No description provided for @recommendationSignalTooDissimilar.
  ///
  /// In zh, this message translates to:
  /// **'不够相似'**
  String get recommendationSignalTooDissimilar;

  /// No description provided for @recommendationSignalWantMoreTagMatch.
  ///
  /// In zh, this message translates to:
  /// **'兴趣不够对口'**
  String get recommendationSignalWantMoreTagMatch;

  /// No description provided for @recommendationSignalTrustworthy.
  ///
  /// In zh, this message translates to:
  /// **'合作感靠谱'**
  String get recommendationSignalTrustworthy;

  /// No description provided for @recommendationSignalGoodInterestMatch.
  ///
  /// In zh, this message translates to:
  /// **'兴趣对口'**
  String get recommendationSignalGoodInterestMatch;

  /// No description provided for @recommendationIssueNotSimilar.
  ///
  /// In zh, this message translates to:
  /// **'不够相似'**
  String get recommendationIssueNotSimilar;

  /// No description provided for @recommendationIssueNotComplementary.
  ///
  /// In zh, this message translates to:
  /// **'缺少互补'**
  String get recommendationIssueNotComplementary;

  /// No description provided for @recommendationIssueNotProactive.
  ///
  /// In zh, this message translates to:
  /// **'不够主动'**
  String get recommendationIssueNotProactive;

  /// No description provided for @recommendationIssueTooMuchPressure.
  ///
  /// In zh, this message translates to:
  /// **'压力太大'**
  String get recommendationIssueTooMuchPressure;

  /// No description provided for @recommendationIssueNotFamiliar.
  ///
  /// In zh, this message translates to:
  /// **'不够熟悉'**
  String get recommendationIssueNotFamiliar;

  /// No description provided for @recommendationIssueInaccurateTags.
  ///
  /// In zh, this message translates to:
  /// **'标签不准'**
  String get recommendationIssueInaccurateTags;

  /// No description provided for @recommendationIssueTooQuiet.
  ///
  /// In zh, this message translates to:
  /// **'太冷清'**
  String get recommendationIssueTooQuiet;

  /// No description provided for @recommendationIssueTooCrowded.
  ///
  /// In zh, this message translates to:
  /// **'太拥挤'**
  String get recommendationIssueTooCrowded;

  /// No description provided for @recommendationIssueMediocreVibe.
  ///
  /// In zh, this message translates to:
  /// **'氛围一般'**
  String get recommendationIssueMediocreVibe;

  /// No description provided for @recommendationIssueUnsuitableThreshold.
  ///
  /// In zh, this message translates to:
  /// **'门槛不合适'**
  String get recommendationIssueUnsuitableThreshold;

  /// No description provided for @recommendationStrengthGreatFit.
  ///
  /// In zh, this message translates to:
  /// **'很契合'**
  String get recommendationStrengthGreatFit;

  /// No description provided for @recommendationStrengthComplementary.
  ///
  /// In zh, this message translates to:
  /// **'很互补'**
  String get recommendationStrengthComplementary;

  /// No description provided for @recommendationStrengthReliable.
  ///
  /// In zh, this message translates to:
  /// **'很靠谱'**
  String get recommendationStrengthReliable;

  /// No description provided for @recommendationStrengthClearReason.
  ///
  /// In zh, this message translates to:
  /// **'理由清楚'**
  String get recommendationStrengthClearReason;

  /// No description provided for @recommendationStrengthInterestMatch.
  ///
  /// In zh, this message translates to:
  /// **'兴趣对口'**
  String get recommendationStrengthInterestMatch;

  /// No description provided for @recommendationStrengthGreatVibe.
  ///
  /// In zh, this message translates to:
  /// **'氛围很好'**
  String get recommendationStrengthGreatVibe;

  /// No description provided for @recommendationStrengthActiveFit.
  ///
  /// In zh, this message translates to:
  /// **'活跃合适'**
  String get recommendationStrengthActiveFit;

  /// No description provided for @personaRefreshPersona.
  ///
  /// In zh, this message translates to:
  /// **'刷新画像'**
  String get personaRefreshPersona;

  /// No description provided for @personaProfileInterpretation.
  ///
  /// In zh, this message translates to:
  /// **'画像解读'**
  String get personaProfileInterpretation;

  /// No description provided for @personaProfileInterpretationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'先看自然语言总结，再决定要不要展开底层结构'**
  String get personaProfileInterpretationSubtitle;

  /// No description provided for @personaL3Subtitle.
  ///
  /// In zh, this message translates to:
  /// **'优先展示系统已经总结出的可感知结论'**
  String get personaL3Subtitle;

  /// No description provided for @personaL1Subtitle.
  ///
  /// In zh, this message translates to:
  /// **'你明确告诉系统的目标和偏好'**
  String get personaL1Subtitle;

  /// No description provided for @personaL2Subtitle.
  ///
  /// In zh, this message translates to:
  /// **'系统与你协作校准后的标签与能力判断'**
  String get personaL2Subtitle;

  /// No description provided for @personaInferenceTitle.
  ///
  /// In zh, this message translates to:
  /// **'系统推断与策略'**
  String get personaInferenceTitle;

  /// No description provided for @personaInferenceSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'更技术性的推断偏好与当前策略，默认收起'**
  String get personaInferenceSubtitle;

  /// No description provided for @personaQuickAccessSystemUpdates.
  ///
  /// In zh, this message translates to:
  /// **'系统更新'**
  String get personaQuickAccessSystemUpdates;

  /// No description provided for @personaQuickAccessMemorySettings.
  ///
  /// In zh, this message translates to:
  /// **'记忆设置'**
  String get personaQuickAccessMemorySettings;

  /// No description provided for @personaCoreProfileUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'核心画像暂时不可用'**
  String get personaCoreProfileUnavailable;

  /// No description provided for @personaDegradedMode.
  ///
  /// In zh, this message translates to:
  /// **'已切换为降级展示，你仍然可以查看和刷新其它分区。\n{message}'**
  String personaDegradedMode(Object message);

  /// No description provided for @personaRetryFullProfile.
  ///
  /// In zh, this message translates to:
  /// **'重试完整画像'**
  String get personaRetryFullProfile;

  /// No description provided for @personaActiveGoal.
  ///
  /// In zh, this message translates to:
  /// **'你当前最明确的目标是：{goalTitle}。'**
  String personaActiveGoal(Object goalTitle);

  /// No description provided for @personaLearningPreference.
  ///
  /// In zh, this message translates to:
  /// **'你的学习偏好更接近{learningStyle}，系统回答深度倾向{responseDepth}。'**
  String personaLearningPreference(Object learningStyle, Object responseDepth);

  /// No description provided for @personaObservedPattern.
  ///
  /// In zh, this message translates to:
  /// **'系统最近观察到的主要模式是：{pattern}。'**
  String personaObservedPattern(Object pattern);

  /// No description provided for @personaCognitiveClueCount.
  ///
  /// In zh, this message translates to:
  /// **'画像里已积累 {count} 条可用于个性化推荐的认知线索。'**
  String personaCognitiveClueCount(Object count);

  /// No description provided for @personaProfileSparse.
  ///
  /// In zh, this message translates to:
  /// **'当前画像还比较稀疏，继续使用后这里会变成更自然、更具体的总结。'**
  String get personaProfileSparse;

  /// No description provided for @personaSimplifiedUnderstanding.
  ///
  /// In zh, this message translates to:
  /// **'这是系统目前对你的简化理解：'**
  String get personaSimplifiedUnderstanding;

  /// No description provided for @personaSectionRefresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新'**
  String get personaSectionRefresh;

  /// No description provided for @personaSectionLoading.
  ///
  /// In zh, this message translates to:
  /// **'加载中…'**
  String get personaSectionLoading;

  /// No description provided for @personaLoadFailedError.
  ///
  /// In zh, this message translates to:
  /// **'加载失败：{error}'**
  String personaLoadFailedError(Object error);

  /// No description provided for @personaPreferenceVersionReason.
  ///
  /// In zh, this message translates to:
  /// **'当前显式偏好与画像上下文版本。'**
  String get personaPreferenceVersionReason;

  /// No description provided for @personaActivePreferencesReason.
  ///
  /// In zh, this message translates to:
  /// **'当前用于 AI 与系统联动的显式偏好。'**
  String get personaActivePreferencesReason;

  /// No description provided for @personaKnowledgeSummaryReason.
  ///
  /// In zh, this message translates to:
  /// **'知识掌握度与当前活跃学习主题摘要。'**
  String get personaKnowledgeSummaryReason;

  /// No description provided for @personaCognitiveSummaryReason.
  ///
  /// In zh, this message translates to:
  /// **'当前认知模式与风险信号摘要。'**
  String get personaCognitiveSummaryReason;

  /// No description provided for @personaInferredDefaultReason.
  ///
  /// In zh, this message translates to:
  /// **'系统会根据最近行为持续更新这项推断。'**
  String get personaInferredDefaultReason;

  /// No description provided for @personaViewRecord.
  ///
  /// In zh, this message translates to:
  /// **'查看记录'**
  String get personaViewRecord;

  /// No description provided for @personaUpdate.
  ///
  /// In zh, this message translates to:
  /// **'更新'**
  String get personaUpdate;

  /// No description provided for @personaAdjust.
  ///
  /// In zh, this message translates to:
  /// **'调整'**
  String get personaAdjust;

  /// No description provided for @personaManualOverride.
  ///
  /// In zh, this message translates to:
  /// **'手动覆盖'**
  String get personaManualOverride;

  /// No description provided for @personaPolicy.
  ///
  /// In zh, this message translates to:
  /// **'策略'**
  String get personaPolicy;

  /// No description provided for @personaSourcePattern.
  ///
  /// In zh, this message translates to:
  /// **'来源模式：{pattern}'**
  String personaSourcePattern(Object pattern);

  /// No description provided for @personaActivePolicyReason.
  ///
  /// In zh, this message translates to:
  /// **'当前已生效的系统策略。'**
  String get personaActivePolicyReason;

  /// No description provided for @personaCorrectionSubmitFailed.
  ///
  /// In zh, this message translates to:
  /// **'提交修正失败：{error}'**
  String personaCorrectionSubmitFailed(Object error);

  /// No description provided for @personaPreferenceUpdated.
  ///
  /// In zh, this message translates to:
  /// **'偏好已更新'**
  String get personaPreferenceUpdated;

  /// No description provided for @personaPreferenceUpdateFailed.
  ///
  /// In zh, this message translates to:
  /// **'偏好更新失败：{error}'**
  String personaPreferenceUpdateFailed(Object error);

  /// No description provided for @personaRolledBack.
  ///
  /// In zh, this message translates to:
  /// **'已回滚到上一版本'**
  String get personaRolledBack;

  /// No description provided for @personaRollbackFailed.
  ///
  /// In zh, this message translates to:
  /// **'回滚失败：{error}'**
  String personaRollbackFailed(Object error);

  /// No description provided for @personaGoalUpdated.
  ///
  /// In zh, this message translates to:
  /// **'目标已更新'**
  String get personaGoalUpdated;

  /// No description provided for @personaGoalUpdateFailed.
  ///
  /// In zh, this message translates to:
  /// **'目标更新失败：{error}'**
  String personaGoalUpdateFailed(Object error);

  /// No description provided for @personaInferredAdjusted.
  ///
  /// In zh, this message translates to:
  /// **'推断偏好已调整'**
  String get personaInferredAdjusted;

  /// No description provided for @personaAdjustFailed.
  ///
  /// In zh, this message translates to:
  /// **'调整失败：{error}'**
  String personaAdjustFailed(Object error);

  /// No description provided for @personaInferredReset.
  ///
  /// In zh, this message translates to:
  /// **'已恢复系统推断值'**
  String get personaInferredReset;

  /// No description provided for @personaRestoreFailed.
  ///
  /// In zh, this message translates to:
  /// **'恢复失败：{error}'**
  String personaRestoreFailed(Object error);

  /// No description provided for @personaUnknownError.
  ///
  /// In zh, this message translates to:
  /// **'未知错误'**
  String get personaUnknownError;

  /// No description provided for @personaHintDecimalRange.
  ///
  /// In zh, this message translates to:
  /// **'请输入 0.0 到 1.0 之间的数字'**
  String get personaHintDecimalRange;

  /// No description provided for @personaHintStudyMinutes.
  ///
  /// In zh, this message translates to:
  /// **'请输入学习时长（分钟）'**
  String get personaHintStudyMinutes;

  /// No description provided for @personaHintPositiveMinutes.
  ///
  /// In zh, this message translates to:
  /// **'请输入大于 0 的分钟数'**
  String get personaHintPositiveMinutes;

  /// No description provided for @personaHintValidPreference.
  ///
  /// In zh, this message translates to:
  /// **'请输入有效的偏好值'**
  String get personaHintValidPreference;

  /// No description provided for @examSprintTitle.
  ///
  /// In zh, this message translates to:
  /// **'考试冲刺设置'**
  String get examSprintTitle;

  /// No description provided for @examSprintMinutesPerDay.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟/天'**
  String examSprintMinutesPerDay(Object minutes);

  /// No description provided for @examSprintStep1Subject.
  ///
  /// In zh, this message translates to:
  /// **'1. 哪门课？'**
  String get examSprintStep1Subject;

  /// No description provided for @examSprintSubjectHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：计算机网络 / 高数 / 英语四级'**
  String get examSprintSubjectHint;

  /// No description provided for @examSprintSubjectRequired.
  ///
  /// In zh, this message translates to:
  /// **'先告诉我你要冲刺哪门课'**
  String get examSprintSubjectRequired;

  /// No description provided for @examSprintStep2Date.
  ///
  /// In zh, this message translates to:
  /// **'2. 考试哪天？'**
  String get examSprintStep2Date;

  /// No description provided for @examSprintSelectDate.
  ///
  /// In zh, this message translates to:
  /// **'选择考试日期'**
  String get examSprintSelectDate;

  /// No description provided for @examSprintDateHint.
  ///
  /// In zh, this message translates to:
  /// **'日期会决定冲刺天数和节奏'**
  String get examSprintDateHint;

  /// No description provided for @examSprintStep3Target.
  ///
  /// In zh, this message translates to:
  /// **'3. 目标是通过、保分还是冲高分？'**
  String get examSprintStep3Target;

  /// No description provided for @examSprintStep4Scope.
  ///
  /// In zh, this message translates to:
  /// **'4. 考试范围 / 老师重点有吗？'**
  String get examSprintStep4Scope;

  /// No description provided for @examSprintStep4Subtitle.
  ///
  /// In zh, this message translates to:
  /// **'可以直接粘贴重点，也可以上传 PDF / DOCX / PPT / TXT。'**
  String get examSprintStep4Subtitle;

  /// No description provided for @examSprintScopeHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：重点看传输层、网络层；老师说会考简答和计算题。'**
  String get examSprintScopeHint;

  /// No description provided for @examSprintUpload.
  ///
  /// In zh, this message translates to:
  /// **'上传资料'**
  String get examSprintUpload;

  /// No description provided for @examSprintNoUpload.
  ///
  /// In zh, this message translates to:
  /// **'还没上传资料'**
  String get examSprintNoUpload;

  /// No description provided for @examSprintUploadedCount.
  ///
  /// In zh, this message translates to:
  /// **'已上传 {count} 份资料'**
  String examSprintUploadedCount(Object count);

  /// No description provided for @examSprintStep5Baseline.
  ///
  /// In zh, this message translates to:
  /// **'5. 你现在大概会多少？最怕哪几章？'**
  String get examSprintStep5Baseline;

  /// No description provided for @examSprintWeakChapters.
  ///
  /// In zh, this message translates to:
  /// **'最怕哪几章？'**
  String get examSprintWeakChapters;

  /// No description provided for @examSprintStep6Daily.
  ///
  /// In zh, this message translates to:
  /// **'6. 每天真实能学多久？'**
  String get examSprintStep6Daily;

  /// No description provided for @examSprintMinutesPerDayLabel.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟 / 天'**
  String examSprintMinutesPerDayLabel(Object minutes);

  /// No description provided for @examSprintMinutesLabel.
  ///
  /// In zh, this message translates to:
  /// **'{minutes} 分钟'**
  String examSprintMinutesLabel(Object minutes);

  /// No description provided for @examSprintDailyHint.
  ///
  /// In zh, this message translates to:
  /// **'用「你大概率能坚持」的时间，不用理想状态。'**
  String get examSprintDailyHint;

  /// No description provided for @examSprintGenerate.
  ///
  /// In zh, this message translates to:
  /// **'生成我的第一天任务'**
  String get examSprintGenerate;

  /// No description provided for @examSprintSubmitHint.
  ///
  /// In zh, this message translates to:
  /// **'提交后会在 3 秒内给出初评，并直接带你进入计划或第一天任务。'**
  String get examSprintSubmitHint;

  /// No description provided for @examSprintHeroTitle.
  ///
  /// In zh, this message translates to:
  /// **'不是填问卷，是一起确定起点'**
  String get examSprintHeroTitle;

  /// No description provided for @examSprintHeroSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'填完这 6 个问题，我会直接给你初始评估、推荐策略和第一天任务。'**
  String get examSprintHeroSubtitle;

  /// No description provided for @examSprintUploadSuccess.
  ///
  /// In zh, this message translates to:
  /// **'资料已上传'**
  String get examSprintUploadSuccess;

  /// No description provided for @examSprintSelectDateFirst.
  ///
  /// In zh, this message translates to:
  /// **'先选择考试日期'**
  String get examSprintSelectDateFirst;

  /// No description provided for @examSprintAssessmentComplete.
  ///
  /// In zh, this message translates to:
  /// **'初步评估已完成'**
  String get examSprintAssessmentComplete;

  /// No description provided for @examSprintPassProbability.
  ///
  /// In zh, this message translates to:
  /// **'通过概率 {percent}%'**
  String examSprintPassProbability(Object percent);

  /// No description provided for @examSprintRecommendedMode.
  ///
  /// In zh, this message translates to:
  /// **'建议模式 {mode}'**
  String examSprintRecommendedMode(Object mode);

  /// No description provided for @examSprintFirstDayFocus.
  ///
  /// In zh, this message translates to:
  /// **'第一天先做什么'**
  String get examSprintFirstDayFocus;

  /// No description provided for @examSprintStartFirstDay.
  ///
  /// In zh, this message translates to:
  /// **'开始第一天任务'**
  String get examSprintStartFirstDay;

  /// No description provided for @examSprintViewPlan.
  ///
  /// In zh, this message translates to:
  /// **'查看计划'**
  String get examSprintViewPlan;

  /// No description provided for @examSprintViewFullPlan.
  ///
  /// In zh, this message translates to:
  /// **'查看整个计划'**
  String get examSprintViewFullPlan;

  /// No description provided for @examSprintBaselineAlmostZero.
  ///
  /// In zh, this message translates to:
  /// **'几乎要从零开始'**
  String get examSprintBaselineAlmostZero;

  /// No description provided for @examSprintBaselineUnstable.
  ///
  /// In zh, this message translates to:
  /// **'上过课，但基础还不稳'**
  String get examSprintBaselineUnstable;

  /// No description provided for @examSprintBaselinePartial.
  ///
  /// In zh, this message translates to:
  /// **'有一部分基础，可以边补边冲'**
  String get examSprintBaselinePartial;

  /// No description provided for @examSprintBaselineSolid.
  ///
  /// In zh, this message translates to:
  /// **'基础不错，重点是提分校准'**
  String get examSprintBaselineSolid;

  /// No description provided for @examSprintDayCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 天'**
  String examSprintDayCount(Object count);

  /// No description provided for @examSprintTargetPass.
  ///
  /// In zh, this message translates to:
  /// **'通过'**
  String get examSprintTargetPass;

  /// No description provided for @examSprintTargetHold.
  ///
  /// In zh, this message translates to:
  /// **'保分'**
  String get examSprintTargetHold;

  /// No description provided for @examSprintTargetHighScore.
  ///
  /// In zh, this message translates to:
  /// **'冲高分'**
  String get examSprintTargetHighScore;

  /// No description provided for @memorySettingsTitle.
  ///
  /// In zh, this message translates to:
  /// **'记忆控制'**
  String get memorySettingsTitle;

  /// No description provided for @memorySettingsBack.
  ///
  /// In zh, this message translates to:
  /// **'返回'**
  String get memorySettingsBack;

  /// No description provided for @memorySettingsDisabled.
  ///
  /// In zh, this message translates to:
  /// **'记忆控制未启用'**
  String get memorySettingsDisabled;

  /// No description provided for @memorySettingsLoadError.
  ///
  /// In zh, this message translates to:
  /// **'加载记忆设置失败: {error}'**
  String memorySettingsLoadError(Object error);

  /// No description provided for @memorySettingsSaveError.
  ///
  /// In zh, this message translates to:
  /// **'保存失败: {error}'**
  String memorySettingsSaveError(Object error);

  /// No description provided for @memorySettingsSaveSuccess.
  ///
  /// In zh, this message translates to:
  /// **'记忆设置已更新'**
  String get memorySettingsSaveSuccess;

  /// No description provided for @memorySettingsUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'记忆控制不可用'**
  String get memorySettingsUnavailable;

  /// No description provided for @memorySettingsEnabledChip.
  ///
  /// In zh, this message translates to:
  /// **'记忆已启用'**
  String get memorySettingsEnabledChip;

  /// No description provided for @memorySettingsDisabledChip.
  ///
  /// In zh, this message translates to:
  /// **'记忆已暂停'**
  String get memorySettingsDisabledChip;

  /// No description provided for @memorySettingsControllableChip.
  ///
  /// In zh, this message translates to:
  /// **'偏好可控'**
  String get memorySettingsControllableChip;

  /// No description provided for @memorySettingsDescription.
  ///
  /// In zh, this message translates to:
  /// **'控制系统长期记忆如何学习你的偏好、目标与经历。默认更克制，只有对后续决策真正有价值的信息才应保留。'**
  String get memorySettingsDescription;

  /// No description provided for @memorySettingsEnableTitle.
  ///
  /// In zh, this message translates to:
  /// **'启用长期记忆'**
  String get memorySettingsEnableTitle;

  /// No description provided for @memorySettingsEnableDesc.
  ///
  /// In zh, this message translates to:
  /// **'关闭后会暂停新的记忆写入，但不会删除历史记录。'**
  String get memorySettingsEnableDesc;

  /// No description provided for @memorySettingsSocialTitle.
  ///
  /// In zh, this message translates to:
  /// **'社交语义子开关'**
  String get memorySettingsSocialTitle;

  /// No description provided for @memorySettingsSocialDesc.
  ///
  /// In zh, this message translates to:
  /// **'Stage 17 只做记忆声明与前门读取。关闭某一类后，该类社交语义会在前门中被隐藏。'**
  String get memorySettingsSocialDesc;

  /// No description provided for @memorySettingsSocialSelf.
  ///
  /// In zh, this message translates to:
  /// **'自我记忆'**
  String get memorySettingsSocialSelf;

  /// No description provided for @memorySettingsSocialPersonMention.
  ///
  /// In zh, this message translates to:
  /// **'人物提及'**
  String get memorySettingsSocialPersonMention;

  /// No description provided for @memorySettingsSocialRelationship.
  ///
  /// In zh, this message translates to:
  /// **'关系动态'**
  String get memorySettingsSocialRelationship;

  /// No description provided for @memorySettingsSocialCommitment.
  ///
  /// In zh, this message translates to:
  /// **'承诺事项'**
  String get memorySettingsSocialCommitment;

  /// No description provided for @memorySettingsPushTitle.
  ///
  /// In zh, this message translates to:
  /// **'主动提醒'**
  String get memorySettingsPushTitle;

  /// No description provided for @memorySettingsPushDesc.
  ///
  /// In zh, this message translates to:
  /// **'Stage 18 默认关闭。只有你显式开启后，系统才会发送承诺跟进或活跃恢复提醒。'**
  String get memorySettingsPushDesc;

  /// No description provided for @memorySettingsPushEnableTitle.
  ///
  /// In zh, this message translates to:
  /// **'启用主动提醒'**
  String get memorySettingsPushEnableTitle;

  /// No description provided for @memorySettingsPushEnableDesc.
  ///
  /// In zh, this message translates to:
  /// **'总开关。关闭后 Stage 18 主动提醒会全部停用。'**
  String get memorySettingsPushEnableDesc;

  /// No description provided for @memorySettingsPushFollowUpTitle.
  ///
  /// In zh, this message translates to:
  /// **'承诺跟进'**
  String get memorySettingsPushFollowUpTitle;

  /// No description provided for @memorySettingsPushFollowUpDesc.
  ///
  /// In zh, this message translates to:
  /// **'只针对你明确表达过、且已经逾期的承诺事项。'**
  String get memorySettingsPushFollowUpDesc;

  /// No description provided for @memorySettingsPushRecoveryTitle.
  ///
  /// In zh, this message translates to:
  /// **'活跃恢复'**
  String get memorySettingsPushRecoveryTitle;

  /// No description provided for @memorySettingsPushRecoveryDesc.
  ///
  /// In zh, this message translates to:
  /// **'只针对曾经连续活跃、且 72 小时未活跃的情况。'**
  String get memorySettingsPushRecoveryDesc;

  /// No description provided for @memorySettingsQuietHoursTitle.
  ///
  /// In zh, this message translates to:
  /// **'静默时段'**
  String get memorySettingsQuietHoursTitle;

  /// No description provided for @memorySettingsQuietHoursDesc.
  ///
  /// In zh, this message translates to:
  /// **'你可以收窄系统默认的 22:00-08:00，但不能把提醒扩张到这段时间里。'**
  String get memorySettingsQuietHoursDesc;

  /// No description provided for @memorySettingsStartTime.
  ///
  /// In zh, this message translates to:
  /// **'开始时间'**
  String get memorySettingsStartTime;

  /// No description provided for @memorySettingsEndTime.
  ///
  /// In zh, this message translates to:
  /// **'结束时间'**
  String get memorySettingsEndTime;

  /// No description provided for @memorySettingsCurrentTimezone.
  ///
  /// In zh, this message translates to:
  /// **'当前时区：{timezone}'**
  String memorySettingsCurrentTimezone(Object timezone);

  /// No description provided for @memorySettingsViewInbox.
  ///
  /// In zh, this message translates to:
  /// **'查看提醒收件箱'**
  String get memorySettingsViewInbox;

  /// No description provided for @memorySettingsTypeTitle.
  ///
  /// In zh, this message translates to:
  /// **'记忆类型'**
  String get memorySettingsTypeTitle;

  /// No description provided for @memorySettingsTypeDesc.
  ///
  /// In zh, this message translates to:
  /// **'决定哪些内容会被长期记住。'**
  String get memorySettingsTypeDesc;

  /// No description provided for @memorySettingsPreferenceTitle.
  ///
  /// In zh, this message translates to:
  /// **'偏好'**
  String get memorySettingsPreferenceTitle;

  /// No description provided for @memorySettingsPreferenceDesc.
  ///
  /// In zh, this message translates to:
  /// **'记录回答风格、学习节奏和常见偏好。'**
  String get memorySettingsPreferenceDesc;

  /// No description provided for @memorySettingsGoalTitle.
  ///
  /// In zh, this message translates to:
  /// **'目标'**
  String get memorySettingsGoalTitle;

  /// No description provided for @memorySettingsGoalDesc.
  ///
  /// In zh, this message translates to:
  /// **'记录已确认的长期目标和阶段意图。'**
  String get memorySettingsGoalDesc;

  /// No description provided for @memorySettingsEpisodicTitle.
  ///
  /// In zh, this message translates to:
  /// **'经历'**
  String get memorySettingsEpisodicTitle;

  /// No description provided for @memorySettingsEpisodicDesc.
  ///
  /// In zh, this message translates to:
  /// **'记录对后续决策有帮助的关键事件与反馈。'**
  String get memorySettingsEpisodicDesc;

  /// No description provided for @memorySettingsInferredTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 自动记忆'**
  String get memorySettingsInferredTitle;

  /// No description provided for @memorySettingsInferredDesc.
  ///
  /// In zh, this message translates to:
  /// **'允许系统从聊天中推断短期经历；每条都必须可见、可撤销。'**
  String get memorySettingsInferredDesc;

  /// No description provided for @memorySettingsCaptureTitle.
  ///
  /// In zh, this message translates to:
  /// **'捕获强度'**
  String get memorySettingsCaptureTitle;

  /// No description provided for @memorySettingsCaptureDesc.
  ///
  /// In zh, this message translates to:
  /// **'越高越积极，但也会记录更多上下文。'**
  String get memorySettingsCaptureDesc;

  /// No description provided for @memorySettingsCaptureLow.
  ///
  /// In zh, this message translates to:
  /// **'低'**
  String get memorySettingsCaptureLow;

  /// No description provided for @memorySettingsCaptureMedium.
  ///
  /// In zh, this message translates to:
  /// **'中'**
  String get memorySettingsCaptureMedium;

  /// No description provided for @memorySettingsCaptureHigh.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get memorySettingsCaptureHigh;

  /// No description provided for @memorySettingsBlockPrefTitle.
  ///
  /// In zh, this message translates to:
  /// **'屏蔽偏好'**
  String get memorySettingsBlockPrefTitle;

  /// No description provided for @memorySettingsBlockPrefDesc.
  ///
  /// In zh, this message translates to:
  /// **'不希望长期存储的偏好项可以在这里关闭。'**
  String get memorySettingsBlockPrefDesc;

  /// No description provided for @memorySettingsBlockSourceTitle.
  ///
  /// In zh, this message translates to:
  /// **'屏蔽来源'**
  String get memorySettingsBlockSourceTitle;

  /// No description provided for @memorySettingsBlockSourceDesc.
  ///
  /// In zh, this message translates to:
  /// **'限制哪些入口不会写入长期记忆。'**
  String get memorySettingsBlockSourceDesc;

  /// No description provided for @memorySettingsSaveButton.
  ///
  /// In zh, this message translates to:
  /// **'保存设置'**
  String get memorySettingsSaveButton;

  /// No description provided for @memorySettingsSaving.
  ///
  /// In zh, this message translates to:
  /// **'保存中...'**
  String get memorySettingsSaving;

  /// No description provided for @reportLearningAnalysisReport.
  ///
  /// In zh, this message translates to:
  /// **'学习分析报告'**
  String get reportLearningAnalysisReport;

  /// No description provided for @reportContinuationSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'继续查看本次学习旅程的分析报告'**
  String get reportContinuationSubtitle;

  /// No description provided for @reportPartialDataDisclaimer.
  ///
  /// In zh, this message translates to:
  /// **'部分数据，仅供参考'**
  String get reportPartialDataDisclaimer;

  /// No description provided for @reportPartialDataMessage.
  ///
  /// In zh, this message translates to:
  /// **'当前基于部分学习记录生成，结果可能不够全面。'**
  String get reportPartialDataMessage;

  /// No description provided for @reportDiagnosisPanelEyebrow.
  ///
  /// In zh, this message translates to:
  /// **'学习诊断面板'**
  String get reportDiagnosisPanelEyebrow;

  /// No description provided for @reportOpenGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'打开知识星图'**
  String get reportOpenGalaxy;

  /// No description provided for @reportPrioritizeNode.
  ///
  /// In zh, this message translates to:
  /// **'优先处理 {nodeName}'**
  String reportPrioritizeNode(Object nodeName);

  /// No description provided for @reportRangeWeek.
  ///
  /// In zh, this message translates to:
  /// **'本周'**
  String get reportRangeWeek;

  /// No description provided for @reportRangeMonth.
  ///
  /// In zh, this message translates to:
  /// **'本月'**
  String get reportRangeMonth;

  /// No description provided for @reportRangeAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get reportRangeAll;

  /// No description provided for @reportCurrentLearningTopic.
  ///
  /// In zh, this message translates to:
  /// **'当前学习主题'**
  String get reportCurrentLearningTopic;

  /// No description provided for @reportMasteryTrendTitle.
  ///
  /// In zh, this message translates to:
  /// **'掌握度趋势'**
  String get reportMasteryTrendTitle;

  /// No description provided for @reportPartialDataPill.
  ///
  /// In zh, this message translates to:
  /// **'部分数据，仅供参考'**
  String get reportPartialDataPill;

  /// No description provided for @reportTrendEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'完成更多学习后将在此展示趋势分析'**
  String get reportTrendEmptyTitle;

  /// No description provided for @reportTrendEmptyMessage.
  ///
  /// In zh, this message translates to:
  /// **'当前还没有足够的真实学习记录来生成趋势，请先完成学习任务、练习或复盘。'**
  String get reportTrendEmptyMessage;

  /// No description provided for @reportTrendChartHint.
  ///
  /// In zh, this message translates to:
  /// **'拖动或点按时间点，就能把这条线和当时的学习投入一起看清楚。'**
  String get reportTrendChartHint;

  /// No description provided for @reportRadarChartTitle.
  ///
  /// In zh, this message translates to:
  /// **'掌握度雷达图'**
  String get reportRadarChartTitle;

  /// No description provided for @reportRadarSubtitleInsufficient.
  ///
  /// In zh, this message translates to:
  /// **'完成更多学习后将在此展示掌握度分析'**
  String get reportRadarSubtitleInsufficient;

  /// No description provided for @reportRadarSubtitleNoComparison.
  ///
  /// In zh, this message translates to:
  /// **'点击任一维度查看更细的掌握情况'**
  String get reportRadarSubtitleNoComparison;

  /// No description provided for @reportRadarSubtitleWithComparison.
  ///
  /// In zh, this message translates to:
  /// **'当前报告已叠加上次轮廓，可点击维度查看详情'**
  String get reportRadarSubtitleWithComparison;

  /// No description provided for @reportRadarEmptyMessage.
  ///
  /// In zh, this message translates to:
  /// **'掌握度雷达图需要真实学习记录支撑，先开始一次学习并留下结果。'**
  String get reportRadarEmptyMessage;

  /// No description provided for @reportKeyMetricsTitle.
  ///
  /// In zh, this message translates to:
  /// **'关键指标'**
  String get reportKeyMetricsTitle;

  /// No description provided for @reportMetricTotalMastery.
  ///
  /// In zh, this message translates to:
  /// **'总掌握度'**
  String get reportMetricTotalMastery;

  /// No description provided for @reportMetricKnowledgeCount.
  ///
  /// In zh, this message translates to:
  /// **'知识点数'**
  String get reportMetricKnowledgeCount;

  /// No description provided for @reportMetricStrengths.
  ///
  /// In zh, this message translates to:
  /// **'强项'**
  String get reportMetricStrengths;

  /// No description provided for @reportMetricWeaknesses.
  ///
  /// In zh, this message translates to:
  /// **'薄弱点'**
  String get reportMetricWeaknesses;

  /// No description provided for @reportExecutionProfileLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'执行画像暂时没有加载出来，不影响你先阅读本次学习报告。'**
  String get reportExecutionProfileLoadFailed;

  /// No description provided for @reportKeyDimensionsTitle.
  ///
  /// In zh, this message translates to:
  /// **'重点知识维度'**
  String get reportKeyDimensionsTitle;

  /// No description provided for @reportAiAnalysisTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI 分析报告'**
  String get reportAiAnalysisTitle;

  /// No description provided for @reportBackToGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'回到 Galaxy'**
  String get reportBackToGalaxy;

  /// No description provided for @reportViewSprintHistory.
  ///
  /// In zh, this message translates to:
  /// **'查看 Sprint 历史'**
  String get reportViewSprintHistory;

  /// No description provided for @reportShareTitle.
  ///
  /// In zh, this message translates to:
  /// **'学习报告 · 平均掌握度 {mastery}%'**
  String reportShareTitle(Object mastery);

  /// No description provided for @reportShareSubtitleSummary.
  ///
  /// In zh, this message translates to:
  /// **'本轮学习分析摘要'**
  String get reportShareSubtitleSummary;

  /// No description provided for @reportShareSubtitlePriority.
  ///
  /// In zh, this message translates to:
  /// **'优先补强 {nodeName}'**
  String reportShareSubtitlePriority(Object nodeName);

  /// No description provided for @reportShareMetadataDimensions.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个维度'**
  String reportShareMetadataDimensions(Object count);

  /// No description provided for @reportShareMessageWithMastery.
  ///
  /// In zh, this message translates to:
  /// **'我刚在 Sparkle 生成了一份学习分析报告，平均掌握度 {mastery}%。'**
  String reportShareMessageWithMastery(Object mastery);

  /// No description provided for @reportShareMessageWithNode.
  ///
  /// In zh, this message translates to:
  /// **'我刚在 Sparkle 生成了一份学习分析报告，当前优先补强的是 {nodeName}。'**
  String reportShareMessageWithNode(Object nodeName);

  /// No description provided for @reportHeroTitlePriority.
  ///
  /// In zh, this message translates to:
  /// **'当前最该先收口的是 {nodeName}'**
  String reportHeroTitlePriority(Object nodeName);

  /// No description provided for @reportHeroTitleStable.
  ///
  /// In zh, this message translates to:
  /// **'你的稳定区已经开始成形'**
  String get reportHeroTitleStable;

  /// No description provided for @reportHeroTitleBuild.
  ///
  /// In zh, this message translates to:
  /// **'先用真实学习记录建立分析基础'**
  String get reportHeroTitleBuild;

  /// No description provided for @reportHeroSubtitleDeltaUp.
  ///
  /// In zh, this message translates to:
  /// **'整体掌握度还在抬升，但 {nodeName} 依然是最容易拖慢进度的环节，优先补它最划算。'**
  String reportHeroSubtitleDeltaUp(Object nodeName);

  /// No description provided for @reportHeroSubtitleDeltaDown.
  ///
  /// In zh, this message translates to:
  /// **'最近节奏有一点回落，先别继续铺开范围，优先把 {nodeName} 重新拉稳。'**
  String reportHeroSubtitleDeltaDown(Object nodeName);

  /// No description provided for @reportHeroSubtitleStrong.
  ///
  /// In zh, this message translates to:
  /// **'这份报告已经把当前强项、薄弱点和趋势放到同一个面板里，先看重点，再决定下一步。'**
  String get reportHeroSubtitleStrong;

  /// No description provided for @reportHeroSubtitleDefault.
  ///
  /// In zh, this message translates to:
  /// **'先用这份报告确认方向，后续随着更多记录补齐，趋势会越来越清楚。'**
  String get reportHeroSubtitleDefault;

  /// No description provided for @reportMetricAvgMastery.
  ///
  /// In zh, this message translates to:
  /// **'平均掌握度'**
  String get reportMetricAvgMastery;

  /// No description provided for @reportMetricPriority.
  ///
  /// In zh, this message translates to:
  /// **'优先补强'**
  String get reportMetricPriority;

  /// No description provided for @reportMetricCurrentStrength.
  ///
  /// In zh, this message translates to:
  /// **'当前强项'**
  String get reportMetricCurrentStrength;

  /// No description provided for @reportMetricTrendChange.
  ///
  /// In zh, this message translates to:
  /// **'变化趋势'**
  String get reportMetricTrendChange;

  /// No description provided for @reportPlaceholderEmpty.
  ///
  /// In zh, this message translates to:
  /// **'暂无学习报告数据。'**
  String get reportPlaceholderEmpty;

  /// No description provided for @reportContinueReading.
  ///
  /// In zh, this message translates to:
  /// **'继续阅读报告'**
  String get reportContinueReading;

  /// No description provided for @reportEvidenceAndAdvice.
  ///
  /// In zh, this message translates to:
  /// **'证据与建议'**
  String get reportEvidenceAndAdvice;

  /// No description provided for @reportGotIt.
  ///
  /// In zh, this message translates to:
  /// **'知道了'**
  String get reportGotIt;

  /// No description provided for @reportMasteryStable.
  ///
  /// In zh, this message translates to:
  /// **'掌握稳定'**
  String get reportMasteryStable;

  /// No description provided for @reportMasteryConsolidate.
  ///
  /// In zh, this message translates to:
  /// **'仍可巩固'**
  String get reportMasteryConsolidate;

  /// No description provided for @reportMasteryNeedFocus.
  ///
  /// In zh, this message translates to:
  /// **'需要重点补强'**
  String get reportMasteryNeedFocus;

  /// No description provided for @reportGuidanceStable.
  ///
  /// In zh, this message translates to:
  /// **'这个知识点已经比较稳，可以更多地通过应用题和迁移练习来保持熟练度。'**
  String get reportGuidanceStable;

  /// No description provided for @reportGuidanceConsolidate.
  ///
  /// In zh, this message translates to:
  /// **'这个知识点理解基本建立，但在连续推理或综合题里可能还会波动，适合再补一轮刻意练习。'**
  String get reportGuidanceConsolidate;

  /// No description provided for @reportGuidanceNeedFocus.
  ///
  /// In zh, this message translates to:
  /// **'这个知识点当前是明显薄弱环节，建议先回到定义、例题和前置概念，再重新做相关练习。'**
  String get reportGuidanceNeedFocus;

  /// No description provided for @reportChartFirstReport.
  ///
  /// In zh, this message translates to:
  /// **'第一份报告已经准备好了。下次再来看，这里就会出现你的趋势变化线。'**
  String get reportChartFirstReport;

  /// No description provided for @reportChartMasteryLabel.
  ///
  /// In zh, this message translates to:
  /// **'掌握度 {mastery}%'**
  String reportChartMasteryLabel(Object mastery);

  /// No description provided for @reportChartStudyMinutes.
  ///
  /// In zh, this message translates to:
  /// **'学习时长 {minutes} 分钟'**
  String reportChartStudyMinutes(Object minutes);

  /// No description provided for @reportChartMinutesShort.
  ///
  /// In zh, this message translates to:
  /// **'{count}分'**
  String reportChartMinutesShort(Object count);

  /// No description provided for @reportChartZeroMinutes.
  ///
  /// In zh, this message translates to:
  /// **'0分'**
  String get reportChartZeroMinutes;

  /// No description provided for @reportLegendMastery.
  ///
  /// In zh, this message translates to:
  /// **'掌握度'**
  String get reportLegendMastery;

  /// No description provided for @reportLegendStudyDuration.
  ///
  /// In zh, this message translates to:
  /// **'学习时长'**
  String get reportLegendStudyDuration;

  /// No description provided for @reportDiagnosisSummaryTitle.
  ///
  /// In zh, this message translates to:
  /// **'诊断摘要'**
  String get reportDiagnosisSummaryTitle;

  /// No description provided for @reportDiagnosisSummaryDesc.
  ///
  /// In zh, this message translates to:
  /// **'先回答三个最关键的问题：你现在最稳的地方在哪里、最该补的地方在哪里、整体是在上升还是停滞。'**
  String get reportDiagnosisSummaryDesc;

  /// No description provided for @reportDiagnosisTitleStrength.
  ///
  /// In zh, this message translates to:
  /// **'当前强项'**
  String get reportDiagnosisTitleStrength;

  /// No description provided for @reportDiagnosisTitleWeakness.
  ///
  /// In zh, this message translates to:
  /// **'主要短板'**
  String get reportDiagnosisTitleWeakness;

  /// No description provided for @reportDiagnosisTitleTrend.
  ///
  /// In zh, this message translates to:
  /// **'整体趋势'**
  String get reportDiagnosisTitleTrend;

  /// No description provided for @reportDiagnosisHeadlinePending.
  ///
  /// In zh, this message translates to:
  /// **'待生成'**
  String get reportDiagnosisHeadlinePending;

  /// No description provided for @reportDiagnosisStrengthBodyPending.
  ///
  /// In zh, this message translates to:
  /// **'生成更多学习记录后，这里会出现最稳的知识点。'**
  String get reportDiagnosisStrengthBodyPending;

  /// No description provided for @reportDiagnosisStrengthBodyData.
  ///
  /// In zh, this message translates to:
  /// **'建议把它作为迁移练习的发力点，带动相关知识点一起稳住。'**
  String get reportDiagnosisStrengthBodyData;

  /// No description provided for @reportDiagnosisWeaknessBodyPending.
  ///
  /// In zh, this message translates to:
  /// **'当前还没有足够数据定位短板。'**
  String get reportDiagnosisWeaknessBodyPending;

  /// No description provided for @reportDiagnosisWeaknessBodyData.
  ///
  /// In zh, this message translates to:
  /// **'这是最值得先补的切入口，优先回到定义、例题和前置关系。'**
  String get reportDiagnosisWeaknessBodyData;

  /// No description provided for @reportDiagnosisWeaknessFallback.
  ///
  /// In zh, this message translates to:
  /// **'薄弱项'**
  String get reportDiagnosisWeaknessFallback;

  /// No description provided for @reportDiagnosisTrendWaitingComparison.
  ///
  /// In zh, this message translates to:
  /// **'等待历史对比'**
  String get reportDiagnosisTrendWaitingComparison;

  /// No description provided for @reportDiagnosisTrendBodyPending.
  ///
  /// In zh, this message translates to:
  /// **'再积累一到两份报告后，这里会显示你的连续变化趋势。'**
  String get reportDiagnosisTrendBodyPending;

  /// No description provided for @reportDiagnosisTrendBodyUp.
  ///
  /// In zh, this message translates to:
  /// **'掌握度在继续抬升，接下来更适合做巩固和迁移。'**
  String get reportDiagnosisTrendBodyUp;

  /// No description provided for @reportDiagnosisTrendBodyDown.
  ///
  /// In zh, this message translates to:
  /// **'最近有回落迹象，建议减少铺开面，先收口当前薄弱点。'**
  String get reportDiagnosisTrendBodyDown;

  /// No description provided for @reportTagConsolidate.
  ///
  /// In zh, this message translates to:
  /// **'可继续巩固'**
  String get reportTagConsolidate;

  /// No description provided for @reportTagProcessFirst.
  ///
  /// In zh, this message translates to:
  /// **'建议先处理'**
  String get reportTagProcessFirst;

  /// No description provided for @reportTagProcessSoon.
  ///
  /// In zh, this message translates to:
  /// **'建议尽快处理'**
  String get reportTagProcessSoon;

  /// No description provided for @reportTagKeepRhythm.
  ///
  /// In zh, this message translates to:
  /// **'保持当前节奏'**
  String get reportTagKeepRhythm;

  /// No description provided for @reportTagCloseGap.
  ///
  /// In zh, this message translates to:
  /// **'建议尽快收口'**
  String get reportTagCloseGap;

  /// No description provided for @reportTagAwaitMore.
  ///
  /// In zh, this message translates to:
  /// **'等待更多记录'**
  String get reportTagAwaitMore;

  /// No description provided for @reportTagObserve.
  ///
  /// In zh, this message translates to:
  /// **'建议继续观察'**
  String get reportTagObserve;

  /// No description provided for @reportActionTitle.
  ///
  /// In zh, this message translates to:
  /// **'下一步行动'**
  String get reportActionTitle;

  /// No description provided for @reportActionDescNoWeakness.
  ///
  /// In zh, this message translates to:
  /// **'先去知识星图确认当前结构，再生成更多练习数据，报告会自动给出更尖锐的下一步建议。'**
  String get reportActionDescNoWeakness;

  /// No description provided for @reportActionDescWithWeakness.
  ///
  /// In zh, this message translates to:
  /// **'优先围绕 {weakNode} 收口，再用 {strongNode} 做迁移练习，能更快把整体掌握度拉起来。'**
  String reportActionDescWithWeakness(Object weakNode, Object strongNode);

  /// No description provided for @reportActionExploreNode.
  ///
  /// In zh, this message translates to:
  /// **'推演 {nodeName}'**
  String reportActionExploreNode(Object nodeName);

  /// No description provided for @reportActionWeaknessFallback.
  ///
  /// In zh, this message translates to:
  /// **'薄弱项'**
  String get reportActionWeaknessFallback;

  /// No description provided for @reportActionStrengthFallback.
  ///
  /// In zh, this message translates to:
  /// **'当前强项'**
  String get reportActionStrengthFallback;

  /// No description provided for @reportActionEnterSimulation.
  ///
  /// In zh, this message translates to:
  /// **'进入学习仿真'**
  String get reportActionEnterSimulation;

  /// No description provided for @reportTrendAutoFillTitle.
  ///
  /// In zh, this message translates to:
  /// **'趋势会随着更多报告自动补全'**
  String get reportTrendAutoFillTitle;

  /// No description provided for @reportTrendFirstReportMessage.
  ///
  /// In zh, this message translates to:
  /// **'第一份报告已经生成好了。先按这次诊断聚焦薄弱知识点，下一次回来这里就会开始连成趋势线。'**
  String get reportTrendFirstReportMessage;

  /// No description provided for @reportTrendLoadingHistory.
  ///
  /// In zh, this message translates to:
  /// **'正在整理你的历史学习报告，稍后会把掌握度趋势补全到这里。'**
  String get reportTrendLoadingHistory;

  /// No description provided for @reportAiExecutionAssistant.
  ///
  /// In zh, this message translates to:
  /// **'AI执行助手'**
  String get reportAiExecutionAssistant;

  /// No description provided for @reportAiExecutionDesc.
  ///
  /// In zh, this message translates to:
  /// **'Sparkle 会记住哪些任务更适合交给 AI，以及这些委派实际帮你节省了多少时间。'**
  String get reportAiExecutionDesc;

  /// No description provided for @reportStatTotalExecutions.
  ///
  /// In zh, this message translates to:
  /// **'总执行'**
  String get reportStatTotalExecutions;

  /// No description provided for @reportStatUnitTimes.
  ///
  /// In zh, this message translates to:
  /// **'次'**
  String get reportStatUnitTimes;

  /// No description provided for @reportStatSuccessRate.
  ///
  /// In zh, this message translates to:
  /// **'成功率'**
  String get reportStatSuccessRate;

  /// No description provided for @reportStatTimeSaved.
  ///
  /// In zh, this message translates to:
  /// **'节省时间'**
  String get reportStatTimeSaved;

  /// No description provided for @reportStatUnitHours.
  ///
  /// In zh, this message translates to:
  /// **'小时'**
  String get reportStatUnitHours;

  /// No description provided for @reportStatUnitMinutes.
  ///
  /// In zh, this message translates to:
  /// **'分钟'**
  String get reportStatUnitMinutes;

  /// No description provided for @reportStatByTypeFormat.
  ///
  /// In zh, this message translates to:
  /// **'{key}: {count}次 · {rate}%'**
  String reportStatByTypeFormat(Object key, Object count, Object rate);

  /// No description provided for @bgmLibraryTitle.
  ///
  /// In zh, this message translates to:
  /// **'BGM 曲库与播放器'**
  String get bgmLibraryTitle;

  /// No description provided for @bgmLibraryRefresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新'**
  String get bgmLibraryRefresh;

  /// No description provided for @bgmLibraryNoImport.
  ///
  /// In zh, this message translates to:
  /// **'没有导入新曲目'**
  String get bgmLibraryNoImport;

  /// No description provided for @bgmLibraryImportedCount.
  ///
  /// In zh, this message translates to:
  /// **'已导入 {count} 首本地音乐'**
  String bgmLibraryImportedCount(Object count);

  /// No description provided for @bgmLibraryPlayingSwitched.
  ///
  /// In zh, this message translates to:
  /// **'正在播放 {title}，已切换到播放器模式'**
  String bgmLibraryPlayingSwitched(Object title);

  /// No description provided for @bgmLibraryRemoved.
  ///
  /// In zh, this message translates to:
  /// **'已移除 {title}'**
  String bgmLibraryRemoved(Object title);

  /// No description provided for @bgmLibraryEmptyFilter.
  ///
  /// In zh, this message translates to:
  /// **'当前筛选下没有曲目，可以尝试切换筛选或导入本地音乐。'**
  String get bgmLibraryEmptyFilter;

  /// No description provided for @bgmLibraryNotPlaying.
  ///
  /// In zh, this message translates to:
  /// **'当前未播放'**
  String get bgmLibraryNotPlaying;

  /// No description provided for @bgmLibraryWaitingPlay.
  ///
  /// In zh, this message translates to:
  /// **'等待播放中'**
  String get bgmLibraryWaitingPlay;

  /// No description provided for @bgmLibraryBrowseHint.
  ///
  /// In zh, this message translates to:
  /// **'你可以在这里直接点播曲库里的任意曲目'**
  String get bgmLibraryBrowseHint;

  /// No description provided for @bgmLibraryNowPlaying.
  ///
  /// In zh, this message translates to:
  /// **'当前播放'**
  String get bgmLibraryNowPlaying;

  /// No description provided for @bgmLibraryPlayerMode.
  ///
  /// In zh, this message translates to:
  /// **'播放器模式'**
  String get bgmLibraryPlayerMode;

  /// No description provided for @bgmLibraryPlayerModeDesc.
  ///
  /// In zh, this message translates to:
  /// **'播放器模式下音乐不会因页面跳转而被打断，适合把 Sparkle 当成舒缓音乐播放器来用。'**
  String get bgmLibraryPlayerModeDesc;

  /// No description provided for @bgmLibraryEnableBgm.
  ///
  /// In zh, this message translates to:
  /// **'启用背景音乐'**
  String get bgmLibraryEnableBgm;

  /// No description provided for @bgmLibraryDisableHint.
  ///
  /// In zh, this message translates to:
  /// **'关闭后播放器页也不会继续播放背景音乐'**
  String get bgmLibraryDisableHint;

  /// No description provided for @bgmLibraryQuickStrategy.
  ///
  /// In zh, this message translates to:
  /// **'快速策略调节'**
  String get bgmLibraryQuickStrategy;

  /// No description provided for @bgmLibraryQuickStrategyDesc.
  ///
  /// In zh, this message translates to:
  /// **'这里保留最常用的调节项，完整细项仍然可以在设置页里继续调整。'**
  String get bgmLibraryQuickStrategyDesc;

  /// No description provided for @bgmLibraryStyleOrientation.
  ///
  /// In zh, this message translates to:
  /// **'风格取向'**
  String get bgmLibraryStyleOrientation;

  /// No description provided for @bgmLibraryIntensityLabel.
  ///
  /// In zh, this message translates to:
  /// **'氛围强度'**
  String get bgmLibraryIntensityLabel;

  /// No description provided for @bgmLibraryVarietyLabel.
  ///
  /// In zh, this message translates to:
  /// **'轮换节奏'**
  String get bgmLibraryVarietyLabel;

  /// No description provided for @bgmLibraryStats.
  ///
  /// In zh, this message translates to:
  /// **'曲库状态'**
  String get bgmLibraryStats;

  /// No description provided for @bgmLibraryTotalTracks.
  ///
  /// In zh, this message translates to:
  /// **'总曲目'**
  String get bgmLibraryTotalTracks;

  /// No description provided for @bgmLibraryCurated.
  ///
  /// In zh, this message translates to:
  /// **'精选曲库'**
  String get bgmLibraryCurated;

  /// No description provided for @bgmLibraryImportedLabel.
  ///
  /// In zh, this message translates to:
  /// **'本地导入'**
  String get bgmLibraryImportedLabel;

  /// No description provided for @bgmLibraryBundled.
  ///
  /// In zh, this message translates to:
  /// **'系统兜底'**
  String get bgmLibraryBundled;

  /// No description provided for @bgmLibraryImportDir.
  ///
  /// In zh, this message translates to:
  /// **'本地导入目录：{path}'**
  String bgmLibraryImportDir(Object path);

  /// No description provided for @bgmLibraryCacheDir.
  ///
  /// In zh, this message translates to:
  /// **'下载缓存目录：{path}'**
  String bgmLibraryCacheDir(Object path);

  /// No description provided for @bgmLibraryDirReadyNote.
  ///
  /// In zh, this message translates to:
  /// **'这两个目录已经准备好，后续可以直接接“默认只打包少量曲目，其余从服务器下载到本地”的轻量化方案。'**
  String get bgmLibraryDirReadyNote;

  /// No description provided for @bgmLibraryImportManage.
  ///
  /// In zh, this message translates to:
  /// **'导入与管理'**
  String get bgmLibraryImportManage;

  /// No description provided for @bgmLibraryImportManageDesc.
  ///
  /// In zh, this message translates to:
  /// **'你可以把自己的舒缓音乐直接导入进来。点播任意曲目时，系统会自动切换到播放器模式，后续跳页也不会中断。'**
  String get bgmLibraryImportManageDesc;

  /// No description provided for @bgmLibraryImportLocal.
  ///
  /// In zh, this message translates to:
  /// **'导入本地歌曲'**
  String get bgmLibraryImportLocal;

  /// No description provided for @bgmLibrarySearchHint.
  ///
  /// In zh, this message translates to:
  /// **'搜索曲目、专辑或场景标签'**
  String get bgmLibrarySearchHint;

  /// No description provided for @bgmLibraryFilterAll.
  ///
  /// In zh, this message translates to:
  /// **'全部'**
  String get bgmLibraryFilterAll;

  /// No description provided for @bgmLibraryPlaying.
  ///
  /// In zh, this message translates to:
  /// **'播放中'**
  String get bgmLibraryPlaying;

  /// No description provided for @bgmLibraryPlay.
  ///
  /// In zh, this message translates to:
  /// **'播放'**
  String get bgmLibraryPlay;

  /// No description provided for @bgmLibraryRemove.
  ///
  /// In zh, this message translates to:
  /// **'移除'**
  String get bgmLibraryRemove;

  /// No description provided for @bgmLibraryTags.
  ///
  /// In zh, this message translates to:
  /// **'标签'**
  String get bgmLibraryTags;

  /// No description provided for @bgmLibraryStyle.
  ///
  /// In zh, this message translates to:
  /// **'风格'**
  String get bgmLibraryStyle;

  /// No description provided for @bgmLibraryEnergy.
  ///
  /// In zh, this message translates to:
  /// **'能量'**
  String get bgmLibraryEnergy;

  /// No description provided for @bgmLibraryDensity.
  ///
  /// In zh, this message translates to:
  /// **'密度'**
  String get bgmLibraryDensity;

  /// No description provided for @bgmLibraryModeAdaptive.
  ///
  /// In zh, this message translates to:
  /// **'跟随页面'**
  String get bgmLibraryModeAdaptive;

  /// No description provided for @bgmLibraryModeContinuous.
  ///
  /// In zh, this message translates to:
  /// **'播放器模式'**
  String get bgmLibraryModeContinuous;

  /// No description provided for @bgmLibraryModeFocusOnly.
  ///
  /// In zh, this message translates to:
  /// **'仅专注'**
  String get bgmLibraryModeFocusOnly;

  /// No description provided for @bgmLibraryModeSilent.
  ///
  /// In zh, this message translates to:
  /// **'静音'**
  String get bgmLibraryModeSilent;

  /// No description provided for @bgmLibraryPaletteAdaptive.
  ///
  /// In zh, this message translates to:
  /// **'自适应'**
  String get bgmLibraryPaletteAdaptive;

  /// No description provided for @bgmLibraryPaletteClassical.
  ///
  /// In zh, this message translates to:
  /// **'精选古典'**
  String get bgmLibraryPaletteClassical;

  /// No description provided for @bgmLibraryPalettePiano.
  ///
  /// In zh, this message translates to:
  /// **'钢琴优先'**
  String get bgmLibraryPalettePiano;

  /// No description provided for @bgmLibraryPaletteAiry.
  ///
  /// In zh, this message translates to:
  /// **'空灵氛围'**
  String get bgmLibraryPaletteAiry;

  /// No description provided for @bgmLibraryPaletteWarm.
  ///
  /// In zh, this message translates to:
  /// **'温暖轻快'**
  String get bgmLibraryPaletteWarm;

  /// No description provided for @bgmLibraryIntensityGentle.
  ///
  /// In zh, this message translates to:
  /// **'柔和'**
  String get bgmLibraryIntensityGentle;

  /// No description provided for @bgmLibraryIntensityBalanced.
  ///
  /// In zh, this message translates to:
  /// **'平衡'**
  String get bgmLibraryIntensityBalanced;

  /// No description provided for @bgmLibraryIntensityLush.
  ///
  /// In zh, this message translates to:
  /// **'丰盈'**
  String get bgmLibraryIntensityLush;

  /// No description provided for @bgmLibraryVarietySteady.
  ///
  /// In zh, this message translates to:
  /// **'稳定'**
  String get bgmLibraryVarietySteady;

  /// No description provided for @bgmLibraryVarietyBalanced.
  ///
  /// In zh, this message translates to:
  /// **'均衡'**
  String get bgmLibraryVarietyBalanced;

  /// No description provided for @bgmLibraryVarietyDynamic.
  ///
  /// In zh, this message translates to:
  /// **'灵动'**
  String get bgmLibraryVarietyDynamic;

  /// No description provided for @bgmLibrarySourceCurated.
  ///
  /// In zh, this message translates to:
  /// **'精选曲库'**
  String get bgmLibrarySourceCurated;

  /// No description provided for @bgmLibrarySourceImported.
  ///
  /// In zh, this message translates to:
  /// **'本地导入'**
  String get bgmLibrarySourceImported;

  /// No description provided for @bgmLibrarySourceBundled.
  ///
  /// In zh, this message translates to:
  /// **'系统兜底'**
  String get bgmLibrarySourceBundled;

  /// No description provided for @galaxyDraftReviewScreenTitle.
  ///
  /// In zh, this message translates to:
  /// **'审核知识星'**
  String get galaxyDraftReviewScreenTitle;

  /// No description provided for @galaxyDraftReviewPromptTitle.
  ///
  /// In zh, this message translates to:
  /// **'我们从 {documentName} 里找到了 {count} 颗知识星，要现在看看吗？'**
  String galaxyDraftReviewPromptTitle(Object count, Object documentName);

  /// No description provided for @galaxyDraftReviewPromptBody.
  ///
  /// In zh, this message translates to:
  /// **'你的星图该由你亲手确认。你可以逐个通过、跳过、合并，或者先改名再收下。'**
  String get galaxyDraftReviewPromptBody;

  /// No description provided for @galaxyDraftReviewNow.
  ///
  /// In zh, this message translates to:
  /// **'现在审核'**
  String get galaxyDraftReviewNow;

  /// No description provided for @galaxyDraftReviewLater.
  ///
  /// In zh, this message translates to:
  /// **'稍后再看'**
  String get galaxyDraftReviewLater;

  /// No description provided for @galaxyDraftPendingIndicator.
  ///
  /// In zh, this message translates to:
  /// **'{batchCount} 份待审核 · {draftCount} 颗星'**
  String galaxyDraftPendingIndicator(Object batchCount, Object draftCount);

  /// No description provided for @galaxyDraftReviewProgress.
  ///
  /// In zh, this message translates to:
  /// **'第 {current} / {total} 颗'**
  String galaxyDraftReviewProgress(Object current, Object total);

  /// No description provided for @galaxyDraftCompletionReady.
  ///
  /// In zh, this message translates to:
  /// **'准备把它们送进你的星图'**
  String get galaxyDraftCompletionReady;

  /// No description provided for @galaxyDraftLongPressHint.
  ///
  /// In zh, this message translates to:
  /// **'右滑通过，左滑跳过，长按还能先改一下名字或描述。'**
  String get galaxyDraftLongPressHint;

  /// No description provided for @galaxyDraftLongPressShort.
  ///
  /// In zh, this message translates to:
  /// **'长按可编辑'**
  String get galaxyDraftLongPressShort;

  /// No description provided for @galaxyDraftApprove.
  ///
  /// In zh, this message translates to:
  /// **'通过'**
  String get galaxyDraftApprove;

  /// No description provided for @galaxyDraftSkip.
  ///
  /// In zh, this message translates to:
  /// **'跳过'**
  String get galaxyDraftSkip;

  /// No description provided for @galaxyDraftMerge.
  ///
  /// In zh, this message translates to:
  /// **'合并'**
  String get galaxyDraftMerge;

  /// No description provided for @galaxyDraftExcerpts.
  ///
  /// In zh, this message translates to:
  /// **'这颗星里装着什么'**
  String get galaxyDraftExcerpts;

  /// No description provided for @galaxyDraftSimilarityLabel.
  ///
  /// In zh, this message translates to:
  /// **'与已有节点相似：{nodeName}（{percent}%）'**
  String galaxyDraftSimilarityLabel(Object nodeName, Object percent);

  /// No description provided for @galaxyDraftEditTitle.
  ///
  /// In zh, this message translates to:
  /// **'调整这颗知识星'**
  String get galaxyDraftEditTitle;

  /// No description provided for @galaxyDraftNameLabel.
  ///
  /// In zh, this message translates to:
  /// **'节点名称'**
  String get galaxyDraftNameLabel;

  /// No description provided for @galaxyDraftDescriptionLabel.
  ///
  /// In zh, this message translates to:
  /// **'节点描述'**
  String get galaxyDraftDescriptionLabel;

  /// No description provided for @galaxyDraftEditSave.
  ///
  /// In zh, this message translates to:
  /// **'保存修改'**
  String get galaxyDraftEditSave;

  /// No description provided for @galaxyDraftReviewEmptyTitle.
  ///
  /// In zh, this message translates to:
  /// **'现在没有待确认的知识星'**
  String get galaxyDraftReviewEmptyTitle;

  /// No description provided for @galaxyDraftReviewEmptyBody.
  ///
  /// In zh, this message translates to:
  /// **'等文档处理完成后，新的知识草稿会先落到这里，等你点头再进入星图。'**
  String get galaxyDraftReviewEmptyBody;

  /// No description provided for @galaxyDraftBackToGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'回到星图'**
  String get galaxyDraftBackToGalaxy;

  /// No description provided for @galaxyDraftCompletionTitle.
  ///
  /// In zh, this message translates to:
  /// **'已确认 {accepted} / {total} 颗知识星'**
  String galaxyDraftCompletionTitle(Object accepted, Object total);

  /// No description provided for @galaxyDraftCompletionBody.
  ///
  /// In zh, this message translates to:
  /// **'{documentName} 里的这些知识星，已经准备好飞进你的星图。'**
  String galaxyDraftCompletionBody(Object documentName);

  /// No description provided for @galaxyDraftCompletionNothingAdded.
  ///
  /// In zh, this message translates to:
  /// **'这批草稿先放一放也没关系，之后随时还能回来继续看。'**
  String get galaxyDraftCompletionNothingAdded;

  /// No description provided for @galaxyDraftCompletionSummary.
  ///
  /// In zh, this message translates to:
  /// **'{accepted} / {total} 颗知识星已加入你的星图！'**
  String galaxyDraftCompletionSummary(Object accepted, Object total);

  /// No description provided for @galaxyUploadFabLabel.
  ///
  /// In zh, this message translates to:
  /// **'添加学习资料'**
  String get galaxyUploadFabLabel;

  /// No description provided for @galaxyUploadDocumentHere.
  ///
  /// In zh, this message translates to:
  /// **'在这里上传文档'**
  String get galaxyUploadDocumentHere;

  /// No description provided for @galaxyNodeAddMaterial.
  ///
  /// In zh, this message translates to:
  /// **'将资料添加到这个节点'**
  String get galaxyNodeAddMaterial;

  /// No description provided for @galaxyUploadTargetGalaxyCore.
  ///
  /// In zh, this message translates to:
  /// **'银河核心'**
  String get galaxyUploadTargetGalaxyCore;

  /// No description provided for @galaxyUploadTargetSelectedConstellation.
  ///
  /// In zh, this message translates to:
  /// **'这片星域'**
  String get galaxyUploadTargetSelectedConstellation;

  /// No description provided for @galaxyUploadAlreadyInProgress.
  ///
  /// In zh, this message translates to:
  /// **'已经有一份学习资料正在飞向你的星图。'**
  String get galaxyUploadAlreadyInProgress;

  /// No description provided for @galaxyUploadStatusUploading.
  ///
  /// In zh, this message translates to:
  /// **'上传中...'**
  String get galaxyUploadStatusUploading;

  /// No description provided for @galaxyUploadStatusQueued.
  ///
  /// In zh, this message translates to:
  /// **'上传完成，正在进入轨道...'**
  String get galaxyUploadStatusQueued;

  /// No description provided for @galaxyUploadStatusExtracting.
  ///
  /// In zh, this message translates to:
  /// **'提取内容中...'**
  String get galaxyUploadStatusExtracting;

  /// No description provided for @galaxyUploadStatusFindingKnowledge.
  ///
  /// In zh, this message translates to:
  /// **'寻找知识中...'**
  String get galaxyUploadStatusFindingKnowledge;

  /// No description provided for @galaxyUploadStatusBuildingNodes.
  ///
  /// In zh, this message translates to:
  /// **'编织新星中...'**
  String get galaxyUploadStatusBuildingNodes;

  /// No description provided for @galaxyUploadSuccessTitle.
  ///
  /// In zh, this message translates to:
  /// **'处理完成！'**
  String get galaxyUploadSuccessTitle;

  /// No description provided for @galaxyUploadSuccessBody.
  ///
  /// In zh, this message translates to:
  /// **'处理完成！共发现 {count} 个知识概念。'**
  String galaxyUploadSuccessBody(Object count);

  /// No description provided for @galaxyUploadSuccessChip.
  ///
  /// In zh, this message translates to:
  /// **'发现了 {count} 个概念'**
  String galaxyUploadSuccessChip(Object count);

  /// No description provided for @galaxyUploadFailedTitle.
  ///
  /// In zh, this message translates to:
  /// **'这颗星还没落稳'**
  String get galaxyUploadFailedTitle;

  /// No description provided for @galaxyUploadFailedBody.
  ///
  /// In zh, this message translates to:
  /// **'文档在落入星图前滑了出去，准备好时再试一次就好。'**
  String get galaxyUploadFailedBody;

  /// No description provided for @galaxyUploadRetry.
  ///
  /// In zh, this message translates to:
  /// **'重新上传'**
  String get galaxyUploadRetry;

  /// No description provided for @galaxyUploadHeadingTo.
  ///
  /// In zh, this message translates to:
  /// **'正飞向 {target}'**
  String galaxyUploadHeadingTo(Object target);

  /// No description provided for @galaxyUploadStepUpload.
  ///
  /// In zh, this message translates to:
  /// **'上传'**
  String get galaxyUploadStepUpload;

  /// No description provided for @galaxyUploadStepExtract.
  ///
  /// In zh, this message translates to:
  /// **'提取'**
  String get galaxyUploadStepExtract;

  /// No description provided for @galaxyUploadStepFind.
  ///
  /// In zh, this message translates to:
  /// **'寻知'**
  String get galaxyUploadStepFind;

  /// No description provided for @galaxyUploadStepComplete.
  ///
  /// In zh, this message translates to:
  /// **'完成'**
  String get galaxyUploadStepComplete;

  /// No description provided for @executionEngineTitle.
  ///
  /// In zh, this message translates to:
  /// **'AI执行引擎'**
  String get executionEngineTitle;

  /// No description provided for @executionConnectionSuccess.
  ///
  /// In zh, this message translates to:
  /// **'连接成功'**
  String get executionConnectionSuccess;

  /// No description provided for @executionConnectionFailure.
  ///
  /// In zh, this message translates to:
  /// **'连接失败'**
  String get executionConnectionFailure;

  /// No description provided for @executionConfigSavedConnected.
  ///
  /// In zh, this message translates to:
  /// **'配置已保存并连接成功'**
  String get executionConfigSavedConnected;

  /// No description provided for @executionConfigSavedUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'配置已保存，但当前引擎不可达'**
  String get executionConfigSavedUnavailable;

  /// No description provided for @executionResultPreview.
  ///
  /// In zh, this message translates to:
  /// **'结果预览'**
  String get executionResultPreview;

  /// No description provided for @executionReplay.
  ///
  /// In zh, this message translates to:
  /// **'执行回放'**
  String get executionReplay;

  /// No description provided for @executionSelfVerification.
  ///
  /// In zh, this message translates to:
  /// **'自验证'**
  String get executionSelfVerification;

  /// No description provided for @executionSelfVerificationHint.
  ///
  /// In zh, this message translates to:
  /// **'自验证提示'**
  String get executionSelfVerificationHint;

  /// No description provided for @executionResultComparison.
  ///
  /// In zh, this message translates to:
  /// **'结果对比'**
  String get executionResultComparison;

  /// No description provided for @executionAdoptResult.
  ///
  /// In zh, this message translates to:
  /// **'采纳结果'**
  String get executionAdoptResult;

  /// No description provided for @executionRejectResult.
  ///
  /// In zh, this message translates to:
  /// **'退回修改'**
  String get executionRejectResult;

  /// No description provided for @executionViewDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看详情'**
  String get executionViewDetails;

  /// No description provided for @executionCollapseDetails.
  ///
  /// In zh, this message translates to:
  /// **'收起详情'**
  String get executionCollapseDetails;

  /// No description provided for @executionQueueAction.
  ///
  /// In zh, this message translates to:
  /// **'加入等待队列'**
  String get executionQueueAction;

  /// No description provided for @executionConnectEngine.
  ///
  /// In zh, this message translates to:
  /// **'先连接 AI执行引擎'**
  String get executionConnectEngine;

  /// No description provided for @executionEngineOffline.
  ///
  /// In zh, this message translates to:
  /// **'AI执行引擎当前离线'**
  String get executionEngineOffline;

  /// No description provided for @executionEngineNotConnected.
  ///
  /// In zh, this message translates to:
  /// **'AI执行引擎尚未连接'**
  String get executionEngineNotConnected;

  /// No description provided for @executionOfflineQueueTitle.
  ///
  /// In zh, this message translates to:
  /// **'离线等待队列'**
  String get executionOfflineQueueTitle;

  /// No description provided for @executionAboutEngineTitle.
  ///
  /// In zh, this message translates to:
  /// **'什么是AI执行引擎？'**
  String get executionAboutEngineTitle;

  /// No description provided for @executionAboutEngineBody.
  ///
  /// In zh, this message translates to:
  /// **'AI执行引擎（OpenClaw）可以自动完成网页调研、文档整理等任务。你可以在自己的电脑上运行 OpenClaw，然后在这里连接它。'**
  String get executionAboutEngineBody;

  /// No description provided for @taskCopyAiPrompt.
  ///
  /// In zh, this message translates to:
  /// **'复制AI提示词'**
  String get taskCopyAiPrompt;

  /// No description provided for @taskObjective.
  ///
  /// In zh, this message translates to:
  /// **'目标'**
  String get taskObjective;

  /// No description provided for @taskEstimatedTime.
  ///
  /// In zh, this message translates to:
  /// **'预计时间'**
  String get taskEstimatedTime;

  /// No description provided for @taskCompletionCriteria.
  ///
  /// In zh, this message translates to:
  /// **'完成标准'**
  String get taskCompletionCriteria;

  /// No description provided for @taskSteps.
  ///
  /// In zh, this message translates to:
  /// **'步骤'**
  String get taskSteps;

  /// No description provided for @taskKeyPoints.
  ///
  /// In zh, this message translates to:
  /// **'关键点'**
  String get taskKeyPoints;

  /// No description provided for @taskStartFocus.
  ///
  /// In zh, this message translates to:
  /// **'开始专注'**
  String get taskStartFocus;

  /// No description provided for @taskOpenAiAssistant.
  ///
  /// In zh, this message translates to:
  /// **'打开AI助手'**
  String get taskOpenAiAssistant;

  /// No description provided for @taskAiGenerate.
  ///
  /// In zh, this message translates to:
  /// **'AI 生成'**
  String get taskAiGenerate;

  /// No description provided for @knowledgeMasteryLevelMastered.
  ///
  /// In zh, this message translates to:
  /// **'已掌握'**
  String get knowledgeMasteryLevelMastered;

  /// No description provided for @knowledgeMasteryLevelPracticing.
  ///
  /// In zh, this message translates to:
  /// **'熟练中'**
  String get knowledgeMasteryLevelPracticing;

  /// No description provided for @knowledgeMasteryLevelBeginner.
  ///
  /// In zh, this message translates to:
  /// **'初涉'**
  String get knowledgeMasteryLevelBeginner;

  /// No description provided for @knowledgeMasteryLevelUntouched.
  ///
  /// In zh, this message translates to:
  /// **'未学习'**
  String get knowledgeMasteryLevelUntouched;

  /// No description provided for @executionStatusDraft.
  ///
  /// In zh, this message translates to:
  /// **'待准备'**
  String get executionStatusDraft;

  /// No description provided for @executionStatusReady.
  ///
  /// In zh, this message translates to:
  /// **'准备完成'**
  String get executionStatusReady;

  /// No description provided for @executionStatusQueued.
  ///
  /// In zh, this message translates to:
  /// **'排队中'**
  String get executionStatusQueued;

  /// No description provided for @executionStatusDispatched.
  ///
  /// In zh, this message translates to:
  /// **'已发送'**
  String get executionStatusDispatched;

  /// No description provided for @executionStatusRunning.
  ///
  /// In zh, this message translates to:
  /// **'执行中'**
  String get executionStatusRunning;

  /// No description provided for @executionStatusWaitingApproval.
  ///
  /// In zh, this message translates to:
  /// **'等待确认'**
  String get executionStatusWaitingApproval;

  /// No description provided for @executionStatusSucceeded.
  ///
  /// In zh, this message translates to:
  /// **'执行成功'**
  String get executionStatusSucceeded;

  /// No description provided for @executionStatusPartial.
  ///
  /// In zh, this message translates to:
  /// **'部分完成'**
  String get executionStatusPartial;

  /// No description provided for @executionStatusFailed.
  ///
  /// In zh, this message translates to:
  /// **'执行失败'**
  String get executionStatusFailed;

  /// No description provided for @executionStatusCanceled.
  ///
  /// In zh, this message translates to:
  /// **'已取消'**
  String get executionStatusCanceled;

  /// No description provided for @executionStatusTimedOut.
  ///
  /// In zh, this message translates to:
  /// **'执行超时'**
  String get executionStatusTimedOut;

  /// No description provided for @executionStatusHandedBack.
  ///
  /// In zh, this message translates to:
  /// **'已交还'**
  String get executionStatusHandedBack;

  /// No description provided for @executionStatusUnknown.
  ///
  /// In zh, this message translates to:
  /// **'状态未知'**
  String get executionStatusUnknown;

  /// No description provided for @executionTrustRaw.
  ///
  /// In zh, this message translates to:
  /// **'原始结果'**
  String get executionTrustRaw;

  /// No description provided for @executionTrustValidated.
  ///
  /// In zh, this message translates to:
  /// **'已校验'**
  String get executionTrustValidated;

  /// No description provided for @executionTrustTrusted.
  ///
  /// In zh, this message translates to:
  /// **'可信结果'**
  String get executionTrustTrusted;

  /// No description provided for @executionTrustUnknown.
  ///
  /// In zh, this message translates to:
  /// **'待评估'**
  String get executionTrustUnknown;

  /// No description provided for @nextActionQuickReviewTitle.
  ///
  /// In zh, this message translates to:
  /// **'快速回顾'**
  String get nextActionQuickReviewTitle;

  /// No description provided for @nextActionQuickReviewDescription.
  ///
  /// In zh, this message translates to:
  /// **'回顾刚才的核心要点'**
  String get nextActionQuickReviewDescription;

  /// No description provided for @nextActionLightExpandTitle.
  ///
  /// In zh, this message translates to:
  /// **'拓展学习'**
  String get nextActionLightExpandTitle;

  /// No description provided for @nextActionLightExpandDescription.
  ///
  /// In zh, this message translates to:
  /// **'了解相关知识点'**
  String get nextActionLightExpandDescription;

  /// No description provided for @nextActionPracticeApplyTitle.
  ///
  /// In zh, this message translates to:
  /// **'实践应用'**
  String get nextActionPracticeApplyTitle;

  /// No description provided for @nextActionPracticeApplyDescription.
  ///
  /// In zh, this message translates to:
  /// **'应用所学知识'**
  String get nextActionPracticeApplyDescription;

  /// No description provided for @nextActionRestBreakTitle.
  ///
  /// In zh, this message translates to:
  /// **'休息一下'**
  String get nextActionRestBreakTitle;

  /// No description provided for @nextActionRestBreakDescription.
  ///
  /// In zh, this message translates to:
  /// **'适当休息，保持状态'**
  String get nextActionRestBreakDescription;

  /// No description provided for @nextActionContinuePlanTitle.
  ///
  /// In zh, this message translates to:
  /// **'继续计划'**
  String get nextActionContinuePlanTitle;

  /// No description provided for @nextActionContinuePlanDescription.
  ///
  /// In zh, this message translates to:
  /// **'继续按计划学习'**
  String get nextActionContinuePlanDescription;

  /// No description provided for @knowledgeRelationPrerequisite.
  ///
  /// In zh, this message translates to:
  /// **'前置知识'**
  String get knowledgeRelationPrerequisite;

  /// No description provided for @knowledgeRelationRelated.
  ///
  /// In zh, this message translates to:
  /// **'相关知识'**
  String get knowledgeRelationRelated;

  /// No description provided for @knowledgeRelationApplication.
  ///
  /// In zh, this message translates to:
  /// **'应用'**
  String get knowledgeRelationApplication;

  /// No description provided for @knowledgeRelationComposition.
  ///
  /// In zh, this message translates to:
  /// **'组成部分'**
  String get knowledgeRelationComposition;

  /// No description provided for @knowledgeRelationEvolution.
  ///
  /// In zh, this message translates to:
  /// **'演进'**
  String get knowledgeRelationEvolution;

  /// No description provided for @knowledgeRelationDefault.
  ///
  /// In zh, this message translates to:
  /// **'关联'**
  String get knowledgeRelationDefault;

  /// No description provided for @knowledgeMasteryLevelLocked.
  ///
  /// In zh, this message translates to:
  /// **'未解锁'**
  String get knowledgeMasteryLevelLocked;

  /// No description provided for @knowledgeMasteryLevelBrilliant.
  ///
  /// In zh, this message translates to:
  /// **'璀璨'**
  String get knowledgeMasteryLevelBrilliant;

  /// No description provided for @knowledgeMasteryLevelShining.
  ///
  /// In zh, this message translates to:
  /// **'闪耀'**
  String get knowledgeMasteryLevelShining;

  /// No description provided for @knowledgeMasteryLevelGlimmer.
  ///
  /// In zh, this message translates to:
  /// **'微光'**
  String get knowledgeMasteryLevelGlimmer;

  /// No description provided for @knowledgeMasteryLevelUnlit.
  ///
  /// In zh, this message translates to:
  /// **'未点亮'**
  String get knowledgeMasteryLevelUnlit;

  /// No description provided for @interventionPhaseForethought.
  ///
  /// In zh, this message translates to:
  /// **'规划中'**
  String get interventionPhaseForethought;

  /// No description provided for @interventionPhasePerformance.
  ///
  /// In zh, this message translates to:
  /// **'执行中'**
  String get interventionPhasePerformance;

  /// No description provided for @interventionPhaseSelfReflection.
  ///
  /// In zh, this message translates to:
  /// **'复盘中'**
  String get interventionPhaseSelfReflection;

  /// No description provided for @stuckHelpTitle.
  ///
  /// In zh, this message translates to:
  /// **'别担心，我们来看看卡在哪里'**
  String get stuckHelpTitle;

  /// No description provided for @stuckHelpAskAi.
  ///
  /// In zh, this message translates to:
  /// **'要不要让AI来看看？'**
  String get stuckHelpAskAi;

  /// No description provided for @stuckHelpChatWithSparkle.
  ///
  /// In zh, this message translates to:
  /// **'和Sparkle聊聊这个问题'**
  String get stuckHelpChatWithSparkle;

  /// No description provided for @stuckHelpContinue.
  ///
  /// In zh, this message translates to:
  /// **'好了，继续'**
  String get stuckHelpContinue;

  /// No description provided for @stuckHelpSuggestion1.
  ///
  /// In zh, this message translates to:
  /// **'把卡住的具体位置写下来'**
  String get stuckHelpSuggestion1;

  /// No description provided for @stuckHelpSuggestion2.
  ///
  /// In zh, this message translates to:
  /// **'换一个更小的子问题'**
  String get stuckHelpSuggestion2;

  /// No description provided for @stuckHelpSuggestion3.
  ///
  /// In zh, this message translates to:
  /// **'先完成你确实会的部分'**
  String get stuckHelpSuggestion3;

  /// No description provided for @stuckHelpSuggestion4.
  ///
  /// In zh, this message translates to:
  /// **'给自己限时5分钟'**
  String get stuckHelpSuggestion4;

  /// No description provided for @stuckHelpSuggestion5.
  ///
  /// In zh, this message translates to:
  /// **'标记这个点，继续其他部分'**
  String get stuckHelpSuggestion5;

  /// No description provided for @stuckHelpAuroraSteps.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 两步帮扶'**
  String get stuckHelpAuroraSteps;

  /// No description provided for @stuckHelpFallbackOrder.
  ///
  /// In zh, this message translates to:
  /// **'卡住时按这个顺序救火'**
  String get stuckHelpFallbackOrder;

  /// No description provided for @stuckHelpWhatToDo.
  ///
  /// In zh, this message translates to:
  /// **'具体该怎么做'**
  String get stuckHelpWhatToDo;

  /// No description provided for @stuckHelpDiagnose.
  ///
  /// In zh, this message translates to:
  /// **'诊断问题'**
  String get stuckHelpDiagnose;

  /// No description provided for @stuckHelpFix.
  ///
  /// In zh, this message translates to:
  /// **'精准修复'**
  String get stuckHelpFix;

  /// No description provided for @taskQuickActionSnoozed.
  ///
  /// In zh, this message translates to:
  /// **'已推迟到明天，今天轻一点。'**
  String get taskQuickActionSnoozed;

  /// No description provided for @taskQuickActionTooHard.
  ///
  /// In zh, this message translates to:
  /// **'拆好了，先做第一小步。'**
  String get taskQuickActionTooHard;

  /// No description provided for @taskQuickActionSkipped.
  ///
  /// In zh, this message translates to:
  /// **'已跳过，这张卡先不打扰你。'**
  String get taskQuickActionSkipped;

  /// No description provided for @taskQuickActionAdjusted.
  ///
  /// In zh, this message translates to:
  /// **'已经帮你调整好了。'**
  String get taskQuickActionAdjusted;

  /// No description provided for @taskQuickActionSnoozing.
  ///
  /// In zh, this message translates to:
  /// **'好，我先把它挪到明天。'**
  String get taskQuickActionSnoozing;

  /// No description provided for @taskQuickActionSimplifying.
  ///
  /// In zh, this message translates to:
  /// **'我来把这张卡拆小一点。'**
  String get taskQuickActionSimplifying;

  /// No description provided for @taskQuickActionSkipping.
  ///
  /// In zh, this message translates to:
  /// **'收到，我先把它从今天拿开。'**
  String get taskQuickActionSkipping;

  /// No description provided for @executionResultNoText.
  ///
  /// In zh, this message translates to:
  /// **'暂无文本结果。'**
  String get executionResultNoText;

  /// No description provided for @executionResultNoStructured.
  ///
  /// In zh, this message translates to:
  /// **'暂无结构化结果字段。'**
  String get executionResultNoStructured;

  /// No description provided for @executionResultNoCode.
  ///
  /// In zh, this message translates to:
  /// **'暂无代码结果。'**
  String get executionResultNoCode;

  /// No description provided for @executionResultNoLinks.
  ///
  /// In zh, this message translates to:
  /// **'暂无链接结果。'**
  String get executionResultNoLinks;

  /// No description provided for @executionResultArtifacts.
  ///
  /// In zh, this message translates to:
  /// **'附件产物'**
  String get executionResultArtifacts;

  /// No description provided for @executionResultMoreFields.
  ///
  /// In zh, this message translates to:
  /// **'还有 {count} 个字段'**
  String executionResultMoreFields(Object count);

  /// No description provided for @executionResultNoPreview.
  ///
  /// In zh, this message translates to:
  /// **'当前附件类型为 {type}，还没有更详细的预览内容。'**
  String executionResultNoPreview(Object type);

  /// No description provided for @executionResultLinkCopied.
  ///
  /// In zh, this message translates to:
  /// **'链接已复制'**
  String get executionResultLinkCopied;

  /// No description provided for @executionResultCopyLink.
  ///
  /// In zh, this message translates to:
  /// **'复制链接'**
  String get executionResultCopyLink;

  /// No description provided for @executionResultArtifactType.
  ///
  /// In zh, this message translates to:
  /// **'类型：{type}'**
  String executionResultArtifactType(Object type);

  /// No description provided for @executionResultArtifactFallback.
  ///
  /// In zh, this message translates to:
  /// **'附件'**
  String get executionResultArtifactFallback;

  /// No description provided for @onboardingVoiceInput.
  ///
  /// In zh, this message translates to:
  /// **'语音输入'**
  String get onboardingVoiceInput;

  /// No description provided for @onboardingVoiceInputEn.
  ///
  /// In zh, this message translates to:
  /// **'英语语音输入'**
  String get onboardingVoiceInputEn;

  /// No description provided for @onboardingVoiceInputDesc.
  ///
  /// In zh, this message translates to:
  /// **'开启麦克风权限，支持语音指令与听写输入'**
  String get onboardingVoiceInputDesc;

  /// No description provided for @onboardingVoiceInputDescEn.
  ///
  /// In zh, this message translates to:
  /// **'开启英语语音输入，支持语音指令与听写'**
  String get onboardingVoiceInputDescEn;

  /// No description provided for @onboardingPermissionEnable.
  ///
  /// In zh, this message translates to:
  /// **'启用'**
  String get onboardingPermissionEnable;

  /// No description provided for @onboardingPermissionEnabled.
  ///
  /// In zh, this message translates to:
  /// **'已启用'**
  String get onboardingPermissionEnabled;

  /// No description provided for @onboardingPermissionReady.
  ///
  /// In zh, this message translates to:
  /// **'就绪 — 已全部设置好'**
  String get onboardingPermissionReady;

  /// No description provided for @onboardingPermissionPending.
  ///
  /// In zh, this message translates to:
  /// **'尚未启用，启用后可使用语音功能。'**
  String get onboardingPermissionPending;

  /// No description provided for @onboardingPermissionWorking.
  ///
  /// In zh, this message translates to:
  /// **'请求中...'**
  String get onboardingPermissionWorking;

  /// No description provided for @homeNotificationUnreadMessages.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条未读消息'**
  String homeNotificationUnreadMessages(Object count);

  /// No description provided for @homeNotificationUnreadNotifications.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条未读通知'**
  String homeNotificationUnreadNotifications(Object count);

  /// No description provided for @splashSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'从第一秒开始，进入更聪明也更有温度的学习旅程。'**
  String get splashSubtitle;

  /// No description provided for @taskGuidePanelCollapse.
  ///
  /// In zh, this message translates to:
  /// **'收起指南'**
  String get taskGuidePanelCollapse;

  /// No description provided for @taskGuidePanelExpand.
  ///
  /// In zh, this message translates to:
  /// **'展开指南'**
  String get taskGuidePanelExpand;

  /// No description provided for @taskGuidePanelEstimatedTimeCustom.
  ///
  /// In zh, this message translates to:
  /// **'预估时间：按自己的节奏'**
  String get taskGuidePanelEstimatedTimeCustom;

  /// No description provided for @taskGuidePanelEstimatedTimeMinutes.
  ///
  /// In zh, this message translates to:
  /// **'预估时间：{minutes} 分钟'**
  String taskGuidePanelEstimatedTimeMinutes(Object minutes);

  /// No description provided for @taskGuidePanelTodayFocus.
  ///
  /// In zh, this message translates to:
  /// **'今日焦点'**
  String get taskGuidePanelTodayFocus;

  /// No description provided for @taskGuidePanelSteps.
  ///
  /// In zh, this message translates to:
  /// **'步骤'**
  String get taskGuidePanelSteps;

  /// No description provided for @taskGuidePanelKeyHints.
  ///
  /// In zh, this message translates to:
  /// **'关键提示'**
  String get taskGuidePanelKeyHints;

  /// No description provided for @taskGuidePanelCompletionCriteria.
  ///
  /// In zh, this message translates to:
  /// **'完成标准'**
  String get taskGuidePanelCompletionCriteria;

  /// No description provided for @taskGuidePanelTapToMark.
  ///
  /// In zh, this message translates to:
  /// **'点一下就能标记你已经完成的标准。'**
  String get taskGuidePanelTapToMark;

  /// No description provided for @taskGuidePanelCommonMistakes.
  ///
  /// In zh, this message translates to:
  /// **'常见陷阱'**
  String get taskGuidePanelCommonMistakes;

  /// No description provided for @taskGuidePanelNoDetailedGuide.
  ///
  /// In zh, this message translates to:
  /// **'这张卡还没有更细的指南，先从你能确定的一小步开始。'**
  String get taskGuidePanelNoDetailedGuide;

  /// No description provided for @taskGuidePanelFailSafeRule.
  ///
  /// In zh, this message translates to:
  /// **'失手时降压规则'**
  String get taskGuidePanelFailSafeRule;

  /// No description provided for @taskGuidePanelFailSafeRuleContent.
  ///
  /// In zh, this message translates to:
  /// **'失手规则：{rule}'**
  String taskGuidePanelFailSafeRuleContent(Object rule);

  /// No description provided for @taskGuidePanelAskAiTriggers.
  ///
  /// In zh, this message translates to:
  /// **'遇到这些情况时问 AI'**
  String get taskGuidePanelAskAiTriggers;

  /// No description provided for @taskGuidePanelStepInProgress.
  ///
  /// In zh, this message translates to:
  /// **'当前进行中'**
  String get taskGuidePanelStepInProgress;

  /// No description provided for @taskGuidePanelCompletedSteps.
  ///
  /// In zh, this message translates to:
  /// **'已完成 {completed}/{total}'**
  String taskGuidePanelCompletedSteps(Object completed, Object total);

  /// No description provided for @taskGuidePanelCompletedCriteria.
  ///
  /// In zh, this message translates to:
  /// **'{completed}/{total}'**
  String taskGuidePanelCompletedCriteria(Object completed, Object total);

  /// No description provided for @taskGuidePanelExpectedOutput.
  ///
  /// In zh, this message translates to:
  /// **'期望产出：{output}'**
  String taskGuidePanelExpectedOutput(Object output);

  /// No description provided for @taskGuidePanelFallbackLastStep.
  ///
  /// In zh, this message translates to:
  /// **'最后用 {output} 做一个最小检查。'**
  String taskGuidePanelFallbackLastStep(Object output);

  /// No description provided for @taskGuidePanelFallbackLastStepDefault.
  ///
  /// In zh, this message translates to:
  /// **'最后做一个最小检查，确认今天真的会了。'**
  String get taskGuidePanelFallbackLastStepDefault;

  /// No description provided for @taskGuidePanelFallbackSplitStep.
  ///
  /// In zh, this message translates to:
  /// **'把这一小步拆成你现在能立刻开始的版本。'**
  String get taskGuidePanelFallbackSplitStep;

  /// No description provided for @taskGuidePanelFallbackOutput1.
  ///
  /// In zh, this message translates to:
  /// **'留下这一步的起手框架或关键词。'**
  String get taskGuidePanelFallbackOutput1;

  /// No description provided for @taskGuidePanelFallbackOutput2.
  ///
  /// In zh, this message translates to:
  /// **'完成一次不看答案的独立输出。'**
  String get taskGuidePanelFallbackOutput2;

  /// No description provided for @taskGuidePanelFallbackOutput3.
  ///
  /// In zh, this message translates to:
  /// **'标出关键缺口，并补一句提醒。'**
  String get taskGuidePanelFallbackOutput3;

  /// No description provided for @taskGuidePanelFallbackOutputCheck.
  ///
  /// In zh, this message translates to:
  /// **'完成最小检查：{check}。'**
  String taskGuidePanelFallbackOutputCheck(Object check);

  /// No description provided for @taskGuidePanelFallbackOutputCheckDefault.
  ///
  /// In zh, this message translates to:
  /// **'完成最小检查，确认不是只看懂。'**
  String get taskGuidePanelFallbackOutputCheckDefault;

  /// No description provided for @reviewPlanHubTitle.
  ///
  /// In zh, this message translates to:
  /// **'复习计划中心'**
  String get reviewPlanHubTitle;

  /// No description provided for @reviewPlanHubTodayList.
  ///
  /// In zh, this message translates to:
  /// **'今日复习清单'**
  String get reviewPlanHubTodayList;

  /// No description provided for @reviewPlanHubNightlyReview.
  ///
  /// In zh, this message translates to:
  /// **'夜间回顾'**
  String get reviewPlanHubNightlyReview;

  /// No description provided for @reviewPlanHubNoActivePlan.
  ///
  /// In zh, this message translates to:
  /// **'还没有活跃计划'**
  String get reviewPlanHubNoActivePlan;

  /// No description provided for @reviewPlanHubStartToday.
  ///
  /// In zh, this message translates to:
  /// **'开始今日复习'**
  String get reviewPlanHubStartToday;

  /// No description provided for @reviewPlanHubOpenReview.
  ///
  /// In zh, this message translates to:
  /// **'打开复习页'**
  String get reviewPlanHubOpenReview;

  /// No description provided for @reviewPlanHubViewReview.
  ///
  /// In zh, this message translates to:
  /// **'查看复习页'**
  String get reviewPlanHubViewReview;

  /// No description provided for @reviewPlanHubViewTonight.
  ///
  /// In zh, this message translates to:
  /// **'查看今晚回顾'**
  String get reviewPlanHubViewTonight;

  /// No description provided for @reviewPlanHubCreatePlan.
  ///
  /// In zh, this message translates to:
  /// **'去创建计划'**
  String get reviewPlanHubCreatePlan;

  /// No description provided for @reviewPlanHubStartTodayReview.
  ///
  /// In zh, this message translates to:
  /// **'开始今天的复习'**
  String get reviewPlanHubStartTodayReview;

  /// No description provided for @reviewPlanHubHeroDescription.
  ///
  /// In zh, this message translates to:
  /// **'把错题复习、夜间回顾和计划任务放在同一个入口里管理。'**
  String get reviewPlanHubHeroDescription;

  /// No description provided for @reviewPlanHubHeroSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'这里不会替代原有复习页，而是把今天值得回看的东西先排好，再带你进入具体执行。'**
  String get reviewPlanHubHeroSubtitle;

  /// No description provided for @reviewPlanHubPlanIntegration.
  ///
  /// In zh, this message translates to:
  /// **'和长期/冲刺计划联动'**
  String get reviewPlanHubPlanIntegration;

  /// No description provided for @reviewPlanHubTodayPlanTasks.
  ///
  /// In zh, this message translates to:
  /// **'今天建议优先回看的计划任务'**
  String get reviewPlanHubTodayPlanTasks;

  /// No description provided for @reviewPlanHubNoDueErrors.
  ///
  /// In zh, this message translates to:
  /// **'今天没有到期错题，但仍然可以检查计划任务与夜间复盘。'**
  String get reviewPlanHubNoDueErrors;

  /// No description provided for @reviewPlanHubHasErrors.
  ///
  /// In zh, this message translates to:
  /// **'今天有 {count} 条待复习错题，适合先完成高优先级回看。'**
  String reviewPlanHubHasErrors(Object count);

  /// No description provided for @reviewPlanHubNoNightlyReview.
  ///
  /// In zh, this message translates to:
  /// **'今晚还没有生成夜间回顾，先完成主线复习也可以。'**
  String get reviewPlanHubNoNightlyReview;

  /// No description provided for @reviewPlanHubHasNightlyReview.
  ///
  /// In zh, this message translates to:
  /// **'系统已经生成夜间回顾，适合在收尾时统一查看。'**
  String get reviewPlanHubHasNightlyReview;

  /// No description provided for @reviewPlanHubNightlyUnavailable.
  ///
  /// In zh, this message translates to:
  /// **'夜间回顾暂不可用，先按计划推进今日复习。'**
  String get reviewPlanHubNightlyUnavailable;

  /// No description provided for @reviewPlanHubLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'复习列表暂时加载失败：{error}'**
  String reviewPlanHubLoadFailed(Object error);

  /// No description provided for @reviewPlanHubCreatePlanFirst.
  ///
  /// In zh, this message translates to:
  /// **'先创建成长计划或冲刺计划，复习计划中心才会把计划任务和复习节奏串起来。'**
  String get reviewPlanHubCreatePlanFirst;

  /// No description provided for @reviewPlanHubNoPlanTasks.
  ///
  /// In zh, this message translates to:
  /// **'今天没有关联到计划的待推进任务，可以先做错题复习或回到计划里补任务。'**
  String get reviewPlanHubNoPlanTasks;

  /// No description provided for @reviewPlanHubSprintProgress.
  ///
  /// In zh, this message translates to:
  /// **'冲刺进度 {percent}% · 剩余 {days} 天'**
  String reviewPlanHubSprintProgress(Object percent, Object days);

  /// No description provided for @reviewPlanHubGrowthProgress.
  ///
  /// In zh, this message translates to:
  /// **'成长进度 {percent}% · 掌握 {mastery}%'**
  String reviewPlanHubGrowthProgress(Object percent, Object mastery);

  /// No description provided for @reviewPlanHubPlanTask.
  ///
  /// In zh, this message translates to:
  /// **'计划任务'**
  String get reviewPlanHubPlanTask;

  /// No description provided for @reviewPlanHubTaskSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'{plan} · {minutes} 分钟'**
  String reviewPlanHubTaskSubtitle(Object plan, Object minutes);

  /// No description provided for @taskQuickActionSnooze.
  ///
  /// In zh, this message translates to:
  /// **'推迟到明天'**
  String get taskQuickActionSnooze;

  /// No description provided for @taskQuickActionTooHardLabel.
  ///
  /// In zh, this message translates to:
  /// **'标记为太难'**
  String get taskQuickActionTooHardLabel;

  /// No description provided for @taskQuickActionSkip.
  ///
  /// In zh, this message translates to:
  /// **'跳过'**
  String get taskQuickActionSkip;

  /// No description provided for @taskQuickActionHelp.
  ///
  /// In zh, this message translates to:
  /// **'寻求帮助'**
  String get taskQuickActionHelp;

  /// No description provided for @statisticsExportTitle.
  ///
  /// In zh, this message translates to:
  /// **'导出统计数据'**
  String get statisticsExportTitle;

  /// No description provided for @statisticsExportFormat.
  ///
  /// In zh, this message translates to:
  /// **'选择导出格式'**
  String get statisticsExportFormat;

  /// No description provided for @statisticsExportIncludeCharts.
  ///
  /// In zh, this message translates to:
  /// **'包含图表数据'**
  String get statisticsExportIncludeCharts;

  /// No description provided for @statisticsExportAs.
  ///
  /// In zh, this message translates to:
  /// **'导出为'**
  String get statisticsExportAs;

  /// No description provided for @statisticsExportStructured.
  ///
  /// In zh, this message translates to:
  /// **'结构化数据'**
  String get statisticsExportStructured;

  /// No description provided for @statisticsExportSpreadsheet.
  ///
  /// In zh, this message translates to:
  /// **'电子表格'**
  String get statisticsExportSpreadsheet;

  /// No description provided for @statisticsExportHDImage.
  ///
  /// In zh, this message translates to:
  /// **'高清图片'**
  String get statisticsExportHDImage;

  /// No description provided for @statisticsExportPDF.
  ///
  /// In zh, this message translates to:
  /// **'PDF文档'**
  String get statisticsExportPDF;

  /// No description provided for @statisticsExportFailed.
  ///
  /// In zh, this message translates to:
  /// **'导出失败: {error}'**
  String statisticsExportFailed(Object error);

  /// No description provided for @statisticsShareTitle.
  ///
  /// In zh, this message translates to:
  /// **'分享统计数据'**
  String get statisticsShareTitle;

  /// No description provided for @statisticsShareWechat.
  ///
  /// In zh, this message translates to:
  /// **'微信'**
  String get statisticsShareWechat;

  /// No description provided for @statisticsShareMoments.
  ///
  /// In zh, this message translates to:
  /// **'朋友圈'**
  String get statisticsShareMoments;

  /// No description provided for @statisticsShareSaveImage.
  ///
  /// In zh, this message translates to:
  /// **'保存图片'**
  String get statisticsShareSaveImage;

  /// No description provided for @statisticsShareCopyLink.
  ///
  /// In zh, this message translates to:
  /// **'复制链接'**
  String get statisticsShareCopyLink;

  /// No description provided for @statisticsShareMore.
  ///
  /// In zh, this message translates to:
  /// **'更多'**
  String get statisticsShareMore;

  /// No description provided for @statisticsWatermark.
  ///
  /// In zh, this message translates to:
  /// **'星火AI学习助手'**
  String get statisticsWatermark;

  /// No description provided for @statisticsDateFormat.
  ///
  /// In zh, this message translates to:
  /// **'{year}年{month}月{day}日'**
  String statisticsDateFormat(Object day, Object month, Object year);

  /// No description provided for @statisticsTypeFocus.
  ///
  /// In zh, this message translates to:
  /// **'专注'**
  String get statisticsTypeFocus;

  /// No description provided for @statisticsTypeAgent.
  ///
  /// In zh, this message translates to:
  /// **'智能体'**
  String get statisticsTypeAgent;

  /// No description provided for @statisticsTypeCapsule.
  ///
  /// In zh, this message translates to:
  /// **'胶囊'**
  String get statisticsTypeCapsule;

  /// No description provided for @statisticsTypeLearning.
  ///
  /// In zh, this message translates to:
  /// **'学习'**
  String get statisticsTypeLearning;

  /// No description provided for @statisticsPeriodToday.
  ///
  /// In zh, this message translates to:
  /// **'今日'**
  String get statisticsPeriodToday;

  /// No description provided for @statisticsPeriodWeek.
  ///
  /// In zh, this message translates to:
  /// **'本周'**
  String get statisticsPeriodWeek;

  /// No description provided for @statisticsPeriodMonth.
  ///
  /// In zh, this message translates to:
  /// **'本月'**
  String get statisticsPeriodMonth;

  /// No description provided for @statisticsPeriodYear.
  ///
  /// In zh, this message translates to:
  /// **'今年'**
  String get statisticsPeriodYear;

  /// No description provided for @statisticsPeriodCustom.
  ///
  /// In zh, this message translates to:
  /// **'自定义'**
  String get statisticsPeriodCustom;

  /// No description provided for @statisticsNoData.
  ///
  /// In zh, this message translates to:
  /// **'暂无数据'**
  String get statisticsNoData;

  /// No description provided for @statisticsLegendLow.
  ///
  /// In zh, this message translates to:
  /// **'低'**
  String get statisticsLegendLow;

  /// No description provided for @statisticsLegendMedium.
  ///
  /// In zh, this message translates to:
  /// **'中'**
  String get statisticsLegendMedium;

  /// No description provided for @statisticsLegendHigh.
  ///
  /// In zh, this message translates to:
  /// **'高'**
  String get statisticsLegendHigh;

  /// No description provided for @statisticsChartMon.
  ///
  /// In zh, this message translates to:
  /// **'一'**
  String get statisticsChartMon;

  /// No description provided for @statisticsChartWed.
  ///
  /// In zh, this message translates to:
  /// **'三'**
  String get statisticsChartWed;

  /// No description provided for @statisticsChartFri.
  ///
  /// In zh, this message translates to:
  /// **'五'**
  String get statisticsChartFri;

  /// No description provided for @statisticsChartMonth1.
  ///
  /// In zh, this message translates to:
  /// **'一月'**
  String get statisticsChartMonth1;

  /// No description provided for @statisticsChartMonth2.
  ///
  /// In zh, this message translates to:
  /// **'二月'**
  String get statisticsChartMonth2;

  /// No description provided for @statisticsChartMonth3.
  ///
  /// In zh, this message translates to:
  /// **'三月'**
  String get statisticsChartMonth3;

  /// No description provided for @statisticsChartMonth4.
  ///
  /// In zh, this message translates to:
  /// **'四月'**
  String get statisticsChartMonth4;

  /// No description provided for @statisticsChartMonth5.
  ///
  /// In zh, this message translates to:
  /// **'五月'**
  String get statisticsChartMonth5;

  /// No description provided for @statisticsChartMonth6.
  ///
  /// In zh, this message translates to:
  /// **'六月'**
  String get statisticsChartMonth6;

  /// No description provided for @statisticsChartMonth7.
  ///
  /// In zh, this message translates to:
  /// **'七月'**
  String get statisticsChartMonth7;

  /// No description provided for @statisticsChartMonth8.
  ///
  /// In zh, this message translates to:
  /// **'八月'**
  String get statisticsChartMonth8;

  /// No description provided for @statisticsChartMonth9.
  ///
  /// In zh, this message translates to:
  /// **'九月'**
  String get statisticsChartMonth9;

  /// No description provided for @statisticsChartMonth10.
  ///
  /// In zh, this message translates to:
  /// **'十月'**
  String get statisticsChartMonth10;

  /// No description provided for @statisticsChartMonth11.
  ///
  /// In zh, this message translates to:
  /// **'十一月'**
  String get statisticsChartMonth11;

  /// No description provided for @statisticsChartMonth12.
  ///
  /// In zh, this message translates to:
  /// **'十二月'**
  String get statisticsChartMonth12;

  /// No description provided for @statisticsExportImageReport.
  ///
  /// In zh, this message translates to:
  /// **'图片报告'**
  String get statisticsExportImageReport;

  /// No description provided for @statisticsExportPDFReport.
  ///
  /// In zh, this message translates to:
  /// **'PDF报告'**
  String get statisticsExportPDFReport;

  /// No description provided for @interventionStartNow.
  ///
  /// In zh, this message translates to:
  /// **'开始'**
  String get interventionStartNow;

  /// No description provided for @interventionLater.
  ///
  /// In zh, this message translates to:
  /// **'稍后'**
  String get interventionLater;

  /// No description provided for @fileUploadTitle.
  ///
  /// In zh, this message translates to:
  /// **'上传文件'**
  String get fileUploadTitle;

  /// No description provided for @fileUploadDesc.
  ///
  /// In zh, this message translates to:
  /// **'支持文档与图片，上传到对话后可继续分享或引用。'**
  String get fileUploadDesc;

  /// No description provided for @fileUploadType.
  ///
  /// In zh, this message translates to:
  /// **'文件'**
  String get fileUploadType;

  /// No description provided for @fileUploadSize.
  ///
  /// In zh, this message translates to:
  /// **'大小'**
  String get fileUploadSize;

  /// No description provided for @fileUploadClickToSelect.
  ///
  /// In zh, this message translates to:
  /// **'点击选择文件'**
  String get fileUploadClickToSelect;

  /// No description provided for @fileUploadSupportedFormats.
  ///
  /// In zh, this message translates to:
  /// **'PDF、DOCX、PPTX、TXT 和常见图片都支持'**
  String get fileUploadSupportedFormats;

  /// No description provided for @fileUploadSelected.
  ///
  /// In zh, this message translates to:
  /// **'已选择文件'**
  String get fileUploadSelected;

  /// No description provided for @fileUploadFormat.
  ///
  /// In zh, this message translates to:
  /// **'{type} · {size}'**
  String fileUploadFormat(Object size, Object type);

  /// No description provided for @fileUploadProgress.
  ///
  /// In zh, this message translates to:
  /// **'上传中 {percent}%'**
  String fileUploadProgress(Object percent);

  /// No description provided for @fileUploadSelect.
  ///
  /// In zh, this message translates to:
  /// **'选择文件'**
  String get fileUploadSelect;

  /// No description provided for @fileUploadReselect.
  ///
  /// In zh, this message translates to:
  /// **'重新选择'**
  String get fileUploadReselect;

  /// No description provided for @fileUploadStart.
  ///
  /// In zh, this message translates to:
  /// **'开始上传'**
  String get fileUploadStart;

  /// No description provided for @fileUploadResume.
  ///
  /// In zh, this message translates to:
  /// **'继续上传'**
  String get fileUploadResume;

  /// No description provided for @fileUploadNetworkError.
  ///
  /// In zh, this message translates to:
  /// **'网络中断，可点击继续上传'**
  String get fileUploadNetworkError;

  /// No description provided for @fileUploadFailed.
  ///
  /// In zh, this message translates to:
  /// **'上传失败: {error}'**
  String fileUploadFailed(Object error);

  /// No description provided for @errorBookCorrectApproach.
  ///
  /// In zh, this message translates to:
  /// **'正确思路'**
  String get errorBookCorrectApproach;

  /// No description provided for @errorBookSimilarTraps.
  ///
  /// In zh, this message translates to:
  /// **'类似易错点'**
  String get errorBookSimilarTraps;

  /// No description provided for @errorBookStudySuggestion.
  ///
  /// In zh, this message translates to:
  /// **'学习建议'**
  String get errorBookStudySuggestion;

  /// No description provided for @errorBookKnowledgeRelated.
  ///
  /// In zh, this message translates to:
  /// **'关联知识点'**
  String get errorBookKnowledgeRelated;

  /// No description provided for @errorBookAnalyzing.
  ///
  /// In zh, this message translates to:
  /// **'AI 正在分析中...'**
  String get errorBookAnalyzing;

  /// No description provided for @errorBookAnalyzingDesc.
  ///
  /// In zh, this message translates to:
  /// **'正在分析错题原因、生成学习建议并关联知识点，预计需要 3-5 秒'**
  String get errorBookAnalyzingDesc;

  /// No description provided for @simulationSceneStudyGroup.
  ///
  /// In zh, this message translates to:
  /// **'虚拟学习小组'**
  String get simulationSceneStudyGroup;

  /// No description provided for @simulationSceneKnowledgeDebate.
  ///
  /// In zh, this message translates to:
  /// **'知识辩论'**
  String get simulationSceneKnowledgeDebate;

  /// No description provided for @simulationSceneHistoricalRoleplay.
  ///
  /// In zh, this message translates to:
  /// **'历史角色扮演'**
  String get simulationSceneHistoricalRoleplay;

  /// No description provided for @simulationSceneSocraticDialogue.
  ///
  /// In zh, this message translates to:
  /// **'苏格拉底式对话'**
  String get simulationSceneSocraticDialogue;

  /// No description provided for @simulationSceneCaseAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'案例拆解'**
  String get simulationSceneCaseAnalysis;

  /// No description provided for @simulationSceneWhatIfPath.
  ///
  /// In zh, this message translates to:
  /// **'假设分支推演'**
  String get simulationSceneWhatIfPath;

  /// No description provided for @simulationSceneConceptMapBuild.
  ///
  /// In zh, this message translates to:
  /// **'概念图共建'**
  String get simulationSceneConceptMapBuild;

  /// No description provided for @simulationSceneErrorDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'错因诊断'**
  String get simulationSceneErrorDiagnosis;

  /// No description provided for @simulationStateWaiting.
  ///
  /// In zh, this message translates to:
  /// **'等待你的判断'**
  String get simulationStateWaiting;

  /// No description provided for @simulationStateCompleted.
  ///
  /// In zh, this message translates to:
  /// **'讨论已收束'**
  String get simulationStateCompleted;

  /// No description provided for @simulationStateRunning.
  ///
  /// In zh, this message translates to:
  /// **'正在推进讨论'**
  String get simulationStateRunning;

  /// No description provided for @simulationStatePending.
  ///
  /// In zh, this message translates to:
  /// **'正在准备'**
  String get simulationStatePending;

  /// No description provided for @simulationStateReady.
  ///
  /// In zh, this message translates to:
  /// **'准备中'**
  String get simulationStateReady;

  /// No description provided for @simulationStanceSupporting.
  ///
  /// In zh, this message translates to:
  /// **'支持派'**
  String get simulationStanceSupporting;

  /// No description provided for @simulationStanceSupportive.
  ///
  /// In zh, this message translates to:
  /// **'补充支持'**
  String get simulationStanceSupportive;

  /// No description provided for @simulationStanceOpposing.
  ///
  /// In zh, this message translates to:
  /// **'反方质疑'**
  String get simulationStanceOpposing;

  /// No description provided for @simulationStanceModerating.
  ///
  /// In zh, this message translates to:
  /// **'居中协调'**
  String get simulationStanceModerating;

  /// No description provided for @simulationStanceProbing.
  ///
  /// In zh, this message translates to:
  /// **'追问推进'**
  String get simulationStanceProbing;

  /// No description provided for @simulationStanceChallenging.
  ///
  /// In zh, this message translates to:
  /// **'提出质疑'**
  String get simulationStanceChallenging;

  /// No description provided for @simulationStanceImmersive.
  ///
  /// In zh, this message translates to:
  /// **'沉浸代入'**
  String get simulationStanceImmersive;

  /// No description provided for @simulationStanceContextual.
  ///
  /// In zh, this message translates to:
  /// **'补充背景'**
  String get simulationStanceContextual;

  /// No description provided for @simulationStanceReflective.
  ///
  /// In zh, this message translates to:
  /// **'回看反思'**
  String get simulationStanceReflective;

  /// No description provided for @simulationActionChallenge.
  ///
  /// In zh, this message translates to:
  /// **'提出质疑'**
  String get simulationActionChallenge;

  /// No description provided for @simulationActionSynthesize.
  ///
  /// In zh, this message translates to:
  /// **'整合观点'**
  String get simulationActionSynthesize;

  /// No description provided for @simulationActionOpen.
  ///
  /// In zh, this message translates to:
  /// **'打开话题'**
  String get simulationActionOpen;

  /// No description provided for @simulationActionGuideUser.
  ///
  /// In zh, this message translates to:
  /// **'邀请你作答'**
  String get simulationActionGuideUser;

  /// No description provided for @simulationActionProbe.
  ///
  /// In zh, this message translates to:
  /// **'继续追问'**
  String get simulationActionProbe;

  /// No description provided for @simulationActionExtend.
  ///
  /// In zh, this message translates to:
  /// **'展开补充'**
  String get simulationActionExtend;

  /// No description provided for @simulationActionUserResponse.
  ///
  /// In zh, this message translates to:
  /// **'你的回应'**
  String get simulationActionUserResponse;

  /// No description provided for @simulationSourceGalaxy.
  ///
  /// In zh, this message translates to:
  /// **'知识星图'**
  String get simulationSourceGalaxy;

  /// No description provided for @simulationSourceTasks.
  ///
  /// In zh, this message translates to:
  /// **'任务记录'**
  String get simulationSourceTasks;

  /// No description provided for @simulationSourcePlan.
  ///
  /// In zh, this message translates to:
  /// **'学习计划'**
  String get simulationSourcePlan;

  /// No description provided for @simulationSourceStarterGraph.
  ///
  /// In zh, this message translates to:
  /// **'起步图谱'**
  String get simulationSourceStarterGraph;

  /// No description provided for @simulationSourceKnowledgeGraph.
  ///
  /// In zh, this message translates to:
  /// **'知识图谱'**
  String get simulationSourceKnowledgeGraph;

  /// No description provided for @simulationSourceTemplate.
  ///
  /// In zh, this message translates to:
  /// **'默认角色模板'**
  String get simulationSourceTemplate;

  /// No description provided for @simulationSourceErrorBook.
  ///
  /// In zh, this message translates to:
  /// **'错题记录'**
  String get simulationSourceErrorBook;

  /// No description provided for @simulationSourceOnboardingProfile.
  ///
  /// In zh, this message translates to:
  /// **'学习画像'**
  String get simulationSourceOnboardingProfile;

  /// No description provided for @simulationRoleAnalyst.
  ///
  /// In zh, this message translates to:
  /// **'分析者'**
  String get simulationRoleAnalyst;

  /// No description provided for @simulationRoleExpert.
  ///
  /// In zh, this message translates to:
  /// **'专家'**
  String get simulationRoleExpert;

  /// No description provided for @simulationRoleCoach.
  ///
  /// In zh, this message translates to:
  /// **'教练'**
  String get simulationRoleCoach;

  /// No description provided for @simulationRoleNavigator.
  ///
  /// In zh, this message translates to:
  /// **'导航者'**
  String get simulationRoleNavigator;

  /// No description provided for @simulationRoleChallenger.
  ///
  /// In zh, this message translates to:
  /// **'质疑者'**
  String get simulationRoleChallenger;

  /// No description provided for @simulationRoleSupporter.
  ///
  /// In zh, this message translates to:
  /// **'支持者'**
  String get simulationRoleSupporter;

  /// No description provided for @simulationRoleObserver.
  ///
  /// In zh, this message translates to:
  /// **'观察者'**
  String get simulationRoleObserver;

  /// No description provided for @simulationRoleMentor.
  ///
  /// In zh, this message translates to:
  /// **'导师'**
  String get simulationRoleMentor;

  /// No description provided for @simulationRoleBuilder.
  ///
  /// In zh, this message translates to:
  /// **'搭建者'**
  String get simulationRoleBuilder;

  /// No description provided for @simulationBubbleSpotlight.
  ///
  /// In zh, this message translates to:
  /// **'当前焦点发言'**
  String get simulationBubbleSpotlight;

  /// No description provided for @simulationBubbleReplyTo.
  ///
  /// In zh, this message translates to:
  /// **'承接 {speaker} 的观点'**
  String simulationBubbleReplyTo(Object speaker);

  /// No description provided for @simulationBubbleStance.
  ///
  /// In zh, this message translates to:
  /// **'立场 {stance}'**
  String simulationBubbleStance(Object stance);

  /// No description provided for @simulationBubbleReply.
  ///
  /// In zh, this message translates to:
  /// **'回应 {speaker}'**
  String simulationBubbleReply(Object speaker);

  /// No description provided for @simulationBubbleRound.
  ///
  /// In zh, this message translates to:
  /// **'第 {round} 轮'**
  String simulationBubbleRound(Object round);

  /// No description provided for @achievementPrestigeLane.
  ///
  /// In zh, this message translates to:
  /// **'声望进阶线'**
  String get achievementPrestigeLane;

  /// No description provided for @weatherTitleSunny.
  ///
  /// In zh, this message translates to:
  /// **'晴空万里'**
  String get weatherTitleSunny;

  /// No description provided for @weatherTitleCloudy.
  ///
  /// In zh, this message translates to:
  /// **'薄雾弥漫'**
  String get weatherTitleCloudy;

  /// No description provided for @weatherTitleRainy.
  ///
  /// In zh, this message translates to:
  /// **'风雨欲来'**
  String get weatherTitleRainy;

  /// No description provided for @weatherTitleMeteor.
  ///
  /// In zh, this message translates to:
  /// **'繁星入梦'**
  String get weatherTitleMeteor;

  /// No description provided for @weatherSubtitleSunny.
  ///
  /// In zh, this message translates to:
  /// **'光感轻轻上扬，今天适合稳定推进。'**
  String get weatherSubtitleSunny;

  /// No description provided for @weatherSubtitleCloudy.
  ///
  /// In zh, this message translates to:
  /// **'边界柔和，适合整理思路与留白。'**
  String get weatherSubtitleCloudy;

  /// No description provided for @weatherSubtitleRainy.
  ///
  /// In zh, this message translates to:
  /// **'环境收拢，适合沉浸、专注与减少噪声。'**
  String get weatherSubtitleRainy;

  /// No description provided for @weatherSubtitleMeteor.
  ///
  /// In zh, this message translates to:
  /// **'灵感高亮，适合冲刺、突破与留下痕迹。'**
  String get weatherSubtitleMeteor;

  /// No description provided for @weatherCompactSunny.
  ///
  /// In zh, this message translates to:
  /// **'明亮推进'**
  String get weatherCompactSunny;

  /// No description provided for @weatherCompactCloudy.
  ///
  /// In zh, this message translates to:
  /// **'轻缓整理'**
  String get weatherCompactCloudy;

  /// No description provided for @weatherCompactRainy.
  ///
  /// In zh, this message translates to:
  /// **'深潜聚焦'**
  String get weatherCompactRainy;

  /// No description provided for @weatherCompactMeteor.
  ///
  /// In zh, this message translates to:
  /// **'高光冲刺'**
  String get weatherCompactMeteor;

  /// No description provided for @weatherAmbientSunny.
  ///
  /// In zh, this message translates to:
  /// **'空气更通透了，节奏也更容易启动。'**
  String get weatherAmbientSunny;

  /// No description provided for @weatherAmbientCloudy.
  ///
  /// In zh, this message translates to:
  /// **'雾层抹平了边界，画面更安静。'**
  String get weatherAmbientCloudy;

  /// No description provided for @weatherAmbientRainy.
  ///
  /// In zh, this message translates to:
  /// **'雨幕把外界压低了，注意力更容易收束。'**
  String get weatherAmbientRainy;

  /// No description provided for @weatherAmbientMeteor.
  ///
  /// In zh, this message translates to:
  /// **'星迹开始拉长，灵感窗口正在打开。'**
  String get weatherAmbientMeteor;

  /// No description provided for @weatherGuideTitle.
  ///
  /// In zh, this message translates to:
  /// **'天气图鉴'**
  String get weatherGuideTitle;

  /// No description provided for @weatherGuidePreview.
  ///
  /// In zh, this message translates to:
  /// **'天气预览'**
  String get weatherGuidePreview;

  /// No description provided for @weatherGuidePreviewSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'这里可以预览系统里的全部天气表现。预览不会改动真实天气，只用于帮助你理解视觉效果与设定。'**
  String get weatherGuidePreviewSubtitle;

  /// No description provided for @weatherGuideCriteria.
  ///
  /// In zh, this message translates to:
  /// **'判定标准'**
  String get weatherGuideCriteria;

  /// No description provided for @weatherGuideCriteriaSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'真实天气依然由你的近期数据决定，下面是当前系统的主要参考规则。'**
  String get weatherGuideCriteriaSubtitle;

  /// No description provided for @weatherGuideRule1Title.
  ///
  /// In zh, this message translates to:
  /// **'晴空是默认状态'**
  String get weatherGuideRule1Title;

  /// No description provided for @weatherGuideRule1Body.
  ///
  /// In zh, this message translates to:
  /// **'当系统没有检测到明显的高压、拖延或强势冲刺信号时，会保持晴空。'**
  String get weatherGuideRule1Body;

  /// No description provided for @weatherGuideRule2Title.
  ///
  /// In zh, this message translates to:
  /// **'薄雾代表节奏变慢'**
  String get weatherGuideRule2Title;

  /// No description provided for @weatherGuideRule2Body.
  ///
  /// In zh, this message translates to:
  /// **'冲刺剩余 7 天内且进度低于 20%，或连续 2 天没有完成任务时，天气更容易转为薄雾。'**
  String get weatherGuideRule2Body;

  /// No description provided for @weatherGuideRule3Title.
  ///
  /// In zh, this message translates to:
  /// **'风雨代表压力偏高'**
  String get weatherGuideRule3Title;

  /// No description provided for @weatherGuideRule3Body.
  ///
  /// In zh, this message translates to:
  /// **'冲刺剩余少于 3 天且进度低于 50% 时，系统会倾向给出风雨状态，提醒你尽快收束焦点。'**
  String get weatherGuideRule3Body;

  /// No description provided for @weatherGuideRule4Title.
  ///
  /// In zh, this message translates to:
  /// **'焦虑会覆盖基础判断'**
  String get weatherGuideRule4Title;

  /// No description provided for @weatherGuideRule4Body.
  ///
  /// In zh, this message translates to:
  /// **'如果近期焦虑指标高于 50%，系统会优先给出风雨天气，用来提示当前负荷偏高。'**
  String get weatherGuideRule4Body;

  /// No description provided for @weatherGuideRule5Title.
  ///
  /// In zh, this message translates to:
  /// **'流星代表高势能'**
  String get weatherGuideRule5Title;

  /// No description provided for @weatherGuideRule5Body.
  ///
  /// In zh, this message translates to:
  /// **'当当前冲刺进度高于 80% 时，系统更容易进入流星天气，强调你的推进势头。'**
  String get weatherGuideRule5Body;

  /// No description provided for @weatherGuideCurrent.
  ///
  /// In zh, this message translates to:
  /// **'当前'**
  String get weatherGuideCurrent;

  /// No description provided for @weatherGuideCurrentWeather.
  ///
  /// In zh, this message translates to:
  /// **'当前天气'**
  String get weatherGuideCurrentWeather;

  /// No description provided for @weatherGuideConditionFallback.
  ///
  /// In zh, this message translates to:
  /// **'当前天气会根据你的真实数据自动更新。'**
  String get weatherGuideConditionFallback;

  /// No description provided for @weatherGuideConditionPrefix.
  ///
  /// In zh, this message translates to:
  /// **'当前判定：{condition}'**
  String weatherGuideConditionPrefix(Object condition);

  /// No description provided for @weatherGuideDisclaimer.
  ///
  /// In zh, this message translates to:
  /// **'这个页面用于理解天气系统的视觉效果与判定逻辑。真正显示给你的天气，仍然会跟随你的真实任务、冲刺和状态数据动态更新。'**
  String get weatherGuideDisclaimer;

  /// No description provided for @weatherGuideTriggerPrefix.
  ///
  /// In zh, this message translates to:
  /// **'真实触发参考：{trigger}'**
  String weatherGuideTriggerPrefix(Object trigger);

  /// No description provided for @intentPredictionSprintSprint.
  ///
  /// In zh, this message translates to:
  /// **'冲刺冲刺'**
  String get intentPredictionSprintSprint;

  /// No description provided for @intentPredictionContinue.
  ///
  /// In zh, this message translates to:
  /// **'继续\"{title}\"'**
  String intentPredictionContinue(Object title);

  /// No description provided for @intentPredictionCreateTask.
  ///
  /// In zh, this message translates to:
  /// **'创建任务'**
  String get intentPredictionCreateTask;

  /// No description provided for @intentPredictionStartFocus.
  ///
  /// In zh, this message translates to:
  /// **'开始专注'**
  String get intentPredictionStartFocus;

  /// No description provided for @intentPredictionViewCalendar.
  ///
  /// In zh, this message translates to:
  /// **'查看日历'**
  String get intentPredictionViewCalendar;

  /// No description provided for @intentPredictionCuriosityCapsule.
  ///
  /// In zh, this message translates to:
  /// **'好奇心胶囊'**
  String get intentPredictionCuriosityCapsule;

  /// No description provided for @intentPredictionSendToAI.
  ///
  /// In zh, this message translates to:
  /// **'发送给AI'**
  String get intentPredictionSendToAI;

  /// No description provided for @intentPredictionNoteIdea.
  ///
  /// In zh, this message translates to:
  /// **'记录想法'**
  String get intentPredictionNoteIdea;

  /// No description provided for @intentPredictionSetReminder.
  ///
  /// In zh, this message translates to:
  /// **'设置提醒'**
  String get intentPredictionSetReminder;

  /// No description provided for @intentPredictionCognitivePrism.
  ///
  /// In zh, this message translates to:
  /// **'认知棱镜'**
  String get intentPredictionCognitivePrism;

  /// No description provided for @intentPredictionTranslate.
  ///
  /// In zh, this message translates to:
  /// **'翻译文本'**
  String get intentPredictionTranslate;

  /// No description provided for @intentPredictionLearnLanguage.
  ///
  /// In zh, this message translates to:
  /// **'学习语言'**
  String get intentPredictionLearnLanguage;

  /// No description provided for @intentPredictionViewPrism.
  ///
  /// In zh, this message translates to:
  /// **'查看认知棱镜'**
  String get intentPredictionViewPrism;

  /// No description provided for @intentPredictionBehaviorAnalysis.
  ///
  /// In zh, this message translates to:
  /// **'行为分析'**
  String get intentPredictionBehaviorAnalysis;

  /// No description provided for @intentPredictionStartSprint.
  ///
  /// In zh, this message translates to:
  /// **'开始冲刺'**
  String get intentPredictionStartSprint;

  /// No description provided for @intentPredictionFocusMode.
  ///
  /// In zh, this message translates to:
  /// **'专注模式'**
  String get intentPredictionFocusMode;

  /// No description provided for @intentPredictionStartLearning.
  ///
  /// In zh, this message translates to:
  /// **'开始学习'**
  String get intentPredictionStartLearning;

  /// No description provided for @intentPredictionCreateStudyPlan.
  ///
  /// In zh, this message translates to:
  /// **'创建学习计划'**
  String get intentPredictionCreateStudyPlan;

  /// No description provided for @intentPredictionStartReview.
  ///
  /// In zh, this message translates to:
  /// **'开始复习'**
  String get intentPredictionStartReview;

  /// No description provided for @intentPredictionViewErrorBook.
  ///
  /// In zh, this message translates to:
  /// **'查看错题本'**
  String get intentPredictionViewErrorBook;

  /// No description provided for @intentPredictionContinuePriority.
  ///
  /// In zh, this message translates to:
  /// **'继续重点任务'**
  String get intentPredictionContinuePriority;

  /// No description provided for @intentPrediction25Min.
  ///
  /// In zh, this message translates to:
  /// **'先做 25 分钟'**
  String get intentPrediction25Min;

  /// No description provided for @flashCapsuleTitle.
  ///
  /// In zh, this message translates to:
  /// **'闪念胶囊'**
  String get flashCapsuleTitle;

  /// No description provided for @flashCapsuleSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'把一闪而过的疑点及时落地成错题线索，减少【知道有问题但没记住】的损耗。'**
  String get flashCapsuleSubtitle;

  /// No description provided for @flashCapsuleHistory.
  ///
  /// In zh, this message translates to:
  /// **'历史胶囊'**
  String get flashCapsuleHistory;

  /// No description provided for @flashCapsuleHistoryEmpty.
  ///
  /// In zh, this message translates to:
  /// **'还没有保存过闪念胶囊。'**
  String get flashCapsuleHistoryEmpty;

  /// No description provided for @flashCapsuleHistoryDesc.
  ///
  /// In zh, this message translates to:
  /// **'这里会显示你之前保存过的闪念与思考胶囊。'**
  String get flashCapsuleHistoryDesc;

  /// No description provided for @flashCapsuleNoHistory.
  ///
  /// In zh, this message translates to:
  /// **'暂无历史胶囊'**
  String get flashCapsuleNoHistory;

  /// No description provided for @flashCapsuleNoHistoryDesc.
  ///
  /// In zh, this message translates to:
  /// **'保存一次闪念胶囊后，就能在这里继续回看。'**
  String get flashCapsuleNoHistoryDesc;

  /// No description provided for @flashCapsuleUnnamed.
  ///
  /// In zh, this message translates to:
  /// **'未命名胶囊'**
  String get flashCapsuleUnnamed;

  /// No description provided for @flashCapsuleNoDesc.
  ///
  /// In zh, this message translates to:
  /// **'暂无补充描述'**
  String get flashCapsuleNoDesc;

  /// No description provided for @flashCapsuleSyncPending.
  ///
  /// In zh, this message translates to:
  /// **'待同步'**
  String get flashCapsuleSyncPending;

  /// No description provided for @flashCapsuleContent.
  ///
  /// In zh, this message translates to:
  /// **'记录内容'**
  String get flashCapsuleContent;

  /// No description provided for @flashCapsuleContentSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'选择科目、错误类型，再补充知识点和描述。'**
  String get flashCapsuleContentSubtitle;

  /// No description provided for @flashCapsuleSubject.
  ///
  /// In zh, this message translates to:
  /// **'科目'**
  String get flashCapsuleSubject;

  /// No description provided for @flashCapsuleSelectSubject.
  ///
  /// In zh, this message translates to:
  /// **'选择科目'**
  String get flashCapsuleSelectSubject;

  /// No description provided for @flashCapsuleKnowledgePoint.
  ///
  /// In zh, this message translates to:
  /// **'知识点'**
  String get flashCapsuleKnowledgePoint;

  /// No description provided for @flashCapsuleKnowledgeHint.
  ///
  /// In zh, this message translates to:
  /// **'例如：三角函数求导、牛顿第二定律...'**
  String get flashCapsuleKnowledgeHint;

  /// No description provided for @flashCapsuleErrorDesc.
  ///
  /// In zh, this message translates to:
  /// **'错误描述'**
  String get flashCapsuleErrorDesc;

  /// No description provided for @flashCapsuleErrorHint.
  ///
  /// In zh, this message translates to:
  /// **'记录你是怎么错的、卡在什么地方、下次要如何避免。'**
  String get flashCapsuleErrorHint;

  /// No description provided for @flashCapsuleKpLength.
  ///
  /// In zh, this message translates to:
  /// **'知识点长度'**
  String get flashCapsuleKpLength;

  /// No description provided for @flashCapsuleDescLength.
  ///
  /// In zh, this message translates to:
  /// **'描述长度'**
  String get flashCapsuleDescLength;

  /// No description provided for @flashCapsuleCognitiveDim.
  ///
  /// In zh, this message translates to:
  /// **'认知维度'**
  String get flashCapsuleCognitiveDim;

  /// No description provided for @flashCapsuleHistoryView.
  ///
  /// In zh, this message translates to:
  /// **'查看历史'**
  String get flashCapsuleHistoryView;

  /// No description provided for @flashCapsuleSaving.
  ///
  /// In zh, this message translates to:
  /// **'记录中...'**
  String get flashCapsuleSaving;

  /// No description provided for @flashCapsuleSave.
  ///
  /// In zh, this message translates to:
  /// **'保存胶囊'**
  String get flashCapsuleSave;

  /// No description provided for @flashCapsuleSubjectCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个科目'**
  String flashCapsuleSubjectCount(Object count);

  /// No description provided for @flashCapsuleHistoryCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 条历史胶囊'**
  String flashCapsuleHistoryCount(Object count);

  /// No description provided for @flashCapsuleSaved.
  ///
  /// In zh, this message translates to:
  /// **'已保存胶囊，并同步到错题本'**
  String get flashCapsuleSaved;

  /// No description provided for @flashCapsuleSavedNoSync.
  ///
  /// In zh, this message translates to:
  /// **'胶囊已保存，错题本同步稍后重试'**
  String get flashCapsuleSavedNoSync;

  /// No description provided for @flashCapsuleSaveFailed.
  ///
  /// In zh, this message translates to:
  /// **'记录失败: {error}'**
  String flashCapsuleSaveFailed(Object error);

  /// No description provided for @flashCapsuleSyncFailed.
  ///
  /// In zh, this message translates to:
  /// **'请补全知识点和错误描述'**
  String get flashCapsuleSyncFailed;

  /// No description provided for @flashCapsuleSaveError.
  ///
  /// In zh, this message translates to:
  /// **'胶囊保存失败，请稍后重试'**
  String get flashCapsuleSaveError;

  /// No description provided for @flashCapsuleLoadError.
  ///
  /// In zh, this message translates to:
  /// **'加载历史胶囊失败: {error}'**
  String flashCapsuleLoadError(Object error);

  /// No description provided for @flashCapsuleErrorConcept.
  ///
  /// In zh, this message translates to:
  /// **'概念混淆'**
  String get flashCapsuleErrorConcept;

  /// No description provided for @flashCapsuleErrorCalc.
  ///
  /// In zh, this message translates to:
  /// **'计算错误'**
  String get flashCapsuleErrorCalc;

  /// No description provided for @flashCapsuleErrorReading.
  ///
  /// In zh, this message translates to:
  /// **'审题不清'**
  String get flashCapsuleErrorReading;

  /// No description provided for @flashCapsuleErrorMemory.
  ///
  /// In zh, this message translates to:
  /// **'知识遗忘'**
  String get flashCapsuleErrorMemory;

  /// No description provided for @flashCapsuleErrorMethod.
  ///
  /// In zh, this message translates to:
  /// **'方法不当'**
  String get flashCapsuleErrorMethod;

  /// No description provided for @flashCapsuleErrorOther.
  ///
  /// In zh, this message translates to:
  /// **'其他'**
  String get flashCapsuleErrorOther;

  /// No description provided for @flashCapsuleSubjectMath.
  ///
  /// In zh, this message translates to:
  /// **'数学'**
  String get flashCapsuleSubjectMath;

  /// No description provided for @flashCapsuleSubjectPhysics.
  ///
  /// In zh, this message translates to:
  /// **'物理'**
  String get flashCapsuleSubjectPhysics;

  /// No description provided for @flashCapsuleSubjectChemistry.
  ///
  /// In zh, this message translates to:
  /// **'化学'**
  String get flashCapsuleSubjectChemistry;

  /// No description provided for @flashCapsuleSubjectBiology.
  ///
  /// In zh, this message translates to:
  /// **'生物'**
  String get flashCapsuleSubjectBiology;

  /// No description provided for @flashCapsuleSubjectEnglish.
  ///
  /// In zh, this message translates to:
  /// **'英语'**
  String get flashCapsuleSubjectEnglish;

  /// No description provided for @flashCapsuleSubjectChinese.
  ///
  /// In zh, this message translates to:
  /// **'语文'**
  String get flashCapsuleSubjectChinese;

  /// No description provided for @flashCapsuleSubjectComputer.
  ///
  /// In zh, this message translates to:
  /// **'计算机'**
  String get flashCapsuleSubjectComputer;

  /// No description provided for @flashCapsuleSubjectOther.
  ///
  /// In zh, this message translates to:
  /// **'其他'**
  String get flashCapsuleSubjectOther;

  /// No description provided for @flashCapsuleTagFlash.
  ///
  /// In zh, this message translates to:
  /// **'闪念'**
  String get flashCapsuleTagFlash;

  /// No description provided for @flashCapsuleTagThink.
  ///
  /// In zh, this message translates to:
  /// **'思考'**
  String get flashCapsuleTagThink;

  /// No description provided for @vocabularyLookupTitle.
  ///
  /// In zh, this message translates to:
  /// **'查词'**
  String get vocabularyLookupTitle;

  /// No description provided for @vocabularyLookupSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'用来做快速词义确认、例句生成和关联词扩展，查询结果可以直接收进本地生词本。'**
  String get vocabularyLookupSubtitle;

  /// No description provided for @vocabularyLookupInput.
  ///
  /// In zh, this message translates to:
  /// **'查询输入'**
  String get vocabularyLookupInput;

  /// No description provided for @vocabularyLookupInputSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'输入英文单词后回车或点击查询。Oxford 词典优先，本地离线包会先于网络命中。'**
  String get vocabularyLookupInputSubtitle;

  /// No description provided for @vocabularyLookupSearch.
  ///
  /// In zh, this message translates to:
  /// **'查询'**
  String get vocabularyLookupSearch;

  /// No description provided for @vocabularyLookupInputHint.
  ///
  /// In zh, this message translates to:
  /// **'输入英文单词...'**
  String get vocabularyLookupInputHint;

  /// No description provided for @vocabularyLookupResults.
  ///
  /// In zh, this message translates to:
  /// **'查询结果'**
  String get vocabularyLookupResults;

  /// No description provided for @vocabularyLookupResultsSubtitle.
  ///
  /// In zh, this message translates to:
  /// **'词义、例句、关联词和模型生成句都在这里。'**
  String get vocabularyLookupResultsSubtitle;

  /// No description provided for @vocabularyLookupStartTyping.
  ///
  /// In zh, this message translates to:
  /// **'输入单词开始查询'**
  String get vocabularyLookupStartTyping;

  /// No description provided for @vocabularyLookupTemporarilyFailed.
  ///
  /// In zh, this message translates to:
  /// **'查询暂时失败'**
  String get vocabularyLookupTemporarilyFailed;

  /// No description provided for @vocabularyLookupErrorDesc.
  ///
  /// In zh, this message translates to:
  /// **'查询完成后可以直接收藏到生词本，并继续生成例句。'**
  String get vocabularyLookupErrorDesc;

  /// No description provided for @vocabularyLookupDefinitions.
  ///
  /// In zh, this message translates to:
  /// **'释义'**
  String get vocabularyLookupDefinitions;

  /// No description provided for @vocabularyLookupDictExamples.
  ///
  /// In zh, this message translates to:
  /// **'词典例句'**
  String get vocabularyLookupDictExamples;

  /// No description provided for @vocabularyLookupGeneratedExample.
  ///
  /// In zh, this message translates to:
  /// **'模型生成例句'**
  String get vocabularyLookupGeneratedExample;

  /// No description provided for @vocabularyLookupRelatedWords.
  ///
  /// In zh, this message translates to:
  /// **'关联词汇'**
  String get vocabularyLookupRelatedWords;

  /// No description provided for @vocabularyLookupInWordbook.
  ///
  /// In zh, this message translates to:
  /// **'已在生词本中'**
  String get vocabularyLookupInWordbook;

  /// No description provided for @vocabularyLookupCanAdd.
  ///
  /// In zh, this message translates to:
  /// **'可加入生词本'**
  String get vocabularyLookupCanAdd;

  /// No description provided for @vocabularyLookupWaitingAssoc.
  ///
  /// In zh, this message translates to:
  /// **'等待关联词'**
  String get vocabularyLookupWaitingAssoc;

  /// No description provided for @vocabularyLookupAssocCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个关联词'**
  String vocabularyLookupAssocCount(Object count);

  /// No description provided for @vocabularyLookupOfflineCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个离线词典包'**
  String vocabularyLookupOfflineCount(Object count);

  /// No description provided for @vocabularyLookupNoOffline.
  ///
  /// In zh, this message translates to:
  /// **'未下载离线词典'**
  String get vocabularyLookupNoOffline;

  /// No description provided for @vocabularyLookupManageOffline.
  ///
  /// In zh, this message translates to:
  /// **'管理离线词典'**
  String get vocabularyLookupManageOffline;

  /// No description provided for @vocabularyLookupDownloadOffline.
  ///
  /// In zh, this message translates to:
  /// **'下载离线词典'**
  String get vocabularyLookupDownloadOffline;

  /// No description provided for @vocabularyLookupOfflinePackages.
  ///
  /// In zh, this message translates to:
  /// **'离线词典包'**
  String get vocabularyLookupOfflinePackages;

  /// No description provided for @vocabularyLookupOfflineDesc.
  ///
  /// In zh, this message translates to:
  /// **'优先使用本地 Oxford 词典，减少网络依赖，也能减轻云端服务器压力。'**
  String get vocabularyLookupOfflineDesc;

  /// No description provided for @vocabularyLookupInstalled.
  ///
  /// In zh, this message translates to:
  /// **'已安装'**
  String get vocabularyLookupInstalled;

  /// No description provided for @vocabularyLookupPackageDesc.
  ///
  /// In zh, this message translates to:
  /// **'Oxford 优先离线词典包'**
  String get vocabularyLookupPackageDesc;

  /// No description provided for @vocabularyLookupEntryCount.
  ///
  /// In zh, this message translates to:
  /// **'{count} 词条'**
  String vocabularyLookupEntryCount(Object count);

  /// No description provided for @vocabularyLookupSizeBytes.
  ///
  /// In zh, this message translates to:
  /// **'{size}'**
  String vocabularyLookupSizeBytes(Object size);

  /// No description provided for @vocabularyLookupInstalledAt.
  ///
  /// In zh, this message translates to:
  /// **'安装于 {date}'**
  String vocabularyLookupInstalledAt(Object date);

  /// No description provided for @vocabularyLookupReDownload.
  ///
  /// In zh, this message translates to:
  /// **'重新下载'**
  String get vocabularyLookupReDownload;

  /// No description provided for @vocabularyLookupDownloadLocal.
  ///
  /// In zh, this message translates to:
  /// **'下载到本地'**
  String get vocabularyLookupDownloadLocal;

  /// No description provided for @vocabularyLookupRemove.
  ///
  /// In zh, this message translates to:
  /// **'移除'**
  String get vocabularyLookupRemove;

  /// No description provided for @vocabularyLookupGenerateSentence.
  ///
  /// In zh, this message translates to:
  /// **'生成例句'**
  String get vocabularyLookupGenerateSentence;

  /// No description provided for @vocabularyLookupRemoveFromWordbook.
  ///
  /// In zh, this message translates to:
  /// **'移出生词本'**
  String get vocabularyLookupRemoveFromWordbook;

  /// No description provided for @vocabularyLookupAddToWordbook.
  ///
  /// In zh, this message translates to:
  /// **'加入生词本'**
  String get vocabularyLookupAddToWordbook;

  /// No description provided for @vocabularyLookupPos.
  ///
  /// In zh, this message translates to:
  /// **'词性 · {pos}'**
  String vocabularyLookupPos(Object pos);

  /// No description provided for @vocabularyLookupAddedToWordbook.
  ///
  /// In zh, this message translates to:
  /// **'已添加「{word}」到生词本'**
  String vocabularyLookupAddedToWordbook(Object word);

  /// No description provided for @vocabularyLookupRemovedFromWordbook.
  ///
  /// In zh, this message translates to:
  /// **'已从生词本移除「{word}」'**
  String vocabularyLookupRemovedFromWordbook(Object word);

  /// No description provided for @vocabularyLookupEnterWord.
  ///
  /// In zh, this message translates to:
  /// **'请输入要查询的单词'**
  String get vocabularyLookupEnterWord;

  /// No description provided for @vocabularyLookupOfflineDownloaded.
  ///
  /// In zh, this message translates to:
  /// **'离线词典已下载，可优先本地查词'**
  String get vocabularyLookupOfflineDownloaded;

  /// No description provided for @vocabularyLookupOfflineDownloadFailed.
  ///
  /// In zh, this message translates to:
  /// **'离线词典下载失败: {error}'**
  String vocabularyLookupOfflineDownloadFailed(Object error);

  /// No description provided for @vocabularyLookupOfflineRemoved.
  ///
  /// In zh, this message translates to:
  /// **'已移除离线词典包'**
  String get vocabularyLookupOfflineRemoved;

  /// No description provided for @vocabularyLookupOfflineRemoveFailed.
  ///
  /// In zh, this message translates to:
  /// **'移除离线词典包失败: {error}'**
  String vocabularyLookupOfflineRemoveFailed(Object error);

  /// No description provided for @vocabularyLookupNoPackage.
  ///
  /// In zh, this message translates to:
  /// **'暂无可下载的离线词典包'**
  String get vocabularyLookupNoPackage;

  /// No description provided for @vocabularyLookupDownloading.
  ///
  /// In zh, this message translates to:
  /// **'下载中...'**
  String get vocabularyLookupDownloading;

  /// No description provided for @vocabularyLookupPackageScope.
  ///
  /// In zh, this message translates to:
  /// **'{scope}'**
  String vocabularyLookupPackageScope(Object scope);

  /// No description provided for @vocabularyLookupPackageInstallDate.
  ///
  /// In zh, this message translates to:
  /// **'安装于 {date}'**
  String vocabularyLookupPackageInstallDate(Object date);

  /// No description provided for @entityCardActionLabel.
  ///
  /// In zh, this message translates to:
  /// **'执行'**
  String get entityCardActionLabel;

  /// No description provided for @entityCardTitleFallback.
  ///
  /// In zh, this message translates to:
  /// **'未命名卡片'**
  String get entityCardTitleFallback;

  /// No description provided for @entityCardEntityFallback.
  ///
  /// In zh, this message translates to:
  /// **'未命名实体'**
  String get entityCardEntityFallback;

  /// No description provided for @entityCardTaskFallback.
  ///
  /// In zh, this message translates to:
  /// **'未命名任务'**
  String get entityCardTaskFallback;

  /// No description provided for @entityCardPlanFallback.
  ///
  /// In zh, this message translates to:
  /// **'学习计划'**
  String get entityCardPlanFallback;

  /// No description provided for @entityCardKnowledgeFallback.
  ///
  /// In zh, this message translates to:
  /// **'知识节点'**
  String get entityCardKnowledgeFallback;

  /// No description provided for @entityCardTaskListFallback.
  ///
  /// In zh, this message translates to:
  /// **'{count} 个可执行任务'**
  String entityCardTaskListFallback(Object count);

  /// No description provided for @entityCardTaskListSummary.
  ///
  /// In zh, this message translates to:
  /// **'AI 已整理任务列表'**
  String get entityCardTaskListSummary;

  /// No description provided for @visualSlotAvatarBorder.
  ///
  /// In zh, this message translates to:
  /// **'头像边框'**
  String get visualSlotAvatarBorder;

  /// No description provided for @visualSlotTitleBar.
  ///
  /// In zh, this message translates to:
  /// **'称号条'**
  String get visualSlotTitleBar;

  /// No description provided for @visualSlotProfileBanner.
  ///
  /// In zh, this message translates to:
  /// **'主页横幅'**
  String get visualSlotProfileBanner;

  /// No description provided for @visualSlotAchievementFrame.
  ///
  /// In zh, this message translates to:
  /// **'成就主题框'**
  String get visualSlotAchievementFrame;

  /// No description provided for @visualSlotHomeAmbience.
  ///
  /// In zh, this message translates to:
  /// **'首页氛围'**
  String get visualSlotHomeAmbience;

  /// No description provided for @visualSlotStarMapEffect.
  ///
  /// In zh, this message translates to:
  /// **'星图征服特效'**
  String get visualSlotStarMapEffect;

  /// No description provided for @visualSlotStreakFlame.
  ///
  /// In zh, this message translates to:
  /// **'连胜火焰'**
  String get visualSlotStreakFlame;

  /// No description provided for @visualSlotDisplayPedestal.
  ///
  /// In zh, this message translates to:
  /// **'陈列台座'**
  String get visualSlotDisplayPedestal;

  /// No description provided for @visualSlotBackground.
  ///
  /// In zh, this message translates to:
  /// **'背景'**
  String get visualSlotBackground;

  /// No description provided for @visualSlotParticle.
  ///
  /// In zh, this message translates to:
  /// **'粒子'**
  String get visualSlotParticle;

  /// No description provided for @visualSlotEffect.
  ///
  /// In zh, this message translates to:
  /// **'特效'**
  String get visualSlotEffect;

  /// No description provided for @visualSlotBundle.
  ///
  /// In zh, this message translates to:
  /// **'套装'**
  String get visualSlotBundle;

  /// No description provided for @visualSlotHomeAtmo.
  ///
  /// In zh, this message translates to:
  /// **'首页氛围'**
  String get visualSlotHomeAtmo;

  /// No description provided for @visualSlotParticleTrail.
  ///
  /// In zh, this message translates to:
  /// **'粒子轨迹'**
  String get visualSlotParticleTrail;

  /// No description provided for @visualSlotGloryEffect.
  ///
  /// In zh, this message translates to:
  /// **'荣耀特效'**
  String get visualSlotGloryEffect;

  /// No description provided for @visualSlotProfile.
  ///
  /// In zh, this message translates to:
  /// **'个人主页'**
  String get visualSlotProfile;

  /// No description provided for @visualSlotAchievementHeader.
  ///
  /// In zh, this message translates to:
  /// **'成就页头图'**
  String get visualSlotAchievementHeader;

  /// No description provided for @visualSlotAchievementPage.
  ///
  /// In zh, this message translates to:
  /// **'成就页'**
  String get visualSlotAchievementPage;

  /// No description provided for @visualSlotDetailModal.
  ///
  /// In zh, this message translates to:
  /// **'详情弹窗'**
  String get visualSlotDetailModal;

  /// No description provided for @visualSlotAvatarArea.
  ///
  /// In zh, this message translates to:
  /// **'头像身份区'**
  String get visualSlotAvatarArea;

  /// No description provided for @visualSlotNicknameBar.
  ///
  /// In zh, this message translates to:
  /// **'昵称称号条'**
  String get visualSlotNicknameBar;

  /// No description provided for @visualSlotDisplayArea.
  ///
  /// In zh, this message translates to:
  /// **'陈列区'**
  String get visualSlotDisplayArea;

  /// No description provided for @visualSlotGloryShowcase.
  ///
  /// In zh, this message translates to:
  /// **'荣耀柜台'**
  String get visualSlotGloryShowcase;

  /// No description provided for @visualSlotStarMapPage.
  ///
  /// In zh, this message translates to:
  /// **'星图页'**
  String get visualSlotStarMapPage;

  /// No description provided for @visualSlotStreakDisplay.
  ///
  /// In zh, this message translates to:
  /// **'连胜展示'**
  String get visualSlotStreakDisplay;

  /// No description provided for @visualSlotConquestTrail.
  ///
  /// In zh, this message translates to:
  /// **'征服轨迹'**
  String get visualSlotConquestTrail;

  /// No description provided for @visualSlotHomePage.
  ///
  /// In zh, this message translates to:
  /// **'首页氛围'**
  String get visualSlotHomePage;

  /// No description provided for @visualSlotHomeParticle.
  ///
  /// In zh, this message translates to:
  /// **'首页粒子'**
  String get visualSlotHomeParticle;

  /// No description provided for @visualUnlockSystem.
  ///
  /// In zh, this message translates to:
  /// **'系统提供'**
  String get visualUnlockSystem;

  /// No description provided for @visualUnlockAchievement.
  ///
  /// In zh, this message translates to:
  /// **'成就解锁'**
  String get visualUnlockAchievement;

  /// No description provided for @visualUnlockShop.
  ///
  /// In zh, this message translates to:
  /// **'商店获取'**
  String get visualUnlockShop;

  /// No description provided for @visualUnlockEvent.
  ///
  /// In zh, this message translates to:
  /// **'活动限定'**
  String get visualUnlockEvent;

  /// No description provided for @visualUnlockSeason.
  ///
  /// In zh, this message translates to:
  /// **'赛季奖励'**
  String get visualUnlockSeason;

  /// No description provided for @errorDefaultTitle.
  ///
  /// In zh, this message translates to:
  /// **'哎呀，出错了'**
  String get errorDefaultTitle;

  /// No description provided for @warningDefaultTitle.
  ///
  /// In zh, this message translates to:
  /// **'温馨提示'**
  String get warningDefaultTitle;

  /// No description provided for @infoDefaultTitle.
  ///
  /// In zh, this message translates to:
  /// **'小提示'**
  String get infoDefaultTitle;

  /// No description provided for @retryLabel.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get retryLabel;

  /// No description provided for @emptyStateTitle.
  ///
  /// In zh, this message translates to:
  /// **'暂无数据'**
  String get emptyStateTitle;

  /// No description provided for @emptyStateTitleNone.
  ///
  /// In zh, this message translates to:
  /// **'数据为空'**
  String get emptyStateTitleNone;

  /// No description provided for @auroraStatusReady.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 已校准'**
  String get auroraStatusReady;

  /// No description provided for @auroraStatusRecalibrating.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 正在校准'**
  String get auroraStatusRecalibrating;

  /// No description provided for @auroraStatusPartial.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 正在理解'**
  String get auroraStatusPartial;

  /// No description provided for @auroraStatusMissing.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 初始化中'**
  String get auroraStatusMissing;

  /// No description provided for @auroraStatusInactive.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 待激活'**
  String get auroraStatusInactive;

  /// No description provided for @auroraFacetAboutYou.
  ///
  /// In zh, this message translates to:
  /// **'关于你'**
  String get auroraFacetAboutYou;

  /// No description provided for @auroraFacetAboutGoal.
  ///
  /// In zh, this message translates to:
  /// **'关于目标'**
  String get auroraFacetAboutGoal;

  /// No description provided for @auroraFacetAboutNow.
  ///
  /// In zh, this message translates to:
  /// **'关于现在'**
  String get auroraFacetAboutNow;

  /// No description provided for @auroraFacetAboutJudgment.
  ///
  /// In zh, this message translates to:
  /// **'关于我的判断'**
  String get auroraFacetAboutJudgment;

  /// No description provided for @auroraFacetReady.
  ///
  /// In zh, this message translates to:
  /// **'已连通'**
  String get auroraFacetReady;

  /// No description provided for @auroraFacetRecalibrating.
  ///
  /// In zh, this message translates to:
  /// **'重校准中'**
  String get auroraFacetRecalibrating;

  /// No description provided for @auroraFacetPartial.
  ///
  /// In zh, this message translates to:
  /// **'补全中'**
  String get auroraFacetPartial;

  /// No description provided for @auroraFacetMissing.
  ///
  /// In zh, this message translates to:
  /// **'未形成'**
  String get auroraFacetMissing;

  /// No description provided for @auroraConfidenceLabel.
  ///
  /// In zh, this message translates to:
  /// **'把握 {percent}%'**
  String auroraConfidenceLabel(Object percent);

  /// No description provided for @auroraFreshnessLabel.
  ///
  /// In zh, this message translates to:
  /// **'{age}前更新'**
  String auroraFreshnessLabel(Object age);

  /// No description provided for @auroraActionConfirm.
  ///
  /// In zh, this message translates to:
  /// **'看起来对'**
  String get auroraActionConfirm;

  /// No description provided for @auroraActionDisagree.
  ///
  /// In zh, this message translates to:
  /// **'不太对'**
  String get auroraActionDisagree;

  /// No description provided for @auroraActionRecalibrate.
  ///
  /// In zh, this message translates to:
  /// **'重新校准'**
  String get auroraActionRecalibrate;

  /// No description provided for @auroraActionViewDetails.
  ///
  /// In zh, this message translates to:
  /// **'查看 Aurora 详情'**
  String get auroraActionViewDetails;

  /// No description provided for @auroraActionCloseDetails.
  ///
  /// In zh, this message translates to:
  /// **'关闭'**
  String get auroraActionCloseDetails;

  /// No description provided for @auroraLoading.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 加载中'**
  String get auroraLoading;

  /// No description provided for @auroraEvidence.
  ///
  /// In zh, this message translates to:
  /// **'基于'**
  String get auroraEvidence;

  /// No description provided for @auroraNeedsConfirm.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 需要确认'**
  String get auroraNeedsConfirm;

  /// No description provided for @auroraStrategyRisk.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 策略风险升高'**
  String get auroraStrategyRisk;

  /// No description provided for @auroraBackground.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 已退回后台'**
  String get auroraBackground;

  /// No description provided for @auroraCalibrationTitle.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 正在校准'**
  String get auroraCalibrationTitle;

  /// No description provided for @auroraCalibrationObserved.
  ///
  /// In zh, this message translates to:
  /// **'我观察到'**
  String get auroraCalibrationObserved;

  /// No description provided for @auroraCalibrationJudgment.
  ///
  /// In zh, this message translates to:
  /// **'我的判断'**
  String get auroraCalibrationJudgment;

  /// No description provided for @auroraCalibrationUncertainty.
  ///
  /// In zh, this message translates to:
  /// **'我可能判断错的地方'**
  String get auroraCalibrationUncertainty;

  /// No description provided for @auroraCalibrationSuggestion.
  ///
  /// In zh, this message translates to:
  /// **'我的建议'**
  String get auroraCalibrationSuggestion;

  /// No description provided for @auroraCalibrationConfirm.
  ///
  /// In zh, this message translates to:
  /// **'需要你确认'**
  String get auroraCalibrationConfirm;

  /// No description provided for @auroraCalibrationComplete.
  ///
  /// In zh, this message translates to:
  /// **'校准完成，回到标准层。'**
  String get auroraCalibrationComplete;

  /// No description provided for @auroraCalibrationExit.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 已退回后台'**
  String get auroraCalibrationExit;

  /// No description provided for @auroraCorrectNotRight.
  ///
  /// In zh, this message translates to:
  /// **'不是这个方向'**
  String get auroraCorrectNotRight;

  /// No description provided for @auroraCorrectShorter.
  ///
  /// In zh, this message translates to:
  /// **'更短一点'**
  String get auroraCorrectShorter;

  /// No description provided for @auroraCorrectDirect.
  ///
  /// In zh, this message translates to:
  /// **'直接出题'**
  String get auroraCorrectDirect;

  /// No description provided for @auroraCorrectRecalibrate.
  ///
  /// In zh, this message translates to:
  /// **'重新校准'**
  String get auroraCorrectRecalibrate;

  /// No description provided for @auroraSourceBadge.
  ///
  /// In zh, this message translates to:
  /// **'基于：{source}'**
  String auroraSourceBadge(Object source);

  /// No description provided for @auroraJudgmentTag.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 判断'**
  String get auroraJudgmentTag;

  /// No description provided for @auroraPhaseDiagnosis.
  ///
  /// In zh, this message translates to:
  /// **'诊断'**
  String get auroraPhaseDiagnosis;

  /// No description provided for @auroraPhaseStrategy.
  ///
  /// In zh, this message translates to:
  /// **'策略'**
  String get auroraPhaseStrategy;

  /// No description provided for @auroraPhaseExecution.
  ///
  /// In zh, this message translates to:
  /// **'执行'**
  String get auroraPhaseExecution;

  /// No description provided for @auroraPhaseCheckpoint.
  ///
  /// In zh, this message translates to:
  /// **'检查点'**
  String get auroraPhaseCheckpoint;

  /// No description provided for @auroraInputHint.
  ///
  /// In zh, this message translates to:
  /// **'告诉 Sparkle 任何想法...'**
  String get auroraInputHint;

  /// No description provided for @auroraBandSensing.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 轻量感知中'**
  String get auroraBandSensing;

  /// No description provided for @auroraBandCalibrated.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 已校准'**
  String get auroraBandCalibrated;

  /// No description provided for @auroraBandRiskFound.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 发现策略风险'**
  String get auroraBandRiskFound;

  /// No description provided for @auroraBandNeedsConfirm.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 需要确认一个判断'**
  String get auroraBandNeedsConfirm;

  /// No description provided for @auroraBandCalibrationAvailable.
  ///
  /// In zh, this message translates to:
  /// **'深度校准可用'**
  String get auroraBandCalibrationAvailable;

  /// No description provided for @auroraBandCoolingDown.
  ///
  /// In zh, this message translates to:
  /// **'Aurora 校准冷却中'**
  String get auroraBandCoolingDown;

  /// No description provided for @auroraWakeAvailable.
  ///
  /// In zh, this message translates to:
  /// **'深度校准可用（今日还剩 {count} 次）'**
  String auroraWakeAvailable(Object count);

  /// No description provided for @auroraWakeCooling.
  ///
  /// In zh, this message translates to:
  /// **'校准冷却中 · 还需 {minutes} 分钟'**
  String auroraWakeCooling(Object minutes);

  /// No description provided for @auroraWakeQuickFallback.
  ///
  /// In zh, this message translates to:
  /// **'快速校准'**
  String get auroraWakeQuickFallback;

  /// No description provided for @auroraWakeViewUpdates.
  ///
  /// In zh, this message translates to:
  /// **'查看刚才更新了什么'**
  String get auroraWakeViewUpdates;
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
