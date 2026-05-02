import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

enum OfflineQueueIndicatorStatus {
  hidden,
  queued,
  sending,
  complete,
}

class OfflineQueueIndicator extends StatelessWidget {
  const OfflineQueueIndicator({
    required this.status,
    required this.pendingCount,
    super.key,
  });

  final OfflineQueueIndicatorStatus status;
  final int pendingCount;

  @override
  Widget build(BuildContext context) {
    if (status == OfflineQueueIndicatorStatus.hidden) {
      return const SizedBox.shrink();
    }

    final copy = _OfflineQueueIndicatorCopy(status, pendingCount);
    final material = _materialFor(status);

    return Semantics(
      container: true,
      label: copy.semanticLabel,
      liveRegion: true,
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        switchInCurve: Curves.easeOutCubic,
        switchOutCurve: Curves.easeInCubic,
        child: Container(
          key: ValueKey<String>('${status.name}-$pendingCount'),
          margin: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing8,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: material.$1,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: material.$2),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _StatusGlyph(status: status),
              const SizedBox(width: DS.spacing8),
              Flexible(
                child: Text(
                  copy.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  (Color, Color) _materialFor(OfflineQueueIndicatorStatus status) {
    switch (status) {
      case OfflineQueueIndicatorStatus.queued:
        return (
          Color.alphaBlend(
            DS.warning.withValues(alpha: 0.10),
            DS.surfacePrimary,
          ),
          DS.warning.withValues(alpha: 0.34),
        );
      case OfflineQueueIndicatorStatus.sending:
        return (
          Color.alphaBlend(
            DS.info.withValues(alpha: 0.10),
            DS.surfacePrimary,
          ),
          DS.info.withValues(alpha: 0.34),
        );
      case OfflineQueueIndicatorStatus.complete:
        return (
          Color.alphaBlend(
            DS.success.withValues(alpha: 0.10),
            DS.surfacePrimary,
          ),
          DS.success.withValues(alpha: 0.34),
        );
      case OfflineQueueIndicatorStatus.hidden:
        return (DS.surfacePrimary, DS.border);
    }
  }
}

class _StatusGlyph extends StatelessWidget {
  const _StatusGlyph({required this.status});

  final OfflineQueueIndicatorStatus status;

  @override
  Widget build(BuildContext context) {
    switch (status) {
      case OfflineQueueIndicatorStatus.queued:
        return Icon(Icons.wifi_off_rounded, size: 16, color: DS.warning);
      case OfflineQueueIndicatorStatus.sending:
        return SizedBox(
          width: 14,
          height: 14,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(DS.info),
          ),
        );
      case OfflineQueueIndicatorStatus.complete:
        return Icon(
          Icons.check_circle_outline_rounded,
          size: 16,
          color: DS.success,
        );
      case OfflineQueueIndicatorStatus.hidden:
        return const SizedBox.shrink();
    }
  }
}

class _OfflineQueueIndicatorCopy {
  _OfflineQueueIndicatorCopy(this.status, this.count);

  final OfflineQueueIndicatorStatus status;
  final int count;

  bool get _zh => I18nService.instance.isChinese;

  String get label {
    switch (status) {
      case OfflineQueueIndicatorStatus.queued:
        return _zh
            ? '$count 条消息等待发送'
            : '$count ${count == 1 ? 'message' : 'messages'} waiting to send';
      case OfflineQueueIndicatorStatus.sending:
        return _zh
            ? '正在发送 $count 条消息...'
            : 'Sending $count ${count == 1 ? 'message' : 'messages'}...';
      case OfflineQueueIndicatorStatus.complete:
        return _zh ? '已全部发送' : 'All sent';
      case OfflineQueueIndicatorStatus.hidden:
        return '';
    }
  }

  String get semanticLabel {
    switch (status) {
      case OfflineQueueIndicatorStatus.queued:
        return _zh
            ? '离线队列中有 $count 条消息等待发送'
            : 'Offline queue has $count ${count == 1 ? 'message' : 'messages'} waiting to send';
      case OfflineQueueIndicatorStatus.sending:
        return _zh
            ? '网络已恢复，正在发送 $count 条排队消息'
            : 'Connection restored, sending $count queued ${count == 1 ? 'message' : 'messages'}';
      case OfflineQueueIndicatorStatus.complete:
        return _zh ? '排队消息已全部发送' : 'All queued messages have been sent';
      case OfflineQueueIndicatorStatus.hidden:
        return '';
    }
  }
}
