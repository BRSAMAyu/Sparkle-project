import 'dart:io';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

enum AppPermissionKind {
  microphone,
  notifications,
  camera,
  photos,
  storage,
}

extension AppPermissionKindX on AppPermissionKind {
  String title(BuildContext context) {
    switch (this) {
      case AppPermissionKind.microphone:
        return context.l10n.voiceInputPermissionTitle;
      case AppPermissionKind.notifications:
        return '需要通知权限';
      case AppPermissionKind.camera:
        return '需要相机权限';
      case AppPermissionKind.photos:
        return '需要相册权限';
      case AppPermissionKind.storage:
        return '需要存储权限';
    }
  }

  String description(BuildContext context) {
    switch (this) {
      case AppPermissionKind.microphone:
        return context.l10n.voiceInputPermissionContent;
      case AppPermissionKind.notifications:
        return '请在系统设置中允许 Sparkle 发送通知，才能接收任务提醒、学习进度和关键更新。';
      case AppPermissionKind.camera:
        return '请在系统设置中允许 Sparkle 访问相机，才能拍摄头像或上传图片。';
      case AppPermissionKind.photos:
        return '请在系统设置中允许 Sparkle 访问照片，才能选择图片或保存内容到相册。';
      case AppPermissionKind.storage:
        return '请在系统设置中允许 Sparkle 访问存储空间，才能保存或导出文件。';
    }
  }

  String settingsHint() {
    final isIOS = Platform.isIOS;
    switch (this) {
      case AppPermissionKind.microphone:
        return isIOS
            ? '打开系统设置后，请进入“Sparkle > 麦克风”并开启权限。'
            : '打开应用信息后，请进入“权限 > 麦克风”并开启权限。';
      case AppPermissionKind.notifications:
        return isIOS
            ? '打开系统设置后，请进入“Sparkle > 通知”并开启权限。'
            : '打开应用信息后，请进入“通知”或“权限”页面并允许 Sparkle 发送通知。';
      case AppPermissionKind.camera:
        return isIOS
            ? '打开系统设置后，请进入“Sparkle > 相机”并开启权限。'
            : '打开应用信息后，请进入“权限 > 相机”并开启权限。';
      case AppPermissionKind.photos:
        return isIOS
            ? '打开系统设置后，请进入“Sparkle > 照片”并开启权限。'
            : '打开应用信息后，请进入“权限 > 照片和视频”并开启权限。';
      case AppPermissionKind.storage:
        return isIOS
            ? '打开系统设置后，请进入“Sparkle > 照片/文件”并开启相关权限。'
            : '打开应用信息后，请进入“权限 > 文件和媒体/存储”并开启权限。';
    }
  }

  IconData get icon {
    switch (this) {
      case AppPermissionKind.microphone:
        return Icons.mic_rounded;
      case AppPermissionKind.notifications:
        return Icons.notifications_active_rounded;
      case AppPermissionKind.camera:
        return Icons.camera_alt_rounded;
      case AppPermissionKind.photos:
        return Icons.photo_library_rounded;
      case AppPermissionKind.storage:
        return Icons.folder_rounded;
    }
  }
}

Future<void> showAppPermissionDialog(
  BuildContext context, {
  required AppPermissionKind permission,
}) {
  return showDialog<void>(
    context: context,
    builder: (dialogContext) => Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: GraphiteModalSurface(
        title: permission.title(dialogContext),
        showHandle: false,
        borderRadius: BorderRadius.circular(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: DS.surfaceTertiary,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(permission.icon, color: DS.primaryBase),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Text(
                    permission.description(dialogContext),
                    style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.md),
            Text(
              permission.settingsHint(),
              style: DS.labelSmall.copyWith(color: DS.textTertiary),
            ),
            const SizedBox(height: DS.lg),
            Row(
              children: [
                Expanded(
                  child: SparkleButton.ghost(
                    label: dialogContext.l10n.cancel,
                    onPressed: () => Navigator.of(dialogContext).pop(),
                  ),
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: SparkleButton.primary(
                    label: dialogContext.l10n.voiceInputOpenSettings,
                    onPressed: () async {
                      Navigator.of(dialogContext).pop();
                      await openAppSettings();
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    ),
  );
}
