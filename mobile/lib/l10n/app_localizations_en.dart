// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Sparkle';

  @override
  String get home => 'Cockpit';

  @override
  String get community => 'Community';

  @override
  String get knowledgeGalaxy => 'Knowledge Galaxy';

  @override
  String get profile => 'Profile';

  @override
  String get tasks => 'Tasks';

  @override
  String get chat => 'Chat';

  @override
  String get plans => 'Plans';

  @override
  String get galaxy => 'Galaxy';

  @override
  String get login => 'Login';

  @override
  String get register => 'Register';

  @override
  String get username => 'Username';

  @override
  String get password => 'Password';

  @override
  String get email => 'Email';

  @override
  String get nickname => 'Nickname';

  @override
  String get noAccount => 'Don\'t have an account?';

  @override
  String get hasAccount => 'Already have an account?';

  @override
  String get loginFailed => 'Login Failed';

  @override
  String get registerFailed => 'Registration Failed';

  @override
  String get weeklyAgenda => 'Weekly Agenda';

  @override
  String get agendaBusy => 'Busy';

  @override
  String get agendaFragmented => 'Fragmented';

  @override
  String get agendaRelax => 'Relax';

  @override
  String get learningMode => 'Learning Mode';

  @override
  String get depthPreference => 'Depth Preference';

  @override
  String get curiosityPreference => 'Curiosity Preference';

  @override
  String get settings => 'Settings';

  @override
  String get language => 'Language';

  @override
  String get languageChinese => '简体中文';

  @override
  String get languageEnglish => 'English';

  @override
  String get schedulePreferences => 'Schedule Preferences';

  @override
  String get notificationSettings => 'Notification Settings';

  @override
  String get theme => 'Theme';

  @override
  String get darkMode => 'Dark Mode';

  @override
  String get lightMode => 'Light Mode';

  @override
  String get followSystem => 'System';

  @override
  String get interactionSettings => 'Interaction Settings';

  @override
  String get enterToSend => 'Press Enter to Send';

  @override
  String get enterToSendDescription =>
      'Press the Enter key in the chat box to send messages directly';

  @override
  String get refresh => 'Refresh';

  @override
  String get chatAiSystemSettings => 'AI system settings';

  @override
  String get sensoryFeedbackSectionTitle => 'Sensory Feedback';

  @override
  String get sensoryFeedbackSectionSubtitle =>
      'Control interaction sounds, achievement feedback, and haptics in one place';

  @override
  String get sensoryFeedbackLoadingSubtitle =>
      'Loading sensory feedback preferences...';

  @override
  String get sensorySoundTitle => 'Sound Feedback';

  @override
  String get sensorySoundSubtitle =>
      'Turn off all Sensory sounds and ambient audio';

  @override
  String get sensoryHapticTitle => 'Haptic Feedback';

  @override
  String get sensoryHapticSubtitle =>
      'Turn off haptics for achievements, galaxy interactions, and more';

  @override
  String get sensoryAmbientSceneTitle => 'Focus Ambience';

  @override
  String get sensoryAmbientVolumeTitle => 'Ambient Volume';

  @override
  String get bgmSectionTitle => 'Background Music';

  @override
  String get bgmSectionSubtitle =>
      'Auto-switch ambience by page, with piano, airy, or warm preferences';

  @override
  String get bgmLoadingSubtitle => 'Loading music preferences...';

  @override
  String get bgmEnabledTitle => 'Enable Background Music';

  @override
  String get bgmEnabledSubtitle =>
      'Automatically switch BGM when entering different pages';

  @override
  String get bgmPlaybackStrategyTitle => 'Playback Strategy';

  @override
  String get themeAiSectionSubtitle =>
      'Theme, chat options, AI tier, and motion intensity';

  @override
  String get aiReasoningTitle => 'AI Tier';

  @override
  String get aiReasoningSubtitle =>
      'Fast is quicker, Balanced is recommended, Deep is strongest for analysis';

  @override
  String get aiReasoningFastLabel => 'Fast';

  @override
  String get aiReasoningBalancedLabel => 'Balanced';

  @override
  String get aiReasoningDeepLabel => 'Deep';

  @override
  String get showChatContextToggleTitle => 'Show chat top controls';

  @override
  String get showChatContextToggleSubtitle =>
      'Control the expandable plan and tier selectors on the chat page';

  @override
  String get showChatPredictionDockTitle => 'Show chat prediction dock';

  @override
  String get showChatPredictionDockSubtitle =>
      'Control behavior predictions and quick suggestions above the input';

  @override
  String get showChatTransparencyCapsuleTitle => 'Show AI transparency capsule';

  @override
  String get showChatTransparencyCapsuleSubtitle =>
      'Control the AI completion and transparency capsule at the bottom of chat';

  @override
  String get taskCard => 'Task Card';

  @override
  String get planCard => 'Plan Card';

  @override
  String get startTask => 'Start Task';

  @override
  String get viewDetails => 'View Details';

  @override
  String get finishTask => 'Finish Task';

  @override
  String get abandonTask => 'Abandon Task';

  @override
  String get estimatedTime => 'Estimated Time';

  @override
  String get difficulty => 'Difficulty';

  @override
  String get exploreGalaxy => 'Explore Galaxy';

  @override
  String get searchNodes => 'Search Nodes';

  @override
  String get sparkNode => 'Spark Node';

  @override
  String get masteryScore => 'Mastery';

  @override
  String get reviewSuggestion => 'Review Suggestion';

  @override
  String get aiTutor => 'AI Tutor';

  @override
  String get send => 'Send';

  @override
  String get typeMessage => 'Type a message...';

  @override
  String get logout => 'Logout';

  @override
  String get confirmLogout => 'Are you sure you want to logout?';

  @override
  String get cancel => 'Cancel';

  @override
  String get confirm => 'Confirm';

  @override
  String get errorConnectionFailed =>
      'The network seems a bit sleepy, please check your connection~';

  @override
  String get errorConnectionTimeout =>
      'Request timed out, let\'s try again in a bit';

  @override
  String get errorServerIssue =>
      'The server is taking a small nap, please try again later';

  @override
  String get errorRateLimit =>
      'Doing things too fast! Take a little break first~';

  @override
  String get errorAuthRequired => 'Please sign in to enjoy this feature';

  @override
  String get errorTokenExpired =>
      'Your session has expired, please sign in again~';

  @override
  String get errorNotFound =>
      'Couldn\'t find what you\'re looking for, maybe try another keyword?';

  @override
  String get errorEmptyState =>
      'It\'s a bit empty here, why not add something?';

  @override
  String get retry => 'Retry';

  @override
  String get back => 'Back';

  @override
  String get welcomeSubtitle => 'Ignite your learning potential';

  @override
  String get pleaseEnterUsername => 'Please enter your username or email';

  @override
  String get pleaseEnterPassword => 'Please enter your password';

  @override
  String get orText => 'OR';

  @override
  String get continueAsGuest => 'Continue as Guest';

  @override
  String get joinSparkle => 'Join Sparkle';

  @override
  String get usernameMinLength => 'Username must be at least 3 characters';

  @override
  String get invalidEmail => 'Please enter a valid email';

  @override
  String get passwordMinLength => 'Password must be at least 6 characters';

  @override
  String get confirmPassword => 'Confirm Password';

  @override
  String get passwordsDoNotMatch => 'Passwords do not match';

  @override
  String get google => 'Google';

  @override
  String get apple => 'Apple';

  @override
  String get wechat => 'WeChat';

  @override
  String get createGrowthPlan => 'Create Growth Plan';

  @override
  String get createSprintPlan => 'Create Sprint Plan';

  @override
  String get planCreateTitle => 'Create Plan';

  @override
  String get planCreateSuccess => 'Plan created successfully';

  @override
  String planCreateFailed(Object error) {
    return 'Failed to create plan: $error';
  }

  @override
  String get planNameLabel => 'Plan Name';

  @override
  String get planNameHint => 'Enter plan name...';

  @override
  String get planNameRequired => 'Please enter plan name';

  @override
  String get planDescLabel => 'Description';

  @override
  String get planDescHint => 'Describe your plan goals...';

  @override
  String get planSubjectLabel => 'Subject';

  @override
  String get planSubjectHint => 'e.g., Computer Science, English...';

  @override
  String get planTargetDateLabel => 'Target Date';

  @override
  String get planTargetDateUnset => 'No target date set';

  @override
  String get planDailyMinutesLabel => 'Daily Available Time';

  @override
  String get planDailyMinutesHint => 'How many minutes per day';

  @override
  String get planPriorityLabel => 'Priority';

  @override
  String get planPriorityCritical => 'Critical';

  @override
  String get planPriorityHigh => 'High';

  @override
  String get planPriorityNormal => 'Normal';

  @override
  String get planPriorityLow => 'Low';

  @override
  String get planCreating => 'Creating...';

  @override
  String get planCreateAction => 'Create Plan';

  @override
  String get featureComingSoon => 'Exciting features are coming soon';

  @override
  String get stayTuned => 'Stay tuned~';

  @override
  String get aiNudgeGentle => 'Take a break, you\'ll be more productive';

  @override
  String get aiNudgeFocus => 'Stay focused, you\'re in the zone!';

  @override
  String get qwen3CognitiveStatus => 'Qwen3 Cognitive Status';

  @override
  String get winStreak => 'Win Streak';

  @override
  String get myPersona => 'My Persona';

  @override
  String get systemActivity => 'System Activity';

  @override
  String get memoryControl => 'Memory Control';

  @override
  String get brightness => 'Brightness';

  @override
  String get dragToAdjust =>
      'Drag the control points to adjust your AI tutoring style';

  @override
  String get capsuleGeneration => 'Capsule Generation';

  @override
  String get adjustAndGenerate =>
      'Adjust preferences and generate exclusive curiosity capsules';

  @override
  String get generateNow => 'Generate Capsule Now';

  @override
  String get generating => 'Generating...';

  @override
  String get selectTimeSlots =>
      'Select time slots: Red for busy, Green for fragmented (AI reminders), Blue for rest';

  @override
  String get enableNotifications => 'Enable Notifications';

  @override
  String get smartReminders => 'Smart Fragment Time Reminders';

  @override
  String get pushMicroTasks => 'Push micro-tasks during green time slots';

  @override
  String get transparentMode => 'Transparent Mode';

  @override
  String get enableTransparentMode => 'Enable Transparent Mode';

  @override
  String get showStatusOverview =>
      'Show status and resource consumption overview';

  @override
  String get transparencyLevel => 'Transparency Level';

  @override
  String get basic => 'Basic';

  @override
  String get standard => 'Standard';

  @override
  String get advanced => 'Advanced';

  @override
  String get systemFeedback => 'System Feedback Level';

  @override
  String get controlUpdateDetails =>
      'Control the detail level of system update notifications';

  @override
  String get silent => 'Silent';

  @override
  String get summary => 'Summary';

  @override
  String get detailed => 'Detailed';

  @override
  String get sync => 'Sync';

  @override
  String get syncCenter => 'Sync Center';

  @override
  String get viewOfflineQueue => 'View offline queue status and retry';

  @override
  String get capsuleTaskCreated => '✨ Capsule generation task created';

  @override
  String get generationFailed => 'Generation failed, please try again later';

  @override
  String generationFailedWithDetail(Object error) {
    return 'Generation failed: $error';
  }

  @override
  String get version => 'Sparkle v2.1.0-stable\n© 2025 Sparkle Team';

  @override
  String get editPlan => 'Edit Plan';

  @override
  String get planEditInProgress => 'Plan edit feature is in development';

  @override
  String get planId => 'Plan ID';

  @override
  String get featureInDevelopment => 'Coming soon...';

  @override
  String get sprintHistory => 'Sprint History';

  @override
  String get noSprintHistory => 'No sprint history yet';

  @override
  String get loadingFailed => 'Loading Failed';

  @override
  String get completionProgress => 'Completion Progress';

  @override
  String tasksCompleted(Object completed, Object total) {
    return '$completed/$total tasks';
  }

  @override
  String get sprintCompleted => '✅ Sprint completed and archived';

  @override
  String sprintExtended(Object days) {
    return 'Sprint extended by $days days';
  }

  @override
  String get sprintAbandoned => 'Sprint abandoned';

  @override
  String get noActiveSprint => 'No active sprint';

  @override
  String get networkErrorRetry => 'Network error, please retry';

  @override
  String get submitFailed => 'Submission failed, please retry';

  @override
  String get loadHistoryFailed => 'Failed to load history';

  @override
  String get loadMoreFailed => 'Failed to load more messages';

  @override
  String get sendFailed => 'Failed to send, please retry';

  @override
  String get view => 'View';

  @override
  String get ongoing => 'Ongoing';

  @override
  String get errorTitle => 'Oops, something went wrong';

  @override
  String get warningTitle => 'Friendly Reminder';

  @override
  String get infoTitle => 'Quick Tip';

  @override
  String get aiStatusThinking => 'Thinking...';

  @override
  String get aiStatusGenerating => 'Generating...';

  @override
  String get aiStatusExecutingTool => 'Using tools...';

  @override
  String get aiStatusSearching => 'Searching...';

  @override
  String get aiStatusProcessing => 'Processing...';

  @override
  String get aiStatusAnalyzing => 'Analyzing...';

  @override
  String get aiStatusPlanning => 'Planning...';

  @override
  String get aiStatusReviewing => 'Reviewing...';

  @override
  String get aiStatusWaiting => 'Waiting for input...';

  @override
  String get aiStatusReady => 'Ready';

  @override
  String get aiStatusError => 'Error occurred';

  @override
  String get aiStatusIdle => 'Idle';

  @override
  String get aiStatusConnecting => 'Connecting...';

  @override
  String get aiStatusReconnecting => 'Reconnecting...';

  @override
  String get aiStatusDisconnected => 'Disconnected';

  @override
  String get levelPrefix => 'Lv.';

  @override
  String get toolsSpeechToTextTitle => 'Speech to Text';

  @override
  String get toolsSpeechToTextDesc => 'Real-time speech transcription';

  @override
  String get toolsCalculatorTitle => 'Calculator';

  @override
  String get toolsCalculatorDesc => 'Quick calculations and math';

  @override
  String get toolsFocusTimerTitle => 'Focus Timer';

  @override
  String get toolsFocusTimerDesc => 'Pomodoro-style focus sessions';

  @override
  String get toolsNotesTitle => 'Quick Notes';

  @override
  String get toolsNotesDesc => 'Capture thoughts instantly';

  @override
  String get toolsTranslatorTitle => 'Translator';

  @override
  String get toolsTranslatorDesc => 'Translate between languages';

  @override
  String get toolsFlashCapsuleTitle => 'Flash Capsule';

  @override
  String get toolsFlashCapsuleDesc => 'Quick learning capsules';

  @override
  String get toolsFocusStatsTitle => 'Focus Stats';

  @override
  String get toolsFocusStatsDesc => 'Track your focus sessions';

  @override
  String get toolsVocabularyLookupTitle => 'Vocabulary Lookup';

  @override
  String get toolsVocabularyLookupDesc => 'Look up word definitions';

  @override
  String get toolsWordbookTitle => 'Word Book';

  @override
  String get toolsWordbookDesc => 'Your personal vocabulary';

  @override
  String get toolsBreathingTitle => 'Breathing Exercise';

  @override
  String get toolsBreathingDesc => 'Guided breathing for relaxation';

  @override
  String get toolsDocumentCleanerTitle => 'Document Cleaner';

  @override
  String get toolsDocumentCleanerDesc => 'Clean and format documents';

  @override
  String get toolsPatternListTitle => 'Pattern List';

  @override
  String get toolsPatternListDesc => 'View learning patterns';

  @override
  String get toolsCuriosityCapsuleTitle => 'Curiosity Capsule';

  @override
  String get toolsCuriosityCapsuleDesc => 'AI-generated curiosity content';

  @override
  String get toolsCognitiveHubTitle => 'Cognitive Tools';

  @override
  String get toolsCognitiveHubDesc => 'Explore cognitive tools';

  @override
  String get toolsSearchPlaceholder => 'Search tools...';

  @override
  String get toolsFocusModeTitle => 'Focus Mode';

  @override
  String get toolsFocusModeDesc => 'Enter task focus interface';

  @override
  String get toolsPomodoroTitle => 'Pomodoro Timer';

  @override
  String get toolsPomodoroDesc => '25-minute work cycles';

  @override
  String get toolsErrorBookTitle => 'Error Book';

  @override
  String get toolsErrorBookDesc => 'Browse and manage error records';

  @override
  String get toolsReviewPlanTitle => 'Review Plan';

  @override
  String get toolsReviewPlanDesc => 'View today\'s review plan';

  @override
  String get toolsLearningForecastTitle => 'Learning Forecast';

  @override
  String get toolsLearningForecastDesc => 'View learning trends and risks';

  @override
  String get toolsCognitivePatternsTitle => 'Cognitive Patterns';

  @override
  String get toolsCognitivePatternsDesc =>
      'View behavior patterns and insights';

  @override
  String get chatModeStandard => 'Standard chat';

  @override
  String get chatModeDeep => 'Deep Focus';

  @override
  String get chatModeCreative => 'Creative';

  @override
  String get chatModeAnalytical => 'Analytical';

  @override
  String get chatModeStandardDesc => 'Standard AI conversation mode';

  @override
  String get chatModeDeepAnalysis => 'Deep Analysis';

  @override
  String get chatModeDeepAnalysisDesc => 'Multi-expert collaborative analysis';

  @override
  String get chatModeStudyPlan => 'Study Plan';

  @override
  String get chatModeStudyPlanDesc => 'Task breakdown and learning plan';

  @override
  String get chatModeErrorDiagnosis => 'Error Diagnosis';

  @override
  String get chatModeErrorDiagnosisDesc => 'Error diagnosis and analysis loop';

  @override
  String get chatModeExpertAuto => 'Expert Auto';

  @override
  String get chatModeExpertAutoDesc => 'Auto-select best expert';

  @override
  String get chatModeExpertDirect => 'Expert direct';

  @override
  String get chatModeExpertDirectDesc => 'Direct expert consultation';

  @override
  String get chatModeSelectorTitle => 'Choose AI Collaboration Mode';

  @override
  String chatModeActivated(Object mode) {
    return '$mode mode activated';
  }

  @override
  String get chatPlanContextSwitched => 'Plan context switched';

  @override
  String get chatPlanSwitchTitle => 'Switch Plan Context';

  @override
  String get chatPlanSwitchMessage =>
      'Switching plans will clear current conversation. Continue?';

  @override
  String chatPlanSwitchUnsavedCount(Object count) {
    return '$count unsaved messages';
  }

  @override
  String get chatReconnecting => 'Reconnecting...';

  @override
  String get chatReconnected => 'Reconnected';

  @override
  String get chatConnectionFailed => 'Connection failed';

  @override
  String get aiCollabModeTitle => 'AI Collaboration';

  @override
  String get switchAgentModeSemantics => 'Switch agent mode';

  @override
  String chatDagLayerProgress(Object current, Object total) {
    return 'Layer $current/$total';
  }

  @override
  String get chatDagProcessing => 'Processing dependencies...';

  @override
  String get chatDagCompleted => 'Analysis complete';

  @override
  String get chatInputPlaceholder => 'Type a message...';

  @override
  String get chatInputAttachment => 'Attach';

  @override
  String get chatInputVoice => 'Voice';

  @override
  String get chatInputShare => 'Share';

  @override
  String get chatInputTapToShare => 'Tap to select content to share';

  @override
  String get chatVoiceInput => 'Voice Input';

  @override
  String get chatAttachment => 'Attach File';

  @override
  String get chatEmoji => 'Emoji';

  @override
  String get chatSend => 'Send';

  @override
  String get chatTyping => 'AI is typing...';

  @override
  String get chatOnline => 'Online';

  @override
  String get chatOffline => 'Offline';

  @override
  String get chatReconnect => 'Reconnect';

  @override
  String get chatClearHistory => 'Clear History';

  @override
  String get chatExportChat => 'Export Chat';

  @override
  String get chatNewChat => 'New Chat';

  @override
  String get chatHistory => 'Chat History';

  @override
  String get chatNoHistory => 'No chat history';

  @override
  String get chatDeleteConfirm => 'Delete this chat?';

  @override
  String get chatDeleted => 'Chat deleted';

  @override
  String get chatCopied => 'Copied to clipboard';

  @override
  String get chatRegenerate => 'Regenerate';

  @override
  String get chatCopy => 'Copy';

  @override
  String get chatShare => 'Share';

  @override
  String get chatCharacters => 'chars';

  @override
  String get chatWords => 'words';

  @override
  String get chatFeedback => 'Feedback';

  @override
  String get chatReportIssue => 'Report Issue';

  @override
  String get chatMessageTooLong => 'Message is too long';

  @override
  String get chatEmptyMessage => 'Cannot send empty message';

  @override
  String get chatConnectionLost => 'Connection lost, retrying...';

  @override
  String get chatConnectionRestored => 'Connection restored';

  @override
  String get chatWelcome => 'Hello! How can I help you today?';

  @override
  String get chatWelcomeSubtitle => 'What do you want to do today?';

  @override
  String get chatSuggestion1 => 'Help me plan my study';

  @override
  String get chatSuggestion2 => 'Explain a concept';

  @override
  String get chatSuggestion3 => 'Review my progress';

  @override
  String get chatSuggestion4 => 'Suggest learning resources';

  @override
  String chatAgentSwitched(Object agent) {
    return 'Switched to $agent';
  }

  @override
  String get achievementTitle => 'Achievements';

  @override
  String get achievementUnlocked => 'Achievement Unlocked!';

  @override
  String get achievementLocked => 'Locked';

  @override
  String get achievementProgress => 'Progress';

  @override
  String get achievementRarityCommon => 'Common';

  @override
  String get achievementRarityRare => 'Rare';

  @override
  String get achievementRarityEpic => 'Epic';

  @override
  String get achievementRarityLegendary => 'Legendary';

  @override
  String get achievementTypeStreak => 'Streak';

  @override
  String get achievementTypeMilestone => 'Milestone';

  @override
  String get achievementTypeChallenge => 'Challenge';

  @override
  String get achievementTypeHidden => 'Hidden';

  @override
  String get achievementTypeSpecial => 'Special';

  @override
  String achievementPoints(Object points) {
    return '$points points';
  }

  @override
  String achievementEarned(Object date) {
    return 'Earned on $date';
  }

  @override
  String get achievementClose => 'Close';

  @override
  String get achievementShare => 'Share';

  @override
  String get achievementViewAll => 'View All';

  @override
  String get achievementNoUnlocked => 'No achievements unlocked yet';

  @override
  String get achievementKeepGoing => 'Keep going to unlock more!';

  @override
  String get achievementStatsTotal => 'Total';

  @override
  String get achievementStatsUnlocked => 'Unlocked';

  @override
  String get achievementStatsPoints => 'Points';

  @override
  String get achievementStatsStreak => 'Day Streak';

  @override
  String get achievementNew => 'New!';

  @override
  String get achievementSearch => 'Search achievements';

  @override
  String get achievementFilter => 'Filter';

  @override
  String get achievementFilterActive => 'Filtering';

  @override
  String get achievementAll => 'All';

  @override
  String get achievementStatusUnlocked => 'Unlocked';

  @override
  String get achievementStatusLocked => 'Locked';

  @override
  String get achievementStatusInProgress => 'In Progress';

  @override
  String get achievementCategoryStreak => 'Streak';

  @override
  String get achievementCategoryMilestone => 'Milestone';

  @override
  String get achievementCategoryMastery => 'Mastery';

  @override
  String get achievementCategoryExploration => 'Exploration';

  @override
  String get achievementCategoryTask => 'Tasks';

  @override
  String get achievementNoMatch => 'No matching achievements found';

  @override
  String get achievementAdjustFilter => 'Try adjusting your filters';

  @override
  String get achievementFilterSheet => 'Filter Achievements';

  @override
  String get achievementRarity => 'Rarity';

  @override
  String get achievementStatus => 'Status';

  @override
  String get achievementApplyFilter => 'Apply Filters';

  @override
  String get achievementDescription => 'Description';

  @override
  String get achievementNoDescription => 'No description yet';

  @override
  String get achievementPrerequisites => 'Prerequisites';

  @override
  String get achievementPrerequisitesHint =>
      'Complete these achievements first:';

  @override
  String get achievementRewards => 'Rewards';

  @override
  String get achievementUnlockRewards => 'Unlock Rewards';

  @override
  String achievementRewardPhotons(Object count) {
    return '$count Photons';
  }

  @override
  String get achievementRewardTitle => 'Title';

  @override
  String get achievementRewardSkin => 'Galaxy Skin';

  @override
  String achievementRewardXp(Object count) {
    return '$count XP';
  }

  @override
  String get achievementRewardMystery => 'Mystery Reward';

  @override
  String get achievementStatType => 'Type';

  @override
  String get achievementCategory => 'Category';

  @override
  String get achievementUnlockedAt => 'Unlocked At';

  @override
  String get achievementShareCount => 'Share Count';

  @override
  String get achievementUnlockRank => 'Unlock Rank';

  @override
  String get achievementFirstUnlocker => 'First Unlocker';

  @override
  String get achievementNotFound => 'Achievement not found';

  @override
  String get achievementShareLocked => 'Unlock this achievement to share it';

  @override
  String get achievementCompletionRate => 'Completion Rate';

  @override
  String get achievementTotalLabel => 'Total Achievements';

  @override
  String get achievementPhotons => 'Photons';

  @override
  String get achievementOverallProgress => 'Overall Progress';

  @override
  String get achievementRarityDistribution => 'Rarity Distribution';

  @override
  String achievementHiddenCount(Object count) {
    return 'Hidden: $count';
  }

  @override
  String get achievementTypeMastery => 'Mastery';

  @override
  String get achievementTypeTaskComplete => 'Tasks';

  @override
  String get achievementTypeNodeExplore => 'Exploration';

  @override
  String get achievementTypeStudyTime => 'Study Time';

  @override
  String get achievementTypeSocial => 'Social';

  @override
  String get achievementTypeContract => 'Contract';

  @override
  String get achievementTypeSprint => 'Sprint';

  @override
  String get achievementAlmostThere => 'Almost There';

  @override
  String achievementNeedMore(Object action) {
    return '$action more to unlock';
  }

  @override
  String achievementCompleteTasks(Object count) {
    return 'Complete $count tasks';
  }

  @override
  String achievementUnlockNodes(Object count) {
    return 'Unlock $count nodes';
  }

  @override
  String achievementChatCount(Object count) {
    return 'Chat $count times';
  }

  @override
  String achievementCheckinDays(Object count) {
    return 'Check in $count days';
  }

  @override
  String achievementCreatePlans(Object count) {
    return 'Create $count plans';
  }

  @override
  String achievementProgressGeneric(Object count) {
    return '$count% progress';
  }

  @override
  String get achievementLimitedTitle => 'Limited-time';

  @override
  String get achievementLimitedSubtitle => 'Available during the event';

  @override
  String get achievementLimitedTime => 'Limited';

  @override
  String get achievementEventWindow => 'Event Window';

  @override
  String get achievementEventStatusUpcoming => 'Upcoming';

  @override
  String get achievementEventStatusLive => 'Live';

  @override
  String get achievementEventStatusEnded => 'Ended';

  @override
  String achievementEventStartsAt(String time) {
    return 'Starts $time';
  }

  @override
  String achievementEventEndsAt(String time) {
    return 'Ends $time';
  }

  @override
  String achievementEventEndsIn(String time) {
    return 'Ends $time';
  }

  @override
  String get achievementEventEnded => 'Event ended';

  @override
  String get achievementRewardVisualElement => 'Visual Effect';

  @override
  String get achievementUnlockToEquip => 'Unlock to equip';

  @override
  String get achievementEquipAction => 'Equip';

  @override
  String get achievementEquipped => 'Equipped';

  @override
  String get achievementMapTitle => 'Achievement Map';

  @override
  String get achievementMapSubtitle => 'Explore achievement paths';

  @override
  String get achievementMapEmpty => 'No map nodes yet';

  @override
  String get contractEntryTitle => 'Contracts';

  @override
  String get contractEntrySubtitle => 'Create a study challenge';

  @override
  String get contractTitle => 'Study Contract';

  @override
  String get contractCreateTitle => 'Create Contract';

  @override
  String get contractCreateSubtitle => 'Set a streak goal and stake photons';

  @override
  String get contractTargetMinutes => 'Daily minutes';

  @override
  String get contractTargetDays => 'Target days';

  @override
  String get contractPhotonStake => 'Photon stake';

  @override
  String get contractCreateAction => 'Create Contract';

  @override
  String get contractActiveTitle => 'Active Contract';

  @override
  String contractProgressLabel(int current, int target) {
    return '$current/$target days completed';
  }

  @override
  String get contractDailyTarget => 'Daily target';

  @override
  String contractMinutesTarget(int current, int target) {
    return '$current/$target min';
  }

  @override
  String get contractEndsAt => 'Ends on';

  @override
  String get contractCancelAction => 'Cancel Contract';

  @override
  String get contractInputInvalid => 'Please enter valid contract values';

  @override
  String get contractCreateFailed => 'Failed to create contract';

  @override
  String get contractCreateSuccess => 'Contract created';

  @override
  String get contractCancelSuccess => 'Contract canceled';

  @override
  String get contractCancelFailed => 'Failed to cancel contract';

  @override
  String get contractCountdown => 'Countdown';

  @override
  String contractDaysRemaining(int days) {
    return '$days days remaining';
  }

  @override
  String get contractDeadlineReached => 'Deadline reached';

  @override
  String get contractRewardMultiplier => 'Reward Multiplier';

  @override
  String get contractCreatedCelebration => 'Contract Created!';

  @override
  String get streakCurrentLabel => 'Current Streak';

  @override
  String get streakBestRecord => 'Best Record';

  @override
  String get streakTotalCheckin => 'Total Check-ins';

  @override
  String get streakFreezeUsed => 'Freeze Used';

  @override
  String get streakCalendarTitle => 'Streak Calendar';

  @override
  String streakCalendarRange(int days) {
    return 'Last $days days';
  }

  @override
  String get streakHistoryEmpty => 'No streak history yet';

  @override
  String get streakStatusActive => 'Active';

  @override
  String get streakStatusFrozen => 'Frozen';

  @override
  String get streakStatusMissed => 'Missed';

  @override
  String get streakRiskNoFreeze =>
      'No freeze charges left. A missed day will break your streak.';

  @override
  String get streakRiskLowFreeze =>
      'Only 1 freeze charge left. Consider refilling.';

  @override
  String get streakShopTitle => 'Need more freeze charges?';

  @override
  String get streakShopSubtitle => 'Visit the Photon Shop to stock up.';

  @override
  String get streakShopAction => 'Open Shop';

  @override
  String get streakDetails => 'Streak Details';

  @override
  String get dashboardCustomizeCards => 'Customizable Cards';

  @override
  String get dashboardEmptyHint =>
      'Keep at least one card. Changes are saved to local config immediately.';

  @override
  String get achievementViewStreakStatus =>
      'View achievements & learning streak';

  @override
  String get taskStatusPending => 'Pending';

  @override
  String get taskStatusInProgress => 'In Progress';

  @override
  String get taskStatusCompleted => 'Completed';

  @override
  String get taskStatusAbandoned => 'Abandoned';

  @override
  String get taskStatusPaused => 'Paused';

  @override
  String get taskActionStart => 'Start';

  @override
  String get taskActionPause => 'Pause';

  @override
  String get taskActionResume => 'Resume';

  @override
  String get taskActionComplete => 'Complete';

  @override
  String get taskActionAbandon => 'Abandon';

  @override
  String get taskActionEdit => 'Edit';

  @override
  String get taskActionDelete => 'Delete';

  @override
  String get taskPriorityHigh => 'High Priority';

  @override
  String get taskPriorityMedium => 'Medium Priority';

  @override
  String get taskPriorityLow => 'Low Priority';

  @override
  String get taskNoTasks => 'No tasks yet';

  @override
  String get taskAddNew => 'Add Task';

  @override
  String taskDueDate(Object date) {
    return 'Due $date';
  }

  @override
  String get taskOverdue => 'Overdue';

  @override
  String get taskDueToday => 'Due today';

  @override
  String get taskDueTomorrow => 'Due tomorrow';

  @override
  String get taskDueThisWeek => 'Due this week';

  @override
  String get taskCategoryWork => 'Work';

  @override
  String get taskCategoryStudy => 'Study';

  @override
  String get taskCategoryPersonal => 'Personal';

  @override
  String get taskCategoryHealth => 'Health';

  @override
  String get taskCategoryOther => 'Other';

  @override
  String get taskFilterAll => 'All';

  @override
  String get taskFilterToday => 'Today';

  @override
  String get taskFilterWeek => 'This Week';

  @override
  String get taskFilterCompleted => 'Completed';

  @override
  String get taskSortByDate => 'Sort by Date';

  @override
  String get taskSortByPriority => 'Sort by Priority';

  @override
  String get taskSortByName => 'Sort by Name';

  @override
  String taskCount(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count tasks',
      one: '1 task',
      zero: 'No tasks',
    );
    return '$_temp0';
  }

  @override
  String get focusTimerTitle => 'Focus Timer';

  @override
  String get focusTimerStart => 'Start Focus';

  @override
  String get focusTimerPause => 'Pause';

  @override
  String get focusTimerResume => 'Resume';

  @override
  String get focusTimerStop => 'Stop';

  @override
  String get focusTimerReset => 'Reset';

  @override
  String get focusTimerComplete => 'Session Complete!';

  @override
  String get focusTimerRemaining => 'Remaining';

  @override
  String get focusTimerElapsed => 'Elapsed';

  @override
  String focusTimerSession(Object current, Object total) {
    return 'Session $current/$total';
  }

  @override
  String get focusTimerBreak => 'Break Time';

  @override
  String get focusTimerShortBreak => 'Short Break';

  @override
  String get focusTimerLongBreak => 'Long Break';

  @override
  String focusTimerNextSession(Object time) {
    return 'Next session in $time';
  }

  @override
  String get focusTimerAutoStart => 'Auto-start next session';

  @override
  String get focusTimerSound => 'Notification Sound';

  @override
  String get focusTimerVolume => 'Volume';

  @override
  String get focusTimerDuration => 'Duration';

  @override
  String get focusTimerPreset25 => '25 min (Pomodoro)';

  @override
  String get focusTimerPreset45 => '45 min (Deep Focus)';

  @override
  String get focusTimerPreset60 => '60 min (Extended)';

  @override
  String get focusTimerCustom => 'Custom';

  @override
  String get focusStatsToday => 'Today';

  @override
  String get focusStatsWeek => 'This Week';

  @override
  String get focusStatsMonth => 'This Month';

  @override
  String get focusStatsTotal => 'Total';

  @override
  String focusStatsSessions(Object count) {
    return '$count sessions';
  }

  @override
  String focusStatsMinutes(Object count) {
    return '$count minutes';
  }

  @override
  String focusStatsHours(Object count) {
    return '$count hours';
  }

  @override
  String focusStatsStreak(Object count) {
    return '$count day streak';
  }

  @override
  String focusStatsBestDay(Object time) {
    return 'Best: $time';
  }

  @override
  String get focusStatsScreenTitle => 'Focus Statistics';

  @override
  String get focusStatsTrendTitle => 'Focus Trend';

  @override
  String focusStatsHeatmapRange(Object days) {
    return 'Activity Heatmap ($days days)';
  }

  @override
  String get focusStatsRecentSessionsTitle => 'Recent Sessions';

  @override
  String get focusStatsNoSessions => 'No focus sessions yet';

  @override
  String get focusStatsLoadMore => 'Load more';

  @override
  String focusStatsDurationTooltip(Object minutes) {
    return 'Focus duration: $minutes minutes';
  }

  @override
  String get focusStatsLegendLow => 'Low';

  @override
  String get focusStatsLegendHigh => 'High';

  @override
  String get focusStatsPomodoroLabel => 'Pomodoro';

  @override
  String get focusStatsStopwatchLabel => 'Timer';

  @override
  String get focusSelectTaskTitle => 'Select Focus Task';

  @override
  String get focusReadyPrompt => 'Ready to focus?';

  @override
  String get focusNoPendingTasks => 'No pending tasks';

  @override
  String get focusNoTasksButCanFocus => 'But you can still start focusing!';

  @override
  String get focusFreeFocus => 'Free Focus';

  @override
  String get focusStartNow => 'Start Now';

  @override
  String get focusCreateTask => 'Or create a new task';

  @override
  String get focusQuickStart => 'Quick Focus (25min)';

  @override
  String focusEstimated(Object minutes) {
    return 'Estimated $minutes minutes';
  }

  @override
  String get focusCoachTitle => 'AI Focus Coach';

  @override
  String focusCoachSummary(Object minutes, Object task) {
    return 'Task: $task · Focused for $minutes min';
  }

  @override
  String get focusCoachPromptBreakdown => 'Plan the next 15 min';

  @override
  String get focusCoachPromptRefocus => 'Refocus me';

  @override
  String get focusCoachPromptNextAction => 'Next action';

  @override
  String focusCoachPromptBreakdownMessage(Object task) {
    return 'Based on the task \"$task\", help me break down the next 15 minutes of focus.';
  }

  @override
  String get focusCoachPromptRefocusMessage =>
      'I just got distracted. Give me one short prompt to get back on track.';

  @override
  String get focusCoachPromptNextActionMessage =>
      'Summarize the next action for this task in a concise and clear way.';

  @override
  String get focusCoachEmpty => 'Ask whenever you need help.';

  @override
  String get focusCoachHint =>
      'Ask me how to stay focused or break down the next steps...';

  @override
  String get focusCandidateTitle => 'Smart Suggestions';

  @override
  String get focusCandidateSubtitle =>
      'Predicted from your current learning state';

  @override
  String get focusCandidateFooterHint =>
      'Swipe down to close · Ignore anything that isn\'t useful';

  @override
  String get focusCandidateDismiss => 'Not interested';

  @override
  String get focusCandidateAccept => 'Try it';

  @override
  String focusInterruptionDetected(Object count) {
    return 'Distraction detected (#$count)';
  }

  @override
  String get focusMindfulnessTitle => 'Mindfulness';

  @override
  String focusLoadFailed(Object error) {
    return 'Failed to load: $error';
  }

  @override
  String get focusReturnToTask => 'Back to Task';

  @override
  String get focusReturnToTaskTitle => 'Return to Task';

  @override
  String get focusReturnToTaskMessage =>
      'Your focus record will pause and you\'ll return to the task execution screen.';

  @override
  String get focusReturnToTaskConfirm => 'Return';

  @override
  String get focusExitMindfulness => 'Exit Mindfulness';

  @override
  String get focusDockMindfulness => 'Mindfulness';

  @override
  String get focusDockToolbox => 'Toolbox';

  @override
  String get focusReflectionTitle => 'Focus Complete';

  @override
  String get focusReflectionPrompt => 'How did this focus session feel?';

  @override
  String get focusReflectionNoteHint => 'Anything worth noting? (Optional)';

  @override
  String get focusReflectionSaved => 'Reflection saved to Cognitive Prism';

  @override
  String focusReflectionSaveFailed(Object error) {
    return 'Failed to save: $error';
  }

  @override
  String focusReflectionSummary(Object feeling, Object note) {
    return 'Focus reflection: status $feeling.\n$note';
  }

  @override
  String get focusReflectionMoodFlow => '🔥 Flow';

  @override
  String get focusReflectionMoodFocused => '🙂 Focused';

  @override
  String get focusReflectionMoodOkay => '😐 Okay';

  @override
  String get focusReflectionMoodDistracted => '😖 Distracted';

  @override
  String get focusReflectionMoodTired => '😫 Tired';

  @override
  String get focusExitTitleStep1 => 'Exit mindfulness mode?';

  @override
  String get focusExitTitleStep2 => 'About to leave';

  @override
  String get focusExitTitleStep3 => 'Final confirmation';

  @override
  String get focusExitMessageStep1 =>
      'You\'re in a focus state. Exiting now may break your momentum.';

  @override
  String focusExitMessageStep2(Object minutes) {
    return 'You\'ve focused for $minutes minutes. Are you sure you want to leave?';
  }

  @override
  String get focusExitMessageStep3 =>
      'Try to stay with it a bit longer. Leaving now will interrupt your focus record.';

  @override
  String get focusExitCancelStep1 => 'Keep focusing';

  @override
  String get focusExitConfirmStep1 => 'Exit';

  @override
  String get focusExitConfirmStep2 => 'Continue exit';

  @override
  String get focusExitConfirmStep3 => 'Confirm exit';

  @override
  String get streakTitle => 'Learning Streak';

  @override
  String streakDays(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count days',
      one: '1 day',
    );
    return '$_temp0';
  }

  @override
  String get streakMaxLabel => 'Best';

  @override
  String streakMax(Object count) {
    return 'Best $count';
  }

  @override
  String get streakTotalLabel => 'Total';

  @override
  String streakTotal(Object count) {
    return 'Total $count';
  }

  @override
  String get streakStartChallenge => 'Start';

  @override
  String get streakChallenge => 'Challenge';

  @override
  String get streakFreezeCharges => 'Freeze Charges';

  @override
  String get errorNetwork => 'Network error';

  @override
  String get errorNetworkDetail => 'Please check your internet connection';

  @override
  String get errorServer => 'Server error';

  @override
  String get errorServerDetail => 'Something went wrong on our end';

  @override
  String get errorUnknown => 'Unknown error';

  @override
  String get errorUnknownDetail => 'An unexpected error occurred';

  @override
  String get errorValidation => 'Validation error';

  @override
  String get errorValidationDetail => 'Please check your input';

  @override
  String get errorPermission => 'Permission denied';

  @override
  String get errorPermissionDetail =>
      'You don\'t have permission to perform this action';

  @override
  String get errorNotFoundTitle => 'Not found';

  @override
  String get errorNotFoundDetail => 'The requested resource was not found';

  @override
  String get errorTimeout => 'Request timeout';

  @override
  String get errorTimeoutDetail => 'The request took too long to complete';

  @override
  String get errorCancelled => 'Cancelled';

  @override
  String get errorCancelledDetail => 'The operation was cancelled';

  @override
  String get errorStorage => 'Storage error';

  @override
  String get errorStorageDetail => 'Failed to save data';

  @override
  String get errorSync => 'Sync error';

  @override
  String get errorSyncDetail => 'Failed to sync data';

  @override
  String get errorAuth => 'Authentication error';

  @override
  String get errorAuthDetail => 'Please sign in again';

  @override
  String get errorRateLimitTitle => 'Too many requests';

  @override
  String get errorRateLimitDetail => 'Please wait a moment and try again';

  @override
  String get errorMaintenance => 'Under maintenance';

  @override
  String get errorMaintenanceDetail =>
      'We\'re making things better, please check back soon';

  @override
  String get timeJustNow => 'Just now';

  @override
  String timeMinutesAgo(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count minutes ago',
      one: '1 minute ago',
    );
    return '$_temp0';
  }

  @override
  String timeHoursAgo(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count hours ago',
      one: '1 hour ago',
    );
    return '$_temp0';
  }

  @override
  String timeDaysAgo(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count days ago',
      one: '1 day ago',
    );
    return '$_temp0';
  }

  @override
  String timeWeeksAgo(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count weeks ago',
      one: '1 week ago',
    );
    return '$_temp0';
  }

  @override
  String timeMonthsAgo(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count months ago',
      one: '1 month ago',
    );
    return '$_temp0';
  }

  @override
  String timeYearsAgo(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count years ago',
      one: '1 year ago',
    );
    return '$_temp0';
  }

  @override
  String timeInMinutes(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count minutes',
      one: '1 minute',
    );
    return 'In $_temp0';
  }

  @override
  String timeInHours(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count hours',
      one: '1 hour',
    );
    return 'In $_temp0';
  }

  @override
  String timeInDays(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count days',
      one: '1 day',
    );
    return 'In $_temp0';
  }

  @override
  String timeInWeeks(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count weeks',
      one: '1 week',
    );
    return 'In $_temp0';
  }

  @override
  String timeInMonths(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count months',
      one: '1 month',
    );
    return 'In $_temp0';
  }

  @override
  String timeInYears(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count years',
      one: '1 year',
    );
    return 'In $_temp0';
  }

  @override
  String get timeToday => 'Today';

  @override
  String get timeYesterday => 'Yesterday';

  @override
  String get timeTomorrow => 'Tomorrow';

  @override
  String get timeThisWeek => 'This week';

  @override
  String get timeNextWeek => 'Next week';

  @override
  String get timeThisMonth => 'This month';

  @override
  String get timeLastMonth => 'Last month';

  @override
  String durationHours(Object count) {
    return '${count}h';
  }

  @override
  String durationMinutes(Object count) {
    return '${count}m';
  }

  @override
  String durationSeconds(Object count) {
    return '${count}s';
  }

  @override
  String durationHoursMinutes(Object hours, Object minutes) {
    return '${hours}h ${minutes}m';
  }

  @override
  String durationMinutesSeconds(Object minutes, Object seconds) {
    return '${minutes}m ${seconds}s';
  }

  @override
  String numberCount(num count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count items',
      one: '1 item',
      zero: 'None',
    );
    return '$_temp0';
  }

  @override
  String numberSelected(Object count) {
    return '$count selected';
  }

  @override
  String numberTotal(Object current, Object total) {
    return '$current of $total';
  }

  @override
  String numberPercent(Object value) {
    return '$value%';
  }

  @override
  String numberProgress(Object value) {
    return '$value% complete';
  }

  @override
  String numberK(Object value) {
    return '${value}K';
  }

  @override
  String numberM(Object value) {
    return '${value}M';
  }

  @override
  String numberB(Object value) {
    return '${value}B';
  }

  @override
  String get commonYes => 'Yes';

  @override
  String get commonNo => 'No';

  @override
  String get commonOk => 'OK';

  @override
  String get commonCancel => 'Cancel';

  @override
  String get commonSave => 'Save';

  @override
  String get commonDelete => 'Delete';

  @override
  String get commonEdit => 'Edit';

  @override
  String get commonAdd => 'Add';

  @override
  String get commonRemove => 'Remove';

  @override
  String get commonClear => 'Clear';

  @override
  String get commonReset => 'Reset';

  @override
  String get commonRefresh => 'Refresh';

  @override
  String get commonSearch => 'Search';

  @override
  String get commonFilter => 'Filter';

  @override
  String get commonSort => 'Sort';

  @override
  String get commonClose => 'Close';

  @override
  String get commonDismiss => 'Dismiss';

  @override
  String get commonApply => 'Apply';

  @override
  String get commonSubmit => 'Submit';

  @override
  String get commonContinue => 'Continue';

  @override
  String get commonSkip => 'Skip';

  @override
  String get commonNext => 'Next';

  @override
  String get commonPrevious => 'Previous';

  @override
  String get commonDone => 'Done';

  @override
  String get commonLoading => 'Loading...';

  @override
  String get commonSaving => 'Saving...';

  @override
  String get commonProcessing => 'Processing...';

  @override
  String get commonSuccess => 'Success';

  @override
  String get commonError => 'Error';

  @override
  String get commonWarning => 'Warning';

  @override
  String get commonInfo => 'Info';

  @override
  String get commonNoData => 'No data';

  @override
  String get commonNoResults => 'No results found';

  @override
  String get commonTryAgain => 'Try again';

  @override
  String get commonLearnMore => 'Learn more';

  @override
  String get commonSeeAll => 'See all';

  @override
  String get operationPreview => 'Operation preview:';

  @override
  String get commonShowLess => 'Show less';

  @override
  String get commonShowMore => 'Show more';

  @override
  String get commonCollapse => 'Collapse';

  @override
  String get commonExpand => 'Expand';

  @override
  String get commonRequired => 'Required';

  @override
  String get commonOptional => 'Optional';

  @override
  String get commonEnabled => 'Enabled';

  @override
  String get commonDisabled => 'Disabled';

  @override
  String get commonOn => 'On';

  @override
  String get commonOff => 'Off';

  @override
  String get commonActive => 'Active';

  @override
  String get commonInactive => 'Inactive';

  @override
  String get commonConnected => 'Connected';

  @override
  String get commonDisconnected => 'Disconnected';

  @override
  String get commonSyncing => 'Syncing...';

  @override
  String get commonSynced => 'Synced';

  @override
  String get commonOffline => 'Offline';

  @override
  String get commonOnline => 'Online';

  @override
  String get commonOperationWarning => 'Operation may not have succeeded';

  @override
  String get emptyStateNoTasksTitle => 'No tasks yet';

  @override
  String get emptyStateNoTasksDescription =>
      'Create your first learning task and get started.';

  @override
  String get emptyStateNoChatsTitle => 'Sparkle is ready';

  @override
  String get emptyStateNoChatsDescription =>
      'Ask anything and start the conversation.';

  @override
  String get emptyStateNoPlansTitle => 'No study plans yet';

  @override
  String get emptyStateNoPlansDescription =>
      'Create a plan and let AI help map the route.';

  @override
  String get emptyStateNoErrorsTitle => 'Looking good';

  @override
  String get emptyStateNoErrorsDescription =>
      'You don\'t have any error records yet.';

  @override
  String get emptyStateNoResultsTitle => 'No results found';

  @override
  String get emptyStateNoResultsDescription => 'Try a different keyword.';

  @override
  String emptyStateNoResultsQuery(Object query) {
    return 'No results related to \"$query\"';
  }

  @override
  String get emptyStateGeneralTitle => 'Nothing here yet';

  @override
  String get emptyStateGeneralDescription => 'Add something to get started.';

  @override
  String get emptyStateStartChatAction => 'Start chat';

  @override
  String get emptyStateCreatePlanAction => 'Create plan';

  @override
  String get voiceInputPermissionTitle => 'Microphone Access Needed';

  @override
  String get voiceInputPermissionContent =>
      'Allow microphone access to use voice input.';

  @override
  String get voiceInputOpenSettings => 'Open Settings';

  @override
  String get voiceInputNoPermission => 'Microphone permission is required.';

  @override
  String get voiceInputLoginRequired =>
      'Please sign in before using voice input.';

  @override
  String voiceInputStartFailed(Object error) {
    return 'Couldn\'t start recording: $error';
  }

  @override
  String get quickReplyTodayPlanLabel => 'Today plan';

  @override
  String get quickReplyTodayPlanMessage => 'What\'s my plan for today?';

  @override
  String get quickReplyReviewPlanLabel => 'Review plan';

  @override
  String get quickReplyReviewPlanMessage => 'Help me review today\'s plan.';

  @override
  String get quickReplyStartFocusLabel => 'Start focus';

  @override
  String get quickReplyStartFocusMessage => 'Start a focus session for me.';

  @override
  String get quickReplyAnalyzeErrorsLabel => 'Analyze errors';

  @override
  String get quickReplyAnalyzeErrorsMessage => 'Analyze my recent mistakes.';

  @override
  String get quickReplyLearningProgressLabel => 'Learning progress';

  @override
  String get quickReplyLearningProgressMessage =>
      'How is my learning progress recently?';

  @override
  String get quickReplyAddErrorLabel => 'Add error';

  @override
  String get quickReplyAddErrorMessage => 'Help me add a new mistake record.';

  @override
  String get quickReplyReviewErrorsLabel => 'Review errors';

  @override
  String get quickReplyReviewErrorsMessage => 'Let\'s review my mistake book.';

  @override
  String get quickReplyErrorStatsLabel => 'Error stats';

  @override
  String get quickReplyErrorStatsMessage => 'Show me my mistake statistics.';

  @override
  String get quickReplyWeakSubjectsLabel => 'Weak areas';

  @override
  String get quickReplyWeakSubjectsMessage =>
      'Which subjects are my weakest right now?';

  @override
  String get quickReplyExploreGalaxyLabel => 'Explore galaxy';

  @override
  String get quickReplyExploreGalaxyMessage =>
      'Take me to the knowledge galaxy.';

  @override
  String get quickReplyAddKnowledgeLabel => 'Add knowledge';

  @override
  String get quickReplyAddKnowledgeMessage =>
      'Help me add a new knowledge point.';

  @override
  String get quickReplyFindGapsLabel => 'Find gaps';

  @override
  String get quickReplyFindGapsMessage => 'Find gaps in my knowledge graph.';

  @override
  String get quickReplyGreetingLateNight =>
      'Still awake? Want me to help you wrap something up?';

  @override
  String get quickReplyGreetingMorning =>
      'Good morning. What do you want to start with today?';

  @override
  String get quickReplyGreetingNoon =>
      'It\'s noon. Want to tune today\'s rhythm?';

  @override
  String get quickReplyGreetingAfternoon =>
      'Good afternoon. Keep pushing or do a quick review?';

  @override
  String get quickReplyGreetingEvening =>
      'Good evening. Want to summarize today or plan tomorrow?';

  @override
  String get quickReplyGreetingNight =>
      'It\'s late. Want to finish up quickly or unwind a bit?';

  @override
  String get privateChatDefaultTitle => 'Chat';

  @override
  String get privateChatEmptyPrompt => 'Start the conversation.';

  @override
  String get chatDefaultGroupName => 'Group Chat';

  @override
  String get chatDefaultFriendName => 'Friend';

  @override
  String get shopTitle => 'Photon Shop';

  @override
  String get shopCategoryAll => 'All';

  @override
  String get shopCategorySkin => 'Skins';

  @override
  String get shopCategoryTitle => 'Titles';

  @override
  String get shopCategoryConsumable => 'Consumables';

  @override
  String get shopCategoryBoost => 'Boosts';

  @override
  String get shopCategoryVisualElement => 'Visual Elements';

  @override
  String get shopEmpty => 'No items yet';

  @override
  String shopPurchaseSuccess(Object name) {
    return 'Purchased $name successfully';
  }

  @override
  String get shopPurchaseFailed => 'Purchase failed';

  @override
  String get purchaseConfirmTitle => 'Confirm Purchase';

  @override
  String get shopPriceLabel => 'Price';

  @override
  String get shopBalanceLabel => 'Current Balance';

  @override
  String get shopBalanceAfterPurchase => 'Balance After Purchase';

  @override
  String get shopInsufficientPhotons => 'Not enough photons';

  @override
  String get shopConfirmPurchase => 'Confirm Purchase';

  @override
  String shopItemSemantics(Object name, Object price) {
    return '$name, price $price photons';
  }

  @override
  String get shopOwned => 'Owned';

  @override
  String shopLimitedStock(Object count) {
    return '$count left';
  }

  @override
  String get userTitlesEmpty => 'No titles yet';

  @override
  String get userTitleUnequippedOption => 'No title equipped';

  @override
  String get notificationCenterTitle => 'Notifications';

  @override
  String notificationMarkAllRead(Object count) {
    return 'Mark all as read ($count)';
  }

  @override
  String get notificationClearRead => 'Clear read';

  @override
  String get notificationEmptyTitle => 'No notifications';

  @override
  String get notificationEmptyDescription =>
      'New notifications will appear here.';

  @override
  String get notificationFilterAll => 'All';

  @override
  String get notificationFilterUnread => 'Unread';

  @override
  String get notificationFilterRead => 'Read';

  @override
  String get notificationSourceAll => 'All types';

  @override
  String get notificationSourceSystem => 'System';

  @override
  String get notificationSourceIntervention => 'Intervention';

  @override
  String get notificationMarkedAllRead => 'Marked all notifications as read';

  @override
  String get notificationClearReadTitle => 'Clear read notifications';

  @override
  String get notificationClearReadMessage => 'Clear all read notifications?';

  @override
  String get notificationClearReadSuccess => 'Read notifications cleared';

  @override
  String get notificationAnalyticsTitle => 'Notification Analytics';

  @override
  String get notificationAnalyticsNoData => 'No data';

  @override
  String notificationAnalyticsLoadFailed(Object error) {
    return 'Failed to load: $error';
  }

  @override
  String get notificationAnalyticsSummary => 'Summary';

  @override
  String get notificationAnalyticsTotalSent => 'Sent';

  @override
  String get notificationAnalyticsTotalViewed => 'Viewed';

  @override
  String get notificationAnalyticsTotalClicked => 'Clicked';

  @override
  String get notificationAnalyticsViewRate => 'View rate';

  @override
  String get notificationAnalyticsByType => 'By type';

  @override
  String get notificationAnalyticsSent => 'Sent';

  @override
  String get notificationAnalyticsViewed => 'Viewed';

  @override
  String get notificationAnalyticsTrends => 'Trends';

  @override
  String get notificationAnalyticsNoTrends => 'No trend data';

  @override
  String get notificationAnalyticsHourlyDistribution => '24-hour distribution';

  @override
  String get notificationAnalyticsPeriod1d => '1 day';

  @override
  String get notificationAnalyticsPeriod7d => '7 days';

  @override
  String get notificationAnalyticsPeriod30d => '30 days';

  @override
  String get notificationAnalyticsPeriodAll => 'All';

  @override
  String get intentAnalysisLabel => 'Analyze intents';

  @override
  String get intentAnalysisInProgress => 'Analyzing...';

  @override
  String get intentAnalysisMultiIntent => 'Multi-intent';

  @override
  String intentAnalysisFailed(Object error) {
    return 'Intent analysis failed: $error';
  }

  @override
  String get intentPreviewTitle => 'Intent Analysis';

  @override
  String get intentPreviewAnalyzing => 'Analyzing intents...';

  @override
  String get intentPreviewSingleIntent => 'Single intent detected';

  @override
  String intentPreviewDetectedCount(Object count) {
    return '$count intents detected:';
  }

  @override
  String intentPreviewAssistantRole(Object role) {
    return 'Assistant: $role';
  }

  @override
  String get intentPreviewExecutionPlan => 'Execution plan';

  @override
  String intentPreviewExecutionPlanWithTime(Object seconds) {
    return 'Execution plan (~${seconds}s)';
  }

  @override
  String get intentPreviewConfirmExecute => 'Confirm and Run';

  @override
  String get intentPreviewDirectExecute => 'Run directly';

  @override
  String get intentExecutionFailed => 'Execution failed. Please try again.';

  @override
  String intentExecutionFailedWithDetail(Object error) {
    return 'Execution failed: $error';
  }

  @override
  String get intentTypeTaskManagement => 'Task management';

  @override
  String get intentTypeKnowledgeQuery => 'Knowledge query';

  @override
  String get intentTypeTimePlanning => 'Time planning';

  @override
  String get intentTypeSocial => 'Social';

  @override
  String get intentTypeLearning => 'Learning';

  @override
  String get intentTypeReflection => 'Reflection';

  @override
  String get intentTypeToolCall => 'Tool call';

  @override
  String get intentTypeUnknown => 'Unknown';

  @override
  String get intentAgentGalaxyGuide => 'Galaxy Guide';

  @override
  String get intentAgentTimeTutor => 'Time Tutor';

  @override
  String get intentAgentExamOracle => 'Exam Oracle';

  @override
  String get intentAgentStudyBuddy => 'Study Buddy';

  @override
  String get avatarSelectTitle => 'Choose an avatar';

  @override
  String get avatarPresetGeek => 'Geek';

  @override
  String get avatarPresetArtist => 'Artist';

  @override
  String get avatarPresetExplorer => 'Explorer';

  @override
  String get avatarPresetScholar => 'Scholar';

  @override
  String get avatarPresetEnergy => 'Energy';

  @override
  String get avatarPresetPet => 'Buddy';

  @override
  String get statisticsWeeklyGrowthTrend => 'Weekly growth trend';

  @override
  String statisticsLearningIndex(Object value) {
    return 'Learning index $value';
  }

  @override
  String get learningModeDepthHigh => 'Depth+';

  @override
  String get learningModeDepthLow => 'Depth-';

  @override
  String get learningModeCuriosityHigh => 'Curiosity+';

  @override
  String get learningModeCuriosityLow => 'Curiosity-';

  @override
  String learningModeDepthValue(Object value) {
    return 'Depth: $value%';
  }

  @override
  String learningModeCuriosityValue(Object value) {
    return 'Curiosity: $value%';
  }

  @override
  String get learningModeSaved => 'Learning preferences saved';

  @override
  String learningModeSaveFailed(Object error) {
    return 'Failed to save: $error';
  }

  @override
  String get learningModeSettingsTitle => 'Learning Mode Settings';

  @override
  String get learningModeDragHint =>
      'Drag the flame to adjust your learning preferences';

  @override
  String learningModeDepthAxisValue(Object value) {
    return 'Depth preference (Y axis): $value%';
  }

  @override
  String learningModeCuriosityAxisValue(Object value) {
    return 'Curiosity preference (X axis): $value%';
  }

  @override
  String get learningModeSave => 'Save preferences';

  @override
  String get notificationReceiveSmartPush =>
      'Receive smart notifications and study reminders';

  @override
  String get schedulePreferencesHint =>
      'Set your fragmented time slots to receive proactive task suggestions.';

  @override
  String get scheduleCommuteTime => 'Commute Time';

  @override
  String get scheduleLunchBreak => 'Lunch Break';

  @override
  String get scheduleStartTime => 'Start Time';

  @override
  String get scheduleEndTime => 'End Time';

  @override
  String get schedulePreferencesSaved => 'Preferences saved';

  @override
  String schedulePreferencesSaveFailed(Object error) {
    return 'Error saving preferences: $error';
  }

  @override
  String get syncCenterRetryAll => 'Retry all now';

  @override
  String get syncCenterRetryAllTriggered => 'Triggered a full retry';

  @override
  String get syncCenterTabAll => 'All';

  @override
  String get syncCenterTabFailed => 'Failed';

  @override
  String get syncCenterTabWaitingAck => 'Waiting Ack';

  @override
  String get syncCenterTabPending => 'Pending';

  @override
  String syncCenterLoadFailed(Object error) {
    return 'Load failed: $error';
  }

  @override
  String get syncCenterCopyDiagnostics => 'Copy diagnostics';

  @override
  String get syncCenterDiagnosticsCopied => 'Diagnostics copied';

  @override
  String syncCenterDisplayLimit(Object limit) {
    return 'Showing up to $limit items';
  }

  @override
  String get syncCenterRetryFailedTriggered =>
      'Triggered retry for failed items';

  @override
  String get syncCenterRetryFailed => 'Retry failed items';

  @override
  String get syncCenterNeverSynced => 'Not synced yet';

  @override
  String syncCenterTotalPending(Object count) {
    return 'Pending items: $count';
  }

  @override
  String syncCenterLastSync(Object value) {
    return 'Last sync: $value';
  }

  @override
  String get syncCenterByTopic => 'By topic';

  @override
  String get syncCenterNoPendingItems => 'No pending items';

  @override
  String get syncCenterTopicLabel => 'Topic';

  @override
  String get syncCenterTopicAll => 'All';

  @override
  String get syncCenterTopicCognitive => 'Cognitive';

  @override
  String get syncCenterTopicKnowledge => 'Knowledge';

  @override
  String get syncCenterTopicCollab => 'Collab';

  @override
  String get syncCenterTopicAnalytics => 'Analytics';

  @override
  String get syncCenterTopicLegacy => 'Legacy';

  @override
  String get syncCenterNoRecords => 'No records';

  @override
  String get syncCenterRetryTriggered => 'Retry triggered';

  @override
  String get syncCenterTraceCopied => 'Trace ID copied';

  @override
  String get syncCenterEntityCopied => 'Entity ID copied';

  @override
  String syncCenterEntityValue(Object entityId, Object entityType) {
    return '$entityType: $entityId';
  }

  @override
  String syncCenterAttemptValue(Object count) {
    return 'Attempts: $count';
  }

  @override
  String syncCenterLastErrorValue(Object value) {
    return 'Last error: $value';
  }

  @override
  String syncCenterNextAttemptValue(Object value) {
    return 'Next attempt: $value';
  }

  @override
  String syncCenterTraceIdValue(Object value) {
    return 'Trace ID: $value';
  }

  @override
  String get syncCenterRetryThis => 'Retry this item';

  @override
  String get syncCenterStatusPending => 'Pending';

  @override
  String get syncCenterStatusFailed => 'Failed';

  @override
  String get syncCenterStatusWaitingAck => 'Waiting Ack';

  @override
  String get shareAchievement => 'Share Achievement';

  @override
  String get sharePreparingCard => 'Preparing share card...';

  @override
  String get shareToSocialMedia => 'Share to Social Media';

  @override
  String get saveToGallery => 'Save to Gallery';

  @override
  String get close => 'Close';

  @override
  String get shareCardGenerateFailed =>
      'Failed to generate share card, please try again later';

  @override
  String shareCardPrepareFailed(Object error) {
    return 'Failed to prepare share card: $error';
  }

  @override
  String shareFailed(Object error) {
    return 'Share failed: $error';
  }

  @override
  String saveFailed(Object error) {
    return 'Save failed: $error';
  }

  @override
  String get savedToGallery => 'Saved to gallery';

  @override
  String get shareCardUrlEmpty => 'Share card URL is empty';

  @override
  String shareCardDownloadFailed(Object statusCode) {
    return 'Failed to download share card ($statusCode)';
  }

  @override
  String get noGalleryPermission => 'No gallery write permission';

  @override
  String get saveResultEmpty => 'Save result is empty';

  @override
  String get gallerySaveFailed => 'Failed to save to gallery';

  @override
  String shareUnlockMessage(Object achievementName) {
    return 'I unlocked \"$achievementName\" in Sparkle!';
  }

  @override
  String get achievementMilestone => 'Learning Milestone';

  @override
  String achievementKnowledgePoints(Object count) {
    return '$count knowledge points';
  }

  @override
  String achievementMilestoneDesc(Object count) {
    return 'Congratulations on mastering $count knowledge points!\nThe light of knowledge illuminates your path forward';
  }

  @override
  String get achievementStreakRecord => 'Streak Record';

  @override
  String achievementStreakDays(Object days) {
    return '$days days';
  }

  @override
  String achievementStreakDesc(Object days, Object username) {
    return '$username has been learning for $days consecutive days\nThe power of persistence is unstoppable!';
  }

  @override
  String get achievementMasteryTitle => 'Domain Mastery';

  @override
  String achievementMasteryPercent(Object percent) {
    return '$percent% mastery';
  }

  @override
  String achievementMasteryDesc(Object domain, Object username) {
    return '$username has reached mastery level in $domain\nKeep it up!';
  }

  @override
  String get achievementTaskComplete => 'Mission Accomplished';

  @override
  String achievementTaskCount(Object count) {
    return 'Completed $count tasks';
  }

  @override
  String achievementTaskDesc(Object username) {
    return '$username performed excellently in this sprint\nYou truly deserve the efficiency star!';
  }

  @override
  String get personaGuide => 'Persona Guide';

  @override
  String get personaMyProfile => 'My Profile';

  @override
  String personaLoadFailed(Object error) {
    return 'Load failed: $error';
  }

  @override
  String get personaL1Title => 'L1 User Declaration';

  @override
  String get personaL2Title => 'L2 Collaborative Calibration';

  @override
  String get personaL3Title => 'L3 System Inference';

  @override
  String get personaL3Hint =>
      'The following content is from system analysis, for reference only';

  @override
  String get personaPreferences => 'Preferences';

  @override
  String get personaGoals => 'Goals';

  @override
  String get personaTags => 'Tags';

  @override
  String get personaCapabilities => 'Capabilities';

  @override
  String get personaPatterns => 'Behavior Patterns';

  @override
  String get personaFragments => 'Cognitive Fragments';

  @override
  String get personaNoData => 'No data';

  @override
  String get personaCompleted => 'Profile is complete, you can refill anytime';

  @override
  String get personaIncomplete =>
      'Complete your profile to enhance personalization';

  @override
  String get personaRefill => 'Refill';

  @override
  String get personaStart => 'Start';

  @override
  String get personaLevelEditable => 'Editable';

  @override
  String get personaLevelWarn => 'Suggested Correction';

  @override
  String get personaLevelReadonly => 'Read Only';

  @override
  String personaConfidence(Object value) {
    return 'Confidence $value';
  }

  @override
  String get personaEdit => 'Edit';

  @override
  String get personaRollback => 'Rollback';

  @override
  String get personaSuggestCorrection => 'Suggest Correction';

  @override
  String get personaCorrectionDialogTitle => 'Suggest Correction';

  @override
  String get personaCorrectionHint =>
      'After submission, the system will evaluate and gradually adjust the profile, which may affect recommendation strategies.';

  @override
  String get personaCorrectionValue => 'Your suggested content';

  @override
  String get personaCorrectionReason => 'Reason (optional)';

  @override
  String get personaCorrectionSubmitted => 'Correction suggestion submitted';

  @override
  String get personaEditPreference => 'Edit Preference';

  @override
  String get personaNewPreferenceValue => 'New preference value';

  @override
  String get personaPleaseEnterValue => 'Please enter a value';

  @override
  String get personaRollbackTitle => 'Rollback Preference';

  @override
  String get personaRollbackConfirm =>
      'Roll back preference to previous version, may affect recommendation effectiveness.';

  @override
  String get personaConfirmRollback => 'Confirm Rollback';

  @override
  String get personaEditGoal => 'Edit Goal';

  @override
  String get personaGoalContent => 'Goal content';

  @override
  String get personaGoalStatus => 'Status';

  @override
  String get personaStatusActive => 'Active';

  @override
  String get personaStatusCompleted => 'Completed';

  @override
  String get personaStatusPaused => 'Paused';

  @override
  String get personaPleaseEnterGoal => 'Please enter goal content';

  @override
  String get personaLearningGoal => 'Learning Goal';

  @override
  String get personaGoalTypeExam => 'Exam';

  @override
  String get personaGoalTypeSkill => 'Skill';

  @override
  String get personaGoalTypeInterest => 'Interest';

  @override
  String get personaGoalHint => 'e.g., Final exam prep / Learn Flutter';

  @override
  String get personaLearningStyle => 'Learning Style';

  @override
  String get personaStyleBalanced => 'Balanced';

  @override
  String get personaStyleVisual => 'Visual';

  @override
  String get personaStylePractice => 'Practice';

  @override
  String get personaStyleLogic => 'Logic';

  @override
  String get personaDailyStudyTime => 'Daily Study Time';

  @override
  String personaMinutes(Object minutes) {
    return '$minutes minutes';
  }

  @override
  String get personaKnowledgeLevel => 'Knowledge Level';

  @override
  String get personaLevelBeginner => 'Beginner';

  @override
  String get personaLevelIntermediate => 'Intermediate';

  @override
  String get personaLevelAdvanced => 'Advanced';

  @override
  String get personaResponsePreference => 'Response Preference';

  @override
  String get personaResponseDepth => 'Response detail level';

  @override
  String get personaCuriosityExtension => 'Curiosity extension level';

  @override
  String get personaNextStep => 'Next';

  @override
  String get personaPreviousStep => 'Previous';

  @override
  String get personaComplete => 'Complete';

  @override
  String get editProfile => 'Edit Profile';

  @override
  String get editProfileSave => 'Save';

  @override
  String get editProfileChangeAvatar => 'Change Avatar';

  @override
  String get editProfileChooseFromPresets => 'Choose from presets';

  @override
  String get editProfileTakePhoto => 'Take photo';

  @override
  String get editProfileChooseFromGallery => 'Choose from gallery';

  @override
  String get editProfileAvatarUpdated => 'Avatar updated successfully';

  @override
  String editProfileUpdateFailed(Object error) {
    return 'Update failed: $error';
  }

  @override
  String editProfileUploadFailed(Object error) {
    return 'Upload failed: $error';
  }

  @override
  String get editProfileNicknameLabel => 'Nickname';

  @override
  String get editProfileNicknameHint => 'Enter your nickname';

  @override
  String get editProfileNicknameEmpty => 'Nickname cannot be empty';

  @override
  String get editProfileEmailLabel => 'Email';

  @override
  String get editProfileEmailHint => 'Enter your email';

  @override
  String get editProfileEmailInvalid => 'Please enter a valid email address';

  @override
  String get editProfileUsernameLabel => 'Username';

  @override
  String get editProfileUsernameReadonly => 'Username cannot be changed';

  @override
  String get editProfileAccountSecurity => 'Account Security';

  @override
  String get editProfileResetPassword => 'Reset Password';

  @override
  String get editProfileAccountInfo => 'Account Information';

  @override
  String get editProfileFlameLevel => 'Flame Level';

  @override
  String get editProfileFlameBrightness => 'Flame Brightness';

  @override
  String get editProfileAccountType => 'Account Type';

  @override
  String get editProfileGuestAccount => 'Guest Account';

  @override
  String get editProfileFullAccount => 'Full Account';

  @override
  String get editProfileProfileUpdated => 'Profile updated successfully';

  @override
  String get editProfileNewAvatarPending => 'New avatar is under review...';

  @override
  String get passwordReset => 'Reset Password';

  @override
  String get passwordResetHint =>
      'Please ensure your new password contains at least 8 characters.';

  @override
  String get passwordResetCurrentLabel => 'Current Password';

  @override
  String get passwordResetCurrentRequired => 'Please enter current password';

  @override
  String get passwordResetNewLabel => 'New Password';

  @override
  String get passwordResetNewRequired => 'Please enter new password';

  @override
  String get passwordResetNewMinLength =>
      'Password must be at least 8 characters';

  @override
  String get passwordResetConfirmLabel => 'Confirm New Password';

  @override
  String get passwordResetConfirmMismatch => 'Passwords do not match';

  @override
  String get passwordResetButton => 'Update Password';

  @override
  String get passwordResetSuccess => 'Password changed successfully';

  @override
  String passwordResetFailed(Object error) {
    return 'Change failed: $error';
  }

  @override
  String get smartPushSettings => 'Smart Push Settings';

  @override
  String get smartPushPersonaSection => 'Persona Settings';

  @override
  String get smartPushFrequencySection => 'Frequency Settings (Daily Cap)';

  @override
  String get smartPushActiveSlotsSection => 'Active Time Slots';

  @override
  String get smartPushActiveSlotsHint =>
      'Push notifications only during these time slots, avoiding rest times.';

  @override
  String get smartPushAddTimeSlot => 'Add Time Slot';

  @override
  String get smartPushTestNotification => 'Send Test Notification (Dev)';

  @override
  String get smartPushTestNotificationSent =>
      'Test notification sent (check notification center)';

  @override
  String get smartPushPersonaCoach => 'Strict Coach';

  @override
  String get smartPushPersonaCoachDesc => 'Discipline, emphasis on rigor';

  @override
  String get smartPushPersonaAnime => 'Anime Assistant';

  @override
  String get smartPushPersonaAnimeDesc => 'Gentle, cute encouragement';

  @override
  String smartPushFrequencyLabel(Object count) {
    return '$count per day';
  }

  @override
  String get smartPushNoSlots => 'No slots set, suggest adding active times';

  @override
  String get smartPushSettingsSaved => 'Settings saved';

  @override
  String smartPushSaveFailed(Object error) {
    return 'Save failed: $error';
  }

  @override
  String get themeSettings => 'Theme Settings';

  @override
  String get themeModeSection => 'Theme Mode';

  @override
  String get themeModeLight => 'Light';

  @override
  String get themeModeDark => 'Dark';

  @override
  String get themeModeSystem => 'System';

  @override
  String get brandPresetSection => 'Brand Preset';

  @override
  String get highContrastSection => 'High Contrast Mode';

  @override
  String get highContrastDesc => 'Enhance text and background contrast';

  @override
  String get resetDefaults => 'Reset to Defaults';

  @override
  String get colorPreviewSection => 'Color Preview';

  @override
  String get colorPrimary => 'Primary';

  @override
  String get colorSecondary => 'Secondary';

  @override
  String get colorSuccess => 'Success';

  @override
  String get colorWarning => 'Warning';

  @override
  String get colorError => 'Error';

  @override
  String get taskTypeColors => 'Task Type Colors';

  @override
  String get taskTypeLearning => 'Learning';

  @override
  String get taskTypeTraining => 'Training';

  @override
  String get taskTypeFix => 'Fix';

  @override
  String get taskTypeReflection => 'Reflection';

  @override
  String get taskTypeSocial => 'Social';

  @override
  String get taskTypePlanning => 'Planning';

  @override
  String get themeResetSuccess => 'Restored to default settings';

  @override
  String get systemUpdates => 'System Activity';

  @override
  String systemUpdatesLoadFailed(Object error) {
    return 'Load failed: $error';
  }

  @override
  String get systemUpdatesSearchHint => 'Search title or description';

  @override
  String get systemUpdatesTypeFilter => 'Type';

  @override
  String get systemUpdatesPriorityFilter => 'Priority';

  @override
  String systemUpdatesCount(Object count) {
    return 'Total $count items';
  }

  @override
  String get systemUpdatesNoItems => 'No system updates';

  @override
  String get systemUpdatesAll => 'All';

  @override
  String systemUpdatesConfidence(Object value) {
    return 'Confidence $value%';
  }

  @override
  String systemUpdatesNextWeekAdjust(Object value) {
    return 'Next week continue adapting: $value';
  }

  @override
  String get systemUpdatesBeforeLabel => 'Before';

  @override
  String get systemUpdatesAfterLabel => 'Now';

  @override
  String systemUpdatesAlignmentScore(Object value) {
    return 'Persona alignment $value%';
  }

  @override
  String get contentReviewCardTitle => 'Content Review';

  @override
  String get contentReviewPassed => 'Content Passed Review';

  @override
  String get contentReviewFailed => 'Content Failed Review';

  @override
  String get contentReviewNeedsRefinement => 'Content Needs Refinement';

  @override
  String get contentReviewScoreLabel => 'Score';

  @override
  String get contentReviewOverallScore => 'Overall Score';

  @override
  String get contentReviewMetrics => 'Evaluation Metrics';

  @override
  String get contentReviewIssues => 'Issues Found';

  @override
  String get contentReviewSuggestions => 'Improvement Suggestions';

  @override
  String get contentReviewCriticalIssues => 'Critical Issues';

  @override
  String get contentReviewWarnings => 'Warnings';

  @override
  String get contentReviewTips => 'Tips';

  @override
  String get contentReviewAccept => 'Accept';

  @override
  String get contentReviewReject => 'Reject';

  @override
  String get contentReviewRequestManual => 'Request Manual Review';

  @override
  String get contentReviewRegenerate => 'Regenerate';

  @override
  String get contentReviewWaitOptimization => 'Waiting for optimization...';

  @override
  String get contentReviewOptimizing => 'Optimizing content...';

  @override
  String get contentReviewOptimized => 'Optimization complete';

  @override
  String get contentReviewOptimizationFailed => 'Optimization failed';

  @override
  String get contentReviewProcessing => 'Processing...';

  @override
  String get contentReviewAgreePassed => 'I agree it should pass';

  @override
  String get contentReviewDisagreePassed => 'I disagree with this result';

  @override
  String get contentReviewReportProblem => 'Report Review Problem';

  @override
  String get contentReviewOverrideDialogTitle => 'Override Review Decision';

  @override
  String get contentReviewDisagreeWithResult =>
      'I disagree with this review result';

  @override
  String get contentReviewAgreeShouldPass =>
      'I think the content should pass review';

  @override
  String get contentReviewReasonHint => 'Enter your reason...';

  @override
  String get contentReviewReasonRequired => 'Please provide a reason';

  @override
  String get contentReviewAppealDialogTitle => 'Report Review Problem';

  @override
  String get contentReviewSelectIssuesHint =>
      'Select issue types (multiple allowed)';

  @override
  String get contentReviewDetailHint => 'Detailed explanation:';

  @override
  String get contentReviewDetailPlaceholder =>
      'Please describe what\'s wrong with the review...';

  @override
  String get contentReviewDetailRequired =>
      'Please provide a detailed explanation';

  @override
  String get contentReviewSelectAtLeastOne =>
      'Please select at least one issue type';

  @override
  String get contentReviewIssueUnfairStandards => 'Review standards are unfair';

  @override
  String get contentReviewIssueScoreCalculation =>
      'Score calculation is incorrect';

  @override
  String get contentReviewIssueMissingContext => 'Important context was missed';

  @override
  String get contentReviewIssueInaccurateDescription =>
      'Description is inaccurate';

  @override
  String get contentReviewIssueUnfeasibleSuggestion =>
      'Suggestion is not feasible';

  @override
  String get contentReviewMetricAccuracy => 'Accuracy';

  @override
  String get contentReviewMetricCompleteness => 'Completeness';

  @override
  String get contentReviewMetricRelevance => 'Relevance';

  @override
  String get contentReviewMetricClarity => 'Clarity';

  @override
  String get contentReviewMetricSafety => 'Safety';

  @override
  String get contentReviewMetricFeasibility => 'Feasibility';

  @override
  String get contentReviewMetricEfficiency => 'Efficiency';

  @override
  String get contentReviewMetricHelpfulness => 'Helpfulness';

  @override
  String get contentReviewMetricTone => 'Tone appropriateness';

  @override
  String get contentReviewScoreExcellent => 'Excellent';

  @override
  String get contentReviewScoreGood => 'Good';

  @override
  String get contentReviewScorePass => 'Pass';

  @override
  String get contentReviewScoreNeedsWork => 'Needs Work';

  @override
  String get contentReviewSeverityCritical => 'Critical';

  @override
  String get contentReviewSeverityWarning => 'Warning';

  @override
  String get contentReviewSeverityInfo => 'Info';

  @override
  String get contentReviewHints => 'Hints';

  @override
  String contentReviewSuggestion(Object suggestion) {
    return 'Suggestion: $suggestion';
  }

  @override
  String get contentReviewSuggestionDesc => 'Suggestion';

  @override
  String get contentReviewReflectionPending => 'Waiting for optimization...';

  @override
  String get contentReviewReflectionInProgress => 'Optimizing content...';

  @override
  String get contentReviewReflectionCompleted => 'Optimization completed';

  @override
  String get contentReviewReflectionFailed => 'Optimization failed';

  @override
  String get contentReviewReflectionProcessing => 'Processing reflection...';

  @override
  String get contentReviewReflectionPendingShort => 'Waiting';

  @override
  String get contentReviewReflectionInProgressShort => 'Optimizing...';

  @override
  String get contentReviewReflectionCompletedShort => 'Optimized';

  @override
  String get contentReviewReflectionFailedShort => 'Failed';

  @override
  String get contentReviewReflectionProcessingShort => 'Processing';

  @override
  String get contentReviewManualReview => 'Manual Review';

  @override
  String get contentReviewDisagreePass => 'I disagree with this result';

  @override
  String get contentReviewAgreePass => 'I think it should pass';

  @override
  String get contentReviewReportIssue => 'Report review issue';

  @override
  String get contentReviewDisagreePassTitle => 'Disagree with approval';

  @override
  String get contentReviewAgreePassTitle =>
      'I think content should pass review';

  @override
  String get contentReviewReasonPrompt => 'Please explain your reason:';

  @override
  String get contentReviewCancel => 'Cancel';

  @override
  String get contentReviewConfirm => 'Confirm';

  @override
  String get contentReviewAppealSelectType => 'Select issue type:';

  @override
  String get contentReviewAppealDetail => 'Detailed explanation:';

  @override
  String get contentReviewAppealDetailHint =>
      'Please describe the issues with the review result...';

  @override
  String get contentReviewAppealDetailRequired =>
      'Please provide a detailed explanation';

  @override
  String get contentReviewAppealTypeRequired =>
      'Please select at least one issue type';

  @override
  String get contentReviewAppealUnreasonableStandard =>
      'Unreasonable review standards';

  @override
  String get contentReviewAppealScoreError => 'Score calculation error';

  @override
  String get contentReviewAppealContextIgnored => 'Important context ignored';

  @override
  String get contentReviewAppealDescriptionInaccurate =>
      'Inaccurate problem description';

  @override
  String get contentReviewAppealSuggestionNotFeasible =>
      'Suggestion not feasible';

  @override
  String get contentReviewAppealSubmit => 'Submit Appeal';

  @override
  String get commonSubmitting => 'Submitting...';

  @override
  String get brandPresetSparkle => 'Sparkle';

  @override
  String get brandPresetOcean => 'Ocean';

  @override
  String get brandPresetForest => 'Forest';

  @override
  String get smartPushDebugTitle => 'Debug: Memory Threshold';

  @override
  String get smartPushDebugBody =>
      'Your [Linear Algebra] is fading, tap to review now!';

  @override
  String get reviewAppealPendingTitle => 'Appeal pending';

  @override
  String get reviewAppealPendingDesc =>
      'Your appeal has been submitted and is waiting to be processed.';

  @override
  String get reviewAppealInReviewTitle => 'Second review in progress';

  @override
  String get reviewAppealInReviewDesc =>
      'A different model is conducting a second review.';

  @override
  String get reviewAppealResolvedTitle => 'Appeal approved';

  @override
  String get reviewAppealResolvedDesc =>
      'Your appeal was approved and the original review result has been updated.';

  @override
  String get reviewAppealRejectedTitle => 'Appeal rejected';

  @override
  String get reviewAppealRejectedDesc =>
      'Your appeal was rejected and the original review result remains unchanged.';

  @override
  String get reviewAppealEscalatedTitle => 'Escalated to manual handling';

  @override
  String get reviewAppealEscalatedDesc =>
      'Manual review is required. Please wait patiently.';

  @override
  String reviewAppealId(Object id) {
    return 'Appeal #$id';
  }

  @override
  String get reviewAppealTimelineSubmitted => 'Appeal submitted';

  @override
  String get reviewAppealTimelineReviewed => 'Second review completed';

  @override
  String get reviewAppealTimelineApproved => 'Appeal approved';

  @override
  String get reviewAppealTimelineRejected => 'Appeal rejected';

  @override
  String reviewAppealScore(Object value) {
    return 'Score: $value%';
  }

  @override
  String reviewAppealSecondaryScore(Object value) {
    return 'Second review score: $value%';
  }

  @override
  String get reviewAppealMinReason =>
      'Please provide more detail (at least 10 characters)';

  @override
  String get reviewAppealOtherIssue => 'Other issue';

  @override
  String get transparencySettingsTitle => 'Transparency Settings';

  @override
  String get transparencyEnable => 'Enable transparency mode';

  @override
  String get transparencyEnableDesc =>
      'Show AI processing steps, agent switches, and token usage.';

  @override
  String get transparencyDisplayOptions => 'Display options';

  @override
  String get transparencyTokenUsage => 'Token usage';

  @override
  String get transparencyTokenUsageDesc =>
      'Show token consumption and estimated cost for each conversation.';

  @override
  String get transparencyAgentSwitching => 'Agent switching';

  @override
  String get transparencyAgentSwitchingDesc =>
      'Show how the system switches between different agents.';

  @override
  String get transparencyReasoningSteps => 'Reasoning steps';

  @override
  String get transparencyReasoningStepsDesc =>
      'Show the model\'s detailed reasoning steps.';

  @override
  String get transparencyWarning =>
      'Detailed transparency may slightly increase response latency.';

  @override
  String get transparencyLoadFailed => 'Failed to load settings';

  @override
  String get nightlyReviewPending => 'Tonight\'s review is still waiting';

  @override
  String get nightlyReviewStart => 'Start';

  @override
  String get thoughtCapsuleTitle => 'Thought Capsule';

  @override
  String get thoughtCapsulePrompt =>
      'What\'s blocking you right now, or what do you want to vent about?';

  @override
  String get thoughtCapsuleHint => 'Write down your thought...';

  @override
  String get thoughtCapsuleCaptured => 'Thought captured';

  @override
  String thoughtCapsuleCaptureFailed(Object error) {
    return 'Capture failed: $error';
  }

  @override
  String get leaderboardTitle => 'Leaderboard';

  @override
  String get leaderboardGlobal => 'Global';

  @override
  String get leaderboardFriends => 'Friends';

  @override
  String get leaderboardGroup => 'Groups';

  @override
  String get leaderboardSubject => 'Subjects';

  @override
  String get leaderboardWeekly => 'Weekly';

  @override
  String get leaderboardStreak => 'Streak';

  @override
  String leaderboardMyRank(int rank) {
    return 'My rank: $rank';
  }

  @override
  String leaderboardPoints(int value) {
    return '$value pts';
  }

  @override
  String leaderboardNoData(Object label) {
    return 'No $label data yet';
  }

  @override
  String get leaderboardLoadFailed =>
      'Failed to load leaderboard. Please try again.';

  @override
  String get omnibarListeningHint => 'Listening...';

  @override
  String get omnibarDefaultHint => 'Tell me what you think...';

  @override
  String get voiceInputAction => 'Voice input';

  @override
  String get voiceInputStopAction => 'Stop recording';

  @override
  String voiceInputSpeechFailed(Object error) {
    return 'Speech recognition failed: $error';
  }

  @override
  String sendFailedWithError(Object error) {
    return 'Failed to send: $error';
  }

  @override
  String submitFailedWithError(Object error) {
    return 'Submission failed: $error';
  }

  @override
  String loadingFailedWithError(Object error) {
    return 'Loading failed: $error';
  }

  @override
  String get delete => 'Delete';

  @override
  String get blockingReasonEfficiency =>
      'I misjudged how much I could get done';

  @override
  String get blockingReasonInterrupted => 'I got interrupted halfway through';

  @override
  String get blockingReasonPerfectionism => 'Perfectionism made me freeze up';

  @override
  String get blockingReasonTooHard =>
      'It felt too hard and I didn\'t know how to start';

  @override
  String get blockingReasonNoMood => 'I wasn\'t in the right headspace';

  @override
  String get blockingSelectReason =>
      'Choose a reason or write your own thought';

  @override
  String get blockingTitle => 'Hit a roadblock?';

  @override
  String get blockingDescription =>
      'Capture what got in the way. AI will look for patterns and help you do better next time.';

  @override
  String get blockingOtherReason => 'Something else...';

  @override
  String get blockingReasonHint => 'Describe what happened';

  @override
  String get blockingConfirmAbandon => 'Stop this task';

  @override
  String get subtaskAddHint => 'Add a subtask...';

  @override
  String get subtaskAddTooltip => 'Add subtask';

  @override
  String get subtaskEmpty => 'No subtasks yet';

  @override
  String get subtaskTitle => 'Subtasks';

  @override
  String get taskFeedbackSubmitted => 'Feedback submitted';

  @override
  String get taskFeedbackPreferenceUpdated => 'Preferences updated';

  @override
  String get taskFeedbackView => 'View';

  @override
  String get taskFeedbackPreferenceDialogTitle => 'Preference updates';

  @override
  String taskFeedbackDepthPreference(Object value) {
    return 'Depth preference: $value';
  }

  @override
  String taskFeedbackDifficultyPreference(Object value) {
    return 'Difficulty preference: $value';
  }

  @override
  String get taskFeedbackPreferenceDialogDesc =>
      'These preferences will help personalize what you should learn next.';

  @override
  String get taskFeedbackGotIt => 'Got it';

  @override
  String get taskFeedbackCompletedTitle => 'Task completed';

  @override
  String get taskFeedbackCompletedSubtitle =>
      'Nice work. Keep the momentum going.';

  @override
  String get taskFeedbackBrightness => 'Glow';

  @override
  String get taskFeedbackStreak => 'Streak';

  @override
  String taskFeedbackStreakDays(int count) {
    return '$count days';
  }

  @override
  String get taskFeedbackOptionalRating => 'Satisfaction rating (optional)';

  @override
  String get taskFeedbackDifficultyQuestion =>
      'How did the difficulty feel this time?';

  @override
  String get taskFeedbackCategoryJustRight => 'Just right';

  @override
  String get taskFeedbackCategoryStillHard => 'Still hard';

  @override
  String get taskFeedbackCategoryTooEasy => 'Too easy';

  @override
  String get taskFeedbackOptionalComment => 'Anything else to add? (optional)';

  @override
  String get taskFeedbackCommentHint => 'Write down a quick reflection...';

  @override
  String get taskFeedbackNextSteps => 'Suggested next steps';

  @override
  String get taskFeedbackSkip => 'Skip';

  @override
  String get taskFeedbackComplete => 'Done';

  @override
  String taskFeedbackReason(Object reason) {
    return 'Why: $reason';
  }

  @override
  String get communityQuote => 'Quote';

  @override
  String get communityCopy => 'Copy';

  @override
  String get communityCopiedToClipboard => 'Copied to clipboard';

  @override
  String get communityThreadReply => 'Reply in thread';

  @override
  String get communityEdit => 'Edit';

  @override
  String get communityRevoke => 'Recall';

  @override
  String get communityRevokedOwnMessage => 'You recalled a message';

  @override
  String communityRevokedUserMessage(Object sender) {
    return '$sender recalled a message';
  }

  @override
  String get communityMemberFallback => 'Member';

  @override
  String communityReadByCount(int count) {
    return '$count read';
  }

  @override
  String get communityQuotedMessageFallback => 'Quoted message';

  @override
  String get communityDailyCheckIn => 'Daily check-in';

  @override
  String get communityDurationLabel => 'Duration';

  @override
  String get communityFlameLabel => 'Flame';

  @override
  String get communityStreakLabel => 'Streak';

  @override
  String get communitySharedTask => 'Shared a task';

  @override
  String get shareResourceTitle => 'Share with community';

  @override
  String get shareResourceTabFriends => 'Friends';

  @override
  String get shareResourceTabGroups => 'Groups';

  @override
  String get shareResourceCommentHint => 'Add a note (optional)';

  @override
  String get shareResourceNow => 'Share now';

  @override
  String get shareResourceNoFriends => 'No friends yet';

  @override
  String get shareResourceNoGroups => 'No groups yet';

  @override
  String shareResourceGroupMembers(int count) {
    return '$count members';
  }

  @override
  String get shareResourceSelectTarget => 'Choose a friend or group first';

  @override
  String get shareResourceSuccess => 'Shared successfully';

  @override
  String shareResourceFailed(Object error) {
    return 'Sharing failed: $error';
  }

  @override
  String get shareTypeNotSupportedYet =>
      'This content type is not yet supported for community sharing. Please use image sharing instead.';

  @override
  String get threadDiscussion => 'Thread';

  @override
  String get threadReplyHint => 'Reply to thread...';

  @override
  String get calendarSetDueDateTitle => 'Set task due date';

  @override
  String calendarSetDueDateMessage(Object task, Object date) {
    return 'Set \"$task\" to be due on $date?';
  }

  @override
  String get calendarTitle => 'Calendar';

  @override
  String get calendarMonthView => 'Month';

  @override
  String get calendarTwoWeekView => '2 weeks';

  @override
  String get calendarYearView => 'Year';

  @override
  String calendarDayScheduleTitle(Object date) {
    return '$date schedule';
  }

  @override
  String get calendarViewDetails => 'View details';

  @override
  String get calendarNoEvents => 'No events yet';

  @override
  String get calendarAllDay => 'All day';

  @override
  String get calendarCreateEvent => 'New event';

  @override
  String get calendarSave => 'Save';

  @override
  String get calendarTitleHint => 'Title';

  @override
  String get calendarLocationHint => 'Location';

  @override
  String get calendarDescriptionHint => 'Description';

  @override
  String get calendarStartTime => 'Start time';

  @override
  String get calendarEndTime => 'End time';

  @override
  String get calendarReminder => 'Reminder';

  @override
  String get calendarReminderAtStart => 'At start time';

  @override
  String calendarReminderMinutes(int count) {
    return '$count min before';
  }

  @override
  String calendarReminderHours(int count) {
    return '$count hour before';
  }

  @override
  String calendarReminderDays(int count) {
    return '$count day before';
  }

  @override
  String get calendarRepeat => 'Repeat';

  @override
  String get calendarRepeatNone => 'Never';

  @override
  String get calendarRepeatDaily => 'Daily';

  @override
  String get calendarRepeatWeekly => 'Weekly';

  @override
  String get calendarRepeatMonthly => 'Monthly';

  @override
  String get calendarTitleRequired => 'Please enter a title';

  @override
  String get dailyDetailEventsSection => 'Events';

  @override
  String get dailyDetailTasksSection => 'Tasks';

  @override
  String get dailyDetailFlame => 'Flame';

  @override
  String get dailyDetailFocusTime => 'Focus time';

  @override
  String get dailyDetailTasksDone => 'Tasks done';

  @override
  String get dailyDetailPrismTitle => 'Today\'s prism snapshot';

  @override
  String get dailyDetailPrismFallback =>
      'Your thinking feels clear and steady today.';

  @override
  String get dailyDetailNoTasks => 'No tasks yet';

  @override
  String get onboardingSkip => 'Skip';

  @override
  String get onboardingGetStarted => 'Get started';

  @override
  String get onboardingNext => 'Next';

  @override
  String get onboardingWelcomeTitle => 'Welcome to Sparkle';

  @override
  String get onboardingWelcomeSubtitle =>
      'Your AI learning companion\nthat helps knowledge turn into momentum.';

  @override
  String get onboardingFeatureGalaxy => 'Knowledge Galaxy';

  @override
  String get onboardingFeatureGalaxyDesc => 'A visual map of what you know';

  @override
  String get onboardingFeatureChat => 'AI Chat';

  @override
  String get onboardingFeatureChatDesc =>
      'A study partner that thinks with you';

  @override
  String get onboardingFeatureTasks => 'Smart Tasks';

  @override
  String get onboardingFeatureTasksDesc =>
      'Adaptive plans built around your rhythm';

  @override
  String get onboardingArchitectureTitle => 'How It Works';

  @override
  String get onboardingArchitectureSubtitle =>
      'A quick look at how Sparkle comes together';

  @override
  String get onboardingGalaxyTitle => 'Knowledge Galaxy';

  @override
  String get onboardingGalaxyDescription =>
      'Turn what you know into a living map you can explore.';

  @override
  String get onboardingGalaxyFeature1 =>
      'Six learning realms to organize different kinds of knowledge';

  @override
  String get onboardingGalaxyFeature2 =>
      'Live decay prediction so you can spot forgetting early';

  @override
  String get onboardingGalaxyFeature3 =>
      'A time-machine view to preview future learning states';

  @override
  String get onboardingGalaxyFeature4 =>
      'Smarter path suggestions based on your knowledge graph';

  @override
  String get onboardingChatTitle => 'AI Chat';

  @override
  String get onboardingChatDescription =>
      'A learning partner that adapts to you.';

  @override
  String get onboardingChatFeature1 =>
      'Multi-agent collaboration across math, code, writing, and science';

  @override
  String get onboardingChatFeature2 =>
      'GraphRAG retrieval with visible reasoning context';

  @override
  String get onboardingChatFeature3 =>
      'Context memory that keeps up with your learning history';

  @override
  String get onboardingChatFeature4 =>
      'Tool use for tasks, knowledge lookup, and planning';

  @override
  String get onboardingTasksTitle => 'Smart Tasks';

  @override
  String get onboardingTasksDescription =>
      'Personalized plans that keep learning moving forward.';

  @override
  String get onboardingTasksFeature1 =>
      'Six task types covering learning, practice, correction, reflection, social, and planning';

  @override
  String get onboardingTasksFeature2 =>
      'Smart reminders based on your current study state';

  @override
  String get onboardingTasksFeature3 => 'Sprint plans for short-term push';

  @override
  String get onboardingTasksFeature4 => 'Growth plans for long-term progress';

  @override
  String get onboardingPersonalizationTitle => 'Personalization';

  @override
  String get onboardingPersonalizationSubtitle =>
      'Help Sparkle understand you better';

  @override
  String get onboardingSettingReminders => 'Study reminders';

  @override
  String get onboardingSettingRemindersDesc =>
      'Get helpful nudges at the right moment';

  @override
  String get onboardingSettingAnalytics => 'Learning insights';

  @override
  String get onboardingSettingAnalyticsDesc =>
      'Generate reports tailored to your learning patterns';

  @override
  String get onboardingSettingAssistant => 'AI assistant';

  @override
  String get onboardingSettingAssistantDesc =>
      'Create learning tasks automatically';

  @override
  String get onboardingChatDemo1 => 'Hi. What would you like help with?';

  @override
  String get onboardingChatDemo2 => 'Explain the basic idea behind calculus';

  @override
  String get onboardingChatDemo3 =>
      'Calculus studies how quantities change over time...';

  @override
  String get onboardingTaskTypeLearning => 'Learning task';

  @override
  String get onboardingTaskTypePractice => 'Practice task';

  @override
  String get onboardingTaskTypeReflection => 'Reflection task';

  @override
  String get onboardingTaskDemo1 => 'Finish chapter one of calculus';

  @override
  String get onboardingTaskDemo2 => 'Solve ten practice questions';

  @override
  String get onboardingTaskDemo3 => 'Summarize what you learned this week';

  @override
  String get onboardingArchitectureStep1Title => 'Mobile app';

  @override
  String get onboardingArchitectureStep1Desc =>
      'A cross-platform Flutter app built for a smooth daily experience';

  @override
  String get onboardingArchitectureStep2Title => 'WebSocket link';

  @override
  String get onboardingArchitectureStep2Desc =>
      'The Go gateway keeps communication real-time, fast, and reliable';

  @override
  String get onboardingArchitectureStep3Title => 'AI engine';

  @override
  String get onboardingArchitectureStep3Desc =>
      'The Python agent engine handles reasoning and tool orchestration';

  @override
  String get onboardingArchitectureStep4Title => 'Data layer';

  @override
  String get onboardingArchitectureStep4Desc =>
      'PostgreSQL plus pgvector for structured data and semantic retrieval';

  @override
  String get onboardingArchitectureStep5Title => 'End-to-end flow';

  @override
  String get onboardingArchitectureStep5Desc =>
      'From question to answer, the whole loop is designed to feel immediate';

  @override
  String get capsuleQualityUnrated => 'Unrated';

  @override
  String get capsuleQualityExcellent => 'Excellent';

  @override
  String get capsuleQualityGood => 'Good';

  @override
  String get capsuleQualityFair => 'Fair';

  @override
  String get capsuleQualityNeedsWork => 'Needs work';

  @override
  String get capsuleJobStatusPending => 'Pending';

  @override
  String get capsuleJobStatusGenerating => 'Generating';

  @override
  String get capsuleJobStatusCompleted => 'Completed';

  @override
  String get capsuleJobStatusFailed => 'Failed';

  @override
  String get capsuleGenerationTypeDaily => 'Daily capsule';

  @override
  String get capsuleGenerationTypeWeekly => 'Weekly capsule';

  @override
  String get capsuleGenerationTypeManual => 'Manual run';

  @override
  String get capsuleGenerationTypePushTriggered => 'Push-triggered';

  @override
  String get capsuleFeedbackTooLong => 'Too long';

  @override
  String get capsuleFeedbackTooShort => 'Too short';

  @override
  String get capsuleFeedbackJustRight => 'Just right';

  @override
  String get capsuleFeedbackTooComplex => 'Too complex';

  @override
  String get capsuleFeedbackTooSimple => 'Too simple';

  @override
  String get capsuleFeedbackIrrelevant => 'Irrelevant';

  @override
  String get capsuleFeedbackOther => 'Other';

  @override
  String get capsuleFeedbackCategoryLabel => 'What could be improved?';

  @override
  String get capsuleDepthShallow => 'Light';

  @override
  String get capsuleDepthMedium => 'Balanced';

  @override
  String get capsuleDepthDeep => 'Deep';

  @override
  String get capsulePersonalizationTitle => 'Why this was recommended';

  @override
  String capsulePersonalizationBadge(String pattern) {
    return 'Based on your $pattern pattern';
  }

  @override
  String capsulePersonalizationExplanation(String patterns) {
    return 'Based on your recent $patterns behavior patterns, AI picked this for you.';
  }

  @override
  String get patternPlanningOptimism => 'Planning optimism';

  @override
  String get patternFocusDecay => 'Focus decay';

  @override
  String get patternProcrastination => 'Procrastination';

  @override
  String get cognitiveSelectGalaxyNodes =>
      'Select the nodes you want to review in Galaxy first';

  @override
  String get cognitiveTimeMachine => 'Knowledge Time Machine';

  @override
  String cognitiveFutureDays(int count) {
    return 'Next $count days';
  }

  @override
  String cognitiveDaysLater(int count) {
    return 'In $count days';
  }

  @override
  String get cognitiveToday => 'Today';

  @override
  String cognitiveDayTick(int count) {
    return '${count}d';
  }

  @override
  String get cognitiveHealthy => 'Healthy';

  @override
  String get cognitiveDecaying => 'Decaying';

  @override
  String get cognitiveRisk => 'At risk';

  @override
  String get cognitiveSimulating => 'Simulating...';

  @override
  String cognitiveReviewNow(int count) {
    return 'Review now? ($count nodes)';
  }

  @override
  String get prismCognitivePatterns => 'Cognitive patterns';

  @override
  String get prismEmotionalPatterns => 'Emotional patterns';

  @override
  String get prismExecutionPatterns => 'Execution patterns';

  @override
  String get prismTitle => 'Cognitive Prism';

  @override
  String get prismNoData => 'No behavior pattern data yet';

  @override
  String get prismHint =>
      'Keep learning and reflecting. The prism will build a clearer picture of your study patterns over time.';

  @override
  String prismTotalPatterns(int count) {
    return '$count patterns';
  }

  @override
  String get capsuleScreenTitle => 'Curiosity Capsules';

  @override
  String capsuleCurrentTab(int count) {
    return 'Current $count';
  }

  @override
  String capsuleArchiveTab(int count) {
    return 'Archive $count';
  }

  @override
  String get capsuleArchiveEmpty => 'No archived capsules yet';

  @override
  String get capsuleEmptyTitle => 'No new curiosity capsule today';

  @override
  String get capsuleEmptySubtitle =>
      'Keep learning and new ideas will keep showing up.';

  @override
  String get capsuleGenerationPreviewTitle => 'Generation preview';

  @override
  String get capsuleGenerationPreviewCountLabel => 'Estimated output';

  @override
  String capsuleGenerationPreviewCount(int count) {
    return '$count capsules';
  }

  @override
  String get capsuleGenerationPreviewDepthLabel => 'Depth';

  @override
  String get capsuleGenerationPreviewModelLabel => 'Model';

  @override
  String get patternCardSolutionLabel => 'Breakout idea';

  @override
  String patternCardCreatedAt(String date) {
    return 'Created on $date';
  }

  @override
  String get capsuleDetailTitle => 'Capsule Details';

  @override
  String get capsuleMissing => 'Capsule not found';

  @override
  String capsuleLoadFailed(String error) {
    return 'Failed to load: $error';
  }

  @override
  String capsuleQualityLabel(String rating) {
    return 'Quality: $rating';
  }

  @override
  String capsuleFeedbackCount(int count) {
    return '$count feedback';
  }

  @override
  String capsuleShareCount(int count) {
    return '$count shares';
  }

  @override
  String get capsuleSubmitFeedback => 'Send feedback';

  @override
  String get capsuleShare => 'Share capsule';

  @override
  String get capsuleCopyLink => 'Copy link';

  @override
  String get capsuleShareToGroup => 'Share to group';

  @override
  String get capsuleRateFirst => 'Please rate it first';

  @override
  String get capsuleFeedbackThanks => 'Thanks for the feedback';

  @override
  String capsuleSubmitFailed(String error) {
    return 'Submit failed: $error';
  }

  @override
  String get capsuleFeedbackQuestion => 'Was this capsule helpful?';

  @override
  String get capsuleFeedbackHint => 'Add a note if you want';

  @override
  String get capsuleSubmit => 'Submit';

  @override
  String get capsuleJobsTitle => 'Generation Jobs';

  @override
  String get capsuleNoJobs => 'No generation jobs yet';

  @override
  String get capsuleNoJobsSubtitle =>
      'Adjust your preferences in Settings and generate capsules there.';

  @override
  String capsuleGeneratingProgress(int progress) {
    return 'Generating... $progress%';
  }

  @override
  String capsuleDepthPercent(int percent) {
    return 'Depth: $percent%';
  }

  @override
  String capsuleCuriosityPercent(int percent) {
    return 'Curiosity: $percent%';
  }

  @override
  String capsuleRequestedCount(int count) {
    return 'Requested: $count';
  }

  @override
  String capsuleActualCount(int count) {
    return 'Generated: $count';
  }

  @override
  String capsuleChipLabel(String id) {
    return 'Capsule $id';
  }

  @override
  String get commonRetry => 'Retry';

  @override
  String get capsuleViewCapsules => 'View capsules';

  @override
  String get capsuleNewDiscovery => 'New discovery';

  @override
  String get capsuleRestoreCurrent => 'Move back to current';

  @override
  String get capsuleArchiveAction => 'Archive this capsule';

  @override
  String get capsuleRestored => 'Moved back to your current list';

  @override
  String get capsuleArchivedInfo =>
      'Archived. You can find it later in History.';

  @override
  String get patternListTitle => 'Cognitive Prism';

  @override
  String get patternListEmptyTitle => 'No real behavior patterns yet';

  @override
  String get patternListEmptySubtitle =>
      'Keep logging thoughts and reviewing your work. This space will turn those signals into meaningful patterns.';

  @override
  String get patternArchived => 'Resolved';

  @override
  String get patternTakeAction => 'Act on it';

  @override
  String patternDiscoveredOn(String date) {
    return 'Discovered on $date';
  }

  @override
  String get patternTypeCognitive => 'Cognitive bias';

  @override
  String get patternTypeEmotional => 'Emotional pattern';

  @override
  String get patternTypeExecution => 'Execution habit';

  @override
  String get patternTypeDefault => 'Behavior pattern';

  @override
  String get chatTitle => 'AI Learning Assistant';

  @override
  String get chatSubtitle => 'Here to help anytime';

  @override
  String get chatHistoryTitle => 'Chat History';

  @override
  String get chatNewConversation => 'New chat';

  @override
  String chatHistoryLoadFailed(String error) {
    return 'Failed to load: $error';
  }

  @override
  String chatHistoryLoadMoreFailed(String error) {
    return 'Failed to load more: $error';
  }

  @override
  String get chatHistoryEmpty => 'No history yet';

  @override
  String get chatSessionUntitled => 'Untitled session';

  @override
  String get chatInvalidNavigationTarget => 'Cannot resolve navigation target';

  @override
  String get chatNavigationFailed => 'Navigation failed, please try again';

  @override
  String get chatSessionDataError => 'Session data error, please try again';

  @override
  String get chatWelcomeTitle => 'Hi, I\'m your AI tutor';

  @override
  String get chatQuickActionNewTask => 'Create micro task';

  @override
  String get chatQuickActionNewTaskPrompt => 'Help me create a new micro task';

  @override
  String get chatQuickActionLongPlan => 'Create long-term plan';

  @override
  String get chatQuickActionLongPlanPrompt =>
      'Help me create a long-term study plan';

  @override
  String get chatQuickActionErrorAttribution => 'Error attribution';

  @override
  String get chatQuickActionErrorAttributionPrompt =>
      'I want to analyze recent errors';

  @override
  String get chatPlanUnbound => 'No plan linked';

  @override
  String get chatFileProcessing =>
      'File is processing and will be available for chat soon';

  @override
  String get chatPromptDeepAnalysis1 =>
      'Give a summary first, then show the rationale';

  @override
  String get chatPromptDeepAnalysis2 => 'Only show key conclusions and risks';

  @override
  String get chatPromptDeepAnalysis3 => 'Add a counterpoint to calibrate me';

  @override
  String get chatPromptStudyPlan1 => 'Start with what I can do today';

  @override
  String get chatPromptStudyPlan2 => 'Split into today and this week';

  @override
  String get chatPromptStudyPlan3 => 'Lower the difficulty one level';

  @override
  String get chatPromptErrorDiagnosis1 =>
      'Identify the root cause and evidence';

  @override
  String get chatPromptErrorDiagnosis2 => 'Give one targeted repair exercise';

  @override
  String get chatPromptErrorDiagnosis3 =>
      'How do I avoid repeating this next time?';

  @override
  String get chatPromptExpertAuto1 =>
      'Auto-pick experts and give me a synthesis';

  @override
  String get chatPromptExpertAuto2 => 'Tell me who you invited this round';

  @override
  String get chatPromptExpertAuto3 => 'Compress results into an action list';

  @override
  String get chatPromptDefault1 => 'Answer my question directly';

  @override
  String get chatPromptDefault2 => 'Give me a 3-step action list first';

  @override
  String get chatPromptDefault3 => 'Continue based on my current plan';

  @override
  String get chatHelpful => 'Helpful';

  @override
  String get chatNotHelpful => 'Not helpful';

  @override
  String get chatQuote => 'Quote';

  @override
  String get chatUndo => 'Undo';

  @override
  String get chatRecalledSelf => 'You recalled a message';

  @override
  String get chatRecalledPeer => 'The other side recalled a message';

  @override
  String get chatRead => 'Read';

  @override
  String get chatAgentNavigator => 'Galaxy Navigator';

  @override
  String get chatAgentExamStrategist => 'Exam Strategist';

  @override
  String get chatAgentTimeCoach => 'Time Coach';

  @override
  String get chatAgentDeepAnalyst => 'Deep Analyst';

  @override
  String get chatAgentCorrectionExpert => 'Correction Expert';

  @override
  String get chatAgentLearningBuddy => 'Learning Buddy';

  @override
  String get chatAgentMathExpert => 'Math Expert';

  @override
  String get chatAgentCodingExpert => 'Coding Expert';

  @override
  String get chatAgentWritingExpert => 'Writing Expert';

  @override
  String get chatAgentScienceExpert => 'Science Expert';

  @override
  String get chatAgentSearchExpert => 'Search Expert';

  @override
  String get chatCollabParallel => 'Parallel collaboration';

  @override
  String get chatCollabDebate => 'Debate collaboration';

  @override
  String get chatCollabDelegation => 'Delegation collaboration';

  @override
  String get chatCollabSequential => 'Sequential collaboration';

  @override
  String get chatCollabExpert => 'Expert collaboration';

  @override
  String get chatTeamSheetTitle => 'Build your expert team';

  @override
  String get chatTeamSheetAvailableExperts => 'Available experts';

  @override
  String get chatTeamSheetNoExperts => 'No experts available';

  @override
  String get chatTeamSheetLoading => 'Loading expert catalog...';

  @override
  String get chatTeamSheetLoadFailed => 'Failed to load, please try again';

  @override
  String get chatTeamSheetCollaborationMode => 'Collaboration mode';

  @override
  String chatTeamSheetSelectedExperts(int count) {
    return 'Selected $count experts';
  }

  @override
  String get chatTeamSheetEnterExpert => 'Enter expert mode';

  @override
  String get chatTeamSheetStartCollaboration => 'Start collaboration';

  @override
  String get chatCollabAuto => 'Auto';

  @override
  String get chatCollabAutoDesc =>
      'The system picks the best collaboration mode for your question';

  @override
  String get chatCollabSequentialShort => 'Sequential';

  @override
  String get chatCollabSequentialDesc =>
      'Experts analyze one by one, and later experts can build on earlier conclusions';

  @override
  String get chatCollabParallelShort => 'Parallel';

  @override
  String get chatCollabParallelDesc =>
      'All experts analyze at the same time, then results are merged';

  @override
  String get chatCollabDebateShort => 'Debate';

  @override
  String get chatCollabDebateDesc =>
      'Experts analyze independently, cross-review, and converge on consensus';

  @override
  String get chatCollabDelegationShort => 'Delegation';

  @override
  String get chatCollabDelegationDesc =>
      'The lead expert splits tasks and delegates to others, then summarizes';

  @override
  String get chatLabelMe => 'Me';

  @override
  String get chatLabelAssistant => 'AI Assistant';

  @override
  String get chatNoContent => 'No content';

  @override
  String get chatTransparencyTitle => 'Transparency';

  @override
  String chatActiveToolsCount(int count) {
    return '$count tools';
  }

  @override
  String get chatActiveTools => 'Active tools';

  @override
  String get chatTokenStats => 'Token stats';

  @override
  String get chatPromptTokens => 'Prompt tokens';

  @override
  String get chatCompletionTokens => 'Completion tokens';

  @override
  String get chatTokenUsageToday => 'Today used';

  @override
  String get chatTokenCostEstimate => 'Cost estimate';

  @override
  String get chatExecutionSteps => 'Execution steps';

  @override
  String chatExecutionStepsCount(int count) {
    return '$count steps';
  }

  @override
  String get chatModeSelect => 'Choose mode';

  @override
  String chatModeTeamSummary(int count, String mode) {
    return '$count experts · $mode';
  }

  @override
  String get chatModeCustomTeamLabel => 'Custom team';

  @override
  String get chatModeCustomTeamTitle => 'Custom expert team';

  @override
  String get chatModeCustomTeamSubtitle =>
      'Choose experts and a collaboration mode';

  @override
  String get chatMetadataContinuity => 'Continuity';

  @override
  String get chatMetadataEvidence => 'Evidence';

  @override
  String get chatMetadataNext => 'Next steps';

  @override
  String get chatMetadataCollaboration => 'Collaboration';

  @override
  String get chatLoginRequired => 'Please log in first';

  @override
  String get chatReviewRegenerationRequested => 'Regeneration requested';

  @override
  String get chatReviewHumanReviewRequested => 'Manual review requested';

  @override
  String get chatReviewOverrideAcceptedEvenFail =>
      'Accepted content (despite failing review)';

  @override
  String get chatReviewOverrideRejectedEvenPass =>
      'Rejected content (despite passing review)';

  @override
  String get chatSubmitFailedRetry => 'Submit failed, please try again';

  @override
  String get chatAppealSubmitted => 'Appeal submitted, processing...';

  @override
  String get commonBack => 'Back';

  @override
  String get noData => 'No Data';

  @override
  String get operationSuccess => 'Success';

  @override
  String get operationFailed => 'Failed';

  @override
  String get confirmDeleteTitle => 'Confirm Delete';

  @override
  String get confirmDeleteMessage => 'This cannot be undone';

  @override
  String get errorBookTitle => 'Error Archive';

  @override
  String get errorBookTabAll => 'All';

  @override
  String get errorBookTabNeedReview => 'Need Review';

  @override
  String get errorBookAddError => 'Add Error';

  @override
  String get errorBookAddFirst => 'Add First Error';

  @override
  String get errorBookFilterTitle => 'Filter Options';

  @override
  String get errorBookSearchHint => 'Search question content...';

  @override
  String get errorBookNoErrors => 'No errors recorded yet';

  @override
  String get errorBookNoErrorsHint => 'Tap the + button to add an error';

  @override
  String get errorBookNoReview => 'No errors need review';

  @override
  String get errorBookNoReviewHint => 'Great job! Keep it up';

  @override
  String get errorBookDeleteSuccess => 'Deleted';

  @override
  String get errorBookDeleteFailed => 'Delete Failed';

  @override
  String get errorBookDeleteConfirmTitle => 'Confirm Delete';

  @override
  String get errorBookDeleteConfirmMessage =>
      'This cannot be undone. Delete this error?';

  @override
  String get errorBookDetailTitle => 'Error Details';

  @override
  String get errorBookEdit => 'Edit';

  @override
  String get errorBookReanalyze => 'Reanalyze';

  @override
  String get errorBookDelete => 'Delete';

  @override
  String errorBookCreatedAt(String date) {
    return 'Created at $date';
  }

  @override
  String errorBookMasteryPercent(int percent) {
    return '$percent% Mastery';
  }

  @override
  String get errorBookSimilarSummary => 'Similar Error Analysis';

  @override
  String get errorBookRootCause => 'Root Cause';

  @override
  String get errorBookStrategySuggestions => 'Strategy Suggestions';

  @override
  String get errorBookSimilarErrors => 'Similar Errors';

  @override
  String get errorBookSimilarCauseFallback => 'Uncategorized';

  @override
  String get errorBookQuestionContent => 'Question Content';

  @override
  String get errorBookImageLoadFailed => 'Image Load Failed';

  @override
  String get errorBookAnswerComparison => 'Answer Comparison';

  @override
  String get errorBookYourAnswer => 'Your Answer';

  @override
  String get errorBookCorrectAnswer => 'Correct Answer';

  @override
  String get errorBookAiAnalysis => 'AI Analysis';

  @override
  String get errorBookKnowledgeLinks => 'Knowledge Links';

  @override
  String get errorBookKnowledgeLinkTooltip => 'View Learning Path';

  @override
  String errorBookKnowledgeLinkSnack(String nodeName) {
    return 'Navigating to $nodeName knowledge point';
  }

  @override
  String get errorBookReviewStats => 'Review Statistics';

  @override
  String get errorBookLastReview => 'Last Review';

  @override
  String get errorBookNextReview => 'Next Review';

  @override
  String get errorBookStartReview => 'Start Review';

  @override
  String get errorBookLoadFailed => 'Load Failed';

  @override
  String get errorBookEditInProgress => 'Edit feature coming soon';

  @override
  String get errorBookReanalyzing => 'Reanalyzing...';

  @override
  String get errorBookReviewInProgress => 'Review feature coming soon';

  @override
  String errorBookDeleteFailedMessage(String error) {
    return 'Delete failed: $error';
  }

  @override
  String errorBookCognitiveFilter(String dimension) {
    return 'Reviewing specifically for \"$dimension\" dimension';
  }

  @override
  String errorBookReviewCount(int count) {
    return 'Reviewed $count times';
  }

  @override
  String get errorBookAIAnalyzed => 'AI Analyzed';

  @override
  String errorBookTimeAgoMinutes(int count) {
    return '$count min ago';
  }

  @override
  String errorBookTimeAgoHours(int count) {
    return '$count hr ago';
  }

  @override
  String errorBookTimeAgoDays(int count) {
    return '$count days ago';
  }

  @override
  String get reviewModeToday => 'Today\'s Review';

  @override
  String get reviewModeTodayDesc => 'Complete all errors due today';

  @override
  String get reviewModeBySubject => 'By Subject';

  @override
  String get reviewModeBySubjectDesc => 'Select a subject for focused review';

  @override
  String get reviewModeWeakest => 'Weakest Areas';

  @override
  String get reviewModeWeakestDesc => 'Prioritize errors with lowest mastery';

  @override
  String get reviewModeRandom => 'Random Quiz';

  @override
  String get reviewModeRandomDesc => 'Randomly select errors to review';

  @override
  String reviewProgress(int current, int total) {
    return 'Progress: $current/$total';
  }

  @override
  String get reviewQuestion => 'Question';

  @override
  String get reviewYourAnswer => 'Your Answer';

  @override
  String get reviewCorrectAnswer => 'Correct Answer';

  @override
  String get reviewAIAnalysis => 'AI Analysis';

  @override
  String get reviewHideAnalysis => 'Hide';

  @override
  String get reviewViewAnalysis => 'View AI Analysis';

  @override
  String get reviewViewAnswer => 'View Answer';

  @override
  String get reviewViewAnswerHint =>
      'Think about the answer first, then reveal';

  @override
  String reviewSubmitFailed(String error) {
    return 'Submit failed: $error';
  }

  @override
  String get reviewNoErrorsToday => 'No errors need review today';

  @override
  String get reviewKeepGoing => 'Great job! Keep it up';

  @override
  String get reviewComplete => 'Review Complete!';

  @override
  String reviewTotalReviewed(int count) {
    return 'Reviewed $count questions this session';
  }

  @override
  String get reviewResults => 'Review Results';

  @override
  String get reviewRemembered => 'Remembered';

  @override
  String get reviewFuzzy => 'Fuzzy';

  @override
  String get reviewForgotten => 'Forgotten';

  @override
  String get reviewEncourageExcellent => 'Excellent! Very solid mastery 🎉';

  @override
  String get reviewEncourageGood => 'Great! Keep up the momentum 💪';

  @override
  String get reviewEncourageFair => 'Good! More review will help 📚';

  @override
  String get reviewEncourageNeedsWork =>
      'Keep going! Practice makes perfect 🌟';

  @override
  String get reviewBackToList => 'Back to List';

  @override
  String get reviewAnotherRound => 'Another Round';

  @override
  String get reviewConfirmExitTitle => 'Confirm Exit';

  @override
  String get reviewConfirmExitMessage => 'Review not completed. Exit anyway?';

  @override
  String get reviewContinue => 'Continue Review';

  @override
  String get reviewExit => 'Exit';

  @override
  String get reviewNoMatchingErrors => 'No matching errors found';

  @override
  String get communityTitle => 'Community';

  @override
  String get communitySearch => 'Search';

  @override
  String get communitySearchUsers => 'Search Users';

  @override
  String get communitySearchGroups => 'Search Groups';

  @override
  String get communityDiscoverFriends => 'Discover Friends';

  @override
  String get communityDiscoverFriendsHint => 'View recommended friends';

  @override
  String get communityCreateGroup => 'Create Group';

  @override
  String get communityCreateGroupHint => 'Create a new study group';

  @override
  String get communityActions => 'Community Actions';

  @override
  String get communityNoFriends => 'No friends yet';

  @override
  String get communityNoGroups => 'No groups joined';

  @override
  String get communityStatusOnline => 'Online';

  @override
  String get communityStatusOffline => 'Offline';

  @override
  String get communityFocusModeOn => 'Focus mode on';

  @override
  String get communityFocusModeOff => 'Enable focus mode';

  @override
  String get communityFocusModeEnabled =>
      'Focus mode enabled. You won\'t be disturbed';

  @override
  String get communityFocusModeDisabled => 'Focus mode disabled';

  @override
  String get communityTabFriends => 'Friends';

  @override
  String get communityTabGroups => 'Groups';

  @override
  String get communityAddFriend => 'Add Friend';

  @override
  String communityMembers(int count) {
    return '$count members';
  }

  @override
  String get taskMonitorTitle => 'Background Tasks';

  @override
  String get taskMonitorFilterAll => 'All';

  @override
  String get taskMonitorFilterRunning => 'Running';

  @override
  String get taskMonitorFilterCompleted => 'Completed';

  @override
  String get taskMonitorFilterFailed => 'Failed';

  @override
  String get taskMonitorEmpty => 'No background tasks';

  @override
  String get taskMonitorStatusPending => 'Pending';

  @override
  String get taskMonitorStatusCancelled => 'Cancelled';

  @override
  String get planHistoryTitle => 'Plan History';

  @override
  String get planHistoryEmpty => 'No plan history';

  @override
  String get planHistoryRestore => 'Restore Plan';

  @override
  String get planHistoryRestoreSuccess => 'Plan restored';

  @override
  String get planHistoryDeleteConfirm => 'Delete this plan history?';

  @override
  String get planTypeSprint => 'Sprint Plan';

  @override
  String get planTypeGrowth => 'Growth Plan';

  @override
  String planProgressPercent(String percent) {
    return '$percent% Complete';
  }

  @override
  String get authForgotPassword => 'Forgot Password?';

  @override
  String get authUserAgreement => 'User Agreement';

  @override
  String get authPrivacyPolicy => 'Privacy Policy';

  @override
  String get authLoginAgreement => 'By logging in, you agree to';

  @override
  String get authAnd => 'and';

  @override
  String get authDemoLogin => 'Demo Account Login';

  @override
  String get authResetPassword => 'Reset Password';

  @override
  String get authResetPasswordHint =>
      'Enter your email and we\'ll send you a reset link';

  @override
  String get authSendResetEmail => 'Send Reset Email';

  @override
  String get authResetEmailSent => 'Reset email sent';

  @override
  String get authBackToLogin => 'Back to Login';

  @override
  String get authForgotPasswordTitle => 'Forgot Password';

  @override
  String get authForgotPasswordHint =>
      'Enter your registered email and we\'ll send you a reset code.';

  @override
  String get authInvalidEmail => 'Please enter a valid email';

  @override
  String get authHaveResetCode => 'I already have a reset code';

  @override
  String get toolsLibraryTitle => 'Tool Library';

  @override
  String get toolsTabBrowse => 'Browse';

  @override
  String get toolsTabManage => 'Manage';

  @override
  String get toolsSearchHint => 'Search tools or keywords';

  @override
  String get toolsRecentTitle => 'Recently Used';

  @override
  String get toolsManagePinned => 'Manage Pinned';

  @override
  String get toolsCategoryInput => 'Input Processing';

  @override
  String get toolsCategoryStudy => 'Study Aids';

  @override
  String get toolsCategoryEfficiency => 'Efficiency';

  @override
  String get toolsCategoryCognition => 'Cognitive Insights';

  @override
  String get toolsNoTools => 'No tools available';

  @override
  String get toolsPinnedEmpty => 'No pinned tools yet';

  @override
  String get toolsManageHint =>
      'Home screen shows top 4, expanded shows top 8. Drag to reorder.';

  @override
  String get toolsBackToBrowse => 'Back to Browse';

  @override
  String get toolsPositionFirstScreen => 'First Screen';

  @override
  String get toolsPositionExpanded => 'Expanded Area';

  @override
  String get toolsPositionMore => 'More Page';

  @override
  String get knowledgeLoadFailed => 'Failed to load knowledge node';

  @override
  String get knowledgeReload => 'Reload';

  @override
  String get knowledgeGeneratePath => 'Generate Learning Path';

  @override
  String get knowledgeDescription => 'Description';

  @override
  String get knowledgeNoDescription => 'No description';

  @override
  String get knowledgeRelatedNodes => 'Related Nodes';

  @override
  String get knowledgePrerequisites => 'Prerequisites';

  @override
  String get knowledgeMasteryProgress => 'Mastery Progress';

  @override
  String get knowledgeKeywords => 'Keywords';

  @override
  String get knowledgeEstimated => 'Estimated';

  @override
  String get knowledgeMinutes => 'minutes';

  @override
  String get knowledgeRelatedTasks => 'Related Tasks';

  @override
  String get knowledgeRelatedPlans => 'Related Plans';

  @override
  String get knowledgeMastery => 'Mastery';

  @override
  String get knowledgeStudyMinutes => 'Study Minutes';

  @override
  String get knowledgeStudyCount => 'Study Count';

  @override
  String get knowledgeNextReview => 'Next Review';

  @override
  String get knowledgeDecayPaused => 'Forgetting Decay Paused';

  @override
  String get knowledgeToday => 'Today';

  @override
  String get knowledgeTomorrow => 'Tomorrow';

  @override
  String knowledgeDaysLater(int days) {
    return '$days days later';
  }

  @override
  String knowledgeWeeksLater(int weeks) {
    return '$weeks weeks later';
  }

  @override
  String get seedLibraryTitle => 'Seed Library';

  @override
  String get seedLibrarySearchHint => 'Search seed libraries...';

  @override
  String get seedLibraryCreate => 'Create Seed Library';

  @override
  String get seedLibraryNotFound => 'Seed library not found';

  @override
  String get seedLibraryDeleteConfirm =>
      'Delete this seed library? This action cannot be undone.';

  @override
  String get seedLibraryEmpty => 'No seed libraries yet';

  @override
  String get seedLibraryCreateFirst =>
      'Create a new seed library to get started';

  @override
  String seedLibraryItemCount(int count) {
    return '$count items';
  }

  @override
  String seedLibraryLastUpdated(String date) {
    return 'Last updated: $date';
  }

  @override
  String get seedLibraryDetail => 'Seed Library Details';

  @override
  String get seedLibraryFilter => 'Filter';

  @override
  String get seedLibraryCategory => 'Category';

  @override
  String get seedLibraryVisibility => 'Visibility';

  @override
  String get seedLibraryClear => 'Clear';

  @override
  String get seedLibraryApply => 'Apply';

  @override
  String get seedLibrarySubscribe => 'Subscribe';

  @override
  String get seedLibraryUnsubscribe => 'Unsubscribe';

  @override
  String get seedLibraryContentItems => 'Content Items';

  @override
  String get seedLibraryNoContent => 'No content yet';

  @override
  String get seedLibraryContent => 'Content';

  @override
  String get seedLibrarySubscribers => 'Subscribers';

  @override
  String get seedLibraryUsage => 'Usage';

  @override
  String get seedLibraryQualityScore => 'Quality Score';

  @override
  String get seedLibraryDeleteTitle => 'Delete Seed Library';

  @override
  String seedLibraryDeleteFailed(String error) {
    return 'Delete failed: $error';
  }

  @override
  String get translationHistoryTitle => 'Translation History';

  @override
  String get translationClearHistory => 'Clear History';

  @override
  String get translationTranslating => 'Translating...';

  @override
  String get translationSaveToVocabulary => 'Save to Vocabulary';

  @override
  String get translationCopy => 'Copy';

  @override
  String get translationCopied => 'Copied';

  @override
  String get translationSearchHint => 'Search translation records...';

  @override
  String get translationNoHistory => 'No translation records';

  @override
  String get translationStartTranslate =>
      'Translations will appear here after you start';

  @override
  String get translationClearConfirm =>
      'Are you sure you want to clear all translation history?';

  @override
  String get translationClearConfirmDetail => 'This action cannot be undone';

  @override
  String get translationClearAll => 'Clear History';

  @override
  String get translationFilterAll => 'All';

  @override
  String get translationFilterFavorites => 'Favorites';

  @override
  String get translationFilterImportant => 'Important';

  @override
  String get translationFilterRecent => 'Recent';

  @override
  String get translationNoSearchResults => 'No results found';

  @override
  String get translationTryOtherKeywords => 'Try other keywords';

  @override
  String get translationNoFavorites => 'No favorites yet';

  @override
  String get translationNoFavoritesHint => 'Star translations to save them';

  @override
  String get translationNoImportant => 'No important translations';

  @override
  String get translationNoImportantHint =>
      '4-star and above translations will appear here';

  @override
  String get translationNoRecordsHint =>
      'Translations are automatically saved when used';

  @override
  String get translationRating => 'Rating';

  @override
  String get translationSelectImportance => 'Select importance level';

  @override
  String get translationDelete => 'Delete Translation';

  @override
  String get translationDeleteConfirm =>
      'Are you sure you want to delete this translation?';

  @override
  String get translationOriginal => 'Original';

  @override
  String get translationTranslated => 'Translation';

  @override
  String get translationHistorySessionOnly =>
      'History is only valid for the current session';

  @override
  String get translationJustNow => 'Just now';

  @override
  String translationMinutesAgo(int minutes) {
    return '${minutes}m ago';
  }

  @override
  String translationHoursAgo(int hours) {
    return '${hours}h ago';
  }

  @override
  String get translationToday => 'Today';

  @override
  String get translationYesterday => 'Yesterday';

  @override
  String translationDaysAgo(int days) {
    return '${days}d ago';
  }

  @override
  String get translationSourceLanguage => 'Source Language';

  @override
  String get translationTargetLanguage => 'Target Language';

  @override
  String get translationSwapLanguages => 'Swap Languages';

  @override
  String get translationDetectLanguage => 'Detect Language';

  @override
  String get translationHistoryEmpty => 'No translation history';

  @override
  String get memoryEvidenceChain => 'Evidence Chain';

  @override
  String get memoryNoEvidence => 'No Evidence';

  @override
  String get memoryCurrentVersion => 'Current Version';

  @override
  String get memoryVersionHistory => 'Version History';

  @override
  String get memorySortNewest => 'Newest';

  @override
  String get memorySortOldest => 'Oldest';

  @override
  String get memorySortImportance => 'Importance';

  @override
  String get memoryEvidenceResolveFailed => 'Evidence resolve failed';

  @override
  String get memoryStatus => 'Status';

  @override
  String get memoryGoalDate => 'Goal Date';

  @override
  String get memoryDeadline => 'Deadline';

  @override
  String get memoryLastUpdated => 'Last Updated';

  @override
  String get memorySource => 'Source';

  @override
  String get memoryOccurredAt => 'Occurred At';

  @override
  String get memoryImportanceScore => 'Importance';

  @override
  String get memoryRetractedAt => 'Retracted At';

  @override
  String get memoryUpdate => 'Update';

  @override
  String get memoryConfidence => 'Confidence';

  @override
  String get memoryDiff => 'Diff';

  @override
  String get memoryRevertToVersion => 'Revert to this version';

  @override
  String get memoryNeedEnableRetraction =>
      'Need to enable ENABLE_MEMORY_RETRACTION';

  @override
  String get memoryInitialVersion => 'Initial version';

  @override
  String get memoryNoChanges => 'No changes';

  @override
  String get memoryRevertNotEnabled => 'Revert feature not enabled';

  @override
  String get memoryWhyThisMemory => 'Why this memory?';

  @override
  String get memoryEvidenceCount => 'Evidence';

  @override
  String get memoryVersions => 'Versions';

  @override
  String get memoryBudget => 'Budget';

  @override
  String get memoryViewEvidence => 'View Evidence';

  @override
  String get memoryAllowedCapture => 'Allowed capture';

  @override
  String get memoryCaptureLevel => 'Capture level';

  @override
  String get memoryTypeNone => 'None';

  @override
  String get memoryTypePreference => 'Preferences';

  @override
  String get memoryTypeGoal => 'Goals';

  @override
  String get memoryTypeEpisodic => 'Episodic';

  @override
  String get memoryDisabledHint =>
      'Long-term memory is currently disabled, such memories will not be recorded.';

  @override
  String get memoryPreferenceDisabledHint =>
      'Preference capture is currently disabled, such memories will not be recorded.';

  @override
  String get memoryGoalDisabledHint =>
      'Goal capture is currently disabled, such memories will not be recorded.';

  @override
  String get memoryEpisodicDisabledHint =>
      'Episodic capture is currently disabled, such memories will not be recorded.';

  @override
  String get memorySourceBlockedHint =>
      'This source is blocked, such memories will not be recorded.';

  @override
  String get memoryKeyBlockedHint =>
      'This preference is blocked, such memories will not be recorded.';

  @override
  String get memoryExplanationPreference =>
      'Captured because your preference updated recently.';

  @override
  String get memoryExplanationEpisodic =>
      'Captured because this experience was marked important.';

  @override
  String get memoryExplanationGoal =>
      'Captured to keep your active goals visible.';

  @override
  String get memoryCopied => 'Memory content copied';

  @override
  String get memoryExportView => 'Export View';

  @override
  String get memoryCorrectionActions => 'Correction Actions';

  @override
  String get memoryCorrectionReject => 'Not true';

  @override
  String get memoryCorrectionNoLongerApplies => 'No longer applies';

  @override
  String get memoryCorrectionLowerConfidence => 'Lower confidence';

  @override
  String get memoryCorrectionMerge => 'Merge';

  @override
  String get memoryMergeComingSoon => 'Merge feature coming soon';

  @override
  String get memoryCorrectionSubmitted => 'Correction submitted';

  @override
  String get memoryCorrectionFailed => 'Correction failed';

  @override
  String get memoryHistoryLoadFailed => 'Failed to load history';

  @override
  String get memorySettingsLoadFailed => 'Failed to load memory settings';

  @override
  String get memoryAddEvidence => 'Add Evidence';

  @override
  String get memoryEvidenceType => 'Evidence Type';

  @override
  String get memoryEvidenceSource => 'Source';

  @override
  String get memoryEvidenceContent => 'Content';

  @override
  String get shareOptionsTitle => 'Share Achievement';

  @override
  String get shareToWeChatFriends => 'Share to WeChat Friends';

  @override
  String get shareToWeChatMoments => 'Share to Moments';

  @override
  String get shareToSystem => 'System Share';

  @override
  String get shareToCommunity => 'Share to Community';

  @override
  String get saveImageToGallery => 'Save Image';

  @override
  String get copyDeepLink => 'Copy Link';

  @override
  String get linkCopied => 'Link copied';

  @override
  String get wechatNotInstalled => 'Please install WeChat first';

  @override
  String get shareTemplateTitle => 'Choose Template';

  @override
  String get shareTemplateCosmic => 'Cosmic';

  @override
  String get shareTemplateMinimal => 'Minimal';

  @override
  String get shareTemplateNeon => 'Neon';

  @override
  String get shareTemplateElegant => 'Elegant';

  @override
  String get shareTemplateCosmicDesc =>
      'Deep blue gradient, golden particles, soft glow';

  @override
  String get shareTemplateMinimalDesc =>
      'Solid color, minimal lines, black text';

  @override
  String get shareTemplateNeonDesc => 'Pure black, neon glow, cyberpunk colors';

  @override
  String get shareTemplateElegantDesc =>
      'Beige and gold, elegant serif, gold accents';

  @override
  String get sharePrivacyTitle => 'Privacy Settings';

  @override
  String get sharePrivacyDisplayName => 'Display Name';

  @override
  String get sharePrivacyDisplayNameHint => 'Use default nickname';

  @override
  String get sharePrivacyDisplayNameNote =>
      'Leave empty to use your default nickname';

  @override
  String get sharePrivacyShowAvatar => 'Show Avatar';

  @override
  String get sharePrivacyShowAvatarDesc =>
      'Display your avatar on the share card';

  @override
  String get sharePrivacyShowDate => 'Show Unlock Date';

  @override
  String get sharePrivacyShowDateDesc => 'Display the achievement unlock date';

  @override
  String get sharePrivacyShowStats => 'Show Progress Stats';

  @override
  String get sharePrivacyShowStatsDesc => 'Display progress bar and statistics';

  @override
  String get sharePrivacyShowFirstBadge => 'First Unlocker Badge';

  @override
  String get sharePrivacyShowFirstBadgeDesc =>
      'Show exclusive badge if you\'re the first unlocker';

  @override
  String get sharePreviewLoading => 'Generating preview...';

  @override
  String get sharePreviewError => 'Preview generation failed';

  @override
  String get shareRegenerateCard => 'Regenerate';

  @override
  String get notificationPermissionStatus => 'Notification Permission';

  @override
  String get notificationPermissionGranted => 'Granted';

  @override
  String get notificationPermissionDenied =>
      'Notification permission denied, please enable in system settings';

  @override
  String get notificationPermissionPartial =>
      'Some notification features are restricted, recommend enabling full permissions';

  @override
  String get notificationPermissionRequest => 'Request Permission';

  @override
  String get notificationPermissionOpenSettings => 'Open Settings';

  @override
  String get notificationPermissionDeniedHint =>
      'Notification permission denied. Please enable in system settings.';

  @override
  String get notificationPermissionPartialHint =>
      'Some notification features are limited. Consider enabling full permissions.';

  @override
  String get visualElementsTitle => 'Visual Elements';

  @override
  String get visualElementsUnlockProgress => 'Unlock Progress';

  @override
  String get visualElementsEquipped => 'Equipped';

  @override
  String get visualElementsRecommended => 'For You';

  @override
  String get visualRecommendationFocus => 'Great for focus';

  @override
  String get visualRecommendationRelax => 'Perfect for relaxation';

  @override
  String get visualRecommendationSprint => 'Boost your sprint';

  @override
  String get visualRecommendationNight => 'Night-friendly';

  @override
  String get visualRecommendationStreak => 'Streak boost';

  @override
  String get visualElementTabAll => 'All';

  @override
  String get visualElementTabBackground => 'Background';

  @override
  String get visualElementTabParticle => 'Particles';

  @override
  String get visualElementTabEffect => 'Effects';

  @override
  String get visualElementTabUnlocked => 'Unlocked';

  @override
  String get visualElementEmpty => 'No visual elements';

  @override
  String get visualElementFilter => 'Filter';

  @override
  String get visualElementApplyFilter => 'Apply Filter';

  @override
  String get visualElementType => 'Type';

  @override
  String get visualElementCategory => 'Category';

  @override
  String get visualElementSource => 'Source';

  @override
  String get visualElementRarity => 'Rarity';

  @override
  String get visualElementEquipped => 'Equipped';

  @override
  String get visualElementUnlocked => 'Unlocked';

  @override
  String get visualElementLocked => 'Locked';

  @override
  String get visualElementEquip => 'Equip';

  @override
  String get visualElementUnequip => 'Unequip';

  @override
  String get visualElementEquipSuccess => 'Equipped successfully';

  @override
  String get visualElementEquipFailed => 'Failed to equip';

  @override
  String get visualElementUnequipSuccess => 'Unequipped';

  @override
  String get visualElementUnequipFailed => 'Failed to unequip';

  @override
  String get visualElementUnlockSystem => 'System Gift';

  @override
  String get visualElementUnlockAchievement => 'Achievement Reward';

  @override
  String get visualElementUnlockShop => 'Shop Purchase';

  @override
  String get visualElementUnlockEvent => 'Event Reward';

  @override
  String get visualElementUnlockSeason => 'Season Reward';

  @override
  String get visualElementUnlockHintSystem => 'Gifted by system';

  @override
  String visualElementUnlockHintAchievement(Object achievement) {
    return 'Unlock by completing achievement \'$achievement\'';
  }

  @override
  String get visualElementUnlockHintAchievementDefault =>
      'Unlock by completing achievement';

  @override
  String visualElementUnlockHintShop(Object price) {
    return 'Purchase for $price photons in shop';
  }

  @override
  String get visualElementUnlockHintShopDefault => 'Purchase in shop';

  @override
  String get visualElementUnlockHintEvent =>
      'Participate in limited-time event';

  @override
  String get visualElementUnlockHintSeason => 'Season reward';

  @override
  String get visualElementBackground => 'Background';

  @override
  String get visualElementParticle => 'Particle';

  @override
  String get visualElementEffect => 'Effect';

  @override
  String get visualElementBundle => 'Bundle';

  @override
  String get visualElementsEntrySubtitle => 'Customize your scene';

  @override
  String get visualElementShare => 'Share';

  @override
  String visualElementShareMessage(Object name) {
    return 'Check out my \"$name\" visual element in Sparkle!';
  }

  @override
  String visualElementShareFailed(Object error) {
    return 'Share failed: $error';
  }

  @override
  String get visualElementShareUnavailable => 'Preview not ready yet';

  @override
  String get visualElementEventTitle => 'Limited-Time Event';

  @override
  String visualElementEventEndsIn(Object time) {
    return 'Ends in $time';
  }

  @override
  String get visualElementEventEnded => 'Event ended';

  @override
  String visualElementEventCountdownDays(Object days, Object hours) {
    return '${days}d ${hours}h';
  }

  @override
  String visualElementEventCountdownHours(Object hours, Object minutes) {
    return '${hours}h ${minutes}m';
  }

  @override
  String visualElementEventCountdownMinutes(Object minutes) {
    return '${minutes}m';
  }

  @override
  String get visualElementCategorySpace => 'Space';

  @override
  String get visualElementCategoryNature => 'Nature';

  @override
  String get visualElementCategoryCyberpunk => 'Cyberpunk';

  @override
  String get visualElementCategoryAbstract => 'Abstract';

  @override
  String get visualElementCategoryAmbient => 'Ambient';

  @override
  String visualElementEmptyType(Object type) {
    return 'No $type elements';
  }

  @override
  String get visualElementStatus => 'Status';

  @override
  String get visualElementSort => 'Sort';

  @override
  String get visualElementSortDefault => 'Default';

  @override
  String get visualElementSortName => 'Name';

  @override
  String get visualElementSortRarity => 'Rarity';

  @override
  String get visualElementSortUnlockDate => 'Unlock Date';

  @override
  String get visualElementUnlockTitle => 'Visual Element Unlocked';

  @override
  String get visualElementUnlockSubtitle => 'You\'ve got a new visual element!';

  @override
  String get visualElementViewCollection => 'View Collection';

  @override
  String get achievementMapFocusTooltip => 'Focus on nearest achievement';

  @override
  String achievementMapFocusHint(Object name) {
    return 'Try unlocking: $name';
  }

  @override
  String get cognitiveDimensionMemory => 'Memory';

  @override
  String get cognitiveDimensionUnderstanding => 'Understanding';

  @override
  String get cognitiveDimensionApplication => 'Application';

  @override
  String get cognitiveDimensionAnalysis => 'Analysis';

  @override
  String get cognitiveDimensionEvaluation => 'Evaluation';

  @override
  String get cognitiveDimensionCreation => 'Creation';

  @override
  String get photonTransactionGrantAchievement => 'Achievement reward';

  @override
  String get photonTransactionGrantDailyFirst => 'Daily first reward';

  @override
  String get photonTransactionGrantContract => 'Contract reward';

  @override
  String get photonTransactionGrantContractBonus => 'Contract bonus';

  @override
  String get photonTransactionDeductContractStake => 'Contract stake';

  @override
  String get photonTransactionPurchase => 'Purchase';

  @override
  String get photonTransactionTransferOut => 'Transfer out';

  @override
  String get photonTransactionTransferIn => 'Transfer in';

  @override
  String get photonTransactionRefund => 'Refund';

  @override
  String get photonTransactionPenalty => 'Penalty';

  @override
  String get photonTransactionAdminAdjustment => 'Admin adjustment';

  @override
  String get shopItemTypeSkin => 'Skin';

  @override
  String get shopItemTypeTitle => 'Title';

  @override
  String get shopItemTypeConsumable => 'Consumable';

  @override
  String get shopItemTypeBoost => 'Boost';

  @override
  String get shopItemTypeVisualElement => 'Visual element';

  @override
  String get taskDueDateUnset => 'No due date';

  @override
  String chatAchievementUnlocked(Object arg0) {
    return '$arg0';
  }

  @override
  String chatActionErrorSuggestion(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatActionErrorTitle => 'Chat Action Error Title';

  @override
  String get chatActionIgnore => 'Chat Action Ignore';

  @override
  String get chatActionLater => 'Chat Action Later';

  @override
  String get chatActionReviewed => 'Chat Action Reviewed';

  @override
  String get chatActionStatusCompleted => 'Chat Action Status Completed';

  @override
  String get chatActionStatusConfirmed => 'Chat Action Status Confirmed';

  @override
  String get chatActionStatusDismissed => 'Chat Action Status Dismissed';

  @override
  String get chatActionStatusFailed => 'Chat Action Status Failed';

  @override
  String get chatActionStatusProcessing => 'Chat Action Status Processing';

  @override
  String chatActionStatusUpdate(Object arg0) {
    return '$arg0';
  }

  @override
  String chatActionSuggestedActions(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatActionTitleAddError => 'Chat Action Title Add Error';

  @override
  String get chatActionTitleBlockedInput => 'Chat Action Title Blocked Input';

  @override
  String get chatActionTitleContinuity => 'Chat Action Title Continuity';

  @override
  String get chatActionTitleCreatePlan => 'Chat Action Title Create Plan';

  @override
  String get chatActionTitleCreateTask => 'Chat Action Title Create Task';

  @override
  String get chatActionTitleDefault => 'Chat Action Title Default';

  @override
  String get chatActionTitleEvolution => 'Chat Action Title Evolution';

  @override
  String get chatActionTitleExecutionSummary =>
      'Chat Action Title Execution Summary';

  @override
  String get chatActionTitleFocusSprint => 'Chat Action Title Focus Sprint';

  @override
  String get chatActionTitleModeExplanation =>
      'Chat Action Title Mode Explanation';

  @override
  String get chatActionTitleNextActions => 'Chat Action Title Next Actions';

  @override
  String get chatActionTitleNightlyReview => 'Chat Action Title Nightly Review';

  @override
  String get chatActionTitleProgress => 'Chat Action Title Progress';

  @override
  String get chatActionTitleReflection => 'Chat Action Title Reflection';

  @override
  String get chatActionTitleSourceSummary => 'Chat Action Title Source Summary';

  @override
  String get chatActionTitleSystemUpdate => 'Chat Action Title System Update';

  @override
  String get chatActionTitleTaskList => 'Chat Action Title Task List';

  @override
  String get chatActionTitleUpdatePreference =>
      'Chat Action Title Update Preference';

  @override
  String get chatActionViewNextSteps => 'Chat Action View Next Steps';

  @override
  String get chatActionViewSources => 'Chat Action View Sources';

  @override
  String get chatAgentRouting => 'Chat Agent Routing';

  @override
  String chatAgentRoutingFallback(Object arg0) {
    return '$arg0';
  }

  @override
  String chatAgentRoutingStrategy(Object arg0) {
    return '$arg0';
  }

  @override
  String chatAlignmentScoreLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String chatAudioParseFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String chatAudioRecordFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String chatAudioStartFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String chatAudioWsConnectFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatAuthExpired => 'Chat Auth Expired';

  @override
  String get chatAuthRefreshing => 'Chat Auth Refreshing';

  @override
  String get chatBlockedInputTitle => 'Chat Blocked Input Title';

  @override
  String chatCitationLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String chatCitationRelevance(Object arg0) {
    return '$arg0';
  }

  @override
  String chatCitationSourcesCount(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatCollabTimelineTitle => 'Chat Collab Timeline Title';

  @override
  String get chatComparisonAfter => 'Chat Comparison After';

  @override
  String get chatComparisonBefore => 'Chat Comparison Before';

  @override
  String chatComparisonCurrentPrevious(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get chatCompletionBlocked => 'Chat Completion Blocked';

  @override
  String get chatCompletionDone => 'Chat Completion Done';

  @override
  String get chatCompletionNeedsInput => 'Chat Completion Needs Input';

  @override
  String get chatCompletionPartial => 'Chat Completion Partial';

  @override
  String get chatCompletionProcessing => 'Chat Completion Processing';

  @override
  String get chatConfidenceCautious => 'Chat Confidence Cautious';

  @override
  String get chatConfidenceHigh => 'Chat Confidence High';

  @override
  String chatConfidenceLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatConfidenceMedium => 'Chat Confidence Medium';

  @override
  String get chatConfirmationActionDefault =>
      'Chat Confirmation Action Default';

  @override
  String get chatConfirmationConfirmUpdate =>
      'Chat Confirmation Confirm Update';

  @override
  String get chatConfirmationTitleDefault => 'Chat Confirmation Title Default';

  @override
  String get chatConfirmationTitleUpdatePreference =>
      'Chat Confirmation Title Update Preference';

  @override
  String get chatConfirmationUpdatePreferenceGeneric =>
      'Chat Confirmation Update Preference Generic';

  @override
  String chatConfirmationUpdatePreferenceKeyOnly(Object arg0) {
    return '$arg0';
  }

  @override
  String chatConfirmationUpdatePreferenceWithValue(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get chatCopiedToClipboard => 'Chat Copied To Clipboard';

  @override
  String get chatDagExecutionAbortedDefault =>
      'Chat Dag Execution Aborted Default';

  @override
  String get chatDagExecutionCompleted => 'Chat Dag Execution Completed';

  @override
  String get chatDagExecutionEndAbortedDefault =>
      'Chat Dag Execution End Aborted Default';

  @override
  String chatDagLayerAborted(Object arg0) {
    return '$arg0';
  }

  @override
  String chatDagLayerCompleted(Object arg0) {
    return '$arg0';
  }

  @override
  String chatDagLayerStart(Object arg0, Object arg1, Object arg2) {
    return '$arg0 $arg1 $arg2';
  }

  @override
  String chatDagStepCompleted(Object arg0) {
    return '$arg0';
  }

  @override
  String chatDagStepCompletedWithDuration(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String chatDagStepFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatDagStepFallback => 'Chat Dag Step Fallback';

  @override
  String chatDurationLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String chatErrorWithSuggestion(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String chatEvolutionExpectedEffect(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatEvolutionHeadlineDefault => 'Chat Evolution Headline Default';

  @override
  String chatEvolutionNextWeekPlan(Object arg0) {
    return '$arg0';
  }

  @override
  String chatEvolutionWhy(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatExecutionCompleted => 'Chat Execution Completed';

  @override
  String get chatExecutionFailed => 'Chat Execution Failed';

  @override
  String get chatExecutionPartial => 'Chat Execution Partial';

  @override
  String get chatFeedbackThanks => 'Chat Feedback Thanks';

  @override
  String get chatFocusSprintDefaultTitle => 'Chat Focus Sprint Default Title';

  @override
  String get chatFocusStart => 'Chat Focus Start';

  @override
  String get chatInputDocumentClean => 'Chat Input Document Clean';

  @override
  String get chatInterventionViewPlan => 'Chat Intervention View Plan';

  @override
  String get chatInterventionViewSettings => 'Chat Intervention View Settings';

  @override
  String get chatKnowledgeCitationBody => 'Chat Knowledge Citation Body';

  @override
  String chatKnowledgeCitationTitle(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatModeCustomTeam => 'Chat Mode Custom Team';

  @override
  String get chatModeCustomTeamDesc => 'Chat Mode Custom Team Desc';

  @override
  String get chatModeKeepCurrent => 'Chat Mode Keep Current';

  @override
  String get chatModeSuggestionTitle => 'Chat Mode Suggestion Title';

  @override
  String get chatModeSwitch => 'Chat Mode Switch';

  @override
  String get chatModeSectionQuickChat => 'Quick Chat';

  @override
  String get chatModeSectionDeepWork => 'Deep Workflows';

  @override
  String get chatModeSectionExpertAccess => 'Expert Access';

  @override
  String chatModeTransitionToWorkflow(Object mode) {
    return 'Switched to $mode — multi-expert collaboration active';
  }

  @override
  String get chatModeTransitionToDirect => 'Returned to standard chat';

  @override
  String chatModeTransitionSwitched(Object mode) {
    return 'Switched to $mode';
  }

  @override
  String get capabilityCeilingTitle => 'Capability Limit';

  @override
  String get capabilityCeilingDefault =>
      'The current mode may not fully resolve this';

  @override
  String get capabilityCeilingAlternatives => 'Try a more capable mode:';

  @override
  String get capabilityCeilingContinue => 'Continue anyway';

  @override
  String get guidanceModeAi => 'AI Guide';

  @override
  String get guidanceModeSelf => 'Self Explore';

  @override
  String get chatMultiAgentCollab => 'Chat Multi Agent Collab';

  @override
  String chatNextActionLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatNextActionsRetryHint => 'Chat Next Actions Retry Hint';

  @override
  String get chatNextActionsTitle => 'Chat Next Actions Title';

  @override
  String get chatNightlyReviewTodos => 'Chat Nightly Review Todos';

  @override
  String get chatNotificationGroupMessage => 'Chat Notification Group Message';

  @override
  String get chatNotificationMention => 'Chat Notification Mention';

  @override
  String get chatOptionalNotesHint => 'Chat Optional Notes Hint';

  @override
  String get chatOrchestrationTraceStep => 'Chat Orchestration Trace Step';

  @override
  String get chatOrchestrationTraceTitle => 'Chat Orchestration Trace Title';

  @override
  String chatPendingMessagesFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatPlanContextClear => 'Chat Plan Context Clear';

  @override
  String get chatPlanContextSelect => 'Chat Plan Context Select';

  @override
  String get chatPlanEmptySubtitle => 'Chat Plan Empty Subtitle';

  @override
  String get chatPlanEmptyTitle => 'Chat Plan Empty Title';

  @override
  String get chatPlanReviewAcknowledged => 'Chat Plan Review Acknowledged';

  @override
  String get chatPlanReviewApproved => 'Chat Plan Review Approved';

  @override
  String get chatPlanReviewModifyRequested =>
      'Chat Plan Review Modify Requested';

  @override
  String get chatPlanReviewRejected => 'Chat Plan Review Rejected';

  @override
  String chatPlanReviewStatusUpdate(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatPlanSelect => 'Chat Plan Select';

  @override
  String chatQuotePrefix(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatReasoningProcess => 'Chat Reasoning Process';

  @override
  String get chatReasoningStatusAnalyzing => 'Chat Reasoning Status Analyzing';

  @override
  String get chatReasoningStatusAudioProcessing =>
      'Chat Reasoning Status Audio Processing';

  @override
  String get chatReasoningStatusCalculating =>
      'Chat Reasoning Status Calculating';

  @override
  String get chatReasoningStatusCoding => 'Chat Reasoning Status Coding';

  @override
  String get chatReasoningStatusDataAnalyzing =>
      'Chat Reasoning Status Data Analyzing';

  @override
  String get chatReasoningStatusDone => 'Chat Reasoning Status Done';

  @override
  String get chatReasoningStatusImageProcessing =>
      'Chat Reasoning Status Image Processing';

  @override
  String get chatReasoningStatusPlanning => 'Chat Reasoning Status Planning';

  @override
  String get chatReasoningStatusPreparing => 'Chat Reasoning Status Preparing';

  @override
  String get chatReasoningStatusReasoning => 'Chat Reasoning Status Reasoning';

  @override
  String get chatReasoningStatusRetrieving =>
      'Chat Reasoning Status Retrieving';

  @override
  String get chatReasoningStatusSearching => 'Chat Reasoning Status Searching';

  @override
  String get chatReasoningStatusTranslating =>
      'Chat Reasoning Status Translating';

  @override
  String get chatReasoningStatusWriting => 'Chat Reasoning Status Writing';

  @override
  String chatReasoningStepsCount(Object arg0) {
    return '$arg0';
  }

  @override
  String chatReasoningSummary(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get chatReflectionDegraded => 'Chat Reflection Degraded';

  @override
  String get chatReflectionFailed => 'Chat Reflection Failed';

  @override
  String chatReflectionFixed(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String chatReflectionImproved(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get chatReflectionNoChange => 'Chat Reflection No Change';

  @override
  String chatReflectionStatusUpdate(Object arg0) {
    return '$arg0';
  }

  @override
  String chatRoundsInfo(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatSourceUnknown => 'Chat Source Unknown';

  @override
  String get chatSourceUntitled => 'Chat Source Untitled';

  @override
  String get chatSourcesAvailable => 'Chat Sources Available';

  @override
  String get chatSourcesUnavailable => 'Chat Sources Unavailable';

  @override
  String chatStreakSummary(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get chatSubmitFeedback => 'Chat Submit Feedback';

  @override
  String get chatSynthesisSuggestions => 'Chat Synthesis Suggestions';

  @override
  String chatTaskDataInvalid(Object arg0) {
    return '$arg0';
  }

  @override
  String chatTaskListMoreCount(Object arg0) {
    return '$arg0';
  }

  @override
  String chatTeamExpertsCount(Object arg0) {
    return '$arg0';
  }

  @override
  String chatUnknownWidgetType(Object arg0) {
    return '$arg0';
  }

  @override
  String chatUsingTool(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatViewComparisonData => 'Chat View Comparison Data';

  @override
  String get chatViewPlanRationale => 'Chat View Plan Rationale';

  @override
  String get chatVoiceNoMicPermission => 'Chat Voice No Mic Permission';

  @override
  String chatVoiceStartFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatWhyThisAnswer => 'Chat Why This Answer';

  @override
  String get chatWorkflowDebateProcessing => 'Chat Workflow Debate Processing';

  @override
  String get chatWorkflowDebateSubtitle => 'Chat Workflow Debate Subtitle';

  @override
  String get chatWorkflowDebateTitle => 'Chat Workflow Debate Title';

  @override
  String get chatWorkflowDefault => 'Chat Workflow Default';

  @override
  String get chatWorkflowDelegationSubtitle =>
      'Chat Workflow Delegation Subtitle';

  @override
  String get chatWorkflowDelegationTitle => 'Chat Workflow Delegation Title';

  @override
  String get chatWorkflowErrorDiagnosis => 'Chat Workflow Error Diagnosis';

  @override
  String get chatWorkflowExpertRouting => 'Chat Workflow Expert Routing';

  @override
  String chatWorkflowExpertsCount(Object arg0) {
    return '$arg0';
  }

  @override
  String chatWorkflowParallelCount(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatWorkflowParallelSubtitle => 'Chat Workflow Parallel Subtitle';

  @override
  String chatWorkflowPhaseLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String get chatWorkflowProgressiveExploration =>
      'Chat Workflow Progressive Exploration';

  @override
  String get chatWorkflowStatusActive => 'Chat Workflow Status Active';

  @override
  String get chatWorkflowStatusDone => 'Chat Workflow Status Done';

  @override
  String get chatWorkflowStatusError => 'Chat Workflow Status Error';

  @override
  String get chatWorkflowStatusWaiting => 'Chat Workflow Status Waiting';

  @override
  String get chatWorkflowTaskDecomposition =>
      'Chat Workflow Task Decomposition';

  @override
  String get commonMinutesShort => 'Common Minutes Short';

  @override
  String get commonUnknown => 'Common Unknown';

  @override
  String get communityAgentCollabOff => 'Community Agent Collab Off';

  @override
  String get communityAgentCollabOn => 'Community Agent Collab On';

  @override
  String get communityAgentName => 'Sparkle AI';

  @override
  String get communityAgentOnlyYou => 'Community Agent Only You';

  @override
  String get communityAgentProcessing => 'Community Agent Processing';

  @override
  String get communityAgentPromptHint => 'Community Agent Prompt Hint';

  @override
  String get communityAgentQuickConsensus => 'Community Agent Quick Consensus';

  @override
  String get communityAgentQuickConsensusPrompt =>
      'Community Agent Quick Consensus Prompt';

  @override
  String get communityAgentQuickReminder => 'Community Agent Quick Reminder';

  @override
  String get communityAgentQuickReminderPrompt =>
      'Community Agent Quick Reminder Prompt';

  @override
  String get communityAgentQuickSummary => 'Community Agent Quick Summary';

  @override
  String get communityAgentQuickSummaryPrompt =>
      'Community Agent Quick Summary Prompt';

  @override
  String get communityAgentThinking => 'Community Agent Thinking';

  @override
  String get communityChatEmpty => 'Community Chat Empty';

  @override
  String get communityChatTitle => 'Community Chat Title';

  @override
  String get communityCheckInAction => 'Community Check In Action';

  @override
  String get communityCheckInDurationLabel =>
      'Community Check In Duration Label';

  @override
  String communityCheckInFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get communityCheckInMessageHint => 'Community Check In Message Hint';

  @override
  String get communityCheckInMessageLabel => 'Community Check In Message Label';

  @override
  String get communityCheckInSuccess => 'Community Check In Success';

  @override
  String get communityCheckInTitle => 'Community Check In Title';

  @override
  String communityFileSharedFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get communityFileSharedSuccess => 'Community File Shared Success';

  @override
  String get communityGroupFiles => 'Community Group Files';

  @override
  String communityGroupMembersCount(Object arg0) {
    return '$arg0';
  }

  @override
  String get communityMessageFallback => 'Community Message Fallback';

  @override
  String get communityMessageInputHint => 'Community Message Input Hint';

  @override
  String get communitySearchGroupMessages => 'Community Search Group Messages';

  @override
  String get deleteAccountChecklistItem1 =>
      'All your personal data will be permanently deleted.';

  @override
  String get deleteAccountChecklistItem2 =>
      'You will not be able to recover your account.';

  @override
  String get deleteAccountChecklistItem3 =>
      'Active subscriptions will be automatically canceled.';

  @override
  String get deleteAccountChecklistTitle =>
      'Please read carefully before proceeding:';

  @override
  String get deleteAccountConfirmButton => 'Delete Account';

  @override
  String get deleteAccountConfirmInputHint => 'Type \"DELETE\" to confirm';

  @override
  String get deleteAccountConfirmInputTitle => 'Confirm Deletion';

  @override
  String get deleteAccountNoSocialProvider =>
      'No associated social account found';

  @override
  String get deleteAccountPasswordHint => 'Enter your password';

  @override
  String get deleteAccountPasswordLabel => 'Password';

  @override
  String get deleteAccountReauthButton => 'Authenticate';

  @override
  String get deleteAccountReauthDone => 'Authenticated';

  @override
  String get deleteAccountReauthSuccess => 'Authentication successful';

  @override
  String get deleteAccountRequireDeleteInput => 'Please type DELETE to confirm';

  @override
  String get deleteAccountRequirePassword => 'Password is required';

  @override
  String get deleteAccountRequireReauth => 'Authentication required';

  @override
  String get deleteAccountSocialProvider => 'Social Account';

  @override
  String deleteAccountSocialReauthNotice(Object arg0) {
    return 'Please authenticate with $arg0';
  }

  @override
  String get deleteAccountSuccess => 'Account deleted successfully';

  @override
  String get deleteAccountTitle => 'Delete Account';

  @override
  String get deleteAccountWeChatUnavailable =>
      'WeChat is currently unavailable';

  @override
  String get editProfileEmailUnverified => 'Unverified';

  @override
  String get editProfileEmailUnverifiedDesc =>
      'Please verify your email address';

  @override
  String get editProfileEmailVerified => 'Verified';

  @override
  String get editProfileEmailVerifiedDesc => 'Your email is verified';

  @override
  String get editProfileEnterCode => 'Enter Code';

  @override
  String get editProfileRegistrationMethod => 'Registration Method';

  @override
  String get editProfileSendEmail => 'Send Verification Email';

  @override
  String get editProfileSetPassword => 'Set Password';

  @override
  String get editProfileSetPasswordHint =>
      'Set a secure password for your account';

  @override
  String get editProfileVerifyEmailConfirm => 'Confirm';

  @override
  String get editProfileVerifyEmailHint => 'Enter the verification code';

  @override
  String get editProfileVerifyEmailTitle => 'Verify Email';

  @override
  String get fileStatusFailed => 'File Status Failed';

  @override
  String get fileStatusProcessing => 'File Status Processing';

  @override
  String get fileStatusReady => 'File Status Ready';

  @override
  String get fileStatusUploaded => 'File Status Uploaded';

  @override
  String get galaxyA11yActionStartLearning =>
      'Galaxy A11y Action Start Learning';

  @override
  String get galaxyA11yActionUnlockNode => 'Galaxy A11y Action Unlock Node';

  @override
  String galaxyA11yClusterLabel(Object arg0, Object arg1, Object arg2) {
    return '$arg0 $arg1 $arg2';
  }

  @override
  String get galaxyA11yHintStartLearning => 'Galaxy A11y Hint Start Learning';

  @override
  String get galaxyA11yHintUnlockNode => 'Galaxy A11y Hint Unlock Node';

  @override
  String galaxyA11yNavigateTo(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyA11yNavigationHint => 'Galaxy A11y Navigation Hint';

  @override
  String galaxyA11yNodeImportance(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyA11yNodeLocked => 'Galaxy A11y Node Locked';

  @override
  String galaxyA11yNodeMastery(Object arg0) {
    return '$arg0';
  }

  @override
  String galaxyA11yNodePrefix(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String galaxyA11yNodeStudyCount(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyA11yNodeUnlocked => 'Galaxy A11y Node Unlocked';

  @override
  String galaxyA11ySectorLabel(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String galaxyA11yZoomLevel(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyControlOverview => 'Galaxy Control Overview';

  @override
  String get galaxyControlReplayStart => 'Galaxy Control Replay Start';

  @override
  String get galaxyControlReplayStop => 'Galaxy Control Replay Stop';

  @override
  String get galaxyControlSearchClose => 'Galaxy Control Search Close';

  @override
  String get galaxyControlSearchOpen => 'Galaxy Control Search Open';

  @override
  String get galaxyControlSettings => 'Galaxy Control Settings';

  @override
  String get galaxyControlZoomIn => 'Galaxy Control Zoom In';

  @override
  String get galaxyControlZoomOut => 'Galaxy Control Zoom Out';

  @override
  String get galaxyEmptyMessage =>
      'Unlock a few knowledge nodes or reload the map to let the constellation begin to grow.';

  @override
  String get galaxyEmptyTitle => 'Your galaxy is still waiting to be charted';

  @override
  String get galaxyErrorConnectionFailed => 'Galaxy Error Connection Failed';

  @override
  String get galaxyErrorConnectionTimeout => 'Galaxy Error Connection Timeout';

  @override
  String get galaxyErrorLoadFailed => 'Galaxy Error Load Failed';

  @override
  String get galaxyErrorNetwork => 'Galaxy Error Network';

  @override
  String get galaxyErrorNetworkFailed => 'Galaxy Error Network Failed';

  @override
  String get galaxyErrorRequestFailed => 'Galaxy Error Request Failed';

  @override
  String get galaxyErrorResponseTimeout => 'Galaxy Error Response Timeout';

  @override
  String get galaxyErrorRetryHint => 'Galaxy Error Retry Hint';

  @override
  String get galaxyErrorServiceTemporarilyUnavailable =>
      'Galaxy Error Service Temporarily Unavailable';

  @override
  String get galaxyErrorServiceUnavailable =>
      'Galaxy Error Service Unavailable';

  @override
  String get galaxyErrorUnknown => 'Galaxy Error Unknown';

  @override
  String get galaxyGraphRagGraph => 'Galaxy Graph Rag Graph';

  @override
  String get galaxyGraphRagSearching => 'Galaxy Graph Rag Searching';

  @override
  String get galaxyGraphRagTime => 'Galaxy Graph Rag Time';

  @override
  String get galaxyGraphRagVector => 'Galaxy Graph Rag Vector';

  @override
  String get galaxyImportanceAdvanced => 'Galaxy Importance Advanced';

  @override
  String get galaxyImportanceBasic => 'Galaxy Importance Basic';

  @override
  String get galaxyImportanceCore => 'Galaxy Importance Core';

  @override
  String get galaxyImportanceEntry => 'Galaxy Importance Entry';

  @override
  String get galaxyImportanceIntermediate => 'Galaxy Importance Intermediate';

  @override
  String get galaxyImportanceNormal => 'Galaxy Importance Normal';

  @override
  String galaxyLLMActionFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyLoadFailed => 'Galaxy Load Failed';

  @override
  String get galaxyLoadFailedTitle => 'Galaxy failed to load';

  @override
  String get galaxyLoadingMessage =>
      'Mapping your current knowledge constellation...';

  @override
  String get galaxyLoadingTitle => 'Loading galaxy';

  @override
  String get galaxyNodeFocus => 'Focus node';

  @override
  String get galaxyNodeInspectConnections => 'View links';

  @override
  String get galaxyNodeLaunchPrediction => 'Run simulation';

  @override
  String get galaxyNodeLocked => 'Locked';

  @override
  String get galaxyNodeLockedHint =>
      'Open the detail view to inspect prerequisites and plan how to unlock this node.';

  @override
  String galaxyNodePreviewSubtitle(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get galaxyNodeUnlocked => 'Unlocked';

  @override
  String get galaxyOfflineMode => 'Galaxy Offline Mode';

  @override
  String get galaxyOverviewMastery => 'Galaxy Overview Mastery';

  @override
  String get galaxyOverviewNodes => 'Galaxy Overview Nodes';

  @override
  String get galaxyOverviewUnlocked => 'Galaxy Overview Unlocked';

  @override
  String galaxyPerfHighJank(Object arg0) {
    return '$arg0';
  }

  @override
  String galaxyPerfLowFpsCritical(Object arg0) {
    return '$arg0';
  }

  @override
  String galaxyPerfLowFpsWarning(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyPerfRecommendationDisableParticles =>
      'Galaxy Perf Recommendation Disable Particles';

  @override
  String get galaxyPerfRecommendationLowQualityMode =>
      'Galaxy Perf Recommendation Low Quality Mode';

  @override
  String get galaxyPerfRecommendationOptimizeLayout =>
      'Galaxy Perf Recommendation Optimize Layout';

  @override
  String get galaxyPerfRecommendationReduceNodes =>
      'Galaxy Perf Recommendation Reduce Nodes';

  @override
  String galaxyPerfSlowRender(Object arg0) {
    return '$arg0';
  }

  @override
  String get galaxyPerfStatusCritical => 'Galaxy Perf Status Critical';

  @override
  String get galaxyPerfStatusDegraded => 'Galaxy Perf Status Degraded';

  @override
  String get galaxyPerfStatusOptimal => 'Galaxy Perf Status Optimal';

  @override
  String get galaxyReload => 'Reload galaxy';

  @override
  String get galaxySearchHint => 'Galaxy Search Hint';

  @override
  String get galaxySearchHintDetail => 'Galaxy Search Hint Detail';

  @override
  String get galaxySearchNoResults => 'Galaxy Search No Results';

  @override
  String galaxySearchResultSubtitle(Object arg0, Object arg1, Object arg2) {
    return '$arg0 $arg1 $arg2';
  }

  @override
  String get galaxySearchTitle => 'Galaxy Search Title';

  @override
  String get galaxySectorArt => 'Galaxy Sector Art';

  @override
  String get galaxySectorCivilization => 'Galaxy Sector Civilization';

  @override
  String get galaxySectorCosmos => 'Galaxy Sector Cosmos';

  @override
  String get galaxySectorLife => 'Galaxy Sector Life';

  @override
  String get galaxySectorTech => 'Galaxy Sector Tech';

  @override
  String get galaxySectorVoid => 'Galaxy Sector Void';

  @override
  String get galaxySectorWisdom => 'Galaxy Sector Wisdom';

  @override
  String get galaxySimulationCenterGravity =>
      'Galaxy Simulation Center Gravity';

  @override
  String get galaxySimulationGravity => 'Galaxy Simulation Gravity';

  @override
  String get galaxySimulationReplaySpeed => 'Galaxy Simulation Replay Speed';

  @override
  String get galaxySimulationRepulsion => 'Galaxy Simulation Repulsion';

  @override
  String get galaxySimulationReset => 'Galaxy Simulation Reset';

  @override
  String get galaxySimulationSubtitle => 'Galaxy Simulation Subtitle';

  @override
  String get galaxySimulationTitle => 'Galaxy Simulation Title';

  @override
  String get galaxyUsingCache => 'Galaxy Using Cache';

  @override
  String get guestUpgradeAcceptPoliciesRequired =>
      'Please read and agree to the policies';

  @override
  String get guestUpgradeAgreePrivacy => 'I agree to the Privacy Policy';

  @override
  String get guestUpgradeAgreeTerms => 'I agree to the Terms of Service';

  @override
  String get guestUpgradeIntro =>
      'Upgrade your guest account to securely save your progress and sync across devices.';

  @override
  String get guestUpgradePasswordMinLength =>
      'Password must be at least 8 characters';

  @override
  String get guestUpgradeSocialSectionTitle => 'Or continue with';

  @override
  String get guestUpgradeSocialSuccess => 'Account upgraded successfully';

  @override
  String get guestUpgradeSuccess => 'Account upgraded successfully';

  @override
  String get guestUpgradeTitle => 'Upgrade Account';

  @override
  String get guestUpgradeUsernameMinLength =>
      'Username must be at least 3 characters';

  @override
  String get guestUpgradeViewPrivacy => 'View Privacy Policy';

  @override
  String get guestUpgradeViewTerms => 'View Terms of Service';

  @override
  String get guestUpgradeWithApple => 'Continue with Apple';

  @override
  String get guestUpgradeWithEmail => 'Upgrade with Email';

  @override
  String get guestUpgradeWithGoogle => 'Continue with Google';

  @override
  String get guestUpgradeWithWeChat => 'Continue with WeChat';

  @override
  String get passwordSetConfirm => 'Password Set Confirm';

  @override
  String get passwordSetHint => 'Password Set Hint';

  @override
  String get passwordSetLabel => 'Password Set Label';

  @override
  String get passwordSetSuccess => 'Password Set Success';

  @override
  String get passwordSetTitle => 'Password Set Title';

  @override
  String get planArchive => 'Plan Archive';

  @override
  String get planArchiveConfirm => 'Plan Archive Confirm';

  @override
  String get planArchiveMessage => 'Plan Archive Message';

  @override
  String get planArchiveTitle => 'Plan Archive Title';

  @override
  String get planArchivedSuccess => 'Plan Archived Success';

  @override
  String get planContextTitle => 'Plan Context Title';

  @override
  String planDaysRemaining(Object arg0) {
    return '$arg0';
  }

  @override
  String get planDetailTitle => 'Plan Detail Title';

  @override
  String get planDetailAddExistingTask => 'Add Existing';

  @override
  String get planDetailAddNewTask => 'Add New Task';

  @override
  String get planDetailAddPhase => 'Add Phase';

  @override
  String get planDetailAiGuide => 'AI Execution Guide';

  @override
  String planDetailCompressionDesc(int taskCount, int totalMinutes) {
    return 'Only $taskCount tasks / $totalMinutes min kept today. Focus on getting the main thread back on track.';
  }

  @override
  String get planDetailCompressionTitle => 'Today\'s plan has been streamlined';

  @override
  String get planDetailCommonMistakes => '⚠️ Common Mistakes';

  @override
  String get planDetailDailyRhythm => 'Daily Rhythm';

  @override
  String planDetailDayGroupSubtitle(int count, int minutes) {
    return '$count items · $minutes min';
  }

  @override
  String get planDetailDefaultRecommendation =>
      'No new content today. Just review high-frequency topics, revisit past mistakes, and do a 30-min mini simulation.';

  @override
  String get planDetailEdit => 'Edit Plan';

  @override
  String get planDetailFullPlan => 'Full Plan';

  @override
  String get planDetailHealthNeedAttention => 'Needs Attention';

  @override
  String get planDetailHealthNeedReplan => 'Needs Replanning';

  @override
  String get planDetailHealthReasonDefault => 'No specific risk identified';

  @override
  String get planDetailHealthReasonProgressLag =>
      'Progress is behind schedule. Prioritize high-yield tasks.';

  @override
  String get planDetailHealthReasonTimeOverrun =>
      'Recent tasks have taken longer than expected. Consider compressing the next steps.';

  @override
  String get planDetailHealthReasonTooEasy =>
      'Recent feedback suggests it\'s too easy. Consider increasing the challenge level.';

  @override
  String get planDetailHealthReasonTooHard =>
      'Recent feedback suggests it\'s too hard. Try breaking it down or covering a prerequisite.';

  @override
  String planDetailHealthScore(int score, String label) {
    return 'Plan Health $score% · $label';
  }

  @override
  String get planDetailHealthStable => 'Stable';

  @override
  String planDetailLearningPathLoadError(String error) {
    return 'Learning path progress failed to load: $error';
  }

  @override
  String get planDetailLoadError => 'Plan Load Failed';

  @override
  String get planDetailLoadError404 =>
      'Plan just finished generating, details may still be syncing. Tap \"Retry\" to continue loading.';

  @override
  String get planDetailLoadErrorEmpty =>
      'Plan details couldn\'t load. Please try again.';

  @override
  String planDetailLoadErrorGeneric(String error) {
    return 'Plan details couldn\'t load: $error';
  }

  @override
  String get planDetailLoadErrorTimeout =>
      'Plan loading timed out. Please check your network and try again.';

  @override
  String planDetailMinutes(int minutes) {
    return '$minutes min';
  }

  @override
  String get planDetailNoPhasesYet =>
      'No phases yet. Create the first phase to break your long-term plan into actionable segments.';

  @override
  String planDetailPhasesLoadError(String error) {
    return 'Phase loading failed: $error';
  }

  @override
  String get planDetailPhasesTitle => 'Plan Phases';

  @override
  String get planDetailPlanScope => 'Plan Scope';

  @override
  String planDetailRecommendationDay1(String thingLabel) {
    return 'Focus on $thingLabel today. You\'re already on the right track.';
  }

  @override
  String planDetailRecommendationDayN(int day, String thingLabel) {
    return 'Start with Day $day\'s $thingLabel to keep your rhythm steady.';
  }

  @override
  String get planDetailSprintMode7Day => '7-Day Sprint Mode';

  @override
  String get planDetailSprintModeExam => 'Exam Sprint Mode';

  @override
  String get planDetailSprintModeLabel => 'Pre-Exam Sprint Mode';

  @override
  String get planDetailSprintNodesLoading =>
      'Sprint nodes are still being organized.';

  @override
  String get planDetailSprintPackDesc =>
      'Secure these high-yield nodes first today. Completed tasks will light up the dots.';

  @override
  String get planDetailSprintPackNodes => 'Sprint Pack Nodes';

  @override
  String get planDetailStatusAbandoned => 'Abandoned';

  @override
  String get planDetailStatusCompleted => 'Completed';

  @override
  String get planDetailStatusInProgress => 'In Progress';

  @override
  String get planDetailStatusPending => 'Pending';

  @override
  String get planDetailStatusStuck => 'Stuck';

  @override
  String get planDetailTaskBlueprint => 'Task Blueprint';

  @override
  String planDetailTaskCount(int completed, int total) {
    return '$completed/$total tasks';
  }

  @override
  String planDetailTaskDifficulty(String difficulty) {
    return 'Difficulty $difficulty';
  }

  @override
  String get planDetailTagErrorRepair => 'Error Repair';

  @override
  String get planDetailTagNoNewContent => 'No New Content';

  @override
  String get planDetailThingCount1 => 'this 1 task';

  @override
  String planDetailThingCountN(int count) {
    return 'these $count tasks';
  }

  @override
  String get planDetailTodayFocus => 'Today\'s Focus';

  @override
  String get planDetailSprintFocus => 'Sprint Focus';

  @override
  String get planDetailWhyNowErrorFix =>
      'Fix this error now to prevent later tasks from being held back by the same gap.';

  @override
  String get planDetailWhyNowLearning =>
      'Handle this now to turn today\'s learning progress into a tangible output.';

  @override
  String get planDetailWhyNowOcr =>
      'Process materials now to turn available info into an entry point for upcoming tasks.';

  @override
  String get planDetailWhyNowPlanning =>
      'Organize the plan now to reduce hesitation in the next steps.';

  @override
  String get planDetailWhyNowReflection =>
      'Review now to turn today\'s results into easier choices for tomorrow.';

  @override
  String get planDetailWhyNowSocial =>
      'Complete this collaboration now to keep external feedback in sync with your learning pace.';

  @override
  String get planDetailWhyNowTraining =>
      'Practice now to quickly confirm you can apply what you just learned.';

  @override
  String get planDueToday => 'Plan Due Today';

  @override
  String planFactsFeedbackSummary(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get planKeyFacts => 'Plan Key Facts';

  @override
  String planLoadFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get planNoContent => 'Plan No Content';

  @override
  String get planNoTasks => 'Plan No Tasks';

  @override
  String get planNoVisualizationData => 'Plan No Visualization Data';

  @override
  String planOverdueDays(Object arg0) {
    return '$arg0';
  }

  @override
  String get planProgressLabel => 'Plan Progress Label';

  @override
  String get planRecentFeedback => 'Plan Recent Feedback';

  @override
  String get planRelatedTasks => 'Plan Related Tasks';

  @override
  String get planRestore => 'Plan Restore';

  @override
  String get planRestoredSuccess => 'Plan Restored Success';

  @override
  String get planReviewAdditionalNotesHint =>
      'Plan Review Additional Notes Hint';

  @override
  String get planReviewAdditionalNotesRequired =>
      'Plan Review Additional Notes Required';

  @override
  String get planReviewApproveExecute => 'Plan Review Approve Execute';

  @override
  String planReviewConfidenceTierLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String get planReviewConfidenceTitle => 'Plan Review Confidence Title';

  @override
  String get planReviewDecisionApproved => 'Plan Review Decision Approved';

  @override
  String get planReviewDecisionNeedsModification =>
      'Plan Review Decision Needs Modification';

  @override
  String get planReviewDecisionRejected => 'Plan Review Decision Rejected';

  @override
  String get planReviewDecisionRequiresConfirmation =>
      'Plan Review Decision Requires Confirmation';

  @override
  String planReviewEvidenceLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String planReviewImpactLabel(Object arg0) {
    return '$arg0';
  }

  @override
  String get planReviewModifyPlan => 'Plan Review Modify Plan';

  @override
  String get planReviewReasonDifficultyTooHigh =>
      'Plan Review Reason Difficulty Too High';

  @override
  String get planReviewReasonDifficultyTooLow =>
      'Plan Review Reason Difficulty Too Low';

  @override
  String get planReviewReasonMissingKeyTask =>
      'Plan Review Reason Missing Key Task';

  @override
  String get planReviewReasonOther => 'Plan Review Reason Other';

  @override
  String get planReviewReasonScheduleUnreasonable =>
      'Plan Review Reason Schedule Unreasonable';

  @override
  String get planReviewReasonTasksTooFew => 'Plan Review Reason Tasks Too Few';

  @override
  String get planReviewReasonTasksTooMany =>
      'Plan Review Reason Tasks Too Many';

  @override
  String get planReviewRejectReasonTitle => 'Plan Review Reject Reason Title';

  @override
  String get planReviewRejectWithFeedback => 'Plan Review Reject With Feedback';

  @override
  String get planReviewSelectReasonRequired =>
      'Plan Review Select Reason Required';

  @override
  String get planReviewSubmitFeedback => 'Plan Review Submit Feedback';

  @override
  String get planReviewSummaryApproved => 'Plan Review Summary Approved';

  @override
  String get planReviewSummaryNeedsModification =>
      'Plan Review Summary Needs Modification';

  @override
  String get planReviewSummaryRejected => 'Plan Review Summary Rejected';

  @override
  String get planReviewSummaryRequiresConfirmation =>
      'Plan Review Summary Requires Confirmation';

  @override
  String get planSectionCompletionRate => 'Plan Section Completion Rate';

  @override
  String get planSectionDailyCompletion => 'Plan Section Daily Completion';

  @override
  String get planSectionTaskTypeDistribution =>
      'Plan Section Task Type Distribution';

  @override
  String get planShare => 'Plan Share';

  @override
  String get planStatusActive => 'Plan Status Active';

  @override
  String get planStatusArchived => 'Plan Status Archived';

  @override
  String get planStatusCompleted => 'Plan Status Completed';

  @override
  String get planStatusPaused => 'Plan Status Paused';

  @override
  String get planStatusUnknown => 'Plan Status Unknown';

  @override
  String get planTabOverview => 'Plan Tab Overview';

  @override
  String get planTabProgress => 'Plan Tab Progress';

  @override
  String planTargetDate(Object arg0) {
    return '$arg0';
  }

  @override
  String planTargetMastery(Object arg0) {
    return '$arg0';
  }

  @override
  String get planTaskProgress => 'Plan Task Progress';

  @override
  String get planUpcomingTasks => 'Plan Upcoming Tasks';

  @override
  String get pomodoroBreakFinished => 'Pomodoro Break Finished';

  @override
  String get pomodoroWorkFinished => 'Pomodoro Work Finished';

  @override
  String get account => 'Account';

  @override
  String get accountSecurity => 'Account & Security';

  @override
  String get accountSecurityIntro =>
      'Manage linked accounts, login devices and security logs';

  @override
  String get personalGrowth => 'Personal Growth';

  @override
  String get profileDeleteAccount => 'Delete Account';

  @override
  String get profileLinkedAccounts => 'Linked Accounts';

  @override
  String get profilePersonalInfo => 'Personal Info';

  @override
  String get profileSecurityLog => 'Security Log';

  @override
  String get profileSessionManagement => 'Session Management';

  @override
  String get profileUpgradeGuest => 'Upgrade Account';

  @override
  String get regenCustomHint => 'Regen Custom Hint';

  @override
  String get regenDescCompleted => 'Regen Desc Completed';

  @override
  String get regenDescFailed => 'Regen Desc Failed';

  @override
  String get regenDescInProgress => 'Regen Desc In Progress';

  @override
  String get regenDescPending => 'Regen Desc Pending';

  @override
  String get regenHintAddExamples => 'Regen Hint Add Examples';

  @override
  String get regenHintFixErrors => 'Regen Hint Fix Errors';

  @override
  String get regenHintFriendlierTone => 'Regen Hint Friendlier Tone';

  @override
  String get regenHintMoreAccurate => 'Regen Hint More Accurate';

  @override
  String get regenHintMoreConcise => 'Regen Hint More Concise';

  @override
  String get regenHintMoreDetailed => 'Regen Hint More Detailed';

  @override
  String get regenHintsOptional => 'Regen Hints Optional';

  @override
  String get regenImprovementsTitle => 'Regen Improvements Title';

  @override
  String get regenProgressTitle => 'Regen Progress Title';

  @override
  String regenQualityImprovement(Object arg0) {
    return '$arg0';
  }

  @override
  String get regenResultFailed => 'Regen Result Failed';

  @override
  String get regenResultSuccess => 'Regen Result Success';

  @override
  String get regenRetryMessage => 'Regen Retry Message';

  @override
  String get regenSelectType => 'Regen Select Type';

  @override
  String get regenStart => 'Regen Start';

  @override
  String get regenTitleCompleted => 'Regen Title Completed';

  @override
  String get regenTitleFailed => 'Regen Title Failed';

  @override
  String get regenTitleIdle => 'Regen Title Idle';

  @override
  String get regenTitleInProgress => 'Regen Title In Progress';

  @override
  String get regenTitlePending => 'Regen Title Pending';

  @override
  String get regenTypeAddDetails => 'Regen Type Add Details';

  @override
  String get regenTypeChangeStyle => 'Regen Type Change Style';

  @override
  String get regenTypeCustom => 'Regen Type Custom';

  @override
  String get regenTypeFixIssues => 'Regen Type Fix Issues';

  @override
  String get regenTypeImproveQuality => 'Regen Type Improve Quality';

  @override
  String get regenTypeSimplify => 'Regen Type Simplify';

  @override
  String get reviewRatingAccuracyTitle => 'Review Rating Accuracy Title';

  @override
  String get reviewRatingAccurate => 'Review Rating Accurate';

  @override
  String get reviewRatingAddInaccuratePoint =>
      'Review Rating Add Inaccurate Point';

  @override
  String get reviewRatingCommentsHint => 'Review Rating Comments Hint';

  @override
  String get reviewRatingCommentsTitle => 'Review Rating Comments Title';

  @override
  String get reviewRatingHelpful => 'Review Rating Helpful';

  @override
  String get reviewRatingInaccurate => 'Review Rating Inaccurate';

  @override
  String get reviewRatingInaccuratePointHint =>
      'Review Rating Inaccurate Point Hint';

  @override
  String get reviewRatingInaccuratePointsTitle =>
      'Review Rating Inaccurate Points Title';

  @override
  String get reviewRatingLessOptions => 'Review Rating Less Options';

  @override
  String get reviewRatingMoreOptions => 'Review Rating More Options';

  @override
  String get reviewRatingNotHelpful => 'Review Rating Not Helpful';

  @override
  String get reviewRatingSpecificityTitle => 'Review Rating Specificity Title';

  @override
  String get reviewRatingSubmit => 'Review Rating Submit';

  @override
  String get reviewRatingSubmitFailed => 'Review Rating Submit Failed';

  @override
  String get reviewRatingSubmitSuccess => 'Review Rating Submit Success';

  @override
  String get reviewRatingSubtitle => 'Review Rating Subtitle';

  @override
  String get reviewRatingTagsTitle => 'Review Rating Tags Title';

  @override
  String get reviewRatingTitle => 'Review Rating Title';

  @override
  String get reviewSpecificityAppropriate => 'Review Specificity Appropriate';

  @override
  String get reviewSpecificityTooDetailed => 'Review Specificity Too Detailed';

  @override
  String get reviewSpecificityTooVague => 'Review Specificity Too Vague';

  @override
  String get reviewTagAccurate => 'Review Tag Accurate';

  @override
  String get reviewTagClear => 'Review Tag Clear';

  @override
  String get reviewTagNeedsImprovement => 'Review Tag Needs Improvement';

  @override
  String get reviewTagPractical => 'Review Tag Practical';

  @override
  String get reviewTagTooLenient => 'Review Tag Too Lenient';

  @override
  String get reviewTagTooStrict => 'Review Tag Too Strict';

  @override
  String get securityLogActionAccountDelete => 'Account Deleted';

  @override
  String get securityLogActionEmailVerify => 'Email Verified';

  @override
  String get securityLogActionGuestUpgrade => 'Guest Upgraded';

  @override
  String get securityLogActionLoginFailed => 'Login Failed';

  @override
  String get securityLogActionLoginSuccess => 'Login';

  @override
  String get securityLogActionLogout => 'Logout';

  @override
  String get securityLogActionPasswordChange => 'Password Changed';

  @override
  String get securityLogActionPasswordReset => 'Password Reset';

  @override
  String get securityLogActionRegister => 'Register';

  @override
  String get securityLogActionSocialLink => 'Social Account Linked';

  @override
  String get securityLogActionSocialUnlink => 'Social Account Unlinked';

  @override
  String get securityLogActionTokenRefresh => 'Token Refreshed';

  @override
  String securityLogAdditionalInfo(Object arg0) {
    return 'Details: $arg0';
  }

  @override
  String get securityLogEmpty => 'No security logs';

  @override
  String get securityLogIntro =>
      'Recent security events associated with your account.';

  @override
  String securityLogOccurredAt(Object arg0) {
    return '$arg0';
  }

  @override
  String get securityLogTitle => 'Security Log';

  @override
  String get sessionManagementCurrent => 'Current Device';

  @override
  String get sessionManagementEmpty => 'No active sessions';

  @override
  String sessionManagementFirstLogin(Object arg0) {
    return 'First login: $arg0';
  }

  @override
  String get sessionManagementIntro =>
      'Manage your active sessions. If you notice any suspicious activity, please revoke the related sessions.';

  @override
  String sessionManagementLastActive(Object arg0) {
    return 'Last active: $arg0';
  }

  @override
  String get sessionManagementRevokeOthers => 'Revoke Other Sessions';

  @override
  String get sessionManagementRevokeThis => 'Revoke';

  @override
  String get sessionManagementTitle => 'Session Management';

  @override
  String get sessionManagementUnknownDevice => 'Unknown Device';

  @override
  String get socialAccountsIntro =>
      'Link third-party accounts for quick sign-in';

  @override
  String get socialAccountsLink => 'Link';

  @override
  String get socialAccountsLinked => 'Linked';

  @override
  String get socialAccountsTitle => 'Linked Accounts';

  @override
  String get socialAccountsUnlink => 'Unlink';

  @override
  String get socialAccountsUnlinkConfirm => 'Confirm Unlink';

  @override
  String get socialAccountsUnlinkMessage =>
      'You won\'t be able to sign in with this account after unlinking';

  @override
  String socialAccountsUnlinkTitle(Object arg0) {
    return '$arg0';
  }

  @override
  String get socialAccountsUnlinkedHint => 'Not linked';

  @override
  String get socialAccountsWeChatPending => 'WeChat linking in progress';

  @override
  String get socialAccountsWeChatUnavailable => 'WeChat unavailable';

  @override
  String get sprintActionAbandonButton => 'Sprint Action Abandon Button';

  @override
  String get sprintActionAbandonSubtitle => 'Sprint Action Abandon Subtitle';

  @override
  String get sprintActionAbandonTitle => 'Sprint Action Abandon Title';

  @override
  String get sprintActionCompleteButton => 'Sprint Action Complete Button';

  @override
  String get sprintActionCompleteSubtitle => 'Sprint Action Complete Subtitle';

  @override
  String get sprintActionCompleteTitle => 'Sprint Action Complete Title';

  @override
  String get sprintActionExtendSubtitle => 'Sprint Action Extend Subtitle';

  @override
  String get sprintActionExtendTitle => 'Sprint Action Extend Title';

  @override
  String get sprintActionsTitle => 'Sprint Actions Title';

  @override
  String get sprintCompletedTasks => 'Sprint Completed Tasks';

  @override
  String get sprintCompletionRate => 'Sprint Completion Rate';

  @override
  String get sprintConfirmAbandonDesc => 'Sprint Confirm Abandon Desc';

  @override
  String sprintConfirmAbandonMessage(Object arg0) {
    return '$arg0';
  }

  @override
  String get sprintConfirmAbandonTitle => 'Sprint Confirm Abandon Title';

  @override
  String get sprintConfirmCompleteDesc => 'Sprint Confirm Complete Desc';

  @override
  String sprintConfirmCompleteMessage(Object arg0) {
    return '$arg0';
  }

  @override
  String get sprintConfirmCompleteTitle => 'Sprint Confirm Complete Title';

  @override
  String get sprintDailyCompletion => 'Sprint Daily Completion';

  @override
  String get sprintDurationDaysLabel => 'Sprint Duration Days Label';

  @override
  String sprintDurationDaysValue(Object arg0) {
    return '$arg0';
  }

  @override
  String get sprintDurationLabel => 'Sprint Duration Label';

  @override
  String get sprintEndDateLabel => 'Sprint End Date Label';

  @override
  String sprintExtendConfirm(Object arg0) {
    return '$arg0';
  }

  @override
  String sprintExtendMessage(Object arg0) {
    return '$arg0';
  }

  @override
  String sprintExtendOptionDays(Object arg0) {
    return '$arg0';
  }

  @override
  String get sprintExtendSelectDays => 'Sprint Extend Select Days';

  @override
  String get sprintExtendTitle => 'Sprint Extend Title';

  @override
  String get sprintIncompleteTasks => 'Sprint Incomplete Tasks';

  @override
  String get sprintInfoTitle => 'Sprint Info Title';

  @override
  String get sprintOngoing => 'Sprint Ongoing';

  @override
  String get sprintProgressTitle => 'Sprint Progress Title';

  @override
  String get sprintRemainingTasks => 'Sprint Remaining Tasks';

  @override
  String get sprintStartDateLabel => 'Sprint Start Date Label';

  @override
  String get sprintStatsEmpty => 'Sprint Stats Empty';

  @override
  String get sprintStatsTitle => 'Sprint Stats Title';

  @override
  String get sprintStatusCompleted => 'Sprint Status Completed';

  @override
  String get sprintStatusInProgress => 'Sprint Status In Progress';

  @override
  String get sprintStatusLabel => 'Sprint Status Label';

  @override
  String get sprintStatusTodo => 'Sprint Status Todo';

  @override
  String sprintTaskCount(Object arg0) {
    return '$arg0';
  }

  @override
  String get sprintTaskSummaryTitle => 'Sprint Task Summary Title';

  @override
  String get sprintTotalTasks => 'Sprint Total Tasks';

  @override
  String get statusCompleted => 'Status Completed';

  @override
  String get statusFailed => 'Status Failed';

  @override
  String get statusInProgress => 'Status In Progress';

  @override
  String get statusPending => 'Status Pending';

  @override
  String taskBatchCreateTitle(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskChatAssistantTitle => 'Task Chat Assistant Title';

  @override
  String get taskChatEmptyPrompt => 'Task Chat Empty Prompt';

  @override
  String get taskChatInputHint => 'Task Chat Input Hint';

  @override
  String get taskCreateAction => 'Task Create Action';

  @override
  String taskCreateFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskCreateSuccess => 'Task Create Success';

  @override
  String get taskCreateTitle => 'Task Create Title';

  @override
  String get taskCreatedWithSuggestions => 'Task Created With Suggestions';

  @override
  String get taskCreating => 'Task Creating';

  @override
  String get taskDeadline => 'Task Deadline';

  @override
  String get taskDeadlineLabel => 'Task Deadline Label';

  @override
  String get taskDeleteConfirm => 'Task Delete Confirm';

  @override
  String get taskDeleteTitle => 'Task Delete Title';

  @override
  String taskDetailLoadFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskDetailLoading => 'Task Detail Loading';

  @override
  String get taskDifficulty => 'Task Difficulty';

  @override
  String get taskDifficultyLabel => 'Task Difficulty Label';

  @override
  String taskDifficultyLevel(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskEnergyCost => 'Task Energy Cost';

  @override
  String get taskEnergyCostLabel => 'Task Energy Cost Label';

  @override
  String taskEnergyCostValue(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskEstimatedDuration => 'Task Estimated Duration';

  @override
  String get taskEstimatedDurationLabel => 'Task Estimated Duration Label';

  @override
  String get taskExecutionAbandon => 'Task Execution Abandon';

  @override
  String get taskExecutionCompleteTitle => 'Task Execution Complete Title';

  @override
  String get taskExecutionCompletedTitle => 'Task Execution Completed Title';

  @override
  String get taskExecutionConfirmComplete => 'Task Execution Confirm Complete';

  @override
  String taskExecutionElapsedMinutes(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskExecutionEnterFocus => 'Task Execution Enter Focus';

  @override
  String taskExecutionExpGained(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskExecutionFeatureCoach => 'Task Execution Feature Coach';

  @override
  String get taskExecutionFeatureDistraction =>
      'Task Execution Feature Distraction';

  @override
  String get taskExecutionFeatureFlipClock =>
      'Task Execution Feature Flip Clock';

  @override
  String get taskExecutionFeatureFullscreen =>
      'Task Execution Feature Fullscreen';

  @override
  String get taskExecutionFeatureReward => 'Task Execution Feature Reward';

  @override
  String get taskExecutionFeatureStarfield =>
      'Task Execution Feature Starfield';

  @override
  String get taskExecutionGuideEmpty => 'Task Execution Guide Empty';

  @override
  String get taskExecutionGuideTitle => 'Task Execution Guide Title';

  @override
  String get taskExecutionNoTask => 'Task Execution No Task';

  @override
  String get taskExecutionNoteHint => 'Task Execution Note Hint';

  @override
  String get taskExecutionNoteLabel => 'Task Execution Note Label';

  @override
  String get taskExecutionSkipAnimation => 'Task Execution Skip Animation';

  @override
  String taskExecutionStartFailed(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskExecutionStartNow => 'Task Execution Start Now';

  @override
  String get taskExecutionSyncFailed => 'Task Execution Sync Failed';

  @override
  String get taskExecutionFreeFocusCompleted => 'Free focus completed';

  @override
  String get taskExecutionTapToContinue => 'Task Execution Tap To Continue';

  @override
  String get taskExecutionTimerLabel => 'Task Execution Timer Label';

  @override
  String get taskExitCancelStep1 => 'Task Exit Cancel Step1';

  @override
  String get taskExitCancelStep2 => 'Task Exit Cancel Step2';

  @override
  String get taskExitCancelStep3 => 'Task Exit Cancel Step3';

  @override
  String get taskExitConfirmStep1 => 'Task Exit Confirm Step1';

  @override
  String get taskExitConfirmStep2 => 'Task Exit Confirm Step2';

  @override
  String get taskExitConfirmStep3 => 'Task Exit Confirm Step3';

  @override
  String get taskExitMessageStep1 => 'Task Exit Message Step1';

  @override
  String taskExitMessageStep2(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get taskExitMessageStep3 => 'Task Exit Message Step3';

  @override
  String get taskExitTitleStep1 => 'Task Exit Title Step1';

  @override
  String get taskExitTitleStep2 => 'Task Exit Title Step2';

  @override
  String get taskExitTitleStep3 => 'Task Exit Title Step3';

  @override
  String get taskGenerateGuideSubtitle => 'Task Generate Guide Subtitle';

  @override
  String get taskGenerateGuideTitle => 'Task Generate Guide Title';

  @override
  String get taskGuideEmpty => 'Task Guide Empty';

  @override
  String get taskGuideTitle => 'Task Guide Title';

  @override
  String get taskListLoading => 'Task List Loading';

  @override
  String get taskListTitle => 'Task List Title';

  @override
  String taskMinutesOption(Object arg0) {
    return '$arg0';
  }

  @override
  String taskNudgeApplied(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskNudgeApply => 'Task Nudge Apply';

  @override
  String taskNudgeConfidence(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskNudgeDismiss => 'Task Nudge Dismiss';

  @override
  String get taskNudgeTitle => 'Task Nudge Title';

  @override
  String get taskReminderEnableSubtitle => 'Task Reminder Enable Subtitle';

  @override
  String get taskReminderEnableTitle => 'Task Reminder Enable Title';

  @override
  String get taskReminderInfoBody => 'Task Reminder Info Body';

  @override
  String get taskReminderInfoTitle => 'Task Reminder Info Title';

  @override
  String get taskReminderPermissionDenied => 'Task Reminder Permission Denied';

  @override
  String get taskReminderRefreshAll => 'Task Reminder Refresh All';

  @override
  String get taskReminderRefreshSuccess => 'Task Reminder Refresh Success';

  @override
  String get taskReminderSettingsTitle => 'Task Reminder Settings Title';

  @override
  String get taskReminderTimesTitle => 'Task Reminder Times Title';

  @override
  String get taskSearchHint => 'Task Search Hint';

  @override
  String get taskStart => 'Task Start';

  @override
  String get taskSuggestedKnowledge => 'Task Suggested Knowledge';

  @override
  String get taskTagsHint => 'Task Tags Hint';

  @override
  String get taskTagsLabel => 'Task Tags Label';

  @override
  String taskTimerMinutes(Object arg0) {
    return '$arg0';
  }

  @override
  String get taskTimerPomodoro => 'Task Timer Pomodoro';

  @override
  String get taskTitleHint => 'Task Title Hint';

  @override
  String get taskTitleLabel => 'Task Title Label';

  @override
  String get taskTitleRequired => 'Task Title Required';

  @override
  String get taskTypeLabel => 'Task Type Label';

  @override
  String get taskTypeOcr => 'Task Type Ocr';

  @override
  String get taskUntitled => 'Task Untitled';

  @override
  String get taskViewAll => 'Task View All';

  @override
  String get weeklyAgendaCollapsedHint => 'Weekly Agenda Collapsed Hint';

  @override
  String get weeklyAgendaEmptyHint => 'Weekly Agenda Empty Hint';

  @override
  String weeklyAgendaSummary(Object arg0, Object arg1, Object arg2) {
    return '$arg0 $arg1 $arg2';
  }

  @override
  String securityLogDevice(Object arg0) {
    return 'Device: $arg0';
  }

  @override
  String get sessionManagementCurrentHint => 'This is your current device';

  @override
  String get personaAdjustInferredPreference => 'Adjust inferred preference';

  @override
  String get personaNewValue => 'New value';

  @override
  String get personaAdjustInferredPreferenceTitle =>
      'Adjust Inferred Preference';

  @override
  String get languageDialogDescription =>
      'Choose your preferred reading and interaction language. The interface and system copy will switch together.';

  @override
  String get languageChineseDescription =>
      'Better suited for Chinese reading and localized expressions.';

  @override
  String get languageEnglishDescription =>
      'Suited for English interface and a more international content environment.';

  @override
  String get learningModeSubtitle => 'Adjust depth and curiosity preferences';

  @override
  String get learningPreferenceSaving => 'Saving...';

  @override
  String get learningPreferenceSaved => 'Learning mode preference saved';

  @override
  String learningPreferenceSaveFailed(String error) {
    return 'Save failed: $error';
  }

  @override
  String get learningPreferenceAutoSaveHint => 'Drag to auto-save to backend';

  @override
  String get bgmVolume => 'Music Volume';

  @override
  String get bgmScenePreference => 'Scene Preference';

  @override
  String bgmPreviewTooltip(String palette) {
    return 'Preview $palette';
  }

  @override
  String get bgmAdvancedControls => 'Advanced Controls';

  @override
  String get bgmAdvancedControlsSubtitle =>
      'Control music intensity, rotation frequency, reading protection, focus priority, and style locking';

  @override
  String get chatPureMode => 'Pure Mode';

  @override
  String get chatPureModeSubtitle =>
      'Keep only text messages in chat, hiding extra info cards and widgets below messages.';

  @override
  String get motionIntensity => 'Motion Intensity';

  @override
  String get aiUsagePanelUnavailable =>
      'Quota panel is temporarily unavailable, but tier switching still works.';

  @override
  String get aiOpsPanelUnavailable =>
      'Ops panel is temporarily unavailable, but AI tier and usage stats still work.';

  @override
  String get notificationManageSubtitle =>
      'Manage system notifications, intervention alerts, quiet hours, and task reminders.';

  @override
  String get notificationLoadingPrefs => 'Loading notification preferences...';

  @override
  String get notificationSystem => 'System Notifications';

  @override
  String get notificationSystemSubtitle =>
      'Control task reminders, achievements, system messages, and in-app notifications';

  @override
  String get notificationInterventions => 'Intervention Alerts';

  @override
  String get notificationInterventionsSubtitle =>
      'Control coach/agent intervention and guidance reminders';

  @override
  String get notificationReminders => 'Reminders';

  @override
  String get notificationRemindersSubtitle =>
      'Control task, plan progress, and comeback reminders';

  @override
  String get notificationSpacedRepetition => 'Review';

  @override
  String get notificationSpacedRepetitionSubtitle =>
      'Control Galaxy spaced repetition reminders';

  @override
  String get notificationWeeklyReport => 'Weekly Report';

  @override
  String get notificationWeeklyReportSubtitle =>
      'Control weekly growth report and learning summary notifications';

  @override
  String get notificationMilestone => 'Milestones';

  @override
  String get notificationMilestoneSubtitle =>
      'Control achievement, stage completion, and progress milestone notifications';

  @override
  String get notificationLevel => 'Notification Level';

  @override
  String notificationLevelSwitched(String level) {
    return 'Notification level switched to $level';
  }

  @override
  String get notificationLevelMinimal => 'Minimal';

  @override
  String get notificationLevelStandard => 'Standard';

  @override
  String get notificationLevelVerbose => 'Verbose';

  @override
  String get notificationLevelMinimalDesc =>
      'Only keep essential reminders to minimize disruption.';

  @override
  String get notificationLevelStandardDesc =>
      'Balance information volume and notification frequency.';

  @override
  String get notificationLevelVerboseDesc =>
      'Show more complete background info and reminder content.';

  @override
  String get notificationLevelMinimalPreview =>
      'Only critical reminders, such as tasks due soon and system notifications that need immediate action.';

  @override
  String get notificationLevelStandardPreview =>
      'Keep primary reminders and add brief context when needed, suitable for most scenarios.';

  @override
  String get notificationLevelVerbosePreview =>
      'Includes more context, such as why you\'re being reminded, next-step suggestions, and supplementary notes.';

  @override
  String notificationLevelPreviewTitle(String level) {
    return '$level Notifications';
  }

  @override
  String get notificationQuietHours => 'Quiet Hours';

  @override
  String get notificationQuietHoursSubtitle =>
      'When off, the system will push notifications at the normal pace';

  @override
  String get notificationQuietHoursStart => 'Start Time';

  @override
  String get notificationQuietHoursEnd => 'End Time';

  @override
  String get notificationQuietHoursHint =>
      'Supports crossing midnight, e.g. 22:00 - 08:00; start and end times cannot be the same.';

  @override
  String get notificationQuietHoursSameTimeError =>
      'Start and end times cannot be the same';

  @override
  String get notificationQuietHoursStartUpdated =>
      'Quiet hours start time updated';

  @override
  String get notificationQuietHoursEndUpdated => 'Quiet hours end time updated';

  @override
  String notificationUpdateFailed(String error) {
    return 'Failed to update notification settings: $error';
  }

  @override
  String get aiExecutionEngine => 'AI Execution Engine';

  @override
  String get aiExecutionEngineSubtitle =>
      'Connect your OpenClaw instance and monitor health status';

  @override
  String get capsuleGenerated => 'New curiosity capsule generated';

  @override
  String get capsuleGeneratedEmpty =>
      'A new capsule has been generated. Tap below to view the full content.';

  @override
  String get capsuleViewNew => 'View New Capsule';

  @override
  String get capsulePreviewFailed => 'Preview failed, please check audio files';

  @override
  String get capsuleScenePreviewFailed =>
      'Current scene preview failed, please check audio files';

  @override
  String aiReasoningModeSwitched(String mode) {
    return 'AI reasoning mode switched to $mode';
  }

  @override
  String get aiReasoningModeSwitchFailed =>
      'AI reasoning mode switch failed, please try again later';

  @override
  String get aiReasoningFastDesc =>
      'Prioritizes faster results, suitable for short Q&A, lightweight queries, and low-latency scenarios.';

  @override
  String get aiReasoningBalancedDesc =>
      'Balances speed and reasoning depth, suitable for most daily use.';

  @override
  String get aiReasoningDeepDesc =>
      'Invests more reasoning budget, suitable for complex problems, planning, and high-precision explanations.';

  @override
  String get taskReminderDisabled => 'Disabled';

  @override
  String get taskReminderEnabledNoTime =>
      'Enabled, but no reminder times selected yet';

  @override
  String get taskReminderEnabledWithTimes => 'Enabled';

  @override
  String taskReminderDaysAgo(int days) {
    return '${days}d ago';
  }

  @override
  String taskReminderHoursAgo(int hours) {
    return '${hours}h ago';
  }

  @override
  String taskReminderMinutesAgo(int minutes) {
    return '${minutes}min ago';
  }

  @override
  String notificationPermissionDeniedTitle(String error) {
    return 'Not authorized: $error';
  }

  @override
  String get notificationRequestPermission => 'Request Permission';

  @override
  String get notificationOpenSettings => 'Open Settings';

  @override
  String get notificationPermissionDialogTitle => 'Notification Permission';

  @override
  String get notificationPermissionDialogContent =>
      'Notification permission has been denied. Please enable it in system settings.';

  @override
  String get bgmPaletteAdaptive => 'Adaptive';

  @override
  String get bgmPaletteClassical => 'Classical';

  @override
  String get bgmPalettePiano => 'Piano';

  @override
  String get bgmPaletteAiry => 'Airy';

  @override
  String get bgmPaletteWarm => 'Warm';

  @override
  String get bgmPaletteAdaptiveDesc =>
      'The system automatically selects the most suitable background music based on page function.';

  @override
  String get bgmPaletteClassicalDesc =>
      'Curated classical piano and strings, prioritizing your local classical library for scene transitions.';

  @override
  String get bgmPalettePianoDesc =>
      'Overall emphasis on light piano and quiet melodies, suitable for long-term companionship.';

  @override
  String get bgmPaletteAiryDesc =>
      'Overall emphasis on ethereal, dreamy, and spatially rich atmospheres.';

  @override
  String get bgmPaletteWarmDesc =>
      'Overall emphasis on warm, soft, and human-feeling upbeat tones.';

  @override
  String get bgmIntensityGentle => 'Gentle';

  @override
  String get bgmIntensityBalanced => 'Balanced';

  @override
  String get bgmIntensityLush => 'Lush';

  @override
  String get bgmIntensityGentleDesc =>
      'Better for long-term companionship, prioritizing light density, low interference, and slow transitions.';

  @override
  String get bgmIntensityBalancedDesc =>
      'Adds a bit more layer and presence while maintaining comfort.';

  @override
  String get bgmIntensityLushDesc =>
      'Makes the same scene more atmospheric and enveloping, while still avoiding obvious abruptness.';

  @override
  String get bgmVarietySteady => 'Steady';

  @override
  String get bgmVarietyBalanced => 'Balanced';

  @override
  String get bgmVarietyDynamic => 'Dynamic';

  @override
  String get bgmVarietySteadyDesc =>
      'Minimize track changes and repetition for a more continuous atmosphere.';

  @override
  String get bgmVarietyBalancedDesc =>
      'Keep a middle ground between continuity and freshness.';

  @override
  String get bgmVarietyDynamicDesc =>
      'Reduce repetition so similar pages can hear new variations more often.';

  @override
  String get bgmModeAdaptive => 'Follow Page';

  @override
  String get bgmModeContinuous => 'Player Mode';

  @override
  String get bgmModeFocusOnly => 'Focus Only';

  @override
  String get bgmModeSilent => 'Global Silent';

  @override
  String get bgmModeAdaptiveDesc =>
      'Home, chat, tasks, achievements, and other pages will automatically switch to matching ambient music.';

  @override
  String get bgmModeContinuousDesc =>
      'The current track keeps playing without being interrupted when you navigate to another page, great for using the App as a relaxing music player.';

  @override
  String get bgmModeFocusOnlyDesc =>
      'Background music only plays when focus starts, during immersion, and when executing tasks; daily pages stay quiet.';

  @override
  String get bgmModeSilentDesc =>
      'Keep sound effects and haptic feedback, but all background music won\'t autoplay.';

  @override
  String get motionIntensityUltra => 'Ultra';

  @override
  String get motionIntensityHigh => 'High';

  @override
  String get motionIntensityMedium => 'Medium';

  @override
  String get motionIntensityOff => 'Off';

  @override
  String get motionIntensityUltraDesc =>
      'Keep full particles, glow, and complex animations, suitable for high-performance devices.';

  @override
  String get motionIntensityHighDesc =>
      'Maintain most visual layers while allowing the system to auto-downgrade by frame rate.';

  @override
  String get motionIntensityMediumDesc =>
      'Tone down particles and glow, prioritize stability and battery saving, while retaining basic depth.';

  @override
  String get motionIntensityOffDesc =>
      'Try to disable strong animations and particle layers, suitable for static, low-stimulus, or low-performance scenarios.';

  @override
  String get bgmSectionSubtitleDefault =>
      'Manage background music by page and player mode';

  @override
  String bgmSectionSubtitleWithCount(int count) {
    return 'Currently $count tracks, freely switch between page strategy and player mode';
  }

  @override
  String bgmLibraryUpdated(int count) {
    return 'Library updated to $count tracks';
  }

  @override
  String get bgmOpenLibrary => 'Open Library';

  @override
  String get bgmCurated => 'Curated';

  @override
  String get bgmImported => 'Local Import';

  @override
  String get bgmBundled => 'System Fallback';

  @override
  String get bgmModeLabel => 'Mode';

  @override
  String get bgmPlayerMode => 'Player Mode';

  @override
  String get bgmPageStrategyMode => 'Page Strategy';

  @override
  String get bgmLibraryHint =>
      'In the new page, you can request tracks from the library, import your own music, and enable \'Player Mode\' for cross-page continuous BGM.';

  @override
  String get bgmNotPlaying => 'Not currently playing';

  @override
  String get bgmBundledTrack => 'Built-in scene track';

  @override
  String get bgmWaitingPlayback => 'Waiting for playback info';

  @override
  String get bgmDisabled => 'Background music disabled';

  @override
  String get bgmGlobalSilent => 'Currently in global silent mode';

  @override
  String get bgmContinuousPlaying => 'Player mode playing continuously';

  @override
  String get bgmNowPlaying => 'Now Playing';

  @override
  String get bgmPreviewCurrentScene => 'Preview Current Scene';

  @override
  String bgmTrackLabel(String name) {
    return 'Track: $name';
  }

  @override
  String bgmSourceLabel(String label) {
    return 'Source: $label';
  }

  @override
  String get bgmIntensityLabel => 'Intensity';

  @override
  String get bgmVarietyLabel => 'Variety';

  @override
  String get bgmReadingProtection => 'Reading Protection';

  @override
  String get bgmFocusPriority => 'Focus Priority';

  @override
  String get bgmStyleLocked => 'Style Locked';

  @override
  String get bgmReadingProtectionTitle => 'Reading Protection';

  @override
  String get bgmReadingProtectionSubtitle =>
      'Chat, insights, and profile pages prioritize low-stimulus and light mixing';

  @override
  String get bgmFocusPriorityTitle => 'Focus Priority';

  @override
  String get bgmFocusPrioritySubtitle =>
      'Focus and execution stages prioritize purer and more stable tracks';

  @override
  String get bgmLockStyleTitle => 'Lock Current Style';

  @override
  String get bgmLockStyleSubtitle =>
      'Continue current vibe across regular pages, without overriding focus and celebration scenes';

  @override
  String get bgmAtmosphereIntensity => 'Atmosphere Intensity';

  @override
  String get bgmVarietyFrequency => 'Track Change Frequency';

  @override
  String get aiUsageTodayPreparing =>
      'Today\'s quota stats are being prepared.';

  @override
  String get aiUsageTodayTitle => 'Today\'s AI Quota & Usage';

  @override
  String aiUsageRequests(int used, int limit) {
    return '$used/$limit times';
  }

  @override
  String aiUsageLatency(String firstToken, String totalMs) {
    return 'Avg first token ${firstToken}ms · Avg total ${totalMs}ms';
  }

  @override
  String get aiOpsModesAccumulating =>
      'Mode-level ops metrics are still accumulating.';

  @override
  String get aiOpsTopChatModeStandard => 'Standard Chat';

  @override
  String get aiOpsTopChatModeStudyPlan => 'Study Planning';

  @override
  String get aiOpsTopChatModeDeepAnalysis => 'Deep Analysis';

  @override
  String get aiOpsTopChatModeErrorDiagnosis => 'Error Diagnosis';

  @override
  String get aiOpsTopChatModeExpertAuto => 'Expert Collaboration';

  @override
  String get aiOpsUserViewTitle => 'User Perspective';

  @override
  String get aiOpsUserViewDesc =>
      'Focus on whether AI responds fast, stable, and can push suggestions into real execution, not just model-layer parameters.';

  @override
  String get aiOpsSuccessRate => 'Success Rate';

  @override
  String get aiOpsAvgFirstToken => 'Avg First Token';

  @override
  String get aiOpsAvgTotalDuration => 'Avg Total Duration';

  @override
  String get aiOpsExecutionConversion => 'Execution Conversion';

  @override
  String get aiOpsPredictedAcceptExec => 'Predicted Accept-to-Exec';

  @override
  String aiOpsTopModeSummary(String topMode) {
    return 'The most recently used chain is \"$topMode\", indicating it\'s already the main workflow in daily experience.';
  }

  @override
  String get aiOpsDevViewTitle => 'Dev Ops Perspective';

  @override
  String get aiOpsDevViewDesc =>
      'Here we look at speed, cost, fallback, and prediction conversion to decide which mode chain to optimize next.';

  @override
  String get aiOpsMonitoringModes => 'Monitoring Modes';

  @override
  String get aiOpsTotalRequests => 'Total Requests';

  @override
  String get aiOpsFallback => 'Fallback';

  @override
  String get aiOpsTotalCost => 'Total Cost';

  @override
  String get aiOpsPromptHit => 'Prompt Hit';

  @override
  String get aiOpsInferenceHit => 'Inference Hit';

  @override
  String aiOpsPredictionSummary(
      int days, String topAction, String promptUtil, String inferenceUtil) {
    return 'In the past $days days, the prediction action worth watching most is \"$topAction\"; prompt/inference hit rates are $promptUtil%/$inferenceUtil%.';
  }

  @override
  String get aiOpsOpenAnalysis => 'Open AI Ops Analysis';

  @override
  String get aiOpsOpenAdminPanel => 'Open Admin Ops Panel';

  @override
  String get memoryDeclaration => 'Declaration';

  @override
  String get memoryEvidenceToken => 'Evidence Token';

  @override
  String get memoryDecayPolicy => 'Decay Policy';

  @override
  String memoryUpdateValue(String date) {
    return 'Updated: $date';
  }

  @override
  String memoryConfidenceValue(String value) {
    return 'Confidence: $value';
  }

  @override
  String memoryAllowedCaptureSummary(String types, String level) {
    return 'Allowed capture: $types\nCapture level: $level';
  }

  @override
  String get memoryAiInferredDisabledHint =>
      'AI auto-memory is currently disabled, such inferred memories will not be recorded.';

  @override
  String get memoryExplanationInferredEpisodic =>
      'This experience was inferred by AI from chat, with evidence tokens, confidence, and retraction path preserved.';

  @override
  String memoryCorrectionSubmittedWithAction(String action) {
    return 'Correction submitted: $action';
  }

  @override
  String memoryCorrectionFailedWithDetail(String error) {
    return 'Correction failed: $error';
  }

  @override
  String tracksCount(int count) {
    return '$count tracks';
  }

  @override
  String get profilePrestigeIdentity => 'Prestige Identity';

  @override
  String get profileNoTitleEquipped => 'No title equipped';

  @override
  String get profileRecentHighlights => 'Recent Highlights';

  @override
  String get profileNoHighlightsHint =>
      'Keep learning and sprinting to light up your Prestige Showcase.';

  @override
  String get profileTraitQ1Title =>
      'When starting a new goal, which approach fits you better?';

  @override
  String get profileTraitQ1Structured => 'Build structure first, then act';

  @override
  String get profileTraitQ1Mixed =>
      'Start with a framework, then adjust as you go';

  @override
  String get profileTraitQ1Explore => 'Try it out and let the direction emerge';

  @override
  String get profileTraitSkip => 'Skip';

  @override
  String get profileTraitQ2Title =>
      'When facing tough problems, where do you recharge?';

  @override
  String get profileTraitQ2Solo => 'Think it through alone first';

  @override
  String get profileTraitQ2SmallGroup => 'Discuss with one or two people';

  @override
  String get profileTraitQ2Group => 'Think through discussion';

  @override
  String get profileTraitQ3Title =>
      'When your plan gets disrupted, what\'s your first reaction?';

  @override
  String get profileTraitQ3Replan => 'Replan immediately and get back on track';

  @override
  String get profileTraitQ3Pause => 'Get stuck briefly, but slowly recover';

  @override
  String get profileTraitQ3Swing => 'Both mood and rhythm are affected';

  @override
  String get profileLearningPortfolio => 'Learning Portfolio';

  @override
  String get profileLearningPortfolioSubtitle =>
      'View sprint history, in-progress and planned records across all subjects';

  @override
  String get profilePosterStudio => 'Poster Studio';

  @override
  String get profilePosterStudioSubtitle =>
      'Turn growth, plans, and inspiration into shareable posters';

  @override
  String get profileMyWay => 'My Way';

  @override
  String get profileMetacognitionPanel => 'Metacognition Panel';

  @override
  String get profileMetacognitionHidden =>
      'Hidden, but still calculating in the background';

  @override
  String get profileMetacognitionVisible =>
      'Show judgment bias summary from past samples';

  @override
  String get profileExportData => 'Export My Data';

  @override
  String get profileExportPreparing => 'Preparing data, please wait...';

  @override
  String get profileExportEmptyFile => 'Empty file';

  @override
  String get profileExportShareSubject => 'Sparkle Data Export';

  @override
  String profileExportFailed(String error) {
    return 'Export failed: $error';
  }

  @override
  String get profileSubtitleAchievements =>
      'View unlocked milestones and honor progress';

  @override
  String get profileSubtitleVisualElements =>
      'Manage backgrounds, particles, and visual rewards';

  @override
  String get profileSubtitlePersona =>
      'View learning traits and preferences understood by the system';

  @override
  String get profileSubtitlePersonalInfo =>
      'Edit avatar, nickname, and basic info';

  @override
  String get profileSubtitlePreferences =>
      'Manage sensory feedback, learning mode, and push preferences';

  @override
  String get profileSubtitleMyWay =>
      'Manage private skills, sharing, and anonymous forks';

  @override
  String get profileSubtitleSecurity =>
      'View security info, devices, and privacy controls';

  @override
  String get profileSubtitleMemory =>
      'Adjust long-term memory and context retention strategy';

  @override
  String get profileSubtitleLogout => 'Safely log out of your account';

  @override
  String get profileSubtitleDeleteAccount =>
      'Permanently remove your account and associated data';

  @override
  String get profileSubtitleDefault =>
      'Continue adjusting detailed settings on this page';

  @override
  String get chatSelfVisibleOnly => 'Self-visible only';

  @override
  String get chatSelfVisibleDraftDesc =>
      'This AI draft is only saved in your current private chat view.';

  @override
  String get chatPromoteToBothVisible => 'Make visible to both';

  @override
  String get chatPromoteToBothDesc =>
      'Put this draft back in the input box for you to confirm before sending.';

  @override
  String get chatViewAccessoryContent => 'View additional content';

  @override
  String get chatViewAccessoryContentDesc =>
      'Temporarily expand task cards and quick actions in pure mode';

  @override
  String get chatActionSuggestion => 'Action suggestion';

  @override
  String get chatActionSuggestionDesc =>
      'Continue this step, or confirm the task and plan first.';

  @override
  String get chatTheaterTitle => 'Prediction Theater';

  @override
  String get chatTheaterDesc =>
      'See which path is worth exploring now and why it suits you better.';

  @override
  String get chatSimulationTitle => 'Learning Simulation';

  @override
  String get chatSimulationDesc =>
      'See the key viewpoint clash first, then decide whether to enter the full simulation.';

  @override
  String get chatReportTitle => 'Learning Report';

  @override
  String get chatReportDesc =>
      'See the core diagnosis and next steps first, then decide whether to enter the full report.';

  @override
  String get chatAccessoryContent => 'Additional content';

  @override
  String get chatContinueExploring => 'Continue exploring';

  @override
  String get chatSwipeToSwitch => 'Swipe left/right to switch entries';

  @override
  String get chatViewTheaterDetails => 'View prediction details';

  @override
  String get chatCurrentLearningTopic => 'Current learning topic';

  @override
  String get chatViewSimulationDetails => 'View simulation details';

  @override
  String get chatCollaborationProcess => 'Collaboration process';

  @override
  String get chatPlanContext => 'Plan context';

  @override
  String get chatPlanStatus => 'Plan status';

  @override
  String get chatContinueFromConversation => 'Continue from the conversation';

  @override
  String get chatReviewFirstThenExpand =>
      'Review highlights first, then decide whether to expand';

  @override
  String get chatPathLabel => 'Path';

  @override
  String get chatMasteryLabel => 'Mastery';

  @override
  String get chatOpenFullExperience => 'Open full experience';

  @override
  String get chatContinueInChat => 'Continue in chat';

  @override
  String get chatViewLatestReport => 'View latest learning report';

  @override
  String get chatViewLearningReport => 'View learning report';

  @override
  String get chatKeyFocusLabel => 'Key focus';

  @override
  String get chatShareResourceInvalidId =>
      'Invalid share resource ID, cannot adopt';

  @override
  String get chatShareResourceAdopted => 'Adopted, navigating...';

  @override
  String chatShareResourceAdoptError(Object error) {
    return 'Adoption failed: $error';
  }

  @override
  String chatTaskConfirmedMessage(Object count) {
    return 'Confirmed $count tasks, starting execution!';
  }

  @override
  String get chatViewPlan => 'View plan';

  @override
  String get chatGoToTaskList => 'Go to task list';

  @override
  String chatConfirmFailed(Object error) {
    return 'Confirmation failed: $error';
  }

  @override
  String chatTaskCompletedDoneMinutes(Object minutes) {
    return 'Completed · ${minutes}min';
  }

  @override
  String get chatTaskCompletedDone => 'Completed';

  @override
  String chatPlanProgressLabel(Object percent) {
    return 'Progress: $percent%';
  }

  @override
  String get chatPromptPreviewCancel => 'Not now';

  @override
  String get chatPromptPreviewSend => 'Send now';

  @override
  String get chatParticipantLabel => 'Participant';

  @override
  String get chatPromptRefinePath => 'Continue refining this path';

  @override
  String chatPromptRefinePathMessage(Object topic) {
    return 'Continue refining the first week\'s priority steps around \"$topic\".';
  }

  @override
  String get chatPromptComparePaths => 'Compare two paths';

  @override
  String chatPromptComparePathsMessage(Object pathA, Object pathB) {
    return 'Compare the trade-offs between \"$pathA\" and \"$pathB\".';
  }

  @override
  String get chatPromptDefaultPathA => 'Path A';

  @override
  String get chatPromptDefaultPathB => 'Path B';

  @override
  String get chatPromptPrerequisites => 'What prerequisites to cover first';

  @override
  String chatPromptPrerequisitesMessage(Object topic) {
    return 'If I start learning \"$topic\" now, what prerequisites should I cover first?';
  }

  @override
  String get chatPromptExamFocus => 'What are the exam key points';

  @override
  String chatPromptExamFocusMessage(Object topic) {
    return 'Tell me the parts of \"$topic\" most likely to be exam key points and why.';
  }

  @override
  String get chatPromptMakePlan => 'Make it a plan';

  @override
  String chatPromptMakePlanMessage(Object topic) {
    return 'Rewrite the \"$topic\" path into a 7-day executable mini-plan.';
  }

  @override
  String get chatPromptSimulateRound => 'Continue simulating another round';

  @override
  String chatPromptSimulateRoundMessage(Object topic) {
    return 'Simulate another round around \"$topic\". I want to continue this learning scenario.';
  }

  @override
  String get chatOneOfTheRoles => 'One of the roles';

  @override
  String get chatPromptLetMeAnswer => 'Let me answer';

  @override
  String chatPromptLetMeAnswerMessage(Object speaker, Object topic) {
    return 'Have $speaker ask me a follow-up question around \"$topic\", and I\'ll answer.';
  }

  @override
  String get chatPromptPracticeExplain => 'Practice explaining to others';

  @override
  String chatPromptPracticeExplainMessage(Object topic) {
    return 'Arrange a simulation round around \"$topic\" where I explain to someone else.';
  }

  @override
  String get chatPromptErrorDiagnosis => 'Switch to error diagnosis';

  @override
  String chatPromptErrorDiagnosisMessage(Object topic) {
    return 'Switch \"$topic\" to error diagnosis mode and help me identify the real blocker.';
  }

  @override
  String get chatPromptOrderActions => 'Order today\'s actions';

  @override
  String get chatPromptOrderActionsMessage =>
      'Based on this learning report, help me create an action order I can start today.';

  @override
  String get chatPromptExpandKeyIssue => 'Expand on key issues';

  @override
  String chatPromptExpandKeyIssueMessage(Object highlight) {
    return 'Explain in detail why \"$highlight\" deserves priority attention.';
  }

  @override
  String get chatPromptPrioritizeArea => 'Which area to cover first';

  @override
  String chatPromptPrioritizeAreaMessage(Object area) {
    return 'Based on this report, explain why \"$area\" should be processed first.';
  }

  @override
  String get chatPromptConvertToPlan => 'Convert to 7-day plan';

  @override
  String get chatPromptConvertToPlanMessage =>
      'Rewrite this learning report into my next 7-day execution sequence.';

  @override
  String get chatPromptReviewOutline => 'Help me make a review outline';

  @override
  String get chatPromptReviewOutlineMessage =>
      'Based on this learning report, give me a review outline I can use tonight.';

  @override
  String dashboardBottleneckPrompt(String topic) {
    return 'I want to understand $topic differently. Help me adjust my learning path based on this bottleneck.';
  }

  @override
  String get dashboardSetFirstGoal => 'Set your first goal';

  @override
  String get dashboardSetFirstGoalSummary =>
      'Tell me the one thing you want to move forward, and I will turn it into an actionable plan.';

  @override
  String get dashboardStartWithAI => 'Start with AI';

  @override
  String get dashboardOpenTaskList => 'Open tasks';

  @override
  String get dashboardDueToday => 'Due today';

  @override
  String dashboardOverdueDays(int days) {
    return '$days days overdue';
  }

  @override
  String dashboardDaysLeft(int days) {
    return '$days days left';
  }

  @override
  String get dashboardMainMove => '1 main move';

  @override
  String dashboardMoreQueued(int count) {
    return '$count more queued';
  }

  @override
  String dashboardProgress(int percent) {
    return '$percent% progress';
  }

  @override
  String get dashboardTodayBriefing => 'Today Briefing';

  @override
  String get dashboardBriefingSummary => 'One place for the important stuff';

  @override
  String get dashboardSparkleObservation => 'What Sparkle Noticed';

  @override
  String get dashboardStartWithThis => 'Start With This';

  @override
  String get dashboardGrowthSignal => 'Growth Signal';

  @override
  String dashboardMoreTasksQueued(int count) {
    return '$count more tasks are still queued after this one.';
  }

  @override
  String get dashboardStartFocus => 'Start Focus';

  @override
  String get dashboardStartHere => 'Start Here';

  @override
  String get dashboardOpenTasks => 'Open Tasks';

  @override
  String get dashboardTaskList => 'View Tasks';

  @override
  String get dashboardActivePlan => 'Active Plan';

  @override
  String dashboardPhaseLabel(String phase) {
    return 'Phase: $phase';
  }

  @override
  String get dashboardPhaseInProgress => 'in progress';

  @override
  String dashboardDaysToDeadline(int days) {
    return '$days days to deadline';
  }

  @override
  String get dashboardPrediction => 'prediction';

  @override
  String dashboardMessagesCount(int count) {
    return '$count messages';
  }

  @override
  String dashboardAlertsCount(int count) {
    return '$count alerts';
  }

  @override
  String dashboardInsightsCount(int count) {
    return '$count insights';
  }

  @override
  String get dashboardReviewPending => 'review pending';

  @override
  String get dashboardUpdatesInsights => 'Updates & Insights';

  @override
  String planEditTypeTitle(String type) {
    return 'Edit $type';
  }

  @override
  String get planUpdated => 'Plan updated';

  @override
  String get planGuideFillNameAndGoalFirst =>
      'Fill in the plan name and goal first, then generate the AI guide';

  @override
  String get planGuideGeneratedHuman => 'Human execution guide generated';

  @override
  String get planGuideGeneratedAi => 'AI execution version generated';

  @override
  String planGuideGenerationFailed(String error) {
    return 'Failed to generate plan guide: $error';
  }

  @override
  String get planSuggestedGrowthTask1 => 'Set up this week\'s main task list';

  @override
  String get planSuggestedGrowthTask2 => 'Complete a milestone review';

  @override
  String get planSuggestedSprintTask1 =>
      'Confirm sprint goals and acceptance criteria';

  @override
  String get planSuggestedSprintTask2 => 'Complete key sprint milestones';

  @override
  String get planSave => 'Save plan';

  @override
  String get planStepBasics => 'Plan setup';

  @override
  String get planStepSchedule => 'Schedule';

  @override
  String get planStepTasks => 'Tasks';

  @override
  String get planStepGuide => 'Boundaries & guide';

  @override
  String get planStepReview => 'Review';

  @override
  String get planAiVersionCopied => 'AI version copied';

  @override
  String get planBasicsDescription =>
      'Define this as a real plan card, not just a regular task.';

  @override
  String get planBasicsNameHint =>
      'e.g., 6-week English speaking improvement / midterm sprint wrap-up';

  @override
  String get planBasicsNameRequired => 'Please fill in the plan name first';

  @override
  String get planBasicsSubjectLabel => 'Subject';

  @override
  String get planBasicsSubjectHint =>
      'English, Flutter, GRE Math, paper reading...';

  @override
  String get planBasicsGoalLabelGrowth => 'Long-term goal';

  @override
  String get planBasicsGoalLabelSprint => 'Sprint goal';

  @override
  String get planBasicsGoalHintGrowth =>
      'Describe the ability, habit, or outcome this growth plan aims to achieve.';

  @override
  String get planBasicsGoalHintSprint =>
      'Describe the sprint outcome, acceptance criteria, and non-negotiable focus.';

  @override
  String get planBasicsGoalRequired =>
      'Please describe the goal of this plan card';

  @override
  String get planBasicsPriorityLabel => 'Plan priority';

  @override
  String get planPriorityNormalValue => 'Normal';

  @override
  String get planPriorityCriticalValue => 'Critical';

  @override
  String get planScheduleDescription =>
      'Set your duration, daily effort, and reminder rhythm all at once.';

  @override
  String get planScheduleDailyMinutesLabel => 'Daily available time';

  @override
  String planScheduleMinutesUnit(int minutes) {
    return '$minutes min';
  }

  @override
  String planScheduleTotalHours(String hours) {
    return 'Total estimated: ${hours}h';
  }

  @override
  String get planScheduleTargetDateUnset => 'Not set';

  @override
  String get planScheduleReminderTime => 'Daily reminder';

  @override
  String get planScheduleStageLabel => 'Current plan stage';

  @override
  String get planScheduleStageSprint => 'Sprint push';

  @override
  String get planScheduleStageDaily => 'Daily execution';

  @override
  String get planScheduleStageReview => 'Review & adjust';

  @override
  String get planScheduleStagePaused => 'Paused';

  @override
  String get planScheduleChipWeekday => 'Weekday push, weekend review';

  @override
  String get planScheduleChipMorning => 'Morning start, evening wrap-up';

  @override
  String get planScheduleChipAfternoon =>
      'Afternoon focus, light evening review';

  @override
  String get planScheduleRhythmLabel => 'Rhythm notes';

  @override
  String get planScheduleRhythmHint =>
      'e.g., Mon-Fri push, Sat review, Sun catch-up';

  @override
  String get planTasksDescription =>
      'This step determines what actions the plan will carry. Existing tasks are for reference; new tasks will be linked to the plan.';

  @override
  String get planTasksBlueprintLabel => 'Task blueprint';

  @override
  String get planTasksBlueprintHint =>
      'e.g., build framework first, push daily progress, then review and fill gaps.';

  @override
  String get planTasksRefExisting => 'Reference existing tasks';

  @override
  String planTasksMinutesDifficulty(int minutes, int difficulty) {
    return '$minutes min · difficulty $difficulty';
  }

  @override
  String get planTasksCopyToPlan => 'Copy to plan';

  @override
  String get planTasksNewTaskLabel => 'New plan task';

  @override
  String get planTasksNewTaskHint => 'e.g., Complete a chapter review';

  @override
  String get planTasksDurationLabel => 'Duration';

  @override
  String get planTasksAddToPlan => 'Add to plan';

  @override
  String get planTasksEmpty => 'No plan tasks yet';

  @override
  String get planGuideScopeLabel => 'Boundaries & notes';

  @override
  String get planGuideScopeHint =>
      'e.g., this plan excludes ad-hoc tasks and focuses only on exam prep; push one main action per day.';

  @override
  String get planGuidePerspectiveLabel => 'Guide perspective';

  @override
  String get planGuideForHuman => 'For myself';

  @override
  String get planGuideForAi => 'For AI';

  @override
  String get planGuideHumanInfo =>
      'The human version is saved as the default execution guide on the plan card, helping you push forward directly.';

  @override
  String get planGuideAiInfo =>
      'The AI version is generated only when needed for Sparkle\'s internal task assistant and is not persisted by default.';

  @override
  String get planGuideHumanTitle => 'Human execution guide';

  @override
  String get planGuideAiTitle => 'AI execution version';

  @override
  String get planGuideGenerating => 'Generating';

  @override
  String get planGuideGenerateHuman => 'Generate human version';

  @override
  String get planGuideGenerateAi => 'Generate AI version';

  @override
  String get planGuideHumanHint =>
      'After generation, you\'ll see the plan\'s main thread, daily rhythm, risk reminders, and today\'s starting action.';

  @override
  String get planGuideAiEmpty =>
      'No AI version yet. Only generated when explicitly needed to avoid wasting tokens.';

  @override
  String get planGuideCopyAi => 'Copy AI version';

  @override
  String planReviewSummary(String planType, int minutes, String hours) {
    return '$planType · $minutes min/day · ${hours}h';
  }

  @override
  String get planReviewEditInfo =>
      'Saving will update the plan description and create new tasks for added drafts.';

  @override
  String get planReviewCreateInfo =>
      'Creating will generate a more complete plan card and create plan tasks.';

  @override
  String get planReviewFinalDescription => 'Final plan description';

  @override
  String get taskExecutionChatAboutStuckPoint =>
      'Chat with Sparkle about this blocker';

  @override
  String get taskExecutionSentToAurora => 'Sent to Aurora';

  @override
  String get taskExecutionStuckPromptIntro =>
      'I\'m stuck on this task and would like to break down the specific blockers with you.';

  @override
  String taskExecutionStuckTaskLabel(String title) {
    return 'Task: $title';
  }

  @override
  String taskExecutionStuckEstimatedTime(int minutes) {
    return 'Estimated: $minutes min';
  }

  @override
  String taskExecutionStuckFocusCue(String cue) {
    return 'Focus cue: $cue';
  }

  @override
  String taskExecutionStuckSteps(String steps) {
    return 'Task steps: $steps';
  }

  @override
  String taskExecutionStuckCriteria(String criteria) {
    return 'Success criteria: $criteria';
  }

  @override
  String taskExecutionStuckSuggestion(String suggestion) {
    return 'Stuck suggestion: $suggestion';
  }

  @override
  String get taskExecutionStuckClarifyPrompt =>
      'Please ask me one key clarifying question, then narrow the next step to something I can start within 5 minutes.';

  @override
  String get taskExecutionStuckTooltip => 'Stuck?';

  @override
  String get taskExecutionStuckLabel => 'Stuck?';

  @override
  String taskExecutionAuroraDiagnosticUnavailable(String error) {
    return 'Aurora diagnostic is temporarily unavailable: $error';
  }

  @override
  String get taskExecutionResetTimer => 'Reset';

  @override
  String get taskExecutionAiHandoffFailed => 'Failed to start AI execution';

  @override
  String get taskExecutionAiCompleted => 'AI completed this execution';

  @override
  String get taskExecutionAiPartial =>
      'AI completed part of the task. Please review.';

  @override
  String get taskExecutionAiFailed => 'AI execution failed';

  @override
  String get taskExecutionAiWaitingApproval =>
      'AI is waiting for your confirmation';

  @override
  String taskExecutionAiHandedOff(String status) {
    return 'Task handed to AI. Status: $status';
  }

  @override
  String get taskExecutionPermissionInsufficientQueued =>
      'Insufficient execution permission. Task has been queued. Retry after permission is granted.';

  @override
  String get taskExecutionAiConfirmFailed => 'Failed to confirm AI result';

  @override
  String get taskExecutionAiResultConfirmed =>
      'AI result confirmed. Task status synced.';

  @override
  String get taskExecutionRejectFailed => 'Failed to retrieve task';

  @override
  String get taskExecutionTaskReturned =>
      'Task returned to you for further processing';

  @override
  String get taskExecutionAiTakingOver => 'AI is taking over this task';

  @override
  String get taskExecutionAiNotStarted => 'AI execution has not started';

  @override
  String taskExecutionAiStatusLabel(String status) {
    return 'AI status: $status';
  }

  @override
  String get taskExecutionSendingToOpenclaw =>
      'Sparkle is sending the task to OpenClaw.';

  @override
  String get taskExecutionDigitalTaskHint =>
      'Digitally executable tasks can be handed off with one tap.';

  @override
  String taskExecutionValidationLabel(int passed, int total) {
    return 'Verified $passed/$total';
  }

  @override
  String taskExecutionResultLabel(String text) {
    return 'Result: $text';
  }

  @override
  String taskExecutionApprovalRequestLabel(int count) {
    return ' · Approval request $count';
  }

  @override
  String taskExecutionGoalWithTrust(String goal, String trust) {
    return 'Goal: $goal · $trust';
  }

  @override
  String taskExecutionResultTrust(String trust) {
    return 'Result trust: $trust';
  }

  @override
  String taskExecutionTemplateLabel(String name) {
    return 'Template: $name';
  }

  @override
  String taskExecutionStrategyLabel(String variant) {
    return 'Strategy: $variant';
  }

  @override
  String taskExecutionNodeLabel(String label) {
    return 'Node: $label';
  }

  @override
  String get taskExecutionAiTakingOverLoading => 'AI taking over...';

  @override
  String get taskExecutionRehandoffToAi => 'Re-hand to AI';

  @override
  String get taskExecutionHandoffToAiAgain => 'Hand to AI again';

  @override
  String get taskExecutionWaitingConfirm => 'Waiting for confirmation';

  @override
  String get taskExecutionAiRunning => 'AI executing';

  @override
  String get taskExecutionHandoffToAi => 'Hand off to AI';

  @override
  String get taskExecutionRecommendedTemplates => 'Recommended templates';

  @override
  String get taskExecutionOpenclawConnectedNoPermission =>
      'OpenClaw is connected but lacks execution permission';

  @override
  String get taskExecutionOpenclawOfflineQueued =>
      'OpenClaw is offline. You can queue the task.';

  @override
  String get taskExecutionOpenclawNotConnected => 'OpenClaw is not connected';

  @override
  String get taskExecutionOpenclawPermissionHint =>
      'Your token can reach the gateway, but execution is blocked by permissions. Queue the task and retry after fixing permissions.';

  @override
  String get taskExecutionOpenclawOfflineHint =>
      'You can continue delegating. The engine will retry automatically when it comes back online.';

  @override
  String get taskExecutionOpenclawNotConnectedHint =>
      'Complete the connection first. The task and chat pages will share the same execution entry.';

  @override
  String get taskExecutionViewAction => 'View';

  @override
  String get taskExecutionConnectAction => 'Connect';

  @override
  String get taskExecutionDismissHint => 'Dismiss';

  @override
  String get taskExecutionMetricConnectedNoPermission =>
      'Connected to gateway, no execution permission';

  @override
  String get taskExecutionMetricConfiguredOffline => 'Configured but offline';

  @override
  String get taskExecutionMetricNotConfigured => 'Not configured';

  @override
  String taskExecutionMetricQueuedTasks(int count) {
    return '$count tasks queued';
  }

  @override
  String get taskExecutionSuggestionFixPermission => 'Fix permissions first';

  @override
  String get taskExecutionSuggestionQueueFirst => 'Queue first, retry later';

  @override
  String get taskExecutionSuggestionConnectFirst =>
      'Connect first, then delegate';

  @override
  String get taskExecutionNudgeCurrentStatus => 'Current status';

  @override
  String get taskExecutionNudgeStatusPermissionIssue =>
      'This device can reach the OpenClaw gateway, but the current authentication lacks execution permission.';

  @override
  String get taskExecutionNudgeStatusOffline =>
      'Connection info is saved, but the engine is temporarily offline.';

  @override
  String get taskExecutionNudgeStatusNotConnected =>
      'This device is not connected to OpenClaw.';

  @override
  String get taskExecutionNudgeWhyThisPrompt => 'Why am I seeing this?';

  @override
  String get taskExecutionNudgeWhyThisPromptValue =>
      'You\'re in a task that supports AI delegation, but the execution entry isn\'t ready yet.';

  @override
  String get taskExecutionNudgeNextAction => 'Next step';

  @override
  String get taskExecutionNudgeNextActionPermissionIssue =>
      'Open the OpenClaw Hub to switch to a token with execution permission, or switch to a paired WebSocket connection; then retry the queue.';

  @override
  String get taskExecutionNudgeNextActionOffline =>
      'Keep queuing tasks, or go to the OpenClaw Hub to restore the connection and retry.';

  @override
  String get taskExecutionNudgeNextActionNotConnected =>
      'Open the OpenClaw Hub to complete the connection, then come back here to delegate.';

  @override
  String get taskExecutionCompletedToday => 'Done for today!';

  @override
  String get taskExecutionCompletionCheckHint =>
      'Check against the success criteria. If it meets them, accept the completion; if not, break it down further.';

  @override
  String get taskExecutionCompletionCriteria => 'Success criteria';

  @override
  String get taskExecutionNoCriteriaHint =>
      'No criteria defined. Judge by the smallest deliverable step you can finish today.';

  @override
  String get taskExecutionCriteriaMatchQuestion => 'Does it meet the criteria?';

  @override
  String get taskExecutionCriteriaNotMet => 'Not yet';

  @override
  String get taskExecutionContinueOrRetryTomorrow =>
      'Keep going, or mark it for tomorrow';

  @override
  String get taskExecutionCriteriaMetComplete => 'Meets criteria, complete';

  @override
  String get taskExecutionRejectReasonInaccurate => 'Inaccurate result';

  @override
  String get taskExecutionRejectReasonIncomplete => 'Incomplete result';

  @override
  String get taskExecutionRejectReasonSafety => 'Safety concern';

  @override
  String get taskExecutionRejectReasonSelfDo => 'I want to do it myself';

  @override
  String get taskExecutionRejectReasonTitle => 'Rejection reason';

  @override
  String get taskExecutionRejectDescription =>
      'Tell Sparkle why this result isn\'t suitable for direct adoption. Future executions will be adjusted based on your feedback.';

  @override
  String get taskExecutionRejectAdditionalNote => 'Additional notes';

  @override
  String get taskExecutionRejectNoteHint =>
      'E.g., missing source, too assertive, I want to keep my own wording';

  @override
  String get taskExecutionRejectConfirm => 'Confirm rejection';

  @override
  String get taskExecutionUserRetrievedTask => 'User retrieved task';

  @override
  String planDetailTaskLoadFailed(Object error) {
    return 'Failed to load tasks: $error';
  }

  @override
  String get planDetailNoExternalTasks =>
      'No unassigned or external tasks available';

  @override
  String get planDetailAddExistingTaskTitle => 'Add existing task to this plan';

  @override
  String get planDetailTaskUnassigned => 'Unassigned';

  @override
  String get planDetailTaskInAnotherPlan => 'Currently in another plan';

  @override
  String get planDetailGroupUnassigned => 'Unassigned tasks';

  @override
  String get planDetailGroupOtherPlans => 'Tasks from other plans';

  @override
  String get planDetailTaskAdded => 'Task added to plan';

  @override
  String planDetailAddTaskFailed(Object error) {
    return 'Add task failed: $error';
  }

  @override
  String planDetailDayLabel(int day) {
    return 'Day $day';
  }

  @override
  String planDetailWeightedProgress(int percent) {
    return 'Weighted progress $percent%';
  }

  @override
  String get planDetailCreatePhaseTitle => 'Create phase';

  @override
  String get planDetailPhaseNameLabel => 'Phase name';

  @override
  String get planDetailPhaseNameHint => 'Foundation / Build / Review';

  @override
  String get planDetailPhaseCreated => 'Phase created';

  @override
  String planDetailCreatePhaseFailed(Object error) {
    return 'Create phase failed: $error';
  }

  @override
  String get planDetailPhaseActivated => 'Phase activated';

  @override
  String planDetailActivatePhaseFailed(Object error) {
    return 'Activate failed: $error';
  }

  @override
  String get planDetailPhaseNeedsFeedback =>
      'This phase needs feedback before advancing';

  @override
  String get planDetailPhaseCompleted => 'Phase completed';

  @override
  String planDetailCompletePhaseFailed(Object error) {
    return 'Complete phase failed: $error';
  }

  @override
  String planDetailPhaseFeedbackTitle(Object title) {
    return 'Phase feedback · $title';
  }

  @override
  String get planDetailPhaseAlignmentQuestion =>
      'How aligned did this phase feel?';

  @override
  String get planDetailPhaseReflectionLabel => 'Reflection';

  @override
  String get planDetailPhaseReflectionHint =>
      'What worked, what failed, what changed?';

  @override
  String get planDetailPhaseBlocked => 'I felt blocked this phase';

  @override
  String get planDetailPhaseLifeChanged => 'My life conditions changed';

  @override
  String get planDetailPhaseRequestReview => 'Request compass review';

  @override
  String get planDetailPhaseActivate => 'Activate';

  @override
  String get planDetailPhaseComplete => 'Complete';

  @override
  String get planDetailPhaseFeedback => 'Feedback';

  @override
  String get planDetailFeedbackSavedWithReview =>
      'Feedback saved, compass review suggested';

  @override
  String get planDetailFeedbackSaved => 'Feedback saved';

  @override
  String planDetailSubmitFeedbackFailed(Object error) {
    return 'Submit feedback failed: $error';
  }

  @override
  String planDetailPhaseStats(
      int progress, int completed, int occurrences, int tasks) {
    return '$progress% · $completed/$occurrences occurrences · $tasks tasks';
  }

  @override
  String get theaterTitle => 'Knowledge Deduction Theater';

  @override
  String get theaterContinuityBanner =>
      'This deduction continues from your previous exploration. You can return to the original conversation anytime to explore paths, risks, and actions.';

  @override
  String theaterShareTopic(Object topic) {
    return 'Deduction topic: $topic';
  }

  @override
  String theaterShareMessage(Object route, Object suggestion, Object topic) {
    return 'I just deduced a learning path in Sparkle: $topic\n$route\n$suggestion';
  }

  @override
  String get theaterShareSuggestion =>
      'First understand the key nodes and risks, then decide how to proceed.';

  @override
  String get theaterRecordActualTitle =>
      'Record actual performance after 7 days';

  @override
  String get theaterRecordActualDesc =>
      'After filling in actual completion rates and mastery, the theater will give you calibration feedback.';

  @override
  String get theaterActualCompletionRate => 'Actual completion rate';

  @override
  String get theaterActualMastery => 'Actual mastery';

  @override
  String get theaterSubmitCalibration => 'Submit calibration';

  @override
  String get theaterNodeDescriptionFallback =>
      'This node is a key knowledge point in the current deduction.';

  @override
  String get theaterNodeCurrentMastery => 'Current mastery';

  @override
  String get theaterNodePredictedMastery => 'Predicted mastery';

  @override
  String get theaterNodeDelta => 'Change';

  @override
  String get theaterNodeRisk => 'Risk';

  @override
  String get theaterNodeRoleInPath => 'Role in current path';

  @override
  String theaterNodeStepLabel(Object dayLabel, Object index) {
    return '$dayLabel · Step $index';
  }

  @override
  String theaterNodeNextAction(Object minutes) {
    return 'Next action: Spend about $minutes minutes on this node first, then proceed to subsequent steps.';
  }

  @override
  String get theaterWhatIfStart => 'Start what-if deduction';

  @override
  String get theaterViewGalaxyRef => 'View galaxy reference';

  @override
  String get theaterNodeNotInWhatIfPath =>
      'This node is not in the current path\'s deductible steps, so what-if analysis cannot be performed directly.';

  @override
  String get theaterNodeNoGalaxyRef =>
      'This node is currently a free node in the theater with no navigable galaxy reference.';

  @override
  String get theaterPromoteNodeFailed =>
      'Failed to add to knowledge galaxy. Please try again later.';

  @override
  String theaterPromoteNodeCreated(Object nodeName) {
    return 'Added 「$nodeName」to the knowledge galaxy. You can continue to refine the node content.';
  }

  @override
  String theaterPromoteNodeFound(Object nodeName) {
    return 'Found 「$nodeName」in the knowledge galaxy. You can continue to refine the node content.';
  }

  @override
  String get theaterGoImprove => 'Go refine';

  @override
  String theaterEdgeStrength(Object strength) {
    return 'Relationship strength $strength%';
  }

  @override
  String get theaterRiskHigh => 'High risk';

  @override
  String get theaterRiskMedium => 'Medium risk';

  @override
  String get theaterRiskLow => 'Low risk';

  @override
  String get theaterRelationPrerequisite => 'Prerequisite';

  @override
  String get theaterRelationExplains => 'Explains';

  @override
  String get theaterRelationSupports => 'Supports';

  @override
  String get theaterRelationContradicts => 'Contradicts';

  @override
  String theaterSelectedNode(Object nodeName) {
    return 'Selected node · $nodeName';
  }

  @override
  String get theaterNodeTapHint =>
      'Tap the node to view detailed deduction information.';

  @override
  String get theaterNodeStatCurrent => 'Current';

  @override
  String get theaterNodeStatPredicted => 'Predicted';

  @override
  String get theaterNodeStatLift => 'Lift';

  @override
  String get theaterNodeStatSource => 'Source';

  @override
  String get theaterComposerEyebrow => 'Deduction Control Panel';

  @override
  String get theaterComposerTitle =>
      'Set a goal, then let AI show you multiple paths';

  @override
  String get theaterComposerSubtitle =>
      'Define the goal first, compare approaches, risks, and daily effort, then decide whether to adopt a path.';

  @override
  String get theaterComposerCurrentTarget => 'Current target';

  @override
  String get theaterComposerWaitingInput => 'Waiting for input';

  @override
  String get theaterComposerRecommendedEntry => 'Recommended entry';

  @override
  String get theaterComposerInputPrompt => 'Start after input';

  @override
  String get theaterComposerOutput => 'Output';

  @override
  String get theaterComposerOutputDesc => 'Paths + Risks + Checkpoints';

  @override
  String get theaterComposerLoading => 'Deducing...';

  @override
  String get theaterComposerStart => 'Start deduction';

  @override
  String theaterComposerTrySuggestion(Object topic) {
    return 'Try $topic';
  }

  @override
  String get theaterComposerHint =>
      'e.g., Master eigenvalues in linear algebra within two weeks';

  @override
  String get theaterComposerGenerating => 'Generate';

  @override
  String get theaterTopBarAdjustTarget => 'Adjust target';

  @override
  String get theaterTopBarShare => 'Share deduction';

  @override
  String get theaterTopBarNoGalaxyRef => 'No galaxy reference nodes available';

  @override
  String get theaterTopBarViewGalaxy => 'View knowledge galaxy';

  @override
  String theaterTopBarTarget(Object name) {
    return 'Target · $name';
  }

  @override
  String theaterTopBarPath(Object title) {
    return 'Path · $title';
  }

  @override
  String theaterTopBarMode(Object mode) {
    return 'Mode · $mode';
  }

  @override
  String theaterTopBarRefMap(Object count) {
    return 'Reference map $count';
  }

  @override
  String get theaterTopBarFreeForm => 'Free-form deduction';

  @override
  String theaterTopBarMastery(Object value) {
    return 'Mastery $value%';
  }

  @override
  String get theaterSettingsTitle => 'Adjust deduction target';

  @override
  String get theaterSettingsSubtitle =>
      'Reset the target and starting point here. Collapse to return full stage space to the graph and discussion flow.';

  @override
  String get theaterSettingsContinuity =>
      'This deduction still carries forward your previous conversation context.';

  @override
  String theaterSettingsCurrentTarget(Object name) {
    return 'Current target: $name';
  }

  @override
  String get theaterSettingsLabel => 'Reset deduction target';

  @override
  String get theaterSettingsHint =>
      'e.g., Master eigenvalues in linear algebra within two weeks';

  @override
  String get theaterSettingsGenerate => 'Generate new deduction';

  @override
  String get theaterSettingsSuggestions => 'Suggested starting points';

  @override
  String get theaterTabGraph => 'Graph';

  @override
  String get theaterTabPaths => 'Paths';

  @override
  String get theaterTabDiscussion => 'Discussion';

  @override
  String get theaterTabCalibration => 'Calibration';

  @override
  String get theaterIntroChangeTarget => 'Change target';

  @override
  String get theaterIntroTitle =>
      'Pick a goal, AI will show you multiple paths';

  @override
  String get theaterIntroSteps =>
      '1. Choose a goal\n2. AI deduces learning paths\n3. Adopt the best plan and sync to Sprint';

  @override
  String get theaterIntroStartFirst => 'Start your first deduction';

  @override
  String get theaterIntroLastSnapshot => 'Last deduction';

  @override
  String get theaterIntroSuggestions =>
      'These topics are a good starting point';

  @override
  String get theaterEmptyTitle => 'No adoptable paths generated yet';

  @override
  String get theaterEmptyMessage =>
      'The system has analyzed the topic but couldn\'t converge on executable routes. Try a more specific goal or try again later.';

  @override
  String theaterGraphRecommended(Object title) {
    return 'Recommended path · $title';
  }

  @override
  String theaterGraphEstimatedMastery(Object value) {
    return 'Estimated mastery $value%';
  }

  @override
  String theaterGraphRisk(Object risk) {
    return 'Risk · $risk';
  }

  @override
  String theaterGraphMode(Object mode) {
    return 'Mode · $mode';
  }

  @override
  String theaterGraphRefCount(Object count) {
    return 'Reference count $count';
  }

  @override
  String get theaterGraphPendingEntry => 'Pending graph entry';

  @override
  String theaterGraphNodeCount(Object count) {
    return '$count nodes';
  }

  @override
  String get theaterGraphMainStage => 'Relationship graph main stage';

  @override
  String get theaterGraphWithGalaxy => 'With galaxy references';

  @override
  String get theaterGraphStandalone => 'Standalone graph';

  @override
  String get theaterGraphInstructions =>
      'Drag with one finger to pan, pinch to zoom, double-tap to reset. Tap a node to view details and add to the knowledge galaxy.';

  @override
  String get theaterCalibrationTitle => 'Calibration & Execution';

  @override
  String get theaterCalibrationSubtitle =>
      'Turn deductions into plans, snapshots, and real feedback to close the loop.';

  @override
  String get theaterRetry => 'Retry';

  @override
  String get theaterGotIt => 'Got it';

  @override
  String get theaterSemanticMatchTitle => 'Free nodes and galaxy references';

  @override
  String theaterSemanticMatchItem(Object freeform, Object galaxy) {
    return '$freeform references $galaxy';
  }

  @override
  String get theaterLoadingTitle => 'AI is building your deduction...';

  @override
  String get theaterLoadingSubtitle =>
      'The graph, paths, and risk assessment are completed in stages. You can track progress as it advances.';

  @override
  String get theaterStageBuildGraph => 'Building knowledge graph';

  @override
  String get theaterStageAnalyzePaths => 'Analyzing learning paths';

  @override
  String get theaterStageGenerateRisk => 'Generating risk predictions';

  @override
  String get theaterStagePrepare => 'Finalizing deduction';

  @override
  String get theaterTimelineTitle => 'Deduction timeline';

  @override
  String get theaterTimelineSubtitle =>
      'Drag to explore predicted progress by day and compare baseline vs. what-if branches.';

  @override
  String get theaterTimelinePause => 'Pause playback';

  @override
  String get theaterTimelineAutoPlay => 'Auto-play';

  @override
  String get theaterTimelineReset => 'Go to start';

  @override
  String get theaterTimelineCurrentPhase => 'Current phase';

  @override
  String get theaterTimelineWaitingPath => 'Waiting for path generation';

  @override
  String get theaterTimelineBaseline => 'Baseline prediction';

  @override
  String get theaterTimelineDiscussionHere => 'Discussion at this point';

  @override
  String get theaterTimelineMastery => 'Current predicted mastery';

  @override
  String get theaterTimelineCompletion => 'Current predicted completion';

  @override
  String theaterTimelinePhaseWithSteps(
      Object compare, Object label, Object step) {
    return 'Current phase: $label · $step · $compare';
  }

  @override
  String get theaterTimelineWaitingDeduction => 'Waiting for deduction';

  @override
  String get theaterRouteList => 'List';

  @override
  String get theaterRouteCompare => 'Compare';

  @override
  String get theaterRouteComparisonTitle => 'Path comparison';

  @override
  String theaterRouteAdoptedPlan(Object planName) {
    return 'Plan created: $planName';
  }

  @override
  String theaterRouteFirstWeekTasks(Object tasks) {
    return 'First week tasks: $tasks';
  }

  @override
  String get theaterRouteRiskControllable => 'Controllable overall';

  @override
  String get theaterRouteRiskPacing => 'Watch the pacing';

  @override
  String theaterRouteEstimatedRange(Object high, Object low) {
    return 'Estimated $low-$high%';
  }

  @override
  String get theaterRouteDataQualityLow => 'Rough estimate';

  @override
  String get theaterRouteDataQualityMedium => 'Based on limited data';

  @override
  String theaterRouteDataQualityHigh(Object score) {
    return 'Data sufficiency $score%';
  }

  @override
  String get theaterRouteDataQualityFallback => 'Data reference';

  @override
  String get theaterRouteDataNoteLow =>
      'No real learning records for this topic yet. Treat range estimates as reference, not precise predictions.';

  @override
  String get theaterRouteDataNoteMedium =>
      'Only partial graph and calibration data available. Percentages still need more observation.';

  @override
  String get theaterRouteModeAnchored => 'Graph anchored';

  @override
  String get theaterRouteModeHybrid => 'Smart hybrid';

  @override
  String get theaterRouteModeFree => 'Free-form deduction';

  @override
  String get theaterRouteModeDeducing => 'Deducing';

  @override
  String get theaterNodeGalaxySyncing => 'Syncing...';

  @override
  String get theaterNodeOpenGalaxy => 'Open knowledge galaxy';

  @override
  String get theaterNodeAddToGalaxy => 'Add to knowledge galaxy';

  @override
  String get theaterNodeSourceExplicit => 'Galaxy node';

  @override
  String get theaterNodeSourceHybrid => 'Reference mapping';

  @override
  String get theaterNodeSourcePending => 'Pending node';

  @override
  String get theaterNodeSourceFree => 'Free node';

  @override
  String get theaterNodeBannerOpenGalaxy =>
      'This node already corresponds to an official knowledge galaxy node. Open it directly to continue expanding.';

  @override
  String get theaterNodeBannerHasMapping =>
      'This free node already has a galaxy reference. Adding will use the unified creation flow.';

  @override
  String get theaterNodeBannerFreeform =>
      'This free node is not yet in the graph. Adding will auto-complete domain, position, relations, and unlock status.';

  @override
  String get theaterRouteRecommended => 'Recommended';

  @override
  String get theaterRouteAdopting => 'Adopting';

  @override
  String get theaterRouteAdopt => 'Adopt this path';

  @override
  String get theaterRouteSimulate => 'Take to simulation';

  @override
  String theaterRouteCompletion(Object value) {
    return 'Completion $value';
  }

  @override
  String theaterRouteMasteryLabel(Object value) {
    return 'Mastery $value';
  }

  @override
  String theaterRouteDailyMinutes(Object minutes) {
    return '$minutes min/day';
  }

  @override
  String theaterRouteRiskCount(Object count) {
    return '$count risks';
  }

  @override
  String theaterRouteScore(Object score) {
    return 'Score $score';
  }

  @override
  String theaterRouteRangePrediction(Object completionHigh,
      Object completionLow, Object masteryHigh, Object masteryLow) {
    return 'Range prediction: completion $completionLow%-$completionHigh%, mastery $masteryLow%-$masteryHigh%';
  }

  @override
  String get theaterRouteRecommendedBaseline => 'Recommended baseline';

  @override
  String get theaterRouteCompletionRate => 'Completion rate';

  @override
  String get theaterRouteMasteryRate => 'Mastery';

  @override
  String get theaterRouteDailyTime => 'Daily time';

  @override
  String get theaterRouteRiskLevel => 'Risk count';

  @override
  String get theaterRouteOverallScore => 'Overall score';

  @override
  String get theaterRouteDataNote => 'Data note';

  @override
  String theaterRouteCompletionRange(Object high, Object low) {
    return 'Completion range $low%-$high%';
  }

  @override
  String theaterRouteMasteryRange(Object high, Object low) {
    return 'Mastery range $low%-$high%';
  }

  @override
  String get theaterRouteSimulateFromCurrent => 'Take to simulation';

  @override
  String get theaterRouteSimulateAfterSwitch => 'Switch then simulate';

  @override
  String get theaterRouteSwitchToThis => 'Switch to this path';

  @override
  String theaterRouteStepMinutes(Object dayLabel, Object minutes) {
    return '$dayLabel · $minutes min';
  }

  @override
  String get theaterDismissTooltip => 'Dismiss';

  @override
  String get theaterCompactComparisonTitle => 'Path comparison';

  @override
  String theaterCompactComparisonSummary(Object summary) {
    return 'Comparison path: $summary';
  }

  @override
  String theaterCompactComparisonCurrent(Object title) {
    return 'Current · $title';
  }

  @override
  String theaterCompactComparisonMastery(Object value) {
    return 'Mastery $value%';
  }

  @override
  String theaterCompactComparisonTime(Object minutes) {
    return 'Time $minutes min/day';
  }

  @override
  String theaterCompactComparisonAlt(Object title) {
    return 'Compare · $title';
  }

  @override
  String get theaterCompactOpenDetail => 'Open path details';

  @override
  String theaterCompactFallbackSingle(Object name) {
    return 'Focus on $name first.';
  }

  @override
  String theaterCompactFallbackMulti(Object first, Object last) {
    return 'Start with $first, then move to $last.';
  }

  @override
  String get theaterComparisonTitle => 'Path comparison';

  @override
  String get theaterComparisonSubtitle =>
      'Compare your current plan with a representative path to better decide whether to play it safe or go faster.';

  @override
  String get theaterComparisonMetric => 'Metric';

  @override
  String get theaterComparisonEstimatedMastery => 'Estimated mastery';

  @override
  String get theaterComparisonTimeInvestment => 'Time investment';

  @override
  String get theaterComparisonRiskLevel => 'Risk level';

  @override
  String get theaterComparisonRiskLow => 'Low';

  @override
  String get theaterComparisonRiskMediumHigh => 'Medium-high';

  @override
  String get theaterComparisonRiskMedium => 'Medium';

  @override
  String get theaterBranchDeltaTitle => 'What-if branch comparison';

  @override
  String get theaterBranchDeltaPath => 'Branch path';

  @override
  String get theaterBranchDeltaWhatIf => 'What-if deduction';

  @override
  String get theaterWhatIfTitle => 'What-if sandbox';

  @override
  String get theaterWhatIfSubtitle =>
      'Select nodes to skip, preview the impact, then generate the full what-if result.';

  @override
  String get theaterWhatIfPreviewTitle => 'Impact preview';

  @override
  String get theaterWhatIfPreviewMastery => 'Mastery';

  @override
  String get theaterWhatIfPreviewCompletion => 'Completion';

  @override
  String get theaterWhatIfNoNodesSelected =>
      'No nodes marked to skip. Keeping the original path.';

  @override
  String theaterWhatIfNodesSkipped(Object nodes) {
    return 'You marked to skip $nodes.';
  }

  @override
  String get theaterWhatIfSelectFirst => 'Select a node first';

  @override
  String get theaterWhatIfGenerateFull => 'Generate full what-if result';

  @override
  String theaterWhatIfOriginal(Object original) {
    return 'Original $original';
  }

  @override
  String theaterWhatIfAdjusted(Object adjusted) {
    return 'Adjusted $adjusted';
  }

  @override
  String theaterWhatIfRemainingPath(Object path) {
    return 'Remaining branch path: $path';
  }

  @override
  String get theaterDiscussionTitle => 'Expert roundtable';

  @override
  String get theaterSnapshotSaving => 'Saving';

  @override
  String get theaterSnapshotSave => 'Save current snapshot';

  @override
  String get theaterSnapshotTitle => 'Save current snapshot';

  @override
  String get theaterSnapshotNoSnapshot =>
      'Save the current deduction to review later.';

  @override
  String theaterSnapshotSaved(Object title) {
    return 'Saved: $title';
  }

  @override
  String get theaterAccuracyTitle => 'Prediction calibration';

  @override
  String get theaterAccuracyWithinRange =>
      'The actual result fell within the prediction range. Current model coverage is on target.';

  @override
  String get theaterAccuracyOutsideRange =>
      'The actual result fell outside the prediction range. The system will use this deviation to calibrate future predictions.';

  @override
  String theaterAccuracyDueDate(Object date) {
    return 'Suggested fill date: $date';
  }

  @override
  String get theaterAccuracyRecordActual => 'Record actual performance';

  @override
  String theaterAccuracySampleCount(Object count) {
    return 'Samples $count';
  }

  @override
  String theaterAccuracyAvgScore(Object score) {
    return 'Average accuracy $score%';
  }

  @override
  String theaterAccuracyConfidenceScore(Object score) {
    return 'Data sufficiency $score%';
  }

  @override
  String theaterAccuracyCoverageRate(Object rate) {
    return 'Range coverage $rate%';
  }

  @override
  String get theaterAccuracyScoreNote =>
      'Data sufficiency reflects the volume of data and calibration count, not prediction accuracy.';

  @override
  String get theaterAccuracyNoSamples =>
      'No historical fill samples yet. Current predictions prioritize ranges over absolute values.';

  @override
  String theaterAccuracyHistoryBias(Object completionBias, Object masteryBias) {
    return 'Historical bias: completion $completionBias%, mastery $masteryBias%.';
  }

  @override
  String get theaterAdoptionSynced => 'Synced to your Sprint';

  @override
  String get theaterAdoptionFirstWeekTasks => 'First week tasks';

  @override
  String theaterAdoptionCheckpoints(Object dates) {
    return 'Checkpoints: $dates';
  }

  @override
  String get theaterAdoptionViewPlan => 'View plan';

  @override
  String get theaterAdoptionContinueExploring => 'Continue exploring';

  @override
  String get planCreateEditingGrowth => 'Edit Growth Plan';

  @override
  String get planCreateEditingSprint => 'Edit Sprint Plan';

  @override
  String get planCreateSavePlan => 'Save Plan';

  @override
  String get planCreateStepPositioning => 'Plan Positioning';

  @override
  String get planCreateStepTimeStructure => 'Time Structure';

  @override
  String get planCreateStepTaskBlueprint => 'Task Blueprint';

  @override
  String get planCreateStepBoundariesGuide => 'Boundaries & Guide';

  @override
  String get planCreateStepReviewConfirm => 'Review & Confirm';

  @override
  String get planCreateBasicsSubtitle =>
      'First, define this as a real plan card, not just a regular task.';

  @override
  String get planCreateNameHint =>
      'e.g., 6-week speaking boost / Midterm sprint wrap-up';

  @override
  String get planCreateSubjectLabel => 'Subject';

  @override
  String get planCreateSubjectHint =>
      'e.g., English, Flutter, Math, Research reading...';

  @override
  String get planCreateGrowthGoalLabel => 'Long-term Goal';

  @override
  String get planCreateSprintGoalLabel => 'Sprint Goal';

  @override
  String get planCreateGrowthGoalHint =>
      'Describe what abilities, habits, or outcomes this growth plan aims to build.';

  @override
  String get planCreateSprintGoalHint =>
      'Describe the sprint\'s target, acceptance criteria, and the main focus.';

  @override
  String get planCreateGoalRequired =>
      'Please write the goal for this plan card';

  @override
  String get planCreateScheduleSubtitle =>
      'Set duration, daily input, and reminder rhythm all at once.';

  @override
  String get planCreateDailyMinutesLabel => 'Daily available time';

  @override
  String planCreateTotalEstimatedHours(Object hours) {
    return 'Total estimated $hours hours';
  }

  @override
  String get planCreateDailyReminderTime => 'Daily reminder time';

  @override
  String get planCreatePlanStageLabel => 'Current stage';

  @override
  String get planCreateStageSprint => 'Sprint Push';

  @override
  String get planCreateStageDaily => 'Daily Execution';

  @override
  String get planCreateStageReview => 'Review & Tune';

  @override
  String get planCreateStagePaused => 'Temporarily Paused';

  @override
  String get planCreateScheduleChipWorkday => 'Weekday push, weekend review';

  @override
  String get planCreateScheduleChipMorning => 'Morning start, evening wrap';

  @override
  String get planCreateScheduleChipAfternoon =>
      'Afternoon focus, light night review';

  @override
  String get planCreateScheduleLabel => 'Rhythm description';

  @override
  String get planCreateScheduleHint =>
      'e.g., Mon-Fri push forward, Sat review, Sun fill gaps';

  @override
  String get planCreateTasksSubtitle =>
      'This step determines what actions the plan will carry. Existing tasks are references; new tasks truly belong to the plan.';

  @override
  String get planCreateTaskBlueprintLabel => 'Task blueprint';

  @override
  String get planCreateTaskBlueprintHint =>
      'e.g., Build the framework first, then push the main line daily, review and fill gaps at the end.';

  @override
  String get planCreateReferenceExistingTasks => 'Reference existing tasks';

  @override
  String get planCreateCopyToPlan => 'Copy to plan';

  @override
  String get planCreateNewTaskLabel => 'New plan task';

  @override
  String get planCreateNewTaskHint =>
      'e.g., Complete one round of chapter review';

  @override
  String get planCreateDurationLabel => 'Duration';

  @override
  String get planCreateDifficultyLabel => 'Difficulty';

  @override
  String get planCreateAddTaskToPlan => 'Add to plan tasks';

  @override
  String get planCreateNoTasks => 'No plan tasks yet';

  @override
  String get planCreateScopeLabel => 'Plan boundaries & notes';

  @override
  String get planCreateScopeHint =>
      'e.g., This plan does not handle ad-hoc tasks, only follows the exam mainline; push only one mainline action per day.';

  @override
  String get planCreateGuidePerspective => 'Task guide perspective';

  @override
  String get planCreateGuideForSelf => 'For myself';

  @override
  String get planCreateGuideForAi => 'For AI';

  @override
  String get planCreateGuideHumanDescription =>
      'The human version is saved by default as the execution guide on the plan card to help you push forward directly.';

  @override
  String get planCreateGuideAiDescription =>
      'The AI version is only generated when needed for Sparkle\'s internal task assistant, not persisted by default.';

  @override
  String get planCreateGuideHumanTitle => 'Human execution guide';

  @override
  String get planCreateGuideAiTitle => 'AI execution version';

  @override
  String get planCreateGenerateHumanGuide => 'Generate human version';

  @override
  String get planCreateGenerateAiGuide => 'Generate AI version';

  @override
  String get planCreateGuideHint =>
      'After generation, you\'ll see the main push thread, daily rhythm, risk reminders, and today\'s starting action here.';

  @override
  String get planCreateAiGuideEmpty =>
      'No AI version yet. Only generate when needed to avoid unnecessary token usage.';

  @override
  String get planCreateCopyAiGuide => 'Copy AI version';

  @override
  String get planCreateAiGuideCopied => 'AI version copied';

  @override
  String planCreateReviewSummary(
      Object dailyMinutes, Object hours, Object type) {
    return '$type · $dailyMinutes min/day · $hours hours';
  }

  @override
  String get planCreateReviewEditDescription =>
      'Saving will update the plan description and create new plan tasks for added drafts.';

  @override
  String get planCreateReviewCreateDescription =>
      'Creating will generate a more complete plan card and sync create plan tasks.';

  @override
  String get planCreateFinalDescription => 'Final written plan description';

  @override
  String planCreateMinutes(Object value) {
    return '$value min';
  }

  @override
  String planCreateTaskSubtitle(Object difficulty, Object minutes) {
    return '$minutes min · Difficulty $difficulty';
  }

  @override
  String get predictedIntentTitle => 'System Prediction';

  @override
  String get predictedIntentCollapsedTitle => 'System Prediction Collapsed';

  @override
  String get predictedIntentCollapsedExpand =>
      'Expand it again whenever you want to review the recommendation.';

  @override
  String get predictedIntentCollapsedUpdated => 'Last updated';

  @override
  String get predictedIntentSummary =>
      'Based on your profile, the last 24 hours, and task rhythm';

  @override
  String get predictedIntentSuggestedCont => 'Suggested Continuation';

  @override
  String get predictedIntentWaiting =>
      'The prediction is ready and waiting for a follow-up prompt.';

  @override
  String predictedIntentConfidence(int percent) {
    return 'Confidence $percent%';
  }

  @override
  String get predictedIntentWhy => 'Why the system predicts this';

  @override
  String get predictedIntentContinuing => 'Continuing...';

  @override
  String get predictedIntentContinue => 'Continue With This';

  @override
  String get predictedIntentError =>
      'Something went wrong while continuing. Please try again.';

  @override
  String get predictedActionResumePriority => 'Resume Priority Task';

  @override
  String get predictedActionStudyPlan => 'Build Study Plan';

  @override
  String get predictedActionDiagnose => 'Diagnose Issue';

  @override
  String get predictedActionCreateTask => 'Turn Into Task';

  @override
  String get predictedActionInstantResult => 'Instant Result';

  @override
  String get predictedActionReviewProgress => 'Review Progress';

  @override
  String get predictedActionPlanNext => 'Plan Next Step';

  @override
  String get predictedActionReflection => 'Quick Reflection';

  @override
  String get predictedActionDefault => 'Predicted Intent';

  @override
  String get predictedWindowNow => 'Right Now';

  @override
  String get predictedWindow30m => 'Next 30 Minutes';

  @override
  String get predictedWindow1h => 'Next Hour';

  @override
  String get predictedWindow2h => 'Next 2 Hours';

  @override
  String get predictedWindow6h => 'Next 6 Hours';

  @override
  String get predictedWindowToday => 'Later Today';

  @override
  String get predictedSourceLongRange => 'Long-Range Forecast';

  @override
  String get predictedSourceRules => 'Rules Fallback';

  @override
  String get predictedFreshnessJustNow => 'just now';

  @override
  String predictedFreshnessMinutes(int count) {
    return '$count min ago';
  }

  @override
  String predictedFreshnessHours(int count) {
    return '$count hr ago';
  }

  @override
  String predictedFreshnessDays(int count) {
    return '$count d ago';
  }

  @override
  String get predictedCategoryPrefTitle => 'Recent same-category signal';

  @override
  String predictedCategoryPrefHint(String category, String tool) {
    return 'Inside $category, recent results have more often favored \"$tool\" first.';
  }

  @override
  String get predictedCategoryPrefCaveat =>
      'Based only on recent results inside this request category. It does not mean Sparkle understands your whole workflow.';

  @override
  String get predictedCategoryPlan => 'planning requests';

  @override
  String get predictedCategoryTask => 'task requests';

  @override
  String get predictedCategoryFocus => 'focus-support requests';

  @override
  String get predictedCategoryGrowth => 'growth requests';

  @override
  String get predictedCategoryQuery => 'query requests';

  @override
  String get predictedCategoryKnowledge => 'knowledge requests';

  @override
  String get predictedCategoryReview => 'review requests';

  @override
  String get predictedCategoryResearch => 'research requests';

  @override
  String get predictedCategoryMemory => 'memory requests';

  @override
  String get predictedCategoryCognitive => 'cognitive requests';

  @override
  String get predictedCategoryDefault => 'similar requests';

  @override
  String get predictedToolCreatePlan => 'Create Plan';

  @override
  String get predictedToolGenerateTasks => 'Expand Plan Steps';

  @override
  String get predictedToolCreateTask => 'Create Task';

  @override
  String get predictedToolListTasks => 'List Tasks';

  @override
  String get predictedToolUpdateTask => 'Update Task';

  @override
  String get predictedToolQueryKnowledge => 'Query Knowledge';

  @override
  String get predictedToolExplainConcept => 'Explain Concept';

  @override
  String get predictedToolReviewProgress => 'Review Progress';

  @override
  String get predictedToolGenerateSummary => 'Generate Summary';

  @override
  String get predictedToolSuggestSchedule => 'Suggest Schedule';

  @override
  String get examSprintHighFreqCoverage => 'High-Freq Coverage';

  @override
  String get examSprintMistakeRepair => 'Mistake Repair';

  @override
  String get examSprintStudyStreak => 'Study Streak';

  @override
  String examSprintStreakDays(int days) {
    return '$days d';
  }

  @override
  String get examSprintKeepRhythm => 'Keep the rhythm';

  @override
  String examSprintHighYieldWeak(String topics) {
    return 'High-yield weak spots: $topics';
  }

  @override
  String get examSprintNoTasksToday => 'No sprint tasks scheduled today.';

  @override
  String get examSprintExamDayReady => 'Exam Day · You\'re Ready 🎓';

  @override
  String get examSprintExamTips => 'Exam Tips';

  @override
  String get examSprintRecordResult => 'Record Exam Result';

  @override
  String get examSprintDashboardTitle => 'Exam Sprint Dashboard';

  @override
  String get examSprintModeHighScore => 'High Score';

  @override
  String get examSprintModeHold => 'Hold';

  @override
  String get examSprintModePass => 'Pass';

  @override
  String get examSprintModeDefault => 'Sprint';

  @override
  String get examSprintExamDay => 'Exam day';

  @override
  String examSprintCountdown(int days) {
    return '$days days until exam';
  }

  @override
  String examSprintTodayTasks(int completed, int total) {
    return 'Today: $completed/$total tasks';
  }

  @override
  String examSprintDaysLeft(int days) {
    return '$days days left';
  }

  @override
  String examSprintTodayDone(int completed, int total) {
    return 'Today $completed/$total done';
  }

  @override
  String get examSprintTodaySprintTasks => 'Today Sprint Tasks';

  @override
  String get examSprintHideLater => 'Hide later days';

  @override
  String examSprintShowLater(int count) {
    return 'Show next $count days';
  }

  @override
  String examSprintDayIndex(int index) {
    return 'Day $index';
  }

  @override
  String examSprintDateFormat(int month, int day) {
    return '$month/$day';
  }

  @override
  String get examSprintNoSprintTasks => 'No sprint tasks yet';

  @override
  String examSprintMinLabel(int minutes, String status) {
    return '$minutes min · $status';
  }

  @override
  String get examSprintStatusDone => 'Done';

  @override
  String get examSprintStatusInProgress => 'In progress';

  @override
  String get examSprintStatusPending => 'Pending';

  @override
  String get insightHubTitle => 'Learning Insights';

  @override
  String insightHubRecommendedSeeds(int count) {
    return '$count recommended scenarios ready to simulate.';
  }

  @override
  String get insightHubFallbackSummary =>
      'Simulations, what-ifs, and reports — now in one lighter learning flow.';

  @override
  String get insightHubSimulation => 'Learning Simulation';

  @override
  String get insightHubTheater => 'Deduction Theater';

  @override
  String get insightHubReport => 'Learning Report';

  @override
  String get insightHubEnterOverview => 'Enter Insight Overview';

  @override
  String get insightHubCompactSimulation => 'Simulation';

  @override
  String get insightHubCompactTheater => 'Theater';

  @override
  String get insightHubCompactReport => 'Report';

  @override
  String get insightHubRefreshWarning =>
      'Some insight data hasn\'t refreshed yet. Existing content will be shown.';

  @override
  String insightHubSeedsToExplore(int count) {
    return '$count scenarios to explore';
  }

  @override
  String get insightHubCompactFallback =>
      'Simulations, what-ifs, and reports now in one card';

  @override
  String get insightHubNoRecentTheater => 'No recent theater';

  @override
  String get insightHubContinueLastTheater => 'Continue last theater';

  @override
  String insightHubContinueTopic(String topic) {
    return 'Continue $topic';
  }

  @override
  String get insightHubContinueLastSimulation => 'Continue last simulation';

  @override
  String insightHubRecommendedSeedsCount(int count) {
    return '$count scenarios';
  }

  @override
  String insightHubContinueSession(String topic) {
    return 'Continue $topic';
  }

  @override
  String get insightHubStartSimulation => 'Start a new simulation';

  @override
  String get insightHubNoRecentReport => 'No recent report';

  @override
  String insightHubMasteryPercent(int percent) {
    return 'Mastery $percent%';
  }

  @override
  String get insightHubRefreshFailed =>
      'Some insight content failed to refresh. Showing existing content.';

  @override
  String get insightHubRetry => 'Retry';

  @override
  String get memoryPanel => 'Memory Panel';

  @override
  String get memoryPanelAdjust => 'Adjust';

  @override
  String get memoryPanelAiAutoMemories => 'AI Auto Memories';

  @override
  String get memoryPanelAiInferredDescription =>
      'AI inferred from chat, for display only, not used in downstream decisions.';

  @override
  String get memoryPanelClearFilter => 'Clear Filter';

  @override
  String get memoryPanelCommitmentDismissed => 'Commitment dismissed';

  @override
  String memoryPanelConfidenceValue(String value) {
    return 'Confidence $value';
  }

  @override
  String memoryPanelConflictFailed(String error) {
    return 'Conflict resolution failed: $error';
  }

  @override
  String get memoryPanelConflictResolvedA => 'Resolved with candidate A';

  @override
  String get memoryPanelConflictResolvedB => 'Resolved with candidate B';

  @override
  String get memoryPanelConflictResolvedNone => 'Conflict candidates revoked';

  @override
  String memoryPanelCorrectionCount(int count) {
    return 'Corrections $count';
  }

  @override
  String get memoryPanelDate => 'Date';

  @override
  String memoryPanelDeviationsDetected(int count) {
    return '$count deviations detected';
  }

  @override
  String get memoryPanelDimCompletionRate => 'Completion Rate';

  @override
  String get memoryPanelDimEngagement => 'Engagement';

  @override
  String get memoryPanelDimMood => 'Mood';

  @override
  String get memoryPanelDimPace => 'Pace';

  @override
  String get memoryPanelDimPlanAdherence => 'Plan Adherence';

  @override
  String memoryPanelDismissFailed(String error) {
    return 'Dismiss failed: $error';
  }

  @override
  String get memoryPanelEmptyDescription =>
      'Start by chatting about your goals, preferences, or recent learning activities so the system can organize long-term memories here.';

  @override
  String get memoryPanelEmptyFilterDescription =>
      'Try clearing filters to see all organized memories.';

  @override
  String get memoryPanelEmptyFilterTitle => 'No matching memories';

  @override
  String get memoryPanelEmptyTitle => 'Memory panel is empty';

  @override
  String get memoryPanelEvidenceAll => 'All Evidence';

  @override
  String get memoryPanelEvidenceMissing => 'Missing';

  @override
  String get memoryPanelEvidenceOk => 'OK';

  @override
  String get memoryPanelEvidenceRedacted => 'Redacted';

  @override
  String get memoryPanelForesightHint => 'Foresight Hint';

  @override
  String memoryPanelImportanceValue(String value) {
    return 'Importance $value';
  }

  @override
  String memoryPanelItemCount(int count) {
    return '$count items';
  }

  @override
  String memoryPanelLoadFailed(String error) {
    return 'Memory panel load failed: $error';
  }

  @override
  String memoryPanelMarkFailed(String error) {
    return 'Mark failed: $error';
  }

  @override
  String get memoryPanelMarkedComplete => 'Marked as complete';

  @override
  String get memoryPanelMetricsNone => 'Metrics: -';

  @override
  String get memoryPanelNotUpdated => 'Not updated';

  @override
  String get memoryPanelRecentScenes => 'Recent Scenes';

  @override
  String get memoryPanelRevoke => 'Revoke';

  @override
  String memoryPanelRevokeFailed(String error) {
    return 'Revoke failed: $error';
  }

  @override
  String get memoryPanelRevokeThis => 'Revoke This';

  @override
  String get memoryPanelRevokedAutoMemory => 'Auto memory revoked';

  @override
  String get memoryPanelRevoking => 'Revoking...';

  @override
  String memoryPanelSceneMemories(String time, int count) {
    return '$time · $count memories';
  }

  @override
  String get memoryPanelUnavailable => 'Memory panel unavailable';

  @override
  String memoryPanelValidUntil(String policy) {
    return 'Valid until $policy';
  }

  @override
  String get theaterComposerDeducing => 'Deducing';

  @override
  String theaterWhatIfCombinedResult(
      String originalMastery,
      String originalCompletion,
      String predictedMastery,
      String predictedCompletion) {
    return 'Original $originalMastery% / $originalCompletion%  →  Adjusted $predictedMastery% / $predictedCompletion%';
  }

  @override
  String theaterAccuracyPredictedActual(String predictedCompletion,
      String predictedMastery, String actualCompletion, String actualMastery) {
    return 'Predicted $predictedCompletion% / $predictedMastery%, Actual $actualCompletion% / $actualMastery%';
  }

  @override
  String theaterPerDayUnit(String minutes) {
    return '$minutes min/day';
  }

  @override
  String get simulationTitle => 'Scenario Simulation';

  @override
  String get simulationCurrentSimulation => 'Current Simulation';

  @override
  String get simulationBackToTheater => 'Back to Theater';

  @override
  String get simulationRunning => 'Simulating...';

  @override
  String get simulationStartSimulation => 'Start This Simulation';

  @override
  String get simulationAwaitingInput => 'Awaiting Input';

  @override
  String get simulationClearTopic => 'Clear Topic';

  @override
  String get simulationRecommendedScenarios => 'Recommended Scenarios';

  @override
  String get simulationGenerate => 'Generate';

  @override
  String get simulationRefresh => 'Refresh';

  @override
  String get simulationStartSimButton => 'Start Simulation';

  @override
  String get simulationGoToTheater => 'Go to Theater';

  @override
  String get simulationContinueSim => 'Continue Simulation';

  @override
  String get simulationPauseSim => 'Pause Simulation';

  @override
  String get simulationCollapseInsight => 'Collapse Insight';

  @override
  String get simulationViewInsight => 'View Insight';

  @override
  String get simulationCollapseSettings => 'Collapse Settings';

  @override
  String get simulationSimSettings => 'Simulation Settings';

  @override
  String get simulationYourTurnTitle => 'Your Turn to Reply';

  @override
  String get simulationYourResponseArea => 'Your Response Area';

  @override
  String get simulationCollapse => 'Collapse';

  @override
  String get simulationJoinDiscussion => 'Join the Discussion';

  @override
  String get simulationOrInputJudgment => 'Or enter your judgment';

  @override
  String get simulationSubmitting => 'Submitting...';

  @override
  String get simulationSubmitJudgment => 'Submit My Judgment';

  @override
  String get simulationContinueInChat => 'Continue in Chat';

  @override
  String get simulationAdjustSimulation => 'Adjust This Simulation';

  @override
  String get simulationDiscussionRounds => 'Discussion Rounds';

  @override
  String get simulationFacilitationStyleTitle => 'Facilitation Style';

  @override
  String get simulationParticipantsTitle => 'Participants';

  @override
  String get simulationRestoreDefault => 'Restore Default';

  @override
  String get simulationCustomHistoricalRole => 'Custom Historical Figure';

  @override
  String get simulationAdd => 'Add';

  @override
  String get simulationRestartSim => 'Restart Simulation';

  @override
  String get simulationContinue => 'Continue';

  @override
  String get simulationPause => 'Pause';

  @override
  String get simulationAwaitingStart => 'Awaiting Start';

  @override
  String get simulationGatheringParticipants => 'Gathering Participants';

  @override
  String get simulationWaitingFirstRound => 'Waiting First Round';

  @override
  String get simulationRolesPending => 'Roles pending';

  @override
  String get simulationGeneratingInBackground =>
      'Still Generating in Background';

  @override
  String get simulationPausedForeground => 'Paused in Foreground';

  @override
  String get simulationImmersiveDiscussion => 'Immersive Discussion';

  @override
  String get simulationCurrentDiscussion => 'Current Discussion';

  @override
  String get simulationWillAppearLive =>
      'Rounds will appear live once started.';

  @override
  String get simulationNoInsightYet => 'No insight summary yet.';

  @override
  String get simulationInsightSummaryTitle => 'Insight Summary';

  @override
  String get simulationGeneratingReport => 'Generating...';

  @override
  String get simulationGenerateLearningReport => 'Generate Learning Report';

  @override
  String get simulationContinueToTheater => 'Continue to Theater';

  @override
  String get simulationShareInsight => 'Share Insight';

  @override
  String get simulationCoreArguments => 'Core Arguments';

  @override
  String get simulationUnresolvedDisagreements => 'Unresolved Disagreements';

  @override
  String get simulationYourContribution => 'Your Contribution';

  @override
  String get simulationExposedKnowledgeGaps => 'Exposed Knowledge Gaps';

  @override
  String get simulationSuggestedNextSteps => 'Suggested Next Steps';

  @override
  String get simulationStructuredInsightGenerated =>
      'Structured insight summary generated.';

  @override
  String get simulationEmptyGenerating => 'Simulation is generating...';

  @override
  String get simulationEmptyStartPrompt =>
      'Start a learning scenario simulation and let roles discuss the topic round by round.';

  @override
  String get simulationCurrentScene => 'Current Scene';

  @override
  String get simulationCurrentGoal => 'Current Goal';

  @override
  String get simulationInteractionStyle => 'Interaction Style';

  @override
  String get simulationRoleDiscussionUserJoin =>
      'Role Discussion + You Respond';

  @override
  String get simulationTopicHint => 'Enter a topic or knowledge point';

  @override
  String get simulationTopicHintExample => 'e.g. Eigenvalues and eigenvectors';

  @override
  String get simulationStartSimulationTopicAction =>
      'Start Simulation About This Topic';

  @override
  String get simulationUserInputTopicHint =>
      'Enter a learning topic or question to discuss';

  @override
  String get simulationUserInputTopicHelper =>
      'After completing more learning tasks, the system will recommend discussion topics based on your real learning data';

  @override
  String get simulationRecommendedEmptyHint =>
      'No recommended seeds yet. You can manually enter a topic to start.';

  @override
  String get simulationRecommendedUserInputHint =>
      'Start with the most specific question you want to discuss. After accumulating more real learning records, the system will recommend topics based on your data.';

  @override
  String get simulationRecommendedPickHint =>
      'Pick a starting point. The recommendation cards will auto-collapse once the discussion begins.';

  @override
  String get simulationScenarioAdjustHint =>
      'Adjusting the scenario will also change the character relationships and discussion dynamics.';

  @override
  String get simulationFacilitationFitHint =>
      'Make the discussion fit the current topic better.';

  @override
  String get simulationDiscussionNote =>
      'Fully adjust the topic, scenario, rounds, facilitation style, and participant roles. Once started, the discussion follows these settings.';

  @override
  String get simulationParticipantHint =>
      'Specify who you want to invite. Keep at least 1 and at most 6 roles.';

  @override
  String get simulationRunningStatusHint =>
      'Simulation in progress. New rounds will appear below in real time.';

  @override
  String get simulationScenarioEyebrow => 'Scenario Simulation';

  @override
  String get simulationScenarioTitle => 'Start This Scenario Simulation';

  @override
  String get simulationScenarioSubtitle =>
      'Choose a discussion scenario, then enter a topic you want to explore. The interface will automatically switch to an immersive discussion view once started.';

  @override
  String get simulationRoleDiscussionValue => 'Role Discussion + You Respond';

  @override
  String get simulationJudgeExampleHint =>
      'e.g. I\'ll strengthen my geometric intuition first, then verify with a problem';

  @override
  String get simulationInteractionExplain =>
      'Give your judgment first, and the next round will truly build around your input.';

  @override
  String get simulationInteractionHint =>
      'Try catching one round here first and let the roles respond to your judgment. You can also bring this step back to the main chat to continue.';

  @override
  String get simulationContinuitySubtitle =>
      'This simulation continues from your previous exploration. You can bring the context back to the original conversation anytime to continue questioning and deciding.';

  @override
  String simulationBridgeCurrentlyVerifyingFormat(String routeTitle) {
    return 'Currently verifying path \"$routeTitle\"';
  }

  @override
  String get simulationBridgeVerifyingRoute =>
      'Currently verifying a deduction path';

  @override
  String simulationBridgeVerificationDescWithTarget(String targetName) {
    return 'This simulation comes from the Knowledge Theater, with a goal of $targetName. You can bring your current progress back to the theater at any time to continue adopting or calibrating.';
  }

  @override
  String get simulationBridgeVerificationContext =>
      'This simulation comes from the Knowledge Theater. The current context remains linked to the original deduction.';

  @override
  String simulationInteractionModeFormat(String mode) {
    return 'Interaction mode: $mode';
  }

  @override
  String get simulationInteractionOpenQuestion => 'Open Question';

  @override
  String get simulationInteractionViewpointChallenge => 'Viewpoint Challenge';

  @override
  String get simulationInteractionBinaryChoice => 'Binary Choice';

  @override
  String get simulationInteractionChoice => 'Choice';

  @override
  String simulationCurrentFocusFormat(String speaker) {
    return 'Current focus: $speaker';
  }

  @override
  String simulationTopicFormat(String topic) {
    return 'Topic: $topic';
  }

  @override
  String simulationTopicAndSpeakerFormat(String topic, String speaker) {
    return 'Topic: $topic · Speaking: $speaker';
  }

  @override
  String simulationRoundN(int round) {
    return 'Round $round';
  }

  @override
  String simulationRoleCountFormat(int count) {
    return '$count roles';
  }

  @override
  String simulationRunningRoundN(int round, int total) {
    return 'Running round $round/$total';
  }

  @override
  String simulationRoundViewpoints(int count) {
    return '$count round viewpoints';
  }

  @override
  String simulationRoleCountLong(int count) {
    return '$count roles';
  }

  @override
  String simulationRoundFormatLabel(int current, int max) {
    return '$current / $max rds';
  }

  @override
  String simulationRoundSliderLabel(int count) {
    return '$count rds';
  }

  @override
  String get simulationParticipantDefaultStatus =>
      'Currently running with default system roles.';

  @override
  String simulationParticipantCurrentStatus(String names) {
    return 'Current participants: $names';
  }

  @override
  String simulationBulletParticipants(String names) {
    return 'Participants: $names';
  }

  @override
  String simulationBulletRounds(int count) {
    return 'Total rounds: $count. Suitable as a basis for further deduction or review report.';
  }

  @override
  String simulationBulletOpening(String message) {
    return 'Opening highlight: $message';
  }

  @override
  String simulationRoundFormatShort(int current, int total) {
    return '$current/$total rds';
  }

  @override
  String get simulationContinueInChatContext =>
      'Continue the simulation in chat.';

  @override
  String simulationContinueTopicLabel(String topic) {
    return 'Topic: $topic';
  }

  @override
  String simulationContinueScenarioLabel(String label) {
    return 'Scenario: $label';
  }

  @override
  String simulationContinueCurrentQuestion(String question) {
    return 'Current question: $question';
  }

  @override
  String simulationContinueMyResponse(String reply) {
    return 'My response: $reply';
  }

  @override
  String get simulationBalancedPush => 'Balanced';

  @override
  String get simulationDebateClash => 'Debate Clash';

  @override
  String get simulationGuidedBreakdown => 'Guided Breakdown';

  @override
  String get simulationPracticalApply => 'Practical Application';

  @override
  String get simulationReportReturnException =>
      'Learning report returned invalid format';

  @override
  String simulationReportGenerationFailed(String error) {
    return 'Failed to generate learning report: $error';
  }

  @override
  String get simulationReportTitle =>
      'This report captures issues exposed in this simulation';

  @override
  String get simulationReportSummary =>
      'Disagreements and knowledge gaps revealed during the simulation have been brought into this formal report.';

  @override
  String simulationShareCreated(String topic, String scenario, String insight) {
    return 'I just ran a learning simulation on Sparkle: $topic\nScenario: $scenario\nInsight: $insight';
  }

  @override
  String simulationShareTitle(String topic) {
    return 'Scenario Simulation · $topic';
  }

  @override
  String simulationShareRawText(String topic, String scenario, String insight) {
    return 'Scenario Simulation\nTopic: $topic\nScenario: $scenario\nInsight: $insight';
  }

  @override
  String get simulationCustomFigureHint => 'e.g. Churchill / Bismarck';

  @override
  String simulationTopicCurrentFocusFormat(String topic, String speaker) {
    return 'Topic: $topic · Speaking: $speaker';
  }

  @override
  String simulationCurrentFocusLabel(String speaker) {
    return 'Current focus: $speaker';
  }

  @override
  String simulationImmersiveTopicAndFocus(String topic, String speaker) {
    return 'Topic: $topic · Speaking: $speaker';
  }

  @override
  String get simulationWaitingInput => 'Awaiting Input';

  @override
  String get simulationScenarioDescStudyGroup =>
      'Multi-role collaborative learning around a topic, ideal for explaining concepts, examples, and misconceptions together.';

  @override
  String get simulationScenarioDescKnowledgeDebate =>
      'Let opposing viewpoints clash directly, ideal for verifying opinions, evidence, and boundary conditions.';

  @override
  String get simulationScenarioDescHistoricalRoleplay =>
      'Bring in characters and era constraints, advancing the discussion like a real historical scene.';

  @override
  String get simulationScenarioDescSocraticDialogue =>
      'Deconstruct premises through persistent questioning, ideal for clarifying vague concepts and reasoning gaps.';

  @override
  String get simulationScenarioDescCaseAnalysis =>
      'Deconstruct, diagnose, and decide around specific cases, ideal for practical topics.';

  @override
  String get simulationScenarioDescWhatIfPath =>
      'Compare different learning or action routes, ideal for planning, trade-offs, and resource allocation.';

  @override
  String get simulationScenarioDescConceptMapBuild =>
      'Weave knowledge points into a structural diagram, ideal for establishing the global framework and connections.';

  @override
  String get simulationScenarioDescErrorDiagnosis =>
      'Focus on identifying error causes, correction paths, and verification methods, ideal for filling gaps.';

  @override
  String get simulationFacilitationDescBalanced =>
      'Fits most topics, emphasizing balanced multi-role progression without any party dominating the field.';

  @override
  String get simulationFacilitationDescDebate =>
      'Actively amplifies controversy and evidence conflicts, better for topics that need viewpoint collision.';

  @override
  String get simulationFacilitationDescGuided =>
      'More like a mentor-led discussion, emphasizing clarification of premises, step-by-step deconstruction, and keeping the user on track.';

  @override
  String get simulationFacilitationDescPractical =>
      'Prioritizes action, verification, and real-world constraints, ideal for skill and solution planning.';

  @override
  String get simulationRoleHonorsStudent => 'Honors Student';

  @override
  String get simulationRoleMidStudent => 'Mid-level Student';

  @override
  String get simulationRoleQuestioner => 'Questioner';

  @override
  String get simulationRoleSummarizer => 'Summarizer';

  @override
  String get simulationRolePracticeCoach => 'Practice Coach';

  @override
  String get simulationRoleProExpert => 'Pro Expert';

  @override
  String get simulationRoleConExpert => 'Con Expert';

  @override
  String get simulationRoleModerator => 'Moderator';

  @override
  String get simulationRoleEvidenceReviewer => 'Evidence Reviewer';

  @override
  String get simulationRolePursuer => 'Pursuer';

  @override
  String get simulationRoleHistoryMentor => 'History Mentor';

  @override
  String get simulationRoleKeyFigure => 'Key Figure';

  @override
  String get simulationRoleEraObserver => 'Era Observer';

  @override
  String get simulationRoleStrategyAdvisor => 'Strategy Advisor';

  @override
  String get simulationRoleRecorder => 'Recorder';

  @override
  String get simulationRoleSocrates => 'Socrates';

  @override
  String get simulationRoleSkeptic => 'Skeptic';

  @override
  String get simulationRoleDeconstructor => 'Deconstructor';

  @override
  String get simulationRoleApplier => 'Applier';

  @override
  String get simulationRoleCaseMentor => 'Case Mentor';

  @override
  String get simulationRoleDiagnostician => 'Diagnostician';

  @override
  String get simulationRolePractitioner => 'Practitioner';

  @override
  String get simulationRoleCounterExample => 'Counter-Example Provider';

  @override
  String get simulationRoleDecisionRecorder => 'Decision Recorder';

  @override
  String get simulationRoleCurrentRoute => 'Current Route';

  @override
  String get simulationRoleRadicalRoute => 'Radical Route';

  @override
  String get simulationRoleRiskObserver => 'Risk Observer';

  @override
  String get simulationRoleResourceScheduler => 'Resource Scheduler';

  @override
  String get simulationRoleVerifier => 'Verifier';

  @override
  String get simulationRoleStructurer => 'Structurer';

  @override
  String get simulationRoleConnector => 'Connector';

  @override
  String get simulationRoleCounterExampleChecker => 'Counter-Example Checker';

  @override
  String get simulationRoleBridgeBuilder => 'Bridge Builder';

  @override
  String get simulationRoleErrorAnalyst => 'Error Analyst';

  @override
  String get simulationRoleCorrectionCoach => 'Correction Coach';

  @override
  String get simulationRoleQuestionDeconstructor => 'Question Deconstructor';

  @override
  String get simulationRoleMigrationCoach => 'Migration Coach';

  @override
  String get simulationRoleStudyBuddy => 'Study Buddy';

  @override
  String get simulationRoleCurrentDiscussionTitle => 'Current Discussion';

  @override
  String simulationBulletOpeningFormat(String message) {
    return 'Opening focus: $message';
  }

  @override
  String get simulationScenarioParticipantOptionsDefault0 => 'Study Buddy';

  @override
  String get simulationScenarioParticipantOptionsDefault1 => 'Questioner';

  @override
  String get simulationScenarioParticipantOptionsDefault2 => 'Summarizer';

  @override
  String get simulationScenarioLabelStudyGroup => 'Study Group';

  @override
  String get simulationScenarioLabelKnowledgeDebate => 'Knowledge Debate';

  @override
  String get simulationScenarioLabelHistoricalRoleplay => 'Historical Roleplay';

  @override
  String get simulationScenarioLabelSocraticDialogue => 'Socratic Dialogue';

  @override
  String get simulationScenarioLabelCaseAnalysis => 'Case Analysis';

  @override
  String get simulationScenarioLabelWhatIfPath => 'What-If Path';

  @override
  String get simulationScenarioLabelConceptMapBuild => 'Concept Map Building';

  @override
  String get simulationScenarioLabelErrorDiagnosis => 'Error Diagnosis';

  @override
  String get openclawPairImportedSaved =>
      'OpenClaw pairing config imported and saved';

  @override
  String get openclawPairImportedVerifyFailed =>
      'Pairing config imported, but connection verification failed';

  @override
  String get openclawClipboardNoPairingPayload =>
      'No OpenClaw pairing string or QR JSON found in clipboard';

  @override
  String get openclawImportedFromClipboard =>
      'Imported OpenClaw pairing config from clipboard';

  @override
  String openclawConnectedToDevice(Object deviceName) {
    return 'Connected to $deviceName';
  }

  @override
  String openclawImportedDevicePairing(Object deviceName) {
    return 'Imported pairing config for $deviceName';
  }

  @override
  String get openclawScannedPairingImported =>
      'Scanned and imported OpenClaw pairing config';

  @override
  String openclawScannedConnectedToDevice(Object deviceName) {
    return 'Scanned and connected to $deviceName';
  }

  @override
  String get openclawUnrecognizedContent =>
      'Cannot recognize this content. Check for gateway_url and token';

  @override
  String get openclawCameraPermissionNeeded =>
      'Camera permission needed for QR pairing. You can also use \"Import from clipboard\" or \"Paste pairing string\".';

  @override
  String get openclawQrNotPairingContent =>
      'The scanned QR code is not a recognizable OpenClaw pairing payload';

  @override
  String get openclawRemoteTemplateFilled =>
      'Remote connection template filled. Add an auth token or import a pairing string next.';

  @override
  String get openclawPairingCodeExpired => 'Pairing code expired';

  @override
  String openclawPairingExpiresSeconds(Object seconds) {
    return 'Complete pairing within $seconds seconds';
  }

  @override
  String openclawPairingExpiresMinutes(Object minutes, Object seconds) {
    return 'Complete pairing within ${minutes}m ${seconds}s';
  }

  @override
  String get openclawInvalidUrlFormat =>
      'Please enter an address starting with http://, https://, ws://, or wss://';

  @override
  String get openclawValidAddressRequired =>
      'Please enter a valid OpenClaw address';

  @override
  String get openclawDisconnected => 'OpenClaw connection disconnected';

  @override
  String openclawPairingCodeGenerated(Object code) {
    return 'Pairing code $code generated';
  }

  @override
  String get openclawDeviceTokenRequired =>
      'Please enter the device token before completing pairing';

  @override
  String get openclawDevicePairingComplete => 'Device pairing completed';

  @override
  String get openclawNoExecutionPermission =>
      'Gateway is accessible but lacks execution permission. Cannot retry queue.';

  @override
  String get openclawExecutionEndpointUnavailable =>
      'Gateway is accessible but the execution endpoint is unavailable. Cannot retry queue.';

  @override
  String get openclawExecutionEngineNotConnected =>
      'Execution engine is not connected. Cannot retry queue.';

  @override
  String openclawQueuedTasksResubmitted(Object count) {
    return '$count queued task(s) resubmitted';
  }

  @override
  String get openclawNoRetryableTasks => 'No queued tasks available to retry';

  @override
  String get openclawPairingCodeCopied => 'Pairing code copied';

  @override
  String get openclawImportPairingString => 'Import Pairing String';

  @override
  String get openclawPairingOrQrLabel => 'Pairing string or QR content';

  @override
  String get openclawPairingPasteHint =>
      'Paste the JSON shared from OpenClaw desktop, openclaw://pair?... link, or text containing gateway_url / pair_token';

  @override
  String get openclawImportAndSave => 'Import & Save';

  @override
  String get openclawApplyWizard => 'Apply Wizard';

  @override
  String get openclawDisconnect => 'Disconnect';

  @override
  String get openclawDisconnectConfirmBody =>
      'This will clear the locally saved OpenClaw connection config.';

  @override
  String get openclawDisconnectAction => 'Disconnect';

  @override
  String get openclawGatewayOnlineNoExecPermission =>
      'Gateway online, but current token lacks execution permission';

  @override
  String get openclawGatewayOnlineExecNotReady =>
      'Gateway online, but execution endpoint is not ready';

  @override
  String get openclawNeedExecutionChainCheck =>
      'An additional execution chain check is needed';

  @override
  String get openclawTroubleshootNoPermissionBody =>
      'Health check passes but execution requests are rejected. Replace the token with one that has the `operator.write` scope, or switch to device pairing + WebSocket.';

  @override
  String get openclawTroubleshootMissingEndpointBody =>
      'Address is reachable but `/v1/responses` execution endpoint is missing. Verify OpenClaw gateway version, proxy forwarding, and transport selection are consistent.';

  @override
  String get openclawTroubleshootGenericBody =>
      'Re-test the connection, then verify the gateway address, auth method, and transport match the current OpenClaw instance.';

  @override
  String get openclawStatusReadyForTasks => 'Ready to take on tasks';

  @override
  String get openclawStatusConfirmingConnection =>
      'Confirming connection status';

  @override
  String get openclawStatusOnlineNoPermission =>
      'Gateway online, but no execution permission';

  @override
  String get openclawStatusNotConnected => 'Not connected yet';

  @override
  String get openclawStatusNotConfigured => 'OpenClaw not configured yet';

  @override
  String get openclawStatusConnectedSubtitle =>
      'Connection is stable. You can delegate work to OpenClaw from the task page or chat page.';

  @override
  String get openclawStatusConnectingSubtitle =>
      'Confirming engine status. Saved results will show here.';

  @override
  String get openclawStatusNoPermissionSubtitle =>
      'Token can access the gateway, but execution will be rejected. This requires permission handling, not just re-entering the address.';

  @override
  String get openclawStatusErrorSubtitleFallback =>
      'Check the address, auth method, and transport protocol, then re-test the connection.';

  @override
  String get openclawStatusDisconnectedSubtitle =>
      'After the first connection, delegation, queuing, and recent activity will auto-link across all entry points.';

  @override
  String get openclawUnsavedChanges => 'Unsaved changes';

  @override
  String get openclawDevicePairing => 'Device pair';

  @override
  String get openclawTokenAuth => 'Token auth';

  @override
  String openclawQueuedRequestCount(Object count) {
    return '$count pending';
  }

  @override
  String get openclawQuickConnect => 'Quick Connect';

  @override
  String get openclawCustomConfig => 'Custom Config';

  @override
  String get openclawCustomConfigDesc =>
      'Connect using a custom gateway URL and token';

  @override
  String get openclawGuestMainDesc =>
      'Use the local gateway for direct connection';

  @override
  String get openclawGuestMainLabel => 'Local Gateway';

  @override
  String get openclawImportFromClipboard => 'Import from Clipboard';

  @override
  String get openclawPastePairingString => 'Paste Pairing String';

  @override
  String get openclawScanToPair => 'Scan to Pair';

  @override
  String get openclawTailscaleRemoteNode => 'Tailscale Remote Node';

  @override
  String get openclawTailscaleIpOrDomain => 'Tailscale IP or domain name';

  @override
  String get openclawTailscaleHint =>
      'e.g. 100.88.1.24 or devbox.tail123.ts.net';

  @override
  String get openclawTailscaleHelperText =>
      'If your OpenClaw is exposed via Tailscale, just enter the node IP or MagicDNS domain. Sparkle will auto-fill the standard port and WebSocket connection.';

  @override
  String get openclawTailscaleLabel => 'Tailscale';

  @override
  String get openclawCloudflareTunnel => 'Cloudflare Tunnel';

  @override
  String get openclawTunnelDomain => 'Tunnel domain';

  @override
  String get openclawCloudflareHint => 'e.g. openclaw.example.com';

  @override
  String get openclawCloudflareHelperText =>
      'If your OpenClaw is exposed via Cloudflare Tunnel, just enter the domain. Sparkle will generate the connection config using HTTPS/WSS.';

  @override
  String get openclawCloudflareLabel => 'Cloudflare';

  @override
  String openclawPresetSelected(Object label) {
    return '\"$label\" selected. Connection details will be auto-filled. If you later see a missing execution permission error, replace the token with one that has `operator.write` scope, or switch to device pairing.';
  }

  @override
  String get openclawGatewayAddress => 'Gateway address';

  @override
  String get openclawGatewayHint => 'e.g. http://localhost:8080';

  @override
  String get openclawAuthMode => 'Auth mode';

  @override
  String get openclawAuthToken => 'Auth token';

  @override
  String get openclawAuthTokenHint => 'Paste OpenClaw gateway token';

  @override
  String get openclawDeviceToken => 'Device token';

  @override
  String get openclawDeviceTokenHint => 'Paste device token after pairing';

  @override
  String get openclawPairingCode => 'Pairing code';

  @override
  String get openclawPairingCodeInstructions =>
      'Enter this 6-digit pairing code on OpenClaw desktop, then paste the returned device token above.';

  @override
  String get openclawGeneratePairingCode => 'Generate pairing code';

  @override
  String get openclawCompletePairing => 'Complete pairing';

  @override
  String get openclawCancelPairing => 'Cancel pairing';

  @override
  String get openclawTransportProtocol => 'Transport protocol';

  @override
  String get openclawDeviceAuthDesc =>
      'Best for pairing with a local OpenClaw instance. Once complete, subsequent connections are smoother.';

  @override
  String get openclawTokenAuthDesc =>
      'Use when you already have a gateway token and need to quickly verify or switch environments.';

  @override
  String get openclawWebSocketTransportDesc =>
      'WebSocket is better for persistent connections, frequent delegation, and state push-back.';

  @override
  String get openclawHttpTransportDesc =>
      'HTTP is better for manual verification and quick connection testing.';

  @override
  String get openclawDefaultConnectionReady =>
      'Default connection details ready';

  @override
  String get openclawTestConnection => 'Test connection';

  @override
  String get openclawSaveConfig => 'Save config';

  @override
  String get openclawRetryQueue => 'Retry queue';

  @override
  String get accountabilityPartnerDefault => 'Accountability Partner';

  @override
  String get accountabilityEndPartnership => 'End partnership';

  @override
  String get accountabilityDashboardLoadFailed =>
      'Partner dashboard failed to load';

  @override
  String get accountabilityNudgeSentDefault =>
      'Sent as an in-app reminder. They will see it in real time when online.';

  @override
  String get accountabilityNudgeCooldown =>
      'Already nudged recently. The reminder was delivered as an in-app notification. They will see it in real time when online.';

  @override
  String get accountabilityNudgeFailed =>
      'Failed to send nudge. Please try again later.';

  @override
  String get accountabilityEndPartnershipConfirm =>
      'Are you sure you want to end this accountability partnership?';

  @override
  String get accountabilityPartnershipEnded => 'Partnership ended';

  @override
  String get accountabilityMyGoal => 'My goal';

  @override
  String get accountabilityGoalNotSet => 'No goal set yet';

  @override
  String get accountabilityGrowingTogether => 'Growing together';

  @override
  String get accountabilityRecentShares => 'Recent shares';

  @override
  String get accountabilitySharedItem => 'Shared item';

  @override
  String get accountabilityMonthlyHeatmap => 'Monthly check-in heatmap';

  @override
  String get accountabilityPartnerAchievements => 'Partner achievements';

  @override
  String get accountabilityPartnerNoAchievements =>
      'Your partner hasn\'t unlocked exclusive achievements yet. Try a round of mutual check-ins first.';

  @override
  String get accountabilityRecentCheckins => 'Recent check-ins';

  @override
  String get accountabilityNoCheckinRecords => 'No check-in records yet';

  @override
  String get accountabilityNoCheckinHint =>
      'Share a quick update today and your partnership will start to feel alive.';

  @override
  String get accountabilityCheckedInToday => 'Checked in today';

  @override
  String get accountabilityCheckInToday => 'Check in today';

  @override
  String get accountabilityTotalCheckins => 'Total check-ins';

  @override
  String get accountabilityCheckedIn => 'Checked in';

  @override
  String get accountabilityCheckin => 'Check in';

  @override
  String get accountabilityNudge => 'Nudge';

  @override
  String get accountabilityShare => 'Share';

  @override
  String get accountabilityChat => 'Chat';

  @override
  String get accountabilityInviteSentWait =>
      'Invitation sent. Partner dashboard will be available after they confirm.';

  @override
  String get accountabilityInvitePendingConfirm =>
      'This partnership invite is waiting for your confirmation. Process it on the invitations page first.';

  @override
  String get accountabilityDashboardNotAvailable =>
      'The full partner dashboard is not available right now.';

  @override
  String get accountabilityInvitePending => 'Partnership invite pending';

  @override
  String get accountabilityDashboardUnavailable =>
      'Partner dashboard unavailable';

  @override
  String get accountabilityViewStatus => 'View status';

  @override
  String get accountabilityHandleInvite => 'Handle invitation';

  @override
  String get accountabilityContinueChat => 'Continue chat';

  @override
  String get accountabilityNoPendingPolicies =>
      'No pending accountability policies.';

  @override
  String get accountabilityPendingPolicies => 'Pending policies';

  @override
  String get accountabilityNoRecentReflections =>
      'No recent cross-event reflections.';

  @override
  String get accountabilityRecentReflections => 'Recent reflections';

  @override
  String get accountabilityForesightHint => 'Foresight hint';

  @override
  String get accountabilityNoForesightHint => 'No foresight hints yet.';

  @override
  String get accountabilityInterventionIneffective =>
      'Intervention ineffective';

  @override
  String get accountabilityPlanStall => 'Plan stall';

  @override
  String get accountabilityOverload => 'Overload';

  @override
  String get accountabilityTooDifficult => 'Too difficult';

  @override
  String get accountabilityUnclear => 'Unclear';

  @override
  String get accountabilityAbandoned => 'Dropped midway';

  @override
  String get accountabilityReflectionSummary => 'Reflection summary';

  @override
  String get accountabilityDimPace => 'Pace';

  @override
  String get accountabilityDimCompletionRate => 'Completion rate';

  @override
  String get accountabilityDimEngagement => 'Engagement';

  @override
  String get accountabilityDimMood => 'Mood';

  @override
  String get accountabilityDimPlanAdherence => 'Plan adherence';

  @override
  String get accountabilityMoodLow => 'Low';

  @override
  String get accountabilityMoodOkay => 'Okay';

  @override
  String get accountabilityMoodSteady => 'Steady';

  @override
  String get accountabilityMoodGood => 'Good';

  @override
  String get accountabilityMoodGreat => 'Great';

  @override
  String get accountabilityPartner => 'Partner';

  @override
  String get accountabilityLike => 'Like';

  @override
  String get accountabilityEncourage => 'Encourage';

  @override
  String get accountabilityEncourageSent => 'Encouragement sent to partner';

  @override
  String get accountabilitySendEncourage => 'Send encouragement';

  @override
  String get accountabilityEncourageHint => 'Write a message to your partner';

  @override
  String get accountabilitySend => 'Send';

  @override
  String get accountabilityEncourageDelivered => 'Encouragement delivered';

  @override
  String get accountabilityTodayProgressHint => 'Today\'s progress...';

  @override
  String get accountabilityTodayMood => 'Today\'s mood:';

  @override
  String get accountabilityPublishCheckin => 'Publish check-in';

  @override
  String get accountabilityProgressRequired =>
      'Please write about today\'s progress';

  @override
  String get accountabilityCheckinSuccess =>
      'Check-in successful. Your partner can see it now.';

  @override
  String get openclawImportedPairing => 'Imported OpenClaw pairing config';

  @override
  String accountabilityPartnerGoal(Object partnerName) {
    return '$partnerName\'s goal';
  }

  @override
  String get accountabilityPartnerGoalNotSet => 'They haven\'t set a goal yet';

  @override
  String get accountabilityMe => 'Me';

  @override
  String get accountabilityThem => 'Them';

  @override
  String accountabilityStreakDays(Object days) {
    return '$days days';
  }

  @override
  String accountabilityCheckinMinutes(Object minutes) {
    return '$minutes min';
  }

  @override
  String accountabilityDaysTogether(Object days) {
    return 'Stayed together for $days days';
  }

  @override
  String accountabilityMyStreakDays(Object days) {
    return 'Me $days days';
  }

  @override
  String accountabilityPartnerStreakDays(Object days) {
    return 'Them $days days';
  }

  @override
  String accountabilityMyAchievementsUnlocked(Object count) {
    return 'I unlocked $count achievements';
  }

  @override
  String accountabilityPartnerAchievementsUnlocked(Object count) {
    return 'They unlocked $count achievements';
  }

  @override
  String accountabilityStreakRank(Object myRank, Object partnerRank) {
    return 'Streak ranking: you $myRank, partner $partnerRank';
  }

  @override
  String accountabilityDeviationsDetected(Object count) {
    return '$count deviation(s) detected';
  }

  @override
  String accountabilityUpdatedAt(Object time) {
    return 'Updated $time';
  }

  @override
  String get accountabilityZeroItems => '0 items';

  @override
  String accountabilityItemCount(Object count) {
    return '$count items';
  }

  @override
  String accountabilityPoliciesReady(Object count) {
    return '$count policy/policies ready, waiting for event trigger.';
  }

  @override
  String accountabilityReflectionsGenerated(Object count) {
    return '$count reflection summary/recently generated.';
  }

  @override
  String accountabilityPoliciesPending(Object count, Object time) {
    return '$count pending policy/policies, next trigger at $time.';
  }

  @override
  String accountabilityReflectionsLatest(Object category, Object time) {
    return 'Last focused on $category, updated $time.';
  }

  @override
  String accountabilityInvestedTime(Object minutes) {
    return 'Time invested: $minutes min';
  }

  @override
  String accountabilityMinutes(Object minutes) {
    return '$minutes min';
  }

  @override
  String get accountabilityEnd => 'End';

  @override
  String get accountabilityOperationFailed => 'Operation failed';

  @override
  String get accountabilityLikeFailed => 'Like failed';

  @override
  String get accountabilitySendFailed => 'Send failed';

  @override
  String get accountabilityCheckinFailed => 'Check-in failed';

  @override
  String get openclawHubGatewayNoPermission =>
      'Gateway is reachable but lacks execution permission; cannot retry queue yet';

  @override
  String get openclawHubEndpointUnavailable =>
      'Gateway is reachable but execution endpoint is unavailable; cannot retry queue yet';

  @override
  String get openclawHubEngineNotConnected =>
      'Execution engine not connected yet; cannot retry queue';

  @override
  String get openclawHubNoRetryQueuedItems => 'No queued items to retry';

  @override
  String get openclawHubQueueCleared => 'Queue cleared';

  @override
  String get openclawHubConnectedDiagnostics =>
      'OpenClaw connected. Tap to view diagnostics';

  @override
  String get openclawHubGatewayNoPermissionDiagnostics =>
      'Gateway reachable but missing execution permission. Tap to view diagnostics';

  @override
  String get openclawHubEndpointIssueDiagnostics =>
      'Gateway reachable but execution endpoint issue. Tap to view diagnostics';

  @override
  String get openclawHubQueuedTasksDiagnostics =>
      'Tasks are queued. Tap to view diagnostics';

  @override
  String get openclawHubNotConnectedDiagnostics =>
      'OpenClaw connection incomplete. Tap to view diagnostics';

  @override
  String get openclawHubOverviewGatewayNoPermission =>
      'Gateway online, but no execution permission';

  @override
  String get openclawHubOverviewEndpointIssue =>
      'Gateway online, but execution endpoint unavailable';

  @override
  String get openclawHubOverviewReady => 'OpenClaw is ready to take over';

  @override
  String get openclawHubOverviewTasksWaiting =>
      'Tasks are waiting for OpenClaw to come back';

  @override
  String get openclawHubOverviewConfigSaved =>
      'Connection info saved, not yet connected';

  @override
  String get openclawHubOverviewConnectFirst =>
      'Connect OpenClaw first, then start delegating steadily';

  @override
  String get openclawHubOverviewGatewayNoPermissionDesc =>
      'The gateway is reachable, but actual execution is blocked by permissions. Add writable scopes, or switch to device pairing + WebSocket to close the loop.';

  @override
  String get openclawHubOverviewEndpointIssueDesc =>
      'The address is reachable, but the execution interface is not ready. Check `/v1/responses`, proxy forwarding, and that the transport selection is consistent.';

  @override
  String get openclawHubOverviewConnectedDesc =>
      'Connection is stable. You can delegate web research, organization, and scraping tasks from the task or chat page.';

  @override
  String get openclawHubOverviewDefaultDesc =>
      'Once connected, home, chat, and task pages will share the same execution center — no more hunting around.';

  @override
  String get openclawHubActionHintPermission =>
      'The top priority now is to replace the token with one that has execution permission, or switch to a paired WebSocket connection.';

  @override
  String get openclawHubActionHintEndpoint =>
      'The top priority now is to check the execution interface and transport, making the gateway go from \"reachable\" to \"executable\".';

  @override
  String get openclawHubActionHintRetryQueue =>
      'The top priority now is to resubmit the waiting queue.';

  @override
  String get openclawHubActionHintReconnect =>
      'The top priority now is to restore the connection so queued tasks can resume.';

  @override
  String get openclawHubActionHintNewDelegation =>
      'The top priority now is to go back to chat or tasks and start a new delegation.';

  @override
  String get openclawHubActionHintCompleteConnection =>
      'The top priority now is to complete the connection so OpenClaw becomes your true execution companion.';

  @override
  String get openclawHubAppBarTitle => 'OpenClaw Hub';

  @override
  String get openclawHubMetricConnectedNoPermission =>
      'Connected, no exec permission';

  @override
  String get openclawHubMetricConnectedEndpointIssue =>
      'Connected, endpoint issue';

  @override
  String get openclawHubMetricConnected => 'Connected';

  @override
  String get openclawHubMetricNotConnected => 'Not connected';

  @override
  String get openclawHubMetricPairedDevice => 'Paired device';

  @override
  String get openclawHubMetricTokenAuth => 'Token auth';

  @override
  String get openclawHubButtonContinueSetup => 'Continue Setup';

  @override
  String get openclawHubButtonViewQueue => 'View Queue';

  @override
  String get openclawHubButtonAutomation => 'Automation';

  @override
  String get openclawHubButtonEnterChat => 'Open Chat';

  @override
  String get openclawHubButtonViewTasks => 'View Tasks';

  @override
  String get openclawHubSectionConnectionTitle => 'Connection & Control';

  @override
  String get openclawHubSectionConnectionSubtitle =>
      'Review the connection summary first, then decide whether to expand the full editor — so you aren\'t hit by the full form on arrival.';

  @override
  String get openclawHubCollapseConnectionEdit => 'Collapse editor';

  @override
  String get openclawHubExpandConnectionEdit => 'Edit connection';

  @override
  String get openclawHubGatewayUrlEmpty => 'Gateway URL not set';

  @override
  String get openclawHubConnectionSummaryPermission =>
      'This gateway is reachable, but the current auth doesn\'t grant real execution permission. Fix permissions first, then retry the queue.';

  @override
  String get openclawHubConnectionSummaryEndpoint =>
      'The gateway is reachable, but the execution interface isn\'t ready. Check transport and `/v1/responses` first for a faster fix.';

  @override
  String get openclawHubConnectionSummaryConnected =>
      'The connection is stable. Continue using the current method for direct delegation.';

  @override
  String get openclawHubConnectionSummaryConfigured =>
      'Configuration is saved locally. Expand to fine-tune auth, protocol, and pairing flow.';

  @override
  String get openclawHubConnectionSummaryFirstTime =>
      'First-time setup usually only needs the address, then pick token auth or device pairing.';

  @override
  String get openclawHubSectionDevicesTitle => 'Devices & Affinity';

  @override
  String get openclawHubSectionDevicesSubtitle =>
      'Explicitly configure which tasks go to which device, so the system doesn\'t have to guess your preferences every time.';

  @override
  String get openclawHubCollapseDeviceDetails => 'Collapse device details';

  @override
  String get openclawHubExpandDeviceDetails => 'View devices & preferences';

  @override
  String get openclawHubDevicesSummaryEmpty =>
      'Node list will appear automatically after a successful OpenClaw connection. Clearer device setup means more stable multi-node scheduling and fallback.';

  @override
  String get openclawHubSectionQueueTitle => 'Queue & Delegation';

  @override
  String get openclawHubSectionQueueSubtitle =>
      'First see what needs your attention most, then decide whether to expand the full queue and template catalog.';

  @override
  String get openclawHubCollapseQueueDetails => 'Collapse queue details';

  @override
  String get openclawHubExpandQueueDetails => 'View full queue';

  @override
  String get openclawHubQueueSummaryConnected =>
      'Your best move right now is to resubmit the queued tasks first, then start new delegations once the engine clears the backlog.';

  @override
  String get openclawHubQueueSummaryNotConnected =>
      'You\'ve already queued tasks. Next step is to restore the connection so they can all resume at once.';

  @override
  String get openclawHubQueueSummaryConnectedEmpty =>
      'No queued tasks right now. This is a great time to go back to chat or tasks and start a new delegation.';

  @override
  String get openclawHubQueueSummaryNotConnectedEmpty =>
      'No queued tasks either. Complete the connection first, then decide whether to start your first delegation.';

  @override
  String get openclawHubQueueEmptyLabel => 'Queue is currently empty';

  @override
  String get openclawHubButtonRetryQueue => 'Retry Queue';

  @override
  String get openclawHubButtonClearQueue => 'Clear Queue';

  @override
  String get openclawHubAvailableTemplates =>
      'Available Templates / Capabilities';

  @override
  String get openclawHubTemplatesEmptyHint =>
      'Templates will load on demand when you open a specific task. For now, tidy up the connection, queue, and recent activity first.';

  @override
  String get openclawHubSectionAutomationTitle => 'Automation & Batch';

  @override
  String get openclawHubSectionAutomationSubtitle =>
      'Put one-off batch execution and long-term scheduled/conditional execution on the same console, so your execution capability goes beyond single clicks.';

  @override
  String get openclawHubCollapseAutomationDetails =>
      'Collapse automation details';

  @override
  String get openclawHubExpandAutomationDetails =>
      'View automation capabilities';

  @override
  String get openclawHubAutomationSummaryEmpty =>
      'No automations yet. Expand to create daily scheduled, event-triggered, or conditional polling automations, and launch batch delegations from here.';

  @override
  String get openclawHubSectionActivityTitle => 'Recent Activity';

  @override
  String get openclawHubSectionActivitySubtitle =>
      'A high-density timeline of recent delegations, so you don\'t have to flip between task pages.';

  @override
  String get openclawHubCollapseActivityDetails => 'Collapse activity details';

  @override
  String get openclawHubExpandActivityDetails => 'View all activity';

  @override
  String get openclawHubActivityEmptyHint =>
      'No recent executions yet. Start your first delegation from a home card, the task execution page, or the chat entry point.';

  @override
  String get openclawHubActivityHint => 'View this task\'s execution details.';

  @override
  String get openclawHubActivityOpenTask => 'Open Task Execution';

  @override
  String get openclawHubStatusRecorded => 'Recorded';

  @override
  String openclawHubRetryQueuedSuccess(int count) {
    return '$count queued tasks resubmitted';
  }

  @override
  String openclawHubLastExecutionStatus(String status) {
    return 'Last execution status is \"$status\". Continue reviewing connection, queue, and activity from here.';
  }

  @override
  String openclawHubPendingDelegationsDesc(int count) {
    return 'You have $count delegations waiting for the connection to come back. Reconnecting the engine first will be most effective.';
  }

  @override
  String openclawHubQueuedTasksCount(int count) {
    return '$count queued tasks';
  }

  @override
  String openclawHubNodeCount(int count) {
    return '$count nodes';
  }

  @override
  String openclawHubAutomationCount(int count) {
    return '$count automations';
  }

  @override
  String openclawHubLatestBatch(int completed, int total) {
    return 'Latest batch $completed/$total';
  }

  @override
  String openclawHubLastTrustLabel(String label) {
    return 'Last trust assessment: $label';
  }

  @override
  String openclawHubDevicesSummaryActiveWithCount(int count) {
    return 'Currently discovered $count nodes. You can assign preferred devices for browser, terminal, document, and API tasks here. When offline, Sparkle will automatically find fallback nodes.';
  }

  @override
  String openclawHubAutomationSummaryActiveWithCount(int count) {
    return '$count automations are currently running. Batch delegation summaries and scheduled task statuses will continuously aggregate here.';
  }

  @override
  String openclawHubTaskLabel(String taskId) {
    return 'Task $taskId';
  }

  @override
  String openclawHubTaskLabelTemplate(String templateId) {
    return 'Template $templateId';
  }

  @override
  String openclawHubTaskLabelSource(String source) {
    return 'Source $source';
  }

  @override
  String get seedLibraryDetailFriendlyError =>
      'The system couldn\'t complete this operation right now. Please try again later.';

  @override
  String get seedLibraryDetailUserRatings => 'User Ratings';

  @override
  String get seedLibraryDetailQualityBreakdown => 'Quality Score Breakdown';

  @override
  String get seedLibraryDetailQualityBreakdownDesc =>
      'The list shows the composite quality score. Here you can also see the system base score and average user rating to help you decide if this seed library is worth keeping active long-term.';

  @override
  String get seedLibraryDetailQualityComprehensive => 'Overall';

  @override
  String get seedLibraryDetailQualitySystem => 'System';

  @override
  String get seedLibraryDetailQualityUser => 'User';

  @override
  String get seedLibraryDetailApplyToSystem => 'Apply to System';

  @override
  String get seedLibraryDetailAppliedSuccess => 'Applied to system';

  @override
  String get seedLibraryDetailPausedSuccess => 'Paused using this seed library';

  @override
  String get seedLibraryDetailStatusUpdated => 'Seed library status updated';

  @override
  String get seedLibraryDetailPauseUse => 'Pause';

  @override
  String get seedLibraryDetailApplyLibrary => 'Apply Library';

  @override
  String get seedLibraryDetailSetPrimarySuccess => 'Set as primary';

  @override
  String get seedLibraryDetailSetPrimary => 'Set as Primary';

  @override
  String get seedLibraryDetailMarkedNotSuitableSuccess =>
      'Recorded \"this library isn\'t a fit for me\"';

  @override
  String get seedLibraryDetailMarkNotSuitable => 'Not a Fit for Me';

  @override
  String get seedLibraryDetailEditRating => 'Edit Rating';

  @override
  String get seedLibraryDetailGiveRating => 'Rate It';

  @override
  String get seedLibraryDetailSubscriptionStatusEnabled => 'Enabled';

  @override
  String get seedLibraryDetailSubscriptionStatusDisabled =>
      'Subscribed, not enabled';

  @override
  String get seedLibraryDetailActiveSubscriptions => 'Active Seed Libraries';

  @override
  String get seedLibraryDetailActiveSubscriptionsDesc =>
      'You can enable multiple seed libraries at once. The system will prioritize high-priority libraries, then blend in content from other enabled libraries.';

  @override
  String get seedLibraryDetailFallbackName => 'Seed Library';

  @override
  String get seedLibraryDetailNoResultsUnderFilter =>
      'No content under current filters';

  @override
  String get seedLibraryDetailUsageFewShot =>
      'Enhances AI response style and example quality for similar tasks';

  @override
  String get seedLibraryDetailUsageTeachingContent =>
      'Provides high-quality teaching content for study plans, task descriptions, and knowledge explanations';

  @override
  String get seedLibraryDetailUsageReplyTemplate =>
      'Improves system reply template and expression stability';

  @override
  String get seedLibraryDetailUsageCustom =>
      'Captures your own content preferences and curated examples';

  @override
  String get seedLibraryDetailFilterTitle => 'Filter Content';

  @override
  String get seedLibraryDetailFilterDesc =>
      'Filter entries in this seed library by content type, difficulty, and enabled status.';

  @override
  String get seedLibraryDetailFilterContentType => 'Content Type';

  @override
  String get seedLibraryDetailFilterAll => 'All';

  @override
  String get seedLibraryDetailFilterDifficulty => 'Difficulty';

  @override
  String get seedLibraryDetailFilterShowInactive => 'Show Inactive Content';

  @override
  String get seedLibraryDetailFilterShowInactiveDesc =>
      'When off, only show currently active entries';

  @override
  String get seedLibraryDetailFilterReset => 'Reset';

  @override
  String get seedLibraryDetailFilterDone => 'Done';

  @override
  String get seedLibraryDetailRatingTitle => 'Rate This Seed Library';

  @override
  String get seedLibraryDetailRatingDescription =>
      'Your rating affects this seed library\'s display quality score.';

  @override
  String get seedLibraryDetailRatingCommentLabel => 'Comment (optional)';

  @override
  String get seedLibraryDetailRatingSubmitted => 'Rating submitted';

  @override
  String get seedLibraryDetailSubmitRating => 'Submit Rating';

  @override
  String get seedLibraryDetailContentBody => 'Body';

  @override
  String get seedLibraryDetailStructuredContent => 'Structured Content';

  @override
  String get seedLibraryDetailEditLibrary => 'Edit Seed Library';

  @override
  String get seedLibraryDetailEditName => 'Name';

  @override
  String get seedLibraryDetailEditNameEmpty => 'Name cannot be empty';

  @override
  String get seedLibraryDetailEditDescriptionOptional =>
      'Description (optional)';

  @override
  String get seedLibraryDetailEditCancel => 'Cancel';

  @override
  String get seedLibraryDetailEditSave => 'Save';

  @override
  String get seedLibraryDetailLibraryUpdated => 'Seed library updated';

  @override
  String get seedLibraryDetailAddItem => 'Add Seed Content';

  @override
  String get seedLibraryDetailAddItemType => 'Content Type';

  @override
  String get seedLibraryDetailAddItemTitle => 'Title';

  @override
  String get seedLibraryDetailAddItemContent => 'Content';

  @override
  String get seedLibraryDetailAddItemSubject => 'Subject';

  @override
  String get seedLibraryDetailAddItemDifficulty => 'Difficulty';

  @override
  String get seedLibraryDetailAddItemUnset => 'Not set';

  @override
  String get seedLibraryDetailAddItemTags => 'Tags (comma separated)';

  @override
  String get seedLibraryDetailAddItemSave => 'Save Content';

  @override
  String get seedLibraryDetailAddItemSuccess => 'Seed content added';

  @override
  String get seedLibraryDetailImportCannotRead => 'Cannot read file content';

  @override
  String get seedLibraryDetailImportInvalidJson =>
      'Invalid JSON format, expected an array or [items:[...]]';

  @override
  String get seedLibraryDetailImportNoItems =>
      'No importable items found in file';

  @override
  String seedLibraryDetailApplyFailed(String error) {
    return 'Apply failed: $error';
  }

  @override
  String seedLibraryDetailSetPrimaryFailed(String error) {
    return 'Set primary failed: $error';
  }

  @override
  String seedLibraryDetailMarkNotSuitableFailed(String error) {
    return 'Record failed: $error';
  }

  @override
  String seedLibraryDetailCurrentStatus(String status, int priority) {
    return 'Current status: $status · Priority $priority';
  }

  @override
  String seedLibraryDetailUsageAppliedEnabled(String hint) {
    return 'Now in effect. $hint The system will use it alongside other active seed libraries by priority.';
  }

  @override
  String seedLibraryDetailUsageSubscribedNotEnabled(String hint) {
    return 'Subscribed but not enabled. Once enabled, $hint.';
  }

  @override
  String seedLibraryDetailUsageNotApplied(String hint) {
    return 'Not yet applied. Once applied, $hint.';
  }

  @override
  String seedLibraryDetailCurrentRating(String score) {
    return 'Current rating: $score / 10';
  }

  @override
  String seedLibraryDetailRatingFailed(String error) {
    return 'Rating failed: $error';
  }

  @override
  String seedLibraryDetailAddItemFailed(String error) {
    return 'Add failed: $error';
  }

  @override
  String seedLibraryDetailImportResult(int imported, int failed) {
    return 'Import complete: $imported succeeded, $failed failed';
  }

  @override
  String seedLibraryDetailImportFailed(String error) {
    return 'Import failed: $error';
  }
}
