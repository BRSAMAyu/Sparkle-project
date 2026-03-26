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
  String get notificationPermissionDenied => 'Denied';

  @override
  String get notificationPermissionPartial => 'Partial';

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
  String get galaxyEmptyMessage => 'Galaxy Empty Message';

  @override
  String get galaxyEmptyTitle => 'Galaxy Empty Title';

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
  String get galaxyLoadFailedTitle => 'Galaxy Load Failed Title';

  @override
  String get galaxyLoadingMessage => 'Galaxy Loading Message';

  @override
  String get galaxyLoadingTitle => 'Galaxy Loading Title';

  @override
  String get galaxyNodeFocus => 'Galaxy Node Focus';

  @override
  String get galaxyNodeInspectConnections => 'Galaxy Node Inspect Connections';

  @override
  String get galaxyNodeLocked => 'Galaxy Node Locked';

  @override
  String galaxyNodePreviewSubtitle(Object arg0, Object arg1) {
    return '$arg0 $arg1';
  }

  @override
  String get galaxyNodeUnlocked => 'Galaxy Node Unlocked';

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
  String get galaxyReload => 'Galaxy Reload';

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
}
