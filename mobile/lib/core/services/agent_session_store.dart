import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

enum AgentSessionScope {
  group,
  privateChat,
  focus,
}

class AgentSessionStore {
  AgentSessionStore(this._prefs);

  final SharedPreferences _prefs;
  static const String _prefix = 'agent_session';
  static const Uuid _uuid = Uuid();

  String getOrCreateSessionId(AgentSessionScope scope, String contextId, String userId) {
    final key = _buildKey(scope, contextId, userId);
    final existing = _prefs.getString(key);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final sessionId = 'agent_${_uuid.v4()}';
    _prefs.setString(key, sessionId);
    return sessionId;
  }

  Future<void> resetSession(AgentSessionScope scope, String contextId, String userId) async {
    final key = _buildKey(scope, contextId, userId);
    await _prefs.remove(key);
  }

  String _buildKey(AgentSessionScope scope, String contextId, String userId) =>
      '$_prefix:${scope.name}:$contextId:$userId';
}
