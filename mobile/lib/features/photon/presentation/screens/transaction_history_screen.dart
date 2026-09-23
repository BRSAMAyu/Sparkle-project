import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/photon/presentation/widgets/transaction_history_list.dart';

/// 光子流水页（N13 资产面三件套的「流水」件：余额数字展示位必须有可达的
/// 流水下钻）。原居 photon_balance_card.dart（PHOTON 卡 #10 死卡删除时迁出），
/// 屏本体行为保持不变。
class TransactionHistoryScreen extends ConsumerWidget {
  const TransactionHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(
          title: Text(context.l10n.auto_transactionhistory),
        ),
        body: const ContentConstraint(
          child: TransactionHistoryList(),
        ),
      );
}
