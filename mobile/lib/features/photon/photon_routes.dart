import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/photon/presentation/screens/photon_redeem_pro_screen.dart';
import 'package:sparkle/features/photon/presentation/screens/transaction_history_screen.dart';

class PhotonRoutes {
  static const String transactionHistory = '/photon/history';
  // /photon/transfer 已撤（PHOTON 卡 #10，A-SPEC2 PH-G3）：P2P 转账触反刷
  // 敏感区（transfer_in 已被排除出可兑换基数），未审计面不应对深链开放；
  // 屏文件 photon_transfer_screen.dart 保留未删，登记于
  // docs/engineering/KNOWN_CODE_DEBT_LEDGER.md，深链落路由 errorBuilder 兜底。
  static const String redeemPro = '/photon/redeem-pro'; // D-COMM-2 兑换出口

  static List<RouteBase> get routes => [
        GoRoute(
          path: transactionHistory,
          name: 'photonTransactionHistory',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const TransactionHistoryScreen(),
          ),
        ),
        // D-COMM-2：光子兑 Pro（「学出会员」奖励出口）
        GoRoute(
          path: redeemPro,
          name: 'photonRedeemPro',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const PhotonRedeemProScreen(),
          ),
        ),
      ];
}
