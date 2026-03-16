import 'dart:io';

import 'package:fluwx/fluwx.dart' as fluwx;
import 'package:logger/logger.dart';

import 'share_service.dart';

/// WeChat share service implementation
///
/// Handles sharing images to WeChat session (friends) and timeline (moments)
/// using the fluwx SDK.
class WeChatShareService {
  factory WeChatShareService() => _instance;
  WeChatShareService._internal();
  static final WeChatShareService _instance = WeChatShareService._internal();

  final fluwx.Fluwx _weChat = fluwx.Fluwx();
  final Logger _logger = Logger();

  bool _initialized = false;

  /// Check if WeChat SDK is initialized and available
  bool get isAvailable => _initialized;

  /// Initialize WeChat SDK (should be called at app startup)
  ///
  /// Returns true if initialization was successful
  Future<bool> initialize({
    required String appId,
    String? universalLink,
  }) async {
    if (_initialized) return true;

    try {
      if (Platform.isIOS && universalLink == null) {
        _logger.w('WeChat universal link required on iOS');
        return false;
      }

      final registered = await _weChat.registerApi(
        appId: appId,
        universalLink: Platform.isIOS ? universalLink : null,
      );

      _initialized = registered;
      if (registered) {
        _logger.i('WeChat Share SDK initialized');
      } else {
        _logger.w('WeChat Share SDK registration failed');
      }
      return registered;
    } catch (e) {
      _logger.e('WeChat Share SDK init error: $e');
      return false;
    }
  }

  /// Check if WeChat is installed on this device
  Future<bool> isWeChatInstalled() async {
    if (!_initialized) return false;
    try {
      return await _weChat.isWeChatInstalled;
    } catch (e) {
      _logger.e('Failed to check WeChat installation: $e');
      return false;
    }
  }

  /// Share image to WeChat session (friends)
  Future<ShareResult> shareImageToSession(File imageFile) =>
      _shareImage(imageFile, fluwx.WeChatScene.session);

  /// Share image to WeChat timeline (moments)
  Future<ShareResult> shareImageToTimeline(File imageFile) =>
      _shareImage(imageFile, fluwx.WeChatScene.timeline);

  Future<ShareResult> _shareImage(File imageFile, fluwx.WeChatScene scene) async {
    if (!_initialized) {
      _logger.w('WeChat SDK not initialized');
      return ShareResult.unavailable;
    }

    final installed = await isWeChatInstalled();
    if (!installed) {
      _logger.w('WeChat not installed');
      return ShareResult.unavailable;
    }

    try {
      final result = await _weChat.share(
        fluwx.WeChatShareImageModel(
          fluwx.WeChatImage.file(imageFile),
          scene: scene,
        ),
      );

      if (result) {
        _logger.i('WeChat share initiated successfully');
        return ShareResult.success;
      } else {
        _logger.w('WeChat share returned false');
        return ShareResult.error;
      }
    } catch (e) {
      _logger.e('WeChat share error: $e');
      return ShareResult.error;
    }
  }

  /// Share webpage with thumbnail to WeChat
  Future<ShareResult> shareWebPage({
    required String webPageUrl,
    required String title,
    String? description,
    fluwx.WeChatImage? thumbnail,
    fluwx.WeChatScene scene = fluwx.WeChatScene.session,
  }) async {
    if (!_initialized) {
      return ShareResult.unavailable;
    }

    final installed = await isWeChatInstalled();
    if (!installed) {
      return ShareResult.unavailable;
    }

    try {
      final result = await _weChat.share(
        fluwx.WeChatShareWebPageModel(
          webPageUrl,
          title: title,
          description: description,
          thumbnail: thumbnail,
          scene: scene,
        ),
      );

      return result ? ShareResult.success : ShareResult.error;
    } catch (e) {
      _logger.e('WeChat webpage share error: $e');
      return ShareResult.error;
    }
  }
}
