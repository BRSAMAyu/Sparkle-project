import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:image_gallery_saver/image_gallery_saver.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'share_service.dart';
import 'wechat_share_service.dart';

/// Shareable content types for the universal share system
enum ShareableContentType {
  achievement,
  taskCompletion,
  planProgress,
  capsule,
  knowledgeNode,
  learningReport,
  cognitivePrism,
}

/// Extension for ShareableContentType
extension ShareableContentTypeExtension on ShareableContentType {
  String get stringValue => switch (this) {
        ShareableContentType.achievement => 'achievement',
        ShareableContentType.taskCompletion => 'task',
        ShareableContentType.planProgress => 'plan',
        ShareableContentType.capsule => 'capsule',
        ShareableContentType.knowledgeNode => 'node',
        ShareableContentType.learningReport => 'report',
        ShareableContentType.cognitivePrism => 'prism',
      };

  String get deepLinkPrefix => switch (this) {
        ShareableContentType.achievement => 'sparkle://achievement',
        ShareableContentType.taskCompletion => 'sparkle://task',
        ShareableContentType.planProgress => 'sparkle://plan',
        ShareableContentType.capsule => 'sparkle://capsule',
        ShareableContentType.knowledgeNode => 'sparkle://node',
        ShareableContentType.learningReport => '',
        ShareableContentType.cognitivePrism => 'sparkle://prism',
      };

  String get defaultTitle => switch (this) {
        ShareableContentType.achievement => '成就分享',
        ShareableContentType.taskCompletion => '任务完成',
        ShareableContentType.planProgress => '学习计划',
        ShareableContentType.capsule => '时光胶囊',
        ShareableContentType.knowledgeNode => '知识节点',
        ShareableContentType.learningReport => '学习报告',
        ShareableContentType.cognitivePrism => '认知棱镜',
      };
}

/// Universal privacy settings for share cards
class UniversalSharePrivacySettings {
  const UniversalSharePrivacySettings({
    this.showUserName = true,
    this.showUserAvatar = true,
    this.showDetailedStats = true,
    this.showProgressPercentage = true,
    this.customDisplayName,
  });

  final bool showUserName;
  final bool showUserAvatar;
  final bool showDetailedStats;
  final bool showProgressPercentage;
  final String? customDisplayName;

  UniversalSharePrivacySettings copyWith({
    bool? showUserName,
    bool? showUserAvatar,
    bool? showDetailedStats,
    bool? showProgressPercentage,
    String? customDisplayName,
  }) =>
      UniversalSharePrivacySettings(
        showUserName: showUserName ?? this.showUserName,
        showUserAvatar: showUserAvatar ?? this.showUserAvatar,
        showDetailedStats: showDetailedStats ?? this.showDetailedStats,
        showProgressPercentage:
            showProgressPercentage ?? this.showProgressPercentage,
        customDisplayName: customDisplayName ?? this.customDisplayName,
      );

  Map<String, dynamic> toMap() => {
        'show_user_name': showUserName,
        'show_user_avatar': showUserAvatar,
        'show_detailed_stats': showDetailedStats,
        'show_progress_percentage': showProgressPercentage,
        if (customDisplayName != null) 'custom_display_name': customDisplayName,
      };

  String settingsHash() =>
      '$showUserName$showUserAvatar$showDetailedStats$showProgressPercentage${customDisplayName?.hashCode ?? ''}';
}

/// Universal payload for sharing operations
class UniversalSharePayload {
  const UniversalSharePayload({
    required this.contentType,
    required this.resourceId,
    required this.title,
    this.subtitle,
    this.description,
    this.metadata,
    this.privacySettings = const UniversalSharePrivacySettings(),
    this.templateId = 'cosmic',
    this.cardImageUrl,
    this.shareMessage,
  });

  final ShareableContentType contentType;
  final String resourceId;
  final String title;
  final String? subtitle;
  final String? description;
  final Map<String, dynamic>? metadata;
  final UniversalSharePrivacySettings privacySettings;
  final String templateId;
  final String? cardImageUrl;
  final String? shareMessage;

  UniversalSharePayload copyWith({
    ShareableContentType? contentType,
    String? resourceId,
    String? title,
    String? subtitle,
    String? description,
    Map<String, dynamic>? metadata,
    UniversalSharePrivacySettings? privacySettings,
    String? templateId,
    String? cardImageUrl,
    String? shareMessage,
  }) =>
      UniversalSharePayload(
        contentType: contentType ?? this.contentType,
        resourceId: resourceId ?? this.resourceId,
        title: title ?? this.title,
        subtitle: subtitle ?? this.subtitle,
        description: description ?? this.description,
        metadata: metadata ?? this.metadata,
        privacySettings: privacySettings ?? this.privacySettings,
        templateId: templateId ?? this.templateId,
        cardImageUrl: cardImageUrl ?? this.cardImageUrl,
        shareMessage: shareMessage ?? this.shareMessage,
      );

