import 'dart:io';

/// Share channel types
enum ShareChannel {
  weChatSession, // 微信好友
  weChatTimeline, // 朋友圈
  systemShare, // 系统分享
  community, // 社区内分享
  saveToGallery, // 保存到相册
  copyLink, // 复制链接
}

/// Share result status
enum ShareResult {
  success,
  cancelled,
  unavailable,
  error,
}

/// Payload for sharing operations
class SharePayload {
  const SharePayload({
    required this.title,
    this.description,
    this.imageFile,
    this.achievementId,
    this.resourceType,
    this.resourceId,
  });

  final String title;
  final String? description;
  final File? imageFile;
  final String? achievementId; // 用于生成深度链接
  final String? resourceType; // 资源类型（社区分享用）
  final String? resourceId; // 资源ID（社区分享用）

  SharePayload copyWith({
    String? title,
    String? description,
    File? imageFile,
    String? achievementId,
    String? resourceType,
    String? resourceId,
  }) => SharePayload(
    title: title ?? this.title,
    description: description ?? this.description,
    imageFile: imageFile ?? this.imageFile,
    achievementId: achievementId ?? this.achievementId,
    resourceType: resourceType ?? this.resourceType,
    resourceId: resourceId ?? this.resourceId,
  );
}

/// Abstract share service interface
abstract class ShareService {
  /// Share to specified channel with given payload
  Future<ShareResult> share(ShareChannel channel, SharePayload payload);

  /// Check if a specific channel is available on this device
  Future<bool> isChannelAvailable(ShareChannel channel);
}
