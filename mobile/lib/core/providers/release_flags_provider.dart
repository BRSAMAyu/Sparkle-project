import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// Release scope flags 五旗契约的移动端视图（V3-FIX-190）。
///
/// 单一权威在 backend `settings.RELEASE_ENABLE_*`（唯一 BaseSettings env 管道，
/// 见 backend/app/config/release_flags.py）；本类只解码 `/release-flags` 契约
/// 响应——键集冻结（shop / photon_transfer / public_leaderboards /
/// public_community / visual_elements），增删必须与契约快照同步。
class ReleaseFlags {
  const ReleaseFlags({
    this.shop = false,
    this.photonTransfer = false,
    this.publicLeaderboards = false,
    this.publicCommunity = false,
    this.visualElements = false,
  });

  /// 缺省全 false = fail-closed：与 backend RELEASE_ENABLE_* 默认值同向。
  /// 契约未拉到/拉取失败时，消费面（VE 解锁调用、元素奖励叙事）按关闭处理——
  /// 宁可少展示，不发注定 403 的请求。
  factory ReleaseFlags.fromContractJson(Map<String, dynamic> json) =>
      ReleaseFlags(
        shop: json['shop'] == true,
        photonTransfer: json['photon_transfer'] == true,
        publicLeaderboards: json['public_leaderboards'] == true,
        publicCommunity: json['public_community'] == true,
        visualElements: json['visual_elements'] == true,
      );

  final bool shop;
  final bool photonTransfer;
  final bool publicLeaderboards;
  final bool publicCommunity;
  final bool visualElements;
}

/// 拉取并缓存 `/release-flags`（会话级，一次成功后不再重发）。
class ReleaseFlagsNotifier extends StateNotifier<ReleaseFlags> {
  ReleaseFlagsNotifier(this._apiClient) : super(const ReleaseFlags());

  final ApiClient _apiClient;
  Future<ReleaseFlags>? _inFlight;
  bool _loaded = false;

  /// 幂等拉取：成功后钉住本会话值；失败保持 fail-closed 并允许下次重试。
  Future<ReleaseFlags> ensureLoaded() =>
      _loaded ? Future<ReleaseFlags>.value(state) : (_inFlight ??= _fetch());

  Future<ReleaseFlags> _fetch() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.releaseFlags,
      );
      final data = response.data;
      if (data != null) {
        state = ReleaseFlags.fromContractJson(data);
      }
      _loaded = true;
    } catch (e) {
      debugPrint('Release flags fetch failed (fail-closed kept): $e');
    } finally {
      if (!_loaded) _inFlight = null;
    }
    return state;
  }

  /// 测试与本地覆盖用：直接钉住旗值（置为已加载）。
  @visibleForTesting
  void seed(ReleaseFlags flags) {
    _loaded = true;
    _inFlight = null;
    state = flags;
  }
}

/// Release flags 消费入口（V3-FIX-190）。
///
/// 当前消费面：核心动线成就解锁短路（task_execution_screen /
/// mindfulness_provider）+ 成就弹窗「解锁视觉元素」叙事裁剪
/// （achievement_unlock_dialog）。
final releaseFlagsProvider =
    StateNotifierProvider<ReleaseFlagsNotifier, ReleaseFlags>(
  (ref) => ReleaseFlagsNotifier(ref.watch(apiClientProvider)),
);