  String get deepLink => '${contentType.deepLinkPrefix}/$resourceId';
  String get defaultShareMessage => shareMessage ?? title;
}

/// Result of a share operation
class UniversalShareResult {
  const UniversalShareResult({
    required this.isSuccess,
    this.error,
    this.filePath,
  });

  final bool isSuccess;
  final String? error;
  final String? filePath;

  static const completed = UniversalShareResult(isSuccess: true);
  static const cancelled = UniversalShareResult(isSuccess: false);
  static const unavailable = UniversalShareResult(isSuccess: false);
}

/// Universal share service for handling all sharing operations
class UniversalShareService {
  factory UniversalShareService() => _instance;
  UniversalShareService._internal();
  static final UniversalShareService _instance = UniversalShareService._internal();

  final WeChatShareService _wechatShare = WeChatShareService();

  /// Share to WeChat session (friends)
  Future<UniversalShareResult> shareToWeChatSession(File imageFile) async {
    final result = await _wechatShare.shareImageToSession(imageFile);
    return _convertShareResult(result);
  }

  /// Share to WeChat timeline (moments)
  Future<UniversalShareResult> shareToWeChatTimeline(File imageFile) async {
    final result = await _wechatShare.shareImageToTimeline(imageFile);
    return _convertShareResult(result);
  }

  /// Share via system share sheet
  Future<UniversalShareResult> shareToSystem({
    required File imageFile,
    String? text,
  }) async {
    try {
      await share_plus.SharePlus.instance.share(
        share_plus.ShareParams(
          files: [share_plus.XFile(imageFile.path)],
          text: text,
        ),
      );
      return UniversalShareResult.completed;
    } catch (e) {
      return UniversalShareResult(isSuccess: false, error: e.toString());
    }
  }

  /// Save image to device gallery
  Future<UniversalShareResult> saveToGallery(
    File imageFile, {
    String? name,
  }) async {
    try {
      final photoStatus = await Permission.photos.request();
      PermissionStatus? storageStatus;

      if (!photoStatus.isGranted &&
          !photoStatus.isLimited &&
          Platform.isAndroid) {
        storageStatus = await Permission.storage.request();
      }

      final hasPermission = photoStatus.isGranted ||
          photoStatus.isLimited ||
          (storageStatus?.isGranted ?? false);

      if (!hasPermission) {
        return const UniversalShareResult(
          isSuccess: false,
          error: 'Permission denied',
        );
      }

      final result = await ImageGallerySaver.saveFile(
        imageFile.path,
        name: name ?? 'sparkle_share',
      );

      if (result != null) {
        final isSuccess = result is Map &&
            (result['isSuccess'] == true || result['success'] == true);
        if (isSuccess) {
          return UniversalShareResult(
            isSuccess: true,
            filePath: imageFile.path,
          );
        }
      }

      return const UniversalShareResult(
        isSuccess: false,
        error: 'Save failed',
      );
    } catch (e) {
      return UniversalShareResult(isSuccess: false, error: e.toString());
    }
  }

  /// Download card image from URL to a temporary file
  Future<File?> downloadCardImage(String url, {String? fileName}) async {
    try {
      final response = await http.get(Uri.parse(url));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        return null;
      }

      final tempDir = await getTemporaryDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final file = File(
        '${tempDir.path}/${fileName ?? 'share_card'}_$timestamp.png',
      );
      await file.writeAsBytes(response.bodyBytes);
      return file;
    } catch (e) {
      return null;
    }
  }

  /// Copy deep link to clipboard
  Future<void> copyDeepLink(String deepLink) async {
    await Clipboard.setData(ClipboardData(text: deepLink));
  }

  /// Check if WeChat is available
  bool get isWeChatAvailable => _wechatShare.isAvailable;

  /// Check if WeChat is installed
  Future<bool> isWeChatInstalled() => _wechatShare.isWeChatInstalled();

  /// Convert legacy ShareResult to UniversalShareResult
  UniversalShareResult _convertShareResult(ShareResult result) =>
      switch (result) {
        ShareResult.success => UniversalShareResult.completed,
        ShareResult.cancelled => UniversalShareResult.cancelled,
        ShareResult.unavailable => UniversalShareResult.unavailable,
        ShareResult.error => const UniversalShareResult(
            isSuccess: false,
            error: 'Unknown error',
          ),
      };
}

/// Riverpod provider for UniversalShareService
final universalShareServiceProvider = Provider<UniversalShareService>((ref) {
  return UniversalShareService();
});
