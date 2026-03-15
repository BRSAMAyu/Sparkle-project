import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/calendar/presentation/screens/calendar_stats_screen.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/screens/create_post_screen.dart';
import 'package:sparkle/features/community/presentation/screens/create_group_screen.dart';
import 'package:sparkle/features/community/presentation/screens/community_main_screen.dart';
import 'package:sparkle/features/home/data/models/notification_model.dart';
import 'package:sparkle/features/home/data/repositories/notification_repository.dart';
import 'package:sparkle/features/home/presentation/screens/notification_list_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/user/presentation/screens/edit_profile_screen.dart';
import 'package:sparkle/features/user/presentation/screens/profile_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  setUp(() {
    DemoDataService.isDemoMode = true;
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  group('Main actions smoke', () {
    testWidgets('dashboard refresh gesture does not throw', (tester) async {
      await _pumpPage(tester, const DashboardScreen());

      await tester.drag(find.byType(CustomScrollView), const Offset(0, 300));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(seconds: 1));

      expect(find.byType(DashboardScreen), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('community tab switch and action sheets work', (tester) async {
      await _pumpPage(tester, const CommunityMainScreen());

      await tester.tap(find.text('群组'));
      await tester.pumpAndSettle();
      expect(find.text('群组'), findsWidgets);

      await tester.tap(find.byIcon(Icons.search));
      await tester.pumpAndSettle();
      expect(find.text('搜索用户'), findsOneWidget);
      expect(find.text('搜索群组'), findsOneWidget);
      Navigator.of(tester.element(find.text('搜索用户'))).pop();
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.person_add_outlined));
      await tester.pumpAndSettle();
      expect(find.text('发现新好友'), findsOneWidget);
      expect(find.text('创建群组'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('profile can navigate to edit profile screen', (tester) async {
      final router = GoRouter(
        initialLocation: '/profile',
        routes: [
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/profile/edit',
            builder: (context, state) => const EditProfileScreen(),
          ),
        ],
      );

      await _pumpRouterPage(
        tester,
        router,
        overrides: [
          authProvider.overrideWith((ref) => _FakeAuthNotifier()),
        ],
      );

      await tester.tap(find.text('个人资料'));
      await tester.pumpAndSettle();

      expect(find.byType(EditProfileScreen), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('chat input sends text through callback', (tester) async {
      String? sent;
      await _pumpPage(
        tester,
        Scaffold(
          body: ChatInput(
            onSend: (text, {replyToId}) => sent = text,
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), '本地联调发送测试');
      await tester.pumpAndSettle();
      await tester.tap(find.bySemanticsLabel('Send message'));
      await tester.pumpAndSettle();

      expect(sent, '本地联调发送测试');
      expect(tester.takeException(), isNull);
    });

    testWidgets('edit profile save triggers profile update', (tester) async {
      final authNotifier = _FakeAuthNotifier();

      await _pumpPage(
        tester,
        const EditProfileScreen(),
        overrides: [
          authProvider.overrideWith((ref) => authNotifier),
        ],
      );

      await tester.enterText(find.byType(TextField).at(0), '联调昵称');
      await tester.enterText(
          find.byType(TextField).at(1), 'integration@example.com',);
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(authNotifier.lastProfileUpdate, isNotNull);
      expect(authNotifier.lastProfileUpdate!['nickname'], '联调昵称');
      expect(
        authNotifier.lastProfileUpdate!['email'],
        'integration@example.com',
      );
      expect(tester.takeException(), isNull);
    });

    testWidgets('create group submits data and reaches group detail route', (
      tester,
    ) async {
      final repository = _FakeCommunityRepository();
      final router = GoRouter(
        initialLocation: '/community/groups/create',
        routes: [
          GoRoute(
            path: '/community/groups/create',
            builder: (context, state) => const CreateGroupScreen(),
          ),
          GoRoute(
            path: '/community/groups/:id',
            builder: (context, state) => Text(
              'group:${state.pathParameters['id']}',
            ),
          ),
        ],
      );

      await _pumpRouterPage(
        tester,
        router,
        overrides: [
          authProvider.overrideWith((ref) => _FakeAuthNotifier()),
          communityRepositoryProvider.overrideWithValue(repository),
        ],
      );

      await tester.enterText(find.byType(TextFormField).at(0), '联调群组');
      await tester.enterText(find.byType(TextFormField).at(1), '群组说明');
      await tester.enterText(find.byType(TextFormField).at(2), 'AI,联调');
      await tester.tap(
        find.byWidgetPredicate(
          (widget) =>
              widget.runtimeType.toString() == 'SparkleButton' &&
              (widget as dynamic).label == 'Create Group',
        ),
      );
      await tester.pumpAndSettle();

      expect(repository.createdGroup, isNotNull);
      expect(repository.createdGroup!.name, '联调群组');
      expect(repository.createdGroup!.focusTags, ['AI', '联调']);
      expect(find.text('group:group-created-1'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('notification tap marks item as read', (tester) async {
      final repository = _FakeNotificationRepository();
      DemoDataService.isDemoMode = false;

      await _pumpPage(
        tester,
        const NotificationListScreen(),
        overrides: [
          authProvider.overrideWith((ref) => _FakeAuthNotifier()),
          notificationRepositoryProvider.overrideWithValue(repository),
        ],
      );

      await tester.tap(find.text('联调通知'));
      await tester.pumpAndSettle();

      expect(repository.markedReadIds, ['notif-1']);
      expect(tester.takeException(), isNull);
    });

    testWidgets('create post submits data through repository', (tester) async {
      final repository = _FakeCommunityRepository();
      final router = GoRouter(
        initialLocation: '/community/posts/create',
        routes: [
          GoRoute(
            path: '/community',
            builder: (context, state) => const Scaffold(body: Text('feed')),
          ),
          GoRoute(
            path: '/community/posts/create',
            builder: (context, state) => const CreatePostScreen(),
          ),
        ],
      );

      await _pumpRouterPage(
        tester,
        router,
        overrides: [
          authProvider.overrideWith((ref) => _FakeAuthNotifier()),
          communityRepositoryProvider.overrideWithValue(repository),
        ],
      );

      await tester.enterText(find.byType(TextField).at(0), '联调发帖内容');
      await tester.enterText(find.byType(TextField).at(1), '知识星图');
      await tester.tap(find.text('Post'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 700));
      await tester.pumpAndSettle();

      expect(repository.createdPostRequest, isNotNull);
      expect(repository.createdPostRequest!.content, '联调发帖内容');
      expect(repository.createdPostRequest!.topic, '知识星图');
      expect(tester.takeException(), isNull);
    });

    testWidgets('calendar add event persists through repository',
        (tester) async {
      final repository = _FakeCalendarRepository();
      final router = GoRouter(
        initialLocation: '/calendar',
        routes: [
          GoRoute(
            path: '/calendar',
            builder: (context, state) => const CalendarStatsScreen(),
          ),
        ],
      );

      await tester.binding.setSurfaceSize(const Size(1280, 2200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pumpRouterPage(
        tester,
        router,
        overrides: [
          calendarRepositoryProvider.overrideWithValue(repository),
        ],
      );

      await tester.tap(find.byIcon(Icons.add));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(0), '联调日程');
      await tester.enterText(find.byType(TextField).at(1), 'Sparkle HQ');
      await tester.enterText(find.byType(TextField).at(2), '验证日历保存链路');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(repository.addedEvents, hasLength(1));
      expect(repository.addedEvents.single.title, '联调日程');
      expect(repository.addedEvents.single.location, 'Sparkle HQ');
      expect(repository.addedEvents.single.description, '验证日历保存链路');
      expect(tester.takeException(), isNull);
    });
  });
}

Future<void> _pumpPage(
  WidgetTester tester,
  Widget page, {
  List<Override> overrides = const [],
}) async {
  SharedPreferences.setMockInitialValues({});
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith((ref) => _FakeAuthNotifier()),
      ...overrides,
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: page,
      ),
    ),
  );

  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _pumpRouterPage(
  WidgetTester tester,
  GoRouter router, {
  List<Override> overrides = const [],
}) async {
  SharedPreferences.setMockInitialValues({});
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(overrides: overrides);
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );

  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(),
    );
  }

  Map<String, dynamic>? lastProfileUpdate;
  List<String>? lastPasswordChange;

  @override
  Future<void> checkAuthStatus() async {}

  @override
  Future<void> updateProfile(Map<String, dynamic> data) async {
    lastProfileUpdate = Map<String, dynamic>.from(data);
    final current = state.user ?? _buildUser();
    state = state.copyWith(
      user: UserModel(
        id: current.id,
        username: current.username,
        email: (data['email'] as String?) ?? current.email,
        nickname: (data['nickname'] as String?) ?? current.nickname,
        avatarUrl: current.avatarUrl,
        avatarStatus: current.avatarStatus,
        pendingAvatarUrl: current.pendingAvatarUrl,
        flameLevel: current.flameLevel,
        flameBrightness: current.flameBrightness,
        depthPreference: current.depthPreference,
        curiosityPreference: current.curiosityPreference,
        schedulePreferences: current.schedulePreferences,
        pushPreferences: current.pushPreferences,
        isActive: current.isActive,
        status: current.status,
        createdAt: current.createdAt,
        updatedAt: DateTime(2026, 3, 6),
        photonBalance: current.photonBalance,
        equippedSkin: current.equippedSkin,
        equippedTitle: current.equippedTitle,
      ),
    );
  }

  @override
  Future<void> changePassword(String oldPassword, String newPassword) async {
    lastPasswordChange = [oldPassword, newPassword];
  }
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'router_test_user',
      email: 'router@example.com',
      nickname: 'Router Test',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), _MemorySecureStorage());

  @override
  Future<bool> isLoggedIn() async => true;

  @override
  Future<UserModel> getCurrentUser() async => _buildUser();

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeCommunityRepository extends CommunityRepository {
  _FakeCommunityRepository() : super(_UnusedApiClient());

  GroupCreate? createdGroup;
  CreatePostRequest? createdPostRequest;
  final List<Post> _posts = <Post>[];

  @override
  Future<List<Post>> getFeed({int page = 1, int limit = 20}) async => _posts;

  @override
  Future<List<GroupListItem>> getMyGroups() async => const [];

  @override
  Future<String> createPost(CreatePostRequest request) async {
    createdPostRequest = request;
    _posts.insert(
      0,
      Post(
        id: 'post-created-1',
        userId: request.userId,
        content: request.content,
        imageUrls: request.imageUrls,
        topic: request.topic,
        createdAt: DateTime(2026, 3, 6),
        user: const PostUser(
            id: '00000000-0000-0000-0000-000000000001',
            username: 'router_test_user',),
      ),
    );
    return 'post-created-1';
  }

  @override
  Future<GroupInfo> createGroup(GroupCreate group) async {
    createdGroup = group;
    return GroupInfo(
      id: 'group-created-1',
      name: group.name,
      description: group.description,
      type: group.type,
      focusTags: group.focusTags,
      deadline: group.deadline,
      sprintGoal: group.sprintGoal,
      memberCount: 1,
      totalFlamePower: 0,
      todayCheckinCount: 0,
      totalTasksCompleted: 0,
      maxMembers: group.maxMembers,
      isPublic: group.isPublic,
      joinRequiresApproval: group.joinRequiresApproval,
      myRole: GroupRole.owner,
      createdAt: DateTime(2026, 3, 6),
      updatedAt: DateTime(2026, 3, 6),
    );
  }
}

class _FakeNotificationRepository extends NotificationRepository {
  _FakeNotificationRepository() : super(_UnusedApiClient());

  final List<String> markedReadIds = <String>[];

  @override
  Future<List<NotificationModel>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
  }) async =>
      [
        NotificationModel(
          id: 'notif-1',
          userId: 'u1',
          title: '联调通知',
          content: '点我应标记已读',
          type: 'system',
          isRead: false,
          createdAt: DateTime(2026, 3, 6),
        ),
      ];

  @override
  Future<void> markAsRead(String id) async {
    markedReadIds.add(id);
  }
}

class _FakeCalendarRepository extends CalendarRepository {
  _FakeCalendarRepository() : super(_UnusedNotificationService());

  final List<CalendarEventModel> addedEvents = <CalendarEventModel>[];

  @override
  Future<List<CalendarEventModel>> getEvents() async => const [];

  @override
  Future<void> addEvent(CalendarEventModel event) async {
    addedEvents.add(event);
  }
}

class _UnusedNotificationService implements NotificationService {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<void> write({
    required String key,
    String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values[key];

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.remove(key);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
