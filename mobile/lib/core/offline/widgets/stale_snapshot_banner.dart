import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';

/// N34/N36（A-SPEC6）：本地快照 stale 标记——「离线数据 · 截至 X」。
///
/// 呈现来自本地 warm 缓存（离线/网络失败回读）的数据时必须挂本徽标
/// （N36：stale 必带时点，复用既有时间格式化）。纯展示件，不携带交互。
class StaleSnapshotBanner extends StatelessWidget {
  const StaleSnapshotBanner({required this.fetchedAt, super.key});

  /// 快照的数据时点戳（缓存落库时刻）。
  final DateTime fetchedAt;

  @override
  Widget build(BuildContext context) {
    final color = DS.semanticWarning;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Semantics(
            // 读屏可达：图标有语义名；时点文案由下方 Text 原生可读
            //（不重复包一层 label，免双播报）。
            label: context.l10n.staleSnapshotAsOf(
              Formatters.formatDateTime(fetchedAt),
            ),
            child: Icon(Icons.cloud_off_outlined, size: 16, color: color),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              context.l10n.staleSnapshotAsOf(
                Formatters.formatDateTime(fetchedAt),
              ),
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
