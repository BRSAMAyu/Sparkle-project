import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/agent_session_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('AgentSessionStore reuses and resets session ids', () async {
    final prefs = await SharedPreferences.getInstance();
    final store = AgentSessionStore(prefs);

    final first = store.getOrCreateSessionId(AgentSessionScope.group, 'group-1', 'user-1');
    final second = store.getOrCreateSessionId(AgentSessionScope.group, 'group-1', 'user-1');

    expect(first, second);

    await store.resetSession(AgentSessionScope.group, 'group-1', 'user-1');
    final third = store.getOrCreateSessionId(AgentSessionScope.group, 'group-1', 'user-1');

    expect(third, isNot(first));
  });
}
