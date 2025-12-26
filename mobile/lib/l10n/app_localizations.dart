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
