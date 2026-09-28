import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';
import 'package:sparkle/features/memory/presentation/widgets/context_receipt_panel.dart';
import 'package:sparkle/features/memory/presentation/widgets/understanding_overview_view.dart';

/// 「Sparkle 对我的理解」完整视图（U-03 四组 + Why-this receipt + 操作）。
///
/// 30 秒测试（acceptance ①）：进入即见四组（你告诉我的 / 我从你的行动中
/// 观察到的 / 我还不确定的 / 对你有效过的方法），每组条目自带来源与操作，
/// 顶部一句话说明"这是什么、能改什么"。
///
/// V4-U03：顶部新增「这次的理解」回执面板（I06 context_selection_receipt
/// 读面唯一呈现位）——最近一次 Sparkle 实际用到的理解，可核对来源并直接忘记。
class UnderstandingScreen extends ConsumerWidget {
  const UnderstandingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => GraphiteScaffold(
        safeArea: false,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            semanticLabel: context.l10n.back,
            onPressed: () => context.pop(),
            variant: ButtonVariant.ghost,
          ),
          title: Text(
            context.l10n.understandingViewTitle,
            style: DS.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          iconTheme: IconThemeData(color: DS.textPrimary),
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          elevation: 0,
        ),
        child: ContentConstraint(
          child: SparkleRefreshIndicator(
            onRefresh: () async {
              await ref.read(understandingOverviewProvider.notifier).refresh();
              await ref.read(contextReceiptProvider.notifier).refresh();
            },
            child: const SingleChildScrollView(
              physics: AlwaysScrollableScrollPhysics(),
              padding: EdgeInsets.all(DS.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ContextReceiptPanel(),
                  SizedBox(height: DS.xl),
                  UnderstandingOverviewView(embedded: false),
                ],
              ),
            ),
          ),
        ),
      );
}
