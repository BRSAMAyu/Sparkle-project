import 'dart:io';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

enum AppPermissionKind {
  microphone,
  notifications,
  camera,
  photos,
  storage,
}

extension AppPermissionKindX on AppPermissionKind {
  String title(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    switch (this) {
      case AppPermissionKind.microphone:
        return context.l10n.voiceInputPermissionTitle;
      case AppPermissionKind.notifications:
        return zh ? '需要通知权限' : 'Notifications permission needed';
      case AppPermissionKind.camera:
        return zh ? '需要相机权限' : 'Camera permission needed';
      case AppPermissionKind.photos:
        return zh ? '需要相册权限' : 'Photos permission needed';
      case AppPermissionKind.storage:
        return zh ? '需要存储权限' : 'Storage permission needed';
    }
  }

  String description(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    switch (this) {
      case AppPermissionKind.microphone:
        return context.l10n.voiceInputPermissionContent;
      case AppPermissionKind.notifications:
        return zh
            ? '请在系统设置中允许 Sparkle 发送通知，才能接收任务提醒、学习进度和关键更新。'
            : 'Please allow Sparkle to send notifications in system settings to receive task reminders, learning progress, and key updates.';
      case AppPermissionKind.camera:
        return zh
            ? '请在系统设置中允许 Sparkle 访问相机，才能拍摄头像或上传图片。'
            : 'Please allow Sparkle to access the camera in system settings to take photos or upload images.';
      case AppPermissionKind.photos:
        return zh
            ? '请在系统设置中允许 Sparkle 访问照片，才能选择图片或保存内容到相册。'
            : 'Please allow Sparkle to access photos in system settings to select images or save content.';
      case AppPermissionKind.storage:
        return zh
            ? '请在系统设置中允许 Sparkle 访问存储空间，才能保存或导出文件。'
            : 'Please allow Sparkle to access storage in system settings to save or export files.';
    }
  }

  String settingsHint() {
    final isIOS = Platform.isIOS;
    final zh = I18nService.instance.isChinese;
    switch (this) {
      case AppPermissionKind.microphone:
        return isIOS
            ? zh
                ? '打开系统设置后，请进入”Sparkle > 麦克风”并开启权限。'
                : 'In Settings, go to “Sparkle > Microphone” and enable it.'
            : zh
                ? '打开应用信息后，请进入”权限 > 麦克风”并开启权限。'
                : 'In App Info, go to “Permissions > Microphone” and enable it.';
      case AppPermissionKind.notifications:
        return isIOS
            ? zh
                ? '打开系统设置后，请进入”Sparkle > 通知”并开启权限。'
                : 'In Settings, go to “Sparkle > Notifications” and enable them.'
            : zh
                ? '打开应用信息后，请进入”通知”或”权限”页面并允许 Sparkle 发送通知。'
                : 'In App Info, go to “Notifications” or “Permissions” and allow Sparkle to send notifications.';
      case AppPermissionKind.camera:
        return isIOS
            ? zh
                ? '打开系统设置后，请进入”Sparkle > 相机”并开启权限。'
                : 'In Settings, go to “Sparkle > Camera” and enable it.'
            : zh
                ? '打开应用信息后，请进入”权限 > 相机”并开启权限。'
                : 'In App Info, go to “Permissions > Camera” and enable it.';
      case AppPermissionKind.photos:
        return isIOS
            ? zh
                ? '打开系统设置后，请进入”Sparkle > 照片”并开启权限。'
                : 'In Settings, go to “Sparkle > Photos” and enable it.'
            : zh
                ? '打开应用信息后，请进入”权限 > 照片和视频”并开启权限。'
                : 'In App Info, go to “Permissions > Photos & videos” and enable it.';
      case AppPermissionKind.storage:
        return isIOS
            ? zh
                ? '打开系统设置后，请进入”Sparkle > 照片/文件”并开启相关权限。'
                : 'In Settings, go to “Sparkle > Photos/Files” and enable the relevant permissions.'
            : zh
                ? '打开应用信息后，请进入”权限 > 文件和媒体/存储”并开启权限。'
                : 'In App Info, go to “Permissions > Files and media/Storage” and enable it.';
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
}) =>
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        final media = MediaQuery.of(dialogContext);
        final stackActions = media.size.width < 360;
        return Dialog(
          backgroundColor: Colors.transparent,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: 460,
              maxHeight: media.size.height * 0.85,
            ),
            child: GraphiteModalSurface(
              title: permission.title(dialogContext),
              showHandle: false,
              borderRadius: BorderRadius.circular(28),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
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
                            style:
                                DS.bodyMedium.copyWith(color: DS.textSecondary),
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
                    if (stackActions) ...[
                      SizedBox(
                        width: double.infinity,
                        child: SparkleButton.primary(
                          label: dialogContext.l10n.voiceInputOpenSettings,
                          onPressed: () async {
                            Navigator.of(dialogContext).pop();
                            await openAppSettings();
                          },
                        ),
                      ),
                      const SizedBox(height: DS.sm),
                      SizedBox(
                        width: double.infinity,
                        child: SparkleButton.ghost(
                          label: dialogContext.l10n.cancel,
                          onPressed: () => Navigator.of(dialogContext).pop(),
                        ),
                      ),
                    ] else
                      Row(
                        children: [
                          Expanded(
                            child: SparkleButton.ghost(
                              label: dialogContext.l10n.cancel,
                              onPressed: () =>
                                  Navigator.of(dialogContext).pop(),
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
          ),
        );
      },
    );
